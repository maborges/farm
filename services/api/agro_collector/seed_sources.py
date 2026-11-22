"""Seed idempotente das fontes iniciais homologadas (Fase 0 / Fase 1A)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AgroDataSource

DEFAULT_AGRO_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "domain": "MERCADO",
        "slug": "deral_pr",
        "nome": "DERAL / SEAB-PR — Preços Recebidos pelos Produtores",
        "sigla": "DERAL/SEAB-PR",
        "tipo_licenca": "DADO_PUBLICO_GOV",
        "atribuicao_obrigatoria": (
            "Fonte: DERAL/SEAB-PR — Preços Recebidos pelos Produtores (Prp.xls)."
        ),
        "uf_padrao": "PR",
        "praca_padrao": "Paraná — Média Estadual",
        "dominios_whitelist": ["www.agricultura.pr.gov.br", "agricultura.pr.gov.br"],
        "url_principal": (
            "https://www.agricultura.pr.gov.br/sites/default/arquivos_restritos/"
            "files/documento/2026-10/prp.xls"
        ),
        "url_indice": "https://www.agricultura.pr.gov.br/deral/precos",
        "estrategia_coleta": "NIVEL1_DETERMINISTICO",
        "config_extrator": {"formato": "xls_deral"},
        "cron_ou_intervalo_seg": 43200,
        "auto_publish_policy": "AUTO_SE_GUARDRAILS_OK",
        "max_variacao_pct": Decimal("15.00"),
        "max_defasagem_dias": 14,
        "prioridade_exibicao": 1,
        "ativo": True,
    },
    {
        "domain": "MERCADO",
        "slug": "iea_sp",
        "nome": "IEA / SAA-SP — Preços Diários Recebidos pela Agropecuária Paulista",
        "sigla": "IEA/SAA-SP",
        "tipo_licenca": "DADO_PUBLICO_GOV",
        "atribuicao_obrigatoria": (
            "Fonte: Instituto de Economia Agrícola (IEA/SAA-SP) — Preços Diários Recebidos."
        ),
        "uf_padrao": "SP",
        "praca_padrao": "São Paulo — Média Estadual (EDRs)",
        "dominios_whitelist": ["infoiea.agricultura.sp.gov.br", "agricultura.sp.gov.br"],
        "url_principal": "https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos",
        "url_indice": "https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos",
        "estrategia_coleta": "NIVEL1_DETERMINISTICO",
        "config_extrator": {"formato": "html_antiforgery_ajax"},
        "cron_ou_intervalo_seg": 21600,
        "auto_publish_policy": "AUTO_SE_GUARDRAILS_OK",
        "max_variacao_pct": Decimal("12.00"),
        "max_defasagem_dias": 7,
        "prioridade_exibicao": 1,
        "ativo": True,
    },
    {
        "domain": "MERCADO",
        "slug": "emater_rs",
        "nome": "EMATER/RS-ASCAR — Cotações Agropecuárias Semanais (PDF)",
        "sigla": "EMATER/RS",
        "tipo_licenca": "DADO_PUBLICO_GOV",
        "atribuicao_obrigatoria": "Fonte: EMATER/RS-ASCAR — Levantamento Semanal de Preços.",
        "uf_padrao": "RS",
        "praca_padrao": "Rio Grande do Sul — Estado",
        "dominios_whitelist": ["www.emater.tche.br", "emater.tche.br"],
        "url_principal": "https://www.emater.tche.br/site/area-tecnica/precos-semanais.php",
        "url_indice": "https://www.emater.tche.br/site/area-tecnica/precos-semanais.php",
        "estrategia_coleta": "NIVEL2_IA_PDF_HTML",
        "config_extrator": {"formato": "pdf_semanal"},
        "cron_ou_intervalo_seg": 86400,
        "auto_publish_policy": "SEMPRE_REVISAO_HUMANA",
        "max_variacao_pct": Decimal("12.00"),
        "max_defasagem_dias": 14,
        "prioridade_exibicao": 1,
        "ativo": False,
    },
    {
        "domain": "MERCADO",
        "slug": "seapa_mg",
        "nome": "SEAPA-MG / Agrodados — Preços Correntes (PDF)",
        "sigla": "SEAPA-MG",
        "tipo_licenca": "DADO_PUBLICO_GOV",
        "atribuicao_obrigatoria": "Fonte: SEAPA-MG — Agrodados / Preços Correntes Semanais.",
        "uf_padrao": "MG",
        "praca_padrao": "Minas Gerais — Estado",
        "dominios_whitelist": ["www.mg.gov.br", "mg.gov.br"],
        "url_principal": (
            "https://www.mg.gov.br/system/files/media/agricultura/documento_detalhado/"
            "2026/dados-conjunturais/precos-correntes/"
            "precos-correntes-de-produtos-selecionado-17-11-2026.pdf"
        ),
        "url_indice": "https://www.mg.gov.br/agricultura/pagina/agrodados-precos-correntes",
        "estrategia_coleta": "NIVEL2_IA_PDF_HTML",
        "config_extrator": {"formato": "pdf_semanal"},
        "cron_ou_intervalo_seg": 86400,
        "auto_publish_policy": "SEMPRE_REVISAO_HUMANA",
        "max_variacao_pct": Decimal("12.00"),
        "max_defasagem_dias": 14,
        "prioridade_exibicao": 1,
        "ativo": False,
    },
    {
        "domain": "MERCADO",
        "slug": "conab_nacional",
        "nome": "CONAB / MAPA — Preços Agropecuários Oficiais",
        "sigla": "CONAB/MAPA",
        "tipo_licenca": "LINK_HOMOLOGADO_APENAS",
        "atribuicao_obrigatoria": "Referência institucional: CONAB / MAPA.",
        "uf_padrao": "BR",
        "praca_padrao": "Brasil — Referência Nacional",
        "dominios_whitelist": ["www.gov.br", "gov.br"],
        "url_principal": (
            "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/"
            "precos-agropecuarios"
        ),
        "url_indice": None,
        "estrategia_coleta": "NIVEL1_DETERMINISTICO",
        "config_extrator": {},
        "cron_ou_intervalo_seg": 86400,
        "auto_publish_policy": "SEMPRE_REVISAO_HUMANA",
        "max_variacao_pct": Decimal("12.00"),
        "max_defasagem_dias": 30,
        "prioridade_exibicao": 3,
        "ativo": False,
    },
    {
        "domain": "MERCADO",
        "slug": "epagri_sc",
        "nome": "EPAGRI / Infoagro-SC — Painel Catarinense de Preços",
        "sigla": "EPAGRI/CEPA-SC",
        "tipo_licenca": "LINK_HOMOLOGADO_APENAS",
        "atribuicao_obrigatoria": "Referência institucional: EPAGRI/Cepa — Infoagro SC.",
        "uf_padrao": "SC",
        "praca_padrao": "Santa Catarina — Estado",
        "dominios_whitelist": ["infoagro.sc.gov.br", "cepa.epagri.sc.gov.br"],
        "url_principal": "https://infoagro.sc.gov.br/",
        "url_indice": "https://cepa.epagri.sc.gov.br/",
        "estrategia_coleta": "NIVEL1_DETERMINISTICO",
        "config_extrator": {},
        "cron_ou_intervalo_seg": 86400,
        "auto_publish_policy": "SEMPRE_REVISAO_HUMANA",
        "max_variacao_pct": Decimal("12.00"),
        "max_defasagem_dias": 14,
        "prioridade_exibicao": 1,
        "ativo": False,
    },
)


async def ensure_default_sources(session: AsyncSession) -> list[AgroDataSource]:
    """Insere fontes homologadas iniciais que ainda não existam em ``agro_data_sources``.

    Args:
        session: Sessão SQLAlchemy ativa.

    Returns:
        Lista atualizada de todas as fontes encontradas/inseridas ordenadas por slug.
    """
    existing = list((await session.execute(select(AgroDataSource))).scalars().all())
    by_slug = {src.slug: src for src in existing}
    created_any = False

    for spec in DEFAULT_AGRO_SOURCES:
        if spec["slug"] in by_slug:
            continue
        source = AgroDataSource(**spec)
        session.add(source)
        by_slug[source.slug] = source
        created_any = True

    if created_any:
        await session.flush()

    return [by_slug[k] for k in sorted(by_slug)]
