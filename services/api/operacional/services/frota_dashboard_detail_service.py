from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import EntityNotFoundError
from operacional.models.abastecimento import Abastecimento
from operacional.models.documento_equipamento import DocumentoEquipamento
from operacional.models.frota import JornadaEquipamento, OrdemServico, PlanoManutencao, RegistroManutencao
from operacional.schemas.frota_dashboard_detail import (
    FrotaDashboardDetalheAbastecimento,
    FrotaDashboardDetalheAlerta,
    FrotaDashboardDetalheCabecalho,
    FrotaDashboardDetalheDocumento,
    FrotaDashboardDetalheIndicadores,
    FrotaDashboardDetalheJornada,
    FrotaDashboardDetalheOrdemServico,
    FrotaDashboardDetalhePlanoManutencao,
    FrotaDashboardDetalheRegistroManutencao,
    FrotaDashboardDetalheResponse,
)
from operacional.services.frota_dashboard_service import FrotaDashboardService


class FrotaDashboardDetailService(FrotaDashboardService):
    DOCUMENTO_PROXIMO_DIAS = 30
    HISTORICO_LIMIT = 10

    async def obter_detalhe_equipamento(
        self,
        equipamento_id: uuid.UUID,
        periodo_dias: int | None = None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDashboardDetalheResponse:
        agora = datetime.now(timezone.utc)
        hoje = agora.date()
        data_corte = agora - timedelta(days=periodo_dias) if periodo_dias else None

        equipamento = await self._obter_equipamento(equipamento_id, unidade_produtiva_id)
        abastecimentos = await self._listar_abastecimentos([equipamento.id])
        ordens_servico = await self._listar_ordens_servico([equipamento.id])
        registros_manutencao = await self._listar_registros_manutencao([equipamento.id])
        planos = await self._listar_planos([equipamento.id])
        documentos = await self._listar_documentos([equipamento.id])
        jornadas = await self._listar_jornadas([equipamento.id])

        abastecimentos_filtrados = self._filtrar_por_data(
            abastecimentos,
            data_corte,
            lambda item: item.data,
        )
        ordens_filtradas = self._filtrar_por_data(
            ordens_servico,
            data_corte,
            lambda item: item.data_abertura,
        )
        registros_filtrados = self._filtrar_por_data(
            registros_manutencao,
            data_corte,
            lambda item: item.data_realizacao,
        )
        jornadas_filtradas = self._filtrar_por_data(
            jornadas,
            data_corte,
            lambda item: item.data_inicio,
        )

        manutencao_status = self._calcular_status_manutencao(equipamento, planos)
        ultimo_abastecimento = self._obter_ultimo_abastecimento(abastecimentos)
        dias_sem_abastecimento = self._dias_sem_abastecimento(ultimo_abastecimento, agora)

        custo_total_abastecimento = round(
            sum(float(item.custo_total or 0.0) for item in abastecimentos_filtrados),
            2,
        )
        custo_total_manutencao = round(
            sum(float(item.custo_total or 0.0) for item in registros_filtrados),
            2,
        )
        custo_total_geral = round(custo_total_abastecimento + custo_total_manutencao, 2)
        horas_trabalhadas_periodo = round(
            sum(float(self._calcular_delta(item.horimetro_inicial, item.horimetro_final) or 0.0) for item in jornadas_filtradas if item.status == "FINALIZADA"),
            2,
        )
        km_trabalhados_periodo = round(
            sum(float(self._calcular_delta(item.km_inicial, item.km_final) or 0.0) for item in jornadas_filtradas if item.status == "FINALIZADA"),
            2,
        )

        total_os_abertas = sum(1 for item in ordens_filtradas if item.status in {"ABERTA", "EM_EXECUCAO"})
        total_os_concluidas = sum(1 for item in ordens_filtradas if item.status == "CONCLUIDA")

        alertas = self._montar_alertas(
            equipamento=equipamento,
            ordens_servico=ordens_servico,
            documentos=documentos,
            manutencao_status=manutencao_status.status,
            dias_sem_abastecimento=dias_sem_abastecimento,
            agora=agora,
            custo_total_geral=custo_total_geral,
            periodo_dias=periodo_dias,
        )
        documentos_alerta = self._montar_documentos_alerta(documentos, hoje)
        planos_detalhe = self._montar_planos_detalhe(equipamento, planos)

        return FrotaDashboardDetalheResponse(
            equipamento=FrotaDashboardDetalheCabecalho(
                equipamento_id=equipamento.id,
                nome=equipamento.nome,
                tipo=equipamento.tipo,
                status=self._normalizar_status(equipamento.status),
                marca=equipamento.marca,
                modelo=equipamento.modelo,
                unidade_produtiva_id=equipamento.unidade_produtiva_id,
                placa=equipamento.placa,
                numero_serie=equipamento.numero_serie,
                patrimonio=equipamento.patrimonio,
                combustivel=equipamento.combustivel,
                capacidade_tanque_l=equipamento.capacidade_tanque_l,
                potencia_cv=equipamento.potencia_cv,
                horimetro_atual=equipamento.horimetro_atual,
                km_atual=equipamento.km_atual,
            ),
            indicadores=FrotaDashboardDetalheIndicadores(
                periodo_dias_aplicado=periodo_dias,
                total_os_abertas=total_os_abertas,
                total_os_concluidas=total_os_concluidas,
                horas_trabalhadas_periodo=horas_trabalhadas_periodo,
                km_trabalhados_periodo=km_trabalhados_periodo,
                custo_total_manutencao=custo_total_manutencao,
                custo_total_abastecimento=custo_total_abastecimento,
                custo_total_geral=custo_total_geral,
                custo_por_hora=self._calcular_custo_por_hora(custo_total_geral, equipamento.horimetro_atual),
                custo_por_km=self._calcular_custo_por_km(custo_total_geral, equipamento.km_atual),
                consumo_medio_km_l=self._calcular_consumo_medio_km_l(abastecimentos_filtrados),
                consumo_medio_l_h=self._calcular_consumo_medio_l_h(abastecimentos_filtrados),
                dias_sem_abastecimento=dias_sem_abastecimento,
                manutencao_status=manutencao_status.status,  # type: ignore[arg-type]
            ),
            ultimos_abastecimentos=[
                FrotaDashboardDetalheAbastecimento(
                    id=item.id,
                    data=item.data,
                    tipo_combustivel=item.tipo_combustivel,
                    litros=float(item.litros or 0.0),
                    preco_litro=float(item.preco_litro or 0.0),
                    custo_total=float(item.custo_total or 0.0),
                    local=item.local,
                    tanque_cheio=bool(item.tanque_cheio),
                    horimetro_na_data=item.horimetro_na_data,
                    km_na_data=item.km_na_data,
                    nota_fiscal=item.nota_fiscal,
                    observacoes=item.observacoes,
                )
                for item in abastecimentos_filtrados[: self.HISTORICO_LIMIT]
            ],
            ultimas_ordens_servico=[
                FrotaDashboardDetalheOrdemServico(
                    id=item.id,
                    numero_os=item.numero_os,
                    tipo=item.tipo,
                    status=item.status,
                    descricao_problema=item.descricao_problema,
                    diagnostico_tecnico=item.diagnostico_tecnico,
                    data_abertura=item.data_abertura,
                    data_conclusao=item.data_conclusao,
                    horimetro_na_abertura=item.horimetro_na_abertura,
                    km_na_abertura=item.km_na_abertura,
                    tecnico_responsavel=item.tecnico_responsavel,
                    custo_total_pecas=float(item.custo_total_pecas or 0.0),
                    custo_mao_obra=float(item.custo_mao_obra or 0.0),
                    custo_total_os=round(float(item.custo_total_pecas or 0.0) + float(item.custo_mao_obra or 0.0), 2),
                )
                for item in ordens_filtradas[: self.HISTORICO_LIMIT]
            ],
            ultimos_registros_manutencao=[
                FrotaDashboardDetalheRegistroManutencao(
                    id=item.id,
                    os_id=item.os_id,
                    data_realizacao=item.data_realizacao,
                    tipo=item.tipo,
                    descricao=item.descricao,
                    custo_total=float(item.custo_total or 0.0),
                    horimetro_na_data=item.horimetro_na_data,
                    km_na_data=item.km_na_data,
                    tecnico_responsavel=item.tecnico_responsavel,
                )
                for item in registros_filtrados[: self.HISTORICO_LIMIT]
            ],
            ultimas_jornadas=await self._montar_jornadas_detalhe(
                equipamento=equipamento,
                jornadas=jornadas_filtradas[: self.HISTORICO_LIMIT],
                unidade_produtiva_id=unidade_produtiva_id,
                custo_total_geral=custo_total_geral,
            ),
            documentos_alerta=documentos_alerta,
            planos_manutencao=planos_detalhe,
            alertas=alertas,
            recomendacao_operacional=self._gerar_recomendacao(alertas, documentos_alerta, planos_detalhe),
            gerado_em=agora,
        )

    async def _obter_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> Equipamento:
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        for equipamento in equipamentos:
            if equipamento.id == equipamento_id:
                return equipamento
        raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")

    @staticmethod
    def _filtrar_por_data(items, data_corte: datetime | None, attr_getter):
        if data_corte is None:
            return items
        return [item for item in items if attr_getter(item) >= data_corte]

    def _calcular_consumo_medio_km_l(
        self,
        abastecimentos: list[Abastecimento],
    ) -> float | None:
        leituras = [item for item in reversed(abastecimentos) if item.km_na_data is not None]
        if len(leituras) < 2:
            return None
        delta_km = float((leituras[-1].km_na_data or 0.0) - (leituras[0].km_na_data or 0.0))
        total_litros = sum(float(item.litros or 0.0) for item in leituras)
        if delta_km <= 0 or total_litros <= 0:
            return None
        return round(delta_km / total_litros, 2)

    def _calcular_consumo_medio_l_h(
        self,
        abastecimentos: list[Abastecimento],
    ) -> float | None:
        leituras = [item for item in reversed(abastecimentos) if item.horimetro_na_data is not None]
        if len(leituras) < 2:
            return None
        delta_horas = float((leituras[-1].horimetro_na_data or 0.0) - (leituras[0].horimetro_na_data or 0.0))
        total_litros = sum(float(item.litros or 0.0) for item in leituras)
        if delta_horas <= 0 or total_litros <= 0:
            return None
        return round(total_litros / delta_horas, 2)

    def _montar_documentos_alerta(
        self,
        documentos: list[DocumentoEquipamento],
        hoje: date,
    ) -> list[FrotaDashboardDetalheDocumento]:
        alerta_docs: list[FrotaDashboardDetalheDocumento] = []
        limite = hoje + timedelta(days=self.DOCUMENTO_PROXIMO_DIAS)

        for item in documentos:
            if item.data_vencimento is None:
                continue
            if item.data_vencimento < hoje:
                status = "VENCIDO"
            elif item.data_vencimento <= limite:
                status = "PROXIMO"
            else:
                continue

            dias_para_vencimento = (item.data_vencimento - hoje).days
            alerta_docs.append(
                FrotaDashboardDetalheDocumento(
                    id=item.id,
                    tipo=item.tipo,
                    descricao=item.descricao,
                    numero=item.numero,
                    data_vencimento=item.data_vencimento,
                    status=status,
                    dias_para_vencimento=dias_para_vencimento,
                )
            )

        return alerta_docs

    def _montar_planos_detalhe(
        self,
        equipamento: Equipamento,
        planos: list[PlanoManutencao],
    ) -> list[FrotaDashboardDetalhePlanoManutencao]:
        resposta: list[FrotaDashboardDetalhePlanoManutencao] = []
        for plano in planos:
            restante_dias = None
            restante_horas = None
            restante_km = None
            status = "OK"

            if plano.frequencia_dias and plano.frequencia_dias > 0:
                base_data = plano.ultimo_registro_data or plano.created_at
                if base_data is not None:
                    restante_dias = int(
                        round(
                            (
                                base_data + timedelta(days=int(plano.frequencia_dias)) - datetime.now(timezone.utc)
                            ).total_seconds()
                            / 86400
                        )
                    )
                    proximidade_dias = min(
                        max(int(round(float(plano.frequencia_dias) * self.PROXIMIDADE_MANUTENCAO)), 3),
                        15,
                    )
                    if restante_dias <= 0:
                        status = "VENCIDA"
                    elif restante_dias <= proximidade_dias:
                        status = "PROXIMA"

            if plano.frequencia_horas and plano.frequencia_horas > 0:
                restante_horas = round(
                    float(plano.frequencia_horas)
                    - (float(equipamento.horimetro_atual or 0.0) - float(plano.ultimo_registro_horas or 0.0)),
                    2,
                )
                if restante_horas <= 0:
                    status = "VENCIDA"
                elif restante_horas <= float(plano.frequencia_horas) * self.PROXIMIDADE_MANUTENCAO:
                    status = "PROXIMA"

            if plano.frequencia_km and plano.frequencia_km > 0:
                restante_km = round(
                    float(plano.frequencia_km)
                    - (float(equipamento.km_atual or 0.0) - float(plano.ultimo_registro_km or 0.0)),
                    2,
                )
                if restante_km <= 0:
                    status = "VENCIDA"
                elif status != "VENCIDA" and restante_km <= float(plano.frequencia_km) * self.PROXIMIDADE_MANUTENCAO:
                    status = "PROXIMA"

            resposta.append(
                FrotaDashboardDetalhePlanoManutencao(
                    id=plano.id,
                    descricao=plano.descricao,
                    frequencia_dias=plano.frequencia_dias,
                    frequencia_horas=plano.frequencia_horas,
                    frequencia_km=plano.frequencia_km,
                    ultimo_registro_data=plano.ultimo_registro_data,
                    ultimo_registro_horas=plano.ultimo_registro_horas,
                    ultimo_registro_km=plano.ultimo_registro_km,
                    status=status,  # type: ignore[arg-type]
                    restante_dias=restante_dias,
                    restante_horas=restante_horas,
                    restante_km=restante_km,
                )
            )
        return resposta

    async def _montar_jornadas_detalhe(
        self,
        equipamento: Equipamento,
        jornadas: list[JornadaEquipamento],
        unidade_produtiva_id: uuid.UUID | None,
        custo_total_geral: float,
    ) -> list[FrotaDashboardDetalheJornada]:
        if not jornadas:
            return []
        pessoas_map = await self._listar_pessoas([item.operador_id for item in jornadas if item.operador_id])
        unidades_map = await self._listar_unidades([item.unidade_produtiva_id for item in jornadas if item.unidade_produtiva_id])
        safras_map = await self._listar_safras([item.safra_id for item in jornadas if item.safra_id])
        talhoes_map = await self._listar_talhoes([item.talhao_id for item in jornadas if item.talhao_id])
        custo_por_hora = self._calcular_custo_por_hora(custo_total_geral, equipamento.horimetro_atual)
        custo_por_km = self._calcular_custo_por_km(custo_total_geral, equipamento.km_atual)

        resposta: list[FrotaDashboardDetalheJornada] = []
        for item in jornadas:
            horas_trabalhadas = self._calcular_delta(item.horimetro_inicial, item.horimetro_final)
            km_trabalhados = self._calcular_delta(item.km_inicial, item.km_final)
            custo_estimado, metrica_custo = self._calcular_custo_estimado_jornada(
                horas_trabalhadas,
                km_trabalhados,
                custo_por_hora,
                custo_por_km,
            )
            resposta.append(
                FrotaDashboardDetalheJornada(
                    id=item.id,
                    operador_nome=pessoas_map.get(item.operador_id) if item.operador_id else None,
                    unidade_produtiva_nome=unidades_map.get(item.unidade_produtiva_id) if item.unidade_produtiva_id else None,
                    safra_nome=safras_map.get(item.safra_id) if item.safra_id else None,
                    talhao_nome=talhoes_map.get(item.talhao_id) if item.talhao_id else None,
                    tipo_operacao=item.tipo_operacao,
                    data_inicio=item.data_inicio,
                    data_fim=item.data_fim,
                    status=item.status,  # type: ignore[arg-type]
                    horimetro_inicial=item.horimetro_inicial,
                    horimetro_final=item.horimetro_final,
                    km_inicial=item.km_inicial,
                    km_final=item.km_final,
                    duracao_horas=self._calcular_duracao_horas(item.data_inicio, item.data_fim),
                    horas_trabalhadas=horas_trabalhadas,
                    km_trabalhados=km_trabalhados,
                    custo_estimado=custo_estimado,
                    metrica_custo=metrica_custo,  # type: ignore[arg-type]
                    observacoes=item.observacoes,
                )
            )
        return resposta

    def _montar_alertas(
        self,
        equipamento: Equipamento,
        ordens_servico: list[OrdemServico],
        documentos: list[DocumentoEquipamento],
        manutencao_status: str,
        dias_sem_abastecimento: int | None,
        agora: datetime,
        custo_total_geral: float,
        periodo_dias: int | None,
    ) -> list[FrotaDashboardDetalheAlerta]:
        alertas: list[FrotaDashboardDetalheAlerta] = []
        hoje = agora.date()
        docs_alerta = self._montar_documentos_alerta(documentos, hoje)

        if self._tem_risco_sem_abastecimento(equipamento, dias_sem_abastecimento):
            alertas.append(
                FrotaDashboardDetalheAlerta(
                    tipo="SEM_ABASTECIMENTO_RECENTE",
                    titulo="Sem abastecimento recente",
                    severidade="warning",
                    detalhe=(
                        f"Equipamento sem abastecimento há {dias_sem_abastecimento} dias."
                        if dias_sem_abastecimento is not None
                        else "Equipamento sem histórico de abastecimento."
                    ),
                    dias_desde_evento=dias_sem_abastecimento,
                )
            )

        ordem_antiga = self._obter_os_aberta_antiga(ordens_servico, agora)
        if ordem_antiga:
            dias_aberta = max((agora - ordem_antiga.data_abertura).days, 0)
            alertas.append(
                FrotaDashboardDetalheAlerta(
                    tipo="OS_ABERTA_ANTIGA",
                    titulo="OS aberta há muitos dias",
                    severidade="danger",
                    detalhe=f"OS {ordem_antiga.numero_os} permanece aberta há {dias_aberta} dias.",
                    dias_desde_evento=dias_aberta,
                    data_referencia=ordem_antiga.data_abertura,
                )
            )

        if manutencao_status == "VENCIDA":
            alertas.append(
                FrotaDashboardDetalheAlerta(
                    tipo="MANUTENCAO_VENCIDA",
                    titulo="Manutenção vencida",
                    severidade="danger",
                    detalhe="Pelo menos um plano de manutenção está vencido pelo horímetro/km atual.",
                )
            )

        if any(item.status == "VENCIDO" for item in docs_alerta):
            alertas.append(
                FrotaDashboardDetalheAlerta(
                    tipo="DOCUMENTO_VENCIDO",
                    titulo="Documento vencido",
                    severidade="danger",
                    detalhe="Há documento regulatório vencido vinculado ao equipamento.",
                )
            )

        if periodo_dias and custo_total_geral > 0:
            dias_referencia = max(periodo_dias, 1)
            custo_dia = custo_total_geral / dias_referencia
            if custo_dia > 100:
                alertas.append(
                    FrotaDashboardDetalheAlerta(
                        tipo="CUSTO_ACIMA_MEDIA",
                        titulo="Custo elevado no período",
                        severidade="warning",
                        detalhe=(
                            f"Custo acumulado de R$ {custo_total_geral:,.2f} no período selecionado."
                        ).replace(",", "X").replace(".", ",").replace("X", "."),
                    )
                )

        return alertas

    @staticmethod
    def _gerar_recomendacao(
        alertas: list[FrotaDashboardDetalheAlerta],
        documentos_alerta: list[FrotaDashboardDetalheDocumento],
        planos: list[FrotaDashboardDetalhePlanoManutencao],
    ) -> str:
        if any(alerta.tipo == "MANUTENCAO_VENCIDA" for alerta in alertas):
            return "Priorize a execução da manutenção vencida antes de ampliar o uso do equipamento."
        if any(alerta.tipo == "OS_ABERTA_ANTIGA" for alerta in alertas):
            return "Revisar e concluir a OS em aberto deve ser a ação imediata para reduzir indisponibilidade."
        if any(item.status == "VENCIDO" for item in documentos_alerta):
            return "Regularize os documentos vencidos do equipamento para evitar risco operacional e de conformidade."
        if any(alerta.tipo == "SEM_ABASTECIMENTO_RECENTE" for alerta in alertas):
            return "Verifique se o equipamento está parado sem registro operacional ou se há falha no lançamento dos abastecimentos."
        if any(plano.status == "PROXIMA" for plano in planos):
            return "Planeje a próxima manutenção preventiva agora para evitar parada corretiva."
        return "Equipamento com operação estável. Mantenha o ritmo de lançamentos e o acompanhamento preventivo."
