"""cria módulo balanca (dispositivos, ordens de pesagem, pesagens, tombstones)

Módulo de balança desenhado como serviço desacoplado: outros módulos
(romaneio/colheita, compras, vendas, pecuária, pessoas) solicitam pesagem
via origem_tipo/origem_id genérico, sem FK direta às tabelas desses módulos
— mantém o módulo extraível/comercializável separadamente.

Offline-first via apps/balanca (PWA dedicado), reaproveitando o padrão de
sync (push/pull idempotente por client_id + tombstones) já usado em campo/.

Revision ID: 20260816_balanca_modulo
Revises: 20260816_imoveis_irrigacao
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "20260816_balanca_modulo"
down_revision = "20260816_imoveis_irrigacao"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "balanca_dispositivos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("device_fingerprint", sa.String(256), nullable=True, unique=True),
        sa.Column("pin_hash", sa.String(255), nullable=True),
        sa.Column("activation_code", sa.String(8), nullable=True),
        sa.Column("activation_code_expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("fazenda_ids", ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_balanca_disp_tenant_status", "balanca_dispositivos", ["tenant_id", "status"])
    op.create_index("ix_balanca_disp_activation", "balanca_dispositivos", ["activation_code"])

    op.create_table(
        "balanca_ordens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origem_tipo", sa.String(30), nullable=False),
        sa.Column("origem_id", UUID(as_uuid=True), nullable=True),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("tipo_pesagem", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("solicitado_por", UUID(as_uuid=True), nullable=True),
        sa.Column("contexto", JSONB, nullable=False, server_default="{}"),
        sa.Column("dispositivo_id", UUID(as_uuid=True), sa.ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("concluida_em", sa.DateTime(), nullable=True),
        sa.Column("cancelada_em", sa.DateTime(), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_balanca_ordens_tenant_status", "balanca_ordens", ["tenant_id", "status"])
    op.create_index("ix_balanca_ordens_origem", "balanca_ordens", ["origem_tipo", "origem_id"])
    op.create_index("ix_balanca_ordens_dispositivo", "balanca_ordens", ["dispositivo_id"])

    op.create_table(
        "balanca_pesagens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordem_id", UUID(as_uuid=True), sa.ForeignKey("balanca_ordens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dispositivo_id", UUID(as_uuid=True), sa.ForeignKey("balanca_dispositivos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("numero_ticket", sa.String(30), nullable=False),
        sa.Column("client_id", sa.String(36), nullable=True),
        sa.Column("peso_bruto_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("peso_tara_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("peso_liquido_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("captured_via", sa.String(15), nullable=False, server_default="MANUAL"),
        sa.Column("leitura_bruta", JSONB, nullable=True),
        sa.Column("placa", sa.String(10), nullable=True),
        sa.Column("motorista", sa.String(150), nullable=True),
        sa.Column("animal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("pessoa_id", UUID(as_uuid=True), nullable=True),
        sa.Column("data_entrada", sa.DateTime(), nullable=True),
        sa.Column("data_saida", sa.DateTime(), nullable=True),
        sa.Column("client_created_at", sa.DateTime(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "client_id", name="uq_balanca_pesagem_tenant_client"),
        sa.UniqueConstraint("tenant_id", "numero_ticket", name="uq_balanca_pesagem_tenant_ticket"),
    )
    op.create_index("ix_balanca_pesagens_tenant", "balanca_pesagens", ["tenant_id"])
    op.create_index("ix_balanca_pesagens_ordem", "balanca_pesagens", ["ordem_id"])
    op.create_index("ix_balanca_pesagens_client_id", "balanca_pesagens", ["client_id"])

    op.create_table(
        "balanca_sync_tombstones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_balanca_tombstones_tenant_type_deleted",
        "balanca_sync_tombstones",
        ["tenant_id", "entity_type", "deleted_at"],
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_table("balanca_sync_tombstones")
    op.drop_table("balanca_pesagens")
    op.drop_table("balanca_ordens")
    op.drop_table("balanca_dispositivos")
    op.execute("COMMIT")
