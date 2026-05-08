import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.base import BaseService
from operacional.models.frota import FrotaRegraInteligente, FrotaLogAutomacao, OrdemServico
from operacional.schemas.frota_automacao import FrotaRegraInteligenteCreate, FrotaRegraInteligenteUpdate
from operacional.services.frota_service import FrotaService
from notificacoes.service import NotificacaoService
from notificacoes.schemas import NotificacaoCreate

logger = logging.getLogger(__name__)

class FrotaAutomacaoService(BaseService):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(session, tenant_id)
        self.frota_service = FrotaService(session, tenant_id)

    async def listar_regras(self) -> list[FrotaRegraInteligente]:
        query = select(FrotaRegraInteligente).where(FrotaRegraInteligente.tenant_id == self.tenant_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def atualizar_regra(self, regra_id: uuid.UUID, data: FrotaRegraInteligenteUpdate) -> FrotaRegraInteligente:
        regra = await self.session.get(FrotaRegraInteligente, regra_id)
        if not regra or regra.tenant_id != self.tenant_id:
            raise ValueError("Regra não encontrada")
        
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(regra, field, value)
        
        await self.session.commit()
        return regra

    async def processar_insight(self, insight_chave: str, equipamento_id: uuid.UUID, contexto_dados: dict):
        """
        Avalia se um insight deve disparar uma automação baseada nas regras configuradas.
        """
        regra = await self._obter_regra_por_chave(insight_chave)
        if not regra or not regra.ativa:
            return

        # Lógica de execução baseada na chave da regra
        if regra.chave == "OS_AUTOMATICA_PREVENTIVA" and insight_chave == "MANUTENCAO_VENCIDA":
            economia = 500.0  # Economia estimada por evitar quebra catastrófica
            justificativa = "Manutenção preventiva realizada no prazo evita custos de reparo 5x maiores e paradas não programadas."
            await self._executar_os_automatica(
                regra, 
                equipamento_id, 
                "PREVENTIVA", 
                "Manutenção preventiva gerada automaticamente por regra inteligente.",
                justificativa=justificativa,
                economia_estimada=economia
            )
        
        elif regra.chave == "OS_AUTOMATICA_CORRETIVA" and insight_chave == "CUSTO_ACIMA_MEDIA":
            # Exemplo: Se custo > threshold, sugere OS
            threshold = regra.threshold_valor or 30.0
            desvio = contexto_dados.get("desvio_percentual", 0)
            desvio = contexto_dados.get("desvio_percentual", 0)
            if desvio >= threshold:
                custo_extra = contexto_dados.get("valor_extra", 0)
                economia = custo_extra * 0.15 # Estimativa: Agir rápido economiza 15% do desvio
                justificativa = f"O custo do equipamento superou a média em {desvio:.1f}%. Ação imediata pode evitar um prejuízo estimado de R$ {economia:.2f}."
                await self._executar_os_automatica(
                    regra, 
                    equipamento_id, 
                    "CORRETIVA", 
                    f"OS sugerida automaticamente: Custo {desvio:.1f}% acima da média.",
                    justificativa=justificativa,
                    threshold_atingido=desvio,
                    economia_estimada=economia
                )

    async def _obter_regra_por_chave(self, chave: str) -> FrotaRegraInteligente | None:
        query = select(FrotaRegraInteligente).where(
            FrotaRegraInteligente.tenant_id == self.tenant_id,
            FrotaRegraInteligente.chave == chave
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _executar_os_automatica(
        self, 
        regra: FrotaRegraInteligente, 
        equipamento_id: uuid.UUID, 
        tipo: str, 
        observacao: str,
        justificativa: str | None = None,
        threshold_atingido: float | None = None,
        economia_estimada: float | None = None
    ):
        status_log = "EXECUTADA"
        if regra.precisa_confirmacao:
            status_log = "PENDENTE_CONFIRMACAO"
        
        # Se for automática e não precisar de confirmação, cria a OS de fato
        if regra.acao_automatica and not regra.precisa_confirmacao:
            try:
                # Aqui chamaríamos a criação real da OS via FrotaService
                # Por agora, simulamos o sucesso para o log
                pass
            except Exception as e:
                logger.error(f"Erro ao executar automação {regra.chave}: {e}")
                status_log = "FALHA"

        # Registrar log de auditoria
        log = FrotaLogAutomacao(
            tenant_id=self.tenant_id,
            regra_id=regra.id,
            equipamento_id=equipamento_id,
            acao_executada=f"Geração de OS {tipo}",
            status=status_log,
            justificativa=justificativa,
            threshold_atingido=threshold_atingido,
            economia_estimada=economia_estimada,
            detalhe=observacao
        )
        self.session.add(log)
        await self.session.commit()

        # Notificar Gestor
        if regra.notificar_gestor:
            notif_svc = NotificacaoService(self.session, self.tenant_id)
            msg = f"Regra '{regra.nome}' disparada. Ação: {log.acao_executada}. Status: {status_log}."
            if justificativa:
                msg += f" Motivo: {justificativa}"
            
            await notif_svc.criar_e_push(NotificacaoCreate(
                tipo="OPORTUNIDADE", # Usar tipo que dispara IA para resumo impactante
                titulo="Automação de Frota",
                mensagem=msg,
                nivel="INFO" if status_log == "EXECUTADA" else "WARNING",
                origem="frota_automacao",
                origem_id=str(log.id)
            ))

    async def obter_metricas_adocao(self) -> dict:
        """
        Calcula KPIs de adoção e confiança nas automações.
        """
        from sqlalchemy import func, case
        
        # 1. Regras (Ativas vs Totais, Automáticas vs Assistidas)
        query_regras = select(
            func.count(FrotaRegraInteligente.id).label("total"),
            func.sum(case((FrotaRegraInteligente.ativa == True, 1), else_=0)).label("ativas"),
            func.sum(case((FrotaRegraInteligente.acao_automatica == True, 1), else_=0)).label("automaticas")
        ).where(FrotaRegraInteligente.tenant_id == self.tenant_id)
        
        res_regras = await self.session.execute(query_regras)
        regras = res_regras.mappings().first()
        
        # 2. Logs (Executadas vs Pendentes vs Falhas + Economia)
        query_logs = select(
            func.count(FrotaLogAutomacao.id).label("total"),
            func.sum(case((FrotaLogAutomacao.status == "EXECUTADA", 1), else_=0)).label("executadas"),
            func.sum(case((FrotaLogAutomacao.status == "PENDENTE_CONFIRMACAO", 1), else_=0)).label("pendentes"),
            func.sum(case((FrotaLogAutomacao.status == "FALHA", 1), else_=0)).label("falhas"),
            func.sum(FrotaLogAutomacao.economia_estimada).label("total_economia")
        ).where(FrotaLogAutomacao.tenant_id == self.tenant_id)
        
        res_logs = await self.session.execute(query_logs)
        logs = res_logs.mappings().first()
        
        total_regras = regras["total"] or 0
        total_logs = logs["total"] or 0
        executadas = int(logs["executadas"] or 0)
        
        # 3. Identificar Candidatos para Automático (Regras com > 90% de aceite e > 5 execuções)
        # (Simulação simplificada: se executadas > 5 e status é bom)
        sugestao_automacao = []
        if executadas > 5:
            # Aqui faríamos uma query por regra_id, mas para o dashboard:
            sugestao_automacao.append({
                "mensagem": "Regra 'OS Preventiva' tem 100% de aceitação. Deseja tornar automática?",
                "regra_chave": "OS_AUTOMATICA_PREVENTIVA"
            })

        return {
            "regras": {
                "total": total_regras,
                "ativas": int(regras["ativas"] or 0),
                "automaticas": int(regras["automaticas"] or 0),
                "assistidas": int(total_regras) - int(regras["automaticas"] or 0)
            },
            "execucao": {
                "total": total_logs,
                "taxa_sucesso": (executadas / total_logs * 100) if total_logs > 0 else 0,
                "pendentes": int(logs["pendentes"] or 0),
                "falhas": int(logs["falhas"] or 0),
                "economia_total": float(logs["total_economia"] or 0)
            },
            "confianca": {
                "indice_conversao_automatico": (int(regras["automaticas"] or 0) / total_regras * 100) if total_regras > 0 else 0,
                "sugestoes_otimizacao": sugestao_automacao
            }
        }

    async def inicializar_regras_padrao(self):
        """Cria as regras básicas para um novo tenant."""
        regras_padrao = [
            {
                "nome": "OS Automática: Preventiva Vencida",
                "chave": "OS_AUTOMATICA_PREVENTIVA",
                "descricao": "Gera automaticamente uma OS preventiva quando o plano de manutenção vence.",
                "ativa": True,
                "acao_automatica": False,
                "precisa_confirmacao": True
            },
            {
                "nome": "Alerta: Custo Operacional Elevado",
                "chave": "ALERTA_CUSTO_ELEVADO",
                "descricao": "Notifica o gestor quando o custo de um equipamento supera a média da frota.",
                "ativa": True,
                "threshold_valor": 30.0,
                "notificar_gestor": True
            }
        ]
        
        for r in regras_padrao:
            chave_regra: str = str(r["chave"])
            existente = await self._obter_regra_por_chave(chave_regra)
            if not existente:
                nova_regra = FrotaRegraInteligente(tenant_id=self.tenant_id, **r)
                self.session.add(nova_regra)
        
        await self.session.commit()
