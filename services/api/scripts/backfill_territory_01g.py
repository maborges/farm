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


async def backfill_territorial_01g(
    apply: bool = False,
    tenant_id: str = None,
    limit: int = None,
    output_report: str = "reports/backfill_01g_report.json"
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
        
        # Pre-fetch ALL properties to memory
        stmt_all_props = select(Propriedade)
        todas_props_db = (await session.execute(stmt_all_props)).scalars().all()
        propriedades_por_tenant = {}
        for p in todas_props_db:
            propriedades_por_tenant.setdefault(p.tenant_id, []).append(p)
            
        # Pre-fetch ALL ExploracaoRural to memory
        stmt_all_expls = select(ExploracaoRural).where(ExploracaoRural.ativo == True)
        todas_expl_db = (await session.execute(stmt_all_expls)).scalars().all()
        expls_por_up = {}
        for e in todas_expl_db:
            expls_por_up.setdefault(e.unidade_produtiva_id, []).append(e)

        for up in ups_sem_exploracao:
            record_info = {
                "unidade_produtiva_id": str(up.id),
                "tenant_id": str(up.tenant_id),
                "status": "PENDING",
                "reason": None
            }

            natureza = None
            if up.tipo_propriedade in ["fazenda", "sitio", "chacara"]:
                natureza = NaturezaVinculo.PROPRIA
            elif up.tipo_propriedade == "arrendamento":
                natureza = NaturezaVinculo.ARRENDAMENTO
            elif up.tipo_propriedade == "parceria":
                natureza = NaturezaVinculo.PARCERIA
            
            if not natureza:
                record_info["status"] = "MANUAL_REVIEW_REQUIRED"
                record_info["reason"] = "MISSING_BUSINESS_SEMANTICS"
                stats["MANUAL_REVIEW_REQUIRED"] += 1
                results.append(record_info)
                continue

            todas_props = propriedades_por_tenant.get(up.tenant_id, [])
            
            props_candidatas = []
            for p in todas_props:
                if up.cpf_cnpj and p.cpf_cnpj and up.cpf_cnpj == p.cpf_cnpj:
                    props_candidatas.append(p)
                elif up.nome and p.nome and up.nome.lower().strip() == p.nome.lower().strip():
                    if p not in props_candidatas:
                        props_candidatas.append(p)

            if not props_candidatas:
                record_info["status"] = "MANUAL_REVIEW"
                record_info["reason"] = "MISSING_PROPERTY - Criacao Automatica Proibida por Regra"
                stats["MANUAL_REVIEW"] += 1
                results.append(record_info)
                continue
                
            if len(props_candidatas) > 1:
                forte = [p for p in props_candidatas if p.cpf_cnpj == up.cpf_cnpj and up.nome and p.nome and p.nome.lower().strip() == up.nome.lower().strip()]
                if len(forte) == 1:
                    propriedade = forte[0]
                    record_info["resolution"] = "SAFE_SELECTION"
                    stats["SAFE_SELECTION"] += 1
                else:
                    record_info["status"] = "MANUAL_SELECTION"
                    record_info["reason"] = "MULTIPLE_PROPERTY_CANDIDATES"
                    stats["MANUAL_SELECTION"] += 1
                    results.append(record_info)
                    continue
            else:
                propriedade = props_candidatas[0]
                record_info["resolution"] = "LINK_EXISTING_PROPERTY"
                stats["LINK_EXISTING_PROPERTY"] += 1
            
            # Verificamos se já existe exploração ativa equivalente
            expls_desta_up = expls_por_up.get(up.id, [])
            existente = next((e for e in expls_desta_up if e.propriedade_id == propriedade.id), None)
            
            if existente:
                record_info["status"] = "IGNORE"
                record_info["reason"] = "ALREADY_HAS_EXPLORACAO"
                stats["IGNORE"] += 1
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
                await session.execute(text(f"SET app.current_tenant_id = '{up.tenant_id}';"))
                session.add(nova_exploracao)
                await session.flush()
                record_info["status"] = "EXPLORACAO_CREATED_APPLIED"
                stats["EXPLORACAO_CREATED_APPLIED"] += 1
            else:
                record_info["status"] = "CAN_CREATE_EXPLORACAO"
                stats["CAN_CREATE_EXPLORACAO"] += 1
                
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
        
        # Puxamos todas UPs referenciadas
        up_ids = list(set([ir.unidade_produtiva_id for ir in imoveis]))
        stmt_ups_imv = select(UnidadeProdutiva).where(UnidadeProdutiva.id.in_(up_ids))
        ups_imv_db = (await session.execute(stmt_ups_imv)).scalars().all()
        up_map = {up.id: up for up in ups_imv_db}
        
        for imovel in imoveis:
            record_info = {
                "imovel_rural_id": str(imovel.id),
                "unidade_produtiva_id": str(imovel.unidade_produtiva_id),
                "tenant_id": str(imovel.tenant_id)
            }
            
            up = up_map.get(imovel.unidade_produtiva_id)
            if up:
                campos_alterados = []
                # Analise de campos fundiarios
                mapping = [
                    ("nirf", up.nirf, imovel.nirf),
                    ("codigo_car", up.codigo_car, imovel.car_numero),
                    ("numero_matricula", up.numero_matricula, imovel.numero_matricula),
                    ("ccir", up.ccir, imovel.ccir_numero),
                    ("sigef_codigo", up.sigef_codigo, imovel.sigef_codigo)
                ]
                
                for field, up_val, im_val in mapping:
                    if up_val and not im_val:
                        campos_alterados.append(field)
                        if field == "nirf": imovel.nirf = up_val
                        elif field == "codigo_car": imovel.car_numero = up_val
                        elif field == "numero_matricula": imovel.numero_matricula = up_val
                        elif field == "ccir": imovel.ccir_numero = up_val
                        elif field == "sigef_codigo": imovel.sigef_codigo = up_val
                    elif up_val and im_val and up_val != im_val:
                        stats["DIVERGENT"] += 1
                    elif up_val and im_val and up_val == im_val:
                        stats["IDENTICAL"] += 1
                        
                if campos_alterados:
                    record_info["legacy_fields_migrated"] = campos_alterados
                    if apply:
                        await session.execute(text(f"SET app.current_tenant_id = '{imovel.tenant_id}';"))
                        await session.flush()
                        stats["LEGACY_FIELDS_MIGRATED_APPLIED"] += 1
                    else:
                        stats["LEGACY_FIELDS_MIGRATED"] += 1
            
            # Buscar exploração para ligar à Propriedade
            exploracoes = [e for e in expls_por_up.get(up.id, []) if e.ativo]
            
            if not exploracoes:
                record_info["link_status"] = "IGNORE"
                record_info["reason"] = "NO_EXPLORACAO_RURAL"
                stats["IGNORE_NO_EXPLORACAO"] += 1
                results.append(record_info)
                continue
                
            propriedades_distintas = list(set(e.propriedade_id for e in exploracoes))
            if len(propriedades_distintas) > 1:
                record_info["link_status"] = "MULTIPLE_TARGETS"
                stats["MULTIPLE_TARGETS"] += 1
                results.append(record_info)
                continue
                
            propriedade_id = propriedades_distintas[0]
            
            # Verifica consistência / conflito
            await session.execute(text(f"SET app.current_tenant_id = '{imovel.tenant_id}';"))
            stmt_pi = select(PropriedadeImovel).where(PropriedadeImovel.imovel_rural_id == imovel.id)
            pis_existentes = (await session.execute(stmt_pi)).scalars().all()
            
            if pis_existentes:
                conflito = False
                for pi in pis_existentes:
                    if pi.propriedade_id != propriedade_id:
                        conflito = True
                        break
                
                if conflito:
                    record_info["link_status"] = "DIVERGENT"
                    record_info["reason"] = "PropriedadeImovel aponta para outra propriedade"
                    stats["DIVERGENT_LINK"] += 1
                else:
                    record_info["link_status"] = "IDENTICAL"
                    stats["IDENTICAL_LINK"] += 1
                results.append(record_info)
                continue
                
            # Criação do link
            if apply:
                # Se a propriedade já tem um principal
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
                    origem_documental="MIGRACAO_SISTEMICA_01G",
                    vinculo_principal=not has_principal
                )
                await session.execute(text(f"SET app.current_tenant_id = '{imovel.tenant_id}';"))
                session.add(novo_vinculo)
                await session.flush()
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
    parser = argparse.ArgumentParser(description="TERRITORY-CONVERGENCE-01G Backfill Avançado")
    parser.add_argument("--apply", action="store_true", help="Aplica as mudanças no banco de dados. Padrão é dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Executa apenas simulação (Padrão).")
    parser.add_argument("--tenant-id", type=str, help="Filtra por um Tenant ID especifico.")
    parser.add_argument("--limit", type=int, help="Limite de registros a processar.")
    parser.add_argument("--output-report", type=str, default="reports/backfill_01g_report.json", help="Caminho do relatório JSON.")
    
    args = parser.parse_args()
    apply = args.apply and not args.dry_run
    
    asyncio.run(backfill_territorial_01g(
        apply=apply,
        tenant_id=args.tenant_id,
        limit=args.limit,
        output_report=args.output_report
    ))
