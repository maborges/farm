"""BASELINE-DEEPFARMS-V1.

This revision is an independent clean-install entry point.  It deliberately
does not depend on the historical Alembic graph and does not use
``MetaData.create_all``.  ORM tables come from the approved registry and
non-ORM objects come from ``baseline_contract``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, CreateEnumType, DropEnumType
from sqlalchemy.schema import CreateIndex, CreateTable

from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models
from migrations.baseline_contract import (
    ENUM_CONTRACT,
    FK_CONTRACT,
    POLICY_CONTRACT,
    REQUIRED_SEQUENCE_NAMES,
    RLS_CONTRACT,
    SEQUENCE_CONTRACT,
)

revision = "baseline_deepfarms_v1"
down_revision = None
branch_labels = ("deepfarms_baseline",)
depends_on = None


def _quote(name: str) -> str:
    """Quote an identifier for the active PostgreSQL dialect."""
    return op.get_bind().dialect.identifier_preparer.quote(name)


def _create_schema() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS farms"))
    op.execute(sa.text("SET search_path TO farms"))


def _create_enums() -> None:
    for name, values in ENUM_CONTRACT.items():
        enum = ENUM(*values, name=name, schema="farms")
        op.execute(CreateEnumType(enum))


def _create_sequences() -> None:
    for name in sorted(REQUIRED_SEQUENCE_NAMES):
        contract = SEQUENCE_CONTRACT[name]
        data_type = contract["data_type"]
        maxvalue = contract["maxvalue"]
        op.execute(sa.text(
            f"CREATE SEQUENCE farms.{_quote(name)} AS {data_type} "
            f"START WITH {contract['start']} INCREMENT BY {contract['increment']} "
            f"MINVALUE {contract['minvalue']} MAXVALUE {maxvalue} "
            f"CACHE {contract['cache']}"
        ))


def _create_tables() -> list[sa.Table]:
    register_models()
    names = baseline_candidate_tables()
    tables = [Base.metadata.tables[name] for name in sorted(names)]
    for table in tables:
        op.execute(CreateTable(table, include_foreign_key_constraints=()))
    return tables


def _create_foreign_keys(tables: list[sa.Table]) -> None:
    for table in tables:
        for constraint in sorted(
            table.foreign_key_constraints,
            key=lambda item: item.name or "",
        ):
            source_columns = tuple(element.parent.name for element in constraint.elements)
            contract = FK_CONTRACT.get((table.name, constraint.name or "", source_columns), {})
            op.create_foreign_key(
                constraint.name,
                table.name,
                constraint.referred_table.name,
                list(source_columns),
                [element.column.name for element in constraint.elements],
                ondelete=contract.get("baseline_on_delete", constraint.ondelete),
                onupdate=contract.get("baseline_on_update", constraint.onupdate),
                deferrable=constraint.deferrable,
                initially=constraint.initially,
            )


def _create_indexes(tables: list[sa.Table]) -> None:
    for table in tables:
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            op.execute(CreateIndex(index))


def _create_functions_and_triggers() -> None:
    op.execute(sa.text("""
        CREATE FUNCTION fn_estoque_movimentos_append_only()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION
            'estoque_movimentos is append-only: use ajuste_de for corrections'
            USING ERRCODE = 'object_not_in_prerequisite_state';
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE FUNCTION fn_production_units_valida_soma()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE v_soma NUMERIC(6,2);
        BEGIN
          SELECT COALESCE(SUM(percentual_participacao), 0) INTO v_soma
            FROM production_units
           WHERE tenant_id = NEW.tenant_id AND safra_id = NEW.safra_id
             AND area_id = NEW.area_id AND status <> 'CANCELADA';
          IF v_soma > 100.01 THEN
            RAISE EXCEPTION
              'soma de percentual_participacao excede 100 em '
              '(tenant=%, safra=%, area=%): soma=% — verifique PUs de consórcio',
              NEW.tenant_id, NEW.safra_id, NEW.area_id, v_soma
              USING ERRCODE = 'check_violation';
          END IF;
          RETURN NULL;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE FUNCTION fn_production_units_refresh_status()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
          v_tenant_id UUID;
          v_safra_id UUID;
          v_area_id UUID;
          v_soma NUMERIC(6,2);
          v_qtd INTEGER;
          v_status VARCHAR(20);
        BEGIN
          IF TG_OP = 'DELETE' THEN
            v_tenant_id := OLD.tenant_id;
            v_safra_id := OLD.safra_id;
            v_area_id := OLD.area_id;
          ELSE
            v_tenant_id := NEW.tenant_id;
            v_safra_id := NEW.safra_id;
            v_area_id := NEW.area_id;
          END IF;
          SELECT COALESCE(SUM(percentual_participacao), 0), COUNT(*)
            INTO v_soma, v_qtd
            FROM production_units
           WHERE tenant_id = v_tenant_id
             AND safra_id  = v_safra_id
             AND area_id   = v_area_id
             AND status <> 'CANCELADA';

          IF v_qtd = 0 THEN
            v_status := 'VAZIO';
          ELSIF v_soma < 99.99 THEN
            v_status := 'INCOMPLETO';
          ELSIF v_soma <= 100.01 THEN
            v_status := 'VALIDO';
          ELSE
            v_status := 'INCONSISTENTE';
          END IF;
          INSERT INTO status_consorcio_area
            (id, tenant_id, safra_id, area_id, soma_participacao,
             qtd_unidades, status, calculado_em)
          VALUES (gen_random_uuid(), v_tenant_id, v_safra_id, v_area_id,
                  v_soma, v_qtd, v_status, now())
          ON CONFLICT (tenant_id, safra_id, area_id) DO UPDATE SET
            soma_participacao = EXCLUDED.soma_participacao,
            qtd_unidades = EXCLUDED.qtd_unidades, status = EXCLUDED.status,
            calculado_em = EXCLUDED.calculado_em;
          -- UPDATE que mude as chaves precisa refrescar também a área antiga.
          IF TG_OP = 'UPDATE' AND (
               OLD.tenant_id <> NEW.tenant_id
            OR OLD.safra_id  <> NEW.safra_id
            OR OLD.area_id   <> NEW.area_id
          ) THEN
            SELECT COALESCE(SUM(percentual_participacao), 0), COUNT(*)
              INTO v_soma, v_qtd
              FROM production_units
             WHERE tenant_id = OLD.tenant_id
               AND safra_id  = OLD.safra_id
               AND area_id   = OLD.area_id
               AND status <> 'CANCELADA';

            IF v_qtd = 0 THEN
              v_status := 'VAZIO';
            ELSIF v_soma < 99.99 THEN
              v_status := 'INCOMPLETO';
            ELSIF v_soma <= 100.01 THEN
              v_status := 'VALIDO';
            ELSE
              v_status := 'INCONSISTENTE';
            END IF;

            INSERT INTO status_consorcio_area
              (id, tenant_id, safra_id, area_id,
               soma_participacao, qtd_unidades, status, calculado_em)
            VALUES
              (gen_random_uuid(), OLD.tenant_id, OLD.safra_id, OLD.area_id,
               v_soma, v_qtd, v_status, now())
            ON CONFLICT (tenant_id, safra_id, area_id) DO UPDATE SET
              soma_participacao = EXCLUDED.soma_participacao,
              qtd_unidades = EXCLUDED.qtd_unidades,
              status = EXCLUDED.status,
              calculado_em = EXCLUDED.calculado_em;
          END IF;
          RETURN NULL;
        END;
        $$
    """))
    op.execute(sa.text("""
        CREATE TRIGGER tg_estoque_movimentos_append_only
          BEFORE UPDATE OR DELETE ON estoque_movimentos FOR EACH ROW
          EXECUTE FUNCTION fn_estoque_movimentos_append_only()
    """))
    op.execute(sa.text("""
        CREATE CONSTRAINT TRIGGER tg_production_units_valida_soma
          AFTER INSERT OR UPDATE ON production_units DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION fn_production_units_valida_soma()
    """))
    op.execute(sa.text("""
        CREATE TRIGGER tg_production_units_refresh_status
          AFTER INSERT OR UPDATE OR DELETE ON production_units FOR EACH ROW
          EXECUTE FUNCTION fn_production_units_refresh_status()
    """))


def _apply_rls_and_policies() -> None:
    for name, contract in sorted(RLS_CONTRACT.items()):
        if contract["enabled"]:
            op.execute(sa.text(f"ALTER TABLE {_quote(name)} ENABLE ROW LEVEL SECURITY"))
        if contract["forced"]:
            op.execute(sa.text(f"ALTER TABLE {_quote(name)} FORCE ROW LEVEL SECURITY"))
    for contract in sorted(POLICY_CONTRACT.values(), key=lambda item: item["name"]):
        table = _quote(contract["table"])
        policy = _quote(contract["name"])
        roles = ", ".join(
            _quote(role) if role != "public" else "PUBLIC"
            for role in contract["roles"]
        )
        mode = "PERMISSIVE" if contract["permissive"] else "RESTRICTIVE"
        sql = (
            f"CREATE POLICY {policy} ON {table} AS {mode} "
            f"FOR {contract['command']} TO {roles}"
        )
        if contract["using_expression"]:
            sql += f" USING ({contract['using_expression']})"
        if contract["with_check_expression"]:
            sql += f" WITH CHECK ({contract['with_check_expression']})"
        op.execute(sa.text(sql))


def upgrade() -> None:
    """Create the approved DeepFarms schema in dependency-safe order."""
    _create_schema()
    _create_enums()
    _create_sequences()
    tables = _create_tables()
    _create_foreign_keys(tables)
    _create_indexes(tables)
    _create_functions_and_triggers()
    _apply_rls_and_policies()


def downgrade() -> None:
    """Remove only objects created by this independent baseline."""
    policies = sorted(
        POLICY_CONTRACT.values(), key=lambda item: item["name"], reverse=True
    )
    for contract in policies:
        op.execute(
            sa.text(
                f"DROP POLICY {_quote(contract['name'])} "
                f"ON {_quote(contract['table'])}"
            )
        )
    for table, trigger in (
        ("estoque_movimentos", "tg_estoque_movimentos_append_only"),
        ("production_units", "tg_production_units_refresh_status"),
        ("production_units", "tg_production_units_valida_soma"),
    ):
        op.execute(sa.text(f"DROP TRIGGER {_quote(trigger)} ON {_quote(table)}"))
    for name in (
        "fn_estoque_movimentos_append_only",
        "fn_production_units_valida_soma",
        "fn_production_units_refresh_status",
    ):
        op.execute(sa.text(f"DROP FUNCTION {_quote(name)}()"))
    register_models()
    for name in sorted(baseline_candidate_tables(), reverse=True):
        op.drop_table(name)
    for name in sorted(REQUIRED_SEQUENCE_NAMES, reverse=True):
        op.execute(sa.text(f"DROP SEQUENCE {_quote(name)}"))
    for name in reversed(tuple(ENUM_CONTRACT)):
        op.execute(DropEnumType(ENUM(*ENUM_CONTRACT[name], name=name, schema="farms")))
    op.execute(sa.text("DROP SCHEMA farms"))
