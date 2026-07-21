# SOIL-PLAN-EXEC-04D — Auditoria da Regra de Reconhecimento de Compras na DRE Agrícola

**Tipo:** Auditoria arquitetural e contábil, somente leitura. Nenhum código de produção, teste, DRE, compras, estoque, financeiro ou migration foi alterado.
**Data:** 2026-07-20

---

## 1. Resumo executivo

A causa raiz exata da dupla contabilização (confirmada em `SOIL-PLAN-EXEC-04B`) é: `agricola/dre/service.py:_consolidar_despesas` (linhas 573-744) já **possui** um mecanismo de exclusão para evitar somar `Despesa` duplicadamente junto com `CostAllocation` — mas essa lógica cobre apenas quatro origens (`OPERACAO_AGRICOLA`, `ORDEM_SERVICO`, `ABASTECIMENTO`, `FIN_RATEIO`, via `_despesa_tem_allocation_canonica`). **`origem_tipo="COMPRA"` nunca foi incluído nessa lista** — não é uma decisão arquitetural deliberada, é uma lacuna de implementação no mesmo padrão já usado para as outras quatro origens.

Uma regra ingênua de "excluir toda `Despesa(COMPRA)` que tenha qualquer `CostAllocation` relacionado" seria **incorreta**, pois:
- O `PedidoCompra` é hoje, na prática, **item único** (1 pedido = 1 produto = 1 `Despesa`, valor = `valor_total` do pedido inteiro) — não existe hoje pedido multi-item com naturezas distintas (frete/serviço/insumo) sendo decomposto em `Despesa`s separadas.
- O valor da compra normalmente é maior que o consumo em um único período — excluir a despesa inteira ao primeiro consumo eliminaria da DRE o saldo ainda em estoque, sem que esse saldo tenha sido apropriado como custo em nenhum lugar (nem `Despesa`, nem `CostAllocation`).
- A DRE **não trata estoque final como ativo** nem calcula CMV/variação de estoque — não há mecanismo compensatório para o saldo não consumido.
- Rastrear qual fração exata de uma compra foi consumida exigiria reconstruir o histórico de consumo FIFO por lote — tecnicamente possível via join multi-tabela, mas frágil e não suportado por nenhum campo direto hoje.

**Direção recomendada: DRE-COMPRA-A** (excluir toda `Despesa(COMPRA)` da DRE agrícola, com `CostAllocation` como fonte exclusiva de custo de produção) — justificada porque, na prática atual do sistema (1 pedido = 1 item, sempre passa por `LoteEstoque`), **toda `Despesa(COMPRA)` no módulo agrícola representa aquisição de estoque**, sem exceção confirmada de "despesa direta não-estocável" nascendo com esse `origem_tipo`. As despesas diretas não-estocáveis (mão de obra, frota, combustível) já usam outras origens (`RH_DIARIA`, `RH_EMPREITADA`, `ORDEM_SERVICO`, `ABASTECIMENTO`) e **já estão** corretamente reconciliadas na DRE.

---

## 2. Modelo atual

`PedidoCompra` (`operacional/models/compras.py:29-80`): campos `item_id`, `deposito_id`, `quantidade`, `unidade`, `valor_unitario`, `valor_total` — todos **singulares**, direto no pedido. Não há relacionamento `List[ItemPedidoCompra]` usado como fonte canônica.

`ItemPedidoCompra` (linhas 82-94) existe como tabela paralela, mas é **auto-gerada por compatibilidade**: `_get_or_create_item_pedido_principal` (`compras_service.py:207-230`) cria exatamente **um** `ItemPedidoCompra` espelhando os campos do próprio `PedidoCompra` (`produto_id=pedido.item_id`, `quantidade_solicitada=pedido.quantidade`, `preco_estimado_unitario=pedido.valor_unitario`). **Não há, em nenhum ponto do código lido, criação de mais de um `ItemPedidoCompra` por `pedido_id`.**

**Conclusão confirmada por código:** hoje, na prática, **1 `PedidoCompra` = 1 produto = 1 `Despesa`**.

