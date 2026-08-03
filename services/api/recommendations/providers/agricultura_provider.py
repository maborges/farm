from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.caderno.models import CadernoCampoEntrada
from agricola.custos.service import CustosService
from agricola.operacoes.models import OperacaoAgricola
from agricola.romaneios.service import RomaneioService
from agricola.safras.models import Safra, SafraTalhao

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


class AgriculturaRecommendationProvider(RecommendationProvider):
    provider_name = "agricultura"
    domains = ("AGRICULTURE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        safra_id = self._resolve_safra_id(context)
        if safra_id is None:
            return []

        safra = await self._get_safra(context.tenant_id, safra_id)
        if safra is None:
            return []

        signal_ids = [signal.signal_id for signal in signals if signal.tenant_id == context.tenant_id]
        candidatos: list[RecommendationCandidate] = []

        latest_operation_date = await self._latest_operation_date(context.tenant_id, safra_id)
        if latest_operation_date is None or (date.today() - latest_operation_date).days >= 7:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_SAFRA_SEM_MOVIMENTACAO_RECENTE",
                    title="Safra sem movimentação recente",
                    summary="A safra está com pouca ou nenhuma movimentação operacional recente.",
                    rationale="A ausência de operações recentes reduz a capacidade de reação do time no campo.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.87"),
                    action_label="Repriorizar",
                    action_target=self._target(safra_id),
                    source_type=RecommendationSourceType.ANALYTICS,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "OperacaoAgricola",
                        "ultima_movimentacao": latest_operation_date.isoformat() if latest_operation_date else None,
                    },
                )
            )

        atraso_operacoes = await self._operations_delay(context.tenant_id, safra_id)
        if atraso_operacoes["count"] > 0:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_OPERACAO_ATRASADA",
                    title="Operação agrícola atrasada",
                    summary=f"{atraso_operacoes['count']} operação(ões) passaram do prazo previsto.",
                    rationale="Operações fora do prazo aumentam custo, risco de retrabalho e perda de eficiência.",
                    priority=RecommendationPriority.URGENT,
                    confidence=Decimal("0.93"),
                    action_label="Replanejar operações",
                    action_target=self._target(safra_id),
                    source_type=RecommendationSourceType.ANALYTICS,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "OperacaoAgricola",
                        "operacoes_em_atraso": atraso_operacoes["count"],
                        "maior_atraso_dias": atraso_operacoes["max_days"],
                    },
                )
            )

        talhao_atualizacao = await self._talhao_sem_atualizacao(context.tenant_id, safra_id)
        if talhao_atualizacao is not None:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_TALHAO_SEM_ATUALIZACAO",
                    title="Talhão sem atualização recente",
                    summary="Há talhão com atualização de campo vencida para a janela operacional atual.",
                    rationale="O campo sem atualização reduz a confiabilidade das decisões de manejo e priorização.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.84"),
                    action_label="Atualizar talhão",
                    action_target=self._target(safra_id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "CadernoCampoEntrada",
                        "talhao_id": str(talhao_atualizacao["talhao_id"]),
                        "idade_dias": talhao_atualizacao["idade_dias"],
                    },
                )
            )

        custo_alerta = await self._budget_gap(context, safra_id)
        if custo_alerta is not None:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_CUSTO_ACIMA_PREVISTO",
                    title="Custo agrícola acima do previsto",
                    summary=f"Desvio orçamentário de {custo_alerta['desvio_pct']:.1f}% acima da previsão.",
                    rationale="O custo realizado já ultrapassa a referência oficial de orçamento da safra.",
                    priority=RecommendationPriority.HIGH if custo_alerta["desvio_pct"] < 25 else RecommendationPriority.URGENT,
                    confidence=Decimal("0.91"),
                    action_label="Revisar orçamento",
                    action_target=self._target(safra_id),
                    source_type=RecommendationSourceType.ANALYTICS,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": custo_alerta["fonte"],
                        "custo_realizado_total": custo_alerta["custo_realizado_total"],
                        "orcamento_previsto_total": custo_alerta["orcamento_previsto_total"],
                        "desvio_orcamento_pct": custo_alerta["desvio_pct"],
                    },
                )
            )

        colheitas_pendentes = await self._colheitas_sem_romaneio(context.tenant_id, safra_id)
        if colheitas_pendentes:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_COLHEITA_SEM_ROMANEIO",
                    title="Colheita sem romaneio lançado",
                    summary=f"{len(colheitas_pendentes)} colheita(s) concluída(s) no campo ainda sem romaneio lançado.",
                    rationale="Sem romaneio, a colheita não gera entrada de estoque nem rastreabilidade — a quantidade colhida fica invisível para o sistema.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.95"),
                    action_label="Lançar romaneio",
                    action_target=self._romaneios_target(safra_id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "TarefaCampo",
                        "total_pendentes": len(colheitas_pendentes),
                        "talhoes": [
                            {"talhao_id": str(c.talhao_id) if c.talhao_id else None, "talhao_nome": c.talhao_nome}
                            for c in colheitas_pendentes[:5]
                        ],
                        "mais_antiga_concluida_em": (
                            mais_antiga.isoformat()
                            if (mais_antiga := min(
                                (c.concluida_em for c in colheitas_pendentes if c.concluida_em), default=None
                            ))
                            else None
                        ),
                    },
                )
            )

        todo_itens = await self._checklist_todo_pendentes(context.tenant_id, safra_id)
        for item, email in todo_itens:
            dias_restantes = (item.prazo_resposta - date.today()).days if item.prazo_resposta else None
            if dias_restantes is not None and dias_restantes < 0:
                prioridade_todo = RecommendationPriority.URGENT
            elif dias_restantes is not None and dias_restantes <= 2:
                prioridade_todo = RecommendationPriority.HIGH
            else:
                prioridade_todo = RecommendationPriority.NORMAL

            prazo_label = f" até {item.prazo_resposta.strftime('%d/%m/%Y')}" if item.prazo_resposta else ""
            candidatos.append(
                RecommendationCandidate(
                    tenant_id=context.tenant_id,
                    unidade_produtiva_id=context.unidade_produtiva_id,
                    domain=RecommendationDomain.AGRICULTURE,
                    priority=prioridade_todo,
                    source_type=RecommendationSourceType.EVENT,
                    action_type=RecommendationActionType.OPEN_ROUTE,
                    provider_name=self.provider_name,
                    rule_code="AGRI_CHECKLIST_TODO_PRAZO",
                    scope_type="SAFRA_CHECKLIST_ITEM",
                    scope_id=str(item.id),
                    title="Pendência de checklist atribuída a você",
                    summary=f'"{item.titulo}" precisa da sua ação{prazo_label}.',
                    rationale="Item de checklist sem tarefa de campo por trás depende de acompanhamento manual do responsável atribuído.",
                    dedupe_key=f"agricultura:{context.tenant_id}:checklist_todo:{item.id}",
                    source_signal_ids=signal_ids,
                    confidence=Decimal("0.90"),
                    action_label="Abrir checklist",
                    action_target=self._checklist_target(safra_id),
                    context={
                        "source": "SafraChecklistItem",
                        "item_id": str(item.id),
                        "fase": item.fase,
                        "tipo_resultado": item.tipo_resultado,
                        "prazo_resposta": item.prazo_resposta.isoformat() if item.prazo_resposta else None,
                        "dias_restantes": dias_restantes,
                        "notification_recipients": [email] if email else [],
                        "safra_id": str(safra_id),
                        "generated_at": context.generated_at.isoformat(),
                    },
                )
            )

        if candidatos:
            candidatos.append(
                self._candidate(
                    context,
                    safra_id=safra_id,
                    rule_code="AGRI_PRIORIZACAO_OPERACIONAL",
                    title="Priorização operacional recomendada",
                    summary="Os sinais atuais pedem priorização das frentes com maior atraso e maior custo.",
                    rationale="A combinação de atraso, custo e baixa atualização indica ganho rápido com foco operacional.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.79"),
                    action_label="Abrir plano",
                    action_target=self._target(safra_id),
                    source_type=RecommendationSourceType.SYSTEM,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RecommendationProvider",
                        "safra_status": safra.status,
                        "total_candidatos": len(candidatos),
                    },
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

    async def _get_safra(self, tenant_id: UUID, safra_id: UUID) -> Safra | None:
        stmt = select(Safra).where(Safra.tenant_id == tenant_id, Safra.id == safra_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def _latest_operation_date(self, tenant_id: UUID, safra_id: UUID) -> date | None:
        stmt = select(func.max(OperacaoAgricola.data_realizada)).where(
            OperacaoAgricola.tenant_id == tenant_id,
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.origem_invalidada == False,  # noqa: E712
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _operations_delay(self, tenant_id: UUID, safra_id: UUID) -> dict[str, int]:
        stmt = select(
            OperacaoAgricola.data_prevista,
            OperacaoAgricola.data_realizada,
        ).where(
            OperacaoAgricola.tenant_id == tenant_id,
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.data_prevista.is_not(None),
            OperacaoAgricola.data_realizada > OperacaoAgricola.data_prevista,
        )
        rows = (await self.session.execute(stmt)).all()
        if not rows:
            return {"count": 0, "max_days": 0}
        atrasos = [(row.data_realizada - row.data_prevista).days for row in rows if row.data_prevista and row.data_realizada]
        return {
            "count": len(atrasos),
            "max_days": max(atrasos) if atrasos else 0,
        }

    async def _talhao_sem_atualizacao(self, tenant_id: UUID, safra_id: UUID) -> dict[str, object] | None:
        stmt = (
            select(
                SafraTalhao.area_id.label("talhao_id"),
                func.max(CadernoCampoEntrada.data_registro).label("ultima_atualizacao"),
            )
            .join(SafraTalhao, SafraTalhao.area_id == CadernoCampoEntrada.talhao_id)
            .where(
                CadernoCampoEntrada.tenant_id == tenant_id,
                CadernoCampoEntrada.safra_id == safra_id,
                SafraTalhao.tenant_id == tenant_id,
                SafraTalhao.safra_id == safra_id,
            )
            .group_by(SafraTalhao.area_id)
            .order_by(func.max(CadernoCampoEntrada.data_registro).asc().nullsfirst())
        )
        rows = (await self.session.execute(stmt)).all()
        if not rows:
            stmt_talhoes = (
                select(SafraTalhao.area_id)
                .where(
                    SafraTalhao.tenant_id == tenant_id,
                    SafraTalhao.safra_id == safra_id,
                )
                .order_by(SafraTalhao.created_at.asc())
                .limit(1)
            )
            talhao = (await self.session.execute(stmt_talhoes)).scalar_one_or_none()
            if talhao is None:
                return None
            return {"talhao_id": talhao, "idade_dias": 999}

        talhao_id, ultima_atualizacao = rows[0]
        if ultima_atualizacao is None:
            return {"talhao_id": talhao_id, "idade_dias": 999}

        idade_dias = (date.today() - ultima_atualizacao).days
        if idade_dias >= 7:
            return {"talhao_id": talhao_id, "idade_dias": idade_dias}
        return None

    async def _colheitas_sem_romaneio(self, tenant_id: UUID, safra_id: UUID) -> list:
        return await RomaneioService(self.session, tenant_id).listar_pendentes_de_romaneio(safra_id=safra_id)

    async def _checklist_todo_pendentes(self, tenant_id: UUID, safra_id: UUID) -> list[tuple[object, str | None]]:
        """Itens de checklist com responsável atribuído (tipo_resultado !=
        TAREFA_CAMPO, que já tem responsável via operador_id da OS/tarefa de
        campo) ainda não concluídos — notificados por e-mail direcionado."""
        from agricola.checklist.models import SafraChecklistItem
        from core.models.auth import Usuario

        stmt = (
            select(SafraChecklistItem, Usuario.email)
            .join(Usuario, Usuario.id == SafraChecklistItem.responsavel_id)
            .where(
                SafraChecklistItem.tenant_id == tenant_id,
                SafraChecklistItem.safra_id == safra_id,
                SafraChecklistItem.responsavel_id.is_not(None),
                SafraChecklistItem.tipo_resultado != "TAREFA_CAMPO",
                SafraChecklistItem.concluido == False,  # noqa: E712
                SafraChecklistItem.cancelado == False,  # noqa: E712
            )
        )
        return list((await self.session.execute(stmt)).all())

    async def _budget_gap(self, context: OperationalContext, safra_id: UUID) -> dict[str, object] | None:
        resumo = await CustosService(self.session, context.tenant_id).get_resumo_safra(safra_id)
        if resumo.orcamento_previsto_total is None or resumo.desvio_orcamento_pct is None:
            return None
        if resumo.desvio_orcamento_pct <= 10:
            return None
        return {
            "fonte": resumo.fonte_orcamento_previsto,
            "custo_realizado_total": float(resumo.custo_total_realizado),
            "orcamento_previsto_total": float(resumo.orcamento_previsto_total),
            "desvio_pct": float(resumo.desvio_orcamento_pct),
        }

    def _candidate(
        self,
        context: OperationalContext,
        *,
        safra_id: UUID,
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
            domain=RecommendationDomain.AGRICULTURE,
            priority=priority,
            source_type=source_type,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name=self.provider_name,
            rule_code=rule_code,
            scope_type=context.scope_type,
            scope_id=str(safra_id),
            title=title,
            summary=summary,
            rationale=rationale,
            dedupe_key=self._dedupe_key(context, safra_id, rule_code),
            source_signal_ids=source_signal_ids,
            confidence=confidence,
            action_label=action_label,
            action_target=action_target,
            context={
                **context_data,
                "safra_id": str(safra_id),
                "generated_at": context.generated_at.isoformat(),
            },
        )

    @staticmethod
    def _target(safra_id: UUID) -> str:
        return f"/agricola/safras/{safra_id}/inteligencia-operacional"

    @staticmethod
    def _romaneios_target(safra_id: UUID) -> str:
        return f"/agricola/safras/{safra_id}/romaneios"

    @staticmethod
    def _checklist_target(safra_id: UUID) -> str:
        return f"/agricola/safras/{safra_id}/checklist"

    @staticmethod
    def _dedupe_key(context: OperationalContext, safra_id: UUID, rule_code: str) -> str:
        unidade = context.unidade_produtiva_id or "tenant"
        return f"agricultura:{context.tenant_id}:{unidade}:{safra_id}:{rule_code}"
