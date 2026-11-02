"""Harden RLS policies: NULLIF uuid cast, global model write protection, public passport read.

Revision ID: 20261102_rls_policies_hardening
Revises: 20261022_agro_admin_01b1
Create Date: 2026-11-02 17:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migrations.baseline_contract import POLICY_CONTRACT

revision: str = "20261102_rls_policies_hardening"
down_revision: str | None = "20261022_agro_admin_01b1"
branch_labels = None
depends_on = None


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def upgrade() -> None:
    """Synchronize all baseline RLS policies with hardened expressions."""
    for contract in sorted(POLICY_CONTRACT.values(), key=lambda item: str(item["name"])):
        table = _quote(str(contract["table"]))
        policy = _quote(str(contract["name"]))
        roles = ", ".join(
            _quote(str(role)) if role != "public" else "PUBLIC"
            for role in contract["roles"]  # type: ignore[union-attr]
        )
        mode = "PERMISSIVE" if contract["permissive"] else "RESTRICTIVE"
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table}"))
        sql = (
            f"CREATE POLICY {policy} ON {table} AS {mode} "
            f"FOR {contract['command']} TO {roles}"
        )
        if contract["using_expression"]:
            sql += f" USING ({contract['using_expression']})"
        if contract["with_check_expression"]:
            sql += f" WITH CHECK ({contract['with_check_expression']})"
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Keep hardened policies in place on downgrade to preserve tenant isolation."""
    pass

