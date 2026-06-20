import asyncio
from datetime import date
from sqlalchemy import case, func, select
from sqlalchemy.dialects import postgresql
from financeiro.models.receita import Receita
from financeiro.models.plano_conta import PlanoConta

hoje = date(2026, 6, 20)
inicio_mes = date(2026, 6, 1)

stmt = select(
    PlanoConta.nome.label("plano_conta_nome"),
    PlanoConta.categoria_rfb.label("categoria_rfb"),
    func.count(Receita.id).label("quantidade"),
    func.sum(func.coalesce(Receita.valor_recebido, Receita.valor_total)).label("total"),
).join(PlanoConta, Receita.plano_conta_id == PlanoConta.id).where(
    Receita.tenant_id == '678122a2-700d-4425-a779-043395c2246a',
    Receita.ativo == True,
    Receita.status.in_({"RECEBIDO", "RECEBIDO_PARCIAL"}),
    Receita.data_recebimento >= inicio_mes,
).group_by(PlanoConta.nome, PlanoConta.categoria_rfb).order_by(func.sum(func.coalesce(Receita.valor_recebido, Receita.valor_total)).desc()).limit(5)

print(stmt.compile(dialect=postgresql.dialect()))
