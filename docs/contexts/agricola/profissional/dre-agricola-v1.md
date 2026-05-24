---
modulo: "Agrícola"
submodulo: DRE Agrícola v1
nivel: profissional
core: false
dependencias_core:
  - core/auth
  - core/tenant
dependencias_modulos:
  - ../essencial/safras.md
  - ../essencial/operacoes-campo.md
  - ../profissional/custos-producao.md
  - ../../financeiro/essencial/fluxo-caixa.md
  - ../../contabilidade/profissional/dre-rural.md
standalone: false
complexidade: M
assinante_alvo:
  - medio-produtor
  - grande-produtor
  - cooperativa
---

# DRE Agrícola v1

## Status

Documento técnico de governança e consolidação. Não define dashboard, exportação pública, schema ou cálculo adicional. A fonte oficial de precedência econômica continua em [Matriz de Precedência Econômica Oficial](../../../architecture/economic-source-precedence.md).

A DRE agrícola v1 também alimenta a página financeira da safra em modo controlado. Nessa tela, os KPIs oficiais da DRE v1 aparecem como fonte primária e os indicadores financeiros legados permanecem apenas como referência secundária.

A mesma base oficial também alimenta a visão de **Rentabilidade Agrícola v1**, acessível pelo card do hub agrícola principal. Essa visão deriva exclusivamente desta DRE e dos KPIs oficiais já existentes, sem recalcular receita ou custo fora da consolidação oficial. Quando houver inconsistências econômicas moderadas ou risco de reconciliação, a interface pode sinalizar que a rentabilidade está sujeita à reconciliação.

A mesma base também alimenta a visão de **Eficiência Operacional Agrícola v1**, acessível pelo card do hub agrícola principal. Essa visão deriva exclusivamente da DRE agrícola v1, dos KPIs oficiais e dos registros operacionais já existentes, sem criar engine analítica paralela nem recalcular economia fora da consolidação oficial. Quando houver inconsistências ou warnings relevantes, os indicadores podem ser exibidos como sujeitos à reconciliação.

A mesma base também alimenta a visão de **Benchmark Operacional e Econômico v1**, acessível pelo card do hub agrícola principal. Essa visão deriva exclusivamente da DRE agrícola v1, dos KPIs oficiais, da rentabilidade oficial e da eficiência operacional oficial, sem criar cubo analítico paralelo, comparativo histórico massivo ou recálculo fora da consolidação oficial. Quando houver inconsistências ou warnings relevantes, o benchmark pode ser exibido como sujeito à reconciliação.

A mesma base também alimenta a visão de **Diagnóstico Operacional e Econômico v1**, acessível pelo card do hub agrícola principal. Essa visão deriva exclusivamente da DRE agrícola v1, dos KPIs oficiais, da rentabilidade oficial, da eficiência operacional oficial e do benchmark oficial, sem criar IA generativa, engine paralela ou BI pesado. Quando houver desvios relevantes, warnings recorrentes ou inconsistências moderadas, os diagnósticos podem ser exibidos como sujeitos à reconciliação.

A mesma base também alimenta a visão de **Recomendações Operacionais e Econômicas Assistidas v1**, acessível pelo card do hub agrícola principal. Essa visão deriva exclusivamente da DRE agrícola v1, dos KPIs oficiais, da rentabilidade oficial, da eficiência operacional oficial, do benchmark oficial e dos diagnósticos oficiais, sem criar IA autônoma, automação de execução ou engine paralela. Quando houver warnings relevantes ou reconciliação pendente, as recomendações podem ser exibidas como sujeitas à reconciliação.

A mesma base também alimenta a visão de **Central Inteligente de Prioridades Agrícolas v1**, acessível pelo card do hub agrícola principal. Essa visão consolida diagnósticos, recomendações, benchmark e warnings oficiais em uma fila priorizada e determinística, sem criar engine paralela, duplicar cálculos ou usar relatórios financeiros legados como fonte principal. Quando houver inconsistências moderadas, riscos econômicos ou warnings relevantes, as prioridades podem ser exibidas como sujeitas à reconciliação.

## Objetivo

Documentar a janela temporal da DRE agrícola v1 e as regras de fallback por fonte para evitar dupla contagem entre receita, despesa, apropriação econômica, caixa e valuation operacional.

## Escopo Funcional

