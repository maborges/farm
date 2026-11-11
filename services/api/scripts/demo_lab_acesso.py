"""Provision a lab-only demo login with a private local password file."""

import asyncio
import os
import secrets
import tempfile

from sqlalchemy import select

from scripts.demo_lab_common import TENANT_ID, demo_id, demo_session, ensure_model
from scripts.demo_lab_guard import DemoLabTargetError


async def load():
    """Create the synthetic owner, farm memberships and free lab subscription."""
    async with demo_session() as session:
        from core.model_registry import register_models

        register_models()
        from core.constants import ALL_MODULES
        from core.models.auth import PerfilAcesso, TenantUsuario, UnidadeProdutivaUsuario, Usuario
        from core.models.billing import AssinaturaTenant, PlanoAssinatura
        from core.services.auth_service import hash_password

        email = "demonstracao@deepfarms.com.br"
        user = (
            await session.execute(select(Usuario).where(Usuario.email == email))
        ).scalar_one_or_none()
        if user is not None:
            if user.id != demo_id("acesso/usuario"):
                raise DemoLabTargetError("Demo email belongs to an unexpected user")
            raise DemoLabTargetError("Demo login already exists; password was not reset")
        plan = await ensure_model(
            session,
            PlanoAssinatura,
            demo_id("acesso/plano"),
            {
                "nome": "Plano laboratório demonstração",
                "modulos_inclusos": list(ALL_MODULES),
                "preco_mensal": 0,
                "preco_anual": 0,
                "plan_tier": "ENTERPRISE",
                "max_fazendas": -1,
                "ativo": True,
                "is_free": True,
                "disponivel_site": False,
                "disponivel_crm": False,
            },
        )
        await ensure_model(
            session,
            AssinaturaTenant,
            demo_id("acesso/assinatura"),
            {
                "tenant_id": TENANT_ID,
                "plano_id": plan.id,
                "tipo_assinatura": "TENANT",
                "status": "ATIVA",
                "usuarios_contratados": 2,
            },
        )
        profile = await ensure_model(
            session,
            PerfilAcesso,
            demo_id("acesso/perfil"),
            {
                "tenant_id": TENANT_ID,
                "nome": "owner",
                "is_custom": True,
                "permissoes": {},
            },
        )
        password = secrets.token_urlsafe(24)
        fd, path = tempfile.mkstemp(prefix="deepfarms-demo-lab-", suffix=".txt", dir="/tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(f"Usuário: {email}\nSenha: {password}\n")
            user = Usuario(
                id=demo_id("acesso/usuario"),
                email=email,
                username="demonstracao",
                nome_completo="Demonstração",
                senha_hash=hash_password(password),
                ativo=True,
                is_superuser=False,
            )
            session.add(user)
            await session.flush()
            await ensure_model(
                session,
                TenantUsuario,
                demo_id("acesso/vinculo"),
                {
                    "tenant_id": TENANT_ID,
                    "usuario_id": user.id,
                    "perfil_id": profile.id,
                    "is_owner": True,
                    "status": "ATIVO",
                },
            )
            for name in ("cafe", "pecuaria"):
                await ensure_model(
                    session,
                    UnidadeProdutivaUsuario,
                    demo_id("acesso/" + name),
                    {
                        "tenant_id": TENANT_ID,
                        "usuario_id": user.id,
                        "unidade_produtiva_id": demo_id(name + "/fazenda"),
                    },
                )
            await session.commit()
        except Exception:
            os.unlink(path)
            raise
        print(f"Local credential file: {path}")


if __name__ == "__main__":
    asyncio.run(load())
