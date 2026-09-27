"""Valores canônicos de `CostAllocation.source` (OPERATIONS-GAP-01 §21.27).

`CostAllocation` (agricola/custos/models.py) é o hub unificado de custo por
ProductionUnit — hoje já cobre agrícola, frota, RH/mão de obra, pecuária e
overhead financeiro rateado, discriminados pelo campo `source` (String livre,
sem enum de banco). Esta lista centraliza os valores usados pelos produtores
reais (`agricola/custos/allocation_service.py`,
`agricola/custos/operational_cost_service.py`, `agricola/operacoes/service.py`,
`pecuaria/services/manejo_sync_service.py`, `operacional/services/estoque_service.py`)
para evitar que um novo `source` seja introduzido divergente do existente.

Regra crítica de consumo (nunca somar duas vezes a mesma despesa):
`FIN_RATEIO` é uma *projeção* de `financeiro.models.rateio.Rateio` dentro de
`CostAllocation` (ver `registrar_allocations_fin_rateio`). Qualquer relatório
que já soma `Rateio` diretamente (ex.: `financeiro/services/relatorio_service.py`,
Centro de Custos financeiro) NUNCA deve também somar
`CostAllocation.source == FIN_RATEIO` — seria a mesma despesa contada duas vezes.
O DRE agrícola (`agricola/dre/service.py`) soma apenas `CostAllocation`
(todas as origens, incluindo `FIN_RATEIO`), nunca `Rateio` diretamente.
"""

OPERATION_EXECUTION = "OPERATION_EXECUTION"
PECUARIA_VACINACAO = "PECUARIA_VACINACAO"
PERDA_ESTOQUE = "PERDA_ESTOQUE"
REQUISICAO_CONSUMO = "REQUISICAO_CONSUMO"
FIN_RATEIO = "FIN_RATEIO"

FROTA_COMBUSTIVEL = "FROTA_COMBUSTIVEL"
FROTA_PECAS = "FROTA_PECAS"
FROTA_MANUTENCAO = "FROTA_MANUTENCAO"
FROTA_APONTAMENTO = "FROTA_APONTAMENTO"

RH_DIARIA = "RH_DIARIA"
RH_EMPREITADA = "RH_EMPREITADA"

DEPRECIACAO_EQUIPAMENTO = "DEPRECIACAO_EQUIPAMENTO"
DEPRECIACAO_BENFEITORIA = "DEPRECIACAO_BENFEITORIA"

KNOWN_SOURCES = frozenset(
    {
        OPERATION_EXECUTION,
        PECUARIA_VACINACAO,
        PERDA_ESTOQUE,
        REQUISICAO_CONSUMO,
        FIN_RATEIO,
        FROTA_COMBUSTIVEL,
        FROTA_PECAS,
        FROTA_MANUTENCAO,
        FROTA_APONTAMENTO,
        RH_DIARIA,
        RH_EMPREITADA,
        DEPRECIACAO_EQUIPAMENTO,
        DEPRECIACAO_BENFEITORIA,
    }
)
