"""Cálculos padronizados de arroba de carcaça, UA e métricas econômicas."""

from __future__ import annotations

from dataclasses import dataclass

RENDIMENTO_CARCACA_PADRAO_PCT = 50.0
KG_POR_ARROBA_CARCACA = 15.0
KG_POR_UA = 450.0


@dataclass(frozen=True)
class EntradaEconomicaArroba:
    """Parâmetros consolidados para cálculo econômico de lote ou rebanho."""

    peso_vivo_kg: float
    peso_inicial_kg: float | None
    rendimento_carcaca_pct: float
    quantidade_animais: int
    custo_aquisicao: float
    custo_sanitario: float
    custo_nutricao: float
    custo_outros: float
    cotacao_arroba: float | None = None


@dataclass(frozen=True)
class MetricasEconomicasArroba:
    """Indicadores econômicos padronizados em função da arroba de carcaça."""

    arrobas_totais: float
    arrobas_produzidas: float
    custo_total_operacional: float
    custo_sanitario_por_arroba: float
    custo_total_por_arroba: float
    custo_por_arroba_produzida: float
    custo_break_even_por_arroba: float
    valor_mercado_estimado: float | None
    margem_bruta_estimada: float | None
    margem_estimada_por_cabeca: float | None


def normalizar_rendimento_carcaca(rendimento_pct: float | None) -> float:
    """Valida e retorna o rendimento de carcaça efetivo em percentual.

    Args:
        rendimento_pct: Percentual de rendimento de carcaça ou None para padrão 50%.

    Returns:
        Rendimento válido no intervalo (0, 100].

    Raises:
        ValueError: Quando o rendimento informado é <= 0 ou > 100.
    """
    if rendimento_pct is None:
        return RENDIMENTO_CARCACA_PADRAO_PCT
    valor = float(rendimento_pct)
    if valor <= 0 or valor > 100:
        raise ValueError("Rendimento de carcaça deve ser maior que 0 e menor ou igual a 100%.")
    return valor


def calcular_arrobas_carcaca(
    peso_vivo_kg: float,
    rendimento_carcaca_pct: float = RENDIMENTO_CARCACA_PADRAO_PCT,
) -> float:
    """Converte peso vivo em arrobas de carcaça equivalentes.

    Args:
        peso_vivo_kg: Peso vivo total em quilogramas.
        rendimento_carcaca_pct: Rendimento de carcaça em % (padrão 50%).

    Returns:
        Quantidade de arrobas de carcaça (15 kg por arroba).

    Raises:
        ValueError: Quando o rendimento informado for inválido.
    """
    rendimento = normalizar_rendimento_carcaca(rendimento_carcaca_pct)
    if peso_vivo_kg <= 0:
        return 0.0
    peso_carcaca = float(peso_vivo_kg) * (rendimento / 100.0)
    return peso_carcaca / KG_POR_ARROBA_CARCACA


def calcular_arrobas_produzidas(
    peso_atual_kg: float,
    peso_inicial_kg: float | None,
    rendimento_carcaca_pct: float = RENDIMENTO_CARCACA_PADRAO_PCT,
) -> float:
    """Calcula apenas as arrobas ganhas sobre o peso inicial registrado.

    Args:
        peso_atual_kg: Peso vivo total atual em quilogramas.
        peso_inicial_kg: Peso vivo total inicial em quilogramas.
        rendimento_carcaca_pct: Rendimento de carcaça em % (padrão 50%).

    Returns:
        Arrobas de carcaça ganhas (mínimo zero).

    Raises:
        ValueError: Quando o rendimento informado for inválido.
    """
    rendimento = normalizar_rendimento_carcaca(rendimento_carcaca_pct)
    if peso_inicial_kg is None or peso_atual_kg <= peso_inicial_kg:
        return 0.0
    ganho_vivo = float(peso_atual_kg) - float(peso_inicial_kg)
    return calcular_arrobas_carcaca(ganho_vivo, rendimento)


def calcular_ua_por_peso(peso_vivo_kg: float, quantidade_cabecas: int) -> float:
    """Calcula Unidades Animais (1 UA = 450 kg) com fallback para animais sem pesagem.

    Args:
        peso_vivo_kg: Peso vivo agregado em quilogramas.
        quantidade_cabecas: Total de cabeças ativas.

    Returns:
        Equivalente em Unidades Animais (UA) arredondado a 2 casas decimais.
    """
    if peso_vivo_kg > 0:
        return round(float(peso_vivo_kg) / KG_POR_UA, 2)
    return round(max(0, int(quantidade_cabecas)) * 0.5, 2)


def _custo_unitario(custo: float, divisor: float) -> float:
    """Divide custo pelo divisor com proteção contra zero."""
    if divisor <= 0 or custo <= 0:
        return 0.0
    return round(custo / divisor, 4)


def _calcular_mercado(
    arrobas_exatas: float,
    custo_investido: float,
    entrada: EntradaEconomicaArroba,
) -> tuple[float | None, float | None, float | None]:
    """Calcula valor de mercado estimado e margens quando há cotação válida."""
    if entrada.cotacao_arroba is None or entrada.cotacao_arroba <= 0 or arrobas_exatas <= 0:
        return None, None, None
    valor_mercado = round(arrobas_exatas * float(entrada.cotacao_arroba), 2)
    margem_bruta = round(valor_mercado - custo_investido, 2)
    margem_cab = (
        round(margem_bruta / entrada.quantidade_animais, 2)
        if entrada.quantidade_animais > 0
        else None
    )
    return valor_mercado, margem_bruta, margem_cab


def calcular_metricas_economicas_arroba(
    entrada: EntradaEconomicaArroba,
) -> MetricasEconomicasArroba:
    """Consolida arrobas, custos unitários, break-even e valor estimado de mercado.

    Args:
        entrada: Dados zootécnicos, custos e cotação de referência.

    Returns:
        MetricasEconomicasArroba preenchidas e consistentes.

    Raises:
        ValueError: Se o rendimento de carcaça estiver fora do intervalo válido.
    """
    arrobas_exatas = calcular_arrobas_carcaca(entrada.peso_vivo_kg, entrada.rendimento_carcaca_pct)
    produzidas_exatas = calcular_arrobas_produzidas(
        entrada.peso_vivo_kg, entrada.peso_inicial_kg, entrada.rendimento_carcaca_pct
    )
    operacional = float(entrada.custo_sanitario) + float(entrada.custo_nutricao) + float(entrada.custo_outros)
    custo_investido = float(entrada.custo_aquisicao) + operacional
    valor_mercado, margem_bruta, margem_cab = _calcular_mercado(
        arrobas_exatas, custo_investido, entrada
    )
    return MetricasEconomicasArroba(
        arrobas_totais=round(arrobas_exatas, 2),
        arrobas_produzidas=round(produzidas_exatas, 2),
        custo_total_operacional=round(operacional, 2),
        custo_sanitario_por_arroba=_custo_unitario(entrada.custo_sanitario, arrobas_exatas),
        custo_total_por_arroba=_custo_unitario(operacional, arrobas_exatas),
        custo_por_arroba_produzida=_custo_unitario(operacional, produzidas_exatas),
        custo_break_even_por_arroba=_custo_unitario(custo_investido, arrobas_exatas),
        valor_mercado_estimado=valor_mercado,
        margem_bruta_estimada=margem_bruta,
        margem_estimada_por_cabeca=margem_cab,
    )
