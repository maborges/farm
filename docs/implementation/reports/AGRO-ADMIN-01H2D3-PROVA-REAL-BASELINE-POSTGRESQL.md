# AGRO-ADMIN-01H2D3 — Prova Real do Baseline PostgreSQL Isolado

**Data:** 2026-10-25  
**Revisão autorizada:** `baseline_deepfarms_v1`  
**Veredicto:** **NO-GO — prova interrompida antes de qualquer migration/DDL DeepFarms**

## 1. Resultado executivo

O gate de identidade confirmou que a conexão da configuração sintética chega ao PostgreSQL do laboratório. A verificação adicional de privilégios, exigida antes do DDL, revelou que o role owner configurado é `SUPERUSER`, com `CREATEDB`, `CREATEROLE`, `REPLICATION` e `BYPASSRLS`. Esse papel pode atuar fora do database descartável. Portanto, não há um papel de execução comprovadamente restrito ao laboratório e a Fase B foi interrompida.

Nenhuma revisão Alembic, `stamp`, downgrade, DDL DeepFarms, operação em outro database, API, frontend ou teste E2E foi executado. O catálogo do database alvo permanece vazio de objetos de aplicação. Não rebaixei o role nem criei outro, porque ambas as ações alterariam privilégios além da autorização limitada à baseline.

## 2. Identidade e isolamento verificados

| Propriedade | Evidência read-only |
|---|---|
| ID/root | `dbdcc24872aa2992`; `/tmp/deepfarms-agro-hml-dbdcc24872aa2992` |
| Servidor | PostgreSQL `16.15 (Ubuntu 16.15-1.pgdg22.04+2)` |
| Endpoint | `127.0.0.1/32`, porta `5433` (o gate estrito aceita esse CIDR exato de loopback) |
| Database | `agro_hml_dbdcc24872aa` |
| Role autenticado na auditoria de privilégios | `agro_hml_owner_dbdcc24872aa`, owner do database |
| Porta/listener e PGDATA | A evidência da Fase B registra PID `1447173`, listener `127.0.0.1:5433` e PGDATA `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` via `pg_ctl status`; o gate de identidade foi repetido nesta fase e passou. |
| Gate existente `agro_labctl.py identity` | **PASS** — database, role, porta/loopback e marcador sintético Redis conferem com o laboratório. |
| Ausência de objetos comerciais/aplicação | **PASS** — no database alvo: schema `farms` ausente, `farms.alembic_version` ausente, zero relações de usuário, zero funções de usuário e zero tipos definidos pelo usuário. Sem objetos de aplicação, não há tabelas/dados comerciais transferidos para esse database. |

O endereço veio como `127.0.0.1/32`, representação CIDR exata do loopback e compatível com o gate ajustado na Fase B. O database, role, porta e versão retornados coincidem com o manifesto sintético. Nenhuma conexão foi aberta para `192.168.0.3`, RDS ou serviço comercial.

## 3. Bloqueio de privilégios

A consulta de catálogo retornou para `agro_hml_owner_dbdcc24872aa`:

| Atributo | Valor |
|---|---:|
| É owner do database alvo | Sim |
| `CREATE` no database alvo | Sim |
| `SUPERUSER` | **Sim** |
| `CREATEDB` | **Sim** |
| `CREATEROLE` | **Sim** |
| `REPLICATION` | **Sim** |
| `BYPASSRLS` | **Sim** |

O ownership e `CREATE` bastariam para vários objetos da baseline, mas os atributos globais tornam o papel inadequado para uma execução que deve ficar restrita ao database do laboratório. O gate de identidade atual comprova destino e marcador, mas não valida os atributos do role; passar esse gate não supera o bloqueio de privilégio.

Não usei o role de aplicação como alternativa: não foi comprovado que ele tenha os privilégios DDL necessários, e mudar grants/roles excederia o escopo autorizado desta prova. Não houve tentativa de DDL com qualquer role.

## 4. Inspeção estática da revisão e do encadeamento

O arquivo `services/api/migrations/versions/20260908_baseline_deepfarms_v1.py` declara:

```text
revision = baseline_deepfarms_v1
down_revision = None
branch_labels = (deepfarms_baseline,)
depends_on = None
```

Assim, o alvo é uma raiz independente. Um upgrade direcionado exclusivamente a `baseline_deepfarms_v1` não requer percorrer a perna histórica que converge em `20260915_merge_documentos_fiscais`; não foi usado `head`, `heads`, `stamp` nem target variável. A presença da outra linhagem no grafo não foi tratada como necessária para esta revisão isolada.

O `env.py` atual configura no modo online o schema de versionamento `farms`, cria esse schema antes de iniciar Alembic e define `search_path`. Para a tabela já existente, a função de capacidade só executa `ALTER COLUMN` se encontrar `farms.alembic_version`; no estado verificado, ela não existe. O catálogo de versionamento, portanto, seria criado dentro do alvo ao aplicar a revisão. Isso foi inspecionado no código; nenhuma conexão Alembic ou SQL de baseline foi executada nesta fase.

## 5. Efeitos estáticos examinados

O corpo de `upgrade()` chama, nesta ordem: `_create_schema`, `_create_enums`, `_create_sequences`, `_create_tables`, `_create_foreign_keys`, `_create_indexes`, `_create_functions_and_triggers` e `_apply_rls_and_policies`.

`CONTRACT_STATUS` em `baseline_contract.py` continua `NO-GO`. Não foi alterado para permitir a execução; a prova PostgreSQL interrompida não resolve as pendências funcionais UNIQUE/CHECK nem os demais critérios do contrato.

