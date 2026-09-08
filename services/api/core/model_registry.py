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

# Models declared in code but without physical evidence in the audited
# database. They remain visible in the ORM registry, but are not approved for
# materialization by BASELINE-DEEPFARMS-V1 until adoption is decided.
BASELINE_PENDING_TABLES = frozenset({
    "api_keys", "api_logs", "api_versions", "arracoamentos", "balanco_hidrico",
    "benchmarks", "colaborador_apontamentos", "contratos_futuros",
    "crm_ofertas_personalizadas", "crm_planos_comerciais", "crm_precificacao_modulo",
    "crm_produtos", "enterprise_esg_relatorios", "esg_indicadores",
    "estacoes_meteorologicas", "growth_landing_eventos", "hedge_registros",
    "ilpf_modulos", "imagens_satelite", "integracao_new_holland",
    "maquinas_new_holland", "marketplace_avaliacoes", "mrv_projetos",
    "mrv_relatorios", "ndvi_registros", "pesagens", "pontos", "powerbi",
    "preditivo", "sap", "sdks", "sensores_iot", "sensores_leituras",
    "tanques_rede",
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
    """Return the conservative model subset proposed for the future baseline."""
    return frozenset(set(registered_tables()) - BASELINE_PENDING_TABLES)


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
