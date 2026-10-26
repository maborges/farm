"""Roteador administrativo do Backoffice para as bibliotecas globais e catálogos compartilhados do DeepFarms Agro.

Gerencia com estrito isolamento multi-tenant:
- Commodities globais (cadastros_commodities com tenant_id IS NULL e sistema=True)
- Culturas agrícolas globais (cadastros_culturas com tenant_id IS NULL e sistema=True)
- Unidades de medida globais (unidades_medida com tenant_id IS NULL e sistema=True)
- Conversões de unidades globais (unidades_medida_conversoes com tenant_id IS NULL)

Garante:
- Preservação da integridade referencial (bloqueio de exclusão com 409 Conflict se houver referências)
- Registro compulsório de auditoria em AdminAuditLog
- Proteção contra duplicidade de códigos canônicos
- Paginação, filtros e busca textual
- Impossibilidade de visualização ou mutação de registros particulares de clientes/tenants
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.commodities.models import Commodity
from core.cadastros.produtos.models import ProdutoCultura, SoloParametroCultura
from core.dependencies import get_session, require_any_permission
from core.measurements.models import UnidadeMedida, UnidadeMedidaConversao
from core.models.admin_audit_log import AdminAuditLog
from core.schemas.agro_config_schemas import (
    AgroCommodityCreateRequest,
    AgroCommodityListResponse,
    AgroCommodityResponse,
    AgroCommodityUpdateRequest,
    AgroCulturaCreateRequest,
    AgroCulturaListResponse,
    AgroCulturaResponse,
    AgroCulturaUpdateRequest,
    AgroUomConversaoCreateRequest,
    AgroUomConversaoListResponse,
    AgroUomConversaoResponse,
    AgroUomConversaoUpdateRequest,
    AgroUomCreateRequest,
    AgroUomListResponse,
    AgroUomResponse,
    AgroUomUpdateRequest,
)

router = APIRouter(
    prefix="/backoffice/agro/catalogo",
    tags=["Backoffice — DeepFarms Agro Catálogos Globais"],
)

PERM_VIEW = [
    "backoffice:agro:catalog:view",
    "backoffice:agro:config:view",
    "backoffice:agro:view",
    "backoffice:agro:*",
]

PERM_EDIT = [
    "backoffice:agro:catalog:edit",
    "backoffice:agro:config:edit",
    "backoffice:agro:*",
]


def _extract_admin_info(admin_claims: dict[str, Any]) -> tuple[Optional[uuid.UUID], Optional[str]]:
    """Extrai com segurança ID e e-mail do operador administrativo autenticado."""
    admin_uid = None
    sub = admin_claims.get("sub")
    if sub:
        try:
            admin_uid = uuid.UUID(str(sub))
        except (ValueError, TypeError):
            pass
    admin_email = admin_claims.get("email") or admin_claims.get("preferred_username") or "backoffice_admin"
    return admin_uid, admin_email


# ==============================================================================
# 1. COMMODITIES GLOBAIS
# ==============================================================================

@router.get(
    "/commodities",
    response_model=AgroCommodityListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista commodities globais do sistema com paginação e busca",
)
async def list_global_commodities(
    q: Optional[str] = Query(default=None, description="Busca por nome ou código"),
    tipo: Optional[str] = Query(default=None, description="Filtro por tipo (AGRICOLA, PECUARIA, FLORESTAL)"),
    ativo: Optional[bool] = Query(default=None, description="Filtro por status de ativação"),
    pagina: int = Query(default=1, ge=1, description="Número da página"),
    tamanho_pagina: int = Query(default=20, ge=1, le=100, description="Itens por página"),
    session: AsyncSession = Depends(get_session),
) -> AgroCommodityListResponse:
    """Retorna apenas registros canônicos globais (tenant_id IS NULL)."""
    stmt = select(Commodity).where(Commodity.tenant_id.is_(None))
    count_stmt = select(func.count(Commodity.id)).where(Commodity.tenant_id.is_(None))

    if q:
        term = f"%{q.strip()}%"
        filtro = or_(Commodity.nome.ilike(term), Commodity.codigo.ilike(term))
        stmt = stmt.where(filtro)
        count_stmt = count_stmt.where(filtro)

    if tipo:
        stmt = stmt.where(Commodity.tipo == tipo.upper())
        count_stmt = count_stmt.where(Commodity.tipo == tipo.upper())

    if ativo is not None:
        stmt = stmt.where(Commodity.ativo == ativo)
        count_stmt = count_stmt.where(Commodity.ativo == ativo)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (pagina - 1) * tamanho_pagina
    stmt = stmt.order_by(Commodity.nome.asc()).offset(offset).limit(tamanho_pagina)
    result = await session.execute(stmt)
    itens = result.scalars().all()

    return AgroCommodityListResponse(
        itens=[AgroCommodityResponse.model_validate(c, from_attributes=True) for c in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.get(
    "/commodities/{commodity_id}",
    response_model=AgroCommodityResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Detalhes de uma commodity global específica",
)
async def get_global_commodity(
    commodity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AgroCommodityResponse:
    """Busca commodity global, rejeitando dados de tenants."""
    stmt = select(Commodity).where(Commodity.id == commodity_id, Commodity.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity global '{commodity_id}' não encontrada ou pertence a um cliente privado.",
        )
    return AgroCommodityResponse.model_validate(item, from_attributes=True)


@router.post(
    "/commodities",
    response_model=AgroCommodityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma nova commodity global no sistema",
)
async def create_global_commodity(
    payload: AgroCommodityCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroCommodityResponse:
    """Cria uma commodity global (sistema=True, tenant_id=None) com validação de unicidade."""
    # Valida duplicidade de código
    existente_res = await session.execute(
        select(Commodity).where(Commodity.codigo == payload.codigo)
    )
    if existente_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma commodity com o código '{payload.codigo}'.",
        )

    novo = Commodity(
        id=uuid.uuid4(),
        tenant_id=None,
        sistema=True,
        nome=payload.nome.strip(),
        codigo=payload.codigo.strip().upper(),
        tipo=payload.tipo,
        unidade_padrao=payload.unidade_padrao,
        peso_unidade=payload.peso_unidade,
        umidade_padrao_pct=payload.umidade_padrao_pct,
        impureza_padrao_pct=payload.impureza_padrao_pct,
        possui_cotacao=payload.possui_cotacao,
        bolsa_referencia=payload.bolsa_referencia,
        codigo_bolsa=payload.codigo_bolsa,
        descricao=payload.descricao,
        ativo=payload.ativo,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(novo)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.commodity.create",
        entidade="cadastros_commodities",
        entidade_id=novo.id,
        descricao=f"Criação de commodity global: {novo.nome} ({novo.codigo})",
        dados_novos=payload.model_dump(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(novo)

    return AgroCommodityResponse.model_validate(novo, from_attributes=True)


@router.put(
    "/commodities/{commodity_id}",
    response_model=AgroCommodityResponse,
    summary="Atualiza metadados autorizados de uma commodity global",
)
async def update_global_commodity(
    commodity_id: uuid.UUID,
    payload: AgroCommodityUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroCommodityResponse:
    """Atualiza metadados de uma commodity global com auditoria estrita."""
    stmt = select(Commodity).where(Commodity.id == commodity_id, Commodity.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity global '{commodity_id}' não encontrada.",
        )

    dados_anteriores = {
        "nome": item.nome,
        "tipo": item.tipo,
        "unidade_padrao": item.unidade_padrao,
        "peso_unidade": item.peso_unidade,
        "possui_cotacao": item.possui_cotacao,
        "ativo": item.ativo,
    }

    if payload.nome is not None:
        item.nome = payload.nome.strip()
    if payload.tipo is not None:
        item.tipo = payload.tipo
    if payload.unidade_padrao is not None:
        item.unidade_padrao = payload.unidade_padrao
    if payload.peso_unidade is not None:
        item.peso_unidade = payload.peso_unidade
    if payload.umidade_padrao_pct is not None:
        item.umidade_padrao_pct = payload.umidade_padrao_pct
    if payload.impureza_padrao_pct is not None:
        item.impureza_padrao_pct = payload.impureza_padrao_pct
    if payload.possui_cotacao is not None:
        item.possui_cotacao = payload.possui_cotacao
    if payload.bolsa_referencia is not None:
        item.bolsa_referencia = payload.bolsa_referencia
    if payload.codigo_bolsa is not None:
        item.codigo_bolsa = payload.codigo_bolsa
    if payload.descricao is not None:
        item.descricao = payload.descricao
    if payload.ativo is not None:
        item.ativo = payload.ativo

    item.updated_at = datetime.now(timezone.utc)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.commodity.update",
        entidade="cadastros_commodities",
        entidade_id=item.id,
        descricao=f"Atualização de metadados da commodity global: {item.nome}",
        dados_anteriores=dados_anteriores,
        dados_novos=payload.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(item)

    return AgroCommodityResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/commodities/{commodity_id}",
    summary="Remove ou desativa uma commodity global preservando integridade referencial",
)
async def delete_global_commodity(
    commodity_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> dict[str, Any]:
    """Exclui commodity se não houver referências operacionais; caso contrário, bloqueia com 409 Conflict."""
    stmt = select(Commodity).where(Commodity.id == commodity_id, Commodity.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity global '{commodity_id}' não encontrada.",
        )

    # 1. Verifica referências em unidades_medida_conversoes
    ref_conv_stmt = select(func.count(UnidadeMedidaConversao.id)).where(
        UnidadeMedidaConversao.commodity_id == commodity_id
    )
    ref_conv_res = await session.execute(ref_conv_stmt)
    ref_conversoes = ref_conv_res.scalar_one()

    if ref_conversoes > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível excluir fisicamente a commodity '{item.nome}' porque existem "
                f"{ref_conversoes} conversão(ões) de unidade vinculadas. "
                "Para descontinuar o uso, altere o status para inativo (ativo=False)."
            ),
        )

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.commodity.delete",
        entidade="cadastros_commodities",
        entidade_id=item.id,
        descricao=f"Exclusão da commodity global: {item.nome} ({item.codigo})",
        dados_anteriores={"nome": item.nome, "codigo": item.codigo, "tipo": item.tipo},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.delete(item)
    await session.commit()

    return {"sucesso": True, "mensagem": f"Commodity global '{item.nome}' excluída com sucesso."}


# ==============================================================================
# 2. CULTURAS AGRÍCOLAS GLOBAIS
# ==============================================================================

@router.get(
    "/culturas",
    response_model=AgroCulturaListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista culturas agrícolas globais do sistema",
)
async def list_global_culturas(
    q: Optional[str] = Query(default=None, description="Busca por nome comum ou científico"),
    grupo: Optional[str] = Query(default=None, description="Filtro por grupo botânico/econômico"),
    ativa: Optional[bool] = Query(default=None, description="Filtro por status de ativação"),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AgroCulturaListResponse:
    """Retorna o catálogo oficial de culturas globais do sistema."""
    stmt = select(ProdutoCultura).where(ProdutoCultura.tenant_id.is_(None))
    count_stmt = select(func.count(ProdutoCultura.id)).where(ProdutoCultura.tenant_id.is_(None))

    if q:
        term = f"%{q.strip()}%"
        filtro = or_(ProdutoCultura.nome.ilike(term), ProdutoCultura.nome_cientifico.ilike(term))
        stmt = stmt.where(filtro)
        count_stmt = count_stmt.where(filtro)

    if grupo:
        stmt = stmt.where(ProdutoCultura.grupo == grupo.upper())
        count_stmt = count_stmt.where(ProdutoCultura.grupo == grupo.upper())

    if ativa is not None:
        stmt = stmt.where(ProdutoCultura.ativa == ativa)
        count_stmt = count_stmt.where(ProdutoCultura.ativa == ativa)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (pagina - 1) * tamanho_pagina
    stmt = stmt.order_by(ProdutoCultura.nome.asc()).offset(offset).limit(tamanho_pagina)
    result = await session.execute(stmt)
    itens = result.scalars().all()

    return AgroCulturaListResponse(
        itens=[AgroCulturaResponse.model_validate(c, from_attributes=True) for c in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.get(
    "/culturas/{cultura_id}",
    response_model=AgroCulturaResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Detalhes de uma cultura global",
)
async def get_global_cultura(
    cultura_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AgroCulturaResponse:
    stmt = select(ProdutoCultura).where(ProdutoCultura.id == cultura_id, ProdutoCultura.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cultura agrícola global '{cultura_id}' não encontrada.",
        )
    return AgroCulturaResponse.model_validate(item, from_attributes=True)


@router.post(
    "/culturas",
    response_model=AgroCulturaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma nova cultura global oficial",
)
async def create_global_cultura(
    payload: AgroCulturaCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroCulturaResponse:
    # Valida duplicidade de nome global
    existente_res = await session.execute(
        select(ProdutoCultura).where(
            ProdutoCultura.tenant_id.is_(None),
            func.lower(ProdutoCultura.nome) == payload.nome.strip().lower(),
        )
    )
    if existente_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma cultura global cadastrada com o nome '{payload.nome}'.",
        )

    nova = ProdutoCultura(
        id=uuid.uuid4(),
        tenant_id=None,
        sistema=True,
        nome=payload.nome.strip(),
        nome_cientifico=payload.nome_cientifico.strip() if payload.nome_cientifico else None,
        grupo=payload.grupo.strip().upper() if payload.grupo else None,
        ciclo_dias_min=payload.ciclo_dias_min,
        ciclo_dias_max=payload.ciclo_dias_max,
        espacamento_cm=payload.espacamento_cm,
        populacao_plantas_ha=payload.populacao_plantas_ha,
        produtividade_media_sc_ha=payload.produtividade_media_sc_ha,
        v_meta_pct_padrao=payload.v_meta_pct_padrao,
        ativa=payload.ativa,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(nova)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.cultura.create",
        entidade="cadastros_culturas",
        entidade_id=nova.id,
        descricao=f"Criação de cultura agrícola global: {nova.nome}",
        dados_novos=payload.model_dump(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(nova)

    return AgroCulturaResponse.model_validate(nova, from_attributes=True)


@router.put(
    "/culturas/{cultura_id}",
    response_model=AgroCulturaResponse,
    summary="Atualiza metadados agronômicos de uma cultura global",
)
async def update_global_cultura(
    cultura_id: uuid.UUID,
    payload: AgroCulturaUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroCulturaResponse:
    stmt = select(ProdutoCultura).where(ProdutoCultura.id == cultura_id, ProdutoCultura.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cultura global '{cultura_id}' não encontrada.",
        )

    dados_anteriores = {
        "nome": item.nome,
        "grupo": item.grupo,
        "ativa": item.ativa,
    }

    if payload.nome is not None:
        item.nome = payload.nome.strip()
    if payload.nome_cientifico is not None:
        item.nome_cientifico = payload.nome_cientifico.strip()
    if payload.grupo is not None:
        item.grupo = payload.grupo.strip().upper()
    if payload.ciclo_dias_min is not None:
        item.ciclo_dias_min = payload.ciclo_dias_min
    if payload.ciclo_dias_max is not None:
        item.ciclo_dias_max = payload.ciclo_dias_max
    if payload.espacamento_cm is not None:
        item.espacamento_cm = payload.espacamento_cm
    if payload.populacao_plantas_ha is not None:
        item.populacao_plantas_ha = payload.populacao_plantas_ha
    if payload.produtividade_media_sc_ha is not None:
        item.produtividade_media_sc_ha = payload.produtividade_media_sc_ha
    if payload.v_meta_pct_padrao is not None:
        item.v_meta_pct_padrao = payload.v_meta_pct_padrao
    if payload.ativa is not None:
        item.ativa = payload.ativa

    item.updated_at = datetime.now(timezone.utc)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.cultura.update",
        entidade="cadastros_culturas",
        entidade_id=item.id,
        descricao=f"Atualização da cultura global: {item.nome}",
        dados_anteriores=dados_anteriores,
        dados_novos=payload.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(item)

    return AgroCulturaResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/culturas/{cultura_id}",
    summary="Remove ou desativa uma cultura global com checagem de referências",
)
async def delete_global_cultura(
    cultura_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> dict[str, Any]:
    stmt = select(ProdutoCultura).where(ProdutoCultura.id == cultura_id, ProdutoCultura.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cultura global '{cultura_id}' não encontrada.",
        )

    # Checa referências em solo_parametros_cultura
    ref_stmt = select(func.count(SoloParametroCultura.id)).where(SoloParametroCultura.cultura_id == cultura_id)
    ref_res = await session.execute(ref_stmt)
    ref_count = ref_res.scalar_one()

    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível excluir a cultura '{item.nome}' porque existem {ref_count} parâmetros agronômicos de solo vinculados. "
                "Para desativar, altere o status para inativo (ativa=False)."
            ),
        )

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.cultura.delete",
        entidade="cadastros_culturas",
        entidade_id=item.id,
        descricao=f"Exclusão da cultura global: {item.nome}",
        dados_anteriores={"nome": item.nome, "grupo": item.grupo},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.delete(item)
    await session.commit()

    return {"sucesso": True, "mensagem": f"Cultura global '{item.nome}' excluída com sucesso."}


# ==============================================================================
# 3. UNIDADES DE MEDIDA GLOBAIS
# ==============================================================================

@router.get(
    "/unidades",
    response_model=AgroUomListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista unidades de medida canônicas globais",
)
async def list_global_uom(
    q: Optional[str] = Query(default=None, description="Busca por código ou nome"),
    dimensao: Optional[str] = Query(default=None, description="Filtro por dimensão (MASSA, VOLUME, etc)"),
    ativo: Optional[bool] = Query(default=None, description="Filtro por status de ativação"),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AgroUomListResponse:
    stmt = select(UnidadeMedida).where(UnidadeMedida.tenant_id.is_(None))
    count_stmt = select(func.count(UnidadeMedida.id)).where(UnidadeMedida.tenant_id.is_(None))

    if q:
        term = f"%{q.strip()}%"
        filtro = or_(UnidadeMedida.nome.ilike(term), UnidadeMedida.codigo.ilike(term))
        stmt = stmt.where(filtro)
        count_stmt = count_stmt.where(filtro)

    if dimensao:
        stmt = stmt.where(UnidadeMedida.dimensao == dimensao.upper())
        count_stmt = count_stmt.where(UnidadeMedida.dimensao == dimensao.upper())

    if ativo is not None:
        stmt = stmt.where(UnidadeMedida.ativo == ativo)
        count_stmt = count_stmt.where(UnidadeMedida.ativo == ativo)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (pagina - 1) * tamanho_pagina
    stmt = stmt.order_by(UnidadeMedida.dimensao.asc(), UnidadeMedida.codigo.asc()).offset(offset).limit(tamanho_pagina)
    result = await session.execute(stmt)
    itens = result.scalars().all()

    return AgroUomListResponse(
        itens=[AgroUomResponse.model_validate(u, from_attributes=True) for u in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.post(
    "/unidades",
    response_model=AgroUomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma nova unidade de medida canônica",
)
async def create_global_uom(
    payload: AgroUomCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroUomResponse:
    existente_res = await session.execute(
        select(UnidadeMedida).where(
            UnidadeMedida.tenant_id.is_(None),
            UnidadeMedida.codigo == payload.codigo.strip().upper(),
        )
    )
    if existente_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma unidade de medida global com o código '{payload.codigo}'.",
        )

    nova = UnidadeMedida(
        id=uuid.uuid4(),
        tenant_id=None,
        sistema=True,
        codigo=payload.codigo.strip().upper(),
        nome=payload.nome.strip(),
        dimensao=payload.dimensao.strip().upper(),
        codigo_referencia=payload.codigo_referencia.strip().upper(),
        fator_referencia=payload.fator_referencia,
        casas_decimais=payload.casas_decimais,
        eh_unidade_base=payload.eh_unidade_base,
        ativo=payload.ativo,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(nova)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.uom.create",
        entidade="unidades_medida",
        entidade_id=nova.id,
        descricao=f"Criação de unidade de medida global: {nova.codigo} ({nova.nome})",
        dados_novos=payload.model_dump(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(nova)

    return AgroUomResponse.model_validate(nova, from_attributes=True)


@router.put(
    "/unidades/{uom_id}",
    response_model=AgroUomResponse,
    summary="Atualiza parâmetros de uma unidade de medida global",
)
async def update_global_uom(
    uom_id: uuid.UUID,
    payload: AgroUomUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroUomResponse:
    stmt = select(UnidadeMedida).where(UnidadeMedida.id == uom_id, UnidadeMedida.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade de medida global '{uom_id}' não encontrada.",
        )

    dados_anteriores = {
        "nome": item.nome,
        "fator_referencia": float(item.fator_referencia),
        "ativo": item.ativo,
    }

    if payload.nome is not None:
        item.nome = payload.nome.strip()
    if payload.dimensao is not None:
        item.dimensao = payload.dimensao.strip().upper()
    if payload.codigo_referencia is not None:
        item.codigo_referencia = payload.codigo_referencia.strip().upper()
    if payload.fator_referencia is not None:
        item.fator_referencia = payload.fator_referencia
    if payload.casas_decimais is not None:
        item.casas_decimais = payload.casas_decimais
    if payload.eh_unidade_base is not None:
        item.eh_unidade_base = payload.eh_unidade_base
    if payload.ativo is not None:
        item.ativo = payload.ativo

    item.updated_at = datetime.now(timezone.utc)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.uom.update",
        entidade="unidades_medida",
        entidade_id=item.id,
        descricao=f"Atualização da UOM global: {item.codigo}",
        dados_anteriores=dados_anteriores,
        dados_novos=payload.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(item)

    return AgroUomResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/unidades/{uom_id}",
    summary="Remove uma unidade de medida com checagem rigorosa de referências",
)
async def delete_global_uom(
    uom_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> dict[str, Any]:
    stmt = select(UnidadeMedida).where(UnidadeMedida.id == uom_id, UnidadeMedida.tenant_id.is_(None))
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade de medida global '{uom_id}' não encontrada.",
        )

    # Checa referências em conversões como origem ou destino
    ref_stmt = select(func.count(UnidadeMedidaConversao.id)).where(
        or_(
            UnidadeMedidaConversao.unidade_origem_id == uom_id,
            UnidadeMedidaConversao.unidade_destino_id == uom_id,
        )
    )
    ref_res = await session.execute(ref_stmt)
    ref_count = ref_res.scalar_one()

    if ref_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível excluir a unidade de medida '{item.codigo}' porque existem "
                f"{ref_count} regra(s) de conversão vinculadas. "
                "Para descontinuar o uso, altere o status para inativo (ativo=False)."
            ),
        )

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.uom.delete",
        entidade="unidades_medida",
        entidade_id=item.id,
        descricao=f"Exclusão da UOM global: {item.codigo}",
        dados_anteriores={"codigo": item.codigo, "nome": item.nome},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.delete(item)
    await session.commit()

    return {"sucesso": True, "mensagem": f"Unidade de medida global '{item.codigo}' excluída com sucesso."}


# ==============================================================================
# 4. CONVERSÕES DE UNIDADES GLOBAIS
# ==============================================================================

@router.get(
    "/conversoes",
    response_model=AgroUomConversaoListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista regras de conversão de unidades globais",
)
async def list_global_conversoes(
    unidade_origem_id: Optional[uuid.UUID] = Query(default=None),
    unidade_destino_id: Optional[uuid.UUID] = Query(default=None),
    commodity_id: Optional[uuid.UUID] = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AgroUomConversaoListResponse:
    stmt = select(UnidadeMedidaConversao).where(UnidadeMedidaConversao.tenant_id.is_(None))
    count_stmt = select(func.count(UnidadeMedidaConversao.id)).where(UnidadeMedidaConversao.tenant_id.is_(None))

    if unidade_origem_id:
        stmt = stmt.where(UnidadeMedidaConversao.unidade_origem_id == unidade_origem_id)
        count_stmt = count_stmt.where(UnidadeMedidaConversao.unidade_origem_id == unidade_origem_id)

    if unidade_destino_id:
        stmt = stmt.where(UnidadeMedidaConversao.unidade_destino_id == unidade_destino_id)
        count_stmt = count_stmt.where(UnidadeMedidaConversao.unidade_destino_id == unidade_destino_id)

    if commodity_id:
        stmt = stmt.where(UnidadeMedidaConversao.commodity_id == commodity_id)
        count_stmt = count_stmt.where(UnidadeMedidaConversao.commodity_id == commodity_id)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (pagina - 1) * tamanho_pagina
    stmt = stmt.offset(offset).limit(tamanho_pagina)
    result = await session.execute(stmt)
    itens = result.scalars().all()

    return AgroUomConversaoListResponse(
        itens=[AgroUomConversaoResponse.model_validate(c, from_attributes=True) for c in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@router.post(
    "/conversoes",
    response_model=AgroUomConversaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma regra de conversão de unidades canônica",
)
async def create_global_conversao(
    payload: AgroUomConversaoCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroUomConversaoResponse:
    # 1. Verifica se unidades existem
    origem_res = await session.execute(select(UnidadeMedida).where(UnidadeMedida.id == payload.unidade_origem_id))
    if not origem_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade de origem '{payload.unidade_origem_id}' não encontrada.",
        )

    destino_res = await session.execute(select(UnidadeMedida).where(UnidadeMedida.id == payload.unidade_destino_id))
    if not destino_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade de destino '{payload.unidade_destino_id}' não encontrada.",
        )

    nova = UnidadeMedidaConversao(
        id=uuid.uuid4(),
        tenant_id=None,
        unidade_origem_id=payload.unidade_origem_id,
        unidade_destino_id=payload.unidade_destino_id,
        fator=payload.fator,
        cultura=payload.cultura,
        commodity_id=payload.commodity_id,
        contexto=payload.contexto,
        observacoes=payload.observacoes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(nova)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.conversao.create",
        entidade="unidades_medida_conversoes",
        entidade_id=nova.id,
        descricao=f"Criação de regra de conversão global (Fator: {nova.fator})",
        dados_novos=payload.model_dump(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(nova)

    return AgroUomConversaoResponse.model_validate(nova, from_attributes=True)


@router.put(
    "/conversoes/{conversao_id}",
    response_model=AgroUomConversaoResponse,
    summary="Atualiza uma regra de conversão de unidades",
)
async def update_global_conversao(
    conversao_id: uuid.UUID,
    payload: AgroUomConversaoUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> AgroUomConversaoResponse:
    stmt = select(UnidadeMedidaConversao).where(
        UnidadeMedidaConversao.id == conversao_id,
        UnidadeMedidaConversao.tenant_id.is_(None),
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra de conversão global '{conversao_id}' não encontrada.",
        )

    dados_anteriores = {
        "fator": float(item.fator),
        "cultura": item.cultura,
        "observacoes": item.observacoes,
    }

    if payload.fator is not None:
        item.fator = payload.fator
    if payload.cultura is not None:
        item.cultura = payload.cultura
    if payload.commodity_id is not None:
        item.commodity_id = payload.commodity_id
    if payload.contexto is not None:
        item.contexto = payload.contexto
    if payload.observacoes is not None:
        item.observacoes = payload.observacoes

    item.updated_at = datetime.now(timezone.utc)

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.conversao.update",
        entidade="unidades_medida_conversoes",
        entidade_id=item.id,
        descricao=f"Atualização de regra de conversão global: {item.id}",
        dados_anteriores=dados_anteriores,
        dados_novos=payload.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(item)

    return AgroUomConversaoResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/conversoes/{conversao_id}",
    summary="Remove uma regra de conversão de unidades global",
)
async def delete_global_conversao(
    conversao_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_EDIT)),
) -> dict[str, Any]:
    stmt = select(UnidadeMedidaConversao).where(
        UnidadeMedidaConversao.id == conversao_id,
        UnidadeMedidaConversao.tenant_id.is_(None),
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regra de conversão global '{conversao_id}' não encontrada.",
        )

    admin_uid, admin_email = _extract_admin_info(admin_claims)
    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="agro.catalog.conversao.delete",
        entidade="unidades_medida_conversoes",
        entidade_id=item.id,
        descricao=f"Exclusão de regra de conversão global: {item.id}",
        dados_anteriores={"fator": float(item.fator)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.delete(item)
    await session.commit()

    return {"sucesso": True, "mensagem": "Regra de conversão global excluída com sucesso."}
