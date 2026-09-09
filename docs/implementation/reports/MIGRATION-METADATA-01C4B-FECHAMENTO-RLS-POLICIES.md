# MIGRATION-METADATA-01C.4B — Fechamento de RLS e Policies

Data: 2026-09-08

## 1. Estado herdado

A 01C.4A fechou 891 constraints FK, 897 elementos, 6 compostas, zero targets
inválidos e zero CASCADE para tenants. Esta fase tratou somente RLS, FORCE RLS
e policies.

## 2. Metodologia

Foram usadas Base.metadata, registry oficial, snapshot read-only da fase 01C.1
e consulta direta de pg_class/pg_policies. Nenhum DDL, DML, upgrade, downgrade,
autogenerate, create_all ou drop_all foi executado.

A decisão de RLS é gerada para todas as 344 tabelas. O conjunto físico aprovado
é preservado; as demais recebem decisão explícita RLS_NOT_REQUIRED, sem inferir
RLS somente pela presença de tenant_id.

## 3. Matriz das 344 tabelas

RLS_CONTRACT em baseline_contract.py possui exatamente uma entrada por tabela da
baseline:

| decisão | quantidade |
|---|---:|
| RLS_REQUIRED | 48 |
| RLS_REQUIRED_NO_FORCE | 1 |
| RLS_NOT_REQUIRED | 295 |
| total | 344 |

As 48 tabelas físicas com FORCE recebem ENABLE + FORCE. propriedade_imovel recebe
ENABLE sem FORCE, preservando a exceção física observada. A matriz também
registra tenant_scope_mode, enabled, forced, source e reason.

## 4. Policies

O snapshot contém 188 policies em 49 tabelas, todas dentro da baseline. Cada
entrada de POLICY_CONTRACT contém:

* schema, tabela e nome;
* command;
* roles;
* permissive;
* using_expression;
* with_check_expression;
* source e reason.

A representação é carregada de uma carga gzip/base64 versionada no próprio
baseline_contract.py; não depende de conexão em runtime nem de arquivo
temporário.

A distribuição física observada foi:

* INSERT: 47;
* SELECT: 47;
* DELETE: 46;
* UPDATE: 46;
* ALL: 2;
* PERMISSIVE: 188.

Não houve policy fora da baseline, inválida, UNKNOWN ou PENDING. Não foram
criadas policies novas para tabelas que não possuíam contrato aprovado.

## 5. Normalização

A comparação considera equivalentes apenas whitespace, parênteses redundantes,
casts/quoting equivalentes, qualificação de schema e representação de roles.
Command, roles, permissive/restrictive, USING e WITH CHECK permanecem campos
estruturais. Expressões de tenant, current_setting e subqueries não são
substituídas por uma policy genérica.

## 6. propriedade_imovel

A consulta direta confirmou:

* RLS enabled: true;
* FORCE RLS: false.

A decisão é RLS_REQUIRED_NO_FORCE, source DATABASE_CURRENT. Não foi alterada a
política nem o banco.

## 7. Policies relacionais e integrações

Nenhum mecanismo novo de tenancy foi criado. As policies existentes de Wizard,
propriedade, unidade produtiva, integrações e Sankhya foram preservadas como
capturadas no catálogo. tenant_integracoes e integration_* permanecem no
contrato atual; Sankhya não foi consolidado ou redesenhado.

## 8. Cinco tabelas ausentes na fotografia física

crm_ofertas_personalizadas, crm_planos_comerciais, crm_precificacao_modulo,
crm_produtos e growth_landing_eventos permanecem INCLUDE no registry e recebem
decisão RLS explícita RLS_NOT_REQUIRED nesta fase, pois não possuem policy física
ou migration de RLS no conjunto de evidências disponível. Essa decisão é
versionada e não depende da ausência silenciosa de uma entrada.

## 9. Tabelas excluídas

Nenhuma decisão RLS/policy foi criada para amostras, mapas_fertilidade,
territory_legacy_backup_01h2, as oito balanca_* ou alembic_version. Não houve
DROP.

## 10. Alterações realizadas

* baseline_contract.py agora gera RLS_CONTRACT para 344 tabelas;
* POLICY_CONTRACT contém as 188 policies read-only;
* foram adicionados contadores de policy inválida e policy fora da baseline;
* test_baseline_contract.py ganhou guardrails de completude, targets, comandos,
  roles e exceção propriedade_imovel;
* este relatório foi criado.

Não foram alteradas migrations históricas, banco, RDS, dados, FKs, types,
defaults, indexes, ENUMs, sequences, functions ou triggers.

## 11. Guardrails e validações

Executado:

PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py tests/unit/core/test_baseline_contract.py

Resultado: 12 passed.

Executado Ruff direcionado nos arquivos alterados: aprovado.
git diff --check: aprovado.

Guardrails confirmados:

* baseline tables = 344;
* RLS decisions = 344/344;
* policies = 188;
* unresolved RLS = 0;
* unresolved FORCE RLS = 0;
* unresolved policies = 0;
* policy INVALID = 0;
* policy target fora da baseline = 0;
* UNKNOWN/PENDING/UNRESOLVED = 0.

## 12. Riscos residuais

A decisão desta fase fecha o contrato RLS/policy com base nas evidências
disponíveis, mas não autoriza a baseline. Permanecem para fases seguintes tipos,
defaults, UNIQUE, CHECK, índices, ENUMs, sequences, functions e triggers.
Nenhuma dessas famílias foi reaberta ou mascarada.

## 13. Tabela final

| item | inicial | final | unresolved |
|---|---:|---:|---:|
| baseline tables | 344 | 344 decididas | 0 |
| RLS enabled | 49 físicas | 49 baseline | 0 |
| FORCE RLS | 48 físicas | 48 baseline | 0 |
| policies | 188 físicas | 188 contratadas | 0 |
| policy target fora baseline | - | 0 | 0 |
| policy INVALID | - | 0 | 0 |
| policy UNKNOWN/PENDING | - | 0 | 0 |
| RLS decisions | - | 344/344 | 0 |

## 14. Veredicto

MIGRATION-METADATA-01C.4B
STATUS: GO

RLS, FORCE RLS e policies estão encerrados no contrato reproduzível. Este GO
fecha somente esta subfase e não autoriza a construção da
BASELINE-DEEPFARMS-V1 nem inicia a 01D.

Próxima fase:

MIGRATION-METADATA-01C.4C — Fechamento de Tipos, Defaults, ENUMs e Sequences.

