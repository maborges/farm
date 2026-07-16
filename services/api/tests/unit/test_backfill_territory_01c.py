import os
import json
import uuid
import pytest
from datetime import date
from sqlalchemy import select, text

from core.models.unidade_produtiva import UnidadeProdutiva
from imoveis.models.imovel import ImovelRural
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural
from core.cadastros.propriedade_imovel.models import PropriedadeImovel

from scripts.backfill_territory_01c import backfill_territorial

pytestmark = pytest.mark.asyncio


async def test_backfill_territorial_dry_run_and_apply(session_a, tmp_path):
    """
    Testa o backfill territorial (Fase 01C) cobrindo:
    - Cenário sem ExploracaoRural
    - Cenário Inequívoco (1 UP -> 1 Propriedade)
    - Cenário já consistente
    - Dry-run não gera commits
    """
    from tests.conftest import TENANT_A_ID

    # Setup
    up1 = UnidadeProdutiva(id=uuid.uuid4(), tenant_id=TENANT_A_ID, nome="UP 1", ativo=True)
    up2 = UnidadeProdutiva(id=uuid.uuid4(), tenant_id=TENANT_A_ID, nome="UP 2", ativo=True)
    up3 = UnidadeProdutiva(id=uuid.uuid4(), tenant_id=TENANT_A_ID, nome="UP 3", ativo=True)
    
    session_a.add_all([up1, up2, up3])
    await session_a.flush()

    prop1 = Propriedade(id=uuid.uuid4(), tenant_id=TENANT_A_ID, nome="Prop 1", ativo=True)
    prop2 = Propriedade(id=uuid.uuid4(), tenant_id=TENANT_A_ID, nome="Prop 2", ativo=True)
    
    session_a.add_all([prop1, prop2])
    await session_a.flush()
    
    # Exploracoes (Ponte UP -> Propriedade)
    # UP1 -> Prop1
    expl1 = ExploracaoRural(id=uuid.uuid4(), tenant_id=TENANT_A_ID, unidade_produtiva_id=up1.id, propriedade_id=prop1.id, natureza="posse", data_inicio=date.today())
    # UP2 -> (Sem exploracao)
    # UP3 -> Prop2 (Ja existente oficial)
    expl3 = ExploracaoRural(id=uuid.uuid4(), tenant_id=TENANT_A_ID, unidade_produtiva_id=up3.id, propriedade_id=prop2.id, natureza="posse", data_inicio=date.today())
    
    session_a.add_all([expl1, expl3])
    await session_a.flush()
    
    # Imoveis Rurais legados pendurados na UP
    imovel1 = ImovelRural(id=uuid.uuid4(), tenant_id=TENANT_A_ID, unidade_produtiva_id=up1.id, nome="Imovel 1", municipio="SP", uf="SP")
    imovel2 = ImovelRural(id=uuid.uuid4(), tenant_id=TENANT_A_ID, unidade_produtiva_id=up2.id, nome="Imovel 2", municipio="SP", uf="SP")
    imovel3 = ImovelRural(id=uuid.uuid4(), tenant_id=TENANT_A_ID, unidade_produtiva_id=up3.id, nome="Imovel 3", municipio="SP", uf="SP")
    
    session_a.add_all([imovel1, imovel2, imovel3])
    await session_a.flush()
    
    # Adicionar o vínculo oficial já existente para UP3
    pi = PropriedadeImovel(
        id=uuid.uuid4(),
        tenant_id=TENANT_A_ID,
        propriedade_id=prop2.id,
        imovel_rural_id=imovel3.id,
        tipo_vinculo="PROPRIEDADE_PRINCIPAL",
        data_inicio=date.today(),
        origem_documental="TESTE"
    )
    session_a.add(pi)
    await session_a.execute(text(f"SET app.current_tenant_id = '{TENANT_A_ID}'"))
    await session_a.flush()  # Garante os dados pro teste
    
    report_file = tmp_path / "report.json"
    
    # 1. DRY-RUN
    await backfill_territorial(
        apply=False,
        tenant_id=str(TENANT_A_ID),
        output_report=str(report_file),
        session_override=session_a
    )
    
    assert report_file.exists()
    data = json.loads(report_file.read_text())
    
    assert data["mode"] == "DRY-RUN"
    stats = data["stats"]
    assert stats.get("LINK_CREATED_DRY_RUN", 0) >= 1
    assert stats.get("NO_EXPLORACAO_RURAL", 0) >= 1
    assert stats.get("ALREADY_CONSISTENT", 0) >= 1
    
    # Validar que banco não foi alterado no dry-run (Apenas PI original existe)
    pis_no_banco = (await session_a.execute(select(PropriedadeImovel).where(PropriedadeImovel.imovel_rural_id.in_([imovel1.id, imovel2.id, imovel3.id])))).scalars().all()
    assert len(pis_no_banco) == 1
    
    # 2. APPLY
    await backfill_territorial(
        apply=True,
        tenant_id=str(TENANT_A_ID),
        output_report=str(report_file),
        session_override=session_a
    )
    
    data_apply = json.loads(report_file.read_text())
    assert data_apply["mode"] == "APPLY"
    stats_apply = data_apply["stats"]
    assert stats_apply.get("LINK_CREATED", 0) >= 1
    
    # Validar que banco FOI alterado
    pis_no_banco_pos = (await session_a.execute(select(PropriedadeImovel).where(PropriedadeImovel.imovel_rural_id.in_([imovel1.id, imovel2.id, imovel3.id])))).scalars().all()
    assert len(pis_no_banco_pos) == 2
    
    # Valida o criado
    pi_criado = next(p for p in pis_no_banco_pos if p.imovel_rural_id == imovel1.id)
    assert pi_criado.propriedade_id == prop1.id
    assert pi_criado.origem_documental == "MIGRACAO_SISTEMICA_01C"
