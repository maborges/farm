-- Privilégio mínimo para os efeitos assíncronos das notificações sob RLS.
-- Não aplicar em farms sem autorização operacional específica.
-- Executar como superuser; cria uma role NOLOGIN compartilhada no cluster.
\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $preflight$
DECLARE
    is_super boolean;
    role_exists boolean;
BEGIN
    IF current_database() <> 'farms' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado farms, encontrado %', current_database();
    END IF;
    SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname=current_user;
    IF NOT coalesce(is_super,false) THEN
        RAISE EXCEPTION 'Instalação exige superuser PostgreSQL para role, policies e grants';
    END IF;
    IF (SELECT count(*) FROM pg_roles WHERE rolname IN (
        'deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner'
    )) <> 3 THEN
        RAISE EXCEPTION 'Pacote base login/notificações não está provisionado';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname IN ('deepfarms_runtime','deepfarms_auth')
          AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit OR NOT rolcanlogin)
    ) OR EXISTS (
        SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid=m.member
        JOIN pg_roles granted_role ON granted_role.oid=m.roleid
        WHERE member_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
           OR granted_role.rolname IN ('deepfarms_runtime','deepfarms_auth','deepfarms_auth_fn_owner')
    ) THEN
        RAISE EXCEPTION 'Role operacional elevada ou membership inesperada no pacote base';
    END IF;
    IF EXISTS (
        SELECT 1 FROM (VALUES
            ('notificacoes'),('tenant_usuarios'),('usuarios'),('notificacoes_preferencias')
        ) AS expected(name)
        WHERE to_regclass(format('farms.%I', expected.name)) IS NULL
    ) THEN
        RAISE EXCEPTION 'Relação obrigatória ausente no schema farms';
    END IF;
    IF EXISTS (
        SELECT 1 FROM (VALUES
            ('notificacoes','id'),('notificacoes','tenant_id'),
            ('notificacoes','tipo'),('notificacoes','nivel'),('notificacoes','mensagem'),
            ('tenant_usuarios','tenant_id'),('tenant_usuarios','usuario_id'),('tenant_usuarios','status'),
            ('usuarios','id'),('usuarios','email'),('notificacoes_preferencias','tenant_id'),
            ('notificacoes_preferencias','usuario_id'),('notificacoes_preferencias','tipo'),
            ('notificacoes_preferencias','email_ativo'),('notificacoes_preferencias','nivel_sensibilidade')
        ) AS expected(table_name,column_name)
        WHERE NOT EXISTS (
            SELECT 1 FROM pg_attribute a
            WHERE a.attrelid=to_regclass(format('farms.%I',expected.table_name))
              AND a.attname=expected.column_name AND a.attnum>0 AND NOT a.attisdropped
        )
    ) THEN
        RAISE EXCEPTION 'Coluna necessária ausente; revisar schema antes de continuar';
    END IF;
    IF EXISTS (
        SELECT 1 FROM (VALUES ('notificacoes'),('tenant_usuarios'),('usuarios'),('notificacoes_preferencias')) expected(name)
        JOIN pg_class c ON c.oid=to_regclass(format('farms.%I',expected.name))
        WHERE NOT c.relrowsecurity OR c.relforcerowsecurity
    ) THEN
        RAISE EXCEPTION 'RLS/ FORCE RLS diverge do baseline esperado nas tabelas do fluxo';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policy p
        JOIN pg_class c ON c.oid=p.polrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname=ANY(ARRAY['notificacoes','tenant_usuarios','usuarios','notificacoes_preferencias'])
          AND p.polname <> ALL(ARRAY[
              'notificacoes_deepfarms_runtime','notificacoes_deepfarms_notification_fn_owner',
              'tenant_usuarios_deepfarms_runtime','tenant_usuarios_deepfarms_auth_fn_owner',
              'tenant_usuarios_deepfarms_notification_fn_owner',
              'usuarios_deepfarms_runtime','usuarios_deepfarms_auth_fn_owner',
              'usuarios_deepfarms_notification_fn_owner',
              'notificacoes_preferencias_deepfarms_runtime',
              'notificacoes_preferencias_deepfarms_notification_fn_owner'
          ])
    ) THEN
        RAISE EXCEPTION 'Policy fora da allowlist nas tabelas das funções; revisão manual requerida';
    END IF;
    IF to_regprocedure('farms.auth_login_material(text)') IS NULL THEN
        RAISE EXCEPTION 'Função base farms.auth_login_material(text) ausente; aplique/verifique o pacote base antes deste adendo';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        WHERE p.oid=to_regprocedure('farms.auth_login_material(text)')
          AND p.prosecdef
          AND pg_get_userbyid(p.proowner)='deepfarms_auth_fn_owner'
          AND NOT has_function_privilege('deepfarms_runtime',p.oid,'EXECUTE')
          AND NOT EXISTS (
              SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
              WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
          )
    ) THEN
        RAISE EXCEPTION 'Função base auth_login_material tem owner/configuração ou ACL incompatível';
    END IF;

    SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner')
    INTO role_exists;
    IF role_exists AND (
        (SELECT shobj_description(oid,'pg_authid') FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner')
            IS DISTINCT FROM 'deepfarms:dev_activation_notification_async:v1'
        OR EXISTS (
            SELECT 1 FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner'
              AND (rolcanlogin OR rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolinherit OR rolreplication)
        )
    ) THEN
        RAISE EXCEPTION 'Role notification_fn_owner existente não pertence ao pacote ou tem atributos incompatíveis';
    END IF;
    IF role_exists AND EXISTS (
        SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid=m.member
        JOIN pg_roles granted_role ON granted_role.oid=m.roleid
        WHERE member_role.rolname='deepfarms_notification_fn_owner'
           OR granted_role.rolname='deepfarms_notification_fn_owner'
    ) THEN
        RAISE EXCEPTION 'Membership inesperado da role notification_fn_owner';
    END IF;
    IF role_exists AND (
        EXISTS (SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname='deepfarms_notification_fn_owner')
        OR EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE n.nspname='farms' AND r.rolname='deepfarms_notification_fn_owner')
        OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='farms' AND r.rolname='deepfarms_notification_fn_owner')
        OR EXISTS (
            SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='farms' AND p.proowner=(SELECT oid FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner')
              AND p.oid NOT IN (
                  coalesce(to_regprocedure('farms.update_notification_message(uuid,text)')::oid,0::oid),
                  coalesce(to_regprocedure('farms.notification_recipient_emails(uuid)')::oid,0::oid)
              )
        )
    ) THEN
        RAISE EXCEPTION 'Role notification_fn_owner possui ownership fora das funções previstas';
    END IF;
    IF to_regprocedure('farms.update_notification_message(uuid,text)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc WHERE oid=to_regprocedure('farms.update_notification_message(uuid,text)')))
           <> 'deepfarms_notification_fn_owner' THEN
        RAISE EXCEPTION 'Função update_notification_message preexistente tem owner inesperado';
    END IF;
    IF to_regprocedure('farms.notification_recipient_emails(uuid)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc WHERE oid=to_regprocedure('farms.notification_recipient_emails(uuid)')))
           <> 'deepfarms_notification_fn_owner' THEN
        RAISE EXCEPTION 'Função notification_recipient_emails preexistente tem owner inesperado';
    END IF;
END
$preflight$;

DO $create_role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner') THEN
        EXECUTE 'CREATE ROLE deepfarms_notification_fn_owner NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION';
        EXECUTE 'COMMENT ON ROLE deepfarms_notification_fn_owner IS ''deepfarms:dev_activation_notification_async:v1''';
    END IF;
END
$create_role$;

GRANT USAGE ON SCHEMA farms TO deepfarms_notification_fn_owner;
REVOKE CREATE ON SCHEMA farms FROM deepfarms_notification_fn_owner;
REVOKE ALL PRIVILEGES ON TABLE
    farms.notificacoes, farms.tenant_usuarios, farms.usuarios,
    farms.notificacoes_preferencias
FROM deepfarms_notification_fn_owner;
DO $revoke_old_column_grants$
DECLARE
    target record;
    column_list text;
BEGIN
    FOR target IN
        SELECT c.oid, n.nspname, c.relname
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND c.relname=ANY(ARRAY['notificacoes','tenant_usuarios','usuarios','notificacoes_preferencias'])
    LOOP
        SELECT string_agg(quote_ident(a.attname), ',') INTO column_list
        FROM pg_attribute a
        WHERE a.attrelid=target.oid AND a.attnum>0 AND NOT a.attisdropped;
        IF column_list IS NOT NULL THEN
            EXECUTE format('REVOKE ALL PRIVILEGES (%s) ON TABLE %I.%I FROM %I',
                column_list,target.nspname,target.relname,'deepfarms_notification_fn_owner');
        END IF;
    END LOOP;
END
$revoke_old_column_grants$;
GRANT SELECT (id,tenant_id,tipo,nivel), UPDATE (mensagem)
    ON farms.notificacoes TO deepfarms_notification_fn_owner;
GRANT SELECT (tenant_id,usuario_id,status)
    ON farms.tenant_usuarios TO deepfarms_notification_fn_owner;
GRANT SELECT (id,email)
    ON farms.usuarios TO deepfarms_notification_fn_owner;
GRANT SELECT (tenant_id,usuario_id,tipo,email_ativo,nivel_sensibilidade)
    ON farms.notificacoes_preferencias TO deepfarms_notification_fn_owner;

DROP POLICY IF EXISTS notificacoes_deepfarms_notification_fn_owner ON farms.notificacoes;
DROP POLICY IF EXISTS tenant_usuarios_deepfarms_notification_fn_owner ON farms.tenant_usuarios;
DROP POLICY IF EXISTS usuarios_deepfarms_notification_fn_owner ON farms.usuarios;
DROP POLICY IF EXISTS notificacoes_preferencias_deepfarms_notification_fn_owner ON farms.notificacoes_preferencias;

CREATE POLICY notificacoes_deepfarms_notification_fn_owner ON farms.notificacoes
    FOR ALL TO deepfarms_notification_fn_owner
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND (nivel IN ('WARNING','DANGER') OR tipo='OPORTUNIDADE')
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND (nivel IN ('WARNING','DANGER') OR tipo='OPORTUNIDADE')
    );
CREATE POLICY tenant_usuarios_deepfarms_notification_fn_owner ON farms.tenant_usuarios
    FOR SELECT TO deepfarms_notification_fn_owner
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        AND status='ATIVO'
    );
