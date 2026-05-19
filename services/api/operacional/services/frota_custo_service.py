from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import EntityNotFoundError
from operacional.models.abastecimento import Abastecimento
from operacional.models.documento_equipamento import DocumentoEquipamento
from operacional.models.frota import ItemOrdemServico, OrdemServico, RegistroManutencao, JornadaEquipamento
from operacional.services.frota_custo_consolidado_service import (
    FrotaCustoConsolidadoService,
    FiltroCustoContexto,
)
from operacional.schemas.frota_custo import (
    FrotaCustoEquipamentoDetalhe,
    FrotaCustoEquipamentoItem,
    FrotaCustoEquipamentoResponse,
    FrotaCustoHistoricoItem,
    FrotaCustoRankingItem,
    FrotaCustoRankingResponse,
    FrotaCustoResponse,
    FrotaCustoResumo,
    FrotaCustoAgrupadoSafra,
    FrotaCustoAgrupadoTalhao,
    FrotaCustoAgrupadoOperacao,
    FrotaCustoAgrupadoUP,
)
from operacional.services.frota_dashboard_service import FrotaDashboardService
from agricola.safras.models import Safra
from core.cadastros.propriedades.models import AreaRural


class FrotaCustoService(FrotaDashboardService):
    RANKING_LIMIT = 10

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(session, tenant_id)
        self.consolidado_svc = FrotaCustoConsolidadoService(session, tenant_id)

    async def obter_custos(
        self,
        periodo_dias: int | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
        tipo_equipamento: str | None = None,
    ) -> FrotaCustoResponse:
        agora = datetime.now(timezone.utc)
        ctx = FiltroCustoContexto(
            tenant_id=self.tenant_id,
            periodo_dias=periodo_dias,
            unidade_produtiva_id=unidade_produtiva_id,
            tipo_equipamento=tipo_equipamento,
        )
        equipamentos = await self.consolidado_svc.obter_equipamentos_filtrados(ctx)
        if not equipamentos:
            return FrotaCustoResponse(
                resumo=FrotaCustoResumo(
                    custo_total_frota=0.0,
                    custo_combustivel=0.0,
                    custo_manutencao=0.0,
                    custo_pecas_itens=0.0,
                    custo_documental=0.0,
                    custo_medio_por_equipamento=0.0,
                ),
                equipamentos=[],
                ranking=[],
                gerado_em=agora,
            )

        equipamento_ids = [equipamento.id for equipamento in equipamentos]
        data_corte = agora - timedelta(days=periodo_dias) if periodo_dias else None

        custo_combustivel = await self.consolidado_svc.obter_custo_combustivel(equipamento_ids, data_corte)
        custo_manutencao_mao_obra = await self.consolidado_svc.obter_custo_mao_obra(equipamento_ids, data_corte)
        custo_pecas = await self.consolidado_svc.obter_custo_pecas(equipamento_ids, data_corte)
        custo_manutencao_avulsa = await self.consolidado_svc.obter_custo_manutencao_avulsa(equipamento_ids, data_corte)

        totais: dict[uuid.UUID, float] = {}
        for equipamento in equipamentos:
            eid = equipamento.id
            total_manut = round(custo_manutencao_mao_obra.get(eid, 0.0) + custo_manutencao_avulsa.get(eid, 0.0), 2)
            totais[eid] = round(
                custo_combustivel.get(eid, 0.0)
                + total_manut
                + custo_pecas.get(eid, 0.0),
                2,
            )

        custo_total_frota = round(sum(totais.values()), 2)
        
        itens = [
            self._serializar_item(
                equipamento=equipamento,
                custo_combustivel=round(custo_combustivel.get(equipamento.id, 0.0), 2),
                custo_manutencao=round(custo_manutencao_mao_obra.get(equipamento.id, 0.0) + custo_manutencao_avulsa.get(equipamento.id, 0.0), 2),
                custo_pecas=round(custo_pecas.get(equipamento.id, 0.0), 2),
                custo_documental=0.0,
                custo_total=totais[equipamento.id],
                custo_total_frota=custo_total_frota,
            )
            for equipamento in equipamentos
        ]
        
        ranking = self._serializar_ranking(itens)
        equipamento_mais_caro = ranking[0] if ranking else None

        safra_res = await self.consolidado_svc.obter_custos_por_safra(data_corte)
        por_safra = [
            FrotaCustoAgrupadoSafra(
                safra_id=row["safra_id"],
                safra_nome=row["safra_nome"],
                custo_total=row["custo_total"],
                participacao_percentual=row["participacao_percentual"],
            )
            for row in safra_res
        ]

        up_res = await self.consolidado_svc.consolidar_por_up(data_corte)
        por_unidade_produtiva = [
            FrotaCustoAgrupadoUP(
                unidade_produtiva_id=row["unidade_produtiva_id"],
                unidade_produtiva_nome=row["unidade_produtiva_nome"],
                custo_total=row["custo_total"],
                participacao_percentual=row["participacao_percentual"],
            )
            for row in up_res
        ]

        por_talhao = await self._obter_custo_por_talhao_sql(equipamento_ids, data_corte, custo_total_frota)
        por_operacao = await self._obter_custo_por_operacao_sql(equipamento_ids, data_corte, custo_total_frota)

        return FrotaCustoResponse(
            resumo=FrotaCustoResumo(
                custo_total_frota=custo_total_frota,
                custo_combustivel=round(sum(custo_combustivel.values()), 2),
                custo_manutencao=round(sum(custo_manutencao_mao_obra.values()) + sum(custo_manutencao_avulsa.values()), 2),
                custo_pecas_itens=round(sum(custo_pecas.values()), 2),
                custo_documental=0.0,
                custo_medio_por_equipamento=round(custo_total_frota / len(equipamentos), 2) if equipamentos else 0.0,
                equipamento_mais_caro_nome=equipamento_mais_caro.equipamento_nome if equipamento_mais_caro else None,
                equipamento_mais_caro_total=equipamento_mais_caro.custo_total if equipamento_mais_caro else None,
            ),
            equipamentos=sorted(itens, key=lambda item: (item.custo_total, item.equipamento_nome), reverse=True),
            ranking=ranking,
            por_safra=por_safra,
            por_talhao=por_talhao,
            por_operacao=por_operacao,
            por_unidade_produtiva=por_unidade_produtiva,
            gerado_em=agora,
        )

    async def obter_custo_equipamento(
        self,
        equipamento_id: uuid.UUID,
        periodo_dias: int | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaCustoEquipamentoResponse:
        resposta = await self.obter_custos(periodo_dias=periodo_dias, unidade_produtiva_id=unidade_produtiva_id)
        equipamento = next((item for item in resposta.equipamentos if item.equipamento_id == equipamento_id), None)
        if not equipamento:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")

        agora = datetime.now(timezone.utc)
        equipamentos = await self._listar_equipamentos_filtrados(unidade_produtiva_id, None)
        equipamento_model = next((item for item in equipamentos if item.id == equipamento_id), None)
        if not equipamento_model:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")

        data_corte = agora - timedelta(days=periodo_dias) if periodo_dias else None
        abastecimentos = self._filtrar_por_data(
            await self._listar_abastecimentos([equipamento_id]),
            data_corte,
            lambda item: item.data,
        )
        ordens = self._filtrar_por_data(
            await self._listar_ordens_servico([equipamento_id]),
            data_corte,
            lambda item: item.data_abertura,
        )
        registros = self._filtrar_por_data(
            await self._listar_registros_manutencao([equipamento_id]),
            data_corte,
            lambda item: item.data_realizacao,
        )
        itens_os = await self._listar_itens_os([ordem.id for ordem in ordens])
        itens_por_os: dict[uuid.UUID, list[ItemOrdemServico]] = defaultdict(list)
        for item in itens_os:
            itens_por_os[item.os_id].append(item)

        historico: list[FrotaCustoHistoricoItem] = []
        for item in abastecimentos:
            historico.append(FrotaCustoHistoricoItem(referencia=str(item.id), tipo="COMBUSTIVEL", valor=round(float(item.custo_total or 0.0), 2), data=item.data))
        for ordem in ordens:
            total_itens = sum(
                float(item.custo_total or (float(item.quantidade or 0.0) * float(item.preco_unitario_na_data or 0.0)))
                for item in itens_por_os[ordem.id]
            )
            pecas = round(total_itens if total_itens > 0 else float(ordem.custo_total_pecas or 0.0), 2)
            if pecas > 0:
                historico.append(FrotaCustoHistoricoItem(referencia=ordem.numero_os, tipo="PECAS", valor=pecas, data=ordem.data_abertura))
            mao_obra = round(float(ordem.custo_mao_obra or 0.0), 2)
            if mao_obra > 0:
                historico.append(FrotaCustoHistoricoItem(referencia=ordem.numero_os, tipo="MANUTENCAO", valor=mao_obra, data=ordem.data_abertura))
        for registro in registros:
            if registro.os_id is None and float(registro.custo_total or 0.0) > 0:
                historico.append(FrotaCustoHistoricoItem(referencia=str(registro.id), tipo="MANUTENCAO_AVULSA", valor=round(float(registro.custo_total or 0.0), 2), data=registro.data_realizacao))

        return FrotaCustoEquipamentoResponse(
            equipamento=FrotaCustoEquipamentoDetalhe(
                equipamento_id=equipamento.equipamento_id,
                equipamento_nome=equipamento.equipamento_nome,
                equipamento_tipo=equipamento.equipamento_tipo,
                equipamento_status=equipamento.equipamento_status,
                horimetro_atual=equipamento.horimetro_atual,
                km_atual=equipamento.km_atual,
                custo_combustivel=equipamento.custo_combustivel,
                custo_manutencao=equipamento.custo_manutencao,
                custo_pecas_itens=equipamento.custo_pecas_itens,
                custo_documental=equipamento.custo_documental,
                custo_total=equipamento.custo_total,
                custo_por_hora=equipamento.custo_por_hora,
                custo_por_km=equipamento.custo_por_km,
                participacao_percentual=equipamento.participacao_percentual,
            ),
            historico=sorted(historico, key=lambda item: item.data or agora, reverse=True),
            gerado_em=agora,
        )

    async def obter_ranking(
        self,
        periodo_dias: int | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
        tipo_equipamento: str | None = None,
    ) -> FrotaCustoRankingResponse:
        resposta = await self.obter_custos(
            periodo_dias=periodo_dias,
            unidade_produtiva_id=unidade_produtiva_id,
            tipo_equipamento=tipo_equipamento,
        )
        return FrotaCustoRankingResponse(ranking=resposta.ranking, gerado_em=resposta.gerado_em)

    async def _listar_equipamentos_filtrados(
        self,
        unidade_produtiva_id: uuid.UUID | None,
        tipo_equipamento: str | None,
    ) -> list[Equipamento]:
        stmt = select(Equipamento).where(Equipamento.tenant_id == self.tenant_id)
        if unidade_produtiva_id:
            stmt = stmt.where(Equipamento.unidade_produtiva_id == unidade_produtiva_id)
        if tipo_equipamento:
            stmt = stmt.where(Equipamento.tipo == tipo_equipamento)
        stmt = stmt.order_by(Equipamento.nome.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_itens_os(self, os_ids: list[uuid.UUID]) -> list[ItemOrdemServico]:
        if not os_ids:
            return []
        stmt = select(ItemOrdemServico).where(
            ItemOrdemServico.tenant_id == self.tenant_id,
            ItemOrdemServico.os_id.in_(os_ids),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _obter_custo_abastecimento_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None = None) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(Abastecimento.equipamento_id, func.sum(Abastecimento.custo_total))
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Abastecimento.equipamento_id.in_(equipamento_ids),
            )
        )
        if data_corte:
            stmt = stmt.where(Abastecimento.data >= data_corte)
        stmt = stmt.group_by(Abastecimento.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_custo_manutencao_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None = None) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(OrdemServico.equipamento_id, func.sum(OrdemServico.custo_mao_obra))
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
            )
        )
        if data_corte:
            stmt = stmt.where(OrdemServico.data_abertura >= data_corte)
        stmt = stmt.group_by(OrdemServico.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_custo_pecas_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None = None) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        # Prioritize ItemOrdemServico sum if items exist, otherwise use OrdemServico.custo_total_pecas
        # For performance, we'll use the OrdemServico field as it's already aggregated
        stmt = (
            select(OrdemServico.equipamento_id, func.sum(OrdemServico.custo_total_pecas))
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
            )
        )
        if data_corte:
            stmt = stmt.where(OrdemServico.data_abertura >= data_corte)
        stmt = stmt.group_by(OrdemServico.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_custo_manutencao_avulsa_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None = None) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(RegistroManutencao.equipamento_id, func.sum(RegistroManutencao.custo_total))
            .where(
                RegistroManutencao.tenant_id == self.tenant_id,
                RegistroManutencao.equipamento_id.in_(equipamento_ids),
                RegistroManutencao.os_id == None
            )
        )
        if data_corte:
            stmt = stmt.where(RegistroManutencao.data_realizacao >= data_corte)
        stmt = stmt.group_by(RegistroManutencao.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_custo_por_safra_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None, total_geral: float) -> list[FrotaCustoAgrupadoSafra]:
        # Agrega abastecimentos e manutenções por safra
        # Safra não possui coluna `nome` — o label é composto por ano_safra + cultura
        stmt = (
            select(Safra.id, Safra.ano_safra, Safra.cultura, func.sum(Abastecimento.custo_total))
            .join(Safra, Abastecimento.safra_id == Safra.id)
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Safra.tenant_id == self.tenant_id,
            )
            .group_by(Safra.id, Safra.ano_safra, Safra.cultura)
        )
        if data_corte:
            stmt = stmt.where(Abastecimento.data >= data_corte)
        result = await self.session.execute(stmt)
        return [
            FrotaCustoAgrupadoSafra(
                safra_id=row[0],
                safra_nome=" / ".join(part for part in [row[1], row[2]] if part),
                custo_total=float(row[3] or 0.0),
                participacao_percentual=round((float(row[3]) / total_geral) * 100, 2) if total_geral > 0 else 0.0
            )
            for row in result.all()
        ]

    async def _obter_custo_por_talhao_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None, total_geral: float) -> list[FrotaCustoAgrupadoTalhao]:
        stmt = (
            select(AreaRural.id, AreaRural.nome, func.sum(Abastecimento.custo_total))
            .join(AreaRural, Abastecimento.talhao_id == AreaRural.id)
            .where(Abastecimento.tenant_id == self.tenant_id)
            .group_by(AreaRural.id, AreaRural.nome)
        )
        result = await self.session.execute(stmt)
        return [
            FrotaCustoAgrupadoTalhao(
                talhao_id=row[0],
                talhao_nome=row[1],
                custo_total=float(row[2] or 0.0),
                participacao_percentual=round((float(row[2]) / total_geral) * 100, 2) if total_geral > 0 else 0.0
            )
            for row in result.all()
        ]

    async def _obter_custo_por_operacao_sql(self, equipamento_ids: list[uuid.UUID], data_corte: datetime | None, total_geral: float) -> list[FrotaCustoAgrupadoOperacao]:
        # Como abastecimento não tem 'operacao' direto, pegamos da jornada via join se houver
        # ou usamos um campo 'tipo_operacao' se adicionarmos.
        # Por enquanto, vamos agregar jornadas concluídas que têm custo estimado ou apenas contar horas.
        # MVP: Agregação por tipo_operacao da Jornada vinculada.
        stmt = (
            select(JornadaEquipamento.tipo_operacao, func.sum(Abastecimento.custo_total))
            .join(JornadaEquipamento, and_(
                Abastecimento.equipamento_id == JornadaEquipamento.equipamento_id,
                Abastecimento.data >= JornadaEquipamento.data_inicio,
                func.coalesce(Abastecimento.data <= JornadaEquipamento.data_fim, True)
            ))
            .where(Abastecimento.tenant_id == self.tenant_id)
            .group_by(JornadaEquipamento.tipo_operacao)
        )
        result = await self.session.execute(stmt)
        return [
            FrotaCustoAgrupadoOperacao(
                operacao=row[0],
                custo_total=float(row[1] or 0.0),
                participacao_percentual=round((float(row[1]) / total_geral) * 100, 2) if total_geral > 0 else 0.0
            )
            for row in result.all()
        ]

    @staticmethod
    def _filtrar_por_data(items, data_corte: datetime | None, attr_getter):
        if data_corte is None:
            return items
        return [item for item in items if attr_getter(item) >= data_corte]

    def _serializar_item(
        self,
        equipamento: Equipamento,
        custo_combustivel: float,
        custo_manutencao: float,
        custo_pecas: float,
        custo_documental: float,
        custo_total: float,
        custo_total_frota: float,
    ) -> FrotaCustoEquipamentoItem:
        return FrotaCustoEquipamentoItem(
            equipamento_id=equipamento.id,
            equipamento_nome=equipamento.nome,
            equipamento_tipo=equipamento.tipo,
            unidade_produtiva_id=equipamento.unidade_produtiva_id,
            equipamento_status=self._normalizar_status(equipamento.status),
            horimetro_atual=equipamento.horimetro_atual,
            km_atual=equipamento.km_atual,
            custo_combustivel=custo_combustivel,
            custo_manutencao=custo_manutencao,
            custo_pecas_itens=custo_pecas,
            custo_documental=custo_documental,
            custo_total=custo_total,
            custo_por_hora=self._calcular_custo_por_hora(custo_total, equipamento.horimetro_atual),
            custo_por_km=self._calcular_custo_por_km(custo_total, equipamento.km_atual),
            participacao_percentual=round((custo_total / custo_total_frota) * 100, 2) if custo_total_frota > 0 else None,
        )

    def _serializar_ranking(self, itens: list[FrotaCustoEquipamentoItem]) -> list[FrotaCustoRankingItem]:
        ranking = [
            FrotaCustoRankingItem(
                equipamento_id=item.equipamento_id,
                equipamento_nome=item.equipamento_nome,
                equipamento_tipo=item.equipamento_tipo,
                custo_total=item.custo_total,
                participacao_percentual=item.participacao_percentual,
                custo_por_hora=item.custo_por_hora,
                custo_por_km=item.custo_por_km,
            )
            for item in itens
        ]
        return sorted(ranking, key=lambda item: (item.custo_total, item.equipamento_nome), reverse=True)[: self.RANKING_LIMIT]
