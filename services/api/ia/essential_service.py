import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ia.plano_acao_service import IAPlanoAcaoService
from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.insights_service import IAInsightsService
from financeiro.services.resumo_diario_service import ResumoDiarioService

from sqlalchemy import select, desc

class IAEssentialService:
    @staticmethod
    async def _obter_contexto_adaptacao(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """
        Busca perfil e contexto recente sem deixar falhas de telemetria
        derrubarem a visão essencial.
        """
        from ia.ux_telemetry_service import IAUXTelemetryService

        perfil = "NEUTRO"
        contexto_recente: Optional[Dict[str, Any]] = None

        try:
            perfil_data = await IAUXTelemetryService.obter_perfil_usuario_ia(session, tenant_id, usuario_id)
            perfil = perfil_data.get("perfil") or "NEUTRO"
        except Exception:
            logger.exception("Erro ao obter perfil de UX para visão essencial. Aplicando fallback NEUTRO.")

        try:
            contexto_recente = await IAUXTelemetryService.obter_contexto_decisao_recente(session, tenant_id, usuario_id)
        except Exception:
            logger.exception("Erro ao obter contexto recente de UX para visão essencial. Seguindo sem memória contextual.")

        return perfil, contexto_recente

    @staticmethod
    def _adaptar_resposta(data: Dict[str, Any], perfil: str, contexto_recente: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aplica adaptação de tom e comunicação (Step UX-09) com memória (Step UX-10)."""
        from ia.ux_telemetry_service import IAUXTelemetryService
        data["acao_label"] = IAUXTelemetryService.gerar_mensagem_adaptada(
            perfil=perfil,
            contexto="ESSENTIAL_CTA",
            base_data={
                "acao_label": data["acao_label"],
                "impacto_financeiro": data["impacto_financeiro"]
            },
            contexto_recente=contexto_recente
        )
        return data

    @staticmethod
    async def resolve_safra_id(session: AsyncSession, tenant_id: uuid.UUID, safra_id: Optional[uuid.UUID] = None) -> Optional[uuid.UUID]:
        """Resolve o ID da safra: usa o fornecido ou busca a ativa/recente do tenant."""
        if safra_id:
            return safra_id
            
        from agricola.safras.models import Safra
        stmt = (
            select(Safra.id)
            .where(
                Safra.tenant_id == tenant_id,
                Safra.status.notin_(["ENCERRADA", "CANCELADA"])
            )
            .order_by(desc(Safra.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def obter_essencial(session: AsyncSession, tenant_id: uuid.UUID, safra_id: Optional[uuid.UUID] = None, usuario_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Consolida todas as camadas de IA em uma visão única e priorizada (Step UX-01).
        A ideia é reduzir a carga cognitiva entregando apenas 'A Coisa Mais Importante'.
        Agora adaptando a comunicação ao perfil do usuário (Step UX-09).
        """
        perfil, contexto_recente = await IAEssentialService._obter_contexto_adaptacao(
            session,
            tenant_id,
            usuario_id=usuario_id,
        )

        safra_id = await IAEssentialService.resolve_safra_id(session, tenant_id, safra_id)
        
        if not safra_id:
            return IAEssentialService._adaptar_resposta({
                "prioridade": "NORMAL",
                "tipo": "STATUS",
                "titulo": "Aguardando Safra",
                "resumo": "Nenhuma safra ativa detectada para análise.",
                "detalhe": "Cadastre uma nova safra para ativar o Copiloto IA.",
                "impacto_financeiro": "R$ 0.00",
                "acao_label": "Cadastrar Safra",
                "rota": "/dashboard/agricola/safras",
                "cor": "slate"
            }, perfil, contexto_recente)

        logger.info(f"Consolidando visão essencial de IA para tenant {tenant_id}, safra {safra_id}")

        # 1. PRIORIDADE MÁXIMA: Plano de Ação Crítico (Risco Extremo)
        try:
            svc_plano = IAPlanoAcaoService(session, tenant_id)
            plano = await svc_plano.gerar_plano_recuperacao(safra_id)
            
            if plano.get("nivel_risco") == "CRITICO" and plano.get("acoes"):
                acao_principal = plano["acoes"][0]
                return IAEssentialService._adaptar_resposta({
                    "prioridade": "CRITICO",
                    "tipo": "PLANO_ACAO",
                    "titulo": "⚠️ Plano de Recuperação Crítico",
                    "resumo": plano["resumo"],
                    "detalhe": acao_principal["descricao"],
                    "impacto_financeiro": acao_principal.get("impacto_estimado", "N/A"),
                    "id_referencia": acao_principal.get("id"),
                    "acao_label": "Executar Plano Agora",
                    "rota": f"/dashboard/ia/plano-acao?safra_id={safra_id}",
                    "cor": "red"
                }, perfil, contexto_recente)
        except Exception as e:
            logger.error(f"Erro ao buscar plano essencial: {e}")

        # 2. SEGUNDA PRIORIDADE: Predição de Risco Alto (Antecipação)
        try:
            svc_predicao = IAPredicaoRiscoService(session, tenant_id)
            predicao = await svc_predicao.prever_risco_financeiro(safra_id)
            
            if predicao.get("risco") == "ALTO":
                return IAEssentialService._adaptar_resposta({
                    "prioridade": "IMPORTANTE",
                    "tipo": "PREDICAO_RISCO",
                    "titulo": "📉 Risco Financeiro Detectado",
                    "resumo": predicao["descricao"],
                    "detalhe": f"Tendência negativa identificada nos últimos dados. {predicao.get('acao_recomendada', '')}",
                    "impacto_financeiro": predicao.get("impacto_estimado", "N/A"),
                    "acao_label": "Simular Impacto",
                    "rota": f"/dashboard/ia/financeiro?safra_id={safra_id}",
                    "cor": "amber"
                }, perfil, contexto_recente)
        except Exception as e:
            logger.error(f"Erro ao buscar predição essencial: {e}")

        # 3. TERCEIRA PRIORIDADE: Alertas Inteligentes (Eventos Atuais)
        try:
            svc_insights = IAInsightsService(session, tenant_id)
            # Nota: obter_alertas retorna uma lista de alertas filtrados pela safra
            alertas = await svc_insights.obter_alertas(safra_id)
            
            alertas_criticos = [a for a in alertas if a.get("nivel") == "CRITICO"]
            if alertas_criticos:
                alerta = alertas_criticos[0]
                return IAEssentialService._adaptar_resposta({
                    "prioridade": "IMPORTANTE",
                    "tipo": "ALERTA",
                    "titulo": f"🔔 {alerta['titulo']}",
                    "resumo": alerta["descricao"],
                    "detalhe": alerta.get("recomendacao", "Revisar dados operacionais."),
                    "impacto_financeiro": alerta.get("impacto", "N/A"),
                    "acao_label": "Resolver Agora",
                    "rota": alerta.get("link", "/dashboard/ia/alertas"),
                    "cor": "amber"
                }, perfil, contexto_recente)
        except Exception as e:
            logger.error(f"Erro ao buscar alertas essenciais: {e}")

        # 4. FALLBACK: Resumo Diário (Informativo)
        try:
            svc_resumo = ResumoDiarioService(session, tenant_id)
            resumo = await svc_resumo.obter_resumo(safra_id)
            
            return IAEssentialService._adaptar_resposta({
                "prioridade": "NORMAL",
                "tipo": "RESUMO_DIARIO",
                "titulo": "📊 Resumo da Safra",
                "resumo": resumo.get("visao_geral", "Operação estável."),
                "detalhe": "Nenhum risco crítico ou ação urgente pendente.",
                "impacto_financeiro": "Estável",
                "acao_label": "Ver Relatório Completo",
                "rota": "/dashboard/ia/resumo",
                "cor": "emerald"
            }, perfil, contexto_recente)
        except Exception as e:
            logger.error(f"Erro ao gerar resumo essencial: {e}")
            
        return IAEssentialService._adaptar_resposta({
            "prioridade": "NORMAL",
            "tipo": "STATUS",
            "titulo": "Sincronizado",
            "resumo": "O Copiloto IA está monitorando sua safra em tempo real.",
            "detalhe": "Tudo sob controle.",
            "impacto_financeiro": "R$ 0.00",
            "acao_label": "Ver Dashboard",
            "rota": "/dashboard/ia",
            "cor": "blue"
        }, perfil, contexto_recente)
