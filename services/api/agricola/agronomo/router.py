from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.constants import PlanTier
from core.dependencies import get_tenant_id, require_module, get_current_user_claims, require_tier
from core.dependencies import get_session_with_tenant
from core.cadastros.propriedades.models import AreaRural
from agricola.agronomo.schemas import (
    MensagemCreate,
    RespostaIA,
    ConversaResponse,
    RelatorioTecnicoCreate,
    RelatorioTecnicoUpdate,
    RelatorioTecnicoResponse,
)
from agricola.agronomo.service import AgronomoService, RelatorioTecnicoService

router = APIRouter(prefix="/agronomo", tags=["Agrônomo Virtual (IA/Ollama)"])


async def _enriquecer_talhao_nome(session: AsyncSession, rats: list):
    talhao_ids = {rat.talhao_id for rat in rats if getattr(rat, "talhao_id", None)}
    if not talhao_ids:
        return [RelatorioTecnicoResponse.model_validate(rat) for rat in rats]

    stmt = select(AreaRural.id, AreaRural.nome).where(AreaRural.id.in_(talhao_ids))
    result = await session.execute(stmt)
    talhoes = {talhao_id: nome for talhao_id, nome in result.all()}

    return [
        RelatorioTecnicoResponse.model_validate(rat).model_copy(
            update={"talhao_nome": talhoes.get(rat.talhao_id)}
        )
        for rat in rats
    ]

@router.post("/chat", response_model=RespostaIA)
async def conversar_com_ia(
    dados: MensagemCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = AgronomoService(session, tenant_id)
    usuario_id = UUID(claims.get("sub"))
    resposta = await svc.enviar_mensagem(usuario_id, dados)
    return RespostaIA(**resposta)

@router.get("/conversas", response_model=List[ConversaResponse])
async def listar_conversas(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = AgronomoService(session, tenant_id)
    usuario_id = UUID(claims.get("sub"))
    conversas = await svc.list_all(usuario_id=usuario_id)
    return [ConversaResponse.model_validate(c) for c in conversas]

@router.get("/rat", response_model=List[RelatorioTecnicoResponse])
async def listar_rats(
    safra_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = RelatorioTecnicoService(session, tenant_id)
    if safra_id:
        rats = await svc.listar_por_safra(safra_id)
    else:
        rats = await svc.list_all()
    return await _enriquecer_talhao_nome(session, rats)

@router.post("/rat", response_model=RelatorioTecnicoResponse, status_code=status.HTTP_201_CREATED)
async def criar_rat(
    dados: RelatorioTecnicoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = RelatorioTecnicoService(session, tenant_id)
    usuario_id = UUID(claims.get("sub"))
    rat = await svc.criar_rat(usuario_id, dados)
    return (await _enriquecer_talhao_nome(session, [rat]))[0]

@router.get("/rat/{rat_id}", response_model=RelatorioTecnicoResponse)
async def obter_rat(
    rat_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = RelatorioTecnicoService(session, tenant_id)
    rat = await svc.get_or_fail(rat_id)
    return (await _enriquecer_talhao_nome(session, [rat]))[0]

@router.patch("/rat/{rat_id}", response_model=RelatorioTecnicoResponse)
async def atualizar_rat(
    rat_id: UUID,
    dados: RelatorioTecnicoUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = RelatorioTecnicoService(session, tenant_id)
    rat = await svc.atualizar_rat(rat_id, dados)
    return (await _enriquecer_talhao_nome(session, [rat]))[0]
