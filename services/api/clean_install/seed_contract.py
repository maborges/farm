"""Deterministic global catalog seeds for a new DeepFarms database.

Only global reference data belongs here. No tenant, user, provider, price,
credential, integration, or demonstration records are seeded.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.engine import Connection

SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from initial_load.seed_categorias_produto import PRODUCT_CATEGORIES  # noqa: E402
from initial_load.seed_fases_operacao import OPERATION_PHASES  # noqa: E402
from initial_load.seed_tipos_relacionamento import RELATIONSHIP_TYPES  # noqa: E402
from initial_load.seed_tipos_servico import SERVICE_TYPES  # noqa: E402
from initial_load.seed_unidades_medida import UNITS  # noqa: E402

SEED_NAMESPACE = UUID("3f8697d8-a25e-4d29-8248-96d653102deb")


@dataclass(frozen=True)
class SeedRow:
    catalog: str
    table: str
    natural_key: tuple[str, ...]
    values: tuple[tuple[str, object], ...]
    depends_on: tuple[str, ...] = ()
    scope: str = "global"

    @property
    def data(self) -> dict[str, object]:
        return dict(self.values)

    @property
    def id(self) -> UUID:
        configured_id = self.data.get("id")
        if configured_id and configured_id != "{id}":
            try:
                return UUID(str(configured_id))
            except ValueError:
                pass
        natural = "|".join(str(self.data[column]) for column in self.natural_key)
        return uuid5(SEED_NAMESPACE, f"{self.catalog}:{natural}")


def _row(catalog: str, table: str, key: tuple[str, ...], **values: object) -> SeedRow:
    return SeedRow(catalog, table, key, tuple(values.items()))


_CATEGORY_IDS = {category[1]: UUID(category[0]) for category in PRODUCT_CATEGORIES}


SEEDS: tuple[SeedRow, ...] = (
    tuple(
        _row(
            "units",
            "unidades_medida",
            ("codigo",),
            id="{id}",
            tenant_id=None,
            codigo=code,
            nome=name,
            dimensao=dimension,
            codigo_referencia=reference,
            fator_referencia=Decimal(factor),
            sistema=True,
            ativo=True,
            casas_decimais=precision,
            eh_unidade_base=base,
        )
        for code, name, dimension, reference, factor, precision, base in UNITS
    )
    + tuple(
        _row(
            "product_categories",
            "cadastros_categorias_produto",
            ("nome",),
            id=category_id,
            tenant_id=None,
            sistema=True,
            parent_id=_CATEGORY_IDS[parent_name] if parent_name else None,
            nome=name,
            descricao=description,
            cor=color,
            icone=icon,
            ordem=order,
            ativo=True,
        )
        for category_id, name, description, color, icon, order, parent_name in PRODUCT_CATEGORIES
    )
    + tuple(
        _row(
            "operation_phases",
            "agricola_operacao_tipo_fase",
            ("tipo_operacao",),
            id=phase_id,
            tipo_operacao=kind,
            fases_permitidas=phases,
            descricao=description,
        )
        for phase_id, kind, phases, description in OPERATION_PHASES
    )
    + tuple(
        _row(
            "relationship_types",
            "cadastros_tipos_relacionamento",
            ("codigo",),
            id=relationship_id,
            tenant_id=None,
            codigo=code,
            nome=name,
            descricao=description,
            cor=color,
            icone=icon,
            sistema=True,
            ativo=True,
        )
        for relationship_id, code, name, color, icon, description in RELATIONSHIP_TYPES
    )
    + tuple(
        _row(
            "service_types",
            "cadastros_tipos_servico",
            ("nome",),
            id=service_id,
            tenant_id=None,
            nome=name,
            unidade_medida=unit,
            custo_referencia=cost,
            observacoes=notes,
            ativo=True,
        )
        for service_id, name, unit, cost, notes in SERVICE_TYPES
    )
)

# Explicit ordering is the dependency contract: all operation-phase/catalog
# records follow unit and category catalogs. Conversion rows are deliberately
# excluded: their historic rows depend on a commodity catalog with no clean
# install seed contract and include agronomic assumptions.
SEED_ORDER = (
    "units",
    "product_categories",
    "operation_phases",
    "relationship_types",
    "service_types",
)
SEED_CATALOGS = {
    "units": {"table": "unidades_medida", "required": True, "scope": "global", "depends_on": ()},
    "product_categories": {
        "table": "cadastros_categorias_produto",
        "required": True,
        "scope": "global",
        "depends_on": (),
    },
    "operation_phases": {
        "table": "agricola_operacao_tipo_fase",
        "required": True,
        "scope": "global",
        "depends_on": (),
    },
    "relationship_types": {
        "table": "cadastros_tipos_relacionamento",
        "required": True,
        "scope": "global",
        "depends_on": (),
    },
    "service_types": {
        "table": "cadastros_tipos_servico",
        "required": True,
        "scope": "global",
        "depends_on": ("units",),
    },
    "commodity_conversions": {
        "table": "unidades_medida_conversoes",
        "required": False,
        "scope": "tenant-or-commodity",
        "depends_on": ("units",),
        "reason": (
            "conversion factors depend on optional commodity identities and "
            "agronomic assumptions"
        ),
    },
    "zoosanitary_defaults": {
        "table": "modelos_zoosanitarios",
        "required": False,
        "scope": "global reference",
        "depends_on": (),
        "reason": (
            "specialist scientific presets are not required for installation "
            "and require domain approval"
        ),
    },
}


def ordered_seed_rows() -> tuple[SeedRow, ...]:
    order = {name: index for index, name in enumerate(SEED_ORDER)}
    return tuple(sorted(SEEDS, key=lambda row: (order[row.catalog], row.catalog, row.id.hex)))


def validate_seed_contract() -> None:
    if len(SEED_ORDER) != len(set(SEED_ORDER)):
        raise ValueError("Seed order contains duplicate catalog names")
    keys: set[tuple[str, tuple[str, ...], tuple[object, ...]]] = set()
    ids: set[UUID] = set()
    for row in SEEDS:
        if row.catalog not in SEED_ORDER or row.scope != "global":
            raise ValueError(f"Unapproved seed scope/catalog: {row.catalog}")
        data = row.data
        if data.get("tenant_id", None) is not None:
            raise ValueError(f"Seed {row.catalog} must remain global")
        key = (row.table, row.natural_key, tuple(data[column] for column in row.natural_key))
        if key in keys or row.id in ids:
            raise ValueError(f"Duplicate natural key or deterministic id in {row.catalog}")
        keys.add(key)
        ids.add(row.id)

    units = {row.data["codigo"]: row.data for row in SEEDS if row.catalog == "units"}
    for code, unit in units.items():
        if unit["fator_referencia"] <= 0:
            raise ValueError(f"Unit {code} must have a positive reference factor")
        base = units.get(unit["codigo_referencia"])
        if base is None or base["dimensao"] != unit["dimensao"]:
            raise ValueError(f"Unit {code} references a missing or incompatible base unit")
        if base["codigo_referencia"] != base["codigo"] or base["fator_referencia"] != 1:
            raise ValueError(f"Unit {code} reference does not resolve to a canonical base")
    base_counts: dict[str, int] = {}
    for unit in units.values():
        if unit["eh_unidade_base"]:
            base_counts[unit["dimensao"]] = base_counts.get(unit["dimensao"], 0) + 1
    if any(count != 1 for count in base_counts.values()):
        raise ValueError("Each seeded unit dimension must have exactly one base unit")

    category_rows = [row for row in SEEDS if row.catalog == "product_categories"]
    category_ids = {row.id for row in category_rows}
    if any(
        row.data["parent_id"] is not None and row.data["parent_id"] not in category_ids
        for row in category_rows
    ):
        raise ValueError("Product-category seed references a missing parent category")

    allowed_phases = {
        "PLANEJADA",
        "PREPARO_SOLO",
        "PLANTIO",
        "DESENVOLVIMENTO",
        "COLHEITA",
        "POS_COLHEITA",
    }
    if any(
        not set(row.data["fases_permitidas"]).issubset(allowed_phases)
        for row in SEEDS
        if row.catalog == "operation_phases"
    ):
        raise ValueError("Operation-phase seed contains an unknown crop phase")


def apply_seeds(
    connection: Connection,
    *,
    catalogs: tuple[str, ...] | None = None,
) -> dict[str, int]:
    """Insert absent global rows; accept exact matches and reject drift."""
    validate_seed_contract()
    selected_catalogs = set(SEED_ORDER if catalogs is None else catalogs)
    unknown_catalogs = selected_catalogs - set(SEED_ORDER)
    if unknown_catalogs:
        raise ValueError(f"Unknown seed catalogs: {sorted(unknown_catalogs)}")
    inserted: dict[str, int] = {name: 0 for name in SEED_ORDER}
    for row in ordered_seed_rows():
        if row.catalog not in selected_catalogs:
            continue
        values = row.data | {"id": row.id}
        if row.table in {"cadastros_categorias_produto", "cadastros_tipos_servico"}:
            values["created_at"] = datetime.now().astimezone()
            values["updated_at"] = values["created_at"]
        key_filter = " AND ".join(
            (f'"{column}" IS NULL' if values[column] is None else f'"{column}" = :key_{index}')
            for index, column in enumerate(row.natural_key)
        )
        if "tenant_id" in values and "tenant_id" not in row.natural_key:
            key_filter += ' AND "tenant_id" IS NULL'
        params = {
            f"key_{index}": values[column]
            for index, column in enumerate(row.natural_key)
            if values[column] is not None
        }
        existing = (
            connection.execute(
                text(f'SELECT * FROM farms."{row.table}" WHERE {key_filter} FOR UPDATE'),  # noqa: S608
                params,
            )
            .mappings()
            .first()
        )
        if existing is not None:
            for column, expected in values.items():
                if column in {"id", "created_at", "updated_at"}:
                    continue
                observed = existing.get(column)
                if column == "fases_permitidas" and observed is not None:
                    observed = list(observed)
                if observed != expected:
                    raise ValueError(
                        f"Seed drift in {row.table} natural key {row.natural_key}; refusing update"
                    )
            continue
        id_collision = connection.execute(
            text(f'SELECT 1 FROM farms."{row.table}" WHERE id = :seed_id'),  # noqa: S608
            {"seed_id": row.id},
        ).first()
        if id_collision is not None:
            raise ValueError(f"Deterministic seed id collision in {row.table}; refusing overwrite")
        columns = tuple(values)
        binds = {column: values[column] for column in columns}
        if row.table == "agricola_operacao_tipo_fase":
            binds["fases_permitidas"] = json.dumps(values["fases_permitidas"])
        placeholders = [
            f"CAST(:{column} AS JSON)" if column == "fases_permitidas" else f":{column}"
            for column in columns
        ]
        connection.execute(
            text(
                f'INSERT INTO farms."{row.table}" '  # noqa: S608
                f'({", ".join(chr(34) + column + chr(34) for column in columns)}) '
                f'VALUES ({", ".join(placeholders)})'
            ),
            binds,
        )
        inserted[row.catalog] += 1
    return inserted
