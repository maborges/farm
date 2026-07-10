from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.dependencies import get_current_user, get_session, get_tenant_id
from core.models.auth import Usuario
from wizard.checklist_engine import ChecklistEngine
from wizard.models import ImplantacaoOperacional, PendenciaSeverity, PendenciaStatus, WizardStatus
from wizard.schemas import (
    WizardActionRequest,
    WizardCargaRequest,
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
from wizard.services import (
    sanitize_legacy_wizard_nullable_uuid_columns as _sanitize_legacy_uuids,
)
from wizard.state_engine import can_transition

router = APIRouter(prefix="/wizard", tags=["Wizard — Implantacao"])
SESSION_DEP = Depends(get_session)
TENANT_DEP = Depends(get_tenant_id)
CURRENT_USER_DEP = Depends(get_current_user)

_LEGACY_TEXT_REPLACEMENTS = {
    "nao habilitada para esta implantacao": "não está habilitada nesta implantação",
    "nao habilitado para esta implantacao": "não está habilitado nesta implantação",
    "não habilitada para esta implantação": "não está habilitada nesta implantação",
    "não habilitado para esta implantação": "não está habilitado nesta implantação",
    "implantacao": "implantação",
    "AreaRural": "Área Rural",
    "Talhao": "Talhão",
    "Pecuaria": "Pecuária",
    "Deposito": "Depósito",
    "Catalogo": "Catálogo",
    "catalogo": "catálogo",
    "Maquinas": "Máquinas",
    "Revisao": "Revisão",
    "Estabilizacao": "Estabilização",
}

_CHECKLIST_ACTION_GUIDANCE = {
    "CHECK_UNIDADE_PRODUTIVA": (
        "Cadastre ou ative pelo menos uma unidade produtiva para vincular a implantação "
        "a uma fazenda válida."
    ),
    "CHECK_ESTRUTURA_TERRITORIAL": (
        "Cadastre ao menos uma área rural ou talhão dentro da unidade produtiva para "
        "formar a estrutura territorial mínima."
    ),
    "CHECK_AGRICULTURA_TALHAO": (
        "Se o módulo agrícola estiver em uso, crie ao menos um talhão ativo para permitir "
        "operações e lançamentos da safra."
    ),
    "CHECK_PECUARIA_PIQUETE": (
        "Se o módulo pecuário estiver em uso, cadastre ao menos um piquete ativo para "
        "organizar o manejo do rebanho."
    ),
    "CHECK_ESTOQUE_DEPOSITO": (
        "Se o estoque estiver habilitado, crie ao menos um depósito ativo para receber "
        "saldos, entradas e saídas."
    ),
    "CHECK_FINANCEIRO_PLANO_CONTA": (
        "Se o financeiro estiver habilitado, configure um plano de contas mínimo para "
        "classificar receitas e despesas."
    ),
    "CHECK_PRODUTO_CATALOGO": (
        "Cadastre os produtos básicos da operação, como insumos, materiais ou itens de "
        "estoque, para liberar o catálogo mínimo."
    ),
    "CHECK_EQUIPAMENTO_CADASTRO": (
        "Se a frota estiver habilitada, cadastre ao menos um equipamento ou máquina para "
        "concluir a configuração operacional."
    ),
    "CHECK_CULTURA": (
        "Cadastre ao menos uma cultura produtiva (ex: Soja, Milho, Café) baseada nas "
        "commodities ou produtos canônicos para habilitar o módulo agrícola."
    ),
    "CHECK_INTEGRACAO_ERP": (
        "Se a operação usa ERP, informe qual sistema está integrado, teste a comunicação "
        "e confirme se as funções mínimas para o piloto já estão disponíveis no console ERP."
    ),
}

_CHECKLIST_ACTION_TARGETS = {
    "CHECK_UNIDADE_PRODUTIVA": ("Abrir propriedades", "/cadastros/propriedades"),
    "CHECK_ESTRUTURA_TERRITORIAL": ("Abrir talhões", "/cadastros/propriedades/talhoes"),
    "CHECK_AGRICULTURA_TALHAO": ("Abrir talhões", "/cadastros/propriedades/talhoes"),
    "CHECK_PECUARIA_PIQUETE": ("Abrir piquetes", "/dashboard/pecuaria/piquetes"),
    "CHECK_ESTOQUE_DEPOSITO": ("Abrir estoque", "/suprimentos/estoque"),
    "CHECK_FINANCEIRO_PLANO_CONTA": ("Abrir planos de conta", "/dashboard/financeiro/planos-conta"),
    "CHECK_PRODUTO_CATALOGO": ("Abrir produtos", "/cadastros/produtos"),
    "CHECK_EQUIPAMENTO_CADASTRO": ("Abrir equipamentos", "/cadastros/equipamentos"),
    "CHECK_CULTURA": ("Abrir culturas", "/cadastros/culturas"),
    "CHECK_INTEGRACAO_ERP": ("Abrir console ERP", "/dashboard/settings/integracoes/erp"),
}


async def _commit_and_restore_rls(session: AsyncSession):
    await session.commit()
    tenant_id = session.info.get("tenant_id")
    if tenant_id:
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))


