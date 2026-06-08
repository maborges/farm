import uuid

import pytest
from sqlalchemy import text

pytest_plugins = ("tests.integration.conftest",)

from tests.integration.conftest import FAZENDA_ID, TENANT_ID, USER_ID
from tests.integration.helpers import garantir_assinatura
from tests.integration.operacional.test_estoque_implantacao import _garantir_schema_confirmacao


async def _garantir_base_runbook(session) -> None:
    await session.execute(text("""
        DELETE FROM estoque_implantacao_itens WHERE tenant_id = :tenant_id
    """), {"tenant_id": str(TENANT_ID)})
    await session.execute(text("""
        DELETE FROM estoque_implantacao_sessoes WHERE tenant_id = :tenant_id
    """), {"tenant_id": str(TENANT_ID)})
    await session.execute(text("""
        DELETE FROM tenant_audit_log
         WHERE tenant_id = :tenant_id
           AND resource IN ('estoque_implantacao_sessoes', 'estoque_implantacao_itens')
    """), {"tenant_id": str(TENANT_ID)})

    await session.execute(text("""
        INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at)
        VALUES (:id, :email, :username, :nome_completo, :senha_hash, true, false, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(USER_ID),
        "email": "smoke-implantacao@teste.local",
        "username": "smoke_implantacao",
        "nome_completo": "Smoke Implantacao Estoque",
        "senha_hash": "hash-nao-utilizado-nos-testes-smoke",
    })

    await session.execute(text("""
        INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
        VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(TENANT_ID),
        "nome": "Tenant Smoke Implantacao",
        "documento": "12345678901",
    })

    await session.execute(text("""
        INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, is_owner, status, created_at)
        SELECT :id, :tenant_id, :usuario_id, true, 'ATIVO', NOW()
        WHERE NOT EXISTS (
            SELECT 1
              FROM tenant_usuarios
             WHERE tenant_id = :tenant_id
               AND usuario_id = :usuario_id
        )
    """), {
        "id": str(uuid.uuid4()),
        "tenant_id": str(TENANT_ID),
        "usuario_id": str(USER_ID),
    })

    await session.execute(text("""
        INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, :nome, true, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(FAZENDA_ID),
        "tenant_id": str(TENANT_ID),
        "nome": "Fazenda Smoke Implantacao",
    })

    await garantir_assinatura(session, TENANT_ID)
    await session.commit()


def _payload_produto(nome: str, codigo: str) -> dict:
    return {
        "nome": nome,
        "unidade_medida": "L",
        "tipo": "INSUMO",
        "descricao": "Produto criado pelo smoke test da implantacao assistida.",
        "codigo_interno": codigo,
    }


@pytest.mark.asyncio
async def test_estoque_implantacao_runbook_smoke(client, session, headers_admin):
    await _garantir_schema_confirmacao(session)
    await _garantir_base_runbook(session)

    produto_codigo = f"SMK-{uuid.uuid4().hex[:8].upper()}"
    produto_nome = f"Herbicida Smoke {uuid.uuid4().hex[:6]}"
    deposito_nome = f"Deposito Smoke {uuid.uuid4().hex[:6]}"
    quantidade = 17.5
    custo_unitario = 12.4

    criar_produto = await client.post(
        "/api/v1/cadastros/produtos",
        json=_payload_produto(produto_nome, produto_codigo),
        headers=headers_admin,
    )
    assert criar_produto.status_code == 201, criar_produto.text
    produto = criar_produto.json()

    criar_deposito = await client.post(
        "/api/v1/estoque/depositos",
        json={
            "unidade_produtiva_id": str(FAZENDA_ID),
            "nome": deposito_nome,
            "tipo": "GERAL",
            "localizacao_desc": "Almoxarifado principal do smoke test",
        },
        headers=headers_admin,
    )
    assert criar_deposito.status_code == 201, criar_deposito.text
    deposito = criar_deposito.json()

    csv_legado = (
        "produto_codigo,produto_nome,deposito_nome,quantidade,unidade,custo_unitario,lote,validade,observacoes\n"
        f"{produto_codigo},{produto_nome},{deposito_nome},{quantidade},L,{custo_unitario},LOTE-SMOKE,,Carga inicial do smoke test\n"
    ).encode("utf-8")

    criar_sessao = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_admin,
        data={"unidade_produtiva_id": str(FAZENDA_ID)},
        files={"file": ("estoque_implantacao_smoke.csv", csv_legado, "text/csv")},
    )
    assert criar_sessao.status_code == 201, criar_sessao.text
    sessao = criar_sessao.json()
    sessao_id = sessao["id"]
    assert sessao["status"] == "PRONTO_PARA_CONFIRMAR"
    assert sessao["linhas_com_erro"] == 0

    aptidao_resp = await client.get(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/aptidao-confirmacao",
        headers=headers_admin,
    )
    assert aptidao_resp.status_code == 200, aptidao_resp.text
    aptidao = aptidao_resp.json()
    assert aptidao["apta"] is True
    assert aptidao["total_itens_confirmaveis"] == 1

    confirmar_resp = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar",
        headers=headers_admin,
        json={
            "confirmar_avisos": True,
            "observacao": "Smoke test operacional do runbook de implantacao assistida.",
        },
    )
    assert confirmar_resp.status_code == 200, confirmar_resp.text
    confirmado = confirmar_resp.json()
    assert confirmado["status"] == "CONFIRMADO"
    assert confirmado["confirmado_por"] == str(USER_ID)

    saldos_resp = await client.get(
        f"/api/v1/estoque/saldos?unidade_produtiva_id={FAZENDA_ID}&produto_id={produto['id']}&deposito_id={deposito['id']}",
        headers=headers_admin,
    )
    assert saldos_resp.status_code == 200, saldos_resp.text
    saldos = saldos_resp.json()
    assert len(saldos) == 1
    saldo = saldos[0]
    assert saldo["produto_id"] == produto["id"]
    assert saldo["deposito_id"] == deposito["id"]
    assert saldo["quantidade_atual"] == quantidade

    movimento = (
        await session.execute(
            text("""
                SELECT tipo_movimento, origem, origem_id, observacoes, quantidade
                  FROM estoque_movimentos
                 WHERE tenant_id = :tenant_id
                   AND produto_id = :produto_id
                   AND deposito_id = :deposito_id
                 ORDER BY created_at DESC
                 LIMIT 1
            """),
            {
                "tenant_id": str(TENANT_ID),
                "produto_id": produto["id"],
                "deposito_id": deposito["id"],
            },
        )
    ).mappings().first()
    assert movimento is not None
    assert movimento["tipo_movimento"] == "SALDO_INICIAL"
    assert movimento["origem"] == "IMPLANTACAO"
    assert float(movimento["quantidade"]) == quantidade
    assert str(sessao_id) in (movimento["observacoes"] or "")

    audit = (
        await session.execute(
            text("""
                SELECT action, resource, user_id
                  FROM tenant_audit_log
                 WHERE tenant_id = :tenant_id
                   AND resource_id = :resource_id
                 ORDER BY created_at DESC
                 LIMIT 1
            """),
            {
                "tenant_id": str(TENANT_ID),
                "resource_id": sessao_id,
            },
        )
    ).mappings().first()
    assert audit is not None
    assert audit["action"] == "confirm_session"
    assert audit["resource"] == "estoque_implantacao_sessoes"
    assert str(audit["user_id"]) == str(USER_ID)
