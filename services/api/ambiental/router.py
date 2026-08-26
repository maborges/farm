from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.dependencies import get_tenant_id, get_session, require_module_and_permission
from core.exceptions import EntityNotFoundError
from ambiental.models import StatusAlerta, StatusCAR, StatusOutorga, SeveridadeAlerta, TipoAlerta, TipoUsoOutorga, OrigemDadosCAR, SituacaoSICAR
from ambiental.service import AmbientalService
from iot_integracao.new_holland.models import CarbonoEmissao, CarbonoProjeto, CarbonoRelatorio

router = APIRouter(prefix="/ambiental", tags=["Ambiental — Compliance"])

MODULE = "AM1_COMPLIANCE"
MODULE_CARBONO = "AM2_CARBONO"
def _carbono_permission(action: str):
    return require_module_and_permission(MODULE_CARBONO, f"ambiental:carbono:{action}")


# ── Schemas ───────────────────────────────────────────────────────────────────

class CARCreate(BaseModel):
    unidade_produtiva_id: UUID
    imovel_rural_id: UUID
    fazenda_nome: str = Field(..., min_length=1, max_length=200)
    codigo_car: str = Field(..., min_length=1, max_length=50)
    uf: str = Field(..., min_length=2, max_length=2)
    municipio: Optional[str] = Field(None, max_length=100)
    status: StatusCAR = StatusCAR.PENDENTE
    area_total_ha: Optional[float] = None
    area_app_ha: Optional[float] = None
    area_rl_ha: Optional[float] = None
    area_vegetacao_nativa_ha: Optional[float] = None
    area_uso_consolidado_ha: Optional[float] = None
    data_inscricao: Optional[date] = None
    data_atualizacao: Optional[date] = None
    pendencias: Optional[str] = None
    observacoes: Optional[str] = None


class CARUpdate(BaseModel):
    status: Optional[StatusCAR] = None
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
    imovel_rural_id: Optional[UUID]
    unidade_nome: Optional[str] = None
    origem_cadastro: bool = False
    fazenda_nome: str
    codigo_car: str
    origem_dados: OrigemDadosCAR = OrigemDadosCAR.MANUAL
    situacao_sicar: SituacaoSICAR = SituacaoSICAR.NAO_CONSULTADO
    data_ultima_consulta_sicar: Optional[date] = None
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
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class AlertaCreate(BaseModel):
    unidade_produtiva_id: UUID
    fazenda_nome: Optional[str] = Field(None, max_length=200)
    tipo: TipoAlerta = TipoAlerta.DESMATAMENTO
    severidade: SeveridadeAlerta = SeveridadeAlerta.MEDIA
    area_ha: Optional[float] = Field(None, ge=0)
    descricao: Optional[str] = None
    fonte: Optional[str] = None
    talhao_nome: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    data_deteccao: Optional[date] = None


class AlertaUpdate(BaseModel):
    status: Optional[StatusAlerta] = None
    severidade: Optional[SeveridadeAlerta] = None
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
    unidade_produtiva_id: UUID
    fazenda_nome: Optional[str] = None
    numero_outorga: str = Field(..., min_length=1, max_length=100)
    orgao_emissor: Optional[str] = None
    tipo_uso: TipoUsoOutorga = TipoUsoOutorga.IRRIGACAO
    corpo_hidrico: Optional[str] = None
    vazao_outorgada_ls: Optional[float] = Field(None, ge=0)
    vazao_outorgada_m3h: Optional[float] = Field(None, ge=0)
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    observacoes: Optional[str] = None


class OutorgaUpdate(BaseModel):
    status: Optional[StatusOutorga] = None
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


class CarbonoPeriodoQuery(BaseModel):
    periodo_inicio: date
    periodo_fim: date

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.periodo_fim < self.periodo_inicio:
            raise ValueError("O período final deve ser igual ou posterior ao período inicial.")
        return self


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


class ContextoFundiarioResponse(BaseModel):
    imovel_rural_id: UUID
    nome: str
    uf: Optional[str] = None
    municipio: Optional[str] = None
    area_total_ha: Optional[float] = None
    area_app_ha: Optional[float] = None
    area_rl_ha: Optional[float] = None
    car_numero: Optional[str] = None
    ccir_numero: Optional[str] = None
    nirf: Optional[str] = None
    numero_matricula: Optional[str] = None
    sigef_codigo: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContextoFundiarioConsolidadoResponse(ContextoFundiarioResponse):
    unidade_produtiva_id: UUID
    unidade_nome: str


# ── CAR ───────────────────────────────────────────────────────────────────────

@router.get(
    "/contexto-fundiario",
    response_model=List[ContextoFundiarioConsolidadoResponse],
)
async def contexto_fundiario_consolidado(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:car:list")),
):
    """Expose fundiario data for the consolidated Ambiental views."""
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_contexto_fundiario_consolidado()

@router.get(
    "/unidades/{unidade_produtiva_id}/contexto-fundiario",
    response_model=List[ContextoFundiarioResponse],
)
async def contexto_fundiario_unidade(
    unidade_produtiva_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:dashboard:view")),
):
    """Expose official rural-property identifiers for the selected farm."""
    svc = AmbientalService(session, tenant_id)
    try:
        imoveis = await svc.listar_contexto_fundiario(unidade_produtiva_id)
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unidade produtiva não encontrada.")
    return [
        ContextoFundiarioResponse(
            imovel_rural_id=imovel.id,
            nome=imovel.nome,
            uf=imovel.uf,
            municipio=imovel.municipio,
            area_total_ha=float(imovel.area_total_ha) if imovel.area_total_ha is not None else None,
            area_app_ha=float(imovel.area_app_ha) if imovel.area_app_ha is not None else None,
            area_rl_ha=float(imovel.area_rl_ha) if imovel.area_rl_ha is not None else None,
            car_numero=imovel.car_numero,
            ccir_numero=imovel.ccir_numero,
            nirf=imovel.nirf,
            numero_matricula=imovel.numero_matricula,
            sigef_codigo=imovel.sigef_codigo,
        )
        for imovel in imoveis
    ]

