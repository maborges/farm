"""field_pwa04_evidencia_upload

Revision ID: 20260607_field_pwa04
Revises: 20260606_field_remediation_01_snapshot
Create Date: 2026-06-07

Adiciona campos de rastreamento de evidência offline na tabela caderno_campo_fotos:
- device_local_id: identificador local da evidência (para idempotência)
- device_id: UUID do dispositivo que capturou
- mime_type: tipo MIME do arquivo
- size_bytes: tamanho em bytes
- storage_path: caminho interno no storage (local/S3/MinIO)
- created_at: timestamp de criação da foto
- constraint única: (entrada_id, device_local_id) para evitar duplicação de upload
"""

from alembic import op
import sqlalchemy as sa


revision = "20260607_field_pwa04"
down_revision = "20260606_field_remediation_01_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona colunas de rastreamento de evidência offline
    op.add_column(
        "caderno_campo_fotos",
        sa.Column("device_local_id", sa.String(80), nullable=True),
    )
    op.add_column(
        "caderno_campo_fotos",
        sa.Column("device_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "caderno_campo_fotos",
        sa.Column("mime_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "caderno_campo_fotos",
        sa.Column("size_bytes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "caderno_campo_fotos",
        sa.Column("storage_path", sa.String(500), nullable=True),
    )
    op.add_column(
        "caderno_campo_fotos",
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )

    # Índice para busca por device_local_id
    op.create_index(
        "ix_caderno_foto_device_local_id",
        "caderno_campo_fotos",
        ["device_local_id"],
    )
    op.create_index(
        "ix_caderno_foto_device_id",
        "caderno_campo_fotos",
        ["device_id"],
    )

    # Constraint única para idempotência: uma entrada pode ter uma foto por device_local_id
    # A constraint permite NULL em device_local_id (fotos do web não têm esse campo)
    op.create_unique_constraint(
        "uq_caderno_foto_device_local_id",
        "caderno_campo_fotos",
        ["entrada_id", "device_local_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_caderno_foto_device_local_id",
        "caderno_campo_fotos",
        type_="unique",
    )
    op.drop_index("ix_caderno_foto_device_id", table_name="caderno_campo_fotos")
    op.drop_index("ix_caderno_foto_device_local_id", table_name="caderno_campo_fotos")
    op.drop_column("caderno_campo_fotos", "created_at")
    op.drop_column("caderno_campo_fotos", "storage_path")
    op.drop_column("caderno_campo_fotos", "size_bytes")
    op.drop_column("caderno_campo_fotos", "mime_type")
    op.drop_column("caderno_campo_fotos", "device_id")
    op.drop_column("caderno_campo_fotos", "device_local_id")
