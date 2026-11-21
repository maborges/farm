"""Serviço multi-tenant de cotações regionais multi-fonte por Fazenda e Tenant/Grupo."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from core.exceptions import EntityNotFoundError
from core.models.configuracao_fazenda import ConfiguracaoFazenda
from core.models.tenant_config import ConfiguracaoTenant
from core.models.unidade_produtiva import UnidadeProdutiva
from public_mercado.precos_publicos import (
    METADADOS_CATALOGO,
    PrecoPublicoItem,
    carregar_precos_publicos,
)

from .schemas import (
    CotacaoRegionalHistoricoItem,
    CotacaoRegionalItemResponse,
    CotacaoRegionalUpsertRequest,
    FonteComparadaRegionalItem,
    PracaDeralResumoItem,
)

CATEGORIA_CONFIG_MERCADO = "mercado"
CHAVE_COTACOES_REGIONAIS = "cotacoes_regionais"
MAX_HISTORICO_POR_COMMODITY = 10
MAX_FONTES_POR_ESCOPO = 12

_CATALOGO_POR_CODIGO: dict[str, dict[str, object]] = {
    str(meta["id"]).upper().replace("-", "_"): meta for meta in METADADOS_CATALOGO
}


def normalizar_codigo_commodity(codigo: str) -> str:
    """Normaliza código da commodity (ex: 'boi-gordo' -> 'BOI_GORDO') contra o catálogo."""
    norm = str(codigo or "").strip().upper().replace("-", "_")
    if norm not in _CATALOGO_POR_CODIGO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Commodity '{codigo}' não homologada para cotação regional.",
        )
    return norm


def _atualizar_colecao_fontes(
    anterior: dict[str, Any] | None,
    nova_fonte: dict[str, Any],
) -> list[dict[str, Any]]:
    """Mantém lista de múltiplas fontes/praças cadastradas no mesmo escopo sem duplicar (praca, fonte)."""
    atuais = list((anterior or {}).get("fontes_regionais") or [])
    if not atuais and anterior and anterior.get("valor"):
        atuais.append({
            "valor": float(anterior["valor"]),
            "data_referencia": str(anterior.get("data_referencia") or ""),
            "praca": str(anterior.get("praca") or ""),
            "fonte": str(anterior.get("fonte") or "Cotação Regional"),
        })
    chave_nova = (
        str(nova_fonte["praca"]).strip().casefold(),
        str(nova_fonte["fonte"]).strip().casefold(),
    )
    filtradas = [
        item for item in atuais
        if isinstance(item, dict)
        and (
            str(item.get("praca") or "").strip().casefold(),
            str(item.get("fonte") or "").strip().casefold(),
        ) != chave_nova
    ]
    return [nova_fonte, *filtradas][:MAX_FONTES_POR_ESCOPO]


def _montar_entrada_regional(
    payload: CotacaoRegionalUpsertRequest,
    anterior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Serializa payload validado preservando múltiplas fontes da região e histórico recente."""
    now_iso = datetime.now(timezone.utc).isoformat()
    valor_round = round(float(payload.valor), 2)
    praca_limpa = payload.praca.strip()
    fonte_limpa = (payload.fonte or "Cotação Regional").strip()
    nova_fonte = {
        "valor": valor_round,
        "data_referencia": payload.data_referencia,
        "praca": praca_limpa,
        "fonte": fonte_limpa,
    }
    fontes_regionais = _atualizar_colecao_fontes(anterior, nova_fonte)
    modo = payload.modo_consolidacao
    if modo == "MEDIA_FONTES" and len(fontes_regionais) > 1:
        valores = [float(f["valor"]) for f in fontes_regionais if f.get("valor")]
        valor_efetivo_escopo = round(sum(valores) / len(valores), 2)
        nomes_f = ", ".join(str(f["fonte"]) for f in fontes_regionais[:3])
        fonte_resumo = f"Média Regional ({nomes_f})"
    else:
        valor_efetivo_escopo = valor_round
        fonte_resumo = fonte_limpa
    hist_ant = list((anterior or {}).get("historico") or [])
    novo_hist = {
        "valor": valor_round,
        "data_referencia": payload.data_referencia,
        "praca": praca_limpa,
        "fonte": fonte_limpa,
        "escopo": payload.escopo,
        "registrado_em": now_iso,
    }
    historico = [novo_hist, *hist_ant][:MAX_HISTORICO_POR_COMMODITY]
    return {
        "valor": valor_efetivo_escopo,
        "data_referencia": payload.data_referencia,
        "praca": praca_limpa,
        "fonte": fonte_resumo,
        "modo_consolidacao": modo,
        "fontes_regionais": fontes_regionais,
        "observacoes": (payload.observacoes or "").strip() or None,
        "updated_at": now_iso,
        "historico": historico,
    }


