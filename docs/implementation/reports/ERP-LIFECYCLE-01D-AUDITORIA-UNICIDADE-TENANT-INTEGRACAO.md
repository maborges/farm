# Relatório de Execução: ERP-LIFECYCLE-01D — Auditoria de Unicidade Física e Concorrência de TenantIntegracao

**Fase:** ERP-LIFECYCLE-01D
**Data:** 2026-07-12
**Banco consultado:** `farms`
**Revisão Alembic do banco consultado:** `f1dfe22c7fa5`
**Veredicto:** `GO`

## 1. Resumo executivo
O domínio de integrações já trata `TenantIntegracao` como registro canônico atual por tenant/provider/escopo, não como histórico append-only. A auditoria confirmou:

- o modelo possui `tenant_id`, `integracao_id`/`provider_id`, `scope_type`, `scope_id`, `status`, `lifecycle_state`, `deleted_at` e timestamps;
- a criação canônica atual é idempotente no fluxo sequencial;
- o banco consultado não possui duplicidades em `tenant_integracoes`;
- o banco consultado tem RLS habilitado e forçado;
- a tabela consultada não possui constraint única física além da PK;
- o código atual escreve e lê apenas escopo `TENANT` para `TenantIntegracao`, embora o contrato já aceite `ESTABELECIMENTO` no runtime/readiness.

Conclusão: a chave natural recomendada é clara e a próxima fase deve ser uma migration de unicidade com tratamento concorrente, sem saneamento prévio.

## 2. Problema
O ponto aberto é a ausência de unicidade física em `farms.tenant_integracoes`, o que deixa uma janela residual de corrida concorrente na criação do primeiro registro canônico.

O problema a resolver é separar:

- unicidade do mesmo provider no mesmo escopo;
- exclusividade operacional de um ERP ativo por escopo;
- preservação de histórico de provider em linhas diferentes, se o produto decidir suportar troca futura.

## 3. Model
Arquivo principal:
- [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py)

Campos de `TenantIntegracao`:

- `id`: PK física, `Integer`
- `tenant_id`: `String(50)`, `nullable=False`, indexado
- `integracao_id`: FK para `marketplace_integracoes.id`, `nullable=False`
- `provider_id`: sinônimo ORM de `integracao_id`
- `status`: `String(50)`, default `"ativa"`
- `configuracoes`: `JSON`, default `{}` no model
- `credenciais`: `JSON`
- `webhook_url`: `String(500)`
- `webhook_secret`: `String(200)`
- `ultima_sincronizacao`: `DateTime`
- `total_sincronizacoes`: `Integer`, default `0`
- `installed_at`: `DateTime`, default `datetime.utcnow`
- `updated_at`: `DateTime`, default `datetime.utcnow`, `onupdate=datetime.utcnow`
- `scope_type`: `String(30)`, `nullable=False`, default `TENANT`
- `scope_id`: `String(50)`, `nullable=True`
- `lifecycle_state`: `String(30)`, `nullable=False`, default `CONFIGURED`
- `connection_payload`: `JSON`
- `credential_ref_id`: FK para `integration_credentials.id`, `nullable=True`
- `deleted_at`: `DateTime`

Não existe coluna `version` em `TenantIntegracao`. Versionamento vive em `integration_versions` e `integration_credentials.version_number`.

## 4. Migrations
Arquivos relevantes:
- [services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py)
- [services/api/migrations/versions/20260701_integrations_domain_03b_operations.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260701_integrations_domain_03b_operations.py)
- [services/api/migrations/versions/23b548507313_add_vento_kmh_to_registro_clima.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/23b548507313_add_vento_kmh_to_registro_clima.py)

O que a foundation define:

