"""HTTP + authentication + ORM/RLS proof, using disposable fixtures in the RLS lab."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy import Column, Text, Uuid, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine

from core import dependencies
from core.config import settings
from core.database import DB_URL as APP_DATABASE_URL
from core.dependencies import get_session, get_tenant_id


RUNTIME_URL = os.getenv("DEEPFARMS_RLS_LAB_DATABASE_URL")
DEPLOY_URL = os.getenv("DEEPFARMS_RLS_LAB_DEPLOY_URL")
ProbeBase = declarative_base()


class HttpRlsProbe(ProbeBase):
    __tablename__ = "rls_http_probe"
    __table_args__ = {"schema": "farms"}

    id = Column(Uuid(as_uuid=True), primary_key=True)
    tenant_id = Column(Uuid(as_uuid=True), nullable=False)
    dado = Column(Text, nullable=False)


def _token(user_id: uuid.UUID, tenant_id: uuid.UUID | None, *, expires_at: datetime) -> str:
    claims = {
        "sub": str(user_id),
        "session_required": True,
        "exp": int(expires_at.timestamp()),
        "is_superuser": False,
        "modules": ["CORE"],
    }
    if tenant_id is not None:
        claims["tenant_id"] = str(tenant_id)
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _session_row(token: str, user_id: uuid.UUID, tenant_id: uuid.UUID | None, *, status: str = "ATIVA"):
    return {
        "id": str(uuid.uuid4()),
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "usuario_id": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "status": status,
        "expira_em": datetime.now(timezone.utc) + timedelta(minutes=20),
    }


@pytest_asyncio.fixture
async def http_rls_lab(monkeypatch):
    if not RUNTIME_URL or not DEPLOY_URL:
        pytest.skip("Configure as URLs runtime e deploy para o teste HTTP no laboratório")

    runtime_url = make_url(RUNTIME_URL)
    deploy_url = make_url(DEPLOY_URL)
    expected = ("192.168.0.3", 5432, "deepfarms_rls_lab")
    assert (runtime_url.host, runtime_url.port, runtime_url.database) == expected
    assert runtime_url.username == "deepfarms_rls_lab_runtime"
    assert (deploy_url.host, deploy_url.port, deploy_url.database) == expected
    assert deploy_url.username == "deepfarms_rls_lab_deploy"
    app_url = make_url(APP_DATABASE_URL)
    assert (app_url.host, app_url.port, app_url.database, app_url.username) == (
        *expected,
        "deepfarms_rls_lab_runtime",
    )
    # Chave efêmera exclusiva dos JWTs deste teste; não usa segredo de aplicação.
    monkeypatch.setattr(settings, "jwt_secret_key", f"01h-{uuid.uuid4()}-{uuid.uuid4()}")
    now = datetime.now(timezone.utc)
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    user_a, user_b, user_missing, user_inactive, user_revoked, user_header = [
        uuid.uuid4() for _ in range(6)
    ]

    tokens = {
        "a": _token(user_a, tenant_a, expires_at=now + timedelta(minutes=15)),
        "b": _token(user_b, tenant_b, expires_at=now + timedelta(minutes=15)),
        "missing_membership": _token(
            user_missing, tenant_a, expires_at=now + timedelta(minutes=15)
        ),
        "inactive_membership": _token(
            user_inactive, tenant_a, expires_at=now + timedelta(minutes=15)
        ),
        "revoked": _token(user_revoked, tenant_a, expires_at=now + timedelta(minutes=15)),
        "no_tenant": _token(user_header, None, expires_at=now + timedelta(minutes=15)),
        "expired": _token(user_a, tenant_a, expires_at=now - timedelta(minutes=2)),
    }

    deploy_engine = create_async_engine(deploy_url)
    created: list[str] = []
    try:
        async with deploy_engine.begin() as connection:
            identity = (
                await connection.execute(
                    text("SELECT current_database(), session_user, current_user")
                )
            ).one()
            assert tuple(identity) == (
                "deepfarms_rls_lab",
                "deepfarms_rls_lab_deploy",
                "deepfarms_rls_lab_deploy",
            )
            names = ["sessoes_ativas", "tenant_usuarios", "rls_http_probe"]
            existing = (
                await connection.execute(
                    text(
                        """
                        SELECT c.relname
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'farms' AND c.relname = ANY(:names)
                        """
                    ),
                    {"names": names},
                )
            ).scalars().all()
            assert not existing, f"Objetos preexistentes impedem fixture segura: {existing}"
            await connection.execute(text("SET ROLE deepfarms_rls_lab_owner"))

            await connection.execute(
                text(
                    """
                    CREATE TABLE farms.sessoes_ativas (
                        id uuid PRIMARY KEY,
                        usuario_id uuid NOT NULL,
                        tenant_id uuid NULL,
                        token_hash varchar(64) NOT NULL UNIQUE,
                        status varchar(20) NOT NULL,
                        expira_em timestamptz NOT NULL
                    )
                    """
                )
            )
            created.append("sessoes_ativas")
            await connection.execute(
                text(
                    """
                    CREATE TABLE farms.tenant_usuarios (
                        id uuid PRIMARY KEY,
                        tenant_id uuid NOT NULL,
                        usuario_id uuid NOT NULL,
                        status varchar(20) NOT NULL
                    )
                    """
                )
            )
            created.append("tenant_usuarios")
            await connection.execute(
                text(
                    """
                    CREATE TABLE farms.rls_http_probe (
                        id uuid PRIMARY KEY,
                        tenant_id uuid NOT NULL,
                        dado text NOT NULL
                    )
                    """
                )
            )
            created.append("rls_http_probe")

            await connection.execute(
                text(
                    """
                    INSERT INTO farms.tenant_usuarios (id, tenant_id, usuario_id, status)
                    VALUES
                        (:a_id, :tenant_a, :user_a, 'ATIVO'),
                        (:b_id, :tenant_b, :user_b, 'ATIVO'),
                        (:inactive_id, :tenant_a, :user_inactive, 'SUSPENSO')
                    """
                ),
                {
                    "a_id": str(uuid.uuid4()),
                    "tenant_a": str(tenant_a),
                    "user_a": str(user_a),
                    "b_id": str(uuid.uuid4()),
                    "tenant_b": str(tenant_b),
                    "user_b": str(user_b),
                    "inactive_id": str(uuid.uuid4()),
                    "user_inactive": str(user_inactive),
                },
            )

            session_rows = [
                _session_row(tokens[key], user, tenant, status=status)
                for key, user, tenant, status in (
                    ("a", user_a, tenant_a, "ATIVA"),
                    ("b", user_b, tenant_b, "ATIVA"),
                    ("missing_membership", user_missing, tenant_a, "ATIVA"),
                    ("inactive_membership", user_inactive, tenant_a, "ATIVA"),
                    ("revoked", user_revoked, tenant_a, "ENCERRADA"),
                    ("no_tenant", user_header, None, "ATIVA"),
                )
            ]
            await connection.execute(
                text(
                    """
                    INSERT INTO farms.sessoes_ativas
                        (id, usuario_id, tenant_id, token_hash, status, expira_em)
                    VALUES
                        (:id, :usuario_id, :tenant_id, :token_hash, :status, :expira_em)
                    """
                ),
                session_rows,
            )
            await connection.execute(
                text(
                    """
                    INSERT INTO farms.rls_http_probe (id, tenant_id, dado)
                    VALUES (:id_a, :tenant_a, 'synthetic-A'),
                           (:id_b, :tenant_b, 'synthetic-B')
                    """
                ),
                {
                    "id_a": str(uuid.uuid4()),
                    "tenant_a": str(tenant_a),
                    "id_b": str(uuid.uuid4()),
                    "tenant_b": str(tenant_b),
                },
            )
            await connection.execute(
                text("ALTER TABLE farms.rls_http_probe ENABLE ROW LEVEL SECURITY")
            )
            await connection.execute(
                text("ALTER TABLE farms.rls_http_probe FORCE ROW LEVEL SECURITY")
            )
            for table in ("sessoes_ativas", "tenant_usuarios"):
                await connection.execute(
                    text(f"ALTER TABLE farms.{table} ENABLE ROW LEVEL SECURITY")
                )
                await connection.execute(
                    text(f"ALTER TABLE farms.{table} FORCE ROW LEVEL SECURITY")
                )
                await connection.execute(
                    text(
                        f"""
                        CREATE POLICY {table}_user_select
                        ON farms.{table} FOR SELECT
                        TO deepfarms_rls_lab_runtime
                        USING (
                            usuario_id = NULLIF(
                                current_setting('app.current_user_id', true), ''
                            )::uuid
                        )
                        """
                    )
                )
            await connection.execute(
                text(
                    """
                    CREATE POLICY sessoes_ativas_user_update
                    ON farms.sessoes_ativas FOR UPDATE
                    TO deepfarms_rls_lab_runtime
                    USING (
                        usuario_id = NULLIF(
                            current_setting('app.current_user_id', true), ''
                        )::uuid
                    )
                    WITH CHECK (
                        usuario_id = NULLIF(
                            current_setting('app.current_user_id', true), ''
                        )::uuid
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    """
                    CREATE POLICY rls_http_probe_tenant_select
                    ON farms.rls_http_probe FOR SELECT
                    TO deepfarms_rls_lab_runtime
                    USING (
                        tenant_id = NULLIF(
                            current_setting('app.current_tenant_id', true), ''
                        )::uuid
                    )
                    """
                )
            )
            await connection.execute(
                text(
                    "GRANT SELECT ON farms.sessoes_ativas, farms.tenant_usuarios, "
                    "farms.rls_http_probe TO deepfarms_rls_lab_runtime"
                )
            )
            await connection.execute(
                text(
                    "GRANT UPDATE (status) ON farms.sessoes_ativas "
                    "TO deepfarms_rls_lab_runtime"
                )
            )

        app = FastAPI()
        activation_sessions = []
        activate_real = dependencies._activate_session_tenant

        async def observe_activation(session, tenant_id):
            activation_sessions.append(session)
            await activate_real(session, tenant_id)

        monkeypatch.setattr(dependencies, "_activate_session_tenant", observe_activation)

        @app.get("/lab/probe")
        async def read_probe(
            tenant_id: uuid.UUID = Depends(get_tenant_id),
            session=Depends(get_session),
        ):
            async def snapshot():
                identity = (
                    await session.execute(
                        text("SELECT current_database(), current_user, session_user")
                    )
                ).one()
                context = await session.scalar(
                    text("SELECT NULLIF(current_setting('app.current_tenant_id', true), '')")
                )
                user_context = await session.scalar(
                    text("SELECT NULLIF(current_setting('app.current_user_id', true), '')")
                )
                rows = (
                    await session.execute(
                        select(HttpRlsProbe.tenant_id, HttpRlsProbe.dado).order_by(
                            HttpRlsProbe.dado
                        )
                    )
                ).all()
                return (
                    tuple(identity),
                    user_context,
                    context,
                    [(str(row.tenant_id), row.dado) for row in rows],
                )

            before = await snapshot()
            await session.commit()
            after_commit = await snapshot()
            await session.rollback()
            after_rollback = await snapshot()
            try:
                await session.execute(text("SELECT 1 / 0"))
            except DBAPIError:
                await session.rollback()
            after_error = await snapshot()
            same_session = bool(activation_sessions) and all(
                activated is session for activated in activation_sessions
            )
            return {
                "tenant_id": str(tenant_id),
                "user_id": str(user_a if tenant_id == tenant_a else user_b),
                "session_identity_confirmed": same_session,
                "before": before,
                "after_commit": after_commit,
                "after_rollback": after_rollback,
                "after_error": after_error,
            }

        yield {
            "app": app,
            "tokens": tokens,
            "tenant_a": tenant_a,
            "tenant_b": tenant_b,
            "activation_sessions": activation_sessions,
        }
    finally:
        if created:
            async with deploy_engine.begin() as connection:
                await connection.execute(text("SET ROLE deepfarms_rls_lab_owner"))
                for name in reversed(created):
                    await connection.execute(text(f"DROP TABLE IF EXISTS farms.{name}"))
        await deploy_engine.dispose()


