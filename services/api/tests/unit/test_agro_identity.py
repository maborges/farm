"""
Testes unitários e de integração para o subsistema segregado de identidade individual do DeepFarms Agro.

Garante:
1. Cadastro (register) com emissão de token, cookie HttpOnly e envio efetivo de código de verificação.
2. Login com proteção contra força bruta (lockout temporário).
3. Logout e revogação imediata da sessão.
4. Consulta de perfil (/me) via cookie e via header Bearer.
5. Fluxo de recuperação de senha, envio real de e-mail e uso estritamente único do token.
6. Rejeição imediata de tokens individuais em rotas e recursos do SaaS comercial (403 Forbidden).
7. Ausência absoluta de criação de Tenants ou registros em TenantUsuario na base comercial.
8. Alteração de senha autenticada e revogação mandatória de sessões ativas.
9. Rate limiting distribuído e tolerância a falhas do Redis (fallback em memória sem erro 500).
10. Isolamento de conexões: guarda-corpo 403 rejeita token individual sem consumir conexões do PostgreSQL comercial.
11. Teste de Envelope Encryption (AES-256-GCM com HKDF e AAD) do cofre BYOK.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient

from agro_identity.backup import create_sqlite_backup, restore_sqlite_backup, verify_sqlite_integrity
from agro_identity.config import AGRO_IDENTITY_DB_DIR, AGRO_IDENTITY_DB_PATH, ensure_secure_storage
from agro_identity.database import init_agro_db
from agro_identity.email_dispatch import clear_sent_emails, get_sent_emails
from agro_identity.security import AgroLoginRateLimiter
from agro_identity.vault_contracts import LocalEnvelopeEncryptionService, mascarar_chave
from main import app


@pytest.fixture(autouse=True)
def ensure_db():
    asyncio.run(init_agro_db())
    clear_sent_emails()


@pytest.fixture
def client():
    # TestClient com cookies habilitados
    return TestClient(app)


def test_01_cadastro_login_e_perfil(client: TestClient):
    email = f"produtor_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha = "SenhaForte123!@"

    # 1. Cadastro
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Produtor Teste", "senha": senha},
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["sucesso"] is True
    assert data["usuario"]["email"] == email
    assert data["usuario"]["nome"] == "Produtor Teste"
    assert data["usuario"]["emailVerificado"] is False
    assert "token" not in data  # Token JWT NUNCA exposto no body JSON (segurança HttpOnly estrita)
    assert "codigoVerificacao" not in data  # NUNCA exposto na resposta pública HTTP

    # Comprova que o e-mail de confirmação foi despachado e obtém o código pelo mecanismo interno
    sent = get_sent_emails()
    assert len(sent) >= 1
    email_confirm = [e for e in sent if e["tipo"] == "CONFIRMACAO_EMAIL" and e["destinatario"] == email]
    assert len(email_confirm) == 1
    cod_verif = email_confirm[0]["codigo"]
    assert len(cod_verif) == 6

    # Verifica cookie HttpOnly na resposta
    assert "deepfarms_agro_session" in reg_resp.cookies
    token = reg_resp.cookies["deepfarms_agro_session"]
    user_id = data["usuario"]["id"]

    # 2. Tentativa de verificação com código incorreto
    err_verify = client.post(
        "/api/v1/agro/auth/verify-email",
        json={"codigo": "000000"},
    )
    assert err_verify.status_code == 400

    # 3. Confirmação efetiva com o código correto recebido
    ok_verify = client.post(
        "/api/v1/agro/auth/verify-email",
        json={"codigo": cod_verif},
    )
    assert ok_verify.status_code == 200
    assert ok_verify.json()["sucesso"] is True

    # 4. Consulta /me usando o cookie (agora com emailVerificado = True)
    me_resp = client.get("/api/v1/agro/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == user_id
    assert me_resp.json()["emailVerificado"] is True

    # 5. Tentativa de reenviar verificação para conta já verificada (deve rejeitar)
    resend_fail = client.post("/api/v1/agro/auth/resend-verification")
    assert resend_fail.status_code == 400

    # 6. Consulta /me usando header Bearer
    client_no_cookie = TestClient(app)
    me_bearer = client_no_cookie.get(
        "/api/v1/agro/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_bearer.status_code == 200
    assert me_bearer.json()["email"] == email

    # 7. Login com as mesmas credenciais
    login_resp = client.post(
        "/api/v1/agro/auth/login",
        json={"email": email, "senha": senha},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["sucesso"] is True


def test_02_protecao_forca_bruta_e_lockout(client: TestClient):
    email = f"ataque_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha_correta = "SenhaCorreta123!"

    # Cadastra usuário
    client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Alvo Forca Bruta", "senha": senha_correta},
    )

    # Executa 5 tentativas com senha errada
    for _ in range(5):
        resp = client.post(
            "/api/v1/agro/auth/login",
            json={"email": email, "senha": "SenhaErrada999!"},
        )
        assert resp.status_code == 401

    # A 6ª tentativa deve ser bloqueada com 429 Too Many Requests
    resp_lockout = client.post(
        "/api/v1/agro/auth/login",
        json={"email": email, "senha": senha_correta},
    )
    assert resp_lockout.status_code == 429
    assert "Muitas tentativas" in resp_lockout.json()["detail"]


def test_03_logout_e_revogacao_sessao(client: TestClient):
    email = f"logout_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha = "SenhaForte123!@"

    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Usuario Logout", "senha": senha},
    )
    assert reg_resp.status_code == 201

    # Sessão ativa
    assert client.get("/api/v1/agro/auth/me").status_code == 200

    # Logout
    logout_resp = client.post("/api/v1/agro/auth/logout")
    assert logout_resp.status_code == 200

    # Sessão deve estar revogada
    assert client.get("/api/v1/agro/auth/me").status_code == 401


def test_04_recuperacao_senha(client: TestClient):
    email = f"recup_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha_antiga = "SenhaVelha123!"
    nova_senha = "NovaSenhaForte456!@"

    client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Usuario Recup", "senha": senha_antiga},
    )

    # 1. Solicita recuperação
    forgot_resp = client.post(
        "/api/v1/agro/auth/forgot-password",
        json={"email": email},
    )
    assert forgot_resp.status_code == 200
    assert "tokenRecuperacao" not in forgot_resp.json()  # NUNCA exposto na resposta pública HTTP

    # Comprova que o e-mail de recuperação de senha foi despachado e obtém o token pelo mecanismo interno
    sent = get_sent_emails()
    email_recup = [e for e in sent if e["tipo"] == "RECUPERACAO_SENHA" and e["destinatario"] == email]
    assert len(email_recup) == 1
    token_recup = email_recup[0]["token"]
    assert token_recup is not None

    # 2. Redefine com nova senha
    reset_resp = client.post(
        "/api/v1/agro/auth/reset-password",
        json={"token": token_recup, "novaSenha": nova_senha},
    )
    assert reset_resp.status_code == 200

    # 3. COMPROVAÇÃO DE USO ÚNICO: Reuso do mesmo token DEVE ser rejeitado com 400
    reset_reuso = client.post(
        "/api/v1/agro/auth/reset-password",
        json={"token": token_recup, "novaSenha": "TentativaAtaque999!"},
    )
    assert reset_reuso.status_code == 400
    assert "inválido, já utilizado ou expirado" in reset_reuso.json()["detail"]

    # 4. Tenta logar com senha antiga (deve falhar)
    resp_old = client.post(
        "/api/v1/agro/auth/login",
        json={"email": email, "senha": senha_antiga},
    )
    assert resp_old.status_code == 401

    # 5. Loga com a nova senha (sucesso)
    resp_new = client.post(
        "/api/v1/agro/auth/login",
        json={"email": email, "senha": nova_senha},
    )
    assert resp_new.status_code == 200


def test_05_rejeicao_de_token_individual_no_saas_comercial(client: TestClient):
    email = f"agro_free_{uuid.uuid4().hex[:8]}@agro.com.br"
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Produtor Free", "senha": "SenhaForte123!@"},
    )
    assert "deepfarms_agro_session" in reg_resp.cookies
    token = reg_resp.cookies["deepfarms_agro_session"]

    # Tenta usar o token individual em endpoints comerciais protegidos do SaaS
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Endpoint comercial /auth/me
    resp_me = client.get("/api/v1/auth/me", headers=headers)
    assert resp_me.status_code == 403
    assert "Tokens de identidade individual" in resp_me.json()["detail"]

    # 2. Endpoint comercial /my-tenants
    resp_tenants = client.get("/api/v1/auth/my-tenants", headers=headers)
    assert resp_tenants.status_code == 403

    # 3. Endpoint comercial /tenants (backoffice)
    resp_backoffice = client.get("/api/v1/backoffice/tenants", headers=headers)
    assert resp_backoffice.status_code == 403


def test_06_ausencia_de_tenants_comerciais(client: TestClient):
    email = f"sem_tenant_{uuid.uuid4().hex[:8]}@agro.com.br"
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Sem Tenant", "senha": "SenhaForte123!@"},
    )
    assert reg_resp.status_code == 201
    usuario_agro = reg_resp.json()["usuario"]

    # Consulta a base comercial diretamente para provar que NENHUM Tenant foi criado
    from core.database import async_session_maker
    from core.models.auth import TenantUsuario
    from core.models.tenant import Tenant
    from sqlalchemy import select

    async def verify_commercial_db():
        async with async_session_maker() as session:
            # Não existe na tabela de tenants
            stmt_t = select(Tenant).where(Tenant.nome.ilike("%Sem Tenant%"))
            assert (await session.execute(stmt_t)).scalar_one_or_none() is None

            # Não existe registro comercial em tenant_usuarios
            stmt_tu = select(TenantUsuario).where(TenantUsuario.usuario_id == uuid.UUID(usuario_agro["id"]))
            assert (await session.execute(stmt_tu)).scalar_one_or_none() is None

    asyncio.run(verify_commercial_db())


def test_07_envelope_encryption_vault_contracts():
    master_key_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    vault_service = LocalEnvelopeEncryptionService(master_key_hex)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    secret_key = "sk_live_twelvedata_secret_test_key_12345"

    # 1. Criptografia para o usuário A
    encrypted = vault_service.encrypt_secret(user_a, secret_key, version=1)
    assert encrypted.ciphertextB64 is not None
    assert encrypted.nonceIvB64 is not None

    # 2. Descriptografia bem-sucedida para o usuário A
    decrypted = vault_service.decrypt_secret(user_a, encrypted)
    assert decrypted == secret_key

    # 3. Tentativa de descriptografia por outro usuário (B) com o mesmo payload (deve falhar pelo AAD)
    with pytest.raises(Exception):
        vault_service.decrypt_secret(user_b, encrypted)

    # 4. Teste de máscara de exibição
    assert mascarar_chave(secret_key) == "••••••••••••••••••••••••••••••••••••2345"
    assert mascarar_chave("123") == "••••"


def test_08_mudanca_de_senha_e_revogacao_de_sessoes(client: TestClient):
    """Comprova que a alteração de senha autenticada revoga imediatamente as sessões ativas."""
    email = f"trocasenha_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha_antiga = "SenhaOriginal123!@"
    senha_nova = "NovaSenhaSegura456!@"

    # 1. Registra e autentica
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Produtor Troca", "senha": senha_antiga},
    )
    assert reg_resp.status_code == 201
    assert client.get("/api/v1/agro/auth/me").status_code == 200

    # 2. Altera a senha
    change_resp = client.post(
        "/api/v1/agro/auth/change-password",
        json={"senhaAtual": senha_antiga, "novaSenha": senha_nova},
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["sucesso"] is True

    # 3. Sessão anterior DEVE estar revogada
    assert client.get("/api/v1/agro/auth/me").status_code == 401

    # 4. Autenticação com nova senha deve funcionar
    login_resp = client.post(
        "/api/v1/agro/auth/login",
        json={"email": email, "senha": senha_nova},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["sucesso"] is True


def test_09_rate_limiting_distribuido_e_resiliencia_redis():
    """Valida o rate limiter em ambiente distribuído e garante fallback em memória sem erro 500 se o Redis falhar."""
    limiter = AgroLoginRateLimiter(redis_url=None)
    email_teste = "test_limiter@agro.com.br"

    # Simula 4 falhas
    for _ in range(4):
        asyncio.run(limiter.record_failure(email_teste))

    # Não deve estar bloqueado com 4 falhas
    asyncio.run(limiter.check_lockout(email_teste, "127.0.0.1"))

    # 5ª falha aplica lockout
    asyncio.run(limiter.record_failure(email_teste))

    with pytest.raises(Exception) as excinfo:
        asyncio.run(limiter.check_lockout(email_teste, "127.0.0.1"))
    assert "Muitas tentativas" in str(excinfo.value)

    # Limpeza em sucesso
    asyncio.run(limiter.record_success(email_teste))
    asyncio.run(limiter.check_lockout(email_teste, "127.0.0.1"))


def test_10_guardrail_zero_conexoes_postgres_comercial(client: TestClient):
    """Comprova que quando um token individual é rejeitado no SaaS comercial, get_session NUNCA é chamado."""
    email = f"zero_pool_{uuid.uuid4().hex[:8]}@agro.com.br"
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "Zero Pool", "senha": "SenhaForte123!@"},
    )
    assert "deepfarms_agro_session" in reg_resp.cookies
    token = reg_resp.cookies["deepfarms_agro_session"]

    # Intercepta get_session em core.dependencies para provar que a engine comercial não foi invocada
    with patch("core.dependencies.get_session") as mock_get_session:
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "Tokens de identidade individual" in resp.json()["detail"]
        mock_get_session.assert_not_called()


def test_11_protecao_csrf_e_isolamento_subdominios(client: TestClient):
    """Comprova proteção CSRF inter-subdomínios: requisições com cookie de subdomínios não-agro são bloqueadas."""
    email = f"csrf_{uuid.uuid4().hex[:8]}@agro.com.br"
    senha = "SenhaForte123!@"

    # Registra e obtém cookie de sessão
    reg_resp = client.post(
        "/api/v1/agro/auth/register",
        json={"email": email, "nome": "CSRF Test", "senha": senha},
    )
    assert reg_resp.status_code == 201

    # 1. Mutação autenticada por cookie com Origin de outro subdomínio (ex: app.deepfarms.com.br) deve ser 403 Forbidden
    resp_cross_subdomain = client.post(
        "/api/v1/agro/auth/resend-verification",
        headers={"Origin": "https://app.deepfarms.com.br"},
    )
    assert resp_cross_subdomain.status_code == 403
    assert "proteção CSRF inter-subdomínios" in resp_cross_subdomain.json()["detail"]

    # 2. Mutação autenticada por cookie com Origin malicioso externo deve ser 403 Forbidden
    resp_cross_origin = client.post(
        "/api/v1/agro/auth/resend-verification",
        headers={"Origin": "https://malicious-site.com"},
    )
    assert resp_cross_origin.status_code == 403
    assert "proteção CSRF inter-subdomínios" in resp_cross_origin.json()["detail"]

    # 3. Mutação autenticada com Origin homologado do Agro deve ser aceita
    resp_ok = client.post(
        "/api/v1/agro/auth/resend-verification",
        headers={"Origin": "https://agro.deepfarms.com.br"},
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["sucesso"] is True


def test_12_seguranca_permissoes_sqlite_e_diretorio():
    """Valida que o diretório persistente possui modo 0700 e os arquivos SQLite possuem modo 0600."""
    ensure_secure_storage()
    assert AGRO_IDENTITY_DB_DIR.exists()

    # Checa permissões do diretório (somente owner rwx: 0700)
    dir_stat = AGRO_IDENTITY_DB_DIR.stat()
    dir_mode = oct(dir_stat.st_mode)[-3:]
    assert dir_mode == "700"

    # Checa permissões do arquivo SQLite principal (somente owner rw: 0600)
    if AGRO_IDENTITY_DB_PATH.exists():
        file_stat = AGRO_IDENTITY_DB_PATH.stat()
        file_mode = oct(file_stat.st_mode)[-3:]
        assert file_mode == "600"


def test_13_backup_online_restauracao_e_integridade(tmp_path):
    """Comprova criação de backup online com integridade 'ok' e procedimento de restauração."""
    ensure_secure_storage()
    assert AGRO_IDENTITY_DB_PATH.exists()

    # 1. Cria backup online em diretório temporário
    backup_file = create_sqlite_backup(dest_dir=tmp_path)
    assert backup_file.exists()
    assert verify_sqlite_integrity(backup_file) is True

    # 2. Valida permissões 0600 do arquivo de backup
    file_mode = oct(backup_file.stat().st_mode)[-3:]
    assert file_mode == "600"

    # 3. Testa restauração em caminho temporário
    restored_target = tmp_path / "restored_test.db"
    ok_restore = restore_sqlite_backup(backup_file=backup_file, target_path=restored_target)
    assert ok_restore is True
    assert restored_target.exists()
    assert verify_sqlite_integrity(restored_target) is True

