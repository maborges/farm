from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from core.exceptions import EntityNotFoundError
from operacional.schemas.frota_agricultura import (
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


class FrotaAgriculturaService(FrotaJornadaService):
    async def obter_resumo(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaAgriculturaResponse:
        agora = datetime.now(timezone.utc)
        registros = await self._montar_registros(unidade_produtiva_id=unidade_produtiva_id)
        return FrotaAgriculturaResponse(
            resumo=self._montar_resumo(registros),
            por_safra=self._agrupar_por_safra(registros),
            por_talhao=self._agrupar_por_talhao(registros),
            por_operacao=self._agrupar_por_operacao(registros),
            equipamentos_por_safra=self._agrupar_equipamentos_por_safra(registros),
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

    def _montar_resumo(self, registros: list[_Registro]) -> FrotaAgriculturaResumo:
        horas_totais = round(sum(item.horas for item in registros), 2)
        km_totais = round(sum(item.km for item in registros), 2)
        custos = [float(item.custo_estimado) for item in registros if item.custo_estimado is not None]
        custo_total = round(sum(custos), 2) if custos else None

        por_operacao = self._agrupar_por_operacao(registros)
        por_talhao = self._agrupar_por_talhao(registros)
        equipamento_mais_usado = self._equipamento_mais_usado(registros)

        return FrotaAgriculturaResumo(
            horas_totais=horas_totais,
            km_totais=km_totais,
            custo_estimado_total=custo_total,
            custo_hora_estimado=self._calcular_custo_unitario(registros, "HORA"),
            custo_km_estimado=self._calcular_custo_unitario(registros, "KM"),
            operacao_mais_cara=por_operacao[0].tipo_operacao if por_operacao and por_operacao[0].custo_estimado_total is not None else None,
            operacao_mais_cara_custo=por_operacao[0].custo_estimado_total if por_operacao else None,
            talhao_mais_caro=por_talhao[0].talhao_nome if por_talhao and por_talhao[0].custo_estimado_total is not None else None,
            talhao_mais_caro_custo=por_talhao[0].custo_estimado_total if por_talhao else None,
            equipamento_mais_usado=equipamento_mais_usado[0] if equipamento_mais_usado else None,
            equipamento_mais_usado_valor=equipamento_mais_usado[1] if equipamento_mais_usado else None,
        )

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
