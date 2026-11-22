"""Guardrails determinísticos de normalização, evidência literal e banda estatística."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .contracts import CANONICAL_COMMODITY_IDS, VALID_UFS, RawObservation, ValidatedObservation

BLOCKING_FLAGS: frozenset[str] = frozenset(
    {
        "FLAG_COMMODITY_INVALIDA",
        "FLAG_UF_INVALIDA",
        "FLAG_VALOR_INVALIDO",
        "FLAG_DATA_FUTURA",
        "FLAG_OUTLIER",
        "FLAG_EVIDENCIA_NAO_CONFERE",
    }
)

_ONE = Decimal("1.000000")
_CENT = Decimal("0.01")
_WEIGHT_KG_PER_UNIT: dict[str, Decimal] = {
    "kg": Decimal("1"),
    "arroba_15kg": Decimal("15"),
    "sc_25kg": Decimal("25"),
    "sc_40kg": Decimal("40"),
    "sc_50kg": Decimal("50"),
    "sc_60kg": Decimal("60"),
    "cx_20kg": Decimal("20"),
    "t": Decimal("1000"),
}


def canonicalize_unit_token(unidade: str) -> str:
    """Mapeia descrições heterogêneas de unidade para chave canônica determinística.

    Args:
        unidade: Texto de unidade original (ex: ``sc.60 kg``, ``@``, ``Saca de 60 kg``).

    Returns:
        Chave canônica da unidade para cálculo seguro de fator de conversão.
    """
    low = re.sub(r"\s+", " ", str(unidade or "").strip().lower())
    if low in {"@", "arroba", "arroba (15 kg)", "r$/@", "r$/arroba", "15 kg"}:
        return "arroba_15kg"
    if any(k in low for k in ("60 kg", "60kg", "sc.60", "sc 60")):
        return "sc_60kg"
    if any(k in low for k in ("50 kg", "50kg", "sc.50", "sc 50")):
        return "sc_50kg"
    if any(k in low for k in ("40 kg", "40kg", "sc.40", "sc 40")):
        return "sc_40kg"
    if any(k in low for k in ("25 kg", "25kg", "sc.25", "sc 25")):
        return "sc_25kg"
    if any(k in low for k in ("20 kg", "20kg", "cx.20", "cx 20")):
        return "cx_20kg"
    if any(k in low for k in ("tonelada", "t/ha")) or low in {"t", "ton", "r$/t"}:
        return "t"
    if any(k in low for k in ("quilograma", "r$/kg")) or low in {"kg", "quilo"}:
        return "kg"
    if "litro" in low or low in {"l", "r$/l"}:
        return "l"
    if "dúzia" in low or "duzia" in low or low in {"dz", "dúzia", "duzia"}:
        return "dz"
    if "cabeça" in low or "cabeca" in low or "cab" in low:
        return "cabeca"
    return f"raw:{low}"


def normalize_unit_value(
    valor: Decimal,
    unidade_origem: str,
    unidade_destino: str,
) -> tuple[Decimal, Decimal, str | None]:
    """Converte preço unitário entre unidades compatíveis com precisão decimal ``HALF_UP``.

    Args:
        valor: Valor monetário numérico original.
        unidade_origem: Unidade extraída da fonte (ex: ``kg``, ``@``, ``sc.60 kg``).
        unidade_destino: Unidade canônica alvo (ex: ``Saca de 60 kg``).

    Returns:
        Tupla ``(valor_normalizado, fator_conversao, descricao_transformacao)``.
    """
    origem_key = canonicalize_unit_token(unidade_origem)
    destino_key = canonicalize_unit_token(unidade_destino)
    if origem_key == destino_key:
        norm = valor.quantize(_CENT, rounding=ROUND_HALF_UP)
        desc = (
            "Arredondamento decimal HALF_UP para 2 casas"
            if norm != valor
            else None
        )
        return norm, _ONE, desc

    origem_kg = _WEIGHT_KG_PER_UNIT.get(origem_key)
    destino_kg = _WEIGHT_KG_PER_UNIT.get(destino_key)
    if origem_kg is not None and destino_kg is not None:
        fator = (destino_kg / origem_kg).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        convertido = (valor * fator).quantize(_CENT, rounding=ROUND_HALF_UP)
        desc = (
            f"Conversão de unidade {unidade_origem} -> {unidade_destino} "
            f"(fator x{fator.normalize()}, HALF_UP)"
        )
        return convertido, fator, desc

    norm = valor.quantize(_CENT, rounding=ROUND_HALF_UP)
    return norm, _ONE, None


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip().casefold()


def verify_literal_evidence(trecho_evidencia: str, raw_text: str) -> bool:
    """Confere se o trecho de evidência extraído existe literalmente no texto de origem.

    Args:
        trecho_evidencia: Trecho literal atribuído à observação.
        raw_text: Texto bruto extraído do HTML, XLS ou PDF.

    Returns:
        ``True`` se houver correspondência literal após normalização de espaços e entidades.
    """
    needle = _normalize_whitespace(trecho_evidencia)
    haystack = _normalize_whitespace(raw_text)
    if not needle or not haystack:
        return False
    return needle in haystack


def _compute_variation(
    atual: Decimal,
    anterior: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    if anterior is None or anterior <= 0:
        return None, None
    diff_abs = (atual - anterior).quantize(_CENT, rounding=ROUND_HALF_UP)
    diff_pct = ((diff_abs / anterior) * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return diff_abs, diff_pct


def validate_observation(
    obs: RawObservation,
    *,
    previous_valor: Decimal | None,
    max_variacao_pct: Decimal,
    max_defasagem_dias: int,
    today: date | None = None,
    raw_text: str | None = None,
) -> ValidatedObservation:
    """Executa todos os guardrails determinísticos em uma observação bruta.

    Args:
        obs: Observação extraída pelo coletor.
        previous_valor: Último valor publicado para comparação estatística (ou ``None``).
        max_variacao_pct: Banda percentual máxima antes de quarentena.
        max_defasagem_dias: Idade máxima sem marcar defasagem.
        today: Data de referência opcional para testes determinísticos.
        raw_text: Texto completo da fonte para verificação literal de evidência.

    Returns:
        ``ValidatedObservation`` pronta para publicação ou quarentena.
    """
    ref_today = today or datetime.now(timezone.utc).date()  # noqa: UP017
    flags: list[str] = []

    if obs.commodity_id not in CANONICAL_COMMODITY_IDS:
        flags.append("FLAG_COMMODITY_INVALIDA")
    if obs.uf.upper() not in VALID_UFS:
        flags.append("FLAG_UF_INVALIDA")

    unidade_alvo = obs.unidade_destino or obs.unidade_original
    try:
        val_norm, fator, transformacao = normalize_unit_value(
            obs.valor_original, obs.unidade_original, unidade_alvo
        )
    except (InvalidOperation, ArithmeticError):
        val_norm = Decimal("0")
        fator = _ONE
        transformacao = None
        flags.append("FLAG_VALOR_INVALIDO")

    if val_norm <= 0 or not val_norm.is_finite():
        flags.append("FLAG_VALOR_INVALIDO")
    if obs.data_referencia > ref_today + timedelta(days=1):
        flags.append("FLAG_DATA_FUTURA")
    if (ref_today - obs.data_referencia).days > max_defasagem_dias:
        flags.append("FLAG_DEFASADO")

    var_abs, var_pct = _compute_variation(val_norm, previous_valor)
    if var_pct is not None and abs(var_pct) > max_variacao_pct:
        flags.append("FLAG_OUTLIER")
    if raw_text is not None and not verify_literal_evidence(obs.trecho_evidencia, raw_text):
        flags.append("FLAG_EVIDENCIA_NAO_CONFERE")

    bloqueado = any(flag in BLOCKING_FLAGS for flag in flags)
    return ValidatedObservation(
        raw=obs,
        valor_normalizado=val_norm,
        unidade_normalizada=unidade_alvo,
        fator_conversao=fator,
        transformacao_aplicada=transformacao,
        flags_anomalia=flags,
        bloqueado_para_publicacao=bloqueado,
        variacao_anterior_abs=var_abs,
        variacao_anterior_pct=var_pct,
    )
