# 03 — Arquitetura e Domínio

## Boundary

O módulo é dono do protocolo de qualidade, critérios, amostras, medições, avaliações, ajustes e aprovações. Ele consome entidades de produção, estoque e comercialização por referência.

## Entidades propostas

| Entidade | Responsabilidade |
|---|---|
| `QualityProtocol` | Protocolo versionado por commodity e contexto |
| `QualityCriterion` | Parâmetro, tipo, unidade e limites |
| `QualityClass` | Classe comercial resultante |
| `QualitySample` | Amostra, origem, método e cadeia de custódia |
| `QualityMeasurement` | Valor aferido por critério |
| `QualityReport` | Laudo/avaliação de um lote |
| `QualityClassification` | Resultado calculado e explicação |
| `QualityAdjustment` | Desconto, prêmio ou bloqueio derivado |
| `QualityApproval` | Revisão e decisão do responsável |
| `QualityEquipmentCalibration` | Calibração e validade do instrumento |
| `QualityNonConformity` | Divergência, contestação ou reanálise |

## Ownership obrigatório

- commodity: `cadastros_commodities`;
- produto/insumo: `cadastros_produtos`;
- cultura: `cadastros_culturas`;
- propriedade/talhão: `production_units` e `cadastros_areas_rurais`;
- lote colhido: `agricola_produtos_colhidos`;
- lote beneficiado: `agricola_lotes_beneficiamento`;
- lote de estoque: `estoque_lotes`;
- financeiro: `fin_receitas` e `fin_despesas`.

Antes da implementação, `operacional_qualidade_laudos`, `operacional_qualidade_protocolos` e `operacional_qualidade_ajustes` devem ser classificados como fonte canônica, extensão ou legado. Não criar duplicatas sem decisão arquitetural.

## Estados do laudo

`RASCUNHO → EM_ANALISE → PENDENTE_REVISAO → APROVADO | REPROVADO | CANCELADO`

Após `APROVADO` ou `REPROVADO`, medições e resultado não são sobrescritos. Uma reanálise cria nova versão relacionada.

## Eventos

- `quality.protocol.published`
- `quality.sample.registered`
- `quality.measurement.recorded`
- `quality.report.evaluated`
- `quality.classification.approved`
- `quality.classification.rejected`
- `quality.adjustment.calculated`
- `quality.lot.blocked`
- `quality.report.reanalyzed`
- `quality.equipment.calibration.expired`
