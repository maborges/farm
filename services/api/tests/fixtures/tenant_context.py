import pytest
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def tenant_session(session: AsyncSession, tenant_id: UUID) -> AsyncSession:
    """
    Sessão do SQLAlchemy configurada com o tenant atual (RLS bypass limitador).
    Necessário para testes envolvendo tabelas com Row-Level Security ativado,
    como 'operational_alerts' ou 'registro_clima'.
    """
    # Define o tenant_id na sessão do banco para a transação atual
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))
    
    yield session
    
    # Limpa a configuração (opcional se a sessão realiza rollback automático)
    await session.execute(text("RESET app.current_tenant_id;"))
