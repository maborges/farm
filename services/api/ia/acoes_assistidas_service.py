import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from ia.models import IAAcaoAssistidaHistorico

class AcaoAssistidaService:
    @staticmethod
    async def registrar_acao(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        origem: str,
        tipo_acao: str,
        origem_id: Optional[uuid.UUID] = None,
        usuario_id: Optional[uuid.UUID] = None,
        parametros_json: Optional[dict] = None,
        metodo_execucao: str = "ASSISTIDA",
        impacto_valor: Optional[Decimal] = None
    ) -> IAAcaoAssistidaHistorico:
        """Registra o início de uma ação assistida pela IA (Step 201/210)."""
        acao = IAAcaoAssistidaHistorico(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            origem=origem,
            origem_id=origem_id,
            tipo_acao=tipo_acao,
            parametros_json=parametros_json,
            metodo_execucao=metodo_execucao,
            impacto_valor=impacto_valor
        )
        session.add(acao)
        await session.flush()
        return acao

    @staticmethod
    async def concluir_acao(
        session: AsyncSession,
        acao_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> bool:
        """Marca uma ação assistida como concluída com sucesso pelo usuário (Step 201)."""
        stmt = select(IAAcaoAssistidaHistorico).where(
            IAAcaoAssistidaHistorico.id == acao_id,
            IAAcaoAssistidaHistorico.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        acao = result.scalar_one_or_none()
        
        if not acao:
            return False
            
        if not acao.concluida:
            acao.concluida = True
            acao.concluida_em = datetime.now(timezone.utc)
            await session.flush()

            # Telemetria UX: Se a ação veio do contexto ESSENCIAL, registra execução
            if acao.parametros_json and acao.parametros_json.get("ux_modo") == "ESSENCIAL":
                from ia.ux_telemetry_service import IAUXTelemetryService
                await IAUXTelemetryService.track_evento(
                    db=session,
                    tenant_id=tenant_id,
                    evento="essential_action_executed",
                    modo="ESSENCIAL",
                    usuario_id=acao.usuario_id,
                    metadados={
                        "acao_id": str(acao_id),
                        "tipo_acao": acao.tipo_acao
                    }
                )
            
        return True

    @staticmethod
    async def reverter_acao(
        session: AsyncSession,
        acao_id: uuid.UUID,
        tenant_id: uuid.UUID
    ) -> bool:
        """Marca uma ação automática como revertida pelo usuário (Step 211)."""
        stmt = select(IAAcaoAssistidaHistorico).where(
            IAAcaoAssistidaHistorico.id == acao_id,
            IAAcaoAssistidaHistorico.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        acao = result.scalar_one_or_none()
        
        if not acao:
            return False
            
        if not acao.revertida:
            acao.revertida = True
            acao.revertida_em = datetime.now(timezone.utc)
            await session.flush()
            
        return True

    @staticmethod
    async def obter_metricas(
        session: AsyncSession,
        tenant_id: uuid.UUID
    ) -> dict:
        """Calcula métricas de eficiência das ações assistidas para o tenant (Step 201)."""
        stmt = select(
            func.count(IAAcaoAssistidaHistorico.id).label("total_executadas"),
            func.count(case((IAAcaoAssistidaHistorico.concluida == True, 1))).label("total_concluidas"),
            func.avg(
                case(
                    (IAAcaoAssistidaHistorico.concluida == True, 
                     func.extract('epoch', IAAcaoAssistidaHistorico.concluida_em - IAAcaoAssistidaHistorico.created_at))
                )
            ).label("tempo_medio_segundos")
        ).where(IAAcaoAssistidaHistorico.tenant_id == tenant_id)
        
        result = await session.execute(stmt)
        row = result.one()
        
        total_executadas = row.total_executadas or 0
        total_concluidas = row.total_concluidas or 0
        taxa_conclusao = (total_concluidas / total_executadas * 100) if total_executadas > 0 else 0
        tempo_medio_minutos = (row.tempo_medio_segundos / 60) if row.tempo_medio_segundos else 0
        
        return {
            "total_executadas": total_executadas,
            "total_concluidas": total_concluidas,
            "taxa_conclusao": round(taxa_conclusao, 2),
            "tempo_medio_conclusao_minutos": round(tempo_medio_minutos, 2)
        }
