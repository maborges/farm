from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from operacional.models.estoque import Deposito, EstoqueMovimento, LoteEstoque, RequisicaoMaterial
from operacional.schemas.estoque import SaldoResponse
from operacional.services.estoque_service import EstoqueService

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class EstoqueRecommendationProvider(RecommendationProvider):
    provider_name = "estoque"
    domains = ("OPERATIONS",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        payload = context.payload or {}
        dias_vencimento = int(payload.get("dias_vencimento", 30))
        janela_consumo_dias = int(payload.get("janela_consumo_dias", 30))

        saldos = await self._listar_saldos(context.unidade_produtiva_id)
        lotes_vencendo = await self._listar_lotes_vencendo(context.unidade_produtiva_id, dias_vencimento)
        requisicoes_pendentes = await self._listar_requisicoes_pendentes(context.unidade_produtiva_id)
        consumo_recente = await self._consumo_recente_por_produto(context.unidade_produtiva_id, janela_consumo_dias)

        candidates: list[RecommendationCandidate] = []

        for saldo in saldos:
            if saldo.abaixo_minimo:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="SALDO",
                        scope_id=str(saldo.id),
                        rule_code="EST_SALDO_ABAIXO_MINIMO",
                        title="Estoque abaixo do mínimo",
                        summary=(
                            f"O item {saldo.produto_nome} no depósito {saldo.deposito_nome} está abaixo do mínimo."
                        ),
                        rationale="O saldo crítico reduz a capacidade de atender consumo e requisições sem ruptura.",
                        priority=RecommendationPriority.HIGH,
                        confidence=Decimal("0.96"),
                        action_label="Repor estoque",
                        action_target=build_route_target("/dashboard/operacional/estoque", saldo.id),
                        source_type=RecommendationSourceType.INDICATOR,
                        source_signal_ids=signal_ids,
                        context_data={
                            "saldo_id": str(saldo.id),
                            "produto_id": str(saldo.produto_id),
                            "produto_nome": saldo.produto_nome,
                            "deposito_id": str(saldo.deposito_id),
                            "deposito_nome": saldo.deposito_nome,
                            "quantidade_disponivel": saldo.quantidade_disponivel,
                            "estoque_minimo": saldo.estoque_minimo,
                        },
                    )
                )

            if saldo.quantidade_reservada > saldo.quantidade_disponivel:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="SALDO",
                        scope_id=str(saldo.id),
                        rule_code="EST_RESERVA_SUPERA_DISPONIVEL",
                        title="Reserva acima do disponível",
                        summary=(
                            f"O item {saldo.produto_nome} tem reservas comprometendo o saldo disponível."
                        ),
                        rationale="Quando a reserva supera a disponibilidade, a operação fica exposta a ruptura imediata.",
                        priority=RecommendationPriority.URGENT,
                        confidence=Decimal("0.94"),
                        action_label="Revisar reserva",
                        action_target=build_route_target("/dashboard/operacional/estoque", saldo.id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "saldo_id": str(saldo.id),
                            "produto_id": str(saldo.produto_id),
                            "quantidade_atual": saldo.quantidade_atual,
                            "quantidade_reservada": saldo.quantidade_reservada,
                            "quantidade_disponivel": saldo.quantidade_disponivel,
                        },
                    )
                )

            consumo_30d = consumo_recente.get(saldo.produto_id, 0.0)
            if consumo_30d > 0 and consumo_30d >= max(float(saldo.quantidade_disponivel), 1.0):
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="PRODUTO",
                        scope_id=str(saldo.produto_id),
                        rule_code="EST_CONSUMO_RECENTE_ALTO",
                        title="Consumo recente acima do saldo",
                        summary=(
                            f"O item {saldo.produto_nome} teve consumo recente de {consumo_30d:.2f}."
                        ),
                        rationale="O consumo recente está pressionando o saldo e merece replanejamento de reposição.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.82"),
                        action_label="Rever consumo",
                        action_target=build_route_target("/dashboard/operacional/estoque", saldo.id),
                        source_type=RecommendationSourceType.ANALYTICS,
                        source_signal_ids=signal_ids,
                        context_data={
                            "produto_id": str(saldo.produto_id),
                            "produto_nome": saldo.produto_nome,
                            "consumo_30d": round(consumo_30d, 4),
                            "janela_dias": janela_consumo_dias,
                            "quantidade_disponivel": saldo.quantidade_disponivel,
                        },
                    )
                )

        for lote in lotes_vencendo:
            candidates.append(
                self._candidate(
                    context,
                    scope_type="LOTE",
                    scope_id=str(lote.id),
                    rule_code="EST_LOTE_VENCENDO",
                    title="Lote de estoque vencendo",
                    summary=(
                        f"O lote {lote.numero_lote} do produto {lote.produto_id} vence em breve."
                    ),
                    rationale="Lotes próximos do vencimento precisam de priorização para evitar perdas.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.91"),
                    action_label="Revisar lote",
                    action_target=build_route_target("/dashboard/operacional/estoque", lote.id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "lote_id": str(lote.id),
                        "produto_id": str(lote.produto_id),
                        "numero_lote": lote.numero_lote,
                        "data_validade": lote.data_validade.isoformat() if lote.data_validade else None,
                        "quantidade_atual": lote.quantidade_atual,
                    },
                )
            )

        for requisicao in requisicoes_pendentes:
            candidates.append(
                self._candidate(
                    context,
                    scope_type="REQUISICAO",
                    scope_id=str(requisicao.id),
                    rule_code="EST_REQUISICAO_PENDENTE",
                    title="Requisição de material pendente",
                    summary="Há requisições pendentes de atendimento para o estoque.",
                    rationale="Pendências de requisição indicam necessidade de reposição, separação ou aprovação operacional.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.80"),
                    action_label="Abrir requisição",
                    action_target=build_route_target("/dashboard/operacional/estoque", requisicao.id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "requisicao_id": str(requisicao.id),
                        "status": requisicao.status,
                        "origem_tipo": requisicao.origem_tipo,
                        "data_necessidade": requisicao.data_necessidade.isoformat() if requisicao.data_necessidade else None,
                    },
                )
            )

        return candidates

    async def _listar_saldos(self, unidade_produtiva_id: UUID | None) -> list[SaldoResponse]:
        return await EstoqueService(self.session, self.tenant_id).listar_saldos(
            unidade_produtiva_id=unidade_produtiva_id,
        )

    async def _listar_lotes_vencendo(
        self,
        unidade_produtiva_id: UUID | None,
        dias_vencimento: int,
    ) -> list[LoteEstoque]:
        limite = date.today() + timedelta(days=dias_vencimento)
        stmt = (
            select(LoteEstoque)
            .join(Deposito, Deposito.id == LoteEstoque.deposito_id)
            .where(
                LoteEstoque.status == "ATIVO",
                LoteEstoque.data_validade.is_not(None),
                LoteEstoque.data_validade <= limite,
                Deposito.tenant_id == self.tenant_id,
            )
            .order_by(LoteEstoque.data_validade.asc().nullslast())
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(Deposito.unidade_produtiva_id == unidade_produtiva_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_requisicoes_pendentes(
        self,
        unidade_produtiva_id: UUID | None,
    ) -> list[RequisicaoMaterial]:
        service = EstoqueService(self.session, self.tenant_id)
        return await service.listar_requisicoes(
            unidade_produtiva_id=unidade_produtiva_id,
            status="PENDENTE",
        )

    async def _consumo_recente_por_produto(
        self,
        unidade_produtiva_id: UUID | None,
        janela_dias: int,
    ) -> dict[UUID, float]:
        limite = datetime.combine(date.today() - timedelta(days=janela_dias), time.min)
        stmt = (
            select(
                EstoqueMovimento.produto_id,
                func.coalesce(func.sum(func.abs(EstoqueMovimento.quantidade)), 0),
            )
            .where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.tipo_movimento == "SAIDA",
                EstoqueMovimento.data_movimento >= limite,
            )
            .group_by(EstoqueMovimento.produto_id)
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(EstoqueMovimento.production_unit_id == unidade_produtiva_id)
        rows = (await self.session.execute(stmt)).all()
        return {row[0]: float(row[1] or 0.0) for row in rows}

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
