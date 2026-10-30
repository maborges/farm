#!/usr/bin/env python3
"""
Seed para criar estágios padrão do CRM.

Cria um pipeline comercial padrão com as seguintes colunas:
1. Prospecção
2. Qualificação
3. Proposta
4. Negociação
5. Fechamento
"""
import asyncio

from sqlalchemy import select

from core.database import async_session_maker
from core.models.crm import PipelineEstagio

# Dados dos estágios padrão
ESTAGIOS_PADRAO = [
    {
        "nome": "Prospecção",
        "cor": "#3b82f6",  # Blue
        "ordem": 1,
    },
    {
        "nome": "Qualificação",
        "cor": "#8b5cf6",  # Purple
        "ordem": 2,
    },
    {
        "nome": "Proposta",
        "cor": "#f59e0b",  # Amber
        "ordem": 3,
    },
    {
        "nome": "Negociação",
        "cor": "#ec4899",  # Pink
        "ordem": 4,
    },
    {
        "nome": "Fechamento",
        "cor": "#10b981",  # Green
        "ordem": 5,
    },
]


async def seed_estagios_crm(session):
    """Cria os estágios globais padrão sem duplicar nomes já cadastrados."""
    existing_names = set(
        (await session.execute(select(PipelineEstagio.nome))).scalars().all()
    )
    inserted = 0
    for dados in ESTAGIOS_PADRAO:
        if dados["nome"] in existing_names:
            continue
        session.add(
            PipelineEstagio(
                nome=dados["nome"],
                cor=dados["cor"],
                ordem=dados["ordem"],
                ativo=True,
            )
        )
        existing_names.add(dados["nome"])
        inserted += 1

    await session.commit()
    return inserted


async def seed():
    """Cria estágios padrão do CRM usando a sessão configurada pela API."""
    async with async_session_maker() as session:
        inserted = await seed_estagios_crm(session)
        print(f"Seed concluído: {inserted} estágios de CRM inseridos.")


if __name__ == "__main__":
    asyncio.run(seed())