@pytest.mark.asyncio
async def test_http_auth_membership_rls_isolation_and_transaction_context(http_rls_lab):
    data = http_rls_lab
    transport = httpx.ASGITransport(app=data["app"])
    async with httpx.AsyncClient(transport=transport, base_url="http://rls-lab.test") as client:
        for tenant_key, other_key in (("a", "b"), ("b", "a")):
            data["activation_sessions"].clear()
            response = await client.get(
                "/lab/probe",
                headers={"Authorization": f"Bearer {data['tokens'][tenant_key]}"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            expected_tenant = str(data[f"tenant_{tenant_key}"])
            expected_marker = f"synthetic-{tenant_key.upper()}"
            assert body["tenant_id"] == expected_tenant
            assert body["session_identity_confirmed"] is True
            for boundary in ("before", "after_commit", "after_rollback", "after_error"):
                identity, user_context, context, rows = body[boundary]
                assert identity == [
                    "deepfarms_rls_lab",
                    "deepfarms_rls_lab_runtime",
                    "deepfarms_rls_lab_runtime",
                ]
                assert context == expected_tenant
                assert user_context == body["user_id"]
                assert rows == [[expected_tenant, expected_marker]]
            assert all(session is not None for session in data["activation_sessions"])

        # Token de A com header B não troca o Tenant autorizado do token.
        response = await client.get(
            "/lab/probe",
            headers={
                "Authorization": f"Bearer {data['tokens']['a']}",
                "x-tenant-id": str(data["tenant_b"]),
            },
        )
        assert response.status_code == 403

        # Usuário sem claim Tenant não pode escolher B por header sem membership.
        response = await client.get(
            "/lab/probe",
            headers={
                "Authorization": f"Bearer {data['tokens']['no_tenant']}",
                "x-tenant-id": str(data["tenant_b"]),
            },
        )
        assert response.status_code == 403

        for key in ("missing_membership", "inactive_membership"):
            response = await client.get(
                "/lab/probe",
                headers={"Authorization": f"Bearer {data['tokens'][key]}"},
            )
            assert response.status_code == 403

        for token in ("invalid.token.value", data["tokens"]["expired"], data["tokens"]["revoked"]):
            response = await client.get(
                "/lab/probe",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 401
