# AgroSaaS - Matriz de Precedencia Economica Oficial

## Status

Documento oficial de governanca. Nao altera schema, endpoints, calculos ou dashboards.

## Objetivo

Formalizar, de forma canonica, qual e a fonte oficial de cada natureza economica no AgroSaaS e qual camada apenas reflete, apropria, realiza, provisiona ou consolida.

Este documento existe para evitar dupla contagem entre:

- `Receita`
- `Despesa`
- `LancamentoFinanceiro`
- `CostAllocation`
- `EstoqueMovimento`
- `LoteEstoque`
- `Rateio`
- `OperacaoAgricola`
- `RecebimentoParcial`
- `DevolucaoFornecedor`
- fluxos de compras
- fluxos de frota e abastecimento

## Premissas De Governanca

- A fonte oficial de um fato economico precisa ser unica.
- Camadas diferentes podem representar o mesmo evento, mas nao podem competir entre si como verdade oficial.
- Leitura gerencial, apropriaçao economica e realizacao financeira sao camadas distintas.
- Estoque fisico, valuation operacional e caixa nao sao a mesma coisa.
- Uma linha so entra direto na DRE futura quando estiver em sua camada oficial consolidada e sem duplicidade de origem.

## Documento Reaproveitado Como Base

Este arquivo consolida e formaliza, sem substituir, os guardrails ja existentes em:

- `docs/architecture/operational-workflow-governance.md`
- `docs/architecture/agro-domain-governance.md`
- `docs/contexts/financeiro/profissional/dre-rural.md`
- `docs/contexts/financeiro/enterprise/custo-producao-safra.md`
- `docs/contexts/step46-cross-module-integration-monetization-context.md`
- `docs/contexts/step48-cross-module-ownership-context.md`
- `services/api/agricola/alertas/service.py`

## 1. Mapa Operacional Das Entidades

