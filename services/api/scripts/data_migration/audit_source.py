"""Read-only audit of the source database before the baseline data load."""

# Identifiers are quoted from model metadata; values use asyncpg parameters.
# ruff: noqa: E501, S608

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy import CheckConstraint, UniqueConstraint

from core.database import Base
from core.model_registry import baseline_candidate_tables, register_models

SCHEMA = "farms"
EXCLUDED_TABLES = frozenset(
    {
        "balanca_afericoes",
        "balanca_avaliacoes_prestador",
        "balanca_dispositivos",
        "balanca_fisicas",
        "balanca_operadores",
        "balanca_ordens",
        "balanca_pesagens",
        "balanca_sync_tombstones",
        "amostras",
        "mapas_fertilidade",
        "territory_legacy_backup_01h2",
    }
)
OPERATIONAL_TABLES = frozenset({"alembic_version"})
CRITICAL_TABLES = (
    "tenants",
    "usuarios",
    "tenant_usuarios",
    "unidades_produtivas",
    "cadastros_propriedades",
    "imoveis_rurais",
    "safras",
    "cultivo_areas",
    "operacoes_agricolas",
    "estoque_movimentos",
    "compras_pedidos",
    "financeiro_lancamentos",
    "tenant_integracoes",
    "wizard_implantacoes_operacionais",
)


def quote(identifier: str) -> str:
    """Quote a trusted PostgreSQL identifier for generated read-only SQL."""
    return '"' + identifier.replace('"', '""') + '"'


def table_sql(table: str) -> str:
    """Return a qualified source table identifier."""
    return f"{quote(SCHEMA)}.{quote(table)}"


async def source_tables(connection: asyncpg.Connection) -> dict[str, dict[str, Any]]:
    """Load source table columns and exact row counts."""
    rows = await connection.fetch(
        """
        SELECT columns.table_name, columns.column_name, columns.data_type,
               columns.udt_name, columns.is_nullable, columns.column_default,
               columns.ordinal_position
        FROM information_schema.columns AS columns
        JOIN information_schema.tables AS tables
          ON tables.table_schema = columns.table_schema
         AND tables.table_name = columns.table_name
        WHERE columns.table_schema = $1
          AND tables.table_type = 'BASE TABLE'
        ORDER BY columns.table_name, ordinal_position
        """,
        SCHEMA,
    )
    tables: dict[str, dict[str, Any]] = {}
    for row in rows:
        table = tables.setdefault(row["table_name"], {"columns": {}, "records": 0})
        table["columns"][row["column_name"]] = dict(row)
    for table in tables:
        tables[table]["records"] = await connection.fetchval(
            f"SELECT count(*) FROM {table_sql(table)}"
        )
        if "tenant_id" in tables[table]["columns"]:
            tables[table]["tenant_count"] = await connection.fetchval(
                f"SELECT count(DISTINCT tenant_id) FROM {table_sql(table)} "
                "WHERE tenant_id IS NOT NULL"
            )
            tables[table]["tenant_nulls"] = await connection.fetchval(
                f"SELECT count(*) FROM {table_sql(table)} WHERE tenant_id IS NULL"
            )
        else:
            tables[table]["tenant_count"] = None
            tables[table]["tenant_nulls"] = None
    return tables


def target_type(column: Any) -> str:
    """Render a baseline column type using PostgreSQL's SQLAlchemy dialect."""
    from sqlalchemy.dialects import postgresql

    return str(column.type.compile(dialect=postgresql.dialect()))


def type_family(type_name: str) -> str:
    """Normalize PostgreSQL aliases before classifying a column conversion."""
    normalized = type_name.lower().split("(", 1)[0].strip()
    aliases = {
        "int2": "smallint",
        "int4": "integer",
        "int8": "bigint",
        "timestamptz": "timestamp with time zone",
        "timestamp without time zone": "timestamp",
        "character varying": "varchar",
        "double precision": "float8",
        "float": "float8",
        "bool": "boolean",
        "json": "json",
        "jsonb": "json",
        "time without time zone": "time",
        "_uuid": "uuid[]",
        "_varchar": "varchar[]",
        "_text": "text[]",
    }
    return aliases.get(normalized, normalized)


