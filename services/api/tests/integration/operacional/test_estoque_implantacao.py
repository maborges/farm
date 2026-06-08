import uuid

import pytest
from sqlalchemy import text

from core.services.auth_service import AuthService
import operacional.models.estoque  # noqa: F401
import operacional.models.estoque_implantacao  # noqa: F401
from operacional.models.estoque_implantacao import EstoqueImplantacaoItem, EstoqueImplantacaoSessao
from tests.integration.conftest import FAZENDA_ID, TENANT_ID, USER_ID
from tests.integration.helpers import garantir_assinatura
from unittest.mock import MagicMock


OUTRO_TENANT_ID = uuid.UUID("ff100003-0000-0000-0000-000000000003")
OUTRA_FAZENDA_ID = uuid.UUID("ff100004-0000-0000-0000-000000000004")


def _headers_para_tenant(tenant_id: uuid.UUID, fazenda_id: uuid.UUID) -> dict[str, str]:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(USER_ID),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": str(fazenda_id), "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    token = svc.create_access_token(claims)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
        "X-Fazenda-ID": str(fazenda_id),
    }


async def _garantir_suporte_implantacao(session, *, tenant_id: uuid.UUID, fazenda_id: uuid.UUID, deposito_id: uuid.UUID, produto_id: uuid.UUID, nome_produto: str = "Herbicida X") -> None:
    await session.execute(text("""
        DELETE FROM estoque_implantacao_itens WHERE tenant_id = :tenant_id
    """), {"tenant_id": str(tenant_id)})
    await session.execute(text("""
        DELETE FROM estoque_implantacao_sessoes WHERE tenant_id = :tenant_id
    """), {"tenant_id": str(tenant_id)})
    await session.execute(text("""
        DELETE FROM tenant_audit_log
         WHERE tenant_id = :tenant_id
           AND resource IN ('estoque_implantacao_sessoes', 'estoque_implantacao_itens')
    """), {"tenant_id": str(tenant_id)})

    await session.execute(text("""
        INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at)
        VALUES (:id, :email, :username, :nome_completo, :senha_hash, true, false, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(USER_ID),
        "email": "operacional-implantacao@teste.local",
        "username": "operacional_implantacao",
        "nome_completo": "Operador Implantacao Estoque",
        "senha_hash": "hash-nao-utilizado-nos-testes-http",
    })

    await session.execute(text("""
        INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
        VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(tenant_id),
        "nome": f"Tenant {str(tenant_id)[:8]}",
        "documento": str(tenant_id).replace("-", "")[:11],
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
        "tenant_id": str(tenant_id),
        "usuario_id": str(USER_ID),
    })

    await session.execute(text("""
        INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, :nome, true, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(fazenda_id),
        "tenant_id": str(tenant_id),
        "nome": f"Fazenda {str(fazenda_id)[:8]}",
    })

    await session.execute(text("""
        INSERT INTO estoque_depositos (id, tenant_id, unidade_produtiva_id, nome, tipo, ativo)
        VALUES (:id, :tenant_id, :unidade_produtiva_id, 'Deposito Central', 'ALMOXARIFADO', true)
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(deposito_id),
        "tenant_id": str(tenant_id),
        "unidade_produtiva_id": str(fazenda_id),
    })

    await session.execute(text("""
        INSERT INTO cadastros_produtos
            (id, tenant_id, nome, tipo, unidade_medida, estoque_minimo, preco_medio, ativo, codigo_interno)
        VALUES (:id, :tenant_id, :nome, 'INSUMO', 'L', 0, 0.0, true, 'ABC123')
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(produto_id),
        "tenant_id": str(tenant_id),
        "nome": nome_produto,
    })

    await garantir_assinatura(session, tenant_id)
    await session.commit()


async def _criar_deposito(
    session,
    *,
    tenant_id: uuid.UUID,
    fazenda_id: uuid.UUID,
    deposito_id: uuid.UUID,
    nome: str,
) -> None:
    await session.execute(text("""
        INSERT INTO estoque_depositos (id, tenant_id, unidade_produtiva_id, nome, tipo, ativo)
        VALUES (:id, :tenant_id, :unidade_produtiva_id, :nome, 'ALMOXARIFADO', true)
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(deposito_id),
        "tenant_id": str(tenant_id),
        "unidade_produtiva_id": str(fazenda_id),
        "nome": nome,
    })
    await session.commit()


