import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger
from financeiro.models.cenario import FinanceiroSafraCenario
from operacional.models.compras import PedidoCompra
from financeiro.services.lancamento_service import LancamentoService

class PerformanceService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def _resposta_vazia() -> dict:
        return {
            "total_decisoes": 0,
            "economia_total": 0.0,
            "melhor_decisao": {
                "safra": "Nenhuma registrada",
                "ganho": 0.0,
            },
            "taxa_sucesso": 0.0,
            "ranking": "TOP 50%",
            "nivel": "INICIANTE",
        }

    async def obter_performance_usuario(self) -> dict:
        """Calcula métricas de performance e gamificação do usuário."""
        try:
            economia_total = 0.0
            cenarios_escolhidos = []

            try:
                stmt_economia = select(func.sum(PedidoCompra.economia_absoluta)).where(
                    PedidoCompra.tenant_id == self.tenant_id
                )
                res_economia = await self.session.execute(stmt_economia)
                economia_total = float(res_economia.scalar() or 0.0)
            except Exception:
                logger.exception("Erro ao calcular economia total de compras para performance do usuário.")

            try:
                stmt_decisoes = select(FinanceiroSafraCenario).where(
                    and_(
                        FinanceiroSafraCenario.tenant_id == self.tenant_id,
                        FinanceiroSafraCenario.escolhido.is_(True)
                    )
                ).order_by(FinanceiroSafraCenario.escolhido_at.desc())

                res_decisoes = await self.session.execute(stmt_decisoes)
                cenarios_escolhidos = res_decisoes.scalars().all()
            except Exception:
                logger.exception("Erro ao listar cenários escolhidos para performance do usuário.")

            total_decisoes = len(cenarios_escolhidos)
            acertos = 0
            melhor_ganho = 0.0
            melhor_decisao_nome = "Nenhuma registrada"

            svc_lancamento = LancamentoService(self.session, self.tenant_id)

            for c in cenarios_escolhidos:
                try:
                    dre = await svc_lancamento.gerar_dre(c.safra_id)
                    if isinstance(dre, dict):
                        resultado_real = float(dre.get("resultado_operacional", 0.0))
                    else:
                        resultado_real = float(getattr(dre, "resultado_operacional"))
                    resultado_simulado = float(c.resultado_simulado)

                    desvio_abs = abs(resultado_real - resultado_simulado)
                    projecao = abs(resultado_simulado)
                    desvio_pct = (desvio_abs / projecao * 100) if projecao != 0 else 0

                    if desvio_pct <= 10:
                        acertos += 1

                    if resultado_real > melhor_ganho:
                        melhor_ganho = resultado_real
                        melhor_decisao_nome = f"Planejamento {c.nome}"
                except Exception:
                    logger.exception("Erro ao analisar cenário {} na performance do usuário.", getattr(c, "id", None))
                    continue

            try:
                stmt_melhor_compra = select(PedidoCompra).where(
                    PedidoCompra.tenant_id == self.tenant_id
                ).order_by(PedidoCompra.economia_absoluta.desc()).limit(1)

                res_compra = await self.session.execute(stmt_melhor_compra)
                melhor_compra = res_compra.scalar_one_or_none()

                melhor_compra_valor = float(melhor_compra.economia_absoluta or 0.0) if melhor_compra else 0.0
                if melhor_compra and melhor_compra_valor > melhor_ganho:
                    melhor_ganho = melhor_compra_valor
                    melhor_decisao_nome = f"Negociação: {melhor_compra.fornecedor_nome}"
            except Exception:
                logger.exception("Erro ao calcular melhor decisão de compras para performance do usuário.")

            taxa_sucesso = (acertos / total_decisoes * 100) if total_decisoes > 0 else 0
            score_ficticio = (total_decisoes * 1000) + economia_total

            if score_ficticio >= 50000:
                ranking = "TOP 1%"
                nivel = "LENDÁRIO"
            elif score_ficticio >= 20000:
                ranking = "TOP 5%"
                nivel = "EXPERIENTE"
            elif score_ficticio >= 5000:
                ranking = "TOP 20%"
                nivel = "PROFISSIONAL"
            else:
                ranking = "TOP 50%"
                nivel = "INICIANTE"

            return {
                "total_decisoes": total_decisoes,
                "economia_total": round(economia_total, 2),
                "melhor_decisao": {
                    "safra": melhor_decisao_nome,
                    "ganho": round(float(melhor_ganho), 2)
                },
                "taxa_sucesso": round(taxa_sucesso, 1),
                "ranking": ranking,
                "nivel": nivel
            }
        except Exception:
            logger.exception("Erro inesperado ao calcular performance do usuário. Retornando fallback.")
            return self._resposta_vazia()
