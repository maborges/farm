"""Suíte de testes para o Cofre Segregado BYOK e Proxy Seguro de Cotações (Fase C3).

Verifica:
1. Criptografia AES-256-GCM com Envelope Encryption (DEK efêmera + KEK versionada).
2. Rotação de KEK KMS (v1 para v2) sem decifrar os dados brutos.
3. Isolamento criptográfico e de dados entre múltiplos usuários (multi-tenant individual).
4. Catálogo de provedores e bloqueio mandatório por compliance de licença (Twelve Data, Polygon, IBKR).
5. Prevenção rigorosa de SSRF e rejeição de URLs e IPs arbitrários.
6. Rate limiting por usuário/provedor com fallback gracioso em memória.
7. Cache privado estritamente isolado por usuário (sem colisão com cache público).
8. Contrato de cotações com separação rigorosa de Mercado FÍSICO vs FUTURO.
9. Revogação e exclusão permanente de credenciais.
10. Ausência absoluta de segredos em texto claro em respostas HTTP e logs.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from agro_identity.byok_proxy import (
    BYOK_PROVIDERS_CATALOG,
    ByokPrivateCache,
    ByokProxyService,
    ByokRateLimiter,
    clear_local_byok_cache,
    validar_ssrf_safety,
)
from agro_identity.byok_vault import (
    ByokVaultService,
    EnvelopeEncryptionEngine,
    LocalKmsKeyManager,
    mascarar_chave,
)
from agro_identity.config import AGRO_VAULT_MASTER_KEY
from agro_identity.email_dispatch import clear_sent_emails
from agro_identity.schemas import ByokProviderStatus, SituacaoCotacao, TipoMercado
from core.database import Base
from core.dependencies import get_session
from core.models.auth import Usuario
from core.models.sessao import SessaoAtiva
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.usuario_byok import UsuarioByokCredential
from core.services.auth_service import AuthService
from datetime import datetime, timezone, timedelta
import hashlib
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from main import app


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    """Garante schema atualizado com tabelas do cofre BYOK e usuários na sessão central isolada."""
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    is_ci = os.getenv("CI_POSTGRESQL") == "true" or os.getenv("GITHUB_ACTIONS") == "true"

    if db_url and "postgresql" in db_url:
        connect_args = {
            "server_settings": {
                "search_path": "farms,public",
            }
        }
        test_engine = create_async_engine(
            db_url,
            connect_args=connect_args,
            poolclass=NullPool,
        )
    elif is_ci:
        raise RuntimeError(
            "CI detectada mas nenhum PostgreSQL fornecido. Fallback para SQLite é proibido."
        )
    else:
        test_db = tmp_path / "test_byok_central.db"
        test_engine = create_async_engine(
            f"sqlite+aiosqlite:///{test_db}",
            poolclass=NullPool,
        )

    if "sqlite" in str(test_engine.url):
        from sqlalchemy import event

        @event.listens_for(test_engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async def init_tables():
        async with test_engine.begin() as conn:
            if "postgresql" in str(test_engine.url):
                from sqlalchemy import text
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS farms"))
                await conn.execute(text("SET search_path TO farms, public"))
            tables = [
                Usuario.__table__,
                Tenant.__table__,
                UnidadeProdutiva.__table__,
                UsuarioByokCredential.__table__,
                SessaoAtiva.__table__,
            ]
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=tables
                )
            )

    asyncio.run(init_tables())
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    clear_sent_emails()
    clear_local_byok_cache()

    yield

    app.dependency_overrides.pop(get_session, None)
    asyncio.run(test_engine.dispose())


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def criar_usuario_autenticado(client: TestClient, prefixo: str = "produtor") -> tuple[dict, str]:
    """Cria um usuário individual homologado e retorna (usuario_dict, session_token)."""
    user_id = uuid.uuid4()
    email = f"{prefixo}_{uuid.uuid4().hex[:8]}@agro.com.br"
    nome = f"Usuário {prefixo.capitalize()}"

    svc = AuthService(None)
    claims = {
        "sub": str(user_id),
        "email": email,
        "is_superuser": False,
        "account_type": "INDIVIDUAL_FREE",
        "product_scope": ["agro:free"],
        "token_version": 2,
    }
    token = svc.create_access_token(data=claims)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    agora = datetime.now(timezone.utc)

    async def _insert_user_and_session():
        override = app.dependency_overrides.get(get_session)
        if not override:
            return
        gen = override()
        try:
            session = await gen.__anext__()
            try:
                user = Usuario(
                    id=user_id,
                    email=email,
                    username=email.split("@")[0],
                    nome_completo=nome,
                    apelido=prefixo,
                    senha_hash="dummy_hash",
                    ativo=True,
                )
                sessao = SessaoAtiva(
                    tenant_id=None,
                    usuario_id=user_id,
                    token_hash=token_hash,
                    ip_address="testclient",
                    user_agent="testclient",
                    inicio=agora,
                    ultimo_heartbeat=agora,
                    expira_em=agora + timedelta(minutes=60),
                    status="ATIVA",
                )
                session.add(user)
                session.add(sessao)
                await session.commit()
            finally:
                await session.close()
        finally:
            await gen.aclose()

    if hasattr(client, "portal") and client.portal is not None:
        client.portal.call(_insert_user_and_session)
    else:
        asyncio.run(_insert_user_and_session())

    user_data = {
        "id": str(user_id),
        "email": email,
        "nome": nome,
        "role": "PRODUTOR_INDIVIDUAL",
    }
    return user_data, token


# ============================================================================
# 1. TESTES CRIPTOGRÁFICOS DE ENVELOPE ENCRYPTION E ROTAÇÃO
# ============================================================================

def test_01_envelope_encryption_e_decriptacao():
    """Valida o ciclo de Envelope Encryption com AES-256-GCM, DEK individual e KEK derivada."""
    kms = LocalKmsKeyManager(AGRO_VAULT_MASTER_KEY)
    engine = EnvelopeEncryptionEngine(kms)

    user_id = uuid.uuid4()
    provider = "SIMULATED"
    segredo_original = "segredo_super_confidencial_api_key_agro_2026"

    # 1. Criptografia em duas camadas
    record = engine.encrypt_secret(
        user_id=user_id,
        provider_slug=provider,
        plaintext_secret=segredo_original,
        key_version=1,
    )

    assert record.key_version == 1
    assert record.mascara_chave == mascarar_chave(segredo_original)
    assert record.ciphertext_b64 != segredo_original
    assert record.dek_encrypted_b64 is not None

    # 2. Decriptação com sucesso
    segredo_recuperado = engine.decrypt_secret(user_id, provider, record)
    assert segredo_recuperado == segredo_original

    # 3. Adulteração do ciphertext deve causar falha por tag GCM inválida
    adulterado = record.__class__(
        ciphertext_b64="YWR1bHRlcmFkbw==",  # "adulterado" em base64
        data_nonce_b64=record.data_nonce_b64,
        dek_encrypted_b64=record.dek_encrypted_b64,
        dek_nonce_b64=record.dek_nonce_b64,
        key_version=record.key_version,
        mascara_chave=record.mascara_chave,
    )
    with pytest.raises(Exception):  # HTTPException 400
        engine.decrypt_secret(user_id, provider, adulterado)


def test_02_rotacao_de_kek_kms():
    """Testa a rotação de versão da KEK (v1 -> v2) sem modificar o payload de dados cifrado."""
    kms = LocalKmsKeyManager(AGRO_VAULT_MASTER_KEY)
    engine = EnvelopeEncryptionEngine(kms)

    user_id = uuid.uuid4()
    provider = "SIMULATED"
    segredo_original = "chave_para_rotacao_987654321"

    # Criptografa na v1
    record_v1 = engine.encrypt_secret(user_id, provider, segredo_original, key_version=1)
    assert record_v1.key_version == 1

    # Rotaciona para a v2
    record_v2 = engine.rotate_key(user_id, provider, record_v1, new_version=2)
    assert record_v2.key_version == 2
    # O ciphertext dos dados brutos e o data_nonce DEVEM ser exatamente iguais
    assert record_v2.ciphertext_b64 == record_v1.ciphertext_b64
    assert record_v2.data_nonce_b64 == record_v1.data_nonce_b64
    # A DEK cifrada e o dek_nonce DEVEM ter sido re-gerados para a nova KEK
    assert record_v2.dek_encrypted_b64 != record_v1.dek_encrypted_b64

    # Decripta o registro na v2 e comprova recuperação íntegra
    recuperado_v2 = engine.decrypt_secret(user_id, provider, record_v2)
    assert recuperado_v2 == segredo_original


# ============================================================================
# 2. ISOLAMENTO MULTI-USUÁRIO
# ============================================================================

def test_03_isolamento_de_credenciais_entre_usuarios(client: TestClient):
    """Garante que Usuário A e Usuário B têm cofre completamente segregado."""
    # Cria Usuário A
    user_a, token_a = criar_usuario_autenticado(client, "user_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Cria Usuário B
    user_b, token_b = criar_usuario_autenticado(client, "user_b")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Usuário A salva credencial SIMULATED no cofre
    resp_save_a = client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers_a,
        json={"providerSlug": "SIMULATED", "apiKey": "chave_secreta_usuario_a_1234"},
    )
    assert resp_save_a.status_code == 201
    data_a = resp_save_a.json()
    assert data_a["usuarioId"] == user_a["id"]
    assert data_a["mascaraChave"] == mascarar_chave("chave_secreta_usuario_a_1234")
    assert "chave_secreta" not in str(data_a)

    # 2. Usuário B lista credenciais: seu cofre DEVE estar vazio
    resp_list_b = client.get("/api/v1/agro/byok/credentials", headers=headers_b)
    assert resp_list_b.status_code == 200
    assert resp_list_b.json() == []

    # 3. Usuário B tenta excluir a credencial do Usuário A: deve receber 404 Not Found
    resp_del_b = client.delete("/api/v1/agro/byok/credentials/SIMULATED", headers=headers_b)
    assert resp_del_b.status_code == 404

    # 4. Usuário A continua com sua credencial ativa e íntegra
    resp_list_a = client.get("/api/v1/agro/byok/credentials", headers=headers_a)
    assert resp_list_a.status_code == 200
    assert len(resp_list_a.json()) == 1
    assert resp_list_a.json()[0]["providerSlug"] == "SIMULATED"


def test_04_bloqueio_criptografico_de_acesso_cruzado():
    """Garante que tentar decifrar segredo do Usuário A com ID do Usuário B falha via AAD."""
    kms = LocalKmsKeyManager(AGRO_VAULT_MASTER_KEY)
    engine = EnvelopeEncryptionEngine(kms)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    provider = "SIMULATED"

    record_a = engine.encrypt_secret(user_a, provider, "chave_privada_a_123")

    # Tentativa de decifrar passando o UUID do Usuário B (simulando ataque ou vazamento de banco)
    with pytest.raises(Exception):
        engine.decrypt_secret(user_b, provider, record_a)


# ============================================================================
# 3. COMPLIANCE DE LICENCIAMENTO E CATÁLOGO DE PROVEDORES
# ============================================================================

def test_05_catalogo_de_provedores_e_bloqueio_de_licenca(client: TestClient):
    """Verifica se Twelve Data, Polygon e IBKR são bloqueados por restrições contratuais."""
    user, token = criar_usuario_autenticado(client, "licenca")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Catálogo oficial
    resp_cat = client.get("/api/v1/agro/byok/providers", headers=headers)
    assert resp_cat.status_code == 200
    providers = resp_cat.json()
    assert len(providers) >= 4

    slugs = {p["slug"]: p for p in providers}
    assert slugs["SIMULATED"]["status"] == "ATIVO"
    assert slugs["TWELVE_DATA"]["status"] == "DESABILITADO_LICENCA"
    assert slugs["POLYGON"]["status"] == "DESABILITADO_LICENCA"
    assert slugs["IBKR"]["status"] == "DESABILITADO_LICENCA"

    # 2. Tentativa de cadastrar chave para Twelve Data deve retornar 403 Forbidden
    resp_twelve = client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "TWELVE_DATA", "apiKey": "twelve_data_live_key_fail"},
    )
    assert resp_twelve.status_code == 403
    assert "desabilitado" in resp_twelve.json()["detail"].lower()

    # 3. Tentativa de cadastrar chave para Polygon deve retornar 403 Forbidden
    resp_poly = client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "POLYGON", "apiKey": "polygon_api_key_fail"},
    )
    assert resp_poly.status_code == 403

    # 4. Tentativa de cadastrar chave para IBKR deve retornar 403 Forbidden
    resp_ibkr = client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "IBKR", "apiKey": "ibkr_api_key_fail"},
    )
    assert resp_ibkr.status_code == 403


# ============================================================================
# 4. PREVENÇÃO DE SSRF E ENTRADAS MALICIOSAS
# ============================================================================

def test_06_prevencao_estrita_de_ssrf(client: TestClient):
    """Comprova o bloqueio imediato de injeções de URLs, esquemas locais e IPs privados."""
    user, token = criar_usuario_autenticado(client, "ssrf")
    headers = {"Authorization": f"Bearer {token}"}

    # Cadastra credencial simulada
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "sim_key_valid_123"},
    )

    ataques_ssrf = [
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "http://127.0.0.1:8000/internal",
        "localhost",
        "10.0.0.1",
        "192.168.1.1",
        "gopher://localhost:6379",
    ]

    import urllib.parse

    for payload in ataques_ssrf:
        # Injeção no parâmetro commodity
        encoded_payload = urllib.parse.quote(payload, safe="")
        resp = client.get(
            f"/api/v1/agro/byok/cotacoes/{encoded_payload}?tipo_mercado=FISICO&provedor=SIMULATED",
            headers=headers,
        )
        assert resp.status_code == 400

        # Injeção no parâmetro provedor
        resp_prov = client.get(
            f"/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor={urllib.parse.quote(payload, safe='')}",
            headers=headers,
        )
        assert resp_prov.status_code == 400

    # Commodity fora do catálogo permitido
    resp_invalido = client.get(
        "/api/v1/agro/byok/cotacoes/CRIPTOMOEDA_X?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_invalido.status_code == 400


# ============================================================================
# 5. CONTRATO DE COTAÇÕES (FÍSICO VS FUTURO)
# ============================================================================

def test_07_contrato_cotacoes_separacao_fisico_vs_futuro(client: TestClient):
    """Comprova padronização e separação rigorosa entre Mercado FÍSICO e FUTURO."""
    user, token = criar_usuario_autenticado(client, "mercado")
    headers = {"Authorization": f"Bearer {token}"}

    # Registra chave simulada
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "sim_agro_key_999"},
    )

    # 1. SOJA FÍSICO (Paranaguá, R$/saca 60kg, Fechamento diário)
    resp_soja_fis = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_soja_fis.status_code == 200
    soja_f = resp_soja_fis.json()
    assert soja_f["commodity"] == "SOJA"
    assert soja_f["tipoMercado"] == "FISICO"
    assert soja_f["moeda"] == "BRL"
    assert soja_f["unidade"] == "saca 60kg"
    assert "Paranaguá" in soja_f["bolsaOuRegiao"]
    assert soja_f["situacao"] == "FECHAMENTO"
    assert soja_f["cached"] is False
    assert soja_f["titularidadeByok"].startswith(f"BYOK-{user['id'][:8]}")

    # 2. SOJA FUTURO (CBOT ZS, USD Cents/bushel, Tempo Real)
    resp_soja_fut = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_soja_fut.status_code == 200
    soja_fut = resp_soja_fut.json()
    assert soja_fut["commodity"] == "SOJA"
    assert soja_fut["tipoMercado"] == "FUTURO"
    assert soja_fut["moeda"] == "USD_CENT"
    assert soja_fut["unidade"] == "bushel"
    assert "CBOT" in soja_fut["bolsaOuRegiao"]
    assert soja_fut["situacao"] == "TEMPO_REAL"

    # 3. MILHO FÍSICO vs FUTURO
    resp_milho_fis = client.get(
        "/api/v1/agro/byok/cotacoes/MILHO?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_milho_fis.status_code == 200
    assert resp_milho_fis.json()["moeda"] == "BRL"
    assert "Campinas" in resp_milho_fis.json()["bolsaOuRegiao"]

    resp_milho_fut = client.get(
        "/api/v1/agro/byok/cotacoes/MILHO?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_milho_fut.status_code == 200
    assert "B3" in resp_milho_fut.json()["bolsaOuRegiao"]

    # 4. BOI GORDO FÍSICO vs FUTURO
    resp_boi_fis = client.get(
        "/api/v1/agro/byok/cotacoes/BOI_GORDO?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_boi_fis.status_code == 200
    assert resp_boi_fis.json()["unidade"] == "@ (arroba 15kg)"

    resp_boi_fut = client.get(
        "/api/v1/agro/byok/cotacoes/BOI_GORDO?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_boi_fut.status_code == 200
    assert resp_boi_fut.json()["instrumento"] == "B3:BGI"

    # 5. CAFÉ FÍSICO vs FUTURO
    resp_cafe_fis = client.get(
        "/api/v1/agro/byok/cotacoes/CAFE?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_cafe_fis.status_code == 200
    assert "Minas" in resp_cafe_fis.json()["bolsaOuRegiao"]

    resp_cafe_fut = client.get(
        "/api/v1/agro/byok/cotacoes/CAFE?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_cafe_fut.status_code == 200
    assert resp_cafe_fut.json()["moeda"] == "USD_CENT"
    assert "ICE" in resp_cafe_fut.json()["bolsaOuRegiao"]

    # 6. TRIGO FÍSICO vs FUTURO
    resp_trigo_fis = client.get(
        "/api/v1/agro/byok/cotacoes/TRIGO?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_trigo_fis.status_code == 200
    assert resp_trigo_fis.json()["unidade"] == "tonelada"

    resp_trigo_fut = client.get(
        "/api/v1/agro/byok/cotacoes/TRIGO?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert resp_trigo_fut.status_code == 200
    assert resp_trigo_fut.json()["instrumento"] == "CBOT:ZW"


# ============================================================================
# 6. ISOLAMENTO DE CACHE POR USUÁRIO
# ============================================================================

def test_08_cache_privado_estritamente_isolado(client: TestClient):
    """Comprova que o cache é privado e não compartilha dados entre usuários nem com o público."""
    user_1, token_1 = criar_usuario_autenticado(client, "cache_1")
    user_2, token_2 = criar_usuario_autenticado(client, "cache_2")

    headers_1 = {"Authorization": f"Bearer {token_1}"}
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    # Cadastra chaves simuladas para ambos
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers_1,
        json={"providerSlug": "SIMULATED", "apiKey": "key_u1"},
    )
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers_2,
        json={"providerSlug": "SIMULATED", "apiKey": "key_u2"},
    )

    # 1. Usuário 1 faz primeira consulta de Soja Físico: cached deve ser False
    resp_1a = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers_1,
    )
    assert resp_1a.status_code == 200
    assert resp_1a.json()["cached"] is False
    assert user_1["id"][:8] in resp_1a.json()["titularidadeByok"]

    # 2. Usuário 1 faz segunda consulta: cached DEVE ser True (veio do cache dele)
    resp_1b = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers_1,
    )
    assert resp_1b.status_code == 200
    assert resp_1b.json()["cached"] is True

    # 3. Usuário 2 consulta a mesma commodity: cached DEVE ser False (cache de 1 não é compartilhado)
    resp_2 = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers_2,
    )
    assert resp_2.status_code == 200
    assert resp_2.json()["cached"] is False
    assert user_2["id"][:8] in resp_2.json()["titularidadeByok"]


# ============================================================================
# 7. RATE LIMITING E RESILIÊNCIA A FALHAS
# ============================================================================

def test_09_rate_limiting_por_usuario(client: TestClient):
    """Verifica que ultrapassar o limite configurado gera 429 Too Many Requests com Retry-After."""
    user, token = criar_usuario_autenticado(client, "ratelimit")
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "key_rate"},
    )

    # Força limite baixo de 3 requisições por minuto para o teste
    with patch("agro_identity.byok_proxy.AGRO_BYOK_RATE_LIMIT_PER_MINUTE", 3):
        # Cria novo serviço com limite 3
        for i in range(3):
            # Primeiras requisições passam
            r = client.get(
                "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
                headers=headers,
            )
            assert r.status_code == 200

    # Testando diretamente o ByokRateLimiter com limite 3 para validação estrita
    from redis.asyncio import Redis
    fake_redis = Redis.from_url("redis://localhost:9999/0")  # offline
    limiter = ByokRateLimiter(fake_redis, limit_per_minute=2)
    user_id = uuid.uuid4()

    # Passa 2 vezes
    asyncio.run(limiter.check_and_increment(user_id, "SIMULATED"))
    asyncio.run(limiter.check_and_increment(user_id, "SIMULATED"))

    # 3ª vez deve lançar HTTPException 429
    with pytest.raises(Exception) as excinfo:
        asyncio.run(limiter.check_and_increment(user_id, "SIMULATED"))
    assert excinfo.value.status_code == 429
    assert "Retry-After" in excinfo.value.headers


# ============================================================================
# 8. REVOGAÇÃO, EXCLUSÃO E ROTAÇÃO VIA API
# ============================================================================

def test_10_revogacao_e_exclusao_de_credenciais(client: TestClient):
    """Testa o fluxo de revogação e exclusão permanente de credencial do cofre."""
    user, token = criar_usuario_autenticado(client, "revogacao")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Salva credencial
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "chave_para_revogar"},
    )

    # Consulta cotação com sucesso
    r_ok = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert r_ok.status_code == 200

    # 2. Revoga credencial
    r_rev = client.post("/api/v1/agro/byok/credentials/SIMULATED/revoke", headers=headers)
    assert r_rev.status_code == 200
    assert r_rev.json()["sucesso"] is True

    # 3. Consulta de cotação DEVE falhar pois a credencial está revogada
    r_fail = client.get(
        "/api/v1/agro/byok/cotacoes/SOJA?tipo_mercado=FISICO&provedor=SIMULATED",
        headers=headers,
    )
    assert r_fail.status_code == 404

    # 4. Exclui credencial permanentemente
    r_del = client.delete("/api/v1/agro/byok/credentials/SIMULATED", headers=headers)
    assert r_del.status_code == 200
    assert r_del.json()["sucesso"] is True

    # 5. Lista deve estar vazia
    r_list = client.get("/api/v1/agro/byok/credentials", headers=headers)
    assert r_list.json() == []


def test_11_rotacao_de_chaves_via_api(client: TestClient):
    """Testa a rotação de chaves KMS v1 -> v2 via endpoint POST /credentials/rotate-keys."""
    user, token = criar_usuario_autenticado(client, "rotacao_api")
    headers = {"Authorization": f"Bearer {token}"}

    # Salva credencial na v1
    client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "chave_rotacao_api_123"},
    )

    # Verifica versão inicial v1
    creds_v1 = client.get("/api/v1/agro/byok/credentials", headers=headers).json()
    assert creds_v1[0]["keyVersion"] == 1

    # Executa rotação para v2
    resp_rot = client.post(
        "/api/v1/agro/byok/credentials/rotate-keys?nova_versao=2",
        headers=headers,
    )
    assert resp_rot.status_code == 200
    assert resp_rot.json()["sucesso"] is True
    assert resp_rot.json()["versaoDestino"] == 2
    assert resp_rot.json()["credenciaisRotacionadas"] == 1

    # Verifica que a credencial agora está na v2
    creds_v2 = client.get("/api/v1/agro/byok/credentials", headers=headers).json()
    assert creds_v2[0]["keyVersion"] == 2

    # Comprova que a consulta de cotação continua funcionando perfeitamente decifrando com a v2
    r_cot = client.get(
        "/api/v1/agro/byok/cotacoes/MILHO?tipo_mercado=FUTURO&provedor=SIMULATED",
        headers=headers,
    )
    assert r_cot.status_code == 200
    assert r_cot.json()["commodity"] == "MILHO"


def test_12_acesso_byok_com_token_central_global(client: TestClient):
    """Garante que usuário autenticado via identidade central (JWT central) acessa o cofre BYOK."""
    user, _ = criar_usuario_autenticado(client, "produtor_global")
    global_user_id = user["id"]
    svc = AuthService(None)
    central_token = svc.create_access_token(
        data={"sub": str(global_user_id), "email": user["email"], "product_scope": ["agro:free"]}
    )
    headers = {"Authorization": f"Bearer {central_token}"}

    # Cadastra credencial
    resp_store = client.post(
        "/api/v1/agro/byok/credentials",
        headers=headers,
        json={"providerSlug": "SIMULATED", "apiKey": "global_user_key_9999"},
    )
    assert resp_store.status_code == 201
    assert resp_store.json()["usuarioId"] == str(global_user_id)
    assert resp_store.json()["mascaraChave"].endswith("9999")

    # Lista credenciais
    resp_list = client.get("/api/v1/agro/byok/credentials", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1
    assert resp_list.json()[0]["usuarioId"] == str(global_user_id)


def test_13_acesso_byok_com_cookie_central(client: TestClient):
    """Garante que o cofre BYOK aceita cookie deepfarms_agro_session ou deepfarms_session emitidos centralmente."""
    user, _ = criar_usuario_autenticado(client, "produtor_cookie")
    global_user_id = user["id"]
    svc = AuthService(None)
    central_token = svc.create_access_token(
        data={"sub": str(global_user_id), "email": user["email"], "product_scope": ["agro:free"]}
    )

    # Usa cookie deepfarms_agro_session
    client.cookies.set("deepfarms_agro_session", central_token)
    resp_store = client.post(
        "/api/v1/agro/byok/credentials",
        json={"providerSlug": "SIMULATED", "apiKey": "cookie_user_key_7777"},
    )
    assert resp_store.status_code == 201
    assert resp_store.json()["usuarioId"] == str(global_user_id)
    client.cookies.clear()

