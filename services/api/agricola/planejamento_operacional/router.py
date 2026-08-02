from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_session, get_tenant_id, get_current_user_claims, require_module, require_tenant_permission
from agricola.planejamento_operacional.schemas import (
    PlanoOperacionalCreate,
    PlanoOperacionalUpdate,
    PlanoOperacionalResponse,
    PlanoOperacionalTarefaCreate,
    PlanoOperacionalTarefaUpdate,
    PlanoOperacionalTarefaResponse,
    PlanoOperacionalTarefaInsumoCreate,
    PlanoOperacionalTarefaInsumoUpdate,
    PlanoOperacionalTarefaInsumoResponse,
    SugestaoProdutoOrcamentoResponse,
    InsumoConsolidadoResponse,
    AplicarInsumoLoteRequest,
    AplicarInsumoLoteResponse,
    AplicarMaquinarioLoteRequest,
    AplicarMaoObraLoteRequest,
    PlanoOperacionalTarefaMaoObraCreate,
    PlanoOperacionalTarefaMaoObraUpdate,
    PlanoOperacionalTarefaMaoObraResponse,
    PlanoOperacionalTarefaMaquinarioCreate,
    PlanoOperacionalTarefaMaquinarioUpdate,
    PlanoOperacionalTarefaMaquinarioResponse,
    GerarOSLoteRequest,
    GerarOSLoteResponse,
    GerarOSResultado,
)
from agricola.planejamento_operacional.service import PlanoOperacionalService
from agricola.receitas_aplicacao.schemas import (
    AplicarReceitaRequest,
    AplicarReceitaResponse,
    AplicarReceitaResultado,
)
from operacional.schemas.compras import SolicitacaoCompraResponse

router = APIRouter(
    prefix="/agricola/planejamento-operacional",
    tags=["Agrícola - Planejamento Operacional em Lote"],
    dependencies=[Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO))],
)


def _user_id(user: dict) -> UUID | None:
    sub = user.get("sub")
    return UUID(sub) if sub else None


