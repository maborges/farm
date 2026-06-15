import asyncio
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database import async_session_maker
from core.models.tenant import Tenant
from core.models.auth import Usuario
from core.cadastros.pessoas.models import Pessoa

TENANT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
FAZENDA_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
USER_ID    = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")

async def setup():
    async with async_session_maker() as session:
        t = await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))
        if not t.scalar_one_or_none():
            tenant = Tenant(id=TENANT_ID, nome='Tenant Teste', ativo=True)
            session.add(tenant)
            
        u = await session.execute(select(Usuario).where(Usuario.id == USER_ID))
        if not u.scalar_one_or_none():
            user = Usuario(id=USER_ID, email='admin@teste.com', username='admin_teste', senha_hash='xyz', ativo=True, is_superuser=True)
            session.add(user)
            
        p = await session.execute(select(Pessoa).where(Pessoa.id == USER_ID))
        if not p.scalar_one_or_none():
            pessoa = Pessoa(id=USER_ID, tenant_id=TENANT_ID, tipo="PF", nome_exibicao="Admin Teste", base_legal="LEGITIMO_INTERESSE", ativo=True, tags=[], dados_extras={})
            session.add(pessoa)
            
        await session.commit()

if __name__ == "__main__":
    asyncio.run(setup())
