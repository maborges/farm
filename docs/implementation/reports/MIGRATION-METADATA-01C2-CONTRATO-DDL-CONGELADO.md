# MIGRATION-METADATA-01C.2 — Contrato DDL e congelamento

Data da auditoria: 2026-09-08  
Status: **NO-GO** para iniciar a 01D.

## 1. Resumo executivo

A 01C.2 corrigiu o defeito inequívoco do metadata: `animal_genetica.animal_id`
declarava `ForeignKey("lotes.id")`, embora `lotes` não exista no registry, na
migration que criou a tabela ou no banco funcional. A migration
`67b25594e50e_add_animal_genetica.py` cria a coluna como `Integer` simples e o
banco não possui essa FK. A declaração ORM inválida foi removida; a coluna foi
preservada.

Também foi criado o contrato machine-readable em
`services/api/migrations/baseline_contract.py`, sem duplicar o registry.
Ele registra schema, decisões de nullable, o bloqueador resolvido, ENUMs,
sequences, RLS, functions, triggers e tabelas físicas excluídas.

O contrato completo ainda não está congelado: permanecem divergências de FK,
tipos, defaults, UNIQUE, CHECK, índices e policies que podem alterar o DDL
da baseline. Portanto o veredicto é `NO-GO`.

## 2. Estado herdado da 01C.1

| evidência | quantidade |
|---|---:|
| models descobertos/classificados | 373/373 |
| tables ORM aprovadas para baseline | 344 |
| tables físicas no schema `farms` | 351 |
| tables físicas compartilhadas | 339 |
| baseline ausentes na fotografia física | 5 |
| tables físicas fora do baseline | 12 |
| diferenças de tipo normalizadas conservadoramente | 489 |
| diferenças nullable | 10 |
| diferenças de presença de default | 383 |
| diferenças de expressão de default | 98 |
| tabelas com FKs divergentes | 248 |
| tabelas com UNIQUE divergente | 11 |
| tabelas com CHECK divergente | 39 |
| tabelas com conjunto de índices divergente | 327 |

## 3. Metodologia

Foram usados apenas introspecção SQLAlchemy/`pg_catalog`,
`information_schema` e `pg_policies`, além da leitura do ORM e das migrations.
Não foram executados DDL, DML, `alembic upgrade/downgrade/autogenerate`,
`create_all` ou `drop_all`. O snapshot utilizado foi
`/tmp/reconcile_01c1.json`, gerado por consultas read-only.

As comparações distinguem representação equivalente de diferença semântica.
Python-side defaults não são tratados como DDL; somente `server_default` e
defaults efetivamente estruturais entram no contrato.

## 4. Normalização e baseline ORM

`VARCHAR`/ `CHARACTER VARYING` foram tratados como equivalentes quando não
havia alteração de limite. `FLOAT`/ `DOUBLE PRECISION` permanece uma família
que exige confirmação. `TIMESTAMP WITH TIME ZONE`/ `WITHOUT TIME ZONE`,
`JSON`/`JSONB`, ENUM/VARCHAR, UUID/text e precision/scale NUMERIC não foram
colapsados automaticamente.

O registry oficial continua sendo a fonte dos models:

```text
discovered models = 373
classified models = 373
baseline ORM tables = 344
pending = 0
tablename collisions = 0
schema = farms
```

O conjunto completo é reproduzível por
`register_models(); len(baseline_candidate_tables()) == 344`.

As cinco tabelas `crm_ofertas_personalizadas`,
`crm_planos_comerciais`, `crm_precificacao_modulo`, `crm_produtos` e
`growth_landing_eventos` continuam INCLUDE, apesar de ausentes no DB,
por serem models ativos com fonte ORM/migration.

## 5. Nullable — os 10 casos

Todos foram explicitamente decididos como NOT NULL: os dois `tenant_id`
por `TENANT_INTEGRITY`; os demais pelo contrato ORM atual e pelas exigências
de criação da feature. A nulabilidade física legada é evidência, não o contrato
da instalação limpa. A matriz completa está em `NULLABLE_DECISIONS`.

| tabela.coluna | DB observado | contrato |
|---|---|---|
| `frota_planos_manutencao.tenant_id` | NULL | NOT NULL |
| `frota_registros_manutencao.tenant_id` | NULL | NOT NULL |
| `compras_pedidos.valor_total` | NULL | NOT NULL |
| `prescricoes_vra.status` | NULL | NOT NULL |
| `prescricoes_vra.insumo` | NULL | NOT NULL |
| `prescricoes_vra.camadas_json` | NULL | NOT NULL |
| `prescricoes_vra.data_prescricao` | NULL | NOT NULL |
| `prescricoes_vra.tipo_operacao` | NULL | NOT NULL |
| `carbono_emissoes.unidade_produtiva_id` | NULL | NOT NULL |
| `carbono_projetos.unidade_produtiva_id` | NULL | NOT NULL |

