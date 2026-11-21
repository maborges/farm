"""Integração resiliente de cotações públicas da arroba para pecuária."""

from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession


async def obter_cotacao_boi_gordo_referencia(
    session: AsyncSession | None = None,
) -> tuple[float | None, str | None]:
    """Obtém a cotação pública de referência do boi gordo sem falhar o chamador.

    Args:
        session: Sessão opcional para sincronizar o snapshot ativo DERAL.

    Returns:
        Tupla (valor_arroba, sigla_fonte) ou (None, None) se indisponível.
    """
    try:
        from public_mercado.precos_publicos_service import get_precos_service

        precos_service = get_precos_service()
        if session is not None:
            try:
                await precos_service.sincronizar_snapshot_ativo(session)
            except Exception:
                pass
        item = await precos_service.get_preco_commodity("boi-gordo")
        if item is None or item.valor <= 0:
            return None, None
        return round(float(item.valor), 2), item.siglaFonte
    except Exception:
        return None, None


async def resolver_cotacao_boi_gordo_contexto(
    session: AsyncSession | None = None,
    tenant_id: uuid.UUID | None = None,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> tuple[float | None, str | None]:
    """Prioriza cotação regional (Fazenda > Tenant) antes da referência pública DERAL.

    Args:
        session: Sessão assíncrona do banco para consulta regional e snapshot DERAL.
        tenant_id: Identificador do tenant proprietário.
        unidade_produtiva_id: Fazenda/unidade produtiva opcional do lote.

    Returns:
        Tupla (valor_arroba, rotulo_fonte) ou fallback para obter_cotacao_boi_gordo_referencia.
    """
    if session is not None and tenant_id is not None:
        try:
            from core.cadastros.commodities.cotacao_regional_service import CotacaoRegionalService

            svc = CotacaoRegionalService(session, tenant_id)
            mapa_faz = await svc._carregar_mapa_fazenda(unidade_produtiva_id)
            entry_faz = mapa_faz.get("BOI_GORDO")
            if entry_faz and entry_faz.get("valor"):
                praca = str(entry_faz.get("praca") or "").strip()
                return round(float(entry_faz["valor"]), 2), f"Regional ({praca})" if praca else "Regional"
            mapa_ten = await svc._carregar_mapa_tenant()
            entry_ten = mapa_ten.get("BOI_GORDO")
            if entry_ten and entry_ten.get("valor"):
                praca = str(entry_ten.get("praca") or "").strip()
                return round(float(entry_ten["valor"]), 2), f"Regional ({praca})" if praca else "Regional"
        except Exception:
            pass
    return await obter_cotacao_boi_gordo_referencia(session)


def resolver_cotacao_lote(
    cotacao_override: float | None,
    cotacao_publica: tuple[float | None, str | None],
) -> tuple[float | None, str | None]:
    """Prioriza cotação personalizada do lote sobre a referência pública.

    Args:
        cotacao_override: Preço manual da arroba configurado no lote.
        cotacao_publica: Tupla (valor, sigla_fonte) da referência pública.

    Returns:
        Tupla (valor_efetivo, fonte_exibicao).
    """
    if cotacao_override is not None and float(cotacao_override) > 0:
        return round(float(cotacao_override), 2), "Personalizado"
    return cotacao_publica
