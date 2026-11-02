# DEEPFARMS-RLS-HOSTINGER-01J1 — Vertical Slice Real de Recomendações sob RLS

**Data:** 2026-11-01  
**Veredicto atualizado:** **GO COM RESSALVAS — provider Wizard validado sob runtime RLS; ciclo dispatcher completo pendente de execução por loopback**  
**Histórico:** a execução inicial foi interrompida antes de DDL por falta de credencial administrativa autenticável. Esse bloqueio foi resolvido pelo responsável; a retomada e evidências atuais constam na seção 9.

## 1. Resultado executivo

A Opção B foi retomada com inspeção dos nove providers e do caminho real do scheduler. O provider escolhido é **Wizard**, que consulta três tabelas de domínio com queries de leitura, não exige chamada externa e pode produzir candidatos com dados sintéticos sem unidade produtiva. É o menor caminho que pode executar no ciclo agendado atual: o provider de clima consulta uma tabela-fonte, mas retorna imediatamente sem `unidade_produtiva_id`, e o scheduler global atual não fornece uma unidade ao ciclo.

O laboratório foi conectado somente como `deepfarms_rls_lab_runtime` e inspecionado. Ele contém as quatro fixtures sintéticas da 01E2, mas não as tabelas que o slice usa. A identidade dispatcher está ausente. `deepfarms_rls_lab_deploy` tem `rolcreaterole = false`. A tentativa de autenticação administrativa como `postgres` falhou; não foi feita nova tentativa com outras credenciais.

Como o usuário instruiu interromper a criação da role caso não haja privilégio administrativo disponível, a execução parou antes de DDL. Não foram alterados o scheduler, código, roles, grants, policies ou dados. Abaixo estão o contrato e as mudanças mínimas que o administrador autorizado precisa executar para que o trabalho possa continuar.

## 2. Provider escolhido

| Provider | Dependências/observação estática | Decisão |
|---|---|---|
| **Wizard** | Consultas a `wizard_implantacoes_operacionais`, `wizard_implantacoes_checklist_itens` e `wizard_implantacoes_pendencias`; somente leitura no provider; não exige unidade; sem chamada externa no caminho `evaluate()`. Candidatos sintéticos podem ser produzidos por status/progresso e checklist/pendências. | **Selecionado.** Menor slice executável no ciclo global sem adaptar domínio/unidade e permite manter `dry_run=True`, exercitando models e queries reais sem criar persistência de recomendação. |
| Clima | Uma query a `registros_clima`, mas `evaluate()` retorna `[]` se o contexto não tiver `unidade_produtiva_id`. O scheduler global não envia unidade. | Menos tabelas, mas não exercita query pelo ciclo real atual. |
| Campo | Consultas a dispositivo, tarefas e tombstones; consultas repetidas em tarefas e leitura de entidades completas. | Mais superfícies e colunas que o Wizard para este teste. |
| ESG | Quatro fontes de certificação no caminho de avaliação. | Dependências maiores. |
| Agricultura | Safra, operações, talhões, checklist e dados de usuário; múltiplas queries/joins. | Dependências maiores. |
| Pecuária | Lotes, eventos e tarefas de campo, além de agregação. | Dependências maiores. |
| Estoque | Lotes e consultas agregadas de movimentos/estoque. | Dependências maiores. |
| Financeiro | Orçamento e dados de lançamentos/custos em queries agregadas. | Dependências maiores. |
| Frota | Delega a `FrotaDashboardService`, com superfície operacional mais ampla que o Wizard. | Dependências maiores. |

A inscrição dos providers padrão é feita em `recommendations/__init__.py`. O harness proposto restringirá o registry em memória a Wizard, sem alterar o registry padrão do processo de produção. `dry_run=True` evita expiry e persistência de resultados, mas ainda executa as consultas do provider selecionado.

## 3. Objetos mínimos identificados para o harness

Os objetos abaixo são **planejados, mas não foram criados**. Todos seriam criados somente em `deepfarms_rls_lab.farms`, com fixture sintética mínima e removível.

