-- Preparação de roles para ativação controlada em farms.
-- NÃO executar sem autorização e janela de manutenção.
-- Executar como administrador PostgreSQL; não contém senhas.
\set ON_ERROR_STOP on

BEGIN;

DO $roles$
DECLARE
    is_super boolean;
    target_role_count integer;
BEGIN
    IF current_database() <> 'farms' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado farms, encontrado %', current_database();
    END IF;

    SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname = current_user;
    IF NOT coalesce(is_super, false) THEN
        RAISE EXCEPTION 'Provisionamento de roles requer sessão administrativa PostgreSQL';
    END IF;

    SELECT count(*) INTO target_role_count FROM pg_roles
    WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner');

    IF target_role_count = 0 THEN
        EXECUTE 'CREATE ROLE deepfarms_runtime LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 32';
        EXECUTE 'COMMENT ON ROLE deepfarms_runtime IS ''deepfarms:dev_activation_login_notifications:v1''';
        EXECUTE 'CREATE ROLE deepfarms_auth LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 8';
        EXECUTE 'COMMENT ON ROLE deepfarms_auth IS ''deepfarms:dev_activation_login_notifications:v1''';
        EXECUTE 'CREATE ROLE deepfarms_auth_fn_owner NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION';
        EXECUTE 'COMMENT ON ROLE deepfarms_auth_fn_owner IS ''deepfarms:dev_activation_login_notifications:v1''';
    ELSIF target_role_count = 3 AND NOT EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
          AND (
              shobj_description(oid,'pg_authid') IS DISTINCT FROM 'deepfarms:dev_activation_login_notifications:v1'
              OR rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication
              OR rolinherit
              OR (rolname IN ('deepfarms_runtime','deepfarms_auth') AND NOT rolcanlogin)
              OR (rolname='deepfarms_runtime' AND rolconnlimit<>32)
              OR (rolname='deepfarms_auth' AND rolconnlimit<>8)
              OR (rolname='deepfarms_auth_fn_owner' AND (rolcanlogin OR rolconnlimit<>-1))
          )
    ) THEN
        NULL; -- Reexecução segura das roles marcadas e com atributos esperados.
    ELSE
        RAISE EXCEPTION 'Roles preexistentes, parciais ou incompatíveis; revisão manual necessária';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid = m.member
        JOIN pg_roles granted_role ON granted_role.oid = m.roleid
        WHERE member_role.rolname IN (
            'deepfarms_runtime', 'deepfarms_auth', 'deepfarms_auth_fn_owner'
        )
        OR granted_role.rolname IN (
            'deepfarms_runtime', 'deepfarms_auth', 'deepfarms_auth_fn_owner'
        )
    ) THEN
        RAISE EXCEPTION 'Uma role DeepFarms alvo já tem membership; revisar manualmente antes de continuar';
    END IF;
END
$roles$;

GRANT CONNECT ON DATABASE farms TO deepfarms_runtime, deepfarms_auth;

COMMIT;
