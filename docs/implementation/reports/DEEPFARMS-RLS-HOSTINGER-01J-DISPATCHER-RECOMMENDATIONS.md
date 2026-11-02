# DEEPFARMS-RLS-HOSTINGER-01J — Dispatcher e Scheduler de Recomendações sob RLS

**Data:** 2026-10-31  
**Veredicto:** **NO-GO — implementação interrompida antes de alterar o scheduler**  
**Motivo:** as tabelas reais e a identidade dispatcher não existem no laboratório; executar o ciclo produtivo exigiria ampliar significativamente o schema de teste.

## 1. Resumo

Foi concluída a inspeção do caminho de recomendações e uma verificação somente leitura do `deepfarms_rls_lab` como `deepfarms_rls_lab_runtime`. O banco contém apenas `rls_probe`, `rls_probe_parent`, `rls_probe_child` e `rls_probe_catalog`; não contém `tenants`, `recommendation_results`, `recommendation_lifecycle_events`, `admin_audit_log` ou tabelas de domínio usadas pelos providers. As únicas roles do laboratório são `deepfarms_rls_lab_owner`, `deepfarms_rls_lab_deploy` e `deepfarms_rls_lab_runtime`; não há dispatcher.

O scheduler padrão carrega nove providers de recomendações. Além da descoberta de Tenants, o ciclo faz expiry de recomendações e executa consultas específicas dos providers. Testar o comportamento real sob runtime restrito, inclusive dry-run, exige tabelas e policies reais ou uma réplica considerável dessas dependências. A restrição da tarefa determina interromper essa parte, sem ampliar automaticamente o laboratório.

Por isso, **nenhum código funcional, role, grant, policy, tabela ou fixture foi alterado/criado**. Os testes obrigatórios de execução do scheduler não foram executados. Não se declara isolamento do scheduler aprovado. É necessária decisão/autorização específica para uma alternativa mínima de laboratório antes de retomar.

## 2. Contrato de privilégios identificado

### Dispatcher

O método atual `_list_active_tenant_ids()` executa:

```sql
SELECT tenants.id
FROM tenants
WHERE tenants.ativo IS TRUE
```

O ORM seleciona somente `Tenant.id`; `Tenant.ativo` é usado no predicado. Não há evidência no método de necessidade de buscar nome, plano ou outros atributos. O grant candidato é, portanto, somente `SELECT (id, ativo)` em `farms.tenants`, com policy restrita a Tenants elegíveis se a semântica de elegibilidade precisar de RLS por linha. A query de catálogo não deve se transformar em uma leitura global do ORM completo.

O lock existente é obtido via `SELECT pg_try_advisory_lock(:lock_id)` e liberado via `SELECT pg_advisory_unlock(:lock_id)`. Não precisa de tabela de negócio. Na sessão runtime usada nesta inspeção, ambas as funções retornaram sucesso em aquisição e liberação no mesmo backend. Isso comprova disponibilidade da chamada isolada, mas **não** comprova exclusão mútua entre dois ciclos concorrentes.

O dispatcher não deve receber grants em tabelas de recomendações, tenants privados, dados dos providers, audit logs, payloads ou credenciais. Não há necessidade identificada de sequence.

### Runtime Tenant

O ciclo `_run_tenant_cycle(tenant_id)` usa uma `AsyncSession` própria para cada Tenant. Antes do serviço, chama expiry (quando `dry_run=False`) e depois `RecommendationSchedulerService.run_scheduled_recommendations(...)`.

Dependências diretamente identificadas no código:

| Operação | Objeto/caminho SQL identificado | Acesso mínimo esperado |
|---|---|---|
| Expiração | `recommendation_results`: busca IDs por `tenant_id`, status ativo e `expires_at`; em seguida carrega/atualiza a recomendação. | Runtime Tenant: SELECT, UPDATE sob policy tenant. |
| Eventos de lifecycle | `recommendation_lifecycle_events`: `_create_lifecycle_event()` insere eventos associados à recomendação. | Runtime Tenant: INSERT sob policy tenant. A FK do evento à recomendação deve ser preservada. |
| Auditoria | `write_audit_log()` grava `TenantAuditLog` (`tenant_audit_log`) na mesma sessão ao criar/alterar resultado no lifecycle. | Runtime Tenant: INSERT tenant-scoped na mesma transação quando o caminho é acionado; confirmar policy e constraints antes de conceder. |
| Providers padrão | Registro global em `recommendations/__init__.py` registra Clima, Agricultura, Financeiro, Pecuária, Estoque, Frota, ESG, Wizard e Campo. Cada provider consulta fontes de domínio distintas. | Grants/RLS por tabela efetivamente tocada pelo provider selecionado, todos no contexto daquele Tenant. Não há allowlist única pequena para `domain=None`. |
| Lock e descoberta | Advisory lock + `tenants(id, ativo)`. | Operação do dispatcher; nenhuma leitura tenant-private. |

