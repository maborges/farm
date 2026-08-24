from pecuaria.climatico.padroes import PADROES_ESTRESSE_TERMICO


def test_especies_adicionais_possuem_limites_validos() -> None:
    esperadas = {"Suíno", "Aves de Corte", "Aves de Postura", "Bubalino", "Asinino"}
    assert esperadas.issubset(PADROES_ESTRESSE_TERMICO)
    for regras in PADROES_ESTRESSE_TERMICO.values():
        assert 0 < regras["nivel_medio"] < regras["nivel_alto"] < regras["nivel_critico"] < 100
        assert regras["fonte_parametros"]
        assert regras["fonte_url"].startswith("https://")
