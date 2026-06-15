import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger
import uuid
import httpx

async def run():
    from core.database import async_session_maker
    from operacional.schemas.qualidade import QualidadeProtocoloCreate
    from operacional.services.qualidade import QualidadeService
    
    # We need a token. Let's just try to insert via the service directly.
    async with async_session_maker() as db:
        # Get a tenant_id and a user_id from the DB to test
        from sqlalchemy import text
        result = await db.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant_id = result.scalar()
        result = await db.execute(text("SELECT id FROM usuarios LIMIT 1"))
        user_id = result.scalar()
        
        print(f"Tenant: {tenant_id}, User: {user_id}")
        
        payload = QualidadeProtocoloCreate(
            nome="Soja Especial Test",
            criterios=[
                {
                    "nome": "Umidade",
                    "tipo_dado": "NUMERIC",
                    "unidade": "%",
                    "valor_padrao": 14.0,
                    "regra_ajuste_json": {
                        "type": "DISCOUNT_WEIGHT",
                        "trigger": "ABOVE_STANDARD"
                    }
                }
            ]
        )
        
        try:
            proto = await QualidadeService.create_protocolo(db, tenant_id, user_id, payload)
            print("Protocolo created:", proto.id)
            
            from operacional.schemas.qualidade import QualidadeLaudoCreate, QualidadeResultadoCreate, QualidadeLaudoStatusUpdate
            
            laudo_payload = QualidadeLaudoCreate(
                protocolo_id=proto.id,
                resultados=[
                    QualidadeResultadoCreate(
                        criterio_id=proto.criterios[0].id,
                        valor_numerico=15.5
                    )
                ]
            )
            laudo = await QualidadeService.create_laudo(db, tenant_id, user_id, laudo_payload)
            print("Laudo created:", laudo.id)
            
            await QualidadeService.update_laudo_status(db, tenant_id, user_id, laudo.id, QualidadeLaudoStatusUpdate(status="APROVADO"))
            print("Laudo approved")
            
            ajustes = await QualidadeService.calcular_ajustes_laudo(db, tenant_id, user_id, laudo.id)
            print("Ajustes calculated:", [(a.tipo, a.valor_numerico, a.motivo) for a in ajustes])
            
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
