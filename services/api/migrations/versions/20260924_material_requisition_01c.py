"""MATERIAL-REQUISITION-FLOW-01C: fundação tenant-safe e append-only.

Esta migration apenas adiciona contrato, origem estruturada, diário de eventos,
idempotência e compatibilidade. Não executa entrega, consumo, devolução ou
reapropriação econômica de dados históricos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_material_requisition_01c"
down_revision: str | Sequence[str] | None = "20260915_merge_documentos_fiscais"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PARENT_UNIQUES = (
    ("safras", "uq_safras_tenant_id"),
    ("safra_tarefas", "uq_safra_tarefas_tenant_id"),
    ("planos_operacionais_tarefas", "uq_plano_op_tarefas_tenant_id"),
    ("operacoes_agricolas", "uq_operacoes_agricolas_tenant_id"),
    ("operacoes_execucoes", "uq_operacoes_execucoes_tenant_id"),
    ("cadastros_pessoas", "uq_cadastros_pessoas_tenant_id"),
)


def _create_parent_uniques() -> None:
    for table_name, constraint_name in PARENT_UNIQUES:
        op.create_unique_constraint(constraint_name, table_name, ["tenant_id", "id"])


def _add_request_columns() -> None:
    columns = (
        ("safra_id", sa.Uuid(), True),
        ("safra_tarefa_id", sa.Uuid(), True),
        ("plano_operacional_tarefa_id", sa.Uuid(), True),
        ("responsavel_pessoa_id", sa.Uuid(), True),
        ("version", sa.Integer(), False),
        ("compatibilidade_legado", sa.String(length=24), True),
    )
    for name, type_, nullable in columns:
        kwargs = {"nullable": nullable}
        if name == "version":
            kwargs["server_default"] = sa.text("1")
        op.add_column("estoque_requisicoes", sa.Column(name, type_, **kwargs))


def _add_request_constraints() -> None:
    op.create_unique_constraint(
        "uq_estoque_requisicoes_tenant_id", "estoque_requisicoes", ["tenant_id", "id"]
    )
    op.create_check_constraint(
        "ck_estoque_requisicoes_version_positiva",
        "estoque_requisicoes",
        "version >= 1",
    )
    op.create_check_constraint(
        "ck_estoque_requisicoes_compatibilidade_legado",
        "estoque_requisicoes",
        "compatibilidade_legado IS NULL OR compatibilidade_legado IN "
        "('LEGACY_OPEN','LEGACY_DELIVERED','LEGACY_RETURNED')",
    )
    foreign_keys = (
        ("fk_req_tenant_operacao_agricola", "operacao_agricola_id", "operacoes_agricolas"),
        ("fk_req_tenant_safra", "safra_id", "safras"),
        ("fk_req_tenant_safra_tarefa", "safra_tarefa_id", "safra_tarefas"),
        (
            "fk_req_tenant_plano_tarefa",
            "plano_operacional_tarefa_id",
            "planos_operacionais_tarefas",
        ),
        ("fk_req_tenant_responsavel_pessoa", "responsavel_pessoa_id", "cadastros_pessoas"),
    )
    for name, child_column, parent_table in foreign_keys:
        op.create_foreign_key(
            name,
            "estoque_requisicoes",
            parent_table,
            ["tenant_id", child_column],
            ["tenant_id", "id"],
            ondelete="NO ACTION",
        )


def _add_item_tenant_scope() -> None:
    op.add_column("estoque_requisicoes_itens", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.add_column(
        "estoque_requisicoes_itens", sa.Column("natureza_item", sa.String(length=20), nullable=True)
    )
    op.execute(
        sa.text(
            "UPDATE farms.estoque_requisicoes_itens AS item "
            "SET tenant_id = req.tenant_id "
            "FROM farms.estoque_requisicoes AS req "
            "WHERE req.id = item.requisicao_id"
        )
    )
    op.alter_column("estoque_requisicoes_itens", "tenant_id", nullable=False)
    op.create_unique_constraint(
        "uq_estoque_requisicoes_itens_tenant_id",
        "estoque_requisicoes_itens",
        ["tenant_id", "id"],
    )
    op.create_check_constraint(
        "ck_estoque_requisicoes_itens_natureza",
        "estoque_requisicoes_itens",
        "natureza_item IS NULL OR natureza_item IN ('CONSUMIVEL','RETORNAVEL')",
    )
    op.create_foreign_key(
        "fk_item_req_tenant_requisicao",
        "estoque_requisicoes_itens",
        "estoque_requisicoes",
        ["tenant_id", "requisicao_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )


def _classify_legacy_requests() -> None:
    op.execute(
        sa.text(
            "UPDATE farms.estoque_requisicoes AS req "
            "SET compatibilidade_legado = CASE "
            "WHEN EXISTS (SELECT 1 FROM farms.estoque_requisicoes_itens item "
            "WHERE item.requisicao_id = req.id AND COALESCE(item.quantidade_devolvida, 0) > 0) "
            "THEN 'LEGACY_RETURNED' "
            "WHEN req.status = 'ENTREGUE' OR EXISTS ("
            "SELECT 1 FROM farms.estoque_requisicoes_itens item "
            "WHERE item.requisicao_id = req.id AND COALESCE(item.quantidade_entregue, 0) > 0) "
            "THEN 'LEGACY_DELIVERED' "
            "WHEN req.status IN ('PENDENTE','APROVADA','SEPARANDO') THEN 'LEGACY_OPEN' "
            "ELSE NULL END "
            "WHERE req.compatibilidade_legado IS NULL"
        )
    )


def _add_confirmation_and_reservation_columns() -> None:
    confirmation_columns = (
        ("device_id", sa.Uuid()),
        ("client_operation_id", sa.String(length=120)),
        ("versao_requisicao", sa.Integer()),
        ("resultado", sa.String(length=30)),
        ("correlation_id", sa.Uuid()),
    )
    for name, type_ in confirmation_columns:
        op.add_column("estoque_requisicao_confirmacoes", sa.Column(name, type_, nullable=True))
    op.create_foreign_key(
        "fk_req_confirmacao_device",
        "estoque_requisicao_confirmacoes",
        "campo_dispositivos",
        ["device_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_estoque_requisicao_confirmacao_tenant_client_operation",
        "estoque_requisicao_confirmacoes",
        ["tenant_id", "client_operation_id"],
    )
    op.add_column("estoque_reservas", sa.Column("item_requisicao_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_estoque_reservas_item_requisicao", "estoque_reservas", ["item_requisicao_id"]
    )
    op.create_foreign_key(
        "fk_reserva_tenant_item_requisicao",
        "estoque_reservas",
        "estoque_requisicoes_itens",
        ["tenant_id", "item_requisicao_id"],
        ["tenant_id", "id"],
        ondelete="NO ACTION",
    )


def _create_event_tables() -> None:
    op.create_table(
        "estoque_requisicao_item_eventos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("requisicao_id", sa.Uuid(), nullable=False),
        sa.Column("item_requisicao_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=30), nullable=False),
        sa.Column("quantidade", sa.Numeric(18, 6), nullable=False),
        sa.Column("unidade", sa.String(length=30), nullable=False),
        sa.Column("produto_id", sa.Uuid(), nullable=True),
        sa.Column("lote_id", sa.Uuid(), nullable=True),
        sa.Column("deposito_id", sa.Uuid(), nullable=True),
        sa.Column("operacao_agricola_id", sa.Uuid(), nullable=True),
        sa.Column("operacao_execucao_id", sa.Uuid(), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("pessoa_operacional_id", sa.Uuid(), nullable=True),
        sa.Column("dispositivo_id", sa.Uuid(), nullable=True),
        sa.Column(
            "ocorrido_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("ocorrido_em_dispositivo", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("versao_requisicao", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("causation_id", sa.Uuid(), nullable=True),
        sa.Column("client_operation_id", sa.String(length=120), nullable=True),
        sa.Column("provenance", sa.String(length=24), nullable=False, server_default="CANONICAL"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "requisicao_id"],
            ["estoque_requisicoes.tenant_id", "estoque_requisicoes.id"],
            name="fk_req_item_evento_tenant_requisicao",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "item_requisicao_id"],
            ["estoque_requisicoes_itens.tenant_id", "estoque_requisicoes_itens.id"],
            name="fk_req_item_evento_tenant_item",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "operacao_agricola_id"],
            ["operacoes_agricolas.tenant_id", "operacoes_agricolas.id"],
            name="fk_req_item_evento_tenant_operacao",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "operacao_execucao_id"],
            ["operacoes_execucoes.tenant_id", "operacoes_execucoes.id"],
            name="fk_req_item_evento_tenant_execucao",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "pessoa_operacional_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_req_item_evento_tenant_pessoa",
            ondelete="NO ACTION",
        ),
        sa.UniqueConstraint("tenant_id", "id", name="uq_req_item_evento_tenant_id"),
        sa.UniqueConstraint(
            "tenant_id", "client_operation_id", name="uq_req_item_evento_tenant_client_operation"
        ),
        sa.CheckConstraint("quantidade > 0", name="ck_req_item_evento_quantidade_positiva"),
        sa.CheckConstraint("versao_requisicao >= 1", name="ck_req_item_evento_versao_positiva"),
        sa.CheckConstraint(
            "tipo_evento IN ('SEPARACAO','ENTREGA','RECEBIMENTO','RECUSA','CONSUMO',"
            "'DEVOLUCAO','PERDA','DANO','EXTRAVIO','AJUSTE_AUTORIZADO')",
            name="ck_req_item_evento_tipo",
        ),
        sa.CheckConstraint(
            "provenance IN ('CANONICAL','LEGACY_BACKFILL')", name="ck_req_item_evento_provenance"
        ),
    )
    op.create_index("ix_req_item_evento_tenant", "estoque_requisicao_item_eventos", ["tenant_id"])
    op.create_index(
        "ix_req_item_evento_item",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "item_requisicao_id"],
    )
    op.create_index(
        "ix_req_item_evento_requisicao",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "requisicao_id"],
    )

    op.create_table(
        "estoque_requisicao_responsabilidades",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("requisicao_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("pessoa_operacional_id", sa.Uuid(), nullable=True),
        sa.Column("papel", sa.String(length=20), nullable=False),
        sa.Column("concedido_por_usuario_id", sa.Uuid(), nullable=True),
        sa.Column(
            "vigencia_inicio",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("vigencia_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["concedido_por_usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "requisicao_id"],
            ["estoque_requisicoes.tenant_id", "estoque_requisicoes.id"],
            name="fk_req_responsabilidade_tenant_requisicao",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "pessoa_operacional_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_req_responsabilidade_tenant_pessoa",
            ondelete="NO ACTION",
        ),
        sa.CheckConstraint(
            "papel IN ('RESPONSAVEL','DELEGADO')", name="ck_req_responsabilidade_papel"
        ),
        sa.CheckConstraint(
            "vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio",
            name="ck_req_responsabilidade_vigencia",
        ),
    )
    op.create_index(
        "ix_req_responsabilidade_tenant_req",
        "estoque_requisicao_responsabilidades",
        ["tenant_id", "requisicao_id"],
    )


def _attach_event_to_ledger() -> None:
    op.add_column(
        "estoque_movimentos", sa.Column("requisicao_item_evento_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        "ix_estoque_movimentos_req_item_evento", "estoque_movimentos", ["requisicao_item_evento_id"]
    )
    op.create_foreign_key(
        "fk_movimento_tenant_req_item_evento",
        "estoque_movimentos",
        "estoque_requisicao_item_eventos",
        ["tenant_id", "requisicao_item_evento_id"],
        ["tenant_id", "id"],
        ondelete="NO ACTION",
    )


def _install_rls_and_append_only() -> None:
    for table_name, prefix in (
        ("estoque_requisicao_item_eventos", "req_item_evento"),
        ("estoque_requisicao_responsabilidades", "req_responsabilidade"),
    ):
        op.execute(sa.text(f"ALTER TABLE farms.{table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE farms.{table_name} FORCE ROW LEVEL SECURITY"))
        expression = "tenant_id::text = NULLIF(current_setting('app.current_tenant_id', true), '')"
        op.execute(
            sa.text(
                f"CREATE POLICY {prefix}_select_tenant ON farms.{table_name} "
                f"FOR SELECT USING ({expression})"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY {prefix}_insert_tenant ON farms.{table_name} "
                f"FOR INSERT WITH CHECK ({expression})"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY {prefix}_update_tenant ON farms.{table_name} "
                f"FOR UPDATE USING ({expression}) WITH CHECK ({expression})"
            )
        )
        op.execute(
            sa.text(
                f"CREATE POLICY {prefix}_delete_tenant ON farms.{table_name} "
                f"FOR DELETE USING ({expression})"
            )
        )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION farms.fn_estoque_requisicao_item_evento_append_only()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
              RAISE EXCEPTION 'estoque_requisicao_item_eventos is append-only'
                USING ERRCODE = 'object_not_in_prerequisite_state';
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_estoque_requisicao_item_evento_append_only
            BEFORE UPDATE OR DELETE ON farms.estoque_requisicao_item_eventos
            FOR EACH ROW EXECUTE FUNCTION farms.fn_estoque_requisicao_item_evento_append_only()
            """
        )
    )