- `scope_type` com `CHECK` em `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`
- `lifecycle_state` com `CHECK` em `NOT_CONFIGURED`, `CONFIGURED`, `VALIDATING`, `VALID`, `INVALID`, `ACTIVE`, `SYNCING`, `PARTIALLY_DEGRADED`, `DEGRADED`, `SUSPENDED`, `DISABLED`, `REVOKED`, `REMOVED`
- FK de `integracao_id` para `marketplace_integracoes.id`
- FK de `credential_ref_id` para `integration_credentials.id`
- índices lógicos no código para `id`, `tenant_id`, `scope`, `lifecycle_state`, `credential_ref_id`

O que a operação define:

- `integration_features` com `UNIQUE(config_id, codigo)`
- `integration_sync_policies` com `UNIQUE(feature_id)`
- `integration_health_snapshots` com `UNIQUE(config_id)`

Observação do banco consultado:
- na revisão ativa consultada, o catálogo físico de `tenant_integracoes` expõe apenas a PK e os índices `id` e `tenant_id`; os índices auxiliares esperados para `scope`, `lifecycle_state` e `credential_ref_id` não apareceram no `pg_indexes` do ambiente consultado.

## 5. Índices
Índices observados no banco consultado:

- `tenant_integracoes_pkey` em `(id)` e único
- `ix_tenant_integracoes_id` em `(id)`
- `ix_tenant_integracoes_tenant_id` em `(tenant_id)`

Índices definidos no código/migrations, mas não visíveis no banco consultado:

- `ix_tenant_integracoes_scope`
- `ix_tenant_integracoes_lifecycle_state`
- `ix_tenant_integracoes_credential_ref_id`

## 6. Constraints
Constraints físicas relevantes no banco consultado:

- PK `tenant_integracoes_pkey`
- FK `tenant_integracoes_integracao_id_fkey`
- FK `fk_tenant_integracoes_credential_ref_id`
- `ck_tenant_integracoes_scope_type`
- `ck_tenant_integracoes_lifecycle_state`

Não existe `UNIQUE` físico em `tenant_integracoes` além da PK.

### RLS
O banco consultado tem RLS habilitado e forçado:

- `relrowsecurity = true`
- `relforcerowsecurity = true`

Policies em `farms.tenant_integracoes`:

- `farms_tenant_integracoes_select_tenant`
- `farms_tenant_integracoes_insert_tenant`
- `farms_tenant_integracoes_update_tenant`
- `farms_tenant_integracoes_delete_tenant`

## 7. Escopos
O enum oficial de escopo é:

- `PLATFORM`
- `TENANT`
- `ESTABELECIMENTO`
- `USUARIO`

Arquiteturalmente, o ERP não deve usar `UNIDADE_PRODUTIVA` como escopo de configuração.

Situação atual:

- o writer canônico de `TenantIntegracao` usa `scope_type = TENANT`
- o readiness/runtime aceita `TENANT` e `ESTABELECIMENTO`
- não há fluxo de escrita para `ESTABELECIMENTO` em `TenantIntegracao` nesta base
- não existe FK física para estabelecimento; `scope_id` é string livre

## 8. Chave natural candidata
Recomendação de chave natural funcional:

- `tenant_id`
- `integracao_id`
- `scope_type`
- `scope_id` normalizado por escopo

Interpretação prática:

- para `TENANT`, a identidade natural é `(tenant_id, integracao_id)`
- para `ESTABELECIMENTO`, a identidade natural é `(tenant_id, integracao_id, scope_id)`

Motivo:

- o provider faz parte da identidade do registro
- o escopo faz parte da identidade operacional
- o `scope_id` distingue filial/estabelecimento quando o escopo não é global ao tenant

## 9. Alternativas avaliadas

### Alternativa A
`UNIQUE(tenant_id, marketplace_integracao_id)`

Problema:

- impediria mais de um provider por tenant mesmo quando o produto precisar preservar histórico de troca
- não distingue escopo
- é forte demais para o modelo atual

### Alternativa B
`UNIQUE(tenant_id, marketplace_integracao_id, scope_type, scope_id)`

Problema:

- no PostgreSQL, `NULL` em `scope_id` permitiria múltiplas linhas com a mesma combinação para `TENANT`
- precisaria de normalização adicional

### Alternativa C
Índices parciais por escopo

Recomendação:

- mais legível
- evita ambiguidade de `NULL`
- representa bem `TENANT` e `ESTABELECIMENTO`

### Alternativa D
`UNIQUE(..., COALESCE(scope_id, sentinela))`

Problema:

- legibilidade pior
- aumenta acoplamento a valor sentinela
- menos natural para manutenção e revisão

### Alternativa E
Unicidade apenas para registros ativos

Problema:

- conflita com o fato de `lifecycle_state` ser estado operacional, não identidade
- `status = inativa` deve continuar ocupando a mesma identidade do registro

## 10. Semântica de nulos
`scope_id` é `nullable` no model e na migration.

Tratamento recomendado:

- `TENANT`: `scope_id` permanece `NULL`
- `ESTABELECIMENTO`: `scope_id` deve ser preenchido
- `UNIQUE` não deve depender de igualdade direta com `NULL`

Recomendação física:

- usar índices únicos parciais por escopo, em vez de uma única constraint com `scope_id` nulo

## 11. Integração inativa
Interpretação funcional atual:

- `status = inativa` e `lifecycle_state = DISABLED` são estados do mesmo registro, não novas identidades
- o adapter atual reusa o mesmo `TenantIntegracao`
- a inatividade não deve abrir espaço para duplicidade do mesmo provider/escopo

Resposta objetiva:

1. Sim, uma integração inativa deve continuar bloqueando nova linha do mesmo provider/escopo enquanto não for deletada.
2. Sim, a reativação deve reutilizar a mesma linha.
3. Não, a coexistência de linha ativa e inativa do mesmo provider/escopo não é um estado desejável.
4. O adapter atual não resolve ambiguidade entre duas linhas equivalentes porque assume uma linha canônica.
5. O status ERP deve refletir a linha canônica do tenant/provider/escopo, não uma duplicata.
6. O histórico deve permanecer em jobs, versions, credentials, health e timeline, não por duplicação de `TenantIntegracao`.

## 12. Múltiplos providers
O domínio permite mais de um provider no catálogo e pode preservar providers antigos em linhas separadas ao longo do tempo, mas o estado operacional corrente não deve ter dois ERPs administrativos ativos no mesmo escopo.

Leitura do código:

- o readiness resolve um runtime por tenant usando provider ERP ativo/recente
- o canonical adapter de Sankhya procura `TenantIntegracao` por `tenant_id + integracao_id + scope_type + deleted_at is null`
- não existe hoje uma política física que permita duas integrações canônicas simultâneas e seguras para o mesmo escopo

Recomendação:

- unicidade física por provider+escopo
- exclusividade de ERP ativo por escopo como regra operacional complementar, não como chave física

## 13. Exclusividade de ERP ativo
O produto não deve acabar com dois ERPs administrativos ativos no mesmo escopo.

Contudo, isso é diferente de unicidade do mesmo provider:

- unicidade do mesmo provider evita duplicidade acidental
- exclusividade de ERP ativo evita dois ERPs concorrentes no mesmo escopo

Para esta fase:

- a unicidade física deve ficar em provider+escopo
- a exclusividade de um único ERP ativo por tenant/estabelecimento deve ser tratada por regra operacional futura, se o swap virar produto

## 14. Troca futura
Se o tenant sair de Sankhya para outro ERP:

- o registro antigo pode ficar `DISABLED` ou `REMOVED`
- o novo provider deve ganhar outro registro
- o domínio deve continuar conseguindo identificar a linha canônica atual

Impacto sobre a constraint:

- não faz sentido uma chave natural apenas por tenant
- faz sentido uma chave por provider e escopo
- não faz sentido usar `lifecycle_state` na chave principal

