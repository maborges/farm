from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_session, get_tenant_id
from core.models.auth import Usuario
from wizard.checklist_engine import ChecklistEngine
from wizard.models import ImplantacaoOperacional, PendenciaSeverity, PendenciaStatus, WizardStatus
from wizard.schemas import (
    WizardActionRequest,
    WizardChecklistItemResponse,
    WizardChecklistResponse,
    WizardEtapaResponse,
    WizardIniciarRequest,
    WizardPendenciaResponse,
    WizardResumoChecklistPendenteResponse,
    WizardResumoPendenciaCriticaResponse,
    WizardResumoResponse,
)
from wizard.services import ImplantacaoService
from wizard.state_engine import can_transition

router = APIRouter(prefix="/wizard", tags=["Wizard — Implantacao"])
SESSION_DEP = Depends(get_session)
TENANT_DEP = Depends(get_tenant_id)
CURRENT_USER_DEP = Depends(get_current_user)


def _merge_payload(
    payload_snapshot: dict[str, object] | None,
    motivo: str | None,
) -> dict[str, object]:
    payload = dict(payload_snapshot or {})
    if motivo:
        payload["motivo"] = motivo
    return payload


async def _get_implantacao_ativa(
    service: ImplantacaoService,
    tenant_id: uuid.UUID,
) -> ImplantacaoOperacional:
    return await service.retomar_implantacao(tenant_id)


async def _build_resumo(
    session: AsyncSession,
    implantacao: ImplantacaoOperacional,
) -> WizardResumoResponse:
    service = ImplantacaoService(session)
    checklist_items = await service.checklist_service.listar_itens(implantacao.id)
    checklist_minimo_satisfeito = await (
        service.checklist_service.minimum_checklist_satisfied(implantacao.id)
    )
    pendencias = await service.pendencia_service.listar_pendencias(implantacao.id)
    pendencias_criticas = [
        pendencia
        for pendencia in pendencias
        if pendencia.severidade == PendenciaSeverity.CRITICA.value
        and pendencia.status
        in {
            PendenciaStatus.ABERTA.value,
            PendenciaStatus.EM_TRATAMENTO.value,
        }
    ]
    pendencias_criticas_abertas = sum(
        1
        for _ in pendencias_criticas
    )
    itens_checklist_faltantes = [
        item
        for item in checklist_items
        if item.obrigatorio
        and item.status not in {"ATENDIDO", "DISPENSADO"}
    ]
    motivos_bloqueio: list[str] = []
    if implantacao.status == WizardStatus.BLOCKED.value:
        motivos_bloqueio.append(
            "A implantação está em BLOCKED e precisa voltar para IN_PROGRESS antes de avançar."
        )
    if implantacao.unidade_produtiva_id is None:
        motivos_bloqueio.append(
            "É obrigatório vincular uma UnidadeProdutiva ativa "
            "antes de READY_FOR_GO_LIVE ou GO_LIVE."
        )
    if not checklist_minimo_satisfeito:
        motivos_bloqueio.append(
            "O checklist mínimo do piloto ainda não está satisfeito "
            "com base no estado real do tenant."
        )
    if pendencias_criticas_abertas > 0:
        motivos_bloqueio.append(
            "Existem pendências críticas abertas que bloqueiam prontidão e go-live assistido."
        )
    elegivel_para_pronto_go_live = can_transition(
        implantacao,
        WizardStatus.READY_FOR_GO_LIVE.value,
        minimum_checklist_satisfied=checklist_minimo_satisfeito,
        has_open_critical_blockers=pendencias_criticas_abertas > 0,
    )
    elegivel_para_go_live = can_transition(
        implantacao,
        WizardStatus.GO_LIVE.value,
        minimum_checklist_satisfied=checklist_minimo_satisfeito,
        has_open_critical_blockers=pendencias_criticas_abertas > 0,
    )
    return WizardResumoResponse(
        implantacao_id=implantacao.id,
        status=implantacao.status,
        etapa_atual=implantacao.etapa_atual,
        percentual_progresso=implantacao.percentual_progresso,
        checklist_minimo_percentual=implantacao.checklist_minimo_percentual,
        unidade_produtiva_id=implantacao.unidade_produtiva_id,
        pendencias_criticas_abertas=pendencias_criticas_abertas,
        checklist_minimo_satisfeito=checklist_minimo_satisfeito,
        elegivel_para_pronto_go_live=elegivel_para_pronto_go_live,
        elegivel_para_go_live=elegivel_para_go_live,
        motivos_bloqueio=motivos_bloqueio,
        itens_checklist_faltantes=[
            WizardResumoChecklistPendenteResponse(
                codigo_item=item.codigo_item,
                descricao=item.descricao,
                obrigatorio=item.obrigatorio,
                status=item.status,
                severidade=item.severidade,
            )
            for item in itens_checklist_faltantes
        ],
        pendencias_criticas=[
            WizardResumoPendenciaCriticaResponse(
                id=pendencia.id,
                titulo=pendencia.titulo,
                descricao=pendencia.descricao,
                status=pendencia.status,
                severidade=pendencia.severidade,
            )
            for pendencia in pendencias_criticas
        ],
    )


