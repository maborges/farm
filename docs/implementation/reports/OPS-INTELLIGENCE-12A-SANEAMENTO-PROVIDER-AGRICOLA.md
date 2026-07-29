# OPS-INTELLIGENCE-12A — Saneamento do Provider Agrícola

## Causa raiz comprovada

A regra `AGRI_CUSTO_ACIMA_PREVISTO` continua vigente em `AgriculturaRecommendationProvider._budget_gap` e usa a cadeia econômica oficial:

- orçamento previsto: `ItemOrcamentoSafra` da safra;
- custo realizado: `CostAllocation` das `ProductionUnit` vinculadas à safra;
- comparação: `CustosService.get_resumo_safra`.

A fixture que falhava criava `OperacaoAgricola.custo_total` e itens de orçamento, mas não criava `ProductionUnit` nem `CostAllocation`. Consequentemente, o `CustosService` apurava custo realizado igual a zero e o desvio não ultrapassava o limiar de 10%; o provider corretamente não gerava o candidato.

## Decisão

**Opção B — corrigir teste/fixture.** O provider e a regra já respeitavam a precedência econômica oficial: `OperacaoAgricola` não é uma fonte de custo realizado consolidado e `Despesa`/`LancamentoFinanceiro` não foram usados como substitutos.

## Correção aplicada

`test_recommendations_providers_real.py` agora semeia a cadeia econômica válida para o cenário positivo:

1. `Cultivo` e `ProductionUnit` pertencentes ao tenant e à safra;
2. `CostAllocation` válida, com categoria e origem aceitas pelas constraints do banco;
3. custo realizado de 1.200 contra orçamento de 900.

O candidato gerado é `AGRI_CUSTO_ACIMA_PREVISTO`, com prioridade `URGENT`, fonte `ORCAMENTO_SAFRA`, dedupe determinístico e justificativa baseada em desvio superior a 25%.

Também foram adicionados cenários que comprovam:

- ausência de `CostAllocation` oficial não gera a regra;
- allocation de outro tenant não gera a regra para a safra do tenant atual;
- o provider não altera `CostAllocation` durante a avaliação.

## Arquivos alterados

- `services/api/tests/unit/recommendations/test_recommendations_providers_real.py`
- `docs/implementation/reports/OPS-INTELLIGENCE-12A-SANEAMENTO-PROVIDER-AGRICOLA.md`

Nenhum arquivo do scheduler produtivo, worker, lock advisory, lifecycle, RLS, registry, API, Web, Campo ou notificações foi alterado. O OPS-INTELLIGENCE-12 não foi reaberto.

## Testes e evidências

```bash
cd services/api
.venv/bin/python -m py_compile tests/unit/recommendations/test_recommendations_providers_real.py
.venv/bin/python -m pytest tests/unit/recommendations -k "agricultura_provider_generates_candidates_from_context" -q
.venv/bin/python -m pytest tests/unit/recommendations -m integration -k "agricultura_provider_generates_candidates_from_context" -q
.venv/bin/python -m pytest tests/unit/recommendations -m integration -k "agricultura_provider" -q
.venv/bin/python -m pytest tests/unit/recommendations -q
.venv/bin/python -m pytest tests/unit/recommendations -m integration -q
```

Resultados:

- comando isolado sem marker: `74 deselected`, pois a configuração marca esse arquivo como `integration`;
- cenário isolado com marker: `1 passed, 73 deselected`;
- cenários agrícolas do provider: `3 passed, 71 deselected`;
- suíte unitária: `44 passed, 30 deselected`;
- suíte de integração completa: `29 passed, 1 failed, 44 deselected`.

A falha restante é distinta desta entrega: `test_list_filters_by_period` em `test_recommendations_query_router.py` executa um `UPDATE recommendation_results` direto depois de um `commit`, sem reaplicar o contexto RLS `app.current_tenant_id`. A política RLS tenta converter o contexto vazio em UUID e o banco rejeita a operação. Não toca `AgriculturaRecommendationProvider`, `CustosService`, `CostAllocation` ou o scheduler produtivo.

## Veredicto

**GO COM RESSALVAS** para encerrar OPS-INTELLIGENCE-12: a divergência agrícola foi corrigida e seus cenários estão verdes. A suíte de integração ainda requer saneamento separado do teste de query por período antes de poder ser usada como gate integral de release.
