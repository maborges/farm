import asyncio
from datetime import date
from sqlalchemy import case, func, select
from sqlalchemy.dialects import postgresql
from financeiro.models.receita import Receita

hoje = date(2026, 6, 20)
inicio_mes = date(2026, 6, 1)

recebido = func.coalesce(Receita.valor_recebido, Receita.valor_total)
stmt = select(
    func.coalesce(func.sum(case(
        ((Receita.status.in_({"RECEBIDO", "RECEBIDO_PARCIAL"})) & (Receita.data_recebimento >= inicio_mes), recebido),
        else_=0,
    )), 0.0).label("total_recebido_mes"),
    func.coalesce(func.sum(case((Receita.status == "A_RECEBER", Receita.valor_total), else_=0)), 0.0).label("total_a_receber"),
    func.coalesce(func.sum(case(((Receita.status == "A_RECEBER") & (Receita.data_vencimento < hoje), Receita.valor_total), else_=0)), 0.0).label("total_atrasado_receitas"),
).where(Receita.tenant_id == '678122a2-700d-4425-a779-043395c2246a', Receita.ativo == True)

print(stmt.compile(dialect=postgresql.dialect()))
