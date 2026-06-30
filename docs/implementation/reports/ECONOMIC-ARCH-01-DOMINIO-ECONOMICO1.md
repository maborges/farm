# ECONOMIC-ARCH-01 — Relatório curto

## Resultado

Auditoria concluída sem alteração de código, migrations, endpoints, models ou cálculos.

Classificação final: **Modelo C**.

## Resposta objetiva

O AgroSaaS **já possui** uma arquitetura econômica canônica identificável:

- receita operacional: `Receita`
- despesa/obrigação: `Despesa`
- custo operacional apropriado: `CostAllocation`
- DRE oficial: `agricola.dre.v1`
- rentabilidade oficial: `agricola.rentabilidade.v1`
- fluxo de caixa oficial: `RelatorioService.fluxo_caixa()` sobre `Receita` e `Despesa`

Mas essa arquitetura **ainda não é a única em execução**.

## Principais caminhos paralelos ainda ativos

- DRE legada baseada em `LancamentoFinanceiro`
- custo de estoque gerando `LancamentoFinanceiro`
- fallback de custos agrícolas por `OperacaoAgricola.custo_total`
- `RomaneioColheita` gerando `Receita`
- `ComercializacaoCommodity` gerando `Receita`
- pecuária gerando `Despesa`/`Receita` direta em fluxos legados
- hedge ainda fora da cadeia oficial de DRE/caixa/rentabilidade

## Decisões fixadas

- Fonte canônica de receita: **`Receita`**
- Fonte canônica de despesa: **`Despesa`**
- Fonte canônica de custo operacional: **`CostAllocation`**
- Relação `Despesa` x `CostAllocation`: **obrigação financeira x apropriação econômica**
- Arquitetura oficial de DRE: **`agricola.dre.v1`**
- Arquitetura oficial de rentabilidade: **derivada exclusivamente da DRE agrícola v1**
- Centro de custo: **agregação analítica, não entidade canônica**

## Impacto prático para v1.0

Pode entrar como oficial:

- `Receita`
- `Despesa`
- `CostAllocation`
- `OperationalCostAllocationService`
- `agricola.dre.v1`
- `agricola.rentabilidade.v1`

Deve ficar como compatibilidade e plano de consolidação:

- DRE legada de `LancamentoFinanceiro`
- estoque -> `LancamentoFinanceiro`
- romaneio como origem de receita estimada
- pecuária econômica heterogênea
- hedge fora da cadeia oficial

## Resposta final obrigatória

**Após esta execução, qualquer novo desenvolvimento econômico no AgroSaaS terá uma referência arquitetural clara sobre como gerar receitas, despesas, custos operacionais, apropriações, DRE, fluxo de caixa e rentabilidade, sem criar caminhos paralelos ou dupla contagem?**

**Sim, terá uma referência clara.**

**Não, isso não significa que a codebase atual já esteja totalmente consolidada.**

Portanto:

- para novos desenvolvimentos, a referência está definida;
- para o estado atual do produto, ainda existem caminhos paralelos relevantes a consolidar antes da v1.0.
