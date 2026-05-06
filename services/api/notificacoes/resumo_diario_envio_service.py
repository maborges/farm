import asyncio
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import cast, Boolean
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.database import async_session_maker
from notificacoes.models import NotificacaoPreferencia, Notificacao
from notificacoes.email_service import enviar_email
from financeiro.services.resumo_diario_service import ResumoDiarioService
from core.models.auth import Usuario
from ia.upgrade_recomendacao_service import IARecomendacaoUpgradeService

class EnvioResumoDiarioService:
    """Serviço responsável por agendar e enviar o resumo diário aos usuários (Step 199)."""

    @classmethod
    async def enviar_resumos_agendados(cls):
        """
        Varre todos os usuários com preferências de resumo diário ativas 
        e envia se o horário coincidir com o atual.
        """
        agora = datetime.now(timezone.utc)
        # Ajuste para horário local (ex: Brasília -3) se necessário, 
        # mas aqui usaremos a comparação de string HH:MM simplificada.
        # Em um sistema real, lidaríamos com o timezone do usuário.
        hora_atual_str = agora.strftime("%H:%M")
        
        logger.info(f"[ResumoDiario] Iniciando verificação de envios para {hora_atual_str}")

        async with async_session_maker() as session:
            # Buscar preferências de resumo diário ativas
            stmt = select(NotificacaoPreferencia, Usuario).join(
                Usuario, NotificacaoPreferencia.usuario_id == Usuario.id
            ).where(
                NotificacaoPreferencia.tipo == "RESUMO_DIARIO",
                NotificacaoPreferencia.horario_envio == hora_atual_str,
                (NotificacaoPreferencia.email_ativo == True) | (NotificacaoPreferencia.whatsapp_ativo == True)
            )
            
            result = await session.execute(stmt)
            preferencias = result.all()

            for pref, user in preferencias:
                try:
                    await cls.processar_envio_usuario(session, pref, user)
                except Exception as e:
                    logger.error(f"[ResumoDiario] Erro ao processar envio para usuário {user.id}: {e}")

    @classmethod
    async def processar_envio_usuario(cls, session: AsyncSession, pref: NotificacaoPreferencia, user: Usuario):
        """Processa o conteúdo e envia para os canais ativos de um usuário."""
        # Evitar envio duplicado no mesmo dia
        hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        stmt_check = select(Notificacao).where(
            Notificacao.tenant_id == pref.tenant_id,
            Notificacao.usuario_id == user.id,
            Notificacao.tipo == "RESUMO_DIARIO",
            Notificacao.created_at >= hoje_inicio
        )
        existe = (await session.execute(stmt_check)).scalar_one_or_none()
        if existe:
            logger.info(f"[ResumoDiario] Resumo já enviado hoje para usuário {user.id}")
            return

        # Step 204: Verificar recomendação comercial e cooldown
        recomendacao = None
        incluir_comercial = False
        cooldown_dias = 7
        data_limite_cooldown = datetime.now(timezone.utc) - timedelta(days=cooldown_dias)

        # Verificar se houve recomendação recente
        stmt_cooldown = select(Notificacao).where(
            Notificacao.tenant_id == pref.tenant_id,
            Notificacao.tipo == "RESUMO_DIARIO",
            cast(Notificacao.meta["has_commercial_recommendation"], Boolean) == True,
            Notificacao.created_at >= data_limite_cooldown
        ).limit(1)
        
        recente = (await session.execute(stmt_cooldown)).scalar_one_or_none()
        
        if not recente:
            # Consultar IARecomendacaoUpgradeService
            recomendacao = await IARecomendacaoUpgradeService.get_recomendacao(session, pref.tenant_id)
            if recomendacao.get("deve_recomendar"):
                incluir_comercial = True
                logger.info(f"[ResumoDiario] Incluindo recomendação comercial para tenant {pref.tenant_id}")

        # Obter o resumo diário
        resumo_svc = ResumoDiarioService(session, pref.tenant_id)
        resumo_data = await resumo_svc.obter_resumo()

        # Formatar mensagem
        titulo = f"📊 Seu Resumo Diário AgroSaaS — {datetime.now().strftime('%d/%m/%Y')}"
        
        corpo_texto = f"{resumo_data.resumo_ia}\n\n"
        
        if resumo_data.top_alertas:
            corpo_texto += "🚨 *Alertas Principais:*\n"
            for alerta in resumo_data.top_alertas[:3]:
                corpo_texto += f"• {alerta.titulo}\n"
            corpo_texto += "\n"

        corpo_texto += f"📌 *Risco:* {resumo_data.risco_principal}\n"
        corpo_texto += f"💡 *Oportunidade:* {resumo_data.oportunidade_principal}\n\n"
        
        if incluir_comercial and recomendacao:
            corpo_texto += "🚀 *Recomendação de Crescimento:*\n"
            corpo_texto += f"{recomendacao['mensagem']}\n"
            cta_text = "Ver Planos" if recomendacao["tipo"] == "UPGRADE_PLANO" else "Solicitar Créditos"
            corpo_texto += f"🔗 [{cta_text}]\n\n"
            # Tracking (Step 204)
            logger.info(f"Tracking: upgrade_intention_viewed, contexto=resumo_diario, tenant={pref.tenant_id}")

        corpo_texto += "Clique abaixo para ver a análise completa no Dashboard."

        # 1. Enviar Email
        if pref.email_ativo:
            try:
                await enviar_email(user.email, titulo, corpo_texto)
                logger.info(f"[ResumoDiario] Email enviado para {user.email}")
            except Exception as e:
                logger.error(f"[ResumoDiario] Erro ao enviar email para {user.email}: {e}")

        # 2. Enviar WhatsApp (Base pronta para integração futura)
        if pref.whatsapp_ativo and user.telefone:
            # Aqui entraria a chamada para API do WhatsApp (ex: Twilio, WPPConnect, etc.)
            logger.info(f"[ResumoDiario] [SIMULAÇÃO] Enviando WhatsApp para {user.telefone}: {titulo}")
            # cls._enviar_whatsapp(user.telefone, corpo_texto)

        # Registrar no histórico de notificações
        nova_notif = Notificacao(
            tenant_id=pref.tenant_id,
            usuario_id=user.id,
            tipo="RESUMO_DIARIO",
            titulo=titulo,
            mensagem=resumo_data.resumo_ia,
            nivel="INFO",
            meta={
                "resumo": corpo_texto,
                "canais": ["email" if pref.email_ativo else None, "whatsapp" if pref.whatsapp_ativo else None],
                "has_commercial_recommendation": incluir_comercial,
                "commercial_type": recomendacao.get("tipo") if recomendacao else None
            }
        )
        session.add(nova_notif)
        await session.commit()
