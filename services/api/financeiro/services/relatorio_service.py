import uuid
from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Date, func, literal, select, union_all

from financeiro.models.despesa import Despesa
from financeiro.models.receita import Receita
from financeiro.models.rateio import Rateio
from agricola.safras.models import Safra
from core.cadastros.propriedades.models import AreaRural
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.relatorio_schema import (
    FluxoCaixaPeriodo,
    FluxoCaixaTotais,
    FluxoCaixaResponse,
    LivroCaixaLancamento,
    LivroCaixaGrupo,
    LivroCaixaResponse,
    DREResponse,
    CentroCustoCategoria,
    CentroCusto,
    CentroCustoResponse,
)

STATUS_REALIZADO_RECEITA = {"RECEBIDO", "RECEBIDO_PARCIAL"}
STATUS_REALIZADO_DESPESA = {"PAGO", "PAGO_PARCIAL"}
STATUS_PREVISTO_RECEITA = {"A_RECEBER"}
STATUS_PREVISTO_DESPESA = {"A_PAGAR", "ATRASADO"}


def _primeiro_dia(d: date) -> date:
    return d.replace(day=1)


def _meses_entre(inicio: date, fim: date) -> list[date]:
    meses = []
    atual = _primeiro_dia(inicio)
    fim_mes = _primeiro_dia(fim)
    while atual <= fim_mes:
        meses.append(atual)
        atual += relativedelta(months=1)
    return meses


def _periodo_mensal(coluna):
    return func.date_trunc("month", coluna).cast(Date).label("periodo")


