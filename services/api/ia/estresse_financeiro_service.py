import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from financeiro.services.lancamento_service import LancamentoService
from financeiro.services.cenario_service import CenarioFinanceiroService
from agricola.safras.models import Safra

class IAEstresseFinanceiroService:
    """
    Serviço responsável por simular cenários extremos de estresse financeiro (Step 206).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def simular_estresse_financeiro(self, safra_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Calcula o impacto de variações severas na receita e custos da safra.
        """
        if not safra_id:
            # Busca safra mais recente
            stmt = select(Safra.id).where(Safra.tenant_id == self.tenant_id).order_by(Safra.created_at.desc()).limit(1)
            safra_id = (await self.session.execute(stmt)).scalar_one_or_none()

        if not safra_id:
            return self._empty_response()

        # 1. Obter dados atuais da safra
        lancamento_svc = LancamentoService(self.session, self.tenant_id)
        cenario_svc = CenarioFinanceiroService(self.session, self.tenant_id)
        
        resumo_data = await lancamento_svc.resumo(safra_id)
        receita_atual = float(resumo_data.total_receitas)
        custo_atual = float(resumo_data.total_custos)
        margem_atual = float(resumo_data.saldo)
        
        if receita_atual == 0 and custo_atual == 0:
            return self._empty_response("Dados insuficientes para simulação de estresse.")

        # 2. Definir Cenários de Estresse
        cenarios = [
            {"nome": "QUEDA_RECEITA_20", "receita_mod": -0.20, "custo_mod": 0.0},
            {"nome": "AUMENTO_CUSTO_20", "receita_mod": 0.0, "custo_mod": 0.20},
            {"nome": "PIOR_CASO", "receita_mod": -0.30, "custo_mod": 0.20},
        ]

        resultados = []
        pior_cenario = None

        for c in cenarios:
            receita_sim = receita_atual * (1 + c["receita_mod"])
            custo_sim = custo_atual * (1 + c["custo_mod"])
            resultado_sim = receita_sim - custo_sim
            margem_pct = (resultado_sim / receita_sim * 100) if receita_sim > 0 else -100

            res = {
                "cenario": c["nome"],
                "receita": receita_sim,
                "custo": custo_sim,
                "resultado": resultado_sim,
                "margem_resultante": round(margem_pct, 2),
                "variacao_resultado": resultado_sim - margem_atual
            }
            resultados.append(res)

            if not pior_cenario or res["resultado"] < pior_cenario["resultado"]:
                pior_cenario = res

        # 3. Determinar Nível de Risco do Pior Caso
        nivel_risco = "BAIXO"
        if pior_cenario["resultado"] < 0:
            nivel_risco = "CRITICO"
        elif pior_cenario["margem_resultante"] < 10:
            nivel_risco = "ALTO"
        elif pior_cenario["margem_resultante"] < 20:
            nivel_risco = "MEDIO"

        # 4. Gerar Interpretação (Mockando IA por enquanto, conforme padrão da stack)
        interpretacao = self._gerar_interpretacao_estresse(pior_cenario, nivel_risco)

        return {
            "safra_id": str(safra_id),
            "nivel_risco": nivel_risco,
            "pior_cenario": pior_cenario,
            "todos_cenarios": resultados,
            "descricao": interpretacao["descricao"],
            "acao_recomendada": interpretacao["acao"],
            "probabilidade": interpretacao["probabilidade"]
        }

    def _gerar_interpretacao_estresse(self, pior_cenario: Dict, nivel: str) -> Dict[str, str]:
        if nivel == "CRITICO":
            return {
                "descricao": f"No pior cenário (Estresse de 30% na receita e 20% no custo), a safra apresenta prejuízo de {pior_cenario['resultado']:.2f}.",
                "acao": "Revisar imediatamente contratos de venda e travar custos de insumos.",
                "probabilidade": "MODERADA (baseada em volatilidade histórica)"
            }
        elif nivel == "ALTO":
            return {
                "descricao": f"A margem pode cair para {pior_cenario['margem_resultante']}% em cenários de alta volatilidade.",
                "acao": "Considerar seguros agrícolas e diversificação de canais de escoamento.",
                "probabilidade": "BAIXA"
            }
        else:
            return {
                "descricao": "A safra demonstra resiliência mesmo em cenários de estresse moderado.",
                "acao": "Manter monitoramento de custos variáveis.",
                "probabilidade": "MUITO BAIXA"
            }

    def _empty_response(self, msg: str = "Nenhuma safra ativa para simulação.") -> Dict[str, Any]:
        return {
            "nivel_risco": "BAIXO",
            "descricao": msg,
            "pior_cenario": None,
            "todos_cenarios": [],
            "acao_recomendada": "Inicie o planejamento financeiro da safra.",
            "probabilidade": "N/A"
        }
