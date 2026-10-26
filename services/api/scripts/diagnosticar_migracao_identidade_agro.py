#!/usr/bin/env python3
"""Diagnóstico somente leitura para uma futura migração SQLite -> PostgreSQL.

O relatório não imprime e-mails, hashes ou segredos. Quando um DSN PostgreSQL é
informado, a transação é explicitamente READ ONLY. Este utilitário nunca migra dados.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()[:12]


def _open_sqlite_read_only(path: Path) -> sqlite3.Connection:
    resolved = path.expanduser().resolve(strict=True)
    connection = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def inspect_sqlite(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with _open_sqlite_read_only(path) as db:
        users = db.execute(
            "SELECT id, email, senha_hash, ativo, email_verificado FROM agro_usuarios"
        ).fetchall()
        counts = {
            "agro_sessoes": db.execute("SELECT count(*) FROM agro_sessoes").fetchone()[0],
            "agro_tokens_recuperacao": db.execute(
                "SELECT count(*) FROM agro_tokens_recuperacao"
            ).fetchone()[0],
            "agro_tokens_verificacao": db.execute(
                "SELECT count(*) FROM agro_tokens_verificacao"
            ).fetchone()[0],
            "agro_user_byok_credentials": db.execute(
                "SELECT count(*) FROM agro_user_byok_credentials"
            ).fetchone()[0],
        }

    records: list[dict[str, Any]] = []
    for row in users:
        try:
            uuid.UUID(str(row["id"]))
            uuid_valid = True
        except ValueError:
            uuid_valid = False
        password_hash = row["senha_hash"] or ""
        records.append(
            {
                "source_uuid": str(row["id"]),
                "email_fingerprint": _fingerprint(row["email"]),
                "email_casefold": row["email"].strip().lower(),
                "uuid_valid": uuid_valid,
                "bcrypt_compatible": password_hash.startswith(("$2a$", "$2b$", "$2y$")),
                "active": bool(row["ativo"]),
                "email_verified": bool(row["email_verificado"]),
            }
        )
    summary = {
        "source_users": len(records),
        "source_sessions": counts["agro_sessoes"],
        "source_password_reset_tokens": counts["agro_tokens_recuperacao"],
        "source_email_verification_tokens": counts["agro_tokens_verificacao"],
        "source_byok_credentials": counts["agro_user_byok_credentials"],
        "invalid_uuids": sum(not record["uuid_valid"] for record in records),
        "incompatible_password_hashes": sum(
            not record["bcrypt_compatible"] for record in records
        ),
        "verified_emails": sum(record["email_verified"] for record in records),
    }
    return summary, records


async def inspect_postgres(dsn: str) -> list[dict[str, str]]:
    import asyncpg  # type: ignore[import-untyped]

    normalized = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(normalized)
    try:
        async with connection.transaction(readonly=True):
            rows = await connection.fetch(
                "SELECT id::text, lower(email) AS email FROM farms.usuarios"
            )
            return [{"id": row["id"], "email": row["email"]} for row in rows]
    finally:
        await connection.close()


def build_report(
    summary: dict[str, Any],
    source: list[dict[str, Any]],
    destination: list[dict[str, str]] | None,
) -> dict[str, Any]:
    destination_by_email = {row["email"]: row["id"] for row in destination or []}
    destination_ids = {row["id"] for row in destination or []}
    email_collisions = []
    uuid_collisions = []
    for record in source:
        if record["email_casefold"] in destination_by_email:
            email_collisions.append(record["email_fingerprint"])
        if record["source_uuid"] in destination_ids:
            uuid_collisions.append(record["source_uuid"])

    return {
        "mode": "DRY_RUN_READ_ONLY",
        "summary": summary,
        "destination_compared": destination is not None,
        "collisions": {
            "email_count": len(email_collisions),
            "email_fingerprints": sorted(email_collisions),
            "uuid_count": len(uuid_collisions),
            "uuids": sorted(uuid_collisions),
        },
        "migration_rules": {
            "preserve_email_verified": True,
            "preserve_compatible_bcrypt_hash": True,
            "sessions_and_tokens_require_explicit_remap": True,
            "byok_requires_same_uuid_or_controlled_decrypt_and_reencrypt": True,
            "byok_reason": "KEK e AAD são derivados dos bytes do UUID do usuário.",
            "destructive_rollback_allowed": False,
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", required=True, type=Path)
    parser.add_argument("--postgres-dsn", help="Destino para comparação READ ONLY")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary, source = inspect_sqlite(args.sqlite_path)
    destination = await inspect_postgres(args.postgres_dsn) if args.postgres_dsn else None
    report = build_report(summary, source, destination)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
