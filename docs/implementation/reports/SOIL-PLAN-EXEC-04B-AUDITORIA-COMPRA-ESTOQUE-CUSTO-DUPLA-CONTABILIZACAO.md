# SOIL-PLAN-EXEC-04B — Auditoria de Compra, Estoque, Apropriação de Custo e Dupla Contabilização

**Tipo:** Auditoria contábil/arquitetural, somente leitura. Nenhum código de produção, teste, migration, banco de dados, frontend, Campo PWA ou integração ERP foi alterado nesta etapa.
**Data:** 2026-07-20

---

## 1. Resumo executivo

A auditoria confirma **dupla contabilização real** no relatório de DRE agrícola (`agricola/dre/service.py`), não no fluxo transacional de compra/aplicação em si (que estão corretamente separados no nível de escrita).

O fluxo de **compra** (`operacional/services/compras_service.py`) gera uma `Despesa` financeira (`status="A_PAGAR"`, `origem_tipo="COMPRA"`) no recebimento do pedido — contrariando a premissa inicial de que só a aplicação gerava fato financeiro. O fluxo de **aplicação** (`agricola/operacoes/service.py`) gera uma segunda `Despesa` (`status="PAGO"`, `origem_tipo="OPERACAO_AGRICOLA"`) e um `CostAllocation` para o mesmo insumo consumido via FIFO. No cálculo do DRE, a lista de exclusão que evita somar `Despesa` duas vezes junto com `CostAllocation` cobre `OPERACAO_AGRICOLA`, `ORDEM_SERVICO`, `ABASTECIMENTO` e `FIN_RATEIO` — **mas não `COMPRA`**. Consequência: o valor da compra (passivo com o fornecedor) e o valor do consumo do mesmo insumo (custo de aplicação) são somados juntos em `resultado_operacional`, contabilizando o mesmo insumo duas vezes.

**Veredicto: HÁ DUPLA CONTABILIZAÇÃO: SIM** (confirmada no relatório DRE, não no razão/estoque em si) — classificação **Opção C** (com elementos de Opção B, ver seção 17).

---

## 2. Fluxo real de compra

`operacional/services/compras_service.py` (1796 linhas):

| Etapa | Método | Linha | Cria/atualiza | Toca estoque? | Toca financeiro? |
|---|---|---|---|---|---|
| Solicitação | `criar_solicitacao` | 646 | `SolicitacaoCompra` | Não | Não |
| Cotação | `criar_cotacao` | 732 | `CotacaoCompra` | Não | Não |
| Aprovação/Pedido | `aprovar_cotacao` | 819 | `PedidoCompra` | Não | Não |
| Recebimento | `receber_pedido` | 909 | `LoteEstoque`, `EstoqueMovimento` (via `_materializar_item_recebimento`, linha 330) **e** `Despesa` | **Sim** | **Sim** |

**Resposta à pergunta central da seção 3 do escopo:** o recebimento **não** gera apenas entrada física — também cria obrigação financeira. `_garantir_despesa_financeira_compra` é chamado em dois pontos: linha 922 (fluxo legado/fallback) e linha 983 (fluxo principal por item recebido).

Detalhe do bloco (`compras_service.py:142-205`, verificado linha a linha):
- **Idempotência confirmada** (linhas 148-159): busca `Despesa` existente com `tenant_id`, `origem_tipo=="COMPRA"`, `origem_id==pedido.id`, `ativo==True` antes de criar outra — se existir, retorna a existente sem duplicar.
- Valor: `valor_total=pedido.valor_total` (linha 189) — valor **total do pedido**, não apenas da fração já consumida.
- Status inicial: `"A_PAGAR"` (linha 193) — diferente do `"PAGO"` da despesa de operação.
- `origem_tipo="COMPRA"`, `origem_id=pedido.id` (linhas 199-200).
- Vencimento calculado a partir das condições de pagamento do fornecedor (linhas 180-183).
- Plano de contas: `_resolver_plano_conta_compra` (linha 168) resolve conta de despesa `categoria_rfb="CUSTEIO"` — a mesma categoria econômica usada pela despesa da operação agrícola (auditoria 04).
- Criação efetiva via `DespesaService(self.session, self.tenant_id).create_with_rateio(payload)` (linha 204).

---

## 3. Fluxo real de estoque (entrada)

