#!/bin/bash
# Ativa o virtualenv e executa o worker

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
cd "$PROJECT_ROOT"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$PROJECT_ROOT/services/api:$PYTHONPATH"

echo "Iniciando worker..."
exec python scripts/run_worker.py
