"""remove colunas redundantes de Fornecedor, migrando tudo para Pessoa

Fornecedor deixa de duplicar email/telefone/cnpj_cpf/razao_social/nome_fantasia
e passa a ser só um "papel de compras" sobre Pessoa (pessoa_id obrigatório).
Backfill: para cada Fornecedor sem pessoa_id, resolve ou cria a Pessoa
correspondente (mesma lógica de operacional/services/fornecedores_service.py
resolve_fornecedor, replicada aqui pois migrations não devem depender de
código de app que pode mudar).

Revision ID: 20260722e_fornecedor_sem_dup
Revises: 20260722d_pedido_adiantamento
Create Date: 2026-07-22
"""
import re
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260722e_fornecedor_sem_dup"
down_revision = "20260722d_pedido_adiantamento"
branch_labels = None
depends_on = None


def _normalizar_documento(documento):
    if not documento:
        return None
    normalizado = re.sub(r"\D", "", documento)
    return normalizado or None


def _tipo_documento(documento):
    normalizado = _normalizar_documento(documento)
    if normalizado and len(normalizado) == 11:
        return "CPF"
    if normalizado and len(normalizado) == 14:
        return "CNPJ"
    return None


def upgrade():
    conn = op.get_bind()

    tipo_fornecedor_id = conn.execute(sa.text(
        "SELECT id FROM cadastros_tipos_relacionamento WHERE codigo='FORNECEDOR' AND tenant_id IS NULL LIMIT 1"
    )).scalar()
    if tipo_fornecedor_id is None:
        # Fallback defensivo: cria o tipo padrão se por algum motivo não existir.
        tipo_fornecedor_id = uuid.uuid4()
        conn.execute(sa.text(
            "INSERT INTO cadastros_tipos_relacionamento (id, tenant_id, codigo) VALUES (:id, NULL, 'FORNECEDOR')"
        ), {"id": str(tipo_fornecedor_id)})

    orfaos = conn.execute(sa.text("""
        SELECT id, tenant_id, nome_fantasia, razao_social, cnpj_cpf, email, telefone
        FROM compras_fornecedores WHERE pessoa_id IS NULL
    """)).mappings().fetchall()

    agora = datetime.now(timezone.utc)

    for forn in orfaos:
        tenant_id = forn["tenant_id"]
        nome_fantasia = forn["nome_fantasia"]
        razao_social = forn["razao_social"]
        cnpj_cpf = forn["cnpj_cpf"]
        email = forn["email"]
        telefone = forn["telefone"]

        documento = _normalizar_documento(cnpj_cpf)
        tipo_doc = _tipo_documento(cnpj_cpf)
        nome_exibicao = nome_fantasia or razao_social or "Fornecedor"

        pessoa_id = None
        if documento and tipo_doc:
            pessoa_id = conn.execute(sa.text("""
                SELECT p.id FROM cadastros_pessoas p
                JOIN cadastros_pessoas_documentos d ON d.pessoa_id = p.id
                WHERE p.tenant_id = :tenant_id AND d.tipo = :tipo AND d.numero = :numero
                LIMIT 1
            """), {"tenant_id": tenant_id, "tipo": tipo_doc, "numero": documento}).scalar()

        if not pessoa_id:
            pessoa_id = conn.execute(sa.text("""
                SELECT id FROM cadastros_pessoas WHERE tenant_id = :tenant_id AND nome_exibicao = :nome LIMIT 1
            """), {"tenant_id": tenant_id, "nome": nome_exibicao}).scalar()

        if not pessoa_id:
            pessoa_id = uuid.uuid4()
            conn.execute(sa.text("""
                INSERT INTO cadastros_pessoas
                    (id, tenant_id, tipo, nome_exibicao, base_legal, ativo, tags, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :tipo, :nome, 'CONTRATO', true, '[]', :agora, :agora)
            """), {
                "id": str(pessoa_id),
                "tenant_id": tenant_id,
                "tipo": "PJ" if (tipo_doc == "CNPJ" or not tipo_doc) else "PF",
                "nome": nome_exibicao,
                "agora": agora,
            })

            if documento and tipo_doc:
                conn.execute(sa.text("""
                    INSERT INTO cadastros_pessoas_documentos
                        (id, pessoa_id, tipo, numero, razao_social, nome_fantasia, nome_completo, updated_at)
                    VALUES
                        (:id, :pessoa_id, :tipo, :numero, :razao_social, :nome_fantasia, :nome_completo, :agora)
                """), {
                    "id": str(uuid.uuid4()),
                    "pessoa_id": str(pessoa_id),
                    "tipo": tipo_doc,
                    "numero": documento,
                    "razao_social": razao_social if tipo_doc == "CNPJ" else None,
                    "nome_fantasia": nome_fantasia if tipo_doc == "CNPJ" else None,
                    "nome_completo": nome_fantasia if tipo_doc == "CPF" else None,
                    "agora": agora,
                })

            if email:
                conn.execute(sa.text("""
                    INSERT INTO cadastros_pessoas_contatos (id, pessoa_id, tipo, valor, principal, verificado, ativo, created_at)
                    VALUES (:id, :pessoa_id, 'EMAIL', :valor, true, false, true, :agora)
                """), {"id": str(uuid.uuid4()), "pessoa_id": str(pessoa_id), "valor": email, "agora": agora})
            if telefone:
                conn.execute(sa.text("""
                    INSERT INTO cadastros_pessoas_contatos (id, pessoa_id, tipo, valor, principal, verificado, ativo, created_at)
                    VALUES (:id, :pessoa_id, 'TELEFONE', :valor, true, false, true, :agora)
                """), {"id": str(uuid.uuid4()), "pessoa_id": str(pessoa_id), "valor": telefone, "agora": agora})

        tem_relacionamento = conn.execute(sa.text("""
            SELECT 1 FROM cadastros_pessoa_relacionamentos WHERE pessoa_id = :pessoa_id AND tipo_id = :tipo_id LIMIT 1
        """), {"pessoa_id": str(pessoa_id), "tipo_id": str(tipo_fornecedor_id)}).scalar()
        if not tem_relacionamento:
            conn.execute(sa.text("""
                INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id)
                VALUES (:id, :pessoa_id, :tipo_id)
            """), {"id": str(uuid.uuid4()), "pessoa_id": str(pessoa_id), "tipo_id": str(tipo_fornecedor_id)})

        conn.execute(sa.text("""
            UPDATE compras_fornecedores SET pessoa_id = :pessoa_id WHERE id = :forn_id
        """), {"pessoa_id": str(pessoa_id), "forn_id": forn["id"]})

    op.execute("ALTER TABLE compras_fornecedores ALTER COLUMN pessoa_id SET NOT NULL")
    op.execute("ALTER TABLE compras_fornecedores DROP COLUMN IF EXISTS email")
    op.execute("ALTER TABLE compras_fornecedores DROP COLUMN IF EXISTS telefone")
    op.execute("ALTER TABLE compras_fornecedores DROP COLUMN IF EXISTS cnpj_cpf")
    op.execute("ALTER TABLE compras_fornecedores DROP COLUMN IF EXISTS razao_social")
    op.execute("ALTER TABLE compras_fornecedores DROP COLUMN IF EXISTS nome_fantasia")
    op.execute("COMMIT")


def downgrade():
    op.execute("ALTER TABLE compras_fornecedores ADD COLUMN IF NOT EXISTS nome_fantasia VARCHAR(150)")
    op.execute("ALTER TABLE compras_fornecedores ADD COLUMN IF NOT EXISTS razao_social VARCHAR(150)")
    op.execute("ALTER TABLE compras_fornecedores ADD COLUMN IF NOT EXISTS cnpj_cpf VARCHAR(20)")
    op.execute("ALTER TABLE compras_fornecedores ADD COLUMN IF NOT EXISTS telefone VARCHAR(20)")
    op.execute("ALTER TABLE compras_fornecedores ADD COLUMN IF NOT EXISTS email VARCHAR(100)")
    op.execute("""
        UPDATE compras_fornecedores f
        SET nome_fantasia = p.nome_exibicao
        FROM cadastros_pessoas p
        WHERE p.id = f.pessoa_id
    """)
    op.execute("ALTER TABLE compras_fornecedores ALTER COLUMN pessoa_id DROP NOT NULL")
    op.execute("COMMIT")
