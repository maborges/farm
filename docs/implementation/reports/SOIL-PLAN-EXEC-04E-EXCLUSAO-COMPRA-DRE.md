# SOIL-PLAN-EXEC-04E — Exclusão de Despesa(COMPRA) da DRE Agrícola

## 1. Causa raiz

`Despesa(origem_tipo="COMPRA")` representa a obrigação financeira com o fornecedor no
momento da aquisição de estoque. `CostAllocation` representa o custo de produção
efetivamente consumido via FIFO. A DRE agrícola somava as duas fontes, gerando dupla
contabilização: o valor total da compra (contas a pagar) e o valor já consumido
(custo de produção).

## 2. Regra anterior

`_consolidar_despesas` só excluía uma `Despesa` quando existia `CostAllocation`
correspondente para as origens `OPERACAO_AGRICOLA`, `ORDEM_SERVICO`, `ABASTECIMENTO`,
`FIN_RATEIO` (e origens canônicas via `_despesa_tem_allocation_canonica`).
`Despesa(origem_tipo="COMPRA")` não se encaixava em nenhuma dessas regras condicionais
e, portanto, sempre entrava na consolidação de despesas operacionais.

## 3. Regra implementada

Exclusão incondicional adicionada em `services/api/agricola/dre/service.py`, dentro do
loop de `_consolidar_despesas`, antes de qualquer verificação de `CostAllocation`:

```python
if despesa.origem_tipo == "COMPRA":
    excluidas += 1
    continue
```

## 4. Por que a exclusão é incondicional

A auditoria `SOIL-PLAN-EXEC-04D` confirmou que toda `Despesa(COMPRA)` nasce do fluxo de
aquisição que passa por estoque (`Compra → PedidoCompra → recebimento → LoteEstoque →
Despesa`), e que não existe despesa direta legítima usando `origem_tipo="COMPRA"`. O
valor da compra nunca deveria entrar diretamente na DRE — o único caminho legítimo para
o custo agrícola é via `CostAllocation`, que reflete o consumo real. Por isso a exclusão
não depende de haver ou não `CostAllocation` associado: mesmo sem consumo, a compra
continua sendo apenas uma obrigação financeira, não um custo produtivo.

## 5. Diff funcional

**Antes:** Compra R$ 10.000 + consumo R$ 2.000 → DRE reconhecia R$ 12.000 (dupla
contagem) ou, em versões com allocation condicional, arriscava reconhecer os R$ 10.000
integrais quando não havia mapeamento de origem específico para COMPRA.

**Depois:** Compra R$ 10.000 + consumo R$ 2.000 → `despesas_operacionais = 0`,
`custos_diretos = 2.000` (via `CostAllocation`), custo agrícola reconhecido = R$ 2.000.

Compra R$ 10.000 sem consumo → `despesas_operacionais = 0`, `custos_diretos = 0`,
custo agrícola reconhecido = R$ 0.

## 6. Arquivos alterados

- `services/api/agricola/dre/service.py` — condição de exclusão incondicional em
  `_consolidar_despesas` (4 linhas adicionadas, incluindo comentário).
- `services/api/tests/test_dre_agricola_v1.py` — novo teste parametrizado de regressão.

## 7. Testes adicionados

`test_dre_v1_exclui_despesa_compra_incondicionalmente` (parametrizado, 3 casos):

- **Cenário A** — compra R$ 10.000 sem consumo → custo agrícola = R$ 0.
- **Cenário B** — compra R$ 10.000 + `CostAllocation` R$ 2.000 → custo agrícola = R$ 2.000.
- **Cenário C** — compra R$ 10.000 + `CostAllocation` R$ 10.000 → custo agrícola = R$ 10.000.

Em todos os casos: `despesas_operacionais == 0.0` e nenhum item com
`origem_tipo == "COMPRA"` aparece em `despesas_operacionais_detalhe.itens`.

## 8. Testes executados

```
.venv/bin/python -m pytest tests/test_dre_agricola_v1.py -q
.venv/bin/python -m pytest tests/test_fifo_estoque.py tests/test_dre_agricola_v1.py \
  tests/integration/financeiro/test_despesas.py tests/test_operacao_despesa_webhook.py \
  tests/test_operacoes_validacao_fase.py -q
.venv/bin/python -m pytest tests/test_compras_lote_integration.py -q
```

## 9. Resultados

- `test_dre_agricola_v1.py`: **11 passed** (8 pré-existentes + 3 novos casos parametrizados).
- Suíte combinada (FIFO, DRE, despesas, webhook, validação de fase): **41 passed**.
- `test_compras_lote_integration.py`: **5 passed, 2 failed** (pré-existentes).

## 10. Falhas pré-existentes

`test_recebimento_cria_lote_e_fifo_consome` e `test_p0_2_supplier_batch_in_itemrecebimento`
falham com `NoReferencedTableError` em `compras_pedidos.tenant_id → estoque_depositos`,
não relacionado à mudança. Confirmado via `git stash`: as mesmas 2 falhas ocorrem também
no `HEAD` antes desta alteração. Não corrigidas nesta etapa.

## 11. Riscos residuais

Nenhum identificado dentro do escopo desta etapa. A exclusão é isolada ao loop de
consolidação de despesas da DRE agrícola; não altera criação de `Despesa`, contas a
pagar, `PedidoCompra`, recebimento, estoque, FIFO, `CostAllocation`, modelos, schemas
ou migrations.

`ruff check` reporta apenas violações de estilo pré-existentes no arquivo (linhas
longas, imports não usados de código legado, comparações `== True`) — nenhuma nova
violação introduzida pelo diff. `git diff --check` limpo.

## 12. Decisão final

```
SOIL-PLAN-EXEC-04E
STATUS: GO
```

```
REGRA FINAL:
Despesa(COMPRA) permanece no financeiro e é excluída da DRE agrícola.
CostAllocation é a fonte exclusiva do custo de insumo consumido.
```

```
PRÓXIMO PASSO:
Migrar o dashboard de margem da safra para usar custo_total/CostAllocation como fonte
única e eliminar a deduplicação min(custo_operacoes, despesa_total).
```