CREATE POLICY usuarios_deepfarms_notification_fn_owner ON farms.usuarios
    FOR SELECT TO deepfarms_notification_fn_owner
    USING (EXISTS (
        SELECT 1 FROM farms.tenant_usuarios tu
        WHERE tu.tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
          AND tu.usuario_id = usuarios.id
          AND tu.status='ATIVO'
    ));
CREATE POLICY notificacoes_preferencias_deepfarms_notification_fn_owner ON farms.notificacoes_preferencias
    FOR SELECT TO deepfarms_notification_fn_owner
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

GRANT CREATE ON SCHEMA farms TO deepfarms_notification_fn_owner;
DROP FUNCTION IF EXISTS farms.update_notification_message(uuid,text);
CREATE FUNCTION farms.update_notification_message(p_notification_id uuid, p_message text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
SET row_security = on
AS $function$
DECLARE
    v_tenant_id uuid := NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
    v_user_id uuid := NULLIF(current_setting('app.current_user_id', true), '')::uuid;
    v_rows integer;
BEGIN
    IF v_tenant_id IS NULL OR v_user_id IS NULL OR p_message IS NULL OR length(p_message) > 1000 THEN
        RETURN false;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM farms.tenant_usuarios tu
        WHERE tu.tenant_id=v_tenant_id AND tu.usuario_id=v_user_id AND tu.status='ATIVO'
    ) THEN
        RETURN false;
    END IF;
    UPDATE farms.notificacoes n
       SET mensagem=p_message
     WHERE n.id=p_notification_id
       AND n.tenant_id=v_tenant_id
       AND (n.nivel IN ('WARNING','DANGER') OR n.tipo='OPORTUNIDADE');
    GET DIAGNOSTICS v_rows = ROW_COUNT;
    RETURN v_rows = 1;