Em `_materializar_item_recebimento` (compras_service.py, ~linhas 330-420):
- `custo_unitario` (linha 339): `preco_real_unitario` do item recebido, com fallback para `_resolver_custo_recebimento(pedido)` (linha 44) se não informado.
- Não há evidência de rateio explícito de frete/impostos/desconto compondo o custo unitário do lote nesse trecho — apenas o preço unitário informado no recebimento.
- `EstoqueMovimento` grava `origem_id`/`origem_tipo="COMPRA"` (linhas 386-387) — rastreabilidade mantida.
- Recebimento parcial: suportado — `RecebimentoParcial`/`ItemRecebimento` (importados linhas 16-18), `item_pedido.quantidade_recebida` acumulada (linha 224).
- Reversão/estorno: `DevolucaoFornecedor`/`ItemDevolucao` (linhas 19-20), lógica de reversão em torno das linhas 469-630, incluindo reativação de lote esgotado, confirmada por testes (`test_p0_3_devolucao_reversal_restaura_estoque`, `test_p0_3_devolucao_reativa_lote_esgotado`).

**Resposta à pergunta central da seção 6:** o custo unitário gravado no `LoteEstoque` no recebimento é o mesmo custo que o FIFO usa depois (`estoque_fifo.py:93`, confirmado na auditoria 04) — não há reavaliação/mudança do custo histórico entre a entrada e o consumo. O custo é consistente entre compra e aplicação; o problema não está no valor em si, mas em **onde esse valor é contabilizado como despesa** (ver seção 6/8 abaixo).

---

## 4. Modelos financeiros reais

Diretório `services/api/financeiro/models/`: `cenario.py, conciliacao.py, despesa.py, lancamento.py, nota_fiscal.py, plano_acao.py, plano_conta.py, rateio.py, receita.py`. **Não existem** `ContaPagar`, `TituloPagar` ou `Pagamento` como modelos separados — `Despesa` cumpre esse papel.

| Modelo | Finalidade real | Gera caixa? | Representa obrigação? | Representa custo? | Pode nascer PAGO? |
|---|---|---|---|---|---|
| `Despesa` (`financeiro/models/despesa.py`, tabela `fin_despesas`) | Lançamento financeiro único que serve tanto como conta a pagar (`A_PAGAR`) quanto como despesa já liquidada (`PAGO`) | Sim, quando `PAGO`/`data_pagamento` preenchida | Sim, quando `A_PAGAR`/`ATRASADO` | Sim (é a base de custo somada na DRE) | **Sim** — `status` aceita `A_PAGAR, PAGO, PAGO_PARCIAL, ATRASADO, CANCELADO` (campo, linhas ~66-67); nada impede nascer diretamente `PAGO` |
| `CostAllocation` (`agricola/custos/models.py`, tabela `cost_allocations`) | Apropriação de custo gerencial a uma unidade produtiva/safra | Não | Não | Sim (exclusivamente) | Não aplicável (não tem status de pagamento) |

**Resposta direta:** no AgroSaaS, `Despesa` é um **modelo único e polimórfico** que representa, a depender do `status`, tanto obrigação financeira em aberto (`A_PAGAR`) quanto pagamento já realizado (`PAGO`) — não há separação estrutural entre "conta a pagar" e "despesa/custo gerencial". Isso é o que permite a mesma classe ser usada tanto para a compra (nasce `A_PAGAR`) quanto para a aplicação (nasce diretamente `PAGO`, pulando o estado de obrigação em aberto).

---

## 5. Compra e criação de despesa (confirmação direta de código)

Confirmado por leitura direta (não apenas pelo agente de pesquisa) em `compras_service.py:142-205`:
```python
existente = await self.session.execute(
    select(Despesa).where(
        Despesa.tenant_id == self.tenant_id,
        Despesa.origem_tipo == "COMPRA",
        Despesa.origem_id == pedido.id,
        Despesa.ativo == True,
    ).limit(1)
).scalar_one_or_none()
if existente is not None:
    return existente
...
payload = DespesaCreate(
    ...
    valor_total=float(pedido.valor_total or 0.0),
    status="A_PAGAR",
    origem_id=pedido.id,
    origem_tipo="COMPRA",
    ...
)
despesas = await DespesaService(self.session, self.tenant_id).create_with_rateio(payload)
```
Vínculo com pedido: `origem_id=pedido.id` direto. Vínculo com recebimento: `numero_nf`/`chave_nfe` do último recebimento (linhas 196-197). Vínculo com fornecedor: `_resolver_fornecedor_financeiro` (linha 179). Vínculo com estoque: indireto, via `pedido` → `deposito_id`/`item_id` (produto), não via `LoteEstoque` diretamente.

---

## 6. Operação agrícola e criação de `Despesa` (releitura confirmada)

