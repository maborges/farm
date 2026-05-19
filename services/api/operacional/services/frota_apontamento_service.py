from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.operational_context import (
    validate_area_in_tenant,
    validate_operador_context,
    validate_production_unit_context,
    validate_safra_area_link,
    validate_safra_in_tenant,
)
from operacional.models.apontamento import ApontamentoUso
from operacional.models.frota import JornadaEquipamento
from operacional.schemas.apontamento import ApontamentoUsoCreate, ApontamentoUsoUpdate


@dataclass(frozen=True)
class _ApontamentoContexto:
    equipamento: Equipamento
    operador_id: uuid.UUID | None
    jornada_id: uuid.UUID | None
    unidade_produtiva_id: uuid.UUID | None
    safra_id: uuid.UUID | None
    production_unit_id: uuid.UUID | None
    talhao_id: uuid.UUID | None
    operacao_id: uuid.UUID | None


class FrotaApontamentoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar(
        self,
        *,
        equipamento_id: uuid.UUID | None = None,
        jornada_id: uuid.UUID | None = None,
        operador_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
        production_unit_id: uuid.UUID | None = None,
        talhao_id: uuid.UUID | None = None,
        operacao_id: uuid.UUID | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> list[ApontamentoUso]:
        stmt = select(ApontamentoUso).where(ApontamentoUso.tenant_id == self.tenant_id)
        if equipamento_id is not None:
            stmt = stmt.where(ApontamentoUso.equipamento_id == equipamento_id)
        if jornada_id is not None:
            stmt = stmt.where(ApontamentoUso.jornada_id == jornada_id)
        if operador_id is not None:
            stmt = stmt.where(ApontamentoUso.operador_id == operador_id)
        if safra_id is not None:
            stmt = stmt.where(ApontamentoUso.safra_id == safra_id)
        if production_unit_id is not None:
            stmt = stmt.where(ApontamentoUso.production_unit_id == production_unit_id)
        if talhao_id is not None:
            stmt = stmt.where(ApontamentoUso.talhao_id == talhao_id)
        if operacao_id is not None:
            stmt = stmt.where(ApontamentoUso.operacao_id == operacao_id)
        if data_inicio is not None:
            stmt = stmt.where(ApontamentoUso.data >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(ApontamentoUso.data <= data_fim)
        stmt = stmt.order_by(ApontamentoUso.data.desc(), ApontamentoUso.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, dados: ApontamentoUsoCreate) -> ApontamentoUso:
        contexto = await self._resolver_contexto(dados)
        apontamento = ApontamentoUso(
            tenant_id=self.tenant_id,
            equipamento_id=contexto.equipamento.id,
            jornada_id=contexto.jornada_id,
            operador_id=contexto.operador_id,
            data=dados.data,
            turno=dados.turno,
            horimetro_inicio=dados.horimetro_inicio,
            horimetro_fim=dados.horimetro_fim,
            km_inicio=dados.km_inicio,
            km_fim=dados.km_fim,
            unidade_produtiva_id=contexto.unidade_produtiva_id,
            safra_id=contexto.safra_id,
            production_unit_id=contexto.production_unit_id,
            talhao_id=contexto.talhao_id,
            operacao_id=contexto.operacao_id,
            area_ha_trabalhada=dados.area_ha_trabalhada,
            quantidade_produzida=dados.quantidade_produzida,
            quantidade_aplicada=dados.quantidade_aplicada,
            custo_total=dados.custo_total,
            custo_por_ha=dados.custo_por_ha,
            implementos_ids=dados.implementos_ids,
            combustivel_consumido_l=dados.combustivel_consumido_l,
            observacoes=dados.observacoes,
        )
        self.session.add(apontamento)
        await self.session.flush()

        await self._atualizar_equipamento(contexto.equipamento, dados)
        await self._registrar_allocacao_economica(apontamento)
        return apontamento

    async def atualizar(self, apontamento_id: uuid.UUID, dados: ApontamentoUsoUpdate) -> ApontamentoUso:
        apontamento = await self._obter(apontamento_id)
        for chave, valor in dados.model_dump(exclude_none=True).items():
            setattr(apontamento, chave, valor)
        await self.session.flush()
        return apontamento

    async def remover(self, apontamento_id: uuid.UUID) -> None:
        apontamento = await self._obter(apontamento_id)
        await self.session.delete(apontamento)

    async def _obter(self, apontamento_id: uuid.UUID) -> ApontamentoUso:
        stmt = select(ApontamentoUso).where(
            ApontamentoUso.id == apontamento_id,
            ApontamentoUso.tenant_id == self.tenant_id,
        )
        apontamento = (await self.session.execute(stmt)).scalar_one_or_none()
        if apontamento is None:
            raise EntityNotFoundError("Apontamento não encontrado.")
        return apontamento

    async def _resolver_contexto(self, dados: ApontamentoUsoCreate) -> _ApontamentoContexto:
        equipamento = await self._obter_equipamento(dados.equipamento_id)
        if equipamento.status != "ATIVO" or equipamento.status == "EM_MANUTENCAO" or getattr(equipamento, "bloqueado_operacional", False):
            raise BusinessRuleError("Equipamento indisponível para apontamento operacional.")

        jornada = None
        if dados.jornada_id is not None:
            jornada = await self._obter_jornada(dados.jornada_id)
            if jornada.equipamento_id != equipamento.id:
                raise BusinessRuleError("Jornada não pertence ao equipamento informado.")
            if jornada.status == "CANCELADA":
                raise BusinessRuleError("Jornada cancelada não pode receber apontamento.")

        operacao = None
        if dados.operacao_id is not None:
            operacao = await self._obter_operacao(dados.operacao_id)

        operador_id = dados.operador_id
        if jornada and jornada.operador_id:
            if operador_id is not None and operador_id != jornada.operador_id:
                raise BusinessRuleError("Operador do apontamento não corresponde à jornada informada.")
            operador_id = jornada.operador_id
        if operacao and operacao.operador_id:
            if operador_id is not None and operador_id != operacao.operador_id:
                raise BusinessRuleError("Operador do apontamento não corresponde à operação informada.")
            operador_id = operacao.operador_id
        safra_id = dados.safra_id or (jornada.safra_id if jornada else None) or (operacao.safra_id if operacao else None)
        talhao_id = dados.talhao_id or (jornada.talhao_id if jornada else None) or (operacao.talhao_id if operacao else None)
        unidade_produtiva_id = dados.unidade_produtiva_id or (jornada.unidade_produtiva_id if jornada else None)

        if jornada and dados.safra_id is not None and jornada.safra_id is not None and dados.safra_id != jornada.safra_id:
            raise BusinessRuleError("Safra do apontamento não corresponde à jornada informada.")
        if jornada and dados.talhao_id is not None and jornada.talhao_id is not None and dados.talhao_id != jornada.talhao_id:
            raise BusinessRuleError("Talhão do apontamento não corresponde à jornada informada.")
        if jornada and dados.unidade_produtiva_id is not None and jornada.unidade_produtiva_id is not None and dados.unidade_produtiva_id != jornada.unidade_produtiva_id:
            raise BusinessRuleError("Unidade produtiva do apontamento não corresponde à jornada informada.")
        if operacao and dados.safra_id is not None and operacao.safra_id != dados.safra_id:
            raise BusinessRuleError("Safra do apontamento não corresponde à operação informada.")
        if operacao and dados.talhao_id is not None and operacao.talhao_id != dados.talhao_id:
            raise BusinessRuleError("Talhão do apontamento não corresponde à operação informada.")

        if talhao_id is not None:
            area = await validate_area_in_tenant(self.session, tenant_id=self.tenant_id, area_id=talhao_id)
            if unidade_produtiva_id is None:
                unidade_produtiva_id = area.unidade_produtiva_id
            elif area.unidade_produtiva_id and area.unidade_produtiva_id != unidade_produtiva_id:
                raise BusinessRuleError("Talhão não pertence à unidade produtiva informada.")
            if safra_id is not None:
                await validate_safra_area_link(
                    self.session,
                    tenant_id=self.tenant_id,
                    safra_id=safra_id,
                    area_id=talhao_id,
                )
        if safra_id is not None:
            await validate_safra_in_tenant(self.session, tenant_id=self.tenant_id, safra_id=safra_id)

        if operador_id is not None:
            await validate_operador_context(
                self.session,
                tenant_id=self.tenant_id,
                operador_id=operador_id,
                unidade_produtiva_id=unidade_produtiva_id,
            )

        production_unit_id = dados.production_unit_id
        if production_unit_id is not None:
            if safra_id is None or talhao_id is None:
                raise BusinessRuleError("ProductionUnit exige safra e talhão informados.")
            await validate_production_unit_context(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=production_unit_id,
                safra_id=safra_id,
                area_id=talhao_id,
            )
        elif safra_id is not None and talhao_id is not None:
            production_unit_id = await self._resolver_production_unit_id(safra_id=safra_id, talhao_id=talhao_id)

        if operacao is not None:
            if safra_id is not None and operacao.safra_id != safra_id:
                raise BusinessRuleError("Operação agrícola incompatível com a safra do apontamento.")
            if talhao_id is not None and operacao.talhao_id != talhao_id:
                raise BusinessRuleError("Operação agrícola incompatível com o talhão do apontamento.")
        if jornada is not None and operacao is not None:
            if jornada.safra_id is not None and operacao.safra_id is not None and jornada.safra_id != operacao.safra_id:
                raise BusinessRuleError("Jornada e operação agrícola não compartilham a mesma safra.")
            if jornada.talhao_id is not None and operacao.talhao_id is not None and jornada.talhao_id != operacao.talhao_id:
                raise BusinessRuleError("Jornada e operação agrícola não compartilham o mesmo talhão.")

        return _ApontamentoContexto(
            equipamento=equipamento,
            operador_id=operador_id,
            jornada_id=jornada.id if jornada else None,
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            talhao_id=talhao_id,
            operacao_id=operacao.id if operacao else dados.operacao_id,
        )

    async def _obter_equipamento(self, equipamento_id: uuid.UUID) -> Equipamento:
        stmt = select(Equipamento).where(
            Equipamento.id == equipamento_id,
            Equipamento.tenant_id == self.tenant_id,
        )
        equipamento = (await self.session.execute(stmt)).scalar_one_or_none()
        if equipamento is None:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant informado.")
        return equipamento

    async def _obter_jornada(self, jornada_id: uuid.UUID) -> JornadaEquipamento:
        stmt = select(JornadaEquipamento).where(
            JornadaEquipamento.id == jornada_id,
            JornadaEquipamento.tenant_id == self.tenant_id,
        )
        jornada = (await self.session.execute(stmt)).scalar_one_or_none()
        if jornada is None:
            raise EntityNotFoundError("Jornada não encontrada para o tenant informado.")
        return jornada

    async def _obter_operacao(self, operacao_id: uuid.UUID) -> OperacaoAgricola:
        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.id == operacao_id,
            OperacaoAgricola.tenant_id == self.tenant_id,
        )
        operacao = (await self.session.execute(stmt)).scalar_one_or_none()
        if operacao is None:
            raise EntityNotFoundError("Operação agrícola não encontrada para o tenant informado.")
        return operacao

    async def _resolver_production_unit_id(self, *, safra_id: uuid.UUID, talhao_id: uuid.UUID) -> uuid.UUID | None:
        stmt = (
            select(ProductionUnit.id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.area_id == talhao_id,
            )
            .order_by((ProductionUnit.status == "ATIVA").desc(), ProductionUnit.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _atualizar_equipamento(self, equipamento: Equipamento, dados: ApontamentoUsoCreate) -> None:
        if dados.horimetro_fim > float(equipamento.horimetro_atual or 0.0):
            equipamento.horimetro_atual = dados.horimetro_fim
        if dados.km_fim is not None and (equipamento.km_atual is None or dados.km_fim > float(equipamento.km_atual)):
            equipamento.km_atual = dados.km_fim

    async def _registrar_allocacao_economica(self, apontamento: ApontamentoUso) -> None:
        if apontamento.custo_total is None or apontamento.custo_total <= 0:
            return
        if apontamento.production_unit_id is None:
            return
        if apontamento.safra_id is None:
            return
        await registrar_cost_allocation(
            self.session,
            tenant_id=self.tenant_id,
            production_unit_id=apontamento.production_unit_id,
            source="MANUAL",
            source_id=apontamento.id,
            amount=float(apontamento.custo_total),
            allocation_date=apontamento.data.date() if isinstance(apontamento.data, datetime) else date.today(),
            cost_category="OUTROS",
            allocation_method="DIRECT",
            allocation_basis=float(apontamento.area_ha_trabalhada or 0.0) if apontamento.area_ha_trabalhada is not None else None,
        )
