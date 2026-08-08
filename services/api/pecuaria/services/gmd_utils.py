def calcular_gmd(peso_atual: float, peso_anterior: float, dias: int) -> float | None:
    """Ganho médio diário entre duas pesagens: (peso_atual - peso_anterior) / dias.
    Retorna None se o intervalo não for positivo (evita divisão por zero/negativa)."""
    if dias <= 0:
        return None
    return round((float(peso_atual) - float(peso_anterior)) / dias, 3)
