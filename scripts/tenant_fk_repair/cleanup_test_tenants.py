#!/usr/bin/env python3
"""Remove tenants de teste criados por scripts/pytest que fazem commit() direto
contra o Postgres real (sem isolamento), e todos os dados filhos em cascata.

Contexto: auditoria de 2026-08-14 encontrou 1295 de 1299 tenants (99,7%) batendo
em padrões de nome de teste (`Tenant <hex>`, `Tenant Teste ...`, `Recommendation
Event`, etc). Só 4 tenants parecem reais: Grupo AgroSaaS, Fazenda Modelo, Fazenda
Nova (x2). Ver memória do projeto project_tenant_fk_repair.

Como a maioria das FKs para farms.tenants é RESTRICT (não CASCADE, de propósito,
por causa do TENANT-FK-REPAIR), não dá pra fazer DELETE FROM tenants direto —
este script descobre a ordem de dependência via pg_constraint e apaga em cascata
manualmente, tabela por tabela, seguindo a cadeia de FKs até achar tenant_id.

USO:
    # 1. Sempre rodar em modo dry-run primeiro (padrão, não apaga nada):
    cd /opt/lampp/htdocs/farm/services/api
    export $(grep DATABASE_URL .env.local | xargs)
    ./.venv/bin/python ../../scripts/tenant_fk_repair/cleanup_test_tenants.py

    # 2. Revisar a lista de tenants e contagens impressas.

    # 3. Rodar de verdade (faz pg_dump de backup automaticamente antes):
    ./.venv/bin/python scripts/tenant_fk_repair/cleanup_test_tenants.py --execute

Requer DATABASE_URL no ambiente (postgresql+asyncpg://... ou postgresql://...).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

SCHEMA = "farms"

# Padrões de nome que identificam tenants de teste. Ajustado empiricamente
# contra o estado real do banco em 2026-08-14 — cobre 1295/1299 tenants.
TEST_NAME_PATTERNS = [
    r"^Tenant ",
    r"teste",
    r"test",
    r"demo",
    r"dashboard pecuaria",
    r"recommendation event",
    r"outro tenant",
]

# Nomes explicitamente protegidos, mesmo que batam em algum padrão acima por
# engano — nunca serão apagados.
PROTECTED_NAMES = {
    "Grupo AgroSaaS",
    "Fazenda Modelo",
    "Fazenda Nova",
}


def db_url_sync(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql://")


async def get_test_tenant_ids(conn: asyncpg.Connection) -> list[tuple[str, str]]:
    rows = await conn.fetch(f"SELECT id, nome FROM {SCHEMA}.tenants ORDER BY nome")
    pattern = re.compile("|".join(TEST_NAME_PATTERNS), re.IGNORECASE)
    result = []
    for r in rows:
        nome = r["nome"] or ""
        if nome in PROTECTED_NAMES:
            continue
        if pattern.search(nome):
            result.append((str(r["id"]), nome))
    return result


async def build_fk_graph(conn: asyncpg.Connection) -> dict[str, list[tuple[str, str, str]]]:
    """table -> [(fk_column, ref_table, ref_column), ...] apenas dentro do schema farms."""
    rows = await conn.fetch(
        """
        SELECT
            c.conrelid::regclass::text  AS tabela,
            a.attname                   AS coluna,
            c.confrelid::regclass::text AS tabela_ref,
            af.attname                  AS coluna_ref
        FROM pg_constraint c
        JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n) ON true
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = x.attnum
        JOIN LATERAL unnest(c.confkey) WITH ORDINALITY AS y(attnum, n) ON y.n = x.n
        JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = y.attnum
        WHERE c.contype = 'f'
          AND c.connamespace = $1::regnamespace
        """,
        SCHEMA,
    )
    graph: dict[str, list[tuple[str, str, str]]] = {}
    for r in rows:
        tabela = r["tabela"].split(".")[-1]
        tabela_ref = r["tabela_ref"].split(".")[-1]
        graph.setdefault(tabela, []).append((r["coluna"], tabela_ref, r["coluna_ref"]))
    return graph


async def get_tenant_id_tables(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT table_name FROM information_schema.columns
        WHERE table_schema = $1 AND column_name = 'tenant_id'
        """,
        SCHEMA,
    )
    return {r["table_name"] for r in rows}


