import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from core.dependencies import get_session, get_tenant_id
from automacoes.service import AutomacoesService

router = APIRouter(prefix="/automacoes", tags=["Automações"])


class ResultadoResponse(BaseModel):
    acoes_criadas: int
    notificacoes_criadas: int
    mensagem: str
    detalhes: list[str] = []
    regras_disparadas: list[str] = []


class ExecucaoResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    safra_id: uuid.UUID
    status: str
    acoes_criadas: int
    notificacoes_criadas: int
    regras_disparadas: list[str]
    mensagem: str
    executado_por: Optional[uuid.UUID] = None
    created_at: datetime


class ConfiguracaoResponse(BaseModel):
    regra: str
    titulo: str
    descricao: str
    ativa: bool
    frequencia: str = "MANUAL"
    proxima_execucao: Optional[datetime] = None


class ConfiguracaoUpdate(BaseModel):
    ativa: bool
    frequencia: Optional[str] = None


@router.post("/executar", response_model=ResultadoResponse)
async def executar_automacoes(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AutomacoesService(session, tenant_id)
    resultado = await svc.executar(safra_id)
    return ResultadoResponse(
        acoes_criadas=resultado.acoes_criadas,
        notificacoes_criadas=resultado.notificacoes_criadas,
        mensagem=resultado.mensagem,
        detalhes=resultado.detalhes,
        regras_disparadas=resultado.regras_disparadas,
    )


@router.get("/execucoes", response_model=list[ExecucaoResponse])
async def listar_execucoes(
    safra_id: uuid.UUID = Query(...),
    limit: int = Query(20, ge=1, le=50),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AutomacoesService(session, tenant_id)
    return await svc.listar_execucoes(safra_id, limit=limit)


@router.get("/configuracoes", response_model=list[ConfiguracaoResponse])
async def listar_configuracoes(
    safra_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AutomacoesService(session, tenant_id)
    configs = await svc.listar_configuracoes(safra_id)
    return [
        ConfiguracaoResponse(
            regra=c.regra, titulo=c.titulo, descricao=c.descricao,
            ativa=c.ativa, frequencia=c.frequencia, proxima_execucao=c.proxima_execucao,
        )
        for c in configs
    ]


@router.patch("/configuracoes/{regra}", response_model=ConfiguracaoResponse)
async def atualizar_configuracao(
    regra: str,
    body: ConfiguracaoUpdate,
    safra_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AutomacoesService(session, tenant_id)
    cfg = await svc.atualizar_configuracao(regra, body.ativa, safra_id, frequencia=body.frequencia)
    await session.commit()
    return ConfiguracaoResponse(
        regra=cfg.regra, titulo=cfg.titulo, descricao=cfg.descricao,
        ativa=cfg.ativa, frequencia=cfg.frequencia, proxima_execucao=cfg.proxima_execucao,
    )