async def _garantir_schema_confirmacao(session) -> None:
    conn = await session.connection()
    await conn.run_sync(lambda sync_conn: EstoqueImplantacaoSessao.__table__.create(sync_conn, checkfirst=True))
    await conn.run_sync(lambda sync_conn: EstoqueImplantacaoItem.__table__.create(sync_conn, checkfirst=True))
    await session.execute(text("""
        ALTER TABLE estoque_implantacao_sessoes
        ADD COLUMN IF NOT EXISTS confirmado_por UUID
    """))
    await session.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM pg_constraint
                 WHERE conname = 'fk_estoque_implantacao_sessoes_confirmado_por'
            ) THEN
                ALTER TABLE estoque_implantacao_sessoes
                ADD CONSTRAINT fk_estoque_implantacao_sessoes_confirmado_por
                FOREIGN KEY (confirmado_por) REFERENCES usuarios(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """))
    await session.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM pg_constraint
                 WHERE conname = 'ck_estoque_movimentos_origem'
            ) THEN
                ALTER TABLE estoque_movimentos DROP CONSTRAINT ck_estoque_movimentos_origem;
            END IF;
            ALTER TABLE estoque_movimentos
            ADD CONSTRAINT ck_estoque_movimentos_origem
            CHECK (origem IN ('OPERACAO_EXECUCAO','COMPRA','COLHEITA','AJUSTE','MANUAL','TRANSFERENCIA','IMPLANTACAO')) NOT VALID;
        END $$;
    """))
    await session.commit()


@pytest.mark.asyncio
async def test_fluxo_http_implantacao_cria_corrige_revalida_confirma(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )

    csv_invalido = (
        "produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "Produto Desconhecido,Deposito Central,12,9.5\n"
    ).encode("utf-8")

    criar = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("estoque.csv", csv_invalido, "text/csv")},
    )
    assert criar.status_code == 201, criar.text
    sessao = criar.json()
    sessao_id = sessao["id"]
    assert sessao["status"] == "VALIDADO_COM_ERROS"

    listar = await client.get("/api/v1/estoque/implantacao-assistida/sessoes", headers=headers_operacional)
    assert listar.status_code == 200, listar.text
    assert any(item["id"] == sessao_id for item in listar.json()["itens"])

    itens_resp = await client.get(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/itens",
        headers=headers_operacional,
    )
    assert itens_resp.status_code == 200, itens_resp.text
    itens = itens_resp.json()["itens"]
    assert len(itens) == 1
    item_id = itens[0]["id"]
    assert itens[0]["status"] == "ERRO"

    corrigir = await client.patch(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/itens/{item_id}",
        headers=headers_operacional,
        json={
            "produto_id_resolvido": str(produto_id),
            "deposito_id_resolvido": str(deposito_id),
            "quantidade": 12,
            "custo_unitario": 9.5,
        },
    )
    assert corrigir.status_code == 200, corrigir.text

    revalidar = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/revalidar",
        headers=headers_operacional,
    )
    assert revalidar.status_code == 200, revalidar.text
    assert revalidar.json()["status"] == "PRONTO_PARA_CONFIRMAR"

    aptidao = await client.get(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/aptidao-confirmacao",
        headers=headers_operacional,
    )
    assert aptidao.status_code == 200, aptidao.text
    aptidao_body = aptidao.json()
    assert aptidao_body["apta"] is True
    assert aptidao_body["total_itens_confirmaveis"] == 1

    confirmar = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar",
        headers=headers_operacional,
        json={
            "confirmar_avisos": True,
            "observacao": "Carga inicial validada pelo almoxarifado",
        },
    )
    assert confirmar.status_code == 200, confirmar.text
    confirmado = confirmar.json()
    assert confirmado["status"] == "CONFIRMADO"
    assert confirmado["confirmado_por"] == str(USER_ID)

    movimento = (
        await session.execute(
            text("""
                SELECT tipo_movimento, origem, origem_id, observacoes
                  FROM estoque_movimentos
                 WHERE tenant_id = :tenant_id
                   AND produto_id = :produto_id
                   AND deposito_id = :deposito_id
                 ORDER BY created_at DESC
                 LIMIT 1
            """),
            {
                "tenant_id": str(TENANT_ID),
                "produto_id": str(produto_id),
                "deposito_id": str(deposito_id),
            },
        )
    ).mappings().first()
    assert movimento is not None
    assert movimento["tipo_movimento"] == "SALDO_INICIAL"
    assert movimento["origem"] == "IMPLANTACAO"
    assert "Implantacao assistida sessao" in (movimento["observacoes"] or "")

    audit = (
        await session.execute(
            text("""
                SELECT action, resource
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


@pytest.mark.asyncio
async def test_confirmacao_http_bloqueia_sessao_com_erro(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )

    csv_invalido = (
        "produto_nome,deposito_nome,quantidade\n"
        "Produto Inexistente,Deposito Central,10\n"
    ).encode("utf-8")

    criar = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("erro.csv", csv_invalido, "text/csv")},
    )
    assert criar.status_code == 201, criar.text
    sessao_id = criar.json()["id"]

    confirmar = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar",
        headers=headers_operacional,
        json={"confirmar_avisos": True},
    )
    assert confirmar.status_code in (400, 422), confirmar.text


@pytest.mark.asyncio
async def test_csv_duplicado_retorna_erro_controlado(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )

    csv_valido = (
        "produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "ABC123,Herbicida X,Deposito Central,5,10\n"
    ).encode("utf-8")

    primeiro = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("duplicado.csv", csv_valido, "text/csv")},
    )
    assert primeiro.status_code == 201, primeiro.text

    duplicado = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("duplicado.csv", csv_valido, "text/csv")},
    )
    assert duplicado.status_code in (400, 422), duplicado.text
    assert "mesmo csv" in duplicado.text.lower()


@pytest.mark.asyncio
async def test_confirmacao_http_bloqueia_segunda_confirmacao(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )

    csv_valido = (
        "produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "ABC123,Herbicida X,Deposito Central,5,10\n"
    ).encode("utf-8")

    criar = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("confirmar.csv", csv_valido, "text/csv")},
    )
    assert criar.status_code == 201, criar.text
    sessao_id = criar.json()["id"]

    confirmar = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar",
        headers=headers_operacional,
        json={"confirmar_avisos": True},
    )
    assert confirmar.status_code == 200, confirmar.text

    confirmar_novamente = await client.post(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/confirmar",
        headers=headers_operacional,
        json={"confirmar_avisos": True},
    )
    assert confirmar_novamente.status_code in (400, 422), confirmar_novamente.text


@pytest.mark.asyncio
async def test_correcao_http_bloqueia_deposito_de_outra_unidade_produtiva(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    outra_fazenda = uuid.uuid4()
    deposito_outra_fazenda = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )
    await session.execute(text("""
        INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, :nome, true, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {
        "id": str(outra_fazenda),
        "tenant_id": str(TENANT_ID),
        "nome": "Outra Fazenda",
    })
    await _criar_deposito(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=outra_fazenda,
        deposito_id=deposito_outra_fazenda,
        nome="Deposito Secundario",
    )

    csv_invalido = (
        "produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "Produto Desconhecido,Deposito Central,12,9.5\n"
    ).encode("utf-8")

    criar = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        data={"unidade_produtiva_id": str(FAZENDA_ID)},
        files={"file": ("unidade.csv", csv_invalido, "text/csv")},
    )
    assert criar.status_code == 201, criar.text
    sessao_id = criar.json()["id"]

    itens_resp = await client.get(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/itens",
        headers=headers_operacional,
    )
    item_id = itens_resp.json()["itens"][0]["id"]

    corrigir = await client.patch(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}/itens/{item_id}",
        headers=headers_operacional,
        json={
            "produto_id_resolvido": str(produto_id),
            "deposito_id_resolvido": str(deposito_outra_fazenda),
            "quantidade": 12,
        },
    )
    assert corrigir.status_code in (400, 422), corrigir.text
    assert "outra unidade produtiva" in corrigir.text.lower()