Não foram geradas queries de execução real ou SQL logging de scheduler, pois isso exigiria as tabelas inexistentes. A lista de dependências acima é derivada de inspeção estática; a query precisa por provider e as colunas de todos os modelos devem ser capturadas numa execução autorizada futura antes de fechar grants. Os IDs das recomendações e eventos são UUIDs gerados pela aplicação nos modelos inspecionados; não foi identificada necessidade de sequence para esse fluxo.

## 3. Estado real do laboratório e roles

Conexão somente leitura confirmada:

| Campo | Resultado |
|---|---|
| Database | `deepfarms_rls_lab` |
| PostgreSQL | `16.15` |
| `current_user` / `session_user` | `deepfarms_rls_lab_runtime` / `deepfarms_rls_lab_runtime` |
| `farms` | USAGE disponível; CREATE negado para runtime |
| Roles lab visíveis | `deepfarms_rls_lab_owner` (NOLOGIN), `deepfarms_rls_lab_deploy` e `deepfarms_rls_lab_runtime` |
| Atributos runtime/deploy/owner | Nenhuma das três é SUPERUSER, BYPASSRLS, CREATEDB ou CREATEROLE |
| Membership | `deepfarms_rls_lab_deploy` é membro de `deepfarms_rls_lab_owner`; runtime não tem membership |
| Role dispatcher | Ausente |
| Objetos em `farms` | `rls_probe`, `rls_probe_parent`, `rls_probe_child`, `rls_probe_catalog` e sequences dessas fixtures; todos os quatro probes têm RLS e FORCE RLS |
| Objetos necessários ao scheduler | `tenants`, `recommendation_results`, `recommendation_lifecycle_events`, `tenant_audit_log`, `unidades_produtivas`, `safras` e `recommendation_rules`: ausentes |

O catálogo de policies mostrou apenas policies das quatro fixtures sintéticas da 01E2, todas destinadas a `deepfarms_rls_lab_runtime`. Não há policy real para Tenants ou recomendações. A role deploy não tem CREATEROLE; não se tentou criar outra role ou usar uma identidade elevada.

## 4. Evidência de extensão das dependências

`recommendations/__init__.py` chama `register_default_recommendation_providers()` e registra nove providers. O ciclo padrão recebe `domain=None`, portanto `_resolve_provider_classes()` seleciona providers de todos os domínios disponíveis. `RecommendationSchedulerService` chama o runner de cada provider; `dry_run=True` evita a expiração e o commit final do ciclo, mas **não elimina as consultas dos providers**. Portanto dry-run não contorna a ausência das tabelas.

Mesmo restringindo a seleção a um domínio, o fluxo real ainda necessita:

1. `farms.tenants` real (ou fixture estruturalmente fiel) para discovery.
2. `recommendation_results` e `recommendation_lifecycle_events` para expiry/lifecycle quando há recomendações vencidas.
3. Dependências de audit log para alterações do lifecycle.
4. Tabelas de negócio consultadas pelo provider selecionado, com FKs/constraints, grants, RLS/FORCE e dados sintéticos coerentes.
5. Policies e grants por cada uma dessas tabelas, sem bypass/ownership para runtime.

Isso excede as fixtures probes atuais e não pode ser coberto apenas concedendo acesso a `rls_probe`. Não foi estimada a quantidade total de objetos de cada provider, pois não houve execução SQL real e fazê-lo demandaria montar o schema ou instrumentar o ORM; o escopo atual basta para confirmar o bloqueio estrutural.

## 5. Matriz dos testes obrigatórios