---

## 3. Tipos de compra

`Produto.tipo` (`core/cadastros/produtos/models.py:228`) é `String(30)` **livre**, sem enum/CHECK constraint. Valores em uso real (`compras_service.py:1679-1680`):
```python
tipo_insumos = ["SEMENTE","DEFENSIVO","FERTILIZANTE","INOCULANTE","ADJUVANTE","RACAO","MEDICAMENTO","VACINA","MINERAL"]
tipo_operacoes = ["PECA","LUBRIFICANTE","COMBUSTIVEL","MATERIAL_GERAL","SERVICO"]
```
**"SERVICO" é um valor válido de `Produto.tipo`.** Um pedido de compra pode ter `item_id` apontando a um "produto" que é, na verdade, um serviço — e mesmo assim passa pelo mesmo fluxo de `LoteEstoque`/`EstoqueMovimento` (`compras_service.py:357-390`), pois **o código não bifurca por `tipo`**. Não há checagem de `produto.tipo == "SERVICO"` para pular a criação de lote/movimento de estoque.

**Resposta à pergunta da seção 4 do escopo:** *`origem_tipo="COMPRA"` identifica exclusivamente aquisição via `PedidoCompra`/`recebimento`, e — pela estrutura de dados atual — **sempre passa por `LoteEstoque`**, mesmo quando o produto subjacente é logicamente um serviço.* Não há mistura de fatos econômicos diferentes dentro de uma mesma `Despesa(COMPRA)` (porque cada uma corresponde a exatamente um pedido de item único), mas há um risco estrutural: um pedido de "produto tipo SERVICO" ainda geraria `LoteEstoque` (fisicamente incorreto, mas não é o foco desta auditoria — está fora do escopo autorizado alterar).

---

## 4. Granularidade

Confirmado em `_garantir_despesa_financeira_compra` (`compras_service.py:142-205`): **uma única `Despesa` por `PedidoCompra`**, não por item, não por recebimento parcial.
- Idempotência: `(tenant_id, origem_tipo="COMPRA", origem_id=pedido.id, ativo=True)` (linhas 148-157) — reusa a Despesa existente, nunca duplica por recebimento parcial subsequente.
- `valor_total=float(pedido.valor_total or 0.0)` (linha 189) — valor total do pedido inteiro.
- Frete, impostos, desconto: busca por esses termos em `compras_service.py` retornou **zero ocorrências**. `_materializar_item_recebimento` (linhas 330-434) usa apenas `custo_unitario = item_recebido.preco_real_unitario` (linha 338), propagado tanto ao `LoteEstoque.custo_unitario` quanto ao valor da `Despesa` — **não há rateio de frete/impostos/desconto em nenhum dos dois**.

**Exemplo real (pedido misto do escopo original) — não ocorre hoje:** como confirmado na seção 2, o sistema não suporta hoje um pedido "item A + item B + frete + serviço" em linhas separadas — cada pedido é de um único produto. O cenário hipotético do escopo (`Pedido → item A, item B, frete, serviço`) é **estrutural, não implementado** — se fosse implementado no futuro, a arquitetura atual criaria uma única `Despesa` somando tudo, sem discriminação, o que seria um problema adicional a resolver separadamente (fora do escopo desta decisão).

---

## 5. Rastreabilidade disponível

| Origem | Destino | Campo de vínculo | Relação confiável? |
|---|---|---|---:|
| `Despesa` | `PedidoCompra` | `origem_id` (`Despesa.origem_id = pedido.id`) | **Sim** |
| `PedidoCompra` | `ItemPedidoCompra` | `pedido_id` | Sim, mas sempre 1:1 na prática |
| `ItemRecebimento` | `LoteEstoque` | `lote_id` | Sim |
| `LoteEstoque` | `EstoqueMovimento` (entrada) | `EstoqueMovimento.lote_id` + `origem_id=pedido.id` na entrada | Sim |
| `EstoqueMovimento` (saída/consumo) | `EstoqueMovimento` (entrada original) | **Não existe campo direto** — só via `lote_id` compartilhado | **Não** — indireto, requer reconstrução |
| `EstoqueMovimento` (saída) | `CostAllocation` | `CostAllocation.inventory_movement_id` | Sim |

