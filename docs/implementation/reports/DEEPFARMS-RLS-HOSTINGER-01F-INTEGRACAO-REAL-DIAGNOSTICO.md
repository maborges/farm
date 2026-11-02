# DEEPFARMS-RLS-HOSTINGER-01F — Diagnóstico da Integração Real com RLS

**Data:** 2026-10-31  
**Escopo:** diagnóstico e experimentos isolados; nenhum código funcional alterado  
**Banco de teste:** `deepfarms_rls_lab`, PostgreSQL 16.15  
**Identidade de runtime:** `deepfarms_rls_lab_runtime`, autenticada diretamente  
**Veredicto:** **GO COM RESSALVAS para iniciar implementação controlada no laboratório**

## 1. Síntese

O código real de criação de engine e sessões conecta ao laboratório sob a role restrita. `_activate_session_tenant`, `get_session`, o helper do outbox e os helpers de contexto dos schedulers foram executados sem alterar código ou iniciar tarefas reais. O pool SQLAlchemy do `core.database` reutilizou a mesma conexão após commit, rollback e erro SQL sem manter `SET LOCAL` residual. Os testes unitários existentes de seleção de Tenant também passaram.

O diagnóstico identificou incompatibilidades que impedem usar o código atual com runtime restrito sem implementação controlada:

1. `get_db()` e `get_db_session()` não instalam contexto Tenant. Rotas que resolvem `tenant_id` por `get_tenant_id` mas fazem queries em `get_db` usam uma sessão diferente da sessão que recebeu contexto.
2. `get_session()` instala `SET LOCAL` uma vez ao iniciar a sessão. Depois de commit ou rollback, a transação seguinte fica sem contexto; a dependência não o reaplica.
3. Os schedulers de recomendações e ERP usam GUC de sessão (`set_config(..., false)`) e limpeza manual. Os helpers foram testados, mas o mecanismo é diferente do contexto transaction-local e depende da limpeza em todos os caminhos.
4. Outbox, automações e OpenWeather fazem descoberta de trabalho sem contexto Tenant. O outbox aceita `tenant_id=None` e omite o filtro tenant; os dois workers varrem configurações globalmente. Uma role runtime não deve executar essa descoberta global sem acesso de dispatcher explícito.
5. API e workers compartilham o engine criado a partir de uma única `settings.database_url`; operações administrativas/globais não trocam para uma identidade de banco separada.

**Conclusão:** há base técnica para começar uma correção pequena e central no laboratório. A aplicação atual não está pronta para operar com a role restrita. Este resultado não libera produção, cutover, Hostinger, nem declara o DeepFarms protegido por RLS.

## 2. Método e limites

- O harness importou o `core.database` real e substituiu `DATABASE_URL` apenas no ambiente do processo pelo endpoint/usuário/database do laboratório. O script verificou host, database e username antes da primeira consulta. O pool foi limitado a uma conexão para observar reuso. Nenhum valor de credencial foi impresso ou registrado.
- As sessões reais usaram `deepfarms_rls_lab_runtime`, `core.database.async_session_maker`, `get_db`, `get_db_session`, `core.dependencies.get_session`, `_activate_session_tenant`, `DomainEventOutboxService._set_rls_context` e os helpers de contexto dos schedulers ERP/recomendações.
- Não há tabelas de autenticação, outbox, automação, integração ou ORM do produto no laboratório. Por isso, não foram executados endpoints reais, consulta de membership contra banco, `claim_batch`, ciclos de scheduler nem tarefas externas. O teste de `get_tenant_id` foi complementado por unit tests com sessões simuladas.
- Os workers foram avaliados estaticamente e por chamadas isoladas aos helpers de contexto. Nenhum worker real foi iniciado.
- Nenhuma migration, DDL ou DML foi executada nesta etapa. O teste de `SELECT 1/0` foi intencional e seguido de rollback. O único banco acessado foi `deepfarms_rls_lab`.

## 3. Matriz dos caminhos de sessão e Tenant

