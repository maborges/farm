"""Contract for installer-internal metadata tables and constraints.

Separates installer-specific tables (manifest, version) from the canonical
ORM baseline contract so that catalog validation can enforce strict boundaries.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import text
from sqlalchemy.engine import Connection

from clean_install import INSTALL_VERSION

INSTALLER_SCHEMA = "farms"
MANIFEST_TABLE = "deepfarms_install_manifest"
VERSION_TABLE = "deepfarms_install_version"
HISTORICAL_EXCLUDED_TABLES = ("alembic_version",)

INSTALLER_TABLES = (MANIFEST_TABLE, VERSION_TABLE)
ALL_EXCLUDED_TABLES = INSTALLER_TABLES + HISTORICAL_EXCLUDED_TABLES

MANIFEST_CHECK_NAME = "ck_deepfarms_install_manifest_singleton"
MANIFEST_CHECK_DEFINITION = "singleton IS TRUE"

MANIFEST_COLUMNS: dict[str, bool] = {
    "singleton": False,
    "install_version": False,
    "baseline_revision": False,
    "baseline_sha256": False,
    "seed_contract_version": False,
    "seed_contract_sha256": False,
    "installed_at": False,
}

MANIFEST_PK_NAME = "deepfarms_install_manifest_pkey"
VERSION_PK_NAME = "deepfarms_install_version_pkc"


def get_installer_check_contract() -> list[tuple[str, str, str, str, str]]:
    """Return installer CHECK constraint specifications.

    Args:
        None.

    Returns:
        List of tuples: (schema, table, name, kind, raw_definition).

    Raises:
        None.
    """
    return [
        (
            INSTALLER_SCHEMA,
            MANIFEST_TABLE,
            MANIFEST_CHECK_NAME,
            "CHECK",
            MANIFEST_CHECK_DEFINITION,
        )
    ]


def validate_manifest_columns(connection: Connection) -> list[str]:
    """Validate deepfarms_install_manifest column names and nullability.

    Args:
        connection: Active SQLAlchemy database connection.

    Returns:
        List of error descriptions, or empty list if valid.

    Raises:
        None.
    """
    rows = connection.execute(
        text("""
            SELECT column_name, is_nullable = 'YES'
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
        """),
        {"schema": INSTALLER_SCHEMA, "table": MANIFEST_TABLE},
    ).all()
    actual_columns = {col_name: is_nullable for col_name, is_nullable in rows}
    errors: list[str] = []
    missing_cols = set(MANIFEST_COLUMNS.keys()) - set(actual_columns.keys())
    if missing_cols:
        errors.append(f"deepfarms_install_manifest missing columns: {sorted(missing_cols)}")
    extra_cols = set(actual_columns.keys()) - set(MANIFEST_COLUMNS.keys())
    if extra_cols:
        errors.append(f"deepfarms_install_manifest unexpected columns: {sorted(extra_cols)}")
    for col_name, expected_nullable in MANIFEST_COLUMNS.items():
        if col_name in actual_columns:
            actual_nullable = actual_columns[col_name]
            if actual_nullable != expected_nullable:
                errors.append(
                    f"deepfarms_install_manifest.{col_name} nullability expected={expected_nullable} "
                    f"actual={actual_nullable}"
                )
    return errors


def validate_manifest_constraints(connection: Connection) -> list[str]:
    """Validate constraints on deepfarms_install_manifest.

    Args:
        connection: Active SQLAlchemy database connection.

    Returns:
        List of error descriptions, or empty list if valid.

    Raises:
        None.
    """
    rows = connection.execute(
        text("""
            SELECT con.conname, con.contype, pg_get_constraintdef(con.oid, false)
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = con.connamespace
            WHERE n.nspname = :schema AND rel.relname = :table
        """),
        {"schema": INSTALLER_SCHEMA, "table": MANIFEST_TABLE},
    ).all()
    errors: list[str] = []
    check_constraints = [r for r in rows if r[1] == "c"]
    pk_constraints = [r for r in rows if r[1] == "p"]

    if not any(r[0] == MANIFEST_CHECK_NAME for r in check_constraints):
        errors.append(
            f"deepfarms_install_manifest missing CHECK constraint {MANIFEST_CHECK_NAME}"
        )
    else:
        for name, _, defn in check_constraints:
            if name == MANIFEST_CHECK_NAME:
                # Canonical definition deparsed by PostgreSQL
                if "singleton IS TRUE" not in defn:
                    errors.append(
                        f"deepfarms_install_manifest {name} definition unexpected: {defn!r}"
                    )

    if not pk_constraints:
        errors.append("deepfarms_install_manifest missing PRIMARY KEY constraint")

    return errors


def validate_manifest_row(
    connection: Connection,
    expected_manifest: dict[str, str],
) -> list[str]:
    """Validate singleton row values in deepfarms_install_manifest.

    Args:
        connection: Active SQLAlchemy database connection.
        expected_manifest: Dictionary containing baseline_sha256 and seed_contract_sha256.

    Returns:
        List of error descriptions, or empty list if valid.

    Raises:
        None.
    """
    from clean_install.manifest import BASELINE_REVISION, SEED_CONTRACT_VERSION

    manifest = connection.execute(
        text("""
            SELECT singleton, install_version, baseline_revision, baseline_sha256,
                   seed_contract_version, seed_contract_sha256
            FROM farms.deepfarms_install_manifest
        """)
    ).one_or_none()
    if manifest is None:
        return ["deepfarms_install_manifest singleton row missing"]

    expected_values = (
        True,
        INSTALL_VERSION,
        BASELINE_REVISION,
        expected_manifest["baseline_sha256"],
        SEED_CONTRACT_VERSION,
        expected_manifest["seed_contract_sha256"],
    )
    if tuple(manifest) != expected_values:
        return [
            f"deepfarms_install_manifest values mismatch: "
            f"expected={expected_values!r} actual={tuple(manifest)!r}"
        ]
    return []


def validate_version_row(connection: Connection) -> list[str]:
    """Validate version row in deepfarms_install_version.

    Args:
        connection: Active SQLAlchemy database connection.

    Returns:
        List of error descriptions, or empty list if valid.

    Raises:
        None.
    """
    version = connection.execute(
        text("SELECT version_num FROM farms.deepfarms_install_version")
    ).scalar_one_or_none()
    if version is None:
        return ["farms.deepfarms_install_version row is missing"]
    if version != INSTALL_VERSION:
        return [
            f"farms.deepfarms_install_version version expected={INSTALL_VERSION!r} "
            f"actual={version!r}"
        ]
    return []


def validate_installer_objects(
    connection: Connection,
    *,
    expected_manifest: dict[str, str] | None = None,
    check_version: bool = False,
) -> list[str]:
    """Validate all installer-internal catalog objects.

    Args:
        connection: Active SQLAlchemy database connection.
        expected_manifest: Optional pinned artifact hashes dictionary.
        check_version: Whether to assert deepfarms_install_version contents.

    Returns:
        List of aggregated error descriptions, or empty list if valid.

    Raises:
        None.
    """
    errors: list[str] = []
    # Check manifest table exists
    manifest_exists = connection.execute(
        text("SELECT to_regclass('farms.deepfarms_install_manifest') IS NOT NULL")
    ).scalar_one()
    if not manifest_exists:
        errors.append("farms.deepfarms_install_manifest table does not exist")
        return errors

    errors.extend(validate_manifest_columns(connection))
    errors.extend(validate_manifest_constraints(connection))

    if expected_manifest is not None:
        errors.extend(validate_manifest_row(connection, expected_manifest))

    if check_version:
        version_exists = connection.execute(
            text("SELECT to_regclass('farms.deepfarms_install_version') IS NOT NULL")
        ).scalar_one()
        if not version_exists:
            errors.append("farms.deepfarms_install_version table does not exist")
        else:
            errors.extend(validate_version_row(connection))

    return errors

