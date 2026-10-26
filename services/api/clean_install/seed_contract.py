"""Deterministic global catalog seeds for a new DeepFarms database.

Only global reference data belongs here. No tenant, user, provider, price,
credential, integration, or demonstration records are seeded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.engine import Connection

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
        natural = "|".join(str(self.data[column]) for column in self.natural_key)
        return uuid5(SEED_NAMESPACE, f"{self.catalog}:{natural}")


def _row(catalog: str, table: str, key: tuple[str, ...], **values: object) -> SeedRow:
    return SeedRow(catalog, table, key, tuple(values.items()))


# Final unit codes incorporate the later ISO 80000 normalization (h/s/min/d/a).
UNITS = (
    ("KG", "Quilograma", "massa", "KG", "1", 2, True),
    ("G", "Grama", "massa", "KG", "0.001", 3, False),
    ("TON", "Tonelada", "massa", "KG", "1000", 4, False),
    ("SC60", "Saca 60 kg", "massa", "KG", "60", 2, False),
    ("SC50", "Saca 50 kg", "massa", "KG", "50", 2, False),
    ("L", "Litro", "volume", "L", "1", 2, True),
    ("ML", "Mililitro", "volume", "L", "0.001", 3, False),
    ("M3", "Metro cúbico", "volume", "L", "1000", 4, False),
    ("HA", "Hectare", "area", "HA", "1", 2, True),
    ("M2", "Metro quadrado", "area", "HA", "0.0001", 0, False),
    ("HM", "Hora-máquina", "hora_maquina", "HM", "1", 2, True),
    ("HH", "Homem-hora", "hora_homem", "HH", "1", 2, True),
    ("UN", "Unidade", "contagem", "UN", "1", 0, True),
    ("BRL", "Real brasileiro", "moeda", "BRL", "1", 2, True),
    ("h", "Hora", "tempo", "h", "1", 2, True),
    ("DIA", "Dia", "tempo", "h", "24", 2, False),
    ("min", "Minuto", "tempo", "h", "0.016666667", 4, False),
    ("s", "Segundo", "tempo", "h", "0.000277778", 0, False),
    ("SEMANA", "Semana", "tempo", "h", "168", 0, False),
    ("MES", "Mês", "tempo", "h", "720", 0, False),
    ("a", "Ano", "tempo", "h", "8760", 0, False),
    ("MANHA", "Manhã (turno de 8h)", "tempo", "h", "8", 0, False),
    ("TARDE", "Tarde (turno de 8h)", "tempo", "h", "8", 0, False),
    ("NOITE", "Noite (turno de 8h)", "tempo", "h", "8", 0, False),
)

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
            id=f"11111111-ca70-0000-0000-{index:012d}",
            tenant_id=None,
            sistema=True,
            parent_id=None,
            nome=name,
            descricao=None,
            cor=None,
            icone=None,
            ordem=0,
            ativo=True,
        )
        for index, name in enumerate(
            (
                "Sementes",
                "Defensivos Agrícolas",
                "Fertilizantes e Corretivos",
                "Inoculantes",
                "Adjuvantes",
                "Ração",
                "Medicamentos Veterinários",
                "Vacinas",
                "Sal Mineral e Suplementos",
                "Peças de Máquinas",
                "Lubrificantes",
                "Combustíveis",
                "Materiais de Uso Geral",
                "Equipamentos de Proteção Individual",
                "Serviços Contratados",
            ),
            1,
        )
    )
    + tuple(
        _row(
            "operation_phases",
            "agricola_operacao_tipo_fase",
            ("tipo_operacao",),
            id="{id}",
            tipo_operacao=kind,
            fases_permitidas=phases,
            descricao=description,
        )
        for kind, phases, description in (
            ("PLANTIO", ["PLANTIO", "DESENVOLVIMENTO"], "Semeadura e plantio"),
            ("ADUBAÇÃO", ["PREPARO_SOLO", "DESENVOLVIMENTO"], "Adubação de base ou cobertura"),
            (
                "PULVERIZAÇÃO",
                ["PLANEJADA", "DESENVOLVIMENTO", "COLHEITA"],
                "Aplicação de defensivos ou bioinsumos",
            ),
            ("COLHEITA", ["COLHEITA"], "Colheita manual ou mecanizada"),
            (
                "OPERAÇÃO_MECANIZADA",
                ["PLANTIO", "DESENVOLVIMENTO"],
                "Operações gerais com máquinas e implementos",
            ),
            ("PREPARO_SOLO", ["PREPARO_SOLO"], "Aração, gradagem, subsolagem e preparo de área"),
            ("CALAGEM", ["PREPARO_SOLO"], "Aplicação de calcário"),
            ("IRRIGAÇÃO", ["DESENVOLVIMENTO", "COLHEITA"], "Operações de irrigação"),
            (
                "OUTROS",
                [
                    "PLANEJADA",
                    "PREPARO_SOLO",
                    "PLANTIO",
                    "DESENVOLVIMENTO",
                    "COLHEITA",
                    "POS_COLHEITA",
                ],
                "Outras operações de campo",
            ),
        )
    )
    + tuple(
        _row(
            "relationship_types",
            "cadastros_tipos_relacionamento",
            ("codigo",),
            id="{id}",
            tenant_id=None,
            codigo=code,
            nome=name,
            descricao=description,
            cor=color,
            icone=icon,
            sistema=True,
            ativo=True,
        )
        for code, name, color, icon, description in (
            ("FORNECEDOR", "Fornecedor", "#F59E0B", "truck", None),
            ("CLIENTE", "Cliente", "#10B981", "user-check", None),
            ("PARCEIRO", "Parceiro", "#6366F1", "handshake", None),
            ("PRESTADOR", "Prestador de Serviço", "#8B5CF6", "wrench", None),
            ("TRANSPORTADORA", "Transportadora", "#3B82F6", "truck-moving", None),
            ("COLABORADOR", "Colaborador / Funcionário", "#EC4899", "hard-hat", None),
            ("PROPRIETARIO", "Proprietário / Arrendador", "#0EA5E9", "landmark", None),
            ("ORGAO", "Órgão / Instituição", "#64748B", "building-2", None),
            ("RESPONSAVEL_TECNICO", "Responsável Técnico", "#14B8A6", "clipboard-check", None),
            (
                "AGRONOMO",
                "Agrônomo",
                "#16A34A",
                "sprout",
                "Engenheiro agrônomo responsável técnico (CREA) por Receituários Agronômicos",
            ),
            (
                "POSTO_RECEBIMENTO",
                "Posto de Recebimento",
                "#0EA5E9",
                "recycle",
                "Estabelecimento/revenda credenciado para devolução de embalagens de defensivos "
                "(Lei 9.974/2000)",
            ),
        )
    )
)

# Explicit ordering is the dependency contract: all operation-phase/catalog
# records follow unit and category catalogs. Conversion rows are deliberately
# excluded: their historic rows depend on a commodity catalog with no clean
# install seed contract and include agronomic assumptions.
SEED_ORDER = ("units", "product_categories", "operation_phases", "relationship_types")
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
        "required": False,
        "scope": "global",
        "depends_on": ("units",),
        "reason": "suggestion-only legacy values reference units absent from final unit contract",
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


def apply_seeds(connection: Connection) -> dict[str, int]:
    """Insert absent global rows; accept exact matches and reject drift."""
    validate_seed_contract()
    inserted: dict[str, int] = {name: 0 for name in SEED_ORDER}
    for row in ordered_seed_rows():
        values = row.data | {"id": row.id}
        if row.table == "cadastros_categorias_produto":
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
