"""Bootstrap mínimo para o domínio de Certificações/ESG."""

from core.database import Base
import core.models  # noqa: F401


def test_certificacao_esg_tables_registradas_no_metadata():
    tables = set(Base.metadata.tables.keys())

    assert {
        "certificacao_programas",
        "certificacao_checklists",
        "certificacao_criterios",
        "certificacao_avaliacoes",
        "certificacao_evidencias",
        "certificacao_nao_conformidades",
        "certificacao_planos_acao",
        "esg_relatorios",
        "esg_relatorio_indicadores",
        "esg_relatorio_evidencias",
        "rastreabilidade_passaportes",
        "rastreabilidade_passaporte_eventos",
        "rastreabilidade_passaporte_evidencias",
    }.issubset(tables)