@router.get("/dashboard", response_model=DashboardAmbientalResponse)
async def dashboard_ambiental(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:dashboard:view")),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.dashboard()


@router.get("/car", response_model=List[CARResponse])
async def listar_cars(
    status_filter: Optional[StatusCAR] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:car:list")),
):
    svc = AmbientalService(session, tenant_id)
    cars = await svc.listar_cars(status_filter=status_filter)
    await session.commit()
    return cars


@router.post("/car", response_model=CARResponse, status_code=status.HTTP_201_CREATED)
async def criar_car(
    dados: CARCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:car:create")),
):
    svc = AmbientalService(session, tenant_id)
    try:
        car = await svc.criar_car(dados.model_dump(exclude_none=True))
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unidade produtiva não encontrada.")
    await session.commit()
    # O objeto já foi validado e recebeu flush antes do commit. Evitamos um
    # refresh pós-commit porque SET LOCAL é encerrado pelo commit e uma nova
    # leitura sem reativar o contexto RLS seria bloqueada pela política do
    # tenant.
    return car


@router.patch("/car/{car_id}", response_model=CARResponse)
async def atualizar_car(
    car_id: UUID,
    dados: CARUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:car:edit")),
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
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:car:delete")),
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
    status_filter: Optional[list[StatusAlerta]] = Query(None, alias="status"),
    severidade: Optional[SeveridadeAlerta] = Query(None),
    tipo: Optional[TipoAlerta] = Query(None),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:monitoramento:list")),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_alertas(status_filter=status_filter, severidade=severidade, tipo=tipo)


@router.post("/alertas", response_model=AlertaResponse, status_code=status.HTTP_201_CREATED)
async def criar_alerta(
    dados: AlertaCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:monitoramento:create")),
):
    svc = AmbientalService(session, tenant_id)
    try:
        alerta = await svc.criar_alerta(dados.model_dump(exclude_none=True))
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unidade produtiva não encontrada.")
    await session.commit()
    await session.refresh(alerta)
    return alerta


@router.patch("/alertas/{alerta_id}", response_model=AlertaResponse)
async def atualizar_alerta(
    alerta_id: UUID,
    dados: AlertaUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:monitoramento:edit")),
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
    status_filter: Optional[StatusOutorga] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:outorgas:list")),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_outorgas(status_filter=status_filter)


@router.post("/outorgas", response_model=OutorgaResponse, status_code=status.HTTP_201_CREATED)
async def criar_outorga(
    dados: OutorgaCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:outorgas:create")),
):
    svc = AmbientalService(session, tenant_id)
    try:
        outorga = await svc.criar_outorga(dados.model_dump(exclude_none=True))
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unidade produtiva não encontrada.")
    await session.commit()
    await session.refresh(outorga)
    return outorga


@router.patch("/outorgas/{outorga_id}", response_model=OutorgaResponse)
async def atualizar_outorga(
    outorga_id: UUID,
    dados: OutorgaUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_module_and_permission(MODULE, "ambiental:outorgas:edit")),
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

@router.get("/carbono/dashboard", response_model=CarbonoResumoResponse, dependencies=[Depends(_carbono_permission("view"))])
async def dashboard_carbono(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    carbono = await svc.dashboard_carbono()
    return carbono


@router.get("/carbono/emissoes", response_model=List[CarbonoEmissaoResponse], dependencies=[Depends(_carbono_permission("list"))])
async def listar_emissoes_carbono(
    escopo: Optional[int] = Query(None, ge=1, le=3),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_emissoes_carbono(escopo=escopo)


@router.post("/carbono/emissoes", response_model=CarbonoEmissaoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_carbono_permission("create"))])
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


@router.get("/carbono/projetos", response_model=List[CarbonoProjetoResponse], dependencies=[Depends(_carbono_permission("list"))])
async def listar_projetos_carbono(
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_projetos_carbono(status_filter=status_filter)


@router.post("/carbono/projetos", response_model=CarbonoProjetoResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_carbono_permission("create"))])
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


@router.get("/carbono/relatorios", response_model=List[CarbonoRelatorioResponse], dependencies=[Depends(_carbono_permission("list"))])
async def listar_relatorios_carbono(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    return await svc.listar_relatorios_carbono()


@router.post("/carbono/relatorios", response_model=CarbonoRelatorioResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(_carbono_permission("create"))])
async def criar_relatorio_carbono(
    periodo: CarbonoPeriodoQuery = Depends(),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    relatorio = await svc.gerar_relatorio_carbono(periodo.periodo_inicio, periodo.periodo_fim)
    await session.commit()
    await session.refresh(relatorio)
    return relatorio


@router.get("/carbono/relatorios/{relatorio_id}/pdf", dependencies=[Depends(_carbono_permission("export"))])
async def exportar_relatorio_carbono_pdf(
    relatorio_id: int,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AmbientalService(session, tenant_id)
    try:
        pdf_bytes = await svc.exportar_pdf_carbono(relatorio_id)
    except EntityNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Relatório de carbono não encontrado.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="carbono_relatorio_{relatorio_id}.pdf"'},
    )
