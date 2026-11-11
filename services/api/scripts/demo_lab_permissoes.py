"""Grant the demo tenant owner all tenant permissions in the isolated lab."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session
from scripts.demo_lab_guard import DemoLabTargetError


async def grant_demo_owner_permissions() -> None:
    """Repair only the deterministic demo owner profile and verify membership."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from core.models.auth import PerfilAcesso, TenantUsuario

        profile_id = demo_id("acesso/perfil")
        membership = (
            await session.execute(
                select(TenantUsuario).where(
                    TenantUsuario.tenant_id == TENANT_ID,
                    TenantUsuario.usuario_id == demo_id("acesso/usuario"),
                )
            )
        ).scalar_one_or_none()
        if (
            membership is None
            or not membership.is_owner
            or membership.perfil_id != profile_id
        ):
            raise DemoLabTargetError("Demo owner membership does not match the expected profile")

        profile = (
            await session.execute(
                select(PerfilAcesso).where(
                    PerfilAcesso.id == profile_id,
                    PerfilAcesso.tenant_id == TENANT_ID,
                )
            )
        ).scalar_one_or_none()
        if (
            profile is None
            or profile.nome not in {"owner", "demonstracao"}
            or not profile.is_custom
        ):
            raise DemoLabTargetError("Demo owner profile is missing or unexpected")

        profile.nome = "demonstracao"
        # This format is understood by both the API and the web permission gate.
        profile.permissoes = {"granted": ["*"]}
        await session.commit()
        print("Demo owner profile updated with full tenant permissions")


if __name__ == "__main__":
    asyncio.run(grant_demo_owner_permissions())