async def _sincronizar_deral_do_banco(session: AsyncSession) -> None:
    """Sincroniza o cache em memória do worker com o snapshot DERAL ativo no PostgreSQL."""
    try:
        from core.services.deral_snapshot_service import deral_snapshot_service

        await deral_snapshot_service.sync_active_snapshot_from_db(session)
    except Exception:
        pass


def _carregar_mapa_deral() -> dict[str, PrecoPublicoItem]:
    """Lê referências DERAL do snapshot ativo já sincronizado em memória ou fallback."""
    try:
        return {item.id: item for item in carregar_precos_publicos()}
    except Exception:
        return {}


def _calcular_spread_deral(
    val_eff: float | None, val_deral: float | None
) -> tuple[float | None, float | None]:
    """Calcula diferença absoluta (R$) e percentual (%) contra a média DERAL."""
    if val_eff is None or val_deral is None or val_deral <= 0:
        return None, None
    diff_brl = round(val_eff - val_deral, 2)
    diff_pct = round(((val_eff - val_deral) / val_deral) * 100.0, 2)
    return diff_brl, diff_pct


def _extrair_historico_combinado(
    faz: dict[str, Any] | None, ten: dict[str, Any] | None
) -> list[CotacaoRegionalHistoricoItem]:
    """Combina e ordena os últimos registros de alteração da fazenda e do tenant."""
    brutos: list[dict[str, Any]] = []
    for origem_dict, escopo_padrao in ((faz, "FAZENDA"), (ten, "TENANT")):
        if not origem_dict:
            continue
        lista = origem_dict.get("historico")
        if isinstance(lista, list) and lista:
            brutos.extend(item for item in lista if isinstance(item, dict))
        elif origem_dict.get("valor"):
            brutos.append({
                "valor": float(origem_dict["valor"]),
                "data_referencia": str(origem_dict.get("data_referencia") or ""),
                "praca": str(origem_dict.get("praca") or ""),
                "fonte": str(origem_dict.get("fonte") or "Regional"),
                "escopo": escopo_padrao,
                "registrado_em": str(origem_dict.get("updated_at") or ""),
            })
    brutos.sort(key=lambda x: str(x.get("registrado_em") or ""), reverse=True)
    return [
        CotacaoRegionalHistoricoItem(
            valor=float(item["valor"]),
            data_referencia=str(item.get("data_referencia") or ""),
            praca=str(item.get("praca") or ""),
            fonte=str(item.get("fonte") or "Regional"),
            escopo="FAZENDA" if item.get("escopo") == "FAZENDA" else "TENANT",
            registrado_em=str(item.get("registrado_em") or ""),
        )
        for item in brutos[:MAX_HISTORICO_POR_COMMODITY]
        if item.get("valor")
    ]