| Caminho | Código observado | Comportamento de contexto | Diagnóstico |
|---|---|---|---|
| Engine e pool | `services/api/core/database.py:21-50` cria um `AsyncEngine` e uma fábrica de `AsyncSession`; `search_path=farms`, `pool_size`/`max_overflow` vêm das settings. | Um engine/configuração por processo; sem seleção de role por request ou por tipo de operação. | Engine real conectou ao laboratório como runtime. **Compatível tecnicamente**, mas sem separação de identidades de runtime, dispatch e operação global. |
| Evento `connect` | `core/database.py:64-71` chama `SET SESSION CHARACTERISTICS ... READ COMMITTED`. | Não configura Tenant. O comentário diz que injeta contexto, mas o SQL executado altera somente isolamento de transação. | **Confirmado:** sessão nova via `get_db()` não tinha GUC e a fixture RLS retornou zero linhas. |
| `get_db()` | `core/database.py:74-88`. | Cria sessão simples e fecha ao final; não recebe `Request` nem define Tenant. | **FAIL para rotas tenant-scoped** quando usado diretamente. Pode continuar sendo necessário para acesso público/global estritamente delimitado. |
| `get_db_session()` | `core/database.py:91-100`. | Cria sessão simples para scripts/workers; não define Tenant. | **FAIL para trabalho tenant-scoped** sem helper explícito antes da primeira query. |
| `get_session()` | `core/dependencies.py:138-149`. | Resolve `request.state.rls_tenant_id` ou Bearer; chama `_activate_session_tenant` uma vez antes de `yield`. | **PASS parcial:** no laboratório, o GUC UUID foi instalado na sessão real. Após commit, ficou limpo; uma nova transação na mesma sessão não foi rearmada. |
| `_activate_session_tenant()` | `core/dependencies.py:62-70`. | Executa `SET LOCAL`; grava UUID também em `session.info`. A interpolação é f-string, não bind parameter. | **PASS para set local/UUID; FAIL para rearmar automaticamente após fronteira transacional.** A chamada inicial após rollback/commit limpa corretamente o estado PostgreSQL, mas o chamador precisa ativá-lo de novo. |
| Resolver do request | `core/dependencies.py:86-129`. | Prefere estado interno; fallback lê e decodifica Bearer. Não lê `x-tenant-id` diretamente. | **PASS limitado:** header sozinho não resolveu Tenant nem instalou GUC. Um JWT sintético assinado foi resolvido e aplicado. Essa simulação não validou sessão nem membership. |
| Middleware RLS | `core/main.py:248-276`. | Lê só Authorization Bearer, verifica assinatura e extrai `tenant_id`, mas desativa validação de `exp`; não consulta sessão nem membership. Algumas rotas são ignoradas pelo middleware. | **Risco identificado:** ele prepara contexto a partir de claim antes da validação completa do endpoint. A dependência de autenticação depois verifica o token, mas o middleware isolado não prova que o usuário/sessão está autorizado. |
| Validação JWT/sessão | `core/dependencies.py:273-319`, `322-402`. | `_decode_platform_token` valida assinatura/expiração e regras v2; `_validate_token_session` consulta `SessaoAtiva` e revogação/expiração conforme o token. | **Confirmado por leitura de código; não exercitado contra lab**, que não contém a tabela de sessões. |
| Autorização do Tenant | `core/dependencies.py:404-494`. | `get_tenant_id` compara header e claim e exige `TenantUsuario.status='ATIVO'` para claim comum; sem claim, header requer vínculo ativo e múltiplos Tenants sem seleção são rejeitados. | Unit tests existentes passaram com sessão simulada. **Membership real não foi testada no banco de laboratório.** |
| `get_current_tenant()` | `core/dependencies.py:528-575`. | Valida Tenant ativo. Quando o JWT já contém `tenant_id`, não consulta `TenantUsuario` para confirmar membership atual. | **Risco identificado, não confirmado como falha explorável:** rotas que usam apenas essa dependência dependem da validade/atualização do claim emitido. |
| Rota tenant com `get_db` | Exemplos: `pecuaria/climatico/router.py:29-37,48-54`, `agricola/templates/router.py:35-44`; outros usos em IA. | A rota recebe `tenant_id` por `get_tenant_id` (que depende de `get_session`) e uma sessão de negócio separada via `get_db`. | **Incompatibilidade confirmada no código:** contexto é instalado numa sessão e a query/commit da rota usa outra sem contexto. Não é apenas uma hipótese sobre middleware. |
| Backoffice/global | `pecuaria/climatico/router.py:134-158`. | `get_current_admin` protege a rota de aplicação; operações de catálogo global continuam usando `get_db` e o mesmo engine/role. | **Incompatível com grants runtime restritos:** autenticação administrativa da aplicação não equivale a uma role de catálogo no PostgreSQL. Não foi executada operação global. |
| Endpoint público | `certificacoes_esg/public_router.py:16-45`. | Token público consulta dados via `get_db`, sem Tenant. | **Não exercitado:** requer policy/consulta pública mínima explícita; não pode herdar acesso global amplo do runtime comum. |

