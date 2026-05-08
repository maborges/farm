from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import EntityNotFoundError
from operacional.models.abastecimento import Abastecimento
from operacional.schemas.frota_consumo import (
    FrotaConsumoAlerta,
    FrotaConsumoEquipamentoDetalhe,
    FrotaConsumoEquipamentoItem,
    FrotaConsumoEquipamentoResponse,
    FrotaConsumoHistoricoItem,
    FrotaConsumoRankingItem,
    FrotaConsumoRankingResponse,
    FrotaConsumoResponse,
    FrotaConsumoResumo,
)
from operacional.services.frota_dashboard_service import FrotaDashboardService


@dataclass
class _MetricasEquipamento:
    litros_totais: float
    custo_total: float
    custo_medio_litro: float | None
    consumo_medio_l_h: float | None
    consumo_medio_km_l: float | None
    custo_por_hora: float | None
    custo_por_km: float | None
    variacao_media_frota_percent: float | None
    variacao_media_historica_percent: float | None
    eficiencia_score: float | None
    metrica_principal: str
    ultimo_abastecimento: Abastecimento | None
    total_abastecimentos: int
    consumo_atual_historico: float | None


@dataclass
class _ContextoEquipamento:
    equipamento: Equipamento
    abastecimentos: list[Abastecimento]
    metricas: _MetricasEquipamento
    alertas: list[FrotaConsumoAlerta]


