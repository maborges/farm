import uuid
import asyncio
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, func, literal, select

from financeiro.models.despesa import Despesa
from financeiro.models.receita import Receita
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.relatorio_schema import (
    AlertaFinanceiro,
    DashboardFinanceiroResponse,
    TopCategoria,
    VencimentoProximo,
)


class DashboardService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def _agregados_receitas(self, inicio_mes: date, hoje: date, unidade_produtiva_id: uuid.UUID | None):
        recebido = func.coalesce(Receita.valor_recebido, Receita.valor_total)
        stmt = select(
            func.coalesce(func.sum(case(
                ((Receita.status.in_({"RECEBIDO", "RECEBIDO_PARCIAL"})) & (Receita.data_recebimento >= inicio_mes), recebido),
                else_=0,
            )), 0.0).label("total_recebido_mes"),
            func.coalesce(func.sum(case((Receita.status == "A_RECEBER", Receita.valor_total), else_=0)), 0.0).label("total_a_receber"),
            func.coalesce(func.sum(case(((Receita.status == "A_RECEBER") & (Receita.data_vencimento < hoje), Receita.valor_total), else_=0)), 0.0).label("total_atrasado_receitas"),
        ).where(Receita.tenant_id == self.tenant_id, Receita.ativo == True)
        if unidade_produtiva_id:
            stmt = stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt)).one()

    async def _agregados_despesas(self, inicio_mes: date, hoje: date, unidade_produtiva_id: uuid.UUID | None):
        pago = func.coalesce(Despesa.valor_pago, Despesa.valor_total)
        stmt = select(
            func.coalesce(func.sum(case(((Despesa.status.in_({"PAGO", "PAGO_PARCIAL"})) & (Despesa.data_pagamento >= inicio_mes), pago), else_=0)), 0.0).label("total_pago_mes"),
            func.coalesce(func.sum(case((Despesa.status.in_({"A_PAGAR", "ATRASADO"}), Despesa.valor_total), else_=0)), 0.0).label("total_a_pagar"),
            func.coalesce(func.sum(case(((Despesa.status.in_({"A_PAGAR", "ATRASADO"})) & (Despesa.data_vencimento < hoje), Despesa.valor_total), else_=0)), 0.0).label("total_atrasado_despesas"),
        ).where(Despesa.tenant_id == self.tenant_id, Despesa.ativo == True)
        if unidade_produtiva_id:
            stmt = stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt)).one()

    async def _vencimentos_receitas(self, hoje: date, unidade_produtiva_id: uuid.UUID | None):
        stmt = select(
            Receita.id,
            literal("RECEITA").label("tipo"),
            Receita.descricao,
            Receita.valor_total.label("valor"),
            Receita.data_vencimento,
            Receita.cliente.label("pessoa_nome"),
        ).where(
            Receita.tenant_id == self.tenant_id,
            Receita.ativo == True,
            Receita.status == "A_RECEBER",
            Receita.data_vencimento >= hoje + timedelta(days=1),
            Receita.data_vencimento <= hoje + timedelta(days=30),
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt.order_by(Receita.data_vencimento))).mappings().all()

    async def _vencimentos_despesas(self, hoje: date, unidade_produtiva_id: uuid.UUID | None):
        stmt = select(
            Despesa.id,
            literal("DESPESA").label("tipo"),
            Despesa.descricao,
            Despesa.valor_total.label("valor"),
            Despesa.data_vencimento,
            Despesa.fornecedor.label("pessoa_nome"),
        ).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.ativo == True,
            Despesa.status.in_({"A_PAGAR", "ATRASADO"}),
            Despesa.data_vencimento >= hoje + timedelta(days=1),
            Despesa.data_vencimento <= hoje + timedelta(days=30),
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt.order_by(Despesa.data_vencimento))).mappings().all()

    async def _top_receitas(self, inicio_mes: date, unidade_produtiva_id: uuid.UUID | None):
        stmt = select(
            PlanoConta.nome.label("plano_conta_nome"),
            PlanoConta.categoria_rfb.label("categoria_rfb"),
            func.count(Receita.id).label("quantidade"),
            func.sum(func.coalesce(Receita.valor_recebido, Receita.valor_total)).label("total"),
        ).join(PlanoConta, Receita.plano_conta_id == PlanoConta.id).where(
            Receita.tenant_id == self.tenant_id,
            Receita.ativo == True,
            Receita.status.in_({"RECEBIDO", "RECEBIDO_PARCIAL"}),
            Receita.data_recebimento >= inicio_mes,
        ).group_by(PlanoConta.nome, PlanoConta.categoria_rfb).order_by(func.sum(func.coalesce(Receita.valor_recebido, Receita.valor_total)).desc()).limit(5)
        if unidade_produtiva_id:
            stmt = stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt)).all()

    async def _top_despesas(self, inicio_mes: date, unidade_produtiva_id: uuid.UUID | None):
        stmt = select(
            PlanoConta.nome.label("plano_conta_nome"),
            PlanoConta.categoria_rfb.label("categoria_rfb"),
            func.count(Despesa.id).label("quantidade"),
            func.sum(func.coalesce(Despesa.valor_pago, Despesa.valor_total)).label("total"),
        ).join(PlanoConta, Despesa.plano_conta_id == PlanoConta.id).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.ativo == True,
            Despesa.status.in_({"PAGO", "PAGO_PARCIAL"}),
            Despesa.data_pagamento >= inicio_mes,
        ).group_by(PlanoConta.nome, PlanoConta.categoria_rfb).order_by(func.sum(func.coalesce(Despesa.valor_pago, Despesa.valor_total)).desc()).limit(5)
        if unidade_produtiva_id:
            stmt = stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        return (await self.session.execute(stmt)).all()

    async def resumo(
        self, unidade_produtiva_id: uuid.UUID | None = None
    ) -> DashboardFinanceiroResponse:
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)

        rec_resumo, desp_resumo, rec_venc, desp_venc, top_rec, top_desp = await asyncio.gather(
            self._agregados_receitas(inicio_mes, hoje, unidade_produtiva_id),
            self._agregados_despesas(inicio_mes, hoje, unidade_produtiva_id),
            self._vencimentos_receitas(hoje, unidade_produtiva_id),
            self._vencimentos_despesas(hoje, unidade_produtiva_id),
            self._top_receitas(inicio_mes, unidade_produtiva_id),
            self._top_despesas(inicio_mes, unidade_produtiva_id),
        )

        total_recebido_mes = float(rec_resumo.total_recebido_mes or 0.0)
        total_a_receber = float(rec_resumo.total_a_receber or 0.0)
        total_atrasado_receitas = float(rec_resumo.total_atrasado_receitas or 0.0)
        total_pago_mes = float(desp_resumo.total_pago_mes or 0.0)
        total_a_pagar = float(desp_resumo.total_a_pagar or 0.0)
        total_atrasado_despesas = float(desp_resumo.total_atrasado_despesas or 0.0)

        vencendo_7d: list[VencimentoProximo] = []
        vencendo_8_15d: list[VencimentoProximo] = []
        vencendo_16_30d: list[VencimentoProximo] = []

        for row in (*rec_venc, *desp_venc):
            dias = (row["data_vencimento"] - hoje).days
            item = VencimentoProximo(
                id=row["id"],
                tipo=row["tipo"],
                descricao=row["descricao"],
                valor=float(row["valor"] or 0.0),
                data_vencimento=row["data_vencimento"],
                dias_restantes=dias,
                pessoa_nome=row["pessoa_nome"],
            )
            if dias <= 7:
                vencendo_7d.append(item)
            elif dias <= 15:
                vencendo_8_15d.append(item)
            elif dias <= 30:
                vencendo_16_30d.append(item)

        _sort = lambda lst: sorted(lst, key=lambda x: x.data_vencimento)
        vencendo_7d = _sort(vencendo_7d)
        vencendo_8_15d = _sort(vencendo_8_15d)
        vencendo_16_30d = _sort(vencendo_16_30d)

        top_despesas = [
            TopCategoria(
                plano_conta_nome=row.plano_conta_nome,
                categoria_rfb=row.categoria_rfb,
                total=round(float(row.total or 0.0), 2),
                quantidade=int(row.quantidade or 0),
            )
            for row in top_desp
        ]
        top_receitas = [
            TopCategoria(
                plano_conta_nome=row.plano_conta_nome,
                categoria_rfb=row.categoria_rfb,
                total=round(float(row.total or 0.0), 2),
                quantidade=int(row.quantidade or 0),
            )
            for row in top_rec
        ]

        # ── Alertas ───────────────────────────────────────────────────────
        alertas: list[AlertaFinanceiro] = []

        if total_atrasado_despesas > 0:
            alertas.append(AlertaFinanceiro(
                tipo="ATRASADO",
                nivel="CRITICO",
                mensagem=f"Você tem R$ {total_atrasado_despesas:,.2f} em contas a pagar vencidas.",
                valor=total_atrasado_despesas,
            ))
        if total_atrasado_receitas > 0:
            alertas.append(AlertaFinanceiro(
                tipo="ATRASADO",
                nivel="ALERTA",
                mensagem=f"Há R$ {total_atrasado_receitas:,.2f} em contas a receber vencidas.",
                valor=total_atrasado_receitas,
            ))
        venc_7d_desp = sum(i.valor for i in vencendo_7d if i.tipo == "DESPESA")
        if venc_7d_desp > 0:
            alertas.append(AlertaFinanceiro(
                tipo="VENCIMENTO_PROXIMO",
                nivel="ALERTA",
                mensagem=f"R$ {venc_7d_desp:,.2f} em despesas vencem nos próximos 7 dias.",
                valor=venc_7d_desp,
                data_referencia=hoje + timedelta(days=7),
            ))
        saldo_mes = round(total_recebido_mes - total_pago_mes, 2)
        if saldo_mes < 0:
            alertas.append(AlertaFinanceiro(
                tipo="SALDO_NEGATIVO",
                nivel="CRITICO",
                mensagem=f"Saldo do mês negativo: R$ {saldo_mes:,.2f}.",
                valor=saldo_mes,
            ))

        return DashboardFinanceiroResponse(
            data_referencia=hoje,
            unidade_produtiva_id=unidade_produtiva_id,
            total_recebido_mes=round(total_recebido_mes, 2),
            total_pago_mes=round(total_pago_mes, 2),
            saldo_mes=saldo_mes,
            total_a_receber=round(total_a_receber, 2),
            total_a_pagar=round(total_a_pagar, 2),
            total_atrasado_receitas=round(total_atrasado_receitas, 2),
            total_atrasado_despesas=round(total_atrasado_despesas, 2),
            vencendo_7d=vencendo_7d,
            vencendo_8_15d=vencendo_8_15d,
            vencendo_16_30d=vencendo_16_30d,
            top_despesas=top_despesas,
            top_receitas=top_receitas,
            alertas=alertas,
        )
