from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
from statistics import mean
from typing import Iterable, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agricola.alertas.service import AlertasAgricolasService, WorkflowGovernanceFinding
from agricola.benchmark import BenchmarkAgricolaV1Service
from agricola.dre import AgricolaDreKpiService, DREAgricolaV1Service
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREWarning
from agricola.eficiencia import EficienciaOperacionalAgricolaV1Service
from agricola.rentabilidade import RentabilidadeAgricolaV1Service
from agricola.safras.models import Safra
from core.base_service import BaseService
from core.services.analytics_taxonomy import classificar_codigo, severidade_ordem
from core.services.analytics_request_cache import (
    build_analytics_scope_key,
    build_analytics_value_key,
    get_analytics_request_cache,
)

from .schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo


class DiagnosticoOperacionalEconomicoAgricolaV1Service(BaseService[Safra]):
    """Camada oficial de diagnóstico agrícola derivada da DRE v1 e dos analytics oficiais consolidados."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Safra, session, tenant_id)

    async def gerar(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> DiagnosticoAgricolaResponse:
        cache_key = build_analytics_value_key(
            "agricola.diagnostico.v1",
            build_analytics_scope_key(
                self.tenant_id,
                safra_id,
                production_unit_id,
                unidade_produtiva_id,
                data_inicio,
                data_fim,
            ),
        )
        cache = get_analytics_request_cache()
        if cache_key in cache:
            return cache[cache_key]

        dre = await DREAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        dre_kpis = dre.kpis or AgricolaDreKpiService.calcular(
            dre,
            area_total_ha=self._area_total(dre),
            warnings=dre.warnings,
        )
        rentabilidade = await RentabilidadeAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        eficiencia = await EficienciaOperacionalAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        benchmark = await BenchmarkAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        alertas = AlertasAgricolasService(self.session, self.tenant_id)
        findings_operacionais = await alertas.detectar_inconsistencias_operacionais()
        findings_reconciliacao = await alertas.detectar_inconsistencias_reconciliacao_economica()

        warnings = self._dedupe_warnings([
            *dre.warnings,
            *rentabilidade.warnings,
            *eficiencia.warnings,
            *benchmark.warnings,
            *self._findings_to_warnings(findings_operacionais),
            *self._findings_to_warnings(findings_reconciliacao),
        ])

        diagnosticos: list[DiagnosticoAgricolaItem] = []
        diagnosticos.extend(self._diagnosticar_safra(benchmark, dre_kpis))
        diagnosticos.extend(self._diagnosticar_production_units(benchmark))
        diagnosticos.extend(self._diagnosticar_equipamentos(eficiencia))
        diagnosticos.extend(self._diagnosticar_operacoes(eficiencia))
        diagnosticos.extend(self._diagnosticar_recorrencias(warnings, findings_operacionais, findings_reconciliacao))

        diagnosticos = self._rankear(diagnosticos)
        resumo = self._resumo(diagnosticos)

        sujeito_reconciliacao = bool(
            warnings
            or any(item.severidade != "INFO" for item in diagnosticos)
        )
        observacao = "diagnósticos sujeitos à reconciliação." if sujeito_reconciliacao else None

        response = DiagnosticoAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            diagnosticos=diagnosticos,
            ranking=diagnosticos,
            resumo=resumo,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )
        cache[cache_key] = response
        return response

    def _diagnosticar_safra(
        self,
        benchmark,
        dre_kpis: DREAgricolaKpis,
    ) -> list[DiagnosticoAgricolaItem]:
        items: list[DiagnosticoAgricolaItem] = []
        safra = benchmark.safra
        production_units = benchmark.production_units or []
        media_margem = self._media(item.margem_pct for item in production_units)
        media_custo = self._media(item.custo_operacional_por_hectare for item in production_units)
        media_resultado = self._media(item.resultado_por_hectare for item in production_units)
        media_receita = self._media(item.receita_liquida_por_hectare for item in production_units)
        media_jornada = self._media(item.hectares_por_jornada for item in production_units)

        if safra.margem_pct is not None and media_margem is not None and safra.margem_pct < media_margem:
            items.append(self._item(
                scope="SAFRA",
                codigo="MARGEM_ABAIXO_MEDIA_TENANT",
                titulo="Margem abaixo da média do tenant",
                severidade=self._severidade_desvio(safra.margem_pct, media_margem, invertido=False),
                categoria="ECONOMICO",
                item_id=str(safra.id),
                label=safra.label,
                mensagem=(
                    f"Margem da safra ({self._fmt_pct(safra.margem_pct)}) está abaixo da média oficial do recorte "
                    f"({self._fmt_pct(media_margem)})."
                ),
                valor_observado=safra.margem_pct,
                valor_referencia=media_margem,
                sugestao="Revisar as frentes com maior custo ou menor receita líquida.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        if safra.custo_operacional_por_hectare is not None and media_custo is not None and safra.custo_operacional_por_hectare > media_custo:
            items.append(self._item(
                scope="SAFRA",
                codigo="CUSTO_HECTARE_ACIMA_MEDIA",
                titulo="Custo/ha acima da média",
                severidade=self._severidade_custo(safra.custo_operacional_por_hectare, media_custo),
                categoria="ECONOMICO",
                item_id=str(safra.id),
                label=safra.label,
                mensagem=(
                    f"Custo operacional por hectare ({self._fmt_money(safra.custo_operacional_por_hectare)}) ficou acima "
                    f"da média do recorte ({self._fmt_money(media_custo)})."
                ),
                valor_observado=safra.custo_operacional_por_hectare,
                valor_referencia=media_custo,
                sugestao="Priorizar reconciliação dos centros de custo mais pesados.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        benchmark_ref = benchmark.destaques.referencia or (production_units[0] if production_units else None)
        if safra.resultado_por_hectare is not None and benchmark_ref and benchmark_ref.resultado_por_hectare is not None and safra.resultado_por_hectare < benchmark_ref.resultado_por_hectare:
            items.append(self._item(
                scope="SAFRA",
                codigo="RESULTADO_SAFRA_ABAIXO_BENCHMARK",
                titulo="Resultado da safra abaixo do benchmark",
                severidade=self._severidade_desvio(safra.resultado_por_hectare, benchmark_ref.resultado_por_hectare, invertido=False),
                categoria="ECONOMICO",
                item_id=str(safra.id),
                label=safra.label,
                mensagem=(
                    f"Resultado por hectare ({self._fmt_money(safra.resultado_por_hectare)}) está abaixo do benchmark "
                    f"oficial ({self._fmt_money(benchmark_ref.resultado_por_hectare)})."
                ),
                valor_observado=safra.resultado_por_hectare,
                valor_referencia=benchmark_ref.resultado_por_hectare,
                sugestao="Rever a combinação de receita líquida e custo operacional na safra.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        if safra.hectares_por_jornada is not None and media_jornada is not None and safra.hectares_por_jornada < media_jornada:
            items.append(self._item(
                scope="JOURNEY",
                codigo="JORNADA_BAIXA_PRODUTIVIDADE",
                titulo="Baixa produtividade por jornada",
                severidade=self._severidade_desvio(safra.hectares_por_jornada, media_jornada, invertido=False),
                categoria="OPERACIONAL",
                item_id=f"{safra.id}:jornada",
                label=safra.label,
                mensagem=(
                    f"Produtividade por jornada ({safra.hectares_por_jornada:.2f} ha/jornada) está abaixo da média "
                    f"do recorte ({media_jornada:.2f} ha/jornada)."
                ),
                valor_observado=safra.hectares_por_jornada,
                valor_referencia=media_jornada,
                sugestao="Revisar dimensionamento de equipe, rota e disponibilidade de equipamento.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        if (
            dre_kpis.resultado_operacional is not None
            and dre_kpis.resultado_operacional < 0
        ):
            items.append(self._item(
                scope="SAFRA",
                codigo="RESULTADO_OPERACIONAL_NEGATIVO",
                titulo="Resultado operacional negativo",
                severidade="RISCO_ECONOMICO",
                categoria="ECONOMICO",
                item_id=str(safra.id),
                label=safra.label,
                mensagem="O resultado operacional da safra está negativo e exige reconciliação econômica imediata.",
                valor_observado=dre_kpis.resultado_operacional,
                valor_referencia=0.0,
                sugestao="Revisar custos alocados, receita reconhecida e eventuais duplicidades.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        if (
            media_receita is not None
            and safra.receita_liquida_por_hectare is not None
            and safra.receita_liquida_por_hectare < media_receita
        ):
            items.append(self._item(
                scope="SAFRA",
                codigo="RECEITA_LIQUIDA_HA_ABAIXO_MEDIA",
                titulo="Receita líquida/ha abaixo da média",
                severidade=self._severidade_desvio(safra.receita_liquida_por_hectare, media_receita, invertido=False),
                categoria="ECONOMICO",
                item_id=str(safra.id),
                label=safra.label,
                mensagem=(
                    f"Receita líquida por hectare ({self._fmt_money(safra.receita_liquida_por_hectare)}) está abaixo "
                    f"da média do recorte ({self._fmt_money(media_receita)})."
                ),
                valor_observado=safra.receita_liquida_por_hectare,
                valor_referencia=media_receita,
                sugestao="Rever produtividade, mix de operações e perdas reconhecidas na DRE.",
                warnings_relevantes=safra.warnings_relevantes,
            ))

        return items

    def _diagnosticar_production_units(self, benchmark) -> list[DiagnosticoAgricolaItem]:
        items: list[DiagnosticoAgricolaItem] = []
        unidades = benchmark.production_units or []
        media_custo = self._media(item.custo_operacional_por_hectare for item in unidades)
        media_resultado = self._media(item.resultado_por_hectare for item in unidades)
        media_jornada = self._media(item.hectares_por_jornada for item in unidades)

        for unidade in unidades:
            desvio_operacional = False
            severidade = "ATENCAO"
            observada = unidade.resultado_por_hectare
            referencia = media_resultado
            mensagem_partes: list[str] = []
            if (
                unidade.custo_operacional_por_hectare is not None
                and media_custo is not None
                and unidade.custo_operacional_por_hectare > media_custo
            ):
                desvio_operacional = True
                mensagem_partes.append(
                    f"custo/ha {self._fmt_money(unidade.custo_operacional_por_hectare)} acima da média {self._fmt_money(media_custo)}"
                )
                if unidade.custo_operacional_por_hectare >= media_custo * 1.25:
                    severidade = "RISCO_ECONOMICO"
            if (
                unidade.resultado_por_hectare is not None
                and media_resultado is not None
                and unidade.resultado_por_hectare < media_resultado
            ):
                desvio_operacional = True
                mensagem_partes.append(
                    f"resultado/ha {self._fmt_money(unidade.resultado_por_hectare)} abaixo da média {self._fmt_money(media_resultado)}"
                )
                if unidade.resultado_por_hectare <= media_resultado * 0.8:
                    severidade = "RISCO_ECONOMICO"
            if (
                unidade.hectares_por_jornada is not None
                and media_jornada is not None
                and unidade.hectares_por_jornada < media_jornada
            ):
                desvio_operacional = True
                mensagem_partes.append(
                    f"hectares/jornada {unidade.hectares_por_jornada:.2f} abaixo da média {media_jornada:.2f}"
                )
                if unidade.hectares_por_jornada <= media_jornada * 0.8:
                    severidade = "RISCO_OPERACIONAL" if severidade != "RISCO_ECONOMICO" else severidade
            if not desvio_operacional:
                continue

            items.append(self._item(
                scope="PRODUCTION_UNIT",
                codigo="PRODUCTION_UNIT_BAIXA_EFICIENCIA",
                titulo="ProductionUnit com baixa eficiência operacional",
                severidade=severidade,
                categoria="ECONOMICO" if severidade == "RISCO_ECONOMICO" else "OPERACIONAL",
                item_id=str(unidade.id),
                label=unidade.label,
                mensagem="; ".join(mensagem_partes) + ".",
                valor_observado=observada,
                valor_referencia=referencia,
                desvio_pct=self._delta_pct(observada, referencia),
                sugestao="Rever apropriação econômica, alocação operacional e execução local.",
                warnings_relevantes=unidade.warnings_relevantes,
            ))

        return items

    def _diagnosticar_equipamentos(self, eficiencia) -> list[DiagnosticoAgricolaItem]:
        items: list[DiagnosticoAgricolaItem] = []
        equipamentos = eficiencia.equipamentos or []
        media_custo = self._media(item.custo_operacional_por_hectare for item in equipamentos)
        for equipamento in equipamentos:
            if equipamento.custo_operacional_por_hectare is None or media_custo is None:
                continue
            if equipamento.custo_operacional_por_hectare <= media_custo:
                continue
            severity = "RISCO_OPERACIONAL" if equipamento.custo_operacional_por_hectare >= media_custo * 1.3 else "ATENCAO"
            items.append(self._item(
                scope="EQUIPMENT",
                codigo="EQUIPAMENTO_CUSTO_ELEVADO",
                titulo="Equipamento com custo operacional elevado",
                severidade=severity,
                categoria="OPERACIONAL",
                item_id=str(equipamento.id),
                label=equipamento.label,
                mensagem=(
                    f"Custo operacional por hectare do equipamento ({self._fmt_money(equipamento.custo_operacional_por_hectare)}) "
                    f"está acima da média dos equipamentos ({self._fmt_money(media_custo)})."
                ),
                valor_observado=equipamento.custo_operacional_por_hectare,
                valor_referencia=media_custo,
                desvio_pct=self._delta_pct(equipamento.custo_operacional_por_hectare, media_custo),
                sugestao="Revisar consumo, manutenção e aproveitamento da jornada do equipamento.",
                warnings_relevantes=equipamento.warnings_relevantes,
            ))
        return items

    def _diagnosticar_operacoes(self, eficiencia) -> list[DiagnosticoAgricolaItem]:
        items: list[DiagnosticoAgricolaItem] = []
        operacoes = eficiencia.operacoes or []
        media_custo = self._media(item.custo_operacional_por_hectare for item in operacoes)
        for operacao in operacoes:
            if operacao.custo_operacional_por_hectare is None or media_custo is None:
                continue
            if operacao.custo_operacional_por_hectare <= media_custo:
                continue
            severity = "RISCO_OPERACIONAL" if operacao.custo_operacional_por_hectare >= media_custo * 1.2 else "ATENCAO"
            items.append(self._item(
                scope="OPERATION",
                codigo="OPERACAO_CUSTO_FORA_CURVA",
                titulo="Operação agrícola com custo fora da curva",
                severidade=severity,
                categoria="OPERACIONAL",
                item_id=str(operacao.id),
                label=operacao.label,
                mensagem=(
                    f"Operação com custo por hectare ({self._fmt_money(operacao.custo_operacional_por_hectare)}) acima "
                    f"da média das operações ({self._fmt_money(media_custo)})."
                ),
                valor_observado=operacao.custo_operacional_por_hectare,
                valor_referencia=media_custo,
                desvio_pct=self._delta_pct(operacao.custo_operacional_por_hectare, media_custo),
                sugestao="Revisar consumo de insumos, ciclo e alocação de horas por operação.",
                warnings_relevantes=operacao.warnings_relevantes,
            ))
        return items

    def _diagnosticar_recorrencias(
        self,
        warnings: list[DREWarning],
        findings_operacionais: list[WorkflowGovernanceFinding],
        findings_reconciliacao: list[WorkflowGovernanceFinding],
    ) -> list[DiagnosticoAgricolaItem]:
        items: list[DiagnosticoAgricolaItem] = []
        counter = Counter(warning.codigo for warning in warnings)
        for finding in [*findings_operacionais, *findings_reconciliacao]:
            counter[finding.codigo] += 1

        economic_codes = [
            codigo
            for codigo, total in counter.items()
            if total >= 2 and classificar_codigo(codigo) == "ECONOMICO"
        ]
        operational_codes = [
            codigo
            for codigo, total in counter.items()
            if total >= 2 and classificar_codigo(codigo) == "OPERACIONAL"
        ]

        if economic_codes:
            codes = sorted(economic_codes, key=lambda codigo: (-counter[codigo], codigo))
            items.append(self._item(
                scope="TENANT",
                codigo="RECORRENCIA_WARNING_ECONOMICO",
                titulo="Recorrência de warning econômico",
                severidade="RISCO_ECONOMICO",
                categoria="RECORRENCIA",
                item_id=str(self.tenant_id),
                label="Tenant",
                mensagem=f"Warnings econômicos recorrentes identificados: {', '.join(codes[:4])}.",
                sugestao="Reconciliar as origens oficiais antes de ampliar o uso analítico.",
                warnings_relevantes=codes[:6],
            ))

        if operational_codes:
            codes = sorted(operational_codes, key=lambda codigo: (-counter[codigo], codigo))
            items.append(self._item(
                scope="TENANT",
                codigo="RECORRENCIA_INCONSISTENCIA_OPERACIONAL",
                titulo="Recorrência de inconsistência operacional",
                severidade="RISCO_OPERACIONAL",
                categoria="RECORRENCIA",
                item_id=str(self.tenant_id),
                label="Tenant",
                mensagem=f"Inconsistências operacionais recorrentes identificadas: {', '.join(codes[:4])}.",
                sugestao="Verificar operações, jornadas e apontamentos com repetição de desvio.",
                warnings_relevantes=codes[:6],
            ))

        return items

    def _rankear(self, items: list[DiagnosticoAgricolaItem]) -> list[DiagnosticoAgricolaItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                severidade_ordem(item.severidade),
                -(abs(item.desvio_pct or 0.0)),
                item.label,
            ),
        )
        for idx, item in enumerate(ranked, start=1):
            item.posicao = idx
        return ranked

    def _resumo(self, items: list[DiagnosticoAgricolaItem]) -> DiagnosticoAgricolaResumo:
        contador = Counter(item.severidade for item in items)
        return DiagnosticoAgricolaResumo(
            total=len(items),
            info=contador.get("INFO", 0),
            atencao=contador.get("ATENCAO", 0),
            risco_operacional=contador.get("RISCO_OPERACIONAL", 0),
            risco_economico=contador.get("RISCO_ECONOMICO", 0),
        )

    @staticmethod
    def _item(
        *,
        scope: Literal["SAFRA", "PRODUCTION_UNIT", "EQUIPMENT", "OPERATION", "JOURNEY", "TENANT"],
        codigo: str,
        titulo: str,
        severidade: Literal["INFO", "ATENCAO", "RISCO_OPERACIONAL", "RISCO_ECONOMICO"],
        categoria: Literal["OPERACIONAL", "ECONOMICO", "RECORRENCIA"],
        item_id: str,
        label: str,
        mensagem: str,
        valor_observado: float | None = None,
        valor_referencia: float | None = None,
        desvio_pct: float | None = None,
        sugestao: str | None = None,
        warnings_relevantes: list[str] | None = None,
    ) -> DiagnosticoAgricolaItem:
        return DiagnosticoAgricolaItem(
            scope=scope,
            id=item_id,
            label=label,
            codigo=codigo,
            titulo=titulo,
            severidade=severidade,
            mensagem=mensagem,
            categoria=categoria,
            valor_observado=valor_observado,
            valor_referencia=valor_referencia,
            desvio_pct=desvio_pct,
            sugestao=sugestao,
            warnings_relevantes=warnings_relevantes or [],
        )

    @staticmethod
    def _findings_to_warnings(findings: Iterable[WorkflowGovernanceFinding]) -> list[DREWarning]:
        return [
            DREWarning(
                codigo=finding.codigo,
                titulo=finding.titulo,
                severidade=finding.severidade,
                mensagem=finding.mensagem,
                origem=finding.origem,
                amostras=list(finding.amostras),
                meta=dict(finding.meta),
            )
            for finding in findings
        ]

    @staticmethod
    def _dedupe_warnings(warnings: list[DREWarning]) -> list[DREWarning]:
        deduped: dict[tuple[str, str], DREWarning] = {}
        for warning in warnings:
            deduped[(warning.codigo, warning.origem)] = warning
        return list(deduped.values())

    @staticmethod
    def _media(values: Iterable[float | None]) -> float | None:
        filtrados = [float(value) for value in values if value is not None]
        if not filtrados:
            return None
        return round(mean(filtrados), 2)

    @staticmethod
    def _delta_pct(observado: float | None, referencia: float | None) -> float | None:
        if observado is None or referencia in (None, 0):
            return None
        return round(((float(observado) - float(referencia)) / float(referencia)) * 100, 2)

    @staticmethod
    def _fmt_money(value: float | None) -> str:
        if value is None:
            return "—"
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _fmt_pct(value: float | None) -> str:
        if value is None:
            return "—"
        return f"{value:.1f}%"

    @staticmethod
    def _severidade_desvio(observado: float, referencia: float, *, invertido: bool) -> str:
        if referencia == 0:
            return "ATENCAO"
        ratio = observado / referencia if referencia else 1.0
        if invertido:
            ratio = referencia / observado if observado else 0.0
        if ratio <= 0.8:
            return "RISCO_ECONOMICO"
        if ratio <= 0.9:
            return "ATENCAO"
        return "INFO"

    @staticmethod
    def _severidade_custo(observado: float, referencia: float) -> str:
        if referencia == 0:
            return "ATENCAO"
        ratio = observado / referencia
        if ratio >= 1.25:
            return "RISCO_ECONOMICO"
        if ratio >= 1.1:
            return "ATENCAO"
        return "INFO"