def upgrade() -> None:
    _create_parent_uniques()
    _add_request_columns()
    _add_request_constraints()
    _add_item_tenant_scope()
    _classify_legacy_requests()
    _add_confirmation_and_reservation_columns()
    _create_event_tables()
    _attach_event_to_ledger()
    _install_rls_and_append_only()


def _drop_rls_and_append_only() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_estoque_requisicao_item_evento_append_only "
        "ON farms.estoque_requisicao_item_eventos"
    )
    op.execute("DROP FUNCTION IF EXISTS farms.fn_estoque_requisicao_item_evento_append_only()")
    for table_name, prefix in (
        ("estoque_requisicao_item_eventos", "req_item_evento"),
        ("estoque_requisicao_responsabilidades", "req_responsabilidade"),
    ):
        for action in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS {prefix}_{action}_tenant ON farms.{table_name}")
        op.execute(f"ALTER TABLE farms.{table_name} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE farms.{table_name} DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    _drop_rls_and_append_only()
    op.drop_constraint(
        "fk_movimento_tenant_req_item_evento", "estoque_movimentos", type_="foreignkey"
    )
    op.drop_index("ix_estoque_movimentos_req_item_evento", table_name="estoque_movimentos")
    op.drop_column("estoque_movimentos", "requisicao_item_evento_id")
    op.drop_table("estoque_requisicao_responsabilidades")
    op.drop_table("estoque_requisicao_item_eventos")
    op.drop_constraint("fk_reserva_tenant_item_requisicao", "estoque_reservas", type_="foreignkey")
    op.drop_index("ix_estoque_reservas_item_requisicao", table_name="estoque_reservas")
    op.drop_column("estoque_reservas", "item_requisicao_id")
    op.drop_constraint(
        "uq_estoque_requisicao_confirmacao_tenant_client_operation",
        "estoque_requisicao_confirmacoes",
        type_="unique",
    )
    op.drop_constraint(
        "fk_req_confirmacao_device", "estoque_requisicao_confirmacoes", type_="foreignkey"
    )
    for name in (
        "correlation_id",
        "resultado",
        "versao_requisicao",
        "client_operation_id",
        "device_id",
    ):
        op.drop_column("estoque_requisicao_confirmacoes", name)
    op.drop_constraint(
        "fk_item_req_tenant_requisicao", "estoque_requisicoes_itens", type_="foreignkey"
    )
    op.drop_constraint(
        "ck_estoque_requisicoes_itens_natureza", "estoque_requisicoes_itens", type_="check"
    )
    op.drop_constraint(
        "uq_estoque_requisicoes_itens_tenant_id", "estoque_requisicoes_itens", type_="unique"
    )
    op.drop_column("estoque_requisicoes_itens", "natureza_item")
    op.drop_column("estoque_requisicoes_itens", "tenant_id")
    for name in (
        "fk_req_tenant_responsavel_pessoa",
        "fk_req_tenant_plano_tarefa",
        "fk_req_tenant_safra_tarefa",
        "fk_req_tenant_safra",
        "fk_req_tenant_operacao_agricola",
    ):
        op.drop_constraint(name, "estoque_requisicoes", type_="foreignkey")
    op.drop_constraint(
        "ck_estoque_requisicoes_compatibilidade_legado", "estoque_requisicoes", type_="check"
    )
    op.drop_constraint(
        "ck_estoque_requisicoes_version_positiva", "estoque_requisicoes", type_="check"
    )
    op.drop_constraint("uq_estoque_requisicoes_tenant_id", "estoque_requisicoes", type_="unique")
    for name in (
        "compatibilidade_legado",
        "version",
        "responsavel_pessoa_id",
        "plano_operacional_tarefa_id",
        "safra_tarefa_id",
        "safra_id",
    ):
        op.drop_column("estoque_requisicoes", name)
    for table_name, constraint_name in reversed(PARENT_UNIQUES):
        op.drop_constraint(constraint_name, table_name, type_="unique")
