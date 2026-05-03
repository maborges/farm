"""
Automações inteligentes — camada de regras simples acionadas manualmente.
Reutiliza PlanoAcaoService, NotificacaoService e LancamentoService sem duplicar lógica.
Registra cada execução em automacoes_execucoes e respeita automacoes_configuracoes.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from financeiro.services.lancamento_service import LancamentoService
from financeiro.models.plano_acao import PlanoAcaoItem
from notificacoes.service import NotificacaoService
from notificacoes.schemas import NotificacaoCreate
from automacoes.models import AutomacaoExecucao, AutomacaoConfiguracao

# Regras disponíveis com metadados para UI
REGRAS_DISPONIVEIS = {
    "MARGEM_NEGATIVA": {
        "titulo": "Margem negativa",
        "descricao": "Cria uma ação quando a margem da safra estiver negativa.",
    },
    "INSUMOS_DOMINANTE": {
        "titulo": "Insumos dominantes",
        "descricao": "Cria uma ação quando insumos forem a maior categoria de custo.",
    },
    "AUMENTO_CUSTO": {
        "titulo": "Aumento de custos",
        "descricao": "Envia uma notificação quando os custos mensais aumentarem mais de 20%.",
    },
}


@dataclass
class ResultadoAutomacao:
    acoes_criadas: int = 0
    notificacoes_criadas: int = 0
    mensagem: str = "Automações executadas com sucesso"
    detalhes: list[str] = field(default_factory=list)
    regras_disparadas: list[str] = field(default_factory=list)


FREQUENCIA_DELTAS: dict[str, timedelta | None] = {
    "MANUAL": None,
    "DIARIA": timedelta(days=1),
    "SEMANAL": timedelta(days=7),
    "MENSAL": timedelta(days=30),
}


def _calcular_proxima_execucao(frequencia: str | None) -> datetime | None:
    delta = FREQUENCIA_DELTAS.get(frequencia or "MANUAL")
    return datetime.now(timezone.utc) + delta if delta else None


@dataclass
class ConfiguracaoItem:
    regra: str
    titulo: str
    descricao: str
    ativa: bool = True
    frequencia: str = "MANUAL"
    proxima_execucao: datetime | None = None


class AutomacoesService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    # ── Configurações ──────────────────────────────────────────────────────────

    async def listar_configuracoes(self, safra_id: uuid.UUID | None = None) -> list[ConfiguracaoItem]:
        """Retorna todas as regras com seu estado (padrão: ativa=True)."""
        stmt = select(AutomacaoConfiguracao).where(
            AutomacaoConfiguracao.tenant_id == self.tenant_id,
            AutomacaoConfiguracao.safra_id == safra_id,
        )
        result = await self.session.execute(stmt)
        db_rows = {r.regra: r for r in result.scalars().all()}

        return [
            ConfiguracaoItem(
                regra=regra,
                titulo=meta["titulo"],
                descricao=meta["descricao"],
                ativa=db_rows[regra].ativa if regra in db_rows else True,
                frequencia=db_rows[regra].frequencia or "MANUAL" if regra in db_rows else "MANUAL",
                proxima_execucao=db_rows[regra].proxima_execucao if regra in db_rows else None,
            )
            for regra, meta in REGRAS_DISPONIVEIS.items()
        ]

    async def atualizar_configuracao(
        self, regra: str, ativa: bool, safra_id: uuid.UUID | None = None,
        frequencia: str | None = None,
    ) -> ConfiguracaoItem:
        if regra not in REGRAS_DISPONIVEIS:
            from core.exceptions import BusinessRuleError
            raise BusinessRuleError(f"Regra '{regra}' não existe")

        stmt = select(AutomacaoConfiguracao).where(
            AutomacaoConfiguracao.tenant_id == self.tenant_id,
            AutomacaoConfiguracao.safra_id == safra_id,
            AutomacaoConfiguracao.regra == regra,
        ).limit(1)
        result = await self.session.execute(stmt)
        cfg = result.scalar_one_or_none()

        freq = frequencia if frequencia in FREQUENCIA_DELTAS else (cfg.frequencia if cfg else "MANUAL")
        proxima = _calcular_proxima_execucao(freq)

        if cfg:
            cfg.ativa = ativa
            cfg.frequencia = freq
            cfg.proxima_execucao = proxima
            cfg.updated_at = datetime.now(timezone.utc)
        else:
            cfg = AutomacaoConfiguracao(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                safra_id=safra_id,
                regra=regra,
                ativa=ativa,
                frequencia=freq,
                proxima_execucao=proxima,
            )
            self.session.add(cfg)

        await self.session.flush()
        meta = REGRAS_DISPONIVEIS[regra]
        return ConfiguracaoItem(
            regra=regra, titulo=meta["titulo"], descricao=meta["descricao"],
            ativa=ativa, frequencia=freq, proxima_execucao=proxima,
        )

    async def _regras_ativas(self, safra_id: uuid.UUID | None = None) -> set[str]:
        configs = await self.listar_configuracoes(safra_id)
        return {c.regra for c in configs if c.ativa}

    # ── Execução ───────────────────────────────────────────────────────────────

    async def executar(self, safra_id: uuid.UUID, executado_por: uuid.UUID | None = None) -> ResultadoAutomacao:
        resultado = ResultadoAutomacao()
        status = "SUCESSO"

        try:
            regras_ativas = await self._regras_ativas(safra_id)

            lanc_svc = LancamentoService(self.session, self.tenant_id)
            notif_svc = NotificacaoService(self.session, self.tenant_id)

            serie = await lanc_svc.serie_temporal(safra_id)
            insight = await lanc_svc.insight_dashboard()

            margem = insight.cenario_margem
            categorias = {c.nome: c.valor for c in insight.categorias}

            # ── Regra 1: Margem negativa ───────────────────────────────────────
            if "MARGEM_NEGATIVA" in regras_ativas and margem is not None and margem < 0:
                criado = await self._criar_acao_sem_duplicar(
                    safra_id,
                    tipo="MARGEM_NEGATIVA",
                    titulo="Revisar margem negativa da safra",
                    descricao=f"A safra está operando com margem negativa de {abs(margem):.1f}%. Revise custos e receitas previstas no cenário.",
                    prioridade="ALTA",
                    rota="/agricola/safras",
                )
                if criado:
                    resultado.acoes_criadas += 1
                    resultado.regras_disparadas.append("MARGEM_NEGATIVA")
                    resultado.detalhes.append("Ação criada: margem negativa")

                notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                    tipo="ALERTA_FINANCEIRO",
                    titulo="Margem negativa detectada",
                    mensagem=f"A safra está com margem negativa de {abs(margem):.1f}%. Revise os cenários.",
                    nivel="DANGER",
                    origem="automacao",
                    origem_id=f"margem_negativa_{safra_id}",
                ))
                if notif:
                    resultado.notificacoes_criadas += 1
                    if "MARGEM_NEGATIVA" not in resultado.regras_disparadas:
                        resultado.regras_disparadas.append("MARGEM_NEGATIVA")

            # ── Regra 2: INSUMOS é a maior categoria ──────────────────────────
            if "INSUMOS_DOMINANTE" in regras_ativas and categorias:
                maior_cat = max(categorias, key=lambda k: categorias[k])
                if maior_cat == "INSUMOS" and categorias["INSUMOS"] > 0:
                    criado = await self._criar_acao_sem_duplicar(
                        safra_id,
                        tipo="REVISAR_INSUMOS_AUTO",
                        titulo="Revisar custos de insumos",
                        descricao="Insumos representam a maior categoria de custos da safra. Verifique oportunidades de redução.",
                        prioridade="MEDIA",
                        rota="/financeiro/lancamentos",
                    )
                    if criado:
                        resultado.acoes_criadas += 1
                        resultado.regras_disparadas.append("INSUMOS_DOMINANTE")
                        resultado.detalhes.append("Ação criada: insumos dominantes")

            # ── Regra 3: Aumento de custo > 20% ───────────────────────────────
            if "AUMENTO_CUSTO" in regras_ativas and len(serie) >= 2:
                ultimo = serie[-1].total
                anterior = serie[-2].total
                if anterior > 0:
                    variacao = (ultimo - anterior) / anterior * 100
                    if variacao > 20:
                        notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                            tipo="ALERTA_FINANCEIRO",
                            titulo="Custos aumentaram no último mês",
                            mensagem=f"Os custos aumentaram {variacao:.1f}% em relação ao mês anterior ({serie[-2].periodo} → {serie[-1].periodo}).",
                            nivel="WARNING",
                            origem="automacao",
                            origem_id=f"aumento_custo_{safra_id}_{serie[-1].periodo}",
                        ))
                        if notif:
                            resultado.notificacoes_criadas += 1
                            resultado.regras_disparadas.append("AUMENTO_CUSTO")
                            resultado.detalhes.append(f"Notificação: aumento de custos {variacao:.1f}%")

        except Exception as exc:
            status = "ERRO"
            resultado.mensagem = f"Erro durante execução: {exc}"
            logger.exception(f"Erro em automações safra={safra_id}: {exc}")

        # ── Persiste execução ──────────────────────────────────────────────────
        self.session.add(AutomacaoExecucao(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            executado_por=executado_por,
            regras_disparadas=resultado.regras_disparadas,
            acoes_criadas=resultado.acoes_criadas,
            notificacoes_criadas=resultado.notificacoes_criadas,
            status=status,
            mensagem=resultado.mensagem,
        ))
        await self.session.commit()

        logger.info(
            f"Automações safra={safra_id} [{status}]: "
            f"{resultado.acoes_criadas} ações, {resultado.notificacoes_criadas} notif, "
            f"regras={resultado.regras_disparadas}"
        )
        return resultado

    async def listar_execucoes(self, safra_id: uuid.UUID, limit: int = 20) -> list[AutomacaoExecucao]:
        stmt = (
            select(AutomacaoExecucao)
            .where(
                AutomacaoExecucao.tenant_id == self.tenant_id,
                AutomacaoExecucao.safra_id == safra_id,
            )
            .order_by(AutomacaoExecucao.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _criar_acao_sem_duplicar(
        self, safra_id: uuid.UUID, tipo: str, titulo: str,
        descricao: str, prioridade: str, rota: str,
    ) -> bool:
        stmt = select(PlanoAcaoItem).where(
            PlanoAcaoItem.tenant_id == self.tenant_id,
            PlanoAcaoItem.safra_id == safra_id,
            PlanoAcaoItem.tipo == tipo,
            PlanoAcaoItem.status.in_(["PENDENTE", "CONCLUIDA"]),
        ).limit(1)
        if (await self.session.execute(stmt)).scalar_one_or_none():
            return False

        self.session.add(PlanoAcaoItem(
            id=uuid.uuid4(), tenant_id=self.tenant_id, safra_id=safra_id,
            tipo=tipo, titulo=titulo, descricao=descricao, prioridade=prioridade,
            status="PENDENTE", rota=rota, origem="AUTOMACAO",
        ))
        await self.session.flush()
        return True
