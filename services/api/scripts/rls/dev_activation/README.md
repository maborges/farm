# Preparação RLS — login e notificações — desenvolvimento

## Estado

Os scripts base `00_roles.sql` e `10_login_notifications_rls.sql` foram aplicados anteriormente no banco de desenvolvimento `farms`; `20_verify_readonly.sql` aprovou aquele estado antes do adendo 03A. Nesta tarefa, `30_notification_async_effects.sql` e `80_rollback_notification_async_effects.sql` foram preparados, mas **não executados**. Nenhuma alteração em `farms` ocorreu nesta tarefa. O script de instalação exige superuser, pois cria uma role PostgreSQL (escopo de cluster) e aplica policies/grants/funções no banco; `borgus` não tem `CREATEROLE` e `admin_farms` tem `BYPASSRLS`, mas não é superuser.

A regra funcional aprovada é: limite global pré-autenticação de 5 tentativas em 15 minutos por e-mail normalizado, incluindo e-mails inexistentes; os limites personalizados do Tenant são carregados e aplicados somente depois da validação bcrypt. O guard global nunca é desativado pela configuração do Tenant.

## Escopo e identidades

O recorte abrange 16 relações: `tenants`, `usuarios`, `tenant_usuarios`, `perfis_acesso`, `unidade_produtiva_usuarios`, `assinaturas_tenant`, `planos_assinatura`, `unidades_produtivas`, `configuracoes_saas`, `configuracoes_tenant`, `sessoes_ativas`, `login_tentativas`, `notificacoes`, `notificacoes_leituras`, `notificacoes_preferencias` e `tenant_audit_log`.

- `deepfarms_runtime`: login e notificações pós-autenticação; sem `SUPERUSER`, `BYPASSRLS`, ownership, memberships ou acesso a hash.
- `deepfarms_auth`: serviço de autenticação isolado; material bcrypt somente via `farms.auth_login_material(text)`, além do contador global de tentativas. Não usar como runtime.
- `deepfarms_auth_fn_owner`: `NOLOGIN`, sem membership; owner não privilegiado da função, com SELECT somente nas colunas necessárias ao bcrypt.
- `deepfarms_notification_fn_owner`: identidade `NOLOGIN` separada, sem `BYPASSRLS` ou memberships; owner de duas funções específicas para os efeitos assíncronos das notificações.
- A role de deploy/administração é a identidade PostgreSQL superuser aprovada para a janela; não fica configurada na aplicação.

Os scripts estão limitados ao banco `farms` e às tabelas do recorte. Habilitam RLS sem `FORCE` durante a canário para que o serviço legado ainda conectado como owner continue operando. Isso é transição controlada, não estado final seguro: a instância owner deve ser removida da operação depois que os demais fluxos forem migrados. O plano não troca o `DATABASE_URL` geral nem encaminha outras rotas à canário.

## Pré-requisitos e sequência autorizada

Executar somente depois de autorização explícita, janela de manutenção, backup e disponibilidade de identidade PostgreSQL **superuser**. Não usar `admin_farms` como substituto: tem `BYPASSRLS`, mas não `SUPERUSER`; `borgus` não pode criar roles. Usar cliente/rede que alcance `192.168.0.2:5432`. Os comandos abaixo são modelos; `<DBA_LOGIN>` deve ser substituído localmente e nenhum segredo deve ser colocado na linha de comando.

1. Registrar baseline em sessão somente leitura e conferir banco/identidade:

   ```bash
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; SELECT current_database(), current_user, session_user, current_setting('transaction_read_only'); SELECT rolname, rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname IN ('borgus','admin_farms'); SELECT n.nspname, c.relname, pg_get_userbyid(c.relowner), c.relrowsecurity, c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='farms' AND c.relname IN ('tenants','usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios','assinaturas_tenant','planos_assinatura','unidades_produtivas','configuracoes_saas','configuracoes_tenant','sessoes_ativas','login_tentativas','notificacoes','notificacoes_leituras','notificacoes_preferencias','tenant_audit_log') ORDER BY c.relname; ROLLBACK;"
   ```

   Confirmar que database é `farms`, que a sessão de aplicação não está sendo usada e que as 16 tabelas/owners/estado RLS correspondem ao baseline documentado. Se algo divergir, parar e revisar o pacote. Antes de DDL, criar backup seguro somente do schema, incluindo ACL/owners, fora do repositório:

   ```bash
   pg_dump -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms --schema-only --schema=farms --file=<CAMINHO_SEGURO>/farms-schema-before-rls.sql
   ```

2. Provisionar roles (script verifica `current_database()` e exige `rolsuper`). Senhas não estão nos arquivos. Defini-las interativamente sem eco/log, e armazená-las no cofre usado pelo serviço:

   ```bash
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/00_roles.sql
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X
   ```

   No prompt `psql`, executar `\password deepfarms_runtime` e `\password deepfarms_auth`; depois `\q`. Não imprimir ou salvar credenciais no repositório.

3. Aplicar primeiro o recorte base, depois o adendo de efeitos assíncronos, e só então executar a verificação completa somente leitura. `20_verify_readonly.sql` agora espera as quatro roles:

   ```bash
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/10_login_notifications_rls.sql
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/30_notification_async_effects.sql
   psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/20_verify_readonly.sql
   ```

   Investigar qualquer linha inesperada no verificador antes de continuar; o checker não é um “PASS” automático se grants herdados, ACLs ou policies divergirem.

