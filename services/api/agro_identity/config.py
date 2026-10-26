"""Configurações exclusivas do módulo de identidade individual do DeepFarms Agro."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from loguru import logger

# Diretório persistente fora do código-fonte (services/api/)
# Configurável por ambiente via AGRO_IDENTITY_DB_DIR ou volume montado
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data" / "agro_identity"
AGRO_IDENTITY_DB_DIR = Path(os.getenv("AGRO_IDENTITY_DB_DIR", str(_DEFAULT_DATA_DIR)))
AGRO_IDENTITY_DB_PATH = AGRO_IDENTITY_DB_DIR / "agro_identity.db"

# Repositório segregado: isolado do PostgreSQL comercial (pool_size=3)
AGRO_IDENTITY_DB_URL = os.getenv(
    "AGRO_IDENTITY_DATABASE_URL",
    f"sqlite+aiosqlite:///{AGRO_IDENTITY_DB_PATH}"
)

# Chave secreta de assinatura JWT exclusiva para identidades individuais do Agro
AGRO_JWT_SECRET_KEY = os.getenv(
    "AGRO_JWT_SECRET_KEY",
    "deepfarms_agro_individual_secret_key_v1_segregated"
)
AGRO_JWT_ALGORITHM = "HS256"
AGRO_JWT_ISSUER = "deepfarms:agro:auth"
AGRO_JWT_AUDIENCE = "deepfarms:agro:app"

# Duração da sessão individual
AGRO_TOKEN_EXPIRE_DAYS = int(os.getenv("AGRO_TOKEN_EXPIRE_DAYS", "7"))
AGRO_COOKIE_NAME = "deepfarms_agro_session"
AGRO_COOKIE_SECURE = os.getenv("APP_ENV", "development") == "production"
AGRO_COOKIE_DOMAIN = os.getenv("AGRO_COOKIE_DOMAIN", None)

# Proteção contra força bruta
AGRO_MAX_LOGIN_ATTEMPTS = 5
AGRO_LOCKOUT_MINUTES = 15

# Chave mestra simulada para o futuro cofre BYOK (KMS Envelope Encryption)
AGRO_VAULT_MASTER_KEY = os.getenv(
    "AGRO_VAULT_MASTER_KEY",
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
)

# Configurações do Proxy BYOK e isolamento de cache
AGRO_BYOK_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
AGRO_BYOK_CACHE_TTL_SECONDS = int(os.getenv("AGRO_BYOK_CACHE_TTL_SECONDS", "60"))
AGRO_BYOK_RATE_LIMIT_PER_MINUTE = int(os.getenv("AGRO_BYOK_RATE_LIMIT_PER_MINUTE", "30"))
AGRO_BYOK_REQUEST_TIMEOUT_SECONDS = float(os.getenv("AGRO_BYOK_REQUEST_TIMEOUT_SECONDS", "5.0"))
AGRO_BYOK_CONCURRENCY_LIMIT = int(os.getenv("AGRO_BYOK_CONCURRENCY_LIMIT", "5"))

# Origens permitidas explicitamente para operações de identidade Agro (CORS / CSRF)
_DEFAULT_ALLOWED_ORIGINS = [
    "https://agro.deepfarms.com.br",
    "http://localhost:3000",
    "http://localhost:3004",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3004",
]
env_origins = os.getenv("AGRO_ALLOWED_ORIGINS")
if env_origins:
    AGRO_ALLOWED_ORIGINS = [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    AGRO_ALLOWED_ORIGINS = _DEFAULT_ALLOWED_ORIGINS


def ensure_secure_storage() -> None:
    """Garante que o diretório persistente e os arquivos SQLite tenham permissões estritas (0700/0600).

    Migra dados legados em services/api/ caso o novo diretório persistente esteja vazio.
    """
    if "sqlite" not in AGRO_IDENTITY_DB_URL:
        return

    # 1. Cria diretório persistente protegido com modo 0700
    try:
        AGRO_IDENTITY_DB_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(AGRO_IDENTITY_DB_DIR, 0o700)
    except OSError as err:
        logger.warning(f"Não foi possível aplicar permissões 0700 ao diretório {AGRO_IDENTITY_DB_DIR}: {err}")

    # 2. Migração segura de arquivo legado na raiz de services/api, se aplicável
    legacy_db = Path(__file__).resolve().parent.parent / "agro_identity.db"
    if legacy_db.exists() and not AGRO_IDENTITY_DB_PATH.exists():
        try:
            shutil.copy2(legacy_db, AGRO_IDENTITY_DB_PATH)
            for ext in ("-wal", "-shm"):
                leg_ext = Path(str(legacy_db) + ext)
                if leg_ext.exists():
                    shutil.copy2(leg_ext, Path(str(AGRO_IDENTITY_DB_PATH) + ext))
            logger.info("Banco SQLite legado migrado para diretório persistente protegido.")
        except Exception as err:
            logger.warning(f"Falha na migração do banco SQLite legado: {err}")

    # 3. Restringe permissões dos arquivos para 0600 (-rw-------)
    for ext in ("", "-wal", "-shm"):
        target = Path(str(AGRO_IDENTITY_DB_PATH) + ext)
        if target.exists():
            try:
                os.chmod(target, 0o600)
            except OSError as err:
                logger.warning(f"Não foi possível ajustar permissões de {target} para 0600: {err}")