| Objeto | Uso no slice e privilégio pretendido |
|---|---|
| `tenants` (fixture estrutural mínima com `id`, `ativo`) | Dispatcher seleciona somente `id` para linhas `ativo = true`; RLS de SELECT para dispatcher restringe elegibilidade. Runtime sem SELECT nesta tabela. |
| `usuarios` (fixture mínima com `id`) | Referência sintética do owner exigido por `wizard_implantacoes_operacionais`; sem grant de leitura para dispatcher/runtime. |
| `unidades_produtivas` (fixture mínima com `id`) | Permite manter a FK mapeada de `unidade_produtiva_id`; o slice usa `NULL` e não consulta a tabela. Sem grant ao dispatcher/runtime. |
| `wizard_implantacoes_operacionais` | A query real seleciona a entidade inteira; exige colunas mapeadas do model e FK `tenant_id → tenants.id`, owner → usuarios e unidade → unidades_produtivas. RLS/FORCE por `tenant_id`; runtime SELECT somente. |
| `wizard_implantacoes_checklist_itens` | A query real agrega `count(id)` por `implantacao_id` e `status`. FK para a implantação. Sem `tenant_id` direto; policy relacional que exige pai visível sob o Tenant contextual. Runtime SELECT somente. |
| `wizard_implantacoes_pendencias` | A query agrega `count(id)` por `implantacao_id`, `status` e `severidade`. FK para a implantação. Policy relacional equivalente; runtime SELECT somente. |

Os dados seriam dois Tenants ativos, uma implantação incompleta por Tenant e, opcionalmente, itens/pendências sintéticos correspondentes. O runtime não receberia DML nessas tabelas no teste dry-run. O dispatcher não receberia grants nos três objetos Wizard nem nas tabelas de usuário/unidade.

### Objetos fora do conjunto mínimo

`recommendation_results`, `recommendation_lifecycle_events` e `tenant_audit_log` não são necessários para a prova de **consulta** com dry-run: a expiração é ignorada e `RecommendationEngine` abre savepoint e reverte a avaliação do provider. Não se planeja persistir recomendações nesta rodada. Essa escolha reduz DDL e deixa o aceite limitado à query real e à geração de candidatos em dry-run.

Se algum comportamento observado no código exigir persistência apesar do dry-run, o teste deve parar e reportar o objeto faltante; não conceder grants ou criar tabelas adicionais por tentativa. A tabela `wizard_implantacoes_etapas` não é consultada pelo provider e as relações são `lazy="noload"`; referências opcionais a etapas ficariam nulas, sem FK nessa fixture mínima. Não foi identificada sequência necessária: IDs são UUIDs ou o `count` não grava.

## 4. Contrato de identidade e privilégio

### Dispatcher candidato

- Nome: `deepfarms_rls_lab_dispatcher`.
- Login restrito ao uso do laboratório por configuração de conexão/ACL operacional; nenhum membership em owner/deploy.
- `NOINHERIT`, `NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`.
- `CONNECT` ao database lab, `USAGE` no schema `farms`, `SELECT (id, ativo)` em `farms.tenants`, policy `FOR SELECT` que expõe somente Tenants ativos.
- Nenhum grant em tabelas de negócio, fixtures Wizard, usuários, unidades, sequences ou funções de domínio.

Observação PostgreSQL: roles são objetos de cluster, não de database. A role deve ficar sem privilégios em outros bancos e a conectividade precisa ser limitada à base lab por ACL/HBA já compatível. **Não** executar `REVOKE CONNECT FROM PUBLIC` em `farms`/`tara` como atalho, pois alteraria acesso de terceiros fora do escopo. O administrador deve confirmar que a regra de conexão permite a identidade apenas ao laboratório antes de fornecer a credencial.

### Runtime

