"""Update the synthetic lab identity and create its two named properties."""

import asyncio

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_base
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Apply the requested names only to known laboratory records."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from core.models.tenant import Tenant
        from core.models.unidade_produtiva import UnidadeProdutiva

        tenant = (await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one()
        if tenant.nome not in ("DeepFarms Demonstração", "demonstracao"):
            raise DemoLabTargetError("Unexpected demonstration tenant name")
        if tenant.email_responsavel not in (None, "demonstracao@deepfarms.com.br"):
            raise DemoLabTargetError("Unexpected demonstration tenant email")
        tenant.nome = "demonstracao"
        tenant.email_responsavel = "demonstracao@deepfarms.com.br"
        farm = (
            await session.execute(
                select(UnidadeProdutiva).where(
                    UnidadeProdutiva.id == demo_id("pecuaria/fazenda"),
                    UnidadeProdutiva.tenant_id == TENANT_ID,
                )
            )
        ).scalar_one_or_none()
        if farm:
            if farm.nome not in ("Fazenda Modelo Pecuária", "Fazenda Modelo 2"):
                raise DemoLabTargetError("Unexpected livestock property name")
            farm.nome = "Fazenda Modelo 2"
        await session.flush()
        await ensure_base(session, "cafe")
        await ensure_base(session, "pecuaria")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(load())
    print("Laboratory demonstration identity and properties configured")
