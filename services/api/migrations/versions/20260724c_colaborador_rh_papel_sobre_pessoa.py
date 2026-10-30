"""ColaboradorRH vira papel sobre Pessoa (mesmo padrão de Fornecedor).

- Para cada rh_colaboradores.pessoa_id IS NULL: cria uma Pessoa (+ PessoaDocumento
  CPF, se houver) a partir de nome/cpf hoje soltos na tabela, e vincula pessoa_id.
- Garante o vínculo PessoaRelacionamento(tipo=COLABORADOR) para todo colaborador.
- pessoa_id vira NOT NULL; colunas nome/cpf são removidas de rh_colaboradores
  (nome/cpf passam a vir sempre de cadastros_pessoas/cadastros_pessoas_documentos).

Revision ID: 20260724c_colab_pessoa
Revises: 20260724b_custo_medio_kardex
Create Date: 2026-07-24
"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260724c_colab_pessoa"
down_revision = "20260724b_custo_medio_kardex"
branch_labels = None
depends_on = None

COLABORADOR_TIPO = {
    "codigo": "COLABORADOR",
    "nome": "Colaborador / Funcionário",
    "cor": "#EC4899",
    "icone": "hard-hat",
}


def upgrade():
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. Backfill: cria Pessoa (+ Documento CPF) para colaboradores sem pessoa_id.
    sem_pessoa = conn.execute(sa.text(
        "SELECT id, tenant_id, nome, cpf FROM rh_colaboradores WHERE pessoa_id IS NULL"
    )).fetchall()
    for colaborador_id, tenant_id, nome, cpf in sem_pessoa:
        pessoa_id = uuid.uuid4()
        conn.execute(sa.text("""
            INSERT INTO cadastros_pessoas
                (id, tenant_id, tipo, nome_exibicao, base_legal, tags, ativo, created_at, updated_at)
            VALUES
                (:id, :tenant_id, 'PF', :nome, 'CONTRATO', '[]', true, :now, :now)
        """), {"id": pessoa_id, "tenant_id": tenant_id, "nome": nome, "now": now})

        if cpf:
            conn.execute(sa.text("""
                INSERT INTO cadastros_pessoas_documentos (id, pessoa_id, tipo, numero, updated_at)
                VALUES (:id, :pessoa_id, 'CPF', :numero, :now)
                ON CONFLICT DO NOTHING
            """), {"id": uuid.uuid4(), "pessoa_id": pessoa_id, "numero": cpf, "now": now})

        conn.execute(sa.text(
            "UPDATE rh_colaboradores SET pessoa_id = :pessoa_id WHERE id = :id"
        ), {"pessoa_id": pessoa_id, "id": colaborador_id})

    # 2. Garante o TipoRelacionamento COLABORADOR (global, tenant_id NULL) — mesmo
    #    seed de scripts/initial_load/seed_tipos_relacionamento.py, caso ainda não tenha rodado.
    tipo_row = conn.execute(sa.text(
        "SELECT id FROM cadastros_tipos_relacionamento WHERE codigo = 'COLABORADOR' AND tenant_id IS NULL"
    )).fetchone()
    if tipo_row:
        tipo_colaborador_id = tipo_row[0]
    else:
        tipo_colaborador_id = uuid.uuid4()
        conn.execute(sa.text("""
            INSERT INTO cadastros_tipos_relacionamento
                (id, tenant_id, codigo, nome, cor, icone, sistema, ativo)
            VALUES
                (:id, NULL, :codigo, :nome, :cor, :icone, true, true)
        """), {"id": tipo_colaborador_id, **COLABORADOR_TIPO})

    # 3. Garante PessoaRelacionamento(COLABORADOR) para toda pessoa vinculada a um
    #    ColaboradorRH que ainda não tenha esse vínculo.
    conn.execute(sa.text("""
        INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id)
        SELECT DISTINCT gen_random_uuid(), c.pessoa_id, CAST(:tipo_id AS uuid)
        FROM rh_colaboradores c
        WHERE c.pessoa_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM cadastros_pessoa_relacionamentos pr
            WHERE pr.pessoa_id = c.pessoa_id AND pr.tipo_id = CAST(:tipo_id AS uuid)
          )
    """), {"tipo_id": str(tipo_colaborador_id)})

    # 4. Schema: pessoa_id obrigatória, remove nome/cpf duplicados.
    op.alter_column("rh_colaboradores", "pessoa_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("rh_colaboradores", "nome")
    op.drop_column("rh_colaboradores", "cpf")

    op.execute("COMMIT")


def downgrade():
    op.add_column("rh_colaboradores", sa.Column("nome", sa.String(200), nullable=False, server_default="—"))
    op.add_column("rh_colaboradores", sa.Column("cpf", sa.String(14), nullable=True))
    op.alter_column("rh_colaboradores", "pessoa_id", existing_type=sa.Uuid(), nullable=True)

    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE rh_colaboradores c
        SET nome = p.nome_exibicao
        FROM cadastros_pessoas p
        WHERE c.pessoa_id = p.id
    """))
    conn.execute(sa.text("""
        UPDATE rh_colaboradores c
        SET cpf = d.numero
        FROM cadastros_pessoas_documentos d
        WHERE c.pessoa_id = d.pessoa_id AND d.tipo = 'CPF'
    """))