| Teste solicitado | Estado | Evidência/razão |
|---|---|---|
| Dispatcher lista somente Tenants elegíveis | **NÃO EXECUTADO** | Role `deepfarms_rls_lab_dispatcher` e tabela `farms.tenants` não existem. |
| Dispatcher não acessa dados privados | **NÃO COMPROVADO** | Não há identidade dispatcher nem tabelas de negócio reais contra as quais tentar SELECT; não se inferiu negação por ausência de objeto. |
| Runtime A não acessa B e runtime B não acessa A | **NÃO EXECUTADO NESTA ETAPA** | A 01E2 comprovou esse comportamento em probes sintéticas; não há policies/tabelas de recomendações reais no lab para repetir pelo scheduler. |
| Sessão sem contexto não revela dados privados | **NÃO EXECUTADO NESTA ETAPA** | Probes da 01E2 têm prova anterior, mas não equivalem às queries do scheduler/provider. |
| Commit e rollback reaplicam o contexto | **NÃO EXECUTADO NESTA ETAPA** | 01G/01H e harness 01E2 têm provas anteriores no mecanismo central; o scheduler real ainda usa GUC persistente nesta versão. |
| Erro SQL não contamina outra sessão | **NÃO EXECUTADO NESTA ETAPA** | Provas anteriores cobrem fixtures/harness, não ciclo real de recomendações sob dispatcher/runtime. |
| Reuso de pool não vaza Tenant | **NÃO EXECUTADO NESTA ETAPA** | Pool unitário foi comprovado em 01E2 e sessão 01H; não foi exercido pelo scheduler atualizado, que não foi modificado. |
| Advisory lock impede ciclos concorrentes | **PARCIAL** | `pg_try_advisory_lock` e `pg_advisory_unlock` funcionaram com runtime na mesma sessão. Duas sessões concorrentes não foram abertas; exclusão não comprovada nesta rodada. |
| Dry-run preserva o comportamento | **NÃO EXECUTADO** | Sem as tabelas e dependências dos providers, o dry-run do ciclo real não inicia. |
| Falha em um Tenant não compromete o próximo | **NÃO EXECUTADO** | Não há fixtures de negócio para executar ciclos A/B consecutivos. Unit mocks não foram considerados prova do runtime RLS. |
| Nenhuma permissão elevada é necessária | **PARCIAL** | A conexão runtime confirmou flags elevadas falsas e ausência de membership; dispatcher não foi criado, então seu contrato efetivo não foi testado. |

**Resultado consolidado:** nenhum teste de execução do scheduler real foi aprovado nesta tarefa. Evidências 01E2/01G/01H permanecem válidas apenas para seus cenários e não são reaproveitadas como PASS da integração de 01J.

## 6. Alterações, lock e regressões

- **Arquivos funcionais modificados:** nenhum.
- **Arquivo de teste criado/alterado:** nenhum.
- **Scheduler:** permanece como estava, incluindo `_list_active_tenant_ids()` usando o engine compartilhado e helpers `_set_tenant_context()` / `_clear_tenant_context()` com `set_config(..., false)` e `RESET`.
- **Advisory lock:** SQL existente é mantido sem alterações. A chamada de adquirir/liberar foi verificada com a identidade runtime; não foi verificado o bloqueio entre ciclos concorrentes.
- **Banco:** somente consultas de catálogo/identidade e chamadas temporárias de aquisição/liberação do advisory lock. Nenhuma DDL/DML, role, grant, policy ou fixture foi criada/alterada.
- **Outros componentes:** não foram modificados. Nenhum worker, provider, automação ou integração externa foi executado.
- **Regressões:** sem alterações funcionais, não há regressão de código introduzida por esta etapa. O comportamento atual segue incompatível com dispatcher e contexto transacional; isso é pendência, não regressão nova.
- **Testes de código:** não executados, pois a mudança funcional foi interrompida antes da edição. Nenhum teste de unidade foi tratado como substituto da prova de integração solicitada.

## 7. Alternativa mínima para retomar

Solicitar uma decisão/autorização específica antes de ampliar o laboratório. Há dois níveis possíveis:

### Opção A — Provar somente a fronteira dispatcher/runtime

Autorizar uma fixture **isolada e sintética**, fora de `farms` de negócio ou sob nomes `rls01j_*`, com duas linhas de Tenant (`id`, `ativo`), policy/grant dispatcher para apenas essas colunas e uma tabela-probe tenant-scoped. Fazer harness do caminho de orquestração com registry vazio/mockado, preservar o lock e verificar sessões A/B, erro, commit/rollback, pool e dry-run. Isso testa a separação de identidades/contexto, mas **não** prova os providers nem consultas reais de recomendações.

### Opção B — Provar o scheduler de recomendações real

Autorizar no laboratório somente um vertical slice de provider escolhido, com snapshot mínimo das tabelas consultadas por esse provider, `tenants`, `recommendation_results`, `recommendation_lifecycle_events`, audit log/dependências acionadas, constraints, grants e policies. Primeiro capturar a lista SQL efetiva no fluxo escolhido. Desabilitar por configuração do harness os demais providers e chamadas externas. O aceite ficaria restrito a esse provider e aos objetos incluídos.

A opção B é necessária para declarar o scheduler de recomendações real aprovado. Nenhuma das opções foi aplicada automaticamente. Não se recomenda criar as tabelas reais dos nove providers em bloco.

## 8. Veredicto e próximo passo

**NO-GO para a implementação/teste real do scheduler sob RLS nesta rodada.** O dispatcher não existe, o runtime lab não tem as tabelas consultadas e o caminho padrão engloba nove providers com dependências de domínio. Continuar exigiria expandir o laboratório além do conjunto de probes já autorizado/documentado.

O próximo passo indispensável é escolher e autorizar a Opção A (prova limitada de fronteira) ou a Opção B (vertical slice real de um provider). Até lá, o scheduler não foi alterado e não deve ser considerado compatível com runtime restrito. Este relatório não autoriza deploy, acesso à Hostinger, mudança de roles reais ou cutover.
