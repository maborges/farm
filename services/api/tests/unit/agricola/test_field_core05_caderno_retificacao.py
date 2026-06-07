import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.service import TarefaService
from agricola.caderno.schemas import EntradaCreate, ExportacaoCreate
from agricola.caderno.service import CadernoCampoService, CadernoExportacaoService
from agricola.operacoes.models import OperacaoAgricola
from core.models.auth import TenantUsuario, Usuario


async def _ensure_caderno_retificacao_schema(session) -> None:
    ddls = [
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(30)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_evento VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_id VARCHAR(80)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_tecnica VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS status_evento VARCHAR(30)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS retifica_evento_id UUID",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS retificado_por_evento_id UUID",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS motivo_retificacao TEXT",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS retificado_em TIMESTAMP",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS retificado_por_usuario_id UUID",
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
    ]
    for ddl in ddls:
        await session.execute(text(ddl))


async def _seed_tenant(session, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID, Usuario]:
    await _ensure_caderno_retificacao_schema(session)

    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(tenant_id), "nome": f"Tenant {tenant_id.hex[:6]}", "documento": tenant_id.hex[:11]},
    )

    usuario = Usuario(
        id=uuid.uuid4(),
        email=f"rt-{tenant_id.hex[:8]}@agrosaas.local",
        username=f"rt_{tenant_id.hex[:8]}",
        nome_completo=f"RT {tenant_id.hex[:6]}",
        ativo=True,
        is_superuser=False,
    )
    session.add(usuario)
    await session.flush()
    session.add(TenantUsuario(tenant_id=tenant_id, usuario_id=usuario.id, is_owner=True, status="ATIVO"))

    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda Teste', true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )
    talhao_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :unidade_produtiva_id, 'TALHAO', 'Talhão Teste', 100.0, true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(talhao_id),
            "tenant_id": str(tenant_id),
            "unidade_produtiva_id": str(unidade_produtiva_id),
        },
    )
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
    return safra_id, talhao_id, usuario


async def _criar_entrada(session, tenant_id: uuid.UUID, safra_id: uuid.UUID, talhao_id: uuid.UUID, usuario_id: uuid.UUID, *, status: str, descricao: str) -> uuid.UUID:
    svc = CadernoCampoService(session, tenant_id)
    entrada = await svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OBSERVACAO",
            descricao=descricao,
            data_registro=date.today(),
            status_evento=status,
        ),
        usuario_id=usuario_id,
    )
    return entrada.id


@pytest.mark.asyncio
async def test_evento_consolidado_nao_edita_diretamente(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)

    entrada_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Evento base")
    await svc.alterar_status_evento(entrada_id, novo_status="APROVADO", justificativa="ok", usuario_id=usuario.id, usuario_role="agronomo")
    await svc.alterar_status_evento(entrada_id, novo_status="CONSOLIDADO", justificativa="ok", usuario_id=usuario.id, usuario_role="agronomo")

    with pytest.raises(BusinessRuleError):
        await svc.update(entrada_id, {"descricao": "Alteração proibida"})