- Identidade já existente: `deepfarms_rls_lab_runtime`, usada diretamente; não criar nem alterar role.
- Consulta do provider: SELECT nas três tabelas Wizard, com policy tenant direta na implantação e policy relacional nas tabelas filhas. `FORCE ROW LEVEL SECURITY`; runtime não é owner nem tem bypass.
- `app.current_tenant_id` deve ser instalado por transação através de `_activate_session_tenant`/hook central da 01G. Sessão independente por Tenant e sem GUC persistente.
- Nenhuma permissão de dispatcher é concedida ao runtime e vice-versa.

## 5. Comandos mínimos pendentes para administrador

A role dispatcher não pôde ser provisionada: a autenticação administrativa disponível foi recusada e a role deploy observada não tem `CREATEROLE`. Um administrador autorizado, conectado ao cluster do PostgreSQL e conferindo o database-alvo, deve executar **somente** o provisionamento da identidade a seguir. A senha deve ser definida interativamente pelo procedimento aprovado de segredos; não colocar senha em SQL, histórico ou relatório.

```sql
-- Executar como administrador do PostgreSQL.
-- A criação de role é cluster-wide; não atribuir membership de owner/deploy.
CREATE ROLE deepfarms_rls_lab_dispatcher
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

GRANT CONNECT ON DATABASE deepfarms_rls_lab
  TO deepfarms_rls_lab_dispatcher;

\password deepfarms_rls_lab_dispatcher
```

Conceder `USAGE` em `farms` e `SELECT (id, ativo)` em `tenants` **somente depois** que o deploy do laboratório criar as fixtures/policy e confirmar o banco atual. Não aplicar ACL a banco principal. O administrador também deve comprovar a restrição de conexão à base lab (por regras existentes de HBA/ACL); se não puder fazê-lo sem alterar `farms` ou `tara`, não provisionar esse login neste servidor e solicitar um endpoint de laboratório isolado.

Após o provisionamento, o deploy poderá usar sua associação existente ao owner para criar as fixtures mínimas no laboratório. O teste de grants negativos do dispatcher deve rodar antes de qualquer consulta scheduler. Este relatório não fornece nem registra credencial.

## 6. Implementação e testes

| Item | Resultado | Evidência |
|---|---|---|
| Inspeção dos nove providers | **CONCLUÍDO** | Modelos/queries e registry padrão lidos; Wizard selecionado pela menor superfície executável no scheduler global. |
| Conexão ao `deepfarms_rls_lab` como runtime | **PASS** | `current_database() = deepfarms_rls_lab`; `current_user = session_user = deepfarms_rls_lab_runtime`; PostgreSQL 16.15. |
| Runtime sem privilégios elevados | **PASS** | `rolsuper = false`, `rolbypassrls = false`, sem membership em owner/deploy; `farms` USAGE=true, CREATE=false. |
| Role dispatcher restrita criada | **BLOQUEADO** | Role ausente; deploy `rolcreaterole = false`; conexão administrativa como `postgres` falhou em autenticação. |
| Objetos mínimos e fixtures A/B | **NÃO EXECUTADO** | Nenhum DDL/DML realizado; as tabelas necessárias não existem. |
| Dispatcher lista somente Tenants ativos | **NÃO EXECUTADO** | Requer role e fixture `tenants`. |
| Dispatcher nega acesso a tabelas privadas | **NÃO EXECUTADO** | Requer grants/role/fixtures do slice para tentativa negativa. |
| Provider Wizard executa query ORM real sob runtime | **NÃO EXECUTADO** | Tabelas Wizard ausentes; nenhum scheduler ou serviço executado. |
| Isolamento runtime A/B, transação e pool | **NÃO EXECUTADO NESTA ETAPA** | Provas sintéticas anteriores da 01E2/01G não foram contadas como PASS do provider real. |
| Advisory lock concorrente | **NÃO EXECUTADO** | Não foram abertas duas sessões de scheduler. |
| Dry-run sem persistência | **NÃO EXECUTADO** | Requer execução do provider no scheduler real. |
| Código/testes funcionais modificados | **NENHUM** | A implementação parou no gate de identidade antes de DDL e alterações de código. |