def _merge_payload(
    payload_snapshot: dict[str, object] | None,
    motivo: str | None,
) -> dict[str, object]:
    payload = dict(payload_snapshot or {})
    if motivo:
        payload["motivo"] = motivo
    return payload


def _normalize_user_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value
    for old, new in _LEGACY_TEXT_REPLACEMENTS.items():
        normalized = normalized.replace(old, new)
    return normalized


def _get_checklist_action_guidance(codigo_item: str) -> str:
    return _CHECKLIST_ACTION_GUIDANCE.get(
        codigo_item,
        (
            "Conclua o cadastro ou a configuração exigida por este item para que a "
            "validação automática seja refeita com sucesso."
        ),
    )


def _get_checklist_action_target(codigo_item: str) -> tuple[str | None, str | None]:
    return _CHECKLIST_ACTION_TARGETS.get(codigo_item, (None, None))


async def _get_implantacao_ativa(
    service: ImplantacaoService,
    tenant_id: uuid.UUID,
    owner_usuario_id: uuid.UUID,
    *,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    from core.exceptions import EntityNotFoundError
    try:
        return await service.retomar_implantacao(
            tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
    except EntityNotFoundError:
        return await service.create_or_get_active(
            tenant_id=tenant_id,
            owner_usuario_id=owner_usuario_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )


def _resolver_unidade_produtiva_contexto(request: Request) -> uuid.UUID | None:
    header = request.headers.get("x-fazenda-id") or request.headers.get("x-unidade-produtiva-id")
    if not header:
        return None
    try:
        return uuid.UUID(header)
    except ValueError:
        return None


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
        modo_implantacao=getattr(implantacao, "modo_implantacao", None) or "ASSISTIDA",
        origem=getattr(implantacao, "origem", None) or "NOVO_ASSINANTE",
        unidade_produtiva_id=implantacao.unidade_produtiva_id,
        escopo_modulos=getattr(implantacao, "escopo_modulos", None),
        diagnostico_inicial_snapshot=getattr(implantacao, "diagnostico_inicial_snapshot", None),
        pendencias_criticas_abertas=pendencias_criticas_abertas,
        checklist_minimo_satisfeito=checklist_minimo_satisfeito,
        elegivel_para_pronto_go_live=elegivel_para_pronto_go_live,
        elegivel_para_go_live=elegivel_para_go_live,
        motivos_bloqueio=motivos_bloqueio,
        itens_checklist_faltantes=[
            WizardResumoChecklistPendenteResponse(
                codigo_item=item.codigo_item,
                descricao=_normalize_user_text(item.descricao) or item.descricao,
                acao_recomendada=_get_checklist_action_guidance(item.codigo_item),
                acao_label=_get_checklist_action_target(item.codigo_item)[0],
                acao_link=_get_checklist_action_target(item.codigo_item)[1],
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
                descricao=_normalize_user_text(pendencia.descricao) or pendencia.descricao,
                status=pendencia.status,
                severidade=pendencia.severidade,
            )
            for pendencia in pendencias_criticas
        ],
    )


async def _recarregar_implantacao_ativa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    implantacao_id: uuid.UUID | None,
) -> ImplantacaoOperacional:
    """Recarrega a implantação ativa para evitar estado ORM expirado após rollback.

    Args:
        service: Serviço de implantação já vinculado à sessão atual.
        tenant_id: Tenant usado para localizar a implantação ativa.
        implantacao: Instância original usada no fluxo de negócio.

    Returns:
        Instância fresca da implantação ativa, preferindo a id original.

    Raises:
        EntityNotFoundError: quando a implantação ativa não puder ser recarregada.
    """
    if implantacao_id is not None:
        stmt = (
            select(ImplantacaoOperacional)
            .where(
                ImplantacaoOperacional.id == implantacao_id,
                ImplantacaoOperacional.tenant_id == tenant_id,
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        recarregada = result.scalar_one_or_none()
        if recarregada is not None:
            return recarregada
    service = ImplantacaoService(session)
    return await service.get_active_implantacao(tenant_id)


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
            WizardChecklistItemResponse.model_validate(
                item,
                from_attributes=True,
            ).model_copy(
                update={
                    "descricao": _normalize_user_text(item.descricao) or item.descricao,
                    "acao_recomendada": _get_checklist_action_guidance(item.codigo_item),
                    "acao_label": _get_checklist_action_target(item.codigo_item)[0],
                    "acao_link": _get_checklist_action_target(item.codigo_item)[1],
                }
            )
            for item in itens
        ],
    )


