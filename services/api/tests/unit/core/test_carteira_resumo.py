from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from agricola.caderno.models import VisitaTecnica
from agricola.safras.models import Safra
from core.models.auth import Usuario
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.services.carteira_service import CarteiraService
from notificacoes.models import Notificacao


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Safra.__table__.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Usuario.__table__,
                    UnidadeProdutiva.__table__,
                    Safra.__table__,
                    Notificacao.__table__,
                    VisitaTecnica.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_obter_resumo_carteira_isola_tenants_e_consolida_contadores(async_session: AsyncSession):
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    t1_id = uuid.uuid4()
    t2_id = uuid.uuid4()
    t3_nao_vinculado_id = uuid.uuid4()

    f1_id = uuid.uuid4()
    s1_id = uuid.uuid4()
    talhao_id = uuid.uuid4()

    async_session.add_all([
        Tenant(id=t1_id, nome="Fazenda Aurora", slug="fazenda-aurora", documento="11111111000101"),
        Tenant(id=t2_id, nome="Sítio Bela Vista", slug="sitio-bela-vista", documento="22222222000102"),
        Tenant(id=t3_nao_vinculado_id, nome="Fazenda Terceira", slug="fazenda-terceira", documento="33333333000103"),
        Safra(id=s1_id, tenant_id=t1_id, ano_safra="2026", status="EM_ANDAMENTO"),
        Safra(id=uuid.uuid4(), tenant_id=t1_id, ano_safra="2025", status="ENCERRADA"),
        Safra(id=uuid.uuid4(), tenant_id=t2_id, ano_safra="2026", status="PLANEJADA"),
        Safra(id=uuid.uuid4(), tenant_id=t3_nao_vinculado_id, ano_safra="2026", status="EM_ANDAMENTO"),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            tipo="ALERTA",
            titulo="Alerta 1",
            mensagem="Msg",
            lida=False,
            usuario_id=None,
        ),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            tipo="ALERTA",
            titulo="Alerta Lido",
            mensagem="Msg",
            lida=True,
            usuario_id=None,
        ),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            tipo="ALERTA",
            titulo="Alerta Outro Usuario",
            mensagem="Msg",
            lida=False,
            usuario_id=other_user_id,
        ),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t2_id,
            tipo="ALERTA",
            titulo="Alerta T2 A",
            mensagem="Msg",
            lida=False,
            usuario_id=user_id,
        ),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t2_id,
            tipo="ALERTA",
            titulo="Alerta T2 B",
            mensagem="Msg",
            lida=False,
            usuario_id=None,
        ),
        Notificacao(
            id=uuid.uuid4(),
            tenant_id=t3_nao_vinculado_id,
            tipo="ALERTA",
            titulo="Alerta T3",
            mensagem="Msg",
            lida=False,
            usuario_id=None,
        ),
        VisitaTecnica(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            safra_id=s1_id,
            talhao_id=talhao_id,
            responsavel_tecnico_id=user_id,
            nome_rt="Eng. Carlos",
            crea="CREA-MG 1234",
            data_visita=date(2026, 10, 10),
        ),
        VisitaTecnica(
            id=uuid.uuid4(),
            tenant_id=t1_id,
            safra_id=s1_id,
            talhao_id=talhao_id,
            responsavel_tecnico_id=user_id,
            nome_rt="Eng. Carlos",
            crea="CREA-MG 1234",
            data_visita=date(2026, 11, 5),
        ),
    ])
    await async_session.commit()

    fake_me = SimpleNamespace(
        tenants=[
            SimpleNamespace(
                tenant_id=t1_id,
                nome_tenant="Fazenda Aurora",
                is_owner=False,
                perfil=SimpleNamespace(nome="Consultor"),
                fazendas=[SimpleNamespace(unidade_produtiva_id=f1_id, nome="Unidade Sede")],
            ),
            SimpleNamespace(
                tenant_id=t2_id,
                nome_tenant="Sítio Bela Vista",
                is_owner=True,
                perfil=SimpleNamespace(nome="Owner"),
                fazendas=[],
            ),
        ]
    )

    with patch("core.services.carteira_service.AuthService.get_user_me", new=AsyncMock(return_value=fake_me)):
        resumo = await CarteiraService(async_session).obter_resumo_carteira(user_id)

    assert resumo["total_tenants"] == 2
    assert resumo["total_propriedades"] == 1
    assert resumo["total_safras_ativas"] == 2
    assert resumo["total_alertas_abertos"] == 3

    # Ordenado por alertas_abertos desc: Sítio Bela Vista (2) antes de Fazenda Aurora (1)
    assert [t["tenant_id"] for t in resumo["tenants"]] == [str(t2_id), str(t1_id)]

    sitio = resumo["tenants"][0]
    assert sitio["alertas_abertos"] == 2
    assert sitio["safras_ativas"] == 1
    assert sitio["ultima_visita_tecnica"] is None

    aurora = resumo["tenants"][1]
    assert aurora["alertas_abertos"] == 1
    assert aurora["safras_ativas"] == 1
    assert aurora["total_propriedades"] == 1
    assert aurora["ultima_visita_tecnica"] == "2026-11-05"