`LoteEstoque` (`operacional/models/estoque.py:43-67`) **não tem campo `pedido_id`/`origem_compra_id`** — o vínculo lote→pedido existe apenas indiretamente via o `EstoqueMovimento` de ENTRADA (que carrega `origem_id=pedido.id`).

**Resposta direta à pergunta da seção 6:** *Sim, tecnicamente é possível hoje* correlacionar uma fração de `Despesa(COMPRA)` com uma fração de `CostAllocation`, via cadeia: `CostAllocation.inventory_movement_id → EstoqueMovimento(saída).lote_id → LoteEstoque → EstoqueMovimento(entrada, mesmo lote_id, origem_id=pedido.id) → Despesa.origem_id`. **Porém é frágil e não trivial**: o consumo é FIFO por lote (uma compra pode gerar um lote consumido em múltiplas operações, em datas/safras diferentes), então uma correlação exata "fração consumida × fração da despesa" exigiria reconstruir a sequência de consumo do lote, não um JOIN 1:1 simples — **não há campo direto e único que resolva isso sem essa reconstrução**.

---

## 6. Regime da DRE

Confirmado por leitura de `agricola/dre/service.py`:
- **Período**: `func.coalesce(Despesa.competencia, Despesa.data_emissao)` (linhas 641, 647, 732-733) — regime de **competência** (emissão/competência, não pagamento).
- **Status**: `desp_stmt = select(Despesa).where(Despesa.tenant_id == self.tenant_id, Despesa.ativo == True)` (linha 637) — **nenhum filtro de `status`**. Despesas `A_PAGAR` (não pagas) entram normalmente, junto com `PAGO`. Confirmado por grep: nenhuma ocorrência de "A_PAGAR"/"PAGO" no arquivo do DRE.
- **CMV / variação de estoque**: busca por "CMV", "custo_mercadoria_vendida", "variação de estoque", "saldo_estoque" no arquivo do DRE — **zero ocorrências**. Não há tratamento de estoque final como ativo, nem dedução de variação de estoque do custo.
- **`CostAllocation.allocation_date`**: campo `Date` (`agricola/custos/models.py:37`), usado como referência de período em `_periodo_clause` — reflete a data econômica da alocação de consumo (operação realizada), não a data da compra.

```text
REGIME REAL DA DRE: COMPETÊNCIA (baseado em Despesa.competencia/data_emissao, sem filtro de status pago/a pagar) — MISTO, no sentido de que soma custo por consumo (CostAllocation, competência da aplicação) e despesa por emissão/competência do documento (Despesa), sem reconciliar as duas dimensões temporais entre si para o mesmo insumo.
```

---

## 7. Cenários obrigatórios

