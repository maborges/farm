"""Sugestões globais de serviços terceirizados."""

# `unidade_medida` é texto no modelo, sem FK para `unidades_medida`. Os códigos
# DIA, KM e SC são opções próprias do cadastro de serviços e estão na tela.
# (id, nome, unidade, custo de referência, observações)
SERVICE_TYPES = (
    (
        "accb8d5d-9870-4164-96aa-a64b7bc83de1",
        "Adubação terceirizada",
        "HA",
        None,
        None,
    ),
    (
        "628eb423-9ea5-4508-b06b-76be557c2423",
        "Aplicação aérea (avião/drone) terceirizada",
        "HA",
        None,
        None,
    ),
    (
        "719c2dae-121e-409b-b258-526a7648a260",
        "Aplicação terrestre (pulverização) terceirizada",
        "HA",
        None,
        None,
    ),
    (
        "a80447eb-9f90-40c0-8247-424ce2ac45b3",
        "Calagem/distribuição de calcário terceirizada",
        "HA",
        None,
        None,
    ),
    (
        "2416ec16-0c2a-46f8-9f5e-61ccb0856e13",
        "Colheita manual (turma terceirizada)",
        "DIA",
        None,
        None,
    ),
    (
        "7ed77a88-aa50-43de-9de1-de5e2ae2195b",
        "Colheita mecanizada terceirizada",
        "HA",
        None,
        None,
    ),
    (
        "a7803e46-ad2b-4d1d-9104-7cb368b45783",
        "Gradagem/preparo de solo terceirizado",
        "HA",
        None,
        None,
    ),
    (
        "2aa74af6-af81-403c-9cb1-4a7d2153977f",
        "Plantio terceirizado",
        "HA",
        None,
        None,
    ),
    (
        "e692a101-c40e-4ad0-8e1f-c116c56524cf",
        "Secagem/armazenagem terceirizada",
        "SC",
        None,
        None,
    ),
    (
        "d9f02a67-df12-4901-990b-4571a4820b13",
        "Transporte de grãos/insumos (frete terceirizado)",
        "KM",
        None,
        None,
    ),
)
