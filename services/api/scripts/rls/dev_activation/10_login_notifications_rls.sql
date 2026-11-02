-- Grants e policies mínimos para login + notificações no banco farms.
-- NÃO executar sem autorização, ambiente parado e roles provisionadas.
-- Conectar como administrador PostgreSQL. A transação torna o conjunto atômico.
\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $preflight$
DECLARE
    is_super boolean;
    expected_tables text[] := ARRAY[
        'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
        'assinaturas_tenant','planos_assinatura','unidades_produtivas',
        'configuracoes_saas','configuracoes_tenant','sessoes_ativas',
        'login_tentativas','notificacoes','notificacoes_leituras',
        'notificacoes_preferencias','tenant_audit_log','tenants'
    ];
BEGIN
    IF current_database() <> 'farms' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado farms, encontrado %', current_database();
    END IF;
    SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname = current_user;
    IF NOT coalesce(is_super, false) THEN
        RAISE EXCEPTION 'Aplicação requer administrador PostgreSQL para alterar owners, grants e RLS';
    END IF;
    IF EXISTS (
        SELECT 1 FROM unnest(expected_tables) x(name)
        WHERE to_regclass(format('farms.%I', x.name)) IS NULL
    ) THEN
        RAISE EXCEPTION 'Tabela necessária ausente no schema farms';
    END IF;
    IF (SELECT count(*) FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')) <> 3 THEN
        RAISE EXCEPTION 'Execute 00_roles.sql primeiro';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
          AND shobj_description(oid,'pg_authid') IS DISTINCT FROM
              'deepfarms:dev_activation_login_notifications:v1'
    ) THEN
        RAISE EXCEPTION 'Role sem marcador de provisionamento deste pacote; revisão manual necessária';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid = m.member
        JOIN pg_roles granted_role ON granted_role.oid = m.roleid
        WHERE member_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
           OR granted_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) THEN
        RAISE EXCEPTION 'Role alvo tem membership inesperado';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth')
          AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit OR NOT rolcanlogin)
    ) OR EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname='deepfarms_auth_fn_owner'
          AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit OR rolcanlogin)
    ) THEN
        RAISE EXCEPTION 'Atributos de role incompatíveis com o contrato mínimo';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles r
        JOIN pg_database d ON d.datdba=r.oid
        WHERE r.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) OR EXISTS (
        SELECT 1 FROM pg_roles r
        JOIN pg_namespace n ON n.nspowner=r.oid
        WHERE r.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) OR EXISTS (
        SELECT 1 FROM pg_roles r
        JOIN pg_class c ON c.relowner=r.oid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND r.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) OR EXISTS (
        SELECT 1 FROM pg_roles r
        JOIN pg_proc p ON p.proowner=r.oid
        JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='farms'
          AND r.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) THEN
        RAISE EXCEPTION 'Role alvo possui ownership de banco, schema, relação ou função em farms';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM pg_policy p
        JOIN pg_class c ON c.oid = p.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'farms'
          AND c.relname = ANY(ARRAY[
              'usuarios','tenant_usuarios','perfis_acesso','unidade_produtiva_usuarios',
              'assinaturas_tenant','unidades_produtivas','configuracoes_saas',
              'configuracoes_tenant','sessoes_ativas','login_tentativas',
              'notificacoes','notificacoes_leituras','notificacoes_preferencias',
              'tenant_audit_log'
          ])
          AND p.polname <> ALL(ARRAY[
              'usuarios_deepfarms_runtime','usuarios_deepfarms_auth_fn_owner',
              'tenant_usuarios_deepfarms_runtime','tenant_usuarios_deepfarms_auth_fn_owner',
              'perfis_acesso_deepfarms_runtime','unidade_produtiva_usuarios_deepfarms_runtime',
              'assinaturas_tenant_deepfarms_runtime','unidades_produtivas_deepfarms_runtime',
              'configuracoes_saas_deepfarms_runtime','configuracoes_tenant_deepfarms_runtime',
              'configuracoes_tenant_deepfarms_auth_fn_owner',
              'sessoes_ativas_deepfarms_runtime','login_tentativas_deepfarms_auth',
              'notificacoes_deepfarms_runtime','notificacoes_leituras_deepfarms_runtime',
              'notificacoes_preferencias_deepfarms_runtime','tenant_audit_log_deepfarms_runtime',
              'notificacoes_deepfarms_notification_fn_owner',
              'tenant_usuarios_deepfarms_notification_fn_owner',
              'usuarios_deepfarms_notification_fn_owner',
              'notificacoes_preferencias_deepfarms_notification_fn_owner'
          ])
    ) THEN
        RAISE EXCEPTION 'Policy não pertencente a este script encontrada; revisar antes de alterar RLS';
    END IF;
    IF to_regprocedure('farms.auth_login_material(text)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc
                            WHERE oid=to_regprocedure('farms.auth_login_material(text)')))
           <> 'deepfarms_auth_fn_owner' THEN
        RAISE EXCEPTION 'Função com mesmo nome já existe com owner diferente; revisão manual necessária';
    END IF;
