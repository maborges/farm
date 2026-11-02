# DEEPFARMS-RLS-HOSTINGER-01G — Sessão Tenant Controlada

**Data:** 2026-10-31  
**Escopo:** sessão SQLAlchemy e ativação de Tenant; nenhuma migration ou alteração estrutural do banco  
**Integração RLS:** `deepfarms_rls_lab`, role `deepfarms_rls_lab_runtime`  
**Veredicto:** **GO COM RESSALVAS**, restrito à continuação controlada em laboratório

## 1. Resultado

A sessão da aplicação agora começa sem Tenant presumido. Depois da validação existente do token e da sessão e da confirmação de membership ativa, o contexto é definido com `set_config` parametrizado e escopo de transação. Um listener `Session.after_begin` reaplica esse contexto ao iniciar cada nova transação física da mesma sessão, inclusive depois de commit, rollback ou erro SQL. O listener usa a `Connection` do evento, sem emitir consultas recursivas via `Session`.

As rotas tenant-scoped identificadas com uma sessão `get_db()` separada foram direcionadas a `get_session()`. Os endpoints globais de modelos climáticos mantiveram `get_db()` sem contexto Tenant. A validação real no laboratório usou o engine e a fábrica de sessões de `core.database`, autenticados diretamente como runtime restrito.

Isso comprova o mecanismo de sessão e RLS sobre fixtures sintéticas. Não comprova o fluxo completo de autenticação/membership contra tabelas reais nem libera produção ou cutover.

## 2. Arquivos e funções modificados

| Arquivo | Alteração |
|---|---|
| `services/api/core/database.py` | Novo listener `apply_tenant_context_after_begin`, que instala o Tenant registrado na sessão usando `set_config(..., true)` na conexão da transação. O listener não altera sessões sem Tenant nem conexões que não sejam PostgreSQL. |
| `services/api/core/dependencies.py` | `_activate_session_tenant` usa SQL parametrizado e mantém o valor autorizado para rearmamento; `get_session` não lê mais `request.state` ou JWT bruto para presumir Tenant; `get_current_user_claims` só ativa claim Tenant depois da validação existente de token/sessão e membership ativa; `get_tenant_id` mantém validação de vínculo e seleção autorizada por header; `get_current_tenant` verifica membership ativa e ativa o contexto antes da leitura do Tenant. |
| `services/api/pecuaria/climatico/router.py` | Sete rotas tenant-scoped passaram de `get_db` para `get_session`. Os quatro endpoints de backoffice global continuam com `get_db`. |
| `services/api/agricola/templates/router.py` | Rotas de templates tenant-scoped passaram para `get_session`. |
| `services/api/ia/router.py` | Os endpoints de simulação de estresse e plano de ação passaram para `get_session`. |
| `services/api/pecuaria/routers/campo_sync.py` | As duas rotas tenant-scoped passaram para `get_session`. |
| `services/api/operacional/routers/qualidade.py` | As rotas tenant-scoped passaram para `get_session`. |
| `services/api/tests/unit/core/test_tenancy.py` | Atualizadas regressões de sessão neutra, validação de membership e ativação autorizada. |
| `services/api/tests/unit/core/test_database_tenant_context.py` | Novos testes unitários do listener, incluindo SQL parametrizado e neutralidade sem Tenant. |
| `services/api/tests/integration/core/test_rls_tenant_session_lab.py` | Novos testes de integração opt-in; recusam URL que não seja host, porta, database e role autorizados e usam o engine real da aplicação. |
| `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py` | Atualizada a expectativa estática de `SET LOCAL` para o `set_config` parametrizado e o listener por transação. |

## 3. Causa e correção das incompatibilidades P0

### Sessão com contexto derivado de claim bruto

Antes, `get_session` confiava em `request.state.rls_tenant_id` ou decodificava o Bearer e ativava o Tenant sem confirmar membership naquela etapa. Agora abre sessão neutra. A sessão só recebe o contexto pelo caminho autenticado: validação existente de token/sessão, UUID válido e membership com status `ATIVO`. A seleção por `x-tenant-id` continua condicionada à autorização existente em `get_tenant_id`; o header sozinho não ativa contexto.

