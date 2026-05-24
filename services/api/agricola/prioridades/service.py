from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Iterable, Literal
from uuid import UUID, NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from agricola.benchmark import BenchmarkAgricolaV1Service
from agricola.diagnostico import DiagnosticoOperacionalEconomicoAgricolaV1Service
from agricola.dre import AgricolaDreKpiService, DREAgricolaV1Service
from agricola.dre.schemas import DREWarning
from agricola.eficiencia import EficienciaOperacionalAgricolaV1Service
from agricola.recomendacoes import RecomendacoesOperacionaisEconomicasAgricolaV1Service
from agricola.rentabilidade import RentabilidadeAgricolaV1Service
from agricola.safras.models import Safra
from core.models.tenant_audit_log import TenantAuditLog
from core.services.audit_service import write_audit_log
from core.base_service import BaseService

from .schemas import (
    PrioridadeAgricolaHistoricoItem,
    PrioridadeAgricolaItem,
    PrioridadeAgricolaResponse,
    PrioridadeAgricolaResumo,
    PrioridadeAgricolaStatusResponse,
)


SEVERIDADE_ORDEM = {
    "PRIORIDADE_CRITICA": 0,
    "RISCO_ECONOMICO": 1,
    "RISCO_OPERACIONAL": 2,
    "ATENCAO": 3,
    "INFO": 4,
}

SEVERIDADE_BASE = {
    "INFO": 20,
    "ATENCAO": 50,
    "RISCO_OPERACIONAL": 72,
    "RISCO_ECONOMICO": 88,
    "PRIORIDADE_CRITICA": 100,
}

ORIGEM_PESO = {
    "DIAGNOSTICO": 12,
    "RECOMENDACAO": 10,
    "BENCHMARK": 8,
    "WARNING": 6,
}

TIPOS_MONETARIOS = {
    "MARGEM_ABAIXO_MEDIA_TENANT",
    "CUSTO_HECTARE_ACIMA_MEDIA",
    "PRODUCTION_UNIT_BAIXA_EFICIENCIA",
    "EQUIPAMENTO_CUSTO_ELEVADO",
    "RESULTADO_OPERACIONAL_NEGATIVO",
    "RESULTADO_SAFRA_ABAIXO_BENCHMARK",
}

TIPOS_RAZAO = {
    "JORNADA_BAIXA_PRODUTIVIDADE",
    "RECORRENCIA_WARNING_ECONOMICO",
    "RECORRENCIA_INCONSISTENCIA_OPERACIONAL",
}

PRIORIDADE_STATUS_RESOURCE = "agricola_prioridade_status"
PRIORIDADE_COMMENT_RESOURCE = "agricola_prioridade_comment"
PRIORIDADE_STATUS_NAMESPACE = uuid5(NAMESPACE_URL, "agrosaas:agricola:prioridades:status")


@dataclass(slots=True)
class _SinalPrioridade:
    chave: str
    tipo: str
    severidade: str
    origem: Literal["DIAGNOSTICO", "RECOMENDACAO", "BENCHMARK", "WARNING"]
    origem_codigo: str
    origem_titulo: str
    scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    item_id: str
    label: str
    entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"]
    entidade_id: str
    entidade_label: str
    contexto_operacional: str
    contexto_economico: str
    acao_sugerida: str
    impacto_estimado: float | None = None
    warnings_relevantes: list[str] = field(default_factory=list)