END
$preflight$;

GRANT USAGE ON SCHEMA farms TO deepfarms_runtime, deepfarms_auth, deepfarms_auth_fn_owner;

-- Remove somente grants anteriores das identidades dedicadas nestas tabelas.
REVOKE ALL PRIVILEGES ON TABLE
    farms.tenants, farms.usuarios, farms.tenant_usuarios, farms.perfis_acesso,
    farms.unidade_produtiva_usuarios, farms.assinaturas_tenant,
    farms.planos_assinatura, farms.unidades_produtivas,
    farms.configuracoes_saas, farms.configuracoes_tenant,
    farms.sessoes_ativas, farms.login_tentativas,
    farms.notificacoes, farms.notificacoes_leituras,
    farms.notificacoes_preferencias, farms.tenant_audit_log
FROM deepfarms_runtime, deepfarms_auth, deepfarms_auth_fn_owner;

-- Remove também grants por coluna preexistentes em roles reutilizadas. Essas
-- identidades são dedicadas; em reruns, somente a allowlist abaixo é refeita.
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
REVOKE SELECT (tenant_id,categoria,chave,ativo,valor)
    ON farms.configuracoes_tenant FROM deepfarms_runtime;
REVOKE SELECT (tenant_id,plano_id,status,usuarios_contratados)
    ON farms.assinaturas_tenant FROM deepfarms_runtime;
REVOKE SELECT (id,modulos_inclusos,plan_tier,max_fazendas)
    ON farms.planos_assinatura FROM deepfarms_runtime;
REVOKE SELECT (id,nome,tenant_id,ativo)
    ON farms.unidades_produtivas FROM deepfarms_runtime;
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
REVOKE REFERENCES (id) ON farms.tenants, farms.usuarios,
    farms.unidades_produtivas FROM deepfarms_runtime;

-- As tabelas abaixo contêm dados do fluxo tenant-scoped ou de identidade.
ALTER TABLE farms.usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.usuarios FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_usuarios FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.perfis_acesso ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.perfis_acesso FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.unidade_produtiva_usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.unidade_produtiva_usuarios FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.assinaturas_tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.assinaturas_tenant FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.unidades_produtivas ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.unidades_produtivas FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_saas ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_saas FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.configuracoes_tenant FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.sessoes_ativas ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.sessoes_ativas FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.login_tentativas ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.login_tentativas FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_leituras ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_leituras FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_preferencias ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.notificacoes_preferencias FORCE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.tenant_audit_log FORCE ROW LEVEL SECURITY;

-- A função pre-auth roda como role NOLOGIN e só possui SELECT das colunas
-- explicitamente utilizadas. As policies internas permitem leitura no escopo
-- da função; nenhuma membership é concedida a essa role.
GRANT SELECT (id,email,username,senha_hash,is_superuser,ativo)
    ON farms.usuarios TO deepfarms_auth_fn_owner;

-- Runtime: permissões compatíveis somente com o login pós-bcrypt e notificações.
GRANT SELECT (id,ativo) ON farms.usuarios TO deepfarms_runtime;
GRANT SELECT ON farms.tenant_usuarios, farms.perfis_acesso,
    farms.unidade_produtiva_usuarios TO deepfarms_runtime;
GRANT SELECT (tenant_id,plano_id,status,usuarios_contratados)
    ON farms.assinaturas_tenant TO deepfarms_runtime;
GRANT SELECT (id,modulos_inclusos,plan_tier,max_fazendas)
    ON farms.planos_assinatura TO deepfarms_runtime;
GRANT SELECT (id,nome,tenant_id,ativo)
    ON farms.unidades_produtivas TO deepfarms_runtime;
GRANT SELECT (tenant_id,categoria,chave,ativo,valor)
    ON farms.configuracoes_tenant TO deepfarms_runtime;
GRANT SELECT (chave,valor,ativo)
    ON farms.configuracoes_saas TO deepfarms_runtime;
GRANT SELECT (token_hash,status,expira_em),
      INSERT (id,tenant_id,usuario_id,unidade_produtiva_id,token_hash,ip_address,user_agent,inicio,ultimo_heartbeat,expira_em,status),
      UPDATE (status)
    ON farms.sessoes_ativas TO deepfarms_runtime;
GRANT SELECT, INSERT ON farms.notificacoes TO deepfarms_runtime;
GRANT SELECT (tenant_id,notificacao_id,usuario_id,lida,acao)
    ON farms.notificacoes_leituras TO deepfarms_runtime;
