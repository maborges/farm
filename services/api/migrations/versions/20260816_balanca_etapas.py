"""balanca: pesagem por etapas (peso informado/aferido) + produto/agendamento/NF na ordem

Revisão do modelo de Pesagem: em vez de 1 registro por "perna" com
bruto/tara/líquido, cada Pesagem passa a representar um evento físico único
(etapa), com peso_informado_kg (declarado) e peso_aferido_kg (medido pela
balança) separados. O peso líquido final passa a viver em OrdemPesagem
(calculado a partir do par de etapas). Suporta também o cenário de
(des)carregamento entre as duas pesagens (2 etapas adicionais de tipo_pesagem).

Sem dados reais em produção neste módulo ainda (só tenants de teste) —
migration destrutiva nas colunas antigas é segura aqui.

Revision ID: 20260816_balanca_etapas
Revises: 20260816_balanca_modulo
Create Date: 2026-08-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Uuid as UUID

revision = "20260816_balanca_etapas"
down_revision = "20260816_balanca_modulo"
branch_labels = None
depends_on = None


def upgrade():
    # --- balanca_ordens: produto/volumes/agendamento/NF/peso líquido final ---
    op.alter_column("balanca_ordens", "tipo_pesagem", type_=sa.String(30))
    op.add_column("balanca_ordens", sa.Column("produto_id", UUID(as_uuid=True), nullable=True))
    op.add_column("balanca_ordens", sa.Column("produto_tipo", sa.String(20), nullable=True))
    op.add_column("balanca_ordens", sa.Column("tipo_volume", sa.String(20), nullable=True))
    op.add_column("balanca_ordens", sa.Column("quantidade_volumes", sa.Numeric(10, 2), nullable=True))
    op.add_column("balanca_ordens", sa.Column("data_agendada", sa.DateTime(), nullable=True))
    op.add_column("balanca_ordens", sa.Column("numero_documento_fiscal", sa.String(60), nullable=True))
    op.add_column("balanca_ordens", sa.Column("peso_liquido_kg", sa.Numeric(12, 3), nullable=True))

    # --- balanca_pesagens: bruto/tara/líquido/entrada/saída -> etapa + informado/aferido ---
    op.add_column("balanca_pesagens", sa.Column("etapa", sa.String(20), nullable=False, server_default="UNICA"))
    op.add_column("balanca_pesagens", sa.Column("peso_informado_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("peso_aferido_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("operador_pessoa_id", UUID(as_uuid=True), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("data_pesagem", sa.DateTime(), nullable=True))

    op.execute("UPDATE balanca_pesagens SET peso_aferido_kg = peso_liquido_kg, data_pesagem = COALESCE(data_entrada, data_saida)")

    op.drop_column("balanca_pesagens", "peso_bruto_kg")
    op.drop_column("balanca_pesagens", "peso_liquido_kg")
    op.drop_column("balanca_pesagens", "data_entrada")
    op.drop_column("balanca_pesagens", "data_saida")

    op.alter_column("balanca_pesagens", "etapa", server_default=None)
    op.create_unique_constraint(
        "uq_balanca_pesagem_ordem_etapa", "balanca_pesagens", ["ordem_id", "etapa"]
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_constraint("uq_balanca_pesagem_ordem_etapa", "balanca_pesagens", type_="unique")

    op.add_column("balanca_pesagens", sa.Column("peso_bruto_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("peso_liquido_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("data_entrada", sa.DateTime(), nullable=True))
    op.add_column("balanca_pesagens", sa.Column("data_saida", sa.DateTime(), nullable=True))
    op.execute("UPDATE balanca_pesagens SET peso_liquido_kg = peso_aferido_kg, data_entrada = data_pesagem")

    op.drop_column("balanca_pesagens", "data_pesagem")
    op.drop_column("balanca_pesagens", "operador_pessoa_id")
    op.drop_column("balanca_pesagens", "peso_aferido_kg")
    op.drop_column("balanca_pesagens", "peso_informado_kg")
    op.drop_column("balanca_pesagens", "etapa")

    op.drop_column("balanca_ordens", "peso_liquido_kg")
    op.drop_column("balanca_ordens", "numero_documento_fiscal")
    op.drop_column("balanca_ordens", "data_agendada")
    op.drop_column("balanca_ordens", "quantidade_volumes")
    op.drop_column("balanca_ordens", "tipo_volume")
    op.drop_column("balanca_ordens", "produto_tipo")
    op.drop_column("balanca_ordens", "produto_id")
    op.alter_column("balanca_ordens", "tipo_pesagem", type_=sa.String(10))

    op.execute("COMMIT")