| Operação classificada | Fonte/escopo | Execução nesta fase |
|---|---|---|
| Criar `farms` e definir `search_path` | `CREATE SCHEMA IF NOT EXISTS farms`; sessão da conexão Alembic | Não executada |
| Criar ENUMs e sequences | `ENUM_CONTRACT`, `SEQUENCE_CONTRACT`/`REQUIRED_SEQUENCE_NAMES`, schema `farms` | Não executada |
| Criar tabelas e índices | Registry ORM (`baseline_candidate_tables`) e metadata atual | Não executada |
| Criar FKs | Constraints ORM + decisões explícitas `FK_CONTRACT` | Não executada |
| Criar funções e triggers | Três funções e três triggers namespaced via `search_path=farms, pg_catalog` ou tabela em `farms` | Não executada |
| Ativar RLS/FORCE e policies | `RLS_CONTRACT` e `POLICY_CONTRACT` | Não executada |
| DML/seed direto na execução | Não foi identificado DML direto em `upgrade()`; INSERT/UPDATE aparece dentro do corpo de uma função trigger para execução futura da aplicação | Não executada; o corpo futuro não foi testado |
| Chamadas externas | Não identificadas no corpo da revisão nem no fluxo Alembic inspecionado | Não executadas |
| Operações destrutivas | O `downgrade()` contém DROP de policies, triggers, funções, tabelas, sequences, ENUMs e schema `farms` | Não executado; downgrade foi proibido |

Inventário estático declarado no contrato/relatórios do checkout: 348 tabelas selecionadas na baseline (377 models descobertos), 76 UNIQUE e 76 CHECK do ORM, 1.063 índices ORM, 892 FKs, 34 ENUMs/146 labels, 32 sequences requeridas, 49 tabelas com RLS enabled (48 forced), 188 policies e 3 funções/3 triggers. Esses números descrevem o inventário de código, não objetos criados nem resultado de catálogo nesta prova; o catálogo real permaneceu sem schema de aplicação.

## 6. Fases C–E: execução e validações não realizadas

A Fase C foi bloqueada pelo privilégio global do papel antes de chamar Alembic. Logo:

- **Revisão executada:** nenhuma. `baseline_deepfarms_v1` foi apenas inspecionada.
- **Objetos criados:** nenhum objeto DeepFarms; nenhuma tabela `alembic_version`.
- **Comparação real do catálogo:** não aplicável; o banco segue vazio para aplicação. Não há diferenças pós-baseline a atribuir por tabela/constraint.
- **ORM, constraints e dados sintéticos:** não testados.
- **RLS com dois tenants e papéis comuns:** não testado.
- **Estado final:** database descartável sem schema `farms` ou objetos de usuário, sem migrations executadas.

Não declarar baseline íntegra ou inválida a partir desta execução: a prova não chegou a executar o DDL.

## 7. Comandos e evidências desta fase

1. Leitura integral dos relatórios AGRO-ADMIN-01H2C1, 01H2C2, 01H2D1 e 01H2D2.
2. Inspeção read-only da revisão baseline, `migrations/env.py`, `baseline_contract.py`, da configuração do controlador e do estado do workspace.
3. Gate de identidade `scripts/homologacao/agro_labctl.py identity --root /tmp/deepfarms-agro-hml-dbdcc24872aa2992`: **PASS**. Valores secretos foram consumidos somente em processo e não impressos.
4. Consulta read-only, autenticada pelo arquivo sintético do laboratório, ao catálogo do database descartável: identidade esperada, schema/tabela Alembic ausentes, contagens de relações/funções/tipos de usuário iguais a zero e atributos do role listados acima.
5. A rotina auxiliar de preflight encerrou com status de bloqueio ao detectar os atributos globais. Ela também tratou inicialmente o texto `127.0.0.1/32` como diferente da string `127.0.0.1`; a evidência do gate estrito e a normalização CIDR demonstram que a identidade de rede é loopback exato. O motivo efetivo do NO-GO é o role superuser, não o endereço.

O workspace já continha numerosas alterações e arquivos não rastreados antes da prova. Eles foram preservados; a única criação no repositório desta fase é este relatório. Nenhum commit, push ou merge foi feito.

## 8. Pró-requisito para uma nova tentativa

Uma nova autorização será necessária depois de preparar, fora desta tentativa, uma identidade de execução não superuser e sem privilégios globais, limitada ao database descartável e com somente os privilégios requeridos pela baseline. A preparação deve preservar a role administrativa existente; não alterar role existente nem conceder acesso a outro database. Antes da nova execução, repetir gate de identidade, confirmar o PGDATA/PID/listener, database vazio, owner e atributos efetivos da role. Se não for possível obter role apropriado sem exceder autorização, manter NO-GO.

Após esse pré-requisito, a prova deverá obter autorização específica vigente para aplicar somente `baseline_deepfarms_v1` e executar os testes ORM/constraints/RLS previstos. Não usar `upgrade head(s)`, `stamp`, downgrade ou reparo automático.

## 9. Veredicto

**NO-GO — interrompido antes da execução.** O alvo e a revisão foram identificados e o database não continha objetos da aplicação, mas o papel que o ambiente atualmente usa para conectar é superuser e possui poderes de cluster. Nenhuma alteração foi feita no database; aguardar revisão de privilégios e nova autorização antes de qualquer tentativa de DDL.
