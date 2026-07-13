# Relatório de Execução: ERP-LIFECYCLE-01D.2 — Migration de Unicidade Física de `TenantIntegracao`

**Fase:** ERP-LIFECYCLE-01D.2  
**Data:** 2026-07-12  
**Banco consultado:** `farms`  
**Revision Alembic:** `20260712_integrations_tenant_integracao_unique_indexes`  
**Down revision:** `f1dfe22c7fa5`  
**Veredicto:** `GO`

## 1. Resumo
Foi criada e validada uma migration Alembic que adiciona unicidade física para `farms.tenant_integracoes` em dois escopos:

- `TENANT`
- `ESTABELECIMENTO`

A implementação usa índices únicos parciais no schema `farms`, preserva `deleted_at IS NULL` na regra física e não altera adapters, services, routers, frontend, Wizard, IAM ou billing.

## 2. Migration criada
Arquivo:

- [services/api/migrations/versions/20260712_integrations_tenant_integracao_unique_indexes.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260712_integrations_tenant_integracao_unique_indexes.py)

Teste de contrato:

- [services/api/tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py)

## 3. Índices criados
Nomes finais:

- `uq_tenant_integracoes_provider_scope_tenant`
- `uq_tenant_integracoes_provider_scope_estabelecimento`

Predicados:

- `scope_type = 'TENANT' AND scope_id IS NULL AND deleted_at IS NULL`
- `scope_type = 'ESTABELECIMENTO' AND scope_id IS NOT NULL AND deleted_at IS NULL`

Colunas:

- Tenant: `(tenant_id, integracao_id)`
- Estabelecimento: `(tenant_id, integracao_id, scope_id)`

## 4. Decisão sobre `deleted_at`
`deleted_at IS NULL` foi mantido no predicado dos dois índices.

Motivo:

- `deleted_at` já funciona como remoção lógica na base consultada
- linhas ativas/inativas continuam ocupando a identidade canônica
- somente registros removidos logicamente deixam de competir pela chave

## 5. Verificação de duplicidades
Consulta local em `farms.tenant_integracoes`:

- total de linhas: `0`
- duplicidades TENANT: `0`
- duplicidades ESTABELECIMENTO: `0`
- registros TENANT com `scope_id` preenchido: `0`
- registros ESTABELECIMENTO com `scope_id` nulo: `0`

Conclusão:

- não havia saneamento a executar neste ambiente
- a migration aborta com mensagem objetiva se encontrar duplicidade ou escopo inválido em outro ambiente

## 6. Escopos inválidos
Foi validado que a migration detecta e rejeita, antes do índice:

- `TENANT` com `scope_id` preenchido
- `ESTABELECIMENTO` com `scope_id` nulo

No ambiente local consultado, ambos os contadores ficaram em `0`.

## 7. Estrutura Alembic
O head antes da fase era:

- `f1dfe22c7fa5`

O upgrade da migration foi aplicado e `alembic current` passou a reportar:

- `20260712_integrations_tenant_integracao_unique_indexes (head)`

## 8. Estratégia de `CONCURRENTLY`
A migration usa `CREATE UNIQUE INDEX CONCURRENTLY` e `DROP INDEX CONCURRENTLY`.

Implementação:

- o código encerra a transação corrente do bind antes do bloco concorrente
- o bloco concorrente é executado com `op.get_context().autocommit_block()`
- o downgrade remove apenas os dois índices criados nesta fase

Observação operacional:

- durante a validação local houve uma sessão em `idle in transaction` que bloqueou o primeiro `CREATE INDEX CONCURRENTLY`
- a sessão foi terminada para completar a validação
- após isso, o upgrade, downgrade e re-upgrade concluíram com sucesso

## 9. Comportamento em falha
Se a migration encontrar qualquer um dos casos abaixo, ela aborta antes de criar índices:

- duplicidade por chave candidata
- registro `TENANT` inválido com `scope_id` preenchido
- registro `ESTABELECIMENTO` inválido com `scope_id` nulo

