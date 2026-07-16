import asyncio
import argparse
import json
import uuid
import sys
from datetime import date
from typing import Dict, Any, List
from collections import Counter
from pathlib import Path

from sqlalchemy import select, func, and_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from imoveis.models.imovel import ImovelRural
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade, NaturezaVinculo
from core.cadastros.propriedade_imovel.models import PropriedadeImovel


async def backfill_territorial_01f(
    apply: bool = False,
    tenant_id: str = None,
    limit: int = None,
    output_report: str = "reports/backfill_01f_report.json"
):
    results: List[Dict[str, Any]] = []
    stats = Counter()

    async with async_session_maker() as session:
        # Busca todas as Unidades Produtivas que não possuem ExploracaoRural
        stmt_ups = select(UnidadeProdutiva).outerjoin(
            ExploracaoRural, ExploracaoRural.unidade_produtiva_id == UnidadeProdutiva.id
        ).where(ExploracaoRural.id == None)

        if tenant_id:
            stmt_ups = stmt_ups.where(UnidadeProdutiva.tenant_id == uuid.UUID(tenant_id))

        if limit:
            stmt_ups = stmt_ups.limit(limit)

        ups_sem_exploracao = (await session.execute(stmt_ups)).scalars().all()

        for up in ups_sem_exploracao:
            record_info = {
                "unidade_produtiva_id": str(up.id),
                "tenant_id": str(up.tenant_id),
                "status": "PENDING",
                "reason": None
            }

            # 1. Verificar Semântica de Negócio (tipo_propriedade)
            natureza = None
            if up.tipo_propriedade in ["fazenda", "sitio", "chacara"]:
                natureza = NaturezaVinculo.PROPRIA
            elif up.tipo_propriedade == "arrendamento":
                natureza = NaturezaVinculo.ARRENDAMENTO
            elif up.tipo_propriedade == "parceria":
                natureza = NaturezaVinculo.PARCERIA
            
            if not natureza:
                record_info["status"] = "MISSING_BUSINESS_SEMANTICS"
                stats["MISSING_BUSINESS_SEMANTICS"] += 1
                results.append(record_info)
                continue

            # 2. Encontrar Propriedade inequivocamente relacionada
            # Vamos tentar encontrar uma propriedade pelo CPF/CNPJ ou Nome no mesmo tenant
            stmt_prop = select(Propriedade).where(
                Propriedade.tenant_id == up.tenant_id
            )
            
            if up.cpf_cnpj:
                stmt_prop = stmt_prop.where(Propriedade.cpf_cnpj == up.cpf_cnpj)
            else:
                stmt_prop = stmt_prop.where(Propriedade.nome == up.nome)
                
            props_candidatas = (await session.execute(stmt_prop)).scalars().all()

            if not props_candidatas:
                record_info["status"] = "MISSING_PROPERTY"
                stats["MISSING_PROPERTY"] += 1
                results.append(record_info)
                continue
                
            if len(props_candidatas) > 1:
                record_info["status"] = "MULTIPLE_PROPERTY_CANDIDATES"
                stats["MULTIPLE_PROPERTY_CANDIDATES"] += 1
                results.append(record_info)
                continue

            propriedade = props_candidatas[0]
            
            # Verificamos se já existe exploração ativa equivalente
            stmt_exist = select(ExploracaoRural).where(
                ExploracaoRural.unidade_produtiva_id == up.id,
                ExploracaoRural.propriedade_id == propriedade.id,
                ExploracaoRural.ativo == True
            )
            existente = (await session.execute(stmt_exist)).scalars().first()
            if existente:
                record_info["status"] = "ALREADY_HAS_EXPLORACAO"
                stats["ALREADY_HAS_EXPLORACAO"] += 1
                results.append(record_info)
                continue
                
            # Tudo certo para criar
            if apply:
                nova_exploracao = ExploracaoRural(
                    tenant_id=up.tenant_id,
                    propriedade_id=propriedade.id,
                    unidade_produtiva_id=up.id,
                    natureza=natureza,
                    data_inicio=date.today(),
                    ativo=True
                )
                session.add(nova_exploracao)
                
                status_mapped = f"CAN_CREATE_{natureza.name}"
                record_info["status"] = status_mapped + "_APPLIED"
                stats[status_mapped + "_APPLIED"] += 1
            else:
                status_mapped = f"CAN_CREATE_{natureza.name}"
                record_info["status"] = status_mapped
                stats[status_mapped] += 1
                
            results.append(record_info)
            
        # ==========================================================
        # Segunda Parte: Backfill de Vínculos PropriedadeImovel e Campos Legados
        # ==========================================================
        stmt_imoveis = select(ImovelRural).where(
            ImovelRural.unidade_produtiva_id.isnot(None)
        )
        if tenant_id:
            stmt_imoveis = stmt_imoveis.where(ImovelRural.tenant_id == uuid.UUID(tenant_id))
        
        imoveis = (await session.execute(stmt_imoveis)).scalars().all()
        
        for imovel in imoveis:
            record_info = {
                "imovel_rural_id": str(imovel.id),
                "unidade_produtiva_id": str(imovel.unidade_produtiva_id),
                "tenant_id": str(imovel.tenant_id)
            }
            
            # Puxamos a UP para verificar campos legados vazios no imovel
            up = await session.get(UnidadeProdutiva, imovel.unidade_produtiva_id)
            if up:
                # Regularização dos campos fundiários da UP
                campos_alterados = []
                if not imovel.nirf and up.nirf:
                    imovel.nirf = up.nirf
                    campos_alterados.append("nirf")
                if not imovel.car_numero and up.codigo_car:
                    imovel.car_numero = up.codigo_car
                    campos_alterados.append("car_numero")
                if not imovel.numero_matricula and up.numero_matricula:
                    imovel.numero_matricula = up.numero_matricula
                    campos_alterados.append("numero_matricula")
                if not imovel.ccir_numero and up.ccir:
                    imovel.ccir_numero = up.ccir
                    campos_alterados.append("ccir_numero")
                if not imovel.sigef_codigo and up.sigef_codigo:
                    imovel.sigef_codigo = up.sigef_codigo
                    campos_alterados.append("sigef_codigo")
                    
                if campos_alterados:
                    record_info["legacy_fields_migrated"] = campos_alterados
                    if apply:
                        stats["LEGACY_FIELDS_MIGRATED_APPLIED"] += 1
                    else:
                        stats["LEGACY_FIELDS_MIGRATED"] += 1
            
            # Buscar exploração para ligar à Propriedade
            stmt_expl = select(ExploracaoRural).where(
                ExploracaoRural.unidade_produtiva_id == imovel.unidade_produtiva_id,
                ExploracaoRural.ativo == True
            )
            exploracoes = (await session.execute(stmt_expl)).scalars().all()
            
            if not exploracoes:
                record_info["link_status"] = "NO_EXPLORACAO_RURAL"
                stats["LINK_NO_EXPLORACAO_RURAL"] += 1
                results.append(record_info)
                continue
                
            propriedades_distintas = list(set(e.propriedade_id for e in exploracoes))
            if len(propriedades_distintas) > 1:
                record_info["link_status"] = "MULTIPLE_PROPERTIES"
                stats["LINK_MULTIPLE_PROPERTIES"] += 1
                results.append(record_info)
                continue
                
            propriedade_id = propriedades_distintas[0]
            
            # Verifica consistência / conflito
            stmt_pi = select(PropriedadeImovel).where(
                PropriedadeImovel.imovel_rural_id == imovel.id
            )
            pis_existentes = (await session.execute(stmt_pi)).scalars().all()
            
            if pis_existentes:
                conflito = False
                for pi in pis_existentes:
                    if pi.propriedade_id != propriedade_id:
                        conflito = True
                        break
                
                if conflito:
                    record_info["link_status"] = "CONFLICT"
                    stats["LINK_CONFLICT"] += 1
                else:
                    record_info["link_status"] = "ALREADY_CANONICAL"
                    stats["LINK_ALREADY_CANONICAL"] += 1
                results.append(record_info)
                continue
                
            # Criação do link
            if apply:
                # Se a propriedade já tem um principal, criamos como secundário
                stmt_has_principal = select(func.count()).where(
                    PropriedadeImovel.propriedade_id == propriedade_id,
                    PropriedadeImovel.vinculo_principal == True
                )
                has_principal = (await session.execute(stmt_has_principal)).scalar() > 0
                
                novo_vinculo = PropriedadeImovel(
                    tenant_id=imovel.tenant_id,
                    propriedade_id=propriedade_id,
                    imovel_rural_id=imovel.id,
                    tipo_vinculo="PROPRIEDADE_PRINCIPAL" if not has_principal else "MATRICULA_ANEXA",
                    ativo=True,
                    data_inicio=date.today(),
                    origem_documental="MIGRACAO_SISTEMICA_01F",
                    vinculo_principal=not has_principal
                )
                session.add(novo_vinculo)
                if has_principal:
                    record_info["link_status"] = "SECONDARY_LINK_CREATED_APPLIED"
                    stats["SECONDARY_LINK_CREATED_APPLIED"] += 1
                else:
                    record_info["link_status"] = "CANONICAL_LINK_CREATED_APPLIED"
                    stats["CANONICAL_LINK_CREATED_APPLIED"] += 1
            else:
                record_info["link_status"] = "CAN_CREATE_LINK"
                stats["CAN_CREATE_LINK"] += 1
                
            results.append(record_info)

        if apply:
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Erro no commit final: {e}")

    # Gera Relatorio
    output_path = Path(output_report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump({
            "mode": "APPLY" if apply else "DRY-RUN",
            "stats": dict(stats),
            "records": results
        }, f, indent=2)
        
    print(f"Relatório gerado em: {output_report}")
    print("Resumo:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TERRITORY-CONVERGENCE-01F Backfill")
    parser.add_argument("--apply", action="store_true", help="Aplica as mudanças no banco de dados. Padrão é dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Executa apenas simulação (Padrão).")
    parser.add_argument("--tenant-id", type=str, help="Filtra por um Tenant ID especifico.")
    parser.add_argument("--limit", type=int, help="Limite de registros a processar.")
    parser.add_argument("--output-report", type=str, default="reports/backfill_01f_report.json", help="Caminho do relatório JSON.")
    
    args = parser.parse_args()
    
    apply = args.apply and not args.dry_run
    
    asyncio.run(backfill_territorial_01f(
        apply=apply,
        tenant_id=args.tenant_id,
        limit=args.limit,
        output_report=args.output_report
    ))
