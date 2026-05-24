from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from agricola.diagnostico import DiagnosticoOperacionalEconomicoAgricolaV1Service
from agricola.prioridades import PrioridadesAgricolasV1Service
from agricola.recomendacoes import RecomendacoesOperacionaisEconomicasAgricolaV1Service
from agricola.safras.models import Safra
from core.exceptions import EntityNotFoundError
from core.base_service import BaseService
from core.services.analytics_request_cache import (
    build_analytics_scope_key,
    memoize_request_async,
    record_analytics_service_call,
)
from core.services.analytics_taxonomy import normalizar_severidade, severidade_base, severidade_ordem

from .schemas import (
    PlanoAcaoOperacionalAgricolaFonte,
    PlanoAcaoOperacionalAgricolaItem,
    PlanoAcaoOperacionalAgricolaResponse,
    PlanoAcaoOperacionalAgricolaResumo,
)


class InteligenciaOperacionalAgricolaV1Service(BaseService[Safra]):
    """Projeção read-only de planos operacionais assistidos derivados da cadeia analítica oficial."""

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
    ) -> PlanoAcaoOperacionalAgricolaResponse:
        record_analytics_service_call("agricola.inteligencia_operacional.v1")
        scope_key = self._scope_key(
            safra_id,
            unidade_produtiva_id,
            production_unit_id,
            data_inicio,
            data_fim,
        )
        return await memoize_request_async(
            "agricola.inteligencia_operacional.v1",
            scope_key,
            lambda: self._gerar_sem_cache(
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                production_unit_id=production_unit_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
            ),
        )

    async def _gerar_sem_cache(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> PlanoAcaoOperacionalAgricolaResponse:
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
        prioridades = await PrioridadesAgricolasV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        plano_items = self._construir_planos(
            diagnostico=diagnostico.diagnosticos,
            recomendacoes=recomendacoes.recomendacoes,
            prioridades=prioridades.prioridades,
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
        )

        warnings = self._dedupe_warnings([
            *diagnostico.warnings,
            *recomendacoes.warnings,
            *prioridades.warnings,
        ])

        resumo = self._resumo(plano_items)
        sujeito_reconciliacao = bool(
            warnings or any(item.severidade != "INFO" for item in plano_items)
        )
        observacao = "planos operacionais sujeitos à reconciliação." if sujeito_reconciliacao else None

        response = PlanoAcaoOperacionalAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            planos=plano_items,
            resumo=resumo,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )
        return response

    def _scope_key(
        self,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> str:
        return build_analytics_scope_key(
            self.tenant_id,
            safra_id,
            production_unit_id,
            unidade_produtiva_id,
            data_inicio,
            data_fim,
        )

    async def obter_plano_por_id(
        self,
        *,
        plano_id: UUID,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> PlanoAcaoOperacionalAgricolaItem:
        resposta = await self.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        for plano in resposta.planos:
            if plano.id == plano_id:
                return plano
        raise EntityNotFoundError(f"Plano operacional assistido {plano_id} não encontrado.")

    def _construir_planos(
        self,
        *,
        diagnostico,
        recomendacoes,
        prioridades,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
    ) -> list[PlanoAcaoOperacionalAgricolaItem]:
        diagnostico_index = {
            self._plano_chave_fonte("DIAGNOSTICO", item.codigo, item.scope, item.id): item
            for item in diagnostico
        }
        recomendacoes_index = {
            self._plano_chave_fonte("RECOMENDACAO", item.origem_diagnostica_codigo, item.scope, item.entidade_id): item
            for item in recomendacoes
        }

        itens: list[PlanoAcaoOperacionalAgricolaItem] = []
        usados: set[str] = set()

        for item in sorted(
            prioridades,
            key=lambda prioridade: (
                severidade_ordem(prioridade.severidade),
                -int(prioridade.score_prioridade or 0),
                prioridade.tipo,
                prioridade.label,
            ),
        ):
            fonte = self._fonte_prioridade(item)
            fontes_relacionadas = self._fontes_relacionadas(
                origem=fonte,
                diagnostico_index=diagnostico_index,
                recomendacoes_index=recomendacoes_index,
            )
            chave = self._plano_chave_plano(fonte.codigo, fonte.scope, fonte.entidade_id)
            if chave in usados:
                continue
            usados.add(chave)
            itens.append(
                self._montar_item(
                    chave=chave,
                    fonte=fonte,
                    fontes_relacionadas=fontes_relacionadas,
                    impacto_estimado=item.impacto_estimado or severidade_base(item.severidade),
                    titulo=item.origem_titulo,
                    resumo=item.contexto_operacional,
                    motivo=item.contexto_economico,
                    acao_sugerida=item.acao_sugerida,
                    safra_id=safra_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    production_unit_id=production_unit_id,
                )
            )

        for item in sorted(
            diagnostico,
            key=lambda diagnostico_item: (
                severidade_ordem(diagnostico_item.severidade),
                diagnostico_item.codigo,
                diagnostico_item.label,
            ),
        ):
            chave = self._plano_chave_plano(item.codigo, item.scope, item.id)
            if chave in usados:
                continue
            usados.add(chave)
            fonte = self._fonte_diagnostico(item)
            itens.append(
                self._montar_item(
                    chave=chave,
                    fonte=fonte,
                    fontes_relacionadas=[],
                    impacto_estimado=severidade_base(item.severidade),
                    titulo=item.titulo,
                    resumo=item.mensagem,
                    motivo=item.sugestao or item.mensagem,
                    acao_sugerida=item.sugestao or self._acao_padrao(item.severidade),
                    safra_id=safra_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    production_unit_id=production_unit_id,
                )
            )

        for item in sorted(
            recomendacoes,
            key=lambda rec: (
                severidade_ordem(rec.severidade),
                rec.tipo,
                rec.label,
            ),
        ):
            chave = self._plano_chave_plano(item.origem_diagnostica_codigo, item.scope, item.entidade_id)
            if chave in usados:
                continue
            usados.add(chave)
            fonte = self._fonte_recomendacao(item)
            itens.append(
                self._montar_item(
                    chave=chave,
                    fonte=fonte,
                    fontes_relacionadas=[],
                    impacto_estimado=severidade_base(item.severidade),
                    titulo=item.explicacao_objetiva,
                    resumo=item.contexto_operacional,
                    motivo=item.contexto_economico,
                    acao_sugerida=item.acao_sugerida,
                    safra_id=safra_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    production_unit_id=production_unit_id,
                )
            )

        for index, item in enumerate(sorted(itens, key=lambda plano: (severidade_ordem(plano.severidade), plano.entidade_tipo, plano.entidade_label, plano.titulo)), start=1):
            item.posicao = index

        return itens

    def _montar_item(
        self,
        *,
        chave: str,
        fonte: PlanoAcaoOperacionalAgricolaFonte,
        fontes_relacionadas: list[PlanoAcaoOperacionalAgricolaFonte],
        impacto_estimado: float,
        titulo: str,
        resumo: str,
        motivo: str,
        acao_sugerida: str,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
    ) -> PlanoAcaoOperacionalAgricolaItem:
        severidade = normalizar_severidade(fonte.severidade)
        acoes = [acao_sugerida.strip()] if acao_sugerida.strip() else []
        if not acoes:
            acoes = self._acoes_padrao(severidade)
        fontes_unificadas = [fonte, *fontes_relacionadas]
        return PlanoAcaoOperacionalAgricolaItem(
            id=uuid5(NAMESPACE_URL, f"agrosaas:agricola:inteligencia-operacional:{self.tenant_id}:{chave}"),
            chave=chave,
            scope=fonte.scope,
            titulo=titulo,
            resumo=resumo,
            motivo=motivo,
            severidade=severidade,
            impacto_estimado=float(impacto_estimado),
            acoes_sugeridas=self._dedupe_strings(acoes),
            prazo_sugerido=self._prazo_sugerido(severidade),
            contexto_operacional=resumo,
            origem_primaria=fonte,
            fontes_analiticas=self._dedupe_fontes(fontes_unificadas),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            entidade_tipo=fonte.entidade_tipo,
            entidade_id=fonte.entidade_id,
            entidade_label=fonte.entidade_label,
        )

    def _fonte_prioridade(self, item) -> PlanoAcaoOperacionalAgricolaFonte:
        return PlanoAcaoOperacionalAgricolaFonte(
            origem_analitica="PRIORIDADE",
            codigo=item.origem_codigo,
            titulo=item.origem_titulo,
            severidade=normalizar_severidade(item.severidade),
            scope=item.scope,
            entidade_tipo=item.entidade_tipo,
            entidade_id=item.entidade_id,
            entidade_label=item.entidade_label,
        )

    def _fonte_diagnostico(self, item) -> PlanoAcaoOperacionalAgricolaFonte:
        scope = self._normalizar_scope(item.scope)
        return PlanoAcaoOperacionalAgricolaFonte(
            origem_analitica="DIAGNOSTICO",
            codigo=item.codigo,
            titulo=item.titulo,
            severidade=normalizar_severidade(item.severidade),
            scope=scope,
            entidade_tipo="SAFRA" if scope == "SAFRA" else scope,  # type: ignore[arg-type]
            entidade_id=item.id,
            entidade_label=item.label,
        )

    def _fonte_recomendacao(self, item) -> PlanoAcaoOperacionalAgricolaFonte:
        return PlanoAcaoOperacionalAgricolaFonte(
            origem_analitica="RECOMENDACAO",
            codigo=item.origem_diagnostica_codigo,
            titulo=item.origem_diagnostica_titulo,
            severidade=normalizar_severidade(item.severidade),
            scope=item.scope,
            entidade_tipo=item.entidade_tipo,
            entidade_id=item.entidade_id,
            entidade_label=item.entidade_label,
        )

    def _fontes_relacionadas(
        self,
        *,
        origem: PlanoAcaoOperacionalAgricolaFonte,
        diagnostico_index: dict[str, object],
        recomendacoes_index: dict[str, object],
    ) -> list[PlanoAcaoOperacionalAgricolaFonte]:
        fontes: list[PlanoAcaoOperacionalAgricolaFonte] = []
        fonte_diagnostico = diagnostico_index.get(self._plano_chave_fonte("DIAGNOSTICO", origem.codigo, origem.scope, origem.entidade_id))
        if fonte_diagnostico is not None:
            fontes.append(self._fonte_diagnostico(fonte_diagnostico))
        fonte_recomendacao = recomendacoes_index.get(self._plano_chave_fonte("RECOMENDACAO", origem.codigo, origem.scope, origem.entidade_id))
        if fonte_recomendacao is not None:
            fontes.append(self._fonte_recomendacao(fonte_recomendacao))
        return fontes

    @staticmethod
    def _plano_chave_fonte(origem_analitica: str, codigo: str, scope: str, entidade_id: str) -> str:
        return f"{origem_analitica}:{codigo}:{InteligenciaOperacionalAgricolaV1Service._normalizar_scope(scope)}:{entidade_id}"

    @staticmethod
    def _plano_chave_plano(codigo: str, scope: str, entidade_id: str) -> str:
        return f"{codigo}:{InteligenciaOperacionalAgricolaV1Service._normalizar_scope(scope)}:{entidade_id}"

    @staticmethod
    def _normalizar_scope(scope: str) -> str:
        return scope if scope in {"SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY"} else "SAFRA"

    @staticmethod
    def _prazo_sugerido(severidade: str) -> str:
        severidade = normalizar_severidade(severidade)
        if severidade == "PRIORIDADE_CRITICA":
            return "Imediato"
        if severidade == "RISCO_ECONOMICO":
            return "Até 48h"
        if severidade == "RISCO_OPERACIONAL":
            return "Até 7 dias"
        if severidade == "ATENCAO":
            return "Até 15 dias"
        return "Quando houver janela operacional"

    @staticmethod
    def _acoes_padrao(severidade: str) -> list[str]:
        severidade = normalizar_severidade(severidade)
        if severidade == "PRIORIDADE_CRITICA":
            return ["Tratar imediatamente e validar a reconciliação oficial."]
        if severidade == "RISCO_ECONOMICO":
            return ["Revisar origem econômica, custos alocados e reconciliação."]
        if severidade == "RISCO_OPERACIONAL":
            return ["Rever execução, produtividade e evidências operacionais."]
        if severidade == "ATENCAO":
            return ["Monitorar o recorte e validar o próximo ciclo operacional."]
        return ["Acompanhar sem ação corretiva imediata."]

    @staticmethod
    def _dedupe_strings(items: list[str]) -> list[str]:
        seen: set[str] = set()
        resultado: list[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            resultado.append(normalized)
        return resultado

    @staticmethod
    def _dedupe_fontes(items: list[PlanoAcaoOperacionalAgricolaFonte]) -> list[PlanoAcaoOperacionalAgricolaFonte]:
        seen: set[tuple[str, str, str, str]] = set()
        resultado: list[PlanoAcaoOperacionalAgricolaFonte] = []
        for item in items:
            chave = (item.origem_analitica, item.codigo, item.scope, item.entidade_id)
            if chave in seen:
                continue
            seen.add(chave)
            resultado.append(item)
        return resultado

    @staticmethod
    def _dedupe_warnings(warnings) -> list:
        vistos: set[tuple[str, str]] = set()
        resultado = []
        for warning in warnings or []:
            chave = (warning.codigo, normalizar_severidade(warning.severidade))
            if chave in vistos:
                continue
            vistos.add(chave)
            resultado.append(warning)
        return resultado

    def _resumo(self, items: list[PlanoAcaoOperacionalAgricolaItem]) -> PlanoAcaoOperacionalAgricolaResumo:
        severidades = Counter(item.severidade for item in items)
        origens = Counter(item.origem_primaria.origem_analitica for item in items)
        entidades = Counter(item.entidade_tipo for item in items)
        prazos = Counter(item.prazo_sugerido for item in items)
        return PlanoAcaoOperacionalAgricolaResumo(
            total=len(items),
            info=severidades.get("INFO", 0),
            atencao=severidades.get("ATENCAO", 0),
            risco_operacional=severidades.get("RISCO_OPERACIONAL", 0),
            risco_economico=severidades.get("RISCO_ECONOMICO", 0),
            prioridade_critica=severidades.get("PRIORIDADE_CRITICA", 0),
            por_origem=dict(sorted(origens.items())),
            por_entidade_tipo=dict(sorted(entidades.items())),
            por_prazo=dict(sorted(prazos.items())),
        )

    @staticmethod
    def criticidade_para_tarefa(severidade: str) -> str:
        return "CRITICA" if normalizar_severidade(severidade) == "PRIORIDADE_CRITICA" else "NORMAL"

    def montar_obs_conversion(
        self,
        *,
        plano: PlanoAcaoOperacionalAgricolaItem,
        titulo: str,
        descricao: str,
        tipo: str,
        prioridade: str,
        data_prevista: date | None,
        aprovado_explicitamente: bool,
        user_id: UUID | None,
    ) -> str:
        fontes = ", ".join(
            f"{fonte.origem_analitica}:{fonte.codigo}"
            for fonte in plano.fontes_analiticas
        ) or "—"
        acoes = " | ".join(plano.acoes_sugeridas) or "—"
        prazo = data_prevista.isoformat() if data_prevista else "Não informado"
        aprovador = str(user_id) if user_id else "—"
        return "\n".join(
            [
                "Plano assistido convertido em tarefa real.",
                f"Plano ID: {plano.id}",
                f"Plano chave: {plano.chave}",
                f"Origem primária: {plano.origem_primaria.origem_analitica}:{plano.origem_primaria.codigo}",
                f"Severidade canônica: {plano.severidade}",
                f"Contexto operacional original: {plano.contexto_operacional}",
                f"Título aprovado: {titulo.strip()}",
                f"Descrição detalhada: {descricao.strip()}",
                f"Tipo selecionado: {tipo}",
                f"Prioridade selecionada: {prioridade}",
                f"Prazo previsto: {prazo}",
                f"Aprovação humana explícita: {'SIM' if aprovado_explicitamente else 'NÃO'}",
                f"Aprovado por: {aprovador}",
                f"Fontes analíticas: {fontes}",
                f"Ações sugeridas: {acoes}",
            ]
        )