@pytest.mark.asyncio
async def test_retificacao_cria_nova_versao_vinculada_e_preserva_original(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)

    original_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Entrada rejeitada")
    await svc.alterar_status_evento(original_id, novo_status="REJEITADO", justificativa="dados inconsistentes", usuario_id=usuario.id, usuario_role="agronomo")

    retificada = await svc.reprocessar_entrada(
        original_id,
        motivo="Correção de evidência",
        dados_corrigidos={"descricao": "Entrada corrigida"},
        usuario_id=usuario.id,
        usuario_role="agronomo",
    )

    original = await svc.get_or_fail(original_id)
    assert original.retificado_por_evento_id == retificada.id
    assert original.motivo_retificacao == "Correção de evidência"
    assert retificada.retifica_evento_id == original.id
    assert retificada.motivo_retificacao == "Correção de evidência"
    assert retificada.descricao == "Entrada corrigida"

    audit_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                  FROM tenant_audit_log
                 WHERE tenant_id = :tenant_id
                   AND resource = 'caderno_campo_entradas'
                   AND action IN ('retify', 'reprocess')
                """
            ),
            {"tenant_id": str(tenant_id)},
        )
    ).scalar_one()
    assert audit_count >= 2


@pytest.mark.asyncio
async def test_exportacao_oficial_usa_versao_vigente_e_auditoria_cadeia_completa(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)
    caderno_svc = CadernoCampoService(session, tenant_id)
    export_svc = CadernoExportacaoService(session, tenant_id)

    original_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Base")
    await caderno_svc.alterar_status_evento(original_id, novo_status="REJEITADO", justificativa="ajuste", usuario_id=usuario.id, usuario_role="agronomo")
    retificada = await caderno_svc.reprocessar_entrada(
        original_id,
        motivo="Reprocessamento após validação",
        dados_corrigidos={"descricao": "Base corrigida"},
        usuario_id=usuario.id,
        usuario_role="agronomo",
    )
    await caderno_svc.alterar_status_evento(retificada.id, novo_status="APROVADO", justificativa="ok", usuario_id=usuario.id, usuario_role="agronomo")

    oficiais = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "OFICIAL")
    auditoria = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "AUDITORIA")

    assert retificada.id in [e.id for e in oficiais]
    assert original_id not in [e.id for e in oficiais]
    assert original_id in [e.id for e in auditoria]
    assert retificada.id in [e.id for e in auditoria]

    exportacao_oficial = await export_svc.gerar(ExportacaoCreate(safra_id=safra_id, talhao_id=talhao_id, modo_exportacao="OFICIAL"))
    assert exportacao_oficial.hash_documental
    assert exportacao_oficial.modo_exportacao == "OFICIAL"

    exportacao_auditoria = await export_svc.gerar(ExportacaoCreate(safra_id=safra_id, talhao_id=talhao_id, modo_exportacao="AUDITORIA"))
    assert exportacao_auditoria.hash_documental
    assert exportacao_auditoria.modo_exportacao == "AUDITORIA"


@pytest.mark.asyncio
async def test_isolamento_por_tenant_com_retificacao(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    safra_a, talhao_a, usuario_a = await _seed_tenant(session, tenant_a)
    safra_b, talhao_b, usuario_b = await _seed_tenant(session, tenant_b)

    svc_a = CadernoCampoService(session, tenant_a)
    svc_b = CadernoCampoService(session, tenant_b)

    entrada_a = await _criar_entrada(session, tenant_a, safra_a, talhao_a, usuario_a.id, status="PENDENTE_APROVACAO", descricao="A")
    entrada_b = await _criar_entrada(session, tenant_b, safra_b, talhao_b, usuario_b.id, status="PENDENTE_APROVACAO", descricao="B")
    await svc_a.alterar_status_evento(entrada_a, novo_status="REJEITADO", justificativa="ok", usuario_id=usuario_a.id, usuario_role="agronomo")
    await svc_b.alterar_status_evento(entrada_b, novo_status="REJEITADO", justificativa="ok", usuario_id=usuario_b.id, usuario_role="agronomo")

    ret_a = await svc_a.reprocessar_entrada(
        entrada_a,
        motivo="corrigindo A",
        dados_corrigidos={"descricao": "A corrigido"},
        usuario_id=usuario_a.id,
        usuario_role="agronomo",
    )
    ret_b = await svc_b.reprocessar_entrada(
        entrada_b,
        motivo="corrigindo B",
        dados_corrigidos={"descricao": "B corrigido"},
        usuario_id=usuario_b.id,
        usuario_role="agronomo",
    )

    lista_a = await svc_a.timeline(safra_a)
    lista_b = await svc_b.timeline(safra_b)

    assert any(item.id == ret_a.id for item in lista_a)
    assert any(item.id == ret_b.id for item in lista_b)
    assert all(item.id != ret_b.id for item in lista_a)
    assert all(item.id != ret_a.id for item in lista_b)


@pytest.mark.asyncio
async def test_invalidez_de_tarefa_propaga_origem_documental_para_operacao_e_caderno(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)
    caderno_svc = CadernoCampoService(session, tenant_id)

    tarefa = SafraTarefa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        origem="MANUAL",
        tipo="PULVERIZACAO",
        descricao="Aplicação concluída",
        criticidade="NORMAL",
        prioridade="MEDIA",
        status="CONCLUIDA",
        concluida_em=datetime.utcnow(),
        created_by=usuario.id,
    )
    session.add(tarefa)
    await session.flush()

    operacao_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO operacoes_agricolas (
                id, tenant_id, safra_id, talhao_id, tarefa_id, tipo, subtipo, descricao,
                data_realizada, custo_total, custo_por_ha, area_aplicada_ha, fotos, status, created_at, updated_at
            )
            VALUES (
                :id, :tenant_id, :safra_id, :talhao_id, :tarefa_id, :tipo, :subtipo, :descricao,
                :data_realizada, :custo_total, :custo_por_ha, :area_aplicada_ha, CAST('[]' AS json), 'REALIZADA', NOW(), NOW()
            )
            """
        ),
        {
            "id": str(operacao_id),
            "tenant_id": str(tenant_id),
            "safra_id": str(safra_id),
            "talhao_id": str(talhao_id),
            "tarefa_id": str(tarefa.id),
            "tipo": "APLICACAO_DEFENSIVO",
            "subtipo": "Pulverização defensiva",
            "descricao": "Aplicação concluída",
            "data_realizada": date.today(),
            "custo_total": 120.0,
            "custo_por_ha": 12.0,
            "area_aplicada_ha": 10.0,
        },
    )
    await session.commit()

    operacao = await session.get(OperacaoAgricola, operacao_id)
    assert operacao is not None
    entrada = await caderno_svc.garantir_evento_operacao(operacao)
    await session.commit()

    service = TarefaService(session, tenant_id, user_id=usuario.id, ip_address="127.0.0.1")
    service._get = AsyncMock(return_value=tarefa)
    service._related_operacao_ids = AsyncMock(return_value=[operacao_id])

    tarefa_invalidada = await service.invalidar(
        tarefa.id,
        motivo="Execução concluída no contexto documental incorreto",
        user_id=usuario.id,
    )
    await session.commit()

    await session.refresh(tarefa_invalidada)
    await session.refresh(operacao)
    await session.refresh(entrada)

    assert tarefa_invalidada.status == "INVALIDADA"
    assert tarefa_invalidada.motivo_invalidacao == "Execução concluída no contexto documental incorreto"
    assert operacao.origem_invalidada is True
    assert operacao.motivo_invalidacao_origem == "Execução concluída no contexto documental incorreto"
    assert entrada.origem_invalidada is True
    assert entrada.motivo_invalidacao_origem == "Execução concluída no contexto documental incorreto"
    assert entrada.documental_status == "ORIGEM_INVALIDADA"

    timeline = await caderno_svc.timeline(safra_id)
    op_item = next(item for item in timeline if item.origem_evento == "OPERACAO_AGRICOLA" and item.origem_id == str(operacao_id))
    assert op_item.origem_invalidada is True
    assert op_item.documental_status == "ORIGEM_INVALIDADA"
    assert op_item.versao_vigente is False

    export_svc = CadernoExportacaoService(session, tenant_id)
    oficiais = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "OFICIAL")
    auditoria = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "AUDITORIA")
    assert entrada.id not in [e.id for e in oficiais]
    assert entrada.id in [e.id for e in auditoria]
