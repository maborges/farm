import asyncio
from core.database import async_session_maker
from integracoes.sankhya.services.legacy_reconciliation import SankhyaLegacyReconciliationService

async def main():
    async with async_session_maker() as session:
        service = SankhyaLegacyReconciliationService(session)
        result = await service.reconcile_tenant('tenant-1')
        print(f'Blocked: {result.blocked}')
        print(f'Block Reasons: {result.block_reasons}')
        print(f'Diff Summary: {result.diff_summary}')

if __name__ == '__main__':
    asyncio.run(main())