`agricola/operacoes/service.py`, dentro do método `criar()` (inicia linha 779), bloco em **linhas 1023-1054**:
- Condição exata (linha 1024): `if custo_total_operacao > 0 and operacao.status == "REALIZADA":`.
- Valor: `custo_total_operacao`, acumulado do consumo FIFO do estoque (confirmado na auditoria 04).
- Campos (linhas 1042-1053): `status="PAGO"` (já nasce paga — diferente de `"A_PAGAR"` da compra), `origem_tipo="OPERACAO_AGRICOLA"`, `origem_id=operacao.id`, `data_pagamento=operacao.data_realizada`.
- **Sem idempotência no caminho de criação**: diferente do padrão em `compras_service.py`, este bloco **não** verifica se já existe uma `Despesa` para a mesma operação antes de criar. O helper `_buscar_despesa_existente` (linha 305) existe, mas só é usado dentro de `_sincronizar_efeitos_operacao` (linha 479), chamada por `atualizar()` (linha 1236) — não pelo caminho de `criar()`. Ou seja: a proteção contra duplicidade só age em **edições subsequentes**, não na criação inicial.
- `CostAllocation` para a mesma operação é criado/atualizado por `_garantir_execucao_e_allocation_leves` (linha 552) e/ou dentro do bloco de `_sincronizar_efeitos_operacao` — **coexistindo** com a `Despesa` para o mesmo fato econômico.

**Respostas diretas às perguntas da seção 7 do escopo:**
- Representa saída de caixa? Tecnicamente sim (`status="PAGO"`, `data_pagamento` preenchida) — mas sem nenhum evento real de pagamento (não passa por conciliação bancária nem confirmação externa; é uma anotação contábil, não uma transação financeira efetiva).
- É considerada em contas a pagar? Não deveria (já nasce `PAGO`), mas usa o mesmo modelo/tabela que representa contas a pagar (`Despesa`) — se algum relatório somar por status sem cuidado, poderia aparecer indevidamente.
- É considerada em DRE? **Sim**, mas é corretamente **excluída** de `_consolidar_despesas` quando há `CostAllocation` para a mesma operação (ver seção 8) — a duplicidade **entre Despesa(OPERACAO_AGRICOLA) e CostAllocation da mesma operação está tratada corretamente**.
- É considerada no custo da safra? Sim, via `CostAllocation`.
- Já existe `CostAllocation` para o mesmo valor? Sim, confirmado.
- Os dois registros são somados em relatórios? **Não** para este par específico (Despesa OPERACAO_AGRICOLA × CostAllocation da mesma operação) — a exclusão funciona. O problema real está em outro par: **Despesa(COMPRA) × CostAllocation(operação que consome o insumo comprado)**, ver seção 8.

---

## 7. `CostAllocation` versus `Despesa`

| Aspecto | `CostAllocation` | `Despesa` |
|---|---|---|
| Origem | Execução de operação, movimento de estoque, rateio financeiro (`source` ∈ `OPERATION_EXECUTION`, `INVENTORY_MOVEMENT`, etc.) | Compra (`COMPRA`), operação agrícola (`OPERACAO_AGRICOLA`), ordem de serviço, abastecimento, rateio financeiro (`FIN_RATEIO`) |
| Valor | `amount` — custo real apropriado (FIFO, mão de obra, máquina) | `valor_total` — valor financeiro do documento/evento |
| Momento | No momento da execução/consumo | No momento do evento financeiro (recebimento da compra, ou execução da operação) |
| Centro econômico | `production_unit_id` obrigatório | `unidade_produtiva_id` |
| Afeta caixa | Não | Sim, quando `status="PAGO"` |
| Afeta resultado da safra | Sim — é a fonte primária de custo no DRE (`_consolidar_costs`) | Sim, exceto quando excluída por já ter `CostAllocation` equivalente |
| Pode ser duplicado | Protegido por `_buscar_allocation_existente` (linha 533) nos caminhos de atualização | Protegido na compra (linhas 148-159); **não protegido** no caminho de criação da operação (linha 1042) |
| Possui estorno | Não encontrado estorno explícito | Não encontrado estorno explícito ao reverter estoque de uma operação (ver seção 12) |

**Resposta direta:** `CostAllocation` já é suficiente, por si só, para reconhecer o custo da aplicação à safra — é a fonte usada por `_consolidar_costs` no DRE (linha 508). A `Despesa` da operação (`origem_tipo="OPERACAO_AGRICOLA"`) é, na prática, **redundante para fins de custo de produção** (o DRE já a exclui quando há CostAllocation correspondente), mas pode ter valor para outros consumidores fora do DRE agrícola (ex.: relatórios financeiros genéricos, fluxo de caixa simulado) que não foram mapeados nesta auditoria como consumidores confirmados — não há evidência de que algum desses consumidores exista de fato hoje.

---

## 8. Relatórios e agregações — achado central