class PrioridadesAgricolasV1Service(BaseService[Safra]):
    """Camada oficial de central inteligente de prioridades agrícolas derivada dos analytics oficiais."""

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
    ) -> PrioridadeAgricolaResponse:
        dre = await DREAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        dre_kpis = dre.kpis or AgricolaDreKpiService.calcular(
            dre,
            area_total_ha=self._area_total(dre),
            warnings=dre.warnings,
        )
        rentabilidade = await RentabilidadeAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        eficiencia = await EficienciaOperacionalAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        benchmark = await BenchmarkAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        diagnostico = await DiagnosticoOperacionalEconomicoAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        recomendacoes = await RecomendacoesOperacionaisEconomicasAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        contexto = self._montar_contexto(
            dre_kpis=dre_kpis,
            rentabilidade=rentabilidade,
            eficiencia=eficiencia,
            benchmark=benchmark,
        )

        sinais = [
            *self._sinais_diagnostico(diagnostico, contexto),
            *self._sinais_recomendacoes(recomendacoes),
            *self._sinais_benchmark(benchmark, contexto),
            *self._sinais_warnings(dre.warnings, "DRE", safra_id),
            *self._sinais_warnings(diagnostico.warnings, "DIAGNOSTICO", safra_id),
            *self._sinais_warnings(benchmark.warnings, "BENCHMARK", safra_id),
            *self._sinais_warnings(recomendacoes.warnings, "RECOMENDACAO", safra_id),
        ]
        prioridades = self._consolidar(sinais)
        prioridades = self._rankear(prioridades)
        status_map = await self._carregar_statuses(prioridades)
        prioridades = self._aplicar_statuses(prioridades, status_map)
        resumo = self._resumo(prioridades)

        warnings = self._dedupe_warnings([
            *dre.warnings,
            *diagnostico.warnings,
            *benchmark.warnings,
            *recomendacoes.warnings,
        ])
        sujeito_reconciliacao = bool(warnings or any(item.severidade != "INFO" for item in prioridades))
        observacao = "prioridades sujeitas à reconciliação." if sujeito_reconciliacao else None

        return PrioridadeAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            prioridades=prioridades,
            resumo=resumo,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )

    async def atualizar_status(
        self,
        *,
        safra_id: UUID,
        prioridade_id: str,
        status: str,
        observacao: str | None,
        user_id: UUID | None,
        responsavel_nome: str | None,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PrioridadeAgricolaStatusResponse:
        prioridade = await self._localizar_prioridade(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        if prioridade is None:
            raise LookupError("Prioridade agrícola não encontrada")

        prioridade_status_id = self._status_resource_id(prioridade_id)
        status_atual = prioridade.status
        historico_atual = await self._historico_status(prioridade_id)
        status_anterior = historico_atual[0].status_novo if historico_atual else status_atual

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=user_id,
            action="update",
            resource=PRIORIDADE_STATUS_RESOURCE,
            resource_id=prioridade_status_id,
            payload_before={
                "prioridade_id": prioridade_id,
                "status": status_anterior,
                "observacao": historico_atual[0].observacao if historico_atual else None,
            },
            payload_after={
                "prioridade_id": prioridade_id,
                "status_anterior": status_anterior,
                "status_novo": status,
                "status": status,
                "observacao": observacao,
                "responsavel_id": str(user_id) if user_id else None,
                "responsavel_nome": responsavel_nome,
                "alterado_em": datetime.now(timezone.utc).isoformat(),
            },
        )
        await self.session.commit()
        return await self.obter_status(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    async def _historico_status(self, prioridade_id: str) -> list[PrioridadeAgricolaHistoricoItem]:
        historico = await self._historico_timeline(prioridade_id)
        return [item for item in historico if item.evento_tipo == "STATUS"]

    async def obter_status(
        self,
        *,
        safra_id: UUID,
        prioridade_id: str,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PrioridadeAgricolaStatusResponse:
        return await self.obter_historico(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    async def obter_historico(
        self,
        *,
        safra_id: UUID,
        prioridade_id: str,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PrioridadeAgricolaStatusResponse:
        prioridade = await self._localizar_prioridade(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        if prioridade is None:
            raise LookupError("Prioridade agrícola não encontrada")

        historico = await self._historico_timeline(prioridade_id)
        status_atual = next(
            (item.status_novo for item in historico if item.evento_tipo == "STATUS" and item.status_novo),
            prioridade.status,
        )
        return PrioridadeAgricolaStatusResponse(
            prioridade_id=prioridade_id,
            prioridade_status_id=self._status_resource_id(prioridade_id),
            status_atual=status_atual,
            historico=historico,
            sujeito_reconciliacao=prioridade.severidade != "INFO",
        )

    async def adicionar_comentario(
        self,
        *,
        safra_id: UUID,
        prioridade_id: str,
        comentario: str,
        user_id: UUID | None,
        responsavel_nome: str | None,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PrioridadeAgricolaStatusResponse:
        texto = comentario.strip()
        if not texto:
            raise ValueError("Comentário não pode ser vazio")

        prioridade = await self._localizar_prioridade(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        if prioridade is None:
            raise LookupError("Prioridade agrícola não encontrada")

        now = datetime.now(timezone.utc)
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=user_id,
            action="create",
            resource=PRIORIDADE_COMMENT_RESOURCE,
            resource_id=self._status_resource_id(prioridade_id),
            payload_before=None,
            payload_after={
                "prioridade_id": prioridade_id,
                "evento_tipo": "COMENTARIO",
                "comentario": texto,
                "responsavel_id": str(user_id) if user_id else None,
                "responsavel_nome": responsavel_nome,
                "alterado_em": now.isoformat(),
            },
        )
        await self.session.commit()
        return await self.obter_historico(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    def _montar_contexto(self, *, dre_kpis, rentabilidade, eficiencia, benchmark) -> dict[str, object]:
        return {
            "dre_kpis": dre_kpis,
            "rentabilidade_por_id": {self._item_key(item): item for item in rentabilidade.production_units},
            "rentabilidade_safra": rentabilidade.safra,
            "eficiencia_por_id": {self._item_key(item): item for item in eficiencia.production_units + eficiencia.equipamentos + eficiencia.operacoes + [eficiencia.safra]},
            "benchmark_por_id": {self._item_key(item): item for item in benchmark.production_units},
            "benchmark_safra": benchmark.safra,
            "benchmark_ref": benchmark.destaques.referencia or benchmark.safra,
        }

    def _sinais_diagnostico(self, diagnostico, contexto: dict[str, object]) -> list[_SinalPrioridade]:
        signals: list[_SinalPrioridade] = []
        rent_by_id = contexto["rentabilidade_por_id"]
        eff_by_id = contexto["eficiencia_por_id"]
        bench_by_id = contexto["benchmark_por_id"]
        for item in diagnostico.ranking:
            impact = self._impacto_diagnostico(item, rent_by_id, eff_by_id, bench_by_id, contexto)
            scope = item.scope if item.scope != "TENANT" else "SAFRA"
            entidade_id = item.id if item.scope != "TENANT" else str(contexto["rentabilidade_safra"].safra_id)
            entidade_label = item.label if item.scope != "TENANT" else contexto["rentabilidade_safra"].label
            signals.append(self._signal_from_item(
                origem="DIAGNOSTICO",
                codigo=item.codigo,
                titulo=item.titulo,
                tipo=item.codigo if item.codigo in self._tipos_validos() else self._tipo_warning(item.severidade),
                severidade=item.severidade,
                scope=scope,
                item_id=item.id,
                label=item.label,
                entidade_tipo=scope,
                entidade_id=entidade_id,
                entidade_label=entidade_label,
                contexto_operacional=item.mensagem,
                contexto_economico=self._contexto_economico(item.codigo, item.valor_observado, item.valor_referencia, impact),
                acao_sugerida=item.sugestao or self._acao_padrao(item.codigo),
                impacto_estimado=impact,
                warnings_relevantes=list(item.warnings_relevantes or []),
            ))
        return signals

    def _sinais_recomendacoes(self, recomendacoes) -> list[_SinalPrioridade]:
        signals: list[_SinalPrioridade] = []
        for item in recomendacoes.recomendacoes:
            signals.append(self._signal_from_item(
                origem="RECOMENDACAO",
                codigo=item.origem_diagnostica_codigo,
                titulo=item.origem_diagnostica_titulo,
                tipo=item.origem_diagnostica_codigo if item.origem_diagnostica_codigo in self._tipos_validos() else self._tipo_warning(item.severidade),
                severidade=item.severidade,
                scope=item.scope,
                item_id=item.id,
                label=item.label,
                entidade_tipo=item.entidade_tipo,
                entidade_id=item.entidade_id,
                entidade_label=item.entidade_label,
                contexto_operacional=item.contexto_operacional,
                contexto_economico=item.contexto_economico,
                acao_sugerida=item.acao_sugerida,
                impacto_estimado=None,
                warnings_relevantes=list(item.warnings_relevantes or []),
            ))
        return signals

    def _sinais_benchmark(self, benchmark, contexto: dict[str, object]) -> list[_SinalPrioridade]:
        signals: list[_SinalPrioridade] = []
        benchmark_ref = contexto["benchmark_ref"]
        safra = benchmark.safra
        if safra.resultado_por_hectare is not None and benchmark_ref and benchmark_ref.resultado_por_hectare is not None and safra.resultado_por_hectare < benchmark_ref.resultado_por_hectare:
            impacto = abs(float(benchmark_ref.resultado_por_hectare) - float(safra.resultado_por_hectare))
            signals.append(self._signal_from_item(
                origem="BENCHMARK",
                codigo="RESULTADO_SAFRA_ABAIXO_BENCHMARK",
                titulo="Resultado da safra abaixo do benchmark",
                tipo="RESULTADO_SAFRA_ABAIXO_BENCHMARK",
                severidade=self._severidade_por_desvio(impacto, base="RISCO_ECONOMICO"),
                scope="SAFRA",
                item_id=str(safra.id),
                label=safra.label,
                entidade_tipo="SAFRA",
                entidade_id=str(safra.id),
                entidade_label=safra.label,
                contexto_operacional=(
                    f"Resultado operacional por hectare ({self._fmt_money(safra.resultado_por_hectare)}) "
                    f"está abaixo da referência do benchmark ({self._fmt_money(benchmark_ref.resultado_por_hectare)})."
                ),
                contexto_economico=self._contexto_economico("RESULTADO_SAFRA_ABAIXO_BENCHMARK", safra.resultado_por_hectare, benchmark_ref.resultado_por_hectare, impacto),
                acao_sugerida="Revisar margem, receita líquida e custo operacional da safra.",
                impacto_estimado=impacto,
                warnings_relevantes=list(safra.warnings_relevantes or []),
            ))
        return signals

    def _sinais_warnings(self, warnings: Iterable[DREWarning], origem: str, safra_id: UUID) -> list[_SinalPrioridade]:
        signals: list[_SinalPrioridade] = []
        for warning in warnings or []:
            tipo = warning.codigo if warning.codigo in self._tipos_validos() else self._tipo_warning(warning.severidade)
            signals.append(self._signal_from_item(
                origem="WARNING",
                codigo=warning.codigo,
                titulo=warning.titulo,
                tipo=tipo,
                severidade=self._severidade_warning(warning.severidade),
                scope="SAFRA",
                item_id=f"{safra_id}:{warning.codigo}",
                label="Safra consolidada",
                entidade_tipo="SAFRA",
                entidade_id=str(safra_id),
                entidade_label="Safra consolidada",
                contexto_operacional=warning.mensagem,
                contexto_economico=f"Warning oficial {warning.codigo} originado em {origem}.",
                acao_sugerida=self._acao_padrao(warning.codigo),
                impacto_estimado=None,
                warnings_relevantes=[warning.codigo],
            ))
        return signals

    def _signal_from_item(
        self,
        *,
        origem: Literal["DIAGNOSTICO", "RECOMENDACAO", "BENCHMARK", "WARNING"],
        codigo: str,
        titulo: str,
        tipo: str,
        severidade: str,
        scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"],
        item_id: str,
        label: str,
        entidade_tipo: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"],
        entidade_id: str,
        entidade_label: str,
        contexto_operacional: str,
        contexto_economico: str,
        acao_sugerida: str,
        impacto_estimado: float | None,
        warnings_relevantes: list[str],
    ) -> _SinalPrioridade:
        return _SinalPrioridade(
            chave=f"{codigo}:{entidade_tipo}:{entidade_id}",
            tipo=tipo if tipo in self._tipos_validos() else self._tipo_warning(severidade),
            severidade=severidade,
            origem=origem,
            origem_codigo=codigo,
            origem_titulo=titulo,
            scope=scope,
            item_id=item_id,
            label=label,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            entidade_label=entidade_label,
            contexto_operacional=contexto_operacional,
            contexto_economico=contexto_economico,
            acao_sugerida=acao_sugerida,
            impacto_estimado=impacto_estimado,
            warnings_relevantes=warnings_relevantes,
        )

    def _consolidar(self, sinais: list[_SinalPrioridade]) -> list[PrioridadeAgricolaItem]:
        grupos: dict[str, list[_SinalPrioridade]] = defaultdict(list)
        for sinal in sinais:
            grupos[sinal.chave].append(sinal)

        itens: list[PrioridadeAgricolaItem] = []
        for chave, grupo in grupos.items():
            dominante = self._selecao_dominante(grupo)
            recorrencia = len(grupo)
            score = self._calcular_score(dominante, recorrencia)
            severidade = self._escalar_severidade(dominante.severidade, score, recorrencia)
            itens.append(PrioridadeAgricolaItem(
                scope=dominante.scope,
                id=chave,
                label=dominante.label,
                tipo=dominante.tipo if dominante.tipo in self._tipos_validos() else self._tipo_warning(dominante.severidade),
                severidade=severidade,
                score_prioridade=score,
                origem=dominante.origem,
                origem_codigo=dominante.origem_codigo,
                origem_titulo=dominante.origem_titulo,
                impacto_estimado=max((abs(s.impacto_estimado or 0.0) for s in grupo), default=None),
                contexto_operacional=dominante.contexto_operacional,
                contexto_economico=dominante.contexto_economico,
                acao_sugerida=dominante.acao_sugerida,
                entidade_tipo=dominante.entidade_tipo,
                entidade_id=dominante.entidade_id,
                entidade_label=dominante.entidade_label,
                warnings_relevantes=self._dedupe_strings([warn for sinal in grupo for warn in sinal.warnings_relevantes]),
                recorrencia=recorrencia,
                fontes_relacionadas=self._dedupe_strings([sinal.origem for sinal in grupo]),
            ))
        return itens

    def _rankear(self, items: list[PrioridadeAgricolaItem]) -> list[PrioridadeAgricolaItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                -item.score_prioridade,
                SEVERIDADE_ORDEM.get(item.severidade, 99),
                -(item.impacto_estimado or 0.0),
                item.tipo,
                item.entidade_label,
            ),
        )
        for index, item in enumerate(ranked, start=1):
            item.posicao = index
        return ranked

    def _resumo(self, items: list[PrioridadeAgricolaItem]) -> PrioridadeAgricolaResumo:
        severidades = Counter(item.severidade for item in items)
        tipos = Counter(item.tipo for item in items)
        origens = Counter(item.origem for item in items)
        status = Counter(item.status for item in items)
        return PrioridadeAgricolaResumo(
            total=len(items),
            nova=status.get("NOVA", 0),
            visualizada=status.get("VISUALIZADA", 0),
            em_analise=status.get("EM_ANALISE", 0),
            resolvida=status.get("RESOLVIDA", 0),
            ignorada=status.get("IGNORADA", 0),
            info=severidades.get("INFO", 0),
            atencao=severidades.get("ATENCAO", 0),
            risco_operacional=severidades.get("RISCO_OPERACIONAL", 0),
            risco_economico=severidades.get("RISCO_ECONOMICO", 0),
            prioridade_critica=severidades.get("PRIORIDADE_CRITICA", 0),
            por_origem=dict(sorted(origens.items())),
            por_tipo=dict(sorted(tipos.items())),
        )

    def _selecao_dominante(self, grupo: list[_SinalPrioridade]) -> _SinalPrioridade:
        return max(
            grupo,
            key=lambda sinal: (
                ORIGEM_PESO.get(sinal.origem, 0),
                SEVERIDADE_BASE.get(sinal.severidade, 0),
                abs(sinal.impacto_estimado or 0.0),
                len(sinal.warnings_relevantes),
            ),
        )

    def _calcular_score(self, sinal: _SinalPrioridade, recorrencia: int) -> int:
        base = SEVERIDADE_BASE.get(sinal.severidade, 20)
        origem = ORIGEM_PESO.get(sinal.origem, 0)
        impacto = self._impacto_bonus(sinal.tipo, sinal.impacto_estimado)
        recorrencia_bonus = min(max(recorrencia - 1, 0) * 7, 21)
        return min(100, base + origem + impacto + recorrencia_bonus)

    def _escalar_severidade(self, severidade: str, score: int, recorrencia: int) -> str:
        if recorrencia >= 3 and severidade in {"RISCO_ECONOMICO", "RISCO_OPERACIONAL"}:
            return "PRIORIDADE_CRITICA"
        if score >= 95:
            return "PRIORIDADE_CRITICA"
        return severidade

    @staticmethod
    def _impacto_bonus(tipo: str, impacto: float | None) -> int:
        if impacto is None:
            return 0
        escala = 1000.0 if tipo in TIPOS_MONETARIOS else 1.0
        return min(int(abs(impacto) / escala), 15)

    @staticmethod
    def _tipo_warning(severidade: str) -> str:
        return "RECORRENCIA_WARNING_ECONOMICO" if severidade == "RISCO_ECONOMICO" else "RECORRENCIA_INCONSISTENCIA_OPERACIONAL"

    @staticmethod
    def _severidade_warning(severidade: str) -> str:
        if severidade == "RISCO_ECONOMICO":
            return "RISCO_ECONOMICO"
        if severidade in {"RISCO_OPERACIONAL", "INCONSISTENCIA_MODERADA"}:
            return "RISCO_OPERACIONAL"
        return "INFO"

    @staticmethod
    def _severidade_por_desvio(desvio: float, *, base: str) -> str:
        if desvio >= 5000:
            return "PRIORIDADE_CRITICA"
        if desvio >= 2000:
            return base
        return "ATENCAO"

    @staticmethod
    def _acao_padrao(codigo: str) -> str:
        mapa = {
            "MARGEM_ABAIXO_MEDIA_TENANT": "Revisar margem e redistribuição econômica da safra.",
            "CUSTO_HECTARE_ACIMA_MEDIA": "Revisar os componentes de custo por hectare.",
            "PRODUCTION_UNIT_BAIXA_EFICIENCIA": "Revisar a ProductionUnit com baixa eficiência.",
            "EQUIPAMENTO_CUSTO_ELEVADO": "Inspecionar o equipamento e validar custo operacional.",
            "JORNADA_BAIXA_PRODUTIVIDADE": "Rever a jornada e a produtividade operacional.",
            "RESULTADO_OPERACIONAL_NEGATIVO": "Investigar a margem negativa e a reconciliação econômica.",
            "RESULTADO_SAFRA_ABAIXO_BENCHMARK": "Revisar a safra abaixo do benchmark.",
            "RECORRENCIA_WARNING_ECONOMICO": "Auditar a recorrência de warning econômico.",
            "RECORRENCIA_INCONSISTENCIA_OPERACIONAL": "Auditar a recorrência de inconsistência operacional.",
        }
        return mapa.get(codigo, "Acompanhar a evolução desta prioridade no recorte oficial.")

    @staticmethod
    def _contexto_economico(codigo: str, observado: float | None, referencia: float | None, impacto: float | None) -> str:
        if observado is None and referencia is None and impacto is None:
            return f"Prioridade consolidada do código {codigo}."
        if impacto is not None and referencia is not None:
            return f"Impacto estimado de {impacto:.2f} no recorte oficial."
        if observado is not None and referencia is not None:
            return f"Observado {observado} vs referência {referencia} no recorte oficial."
        if observado is not None:
            return f"Observado {observado} no recorte oficial."
        return f"Referência oficial {referencia} no recorte consolidado."

    @staticmethod
    def _impacto_diagnostico(item, rent_by_id, eff_by_id, bench_by_id, contexto: dict[str, object]) -> float | None:
        if item.valor_observado is not None and item.valor_referencia is not None:
            return abs(float(item.valor_observado) - float(item.valor_referencia))
        if item.codigo == "RESULTADO_OPERACIONAL_NEGATIVO":
            return abs(float(item.valor_observado or contexto["dre_kpis"].resultado_operacional or 0.0))
        if item.codigo == "RESULTADO_SAFRA_ABAIXO_BENCHMARK":
            benchmark_ref = contexto["benchmark_ref"]
            if benchmark_ref and benchmark_ref.resultado_por_hectare is not None:
                base = item.valor_observado if item.valor_observado is not None else contexto["rentabilidade_safra"].resultado_por_hectare
                if base is not None:
                    return abs(float(base) - float(benchmark_ref.resultado_por_hectare))
        if item.scope == "PRODUCTION_UNIT":
            chave = f"PRODUCTION_UNIT:{item.id}"
            rent_item = rent_by_id.get(chave)
            eff_item = eff_by_id.get(chave)
            bench_item = bench_by_id.get(chave)
            if item.codigo == "PRODUCTION_UNIT_BAIXA_EFICIENCIA":
                base = None
                for candidate in (
                    getattr(eff_item, "custo_operacional_por_hectare", None),
                    getattr(rent_item, "resultado_por_hectare", None),
                    getattr(bench_item, "resultado_por_hectare", None),
                ):
                    if candidate is not None:
                        base = float(candidate)
                        break
                return base
            if item.codigo == "CUSTO_HECTARE_ACIMA_MEDIA" and eff_item is not None:
                return float(getattr(eff_item, "custo_operacional_por_hectare", 0.0) or 0.0)
            if item.codigo == "MARGEM_ABAIXO_MEDIA_TENANT" and rent_item is not None:
                return float(getattr(rent_item, "margem_pct", 0.0) or 0.0)
        return None

    @staticmethod
    def _dedupe_strings(values: Iterable[str]) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.append(value)
        return seen

    @staticmethod
    def _dedupe_warnings(warnings: list[DREWarning]) -> list[DREWarning]:
        deduped: dict[str, DREWarning] = {}
        for warning in warnings:
            deduped[warning.codigo] = warning
        return list(deduped.values())

    async def _carregar_statuses(self, prioridades: list[PrioridadeAgricolaItem]) -> dict[str, dict[str, object]]:
        if not prioridades:
            return {}
        resource_ids = [self._status_resource_id(item.id) for item in prioridades]
        stmt = (
            select(TenantAuditLog)
            .where(
                TenantAuditLog.tenant_id == self.tenant_id,
                TenantAuditLog.resource == PRIORIDADE_STATUS_RESOURCE,
                TenantAuditLog.resource_id.in_(resource_ids),
            )
            .order_by(desc(TenantAuditLog.created_at))
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()
        prioridade_por_resource = {self._status_resource_id(item.id): item.id for item in prioridades}
        status_map: dict[str, dict[str, object]] = {}
        for log in logs:
            prioridade_id = prioridade_por_resource.get(log.resource_id)
            if not prioridade_id or prioridade_id in status_map:
                continue
            payload_after = log.payload_after or {}
            status_map[prioridade_id] = {
                "status": payload_after.get("status_novo") or payload_after.get("status") or "NOVA",
                "log": log,
            }
        return status_map

    def _aplicar_statuses(
        self,
        prioridades: list[PrioridadeAgricolaItem],
        status_map: dict[str, dict[str, object]],
    ) -> list[PrioridadeAgricolaItem]:
        for prioridade in prioridades:
            atual = status_map.get(prioridade.id)
            if atual:
                prioridade.status = str(atual["status"])
        return prioridades

    async def _historico_timeline(self, prioridade_id: str) -> list[PrioridadeAgricolaHistoricoItem]:
        stmt = (
            select(TenantAuditLog)
            .where(
                TenantAuditLog.tenant_id == self.tenant_id,
                TenantAuditLog.resource.in_([PRIORIDADE_STATUS_RESOURCE, PRIORIDADE_COMMENT_RESOURCE]),
                TenantAuditLog.resource_id == self._status_resource_id(prioridade_id),
            )
            .order_by(desc(TenantAuditLog.created_at))
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()
        historico: list[PrioridadeAgricolaHistoricoItem] = []
        for log in logs:
            payload_after = log.payload_after or {}
            evento_tipo = payload_after.get("evento_tipo") or ("STATUS" if log.resource == PRIORIDADE_STATUS_RESOURCE else "COMENTARIO")
            historico.append(PrioridadeAgricolaHistoricoItem(
                id=log.id,
                prioridade_id=payload_after.get("prioridade_id") or prioridade_id,
                evento_tipo=evento_tipo,
                status_anterior=payload_after.get("status_anterior"),
                status_novo=payload_after.get("status_novo") or payload_after.get("status"),
                observacao=payload_after.get("observacao"),
                comentario=payload_after.get("comentario"),
                responsavel_id=self._parse_uuid(payload_after.get("responsavel_id")),
                responsavel_nome=payload_after.get("responsavel_nome"),
                alterado_em=log.created_at,
            ))
        return historico

    async def _localizar_prioridade(
        self,
        *,
        safra_id: UUID,
        prioridade_id: str,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> PrioridadeAgricolaItem | None:
        response = await self.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        for prioridade in response.prioridades:
            if prioridade.id == prioridade_id:
                return prioridade
        return None

    @staticmethod
    def _parse_uuid(value) -> UUID | None:
        try:
            return UUID(str(value))
        except Exception:
            return None

    def _status_resource_id(self, prioridade_id: str) -> UUID:
        return uuid5(PRIORIDADE_STATUS_NAMESPACE, f"{self.tenant_id}:{prioridade_id}")

    @staticmethod
    def _tipos_validos() -> set[str]:
        return {
            "MARGEM_ABAIXO_MEDIA_TENANT",
            "CUSTO_HECTARE_ACIMA_MEDIA",
            "PRODUCTION_UNIT_BAIXA_EFICIENCIA",
            "EQUIPAMENTO_CUSTO_ELEVADO",
            "JORNADA_BAIXA_PRODUTIVIDADE",
            "RESULTADO_OPERACIONAL_NEGATIVO",
            "RESULTADO_SAFRA_ABAIXO_BENCHMARK",
            "RECORRENCIA_WARNING_ECONOMICO",
            "RECORRENCIA_INCONSISTENCIA_OPERACIONAL",
        }

    @staticmethod
    def _item_key(item) -> str:
        return f"{item.scope}:{item.id}"

    @staticmethod
    def _area_total(dre) -> float:
        return float(getattr(dre.kpis, "area_total_ha", 0.0) or 0.0)

    @staticmethod
    def _fmt_money(value: float | None) -> str:
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
