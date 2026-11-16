import uuid
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.database import Base
from core.models.auth import PerfilAcesso
from core.models.tenant import Tenant
from core.services.onboarding_service import OnboardingService


@pytest.fixture
async def sqlite_session():
    """Cria uma sessão isolada com SQLite em memória para testes do serviço."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c, tables=[Tenant.__table__, PerfilAcesso.__table__]
            )
        )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_perfil_owner_sistema_auto_provisions_when_missing(sqlite_session):
    """Verifica se o perfil Owner é provisionado automaticamente quando ausente."""
    service = OnboardingService(sqlite_session)
    perfil = await service._get_perfil_owner_sistema()

    assert perfil is not None
    assert perfil.id == uuid.UUID("671656ad-1e32-4244-a2d8-0e4dbbddd072")
    assert perfil.nome == "Owner"
    assert perfil.is_custom is False
    assert perfil.tenant_id is None
    assert perfil.permissoes == {"*": "*"}


@pytest.mark.asyncio
async def test_get_perfil_owner_sistema_matches_title_case_owner(sqlite_session):
    """Verifica se encontra o perfil quando cadastrado como 'Owner'."""
    existing_id = uuid.uuid4()
    perfil_salvo = PerfilAcesso(
        id=existing_id,
        tenant_id=None,
        nome="Owner",
        is_custom=False,
        permissoes={"*": "*"},
        descricao="Perfil existente",
    )
    sqlite_session.add(perfil_salvo)
    await sqlite_session.flush()

    service = OnboardingService(sqlite_session)
    perfil = await service._get_perfil_owner_sistema()

    assert perfil is not None
    assert perfil.id == existing_id
    assert perfil.nome == "Owner"


@pytest.mark.asyncio
async def test_get_perfil_owner_sistema_matches_lowercase_owner(sqlite_session):
    """Verifica se encontra o perfil quando cadastrado como 'owner'."""
    existing_id = uuid.uuid4()
    perfil_salvo = PerfilAcesso(
        id=existing_id,
        tenant_id=None,
        nome="owner",
        is_custom=False,
        permissoes={"*": "*"},
        descricao="Perfil lowercase",
    )
    sqlite_session.add(perfil_salvo)
    await sqlite_session.flush()

    service = OnboardingService(sqlite_session)
    perfil = await service._get_perfil_owner_sistema()

    assert perfil is not None
    assert perfil.id == existing_id
    assert perfil.nome == "owner"


@pytest.mark.asyncio
async def test_get_perfil_owner_sistema_matches_canonical_id(sqlite_session):
    """Verifica se encontra o perfil pelo ID canônico mesmo se nome for personalizado."""
    canonical_id = uuid.UUID("671656ad-1e32-4244-a2d8-0e4dbbddd072")
    perfil_salvo = PerfilAcesso(
        id=canonical_id,
        tenant_id=None,
        nome="Proprietário Geral",
        is_custom=False,
        permissoes={"*": "*"},
        descricao="Perfil canonico",
    )
    sqlite_session.add(perfil_salvo)
    await sqlite_session.flush()

    service = OnboardingService(sqlite_session)
    perfil = await service._get_perfil_owner_sistema()

    assert perfil is not None
    assert perfil.id == canonical_id
    assert perfil.nome == "Proprietário Geral"
