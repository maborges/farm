from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from certificacoes_esg.models import (
    ChecklistCertificacao,
    NaoConformidadeCertificacao,
    PlanoAcaoCertificacao,
    ProgramaCertificacao,
    StatusChecklistCertificacao,
    StatusNaoConformidade,
    StatusPlanoAcao,
    StatusProgramaCertificacao,
)

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class ESGRecommendationProvider(RecommendationProvider):
    provider_name = "esg"
    domains = ("SYSTEM",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        payload = context.payload or {}
        dias_alerta = int(payload.get("dias_alerta_vencimento", 30))
        programas = await self._listar_programas(context.tenant_id, payload)
        checklists = await self._listar_checklists(context.tenant_id, payload)
        nao_conformidades = await self._listar_nao_conformidades(context.tenant_id, payload)
        planos_acao = await self._listar_planos_acao(context.tenant_id, payload)

        candidates: list[RecommendationCandidate] = []
        hoje = date.today()
        agora = datetime.now(timezone.utc)

        for programa in programas:
            if programa.data_fim is not None:
                dias_restantes = (programa.data_fim - hoje).days
                if dias_restantes < 0:
                    candidates.append(
                        self._candidate(
                            context,
                            scope_type="PROGRAMA",
                            scope_id=str(programa.id),
                            rule_code="ESG_CERTIFICACAO_VENCIDA",
                            title="Certificação vencida",
                            summary=f"A certificação {programa.nome} está vencida.",
                            rationale="Certificações vencidas exigem correção imediata para preservar conformidade.",
                            priority=RecommendationPriority.URGENT,
                            confidence=Decimal("0.98"),
                            action_label="Abrir programa",
                            action_target=build_route_target("/dashboard/compliance/esg", programa.id),
                            source_type=RecommendationSourceType.INDICATOR,
                            source_signal_ids=signal_ids,
                            context_data={
                                "programa_id": str(programa.id),
                                "nome": programa.nome,
                                "status_programa": programa.status_programa,
                                "data_fim": programa.data_fim.isoformat(),
                            },
                        )
                    )
                elif dias_restantes <= dias_alerta:
                    candidates.append(
                        self._candidate(
                            context,
                            scope_type="PROGRAMA",
                            scope_id=str(programa.id),
                            rule_code="ESG_CERTIFICACAO_VENCENDO",
                            title="Certificação vencendo",
                            summary=f"A certificação {programa.nome} vence em {dias_restantes} dia(s).",
                            rationale="A janela de vencimento pede revisão preventiva para evitar ruptura de conformidade.",
                            priority=RecommendationPriority.HIGH,
                            confidence=Decimal("0.94"),
                            action_label="Revisar programa",
                            action_target=build_route_target("/dashboard/compliance/esg", programa.id),
                            source_type=RecommendationSourceType.INDICATOR,
                            source_signal_ids=signal_ids,
                            context_data={
                                "programa_id": str(programa.id),
                                "nome": programa.nome,
                                "data_fim": programa.data_fim.isoformat(),
                                "dias_restantes": dias_restantes,
                            },
                        )
                    )

        for checklist in checklists:
            percentual = float(checklist.percentual_conformidade or 0)
            if checklist.status_checklist != StatusChecklistCertificacao.PUBLICADO or percentual < 80.0:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="CHECKLIST",
                        scope_id=str(checklist.id),
                        rule_code="ESG_CHECKLIST_INCOMPLETO",
                        title="Checklist de certificação incompleto",
                        summary=f"O checklist {checklist.nome} ainda não atingiu maturidade suficiente.",
                        rationale="Checklists incompletos sinalizam lacunas operacionais e atraso de conformidade.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.83"),
                        action_label="Abrir checklist",
                        action_target=build_route_target("/dashboard/compliance/esg", checklist.id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "checklist_id": str(checklist.id),
                            "programa_id": str(checklist.programa_certificacao_id),
                            "status_checklist": checklist.status_checklist,
                            "percentual_conformidade": percentual,
                        },
                    )
                )

        for nc in nao_conformidades:
            if nc.status in {StatusNaoConformidade.ABERTA, StatusNaoConformidade.EM_ANALISE, StatusNaoConformidade.EM_CORRECAO}:
                prazo_vencido = nc.prazo_correcao is not None and nc.prazo_correcao < agora
                priority = RecommendationPriority.URGENT if prazo_vencido or nc.severidade == "CRITICA" else RecommendationPriority.HIGH
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="NAO_CONFORMIDADE",
                        scope_id=str(nc.id),
                        rule_code="ESG_NAO_CONFORMIDADE_ABERTA",
                        title="Não conformidade aberta",
                        summary=f"A não conformidade {nc.titulo} permanece em aberto.",
                        rationale="Não conformidades abertas precisam de acompanhamento para evitar escalada de risco.",
                        priority=priority,
                        confidence=Decimal("0.96"),
                        action_label="Abrir não conformidade",
                        action_target=build_route_target("/dashboard/compliance/esg", nc.id),
                        source_type=RecommendationSourceType.EVENT,
                        source_signal_ids=signal_ids,
                        context_data={
                            "nao_conformidade_id": str(nc.id),
                            "programa_id": str(nc.programa_id),
                            "status": nc.status,
                            "severidade": nc.severidade,
                            "prazo_correcao": nc.prazo_correcao.isoformat() if nc.prazo_correcao else None,
                        },
                    )
                )

        for plano in planos_acao:
            if plano.status != StatusPlanoAcao.CONCLUIDO and plano.prazo < agora:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="PLANO_ACAO",
                        scope_id=str(plano.id),
                        rule_code="ESG_PLANO_ACAO_ATRASADO",
                        title="Plano de ação atrasado",
                        summary=f"O plano de ação {plano.titulo} está atrasado.",
                        rationale="Planos atrasados reduzem a capacidade de resposta em auditorias e certificações.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.95"),
                        action_label="Abrir plano",
                        action_target=build_route_target("/dashboard/compliance/esg", plano.id),
                        source_type=RecommendationSourceType.EVENT,
                        source_signal_ids=signal_ids,
                        context_data={
                            "plano_acao_id": str(plano.id),
                            "programa_id": str(plano.programa_id),
                            "status": plano.status,
                            "prazo": plano.prazo.isoformat(),
                        },
                    )
                )

        return candidates

    async def _listar_programas(self, tenant_id: UUID, payload: dict[str, object]) -> list[ProgramaCertificacao]:
        stmt = select(ProgramaCertificacao).where(ProgramaCertificacao.tenant_id == tenant_id)
        stmt = self._apply_programa_filters(stmt, payload)
        stmt = stmt.where(
            ProgramaCertificacao.status_programa.in_(
                (StatusProgramaCertificacao.ATIVO, StatusProgramaCertificacao.SUSPENSO)
            )
        )
        stmt = stmt.order_by(ProgramaCertificacao.data_fim.asc().nullslast(), ProgramaCertificacao.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_checklists(self, tenant_id: UUID, payload: dict[str, object]) -> list[ChecklistCertificacao]:
        stmt = select(ChecklistCertificacao).where(ChecklistCertificacao.tenant_id == tenant_id)
        stmt = self._apply_checklist_filters(stmt, payload)
        stmt = stmt.order_by(ChecklistCertificacao.percentual_conformidade.asc(), ChecklistCertificacao.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_nao_conformidades(self, tenant_id: UUID, payload: dict[str, object]) -> list[NaoConformidadeCertificacao]:
        stmt = select(NaoConformidadeCertificacao).where(NaoConformidadeCertificacao.tenant_id == tenant_id)
        stmt = self._apply_domestic_filters(stmt, NaoConformidadeCertificacao, payload)
        stmt = stmt.order_by(NaoConformidadeCertificacao.detectada_em.desc(), NaoConformidadeCertificacao.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_planos_acao(self, tenant_id: UUID, payload: dict[str, object]) -> list[PlanoAcaoCertificacao]:
        stmt = select(PlanoAcaoCertificacao).where(PlanoAcaoCertificacao.tenant_id == tenant_id)
        stmt = self._apply_domestic_filters(stmt, PlanoAcaoCertificacao, payload)
        stmt = stmt.order_by(PlanoAcaoCertificacao.prazo.asc(), PlanoAcaoCertificacao.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    def _apply_programa_filters(self, stmt, payload: dict[str, object]):
        return self._apply_uuid_filters(
            stmt,
            ProgramaCertificacao,
            payload,
            {
                "programa_id": "id",
                "propriedade_id": "propriedade_id",
                "imovel_rural_id": "imovel_rural_id",
                "propriedade_imovel_id": "propriedade_imovel_id",
            },
        )

    def _apply_checklist_filters(self, stmt, payload: dict[str, object]):
        return self._apply_uuid_filters(
            stmt,
            ChecklistCertificacao,
            payload,
            {
                "programa_id": "programa_certificacao_id",
                "propriedade_id": "propriedade_id",
                "imovel_rural_id": "imovel_rural_id",
                "propriedade_imovel_id": "propriedade_imovel_id",
            },
        )

    def _apply_domestic_filters(self, stmt, model, payload: dict[str, object]):
        return self._apply_uuid_filters(
            stmt,
            model,
            payload,
            {
                "programa_id": "programa_id",
                "propriedade_id": "propriedade_id",
                "imovel_rural_id": "imovel_rural_id",
                "propriedade_imovel_id": "propriedade_imovel_id",
            },
        )

    def _apply_uuid_filters(self, stmt, model, payload: dict[str, object], mapping: dict[str, str]):
        for payload_key, column_name in mapping.items():
            value = payload.get(payload_key)
            if value is None:
                continue
            try:
                stmt = stmt.where(getattr(model, column_name) == UUID(str(value)))
            except (TypeError, ValueError, AttributeError):
                continue
        return stmt

    def _candidate(
        self,
        context: OperationalContext,
        *,
        scope_type: str,
        scope_id: str,
        rule_code: str,
        title: str,
        summary: str,
        rationale: str,
        priority: RecommendationPriority,
        confidence: Decimal,
        action_label: str,
        action_target: str,
        source_type: RecommendationSourceType,
        source_signal_ids: list[UUID],
        context_data: dict[str, object],
    ) -> RecommendationCandidate:
        return RecommendationCandidate(
            tenant_id=context.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            domain=RecommendationDomain.SYSTEM,
            priority=priority,
            source_type=source_type,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name=self.provider_name,
            rule_code=rule_code,
            scope_type=scope_type,
            scope_id=scope_id,
            title=title,
            summary=summary,
            rationale=rationale,
            dedupe_key=stable_dedupe_key(
                self.provider_name,
                context.tenant_id,
                scope_id,
                rule_code,
                context.unidade_produtiva_id,
            ),
            source_signal_ids=source_signal_ids,
            confidence=confidence,
            action_label=action_label,
            action_target=action_target,
            context=build_candidate_context(context, context_data),
        )
