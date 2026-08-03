"""checklist por fase vira processo (tipo_resultado, responsavel, prazo, artefatos)

Revision ID: 20260803_checklist_proc
Revises: 20260803_disp_pin_hash
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260803_checklist_proc'
down_revision: Union[str, Sequence[str], None] = '20260803_disp_pin_hash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'phase_template_checklist_items',
        sa.Column('tipo_resultado', sa.String(30), nullable=False, server_default='MANUAL'),
    )
    op.add_column(
        'phase_template_checklist_items',
        sa.Column('produto_id_padrao', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'phase_template_checklist_items',
        sa.Column('quantidade_minima', sa.Float(), nullable=True),
    )
    op.create_foreign_key(
        'fk_phase_tmpl_checklist_produto',
        'phase_template_checklist_items', 'cadastros_produtos',
        ['produto_id_padrao'], ['id'], ondelete='SET NULL',
    )

    op.add_column(
        'safra_checklist_itens',
        sa.Column('tipo_resultado', sa.String(30), nullable=False, server_default='MANUAL'),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('operacao_agricola_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('reserva_estoque_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('requisicao_material_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('responsavel_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('prazo_resposta', sa.Date(), nullable=True),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('status_verificacao', sa.String(20), nullable=False, server_default='PENDENTE'),
    )
    op.add_column(
        'safra_checklist_itens',
        sa.Column('justificativa_ok_parcial', sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        'fk_safra_checklist_operacao', 'safra_checklist_itens', 'operacoes_agricolas',
        ['operacao_agricola_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_safra_checklist_reserva', 'safra_checklist_itens', 'estoque_reservas',
        ['reserva_estoque_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_safra_checklist_requisicao', 'safra_checklist_itens', 'estoque_requisicoes',
        ['requisicao_material_id'], ['id'], ondelete='SET NULL',
    )
    op.execute("COMMIT")


def downgrade() -> None:
    op.drop_constraint('fk_safra_checklist_requisicao', 'safra_checklist_itens', type_='foreignkey')
    op.drop_constraint('fk_safra_checklist_reserva', 'safra_checklist_itens', type_='foreignkey')
    op.drop_constraint('fk_safra_checklist_operacao', 'safra_checklist_itens', type_='foreignkey')
    op.drop_column('safra_checklist_itens', 'justificativa_ok_parcial')
    op.drop_column('safra_checklist_itens', 'status_verificacao')
    op.drop_column('safra_checklist_itens', 'prazo_resposta')
    op.drop_column('safra_checklist_itens', 'responsavel_id')
    op.drop_column('safra_checklist_itens', 'requisicao_material_id')
    op.drop_column('safra_checklist_itens', 'reserva_estoque_id')
    op.drop_column('safra_checklist_itens', 'operacao_agricola_id')
    op.drop_column('safra_checklist_itens', 'tipo_resultado')

    op.drop_constraint('fk_phase_tmpl_checklist_produto', 'phase_template_checklist_items', type_='foreignkey')
    op.drop_column('phase_template_checklist_items', 'quantidade_minima')
    op.drop_column('phase_template_checklist_items', 'produto_id_padrao')
    op.drop_column('phase_template_checklist_items', 'tipo_resultado')
    op.execute("COMMIT")
