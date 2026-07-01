"""wizard foundation

Revision ID: 20260630_wizard_foundation
Revises: c8be30cbd1fe
Create Date: 2026-06-30 00:00:00.000000
"""

from __future__ import annotations

# ruff: noqa: S608
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260630_wizard_foundation"
down_revision = "c8be30cbd1fe"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
SCHEMA = "farms"

IMPLANTACAO_TABLE = "wizard_implantacoes_operacionais"
ETAPA_TABLE = "wizard_implantacoes_etapas"
CHECKLIST_TABLE = "wizard_implantacoes_checklist_itens"
PENDENCIA_TABLE = "wizard_implantacoes_pendencias"
HISTORICO_TABLE = "wizard_implantacoes_historico"

ACTIVE_STATUSES_SQL = (
    "status IN ('NOT_STARTED', 'IN_PROGRESS', 'PAUSED', 'BLOCKED', "
    "'READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION')"
)
WIZARD_STATUS_SQL = (
    "status IN ('NOT_STARTED', 'IN_PROGRESS', 'PAUSED', 'BLOCKED', "
    "'READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION', 'COMPLETED', "
    "'CANCELLED')"
)
WIZARD_STAGE_SQL = (
    "codigo_etapa IN ('DIAGNOSTICO', 'UNIDADE_PRODUTIVA', 'TERRITORIO', "
    "'ATIVIDADES', 'AGRICULTURA', 'PECUARIA', 'ESTOQUE', 'FINANCEIRO', "
    "'MAQUINAS', 'EQUIPE', 'REVISAO', 'GO_LIVE', 'ESTABILIZACAO')"
)


def _enable_tenant_rls(table_name: str) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    op.execute(sa.text(f"ALTER TABLE {table_ref} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON {table_ref}
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON {table_ref}
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON {table_ref}
            FOR UPDATE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON {table_ref}
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )


def _enable_child_rls(table_name: str, *, append_only: bool = False) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    tenant_predicate = " ".join(  # noqa: S608
        [
            "EXISTS (",
            f"SELECT 1 FROM {SCHEMA}.{IMPLANTACAO_TABLE} io",
            f"WHERE io.id = {table_name}.implantacao_id",
            "AND io.tenant_id = current_setting('app.current_tenant_id', true)::uuid",
            ")",
        ]
    )
    op.execute(sa.text(f"ALTER TABLE {table_ref} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON {table_ref}
            FOR SELECT
            USING ({tenant_predicate})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON {table_ref}
            FOR INSERT
            WITH CHECK ({tenant_predicate})
            """
        )
    )
    if append_only:
        return
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON {table_ref}
            FOR UPDATE
            USING ({tenant_predicate})
            WITH CHECK ({tenant_predicate})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON {table_ref}
            FOR DELETE
            USING ({tenant_predicate})
            """
        )
    )


def _disable_rls(table_name: str, *, append_only: bool = False) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    if not append_only:
        op.execute(
            sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_delete_tenant ON {table_ref}")
        )
        op.execute(
            sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_update_tenant ON {table_ref}")
        )
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_insert_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_select_tenant ON {table_ref}"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} DISABLE ROW LEVEL SECURITY"))


