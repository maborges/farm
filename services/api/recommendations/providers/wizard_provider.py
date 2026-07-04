from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from wizard.models import ImplantacaoChecklistItem, ImplantacaoOperacional, ImplantacaoPendencia

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class WizardRecommendationProvider(RecommendationProvider):
    provider_name = "wizard"
    domains = ("SYSTEM",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        implantacoes = await self._listar_implantacoes(context.tenant_id, context.unidade_produtiva_id)
        candidates: list[RecommendationCandidate] = []

        for implantacao in implantacoes:
            checklist_pendentes = await self._contar_checklist_pendentes(implantacao.id)
            pendencias_criticas = await self._contar_pendencias_criticas(implantacao.id)

            if implantacao.unidade_produtiva_id is None:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="IMPLANTACAO",
                        scope_id=str(implantacao.id),
                        rule_code="WIZARD_UNIDADE_PRODUTIVA_AUSENTE",
                        title="Unidade produtiva ausente",
                        summary="A implantação ainda não possui Unidade Produtiva vinculada.",
                        rationale="A vinculação da unidade é necessária para consolidar o go-live e os módulos operacionais.",
                        priority=RecommendationPriority.URGENT,
                        confidence=Decimal("0.97"),
                        action_label="Vincular unidade",
                        action_target=build_route_target("/dashboard/wizard", implantacao.id),
                        source_type=RecommendationSourceType.SYSTEM,
                        source_signal_ids=signal_ids,
                        context_data={
                            "implantacao_id": str(implantacao.id),
                            "status": implantacao.status,
                            "etapa_atual": implantacao.etapa_atual,
                            "percentual_progresso": implantacao.percentual_progresso,
                        },
                    )
                )

            if implantacao.status not in {"COMPLETED", "CANCELLED"} and implantacao.percentual_progresso < 100:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="IMPLANTACAO",
                        scope_id=str(implantacao.id),
                        rule_code="WIZARD_ONBOARDING_INCOMPLETO",
                        title="Onboarding incompleto",
                        summary="A implantação ainda não atingiu o nível de conclusão esperado.",
                        rationale="O go-live depende da conclusão do onboarding e da organização dos módulos mínimos.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.90"),
                        action_label="Continuar implantação",
                        action_target=build_route_target("/dashboard/wizard", implantacao.id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "implantacao_id": str(implantacao.id),
                            "status": implantacao.status,
                            "etapa_atual": implantacao.etapa_atual,
                            "percentual_progresso": implantacao.percentual_progresso,
                            "checklist_minimo_percentual": implantacao.checklist_minimo_percentual,
                        },
                    )
                )

            if implantacao.status == "BLOCKED" or implantacao.bloqueio_critico_aberto or pendencias_criticas > 0:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="IMPLANTACAO",
                        scope_id=str(implantacao.id),
                        rule_code="WIZARD_PENDENCIA_CRITICA",
                        title="Pendência crítica de implantação",
                        summary="Há pendências críticas bloqueando a evolução da implantação.",
                        rationale="Pendências críticas devem ser resolvidas antes de liberar o go-live.",
                        priority=RecommendationPriority.URGENT,
                        confidence=Decimal("0.95"),
                        action_label="Abrir pendências",
                        action_target=build_route_target("/dashboard/wizard", implantacao.id),
                        source_type=RecommendationSourceType.EVENT,
                        source_signal_ids=signal_ids,
                        context_data={
                            "implantacao_id": str(implantacao.id),
                            "status": implantacao.status,
                            "bloqueio_critico_aberto": implantacao.bloqueio_critico_aberto,
                            "pendencias_criticas": pendencias_criticas,
                        },
                    )
                )

            if implantacao.status == "READY_FOR_GO_LIVE" and checklist_pendentes > 0:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="IMPLANTACAO",
                        scope_id=str(implantacao.id),
                        rule_code="WIZARD_GO_LIVE_BLOQUEADO",
                        title="Go-live pronto, mas checklist ainda pendente",
                        summary="A implantação ainda possui checklist pendente antes do go-live.",
                        rationale="Checklist pendente antes do go-live aumenta risco de suporte e reabertura de pendências.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.89"),
                        action_label="Revisar checklist",
                        action_target=build_route_target("/dashboard/wizard", implantacao.id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "implantacao_id": str(implantacao.id),
                            "status": implantacao.status,
                            "checklist_pendentes": checklist_pendentes,
                        },
                    )
                )

        return candidates

    async def _listar_implantacoes(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[ImplantacaoOperacional]:
        stmt = select(ImplantacaoOperacional).where(ImplantacaoOperacional.tenant_id == tenant_id)
        if unidade_produtiva_id is not None:
            stmt = stmt.where(ImplantacaoOperacional.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.where(ImplantacaoOperacional.status.notin_(("COMPLETED", "CANCELLED")))
        stmt = stmt.order_by(ImplantacaoOperacional.updated_at.desc(), ImplantacaoOperacional.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _contar_checklist_pendentes(self, implantacao_id: UUID) -> int:
        stmt = select(func.count(ImplantacaoChecklistItem.id)).where(
            ImplantacaoChecklistItem.implantacao_id == implantacao_id,
            ImplantacaoChecklistItem.status == "PENDENTE",
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_pendencias_criticas(self, implantacao_id: UUID) -> int:
        stmt = select(func.count(ImplantacaoPendencia.id)).where(
            ImplantacaoPendencia.implantacao_id == implantacao_id,
            ImplantacaoPendencia.status == "ABERTA",
            ImplantacaoPendencia.severidade == "CRITICA",
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

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
