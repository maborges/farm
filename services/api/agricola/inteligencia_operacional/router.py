from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos, PlanTier
from core.dependencies import (
    get_session_with_tenant,
    get_tenant_id,
    require_module,
    require_tenant_permission,
    require_tier,
    require_role,
)
from core.services.audit_service import write_audit_log

from agricola.tarefas.schemas import TarefaCreate, TarefaResponse
from agricola.tarefas.service import TarefaService

from .schemas import (
    PlanoAcaoOperacionalAgricolaConverterTarefaRequest,
    PlanoAcaoOperacionalAgricolaResponse,
)
from .service import InteligenciaOperacionalAgricolaV1Service

router = APIRouter(
    prefix="/agricola/inteligencia-operacional",
    tags=["Inteligência Operacional Agrícola v1"],
    dependencies=[
        Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO)),
        Depends(require_tier(PlanTier.PROFISSIONAL)),
    ],
)


@router.get(
    "/v1",
    response_model=PlanoAcaoOperacionalAgricolaResponse,
    summary="Planos de ação operacional assistidos da cadeia agrícola",
)
async def planos_de_acao_operacionais_agricolas_v1(
    safra_id: UUID = Query(..., description="Safra alvo dos planos assistidos"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional dos planos assistidos"),
    data_fim: date | None = Query(None, description="Período opcional dos planos assistidos"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session_with_tenant),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
    return await svc.gerar(
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.post(
    "/planos/{plano_id}/converter-tarefa",
    response_model=TarefaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Converte um plano assistido em tarefa real mediante aprovação humana",
)
async def converter_plano_em_tarefa(
    plano_id: UUID,
    dados: PlanoAcaoOperacionalAgricolaConverterTarefaRequest,
    safra_id: UUID = Query(..., description="Safra do plano assistido"),
    production_unit_id: UUID | None = Query(None, description="ProductionUnit do recorte assistido"),
    unidade_produtiva_id: UUID | None = Query(None, description="Unidade produtiva do recorte assistido"),
    data_inicio: date | None = Query(None, description="Início do recorte assistido"),
    data_fim: date | None = Query(None, description="Fim do recorte assistido"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session_with_tenant),
    _: None = Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO)),
    claims: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    svc = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
    plano = await svc.obter_plano_por_id(
        plano_id=plano_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    user_id = UUID(claims["sub"]) if claims.get("sub") else None
    tarefa_svc = TarefaService(session, tenant_id)
    tarefa_dados = TarefaCreate(
        talhao_id=None,
        production_unit_id=plano.production_unit_id or production_unit_id,
        cultivo_area_id=None,
        analise_solo_id=None,
        origem="MANUAL",
        tipo=dados.tipo,
        fase=None,
        criticidade=svc.criticidade_para_tarefa(plano.severidade),
        descricao=dados.titulo.strip(),
        obs=svc.montar_obs_conversion(
            plano=plano,
            titulo=dados.titulo,
            descricao=dados.descricao,
            tipo=dados.tipo,
            prioridade=dados.prioridade,
            data_prevista=dados.data_prevista,
            aprovado_explicitamente=dados.confirmado,
            user_id=user_id,
        ),
        prioridade=dados.prioridade,
        data_prevista=dados.data_prevista,
    )
    tarefa = await tarefa_svc.criar(safra_id, tarefa_dados, user_id=user_id)
    agora = datetime.utcnow()
    if user_id is not None:
        tarefa.aprovado_por = user_id
    tarefa.aprovado_em = agora
    tarefa.updated_at = agora
    tarefa_payload = TarefaResponse.model_validate(tarefa).model_dump(mode="json")

    await write_audit_log(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        action="convert_to_task",
        resource="agricola_inteligencia_operacional_plano",
        resource_id=tarefa.id,
        payload_before={
            "plano_id": str(plano.id),
            "plano_chave": plano.chave,
            "plano": plano.model_dump(mode="json"),
        },
        payload_after={
            "confirmado": dados.confirmado,
            "plano_id": str(plano.id),
            "plano_chave": plano.chave,
            "tarefa": tarefa_payload,
        },
    )
    await session.commit()
    await session.refresh(tarefa)
    return tarefa
