# DB-MIGRATION-FIX-01 — Auditoria e Correção da Divergência Alembic x Banco Físico

## Escopo auditado

- Migration [services/api/migrations/versions/20260703_ops_intelligence_02_recommendations_foundation.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260703_ops_intelligence_02_recommendations_foundation.py)
- Migration [services/api/migrations/versions/20260704_sankhya_gateway_auth.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260704_sankhya_gateway_auth.py)
- Migration-base Sankhya [services/api/migrations/versions/fase3_sankhya.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/fase3_sankhya.py)
- Estado físico do schema `farms`
- Estado lógico registrado em `farms.alembic_version`

## Diagnóstico inicial

### Estado Alembic

- `alembic heads`: `20260706_integrations_external_record_links_pending_local`
- `alembic current`: `23b548507313`
- `alembic upgrade head`: falhou em `23b548507313 -> 20260703_ops_intelligence_02_recommendations_foundation`
- erro: `DuplicateTableError: relation "recommendation_results" already exists`

### Conclusão inicial

O banco físico já continha objetos da migration `20260703_ops_intelligence_02_recommendations_foundation`, mas o Alembic ainda não considerava essa revisão aplicada.

Isso impedia avanço seguro porque:

- a migration tentava recriar objetos já existentes;
- havia dados nas tabelas;
- `stamp` direto seria arriscado sem comprovar compatibilidade física completa.

## Objetos esperados pela migration 20260703

### Tabelas

- `recommendation_results`
- `recommendation_lifecycle_events`

### Índices

- `ix_recommendation_results_tenant_status`
- `ix_recommendation_results_tenant_domain`
- `ix_recommendation_results_tenant_scope`
- `ix_recommendation_results_tenant_dedupe`
- `ix_recommendation_results_active_dedupe`
- `ix_recommendation_lifecycle_events_tenant_recommendation`

### Constraints relevantes

- checks em `recommendation_results`:
  - `ck_recommendation_results_domain`
  - `ck_recommendation_results_status`
  - `ck_recommendation_results_priority`
  - `ck_recommendation_results_source_type`
  - `ck_recommendation_results_action_type`
  - `ck_recommendation_results_confidence_range`
- checks em `recommendation_lifecycle_events`:
  - `ck_recommendation_lifecycle_action_type`
  - `ck_recommendation_lifecycle_previous_status`
  - `ck_recommendation_lifecycle_new_status`
- FKs:
  - `tenant_id -> tenants.id`
  - `unidade_produtiva_id -> unidades_produtivas.id`
  - `superseded_by_id -> recommendation_results.id`
  - `performed_by -> usuarios.id`

### Segurança

- `ENABLE ROW LEVEL SECURITY`
- `FORCE ROW LEVEL SECURITY`
- 4 policies por tabela, baseadas em `app.current_tenant_id`

## Estado físico encontrado antes da correção

### Objetos já existentes

- tabelas `recommendation_results` e `recommendation_lifecycle_events`
- PKs e FKs principais
- alguns índices básicos

### Objetos ausentes ou incompatíveis

- checks da migration não existiam
- RLS não estava habilitado
- policies não existiam
- índices compostos e índice parcial único não existiam
- colunas JSON estavam em `json`, enquanto a migration esperava `jsonb`
- defaults de `created_at` e `updated_at` não estavam alinhados ao esperado

### Dados existentes

- `recommendation_results`: 221 registros
- `recommendation_lifecycle_events`: 354 registros

## Validação de compatibilidade dos dados

Foi auditado o conteúdo das tabelas antes de qualquer correção:

- domínios, status, prioridades, `source_type`, `action_type` e transições de lifecycle estavam compatíveis com os checks da migration;
- não foram encontrados conflitos com o índice parcial único de deduplicação ativa;
- não foi identificado risco imediato de perda de dados para convergência da estrutura.

## Estratégia escolhida

Foi adotada a alternativa mais segura:

1. convergir fisicamente os objetos faltantes no banco;
2. validar compatibilidade;
3. somente então executar `alembic stamp 20260703_ops_intelligence_02_recommendations_foundation`.

