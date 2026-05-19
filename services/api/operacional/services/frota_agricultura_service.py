from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from agricola.operacoes.models import OperacaoAgricola
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa
from core.exceptions import EntityNotFoundError
from operacional.models.apontamento import ApontamentoUso
from operacional.schemas.frota_agricultura import (
    FrotaAgriculturaApontamentoEquipamentoItem,
    FrotaAgriculturaApontamentoOperacaoItem,
    FrotaAgriculturaApontamentoOperadorItem,
    FrotaAgriculturaApontamentoTalhaoItem,
    FrotaAgriculturaEquipamentoResponse,
    FrotaAgriculturaEquipamentoSafraItem,
    FrotaAgriculturaOperacaoItem,
    FrotaAgriculturaOperacoesResponse,
    FrotaAgriculturaResponse,
    FrotaAgriculturaResumo,
    FrotaAgriculturaSafraItem,
    FrotaAgriculturaSafraResponse,
    FrotaAgriculturaTalhaoItem,
    FrotaAgriculturaTalhaoResponse,
)
from operacional.services.frota_jornada_service import FrotaJornadaService


@dataclass
class _Registro:
    jornada_id: uuid.UUID
    equipamento_id: uuid.UUID
    equipamento_nome: str
    equipamento_tipo: str
    safra_id: uuid.UUID | None
    safra_nome: str
    talhao_id: uuid.UUID | None
    talhao_nome: str
    tipo_operacao: str
    horas: float
    km: float
    custo_estimado: float | None
    metrica_custo: str


@dataclass
class _RegistroApontamento:
    apontamento_id: uuid.UUID
    equipamento_id: uuid.UUID
    equipamento_nome: str
    equipamento_tipo: str
    operador_id: uuid.UUID | None
    operador_nome: str | None
    safra_id: uuid.UUID | None
    safra_nome: str
    talhao_id: uuid.UUID | None
    talhao_nome: str
    operacao_id: uuid.UUID | None
    operacao_nome: str
    horas: float
    hectares: float
    quantidade: float
    custo_total: float | None
    custo_por_ha: float | None


