import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ia.models import IAUXTelemetria, IAUXThreshold
from core.database import get_db

class IAUXTelemetryService:
    @staticmethod
    def _metricas_vazias() -> Dict[str, Any]:
        return {
            "resumo_geral": {
                "total_eventos": 0,
                "taxa_engajamento": 0.0,
                "tempo_medio_decisao_ms": 0.0,
                "taxa_abertura_avancado": 0.0,
            },
            "funil": {
                "visualizou": 0,
                "clicou": 0,
                "executou": 0,
                "taxa_conversao_clique": 0.0,
                "taxa_conversao_execucao": 0.0,
            },
            "comparativo_modo": {},
            "insights": [],
        }

    @staticmethod
    def _perfil_padrao() -> Dict[str, Any]:
        return {
            "perfil": "NEUTRO",
            "metadados": {
                "taxa_abertura": 0.0,
                "taxa_execucao": 0.0,
                "tempo_decisao_ms": 0.0,
                "total_visualizacoes": 0,
            },
            "justificativa": "Dados insuficientes para classificar o perfil neste momento.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _explicacao_padrao() -> Dict[str, Any]:
        return {
            "perfil": "NEUTRO",
            "titulo": "Perfil Neutro",
            "explicacao": "A IA está aprendendo seu ritmo para ajustar a interface conforme suas necessidades.",
            "metricas_usuario": {
                "tempo_medio": "0,0s",
                "taxa_execucao": "0%",
                "curiosidade": "0% abertura detalhada",
            },
            "thresholds_referencia": {},
        }

    @staticmethod
    def _progresso_padrao() -> Dict[str, Any]:
        return {
            "progresso": {
                "tempo_decisao": {
                    "atual": "0,0s",
                    "melhoria": 0,
                    "status": "ESTÁVEL",
                },
                "taxa_execucao": {
                    "atual": "0%",
                    "melhoria": 0,
                    "status": "ESTÁVEL",
                },
                "roi": {
                    "total": "R$ 0,00",
                    "melhoria": 0,
                    "status": "ESTÁVEL",
                },
                "perfil": {
                    "atual": "NEUTRO",
                    "anterior": "NEUTRO",
                    "evoluiu": False,
                },
            },
            "mensagem_destaque": "Ainda não há histórico suficiente para medir evolução da IA.",
            "periodo": "Últimos 7 dias vs período anterior",
        }

    @staticmethod
    async def track_evento(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        evento: str,
        modo: str,
        usuario_id: Optional[uuid.UUID] = None,
        sessao_id: Optional[str] = None,
        metadados: Optional[Dict[str, Any]] = None
    ) -> IAUXTelemetria:
        """Registra um evento de telemetria de UX."""
        try:
            nova_telemetria = IAUXTelemetria(
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                evento=evento,
                modo=modo,
                sessao_id=sessao_id,
                metadados=metadados or {}
            )
            db.add(nova_telemetria)
            await db.commit()
            await db.refresh(nova_telemetria)
            return nova_telemetria
        except Exception:
            await db.rollback()
            logger.exception("Erro ao registrar evento de UX '{}'.", evento)
            raise

    @staticmethod
    def gerar_mensagem_adaptada(
        perfil: str, 
        contexto: str, 
        base_data: Dict[str, Any],
        contexto_recente: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Adapta o tom e a forma de comunicação da IA com base no perfil e contexto (Step UX-09).
        Agora suporta Memória Contextual (Step UX-10).
        """
        impacto = base_data.get("impacto_financeiro", "R$ 0,00")
        acao = base_data.get("acao_label", "Executar")
        
        # 0. Processamento de Continuidade (Memory Hook UX-10)
        prefixo_contextual = ""
        if contexto_recente:
            # Prioridade: Execuções > Simulações > Alertas
            ultima_execucao = next((e for e in contexto_recente if e["evento"] == "essential_action_executed"), None)
            ultima_simulacao = next((e for e in contexto_recente if e["evento"] == "simulacao_ia_concluida"), None)
            ultimo_alerta = next((e for e in contexto_recente if e["evento"] == "alerta_ia_emitido"), None)

            if ultima_execucao:
                prefixo_contextual = "Dando continuidade à sua ação anterior, "
            elif ultima_simulacao:
                prefixo_contextual = "Com base na sua simulação, "
            elif ultimo_alerta:
                prefixo_contextual = "Reforçando o alerta recente, "

        # 1. Mensagens para CTA do Modo Essencial
        if contexto == "ESSENTIAL_CTA":
            if perfil == "CONFIANTE":
                return f"{prefixo_contextual}{acao} agora: {impacto}"
            elif perfil == "ANALÍTICO":
                return f"{prefixo_contextual}{acao} (impacto estimado: {impacto})"
            elif perfil == "INSEGURO":
                return f"{prefixo_contextual}Confirmar ação segura ({impacto})"
            return f"{prefixo_contextual}{acao}: {impacto}"
        
        # 2. Nudges de Fricção (UX-08)
        if contexto == "NUDGE_FRICCAO":
            if perfil == "CONFIANTE":
                return f"{prefixo_contextual}Simplificar visão?"
            elif perfil == "ANALÍTICO":
                return f"{prefixo_contextual}Precisa de mais detalhes?"
            else: # INSEGURO
                return f"{prefixo_contextual}Quer que eu explique o passo a passo?"

        return acao

        # 2. Mensagens para Nudges de Fricção
        if contexto == "NUDGE_FRICCAO":
            msg = "Precisa de ajuda com esta decisão?"
            if perfil == "CONFIANTE":
                msg = "Decisão rápida? Simplificamos a visão para você."
            elif perfil == "ANALÍTICO":
                msg = "Dúvida nos dados? Impacto com 95% de confiança histórica."
            elif perfil == "INSEGURO":
                msg = "Segurança em primeiro lugar: ação validada por 127 filtros."
            
            return f"{prefixo_contextual}{msg}" if prefixo_contextual else msg

        # 3. Mensagens para Feedback de Decisão (UX-04)
        if contexto == "FEEDBACK_DECISAO":
            if perfil == "CONFIANTE":
                return f"Decisão ágil — {impacto} garantidos."
            elif perfil == "ANALÍTICO":
                return f"Excelente precisão — {impacto} otimizados nos dados."
            elif perfil == "INSEGURO":
                return f"Ótima escolha — ação segura garante {impacto}."
            return f"Boa decisão — impacto de {impacto}."

        return base_data.get("original", "")

    @staticmethod
    async def obter_metricas(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        dias: Optional[int] = 30,
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calcula métricas de eficiência de UX (Modo Essencial vs Avançado)."""
        try:
            if not inicio:
                inicio = datetime.now(timezone.utc) - timedelta(days=dias)
            if not fim:
                fim = datetime.now(timezone.utc) + timedelta(days=1)

            # 1. Total de carregamentos (Essential View Loaded)
            q_loaded = await db.execute(
                select(func.count(IAUXTelemetria.id))
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.evento == "essential_view_loaded",
                    IAUXTelemetria.created_at >= inicio,
                    IAUXTelemetria.created_at < fim
                ))
            )
            total_view_loaded = q_loaded.scalar() or 0

            # 2. Total de cliques no CTA Essencial
            q_cta = await db.execute(
                select(func.count(IAUXTelemetria.id))
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.evento == "essential_cta_clicked",
                    IAUXTelemetria.created_at >= inicio,
                    IAUXTelemetria.created_at < fim
                ))
            )
            total_cta_clicked = q_cta.scalar() or 0

            # 3. Total de execuções (Essential Action Executed)
            q_exec = await db.execute(
                select(func.count(IAUXTelemetria.id))
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.evento == "essential_action_executed",
                    IAUXTelemetria.created_at >= inicio,
                    IAUXTelemetria.created_at < fim
                ))
            )
            total_executed = q_exec.scalar() or 0

            # 4. Total de aberturas do Modo Avançado
            q_adv = await db.execute(
                select(func.count(IAUXTelemetria.id))
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.evento == "advanced_mode_opened",
                    IAUXTelemetria.created_at >= inicio,
                    IAUXTelemetria.created_at < fim
                ))
            )
            total_advanced_opened = q_adv.scalar() or 0

            # 5. Tempo médio até decisão (time_to_action_ms nos metadados do essential_cta_clicked)
            q_time = await db.execute(
                text("""
                    SELECT AVG((metadados->>'time_to_action_ms')::float)
                    FROM ia_ux_telemetria
                    WHERE tenant_id = :tenant_id
                    AND evento = 'essential_cta_clicked'
                    AND created_at >= :inicio AND created_at < :fim
                    AND metadados->>'time_to_action_ms' IS NOT NULL
                """),
                {"tenant_id": tenant_id, "inicio": inicio, "fim": fim}
            )
            tempo_medio_decisao = q_time.scalar() or 0

            # 6. Comparação Essencial vs Avançado (Execuções)
            q_comparativo = await db.execute(
                select(IAUXTelemetria.modo, func.count(IAUXTelemetria.id))
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.evento == "essential_action_executed",
                    IAUXTelemetria.created_at >= inicio,
                    IAUXTelemetria.created_at < fim
                ))
                .group_by(IAUXTelemetria.modo)
            )
            comparativo = {modo: count for modo, count in q_comparativo.all()}

            # 7. Taxas
            taxa_execucao_essencial = (total_executed / total_view_loaded * 100) if total_view_loaded > 0 else 0
            taxa_abertura_avancado = (total_advanced_opened / total_view_loaded * 100) if total_view_loaded > 0 else 0

            # 8. Insight Automático
            insight = "O modo essencial está ajudando o usuário a decidir mais rápido."
            if tempo_medio_decisao > 0:
                if taxa_execucao_essencial > 50:
                    insight = f"Alta eficiência: {taxa_execucao_essencial:.1f}% das recomendações essenciais são executadas diretamente."
                elif taxa_abertura_avancado > 40:
                    insight = "Os usuários ainda preferem validar detalhes no modo avançado."


            return {
                "resumo_geral": {
                    "total_eventos": total_view_loaded + total_cta_clicked + total_executed + total_advanced_opened,
                    "taxa_engajamento": round(taxa_execucao_essencial + (total_cta_clicked / total_view_loaded * 100 if total_view_loaded > 0 else 0), 2),
                    "tempo_medio_decisao_ms": round(tempo_medio_decisao, 2),
                    "taxa_abertura_avancado": round(taxa_abertura_avancado, 2)
                },
                "funil": {
                    "visualizou": total_view_loaded,
                    "clicou": total_cta_clicked,
                    "executou": total_executed,
                    "taxa_conversao_clique": round(total_cta_clicked / total_view_loaded * 100 if total_view_loaded > 0 else 0, 2),
                    "taxa_conversao_execucao": round(total_executed / total_view_loaded * 100 if total_view_loaded > 0 else 0, 2)
                },
                "comparativo_modo": comparativo,
                "insights": [insight] if insight else []
            }
        except Exception:
            logger.exception("Erro ao calcular métricas de UX. Retornando métricas vazias.")
            return IAUXTelemetryService._metricas_vazias()

    @staticmethod
    async def obter_perfil_usuario_ia(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        dias: int = 30,
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Classifica o perfil do usuário baseado em comportamento de IA (Step UX-05)."""
        try:
            metricas = await IAUXTelemetryService.obter_metricas(db, tenant_id, dias=dias, inicio=inicio, fim=fim)

            resumo = metricas["resumo_geral"]
            funil = metricas["funil"]

            taxa_abertura = resumo["taxa_abertura_avancado"]
            taxa_execucao = funil["taxa_conversao_execucao"]
            tempo_decisao = resumo["tempo_medio_decisao_ms"]

            perfil = "NEUTRO"
            justificativa = "Comportamento equilibrado detectado."

            confiante_abertura_max = await IAUXTelemetryService.get_threshold(db, "confiante_abertura_max", 15.0)
            confiante_execucao_min = await IAUXTelemetryService.get_threshold(db, "confiante_execucao_min", 40.0)
            analitico_abertura_min = await IAUXTelemetryService.get_threshold(db, "analitico_abertura_min", 30.0)
            analitico_tempo_min = await IAUXTelemetryService.get_threshold(db, "analitico_tempo_min", 15000.0)
            inseguro_execucao_max = await IAUXTelemetryService.get_threshold(db, "inseguro_execucao_max", 15.0)

            if taxa_abertura < confiante_abertura_max and taxa_execucao > confiante_execucao_min:
                perfil = "CONFIANTE"
                justificativa = f"Alta taxa de execução (> {confiante_execucao_min:.0f}%) com baixa necessidade de validação detalhada."
            elif taxa_abertura > analitico_abertura_min or (tempo_decisao > analitico_tempo_min and taxa_execucao > 20):
                perfil = "ANALÍTICO"
                justificativa = f"Tendência a validar detalhes (> {analitico_abertura_min:.0f}% abertura) antes da execução."
            elif taxa_execucao < inseguro_execucao_max and funil["visualizou"] > 5:
                perfil = "INSEGURO"
                justificativa = f"Baixa conversão (< {inseguro_execucao_max:.0f}%) nas recomendações; necessita mais suporte."

            return {
                "perfil": perfil,
                "metadados": {
                    "taxa_abertura": taxa_abertura,
                    "taxa_execucao": taxa_execucao,
                    "tempo_decisao_ms": tempo_decisao,
                    "total_visualizacoes": funil["visualizou"]
                },
                "justificativa": justificativa,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            logger.exception("Erro ao classificar perfil de UX. Retornando perfil neutro.")
            return IAUXTelemetryService._perfil_padrao()

    @staticmethod
    async def get_threshold(db: AsyncSession, chave: str, fallback: float) -> float:
        """Busca um threshold no banco ou retorna o fallback."""
        try:
            q = await db.execute(select(IAUXThreshold).where(IAUXThreshold.chave == chave))
            obj = q.scalar_one_or_none()
            return obj.valor if obj else fallback
        except Exception:
            logger.exception("Erro ao buscar threshold de UX '{}'. Aplicando fallback.", chave)
            return fallback

    @staticmethod
    async def ajustar_thresholds_ia(db: AsyncSession) -> Dict[str, Any]:
        """
        Recalibra thresholds de UX baseados na distribuição real (Step UX-06).
        Calcula percentis (P25, P75) globais e aplica variação controlada (max 5%).
        """
        # 1. Configurações de Thresholds e Fallbacks
        configs = {
            "confiante_abertura_max": 15.0,
            "confiante_execucao_min": 40.0,
            "analitico_abertura_min": 30.0,
            "analitico_tempo_min": 15000.0,
            "inseguro_execucao_max": 15.0
        }

        # 2. Busca dados reais (simplificado para este MVP: agregando por tenant)
        # Em produção, usaríamos uma tabela de 'ia_ux_user_stats' pré-agregada
        # Aqui vamos simular a busca de percentis baseados nos dados atuais
        
        # Exemplo de lógica para buscar P25/P75 de tempo_decisao
        # SELECT percentile_cont(0.25) WITHIN GROUP (ORDER BY (metadados->>'time_to_action_ms')::float)
        
        try:
            q_stats = await db.execute(text("""
                WITH user_metrics AS (
                    SELECT 
                        tenant_id,
                        COUNT(CASE WHEN evento = 'essential_view_loaded' THEN 1 END) as views,
                        COUNT(CASE WHEN evento = 'essential_cta_clicked' THEN 1 END) as clicks,
                        COUNT(CASE WHEN evento = 'essential_action_executed' THEN 1 END) as execs,
                        COUNT(CASE WHEN evento = 'advanced_mode_opened' THEN 1 END) as adv_views,
                        AVG((metadados->>'time_to_action_ms')::float) as avg_time
                    FROM ia_ux_telemetria
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY tenant_id
                )
                SELECT 
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (adv_views::float / NULLIF(views, 0) * 100)) as p25_abertura,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (adv_views::float / NULLIF(views, 0) * 100)) as p75_abertura,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (execs::float / NULLIF(views, 0) * 100)) as p25_exec,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (execs::float / NULLIF(views, 0) * 100)) as p75_exec,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_time) as p75_time
                FROM user_metrics
                WHERE views > 5
            """))
            stats = q_stats.mappings().first()
            
            if not stats or stats['p75_exec'] is None:
                return {"status": "skipped", "reason": "Dados insuficientes para recalibração."}

            # 3. Mapeamento de novas métricas (Percentis)
            novos_valores = {
                "confiante_abertura_max": stats['p25_abertura'] or 15.0,
                "confiante_execucao_min": stats['p75_exec'] or 40.0,
                "analitico_abertura_min": stats['p75_abertura'] or 30.0,
                "analitico_tempo_min": stats['p75_time'] or 15000.0,
                "inseguro_execucao_max": stats['p25_exec'] or 15.0
            }

            logs = []
            for chave, novo_valor in novos_valores.items():
                # Busca valor atual
                q = await db.execute(select(IAUXThreshold).where(IAUXThreshold.chave == chave))
                obj = q.scalar_one_or_none()
                
                valor_padrao = configs[chave]
                valor_atual = obj.valor if obj else valor_padrao
                
                # Regra de variação máxima de 5%
                variacao_permitida = valor_atual * 0.05
                delta = novo_valor - valor_atual
                
                if abs(delta) > variacao_permitida:
                    ajuste = variacao_permitida if delta > 0 else -variacao_permitida
                    valor_final = valor_atual + ajuste
                else:
                    valor_final = novo_valor

                # Garante que não fuja muito do padrão (safety limits ex: 50% do original)
                limite_min = valor_padrao * 0.5
                limite_max = valor_padrao * 2.0
                valor_final = max(limite_min, min(limite_max, valor_final))

                if not obj:
                    obj = IAUXThreshold(chave=chave, valor=valor_final, valor_padrao=valor_padrao)
                    db.add(obj)
                else:
                    obj.valor = valor_final
                
                logs.append({
                    "chave": chave,
                    "de": round(valor_atual, 2),
                    "para": round(valor_final, 2),
                    "delta_real": round(delta, 2)
                })

            await db.commit()
            return {"status": "success", "logs": logs}

        except Exception as e:
            await db.rollback()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def obter_explicacao_perfil(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Gera uma explicação amigável sobre a adaptação da IA (Step UX-07)."""
        try:
            perfil_data = await IAUXTelemetryService.obter_perfil_usuario_ia(db, tenant_id, usuario_id)
            perfil = perfil_data["perfil"]
            metadados = perfil_data["metadados"]

            explicações = {
                "CONFIANTE": "Otimizamos sua interface para agilidade, pois você costuma decidir rapidamente sem precisar de muitos detalhes técnicos.",
                "ANALÍTICO": "Aumentamos a profundidade das informações porque você prefere validar dados e métricas antes de confirmar uma ação.",
                "INSEGURO": "Adicionamos camadas extras de segurança e explicação para apoiar suas decisões de forma mais assistida.",
                "NEUTRO": "A IA está aprendendo seu ritmo para ajustar a interface conforme suas necessidades."
            }

            try:
                q_th = await db.execute(select(IAUXThreshold))
                thresholds = {th.chave: th.valor for th in q_th.scalars().all()}
            except Exception:
                logger.exception("Erro ao listar thresholds de UX. Retornando lista vazia.")
                thresholds = {}

            return {
                "perfil": perfil,
                "titulo": f"Perfil {perfil.capitalize()}",
                "explicacao": explicações.get(perfil, explicações["NEUTRO"]),
                "metricas_usuario": {
                    "tempo_medio": f"{metadados['tempo_decisao_ms']/1000:.1f}s",
                    "taxa_execucao": f"{metadados['taxa_execucao']:.0f}%",
                    "curiosidade": f"{metadados['taxa_abertura']:.0f}% abertura detalhada"
                },
                "thresholds_referencia": thresholds
            }
        except Exception:
            logger.exception("Erro ao gerar explicação de perfil de UX. Retornando fallback.")
            return IAUXTelemetryService._explicacao_padrao()

    @staticmethod
    async def detectar_friccao_usuario(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        sessao_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detecta sinais de fricção e sugere ações proativas (Step UX-08)."""
        try:
            duas_horas_atras = datetime.now(timezone.utc) - timedelta(hours=2)

            q_session = await db.execute(
                select(IAUXTelemetria)
                .where(and_(
                    IAUXTelemetria.tenant_id == tenant_id,
                    IAUXTelemetria.sessao_id == sessao_id,
                    IAUXTelemetria.created_at >= duas_horas_atras
                ))
                .order_by(desc(IAUXTelemetria.created_at))
                .limit(20)
            )
            eventos = q_session.scalars().all()

            if not eventos:
                return {"friccao": "BAIXA", "nudge": None, "acao": None}

            aberturas_avancado = len([e for e in eventos if e.evento == "advanced_mode_opened"])
            execucoes = len([e for e in eventos if e.evento == "essential_action_executed"])
            visualizacoes = len([e for e in eventos if e.evento == "essential_view_loaded"])

            perfil_data = await IAUXTelemetryService.obter_perfil_usuario_ia(db, tenant_id, usuario_id)
            tempo_medio_perfil = perfil_data["metadados"]["tempo_decisao_ms"]
            tempo_ref = tempo_medio_perfil if tempo_medio_perfil > 0 else 10000.0

            friccao = "BAIXA"
            nudge = None
            acao = None

            if (aberturas_avancado >= 3 or visualizacoes >= 5) and execucoes == 0:
                friccao = "ALTA"
                acao = "simplificar_ui"
            elif aberturas_avancado >= 2 and execucoes == 0:
                friccao = "MEDIA"
                acao = "mostrar_explicacao_extra"

            ultima_view = next((e for e in eventos if e.evento == "essential_view_loaded"), None)
            if ultima_view and execucoes == 0:
                tempo_decorrido_ms = (datetime.now(timezone.utc) - ultima_view.created_at).total_seconds() * 1000
                if tempo_decorrido_ms > (tempo_ref * 2.5):
                    friccao = "ALTA"
                    acao = "simplificar_ui"
                elif tempo_decorrido_ms > (tempo_ref * 1.5):
                    if friccao != "ALTA":
                        friccao = "MEDIA"
                        acao = "reforçar_seguranca"

            if friccao != "BAIXA":
                contexto_recente = await IAUXTelemetryService.obter_contexto_decisao_recente(db, tenant_id, usuario_id)
                nudge = IAUXTelemetryService.gerar_mensagem_adaptada(
                    perfil=perfil_data["perfil"],
                    contexto="NUDGE_FRICCAO",
                    base_data={"nivel_friccao": friccao},
                    contexto_recente=contexto_recente
                )

            if friccao != "BAIXA":
                try:
                    await IAUXTelemetryService.track_evento(
                        db, tenant_id, "friccao_detectada", "SISTEMA",
                        usuario_id=usuario_id, sessao_id=sessao_id,
                        metadados={"nivel": friccao, "nudge": nudge, "acao": acao, "perfil": perfil_data["perfil"]}
                    )
                except Exception:
                    logger.exception("Erro ao registrar evento de fricção. Seguindo sem persistência.")

            return {
                "friccao": friccao,
                "nudge": nudge,
                "acao": acao,
                "perfil": perfil_data["perfil"],
                "contexto": {
                    "aberturas_avancado": aberturas_avancado,
                    "tempo_decorrido_ms": round((datetime.now(timezone.utc) - eventos[0].created_at).total_seconds() * 1000, 2) if eventos else 0
                }
            }
        except Exception:
            logger.exception("Erro ao detectar fricção de UX. Retornando estado neutro.")
            return {"friccao": "BAIXA", "nudge": None, "acao": None, "perfil": "NEUTRO", "contexto": {"aberturas_avancado": 0, "tempo_decorrido_ms": 0}}

    @staticmethod
    async def obter_contexto_decisao_recente(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None,
        limite: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recupera as decisões recentes para manter continuidade no raciocínio (Step UX-10).
        Considera ações executadas, aberturas de modo avançado e alertas emitidos.
        """
        try:
            inicio = datetime.now(timezone.utc) - timedelta(days=7)

            # Filtro base
            filtros = [
                IAUXTelemetria.tenant_id == tenant_id,
                IAUXTelemetria.evento.in_([
                    "essential_action_executed",
                    "advanced_mode_opened",
                    "alerta_ia_emitido",
                    "simulacao_ia_concluida",
                    "essential_view_loaded"
                ]),
                IAUXTelemetria.created_at >= inicio
            ]

            if usuario_id:
                filtros.append(IAUXTelemetria.usuario_id == usuario_id)

            q = await db.execute(
                select(IAUXTelemetria)
                .where(and_(*filtros))
                .order_by(desc(IAUXTelemetria.created_at))
                .limit(limite)
            )
            eventos = q.scalars().all()

            contexto = []
            for e in eventos:
                contexto.append({
                    "evento": e.evento,
                    "timestamp": e.created_at,
                    "metadados": e.metadados,
                    "modo": e.modo
                })

            return contexto
        except Exception:
            logger.exception("Erro ao obter contexto recente de UX. Retornando lista vazia.")
            return []

    @staticmethod
    async def calcular_progresso_usuario_ia(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Calcula a evolução do usuário no uso da IA (Step UX-11)."""
        try:
            hoje = datetime.now(timezone.utc)
            inicio_atual = hoje - timedelta(days=7)
            inicio_anterior = hoje - timedelta(days=14)
            fim_anterior = inicio_atual

            p_atual = await IAUXTelemetryService.obter_perfil_usuario_ia(db, tenant_id, usuario_id, inicio=inicio_atual)
            m_atual = await IAUXTelemetryService.obter_metricas(db, tenant_id, inicio=inicio_atual)

            q_roi_atual = await db.execute(
                text("""
                    SELECT SUM((metadados->>'impacto_valor')::float)
                    FROM ia_ux_telemetria
                    WHERE tenant_id = :tenant_id
                    AND evento = 'essential_action_executed'
                    AND created_at >= :inicio
                    AND metadados->>'impacto_valor' IS NOT NULL
                """),
                {"tenant_id": tenant_id, "inicio": inicio_atual}
            )
            roi_atual = q_roi_atual.scalar() or 0.0

            p_anterior = await IAUXTelemetryService.obter_perfil_usuario_ia(db, tenant_id, usuario_id, inicio=inicio_anterior, fim=fim_anterior)
            m_anterior = await IAUXTelemetryService.obter_metricas(db, tenant_id, inicio=inicio_anterior, fim=fim_anterior)

            q_roi_ant = await db.execute(
                text("""
                    SELECT SUM((metadados->>'impacto_valor')::float)
                    FROM ia_ux_telemetria
                    WHERE tenant_id = :tenant_id
                    AND evento = 'essential_action_executed'
                    AND created_at >= :inicio AND created_at < :fim
                    AND metadados->>'impacto_valor' IS NOT NULL
                """),
                {"tenant_id": tenant_id, "inicio": inicio_anterior, "fim": fim_anterior}
            )
            roi_anterior = q_roi_ant.scalar() or 0.0

            tempo_atual = m_atual["resumo_geral"]["tempo_medio_decisao_ms"]
            tempo_anterior = m_anterior["resumo_geral"]["tempo_medio_decisao_ms"]
            taxa_atual = m_atual["funil"]["taxa_conversao_execucao"]
            taxa_anterior = m_anterior["funil"]["taxa_conversao_execucao"]

            def calc_melhoria(atual, anterior, inverter=False):
                if anterior <= 0:
                    return 0
                delta = ((atual - anterior) / anterior) * 100
                return round(-delta if inverter else delta, 1)

            progresso = {
                "tempo_decisao": {
                    "atual": f"{tempo_atual/1000:.1f}s",
                    "melhoria": calc_melhoria(tempo_atual, tempo_anterior, inverter=True),
                    "status": "EVOLUINDO" if tempo_atual < tempo_anterior and tempo_anterior > 0 else "ESTÁVEL"
                },
                "taxa_execucao": {
                    "atual": f"{taxa_atual:.0f}%",
                    "melhoria": calc_melhoria(taxa_atual, taxa_anterior),
                    "status": "EVOLUINDO" if taxa_atual > taxa_anterior else "ESTÁVEL"
                },
                "roi": {
                    "total": f"R$ {roi_atual:,.2f}",
                    "melhoria": calc_melhoria(roi_atual, roi_anterior),
                    "status": "CRESCENTE" if roi_atual > roi_anterior else "ESTÁVEL"
                },
                "perfil": {
                    "atual": p_atual["perfil"],
                    "anterior": p_anterior["perfil"],
                    "evoluiu": p_atual["perfil"] != p_anterior["perfil"]
                }
            }

            destaque = "Você está mantendo uma operação estável com o Copiloto."
            if progresso["tempo_decisao"]["melhoria"] > 10:
                destaque = f"Incrível! Você está decidindo {progresso['tempo_decisao']['melhoria']}% mais rápido que na semana passada."
            elif progresso["roi"]["melhoria"] > 5:
                destaque = f"Seu ROI com as decisões de IA cresceu {progresso['roi']['melhoria']}% este período."
            elif progresso["perfil"]["evoluiu"]:
                destaque = f"Evolução detectada: Seu perfil mudou de {p_anterior['perfil']} para {p_atual['perfil']}."

            return {
                "progresso": progresso,
                "mensagem_destaque": destaque,
                "periodo": "Últimos 7 dias vs período anterior"
            }
        except Exception:
            logger.exception("Erro ao calcular progresso do usuário em UX. Retornando fallback.")
            return IAUXTelemetryService._progresso_padrao()