| Cenário | DRE atual | DRE desejável | Diferença |
|---|---:|---:|---:|
| **A** — compra R$10.000, consumo R$0 | R$10.000 (Despesa integral) | R$0 (nada consumido ainda; a obrigação financeira existe mas não é custo de produção do período) | R$10.000 de excesso |
| **B** — compra R$10.000, consumo R$2.000, saldo R$8.000 | R$10.000 (Despesa) + R$2.000 (CostAllocation) = R$12.000 | R$2.000 (só o CostAllocation) | R$10.000 de excesso |
| **C** — compra R$10.000, consumo total R$10.000 no mesmo período | R$10.000 (Despesa) + R$10.000 (CostAllocation) = R$20.000 | R$10.000 | R$10.000 de excesso |
| **D** — compra em dezembro, consumo em janeiro | Dezembro: R$10.000 (Despesa). Janeiro: R$X (CostAllocation) | Dezembro: R$0. Janeiro: R$X | Dezembro distorcido por 100% do valor da compra |
| **E** — saldo inicial sem compra registrada no sistema | Só CostAllocation entra (sem Despesa correspondente) — **já correto hoje**, pois não há Despesa(COMPRA) para esse insumo | Idêntico | Nenhuma |
| **F** — múltiplos itens, consumo parcial de apenas um | Não ocorre hoje (pedido é de item único, seção 2) | N/A | N/A — cenário não implementado na arquitetura atual |
| **G** — compra de serviço sem entrada em estoque | Hoje **sempre** gera `LoteEstoque` (seção 3, produto tipo SERVICO não bifurca) — se o serviço nunca for "consumido" via operação, a Despesa nunca seria excluída em nenhuma regra baseada em CostAllocation, permanecendo corretamente como despesa direta | Deveria permanecer na DRE (é uma despesa real do período), mas fisicamente não deveria gerar estoque — problema estrutural fora do escopo desta decisão | Nenhuma diferença na regra de exclusão em si; risco estrutural separado |
| **H** — frete incorporado ou não ao custo do lote | Frete nunca é incorporado (seção 4) — não afeta a regra de exclusão da DRE, mas o `CostAllocation` subestima o custo real do insumo aplicado (o frete nunca é reconhecido em lugar nenhum como custo de produção) | Frete deveria compor `custo_unitario` do lote | Gap identificado, fora do escopo desta decisão |
| **I** — devolução parcial ao fornecedor | `LoteEstoque` é revertido (confirmado nas auditorias 04/04B), mas **não há evidência de ajuste no `valor_total` da `Despesa(COMPRA)`** — a obrigação financeira permanece pelo valor original mesmo após devolução física | Deveria refletir o valor líquido após devolução | Divergência entre estoque físico e obrigação financeira registrada — gap pré-existente, fora do escopo desta decisão |
| **J** — cancelamento da operação após consumo e apropriação | `Despesa(OPERACAO_AGRICOLA)` e `CostAllocation` permanecem órfãos (confirmado em `SOIL-PLAN-EXEC-04B`/`04C`) — não afeta a regra de exclusão de `Despesa(COMPRA)` diretamente, mas mantém o "consumo" contabilizado mesmo revertido | Deveria reverter `CostAllocation` também | Gap já documentado, fora do escopo desta decisão |

---

## 8. Despesas diretas não representadas por `CostAllocation`

Confirmadas, todas com `origem_tipo` **diferente** de `"COMPRA"`, todas **já cobertas** pela reconciliação existente em `_consolidar_despesas`:
- `services/api/rh/service.py:165` — `origem_tipo="RH_DIARIA"` (mão de obra diária).
- `services/api/rh/service.py:264` — `origem_tipo="RH_EMPREITADA"` (mão de obra contratada).
- `services/api/operacional/services/frota_service.py:287,305,322,370,388` — `origem_tipo="ORDEM_SERVICO"` (manutenção/peças/serviço terceirizado de frota).
- `services/api/operacional/services/abastecimento_service.py:77,97` — `origem_tipo="ABASTECIMENTO"` (combustível).

Não foi encontrada nenhuma `Despesa` com `origem_tipo` dedicado para "análise laboratorial", "consultoria", "arrendamento", "energia" — essas, se existirem no sistema, provavelmente são lançadas manualmente via `origem_tipo="FIN_RATEIO"` ou sem automação (não confirmado nesta auditoria, fora do escopo verificar lançamentos manuais).

**Resposta direta:** *Não — se todas as `Despesa(COMPRA)` forem excluídas da DRE agrícola, nenhum custo agrícola legítimo desaparece*, porque nenhuma despesa direta legítima usa `origem_tipo="COMPRA"` — todas as categorias de despesa direta confirmadas (mão de obra, frota, combustível) já usam origens próprias, já reconciliadas.

---

## 9. Plano de contas e categoria

`PlanoConta` (`financeiro/models/plano_conta.py:9-19`): campos `tipo` (RECEITA|DESPESA), `natureza` (SINTETICA|ANALITICA), `categoria_rfb` (texto livre, mapeado para "grupos do Livro Caixa do Produtor Rural (RFB)" — ex. CUSTEIO, INVESTIMENTO — conforme docstring do modelo), `is_sistema`, `ativo`.

