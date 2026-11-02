-- Verificação pós-aplicação. Somente SELECT; executar conectado a farms.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SELECT current_database() AS database, current_user, session_user,
       inet_client_addr() AS client_addr,
       current_setting('transaction_read_only') AS transaction_read_only;

SELECT rolname, rolcanlogin, rolsuper, rolbypassrls, rolcreatedb,
       rolcreaterole, rolinherit, rolreplication, rolconnlimit,
       shobj_description(oid,'pg_authid') AS package_marker
FROM pg_roles
WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner','deepfarms_notification_fn_owner')
ORDER BY rolname;

SELECT target.rolname,
       EXISTS (SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname=target.rolname) AS owns_database,
       EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname='farms' AND r.rolname=target.rolname) AS owns_farms_schema,
       EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='farms' AND r.rolname=target.rolname) AS owns_farms_relation,
       EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname='farms' AND r.rolname=target.rolname) AS owns_farms_function
FROM (VALUES ('deepfarms_runtime'),('deepfarms_auth'),('deepfarms_auth_fn_owner'),('deepfarms_notification_fn_owner')) AS target(rolname)
ORDER BY target.rolname;

SELECT target.rolname,
       has_database_privilege(target.rolname,'farms','CONNECT') AS database_connect,
       has_schema_privilege(target.rolname,'farms','USAGE') AS farms_usage,
       has_schema_privilege(target.rolname,'farms','CREATE') AS farms_create
FROM (VALUES ('deepfarms_runtime'),('deepfarms_auth'),('deepfarms_auth_fn_owner'),('deepfarms_notification_fn_owner')) AS target(rolname)
ORDER BY target.rolname;

SELECT member.rolname AS member, granted.rolname AS granted_role,
       m.admin_option, m.inherit_option, m.set_option
FROM pg_auth_members AS m
JOIN pg_roles AS member ON member.oid=m.member
JOIN pg_roles AS granted ON granted.oid=m.roleid
WHERE member.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner','deepfarms_notification_fn_owner')
   OR granted.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner','deepfarms_notification_fn_owner')
ORDER BY 1,2;

SELECT c.relname, pg_get_userbyid(c.relowner) AS owner,
       c.relrowsecurity AS rls, c.relforcerowsecurity AS force_rls,
       has_table_privilege('deepfarms_runtime',c.oid,'SELECT') AS runtime_select,
       has_table_privilege('deepfarms_runtime',c.oid,'INSERT') AS runtime_insert,
       has_table_privilege('deepfarms_auth',c.oid,'SELECT') AS auth_select
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid=c.relnamespace
WHERE n.nspname='farms'
  AND c.relname IN (
      'tenants','usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
      'assinaturas_tenant','planos_assinatura','unidades_produtivas',
      'configuracoes_saas','configuracoes_tenant','sessoes_ativas',
      'login_tentativas','notificacoes','notificacoes_leituras',
      'notificacoes_preferencias','tenant_audit_log'
  )
ORDER BY c.relname;

-- Deve retornar zero linhas: grants em nível de tabela fora da allowlist.
WITH target_roles(role_name) AS (
    VALUES ('deepfarms_runtime'),('deepfarms_auth'),('deepfarms_auth_fn_owner'),('deepfarms_notification_fn_owner')
),
target_tables(table_name) AS (
    VALUES ('tenants'),('usuarios'),('tenant_usuarios'),('perfis_acesso'),
          ('unidade_produtiva_usuarios'),('assinaturas_tenant'),('planos_assinatura'),
          ('unidades_produtivas'),('configuracoes_saas'),('configuracoes_tenant'),
          ('sessoes_ativas'),('login_tentativas'),('notificacoes'),
          ('notificacoes_leituras'),('notificacoes_preferencias'),('tenant_audit_log')
),
privileges(privilege_name) AS (
    VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER')
),
checks AS (
    SELECT r.role_name, t.table_name, p.privilege_name,
           has_table_privilege(r.role_name,format('farms.%I',t.table_name),p.privilege_name) AS granted,
           CASE
             WHEN r.role_name='deepfarms_runtime' AND p.privilege_name='SELECT'
               AND t.table_name IN ('tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios','notificacoes') THEN true
             WHEN r.role_name='deepfarms_runtime' AND p.privilege_name='INSERT'
               AND t.table_name IN ('notificacoes','tenant_audit_log') THEN true
             WHEN r.role_name='deepfarms_auth' AND t.table_name='login_tentativas'
               AND p.privilege_name IN ('SELECT','INSERT','UPDATE') THEN true
             ELSE false
           END AS allowed
    FROM target_roles r CROSS JOIN target_tables t CROSS JOIN privileges p
)
SELECT role_name, table_name, privilege_name
FROM checks
WHERE granted AND NOT allowed
ORDER BY role_name,table_name,privilege_name;

