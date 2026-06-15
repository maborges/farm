"""
Serviço de cálculo e persistência do Mark-to-Market de Hedge V2.
EXECUTION-HEDGE-04A
"""
from __future__ import annotations

import uuid
import calendar
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.services.audit_service import write_audit_log
from core.cadastros.commodities.models import CotacaoCommodity
from financeiro.hedge.models import ContratoFuturo, HedgePositionSnapshot


class HedgeSnapshotService:
    """
    Responsável por calcular o MTM de Hedge e persistir os snapshots diários.
    
    A fórmula oficial adotada no MVP:
    - VENDA (Short): MtM = (preco_contratado - preco_mercado) * quantidade_aberta
    - COMPRA (Long): MtM = (preco_mercado - preco_contratado) * quantidade_aberta
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _buscar_cotacao(self, commodity_id: uuid.UUID, data_ref: date) -> Optional[CotacaoCommodity]:
        """Busca a cotação exata da data ou a última disponível anterior a ela (fallback D-X)."""
        stmt = (
            select(CotacaoCommodity)
            .where(
                CotacaoCommodity.commodity_id == commodity_id,
                CotacaoCommodity.data <= data_ref
            )
            .order_by(desc(CotacaoCommodity.data))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def gerar_snapshot_contrato(self, contrato: ContratoFuturo, data_ref: date) -> Optional[HedgePositionSnapshot]:
        """
        Gera ou atualiza (UPSERT lógico) o snapshot de um contrato específico para a data informada.
        Se não houver cotação válida, registra auditoria e pula (não zera).
        """
        # Ignorar contratos que não possuem preço ou commodity_id (não deveriam existir, mas por garantia)
        if not contrato.preco_contratado or not contrato.commodity_id:
            return None

        # 1. Localizar cotação válida (D-0 ou fallback)
        cotacao = await self._buscar_cotacao(contrato.commodity_id, data_ref)

        if not cotacao:
            # Não encontrou cotação - registra auditoria e aborta (SKIP)
            logger.warning(f"Sem cotação para commodity {contrato.commodity_id} até {data_ref}. Pula MTM.")
            await write_audit_log(
                self._session,
                tenant_id=contrato.tenant_id,
                user_id=None,
                action="MTM_SKIPPED",
                resource="hedge_position_snapshots_v2",
                resource_id=contrato.id,
                payload_before=None,
                payload_after={
                    "contrato_futuro_id": str(contrato.id),
                    "commodity_id": str(contrato.commodity_id),
                    "data_referencia": data_ref.isoformat()
                }
            )
            return None

        preco_mercado = float(cotacao.preco)
        preco_contratado = float(contrato.preco_contratado)
        quantidade_aberta = float(contrato.quantidade)

        # 2. Aplicar Fórmula Oficial
        if contrato.tipo_posicao == "COMPRA":
            mtm_valor = (preco_mercado - preco_contratado) * quantidade_aberta
        else: # VENDA
            mtm_valor = (preco_contratado - preco_mercado) * quantidade_aberta

        # 3. Executar UPSERT
        # Tenta localizar snapshot existente para atualizar
        stmt = select(HedgePositionSnapshot).where(
            and_(
                HedgePositionSnapshot.tenant_id == contrato.tenant_id,
                HedgePositionSnapshot.contrato_futuro_id == contrato.id,
                HedgePositionSnapshot.data_referencia == data_ref
            )
        )
        existente = (await self._session.execute(stmt)).scalar_one_or_none()

        acao_audit = "SNAPSHOT_UPDATED" if existente else "SNAPSHOT_CREATED"
        agora = datetime.now(timezone.utc)

        if existente:
            existente.quantidade_aberta = quantidade_aberta
            existente.preco_contratado = preco_contratado
            existente.preco_mercado = preco_mercado
            existente.mtm_valor = mtm_valor
            existente.pnl_nao_realizado = mtm_valor
            existente.fonte_preco = cotacao.fonte
            existente.calculado_em = agora
            snapshot = existente
        else:
            snapshot = HedgePositionSnapshot(
                tenant_id=contrato.tenant_id,
                contrato_futuro_id=contrato.id,
                safra_id=contrato.safra_id,
                commodity_id=contrato.commodity_id,
                data_referencia=data_ref,
                quantidade_aberta=quantidade_aberta,
                preco_contratado=preco_contratado,
                preco_mercado=preco_mercado,
                moeda=contrato.unidade or "BRL",  # Simplificação para não crachar caso ausente
                unidade=contrato.unidade or "sc",
                mtm_valor=mtm_valor,
                pnl_nao_realizado=mtm_valor,
                fonte_preco=cotacao.fonte,
                calculado_em=agora
            )
            self._session.add(snapshot)
            # Para garantir que o ID é gerado e usável no audit_log
            await self._session.flush()

        # 4. Registrar Auditoria de Sucesso
        await write_audit_log(
            self._session,
            tenant_id=contrato.tenant_id,
            user_id=None,
            action=acao_audit,
            resource="hedge_position_snapshots_v2",
            resource_id=snapshot.id,
            payload_before=None,
            payload_after={
                "contrato_futuro_id": str(contrato.id),
                "data_referencia": data_ref.isoformat(),
                "preco_mercado_utilizado": preco_mercado,
                "mtm_valor": mtm_valor
            }
        )

        return snapshot

    async def processar_tenant(self, tenant_id: uuid.UUID, data_ref: date) -> int:
        """
        Varre todos os contratos abertos de um tenant e processa o snapshot na data_ref.
        Retorna a quantidade de snapshots gerados com sucesso.
        """
        stmt = select(ContratoFuturo).where(
            ContratoFuturo.tenant_id == tenant_id,
            ContratoFuturo.status == "ABERTO"
        )
        contratos = (await self._session.execute(stmt)).scalars().all()

        sucesso_count = 0
        for contrato in contratos:
            snapshot = await self.gerar_snapshot_contrato(contrato, data_ref)
            if snapshot:
                sucesso_count += 1

        # O caller (job) é responsável por fazer o commit.
        return sucesso_count

    async def _buscar_cotacao_exata(self, commodity_id: uuid.UUID, data_ref: date) -> Optional[CotacaoCommodity]:
        stmt = select(CotacaoCommodity).where(
            CotacaoCommodity.commodity_id == commodity_id,
            CotacaoCommodity.data == data_ref
        ).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def processar_alertas_tenant(self, tenant_id: uuid.UUID, data_ref: date) -> int:
        """
        Processa e emite alertas de risco baseados nos snapshots e contratos de hedge.
        """
        from notificacoes.service import NotificacaoService
        from notificacoes.schemas import NotificacaoCreate
        
        stmt = select(ContratoFuturo).where(
            ContratoFuturo.tenant_id == tenant_id,
            ContratoFuturo.status == "ABERTO"
        )
        contratos = (await self._session.execute(stmt)).scalars().all()
        notif_svc = NotificacaoService(self._session, tenant_id)
        
        alertas_gerados = 0
        
        for contrato in contratos:
            # 1. Alerta de Vencimento
            if contrato.mes_vencimento: # formato YYYY-MM
                try:
                    ano, mes = map(int, contrato.mes_vencimento.split("-"))
                    _, ultimo_dia = calendar.monthrange(ano, mes)
                    data_vencimento = date(ano, mes, ultimo_dia)
                    dias_restantes = (data_vencimento - data_ref).days
                    
                    if dias_restantes in [15, 7]:
                        notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                            tipo="HEDGE_CONTRACT_EXPIRING",
                            titulo=f"Contrato {contrato.commodity} vencendo",
                            mensagem=f"Contrato futuro {contrato.commodity} ({contrato.mes_vencimento}) vence em {dias_restantes} dias.",
                            nivel="INFO",
                            origem="hedge_contrato_futuro",
                            origem_id=f"{contrato.id}_{dias_restantes}d"
                        ))
                        if notif:
                            alertas_gerados += 1
                            await write_audit_log(
                                session=self._session, 
                                tenant_id=tenant_id, 
                                user_id=None, 
                                action="HEDGE_ALERT_CREATED", 
                                resource="hedge_position_snapshots_v2", 
                                resource_id=contrato.id, 
                                payload_before=None, 
                                payload_after={"tipo": "HEDGE_CONTRACT_EXPIRING", "severidade": "BAIXA"}
                            )
                except Exception as e:
                    logger.warning(f"Erro ao calcular vencimento: {e}")

            # 2. Alerta de Cotação Faltante (MTM SKIPPED 2 dias)
            if contrato.commodity_id:
                cotacao_d0 = await self._buscar_cotacao_exata(contrato.commodity_id, data_ref)
                cotacao_d1 = await self._buscar_cotacao_exata(contrato.commodity_id, data_ref - timedelta(days=1))
                
                if not cotacao_d0 and not cotacao_d1:
                    notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                        tipo="HEDGE_MTM_PRICE_MISSING",
                        titulo="Falha no MTM por falta de Cotação",
                        mensagem=f"Não foi possível calcular o MtM do contrato de {contrato.commodity} por ausência de cotação nos últimos 2 dias.",
                        nivel="WARNING",  # MEDIA
                        origem="hedge_contrato_futuro",
                        origem_id=f"{contrato.id}_missing_{data_ref.isoformat()}"
                    ))
                    if notif:
                        alertas_gerados += 1
                        await write_audit_log(
                            session=self._session, 
                            tenant_id=tenant_id, 
                            user_id=None, 
                            action="HEDGE_ALERT_CREATED", 
                            resource="hedge_position_snapshots_v2", 
                            resource_id=contrato.id, 
                            payload_before=None, 
                            payload_after={"tipo": "HEDGE_MTM_PRICE_MISSING", "severidade": "MEDIA"}
                        )

            # 3. Alerta de PnL Crítico (15%)
            stmt_snap = select(HedgePositionSnapshot).where(
                HedgePositionSnapshot.contrato_futuro_id == contrato.id,
                HedgePositionSnapshot.data_referencia == data_ref
            ).limit(1)
            snapshot = (await self._session.execute(stmt_snap)).scalar_one_or_none()
            
            if snapshot and snapshot.pnl_nao_realizado is not None and snapshot.pnl_nao_realizado < 0:
                pnl = float(snapshot.pnl_nao_realizado)
                volume_fin = float(contrato.quantidade) * float(contrato.preco_contratado)
                limite_perda = volume_fin * 0.15
                
                if abs(pnl) > limite_perda:
                    notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                        tipo="HEDGE_CRITICAL_PNL",
                        titulo="Aviso de PnL Crítico",
                        mensagem=f"PnL não realizado ultrapassou o limite de perda configurado.",
                        nivel="DANGER",  # ALTA
                        origem="hedge_contrato_futuro",
                        origem_id=f"{contrato.id}_pnl_critico"
                    ))
                    if notif:
                        alertas_gerados += 1
                        await write_audit_log(
                            session=self._session, 
                            tenant_id=tenant_id, 
                            user_id=None, 
                            action="HEDGE_ALERT_CREATED", 
                            resource="hedge_position_snapshots_v2", 
                            resource_id=contrato.id, 
                            payload_before=None, 
                            payload_after={"tipo": "HEDGE_CRITICAL_PNL", "severidade": "ALTA"}
                        )

        return alertas_gerados

    async def verificar_exposicao_comercial(
        self,
        tenant_id: uuid.UUID,
        data_ref: date,
    ) -> int:
        """Verifica e emite alertas de risco de cobertura comercial do tenant.

        Verifica três condições de risco baseadas na fórmula de exposição:
        - COBERTURA_INSUFICIENTE: percentual_cobertura < 70%
        - SOBRECOBERTURA: percentual_cobertura > 110%
        - VENDA_SEM_LASTRO: comercializações confirmadas > exposição física bruta

        Usa criar_sem_duplicar() para garantir que o mesmo alerta não seja emitido
        mais de uma vez por dia (deduplicação via origem_id).

        Args:
            tenant_id: UUID do tenant.
            data_ref: Data de referência para o alerta (hoje).

        Returns:
            Número de alertas gerados.
        """
        from notificacoes.service import NotificacaoService
        from notificacoes.schemas import NotificacaoCreate
        from financeiro.hedge.service import HedgeExposureService
        from financeiro.hedge.schemas import LIMITE_COBERTURA_MINIMO, LIMITE_COBERTURA_MAXIMO

        notif_svc = NotificacaoService(self._session, tenant_id)
        exp_svc = HedgeExposureService(self._session, tenant_id)
        alertas_gerados = 0

        try:
            exposicao = await exp_svc.calcular_exposicao()
        except Exception as exc:
            logger.warning(f"Tenant {tenant_id}: erro ao calcular exposição para alertas — {exc}")
            return 0

        perc = exposicao.percentual_cobertura
        data_str = data_ref.isoformat()

        # Alerta 1: Cobertura Insuficiente
        if perc < LIMITE_COBERTURA_MINIMO and exposicao.exposicao_liquida_sc > 0:
            notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                tipo="HEDGE_COBERTURA_INSUFICIENTE",
                titulo=f"Risco: Cobertura Financeira Insuficiente ({perc:.1f}%)",
                mensagem=(
                    f"Apenas {perc:.1f}% da exposição física está coberta financeiramente. "
                    f"Exposição aberta: {exposicao.exposicao_aberta_sc:,.0f} sc. "
                    "Considere reforçar a proteção via contratos futuros."
                ),
                nivel="WARNING",
                origem="hedge_exposicao_comercial",
                origem_id=f"cobertura_insuficiente_{data_str}",
                meta={
                    "percentual_cobertura": perc,
                    "exposicao_aberta_sc": exposicao.exposicao_aberta_sc,
                    "classificacao_risco": exposicao.classificacao_risco,
                },
            ))
            if notif:
                alertas_gerados += 1
                await write_audit_log(
                    session=self._session,
                    tenant_id=tenant_id,
                    user_id=None,
                    action="HEDGE_ALERT_CREATED",
                    resource="hedge_exposicao_comercial",
                    resource_id=None,
                    payload_before=None,
                    payload_after={"tipo": "HEDGE_COBERTURA_INSUFICIENTE", "percentual": perc},
                )

        # Alerta 2: Sobrecobertura
        elif perc > LIMITE_COBERTURA_MAXIMO and exposicao.exposicao_liquida_sc > 0:
            notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                tipo="HEDGE_SOBRECOBERTURA",
                titulo=f"Atenção: Sobrecobertura Financeira ({perc:.1f}%)",
                mensagem=(
                    f"A proteção financeira ({perc:.1f}%) excede a exposição física líquida. "
                    f"Contratos hedgeados: {exposicao.ja_hedgeado_sc:,.0f} sc | "
                    f"Exposição física: {exposicao.exposicao_liquida_sc:,.0f} sc. "
                    "Avalie reduzir posição para evitar risco de base."
                ),
                nivel="INFO",
                origem="hedge_exposicao_comercial",
                origem_id=f"sobrecobertura_{data_str}",
                meta={
                    "percentual_cobertura": perc,
                    "excesso_sc": exposicao.ja_hedgeado_sc - exposicao.exposicao_liquida_sc,
                    "classificacao_risco": exposicao.classificacao_risco,
                },
            ))
            if notif:
                alertas_gerados += 1
                await write_audit_log(
                    session=self._session,
                    tenant_id=tenant_id,
                    user_id=None,
                    action="HEDGE_ALERT_CREATED",
                    resource="hedge_exposicao_comercial",
                    resource_id=None,
                    payload_before=None,
                    payload_after={"tipo": "HEDGE_SOBRECOBERTURA", "percentual": perc},
                )

        # Alerta 3: Venda Sem Lastro Físico (ja_vendido > exposicao_bruta)
        if (
            exposicao.ja_vendido_sc > exposicao.exposicao_bruta_sc > 0
        ):
            excesso = exposicao.ja_vendido_sc - exposicao.exposicao_bruta_sc
            notif = await notif_svc.criar_sem_duplicar(NotificacaoCreate(
                tipo="HEDGE_VENDA_SEM_LASTRO",
                titulo="Risco Crítico: Venda Sem Lastro Físico",
                mensagem=(
                    f"As comercializações confirmadas ({exposicao.ja_vendido_sc:,.0f} sc) "
                    f"excedem a exposição física bruta ({exposicao.exposicao_bruta_sc:,.0f} sc) "
                    f"em {excesso:,.0f} sc. Verifique os contratos de comercialização."
                ),
                nivel="DANGER",
                origem="hedge_exposicao_comercial",
                origem_id=f"venda_sem_lastro_{data_str}",
                meta={
                    "ja_vendido_sc": exposicao.ja_vendido_sc,
                    "exposicao_bruta_sc": exposicao.exposicao_bruta_sc,
                    "excesso_sc": excesso,
                },
            ))
            if notif:
                alertas_gerados += 1
                await write_audit_log(
                    session=self._session,
                    tenant_id=tenant_id,
                    user_id=None,
                    action="HEDGE_ALERT_CREATED",
                    resource="hedge_exposicao_comercial",
                    resource_id=None,
                    payload_before=None,
                    payload_after={"tipo": "HEDGE_VENDA_SEM_LASTRO", "excesso_sc": excesso},
                )

        return alertas_gerados

    async def listar_snapshots(
        self,
        tenant_id: uuid.UUID,
        safra_id: Optional[uuid.UUID] = None,
        commodity_id: Optional[uuid.UUID] = None,
        contrato_futuro_id: Optional[uuid.UUID] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[HedgePositionSnapshot]:
        """
        Lista os snapshots de MTM salvos com filtros opcionais.
        Retorna em ordem cronológica reversa (mais recentes primeiro).
        """
        stmt = select(HedgePositionSnapshot).where(
            HedgePositionSnapshot.tenant_id == tenant_id
        )

        if safra_id:
            stmt = stmt.where(HedgePositionSnapshot.safra_id == safra_id)
        if commodity_id:
            stmt = stmt.where(HedgePositionSnapshot.commodity_id == commodity_id)
        if contrato_futuro_id:
            stmt = stmt.where(HedgePositionSnapshot.contrato_futuro_id == contrato_futuro_id)
        if data_inicio:
            stmt = stmt.where(HedgePositionSnapshot.data_referencia >= data_inicio)
        if data_fim:
            stmt = stmt.where(HedgePositionSnapshot.data_referencia <= data_fim)

        stmt = stmt.order_by(desc(HedgePositionSnapshot.data_referencia))
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def reprocessar_snapshots(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        data_inicio: date,
        data_fim: date,
        safra_id: Optional[uuid.UUID] = None,
        commodity_id: Optional[uuid.UUID] = None,
        contrato_futuro_id: Optional[uuid.UUID] = None,
        motivo: str = ""
    ) -> dict:
        """
        Reprocessa o MTM retroativamente para um intervalo de datas e contratos aplicáveis.
        Limite máximo de 31 dias por chamada para evitar sobrecarga.
        """
        if data_fim < data_inicio:
            raise ValueError("data_fim não pode ser menor que data_inicio")
            
        periodo_dias = (data_fim - data_inicio).days + 1
        if periodo_dias > 31:
            raise ValueError("O intervalo máximo permitido para reprocessamento é de 31 dias.")
            
        if not motivo or len(motivo) < 10:
            raise ValueError("Motivo válido é obrigatório (mínimo 10 caracteres).")

        # 1. Localizar Contratos Aplicáveis
        stmt = select(ContratoFuturo).where(
            ContratoFuturo.tenant_id == tenant_id,
            ContratoFuturo.status == "ABERTO"
        )
        if safra_id:
            stmt = stmt.where(ContratoFuturo.safra_id == safra_id)
        if commodity_id:
            stmt = stmt.where(ContratoFuturo.commodity_id == commodity_id)
        if contrato_futuro_id:
            stmt = stmt.where(ContratoFuturo.id == contrato_futuro_id)
            
        contratos = (await self._session.execute(stmt)).scalars().all()
        
        resultado = {
            "processados": 0,
            "criados": 0,
            "atualizados": 0,
            "ignorados_sem_preco": 0,
            "erros": 0,
            "periodo_dias": periodo_dias,
            "filtros_aplicados": {
                "safra_id": str(safra_id) if safra_id else None,
                "commodity_id": str(commodity_id) if commodity_id else None,
                "contrato_futuro_id": str(contrato_futuro_id) if contrato_futuro_id else None
            }
        }

        # 2. Iterar no intervalo de datas e processar
        for i in range(periodo_dias):
            data_ref = data_inicio + timedelta(days=i)
            
            for contrato in contratos:
                try:
                    # Captura quantos haviam antes para saber se atualizou ou criou
                    stmt_check = select(HedgePositionSnapshot).where(
                        and_(
                            HedgePositionSnapshot.tenant_id == tenant_id,
                            HedgePositionSnapshot.contrato_futuro_id == contrato.id,
                            HedgePositionSnapshot.data_referencia == data_ref
                        )
                    )
                    existia = (await self._session.execute(stmt_check)).scalar_one_or_none() is not None
                    
                    snapshot = await self.gerar_snapshot_contrato(contrato, data_ref)
                    if snapshot:
                        resultado["processados"] += 1
                        if existia:
                            resultado["atualizados"] += 1
                        else:
                            resultado["criados"] += 1
                    else:
                        resultado["ignorados_sem_preco"] += 1
                except Exception as e:
                    logger.error(f"Erro ao reprocessar {contrato.id} na data {data_ref}: {str(e)}")
                    resultado["erros"] += 1

        # 3. Auditoria da Ação Administrativa
        await write_audit_log(
            self._session,
            tenant_id=tenant_id,
            user_id=user_id,
            action="HEDGE_MTM_REPROCESS",
            resource="hedge_position_snapshots_v2",
            resource_id=None,
            payload_before=None,
            payload_after={
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                "motivo": motivo,
                "resultado": resultado
            }
        )

        return resultado