`get_current_user_claims` instala o contexto para tokens comerciais com claim Tenant depois de validar o vínculo, de modo que feature gates executados antes da função da rota usem a mesma sessão contextual. Tokens globais/superuser sem contexto e sessões públicas/globais que usam `get_db()` continuam neutros.

### Contexto perdido depois da fronteira transacional

Antes, `SET LOCAL` era executado somente uma vez na abertura da sessão. Commit e rollback removiam o GUC e a próxima transação não recebia Tenant. Agora `Session.after_begin` aplica o GUC em cada nova transação, usando `Connection.execute` e bind parameter. Quando o Tenant é autorizado no meio de uma transação já iniciada, `_activate_session_tenant` define o GUC diretamente nessa transação e registra o valor para as seguintes. A prova consulta `current_setting` no PostgreSQL; `session.info` é somente a fonte de rearmamento, não a evidência de que o GUC está efetivo.

### Query de negócio em sessão diferente

As rotas identificadas usavam `get_tenant_id()` e `get_db()` em paralelo. A primeira dependência autorizava o Tenant em uma sessão e a rota consultava por outra, neutra. As rotas tenant-scoped listadas acima agora usam `get_session()`, compartilhada por FastAPI com as dependências de autorização da mesma requisição. Os endpoints de catálogo global/backoffice seguem explicitamente em `get_db()`.

### Autorização de `get_current_tenant`

Antes, um claim Tenant válido sintaticamente não revalidava membership ativa no `get_current_tenant`. Agora a função verifica o vínculo ativo, ativa o contexto transacional e só então consulta o Tenant. Testes unitários cobrem membership válida e rejeição sem vínculo.

## 4. Matriz de testes

| Cenário | Esperado | Observado | Resultado |
|---|---|---|---|
| Sessão iniciada com JWT/`request.state` sem autorização executada | Sem GUC | `get_session` não executou SQL e não preencheu Tenant | **PASS** |
| Claim com Tenant e membership ativa | Contexto aplicado após validação de token/sessão e membership | Teste unitário confirmou a ordem e o `set_config` | **PASS unitário** |
| Claim com Tenant sem membership ativa | Rejeição sem contexto | HTTP 403; nenhuma ativação | **PASS unitário** |
| `get_current_tenant` com membership ativa | Ativa e retorna Tenant | Teste unitário confirmou membership, ativação e retorno | **PASS unitário** |
| `get_current_tenant` sem membership | Rejeição sem contexto | HTTP 403; nenhuma ativação | **PASS unitário** |
| SQL de contexto | Parametrizado e transaction-local | `set_config('app.current_tenant_id', :tenant_id, true)` | **PASS** |
| Listener em sessão sem Tenant / dialeto SQLite | Nenhuma configuração | Nenhuma chamada à conexão | **PASS unitário** |
| Identidade de integração | Banco e usuário restritos | `deepfarms_rls_lab`; `current_user = session_user = deepfarms_rls_lab_runtime` | **PASS** |
| Sem contexto, fixture privada | Nenhuma linha A/B | GUC vazio; zero linhas | **PASS laboratório** |
| Tenant A e Tenant B | Cada um vê somente suas linhas | A viu `tenant-a`; B viu `tenant-b` | **PASS laboratório** |
| Commit e transação seguinte | Contexto reaplicado antes da próxima consulta | `current_setting` voltou a A na transação seguinte | **PASS laboratório** |
| Rollback e transação seguinte | Contexto reaplicado | `current_setting` voltou a A | **PASS laboratório** |
| Erro SQL seguido de rollback | Sessão recuperável, sem perder contexto Tenant | `SELECT 1/0`, rollback e leitura seguinte sob B | **PASS laboratório** |
| INSERT seguido de COMMIT | Marker persiste para A | Encontrado em sessão subsequente de A; removido pela limpeza do teste | **PASS laboratório** |
| INSERT seguido de ROLLBACK | Marker não persiste | Ausente na consulta subsequente de A | **PASS laboratório** |
| Reutilização do pool | Backend reusado sem vazamento entre sessões | Uma conexão do engine real da aplicação; A/B/sem contexto preservados | **PASS laboratório** |
| Rotas globais de modelos climáticos | Sem contexto Tenant automático | Continuam usando `get_db()` | **PASS por inspeção** |
| Membership autenticada contra schema real | Autenticação/sessão/membership reais aprovadas no lab | Tabelas de autenticação do produto não existem na fixture | **NÃO EXECUTADO** |
| Endpoints HTTP reais com ORM do produto | Queries RLS reais aprovadas | Tabelas/modelos de negócio não existem no lab | **NÃO EXECUTADO** |

