-- Remove somente os efeitos assíncronos instalados por 30_notification_async_effects.sql.
-- Executar como superuser depois de parar a canário e remover o roteamento.
\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $preflight$
DECLARE
    is_super boolean;
BEGIN
    IF current_database() <> 'farms' THEN
        RAISE EXCEPTION 'Banco incorreto: esperado farms, encontrado %', current_database();
    END IF;
    SELECT rolsuper INTO is_super FROM pg_roles WHERE rolname=current_user;
    IF NOT coalesce(is_super,false) THEN
        RAISE EXCEPTION 'Rollback requer superuser PostgreSQL';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner'
          AND shobj_description(oid,'pg_authid')='deepfarms:dev_activation_notification_async:v1'
          AND NOT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls
    ) THEN
        RAISE EXCEPTION 'Role do pacote ausente ou incompatível; rollback interrompido';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member_role ON member_role.oid=m.member
        JOIN pg_roles granted_role ON granted_role.oid=m.roleid
        WHERE member_role.rolname='deepfarms_notification_fn_owner'
           OR granted_role.rolname='deepfarms_notification_fn_owner'
    ) THEN
        RAISE EXCEPTION 'Membership inesperado; não remover role automaticamente';
    END IF;
    IF to_regprocedure('farms.update_notification_message(uuid,text)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc WHERE oid=to_regprocedure('farms.update_notification_message(uuid,text)')))
           <> 'deepfarms_notification_fn_owner' THEN
        RAISE EXCEPTION 'Owner inesperado em update_notification_message';
    END IF;
    IF to_regprocedure('farms.notification_recipient_emails(uuid)') IS NOT NULL
       AND pg_get_userbyid((SELECT proowner FROM pg_proc WHERE oid=to_regprocedure('farms.notification_recipient_emails(uuid)')))
           <> 'deepfarms_notification_fn_owner' THEN
        RAISE EXCEPTION 'Owner inesperado em notification_recipient_emails';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policy p
        JOIN pg_class c ON c.oid=p.polrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='farms'
          AND p.polname = ANY(ARRAY[
              'notificacoes_deepfarms_notification_fn_owner',
              'tenant_usuarios_deepfarms_notification_fn_owner',
              'usuarios_deepfarms_notification_fn_owner',
              'notificacoes_preferencias_deepfarms_notification_fn_owner'
          ])
          AND p.polroles <> ARRAY[(SELECT oid FROM pg_roles WHERE rolname='deepfarms_notification_fn_owner')]
    ) THEN
        RAISE EXCEPTION 'Policy com nome do pacote tem role inesperada; rollback interrompido';
    END IF;
END
$preflight$;

REVOKE ALL ON FUNCTION farms.update_notification_message(uuid,text) FROM PUBLIC, deepfarms_runtime, deepfarms_auth;
REVOKE ALL ON FUNCTION farms.notification_recipient_emails(uuid) FROM PUBLIC, deepfarms_runtime, deepfarms_auth;
DROP FUNCTION IF EXISTS farms.update_notification_message(uuid,text);
DROP FUNCTION IF EXISTS farms.notification_recipient_emails(uuid);

DROP POLICY IF EXISTS notificacoes_deepfarms_notification_fn_owner ON farms.notificacoes;
DROP POLICY IF EXISTS tenant_usuarios_deepfarms_notification_fn_owner ON farms.tenant_usuarios;
DROP POLICY IF EXISTS usuarios_deepfarms_notification_fn_owner ON farms.usuarios;
DROP POLICY IF EXISTS notificacoes_preferencias_deepfarms_notification_fn_owner ON farms.notificacoes_preferencias;

REVOKE SELECT (id,tenant_id,tipo,nivel), UPDATE (mensagem)
    ON farms.notificacoes FROM deepfarms_notification_fn_owner;
REVOKE SELECT (tenant_id,usuario_id,status)
    ON farms.tenant_usuarios FROM deepfarms_notification_fn_owner;
REVOKE SELECT (id,email)
    ON farms.usuarios FROM deepfarms_notification_fn_owner;
REVOKE SELECT (tenant_id,usuario_id,tipo,email_ativo,nivel_sensibilidade)
    ON farms.notificacoes_preferencias FROM deepfarms_notification_fn_owner;
REVOKE CREATE, USAGE ON SCHEMA farms FROM deepfarms_notification_fn_owner;

DROP ROLE deepfarms_notification_fn_owner;

COMMIT;