| Entidade | Escreve | Consome | Apropria | Reflete | Realiza | Risco De Duplicidade |
| --- | --- | --- | --- | --- | --- | --- |
| `Receita` | `ReceitaService`, fluxos comerciais/operacionais | DRE futura, analises de resultado, alertas, relatórios de recebimento | Nao apropria custo; e fonte de receita | Pode ser refletida por `LancamentoFinanceiro` quando recebida | Nao realiza caixa sozinha | `LancamentoFinanceiro` pode repetir o mesmo fato se usado como receita primaria |
| `Despesa` | `DespesaService`, abastecimento externo, operacoes, frota, compras com origem automatica | DRE futura, custo de safra, alertas, conciliacao | Nao apropria; e obrigacao financeira | Pode ser refletida por `Rateio` e `CostAllocation` | Pode ser liquidada por `LancamentoFinanceiro` | Duplicidade ao somar despesa + pagamento + rateio sem regra de precedencia |
| `LancamentoFinanceiro` | `LancamentoService`, fluxos de recebimento/pagamento/caixa | Caixa, conciliacao, fluxo financeiro, DRE financeira futura | Nao apropria custo operacional por si so | Reflete receitas e despesas em caixa | Sim, e a realizacao financeira | Risco alto de dupla contagem se entrar como receita/despesa e tambem como liquidacao |
| `CostAllocation` | `allocation_service`, regras de operacao, rateio financeiro convertido, reconciliation guards | Custo por PU, cenarios, analises economicas, alertas | Sim, e a apropriacao economica oficial | Pode refletir `EstoqueMovimento`, `Despesa` ou `Rateio` | Nao realiza caixa | Duplicidade critica se houver mais de uma alocacao para a mesma origem e PU |
| `EstoqueMovimento` | `EstoqueService`, compras, operacoes, devolucoes, abastecimento interno, ajustes | Saldo, valuation, FIFO, reconciliação, alertas | Nao apropria sozinha | Reflete consumo/entrada fisica e valuation operacional | Nao realiza caixa | Risco alto se entrar direto na DRE ou se for transformada em custo por multiplas camadas |
| `LoteEstoque` | `EstoqueService`, compras, recebimentos | FIFO, valuation, auditoria, rastreabilidade | Nao apropria | Reflete custo historico por lote | Nao realiza caixa | Risco moderado se o lote for tratado como custo realizado em vez de base de valuation |
| `Rateio` | `DespesaService` | `allocation_service`, custo por PU, governanca economica | E a ponte do rateio financeiro para apropriacao | Reflete a distribuicao de uma despesa | Nao realiza caixa | Duplicidade se o mesmo rateio gerar mais de uma apropriacao para a mesma origem |
| `OperacaoAgricola` | `OperacaoService`, operacao de campo | custos operacionais, estoque, DRE futura, alertas | Nao apropria diretamente; e origem operacional | Reflete a execucao real do manejo | Nao realiza caixa | Risco se custo, execucao e apropriação forem agregados sem filtro de origem |
| `OperacaoExecucao` | `OperacaoService` | `CostAllocation`, estoque, alertas | Nao apropria sozinha | Reflete a evidência da execucao | Nao realiza caixa | Risco de duplicidade com `OperacaoAgricola` se ambos forem tratados como fatos independentes |
| `RecebimentoParcial` | `ComprasService` | estoque, lote, valuation, devolucoes, alertas | Nao apropria | Reflete a materializacao do recebimento | Nao realiza caixa | Risco se o recebimento for lido como despesa ou receita |
| `DevolucaoFornecedor` | `ComprasService` | estoque, reversao de valuation, alertas | Nao apropria | Reflete reversao operacional e fiscal | Nao realiza caixa | Risco alto se a devolucao nao apontar o movimento original |
| `Compras`/`PedidoCompra` | `ComprasService` | recebimento, estoque, custo, economia de compra | Nao apropria | Reflete compromisso operacional de compra | Nao realiza caixa | Risco de somar pedido + recebimento + despesa sem precedencia |
| `Frota`/`Abastecimento` | `AbastecimentoService`, servicos de frota | estoque de combustivel, despesa, custo operacional | Pode gerar apropriacao via despesa/allocacao, mas nao e a fonte primaria de DRE | Reflete consumo ou compra de combustivel | Pode realizar despesa quando externo | Risco de duplicar custo se combustivel interno, despesa externa e allocation forem somados sem regra |

## 2. Fontes Oficiais Por Natureza Economica

| Natureza | Fonte oficial | Camada derivada imediata | Comentario de governanca |
| --- | --- | --- | --- |
| Receita operacional | `Receita` | `LancamentoFinanceiro` quando houver recebimento | A receita nasce no fato comercial e nao no caixa |
| Receita financeira | `LancamentoFinanceiro` | extratos, conciliacao, resumos de caixa | E resultado financeiro, nao receita operacional |
| Receita realizada | `LancamentoFinanceiro` vinculado a `Receita` | recebimentos parciais/integrais | Nao deve ser somada novamente como receita primaria |
| Despesa operacional | `Despesa` | `LancamentoFinanceiro` quando liquidada | A despesa nasce como obrigacao/compromisso |
| Despesa financeira | `Despesa` e sua liquidacao em `LancamentoFinanceiro` | pagamentos, conciliacao, fluxo de caixa | A obrigacao e a realizacao nao podem ser somadas em duplicidade |
| Custo operacional | `CostAllocation` | `Despesa`, `EstoqueMovimento`, `Rateio` | Apropriacao economica e a camada oficial do custo por PU |
| Consumo fisico | `EstoqueMovimento` | `LoteEstoque` e saldo | E valuation operacional/fisico, nao DRE por si so |
| Apropriacao economica | `CostAllocation` | operacao, estoque, rateio, despesa | E a camada oficial de custo economico |
| Caixa realizado | `LancamentoFinanceiro` | conciliacao bancaria | E realizacao financeira, nao resultado operacional direto |
| Provisionamento | `Despesa` pendente e/ou previsao economica formal | `LancamentoFinanceiro` futuro | Provisao nao e caixa e nao e consumo fisico |
| Rateio | `Rateio` | `CostAllocation` financeiro | Rateio e mecanismo de distribuicao, nao linha final de DRE |
| Ajuste operacional | `EstoqueMovimento` de ajuste | `CostAllocation` ou reversao de custo | Ajuste e correcao, nao nova origem economica |
| Ajuste financeiro | `LancamentoFinanceiro` de ajuste | conciliacao e reclassificacao | Ajuste corrige o financeiramente registrado, nao cria novo fato economico |

