import uuid
from datetime import date

import pytest
from sqlalchemy import text, select

from agricola.caderno.schemas import EntradaCreate, ExportacaoCreate
from agricola.caderno.service import CadernoCampoService, CadernoExportacaoService
from agricola.caderno.models import CadernoExportacao
from core.models.auth import Usuario, TenantUsuario


async def _ensure_caderno_export_schema(session) -> None:
    ddl = [
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(30)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_evento VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_id VARCHAR(80)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS origem_tecnica VARCHAR(40)",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS status_evento VARCHAR(30)",
        "CREATE TABLE IF NOT EXISTS caderno_evento_status_historico (id UUID PRIMARY KEY, tenant_id UUID NOT NULL, caderno_entrada_id UUID NOT NULL, status_anterior VARCHAR(30), status_novo VARCHAR(30) NOT NULL, usuario_id UUID, justificativa TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS modo_exportacao VARCHAR(20)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS hash_documental VARCHAR(128)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS assinatura_hash VARCHAR(128)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS responsavel_tecnico_id UUID",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS responsavel_tecnico_nome VARCHAR(200)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS responsavel_tecnico_crea VARCHAR(30)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS assinado_em TIMESTAMP",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS assinatura_origem VARCHAR(40)",
        "ALTER TABLE caderno_exportacoes ADD COLUMN IF NOT EXISTS observacao_assinatura TEXT",
    ]
    for stmt in ddl:
        await session.execute(text(stmt))


async def _seed_tenant(session, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID, Usuario]:
    await _ensure_caderno_export_schema(session)

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

    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda Teste', true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(tenant_id)},
    )
    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda Teste 2', true, NOW(), NOW())
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
async def test_exportacao_oficial_ignora_rejeitados(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)

    caderno_svc = CadernoCampoService(session, tenant_id)
    aprovado_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Aprovado")
    rejeitado_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Rejeitado")
    await caderno_svc.alterar_status_evento(aprovado_id, novo_status="APROVADO", justificativa="Conferido", usuario_id=usuario.id, usuario_role="agronomo")
    await caderno_svc.alterar_status_evento(rejeitado_id, novo_status="REJEITADO", justificativa="Dados inconsistentes", usuario_id=usuario.id, usuario_role="agronomo")

    export_svc = CadernoExportacaoService(session, tenant_id)
    oficiais = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "OFICIAL")
    auditoria = await export_svc._listar_eventos_documentais(safra_id, talhao_id, "AUDITORIA")

    assert aprovado_id in [e.id for e in oficiais]
    assert rejeitado_id not in [e.id for e in oficiais]
    assert aprovado_id in [e.id for e in auditoria]
    assert rejeitado_id in [e.id for e in auditoria]


@pytest.mark.asyncio
async def test_assinatura_gera_hash_e_auditoria(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, usuario = await _seed_tenant(session, tenant_id)

    caderno_svc = CadernoCampoService(session, tenant_id)
    entrada_id = await _criar_entrada(session, tenant_id, safra_id, talhao_id, usuario.id, status="PENDENTE_APROVACAO", descricao="Evento base")
    await caderno_svc.alterar_status_evento(entrada_id, novo_status="APROVADO", justificativa="Conferido", usuario_id=usuario.id, usuario_role="agronomo")

    export_svc = CadernoExportacaoService(session, tenant_id)
    exportacao = await export_svc.gerar(ExportacaoCreate(safra_id=safra_id, modo_exportacao="OFICIAL"))
    assert exportacao.hash_documental
    assert exportacao.assinado_em is None

    assinada = await export_svc.registrar_assinatura(
        exportacao.id,
        usuario=usuario,
        responsavel_tecnico_id=usuario.id,
        responsavel_tecnico_nome="Nome Livre do Frontend",
        crea_rt="12345/UF",
        observacao="Assinatura técnica do caderno",
        ip_address="127.0.0.1",
    )

    assert assinada.responsavel_tecnico_id == usuario.id
    assert assinada.responsavel_tecnico_nome == usuario.nome_completo
    assert assinada.assinatura_hash == assinada.hash_documental
    assert assinada.assinado_em is not None

    audit_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                  FROM tenant_audit_log
                 WHERE tenant_id = :tenant_id
                   AND resource = 'caderno_exportacoes'
                   AND action = 'sign'
                """
            ),
            {"tenant_id": str(tenant_id)},
        )
    ).scalar_one()
    assert audit_count == 1


@pytest.mark.asyncio
async def test_exportacao_isolamento_por_tenant(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    safra_a, talhao_a, usuario_a = await _seed_tenant(session, tenant_a)
    safra_b, talhao_b, usuario_b = await _seed_tenant(session, tenant_b)

    svc_a = CadernoExportacaoService(session, tenant_a)
    svc_b = CadernoExportacaoService(session, tenant_b)
    caderno_a = CadernoCampoService(session, tenant_a)
    caderno_b = CadernoCampoService(session, tenant_b)

    entrada_a = await _criar_entrada(session, tenant_a, safra_a, talhao_a, usuario_a.id, status="PENDENTE_APROVACAO", descricao="A")
    entrada_b = await _criar_entrada(session, tenant_b, safra_b, talhao_b, usuario_b.id, status="PENDENTE_APROVACAO", descricao="B")
    await caderno_a.alterar_status_evento(entrada_a, novo_status="APROVADO", justificativa="ok", usuario_id=usuario_a.id, usuario_role="agronomo")
    await caderno_b.alterar_status_evento(entrada_b, novo_status="APROVADO", justificativa="ok", usuario_id=usuario_b.id, usuario_role="agronomo")

    exp_a = await svc_a.gerar(ExportacaoCreate(safra_id=safra_a, modo_exportacao="OFICIAL"))
    exp_b = await svc_b.gerar(ExportacaoCreate(safra_id=safra_b, modo_exportacao="OFICIAL"))

    lista_a = await svc_a.listar_todas()
    lista_b = await svc_b.listar_todas()

    assert exp_a.id in [e.id for e in lista_a]
    assert exp_b.id in [e.id for e in lista_b]
    assert all(e.tenant_id == tenant_a for e in lista_a)
    assert all(e.tenant_id == tenant_b for e in lista_b)