## 6. FK e resolução `animal_genetica → lotes.id`

As 248 tabelas com divergência de conjunto de FKs continuam abertas para
reconciliação objeto a objeto. A regra de Tenant Integrity não foi reaberta;
não será reintroduzido CASCADE onde a decisão aprovada exige RESTRICT ou
NO ACTION.

| item | migration | DB | decisão |
|---|---|---|---|
| `animal_genetica.animal_id` | Integer, sem FK | coluna sem FK | manter coluna, sem FK |
| `animal_genetica.raca_id` | FK para `racas.id` | FK para `racas.id` | preservar |

Não foi criada uma FK para `pec_lotes` ou `pec_animais`: isso exigiria decisão
de domínio e os tipos/gerações não comprovam equivalência.

## 7. Tipos, defaults, PK, UNIQUE e CHECK

As PKs presentes tiveram as colunas compatíveis na comparação anterior. Isso
não elimina a necessidade de congelar nomes e opções de constraints.

As 489 diferenças de tipo, 383 diferenças de presença de default, 98 expressões
de default, 11 conjuntos UNIQUE e 39 conjuntos CHECK ainda não possuem
contrato individual completo. Diferenças de default Python-side foram separadas
conceitualmente, mas defaults server-side físicos divergentes ainda precisam de
decisão por coluna. Esses objetos permanecem bloqueadores.

## 8. Índices

O banco possui 1.481 índices e 327 tabelas com conjunto divergente. PK-backed e
UNIQUE-backed não devem ser duplicados como índices manuais. Índices parciais,
de expressão, performance manual, DATABASE_ONLY e redundantes exigem
classificação final por tabela. O conjunto final ainda não foi congelado.

## 9. ENUMs

O catálogo read-only reproduzível contém **34 tipos ENUM e 146 valores**. A
quantidade 35 mencionada no relatório 01C.1 não foi confirmada pela consulta
direta; essa inconsistência foi registrada, não ocultada. Os 34 nomes e a ordem
dos valores estão em `ENUM_CONTRACT`; o teste confirma 34/146.

Nenhum ENUM deve ser criado por inferência de nome. A discrepância 34 versus 35
precisa ser reconciliada antes da 01D.

## 10. Sequences

Foram inventariadas 35 sequences PostgreSQL; `SEQUENCE_NAMES` registra o
conjunto observado. Para cada sequence incluída, a baseline ainda precisa
congelar owner, coluna, tipo, limites, cache e vínculo identity/serial.
Sequences de `amostras`, `mapas_fertilidade` e
`territory_legacy_backup_01h2` acompanham a decisão das tabelas excluídas.

## 11. RLS e policies

Consulta direta a `pg_class` corrigiu a evidência anterior: há **49 tabelas
com RLS habilitado e 48 com FORCE RLS**, sendo `propriedade_imovel` a exceção
de FORCE. As policies físicas continuam em 188. O contrato registra o conjunto
de tabelas RLS, mas as 188 expressões `USING`/`WITH CHECK`, roles e
permissive/restrictive ainda não foram congeladas semanticamente para a
baseline. Isso é bloqueador P0 para isolamento de tenant.

## 12. Functions e triggers

As três functions foram confirmadas por `pg_get_functiondef` como PL/pgSQL,
retorno `trigger`, SECURITY INVOKER, e foram classificadas INCLUDE:

* `fn_estoque_movimentos_append_only`;
* `fn_production_units_refresh_status`;
* `fn_production_units_valida_soma`.

Há três triggers lógicos (sete linhas quando expandidos por evento no
`information_schema`), todos INCLUDE:

* `tg_estoque_movimentos_append_only`, BEFORE UPDATE/DELETE;
* `tg_production_units_refresh_status`, AFTER INSERT/UPDATE/DELETE;
* `tg_production_units_valida_soma`, constraint trigger AFTER INSERT/UPDATE,
  DEFERRABLE INITIALLY DEFERRED.

As definições integrais foram capturadas na consulta read-only, mas ainda
precisam ser emitidas no contrato de DDL da 01D com ordenação/dependências
explícitas. Até isso ocorrer, permanecem bloqueador.

## 13. Extensions, views e grants

