from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from certificacoes_esg.schemas import (
    EvidenciaCertificacaoCreate,
    EvidenciaCertificacaoResponse,
    NaoConformidadeCertificacaoCreate,
    NaoConformidadeCertificacaoResponse,
    NaoConformidadeStatusUpdate,
    PlanoAcaoCertificacaoCreate,
    PlanoAcaoCertificacaoResponse,
    PlanoAcaoStatusUpdate,
    PassaporteRastreabilidadeCreate,
    PassaporteRastreabilidadeUpdateStatus,
    PassaporteRastreabilidadeResponse,
    PassaporteRastreabilidadeEventoCreate,
    PassaporteRastreabilidadeEventoResponse,
    PassaporteRastreabilidadeEvidenciaCreate,
    PassaporteRastreabilidadeEvidenciaResponse,
    RelatorioESGCreate,
    RelatorioESGUpdateStatus,
    RelatorioESGResponse,
    RelatorioESGIndicadorCreate,
    RelatorioESGIndicadorResponse,
    RelatorioESGEvidenciaCreate,
    RelatorioESGEvidenciaResponse,
    ProgramaCertificacaoCreate,
    ProgramaCertificacaoResponse,
    ProgramaCertificacaoUpdate,
)
from certificacoes_esg.models import (
    PrioridadePlanoAcao,
    SeveridadeNaoConformidade,
    StatusNaoConformidade,
    StatusPlanoAcao,
    TipoEvidencia,
    StatusRelatorioESG,
    StatusPassaporte,
)
from certificacoes_esg.service import CertificacoesESGService
from core.dependencies import get_session, get_tenant_id, get_user_id, require_tenant_permission


router = APIRouter(prefix="/certificacoes-esg", tags=["Certificações / ESG"])


def _user_id_or_unauthorized(user_id: uuid.UUID | None) -> uuid.UUID:
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return user_id


def _service(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None) -> CertificacoesESGService:
    return CertificacoesESGService(session, tenant_id, user_id=_user_id_or_unauthorized(user_id))


