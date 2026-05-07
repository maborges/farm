import uuid
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger
from sqlalchemy import select, func, and_, or_, cast, Float, update as sa_update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from ia.growth_llm_service import IAGrowthLLMService, ContextoUsuarioGrowth, DadosGrowth

from core.constants import PlanTier
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.auth import Usuario
from ia.models import (
    IAGrowthEvento, IAGrowthConfig, IAGrowthConfigHistorico, IAGrowthSugestaoRegistro,
    IAGrowthExperimento, IAGrowthExperimentoVariante, IAGrowthExperimentoEvento,
    IAGrowthUserProfile, IAUXTelemetria, IAUso, IAGrowthPlanoRecomendadoLog,
    IAGrowthAssistenteInteracao, IAGrowthAutopilotAcao
)
from ia.upgrade_recomendacao_service import IARecomendacaoUpgradeService
from ia.autopilot_service import IAAutopilotService
from ia.usage_service import consultar_creditos
from ia.ux_telemetry_service import IAUXTelemetryService

COOLDOWN_HORAS = 24
ROI_TRIGGER_MINIMO = 500.0      # R$ mínimo de ROI para gatilho
IMPACTO_ALTO_MINIMO = 5_000.0   # R$ de impacto de ação para gatilho
USO_QUOTA_PERC = 80.0           # % da cota para gatilho de créditos
PROGRESSO_MINIMO = 30.0         # % de melhoria para gatilho

# IA-Growth-12: Personas
PERSONAS = ["CONSERVADOR", "EXPLORADOR", "ORIENTADO_A_RESULTADO", "INICIANTE", "AVANCADO"]
CHURN_NIVEIS = ("BAIXO", "MEDIO", "ALTO")
OPORTUNIDADE_CATEGORIAS = ("ALTO_POTENCIAL", "TRAVADO", "RISCO", "NEUTRO")
TIER_ORDEM = [PlanTier.BASICO.value, PlanTier.PROFISSIONAL.value, PlanTier.ENTERPRISE.value]
AUTOPILOT_MODOS = {
    "BAIXO": "CONSERVADOR",
    "MEDIO": "BALANCEADO",
    "ALTO": "AGRESSIVO",
}


