#!/usr/bin/env python3
"""Script de Homologação em PostgreSQL 16 Descartável (AGRO-ADMIN-01B2D).

Executa:
1. Verificação estrita de isolamento de banco de dados (rejeita conexões compartilhadas/RDS).
2. Execução da cadeia completa de migrations Alembic (upgrade head).
3. Validação das constraints e schema PostgreSQL:
   - farms.sessoes_ativas.tenant_id nullable.
   - farms.usuario_byok_credenciais presente com constraints adequadas.
4. Teste de segurança do downgrade e rollback:
   - Bloqueio com credenciais BYOK ativas.
   - Bloqueio com sessões sem tenant ativas.
   - Downgrade limpo sem órfãos.
   - Re-upgrade para head.
"""

from __future__ import annotations

import asyncio
import os
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Assegura PYTHONPATH
API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))


def _assert_strict_isolation(db_url: str) -> None:
    """Garante que a URL do banco NUNCA aponta para RDS ou banco compartilhado."""
    if not db_url or "postgresql" not in db_url:
        print(f"ERRO: DATABASE_URL deve ser PostgreSQL. Recebido: {db_url}", file=sys.stderr)
        sys.exit(1)

    # Converte postgresql+asyncpg para postgresql padrão para parse
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urllib.parse.urlparse(clean_url)
    host = parsed.hostname or ""

    # Rejeição imediata de bancos não locais
    if host not in ("localhost", "127.0.0.1", "postgres"):
        print(f"ERRO FATAL: Tentativa de homologação contra host externo: {host}", file=sys.stderr)
        sys.exit(1)

    if "192.168." in db_url or "rds.amazonaws.com" in db_url or "farms" == parsed.path.strip("/") and host not in ("localhost", "127.0.0.1", "postgres"):
        print("ERRO FATAL: Banco compartilhado ou RDS detectado!", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Isolamento estrito confirmado. Banco alvo: {host}:{parsed.port}/{parsed.path.lstrip('/')}")


def _get_alembic_config(db_url: str) -> Config:
    ini_path = API_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    # Alembic usa async engine definida no env.py através de DB_URL / sqlalchemy.url
    cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
    return cfg


async def _run_alembic_upgrade_head(alembic_cfg: Config) -> None:
    print("\n--- Executando Alembic Upgrade Head ---")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
    print("✓ Alembic upgrade head concluído com sucesso.")


async def _validar_schema_postgresql(engine) -> None:
    print("\n--- Validando Schema e Constraints PostgreSQL 16 ---")
    async with engine.connect() as conn:
        # 1. Verifica se schema farms existe
        schema_exists = (await conn.execute(
            text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'farms'")
        )).scalar_one_or_none()
        assert schema_exists == "farms", "Schema 'farms' não foi criado pelo Alembic!"
        print("✓ Schema 'farms' existe.")

        # 2. Verifica se sessoes_ativas.tenant_id é nullable (YES)
        col_nullable = (await conn.execute(
            text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_schema = 'farms' 
                  AND table_name = 'sessoes_ativas' 
                  AND column_name = 'tenant_id'
            """)
        )).scalar_one_or_none()
        assert col_nullable == "YES", f"Esperado tenant_id IS NULLABLE='YES', obtido: '{col_nullable}'"
        print("✓ farms.sessoes_ativas.tenant_id é NULLABLE (YES).")

        # 3. Verifica se usuario_byok_credenciais existe e possui as colunas obrigatórias
        byok_table = (await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'farms' AND table_name = 'usuario_byok_credenciais'")
        )).scalar_one_or_none()
        assert byok_table == "usuario_byok_credenciais", "Tabela farms.usuario_byok_credenciais não foi criada!"
        print("✓ Tabela farms.usuario_byok_credenciais existe.")

        byok_cols = (await conn.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'farms' 
                  AND table_name = 'usuario_byok_credenciais'
            """)
        )).scalars().all()
        required_cols = {"id", "usuario_id", "provider_slug", "dek_encrypted", "dek_nonce", "ciphertext", "data_nonce", "key_version", "mascara_chave", "status"}
        missing_cols = required_cols - set(byok_cols)
        assert not missing_cols, f"Colunas ausentes em farms.usuario_byok_credenciais: {missing_cols}"
        print(f"✓ Todas as colunas do cofre BYOK validadas: {required_cols}")


