from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field

from core.dependencies import get_tenant_id, get_session, require_module
from core.exceptions import EntityNotFoundError
from ambiental.service import AmbientalService
from iot_integracao.new_holland.models import CarbonoEmissao, CarbonoProjeto, CarbonoRelatorio

router = APIRouter(prefix="/ambiental", tags=["Ambiental — Compliance"])

MODULE = "AM1_COMPLIANCE"
MODULE_CARBONO = "AM2_CARBONO"
MODULE_CARBONO_DEPENDENCY = require_module(MODULE_CARBONO)


# ── Schemas ───────────────────────────────────────────────────────────────────

class CARCreate(BaseModel):
    fazenda_nome: str
    codigo_car: str
    uf: str
    municipio: Optional[str] = None
    status: str = "PENDENTE"
    area_total_ha: Optional[float] = None
    area_app_ha: Optional[float] = None
    area_rl_ha: Optional[float] = None
    area_vegetacao_nativa_ha: Optional[float] = None
    area_uso_consolidado_ha: Optional[float] = None
    data_inscricao: Optional[date] = None
    data_atualizacao: Optional[date] = None
    pendencias: Optional[str] = None
    observacoes: Optional[str] = None
    unidade_produtiva_id: Optional[UUID] = None


class CARUpdate(BaseModel):
    status: Optional[str] = None
    area_total_ha: Optional[float] = None
    area_app_ha: Optional[float] = None
    area_rl_ha: Optional[float] = None
    area_vegetacao_nativa_ha: Optional[float] = None
    area_uso_consolidado_ha: Optional[float] = None
    data_atualizacao: Optional[date] = None
    pendencias: Optional[str] = None
    observacoes: Optional[str] = None


class CARResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID]
    fazenda_nome: str
    codigo_car: str
    uf: str
    municipio: Optional[str]
    status: str
    area_total_ha: Optional[float]
    area_app_ha: Optional[float]
    area_rl_ha: Optional[float]
    area_vegetacao_nativa_ha: Optional[float]
    area_uso_consolidado_ha: Optional[float]
    data_inscricao: Optional[date]
    data_atualizacao: Optional[date]
    pendencias: Optional[str]
    observacoes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AlertaCreate(BaseModel):
    fazenda_nome: Optional[str] = None
    unidade_produtiva_id: Optional[UUID] = None
    tipo: str = "DESMATAMENTO"
    severidade: str = "MEDIA"
    area_ha: Optional[float] = None
    descricao: Optional[str] = None
    fonte: Optional[str] = None
    talhao_nome: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    data_deteccao: Optional[date] = None


class AlertaUpdate(BaseModel):
    status: Optional[str] = None
    severidade: Optional[str] = None
    data_resolucao: Optional[date] = None
    resolucao_descricao: Optional[str] = None


class AlertaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID]
    fazenda_nome: Optional[str]
    tipo: str
    severidade: str
    status: str
    area_ha: Optional[float]
    descricao: Optional[str]
    fonte: Optional[str]
    talhao_nome: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    data_deteccao: date
    data_resolucao: Optional[date]
    resolucao_descricao: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OutorgaCreate(BaseModel):
    fazenda_nome: Optional[str] = None
    unidade_produtiva_id: Optional[UUID] = None
    numero_outorga: str
    orgao_emissor: Optional[str] = None
    tipo_uso: str = "IRRIGACAO"
    corpo_hidrico: Optional[str] = None
    vazao_outorgada_ls: Optional[float] = None
    vazao_outorgada_m3h: Optional[float] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None


class OutorgaUpdate(BaseModel):
    status: Optional[str] = None
    vazao_outorgada_ls: Optional[float] = None
    vazao_outorgada_m3h: Optional[float] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class OutorgaResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID]
    fazenda_nome: Optional[str]
    numero_outorga: str
    orgao_emissor: Optional[str]
    tipo_uso: str
    corpo_hidrico: Optional[str]
    vazao_outorgada_ls: Optional[float]
    vazao_outorgada_m3h: Optional[float]
    status: str
    data_emissao: Optional[date]
    data_vencimento: Optional[date]
    observacoes: Optional[str]
    ativo: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DashboardAmbientalResponse(BaseModel):
    total_cars: int
    cars_ativos: int
    cars_pendentes: int
    total_alertas_abertos: int
    alertas_criticos: int
    total_outorgas: int
    outorgas_vencendo: int


