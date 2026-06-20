import uuid
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from financeiro.models.lancamento import LancamentoFinanceiro
from core.schemas.pagination import PaginatedResponse
from financeiro.schemas.lancamento_schema import LancamentoCreate, LancamentoResumo, InsightDashboard, CategoriaBreakdown, SerieTemporal, AlertaSafra, RecomendacaoSafra, ResumoInteligente, ItemPlanoAcao, LancamentoOrigemItem, DREOperacional
from agricola.safras.models import Safra
from agricola.cenarios.models import SafraCenario


class LancamentoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar(self, data: LancamentoCreate) -> LancamentoFinanceiro:
        # Valida que safra_id pertence ao tenant
        if data.safra_id is not None:
            safra = await self.session.get(Safra, data.safra_id)
            if safra is None or safra.tenant_id != self.tenant_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Safra indisponível ou não encontrada para este tenant.")

        # Detecção de duplicata: mesmos tenant+safra+tipo+categoria+valor+data+descricao normalizada
        descricao_norm = data.descricao.strip().lower()
        stmt_dup = select(LancamentoFinanceiro.id).where(
            and_(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.safra_id == data.safra_id,
                LancamentoFinanceiro.tipo == data.tipo,
                LancamentoFinanceiro.categoria == data.categoria,
                LancamentoFinanceiro.valor == data.valor,
                LancamentoFinanceiro.data == data.data,
                func.lower(func.trim(LancamentoFinanceiro.descricao)) == descricao_norm,
            )
        ).limit(1)
        dup = (await self.session.execute(stmt_dup)).first()
        if dup:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Lançamento duplicado: já existe um registro idêntico para esta data, valor, categoria e descrição.",
            )

        lancamento = LancamentoFinanceiro(
            tenant_id=self.tenant_id,
            safra_id=data.safra_id,
            descricao=data.descricao,
            valor=data.valor,
            data=data.data,
            tipo=data.tipo,
            categoria=data.categoria,
            origem=data.origem,
            origem_id=data.origem_id,
        )
        self.session.add(lancamento)
        await self.session.commit()
        await self.session.refresh(lancamento)
        return lancamento

    async def atualizar(self, lancamento_id: uuid.UUID, data: "LancamentoUpdate") -> LancamentoFinanceiro:
        from financeiro.schemas.lancamento_schema import LancamentoUpdate
        from fastapi import HTTPException

        lancamento = (
            await self.session.execute(
                select(LancamentoFinanceiro).where(
                    and_(
                        LancamentoFinanceiro.id == lancamento_id,
                        LancamentoFinanceiro.tenant_id == self.tenant_id,
                    )
                )
            )
        ).scalars().first()

        if lancamento is None:
            raise HTTPException(status_code=404, detail="Lançamento indisponível ou não encontrado.")

        if lancamento.origem is not None and lancamento.origem != "MANUAL":
            raise HTTPException(
                status_code=422,
                detail="Lançamentos gerados pelo estoque devem ser ajustados na movimentação de estoque.",
            )

        if data.descricao is not None:
            lancamento.descricao = data.descricao
        if data.valor is not None:
            lancamento.valor = data.valor
        if data.data is not None:
            lancamento.data = data.data
        if data.categoria is not None:
            lancamento.categoria = data.categoria

        await self.session.flush()
        await self.session.refresh(lancamento)

        if lancamento.safra_id:
            try:
                from agricola.cenarios.service import CenariosService
                await CenariosService(self.session, self.tenant_id).recalcular_base(lancamento.safra_id)
            except Exception:
                pass

        return lancamento

    async def listar_origens(self, safra_id: uuid.UUID) -> list[LancamentoOrigemItem]:
        stmt = (
            select(
                LancamentoFinanceiro.id,
                LancamentoFinanceiro.descricao,
                LancamentoFinanceiro.valor,
                LancamentoFinanceiro.origem,
                LancamentoFinanceiro.origem_id,
                LancamentoFinanceiro.data,
                LancamentoFinanceiro.categoria,
            )
            .where(
                and_(
                    LancamentoFinanceiro.tenant_id == self.tenant_id,
                    LancamentoFinanceiro.safra_id == safra_id,
                )
            )
            .order_by(LancamentoFinanceiro.data.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            LancamentoOrigemItem(
                lancamento_id=r.id,
                descricao=r.descricao,
                valor=float(r.valor),
                origem=r.origem or "MANUAL",
                origem_id=r.origem_id,
                data=r.data,
                categoria=r.categoria,
                gerado_automaticamente=r.origem is not None,
            )
            for r in rows
        ]

    def _aplicar_filtros_listagem(
        self,
        stmt,
        safra_id: uuid.UUID | None,
        tipo: str | None,
        categoria: str | None,
        origem: str | None,
        data_inicio: date | None,
        data_fim: date | None,
    ):
        if safra_id:
            stmt = stmt.where(LancamentoFinanceiro.safra_id == safra_id)
        if tipo:
            stmt = stmt.where(LancamentoFinanceiro.tipo == tipo)
        if categoria:
            stmt = stmt.where(LancamentoFinanceiro.categoria == categoria)
        if origem:
            stmt = stmt.where(LancamentoFinanceiro.origem == origem)
        if data_inicio:
            stmt = stmt.where(LancamentoFinanceiro.data >= data_inicio)
        if data_fim:
            stmt = stmt.where(LancamentoFinanceiro.data <= data_fim)
        return stmt

    async def listar(
        self,
        safra_id: uuid.UUID | None = None,
        tipo: str | None = None,
        categoria: str | None = None,
        origem: str | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResponse[LancamentoFinanceiro]:
        stmt = select(LancamentoFinanceiro).where(LancamentoFinanceiro.tenant_id == self.tenant_id)
        stmt = self._aplicar_filtros_listagem(stmt, safra_id, tipo, categoria, origem, data_inicio, data_fim)

        # Count
        count_stmt = select(func.count()).select_from(LancamentoFinanceiro).where(LancamentoFinanceiro.tenant_id == self.tenant_id)
        count_stmt = self._aplicar_filtros_listagem(count_stmt, safra_id, tipo, categoria, origem, data_inicio, data_fim)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Paginating
        limit = min(limit, 200)
        stmt = stmt.order_by(LancamentoFinanceiro.data.desc(), LancamentoFinanceiro.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )

    async def resumo(self, safra_id: uuid.UUID | None = None) -> LancamentoResumo:
        stmt = select(
            func.coalesce(
                func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "CUSTO"), 0
            ).label("total_custos"),
            func.coalesce(
                func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "RECEITA"), 0
            ).label("total_receitas"),
            func.count(LancamentoFinanceiro.id).label("quantidade"),
        ).where(LancamentoFinanceiro.tenant_id == self.tenant_id)

        if safra_id:
            stmt = stmt.where(LancamentoFinanceiro.safra_id == safra_id)

        row = (await self.session.execute(stmt)).one()
        total_custos = float(row.total_custos)
        total_receitas = float(row.total_receitas)
        return LancamentoResumo(
            total_custos=total_custos,
            total_receitas=total_receitas,
            saldo=total_receitas - total_custos,
            quantidade_lancamentos=row.quantidade,
        )

    async def insight_dashboard(self) -> InsightDashboard:
        """Agrega lançamentos + cenário base da safra mais recente para o dashboard."""
        stmt_resumo = select(
            func.coalesce(func.sum(LancamentoFinanceiro.valor).filter(LancamentoFinanceiro.tipo == "CUSTO"), 0).label("total_custos"),
            func.count(LancamentoFinanceiro.id).label("quantidade"),
        ).where(LancamentoFinanceiro.tenant_id == self.tenant_id)
        row = (await self.session.execute(stmt_resumo)).one()
        total_custos = float(row.total_custos)
        quantidade = int(row.quantidade)

        safra_sq = (
            select(
                Safra.id.label("safra_id"),
                Safra.ano_safra.label("ano_safra"),
            )
            .where(and_(Safra.tenant_id == self.tenant_id, Safra.status != "CANCELADA"))
            .order_by(Safra.created_at.desc())
            .limit(1)
        ).subquery()
        safra_stmt = select(
            safra_sq.c.safra_id,
            safra_sq.c.ano_safra,
            SafraCenario.custo_total,
            SafraCenario.receita_bruta_total,
        ).select_from(
            safra_sq.outerjoin(
                SafraCenario,
                and_(
                    SafraCenario.tenant_id == self.tenant_id,
                    SafraCenario.safra_id == safra_sq.c.safra_id,
                    SafraCenario.eh_base == True,
                ),
            )
        ).limit(1)
        safra_row = (await self.session.execute(safra_stmt)).first()
        cenario_custo = None
        cenario_receita = None
        cenario_margem = None
        safra_nome = None

        if safra_row:
            safra_nome = safra_row.ano_safra
            if safra_row.custo_total is not None:
                cenario_custo = float(safra_row.custo_total)
            if safra_row.receita_bruta_total is not None:
                cenario_receita = float(safra_row.receita_bruta_total)
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
            safra_id=safra_row.safra_id if safra_row else None,
            safra_nome=safra_nome,
            cenario_custo_total=cenario_custo,
            cenario_receita_total=cenario_receita,
            cenario_margem=cenario_margem,
            mensagem=mensagem,
            categorias=categorias,
        )

    async def _contexto_safra(self, safra_id: uuid.UUID) -> dict[str, object]:
        """Carrega os agregados base usados por alertas, recomendações e resumo."""
        stmt_total = select(
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0).label("total"),
            func.count(LancamentoFinanceiro.id).label("qtd"),
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "CUSTO",
        ))
        stmt_cat = select(
            LancamentoFinanceiro.categoria,
            func.sum(LancamentoFinanceiro.valor).label("total"),
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "CUSTO",
        )).group_by(LancamentoFinanceiro.categoria).order_by(func.sum(LancamentoFinanceiro.valor).desc()).limit(1)
        stmt_cenario = select(SafraCenario).where(and_(
            SafraCenario.tenant_id == self.tenant_id,
            SafraCenario.safra_id == safra_id,
            SafraCenario.eh_base == True,
        )).limit(1)
        stmt_serie = select(
            func.to_char(LancamentoFinanceiro.data, "YYYY-MM").label("periodo"),
            func.sum(LancamentoFinanceiro.valor).label("total"),
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "CUSTO",
        )).group_by(text("periodo")).order_by(text("periodo ASC"))

        total_row = (await self.session.execute(stmt_total)).one()
        cat_row = (await self.session.execute(stmt_cat)).first()
        cenario = (await self.session.execute(stmt_cenario)).scalar_one_or_none()
        serie_rows = (await self.session.execute(stmt_serie)).fetchall()
        serie = [SerieTemporal(periodo=r[0], total=float(r[1])) for r in serie_rows]

        margem: float | None = None
        if cenario and cenario.custo_total is not None and cenario.receita_bruta_total is not None:
            margem = float(cenario.receita_bruta_total) - float(cenario.custo_total)

        cat_dominante = None
        if cat_row:
            cat_dominante = str(cat_row[0] or "")

        return {
            "total_custos": float(total_row.total),
            "quantidade": int(total_row.qtd),
            "cat_dominante": cat_dominante,
            "margem": margem,
            "serie": serie,
            "cenario": cenario,
        }

    def _alertas_do_contexto(self, contexto: dict[str, object]) -> list[AlertaSafra]:
        alertas: list[AlertaSafra] = []
        total_custos = float(contexto["total_custos"])
        qtd = int(contexto["quantidade"])
        if total_custos > 0:
            alertas.append(AlertaSafra(
                tipo="CUSTO_REGISTRADO",
                nivel="info",
                mensagem=f"Você possui {qtd} lançamento{'s' if qtd != 1 else ''} de custo registrado{'s' if qtd != 1 else ''} nesta safra.",
            ))

        margem = contexto["margem"]
        if margem is not None and margem < 0:
            alertas.append(AlertaSafra(
                tipo="MARGEM_NEGATIVA",
                nivel="danger",
                mensagem=f"Sua operação está com margem negativa de R$ {abs(margem):,.2f}. Revise os custos.",
            ))

        serie = contexto["serie"]
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

    def _recomendacoes_do_contexto(self, safra_id: uuid.UUID, contexto: dict[str, object]) -> list[RecomendacaoSafra]:
        recomendacoes: list[RecomendacaoSafra] = []
        safra_id_str = str(safra_id)
        margem = contexto["margem"]
        if margem is not None and margem < 0:
            recomendacoes.append(RecomendacaoSafra(
                tipo="REVISAR_CUSTOS",
                mensagem="Revise seus custos operacionais. A margem atual está negativa.",
                acao="Ver cenários",
                rota=f"/agricola/safras/{safra_id_str}/cenarios",
            ))

        if str(contexto["cat_dominante"]).upper() == "INSUMOS":
            recomendacoes.append(RecomendacaoSafra(
                tipo="ANALISAR_INSUMOS",
                mensagem="Custos com insumos estão elevados e lideram sua estrutura de custos.",
                acao="Analisar por categoria",
                rota=f"/agricola/safras/{safra_id_str}/cenarios",
            ))

        serie = contexto["serie"]
        if len(serie) >= 2:
            ultimo = serie[-1].total
            penultimo = serie[-2].total
            if penultimo > 0:
                variacao_pct = (ultimo - penultimo) / penultimo * 100
                if variacao_pct > 20:
                    recomendacoes.append(RecomendacaoSafra(
                        tipo="VER_EVOLUCAO",
                        mensagem=f"Seus custos aumentaram {variacao_pct:.1f}% recentemente. Acompanhe a evolução.",
                        acao="Ver evolução de custos",
                        rota=f"/agricola/safras/{safra_id_str}/operacoes",
                    ))
        return recomendacoes

    async def gerar_alertas(self, safra_id: uuid.UUID) -> list[AlertaSafra]:
        contexto = await self._contexto_safra(safra_id)
        return self._alertas_do_contexto(contexto)

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

    async def gerar_recomendacoes(self, safra_id: uuid.UUID) -> list[RecomendacaoSafra]:
        """Gera recomendações acionáveis baseadas em regras determinísticas.

        Reutiliza dados já disponíveis (cenário base, categorias, série temporal)
        sem recalcular tudo do zero.

        Args:
            safra_id: UUID da safra a ser analisada.

        Returns:
            Lista de RecomendacaoSafra ordenada por prioridade (margem primeiro).
        """
        contexto = await self._contexto_safra(safra_id)
        return self._recomendacoes_do_contexto(safra_id, contexto)

    async def gerar_resumo_inteligente(self, safra_id: uuid.UUID) -> ResumoInteligente:
        LABEL_CAT = {"INSUMOS": "insumos", "MAO_OBRA": "mão de obra", "OPERACOES": "operações", "ADMINISTRATIVO": "administrativo"}

        contexto = await self._contexto_safra(safra_id)
        total_custos = contexto["total_custos"]
        qtd = contexto["quantidade"]
        cat_dominante = LABEL_CAT.get(str(contexto["cat_dominante"]) or "", str(contexto["cat_dominante"]) or "") if contexto["cat_dominante"] else None
        margem = contexto["margem"]
        serie = contexto["serie"]
        alertas = self._alertas_do_contexto(contexto)
        recomendacoes = self._recomendacoes_do_contexto(safra_id, contexto)

        # Monta resumo
        fmt = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        if total_custos == 0:
            return ResumoInteligente(
                titulo="Resumo financeiro da safra",
                resumo="Nenhum custo registrado nesta safra ainda. Comece lançando os primeiros custos operacionais.",
                pontos_atencao=[],
                proximas_acoes=["Registrar primeiro custo", "Vincular insumos à safra"],
            )

        partes_resumo = [f"Sua safra possui {fmt(total_custos)} em custos registrados ({qtd} lançamento{'s' if qtd != 1 else ''})."]
        if cat_dominante:
            partes_resumo.append(f"A maior concentração está em {cat_dominante}.")
        if margem is not None:
            if margem >= 0:
                partes_resumo.append(f"O cenário base apresenta margem positiva de {fmt(margem)}.")
            else:
                partes_resumo.append(f"O cenário base apresenta margem negativa de {fmt(abs(margem))}.")

        # Pontos de atenção priorizados e deduplicados por tipo semântico
        # Ordem: margem_negativa → aumento_custo → categoria_dominante
        pontos: list[str] = []
        seen: set[str] = set()

        # 1. Margem negativa (danger — máxima prioridade)
        if margem is not None and margem < 0:
            pontos.append(f"Operação com margem negativa de {fmt(abs(margem))}. Revise os custos.")
            seen.add("aumento_custo")  # suprime variação se margem já é negativa

        # 2. Variação de custo no último período
        if "aumento_custo" not in seen and len(serie) >= 2 and serie[-2].total > 0:
            variacao = (serie[-1].total - serie[-2].total) / serie[-2].total * 100
            if variacao > 20:
                pontos.append(f"Custos aumentaram {variacao:.1f}% entre {serie[-2].periodo} e {serie[-1].periodo}.")
                seen.add("aumento_custo")
            elif variacao < -10:
                pontos.append(f"Custos reduziram {abs(variacao):.1f}% no último período — boa evolução.")
                seen.add("aumento_custo")

        # 3. Categoria dominante
        if cat_dominante and "cat_dominante" not in seen:
            pontos.append(f"A categoria {cat_dominante} representa a maior concentração de custos.")
            seen.add("cat_dominante")

        proximas: list[str] = []
        seen_rec: set[str] = set()
        for r in recomendacoes:
            if r.tipo not in seen_rec:
                proximas.append(r.mensagem)
                seen_rec.add(r.tipo)
        if not proximas:
            proximas = ["Revisar custos por categoria", "Comparar cenários econômicos", "Acompanhar evolução mensal"]

        return ResumoInteligente(
            titulo="Resumo financeiro da safra",
            resumo=" ".join(partes_resumo),
            pontos_atencao=pontos[:3],
            proximas_acoes=proximas[:3],
        )

    async def gerar_plano_acao(self, safra_id: uuid.UUID) -> list[ItemPlanoAcao]:
        """Transforma recomendações em itens de plano de ação priorizados.

        Reutiliza gerar_recomendacoes() — sem recalcular regras.
        """
        MAPA: dict[str, dict] = {
            "REVISAR_CUSTOS": {
                "titulo": "Revisar custos e cenários da safra",
                "descricao": "A margem atual está negativa. Revise os custos operacionais e compare os cenários econômicos.",
                "prioridade": "ALTA",
            },
            "ANALISAR_INSUMOS": {
                "titulo": "Analisar custos de insumos",
                "descricao": "Os insumos representam a maior parte dos custos da safra. Avalie oportunidades de redução.",
                "prioridade": "MEDIA",
            },
            "VER_EVOLUCAO": {
                "titulo": "Verificar evolução mensal dos custos",
                "descricao": "Os custos tiveram variação significativa no último período. Acompanhe a tendência.",
                "prioridade": "MEDIA",
            },
        }

        recomendacoes = await self.gerar_recomendacoes(safra_id)
        plano: list[ItemPlanoAcao] = []
        seen: set[str] = set()

        for rec in recomendacoes:
            if rec.tipo in seen or rec.tipo not in MAPA:
                continue
            seen.add(rec.tipo)
            meta = MAPA[rec.tipo]
            plano.append(ItemPlanoAcao(
                id=rec.tipo.lower(),
                tipo=rec.tipo.upper(),
                titulo=meta["titulo"],
                descricao=meta["descricao"],
                prioridade=meta["prioridade"],
                status="PENDENTE",
                rota=rec.rota,
            ))

        return plano

    async def gerar_dre(self, safra_id: uuid.UUID) -> DREOperacional:
        from financeiro.schemas.lancamento_schema import DREOperacional, CategoriaBreakdown
        
        # DRE operacional/financeira legada:
        # continua baseada somente em LancamentoFinanceiro para compatibilidade.
        # A DRE agrícola v1 consolidada é provida separadamente por agricola.dre.service.

        # Valida safra
        safra = await self.session.get(Safra, safra_id)
        if not safra or safra.tenant_id != self.tenant_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Safra indisponível ou não encontrada.")

        # Soma Receitas por categoria
        stmt_rec = select(
            LancamentoFinanceiro.categoria,
            func.sum(LancamentoFinanceiro.valor).label("total")
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "RECEITA"
        )).group_by(LancamentoFinanceiro.categoria)
        
        rec_rows = (await self.session.execute(stmt_rec)).fetchall()
        breakdown_rec = [CategoriaBreakdown(nome=r[0], valor=float(r[1])) for r in rec_rows]
        total_rec = sum(r.valor for r in breakdown_rec)

        # Soma Custos por categoria
        stmt_custo = select(
            LancamentoFinanceiro.categoria,
            func.sum(LancamentoFinanceiro.valor).label("total")
        ).where(and_(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.safra_id == safra_id,
            LancamentoFinanceiro.tipo == "CUSTO"
        )).group_by(LancamentoFinanceiro.categoria)
        
        custo_rows = (await self.session.execute(stmt_custo)).fetchall()
        breakdown_custo = [CategoriaBreakdown(nome=r[0], valor=float(r[1])) for r in custo_rows]
        total_custo = sum(r.valor for r in breakdown_custo)

        resultado = total_rec - total_custo
        margem = (resultado / total_rec * 100) if total_rec > 0 else 0

        return DREOperacional(
            receita_bruta=total_rec,
            custos_operacionais=total_custo,
            resultado_operacional=resultado,
            margem_percentual=margem,
            breakdown_receitas=breakdown_rec,
            breakdown_custos=breakdown_custo
        )

    async def simular_dre(
        self, 
        safra_id: uuid.UUID, 
        receita_pct: float, 
        custos_pct: float
    ) -> "SimulacaoDREResponse":
        from financeiro.schemas.lancamento_schema import SimulacaoDREResponse
        
        # Simulação legada da mesma DRE operacional/financeira.
        # Não substitui a DRE agrícola v1 e não altera a precedência econômica oficial.

        # Obtém dados reais
        dre_real = await self.gerar_dre(safra_id)
        
        # Aplica ajustes
        rec_sim = dre_real.receita_bruta * (1 + receita_pct / 100)
        custo_sim = dre_real.custos_operacionais * (1 + custos_pct / 100)
        
        # Recalcula
        res_sim = rec_sim - custo_sim
        margem_sim = (res_sim / rec_sim * 100) if rec_sim > 0 else 0
        
        # Variações
        var_abs = res_sim - dre_real.resultado_operacional
        var_pct = (var_abs / abs(dre_real.resultado_operacional) * 100) if dre_real.resultado_operacional != 0 else 0
        
        return SimulacaoDREResponse(
            receita_real=dre_real.receita_bruta,
            custos_real=dre_real.custos_operacionais,
            resultado_real=dre_real.resultado_operacional,
            margem_real=dre_real.margem_percentual,
            receita_simulada=rec_sim,
            custos_simulados=custo_sim,
            resultado_simulado=res_sim,
            margem_simulada=margem_sim,
            variacao_resultado=var_abs,
            variacao_resultado_percentual=var_pct
        )