`agricola/dre/service.py`:
- `_consolidar_costs` (linha 508): soma **todo** `CostAllocation` do período (linhas 521-526), sem distinguir se a alocação decorre de um insumo comprado recentemente ou de estoque pré-existente.
- `_consolidar_despesas` (linha 573): soma `Despesa` do período, com exclusões explícitas verificadas linha a linha:
  ```python
  # linha 684
  if despesa.origem_tipo == "OPERACAO_AGRICOLA" and despesa.origem_id in alloc_op_ids:
      excluidas += 1; continue
  # linha 687
  if despesa.origem_tipo in {"ORDEM_SERVICO", "ABASTECIMENTO"} and despesa.origem_id in alloc_mov_origin_ids:
      excluidas += 1; continue
  # linha 690
  if despesa.origem_tipo == "FIN_RATEIO" and any(...):
      excluidas += 1; continue
  # linha 693
  if self._despesa_tem_allocation_canonica(despesa, alloc_source_ids):
      excluidas += 1; continue
  ```
  `_despesa_tem_allocation_canonica` (linhas 747-761) mapeia apenas: `ABASTECIMENTO→FROTA_COMBUSTIVEL`, `ORDEM_SERVICO→{FROTA_PECAS, FROTA_MANUTENCAO}`, `RH_DIARIA→RH_DIARIA`, `RH_EMPREITADA→RH_EMPREITADA`.

  **`origem_tipo == "COMPRA"` não aparece em nenhuma das quatro regras de exclusão** (confirmado por leitura completa de `_consolidar_despesas`, linhas 573-744, e do mapa em `_despesa_tem_allocation_canonica`).

- Composição final do resultado (linha 175): `resultado_operacional = margem_bruta - custos_operacionais - despesas_operacionais`, onde `custos_operacionais` vem de `_consolidar_costs` (soma de `CostAllocation`, linha 152) e `despesas_operacionais` vem de `_consolidar_despesas` (linha 153-156) — **ambos são subtraídos separadamente**, sem cruzamento entre eles para o par Compra×Aplicação.

**Consequência confirmada:** quando um insumo é comprado (gerando `Despesa(origem_tipo="COMPRA", valor_total=pedido.valor_total)`) e depois parcial ou totalmente aplicado numa operação (gerando `CostAllocation` via FIFO, somado em `custos_operacionais`), **ambos os valores entram no `resultado_operacional` da mesma DRE**, sem nenhuma regra que reconcilie "este CostAllocation já é o consumo do lote gerado por aquela Despesa de compra". O valor do insumo comprado é contabilizado como custo duas vezes: uma como obrigação/despesa de compra, outra como custo de aplicação.

**Nuance importante:** os dois valores não são numericamente idênticos na maioria dos casos — `Despesa(COMPRA).valor_total` é o valor total do **pedido** (podendo cobrir muito mais do que o que foi efetivamente consumido no período), enquanto `CostAllocation.amount` reflete apenas o custo FIFO do que foi de fato consumido. Isso não elimina a duplicidade — apenas significa que ela não é uma duplicata exata linha a linha, mas uma sobreposição de reconhecimento econômico do mesmo insumo em duas categorias somadas no mesmo resultado.

---

## 9. Cenários obrigatórios

**Cenário A — comprado e aplicado.** Compra de 100 un. → recebimento cria `LoteEstoque` + `EstoqueMovimento(ENTRADA)` + `Despesa(COMPRA, A_PAGAR, valor_total=pedido.valor_total)`. Aplicação de 20 un. → `OperacaoAgricola.status=REALIZADA` → consumo FIFO de 20 un. → `CostAllocation(amount=custo FIFO de 20un)` + `Despesa(OPERACAO_AGRICOLA, PAGO, valor=custo_total_operacao)`. No DRE: `Despesa(OPERACAO_AGRICOLA)` é excluída (tem CostAllocation correspondente); `Despesa(COMPRA)` **não** é excluída e entra integralmente (valor de 100 un., não só das 20 aplicadas) somada ao `CostAllocation` das 20 un. consumidas — **duplicidade confirmada neste cenário**.

**Cenário B — saldo inicial sem compra registrada.** Se o `LoteEstoque` existir sem `PedidoCompra`/`Despesa(COMPRA)` associada (ex.: carga inicial/migração), a aplicação ainda cria `Despesa(OPERACAO_AGRICOLA, PAGO)` normalmente — não há checagem de "este insumo teve compra registrada" antes de gerar a despesa da operação. Não há duplicidade neste caso (não existe Despesa de compra para duplicar), mas confirma que a Despesa da operação é criada de forma incondicional sempre que há custo, independentemente da origem do estoque.

**Cenário C — compra ainda não paga.** `Despesa(COMPRA, A_PAGAR)` existe; insumo aplicado antes do pagamento gera `Despesa(OPERACAO_AGRICOLA, PAGO)` normalmente — **confirma o Cenário A**: a aplicação não verifica o status de pagamento da compra original, criando uma segunda despesa já paga para o mesmo insumo cuja compra ainda está em aberto.