@pytest.mark.asyncio
async def test_sessoes_implantacao_isoladas_por_tenant(client, session, headers_operacional):
    await _garantir_schema_confirmacao(session)
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    await _garantir_suporte_implantacao(
        session,
        tenant_id=TENANT_ID,
        fazenda_id=FAZENDA_ID,
        deposito_id=deposito_id,
        produto_id=produto_id,
    )
    await _garantir_suporte_implantacao(
        session,
        tenant_id=OUTRO_TENANT_ID,
        fazenda_id=OUTRA_FAZENDA_ID,
        deposito_id=uuid.uuid4(),
        produto_id=uuid.uuid4(),
        nome_produto="Produto Outro Tenant",
    )

    csv_valido = (
        "produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\n"
        "ABC123,Herbicida X,Deposito Central,5,10\n"
    ).encode("utf-8")

    criar = await client.post(
        "/api/v1/estoque/implantacao-assistida/sessoes",
        headers=headers_operacional,
        files={"file": ("isolamento.csv", csv_valido, "text/csv")},
    )
    assert criar.status_code == 201, criar.text
    sessao_id = criar.json()["id"]

    outro_headers = _headers_para_tenant(OUTRO_TENANT_ID, OUTRA_FAZENDA_ID)

    listar = await client.get("/api/v1/estoque/implantacao-assistida/sessoes", headers=outro_headers)
    assert listar.status_code == 200, listar.text
    assert all(item["id"] != sessao_id for item in listar.json()["itens"])

    obter = await client.get(
        f"/api/v1/estoque/implantacao-assistida/sessoes/{sessao_id}",
        headers=outro_headers,
    )
    assert obter.status_code == 404, obter.text
