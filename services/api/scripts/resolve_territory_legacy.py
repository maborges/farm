import asyncio
import csv
import uuid
import sys
import argparse
from datetime import date
from typing import Dict, Any, List
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade, NaturezaVinculo
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from imoveis.models.imovel import ImovelRural

async def apply_decision(session: AsyncSession, record: dict, apply: bool = False):
    tenant_id = record.get("tenant_id")
    up_id = record.get("unidade_produtiva_id")
    imovel_id = record.get("imovel_rural_id")
    action = record.get("action")

    if action in ["SKIP", "MANUAL_REVIEW", ""]:
        return "SKIPPED"

    if not all([tenant_id, up_id, imovel_id]):
        raise ValueError("tenant_id, unidade_produtiva_id e imovel_rural_id são obrigatórios.")

    if action == "CREATE_PROPERTY":
        nome = record.get("nome_nova_propriedade")
        justification = record.get("justification")
        reviewed_by = record.get("reviewed_by")

        if not nome or not justification or not reviewed_by:
            raise ValueError("CREATE_PROPERTY requer nome_nova_propriedade, justification e reviewed_by.")
    elif action == "LINK_EXISTING_PROPERTY":
        prop_str = record.get("propriedade_id")
        if not prop_str:
            raise ValueError("LINK_EXISTING_PROPERTY requer propriedade_id.")
    else:
        raise ValueError(f"Action {action} desconhecida.")

    up = await session.get(UnidadeProdutiva, uuid.UUID(up_id))
    if not up:
        raise ValueError(f"UP {up_id} não encontrada")
    
    if str(up.tenant_id) != tenant_id:
        raise ValueError("Tenant mismatch na UP")

    imovel = await session.get(ImovelRural, uuid.UUID(imovel_id))
    if not imovel:
        raise ValueError(f"Imovel {imovel_id} não encontrado")

    if str(imovel.tenant_id) != tenant_id:
        raise ValueError("Tenant mismatch no Imovel")

    propriedade_id = None
    
    if action == "CREATE_PROPERTY":
        nome = record.get("nome_nova_propriedade")
        justification = record.get("justification")
        reviewed_by = record.get("reviewed_by")

        nova_prop = Propriedade(
            tenant_id=up.tenant_id,
            nome=nome,
            cpf_cnpj=up.cpf_cnpj,
            ativo=True
        )
        if apply:
            session.add(nova_prop)
            await session.flush()
        propriedade_id = nova_prop.id

    elif action == "LINK_EXISTING_PROPERTY":
        prop_str = record.get("propriedade_id")
        if not prop_str:
            raise ValueError("LINK_EXISTING_PROPERTY requer propriedade_id.")
        propriedade_id = uuid.UUID(prop_str)
        
        prop_db = await session.get(Propriedade, propriedade_id)
        if not prop_db or str(prop_db.tenant_id) != tenant_id:
            raise ValueError(f"Propriedade {propriedade_id} inválida ou de outro tenant.")
    else:
        raise ValueError(f"Action {action} desconhecida.")

    natureza_str = record.get("tipo_exploracao")
    natureza = NaturezaVinculo.PROPRIA
    if natureza_str:
        if natureza_str == "ARRENDAMENTO": natureza = NaturezaVinculo.ARRENDAMENTO
        elif natureza_str == "PARCERIA": natureza = NaturezaVinculo.PARCERIA
    else:
        if up.tipo_propriedade == "arrendamento": natureza = NaturezaVinculo.ARRENDAMENTO
        elif up.tipo_propriedade == "parceria": natureza = NaturezaVinculo.PARCERIA

    # Verificar se já existe exploração
    stmt_expl = select(ExploracaoRural).where(
        ExploracaoRural.unidade_produtiva_id == up.id,
        ExploracaoRural.propriedade_id == propriedade_id,
        ExploracaoRural.ativo == True
    )
    expl_existente = (await session.execute(stmt_expl)).scalars().first()

    if not expl_existente:
        nova_expl = ExploracaoRural(
            tenant_id=up.tenant_id,
            propriedade_id=propriedade_id,
            unidade_produtiva_id=up.id,
            natureza=natureza,
            data_inicio=date.today(),
            ativo=True
        )
        if apply:
            session.add(nova_expl)
            await session.flush()

    # Contexto RLS
    if apply:
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))
    
    # Check existing PI
    stmt_pi_exists = select(PropriedadeImovel).where(
        PropriedadeImovel.imovel_rural_id == imovel.id,
        PropriedadeImovel.propriedade_id == propriedade_id
    )
    pi_existente = (await session.execute(stmt_pi_exists)).scalars().first()
    if pi_existente:
        return "ALREADY_LINKED"

    # Criar PropriedadeImovel
    if apply:
        stmt_has_principal = select(PropriedadeImovel).where(
            PropriedadeImovel.propriedade_id == propriedade_id,
            PropriedadeImovel.vinculo_principal == True
        )
        has_principal = (await session.execute(stmt_has_principal)).scalars().first() is not None

        novo_vinculo = PropriedadeImovel(
            tenant_id=imovel.tenant_id,
            propriedade_id=propriedade_id,
            imovel_rural_id=imovel.id,
            tipo_vinculo="PROPRIEDADE_PRINCIPAL" if not has_principal else "MATRICULA_ANEXA",
            ativo=True,
            data_inicio=date.today(),
            origem_documental="MIGRACAO_SISTEMICA_01G1",
            vinculo_principal=not has_principal
        )
        session.add(novo_vinculo)
        
    return "APPLIED"


async def resolve_batch(csv_path: str, apply: bool = False):
    path = Path(csv_path)
    if not path.exists():
        print(f"CSV não encontrado: {csv_path}")
        return
        
    records = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
            
    if not records:
        print("CSV vazio!")
        return
        
    print(f"Processando {len(records)} decisões (Modo: {'APPLY' if apply else 'DRY-RUN'})")
    
    sucessos = 0
    erros = 0
    ignorados = 0
    
    async with async_session_maker() as session:
        for i, record in enumerate(records):
            try:
                # Transação por linha
                async with session.begin_nested():
                    resultado = await apply_decision(session, record, apply=apply)
                    if resultado == "SKIPPED":
                        ignorados += 1
                    elif resultado == "ALREADY_LINKED":
                        sucessos += 1
                        print(f"Linha {i+1}: ALREADY_LINKED")
                    else:
                        sucessos += 1
                        print(f"Linha {i+1}: SUCESSO - {resultado}")
            except Exception as e:
                erros += 1
                print(f"Linha {i+1}: ERRO - {e}")
                
        if apply:
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Erro no commit final: {e}")
                
    print("\nResumo Final:")
    print(f"  Sucessos: {sucessos}")
    print(f"  Erros: {erros}")
    print(f"  Ignorados: {ignorados}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aplicador Batch (CSV) de Resolução de Imóveis Legados")
    parser.add_argument("--decisions", type=str, required=True, help="Caminho para o CSV de decisões.")
    parser.add_argument("--apply", action="store_true", help="Aplica no banco (default é dry-run).")
    
    args = parser.parse_args()
    asyncio.run(resolve_batch(args.decisions, args.apply))