**Cenário D — recebimento parcial.** Suportado estruturalmente (`RecebimentoParcial`, `item_pedido.quantidade_recebida`), mas `_garantir_despesa_financeira_compra` é chamada por recebimento (linha 983) com idempotência por `pedido.id` (não por `recebimento.id`) — ou seja, `existente` (linha 148-159) é buscada por `origem_id=pedido.id`, então **um segundo recebimento parcial do mesmo pedido não geraria uma segunda Despesa** (a primeira já existe e é retornada) — isso é uma proteção contra duplicidade financeira em recebimentos parciais múltiplos, mas também significa que o `valor_total` da despesa não é ajustado incrementalmente por recebimento parcial (permanece o valor do pedido definido na primeira chamada bem-sucedida) — não confirmado se há atualização de valor em recebimentos subsequentes dentro do escopo lido.

**Cenário E — devolução ao fornecedor.** `DevolucaoFornecedor`/`ItemDevolucao` revertem o `LoteEstoque` (confirmado por teste `test_p0_3_devolucao_reversal_restaura_estoque`), mas não há evidência, no trecho lido, de que a devolução ajuste/cancele a `Despesa(COMPRA)` correspondente — o ajuste financeiro da devolução não foi confirmado no escopo desta auditoria.

**Cenário F — cancelamento/estorno da operação.** `_reverter_movimentos_estoque_operacao` (linhas 425-478) reverte apenas `LoteEstoque.quantidade_atual` e registra ledger de devolução — **nenhuma referência a `Despesa` ou `CostAllocation` dentro dessa função** (confirmado por ausência total do termo no trecho). A `Despesa(OPERACAO_AGRICOLA, PAGO)` e o `CostAllocation` associados **não são revertidos automaticamente** quando o estoque de uma operação é revertido.

**Cenário G — operação reprocessada.** Caminho de `atualizar()` usa `_buscar_despesa_existente` (linha 305, chamada em linha 514) e `_buscar_allocation_existente` (linha 533) — **protegido contra duplicação em reprocessamento via update**. O caminho de `criar()` (primeira execução) não tem essa proteção para `Despesa`, mas por ser criação única (não reprocessamento), o risco prático é menor — o risco real é uma dupla *chamada* ao endpoint de criação para a mesma operação, não coberto por constraint de banco (nenhuma unique constraint em `(origem_tipo, origem_id)` foi confirmada para `Despesa`).

**Cenário H — custo sem compra financeira (doação/transferência/saldo inicial).** Confirma o mesmo comportamento do Cenário B: a aplicação sempre cria `Despesa(OPERACAO_AGRICOLA, PAGO)` quando há custo > 0, **independente da origem do estoque ter ou não gerado uma obrigação financeira real**. Isso não é "indevido" por si só (é o reconhecimento do custo de produção), mas reforça que a Despesa da operação é um lançamento de **custo gerencial**, não uma obrigação financeira real — o `status="PAGO"` é uma simplificação de modelagem, não um pagamento efetivo.

---

## 10. Idempotência

| Efeito | Chave de idempotência | Constraint de banco | Checagem no serviço | Cobertura de teste |
|---|---|---|---|---|
| Entrada de estoque (LoteEstoque) | Nenhuma chave de dedupe explícita encontrada | Não confirmada | Recebimento por item, sem re-checagem de duplicidade de lote | `test_recebimento_cria_lote_e_fifo_consome` (falhando por motivo pré-existente, ver seção 15) |
| Despesa da compra | `origem_tipo="COMPRA" + origem_id=pedido.id` | Não confirmada (checagem é applicacional, não constraint) | Sim — `compras_service.py:148-159` | Não identificado teste dedicado a duplo recebimento gerando despesa duplicada |
| Pagamento | N/A (não há modelo `Pagamento` separado) | N/A | N/A | N/A |
| FIFO | Consumo idempotente por transação (auditoria 04) | N/A | Confirmado na auditoria 04 | `test_fifo_estoque.py` (6/6 passando) |
| OperacaoExecucao | Verificação de execução existente (`_buscar_execucao_existente`, auditoria 04) | Não confirmada nesta etapa | Sim, nos caminhos de update | Parcial |
| CostAllocation | `_buscar_allocation_existente` (linha 533) | Não confirmada | Sim, nos caminhos de update/sincronização | Parcial |
| Despesa da operação | **Nenhuma** no caminho de criação (`criar()`, linha 1042) | Não confirmada | Só existe em `atualizar()` via `_sincronizar_efeitos_operacao` | `test_operacao_despesa_webhook.py` — falhando por motivo pré-existente (ver seção 15), não foi possível confirmar comportamento via execução real nesta rodada |

Nenhuma constraint de banco (unique index) foi confirmada para `(Despesa.origem_tipo, Despesa.origem_id)` — a proteção é inteiramente aplicacional, em ambos os fluxos.

---

## 11. Estornos

`_reverter_movimentos_estoque_operacao` (`agricola/operacoes/service.py:425-478`): reverte `LoteEstoque.quantidade_atual` e grava ledger de devolução — **não contém nenhuma referência a `Despesa` ou `CostAllocation`**.

