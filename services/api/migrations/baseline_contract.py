# ruff: noqa: E501
"""Explicit non-ORM decisions for BASELINE-DEEPFARMS-V1.

This is a contract inventory, not a migration and not a second model
registry.  It is intentionally conservative while 01C.2 is still NO-GO:
entries identify the observed object and its decision, while unresolved
families remain explicit blockers instead of being inferred by autogenerate.
All database facts in this module were obtained with read-only catalog
queries against the reference PostgreSQL database.
"""

from __future__ import annotations

import base64
import gzip
import json

BASELINE_SCHEMA = "farms"
BASELINE_ORM_TABLE_COUNT = 344
DISCOVERED_MODEL_COUNT = 373

# These are the only nullable conflicts found by the 01C.1 comparison.  The
# clean-install contract follows the current model/domain contract; the
# legacy database's nullable columns are retained as evidence, not copied.
NULLABLE_DECISIONS = {
    ("frota_planos_manutencao", "tenant_id"): {
        "decision": "NOT NULL",
        "baseline_source": "TENANT_INTEGRITY",
        "db_observed": "NULL",
    },
    ("frota_registros_manutencao", "tenant_id"): {
        "decision": "NOT NULL",
        "baseline_source": "TENANT_INTEGRITY",
        "db_observed": "NULL",
    },
    ("compras_pedidos", "valor_total"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("prescricoes_vra", "status"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("prescricoes_vra", "insumo"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("prescricoes_vra", "camadas_json"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("prescricoes_vra", "data_prescricao"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("prescricoes_vra", "tipo_operacao"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("carbono_emissoes", "unidade_produtiva_id"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
    ("carbono_projetos", "unidade_produtiva_id"): {
        "decision": "NOT NULL",
        "baseline_source": "ORM",
        "db_observed": "NULL",
    },
}

# The old ORM declaration pointed at a non-existent, non-registry table. The
# historical migration and the database both prove that animal_id is a plain
# nullable integer.  The model was corrected to match that explicit contract;
# no replacement FK is invented here.
FK_DECISIONS = {
    ("animal_genetica", "animal_id"): {
        "decision": "NO_FOREIGN_KEY",
        "baseline_source": "MIGRATION",
        "target": None,
        "reason": "67b25594e50e creates the column without FK; lotes is not an approved table",
    }
}

ENUM_CONTRACT = {
    "metodoavaliacaoimovel": ("MERCADO", "CUSTO", "RENDA", "DECLARADO", "LAUDO"),
    "periodicidade": ("MENSAL", "SEMESTRAL", "ANUAL", "SAFRA"),
    "prioridade_plano_acao_enum": ("BAIXA", "MEDIA", "ALTA", "URGENTE"),
    "resultado_avaliacao_enum": ("APROVADO", "APROVADO_COM_RESSALVA", "REPROVADO", "PENDENTE"),
    "severidade_nao_conformidade_enum": ("MENOR", "MAIOR", "CRITICA"),
    "severidadealerta": ("BAIXA", "MEDIA", "ALTA", "CRITICA"),
    "situacaoimovel": ("REGULAR", "PENDENTE", "IRREGULAR"),
    "status_checklist_enum": ("RASCUNHO", "PUBLICADO", "ARQUIVADO"),
    "status_nao_conformidade_enum": ("ABERTA", "EM_ANALISE", "EM_CORRECAO", "RESOLVIDA", "CANCELADA"),
    "status_passaporte_enum": ("RASCUNHO", "ATIVO", "REVOGADO", "EM_VALIDACAO", "PUBLICADO"),
    "status_plano_acao_enum": ("PENDENTE", "EM_ANDAMENTO", "CONCLUIDO", "ATRASADO", "CANCELADO"),
    "status_programa_enum": ("ATIVO", "INATIVO", "SUSPENSO"),
    "status_relatorio_esg_enum": ("RASCUNHO", "EM_REVISAO", "PUBLICADO", "ARQUIVADO", "CANCELADO"),
    "statusalerta": ("NOVO", "EM_ANALISE", "RESOLVIDO", "IGNORADO"),
    "statuscar": ("ATIVO", "PENDENTE", "CANCELADO", "SUSPENSO", "EM_ANALISE"),
    "statuscontrato": ("ATIVO", "ENCERRADO", "RESCINDIDO", "SUSPENSO"),
    "statusdocumento": ("ATIVO", "SUBSTITUIDO", "VENCIDO", "CANCELADO"),
    "statusoutorga": ("ATIVA", "VENCIDA", "SUSPENSA", "CANCELADA", "EM_RENOVACAO"),
    "statusparcela": ("PREVISTA", "PAGA", "CANCELADA", "VENCIDA"),
    "statussefaz": ("EM_DIGITACAO", "ASSINADA", "TRANSMITIDA", "AUTORIZADA", "CANCELADA", "DENEGADA", "INUTILIZADA"),
    "ticketpriority": ("BAIXA", "MEDIA", "ALTA", "URGENTE"),
    "ticketstatus": ("ABERTO", "EM_ATENDIMENTO", "AGUARDANDO_CLIENTE", "CONCLUIDO", "CANCELADO"),
    "tipo_certificacao_enum": ("ORGANICO", "GLOBALGAP", "REGENAGRI", "ESG_INTERNO", "OUTRO"),
    "tipo_evento_passaporte_enum": ("GERADO", "VALIDADO", "PUBLICADO", "REVOGADO", "ATUALIZADO"),
    "tipo_evidencia_enum": ("DOCUMENTO_PDF", "FOTO_CAMPO", "DADO_SATELITE", "OUTRO"),
    "tipoalerta": ("DESMATAMENTO", "QUEIMADA", "INUNDACAO", "EROSAO", "OUTRO"),
    "tipoarrendatario": ("PESSOA_FISICA", "PESSOA_JURIDICA", "FAZENDA_TENANT"),
    "tipocategoria": ("despesa", "receita", "operacao", "produto", "insumo"),
    "tipocontrato": ("ARRENDAMENTO", "PARCERIA"),
    "tipodocumento": ("CCIR", "ITR_DITR", "CAR", "ESCRITURA", "MATRICULA", "GEOREFERENCIAMENTO", "OUTRO"),
    "tipoimovel": ("RURAL", "PARTICULAR", "DEVOLUTA", "POSSE"),
    "tiponf": ("NFP_E", "NF_E", "NFC_E"),
    "tipousooutorga": ("IRRIGACAO", "DESSEDENTACAO", "USO_INDUSTRIAL", "AQUICULTURA", "OUTRO"),
    "valormodalidade": ("FIXO_BRL", "FIXO_SACAS", "PERCENTUAL"),
}

SEQUENCE_NAMES = (
    "amostras_id_seq", "animal_genetica_id_seq", "balanca_webhook_credentials_id_seq",
    "carbono_emissoes_id_seq", "carbono_projetos_id_seq", "carbono_relatorios_id_seq", "case_ih_id_seq",
    "cochos_id_seq", "comparador_precos_id_seq", "confinamento_lotes_id_seq",
    "diagnosticos_id_seq", "integration_credentials_id_seq", "integration_features_id_seq",
    "integration_health_snapshots_id_seq", "integration_sync_policies_id_seq",
    "integration_versions_id_seq", "john_deere_id_seq", "mapas_fertilidade_id_seq",
    "marketplace_integracoes_id_seq", "modelos_ml_id_seq", "pragas_doencas_id_seq",
    "racas_id_seq", "racoes_tmr_id_seq", "recomendacoes_id_seq", "sankhya_config_id_seq",
    "sankhya_lancamentos_financeiros_id_seq", "sankhya_nfe_id_seq", "sankhya_pessoas_id_seq",
    "sankhya_produtos_id_seq", "sankhya_tabelas_id_seq", "sugestoes_acasalamento_id_seq",
    "tenant_integracoes_id_seq", "territory_legacy_backup_01h2_id_seq", "tratamentos_id_seq",
    "whatsapp_id_seq",
)

EXCLUDED_SEQUENCE_NAMES = frozenset({
    "amostras_id_seq",
    "mapas_fertilidade_id_seq",
    "territory_legacy_backup_01h2_id_seq",
})
REQUIRED_SEQUENCE_NAMES = frozenset(SEQUENCE_NAMES) - EXCLUDED_SEQUENCE_NAMES
SEQUENCE_CONTRACT = {
    name: {
        "schema": BASELINE_SCHEMA,
        "name": name,
        "owned_table": name.removesuffix("_id_seq"),
        "owned_column": "id",
        "data_type": "bigint" if name.startswith("sankhya_") else "integer",
        "start": 1,
        "increment": 1,
        "minvalue": 1,
        "maxvalue": 9223372036854775807 if name.startswith("sankhya_") else 2147483647,
        "cache": 1,
        "cycle": False,
        "identity_or_serial": "SERIAL",
        "baseline_decision": "REQUIRED" if name in REQUIRED_SEQUENCE_NAMES else "NOT_REQUIRED",
    }
    for name in SEQUENCE_NAMES
}

RLS_ENABLED_TABLES = frozenset({
    "alert_events", "alert_indicators", "alert_insights", "alert_lifecycle_events", "amb_alertas",
    "amb_outorgas_hidricas", "amb_registros_car", "balanca_inbound_events", "balanca_webhook_credentials",
    "carbono_emissoes", "carbono_projetos", "carbono_relatorios", "certificacao_avaliacoes",
    "certificacao_checklists", "certificacao_criterios", "certificacao_evidencias",
    "certificacao_nao_conformidades", "certificacao_planos_acao", "certificacao_programas",
    "configuracao_fazenda", "domain_event_outbox", "esg_relatorio_evidencias", "esg_relatorio_indicadores",
    "esg_relatorios", "integration_credentials", "integration_external_record_link_history",
    "integration_external_record_links", "integration_features", "integration_health_snapshots",
    "integration_jobs", "integration_sync_policies", "integration_versions", "modelos_fitossanitarios",
    "modelos_zoosanitarios", "operational_alerts", "previsoes_clima", "propriedade_imovel",
    "rastreabilidade_passaporte_eventos", "rastreabilidade_passaporte_evidencias", "rastreabilidade_passaportes",
    "recommendation_lifecycle_events", "recommendation_results", "registros_clima", "tenant_integracoes",
    "wizard_implantacoes_checklist_itens", "wizard_implantacoes_etapas", "wizard_implantacoes_historico",
    "wizard_implantacoes_operacionais", "wizard_implantacoes_pendencias",
})
RLS_FORCED_TABLES = RLS_ENABLED_TABLES - {"propriedade_imovel"}


def build_rls_contract() -> dict[str, dict[str, object]]:
    """Return one explicit RLS decision for every approved baseline table."""
    from core.database import Base
    from core.model_registry import baseline_candidate_tables, register_models

    register_models()
    baseline = baseline_candidate_tables()
    contract = {}
    for name in sorted(baseline):
        enabled = name in RLS_ENABLED_TABLES
        contract[name] = {
            "table": name,
            "tenant_scope_mode": "DIRECT" if "tenant_id" in Base.metadata.tables[name].c else "GLOBAL",
            "enabled": enabled,
            "forced": name in RLS_FORCED_TABLES,
            "classification": (
                "RLS_REQUIRED"
                if enabled and name in RLS_FORCED_TABLES
                else "RLS_REQUIRED_NO_FORCE"
                if enabled
                else "RLS_NOT_REQUIRED"
            ),
            "source": "DATABASE_CURRENT" if enabled else "MANUAL_CONTRACT",
            "reason": "physical RLS contract preserved" if enabled else "no approved RLS policy in reference contract",
        }
    return contract


RLS_CONTRACT = build_rls_contract()

FUNCTION_CONTRACT = {
    "fn_estoque_movimentos_append_only": {"decision": "INCLUDE", "language": "plpgsql", "return": "trigger"},
    "fn_production_units_refresh_status": {"decision": "INCLUDE", "language": "plpgsql", "return": "trigger"},
    "fn_production_units_valida_soma": {"decision": "INCLUDE", "language": "plpgsql", "return": "trigger"},
}

TRIGGER_CONTRACT = {
    "tg_estoque_movimentos_append_only": {"table": "estoque_movimentos", "decision": "INCLUDE", "timing": "BEFORE", "events": ("DELETE", "UPDATE")},
    "tg_production_units_refresh_status": {"table": "production_units", "decision": "INCLUDE", "timing": "AFTER", "events": ("INSERT", "DELETE", "UPDATE")},
    "tg_production_units_valida_soma": {"table": "production_units", "decision": "INCLUDE", "timing": "AFTER", "events": ("INSERT", "UPDATE"), "deferrable": True, "initially_deferred": True},
}

PHYSICAL_TABLES_OUTSIDE_BASELINE = frozenset({
    "alembic_version", "amostras", "mapas_fertilidade", "territory_legacy_backup_01h2",
    "balanca_afericoes", "balanca_avaliacoes_prestador", "balanca_dispositivos", "balanca_fisicas",
    "balanca_operadores", "balanca_ordens", "balanca_pesagens", "balanca_sync_tombstones",
})

# Explicit blockers: these are intentionally machine-readable.  A future
# phase may close them only after object-level decisions are committed here.
UNRESOLVED_STRUCTURAL_AREAS = (
    "248 FK table divergences require object-level Tenant Integrity reconciliation",
    "489 type differences require semantic per-column contract",
    "383 default-presence differences require server-default separation",
    "98 default-expression differences require explicit baseline definitions",
    "11 UNIQUE divergent tables require representation decisions",
    "39 CHECK divergent tables require semantic decisions",
    "327 index-divergent tables require final manual/performance index set",
    "188 policies require frozen definitions and approved baseline membership",
    "function and trigger full definitions are captured in the report but not yet emitted as baseline DDL",
)

CONTRACT_STATUS = "NO-GO"

# Counts are deliberately explicit rather than inferred as zero.  They are
# the current closure gate consumed by the 01C.3 tests and report.
UNRESOLVED_COUNTS = {
    "fk": 0,
    "fk_target": 0,
    "nullable": 0,
    "meaningful_type": 0,
    "structural_default": 0,
    "unique": 11,
    "check": 39,
    "enum": 0,
    "sequence": 0,
    "rls": 0,
    "policy": 0,
    "function": 3,
    "trigger": 3,
    "required_index": 327,
}

# These summaries make the boundary explicit: historical differences are not
# all DDL blockers for a clean CREATE TABLE compilation.
TYPE_DECISIONS = {
    "historical_difference_count": 489,
    "representation_only_policy": "VARCHAR/CHARACTER VARYING and safe FLOAT rendering",
    "type_blocker_for_create": 0,
}
SERVER_DEFAULT_DECISIONS = {
    "historical_difference_count": 481,
    "python_side_defaults_excluded": True,
    "unresolved_required_server_default": 0,
}
TENANT_INTEGRITY_ON_DELETE = "RESTRICT"
UNIQUE_CONTRACT = {}
CHECK_CONTRACT = {}
POLICY_SNAPSHOT_GZIP_B64 = (
    """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"""
)


def load_policy_contract() -> dict[tuple[str, str, str], dict[str, object]]:
    """Decode the read-only pg_policies snapshot captured for this phase."""
    rows = json.loads(gzip.decompress(base64.b64decode(POLICY_SNAPSHOT_GZIP_B64)))
    return {
        (row["schemaname"], row["tablename"], row["policyname"]): {
            "schema": row["schemaname"],
            "table": row["tablename"],
            "name": row["policyname"],
            "command": row["cmd"],
            "roles": tuple(row["roles"]),
            "permissive": row["permissive"] == "PERMISSIVE",
            "using_expression": row["qual"],
            "with_check_expression": row["with_check"],
            "source": "DATABASE_CURRENT",
            "reason": "policy captured from pg_policies and target is in baseline",
        }
        for row in rows
    }


POLICY_CONTRACT = load_policy_contract()
POLICY_INVALID_COUNT = 0
POLICY_OUTSIDE_BASELINE_COUNT = 0
INDEX_CONTRACT = {}


def build_fk_contract() -> dict[tuple[str, str, tuple[str, ...]], dict[str, object]]:
    """Build the complete baseline FK matrix from the official ORM."""
    from core.database import Base
    from core.model_registry import baseline_candidate_tables, register_models

    register_models()
    baseline = baseline_candidate_tables()
    matrix: dict[tuple[str, str, tuple[str, ...]], dict[str, object]] = {}
    for table in Base.metadata.tables.values():
        if table.name not in baseline:
            continue
        for constraint in table.foreign_key_constraints:
            elements = tuple(constraint.elements)
            if not elements:
                continue
            first = elements[0]
            target_table = first.column.table.name
            if target_table not in Base.metadata.tables:
                classification = "INVALID"
            elif target_table == "tenants" and (constraint.ondelete or "NO ACTION").upper() == "CASCADE":
                classification = "TENANT_INTEGRITY_OVERRIDE"
            else:
                classification = "ORM_CURRENT"
            source_columns = tuple(element.parent.name for element in elements)
            target_columns = tuple(element.column.name for element in elements)
            key = (table.name, constraint.name or "", source_columns)
            matrix[key] = {
                "source_table": table.name,
                "constraint_name": constraint.name,
                "source_columns": source_columns,
                "target_table": target_table,
                "target_columns": target_columns,
                "orm_on_delete": constraint.ondelete,
                "orm_on_update": constraint.onupdate,
                "baseline_on_delete": (
                    TENANT_INTEGRITY_ON_DELETE
                    if classification == "TENANT_INTEGRITY_OVERRIDE"
                    else (constraint.ondelete or "NO ACTION").upper()
                ),
                "baseline_on_update": (constraint.onupdate or "NO ACTION").upper(),
                "classification": classification,
                "source_of_decision": (
                    "TENANT_INTEGRITY"
                    if classification == "TENANT_INTEGRITY_OVERRIDE"
                    else "ORM"
                ),
            }
    return matrix


FK_CONTRACT = build_fk_contract()
FK_DIVERGENT_TABLES_INITIAL = 248
