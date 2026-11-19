"""Habilita escrita administrativa nominativa de catálogos globais sob FORCE RLS.

Revision ID: 20261119_rls_global_catalog_admin_write
Revises: 20261118_plano_acao_capex
Create Date: 2026-11-19 17:35:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_rls_global_catalog_admin_write"
down_revision: str | None = "20261118_plano_acao_capex"
branch_labels = None
depends_on = None

GLOBAL_MODEL_TABLES: tuple[str, ...] = (
    "modelos_fitossanitarios",
    "modelos_zoosanitarios",
)
DEDICATED_ADMIN_ROLES: tuple[str, ...] = (
    "df_catalog_admin",
    "deepfarms_catalog_admin",
)
EXCLUDED_ROLE_SUFFIXES: tuple[str, ...] = ("_runtime", "_auth", "_dispatcher")
GLOBAL_ONLY_EXPR = (
    "((tenant_id IS NULL) AND "
    "(NULLIF(current_setting('app.current_tenant_id'::text, true), ''::text) IS NULL))"
)
POLICY_SPECS: tuple[tuple[str, str, bool, bool], ...] = (
    ("insert", "INSERT", False, True),
    ("update", "UPDATE", True, True),
    ("delete", "DELETE", True, False),
)


def _quote_ident(identifier: str) -> str:
    """Escapa um identificador SQL para uso seguro em DDL.

    Args:
        identifier: Nome da tabela, policy ou role PostgreSQL.

    Returns:
        Identificador delimitado por aspas duplas.
    """
    return '"' + identifier.replace('"', '""') + '"'


def _is_restricted_runtime_role(role_name: str) -> bool:
    """Indica se a role pertence a runtime restrito, auth, dispatcher ou public.

    Args:
        role_name: Nome da role PostgreSQL inspecionada.

    Returns:
        True quando a role nunca pode receber policy administrativa global.
    """
    normalized = role_name.strip().lower()
    if not normalized or normalized == "public":
        return True
    return normalized.endswith(EXCLUDED_ROLE_SUFFIXES)


def _resolve_global_catalog_admin_roles(bind, table_name: str) -> list[str]:
    """Resolve owner e roles dedicadas autorizadas para escrita global da tabela.

    Args:
        bind: Conexão SQLAlchemy síncrona do Alembic.
        table_name: Nome da tabela alvo no schema atual.

    Returns:
        Lista ordenada e deduplicada de roles administrativas elegíveis.

    Raises:
        RuntimeError: Se nenhuma role elegível for encontrada para a tabela.
    """
    owner = bind.execute(
        sa.text(
            "SELECT pg_get_userbyid(c.relowner)::text "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = current_schema() AND c.relname = :table_name"
        ),
        {"table_name": table_name},
    ).scalar_one_or_none()
    dedicated_rows = bind.execute(
        sa.text(
            "SELECT rolname::text FROM pg_roles "
            "WHERE rolname IN ('df_catalog_admin', 'deepfarms_catalog_admin') "
            "ORDER BY rolname"
        )
    ).fetchall()
    candidates = [owner, *(row[0] for row in dedicated_rows)]
    roles = list(
        dict.fromkeys(
            role for role in candidates
            if role and not _is_restricted_runtime_role(str(role))
        )
    )
    if not roles:
        raise RuntimeError(
            f"Nenhuma role administrativa elegível encontrada para {table_name}"
        )
    return roles


def _apply_global_admin_policies(table_name: str, roles_sql: str) -> None:
    """Cria policies permissivas nominativas apenas para registros globais.

    Args:
        table_name: Nome da tabela protegida por RLS.
        roles_sql: Lista formatada de roles elegíveis para cláusula TO.
    """
    quoted_table = _quote_ident(table_name)
    for suffix, command, has_using, has_with_check in POLICY_SPECS:
        policy_ident = _quote_ident(f"{table_name}_global_admin_{suffix}")
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_ident} ON {quoted_table}"))
        sql = (
            f"CREATE POLICY {policy_ident} ON {quoted_table} "
            f"AS PERMISSIVE FOR {command} TO {roles_sql}"
        )
        if has_using:
            sql += f" USING ({GLOBAL_ONLY_EXPR})"
        if has_with_check:
            sql += f" WITH CHECK ({GLOBAL_ONLY_EXPR})"
        op.execute(sa.text(sql))


def upgrade() -> None:
    """Adiciona policies nominativas de escrita global sem abrir para PUBLIC."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name in GLOBAL_MODEL_TABLES:
        roles = _resolve_global_catalog_admin_roles(bind, table_name)
        roles_sql = ", ".join(_quote_ident(role) for role in roles)
        _apply_global_admin_policies(table_name, roles_sql)


def downgrade() -> None:
    """Remove as policies nominativas de escrita global de catálogos."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table_name in GLOBAL_MODEL_TABLES:
        quoted_table = _quote_ident(table_name)
        for suffix, _, _, _ in POLICY_SPECS:
            policy_ident = _quote_ident(f"{table_name}_global_admin_{suffix}")
            op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_ident} ON {quoted_table}"))
