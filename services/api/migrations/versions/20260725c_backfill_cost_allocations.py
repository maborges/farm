"""backfill cost_allocations ausentes para operacoes_execucoes historicas

A migration step17_operacoes_execucoes fez backfill de OperacaoExecucao via
SQL bruto para operações REALIZADA legadas, mas nunca criou os
CostAllocation correspondentes (esse passo só acontece hoje via
_garantir_execucao_e_allocation_leves em agricola/operacoes/service.py,
que não roda para execuções já existentes). Resultado: CostAllocation
ficou vazio para todo tenant com operações históricas, mesmo com
production_unit_id e custo_total > 0 presentes.

Este backfill cria um CostAllocation (source='OPERATION_EXECUTION") para
cada OperacaoExecucao que:
- referencia uma OperacaoAgricola com custo_total > 0 e production_unit_id
  preenchido;
- ainda não possui CostAllocation vinculado (nem por operation_execution_id
  nem por production_unit_id+source, mesma checagem de
  _buscar_allocation_existente).

Usa o custo_total ATUAL da operação (não o valor congelado em
operacoes_execucoes.custo_real, que pode estar desatualizado/zerado para
os casos históricos que motivaram esta migration).

Revision ID: 20260725c_backfill_cost_allocations
Revises: 20260725b_tipo_servico
Create Date: 2026-07-25
"""
from alembic import op

revision = "20260725c_backfill_cost_allocations"
down_revision = "20260725b_tipo_servico"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO cost_allocations (
          id, tenant_id, production_unit_id, source, source_id,
          operation_execution_id, cost_category, amount, currency,
          allocation_date, allocation_method, allocation_basis, created_at
        )
        SELECT
          gen_random_uuid(),
          oe.tenant_id,
          oa.production_unit_id,
          'OPERATION_EXECUTION',
          oe.id,
          oe.id,
          'OUTROS',
          oa.custo_total,
          'BRL',
          COALESCE(oe.data_execucao, oa.data_realizada, CURRENT_DATE),
          'DIRECT',
          oe.area_ha_executada,
          now()
        FROM operacoes_execucoes oe
        JOIN operacoes_agricolas oa ON oa.id = oe.operacao_id
        WHERE oa.custo_total IS NOT NULL
          AND oa.custo_total > 0
          AND oa.production_unit_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM cost_allocations ca
             WHERE ca.operation_execution_id = oe.id
          )
          AND NOT EXISTS (
            SELECT 1 FROM cost_allocations ca
             WHERE ca.production_unit_id = oa.production_unit_id
               AND ca.source = 'OPERATION_EXECUTION'
               AND ca.operation_execution_id IS NULL
          )
        """
    )
    op.execute("COMMIT")


def downgrade():
    # Backfill não é reversível com segurança (não há como distinguir
    # allocations criadas por este backfill de allocations legítimas
    # criadas normalmente pela aplicação depois que a migration rodou).
    pass
