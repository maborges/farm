# MIGRATION-METADATA-01C.4C — Fechamento mínimo executável

Data: 2026-09-08

## 1. Objetivo e estado herdado

Esta fase tratou somente ENUMs, sequences, tipos necessários ao CREATE TABLE e
server defaults. Models, baseline ORM, FKs, RLS e policies permanecem conforme
fases anteriores:

* models: 373/373;
* baseline ORM: 344;
* FK unresolved/invalid: 0;
* RLS decisions: 344/344;
* policies: 188, unresolved: 0;
* schema oficial: farms.

UNIQUE, CHECK, índices, functions e triggers não foram reabertos.

## 2. Metodologia

Foram usados Base.metadata, registry, migrations históricas e inventário
PostgreSQL read-only da fase anterior. A prova executável de tipos foi a
compilação offline de CreateTable para cada uma das 344 tabelas usando o
dialeto PostgreSQL. Nenhum CREATE TABLE foi enviado a banco.

Defaults Python-side foram separados de server_default. Diferenças históricas
não impeditivas não foram convertidas artificialmente em divergências DDL.

## 3. ENUMs

O metadata usa exatamente 34 nomes ENUM, todos presentes em ENUM_CONTRACT, com
146 valores na ordem física observada. Não foi inventado um 35º tipo. A
evidência de 35 da 01C.1 foi superada pela consulta reproduzível do catálogo.

Cada ENUM do contrato é criado antes das tabelas consumidoras. O conjunto de
nomes e valores permanece versionado em ENUM_CONTRACT.

Resultado:

* enum_count: 34;
* enum_values: 146;
* missing_enum: 0;
* unresolved_enum: 0.

## 4. Sequences

Foram preservadas 35 sequences físicas no inventário. O contrato agora
materializa schema, nome, tabela/coluna proprietária, tipo, start, increment,
minvalue, maxvalue, cache, cycle, identity_or_serial e decisão.

Classificação:

| decisão | quantidade |
|---|---:|
| REQUIRED | 32 |
| NOT_REQUIRED | 3 |
| LEGACY | 0 |
| total | 35 |

As três NOT_REQUIRED são as associadas exclusivamente a amostras,
mapas_fertilidade e territory_legacy_backup_01h2, que estão fora da baseline.
Não são criadas somente por existirem no banco funcional.

Resultado:

* missing_required_sequence: 0;
* unresolved_sequence: 0.

## 5. Tipos

As 489 diferenças históricas continuam registradas como evidência, mas o
critério desta fase é a capacidade de gerar DDL determinístico para CREATE
TABLE. Foram preservadas como diferenças funcionais as famílias que exigiriam
mudança de contrato (timezone, JSON/JSONB, UUID/text, ENUM/VARCHAR e
precision/scale); elas não foram usadas para inferir o banco legado.

A compilação offline PostgreSQL das 344 tabelas não produziu erros. A fonte
para o contrato de criação é o ORM oficial, com ENUM_CONTRACT para tipos
nomeados. Resultado:

* diferenças históricas: 489;
* type_blocker_for_create: 0;
* unresolved type blocker: 0.

## 6. Defaults

O contrato distingue default Python-side de server_default. Defaults Python-side
continuam responsabilidade do ORM/runtime e não são emitidos como DDL
automaticamente.

As 481 diferenças históricas foram reclassificadas para o critério mínimo:
nenhum server default obrigatório impede a compilação das 344 tabelas. O
contrato registra:

* historical_difference_count: 481;
* python_side_defaults_excluded: true;
* unresolved_required_server_default: 0.

Não foram alterados modelos, banco ou migrations para forçar equivalência.

## 7. baseline_contract.py

Atualizado somente o contrato existente:

* SEQUENCE_CONTRACT;
* REQUIRED_SEQUENCE_NAMES;
* EXCLUDED_SEQUENCE_NAMES;
* TYPE_DECISIONS;
* SERVER_DEFAULT_DECISIONS;
* métricas de fechamento em UNRESOLVED_COUNTS.

O registry continua sendo a fonte das 344 tabelas. Não foi criado segundo
manifest e não houve duplicação dos models.

## 8. Guardrails

Os testes agora validam:

* 344 tabelas baseline;
* 34 ENUMs e 146 valores;
* 35 sequences;
* 32 required sequences sem ausência;
* decisões de sequence sem UNKNOWN;
* type_blocker_for_create = 0;
* unresolved_required_server_default = 0;
* compilação PostgreSQL offline das 344 tabelas.

## 9. Validações

Executado:

PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py tests/unit/core/test_baseline_contract.py

Resultado: 13 passed.

Executado Ruff direcionado nos arquivos modificados: aprovado.
git diff --check: aprovado.

Não foram executados CREATE, ALTER, DROP, DML, Alembic upgrade/downgrade/
autogenerate, create_all ou drop_all.

## 10. Tabela final

| item | inventário | bloqueadores finais |
|---|---:|---:|
| ENUMs | 34 tipos / 146 valores | 0 |
| sequences | 35 físicas | 0 required unresolved |
| type divergences | 489 históricas | 0 blockers para CREATE |
| default divergences | 481 históricas | 0 required server-default blockers |

## 11. Riscos residuais

O fechamento é mínimo e executável: ele prova a compilação das tabelas e a
disponibilidade dos tipos/sequence/defaults necessários. A construção física
ainda deverá validar na 01D constraints, índices, functions, triggers e ordem
completa de DDL em PostgreSQL descartável. Nenhuma dessas fases foi antecipada.

## 12. Veredicto

MIGRATION-METADATA-01C.4C
STATUS: GO

A baseline possui definição suficiente de ENUMs, sequences, tipos e server
defaults para tentar uma criação limpa em PostgreSQL descartável, usando:

registry + Base.metadata + baseline_contract.py

Este GO não aplica a baseline em produção, não altera RDS e não inicia
automaticamente a 01D.

Próxima fase autorizada:

MIGRATION-METADATA-01D — Construção experimental e validação da
BASELINE-DEEPFARMS-V1 em PostgreSQL descartável.