Não houve FAIL de isolamento observado; os cenários operacionais simplesmente não foram exercitados. Não foram executados outros workers ou integrações externas.

## 7. Próxima execução após desbloqueio

Depois do administrador confirmar a role dispatcher e a restrição de conexão, seguir em ordem:

1. Criar apenas as seis fixtures listadas, por deploy no database lab, com FKs necessárias, policies/FORCE RLS e grants nominativos; sem migrations do produto.
2. Inserir dados sintéticos A/B como owner antes de FORCE RLS, sem copiar dados reais.
3. Alterar somente o scheduler para usar sessão dispatcher para lock/discovery e runtime independente por Tenant com helper central da 01G. Usar o registry Wizard apenas no harness; produção conserva registry padrão.
4. Testar primeiro permissões e RLS diretamente como dispatcher/runtime; depois executar scheduler dry-run com pool unitário e duas sessões concorrentes para lock.
5. Remover as fixtures temporárias em teardown apenas depois de confirmar que foram criadas por esta rodada, ou mantê-las se a regra operacional do lab exigir evidência persistente. Registrar o estado final sem credenciais.

Se o serviço Wizard emitir SQL sobre outro objeto, interromper antes de ampliar fixtures e revisar a query capturada. Se qualquer chamada externa for introduzida, não executá-la; o provider escolhido não deve exigir uma.

## 8. Limitações e veredicto

**NO-GO para o vertical slice nesta execução.** O obstáculo é operacional e específico: não há credencial administrativa autenticável para criar a role dispatcher restrita. A execução parou nesse ponto, antes de alterações, como solicitado. O conjunto de fixtures foi identificado e é pequeno o bastante para uma próxima tentativa autorizada, mas não foi criado.

Não há alteração de código para reverter nem mudança de banco nesta rodada. O passo indispensável é um administrador autorizado provisionar a identidade conforme a seção 5 e confirmar que ela só alcança o database de laboratório; depois, retomar o DDL mínimo e o teste do provider Wizard. Este veredicto não aprova nenhum provider, o scheduler completo, produção ou cutover.

## 9. Retomada autorizada — estado atual

Esta seção supersede as conclusões operacionais das seções 1, 6, 7 e 8, que registram a interrupção inicial. A retomada manteve o escopo no provider Wizard e no database `deepfarms_rls_lab`.

### Estado do laboratório e identidade

- A role `deepfarms_rls_lab_dispatcher` foi encontrada, com LOGIN e sem `INHERIT`, SUPERUSER, BYPASSRLS, CREATEDB ou CREATEROLE. Catálogo `pg_auth_members`: **zero memberships** para dispatcher e runtime.
- O runtime conectado confirmou `current_database=deepfarms_rls_lab`, `current_user=session_user=deepfarms_rls_lab_runtime`, PostgreSQL 16.15. Runtime sem SUPERUSER/BYPASSRLS.
- Owner dos objetos de fixture: `deepfarms_rls_lab_owner`; conexão de DDL foi `deepfarms_rls_lab_deploy` com `SET ROLE deepfarms_rls_lab_owner`. Roles administrativas existentes não foram modificadas.
- `has_column_privilege` confirmou `SELECT` do dispatcher nas colunas `tenants.id` e `tenants.ativo`; o dispatcher não tem SELECT de tabela nos dados Wizard. Runtime tem SELECT nas três tabelas Wizard e não tem SELECT em `tenants`.
- O executor está remoto do PostgreSQL: o servidor registrou cliente `172.26.128.1` e endereço do servidor `172.26.132.19`. Tentativas do dispatcher foram rejeitadas pelo HBA para SSL e sem SSL. Nenhuma regra HBA foi alterada. A autenticação dispatcher via loopback foi informada como PASS pelo responsável, mas não pôde ser repetida por este executor.
- Todas as consultas e DDL desta retomada apontaram para `deepfarms_rls_lab`. Não houve conexão nem alteração em `farms`, `tara`, Hostinger ou outro banco de desenvolvimento.