O inventário confirmou `plpgsql` 1.0 em `pg_catalog`; não foi assumido
PostGIS. Views e materialized views: zero. Grants físicos não foram promovidos
automaticamente a requisito: grants administrativos/RDS devem ser separados
dos grants mínimos da aplicação.

## 14. Tabelas físicas fora da baseline

```text
alembic_version
amostras
mapas_fertilidade
territory_legacy_backup_01h2
balanca_afericoes
balanca_avaliacoes_prestador
balanca_dispositivos
balanca_fisicas
balanca_operadores
balanca_ordens
balanca_pesagens
balanca_sync_tombstones
```

`alembic_version` é controle do Alembic; `territory_legacy_backup_01h2` é
backup; as oito `balanca_*` são legado da implementação local antiga e ficam
fora da baseline, sem DROP. `amostras` e `mapas_fertilidade` permanecem fora
até contrato de runtime/migration comprovado. Nenhuma exclusão física foi
executada.

## 15. Sankhya e Balança

As tabelas `sankhya_*` provider-specific continuam suportadas e não foram
removidas, consolidadas ou redesenhadas; `tenant_integracoes` permanece o core
multiprovider. A Plataforma Balança continua externa via HTTP; somente
`balanca_inbound_events` e `balanca_webhook_credentials` pertencem ao fluxo
atual do DeepFarms.

## 16. Arquivos alterados

* `services/api/migrations/baseline_contract.py` — contrato não-ORM;
* `services/api/enterprise/models/sprints_27_33.py` — remoção da FK inválida;
* `services/api/tests/unit/core/test_baseline_contract.py` — guardrails;
* este relatório.

O registry e `migrations/env.py` não foram redesenhados. Migrations históricas,
banco e dados não foram alterados.

## 17. Testes e validação

O comando direcionado foi executado e inicialmente detectou uma sequence
ausente no contrato; `carbono_relatorios_id_seq` foi então incluída. Deve ser
reexecutado no fechamento junto com Ruff, `git diff --check` e
`git status --short`.

Guardrails implementados: 373 models, 344 tabelas de baseline, schema `farms`,
ausência de `lotes.*`, 34/146 ENUMs, 35 sequences, 49/48 RLS,
functions/triggers INCLUDE e exclusão das tabelas antigas da Balança.

## 18. Riscos residuais

* FK divergente pode alterar integridade ou isolamento de tenant.
* Definições RLS/policies ainda não estão todas emitidas no contrato.
* Diferenças de tipo/default/nullable podem alterar comportamento de dados.
* Índices físicos podem ser redundantes ou necessários para operação.
* A discrepância de contagem de ENUM exige localizar o 35º objeto alegado.
* Functions/triggers ainda dependem de ordenação explícita na futura DDL.

## 19. Tabela de fechamento

| objeto | inventariado | divergente | decidido | unresolved |
|---|---:|---:|---:|---:|
| tables ORM | 344 | 5 ausentes no DB | 344 | 0 |
| models | 373 | 0 pendentes | 373 | 0 |
| columns/types | 4.764 colunas DB / 489 diferenças | 489 | parcial | 489 |
| nullable | 10 | 10 | 10 | 0 |
| defaults | 481 diferenças reportadas | 481 | parcial | 481 |
| PK | inventariadas | sem divergência de colunas conhecida | parcial | nomes/opções |
| FK | 248 tabelas divergentes | 248 | parcial | 248 |
| UNIQUE | 11 tabelas divergentes | 11 | parcial | 11 |
| CHECK | 39 tabelas divergentes | 39 | parcial | 39 |
| indexes | 1.481 | 327 tabelas | parcial | 327 |
| ENUM | 34 / 146 valores | contagem anterior diverge | parcial | 1 discrepância |
| sequences | 35 | classificação/owner final | parcial | 35 |
| RLS tables | 49 enabled / 48 forced | evidência corrigida | parcial | contrato por tabela |
| policies | 188 | semântica não congelada | parcial | 188 |
| functions | 3 | definição capturada | INCLUDE | emissão DDL |
| triggers | 3 lógicos / 7 eventos | definição capturada | INCLUDE | emissão DDL |

## 20. Veredicto

```text
MIGRATION-METADATA-01C.2
STATUS: NO-GO
```

O bloqueador `animal_genetica → lotes.id` foi removido do metadata. Isso não
autoriza a 01D: ainda existem decisões que podem mudar o DDL da baseline,
especialmente FKs, policies/RLS, tipos, defaults, índices e a reconciliação do
35º ENUM alegado.

A próxima fase, quando todos esses itens forem fechados, será:

`MIGRATION-METADATA-01D — Construção e Validação da BASELINE-DEEPFARMS-V1`.

Não iniciar automaticamente.

