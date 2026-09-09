# MIGRATION-METADATA-01D4 — Correção dos blockers da baseline

## Veredicto

```text
MIGRATION-METADATA-01D4 STATUS: GO PARA PROVA POSTGRESQL
```

Os cinco blockers identificados em 01D3 foram corrigidos no desenvolvimento.
Nenhuma migration histórica, RDS, EC2, arquitetura ERP ou decisão de Tenant
Integrity foi alterada. A baseline está liberada somente para a próxima prova
online em PostgreSQL vazio; não houve execução no RDS nesta fase.

## Arquivos alterados

- `services/api/enterprise/models/sprints_27_33.py`
- `services/api/enterprise/services/sprints_27_33_service.py`
- `services/api/pecuaria/advanced_schemas.py`
- `services/api/core/cadastros/equipamentos/models.py`
- `services/api/operacional/models/frota.py`
- `services/api/operacional/models/estoque.py`
- `services/api/operacional/models/compras.py`
- `services/api/migrations/metadata_audit.py`
- `services/api/tests/migrations/test_baseline_metadata_audit.py`
- `docs/implementation/reports/MIGRATION-METADATA-01D4-CORRECAO-BLOCKERS-BASELINE.md`

## Decisões semânticas

### `cochos.responsavel_id`

O campo representa o usuário responsável pelo registro: o model tinha FK
direta para `usuarios.id`, e a migration `67b25594e50f_add_confinamento_models.py`
declara o campo como `postgresql.UUID` com a mesma FK. A ocorrência `Integer`
em `fase3_sprints27_33_final.py` é evidência histórica divergente do contrato
canônico atual. Não foram encontrados schemas, inserts ou updates que tratem o
valor como código textual alternativo. O campo foi alinhado para
`UUID(as_uuid=True)` e a FK foi preservada.

### `confinamento_lotes.unidade_produtiva_id`

O campo referencia a unidade produtiva oficial. O pai
`unidades_produtivas.id` é UUID e a migration
`67b25594e50f_add_confinamento_models.py` já usava UUID nessa coluna. O schema
Pydantic e o serviço antigo ainda tipavam o valor como `int`; ambos foram
alinhados para UUID. Não foi criado cast implícito nem removida a FK.

## Constraints restauradas

Foram restauradas no ORM, com os nomes fechados pelo histórico Tenant
Integrity:

- `uq_unidades_produtivas_tenant_id_id`
- `uq_cadastros_equipamentos_tenant_id`
- `uq_frota_jornadas_tenant_id`
- `uq_estoque_depositos_tenant_id`

Também foi restaurada em `PedidoCompra` a coluna UUID nullable `deposito_id` e
a FK composta:

```text
fk_cp_tenant_deposito
compras_pedidos (tenant_id, deposito_id)
  → estoque_depositos (tenant_id, id)
ON DELETE NO ACTION
```

As demais relações compostas fechadas permanecem presentes:
`fk_car_tenant_unidade_produtiva`, `fk_ed_tenant_unidade_produtiva`,
`fk_ce_tenant_unidade_produtiva`, `fk_fje_tenant_unidade_produtiva`,
`fk_fau_tenant_jornada` e `fk_fa_tenant_equipamento`.

## Resultado do auditor

O auditor reutilizado em `migrations/metadata_audit.py` retornou:

| Verificação | Resultado |
|---|---:|
| Incompatibilidades de tipo PostgreSQL | 0 |
| FKs compostas sem PK/UNIQUE compatível | 0 |
| Targets fora da baseline | 0 |
| CHECKs com coluna inexistente | 0 |
| Relações Tenant Integrity ausentes | 0 |
| Tabelas baseline | 344 |
| FKs baseline | 892 |

O aumento de 891 para 892 FKs é esperado: corresponde à restauração de
`fk_cp_tenant_deposito`.

## Validações

```text
PYTHONPATH=. .venv/bin/pytest -q tests/migrations/test_baseline_metadata_audit.py
6 passed

PYTHONPATH=. .venv/bin/pytest -q \
  tests/unit/core/test_model_registry.py \
  tests/unit/core/test_baseline_ddl_contract.py \
  tests/unit/core/test_baseline_contract.py
14 passed

.venv/bin/ruff check migrations/metadata_audit.py tests/migrations/test_baseline_metadata_audit.py
All checks passed

PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql \
  > /tmp/migration-metadata-01d4-baseline.sql
return code 0

git diff --check
passed
```

O SQL offline contém as quatro UNIQUEs compostas antes das FKs e a emissão de
`fk_cp_tenant_deposito` com `ON DELETE NO ACTION`.

Foi executada adicionalmente a suíte `tests/unit/pecuaria/test_advanced_service.py`.
Ela apresentou uma falha preexistente no teste `test_resumo_genetica_agrega_registros`:
o `AsyncMock` fornece somente duas respostas, enquanto o serviço executa mais
consultas. A falha ocorre no fluxo de genética e não é causada pelas alterações
de confinamento; não foi modificada por estar fora do escopo 01D4.

## Blockers remanescentes

Nenhum blocker estrutural da 01D3 permanece. A prova online em database
PostgreSQL vazio ainda não foi executada e constitui a próxima fase, não uma
alteração desta entrega.
