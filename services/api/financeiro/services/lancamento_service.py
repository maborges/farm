import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.schemas.lancamento_schema import LancamentoCreate, LancamentoResumo, InsightDashboard, CategoriaBreakdown, SerieTemporal, AlertaSafra
from agricola.safras.models import Safra
from agricola.cenarios.models import SafraCenario


class LancamentoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: LancamentoCreate) -> LancamentoFinanceiro:
        lancamento = LancamentoFinanceiro(
            tenant_id=self.tenant_id,
            safra_id=data.safra_id,
            descricao=data.descricao,
            valor=data.valor,
            data=data.data,
            tipo=data.tipo,
            categoria=data.categoria,
        )
        self.session.add(lancamento)
        await self.session.commit()
        await self.session.refresh(lancamento)
        return lancamento

    async def resumo(self) -> LancamentoResumo:
        stmt = select(
            func.coalesce(
                func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "CUSTO"), 0
            ).label("total_custos"),
            func.coalesce(
                func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "RECEITA"), 0
            ).label("total_receitas"),
            func.count(LancamentoFinanceiro.id).label("quantidade"),
        ).where(LancamentoFinanceiro.tenant_id == self.tenant_id)

        row = (await self.session.execute(stmt)).one()
        total_custos = float(row.total_custos)
        total_receitas = float(row.total_receitas)
        return LancamentoResumo(
            total_custos=total_custos,
            total_receitas=total_receitas,
            saldo=total_receitas - total_custos,
            quantidade=row.quantidade,
        )

    async def insight_dashboard(self) -> InsightDashboard:
        """Agrega lançamentos + cenário base da safra mais recente para o dashboard."""
        # Resumo geral de lançamentos
        stmt_resumo = select(
            func.coalesce(func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "CUSTO"), 0).label("total_custos"),
            func.count(LancamentoFinanceiro.id).label("quantidade"),
        ).where(LancamentoFinanceiro.tenant_id == self.tenant_id)
        row = (await self.session.execute(stmt_resumo)).one()
        total_custos = float(row.total_custos)
        quantidade = int(row.quantidade)

        # Safra mais recente do tenant
        stmt_safra = (
            select(Safra)
            .where(and_(Safra.tenant_id == self.tenant_id, Safra.status != "CANCELADA"))
            .order_by(Safra.created_at.desc())
            .limit(1)
        )
        safra = (await self.session.execute(stmt_safra)).scalar_one_or_none()

        cenario_custo = None
        cenario_receita = None
        cenario_margem = None
        safra_nome = None

        if safra:
            safra_nome = safra.ano_safra
            stmt_cenario = (
                select(SafraCenario)
                .where(and_(
                    SafraCenario.tenant_id == self.tenant_id,
                    SafraCenario.safra_id == safra.id,
                    SafraCenario.eh_base == True,
                ))
                .limit(1)
            )
            cenario = (await self.session.execute(stmt_cenario)).scalar_one_or_none()
            if cenario:
                cenario_custo = float(cenario.custo_total) if cenario.custo_total is not None else None
                cenario_receita = float(cenario.receita_bruta_total) if cenario.receita_bruta_total is not None else None
                if cenario_custo is not None and cenario_receita is not None:
                    cenario_margem = cenario_receita - cenario_custo

        # Gerar mensagem de insight
        mensagem = None
        if total_custos > 0 and cenario_margem is None:
            mensagem = "Você já começou a registrar custos da sua safra."
        elif cenario_margem is not None and cenario_margem < 0:
            mensagem = "Sua operação está com margem negativa. Revise os custos."
        elif cenario_margem is not None and cenario_margem >= 0:
            mensagem = "Sua safra está com margem positiva."

        # Breakdown por categoria (somente CUSTO)
        stmt_cat = select(
            LancamentoFinanceiro.categoria,
            func.sum(LancamentoFinanceiro.valor).label("total"),
        ).where(
            and_(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.tipo == "CUSTO",
            )
        ).group_by(LancamentoFinanceiro.categoria).order_by(func.sum(LancamentoFinanceiro.valor).desc())

        cat_rows = (await self.session.execute(stmt_cat)).fetchall()
        categorias = [CategoriaBreakdown(nome=r[0] or "OPERACOES", valor=float(r[1])) for r in cat_rows]

        return InsightDashboard(
            total_custos=total_custos,
            quantidade_lancamentos=quantidade,
            safra_id=safra.id if safra else None,
            safra_nome=safra_nome,
            cenario_custo_total=cenario_custo,
            cenario_receita_total=cenario_receita,
            cenario_margem=cenario_margem,
            mensagem=mensagem,
            categorias=categorias,
        )

    async def gerar_alertas(self, safra_id: uuid.UUID) -> list[AlertaSafra]:
        alertas: list[AlertaSafra] = []

        # Total de custos na safra
        stmt_total = select(
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0).label("total"),
            func.count(LancamentoFinanceiro.id).label("qtd"),
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "CUSTO",
        ))
        row = (await self.session.execute(stmt_total)).one()
        total_custos = float(row.total)
        qtd = int(row.qtd)

        if total_custos > 0:
            alertas.append(AlertaSafra(
                tipo="CUSTO_REGISTRADO",
                nivel="info",
                mensagem=f"Você possui {qtd} lançamento{'s' if qtd != 1 else ''} de custo registrado{'s' if qtd != 1 else ''} nesta safra.",
            ))

        # Margem do cenário BASE
        stmt_cenario = (
            select(SafraCenario)
            .where(and_(
                SafraCenario.tenant_id == self.tenant_id,
                SafraCenario.safra_id == safra_id,
                SafraCenario.eh_base == True,
            ))
            .limit(1)
        )
        cenario = (await self.session.execute(stmt_cenario)).scalar_one_or_none()
        if cenario and cenario.custo_total is not None and cenario.receita_bruta_total is not None:
            margem = float(cenario.receita_bruta_total) - float(cenario.custo_total)
            if margem < 0:
                alertas.append(AlertaSafra(
                    tipo="MARGEM_NEGATIVA",
                    nivel="danger",
                    mensagem=f"Sua operação está com margem negativa de R$ {abs(margem):,.2f}. Revise os custos.",
                ))

        # Variação de custo no último mês (> 20%)
        serie = await self.serie_temporal(safra_id)
        if len(serie) >= 2:
            ultimo = serie[-1].total
            penultimo = serie[-2].total
            if penultimo > 0:
                variacao_pct = (ultimo - penultimo) / penultimo * 100
                if variacao_pct > 20:
                    alertas.append(AlertaSafra(
                        tipo="AUMENTO_CUSTO",
                        nivel="warning",
                        mensagem=f"Seus custos aumentaram {variacao_pct:.1f}% no último período ({serie[-2].periodo} → {serie[-1].periodo}).",
                    ))

        return alertas

    async def serie_temporal(self, safra_id: uuid.UUID) -> list[SerieTemporal]:
        stmt = select(
            func.to_char(LancamentoFinanceiro.data, "YYYY-MM").label("periodo"),
            func.sum(LancamentoFinanceiro.valor).label("total"),
        ).where(
            and_(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.safra_id == safra_id,
                LancamentoFinanceiro.tipo == "CUSTO",
            )
        ).group_by(text("periodo")).order_by(text("periodo ASC"))

        rows = (await self.session.execute(stmt)).fetchall()
        return [SerieTemporal(periodo=r[0], total=float(r[1])) for r in rows]
