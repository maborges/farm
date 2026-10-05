import asyncio
from core.database import async_session_maker
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from core.models.tenant import Tenant
from sqlalchemy import select
import uuid

async def test():
    async with async_session_maker() as session:
        tenant = (await session.execute(select(Tenant))).scalars().first()
        svc = UnidadeProdutivaService(session, tenant.id)
        
        print("1. Criando UP nova...")
        dados_create = UnidadeProdutivaCreate(
            nome="Fazenda Teste Erro",
            tipo_propriedade="fazenda",
            ativo=True
        )
        u = await svc.create_unidade_produtiva(dados_create)
        await session.commit()
        print(f"UP criada: {u.id}")
        
        print("\n2. Atualizando com os dados da imagem...")
        dados_update = UnidadeProdutivaUpdate(
            codigo_car="SP-3550308-TESTE",
            nirf="1234777",
            ccir="00012355678",
            sigef_codigo="BR-SP-089978-0",
            numero_matricula="11111"
        )
        
        try:
            # Emula a chamada da rota
            u_updated = await svc.update(u.id, dados_update)
            await session.commit()
            print("Update bem sucedido!")
        except Exception as e:
            print(f"ERRO NO UPDATE: {e}")
            await session.rollback()
            return
            
        print("\n3. Fazendo GET para ver o que a tela carrega...")
        u_get = await svc.get(u.id)
        print(f"GET codigo_car: {u_get.codigo_car}")
        print(f"GET nirf: {u_get.nirf}")
        print(f"GET ccir: {u_get.ccir}")
        print(f"GET sigef_codigo: {u_get.sigef_codigo}")
        print(f"GET numero_matricula: {u_get.numero_matricula}")

asyncio.run(test())
