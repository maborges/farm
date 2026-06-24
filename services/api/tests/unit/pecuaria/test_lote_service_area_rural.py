import uuid

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from core.cadastros.propriedades.models import TipoArea
from pecuaria.schemas.lote_schema import LoteBovinoCreate
from pecuaria.services.lote_service import LoteBovinoService


async def _criar_area(
    session,
    *,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    tipo: str = TipoArea.PIQUETE.value,
    nome: str = "Piquete Teste",
) -> uuid.UUID:
    area_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais
                (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at)
            VALUES
                (:id, :tenant_id, :unidade_produtiva_id, :tipo, :nome, 10.0, true, NOW(), NOW())
            """
        ),
        {
            "id": str(area_id),
            "tenant_id": str(tenant_id),
            "unidade_produtiva_id": str(unidade_produtiva_id),
            "tipo": tipo,
            "nome": nome,
        },
    )
    await session.commit()
    return area_id


async def _criar_unidade_produtiva(session, *, tenant_id: uuid.UUID) -> uuid.UUID:
    unidade_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :nome, true, NOW(), NOW())
            """
        ),
        {
            "id": str(unidade_id),
            "tenant_id": str(tenant_id),
            "nome": "Unidade de Teste",
        },
    )
    await session.commit()
    return unidade_id


def test_lote_schema_aceita_area_id_como_alias():
    area_id = uuid.uuid4()
    payload = LoteBovinoCreate.model_validate(
        {
            "unidade_produtiva_id": str(uuid.uuid4()),
            "area_id": str(area_id),
            "identificacao": "Lote Alias",
            "categoria": "Novilhas",
            "raca": "Nelore",
            "quantidade_cabecas": 12,
        }
    )

    assert payload.piquete_id == area_id


@pytest.mark.asyncio
async def test_create_lote_aceita_area_rural_piquete(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    area_id = await _criar_area(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo=TipoArea.PIQUETE.value,
    )
    service = LoteBovinoService(tenant_id)
    payload = LoteBovinoCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        piquete_id=area_id,
        identificacao="Lote Piquete",
        categoria="Recria",
        raca="Nelore",
        quantidade_cabecas=20,
        peso_medio_kg=250.0,
    )

    lote = await service.create_lote(session, obj_in=payload)

    assert lote.area_id == area_id
    assert lote.tenant_id == tenant_id
    assert (await session.execute(text("SELECT count(*) FROM pec_piquetes"))).scalar_one() == 0


@pytest.mark.asyncio
async def test_create_lote_bloqueia_area_de_outro_tenant(
    session,
    tenant_id: uuid.UUID,
    outro_tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    outra_unidade_id = await _criar_unidade_produtiva(session, tenant_id=outro_tenant_id)
    area_id = await _criar_area(
        session,
        tenant_id=outro_tenant_id,
        unidade_produtiva_id=outra_unidade_id,
        tipo=TipoArea.PIQUETE.value,
    )
    service = LoteBovinoService(tenant_id)
    payload = LoteBovinoCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        piquete_id=area_id,
        identificacao="Lote Tenant",
        categoria="Recria",
        raca="Nelore",
        quantidade_cabecas=10,
    )

    with pytest.raises(BusinessRuleError, match="não existe, está inativo ou não pertence"):
        await service.create_lote(session, obj_in=payload)


@pytest.mark.asyncio
async def test_create_lote_bloqueia_area_de_outra_unidade_produtiva(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    outra_unidade_id = await _criar_unidade_produtiva(session, tenant_id=tenant_id)
    area_id = await _criar_area(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=outra_unidade_id,
        tipo=TipoArea.PIQUETE.value,
    )
    service = LoteBovinoService(tenant_id)
    payload = LoteBovinoCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        piquete_id=area_id,
        identificacao="Lote Unidade",
        categoria="Recria",
        raca="Nelore",
        quantidade_cabecas=10,
    )

    with pytest.raises(BusinessRuleError, match="não existe, está inativo ou não pertence"):
        await service.create_lote(session, obj_in=payload)


@pytest.mark.asyncio
async def test_create_lote_bloqueia_tipo_incompativel(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
):
    area_id = await _criar_area(
        session,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo=TipoArea.TALHAO.value,
        nome="Talhão Teste",
    )
    service = LoteBovinoService(tenant_id)
    payload = LoteBovinoCreate(
        unidade_produtiva_id=unidade_produtiva_id,
        piquete_id=area_id,
        identificacao="Lote Tipo",
        categoria="Recria",
        raca="Nelore",
        quantidade_cabecas=10,
    )

    with pytest.raises(BusinessRuleError, match="não existe, está inativo ou não pertence"):
        await service.create_lote(session, obj_in=payload)