END
$function$;
ALTER FUNCTION farms.update_notification_message(uuid,text) OWNER TO deepfarms_notification_fn_owner;

DROP FUNCTION IF EXISTS farms.notification_recipient_emails(uuid);
CREATE FUNCTION farms.notification_recipient_emails(p_notification_id uuid)
RETURNS TABLE(email text)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
SET row_security = on
AS $function$
DECLARE
    v_tenant_id uuid := NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
    v_user_id uuid := NULLIF(current_setting('app.current_user_id', true), '')::uuid;
BEGIN
    IF v_tenant_id IS NULL OR v_user_id IS NULL THEN
        RETURN;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM farms.tenant_usuarios tu
        WHERE tu.tenant_id=v_tenant_id AND tu.usuario_id=v_user_id AND tu.status='ATIVO'
    ) THEN
        RETURN;
    END IF;
    RETURN QUERY
    SELECT u.email::text
    FROM farms.notificacoes n
    JOIN farms.tenant_usuarios tu
      ON tu.tenant_id=n.tenant_id AND tu.status='ATIVO'
    JOIN farms.usuarios u ON u.id=tu.usuario_id
    LEFT JOIN farms.notificacoes_preferencias pref
      ON pref.tenant_id=tu.tenant_id AND pref.usuario_id=tu.usuario_id AND pref.tipo=n.tipo
    WHERE n.id=p_notification_id
      AND n.tenant_id=v_tenant_id
      AND (n.nivel IN ('WARNING','DANGER') OR n.tipo='OPORTUNIDADE')
      AND coalesce(pref.email_ativo,true)
      AND CASE coalesce(pref.nivel_sensibilidade,'ALTO')
          WHEN 'MEDIO' THEN n.nivel IN ('WARNING','DANGER')
          WHEN 'BAIXO' THEN n.nivel='DANGER'
          ELSE true
      END;
