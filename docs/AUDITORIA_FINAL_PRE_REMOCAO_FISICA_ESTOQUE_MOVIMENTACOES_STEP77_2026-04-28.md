# Step 77: auditoria final pré-remoção física de `estoque_movimentacoes`

## Contexto e objetivo

Esta auditoria consolida o estado final do legado `estoque_movimentacoes` após:

- Step 61: novos writes direcionados ao ledger oficial `estoque_movimentos`
- Step 63: adaptação inicial de leituras
- Step 71: backfill real do legado elegível
- Step 74: guardrails de legado `read-only`
- Step 75: remoção do fallback funcional em Safra e Relatórios
- Step 76: redução da allowlist ao mínimo necessário

Objetivo desta etapa:

- confirmar `0` uso funcional de leitura do legado
- confirmar `0` writes novos no legado
- listar os artefatos estruturais que ainda existem antes de qualquer remoção física da tabela

## Evidências coletadas

### Busca estática

Comando executado:

```bash
rg -n "MovimentacaoEstoque|estoque_movimentacoes" apps/web/services/api -g '*.py'
```

Resultado consolidado fora de `migrations/`:

- `apps/web/services/api/operacional/models/estoque.py`
  - model ORM legado `MovimentacaoEstoque`
- `apps/web/services/api/scripts/backfill_estoque_movimentacoes.py`
  - script congelado de backfill/histórico
- `apps/web/services/api/tests/integration/operacional/test_estoque.py`
  - teste guarda de ausência de novos writes no legado
- `apps/web/services/api/tests/unit/operacional/test_backfill_estoque_movimentacoes.py`
  - teste do script de backfill
- `apps/web/services/api/tests/unit/operacional/test_estoque_movimentacoes_guardrails.py`
  - teste estático da allowlist
- `apps/web/services/api/migrations/env.py`
  - import estrutural de metadata ORM

Leitura prática:

- não há mais serviços funcionais consultando `MovimentacaoEstoque`
- não há mais routers/services com fallback de leitura para `estoque_movimentacoes`
- as referências restantes são estruturais, históricas ou de teste

### Validação dos guardrails

Comando executado:

```bash
services/api/.venv/bin/pytest \
  apps/web/services/api/tests/unit/operacional/test_estoque_movimentacoes_guardrails.py \
  apps/web/services/api/tests/integration/operacional/test_estoque.py
```

Resultado:

- `13 passed`
- warnings apenas deprecações antigas de Pydantic, fora do escopo desta auditoria

## Conclusões auditadas

### 1. Uso funcional

Status: `ZERO USO FUNCIONAL`

Conclusão:

- nenhuma leitura funcional depende de `estoque_movimentacoes`
- Safra e Relatórios já operam exclusivamente sobre `estoque_movimentos`
- não há código de negócio ativo autorizado a consultar o legado

### 2. Novos writes

Status: `ZERO WRITES NOVOS`

Conclusão:

- o teste de integração de estoque continua verificando que os fluxos atuais não criam linhas em `estoque_movimentacoes`
- o legado permanece apenas como histórico `read-only`

### 3. Artefatos estruturais remanescentes

Status: `PRESENTES E ESPERADOS`

Permanecem no repositório:

- model legado ORM:
  - `apps/web/services/api/operacional/models/estoque.py`
- metadata de migrations:
  - `apps/web/services/api/migrations/env.py`
- migrations históricas que referenciam a tabela:
  - `apps/web/services/api/migrations/versions/*.py`
- script congelado de backfill:
  - `apps/web/services/api/scripts/backfill_estoque_movimentacoes.py`
- testes de proteção/compatibilidade:
  - `apps/web/services/api/tests/integration/operacional/test_estoque.py`
  - `apps/web/services/api/tests/unit/operacional/test_backfill_estoque_movimentacoes.py`
  - `apps/web/services/api/tests/unit/operacional/test_estoque_movimentacoes_guardrails.py`

## Classificação final dos resíduos

- `estrutural obrigatório`
  - model ORM legado
  - `migrations/env.py`
  - migrations históricas
- `congelado para histórico`
  - script de backfill
- `proteção de desativação`
  - teste guarda de ausência de novos writes
  - teste estático de allowlist
- `teste histórico controlado`
  - teste unitário do backfill

## Parecer pré-remoção física

Situação atual:

- `0` leituras funcionais
- `0` writes novos
- apenas artefatos estruturais e testes residuais

Parecer:

- o sistema está pronto para a próxima etapa de planejamento da remoção física
- a remoção da tabela **ainda não deve ser executada nesta etapa**
- antes da remoção física, o plano deve cobrir explicitamente:
  - ajuste de metadata/imports do Alembic
  - remoção ou isolamento final do model ORM legado
  - destino do script congelado de backfill
  - política para preservação histórica/auditoria após drop da tabela

