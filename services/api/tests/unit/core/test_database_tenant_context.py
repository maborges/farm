from unittest.mock import MagicMock

import pytest

from core.database import _assert_restricted_database_role, apply_tenant_context_after_begin


def test_after_begin_sets_parameterized_transaction_local_context():
    session = MagicMock(info={"tenant_id": "tenant-a"})
    connection = MagicMock()
    connection.dialect.name = "postgresql"

    apply_tenant_context_after_begin(session, MagicMock(), connection)

    statement, params = connection.execute.call_args.args
    assert "set_config('app.current_tenant_id', :tenant_id, true)" in str(statement)
    assert params == {"tenant_id": "tenant-a"}


def test_after_begin_sets_authenticated_user_before_tenant_context():
    session = MagicMock(info={"user_id": "user-a", "tenant_id": "tenant-a"})
    connection = MagicMock()
    connection.dialect.name = "postgresql"

    apply_tenant_context_after_begin(session, MagicMock(), connection)

    assert connection.execute.call_count == 2
    user_statement, user_params = connection.execute.call_args_list[0].args
    tenant_statement, tenant_params = connection.execute.call_args_list[1].args
    assert "app.current_user_id" in str(user_statement)
    assert user_params == {"user_id": "user-a"}
    assert "app.current_tenant_id" in str(tenant_statement)
    assert tenant_params == {"tenant_id": "tenant-a"}


def test_after_begin_leaves_sessions_without_tenant_untouched():
    session = MagicMock(info={})
    connection = MagicMock()
    connection.dialect.name = "postgresql"

    apply_tenant_context_after_begin(session, MagicMock(), connection)

    connection.execute.assert_not_called()


def test_after_begin_is_noop_for_non_postgresql_connections():
    session = MagicMock(info={"tenant_id": "tenant-a"})
    connection = MagicMock()
    connection.dialect.name = "sqlite"

    apply_tenant_context_after_begin(session, MagicMock(), connection)

    connection.execute.assert_not_called()


def test_restricted_database_role_accepts_non_elevated_non_owner_identity():
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        "app_runtime",
        "app_runtime",
        False,
        False,
        False,
        False,
        False,
    )
    connection = MagicMock()
    connection.cursor.return_value = cursor

    _assert_restricted_database_role(connection)

    assert "pg_auth_members" in cursor.execute.call_args.args[0]
    assert "pg_class" in cursor.execute.call_args.args[0]
    cursor.close.assert_called_once()


def test_restricted_database_role_rejects_elevation_and_owner():
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        "app_runtime",
        "app_runtime",
        False,
        True,
        False,
        False,
        False,
    )
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with pytest.raises(RuntimeError, match="without memberships or ownership"):
        _assert_restricted_database_role(connection)

    cursor.close.assert_called_once()


def test_restricted_database_role_rejects_set_role_identity_mismatch():
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        "elevated_role",
        "app_runtime",
        False,
        False,
        False,
        False,
        False,
    )
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with pytest.raises(RuntimeError, match="without memberships or ownership"):
        _assert_restricted_database_role(connection)