## 3. Matriz De Precedencia Economica

Regra geral:

1. A camada mais alta da cadeia e a unica elegivel para consolidacao final.
2. Camadas inferiores podem refletir ou reconciliar, mas nao podem competir com a camada oficial.
3. Quando existir mais de uma representacao do mesmo fato, a camada mais alta prevalece.

| Natureza | Fonte Oficial | Pode refletir | Pode consolidar | Pode apropriar | Entra direto na DRE |
| --- | --- | --- | --- | --- | --- |
| Receita operacional | `Receita` | `LancamentoFinanceiro`, `RecebimentoParcial` | Sim, como receita consolidada da safra | Nao | Sim |
| Receita financeira | `LancamentoFinanceiro` | extrato bancario, conciliacao | Sim, no resultado financeiro | Nao | Sim, apenas na faixa financeira |
| Receita realizada | `LancamentoFinanceiro` vinculado a `Receita` | `Receita` | Sim, como caixa realizado | Nao | Nao, se a receita ja foi reconhecida na camada operacional |
| Despesa operacional | `Despesa` | `LancamentoFinanceiro`, `Rateio`, `CostAllocation` | Sim, como obrigacao consolidada | Sim, indiretamente quando origina custo | Sim, quando nao houver camada mais especifica de custo |
| Despesa financeira | `LancamentoFinanceiro` liquidando `Despesa` | `Despesa` | Sim, no resultado financeiro e no caixa | Nao | Sim, apenas na faixa financeira |
| Custo operacional | `CostAllocation` | `Despesa`, `EstoqueMovimento`, `OperacaoExecucao` | Sim, como custo por PU/safra | Sim | Sim |
| Consumo fisico | `EstoqueMovimento` | `LoteEstoque`, saldo, rastreabilidade | Sim, para valuation e reconciliacao | Nao | Nao |
| Apropriacao economica | `CostAllocation` | `Despesa`, `EstoqueMovimento`, `Rateio` | Sim | Sim | Sim |
| Caixa realizado | `LancamentoFinanceiro` | `Receita`, `Despesa` | Sim | Nao | Nao, salvo na faixa financeira de resultado |
| Provisionamento | `Despesa` em aberto ou provisao formal | `LancamentoFinanceiro` futuro | Sim, para conciliacao e competencia | Nao | Nao, sem regra de competencia |
| Rateio | `Rateio` | `Despesa` | Sim, como insumo da apropriacao | Sim, via `CostAllocation` | Nao |
| Ajuste operacional | `EstoqueMovimento` de ajuste | `CostAllocation` | Sim, para correcao de valuation | Sim, se reclassificado em custo | Nao |
| Ajuste financeiro | `LancamentoFinanceiro` de ajuste | `Despesa`/`Receita` originais | Sim, para reclassificacao e conciliacao | Nao | Nao |

## 4. Definicoes Criticas Oficiais

### 4.1 Receita != LancamentoFinanceiro

- `Receita` e a origem do fato economico comercial.
- `LancamentoFinanceiro` e a realizacao em caixa.
- Se o mesmo fato entrar pelas duas camadas sem regra de precedencia, ha dupla contagem.

### 4.2 CostAllocation != EstoqueMovimento

- `EstoqueMovimento` mede consumo, entrada, saida e valuation operacional.
- `CostAllocation` e a apropriacao economica oficial por unidade de producao.
- Um movimento pode gerar apropriacao, mas nao e a apropriacao final.

### 4.3 Despesa != CostAllocation

