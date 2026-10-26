#!/usr/bin/env bash
# ==============================================================================
# DeepFarms Agro — Procedimento de Inicialização Segura de Staging (AGRO-ADMIN-01H1)
# ==============================================================================
# ATENÇÃO: NÃO EXECUTAR AUTOMATICAMENTE SEM AUTORIZAÇÃO EXPRESSA.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/infrastructure/staging/.env.staging"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/staging/docker-compose.agro-staging.yml"

echo "=================================================================="
echo "  DeepFarms Agro — Inicialização de Ambiente de Staging Isolado"
echo "=================================================================="

# 1. Verifica existência de .env.staging
if [ ! -f "${ENV_FILE}" ]; then
    echo "[ERRO] Arquivo '${ENV_FILE}' não encontrado!"
    echo "       Crie-o a partir de '${ROOT_DIR}/infrastructure/staging/.env.staging.example'"
    echo "       e configure segredos criptográficos fortes."
    exit 1
fi

# 2. Validação estrita de isolamento
echo "[*] Executando validação de isolamento..."
python3 "${SCRIPT_DIR}/validate_isolation.py" --env-file "${ENV_FILE}"

# 3. Exporta variáveis do arquivo para checagem de migrations
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# 4. Sobe infraestrutura base (Postgres, Redis, MinIO)
echo "[*] Subindo containers de banco de dados, cache e storage de teste..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d staging-postgres staging-redis staging-minio

echo "[*] Aguardando inicialização saudável do PostgreSQL e Redis (healthchecks)..."
until [ "$(docker inspect -f {{.State.Health.Status}} deepfarms-agro-staging-db 2>/dev/null)" == "healthy" ]; do
    printf "."
    sleep 2
done
echo " PostgreSQL OK."

until [ "$(docker inspect -f {{.State.Health.Status}} deepfarms-agro-staging-redis 2>/dev/null)" == "healthy" ]; do
    printf "."
    sleep 2
done
echo " Redis OK."

# 5. Execução controlada de migrations Alembic contra o PostgreSQL isolado (127.0.0.1:5433)
echo "[*] Aplicando migrations Alembic no banco de dados de staging isolado..."
STAGING_MIGRATION_URL="postgresql+asyncpg://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@127.0.0.1:${STAGING_DB_PORT:-5433}/${STAGING_DB_NAME}"
(
    cd "${ROOT_DIR}/services/api"
    export PYTHONPATH=.
    export DATABASE_URL="${STAGING_MIGRATION_URL}"
    export ENVIRONMENT=staging
    export APP_ENV=staging
    export PLATFORM_CREDENTIALS_MASTER_KEY="${STAGING_PLATFORM_CREDENTIALS_MASTER_KEY}"
    "${ROOT_DIR}/services/api/.venv/bin/alembic" -c alembic.ini upgrade head
)
echo "[*] Migrations aplicadas com sucesso!"

# 6. Sobe serviços de aplicação (API workers, Backoffice Web, PWA Agro)
echo "[*] Inicializando containers de aplicação..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d staging-api-worker-1 staging-api-worker-2 staging-web staging-agro

echo "=================================================================="
echo "  Staging Isolado Inicializado com Sucesso!"
echo "  - API Worker 1:      http://127.0.0.1:8001"
echo "  - API Worker 2:      http://127.0.0.1:8002"
echo "  - Backoffice Web:    http://127.0.0.1:3001"
echo "  - PWA Agro:          http://127.0.0.1:3005"
echo "  - MinIO Storage:     http://127.0.0.1:9002 (Console: :9003)"
echo "=================================================================="
