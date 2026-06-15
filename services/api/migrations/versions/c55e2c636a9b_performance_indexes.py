"""performance_indexes

Revision ID: c55e2c636a9b
Revises: 20260608_merge_estoque_implantacao_heads
Create Date: 2026-06-08 19:11:06.392817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c55e2c636a9b'
down_revision: Union[str, Sequence[str], None] = '20260608_merge_estoque_implantacao_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.engine.reflection import Inspector

def upgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    
    def create_idx_if_table_exists(idx_name, table_name, columns):
        if insp.has_table(table_name):
            # Check if index already exists
            indexes = insp.get_indexes(table_name)
            if not any(idx['name'] == idx_name for idx in indexes):
                op.create_index(idx_name, table_name, columns, unique=False)

    # Financeiro
    create_idx_if_table_exists('ix_financeiro_lancamentos_data', 'financeiro_lancamentos', ['data'])
    
    create_idx_if_table_exists('ix_fin_receitas_unidade_produtiva_id', 'fin_receitas', ['unidade_produtiva_id'])
    create_idx_if_table_exists('ix_fin_receitas_data_recebimento', 'fin_receitas', ['data_recebimento'])
    
    create_idx_if_table_exists('ix_fin_despesas_unidade_produtiva_id', 'fin_despesas', ['unidade_produtiva_id'])
    create_idx_if_table_exists('ix_fin_despesas_data_pagamento', 'fin_despesas', ['data_pagamento'])
    
    create_idx_if_table_exists('ix_fin_notas_fiscais_unidade_produtiva_id', 'fin_notas_fiscais', ['unidade_produtiva_id'])
    create_idx_if_table_exists('ix_fin_notas_fiscais_status_sefaz', 'fin_notas_fiscais', ['status_sefaz'])
    create_idx_if_table_exists('ix_fin_notas_fiscais_data_emissao', 'fin_notas_fiscais', ['data_emissao'])

    # Ambiental / Enterprise tenant_id indexes
    tables_with_tenant = [
        "ambiental_monitoramento_app", "ambiental_alertas_desmatamento", "ambiental_outorgas_hidricas",
        "ambiental_ccir", "mrv_projetos", "mrv_relatorios", "esg_indicadores", "esg_relatorios",
        "tanques_rede", "arracoamentos", "pesagens", "confinamento_lotes", "racoes_tmr", "cochos",
        "animal_genetica", "sugestoes_acasalamento", "contratos_futuros", "hedge_registros",
        "sensores_iot", "sensores_leituras", "ilpf_modulos", "colaborador_apontamentos"
    ]
    for table in tables_with_tenant:
        create_idx_if_table_exists(f'ix_{table}_tenant_id', table, ['tenant_id'])

def downgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    
    def drop_idx_if_exists(idx_name, table_name):
        if insp.has_table(table_name):
            indexes = insp.get_indexes(table_name)
            if any(idx['name'] == idx_name for idx in indexes):
                op.drop_index(idx_name, table_name=table_name)

    tables_with_tenant = [
        "ambiental_monitoramento_app", "ambiental_alertas_desmatamento", "ambiental_outorgas_hidricas",
        "ambiental_ccir", "mrv_projetos", "mrv_relatorios", "esg_indicadores", "esg_relatorios",
        "tanques_rede", "arracoamentos", "pesagens", "confinamento_lotes", "racoes_tmr", "cochos",
        "animal_genetica", "sugestoes_acasalamento", "contratos_futuros", "hedge_registros",
        "sensores_iot", "sensores_leituras", "ilpf_modulos", "colaborador_apontamentos"
    ]
    for table in tables_with_tenant:
        drop_idx_if_exists(f'ix_{table}_tenant_id', table)

    drop_idx_if_exists('ix_fin_notas_fiscais_data_emissao', 'fin_notas_fiscais')
    drop_idx_if_exists('ix_fin_notas_fiscais_status_sefaz', 'fin_notas_fiscais')
    drop_idx_if_exists('ix_fin_notas_fiscais_unidade_produtiva_id', 'fin_notas_fiscais')
    
    drop_idx_if_exists('ix_fin_despesas_data_pagamento', 'fin_despesas')
    drop_idx_if_exists('ix_fin_despesas_unidade_produtiva_id', 'fin_despesas')
    
    drop_idx_if_exists('ix_fin_receitas_data_recebimento', 'fin_receitas')
    drop_idx_if_exists('ix_fin_receitas_unidade_produtiva_id', 'fin_receitas')
    
    drop_idx_if_exists('ix_financeiro_lancamentos_data', 'financeiro_lancamentos')
