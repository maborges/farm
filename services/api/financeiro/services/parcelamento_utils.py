from decimal import Decimal, ROUND_HALF_UP


def calcular_parcelas(valor_total: float, total_parcelas: int) -> list[float]:
    """
    Divide o valor total em parcelas com centavos corretos.
    A diferença de arredondamento vai para a última parcela.
    """
    valor_dec = Decimal(str(valor_total))
    parcela_base = (valor_dec / total_parcelas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    parcelas = [float(parcela_base)] * total_parcelas
    diferenca = float(valor_dec - parcela_base * total_parcelas)
    if diferenca != 0:
        parcelas[-1] = round(parcelas[-1] + diferenca, 2)
    return parcelas
