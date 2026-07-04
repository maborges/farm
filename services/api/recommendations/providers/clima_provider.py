from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from agricola.climatico.config import ClimaThresholds
from agricola.climatico.models import RegistroClima

from ..enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from ..provider import RecommendationProvider
from ..schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


class ClimaRecommendationProvider(RecommendationProvider):
    provider_name = "clima"
    domains = ("AGRICULTURE", "FIELD")

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        if self.session is None or context.unidade_produtiva_id is None:
            return []

        latest = await self._latest_record(context.tenant_id, context.unidade_produtiva_id)
        signal_ids = [signal.signal_id for signal in signals if signal.tenant_id == context.tenant_id]
        if latest is None:
            return [
                self._candidate(
                    context,
                    rule_code="CLIMA_SEM_DADOS_RECENTES",
                    title="Atualizar leitura climática",
                    summary="Não há leitura climática recente para sustentar a operação.",
                    rationale="Sem RegistroClima recente, a decisão operacional climática perde precisão.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.62"),
                    action_label="Revisar clima",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "status": "SEM_DADOS",
                    },
                )
            ]

        thresholds = self._thresholds(context)
        age_days = max((date.today() - latest.data_registro).days, 0)
        candidates: list[RecommendationCandidate] = []

        if age_days >= thresholds["data_max_age_days"]:
            candidates.append(
                self._candidate(
                    context,
                    rule_code="CLIMA_ATUALIZACAO_ATRASADA",
                    title="Janela climática desatualizada",
                    summary="A leitura climática está velha demais para suportar a decisão de campo com segurança.",
                    rationale=f"O último RegistroClima tem {age_days} dias e já ultrapassa a janela operacional configurada.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.70"),
                    action_label="Revisar leitura",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "data_registro": latest.data_registro.isoformat(),
                        "idade_dias": age_days,
                    },
                )
            )

        vento = float(latest.vento_kmh or 0)
        chuva = float(latest.precipitacao_mm or 0)
        temp_max = float(latest.temp_max_c or 0)
        temp_min = float(latest.temp_min_c or 0)
        umidade = float(latest.umidade_rel_pct or 0)

        if vento >= thresholds["vento_alerta_kmh"]:
            candidates.append(
                self._candidate(
                    context,
                    rule_code="CLIMA_JANELA_PULVERIZACAO_DESFAVORAVEL",
                    title="Janela desfavorável para pulverização",
                    summary=f"Vento em {vento:.1f} km/h acima do limite seguro para pulverização.",
                    rationale="A leitura climática oficial mostra vento acima do limiar canônico para aplicação.",
                    priority=RecommendationPriority.URGENT,
                    confidence=Decimal("0.97"),
                    action_label="Aguardar janela",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "vento_kmh": vento,
                        "limite_vento_kmh": thresholds["vento_alerta_kmh"],
                    },
                )
            )

        if chuva >= thresholds["chuva_alerta_mm"]:
            candidates.append(
                self._candidate(
                    context,
                    rule_code="CLIMA_RISCO_OPERACAO_AGRICOLA",
                    title="Risco climático para operação agrícola",
                    summary=f"Precipitação recente de {chuva:.1f} mm pede reavaliação da operação em campo.",
                    rationale="A chuva observada aumenta o risco de atraso, compactação e perda de eficiência operacional.",
                    priority=RecommendationPriority.HIGH,
                    confidence=Decimal("0.92"),
                    action_label="Reprogramar operação",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "precipitacao_mm": chuva,
                        "limite_chuva_mm": thresholds["chuva_alerta_mm"],
                    },
                )
            )

        if temp_max >= thresholds["temp_max_c"] or temp_min <= thresholds["temp_min_c"] or umidade <= thresholds["umidade_min_pct"]:
            candidates.append(
                self._candidate(
                    context,
                    rule_code="CLIMA_RECOMENDACAO_GERAL",
                    title="Rever a operação pela janela climática",
                    summary="Temperatura ou umidade sugerem revisar o tipo de operação antes da execução.",
                    rationale="A janela climática atual está fora do intervalo confortável para operação plena.",
                    priority=RecommendationPriority.NORMAL,
                    confidence=Decimal("0.81"),
                    action_label="Reavaliar",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "temp_max_c": temp_max,
                        "temp_min_c": temp_min,
                        "umidade_rel_pct": umidade,
                        "limites": thresholds,
                    },
                )
            )

        if not candidates:
            candidates.append(
                self._candidate(
                    context,
                    rule_code="CLIMA_CONDICAO_FAVORAVEL",
                    title="Condições climáticas favoráveis",
                    summary="A leitura climática atual não mostra restrições operacionais relevantes.",
                    rationale="Os parâmetros observados permanecem dentro dos limites canônicos do motor climático.",
                    priority=RecommendationPriority.LOW,
                    confidence=Decimal("0.88"),
                    action_label="Prosseguir",
                    action_target=self._target(context.unidade_produtiva_id),
                    source_type=RecommendationSourceType.INDICATOR,
                    source_signal_ids=signal_ids,
                    context_data={
                        "source": "RegistroClima",
                        "data_registro": latest.data_registro.isoformat(),
                        "leitura": {
                            "vento_kmh": vento,
                            "precipitacao_mm": chuva,
                            "temp_max_c": temp_max,
                            "temp_min_c": temp_min,
                            "umidade_rel_pct": umidade,
                        },
                    },
                )
            )

        return candidates

    async def _latest_record(self, tenant_id: UUID, unidade_produtiva_id: UUID) -> RegistroClima | None:
        stmt = (
            select(RegistroClima)
            .where(
                RegistroClima.tenant_id == tenant_id,
                RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
            )
            .order_by(RegistroClima.data_registro.desc(), RegistroClima.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    @staticmethod
    def _thresholds(context: OperationalContext) -> dict[str, float]:
        payload = context.payload or {}
        return {
            "chuva_alerta_mm": float(payload.get("chuva_alerta_mm", ClimaThresholds.CHUVA_ALERTA_MM)),
            "vento_alerta_kmh": float(payload.get("vento_alerta_kmh", ClimaThresholds.VENTO_ALERTA_KMH)),
            "temp_min_c": float(payload.get("temp_min_c", ClimaThresholds.TEMPERATURA_MIN_C)),
            "temp_max_c": float(payload.get("temp_max_c", ClimaThresholds.TEMPERATURA_MAX_C)),
            "umidade_min_pct": float(payload.get("umidade_min_pct", 35.0)),
            "data_max_age_days": float(payload.get("data_max_age_days", 2)),
        }

    @staticmethod
    def _target(unidade_produtiva_id: UUID) -> str:
        return f"/agricola/clima?unidade_produtiva_id={unidade_produtiva_id}"

    def _candidate(
        self,
        context: OperationalContext,
        *,
        rule_code: str,
        title: str,
        summary: str,
        rationale: str,
        priority: RecommendationPriority,
        confidence: Decimal,
        action_label: str,
        action_target: str,
        source_type: RecommendationSourceType,
        source_signal_ids: list[UUID],
        context_data: dict[str, object],
    ) -> RecommendationCandidate:
        return RecommendationCandidate(
            tenant_id=context.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            domain=RecommendationDomain.AGRICULTURE,
            priority=priority,
            source_type=source_type,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name=self.provider_name,
            rule_code=rule_code,
            scope_type=context.scope_type,
            scope_id=context.scope_id,
            title=title,
            summary=summary,
            rationale=rationale,
            dedupe_key=self._dedupe_key(context, rule_code),
            source_signal_ids=source_signal_ids,
            confidence=confidence,
            action_label=action_label,
            action_target=action_target,
            context={
                **context_data,
                "generated_at": context.generated_at.isoformat(),
            },
        )

    @staticmethod
    def _dedupe_key(context: OperationalContext, rule_code: str) -> str:
        unidade = context.unidade_produtiva_id or "tenant"
        return f"clima:{context.tenant_id}:{unidade}:{rule_code}"
