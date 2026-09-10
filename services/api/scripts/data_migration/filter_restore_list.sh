#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-/tmp/restore.list}"
OUTPUT="${2:-/tmp/restore.filtered.list}"

grep -vE \
'(alembic_version|amostras|balanca_afericoes|balanca_avaliacoes_prestador|balanca_dispositivos|balanca_fisicas|balanca_operadores|balanca_ordens|balanca_pesagens|balanca_sync_tombstones|mapas_fertilidade|territory_legacy_backup_01h2)' \
"$INPUT" \
| grep -v 'TABLE DATA farms status_consorcio_area ' \
> "$OUTPUT"

echo "Restore list gerada: $OUTPUT"
echo "status_consorcio_area: dados derivados, não restaurados diretamente."
