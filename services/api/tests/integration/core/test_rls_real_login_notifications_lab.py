"""Real product login and notification routes against the isolated RLS lab."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import MetaData, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.schema import CreateTable

from core.config import settings
from core.database import (
    AUTHENTICATION_DB_URL,
    DB_URL,
    async_session_maker,
    authentication_async_session_maker,
    engine,
)
from core.services.auth_service import hash_password


RUNTIME_URL = os.getenv("DEEPFARMS_RLS_LAB_DATABASE_URL")
DEPLOY_URL = os.getenv("DEEPFARMS_RLS_LAB_DEPLOY_URL")
AUTH_URL = os.getenv("AUTHENTICATION_DATABASE_URL")
SCHEMA_TABLES = (
    "tenants", "usuarios", "tenant_usuarios", "perfis_acesso",
    "unidade_produtiva_usuarios", "login_tentativas", "sessoes_ativas",
    "planos_assinatura", "assinaturas_tenant", "unidades_produtivas",
    "configuracoes_saas", "configuracoes_tenant", "notificacoes",
    "notificacoes_leituras", "notificacoes_preferencias",
    "tenant_audit_log",
)
FIXTURE_TABLES = tuple(name for name in SCHEMA_TABLES if name != "tenants")


def _model_tables():
    from core.models.auth import (
        PerfilAcesso, TentativaLogin, TenantUsuario,
        UnidadeProdutivaUsuario, Usuario,
    )
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from core.models.configuration import ConfiguracaoSaaS
    from core.models.sessao import SessaoAtiva
    from core.models.tenant import Tenant
    from core.models.tenant_config import ConfiguracaoTenant
    from core.models.tenant_audit_log import TenantAuditLog
    from core.models.unidade_produtiva import UnidadeProdutiva
    from notificacoes.models import Notificacao, NotificacaoLeitura, NotificacaoPreferencia

    return [
        model.__table__ for model in (
            Tenant, Usuario, TenantUsuario, PerfilAcesso, UnidadeProdutivaUsuario,
            TentativaLogin, SessaoAtiva, PlanoAssinatura, AssinaturaTenant,
            UnidadeProdutiva, ConfiguracaoSaaS, ConfiguracaoTenant,
            Notificacao, NotificacaoLeitura, NotificacaoPreferencia,
            TenantAuditLog,
        )
    ]


def _validate_lab_urls():
    expected = ("192.168.0.3", 5432, "deepfarms_rls_lab")
    assert RUNTIME_URL and DEPLOY_URL and AUTH_URL
    for value, username in (
        (RUNTIME_URL, "deepfarms_rls_lab_runtime"),
        (DEPLOY_URL, "deepfarms_rls_lab_deploy"),
        (AUTH_URL, "deepfarms_rls_lab_auth"),
    ):
        url = make_url(value)
        assert (url.host, url.port, url.database, url.username) == (*expected, username)
    assert make_url(DB_URL).username == "deepfarms_rls_lab_runtime"
    assert make_url(AUTHENTICATION_DB_URL).username == "deepfarms_rls_lab_auth"
    assert settings.require_restricted_runtime_role is True
    assert authentication_async_session_maker is not None


async def _create_fixture_tables(deploy_engine, created):
    # The lab already contains a dispatcher-owned tenants table and sparse
    # usuarios/unidades_produtivas fixtures. Reuse those relations without
    # changing tenants or deleting any pre-existing rows.
    preexisting = {"tenants", "usuarios", "unidades_produtivas"}
    column_definitions = {
        "usuarios": {
            "email": "varchar(255)", "username": "varchar(50)",
            "senha_hash": "varchar(255)",
            "is_superuser": "boolean NOT NULL DEFAULT false",
            "ativo": "boolean NOT NULL DEFAULT true",
        },
        "unidades_produtivas": {
            "tenant_id": "uuid", "nome": "varchar(150)",
            "ativo": "boolean NOT NULL DEFAULT true",
        },
    }
    columns_to_restore = {}
    async with deploy_engine.begin() as connection:
        identity = (await connection.execute(
            text("SELECT current_database(), current_user, session_user")
        )).one()
        assert tuple(identity) == (
            "deepfarms_rls_lab", "deepfarms_rls_lab_deploy", "deepfarms_rls_lab_deploy"
        )
        existing = (await connection.execute(text(
            "SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='farms' AND c.relname = ANY(:names)"
        ), {"names": list(SCHEMA_TABLES)})).scalars().all()
        partial_fixture = set(existing).difference(preexisting)
        await connection.execute(text("SET LOCAL ROLE deepfarms_rls_lab_owner"))
        owner_identity = (await connection.execute(
            text("SELECT current_database(), current_user, session_user")
        )).one()
        assert tuple(owner_identity) == (
            "deepfarms_rls_lab", "deepfarms_rls_lab_owner", "deepfarms_rls_lab_deploy"
        )
        if partial_fixture:
            partial_state = (await connection.execute(text(
                "SELECT c.relname, pg_get_userbyid(c.relowner) AS owner, "
                "c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='farms' AND c.relname = ANY(:names)"
            ), {"names": sorted(partial_fixture)})).all()
            assert len(partial_state) == len(partial_fixture)
            assert all(row.owner == "deepfarms_rls_lab_owner" for row in partial_state)
            for name in partial_fixture:
                count = (await connection.execute(
                    text(f"SELECT count(*) FROM farms.{name}")
                )).scalar_one()
                assert count == 0, f"Refusing to reuse non-empty partial fixture {name}"
            # These are empty product-shaped tables committed by the failed
            # setup attempt in this same test; mark them for teardown.
            created.extend(sorted(partial_fixture))
        auth_schema_usage = (await connection.execute(text(
            "SELECT has_schema_privilege('deepfarms_rls_lab_auth', 'farms', 'USAGE')"
        ))).scalar_one()
        rls_state = (await connection.execute(text(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='farms' AND c.relname=ANY(:names)"
        ), {"names": existing})).all()
        no_policy_relations = {"usuarios", "unidades_produtivas"}.intersection(existing)
        prior_fixture_policies = set((await connection.execute(text(
            "SELECT c.relname FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='farms' AND p.polname = ANY(:names)"
        ), {"names": [f"{name}_lab_fixture_owner" for name in no_policy_relations]})).scalars())
        # A previous interrupted setup may have committed its temporary RLS
        # columns/policy. Track the original pre-fixture state for cleanup.
        rls_state = [
            (row.relname, False, False)
            if row.relname in prior_fixture_policies else
            (row.relname, row.relrowsecurity, row.relforcerowsecurity)
            for row in rls_state
        ]
        for name in set(existing).intersection({"usuarios", "unidades_produtivas"}):
            if name not in prior_fixture_policies:
                await connection.execute(text(
                    f"CREATE POLICY {name}_lab_fixture_owner ON farms.{name} FOR ALL "
                    "TO deepfarms_rls_lab_owner USING (true) WITH CHECK (true)"
                ))
        if "usuarios" in existing:
            columns_to_restore["usuarios"] = await _add_missing_fixture_columns(
                connection, "usuarios", column_definitions["usuarios"]
            )
            await connection.execute(text(
                "ALTER TABLE farms.usuarios ENABLE ROW LEVEL SECURITY"
            ))
            await connection.execute(text(
                "ALTER TABLE farms.usuarios FORCE ROW LEVEL SECURITY"
            ))
        if "unidades_produtivas" in existing:
            columns_to_restore["unidades_produtivas"] = await _add_missing_fixture_columns(
                connection, "unidades_produtivas", column_definitions["unidades_produtivas"]
            )
            await connection.execute(text(
                "ALTER TABLE farms.unidades_produtivas ENABLE ROW LEVEL SECURITY"
            ))
            await connection.execute(text(
                "ALTER TABLE farms.unidades_produtivas FORCE ROW LEVEL SECURITY"
            ))
        for table in _model_tables():
            if table.name in existing:
                continue
            lab_table = table.to_metadata(MetaData(), schema="farms")
            ddl = CreateTable(
                lab_table,
                include_foreign_key_constraints=set(),
            ).compile(dialect=connection.dialect)
            await connection.execute(text(str(ddl)))
            created.append(table.name)
    original_relations = set(existing).difference(partial_fixture)
    return original_relations, columns_to_restore, rls_state, auth_schema_usage


async def _add_missing_fixture_columns(connection, table, definitions):
    existing = set((await connection.execute(text(
        "SELECT attname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='farms' AND c.relname=:table AND a.attnum > 0 "
        "AND NOT a.attisdropped"
    ), {"table": table})).scalars())
    missing = {name: definition for name, definition in definitions.items() if name not in existing}
    if missing:
        additions = ", ".join(f"ADD COLUMN {name} {definition}" for name, definition in missing.items())
        await connection.execute(text(f"ALTER TABLE farms.{table} {additions}"))
    return tuple(missing)


async def _apply_policies_and_grants(connection, preexisting):
    await connection.execute(text("SET LOCAL ROLE deepfarms_rls_lab_owner"))
    runtime_tenant_tables = (
        "tenant_usuarios", "perfis_acesso", "unidade_produtiva_usuarios",
        "assinaturas_tenant", "unidades_produtivas", "notificacoes",
    )
    for table in FIXTURE_TABLES:
        await connection.execute(text(f"ALTER TABLE farms.{table} ENABLE ROW LEVEL SECURITY"))
        await connection.execute(text(f"ALTER TABLE farms.{table} FORCE ROW LEVEL SECURITY"))
        if table not in preexisting:
            await connection.execute(text(
                f"CREATE POLICY {table}_lab_owner ON farms.{table} FOR ALL "
                "TO deepfarms_rls_lab_owner USING (true) WITH CHECK (true)"
            ))

    policies = {
        "usuarios": "id = NULLIF(current_setting('app.current_user_id', true), '')::uuid",
        "tenant_usuarios": "usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid",
        "perfis_acesso": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "unidade_produtiva_usuarios": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "assinaturas_tenant": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "unidades_produtivas": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "notificacoes": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "tenant_audit_log": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "sessoes_ativas": "usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid",
        "configuracoes_saas": "chave = 'sessao'",
        "login_tentativas": "lower(email) = NULLIF(current_setting('app.current_login_email', true), '')",
        "configuracoes_tenant": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid",
        "notificacoes_leituras": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid AND usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid",
        "notificacoes_preferencias": "tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid AND usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid",
    }
    for table, predicate in policies.items():
        await connection.execute(text(
            f"CREATE POLICY {table}_lab_runtime ON farms.{table} "
            f"FOR ALL TO deepfarms_rls_lab_runtime USING ({predicate}) WITH CHECK ({predicate})"
        ))
    await connection.execute(text(
        "CREATE POLICY planos_assinatura_lab_runtime ON farms.planos_assinatura "
        "FOR SELECT TO deepfarms_rls_lab_runtime USING (true)"
    ))
    await connection.execute(text(
        "CREATE POLICY login_tentativas_lab_auth ON farms.login_tentativas "
        "FOR ALL TO deepfarms_rls_lab_auth USING "
        "(lower(email)=NULLIF(current_setting('app.current_login_email', true), '')) "
        "WITH CHECK (lower(email)=NULLIF(current_setting('app.current_login_email', true), ''))"
    ))

    await connection.execute(text("GRANT USAGE ON SCHEMA farms TO deepfarms_rls_lab_runtime, deepfarms_rls_lab_auth"))
    await connection.execute(text(
        "GRANT SELECT (id, ativo) ON farms.usuarios TO deepfarms_rls_lab_runtime"
    ))
    for table in runtime_tenant_tables:
        await connection.execute(text(f"GRANT SELECT ON farms.{table} TO deepfarms_rls_lab_runtime"))
    await connection.execute(text("GRANT SELECT ON farms.planos_assinatura TO deepfarms_rls_lab_runtime"))
    await connection.execute(text(
        "GRANT SELECT, INSERT, UPDATE ON farms.sessoes_ativas TO deepfarms_rls_lab_runtime"
    ))
    await connection.execute(text(
        "GRANT SELECT (chave, valor, ativo) ON farms.configuracoes_saas TO deepfarms_rls_lab_runtime"
    ))
    await connection.execute(text(
        "GRANT SELECT (tenant_id, categoria, chave, valor, ativo) "
        "ON farms.configuracoes_tenant TO deepfarms_rls_lab_runtime"
    ))
    await connection.execute(text("GRANT SELECT ON farms.notificacoes_leituras, farms.notificacoes_preferencias TO deepfarms_rls_lab_runtime"))
    await connection.execute(text("GRANT SELECT, INSERT ON farms.notificacoes TO deepfarms_rls_lab_runtime"))
    await connection.execute(text("GRANT INSERT ON farms.tenant_audit_log TO deepfarms_rls_lab_runtime"))
    await connection.execute(text(
        "GRANT SELECT, INSERT, UPDATE ON farms.login_tentativas TO deepfarms_rls_lab_auth"
    ))

    script = Path(__file__).parents[3] / "scripts/rls/lab_auth_login_material.sql"
    source = script.read_text()
    await connection.execute(text("DROP FUNCTION IF EXISTS farms.auth_login_material(text)"))
    source = source.replace("DROP FUNCTION IF EXISTS farms.auth_login_material(text);", "")
    chunks = source.split("$function$;")
    await connection.execute(text(chunks[0] + "$function$;"))
    for statement in chunks[1].split(";"):
        if statement.strip():
            await connection.execute(text(statement))


async def _seed_lab(deploy_engine, ids):
    from core.models.auth import PerfilAcesso, TenantUsuario, Usuario
    from core.models.billing import AssinaturaTenant, PlanoAssinatura
    from core.models.configuration import ConfiguracaoSaaS
    from core.models.tenant_config import ConfiguracaoTenant

    async with AsyncSession(deploy_engine, expire_on_commit=False) as session:
        await session.execute(text("SET LOCAL ROLE deepfarms_rls_lab_owner"))
        for tenant_key in ("a", "b"):
            tenant_id, user_id, profile_id, plan_id = (
                ids[f"tenant_{tenant_key}"], ids[f"user_{tenant_key}"],
                ids[f"profile_{tenant_key}"], ids[f"plan_{tenant_key}"],
            )
            await session.execute(text(
                "INSERT INTO farms.usuarios "
                "(id, email, username, senha_hash, is_superuser, ativo) "
                "VALUES (:id, :email, :username, :hash, false, true)"
            ), {
                "id": str(user_id),
                "email": f"rls-{tenant_key}@example.com",
                "username": f"rls_{tenant_key}",
                "hash": hash_password("Laboratorio@2026"),
            })
            session.add_all([
                PerfilAcesso(
                    id=profile_id, tenant_id=tenant_id, nome="admin",
                    is_custom=False, permissoes={},
                ),
                TenantUsuario(
                    tenant_id=tenant_id, usuario_id=user_id, perfil_id=profile_id,
                    is_owner=True, status="ATIVO",
                ),
                PlanoAssinatura(
                    id=plan_id, nome=f"Lab {tenant_key.upper()}",
                    modulos_inclusos=["CORE"], plan_tier="BASICO", max_fazendas=1,
                ),
                AssinaturaTenant(
                    tenant_id=tenant_id, plano_id=plan_id,
                    usuarios_contratados=2, status="ATIVA",
                ),
                ConfiguracaoTenant(
                    tenant_id=tenant_id, categoria="seguranca",
                    chave="rate_limiting_ativo", valor=True, ativo=True,
                ),
                ConfiguracaoTenant(
                    tenant_id=tenant_id, categoria="seguranca",
                    chave="max_tentativas", valor=2 if tenant_key == "a" else 7, ativo=True,
                ),
                ConfiguracaoTenant(
                    tenant_id=tenant_id, categoria="seguranca",
                    chave="tempo_bloqueio_minutos", valor=15, ativo=True,
                ),
            ])
        session.add(ConfiguracaoSaaS(
            chave="sessao", valor={"tempo_inatividade_minutos": 30}, ativo=True,
        ))
        await session.commit()


@pytest_asyncio.fixture
async def real_api_rls_lab():
    _validate_lab_urls()
    from core.database import authentication_engine

    deploy_engine = create_async_engine(
        DEPLOY_URL,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": "farms,pg_catalog"}},
    )
    created = []
    preexisting = set()
    columns_to_restore = {}
    rls_state = []
    auth_schema_usage = False
    ids = {key: uuid.uuid4() for key in (
        "tenant_a", "tenant_b", "user_a", "user_b",
        "profile_a", "profile_b", "plan_a", "plan_b",
    )}
    app_ref = None
    try:
        preexisting, columns_to_restore, rls_state, auth_schema_usage = await _create_fixture_tables(
            deploy_engine, created
        )
        async with deploy_engine.begin() as connection:
            identity = (await connection.execute(text(
                "SELECT current_database(), current_user, session_user"
            ))).one()
            assert tuple(identity) == (
                "deepfarms_rls_lab", "deepfarms_rls_lab_deploy", "deepfarms_rls_lab_deploy"
            )
            await _apply_policies_and_grants(connection, preexisting)
        await _seed_lab(deploy_engine, ids)

        async with engine.connect() as connection:
            rights = (await connection.execute(text(
                "SELECT has_column_privilege(current_user, 'farms.usuarios', 'senha_hash', 'SELECT'), "
                "has_function_privilege(current_user, 'farms.auth_login_material(text)', 'EXECUTE')"
            ))).one()
            assert tuple(rights) == (False, False)
        async with authentication_async_session_maker() as auth_session:
            auth_rights = (await auth_session.execute(text(
                "SELECT has_function_privilege(current_user, 'farms.auth_login_material(text)', 'EXECUTE'), "
                "has_table_privilege(current_user, 'farms.usuarios', 'SELECT'), "
                "has_table_privilege(current_user, 'farms.tenant_usuarios', 'SELECT'), "
                "has_table_privilege(current_user, 'farms.configuracoes_tenant', 'SELECT')"
            ))).one()
            assert tuple(auth_rights) == (True, False, False, False)
        async with deploy_engine.connect() as connection:
            function_result = (await connection.execute(text(
                "SELECT pg_get_function_result(p.oid) FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid=p.pronamespace "
                "WHERE n.nspname='farms' AND p.proname='auth_login_material'"
            ))).scalar_one()
            assert "tenant_id" not in function_result
            assert "rate_limiting" not in function_result

        from main import app
        app_ref = app
        yield app, ids, deploy_engine
    finally:
        if created:
            async with deploy_engine.begin() as connection:
                await connection.execute(text("SET LOCAL ROLE deepfarms_rls_lab_owner"))
                await connection.execute(text("DROP FUNCTION IF EXISTS farms.auth_login_material(text)"))
                for name in reversed(created):
                    await connection.execute(text(f"DROP TABLE IF EXISTS farms.{name} CASCADE"))
                if "usuarios" in preexisting:
                    await connection.execute(text(
                        "DELETE FROM farms.usuarios WHERE id = ANY(:ids)"
                    ), {"ids": [ids["user_a"], ids["user_b"]]})
                    await connection.execute(text(
                        "REVOKE SELECT (id, ativo) ON farms.usuarios "
                        "FROM deepfarms_rls_lab_runtime"
                    ))
                if "unidades_produtivas" in preexisting:
                    await connection.execute(text(
                        "REVOKE SELECT ON farms.unidades_produtivas "
                        "FROM deepfarms_rls_lab_runtime"
                    ))
                for name in set(preexisting).intersection({"usuarios", "unidades_produtivas"}):
                    await connection.execute(text(
                        f"DROP POLICY IF EXISTS {name}_lab_runtime ON farms.{name}"
                    ))
                    await connection.execute(text(
                        f"DROP POLICY IF EXISTS {name}_lab_fixture_owner ON farms.{name}"
                    ))
                    old_state = next(row for row in rls_state if row[0] == name)
                    if not old_state[1]:
                        await connection.execute(text(
                            f"ALTER TABLE farms.{name} DISABLE ROW LEVEL SECURITY"
                        ))
                    if not old_state[2]:
                        await connection.execute(text(
                            f"ALTER TABLE farms.{name} NO FORCE ROW LEVEL SECURITY"
                        ))
                    for column in columns_to_restore.get(name, ()):
                        await connection.execute(text(
                            f"ALTER TABLE farms.{name} DROP COLUMN {column}"
                        ))
                if not auth_schema_usage:
                    await connection.execute(text(
                        "REVOKE USAGE ON SCHEMA farms FROM deepfarms_rls_lab_auth"
                    ))
        await deploy_engine.dispose()
        if app_ref is not None:
            await engine.dispose()
            if authentication_engine is not None:
                await authentication_engine.dispose()


@pytest.mark.asyncio
async def test_real_login_and_notification_routes_are_isolated_by_rls(real_api_rls_lab):
    app, ids, deploy_engine = real_api_rls_lab
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://rls-lab.test") as client:
        login_tokens = {}
        # The approved global guard covers nonexistent addresses too and uses
        # the same normalized email key before credential lookup.
        missing_email = f"RLS-MISSING-{uuid.uuid4()}@EXAMPLE.COM"
        for _ in range(5):
            response = await client.post("/api/v1/auth/login", json={
                "email": missing_email, "senha": "senha-incorreta",
            })
            assert response.status_code == 401
        missing_email_locked = await client.post("/api/v1/auth/login", json={
            "email": missing_email, "senha": "senha-incorreta",
        })
        assert missing_email_locked.status_code == 423
        async with deploy_engine.begin() as connection:
            await connection.execute(text("SET LOCAL ROLE deepfarms_rls_lab_owner"))
            missing_attempt = (await connection.execute(text(
                "SELECT tentativas_count, bloqueado FROM farms.login_tentativas "
                "WHERE email=:email"
            ), {"email": missing_email.strip().lower()})).one()
            assert tuple(missing_attempt) == (5, True)

        bad_login = await client.post("/api/v1/auth/login", json={
            "email": "rls-a@example.com",
            "senha": "senha-incorreta",
        })
        assert bad_login.status_code == 401
        for key in ("a", "b"):
            response = await client.post("/api/v1/auth/login", json={
                "email": f"rls-{key}@example.com",
                "senha": "Laboratorio@2026",
            })
            assert response.status_code == 200, response.text
            login_tokens[key] = response.json()["access_token"]

        for key in ("a", "b"):
            response = await client.post(
                "/api/v1/notificacoes/",
                headers={"Authorization": f"Bearer {login_tokens[key]}"},
                json={
                    "tipo": "RLS_LAB_PROBE",
                    "titulo": f"Tenant {key.upper()}",
                    "mensagem": f"synthetic-marker-{key.upper()}",
                    "nivel": "INFO",
                    "meta": {},
                },
            )
            assert response.status_code == 201, response.text

        for key, other in (("a", "b"), ("b", "a")):
            response = await client.get(
                "/api/v1/notificacoes/",
                headers={"Authorization": f"Bearer {login_tokens[key]}"},
            )
            assert response.status_code == 200, response.text
            markers = {item["mensagem"] for item in response.json()}
            assert f"synthetic-marker-{key.upper()}" in markers
            assert f"synthetic-marker-{other.upper()}" not in markers

        cross = await client.get(
            "/api/v1/notificacoes/",
            headers={
                "Authorization": f"Bearer {login_tokens['a']}",
                "x-tenant-id": str(ids["tenant_b"]),
            },
        )
        assert cross.status_code == 403
        cross_write = await client.post(
            "/api/v1/notificacoes/",
            headers={
                "Authorization": f"Bearer {login_tokens['a']}",
                "x-tenant-id": str(ids["tenant_b"]),
            },
            json={
                "tipo": "RLS_LAB_CROSS_WRITE", "titulo": "forbidden",
                "mensagem": "must not persist", "nivel": "INFO", "meta": {},
            },
        )
        assert cross_write.status_code == 403
        unauth_transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=unauth_transport, base_url="http://rls-lab.test"
        ) as unauth_client:
            unauthenticated = await unauth_client.get("/api/v1/notificacoes/")
        assert unauthenticated.status_code == 401

        # A custom stricter Tenant limit is applied only after valid bcrypt;
        # invalid credentials still receive the fixed pre-authentication guard.
        for _ in range(2):
            response = await client.post("/api/v1/auth/login", json={
                "email": "rls-a@example.com", "senha": "senha-incorreta",
            })
            assert response.status_code == 401
        tenant_a_lock = await client.post("/api/v1/auth/login", json={
            "email": "rls-a@example.com", "senha": "Laboratorio@2026",
        })
        assert tenant_a_lock.status_code == 423

        # Tenant B's custom limit is higher than the global pre-auth ceiling.
        # The sixth invalid request is denied by the generic guard, so custom
        # limits cannot safely alter invalid-password responses pre-bcrypt.
        for _ in range(5):
            response = await client.post("/api/v1/auth/login", json={
                "email": "rls-b@example.com", "senha": "senha-incorreta",
            })
            assert response.status_code == 401
        default_guard_lock = await client.post("/api/v1/auth/login", json={
            "email": "rls-b@example.com", "senha": "Laboratorio@2026",
        })
        assert default_guard_lock.status_code == 423

    async with async_session_maker() as runtime:
        identity = (await runtime.execute(text(
            "SELECT current_database(), current_user, session_user"
        ))).one()
        assert tuple(identity) == (
            "deepfarms_rls_lab", "deepfarms_rls_lab_runtime", "deepfarms_rls_lab_runtime"
        )
        rows = (await runtime.execute(text(
            "SELECT count(*) FROM farms.notificacoes"
        ))).scalar_one()
        assert rows == 0