Se a criação concorrente encontrar índice existente inválido, a migration remove o índice inválido antes de tentar recriar.

## 10. Índice inválido
O helper de upgrade/downgrade checa o catálogo (`pg_class` + `pg_index`) para distinguir:

- índice inexistente
- índice existente e válido
- índice existente e inválido

Isso evita tratar existência nominal como sucesso.

## 11. Downgrade
O downgrade remove somente:

- `uq_tenant_integracoes_provider_scope_estabelecimento`
- `uq_tenant_integracoes_provider_scope_tenant`

Não remove:

- PK
- FKs
- checks
- RLS
- policies
- dados

## 12. Model metadata
Não foi alterado `TenantIntegracao.__table_args__`.

Decisão:

- a fonte de verdade desta fase é a migration física
- não houve drift de metadata para o model nesta execução
- a modelagem futura pode espelhar os índices se o projeto decidir padronizar isso

## 13. PostgreSQL
Validações feitas:

- `alembic upgrade head`
- `alembic current`
- verificação no catálogo com `pg_class` / `pg_index`
- `alembic downgrade -1`
- `alembic upgrade head` novamente

Resultado final do catálogo:

- ambos os índices existem em `farms`
- ambos estão `indisvalid = true`
- ambos estão `indisready = true`

## 14. SQLite
A migration mantém fallback de teste para SQLite com índice parcial equivalente.

Não foi usada nenhuma simulação de `CONCURRENTLY` em SQLite.

## 15. RLS
RLS permanece inalterado.

Não houve:

- mudança de owner
- mudança de policies
- mudança em `tenant_id`
- alteração de escopo de visibilidade

## 16. Testes executados
Comandos executados:

- `cd services/api && .venv/bin/pytest -q tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py`
- `cd services/api && .venv/bin/ruff check migrations/versions/20260712_integrations_tenant_integracao_unique_indexes.py tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py`
- `cd services/api && .venv/bin/alembic current`
- `cd services/api && .venv/bin/alembic downgrade -1`
- `cd services/api && .venv/bin/alembic upgrade head`
- `git diff --check`
- `git -C apps/web diff --check`

Resultados:

- `3 passed` na suíte nova da migration
- `ruff` sem erros
- `alembic current` no head esperado
- downgrade e re-upgrade concluídos
- `diff --check` limpo

## 17. Arquivos alterados
Arquivos desta fase:

- [services/api/migrations/versions/20260712_integrations_tenant_integracao_unique_indexes.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260712_integrations_tenant_integracao_unique_indexes.py)
- [services/api/tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_tenant_integracao_unique_indexes_migration.py)
- [docs/implementation/reports/ERP-LIFECYCLE-01D2-MIGRATION-UNICIDADE-TENANT-INTEGRACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-LIFECYCLE-01D2-MIGRATION-UNICIDADE-TENANT-INTEGRACAO.md)

Não houve alteração nesta fase em:

- frontend
- adapters
- routers
- services
- Wizard
- IAM
- billing
- Estoque P2
- Pedidos P2

## 18. Riscos e limitações
Riscos remanescentes:

- a concorrência ainda pode ser impactada por sessões externas em `idle in transaction`
- a fase não implementa tratamento de `IntegrityError` e reread, que fica para `01D.3`

Limitações:

- não houve necessidade de saneamento no banco local consultado
- não houve alteração de metadata do model

## 19. Veredicto
`GO`

Justificativa:

- os dois índices únicos parciais foram criados
- a proteção física de `TENANT` e `ESTABELECIMENTO` foi validada
- a semântica de `NULL` ficou correta
- o downgrade remove apenas os índices da fase
- o upgrade local passou
- o catálogo físico foi validado
- RLS permaneceu intacto

## 20. Recomendação para `ERP-LIFECYCLE-01D.3`
Iniciar a próxima fase com:

- tratamento de `IntegrityError`
- reread do registro existente
- preservação da idempotência concorrente
- testes de concorrência no adapter canônico

