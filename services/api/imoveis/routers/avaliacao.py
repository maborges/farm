from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_current_tenant, get_current_user, get_session, require_module
from core.models.auth import Usuario
from core.models.tenant import Tenant
from imoveis.models.imovel import MetodoAvaliacaoImovel
from imoveis.services.avaliacao_service import AvaliacaoService

router = APIRouter(prefix="/imoveis/avaliacoes", tags=["Imóveis Rurais — Avaliações"])
MODULE = Modulos.IMOVEIS_AVALIACAO
MODULE_DEPENDENCY = require_module(MODULE)


def _coerce_enum(enum_cls, raw_value: Optional[str], field_name: str):
    if raw_value is None:
        return None

    value = str(raw_value).strip().replace("-", "_").replace(" ", "_")
    candidates = [value, value.upper()]
    for candidate in candidates:
        if candidate in enum_cls.__members__:
            return enum_cls[candidate]

    for member in enum_cls:
        if member.value.lower() == value.lower():
            return member

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Valor inválido para {field_name}: {raw_value}")


class AvaliacaoCreate(BaseModel):
    imovel_id: uuid.UUID
    data_avaliacao: date
    metodo: str = Field(default="LAUDO")
    valor_total: Optional[Decimal] = None
    valor_por_hectare: Optional[Decimal] = None
    valor_terra_nua: Optional[Decimal] = None
    valor_benfeitorias: Optional[Decimal] = None
    valor_lavoura_perene: Optional[Decimal] = None
    moeda: str = Field(default="BRL", min_length=3, max_length=3)
    responsavel: Optional[str] = None
    numero_laudo: Optional[str] = None
    observacoes: Optional[str] = None
    anexos: list[dict] = Field(default_factory=list)


class AvaliacaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    imovel_id: uuid.UUID
    data_avaliacao: datetime
    metodo: MetodoAvaliacaoImovel
    valor_total: Decimal
    valor_por_hectare: Optional[Decimal]
    valor_terra_nua: Optional[Decimal]
    valor_benfeitorias: Optional[Decimal]
    valor_lavoura_perene: Optional[Decimal]
    moeda: str
    responsavel: Optional[str]
    numero_laudo: Optional[str]
    observacoes: Optional[str]
    anexos: Optional[list[dict]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImovelResumoResponse(BaseModel):
    id: uuid.UUID
    nome: str
    municipio: str
    uf: str
    area_total_ha: Decimal

    model_config = ConfigDict(from_attributes=True)


class AvaliacaoResumoResponse(BaseModel):
    imovel: ImovelResumoResponse
    total_avaliacoes: int
    ultima_avaliacao: Optional[AvaliacaoResponse]
    valor_total_atual: Optional[Decimal]
    valor_por_hectare_atual: Optional[Decimal]
    variacao_percentual: Optional[float]
    serie_historica: list[AvaliacaoResponse]
    area_total_ha: Decimal


@router.get("", response_model=list[AvaliacaoResponse], dependencies=[Depends(MODULE_DEPENDENCY)])
async def listar_avaliacoes(
    imovel_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = AvaliacaoService(session)
    return await service.listar_avaliacoes(tenant.id, imovel_id=imovel_id)


@router.post("", response_model=AvaliacaoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MODULE_DEPENDENCY)])
async def criar_avaliacao(
    data: AvaliacaoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = AvaliacaoService(session)

    try:
        avaliacao, _alertas = await service.criar_avaliacao(
            tenant_id=tenant.id,
            imovel_id=data.imovel_id,
            data_avaliacao=datetime.combine(data.data_avaliacao, time.min, tzinfo=timezone.utc),
            metodo=_coerce_enum(MetodoAvaliacaoImovel, data.metodo, "metodo"),
            valor_total=data.valor_total,
            valor_por_hectare=data.valor_por_hectare,
            valor_terra_nua=data.valor_terra_nua,
            valor_benfeitorias=data.valor_benfeitorias,
            valor_lavoura_perene=data.valor_lavoura_perene,
            moeda=data.moeda.upper(),
            responsavel=data.responsavel,
            numero_laudo=data.numero_laudo,
            observacoes=data.observacoes,
            anexos=data.anexos,
            created_by=user.id,
        )
        await session.commit()
        await session.refresh(avaliacao)
        return avaliacao
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{imovel_id}/resumo", response_model=AvaliacaoResumoResponse, dependencies=[Depends(MODULE_DEPENDENCY)])
async def obter_resumo(
    imovel_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = AvaliacaoService(session)
    try:
        resumo = await service.get_resumo_imovel(tenant.id, imovel_id)
        return resumo
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{imovel_id}/export/pdf", dependencies=[Depends(MODULE_DEPENDENCY)])
async def exportar_pdf(
    imovel_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = AvaliacaoService(session)
    try:
        pdf_bytes = await service.gerar_pdf_historico(tenant.id, imovel_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="avaliacao_imovel_{imovel_id}.pdf"'},
    )
