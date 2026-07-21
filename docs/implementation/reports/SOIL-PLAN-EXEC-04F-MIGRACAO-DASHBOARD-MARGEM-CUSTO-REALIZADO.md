# SOIL-PLAN-EXEC-04F — Migração do Dashboard de Margem para Custo Agrícola Realizado

## 1. Lógica anterior

`services/api/agricola/dashboard/service.py`, método `resumo_financeiro_safra()`:

```python
custo_operacoes = sum(float(op.custo_total or 0) for op in operacoes)
...
despesas = select(Despesa).where(
    Despesa.origem_tipo == "OPERACAO_AGRICOLA",
    Despesa.origem_id.in_(operacao_ids),
)
despesa_total = sum(float(d.valor_total or 0) for d in despesas)
...
custo_base = min(custo_operacoes, despesa_total) if despesa_total > 0 else custo_operacoes
```

O `min()` era uma compensação manual para uma duplicidade antiga entre `OperacaoAgricola.custo_total`
e `Despesa(OPERACAO_AGRICOLA)`, sem lastro em nenhuma regra econômica — apenas escolhia o menor
dos dois valores.

## 2. Consumidor identificado

Único consumidor não redundante de `Despesa(origem_tipo="OPERACAO_AGRICOLA")` no cálculo de
margem: `DashboardAgricolaService.resumo_financeiro_safra()`. Não há outro método no dashboard
(`resumo_margem_por_talhao`, por exemplo) que usava despesa nesse cálculo — o cálculo por talhão
já usa apenas `OperacaoAgricola.custo_total` diretamente e não foi alterado.

## 3. Fonte econômica escolhida

`CostAllocation`, vinculado por operação via `OperacaoExecucao.operacao_id`:

```python
stmt_alloc = (
    select(OperacaoExecucao.operacao_id, func.sum(CostAllocation.amount))
    .join(CostAllocation, CostAllocation.operation_execution_id == OperacaoExecucao.id)
    .where(
        CostAllocation.tenant_id == self.tenant_id,
        OperacaoExecucao.operacao_id.in_(operacao_ids),
    )
    .group_by(OperacaoExecucao.operacao_id)
)
```

O join usa `CostAllocation.operation_execution_id`, que é preenchido quando a apropriação é
gerada a partir da execução da operação (`source="OPERATION_EXECUTION"`, ver
`agricola/operacoes/service.py`). O escopo respeita `tenant_id` e é restrito às operações da
safra consultada (`operacao_ids` já filtrado por `safra_id` e `tenant_id`).

## 4. Estratégia de fallback

Por operação, não por safra inteira:

```python
custo_operacoes = sum(
    alloc_por_operacao[op.id] if op.id in alloc_por_operacao else float(op.custo_total or 0)
    for op in operacoes
)
```

Se a operação tem `CostAllocation` (mesmo que zero por algum motivo, o `in` distingue
"tem allocation" de "não tem"), usa a soma das allocations. Caso contrário, cai no fallback de
`OperacaoAgricola.custo_total`. Os dois nunca são somados para a mesma operação. `Despesa` não
participa em nenhum ramo do cálculo.

## 5. Tratamento por operação

A escolha é feita individualmente por `operacao.id`, agregada depois via `sum()`. Isso evita:
- dupla contagem (uma operação nunca soma allocation + custo_total);
- perda de custo em operações antigas sem allocation (fallback preserva o valor histórico);
- uso de `min()`/`max()` como regra de reconciliação.

## 6. Alteração de schema

`agricola/dashboard/schemas.py`: comentário do campo `despesa_total` atualizado para refletir a
nova semântica (Opção A do spec — campo legado mantido, mas com o significado de custo agrícola
realizado). Nenhum campo foi removido ou renomeado.

```python
despesa_total: float  # Campo legado: custo agrícola realizado (CostAllocation, com fallback por custo_total)
```

`custo_operacoes_total` manteve seu contrato (agora também reflete o custo realizado, já que
`custo_operacoes` passou a ser calculado com a nova lógica) — seu valor numérico muda, mas o
schema não mudou.

## 7. Impacto frontend

Auditado `apps/web/src`:
- `financeiro-kpis.tsx` e `financeiro-chart.tsx` consomem `despesa_total` diretamente para exibir
  "Despesa Total" e calcular lucro no gráfico (`receita_total - despesa_total`). Como `despesa_total`
  continua existindo com o mesmo tipo e agora carrega o custo realizado (Opção A), **nenhuma
  alteração de frontend foi necessária** — o valor exibido passa a ser economicamente correto sem
  mudança de código.
- `custo_operacoes_total` está tipado em `financeiro/page.tsx` mas não é renderizado em nenhum
  componente auditado — não há risco de rótulo duplicado ou incoerente.
- Nenhuma alteração de layout ou contrato de API foi feita.

## 8. Arquivos alterados

- `services/api/agricola/dashboard/service.py` — nova lógica de custo realizado por operação,
  remoção da query de `Despesa` e do `min()`.
- `services/api/agricola/dashboard/schemas.py` — comentário do campo `despesa_total` atualizado.
- `services/api/tests/test_dashboard_financeiro_safra.py` — 6 novos testes de regressão
  (cenários A–F).

