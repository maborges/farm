# ruff: noqa: S608
"""Restaurar geração automática dos IDs legados Sankhya.

Revision ID: 20260718_sankhya_ids
Revises: 20260718_sankhya_endpoints
Create Date: 2026-07-18

As tabelas foram criadas originalmente com PK inteira, mas alguns bancos
legados perderam os defaults das sequences. A migração preserva todas as
linhas e reposiciona cada sequence depois do maior ID existente.
"""

from alembic import op

revision = "20260718_sankhya_ids"
down_revision = "20260718_sankhya_endpoints"
branch_labels = None
depends_on = None

SCHEMA = "farms"
TABLES = (
    "sankhya_config",
    "sankhya_sync_logs",
    "sankhya_pessoas",
    "sankhya_produtos",
    "sankhya_nfe",
    "sankhya_lancamentos_financeiros",
    "sankhya_tabelas",
)


def upgrade() -> None:
    """Preservar identities e reparar somente PKs sem geração automática."""
    for table_name in TABLES:
        sequence_name = f"{table_name}_id_seq"
        op.execute(f"""
            DO $$
            DECLARE
                sequence_regclass text;
                max_id bigint;
                is_identity boolean;
            BEGIN
                SELECT columns.is_identity = 'YES'
                  INTO is_identity
                  FROM information_schema.columns
                 WHERE columns.table_schema = '{SCHEMA}'
                   AND columns.table_name = '{table_name}'
                   AND columns.column_name = 'id';

                IF is_identity IS NULL THEN
                    RAISE EXCEPTION 'Coluna {SCHEMA}.{table_name}.id não encontrada';
                END IF;

                sequence_regclass := pg_get_serial_sequence(
                    '{SCHEMA}.{table_name}',
                    'id'
                );

                IF NOT is_identity THEN
                    IF sequence_regclass IS NULL THEN
                        sequence_regclass := '{SCHEMA}.{sequence_name}';
                        IF to_regclass(sequence_regclass) IS NULL THEN
                            EXECUTE format(
                                'CREATE SEQUENCE %I.%I',
                                '{SCHEMA}',
                                '{sequence_name}'
                            );
                        END IF;
                        EXECUTE format(
                            'ALTER SEQUENCE %s OWNED BY %I.%I.id',
                            sequence_regclass,
                            '{SCHEMA}',
                            '{table_name}'
                        );
                    END IF;

                    EXECUTE format(
                        'ALTER TABLE %I.%I ALTER COLUMN id '
                        'SET DEFAULT nextval(%L::regclass)',
                        '{SCHEMA}',
                        '{table_name}',
                        sequence_regclass
                    );
                END IF;

                IF sequence_regclass IS NULL THEN
                    RAISE EXCEPTION 'Sequence de {SCHEMA}.{table_name}.id não encontrada';
                END IF;

                EXECUTE format(
                    'SELECT MAX(id) FROM %I.%I',
                    '{SCHEMA}',
                    '{table_name}'
                ) INTO max_id;
                PERFORM setval(
                    sequence_regclass::regclass,
                    GREATEST(COALESCE(max_id, 0), 1),
                    max_id IS NOT NULL
                );
            END
            $$
        """)


def downgrade() -> None:
    """Preservar a integridade reparada; remover defaults recriaria o defeito."""