def build_condition(
    table: str,
    graph: dict[str, list[tuple[str, str, str]]],
    tenant_tables: set[str],
    memo: dict[str, str | None],
    visiting: set[str],
) -> str | None:
    """Monta recursivamente a condição WHERE que identifica linhas de `table`
    pertencentes a algum tenant de teste, seguindo a cadeia de FKs até achar
    tenant_id. Retorna None se não há caminho até tenant_id (tabela não filha
    de nenhuma cadeia tenant-scoped conhecida)."""
    if table in memo:
        return memo[table]
    if table in visiting:
        return None  # ciclo - não deveria acontecer no nosso schema
    visiting.add(table)

    if table in tenant_tables:
        # cast pra texto: algumas tabelas (animal_genetica, cochos,
        # confinamento_lotes, racoes_tmr, sugestoes_acasalamento) ainda têm
        # tenant_id como varchar, não uuid — ver project_tenant_fk_repair
        memo[table] = "tenant_id::text = ANY($1::text[])"
        visiting.discard(table)
        return memo[table]

    for fk_col, ref_table, ref_col in graph.get(table, []):
        if ref_table == table:
            continue
        sub = build_condition(ref_table, graph, tenant_tables, memo, visiting)
        if sub is not None:
            # cast pra texto dos dois lados: algumas FKs têm tipo divergente
            # (varchar apontando pra coluna uuid) — ver project_tenant_fk_repair
            cond = (
                f'"{fk_col}"::text IN '
                f'(SELECT "{ref_col}"::text FROM {SCHEMA}."{ref_table}" WHERE {sub})'
            )
            memo[table] = cond
            visiting.discard(table)
            return cond

    memo[table] = None
    visiting.discard(table)
    return None