## 9. Testes adicionados

Classe `TestDashboardFinanceiroSafraCustoRealizado` (fixtures isoladas por tenant/safra, per
item 12 do plano):

- **Cenário A** — allocation e custo_total concordam (1.000), despesa igual (1.000): custo
  considerado = 1.000 (não 2.000).
- **Cenário B** — allocation = 1.200, despesa = 900: custo considerado = 1.200 (sem `min()`).
- **Cenário C** — operação antiga sem allocation, custo_total = 800: fallback = 800.
- **Cenário D** — sem custo e sem allocation: custo = 0, `roi_pct is None`.
- **Cenário E** — duas operações (uma com allocation, outra com fallback): soma = 800, sem
  duplicidade por operação.
- **Cenário F** — despesa `OPERACAO_AGRICOLA` órfã (sem operação/custo/allocation
  correspondente): não entra no cálculo (`total_operacoes == 0`, custo = 0).

## 10. Testes executados

```bash
.venv/bin/python -m pytest tests/test_dashboard_financeiro_safra.py -q
.venv/bin/python -m pytest tests/test_dashboard_financeiro_safra.py tests/test_dre_agricola_v1.py \
  tests/test_fifo_estoque.py tests/test_operacao_despesa_webhook.py \
  tests/test_operacoes_validacao_fase.py -q
.venv/bin/python -m pytest tests/unit/agricola tests/test_launch_core01_operational_cost_engine.py \
  -k "cost or custo or allocation or margem or dashboard" -q
.venv/bin/ruff check agricola/dashboard/service.py agricola/dashboard/schemas.py \
  tests/test_dashboard_financeiro_safra.py
```

## 11. Resultados

- `test_dashboard_financeiro_safra.py`: **9 passed / 3 failed** (3 falhas pré-existentes de
  `receita_total`, idênticas ao baseline reproduzido no `HEAD` antes da alteração).
- Suíte combinada (dashboard + DRE + FIFO + webhook + validação de fase): **40 passed / 3
  failed** (mesmas 3 falhas pré-existentes).
- Busca ampla por custo/allocation/margem/dashboard: **8 passed / 4 failed**, falhas idênticas
  ao `HEAD` (confirmadas via `git stash`), causadas por `NoReferencedTableError` em
  `frota_abastecimentos` — problema de metadata SQLAlchemy ao rodar esse subconjunto de arquivos
  isoladamente, não relacionado a esta mudança.
- `ruff check`: **21 erros**, mesma contagem do baseline (`git stash` reproduziu exatamente os
  mesmos 21 antes da mudança) — nenhuma violação nova introduzida.
- `git diff --check`: limpo.

## 12. Falhas pré-existentes

1. `test_resumo_financeiro_safra_valido`, `test_resumo_financeiro_safra_sem_operacoes`,
   `test_resumo_roi_calculado` — falham em `receita_total` (não em custo/despesa). Causa raiz:
   os três testes originais compartilham o mesmo `tenant_id` fixo (`TENANT_A_ID`, fixture
   `conftest.py`) sem isolamento de dados entre execuções, e a ordem de execução dentro da
   suíte altera a soma acumulada de romaneios/comercializações visíveis. Reproduzido
   identicamente no `HEAD` antes da mudança (via `git stash`) e também variando apenas por
   reordenação de testes — não é causado nem agravado pela lógica de custo alterada aqui. Não
   corrigido, conforme item 12 do plano (fora de escopo; a correção de receita/isolamento seria
   uma tarefa separada).
2. `NoReferencedTableError` em `frota_abastecimentos`/`compras_pedidos` ao rodar subconjuntos
   isolados de arquivos de teste — problema de import/registro de metadata SQLAlchemy,
   reproduzido de forma idêntica no `HEAD`.

## 13. Riscos residuais

- **CostAllocation não revertido após cancelamento de operação** continua sendo risco residual,
  agora mais visível: como o dashboard depende diretamente de `CostAllocation`, uma operação
  cancelada cuja allocation não foi estornada continuará contribuindo para o custo realizado
  exibido. Não corrigido nesta etapa — não foi mascarado com fallback ou filtro improvisado, e
  fica registrado como escopo de `SOIL-PLAN-EXEC-04G`.
- Nenhuma migration foi criada; nenhum fluxo de DRE, financeiro, estoque, FIFO, criação de
  `CostAllocation` ou cancelamento foi alterado.

## 14. Decisão final

```
SOIL-PLAN-EXEC-04F
STATUS: GO
```

```
REGRA FINAL:
O dashboard de margem utiliza CostAllocation como fonte primária do custo realizado.
OperacaoAgricola.custo_total pode ser usado apenas como fallback por operação sem allocation.
Despesa(OPERACAO_AGRICOLA) não participa do cálculo de margem, lucro ou ROI.
```

```
PRÓXIMO PASSO:
SOIL-PLAN-EXEC-04G — implementar reversão econômica no cancelamento da operação,
tratando CostAllocation e Despesa(OPERACAO_AGRICOLA) de forma transacional e idempotente.
```
