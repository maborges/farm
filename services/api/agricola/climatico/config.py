class ClimaThresholds:
    """
    Configurações canônicas de limites climáticos.
    Garante consistência entre a geração de alertas (AlertEngine)
    e a emissão de recomendações (RecommendationEngine).
    """
    CHUVA_ALERTA_MM = 10.0
    VENTO_ALERTA_KMH = 25.0
    TEMPERATURA_MIN_C = 5.0
    TEMPERATURA_MAX_C = 35.0
