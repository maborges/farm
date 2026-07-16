import asyncio
import json
import csv
from collections import Counter
from pathlib import Path
from datetime import date
from sqlalchemy import select, text
from core.database import async_session_maker
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.propriedade_models import ExploracaoRural, Propriedade
from imoveis.models.imovel import ImovelRural
from core.cadastros.propriedade_imovel.models import PropriedadeImovel

def _mascarar_doc(doc: str) -> str:
    if not doc:
        return ""
    doc = str(doc).strip()
    if len(doc) <= 4:
        return doc
    return f"{doc[:2]}...{doc[-2:]}"

async def generate_reports():
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    json_path = reports_dir / "territory_01g1_direct_only.json"
    csv_path = reports_dir / "territory_01g1_decisions.csv"

    stats = Counter()
    json_records = []
    csv_records = []

    async with async_session_maker() as session:
        await session.execute(text("ALTER TABLE propriedade_imovel NO FORCE ROW LEVEL SECURITY;"))
        await session.execute(text("SET row_security = OFF;"))
        
        stmt_ir = select(ImovelRural).outerjoin(
            PropriedadeImovel, PropriedadeImovel.imovel_rural_id == ImovelRural.id
        ).where(
            PropriedadeImovel.id.is_(None),
            ImovelRural.unidade_produtiva_id.is_not(None)
        )
        imoveis = (await session.execute(stmt_ir)).scalars().all()
        
        # ALSO fetch the 9 ORPHANS!
        stmt_orphans = text("""
            SELECT DISTINCT ir.id
            FROM imoveis_rurais ir
            JOIN unidades_produtivas up ON ir.unidade_produtiva_id = up.id
            LEFT JOIN cadastros_exploracoes_rurais er ON er.unidade_produtiva_id = up.id
            WHERE er.id IS NULL
        """)
        orphan_ids = [row[0] for row in (await session.execute(stmt_orphans)).fetchall()]
        
        if orphan_ids:
            stmt_ir_orphans = select(ImovelRural).where(ImovelRural.id.in_(orphan_ids))
            orphans = (await session.execute(stmt_ir_orphans)).scalars().all()
            for o in orphans:
                if o not in imoveis:
                    imoveis.append(o)
        
        await session.execute(text("ALTER TABLE propriedade_imovel FORCE ROW LEVEL SECURITY;"))

        up_ids = list(set(ir.unidade_produtiva_id for ir in imoveis))
        stmt_ups = select(UnidadeProdutiva).where(UnidadeProdutiva.id.in_(up_ids))
        ups_db = (await session.execute(stmt_ups)).scalars().all()
        up_map = {up.id: up for up in ups_db}

        stmt_expl = select(ExploracaoRural).where(ExploracaoRural.unidade_produtiva_id.in_(up_ids))
        expls_db = (await session.execute(stmt_expl)).scalars().all()
        expl_por_up = {}
        for e in expls_db:
            expl_por_up.setdefault(e.unidade_produtiva_id, []).append(e)

        tenant_ids = list(set(up.tenant_id for up in ups_db))
        stmt_prop = select(Propriedade).where(Propriedade.tenant_id.in_(tenant_ids))
        props_db = (await session.execute(stmt_prop)).scalars().all()
        props_por_tenant = {}
        for p in props_db:
            props_por_tenant.setdefault(p.tenant_id, []).append(p)

        for imovel in imoveis:
            up = up_map.get(imovel.unidade_produtiva_id)
            if not up:
                continue

            tenant_id = imovel.tenant_id
            if imovel.tenant_id != up.tenant_id:
                classification = "TENANT_MISMATCH"
                action = "MANUAL_REVIEW"
            else:
                exploracoes = [e for e in expl_por_up.get(up.id, []) if e.ativo]
                todas_props = props_por_tenant.get(tenant_id, [])
                
                if not exploracoes:
                    props_candidatas = []
                    for p in todas_props:
                        match = False
                        if up.cpf_cnpj and p.cpf_cnpj == up.cpf_cnpj: match = True
                        elif up.nome and p.nome and up.nome.lower().strip() == p.nome.lower().strip(): match = True
                        if match:
                            props_candidatas.append(p)

                    if len(props_candidatas) == 1:
                        classification = "MISSING_EXPLORATION_SEMANTICS"
                        action = "MANUAL_REVIEW"
                    elif len(props_candidatas) > 1:
                        classification = "MULTIPLE_PROPERTY_CANDIDATES"
                        action = "MANUAL_REVIEW"
                    else:
                        classification = "MISSING_PROPERTY"
                        action = "MANUAL_REVIEW"
                else:
                    prop_ids = list(set(e.propriedade_id for e in exploracoes))
                    if len(prop_ids) == 1:
                        classification = "SAFE_EXISTING_PROPERTY"
                        action = "LINK_EXISTING_PROPERTY"
                    else:
                        classification = "SAFE_SAME_PROPERTY_FROM_MULTIPLE_EXPLORATIONS"
                        action = "MANUAL_REVIEW"

            stats[classification] += 1

            docs_mascarados = {
                "up_nirf": _mascarar_doc(up.nirf),
                "up_car": _mascarar_doc(up.codigo_car),
                "up_mat": _mascarar_doc(up.numero_matricula),
                "imovel_nirf": _mascarar_doc(imovel.nirf),
                "imovel_car": _mascarar_doc(imovel.car_numero)
            }

            prop_cand_ids = []
            if classification in ["MISSING_EXPLORATION_SEMANTICS", "MULTIPLE_PROPERTY_CANDIDATES"]:
                prop_cand_ids = [str(p.id) for p in props_candidatas]

            suggested_prop_id = prop_ids[0] if classification == "SAFE_EXISTING_PROPERTY" else (prop_cand_ids[0] if len(prop_cand_ids) == 1 else "")

            json_records.append({
                "tenant_id": str(imovel.tenant_id),
                "imovel_rural_id": str(imovel.id),
                "unidade_produtiva_id": str(up.id),
                "propriedades_candidatas": prop_cand_ids,
                "exploracoes_ativas": [str(e.id) for e in exploracoes] if exploracoes else [],
                "associacoes_existentes": [],
                "documentos_presentes_mascarados": docs_mascarados,
                "classification": classification,
                "reason_codes": [],
                "suggested_action": action
            })

            csv_records.append({
                "tenant_id": str(imovel.tenant_id),
                "unidade_produtiva_id": str(up.id),
                "imovel_rural_id": str(imovel.id),
                "action": action,
                "propriedade_id": str(suggested_prop_id),
                "tipo_exploracao": "PROPRIA" if action == "LINK_EXISTING_PROPERTY" else "",
                "data_inicio": date.today().isoformat() if action == "LINK_EXISTING_PROPERTY" else "",
                "nome_nova_propriedade": "",
                "justification": "Automated Safe Selection" if action == "LINK_EXISTING_PROPERTY" else "",
                "reviewed_by": "System" if action == "LINK_EXISTING_PROPERTY" else ""
            })

    with open(json_path, "w") as f:
        json.dump({"records": json_records}, f, indent=2)

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "tenant_id", "unidade_produtiva_id", "imovel_rural_id", "action", 
            "propriedade_id", "tipo_exploracao", "data_inicio", 
            "nome_nova_propriedade", "justification", "reviewed_by"
        ])
        writer.writeheader()
        writer.writerows(csv_records)

    print(f"Relatório gerado em: {json_path}")
    print(f"CSV de Decisões gerado em: {csv_path}")
    print("Resumo:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(generate_reports())
