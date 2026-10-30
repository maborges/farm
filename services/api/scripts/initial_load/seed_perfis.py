"""Carga idempotente dos cinco perfis globais aprovados para implantação."""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_ROOT = os.path.dirname(SCRIPTS_DIR)
for import_root in (SCRIPTS_DIR, API_ROOT):
    if import_root not in sys.path:
        sys.path.insert(0, import_root)

from sqlalchemy import select

from core.database import async_session_maker
from core.models.auth import PerfilAcesso


CREATED_AT = datetime(2026, 4, 2, 3, 9, 21, 489000, tzinfo=timezone(timedelta(hours=-3)))

PERFIS_PADRAO = (
    {
        "id": UUID("671656ad-1e32-4244-a2d8-0e4dbbddd072"),
        "nome": "Owner",
        "permissoes": {"*": "*"},
        "descricao": "Acesso total ao tenant",
    },
    {
        "id": UUID("c703b9dd-ac1b-49f9-9aae-eb8efca7e7bf"),
        "nome": "Agrônomo",
        "permissoes": {"agricola": "write", "pecuaria": "read", "financeiro": "read"},
        "descricao": "Gestão agrícola e monitoramento",
    },
    {
        "id": UUID("c14116ef-b777-4e06-89cc-f322c9c6ddab"),
        "nome": "Operador",
        "permissoes": {"agricola": "write", "pecuaria": "write", "financeiro": "none"},
        "descricao": "Registro de operações de campo",
    },
    {
        "id": UUID("f4e174ed-0365-411b-acaf-1e91af20fd5a"),
        "nome": "Consultor",
        "permissoes": {"agricola": "read", "pecuaria": "read", "financeiro": "read"},
        "descricao": "Apenas leitura para consultoria",
    },
    {
        "id": UUID("3cacba5a-6635-4912-821a-05e28e9fffd9"),
        "nome": "Administrador",
        "permissoes": {
            "agricola": "write",
            "pecuaria": "write",
            "financeiro": "write",
            "operacional": "write",
            "rh": "write",
            "relatorios": "write",
            "configuracoes": "write",
            "ambiental": "write",
        },
        "descricao": "Acesso administrativo completo",
    },
)


async def seed_perfis() -> None:
    async with async_session_maker() as session:
        criados = 0
        atualizados = 0

        for perfil_data in PERFIS_PADRAO:
            perfil = await session.get(PerfilAcesso, perfil_data["id"])
            if perfil is None:
                conflito = await session.scalar(
                    select(PerfilAcesso.id).where(
                        PerfilAcesso.tenant_id.is_(None),
                        PerfilAcesso.nome == perfil_data["nome"],
                    )
                )
                if conflito is not None:
                    raise ValueError(
                        "Já existe perfil global com o nome "
                        f"{perfil_data['nome']!r} e ID diferente do contrato de implantação."
                    )
                perfil = PerfilAcesso(
                    id=perfil_data["id"],
                    tenant_id=None,
                    nome=perfil_data["nome"],
                    is_custom=False,
                    permissoes=perfil_data["permissoes"],
                    created_at=CREATED_AT,
                    descricao=perfil_data["descricao"],
                )
                session.add(perfil)
                criados += 1
            else:
                if perfil.tenant_id is not None:
                    raise ValueError(
                        f"O ID reservado ao perfil global {perfil_data['nome']!r} "
                        "já pertence a um perfil de tenant."
                    )
                perfil.nome = perfil_data["nome"]
                perfil.is_custom = False
                perfil.permissoes = perfil_data["permissoes"]
                perfil.descricao = perfil_data["descricao"]
                atualizados += 1

        await session.commit()
        print(f"Perfis globais: {criados} criados, {atualizados} atualizados.")


if __name__ == "__main__":
    asyncio.run(seed_perfis())