async def _avaliar_checklist(
    session: AsyncSession,
    implantacao: ImplantacaoOperacional,
    *,
    tenant_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    """Reavalia o checklist do wizard, tratando UUIDs vazios legados.

    Args:
        session: Sessão assíncrona do SQLAlchemy.
        implantacao: Instância da implantação a reavaliar.
        tenant_id: Tenant usado para recarregar a implantação após sanitização.

    Returns:
        Instância da implantação (possivelmente recarregada após sanitização).
    """
    engine = ChecklistEngine(session)
    try:
        await engine.avaliar_implantacao(implantacao)
        return implantacao
    except DBAPIError as exc:
        raise


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
        implantacao = await _avaliar_checklist(session, implantacao)
    if implantacao.status == target_status:
        return implantacao
    service = ImplantacaoService(session)
    implantacao = await service.aplicar_transicao_estado(
        implantacao,
        target_status,
        ator_usuario_id=actor_user_id,
        payload_snapshot=_merge_payload(request.payload_snapshot, request.motivo),
    )
    await _commit_and_restore_rls(session)
    return implantacao


@router.get("/status", response_model=WizardResumoResponse)
async def wizard_status(
    request: Request,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    try:
        service = ImplantacaoService(session)
        implantacao = await _get_implantacao_ativa(
            service,
            tenant_id,
            current_user.id,
            unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
        )
        implantacao = await _avaliar_checklist(session, implantacao, tenant_id=tenant_id)
        await _commit_and_restore_rls(session)
        implantacao_id = implantacao.id
        implantacao = await _recarregar_implantacao_ativa(session, tenant_id, implantacao_id)
        return await _build_resumo(session, implantacao)
    except Exception as e:
        import traceback
        with open("/tmp/wizard_error.log", "a") as f:
            f.write(f"\nError in wizard_status:\n{traceback.format_exc()}\n")
        raise


async def _validate_erp_payload(session: AsyncSession, diagnostico: dict | None):
    if not diagnostico:
        return

    utiliza_erp = diagnostico.get("utiliza_erp") is True
    configurar_depois = diagnostico.get("configurar_erp_depois") is True
    erp_id = diagnostico.get("marketplace_integracao_id")
    erp_slug = diagnostico.get("marketplace_integracao_slug")

    if not utiliza_erp and erp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido enviar marketplace_integracao_id quando utiliza_erp é false",
        )

    if configurar_depois and erp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido enviar marketplace_integracao_id quando configurar_erp_depois é true",
        )

    if utiliza_erp and not erp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A seleção de um ERP é obrigatória quando utiliza_erp é true",
        )

    if erp_id:
        from integracoes.models import MarketplaceIntegracao
        from sqlalchemy import select

        stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.id == erp_id)
        result = await session.execute(stmt)
        provider = result.scalar_one_or_none()

        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ERP não encontrado no marketplace")

        if not provider.ativa:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O provider selecionado está inativo")

        if provider.provider_type != "ERP":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O provider selecionado não é do tipo ERP")

        if erp_slug and provider.slug != erp_slug:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O slug enviado não corresponde ao ERP selecionado")



@router.post(
    "/iniciar",
    response_model=WizardResumoResponse,
    status_code=status.HTTP_200_OK,
)
async def iniciar_wizard(
    request: Request,
    payload: WizardIniciarRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    payload = payload or WizardIniciarRequest()
    service = ImplantacaoService(session)
    implantacao = await service.create_or_get_active(
        tenant_id=tenant_id,
        owner_usuario_id=current_user.id,
        unidade_produtiva_id=payload.unidade_produtiva_id
        or _resolver_unidade_produtiva_contexto(request),
        modo_implantacao=payload.modo_implantacao,
        origem=payload.origem,
    )
    if payload.escopo_modulos is not None:
        implantacao.escopo_modulos = payload.escopo_modulos
    if payload.diagnostico_inicial_snapshot is not None:
        await _validate_erp_payload(session, payload.diagnostico_inicial_snapshot)
        implantacao.diagnostico_inicial_snapshot = payload.diagnostico_inicial_snapshot
    session.add(implantacao)
    implantacao = await _avaliar_checklist(session, implantacao, tenant_id=tenant_id)
    if implantacao.status == WizardStatus.NOT_STARTED.value:
        implantacao = await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.IN_PROGRESS.value,
            ator_usuario_id=current_user.id,
            payload_snapshot={"origem_endpoint": "wizard.iniciar"},
        )
    await _commit_and_restore_rls(session)
    return await _build_resumo(session, implantacao)