### Execuções

- Suíte unitária focada: **48 passed, 1 skipped**, incluindo tenancy, listener, guardrail pertinente, testes de domínio pecuário e gates agrícolas. Um aviso Pydantic existente foi emitido.
- Integração com o engine real, configurado em processo exclusivamente para o laboratório: **2 passed**.
- `compileall` dos arquivos modificados: **PASS**.
- `git diff --check`: **PASS**.
- A suíte unitária opt-in de laboratório foi executada sem a variável de URL em uma rodada comum e pulou; a execução autorizada posterior passou os dois cenários no laboratório.

Uma execução exploratória mais ampla também encontrou seis falhas não relacionadas a esta mudança: expectativas antigas de documentação/sidebar/Sankhya nos guardrails de arquitetura e ausência do módulo `agricola.ndvi_avancado.routers.irrigacao`. O guardrail de `SET LOCAL` que ficou obsoleto foi atualizado e seu teste focado passou. Essas seis falhas estão em arquivos/funcionalidades fora deste escopo.

O Ruff completo do conjunto de arquivos não ficou limpo devido a regras preexistentes de estilo nos routers. A checagem restrita encontrou dois nomes já não resolvidos em `core/dependencies.py` (`Any` e `Usuario`), fora das linhas alteradas. A compilação Python e os testes focados passaram.

## 5. Regressões e ressalvas

- `get_session` não instala mais GUC a partir do middleware ou de um Bearer apenas decodificado. Código que dependia desse comportamento sem passar por `get_current_user_claims`, `get_tenant_id` ou `get_current_tenant` poderá agora falhar fechado sem contexto; esses caminhos precisam ser inventariados antes de adoção ampla.
- A dependência `get_current_user_claims` agora consulta membership para tokens com claim Tenant. O laboratório não contém `TenantUsuario`, `SessaoAtiva` nem as tabelas de usuário; o caminho foi coberto unitariamente, não por autenticação HTTP/database end-to-end.
- A fixture comprovou o mecanismo RLS sintético, não policies das tabelas reais nem todos os ORM/services.
- A suíte de integração altera somente os markers sintéticos da `farms.rls_probe` no laboratório. Os markers de commit foram excluídos no `finally`; nenhuma DDL foi executada.

## 6. Pendências fora do escopo desta etapa

1. Validar sessão real, revogação e membership ativa em fixture de autenticação no laboratório, sem usar banco principal.
2. Executar uma rota HTTP representativa com ORM e policies correspondentes no laboratório.
3. Inventariar outros módulos que ainda combinam dependências de Tenant com `get_db`. Alguns encontrados na busca são stubs sem consulta implementada; `enterprise/sprints_27_33_router.py` também combina handlers síncronos com um getter assíncrono e requer diagnóstico próprio antes de troca pontual.
4. Workers, schedulers, dispatcher, operações globais e políticas das tabelas de produção permanecem fora do escopo e não foram alterados.
5. Não foram feitos deploy, cutover, conexão à Hostinger, migrations ou mudanças nos bancos `farms` de desenvolvimento e `tara`.

## 7. Veredicto

**GO COM RESSALVAS** para continuar a implementação controlada exclusivamente no laboratório. O engine real da aplicação demonstrou isolamento A/B, contexto ausente, rearmamento após commit/rollback/erro e reutilização de pool com a role runtime.

As provas de autorização e membership são unitárias, pois as tabelas reais de identidade não estão na fixture. Portanto, este resultado não autoriza configurar a aplicação completa com runtime restrito, deploy, cutover ou declaração de segurança em produção.

### Próximo passo indispensável

Adicionar ao laboratório uma fixture mínima de autenticação/membership compatível e executar uma requisição HTTP representativa, com token/sessão válidos, para provar que a autorização real precede o contexto RLS na mesma sessão da query de negócio.
