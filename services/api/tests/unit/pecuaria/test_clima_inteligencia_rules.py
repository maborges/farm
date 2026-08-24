from pecuaria.climatico.service import InteligenciaPecuariaService
from types import SimpleNamespace


def test_ith_classico() -> None:
    ith = InteligenciaPecuariaService._calcular_ith(30.0, 70.0)
    assert round(ith, 2) == 81.32


def test_ith_responde_a_umidade() -> None:
    baixo = InteligenciaPecuariaService._calcular_ith(30.0, 40.0)
    alto = InteligenciaPecuariaService._calcular_ith(30.0, 80.0)
    assert alto > baixo


def test_alerta_de_atualizacao_climatica() -> None:
    alertas = InteligenciaPecuariaService._gerar_alertas(3, 70.0)
    assert any("desatualizados" in alerta for alerta in alertas)


def test_alerta_de_tendencia_termica() -> None:
    alertas = InteligenciaPecuariaService._gerar_alertas(0, 78.0)
    assert any("alto ou crítico" in alerta for alerta in alertas)


def test_previsao_sem_umidade_nao_inventa_ith() -> None:
    previsao = SimpleNamespace(
        data_previsao=__import__("datetime").date.today(),
        temp_max_c=32,
        periodos=[{"temperatura_c": 32, "umidade_pct": None}],
    )
    resumo = InteligenciaPecuariaService._resumo_dia(previsao, (82, 78, 72))
    assert resumo["ith_max"] is None
    assert resumo["risco"] == "INDETERMINADO"


def test_previsao_calcula_duracao_e_janela_de_manejo() -> None:
    periodos = [
        {"horario": "2026-08-24 06:00:00", "temperatura_c": 22, "umidade_pct": 60, "probabilidade_chuva_pct": 10, "vento_kmh": 8},
        {"horario": "2026-08-24 12:00:00", "temperatura_c": 30, "umidade_pct": 80, "probabilidade_chuva_pct": 10, "vento_kmh": 8},
    ]
    resumo = InteligenciaPecuariaService._resumo_estresse(periodos, (82, 78, 72))
    janela = InteligenciaPecuariaService._janela_manejo(periodos, (82, 78, 72))
    assert resumo["duracao_horas"] == 3
    assert janela["status"] == "RECOMENDADA"