### Fixtures criadas exclusivamente no laboratório

Foram criadas seis tabelas sintéticas, sem migrations de produto e sem dados reais:

| Tabela | Conteúdo/uso | RLS |
|---|---|---|
| `tenants` | Colunas mínimas `id`, `ativo`; dois tenants ativos A/B e um inativo para testar elegibilidade. | ENABLE + FORCE; policy SELECT dispatcher `ativo IS TRUE`. |
| `usuarios` | IDs sintéticos referenciados pelo owner Wizard. | Sem grant runtime/dispatcher. |
| `unidades_produtivas` | IDs sintéticos e estrutura mínima da FK mapeada; implantação usa unidade NULL. | Sem grant runtime/dispatcher. |
| `wizard_implantacoes_operacionais` | Colunas ORM consultadas pela seleção da entidade; duas implantações incompletas, uma por Tenant; FK a tenants, users e unidade. | ENABLE + FORCE; policy runtime SELECT por `tenant_id = current_setting(..., true)`. |
| `wizard_implantacoes_checklist_itens` | `id`, `implantacao_id`, `status`; FK à implantação; uma linha pendente por Tenant. | ENABLE + FORCE; policy relacional SELECT via pai e contexto Tenant. |
| `wizard_implantacoes_pendencias` | `id`, `implantacao_id`, `status`, `severidade`; FK à implantação; uma pendência crítica aberta por Tenant. | ENABLE + FORCE; policy relacional SELECT via pai e contexto Tenant. |

Não foram criadas `recommendation_results`, `recommendation_lifecycle_events` ou `tenant_audit_log`: o slice usa `dry_run=True`, que executa a avaliação em savepoint e reverte, sem persistir recomendações. As três fixtures operacionais receberam somente SELECT para runtime. Dispatcher não recebeu grants nelas. Nenhuma sequence foi necessária.

### Arquivos modificados

- `services/api/core/config.py`: novo `recommendation_dispatcher_database_url`, fornecido via `RECOMMENDATION_DISPATCHER_DATABASE_URL`.
- `services/api/core/database.py`: engine e sessionmaker dispatcher opcionais e separados; sem URL configurada, não há fallback para runtime.
- `services/api/main.py`: dispose do engine dispatcher no shutdown.
- `services/api/recommendations/scheduler.py`: advisory lock e discovery passam pelo dispatcher; a query seleciona apenas `Tenant.id` e filtra `Tenant.ativo`; o lock é mantido durante o ciclo e sobrevive ao commit que fecha o snapshot de discovery. Cada Tenant segue em sessão runtime própria. Contexto instalado via `_activate_session_tenant` da 01G; removido o GUC persistente `set_config(..., false)` e cleanup `RESET`; rollback de cleanup deixa o contexto local transacional encerrado. Sem URL dispatcher o scheduler falha fechado.
- `services/api/tests/unit/recommendations/test_recommendations_productive_scheduler.py`: regressões atualizadas para dispatcher, falha fechada, contexto central e dry-run.
- `services/api/tests/integration/recommendations/test_rls_wizard_scheduler_lab.py`: prova integrada executável no host/loopback, com registry temporário contendo somente Wizard e URLs lab injetadas pelo runner.

O registry default de produção não foi alterado. Nenhum outro provider, scheduler ou worker foi modificado. Nenhuma chamada externa foi feita.

### Evidências e matriz atualizada

