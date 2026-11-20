from pecuaria.climatico.padroes import PADROES_ESTRESSE_TERMICO


ESPECIES_CANONICAS = {
    "Bovino de Leite",
    "Bovino de Corte",
    "Ovino",
    "Caprino",
    "Equino",
    "Suíno",
    "Aves de Corte",
    "Aves de Postura",
    "Bubalino",
    "Asinino",
}


def test_especies_canonicas_possuem_limites_e_fontes_validas() -> None:
    assert set(PADROES_ESTRESSE_TERMICO.keys()) == ESPECIES_CANONICAS
    for regras in PADROES_ESTRESSE_TERMICO.values():
        assert 0 < regras["nivel_medio"] < regras["nivel_alto"] < regras["nivel_critico"] < 100
        assert regras["indice"] == "ITH_CLÁSSICO"
        assert regras["fonte_parametros"]
        assert regras["fonte_url"].startswith("https://")
        assert regras["observacao"]

