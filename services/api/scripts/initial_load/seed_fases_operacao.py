"""Tipos de operação e fases permitidas do catálogo de referência."""

# (id, tipo de operação, fases permitidas, descrição)
OPERATION_PHASES = (
    (
        "35c1591a-c5d6-440e-be78-ea21b2edda25",
        "ADUBAÇÃO",
        ["PREPARO_SOLO", "DESENVOLVIMENTO"],
        "Adubação de base ou cobertura",
    ),
    (
        "60089547-6dd2-4681-82b9-ab449e65c228",
        "CALAGEM",
        ["PREPARO_SOLO"],
        "Aplicação de calcário",
    ),
    (
        "8d1ad33c-d147-49c3-b5a2-be7e55d2329f",
        "COLHEITA",
        ["COLHEITA"],
        "Colheita manual ou mecanizada",
    ),
    (
        "9caddf2b-cb1f-4c98-8a5c-fe6fb8851bce",
        "IRRIGAÇÃO",
        ["DESENVOLVIMENTO", "COLHEITA"],
        "Operações de irrigação",
    ),
    (
        "b53ead9b-6ff6-49fb-884b-a969cf992972",
        "OPERAÇÃO_MECANIZADA",
        ["PLANTIO", "DESENVOLVIMENTO"],
        "Operações gerais com máquinas e implementos",
    ),
    (
        "f3ff4633-fc3d-4a18-8636-dbad525c1823",
        "OUTROS",
        ["PLANEJADA", "PREPARO_SOLO", "PLANTIO", "DESENVOLVIMENTO", "COLHEITA", "POS_COLHEITA"],
        "Outras operações de campo",
    ),
    (
        "0db4f455-7064-4742-970a-834ca798a9f2",
        "PLANTIO",
        ["PLANTIO", "DESENVOLVIMENTO"],
        "Semeadura e plantio",
    ),
    (
        "bcc1275c-a3fc-429d-81fd-6148859d2993",
        "PREPARO_SOLO",
        ["PREPARO_SOLO"],
        "Aração, gradagem, subsolagem e preparo de área",
    ),
    (
        "e5ce554d-9e54-4f56-9c7c-8aa65ac437bc",
        "PULVERIZAÇÃO",
        ["PLANEJADA", "DESENVOLVIMENTO", "COLHEITA"],
        "Aplicação de defensivos ou bioinsumos",
    ),
)
