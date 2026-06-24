from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.schemas.lote_resumo_sanitario_schema import (
    LoteResumoSanitarioHistoricoItem,
    LoteResumoSanitarioProdutoItem,
    LoteResumoSanitarioResponse,
)
from campo.models import TarefaCampo
from core.cadastros.produtos.models import Produto
from operacional.models.estoque import EstoqueMovimento
from agricola.custos.models import CostAllocation


class LoteResumoSanitarioService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def resumir(self, lote_id: uuid.UUID) -> LoteResumoSanitarioResponse:
        lote = await self._buscar_lote(lote_id)
        quantidade_animais = await self._contar_animais_ativos(lote_id)
        linhas = await self._buscar_linhas_vacinacao(lote_id)
        custos = await self._buscar_custos_vacinacao(lote_id)
        return self._montar_resumo(lote, quantidade_animais, linhas, custos)

    async def _buscar_lote(self, lote_id: uuid.UUID) -> LoteAnimal:
        lote = await self.session.scalar(
            select(LoteAnimal).where(LoteAnimal.id == lote_id, LoteAnimal.tenant_id == self.tenant_id)
        )
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado")
        return lote

    async def _contar_animais_ativos(self, lote_id: uuid.UUID) -> int:
        stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _buscar_linhas_vacinacao(self, lote_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(
                TarefaCampo.id.label("tarefa_campo_id"),
                TarefaCampo.concluida_em.label("concluida_em"),
                EventoAnimal.produto_id.label("produto_id"),
                Produto.nome.label("produto_nome"),
                func.count(EventoAnimal.id).label("quantidade_eventos"),
            )
            .join(
                EventoAnimal,
                and_(
                    EventoAnimal.tarefa_campo_id == TarefaCampo.id,
                    EventoAnimal.tenant_id == self.tenant_id,
                    EventoAnimal.tipo == "VACINACAO",
                ),
            )
            .join(
                Animal,
                and_(
                    Animal.id == EventoAnimal.animal_id,
                    Animal.tenant_id == self.tenant_id,
                    Animal.lote_id == lote_id,
                    Animal.status == "ATIVO",
                ),
            )
            .join(Produto, Produto.id == EventoAnimal.produto_id)
            .where(
                TarefaCampo.tenant_id == self.tenant_id,
                TarefaCampo.lote_id == lote_id,
                TarefaCampo.module == "pecuaria",
                TarefaCampo.type == "VACINACAO",
                TarefaCampo.status_execucao == "CONCLUIDA",
            )
            .group_by(TarefaCampo.id, TarefaCampo.concluida_em, EventoAnimal.produto_id, Produto.nome)
            .order_by(desc(TarefaCampo.concluida_em))
        )
        rows = await self.session.execute(stmt)
        return [dict(row._mapping) for row in rows.all()]

    async def _buscar_custos_vacinacao(self, lote_id: uuid.UUID) -> dict[tuple[uuid.UUID, uuid.UUID], float]:
        stmt = (
            select(
                TarefaCampo.id.label("tarefa_campo_id"),
                EstoqueMovimento.produto_id.label("produto_id"),
                func.coalesce(func.sum(CostAllocation.amount), 0).label("custo_total"),
            )
            .join(
                EstoqueMovimento,
                and_(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.origem == "PECUARIA_VACINACAO",
                    EstoqueMovimento.origem_id == TarefaCampo.id,
                ),
            )
            .outerjoin(
                CostAllocation,
                and_(
                    CostAllocation.tenant_id == self.tenant_id,
                    CostAllocation.source == "PECUARIA_VACINACAO",
                    CostAllocation.source_id == TarefaCampo.id,
                    CostAllocation.inventory_movement_id == EstoqueMovimento.id,
                    CostAllocation.cost_category == "SANITARIO",
                ),
            )
            .where(
                TarefaCampo.tenant_id == self.tenant_id,
                TarefaCampo.lote_id == lote_id,
                TarefaCampo.module == "pecuaria",
                TarefaCampo.type == "VACINACAO",
                TarefaCampo.status_execucao == "CONCLUIDA",
            )
            .group_by(TarefaCampo.id, EstoqueMovimento.produto_id)
        )
        rows = await self.session.execute(stmt)
        custos: dict[tuple[uuid.UUID, uuid.UUID], float] = {}
        for row in rows.all():
            custos[(row.tarefa_campo_id, row.produto_id)] = float(row.custo_total or 0)
        return custos

    def _montar_resumo(
        self,
        lote: LoteAnimal,
        quantidade_animais: int,
        linhas: list[dict],
        custos: dict[tuple[uuid.UUID, uuid.UUID], float],
    ) -> LoteResumoSanitarioResponse:
        produtos: dict[uuid.UUID, dict[str, object]] = {}
        historico: list[LoteResumoSanitarioHistoricoItem] = []
        custo_total = 0.0
        ultima_vacinacao: date | None = None
        vacinacoes = {row["tarefa_campo_id"] for row in linhas}

        for row in linhas:
            custo = custos.get((row["tarefa_campo_id"], row["produto_id"]), 0.0)
            data_vacinacao = row["concluida_em"].date() if row["concluida_em"] else None
            if data_vacinacao and (ultima_vacinacao is None or data_vacinacao > ultima_vacinacao):
                ultima_vacinacao = data_vacinacao
            custo_total += custo
            self._acumular_produto(produtos, row, custo)
            historico.append(
                LoteResumoSanitarioHistoricoItem(
                    tarefa_campo_id=row["tarefa_campo_id"],
                    produto_id=row["produto_id"],
                    produto_nome=row["produto_nome"],
                    data_vacinacao=data_vacinacao,
                    quantidade_eventos=int(row["quantidade_eventos"]),
                    custo_total=custo,
                )
            )

        return LoteResumoSanitarioResponse(
            lote_id=lote.id,
            nome_lote=lote.identificacao,
            quantidade_animais=quantidade_animais,
            eventos_sanitarios=sum(item.quantidade_eventos for item in historico),
            vacinacoes=len(vacinacoes),
            custo_sanitario_total=custo_total,
            custo_sanitario_por_animal=(custo_total / quantidade_animais) if quantidade_animais else 0.0,
            ultima_vacinacao=ultima_vacinacao,
            produto_mais_usado=self._produto_mais_usado(produtos),
            produtos_utilizados=[
                LoteResumoSanitarioProdutoItem(
                    produto_id=produto_id,
                    nome=str(dados["nome"]),
                    quantidade_eventos=int(dados["quantidade_eventos"]),
                    custo_total=float(dados["custo_total"]),
                )
                for produto_id, dados in produtos.items()
            ],
            historico_sanitario_resumido=historico,
        )

    def _produto_mais_usado(
        self,
        produtos: dict[uuid.UUID, dict[str, object]],
    ) -> LoteResumoSanitarioProdutoItem | None:
        if not produtos:
            return None
        produto_id, dados = sorted(
            produtos.items(),
            key=lambda item: (
                -int(item[1]["quantidade_eventos"]),
                -float(item[1]["custo_total"]),
                str(item[1]["nome"]),
            ),
        )[0]
        return LoteResumoSanitarioProdutoItem(
            produto_id=produto_id,
            nome=str(dados["nome"]),
            quantidade_eventos=int(dados["quantidade_eventos"]),
            custo_total=float(dados["custo_total"]),
        )

    def _acumular_produto(self, produtos: dict[uuid.UUID, dict[str, object]], row: dict, custo: float) -> None:
        produto_id = row["produto_id"]
        atual = produtos.get(produto_id)
        if not atual:
            produtos[produto_id] = {
                "nome": row["produto_nome"],
                "quantidade_eventos": int(row["quantidade_eventos"]),
                "custo_total": float(custo),
            }
            return
        atual["quantidade_eventos"] = int(atual["quantidade_eventos"]) + int(row["quantidade_eventos"])
        atual["custo_total"] = float(atual["custo_total"]) + float(custo)
