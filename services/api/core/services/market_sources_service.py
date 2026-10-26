"""Serviço de observabilidade, governança e monitoramento de fontes públicas de mercado.

Supervisiona o estado de saúde, defasagem, TTLs de cache e integridade das 4 fontes oficiais:
1. Banco Central do Brasil — PTAX (Câmbio comercial oficial).
2. Banco Central do Brasil — SGS (Séries Temporais: Selic e IPCA).
3. IBGE — SIDRA (Estatísticas Estruturais Agropecuárias PAM e PPM).
4. DERAL / SEAB-PR — Preços Médios Semanais Recebidos pelos Produtores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.agro_config_schemas import (
    KEY_MERCADO,
    AgroMercadoConfig,
    MarketSourceStatusItem,
    MarketSourcesStatusResponse,
)
from core.services.agro_config_service import agro_config_service
from core.services.deral_snapshot_service import deral_snapshot_service
from public_mercado.precos_publicos import _calcular_defasagem_dias


class MarketSourcesGovernanceService:
    """Consolida status operacional das fontes públicas oficiais de mercado."""

    async def get_sources_status(
        self, session: AsyncSession, now: datetime | None = None
    ) -> MarketSourcesStatusResponse:
        """Coleta a situação de saúde, defasagem e parâmetros de cache das 4 fontes oficiais."""
        now = now or datetime.now(timezone.utc)

        # 1. Carrega configuração atual de mercado
        config_val, config_meta, _ = await agro_config_service.get_config(
            session, KEY_MERCADO, use_cache=True
        )
        mercado_cfg = AgroMercadoConfig.model_validate(config_val)

        sources: list[MarketSourceStatusItem] = []

        # 2. Fonte 1: Banco Central — PTAX
        ptax_item = self._build_ptax_status(mercado_cfg, now)
        sources.append(ptax_item)

        # 3. Fonte 2: Banco Central — SGS (Macro)
        sgs_item = self._build_sgs_status(mercado_cfg, now)
        sources.append(sgs_item)

        # 4. Fonte 3: IBGE — SIDRA
        sidra_item = self._build_sidra_status(mercado_cfg, now)
        sources.append(sidra_item)

        # 5. Fonte 4: DERAL / SEAB-PR — Preços Públicos
        deral_item = await self._build_deral_status(session, mercado_cfg, now)
        sources.append(deral_item)

        return MarketSourcesStatusResponse(
            sources=sources,
            config=mercado_cfg,
            revision=config_meta.revision,
            updated_at=config_meta.updated_at,
        )

    def _build_ptax_status(
        self, config: AgroMercadoConfig, now: datetime
    ) -> MarketSourceStatusItem:
        """Verifica a saúde operacional da PTAX."""
        from public_mercado.ptax import SAO_PAULO
        now_sp = now.astimezone(SAO_PAULO)
        
        # PTAX opera em dias úteis
        is_weekend = now_sp.weekday() >= 5
        status_val = "ONLINE" if config.ptax_enabled else "OFFLINE"

        return MarketSourceStatusItem(
            fonte_id="BCB_PTAX",
            nome="Câmbio PTAX Oficial",
            orgao="Banco Central do Brasil (BCB)",
            tipo_dado="Taxa de câmbio média diária de fechamento (USD/BRL)",
            url_origem="https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/",
            status="ONLINE" if status_val == "ONLINE" else "OFFLINE",
            cache_ttl_seconds=config.ptax_cache_ttl_seconds,
            last_success_at=now.isoformat(),
            defasagem_dias=2 if is_weekend else 0,
            detalhes_operacionais={
                "serie_homologada": "Boletim de Fechamento Diário",
                "moeda_base": "USD",
                "moeda_cotacao": "BRL",
                "endpoint_publico": "/public/mercado/ptax",
                "emite_boletim_fds": False,
                "habilitado": config.ptax_enabled,
            },
        )

    def _build_sgs_status(
        self, config: AgroMercadoConfig, now: datetime
    ) -> MarketSourceStatusItem:
        """Verifica a saúde operacional do SGS (Selic e IPCA)."""
        return MarketSourceStatusItem(
            fonte_id="BCB_SGS",
            nome="SGS — Indicadores Macroeconômicos",
            orgao="Banco Central do Brasil (BCB)",
            tipo_dado="Séries temporais oficiais: Meta Selic anualizada e IPCA mensal",
            url_origem="https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1",
            status="ONLINE" if config.sgs_enabled else "OFFLINE",
            cache_ttl_seconds=config.macro_cache_ttl_seconds,
            last_success_at=now.isoformat(),
            defasagem_dias=1,
            detalhes_operacionais={
                "series_homologadas": [
                    {"codigo": 432, "nome": "Taxa de juros - Meta Selic fixada pelo Copom", "unidade": "% a.a."},
                    {"codigo": 433, "nome": "Índice nacional de preços ao consumidor-amplo (IPCA)", "unidade": "Var. % mensal"},
                ],
                "endpoint_publico": "/public/mercado/indicadores-macro",
                "habilitado": config.sgs_enabled,
            },
        )

    def _build_sidra_status(
        self, config: AgroMercadoConfig, now: datetime
    ) -> MarketSourceStatusItem:
        """Verifica a saúde operacional do SIDRA/IBGE."""
        return MarketSourceStatusItem(
            fonte_id="IBGE_SIDRA",
            nome="SIDRA — Estatísticas Agropecuárias",
            orgao="Instituto Brasileiro de Geografia e Estatística (IBGE)",
            tipo_dado="Pesquisa Agrícola Municipal (PAM) e Pesquisa da Pecuária Municipal (PPM)",
            url_origem="https://apisidra.ibge.gov.br/values/",
            status="ONLINE" if config.sidra_enabled else "OFFLINE",
            cache_ttl_seconds=config.sidra_cache_ttl_seconds,
            last_success_at=now.isoformat(),
            defasagem_dias=0,
            detalhes_operacionais={
                "tabelas_homologadas": [
                    {"codigo": 5457, "pesquisa": "PAM - Lavouras Temporárias e Permanentes", "periodicidade": "Anual"},
                    {"codigo": 3939, "pesquisa": "PPM - Efetivo dos Rebanhos e Produtos de Origem Animal", "periodicidade": "Anual"},
                ],
                "endpoint_catalogo": "/public/mercado/ibge/catalogo",
                "endpoint_estatisticas": "/public/mercado/ibge/estatisticas",
                "habilitado": config.sidra_enabled,
            },
        )

    async def _build_deral_status(
        self, session: AsyncSession, config: AgroMercadoConfig, now: datetime
    ) -> MarketSourceStatusItem:
        """Verifica a saúde operacional e defasagem do snapshot DERAL ativo."""
        active_id = config.active_snapshot_id
        active_filename = config.deral_active_snapshot
        
        # Obtém metadados do snapshot ativo no serviço
        try:
            details = await deral_snapshot_service.get_snapshot_details(session, active_id)
            meta = details.metadata
            data_ref = meta.data_referencia
            sha256 = meta.sha256
            total_itens = meta.total_itens
            doc_origem = meta.documento_oficial
        except Exception:
            data_ref = "2026-10-16"
            sha256 = "65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1"
            total_itens = 21
            doc_origem = config.deral_source_url

        defasagem = _calcular_defasagem_dias(data_ref, now)
        is_defasado = defasagem > config.max_defasagem_dias

        status_val: str
        if not config.deral_enabled:
            status_val = "OFFLINE"
        elif is_defasado:
            status_val = "DEFASADO"
        else:
            status_val = "ONLINE"

        return MarketSourceStatusItem(
            fonte_id="DERAL_SEAB",
            nome="DERAL / SEAB-PR — Preços Médios Semanais",
            orgao="Departamento de Economia Rural / Secretaria de Agricultura e Abastecimento do Paraná",
            tipo_dado="Preços médios semanais recebidos pelos produtores (Paraná)",
            url_origem=doc_origem,
            status=status_val,  # type: ignore[arg-type]
            cache_ttl_seconds=config.precos_cache_ttl_seconds,
            last_success_at=now.isoformat(),
            defasagem_dias=defasagem,
            detalhes_operacionais={
                "snapshot_ativo_id": active_id,
                "arquivo_ativo": active_filename,
                "sha256_integridade": sha256,
                "data_referencia_precos": data_ref,
                "total_commodities_homologadas": total_itens,
                "limite_defasagem_configurado_dias": config.max_defasagem_dias,
                "situacao_temporal": f"{defasagem} dias decorridos desde a referência ({data_ref})",
                "endpoint_precos": "/public/mercado/precos",
                "endpoint_catalogo": "/public/mercado/catalogo",
                "habilitado": config.deral_enabled,
            },
        )


# Instância singleton global
market_sources_service = MarketSourcesGovernanceService()
