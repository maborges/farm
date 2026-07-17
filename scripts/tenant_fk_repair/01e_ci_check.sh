#!/usr/bin/env bash
# TENANT-FK-REPAIR-01E — Executa guardrails de integridade em CI
# Uso: ./scripts/tenant_fk_repair/01e_ci_check.sh
# Retorna exit code 0 se tudo OK, 1 se algum guardrail falhar.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(cd "$SCRIPT_DIR/../../services/api" && pwd)"

echo "=== TENANT-FK-REPAIR-01E — Guardrails de Integridade Multi-Tenant ==="
echo "Diretório: $API_DIR"
echo ""

cd "$API_DIR"

# Rodar apenas os testes de integridade (não os de feature)
python -m pytest tests/integrity/test_tenant_fk_guardrails.py \
    -v \
    --tb=short \
    --no-header \
    -q \
    "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Todos os guardrails de integridade multi-tenant passaram."
else
    echo ""
    echo "✗ Guardrails falharam — ver saída acima."
    echo "  Consulte docs/implementation/reports/TENANT-FK-AUDIT-01-AUDITORIA-INTEGRIDADE-REFERENCIAL.md"
    echo "  e os scripts em scripts/tenant_fk_repair/ para correção."
fi

exit $EXIT_CODE