class CarbonoEmissaoCreate(BaseModel):
    unidade_produtiva_id: Optional[UUID] = None
    escopo: int = Field(..., ge=1, le=3)
    categoria: str
    fonte: Optional[str] = None
    atividade: Optional[str] = None
    quantidade: float = Field(..., gt=0)
    unidade: str
    fator_emissao: Optional[float] = None
    fator_emissao_referencia: Optional[str] = None
    data_referencia: datetime
    observacoes: Optional[str] = None
    arquivo_comprovante: Optional[str] = None
    created_by: Optional[UUID] = None


class CarbonoEmissaoResponse(BaseModel):
    id: int
    tenant_id: str
    unidade_produtiva_id: Optional[UUID]
    escopo: int
    categoria: str
    fonte: Optional[str]
    atividade: Optional[str]
    quantidade: float
    unidade: str
    fator_emissao: Optional[float]
    fator_emissao_referencia: Optional[str]
    total_co2e: Optional[float]
    data_referencia: datetime
    observacoes: Optional[str]
    arquivo_comprovante: Optional[str]
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CarbonoProjetoCreate(BaseModel):
    unidade_produtiva_id: Optional[UUID] = None
    nome: str
    descricao: Optional[str] = None
    tipo: str
    metodologia: Optional[str] = None
    area_ha: float = Field(..., gt=0)
    geometria: Optional[dict] = None
    creditos_estimados: Optional[float] = None
    creditos_verificados: Optional[float] = None
    creditos_vendidos: Optional[float] = None
    status: str = "planejamento"
    data_inicio: Optional[date] = None
    data_verificacao: Optional[date] = None
    data_certificacao: Optional[date] = None
    certificador: Optional[str] = None
    numero_registro: Optional[str] = None
    padrao: Optional[str] = None


class CarbonoProjetoResponse(BaseModel):
    id: int
    tenant_id: str
    unidade_produtiva_id: Optional[int]
    nome: str
    descricao: Optional[str]
    tipo: str
    metodologia: Optional[str]
    area_ha: float
    geometria: Optional[dict]
    creditos_estimados: Optional[float]
    creditos_verificados: Optional[float]
    creditos_vendidos: Optional[float]
    status: str
    data_inicio: Optional[date]
    data_verificacao: Optional[date]
    data_certificacao: Optional[date]
    certificador: Optional[str]
    numero_registro: Optional[str]
    padrao: Optional[str]
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CarbonoRelatorioResponse(BaseModel):
    id: int
    tenant_id: str
    periodo_inicio: datetime
    periodo_fim: datetime
    escopo_1_total: Optional[float]
    escopo_2_total: Optional[float]
    escopo_3_total: Optional[float]
    total_geral: Optional[float]
    creditos_gerados: Optional[float]
    saldo_liquido: Optional[float]
    intensidade_carbono: Optional[float]
    unidade_producao: Optional[str]
    total_produzido: Optional[float]
    status: Optional[str]
    arquivo_pdf: Optional[str]
    created_at: Optional[datetime]
    published_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CarbonoResumoResponse(BaseModel):
    total_emissoes: float
    total_creditos: float
    saldo_liquido: float
    total_emissoes_registradas: int
    total_projetos: int
    total_relatorios: int
    emissoes_escopo_1: float
    emissoes_escopo_2: float
    emissoes_escopo_3: float


