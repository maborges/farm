#!/bin/bash
# Ativa o virtualenv e executa o worker

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

export PYTHONPATH="$DIR/services/api:$PYTHONPATH"

echo "Iniciando worker..."
python scripts/run_worker.py
