"""Migrações versionadas exclusivas para o banco segregado de identidades e cofre BYOK do Agro.

Opera com versionamento em tabela própria (agro_schema_versions), garantindo evolução
idempotente e isolamento absoluto contra as migrações comerciais do Alembic do SaaS.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine

from .config import AGRO_IDENTITY_DB_PATH, ensure_secure_storage


def _get_sqlite_connection() -> sqlite3.Connection:
    ensure_secure_storage()
    conn = sqlite3.connect(str(AGRO_IDENTITY_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_current_agro_schema_version() -> int:
    """Retorna a versão atual do schema do banco Agro."""
    if not Path(AGRO_IDENTITY_DB_PATH).exists():
        return 0

    with _get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agro_schema_versions';"
        )
        if not cursor.fetchone():
            return 0
        cursor.execute("SELECT MAX(version) FROM agro_schema_versions;")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0


def run_agro_migrations() -> int:
    """Aplica todas as migrações pendentes no banco SQLite segregado do Agro.

    Returns:
        Número da versão atual após as migrações.
    """
    ensure_secure_storage()
    with _get_sqlite_connection() as conn:
        cursor = conn.cursor()

        # Cria tabela de controle de versão se não existir
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agro_schema_versions (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )

        cursor.execute("SELECT version FROM agro_schema_versions;")
        applied = {row["version"] for row in cursor.fetchall()}

        # -------------------------------------------------------------
        # Migração 1: Tabelas fundamentais de identidade
        # -------------------------------------------------------------
        if 1 not in applied:
            logger.info("Aplicando migração Agro 001: tabelas fundamentais de identidade...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agro_usuarios (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT 1,
                    email_verificado BOOLEAN NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_agro_usuarios_email ON agro_usuarios(email);")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agro_sessoes (
                    id TEXT PRIMARY KEY,
                    usuario_id TEXT NOT NULL REFERENCES agro_usuarios(id) ON DELETE CASCADE,
                    token_hash TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    revogado BOOLEAN NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    ultimo_acesso TEXT NOT NULL,
                    expira_em TEXT NOT NULL
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_agro_sessoes_token_hash ON agro_sessoes(token_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_agro_sessoes_usuario_id ON agro_sessoes(usuario_id);")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agro_tokens_recuperacao (
                    id TEXT PRIMARY KEY,
                    usuario_id TEXT NOT NULL REFERENCES agro_usuarios(id) ON DELETE CASCADE,
                    token_hash TEXT UNIQUE NOT NULL,
                    usado BOOLEAN NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_agro_tokens_recup_hash ON agro_tokens_recuperacao(token_hash);")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agro_tokens_verificacao (
                    id TEXT PRIMARY KEY,
                    usuario_id TEXT NOT NULL REFERENCES agro_usuarios(id) ON DELETE CASCADE,
                    codigo TEXT NOT NULL,
                    usado BOOLEAN NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_agro_tokens_verif_cod ON agro_tokens_verificacao(codigo);")

            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO agro_schema_versions (version, name, applied_at) VALUES (1, 'initial_identity', ?);",
                (now_iso,),
            )
            applied.add(1)

        # -------------------------------------------------------------
        # Migração 2: Cofre segregado BYOK com envelope encryption
        # -------------------------------------------------------------
        # Verifica se tabela legada sem mascara_chave precisa ser recriada
        cursor.execute("PRAGMA table_info(agro_user_byok_credentials);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if existing_cols and "mascara_chave" not in existing_cols:
            logger.info("Atualizando tabela legada agro_user_byok_credentials para schema completo de envelope encryption...")
            cursor.execute("DROP TABLE agro_user_byok_credentials;")
            applied.discard(2)
            cursor.execute("DELETE FROM agro_schema_versions WHERE version = 2;")

        if 2 not in applied:
            logger.info("Aplicando migração Agro 002: cofre BYOK com envelope encryption...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agro_user_byok_credentials (
                    id TEXT PRIMARY KEY,
                    usuario_id TEXT NOT NULL REFERENCES agro_usuarios(id) ON DELETE CASCADE,
                    provider_slug TEXT NOT NULL,
                    mascara_chave TEXT NOT NULL,
                    ciphertext_b64 TEXT NOT NULL,
                    data_nonce_b64 TEXT NOT NULL,
                    dek_encrypted_b64 TEXT NOT NULL,
                    dek_nonce_b64 TEXT NOT NULL,
                    key_version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'CONECTADO',
                    ultimo_uso TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_agro_byok_user_provider ON agro_user_byok_credentials(usuario_id, provider_slug);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_agro_byok_usuario_id ON agro_user_byok_credentials(usuario_id);"
            )

            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO agro_schema_versions (version, name, applied_at) VALUES (2, 'byok_envelope_vault', ?);",
                (now_iso,),
            )
            applied.add(2)

        conn.commit()

    ensure_secure_storage()
    final_version = max(applied) if applied else 0
    logger.info(f"Migrações do banco segregado Agro concluídas. Versão atual: {final_version}")
    return final_version
