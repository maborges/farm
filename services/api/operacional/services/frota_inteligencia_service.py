from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.exceptions import EntityNotFoundError
from operacional.models.frota import OrdemServico
from operacional.schemas.frota_inteligencia import (
    FrotaInteligenciaEquipamentoItem,
    FrotaInteligenciaEquipamentoResponse,
    FrotaInteligenciaFator,
    FrotaInteligenciaRankingItem,
    FrotaInteligenciaResponse,
    FrotaInteligenciaResumo,
    FrotaInteligenciaInsight,
    FrotaInteligenciaAcaoDireta,
)
from operacional.services.frota_consumo_service import FrotaConsumoService
from operacional.services.frota_custo_service import FrotaCustoService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_disponibilidade_service import FrotaDisponibilidadeService
from operacional.services.frota_jornada_service import FrotaJornadaService
from operacional.services.frota_automacao_service import FrotaAutomacaoService


@dataclass
class _ContextoInteligencia:
    item: FrotaInteligenciaEquipamentoItem


class FrotaInteligenciaService(FrotaDashboardService):
    RANKING_LIMIT = 5
    JORNADA_RECENTE_DIAS = 7
    HORAS_USO_INTENSIVO = 40.0
    KM_USO_INTENSIVO = 1200.0
    PESOS = {
        "MANUTENCAO_VENCIDA": 30,
        "MANUTENCAO_PROXIMA": 12,
        "CONSUMO_ACIMA_MEDIA": 14,
        "CUSTO_ACIMA_MEDIA": 14,
        "USO_INTENSIVO": 12,
        "SEM_ABASTECIMENTO_RECENTE": 10,
        "CHECKLIST_NAO_CONFORME": 18,
        "CHECKLIST_PENDENTE": 8,
        "DOCUMENTO_VENCIDO": 20,
        "OS_ABERTA_ANTIGA": 18,
        "RISCO_PARADA": 10,
    }

    async def obter_inteligencia(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaInteligenciaResponse:
        agora = datetime.now(timezone.utc)
        contextos = await self._montar_contextos(unidade_produtiva_id, agora)
        equipamentos = [item.item for item in contextos]

        contador_niveis = Counter(item.nivel_risco for item in equipamentos)
        recomendacoes_gerais = self._montar_recomendacoes_gerais(equipamentos)

        return FrotaInteligenciaResponse(
            resumo=FrotaInteligenciaResumo(
                total_equipamentos=len(equipamentos),
                equipamentos_criticos=contador_niveis.get("CRITICO", 0),
                equipamentos_alto_risco=contador_niveis.get("ALTO", 0),
                equipamentos_medio_risco=contador_niveis.get("MEDIO", 0),
                equipamentos_baixo_risco=contador_niveis.get("BAIXO", 0),
                alertas_consolidados=sum(len(item.fatores) for item in equipamentos),
            ),
            equipamentos=sorted(equipamentos, key=lambda item: (item.score_risco, item.custo_total, item.equipamento_nome), reverse=True),
            ranking_risco=self._ranking_risco(equipamentos),
            ranking_mais_caros=self._ranking_mais_caros(equipamentos),
            ranking_menos_eficientes=self._ranking_menos_eficientes(equipamentos),
            recomendacoes_gerais=recomendacoes_gerais,
            insights_financeiros=await self._gerar_insights_financeiros(unidade_produtiva_id),
            gerado_em=agora,
        )

    async def obter_inteligencia_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaInteligenciaEquipamentoResponse:
        resposta = await self.obter_inteligencia(unidade_produtiva_id=unidade_produtiva_id)
        equipamento = next((item for item in resposta.equipamentos if item.equipamento_id == equipamento_id), None)
        if equipamento is None:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")
        ranking_posicao = next(
            (index + 1 for index, item in enumerate(resposta.ranking_risco) if item.equipamento_id == equipamento_id),
            None,
        )
        return FrotaInteligenciaEquipamentoResponse(
            equipamento=equipamento,
            ranking_risco_posicao=ranking_posicao,
            gerado_em=resposta.gerado_em,
        )

    async def _montar_contextos(
        self,
        unidade_produtiva_id: uuid.UUID | None,
        agora: datetime,
    ) -> list[_ContextoInteligencia]:
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        if not equipamentos:
            return []

        consumo = await FrotaConsumoService(self.session, self.tenant_id).obter_resumo_consumo(unidade_produtiva_id)
        custos = await FrotaCustoService(self.session, self.tenant_id).obter_custos(unidade_produtiva_id=unidade_produtiva_id)
        disponibilidade = await FrotaDisponibilidadeService(self.session, self.tenant_id).obter_disponibilidade(unidade_produtiva_id)
        jornadas = await FrotaJornadaService(self.session, self.tenant_id).listar_jornadas(
            unidade_produtiva_id=unidade_produtiva_id,
            periodo_dias=self.JORNADA_RECENTE_DIAS,
        )

        consumo_map = {item.equipamento_id: item for item in consumo.equipamentos}
        custo_map = {item.equipamento_id: item for item in custos.equipamentos}
        custo_medio_frota = float(custos.resumo.custo_medio_por_equipamento or 0.0)
        disponibilidade_map = {item.equipamento_id: item for item in disponibilidade.equipamentos}
        consumo_alertas_map: dict[uuid.UUID, list] = defaultdict(list)
        for alerta in consumo.alertas:
            consumo_alertas_map[alerta.equipamento_id].append(alerta)
        jornadas_map: dict[uuid.UUID, list] = defaultdict(list)
        for jornada in jornadas.jornadas:
            jornadas_map[jornada.equipamento_id].append(jornada)
        planos_map: dict[uuid.UUID, list] = defaultdict(list)
        for plano in await self._listar_planos([item.id for item in equipamentos]):
            planos_map[plano.equipamento_id].append(plano)

        ordens = await self._listar_ordens_servico([item.id for item in equipamentos])
        os_abertas_antigas: dict[uuid.UUID, OrdemServico] = {}
        for ordem in ordens:
            antiga = self._obter_os_aberta_antiga([ordem], agora)
            if antiga and ordem.equipamento_id not in os_abertas_antigas:
                os_abertas_antigas[ordem.equipamento_id] = ordem

        contextos: list[_ContextoInteligencia] = []
        for equipamento in equipamentos:
            consumo_item = consumo_map.get(equipamento.id)
            custo_item = custo_map.get(equipamento.id)
            disponibilidade_item = disponibilidade_map.get(equipamento.id)
            jornadas_equipamento = jornadas_map.get(equipamento.id, [])
            item = self._construir_item(
                equipamento=equipamento,
                consumo_item=consumo_item,
                consumo_alertas=consumo_alertas_map.get(equipamento.id, []),
                custo_item=custo_item,
                custo_medio_frota=custo_medio_frota,
                disponibilidade_item=disponibilidade_item,
                jornadas=jornadas_equipamento,
                os_aberta_antiga=os_abertas_antigas.get(equipamento.id),
                manutencao_status=self._calcular_status_manutencao(equipamento, planos_map[equipamento.id]),
            )
            contextos.append(_ContextoInteligencia(item=item))
        return contextos

    def _construir_item(
        self,
        equipamento,
        consumo_item,
        consumo_alertas: list,
        custo_item,
        custo_medio_frota: float,
        disponibilidade_item,
        jornadas: list,
        os_aberta_antiga: OrdemServico | None,
        manutencao_status,
    ) -> FrotaInteligenciaEquipamentoItem:
        fatores: list[FrotaInteligenciaFator] = []
        recomendacoes: list[str] = []

        horas_recentes = round(sum(float(item.horas_trabalhadas or 0.0) for item in jornadas if item.status == "FINALIZADA"), 2)
        km_recentes = round(sum(float(item.km_trabalhados or 0.0) for item in jornadas if item.status == "FINALIZADA"), 2)
        jornada_aberta = any(item.status == "ABERTA" for item in jornadas)

        manutencao_status_value = manutencao_status.status
        checklist_status = "SEM_EXIGENCIA"
        documento_vencido = False
        os_abertas = 0
        dias_sem_abastecimento = None

        if disponibilidade_item:
            os_abertas = 1 if disponibilidade_item.os_aberta else 0
            documento_vencido = len(disponibilidade_item.documentos_vencidos) > 0
            if disponibilidade_item.nao_conforme:
                checklist_status = "NAO_CONFORME"
            elif disponibilidade_item.checklist_pendente:
                checklist_status = "PENDENTE"
            else:
                checklist_status = "OK"
            if disponibilidade_item.manutencao_preventiva_vencida:
                manutencao_status_value = "VENCIDA"

        if consumo_item:
            dias_sem_abastecimento = consumo_item.dias_sem_abastecimento
        if custo_item and custo_item.custo_total > 0 and custo_medio_frota > 0 and custo_item.custo_total > custo_medio_frota * 1.2:
            fatores.append(self._fator("CUSTO_ACIMA_MEDIA", "Custo acima da média", f"Custo total acima da média da frota de {custo_medio_frota:.2f}."))
            recomendacoes.append("Equipamento com custo acima da média")

        if consumo_item:
            if any(alerta.tipo == "CONSUMO_ACIMA_MEDIA" for alerta in consumo_alertas):
                fatores.append(self._fator("CONSUMO_ACIMA_MEDIA", "Consumo acima da média", "O consumo/eficiência está fora da média esperada da frota."))
                recomendacoes.append("Verificar consumo elevado")
            if any(alerta.tipo == "CUSTO_ACIMA_MEDIA" for alerta in consumo_alertas):
                fatores.append(self._fator("CUSTO_ACIMA_MEDIA", "Custo operacional acima da média", "Custo por hora/km acima da referência da frota."))
                if "Equipamento com custo acima da média" not in recomendacoes:
                    recomendacoes.append("Equipamento com custo acima da média")
            if consumo_item.dias_sem_abastecimento is None or (consumo_item.dias_sem_abastecimento is not None and consumo_item.dias_sem_abastecimento > self.SEM_ABASTECIMENTO_DIAS):
                fatores.append(self._fator("SEM_ABASTECIMENTO_RECENTE", "Sem abastecimento recente", "Equipamento sem abastecimento recente ou sem histórico suficiente."))

        if manutencao_status_value == "VENCIDA":
            fatores.append(self._fator("MANUTENCAO_VENCIDA", "Manutenção preventiva vencida", "Há plano preventivo vencido para o equipamento."))
            recomendacoes.append("Realizar manutenção preventiva")
        elif manutencao_status_value == "PROXIMA":
            fatores.append(self._fator("MANUTENCAO_PROXIMA", "Manutenção próxima do vencimento", "Há plano preventivo próximo do vencimento."))

        if horas_recentes >= self.HORAS_USO_INTENSIVO or km_recentes >= self.KM_USO_INTENSIVO:
            fatores.append(self._fator("USO_INTENSIVO", "Uso intensivo recente", "O equipamento acumulou uso elevado nos últimos 7 dias."))
            recomendacoes.append("Equipamento com uso intensivo recente")

        if checklist_status == "NAO_CONFORME":
            fatores.append(self._fator("CHECKLIST_NAO_CONFORME", "Checklist não conforme", "Último checklist bloqueou liberação operacional."))
        elif checklist_status == "PENDENTE":
            fatores.append(self._fator("CHECKLIST_PENDENTE", "Checklist pendente", "Checklist operacional exigido fora da janela recente."))

        if documento_vencido:
            fatores.append(self._fator("DOCUMENTO_VENCIDO", "Documento vencido", "Há pendência documental crítica no equipamento."))

        if os_aberta_antiga is not None:
            fatores.append(self._fator("OS_ABERTA_ANTIGA", "OS aberta há muito tempo", f"OS {os_aberta_antiga.numero_os} aberta acima do limite operacional."))

        if (
            manutencao_status_value == "VENCIDA"
            or checklist_status == "NAO_CONFORME"
            or documento_vencido
            or os_aberta_antiga is not None
        ):
            fatores.append(self._fator("RISCO_PARADA", "Risco de parada", "Combinação de fatores com potencial de indisponibilidade do equipamento."))
            recomendacoes.append("Equipamento com risco de parada")

        score = min(sum(item.pontuacao for item in fatores), 100)
        nivel = self._classificar_score(score)

        if not recomendacoes and nivel == "BAIXO":
            recomendacoes = ["Monitorar operação dentro da rotina normal"]

        return FrotaInteligenciaEquipamentoItem(
            equipamento_id=equipamento.id,
            equipamento_nome=equipamento.nome,
            equipamento_tipo=equipamento.tipo,
            equipamento_status=self._normalizar_status(equipamento.status),
            unidade_produtiva_id=equipamento.unidade_produtiva_id,
            score_risco=score,
            nivel_risco=nivel,  # type: ignore[arg-type]
            custo_total=float(custo_item.custo_total if custo_item else 0.0),
            custo_por_hora=custo_item.custo_por_hora if custo_item else None,
            custo_por_km=custo_item.custo_por_km if custo_item else None,
            eficiencia_score=consumo_item.eficiencia_score if consumo_item else None,
            jornada_aberta=jornada_aberta,
            horas_trabalhadas_recentes=horas_recentes if horas_recentes > 0 else None,
            km_trabalhados_recentes=km_recentes if km_recentes > 0 else None,
            dias_sem_abastecimento=dias_sem_abastecimento,
            os_abertas=os_abertas,
            os_aberta_antiga=os_aberta_antiga is not None,
            manutencao_status=manutencao_status_value,  # type: ignore[arg-type]
            checklist_status=checklist_status,  # type: ignore[arg-type]
            documento_vencido=documento_vencido,
            consumo_alerta=any(item.chave == "CONSUMO_ACIMA_MEDIA" for item in fatores),
            custo_alerta=any(item.chave == "CUSTO_ACIMA_MEDIA" for item in fatores),
            uso_intensivo_alerta=any(item.chave == "USO_INTENSIVO" for item in fatores),
            recomendacoes=list(dict.fromkeys(recomendacoes)),
            fatores=fatores,
        )

    def _ranking_risco(self, equipamentos: list[FrotaInteligenciaEquipamentoItem]) -> list[FrotaInteligenciaRankingItem]:
        return [
            FrotaInteligenciaRankingItem(
                equipamento_id=item.equipamento_id,
                equipamento_nome=item.equipamento_nome,
                equipamento_tipo=item.equipamento_tipo,
                score_risco=item.score_risco,
                nivel_risco=item.nivel_risco,
                detalhe=", ".join(item.recomendacoes[:2]) if item.recomendacoes else None,
            )
            for item in sorted(equipamentos, key=lambda item: (item.score_risco, item.custo_total), reverse=True)[: self.RANKING_LIMIT]
        ]

    def _ranking_mais_caros(self, equipamentos: list[FrotaInteligenciaEquipamentoItem]) -> list[FrotaInteligenciaRankingItem]:
        return [
            FrotaInteligenciaRankingItem(
                equipamento_id=item.equipamento_id,
                equipamento_nome=item.equipamento_nome,
                equipamento_tipo=item.equipamento_tipo,
                valor=item.custo_total,
                score_risco=item.score_risco,
                nivel_risco=item.nivel_risco,
                detalhe="Custo total consolidado",
            )
            for item in sorted(equipamentos, key=lambda item: item.custo_total, reverse=True)[: self.RANKING_LIMIT]
        ]

    def _ranking_menos_eficientes(self, equipamentos: list[FrotaInteligenciaEquipamentoItem]) -> list[FrotaInteligenciaRankingItem]:
        candidatos = [item for item in equipamentos if item.eficiencia_score is not None]
        return [
            FrotaInteligenciaRankingItem(
                equipamento_id=item.equipamento_id,
                equipamento_nome=item.equipamento_nome,
                equipamento_tipo=item.equipamento_tipo,
                valor=item.eficiencia_score,
                score_risco=item.score_risco,
                nivel_risco=item.nivel_risco,
                detalhe="Eficiência relativa da frota",
            )
            for item in sorted(candidatos, key=lambda item: item.eficiencia_score or 9999)[: self.RANKING_LIMIT]
        ]

    def _montar_recomendacoes_gerais(self, equipamentos: list[FrotaInteligenciaEquipamentoItem]) -> list[str]:
        contagem = Counter(recomendacao for item in equipamentos for recomendacao in item.recomendacoes)
        return [item for item, _ in contagem.most_common(5)]

    def _fator(self, chave: str, titulo: str, detalhe: str | None = None) -> FrotaInteligenciaFator:
        peso = int(self.PESOS.get(chave, 0))
        return FrotaInteligenciaFator(
            chave=chave,
            titulo=titulo,
            peso=peso,
            pontuacao=peso,
            detalhe=detalhe,
        )

    @staticmethod
    def _classificar_score(score: int) -> str:
        if score >= 70:
            return "CRITICO"
        if score >= 45:
            return "ALTO"
        if score >= 20:
            return "MEDIO"
        return "BAIXO"

    async def _gerar_insights_financeiros(self, unidade_produtiva_id: uuid.UUID | None) -> list[FrotaInteligenciaInsight]:
        custos = await FrotaCustoService(self.session, self.tenant_id).obter_custos(unidade_produtiva_id=unidade_produtiva_id)
        insights: list[FrotaInteligenciaInsight] = []

        # 1. Insights por Talhão (Desvio > 30% da média)
        if custos.por_talhao:
            media_talhao = sum(t.custo_total for t in custos.por_talhao) / len(custos.por_talhao)
            for talhao in custos.por_talhao:
                if talhao.custo_total > media_talhao * 1.3:
                    insights.append(
                        FrotaInteligenciaInsight(
                            titulo=f"Custo elevado no Talhão {talhao.talhao_nome}",
                            descricao=f"O custo da frota neste talhão está {((talhao.custo_total/media_talhao)-1)*100:.0f}% acima da média dos demais talhões.",
                            impacto_financeiro=round(talhao.custo_total - media_talhao, 2),
                            gravidade="ALTA",
                            acao_sugerida="Avaliar condições do terreno ou excesso de manobras na área.",
                            contexto="Talhão",
                            acao_direta=FrotaInteligenciaAcaoDireta(
                                label="Ver Operações",
                                url=f"/dashboard/frota/custos?talhao_id={talhao.talhao_id}",
                                tipo="LINK"
                            )
                        )
                    )
                    # Trigger Automação
                    await FrotaAutomacaoService(self.session, self.tenant_id).processar_insight(
                        "CUSTO_ACIMA_MEDIA", 
                        uuid.UUID("00000000-0000-0000-0000-000000000000"), # Contexto global/área
                        {"desvio_percentual": (talhao.custo_total/media_talhao-1)*100}
                    )

        # 2. Insights por Operação
        if custos.por_operacao:
            media_operacao = sum(o.custo_total for o in custos.por_operacao) / len(custos.por_operacao)
            for operacao in custos.por_operacao:
                if operacao.custo_total > media_operacao * 1.5:
                    insights.append(
                        FrotaInteligenciaInsight(
                            titulo=f"Operação {operacao.operacao} com custo crítico",
                            descricao=f"Esta operação representa {operacao.participacao_percentual}% do custo total da frota, superando as referências históricas.",
                            impacto_financeiro=round(operacao.custo_total - media_operacao, 2),
                            gravidade="MEDIA",
                            acao_sugerida="Revisar configuração das máquinas para esta operação ou treinar operadores.",
                            contexto="Operação",
                            acao_direta=FrotaInteligenciaAcaoDireta(
                                label="Analisar Jornadas",
                                url=f"/dashboard/frota/jornadas?operacao={operacao.operacao}",
                                tipo="LINK"
                            )
                        )
                    )

        # 3. Equipamentos menos eficientes (Top 1)
        if custos.equipamentos:
            # Pegar o que tem maior custo por hora se disponível
            equip_caros = [e for e in custos.equipamentos if e.custo_por_hora and e.custo_por_hora > 0]
            if equip_caros:
                media_hora = sum(e.custo_por_hora for e in equip_caros) / len(equip_caros)
                pior_equip = max(equip_caros, key=lambda e: e.custo_por_hora or 0)
                if pior_equip.custo_por_hora and pior_equip.custo_por_hora > media_hora * 1.4:
                    insights.append(
                        FrotaInteligenciaInsight(
                            titulo=f"Ineficiência crítica: {pior_equip.equipamento_nome}",
                            descricao=f"Custo de R$ {pior_equip.custo_por_hora:.2f}/h é {((pior_equip.custo_por_hora/media_hora)-1)*100:.0f}% superior à média da frota.",
                            impacto_financeiro=round((pior_equip.custo_por_hora - media_hora) * (pior_equip.horimetro_atual or 1), 2),
                            gravidade="ALTA",
                            acao_sugerida="Avaliar substituição do equipamento ou revisão geral do motor/sistema hidráulico.",
                            contexto="Equipamento",
                            acao_direta=FrotaInteligenciaAcaoDireta(
                                label="Abrir OS de Manutenção",
                                url="/dashboard/frota/manutencao/nova",
                                tipo="ACTION",
                                payload={"equipamento_id": str(pior_equip.equipamento_id), "tipo": "CORRETIVA", "observacao": "Manutenção sugerida por inteligência de custo elevado."}
                            )
                        )
                    )

        return sorted(insights, key=lambda x: x.impacto_financeiro or 0, reverse=True)
