from decimal import Decimal
import uuid

import pytest
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from core.cadastros.propriedades.models import AreaRural, FILHOS_PERMITIDOS, TipoArea, TipoIrrigacao, TipoSolo
from core.cadastros.propriedades.schemas import AreaRuralUpdate
from core.cadastros.propriedades.service import AreaRuralService
from core.exceptions import BusinessRuleError
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: AreaRural.__table__.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    UnidadeProdutiva.__table__,
                    TipoSolo.__table__,
                    TipoIrrigacao.__table__,
                    AreaRural.__table__,
                    PlanoAssinatura.__table__,
                    AssinaturaTenant.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_hierarquia_permite_piquete_direto_na_gleba_e_subdivisoes_no_talhao():
    assert TipoArea.PIQUETE in FILHOS_PERMITIDOS[TipoArea.GLEBA]
    assert TipoArea.TALHAO in FILHOS_PERMITIDOS[TipoArea.GLEBA]
    assert TipoArea.SUBTALHAO in FILHOS_PERMITIDOS[TipoArea.TALHAO]
    assert TipoArea.ZONA_MANEJO in FILHOS_PERMITIDOS[TipoArea.TALHAO]
    assert TipoArea.PIQUETE in FILHOS_PERMITIDOS[TipoArea.TALHAO]


@pytest.mark.asyncio
async def test_validar_hierarquia_e_listar_apenas_produtivas(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    gleba_id = uuid.uuid4()
    talhao_id = uuid.uuid4()
    piquete_id = uuid.uuid4()
    app_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Mista", slug="faz-mista", documento="11111111000101"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade 1"),
        AreaRural(id=gleba_id, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, nome="Gleba A", tipo="GLEBA", ativo=True),
        AreaRural(id=talhao_id, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, parent_id=gleba_id, nome="Talhão 01", tipo="TALHAO", ativo=True),
        AreaRural(id=piquete_id, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, parent_id=gleba_id, nome="Piquete 01", tipo="PIQUETE", ativo=True),
        AreaRural(id=app_id, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, parent_id=gleba_id, nome="APP Nascente", tipo="APP", ativo=True),
    ])
    await async_session.commit()

    svc = AreaRuralService(AreaRural, async_session, tenant_id)

    # GLEBA -> PIQUETE e TALHAO -> PIQUETE devem passar sem erro
    await svc._validar_hierarquia(TipoArea.PIQUETE, gleba_id)
    await svc._validar_hierarquia(TipoArea.PIQUETE, talhao_id)

    # PIQUETE -> TALHAO continua proibido
    with pytest.raises(BusinessRuleError):
        await svc._validar_hierarquia(TipoArea.TALHAO, piquete_id)

    produtivas = await svc.listar(unidade_produtiva_id=fazenda_id, apenas_produtivas=True)
    nomes = {a.nome for a in produtivas}
    assert nomes == {"Talhão 01", "Piquete 01"}


@pytest.mark.asyncio
async def test_desmarcar_geometria_area_rural(async_session: AsyncSession):
    tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    gleba_id = uuid.uuid4()
    talhao_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=tenant_id, nome="Fazenda Geo", slug="faz-geo", documento="22222222000102"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Unidade Geo"),
        AreaRural(id=gleba_id, tenant_id=tenant_id, unidade_produtiva_id=fazenda_id, nome="Gleba Geo", tipo="GLEBA", ativo=True),
        AreaRural(
            id=talhao_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            parent_id=gleba_id,
            nome="Talhão Mapeado",
            tipo="TALHAO",
            area_hectares=Decimal("25.5000"),
            area_hectares_manual=Decimal("26.0000"),
            geometria={
                "type": "Polygon",
                "coordinates": [[[-51.9, -23.4], [-51.89, -23.4], [-51.89, -23.39], [-51.9, -23.39], [-51.9, -23.4]]],
            },
            centroide_lat=-23.395,
            centroide_lng=-51.895,
            ativo=True,
        ),
    ])
    await async_session.commit()

    payload = AreaRuralUpdate(
        geometria=None,
        area_hectares=None,
        centroide_lat=None,
        centroide_lng=None,
    ).model_dump(exclude_unset=True)

    assert set(payload.keys()) == {"geometria", "area_hectares", "centroide_lat", "centroide_lng"}

    svc = AreaRuralService(AreaRural, async_session, tenant_id)
    atualizado = await svc.atualizar_area(talhao_id, payload)

    assert atualizado.geometria is None
    assert atualizado.area_hectares is None
    assert atualizado.centroide_lat is None
    assert atualizado.centroide_lng is None
    assert atualizado.nome == "Talhão Mapeado"
    assert atualizado.area_hectares_manual == Decimal("26.0000")
