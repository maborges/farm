"""
Services — Hedge MVP (EXECUTION-HEDGE-01)

HedgeService: CRUD de ContratoFuturo e HedgeRegistro com regras de negócio.
HedgeExposureService: Cálculo de exposição líquida — query pura, sem persistência.
"""
from __future__ import annotations

import uuid
from datetime import date
import unicodedata
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo
from core.cadastros.commodities.models import Commodity
from core.exceptions import EntityNotFoundError, BusinessRuleError
from core.services.cultura_resolution_service import CulturaResolutionService
from core.services.audit_service import write_audit_log

from .models import ContratoFuturo, HedgeRegistro
from .schemas import (
    ContratoFuturoCreate,
    HedgeRegistroCreate,
    HedgePosicaoResponse,
    HedgeExposicaoResponse,
)


class HedgeService:
    """Operações de CRUD sobre ContratoFuturo e HedgeRegistro.

    Todas as operações são tenant-scoped e validam regras de negócio.

    Args:
        session: Sessão AsyncSession injetada via dependency.
        tenant_id: UUID do tenant autenticado — obrigatório para isolamento.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._cultura_resolver = CulturaResolutionService(session, tenant_id)

    # ------------------------------------------------------------------
    # ContratoFuturo
    # ------------------------------------------------------------------

    async def criar_contrato(
        self,
        data: ContratoFuturoCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> ContratoFuturo:
        """Cria um novo contrato futuro vinculado ao tenant.

        Args:
            data: Dados do contrato a criar.
            user_id: ID do usuário para auditoria (opcional).

        Returns:
            ContratoFuturo recém-criado.

        Raises:
            BusinessRuleError: Se os dados violam regras de negócio.
        """
        commodity_id = await self._validar_e_resolver_commodity(data)
        contrato = ContratoFuturo(
            tenant_id=self._tenant_id,
            safra_id=data.safra_id,
            commodity_id=data.commodity_id or commodity_id,
            commodity=data.commodity,
            mercado=data.mercado,
            codigo_contrato=data.codigo_contrato,
            mes_vencimento=data.mes_vencimento,
            tipo_posicao=data.tipo_posicao,
            quantidade=data.quantidade,
            unidade=data.unidade,
            preco_contratado=data.preco_contratado,
            status="ABERTO",
        )
        self._session.add(contrato)
        await self._session.flush()

        await write_audit_log(
            self._session,
            tenant_id=self._tenant_id,
            user_id=user_id,
            action="HEDGE_CONTRATO_CRIADO",
            resource="contratos_futuros_v2",
            resource_id=contrato.id,
            payload_before=None,
            payload_after={
                "commodity": contrato.commodity,
                "quantidade": float(contrato.quantidade),
                "tipo_posicao": contrato.tipo_posicao,
            },
        )
        return contrato

    def _normalizar_texto(self, value: str) -> str:
        """Normaliza textos para comparação de commodity/cultura.

        Args:
            value: Texto de entrada.

        Returns:
            Texto normalizado em caixa alta e sem acentos.
        """
        texto = unicodedata.normalize("NFD", value or "")
        texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
        return "".join(ch for ch in texto if ch.isalnum()).upper()

    async def _resolver_commodity_da_safra(
        self, safra_id: uuid.UUID
    ) -> tuple[str | None, uuid.UUID | None]:
        """Resolve a commodity canônica associada à safra.

        Args:
            safra_id: Identificador da safra do tenant.

        Returns:
            Tuple com nome e id da commodity resolvida, ou (None, None).
        """
        cultivo_result = await self._session.execute(
            select(Cultivo.commodity_id, Commodity.nome).join(
                Commodity, Commodity.id == Cultivo.commodity_id, isouter=True
            ).where(
                Cultivo.safra_id == safra_id,
                Cultivo.tenant_id == self._tenant_id,
                Cultivo.commodity_id.is_not(None),
            )
        )
        commodities_cultivo = cultivo_result.all()
        commodity_ids = {
            commodity_id for commodity_id, _ in commodities_cultivo if commodity_id is not None
        }
        if len(commodity_ids) == 1:
            commodity_id = next(iter(commodity_ids))
            commodity_nome = next(
                (
                    nome
                    for atual_id, nome in commodities_cultivo
                    if atual_id == commodity_id and nome
                ),
                None,
            )
            if commodity_nome:
                return str(commodity_nome), commodity_id
            commodity_obj = await self._session.get(Commodity, commodity_id)
            if commodity_obj is not None:
                return commodity_obj.nome, commodity_obj.id
            return None, None
        if len(commodity_ids) > 1:
            return None, None

        cultura = await self._resolver_cultura_da_safra(safra_id)
        if not cultura:
            return None, None

        commodity_result = await self._session.execute(
            select(Commodity.id, Commodity.nome).where(
                or_(Commodity.tenant_id.is_(None), Commodity.tenant_id == self._tenant_id),
                Commodity.ativo.is_(True),
                or_(
                    func.upper(Commodity.nome) == cultura.strip().upper(),
                    func.upper(Commodity.codigo) == cultura.strip().upper(),
                ),
            )
        )
        commodity = commodity_result.first()
        if commodity is None:
            return None, None
        return str(commodity[1]), commodity[0]

    async def _resolver_cultura_da_safra(self, safra_id: uuid.UUID) -> str | None:
        """Resolve o nome de cultura da safra via camada canônica.

        Args:
            safra_id: Identificador da safra.

        Returns:
            Nome da cultura resolvida, ou None quando não houver resolução.
        """
        result = await self._cultura_resolver.resolve_by_safra(safra_id)
        return result.nome if result.resolved else None

    async def _validar_e_resolver_commodity(
        self, data: ContratoFuturoCreate
    ) -> uuid.UUID | None:
        """Valida a commodity informada contra a safra selecionada.

        Args:
            data: Payload de criação do contrato.

        Returns:
            commodity_id resolvido da safra, quando existir.

        Raises:
            BusinessRuleError: Quando a commodity informada diverge da safra.
        """
        if data.safra_id is None:
            return None

        commodity_safra, commodity_id = await self._resolver_commodity_da_safra(data.safra_id)
        if not commodity_safra:
            return None

        if self._normalizar_texto(data.commodity) != self._normalizar_texto(commodity_safra):
            raise BusinessRuleError(
                "Commodity incompatível com a Safra selecionada."
            )

        if (
            data.commodity_id is not None
            and commodity_id is not None
            and data.commodity_id != commodity_id
        ):
            raise BusinessRuleError(
                "Commodity incompatível com a Safra selecionada."
            )

        return commodity_id

    async def listar_contratos(
        self,
        safra_id: Optional[uuid.UUID] = None,
        commodity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ContratoFuturo]:
        """Lista contratos futuros do tenant com filtros opcionais.

        Args:
            safra_id: Filtro por safra.
            commodity: Filtro por nome de commodity.
            status: Filtro por status (ABERTO, ENCERRADO, LIQUIDADO).

        Returns:
            Lista de ContratoFuturo.
        """
        stmt = select(ContratoFuturo).where(
            ContratoFuturo.tenant_id == self._tenant_id
        )
        if safra_id:
            stmt = stmt.where(ContratoFuturo.safra_id == safra_id)
        if commodity:
            stmt = stmt.where(ContratoFuturo.commodity == commodity.upper())
        if status:
            stmt = stmt.where(ContratoFuturo.status == status.upper())
        stmt = stmt.order_by(ContratoFuturo.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def obter_contrato(self, contrato_id: uuid.UUID) -> ContratoFuturo:
        """Busca um contrato futuro por ID, garantindo isolamento de tenant.

        Args:
            contrato_id: UUID do contrato.

        Returns:
            ContratoFuturo encontrado.

        Raises:
            EntityNotFoundError: Se o contrato não existe ou não pertence ao tenant.
        """
        result = await self._session.execute(
            select(ContratoFuturo).where(
                ContratoFuturo.id == contrato_id,
                ContratoFuturo.tenant_id == self._tenant_id,
            )
        )
        contrato = result.scalar_one_or_none()
        if contrato is None:
            raise EntityNotFoundError(f"ContratoFuturo {contrato_id} não encontrado")
        return contrato

    # ------------------------------------------------------------------
    # HedgeRegistro
    # ------------------------------------------------------------------

    async def criar_registro(
        self,
        data: HedgeRegistroCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> HedgeRegistro:
        """Registra uma operação de hedge dentro de um contrato futuro.

        Args:
            data: Dados da operação.
            user_id: ID do usuário para auditoria.

        Returns:
            HedgeRegistro recém-criado.

        Raises:
            EntityNotFoundError: Se o contrato não existe ou pertence a outro tenant.
            BusinessRuleError: Se o contrato está ENCERRADO ou LIQUIDADO.
        """
        contrato = await self.obter_contrato(data.contrato_futuro_id)

        if contrato.status in ("ENCERRADO", "LIQUIDADO"):
            raise BusinessRuleError(
                f"Não é possível registrar operação em contrato {contrato.status.lower()}."
            )

        registro = HedgeRegistro(
            tenant_id=self._tenant_id,
            contrato_futuro_id=contrato.id,
            safra_id=data.safra_id or contrato.safra_id,
            tipo=data.tipo,
            quantidade=data.quantidade,
            preco=data.preco,
            data_operacao=data.data_operacao,
            base=data.base,
            resultado_papel=data.resultado_papel,
            resultado_fisico=data.resultado_fisico,
            resultado_liquido=data.resultado_liquido,
            observacoes=data.observacoes,
        )
        self._session.add(registro)
        await self._session.flush()

        await write_audit_log(
            self._session,
            tenant_id=self._tenant_id,
            user_id=user_id,
            action="HEDGE_REGISTRO_CRIADO",
            resource="hedge_registros_v2",
            resource_id=registro.id,
            payload_before=None,
            payload_after={
                "contrato_futuro_id": str(contrato.id),
                "tipo": registro.tipo,
                "quantidade": float(registro.quantidade),
                "preco": float(registro.preco),
            },
        )
        return registro

    async def listar_registros(
        self,
        contrato_futuro_id: Optional[uuid.UUID] = None,
        safra_id: Optional[uuid.UUID] = None,
    ) -> list[HedgeRegistro]:
        """Lista operações de hedge do tenant com filtros opcionais.

        Args:
            contrato_futuro_id: Filtro por contrato.
            safra_id: Filtro por safra.

        Returns:
            Lista de HedgeRegistro.
        """
        stmt = select(HedgeRegistro).where(
            HedgeRegistro.tenant_id == self._tenant_id
        )
        if contrato_futuro_id:
            stmt = stmt.where(
                HedgeRegistro.contrato_futuro_id == contrato_futuro_id
            )
        if safra_id:
            stmt = stmt.where(HedgeRegistro.safra_id == safra_id)
        stmt = stmt.order_by(HedgeRegistro.data_operacao.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def calcular_posicao(
        self,
        safra_id: Optional[uuid.UUID] = None,
        commodity: Optional[str] = None,
    ) -> HedgePosicaoResponse:
        """Calcula a posição consolidada de hedge — projeção sem tabela.

        Agrega os contratos abertos e calcula preço médio ponderado.

        Args:
            safra_id: Filtro por safra.
            commodity: Filtro por commodity.

        Returns:
            HedgePosicaoResponse com dados calculados.
        """
        stmt = select(ContratoFuturo).where(
            ContratoFuturo.tenant_id == self._tenant_id,
            ContratoFuturo.status == "ABERTO",
        )
        if safra_id:
            stmt = stmt.where(ContratoFuturo.safra_id == safra_id)
        if commodity:
            stmt = stmt.where(ContratoFuturo.commodity == commodity.upper())

        result = await self._session.execute(stmt)
        contratos = list(result.scalars().all())

        total_quantidade = sum(float(c.quantidade) for c in contratos)
        preco_medio: Optional[float] = None
        if total_quantidade > 0:
            soma_ponderada = sum(
                float(c.quantidade) * float(c.preco_contratado or 0)
                for c in contratos
                if c.preco_contratado
            )
            contratos_com_preco = [c for c in contratos if c.preco_contratado]
            if contratos_com_preco:
                qt_com_preco = sum(float(c.quantidade) for c in contratos_com_preco)
                preco_medio = soma_ponderada / qt_com_preco if qt_com_preco > 0 else None

        return HedgePosicaoResponse(
            tenant_id=self._tenant_id,
            safra_id=safra_id,
            commodity=commodity,
            total_contratos_abertos=len(contratos),
            quantidade_total_hedgeada=total_quantidade,
            preco_medio_ponderado=preco_medio,
            unidade="sc",
        )


class HedgeExposureService:
    """Serviço de cálculo de exposição física e financeira de commodities.

    Fórmula Oficial:
        exposicao_bruta      = Σ (produtividade_meta_sc_ha × area_ha) + estoque_fisico
        compromissos_fisicos = Σ comercializacoes confirmadas/entregues/finalizadas
        exposicao_fisica_liq = exposicao_bruta - compromissos_fisicos
        protecao_financeira  = Σ contratos futuros ABERTOS
        exposicao_aberta     = exposicao_fisica_liq - protecao_financeira
        percentual_cobertura = (protecao_financeira / exposicao_fisica_liq) × 100
        hedge_ratio          = percentual_cobertura / 100
        classificacao_risco  = DESCOBERTO | EQUILIBRADO | SOBREPROTEGIDO

    Não persiste nada. Todos os dados vêm das fontes canônicas:
    - Cultivo + CultivoArea → produção estimada
    - SaldoEstoque + cadastros_commodities → estoque físico de commodities
    - ComercializacaoCommodity → compromissos físicos
    - ContratoFuturo → proteção financeira

    Args:
        session: Sessão AsyncSession.
        tenant_id: UUID do tenant autenticado.
    """

    _STATUS_VENDIDO = ("CONFIRMADO", "ENTREGUE", "FINALIZADO")

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Classificação de Risco (função pura — sem I/O)
    # ------------------------------------------------------------------

    @staticmethod
    def _classificar_risco_cobertura(percentual_cobertura: float) -> str:
        """Classifica o nível de risco de cobertura com base no percentual.

        Args:
            percentual_cobertura: Percentual de cobertura financeira sobre
                a exposição física líquida (0–100+%).

        Returns:
            DESCOBERTO se < 70%, EQUILIBRADO se 70–110%, SOBREPROTEGIDO se > 110%.
        """
        from financeiro.hedge.schemas import (
            CLASSIFICACAO_DESCOBERTO,
            CLASSIFICACAO_EQUILIBRADO,
            CLASSIFICACAO_SOBREPROTEGIDO,
            LIMITE_COBERTURA_MINIMO,
            LIMITE_COBERTURA_MAXIMO,
        )
        if percentual_cobertura < LIMITE_COBERTURA_MINIMO:
            return CLASSIFICACAO_DESCOBERTO
        if percentual_cobertura > LIMITE_COBERTURA_MAXIMO:
            return CLASSIFICACAO_SOBREPROTEGIDO
        return CLASSIFICACAO_EQUILIBRADO

    # ------------------------------------------------------------------
    # Cálculo Principal
    # ------------------------------------------------------------------

    async def calcular_exposicao(
        self,
        safra_id: Optional[uuid.UUID] = None,
        commodity: Optional[str] = None,
        unidade_produtiva_id: Optional[uuid.UUID] = None,
    ) -> HedgeExposicaoResponse:
        """Calcula a exposição física e financeira completa para o tenant.

        Args:
            safra_id: Filtro opcional por safra.
            commodity: Filtro opcional por nome de commodity (case-insensitive).
            unidade_produtiva_id: Filtro opcional por Unidade Produtiva (via talhão).

        Returns:
            HedgeExposicaoResponse com todos os componentes da fórmula.
        """
        producao = await self._calcular_producao_estimada(
            safra_id, commodity, unidade_produtiva_id
        )
        estoque_fisico = await self._calcular_estoque_fisico(commodity)
        ja_vendido = await self._calcular_ja_vendido(safra_id, commodity)
        ja_hedgeado = await self._calcular_ja_hedgeado(safra_id, commodity)

        exposicao_bruta = producao + estoque_fisico
        exposicao_liquida = exposicao_bruta - ja_vendido
        exposicao_aberta = exposicao_liquida - ja_hedgeado

        percentual = (
            (ja_hedgeado / exposicao_liquida * 100) if exposicao_liquida > 0 else 0.0
        )
        hedge_ratio = percentual / 100.0
        classificacao = self._classificar_risco_cobertura(percentual)

        return HedgeExposicaoResponse(
            tenant_id=self._tenant_id,
            safra_id=safra_id,
            commodity=commodity,
            producao_estimada_sc=producao,
            estoque_fisico_sc=estoque_fisico,
            exposicao_bruta_sc=exposicao_bruta,
            ja_vendido_sc=ja_vendido,
            ja_hedgeado_sc=ja_hedgeado,
            exposicao_liquida_sc=exposicao_liquida,
            exposicao_aberta_sc=exposicao_aberta,
            percentual_cobertura=round(percentual, 2),
            hedge_ratio=round(hedge_ratio, 4),
            classificacao_risco=classificacao,
        )

    async def simular_exposicao(
        self, request: "SimulacaoExposicaoRequest"
    ) -> "SimulacaoExposicaoResponse":
        """Calcula um cenário simulado de exposição sem persistência.
        
        Aplica os deltas (variações) solicitados sobre a base de dados real
        e retorna a comparação entre o cenário atual e o simulado.
        """
        from financeiro.hedge.schemas import SimulacaoExposicaoResponse, HedgeExposicaoResponse
        from core.exceptions import BusinessRuleError

        # 1. Calcula cenário atual
        atual = await self.calcular_exposicao(
            safra_id=request.safra_id,
            commodity=request.commodity,
            unidade_produtiva_id=request.unidade_produtiva_id,
        )

        # 2. Aplica deltas
        prod_sim = atual.producao_estimada_sc + request.variacao_producao_sc
        estq_sim = atual.estoque_fisico_sc + request.variacao_estoque_sc
        vend_sim = atual.ja_vendido_sc + request.variacao_venda_sc
        hedg_sim = atual.ja_hedgeado_sc + request.variacao_hedge_sc

        # 3. Validações de Domínio de Simulação
        if prod_sim < 0:
            raise BusinessRuleError("A produção simulada não pode ser negativa.")
        if estq_sim < 0:
            raise BusinessRuleError("O estoque físico simulado não pode ser negativo.")
        if vend_sim < 0:
            raise BusinessRuleError("As vendas simuladas não podem ser negativas.")
        if hedg_sim < 0:
            raise BusinessRuleError("O volume hedgeado simulado não pode ser negativo.")

        exposicao_bruta_sim = prod_sim + estq_sim
        
        if exposicao_bruta_sim == 0 and (vend_sim > 0 or hedg_sim > 0):
            raise BusinessRuleError("Não é possível simular vendas ou hedge sem base física (Exposição Bruta zero).")

        if vend_sim > exposicao_bruta_sim:
            raise BusinessRuleError("A venda simulada excede o lastro físico (Exposição Bruta).")

        exposicao_liquida_sim = exposicao_bruta_sim - vend_sim
        
        if hedg_sim > exposicao_liquida_sim:
            raise BusinessRuleError("O hedge simulado excede a exposição real disponível (Exposição Líquida).")

        exposicao_aberta_sim = exposicao_liquida_sim - hedg_sim

        percentual_sim = (
            (hedg_sim / exposicao_liquida_sim * 100) if exposicao_liquida_sim > 0 else 0.0
        )
        hedge_ratio_sim = percentual_sim / 100.0
        classificacao_sim = self._classificar_risco_cobertura(percentual_sim)

        simulado = HedgeExposicaoResponse(
            tenant_id=atual.tenant_id,
            safra_id=atual.safra_id,
            commodity=atual.commodity,
            producao_estimada_sc=prod_sim,
            estoque_fisico_sc=estq_sim,
            exposicao_bruta_sc=exposicao_bruta_sim,
            ja_vendido_sc=vend_sim,
            ja_hedgeado_sc=hedg_sim,
            exposicao_liquida_sc=exposicao_liquida_sim,
            exposicao_aberta_sc=exposicao_aberta_sim,
            percentual_cobertura=round(percentual_sim, 2),
            hedge_ratio=round(hedge_ratio_sim, 4),
            classificacao_risco=classificacao_sim,
        )

        alertas = []
        if classificacao_sim != atual.classificacao_risco:
            alertas.append(f"Atenção: A simulação altera a classificação de risco de {atual.classificacao_risco} para {classificacao_sim}.")

        return SimulacaoExposicaoResponse(
            cenario_atual=atual,
            cenario_simulado=simulado,
            alertas=alertas
        )

    async def calcular_consolidado(self) -> "ExposicaoConsolidadaResponse":
        """Calcula a visão consolidada multi-safra e multi-commodity.

        Agrega todas as safras ativas do tenant agrupando por safra e cultura.
        Retorna subtotais por grupo e totais globais.

        Returns:
            ExposicaoConsolidadaResponse com breakdown por safra/commodity.
        """
        from financeiro.hedge.schemas import (
            ExposicaoConsolidadaResponse,
            ExposicaoConsolidadaItemResponse,
        )
        from sqlalchemy import text as sa_text

        # Consulta de produção estimada agrupada por safra e cultura
        stmt = sa_text(
            """
            SELECT
                c.safra_id,
                s.ano_safra,
                UPPER(c.cultura) AS commodity,
                COALESCE(SUM(c.produtividade_meta_sc_ha * ca.area_ha), 0.0) AS producao
            FROM cultivos c
            JOIN cultivo_areas ca ON ca.cultivo_id = c.id
            JOIN safras s ON s.id = c.safra_id
            WHERE s.tenant_id = :tenant_id
              AND c.produtividade_meta_sc_ha IS NOT NULL
              AND ca.area_ha IS NOT NULL
            GROUP BY c.safra_id, s.ano_safra, UPPER(c.cultura)
            """
        )
        result = await self._session.execute(stmt, {"tenant_id": str(self._tenant_id)})
        rows = result.fetchall()

        itens: list[ExposicaoConsolidadaItemResponse] = []
        total_bruta = 0.0
        total_vendido = 0.0
        total_hedgeado = 0.0

        for row in rows:
            safra_id_row = row[0]
            ano_safra = row[1]
            commodity_row = row[2]
            producao = float(row[3])

            vendido = await self._calcular_ja_vendido(safra_id_row, commodity_row)
            hedgeado = await self._calcular_ja_hedgeado(safra_id_row, commodity_row)
            exposicao_bruta = producao
            exposicao_aberta = exposicao_bruta - vendido - hedgeado
            perc = (hedgeado / (exposicao_bruta - vendido) * 100) if (exposicao_bruta - vendido) > 0 else 0.0

            itens.append(ExposicaoConsolidadaItemResponse(
                safra_id=safra_id_row,
                ano_safra=ano_safra,
                commodity=commodity_row,
                exposicao_bruta_sc=round(exposicao_bruta, 2),
                ja_vendido_sc=round(vendido, 2),
                ja_hedgeado_sc=round(hedgeado, 2),
                exposicao_aberta_sc=round(exposicao_aberta, 2),
                percentual_cobertura=round(perc, 2),
                classificacao_risco=self._classificar_risco_cobertura(perc),
            ))
            total_bruta += exposicao_bruta
            total_vendido += vendido
            total_hedgeado += hedgeado

        total_liquida = total_bruta - total_vendido
        total_aberta = total_liquida - total_hedgeado
        perc_global = (total_hedgeado / total_liquida * 100) if total_liquida > 0 else 0.0

        return ExposicaoConsolidadaResponse(
            tenant_id=self._tenant_id,
            total_exposicao_bruta_sc=round(total_bruta, 2),
            total_compromissos_sc=round(total_vendido, 2),
            total_protecao_sc=round(total_hedgeado, 2),
            total_exposicao_aberta_sc=round(total_aberta, 2),
            percentual_cobertura_global=round(perc_global, 2),
            classificacao_risco_global=self._classificar_risco_cobertura(perc_global),
            por_safra_commodity=itens,
        )

    # ------------------------------------------------------------------
    # Métodos Privados de Cálculo
    # ------------------------------------------------------------------

    async def _calcular_producao_estimada(
        self,
        safra_id: Optional[uuid.UUID],
        commodity: Optional[str],
        unidade_produtiva_id: Optional[uuid.UUID] = None,
    ) -> float:
        """Calcula produção estimada somando produtividade_meta × área por cultivo.

        Usa Cultivo.produtividade_meta_sc_ha × CultivoArea.area_ha.
        Filtra pelo tenant via Safra.tenant_id.
        Suporta filtro opcional por Unidade Produtiva via talhão → UP.

        Args:
            safra_id: Filtro por safra.
            commodity: Filtro por nome de cultura/commodity.
            unidade_produtiva_id: Filtro por Unidade Produtiva (via estoque_depositos.unidade_produtiva_id).

        Returns:
            Produção estimada total em sacas.
        """
        from sqlalchemy import text as sa_text

        params: dict = {"tenant_id": str(self._tenant_id)}
        filters = "s.tenant_id = :tenant_id"

        if safra_id:
            filters += " AND c.safra_id = :safra_id"
            params["safra_id"] = str(safra_id)

        if commodity:
            filters += " AND UPPER(c.cultura) = :commodity"
            params["commodity"] = commodity.upper()

        if unidade_produtiva_id:
            # Vínculo: CultivoArea.area_id → cadastros_areas_rurais.id → unidade_produtiva_id
            filters += (
                " AND EXISTS ("
                " SELECT 1 FROM cadastros_areas_rurais ar"
                " WHERE ar.id = ca.area_id"
                " AND ar.unidade_produtiva_id = :unidade_produtiva_id"
                ")"
            )
            params["unidade_produtiva_id"] = str(unidade_produtiva_id)

        stmt = sa_text(
            f"""
            SELECT COALESCE(SUM(c.produtividade_meta_sc_ha * ca.area_ha), 0.0)
            FROM cultivos c
            JOIN cultivo_areas ca ON ca.cultivo_id = c.id
            JOIN safras s ON s.id = c.safra_id
            WHERE {filters}
              AND c.produtividade_meta_sc_ha IS NOT NULL
              AND ca.area_ha IS NOT NULL
            """
        )
        result = await self._session.execute(stmt, params)
        return float(result.scalar() or 0.0)

    async def _calcular_estoque_fisico(
        self,
        commodity: Optional[str],
    ) -> float:
        """Calcula o estoque físico atual disponível nos armazéns do tenant.

        Busca os lotes de produtos colhidos que não estão vendidos nem em trânsito.

        Args:
            commodity: Filtro por nome de commodity.

        Returns:
            Soma do estoque físico em sacas.
        """
        from sqlalchemy import text as sa_text

        params: dict = {"tenant_id": str(self._tenant_id)}

        commodity_filter = ""
        if commodity:
            commodity_filter = (
                " AND EXISTS ("
                " SELECT 1 FROM cadastros_commodities cc"
                " WHERE cc.id = pc.commodity_id"
                " AND UPPER(cc.nome) = :commodity"
                ")"
            )
            params["commodity"] = commodity.upper()

        stmt = sa_text(
            f"""
            SELECT COALESCE(SUM(pc.quantidade), 0.0)
            FROM agricola_produtos_colhidos pc
            WHERE pc.tenant_id = :tenant_id
              AND pc.status IN ('ARMAZENADO', 'RESERVADO')
              {commodity_filter}
            """
        )
        result = await self._session.execute(stmt, params)
        return float(result.scalar() or 0.0)

    async def _calcular_ja_vendido(
        self,
        safra_id: Optional[uuid.UUID],
        commodity: Optional[str],
    ) -> float:
        """Soma quantidade das comercializações confirmadas/entregues/finalizadas.

        Filtra pelo tenant e pelos status que representam venda efetiva.

        Args:
            safra_id: Filtro por safra (não aplicável diretamente; legado mantido).
            commodity: Filtro por nome de commodity.

        Returns:
            Total vendido em sacas (ou unidade da comercialização).
        """
        from sqlalchemy import text as sa_text

        status_list = ", ".join(f"'{s}'" for s in self._STATUS_VENDIDO)
        params: dict = {"tenant_id": str(self._tenant_id)}
        filters = f"fc.tenant_id = :tenant_id AND fc.status IN ({status_list})"

        if commodity:
            filters += (
                " AND EXISTS ("
                " SELECT 1 FROM cadastros_commodities cc"
                " WHERE cc.id = fc.commodity_id"
                " AND UPPER(cc.nome) = :commodity"
                ")"
            )
            params["commodity"] = commodity.upper()

        stmt = sa_text(
            f"""
            SELECT COALESCE(SUM(fc.quantidade), 0.0)
            FROM financeiro_comercializacoes fc
            WHERE {filters}
            """
        )
        result = await self._session.execute(stmt, params)
        return float(result.scalar() or 0.0)

    async def _calcular_ja_hedgeado(
        self,
        safra_id: Optional[uuid.UUID],
        commodity: Optional[str],
    ) -> float:
        """Soma quantidade dos contratos futuros ABERTOS do tenant.

        Args:
            safra_id: Filtro por safra.
            commodity: Filtro por nome de commodity.

        Returns:
            Total hedgeado em sacas.
        """
        stmt = select(func.coalesce(func.sum(ContratoFuturo.quantidade), 0.0)).where(
            ContratoFuturo.tenant_id == self._tenant_id,
            ContratoFuturo.status == "ABERTO",
        )
        if safra_id:
            stmt = stmt.where(ContratoFuturo.safra_id == safra_id)
        if commodity:
            stmt = stmt.where(ContratoFuturo.commodity == commodity.upper())

        result = await self._session.execute(stmt)
        return float(result.scalar() or 0.0)

    async def gerar_recomendacoes(
        self,
        exposicao: "HedgeExposicaoResponse",
    ) -> list["RecomendacaoComercial"]:
        """Analisa a exposição e gera recomendações heurísticas (stateless)."""
        from financeiro.hedge.schemas import RecomendacaoComercial, LIMITE_COBERTURA_MINIMO, LIMITE_COBERTURA_MAXIMO
        from datetime import date, timedelta
        
        recs: list[RecomendacaoComercial] = []
        
        perc = exposicao.percentual_cobertura
        aberta = exposicao.exposicao_aberta_sc

        # 1. Venda Sem Lastro (PRIORIDADE: CRITICA)
        if exposicao.ja_vendido_sc > exposicao.exposicao_bruta_sc and exposicao.ja_vendido_sc > 0:
            recs.append(RecomendacaoComercial(
                id_regra="VENDA_SEM_LASTRO",
                titulo="Venda sem lastro identificada",
                mensagem=f"O volume vendido ({exposicao.ja_vendido_sc:,.0f} sc) excede o lastro físico ({exposicao.exposicao_bruta_sc:,.0f} sc). Risco de default na entrega.",
                prioridade="CRITICA",
                acao_sugerida="Revisar contratos de venda e estoques."
            ))

        # 2. Safra Próxima da Colheita (Verificação no BD)
        colheita_proxima = False
        if exposicao.safra_id:
            from sqlalchemy import select, and_
            from agricola.cultivos.models import Cultivo
            hoje = date.today()
            limite_dias = hoje + timedelta(days=60)
            
            stmt = select(Cultivo.id).where(
                and_(
                    Cultivo.tenant_id == self._tenant_id,
                    Cultivo.safra_id == exposicao.safra_id,
                    Cultivo.data_colheita_prevista >= hoje,
                    Cultivo.data_colheita_prevista <= limite_dias
                )
            ).limit(1)
            result = await self._session.execute(stmt)
            if result.first() is not None:
                colheita_proxima = True

        # 3. Cobertura Baixa vs Safra Próxima
        if exposicao.exposicao_liquida_sc > 0:
            if perc < LIMITE_COBERTURA_MINIMO:
                if colheita_proxima:
                    recs.append(RecomendacaoComercial(
                        id_regra="SAFRA_PROXIMA_BAIXA_COBERTURA",
                        titulo="Safra próxima da colheita sem proteção adequada",
                        mensagem=f"A colheita inicia em <60 dias e a cobertura financeira está em apenas {perc:.1f}%. A margem está exposta à volatilidade de curtíssimo prazo.",
                        prioridade="ALTA",
                        acao_sugerida="Avaliar trava imediata via Opções de Venda (Put) ou Venda Física."
                    ))
                else:
                    recs.append(RecomendacaoComercial(
                        id_regra="COBERTURA_BAIXA",
                        titulo="Exposição descoberta relevante",
                        mensagem=f"A cobertura financeira de {perc:.1f}% está abaixo do limite de segurança ({LIMITE_COBERTURA_MINIMO}%). Avalie aumentar a proteção financeira.",
                        prioridade="ALTA",
                        acao_sugerida="Avaliar criação de novo Contrato Futuro."
                    ))
            elif perc <= 70.0:
                # 4. Cobertura Moderada
                recs.append(RecomendacaoComercial(
                    id_regra="COBERTURA_MODERADA",
                    titulo="Cobertura abaixo da zona recomendada",
                    mensagem=f"A proteção atual ({perc:.1f}%) cobre mais da metade da exposição, mas ainda expõe a margem a choques de mercado. A meta conservadora é >70%.",
                    prioridade="MEDIA",
                    acao_sugerida="Aguardar momento ótimo de mercado para incrementar."
                ))

        # 5. Sobreproteção
        if perc > LIMITE_COBERTURA_MAXIMO and exposicao.exposicao_liquida_sc > 0:
            recs.append(RecomendacaoComercial(
                id_regra="SOBREPROTECAO",
                titulo="Posição financeira acima da exposição física",
                mensagem=f"O volume hedgeado ({exposicao.ja_hedgeado_sc:,.0f} sc) excede a exposição ({exposicao.exposicao_liquida_sc:,.0f} sc). Você está especulando e sujeito a risco de base.",
                prioridade="ALTA",
                acao_sugerida="Avaliar recompra parcial de contratos (Short Covering)."
            ))

        # 6. Exposição Aberta Elevada
        LIMITE_ABERTO_RELEVANTE = 50_000 # hardcoded para primeira heuristica
        if aberta > LIMITE_ABERTO_RELEVANTE and perc >= LIMITE_COBERTURA_MINIMO and perc <= LIMITE_COBERTURA_MAXIMO:
            recs.append(RecomendacaoComercial(
                id_regra="EXPOSICAO_ABERTA_ELEVADA",
                titulo="Exposição aberta relevante para o porte da operação",
                mensagem=f"O volume descoberto absoluto é alto ({aberta:,.0f} sc), mesmo com o percentual de cobertura aceitável.",
                prioridade="ALTA",
                acao_sugerida="Analisar proteção via Opções Fora do Dinheiro (OTM) de baixo custo."
            ))

        return recs
