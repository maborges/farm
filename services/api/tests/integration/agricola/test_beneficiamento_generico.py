import uuid
from datetime import date

import pytest
from sqlalchemy import select

from agricola.beneficiamento.models import LoteBeneficiamentoCafeDetalhe
from agricola.beneficiamento.schemas import (
    LoteBeneficiamentoCreate,
    LoteBeneficiamentoUpdate,
    LoteBeneficiamentoCafeDetalheCreate,
)
from agricola.beneficiamento.service import BeneficiamentoService
from agricola.safras.models import Safra
from core.exceptions import EntityNotFoundError
import operacional.models.qualidade  # noqa: F401
import campo.models  # noqa: F401


async def _criar_safra(session, tenant_id) -> uuid.UUID:
    safra_id = uuid.uuid4()
    session.add(Safra(id=safra_id, tenant_id=tenant_id, ano_safra="2025", status="PLANEJAMENTO"))
    await session.commit()
    return safra_id


@pytest.mark.asyncio
async def test_criar_lote_generico_sem_detalhe_cafe(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id)
    svc = BeneficiamentoService(session, tenant_id)

    lote = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-SOJA-1",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=1000.0,
    ))
    await session.commit()

    assert lote.detalhe_cafe is None
    detalhe = await svc._get_detalhe_cafe(lote.id)
    assert detalhe is None


@pytest.mark.asyncio
async def test_atualizar_lote_generico_sem_fator_manual_nao_calcula_perda(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id)
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-SOJA-2",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=1000.0,
    ))
    await session.commit()

    atualizado = await svc.atualizar(lote.id, LoteBeneficiamentoUpdate(peso_saida_kg=800.0))
    await session.commit()

    assert float(atualizado.fator_reducao) == 1.25
    assert float(atualizado.sacas_beneficiadas) == round(800.0 / 60.0, 3)
    assert atualizado.perda_pct is None


@pytest.mark.asyncio
async def test_atualizar_lote_generico_com_fator_manual_calcula_perda(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id)
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-SOJA-3",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=1000.0,
        fator_esperado_manual=1.1,
    ))
    await session.commit()

    atualizado = await svc.atualizar(lote.id, LoteBeneficiamentoUpdate(peso_saida_kg=800.0))
    await session.commit()

    peso_esperado = 1000.0 / 1.1
    perda_esperada = round((peso_esperado - 800.0) / peso_esperado * 100, 2)
    assert float(atualizado.perda_pct) == perda_esperada


@pytest.mark.asyncio
async def test_criar_lote_com_detalhe_cafe_persiste_extensao_e_calcula_via_fator_esperado(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id)
    svc = BeneficiamentoService(session, tenant_id)

    lote = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-CAFE-1",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=4800.0,
        detalhe_cafe=LoteBeneficiamentoCafeDetalheCreate(metodo="NATURAL"),
    ))
    await session.commit()

    assert lote.detalhe_cafe is not None
    assert lote.detalhe_cafe.metodo == "NATURAL"

    atualizado = await svc.atualizar(lote.id, LoteBeneficiamentoUpdate(peso_saida_kg=1000.0))
    await session.commit()

    # FATOR_ESPERADO["NATURAL"] = 4.8 -> peso_esperado = 1000.0
    assert float(atualizado.perda_pct) == 0.0


@pytest.mark.asyncio
async def test_isolamento_tenant_detalhe_cafe(session_a, session_b, tenant_id, outro_tenant_id, talhao_id):
    safra_id = await _criar_safra(session_a, tenant_id)
    svc_a = BeneficiamentoService(session_a, tenant_id)
    lote = await svc_a.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-CAFE-ISO",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=1000.0,
        detalhe_cafe=LoteBeneficiamentoCafeDetalheCreate(metodo="LAVADO"),
    ))
    await session_a.commit()

    svc_b = BeneficiamentoService(session_b, outro_tenant_id)
    with pytest.raises(EntityNotFoundError):
        await svc_b.obter_com_detalhe(lote.id)


@pytest.mark.asyncio
async def test_relatorio_rendimento_mistura_cafe_e_generico(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id)
    svc = BeneficiamentoService(session, tenant_id)

    lote_cafe = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-REL-CAFE",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=4800.0,
        detalhe_cafe=LoteBeneficiamentoCafeDetalheCreate(metodo="NATURAL"),
    ))
    await session.commit()
    await svc.atualizar(lote_cafe.id, LoteBeneficiamentoUpdate(peso_saida_kg=1000.0))
    await session.commit()

    lote_generico = await svc.criar(LoteBeneficiamentoCreate(
        safra_id=safra_id, talhao_id=talhao_id, numero_lote="BEN-REL-GEN",
        data_entrada=date(2025, 5, 1), peso_entrada_kg=1000.0,
    ))
    await session.commit()
    await svc.atualizar(lote_generico.id, LoteBeneficiamentoUpdate(peso_saida_kg=800.0))
    await session.commit()

    relatorio = await svc.relatorio_rendimento(safra_id)
    metodos = {item.metodo for item in relatorio.por_metodo}
    assert "NATURAL" in metodos
    assert "GENERICO" in metodos
    assert relatorio.total_lotes == 2