| Prova | Resultado | Evidência |
|---|---|---|
| Provider com menor slice executável | **PASS** | Wizard usa três consultas/tabelas de domínio, sem unidade ou chamada externa obrigatória; duas implantações sintéticas geraram três candidatos para cada Tenant. |
| Fixtures/constraints/FKs | **PASS** | DDL somente em `deepfarms_rls_lab`; FK tenant/owner/unidade e FKs filhas à implantação. RLS/FORCE ativo nas quatro tabelas com dados de Tenant/dispatcher/runtime. |
| Atributos e memberships | **PASS** | Roles runtime e dispatcher sem atributos elevados; nenhum membership para owner/deploy. |
| Grants de dispatcher | **PASS por catálogo** | SELECT de colunas `id`,`ativo` em `tenants`; sem privilégio nas tabelas Wizard; autenticação/consulta efetiva como dispatcher bloqueada para este executor pelo HBA. |
| Runtime A/B com provider ORM real | **PASS** | `_run_tenant_cycle(..., dry_run=True)` com o scheduler/runner/model/service reais e registry de teste Wizard-only: A recebeu só linha A, B só linha B; três candidatos cada; current_user/session_user runtime e GUC correspondente. |
| Pool sem vazamento | **PASS** | Pool runtime com `pool_size=1`; Tenant A e B usaram o mesmo backend PostgreSQL `123154`, sem compartilhar a linha ou o contexto. |
| Sem contexto | **PASS** | Sessão runtime nova retornou zero implantações. |
| Contexto após COMMIT/ROLLBACK/erro | **PASS** | Mesma AsyncSession reaplicou o Tenant A e retornou uma linha A após commit, rollback e `division by zero` seguido de rollback. |
| Dry-run | **PASS no caminho runtime** | Provider executou queries reais e produziu candidatos; `dry_run=True`, sem commit do ciclo nem persistência de recomendação. Os objetos de recomendação continuam ausentes. O teste integrado automatizado também compara snapshots operacionais antes/depois quando executado no host autorizado. |
| Lock advisory concorrente | **NÃO EXECUTADO com dispatcher** | O teste integrado implementa duas sessões dispatcher (`acquire`, segunda tentativa negada, release e nova aquisição), mas foi pulado/bloqueado neste executor remoto pelo HBA. Unit mocks não contam como prova PostgreSQL. |
| Falha de A e continuação em B | **NÃO EXECUTADO no scheduler completo** | Erro SQL e recuperação da sessão A foram provados; ciclo completo A-falha/B-sucesso depende do teste dispatcher no host. |
| Ciclo completo `run_scheduled_recommendation_cycle` via dispatcher | **PENDENTE** | `pytest` do módulo de integração: 1 skipped sem URLs lab; acesso dispatcher deste executor rejeitado por HBA. |

Testes de regressão: `services/api/.venv/bin/pytest -q services/api/tests/unit/recommendations/test_recommendations_productive_scheduler.py` — **8 passed**. `compileall` dos arquivos alterados — **PASS**. `git diff --check` — **PASS**. Módulo de integração no executor atual — **1 skipped**, pois precisa dos URLs runtime/dispatcher e de execução pelo loopback permitido.

### Bloqueio residual e veredicto

O bloqueio administrativo original não existe mais. O bloqueio residual é exclusivamente de origem de rede: este executor chega como `172.26.128.1`, enquanto o HBA do dispatcher aceita loopback. Não alterei HBA nem concedi acesso adicional. Para fechar a matriz, executar `services/api/tests/integration/recommendations/test_rls_wizard_scheduler_lab.py` no host/loopback autorizado com `DEEPFARMS_RLS_01J1_RUNTIME_URL` e `DEEPFARMS_RLS_01J1_DISPATCHER_URL` apontando para `deepfarms_rls_lab`; não usar a URL do banco principal.

**GO COM RESSALVAS**, restrito à avaliação real do provider Wizard sob runtime Tenant nas fixtures RLS. A parte runtime, isolamento A/B, contexto transacional, erro e pool foi exercitada. A descoberta e exclusão mútua via conexão dispatcher ainda precisam da execução do teste integrado no loopback. Não se declara aprovado o scheduler completo nem qualquer outro provider; não há autorização de deploy, produção ou cutover.

## 10. Correção do advisory lock — 2026-11-01

### Causa-raiz

