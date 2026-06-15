"""
Services — Hedge MVP (EXECUTION-HEDGE-01)

HedgeService: CRUD de ContratoFuturo e HedgeRegistro com regras de negócio.
HedgeExposureService: Cálculo de exposição líquida — query pura, sem persistência.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError, BusinessRuleError
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
        contrato = ContratoFuturo(
            tenant_id=self._tenant_id,
            safra_id=data.safra_id,
            commodity_id=data.commodity_id,
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