def upgrade() -> None:
    op.create_table(
        IMPLANTACAO_TABLE,
        sa.Column("id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("unidade_produtiva_id", UUID, nullable=True),
        sa.Column("owner_usuario_id", UUID, nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'NOT_STARTED'"),
        ),
        sa.Column(
            "etapa_atual",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'DIAGNOSTICO'"),
        ),
        sa.Column(
            "percentual_progresso",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "modo_implantacao",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'ASSISTIDA'"),
        ),
        sa.Column(
            "origem",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'NOVO_ASSINANTE'"),
        ),
        sa.Column("diagnostico_inicial_snapshot", sa.JSON(), nullable=True),
        sa.Column("escopo_modulos", sa.JSON(), nullable=True),
        sa.Column(
            "bloqueio_critico_aberto",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "checklist_minimo_percentual",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("go_live_aprovado_por_usuario_id", UUID, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_for_go_live_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("go_live_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stabilization_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(WIZARD_STATUS_SQL, name="ck_wizard_implantacao_status"),
        sa.CheckConstraint(
            WIZARD_STAGE_SQL.replace("codigo_etapa", "etapa_atual"),
            name="ck_wizard_implantacao_etapa_atual",
        ),
        sa.CheckConstraint(
            "modo_implantacao IN ('ASSISTIDA', 'MANUAL_ASSISTIDA', "
            "'PILOTO_CONTROLADO', 'PARCEIRO')",
            name="ck_wizard_implantacao_modo",
        ),
        sa.CheckConstraint(
            "origem IN ('NOVO_ASSINANTE', 'UPGRADE_ASSINANTE', "
            "'IMPLANTACAO_INTERNA', 'PARCEIRO')",
            name="ck_wizard_implantacao_origem",
        ),
        sa.CheckConstraint(
            "percentual_progresso >= 0 AND percentual_progresso <= 100",
            name="ck_wizard_implantacao_progresso_range",
        ),
        sa.CheckConstraint(
            "checklist_minimo_percentual >= 0 AND checklist_minimo_percentual <= 100",
            name="ck_wizard_implantacao_checklist_percentual_range",
        ),
        sa.CheckConstraint(
            "status <> 'BLOCKED' OR blocked_at IS NOT NULL",
            name="ck_wizard_implantacao_blocked_requires_blocked_at",
        ),
        sa.CheckConstraint(
            "status NOT IN ('READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION', "
            "'COMPLETED') OR unidade_produtiva_id IS NOT NULL",
            name="ck_wizard_implantacao_status_requires_unidade",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_wizard_implantacao_completed_after_started",
        ),
        sa.CheckConstraint(
            "cancelled_at IS NULL OR started_at IS NULL OR cancelled_at >= started_at",
            name="ck_wizard_implantacao_cancelled_after_started",
        ),
        sa.CheckConstraint(
            "go_live_at IS NULL OR started_at IS NULL OR go_live_at >= started_at",
            name="ck_wizard_implantacao_go_live_after_started",
        ),
        sa.CheckConstraint(
            "ready_for_go_live_at IS NULL OR started_at IS NULL OR "
            "ready_for_go_live_at >= started_at",
            name="ck_wizard_implantacao_ready_after_started",
        ),
        sa.CheckConstraint(
            "stabilization_started_at IS NULL OR go_live_at IS NULL OR "
            "stabilization_started_at >= go_live_at",
            name="ck_wizard_implantacao_stabilization_after_go_live",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["unidade_produtiva_id"],
            ["unidades_produtivas.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_usuario_id"], ["usuarios.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["go_live_aprovado_por_usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_implantacao_tenant_id",
        IMPLANTACAO_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_implantacao_tenant_status",
        IMPLANTACAO_TABLE,
        ["tenant_id", "status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_implantacao_owner",
        IMPLANTACAO_TABLE,
        ["owner_usuario_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_implantacao_unidade",
        IMPLANTACAO_TABLE,
        ["unidade_produtiva_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_wizard_implantacao_ativa_por_tenant",
        IMPLANTACAO_TABLE,
        ["tenant_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text(ACTIVE_STATUSES_SQL),
    )

    op.create_table(
        ETAPA_TABLE,
        sa.Column("id", UUID, nullable=False),
        sa.Column("implantacao_id", UUID, nullable=False),
        sa.Column("codigo_etapa", sa.String(length=30), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'NOT_STARTED'"),
        ),
        sa.Column(
            "obrigatoria",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column(
            "percentual_peso",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dados_snapshot", sa.JSON(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(WIZARD_STAGE_SQL, name="ck_wizard_etapa_codigo"),
        sa.CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED', "
            "'BLOCKED')",
            name="ck_wizard_etapa_status",
        ),
        sa.CheckConstraint(
            "percentual_peso >= 0 AND percentual_peso <= 100",
            name="ck_wizard_etapa_peso_range",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_wizard_etapa_completed_after_started",
        ),
        sa.CheckConstraint(
            "skipped_at IS NULL OR started_at IS NULL OR skipped_at >= started_at",
            name="ck_wizard_etapa_skipped_after_started",
        ),
        sa.CheckConstraint(
            "blocked_at IS NULL OR started_at IS NULL OR blocked_at >= started_at",
            name="ck_wizard_etapa_blocked_after_started",
        ),
        sa.ForeignKeyConstraint(
            ["implantacao_id"],
            [f"{IMPLANTACAO_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_etapa_implantacao_status",
        ETAPA_TABLE,
        ["implantacao_id", "status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_wizard_etapa_implantacao_codigo",
        ETAPA_TABLE,
        ["implantacao_id", "codigo_etapa"],
        unique=True,
        schema=SCHEMA,
    )

    op.create_table(
        CHECKLIST_TABLE,
        sa.Column("id", UUID, nullable=False),
        sa.Column("implantacao_id", UUID, nullable=False),
        sa.Column("etapa_id", UUID, nullable=True),
        sa.Column("codigo_item", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column(
            "obrigatorio",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDENTE'"),
        ),
        sa.Column(
            "severidade",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'INFO'"),
        ),
        sa.Column(
            "evidencia_tipo",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'AUTOMATICA'"),
        ),
        sa.Column("evidencia_ref_id", sa.String(length=120), nullable=True),
        sa.Column("checked_by_usuario_id", UUID, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDENTE', 'ATENDIDO', 'DISPENSADO', 'FALHOU')",
            name="ck_wizard_checklist_status",
        ),
        sa.CheckConstraint(
            "severidade IN ('INFO', 'ATENCAO', 'CRITICO')",
            name="ck_wizard_checklist_severidade",
        ),
        sa.CheckConstraint(
            "evidencia_tipo IN ('AUTOMATICA', 'MANUAL', 'DOCUMENTAL', "
            "'REFERENCIAL')",
            name="ck_wizard_checklist_evidencia_tipo",
        ),
        sa.CheckConstraint(
            "checked_at IS NULL OR checked_by_usuario_id IS NOT NULL",
            name="ck_wizard_checklist_checked_requires_user",
        ),
        sa.ForeignKeyConstraint(
            ["implantacao_id"],
            [f"{IMPLANTACAO_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["etapa_id"],
            [f"{ETAPA_TABLE}.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["checked_by_usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_wizard_checklist_implantacao_codigo",
        CHECKLIST_TABLE,
        ["implantacao_id", "codigo_item"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_checklist_implantacao_status",
        CHECKLIST_TABLE,
        ["implantacao_id", "status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_checklist_etapa",
        CHECKLIST_TABLE,
        ["etapa_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        PENDENCIA_TABLE,
        sa.Column("id", UUID, nullable=False),
        sa.Column("implantacao_id", UUID, nullable=False),
        sa.Column("etapa_id", UUID, nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("severidade", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ABERTA'"),
        ),
        sa.Column("titulo", sa.String(length=180), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("responsavel_usuario_id", UUID, nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "tipo IN ('PENDENCIA', 'BLOQUEIO', 'RISCO', 'TAREFA_MANUAL')",
            name="ck_wizard_pendencia_tipo",
        ),
        sa.CheckConstraint(
            "severidade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')",
            name="ck_wizard_pendencia_severidade",
        ),
        sa.CheckConstraint(
            "status IN ('ABERTA', 'EM_TRATAMENTO', 'RESOLVIDA', "
            "'DESCARTADA')",
            name="ck_wizard_pendencia_status",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR status IN ('RESOLVIDA', 'DESCARTADA')",
            name="ck_wizard_pendencia_resolved_status",
        ),
        sa.CheckConstraint(
            "due_date IS NULL OR resolved_at IS NULL OR resolved_at::date >= due_date",
            name="ck_wizard_pendencia_resolved_after_due",
        ),
        sa.ForeignKeyConstraint(
            ["implantacao_id"],
            [f"{IMPLANTACAO_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["etapa_id"],
            [f"{ETAPA_TABLE}.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_pendencia_implantacao_status",
        PENDENCIA_TABLE,
        ["implantacao_id", "status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_pendencia_implantacao_severidade",
        PENDENCIA_TABLE,
        ["implantacao_id", "severidade"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        HISTORICO_TABLE,
        sa.Column("id", UUID, nullable=False),
        sa.Column("implantacao_id", UUID, nullable=False),
        sa.Column("evento", sa.String(length=120), nullable=False),
        sa.Column("status_anterior", sa.String(length=30), nullable=True),
        sa.Column("status_novo", sa.String(length=30), nullable=True),
        sa.Column("etapa_anterior", sa.String(length=30), nullable=True),
        sa.Column("etapa_nova", sa.String(length=30), nullable=True),
        sa.Column("ator_usuario_id", UUID, nullable=True),
        sa.Column("payload_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["implantacao_id"],
            [f"{IMPLANTACAO_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ator_usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_wizard_historico_implantacao_created",
        HISTORICO_TABLE,
        ["implantacao_id", "created_at"],
        unique=False,
        schema=SCHEMA,
    )

    _enable_tenant_rls(IMPLANTACAO_TABLE)
    _enable_child_rls(ETAPA_TABLE)
    _enable_child_rls(CHECKLIST_TABLE)
    _enable_child_rls(PENDENCIA_TABLE)
    _enable_child_rls(HISTORICO_TABLE, append_only=True)


def downgrade() -> None:
    _disable_rls(HISTORICO_TABLE, append_only=True)
    _disable_rls(PENDENCIA_TABLE)
    _disable_rls(CHECKLIST_TABLE)
    _disable_rls(ETAPA_TABLE)
    _disable_rls(IMPLANTACAO_TABLE)

    op.drop_index(
        "ix_wizard_historico_implantacao_created",
        table_name=HISTORICO_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(HISTORICO_TABLE, schema=SCHEMA)

    op.drop_index(
        "ix_wizard_pendencia_implantacao_severidade",
        table_name=PENDENCIA_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_pendencia_implantacao_status",
        table_name=PENDENCIA_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(PENDENCIA_TABLE, schema=SCHEMA)

    op.drop_index(
        "ix_wizard_checklist_etapa",
        table_name=CHECKLIST_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_checklist_implantacao_status",
        table_name=CHECKLIST_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "uq_wizard_checklist_implantacao_codigo",
        table_name=CHECKLIST_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(CHECKLIST_TABLE, schema=SCHEMA)

    op.drop_index(
        "uq_wizard_etapa_implantacao_codigo",
        table_name=ETAPA_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_etapa_implantacao_status",
        table_name=ETAPA_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(ETAPA_TABLE, schema=SCHEMA)

    op.drop_index(
        "uq_wizard_implantacao_ativa_por_tenant",
        table_name=IMPLANTACAO_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_implantacao_unidade",
        table_name=IMPLANTACAO_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_implantacao_owner",
        table_name=IMPLANTACAO_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_implantacao_tenant_status",
        table_name=IMPLANTACAO_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_wizard_implantacao_tenant_id",
        table_name=IMPLANTACAO_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(IMPLANTACAO_TABLE, schema=SCHEMA)
