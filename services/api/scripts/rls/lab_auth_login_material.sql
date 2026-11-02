-- Lab-only pre-auth lookup. Run only in deepfarms_rls_lab as the deploy role
-- after verifying current_database(), then SET ROLE deepfarms_rls_lab_owner.
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
    SELECT u.id,
           u.email,
           u.username,
           u.senha_hash,
           u.is_superuser,
           u.ativo
    FROM farms.usuarios u
    WHERE lower(btrim(u.email)) = lower(btrim(p_email));
$function$;

ALTER FUNCTION farms.auth_login_material(text) OWNER TO deepfarms_rls_lab_owner;
REVOKE ALL ON FUNCTION farms.auth_login_material(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION farms.auth_login_material(text) FROM deepfarms_rls_lab_runtime;
GRANT USAGE ON SCHEMA farms TO deepfarms_rls_lab_auth;
GRANT EXECUTE ON FUNCTION farms.auth_login_material(text) TO deepfarms_rls_lab_auth;
