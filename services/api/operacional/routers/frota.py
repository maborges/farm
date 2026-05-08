from fastapi import APIRouter, Depends, status, UploadFile, File
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PlanTier
from core.dependencies import get_tenant_id, require_module, require_tier
from core.dependencies import get_session_with_tenant
from operacional.schemas.frota_dashboard_detail import FrotaDashboardDetalheResponse
from operacional.schemas.frota_dashboard import FrotaDashboardResponse
from operacional.schemas.frota_custo import (
    FrotaCustoEquipamentoResponse,
    FrotaCustoRankingResponse,
    FrotaCustoResponse,
)
from operacional.schemas.frota_disponibilidade import (
    FrotaDisponibilidadeBloqueioRequest,
    FrotaDisponibilidadeBloqueioResponse,
    FrotaDisponibilidadeEquipamentoResponse,
    FrotaDisponibilidadeResponse,
)
from operacional.schemas.frota_consumo import (
    FrotaConsumoEquipamentoResponse,
    FrotaConsumoRankingResponse,
    FrotaConsumoResponse,
)
from operacional.schemas.frota_jornada import (
    FrotaJornadaCancelarRequest,
    FrotaJornadaCreate,
    FrotaJornadaDetailResponse,
    FrotaJornadaFinalizarRequest,
    FrotaJornadaListResponse,
    FrotaJornadaUpdate,
)
from operacional.schemas.frota_agricultura import (
    FrotaAgriculturaEquipamentoResponse,
    FrotaAgriculturaOperacoesResponse,
    FrotaAgriculturaResponse,
    FrotaAgriculturaSafraResponse,
    FrotaAgriculturaTalhaoResponse,
)
from operacional.schemas.frota_inteligencia import (
    FrotaInteligenciaEquipamentoResponse,
    FrotaInteligenciaResponse,
)
from operacional.schemas.frota_automacao import (
    FrotaRegraInteligenteSchema,
    FrotaRegraInteligenteUpdate,
    FrotaLogAutomacaoSchema,
)
from operacional.schemas.frota_preventiva import (
    FrotaPreventivaEquipamentoResponse,
    FrotaPreventivaListResponse,
    GerarOsPreventivaResponse,
)
from operacional.schemas.frota import (
    MaquinarioCreate, MaquinarioResponse, MaquinarioUpdate,
    PlanoManutencaoCreate, PlanoManutencaoResponse,
    OrdemServicoCreate, OrdemServicoResponse, OrdemServicoUpdate,
    ItemOrdemServicoCreate, ItemOrdemServicoResponse
)
from operacional.services.frota_dashboard_detail_service import FrotaDashboardDetailService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_custo_service import FrotaCustoService
from operacional.services.frota_disponibilidade_service import FrotaDisponibilidadeService
from operacional.services.frota_consumo_service import FrotaConsumoService
from operacional.services.frota_jornada_service import FrotaJornadaService
from operacional.services.frota_inteligencia_service import FrotaInteligenciaService
from operacional.services.frota_agricultura_service import FrotaAgriculturaService
from operacional.services.frota_manutencao_preventiva_service import FrotaManutencaoPreventivaService
from operacional.services.frota_automacao_service import FrotaAutomacaoService
from operacional.services.frota_service import FrotaService
from operacional.services.frota_import_service import FrotaImportService

router = APIRouter(prefix="/frota", tags=["Frota — Maquinários"])