GRANT SELECT (tenant_id,usuario_id,tipo,sistema_ativo)
    ON farms.notificacoes_preferencias TO deepfarms_runtime;
GRANT INSERT ON farms.tenant_audit_log TO deepfarms_runtime;
-- Catálogo de planos é global e somente leitura para runtime. Não recebe RLS;
-- o role não recebe INSERT/UPDATE/DELETE.

-- Rate-limit permanece isolado por email e na identidade auth dedicada.
GRANT SELECT, INSERT, UPDATE ON farms.login_tentativas TO deepfarms_auth;

-- Cada policy do pacote é substituída pelo nome exato para permitir repetição.
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

CREATE POLICY usuarios_deepfarms_runtime ON farms.usuarios
    FOR SELECT TO deepfarms_runtime
    USING (id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
CREATE POLICY usuarios_deepfarms_auth_fn_owner ON farms.usuarios
    FOR SELECT TO deepfarms_auth_fn_owner USING (true);

CREATE POLICY tenant_usuarios_deepfarms_runtime ON farms.tenant_usuarios
    FOR SELECT TO deepfarms_runtime
    USING (usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);

-- Existem vínculos reais a perfis globais (tenant_id NULL); mantê-los legíveis.
CREATE POLICY perfis_acesso_deepfarms_runtime ON farms.perfis_acesso
    FOR SELECT TO deepfarms_runtime
    USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
CREATE POLICY unidade_produtiva_usuarios_deepfarms_runtime ON farms.unidade_produtiva_usuarios
    FOR SELECT TO deepfarms_runtime
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );
CREATE POLICY assinaturas_tenant_deepfarms_runtime ON farms.assinaturas_tenant
    FOR SELECT TO deepfarms_runtime
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
CREATE POLICY unidades_produtivas_deepfarms_runtime ON farms.unidades_produtivas
    FOR SELECT TO deepfarms_runtime
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

-- Só a configuração global necessária para expiração de sessão é legível.
CREATE POLICY configuracoes_saas_deepfarms_runtime ON farms.configuracoes_saas
    FOR SELECT TO deepfarms_runtime USING (chave = 'sessao');
CREATE POLICY configuracoes_tenant_deepfarms_runtime ON farms.configuracoes_tenant
    FOR SELECT TO deepfarms_runtime
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY sessoes_ativas_deepfarms_runtime ON farms.sessoes_ativas
    FOR ALL TO deepfarms_runtime
    USING (usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
    WITH CHECK (usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
CREATE POLICY login_tentativas_deepfarms_auth ON farms.login_tentativas
    FOR ALL TO deepfarms_auth
    USING (lower(email) = NULLIF(current_setting('app.current_login_email', true), ''))
    WITH CHECK (lower(email) = NULLIF(current_setting('app.current_login_email', true), ''));
CREATE POLICY notificacoes_deepfarms_runtime ON farms.notificacoes
    FOR ALL TO deepfarms_runtime
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
CREATE POLICY notificacoes_leituras_deepfarms_runtime ON farms.notificacoes_leituras
    FOR SELECT TO deepfarms_runtime
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );
CREATE POLICY notificacoes_preferencias_deepfarms_runtime ON farms.notificacoes_preferencias
    FOR SELECT TO deepfarms_runtime
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND usuario_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
    );
CREATE POLICY tenant_audit_log_deepfarms_runtime ON farms.tenant_audit_log
    FOR INSERT TO deepfarms_runtime
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

-- A função é criada pelo administrador, transferida ao owner dedicado e
-- EXECUTE é concedido exclusivamente ao serviço auth.
GRANT CREATE ON SCHEMA farms TO deepfarms_auth_fn_owner;
DROP FUNCTION IF EXISTS farms.auth_login_material(text);
CREATE FUNCTION farms.auth_login_material(p_email text)
RETURNS TABLE (
    usuario_id uuid,
    email text,
    username text,
    senha_hash text,
    is_superuser boolean,
    ativo boolean
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
SET row_security = on
AS $function$
    SELECT u.id, u.email, u.username, u.senha_hash, u.is_superuser, u.ativo
    FROM farms.usuarios AS u
    WHERE lower(btrim(u.email)) = lower(btrim(p_email));
$function$;
ALTER FUNCTION farms.auth_login_material(text) OWNER TO deepfarms_auth_fn_owner;
REVOKE CREATE ON SCHEMA farms FROM deepfarms_auth_fn_owner;
REVOKE ALL ON FUNCTION farms.auth_login_material(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION farms.auth_login_material(text) FROM deepfarms_runtime;
GRANT EXECUTE ON FUNCTION farms.auth_login_material(text) TO deepfarms_auth;

COMMIT;