class RelatorioService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def fluxo_caixa(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FluxoCaixaResponse:
        meses = _meses_entre(data_inicio, data_fim)
        periodos_map: dict[date, FluxoCaixaPeriodo] = {
            m: FluxoCaixaPeriodo(periodo=m) for m in meses
        }

        consultas = self._consultas_fluxo_caixa(data_inicio, data_fim, unidade_produtiva_id)
        stmt = union_all(*consultas).subquery()
        agrupado = select(
            stmt.c.periodo,
            func.sum(stmt.c.receitas_realizadas).label("receitas_realizadas"),
            func.sum(stmt.c.despesas_realizadas).label("despesas_realizadas"),
            func.sum(stmt.c.receitas_previstas).label("receitas_previstas"),
            func.sum(stmt.c.despesas_previstas).label("despesas_previstas"),
        ).group_by(stmt.c.periodo).order_by(stmt.c.periodo)

        for row in (await self.session.execute(agrupado)).all():
            periodo = _primeiro_dia(row.periodo)
            if periodo not in periodos_map:
                continue
            item = periodos_map[periodo]
            item.receitas_realizadas = float(row.receitas_realizadas or 0.0)
            item.despesas_realizadas = float(row.despesas_realizadas or 0.0)
            item.receitas_previstas = float(row.receitas_previstas or 0.0)
            item.despesas_previstas = float(row.despesas_previstas or 0.0)

        # Calcula saldos e acumulado
        saldo_acumulado = 0.0
        for mes in meses:
            p = periodos_map[mes]
            p.receitas_realizadas = round(p.receitas_realizadas, 2)
            p.despesas_realizadas = round(p.despesas_realizadas, 2)
            p.receitas_previstas = round(p.receitas_previstas, 2)
            p.despesas_previstas = round(p.despesas_previstas, 2)
            p.saldo_realizado = round(p.receitas_realizadas - p.despesas_realizadas, 2)
            p.saldo_previsto = round(p.receitas_previstas - p.despesas_previstas, 2)
            saldo_acumulado += p.saldo_realizado
            p.saldo_acumulado = round(saldo_acumulado, 2)

        periodos = [periodos_map[m] for m in meses]

        totais = FluxoCaixaTotais(
            total_receitas_realizadas=round(sum(p.receitas_realizadas for p in periodos), 2),
            total_despesas_realizadas=round(sum(p.despesas_realizadas for p in periodos), 2),
            total_saldo_realizado=round(sum(p.saldo_realizado for p in periodos), 2),
            total_receitas_previstas=round(sum(p.receitas_previstas for p in periodos), 2),
            total_despesas_previstas=round(sum(p.despesas_previstas for p in periodos), 2),
            total_saldo_previsto=round(sum(p.saldo_previsto for p in periodos), 2),
        )

        return FluxoCaixaResponse(
            data_inicio=data_inicio,
            data_fim=data_fim,
            unidade_produtiva_id=unidade_produtiva_id,
            periodos=periodos,
            totais=totais,
        )

    def _consultas_fluxo_caixa(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list:
        consultas = [
            self._receitas_realizadas_fluxo(data_inicio, data_fim, unidade_produtiva_id),
            self._receitas_previstas_fluxo(data_inicio, data_fim, unidade_produtiva_id),
            self._despesas_realizadas_fluxo(data_inicio, data_fim, unidade_produtiva_id),
            self._despesas_previstas_fluxo(data_inicio, data_fim, unidade_produtiva_id),
        ]
        return consultas

    def _base_fluxo_query(self, model, valor_coluna, periodo_coluna, statuses, label):
        colunas = {
            "receitas_realizadas": literal(0.0),
            "despesas_realizadas": literal(0.0),
            "receitas_previstas": literal(0.0),
            "despesas_previstas": literal(0.0),
        }
        colunas[label] = func.coalesce(func.sum(valor_coluna), 0.0)
        stmt = select(
            _periodo_mensal(periodo_coluna),
            colunas["receitas_realizadas"].label("receitas_realizadas"),
            colunas["despesas_realizadas"].label("despesas_realizadas"),
            colunas["receitas_previstas"].label("receitas_previstas"),
            colunas["despesas_previstas"].label("despesas_previstas"),
        ).where(
            model.tenant_id == self.tenant_id,
            model.ativo == True,
            model.status.in_(statuses),
            periodo_coluna.is_not(None),
        )
        return stmt.group_by(_periodo_mensal(periodo_coluna))

    def _receitas_realizadas_fluxo(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None,
    ):
        stmt = self._base_fluxo_query(
            Receita,
            func.coalesce(Receita.valor_recebido, Receita.valor_total),
            Receita.data_recebimento,
            STATUS_REALIZADO_RECEITA,
            "receitas_realizadas",
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        return stmt.where(Receita.data_recebimento >= data_inicio, Receita.data_recebimento <= data_fim)

    def _receitas_previstas_fluxo(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None,
    ):
        stmt = self._base_fluxo_query(
            Receita,
            Receita.valor_total,
            Receita.data_vencimento,
            STATUS_PREVISTO_RECEITA,
            "receitas_previstas",
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        return stmt.where(Receita.data_vencimento >= data_inicio, Receita.data_vencimento <= data_fim)

    def _despesas_realizadas_fluxo(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None,
    ):
        stmt = self._base_fluxo_query(
            Despesa,
            func.coalesce(Despesa.valor_pago, Despesa.valor_total),
            Despesa.data_pagamento,
            STATUS_REALIZADO_DESPESA,
            "despesas_realizadas",
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        return stmt.where(Despesa.data_pagamento >= data_inicio, Despesa.data_pagamento <= data_fim)

    def _despesas_previstas_fluxo(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None,
    ):
        stmt = self._base_fluxo_query(
            Despesa,
            Despesa.valor_total,
            Despesa.data_vencimento,
            STATUS_PREVISTO_DESPESA,
            "despesas_previstas",
        )
        if unidade_produtiva_id:
            stmt = stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        return stmt.where(Despesa.data_vencimento >= data_inicio, Despesa.data_vencimento <= data_fim)

    def _base_livro_caixa_query(
        self,
        model,
        data_expr,
        valor_expr,
        tipo: str,
    ):
        return select(
            func.coalesce(model.competencia, data_expr).label("data"),
            model.descricao.label("descricao"),
            literal(tipo).label("tipo"),
            PlanoConta.categoria_rfb.label("categoria_rfb"),
            PlanoConta.nome.label("plano_conta_nome"),
            func.coalesce(valor_expr, model.valor_total).label("valor"),
            (model.forma_recebimento if tipo == "RECEITA" else model.forma_pagamento).label("forma"),
            model.numero_nf.label("documento"),
        ).join(
            PlanoConta,
            model.plano_conta_id == PlanoConta.id,
        ).where(
            model.tenant_id == self.tenant_id,
            model.ativo == True,
        )

    def _data_ref_livro_caixa(self, model, data_expr):
        return func.coalesce(model.competencia, data_expr)

    async def livro_caixa(
        self,
        competencia_inicio: date,
        competencia_fim: date,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> LivroCaixaResponse:
        """
        Livro Caixa do Produtor Rural (RFB).
        Agrupa lançamentos realizados por categoria_rfb do plano de contas.
        Filtra por campo `competencia` quando preenchido, senão usa data_recebimento/data_pagamento.
        """
        receitas = self._base_livro_caixa_query(
            Receita,
            Receita.data_recebimento,
            Receita.valor_recebido,
            "RECEITA",
        ).where(
            Receita.status.in_(STATUS_REALIZADO_RECEITA),
            self._data_ref_livro_caixa(Receita, Receita.data_recebimento).is_not(None),
            self._data_ref_livro_caixa(Receita, Receita.data_recebimento) >= competencia_inicio,
            self._data_ref_livro_caixa(Receita, Receita.data_recebimento) <= competencia_fim,
        )
        despesas = self._base_livro_caixa_query(
            Despesa,
            Despesa.data_pagamento,
            Despesa.valor_pago,
            "DESPESA",
        ).where(
            Despesa.status.in_(STATUS_REALIZADO_DESPESA),
            self._data_ref_livro_caixa(Despesa, Despesa.data_pagamento).is_not(None),
            self._data_ref_livro_caixa(Despesa, Despesa.data_pagamento) >= competencia_inicio,
            self._data_ref_livro_caixa(Despesa, Despesa.data_pagamento) <= competencia_fim,
        )
        if unidade_produtiva_id:
            receitas = receitas.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
            despesas = despesas.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)

        combined = union_all(receitas, despesas)
        lancamentos_rows = (await self.session.execute(combined)).mappings().all()

        lancamentos: list[LivroCaixaLancamento] = [
            LivroCaixaLancamento(
                data=row["data"],
                descricao=row["descricao"],
                tipo=row["tipo"],
                categoria_rfb=row["categoria_rfb"],
                plano_conta_nome=row["plano_conta_nome"],
                valor=float(row["valor"] or 0.0),
                forma=row["forma"],
                documento=row["documento"],
            )
            for row in lancamentos_rows
        ]

        # Agrupa por (categoria_rfb, tipo)
        grupos_map: dict[tuple, list[LivroCaixaLancamento]] = defaultdict(list)
        for l in sorted(lancamentos, key=lambda x: x.data):
            key = (l.categoria_rfb or "SEM_CATEGORIA", l.tipo)
            grupos_map[key].append(l)

        grupos = [
            LivroCaixaGrupo(
                categoria_rfb=key[0],
                tipo=key[1],
                total=round(sum(l.valor for l in items), 2),
                lancamentos=items,
            )
            for key, items in sorted(grupos_map.items())
        ]

        total_receitas = round(sum(g.total for g in grupos if g.tipo == "RECEITA"), 2)
        total_despesas = round(sum(g.total for g in grupos if g.tipo == "DESPESA"), 2)

        return LivroCaixaResponse(
            competencia_inicio=competencia_inicio,
            competencia_fim=competencia_fim,
            unidade_produtiva_id=unidade_produtiva_id,
            total_receitas=total_receitas,
            total_despesas=total_despesas,
            resultado=round(total_receitas - total_despesas, 2),
            grupos=grupos,
        )

    async def dre(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> DREResponse:
        """
        DRE financeira simplificada: agrupa por categoria_rfb do plano de contas.
        Usa agregação SQL direta para evitar carregamento massivo de registros em memória.
        """
        receita_stmt = select(
            PlanoConta.categoria_rfb.label("categoria_rfb"),
            literal("RECEITA").label("tipo"),
            func.sum(func.coalesce(Receita.valor_recebido, Receita.valor_total)).label("total"),
        ).join(PlanoConta, Receita.plano_conta_id == PlanoConta.id).where(
            Receita.tenant_id == self.tenant_id,
            Receita.ativo == True,
            Receita.status.in_(STATUS_REALIZADO_RECEITA),
            func.coalesce(Receita.competencia, Receita.data_recebimento) >= data_inicio,
            func.coalesce(Receita.competencia, Receita.data_recebimento) <= data_fim,
        )
        if unidade_produtiva_id:
            receita_stmt = receita_stmt.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        receita_stmt = receita_stmt.group_by(PlanoConta.categoria_rfb)

        despesa_stmt = select(
            PlanoConta.categoria_rfb.label("categoria_rfb"),
            literal("DESPESA").label("tipo"),
            func.sum(func.coalesce(Despesa.valor_pago, Despesa.valor_total)).label("total"),
        ).join(PlanoConta, Despesa.plano_conta_id == PlanoConta.id).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.ativo == True,
            Despesa.status.in_(STATUS_REALIZADO_DESPESA),
            func.coalesce(Despesa.competencia, Despesa.data_pagamento) >= data_inicio,
            func.coalesce(Despesa.competencia, Despesa.data_pagamento) <= data_fim,
        )
        if unidade_produtiva_id:
            despesa_stmt = despesa_stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        despesa_stmt = despesa_stmt.group_by(PlanoConta.categoria_rfb)

        rows = (await self.session.execute(union_all(receita_stmt, despesa_stmt))).all()
        totais_rfb: dict[tuple, float] = defaultdict(float)
        for row in rows:
            totais_rfb[(row.categoria_rfb or "SEM_CATEGORIA", row.tipo)] += float(row.total or 0.0)

        receita_atividade = totais_rfb.get(("RECEITA_ATIVIDADE", "RECEITA"), 0.0)
        outras_receitas = totais_rfb.get(("RECEITA_FORA_ATIVIDADE", "RECEITA"), 0.0)
        custeio = totais_rfb.get(("CUSTEIO", "DESPESA"), 0.0)
        investimento = totais_rfb.get(("INVESTIMENTO", "DESPESA"), 0.0)
        nao_dedutivel = totais_rfb.get(("NAO_DEDUTIVEL", "DESPESA"), 0.0)

        resultado_atividade = round(receita_atividade - custeio, 2)
        resultado_liquido = round(resultado_atividade + outras_receitas - nao_dedutivel, 2)

        return DREResponse(
            data_inicio=data_inicio,
            data_fim=data_fim,
            unidade_produtiva_id=unidade_produtiva_id,
            receita_bruta=round(receita_atividade, 2),
            total_custeio=round(custeio, 2),
            total_investimento=round(investimento, 2),
            total_nao_dedutivel=round(nao_dedutivel, 2),
            resultado_atividade_rural=resultado_atividade,
            outras_receitas=round(outras_receitas, 2),
            resultado_liquido=resultado_liquido,
        )

    async def centro_custos(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
    ) -> CentroCustoResponse:
        """
        Custo por centro de custo (safra/talhão).
        Considera apenas despesas pagas (PAGO/PAGO_PARCIAL) com rateios no período.
        """
        # Lookups
        planos_stmt = select(PlanoConta).where(PlanoConta.tenant_id == self.tenant_id)
        planos = {
            pc.id: pc
            for pc in (await self.session.execute(planos_stmt)).scalars().all()
        }

        safras_stmt = select(Safra).where(Safra.tenant_id == self.tenant_id)
        safras = {
            s.id: s
            for s in (await self.session.execute(safras_stmt)).scalars().all()
        }

        talhoes_stmt = select(AreaRural).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.tipo == "TALHAO",
        )
        talhoes = {
            t.id: t
            for t in (await self.session.execute(talhoes_stmt)).scalars().all()
        }

        # Despesas pagas no período
        desp_stmt = select(Despesa).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.ativo == True,
            Despesa.status.in_({"PAGO", "PAGO_PARCIAL"}),
            Despesa.data_pagamento >= data_inicio,
            Despesa.data_pagamento <= data_fim,
        )
        if unidade_produtiva_id:
            desp_stmt = desp_stmt.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        despesas_map = {
            d.id: d
            for d in (await self.session.execute(desp_stmt)).scalars().all()
        }

        if not despesas_map:
            return CentroCustoResponse(
                data_inicio=data_inicio,
                data_fim=data_fim,
                unidade_produtiva_id=unidade_produtiva_id,
                total_geral=0.0,
                centros=[],
            )

        # Rateios das despesas do período
        rat_stmt = select(Rateio).where(
            Rateio.tenant_id == self.tenant_id,
            Rateio.despesa_id.in_(list(despesas_map.keys())),
        )
        if safra_id:
            rat_stmt = rat_stmt.where(Rateio.safra_id == safra_id)
        rateios = list((await self.session.execute(rat_stmt)).scalars().all())

        # Agrupa por (safra_id, talhao_id) → plano_conta_id → [valores]
        grupos: dict[tuple, dict[uuid.UUID, list[float]]] = defaultdict(lambda: defaultdict(list))
        for r in rateios:
            key = (r.safra_id, r.talhao_id)
            desp = despesas_map.get(r.despesa_id)
            if desp:
                grupos[key][desp.plano_conta_id].append(float(r.valor_rateado))

        centros: list[CentroCusto] = []
        for (s_id, t_id), por_plano in sorted(grupos.items(), key=lambda x: str(x[0])):
            safra = safras.get(s_id) if s_id else None
            talhao = talhoes.get(t_id) if t_id else None

            categorias = [
                CentroCustoCategoria(
                    plano_conta_nome=planos[pc_id].nome if pc_id in planos else "—",
                    categoria_rfb=planos[pc_id].categoria_rfb if pc_id in planos else None,
                    total_rateado=round(sum(vals), 2),
                    quantidade=len(vals),
                )
                for pc_id, vals in sorted(por_plano.items(), key=lambda x: str(x[0]))
            ]
            total = round(sum(c.total_rateado for c in categorias), 2)

            centros.append(CentroCusto(
                safra_id=s_id,
                safra_nome=f"{safra.cultura} {safra.ano_safra}" if safra else None,
                talhao_id=t_id,
                talhao_nome=talhao.nome if talhao else None,
                total_rateado=total,
                por_categoria=sorted(categorias, key=lambda x: x.total_rateado, reverse=True),
            ))

        centros.sort(key=lambda x: x.total_rateado, reverse=True)
        total_geral = round(sum(c.total_rateado for c in centros), 2)

        return CentroCustoResponse(
            data_inicio=data_inicio,
            data_fim=data_fim,
            unidade_produtiva_id=unidade_produtiva_id,
            total_geral=total_geral,
            centros=centros,
        )