def _extrair_fontes_escopo(
    bloco: dict[str, Any] | None, escopo: Literal["FAZENDA", "TENANT"]
) -> list[FonteComparadaRegionalItem]:
    """Extrai as fontes individuais salvas em um escopo (FAZENDA ou TENANT)."""
    if not bloco:
        return []
    lista = bloco.get("fontes_regionais")
    if isinstance(lista, list) and lista:
        return [
            FonteComparadaRegionalItem(
                escopo=escopo,
                fonte=str(f.get("fonte") or "Cotação Regional"),
                praca=str(f.get("praca") or ""),
                valor=round(float(f["valor"]), 2),
                data_referencia=str(f.get("data_referencia") or ""),
            )
            for f in lista
            if isinstance(f, dict) and f.get("valor")
        ]
    if bloco.get("valor"):
        return [
            FonteComparadaRegionalItem(
                escopo=escopo,
                fonte=str(bloco.get("fonte") or "Cotação Regional"),
                praca=str(bloco.get("praca") or ""),
                valor=round(float(bloco["valor"]), 2),
                data_referencia=str(bloco.get("data_referencia") or ""),
            )
        ]
    return []


def _montar_painel_fontes_comparadas(
    faz: dict[str, Any] | None,
    ten: dict[str, Any] | None,
    deral: PrecoPublicoItem | None,
) -> tuple[list[FonteComparadaRegionalItem], float | None, float | None, float | None, float | None]:
    """Combina todas as fontes da região (Fazenda, Tenant, Núcleo DERAL e Média DERAL) e calcula faixa."""
    fontes: list[FonteComparadaRegionalItem] = [
        *_extrair_fontes_escopo(faz, "FAZENDA"),
        *_extrair_fontes_escopo(ten, "TENANT"),
    ]
    praca_alvo = str((faz or {}).get("praca") or (ten or {}).get("praca") or "").casefold()
    if deral:
        if praca_alvo:
            nucleo = next(
                (p for p in deral.pracasRegionais if p.praca.casefold() in praca_alvo),
                None,
            )
            if nucleo:
                fontes.append(
                    FonteComparadaRegionalItem(
                        escopo="DERAL_NUCLEO",
                        fonte=f"DERAL/SEAB-PR (Núcleo {nucleo.praca})",
                        praca=f"{nucleo.praca}/PR",
                        valor=round(float(nucleo.valor), 2),
                        data_referencia=deral.dataReferencia,
                    )
                )
        fontes.append(
            FonteComparadaRegionalItem(
                escopo="DERAL_MEDIA",
                fonte="DERAL/SEAB-PR (Média Estadual)",
                praca=deral.pracaReferencia,
                valor=round(float(deral.valor), 2),
                data_referencia=deral.dataReferencia,
            )
        )
    if not fontes:
        return [], None, None, None, None
    valores = [f.valor for f in fontes]
    v_min = round(min(valores), 2)
    v_max = round(max(valores), 2)
    v_med = round(sum(valores) / len(valores), 2)
    disp = round(((v_max - v_min) / v_med) * 100.0, 2) if v_med > 0 and len(valores) > 1 else 0.0
    for f in fontes:
        f.diferenca_para_media_pct = round(((f.valor - v_med) / v_med) * 100.0, 2) if v_med > 0 else 0.0
    return fontes, v_min, v_med, v_max, disp