- Serviço interno somente leitura.
- Rota interna protegida para validação controlada.
- Consolidação por `tenant`, `safra`, `ProductionUnit`, `unidade_produtiva` e período.
- Reconciliação e warnings respeitam a mesma janela temporal da consolidação.

## Regras de Fonte e Data

### Receita

- Fonte oficial: `Receita`.
- Campo econômico principal: `competencia`.
- Fallback: `data_emissao` quando `competencia` estiver ausente.
- A linha só entra na DRE consolidada se cair dentro de `data_inicio` / `data_fim` pela data econômica escolhida.
- `LancamentoFinanceiro` de recebimento não substitui `Receita` como linha principal.

### CostAllocation

- Fonte oficial de custo apropriado: `CostAllocation`.
- Campo temporal: `allocation_date`.
- A janela temporal da DRE usa `allocation_date` como referência da apropriação.
- `EstoqueMovimento` pode refletir o fato físico, mas não substitui a apropriação econômica.

### Despesa

- Fonte oficial de obrigação financeira: `Despesa`.
- Campo econômico principal: `competencia`.
- Fallback: `data_emissao` quando `competencia` estiver ausente.
- A despesa entra como linha principal apenas quando não houver camada econômica superior que a supere por precedência.

### LancamentoFinanceiro

- Não entra como linha principal da DRE agrícola v1.
- É usado apenas para reconciliação econômica e observabilidade.
- Campo temporal para reconciliação: `data`.

### EstoqueMovimento

- Não entra como linha principal da DRE agrícola v1.
- É usado apenas para reconciliação, warnings e validação de valuation operacional.
- Campo temporal para reconciliação: `data_movimento`.

## Comportamento Da Janela Temporal

### Quando `data_inicio` e `data_fim` não são informados

- O serviço mantém o comportamento atual.
- A consolidação continua obedecendo a precedência econômica oficial.
- A reconciliação pode usar toda a base elegível do tenant/safra conforme o escopo selecionado.

### Quando `data_inicio` e/ou `data_fim` são informados

- Receita é filtrada por `competencia` ou, em fallback, por `data_emissao`.
- `CostAllocation` é filtrado por `allocation_date`.
- `Despesa` é filtrada por `competencia` ou, em fallback, por `data_emissao`.
- `LancamentoFinanceiro` e `EstoqueMovimento` entram na reconciliação pela respectiva data econômica/física.
- `CostAllocation` usado na reconciliação também respeita `allocation_date`.

## Warnings E Reconciliação

- Warnings de inconsistência econômica respeitam o período quando a janela é informada.
- Sem período informado, a reconciliação pode observar a base completa do escopo.
- `MOVIMENTO_COM_CUSTO_SEM_ALLOCATION` deve ser interpretado como risco de dupla ou ausência de apropriação, nunca como linha principal da DRE.
- `LancamentoFinanceiro` e `EstoqueMovimento` permanecem como camadas de observabilidade, não de consolidação principal.

## Regras De Precedência Reforçadas

- `Receita` permanece fonte oficial de receita.
- `CostAllocation` permanece fonte oficial de custo apropriado.
- `Despesa` permanece fonte oficial de obrigação financeira.
- `LancamentoFinanceiro` é realização financeira.
- `EstoqueMovimento` é valuation operacional/físico.
- Nenhuma dessas camadas deve ser somada duas vezes quando o mesmo fato econômico aparece em mais de uma delas.

## Relação Com A Governança Oficial

Este documento operacionaliza a matriz oficial descrita em:

- [economic-source-precedence.md](../../../architecture/economic-source-precedence.md)
- [agro-domain-governance.md](../../../architecture/agro-domain-governance.md)
- [operational-workflow-governance.md](../../../architecture/operational-workflow-governance.md)

## Próxima Evolução

- Exposição controlada da DRE agrícola v1 para validação restrita.
- Rentabilidade Agrícola v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Eficiência Operacional Agrícola v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Benchmark Operacional e Econômico v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Diagnóstico Operacional e Econômico v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Recomendações Operacionais e Econômicas Assistidas v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Central Inteligente de Prioridades Agrícolas v1 como visão oficial derivada da DRE agrícola v1, acessível pelo hub agrícola principal.
- Consolidação futura de linhas contábeis e financeiras em camadas próprias, sem quebrar a precedência econômica oficial.
- Expansão de relatórios por safra e unidade operacional com a mesma janela temporal.
- Manutenção da página financeira da safra como superfície de consumo dos KPIs oficiais, com legado apenas como referência secundária.
