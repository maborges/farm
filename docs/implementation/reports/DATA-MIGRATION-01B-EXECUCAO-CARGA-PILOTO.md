# DATA-MIGRATION-01B — Execução controlada da carga no PostgreSQL do piloto

## Veredicto

`DATA-MIGRATION-01B STATUS: NO-GO`

A carga não foi executada. O ambiente disponibilizou e confirmou somente a
origem PostgreSQL no schema `farms`; não foi disponibilizada uma conexão
separada para o banco piloto. Sem o destino não é possível executar o
pre-flight obrigatório, proteger contra inversão origem/destino, confirmar a
revision `baseline_deepfarms_v1`, validar RLS/policies ou comparar os dados
após a carga.

## Evidência da origem

- 351 tabelas físicas;
- 154 tabelas com registros;
- 21.637 registros;
- 2 tenants;
- 338 classificações `DIRECT_COPY`;
- 1 classificação `TRANSFORM`: `compras_pedidos.deposito_id` deve ser `NULL`;
- 12 tabelas `EXCLUDED`;
- 5 tabelas `EMPTY_TARGET`;
- `REVIEW_REQUIRED = 0`;
- FK, tenant, CHECK, UNIQUE, ENUM e NOT NULL violations: 0;
- 52 ciclos de FK identificados no grafo da baseline;
- 33 sequências identificadas para ajuste posterior.

Os números acima foram produzidos pelo auditor versionado de 01A em modo
somente leitura. Nenhum `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, DDL ou
`setval` foi executado.

## Pré-flight pendente

Antes de qualquer execução, fornecer no ambiente de execução uma variável
`TARGET_DATABASE_URL` apontando para o PostgreSQL piloto, sem registrar a
credencial no repositório. O executor deverá confirmar, no destino:

- database, host e usuário esperados;
- schema `farms`;
- revision Alembic `baseline_deepfarms_v1`;
- 344 tabelas presentes;
- destino sem dados operacionais;
- RLS e policies da baseline preservados;
- fingerprint diferente da origem.

Sem essas confirmações, o menor conjunto seguro de ações é zero alterações.

## Próxima ação

Após a disponibilização do destino, criar/executar
`services/api/scripts/data_migration/migrate_data.py` com modos explícitos
`--plan`, `--execute` e `--validate`, utilizando o inventário congelado de
01A, SCCs calculados e evidência JSON sem secrets. A carga deverá permanecer
bloqueada até que o tratamento dos 52 ciclos e o pre-flight do destino sejam
validados.
