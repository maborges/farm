#!/usr/bin/env python
import sys
import os
from pathlib import Path

# Adiciona o diretório da API ao path para importações corretas
api_dir = Path(__file__).parent.parent / "services" / "api"
sys.path.insert(0, str(api_dir))

# Importa o main apenas para garantir que todos os models do SQLAlchemy 
# sejam carregados e mapeados no Base antes do worker iniciar as queries
import main

import asyncio
from automacoes.worker import run_worker_loop
from loguru import logger

if __name__ == "__main__":
    logger.info("Iniciando script run_worker.py...")
    try:
        asyncio.run(run_worker_loop())
    except KeyboardInterrupt:
        logger.info("Execução do worker finalizada.")