### Origem autenticada versus parâmetro do cliente

O teste contra a dependência real confirmou que um `x-tenant-id` isolado não instala contexto. Um Bearer sintético assinado foi convertido em UUID e aplicado; a chamada direta do unit test para `get_tenant_id` também confirmou que a seleção por header depende de vínculo ativo e que header sem vínculo resulta em 403. Os três testes unitários relevantes passaram.

O teste com Bearer no harness chamou a resolução de contexto, não `_validate_token_session` nem a autorização no banco. Portanto, a evidência mostra que o código não usa o header arbitrário como fonte direta, mas **não comprova autenticação end-to-end ou membership real no laboratório**. O middleware também não verifica `exp`; rotas precisam manter dependência de autenticação completa, e o contexto não deve ser tratado como autorização por si só.

## 4. Matriz dos caminhos de worker

| Caminho | Sessão/contexto encontrado | Simulação | Resultado com runtime restrito |
|---|---|---|---|
| Outbox service | `list_pending`/`claim_batch` só chamam `_set_rls_context` se o Tenant efetivo não for `None` (`events/outbox_service.py:62-100,191-203`). `run_outbox_relay_once` e o loop aceitam `tenant_id=None` por padrão (`events/outbox_worker.py:370-380, ...`). | O método real `_set_rls_context` foi chamado usando sessão runtime e instalou contexto `SET LOCAL`; commit o removeu. A tabela de outbox não existe no laboratório, então claim/relay não foram executados. | **Incompatibilidade confirmada por fluxo de código:** execução sem Tenant consulta sem contexto e sem filtro por Tenant. Sob policies tenant-private tende a retornar zero/ser negada, sem dispatcher dedicado o worker não descobre o trabalho. |
| Automação | `automacoes/worker.py:15-25` busca todas as configurações vencidas sem contexto; depois passa `cfg.tenant_id` ao service, usa a mesma sessão e faz commit dentro do loop (`32-47`). | Nenhuma tarefa foi iniciada. Inspeção estática; `AutomacoesService` filtra Tenant, mas não há instalação central do GUC no worker. | **Incompatibilidade confirmada no caminho:** seleção inicial não é Tenant-scoped; a sessão de processamento também não recebe contexto no worker antes da chamada. |
| OpenWeather | `integracoes/openweather/worker.py:14-34` enumera configs ativas sem contexto, depois itera Tenant usando a mesma sessão (`36+`). | Nenhuma consulta de integração/tarefa externa foi executada. | **Incompatibilidade confirmada no código e risco de execução:** enumeração transversal não cabe no runtime comum sem política/role dispatcher estreita; processamento posterior deve operar em sessão por Tenant. |
| Recommendations scheduler | Enumera `Tenant.id` numa sessão sem contexto (`recommendations/scheduler.py:484-488`), depois abre sessão por Tenant; `_set_tenant_context` usa `set_config(..., false)` e `_clear` faz rollback/RESET/commit (`491-509`). | Os helpers reais foram executados no lab: o contexto persistiu após commit e foi removido pela rotina de limpeza. Nenhum ciclo/provider foi executado. | **PASS do cleanup observado; incompatibilidade de arquitetura:** GUC de sessão não é local à transação. Descoberta global de Tenants também requer acesso de dispatcher. |
| ERP scheduler | Enumera Tenants sem contexto (`integracoes/erp/scheduler.py:66-79`), depois abre sessão por Tenant. Helper usa `set_config(..., false)` e cleanup com RESET (`245-263`). | Os helpers reais foram executados no lab: estado persistiu após commit e cleanup o removeu. Nenhum adapter, job ou integração foi executado. | **PASS do cleanup observado; mesma incompatibilidade** de GUC de sessão e descoberta global. |
| Workers globais/admin | Engine de `core.database` é compartilhado e não troca role por processo/escopo. | Não iniciados. | **Sem caminho PostgreSQL separado** para dispatcher, catálogo global ou administração sob runtime mínimo. |