- `Despesa` e obrigacao financeira.
- `CostAllocation` e custo economico apropriado.
- Uma despesa pode originar custo, mas nao pode ser somada duas vezes como custo e obrigacao.

### 4.4 EstoqueMovimento Nao Entra Sozinho Na DRE

- Movimento de estoque e ledger operacional.
- Ele alimenta valuation e reconciliacao.
- A DRE futura deve consumir o resultado consolidado, nao o movimento bruto.

### 4.5 Produto.preco_medio E Snapshot/Fallback

- `Produto.preco_medio` e compatibilidade legada.
- Pode servir como fallback de interface e consulta resumida.
- Nao pode ser usado como fonte oficial de valuation, DRE ou custo historico real.

### 4.6 CostAllocation E A Apropriacao Oficial

- Toda alocacao economica oficial da safra deve passar por `CostAllocation`.
- Se o fato economico nao consegue gerar `CostAllocation`, ele ainda pode existir como evento operacional ou financeiro, mas nao como apropriacao oficial.

### 4.7 LancamentoFinanceiro E A Realizacao Financeira

- `LancamentoFinanceiro` representa pagamento, recebimento, ajuste ou caixa.
- Nao deve ser usado como substituto de receita, despesa ou custo operacional.

### 4.8 Despesa E A Obrigacao Financeira

- `Despesa` representa a obrigacao a pagar.
- Pode nascer de operacao, frota, abastecimento, compras ou outro fato rastreavel.
- A liquidacao pertence a `LancamentoFinanceiro`.

### 4.9 EstoqueMovimento E O Valuation Fisico/Operacional

- `EstoqueMovimento` representa a trilha fisica oficial.
- O lote e o movimento sustentam o valuation.
- Se houver custo, a apropriacao final precisa passar pela camada economica oficial.

## 5. Regras Anti-Duplicidade

### 5.1 Uma origem, uma apropriacao

- Uma mesma origem operacional nao pode gerar duas `CostAllocation` para a mesma `production_unit_id`.
- Guardrail existente: `ALLOCATION_POTENCIALMENTE_DUPLICADA`.

### 5.2 Uma origem automatica, uma despesa automatica

- Fluxos automatizados de despesa nao podem repetir a mesma origem.
- Guardrails existentes: `DESPESA_AUTOMATICA_SEM_ORIGEM` e `DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM`.

### 5.3 Movimento com custo precisa de apropriacao

- Se houver custo operacional em `EstoqueMovimento`, a DRE futura nao pode ignorar a camada economica correspondente.
- Guardrail existente: `MOVIMENTO_COM_CUSTO_SEM_ALLOCATION`.

### 5.4 Custo operacional sem reflexo economico e um risco

- Nenhum custo operacional relevante pode ficar sem reflexo financeiro ou reclassificacao economica.
- Guardrail existente: `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO`.

### 5.5 Valor operacional apropriado precisa bater com a soma consolidada

- Divergencia entre o valor operacional e a soma das apropriacoes deve ser tratada como reconciliacao, nao como nova origem.
- Guardrail existente: `DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO`.

### 5.6 Devolucao precisa do movimento original

- Devolucao de fornecedor nao deve ser processada sem rastreio do movimento original.
- Sem esse vinculo, o risco e de reversao sem base de valuation.

### 5.7 Pedido recebido nao pode virar custo duplicado

- `PedidoCompra`, `RecebimentoParcial` e `EstoqueMovimento` descrevem fases de um mesmo fato economico.
- Eles nao devem ser contados como custo, despesa e caixa ao mesmo tempo.

### 5.8 Receita recebida nao pode ser receita nova

- `Receita` reconhecida e `LancamentoFinanceiro` de recebimento podem coexistir.
- O recebimento financeiro nao cria uma nova receita.

## 6. Regras De DRE Futura

### Entra direto na DRE

- `Receita` consolidada na camada operacional.
- `CostAllocation` consolidada como custo economico.
- `Despesa` quando for a camada oficial de obrigacao e ainda nao houver camada mais especifica.
- `LancamentoFinanceiro` apenas na faixa financeira do resultado, quando representar realizacao real e nao repeticao de evento ja reconhecido.

