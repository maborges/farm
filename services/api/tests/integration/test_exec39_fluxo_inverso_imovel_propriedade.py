"""
EXECUTION-39 — Testes de integração: fluxo inverso Imóvel Rural -> Propriedade existente.

Valida:
  - CREATE de Imóvel Rural com propriedade_id cria PropriedadeImovel canônico
  - CREATE sem propriedade_id não cria vínculo
  - UPDATE com propriedade_id cria vínculo
  - UPDATE idempotente não duplica vínculo
  - Tenant divergente não consegue vincular
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select, text

from core.cadastros.propriedade_imovel.models import PropriedadeImovel, TipoVinculoPropriedadeImovel
from core.cadastros.propriedades.propriedade_models import Propriedade
from core.models.unidade_produtiva import UnidadeProdutiva
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from core.exceptions import EntityNotFoundError
from imoveis.models.imovel import ImovelRural
from imoveis.services.imovel_service import ImovelService


TEST_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _set_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))


async def _criar_unidade(session, tenant_id: uuid.UUID, nome: str, area_total_ha: Decimal = Decimal("200")) -> UnidadeProdutiva:
    service = UnidadeProdutivaService(session, tenant_id, user_id=TEST_USER_ID)
    dados = UnidadeProdutivaCreate(
        nome=nome,
        area_total_ha=area_total_ha,
        municipio="Sorriso",
        uf="MT",
    )
    return await service.create_unidade_produtiva(dados)


async def _criar_propriedade(session, tenant_id: uuid.UUID, nome: str) -> Propriedade:
    propriedade = Propriedade(
        tenant_id=tenant_id,
        nome=nome,
        ie_isento=True,
    )
    session.add(propriedade)
    await session.flush()
    return propriedade


@pytest.mark.asyncio
async def test_create_imovel_com_propriedade_cria_vinculo(session, tenant_id):
    await _set_tenant(session, tenant_id)
    unidade = await _criar_unidade(session, tenant_id, "Fazenda Exec39 Create")
    propriedade = await _criar_propriedade(session, tenant_id, "Propriedade Exec39 Create")

    service = ImovelService(session)
    imovel, _ = await service.criar_imovel(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade.id,
        nome="Imóvel Rural Exec39",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("50"),
        car_numero="MT123456789012",
        ccir_numero="CCIR-EXEC39",
        numero_matricula="12.345",
        propriedade_id=propriedade.id,
        tipo_vinculo=TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL,
        created_by=TEST_USER_ID,
    )
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.propriedade_id == propriedade.id,
        PropriedadeImovel.imovel_rural_id == imovel.id,
        PropriedadeImovel.ativo.is_(True),
    )
    vinculo = (await session.execute(stmt)).scalar_one_or_none()

    assert vinculo is not None
    assert vinculo.tipo_vinculo == TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL.value
    assert vinculo.propriedade_id == propriedade.id
    assert vinculo.imovel_rural_id == imovel.id


@pytest.mark.asyncio
async def test_create_imovel_sem_propriedade_nao_cria_vinculo(session, tenant_id):
    await _set_tenant(session, tenant_id)
    unidade = await _criar_unidade(session, tenant_id, "Fazenda Exec39 Sem Vinculo")

    service = ImovelService(session)
    imovel, _ = await service.criar_imovel(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade.id,
        nome="Imóvel Rural Sem Vínculo",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("50"),
        car_numero="MT123456789013",
        ccir_numero="CCIR-EXEC39-2",
        numero_matricula="12.346",
        created_by=TEST_USER_ID,
    )
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.imovel_rural_id == imovel.id,
    )
    vinculos = (await session.execute(stmt)).scalars().all()

    assert vinculos == []


@pytest.mark.asyncio
async def test_update_imovel_adiciona_vinculo_sem_duplicar(session, tenant_id):
    await _set_tenant(session, tenant_id)
    unidade = await _criar_unidade(session, tenant_id, "Fazenda Exec39 Update")
    propriedade = await _criar_propriedade(session, tenant_id, "Propriedade Exec39 Update")

    service = ImovelService(session)
    imovel, _ = await service.criar_imovel(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade.id,
        nome="Imóvel Update",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("50"),
        car_numero="MT123456789014",
        ccir_numero="CCIR-EXEC39-3",
        numero_matricula="12.347",
        created_by=TEST_USER_ID,
    )
    await session.commit()

    await _set_tenant(session, tenant_id)
    atualizado, _ = await service.atualizar_imovel(
        imovel,
        {
            "propriedade_id": propriedade.id,
            "tipo_vinculo": TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL,
        },
        usuario_id=TEST_USER_ID,
    )
    await session.commit()

    await _set_tenant(session, tenant_id)
    stmt = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.propriedade_id == propriedade.id,
        PropriedadeImovel.imovel_rural_id == atualizado.id,
    )
    vinculos = (await session.execute(stmt)).scalars().all()

    assert len(vinculos) == 1
    assert vinculos[0].ativo is True

    await _set_tenant(session, tenant_id)
    await service.atualizar_imovel(
        atualizado,
        {
            "propriedade_id": propriedade.id,
            "tipo_vinculo": TipoVinculoPropriedadeImovel.PROPRIEDADE_PRINCIPAL,
        },
        usuario_id=TEST_USER_ID,
    )
    await session.commit()

    await _set_tenant(session, tenant_id)
    vinculos = (await session.execute(stmt)).scalars().all()
    assert len(vinculos) == 1, "Atualização idempotente não deve duplicar vínculos"


@pytest.mark.asyncio
async def test_tenant_divergente_bloqueia_vinculo(session, tenant_id, outro_tenant_id):
    await _set_tenant(session, tenant_id)
    unidade_a = await _criar_unidade(session, tenant_id, "Fazenda Exec39 Tenant A")
    propriedade_a = await _criar_propriedade(session, tenant_id, "Propriedade Exec39 Tenant A")
    service_a = ImovelService(session)
    imovel_a, _ = await service_a.criar_imovel(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_a.id,
        nome="Imóvel Tenant A",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("50"),
        car_numero="MT123456789015",
        ccir_numero="CCIR-EXEC39-4",
        numero_matricula="12.348",
        created_by=TEST_USER_ID,
    )
    imovel_a_id = imovel_a.id
    await session.commit()

    await _set_tenant(session, outro_tenant_id)
    unidade_b = await _criar_unidade(session, outro_tenant_id, "Fazenda Exec39 Tenant B")
    service_b = ImovelService(session)

    with pytest.raises(EntityNotFoundError, match="Propriedade não encontrada"):
        await service_b.criar_imovel(
            tenant_id=outro_tenant_id,
            unidade_produtiva_id=unidade_b.id,
            nome="Imóvel Tenant B",
            municipio="Sorriso",
            uf="MT",
            area_total_ha=Decimal("50"),
            car_numero="MT123456789016",
            ccir_numero="CCIR-EXEC39-5",
            numero_matricula="12.349",
            propriedade_id=propriedade_a.id,
            created_by=TEST_USER_ID,
        )

    await session.rollback()

    await _set_tenant(session, tenant_id)
    stmt = select(PropriedadeImovel).where(
        PropriedadeImovel.tenant_id == tenant_id,
        PropriedadeImovel.imovel_rural_id == imovel_a_id,
    )
    assert (await session.execute(stmt)).scalars().all() == []