async def _build_checklist_response(
    session: AsyncSession,
    implantacao: ImplantacaoOperacional,
) -> WizardChecklistResponse:
    service = ImplantacaoService(session)
    itens = await service.checklist_service.listar_itens(implantacao.id)
    checklist_minimo_satisfeito = await (
        service.checklist_service.minimum_checklist_satisfied(implantacao.id)
    )
    pendencias = await service.pendencia_service.listar_pendencias(implantacao.id)
    pendencias_criticas_abertas = sum(
        1
        for pendencia in pendencias
        if pendencia.severidade == PendenciaSeverity.CRITICA.value
        and pendencia.status
        in {
            PendenciaStatus.ABERTA.value,
            PendenciaStatus.EM_TRATAMENTO.value,
        }
    )
    return WizardChecklistResponse(
        implantacao_id=implantacao.id,
        checklist_minimo_satisfeito=checklist_minimo_satisfeito,
        pendencias_criticas_abertas=pendencias_criticas_abertas,
        itens=[
            WizardChecklistItemResponse.model_validate(item, from_attributes=True)
            for item in itens
        ],
    )


async def _avaliar_checklist(
    session: AsyncSession,
    implantacao: ImplantacaoOperacional,
) -> None:
    engine = ChecklistEngine(session)
    await engine.avaliar_implantacao(implantacao)


async def _apply_transition_and_commit(
    session: AsyncSession,
    implantacao: ImplantacaoOperacional,
    *,
    target_status: str,
    actor_user_id: uuid.UUID,
    request: WizardActionRequest,
    reevaluate_checklist: bool = False,
) -> ImplantacaoOperacional:
    if reevaluate_checklist:
        await _avaliar_checklist(session, implantacao)
    if implantacao.status == target_status:
        return implantacao
    service = ImplantacaoService(session)
    implantacao = await service.aplicar_transicao_estado(
        implantacao,
        target_status,
        ator_usuario_id=actor_user_id,
        payload_snapshot=_merge_payload(request.payload_snapshot, request.motivo),
    )
    await session.commit()
    return implantacao


@router.get("/status", response_model=WizardResumoResponse)
async def wizard_status(
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    del current_user
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    return await _build_resumo(session, implantacao)


@router.post(
    "/iniciar",
    response_model=WizardResumoResponse,
    status_code=status.HTTP_200_OK,
)
async def iniciar_wizard(
    request: WizardIniciarRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    payload = request or WizardIniciarRequest()
    service = ImplantacaoService(session)
    implantacao = await service.create_or_get_active(
        tenant_id=tenant_id,
        owner_usuario_id=current_user.id,
        unidade_produtiva_id=payload.unidade_produtiva_id,
        modo_implantacao=payload.modo_implantacao,
        origem=payload.origem,
    )
    if payload.escopo_modulos is not None:
        implantacao.escopo_modulos = payload.escopo_modulos
    if payload.diagnostico_inicial_snapshot is not None:
        implantacao.diagnostico_inicial_snapshot = payload.diagnostico_inicial_snapshot
    session.add(implantacao)
    await _avaliar_checklist(session, implantacao)
    if implantacao.status == WizardStatus.NOT_STARTED.value:
        implantacao = await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.IN_PROGRESS.value,
            ator_usuario_id=current_user.id,
            payload_snapshot={"origem_endpoint": "wizard.iniciar"},
        )
    await session.commit()
    return await _build_resumo(session, implantacao)


@router.get("/etapas", response_model=list[WizardEtapaResponse])
async def listar_etapas(
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    del current_user
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    etapas = await service.etapa_service.listar_etapas(implantacao.id)
    return [
        WizardEtapaResponse.model_validate(etapa, from_attributes=True)
        for etapa in etapas
    ]


@router.get("/checklist", response_model=WizardChecklistResponse)
async def listar_checklist(
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    del current_user
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    return await _build_checklist_response(session, implantacao)


@router.post("/checklist/reavaliar", response_model=WizardChecklistResponse)
async def reavaliar_checklist(
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    del current_user
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    await _avaliar_checklist(session, implantacao)
    await session.commit()
    return await _build_checklist_response(session, implantacao)


@router.get("/pendencias", response_model=list[WizardPendenciaResponse])
async def listar_pendencias(
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    del current_user
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    pendencias = await service.pendencia_service.listar_pendencias(implantacao.id)
    return [
        WizardPendenciaResponse.model_validate(pendencia, from_attributes=True)
        for pendencia in pendencias
    ]


@router.post("/pausar", response_model=WizardResumoResponse)
async def pausar_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.PAUSED.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/retomar", response_model=WizardResumoResponse)
async def retomar_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.IN_PROGRESS.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/bloquear", response_model=WizardResumoResponse)
async def bloquear_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.BLOCKED.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/desbloquear", response_model=WizardResumoResponse)
async def desbloquear_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.IN_PROGRESS.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/pronto-go-live", response_model=WizardResumoResponse)
async def pronto_go_live(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.READY_FOR_GO_LIVE.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
        reevaluate_checklist=True,
    )
    return await _build_resumo(session, implantacao)


@router.post("/go-live", response_model=WizardResumoResponse)
async def executar_go_live(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.GO_LIVE.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
        reevaluate_checklist=True,
    )
    return await _build_resumo(session, implantacao)


@router.post("/estabilizar", response_model=WizardResumoResponse)
async def estabilizar_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.STABILIZATION.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/concluir", response_model=WizardResumoResponse)
async def concluir_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.COMPLETED.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/cancelar", response_model=WizardResumoResponse)
async def cancelar_wizard(
    request: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.CANCELLED.value,
        actor_user_id=current_user.id,
        request=request or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)
