# DeepFarms — RLS-DEV-02 — Homologação Canário

## Veredicto: **GO**

Homologação concluída em `farms` por HTTP real, com as roles restritas, isolamento A/B, rate-limit e uso do pool verificados. O canário foi encerrado. Este GO cobre somente as três rotas homologadas; não representa cutover geral nem aprovação dos demais módulos.

## Ambiente e identidades

- PostgreSQL: `192.168.0.3:5432/farms`, schema `farms`.
- API canário: `127.0.0.1:8012`, sem exposição pública.
- Runtime: `deepfarms_runtime`; autenticação: `deepfarms_auth`.
- `current_database()`, `current_user` e `session_user` foram conferidos para as duas conexões. Ambas as roles não têm `SUPERUSER` nem `BYPASSRLS`; o runtime não tem `SELECT` em `usuarios.senha_hash` nem `EXECUTE` em `farms.auth_login_material(text)`. A auth não tem acesso direto ao hash.
- Durante a execução, `pg_stat_activity` mostrou uma conexão de cada role. O launcher manteve `REQUIRE_RESTRICTED_RUNTIME_ROLE=true`, pool runtime de duas conexões, jobs embutidos desativados e allowlist das rotas homologadas.
- O canário encerrou normalmente após os testes. A API principal e seu `DATABASE_URL` não foram alterados.

## Testes HTTP e SQLAlchemy

Fixtures sintéticas novas, sem reutilizar registros existentes:

- Tenant A `69c139cb-ff24-44d6-9af3-cb55fbcf746d`, usuário `c5c49af5-2201-45ab-a48a-81f12b5f4b42`.
- Tenant B `4ab79067-b046-45cf-bf25-0da019fff5c5`, usuário `f316b001-2a15-486b-aedc-18cd95953bfd`.

Todos os testes abaixo passaram usando `POST /api/v1/auth/login`, `POST /api/v1/notificacoes/` e `GET /api/v1/notificacoes/` no processo FastAPI real:

| Cenário | Resultado |
|---|---|
| Login válido para A e B | PASS |
| Senha inválida e e-mail inexistente com resposta externa igual | PASS |
| Limite global: cinco falhas em e-mail normalizado, sexta tentativa bloqueada | PASS |
| Limite personalizado A (`max_tentativas=2`), aplicado após bcrypt | PASS |
| POST de notificação INFO em A e B | PASS |
| GET retorna marcador do Tenant autenticado e oculta o outro Tenant | PASS |
| Header `X-Tenant-Id` apontando para o outro Tenant | Negado com 403 |
| GET sem autenticação/cookie | Negado com 401 |
| Alternância HTTP A → B → B → A → A → B pelo pool da canário | PASS, sem vazamento observado |
| Hook SQLAlchemy real: leitura A, rollback, erro SQL, leitura B, commit e transação sem contexto | PASS; contexto ausente viu zero notificações sintéticas |
| Conexão runtime sem contexto Tenant | PASS; RLS retornou zero linhas sintéticas |
| Rotas fora da allowlist (`/docs`) | Negadas com 404 |

As notificações de teste usaram nível `INFO`, sem envio de e-mail, chamada de IA ou integração externa. Os testes unitários de autenticação, rate-limit e contexto de sessão registrados nesta execução: **30 passed**.

## Fixtures e limpeza

Fixtures criadas por `borgus` (owner do recorte) somente com IDs/e-mails aleatórios desta execução; nenhuma role, policy, grant ou objeto foi alterado. Foram removidos usuários, Tenants, memberships, perfis, unidades, configurações de rate-limit, sessões, tentativas, notificações e registros de auditoria sintéticos. A verificação somente leitura posterior confirmou **zero** Tenants, usuários e notificações restantes para os IDs finais; resíduos de uma execução de teste interrompida também foram removidos por IDs exatos. Nenhum registro preexistente foi apagado.