class FrotaConsumoService(FrotaDashboardService):
    RANKING_LIMIT = 10
    INTERVALO_CURTO_DIAS = 2
    INTERVALO_CURTO_HORAS = 5.0
    INTERVALO_CURTO_KM = 50.0
    DESVIO_ALERTA_PERCENT = 20.0

    async def obter_resumo_consumo(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaConsumoResponse:
        agora = datetime.now(timezone.utc)
        contextos = await self._montar_contextos(unidade_produtiva_id, agora)
        historico = self._serializar_historico_frota(contextos)
        ranking = self._serializar_ranking(contextos)
        alertas = self._ordenar_alertas([alerta for contexto in contextos for alerta in contexto.alertas])

        return FrotaConsumoResponse(
            resumo=self._montar_resumo(contextos, alertas),
            equipamentos=[self._serializar_item(contexto) for contexto in self._ordenar_contextos(contextos)],
            ranking_eficiencia=ranking,
            alertas=alertas,
            historico_abastecimentos=historico,
            gerado_em=agora,
        )

    async def obter_consumo_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaConsumoEquipamentoResponse:
        agora = datetime.now(timezone.utc)
        contextos = await self._montar_contextos(unidade_produtiva_id, agora)
        contexto = next((item for item in contextos if item.equipamento.id == equipamento_id), None)
        if not contexto:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")

        return FrotaConsumoEquipamentoResponse(
            equipamento=FrotaConsumoEquipamentoDetalhe(
                equipamento_id=contexto.equipamento.id,
                equipamento_nome=contexto.equipamento.nome,
                equipamento_tipo=contexto.equipamento.tipo,
                equipamento_status=self._normalizar_status(contexto.equipamento.status),
                litros_totais=contexto.metricas.litros_totais,
                custo_total_combustivel=contexto.metricas.custo_total,
                custo_medio_litro=contexto.metricas.custo_medio_litro,
                consumo_medio_l_h=contexto.metricas.consumo_medio_l_h,
                consumo_medio_km_l=contexto.metricas.consumo_medio_km_l,
                custo_por_hora=contexto.metricas.custo_por_hora,
                custo_por_km=contexto.metricas.custo_por_km,
                variacao_media_frota_percent=contexto.metricas.variacao_media_frota_percent,
                variacao_media_historica_percent=contexto.metricas.variacao_media_historica_percent,
                eficiencia_score=contexto.metricas.eficiencia_score,
                metrica_principal=contexto.metricas.metrica_principal,  # type: ignore[arg-type]
                total_abastecimentos=contexto.metricas.total_abastecimentos,
                ultimo_abastecimento_em=contexto.metricas.ultimo_abastecimento.data if contexto.metricas.ultimo_abastecimento else None,
                dias_sem_abastecimento=self._dias_sem_abastecimento(contexto.metricas.ultimo_abastecimento, agora),
            ),
            historico_abastecimentos=self._serializar_historico(contexto.abastecimentos),
            alertas=self._ordenar_alertas(contexto.alertas),
            gerado_em=agora,
        )

    async def obter_ranking(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaConsumoRankingResponse:
        agora = datetime.now(timezone.utc)
        contextos = await self._montar_contextos(unidade_produtiva_id, agora)
        return FrotaConsumoRankingResponse(
            ranking=self._serializar_ranking(contextos),
            gerado_em=agora,
        )

    async def _montar_contextos(
        self,
        unidade_produtiva_id: uuid.UUID | None,
        agora: datetime,
    ) -> list[_ContextoEquipamento]:
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        if not equipamentos:
            return []

        equipamento_ids = [equipamento.id for equipamento in equipamentos]
        abastecimentos = await self._listar_abastecimentos(equipamento_ids)
        abastecimentos_por_equipamento: dict[uuid.UUID, list[Abastecimento]] = defaultdict(list)
        for item in reversed(abastecimentos):
            abastecimentos_por_equipamento[item.equipamento_id].append(item)

        pre_metricas: dict[uuid.UUID, dict[str, float | None | str | Abastecimento | int]] = {}
        hora_values: list[float] = []
        km_values: list[float] = []
        custo_h_values: list[float] = []
        custo_km_values: list[float] = []
        historico_h_values: list[float] = []
        historico_km_values: list[float] = []

        for equipamento in equipamentos:
            metricas = self._calcular_metricas_base(equipamento, abastecimentos_por_equipamento[equipamento.id], agora)
            pre_metricas[equipamento.id] = metricas
            if metricas["consumo_medio_l_h"] is not None:
                hora_values.append(float(metricas["consumo_medio_l_h"]))
            if metricas["consumo_medio_km_l"] is not None:
                km_values.append(float(metricas["consumo_medio_km_l"]))
            if metricas["custo_por_hora"] is not None:
                custo_h_values.append(float(metricas["custo_por_hora"]))
            if metricas["custo_por_km"] is not None:
                custo_km_values.append(float(metricas["custo_por_km"]))
            if metricas["variacao_media_historica_percent"] is not None:
                principal = str(metricas["metrica_principal"])
                if principal == "HORIMETRO":
                    historico_h_values.append(float(metricas["variacao_media_historica_percent"]))
                if principal == "KM":
                    historico_km_values.append(float(metricas["variacao_media_historica_percent"]))

        media_hora = statistics.mean(hora_values) if hora_values else None
        media_km = statistics.mean(km_values) if km_values else None
        media_custo_hora = statistics.mean(custo_h_values) if custo_h_values else None
        media_custo_km = statistics.mean(custo_km_values) if custo_km_values else None

        contextos: list[_ContextoEquipamento] = []
        for equipamento in equipamentos:
            base = pre_metricas[equipamento.id]
            metricas = self._finalizar_metricas(
                equipamento=equipamento,
                base=base,
                media_hora=media_hora,
                media_km=media_km,
                media_custo_hora=media_custo_hora,
                media_custo_km=media_custo_km,
            )
            alertas = self._montar_alertas(
                equipamento=equipamento,
                abastecimentos=abastecimentos_por_equipamento[equipamento.id],
                metricas=metricas,
                media_hora=media_hora,
                media_km=media_km,
                media_custo_hora=media_custo_hora,
                media_custo_km=media_custo_km,
                agora=agora,
            )
            contextos.append(
                _ContextoEquipamento(
                    equipamento=equipamento,
                    abastecimentos=abastecimentos_por_equipamento[equipamento.id],
                    metricas=metricas,
                    alertas=alertas,
                )
            )
        return contextos

    def _calcular_metricas_base(
        self,
        equipamento: Equipamento,
        abastecimentos: list[Abastecimento],
        agora: datetime,
    ) -> dict[str, float | None | str | Abastecimento | int]:
        litros_totais = round(sum(float(item.litros or 0.0) for item in abastecimentos), 2)
        custo_total = round(sum(float(item.custo_total or 0.0) for item in abastecimentos), 2)
        custo_medio_litro = round(custo_total / litros_totais, 2) if litros_totais > 0 else None

        leituras_hora = [item for item in abastecimentos if item.horimetro_na_data is not None]
        consumo_medio_l_h, custo_por_hora, historico_hora = self._calcular_metricas_hora(leituras_hora, custo_total, litros_totais)

        leituras_km = [item for item in abastecimentos if item.km_na_data is not None]
        consumo_medio_km_l, custo_por_km, historico_km = self._calcular_metricas_km(leituras_km, custo_total, litros_totais)

        metrica_principal = self._resolver_metrica_principal(equipamento, consumo_medio_l_h, consumo_medio_km_l)
        consumo_atual_historico = historico_hora["atual"] if metrica_principal == "HORIMETRO" else historico_km["atual"]
        variacao_historica = None
        if metrica_principal == "HORIMETRO":
            variacao_historica = self._calcular_variacao_percentual(consumo_atual_historico, historico_hora["media"])
        elif metrica_principal == "KM":
            variacao_historica = self._calcular_variacao_percentual(consumo_atual_historico, historico_km["media"])

        ultimo_abastecimento = abastecimentos[-1] if abastecimentos else None
        return {
            "litros_totais": litros_totais,
            "custo_total": custo_total,
            "custo_medio_litro": custo_medio_litro,
            "consumo_medio_l_h": consumo_medio_l_h,
            "consumo_medio_km_l": consumo_medio_km_l,
            "custo_por_hora": custo_por_hora,
            "custo_por_km": custo_por_km,
            "variacao_media_historica_percent": variacao_historica,
            "metrica_principal": metrica_principal,
            "ultimo_abastecimento": ultimo_abastecimento,
            "total_abastecimentos": len(abastecimentos),
            "consumo_atual_historico": consumo_atual_historico,
        }

    @staticmethod
    def _calcular_metricas_hora(
        abastecimentos: list[Abastecimento],
        custo_total: float,
        litros_totais: float,
    ) -> tuple[float | None, float | None, dict[str, float | None]]:
        if len(abastecimentos) < 2:
            return None, None, {"atual": None, "media": None}
        delta_horas = float((abastecimentos[-1].horimetro_na_data or 0.0) - (abastecimentos[0].horimetro_na_data or 0.0))
        if delta_horas <= 0:
            return None, None, {"atual": None, "media": None}

        consumo_medio_l_h = round(litros_totais / delta_horas, 2) if litros_totais > 0 else None
        custo_por_hora = round(custo_total / delta_horas, 2) if custo_total > 0 else None
        intervalos = []
        for anterior, atual in zip(abastecimentos, abastecimentos[1:]):
            delta = float((atual.horimetro_na_data or 0.0) - (anterior.horimetro_na_data or 0.0))
            if delta > 0 and float(atual.litros or 0.0) > 0:
                intervalos.append(round(float(atual.litros or 0.0) / delta, 4))
        atual_intervalo = intervalos[-1] if intervalos else None
        media_intervalos = round(statistics.mean(intervalos), 4) if intervalos else None
        return consumo_medio_l_h, custo_por_hora, {"atual": atual_intervalo, "media": media_intervalos}

    @staticmethod
    def _calcular_metricas_km(
        abastecimentos: list[Abastecimento],
        custo_total: float,
        litros_totais: float,
    ) -> tuple[float | None, float | None, dict[str, float | None]]:
        if len(abastecimentos) < 2:
            return None, None, {"atual": None, "media": None}
        delta_km = float((abastecimentos[-1].km_na_data or 0.0) - (abastecimentos[0].km_na_data or 0.0))
        if delta_km <= 0 or litros_totais <= 0:
            return None, None, {"atual": None, "media": None}

        consumo_medio_km_l = round(delta_km / litros_totais, 2)
        custo_por_km = round(custo_total / delta_km, 2) if custo_total > 0 else None
        intervalos = []
        for anterior, atual in zip(abastecimentos, abastecimentos[1:]):
            delta = float((atual.km_na_data or 0.0) - (anterior.km_na_data or 0.0))
            litros = float(atual.litros or 0.0)
            if delta > 0 and litros > 0:
                intervalos.append(round(delta / litros, 4))
        atual_intervalo = intervalos[-1] if intervalos else None
        media_intervalos = round(statistics.mean(intervalos), 4) if intervalos else None
        return consumo_medio_km_l, custo_por_km, {"atual": atual_intervalo, "media": media_intervalos}

    def _finalizar_metricas(
        self,
        equipamento: Equipamento,
        base: dict[str, float | None | str | Abastecimento | int],
        media_hora: float | None,
        media_km: float | None,
        media_custo_hora: float | None,
        media_custo_km: float | None,
    ) -> _MetricasEquipamento:
        metrica_principal = str(base["metrica_principal"])
        variacao_frota = None
        eficiencia_score = None
        if metrica_principal == "HORIMETRO":
            consumo = self._as_float(base["consumo_medio_l_h"])
            variacao_frota = self._calcular_variacao_percentual(consumo, media_hora)
            if consumo and media_hora and consumo > 0:
                eficiencia_score = round((media_hora / consumo) * 100, 2)
        elif metrica_principal == "KM":
            consumo = self._as_float(base["consumo_medio_km_l"])
            variacao_frota = self._calcular_variacao_percentual(consumo, media_km)
            if consumo and media_km and media_km > 0:
                eficiencia_score = round((consumo / media_km) * 100, 2)

        return _MetricasEquipamento(
            litros_totais=float(base["litros_totais"] or 0.0),
            custo_total=float(base["custo_total"] or 0.0),
            custo_medio_litro=self._as_float(base["custo_medio_litro"]),
            consumo_medio_l_h=self._as_float(base["consumo_medio_l_h"]),
            consumo_medio_km_l=self._as_float(base["consumo_medio_km_l"]),
            custo_por_hora=self._as_float(base["custo_por_hora"]),
            custo_por_km=self._as_float(base["custo_por_km"]),
            variacao_media_frota_percent=variacao_frota,
            variacao_media_historica_percent=self._as_float(base["variacao_media_historica_percent"]),
            eficiencia_score=eficiencia_score,
            metrica_principal=metrica_principal,
            ultimo_abastecimento=base["ultimo_abastecimento"] if isinstance(base["ultimo_abastecimento"], Abastecimento) else None,
            total_abastecimentos=int(base["total_abastecimentos"] or 0),
            consumo_atual_historico=self._as_float(base["consumo_atual_historico"]),
        )

    def _montar_alertas(
        self,
        equipamento: Equipamento,
        abastecimentos: list[Abastecimento],
        metricas: _MetricasEquipamento,
        media_hora: float | None,
        media_km: float | None,
        media_custo_hora: float | None,
        media_custo_km: float | None,
        agora: datetime,
    ) -> list[FrotaConsumoAlerta]:
        alertas: list[FrotaConsumoAlerta] = []
        ultimo = metricas.ultimo_abastecimento
        dias_sem_abastecimento = self._dias_sem_abastecimento(ultimo, agora)

        if self._tem_risco_sem_abastecimento(equipamento, dias_sem_abastecimento):
            alertas.append(
                FrotaConsumoAlerta(
                    tipo="SEM_ABASTECIMENTO_RECENTE",
                    titulo="Sem abastecimento recente",
                    severidade="warning",
                    equipamento_id=equipamento.id,
                    equipamento_nome=equipamento.nome,
                    detalhe=(
                        f"Equipamento sem abastecimento há {dias_sem_abastecimento} dias."
                        if dias_sem_abastecimento is not None
                        else "Equipamento sem histórico de abastecimento."
                    ),
                    data_referencia=ultimo.data if ultimo else None,
                    dias_desde_evento=dias_sem_abastecimento,
                )
            )

        if metricas.metrica_principal == "HORIMETRO" and metricas.consumo_medio_l_h and media_hora:
            if metricas.consumo_medio_l_h > media_hora * 1.2:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="CONSUMO_ACIMA_MEDIA",
                        titulo="Consumo por hora acima da média",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"Consumo médio de {metricas.consumo_medio_l_h:.2f} L/h acima da média da frota.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )
            if metricas.custo_por_hora and media_custo_hora and metricas.custo_por_hora > media_custo_hora * 1.2:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="CUSTO_ACIMA_MEDIA",
                        titulo="Custo por hora acima da média",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"Custo de R$ {metricas.custo_por_hora:.2f}/h acima da média da frota.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )
        elif metricas.metrica_principal == "KM" and metricas.consumo_medio_km_l and media_km:
            if metricas.consumo_medio_km_l < media_km * 0.8:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="CONSUMO_ACIMA_MEDIA",
                        titulo="Eficiência por km abaixo da média",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"Eficiência média de {metricas.consumo_medio_km_l:.2f} km/L abaixo da média da frota.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )
            if metricas.custo_por_km and media_custo_km and metricas.custo_por_km > media_custo_km * 1.2:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="CUSTO_ACIMA_MEDIA",
                        titulo="Custo por km acima da média",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"Custo de R$ {metricas.custo_por_km:.2f}/km acima da média da frota.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )

        if metricas.variacao_media_historica_percent is not None:
            if metricas.metrica_principal == "HORIMETRO" and metricas.variacao_media_historica_percent > self.DESVIO_ALERTA_PERCENT:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="DESVIO_MEDIA_HISTORICA",
                        titulo="Desvio da média histórica",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe="Consumo por hora acima da média histórica recente do equipamento.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )
            elif metricas.metrica_principal == "KM" and metricas.variacao_media_historica_percent < -self.DESVIO_ALERTA_PERCENT:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="DESVIO_MEDIA_HISTORICA",
                        titulo="Desvio da média histórica",
                        severidade="warning",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe="Eficiência por km abaixo da média histórica recente do equipamento.",
                        data_referencia=ultimo.data if ultimo else None,
                    )
                )

        for alerta in self._alertas_sequenciais(equipamento, abastecimentos):
            alertas.append(alerta)

        return alertas

    def _alertas_sequenciais(
        self,
        equipamento: Equipamento,
        abastecimentos: list[Abastecimento],
    ) -> list[FrotaConsumoAlerta]:
        alertas: list[FrotaConsumoAlerta] = []
        for anterior, atual in zip(abastecimentos, abastecimentos[1:]):
            if (
                anterior.horimetro_na_data is not None
                and atual.horimetro_na_data is not None
                and atual.horimetro_na_data < anterior.horimetro_na_data
            ):
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="LEITURA_MENOR_ANTERIOR",
                        titulo="Horímetro menor que a leitura anterior",
                        severidade="danger",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe="Há abastecimento com leitura de horímetro regressiva.",
                        data_referencia=atual.data,
                    )
                )
                break
            if anterior.km_na_data is not None and atual.km_na_data is not None and atual.km_na_data < anterior.km_na_data:
                alertas.append(
                    FrotaConsumoAlerta(
                        tipo="LEITURA_MENOR_ANTERIOR",
                        titulo="KM menor que a leitura anterior",
                        severidade="danger",
                        equipamento_id=equipamento.id,
                        equipamento_nome=equipamento.nome,
                        detalhe="Há abastecimento com leitura de km regressiva.",
                        data_referencia=atual.data,
                    )
                )
                break

            delta_dias = max((atual.data - anterior.data).days, 0)
            delta_horas = (
                float((atual.horimetro_na_data or 0.0) - (anterior.horimetro_na_data or 0.0))
                if anterior.horimetro_na_data is not None and atual.horimetro_na_data is not None
                else None
            )
            delta_km = (
                float((atual.km_na_data or 0.0) - (anterior.km_na_data or 0.0))
                if anterior.km_na_data is not None and atual.km_na_data is not None
                else None
            )
            if delta_dias <= self.INTERVALO_CURTO_DIAS:
                hora_curta = delta_horas is not None and 0 <= delta_horas <= self.INTERVALO_CURTO_HORAS
                km_curto = delta_km is not None and 0 <= delta_km <= self.INTERVALO_CURTO_KM
                if hora_curta or km_curto:
                    alertas.append(
                        FrotaConsumoAlerta(
                            tipo="INTERVALO_CURTO",
                            titulo="Abastecimento em intervalo muito curto",
                            severidade="warning",
                            equipamento_id=equipamento.id,
                            equipamento_nome=equipamento.nome,
                            detalhe="Há abastecimentos muito próximos entre si para a leitura registrada.",
                            data_referencia=atual.data,
                            dias_desde_evento=delta_dias,
                        )
                    )
                    break
        return alertas

    def _montar_resumo(
        self,
        contextos: list[_ContextoEquipamento],
        alertas: list[FrotaConsumoAlerta],
    ) -> FrotaConsumoResumo:
        litros_totais = round(sum(contexto.metricas.litros_totais for contexto in contextos), 2)
        custo_total = round(sum(contexto.metricas.custo_total for contexto in contextos), 2)
        custo_medio_litro = round(custo_total / litros_totais, 2) if litros_totais > 0 else None
        medias_hora = [item.metricas.consumo_medio_l_h for item in contextos if item.metricas.consumo_medio_l_h is not None]
        medias_km = [item.metricas.consumo_medio_km_l for item in contextos if item.metricas.consumo_medio_km_l is not None]
        equipamentos_com_anomalia = sum(1 for contexto in contextos if contexto.alertas)
        return FrotaConsumoResumo(
            litros_totais=litros_totais,
            custo_total_combustivel=custo_total,
            custo_medio_litro=custo_medio_litro,
            consumo_medio_l_h=round(statistics.mean(medias_hora), 2) if medias_hora else None,
            consumo_medio_km_l=round(statistics.mean(medias_km), 2) if medias_km else None,
            equipamentos_com_anomalia=equipamentos_com_anomalia,
            total_alertas=len(alertas),
        )

    def _serializar_item(self, contexto: _ContextoEquipamento) -> FrotaConsumoEquipamentoItem:
        return FrotaConsumoEquipamentoItem(
            equipamento_id=contexto.equipamento.id,
            equipamento_nome=contexto.equipamento.nome,
            equipamento_tipo=contexto.equipamento.tipo,
            equipamento_status=self._normalizar_status(contexto.equipamento.status),
            unidade_produtiva_id=contexto.equipamento.unidade_produtiva_id,
            total_abastecimentos=contexto.metricas.total_abastecimentos,
            litros_totais=contexto.metricas.litros_totais,
            custo_total_combustivel=contexto.metricas.custo_total,
            custo_medio_litro=contexto.metricas.custo_medio_litro,
            consumo_medio_l_h=contexto.metricas.consumo_medio_l_h,
            consumo_medio_km_l=contexto.metricas.consumo_medio_km_l,
            custo_por_hora=contexto.metricas.custo_por_hora,
            custo_por_km=contexto.metricas.custo_por_km,
            variacao_media_frota_percent=contexto.metricas.variacao_media_frota_percent,
            variacao_media_historica_percent=contexto.metricas.variacao_media_historica_percent,
            eficiencia_score=contexto.metricas.eficiencia_score,
            metrica_principal=contexto.metricas.metrica_principal,  # type: ignore[arg-type]
            ultimo_abastecimento_em=contexto.metricas.ultimo_abastecimento.data if contexto.metricas.ultimo_abastecimento else None,
            dias_sem_abastecimento=None if not contexto.metricas.ultimo_abastecimento else self._dias_sem_abastecimento(contexto.metricas.ultimo_abastecimento, datetime.now(timezone.utc)),
            alertas_total=len(contexto.alertas),
        )

    def _serializar_ranking(self, contextos: list[_ContextoEquipamento]) -> list[FrotaConsumoRankingItem]:
        ranking = [
            FrotaConsumoRankingItem(
                equipamento_id=contexto.equipamento.id,
                equipamento_nome=contexto.equipamento.nome,
                equipamento_tipo=contexto.equipamento.tipo,
                metrica_principal=contexto.metricas.metrica_principal,  # type: ignore[arg-type]
                eficiencia_score=contexto.metricas.eficiencia_score,
                consumo_medio_l_h=contexto.metricas.consumo_medio_l_h,
                consumo_medio_km_l=contexto.metricas.consumo_medio_km_l,
                custo_por_hora=contexto.metricas.custo_por_hora,
                custo_por_km=contexto.metricas.custo_por_km,
                variacao_media_frota_percent=contexto.metricas.variacao_media_frota_percent,
            )
            for contexto in contextos
            if contexto.metricas.eficiencia_score is not None
        ]
        return sorted(
            ranking,
            key=lambda item: (item.eficiencia_score or 0.0, item.equipamento_nome),
            reverse=True,
        )[: self.RANKING_LIMIT]

    def _serializar_historico_frota(self, contextos: list[_ContextoEquipamento]) -> list[FrotaConsumoHistoricoItem]:
        historico = []
        for contexto in contextos:
            for item in contexto.abastecimentos[-10:]:
                historico.append(self._serializar_historico_item(item))
        return sorted(historico, key=lambda item: item.data, reverse=True)[:10]

    def _serializar_historico(self, abastecimentos: list[Abastecimento]) -> list[FrotaConsumoHistoricoItem]:
        return [self._serializar_historico_item(item) for item in reversed(abastecimentos[-20:])]

    @staticmethod
    def _serializar_historico_item(item: Abastecimento) -> FrotaConsumoHistoricoItem:
        return FrotaConsumoHistoricoItem(
            id=item.id,
            data=item.data,
            litros=float(item.litros or 0.0),
            custo_total=float(item.custo_total or 0.0),
            preco_litro=float(item.preco_litro or 0.0),
            tipo_combustivel=item.tipo_combustivel,
            tanque_cheio=bool(item.tanque_cheio),
            horimetro_na_data=item.horimetro_na_data,
            km_na_data=item.km_na_data,
            local=item.local,
            observacoes=item.observacoes,
        )

    @staticmethod
    def _ordenar_alertas(alertas: list[FrotaConsumoAlerta]) -> list[FrotaConsumoAlerta]:
        return sorted(
            alertas,
            key=lambda item: (
                1 if item.severidade == "danger" else 0,
                item.dias_desde_evento or 0,
                item.equipamento_nome,
            ),
            reverse=True,
        )

    @staticmethod
    def _ordenar_contextos(contextos: list[_ContextoEquipamento]) -> list[_ContextoEquipamento]:
        return sorted(
            contextos,
            key=lambda item: (
                len(item.alertas),
                item.metricas.eficiencia_score or 0.0,
                item.equipamento.nome,
            ),
            reverse=True,
        )

    @staticmethod
    def _calcular_variacao_percentual(atual: float | None, media: float | None) -> float | None:
        if atual is None or media is None or media == 0:
            return None
        return round(((atual - media) / media) * 100, 2)

    @staticmethod
    def _resolver_metrica_principal(
        equipamento: Equipamento,
        consumo_hora: float | None,
        consumo_km: float | None,
    ) -> str:
        if consumo_hora is not None and consumo_km is not None:
            if equipamento.tipo == "VEICULO":
                return "KM"
            return "HORIMETRO"
        if consumo_hora is not None:
            return "HORIMETRO"
        if consumo_km is not None:
            return "KM"
        if equipamento.horimetro_atual > 0 and equipamento.km_atual > 0:
            return "AMBOS"
        return "INDISPONIVEL"

    @staticmethod
    def _as_float(value: object) -> float | None:
        if value is None:
            return None
        return float(value)