-- Também deve retornar zero linhas: privilégios efetivos por coluna, inclusive
-- direitos herdados de PUBLIC. A allowlist replica os GRANTs de 10_...sql.
WITH target_roles(role_name) AS (
    VALUES ('deepfarms_runtime'),('deepfarms_auth'),('deepfarms_auth_fn_owner'),('deepfarms_notification_fn_owner')
), target_tables(table_name) AS (
    VALUES ('tenants'),('usuarios'),('tenant_usuarios'),('perfis_acesso'),
          ('unidade_produtiva_usuarios'),('assinaturas_tenant'),('planos_assinatura'),
          ('unidades_produtivas'),('configuracoes_saas'),('configuracoes_tenant'),
          ('sessoes_ativas'),('login_tentativas'),('notificacoes'),
          ('notificacoes_leituras'),('notificacoes_preferencias'),('tenant_audit_log')
), privileges(privilege_name) AS (
    VALUES ('SELECT'),('INSERT'),('UPDATE'),('REFERENCES')
), effective AS (
    SELECT r.role_name, t.table_name, a.attname AS column_name, p.privilege_name,
           has_column_privilege(r.role_name,format('farms.%I',t.table_name),a.attname,p.privilege_name) AS granted
    FROM target_roles r
    CROSS JOIN target_tables t
    JOIN pg_class c ON c.relname=t.table_name
    JOIN pg_namespace n ON n.oid=c.relnamespace AND n.nspname='farms'
    JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
    CROSS JOIN privileges p
), checks AS (
    SELECT *, CASE
      WHEN role_name='deepfarms_runtime' AND privilege_name='SELECT'
        AND table_name IN ('tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios','notificacoes') THEN true
      WHEN role_name='deepfarms_runtime' AND privilege_name='INSERT'
        AND table_name IN ('notificacoes','tenant_audit_log') THEN true
      WHEN role_name='deepfarms_auth' AND table_name='login_tentativas'
        AND privilege_name IN ('SELECT','INSERT','UPDATE') THEN true
      WHEN role_name='deepfarms_auth_fn_owner' AND table_name='usuarios'
        AND privilege_name='SELECT'
        AND column_name IN ('id','email','username','senha_hash','is_superuser','ativo') THEN true
      WHEN role_name='deepfarms_notification_fn_owner' AND privilege_name='SELECT' AND (
        (table_name='notificacoes' AND column_name IN ('id','tenant_id','tipo','nivel')) OR
        (table_name='tenant_usuarios' AND column_name IN ('tenant_id','usuario_id','status')) OR
        (table_name='usuarios' AND column_name IN ('id','email')) OR
        (table_name='notificacoes_preferencias' AND column_name IN ('tenant_id','usuario_id','tipo','email_ativo','nivel_sensibilidade'))
      ) THEN true
      WHEN role_name='deepfarms_notification_fn_owner' AND privilege_name='UPDATE'
        AND table_name='notificacoes' AND column_name='mensagem' THEN true
      WHEN role_name='deepfarms_runtime' AND privilege_name='SELECT' AND (
        (table_name='usuarios' AND column_name IN ('id','ativo')) OR
        (table_name='assinaturas_tenant' AND column_name IN ('tenant_id','plano_id','status','usuarios_contratados')) OR
        (table_name='planos_assinatura' AND column_name IN ('id','modulos_inclusos','plan_tier','max_fazendas')) OR
        (table_name='unidades_produtivas' AND column_name IN ('id','nome','tenant_id','ativo')) OR
        (table_name='configuracoes_tenant' AND column_name IN ('tenant_id','categoria','chave','ativo','valor')) OR
        (table_name='configuracoes_saas' AND column_name IN ('chave','valor','ativo')) OR
        (table_name='sessoes_ativas' AND column_name IN ('token_hash','status','expira_em')) OR
        (table_name='notificacoes_leituras' AND column_name IN ('tenant_id','notificacao_id','usuario_id','lida','acao')) OR
        (table_name='notificacoes_preferencias' AND column_name IN ('tenant_id','usuario_id','tipo','sistema_ativo'))
      ) THEN true
      WHEN role_name='deepfarms_runtime' AND privilege_name='INSERT' AND table_name='sessoes_ativas'
        AND column_name IN ('id','tenant_id','usuario_id','unidade_produtiva_id','token_hash','ip_address','user_agent','inicio','ultimo_heartbeat','expira_em','status') THEN true
      WHEN role_name='deepfarms_runtime' AND privilege_name='UPDATE'
        AND table_name='sessoes_ativas' AND column_name='status' THEN true
      ELSE false
    END AS allowed
    FROM effective
)
SELECT role_name,table_name,column_name,privilege_name
FROM checks WHERE granted AND NOT allowed
ORDER BY role_name,table_name,column_name,privilege_name;

SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname='farms'
  AND policyname LIKE '%_deepfarms_%'
ORDER BY tablename, policyname;

SELECT p.oid::regprocedure AS function,
       pg_get_userbyid(p.proowner) AS owner,
       p.prosecdef AS security_definer,
       p.proconfig AS function_settings,
       EXISTS (
           SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
           WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
       ) AS public_execute,
       has_function_privilege('deepfarms_runtime',p.oid,'EXECUTE') AS runtime_execute,
       has_function_privilege('deepfarms_auth',p.oid,'EXECUTE') AS auth_execute,
       has_column_privilege('deepfarms_runtime','farms.usuarios','id','SELECT') AS runtime_user_id_select,
       has_column_privilege('deepfarms_runtime','farms.usuarios','senha_hash','SELECT') AS runtime_hash_select,
       has_table_privilege('deepfarms_auth','farms.usuarios','SELECT') AS auth_user_table_select,
       has_table_privilege('deepfarms_auth','farms.tenant_usuarios','SELECT') AS auth_membership_table_select,
       has_table_privilege('deepfarms_auth','farms.configuracoes_tenant','SELECT') AS auth_tenant_config_table_select,
       has_column_privilege('deepfarms_auth_fn_owner','farms.usuarios','senha_hash','SELECT') AS function_owner_hash_select,
       has_column_privilege('deepfarms_runtime','farms.configuracoes_tenant','valor','SELECT') AS runtime_tenant_config_select,
       has_column_privilege('deepfarms_auth_fn_owner','farms.tenant_usuarios','tenant_id','SELECT') AS function_owner_membership_select,
       has_column_privilege('deepfarms_auth_fn_owner','farms.configuracoes_tenant','valor','SELECT') AS function_owner_rate_config_select,
       has_table_privilege('deepfarms_auth','farms.login_tentativas','INSERT') AS auth_rate_limit_insert
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid=p.pronamespace
WHERE n.nspname='farms' AND p.proname='auth_login_material';

SELECT p.oid::regprocedure AS function,
       pg_get_userbyid(p.proowner) AS owner,
       p.prosecdef AS security_definer,
       p.proconfig AS function_settings,
       EXISTS (
           SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
           WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
       ) AS public_execute,
       has_function_privilege('deepfarms_runtime',p.oid,'EXECUTE') AS runtime_execute,
       has_function_privilege('deepfarms_auth',p.oid,'EXECUTE') AS auth_execute,
       has_column_privilege('deepfarms_runtime','farms.notificacoes','mensagem','UPDATE') AS runtime_message_update,
       has_column_privilege('deepfarms_runtime','farms.usuarios','email','SELECT') AS runtime_user_email_select,
       has_column_privilege('deepfarms_notification_fn_owner','farms.notificacoes','mensagem','UPDATE') AS function_owner_message_update
FROM pg_proc AS p
JOIN pg_namespace AS n ON n.oid=p.pronamespace
WHERE n.nspname='farms'
  AND p.proname IN ('update_notification_message','notification_recipient_emails')
ORDER BY p.proname;

-- Deve retornar zero linhas: o schema farms não pode oferecer outra função
-- SECURITY DEFINER com EXECUTE para PUBLIC aos roles da canário.
SELECT p.oid::regprocedure AS unexpected_public_security_definer
FROM pg_proc p
JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='farms' AND p.prosecdef
  AND EXISTS (
      SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
      WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
  )
ORDER BY 1;
COMMIT;
