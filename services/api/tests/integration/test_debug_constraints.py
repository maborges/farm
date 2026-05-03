import pytest
import uuid
import sqlalchemy as sa
from sqlalchemy import text

@pytest.mark.asyncio
async def test_debug_constraints(session):
    # Print all constraints for compras_cotacoes from within the test environment
    res = await session.execute(text("""
        SELECT n.nspname, conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        JOIN pg_class cl ON cl.oid = c.conrelid
        WHERE cl.relname = 'compras_cotacoes'
    """))
    print("\nConstraints found in test:")
    for row in res.all():
        print(row)
        
    res_idx = await session.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'compras_cotacoes'
    """))
    print("\nIndexes found in test:")
    for row in res_idx.all():
        print(row)
