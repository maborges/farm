import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ia.essential_service import IAEssentialService

# Importar modelos para garantir que o SQLAlchemy inicialize os mappers
from agricola.safras.models import Safra
from agricola.cultivos.models import Cultivo
from financeiro.models.lancamento import LancamentoFinanceiro
from ia.models import IAAlertaHistorico
from core.models.tenant import Tenant
# Usuario é o nome real da classe em core.models.auth
from core.models.auth import Usuario

# Configuração simplificada para teste
DATABASE_URL = "postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_essential_service():
    tenant_id = uuid.UUID("592b906e-0329-44df-8c58-80ca744ae243") 
    safra_id = uuid.UUID("e122e7f7-f0a2-4f4b-a4df-ead9c05e9966")  
    
    async with AsyncSessionLocal() as session:
        print(f"Testando visão essencial para Safra: {safra_id}")
        result = await IAEssentialService.obter_essencial(session, tenant_id, safra_id)
        
        print("\n--- RESULTADO ESSENCIAL ---")
        print(f"Prioridade: {result['prioridade']}")
        print(f"Tipo: {result['tipo']}")
        print(f"Título: {result['titulo']}")
        print(f"Resumo: {result['resumo']}")
        print(f"Ação: {result['acao_label']} -> {result['rota']}")
        print("---------------------------\n")

if __name__ == "__main__":
    asyncio.run(test_essential_service())
