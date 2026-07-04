from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.safras.models import Safra
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.receita import Receita
from financeiro.services.dashboard_service import DashboardService
from financeiro.services.lancamento_service import LancamentoService

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


class FinanceiroRecommendationProvider(RecommendationProvider):
    provider_name = "financeiro"
    domains = ("FINANCE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = [signal.signal_id for signal in signals if signal.tenant_id == context.tenant_id]
        dashboard = await DashboardService(self.session, context.tenant_id).resumo(context.unidade_produtiva_id)
        candidatos: list[RecommendationCandidate] = []

        if dashboard.saldo_mes < 0:
            candidatos.append(
                self._candidate(
                    context,
                    rule_code="FIN_FLUXO_CAIXA_CRITICO",
                    title="Fluxo de caixa crítico",
                    summary=f"Saldo do mês negativo em R$ {abs(dashboard.saldo_mes):,.2f}.",
                    rationale="O caixa já está pressionado e precisa de revisão de entradas e saídas no curto prazo.",
                    priority=RecommendationPriority.URGENT,
                    confidence=Decimal("0.96"),
                    action_label="Revisar caixa",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "saldo_mes": dashboard.saldo_mes,
                        "total_recebido_mes": dashboard.total_recebido_mes,
                        "total_pago_mes": dashboard.total_pago_mes,
                    },
                )
            )

        total_vencido = dashboard.total_atrasado_despesas + dashboard.total_atrasado_receitas
        if total_vencido > 0:
            candidatos.append(
                self._candidate(
                    context,
                    rule_code="FIN_CONTAS_VENCIDAS",
                    title="Contas vencidas exigem revisão",
                    summary=f"Há R$ {total_vencido:,.2f} em contas vencidas no recorte atual.",
                    rationale="Contas vencidas elevam risco de perda de caixa e travam a operação de curto prazo.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.94"),
                    action_label="Rever vencidos",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "total_atrasado_despesas": dashboard.total_atrasado_despesas,
                        "total_atrasado_receitas": dashboard.total_atrasado_receitas,
                    },
                )
            )

        vencimentos_proximos = sum(item.valor for item in dashboard.vencendo_7d if item.tipo == "DESPESA")
        if vencimentos_proximos > 0:
            candidatos.append(
                self._candidate(
                    context,
                    rule_code="FIN_CONTAS_A_VENCER",
                    title="Contas a pagar vencendo em breve",
                    summary=f"R$ {vencimentos_proximos:,.2f} vencem nos próximos 7 dias.",
                    rationale="É melhor antecipar a análise de liquidez do que reagir depois do vencimento.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.90"),
                    action_label="Planejar pagamento",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "janela_dias": 7,
                        "valor_vencendo": vencimentos_proximos,
                    },
                )
            )

        if dashboard.top_despesas:
            top_total = sum(item.total for item in dashboard.top_despesas)
            total_despesas = dashboard.total_pago_mes or dashboard.total_a_pagar or 0.0
            concentracao = (top_total / total_despesas * 100) if total_despesas > 0 else 0.0
            if concentracao >= 45:
                candidatos.append(
                    self._candidate(
                        context,
                        rule_code="FIN_CONCENTRACAO_DESPESA",
                        title="Concentração de despesa elevada",
                        summary="Poucas categorias concentram grande parte da despesa do período.",
                        rationale="Quando a despesa concentra demais em poucos centros, a negociação e o corte de custo ficam mais urgentes.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.82"),
                        action_label="Abrir análise",
                        action_target=self._target(context.unidade_produtiva_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "concentracao_pct": round(concentracao, 2),
                            "top_categorias": [item.model_dump() for item in dashboard.top_despesas[:3]],
                        },
                    )
                )

        safra_id = self._resolve_safra_id(context)
        if safra_id is not None:
            dre = await LancamentoService(self.session, context.tenant_id).gerar_dre(safra_id)
            if dre.margem_percentual < 10:
                candidatos.append(
                    self._candidate(
                        context,
                        rule_code="FIN_MARGEM_APERTADA",
                        title="Margem financeira apertada",
                        summary=f"Margem operacional atual em {dre.margem_percentual:.1f}%.",
                        rationale="A margem abaixo do limite canônico exige revisão financeira imediata.",
                        priority=RecommendationPriority.HIGH if dre.margem_percentual >= 0 else RecommendationPriority.URGENT,
                        confidence=Decimal("0.93"),
                        action_label="Revisar DRE",
                        action_target=self._target(context.unidade_produtiva_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "safra_id": str(safra_id),
                            "receita_bruta": dre.receita_bruta,
                            "custos_operacionais": dre.custos_operacionais,
                            "resultado_operacional": dre.resultado_operacional,
                            "margem_percentual": dre.margem_percentual,
                        },
                    )
                )

            orcamento_gap = await self._budget_gap(context.tenant_id, safra_id)
            if orcamento_gap is not None:
                candidatos.append(
                    self._candidate(
                        context,
                        rule_code="FIN_ORCAMENTO_EXCEDIDO",
                        title="Orçamento comprometido",
                        summary=f"O custo comprometido já excede o orçamento em {orcamento_gap['desvio_pct']:.1f}%.",
                        rationale="O orçamento previsto da safra já foi ultrapassado e precisa de revisão do plano de gasto.",
                        priority=RecommendationPriority.URGENT,
                        confidence=Decimal("0.91"),
                        action_label="Revisar orçamento",
                        action_target=self._target(context.unidade_produtiva_id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data=orcamento_gap,
                    )
                )

        return candidatos

    def _resolve_safra_id(self, context: OperationalContext) -> UUID | None:
        if context.payload and context.payload.get("safra_id"):
            try:
                return UUID(str(context.payload["safra_id"]))
            except (TypeError, ValueError):
                return None
        try:
            return UUID(str(context.scope_id))
        except (TypeError, ValueError):
            return None

    async def _budget_gap(self, tenant_id: UUID, safra_id: UUID) -> dict[str, object] | None:
        stmt_budget = select(func.coalesce(func.sum(ItemOrcamentoSafra.custo_total), 0)).where(
            ItemOrcamentoSafra.tenant_id == tenant_id,
            ItemOrcamentoSafra.safra_id == safra_id,
        )
        budget_total = float((await self.session.execute(stmt_budget)).scalar_one() or 0.0)
        if budget_total <= 0:
            return None

        despesas_comprometidas = await self._soma_lancamentos_comprometidos(tenant_id, safra_id)
        if despesas_comprometidas <= budget_total * 1.1:
            return None
        return {
            "fonte": "agricola_orcamento_itens",
            "orcamento_previsto_total": round(budget_total, 2),
            "despesas_comprometidas_total": round(despesas_comprometidas, 2),
            "desvio_pct": round(((despesas_comprometidas - budget_total) / budget_total) * 100, 2),
        }

    async def _soma_lancamentos_comprometidos(self, tenant_id: UUID, safra_id: UUID) -> float:
        stmt = select(
            func.coalesce(
                func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "CUSTO"),
                0,
            )
        ).where(
            LancamentoFinanceiro.tenant_id == tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
        )
        return float((await self.session.execute(stmt)).scalar_one() or 0.0)

    def _candidate(
        self,
        context: OperationalContext,
        *,
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
            domain=RecommendationDomain.FINANCE,
            priority=priority,
            source_type=source_type,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name=self.provider_name,
            rule_code=rule_code,
            scope_type=context.scope_type,
            scope_id=context.scope_id,
            title=title,
            summary=summary,
            rationale=rationale,
            dedupe_key=self._dedupe_key(context, rule_code),
            source_signal_ids=source_signal_ids,
            confidence=confidence,
            action_label=action_label,
            action_target=action_target,
            context={
                **context_data,
                "generated_at": context.generated_at.isoformat(),
            },
        )

    @staticmethod
    def _target(unidade_produtiva_id: UUID | None) -> str:
        if unidade_produtiva_id is None:
            return "/financeiro/dashboard"
        return f"/financeiro/dashboard?unidade_produtiva_id={unidade_produtiva_id}"

    @staticmethod
    def _dedupe_key(context: OperationalContext, rule_code: str) -> str:
        unidade = context.unidade_produtiva_id or "tenant"
        return f"financeiro:{context.tenant_id}:{unidade}:{rule_code}"
