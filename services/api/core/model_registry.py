"""Canonical SQLAlchemy model registry for Alembic and metadata audits.

This module owns model discovery. It deliberately does not create tables or
execute database statements.
"""

from __future__ import annotations

import importlib
from collections import defaultdict
from types import MappingProxyType

from core.database import Base

# Explicit production model modules. Keep this list independent from routers,
# services, seed scripts and Alembic revision files.
MODEL_MODULES: tuple[str, ...] = (
    "agricola.a1_planejamento.models",
    "agricola.agronomo.models",
    "agricola.analises_solo.models",
    "agricola.beneficiamento.models",
    "agricola.cadastros.models",
    "agricola.caderno.models",
    "agricola.cenarios.models",
    "agricola.checklist.models",
    "agricola.climatico.models",
    "agricola.colheita.models",
    "agricola.cultivos.models",
    "agricola.custos.models",
    "agricola.fenologia.models",
    "agricola.logistica_reversa_embalagens.models",
    "agricola.models.operacao_tipo_fase",
    "agricola.models.templates",
    "agricola.monitoramento.catalogo_model",
    "agricola.monitoramento.models",
    "agricola.ndvi.models",
    "agricola.ndvi_avancado.models.balanco_hidrico",
    "agricola.ndvi_avancado.models.estacoes_meteorologicas",
    "agricola.ndvi_avancado.models.imagens_satelite",
    "agricola.ndvi_avancado.models.ndvi_registros",
    "agricola.operacoes.models",
    "agricola.planejamento_operacional.models",
    "agricola.prescricoes.models",
    "agricola.previsoes.models",
    "agricola.production_units.models",
    "agricola.rastreabilidade.models",
    "agricola.receitas_aplicacao.models",
    "agricola.receituario_agronomico.models",
    "agricola.romaneios.models",
    "agricola.safras.models",
    "agricola.tarefas.models",
    "alert_engine.models",
    "ambiental.models",
    "automacoes.models",
    "campo.models",
    "certificacoes_esg.models",
    "core.api_publica.models.api_keys",
    "core.api_publica.models.api_logs",
    "core.api_publica.models.api_versions",
    "core.api_publica.models.sdks",
    "core.cadastros.commodities.conversao",
    "core.cadastros.commodities.models",
    "core.cadastros.equipamentos.models",
    "core.cadastros.pessoas.models",
    "core.cadastros.produtos.models",
    "core.cadastros.propriedade_imovel.models",
    "core.cadastros.propriedades.models",
    "core.cadastros.propriedades.propriedade_models",
    "core.cadastros.tipos_servico.models",
    "core.measurements.models",
    "core.models.admin_audit_log",
    "core.models.admin_impersonation",
    "core.models.admin_user",
    "core.models.auth",
    "core.models.billing",
    "core.models.categoria_custom",
    "core.models.configuracao_fazenda",
    "core.models.configuration",
    "core.models.crm",
    "core.models.crm_ofertas",
    "core.models.cupom",
    "core.models.email_template",
    "core.models.historico_configuracao",
    "core.models.knowledge_base",
    "core.models.module_usage",
    "core.models.plan_changes",
    "core.models.sequencial",
    "core.models.sessao",
    "core.models.solicitacoes_comerciais",
    "core.models.solicitacoes_historico",
    "core.models.support",
    "core.models.tenant",
    "core.models.tenant_audit_log",
    "core.models.tenant_config",
    "core.models.unidade_produtiva",
    "enterprise.models.benchmarks",
    "enterprise.models.pontos",
    "enterprise.models.powerbi",
    "enterprise.models.preditivo",
    "enterprise.models.sap",
    "enterprise.models.sprints_27_33",
    "events.outbox_model",
    "financeiro.comercializacao.models",
    "financeiro.hedge.models",
    "financeiro.models.cenario",
    "financeiro.models.conciliacao",
    "financeiro.models.despesa",
    "financeiro.models.lancamento",
    "financeiro.models.nota_fiscal",
    "financeiro.models.ordem_pagamento",
    "financeiro.models.plano_acao",
    "financeiro.models.plano_conta",
    "financeiro.models.rateio",
    "financeiro.models.receita",
    "growth.models",
    "ia.models",
    "ia_diagnostico.models.diagnosticos",
    "ia_diagnostico.models.modelos_ml",
    "ia_diagnostico.models.pragas_doencas",
    "ia_diagnostico.models.recomendacoes",
    "ia_diagnostico.models.tratamentos",
    "imoveis.models.imovel",
    "imoveis.models.irrigacao",
    "imoveis.models.manutencao_benfeitoria",
    "integracoes.models",
    "integracoes.sankhya.models",
    "iot_integracao.models.case_ih",
    "iot_integracao.models.comparador_precos",
    "iot_integracao.models.john_deere",
    "iot_integracao.models.whatsapp",
    "iot_integracao.new_holland.models",
    "notificacoes.models",
    "operacional.models.abastecimento",
    "operacional.models.apontamento",
    "operacional.models.checklist",
    "operacional.models.compras",
    "operacional.models.contagem_estoque",
    "operacional.models.documento_equipamento",
    "operacional.models.estoque",
    "operacional.models.estoque_implantacao",
    "operacional.models.frota",
    "operacional.models.qualidade",
    "pecuaria.animal.models",
    "pecuaria.climatico.models",
    "pecuaria.models.manejo",
    "pecuaria.models.piquete",
    "pecuaria.producao.models",
    "recommendations.models",
    "rh.models",
    "wizard.models",
)

