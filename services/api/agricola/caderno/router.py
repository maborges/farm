from fastapi import APIRouter, Depends, status, Request, UploadFile, File, Form
from fastapi.responses import Response
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from pathlib import Path

from core.constants import PlanTier
from core.dependencies import get_tenant_id, require_module, require_role, require_tier, get_session_with_tenant, get_current_user
from core.exceptions import BusinessRuleError
from agricola.caderno.models import CadernoExportacao
from agricola.caderno.schemas import (
    EntradaCreate,
    EntradaUpdate,
    EntradaDeleteRequest,
    EntradaResponse,
    FotoResponse,
    VisitaTecnicaCreate,
    VisitaTecnicaResponse,
    AssinarVisitaRequest,
    EPIEntregaCreate,
    EPIEntregaResponse,
    ExportacaoCreate,
    ExportacaoResponse,
    AssinarExportacaoRequest,
    ReprocessarEntradaRequest,
    StatusEventoUpdateRequest,
    TimelineItem,
)
from agricola.caderno.service import (
    CadernoCampoService,
    VisitaTecnicaService,
    EPIEntregaService,
    CadernoExportacaoService,
)
from core.models.auth import Usuario
from core.services.storage_service import StorageService

router = APIRouter(prefix="/caderno", tags=["Caderno de Campo"])

_MODULE = require_module("A1_PLANEJAMENTO")


# ─── Timeline ─────────────────────────────────────────────────────────────────

@router.get("/safra/{safra_id}/timeline", response_model=List[TimelineItem])
async def timeline(
    safra_id: UUID,
    talhao_id: UUID | None = None,
    tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    incluir_excluidas: bool = False,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    svc = CadernoCampoService(session, tenant_id)
    return await svc.timeline(
        safra_id,
        talhao_id=talhao_id,
        tipo=tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
        incluir_excluidas=incluir_excluidas,
    )


@router.get("/timeline", response_model=List[TimelineItem])
async def timeline_global(
    safra_id: UUID | None = None,
    talhao_id: UUID | None = None,
    tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    incluir_excluidas: bool = False,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    """Timeline global cross-safras. Se safra_id não informado, agrega todas as safras ativas."""
    from agricola.safras.models import Safra

    if safra_id:
        # Comportamento normal: timeline de uma safra específica
        svc = CadernoCampoService(session, tenant_id)
        return await svc.timeline(
            safra_id,
            talhao_id=talhao_id,
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            incluir_excluidas=incluir_excluidas,
        )

    # Cross-safras: busca todas as safras ativas do tenant
    svc = CadernoCampoService(session, tenant_id)
    safras = await svc.listar_safras_ativas()

    if not safras:
        return []

    # Agrega timeline de todas as safras
    svc = CadernoCampoService(session, tenant_id)
    todos_items = []
    for safra in safras:
        items = await svc.timeline(
            safra.id,
            talhao_id=talhao_id,
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            incluir_excluidas=incluir_excluidas,
        )
        todos_items.extend(items)

    # Ordena por data desc
    todos_items.sort(key=lambda x: x.data_registro, reverse=True)
    return todos_items


# ─── Alertas ──────────────────────────────────────────────────────────────────

@router.get("/alertas")
async def caderno_alertas(
    safra_id: UUID | None = None,
    dias_sem_registro: int = 7,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    """Retorna safras ativas sem registros há X dias (padrão: 7 dias, configurável)."""
    svc = CadernoCampoService(session, tenant_id)
    return await svc.listar_alertas(safra_id=safra_id, dias_sem_registro=dias_sem_registro)


# ─── Entradas ─────────────────────────────────────────────────────────────────

@router.post("/entradas", response_model=EntradaResponse, status_code=status.HTTP_201_CREATED)
async def criar_entrada(
    dados: EntradaCreate,
    request: Request,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "operador", "gerente"])),
):
    svc = CadernoCampoService(session, tenant_id, user_id=UUID(user["sub"]), ip_address=request.client.host if request.client else None)
    usuario_id = UUID(user["sub"])
    ip = request.client.host if request.client else None
    entrada = await svc.criar_entrada(dados, usuario_id=usuario_id, ip=ip)
    await session.commit()
    await session.refresh(entrada)
    return EntradaResponse.model_validate(entrada)


