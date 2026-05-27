import uuid
from datetime import date

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from agricola.caderno.models import CadernoEventoStatusHistorico
from agricola.caderno.schemas import EntradaCreate
from agricola.caderno.service import CadernoCampoService
from agricola.operacoes.models import OperacaoAgricola


async def _ensure_caderno_status_schema(session) -> None:
    for ddl in [
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(30)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_evento VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_id VARCHAR(80)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_tecnica VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS status_evento VARCHAR(30)",
        """
        CREATE TABLE IF NOT EXISTS caderno_evento_status_historico (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            caderno_entrada_id UUID NOT NULL,
            status_anterior VARCHAR(30),
            status_novo VARCHAR(30) NOT NULL,
            usuario_id UUID,
            justificativa TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
        """,
    ]:
        await session.execute(text(ddl))


async def _criar_safra(session, tenant_id: uuid.UUID, talhao_id: uuid.UUID) -> uuid.UUID:
    await _ensure_caderno_status_schema(session)

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
async def test_transicao_permitida_e_historico_registrado(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OBSERVACAO",
            descricao="Rascunho operacional",
            data_registro=date.today(),
            status_evento="RASCUNHO",
        ),
        usuario_id=uuid.uuid4(),
    )

    assert entrada.status_evento == "RASCUNHO"

    atualizada = await svc.alterar_status_evento(
        entrada.id,
        novo_status="PENDENTE_APROVACAO",
        justificativa="Conferência técnica pendente",
        usuario_id=uuid.uuid4(),
        usuario_role="agronomo",
    )

    assert atualizada.status_evento == "PENDENTE_APROVACAO"

    count = (
        await session.execute(
            text("SELECT COUNT(*) FROM caderno_evento_status_historico WHERE caderno_entrada_id = :id"),
            {"id": str(entrada.id)},
        )
    ).scalar_one()
    assert count >= 2


@pytest.mark.asyncio
async def test_transicao_invalida_rejeitada(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OBSERVACAO",
            descricao="Fluxo inválido",
            data_registro=date.today(),
            status_evento="RASCUNHO",
        ),
        usuario_id=uuid.uuid4(),
    )

    with pytest.raises(BusinessRuleError):
        await svc.alterar_status_evento(
            entrada.id,
            novo_status="CONSOLIDADO",
            justificativa="Tentativa inválida",
            usuario_id=uuid.uuid4(),
            usuario_role="agronomo",
        )


@pytest.mark.asyncio
async def test_aprovacao_exige_permissao(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OCORRENCIA",
            descricao="Incidente pendente",
            data_registro=date.today(),
            status_evento="PENDENTE_APROVACAO",
        ),
        usuario_id=uuid.uuid4(),
    )

    with pytest.raises(BusinessRuleError):
        await svc.alterar_status_evento(
            entrada.id,
            novo_status="APROVADO",
            justificativa="Aprovado",
            usuario_id=uuid.uuid4(),
            usuario_role="operador",
        )


@pytest.mark.asyncio
async def test_rejeicao_exige_justificativa(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="VISITA_TECNICA",
            descricao="Visita sem parecer",
            data_registro=date.today(),
            status_evento="PENDENTE_APROVACAO",
        ),
        usuario_id=uuid.uuid4(),
    )

    with pytest.raises(BusinessRuleError):
        await svc.alterar_status_evento(
            entrada.id,
            novo_status="REJEITADO",
            justificativa=None,
            usuario_id=uuid.uuid4(),
            usuario_role="agronomo",
        )


@pytest.mark.asyncio
async def test_pwa_offline_nao_consolida_sem_aprovacao(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="MONITORAMENTO",
            descricao="Registro offline",
            data_registro=date.today(),
            origem_evento="PWA_OFFLINE",
            status_evento="PENDENTE_SINCRONIZACAO",
        ),
        usuario_id=uuid.uuid4(),
    )

    sincronizada = await svc.alterar_status_evento(
        entrada.id,
        novo_status="SINCRONIZADO",
        justificativa="Sincronização concluída",
        usuario_id=uuid.uuid4(),
        usuario_role="agronomo",
    )
    assert sincronizada.status_evento == "SINCRONIZADO"

    with pytest.raises(BusinessRuleError):
        await svc.alterar_status_evento(
            entrada.id,
            novo_status="CONSOLIDADO",
            justificativa="Tentativa de consolidar sem aprovação",
            usuario_id=uuid.uuid4(),
            usuario_role="agronomo",
        )


@pytest.mark.asyncio
async def test_operacao_automatica_pode_consolidar_e_historia(session, tenant_id, talhao_id):
    safra_id = await _criar_safra(session, tenant_id, talhao_id)
    operacao_id = await _criar_operacao(session, tenant_id, safra_id, talhao_id)

    operacao = await session.get(OperacaoAgricola, operacao_id)
    assert operacao is not None

    svc = CadernoCampoService(session, tenant_id)
    entrada = await svc.garantir_evento_operacao(operacao)

    assert entrada.status_evento == "CONSOLIDADO"

    count = (
        await session.execute(
            text("SELECT COUNT(*) FROM caderno_evento_status_historico WHERE caderno_entrada_id = :id"),
            {"id": str(entrada.id)},
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_isolamento_por_tenant_em_status(session, tenant_id, outro_tenant_id, unidade_produtiva_id, talhao_id):
    # Tenant A
    safra_a = await _criar_safra(session, tenant_id, talhao_id)
    svc_a = CadernoCampoService(session, tenant_id)
    entrada_a = await svc_a.criar_entrada(
        EntradaCreate(
            safra_id=safra_a,
            talhao_id=talhao_id,
            tipo="OBSERVACAO",
            descricao="Tenant A",
            data_registro=date.today(),
        ),
        usuario_id=uuid.uuid4(),
    )

    # Tenant B
    talhao_b = uuid.uuid4()
    unidade_produtiva_b = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda B', true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(unidade_produtiva_b), "tenant_id": str(outro_tenant_id)},
    )
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :unidade_produtiva_id, 'TALHAO', 'Talhão B', 100.0, true, NOW(), NOW())
            """
        ),
        {
            "id": str(talhao_b),
            "tenant_id": str(outro_tenant_id),
            "unidade_produtiva_id": str(unidade_produtiva_b),
        },
    )
    safra_b = await _criar_safra(session, outro_tenant_id, talhao_b)
    svc_b = CadernoCampoService(session, outro_tenant_id)
    entrada_b = await svc_b.criar_entrada(
        EntradaCreate(
            safra_id=safra_b,
            talhao_id=talhao_b,
            tipo="OBSERVACAO",
            descricao="Tenant B",
            data_registro=date.today(),
        ),
        usuario_id=uuid.uuid4(),
    )

    with pytest.raises(Exception):
        await svc_a.alterar_status_evento(
            entrada_b.id,
            novo_status="CANCELADO",
            justificativa="Tentativa cross-tenant",
            usuario_id=uuid.uuid4(),
            usuario_role="agronomo",
        )