# ── CAR ───────────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardAmbientalResponse)
async def dashboard_ambiental(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.dashboard()


@router.get("/car", response_model=List[CARResponse])
async def listar_cars(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_cars(status_filter=status_filter)


@router.post("/car", response_model=CARResponse, status_code=status.HTTP_201_CREATED)
async def criar_car(
    dados: CARCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    car = await svc.criar_car(dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(car)
    return car


@router.patch("/car/{car_id}", response_model=CARResponse)
async def atualizar_car(
    car_id: UUID,
    dados: CARUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    try:
        car = await svc.atualizar_car(car_id, dados.model_dump(exclude_none=True))
        await session.commit()
        await session.refresh(car)
        return car
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CAR não encontrado.")


@router.delete("/car/{car_id}", status_code=200)
async def excluir_car(
    car_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    try:
        await svc.excluir_car(car_id)
        await session.commit()
        return {"message": "CAR excluído."}
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CAR não encontrado.")


# ── Alertas ───────────────────────────────────────────────────────────────────

@router.get("/alertas", response_model=List[AlertaResponse])
async def listar_alertas(
    status_filter: Optional[str] = Query(None, alias="status"),
    severidade: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_alertas(status_filter=status_filter, severidade=severidade, tipo=tipo)


@router.post("/alertas", response_model=AlertaResponse, status_code=status.HTTP_201_CREATED)
async def criar_alerta(
    dados: AlertaCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    alerta = await svc.criar_alerta(dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(alerta)
    return alerta


@router.patch("/alertas/{alerta_id}", response_model=AlertaResponse)
async def atualizar_alerta(
    alerta_id: UUID,
    dados: AlertaUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    try:
        alerta = await svc.atualizar_alerta(alerta_id, dados.model_dump(exclude_none=True))
        await session.commit()
        await session.refresh(alerta)
        return alerta
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta não encontrado.")


# ── Outorgas ──────────────────────────────────────────────────────────────────

@router.get("/outorgas", response_model=List[OutorgaResponse])
async def listar_outorgas(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_outorgas(status_filter=status_filter)


@router.post("/outorgas", response_model=OutorgaResponse, status_code=status.HTTP_201_CREATED)
async def criar_outorga(
    dados: OutorgaCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    outorga = await svc.criar_outorga(dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(outorga)
    return outorga


@router.patch("/outorgas/{outorga_id}", response_model=OutorgaResponse)
async def atualizar_outorga(
    outorga_id: UUID,
    dados: OutorgaUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module(MODULE)),
):
    svc = AmbientalService(session, tenant_id)
    try:
        outorga = await svc.atualizar_outorga(outorga_id, dados.model_dump(exclude_none=True))
        await session.commit()
        await session.refresh(outorga)
        return outorga
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outorga não encontrada.")


# ── Carbono ───────────────────────────────────────────────────────────────────

@router.get("/carbono/dashboard", response_model=CarbonoResumoResponse, dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def dashboard_carbono(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    carbono = await svc.dashboard_carbono()
    return carbono


@router.get("/carbono/emissoes", response_model=List[CarbonoEmissaoResponse], dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def listar_emissoes_carbono(
    escopo: Optional[int] = Query(None, ge=1, le=3),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_emissoes_carbono(escopo=escopo)


@router.post("/carbono/emissoes", response_model=CarbonoEmissaoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def criar_emissao_carbono(
    dados: CarbonoEmissaoCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    emissao = await svc.registrar_emissao_carbono(dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(emissao)
    return emissao


@router.get("/carbono/projetos", response_model=List[CarbonoProjetoResponse], dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def listar_projetos_carbono(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_projetos_carbono(status_filter=status_filter)


@router.post("/carbono/projetos", response_model=CarbonoProjetoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def criar_projeto_carbono(
    dados: CarbonoProjetoCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    projeto = await svc.criar_projeto_carbono(dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(projeto)
    return projeto


@router.get("/carbono/relatorios", response_model=List[CarbonoRelatorioResponse], dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def listar_relatorios_carbono(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_relatorios_carbono()


@router.post("/carbono/relatorios", response_model=CarbonoRelatorioResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def criar_relatorio_carbono(
    periodo_inicio: date,
    periodo_fim: date,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    relatorio = await svc.gerar_relatorio_carbono(periodo_inicio, periodo_fim)
    await session.commit()
    await session.refresh(relatorio)
    return relatorio


@router.get("/carbono/relatorios/{relatorio_id}/pdf", dependencies=[Depends(MODULE_CARBONO_DEPENDENCY)])
async def exportar_relatorio_carbono_pdf(
    relatorio_id: int,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    pdf_bytes = await svc.exportar_pdf_carbono(relatorio_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="carbono_relatorio_{relatorio_id}.pdf"'},
    )
