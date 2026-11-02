-- Rollback do pacote 10_login_notifications_rls.sql e das roles de 00_roles.sql.
-- Aceita instalação completa ou somente as roles após falha antes do script 10.
-- Parar a API/workers antes. Executar como administrador PostgreSQL após aprovação.
-- Se 30_notification_async_effects.sql tiver sido aplicado, executar primeiro
-- 80_rollback_notification_async_effects.sql; o preflight deste rollback rejeita
-- as policies adicionais para evitar remoção parcial.
\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $preflight$
DECLARE
    is_super boolean;
    expected_policy_names text[] := ARRAY[
        'usuarios_deepfarms_runtime','usuarios_deepfarms_auth_fn_owner',
        'tenant_usuarios_deepfarms_runtime','tenant_usuarios_deepfarms_auth_fn_owner',
        'perfis_acesso_deepfarms_runtime','unidade_produtiva_usuarios_deepfarms_runtime',
        'assinaturas_tenant_deepfarms_runtime','unidades_produtivas_deepfarms_runtime',
        'configuracoes_saas_deepfarms_runtime','configuracoes_tenant_deepfarms_runtime',
        'configuracoes_tenant_deepfarms_auth_fn_owner',
        'sessoes_ativas_deepfarms_runtime','login_tentativas_deepfarms_auth',
        'notificacoes_deepfarms_runtime','notificacoes_leituras_deepfarms_runtime',
        'notificacoes_preferencias_deepfarms_runtime','tenant_audit_log_deepfarms_runtime'
    ];