def topological_order(graph: dict[str, list[tuple[str, str, str]]], all_tables: set[str]) -> list[str]:
    """Ordem de exclusão: tabelas filhas antes das tabelas pai.

    DFS pós-ordem sobre as arestas "t referencia ref_table" naturalmente
    produz ref_table (pai) ANTES de t (filho) — é a ordem certa pra CRIAR
    tabelas, não pra apagar linhas. Pra apagar precisamos do inverso: filho
    antes do pai, senão o DELETE no pai falha com FK violation (bug real,
    encontrado ao rodar --execute em produção em 2026-08-14 — ver
    project_tenant_fk_repair). Por isso o reversed() no final.
    """
    order: list[str] = []
    visited: set[str] = set()

    def visit(t: str) -> None:
        if t in visited:
            return
        visited.add(t)
        for _fk_col, ref_table, _ref_col in graph.get(t, []):
            if ref_table != t:
                visit(ref_table)
        order.append(t)

    for t in sorted(all_tables):
        visit(t)
    order.reverse()
    return order


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Executa de verdade (senão só dry-run)")
    parser.add_argument("--skip-backup", action="store_true", help="Pula o pg_dump automático (não recomendado)")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL não definido no ambiente.", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        test_tenants = await get_test_tenant_ids(conn)
        print(f"Tenants de teste identificados: {len(test_tenants)}")
        if not test_tenants:
            print("Nada para apagar.")
            return

        ids = [t[0] for t in test_tenants]

        graph = await build_fk_graph(conn)
        tenant_tables = await get_tenant_id_tables(conn)
        all_tables_rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = $1 AND table_type = 'BASE TABLE'",
            SCHEMA,
        )
        all_tables = {r["table_name"] for r in all_tables_rows}
        all_tables.discard("tenants")

        memo: dict[str, str | None] = {}
        conditions: dict[str, str] = {}
        unreachable: list[str] = []
        for t in all_tables:
            cond = build_condition(t, graph, tenant_tables, memo, set())
            if cond is None:
                unreachable.append(t)
            else:
                conditions[t] = cond

        order = [t for t in topological_order(graph, all_tables) if t in conditions]

        print(f"\nTabelas alcançáveis a partir de tenant_id: {len(conditions)}")
        print(f"Tabelas SEM caminho até tenant_id (não tocadas): {len(unreachable)}")
        if unreachable:
            print("  " + ", ".join(sorted(unreachable)))

        print("\n=== DRY RUN: contagem de linhas que seriam apagadas por tabela ===")
        total_rows = 0
        counts: dict[str, int] = {}
        for t in order:
            cond = conditions[t]
            sql = f'SELECT COUNT(*) FROM {SCHEMA}."{t}" WHERE {cond}'
            try:
                cnt = await conn.fetchval(sql, ids)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERRO ao contar {t}: {exc}")
                continue
            if cnt:
                counts[t] = cnt
                total_rows += cnt
                print(f"  {t}: {cnt}")

        print(f"\nTotal de linhas a apagar (excluindo tenants): {total_rows}")
        print(f"Tenants a apagar: {len(ids)}")

        if not args.execute:
            print("\nModo dry-run (padrão). Rode com --execute para aplicar de verdade.")
            return

        # Tabelas com FORCE ROW LEVEL SECURITY bloqueiam tanto o pg_dump
        # quanto o DELETE, mesmo pro dono da tabela (borgus não é
        # superuser/bypassrls) — algumas têm política baseada em
        # current_setting('app.current_tenant_id'), que esta sessão nunca
        # seta, então o DELETE filtra silenciosamente 0 linhas (sem erro!)
        # e a linha real sobrevive pra travar o DELETE FROM tenants depois.
        # Descoberto em produção em 2026-08-14 (alert_lifecycle_events).
        # Por isso o desligamento cobre backup E exclusão juntos, só
        # religando no finally bem no final.
        force_rls_rows = await conn.fetch(
            "SELECT relname FROM pg_class "
            "WHERE relforcerowsecurity = true AND relnamespace = $1::regnamespace",
            SCHEMA,
        )
        force_rls_tables = [r["relname"] for r in force_rls_rows]
        if force_rls_tables:
            print(f"\nDesligando FORCE RLS temporariamente em {len(force_rls_tables)} tabela(s)...")
            for t in force_rls_tables:
                await conn.execute(f'ALTER TABLE {SCHEMA}."{t}" NO FORCE ROW LEVEL SECURITY')

        try:
            if not args.skip_backup:
                backup_dir = Path(__file__).parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"pre_cleanup_test_tenants_{ts}.sql.gz"
                print(f"Fazendo backup em {backup_file} ...")
                sync_url = db_url_sync(db_url)
                # set -o pipefail: sem isso, o exit code é só do gzip, e um
                # pg_dump que falha no meio (ex. erro de RLS) passa
                # despercebido com um arquivo .gz pequeno e corrompido —
                # bug real encontrado em produção em 2026-08-14.
                dump_cmd = f"set -o pipefail; pg_dump '{sync_url}' | gzip > '{backup_file}'"
                result = subprocess.run(["bash", "-c", dump_cmd])
                if result.returncode != 0 or not backup_file.exists() or backup_file.stat().st_size == 0:
                    print("Backup falhou — abortando sem apagar nada.", file=sys.stderr)
                    if backup_file.exists():
                        backup_file.unlink()
                    sys.exit(1)
                print(f"Backup OK ({backup_file.stat().st_size} bytes).")

            print("\n=== EXECUTANDO exclusão em transação única ===")
            # Algumas tabelas têm trigger BEFORE DELETE que bloqueia exclusão
            # por design (ex. estoque_movimentos é append-only — correções só
            # via "ajuste_de"). Pra limpar dado de teste isso não se aplica;
            # desligamos qualquer trigger BEFORE DELETE nas tabelas afetadas,
            # dentro da transação, e religamos antes do commit.
            #
            # Também pode haver processo de fundo (scheduler do alert_engine)
            # inserindo/atualizando linhas pros mesmos tenants em tempo real —
            # por isso o retry: nunca pular DELETE por causa de uma contagem
            # antiga, e tentar de novo (transação nova) se colidir.
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    async with conn.transaction():
                        trigger_rows = await conn.fetch(
                            """
                            SELECT DISTINCT c.relname AS tabela, t.tgname AS trigger
                            FROM pg_trigger t
                            JOIN pg_class c ON c.oid = t.tgrelid
                            WHERE c.relnamespace = $1::regnamespace
                              AND NOT t.tgisinternal
                              AND (t.tgtype::int & 8) = 8   -- TRIGGER_TYPE_DELETE
                              AND (t.tgtype::int & 2) = 2   -- TRIGGER_TYPE_BEFORE
                              AND c.relname = ANY($2::text[])
                            """,
                            SCHEMA,
                            order,
                        )
                        if trigger_rows:
                            print(f"Desligando {len(trigger_rows)} trigger(s) BEFORE DELETE nas tabelas afetadas...")
                            for r in trigger_rows:
                                await conn.execute(
                                    f'ALTER TABLE {SCHEMA}."{r["tabela"]}" DISABLE TRIGGER "{r["trigger"]}"'
                                )

                        for t in order:
                            cond = conditions[t]
                            await conn.execute(f'DELETE FROM {SCHEMA}."{t}" WHERE {cond}', ids)
                        deleted = await conn.fetch(
                            f"DELETE FROM {SCHEMA}.tenants WHERE id = ANY($1::uuid[]) RETURNING id", ids
                        )

                        if trigger_rows:
                            print(f"Religando {len(trigger_rows)} trigger(s)...")
                            for r in trigger_rows:
                                await conn.execute(
                                    f'ALTER TABLE {SCHEMA}."{r["tabela"]}" ENABLE TRIGGER "{r["trigger"]}"'
                                )
                    print(f"Tenants apagados: {len(deleted)}")
                    break
                except asyncpg.exceptions.ForeignKeyViolationError as exc:
                    if attempt == max_attempts:
                        raise
                    print(f"Colisão com processo concorrente (tentativa {attempt}/{max_attempts}): {exc}")
                    print("Tentando de novo em transação nova...")
            print("Concluído com sucesso.")
        finally:
            if force_rls_tables:
                print(f"Religando FORCE RLS em {len(force_rls_tables)} tabela(s)...")
                for t in force_rls_tables:
                    await conn.execute(f'ALTER TABLE {SCHEMA}."{t}" FORCE ROW LEVEL SECURITY')

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
