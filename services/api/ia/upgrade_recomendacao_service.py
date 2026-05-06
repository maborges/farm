from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.constants import PlanTier
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from ia.performance_service import IAPerformanceService
from ia.usage_service import consultar_creditos, _inicio_mes
from ia.models import IAUso

class IARecomendacaoUpgradeService:
    """Serviço para gerar recomendações inteligentes de upgrade baseadas em ROI e Uso de IA (Step 203)."""

    @staticmethod
    async def get_recomendacao(session: AsyncSession, tenant_id: UUID, current_tier: str | None = None):
        # 1. Recuperar Tier Atual se não fornecido
        if not current_tier:
            stmt = (
                select(PlanoAssinatura.plan_tier)
                .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
                .where(
                    AssinaturaTenant.tenant_id == tenant_id,
                    AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                    AssinaturaTenant.tipo_assinatura == "TENANT"
                )
            ).limit(1)
            result = await session.execute(stmt)
            current_tier = result.scalar_one_or_none() or PlanTier.BASICO.value

        # 2. Recuperar Métricas de Performance e ROI
        metrics_data = await IAPerformanceService.get_dashboard_metrics(session, tenant_id)
        metrics = metrics_data["metrics"]
        economia_total = Decimal(str(metrics["economia_total_gerada"]))

        # 3. Recuperar Uso e Créditos
        uso_data = await consultar_creditos(tenant_id, current_tier, session)
        
        # 4. Verificar Fallbacks (Erros por limite excedido)
        # IAUso.status == 'ERRO' e possivelmente uma mensagem de limite, mas o usage_service não bloqueia a chamada, 
        # ele apenas retorna False no verificar_limite_ia.
        # Vamos contar quantos registros de IAUso falharam por limite se houver esse tracking, 
        # ou se o usuário tentou usar e não conseguiu (origem de fallback).
        # Para o Step 203, vamos olhar para 'status' == 'LIMITE_EXCEDIDO' (se implementarmos) 
        # ou se o uso_plano >= limite_plano.
        
        limite_plano = uso_data.get("limite_plano") or 0
        usado_plano = uso_data.get("usado_plano") or 0
        total_disponivel = uso_data.get("total_disponivel") or 0
        
        # Regras de Recomendação
        recomendar = False
        tipo = "UPGRADE_PLANO"
        mensagem = ""
        plano_recomendado = ""
        roi_estimado = Decimal("0")

        # Regra 1: Se Tier BÁSICO e tem economia expressiva ou uso alto
        if current_tier == PlanTier.BASICO.value:
            # Upgrade para Profissional (custo incremental estimado R$ 200)
            custo_upgrade = Decimal("200") 
            if economia_total > custo_upgrade:
                recomendar = True
                plano_recomendado = "PROFISSIONAL"
                roi_estimado = (economia_total / custo_upgrade) if custo_upgrade > 0 else Decimal("0")
                mensagem = f"A IA já gerou R$ {economia_total:,.2f} em economia. O plano Profissional pode ampliar esse ganho com recursos avançados de simulação."
            elif usado_plano >= (limite_plano * 0.9) and limite_plano > 0:
                recomendar = True
                plano_recomendado = "PROFISSIONAL"
                mensagem = "Você está quase atingindo o limite de IA do plano Básico. O plano Profissional oferece 100 créditos mensais."

        # Regra 2: Se Tier PROFISSIONAL atingiu mais de 80% do limite
        elif current_tier == PlanTier.PROFISSIONAL.value:
            if usado_plano >= (limite_plano * 0.8):
                recomendar = True
                tipo = "CREDITOS_IA"
                mensagem = f"Você consumiu {usado_plano} de {limite_plano} créditos de IA este mês. Garanta continuidade com um pacote de créditos extras."
                plano_recomendado = "ADICIONAL_CREDITOS"
            elif economia_total > Decimal("1000"):
                recomendar = True
                tipo = "UPGRADE_PLANO"
                plano_recomendado = "ENTERPRISE"
                mensagem = f"ROI de IA confirmado: R$ {economia_total:,.2f} economizados. O plano Enterprise oferece IA ilimitada e benchmarking avançado."

        return {
            "deve_recomendar": recomendar,
            "tipo": tipo,
            "mensagem": mensagem,
            "roi_estimado": float(roi_estimado),
            "economia_gerada": float(economia_total),
            "plano_atual": current_tier,
            "plano_recomendado": plano_recomendado
        }
