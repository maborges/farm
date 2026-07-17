# TENANT-FK-REPAIR-01A — Quarentena de cruzamentos A→B

## Contexto

103 associações onde `filho.tenant_id ≠ pai.tenant_id` foram identificadas em 7 tabelas críticas (auditoria 2026-07-17). Esses registros representam vazamento de dados entre tenants.

## Tabelas afetadas

| Tabela | Cruzamentos | Pai principal |
|--------|-------------|---------------|
| `cadastros_areas_rurais` | 43 | `unidades_produtivas` |
| `frota_apontamentos_uso` | 16 | `frota_jornadas_equipamento` |
| `frota_jornadas_equipamento` | 15 | `unidades_produtivas` |
| `estoque_depositos` | 14 | `unidades_produtivas` |
| `frota_abastecimentos` | 8 | `cadastros_equipamentos` |
| `cadastros_equipamentos` | 4 | `unidades_produtivas` |
| `compras_pedidos` | 3 | `estoque_depositos` |

## Sequência de execução

```bash
# 1. Aplicar migration (cria tenant_fk_quarantine)
cd services/api
alembic upgrade tenant_fk_repair_01a

# 2. Diagnóstico — revisar ANTES de quarentenar
psql $DATABASE_URL -f scripts/tenant_fk_repair/01a_diagnose.sql > /tmp/diagnose_$(date +%Y%m%d).txt

# 3. Quarentena (em staging primeiro, produção depois)
psql $DATABASE_URL -f scripts/tenant_fk_repair/01a_quarantine.sql

# 4. Verificar quarentena
psql $DATABASE_URL -c "SELECT source_table, COUNT(*) FROM farms.tenant_fk_quarantine WHERE NOT resolved GROUP BY 1"

# 5. Resolver (escolher ação no 01a_resolve.sql e descomentar)
psql $DATABASE_URL -f scripts/tenant_fk_repair/01a_resolve.sql
```

## Decisão por tabela

Antes de resolver, definir por tabela:

- **delete** — dados de teste/migração, sem valor de negócio
- **restore** — erro de tenant_id, dados pertencem ao tenant original
- **reassign** — dado pertence ao tenant do pai; atualizar tenant_id do filho

## Reversão de emergência

Se a quarentena for executada e precisar ser desfeita antes da resolução, usar a Opção B (restore) no `01a_resolve.sql` para todas as tabelas.
