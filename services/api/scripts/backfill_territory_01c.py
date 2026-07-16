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
from core.cadastros.propriedade_imovel.models import PropriedadeImovel
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade


async def backfill_territorial(
    apply: bool = False,
    tenant_id: str = None,
    limit: int = None,
    output_report: str = "reports/backfill_01c_report.json",
    session_override: AsyncSession = None
):
    results: List[Dict[str, Any]] = []
    stats = Counter()
    
    import contextlib
    
    @contextlib.asynccontextmanager
    async def get_session_ctx():
        if session_override:
            yield session_override
        else:
            async with async_session_maker() as s:
                yield s

    async with get_session_ctx() as session:
        # Busca Imoveis Rurais legados (com unidade_produtiva_id) que nao foram deletados
        stmt_imoveis = select(ImovelRural).where(
            ImovelRural.unidade_produtiva_id.isnot(None)
        ).order_by(ImovelRural.id)
        
        if tenant_id:
            stmt_imoveis = stmt_imoveis.where(ImovelRural.tenant_id == uuid.UUID(tenant_id))
            
        if limit:
            stmt_imoveis = stmt_imoveis.limit(limit)
            
        imoveis = (await session.execute(stmt_imoveis)).scalars().all()
        
        for imovel in imoveis:
            record_info = {
                "imovel_rural_id": str(imovel.id),
                "tenant_id": str(imovel.tenant_id),
                "unidade_produtiva_id": str(imovel.unidade_produtiva_id),
                "status": "PENDING",
                "propriedade_id": None,
                "exploracao_rural_ids": [],
                "reason": None
            }
            
            # Busca Exploracoes Rurais associadas a esta Unidade Produtiva
            stmt_expl = select(ExploracaoRural).where(
                ExploracaoRural.unidade_produtiva_id == imovel.unidade_produtiva_id,
                ExploracaoRural.ativo == True
            )
            exploracoes = (await session.execute(stmt_expl)).scalars().all()
            
            if not exploracoes:
                record_info["status"] = "NO_EXPLORACAO_RURAL"
                stats["NO_EXPLORACAO_RURAL"] += 1
                results.append(record_info)
                continue
                
            record_info["exploracao_rural_ids"] = [str(e.id) for e in exploracoes]
            
            # Cross-Tenant Check nas Exploracoes
            if any(e.tenant_id != imovel.tenant_id for e in exploracoes):
                record_info["status"] = "TENANT_MISMATCH"
                stats["TENANT_MISMATCH"] += 1
                results.append(record_info)
                continue
                
            propriedades_distintas = list(set(e.propriedade_id for e in exploracoes))
            
            if len(propriedades_distintas) > 1:
                record_info["status"] = "MULTIPLE_PROPERTIES"
                stats["MULTIPLE_PROPERTIES"] += 1
                results.append(record_info)
                continue
                
            propriedade_id = propriedades_distintas[0]
            record_info["propriedade_id"] = str(propriedade_id)
            
            # Verifica propriedade ativa
            prop_obj = (await session.execute(
                select(Propriedade).where(Propriedade.id == propriedade_id, Propriedade.ativo == True)
            )).scalar_one_or_none()
            
            if not prop_obj:
                record_info["status"] = "NO_PROPRIEDADE"
                record_info["reason"] = "Propriedade apontada por exploracao não existe ou está deletada."
                stats["NO_PROPRIEDADE"] += 1
                results.append(record_info)
                continue
                
            # Cross-Tenant Check na Propriedade
            if prop_obj.tenant_id != imovel.tenant_id:
                record_info["status"] = "TENANT_MISMATCH"
                stats["TENANT_MISMATCH"] += 1
                results.append(record_info)
                continue
                
            # Verifica se ImovelRural já possui algum vínculo oficial (ALREADY_CONSISTENT / CONFLICT)
            stmt_pi = select(PropriedadeImovel).where(
                PropriedadeImovel.imovel_rural_id == imovel.id
            )
            pis_existentes = (await session.execute(stmt_pi)).scalars().all()
            
            if pis_existentes:
                conflito = False
                for pi in pis_existentes:
                    if pi.propriedade_id != propriedade_id:
                        conflito = True
                        record_info["reason"] = f"Vinculo existente aponta para {pi.propriedade_id} em vez de {propriedade_id}"
                        break
                
                if conflito:
                    record_info["status"] = "CONFLICT"
                    stats["CONFLICT"] += 1
                else:
                    record_info["status"] = "ALREADY_CONSISTENT"
                    stats["ALREADY_CONSISTENT"] += 1
                results.append(record_info)
                continue
                
            # Tudo certo para criar o vínculo
            if not apply:
                if len(exploracoes) > 1:
                    record_info["status"] = "MULTIPLE_EXPLORACOES_SAME_PROPERTY"
                    stats["MULTIPLE_EXPLORACOES_SAME_PROPERTY"] += 1
                else:
                    record_info["status"] = "LINK_CREATED_DRY_RUN"
                    stats["LINK_CREATED_DRY_RUN"] += 1
                results.append(record_info)
                continue
                
            # APPLY MODE
            novo_vinculo = PropriedadeImovel(
                tenant_id=imovel.tenant_id,
                propriedade_id=propriedade_id,
                imovel_rural_id=imovel.id,
                tipo_vinculo="PROPRIEDADE_PRINCIPAL",
                ativo=True,
                data_inicio=date.today(),
                origem_documental="MIGRACAO_SISTEMICA_01C",
                vinculo_principal=True
            )
            
            try:
                # Usa savepoint para evitar corrupcao da transacao em caso de constraint falha
                async with session.begin_nested():
                    await session.execute(text(f"SET app.current_tenant_id = '{imovel.tenant_id}'"))
                    session.add(novo_vinculo)
                    await session.flush()
                    
                if len(exploracoes) > 1:
                    record_info["status"] = "MULTIPLE_EXPLORACOES_SAME_PROPERTY"
                    stats["MULTIPLE_EXPLORACOES_SAME_PROPERTY"] += 1
                else:
                    record_info["status"] = "LINK_CREATED"
                    stats["LINK_CREATED"] += 1
                record_info["created_association_id"] = str(novo_vinculo.id)
                
            except IntegrityError as e:
                # Falha na constraint uq_propriedade_imovel_principal_ativo 
                record_info["status"] = "CONFLICT"
                record_info["reason"] = "Falha de IntegrityError (provável uq_propriedade_imovel_principal_ativo)"
                stats["CONFLICT"] += 1
            except Exception as e:
                record_info["status"] = "ERROR"
                record_info["reason"] = str(e)
                stats["ERROR"] += 1
                
            results.append(record_info)
            
        if apply:
            if session_override:
                await session.flush()
            else:
                await session.commit()
            
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
    parser = argparse.ArgumentParser(description="TERRITORY-CONVERGENCE-01C Backfill")
    parser.add_argument("--apply", action="store_true", help="Aplica as mudanças no banco de dados. Padrão é dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Executa apenas simulação (Padrão).")
    parser.add_argument("--tenant-id", type=str, help="Filtra por um Tenant ID especifico.")
    parser.add_argument("--limit", type=int, help="Limite de registros a processar.")
    parser.add_argument("--output-report", type=str, default="reports/backfill_01c_report.json", help="Caminho do relatório JSON.")
    
    args = parser.parse_args()
    
    # --dry-run é default
    apply = args.apply and not args.dry_run
    
    asyncio.run(backfill_territorial(
        apply=apply,
        tenant_id=args.tenant_id,
        limit=args.limit,
        output_report=args.output_report
    ))