class FrotaAgriculturaService(FrotaJornadaService):
    async def obter_resumo(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaResponse:
        agora = datetime.now(timezone.utc)
        registros = await self._montar_registros(unidade_produtiva_id=unidade_produtiva_id)
        apontamentos = await self._montar_apontamentos_registros(unidade_produtiva_id=unidade_produtiva_id)
        return FrotaAgriculturaResponse(
            resumo=self._montar_resumo(registros, apontamentos),
            por_safra=self._agrupar_por_safra(registros),
            por_talhao=self._agrupar_por_talhao(registros),
            por_operacao=self._agrupar_por_operacao(registros),
            equipamentos_por_safra=self._agrupar_equipamentos_por_safra(registros),
            apontamentos_por_operacao=self._agrupar_apontamentos_por_operacao(apontamentos),
            apontamentos_por_talhao=self._agrupar_apontamentos_por_talhao(apontamentos),
            apontamentos_por_operador=self._agrupar_apontamentos_por_operador(apontamentos),
            equipamentos_por_apontamento=self._agrupar_apontamentos_por_equipamento(apontamentos),
            gerado_em=agora,
        )

    async def obter_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaEquipamentoResponse:
        agora = datetime.now(timezone.utc)
        registros = await self._montar_registros(
            unidade_produtiva_id=unidade_produtiva_id,
            equipamento_id=equipamento_id,
        )
        if not registros:
            raise EntityNotFoundError("Equipamento sem jornadas agrícolas no tenant/contexto informado.")
        return FrotaAgriculturaEquipamentoResponse(
            equipamento_id=equipamento_id,
            equipamento_nome=registros[0].equipamento_nome,
            equipamento_tipo=registros[0].equipamento_tipo,
            resumo=self._montar_resumo(registros),
            por_safra=self._agrupar_por_safra(registros),
            por_talhao=self._agrupar_por_talhao(registros),
            por_operacao=self._agrupar_por_operacao(registros),
            gerado_em=agora,
        )

    async def obter_safra(
        self,
        safra_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaSafraResponse:
        agora = datetime.now(timezone.utc)
        registros = [item for item in await self._montar_registros(unidade_produtiva_id=unidade_produtiva_id) if item.safra_id == safra_id]
        if not registros:
            raise EntityNotFoundError("Safra sem jornadas de frota no tenant/contexto informado.")
        return FrotaAgriculturaSafraResponse(
            safra_id=safra_id,
            safra_nome=registros[0].safra_nome,
            resumo=self._montar_resumo(registros),
            por_talhao=self._agrupar_por_talhao(registros),
            por_operacao=self._agrupar_por_operacao(registros),
            equipamentos=self._agrupar_equipamentos_por_safra(registros),
            gerado_em=agora,
        )

    async def obter_talhao(
        self,
        talhao_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaTalhaoResponse:
        agora = datetime.now(timezone.utc)
        registros = [item for item in await self._montar_registros(unidade_produtiva_id=unidade_produtiva_id) if item.talhao_id == talhao_id]
        if not registros:
            raise EntityNotFoundError("Talhão sem jornadas de frota no tenant/contexto informado.")
        return FrotaAgriculturaTalhaoResponse(
            talhao_id=talhao_id,
            talhao_nome=registros[0].talhao_nome,
            resumo=self._montar_resumo(registros),
            por_operacao=self._agrupar_por_operacao(registros),
            equipamentos=self._agrupar_equipamentos_por_safra(registros),
            gerado_em=agora,
        )

    async def obter_operacoes(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaOperacoesResponse:
        agora = datetime.now(timezone.utc)
        registros = await self._montar_registros(unidade_produtiva_id=unidade_produtiva_id)
        return FrotaAgriculturaOperacoesResponse(
            resumo=self._montar_resumo(registros),
            operacoes=self._agrupar_por_operacao(registros),
            gerado_em=agora,
        )

    async def _montar_registros(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        equipamento_id: uuid.UUID | None = None,
    ) -> list[_Registro]:
        jornadas = await self.listar_jornadas(
            unidade_produtiva_id=unidade_produtiva_id,
            equipamento_id=equipamento_id,
            status="FINALIZADA",
        )
        if not jornadas.jornadas:
            return []
        return [
            _Registro(
                jornada_id=item.id,
                equipamento_id=item.equipamento_id,
                equipamento_nome=item.equipamento_nome,
                equipamento_tipo=item.equipamento_tipo,
                safra_id=item.safra_id,
                safra_nome=item.safra_nome or "Sem safra",
                talhao_id=item.talhao_id,
                talhao_nome=item.talhao_nome or "Sem talhão",
                tipo_operacao=item.tipo_operacao,
                horas=float(item.horas_trabalhadas or 0.0),
                km=float(item.km_trabalhados or 0.0),
                custo_estimado=item.custo_estimado,
                metrica_custo=item.metrica_custo,
            )
            for item in jornadas.jornadas
        ]

    async def _montar_apontamentos_registros(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> list[_RegistroApontamento]:
        stmt = select(ApontamentoUso).where(ApontamentoUso.tenant_id == self.tenant_id)
        if unidade_produtiva_id is not None:
            stmt = stmt.where(ApontamentoUso.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(ApontamentoUso.data.desc(), ApontamentoUso.created_at.desc())
        apontamentos = list((await self.session.execute(stmt)).scalars().all())
        if not apontamentos:
            return []

        equipamento_ids = {item.equipamento_id for item in apontamentos}
        operador_ids = {item.operador_id for item in apontamentos if item.operador_id}
        safra_ids = {item.safra_id for item in apontamentos if item.safra_id}
        talhao_ids = {item.talhao_id for item in apontamentos if item.talhao_id}
        operacao_ids = {item.operacao_id for item in apontamentos if item.operacao_id}

        equipamentos = await self._listar_equipamentos_por_ids(list(equipamento_ids))
        pessoas = await self._listar_pessoas(list(operador_ids))
        safras = await self._listar_safras(list(safra_ids))
        talhoes = await self._listar_talhoes(list(talhao_ids))
        operacoes = await self._listar_operacoes(list(operacao_ids))

        return [
            _RegistroApontamento(
                apontamento_id=item.id,
                equipamento_id=item.equipamento_id,
                equipamento_nome=(equipamentos.get(item.equipamento_id).nome if equipamentos.get(item.equipamento_id) else "Equipamento"),
                equipamento_tipo=(equipamentos.get(item.equipamento_id).tipo if equipamentos.get(item.equipamento_id) else "—"),
                operador_id=item.operador_id,
                operador_nome=pessoas.get(item.operador_id) if item.operador_id else None,
                safra_id=item.safra_id,
                safra_nome=safras.get(item.safra_id, "Sem safra") if item.safra_id else "Sem safra",
                talhao_id=item.talhao_id,
                talhao_nome=talhoes.get(item.talhao_id, "Sem talhão") if item.talhao_id else "Sem talhão",
                operacao_id=item.operacao_id,
                operacao_nome=operacoes.get(item.operacao_id, "Sem operação") if item.operacao_id else "Sem operação",
                horas=float(item.horimetro_fim - item.horimetro_inicio),
                hectares=float(item.area_ha_trabalhada or 0.0),
                quantidade=float(item.quantidade_produzida or item.quantidade_aplicada or 0.0),
                custo_total=float(item.custo_total) if item.custo_total is not None else None,
                custo_por_ha=float(item.custo_por_ha) if item.custo_por_ha is not None else None,
            )
            for item in apontamentos
        ]

    def _montar_resumo(
        self,
        registros: list[_Registro],
        apontamentos: list[_RegistroApontamento] | None = None,
    ) -> FrotaAgriculturaResumo:
        horas_totais = round(sum(item.horas for item in registros), 2)
        km_totais = round(sum(item.km for item in registros), 2)
        custos = [float(item.custo_estimado) for item in registros if item.custo_estimado is not None]
        custo_total = round(sum(custos), 2) if custos else None
        apontamentos = apontamentos or []
        hectares_totais = round(sum(item.hectares for item in apontamentos), 2)
        quantidade_total = round(sum(item.quantidade for item in apontamentos), 2)
        horas_apontamentos = round(sum(item.horas for item in apontamentos), 2)
        custos_apontamento = [float(item.custo_total) for item in apontamentos if item.custo_total is not None]
        custo_apontamentos_total = round(sum(custos_apontamento), 2) if custos_apontamento else None
        horas_base_produtividade = horas_totais if horas_totais > 0 else horas_apontamentos
        produtividade_media = round(hectares_totais / horas_base_produtividade, 2) if horas_base_produtividade > 0 and hectares_totais > 0 else None
        custo_medio_por_ha = round(custo_apontamentos_total / hectares_totais, 2) if custo_apontamentos_total is not None and hectares_totais > 0 else None

        por_operacao = self._agrupar_por_operacao(registros)
        por_talhao = self._agrupar_por_talhao(registros)
        equipamento_mais_usado = self._equipamento_mais_usado(registros)

        return FrotaAgriculturaResumo(
            horas_totais=horas_totais,
            km_totais=km_totais,
            custo_estimado_total=custo_total,
            custo_hora_estimado=self._calcular_custo_unitario(registros, "HORA"),
            custo_km_estimado=self._calcular_custo_unitario(registros, "KM"),
            apontamentos_total=len(apontamentos),
            hectares_totais=hectares_totais,
            quantidade_total=quantidade_total,
            custo_apontamentos_total=custo_apontamentos_total,
            produtividade_media_ha_hora=produtividade_media,
            custo_medio_por_ha=custo_medio_por_ha,
            operacao_mais_cara=por_operacao[0].tipo_operacao if por_operacao and por_operacao[0].custo_estimado_total is not None else None,
            operacao_mais_cara_custo=por_operacao[0].custo_estimado_total if por_operacao else None,
            talhao_mais_caro=por_talhao[0].talhao_nome if por_talhao and por_talhao[0].custo_estimado_total is not None else None,
            talhao_mais_caro_custo=por_talhao[0].custo_estimado_total if por_talhao else None,
            equipamento_mais_usado=equipamento_mais_usado[0] if equipamento_mais_usado else None,
            equipamento_mais_usado_valor=equipamento_mais_usado[1] if equipamento_mais_usado else None,
        )

    def _agrupar_apontamentos_por_operacao(self, registros: list[_RegistroApontamento]) -> list[FrotaAgriculturaApontamentoOperacaoItem]:
        grupos: dict[str, list[_RegistroApontamento]] = defaultdict(list)
        for item in registros:
            grupos[item.operacao_nome].append(item)
        resposta = [
            FrotaAgriculturaApontamentoOperacaoItem(
                tipo_operacao=chave,
                apontamentos=len(itens),
                hectares_totais=round(sum(item.hectares for item in itens), 2),
                horas_totais=round(sum(item.horas for item in itens), 2),
                custo_total=self._somar_custos_apontamentos(itens),
                custo_por_ha=self._calcular_apontamento_custo_unitario(itens, "HA"),
                custo_por_hora=self._calcular_apontamento_custo_unitario(itens, "HORA"),
                produtividade_ha_hora=self._calcular_apontamento_produtividade(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.custo_total or 0.0, item.hectares_totais, item.tipo_operacao), reverse=True)

    def _agrupar_apontamentos_por_talhao(self, registros: list[_RegistroApontamento]) -> list[FrotaAgriculturaApontamentoTalhaoItem]:
        grupos: dict[tuple[uuid.UUID | None, str, uuid.UUID | None, str], list[_RegistroApontamento]] = defaultdict(list)
        for item in registros:
            grupos[(item.talhao_id, item.talhao_nome, item.safra_id, item.safra_nome)].append(item)
        resposta = [
            FrotaAgriculturaApontamentoTalhaoItem(
                talhao_id=chave[0],
                talhao_nome=chave[1],
                safra_id=chave[2],
                safra_nome=chave[3],
                apontamentos=len(itens),
                hectares_totais=round(sum(item.hectares for item in itens), 2),
                horas_totais=round(sum(item.horas for item in itens), 2),
                custo_total=self._somar_custos_apontamentos(itens),
                custo_por_ha=self._calcular_apontamento_custo_unitario(itens, "HA"),
                produtividade_ha_hora=self._calcular_apontamento_produtividade(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.custo_total or 0.0, item.hectares_totais, item.talhao_nome), reverse=True)

    def _agrupar_apontamentos_por_operador(self, registros: list[_RegistroApontamento]) -> list[FrotaAgriculturaApontamentoOperadorItem]:
        grupos: dict[tuple[uuid.UUID | None, str], list[_RegistroApontamento]] = defaultdict(list)
        for item in registros:
            grupos[(item.operador_id, item.operador_nome or "Sem operador")].append(item)
        resposta = [
            FrotaAgriculturaApontamentoOperadorItem(
                operador_id=chave[0],
                operador_nome=chave[1],
                apontamentos=len(itens),
                equipamentos_utilizados=len({item.equipamento_id for item in itens}),
                horas_totais=round(sum(item.horas for item in itens), 2),
                hectares_totais=round(sum(item.hectares for item in itens), 2),
                custo_total=self._somar_custos_apontamentos(itens),
                custo_por_ha=self._calcular_apontamento_custo_unitario(itens, "HA"),
                produtividade_ha_hora=self._calcular_apontamento_produtividade(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.horas_totais, item.hectares_totais, item.operador_nome), reverse=True)

    def _agrupar_apontamentos_por_equipamento(self, registros: list[_RegistroApontamento]) -> list[FrotaAgriculturaApontamentoEquipamentoItem]:
        grupos: dict[tuple[uuid.UUID, str, str], list[_RegistroApontamento]] = defaultdict(list)
        for item in registros:
            grupos[(item.equipamento_id, item.equipamento_nome, item.equipamento_tipo)].append(item)
        resposta = [
            FrotaAgriculturaApontamentoEquipamentoItem(
                equipamento_id=chave[0],
                equipamento_nome=chave[1],
                equipamento_tipo=chave[2],
                apontamentos=len(itens),
                horas_totais=round(sum(item.horas for item in itens), 2),
                hectares_totais=round(sum(item.hectares for item in itens), 2),
                custo_total=self._somar_custos_apontamentos(itens),
                custo_por_ha=self._calcular_apontamento_custo_unitario(itens, "HA"),
                produtividade_ha_hora=self._calcular_apontamento_produtividade(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.hectares_totais, item.horas_totais, item.equipamento_nome), reverse=True)

    def _agrupar_por_safra(self, registros: list[_Registro]) -> list[FrotaAgriculturaSafraItem]:
        grupos: dict[tuple[uuid.UUID | None, str], list[_Registro]] = defaultdict(list)
        for item in registros:
            grupos[(item.safra_id, item.safra_nome)].append(item)

        resposta = [
            FrotaAgriculturaSafraItem(
                safra_id=chave[0],
                safra_nome=chave[1],
                horas_totais=round(sum(item.horas for item in itens), 2),
                km_totais=round(sum(item.km for item in itens), 2),
                custo_estimado_total=self._somar_custos(itens),
                custo_hora_estimado=self._calcular_custo_unitario(itens, "HORA"),
                custo_km_estimado=self._calcular_custo_unitario(itens, "KM"),
                total_jornadas=len(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.custo_estimado_total or 0.0, item.horas_totais, item.safra_nome), reverse=True)

    def _agrupar_por_talhao(self, registros: list[_Registro]) -> list[FrotaAgriculturaTalhaoItem]:
        grupos: dict[tuple[uuid.UUID | None, str, uuid.UUID | None, str | None], list[_Registro]] = defaultdict(list)
        for item in registros:
            grupos[(item.talhao_id, item.talhao_nome, item.safra_id, item.safra_nome)].append(item)

        resposta = [
            FrotaAgriculturaTalhaoItem(
                talhao_id=chave[0],
                talhao_nome=chave[1],
                safra_id=chave[2],
                safra_nome=chave[3],
                horas_totais=round(sum(item.horas for item in itens), 2),
                km_totais=round(sum(item.km for item in itens), 2),
                custo_estimado_total=self._somar_custos(itens),
                custo_hora_estimado=self._calcular_custo_unitario(itens, "HORA"),
                custo_km_estimado=self._calcular_custo_unitario(itens, "KM"),
                total_jornadas=len(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.custo_estimado_total or 0.0, item.horas_totais, item.talhao_nome), reverse=True)

    def _agrupar_por_operacao(self, registros: list[_Registro]) -> list[FrotaAgriculturaOperacaoItem]:
        grupos: dict[str, list[_Registro]] = defaultdict(list)
        for item in registros:
            grupos[item.tipo_operacao].append(item)
        resposta = [
            FrotaAgriculturaOperacaoItem(
                tipo_operacao=chave,
                horas_totais=round(sum(item.horas for item in itens), 2),
                km_totais=round(sum(item.km for item in itens), 2),
                custo_estimado_total=self._somar_custos(itens),
                custo_hora_estimado=self._calcular_custo_unitario(itens, "HORA"),
                custo_km_estimado=self._calcular_custo_unitario(itens, "KM"),
                total_jornadas=len(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(resposta, key=lambda item: (item.custo_estimado_total or 0.0, item.horas_totais, item.tipo_operacao), reverse=True)

    def _agrupar_equipamentos_por_safra(self, registros: list[_Registro]) -> list[FrotaAgriculturaEquipamentoSafraItem]:
        grupos: dict[tuple[uuid.UUID | None, str, uuid.UUID, str, str], list[_Registro]] = defaultdict(list)
        for item in registros:
            grupos[(item.safra_id, item.safra_nome, item.equipamento_id, item.equipamento_nome, item.equipamento_tipo)].append(item)
        resposta = [
            FrotaAgriculturaEquipamentoSafraItem(
                safra_id=chave[0],
                safra_nome=chave[1],
                equipamento_id=chave[2],
                equipamento_nome=chave[3],
                equipamento_tipo=chave[4],
                horas_totais=round(sum(item.horas for item in itens), 2),
                km_totais=round(sum(item.km for item in itens), 2),
                custo_estimado_total=self._somar_custos(itens),
                custo_hora_estimado=self._calcular_custo_unitario(itens, "HORA"),
                custo_km_estimado=self._calcular_custo_unitario(itens, "KM"),
                total_jornadas=len(itens),
            )
            for chave, itens in grupos.items()
        ]
        return sorted(
            resposta,
            key=lambda item: (
                item.safra_nome,
                max(item.horas_totais, item.km_totais),
                item.custo_estimado_total or 0.0,
                item.equipamento_nome,
            ),
            reverse=True,
        )

    @staticmethod
    def _somar_custos(registros: list[_Registro]) -> float | None:
        custos = [float(item.custo_estimado) for item in registros if item.custo_estimado is not None]
        if not custos:
            return None
        return round(sum(custos), 2)

    @staticmethod
    def _calcular_custo_unitario(registros: list[_Registro], metrica: str) -> float | None:
        custos = [
            float(item.custo_estimado)
            for item in registros
            if item.custo_estimado is not None and item.metrica_custo == metrica
        ]
        if not custos:
            return None
        divisor = sum(
            item.horas if metrica == "HORA" else item.km
            for item in registros
            if item.metrica_custo == metrica
        )
        if divisor <= 0:
            return None
        return round(sum(custos) / divisor, 2)

    @staticmethod
    def _somar_custos_apontamentos(registros: list[_RegistroApontamento]) -> float | None:
        custos = [float(item.custo_total) for item in registros if item.custo_total is not None]
        if not custos:
            return None
        return round(sum(custos), 2)

    @staticmethod
    def _calcular_apontamento_custo_unitario(registros: list[_RegistroApontamento], divisor: str) -> float | None:
        custos = [float(item.custo_total) for item in registros if item.custo_total is not None]
        if not custos:
            return None
        base = sum(item.hectares for item in registros) if divisor == "HA" else sum(item.horas for item in registros)
        if base <= 0:
            return None
        return round(sum(custos) / base, 2)

    @staticmethod
    def _calcular_apontamento_produtividade(registros: list[_RegistroApontamento]) -> float | None:
        horas = sum(item.horas for item in registros)
        hectares = sum(item.hectares for item in registros)
        if horas <= 0:
            return None
        return round(hectares / horas, 2)

    @staticmethod
    def _equipamento_mais_usado(registros: list[_Registro]) -> tuple[str, float] | None:
        if not registros:
            return None
        agregados: dict[str, float] = defaultdict(float)
        for item in registros:
            valor = item.horas if item.horas > 0 else item.km
            agregados[item.equipamento_nome] += valor
        if not agregados:
            return None
        return max(agregados.items(), key=lambda item: item[1])

    async def _listar_operacoes(self, operacao_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not operacao_ids:
            return {}
        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.id.in_(operacao_ids),
        )
        operacoes = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item.tipo for item in operacoes}

    async def _listar_equipamentos_por_ids(self, equipamento_ids: list[uuid.UUID]) -> dict[uuid.UUID, Equipamento]:
        if not equipamento_ids:
            return {}
        stmt = select(Equipamento).where(
            Equipamento.tenant_id == self.tenant_id,
            Equipamento.id.in_(equipamento_ids),
        )
        equipamentos = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item for item in equipamentos}
