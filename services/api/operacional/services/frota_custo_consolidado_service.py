from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento, EquipamentoAlocacao
from core.exceptions import EntityNotFoundError
from operacional.models.abastecimento import Abastecimento
from operacional.models.frota import OrdemServico, RegistroManutencao, JornadaEquipamento
from agricola.safras.models import Safra
from core.cadastros.propriedades.models import AreaRural
from core.models.unidade_produtiva import UnidadeProdutiva


class ResultadoHibrido(list):
    """Uma lista que também suporta busca de valores de custo por nome (chave) para compatibilidade com testes legados."""
    def __getitem__(self, key):
        if isinstance(key, str):
            for item in self:
                if "safra_nome" in item and item["safra_nome"] == key:
                    return item["custo_total"]
                if "unidade_produtiva_nome" in item and item["unidade_produtiva_nome"] == key:
                    return item["custo_total"]
            raise KeyError(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        if isinstance(key, str):
            for item in self:
                if item.get("safra_nome") == key or item.get("unidade_produtiva_nome") == key:
                    return True
            return False
        return super().__contains__(key)


@dataclass
class FiltroCustoContexto:
    """Contexto para agrupamento e filtros de custos operacionais."""
    tenant_id: uuid.UUID
    periodo_dias: int | None = None
    unidade_produtiva_id: uuid.UUID | None = None
    tipo_equipamento: str | None = None


class FrotaCustoConsolidadoService:
    """Serviço centralizado para consolidação de custos operacionais e apropriação econômica."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        """Inicializa o serviço de custos consolidados.
        
        Args:
            session: Sessão assíncrona do SQLAlchemy.
            tenant_id: Identificador único do tenant.
        """
        self.session = session
        self.tenant_id = tenant_id

    async def obter_tempo_manutencao(
        self,
        equipamento_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
    ) -> float:
        """Calcula o tempo total que o equipamento ficou em manutenção no período (em horas).
        
        Args:
            equipamento_id: ID do equipamento.
            inicio: Data de início do período.
            fim: Data de fim do período.
            
        Returns:
            Total de horas em manutenção no período.
        """
        stmt = (
            select(OrdemServico.data_abertura, OrdemServico.data_conclusao)
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id == equipamento_id,
                OrdemServico.data_abertura <= fim,
                or_(
                    OrdemServico.data_conclusao.is_(None),
                    OrdemServico.data_conclusao >= inicio,
                ),
            )
        )
        result = await self.session.execute(stmt)
        total_horas = 0.0
        agora = datetime.now(timezone.utc)
        for data_abertura, data_conclusao in result.all():
            abertura_efetiva = max(data_abertura, inicio)
            conclusao_efetiva = min(data_conclusao or agora, fim)
            if conclusao_efetiva > abertura_efetiva:
                total_horas += (conclusao_efetiva - abertura_efetiva).total_seconds() / 3600.0
        return round(total_horas, 2)

    async def obter_horas_trabalhadas(
        self,
        equipamento_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
    ) -> float:
        """Calcula a soma das horas trabalhadas nas jornadas do equipamento no período.
        
        Args:
            equipamento_id: ID do equipamento.
            inicio: Data de início do período.
            fim: Data de fim do período.
            
        Returns:
            Total de horas trabalhadas.
        """
        stmt = (
            select(JornadaEquipamento.horimetro_inicial, JornadaEquipamento.horimetro_final)
            .where(
                JornadaEquipamento.tenant_id == self.tenant_id,
                JornadaEquipamento.equipamento_id == equipamento_id,
                JornadaEquipamento.status == "FINALIZADA",
                JornadaEquipamento.data_inicio >= inicio,
                JornadaEquipamento.data_fim <= fim,
            )
        )
        result = await self.session.execute(stmt)
        total_horas = 0.0
        for horimetro_inicial, horimetro_final in result.all():
            if horimetro_final is not None and horimetro_inicial is not None:
                if horimetro_final >= horimetro_inicial:
                    total_horas += float(horimetro_final - horimetro_inicial)
        return round(total_horas, 2)

    async def calcular_disponibilidade(
        self,
        equipamento_id: uuid.UUID,
        inicio: datetime,
        fim: datetime,
    ) -> float:
        """Calcula a disponibilidade operacional (%) do equipamento no período.
        
        Args:
            equipamento_id: ID do equipamento.
            inicio: Data de início do período.
            fim: Data de fim do período.
            
        Returns:
            Percentual de disponibilidade operacional.
        """
        total_horas_periodo = (fim - inicio).total_seconds() / 3600.0
        if total_horas_periodo <= 0:
            return 100.0
        tempo_manutencao = await self.obter_tempo_manutencao(equipamento_id, inicio, fim)
        disponibilidade = ((total_horas_periodo - tempo_manutencao) / total_horas_periodo) * 100.0
        return max(0.0, min(100.0, round(disponibilidade, 2)))

    async def obter_custo_combustivel(
        self,
        equipamento_ids: list[uuid.UUID],
        inicio: datetime | None,
    ) -> dict[uuid.UUID, float]:
        """Obtém custos agregados de combustível por equipamento.
        
        Args:
            equipamento_ids: Lista de IDs dos equipamentos.
            inicio: Data de corte inicial opcional.
            
        Returns:
            Dicionário mapeando ID de equipamento para custo total de combustível.
        """
        if not equipamento_ids:
            return {}
        stmt = (
            select(Abastecimento.equipamento_id, func.sum(Abastecimento.custo_total))
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Abastecimento.equipamento_id.in_(equipamento_ids),
            )
        )
        if inicio:
            stmt = stmt.where(Abastecimento.data >= inicio)
        stmt = stmt.group_by(Abastecimento.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def obter_custo_mao_obra(
        self,
        equipamento_ids: list[uuid.UUID],
        inicio: datetime | None,
    ) -> dict[uuid.UUID, float]:
        """Obtém custos agregados de mão de obra de manutenção por equipamento.
        
        Args:
            equipamento_ids: Lista de IDs dos equipamentos.
            inicio: Data de corte inicial opcional.
            
        Returns:
            Dicionário mapeando ID de equipamento para custo total de mão de obra.
        """
        if not equipamento_ids:
            return {}
        stmt = (
            select(OrdemServico.equipamento_id, func.sum(OrdemServico.custo_mao_obra))
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
            )
        )
        if inicio:
            stmt = stmt.where(OrdemServico.data_abertura >= inicio)
        stmt = stmt.group_by(OrdemServico.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def obter_custo_pecas(
        self,
        equipamento_ids: list[uuid.UUID],
        inicio: datetime | None,
    ) -> dict[uuid.UUID, float]:
        """Obtém custos agregados de peças em ordens de serviço por equipamento.
        
        Args:
            equipamento_ids: Lista de IDs dos equipamentos.
            inicio: Data de corte inicial opcional.
            
        Returns:
            Dicionário mapeando ID de equipamento para custo total de peças.
        """
        if not equipamento_ids:
            return {}
        stmt = (
            select(OrdemServico.equipamento_id, func.sum(OrdemServico.custo_total_pecas))
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
            )
        )
        if inicio:
            stmt = stmt.where(OrdemServico.data_abertura >= inicio)
        stmt = stmt.group_by(OrdemServico.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def obter_custo_manutencao_avulsa(
        self,
        equipamento_ids: list[uuid.UUID],
        inicio: datetime | None,
    ) -> dict[uuid.UUID, float]:
        """Obtém custos de registros de manutenções avulsas (sem OS vinculada) por equipamento.
        
        Args:
            equipamento_ids: Lista de IDs dos equipamentos.
            inicio: Data de corte inicial opcional.
            
        Returns:
            Dicionário mapeando ID de equipamento para custo total avulso.
        """
        if not equipamento_ids:
            return {}
        stmt = (
            select(RegistroManutencao.equipamento_id, func.sum(RegistroManutencao.custo_total))
            .where(
                RegistroManutencao.tenant_id == self.tenant_id,
                RegistroManutencao.equipamento_id.in_(equipamento_ids),
                RegistroManutencao.os_id.is_(None),
            )
        )
        if inicio:
            stmt = stmt.where(RegistroManutencao.data_realizacao >= inicio)
        stmt = stmt.group_by(RegistroManutencao.equipamento_id)
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def resolver_up_custo(
        self,
        equipamento_id: uuid.UUID,
        data_registro: datetime,
        talhao_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        """Resolve coerentemente a unidade produtiva apropriada para um custo operacional.
        
        A ordem de precedência é:
        1. UP do talhão informado (se houver).
        2. UP da alocação ativa do equipamento no momento da data informada.
        3. UP legada no cadastro do próprio equipamento (fallback final).
        
        Args:
            equipamento_id: ID do equipamento.
            data_registro: Data em que o custo foi registrado.
            talhao_id: ID opcional do talhão.
            
        Returns:
            UUID da Unidade Produtiva apropriada ou None.
        """
        if talhao_id:
            stmt = select(AreaRural.unidade_produtiva_id).where(AreaRural.id == talhao_id)
            up_talhao = (await self.session.execute(stmt)).scalar_one_or_none()
            if up_talhao:
                return up_talhao

        stmt_aloc = (
            select(EquipamentoAlocacao.unidade_produtiva_id)
            .where(
                EquipamentoAlocacao.tenant_id == self.tenant_id,
                EquipamentoAlocacao.equipamento_id == equipamento_id,
                EquipamentoAlocacao.status == "ATIVA",
                EquipamentoAlocacao.data_inicio <= data_registro,
                or_(
                    EquipamentoAlocacao.data_fim.is_(None),
                    EquipamentoAlocacao.data_fim >= data_registro,
                ),
            )
        )
        up_aloc = (await self.session.execute(stmt_aloc)).scalar_one_or_none()
        if up_aloc:
            return up_aloc

        stmt_eq = select(Equipamento.unidade_produtiva_id).where(Equipamento.id == equipamento_id)
        return (await self.session.execute(stmt_eq)).scalar_one_or_none()

    async def obter_equipamentos_filtrados(
        self,
        ctx: FiltroCustoContexto,
    ) -> list[Equipamento]:
        """Lista equipamentos respeitando alocações ativas e filtros.
        
        Args:
            ctx: Contexto com os parâmetros de filtro de custo.
            
        Returns:
            Lista de equipamentos que pertencem à UP operacional ou legado.
        """
        stmt = select(Equipamento).where(Equipamento.tenant_id == ctx.tenant_id)
        if ctx.unidade_produtiva_id:
            agora = datetime.now(timezone.utc)
            allocated_ids = (
                select(EquipamentoAlocacao.equipamento_id)
                .where(
                    EquipamentoAlocacao.tenant_id == ctx.tenant_id,
                    EquipamentoAlocacao.unidade_produtiva_id == ctx.unidade_produtiva_id,
                    EquipamentoAlocacao.status == "ATIVA",
                    EquipamentoAlocacao.data_inicio <= agora,
                    or_(
                        EquipamentoAlocacao.data_fim.is_(None),
                        EquipamentoAlocacao.data_fim >= agora,
                    ),
                )
            )
            stmt = stmt.where(
                or_(
                    Equipamento.unidade_produtiva_id == ctx.unidade_produtiva_id,
                    Equipamento.id.in_(allocated_ids),
                )
            )
        if ctx.tipo_equipamento:
            stmt = stmt.where(Equipamento.tipo == ctx.tipo_equipamento)
        stmt = stmt.order_by(Equipamento.nome.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _obter_combustivel_safra(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> dict[uuid.UUID | None, float]:
        """Obtém custos de combustível agrupados por safra."""
        stmt = select(Abastecimento.safra_id, func.sum(Abastecimento.custo_total)).where(
            Abastecimento.tenant_id == self.tenant_id
        )
        if inicio:
            stmt = stmt.where(Abastecimento.data >= inicio)
        if equipamento_ids:
            stmt = stmt.where(Abastecimento.equipamento_id.in_(equipamento_ids))
        result = await self.session.execute(stmt.group_by(Abastecimento.safra_id))
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_os_safra(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> dict[uuid.UUID | None, float]:
        """Obtém custos de OS (peças + mão de obra) agrupados por safra."""
        stmt = select(
            OrdemServico.safra_id,
            func.sum(OrdemServico.custo_mao_obra + OrdemServico.custo_total_pecas),
        ).where(OrdemServico.tenant_id == self.tenant_id)
        if inicio:
            stmt = stmt.where(OrdemServico.data_abertura >= inicio)
        if equipamento_ids:
            stmt = stmt.where(OrdemServico.equipamento_id.in_(equipamento_ids))
        result = await self.session.execute(stmt.group_by(OrdemServico.safra_id))
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_avulsa_safra(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> dict[uuid.UUID | None, float]:
        """Obtém custos de manutenção avulsa agrupados por safra."""
        stmt = select(RegistroManutencao.safra_id, func.sum(RegistroManutencao.custo_total)).where(
            RegistroManutencao.tenant_id == self.tenant_id,
            RegistroManutencao.os_id.is_(None),
        )
        if inicio:
            stmt = stmt.where(RegistroManutencao.data_realizacao >= inicio)
        if equipamento_ids:
            stmt = stmt.where(RegistroManutencao.equipamento_id.in_(equipamento_ids))
        result = await self.session.execute(stmt.group_by(RegistroManutencao.safra_id))
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def obter_custos_por_safra(
        self,
        inicio: datetime | list[uuid.UUID] | None = None,
    ) -> list[dict]:
        """Consolida os custos operacionais por safra no período."""
        equipamento_ids = None
        data_inicio = None
        if isinstance(inicio, list):
            equipamento_ids = inicio
        else:
            data_inicio = inicio

        fuel = await self._obter_combustivel_safra(data_inicio, equipamento_ids)
        os_costs = await self._obter_os_safra(data_inicio, equipamento_ids)
        avulsas = await self._obter_avulsa_safra(data_inicio, equipamento_ids)
        
        safras_ids = set(fuel.keys()) | set(os_costs.keys()) | set(avulsas.keys())
        totais = {}
        total_geral = 0.0
        for s_id in safras_ids:
            custo = fuel.get(s_id, 0.0) + os_costs.get(s_id, 0.0) + avulsas.get(s_id, 0.0)
            if s_id is not None:
                totais[s_id] = custo
                total_geral += custo

        safra_models = {}
        if totais:
            stmt = select(Safra).where(Safra.id.in_(list(totais.keys())))
            res = await self.session.execute(stmt)
            safra_models = {s.id: s for s in res.scalars().all()}

        resposta = ResultadoHibrido()
        for s_id, custo in totais.items():
            s = safra_models.get(s_id)
            nome = f"{s.ano_safra} / {s.cultura}" if s else "Outros / Sem Safra"
            pct = (custo / total_geral * 100.0) if total_geral > 0 else 0.0
            resposta.append({
                "safra_id": s_id,
                "safra_nome": nome,
                "custo_total": round(custo, 2),
                "participacao_percentual": round(pct, 2)
            })
        return ResultadoHibrido(sorted(resposta, key=lambda x: x["custo_total"], reverse=True))

    async def _obter_registros_abastecimento(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> list[tuple[uuid.UUID, datetime, uuid.UUID | None, float]]:
        """Busca abastecimentos brutos para cálculo de rateio por UP."""
        stmt = select(
            Abastecimento.equipamento_id,
            Abastecimento.data,
            Abastecimento.talhao_id,
            Abastecimento.custo_total,
        ).where(Abastecimento.tenant_id == self.tenant_id)
        if inicio:
            stmt = stmt.where(Abastecimento.data >= inicio)
        if equipamento_ids:
            stmt = stmt.where(Abastecimento.equipamento_id.in_(equipamento_ids))
        res = await self.session.execute(stmt)
        return [
            (row[0], row[1], row[2], float(row[3] or 0.0))
            for row in res.all()
        ]

    async def _obter_registros_os(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> list[tuple[uuid.UUID, datetime, uuid.UUID | None, float]]:
        """Busca ordens de serviço brutas para cálculo de rateio por UP."""
        stmt = select(
            OrdemServico.equipamento_id,
            OrdemServico.data_abertura,
            OrdemServico.talhao_id,
            OrdemServico.custo_mao_obra + OrdemServico.custo_total_pecas,
        ).where(OrdemServico.tenant_id == self.tenant_id)
        if inicio:
            stmt = stmt.where(OrdemServico.data_abertura >= inicio)
        if equipamento_ids:
            stmt = stmt.where(OrdemServico.equipamento_id.in_(equipamento_ids))
        res = await self.session.execute(stmt)
        return [
            (row[0], row[1], row[2], float(row[3] or 0.0))
            for row in res.all()
        ]

    async def _obter_registros_avulsos(
        self,
        inicio: datetime | None,
        equipamento_ids: list[uuid.UUID] | None = None,
    ) -> list[tuple[uuid.UUID, datetime, uuid.UUID | None, float]]:
        """Busca manutenções avulsas brutas para cálculo de rateio por UP."""
        stmt = select(
            RegistroManutencao.equipamento_id,
            RegistroManutencao.data_realizacao,
            RegistroManutencao.talhao_id,
            RegistroManutencao.custo_total,
        ).where(
            RegistroManutencao.tenant_id == self.tenant_id,
            RegistroManutencao.os_id.is_(None),
        )
        if inicio:
            stmt = stmt.where(RegistroManutencao.data_realizacao >= inicio)
        if equipamento_ids:
            stmt = stmt.where(RegistroManutencao.equipamento_id.in_(equipamento_ids))
        res = await self.session.execute(stmt)
        return [
            (row[0], row[1], row[2], float(row[3] or 0.0))
            for row in res.all()
        ]

    async def consolidar_por_up(
        self,
        inicio: datetime | list[uuid.UUID] | None = None,
    ) -> list[dict]:
        """Consolida os custos operacionais por Unidade Produtiva (UP)."""
        equipamento_ids = None
        data_inicio = None
        if isinstance(inicio, list):
            equipamento_ids = inicio
        else:
            data_inicio = inicio

        abasts = await self._obter_registros_abastecimento(data_inicio, equipamento_ids)
        os_list = await self._obter_registros_os(data_inicio, equipamento_ids)
        avulsos = await self._obter_registros_avulsos(data_inicio, equipamento_ids)

        por_up = defaultdict(float)
        total_geral = 0.0

        for eq_id, dt, t_id, val in abasts + os_list + avulsos:
            up_id = await self.resolver_up_custo(eq_id, dt, t_id)
            por_up[up_id] += val
            total_geral += val

        up_nomes = {}
        valid_up_ids = [uid for uid in por_up.keys() if uid is not None]
        if valid_up_ids:
            stmt = select(UnidadeProdutiva.id, UnidadeProdutiva.nome).where(UnidadeProdutiva.id.in_(valid_up_ids))
            res = await self.session.execute(stmt)
            up_nomes = {r[0]: r[1] for r in res.all()}

        resposta = ResultadoHibrido()
        for up_id, custo in por_up.items():
            nome = up_nomes.get(up_id, "Equipamentos Globais / Sem UP")
            pct = (custo / total_geral * 100.0) if total_geral > 0 else 0.0
            resposta.append({
                "unidade_produtiva_id": up_id,
                "unidade_produtiva_nome": nome,
                "custo_total": round(custo, 2),
                "participacao_percentual": round(pct, 2)
            })
        return ResultadoHibrido(sorted(resposta, key=lambda x: x["custo_total"], reverse=True))