END
$function$;
ALTER FUNCTION farms.notification_recipient_emails(uuid) OWNER TO deepfarms_notification_fn_owner;
REVOKE CREATE ON SCHEMA farms FROM deepfarms_notification_fn_owner;

REVOKE ALL ON FUNCTION farms.update_notification_message(uuid,text) FROM PUBLIC, deepfarms_runtime, deepfarms_auth;
REVOKE ALL ON FUNCTION farms.notification_recipient_emails(uuid) FROM PUBLIC, deepfarms_runtime, deepfarms_auth;
GRANT EXECUTE ON FUNCTION farms.update_notification_message(uuid,text) TO deepfarms_runtime;
GRANT EXECUTE ON FUNCTION farms.notification_recipient_emails(uuid) TO deepfarms_runtime;

DO $postflight$
BEGIN
    IF has_column_privilege('deepfarms_runtime','farms.notificacoes','mensagem','UPDATE')
       OR has_column_privilege('deepfarms_runtime','farms.usuarios','email','SELECT')
       OR has_table_privilege('deepfarms_runtime','farms.usuarios','SELECT')
       OR has_function_privilege('deepfarms_auth','farms.update_notification_message(uuid,text)','EXECUTE')
       OR has_function_privilege('deepfarms_auth','farms.notification_recipient_emails(uuid)','EXECUTE')
       OR has_function_privilege('deepfarms_runtime','farms.auth_login_material(text)','EXECUTE')
       OR NOT has_function_privilege('deepfarms_runtime','farms.update_notification_message(uuid,text)','EXECUTE')
       OR NOT has_function_privilege('deepfarms_runtime','farms.notification_recipient_emails(uuid)','EXECUTE')
       OR EXISTS (
           SELECT 1 FROM pg_proc p
           CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) acl
           WHERE p.oid IN (
               'farms.update_notification_message(uuid,text)'::regprocedure,
               'farms.notification_recipient_emails(uuid)'::regprocedure
           ) AND acl.grantee=0 AND acl.privilege_type='EXECUTE'
       ) THEN
        RAISE EXCEPTION 'Postflight de privilégio mínimo falhou';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        WHERE p.oid IN (
            'farms.update_notification_message(uuid,text)'::regprocedure,
            'farms.notification_recipient_emails(uuid)'::regprocedure
        )
        AND (NOT p.prosecdef OR pg_get_userbyid(p.proowner)<>'deepfarms_notification_fn_owner'
             OR NOT ('search_path=pg_catalog, pg_temp'=ANY(p.proconfig))
             OR NOT ('row_security=on'=ANY(p.proconfig)))
    ) THEN
        RAISE EXCEPTION 'Owner ou configuração SECURITY DEFINER diverge do contrato';
    END IF;
END
$postflight$;

COMMIT;