@router.post(
    "/",
    response_model=PlanoOperacionalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um Planejamento Operacional em Lote (nasce RASCUNHO)",
)
async def criar_plano(
    dados: PlanoOperacionalCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:criar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    plano = await svc.criar(dados)
    plano.criado_por = _user_id(user)
    await session.commit()
    await session.refresh(plano)
    return plano


@router.get(
    "/",
    response_model=List[PlanoOperacionalResponse],
    summary="Lista Planejamentos Operacionais do tenant",
)
async def listar_planos(
    safra_id: Optional[UUID] = Query(None),
    status_filtro: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.list_all(skip=skip, limit=limit, safra_id=safra_id, status=status_filtro)


@router.get(
    "/{plano_id}",
    response_model=PlanoOperacionalResponse,
    summary="Detalha um Planejamento Operacional",
)
async def obter_plano(
    plano_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.get_or_fail(plano_id)


@router.patch(
    "/{plano_id}",
    response_model=PlanoOperacionalResponse,
    summary="Atualiza o cabeçalho do plano (apenas RASCUNHO/EM_ANALISE)",
)
async def atualizar_plano(
    plano_id: UUID,
    dados: PlanoOperacionalUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    plano = await svc.atualizar(plano_id, dados)
    await session.commit()
    await session.refresh(plano)
    return plano


@router.post(
    "/{plano_id}/avancar",
    response_model=PlanoOperacionalResponse,
    summary="Avança o status do plano (ex.: aprovar, cancelar)",
)
async def avancar_status_plano(
    plano_id: UUID,
    novo_status: str = Query(..., description="Novo status do plano"),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:aprovar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    plano = await svc.avancar_status(plano_id, novo_status)
    await session.commit()
    await session.refresh(plano)
    return plano


@router.post(
    "/{plano_id}/tarefas",
    response_model=PlanoOperacionalTarefaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona uma SafraTarefa (já aprovada) ao plano",
)
async def adicionar_tarefa(
    plano_id: UUID,
    dados: PlanoOperacionalTarefaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    item = await svc.adicionar_tarefa(plano_id, dados)
    await session.commit()
    await session.refresh(item)
    return item


@router.get(
    "/{plano_id}/tarefas",
    response_model=List[PlanoOperacionalTarefaResponse],
    summary="Lista as tarefas associadas ao plano",
)
async def listar_tarefas_do_plano(
    plano_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.listar_itens(plano_id)


@router.patch(
    "/{plano_id}/tarefas/{item_id}",
    response_model=PlanoOperacionalTarefaResponse,
    summary="Atualiza o estado de uma tarefa dentro do plano",
)
async def atualizar_item_plano(
    plano_id: UUID,
    item_id: UUID,
    dados: PlanoOperacionalTarefaUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    item = await svc.atualizar_item(plano_id, item_id, dados)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete(
    "/{plano_id}/tarefas/{item_id}",
    response_model=PlanoOperacionalTarefaResponse,
    summary="Remove (logicamente) uma tarefa do plano",
)
async def remover_tarefa_do_plano(
    plano_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    item = await svc.remover_tarefa(plano_id, item_id)
    await session.commit()
    await session.refresh(item)
    return item


@router.post(
    "/{plano_id}/tarefas/{item_id}/insumos",
    response_model=PlanoOperacionalTarefaInsumoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Escolhe um produto comercial para atender a necessidade da tarefa (simulação)",
)
async def adicionar_insumo(
    plano_id: UUID,
    item_id: UUID,
    dados: PlanoOperacionalTarefaInsumoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    insumo = await svc.adicionar_insumo(plano_id, item_id, dados)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.get(
    "/necessidades/{necessidade_id}/sugestoes-produto",
    response_model=List[SugestaoProdutoOrcamentoResponse],
    summary="Sugere produtos já escolhidos no orçamento da safra para essa necessidade técnica",
)
async def sugerir_produtos_orcamento(
    necessidade_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.sugerir_produtos_orcamento(necessidade_id)


@router.get(
    "/{plano_id}/insumos-consolidados",
    response_model=List[InsumoConsolidadoResponse],
    summary="Agrupa as necessidades técnicas de todas as tarefas do plano por categoria+item, somando quantidade",
)
async def listar_insumos_consolidados(
    plano_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.listar_insumos_consolidados(plano_id)


@router.post(
    "/{plano_id}/insumos-consolidados/aplicar",
    response_model=AplicarInsumoLoteResponse,
    summary="Aplica o mesmo produto comercial a várias necessidades de uma vez (uma tarefa por necessidade)",
)
async def aplicar_insumo_lote(
    plano_id: UUID,
    dados: AplicarInsumoLoteRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    resultado = await svc.aplicar_insumo_lote(plano_id, dados)
    await session.commit()
    return resultado


@router.post(
    "/{plano_id}/insumos-consolidados/aplicar-maquinario",
    response_model=AplicarInsumoLoteResponse,
    summary="Aplica a mesma máquina/implemento a várias necessidades de maquinário de uma vez",
)
async def aplicar_maquinario_lote(
    plano_id: UUID,
    dados: AplicarMaquinarioLoteRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    resultado = await svc.aplicar_maquinario_lote(plano_id, dados)
    await session.commit()
    return resultado


@router.post(
    "/{plano_id}/insumos-consolidados/aplicar-mao-obra",
    response_model=AplicarInsumoLoteResponse,
    summary="Aplica o mesmo tipo de serviço/pessoa a várias necessidades de mão de obra de uma vez",
)
async def aplicar_mao_obra_lote(
    plano_id: UUID,
    dados: AplicarMaoObraLoteRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    resultado = await svc.aplicar_mao_obra_lote(plano_id, dados)
    await session.commit()
    return resultado


@router.get(
    "/{plano_id}/tarefas/{item_id}/insumos",
    response_model=List[PlanoOperacionalTarefaInsumoResponse],
    summary="Lista os insumos escolhidos para a tarefa dentro do plano",
)
async def listar_insumos(
    plano_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.listar_insumos(plano_id, item_id)


@router.patch(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}",
    response_model=PlanoOperacionalTarefaInsumoResponse,
    summary="Atualiza um insumo planejado (recalcula snapshot de disponibilidade/custo)",
)
async def atualizar_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    dados: PlanoOperacionalTarefaInsumoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    insumo = await svc.atualizar_insumo(plano_id, item_id, insumo_id, dados)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.post(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}/recalcular",
    response_model=PlanoOperacionalTarefaInsumoResponse,
    summary="Recalcula o snapshot de disponibilidade/custo do insumo com dados atuais",
)
async def recalcular_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    insumo = await svc.recalcular_insumo(plano_id, item_id, insumo_id)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.delete(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um insumo planejado",
)
async def remover_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    await svc.remover_insumo(plano_id, item_id, insumo_id)
    await session.commit()


@router.post(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}/reservar",
    response_model=PlanoOperacionalTarefaInsumoResponse,
    summary="Cria reserva real de estoque para este insumo",
)
async def reservar_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:aprovar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    insumo = await svc.reservar_insumo(plano_id, item_id, insumo_id)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.delete(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}/reserva",
    response_model=PlanoOperacionalTarefaInsumoResponse,
    summary="Libera a reserva de estoque deste insumo",
)
async def liberar_reserva_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    insumo = await svc.liberar_reserva_insumo(plano_id, item_id, insumo_id)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.post(
    "/{plano_id}/tarefas/{item_id}/aprovar",
    response_model=PlanoOperacionalTarefaResponse,
    summary="Aprova o item (reserva parcialmente os insumos disponíveis)",
)
async def aprovar_item(
    plano_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:aprovar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    item = await svc.aprovar_item(plano_id, item_id)
    await session.commit()
    await session.refresh(item)
    return item


@router.post(
    "/{plano_id}/tarefas/{item_id}/insumos/{insumo_id}/solicitar-compra",
    response_model=SolicitacaoCompraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita a compra da quantidade faltante deste insumo (ação explícita, idempotente)",
)
async def solicitar_compra_insumo(
    plano_id: UUID,
    item_id: UUID,
    insumo_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    solicitacao = await svc.solicitar_compra_insumo(plano_id, item_id, insumo_id)
    await session.commit()
    return solicitacao


@router.post(
    "/{plano_id}/aplicar-receita",
    response_model=AplicarReceitaResponse,
    summary="Aplica uma Receita de Aplicação (produto+dose/ha e mão de obra) a várias tarefas do plano de uma vez",
)
async def aplicar_receita(
    plano_id: UUID,
    dados: AplicarReceitaRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    resultados = await svc.aplicar_receita(plano_id, dados.receita_id, dados.plano_operacional_tarefa_ids)
    await session.commit()
    return AplicarReceitaResponse(resultados=[AplicarReceitaResultado(**r) for r in resultados])


@router.post(
    "/{plano_id}/gerar-os",
    response_model=GerarOSLoteResponse,
    summary="Gera a Ordem de Serviço (OperacaoAgricola) em lote para os itens PRONTA selecionados do plano",
)
async def gerar_os_lote(
    plano_id: UUID,
    dados: GerarOSLoteRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:aprovar")),
):
    svc = PlanoOperacionalService(session, tenant_id, _user_id(user))
    resultados = await svc.gerar_os_lote(plano_id, dados.itens)
    return GerarOSLoteResponse(resultados=[GerarOSResultado(**r) for r in resultados])


@router.post(
    "/{plano_id}/tarefas/{item_id}/mao-obra",
    response_model=PlanoOperacionalTarefaMaoObraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona necessidade de mão de obra estimada ao item de plano",
)
async def adicionar_mao_obra(
    plano_id: UUID,
    item_id: UUID,
    dados: PlanoOperacionalTarefaMaoObraCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    mao_obra = await svc.adicionar_mao_obra(plano_id, item_id, dados)
    await session.commit()
    await session.refresh(mao_obra)
    return mao_obra


@router.get(
    "/{plano_id}/tarefas/{item_id}/mao-obra",
    response_model=List[PlanoOperacionalTarefaMaoObraResponse],
    summary="Lista as necessidades de mão de obra do item de plano",
)
async def listar_mao_obra(
    plano_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.listar_mao_obra(plano_id, item_id)


@router.patch(
    "/{plano_id}/tarefas/{item_id}/mao-obra/{mao_obra_id}",
    response_model=PlanoOperacionalTarefaMaoObraResponse,
    summary="Atualiza uma necessidade de mão de obra (recalcula snapshot de custo)",
)
async def atualizar_mao_obra(
    plano_id: UUID,
    item_id: UUID,
    mao_obra_id: UUID,
    dados: PlanoOperacionalTarefaMaoObraUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    mao_obra = await svc.atualizar_mao_obra(plano_id, item_id, mao_obra_id, dados)
    await session.commit()
    await session.refresh(mao_obra)
    return mao_obra


@router.delete(
    "/{plano_id}/tarefas/{item_id}/mao-obra/{mao_obra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma necessidade de mão de obra do item de plano",
)
async def remover_mao_obra(
    plano_id: UUID,
    item_id: UUID,
    mao_obra_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    await svc.remover_mao_obra(plano_id, item_id, mao_obra_id)
    await session.commit()


@router.post(
    "/{plano_id}/tarefas/{item_id}/maquinario",
    response_model=PlanoOperacionalTarefaMaquinarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona necessidade de maquinário (máquina/implemento) ao item de plano",
)
async def adicionar_maquinario(
    plano_id: UUID,
    item_id: UUID,
    dados: PlanoOperacionalTarefaMaquinarioCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    maquinario = await svc.adicionar_maquinario(plano_id, item_id, dados)
    await session.commit()
    await session.refresh(maquinario)
    return maquinario


@router.get(
    "/{plano_id}/tarefas/{item_id}/maquinario",
    response_model=List[PlanoOperacionalTarefaMaquinarioResponse],
    summary="Lista as necessidades de maquinário do item de plano",
)
async def listar_maquinario(
    plano_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:visualizar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    return await svc.listar_maquinario(plano_id, item_id)


@router.patch(
    "/{plano_id}/tarefas/{item_id}/maquinario/{maquinario_id}",
    response_model=PlanoOperacionalTarefaMaquinarioResponse,
    summary="Atualiza uma necessidade de maquinário (recalcula snapshot de custo)",
)
async def atualizar_maquinario(
    plano_id: UUID,
    item_id: UUID,
    maquinario_id: UUID,
    dados: PlanoOperacionalTarefaMaquinarioUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    maquinario = await svc.atualizar_maquinario(plano_id, item_id, maquinario_id, dados)
    await session.commit()
    await session.refresh(maquinario)
    return maquinario


@router.delete(
    "/{plano_id}/tarefas/{item_id}/maquinario/{maquinario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma necessidade de maquinário do item de plano",
)
async def remover_maquinario(
    plano_id: UUID,
    item_id: UUID,
    maquinario_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:planejamento_operacional:editar")),
):
    svc = PlanoOperacionalService(session, tenant_id)
    await svc.remover_maquinario(plano_id, item_id, maquinario_id)
    await session.commit()