def _consolidar_item(
    codigo: str,
    meta: dict[str, object],
    fontes: tuple[dict[str, Any] | None, dict[str, Any] | None, PrecoPublicoItem | None],
) -> CotacaoRegionalItemResponse:
    """Combina escopos FAZENDA > TENANT > DERAL com múltiplas fontes, spread e núcleos regionais."""
    faz, ten, deral = fontes
    public_id = str(meta["id"])
    unidade = str(deral.unidade if deral else meta["defaultUnidade"])
    origem: Literal["FAZENDA", "TENANT", "DERAL", "INDISPONIVEL"] = "INDISPONIVEL"
    modo_eff: Literal["FONTE_SELECIONADA", "MEDIA_FONTES"] = "FONTE_SELECIONADA"
    val_eff, data_eff, praca_eff, fonte_eff = None, None, None, None
    if faz and faz.get("valor"):
        origem = "FAZENDA"
        val_eff, data_eff = float(faz["valor"]), str(faz.get("data_referencia") or "")
        praca_eff, fonte_eff = str(faz.get("praca") or ""), str(faz.get("fonte") or "Regional")
        if faz.get("modo_consolidacao") == "MEDIA_FONTES":
            modo_eff = "MEDIA_FONTES"
    elif ten and ten.get("valor"):
        origem = "TENANT"
        val_eff, data_eff = float(ten["valor"]), str(ten.get("data_referencia") or "")
        praca_eff, fonte_eff = str(ten.get("praca") or ""), str(ten.get("fonte") or "Regional")
        if ten.get("modo_consolidacao") == "MEDIA_FONTES":
            modo_eff = "MEDIA_FONTES"
    elif deral:
        origem = "DERAL"
        val_eff, data_eff = float(deral.valor), deral.dataReferencia
        praca_eff, fonte_eff = deral.pracaReferencia, deral.siglaFonte
    val_deral = float(deral.valor) if deral else None
    diff_brl, diff_pct = _calcular_spread_deral(val_eff, val_deral)
    pracas_deral = [
        PracaDeralResumoItem(praca=p.praca, valor=p.valor, registro_original=p.registroOriginal)
        for p in (deral.pracasRegionais if deral else [])
    ]
    fontes_comp, v_min_f, v_med_f, v_max_f, disp_f = _montar_painel_fontes_comparadas(faz, ten, deral)
    return CotacaoRegionalItemResponse(
        codigo=codigo, commodity_id_publico=public_id, nome=str(meta["nome"]),
        unidade=unidade, origem_efetiva=origem, modo_consolidacao=modo_eff,
        valor_efetivo=val_eff, data_referencia_efetiva=data_eff,
        praca_efetiva=praca_eff, fonte_efetiva=fonte_eff,
        valor_fazenda=float(faz["valor"]) if faz and faz.get("valor") else None,
        data_fazenda=str(faz.get("data_referencia")) if faz and faz.get("data_referencia") else None,
        praca_fazenda=str(faz.get("praca")) if faz and faz.get("praca") else None,
        fonte_fazenda=str(faz.get("fonte")) if faz and faz.get("fonte") else None,
        valor_tenant=float(ten["valor"]) if ten and ten.get("valor") else None,
        data_tenant=str(ten.get("data_referencia")) if ten and ten.get("data_referencia") else None,
        praca_tenant=str(ten.get("praca")) if ten and ten.get("praca") else None,
        fonte_tenant=str(ten.get("fonte")) if ten and ten.get("fonte") else None,
        valor_deral=val_deral,
        data_deral=deral.dataReferencia if deral else None,
        praca_deral=deral.pracaReferencia if deral else None,
        variacao_semanal_deral_pct=deral.variacaoSemanalPct if deral else None,
        diferenca_deral_brl=diff_brl,
        diferenca_deral_pct=diff_pct,
        valor_minimo_regional_deral=deral.valorMinimoRegional if deral else None,
        praca_minimo_regional_deral=deral.pracaMinimoRegional if deral else None,
        valor_maximo_regional_deral=deral.valorMaximoRegional if deral else None,
        praca_maximo_regional_deral=deral.pracaMaximoRegional if deral else None,
        total_fontes_ativas=len(fontes_comp),
        valor_minimo_fontes=v_min_f,
        valor_medio_fontes=v_med_f,
        valor_maximo_fontes=v_max_f,
        dispersao_fontes_pct=disp_f,
        fontes_comparadas=fontes_comp,
        pracas_deral_disponiveis=pracas_deral,
        historico_recente=_extrair_historico_combinado(faz, ten),
    )


