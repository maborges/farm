import uuid
from datetime import timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from atividades.schemas import AtividadeItem


def _fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class AtividadesService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar(self, safra_id: uuid.UUID, limit: int = 20) -> list[AtividadeItem]:
        itens: list[AtividadeItem] = []

        # ── 1. Lançamentos financeiros ─────────────────────────────────────────
        stmt = text("""
            SELECT id, descricao, valor, categoria, tipo, created_at
            FROM financeiro_lancamentos
            WHERE tenant_id = :tenant_id
              AND safra_id = :safra_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        rows = (await self.session.execute(stmt, {
            "tenant_id": self.tenant_id, "safra_id": safra_id, "limit": limit
        })).fetchall()

        for r in rows:
            tipo_label = "RECEITA_LANCADA" if r.tipo == "RECEITA" else "CUSTO_LANCADO"
            itens.append(AtividadeItem(
                id=f"lanc-{r.id}",
                tipo=tipo_label,
                descricao=f"{_fmt_brl(float(r.valor))} registrado em {r.categoria.replace('_', ' ').title()}",
                data=r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc),
                origem="financeiro",
                origem_id=str(r.id),
                meta={"categoria": r.categoria, "valor": float(r.valor)},
            ))

        # ── 2. Ações do plano concluídas ───────────────────────────────────────
        stmt2 = text("""
            SELECT id, titulo, concluido_at
            FROM financeiro_plano_acoes
            WHERE tenant_id = :tenant_id
              AND safra_id = :safra_id
              AND status = 'CONCLUIDA'
              AND concluido_at IS NOT NULL
            ORDER BY concluido_at DESC
            LIMIT :limit
        """)
        rows2 = (await self.session.execute(stmt2, {
            "tenant_id": self.tenant_id, "safra_id": safra_id, "limit": limit
        })).fetchall()

        for r in rows2:
            itens.append(AtividadeItem(
                id=f"acao-{r.id}",
                tipo="ACAO_CONCLUIDA",
                descricao=f"Ação concluída: {r.titulo}",
                data=r.concluido_at if r.concluido_at.tzinfo else r.concluido_at.replace(tzinfo=timezone.utc),
                origem="plano_acao",
                origem_id=str(r.id),
            ))

        # ── 3. Saídas de estoque vinculadas à safra (via lancamentos) ──────────
        stmt3 = text("""
            SELECT em.id, em.data_movimento, em.custo_total, em.tipo_movimento
            FROM estoque_movimentos em
            JOIN financeiro_lancamentos fl
              ON fl.tenant_id = em.tenant_id
             AND fl.safra_id = :safra_id
             AND em.origem_id = fl.id
            WHERE em.tenant_id = :tenant_id
              AND em.tipo_movimento = 'SAIDA'
            ORDER BY em.data_movimento DESC
            LIMIT :limit
        """)
        rows3 = (await self.session.execute(stmt3, {
            "tenant_id": self.tenant_id, "safra_id": safra_id, "limit": limit
        })).fetchall()

        for r in rows3:
            custo = float(r.custo_total) if r.custo_total else 0
            itens.append(AtividadeItem(
                id=f"mov-{r.id}",
                tipo="SAIDA_ESTOQUE",
                descricao=f"Saída de insumo registrada — custo {_fmt_brl(custo)}",
                data=r.data_movimento if r.data_movimento.tzinfo else r.data_movimento.replace(tzinfo=timezone.utc),
                origem="estoque",
                origem_id=str(r.id),
                meta={"custo_total": custo},
            ))

        # ── Ordenar por data desc, limitar ─────────────────────────────────────
        itens.sort(key=lambda x: x.data, reverse=True)
        return itens[:limit]
