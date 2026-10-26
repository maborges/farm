#!/usr/bin/env bash
# ==============================================================================
# DeepFarms Agro — Procedimento de Descarte e Limpeza de Staging (AGRO-ADMIN-01H1)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infrastructure/staging/docker-compose.agro-staging.yml"
ENV_FILE="${ROOT_DIR}/infrastructure/staging/.env.staging"

echo "=================================================================="
echo "  DeepFarms Agro — Descarte do Ambiente de Staging Isolado"
echo "=================================================================="

if [ -f "${ENV_FILE}" ]; then
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down --volumes --remove-orphans
else
    docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans
fi

echo "[*] Removendo volumes de dados efêmeros de staging..."
docker volume rm deepfarms_staging_postgres_data deepfarms_staging_redis_data deepfarms_staging_minio_data 2>/dev/null || true

echo "=================================================================="
echo "  Ambiente de Staging descartado e volumes limpos com sucesso!"
echo "=================================================================="