**Não existe nenhum campo que distinga "aquisição de estoque" de "despesa direta do período"** no plano de contas. A resolução usada por `compras_service.py:132-134` é o mesmo fallback genérico (`categoria_rfb == "CUSTEIO"`, `natureza == "ANALITICA"`) usado por qualquer outra despesa operacional — **não há discriminador estrutural confiável no plano de contas** para basear uma exclusão seletiva.

**Conclusão:** a decisão de exclusão não pode (e não deve) se basear em plano de contas, categoria RFB, ou texto livre — deve se basear em `origem_tipo`, que é o único campo estruturado e já usado consistentemente para as outras quatro reconciliações existentes.

---

## 10. Devoluções e recebimentos parciais

- Recebimento parcial: idempotência da `Despesa` é por `pedido.id` (não por `recebimento.id`) — um segundo recebimento parcial do mesmo pedido **não gera segunda Despesa** (retorna a existente). Não confirmado se o `valor_total` é reajustado incrementalmente por recebimento parcial subsequente (o valor gravado na primeira chamada bem-sucedida parece ser definitivo, `valor_total=pedido.valor_total`, que já é o total do pedido, não do recebimento).
- Devolução: `LoteEstoque` é revertido (confirmado nas auditorias 04/04B via `DevolucaoFornecedor`/`ItemDevolucao`), mas **não há evidência de ajuste da `Despesa(COMPRA).valor_total`** correspondente.
- Impacto na DRE: como a `Despesa(COMPRA)` permanece pelo valor original mesmo após devolução física, uma regra de exclusão total (DRE-COMPRA-A) **remove esse gap da visão da DRE agrícola** — a DRE deixa de exibir qualquer valor de compra, então a divergência entre valor devolvido e valor financeiro registrado deixa de afetar o resultado agrícola (ainda existiria no módulo financeiro genérico, fora do escopo da DRE agrícola).

---

## 11. Testes executados

```bash
$ .venv/bin/python -m pytest tests/test_fifo_estoque.py tests/test_dre_agricola_v1.py tests/integration/financeiro/test_despesas.py -q
24 passed in 52.78s   (6 FIFO + 8 DRE + 10 despesas genéricas)

$ .venv/bin/python -m pytest tests/test_compras_lote_integration.py -q
2 failed, 5 passed in 16.22s
FAILED test_recebimento_cria_lote_e_fifo_consome — NoReferencedTableError (metadata SQLAlchemy)
FAILED test_p0_2_supplier_batch_in_itemrecebimento — mesma causa
```
**Classificação:** as 2 falhas são **pré-existentes** — já documentadas e reproduzidas de forma idêntica nas auditorias `SOIL-PLAN-EXEC-04B`/`04C0` (causa: `NoReferencedTableError` de registro de metadata SQLAlchemy ao rodar o arquivo isoladamente, não relacionada a `Despesa`/DRE/compras em si). Classificação: **metadata/infraestrutura, não relacionada** a esta auditoria. Nenhuma correção aplicada.

**Nenhum teste existente** cobre especificamente: exclusão de `Despesa(COMPRA)` da DRE quando há `CostAllocation` do consumo do mesmo insumo (o cenário central desta auditoria) — confirma que a lacuna nunca foi coberta por teste de regressão, reforçando que é uma omissão de implementação, não uma decisão testada e validada.

---

## 12. Respostas obrigatórias