`_acquire_scheduler_lock` usa `pg_try_advisory_lock`, que cria um **lock de sessão PostgreSQL** associado ao backend físico. Antes da correção, o lock era adquirido pela conexão gerenciada por `AsyncSession`. `AsyncSession.commit()` encerra a transação e pode devolver essa conexão ao pool; a sessão SQLAlchemy continua viva, mas não garante manter o mesmo backend. Se outra sessão recebe do pool o backend que ainda detém o lock, PostgreSQL considera a chamada reentrante na mesma sessão e `pg_try_advisory_lock` retorna `true`. O retorno observado pelo teste é compatível com esse caso. Os PIDs do teste que falhou não foram registrados, portanto não se afirma que a reutilização do mesmo backend foi diretamente observada naquela execução.

### Correção implementada

- `services/api/recommendations/scheduler.py`: o ciclo agora abre uma `AsyncConnection` diretamente de `dispatcher_engine` e a mantém checked-out desde a aquisição até o processamento de todos os Tenants. O `COMMIT` após a descoberta encerra o snapshot sem devolver a conexão física ao pool. Runtime Tenant continua em sessões separadas.
- O lock segue sendo de sessão. A liberação explícita ocorre em `finally`, após rollback de eventual transação de descoberta falha. Se o unlock falhar, a conexão é invalidada para que um lock ainda ativo não retorne ao pool.
- `services/api/tests/integration/recommendations/test_rls_wizard_scheduler_lab.py`: o teste concorrente agora usa duas conexões dispatcher distintas, registra `pg_backend_pid()` de ambas, verifica PIDs distintos, confirma que o PID da primeira permanece igual após `COMMIT`, espera `false` na segunda aquisição, e depois verifica aquisição pela segunda conexão após o unlock.
- `services/api/tests/unit/recommendations/test_recommendations_productive_scheduler.py`: testes unitários adaptados para a conexão dedicada e para invalidar conexão se o unlock falhar.

Não foram alterados roles, grants, policies, fixtures, HBA, banco principal, `tara` ou Hostinger.

### Verificação desta correção

| Verificação | Resultado | Evidência |
|---|---|---|
| Testes unitários do scheduler | **PASS** | `services/api/.venv/bin/pytest -q services/api/tests/unit/recommendations/test_recommendations_productive_scheduler.py` — **9 passed**. |
| Teste PostgreSQL integrado solicitado | **NÃO COMPROVADO NESTE EXECUTOR** | Executado `services/api/.venv/bin/pytest -rs -v services/api/tests/integration/recommendations/test_rls_wizard_scheduler_lab.py`; **1 skipped**, porque `DEEPFARMS_RLS_01J1_RUNTIME_URL` e `DEEPFARMS_RLS_01J1_DISPATCHER_URL` não foram fornecidas ao processo. Nenhum PID PostgreSQL foi coletado nesta execução. |
| Causa de reentrância | **CONFIRMADA PELO TIPO DO LOCK E PELO FLUXO** | O lock é session-scoped e a conexão via `AsyncSession` podia ser liberada no commit. A execução original não tinha captura de PID, então a reutilização do mesmo backend naquela falha específica é inferência compatível, não uma medição retrospectiva. |
| Retenção da conexão corrigida | **IMPLEMENTADA; PENDENTE PROVA PostgreSQL** | `AsyncConnection` é adquirida diretamente do engine e permanece no escopo externo até o `finally`; teste de integração atualizado para verificar os PIDs quando executado com as URLs autorizadas. |
| Unlock/sem vazamento ao pool | **PASS UNITÁRIO; PENDENTE PROVA PostgreSQL** | `finally` chama unlock; falha de unlock invalida a conexão. Teste unitário verifica invalidação. |

O aceite pedido para o advisory lock ainda não está satisfeito: a integração precisa resultar em **1 passed** no executor com acesso autorizado ao loopback e URLs exclusivamente do laboratório. A execução remota atual não tentou contornar o HBA nem alterou a rede. O veredicto geral permanece **GO COM RESSALVAS**; não se declara concorrência PostgreSQL aprovada até a execução integrada real.