4. Preparar canário isolada, sem substituir o `DATABASE_URL` da API geral:

   - `DATABASE_URL`: conexão como `deepfarms_runtime`.
   - `AUTHENTICATION_DATABASE_URL`: conexão como `deepfarms_auth`.
   - `AUTHENTICATION_DATABASE_ROLE=deepfarms_auth`.
   - `REQUIRE_RESTRICTED_RUNTIME_ROLE=true`.
   - Manter segredos e demais chaves de autenticação no secret store; não passar URLs com senha em argumentos/logs.
   - Configurar roteamento da canário somente para `POST /api/v1/auth/login`, `POST /api/v1/notificacoes/` e `GET /api/v1/notificacoes/`; manter outros caminhos na instância legada.

   A configuração de processo/proxy e o início da canário **não** fazem parte deste pacote nem desta preparação.

5. Antes do HTTP, usar somente duas identidades/Tenants sintéticos autorizados para validar login, criação/listagem de notificações, negação cross-tenant e ausência de autenticação/contexto. No estado observado de `farms` não há fixture sintética aprovada; não testar com conta real. A autorização da futura rodada deve cobrir criação/limpeza de fixtures sintéticas, ou limitar-se à aplicação/verificação SQL e deixar o HTTP pendente.

## Rollback

Rollback exige autorização e superuser. Primeiro remover o roteamento para canário/parar a canário e restaurar a configuração anterior do processo. `90_rollback_login_notifications_rls.sql` aceita o estado integralmente aplicado ou somente as roles de `00_roles.sql` (por exemplo, se `10_...sql` abortar atomicamente):

```bash
psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/90_rollback_login_notifications_rls.sql
psql -h 192.168.0.2 -p 5432 -U <DBA_LOGIN> -d farms -W -X -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; SELECT rolname FROM pg_roles WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner'); SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='farms' AND c.relname IN ('usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios','assinaturas_tenant','unidades_produtivas','configuracoes_saas','configuracoes_tenant','sessoes_ativas','login_tentativas','notificacoes','notificacoes_leituras','notificacoes_preferencias','tenant_audit_log') ORDER BY c.relname; SELECT schemaname,tablename,policyname FROM pg_policies WHERE schemaname='farms' AND policyname LIKE '%_deepfarms_%'; SELECT to_regprocedure('farms.auth_login_material(text)'); ROLLBACK;"
```

O rollback desabilita RLS, remove policies/grants do recorte, função e roles do pacote, mas não apaga linhas criadas por testes HTTP (tentativas, sessões, notificações ou auditoria). Registrar IDs das fixtures e limpar apenas linhas sintéticas identificadas, em operação separada autorizada. Se o preflight encontrar policies adicionais, memberships ou estado diferente, ele interrompe; não contornar manualmente. Não executar `20_verify_readonly.sql` depois do rollback: ele verifica roles já removidas.

## Efeitos assíncronos sob runtime restrito (adendo 03A)

`30_notification_async_effects.sql` concede à role `deepfarms_runtime` apenas EXECUTE em `farms.update_notification_message(uuid,text)` e `farms.notification_recipient_emails(uuid)`. As funções exigem contexto de usuário e Tenant, validam membership ativa, restringem-se à notificação do Tenant e executam sob `deepfarms_notification_fn_owner`, que possui somente SELECT das colunas necessárias e UPDATE da coluna `notificacoes.mensagem`. O runtime não recebe SELECT em `usuarios.email` nem UPDATE direto na mensagem. Os destinatários vêm de memberships ativas do Tenant e respeitam `email_ativo`/`nivel_sensibilidade` da preferência da própria pessoa.

Estas funções não são aplicadas por `10_login_notifications_rls.sql`. Após aprovação operacional específica, executar `30_notification_async_effects.sql`, validar com `20_verify_readonly.sql` e então homologar a canário. Para reverter somente este adendo, parar a canário e executar `80_rollback_notification_async_effects.sql`; para rollback completo do pacote base, executar depois `90_rollback_login_notifications_rls.sql`. A criação da role de função é cluster-wide e requer superuser. Nenhum destes scripts foi executado como parte da preparação 03A.

Comando de aplicação manual após autorização expressa, na WSL Flash (autenticação local do usuário `postgres`; nenhum segredo é necessário):

```bash
cd /opt/lampp/htdocs/farm
sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/30_notification_async_effects.sql
sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/20_verify_readonly.sql
```

Se o checkout não estiver montado nesse caminho na WSL Flash, copiar os arquivos SQL versionados para um caminho local legível pelo usuário `postgres` e ajustar somente o caminho passado a `-f`.

Rollback específico, após parar/remover o canário:

```bash
sudo -u postgres psql -d farms -X -v ON_ERROR_STOP=1 -f services/api/scripts/rls/dev_activation/80_rollback_notification_async_effects.sql
```

## Evidências e limitações

O estado real consultado em modo somente leitura mostrou `borgus` como owner das relações examinadas e sem `CREATEROLE`; `admin_farms` tem `BYPASSRLS`, não é superuser; as três roles do pacote ainda não existiam; as tabelas do recorte estavam sem RLS/policies. Nenhuma alteração foi aplicada no banco principal nesta preparação. Testes de aplicação/RLS são executados somente no `deepfarms_rls_lab`.