## 5. Testes controlados

| Teste | Resultado | Evidência objetiva / limite |
|---|---|---|
| Engine real aponta somente ao laboratório sob runtime | **PASS** | Harness validou host/database/username antes da conexão; PostgreSQL retornou `current_database=deepfarms_rls_lab` e `current_user=session_user=deepfarms_rls_lab_runtime`. |
| `get_db()` real sem contexto | **PASS como comportamento observado; FAIL para uso tenant-scoped** | GUC ausente e SELECT da fixture tenant-private retornou zero linhas. |
| `get_db_session()` real sem contexto | **PASS como comportamento observado; FAIL para uso tenant-scoped** | GUC ausente sob runtime. |
| `_activate_session_tenant()` define GUC local | **PASS** | UUID sintético apareceu em `current_setting`; commit e rollback removeram o valor. |
| `get_session()` aplica estado interno | **PASS** | Request state simulado, sessão real e GUC coincidiram. |
| `get_session()` reaplica após commit | **FAIL** | Após commit a nova transação ficou sem GUC; a dependência não reativou o Tenant. |
| Resolver usa header `x-tenant-id` arbitrário como fonte direta | **PASS — rejeitado** | Header sozinho resolveu `None`; sessão real continuou sem contexto. |
| Bearer assinado resolve Tenant | **PASS parcial** | JWT sintético assinado foi resolvido/aplicado; não validamos sessão ativa nem membership com tabelas reais. |
| Unit tests de membership/header e fallback JWT | **PASS** | 3 testes existentes de `test_tenancy.py` passaram; são testes com mocks, não prova de banco. |
| `DomainEventOutboxService._set_rls_context()` | **PASS do helper** | Contexto local setado e removido após commit. Claim/relay não testados: tabela ausente no lab. |
| AsyncEngine real do `core.database`: commit/rollback/erro e pool | **PASS** | `pool_size=1`, `max_overflow=0`; mesmo `pg_backend_pid` nos quatro checkouts; GUC limpo depois de commit, rollback e `SELECT 1/0` seguido de rollback. |
| Helpers de contexto Recommendations/ERP | **PASS para set/cleanup; FAIL para escopo transacional esperado** | Ambos usam GUC de sessão, que permaneceu após commit; cleanup real resetou. Não foram executadas tarefas. |
| Rotas com modelo ORM no lab / autenticação completa | **NÃO EXECUTADO** | Tabelas de aplicação, usuário, sessões, TenantUsuario e ORM não existem na fixture. |
| Automação, OpenWeather, outbox relay, scheduler ou ERP real | **NÃO EXECUTADO** | Restrição respeitada: nenhum trabalho real ou integração externa iniciada. |

**Sem alterações persistentes no banco durante esta etapa:** o harness fez apenas consultas e alterações transacionais do GUC, sem DDL/DML; as transações de contexto foram encerradas e o pool foi disposed.

## 6. Incompatibilidades confirmadas versus riscos identificados

### Confirmadas

1. A aplicação tem dois caminhos de sessão com semânticas diferentes: `get_session()` contextualiza uma vez; `get_db()` e `get_db_session()` nunca contextualizam.
2. Um endpoint pode obter Tenant validado em `get_tenant_id()` e usar outra sessão `get_db()` para a operação. Isso ocorre, por exemplo, nas rotas de pecuária climática e templates agrícolas citadas acima.
3. `get_session()` não rearma o contexto depois de commit/rollback dentro da sessão. O comportamento foi observado com o engine real e pool real.
4. Os schedulers de recommendations/ERP usam GUC de sessão (`is_local=false`); helpers limpam em `finally`, mas o estado sobrevive a commits.
5. Outbox/automação/OpenWeather e enumeração de Tenant executam discovery sem contexto e não têm identidade de dispatcher separada no engine atual.
6. A role administrativa da aplicação não altera `current_user` do PostgreSQL; endpoints globais usam o mesmo `get_db` e URL de banco.

