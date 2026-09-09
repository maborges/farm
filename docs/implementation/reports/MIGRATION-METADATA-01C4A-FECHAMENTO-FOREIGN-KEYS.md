# MIGRATION-METADATA-01C.4A — Fechamento de Foreign Keys

Data: 2026-09-08

## 1. Estado herdado

O registry mantém 373 models classificados, 344 tabelas de baseline, zero
pendências, zero colisões e schema farms. A referência inválida
animal_genetica.animal_id → lotes.id já havia sido removida na 01C.2.

A 01C.3 registrou 248 tabelas com divergência de Foreign Key. Esta fase tratou
exclusivamente FKs.

## 2. Metodologia

A matriz final é gerada pela função build_fk_contract() em
services/api/migrations/baseline_contract.py, usando exclusivamente a Base
oficial e baseline_candidate_tables(). A unidade é a constraint, não cada
elemento isolado, preservando FKs compostas.

Foram validados:

* target table e target columns no metadata;
* source/target columns e ordem;
* on delete/update;
* nome da constraint quando disponível;
* classificação e fonte da decisão;
* ausência de target fora do registry/base set;
* regra Tenant Integrity para referências a tenants.

A matriz de banco/migration continua evidência histórica do snapshot da 01C.1;
a decisão de instalação limpa é explícita no contrato ORM oficial e nos
overrides de Tenant Integrity.

## 3. Resultado do inventário

| item | quantidade |
|---|---:|
| tabelas ORM baseline | 344 |
| constraints FK da baseline | 891 |
| elementos FK individuais | 897 |
| FKs compostas | 6 |
| divergências iniciais por tabela | 248 |
| targets inválidos | 0 |
| targets fora da baseline | 0 |
| FKs com Tenant Integrity override | 233 |
| decisões sem UNKNOWN/PENDING/UNRESOLVED | 891 |

## 4. Normalização e classificação

Nome de constraint, schema qualification e NO ACTION implícito foram tratados
como representação quando não alteram a relação. Não foram normalizados
CASCADE, RESTRICT, NO ACTION, SET NULL ou SET DEFAULT entre si. Também não
foram reduzidas FKs compostas a FKs simples.

A classificação final do contrato é:

| classificação | quantidade |
|---|---:|
| MATCH | 0 |
| REPRESENTATION_ONLY | 0 |
| TENANT_INTEGRITY_OVERRIDE | 233 |
| ORM_CURRENT | 658 |
| DATABASE_CURRENT | 0 |
| MIGRATION_CURRENT | 0 |
| LEGACY_DATABASE | 0 |
| LEGACY_ORM | 0 |
| MANUAL_CONTRACT | 0 |
| INVALID | 0 |
| UNRESOLVED | 0 |

As divergências físicas iniciais não foram copiadas cegamente. Quando não
havia decisão histórica específica de Tenant Integrity, a definição ORM
registrada foi escolhida como contrato de instalação nova. Isso torna a escolha
reproduzível; não afirma que o banco legado seja idêntico.

## 5. Tenant Integrity

Para toda FK da baseline que aponta para tenants e declarava CASCADE no ORM,
o contrato aplica explicitamente:

source_of_decision = TENANT_INTEGRITY
baseline_on_delete = RESTRICT

Assim, nenhuma FK de tenant do contrato final reintroduz CASCADE. As demais
ações não relacionadas diretamente ao parent tenants permanecem conforme a
declaração ORM, inclusive SET NULL e CASCADE quando pertencem a relações de
domínio não cobertas por essa regra.

Estado guardado pelo contrato:

* Tenant Integrity override: 233;
* baseline tenant CASCADE: 0;
* target inválido: 0.

## 6. FKs compostas

As seis constraints compostas são representadas por uma única entrada, com
source_columns e target_columns como tuplas ordenadas. Nenhuma foi dividida ou
duplicada. A função build_fk_contract() usa
table.foreign_key_constraints, evitando a perda da unidade da constraint.

## 7. Tenant-scoped e integrações

Não foi criada nova arquitetura de tenancy. As relações existentes com tenants,
tenant_integracoes, integration_* e sankhya_* foram preservadas conforme o
metadata oficial e os overrides aprovados. Sankhya não foi consolidado ou
redesenhado.

## 8. Cinco tabelas novas

As tabelas crm_ofertas_personalizadas, crm_planos_comerciais,
crm_precificacao_modulo, crm_produtos e growth_landing_eventos permanecem
INCLUDE. Suas FKs são resolvidas contra targets presentes no registry oficial;
nenhum target ausente foi encontrado.

## 9. Tabelas excluídas

Nenhuma FK da baseline aponta para as tabelas físicas excluídas:

* amostras;
* mapas_fertilidade;
* territory_legacy_backup_01h2;
* oito tabelas antigas balanca_*.

Não houve DROP nem alteração física.

## 10. Alterações

* baseline_contract.py agora gera FK_CONTRACT completo por constraint,
  incluindo FKs compostas e campos de decisão;
* foi registrada a política TENANT_INTEGRITY_ON_DELETE = RESTRICT;
* test_baseline_contract.py ganhou guardrail de target, classificação e bloqueio
  de CASCADE para tenants;
* este relatório foi criado.

Não foram alterados migrations históricos, banco, RDS, dados, env.py ou outros
domínios. A correção anterior de animal_genetica foi apenas preservada.

## 11. Guardrails

Os testes verificam:

* 373 models;
* 344 tabelas baseline;
* zero pending e zero colisões;
* schema farms;
* zero target inválido;
* zero target fora do metadata;
* nenhuma FK UNKNOWN/PENDING/UNRESOLVED;
* nenhuma FK baseline para tenants com CASCADE;
* manutenção das tabelas Balança fora da baseline.

## 12. Validações

Executado:

PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py tests/unit/core/test_baseline_contract.py

Resultado: 11 passed.

Também executado Ruff direcionado nos arquivos relevantes: aprovado.
git diff --check: aprovado.

Não foram executados upgrade, downgrade, autogenerate, create_all, drop_all ou
qualquer comando mutável no PostgreSQL.

## 13. Tabela de fechamento

| classificação | quantidade |
|---|---:|
| MATCH | 0 |
| REPRESENTATION_ONLY | 0 |
| TENANT_INTEGRITY_OVERRIDE | 233 |
| ORM_CURRENT | 658 |
| DATABASE_CURRENT | 0 |
| MIGRATION_CURRENT | 0 |
| LEGACY_DATABASE | 0 |
| LEGACY_ORM | 0 |
| MANUAL_CONTRACT | 0 |
| INVALID | 0 |
| UNRESOLVED | 0 |

## 14. Veredicto

MIGRATION-METADATA-01C.4A
STATUS: GO

As Foreign Keys da futura baseline estão fechadas no contrato reproduzível:

* 891 constraints decididas;
* 6 compostas preservadas;
* unresolved_fk = 0;
* invalid_fk_target = 0;
* baseline tenant CASCADE = 0.

Este GO autoriza somente a próxima subfase de fechamento DDL de RLS e
Policies. Não autoriza a construção da BASELINE-DEEPFARMS-V1 nem inicia a 01D.

Próxima fase:

MIGRATION-METADATA-01C.4B — Fechamento de RLS e Policies.