BEGIN
    IF current_database() <> 'farms' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado farms, encontrado %', current_database();
    END IF;
    SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname=current_user;
    IF NOT coalesce(is_super,false) THEN
        RAISE EXCEPTION 'Rollback requer administrador PostgreSQL';
    END IF;
    IF (SELECT count(*) FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')) <> 3 THEN
        RAISE EXCEPTION 'As três roles do pacote devem existir para executar o rollback';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
          AND shobj_description(oid,'pg_authid') IS DISTINCT FROM
              'deepfarms:dev_activation_login_notifications:v1'
    ) THEN
        RAISE EXCEPTION 'Role não marcada como criada por este pacote; rollback interrompido';
    END IF;
    IF to_regprocedure('farms.auth_login_material(text)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc
                            WHERE oid=to_regprocedure('farms.auth_login_material(text)')))
           <> 'deepfarms_auth_fn_owner' THEN
        RAISE EXCEPTION 'Função auth_login_material tem owner inesperado; rollback interrompido';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid=m.member
        JOIN pg_roles granted_role ON granted_role.oid=m.roleid
        WHERE member_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
           OR granted_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) THEN
        RAISE EXCEPTION 'Membership inesperado das roles; rollback automático interrompido';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policy p
        JOIN pg_class c ON c.oid=p.polrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname IN (
              'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
              'assinaturas_tenant','unidades_produtivas','configuracoes_saas',
              'configuracoes_tenant','sessoes_ativas','login_tentativas',
              'notificacoes','notificacoes_leituras','notificacoes_preferencias',
              'tenant_audit_log'
          )
          AND NOT (p.polname = ANY(expected_policy_names))
    ) THEN
        RAISE EXCEPTION 'Policy adicional encontrada; rollback automático interrompido para preservar alterações alheias';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname = ANY(ARRAY[
              'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
              'assinaturas_tenant','unidades_produtivas','configuracoes_saas',
              'configuracoes_tenant','sessoes_ativas','login_tentativas',
              'notificacoes','notificacoes_leituras','notificacoes_preferencias',
              'tenant_audit_log'
          ]) AND c.relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'FORCE RLS inesperado; rollback interrompido para revisão manual';
    END IF;
    IF (
        SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname = ANY(ARRAY[
              'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
              'assinaturas_tenant','unidades_produtivas','configuracoes_saas',
              'configuracoes_tenant','sessoes_ativas','login_tentativas',
              'notificacoes','notificacoes_leituras','notificacoes_preferencias',
              'tenant_audit_log'
          ]) AND c.relrowsecurity
    ) NOT IN (0,14) THEN
        RAISE EXCEPTION 'Estado RLS parcial; rollback interrompido para revisão manual';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname = ANY(ARRAY[
              'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
              'assinaturas_tenant','unidades_produtivas','configuracoes_saas',
              'configuracoes_tenant','sessoes_ativas','login_tentativas',
              'notificacoes','notificacoes_leituras','notificacoes_preferencias',
              'tenant_audit_log'
          ]) AND c.relrowsecurity
    ) AND (
        EXISTS (
            SELECT 1 FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='farms' AND p.polname = ANY(expected_policy_names)
        ) OR to_regprocedure('farms.auth_login_material(text)') IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Objetos do pacote existem sem RLS completo; rollback interrompido';
    END IF;
END
$preflight$;

DROP FUNCTION IF EXISTS farms.auth_login_material(text);

DROP POLICY IF EXISTS usuarios_deepfarms_runtime ON farms.usuarios;
DROP POLICY IF EXISTS usuarios_deepfarms_auth_fn_owner ON farms.usuarios;
DROP POLICY IF EXISTS tenant_usuarios_deepfarms_runtime ON farms.tenant_usuarios;
DROP POLICY IF EXISTS tenant_usuarios_deepfarms_auth_fn_owner ON farms.tenant_usuarios;
DROP POLICY IF EXISTS perfis_acesso_deepfarms_runtime ON farms.perfis_acesso;
DROP POLICY IF EXISTS unidade_produtiva_usuarios_deepfarms_runtime ON farms.unidade_produtiva_usuarios;
DROP POLICY IF EXISTS assinaturas_tenant_deepfarms_runtime ON farms.assinaturas_tenant;
DROP POLICY IF EXISTS unidades_produtivas_deepfarms_runtime ON farms.unidades_produtivas;
DROP POLICY IF EXISTS configuracoes_saas_deepfarms_runtime ON farms.configuracoes_saas;
DROP POLICY IF EXISTS configuracoes_tenant_deepfarms_runtime ON farms.configuracoes_tenant;
DROP POLICY IF EXISTS configuracoes_tenant_deepfarms_auth_fn_owner ON farms.configuracoes_tenant;
DROP POLICY IF EXISTS sessoes_ativas_deepfarms_runtime ON farms.sessoes_ativas;
DROP POLICY IF EXISTS login_tentativas_deepfarms_auth ON farms.login_tentativas;
DROP POLICY IF EXISTS notificacoes_deepfarms_runtime ON farms.notificacoes;
DROP POLICY IF EXISTS notificacoes_leituras_deepfarms_runtime ON farms.notificacoes_leituras;
DROP POLICY IF EXISTS notificacoes_preferencias_deepfarms_runtime ON farms.notificacoes_preferencias;
DROP POLICY IF EXISTS tenant_audit_log_deepfarms_runtime ON farms.tenant_audit_log;

ALTER TABLE farms.usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.usuarios NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_usuarios NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.perfis_acesso DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.perfis_acesso NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.unidade_produtiva_usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.unidade_produtiva_usuarios NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.assinaturas_tenant DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.assinaturas_tenant NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.unidades_produtivas DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.unidades_produtivas NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_saas DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_saas NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_tenant DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_tenant NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.sessoes_ativas DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.sessoes_ativas NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.login_tentativas DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.login_tentativas NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_leituras DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_leituras NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_preferencias DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_preferencias NO FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_audit_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_audit_log NO FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
    farms.tenants, farms.usuarios, farms.tenant_usuarios, farms.perfis_acesso,
    farms.unidade_produtiva_usuarios, farms.assinaturas_tenant,
    farms.planos_assinatura, farms.unidades_produtivas,
    farms.configuracoes_saas, farms.configuracoes_tenant,
    farms.sessoes_ativas, farms.login_tentativas,
    farms.notificacoes, farms.notificacoes_leituras,
    farms.notificacoes_preferencias, farms.tenant_audit_log
FROM deepfarms_runtime, deepfarms_auth, deepfarms_auth_fn_owner;

DO $revoke_column_grants$
DECLARE
    target record;
    column_list text;
BEGIN
    FOR target IN
        SELECT n.nspname, c.relname, c.oid
        FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relkind IN ('r','p')
          AND c.relname = ANY(ARRAY[
              'tenants','usuarios','tenant_usuarios','perfis_acesso',
              'unidade_produtiva_usuarios','assinaturas_tenant','planos_assinatura',
              'unidades_produtivas','configuracoes_saas','configuracoes_tenant',
              'sessoes_ativas','login_tentativas','notificacoes',
              'notificacoes_leituras','notificacoes_preferencias','tenant_audit_log'
          ])
    LOOP
        SELECT string_agg(quote_ident(a.attname), ',')
        INTO column_list
        FROM pg_attribute a
        WHERE a.attrelid=target.oid AND a.attnum>0 AND NOT a.attisdropped;
        IF column_list IS NOT NULL THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES (%s) ON TABLE %I.%I FROM %I, %I, %I',
                column_list, target.nspname, target.relname,
                'deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner'
            );
        END IF;
    END LOOP;
