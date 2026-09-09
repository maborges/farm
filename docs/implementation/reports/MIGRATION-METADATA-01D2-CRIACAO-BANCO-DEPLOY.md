# MIGRATION-METADATA-01D.2 — Criação do banco de deploy

## Status

```text
MIGRATION-METADATA-01D
STATUS: STOP
```

A validação de desenvolvimento foi concluída, mas a aplicação na EC2 não
foi executada nesta sessão. Não há acesso SSH nem configuração de deploy
disponível aqui. A única configuração local encontrada aponta para o banco
funcional `farms`, que é um alvo proibido para esta operação.

## Validação no desenvolvimento

Executado em `services/api`:

```bash
PYTHONPATH=. .venv/bin/pytest tests/unit/core/test_baseline_contract.py -q
PYTHONPATH=. .venv/bin/ruff check \
  core/model_registry.py \
  migrations/baseline_contract.py \
  migrations/versions/20260908_baseline_deepfarms_v1.py
PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql \
  > /tmp/baseline_deepfarms_v1.sql
git diff --check
```

Resultados:

```text
8 testes aprovados
Ruff aprovado
SQL offline aprovado
git diff --check aprovado
```

O SQL offline emitiu:

```text
34 ENUMs
345 CREATE TABLE (344 baseline + alembic_version)
891 FKs
188 policies
```

## Artefatos necessários no deploy

```text
services/api/core/model_registry.py
services/api/migrations/baseline_contract.py
services/api/migrations/versions/20260908_baseline_deepfarms_v1.py
```

```text
revision      = baseline_deepfarms_v1
down_revision = None
```

## Execução pendente na EC2

No servidor de deploy, após confirmar o `DATABASE_URL` real e mascarar sua
senha nos registros:

```bash
cd services/api

PYTHONPATH=. .venv/bin/python -c \
  'from core.database import DB_URL; print(DB_URL.split("@")[-1])'

PYTHONPATH=. .venv/bin/alembic current
PYTHONPATH=. .venv/bin/alembic heads
PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1
PYTHONPATH=. .venv/bin/alembic current
```

Antes do upgrade, devem ser executadas consultas read-only para confirmar
`current_database()`, `current_user`, versão PostgreSQL, schemas, tabelas de
usuário e ausência de `alembic_version`/dados operacionais.

## Bloqueio

Não foi possível comprovar:

* identidade do database de deploy;
* vazio inicial;
* backup schema-only do alvo;
* aplicação online da baseline;
* inventário físico final;
* Alembic current após aplicação;
* startup da API;
* smoke funcional e isolamento tenant.

Consequentemente, não é permitido emitir `GO` nem continuar o deploy.

O próximo passo é executar esta validação dentro da EC2 ou fornecer acesso
SSH/configuração segura do ambiente de deploy. Nenhum banco, RDS, dado ou
migration histórica foi alterado por esta etapa.