@router.get("/dashboard", response_model=FrotaDashboardResponse)
async def obter_dashboard_executivo(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaDashboardService(session, tenant_id)
    return await svc.obter_dashboard(unidade_produtiva_id=unidade_produtiva_id)


@router.get("/dashboard/equipamentos/{equipamento_id}", response_model=FrotaDashboardDetalheResponse)
async def obter_detalhe_equipamento_dashboard(
    equipamento_id: UUID,
    periodo_dias: int | None = None,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaDashboardDetailService(session, tenant_id)
    return await svc.obter_detalhe_equipamento(
        equipamento_id=equipamento_id,
        periodo_dias=periodo_dias,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/manutencao-preventiva", response_model=FrotaPreventivaListResponse)
async def listar_manutencao_preventiva(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaManutencaoPreventivaService(session, tenant_id)
    return await svc.listar_planos_preventivos(unidade_produtiva_id=unidade_produtiva_id)


@router.get(
    "/manutencao-preventiva/equipamentos/{equipamento_id}",
    response_model=FrotaPreventivaEquipamentoResponse,
)
async def listar_manutencao_preventiva_por_equipamento(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaManutencaoPreventivaService(session, tenant_id)
    return await svc.listar_planos_preventivos_por_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.post("/manutencao-preventiva/{plano_id}/gerar-os", response_model=GerarOsPreventivaResponse)
async def gerar_os_preventiva(
    plano_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaManutencaoPreventivaService(session, tenant_id)
    return await svc.gerar_os_preventiva(
        plano_id=plano_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/consumo", response_model=FrotaConsumoResponse)
async def obter_resumo_consumo(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaConsumoService(session, tenant_id)
    return await svc.obter_resumo_consumo(unidade_produtiva_id=unidade_produtiva_id)


@router.get("/consumo/equipamentos/{equipamento_id}", response_model=FrotaConsumoEquipamentoResponse)
async def obter_consumo_equipamento(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaConsumoService(session, tenant_id)
    return await svc.obter_consumo_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/consumo/ranking", response_model=FrotaConsumoRankingResponse)
async def obter_ranking_eficiencia(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaConsumoService(session, tenant_id)
    return await svc.obter_ranking(unidade_produtiva_id=unidade_produtiva_id)


@router.get("/disponibilidade", response_model=FrotaDisponibilidadeResponse)
async def obter_disponibilidade_operacional(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaDisponibilidadeService(session, tenant_id)
    return await svc.obter_disponibilidade(unidade_produtiva_id=unidade_produtiva_id)


@router.get(
    "/disponibilidade/equipamentos/{equipamento_id}",
    response_model=FrotaDisponibilidadeEquipamentoResponse,
)
async def obter_disponibilidade_equipamento(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaDisponibilidadeService(session, tenant_id)
    return await svc.obter_disponibilidade_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.post(
    "/disponibilidade/equipamentos/{equipamento_id}/bloquear",
    response_model=FrotaDisponibilidadeBloqueioResponse,
)
async def bloquear_equipamento_operacional(
    equipamento_id: UUID,
    dados: FrotaDisponibilidadeBloqueioRequest,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaDisponibilidadeService(session, tenant_id)
    return await svc.bloquear_equipamento(
        equipamento_id=equipamento_id,
        motivo=dados.motivo,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.post(
    "/disponibilidade/equipamentos/{equipamento_id}/liberar",
    response_model=FrotaDisponibilidadeBloqueioResponse,
)
async def liberar_equipamento_operacional(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaDisponibilidadeService(session, tenant_id)
    return await svc.liberar_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/custos", response_model=FrotaCustoResponse)
async def obter_custos_frota(
    periodo_dias: int | None = None,
    unidade_produtiva_id: UUID | None = None,
    tipo_equipamento: str | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaCustoService(session, tenant_id)
    return await svc.obter_custos(
        periodo_dias=periodo_dias,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo_equipamento=tipo_equipamento,
    )


@router.get("/custos/equipamentos/{equipamento_id}", response_model=FrotaCustoEquipamentoResponse)
async def obter_custo_equipamento(
    equipamento_id: UUID,
    periodo_dias: int | None = None,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaCustoService(session, tenant_id)
    return await svc.obter_custo_equipamento(
        equipamento_id=equipamento_id,
        periodo_dias=periodo_dias,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/custos/ranking", response_model=FrotaCustoRankingResponse)
async def obter_ranking_custos(
    periodo_dias: int | None = None,
    unidade_produtiva_id: UUID | None = None,
    tipo_equipamento: str | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaCustoService(session, tenant_id)
    return await svc.obter_ranking(
        periodo_dias=periodo_dias,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo_equipamento=tipo_equipamento,
    )


@router.get("/jornadas", response_model=FrotaJornadaListResponse)
async def listar_jornadas_frota(
    unidade_produtiva_id: UUID | None = None,
    equipamento_id: UUID | None = None,
    status_jornada: str | None = None,
    periodo_dias: int | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.listar_jornadas(
        unidade_produtiva_id=unidade_produtiva_id,
        equipamento_id=equipamento_id,
        status=status_jornada,
        periodo_dias=periodo_dias,
    )


@router.post("/jornadas", response_model=FrotaJornadaDetailResponse, status_code=status.HTTP_201_CREATED)
async def criar_jornada_frota(
    dados: FrotaJornadaCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.criar_jornada(dados)


@router.get("/jornadas/{jornada_id}", response_model=FrotaJornadaDetailResponse)
async def detalhar_jornada_frota(
    jornada_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.obter_jornada(jornada_id)


@router.patch("/jornadas/{jornada_id}", response_model=FrotaJornadaDetailResponse)
async def atualizar_jornada_frota(
    jornada_id: UUID,
    dados: FrotaJornadaUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.atualizar_jornada(jornada_id, dados)


@router.post("/jornadas/{jornada_id}/finalizar", response_model=FrotaJornadaDetailResponse)
async def finalizar_jornada_frota(
    jornada_id: UUID,
    dados: FrotaJornadaFinalizarRequest,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.finalizar_jornada(jornada_id, dados)


@router.post("/jornadas/{jornada_id}/cancelar", response_model=FrotaJornadaDetailResponse)
async def cancelar_jornada_frota(
    jornada_id: UUID,
    dados: FrotaJornadaCancelarRequest | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaJornadaService(session, tenant_id)
    return await svc.cancelar_jornada(jornada_id, dados)


@router.get("/inteligencia", response_model=FrotaInteligenciaResponse)
async def obter_inteligencia_frota(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaInteligenciaService(session, tenant_id)
    return await svc.obter_inteligencia(unidade_produtiva_id=unidade_produtiva_id)


@router.get("/inteligencia/equipamentos/{equipamento_id}", response_model=FrotaInteligenciaEquipamentoResponse)
async def obter_inteligencia_equipamento_frota(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaInteligenciaService(session, tenant_id)
    return await svc.obter_inteligencia_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/agricultura/resumo", response_model=FrotaAgriculturaResponse)
async def obter_resumo_frota_agricultura(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaAgriculturaService(session, tenant_id)
    return await svc.obter_resumo(unidade_produtiva_id=unidade_produtiva_id)


@router.get("/agricultura/equipamentos/{equipamento_id}", response_model=FrotaAgriculturaEquipamentoResponse)
async def obter_frota_agricultura_equipamento(
    equipamento_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaAgriculturaService(session, tenant_id)
    return await svc.obter_equipamento(
        equipamento_id=equipamento_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get("/agricultura/safras/{safra_id}", response_model=FrotaAgriculturaSafraResponse)
async def obter_frota_agricultura_safra(
    safra_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaAgriculturaService(session, tenant_id)
    return await svc.obter_safra(safra_id=safra_id, unidade_produtiva_id=unidade_produtiva_id)


@router.get("/agricultura/talhoes/{talhao_id}", response_model=FrotaAgriculturaTalhaoResponse)
async def obter_frota_agricultura_talhao(
    talhao_id: UUID,
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaAgriculturaService(session, tenant_id)
    return await svc.obter_talhao(talhao_id=talhao_id, unidade_produtiva_id=unidade_produtiva_id)


@router.get("/agricultura/operacoes", response_model=FrotaAgriculturaOperacoesResponse)
async def obter_frota_agricultura_operacoes(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.ENTERPRISE)),
):
    svc = FrotaAgriculturaService(session, tenant_id)
    return await svc.obter_operacoes(unidade_produtiva_id=unidade_produtiva_id)

@router.post("/", response_model=MaquinarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_maquinario(
    dados: MaquinarioCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    maq = await svc.create(dados)
    await session.commit()
    await session.refresh(maq)
    return maq

@router.get("/", response_model=List[MaquinarioResponse])
async def listar_maquinarios(
    unidade_produtiva_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    filters = {}
    if unidade_produtiva_id: filters["unidade_produtiva_id"] = unidade_produtiva_id
    return await svc.list_all(**filters)

@router.get("/{id}", response_model=MaquinarioResponse)
async def detalhar_maquinario(
    id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    return await svc.get_or_fail(id)

@router.patch("/{id}", response_model=MaquinarioResponse)
async def atualizar_maquinario(
    id: UUID,
    dados: MaquinarioUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    maq = await svc.update(id, dados)
    await session.commit()
    await session.refresh(maq)
    return maq

# --- Planos de Manutenção ---

@router.post("/planos/", response_model=PlanoManutencaoResponse)
async def criar_plano(
    dados: PlanoManutencaoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaService(session, tenant_id)
    plano = await svc.criar_plano_manutencao(dados)
    await session.commit()
    await session.refresh(plano)
    return plano

@router.get("/{maquinario_id}/planos", response_model=List[PlanoManutencaoResponse])
async def listar_planos(
    maquinario_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    svc = FrotaService(session, tenant_id)
    return await svc.listar_planos(maquinario_id)

# --- Ordens de Serviço ---

@router.post("/os/", response_model=OrdemServicoResponse)
async def abrir_ordem_servico(
    dados: OrdemServicoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    return await svc.abrir_os(dados)

@router.post("/os/{os_id}/itens", response_model=ItemOrdemServicoResponse)
async def adicionar_peça_os(
    os_id: UUID,
    dados: ItemOrdemServicoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    return await svc.adicionar_item_os(os_id, dados)

@router.patch("/os/{os_id}/fechar", response_model=OrdemServicoResponse)
async def fechar_ordem_servico(
    os_id: UUID,
    dados: OrdemServicoUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    svc = FrotaService(session, tenant_id)
    return await svc.fechar_os(os_id, dados)

# --- Importação de Dados ---

@router.post("/importar/abastecimentos", status_code=status.HTTP_200_OK)
async def importar_abastecimentos(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    content = await file.read()
    csv_text = content.decode("utf-8")
    svc = FrotaImportService(session, tenant_id)
    return await svc.importar_abastecimentos(csv_text)

@router.post("/importar/manutencoes", status_code=status.HTTP_200_OK)
async def importar_manutencoes(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("O1_FROTA"))
):
    content = await file.read()
    csv_text = content.decode("utf-8")
    svc = FrotaImportService(session, tenant_id)
    return await svc.importar_manutencoes(csv_text)

# --- Inteligência e Automação ---

@router.get("/inteligencia/regras", response_model=list[FrotaRegraInteligenteSchema])
async def listar_regras_automacao(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id)
):
    svc = FrotaAutomacaoService(session, tenant_id)
    return await svc.listar_regras()

@router.patch("/inteligencia/regras/{regra_id}", response_model=FrotaRegraInteligenteSchema)
async def atualizar_regra_automacao(
    regra_id: UUID,
    dados: FrotaRegraInteligenteUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id)
):
    svc = FrotaAutomacaoService(session, tenant_id)
    return await svc.atualizar_regra(regra_id, dados)

@router.get("/inteligencia/automacoes/logs", response_model=list[FrotaLogAutomacaoSchema])
async def listar_logs_automacao(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id)
):
    # Query direta no banco para logs de automação
    from operacional.models.frota import FrotaLogAutomacao
    from sqlalchemy import select
    query = select(FrotaLogAutomacao).where(FrotaLogAutomacao.tenant_id == tenant_id).order_by(FrotaLogAutomacao.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())

@router.get("/inteligencia/automacoes/metricas")
async def obter_metricas_automacao(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id)
):
    """
    Retorna KPIs de adoção das automações (FROTA-38).
    """
    svc = FrotaAutomacaoService(session, tenant_id)
    return await svc.obter_metricas_adocao()

@router.get("/inteligencia/benchmark")
async def obter_benchmark_frota(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id)
):
    """
    Retorna benchmarks e rankings de desempenho (FROTA-40).
    """
    from operacional.services.frota_benchmark_service import FrotaBenchmarkService
    svc = FrotaBenchmarkService(session, tenant_id)
    return {
        "geral": await svc.obter_benchmark_geral(),
        "ranking_talhoes": await svc.obter_ranking_talhoes(),
        "impacto_automacao": await svc.obter_impacto_automacao()
    }
