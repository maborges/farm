"""Padrões climáticos iniciais para modelos zoossanitários globais.

Os limiares são referências ambientais baseadas no Índice de Temperatura e
Umidade (ITH clássico) para triagem preventiva. Não substituem avaliação
veterinária nem medições do microclima das instalações.
"""

PADROES_ESTRESSE_TERMICO: dict[str, dict[str, int | str]] = {
    "Bovino de Leite": {
        "nivel_medio": 72,
        "nivel_alto": 78,
        "nivel_critico": 82,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Gado de Leite",
        "fonte_url": "https://www.embrapa.br/gado-de-leite",
        "observacao": (
            "Vacas leiteiras de alta produção apresentam redução do consumo de "
            "matéria seca e queda produtiva a partir de ITH 72."
        ),
    },
    "Bovino de Corte": {
        "nivel_medio": 75,
        "nivel_alto": 80,
        "nivel_critico": 85,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Gado de Corte",
        "fonte_url": "https://www.embrapa.br/gado-de-corte",
        "observacao": (
            "Bovinos de corte em pastejo ou confinamento demandam sombra e água "
            "abundante quando o ITH atinge faixa moderada a crítica."
        ),
    },
    "Ovino": {
        "nivel_medio": 74,
        "nivel_alto": 79,
        "nivel_critico": 84,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Caprinos e Ovinos",
        "fonte_url": "https://www.embrapa.br/caprinos-e-ovinos",
        "observacao": (
            "Ovinos ativam aumento de frequência respiratória em estresse térmico; "
            "evitar manejo de lote em horários de pico calórico."
        ),
    },
    "Caprino": {
        "nivel_medio": 75,
        "nivel_alto": 80,
        "nivel_critico": 85,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Caprinos e Ovinos",
        "fonte_url": "https://www.embrapa.br/caprinos-e-ovinos",
        "observacao": (
            "Caprinos têm boa adaptação ao calor, mas sofrem queda reprodutiva e "
            "de ingestão sob radiação intensa e umidade elevada."
        ),
    },
    "Equino": {
        "nivel_medio": 72,
        "nivel_alto": 78,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Pantanal (Equideocultura)",
        "fonte_url": "https://www.embrapa.br/pantanal",
        "observacao": (
            "Equinos dependem da sudorese evaporativa; sob umidade alta, "
            "restringir trabalho intenso e garantir hidratação e sombra."
        ),
    },
    "Suíno": {
        "nivel_medio": 68,
        "nivel_alto": 74,
        "nivel_critico": 78,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Suínos e Aves",
        "fonte_url": "https://www.embrapa.br/suinos-e-aves",
        "observacao": (
            "Suínos possuem glândulas sudoríparas pouco funcionais e são altamente "
            "sensíveis ao calor em terminação e lactação."
        ),
    },
    "Aves de Corte": {
        "nivel_medio": 76,
        "nivel_alto": 80,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Suínos e Aves",
        "fonte_url": "https://www.embrapa.br/suinos-e-aves",
        "observacao": (
            "Frangos de corte em fase final requerem ventilação e resfriamento "
            "evaporativo preventivos antes que o ITH alcance faixa crítica."
        ),
    },
    "Aves de Postura": {
        "nivel_medio": 76,
        "nivel_alto": 80,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Suínos e Aves",
        "fonte_url": "https://www.embrapa.br/suinos-e-aves",
        "observacao": (
            "Poedeiras comerciais reduzem postura e qualidade de casca sob "
            "estresse térmico prolongado."
        ),
    },
    "Bubalino": {
        "nivel_medio": 75,
        "nivel_alto": 80,
        "nivel_critico": 85,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Amazônia Oriental (Bubalinocultura)",
        "fonte_url": "https://www.embrapa.br/amazonia-oriental",
        "observacao": (
            "Bubalinos têm menor densidade de glândulas sudoríparas e pele escura, "
            "exigindo acesso a sombra ou áreas de imersão."
        ),
    },
    "Asinino": {
        "nivel_medio": 72,
        "nivel_alto": 78,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Embrapa Semiárido",
        "fonte_url": "https://www.embrapa.br/semiarido",
        "observacao": (
            "Asininos apresentam boa tolerância térmica em repouso, porém exigem "
            "sombra e hidratação em manejo sob calor e umidade elevados."
        ),
    },
}
