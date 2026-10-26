"""AGRO-ADMIN-01B1: permite sessões globais sem tenant.

Revision ID: 20261022_agro_admin_01b1
Revises: 20260926_material_requisition_01g
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_agro_admin_01b1"
down_revision: str | Sequence[str] | None = "20260926_material_requisition_01g"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "sessoes_ativas",
        "tenant_id",
        existing_type=sa.Uuid(),
        nullable=True,
        schema="farms",
    )
    op.create_table(
        "usuario_byok_credenciais",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("farms.usuarios.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider_slug", sa.String(50), nullable=False),
        sa.Column("mascara_chave", sa.String(50), nullable=False),
        sa.Column("ciphertext_b64", sa.String(1024), nullable=False),
        sa.Column("data_nonce_b64", sa.String(64), nullable=False),
        sa.Column("dek_encrypted_b64", sa.String(256), nullable=False),
        sa.Column("dek_nonce_b64", sa.String(64), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="CONECTADO"),
        sa.Column("ultimo_uso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("usuario_id", "provider_slug", name="uq_usuario_byok_provider"),
        schema="farms",
    )


def downgrade() -> None:
    from alembic import context

    if context.is_offline_mode():
        raise RuntimeError(
            "Downgrade bloqueado em modo offline: confirme sessões globais e credenciais "
            "BYOK em PostgreSQL antes de gerar qualquer DDL destrutivo."
        )

    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if inspector.has_table("usuario_byok_credenciais", schema="farms"):
        credential_count = connection.execute(
            sa.text("SELECT count(*) FROM farms.usuario_byok_credenciais")
        ).scalar_one()
        if credential_count:
            raise RuntimeError(
                "Downgrade bloqueado: há credenciais BYOK persistidas. Preserve e valide "
                "um backup PostgreSQL e aprove um procedimento de rollback antes de removê-las."
            )

    orphan_count = connection.execute(
        sa.text("SELECT count(*) FROM farms.sessoes_ativas WHERE tenant_id IS NULL")
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            "Downgrade bloqueado: encerre as sessões globais sem tenant antes de restaurar NOT NULL."
        )

    if inspector.has_table("usuario_byok_credenciais", schema="farms"):
        op.drop_table("usuario_byok_credenciais", schema="farms")
    op.alter_column(
        "sessoes_ativas",
        "tenant_id",
        existing_type=sa.Uuid(),
        nullable=False,
        schema="farms",
    )