Verificação final RLS anterior à homologação: `20_verify_readonly.sql` terminou com código 0; 14 tabelas com RLS, 15 policies, sem FORCE, sem memberships indevidas ou privilégios elevados para runtime/auth; hash e função de autenticação protegidos conforme allowlist. Nenhum script de ativação foi reaplicado.

## Arquivos e operação

- Canário reaproveitado: `services/api/rls_canary.py`, `services/api/start_rls_canary.py` e `.gitignore` (a regra exclui o arquivo local de credenciais). Credenciais permaneceram em `services/api/.env.rls-canary.local`, modo `0600`, sem valores registrados neste relatório.
- Nesta retomada, nenhum código funcional da API foi alterado; o harness de fixture/testes ficou temporário em `/tmp` e não foi adicionado ao repositório.
- Para uma nova homologação aprovada: `cd /opt/lampp/htdocs/farm/services/api && ./.venv/bin/python start_rls_canary.py`; parar com `Ctrl+C`. A porta fixa é `127.0.0.1:8012`.

Não houve rollback de banco porque não foram feitas alterações estruturais. Hostinger, `tara`, proxy e instância principal permaneceram fora da execução.

## RLS-DEV-03 — Integração controlada por rota

### Implementação e testes

Foi adicionado `RLS_DEV_ROUTE_SESSIONS_ENABLED` (padrão `false`, permitido somente com `ENVIRONMENT=development`). A opção seletiva exige `REQUIRE_RESTRICTED_RUNTIME_ROLE=false`, preservando o engine legado global durante a migração. Com a opção ativa, `get_session` seleciona runtime restrito somente para `POST /api/v1/auth/login`, `POST /api/v1/notificacoes/` e `GET /api/v1/notificacoes/`; qualquer outra requisição continua usando o engine definido em `DATABASE_URL`. Se o engine restrito não inicializar, a rota falha sem fallback. O launcher `start_rls_dev_routes.py` iniciou a app completa somente em `127.0.0.1:8013`, sem substituir `DATABASE_URL` e sem iniciar jobs.

As pools dedicadas foram construídas a partir do arquivo local protegido já existente. O runtime confere banco e identidade `farms/deepfarms_runtime` ao conectar e rejeita roles elevadas, com memberships ou ownership; auth usa `farms/deepfarms_auth`. `application_name` separado permitiu confirmar ambas as conexões da instância na atividade PostgreSQL. O login usou a função de material bcrypt e o fluxo de Tenant permaneceu no runtime. Os processos internos de notificação, quando a opção está ligada, também selecionam runtime e propagam o contexto; não usam a conexão legada.

Homologação em `farms`, usando apenas usuários/Tenants sintéticos e removidos ao final:

| Cenário | Resultado |
|---|---|
| Login A/B válido, inválido e e-mail inexistente não enumerável | PASS |
| Rate-limit global e personalizado por Tenant | PASS |
| POST/GET notificação A/B e bloqueio de tentativa cross-tenant | PASS |
| Requisição sem autenticação e query runtime sem contexto | PASS: 401 e zero linhas sintéticas |
| Alternância A/B, commit, rollback, erro SQL e reuso do pool | PASS |
| Roles efetivas nas pools live da app | PASS: runtime e auth confirmadas em `pg_stat_activity` |
| Endpoint não migrado `GET /api/v1/auth/me` | PASS pelo engine legado; a resposta exige colunas que runtime não possui |
| Opção desabilitada com arquivo de credenciais inexistente | PASS: nenhum engine restrito foi criado; engine legado continuou em `farms` |
| Documentação e endpoints não listados | PASS: `/docs` continuou disponível na app completa |

Testes focados: **94 passed, 1 skipped**, com três warnings em mocks de auditoria. `py_compile` passou. Um conjunto mais amplo adicional teve **6 falhas e 117 passes** nos testes do dispatcher genérico `tests/unit/notifications/test_notification_dispatcher*.py`; esses módulos não foram modificados. Os testes FastAPI em `tests/unit/notificacoes`, auth, rate-limit, tenancy e roteamento passaram.

