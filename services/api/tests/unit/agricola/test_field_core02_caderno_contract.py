import uuid
from datetime import date

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from agricola.caderno.models import CadernoCampoEntrada
from agricola.caderno.schemas import EntradaCreate
from agricola.caderno.service import (
    CadernoCampoService,
    _mapear_tipo_evento_legado,
)
from agricola.operacoes.models import OperacaoAgricola


async def _criar_safra(session, tenant_id: uuid.UUID, talhao_id: uuid.UUID) -> uuid.UUID:
    for ddl in [
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(30)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_evento VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_id VARCHAR(80)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_tecnica VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS status_evento VARCHAR(30)",
    ]:
        await session.execute(text(ddl))

    safra_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO safras (id, tenant_id, ano_safra, cultura, status, created_at, updated_at)
            VALUES (:id, :tenant_id, '2025/26', 'Soja', 'PLANEJADA', NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(safra_id), "tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            """
            INSERT INTO safra_talhoes (id, tenant_id, safra_id, area_id, area_ha, principal, created_at)
            VALUES (:id, :tenant_id, :safra_id, :talhao_id, 100.0, true, NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "safra_id": str(safra_id),
            "talhao_id": str(talhao_id),
        },
    )
    await session.commit()
    return safra_id


async def _criar_operacao(session, tenant_id: uuid.UUID, safra_id: uuid.UUID, talhao_id: uuid.UUID) -> uuid.UUID:
    operacao_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO operacoes_agricolas (
                id, tenant_id, safra_id, talhao_id, tipo, subtipo, descricao,
                data_realizada, custo_total, custo_por_ha, area_aplicada_ha, fotos, status, created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :safra_id, :talhao_id, :tipo, :subtipo, :descricao,
                :data_realizada, :custo_total, :custo_por_ha, :area_aplicada_ha, CAST('[]' AS json), 'REALIZADA', NOW(), NOW()
            )
            """
        ),
        {
            "id": str(operacao_id),
            "tenant_id": str(tenant_id),
            "safra_id": str(safra_id),
            "talhao_id": str(talhao_id),
            "tipo": "APLICACAO_DEFENSIVO",
            "subtipo": "Pulverização defensiva",
            "descricao": "Aplicação canônica",
            "data_realizada": date.today(),
            "custo_total": 0,
            "custo_por_ha": 0,
            "area_aplicada_ha": 10.0,
        },
    )
    await session.commit()
    return operacao_id


@pytest.mark.asyncio
async def test_caderno_evento_valido_e_tipo_invalido_rejeitado(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="monitoramento",
            descricao="Monitoramento de praga",
            data_registro=date.today(),
        ),
        usuario_id=uuid.uuid4(),
    )

    assert entrada.tipo == "MONITORAMENTO"
    assert entrada.tipo_evento == "MONITORAMENTO"
    assert entrada.origem_evento == "WEB_MANUAL"
    assert entrada.origem_tecnica == "MANUAL_DIGITAL"
    assert entrada.status_evento == "CONSOLIDADO"

    with pytest.raises(BusinessRuleError):
        await svc.criar_entrada(
            EntradaCreate(
                safra_id=safra_id,
                talhao_id=talhao_id,
                tipo="TIPO_INEXISTENTE",
                descricao="Entrada inválida",
                data_registro=date.today(),
            ),
            usuario_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_operacao_gera_evento_canonico_idempotente(session, tenant_id, unidade_produtiva_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    operacao_id = await _criar_operacao(session, tenant_id, safra_id, talhao_id)

    operacao = await session.get(OperacaoAgricola, operacao_id)
    assert operacao is not None

    svc = CadernoCampoService(session, tenant_id)
    evento_1 = await svc.garantir_evento_operacao(operacao)
    evento_2 = await svc.garantir_evento_operacao(operacao)

    assert evento_1.id == evento_2.id
    assert evento_1.tipo == "PULVERIZACAO"
    assert evento_1.tipo_evento == "PULVERIZACAO"
    assert evento_1.origem_evento == "OPERACAO_AGRICOLA"
    assert evento_1.origem_id == str(operacao_id)
    assert evento_1.origem_tecnica == "OPERACAO_AUTO"
    assert evento_1.status_evento == "CONSOLIDADO"

    items = await svc.timeline(safra_id)
    matches = [item for item in items if item.origem_evento == "OPERACAO_AGRICOLA" and item.origem_id == str(operacao_id)]
    assert len(matches) == 1
    assert matches[0].tipo_evento == "PULVERIZACAO"


@pytest.mark.asyncio
async def test_compatibilidade_tipo_legado_operacao_auto():
    assert _mapear_tipo_evento_legado("OPERACAO_AUTO") == "EXECUCAO_OPERACIONAL"
