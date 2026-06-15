from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from uuid import UUID
from fastapi import HTTPException
from operacional.models.qualidade import QualidadeProtocolo, QualidadeCriterio, QualidadeLaudo, QualidadeResultado, QualidadeAjuste
from operacional.schemas.qualidade import QualidadeProtocoloCreate, QualidadeLaudoCreate, QualidadeLaudoStatusUpdate, QualidadeRomaneioIntegrationResponse
from core.services.audit_service import write_audit_log, _serialize
from core.constants import QUALITY_CREATE, QUALITY_UPDATE, QUALITY_CALC, QUALITY_APPLY_ROMANEIO
from agricola.colheita.models import ProdutoColhido
from agricola.romaneios.models import RomaneioColheita
from agricola.qualidade_resolver import resolver_qualidade_efetiva

class QualidadeService:
    @staticmethod
    async def _sincronizar_produto_colhido_romaneio(
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        romaneio: RomaneioColheita,
    ) -> None:
        result_pc = await session.execute(
            select(ProdutoColhido).where(
                ProdutoColhido.tenant_id == tenant_id,
                ProdutoColhido.romaneio_id == romaneio.id,
            )
        )
        produtos = result_pc.scalars().all()
        if not produtos:
            return

        for produto in produtos:
            efetivo_antes = resolver_qualidade_efetiva(produto, romaneio)
            payload_before = {
                "qualidade_laudo_id": str(efetivo_antes.qualidade_laudo_id) if efetivo_antes.qualidade_laudo_id else None,
                "qualidade_status": efetivo_antes.qualidade_status,
                "peso_desconto_qualidade_kg": float(efetivo_antes.peso_desconto_qualidade_kg),
                "peso_liquido_comercial_kg": efetivo_antes.peso_liquido_comercial_kg,
            }
            produto.qualidade_laudo_id = romaneio.qualidade_laudo_id
            produto.qualidade_status = romaneio.qualidade_status
            produto.peso_desconto_qualidade_kg = romaneio.peso_desconto_qualidade_kg or 0
            produto.peso_liquido_comercial_kg = romaneio.peso_liquido_comercial_kg
            await session.flush()
            efetivo_depois = resolver_qualidade_efetiva(produto, romaneio)
            await write_audit_log(
                session=session,
                tenant_id=tenant_id,
                user_id=user_id,
                action="sync_quality_pc",
                resource="agricola_produtos_colhidos",
                resource_id=produto.id,
                payload_before=payload_before,
                payload_after={
                    "qualidade_laudo_id": str(efetivo_depois.qualidade_laudo_id) if efetivo_depois.qualidade_laudo_id else None,
                    "qualidade_status": efetivo_depois.qualidade_status,
                    "peso_desconto_qualidade_kg": float(efetivo_depois.peso_desconto_qualidade_kg),
                    "peso_liquido_comercial_kg": efetivo_depois.peso_liquido_comercial_kg,
                    "romaneio_id": str(romaneio.id),
                },
            )

    @staticmethod
    async def create_protocolo(session: AsyncSession, tenant_id: UUID, user_id: UUID, data: QualidadeProtocoloCreate) -> QualidadeProtocolo:
        protocolo = QualidadeProtocolo(
            tenant_id=tenant_id,
            nome=data.nome,
            commodity_id=data.commodity_id,
            ativo=data.ativo
        )
        for crit in data.criterios:
            criterio = QualidadeCriterio(
                nome=crit.nome,
                tipo_dado=crit.tipo_dado,
                unidade=crit.unidade,
                min_aceitavel=crit.min_aceitavel,
                max_aceitavel=crit.max_aceitavel,
                valor_padrao=crit.valor_padrao,
                regra_ajuste_json=crit.regra_ajuste_json
            )
            protocolo.criterios.append(criterio)
        
        session.add(protocolo)
        await session.flush()
        
        await write_audit_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            action=QUALITY_CREATE,
            resource="operacional_qualidade_protocolos",
            resource_id=protocolo.id,
            payload_before=None,
            payload_after=_serialize(protocolo)
        )
        
        await session.commit()
        await session.refresh(protocolo)
        return await QualidadeService.get_protocolo(session, tenant_id, protocolo.id)

    @staticmethod
    async def get_protocolo(session: AsyncSession, tenant_id: UUID, protocolo_id: UUID) -> QualidadeProtocolo:
        result = await session.execute(
            select(QualidadeProtocolo)
            .where(QualidadeProtocolo.id == protocolo_id, QualidadeProtocolo.tenant_id == tenant_id)
            .options(selectinload(QualidadeProtocolo.criterios))
        )
        protocolo = result.scalars().first()
        if not protocolo:
            raise HTTPException(status_code=404, detail="Protocolo não encontrado.")
        return protocolo

    @staticmethod
    async def list_protocolos(session: AsyncSession, tenant_id: UUID):
        result = await session.execute(
            select(QualidadeProtocolo)
            .where(QualidadeProtocolo.tenant_id == tenant_id)
            .options(selectinload(QualidadeProtocolo.criterios))
        )
        return result.scalars().all()

    @staticmethod
    async def list_criterios_by_protocolo(session: AsyncSession, tenant_id: UUID, protocolo_id: UUID):
        protocolo = await QualidadeService.get_protocolo(session, tenant_id, protocolo_id)
        return protocolo.criterios

    @staticmethod
    async def create_laudo(session: AsyncSession, tenant_id: UUID, user_id: UUID, data: QualidadeLaudoCreate) -> QualidadeLaudo:
        protocolo = await QualidadeService.get_protocolo(session, tenant_id, data.protocolo_id)
        if not protocolo.ativo:
            raise HTTPException(status_code=400, detail="Não é possível criar laudo para um protocolo inativo.")
            
        if data.romaneio_id:
            from agricola.romaneios.models import RomaneioColheita
            rom_result = await session.execute(select(RomaneioColheita.id).where(RomaneioColheita.id == data.romaneio_id, RomaneioColheita.tenant_id == tenant_id))
            if not rom_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Romaneio não encontrado ou não pertence a este tenant.")
        
        # Validar criterios
        criterios_dict = {c.id: c for c in protocolo.criterios}
        criterios_enviados = set()
        
        for res in data.resultados:
            if res.criterio_id not in criterios_dict:
                raise HTTPException(status_code=400, detail=f"O critério {res.criterio_id} não pertence a este protocolo.")
            if res.criterio_id in criterios_enviados:
                raise HTTPException(status_code=400, detail=f"Critério {res.criterio_id} duplicado no laudo.")
            criterios_enviados.add(res.criterio_id)
            
            criterio_db = criterios_dict[res.criterio_id]
            if criterio_db.tipo_dado == "NUMERIC":
                if res.valor_numerico is None:
                    raise HTTPException(status_code=400, detail=f"O critério {criterio_db.nome} requer um valor_numerico.")
                val = float(res.valor_numerico)
                if criterio_db.min_aceitavel is not None and val < float(criterio_db.min_aceitavel):
                    raise HTTPException(status_code=400, detail=f"O valor para {criterio_db.nome} é menor que o mínimo aceitável ({criterio_db.min_aceitavel}).")
                if criterio_db.max_aceitavel is not None and val > float(criterio_db.max_aceitavel):
                    raise HTTPException(status_code=400, detail=f"O valor para {criterio_db.nome} é maior que o máximo aceitável ({criterio_db.max_aceitavel}).")
            elif criterio_db.tipo_dado in ("ENUM", "BOOLEAN"):
                if not res.valor_texto:
                    raise HTTPException(status_code=400, detail=f"O critério {criterio_db.nome} requer um valor_texto.")
                    
        laudo = QualidadeLaudo(
            tenant_id=tenant_id,
            unidade_produtiva_id=data.unidade_produtiva_id,
            protocolo_id=data.protocolo_id,
            romaneio_id=data.romaneio_id,
            avaliador_id=data.avaliador_id,
            status=data.status
        )
        
        for res in data.resultados:
            resultado = QualidadeResultado(
                criterio_id=res.criterio_id,
                valor_numerico=res.valor_numerico,
                valor_texto=res.valor_texto
            )
            laudo.resultados.append(resultado)
            
        session.add(laudo)
        await session.flush()
        
        await write_audit_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            action=QUALITY_CREATE,
            resource="operacional_qualidade_laudos",
            resource_id=laudo.id,
            payload_before=None,
            payload_after=_serialize(laudo)
        )
        
        await session.commit()
        await session.refresh(laudo)
        return await QualidadeService.get_laudo(session, tenant_id, laudo.id)

    @staticmethod
    async def get_laudo(session: AsyncSession, tenant_id: UUID, laudo_id: UUID) -> QualidadeLaudo:
        result = await session.execute(
            select(QualidadeLaudo)
            .where(QualidadeLaudo.id == laudo_id, QualidadeLaudo.tenant_id == tenant_id)
            .options(selectinload(QualidadeLaudo.resultados), selectinload(QualidadeLaudo.ajustes))
        )
        laudo = result.scalars().first()
        if not laudo:
            raise HTTPException(status_code=404, detail="Laudo não encontrado.")
        return laudo

    @staticmethod
    async def update_laudo_status(session: AsyncSession, tenant_id: UUID, user_id: UUID, laudo_id: UUID, data: QualidadeLaudoStatusUpdate) -> QualidadeLaudo:
        laudo = await QualidadeService.get_laudo(session, tenant_id, laudo_id)
        if laudo.status != "RASCUNHO":
            raise HTTPException(status_code=400, detail="Apenas laudos em RASCUNHO podem ter o status atualizado para APROVADO/REJEITADO.")
            
        payload_before = _serialize(laudo)
        
        laudo.status = data.status
        if data.avaliador_id:
            laudo.avaliador_id = data.avaliador_id
            
        await session.flush()
        
        await write_audit_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            action=QUALITY_UPDATE,
            resource="operacional_qualidade_laudos",
            resource_id=laudo.id,
            payload_before=payload_before,
            payload_after=_serialize(laudo)
        )
        
        await session.commit()
        await session.refresh(laudo)
        return laudo
        
    @staticmethod
    async def list_laudos_by_romaneio(session: AsyncSession, tenant_id: UUID, romaneio_id: UUID):
        result = await session.execute(
            select(QualidadeLaudo)
            .where(QualidadeLaudo.romaneio_id == romaneio_id, QualidadeLaudo.tenant_id == tenant_id)
            .options(selectinload(QualidadeLaudo.resultados))
        )
        return result.scalars().all()

    @staticmethod
    async def calcular_ajustes_laudo(session: AsyncSession, tenant_id: UUID, user_id: UUID, laudo_id: UUID) -> list[QualidadeAjuste]:
        laudo = await QualidadeService.get_laudo(session, tenant_id, laudo_id)
        if laudo.status != "APROVADO":
            raise HTTPException(status_code=400, detail="Apenas laudos APROVADOS podem ter seus ajustes calculados.")
        
        # Carregar protocolo e criterios para pegar a regra
        protocolo = await QualidadeService.get_protocolo(session, tenant_id, laudo.protocolo_id)
        criterios_dict = {c.id: c for c in protocolo.criterios}

        # Idempotência: remover ajustes antigos
        await session.execute(
            delete(QualidadeAjuste)
            .where(QualidadeAjuste.laudo_id == laudo_id, QualidadeAjuste.tenant_id == tenant_id)
        )
        
        novos_ajustes = []
        for res in laudo.resultados:
            criterio = criterios_dict.get(res.criterio_id)
            if not criterio or not criterio.regra_ajuste_json:
                continue
                
            regra = criterio.regra_ajuste_json
            tipo = regra.get("type")
            trigger = regra.get("trigger")
            std_val = regra.get("standard_value")
            rate = regra.get("rate_per_unit", 1.0)
            unit = regra.get("unit")
            
            if criterio.tipo_dado == "NUMERIC" and res.valor_numerico is not None and std_val is not None:
                val = float(res.valor_numerico)
                diff = val - float(std_val)
                adj_value = 0.0
                
                if trigger == "ABOVE_STANDARD" and diff > 0:
                    adj_value = diff * float(rate)
                elif trigger == "BELOW_STANDARD" and diff < 0:
                    adj_value = abs(diff) * float(rate)
                
                if adj_value > 0 or tipo == "REJECTION":
                    # Se for REJECTION e a condição trigou, não depende de diff valorado necessariamente, 
                    # mas para manter simples, consideramos a diff pro REJECTION também ou apenas o fato de bater a trigger.
                    ajuste = QualidadeAjuste(
                        tenant_id=tenant_id,
                        laudo_id=laudo.id,
                        criterio_id=criterio.id,
                        tipo=tipo,
                        valor_numerico=adj_value if tipo != "REJECTION" else val,
                        valor_unidade=unit,
                        motivo=f"Ajuste aplicado pois o valor ({val}) foi {trigger} do padrão ({std_val})",
                        metadata_json={"diff_aplicada": diff},
                        created_by=user_id
                    )
                    novos_ajustes.append(ajuste)
        
        if novos_ajustes:
            session.add_all(novos_ajustes)
        
        await session.flush()
        
        await write_audit_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            action=QUALITY_CALC,
            resource="operacional_qualidade_laudos",
            resource_id=laudo.id,
            payload_before=None,
            payload_after={"quantidade_ajustes": len(novos_ajustes)}
        )
        
        await session.commit()
        return novos_ajustes

    @staticmethod
    async def aplicar_laudo_romaneio(session: AsyncSession, tenant_id: UUID, user_id: UUID, laudo_id: UUID) -> QualidadeRomaneioIntegrationResponse:
        laudo = await QualidadeService.get_laudo(session, tenant_id, laudo_id)
        if laudo.status != "APROVADO":
            raise HTTPException(status_code=400, detail="Apenas laudos APROVADOS podem ser aplicados ao romaneio.")
            
        if not laudo.romaneio_id:
            raise HTTPException(status_code=400, detail="Laudo não está vinculado a nenhum romaneio.")
            
        # Buscar Romaneio
        result_rom = await session.execute(
            select(RomaneioColheita).where(
                RomaneioColheita.id == laudo.romaneio_id,
                RomaneioColheita.tenant_id == tenant_id
            )
        )
        romaneio = result_rom.scalars().first()
        
        if not romaneio:
            raise HTTPException(status_code=404, detail="Romaneio vinculado não encontrado neste tenant.")
            
        # Calcular descontos DISCOUNT_WEIGHT
        peso_desconto_qualidade = 0.0
        tem_rejeicao = False
        
        for ajuste in laudo.ajustes:
            if ajuste.tipo == "DISCOUNT_WEIGHT":
                peso_desconto_qualidade += float(ajuste.valor_numerico)
            elif ajuste.tipo == "REJECTION":
                tem_rejeicao = True
                
        status_qualidade = "REPROVADO" if tem_rejeicao else "APROVADO"
        
        # Calcular peso líquido comercial
        # O padrão é deduzir do peso_liquido_padrao_kg (já descontadas quebras mapa). Se for nulo, usar peso_liquido_kg
        peso_base = romaneio.peso_liquido_padrao_kg if romaneio.peso_liquido_padrao_kg is not None else romaneio.peso_liquido_kg
        if peso_base is None:
             peso_base = 0.0
             
        peso_liquido_comercial = float(peso_base) - peso_desconto_qualidade
        
        estado_anterior = resolver_qualidade_efetiva(romaneio=romaneio)
        payload_before = {
            "qualidade_laudo_id": str(estado_anterior.qualidade_laudo_id) if estado_anterior.qualidade_laudo_id else None,
            "qualidade_status": estado_anterior.qualidade_status,
            "peso_desconto_qualidade_kg": float(estado_anterior.peso_desconto_qualidade_kg),
            "peso_liquido_comercial_kg": estado_anterior.peso_liquido_comercial_kg
        }
        
        romaneio.qualidade_laudo_id = laudo.id
        romaneio.qualidade_status = status_qualidade
        romaneio.peso_desconto_qualidade_kg = peso_desconto_qualidade
        romaneio.peso_liquido_comercial_kg = peso_liquido_comercial

        await QualidadeService._sincronizar_produto_colhido_romaneio(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            romaneio=romaneio,
        )

        estado_depois = resolver_qualidade_efetiva(romaneio=romaneio)
        payload_after = {
            "qualidade_laudo_id": str(estado_depois.qualidade_laudo_id),
            "qualidade_status": estado_depois.qualidade_status,
            "peso_desconto_qualidade_kg": float(estado_depois.peso_desconto_qualidade_kg),
            "peso_liquido_comercial_kg": estado_depois.peso_liquido_comercial_kg
        }
        
        await session.flush()
        
        await write_audit_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            action=QUALITY_APPLY_ROMANEIO,
            resource="romaneios_colheita",
            resource_id=romaneio.id,
            payload_before=payload_before,
            payload_after=payload_after
        )
        
        await session.commit()
        
        return QualidadeRomaneioIntegrationResponse(
            romaneio_id=romaneio.id,
            laudo_id=laudo.id,
            peso_liquido_padrao_kg=float(romaneio.peso_liquido_padrao_kg) if romaneio.peso_liquido_padrao_kg is not None else None,
            peso_liquido_kg=float(romaneio.peso_liquido_kg) if romaneio.peso_liquido_kg is not None else None,
            peso_desconto_qualidade_kg=peso_desconto_qualidade,
            peso_liquido_comercial_kg=peso_liquido_comercial,
            status_qualidade=status_qualidade,
            ajustes_aplicados=len(laudo.ajustes)
        )
