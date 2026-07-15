import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker
from integracoes.sankhya.services.legacy_reconciliation import SankhyaLegacyReconciliationService

async def main():
    async with async_session_maker() as session:
        service = SankhyaLegacyReconciliationService(session)
        snapshot = await service._load_snapshot('tenant-1')
        
        if snapshot.legacy_config:
            # Força o sincronismo do legado para o canônico usando o adapter oficial
            # com password_changed=True para sobreescrever credenciais
            await service.adapter.sync_provider_config(snapshot.legacy_config, password_changed=True)
            await session.commit()
            print("tenant-1: Forced sync with password_changed=True.")
        else:
            print("No legacy config found.")

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
