"""campo_pwa_dispositivos_tarefas_tombstones

Revision ID: 20260508_campo_pwa
Revises: ddaa3c59131c
Create Date: 2026-05-08

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260508_campo_pwa"
down_revision: Union[str, Sequence[str], None] = "ddaa3c59131c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # campo_dispositivos
    op.create_table(
        "campo_dispositivos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("device_fingerprint", sa.String(256), nullable=True, unique=True),
        sa.Column("activation_code", sa.String(8), nullable=True),
        sa.Column("activation_code_expires_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("fazenda_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("modulos", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("last_sync_at", sa.DateTime, nullable=True),
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_campo_disp_tenant_user", "campo_dispositivos", ["tenant_id", "user_id"])
    op.create_index("ix_campo_disp_status", "campo_dispositivos", ["status"])
    op.create_index("ix_campo_disp_activation", "campo_dispositivos", ["activation_code"])

    # campo_tarefas
    op.create_table(
        "campo_tarefas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dispositivo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campo_dispositivos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("dados", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("fotos", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("unidade_produtiva_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("area_rural_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("localizacao_status", sa.String(20), nullable=False, server_default="INDISPONIVEL"),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("client_created_at", sa.DateTime, nullable=False),
        sa.Column("client_updated_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "client_id", name="uq_campo_tarefa_tenant_client"),
    )
    op.create_index("ix_campo_tarefas_tenant_status", "campo_tarefas", ["tenant_id", "status"])
    op.create_index("ix_campo_tarefas_unidade", "campo_tarefas", ["unidade_produtiva_id"])
    op.create_index("ix_campo_tarefas_type", "campo_tarefas", ["type"])
    op.create_index("ix_campo_tarefas_dispositivo", "campo_tarefas", ["dispositivo_id"])

    # campo_sync_tombstones
    op.create_table(
        "campo_sync_tombstones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tombstones_tenant_type_deleted", "campo_sync_tombstones", ["tenant_id", "entity_type", "deleted_at"])


def downgrade() -> None:
    op.drop_table("campo_sync_tombstones")
    op.drop_table("campo_tarefas")
    op.drop_table("campo_dispositivos")
