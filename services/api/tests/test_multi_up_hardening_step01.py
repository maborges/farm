import uuid
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.operacoes.schemas import OperacaoAgricolaCreate
from agricola.operacoes.service import OperacaoService
from agricola.safras.models import Safra, SafraTalhao
from core.exceptions import BusinessRuleError
from core.models.auth import TenantUsuario, UnidadeProdutivaUsuario, Usuario
from core.operational_context import resolve_unidade_produtiva_context
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.despesa_schema import DespesaCreate, RateioCreate
from financeiro.services.despesa_service import DespesaService


async def _criar_unidade_e_talhao(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    unidade_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nome, true, now(), now())"
        ),
        {"id": str(unidade_id), "tenant_id": str(tenant_id), "nome": f"UP {unidade_id.hex[:6]}"},
    )
    await session.execute(
        text(
            "INSERT INTO cadastros_areas_rurais "
            "(id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :unidade_id, 'TALHAO', :nome, 50, true, now(), now())"
        ),
        {"id": str(talhao_id), "tenant_id": str(tenant_id), "unidade_id": str(unidade_id), "nome": f"T {talhao_id.hex[:6]}"},
    )
    await session.commit()
    return unidade_id, talhao_id


async def _criar_plano_custeio(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    plano_id = uuid.uuid4()
    session.add(
        PlanoConta(
            id=plano_id,
            tenant_id=tenant_id,
            codigo=f"5.1.{plano_id.hex[:6]}",
            nome="Custeio Multi-UP",
            tipo="DESPESA",
            natureza="ANALITICA",
            categoria_rfb="CUSTEIO",
            ativo=True,
        )
    )
    await session.commit()
    return plano_id


async def _criar_usuario_tenant(session: AsyncSession, tenant_id: uuid.UUID, *, is_owner: bool = False) -> uuid.UUID:
    user_id = uuid.uuid4()
    suffix = user_id.hex[:10]
    usuario = Usuario(
        id=user_id,
        email=f"multi-up-{suffix}@agrosaas.test",
        username=f"multi_up_{suffix}",
        nome_completo="Usuario Multi UP",
        ativo=True,
    )
    session.add(usuario)
    await session.flush()
    session.add(
        TenantUsuario(
            tenant_id=tenant_id,
            usuario_id=user_id,
            is_owner=is_owner,
            status="ATIVO",
        )
    )
    await session.commit()
    return user_id


@pytest.mark.asyncio
async def test_operacao_rejeita_talhao_fora_do_vinculo_explicito_da_safra(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    talhao_id: uuid.UUID,
):
    _, talhao_outra_up = await _criar_unidade_e_talhao(session, tenant_id)
    safra = Safra(id=uuid.uuid4(), tenant_id=tenant_id, ano_safra="2025/26", cultura="SOJA", status="COLHEITA")
    session.add(safra)
    session.add(SafraTalhao(tenant_id=tenant_id, safra_id=safra.id, area_id=talhao_id, principal=True, area_ha=100))
    await session.commit()

    service = OperacaoService(session, tenant_id)
    payload = OperacaoAgricolaCreate(
        safra_id=safra.id,
        talhao_id=talhao_outra_up,
        tipo="COLHEITA",
        descricao="Colheita em talhão incompatível",
        data_realizada=date.today(),
        area_aplicada_ha=10,
        insumos=[],
    )

    with pytest.raises(BusinessRuleError, match="Talhão/área não pertence"):
        await service.criar(payload)


@pytest.mark.asyncio
async def test_operacao_cria_despesa_com_unidade_produtiva_derivada_do_talhao(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    talhao_id: uuid.UUID,
):
    await _criar_plano_custeio(session, tenant_id)
    safra = Safra(id=uuid.uuid4(), tenant_id=tenant_id, ano_safra="2025/26", cultura="MILHO", status="COLHEITA")
    session.add(safra)
    session.add(SafraTalhao(tenant_id=tenant_id, safra_id=safra.id, area_id=talhao_id, principal=True, area_ha=100))
    await session.commit()

    service = OperacaoService(session, tenant_id)
    operacao = await service.criar(
        OperacaoAgricolaCreate(
            safra_id=safra.id,
            talhao_id=talhao_id,
            tipo="COLHEITA",
            descricao="Colheita com custo manual",
            data_realizada=date.today(),
            area_aplicada_ha=10,
            custo_total=250,
            insumos=[],
        )
    )

    despesa = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "OPERACAO_AGRICOLA",
                Despesa.origem_id == operacao.id,
            )
        )
    ).scalars().first()
    assert despesa is not None
    assert despesa.unidade_produtiva_id == unidade_produtiva_id