def classify_tables(source: dict[str, dict[str, Any]], baseline: set[str]) -> list[dict[str, Any]]:
    """Classify every source and baseline table without changing either database."""
    all_tables = sorted(set(source) | baseline)
    result = []
    for name in all_tables:
        if name in EXCLUDED_TABLES or name in OPERATIONAL_TABLES:
            classification = "EXCLUDED"
        elif name not in source:
            classification = "EMPTY_TARGET"
        elif name not in baseline:
            classification = "REVIEW_REQUIRED"
        else:
            target = Base.metadata.tables[name]
            source_columns = source[name]["columns"]
            differences = []
            review_reasons = []
            for column in target.columns:
                if column.name not in source_columns:
                    differences.append(f"missing_source:{column.name}")
                    if (
                        source[name]["records"]
                        and not column.nullable
                        and column.default is None
                        and column.server_default is None
                    ):
                        review_reasons.append(f"missing_required_column:{column.name}")
                    continue
                source_column = source_columns[column.name]
                source_type = type_family(source_column["udt_name"])
                target_name = type_family(target_type(column))
                if source_type != target_name:
                    differences.append(f"type:{column.name}:{source_type}->{target_type(column)}")
                if (
                    not column.nullable
                    and source_column["is_nullable"] == "YES"
                    and source[name]["null_counts"].get(column.name, 0)
                ):
                    differences.append(f"nullable:{column.name}")
                    review_reasons.append(f"nullability:{column.name}")
            classification = (
                "REVIEW_REQUIRED"
                if review_reasons
                else ("TRANSFORM" if differences else "DIRECT_COPY")
            )
        record = {
            "table": name,
            "records": source.get(name, {}).get("records", 0),
            "tenant_scoped": "tenant_id" in source.get(name, {}).get("columns", {}),
            "tenant_count": source.get(name, {}).get("tenant_count"),
            "tenant_nulls": source.get(name, {}).get("tenant_nulls"),
            "destination_baseline": name in baseline,
            "classification": classification,
        }
        if name in baseline and name in source:
            record["source_columns"] = len(source[name]["columns"])
            record["target_columns"] = len(Base.metadata.tables[name].columns)
            if name in baseline and classification == "REVIEW_REQUIRED":
                record["review_reasons"] = review_reasons
            if differences:
                record["differences"] = differences
        result.append(record)
    return result


def load_order(baseline: set[str]) -> dict[str, Any]:
    """Derive a dependency order and report cycles from baseline foreign keys."""
    dependencies = {name: set() for name in baseline}
    children: defaultdict[str, set[str]] = defaultdict(set)
    for name in baseline:
        for fk in Base.metadata.tables[name].foreign_key_constraints:
            parent = fk.referred_table.name
            if parent in baseline and parent != name:
                dependencies[name].add(parent)
                children[parent].add(name)
    ready = sorted(name for name, parents in dependencies.items() if not parents)
    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for child in sorted(children[current]):
            dependencies[child].discard(current)
            if not dependencies[child]:
                ready.append(child)
        ready.sort()
    cycles = sorted(name for name, parents in dependencies.items() if parents)
    return {"tables": ordered, "cycles": cycles}


async def audit_foreign_keys(
    connection: asyncpg.Connection, source: dict[str, dict[str, Any]], baseline: set[str]
) -> list[dict[str, Any]]:
    """Find source rows that would violate baseline foreign keys."""
    violations = []
    for name in sorted(baseline):
        table = Base.metadata.tables[name]
        for fk in table.foreign_key_constraints:
            source_columns = tuple(element.parent.name for element in fk.elements)
            target_table = fk.referred_table.name
            target_columns = tuple(element.column.name for element in fk.elements)
            if name not in source or target_table not in source:
                continue
            if any(column not in source[name]["columns"] for column in source_columns):
                continue
            if any(column not in source[target_table]["columns"] for column in target_columns):
                continue
            source_match = " AND ".join(
                f"child.{quote(left)} = parent.{quote(right)}"
                for left, right in zip(source_columns, target_columns, strict=True)
            )
            non_null = " AND ".join(
                f"child.{quote(column)} IS NOT NULL" for column in source_columns
            )
            query = (
                f"SELECT count(*) FROM {table_sql(name)} child "
                f"WHERE {non_null} AND NOT EXISTS (SELECT 1 FROM {table_sql(target_table)} parent "
                f"WHERE {source_match})"
            )
            count = await connection.fetchval(query)
            if count:
                violations.append({"table": name, "constraint": fk.name, "count": count})
    return violations