@router.get("/entradas/{entrada_id}", response_model=EntradaResponse)
async def detalhar_entrada(
    entrada_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    svc = CadernoCampoService(session, tenant_id)
    return EntradaResponse.model_validate(await svc.get_or_fail(entrada_id))


@router.patch("/entradas/{entrada_id}", response_model=EntradaResponse)
async def atualizar_entrada(
    entrada_id: UUID,
    dados: EntradaUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "gerente"])),
):
    svc = CadernoCampoService(session, tenant_id, user_id=UUID(user["sub"]))
    entrada_atual = await svc.get_or_fail(entrada_id)
    payload = dados.model_dump(exclude_none=True)
    if "status_evento" in payload:
        if payload["status_evento"] != entrada_atual.status_evento:
            raise BusinessRuleError("Use o endpoint /entradas/{id}/status para alterar o status do evento.")
        payload.pop("status_evento", None)
    entrada = await svc.update(entrada_id, payload)
    await session.commit()
    await session.refresh(entrada)
    return EntradaResponse.model_validate(entrada)


@router.patch("/{entrada_id}/status", response_model=EntradaResponse)
@router.patch("/entradas/{entrada_id}/status", response_model=EntradaResponse)
async def alterar_status_entrada(
    entrada_id: UUID,
    body: StatusEventoUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "gerente"])),
):
    svc = CadernoCampoService(session, tenant_id, user_id=UUID(user["sub"]), ip_address=request.client.host if request.client else None)
    entrada = await svc.alterar_status_evento(
        entrada_id,
        novo_status=body.status_evento,
        justificativa=body.justificativa,
        usuario_id=UUID(user["sub"]),
        usuario_role=user.get("role"),
        ip=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(entrada)
    return EntradaResponse.model_validate(entrada)


@router.delete("/entradas/{entrada_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_entrada(
    entrada_id: UUID,
    body: EntradaDeleteRequest,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo"])),
):
    svc = CadernoCampoService(session, tenant_id, user_id=UUID(user["sub"]))
    await svc.soft_delete(entrada_id, body.motivo_exclusao)
    await session.commit()


@router.post("/entradas/{entrada_id}/reprocessar", response_model=EntradaResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{entrada_id}/reprocessar", response_model=EntradaResponse, status_code=status.HTTP_201_CREATED)
async def reprocessar_entrada(
    entrada_id: UUID,
    body: ReprocessarEntradaRequest,
    request: Request,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "gerente"])),
):
    svc = CadernoCampoService(session, tenant_id, user_id=UUID(user["sub"]), ip_address=request.client.host if request.client else None)
    entrada = await svc.reprocessar_entrada(
        entrada_id,
        motivo=body.motivo,
        dados_corrigidos=body.dados_corrigidos,
        usuario_id=UUID(user["sub"]),
        usuario_role=user.get("role"),
        ip=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(entrada)
    return EntradaResponse.model_validate(entrada)


@router.post("/entradas/{entrada_id}/fotos", response_model=FotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_foto_entrada(
    entrada_id: UUID,
    file: UploadFile = File(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "operador", "gerente"])),
):
    """Upload de foto para uma entrada do caderno. Armazena metadados; arquivo vai para storage local/S3."""
    # Verifica se entrada existe e pertence ao tenant
    svc = CadernoCampoService(session, tenant_id)
    entrada = await svc.get_or_fail(entrada_id)

    import uuid as _uuid
    from datetime import datetime as _dt

    from pathlib import Path
    ext = Path(file.filename or "").suffix or ".jpg"
    filename = f"{_uuid.uuid4()}{ext}"
    storage_path = f"static/fotos_caderno/{filename}"

    content = await file.read()
    StorageService.save_blob(content, storage_path)
    url = StorageService.public_url(storage_path)

    foto = await svc.adicionar_foto(
        entrada_id=entrada_id,
        url=url,
        latitude=latitude,
        longitude=longitude,
        data_captura=_dt.now(),
    )

    # Rastreia uso de storage do tenant
    from core.services.storage_service import increment_storage
    await increment_storage(session, tenant_id, len(content))

    await session.commit()
    return FotoResponse.model_validate(foto)


# ─── Visitas Técnicas ─────────────────────────────────────────────────────────