async def _testar_seguranca_rollback(alembic_cfg: Config, engine) -> None:
    print("\n--- Testando Segurança de Downgrade e Rollback ---")
    loop = asyncio.get_running_loop()

    # Cria dados de teste
    test_user_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(text("""
            INSERT INTO farms.usuarios (id, email, username, senha_hash, ativo)
            VALUES (:id, 'ci.test@deepfarms.com', 'ci_user', 'hash', true)
            ON CONFLICT DO NOTHING
        """), {"id": test_user_id})

        # Insere credencial BYOK
        await conn.execute(text("""
            INSERT INTO farms.usuario_byok_credenciais (
                id, usuario_id, provider_slug, dek_encrypted, dek_nonce, ciphertext, data_nonce, key_version, mascara_chave, status
            ) VALUES (
                :id, :user_id, 'SIMULATED', 'dek', 'nonce', 'cipher', 'data_nonce', 1, 'key***', 'ACTIVE'
            )
        """), {"id": uuid.uuid4(), "user_id": test_user_id})

    # 1. Tentar downgrade com credencial ativa -> DEVE lançar RuntimeError
    print("Testando bloqueio de downgrade com credencial BYOK presente...")
    downgrade_blocked = False
    try:
        await loop.run_in_executor(None, command.downgrade, alembic_cfg, "-1")
    except RuntimeError as exc:
        if "há credenciais BYOK persistidas" in str(exc):
            downgrade_blocked = True
            print("✓ Downgrade bloqueado com sucesso devido a credenciais BYOK.")
        else:
            raise

    assert downgrade_blocked, "FALHA: O downgrade não foi bloqueado na presença de credenciais BYOK!"

    # Limpa credencial e insere sessão sem tenant
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM farms.usuario_byok_credenciais WHERE usuario_id = :user_id"), {"user_id": test_user_id})
        agora = datetime.now(timezone.utc)
        await conn.execute(text("""
            INSERT INTO farms.sessoes_ativas (
                id, usuario_id, tenant_id, token_hash, inicio, ultimo_heartbeat, expira_em, status
            ) VALUES (
                :id, :user_id, NULL, 'hash_test_ci', :agora, :agora, :expira, 'ATIVA'
            )
        """), {
            "id": uuid.uuid4(),
            "user_id": test_user_id,
            "agora": agora,
            "expira": agora + timedelta(hours=1),
        })

    # 2. Tentar downgrade com sessão órfã -> DEVE lançar RuntimeError
    print("Testando bloqueio de downgrade com sessão órfã (sem tenant)...")
    downgrade_blocked_orphan = False
    try:
        await loop.run_in_executor(None, command.downgrade, alembic_cfg, "-1")
    except RuntimeError as exc:
        if "encerre as sessões globais sem tenant" in str(exc):
            downgrade_blocked_orphan = True
            print("✓ Downgrade bloqueado com sucesso devido a sessão sem tenant.")
        else:
            raise

    assert downgrade_blocked_orphan, "FALHA: O downgrade não foi bloqueado na presença de sessões órfãs!"

    # Limpa dados de teste
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM farms.sessoes_ativas WHERE usuario_id = :user_id"), {"user_id": test_user_id})
        await conn.execute(text("DELETE FROM farms.usuarios WHERE id = :user_id"), {"user_id": test_user_id})

    # 3. Executa downgrade limpo -> DEVE ter sucesso
    print("Executando downgrade com banco limpo...")
    await loop.run_in_executor(None, command.downgrade, alembic_cfg, "-1")
    print("✓ Downgrade executado com sucesso.")

    # Verifica que tabela BYOK foi dropada e tenant_id é NOT NULL
    async with engine.connect() as conn:
        table_exists = (await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'farms' AND table_name = 'usuario_byok_credenciais'")
        )).scalar_one_or_none()
        assert table_exists is None, "Tabela usuario_byok_credenciais deveria ter sido dropada!"

        col_nullable = (await conn.execute(
            text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_schema = 'farms' 
                  AND table_name = 'sessoes_ativas' 
                  AND column_name = 'tenant_id'
            """)
        )).scalar_one_or_none()
        assert col_nullable == "NO", f"tenant_id deveria ser NOT NULL (NO) após downgrade, obtido: {col_nullable}"
        print("✓ farms.sessoes_ativas.tenant_id restaurado para NOT NULL após downgrade.")

    # 4. Re-executa upgrade head para restaurar estado atualizado
    print("Restaurando banco para head...")
    await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
    print("✓ Re-upgrade para head concluído com sucesso.")


async def main() -> None:
    db_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL", "")
    _assert_strict_isolation(db_url)

    alembic_cfg = _get_alembic_config(db_url)
    engine = create_async_engine(db_url, connect_args={"server_settings": {"search_path": "farms,public"}})

    try:
        await _run_alembic_upgrade_head(alembic_cfg)
        await _validar_schema_postgresql(engine)
        await _testar_seguranca_rollback(alembic_cfg, engine)
        print("\n=======================================================")
        print("✅ HOMOLOGAÇÃO POSTGRESQL 16 CONCLUÍDA COM 100% DE SUCESSO")
        print("=======================================================\n")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