async def audit_constraints(
    connection: asyncpg.Connection, source: dict[str, dict[str, Any]], baseline: set[str]
) -> dict[str, list[dict[str, Any]]]:
    """Evaluate baseline NOT NULL, UNIQUE, CHECK and ENUM contracts on source rows."""
    result = {"not_null": [], "unique": [], "check": [], "enum": []}
    for name in sorted(baseline & set(source)):
        source_columns = source[name]["columns"]
        table = Base.metadata.tables[name]
        for column in table.columns:
            if not column.nullable and column.name in source_columns:
                count = await connection.fetchval(
                    f"SELECT count(*) FROM {table_sql(name)} WHERE {quote(column.name)} IS NULL"
                )
                if count:
                    result["not_null"].append(
                        {"table": name, "column": column.name, "count": count}
                    )
            enum_values = getattr(column.type, "enums", None)
            if enum_values and column.name in source_columns:
                values = ", ".join(f"${index}" for index in range(1, len(enum_values) + 1))
                count = await connection.fetchval(
                    f"SELECT count(*) FROM {table_sql(name)} WHERE {quote(column.name)} IS NOT NULL "
                    f"AND {quote(column.name)} NOT IN ({values})",
                    *enum_values,
                )
                if count:
                    result["enum"].append({"table": name, "column": column.name, "count": count})
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint):
                columns = tuple(column.name for column in constraint.columns)
                if all(column in source_columns for column in columns):
                    group = ", ".join(quote(column) for column in columns)
                    present = " AND ".join(f"{quote(column)} IS NOT NULL" for column in columns)
                    count = await connection.fetchval(
                        f"SELECT count(*) FROM (SELECT {group} FROM {table_sql(name)} "
                        f"WHERE {present} GROUP BY {group} HAVING count(*) > 1) duplicates"
                    )
                    if count:
                        result["unique"].append(
                            {"table": name, "constraint": constraint.name, "count": count}
                        )
            if isinstance(constraint, CheckConstraint):
                try:
                    count = await connection.fetchval(
                        f"SELECT count(*) FROM {table_sql(name)} WHERE NOT ({constraint.sqltext})"
                    )
                except Exception as error:  # pragma: no cover - source-specific SQL
                    result["check"].append(
                        {"table": name, "constraint": constraint.name, "error": str(error)}
                    )
                else:
                    if count:
                        result["check"].append(
                            {"table": name, "constraint": constraint.name, "count": count}
                        )
    return result