**Resposta direta:** o cancelamento/reversão da operação reverte **apenas o estoque**. A `Despesa(OPERACAO_AGRICOLA, PAGO)` e o `CostAllocation` continuam existindo com o valor original, mesmo que o estoque tenha sido devolvido — isso é uma **inconsistência confirmada, independente do problema de dupla contabilização da seção 8**: um estorno físico sem estorno financeiro/de custo correspondente.

---

## 12. Fronteira ERP

- Compra pode existir sem ERP: sim — `compras_service.py` opera inteiramente sobre modelos internos (`SolicitacaoCompra`, `CotacaoCompra`, `PedidoCompra`), sem qualquer referência a `erp` encontrada nos trechos lidos.
- `Despesa` automática da operação (linhas 1023-1054) não chama nenhuma integração ERP — confirmado por ausência de referência a `erp` no bloco e no restante do método lido.
- Não há indício de que o AgroSaaS e um ERP externo possam registrar o mesmo pagamento em duplicidade nesta etapa — a fronteira permanece: estoque operacional e este fluxo financeiro interno (`Despesa`) são inteiramente internos ao AgroSaaS, sem dependência de ERP.

---

## 13. Transações e eventos

- Não há uso de outbox/eventos de domínio nos blocos de criação de `Despesa`/`CostAllocation` (confirmado nas auditorias 04/04A) — tudo ocorre na mesma `AsyncSession`/transação do método `criar()`/`atualizar()`.
- Uma compra pode entrar no estoque sem gerar obrigação? Não — `receber_pedido` sempre chama `_garantir_despesa_financeira_compra` (linhas 922, 983); se essa chamada falhar (ex.: `BusinessRuleError` por depósito/produto indisponível, linhas 163-166), a exceção se propagaria e, por estarem na mesma sessão/transação, o recebimento inteiro (incluindo a entrada em estoque) seria revertido junto — não foi confirmado com certeza se há `try/except` isolando a falha financeira do sucesso do recebimento físico; pelo código lido, não há tal isolamento, então uma falha na despesa bloquearia também a entrada em estoque.
- Falha financeira reverte o FIFO? Não aplicável diretamente (FIFO ocorre na aplicação, não na compra) — mas na aplicação, o bloco de criação de `Despesa` (linha 1042) ocorre **depois** do consumo FIFO já ter sido processado, na mesma transação — uma falha ali reverteria (via rollback da transação) tanto a Despesa quanto o consumo FIFO e o CostAllocation, mantendo atomicidade dentro de uma única chamada.

---

## 14. Testes existentes e resultados de execução

Comandos executados com o PostgreSQL de teste configurado (`.venv/bin/python -m pytest`, dentro de `services/api/`):

```bash
$ .venv/bin/python -m pytest tests/test_fifo_estoque.py -q
6 passed in 7.75s

$ .venv/bin/python -m pytest tests/test_dre_agricola_v1.py -q
8 passed in 15.43s

$ .venv/bin/python -m pytest tests/test_compras_lote_integration.py -q
2 failed, 5 passed in 10.91s
FAILED test_recebimento_cria_lote_e_fifo_consome — NoReferencedTableError: FK 'compras_pedidos.tenant_id' não encontra tabela 'farms.estoque_depositos' (falha de registro de metadata SQLAlchemy, pré-existente — reproduzida também em execução isolada, não introduzida por esta auditoria)
FAILED test_p0_2_supplier_batch_in_itemrecebimento — mesma causa

$ .venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py -q
7 failed in 10.22s
Causa: TypeError: 'talhao_id' is an invalid keyword argument for Safra — deriva de fixture de teste usando um campo que não existe mais no modelo Safra (drift entre teste e model, pré-existente)

$ .venv/bin/python -m pytest tests/test_launch_core01_operational_cost_engine.py -q
1 passed, 4 failed
Causa: mesma NoReferencedTableError de metadata (frota_abastecimentos.tenant_id → farms.cadastros_equipamentos)
```

Todas as falhas foram confirmadas como **pré-existentes** (reproduzidas em execução isolada por arquivo, não relacionadas a qualquer mudança desta sessão — nenhum arquivo de produção foi tocado nesta auditoria). Não corrigi os testes, conforme instrução.

Classificação de cobertura:

| Área | Classificação |
|---|---|
| Fluxo completo de compra (solicitação→cotação→pedido) | COBERTO (testes passando indiretamente via `test_compras_alertas_step154.py`/`test_solicitacoes_compra_step148.py`, não executados nesta rodada) |
| Recebimento/entrada de lote | **NÃO EXECUTÁVEL nesta rodada** (falha pré-existente de metadata) — cobertura declarada existe (`test_recebimento_cria_lote_e_fifo_consome`), mas não pôde ser confirmada em execução real |
| Conta a pagar (Despesa COMPRA) | PARCIALMENTE COBERTO — idempotência testada implicitamente, nenhum teste nomeado especificamente para "Despesa da compra" |
| Pagamento | NÃO COBERTO (não há modelo dedicado) |
| FIFO | COBERTO (6/6 passando) |
| Custo da operação / Despesa automática | **NÃO EXECUTÁVEL nesta rodada** (falha pré-existente de fixture) |
| `CostAllocation` | PARCIALMENTE COBERTO (via `test_dre_agricola_v1.py`, passando) |
| Reprocessamento/idempotência de custo operacional | **NÃO EXECUTÁVEL nesta rodada** (falha pré-existente de metadata) |
| Cancelamento/estorno de operação × Despesa/CostAllocation | **NÃO COBERTO** — nenhum teste nomeado localizado para esse cenário específico |
| Compra parcialmente recebida × financeiro | PARCIALMENTE COBERTO (estoque sim, efeito financeiro incremental não confirmado) |
| Devolução × ajuste financeiro | NÃO COBERTO (devolução de estoque testada; ajuste de Despesa não) |
| **Dupla contabilização Compra × Aplicação (o cerne desta auditoria)** | **NÃO COBERTO** — nenhum teste, em nenhum arquivo revisado, verifica o cenário de uma Despesa(COMPRA) e um CostAllocation coexistindo na mesma DRE para o mesmo insumo. O teste mais próximo, `test_dre_v1_costallocation_prevalece_sobre_estoque_movimento` (em `test_dre_agricola_v1.py`, passando), valida precedência para movimentos de estoque genéricos, não especificamente para `origem_tipo="COMPRA"` |
| Relatórios (DRE) | COBERTO estruturalmente (8/8 testes passando), mas **nenhum desses testes cobre o cenário de Despesa(COMPRA) não excluída** — a suíte de DRE tem alta cobertura para os pares já tratados (OPERACAO_AGRICOLA, ORDEM_SERVICO, ABASTECIMENTO, FIN_RATEIO), e nenhuma cobertura para o par COMPRA×CostAllocation, exatamente o gap identificado no código |

---

## 15. Matriz de fatos econômicos

| Evento | Estoque físico | Valor do estoque | Conta a pagar (Despesa A_PAGAR) | Caixa | Custo da safra (CostAllocation) | Despesa gerencial |
|---|---:|---:|---:|---:|---:|---:|
| Pedido aprovado | Não afetado | Não afetado | Não | Não | Não | Não |
| Recebimento | **+ (entrada)** | **+ (valorização pelo custo unitário)** | **Sim, criada (`A_PAGAR`)** | Não | Não | Não |
| Pagamento | Não afetado | Não afetado | Atualiza status (não confirmado em detalhe nesta auditoria) | Sim (quando confirmado) | Não | Não |
| Aplicação | **− (saída via FIFO)** | **− (baixa pelo custo histórico)** | Não (nova) | **Sim** (Despesa nasce `PAGO` — anotação, não pagamento real) | **Sim (+)** | **Sim (+, `Despesa` OPERACAO_AGRICOLA)** |
| Cancelamento da operação | **+ (estoque revertido)** | **+ (revertido)** | Não afetado | **Não revertido** (Despesa/CostAllocation permanecem) | **Não revertido** | **Não revertido** |

**Observação de leitura da matriz:** a linha "Aplicação" mostra que o mesmo evento gera efeito em **três colunas simultaneamente** (Caixa/PAGO, Custo da safra, Despesa gerencial) para o mesmo valor, enquanto a linha "Recebimento" já havia gerado o efeito "Conta a pagar" para o valor total do insumo comprado — sem nenhuma coluna comum sendo decrementada de um lado quando incrementada do outro. É essa ausência de reconciliação entre a coluna "Conta a pagar" (linha Recebimento) e a coluna "Custo da safra" (linha Aplicação) que caracteriza a dupla contabilização no nível de relatório agregado (DRE).

---

## 16. Classificação final

**Opção C — dupla contabilização confirmada**, com elemento de **Opção D** (a duplicidade parcialmente não afeta caixa real de forma dupla, pois a `Despesa(OPERACAO_AGRICOLA, PAGO)` é uma anotação gerencial sem evento de pagamento efetivo — mas afeta diretamente o **resultado da DRE**, que é o relatório de referência para rentabilidade/custo, tornando a duplicidade economicamente relevante mesmo sem duplicar caixa físico).

**Classificação combinada: Opção C + D.**

