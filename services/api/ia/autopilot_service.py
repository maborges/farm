import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.constants import PlanTier
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from ia.models import IAAutopilotConfig, IAAcaoAssistidaHistorico
from ia.acoes_assistidas_service import AcaoAssistidaService

class IAAutopilotService:
    @staticmethod
    async def _current_tier(session: AsyncSession, tenant_id: uuid.UUID) -> str:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() or PlanTier.BASICO.value

    @staticmethod
    async def get_config(session: AsyncSession, tenant_id: uuid.UUID) -> IAAutopilotConfig:
        """Obtém ou cria a configuração de autopilot para o tenant (Step 210)."""
        stmt = select(IAAutopilotConfig).where(IAAutopilotConfig.tenant_id == tenant_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            config = IAAutopilotConfig(
                tenant_id=tenant_id,
                ativo=False,
                autopilot_enabled=False,
                growth_engine_enabled=False,
                growth_llm_copy_enabled=False,
                growth_incentivos_enabled=False,
                growth_learning_enabled=False,
                growth_max_acoes_dia=3,
                growth_max_incentivos_mes=0,
                growth_modo="BALANCEADO",
                nivel_autonomia="BAIXO",
                tipos_permitidos=["SIMULACAO"],
                limite_impacto_percentual=10.0
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)
            
        return config

    @staticmethod
    async def update_config(
        session: AsyncSession, 
        tenant_id: uuid.UUID, 
        updates: dict
    ) -> IAAutopilotConfig:
        """Atualiza as configurações de autopilot (Step 210)."""
        config = await IAAutopilotService.get_config(session, tenant_id)
        tier = await IAAutopilotService._current_tier(session, tenant_id)
        tier_enterprise = tier == PlanTier.ENTERPRISE.value
        tier_profissional = tier == PlanTier.PROFISSIONAL.value
        
        if "ativo" in updates:
            config.ativo = bool(updates["ativo"]) if tier_enterprise else False
            config.autopilot_enabled = config.ativo
        if "autopilot_enabled" in updates:
            config.autopilot_enabled = bool(updates["autopilot_enabled"]) if tier_enterprise else False
            config.ativo = config.autopilot_enabled
        if "growth_llm_copy_enabled" in updates:
            config.growth_llm_copy_enabled = bool(updates["growth_llm_copy_enabled"]) if tier_enterprise else False
        if "growth_engine_enabled" in updates:
            config.growth_engine_enabled = bool(updates["growth_engine_enabled"]) if tier != PlanTier.BASICO.value else False
        if "growth_incentivos_enabled" in updates:
            config.growth_incentivos_enabled = bool(updates["growth_incentivos_enabled"]) if tier_enterprise else False
        if "growth_learning_enabled" in updates:
            config.growth_learning_enabled = bool(updates["growth_learning_enabled"]) if tier_enterprise else False
        if "growth_max_acoes_dia" in updates:
            limite = 3 if tier == PlanTier.BASICO.value else 10 if tier_profissional else 25
            config.growth_max_acoes_dia = min(int(updates["growth_max_acoes_dia"]), limite)
        if "growth_max_incentivos_mes" in updates:
            limite = 0 if tier != PlanTier.ENTERPRISE.value else 50
            config.growth_max_incentivos_mes = min(int(updates["growth_max_incentivos_mes"]), limite)
        if "growth_modo" in updates:
            modo = str(updates["growth_modo"]).upper()
            if tier == PlanTier.BASICO.value:
                config.growth_modo = "CONSERVADOR"
            elif tier == PlanTier.PROFISSIONAL.value:
                config.growth_modo = "BALANCEADO"
            else:
                config.growth_modo = modo if modo in {"CONSERVADOR", "BALANCEADO", "AGRESSIVO"} else "BALANCEADO"
        if "nivel_autonomia" in updates:
            config.nivel_autonomia = updates["nivel_autonomia"] if tier_enterprise else ("MEDIO" if tier_profissional else "BAIXO")
        if "tipos_permitidos" in updates:
            config.tipos_permitidos = updates["tipos_permitidos"]
        if "limite_impacto_percentual" in updates:
            config.limite_impacto_percentual = float(updates["limite_impacto_percentual"])
            
        await session.commit()
        await session.refresh(config)
        return config

    @staticmethod
    async def avaliar_e_executar(
        session: AsyncSession, 
        tenant_id: uuid.UUID, 
        plano_acao: dict
    ) -> list:
        """
        Avalia um plano de ação e executa automaticamente as ações que cumprem os critérios de autopilot (Step 210).
        Retorna a lista de ações que foram executadas automaticamente.
        """
        config = await IAAutopilotService.get_config(session, tenant_id)
        
        if not config.ativo:
            return []
            
        acoes_executadas = []
        nivel_risco_geral = plano_acao.get("nivel_risco", "BAIXO")
        
        # Regra de Ouro: Nunca executa se o risco do plano for CRITICO
        if nivel_risco_geral == "CRITICO":
            return []
            
        for acao in plano_acao.get("acoes", []):
            tipo = acao.get("tipo")
            impacto_str = acao.get("impacto_estimado", "0") # Ex: "+R$ 12.000" ou "+5%"
            
            # Tentar extrair percentual se houver para validação de limite
            impacto_percentual = 0.0
            if "%" in impacto_str:
                try:
                    # Remove símbolos e converte para float absoluto
                    clean_val = impacto_str.replace("+", "").replace("-", "").replace("%", "").strip()
                    impacto_percentual = abs(float(clean_val))
                except ValueError:
                    impacto_percentual = 0.0
            
            # Critérios de Execução Automática (Autopilot Controlado):
            # 1. Tipo de ação deve estar na lista de permitidos do usuário
            # 2. Impacto percentual deve ser menor ou igual ao limite configurado
            # 3. Ações automáticas são sempre do tipo SIMULACAO no DRE (seguras/reversíveis)
            
            permitido_pelo_usuario = tipo in config.tipos_permitidos
            dentro_do_limite = impacto_percentual <= config.limite_impacto_percentual
            eh_seguro = tipo in ["SIMULACAO", "AJUSTE_CENARIO"] # Ações que não alteram dados reais de lançamento
            
            if permitido_pelo_usuario and dentro_do_limite and eh_seguro:
                # Tentar extrair valor monetário se houver (Step 211)
                from decimal import Decimal
                impacto_valor = None
                if "R$" in impacto_str:
                    try:
                        # Remove R$, pontos e converte para Decimal
                        clean_val = impacto_str.replace("R$", "").replace(".", "").replace("+", "").replace("-", "").replace(",", ".").strip()
                        impacto_valor = Decimal(clean_val)
                    except Exception:
                        impacto_valor = None

                # Executar ação automaticamente no motor de assistência
                # Isso registrará a ação no histórico como AUTOMATICA
                await AcaoAssistidaService.registrar_acao(
                    session=session,
                    tenant_id=tenant_id,
                    origem="PLANO_ACAO",
                    origem_id=None,
                    tipo_acao=tipo,
                    parametros_json=acao.get("parametros", {}),
                    metodo_execucao="AUTOMATICA",
                    impacto_valor=impacto_valor
                )
                acoes_executadas.append({
                    "descricao": acao.get("descricao"),
                    "tipo": tipo,
                    "impacto": impacto_str
                })
                
        if acoes_executadas:
            await session.commit()
            
        return acoes_executadas
