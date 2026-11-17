from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.caderno.models import VisitaTecnica
from agricola.custos.models import CostAllocation
from agricola.safras.models import Safra
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from core.models.maturidade import MaturidadeSnapshot
from core.models.plano_acao import PlanoAcaoGerencial
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.lancamento import LancamentoFinanceiro
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.producao.models import ProducaoLeite


class MaturidadeService:
    """Serviço determinístico de cálculo do Score Consolidado de Maturidade da Fazenda (0–100)."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        unidade_produtiva_id: Optional[UUID] = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.unidade_produtiva_id = unidade_produtiva_id

    async def calcular_e_registrar(self, persistir_snapshot: bool = True) -> dict:
        """Calcula os 4 pilares de maturidade, persiste snapshot mensal e retorna evolução.

        Args:
            persistir_snapshot: Quando True, grava/atualiza o snapshot da competência atual.

        Returns:
            dict: Score geral, notas por pilar, tendência vs mês anterior e pontos de melhoria.
        """
        p_operacional = await self._calcular_pilar_operacional()
        p_agro_zoo = await self._calcular_pilar_agronomico_zootecnico()
        p_economico = await self._calcular_pilar_economico()
        p_financeiro = await self._calcular_pilar_financeiro()

        score_geral = round((p_operacional + p_agro_zoo + p_economico + p_financeiro) / 4.0, 1)
        competencia = date.today().strftime("%Y-%m")
        tendencia = await self._obter_tendencia_anterior(competencia, score_geral)

        if persistir_snapshot:
            await self._salvar_snapshot(
                competencia,
                score_geral,
                p_operacional,
                p_agro_zoo,
                p_economico,
                p_financeiro,
            )

        pilares = [
            {"chave": "operacional", "nome": "Operacional", "score": p_operacional, "href": "/dashboard/campo"},
            {
                "chave": "agronomico_zootecnico",
                "nome": "Agronômico / Zootécnico",
                "score": p_agro_zoo,
                "href": "/agricola",
            },
            {"chave": "economico", "nome": "Econômico", "score": p_economico, "href": "/dashboard/planos-acao"},
            {"chave": "financeiro", "nome": "Financeiro", "score": p_financeiro, "href": "/dashboard/financeiro"},
        ]
        pontos_melhoria = [
            {
                "pilar": p["nome"],
                "score": p["score"],
                "recomendacao": self._recomendacao_para_pilar(p["chave"]),
                "href": p["href"],
            }
            for p in pilares
            if p["score"] < 70.0
        ]

        return {
            "competencia": competencia,
            "unidade_produtiva_id": str(self.unidade_produtiva_id) if self.unidade_produtiva_id else None,
            "score_geral": score_geral,
            "tendencia_mes_anterior": tendencia,
            "pilares": pilares,
            "pontos_melhoria": pontos_melhoria,
        }

    async def _calcular_pilar_operacional(self) -> float:
        """Avalia cadastro territorial (unidades/áreas) e taxa de execução de tarefas de campo."""
        unidades = int((await self.session.execute(
            select(func.count(UnidadeProdutiva.id)).where(UnidadeProdutiva.tenant_id == self.tenant_id)
        )).scalar_one() or 0)
        areas_stmt = select(func.count(AreaRural.id)).where(
            AreaRural.tenant_id == self.tenant_id, AreaRural.ativo.is_(True)
        )
        if self.unidade_produtiva_id:
            areas_stmt = areas_stmt.where(AreaRural.unidade_produtiva_id == self.unidade_produtiva_id)
        areas = int((await self.session.execute(areas_stmt)).scalar_one() or 0)

        base_cadastro = 30.0 if unidades > 0 else 0.0
        base_areas = 30.0 if areas > 0 else 0.0

        tarefas_stmt = select(func.count(TarefaCampo.id)).where(TarefaCampo.tenant_id == self.tenant_id)
        concluidas_stmt = select(func.count(TarefaCampo.id)).where(
            TarefaCampo.tenant_id == self.tenant_id, TarefaCampo.status_execucao == "CONCLUIDA"
        )
        if self.unidade_produtiva_id:
            tarefas_stmt = tarefas_stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)
            concluidas_stmt = concluidas_stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)

        total_tarefas = int((await self.session.execute(tarefas_stmt)).scalar_one() or 0)
        concluidas = int((await self.session.execute(concluidas_stmt)).scalar_one() or 0)
        if total_tarefas == 0:
            score_exec = 20.0 if areas > 0 else 0.0
        else:
            score_exec = round((concluidas / total_tarefas) * 40.0, 1)
        return round(min(100.0, base_cadastro + base_areas + score_exec), 1)

    async def _calcular_pilar_agronomico_zootecnico(self) -> float:
        """Avalia presença e acompanhamento de safras agrícolas e/ou rebanho pecuário."""
        safras = int((await self.session.execute(
            select(func.count(Safra.id)).where(Safra.tenant_id == self.tenant_id)
        )).scalar_one() or 0)
        visitas = int((await self.session.execute(
            select(func.count(VisitaTecnica.id)).where(VisitaTecnica.tenant_id == self.tenant_id)
        )).scalar_one() or 0)

        lotes_stmt = select(func.count(LoteAnimal.id)).where(
            LoteAnimal.tenant_id == self.tenant_id, LoteAnimal.ativo.is_(True)
        )
        animais_stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id, Animal.status == "ATIVO"
        )
        if self.unidade_produtiva_id:
            lotes_stmt = lotes_stmt.where(LoteAnimal.unidade_produtiva_id == self.unidade_produtiva_id)
            animais_stmt = animais_stmt.where(Animal.unidade_produtiva_id == self.unidade_produtiva_id)

        lotes = int((await self.session.execute(lotes_stmt)).scalar_one() or 0)
        animais = int((await self.session.execute(animais_stmt)).scalar_one() or 0)
        pesagens = int((await self.session.execute(
            select(func.count(EventoAnimal.id)).where(
                EventoAnimal.tenant_id == self.tenant_id, EventoAnimal.tipo == "PESAGEM"
            )
        )).scalar_one() or 0)

        score_agro = (60.0 if safras > 0 else 0.0) + (40.0 if visitas > 0 else 0.0)
        score_pec = (50.0 if (lotes > 0 or animais > 0) else 0.0) + (50.0 if pesagens > 0 else 0.0)

        if safras > 0 and (lotes > 0 or animais > 0):
            return round((score_agro + score_pec) / 2.0, 1)
        if safras > 0:
            return round(score_agro, 1)
        if lotes > 0 or animais > 0:
            return round(score_pec, 1)
        return 0.0

    async def _calcular_pilar_economico(self) -> float:
        """Avalia alocação de custos, produção econômica e execução de planos de ação."""
        alocacoes = int((await self.session.execute(
            select(func.count(CostAllocation.id)).where(CostAllocation.tenant_id == self.tenant_id)
        )).scalar_one() or 0)
        leite = int((await self.session.execute(
            select(func.count(ProducaoLeite.id)).where(ProducaoLeite.tenant_id == self.tenant_id)
        )).scalar_one() or 0)
        planos_total = int((await self.session.execute(
            select(func.count(PlanoAcaoGerencial.id)).where(PlanoAcaoGerencial.tenant_id == self.tenant_id)
        )).scalar_one() or 0)
        planos_concluidos = int((await self.session.execute(
            select(func.count(PlanoAcaoGerencial.id)).where(
                PlanoAcaoGerencial.tenant_id == self.tenant_id,
                PlanoAcaoGerencial.status == "CONCLUIDO",
            )
        )).scalar_one() or 0)

        base_custos = 55.0 if (alocacoes > 0 or leite > 0) else 0.0
        if planos_total == 0:
            base_planos = 25.0 if base_custos > 0 else 0.0
        else:
            base_planos = 20.0 + round((planos_concluidos / planos_total) * 25.0, 1)
        return round(min(100.0, base_custos + base_planos), 1)

    async def _calcular_pilar_financeiro(self) -> float:
        """Avalia registros financeiros (custos e receitas) lançados no período."""
        custos = int((await self.session.execute(
            select(func.count(LancamentoFinanceiro.id)).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.tipo == "CUSTO",
            )
        )).scalar_one() or 0)
        receitas = int((await self.session.execute(
            select(func.count(LancamentoFinanceiro.id)).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.tipo == "RECEITA",
            )
        )).scalar_one() or 0)

        score = 0.0
        if custos > 0:
            score += 50.0
        if receitas > 0:
            score += 50.0
        return score

    async def _obter_tendencia_anterior(self, competencia_atual: str, score_atual: float) -> Optional[float]:
        cond_unidade = (
            MaturidadeSnapshot.unidade_produtiva_id == self.unidade_produtiva_id
            if self.unidade_produtiva_id is not None
            else MaturidadeSnapshot.unidade_produtiva_id.is_(None)
        )
        stmt = (
            select(MaturidadeSnapshot.score_geral)
            .where(
                MaturidadeSnapshot.tenant_id == self.tenant_id,
                cond_unidade,
                MaturidadeSnapshot.competencia < competencia_atual,
            )
            .order_by(MaturidadeSnapshot.competencia.desc())
            .limit(1)
        )
        anterior = (await self.session.execute(stmt)).scalar_one_or_none()
        if anterior is None:
            return None
        return round(score_atual - float(anterior), 1)

    async def _salvar_snapshot(
        self,
        competencia: str,
        score_geral: float,
        p_op: float,
        p_agro: float,
        p_eco: float,
        p_fin: float,
    ) -> None:
        cond_unidade = (
            MaturidadeSnapshot.unidade_produtiva_id == self.unidade_produtiva_id
            if self.unidade_produtiva_id is not None
            else MaturidadeSnapshot.unidade_produtiva_id.is_(None)
        )
        existente = await self.session.scalar(
            select(MaturidadeSnapshot).where(
                and_(
                    MaturidadeSnapshot.tenant_id == self.tenant_id,
                    cond_unidade,
                    MaturidadeSnapshot.competencia == competencia,
                )
            )
        )
        if existente:
            existente.score_geral = score_geral
            existente.pilar_operacional = p_op
            existente.pilar_agronomico_zootecnico = p_agro
            existente.pilar_economico = p_eco
            existente.pilar_financeiro = p_fin
        else:
            self.session.add(
                MaturidadeSnapshot(
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=self.unidade_produtiva_id,
                    competencia=competencia,
                    score_geral=score_geral,
                    pilar_operacional=p_op,
                    pilar_agronomico_zootecnico=p_agro,
                    pilar_economico=p_eco,
                    pilar_financeiro=p_fin,
                    detalhes={},
                )
            )
        await self.session.flush()

    def _recomendacao_para_pilar(self, chave: str) -> str:
        mapa = {
            "operacional": "Cadastre áreas rurais e conclua as tarefas de campo em aberto.",
            "agronomico_zootecnico": "Registre safras/visitas técnicas ou pesagens periódicas do rebanho.",
            "economico": "Aloque custos operacionais e conclua os planos de ação gerenciais.",
            "financeiro": "Mantenha receitas e custos lançados para acompanhar a margem real.",
        }
        return mapa.get(chave, "Atualize os registros deste pilar.")
