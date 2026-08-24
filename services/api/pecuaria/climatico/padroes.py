"""Padrões climáticos iniciais para modelos zoossanitários globais.

Os limiares são referências ambientais para triagem preventiva. Não substituem
avaliação veterinária nem medições do microclima das instalações.
"""

PADROES_ESTRESSE_TERMICO = {
    "Suíno": {
        "nivel_medio": 68,
        "nivel_alto": 74,
        "nivel_critico": 78,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "UMN Extension: Heat stress in swine affects production",
        "fonte_url": "https://extension.umn.edu/agriculture/animals-and-livestock/swine/heat-stress-swine-affects-production",
        "observacao": "Limiar preventivo convertido para ITH clássico; idade, peso e fase produtiva alteram a resposta.",
    },
    "Aves de Corte": {
        "nivel_medio": 76,
        "nivel_alto": 80,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "PMC: An acute, rather than progressive, increase of THI has severe effects in laying hens",
        "fonte_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7674306/",
        "observacao": "Referência preventiva para aves adultas; idade, linhagem, densidade e ventilação devem ser consideradas.",
    },
    "Aves de Postura": {
        "nivel_medio": 76,
        "nivel_alto": 80,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "PMC: An acute, rather than progressive, increase of THI has severe effects in laying hens",
        "fonte_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7674306/",
        "observacao": "A produção e a mortalidade respondem também à umidade; monitorar ofegação e consumo de água.",
    },
    "Bubalino": {
        "nivel_medio": 75,
        "nivel_alto": 80,
        "nivel_critico": 85,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "Acta Amazonica: bioclimatologia de búfalas Murrah",
        "fonte_url": "https://acta.inpa.gov.br/fasciculos/41-3/BODY/v41n3a14.html",
        "observacao": "Acesso à sombra e à água é determinante; o ITGU pode ser mais adequado quando houver radiação/globo.",
    },
    "Asinino": {
        "nivel_medio": 72,
        "nivel_alto": 78,
        "nivel_critico": 83,
        "indice": "ITH_CLÁSSICO",
        "fonte_parametros": "PubMed: rectal temperature responses of donkeys under heat and packing stress",
        "fonte_url": "https://pubmed.ncbi.nlm.nih.gov/22869338/",
        "observacao": "Triagem ambiental conservadora; trabalho, transporte e aclimatação podem elevar o risco antes do limiar.",
    },
}
