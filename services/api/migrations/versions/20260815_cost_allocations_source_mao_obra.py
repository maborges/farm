"""allow APONTAMENTO_MAO_OBRA source in cost_allocations

OPERATIONS-GAP-01 §21.14: ApontamentoMaoObraService gera CostAllocation com
source="APONTAMENTO_MAO_OBRA" quando há production_unit_id resolvido — a
constraint ck_cost_allocations_source precisa incluir esse valor, mesmo padrão
já usado para liberar 'PECUARIA_VACINACAO' (20260624).

Nota: durante esta correção notou-se que 'FROTA_APONTAMENTO' e 'RH_DIARIA'/
'RH_EMPREITADA' (gerados por _mapear_source em operational_cost_service.py)
também não estão na whitelist atual do banco — só não quebram hoje porque, na
prática, o production_unit_id desses fluxos frequentemente não resolve (o que
faz _upsert_allocation retornar None antes de tentar o INSERT). Não corrigido
nesta migration — fora do escopo cirúrgico desta correção; registrado como
achado colateral no relatório de auditoria.

Revision ID: 20260815_cost_alloc_src_mao_obra
Revises: 20260815_apontamento_mao_obra
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_cost_alloc_src_mao_obra"
down_revision = "20260815_apontamento_mao_obra"
branch_labels = None
depends_on = None


def _rebuild_check_constraint(valores: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {check["name"] for check in inspector.get_check_constraints("cost_allocations")}
    if "ck_cost_allocations_source" in constraints:
        op.drop_constraint("ck_cost_allocations_source", "cost_allocations", type_="check")
    op.create_check_constraint(
        "ck_cost_allocations_source",
        "cost_allocations",
        f"source IN ({valores})",
    )


def upgrade() -> None:
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO','APONTAMENTO_MAO_OBRA'"
    )
    op.execute("COMMIT")


def downgrade() -> None:
    _rebuild_check_constraint(
        "'OPERATION_EXECUTION','INVENTORY_MOVEMENT','FIN_RATEIO','MANUAL','PECUARIA_VACINACAO'"
    )
    op.execute("COMMIT")