@router.post("/visitas", response_model=VisitaTecnicaResponse, status_code=status.HTTP_201_CREATED)
async def criar_visita(
    dados: VisitaTecnicaCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo"])),
):
    svc = VisitaTecnicaService(session, tenant_id)
    visita = await svc.criar(dados, usuario_id=UUID(user["sub"]))
    await session.commit()
    await session.refresh(visita)
    return VisitaTecnicaResponse.model_validate(visita)


@router.get("/visitas/safra/{safra_id}", response_model=List[VisitaTecnicaResponse])
async def listar_visitas(
    safra_id: UUID,
    talhao_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    svc = VisitaTecnicaService(session, tenant_id)
    return [VisitaTecnicaResponse.model_validate(v) for v in await svc.listar_por_safra(safra_id, talhao_id)]


@router.post("/visitas/{visita_id}/assinar", response_model=VisitaTecnicaResponse)
async def assinar_visita(
    visita_id: UUID,
    body: AssinarVisitaRequest,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo"])),
):
    svc = VisitaTecnicaService(session, tenant_id)
    visita = await svc.assinar(visita_id, body.nome_rt, body.crea)
    await session.commit()
    return VisitaTecnicaResponse.model_validate(visita)


# ─── EPIs ──────────────────────────────────────────────────────────────────────

@router.post("/epis", response_model=EPIEntregaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_epi(
    dados: EPIEntregaCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    user: dict = Depends(require_role(["admin", "agronomo", "gerente"])),
):
    svc = EPIEntregaService(session, tenant_id)
    epi = await svc.criar(dados)
    await session.commit()
    await session.refresh(epi)
    return EPIEntregaResponse.model_validate(epi)


@router.get("/epis", response_model=List[EPIEntregaResponse])
async def listar_epis(
    operacao_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
):
    svc = EPIEntregaService(session, tenant_id)
    return [EPIEntregaResponse.model_validate(e) for e in await svc.listar(operacao_id)]


# ─── Exportação PDF ───────────────────────────────────────────────────────────

@router.post("/exportar", response_model=ExportacaoResponse, status_code=status.HTTP_201_CREATED)
async def exportar_caderno(
    dados: ExportacaoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
    user: dict = Depends(require_role(["admin", "agronomo", "gerente", "proprietario"])),
):
    svc = CadernoExportacaoService(session, tenant_id)
    exportacao = await svc.gerar(dados)
    await session.commit()
    await session.refresh(exportacao)
    return ExportacaoResponse.model_validate(exportacao)


@router.get("/exportacoes/safra/{safra_id}", response_model=List[ExportacaoResponse])
async def listar_exportacoes(
    safra_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = CadernoExportacaoService(session, tenant_id)
    return [ExportacaoResponse.model_validate(e) for e in await svc.listar_por_safra(safra_id)]


@router.get("/exportacoes", response_model=List[ExportacaoResponse])
async def listar_exportacoes_global(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    """Lista todas as exportações do tenant, cross-safras."""
    svc = CadernoExportacaoService(session, tenant_id)
    return [ExportacaoResponse.model_validate(e) for e in await svc.listar_todas()]


@router.get("/exportacoes/{exportacao_id}/download")
async def download_pdf(
    exportacao_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    """Download do PDF do caderno de campo."""
    svc = CadernoExportacaoService(session, tenant_id)
    exportacao = await svc.get_or_fail(exportacao_id)

    from urllib.parse import urlparse
    parsed = urlparse(exportacao.url_pdf)
    storage_path = parsed.path.lstrip("/") if parsed.scheme else exportacao.url_pdf.lstrip("/")
    if not storage_path:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PDF não encontrado. Gere novamente.")

    try:
        pdf_bytes = StorageService.read(storage_path)
    except FileNotFoundError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PDF não encontrado. Gere novamente.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Caderno_Campo_{exportacao.safra_id}.pdf"',
            "X-Documental-Hash": exportacao.hash_documental or "",
            "X-Documental-Mode": exportacao.modo_exportacao,
        },
    )


@router.post("/exportacoes/{exportacao_id}/assinar", response_model=ExportacaoResponse)
async def assinar_exportacao(
    exportacao_id: UUID,
    body: AssinarExportacaoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
    user_claims: dict = Depends(require_role(["admin", "agronomo"])),
    usuario: Usuario = Depends(get_current_user),
):
    """Registra assinatura do RT na exportação do caderno."""
    from datetime import date, timedelta
    svc = CadernoExportacaoService(session, tenant_id)

    # Validação do CREA: verifica se está vencido ou vencendo em 30 dias
    if body.crea_validade:
        hoje = date.today()
        dias_para_vencer = (body.crea_validade - hoje).days
        if dias_para_vencer < 0:
            raise BusinessRuleError(
                f"O CREA informado está vencido desde {body.crea_validade.strftime('%d/%m/%Y')}. "
                "Renove o registro antes de assinar."
            )
        elif dias_para_vencer <= 30:
            raise BusinessRuleError(
                f"O CREA informado vence em {dias_para_vencer} dias ({body.crea_validade.strftime('%d/%m/%Y')}). "
                "Renove o registro antes de assinar."
            )
    if not body.crea_rt:
        raise BusinessRuleError("Informe o CREA para assinar a exportação.")

    if body.responsavel_tecnico_id and body.responsavel_tecnico_id != usuario.id:
        raise BusinessRuleError("O responsável técnico informado deve ser o usuário autenticado.")

    exportacao = await svc.registrar_assinatura(
        exportacao_id,
        usuario=usuario,
        responsavel_tecnico_id=body.responsavel_tecnico_id or usuario.id,
        responsavel_tecnico_nome=body.responsavel_tecnico_nome or body.assinado_por,
        crea_rt=body.crea_rt,
        crea_validade=body.crea_validade,
        observacao=body.observacao,
        assinatura_origem="WEB_SESSION",
        ip_address=request.client.host if request and request.client else None,
    )
    await session.commit()
    await session.refresh(exportacao)
    return ExportacaoResponse.model_validate(exportacao)


@router.post("/exportacoes/assinar-ultima", response_model=ExportacaoResponse)
async def assinar_ultima_exportacao(
    body: AssinarExportacaoRequest,
    request: Request,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(_MODULE),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
    user_claims: dict = Depends(require_role(["admin", "agronomo"])),
    usuario: Usuario = Depends(get_current_user),
):
    """Assina a última exportação de uma safra. Cria uma nova se não existir."""
    from datetime import date as _date
    from agricola.caderno.schemas import ExportacaoCreate

    if not body.safra_id:
        raise BusinessRuleError("Informe a safra para assinar a última exportação.")
    safra_id = body.safra_id

    # Validação do CREA: verifica se está vencido ou vencendo em 30 dias
    if body.crea_validade:
        hoje = _date.today()
        dias_para_vencer = (body.crea_validade - hoje).days
        if dias_para_vencer < 0:
            raise BusinessRuleError(
                f"O CREA informado está vencido desde {body.crea_validade.strftime('%d/%m/%Y')}. "
                "Renove o registro antes de assinar."
            )
        elif dias_para_vencer <= 30:
            raise BusinessRuleError(
                f"O CREA informado vence em {dias_para_vencer} dias ({body.crea_validade.strftime('%d/%m/%Y')}). "
                "Renove o registro antes de assinar."
            )
    if not body.crea_rt:
        raise BusinessRuleError("Informe o CREA para assinar a exportação.")

    svc = CadernoExportacaoService(session, tenant_id)
    exportacoes = await svc.listar_por_safra(safra_id)

    if exportacoes:
        # Usa a mais recente
        exportacao = exportacoes[0]
    else:
        # Cria uma nova exportação placeholder
        exportacao = await svc.gerar(ExportacaoCreate(safra_id=safra_id, modo_exportacao="OFICIAL"))

    exportacao = await svc.registrar_assinatura(
        exportacao.id,
        usuario=usuario,
        responsavel_tecnico_id=body.responsavel_tecnico_id,
        responsavel_tecnico_nome=body.responsavel_tecnico_nome or body.assinado_por,
        crea_rt=body.crea_rt,
        crea_validade=body.crea_validade,
        observacao=body.observacao,
        assinatura_origem="WEB_SESSION",
        ip_address=request.client.host if request and request.client else None,
    )
    await session.commit()
    await session.refresh(exportacao)
    return ExportacaoResponse.model_validate(exportacao)
