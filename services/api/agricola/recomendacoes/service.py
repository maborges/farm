from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from typing import Iterable, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agricola.diagnostico import DiagnosticoOperacionalEconomicoAgricolaV1Service
from agricola.dre.schemas import DREWarning
from agricola.safras.models import Safra
from core.base_service import BaseService
from core.services.analytics_request_cache import (
    build_analytics_scope_key,
    build_analytics_value_key,
    get_analytics_request_cache,
)

from .schemas import RecomendacaoAgricolaItem, RecomendacaoAgricolaResponse, RecomendacaoAgricolaResumo

SEVERIDADE_ORDEM = {
    "RISCO_ECONOMICO": 0,
    "RISCO_OPERACIONAL": 1,
    "ATENCAO": 2,
    "INFO": 3,
}


class RecomendacoesOperacionaisEconomicasAgricolaV1Service(BaseService[Safra]):
    """Camada oficial de recomendações assistidas derivada do diagnóstico agrícola governado."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Safra, session, tenant_id)

    async def gerar(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> RecomendacaoAgricolaResponse:
        cache_key = build_analytics_value_key(
            "agricola.recomendacoes.v1",
            build_analytics_scope_key(
                self.tenant_id,
                safra_id,
                production_unit_id,
                unidade_produtiva_id,
                data_inicio,
                data_fim,
            ),
        )
        cache = get_analytics_request_cache()
        if cache_key in cache:
            return cache[cache_key]

        diagnostico = await DiagnosticoOperacionalEconomicoAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        recomendacoes = [
            recomendacao
            for item in diagnostico.ranking
            for recomendacao in self._mapear_item(item, safra_id=safra_id)
        ]
        recomendacoes = self._rankear(recomendacoes)
        resumo = self._resumo(recomendacoes)

        sujeito_reconciliacao = bool(
            diagnostico.sujeito_reconciliacao
            or any(item.severidade != "INFO" for item in recomendacoes)
        )
        observacao = "recomendações sujeitas à reconciliação." if sujeito_reconciliacao else None

        response = RecomendacaoAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            recomendacoes=recomendacoes,
            resumo=resumo,
            warnings=diagnostico.warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )
        cache[cache_key] = response
        return response

    def _mapear_item(self, item, *, safra_id: UUID) -> list[RecomendacaoAgricolaItem]:
        mapeamentos = {
            "OPERACAO_CUSTO_FORA_CURVA": {
                "tipo": "REVISAO_OPERACAO",
                "entidade_tipo": "OPERATION",
                "acao": "Revisar a operação com custo fora da curva e confirmar a origem do custo alocado.",
            },
            "EQUIPAMENTO_CUSTO_ELEVADO": {
                "tipo": "INSPECAO_EQUIPAMENTO",
                "entidade_tipo": "EQUIPMENT",
                "acao": "Agendar inspeção de manutenção e checar consumo, disponibilidade e jornada do equipamento.",
            },
            "JORNADA_BAIXA_PRODUTIVIDADE": {
                "tipo": "REVISAO_JORNADA",
                "entidade_tipo": "JOURNEY",
                "acao": "Revisar desenho da jornada, deslocamento e aproveitamento de horas no campo.",
            },
            "PRODUCTION_UNIT_BAIXA_EFICIENCIA": {
                "tipo": "ANALISE_PRODUCTION_UNIT",
                "entidade_tipo": "PRODUCTION_UNIT",
                "acao": "Analisar a ProductionUnit abaixo da média e revisar custo, resultado e produtividade.",
            },
            "RESULTADO_OPERACIONAL_NEGATIVO": {
                "tipo": "INVESTIGACAO_MARGEM_NEGATIVA",
                "entidade_tipo": "SAFRA",
                "acao": "Investigar a margem negativa e confirmar se há custo ou receita divergente da DRE oficial.",
            },
            "CUSTO_HECTARE_ACIMA_MEDIA": {
                "tipo": "REVISAO_CUSTO_HECTARE",
                "entidade_tipo": "SAFRA",
                "acao": "Revisar os componentes de custo por hectare e priorizar os centros de custo mais pesados.",
            },
            "RECORRENCIA_WARNING_ECONOMICO": {
                "tipo": "REVISAO_RECONCILIACAO_ECONOMICA",
                "entidade_tipo": "SAFRA",
                "acao": "Auditar a recorrência de warning econômico antes de ampliar o uso analítico.",
            },
            "RECORRENCIA_INCONSISTENCIA_OPERACIONAL": {
                "tipo": "AUDITORIA_INCONSISTENCIA_OPERACIONAL",
                "entidade_tipo": "SAFRA",
                "acao": "Auditar a recorrência de inconsistências operacionais em operações, jornadas e apontamentos.",
            },
            "RESULTADO_SAFRA_ABAIXO_BENCHMARK": {
                "tipo": "ANALISE_SAFRA_BENCHMARK",
                "entidade_tipo": "SAFRA",
                "acao": "Analisar a safra abaixo do benchmark e revalidar custo, margem e produtividade.",
            },
            "MARGEM_ABAIXO_MEDIA_TENANT": {
                "tipo": "INVESTIGACAO_MARGEM_NEGATIVA",
                "entidade_tipo": "SAFRA",
                "acao": "Investigar a margem da safra abaixo da média do tenant e revisar o pacote econômico.",
            },
        }

        mapping = mapeamentos.get(item.codigo)
        if not mapping:
            return []

        return [
            self._build_recomendacao(
                item=item,
                safra_id=safra_id,
                tipo=mapping["tipo"],
                entidade_tipo=mapping["entidade_tipo"],
                acao_sugerida=mapping["acao"],
            )
        ]

    def _build_recomendacao(
        self,
        *,
        item,
        safra_id: UUID,
        tipo: Literal[
            "REVISAO_OPERACAO",
            "INSPECAO_EQUIPAMENTO",
            "REVISAO_JORNADA",
            "ANALISE_PRODUCTION_UNIT",
            "INVESTIGACAO_MARGEM_NEGATIVA",
            "REVISAO_CUSTO_HECTARE",
            "REVISAO_RECONCILIACAO_ECONOMICA",
            "AUDITORIA_INCONSISTENCIA_OPERACIONAL",
            "ANALISE_SAFRA_BENCHMARK",
        ],
        entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"],
        acao_sugerida: str,
    ) -> RecomendacaoAgricolaItem:
        contexto_operacional = item.mensagem
        contexto_economico = self._contexto_economico(item.codigo, item.valor_observado, item.valor_referencia)
        explicacao_objetiva = item.titulo
        entidade_id = item.id if item.scope != "TENANT" else str(safra_id)
        entidade_label = item.label if item.scope != "TENANT" else "Safra consolidada"
        return RecomendacaoAgricolaItem(
            scope=item.scope if item.scope != "TENANT" else "SAFRA",
            id=f"{item.codigo}:{item.id}",
            label=item.label,
            tipo=tipo,
            severidade=item.severidade,
            origem_diagnostica_codigo=item.codigo,
            origem_diagnostica_titulo=item.titulo,
            contexto_operacional=contexto_operacional,
            contexto_economico=contexto_economico,
            explicacao_objetiva=explicacao_objetiva,
            acao_sugerida=acao_sugerida,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            entidade_label=entidade_label,
            warnings_relevantes=list(item.warnings_relevantes or []),
        )

    @staticmethod
    def _contexto_economico(codigo: str, observado: float | None, referencia: float | None) -> str:
        if observado is None and referencia is None:
            return f"Recomendação derivada do diagnóstico {codigo}."
        if observado is None:
            return f"Observação sem valor observável, referência oficial de {referencia}."
        if referencia is None:
            return f"Valor observado oficial {observado} sem base comparativa."
        return f"Observado {observado} vs referência {referencia} no recorte oficial."

    def _rankear(self, items: list[RecomendacaoAgricolaItem]) -> list[RecomendacaoAgricolaItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                SEVERIDADE_ORDEM.get(item.severidade, 99),
                item.tipo,
                item.label,
            ),
        )
        for index, item in enumerate(ranked, start=1):
            item.posicao = index
        return ranked

    def _resumo(self, items: list[RecomendacaoAgricolaItem]) -> RecomendacaoAgricolaResumo:
        severidades = Counter(item.severidade for item in items)
        tipos = Counter(item.tipo for item in items)
        status = Counter(item.status for item in items)
        return RecomendacaoAgricolaResumo(
            total=len(items),
            nova=status.get("NOVA", 0),
            visualizada=status.get("VISUALIZADA", 0),
            aceita=status.get("ACEITA", 0),
            ignorada=status.get("IGNORADA", 0),
            info=severidades.get("INFO", 0),
            atencao=severidades.get("ATENCAO", 0),
            risco_operacional=severidades.get("RISCO_OPERACIONAL", 0),
            risco_economico=severidades.get("RISCO_ECONOMICO", 0),
            por_tipo=dict(sorted(tipos.items())),
        )