### Nao entra direto na DRE

- `EstoqueMovimento`
- `LoteEstoque`
- `Rateio`
- `RecebimentoParcial`
- `PedidoCompra`
- `DevolucaoFornecedor`
- `OperacaoExecucao`
- `Produto.preco_medio`

### Consolida

- `CostAllocation` consolida custo economico por PU, safra e origem.
- `Despesa` consolida obrigacao e provisionamento.
- `LancamentoFinanceiro` consolida caixa e realizacao.
- `EstoqueMovimento` consolida valuation fisico e trilha de consumo.

### Apenas Reconcilia

- `EstoqueMovimento` sem apropriacao financeira ainda.
- `Despesa` sem liquidacao.
- `LancamentoFinanceiro` sem origem economica rastreavel.
- `Rateio` sem alocacao concluida.

### E Operacional

- `OperacaoAgricola`
- `OperacaoExecucao`
- `RecebimentoParcial`
- `DevolucaoFornecedor`
- `EstoqueMovimento`

### E Financeiro

- `Despesa`
- `LancamentoFinanceiro`
- `Rateio`
- liquidacoes e ajustes monetarios

### E Provisionado

- despesas abertas
- rateios pendentes de consolidacao
- custos ainda nao apropriados, mas rastreaveis

### E Realizado

- caixa efetivamente movimentado
- receita recebida
- despesa paga

## 7. Diretrizes Para Novas Features Economicas

Toda nova feature economica deve declarar explicitamente:

- fonte oficial
- impacto economico
- impacto operacional
- impacto financeiro
- se apropria
- se realiza
- se provisiona
- se consolida
- se entra na DRE

### Regra de entrada

Se a feature nao declarar sua posicao na matriz, ela nao pode nascer como fonte oficial nova.

### Regra de extensao

Se a feature apenas reflete um fato ja existente, ela deve ser implementada como camada derivada e nao como nova origem.

### Regra de bloqueio conceitual

Se a feature competir com `Receita`, `Despesa`, `CostAllocation`, `LancamentoFinanceiro` ou `EstoqueMovimento` pela mesma verdade economica, ela deve ser tratada como duplicidade, nao como modelagem nova.

## 8. Riscos Remanescentes

- Estoque historico legado ainda pode carregar divergencias antigas de valuation.
- Fluxos automatizados antigos podem repetir a mesma origem em mais de uma camada.
- `LancamentoFinanceiro` ainda e tentador como fonte universal de DRE, mas isso geraria dupla contagem.
- Compras, abastecimento e frota podem gerar fatos economicos parecidos com codigos diferentes.
- Ajustes manuais continuam sendo uma fonte de risco se nao tiverem origem rastreavel.
- `Produto.preco_medio` continua sendo um atalho perigoso se tratado como verdade oficial.

## 9. Proximos Passos Incrementais

1. Usar esta matriz como referencia obrigatoria em toda feature economica nova.
2. Fazer a futura DRE consumir apenas camadas consolidadas e deduplicadas.
3. Manter `CostAllocation` como camada oficial de apropriacao economica.
4. Manter `LancamentoFinanceiro` como camada oficial de realizacao financeira.
5. Manter `EstoqueMovimento` como camada oficial de valuation fisico/operacional.
6. Manter `Despesa` como camada oficial de obrigacao financeira.
7. Tratar qualquer nova fonte economica como excecao arquitetural a ser justificada.

## Decisao Final

O AgroSaaS passa a operar sob uma governanca economica formal onde:

- existe uma fonte oficial por natureza economica;
- camadas inferiores podem refletir, mas nao competir;
- `CostAllocation` e a apropriacao economica oficial;
- `LancamentoFinanceiro` e a realizacao financeira oficial;
- `EstoqueMovimento` e o valuation operacional/fisico oficial;
- a DRE futura devera consolidar, nao somar fatos paralelos.

