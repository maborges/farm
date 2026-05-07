import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ia.models import IAAutopilotConfig, IAAcaoAssistidaHistorico
from ia.acoes_assistidas_service import AcaoAssistidaService

class IAAutopilotService:
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
        
        if "ativo" in updates:
            config.ativo = updates["ativo"]
            config.autopilot_enabled = updates["ativo"]
        if "autopilot_enabled" in updates:
            config.autopilot_enabled = updates["autopilot_enabled"]
            config.ativo = updates["autopilot_enabled"]
        if "nivel_autonomia" in updates:
            config.nivel_autonomia = updates["nivel_autonomia"]
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