_loaded = False

# Final decisions from MIGRATION-METADATA-01C. Models remain visible in the
# registry even when excluded from the future baseline, so code is not erased
# merely because a feature is not deployed in the reference database.
BASELINE_DECISIONS: dict[str, str] = {
    "api_keys": "CODE_ONLY_NOT_DEPLOYED",
    "api_logs": "CODE_ONLY_NOT_DEPLOYED",
    "api_versions": "CODE_ONLY_NOT_DEPLOYED",
    "arracoamentos": "DEAD_ORPHAN_MODEL",
    "balanco_hidrico": "SUPERSEDED",
    "benchmarks": "CODE_ONLY_NOT_DEPLOYED",
    "colaborador_apontamentos": "DEAD_ORPHAN_MODEL",
    "contratos_futuros": "SUPERSEDED",
    "crm_ofertas_personalizadas": "ACTIVE_BASELINE",
    "crm_planos_comerciais": "ACTIVE_BASELINE",
    "crm_precificacao_modulo": "ACTIVE_BASELINE",
    "crm_produtos": "ACTIVE_BASELINE",
    "enterprise_esg_relatorios": "SUPERSEDED",
    "esg_indicadores": "SUPERSEDED",
    "estacoes_meteorologicas": "SUPERSEDED",
    "growth_landing_eventos": "ACTIVE_BASELINE",
    "hedge_registros": "SUPERSEDED",
    "ilpf_modulos": "DEAD_ORPHAN_MODEL",
    "imagens_satelite": "SUPERSEDED",
    "integracao_new_holland": "CODE_ONLY_NOT_DEPLOYED",
    "maquinas_new_holland": "CODE_ONLY_NOT_DEPLOYED",
    "marketplace_avaliacoes": "CODE_ONLY_NOT_DEPLOYED",
    "mrv_projetos": "DEAD_ORPHAN_MODEL",
    "mrv_relatorios": "DEAD_ORPHAN_MODEL",
    "ndvi_registros": "SUPERSEDED",
    "pesagens": "DEAD_ORPHAN_MODEL",
    "pontos": "DEAD_ORPHAN_MODEL",
    "powerbi": "CODE_ONLY_NOT_DEPLOYED",
    "preditivo": "CODE_ONLY_NOT_DEPLOYED",
    "sap": "CODE_ONLY_NOT_DEPLOYED",
    "sdks": "CODE_ONLY_NOT_DEPLOYED",
    "sensores_iot": "DEAD_ORPHAN_MODEL",
    "sensores_leituras": "DEAD_ORPHAN_MODEL",
    "tanques_rede": "DEAD_ORPHAN_MODEL",
}

BASELINE_EXCLUDED_TABLES = frozenset(
    name for name, decision in BASELINE_DECISIONS.items()
    if decision != "ACTIVE_BASELINE"
)

LEGACY_BALANCA_TABLES = frozenset({
    "balanca_afericoes", "balanca_avaliacoes_prestador", "balanca_dispositivos",
    "balanca_fisicas", "balanca_operadores", "balanca_ordens",
    "balanca_pesagens", "balanca_sync_tombstones",
})


def register_models() -> None:
    """Import every approved production model module exactly once."""
    global _loaded
    if _loaded:
        return
    for module_name in MODEL_MODULES:
        importlib.import_module(module_name)
    _loaded = True
    _assert_no_table_collisions()


def registered_tables() -> MappingProxyType:
    """Return the immutable current metadata table mapping."""
    register_models()
    return MappingProxyType(dict(Base.metadata.tables))


def baseline_candidate_tables() -> frozenset[str]:
    """Return the frozen ORM subset approved for the future baseline."""
    return frozenset(set(registered_tables()) - BASELINE_EXCLUDED_TABLES)


def table_owners() -> dict[str, tuple[str, ...]]:
    """Return mapped ORM owners for each registered table."""
    register_models()
    owners: dict[str, list[str]] = defaultdict(list)
    for mapper in Base.registry.mappers:
        table_name = mapper.local_table.fullname
        owner = f"{mapper.class_.__module__}.{mapper.class_.__name__}"
        owners[table_name].append(owner)
    return {name: tuple(sorted(values)) for name, values in owners.items()}


def _assert_no_table_collisions() -> None:
    collisions = {
        table: owners
        for table, owners in table_owners().items()
        if len(owners) > 1
    }
    if collisions:
        details = "; ".join(f"{table}: {owners}" for table, owners in sorted(collisions.items()))
        raise RuntimeError(f"Colisão de tabela no registry ORM: {details}")