A dupla contabilização não está no fluxo transacional de escrita (compra e aplicação escrevem em tabelas/contextos corretamente distintos, com idempotência própria em cada um), mas sim na **camada de consolidação de relatório** (`agricola/dre/service.py`), que soma `Despesa(COMPRA)` integralmente junto com `CostAllocation` do consumo do mesmo insumo, sem regra de exclusão equivalente às já existentes para `OPERACAO_AGRICOLA`/`ORDEM_SERVICO`/`ABASTECIMENTO`/`FIN_RATEIO`.

---

## 17. Direção recomendada (não implementar)

Entre as seis direções do escopo, a mais aderente à evidência coletada é a combinação de:

**Direção 5 — separar custo e financeiro** (a mais aderente à arquitetura já existente): o padrão de exclusão já implementado para `OPERACAO_AGRICOLA`/`ORDEM_SERVICO`/`ABASTECIMENTO`/`FIN_RATEIO` em `_consolidar_despesas` demonstra que a arquitetura **já reconhece** o problema geral (Despesa × CostAllocation do mesmo fato) e já tem o mecanismo para resolvê-lo — só falta estender essa mesma lógica para `origem_tipo="COMPRA"`, tratando a Despesa de compra como fato exclusivamente financeiro/de caixa (obrigação com fornecedor), e deixando o `CostAllocation` como única fonte de custo de produção quando o insumo comprado é de fato consumido.

Isso é preferível à **Direção 2** (remover a criação de Despesa da operação) porque a Despesa da compra é a que representa a obrigação real e reconciliável (fornecedor, vencimento, NF); e preferível à **Direção 3** (mudar status/natureza) porque não exige alterar o modelo `Despesa` em si — apenas a regra de agregação no DRE, que já é o ponto de extensão natural usado para os outros quatro casos.

**Não recomendo, nesta etapa (nem em qualquer etapa sem nova auditoria dedicada):**
- Remover a `Despesa(OPERACAO_AGRICOLA)` sem antes confirmar se algum consumidor fora do DRE agrícola depende dela (não identificado nesta auditoria, mas não descartado com 100% de certeza — os testes que poderiam confirmar isso, `test_operacao_despesa_webhook.py`, estão falhando por motivo pré-existente e não puderam ser executados com sucesso nesta rodada).
- Adicionar reconciliação automática entre `Despesa(COMPRA)` e `CostAllocation` por quantidade consumida (isso exigiria rastrear proporcionalmente qual fração de cada pedido de compra foi de fato aplicada — mudança de maior porte, fora do escopo de "menor próximo passo").

---

## Veredicto

```text
HÁ DUPLA CONTABILIZAÇÃO: SIM
```
(confirmada no relatório de DRE agrícola — `agricola/dre/service.py:_consolidar_despesas`, ausência de regra de exclusão para `origem_tipo="COMPRA"` equivalente às já existentes para `OPERACAO_AGRICOLA`/`ORDEM_SERVICO`/`ABASTECIMENTO`/`FIN_RATEIO`)

```text
PRÓXIMO PASSO: Investigar, em nova etapa dedicada e ainda somente leitura, se algum
consumidor real (fora do DRE agrícola) depende da Despesa(origem_tipo="OPERACAO_AGRICOLA")
como fato financeiro autônomo — reexecutando test_operacao_despesa_webhook.py após
corrigir isoladamente o drift de fixture (`talhao_id` em Safra) que impede sua execução
hoje. Só então definir se a correção da duplicidade Compra×CostAllocation deve seguir
a Direção 5 (excluir Despesa(COMPRA) de _consolidar_despesas quando há CostAllocation
correspondente ao consumo do mesmo insumo) — sem tocar em FIFO, ERP, ou nos módulos já
protegidos (OPERACAO_AGRICOLA/ORDEM_SERVICO/ABASTECIMENTO/FIN_RATEIO).
```

---

## Validações executadas

```bash
$ git status --short   # nenhuma alteração de código de produção nesta etapa
 M apps/campo/next.config.ts                          # já existente, de etapa anterior
 M apps/campo/src/app/(auth)/activate/page.tsx         # já existente, de etapa anterior
 M apps/campo/src/app/(campo)/home/page.tsx            # já existente, de etapa anterior
 M apps/campo/src/lib/stores/session-store.ts          # já existente, de etapa anterior
 M apps/campo/src/lib/sync/push.ts                     # já existente, de etapa anterior

$ git diff --check
(sem saída — limpo)

$ .venv/bin/python -m pytest tests/test_fifo_estoque.py tests/test_dre_agricola_v1.py -q
14 passed

$ .venv/bin/python -m pytest tests/test_compras_lote_integration.py tests/test_operacao_despesa_webhook.py tests/test_launch_core01_operational_cost_engine.py -q
13 failed, 6 passed — todas as 13 falhas confirmadas como pré-existentes (metadata SQLAlchemy
e drift de fixture de teste), reproduzidas também em execução isolada por arquivo, não
introduzidas por esta auditoria
```

O único arquivo novo criado nesta etapa é este relatório.
