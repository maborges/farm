"""
Arrendamentos Rurais - API Routes

Endpoints para gestão de contratos de arrendamento e parceria rural.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_current_tenant, get_current_user, get_session, require_module
from core.models.auth import Usuario
from core.models.tenant import Tenant
from imoveis.models.imovel import (
    ContratoArrendamento,
    ParcelaArrendamento,
    Periodicidade,
    StatusContrato,
    StatusParcela,
    TipoArrendatario,
    TipoContrato,
    ValorModalidade,
)
from imoveis.services.arrendamento_service import ArrendamentoService

router = APIRouter(prefix="/imoveis/arrendamentos", tags=["Imóveis Rurais — Arrendamentos"])
MODULE = Modulos.IMOVEIS_ARRENDAMENTOS
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


class ContratoArrendamentoCreate(BaseModel):
    imovel_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    tipo: str = Field(default="arrendamento")
    arrendatario_tipo: str = Field(default="pessoa_fisica")
    area_arrendada_ha: Decimal
    valor_modalidade: str = Field(default="fixo_brl")
    valor: Decimal
    periodicidade: str = Field(default="anual")
    data_inicio: date
    data_fim: date
    dia_vencimento: int = Field(default=10, ge=1, le=28)
    indice_reajuste: Optional[str] = None
    data_reajuste_anual: Optional[date] = None
    commodity_referencia: Optional[str] = None
    arrendatario_pessoa_id: Optional[uuid.UUID] = None
    arrendatario_fazenda_id: Optional[uuid.UUID] = None
    path_contrato_pdf: Optional[str] = None
    registro_cartorio: Optional[str] = None
    clausulas_observacoes: Optional[str] = None


class ReajusteContratoRequest(BaseModel):
    indice_nome: str = Field(..., min_length=1, max_length=50)
    indice_valor: Decimal = Field(..., gt=0)


class RescisaoContratoRequest(BaseModel):
    motivo: str = Field(..., min_length=1)
    data_rescisao: date = Field(default_factory=date.today)


class ParcelaArrendamentoResponse(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    numero_parcela: int
    data_vencimento: date
    valor_centavos: int
    valor_sacas: Optional[Decimal]
    status: StatusParcela
    data_pagamento: Optional[date]
    indice_aplicado: Optional[Decimal]
    observacao: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ImovelResumoResponse(BaseModel):
    id: uuid.UUID
    nome: str
    municipio: str
    uf: str

    model_config = ConfigDict(from_attributes=True)


class ContratoArrendamentoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    imovel_id: uuid.UUID
    unidade_produtiva_id: uuid.UUID
    tipo: TipoContrato
    arrendatario_tipo: TipoArrendatario
    arrendatario_pessoa_id: Optional[uuid.UUID]
    arrendatario_fazenda_id: Optional[uuid.UUID]
    area_arrendada_ha: Decimal
    valor_modalidade: ValorModalidade
    valor: Decimal
    commodity_referencia: Optional[str]
    periodicidade: Periodicidade
    data_inicio: date
    data_fim: date
    dia_vencimento: Optional[int]
    indice_reajuste: Optional[str]
    data_reajuste_anual: Optional[date]
    status: StatusContrato
    motivo_rescisao: Optional[str]
    path_contrato_pdf: Optional[str]
    registro_cartorio: Optional[str]
    clausulas_observacoes: Optional[str]
    imovel: Optional[ImovelResumoResponse] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ResumoContratoArrendamentoResponse(BaseModel):
    contrato: ContratoArrendamentoResponse
    total_parcelas: int
    parcelas_pagas: int
    parcelas_pendentes: int
    parcelas_vencidas: int
    valor_total_centavos: int
    valor_pago_centavos: int
    valor_pendente_centavos: int
    percentual_pago: float


@router.get("", response_model=List[ContratoArrendamentoResponse], dependencies=[Depends(MODULE_DEPENDENCY)])
async def listar_contratos(
    imovel_id: Optional[uuid.UUID] = Query(None),
    status_contrato: Optional[StatusContrato] = Query(None, alias="status"),
    apenas_ativos: bool = Query(False),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    return await service.listar_contratos(
        tenant_id=tenant.id,
        imovel_id=imovel_id,
        status=status_contrato,
        apenas_ativos=apenas_ativos,
    )


@router.get("/parcelas/vencidas", response_model=List[ParcelaArrendamentoResponse], dependencies=[Depends(MODULE_DEPENDENCY)])
async def listar_parcelas_vencidas(
    dias_atraso: int = Query(1, ge=1, le=3650),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    return await service.get_parcelas_vencidas(tenant.id, dias_atraso=dias_atraso)


@router.post("", response_model=ContratoArrendamentoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MODULE_DEPENDENCY)])
async def criar_contrato(
    data: ContratoArrendamentoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)

    try:
        contrato, _alertas = await service.criar_contrato(
            tenant_id=tenant.id,
            imovel_id=data.imovel_id,
            unidade_produtiva_id=data.unidade_produtiva_id,
            tipo=_coerce_enum(TipoContrato, data.tipo, "tipo"),
            arrendatario_tipo=_coerce_enum(TipoArrendatario, data.arrendatario_tipo, "arrendatario_tipo"),
            area_arrendada_ha=data.area_arrendada_ha,
            valor_modalidade=_coerce_enum(ValorModalidade, data.valor_modalidade, "valor_modalidade"),
            valor=data.valor,
            periodicidade=_coerce_enum(Periodicidade, data.periodicidade, "periodicidade"),
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
            dia_vencimento=data.dia_vencimento,
            indice_reajuste=data.indice_reajuste,
            data_reajuste_anual=data.data_reajuste_anual,
            commodity_referencia=data.commodity_referencia,
            arrendatario_pessoa_id=data.arrendatario_pessoa_id,
            arrendatario_fazenda_id=data.arrendatario_fazenda_id,
            path_contrato_pdf=data.path_contrato_pdf,
            registro_cartorio=data.registro_cartorio,
            clausulas_observacoes=data.clausulas_observacoes,
            created_by=user.id,
        )
        await session.commit()
        await session.refresh(contrato)
        return contrato
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{contrato_id}", response_model=ContratoArrendamentoResponse, dependencies=[Depends(MODULE_DEPENDENCY)])
async def obter_contrato(
    contrato_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    contrato = await service.get_contrato_by_id(contrato_id, tenant.id)
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return contrato


@router.get("/{contrato_id}/resumo", response_model=ResumoContratoArrendamentoResponse, dependencies=[Depends(MODULE_DEPENDENCY)])
async def obter_resumo_contrato(
    contrato_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    try:
        return await service.get_resumo_contrato(contrato_id, tenant.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{contrato_id}/reajuste", response_model=ContratoArrendamentoResponse, dependencies=[Depends(MODULE_DEPENDENCY)])
async def aplicar_reajuste(
    contrato_id: uuid.UUID,
    data: ReajusteContratoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    try:
        contrato, _alertas = await service.aplicar_reajuste(
            contrato_id=contrato_id,
            tenant_id=tenant.id,
            indice_nome=data.indice_nome,
            indice_valor=data.indice_valor,
            usuario_id=user.id,
        )
        await session.commit()
        await session.refresh(contrato)
        return contrato
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{contrato_id}/rescindir", response_model=ContratoArrendamentoResponse, dependencies=[Depends(MODULE_DEPENDENCY)])
async def rescindir_contrato(
    contrato_id: uuid.UUID,
    data: RescisaoContratoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = ArrendamentoService(session)
    try:
        contrato, _alertas = await service.rescindir_contrato(
            contrato_id=contrato_id,
            tenant_id=tenant.id,
            motivo=data.motivo,
            data_rescisao=data.data_rescisao,
            usuario_id=user.id,
        )
        await session.commit()
        await session.refresh(contrato)
        return contrato
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
