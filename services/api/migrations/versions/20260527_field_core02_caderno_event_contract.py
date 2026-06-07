"""field_core02_caderno_event_contract

Revision ID: 20260527_field_core02
Revises: 8c2e891d6ba9
Create Date: 2026-05-27 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import unicodedata

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260527_field_core02"
down_revision: Union[str, Sequence[str], None] = "8c2e891d6ba9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIPOS_EVENTO_VALIDOS = {
    "PLANTIO",
    "PULVERIZACAO",
    "APLICACAO",
    "IRRIGACAO",
    "COLHEITA",
    "INSPECAO",
    "OCORRENCIA",
    "MANUTENCAO",
    "ABASTECIMENTO",
    "EXECUCAO_OPERACIONAL",
    "MONITORAMENTO",
    "VISITA_TECNICA",
    "EPI_ENTREGA",
    "OBSERVACAO",
    "CLIMA",
    "SOLO",
}


def _normalizar(valor: str | None) -> str:
    if not valor:
        return ""
    texto = unicodedata.normalize("NFKD", valor)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().upper().replace("-", "_").replace(" ", "_")
    while "__" in texto:
        texto = texto.replace("__", "_")
    return texto


def _mapear_tipo_evento(tipo: str, subtipo: str | None = None) -> str:
    tipo_norm = _normalizar(tipo)
    subtipo_norm = _normalizar(subtipo)
    if tipo_norm in TIPOS_EVENTO_VALIDOS:
        return tipo_norm
    if tipo_norm in {"PLANTIO_REGISTRO"}:
        return "PLANTIO"
    if tipo_norm in {"COLHEITA_REGISTRO"}:
        return "COLHEITA"
    if tipo_norm in {"IRRIGACAO_EVENTO"}:
        return "IRRIGACAO"
    if tipo_norm in {"APLICACAO_DEFENSIVO"}:
        return "PULVERIZACAO"
    if tipo_norm in {"APLICACAO_FERTILIZANTE"}:
        return "APLICACAO"
    if tipo_norm in {"MONITORAMENTO_PRAGA"}:
        return "MONITORAMENTO"
    if tipo_norm in {"AMOSTRAGEM_SOLO", "PREPARO_SOLO", "SOLO"}:
        return "SOLO"
    if tipo_norm in {"INSPECAO_EQUIPAMENTO"}:
        return "INSPECAO"
    if tipo_norm in {"ABASTECIMENTO_MAQUINA"}:
        return "ABASTECIMENTO"
    if tipo_norm in {"MANUTENCAO_OCORRENCIA"}:
        return "MANUTENCAO"
    if tipo_norm == "APLICACAO" and "DEFENS" in subtipo_norm:
        return "PULVERIZACAO"
    if tipo_norm == "APLICACAO":
        return "APLICACAO"
    return "EXECUCAO_OPERACIONAL"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("caderno_campo_entradas")}

    if "tipo_evento" not in existing_columns:
        op.add_column(
            "caderno_campo_entradas",
            sa.Column("tipo_evento", sa.String(length=30), nullable=True),
        )
    if "origem_evento" not in existing_columns:
        op.add_column(
            "caderno_campo_entradas",
            sa.Column("origem_evento", sa.String(length=40), nullable=True),
        )
    if "origem_id" not in existing_columns:
        op.add_column(
            "caderno_campo_entradas",
            sa.Column("origem_id", sa.String(length=80), nullable=True),
        )
    if "origem_tecnica" not in existing_columns:
        op.add_column(
            "caderno_campo_entradas",
            sa.Column("origem_tecnica", sa.String(length=40), nullable=True),
        )
    if "status_evento" not in existing_columns:
        op.add_column(
            "caderno_campo_entradas",
            sa.Column("status_evento", sa.String(length=30), nullable=True),
        )

    rows = bind.execute(
        sa.text(
            """
            SELECT e.id, e.tipo, e.operacao_id, e.origem_evento AS origem_evento_atual,
                   e.origem_id AS origem_id_atual, e.origem_tecnica AS origem_tecnica_atual,
                   e.status_evento AS status_evento_atual,
                   o.tipo AS operacao_tipo, o.subtipo AS operacao_subtipo
              FROM caderno_campo_entradas e
         LEFT JOIN operacoes_agricolas o ON o.id = e.operacao_id
            """
        )
    ).mappings().all()

    for row in rows:
        tipo_norm = _normalizar(row["tipo"])
        if tipo_norm == "OPERACAO_AUTO":
            tipo_evento = _mapear_tipo_evento(row["operacao_tipo"] or row["tipo"], row["operacao_subtipo"])
        else:
            tipo_evento = _mapear_tipo_evento(row["tipo"], row["operacao_subtipo"])

        origem_evento = row["origem_evento_atual"] or ("OPERACAO_AGRICOLA" if row["operacao_id"] else "WEB_MANUAL")
        origem_tecnica = row["origem_tecnica_atual"] or ("OPERACAO_AUTO" if row["operacao_id"] or tipo_norm == "OPERACAO_AUTO" else "MANUAL_DIGITAL")
        origem_id = row["origem_id_atual"] or str(row["operacao_id"] or row["id"])
        status_evento = row["status_evento_atual"] or "CONSOLIDADO"

        bind.execute(
            sa.text(
                """
                UPDATE caderno_campo_entradas
                   SET tipo = :tipo,
                       tipo_evento = :tipo_evento,
                       origem_evento = :origem_evento,
                       origem_id = :origem_id,
                       origem_tecnica = :origem_tecnica,
                       status_evento = :status_evento
                 WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "tipo": tipo_evento,
                "tipo_evento": tipo_evento,
                "origem_evento": _normalizar(origem_evento),
                "origem_id": str(origem_id),
                "origem_tecnica": _normalizar(origem_tecnica),
                "status_evento": _normalizar(status_evento) or "CONSOLIDADO",
            },
        )

    op.alter_column("caderno_campo_entradas", "tipo_evento", nullable=False)
    op.alter_column("caderno_campo_entradas", "origem_evento", nullable=False)
    op.alter_column("caderno_campo_entradas", "origem_id", nullable=False)
    op.alter_column("caderno_campo_entradas", "origem_tecnica", nullable=False)
    op.alter_column("caderno_campo_entradas", "status_evento", nullable=False)

    existing_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("caderno_campo_entradas")
        if constraint.get("name")
    }
    if "uq_caderno_campo_origem_evento" not in existing_constraints:
        op.create_unique_constraint(
            "uq_caderno_campo_origem_evento",
            "caderno_campo_entradas",
            ["tenant_id", "origem_evento", "origem_id"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_caderno_campo_origem_evento", "caderno_campo_entradas", type_="unique")
    op.drop_column("caderno_campo_entradas", "status_evento")
    op.drop_column("caderno_campo_entradas", "origem_tecnica")
    op.drop_column("caderno_campo_entradas", "origem_id")
    op.drop_column("caderno_campo_entradas", "origem_evento")
    op.drop_column("caderno_campo_entradas", "tipo_evento")