Essa abordagem foi preferida a:

- editar retroativamente a migration antiga de forma arriscada;
- usar `stamp head` sem comprovação física intermediária;
- recriar tabelas com dados já existentes.

## Correção aplicada

### Ajustes físicos executados no banco

- conversão para `jsonb`:
  - `recommendation_results.source_signal_ids`
  - `recommendation_results.context`
  - `recommendation_lifecycle_events.payload`
- criação dos índices faltantes da migration
- criação dos check constraints faltantes
- habilitação de `RLS` e `FORCE RLS` nas duas tabelas
- criação das 8 policies esperadas
- alinhamento de defaults de datas

### O que não foi feito

- nenhum dado foi apagado;
- nenhuma tabela foi dropada;
- nenhuma migration antiga foi alterada para forçar execução idempotente;
- nenhuma migration nova do domínio de associação externa foi tocada.

## Resultado após a convergência da migration 20260703

### Estado validado

- `alembic current`: `20260703_ops_intelligence_02_recommendations_foundation`
- `farms.alembic_version`: `20260703_ops_intelligence_02_recommendations_foundation`
- estruturas de `recommendation_results` e `recommendation_lifecycle_events` ficaram compatíveis com a migration auditada

### Conclusão

A divergência original de `recommendation_results` foi corrigida com segurança.

## Novo bloqueio encontrado ao seguir para o próximo passo

Após resolver a divergência anterior, `alembic upgrade head` avançou além de `20260703` e falhou na migration seguinte:

- revisão: `20260704_sankhya_gateway_auth`
- erro: `UndefinedTableError: relation "sankhya_config" does not exist`

### Causa provável

A migration [services/api/migrations/versions/20260704_sankhya_gateway_auth.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260704_sankhya_gateway_auth.py) altera a tabela `sankhya_config`, mas essa tabela-base deveria ter sido criada antes por [services/api/migrations/versions/fase3_sankhya.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/fase3_sankhya.py).

No banco físico auditado:

- `sankhya_config` não existe;
- portanto, existe uma segunda divergência histórica, distinta da primeira.

## Risco

### Risco mitigado

- a divergência de `recommendation_results` não representa mais bloqueio.

### Risco ainda aberto

- o histórico Alembic e o banco físico ainda não estão totalmente convergidos por causa do bloco Sankhya;
- qualquer `stamp` acima de `20260703` seria incorreto sem auditar primeiro a base física de `fase3_sankhya`.

## Recomendação objetiva

1. considerar `20260703_ops_intelligence_02_recommendations_foundation` como convergida e regularizada;
2. abrir uma segunda auditoria/correção específica para a cadeia Sankhya:
   - confirmar se `fase3_sankhya` nunca foi aplicada fisicamente;
   - verificar se existem outras tabelas `sankhya_*` ausentes ou parcialmente criadas;
   - decidir entre criar migration de convergência ou reconstruir a base física faltante de forma segura;
3. somente depois retomar `alembic upgrade head`.

## Arquivos alterados

Nenhuma migration do repositório foi alterada como parte da correção final.

Foi criado apenas este relatório:

- [docs/implementation/reports/DB-MIGRATION-FIX-01-ALEMBIC-RECOMMENDATIONS-CONVERGENCIA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/DB-MIGRATION-FIX-01-ALEMBIC-RECOMMENDATIONS-CONVERGENCIA.md)

## Comandos de validação executados

```bash
cd services/api
.venv/bin/python -m alembic heads
.venv/bin/python -m alembic current
.venv/bin/python -m alembic stamp 20260703_ops_intelligence_02_recommendations_foundation
.venv/bin/python -m alembic upgrade head
```

## Status final desta entrega

- divergência original corrigida: `sim`
- perda de dados: `não`
- drop de objetos existentes: `não`
- `upgrade head` até o head final: `não concluído`
- motivo do bloqueio remanescente: ausência física de `sankhya_config` antes da migration `20260704_sankhya_gateway_auth`