Arquivos alterados nesta etapa: `services/api/core/config.py`, `services/api/core/database.py`, `services/api/core/dependencies.py`, `services/api/core/services/auth_service.py`, `services/api/notificacoes/service.py`, `services/api/.env.example`, `services/api/start_rls_dev_routes.py`, `services/api/tests/unit/core/test_rls_route_session_routing.py` e este relatório. Nenhum script SQL, role, grant, policy, `DATABASE_URL` local ou código de outros módulos foi alterado. O teste usou `borgus` apenas para fixtures e para a rota não migrada, nunca como runtime das três rotas restritas. A instância da porta 8013 foi encerrada; os IDs sintéticos foram removidos e a conferência por IDs retornou zero.

### Bloqueador funcional confirmado

O fluxo HTTP de criação/listagem funciona, mas a execução assíncrona de notificações `WARNING`, `DANGER` e `OPORTUNIDADE` também deriva desta rota. A ACL atual não permite ao runtime `UPDATE farms.notificacoes` nem `SELECT usuarios.email` (verificação somente leitura: `true, true, false, false, false` para SELECT/INSERT/UPDATE de notificações, SELECT de e-mail e EXECUTE da função de autenticação). Assim, a atualização da mensagem gerada por IA e o fan-out de e-mail falham fechados e são registrados no log; não há fallback para `borgus`. Esses níveis não foram disparados durante a homologação para evitar efeitos externos.

## Veredicto da RLS-DEV-03: **NO-GO**

O roteamento restrito das três rotas e o isolamento A/B estão implementados e aprovados. A integração não pode ser considerada concluída sem resolver como os efeitos assíncronos de notificação que exigem escrita/read de e-mail operarão sem a conexão legada. Não ampliar grants nem reativar fallback privilegiado. A próxima decisão indispensável é autorizar uma solução restrita para esses efeitos ou aceitar formalmente que eles permaneçam indisponíveis antes de habilitar o modo na instância principal de desenvolvimento. A opção continua desabilitada por padrão.

## RLS-DEV-03A — Efeitos assíncronos de notificações

### Correção preparada

Para sessões marcadas pela allowlist de `get_session`, os efeitos em background agora usam pool runtime restrito e propagam Tenant e usuário autenticado. A sessão só é marcada nas três combinações de método/rota aprovadas; fluxos ainda legados preservam seu pool existente. Contexto de usuário ausente falha fechado. A atualização da mensagem e a resolução de destinatários não fazem fallback para `borgus`.

O runtime chama somente `farms.update_notification_message(uuid,text)` e `farms.notification_recipient_emails(uuid)`. O desenho SQL dá à nova role `deepfarms_notification_fn_owner` (NOLOGIN, sem BYPASSRLS/membership) SELECT das colunas necessárias em notificações, memberships, usuários e preferências, e UPDATE somente de `notificacoes.mensagem`. As funções exigem membership ativa do usuário e restringem leitura/escrita à notificação e Tenant no contexto transacional. O runtime não recebe SELECT em `usuarios.email` nem UPDATE direto da mensagem.

### Arquivos desta correção

- `services/api/core/dependencies.py`
- `services/api/notificacoes/service.py`
- `services/api/tests/unit/core/test_rls_route_session_routing.py`
- `services/api/tests/unit/notificacoes/test_rls_background_notification_access.py`
- `services/api/scripts/rls/dev_activation/10_login_notifications_rls.sql` (allowlist de policies)
- `services/api/scripts/rls/dev_activation/20_verify_readonly.sql`
- `services/api/scripts/rls/dev_activation/30_notification_async_effects.sql`
- `services/api/scripts/rls/dev_activation/80_rollback_notification_async_effects.sql`
- `services/api/scripts/rls/dev_activation/90_rollback_login_notifications_rls.sql` (ordem de rollback)
- `services/api/scripts/rls/dev_activation/README.md`