class CotacaoRegionalService:
    """Gerencia cotações regionais com isolamento estrito por tenant e fazenda."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def _validar_unidade_produtiva(self, unidade_produtiva_id: uuid.UUID) -> None:
        stmt = select(UnidadeProdutiva.id).where(
            UnidadeProdutiva.id == unidade_produtiva_id,
            UnidadeProdutiva.tenant_id == self.tenant_id,
        )
        if (await self.session.execute(stmt)).scalar_one_or_none() is None:
            raise EntityNotFoundError("Fazenda/unidade produtiva não encontrada neste tenant.")

    async def _buscar_config_tenant(self) -> ConfiguracaoTenant | None:
        stmt = select(ConfiguracaoTenant).where(
            ConfiguracaoTenant.tenant_id == self.tenant_id,
            ConfiguracaoTenant.categoria == CATEGORIA_CONFIG_MERCADO,
            ConfiguracaoTenant.chave == CHAVE_COTACOES_REGIONAIS,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _buscar_config_fazenda(self, unidade_produtiva_id: uuid.UUID) -> ConfiguracaoFazenda | None:
        stmt = select(ConfiguracaoFazenda).where(
            ConfiguracaoFazenda.unidade_produtiva_id == unidade_produtiva_id,
            ConfiguracaoFazenda.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _carregar_mapa_tenant(self) -> dict[str, dict[str, Any]]:
        cfg = await self._buscar_config_tenant()
        if cfg and cfg.ativo and isinstance(cfg.valor, dict):
            return dict(cfg.valor)
        return {}

    async def _carregar_mapa_fazenda(self, unidade_produtiva_id: uuid.UUID | None) -> dict[str, dict[str, Any]]:
        if unidade_produtiva_id is None:
            return {}
        cfg = await self._buscar_config_fazenda(unidade_produtiva_id)
        if cfg and isinstance(cfg.overrides, dict):
            sub = cfg.overrides.get(CHAVE_COTACOES_REGIONAIS)
            if isinstance(sub, dict):
                return dict(sub)
        return {}

    async def salvar_cotacao_regional(
        self,
        codigo: str,
        payload: CotacaoRegionalUpsertRequest,
    ) -> CotacaoRegionalItemResponse:
        """Persiste ou atualiza uma cotação regional no escopo TENANT ou FAZENDA."""
        codigo_norm = normalizar_codigo_commodity(codigo)
        if payload.escopo == "FAZENDA":
            await self._salvar_escopo_fazenda(codigo_norm, payload.unidade_produtiva_id, payload)
        else:
            await self._salvar_escopo_tenant(codigo_norm, payload)
        await self.session.flush()
        return await self.obter_referencia_consolidada(codigo_norm, payload.unidade_produtiva_id)

    async def _salvar_escopo_fazenda(
        self, codigo_norm: str, unidade_id: uuid.UUID | None, payload: CotacaoRegionalUpsertRequest
    ) -> None:
        if unidade_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unidade_produtiva_id obrigatório.")
        await self._validar_unidade_produtiva(unidade_id)
        cfg = await self._buscar_config_fazenda(unidade_id)
        if cfg is None:
            cfg = ConfiguracaoFazenda(
                unidade_produtiva_id=unidade_id, tenant_id=self.tenant_id, overrides={}
            )
            self.session.add(cfg)
        overrides = dict(cfg.overrides or {})
        reg = dict(overrides.get(CHAVE_COTACOES_REGIONAIS) or {})
        anterior = reg.get(codigo_norm) if isinstance(reg.get(codigo_norm), dict) else None
        reg[codigo_norm] = _montar_entrada_regional(payload, anterior)
        overrides[CHAVE_COTACOES_REGIONAIS] = reg
        cfg.overrides = overrides
        flag_modified(cfg, "overrides")

    async def _salvar_escopo_tenant(
        self, codigo_norm: str, payload: CotacaoRegionalUpsertRequest
    ) -> None:
        cfg = await self._buscar_config_tenant()
        if cfg is None:
            cfg = ConfiguracaoTenant(
                tenant_id=self.tenant_id,
                categoria=CATEGORIA_CONFIG_MERCADO,
                chave=CHAVE_COTACOES_REGIONAIS,
                valor={},
                descricao="Cotações regionais de mercado configuradas pelo grupo/tenant",
                ativo=True,
            )
            self.session.add(cfg)
        mapa = dict(cfg.valor or {})
        anterior = mapa.get(codigo_norm) if isinstance(mapa.get(codigo_norm), dict) else None
        mapa[codigo_norm] = _montar_entrada_regional(payload, anterior)
        cfg.valor = mapa
        cfg.ativo = True
        flag_modified(cfg, "valor")

    async def remover_cotacao_regional(
        self,
        codigo: str,
        escopo: Literal["TENANT", "FAZENDA"],
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> None:
        """Remove uma cotação regional mantendo demais overrides intactos."""
        codigo_norm = normalizar_codigo_commodity(codigo)
        if escopo == "FAZENDA":
            if unidade_produtiva_id is None:
                raise HTTPException(status_code=400, detail="unidade_produtiva_id obrigatório para escopo FAZENDA.")
            await self._validar_unidade_produtiva(unidade_produtiva_id)
            cfg = await self._buscar_config_fazenda(unidade_produtiva_id)
            if cfg and isinstance(cfg.overrides, dict):
                overrides = dict(cfg.overrides)
                reg = dict(overrides.get(CHAVE_COTACOES_REGIONAIS) or {})
                reg.pop(codigo_norm, None)
                if reg:
                    overrides[CHAVE_COTACOES_REGIONAIS] = reg
                else:
                    overrides.pop(CHAVE_COTACOES_REGIONAIS, None)
                cfg.overrides = overrides
                flag_modified(cfg, "overrides")
        else:
            cfg_t = await self._buscar_config_tenant()
            if cfg_t and isinstance(cfg_t.valor, dict):
                mapa = dict(cfg_t.valor)
                mapa.pop(codigo_norm, None)
                cfg_t.valor = mapa
                flag_modified(cfg_t, "valor")
        await self.session.flush()

    async def listar_referencias_consolidadas(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> list[CotacaoRegionalItemResponse]:
        """Lista as 22 commodities com o valor efetivo resolvido por hierarquia."""
        if unidade_produtiva_id is not None:
            await self._validar_unidade_produtiva(unidade_produtiva_id)
        await _sincronizar_deral_do_banco(self.session)
        mapa_ten = await self._carregar_mapa_tenant()
        mapa_faz = await self._carregar_mapa_fazenda(unidade_produtiva_id)
        mapa_deral = _carregar_mapa_deral()
        return [
            _consolidar_item(
                codigo,
                meta,
                (mapa_faz.get(codigo), mapa_ten.get(codigo), mapa_deral.get(str(meta["id"]))),
            )
            for codigo, meta in _CATALOGO_POR_CODIGO.items()
        ]

    async def obter_referencia_consolidada(
        self,
        codigo: str,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> CotacaoRegionalItemResponse:
        """Retorna item consolidado único de uma commodity."""
        codigo_norm = normalizar_codigo_commodity(codigo)
        itens = await self.listar_referencias_consolidadas(unidade_produtiva_id)
        return next(item for item in itens if item.codigo == codigo_norm)

    async def resolver_cotacao_efetiva(
        self,
        codigo: str,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> tuple[float | None, str | None]:
        """Resolve (valor, rotulo_fonte) seguindo Fazenda > Tenant > DERAL."""
        codigo_norm = normalizar_codigo_commodity(codigo)
        mapa_faz = await self._carregar_mapa_fazenda(unidade_produtiva_id)
        entry_faz = mapa_faz.get(codigo_norm)
        if entry_faz and entry_faz.get("valor"):
            praca = str(entry_faz.get("praca") or "").strip()
            return round(float(entry_faz["valor"]), 2), f"Regional ({praca})" if praca else "Regional"
        mapa_ten = await self._carregar_mapa_tenant()
        entry_ten = mapa_ten.get(codigo_norm)
        if entry_ten and entry_ten.get("valor"):
            praca = str(entry_ten.get("praca") or "").strip()
            return round(float(entry_ten["valor"]), 2), f"Regional ({praca})" if praca else "Regional"
        await _sincronizar_deral_do_banco(self.session)
        deral_item = _carregar_mapa_deral().get(str(_CATALOGO_POR_CODIGO[codigo_norm]["id"]))
        if deral_item is not None and deral_item.valor > 0:
            return round(float(deral_item.valor), 2), deral_item.siglaFonte
        return None, None