async def sequence_plan(
    connection: asyncpg.Connection, source: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Collect MAX values and serial sequence names for integer primary keys."""
    plan = []
    for name, details in sorted(source.items()):
        table = Base.metadata.tables.get(name)
        if table is None:
            continue
        for column in table.primary_key.columns:
            if column.name not in details["columns"] or column.type.__class__.__name__ not in {
                "Integer",
                "BigInteger",
            }:
                continue
            sequence = await connection.fetchval(
                "SELECT pg_get_serial_sequence($1, $2)", f"{SCHEMA}.{name}", column.name
            )
            maximum = await connection.fetchval(
                f"SELECT max({quote(column.name)}) FROM {table_sql(name)}"
            )
            if sequence:
                plan.append(
                    {"table": name, "column": column.name, "sequence": sequence, "max_id": maximum}
                )
    return plan


async def critical_content_stats(
    connection: asyncpg.Connection, source: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Collect source counts and numeric ID bounds for critical tables."""
    stats = []
    for name in CRITICAL_TABLES:
        if name not in source:
            continue
        table = Base.metadata.tables.get(name)
        primary_key = next(iter(table.primary_key.columns), None) if table is not None else None
        record: dict[str, Any] = {
            "table": name,
            "records": source[name]["records"],
            "tenant_count": source[name]["tenant_count"],
        }
        if primary_key is not None and primary_key.type.__class__.__name__ in {
            "Integer",
            "BigInteger",
        }:
            record["min_id"] = await connection.fetchval(
                f"SELECT min({quote(primary_key.name)}) FROM {table_sql(name)}"
            )
            record["max_id"] = await connection.fetchval(
                f"SELECT max({quote(primary_key.name)}) FROM {table_sql(name)}"
            )
        else:
            record["min_id"] = None
            record["max_id"] = None
        stats.append(record)
    return stats


async def audit_source(dsn: str) -> dict[str, Any]:
    """Run the complete source audit without writing to the database."""
    register_models()
    baseline = set(baseline_candidate_tables())
    connection = await asyncpg.connect(dsn)
    try:
        source = await source_tables(connection)
        for name, details in source.items():
            target = Base.metadata.tables.get(name)
            columns = (
                tuple(
                    column.name
                    for column in target.columns
                    if not column.nullable and column.name in details["columns"]
                )
                if target is not None
                else ()
            )
            if columns:
                expressions = ", ".join(
                    f"count(*) FILTER (WHERE {quote(column)} IS NULL) AS n{index}"
                    for index, column in enumerate(columns)
                )
                nulls = await connection.fetchrow(f"SELECT {expressions} FROM {table_sql(name)}")
                details["null_counts"] = {
                    column: nulls[f"n{index}"] for index, column in enumerate(columns)
                }
            else:
                details["null_counts"] = {}
        classifications = classify_tables(source, baseline)
        constraints = await audit_constraints(connection, source, baseline)
        fk_violations = await audit_foreign_keys(connection, source, baseline)
        tenant_violations = []
        if "tenants" in source:
            for name, details in source.items():
                if "tenant_id" not in details["columns"] or name in EXCLUDED_TABLES:
                    continue
                target = Base.metadata.tables.get(name)
                target_tenant = target.c.get("tenant_id") if target is not None else None
                if (
                    target_tenant is not None
                    and not target_tenant.nullable
                    and details["tenant_nulls"]
                ):
                    tenant_violations.append(
                        {"table": name, "kind": "null_tenant_id", "count": details["tenant_nulls"]}
                    )
                count = await connection.fetchval(
                    f"SELECT count(*) FROM {table_sql(name)} child "
                    f"WHERE child.tenant_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM {table_sql('tenants')} parent "
                    "WHERE parent.id::text = child.tenant_id::text)"
                )
                if count:
                    tenant_violations.append(
                        {"table": name, "kind": "unknown_tenant_id", "count": count}
                    )
        tenants = []
        if "tenants" in source:
            tenants = [
                dict(row)
                for row in await connection.fetch(
                    f"SELECT id::text AS id, COALESCE(nome, id::text) AS label "
                    f"FROM {table_sql('tenants')} ORDER BY id"
                )
            ]
        tenant_volume = []
        for name, details in sorted(source.items()):
            if "tenant_id" not in details["columns"]:
                continue
            rows = await connection.fetch(
                f"SELECT tenant_id::text AS tenant_id, count(*) AS records FROM {table_sql(name)} "
                "WHERE tenant_id IS NOT NULL GROUP BY tenant_id ORDER BY tenant_id"
            )
            tenant_volume.extend(
                {"table": name, "tenant_id": row["tenant_id"], "records": row["records"]}
                for row in rows
            )
        return {
            "schema": SCHEMA,
            "source_tables": len(source),
            "tables_with_records": sum(details["records"] > 0 for details in source.values()),
            "total_records": sum(details["records"] for details in source.values()),
            "tenants": tenants,
            "tenant_volume": tenant_volume,
            "tables_without_tenant_id": sorted(
                name for name, details in source.items() if "tenant_id" not in details["columns"]
            ),
            "tables": classifications,
            "constraints": constraints,
            "fk_violations": fk_violations,
            "tenant_violations": tenant_violations,
            "sequence_plan": await sequence_plan(connection, source),
            "critical_content": await critical_content_stats(connection, source),
            "load_order": load_order(baseline),
            "excluded_tables": sorted((EXCLUDED_TABLES | OPERATIONAL_TABLES) & set(source)),
        }
    finally:
        await connection.close()


def parse_args() -> argparse.Namespace:
    """Parse safe command-line options without exposing credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("SOURCE_DATABASE_URL"))
    parser.add_argument("--output", type=argparse.FileType("w"))
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def render_report(payload: dict[str, Any]) -> str:
    """Render a deterministic Markdown handoff from the JSON audit result."""
    has_review = any(row["classification"] == "REVIEW_REQUIRED" for row in payload["tables"])
    has_blockers = bool(
        payload["fk_violations"]
        or payload["tenant_violations"]
        or has_review
        or any(payload["constraints"].values())
    )
    has_cycles = bool(payload["load_order"]["cycles"])
    status = "NO-GO" if has_blockers else ("GO COM RESSALVAS" if has_cycles else "GO PARA CARGA")
    counts = {
        classification: sum(row["classification"] == classification for row in payload["tables"])
        for classification in (
            "DIRECT_COPY",
            "TRANSFORM",
            "EXCLUDED",
            "EMPTY_TARGET",
            "REVIEW_REQUIRED",
        )
    }
    lines = [
        "# DATA-MIGRATION-01A — Auditoria da origem e plano de carga",
        "",
        "## Veredicto",
        "",
        f"`DATA-MIGRATION-01A STATUS: {status}`",
        "",
        "A auditoria foi executada em modo somente leitura no PostgreSQL de origem. "
        "Nenhuma tabela, constraint, policy, sequência ou registro foi alterado.",
        "",
        "## Resumo executivo",
        "",
        f"- Origem: `{payload['source_tables']}` tabelas físicas, "
        f"`{payload['tables_with_records']}` com registros, `{payload['total_records']}` registros exatos;",
        f"- Tenants cadastrados: `{len(payload['tenants'])}`; schema: `{payload['schema']}`;",
        f"- Destino: `{len(baseline_candidate_tables())}` tabelas da baseline;",
        f"- DIRECT_COPY: `{counts['DIRECT_COPY']}`; TRANSFORM: `{counts['TRANSFORM']}`; "
        f"EXCLUDED: `{counts['EXCLUDED']}`; EMPTY_TARGET: `{counts['EMPTY_TARGET']}`; "
        f"REVIEW_REQUIRED: `{counts['REVIEW_REQUIRED']}`;",
        f"- FK violations: `{len(payload['fk_violations'])}`; Tenant violations: `{len(payload['tenant_violations'])}`;",
        f"- CHECK violations: `{len(payload['constraints']['check'])}`; UNIQUE violations: `{len(payload['constraints']['unique'])}`; "
        f"ENUM violations: `{len(payload['constraints']['enum'])}`; NOT NULL violations: `{len(payload['constraints']['not_null'])}`.",
        "",
        "## Inventário origem × baseline",
        "",
        "| tabela | registros | tenant_scoped | tenant_count | destino_baseline | classificação |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    lines.extend(
        f"| `{row['table']}` | {row['records']} | {row['tenant_scoped']} | "
        f"{row['tenant_count'] if row['tenant_count'] is not None else '—'} | "
        f"{row['destination_baseline']} | `{row['classification']}` |"
        for row in payload["tables"]
    )
    lines.extend(
        [
            "",
            "## Tenants e dados fora do escopo",
            "",
            "Tenants presentes na origem: "
            + ", ".join(f"`{tenant['id']}` ({tenant['label']})" for tenant in payload["tenants"])
            + ".",
            "",
            "Tabelas explicitamente excluídas ou operacionais: "
            + ", ".join(f"`{name}`" for name in payload["excluded_tables"])
            + ".",
            "",
            "Tabelas sem `tenant_id`: "
            + f"`{len(payload['tables_without_tenant_id'])}`; a lista completa permanece no JSON produzido pelo auditor.",
            "",
            "## Divergências e violações",
            "",
            "Amostra/total de `REVIEW_REQUIRED`:",
        ]
    )
    lines.extend(
        f"- `{row['table']}`: {', '.join(row.get('review_reasons', []))}"
        for row in payload["tables"]
        if row["classification"] == "REVIEW_REQUIRED"
    )
    lines.extend(
        [
            "",
            "UNIQUE: " + json.dumps(payload["constraints"]["unique"], ensure_ascii=False),
            "",
            "FK violations: " + json.dumps(payload["fk_violations"], ensure_ascii=False),
            "",
            "Tenant violations: " + json.dumps(payload["tenant_violations"], ensure_ascii=False),
            "",
            "## IDs e ordem de carga",
            "",
            f"Foram encontrados `{len(payload['sequence_plan'])}` pares tabela/sequência para ajuste posterior com `setval(...)`. "
            "UUIDs devem ser preservados exatamente.",
            "",
            "### Tabelas críticas — origem",
            "",
            "| tabela | registros | tenant_count | min_id | max_id |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        f"| `{row['table']}` | {row['records']} | "
        f"{row['tenant_count'] if row['tenant_count'] is not None else '—'} | "
        f"{row['min_id'] if row['min_id'] is not None else '—'} | "
        f"{row['max_id'] if row['max_id'] is not None else '—'} |"
        for row in payload["critical_content"]
    )
    lines.extend(
        [
            "",
            "A comparação COUNT/MIN/MAX origem × destino ficará para a fase 01B, "
            "pois o destino PostgreSQL do piloto não foi consultado nesta auditoria.",
            "",
            f"A ordem foi derivada do grafo de FKs da baseline. Foram detectados `{len(payload['load_order']['cycles'])}` ciclos; "
            "a execução deverá usar constraints deferíveis ou carga por grupos controlados antes da fase 01B.",
            "",
            "## Estratégia preparada",
            "",
            "A próxima fase deve usar COPY/bulk insert, preservar IDs, manter RLS/policies e constraints, "
            "executar com papel administrativo controlado e produzir contagens origem × destino. "
            "Nenhum dado de dry-run/fixture foi removido automaticamente.",
            "",
            "## Pendências para liberar a carga",
            "",
            "A fase não está liberada para execução irrestrita enquanto houver qualquer REVIEW_REQUIRED, "
            "violação de constraint ou ciclo de FK sem estratégia operacional aprovada. "
            "Resolver/documentar as seguintes diferenças antes da execução:",
        ]
    )
    lines.extend(
        f"- `{row['table']}`: {', '.join(row.get('review_reasons', []))}"
        for row in payload["tables"]
        if row["classification"] == "REVIEW_REQUIRED"
    )
    lines.extend(
        [
            "",
            "A violação UNIQUE observada anteriormente em `cadastros_produtos` era causada por cinco linhas com "
            "`codigo_interno IS NULL`; como UNIQUE do PostgreSQL permite múltiplos NULLs, ela não é uma violação "
            "após a correção da simulação. Nenhuma linha foi alterada.",
            "",
            "O auditor versionado é `services/api/scripts/data_migration/audit_source.py`. Sua saída JSON deve ser "
            "preservada como evidência da execução, sem registrar credenciais, passwords, tokens ou chaves.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run the read-only audit and write JSON to stdout or a selected file."""
    args = parse_args()
    if not args.database_url:
        raise SystemExit("Defina SOURCE_DATABASE_URL; a URL não é registrada pelo auditor.")
    payload = asyncio.run(audit_source(args.database_url))
    output = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if args.output:
        args.output.write(output)
    else:
        print(output)
    if args.report:
        args.report.write_text(render_report(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