```text
1. TODA DESPESA(COMPRA) É AQUISIÇÃO DE ESTOQUE: SIM
   (confirmado por código: todo PedidoCompra gera LoteEstoque no recebimento,
   independente do tipo do produto — não há bifurcação por tipo="SERVICO")

2. EXISTEM COMPRAS DE SERVIÇO OU DESPESA DIRETA COM origem_tipo="COMPRA": SIM, ESTRUTURALMENTE POSSÍVEL,
   MAS SEM EVIDÊNCIA DE USO REAL — Produto.tipo="SERVICO" é um valor válido, mas mesmo assim
   passa pelo fluxo de estoque; nenhuma despesa direta confirmada usa origem_tipo="COMPRA"
   (todas usam RH_DIARIA/RH_EMPREITADA/ORDEM_SERVICO/ABASTECIMENTO)

3. A DRE ATUAL USA COMPETÊNCIA, CAIXA OU MODELO MISTO: COMPETÊNCIA (por Despesa.competencia/
   data_emissao, sem filtro de status pago/a pagar), mas sem reconciliação temporal entre a
   competência da despesa de compra e a competência do consumo (CostAllocation.allocation_date)

4. É POSSÍVEL LIGAR COMPRA A COSTALLOCATION: PARCIALMENTE — tecnicamente via join multi-tabela
   (Despesa→PedidoCompra→EstoqueMovimento(entrada)→LoteEstoque→EstoqueMovimento(saída)→CostAllocation),
   mas sem campo direto e sem suporte a rateio proporcional fração-a-fração sem reconstrução do FIFO

5. EXCLUIR TODA COMPRA É SEGURO: SIM, NO ESTADO ATUAL DO CÓDIGO (1 pedido = 1 item = sempre estoque,
   nenhuma despesa direta confirmada usando essa origem) — COM A RESSALVA de que, se o sistema
   evoluir para suportar pedidos multi-item ou compra de serviço sem estoque, essa premissa
   precisará ser revalidada

6. EXCLUSÃO PROPORCIONAL É VIÁVEL: NÃO RECOMENDADA — exigiria reconstrução de FIFO por lote,
   complexidade desproporcional ao ganho, sem campo de suporte direto hoje

7. REGRA RECOMENDADA: excluir Despesa(origem_tipo="COMPRA") de _consolidar_despesas quando
   existir qualquer CostAllocation cujo EstoqueMovimento de origem remonte (via lote_id) a um
   EstoqueMovimento de entrada com origem_id igual ao PedidoCompra da despesa — equivalente
   em espírito às quatro reconciliações já existentes, mas dado que hoje 1 despesa = 1 pedido
   sempre integralmente estocável, a forma mais simples e segura é: se existe QUALQUER
   CostAllocation relacionado (mesmo parcial), excluir a Despesa inteira da DRE (ela nunca
   deveria ter entrado como custo de produção; ela é uma obrigação financeira, não um CMV) —
   e não excluir apenas quando NÃO há nenhum CostAllocation associado (compra ainda 100% em
   estoque, caso em que ela nunca deveria aparecer como custo de produção mesmo assim,
   reforçando DRE-COMPRA-A: excluir SEMPRE, incondicionalmente, não apenas quando há consumo)

8. ARQUIVOS QUE PRECISARIAM SER ALTERADOS: agricola/dre/service.py
   (_consolidar_despesas, adicionar exclusão incondicional para origem_tipo="COMPRA",
   análogo às linhas 684-693 já existentes para as outras quatro origens)

9. TESTES QUE PRECISARIAM SER CRIADOS OU AJUSTADOS: novo teste em test_dre_agricola_v1.py
   cobrindo Cenário B/C desta auditoria (compra + consumo parcial/total no mesmo período,
   validando que só o CostAllocation entra no resultado, não a Despesa(COMPRA))
```

---

## 13. Direção final

```text
DRE-COMPRA-A
Excluir toda Despesa(origem_tipo="COMPRA") da DRE agrícola.
```

**Justificativa consolidada:** ao contrário do temor inicial do escopo desta auditoria (que uma regra "excluir toda compra" pudesse eliminar indevidamente saldo não consumido da visão financeira), a investigação mostra que **a DRE agrícola não deveria estar reconhecendo o valor da compra como custo de produção em nenhum momento** — nem parcial, nem total — porque:
1. `CostAllocation` já é, e deve continuar sendo, a **única** fonte de custo de produção (reflete exatamente o que foi consumido, pelo custo histórico FIFO correto).
2. `Despesa(COMPRA)` é uma obrigação financeira/fluxo de caixa (compra + pagamento ao fornecedor) — pertence ao módulo financeiro genérico (Contas a Pagar), não à DRE **agrícola** (que mede resultado de produção, não fluxo de caixa).
3. A ausência de tratamento de "estoque final como ativo"/CMV na DRE agrícola confirma que ela **nunca foi desenhada** para reconhecer despesas de aquisição de insumo diretamente — o padrão correto, já aplicado às outras quatro origens, é reconhecer apenas via `CostAllocation`.
4. Não há, hoje, nenhuma despesa direta legítima usando `origem_tipo="COMPRA"` que se perderia com a exclusão total.