### Riscos apenas identificados, sem exploração/prova de falha

- O middleware extrai claim de JWT com `verify_exp=False`; dependências de autenticação completas validam token/sessão posteriormente, mas uma rota sem essas dependências poderia receber contexto derivado de token vencido. Não foi feita chamada HTTP com token expirado nem revisão exaustiva de todas as rotas.
- `get_current_tenant()` não confirma vínculo ativo quando o token já contém `tenant_id`; rotas devem ser revisadas para uso de `get_tenant_id()` quando membership atual for requisito.
- A validação de contexto não torna `app.current_tenant_id` secreto ou não-forjável para uma conexão SQL direta. Um cliente com credencial runtime e execução SQL arbitrária pode definir custom GUC; a confiança depende da fronteira de conexão e da aplicação validar o Tenant.
- A fixture não contém tabelas de negócio. A auditoria não mediu quais consultas reais falhariam ou quais tabelas sem RLS dependem hoje de filtros ORM.
- Falha de cleanup em schedulers pode invalidar a sessão conforme código, mas interrupção abrupta do processo, cancelamento durante cleanup e múltiplos processos não foram testados.

## 7. Correções mínimas necessárias por criticidade

1. **P0 — Um único caminho contextual para operações tenant-scoped.** Faça a sessão usada pela query de negócio ser a mesma sessão que recebe o Tenant validado. Direcione rotas protegidas para a dependência contextual central; mantenha exceções públicas/globais explícitas e estreitas. Não deixe `get_tenant_id()` contextualizar uma sessão enquanto o endpoint usa outro `get_db()`.
2. **P0 — Contexto local e rearmado por transação.** Centralize a aplicação de `app.current_tenant_id` com bind parameter (`set_config(..., :tenant, true)`) e reative no início de toda transação protegida, inclusive depois de commit/rollback. Falha de ativação deve fechar a operação. Não trate `session.info` como prova de que o GUC ainda está ativo.
3. **P0 — Só ativar contexto após validação de identidade/autorização.** Use JWT completo e sessão válida; confirme membership ativa no Tenant selecionado. O middleware pode encaminhar uma claim como dado auxiliar, mas não deve ser a autorização final. Cobrir também cookie e seleção por header sem aceitar Tenant arbitrário.
4. **P1 — Separar discovery de execução em workers.** Não fazer varredura global por uma role tenant comum. Use uma etapa dispatcher com acesso nominativo mínimo para descobrir IDs/status e abra uma sessão/contexto local por Tenant para cada trabalho. No outbox, não executar `tenant_id=None` como caminho de processamento normal sob runtime restrito.
5. **P1 — Separar operações globais/admin.** Catálogo global, endpoints de backoffice e leitura pública devem ter grants/policies e, quando necessário, role própria de baixo privilégio. `get_current_admin()` da aplicação não deve implicar privilégio SQL amplo; nunca usar `SUPERUSER`/`BYPASSRLS` como solução.

Essas mudanças podem começar pela dependência/session factory central e um teste de contrato no laboratório. Não é necessário iniciar refatoração de cada service antes de provar essa fronteira central; exceções de worker/global devem ser tratadas em trilhas pequenas após o contexto básico.

## 8. Veredicto

**GO COM RESSALVAS para iniciar implementação controlada exclusivamente no laboratório.** Os testes demonstraram que o engine real e uma sessão restrita conseguem instalar e limpar contexto, e que o pool não vazou GUC nos cenários exercitados. A mesma evidência confirmou que o caminho atual `get_session()` não reativa contexto por transação e que `get_db()` não o instala.

**NO-GO para configurar a aplicação atual para usar runtime restrito, liberar cutover ou declarar segurança em produção.** Primeiro devem ser corrigidos e testados os itens P0 e as rotas/workers globais identificados. A validação real de sessão autenticada/membership, endpoints, ORM e tarefas de worker exige fixtures correspondentes no laboratório e permanece pendente.

## 9. Próximo passo recomendado

Implementar e provar no laboratório somente a sessão contextual central — incluindo rotas que hoje misturam `get_tenant_id` com `get_db` — antes de ampliar para workers ou operações globais.
