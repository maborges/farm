from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from campo.models import TarefaCampo
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from pecuaria.services.lote_resumo_sanitario_service import LoteResumoSanitarioService

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal
from ._common import build_candidate_context, build_route_target, stable_dedupe_key, tenant_signal_ids


class PecuariaRecommendationProvider(RecommendationProvider):
    provider_name = "pecuaria"
    domains = ("LIVESTOCK",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None:
            return []

        signal_ids = tenant_signal_ids(signals, context.tenant_id)
        payload = context.payload or {}
        dias_sem_pesagem = int(payload.get("dias_sem_pesagem", 45))
        dias_sem_movimentacao = int(payload.get("dias_sem_movimentacao", 30))
        limite_custo_sanitario = float(payload.get("limite_custo_sanitario_por_cabeca", 50.0))

        candidates: list[RecommendationCandidate] = []
        for lote in await self._listar_lotes(context.tenant_id, context.unidade_produtiva_id):
            indicadores = await self._resumo_lote(lote.id)
            sanitario = await self._resumo_sanitario(lote.id)
            ultima_movimentacao = await self._ultima_movimentacao(lote.id)

            if indicadores is not None:
                if self._precisa_pesagem(indicadores.ultima_pesagem, dias_sem_pesagem):
                    candidates.append(
                        self._candidate(
                            context,
                            scope_type="LOTE",
                            scope_id=str(lote.id),
                            rule_code="PEC_LOTE_SEM_PESAGEM_RECENTE",
                            title="Lote sem pesagem recente",
                            summary=(
                                f"O lote '{lote.identificacao}' está sem pesagem recente."
                            ),
                            rationale=(
                                "A pesagem atualizada é a base para acompanhar ganho de peso e orientar o manejo."
                            ),
                            priority=RecommendationPriority.HIGH,
                            confidence=Decimal("0.90"),
                            action_label="Abrir lote",
                            action_target=build_route_target(
                                "/dashboard/pecuaria/lotes",
                                lote.id,
                            ),
                            source_type=RecommendationSourceType.INDICATOR,
                            source_signal_ids=signal_ids,
                            context_data={
                                "lote_id": str(lote.id),
                                "lote_identificacao": lote.identificacao,
                                "ultima_pesagem": indicadores.ultima_pesagem.isoformat() if indicadores.ultima_pesagem else None,
                                "quantidade_animais": indicadores.quantidade_animais,
                                "dias_sem_pesagem": dias_sem_pesagem,
                            },
                        )
                    )

                if sanitario is not None and sanitario.custo_sanitario_por_animal >= limite_custo_sanitario:
                    candidates.append(
                        self._candidate(
                            context,
                            scope_type="LOTE",
                            scope_id=str(lote.id),
                            rule_code="PEC_CUSTO_SANITARIO_ALTO",
                            title="Custo sanitário acima do esperado",
                            summary=(
                                f"O lote '{lote.identificacao}' apresenta custo sanitário de "
                                f"R$ {sanitario.custo_sanitario_por_animal:.2f} por cabeça."
                            ),
                            rationale=(
                                "O custo sanitário do lote está acima do patamar operacional de referência."
                            ),
                            priority=RecommendationPriority.NORMAL,
                            confidence=Decimal("0.84"),
                            action_label="Revisar sanidade",
                            action_target=build_route_target(
                                "/dashboard/pecuaria/lotes",
                                lote.id,
                            ),
                            source_type=RecommendationSourceType.ANALYTICS,
                            source_signal_ids=signal_ids,
                            context_data={
                                "lote_id": str(lote.id),
                                "custo_sanitario_total": sanitario.custo_sanitario_total,
                                "custo_sanitario_por_cabeca": sanitario.custo_sanitario_por_animal,
                                "ultima_vacinacao": sanitario.ultima_vacinacao.isoformat() if sanitario.ultima_vacinacao else None,
                            },
                        )
                    )

            if self._movimentacao_antiga(ultima_movimentacao, dias_sem_movimentacao):
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="LOTE",
                        scope_id=str(lote.id),
                        rule_code="PEC_LOTE_SEM_MOVIMENTACAO_RECENTE",
                        title="Lote sem movimentação recente",
                        summary="Não há movimentação zootécnica recente suficiente para o lote.",
                        rationale="A ausência de eventos recentes reduz a visibilidade operacional do lote e do piquete.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.82"),
                        action_label="Revisar manejo",
                        action_target=build_route_target(
                            "/dashboard/pecuaria/lotes",
                            lote.id,
                        ),
                        source_type=RecommendationSourceType.EVENT,
                        source_signal_ids=signal_ids,
                        context_data={
                            "lote_id": str(lote.id),
                            "ultima_movimentacao": ultima_movimentacao.isoformat() if ultima_movimentacao else None,
                            "dias_sem_movimentacao": dias_sem_movimentacao,
                            "area_id": str(lote.area_id) if lote.area_id else None,
                        },
                    )
                )

            if lote.area_id is None:
                candidates.append(
                    self._candidate(
                        context,
                        scope_type="LOTE",
                        scope_id=str(lote.id),
                        rule_code="PEC_LOTE_SEM_PIQUETE",
                        title="Lote sem piquete vinculado",
                        summary="O lote não possui piquete vinculado para orientar o manejo coletivo.",
                        rationale="Sem piquete associado, o controle operacional do lote perde precisão.",
                        priority=RecommendationPriority.NORMAL,
                        confidence=Decimal("0.76"),
                        action_label="Vincular piquete",
                        action_target=build_route_target(
                            "/dashboard/pecuaria/lotes",
                            lote.id,
                        ),
                        source_type=RecommendationSourceType.SYSTEM,
                        source_signal_ids=signal_ids,
                        context_data={
                            "lote_id": str(lote.id),
                            "lote_identificacao": lote.identificacao,
                            "area_id": None,
                        },
                    )
                )

        for tarefa in await self._tarefas_vacinacao_atrasadas(context.tenant_id, context.unidade_produtiva_id):
            candidates.append(
                self._candidate(
                    context,
                    scope_type="TASK",
                    scope_id=str(tarefa.id),
                    rule_code="PEC_VACINACAO_ATRASADA",
                    title="Vacinação atrasada",
                    summary=(
                        f"A tarefa '{tarefa.titulo or tarefa.type}' está atrasada para o lote {tarefa.lote_id}."
                    ),
                    rationale="Vacinações atrasadas elevam risco sanitário e quebram o calendário de manejo.",
                    priority=RecommendationPriority.URGENT,
                    confidence=Decimal("0.95"),
                    action_label="Abrir manejo",
                    action_target=build_route_target("/dashboard/pecuaria/manejo", tarefa.id),
                    source_type=RecommendationSourceType.EVENT,
                    source_signal_ids=signal_ids,
                    context_data={
                        "tarefa_campo_id": str(tarefa.id),
                        "lote_id": str(tarefa.lote_id) if tarefa.lote_id else None,
                        "data_programada": tarefa.data_programada.isoformat() if tarefa.data_programada else None,
                        "status_execucao": tarefa.status_execucao,
                    },
                )
            )

        return candidates

    async def _listar_lotes(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[LoteAnimal]:
        stmt = select(LoteAnimal).where(
            LoteAnimal.tenant_id == tenant_id,
            LoteAnimal.ativo.is_(True),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(LoteAnimal.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(LoteAnimal.updated_at.desc(), LoteAnimal.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _resumo_lote(self, lote_id: UUID):
        return await LoteIndicadoresService(self.session, self.tenant_id).resumir(lote_id)

    async def _resumo_sanitario(self, lote_id: UUID):
        return await LoteResumoSanitarioService(self.session, self.tenant_id).resumir(lote_id)

    async def _ultima_movimentacao(self, lote_id: UUID) -> date | None:
        stmt = (
            select(func.max(EventoAnimal.data_evento))
            .join(Animal, Animal.id == EventoAnimal.animal_id)
            .where(
                EventoAnimal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _tarefas_vacinacao_atrasadas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[TarefaCampo]:
        stmt = select(TarefaCampo).where(
            TarefaCampo.tenant_id == tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type.in_(("VACINACAO", "VACINACAO_LOTE")),
            TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
            TarefaCampo.data_programada.is_not(None),
            TarefaCampo.data_programada < date.today(),
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(TarefaCampo.data_programada.asc(), TarefaCampo.created_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    @staticmethod
    def _precisa_pesagem(ultima_pesagem, dias_sem_pesagem: int) -> bool:
        if ultima_pesagem is None:
            return True
        return (date.today() - ultima_pesagem).days >= dias_sem_pesagem

    @staticmethod
    def _movimentacao_antiga(ultima_movimentacao, dias_sem_movimentacao: int) -> bool:
        if ultima_movimentacao is None:
            return True
        return (date.today() - ultima_movimentacao).days >= dias_sem_movimentacao

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
        context_data: dict[str, Any],
    ) -> RecommendationCandidate:
        return RecommendationCandidate(
            tenant_id=context.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            domain=RecommendationDomain.LIVESTOCK,
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
