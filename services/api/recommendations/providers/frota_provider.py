from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from operacional.services.frota_dashboard_service import FrotaDashboardService

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class FrotaRecommendationProvider(RecommendationProvider):
    provider_name = "frota"
    domains = ("OPERATIONS",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        dashboard = await self._obter_dashboard(context.unidade_produtiva_id)
        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        dias_sem_abastecimento = int(context.payload.get("dias_sem_abastecimento", 30)) if context.payload else 30
        dias_ociosidade = int(context.payload.get("dias_ociosidade", 14)) if context.payload else 14

        candidates: list[RecommendationCandidate] = []
        for item in dashboard.equipamentos:
            if item.manutencao_status == "VENCIDA":
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_MANUTENCAO_VENCIDA",
                        title="Manutenção preventiva vencida",
                        summary=f"O equipamento {item.nome} possui manutenção preventiva vencida.",
                        rationale="A manutenção vencida aumenta o risco de parada e de custo corretivo inesperado.",
                        priority=RecommendationPriority.URGENT,
                        confidence=Decimal("0.98"),
                        action_label="Abrir frota",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.INDICATOR,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "manutencao_status": item.manutencao_status,
                            "custo_total": item.custo_total,
                            "os_abertas": item.os_abertas,
                        },
                    )
                )
            elif item.manutencao_status == "PROXIMA":
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_MANUTENCAO_PROXIMA",
                        title="Manutenção preventiva próxima do vencimento",
                        summary=f"O equipamento {item.nome} entra na janela preventiva.",
                        rationale="A prevenção evita parada operacional e prolonga a vida útil do ativo.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.90"),
                        action_label="Programar manutenção",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.INDICATOR,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "manutencao_status": item.manutencao_status,
                            "os_abertas": item.os_abertas,
                        },
                    )
                )

            if item.os_abertas > 0:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_OS_PENDENTE",
                        title="Ordem de serviço pendente",
                        summary=f"O equipamento {item.nome} possui OS aberta ou em execução.",
                        rationale="OS pendentes reduzem previsibilidade da frota e podem esconder indisponibilidade operacional.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.87"),
                        action_label="Abrir OS",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.EVENT,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "os_abertas": item.os_abertas,
                            "riscos": list(item.riscos),
                        },
                    )
                )

            if item.dias_sem_abastecimento is not None and item.dias_sem_abastecimento >= dias_sem_abastecimento:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_SEM_ABASTECIMENTO_RECENTE",
                        title="Sem abastecimento recente",
                        summary=f"O equipamento {item.nome} está há {item.dias_sem_abastecimento} dias sem abastecimento.",
                        rationale="A falta de abastecimento recente pode indicar inatividade, baixa rastreabilidade ou lacuna operacional.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.81"),
                        action_label="Revisar uso",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "dias_sem_abastecimento": item.dias_sem_abastecimento,
                        },
                    )
                )

            if item.dias_sem_abastecimento is not None and item.dias_sem_abastecimento >= dias_ociosidade and not item.jornada_aberta:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_EQUIPAMENTO_OCIOSO",
                        title="Equipamento possivelmente ocioso",
                        summary=f"O equipamento {item.nome} não mostra jornada aberta recente.",
                        rationale="Baixa utilização por período prolongado pode indicar ociosidade ou problema de alocação.",
                        priority=RecommendationPriority.LOW,
                        confidence=Decimal("0.72"),
                        action_label="Reavaliar alocação",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "dias_sem_abastecimento": item.dias_sem_abastecimento,
                            "jornada_aberta": item.jornada_aberta,
                        },
                    )
                )

            if item.risco_total >= 3:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="EQUIPAMENTO",
                        scope_id=str(item.equipamento_id),
                        rule_code="FROTA_RISCO_CONSOLIDADO",
                        title="Risco operacional consolidado",
                        summary="O equipamento acumula fatores suficientes para revisão operacional.",
                        rationale="A combinação de fatores de risco exige atenção para evitar parada e custo adicional.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.78"),
                        action_label="Abrir análise",
                        action_target=build_route_target("/dashboard/operacional/frota", item.equipamento_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "equipamento_id": str(item.equipamento_id),
                            "equipamento_nome": item.nome,
                            "risco_total": item.risco_total,
                            "riscos": list(item.riscos),
                        },
                    )
                )

        return candidates

    async def _obter_dashboard(self, unidade_produtiva_id: UUID | None):
        return await FrotaDashboardService(self.session, self.tenant_id).obter_dashboard(
            unidade_produtiva_id=unidade_produtiva_id,
        )

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
            domain=RecommendationDomain.OPERATIONS,
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