class IAGrowthService:
    @staticmethod
    def _tier_rank(tier: str) -> int:
        try:
            return TIER_ORDEM.index(tier)
        except ValueError:
            return 0

    @staticmethod
    def _formatar_valor(valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _classificar_risco_churn(score: float) -> str:
        if score >= 0.7:
            return "ALTO"
        if score >= 0.4:
            return "MEDIO"
        return "BAIXO"

    @staticmethod
    def _estrategia_cta_churn(contexto: str, nivel: str) -> Dict[str, str]:
        if nivel == "ALTO":
            return {
                "tipo": "RECUPERACAO_CHURN",
                "mensagem": "Precisa de ajuda para aproveitar melhor o sistema? Veja orientacoes praticas para retomar valor sem mudar seu fluxo.",
                "cta_label": "Ver ajuda rapida",
                "cta_url": "/dashboard/ia",
                "titulo_alternativo": "Aproveite melhor a plataforma",
                "tipo_abordagem": "SUPORTE",
            }

        return {
            "tipo": "REENGAJAMENTO_LEVE",
            "mensagem": "Ha recursos simples que podem gerar valor rapido no seu dia. Retome com uma recomendacao pratica e objetiva.",
            "cta_label": "Retomar agora",
            "cta_url": "/dashboard/ia",
            "titulo_alternativo": "Valor pratico para voltar ao ritmo",
            "tipo_abordagem": "VALOR_PRATICO" if contexto != "resumo" else "EDUCATIVO",
        }

    @staticmethod
    async def _cooldown_ativo(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        tipo_cta: str,
        cooldown_horas: int = COOLDOWN_HORAS,
    ) -> bool:
        """Verifica se CTA deste tipo foi exibido no período de cooldown configurado."""
        desde = datetime.now(timezone.utc) - timedelta(hours=cooldown_horas)
        filtros = [
            IAGrowthEvento.tenant_id == tenant_id,
            IAGrowthEvento.evento == "upgrade_cta_viewed",
            IAGrowthEvento.tipo_cta == tipo_cta,
            IAGrowthEvento.created_at >= desde,
        ]
        if usuario_id:
            filtros.append(IAGrowthEvento.usuario_id == usuario_id)

        q = await db.execute(select(func.count()).select_from(IAGrowthEvento).where(and_(*filtros)))
        return (q.scalar() or 0) > 0

    @staticmethod
    async def _get_config(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
    ) -> IAGrowthConfig:
        """Retorna config do contexto, criando com defaults se não existir."""
        q = await db.execute(
            select(IAGrowthConfig).where(
                IAGrowthConfig.tenant_id == tenant_id,
                IAGrowthConfig.contexto == contexto,
            )
        )
        cfg = q.scalar_one_or_none()
        if not cfg:
            cfg = IAGrowthConfig(tenant_id=tenant_id, contexto=contexto)
            db.add(cfg)
            await db.flush()
        return cfg

    @staticmethod
    async def _tier_atual(db: AsyncSession, tenant_id: uuid.UUID) -> str:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or PlanTier.BASICO.value

    @staticmethod
    def _cta_por_tier(tier: str) -> Dict[str, str]:
        if tier in (PlanTier.BASICO.value, "BASICO"):
            return {
                "tipo": "UPGRADE_PLANO",
                "cta_label": "Ver planos",
                "cta_url": "/dashboard/settings/billing",
            }
        elif tier in (PlanTier.PROFISSIONAL.value, "PROFISSIONAL"):
            return {
                "tipo": "CREDITOS_IA",
                "cta_label": "Solicitar créditos",
                "cta_url": "/dashboard/settings/ia",
            }
        else:
            return {
                "tipo": "ESPECIALISTA",
                "cta_label": "Falar com especialista",
                "cta_url": "/dashboard/settings/support",
            }

    @staticmethod
    async def calcular_score_momento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        contexto: str
    ) -> float:
        """
        Calcula score de 0 a 1 indicando o momento ideal para exibir CTA (IA-Growth-14).
        Sinais (+): Acesso a features bloqueadas, navegação intensa.
        Sinais (-): CTA fechado recentemente, baixa interação.
        """
        if not usuario_id:
            return 0.5  # Neutro para anônimos
            
        score = 0.5  # Base neutra
        
        # 1. Sinais Positivos (+)
        # Navegação intensa nos últimos 30 min (UX Telemetria)
        desde_30m = datetime.now(timezone.utc) - timedelta(minutes=30)
        q_ux = await db.execute(
            select(func.count(IAUXTelemetria.id))
            .where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.created_at >= desde_30m
            )
        )
        count_ux = q_ux.scalar() or 0
        if count_ux > 10:
            score += 0.2
        elif count_ux > 5:
            score += 0.1
            
        # Tentativa de feature bloqueada ou acesso a configs
        q_blocked = await db.execute(
            select(func.count(IAUXTelemetria.id))
            .where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.evento.in_(["restricted_access_view", "billing_view", "credits_low"]),
                IAUXTelemetria.created_at >= desde_30m
            )
        )
        if (q_blocked.scalar() or 0) > 0:
            score += 0.3

        # 2. Sinais Negativos (-)
        # CTA descartado recentemente (últimas 4 horas)
        desde_4h = datetime.now(timezone.utc) - timedelta(hours=4)
        q_neg = await db.execute(
            select(func.count(IAGrowthEvento.id))
            .where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.usuario_id == usuario_id,
                IAGrowthEvento.evento == "upgrade_cta_dismissed",
                IAGrowthEvento.created_at >= desde_4h
            )
        )
        if (q_neg.scalar() or 0) > 0:
            score -= 0.5

        # Baixa interação (menos de 2 eventos em 30 min)
        if count_ux < 2:
            score -= 0.1

        return float(max(0.0, min(1.0, score)))

    @staticmethod
    async def calcular_risco_churn(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        """
        IA-Growth-15.
        Calcula risco de churn de 0 a 1 usando sinais de uso, interação com CTAs e adoção de IA.
        """
        if not usuario_id:
            return {"score": 0.0, "nivel": "BAIXO", "sinais": {}}

        agora = datetime.now(timezone.utc)
        desde_7d = agora - timedelta(days=7)
        desde_14d = agora - timedelta(days=14)

        q_ux = await db.execute(
            select(
                func.count(IAUXTelemetria.id).filter(IAUXTelemetria.created_at >= desde_7d).label("recentes"),
                func.count(IAUXTelemetria.id).filter(
                    and_(IAUXTelemetria.created_at >= desde_14d, IAUXTelemetria.created_at < desde_7d)
                ).label("anteriores"),
            ).where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.usuario_id == usuario_id,
            )
        )
        ux_row = q_ux.one()
        uso_recente = ux_row.recentes or 0
        uso_anterior = ux_row.anteriores or 0

        dias_rows = await db.execute(
            select(IAUXTelemetria.created_at).where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.created_at >= desde_7d,
            )
        )
        dias_ativos_7d = len({row[0].date() for row in dias_rows.all() if row[0]})

        q_cta = await db.execute(
            select(
                func.count(IAGrowthEvento.id).filter(
                    and_(
                        IAGrowthEvento.evento == "upgrade_cta_viewed",
                        IAGrowthEvento.created_at >= desde_14d,
                    )
                ).label("views"),
                func.count(IAGrowthEvento.id).filter(
                    and_(
                        IAGrowthEvento.evento == "upgrade_cta_dismissed",
                        IAGrowthEvento.created_at >= desde_14d,
                    )
                ).label("dismisses"),
                func.count(IAGrowthEvento.id).filter(
                    and_(
                        IAGrowthEvento.evento == "upgrade_cta_skipped",
                        IAGrowthEvento.created_at >= desde_14d,
                    )
                ).label("skipped"),
                func.count(IAGrowthEvento.id).filter(
                    and_(
                        IAGrowthEvento.evento == "upgrade_cta_clicked",
                        IAGrowthEvento.created_at >= desde_14d,
                    )
                ).label("clicks"),
            ).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.usuario_id == usuario_id,
            )
        )
        cta_row = q_cta.one()
        views_14d = cta_row.views or 0
        dismisses_14d = cta_row.dismisses or 0
        skipped_14d = cta_row.skipped or 0
        clicks_14d = cta_row.clicks or 0
        dismiss_ratio = (dismisses_14d / views_14d) if views_14d else 0.0
        skipped_ratio = (skipped_14d / max(views_14d + skipped_14d, 1)) if (views_14d + skipped_14d) else 0.0

        q_key_features = await db.execute(
            select(func.count(IAUXTelemetria.id)).where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.created_at >= desde_14d,
                or_(
                    IAUXTelemetria.evento.in_(["essential_view_loaded", "essential_action_executed"]),
                    IAUXTelemetria.evento.like("%metricas%"),
                )
            )
        )
        uso_features_chave = q_key_features.scalar() or 0

        q_ia = await db.execute(
            select(func.count(IAUso.id)).where(
                IAUso.tenant_id == tenant_id,
                IAUso.usuario_id == usuario_id,
                IAUso.created_at >= desde_14d,
            )
        )
        uso_ia_14d = q_ia.scalar() or 0

        score = 0.35

        if uso_anterior >= 6 and uso_recente <= max(1, int(uso_anterior * 0.5)):
            score += 0.25
        elif uso_recente == 0:
            score += 0.18

        if dias_ativos_7d <= 1:
            score += 0.16
        elif dias_ativos_7d <= 3:
            score += 0.08

        if views_14d >= 2 and dismiss_ratio >= 0.4:
            score += 0.12
        if (views_14d + skipped_14d) >= 2 and skipped_ratio >= 0.35:
            score += 0.12
        if uso_features_chave == 0:
            score += 0.12
        if uso_ia_14d == 0:
            score += 0.14

        if dias_ativos_7d >= 4:
            score -= 0.10
        if uso_recente > uso_anterior and uso_recente >= 6:
            score -= 0.16
        if clicks_14d >= 1:
            score -= 0.10
        if uso_features_chave >= 4:
            score -= 0.08
        if uso_ia_14d >= 3:
            score -= 0.10

        score = float(max(0.0, min(1.0, score)))
        nivel = IAGrowthService._classificar_risco_churn(score)

        return {
            "score": score,
            "nivel": nivel,
            "sinais": {
                "uso_recente": uso_recente,
                "uso_anterior": uso_anterior,
                "dias_ativos_7d": dias_ativos_7d,
                "dismiss_ratio": round(dismiss_ratio, 3),
                "skipped_ratio": round(skipped_ratio, 3),
                "uso_features_chave": uso_features_chave,
                "uso_ia_14d": uso_ia_14d,
                "clicks_14d": clicks_14d,
            },
        }

    @staticmethod
    async def recomendacao_upgrade(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        contexto: str = "progresso",
    ) -> Dict[str, Any]:
        """
        Avalia gatilhos de conversão e retorna CTA contextual ou vazio.
        Gatilhos: ROI alto, cota 80%, ação de impacto alto, progresso relevante.
        """
        perfil_usuario = await IAGrowthService.get_perfil_usuario(db, usuario_id) if usuario_id else None

        # Respeita configuração manual do tenant (Growth-03)
        cfg = await IAGrowthService._get_config(db, tenant_id, contexto)

        if not cfg.ativo:
            return {"deve_exibir": False, "tipo": "", "mensagem": "", "cta_label": "",
                    "cta_url": "", "contexto": contexto, "cooldown_ativo": False, "roi_valor": 0.0}

        tier = await IAGrowthService._tier_atual(db, tenant_id)
        cta_info = IAGrowthService._cta_por_tier(tier)
        tipo_cta = cta_info["tipo"]

        # --- IA-Growth-14: Score de Momento (Timing Inteligente) ---
        moment_score = await IAGrowthService.calcular_score_momento(db, tenant_id, usuario_id, contexto)
        timing_decision = "FULL" # FULL, SOFT, HIDDEN
        
        if moment_score >= 0.7:
            timing_decision = "FULL"
        elif moment_score >= 0.4:
            timing_decision = "SOFT"
        else:
            timing_decision = "HIDDEN"

        # --- IA-Growth-15: Risco de Churn ---
        churn = await IAGrowthService.calcular_risco_churn(db, tenant_id, usuario_id)
        churn_risk_score = churn["score"]
        churn_risk_level = churn["nivel"]

        # --- Gatilho 1: ROI acumulado via progresso UX-11 ---
        roi_valor = 0.0
        melhoria_progresso = 0.0
        try:
            progresso = await IAUXTelemetryService.calcular_progresso_usuario_ia(db, tenant_id, usuario_id)
            roi_str = progresso["progresso"]["roi"]["total"]
            roi_valor = float(roi_str.replace("R$", "").replace(".", "").replace(",", ".").strip())
            melhoria_progresso = progresso["progresso"]["tempo_decisao"]["melhoria"]
        except Exception:
            pass

        # --- Gatilho 2: Uso da cota de IA ---
        percentual_uso = 0.0
        try:
            uso = await consultar_creditos(tenant_id, tier, db)
            limite = uso.get("limite_plano") or 0
            usado = uso.get("usado_plano") or 0
            if limite > 0:
                percentual_uso = (usado / limite) * 100
        except Exception:
            pass

        # 1. Verifica se existe experimento ATIVO para o contexto (Growth-08)
        experimento_info = None
        if churn_risk_level == "BAIXO":
            experimento_info = await IAGrowthService._aplicar_experimento_se_ativo(db, tenant_id, contexto)
            
            # Se houver experimento, ele pode fazer override de campos da config
            if experimento_info:
                override = experimento_info["config_override"]
                for campo, valor in override.items():
                    if hasattr(cfg, campo):
                        setattr(cfg, campo, valor)

        # Avalia qual gatilho dispara
        mensagem = ""
        dispara = False
        cta_info_override: Optional[Dict[str, str]] = None

        if roi_valor >= ROI_TRIGGER_MINIMO:
            dispara = True
            roi_fmt = f"R$ {roi_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            mensagem = f"A IA já gerou {roi_fmt} em valor para sua operação — destrave mais decisões com o plano {PlanTier.PROFISSIONAL.value.capitalize()}."

        elif percentual_uso >= USO_QUOTA_PERC:
            dispara = True
            mensagem = f"Você usou {percentual_uso:.0f}% da cota de IA este mês. Continue sem interrupções."

        elif melhoria_progresso >= PROGRESSO_MINIMO:
            dispara = True
            mensagem = f"Você está decidindo {melhoria_progresso:.0f}% mais rápido. Amplie esse resultado com recursos avançados."

        if churn_risk_level in {"ALTO", "MEDIO"}:
            estrategia_churn = IAGrowthService._estrategia_cta_churn(contexto, churn_risk_level)
            cta_info_override = estrategia_churn
            mensagem = estrategia_churn["mensagem"]
            dispara = True

        tipo_cta_efetivo = cta_info_override["tipo"] if cta_info_override else tipo_cta
        cta_label_efetivo = cta_info_override["cta_label"] if cta_info_override else cta_info["cta_label"]
        cta_url_efetivo = cta_info_override["cta_url"] if cta_info_override else cta_info["cta_url"]

        # --- IA-Growth-16: ajuste de agressividade pelo fit do plano ---
        # Não altera billing nem força downgrade; apenas suaviza copy/CTA
        # quando o fit é baixo, e evita sugerir Enterprise para perfis sem fit.
        try:
            fit = await IAGrowthService.calcular_fit_plano(db, tenant_id, usuario_id)
            urgencia_fit = fit["urgencia_recomendacao"]
            score_enterprise = next(
                (p["score_fit"] for p in fit["fit_por_plano"] if p["plano"] == PlanTier.ENTERPRISE.value),
                0.0,
            )
            # Evita sugerir Enterprise para usuário com fit baixo
            if "Enterprise" in mensagem and score_enterprise < 0.45:
                mensagem = mensagem.replace("Enterprise", "Profissional")
            # Suaviza CTA agressivo quando fit aponta urgência BAIXA e churn não é alto
            if urgencia_fit == "BAIXA" and churn_risk_level != "ALTO":
                cta_label_efetivo = "Ver opções de evolução"
                if dispara and timing_decision == "FULL":
                    timing_decision = "SOFT"
        except Exception:
            pass

        # Decisão final baseada em gatilho + timing
        if not dispara or timing_decision == "HIDDEN":
            # Tracking de SKIPPED se houver gatilho mas score baixo
            if dispara and timing_decision == "HIDDEN":
                skipped = IAGrowthEvento(
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    evento="upgrade_cta_skipped",
                    tipo_cta=tipo_cta_efetivo,
                    contexto=contexto,
                    churn_risk_score=churn_risk_score,
                    churn_risk_level=churn_risk_level,
                    metadados={
                        "moment_score": moment_score,
                        "timing_decision": timing_decision,
                        "roi_valor": roi_valor,
                        "churn_risk_score": churn_risk_score,
                        "churn_risk_level": churn_risk_level,
                        "preventivo": cta_info_override is not None,
                    }
                )
                db.add(skipped)
                await db.flush()

            return {
                "deve_exibir": False,
                "tipo": "",
                "mensagem": "",
                "cta_label": "",
                "cta_url": "",
                "contexto": contexto,
                "cooldown_ativo": False,
                "roi_valor": roi_valor,
                "moment_score": moment_score,
                "timing_decision": timing_decision,
                "churn_risk_score": churn_risk_score,
                "churn_risk_level": churn_risk_level,
            }

        # Verifica cooldown
        em_cooldown = await IAGrowthService._cooldown_ativo(db, tenant_id, usuario_id, tipo_cta_efetivo, cfg.cooldown_horas)
        if em_cooldown:
            return {
                "deve_exibir": False,
                "tipo": tipo_cta_efetivo,
                "mensagem": mensagem,
                "cta_label": cta_label_efetivo,
                "cta_url": cta_url_efetivo,
                "contexto": contexto,
                "cooldown_ativo": True,
                "roi_valor": roi_valor,
                "moment_score": moment_score,
                "timing_decision": timing_decision,
                "churn_risk_score": churn_risk_score,
                "churn_risk_level": churn_risk_level,
            }

        res = {
            "deve_exibir": True,
            "tipo": tipo_cta_efetivo,
            "mensagem": mensagem,
            "cta_label": cta_label_efetivo,
            "cta_url": cta_url_efetivo,
            "contexto": contexto,
            "cooldown_ativo": False,
            "roi_valor": roi_valor,
            "origem_copy": "HEURISTICA",
            "moment_score": moment_score,
            "timing_decision": timing_decision,
            "churn_risk_score": churn_risk_score,
            "churn_risk_level": churn_risk_level,
        }

        if cta_info_override:
            res["titulo_alternativo"] = cta_info_override["titulo_alternativo"]
            res["tipo_abordagem"] = cta_info_override["tipo_abordagem"]

        # --- IA-Growth-11: Geração Dinâmica via LLM ---
        if experimento_info and not cta_info_override:
            res["experimento_id"] = str(experimento_info["experimento_id"])
            res["variante_id"] = str(experimento_info["variante_id"])
            res["origem_copy"] = experimento_info.get("origem_copy") or "HEURISTICA"

            cta_dinamico = experimento_info.get("cta")
            
            # Se a variante for LLM e não tiver CTA estático, gera via LLM (ou usa cache)
            if res["origem_copy"] == "LLM" and not cta_dinamico:
                # Busca métricas para reforçar abordagem vencedora
                metricas = await IAGrowthService.calcular_metricas_cta(db, tenant_id)
                
                # IA-Growth-12: Persona e Aprendizado
                melhor_abordagem = await IAGrowthService.get_melhor_abordagem_por_perfil(db, perfil_usuario, contexto)
                
                ctx_usuario = ContextoUsuarioGrowth(
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    tier_atual=tier or "FREE",
                    nivel_uso="ALTO" if percentual_uso > 70 else "MEDIO",
                    roi_acumulado=roi_valor,
                    perfil_persona=perfil_usuario
                )
                
                dados_growth = DadosGrowth(
                    taxa_conversao_atual=metricas["taxa_conversao_geral"],
                    abordagem_vencedora=melhor_abordagem or "GANHO"
                )

                cta_dinamico = await IAGrowthLLMService.gerar_copy_cta_llm(
                    db, tenant_id, contexto, ctx_usuario, dados_growth, usuario_id=usuario_id
                )

            # Aplica copy dinâmico (estático da variante ou gerado por LLM)
            if cta_dinamico:
                res["mensagem"] = cta_dinamico.get("descricao") or res["mensagem"]
                res["cta_label"] = cta_dinamico.get("botao") or res["cta_label"]
                res["titulo_alternativo"] = cta_dinamico.get("titulo")
                res["tipo_abordagem"] = cta_dinamico.get("tipo_abordagem")

            await IAGrowthService.registrar_evento_experimento(
                db,
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                experimento_id=experimento_info["experimento_id"],
                variante_id=experimento_info["variante_id"],
                evento="SHOWN",
                contexto=contexto,
                churn_risk_score=churn_risk_score,
                churn_risk_level=churn_risk_level,
            )

        return res

    @staticmethod
    async def registrar_evento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        evento: str,
        tipo_cta: str,
        contexto: str,
        usuario_id: Optional[uuid.UUID] = None,
        churn_risk_score: Optional[float] = None,
        churn_risk_level: Optional[str] = None,
        metadados: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = metadados or {}
        if churn_risk_score is None:
            churn_risk_score = payload.get("churn_risk_score")
        if churn_risk_level is None:
            churn_risk_level = payload.get("churn_risk_level")

        db.add(IAGrowthEvento(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            evento=evento,
            tipo_cta=tipo_cta,
            contexto=contexto,
            churn_risk_score=churn_risk_score,
            churn_risk_level=churn_risk_level,
            metadados=payload,
        ))
        await db.commit()

    @staticmethod
    async def calcular_metricas_cta(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        """Growth-02 — Métricas de conversão de CTAs por contexto."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        stmt = (
            select(
                IAGrowthEvento.contexto,
                func.count().filter(IAGrowthEvento.evento == "upgrade_cta_viewed").label("exibicoes"),
                func.count().filter(IAGrowthEvento.evento == "upgrade_cta_clicked").label("cliques"),
            )
            .where(and_(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.evento.in_(["upgrade_cta_viewed", "upgrade_cta_clicked"]),
            ))
            .group_by(IAGrowthEvento.contexto)
        )
        rows = (await db.execute(stmt)).all()

        total_exibicoes = sum(r.exibicoes for r in rows)
        total_cliques = sum(r.cliques for r in rows)
        taxa_geral = (total_cliques / total_exibicoes * 100) if total_exibicoes else 0.0

        por_contexto = []
        for r in rows:
            taxa = (r.cliques / r.exibicoes * 100) if r.exibicoes else 0.0
            if taxa >= 15:
                clf = "ALTA"
            elif taxa >= 5:
                clf = "MÉDIA"
            else:
                clf = "BAIXA"
            por_contexto.append({
                "contexto": r.contexto or "geral",
                "total_exibicoes": r.exibicoes,
                "total_cliques": r.cliques,
                "taxa_conversao": round(taxa, 1),
                "classificacao": clf,
            })

        recomendacoes: list[str] = []
        baixas = [c for c in por_contexto if c["classificacao"] == "BAIXA"]
        for b in baixas:
            recomendacoes.append(
                f"Contexto '{b['contexto']}' com taxa {b['taxa_conversao']}%: "
                "revise a mensagem ou o momento de exibição do CTA."
            )
        if taxa_geral >= 15:
            recomendacoes.append("Taxa geral alta — considere expandir CTAs para outros contextos.")
        if not recomendacoes:
            recomendacoes.append("Conversão estável. Monitore semanalmente para detectar quedas.")

        return {
            "periodo_dias": periodo_dias,
            "total_exibicoes": total_exibicoes,
            "total_cliques": total_cliques,
            "taxa_conversao_geral": round(taxa_geral, 1),
            "por_contexto": por_contexto,
            "recomendacoes": recomendacoes,
        }

    @staticmethod
    async def listar_configs(
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Retorna configs de todos os contextos conhecidos, criando defaults se ausentes."""
        contextos = ["progresso", "acao", "resumo"]
        resultado = []
        for ctx in contextos:
            cfg = await IAGrowthService._get_config(db, tenant_id, ctx)
            resultado.append({
                "contexto": cfg.contexto,
                "ativo": cfg.ativo,
                "cooldown_horas": cfg.cooldown_horas,
                "prioridade": cfg.prioridade,
                "updated_at": cfg.updated_at,
            })
        await db.commit()
        return resultado

    @staticmethod
    async def atualizar_config(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
        usuario_id: Optional[uuid.UUID],
        dados: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Aplica ajuste manual em config de CTA e registra histórico."""
        cfg = await IAGrowthService._get_config(db, tenant_id, contexto)

        campos_editaveis = {"ativo": bool, "cooldown_horas": int, "prioridade": int}
        for campo, tipo in campos_editaveis.items():
            if campo not in dados or dados[campo] is None:
                continue
            valor_anterior = str(getattr(cfg, campo))
            valor_novo = str(dados[campo])
            setattr(cfg, campo, tipo(dados[campo]))
            db.add(IAGrowthConfigHistorico(
                tenant_id=tenant_id,
                contexto=contexto,
                campo_alterado=campo,
                valor_anterior=valor_anterior,
                valor_novo=valor_novo,
                alterado_por=usuario_id,
            ))

        cfg.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(cfg)
        return {
            "contexto": cfg.contexto,
            "ativo": cfg.ativo,
            "cooldown_horas": cfg.cooldown_horas,
            "prioridade": cfg.prioridade,
            "updated_at": cfg.updated_at,
        }

    @staticmethod
    async def reverter_config(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
        usuario_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        """Reverte config para defaults de fábrica e registra no histórico."""
        cfg = await IAGrowthService._get_config(db, tenant_id, contexto)
        defaults = {"ativo": True, "cooldown_horas": COOLDOWN_HORAS, "prioridade": 1}
        for campo, valor in defaults.items():
            valor_anterior = str(getattr(cfg, campo))
            setattr(cfg, campo, valor)
            db.add(IAGrowthConfigHistorico(
                tenant_id=tenant_id,
                contexto=contexto,
                campo_alterado=campo,
                valor_anterior=valor_anterior,
                valor_novo=str(valor),
                alterado_por=usuario_id,
            ))
        cfg.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(cfg)
        return {
            "contexto": cfg.contexto,
            "ativo": cfg.ativo,
            "cooldown_horas": cfg.cooldown_horas,
            "prioridade": cfg.prioridade,
            "updated_at": cfg.updated_at,
        }

    @staticmethod
    async def listar_historico(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: Optional[str] = None,
        periodo_dias: int = 30,
    ) -> List[Dict[str, Any]]:
        """Growth-04 — Histórico auditável de alterações em growth config."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        filtros = [
            IAGrowthConfigHistorico.tenant_id == tenant_id,
            IAGrowthConfigHistorico.criado_em >= desde,
        ]
        if contexto:
            filtros.append(IAGrowthConfigHistorico.contexto == contexto)

        stmt = (
            select(IAGrowthConfigHistorico, Usuario.nome_completo, Usuario.email)
            .outerjoin(Usuario, Usuario.id == IAGrowthConfigHistorico.alterado_por)
            .where(and_(*filtros))
            .order_by(IAGrowthConfigHistorico.criado_em.desc())
            .limit(100)
        )
        rows = (await db.execute(stmt)).all()

        return [
            {
                "id": str(h.id),
                "contexto": h.contexto,
                "campo_alterado": h.campo_alterado,
                "valor_anterior": h.valor_anterior,
                "valor_novo": h.valor_novo,
                "alterado_por_id": str(h.alterado_por) if h.alterado_por else None,
                "alterado_por_nome": nome_completo or email or "Sistema",
                "criado_em": h.criado_em.isoformat(),
            }
            for h, nome_completo, email in rows
        ]

    @staticmethod
    async def gerar_sugestoes_otimizacao(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        """Growth-05/06 — Heurística de sugestões persistidas de otimização de CTAs."""
        import hashlib

        metricas = await IAGrowthService.calcular_metricas_cta(db, tenant_id, periodo_dias)
        configs = await IAGrowthService.listar_configs(db, tenant_id)
        historico = await IAGrowthService.listar_historico(db, tenant_id, periodo_dias=7)

        cfg_map = {c["contexto"]: c for c in configs}
        mudancas_map: Dict[str, int] = {}
        for h in historico:
            mudancas_map[h["contexto"]] = mudancas_map.get(h["contexto"], 0) + 1

        # Carregar registros existentes para verificar status
        q = await db.execute(
            select(IAGrowthSugestaoRegistro).where(IAGrowthSugestaoRegistro.tenant_id == tenant_id)
        )
        existentes: Dict[str, IAGrowthSugestaoRegistro] = {r.sugestao_id: r for r in q.scalars().all()}

        candidatas = []
        for metrica in metricas["por_contexto"]:
            ctx = metrica["contexto"]
            taxa = metrica["taxa_conversao"]
            clf = metrica["classificacao"]
            cfg = cfg_map.get(ctx, {"ativo": True, "cooldown_horas": COOLDOWN_HORAS, "prioridade": 1})
            mudancas = mudancas_map.get(ctx, 0)

            def _add(sid: str, tipo: str, just: str, impacto: str, conf: float, payload: Dict):
                candidatas.append({
                    "id": sid, "contexto": ctx, "tipo": tipo,
                    "justificativa": just, "impacto": impacto,
                    "confianca": conf, "aplicavel": bool(payload), "acao_payload": payload,
                })

            if clf == "BAIXA" and cfg["ativo"] and cfg["cooldown_horas"] > 24:
                sid = hashlib.md5(f"REDUZIR_COOLDOWN:{ctx}".encode()).hexdigest()[:12]
                _add(sid, "REDUZIR_COOLDOWN",
                     f"Contexto '{ctx}' com taxa {taxa}% (baixa). Reduzir cooldown para 12h aumenta frequência de exposição.",
                     "MÉDIO", 0.72, {"cooldown_horas": 12})

            elif clf == "BAIXA" and cfg["ativo"] and cfg["cooldown_horas"] <= 24 and metrica["total_exibicoes"] >= 5:
                sid = hashlib.md5(f"DESATIVAR:{ctx}".encode()).hexdigest()[:12]
                _add(sid, "DESATIVAR",
                     f"Contexto '{ctx}' com {metrica['total_exibicoes']} exibições e apenas {taxa}% de conversão. Desativar evita desgaste.",
                     "ALTO", 0.65, {"ativo": False})

            if clf == "ALTA" and cfg["cooldown_horas"] > 24:
                sid = hashlib.md5(f"REDUZIR_COOLDOWN_ALTA:{ctx}".encode()).hexdigest()[:12]
                _add(sid, "REDUZIR_COOLDOWN",
                     f"Contexto '{ctx}' com alta conversão ({taxa}%) e cooldown de {cfg['cooldown_horas']}h. Reduzir para aproveitar engajamento.",
                     "ALTO", 0.85, {"cooldown_horas": 12})

            if clf == "ALTA" and cfg["prioridade"] < 3:
                sid = hashlib.md5(f"AUMENTAR_PRIORIDADE:{ctx}".encode()).hexdigest()[:12]
                _add(sid, "AUMENTAR_PRIORIDADE",
                     f"Contexto '{ctx}' converte bem ({taxa}%) mas tem prioridade {cfg['prioridade']}. Aumentar para 3 privilegia este contexto.",
                     "MÉDIO", 0.78, {"prioridade": 3})

            if mudancas >= 3:
                sid = hashlib.md5(f"ESTABILIZAR:{ctx}".encode()).hexdigest()[:12]
                _add(sid, "ESTABILIZAR",
                     f"Contexto '{ctx}' teve {mudancas} alterações nos últimos 7 dias. Mudanças frequentes dificultam análise de impacto.",
                     "BAIXO", 0.90, {})

        # Persistir/atualizar registros; ignorar sugestões já IGNORADAS/APLICADAS
        sugestoes_visiveis = []
        agora = datetime.now(timezone.utc)
        for s in candidatas:
            reg = existentes.get(s["id"])
            if reg is None:
                reg = IAGrowthSugestaoRegistro(
                    tenant_id=tenant_id, sugestao_id=s["id"],
                    contexto=s["contexto"], tipo=s["tipo"],
                    impacto=s["impacto"], confianca=s["confianca"],
                    justificativa=s["justificativa"],
                    acao_sugerida=s["acao_payload"], status="PENDENTE",
                )
                db.add(reg)
                sugestoes_visiveis.append(s)
            elif reg.status == "PENDENTE":
                # Atualizar dados frescos
                reg.justificativa = s["justificativa"]
                reg.confianca = s["confianca"]
                reg.updated_at = agora
                sugestoes_visiveis.append(s)
            # IGNORADA ou APLICADA → não exibir

        await db.commit()

        ordem_impacto = {"ALTO": 0, "MÉDIO": 1, "BAIXO": 2}
        sugestoes_visiveis.sort(key=lambda s: (ordem_impacto.get(s["impacto"], 9), -s["confianca"]))

        return {
            "periodo_dias": periodo_dias,
            "total": len(sugestoes_visiveis),
            "sugestoes": sugestoes_visiveis,
        }

    @staticmethod
    async def aplicar_sugestao(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        sugestao_id: str,
        usuario_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        """Growth-06 — Aplica sugestão, atualiza config e marca como APLICADA."""
        q = await db.execute(
            select(IAGrowthSugestaoRegistro).where(
                IAGrowthSugestaoRegistro.tenant_id == tenant_id,
                IAGrowthSugestaoRegistro.sugestao_id == sugestao_id,
            )
        )
        reg = q.scalar_one_or_none()
        if not reg:
            raise ValueError(f"Sugestão {sugestao_id} não encontrada.")
        if reg.status != "PENDENTE":
            raise ValueError(f"Sugestão já está {reg.status}.")

        if reg.acao_sugerida:
            await IAGrowthService.atualizar_config(db, tenant_id, reg.contexto, usuario_id, reg.acao_sugerida)

        reg.status = "APLICADA"
        reg.applied_at = datetime.now(timezone.utc)
        reg.responsavel_id = usuario_id
        await db.commit()
        return {"status": "APLICADA", "sugestao_id": sugestao_id, "contexto": reg.contexto}

    @staticmethod
    async def ignorar_sugestao(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        sugestao_id: str,
        usuario_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        """Growth-06 — Marca sugestão como IGNORADA."""
        q = await db.execute(
            select(IAGrowthSugestaoRegistro).where(
                IAGrowthSugestaoRegistro.tenant_id == tenant_id,
                IAGrowthSugestaoRegistro.sugestao_id == sugestao_id,
            )
        )
        reg = q.scalar_one_or_none()
        if not reg:
            raise ValueError(f"Sugestão {sugestao_id} não encontrada.")
        if reg.status != "PENDENTE":
            raise ValueError(f"Sugestão já está {reg.status}.")

        reg.status = "IGNORADA"
        reg.ignored_at = datetime.now(timezone.utc)
        reg.responsavel_id = usuario_id
        await db.commit()
        return {"status": "IGNORADA", "sugestao_id": sugestao_id}

    @staticmethod
    async def avaliar_resultado_sugestoes(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        """Growth-07 — Avalia se sugestões aplicadas melhoraram a conversão."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
        janela = 7  # dias para comparar antes/depois

        # Contagens gerais
        q_total = await db.execute(
            select(
                IAGrowthSugestaoRegistro.status,
                func.count().label("qt")
            ).where(
                IAGrowthSugestaoRegistro.tenant_id == tenant_id,
                IAGrowthSugestaoRegistro.created_at >= desde,
            ).group_by(IAGrowthSugestaoRegistro.status)
        )
        contagens: Dict[str, int] = {r.status: r.qt for r in q_total.all()}
        total_geradas = sum(contagens.values())
        total_aplicadas = contagens.get("APLICADA", 0)
        total_ignoradas = contagens.get("IGNORADA", 0)
        total_pendentes = contagens.get("PENDENTE", 0)
        taxa_aplicacao = round((total_aplicadas / total_geradas * 100) if total_geradas else 0.0, 1)

        # Sugestões aplicadas com applied_at
        q_apl = await db.execute(
            select(IAGrowthSugestaoRegistro).where(
                IAGrowthSugestaoRegistro.tenant_id == tenant_id,
                IAGrowthSugestaoRegistro.status == "APLICADA",
                IAGrowthSugestaoRegistro.applied_at.isnot(None),
                IAGrowthSugestaoRegistro.created_at >= desde,
            )
        )
        aplicadas = q_apl.scalars().all()

        async def _taxa(contexto: str, inicio: datetime, fim: datetime) -> float:
            """Taxa de conversão de um contexto em um período."""
            filtros = [
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.contexto == contexto,
                IAGrowthEvento.created_at >= inicio,
                IAGrowthEvento.created_at < fim,
                IAGrowthEvento.evento.in_(["upgrade_cta_viewed", "upgrade_cta_clicked"]),
            ]
            r = await db.execute(
                select(
                    func.count().filter(IAGrowthEvento.evento == "upgrade_cta_viewed").label("v"),
                    func.count().filter(IAGrowthEvento.evento == "upgrade_cta_clicked").label("c"),
                ).where(and_(*filtros))
            )
            row = r.one()
            return round((row.c / row.v * 100) if row.v else 0.0, 1)

        resultados = []
        for reg in aplicadas:
            t_app = reg.applied_at
            inicio_antes = t_app - timedelta(days=janela)
            fim_depois = min(t_app + timedelta(days=janela), datetime.now(timezone.utc))

            taxa_antes = await _taxa(reg.contexto, inicio_antes, t_app)
            taxa_depois = await _taxa(reg.contexto, t_app, fim_depois)

            if taxa_antes > 0:
                variacao = round((taxa_depois - taxa_antes) / taxa_antes * 100, 1)
            else:
                variacao = 100.0 if taxa_depois > 0 else 0.0

            resultados.append({
                "sugestao_id": reg.sugestao_id,
                "contexto": reg.contexto,
                "tipo": reg.tipo,
                "impacto": reg.impacto,
                "applied_at": t_app.isoformat(),
                "taxa_antes": taxa_antes,
                "taxa_depois": taxa_depois,
                "variacao": variacao,
                "ganho": taxa_depois > taxa_antes,
            })

        com_ganho = sorted([r for r in resultados if r["ganho"]], key=lambda x: -x["variacao"])
        sem_ganho = sorted([r for r in resultados if not r["ganho"]], key=lambda x: x["variacao"])

        med_antes = round(sum(r["taxa_antes"] for r in resultados) / len(resultados), 1) if resultados else 0.0
        med_depois = round(sum(r["taxa_depois"] for r in resultados) / len(resultados), 1) if resultados else 0.0
        var_media = round(sum(r["variacao"] for r in resultados) / len(resultados), 1) if resultados else 0.0

        return {
            "periodo_dias": periodo_dias,
            "total_geradas": total_geradas,
            "total_aplicadas": total_aplicadas,
            "total_ignoradas": total_ignoradas,
            "total_pendentes": total_pendentes,
            "taxa_aplicacao": taxa_aplicacao,
            "conversao_media_antes": med_antes,
            "conversao_media_depois": med_depois,
            "variacao_media": var_media,
            "com_ganho": com_ganho,
            "sem_ganho": sem_ganho,
        }

    @staticmethod
    async def _aplicar_experimento_se_ativo(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
    ) -> Optional[Dict[str, Any]]:
        """Busca experimento ativo para o contexto e escolhe uma variante (Growth-08)."""
        from ia.models import IAGrowthExperimento, IAGrowthExperimentoVariante
        import random

        stmt = (
            select(IAGrowthExperimento)
            .where(and_(
                IAGrowthExperimento.tenant_id == tenant_id,
                IAGrowthExperimento.contexto == contexto,
                IAGrowthExperimento.status == "ATIVO"
            ))
            .limit(1)
        )
        exp = (await db.execute(stmt)).scalar_one_or_none()
        if not exp:
            return None

        # Carrega variantes
        stmt_vars = select(IAGrowthExperimentoVariante).where(and_(
            IAGrowthExperimentoVariante.experimento_id == exp.id,
            IAGrowthExperimentoVariante.ativo == True
        ))
        variantes = (await db.execute(stmt_vars)).scalars().all()
        if not variantes:
            return None

        # Random ponderado
        total_peso = sum(v.peso for v in variantes)
        if total_peso <= 0:
            return None
        
        r = random.uniform(0, total_peso)
        acumulado = 0
        escolhida = variantes[0]
        for v in variantes:
            acumulado += v.peso
            if r <= acumulado:
                escolhida = v
                break
        
        return {
            "experimento_id": exp.id,
            "variante_id": escolhida.id,
            "config_override": escolhida.config_override,
            "cta": escolhida.cta, # Growth-10
            "origem_copy": escolhida.origem_copy # Growth-11
        }

    @staticmethod
    async def registrar_evento_experimento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        experimento_id: uuid.UUID,
        variante_id: uuid.UUID,
        evento: str,
        contexto: str,
        churn_risk_score: Optional[float] = None,
        churn_risk_level: Optional[str] = None,
    ) -> None:
        """Registra SHOWN ou CLICKED para uma variante de experimento (Growth-08/11/12)."""
        # IA-Growth-11: Rastreia origem da copy
        origem = await IAGrowthService._obter_origem_copy(db, variante_id)

        db.add(IAGrowthExperimentoEvento(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            experimento_id=experimento_id,
            variante_id=variante_id,
            evento=evento,
            contexto=contexto,
            origem_copy=origem,
            churn_risk_score=churn_risk_score,
            churn_risk_level=churn_risk_level,
        ))
        await db.commit()

    @staticmethod
    async def _obter_origem_copy(db: AsyncSession, variante_id: uuid.UUID) -> Optional[str]:
        """Busca a origem do copy da variante para o tracking (Growth-11)."""
        from ia.models import IAGrowthExperimentoVariante
        stmt = select(IAGrowthExperimentoVariante.origem_copy).where(IAGrowthExperimentoVariante.id == variante_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def registrar_click_experimento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        experimento_id: uuid.UUID,
        variante_id: uuid.UUID,
        contexto: str,
        churn_risk_score: Optional[float] = None,
        churn_risk_level: Optional[str] = None,
    ) -> None:
        """
        Registra clique em um CTA de experimento (Growth-08/12).
        """
        await IAGrowthService.registrar_evento_experimento(
            db,
            tenant_id,
            usuario_id,
            experimento_id,
            variante_id,
            "CLICKED",
            contexto,
            churn_risk_score=churn_risk_score,
            churn_risk_level=churn_risk_level,
        )

    @staticmethod
    async def criar_experimento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
        nome: str,
        variantes_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Cria um novo experimento A/B, garantindo que apenas um esteja ativo por contexto."""
        from ia.models import IAGrowthExperimento, IAGrowthExperimentoVariante

        # Finaliza experimentos anteriores ativos para o mesmo contexto
        await db.execute(
            sa_update(IAGrowthExperimento)
            .where(and_(
                IAGrowthExperimento.tenant_id == tenant_id,
                IAGrowthExperimento.contexto == contexto,
                IAGrowthExperimento.status == "ATIVO"
            ))
            .values(status="FINALIZADO", ended_at=datetime.now(timezone.utc))
        )

        novo_exp = IAGrowthExperimento(
            tenant_id=tenant_id,
            contexto=contexto,
            nome=nome,
            status="ATIVO",
            started_at=datetime.now(timezone.utc)
        )
        db.add(novo_exp)
        await db.flush()

        for v in variantes_data:
            db.add(IAGrowthExperimentoVariante(
                experimento_id=novo_exp.id,
                nome=v["nome"],
                config_override=v.get("config_override", {}),
                cta=v.get("cta"), # Growth-10
                peso=v.get("peso", 1.0),
                origem_copy=v.get("origem", "HEURISTICA"), # Growth-11
                ativo=True
            ))
        
        await db.commit()
        return {"id": str(novo_exp.id), "status": "ATIVO"}

    @staticmethod
    async def finalizar_experimento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        experimento_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Finaliza um experimento manual."""
        from ia.models import IAGrowthExperimento
        stmt = select(IAGrowthExperimento).where(and_(
            IAGrowthExperimento.id == experimento_id,
            IAGrowthExperimento.tenant_id == tenant_id
        ))
        exp = (await db.execute(stmt)).scalar_one_or_none()
        if not exp:
            raise ValueError("Experimento não encontrado")
        
        exp.status = "FINALIZADO"
        exp.ended_at = datetime.now(timezone.utc)
        await db.commit()
        return {"id": str(exp.id), "status": "FINALIZADO"}

    @staticmethod
    async def listar_experimentos(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todos os experimentos do tenant com filtros (Growth-08)."""
        from ia.models import IAGrowthExperimento, IAGrowthExperimentoVariante
        
        filters = [IAGrowthExperimento.tenant_id == tenant_id]
        if contexto:
            filters.append(IAGrowthExperimento.contexto == contexto)
        if status:
            filters.append(IAGrowthExperimento.status == status)
            
        stmt = (
            select(IAGrowthExperimento)
            .where(and_(*filters))
            .order_by(IAGrowthExperimento.created_at.desc())
        )
        exps = (await db.execute(stmt)).scalars().all()
        
        res = []
        for e in exps:
            # Busca variantes para compor o schema
            vars_stmt = select(IAGrowthExperimentoVariante).where(IAGrowthExperimentoVariante.experimento_id == e.id)
            variantes = (await db.execute(vars_stmt)).scalars().all()
            
            res.append({
                "id": e.id,
                "nome": e.nome,
                "contexto": e.contexto,
                "status": e.status,
                "created_at": e.created_at,
                "started_at": e.started_at,
                "ended_at": e.ended_at,
                "variantes": [
                    {
                        "id": v.id,
                        "nome": v.nome,
                        "config_override": v.config_override,
                        "cta": v.cta, # Growth-10
                        "peso": v.peso,
                        "ativo": v.ativo
                    } for v in variantes
                ]
            })
        return res

    @staticmethod
    async def calcular_resultado_experimento(
        db: AsyncSession,
        experimento_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Calcula métricas de desempenho por variante (Growth-08)."""
        from ia.models import IAGrowthExperimento, IAGrowthExperimentoVariante, IAGrowthExperimentoEvento

        exp_stmt = select(IAGrowthExperimento).where(IAGrowthExperimento.id == experimento_id)
        exp = (await db.execute(exp_stmt)).scalar_one_or_none()
        if not exp:
            raise ValueError("Experimento não encontrado")

        vars_stmt = select(IAGrowthExperimentoVariante).where(IAGrowthExperimentoVariante.experimento_id == experimento_id)
        variantes = (await db.execute(vars_stmt)).scalars().all()

        resultados_variantes = []
        for v in variantes:
            metrics_stmt = (
                select(
                    func.count().filter(IAGrowthExperimentoEvento.evento == "SHOWN").label("v"),
                    func.count().filter(IAGrowthExperimentoEvento.evento == "CLICKED").label("c"),
                ).where(IAGrowthExperimentoEvento.variante_id == v.id)
            )
            m = (await db.execute(metrics_stmt)).one()
            taxa = (m.c / m.v * 100) if m.v > 0 else 0.0
            resultados_variantes.append({
                "variante_id": v.id,
                "nome": v.nome,
                "exibicoes": m.v,
                "cliques": m.c,
                "conversao": round(taxa, 2),
            })

        total_v = sum(v["exibicoes"] for v in resultados_variantes)
        total_c = sum(v["cliques"] for v in resultados_variantes)

        # Melhor variante (heurística simples)
        vencedora = None
        if resultados_variantes:
            melhor = max(resultados_variantes, key=lambda x: x["conversao"])
            if melhor["exibicoes"] >= 10: # Mínimo de impressões
                vencedora = melhor["nome"]

        return {
            "experimento_id": exp.id,
            "nome": exp.nome,
            "status": exp.status,
            "total_exibicoes": total_v,
            "total_cliques": total_c,
            "variantes": resultados_variantes,
            "vencedora": vencedora,
            "significancia_atingida": any(v["exibicoes"] >= 20 for v in resultados_variantes)
        }

    @staticmethod
    async def _obter_dados_growth_analiticos(db: AsyncSession, tenant_id: uuid.UUID) -> DadosGrowth:
        """Coleta dados de performance e sugestões para enriquecer o prompt da IA (Growth-11)."""
        perf = await IAGrowthService.calcular_performance_copy(db, tenant_id)
        melhor = "GANHO"
        if perf:
            # Filtra apenas quem tem exibições mínimas
            validos = [p for p in perf if p["exibicoes"] >= 5]
            if validos:
                melhor = max(validos, key=lambda x: x["conversao"])["tipo_abordagem"]
            
        sug_svc = await IAGrowthService.gerar_sugestoes_otimizacao(db, tenant_id)
        sugestoes = [s["justificativa"] for s in sug_svc.get("sugestoes", [])[:3]]
        
        return DadosGrowth(
            melhor_abordagem_atual=melhor,
            historico_conversao=0.0,
            sugestoes_recentes=sugestoes
        )

    @staticmethod
    async def _obter_contexto_usuario(db: AsyncSession, tenant_id: uuid.UUID, usuario_id: Optional[uuid.UUID]) -> ContextoUsuarioGrowth:
        """Coleta o perfil comportamental e operacional do usuário (Growth-11)."""
        from ia.ux_telemetry_service import IAUXTelemetryService
        perfil_data = await IAUXTelemetryService.obter_perfil_usuario_ia(db, tenant_id, usuario_id)
        
        # Simulação de dados operacionais que viriam de outros serviços
        return ContextoUsuarioGrowth(
            modulos_ativos=["FINANCEIRO", "AGRICOLA", "IA"],
            estagio_safra="DESENVOLVIMENTO",
            nivel_uso="MEDIO",
            perfil_risco=perfil_data["perfil"]
        )

    @staticmethod
    async def gerar_variacoes_cta(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
        dados_contexto: Dict[str, Any],
        usuario_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Gera variações de copy misturando LLM e Heurísticas (Growth-11).
        """
        roi_valor = dados_contexto.get("roi_valor", 0.0)
        uso = dados_contexto.get("percentual_uso", 0.0)
        
        # 1. Tenta gerar via LLM (Variante A)
        llm_cta = None
        try:
            # Verifica feature flag 'llm_growth_enabled' se necessário (Step 10)
            # Para este step, habilitamos se o tenant tem IA geral
            usuario_ctx = await IAGrowthService._obter_contexto_usuario(db, tenant_id, usuario_id)
            growth_ctx = await IAGrowthService._obter_dados_growth_analiticos(db, tenant_id)
            
            llm_cta = await IAGrowthLLMService.gerar_copy_cta_llm(
                db, tenant_id, contexto, usuario_ctx, growth_ctx, usuario_id
            )
        except Exception as e:
            logger.error(f"Erro ao gerar copy via LLM: {e}")

        # 2. Templates Heurísticos (Variante B, C...)
        templates = {
            "URGENCIA": {
                "titulo": "Sua cota de IA está acabando!",
                "descricao": f"Você já usou {uso:.0f}% dos seus créditos. Não deixe sua operação parar por falta de insights.",
                "botao": "Expandir Cota Agora",
            },
            "PROVA_SOCIAL": {
                "titulo": "Junte-se aos grandes produtores",
                "descricao": "Produtores de alta performance usam o plano PRO para automatizar o DRE e reduzir custos em até 15%.",
                "botao": "Ver Planos PRO",
            },
            "GANHO": {
                "titulo": f"Valor gerado: R$ {roi_valor:,.2f}",
                "descricao": "Com o plano avançado, você libera ferramentas de predição que potencializam seu lucro real.",
                "botao": "Potencializar Lucro",
            },
            "PERDA": {
                "titulo": "Não perca a visibilidade da sua margem",
                "descricao": "Sem os alertas avançados, você corre o risco de identificar furos no caixa tarde demais.",
                "botao": "Garantir Segurança",
            },
            "EDUCATIVO": {
                "titulo": "Saiba como o Autopilot pode ajudar",
                "descricao": "O Autopilot economiza em média 4 horas semanais de digitação e conferência de dados.",
                "botao": "Descobrir Como",
            }
        }

        abordagens = ["GANHO", "PROVA_SOCIAL", "URGENCIA", "EDUCATIVO"]
        if contexto == "acao":
            abordagens = ["URGENCIA", "PERDA", "GANHO", "PROVA_SOCIAL"]
        
        variacoes = []
        
        # Se LLM funcionou, ele é a primeira variante
        if llm_cta:
            llm_cta["origem"] = "LLM"
            variacoes.append(llm_cta)
            # Remove a abordagem que o LLM escolheu da lista de heurísticas para evitar duplicidade
            if llm_cta["tipo_abordagem"] in abordagens:
                abordagens.remove(llm_cta["tipo_abordagem"])
        
        # Preenche com heurísticas até ter 3 variações
        for tipo in abordagens:
            if len(variacoes) >= 3:
                break
            copy = templates[tipo].copy()
            copy["tipo_abordagem"] = tipo
            copy["origem"] = "HEURISTICA"
            variacoes.append(copy)
            
        return variacoes

    @staticmethod
    async def calcular_performance_copy(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Calcula conversão por tipo de abordagem de copy (Growth-10)."""
        from ia.models import IAGrowthExperimentoVariante, IAGrowthExperimentoEvento, IAGrowthExperimento
        
        stmt = (
            select(
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].astext.label("tipo"),
                func.count().filter(IAGrowthExperimentoEvento.evento == "SHOWN").label("v"),
                func.count().filter(IAGrowthExperimentoEvento.evento == "CLICKED").label("c"),
            )
            .select_from(IAGrowthExperimentoVariante)
            .join(IAGrowthExperimentoEvento, IAGrowthExperimentoEvento.variante_id == IAGrowthExperimentoVariante.id)
            .join(IAGrowthExperimento, IAGrowthExperimento.id == IAGrowthExperimentoVariante.experimento_id)
            .where(IAGrowthExperimento.tenant_id == tenant_id)
        )
        
        if contexto:
            stmt = stmt.where(IAGrowthExperimento.contexto == contexto)
            
        stmt = stmt.group_by("tipo")
        
        res = await db.execute(stmt)
        rows = res.all()
        
        performance = []
        for row in rows:
            if not row.tipo: continue
            taxa = (row.c / row.v * 100) if row.v > 0 else 0.0
            performance.append({
                "tipo_abordagem": row.tipo,
                "exibicoes": row.v,
                "cliques": row.c,
                "conversao": round(taxa, 2)
            })
            
    @staticmethod
    async def classificar_perfil_growth(db: AsyncSession, usuario_id: uuid.UUID) -> str:
        """Classifica o perfil do usuário (Persona) com base na heurística local de uso (Growth-12)."""
        desde = datetime.now(timezone.utc) - timedelta(days=30)
        
        # 1. Contagem de interações via Telemetria
        q_telemetria = await db.execute(
            select(func.count(IAUXTelemetria.id)).where(
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.created_at >= desde
            )
        )
        interacoes = q_telemetria.scalar() or 0
        
        # 2. Uso de IA
        q_uso = await db.execute(
            select(func.count(IAUso.id)).where(
                IAUso.usuario_id == usuario_id,
                IAUso.created_at >= desde
            )
        )
        uso_ia = q_uso.scalar() or 0
        
        # 3. Acesso a métricas
        q_metricas = await db.execute(
            select(func.count(IAUXTelemetria.id)).where(
                IAUXTelemetria.usuario_id == usuario_id,
                IAUXTelemetria.evento.like("%metricas%"),
                IAUXTelemetria.created_at >= desde
            )
        )
        acesso_metricas = q_metricas.scalar() or 0

        # Heurística de classificação
        perfil = "INICIANTE"
        if interacoes > 100 or uso_ia > 50:
            perfil = "AVANCADO"
        elif acesso_metricas > 10:
            perfil = "ORIENTADO_A_RESULTADO"
        elif interacoes > 30:
            perfil = "EXPLORADOR"
        elif interacoes > 5:
            perfil = "CONSERVADOR"
            
        # Salva ou atualiza perfil
        stmt = sa_update(IAGrowthUserProfile).where(IAGrowthUserProfile.user_id == usuario_id).values(
            perfil=perfil,
            score={"interacoes": interacoes, "uso_ia": uso_ia, "acesso_metricas": acesso_metricas},
            updated_at=datetime.now(timezone.utc)
        )
        res = await db.execute(stmt)
        if res.rowcount == 0:
            db.add(IAGrowthUserProfile(
                user_id=usuario_id,
                perfil=perfil,
                score={"interacoes": interacoes, "uso_ia": uso_ia, "acesso_metricas": acesso_metricas}
            ))
        
        await db.commit()
        return perfil

    @staticmethod
    async def get_perfil_usuario(db: AsyncSession, usuario_id: uuid.UUID) -> str:
        """Retorna o perfil do usuário, classificando se necessário (Growth-12)."""
        q = await db.execute(select(IAGrowthUserProfile.perfil).where(IAGrowthUserProfile.user_id == usuario_id))
        perfil = q.scalar()
        if not perfil:
            perfil = await IAGrowthService.classificar_perfil_growth(db, usuario_id)
        return perfil

    @staticmethod
    async def get_melhor_abordagem_por_perfil(db: AsyncSession, perfil: str, contexto: str) -> Optional[str]:
        """Identifica a abordagem com melhor conversão para o perfil e contexto (Growth-12)."""
        # Agrega performance por abordagem para este perfil
        stmt = (
            select(
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].astext.label("abordagem"),
                (cast(func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "CLICKED"), Float) /
                func.nullif(cast(func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "SHOWN"), Float), 0))
                .label("taxa_conversao")
            )
            .join(IAGrowthExperimentoEvento, IAGrowthExperimentoEvento.variante_id == IAGrowthExperimentoVariante.id)
            .join(IAGrowthUserProfile, IAGrowthUserProfile.user_id == IAGrowthExperimentoEvento.usuario_id)
            .where(
                IAGrowthUserProfile.perfil == perfil,
                IAGrowthExperimentoEvento.contexto == contexto,
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].is_not(None)
            )
            .group_by(text("abordagem"))
            .order_by(text("taxa_conversao DESC"))
            .limit(1)
        )
        
        res = await db.execute(stmt)
        row = res.one_or_none()
        return row.abordagem if row else None

    @staticmethod
    async def get_performance_por_perfil(db: AsyncSession, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Retorna relatório de performance por perfil para o dashboard (Growth-12)."""
        stmt = (
            select(
                IAGrowthUserProfile.perfil,
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].astext.label("abordagem"),
                func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "CLICKED").label("cliques"),
                func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "SHOWN").label("exibicoes")
            )
            .join(IAGrowthExperimentoEvento, IAGrowthExperimentoEvento.variante_id == IAGrowthExperimentoVariante.id)
            .join(IAGrowthUserProfile, IAGrowthUserProfile.user_id == IAGrowthExperimentoEvento.usuario_id)
            .where(
                IAGrowthExperimentoEvento.tenant_id == tenant_id,
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].is_not(None)
            )
            .group_by(IAGrowthUserProfile.perfil, text("abordagem"))
        )
        
        rows = (await db.execute(stmt)).all()
        
        # Agrupa para pegar a melhor abordagem por perfil
        result_map = {}
        for r in rows:
            if r.perfil not in result_map:
                result_map[r.perfil] = {"melhor_abordagem": None, "max_taxa": -1.0}
            
            taxa = (r.cliques / r.exibicoes * 100) if r.exibicoes else 0.0
            if taxa > result_map[r.perfil]["max_taxa"]:
                result_map[r.perfil]["max_taxa"] = taxa
                result_map[r.perfil]["melhor_abordagem"] = r.abordagem
        
        final_list = []
        for p, data in result_map.items():
            final_list.append({
                "perfil": p,
                "melhor_abordagem": data["melhor_abordagem"],
                "taxa_conversao": round(data["max_taxa"], 1)
            })
            
        return final_list

    @staticmethod
    async def get_dashboard_personas(
        db: AsyncSession, 
        tenant_id: uuid.UUID, 
        periodo_dias: int = 30
    ) -> Dict[str, Any]:
        """Consolida métricas completas por persona para o Dashboard (Growth-13)."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        # 1. Total de usuários classificados
        total_q = await db.execute(
            select(func.count(IAGrowthUserProfile.user_id))
            .join(Usuario, Usuario.id == IAGrowthUserProfile.user_id)
            .where(Usuario.tenant_id == tenant_id)
        )
        total_usuarios = total_q.scalar() or 0

        # 2. Distribuição por persona
        dist_q = await db.execute(
            select(IAGrowthUserProfile.perfil, func.count(IAGrowthUserProfile.user_id))
            .join(Usuario, Usuario.id == IAGrowthUserProfile.user_id)
            .where(Usuario.tenant_id == tenant_id)
            .group_by(IAGrowthUserProfile.perfil)
        )
        distribuicao = {r[0]: r[1] for r in dist_q.all()}

        # 3. Performance Detalhada (Conversão, Melhor Abordagem, Origem, Contexto)
        stmt = (
            select(
                IAGrowthUserProfile.perfil,
                IAGrowthExperimentoEvento.contexto,
                IAGrowthExperimentoVariante.origem_copy,
                IAGrowthExperimentoVariante.cta["tipo_abordagem"].astext.label("abordagem"),
                func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "SHOWN").label("exibicoes"),
                func.count(IAGrowthExperimentoEvento.id).filter(IAGrowthExperimentoEvento.evento == "CLICKED").label("cliques")
            )
            .join(IAGrowthExperimentoVariante, IAGrowthExperimentoVariante.id == IAGrowthExperimentoEvento.variante_id)
            .join(IAGrowthUserProfile, IAGrowthUserProfile.user_id == IAGrowthExperimentoEvento.usuario_id)
            .where(
                IAGrowthExperimentoEvento.tenant_id == tenant_id,
                IAGrowthExperimentoEvento.created_at >= desde
            )
            .group_by(IAGrowthUserProfile.perfil, IAGrowthExperimentoEvento.contexto, IAGrowthExperimentoVariante.origem_copy, text("abordagem"))
        )
        
        rows = (await db.execute(stmt)).all()
        
        # Processamento das métricas por persona
        stats_por_persona = {}
        for r in rows:
            p = r.perfil
            if p not in stats_por_persona:
                stats_por_persona[p] = {
                    "usuarios": distribuicao.get(p, 0),
                    "exibicoes": 0,
                    "cliques": 0,
                    "abordagens": {},
                    "origens": {},
                    "contextos": {}
                }
            
            stats_por_persona[p]["exibicoes"] += r.exibicoes
            stats_por_persona[p]["cliques"] += r.cliques
            
            # Acumula por abordagem
            if r.abordagem:
                stats_por_persona[p]["abordagens"][r.abordagem] = stats_por_persona[p]["abordagens"].get(r.abordagem, 0) + r.cliques
            
            # Acumula por origem
            stats_por_persona[p]["origens"][r.origem_copy] = stats_por_persona[p]["origens"].get(r.origem_copy, 0) + r.cliques
            
            # Acumula por contexto
            stats_por_persona[p]["contextos"][r.contexto] = stats_por_persona[p]["contextos"].get(r.contexto, 0) + r.cliques

        performance_list = []
        melhor_persona_conv = None
        max_taxa_persona = -1.0
        
        abordagens_geral = {}
        origens_geral = {}

        for p, data in stats_por_persona.items():
            taxa = (data["cliques"] / data["exibicoes"] * 100) if data["exibicoes"] > 0 else 0.0
            
            # Melhores de cada persona
            m_abordagem = max(data["abordagens"].items(), key=lambda x: x[1])[0] if data["abordagens"] else None
            m_origem = max(data["origens"].items(), key=lambda x: x[1])[0] if data["origens"] else None
            m_contexto = max(data["contextos"].items(), key=lambda x: x[1])[0] if data["contextos"] else None
            
            performance_list.append({
                "persona": p,
                "usuarios": data["usuarios"],
                "exibicoes": data["exibicoes"],
                "cliques": data["cliques"],
                "conversao": round(taxa, 1),
                "melhor_abordagem": m_abordagem,
                "melhor_origem": m_origem,
                "melhor_contexto": m_contexto
            })

            if taxa > max_taxa_persona:
                max_taxa_persona = taxa
                melhor_persona_conv = p
            
            # Acumuladores gerais
            for a, c in data["abordagens"].items():
                abordagens_geral[a] = abordagens_geral.get(a, 0) + c
            for o, c in data["origens"].items():
                origens_geral[o] = origens_geral.get(o, 0) + c

        # 4. Performance por Timing (IA-Growth-14)
        timing_stmt = (
            select(
                IAGrowthEvento.evento,
                IAGrowthEvento.metadados["timing_decision"].astext.label("decision"),
                func.count(IAGrowthEvento.id).label("total")
            )
            .where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.evento.in_(["upgrade_cta_viewed", "upgrade_cta_clicked", "upgrade_cta_skipped"])
            )
            .group_by(IAGrowthEvento.evento, text("decision"))
        )
        timing_rows = (await db.execute(timing_stmt)).all()
        
        timing_map = {} # {decision: {exibicoes, cliques, skipped}}
        for r in timing_rows:
            decision = r.decision or "FULL" # Fallback para legados
            if decision not in timing_map:
                timing_map[decision] = {"exibicoes": 0, "cliques": 0, "skipped": 0}
            
            if r.evento == "upgrade_cta_viewed":
                timing_map[decision]["exibicoes"] += r.total
            elif r.evento == "upgrade_cta_clicked":
                timing_map[decision]["cliques"] += r.total
            elif r.evento == "upgrade_cta_skipped":
                timing_map[decision]["skipped"] += r.total

        timing_list = []
        for dec, d in timing_map.items():
            timing_list.append({
                "timing_decision": dec,
                "exibicoes": d["exibicoes"],
                "cliques": d["cliques"],
                "skipped": d["skipped"],
                "conversao": round((d["cliques"] / d["exibicoes"] * 100) if d["exibicoes"] > 0 else 0.0, 1)
            })

        # Melhores gerais (Growth-13)
        m_abordagem_geral = max(abordagens_geral.items(), key=lambda x: x[1])[0] if abordagens_geral else None
        m_origem_geral = max(origens_geral.items(), key=lambda x: x[1])[0] if origens_geral else None

        return {
            "periodo_dias": periodo_dias,
            "total_usuarios_classificados": total_usuarios,
            "distribuicao_persona": distribuicao,
            "performance_por_persona": performance_list,
            "timing_performance": timing_list,
            "melhor_persona_conversao": melhor_persona_conv,
            "melhor_abordagem_geral": m_abordagem_geral,
            "melhor_origem_geral": m_origem_geral
        }

    @staticmethod
    async def get_dashboard_churn(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        """IA-Growth-15. Consolida distribuicao, conversao e recuperacao por risco de churn."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        users_rows = await db.execute(
            select(Usuario.id).where(Usuario.tenant_id == tenant_id)
        )
        user_ids = [row[0] for row in users_rows.all()]

        distribuicao_map = {nivel: 0 for nivel in CHURN_NIVEIS}
        for user_id in user_ids:
            churn = await IAGrowthService.calcular_risco_churn(db, tenant_id, user_id)
            distribuicao_map[churn["nivel"]] += 1

        total_usuarios = len(user_ids)
        distribuicao_niveis = []
        for nivel in CHURN_NIVEIS:
            usuarios = distribuicao_map[nivel]
            percentual = (usuarios / total_usuarios * 100) if total_usuarios else 0.0
            distribuicao_niveis.append({
                "nivel": nivel,
                "usuarios": usuarios,
                "percentual": round(percentual, 1),
            })

        eventos_stmt = (
            select(
                IAGrowthEvento.churn_risk_level,
                IAGrowthEvento.evento,
                func.count(IAGrowthEvento.id).label("total"),
            )
            .where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.churn_risk_level.is_not(None),
                IAGrowthEvento.evento.in_(["upgrade_cta_viewed", "upgrade_cta_clicked", "upgrade_cta_dismissed"]),
            )
            .group_by(IAGrowthEvento.churn_risk_level, IAGrowthEvento.evento)
        )
        eventos_rows = (await db.execute(eventos_stmt)).all()

        conversao_map = {
            nivel: {"exibicoes": 0, "cliques": 0}
            for nivel in CHURN_NIVEIS
        }
        for row in eventos_rows:
            nivel = row.churn_risk_level or "BAIXO"
            if nivel not in conversao_map:
                conversao_map[nivel] = {"exibicoes": 0, "cliques": 0}
            if row.evento == "upgrade_cta_viewed":
                conversao_map[nivel]["exibicoes"] += row.total
            elif row.evento == "upgrade_cta_clicked":
                conversao_map[nivel]["cliques"] += row.total

        conversao_por_nivel = []
        for nivel in CHURN_NIVEIS:
            exibicoes = conversao_map[nivel]["exibicoes"]
            cliques = conversao_map[nivel]["cliques"]
            conversao = (cliques / exibicoes * 100) if exibicoes else 0.0
            conversao_por_nivel.append({
                "nivel": nivel,
                "exibicoes": exibicoes,
                "cliques": cliques,
                "conversao": round(conversao, 1),
            })

        alto_risco_viewed = await db.execute(
            select(func.count(func.distinct(IAGrowthEvento.usuario_id))).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.churn_risk_level == "ALTO",
                IAGrowthEvento.tipo_cta == "RECUPERACAO_CHURN",
                IAGrowthEvento.evento == "upgrade_cta_viewed",
                IAGrowthEvento.usuario_id.is_not(None),
            )
        )
        alto_risco_clicked = await db.execute(
            select(func.count(func.distinct(IAGrowthEvento.usuario_id))).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.churn_risk_level == "ALTO",
                IAGrowthEvento.tipo_cta == "RECUPERACAO_CHURN",
                IAGrowthEvento.evento == "upgrade_cta_clicked",
                IAGrowthEvento.usuario_id.is_not(None),
            )
        )

        usuarios_alto_risco = alto_risco_viewed.scalar() or 0
        usuarios_recuperados = alto_risco_clicked.scalar() or 0
        taxa_recuperacao = (usuarios_recuperados / usuarios_alto_risco * 100) if usuarios_alto_risco else 0.0

        impacto_stmt = await db.execute(
            select(
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_viewed").label("views"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_clicked").label("clicks"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_dismissed").label("dismisses"),
            ).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.tipo_cta.in_(["RECUPERACAO_CHURN", "REENGAJAMENTO_LEVE"]),
            )
        )
        impacto_row = impacto_stmt.one()
        impacto_views = impacto_row.views or 0
        impacto_clicks = impacto_row.clicks or 0
        impacto_dismisses = impacto_row.dismisses or 0

        return {
            "periodo_dias": periodo_dias,
            "total_usuarios_avaliados": total_usuarios,
            "distribuicao_niveis": distribuicao_niveis,
            "conversao_por_nivel": conversao_por_nivel,
            "recuperacao_alto_risco": {
                "usuarios_alto_risco": usuarios_alto_risco,
                "usuarios_recuperados": usuarios_recuperados,
                "taxa_recuperacao": round(taxa_recuperacao, 1),
            },
            "impacto_cta_preventivo": {
                "exibicoes": impacto_views,
                "cliques": impacto_clicks,
                "dismisses": impacto_dismisses,
                "conversao": round((impacto_clicks / impacto_views * 100) if impacto_views else 0.0, 1),
            },
        }

    # ─── IA-Growth-16: Recomendação consultiva de plano ──────────────────────

    PLANO_LABEL = {
        PlanTier.BASICO.value: "Plano Essencial / Planejamento",
        PlanTier.PROFISSIONAL.value: "Plano Profissional",
        PlanTier.ENTERPRISE.value: "Plano Enterprise",
    }

    PLANO_FEATURES = {
        PlanTier.BASICO.value: [
            "Planejamento de safra e orçamento",
            "Cadastros essenciais",
            "Relatórios básicos",
        ],
        PlanTier.PROFISSIONAL.value: [
            "Cenários financeiros e DRE",
            "Alertas inteligentes e recomendações",
            "Relatórios agrícolas avançados",
            "Hedging e gestão de custos",
            "Integrações fiscais",
        ],
        PlanTier.ENTERPRISE.value: [
            "Rastreabilidade ponta-a-ponta",
            "Operações multi-unidade",
            "Compliance e exportação",
            "IA ilimitada e benchmarking",
            "Carbono e ESG",
        ],
    }

    @staticmethod
    def _plano_atual_para_fit(tier: str) -> str:
        """Normaliza tier (PREMIUM == ENTERPRISE para fins de fit)."""
        if tier in {PlanTier.ENTERPRISE.value, "ENTERPRISE", "PREMIUM"}:
            return PlanTier.ENTERPRISE.value
        if tier in {PlanTier.PROFISSIONAL.value, "PROFISSIONAL"}:
            return PlanTier.PROFISSIONAL.value
        return PlanTier.BASICO.value

    @staticmethod
    async def _coletar_sinais_fit(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        """Coleta sinais brutos usados pelo fit. Falhas individuais não derrubam o cálculo."""
        sinais: Dict[str, Any] = {
            "uso_ia_pct": 0.0,
            "uso_features_chave": 0,
            "tentativas_features_bloqueadas": 0,
            "eventos_intencao_upgrade": 0,
            "dias_ativos_30d": 0,
            "uso_ia_ilimitada_perto_limite": False,
            "tem_multi_unidade": False,
            "tem_pecuaria": False,
            "tem_rh": False,
        }

        tier_atual = await IAGrowthService._tier_atual(db, tenant_id)

        # Uso de IA (% da cota)
        try:
            uso = await consultar_creditos(tenant_id, tier_atual, db)
            limite = uso.get("limite_plano") or 0
            usado = uso.get("usado_plano") or 0
            if limite > 0:
                pct = (usado / limite) * 100
                sinais["uso_ia_pct"] = float(round(pct, 2))
                sinais["uso_ia_ilimitada_perto_limite"] = pct >= 70.0
        except Exception:
            pass

        # Atividade nos últimos 30 dias
        try:
            desde = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = select(func.count(func.distinct(func.date(IAUXTelemetria.created_at)))).where(
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.created_at >= desde,
            )
            if usuario_id:
                stmt = stmt.where(IAUXTelemetria.usuario_id == usuario_id)
            sinais["dias_ativos_30d"] = int((await db.execute(stmt)).scalar() or 0)
        except Exception:
            pass

        # Tentativas de uso de features bloqueadas (eventos do front)
        try:
            desde = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = select(func.count(IAGrowthEvento.id)).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.evento.in_(["monetization_blocked", "feature_blocked", "tier_required"]),
            )
            sinais["tentativas_features_bloqueadas"] = int((await db.execute(stmt)).scalar() or 0)
        except Exception:
            pass

        # Eventos de intenção de upgrade (cliques no CTA, abertura da página de billing)
        try:
            desde = datetime.now(timezone.utc) - timedelta(days=30)
            stmt = select(func.count(IAGrowthEvento.id)).where(
                IAGrowthEvento.tenant_id == tenant_id,
                IAGrowthEvento.created_at >= desde,
                IAGrowthEvento.evento.in_(["upgrade_cta_clicked", "upgrade_intention_created", "billing_page_view"]),
            )
            sinais["eventos_intencao_upgrade"] = int((await db.execute(stmt)).scalar() or 0)
        except Exception:
            pass

        # Uso de features-chave da IA (compartilhado com o pacote do calcular_score_momento)
        try:
            desde = datetime.now(timezone.utc) - timedelta(days=14)
            stmt = select(func.count(IAUso.id)).where(
                IAUso.tenant_id == tenant_id,
                IAUso.created_at >= desde,
            )
            sinais["uso_features_chave"] = int((await db.execute(stmt)).scalar() or 0)
        except Exception:
            pass

        # Tamanho/complexidade do tenant — best-effort, opcional
        try:
            from core.models.unidade_produtiva import UnidadeProdutiva  # type: ignore
            stmt = select(func.count(UnidadeProdutiva.id)).where(
                UnidadeProdutiva.tenant_id == tenant_id,
                UnidadeProdutiva.ativo.is_(True),
            )
            qtd_unidades = int((await db.execute(stmt)).scalar() or 0)
            sinais["qtd_unidades_produtivas"] = qtd_unidades
            sinais["tem_multi_unidade"] = qtd_unidades >= 2
        except Exception:
            sinais["qtd_unidades_produtivas"] = 0

        return sinais

    @staticmethod
    async def calcular_fit_plano(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Calcula o score de fit (0..1) para BASICO, PROFISSIONAL e ENTERPRISE.

        Retorna dict com:
          plano_recomendado, score_fit, motivos, funcionalidades_mais_relevantes,
          urgencia_recomendacao, persona, churn_risk_level, fit_por_plano, sinais,
          plano_atual.
        """
        tier_atual_raw = await IAGrowthService._tier_atual(db, tenant_id)
        tier_atual = IAGrowthService._plano_atual_para_fit(tier_atual_raw)

        sinais = await IAGrowthService._coletar_sinais_fit(db, tenant_id, usuario_id)

        persona = await IAGrowthService.get_perfil_usuario(db, usuario_id) if usuario_id else None
        churn = await IAGrowthService.calcular_risco_churn(db, tenant_id, usuario_id)
        churn_level = churn.get("nivel", "BAIXO")

        # Score base começa pelo tier atual (mantém continuidade)
        scores: Dict[str, float] = {
            PlanTier.BASICO.value: 0.30,
            PlanTier.PROFISSIONAL.value: 0.30,
            PlanTier.ENTERPRISE.value: 0.20,
        }
        motivos_por_plano: Dict[str, List[str]] = {
            PlanTier.BASICO.value: [],
            PlanTier.PROFISSIONAL.value: [],
            PlanTier.ENTERPRISE.value: [],
        }

        # Sinais → pontuação
        if sinais["uso_ia_pct"] >= 70.0:
            scores[PlanTier.PROFISSIONAL.value] += 0.20
            scores[PlanTier.ENTERPRISE.value] += 0.10
            motivos_por_plano[PlanTier.PROFISSIONAL.value].append(
                f"Você já usou {sinais['uso_ia_pct']:.0f}% da cota mensal de IA"
            )

        if sinais["tentativas_features_bloqueadas"] >= 3:
            scores[PlanTier.PROFISSIONAL.value] += 0.20
            scores[PlanTier.ENTERPRISE.value] += 0.10
            motivos_por_plano[PlanTier.PROFISSIONAL.value].append(
                f"{sinais['tentativas_features_bloqueadas']} tentativas de uso de recursos não disponíveis no plano atual"
            )

        if sinais["eventos_intencao_upgrade"] >= 1:
            scores[PlanTier.PROFISSIONAL.value] += 0.10
            scores[PlanTier.ENTERPRISE.value] += 0.10
            motivos_por_plano[PlanTier.PROFISSIONAL.value].append(
                "Você demonstrou interesse explícito em planos superiores"
            )

        if sinais["dias_ativos_30d"] >= 15:
            scores[PlanTier.PROFISSIONAL.value] += 0.10
            motivos_por_plano[PlanTier.PROFISSIONAL.value].append(
                f"Uso recorrente da plataforma ({sinais['dias_ativos_30d']} dias ativos no mês)"
            )

        if sinais["tem_multi_unidade"]:
            scores[PlanTier.ENTERPRISE.value] += 0.25
            motivos_por_plano[PlanTier.ENTERPRISE.value].append(
                f"Operação multi-unidade ({sinais.get('qtd_unidades_produtivas', 0)} propriedades ativas)"
            )

        if sinais["uso_features_chave"] >= 30:
            scores[PlanTier.PROFISSIONAL.value] += 0.10
            scores[PlanTier.ENTERPRISE.value] += 0.05

        # Persona → suaviza/amplia
        if persona == "ORIENTADO_A_RESULTADO":
            scores[PlanTier.PROFISSIONAL.value] += 0.05
            scores[PlanTier.ENTERPRISE.value] += 0.10
        elif persona == "AVANCADO":
            scores[PlanTier.ENTERPRISE.value] += 0.10
        elif persona == "INICIANTE" or persona == "CONSERVADOR":
            scores[PlanTier.BASICO.value] += 0.10
            # Penaliza Enterprise para perfis iniciantes/conservadores
            scores[PlanTier.ENTERPRISE.value] = max(0.0, scores[PlanTier.ENTERPRISE.value] - 0.15)

        # Churn → reduz agressividade (não força downgrade)
        if churn_level == "ALTO":
            for k in scores:
                scores[k] = max(0.0, scores[k] - 0.10)
        elif churn_level == "MEDIO":
            for k in scores:
                scores[k] = max(0.0, scores[k] - 0.05)

        # Não recomendar tier inferior ao atual (consultivo, não downgrade)
        ordem = [PlanTier.BASICO.value, PlanTier.PROFISSIONAL.value, PlanTier.ENTERPRISE.value]
        idx_atual = ordem.index(tier_atual)
        for tier_inferior in ordem[:idx_atual]:
            scores[tier_inferior] = 0.0

        # Clamp em [0, 1]
        for k in scores:
            scores[k] = float(min(1.0, max(0.0, scores[k])))

        # Ranking → melhor fit
        plano_recomendado, score_fit = max(scores.items(), key=lambda kv: kv[1])

        # Se nada se diferencia, mantém o atual
        if score_fit < 0.35:
            plano_recomendado = tier_atual
            score_fit = scores.get(tier_atual, 0.30)

        # Urgência baseada em sinais críticos
        if (
            sinais["uso_ia_pct"] >= 90.0
            or sinais["tentativas_features_bloqueadas"] >= 5
            or sinais["eventos_intencao_upgrade"] >= 3
        ):
            urgencia = "ALTA"
        elif score_fit >= 0.60:
            urgencia = "MEDIA"
        else:
            urgencia = "BAIXA"

        # Em churn alto, bloqueia "ALTA"
        if churn_level == "ALTO" and urgencia == "ALTA":
            urgencia = "MEDIA"

        funcionalidades = IAGrowthService.PLANO_FEATURES.get(plano_recomendado, [])
        motivos = motivos_por_plano.get(plano_recomendado, [])
        if not motivos:
            motivos.append(
                f"Seu uso atual indica que o {IAGrowthService.PLANO_LABEL.get(plano_recomendado, plano_recomendado)} entrega o melhor custo-benefício."
            )

        fit_por_plano = [
            {
                "plano": p,
                "plano_label": IAGrowthService.PLANO_LABEL.get(p, p),
                "score_fit": scores[p],
                "motivos": motivos_por_plano[p][:3],
                "funcionalidades_relevantes": IAGrowthService.PLANO_FEATURES.get(p, [])[:3],
            }
            for p in ordem
        ]

        return {
            "plano_atual": tier_atual,
            "plano_recomendado": plano_recomendado,
            "score_fit": round(score_fit, 3),
            "motivos": motivos[:4],
            "funcionalidades_mais_relevantes": funcionalidades[:5],
            "urgencia_recomendacao": urgencia,
            "persona": persona,
            "churn_risk_level": churn_level,
            "fit_por_plano": fit_por_plano,
            "sinais": sinais,
        }

    @staticmethod
    async def calcular_score_oportunidade(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Calcula score de oportunidade comercial por usuário (IA-Growth-18)."""
        fit = await IAGrowthService.calcular_fit_plano(db, tenant_id, usuario_id)
        sinais = fit.get("sinais", {})
        plano_atual = fit["plano_atual"]
        plano_recomendado = fit["plano_recomendado"]
        churn_level = fit["churn_risk_level"]
        persona = fit.get("persona") or "NEUTRO"
        score_fit = float(fit["score_fit"])

        desde_30d = datetime.now(timezone.utc) - timedelta(days=30)
        desde_14d = datetime.now(timezone.utc) - timedelta(days=14)

        assist_filters = [
            IAGrowthAssistenteInteracao.tenant_id == tenant_id,
            IAGrowthAssistenteInteracao.created_at >= desde_30d,
        ]
        if usuario_id:
            assist_filters.append(IAGrowthAssistenteInteracao.usuario_id == usuario_id)
        q_assistente = await db.execute(
            select(func.count(IAGrowthAssistenteInteracao.id)).where(*assist_filters)
        )
        interacoes_assistente = int(q_assistente.scalar() or 0)

        cta_filters = [
            IAGrowthEvento.tenant_id == tenant_id,
            IAGrowthEvento.created_at >= desde_14d,
        ]
        if usuario_id:
            cta_filters.append(IAGrowthEvento.usuario_id == usuario_id)
        q_cta = await db.execute(
            select(
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_viewed").label("views"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_clicked").label("clicks"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_dismissed").label("dismisses"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_skipped").label("skipped"),
            ).where(*cta_filters)
        )
        cta_row = q_cta.one()
        cta_views = int(cta_row.views or 0)
        cta_clicks = int(cta_row.clicks or 0)
        cta_dismisses = int(cta_row.dismisses or 0)
        cta_skipped = int(cta_row.skipped or 0)
        cta_rate = (cta_clicks / cta_views) if cta_views else 0.0

        usage_score = min(1.0, max(float(sinais.get("uso_ia_pct", 0.0)) / 100.0, float(sinais.get("uso_features_chave", 0.0)) / 10.0))
        bloqueio_score = min(1.0, float(sinais.get("tentativas_features_bloqueadas", 0.0)) / 5.0)
        freq_score = min(1.0, float(sinais.get("dias_ativos_30d", 0.0)) / 12.0)
        persona_score = 0.9 if persona in {"EXPLORADOR", "AVANCADO"} else 0.65 if persona == "ORIENTADO_A_RESULTADO" else 0.35
        churn_score = 1.0 if churn_level == "BAIXO" else 0.45 if churn_level == "MEDIO" else 0.0
        assist_score = min(1.0, interacoes_assistente / 4.0)
        cta_score = min(1.0, cta_rate + (cta_clicks / 6.0))
        engagement_bonus = min(1.0, float(sinais.get("eventos_intencao_upgrade", 0.0)) / 3.0)

        score = (
            score_fit * 0.34
            + usage_score * 0.16
            + bloqueio_score * 0.10
            + freq_score * 0.10
            + persona_score * 0.08
            + churn_score * 0.10
            + assist_score * 0.07
            + cta_score * 0.05
            + engagement_bonus * 0.00
        )

        if churn_level == "ALTO":
            score -= 0.18
        elif churn_level == "MEDIO":
            score -= 0.06

        if usage_score >= 0.7 and churn_level == "BAIXO":
            score += 0.06
        if cta_clicks > 0:
            score += 0.04
        if cta_dismisses > cta_clicks:
            score -= 0.04
        if cta_skipped > 0:
            score -= 0.02

        score = float(max(0.0, min(1.0, score)))

        if churn_level == "ALTO":
            categoria = "RISCO"
        elif score_fit >= 0.7 and churn_level == "BAIXO" and usage_score >= 0.55:
            categoria = "ALTO_POTENCIAL"
        elif score_fit >= 0.65 and (cta_views > 0 and cta_clicks == 0):
            categoria = "TRAVADO"
        else:
            categoria = "NEUTRO"

        nivel = "ALTO" if score >= 0.7 else "MEDIO" if score >= 0.4 else "BAIXO"
        plano_atual_rank = IAGrowthService._tier_rank(plano_atual)
        plano_recomendado_rank = IAGrowthService._tier_rank(plano_recomendado)

        if categoria == "RISCO":
            acao_sugerida = "REENGAJAMENTO"
            cta_label = "Retomar valor"
            cta_url = "/dashboard/ia/performance"
        elif categoria == "ALTO_POTENCIAL":
            acao_sugerida = "CTA_AGRESSIVO"
            cta_label = "Ver plano recomendado"
            cta_url = "/dashboard/settings/billing"
        elif categoria == "TRAVADO":
            acao_sugerida = "ASSISTENTE_PROATIVO"
            cta_label = "Explicar valor"
            cta_url = "/dashboard/ia/performance"
        else:
            acao_sugerida = "CONTEUDO_EDUCATIVO"
            cta_label = "Aprender mais"
            cta_url = "/dashboard/ia"

        if plano_recomendado_rank <= plano_atual_rank and categoria == "ALTO_POTENCIAL":
            cta_url = "/dashboard/ia/performance"

        impact_base = max(
            0.0,
            float(sinais.get("uso_ia_pct", 0.0)) * 0.18
            + float(sinais.get("uso_features_chave", 0.0)) * 14.0
            + interacoes_assistente * 4.0
            + cta_clicks * 12.0,
        )
        if plano_recomendado_rank > plano_atual_rank:
            delta_tier = float(plano_recomendado_rank - plano_atual_rank)
            impact_base += 120.0 * delta_tier * (0.65 + score_fit)
        else:
            impact_base += 45.0 * (0.4 + score_fit)
        if categoria == "RISCO":
            impact_base *= 0.45
        elif categoria == "TRAVADO":
            impact_base *= 0.75

        return {
            "score": score,
            "nivel": nivel,
            "categoria": categoria,
            "plano_atual": plano_atual,
            "plano_recomendado": plano_recomendado,
            "persona": persona,
            "churn_risk_level": churn_level,
            "cta_views": cta_views,
            "cta_clicks": cta_clicks,
            "assistente_interacoes": interacoes_assistente,
            "uso_features_chave": float(sinais.get("uso_features_chave", 0.0)),
            "uso_ia_pct": float(sinais.get("uso_ia_pct", 0.0)),
            "frequencia_uso_score": freq_score,
            "uso_premium_score": usage_score,
            "bloqueios_score": bloqueio_score,
            "assistente_score": assist_score,
            "cta_score": cta_score,
            "cta_label": cta_label,
            "cta_url": cta_url,
            "acao_sugerida": acao_sugerida,
            "impacto_estimado": round(impact_base, 2),
            "score_fit": score_fit,
        }

    @staticmethod
    async def get_dashboard_oportunidades(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
        limite: int = 20,
        persona: Optional[str] = None,
        plano: Optional[str] = None,
        contexto: Optional[str] = None,
        categoria: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consolida prioridades de Revenue Intelligence por usuário."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        plano_map = {
            row.plan_tier: {"nome": row.nome, "preco_mensal": float(row.preco_mensal or 0.0)}
            for row in (await db.execute(
                select(PlanoAssinatura.plan_tier, PlanoAssinatura.nome, PlanoAssinatura.preco_mensal)
                .where(PlanoAssinatura.ativo == True)  # noqa: E712
            )).all()
        }

        user_rows = await db.execute(
            select(Usuario.id, Usuario.nome_completo, Usuario.username).where(Usuario.tenant_id == tenant_id)
        )
        usuarios = user_rows.all()

        oportunidades: List[Dict[str, Any]] = []
        for usuario_id, nome_completo, username in usuarios:
            score = await IAGrowthService.calcular_score_oportunidade(db, tenant_id, usuario_id)

            contexto_q = await db.execute(
                select(IAGrowthEvento.contexto)
                .where(
                    IAGrowthEvento.tenant_id == tenant_id,
                    IAGrowthEvento.usuario_id == usuario_id,
                    IAGrowthEvento.created_at >= desde,
                )
                .order_by(IAGrowthEvento.created_at.desc())
                .limit(1)
            )
            contexto_ultimo = contexto_q.scalar_one_or_none() or "geral"

            plano_atual = score["plano_atual"]
            plano_recomendado = score["plano_recomendado"]
            plano_atual_info = plano_map.get(plano_atual, {})
            plano_rec_info = plano_map.get(plano_recomendado, {})
            preco_atual = float(plano_atual_info.get("preco_mensal", 0.0))
            preco_rec = float(plano_rec_info.get("preco_mensal", 0.0))
            delta_preco = max(0.0, preco_rec - preco_atual)
            if delta_preco <= 0:
                delta_preco = max(20.0, preco_atual * 0.2)

            impacto_estimado = round(delta_preco * (0.55 + score["score"]), 2)
            if score["categoria"] == "RISCO":
                impacto_estimado = round(impacto_estimado * 0.55, 2)
            elif score["categoria"] == "TRAVADO":
                impacto_estimado = round(impacto_estimado * 0.85, 2)

            oportunidades.append({
                "usuario_id": str(usuario_id),
                "usuario_label": nome_completo or username or "Usuário",
                "persona": score["persona"],
                "plano_atual": plano_atual,
                "plano_atual_label": IAGrowthService.PLANO_LABEL.get(plano_atual, plano_atual),
                "plano_recomendado": plano_recomendado,
                "plano_recomendado_label": IAGrowthService.PLANO_LABEL.get(plano_recomendado, plano_recomendado),
                "score_fit": score["score_fit"],
                "score_oportunidade": score["score"],
                "nivel": score["nivel"],
                "categoria": score["categoria"],
                "contexto": contexto_ultimo,
                "cta_label": score["cta_label"],
                "cta_url": score["cta_url"],
                "acao_sugerida": score["acao_sugerida"],
                "impacto_estimado": impacto_estimado,
                "impacto_estimado_label": IAGrowthService._formatar_valor(impacto_estimado),
                "churn_risk_level": score["churn_risk_level"],
                "uso_premium_score": score["uso_premium_score"],
                "frequencia_uso_score": score["frequencia_uso_score"],
                "assistente_score": score["assistente_score"],
                "cta_score": score["cta_score"],
                "cta_clicks": score["cta_clicks"],
                "cta_views": score["cta_views"],
                "assistente_interacoes": score["assistente_interacoes"],
            })

        filtered: List[Dict[str, Any]] = []
        for item in oportunidades:
            if persona and item["persona"] != persona:
                continue
            if plano and item["plano_recomendado"] != plano and item["plano_atual"] != plano:
                continue
            if contexto and item["contexto"] != contexto:
                continue
            if categoria and item["categoria"] != categoria:
                continue

            filtered.append(item)

        categorias = {c: 0 for c in OPORTUNIDADE_CATEGORIAS}
        impacto_total = 0.0
        contextos = []
        for item in filtered:
            categorias[item["categoria"]] = categorias.get(item["categoria"], 0) + 1
            impacto_total += float(item["impacto_estimado"] or 0.0)
            if item["contexto"] not in contextos:
                contextos.append(item["contexto"])

        filtered.sort(key=lambda item: (item["impacto_estimado"], item["score_oportunidade"]), reverse=True)
        oportunidades_visiveis = filtered[:limite]

        return {
            "periodo_dias": periodo_dias,
            "total_oportunidades": len(filtered),
            "alto_potencial": categorias.get("ALTO_POTENCIAL", 0),
            "travados": categorias.get("TRAVADO", 0),
            "risco": categorias.get("RISCO", 0),
            "neutros": categorias.get("NEUTRO", 0),
            "impacto_total_estimado": round(impacto_total, 2),
            "contextos_disponiveis": contextos,
            "oportunidades": oportunidades_visiveis,
        }

    @staticmethod
    def _autopilot_modo_label(nivel_autonomia: str) -> str:
        return AUTOPILOT_MODOS.get(nivel_autonomia, "BALANCEADO")

    @staticmethod
    def _autopilot_permite_categoria(nivel_autonomia: str, categoria: str) -> bool:
        if nivel_autonomia == "BAIXO":
            return categoria in {"RISCO", "TRAVADO"}
        if nivel_autonomia == "MEDIO":
            return categoria in {"RISCO", "TRAVADO", "ALTO_POTENCIAL"}
        return True

    @staticmethod
    async def _autopilot_ja_executou(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tipo_acao: str,
        cooldown_horas: int = 24,
    ) -> bool:
        desde = datetime.now(timezone.utc) - timedelta(hours=cooldown_horas)
        stmt = (
            select(func.count(IAGrowthAutopilotAcao.id))
            .where(
                IAGrowthAutopilotAcao.tenant_id == tenant_id,
                IAGrowthAutopilotAcao.usuario_id == usuario_id,
                IAGrowthAutopilotAcao.tipo_acao == tipo_acao,
                IAGrowthAutopilotAcao.executada_em >= desde,
            )
        )
        qtd = (await db.execute(stmt)).scalar() or 0
        return qtd > 0

    @staticmethod
    def _autopilot_tipo_acao(categoria: str, modo_label: str) -> List[Dict[str, Any]]:
        if categoria == "ALTO_POTENCIAL":
            if modo_label == "AGRESSIVO":
                return [
                    {"tipo_acao": "CTA_AGRESSIVO", "resultado": "CTA agressivo priorizado"},
                    {"tipo_acao": "EXPERIMENTO_COPY", "resultado": "Copy vencedora priorizada"},
                ]
            return [
                {"tipo_acao": "CTA_AGRESSIVO", "resultado": "CTA agressivo priorizado"},
            ]

        if categoria == "TRAVADO":
            return [
                {"tipo_acao": "ASSISTENTE_PROATIVO", "resultado": "Assistente comercial acionado"},
                {"tipo_acao": "COPY_EDUCATIVA", "resultado": "Copy educativa reforçada"},
            ]

        if categoria == "RISCO":
            return [
                {"tipo_acao": "CTA_PREVENTIVO", "resultado": "CTA preventivo ativado"},
                {"tipo_acao": "CONTEUDO_EDUCATIVO", "resultado": "Conteúdo educativo priorizado"},
            ]

        return [
            {"tipo_acao": "REENGAJAMENTO_LEVE", "resultado": "Reengajamento leve aplicado"},
        ]

    @staticmethod
    async def executar_acoes_growth(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
        limite_usuarios: int = 50,
    ) -> Dict[str, Any]:
        """Executa ações automáticas de Growth com regras de segurança e auditoria."""
        config = await IAAutopilotService.get_config(db, tenant_id)
        autopilot_ativo = bool(getattr(config, "autopilot_enabled", None) if getattr(config, "autopilot_enabled", None) is not None else config.ativo)

        if not autopilot_ativo:
            return {
                "ativo": False,
                "modo": IAGrowthService._autopilot_modo_label(config.nivel_autonomia),
                "acoes_executadas": 0,
                "impacto_estimado": 0.0,
                "recentes": [],
            }

        oportunidades = await IAGrowthService.get_dashboard_oportunidades(
            db,
            tenant_id,
            periodo_dias=periodo_dias,
            limite=limite_usuarios,
        )

        executadas: List[Dict[str, Any]] = []
        impacto_total = 0.0
        modo_label = IAGrowthService._autopilot_modo_label(config.nivel_autonomia)
        max_por_usuario = 2 if config.nivel_autonomia != "ALTO" else 3
        desde_dismiss = datetime.now(timezone.utc) - timedelta(days=7)
        contagem_local: Dict[uuid.UUID, int] = {}

        for item in oportunidades["oportunidades"]:
            usuario_id = uuid.UUID(item["usuario_id"])
            score_oportunidade = float(item["score_oportunidade"])
            churn = float(1.0 if item["churn_risk_level"] == "ALTO" else 0.45 if item["churn_risk_level"] == "MEDIO" else 0.0)
            moment_score = await IAGrowthService.calcular_score_momento(db, tenant_id, usuario_id, item["contexto"])

            if moment_score < 0.4 and item["categoria"] != "RISCO":
                continue

            q_dismiss = await db.execute(
                select(func.count(IAGrowthEvento.id)).where(
                    IAGrowthEvento.tenant_id == tenant_id,
                    IAGrowthEvento.usuario_id == usuario_id,
                    IAGrowthEvento.evento == "upgrade_cta_dismissed",
                    IAGrowthEvento.created_at >= desde_dismiss,
                )
            )
            if (q_dismiss.scalar() or 0) > 0:
                continue

            q_count = await db.execute(
                select(func.count(IAGrowthAutopilotAcao.id)).where(
                    IAGrowthAutopilotAcao.tenant_id == tenant_id,
                    IAGrowthAutopilotAcao.usuario_id == usuario_id,
                    IAGrowthAutopilotAcao.executada_em >= datetime.now(timezone.utc) - timedelta(days=1),
                )
            )
            total_usuario = int(q_count.scalar() or 0) + contagem_local.get(usuario_id, 0)
            if total_usuario >= max_por_usuario:
                continue

            if not IAGrowthService._autopilot_permite_categoria(config.nivel_autonomia, item["categoria"]):
                continue

            for acao in IAGrowthService._autopilot_tipo_acao(item["categoria"], modo_label):
                if await IAGrowthService._autopilot_ja_executou(db, tenant_id, usuario_id, acao["tipo_acao"]):
                    continue

                impacto_estimado = float(item["impacto_estimado"]) * (
                    0.35 if item["categoria"] == "RISCO" else 0.55 if item["categoria"] == "TRAVADO" else 0.70
                )
                if moment_score < 0.55 and item["categoria"] != "RISCO":
                    continue

                if acao["tipo_acao"] == "CTA_AGRESSIVO" and item["categoria"] == "ALTO_POTENCIAL" and score_oportunidade < 0.7:
                    continue

                abordagem_vencedora = None
                if item["categoria"] in {"ALTO_POTENCIAL", "TRAVADO"} and item.get("persona"):
                    try:
                        abordagem_vencedora = await IAGrowthService.get_melhor_abordagem_por_perfil(
                            db,
                            item["persona"],
                            item["contexto"],
                        )
                    except Exception:
                        abordagem_vencedora = None

                registro = IAGrowthAutopilotAcao(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    tipo_acao=acao["tipo_acao"],
                    contexto=item["contexto"],
                    motivo=(
                        f"Categoria {item['categoria']} com score {score_oportunidade:.2f}, "
                        f"fit {float(item['score_fit']):.2f} e churn {item['churn_risk_level']}."
                    ),
                    score_oportunidade=score_oportunidade,
                    churn_risk=churn,
                    impacto_estimado=round(impacto_estimado, 2),
                    resultado={
                        "resultado": acao["resultado"],
                        "usuario_label": item["usuario_label"],
                        "plano_recomendado": item["plano_recomendado"],
                        "modo": modo_label,
                        "moment_score": round(moment_score, 3),
                        "abordagem_vencedora": abordagem_vencedora,
                    },
                    executada_em=datetime.now(timezone.utc),
                )
                db.add(registro)
                contagem_local[usuario_id] = contagem_local.get(usuario_id, 0) + 1
                executadas.append({
                    "id": str(registro.id),
                    "usuario_id": item["usuario_id"],
                    "usuario_label": item["usuario_label"],
                    "tipo_acao": acao["tipo_acao"],
                    "contexto": item["contexto"],
                    "motivo": registro.motivo,
                    "score_oportunidade": score_oportunidade,
                    "churn_risk": churn,
                    "impacto_estimado": round(impacto_estimado, 2),
                    "executada_em": registro.executada_em.isoformat(),
                    "resultado": registro.resultado,
                })
                impacto_total += round(impacto_estimado, 2)

        if executadas:
            await db.commit()

        return {
            "ativo": True,
            "modo": modo_label,
            "acoes_executadas": len(executadas),
            "impacto_estimado": round(impacto_total, 2),
            "recentes": executadas[:10],
        }

    @staticmethod
    async def get_status_autopilot(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        config = await IAAutopilotService.get_config(db, tenant_id)
        autopilot_ativo = bool(getattr(config, "autopilot_enabled", None) if getattr(config, "autopilot_enabled", None) is not None else config.ativo)

        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
        stmt = (
            select(IAGrowthAutopilotAcao)
            .where(
                IAGrowthAutopilotAcao.tenant_id == tenant_id,
                IAGrowthAutopilotAcao.executada_em >= desde,
            )
            .order_by(IAGrowthAutopilotAcao.executada_em.desc())
        )
        rows = (await db.execute(stmt)).scalars().all()
        impacto_total = sum(float(r.impacto_estimado or 0.0) for r in rows)

        return {
            "ativo": autopilot_ativo,
            "modo": IAGrowthService._autopilot_modo_label(config.nivel_autonomia),
            "nivel_autonomia": config.nivel_autonomia,
            "autopilot_enabled": autopilot_ativo,
            "acoes_executadas": len(rows),
            "impacto_estimado": round(impacto_total, 2),
            "recentes": [
                {
                    "id": str(r.id),
                    "usuario_id": str(r.usuario_id) if r.usuario_id else None,
                    "tipo_acao": r.tipo_acao,
                    "contexto": r.contexto,
                    "motivo": r.motivo,
                    "score_oportunidade": float(r.score_oportunidade or 0.0),
                    "churn_risk": float(r.churn_risk or 0.0),
                    "impacto_estimado": float(r.impacto_estimado or 0.0),
                    "executada_em": r.executada_em.isoformat(),
                    "resultado": r.resultado,
                }
                for r in rows[:10]
            ],
        }

    @staticmethod
    async def gerar_recomendacao_plano(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        persistir_log: bool = True,
    ) -> Dict[str, Any]:
        """Gera a recomendação consultiva de plano (copy + CTA + fit).

        Quando `persistir_log=True`, registra um snapshot em
        `ia_growth_plano_recomendado_log` para alimentar as métricas.
        """
        fit = await IAGrowthService.calcular_fit_plano(db, tenant_id, usuario_id)

        plano_atual = fit["plano_atual"]
        plano_recomendado = fit["plano_recomendado"]
        churn_level = fit["churn_risk_level"]

        # Caso especial: Enterprise com fit muito baixo → reengajamento
        # (não recomenda upgrade nem mantém recomendação neutra)
        enterprise_low_fit = (
            plano_atual == PlanTier.ENTERPRISE.value
            and fit["score_fit"] < 0.20
        )

        # Copy consultiva por plano
        if enterprise_low_fit:
            copy = (
                "Você contratou o Plano Enterprise mas ainda está usando uma fração "
                "dos recursos. Vamos te mostrar onde extrair valor agora."
            )
        elif plano_recomendado == PlanTier.PROFISSIONAL.value:
            copy = (
                "Pelo uso atual, o Plano Profissional parece ideal: você já explora "
                "cenários, alertas e relatórios — recursos com maior retorno nesse plano."
            )
        elif plano_recomendado == PlanTier.ENTERPRISE.value:
            copy = (
                "Sua operação tem perfil Enterprise: rastreabilidade ponta-a-ponta, "
                "múltiplas unidades e exportações são desbloqueadas neste plano."
            )
        else:
            copy = (
                "O Plano Essencial cobre o que você usa hoje. Quando seus indicadores "
                "evoluírem, te avisamos sobre o próximo passo natural."
            )

        # CTA principal — orquestrado por upgrade_recomendacao_service para evitar conflito
        recomendacao_billing = await IARecomendacaoUpgradeService.get_recomendacao(
            db, tenant_id, current_tier=plano_atual
        )
        cta_label = "Ver plano recomendado"
        cta_url = "/dashboard/settings/billing"
        cta_secundaria_label: Optional[str] = "Falar com especialista"
        cta_secundaria_url: Optional[str] = "/dashboard/settings/support"

        if enterprise_low_fit:
            # Reengajamento: foca em ativar uso, não em billing
            cta_label = "Ativar recursos do Enterprise"
            cta_url = "/dashboard/ia/progresso"
            cta_secundaria_label = "Falar com especialista"
            cta_secundaria_url = "/dashboard/settings/support"
        elif plano_recomendado == plano_atual:
            cta_label = "Ver detalhes do meu plano"
            cta_url = "/dashboard/settings/billing"
            cta_secundaria_label = None
            cta_secundaria_url = None
        elif recomendacao_billing.get("tipo") == "CREDITOS_IA":
            cta_label = "Solicitar créditos de IA"
            cta_url = "/dashboard/settings/ia"

        # Em churn alto, suaviza tom — mantém CTA mas remove ação agressiva
        if churn_level == "ALTO" and not enterprise_low_fit:
            cta_label = "Ver como aproveitar mais"
            cta_secundaria_label = "Falar com especialista"
            cta_secundaria_url = "/dashboard/settings/support"

        # Persistência (snapshot)
        log_id: Optional[uuid.UUID] = None
        if persistir_log:
            try:
                novo = IAGrowthPlanoRecomendadoLog(
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    plano_atual=plano_atual,
                    plano_recomendado=plano_recomendado,
                    score_fit=fit["score_fit"],
                    nivel_urgencia=fit["urgencia_recomendacao"],
                    persona=fit["persona"],
                    churn_risk_level=churn_level,
                    motivos=fit["motivos"],
                    funcionalidades_relevantes=fit["funcionalidades_mais_relevantes"],
                    sinais=fit["sinais"],
                )
                db.add(novo)
                await db.flush()
                log_id = novo.id
                await db.commit()
            except Exception as exc:
                logger.warning(f"[IA-Growth-16] Falha ao persistir log de recomendação: {exc}")
                await db.rollback()

        # Override de motivos/urgência quando reengajamento Enterprise
        if enterprise_low_fit:
            motivos_final = [
                "Seu plano libera recursos que ainda não foram explorados",
                "Aumentar a adoção destrava o ROI esperado do Enterprise",
            ]
            urgencia_final = "MEDIA" if churn_level != "ALTO" else fit["urgencia_recomendacao"]
        else:
            motivos_final = fit["motivos"]
            urgencia_final = fit["urgencia_recomendacao"]

        return {
            "plano_atual": plano_atual,
            "plano_atual_label": IAGrowthService.PLANO_LABEL.get(plano_atual, plano_atual),
            "plano_recomendado": plano_recomendado,
            "plano_recomendado_label": IAGrowthService.PLANO_LABEL.get(plano_recomendado, plano_recomendado),
            "score_fit": fit["score_fit"],
            "motivos": motivos_final,
            "beneficios": [copy] + fit["funcionalidades_mais_relevantes"][:3],
            "funcionalidades_mais_relevantes": fit["funcionalidades_mais_relevantes"],
            "cta_label": cta_label,
            "cta_url": cta_url,
            "cta_secundaria_label": cta_secundaria_label,
            "cta_secundaria_url": cta_secundaria_url,
            "nivel_urgencia": urgencia_final,
            "churn_risk_level": churn_level,
            "persona": fit["persona"],
            "fit_por_plano": fit["fit_por_plano"],
            "log_id": log_id,
        }

    @staticmethod
    async def metricas_plano_recomendado(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        periodo_dias: int = 30,
    ) -> Dict[str, Any]:
        """Distribuição/CTR/conversão por plano recomendado nos últimos N dias."""
        desde = datetime.now(timezone.utc) - timedelta(days=periodo_dias)

        stmt = select(
            IAGrowthPlanoRecomendadoLog.plano_recomendado.label("plano"),
            func.count(IAGrowthPlanoRecomendadoLog.id).label("total"),
            func.count(IAGrowthPlanoRecomendadoLog.clicada_em).label("clicks"),
            func.count(IAGrowthPlanoRecomendadoLog.convertida_em).label("conversoes"),
        ).where(
            IAGrowthPlanoRecomendadoLog.tenant_id == tenant_id,
            IAGrowthPlanoRecomendadoLog.exibida_em >= desde,
        ).group_by(IAGrowthPlanoRecomendadoLog.plano_recomendado)

        rows = (await db.execute(stmt)).all()
        distribuicao: List[Dict[str, Any]] = []
        total_geral = 0
        for r in rows:
            total = int(r.total or 0)
            clicks = int(r.clicks or 0)
            conv = int(r.conversoes or 0)
            total_geral += total
            distribuicao.append({
                "plano": r.plano,
                "plano_label": IAGrowthService.PLANO_LABEL.get(r.plano, r.plano),
                "total_recomendacoes": total,
                "total_clicks": clicks,
                "taxa_clique": round((clicks / total) if total else 0.0, 3),
                "total_conversoes": conv,
                "taxa_conversao": round((conv / total) if total else 0.0, 3),
            })

        return {
            "periodo_dias": periodo_dias,
            "total_recomendacoes": total_geral,
            "distribuicao": distribuicao,
        }

    @staticmethod
    async def marcar_plano_recomendado_evento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        log_id: uuid.UUID,
        evento: str,
    ) -> bool:
        """Atualiza um snapshot de recomendação de plano. evento ∈ {clique, conversao}."""
        if evento not in {"clique", "conversao"}:
            return False
        col = (
            IAGrowthPlanoRecomendadoLog.clicada_em
            if evento == "clique"
            else IAGrowthPlanoRecomendadoLog.convertida_em
        )
        stmt = (
            sa_update(IAGrowthPlanoRecomendadoLog)
            .where(
                IAGrowthPlanoRecomendadoLog.id == log_id,
                IAGrowthPlanoRecomendadoLog.tenant_id == tenant_id,
            )
            .values({col: datetime.now(timezone.utc)})
        )
        result = await db.execute(stmt)
        await db.commit()
        return (result.rowcount or 0) > 0