## 15. Adapter
Arquivos principais:
- [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

Comportamento observado:

- `_ensure_config` usa `select(...).where(tenant_id, integracao_id, scope_type, deleted_at is None)` e `scalar_one_or_none()`
- se não achar linha, cria `TenantIntegracao`
- se achar, reaproveita a mesma linha e atualiza payloads/estado
- não existe `IntegrityError` handler para corrida concorrente
- não existe lock forte
- não existe upsert atômico

Conclusão:

- o adapter assume registro canônico único por provider/escopo
- a proteção concorrente ainda não é física

## 16. Concorrência
Sequência atual:

1. `SELECT` pelo registro canônico
2. ausência do registro
3. `INSERT`
4. `flush/commit`

Ponto de corrida:

- duas requisições concorrentes podem passar pelo `SELECT` antes do `INSERT`

Estratégia mínima recomendada para a próxima fase:

1. criar a unicidade física
2. tratar `IntegrityError`
3. reler o registro existente
4. manter o fluxo idempotente

Estratégias avaliadas:

- `UPSERT` PostgreSQL: possível, mas menos portável e mais acoplado ao dialect
- `SELECT FOR UPDATE`: protege, mas aumenta custo e complexidade
- advisory lock: resolve concorrência, mas complica operação

Recomendação:

- constraint física + tratamento de `IntegrityError`

## 17. Dados existentes
Consulta executada apenas em leitura no banco `farms`.

Resultados:

- total de linhas em `farms.tenant_integracoes`: `0`
- duplicidades por `(tenant_id, integracao_id, scope_type, scope_id)`: `0`
- duplicidades por `(tenant_id, integracao_id)`: `0`
- tenants com mais de uma linha ativa: `0`
- tenants com mais de uma linha ativa por provider: `0`
- tenants com mais de uma linha ativa por provider/escopo: `0`
- linhas `TENANT` com `scope_id IS NULL`: `0`
- linhas `ESTABELECIMENTO` com `scope_id IS NULL`: `0`
- `scope_type` inválido: `0`
- linhas ativas: `0`

Conclusão:

- não há duplicidades a sanar no banco consultado
- não há massa de dados para migração corretiva nesta fase

## 18. Duplicidades
Classificação:

- `NO_DUPLICATES`

## 19. Dependências
Tabelas que referenciam `farms.tenant_integracoes` por FK direta:

- `integration_versions.config_id`
- `integration_features.config_id`
- `integration_sync_policies.config_id`
- `integration_health_snapshots.config_id`
- `integration_jobs.config_id`
- `integration_external_record_links.config_id`

Tabelas correlatas sem FK direta, mas dependentes da integração:

- `integration_credentials`
- tabelas de Sankhya legada
- jobs, timelines e associações que usam `config_id`, `provider_id` e `feature_id`

## 20. Saneamento
Não necessário nesta execução.

Motivo:

- não existem duplicidades no banco consultado
- não há linhas ativas ou legadas a consolidar

## 21. PostgreSQL
Compatibilidade:

- a recomendação de unicidade deve ser implementada com `CREATE UNIQUE INDEX CONCURRENTLY` em uma migration futura
- a semântica de `NULL` do PostgreSQL torna menos atraente um `UNIQUE` único com `scope_id` nulo
- índices parciais são a forma mais clara para `TENANT` e `ESTABELECIMENTO`
- a PK e as FKs atuais são compatíveis com a estratégia proposta

## 22. SQLite
Compatibilidade:

- SQLite moderno suporta índices parciais
- a regra principal pode ser testada em SQLite em suites unitárias
- testes de concorrência e semantics de `NULL` devem ser considerados preferencialmente no PostgreSQL

Conclusão:

- a regra de produção não precisa ser rebaixada para acomodar SQLite

## 23. RLS
O banco consultado já aplica RLS corretamente em `tenant_integracoes`.

Isso significa:

- a unicidade proposta não substitui RLS
- a unicidade deve incluir `tenant_id`
- a revisão de unicidade não mistura tenants

## 24. Riscos
- ausência atual de índice único físico em `tenant_integracoes`
- ausência de handler concorrente no adapter
- `scope_id` livre sem FK para estabelecimento
- ausência de writer para `ESTABELECIMENTO`
- catálogo consultado sem massa de dados para validar migração em produção real
- índice físico ausente no ambiente consultado para `scope`, `lifecycle_state` e `credential_ref_id`

## 25. Achados classificados
- `NO_DUPLICATES`
- `CONCURRENT_INSERT_RISK`
- `SCOPE_MODEL_GAP`
- `MIGRATION_LOCK_RISK`
- `TEST_DIALECT_GAP`

## 26. Decisão recomendada
Recomendação objetiva:

- a chave natural física deve ser por `tenant_id + integracao_id + scope_type + scope_id_normalizado`
- na prática, o melhor desenho é via índices únicos parciais por escopo
- `lifecycle_state` não deve entrar na chave física
- `deleted_at` pode ser usado como filtro parcial se a política futura quiser permitir recriação após soft delete

Regra para `scope_id`:

- `TENANT`: `NULL` permitido
- `ESTABELECIMENTO`: obrigatório

Regra para inatividade:

- integração inativa continua bloqueando duplicidade do mesmo provider/escopo

Regra para múltiplos providers:

- mais de um provider pode existir no histórico da tabela
- mais de um provider ativo no mesmo escopo não deve ser suportado como estado normal

## 27. Estratégia de migration
Estratégia futura recomendada:

1. inventariar ambiente de produção
2. se houver duplicados, fazer saneamento manual controlado
3. criar índices únicos parciais com `CONCURRENTLY`
4. validar com testes de concorrência
5. só então endurecer o fluxo com tratamento de `IntegrityError`

Proposta de forma física:

- índice único parcial para `TENANT`
- índice único parcial para `ESTABELECIMENTO`

## 28. Estratégia de `IntegrityError`
Sequência recomendada:

1. tentar inserir
2. o banco rejeita duplicidade
3. fazer rollback
4. reler o registro canônico existente
5. continuar o fluxo idempotente

Isso evita depender apenas de `SELECT` prévio.

## 29. Plano incremental
Fases sugeridas:

- `ERP-LIFECYCLE-01D.2`: migration de unicidade física
- `ERP-LIFECYCLE-01D.3`: tratamento concorrente no adapter
- `ERP-LIFECYCLE-01D.4`: testes de concorrência e escopos

Não há necessidade de fase de saneamento nesta execução.

## 30. Testes futuros
Testes a priorizar na próxima fase:

- duplicidade por provider+escopo
- concorrência de `INSERT`
- reativação de integração inativa
- troca de provider com preservação de histórico
- `TENANT` vs `ESTABELECIMENTO`
- `NULL` de `scope_id`

Arquivos prováveis:

- [services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py)
- [services/api/tests/unit/integracoes/test_erp_readiness_service.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_readiness_service.py)
- [services/api/tests/unit/integracoes/test_integrations_foundation_models.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_integrations_foundation_models.py)
- [services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py)

## 31. Impacto no piloto
Impacto operacional esperado:

- nenhum impacto imediato no piloto atual
- nenhuma mudança de fluxo foi aplicada nesta fase
- o Console ERP e o adapter continuam com o mesmo comportamento sequencial

## 32. Veredicto
**GO**

Motivos:

- chave natural ficou clara
- não existem duplicidades no banco consultado
- a estratégia de migration é segura
- a concorrência futura ficou bem delimitada
- a regra física pode ser implementada sem redesenhar o domínio

## 33. Recomendação final
Próxima fase recomendada:

- `ERP-LIFECYCLE-01D.2` com migration de unicidade física baseada em índices parciais
- depois `ERP-LIFECYCLE-01D.3` com `IntegrityError` + reread

Nenhuma migration foi criada nesta execução.