Isso é consistente com **DRE-COMPRA-A** puro (excluir sempre), não com uma variante condicional B/C — a distinção entre "compra estocável" e "despesa direta" (que motivaria B) já é feita, na prática, pelo próprio `origem_tipo` (COMPRA é sempre estoque; despesas diretas usam outras origens) — não é necessário introduzir classificação nova (D) nem proporcionalidade (C).

---

## 14. Plano mínimo de implementação (não executado nesta etapa)

1. Em `agricola/dre/service.py:_consolidar_despesas`, adicionar `origem_tipo == "COMPRA"` a uma nova condição de exclusão incondicional (análoga à estrutura das linhas 684-693, mas sem exigir a existência de um `CostAllocation` associado — excluir sempre, pois a compra nunca deveria ter entrado como custo de produção).
2. Ajustar a contagem `excluidas` (linha 681+) para refletir também essas exclusões, mantendo a semântica de auditoria já existente no método.
3. Adicionar teste cobrindo Cenário B/C (compra + CostAllocation do mesmo insumo no mesmo período — validar que apenas o CostAllocation entra no resultado).
4. Validar contra a suíte de regressão já usada nas etapas anteriores (FIFO, DRE, despesas, compras).

---

## 15. Riscos

- **Estrutural, pré-existente, fora do escopo desta correção:** se o sistema evoluir para suportar pedidos multi-item (ex.: um pedido com insumo + frete + serviço em linhas separadas), a premissa "toda Despesa(COMPRA) é sempre 100% estocável" deixaria de ser universalmente verdadeira, exigindo reavaliação da regra (possível migração futura para DRE-COMPRA-B/D).
- **Produto tipo "SERVICO" passando por fluxo de estoque** (seção 3) é um risco estrutural separado (fisicamente incorreto), não corrigido por esta decisão — a exclusão da Despesa da DRE não resolve o fato de que um "serviço" comprado ainda geraria `LoteEstoque` indevidamente.
- **Devolução sem ajuste de `Despesa.valor_total`** (seção 10) — a exclusão total da DRE agrícola neutraliza o impacto desse gap especificamente na DRE, mas o gap financeiro (módulo genérico de Contas a Pagar) permanece, fora do escopo desta decisão.
- **Cancelamento de operação não reverte `CostAllocation`** (já documentado em `SOIL-PLAN-EXEC-04C`) — independente desta decisão, permanece um gap a resolver separadamente.

---

## Validações executadas

```bash
$ git status --short
(nenhuma alteração introduzida por esta auditoria)

$ git diff --check
(sem saída — limpo)
```

O único arquivo novo criado nesta etapa é este relatório.

---

## Veredicto

```text
SOIL-PLAN-EXEC-04D
STATUS: GO
```

```text
DIREÇÃO RECOMENDADA: DRE-COMPRA-A
```

```text
PRÓXIMO PASSO: Implementar a exclusão incondicional de Despesa(origem_tipo="COMPRA") em
agricola/dre/service.py:_consolidar_despesas (análoga às quatro exclusões já existentes),
acompanhada de um teste de regressão cobrindo compra + CostAllocation do mesmo insumo no
mesmo período (Cenário B/C desta auditoria). Esta é agora a correção definitiva pendente
desde SOIL-PLAN-EXEC-04B, com a regra exata e o risco de "exclusão indevida de saldo não
consumido" descartado pela evidência de que a DRE nunca deveria ter reconhecido valor de
compra como custo de produção em nenhuma fração.
```