END
$revoke_column_grants$;

REVOKE SELECT (id,ativo) ON farms.usuarios FROM deepfarms_runtime;
REVOKE SELECT (id,email,username,senha_hash,is_superuser,ativo)
    ON farms.usuarios FROM deepfarms_auth_fn_owner;
REVOKE SELECT (usuario_id,tenant_id,status)
    ON farms.tenant_usuarios FROM deepfarms_auth_fn_owner;
REVOKE SELECT (tenant_id,categoria,chave,ativo,valor)
    ON farms.configuracoes_tenant FROM deepfarms_auth_fn_owner;
REVOKE SELECT (tenant_id,plano_id,status,usuarios_contratados)
    ON farms.assinaturas_tenant FROM deepfarms_runtime;
REVOKE SELECT (id,modulos_inclusos,plan_tier,max_fazendas)
    ON farms.planos_assinatura FROM deepfarms_runtime;
REVOKE SELECT (id,nome,tenant_id,ativo)
    ON farms.unidades_produtivas FROM deepfarms_runtime;
REVOKE SELECT (tenant_id,categoria,chave,ativo,valor)
    ON farms.configuracoes_tenant FROM deepfarms_runtime;
REVOKE SELECT (chave,valor,ativo)
    ON farms.configuracoes_saas FROM deepfarms_runtime;
REVOKE SELECT (token_hash,status,expira_em),
       INSERT (id,tenant_id,usuario_id,unidade_produtiva_id,token_hash,ip_address,user_agent,inicio,ultimo_heartbeat,expira_em,status),
       UPDATE (status)
    ON farms.sessoes_ativas FROM deepfarms_runtime;
REVOKE SELECT (tenant_id,notificacao_id,usuario_id,lida,acao)
    ON farms.notificacoes_leituras FROM deepfarms_runtime;
REVOKE SELECT (tenant_id,usuario_id,tipo,sistema_ativo)
    ON farms.notificacoes_preferencias FROM deepfarms_runtime;
REVOKE CREATE, USAGE ON SCHEMA farms
    FROM deepfarms_runtime, deepfarms_auth, deepfarms_auth_fn_owner;
REVOKE CONNECT ON DATABASE farms FROM deepfarms_runtime, deepfarms_auth;

DROP ROLE IF EXISTS deepfarms_runtime;
DROP ROLE IF EXISTS deepfarms_auth;
DROP ROLE IF EXISTS deepfarms_auth_fn_owner;

COMMIT;
