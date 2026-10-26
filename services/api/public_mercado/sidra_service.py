"""Orquestrador do serviço de estatísticas agropecuárias oficiais IBGE/SIDRA."""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Literal

import httpx
from loguru import logger
from pydantic import ValidationError

from .sidra import (
    ANO_MINIMO,
    AVISO_ESTATISTICA,
    AVISO_ESTIMATIVA,
    FONTE_LSPA,
    FONTE_PAM,
    PRODUTOS,
    UFS,
    CatalogoIbgeResponse,
    ConsultaSidra,
    EstatisticasIbgeResponse,
    Fonte,
    FonteSidra,
    IbgeSidraClient,
    IndicadorIbge,
    LocalidadeIbge,
    MunicipiosIbgeResponse,
    Nivel,
    ProdutoCatalogoIbge,
    ProdutoIbge,
    UfIbge,
    url_tabela,
)
from .sidra_cache import SidraCache, SidraCacheEntry

RE_MUNICIPIO = re.compile(r"^\d{7}$")


class IbgeSidraService:
    """Orquestrador de consultas públicas ao IBGE/SIDRA sem acesso a banco relacional."""

    def __init__(
        self,
        cache: SidraCache,
        client: IbgeSidraClient,
        ttl_annual_seconds: int = 86400,
        ttl_monthly_seconds: int = 14400,
    ) -> None:
        self.cache = cache
        self.client = client
        self.ttl_annual = max(300, ttl_annual_seconds)
        self.ttl_monthly = max(300, ttl_monthly_seconds)

    def get_catalogo(self) -> CatalogoIbgeResponse:
        """Retorna o catálogo de produtos agropecuários e UFs homologadas."""
        produtos_list = [
            ProdutoCatalogoIbge(
                id=p.id,
                nome=p.nome,
                tipo=p.tipo,
                pesquisa=p.fonte.pesquisa,
                indicadores=[v.nome for v in p.fonte.variaveis],
                suportaLspa=bool(p.lspa_categorias),
            )
            for p in PRODUTOS.values()
        ]
        ufs_list = [
            UfIbge(codigo=code, sigla=sigla, nome=nome)
            for code, (sigla, nome) in sorted(UFS.items(), key=lambda kv: kv[1][0])
        ]
        return CatalogoIbgeResponse(
            anoMinimo=ANO_MINIMO,
            produtos=sorted(produtos_list, key=lambda p: p.nome),
            ufs=ufs_list,
        )

    async def get_municipios(self, uf: str) -> MunicipiosIbgeResponse:
        """Consulta e armazena em cache a lista de municípios de uma UF homologada."""
        if uf not in UFS:
            raise ValueError(f"Código de UF '{uf}' não é homologado no IBGE.")

        shared = await self.cache.redis_ready()
        cached = await self.cache.get_municipios(uf, shared)
        if cached:
            return cached

        try:
            municipios = await self.client.fetch_municipios(uf)
            response = MunicipiosIbgeResponse(
                sucesso=True,
                uf=uf,
                dataConsultaIso=datetime.now(timezone.utc),
                cacheAtualizadoEmIso=datetime.now(timezone.utc),
                estadoDisponibilidade="NORMAL",
                estaDesatualizado=False,
                itens=municipios,
            )
            # Municípios têm estabilidade alta: TTL de 7 dias (604800s)
            await self.cache.save_municipios(uf, response, 604800, shared)
            return response
        except Exception as exc:
            logger.warning("Falha ao consultar municípios no IBGE", uf=uf, error=str(exc))
            return MunicipiosIbgeResponse(
                sucesso=False,
                uf=uf,
                dataConsultaIso=datetime.now(timezone.utc),
                cacheAtualizadoEmIso=None,
                estadoDisponibilidade="FONTE_INDISPONIVEL",
                estaDesatualizado=True,
                itens=[],
            )

    async def get_estatisticas(
        self,
        produto_id: str,
        nivel: Nivel = "BRASIL",
        uf: str | None = None,
        municipio: str | None = None,
        anos: int = 5,
        fonte_override: Fonte | None = None,
        now: datetime | None = None,
    ) -> EstatisticasIbgeResponse:
        """Executa consulta validada com cache em 2 níveis e fallback transparente."""
        now = now or datetime.now(timezone.utc)
        consulta = self._validar_parametros(produto_id, nivel, uf, municipio, anos, fonte_override)
        cache_key = self._gerar_cache_key(consulta)

        shared = await self.cache.redis_ready()
        fresh = await self.cache.get_fresh(cache_key, shared)
        if fresh:
            return self._formatar_resposta(fresh.payload, now, fresh.synced_at, fresh.payload.estadoDisponibilidade)

        last = await self.cache.get_last(cache_key, shared)

        if not shared and not self.cache.single_worker_fallback:
            return self._fallback_resposta(last, consulta, now)

        token = await self.cache.acquire(cache_key, shared)
        if token is None:
            return await self._wait_or_fallback(cache_key, shared, last, consulta, now)

        try:
            # Dupla checagem após adquirir lock
            fresh = await self.cache.get_fresh(cache_key, shared)
            if fresh:
                return self._formatar_resposta(fresh.payload, now, fresh.synced_at, fresh.payload.estadoDisponibilidade)

            try:
                local_nome, indicadores = await self.client.fetch_valores(consulta)
                modificacoes = await self.client.fetch_modificacoes(consulta.fonte.tabela)

                # Avalia data da fonte e staleness
                ultimo_periodo = indicadores[0].ultimoPeriodo if indicadores and indicadores[0].ultimoPeriodo else None
                data_atualizacao = modificacoes.get(ultimo_periodo) if ultimo_periodo else None

                estado_disp, esta_desatualizado, aviso_defasagem = self._avaliar_disponibilidade(
                    consulta, indicadores, ultimo_periodo, now
                )

                nome_localidade = local_nome or self._nome_localidade_padrao(consulta)
                aviso_legal = AVISO_ESTIMATIVA if consulta.fonte.fonte == "LSPA" else AVISO_ESTATISTICA

                resposta = EstatisticasIbgeResponse(
                    sucesso=True,
                    dataConsultaIso=now,
                    cacheAtualizadoEmIso=now,
                    estadoDisponibilidade=estado_disp,
                    estaDesatualizado=esta_desatualizado,
                    avisoLegal=aviso_legal,
                    pesquisa=consulta.fonte.pesquisa,
                    fontePesquisa=consulta.fonte.fonte,
                    tabelaSidra=consulta.fonte.tabela,
                    urlTabela=url_tabela(consulta.fonte.tabela),
                    periodicidade=consulta.fonte.periodicidade,
                    produto=ProdutoIbge(
                        id=consulta.produto.id,
                        nome=consulta.produto.nome,
                        tipo=consulta.produto.tipo,
                    ),
                    localidade=LocalidadeIbge(
                        nivel=consulta.nivel,
                        codigo="1" if consulta.nivel == "BRASIL" else consulta.codigo,
                        nome=nome_localidade,
                    ),
                    periodoSolicitado=consulta.periodo,
                    ultimoPeriodoDisponivel=ultimo_periodo,
                    dataAtualizacaoFonte=data_atualizacao,
                    avisoDefasagem=aviso_defasagem,
                    indicadores=indicadores,
                )

                ttl = self.ttl_monthly if consulta.fonte.periodicidade == "MENSAL" else self.ttl_annual
                entry = SidraCacheEntry(payload=resposta, synced_at=now)
                await self.cache.save(cache_key, entry, ttl, shared)
                return resposta

            except (httpx.HTTPError, ValueError, ValidationError, TimeoutError, OSError) as exc:
                logger.warning("Falha ao consultar IBGE/SIDRA", cache_key=cache_key, error=str(exc))
                return self._fallback_resposta(last, consulta, now)
        finally:
            await self.cache.release(cache_key, token, shared)

    def _validar_parametros(
        self,
        produto_id: str,
        nivel: Nivel,
        uf: str | None,
        municipio: str | None,
        anos: int,
        fonte_override: Fonte | None,
    ) -> ConsultaSidra:
        if produto_id not in PRODUTOS:
            raise ValueError(f"Produto '{produto_id}' não homologado na lista permitida.")

        produto = PRODUTOS[produto_id]
        anos_validos = max(1, min(anos, 10))

        # Determinação da fonte
        fonte: FonteSidra = produto.fonte
        categorias: tuple[int, ...] = (produto.categoria,)

        if fonte_override == "LSPA":
            if not produto.lspa_categorias:
                raise ValueError(f"Produto '{produto.nome}' não possui série no LSPA.")
            if nivel == "MUNICIPIO":
                raise ValueError("O LSPA não possui desagregação por município (apenas Brasil e UF).")
            fonte = FONTE_LSPA
            categorias = produto.lspa_categorias

        # Validação territorial
        if nivel == "BRASIL":
            codigo = "all"
        elif nivel == "UF":
            if not uf or uf not in UFS:
                raise ValueError(f"Código de UF '{uf}' inválido ou não homologado.")
            codigo = uf
        elif nivel == "MUNICIPIO":
            if not municipio or not RE_MUNICIPIO.match(municipio):
                raise ValueError(f"Código de município '{municipio}' deve possuir 7 dígitos.")
            uf_prefix = municipio[:2]
            if uf_prefix not in UFS:
                raise ValueError(f"Prefixo de UF '{uf_prefix}' do município não homologado.")
            codigo = municipio
        else:
            raise ValueError(f"Nível territorial '{nivel}' inválido.")

        # Período
        periodo = f"last {anos_validos * 12}" if fonte.periodicidade == "MENSAL" else f"last {anos_validos}"

        return ConsultaSidra(
            produto=produto,
            fonte=fonte,
            nivel=nivel,
            codigo=codigo,
            periodo=periodo,
            categorias=categorias,
        )

    @staticmethod
    def _gerar_cache_key(consulta: ConsultaSidra) -> str:
        return f"{consulta.produto.id}:{consulta.fonte.fonte}:{consulta.nivel}:{consulta.codigo}:{consulta.periodo}"

    @staticmethod
    def _nome_localidade_padrao(consulta: ConsultaSidra) -> str:
        if consulta.nivel == "BRASIL":
            return "Brasil"
        if consulta.nivel == "UF" and consulta.codigo in UFS:
            return UFS[consulta.codigo][1]
        return consulta.codigo

    @staticmethod
    def _avaliar_disponibilidade(
        consulta: ConsultaSidra,
        indicadores: list[IndicadorIbge],
        ultimo_periodo: str | None,
        now: datetime,
    ) -> tuple[Literal["NORMAL", "FONTE_INDISPONIVEL", "SEM_DADOS", "INDISPONIVEL"], bool, str | None]:
        # Verifica se todos os pontos têm valor nulo (cultura sem produção no local)
        todos_nulos = all(p.valor is None for ind in indicadores for p in ind.pontos)
        if todos_nulos or not ultimo_periodo:
            aviso = f"Não há registro de produção de {consulta.produto.nome} para a localidade solicitada no período."
            return "SEM_DADOS", False, aviso

        # Avaliação de defasagem legítima vs publicação normal
        ano_corrente = now.year
        if consulta.fonte.periodicidade == "ANUAL":
            try:
                ano_ultimo = int(ultimo_periodo)
                # Estatísticas anuais de safra e pecuária fecham no final do ano seguinte
                # Ex: dados de 2024/2025 são divulgados em set/out do ano subsequente.
                # Se o dado mais recente tiver mais de 2 anos de defasagem, marca como defasado.
                if (ano_corrente - ano_ultimo) > 2:
                    aviso = f"A publicação mais recente do IBGE para esta pesquisa é referente a {ano_ultimo}."
                    return "NORMAL", True, aviso
            except ValueError:
                pass
        elif consulta.fonte.periodicidade == "MENSAL":
            # LSPA mensal: se o último mês for mais de 3 meses anterior ao mês corrente
            pass

        return "NORMAL", False, None

    def _fallback_resposta(
        self,
        last: SidraCacheEntry | None,
        consulta: ConsultaSidra,
        now: datetime,
    ) -> EstatisticasIbgeResponse:
        if last:
            return self._formatar_resposta(last.payload, now, last.synced_at, "FONTE_INDISPONIVEL")

        return EstatisticasIbgeResponse(
            sucesso=False,
            dataConsultaIso=now,
            cacheAtualizadoEmIso=None,
            estadoDisponibilidade="INDISPONIVEL",
            estaDesatualizado=True,
            avisoLegal=AVISO_ESTATISTICA,
            pesquisa=consulta.fonte.pesquisa,
            fontePesquisa=consulta.fonte.fonte,
            tabelaSidra=consulta.fonte.tabela,
            urlTabela=url_tabela(consulta.fonte.tabela),
            periodicidade=consulta.fonte.periodicidade,
            produto=ProdutoIbge(
                id=consulta.produto.id,
                nome=consulta.produto.nome,
                tipo=consulta.produto.tipo,
            ),
            localidade=LocalidadeIbge(
                nivel=consulta.nivel,
                codigo="1" if consulta.nivel == "BRASIL" else consulta.codigo,
                nome=self._nome_localidade_padrao(consulta),
            ),
            periodoSolicitado=consulta.periodo,
            ultimoPeriodoDisponivel=None,
            dataAtualizacaoFonte=None,
            avisoDefasagem="Serviço do IBGE temporariamente indisponível.",
            indicadores=[],
        )

    @staticmethod
    def _formatar_resposta(
        payload: EstatisticasIbgeResponse,
        consulted: datetime,
        synced: datetime | None,
        availability: Literal["NORMAL", "FONTE_INDISPONIVEL", "SEM_DADOS", "INDISPONIVEL"],
    ) -> EstatisticasIbgeResponse:
        is_stale = availability != "NORMAL" or payload.estaDesatualizado
        return payload.model_copy(
            update={
                "dataConsultaIso": consulted,
                "cacheAtualizadoEmIso": synced,
                "estadoDisponibilidade": availability,
                "estaDesatualizado": is_stale,
            }
        )

    async def _wait_or_fallback(
        self,
        cache_key: str,
        shared: bool,
        last: SidraCacheEntry | None,
        consulta: ConsultaSidra,
        now: datetime,
    ) -> EstatisticasIbgeResponse:
        for _ in range(5):
            await asyncio.sleep(0.3)
            fresh = await self.cache.get_fresh(cache_key, shared)
            if fresh:
                return self._formatar_resposta(fresh.payload, now, fresh.synced_at, fresh.payload.estadoDisponibilidade)
            if last:
                break
        return self._fallback_resposta(last, consulta, now)