@pytest.mark.asyncio
async def test_despesa_rateio_rejeita_talhao_de_outra_unidade_produtiva(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    _, talhao_outra_up = await _criar_unidade_e_talhao(session, tenant_id)
    plano_id = await _criar_plano_custeio(session, tenant_id)
    service = DespesaService(session, tenant_id)

    payload = DespesaCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        plano_conta_id=plano_id,
        descricao="Despesa rateada em talhão incompatível",
        valor_total=1000,
        data_emissao=date.today(),
        data_vencimento=date.today() + timedelta(days=10),
        rateios=[RateioCreate(talhao_id=talhao_outra_up, valor_rateado=1000, percentual=100)],
    )

    with pytest.raises(BusinessRuleError, match="talhão de outra unidade produtiva"):
        await service.create_with_rateio(payload)


@pytest.mark.asyncio
async def test_contexto_up_permite_usuario_com_acesso_parcial_na_up_correta(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    user_id = await _criar_usuario_tenant(session, tenant_id)
    _, talhao_outra_up = await _criar_unidade_e_talhao(session, tenant_id)
    outra_up = (
        await session.execute(
            text("SELECT unidade_produtiva_id FROM cadastros_areas_rurais WHERE id = :talhao_id"),
            {"talhao_id": str(talhao_outra_up)},
        )
    ).scalar_one()
    session.add(
        UnidadeProdutivaUsuario(
            tenant_id=tenant_id,
            usuario_id=user_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
    )
    await session.commit()

    contexto = await resolve_unidade_produtiva_context(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        user_id=user_id,
        required=True,
    )
    assert contexto.unidade_produtiva_id == unidade_produtiva_id

    with pytest.raises(HTTPException) as exc_info:
        await resolve_unidade_produtiva_context(
            session,
            tenant_id=tenant_id,
            unidade_produtiva_id=outra_up,
            user_id=user_id,
            required=True,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_contexto_up_rejeita_usuario_sem_acesso_a_fazenda(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    user_id = await _criar_usuario_tenant(session, tenant_id)

    with pytest.raises(HTTPException) as exc_info:
        await resolve_unidade_produtiva_context(
            session,
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            user_id=user_id,
            required=True,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_contexto_up_rejeita_header_x_fazenda_id_invalido(
    session: AsyncSession,
    tenant_id: uuid.UUID,
):
    request = SimpleNamespace(headers={"x-fazenda-id": "nao-e-uuid"}, query_params={})

    with pytest.raises(HTTPException) as exc_info:
        await resolve_unidade_produtiva_context(
            session,
            tenant_id=tenant_id,
            request=request,
            required=True,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_contexto_up_rejeita_unidade_de_outro_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(outro_tenant_id), "nome": "Tenant Outro", "doc": str(outro_tenant_id)[:11]},
    )
    await session.commit()
    outra_up, _ = await _criar_unidade_e_talhao(session, outro_tenant_id)

    with pytest.raises(BusinessRuleError, match="Unidade produtiva"):
        await resolve_unidade_produtiva_context(
            session,
            tenant_id=tenant_id,
            unidade_produtiva_id=outra_up,
            required=True,
        )