@router.get("/programas", response_model=list[ProgramaCertificacaoResponse])
async def listar_programas(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_programas()


@router.post("/programas", response_model=ProgramaCertificacaoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_programa(
    dados: ProgramaCertificacaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_programa(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.patch("/programas/{programa_id}", response_model=ProgramaCertificacaoResponse,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def atualizar_programa(
    programa_id: uuid.UUID,
    dados: ProgramaCertificacaoUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).atualizar_programa(programa_id, dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/evidencias", response_model=EvidenciaCertificacaoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_evidencia(
    dados: EvidenciaCertificacaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_evidencia(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/evidencias", response_model=list[EvidenciaCertificacaoResponse])
async def listar_evidencias(
    programa_id: uuid.UUID | None = Query(None),
    checklist_id: uuid.UUID | None = Query(None),
    criterio_id: uuid.UUID | None = Query(None),
    avaliacao_id: uuid.UUID | None = Query(None),
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    propriedade_imovel_id: uuid.UUID | None = Query(None),
    tipo_evidencia: TipoEvidencia | None = Query(None),
    publico: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_evidencias(
        programa_id=programa_id,
        checklist_id=checklist_id,
        criterio_id=criterio_id,
        avaliacao_id=avaliacao_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_rural_id,
        propriedade_imovel_id=propriedade_imovel_id,
        tipo_evidencia=tipo_evidencia,
        publico=publico,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/nao-conformidades",
    response_model=NaoConformidadeCertificacaoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_nao_conformidade(
    dados: NaoConformidadeCertificacaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_nao_conformidade(
        dados,
        created_by=_user_id_or_unauthorized(user_id),
    )
    await session.commit()
    return obj


@router.get("/nao-conformidades", response_model=list[NaoConformidadeCertificacaoResponse])
async def listar_nao_conformidades(
    programa_id: uuid.UUID | None = Query(None),
    checklist_id: uuid.UUID | None = Query(None),
    criterio_id: uuid.UUID | None = Query(None),
    avaliacao_id: uuid.UUID | None = Query(None),
    evidencia_id: uuid.UUID | None = Query(None),
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    propriedade_imovel_id: uuid.UUID | None = Query(None),
    severidade: SeveridadeNaoConformidade | None = Query(None),
    status: StatusNaoConformidade | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    svc = _service(session, tenant_id, user_id)
    stmt = await svc.listar_nao_conformidades(
        programa_id=programa_id,
        checklist_id=checklist_id,
        criterio_id=criterio_id,
        avaliacao_id=avaliacao_id,
        evidencia_id=evidencia_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_rural_id,
        propriedade_imovel_id=propriedade_imovel_id,
        severidade=severidade,
        status=status,
        skip=skip,
        limit=limit,
    )
    return stmt


@router.patch("/nao-conformidades/{nao_conformidade_id}/status", response_model=NaoConformidadeCertificacaoResponse,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def atualizar_status_nao_conformidade(
    nao_conformidade_id: uuid.UUID,
    dados: NaoConformidadeStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).atualizar_status_nao_conformidade(
        nao_conformidade_id,
        dados,
    )
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/planos-acao", response_model=PlanoAcaoCertificacaoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_plano_acao(
    dados: PlanoAcaoCertificacaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_plano_acao(
        dados,
        created_by=_user_id_or_unauthorized(user_id),
    )
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/planos-acao", response_model=list[PlanoAcaoCertificacaoResponse])
async def listar_planos_acao(
    programa_id: uuid.UUID | None = Query(None),
    nao_conformidade_id: uuid.UUID | None = Query(None),
    evidencia_id: uuid.UUID | None = Query(None),
    responsavel_pessoa_id: uuid.UUID | None = Query(None),
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    propriedade_imovel_id: uuid.UUID | None = Query(None),
    prioridade: PrioridadePlanoAcao | None = Query(None),
    status: StatusPlanoAcao | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_planos_acao(
        programa_id=programa_id,
        nao_conformidade_id=nao_conformidade_id,
        evidencia_id=evidencia_id,
        responsavel_pessoa_id=responsavel_pessoa_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_rural_id,
        propriedade_imovel_id=propriedade_imovel_id,
        prioridade=prioridade,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.patch("/planos-acao/{plano_acao_id}/status", response_model=PlanoAcaoCertificacaoResponse,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def atualizar_status_plano_acao(
    plano_acao_id: uuid.UUID,
    dados: PlanoAcaoStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).atualizar_status_plano_acao(plano_acao_id, dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/relatorios-esg", response_model=RelatorioESGResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_relatorio_esg(
    dados: RelatorioESGCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_relatorio_esg(
        dados,
        created_by=_user_id_or_unauthorized(user_id),
    )
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/relatorios-esg", response_model=list[RelatorioESGResponse])
async def listar_relatorios_esg(
    programa_id: uuid.UUID | None = Query(None),
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    propriedade_imovel_id: uuid.UUID | None = Query(None),
    status: StatusRelatorioESG | None = Query(None),
    publico: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_relatorios_esg(
        programa_id=programa_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_rural_id,
        propriedade_imovel_id=propriedade_imovel_id,
        status=status,
        publico=publico,
        skip=skip,
        limit=limit,
    )


@router.patch("/relatorios-esg/{id}/status", response_model=RelatorioESGResponse,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def atualizar_status_relatorio_esg(
    id: uuid.UUID,
    dados: RelatorioESGUpdateStatus,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).atualizar_status_relatorio_esg(id, dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/relatorios-esg/{id}/indicadores", response_model=RelatorioESGIndicadorResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def adicionar_indicador_relatorio_esg(
    id: uuid.UUID,
    dados: RelatorioESGIndicadorCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    if dados.relatorio_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID da rota não confere com ID do payload")
    obj = await _service(session, tenant_id, user_id).adicionar_indicador_relatorio_esg(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/relatorios-esg/{id}/indicadores", response_model=list[RelatorioESGIndicadorResponse])
async def listar_indicadores_relatorio_esg(
    id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_indicadores_relatorio_esg(id)


@router.post("/relatorios-esg/{id}/evidencias", response_model=RelatorioESGEvidenciaResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def vincular_evidencia_relatorio_esg(
    id: uuid.UUID,
    dados: RelatorioESGEvidenciaCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    if dados.relatorio_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID da rota não confere com ID do payload")
    obj = await _service(session, tenant_id, user_id).vincular_evidencia_relatorio_esg(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/relatorios-esg/{id}/evidencias", response_model=list[RelatorioESGEvidenciaResponse])
async def listar_evidencias_relatorio_esg(
    id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_evidencias_relatorio_esg(id)


@router.post("/passaportes", response_model=PassaporteRastreabilidadeResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def criar_passaporte_rastreabilidade(
    dados: PassaporteRastreabilidadeCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).criar_passaporte_rastreabilidade(
        dados,
        created_by=_user_id_or_unauthorized(user_id),
    )
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/passaportes", response_model=list[PassaporteRastreabilidadeResponse])
async def listar_passaportes_rastreabilidade(
    programa_id: uuid.UUID | None = Query(None),
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    propriedade_imovel_id: uuid.UUID | None = Query(None),
    status: StatusPassaporte | None = Query(None),
    publico: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_passaportes_rastreabilidade(
        programa_id=programa_id,
        propriedade_id=propriedade_id,
        imovel_rural_id=imovel_rural_id,
        propriedade_imovel_id=propriedade_imovel_id,
        status=status,
        publico=publico,
        skip=skip,
        limit=limit,
    )


@router.patch("/passaportes/{id}/status", response_model=PassaporteRastreabilidadeResponse,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def atualizar_status_passaporte_rastreabilidade(
    id: uuid.UUID,
    dados: PassaporteRastreabilidadeUpdateStatus,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    obj = await _service(session, tenant_id, user_id).atualizar_status_passaporte_rastreabilidade(id, dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/passaportes/{id}/eventos", response_model=PassaporteRastreabilidadeEventoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def adicionar_evento_passaporte(
    id: uuid.UUID,
    dados: PassaporteRastreabilidadeEventoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    if dados.passaporte_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID da rota não confere com ID do payload")
    obj = await _service(session, tenant_id, user_id).adicionar_evento_passaporte(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/passaportes/{id}/eventos", response_model=list[PassaporteRastreabilidadeEventoResponse])
async def listar_eventos_passaporte(
    id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_eventos_passaporte(id)


@router.post("/passaportes/{id}/evidencias", response_model=PassaporteRastreabilidadeEvidenciaResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("certificacoes_esg:*"))]
)
async def vincular_evidencia_passaporte(
    id: uuid.UUID,
    dados: PassaporteRastreabilidadeEvidenciaCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    if dados.passaporte_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID da rota não confere com ID do payload")
    obj = await _service(session, tenant_id, user_id).vincular_evidencia_passaporte(dados)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/passaportes/{id}/evidencias", response_model=list[PassaporteRastreabilidadeEvidenciaResponse])
async def listar_evidencias_passaporte(
    id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: uuid.UUID | None = Depends(get_user_id),
    session: AsyncSession = Depends(get_session),
):
    return await _service(session, tenant_id, user_id).listar_evidencias_passaporte(id)