@router.post(
    "/configurar-carga",
    response_model=WizardResumoResponse,
    status_code=status.HTTP_200_OK,
)
async def configurar_carga_wizard(
    request: Request,
    payload: WizardCargaRequest,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao.modo_implantacao = payload.modo_implantacao
    implantacao.origem = payload.origem
    implantacao.escopo_modulos = payload.escopo_modulos

    if payload.diagnostico_inicial_snapshot is not None:
        await _validate_erp_payload(session, payload.diagnostico_inicial_snapshot)

    implantacao.diagnostico_inicial_snapshot = payload.diagnostico_inicial_snapshot
    session.add(implantacao)
    await _commit_and_restore_rls(session)
    implantacao = await _recarregar_implantacao_ativa(session, tenant_id, implantacao.id)
    return await _build_resumo(session, implantacao)


@router.get("/etapas", response_model=list[WizardEtapaResponse])
async def listar_etapas(
    request: Request,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    etapas = await service.etapa_service.listar_etapas(implantacao.id)
    return [
        WizardEtapaResponse.model_validate(
            etapa,
            from_attributes=True,
        ).model_copy(
            update={
                "nome": _normalize_user_text(etapa.nome) or etapa.nome,
                "observacoes": _normalize_user_text(etapa.observacoes),
            }
        )
        for etapa in etapas
    ]


@router.get("/checklist", response_model=WizardChecklistResponse)
async def listar_checklist(
    request: Request,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _avaliar_checklist(session, implantacao, tenant_id=tenant_id)
    await _commit_and_restore_rls(session)
    implantacao_id = implantacao.id
    implantacao = await _recarregar_implantacao_ativa(session, tenant_id, implantacao_id)
    return await _build_checklist_response(session, implantacao)


@router.post("/checklist/reavaliar", response_model=WizardChecklistResponse)
async def reavaliar_checklist(
    request: Request,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _avaliar_checklist(session, implantacao, tenant_id=tenant_id)
    await _commit_and_restore_rls(session)
    implantacao_id = implantacao.id
    implantacao = await _recarregar_implantacao_ativa(session, tenant_id, implantacao_id)
    return await _build_checklist_response(session, implantacao)


@router.get("/pendencias", response_model=list[WizardPendenciaResponse])
async def listar_pendencias(
    request: Request,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _avaliar_checklist(session, implantacao, tenant_id=tenant_id)
    await _commit_and_restore_rls(session)
    implantacao_id = implantacao.id
    implantacao = await _recarregar_implantacao_ativa(session, tenant_id, implantacao_id)
    service = ImplantacaoService(session)
    pendencias = await service.pendencia_service.listar_pendencias(implantacao.id)
    return [
        WizardPendenciaResponse.model_validate(
            pendencia,
            from_attributes=True,
        ).model_copy(
            update={
                "titulo": _normalize_user_text(pendencia.titulo) or pendencia.titulo,
                "descricao": _normalize_user_text(pendencia.descricao) or pendencia.descricao,
            }
        )
        for pendencia in pendencias
    ]


@router.post("/pausar", response_model=WizardResumoResponse)
async def pausar_wizard(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.PAUSED.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/retomar", response_model=WizardResumoResponse)
async def retomar_wizard(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.IN_PROGRESS.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/bloquear", response_model=WizardResumoResponse)
async def bloquear_wizard(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.BLOCKED.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/desbloquear", response_model=WizardResumoResponse)
async def desbloquear_wizard(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.IN_PROGRESS.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/pronto-go-live", response_model=WizardResumoResponse)
async def pronto_go_live(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.READY_FOR_GO_LIVE.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
        reevaluate_checklist=True,
    )
    return await _build_resumo(session, implantacao)


@router.post("/go-live", response_model=WizardResumoResponse)
async def executar_go_live(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.GO_LIVE.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
        reevaluate_checklist=True,
    )
    return await _build_resumo(session, implantacao)


@router.post("/estabilizar", response_model=WizardResumoResponse)
async def estabilizar_wizard(
    request: Request,
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(
        service,
        tenant_id,
        current_user.id,
        unidade_produtiva_id=_resolver_unidade_produtiva_contexto(request),
    )
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.STABILIZATION.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/concluir", response_model=WizardResumoResponse)
async def concluir_wizard(
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id, current_user.id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.COMPLETED.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)


@router.post("/cancelar", response_model=WizardResumoResponse)
async def cancelar_wizard(
    body: WizardActionRequest | None = None,
    session: AsyncSession = SESSION_DEP,
    tenant_id: uuid.UUID = TENANT_DEP,
    current_user: Usuario = CURRENT_USER_DEP,
):
    service = ImplantacaoService(session)
    implantacao = await _get_implantacao_ativa(service, tenant_id, current_user.id)
    implantacao = await _apply_transition_and_commit(
        session,
        implantacao,
        target_status=WizardStatus.CANCELLED.value,
        actor_user_id=current_user.id,
        request=body or WizardActionRequest(),
    )
    return await _build_resumo(session, implantacao)