### Validação e pendência

- `pytest tests/unit/notificacoes tests/unit/core/test_rls_route_session_routing.py`: **48 passed**, três warnings preexistentes de mocks no serviço de auditoria.
- `ruff check` nos dois arquivos de teste: **PASS**; compilação Python e `git diff --check`: **PASS**.
- Os seis testes do dispatcher genérico foram reproduzidos no checkout `HEAD` exportado em `/tmp`: **6 failed, 5 passed** tanto no baseline quanto no workspace. Causa observada: às 22h UTC a janela de silêncio real suprime antes de chegar ao adaptador. São preexistentes e não pertencem ao pacote RLS de notificações.
- A inspeção read-only em `farms` confirmou as colunas necessárias nas quatro tabelas e nenhum trigger de usuário que altere a semântica da atualização. A sessão foi `borgus`; não houve DDL/DML.
- A validação SQL foi concluída em uma instância PostgreSQL 16.15 temporária e isolada em `/tmp` (socket Unix local, sem acesso TCP), com fixtures sintéticas A/B e runtime autenticado diretamente como `deepfarms_runtime`, sem `SUPERUSER`/`BYPASSRLS`. `30_notification_async_effects.sql` instalou role, duas funções, grants e quatro policies; segunda execução também passou. O runtime atualizou somente a notificação A autorizada; B atualizou somente B; consultas e atualizações cruzadas, usuário não membro e contexto ausente foram negados. A resolução retornou apenas os destinatários autorizados de cada Tenant, excluindo preferência de e-mail desativada e sensibilidade insuficiente. Tentativas diretas do runtime de `SELECT usuarios.email` e `UPDATE notificacoes.mensagem` retornaram `permission denied`. `80_rollback_notification_async_effects.sql` terminou com COMMIT e a verificação posterior confirmou remoção das duas funções, quatro policies e role auxiliar, mantendo RLS base ativo, sem FORCE, e sem grants diretos de e-mail/update ao runtime.
- A primeira execução de validação encontrou uma falha de diagnóstico no preflight de `30`: a ausência da função base `farms.auth_login_material(text)` no fixture mínimo causava erro de resolução antes de uma mensagem clara. O preflight foi corrigido para declarar esse pré-requisito explicitamente e verificar owner `deepfarms_auth_fn_owner`, `SECURITY DEFINER`, ausência de EXECUTE para runtime/PUBLIC. Com a função base sintética correta no fixture, instalação, reinstalação e rollback passaram. Nenhuma alteração foi aplicada a `farms`, `tara` ou Hostinger.
- Para aplicar manualmente em desenvolvimento, após a autorização operacional, na WSL Flash: `cd /opt/lampp/htdocs/farm && sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/30_notification_async_effects.sql`; em seguida executar a verificação: `sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/20_verify_readonly.sql`. Em caso de rollback aprovado: `sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/80_rollback_notification_async_effects.sql`.
- A homologação HTTP final de `WARNING`, `DANGER` e `OPORTUNIDADE` ainda depende da aplicação do SQL em `farms`; não foi executada nesta validação isolada.

### Veredicto RLS-DEV-03A: **PENDENTE DA APLICAÇÃO CONTROLADA EM DESENVOLVIMENTO**

O SQL está validado e liberado para aplicação controlada: cria uma role NOLOGIN no cluster, quatro policies e duas funções no schema `farms`, concede apenas grants de colunas mínimos à role auxiliar e EXECUTE das funções ao `deepfarms_runtime`. Para encerrar a RLS-DEV-03A, aplique o script pela WSL Flash e retome a homologação HTTP; nenhum SQL foi aplicado ao banco real nesta tarefa. O rollback específico é `80_rollback_notification_async_effects.sql`.
