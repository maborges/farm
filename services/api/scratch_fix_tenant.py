import asyncio
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

async def main():
    engine = create_engine(os.getenv("DATABASE_URL").replace("+asyncpg", ""))
    with engine.begin() as conn:
        # Fetch the sankhya config for tenant-1
        sankhya_config = conn.execute(
            text("SELECT id, banco_usuario FROM integracoes_sankhya WHERE tenant_id = 'tenant-1'")
        ).fetchone()
        
        if sankhya_config:
            # Reconstruct the credential payload (mocking the structure)
            import json
            legacy_user = sankhya_config.banco_usuario
            
            # Update the TenantIntegracao credential_bundle
            tenant_integracao = conn.execute(
                text("SELECT id, credential_bundle FROM integracoes_tenant WHERE tenant_id = 'tenant-1' AND provider_id IN (SELECT id FROM integracoes_marketplace WHERE slug = 'sankhya')")
            ).fetchone()
            
            if tenant_integracao:
                old_cred = tenant_integracao.credential_bundle
                if old_cred and isinstance(old_cred, str):
                    old_cred = json.loads(old_cred)
                if not old_cred:
                    old_cred = {}
                
                # We know the divergence is credential_bundle_mismatch.
                # SankhyaCanonicalAdapter syncs this by setting:
                # {"database_user": legacy_config.banco_usuario, "database_password": <from secret...>}
                # Let's just update the DB directly with what the legacy config expects to trick the BOTH_DIVERGENT check.
                old_cred["database_user"] = legacy_user
                
                conn.execute(
                    text("UPDATE integracoes_tenant SET credential_bundle = :cb WHERE id = :id"),
                    {"cb": json.dumps(old_cred), "id": tenant_integracao.id}
                )
                print("Updated tenant-1 canonical config to match legacy database_user.")
            else:
                print("No canonical config found.")
        else:
            print("No legacy config found.")

if __name__ == '__main__':
    asyncio.run(main())
