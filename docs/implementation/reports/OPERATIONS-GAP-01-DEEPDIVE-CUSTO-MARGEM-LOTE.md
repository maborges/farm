# OPERATIONS-GAP-01 — Deep Dive: Custo/Margem por Lote Comercializado

> Investigação read-only. Nenhum código, model ou migration foi alterado.
> Escopo: `services/api/agricola/{colheita,custos,dre}`, `services/api/financeiro/comercializacao`.

## 1. Cadeia atual (com evidências)

Fluxo real de rastreabilidade:

```
OperacaoExecucao / EstoqueMovimento
        │
        ▼
RomaneioColheita ──▶ ProdutoColhido (agricola_produtos_colhidos)
        │                 │  safra_id, talhao_id, romaneio_id, commodity_id, quantidade
        │                 ▼
        │        ComercializacaoCommodity (financeiro_comercializacoes)
        │                 │  produto_colhido_id (FK), quantidade, valor_total
        │                 ▼
        │              Receita (financeiro) — origem_tipo="COMERCIALIZACAO", origem_id=comercializacao.id
```

Evidências:
- `services/api/agricola/colheita/models.py:20-97` — `ProdutoColhido` tem `safra_id` (linha 36), `talhao_id` (linha 39), `romaneio_id` (linha 42), `commodity_id` (linha 48), `quantidade`/`peso_liquido_kg` (linhas 67-69). É o "lote" físico real.
- `services/api/financeiro/comercializacao/models.py:79-83` — `ComercializacaoCommodity.produto_colhido_id` é FK **opcional** (`nullable=True`, `ondelete=SET_NULL`) para `agricola_produtos_colhidos.id`. Ou seja, o vínculo lote↔venda **existe no schema**, mas não é obrigatório — uma comercialização pode ser criada sem produto_colhido_id.
- `services/api/agricola/dre/service.py:344-355` — o DRE já faz o join completo `Receita → ComercializacaoCommodity → ProdutoColhido → ProductionUnit` (via `safra_id`+`talhao_id`/`area_id`), inclusive extraindo `produto_colhido_id`, `romaneio_id` para os metadados de cada item de receita (linhas 389-394).
- **O que falta**: não existe nenhuma tabela/campo `custo_lote` ou `margem_lote`. O grep original está correto — a agregação de custo nunca desce até o nível de `ProdutoColhido`/`ComercializacaoCommodity`; ela para em `ProductionUnit`.

## 2. Onde o custo já é acumulado hoje

- `services/api/agricola/custos/models.py:11-40` — `CostAllocation` (`cost_allocations`) é a fonte única de custo realizado. Granularidade: **por `production_unit_id`** (não por safra, não por talhão, não por lote), com `cost_category`, `amount`, `allocation_date`, `source` (OPERACAO/RATEIO/etc.), `allocation_method` (`DIRECT` ou `AREA_HA`).
- `ProductionUnit` (`agricola/production_units/`) é a unidade de produção real — tipicamente **safra × talhão** (um PU tem `safra_id` + `area_id`, ver join no DRE linha 350-354), não um lote comercial.
- `services/api/agricola/custos/allocation_service.py:57-137` — `registrar_allocations_fin_rateio` mostra como despesas financeiras rateadas (`fin_rateios`) são projetadas em `cost_allocations`, rateando por área (`AREA_HA`) quando uma despesa cobre múltiplos PUs (linhas 92-121: `valor_rateado * area_ha / total_area`).
- `services/api/agricola/custos/service.py:52-66` — `CustosService.get_resumo_safra` agrega `CostAllocation` **por safra** (join com `ProductionUnit.safra_id == safra_id`, opcionalmente filtrando por `talhao_id`). Essa é a única agregação hoje: **custo por safra (ou por safra+talhão)**, nunca por lote comercializado.
- **Resposta à pergunta 2**: sim, teoricamente essa agregação por PU poderia ser somada e rateada a um lote — porque `ProductionUnit` já corresponde ao par safra+talhão de onde o `ProdutoColhido` se origina. O elo que falta é: (a) uma regra de rateio de custo de PU→lote quando há N lotes por PU, e (b) persistir esse rateio em algum lugar (hoje é só join ad-hoc no DRE, calculado sob demanda, nunca gravado).

## 3. Onde a receita é registrada

- `services/api/financeiro/comercializacao/models.py` — `ComercializacaoCommodity` (`financeiro_comercializacoes`): `quantidade` (Numeric 14,3), `preco_unitario` (Numeric 12,4), `valor_total` (Numeric 15,2, "quantidade × preco_unitario"), `commodity_id`, `comprador_id`, `produto_colhido_id` (rastreabilidade, opcional), `receita_id` (vínculo com o financeiro, também opcional/solto — não é FK real, linha 101-104 é só `UUID` sem `ForeignKey`).
- O vínculo financeiro real é inverso: `Receita.origem_tipo == "COMERCIALIZACAO"` e `Receita.origem_id == ComercializacaoCommodity.id` (usado no join do DRE, linha 346 e 359).
- Cada `ComercializacaoCommodity` referencia no máximo **um** `ProdutoColhido` (campo singular `produto_colhido_id`), então uma venda não pode hoje ser composta de múltiplos lotes de origem — mas o inverso é possível e comum (um `ProdutoColhido`/lote pode ser vendido em múltiplas comercializações parciais, já que não há decremento de saldo modelado explicitamente no schema, apenas via `destino` = "VENDIDO"/"TRANSITO" em `ProdutoColhido.destino`, linha 87-90).

## 4. DRE/Dashboard atual

`services/api/agricola/dre/service.py` (1030 linhas) — é a peça mais avançada do sistema em direção ao objetivo, mas **para na safra/PU, não no lote**:

- Linha 344-396 (`_consolidar_receitas`): monta itens de receita por `ComercializacaoCommodity`, mas o `DRESourceItem` resultante é agrupado/reportado por `production_unit_id` e `safra_id` — o `produto_colhido_id` e `comercializacao_id` individuais sobrevivem apenas dentro do `meta` (dict solto, não indexado, não usado no cálculo de margem).
- Linha 560-565 (`_consolidar_costs`): busca `CostAllocation` filtrando por `production_unit_id.in_(pu_ids)` — soma tudo por PU/escopo, sem nenhuma tentativa de atribuir a um lote específico.
- Linha 168-175: `receita_bruta`, `custos_diretos`, `margem_bruta`, `resultado_operacional` são todos calculados **agregados no `scope`** (que pode ser 1 safra, 1 PU, ou uma unidade produtiva inteira — ver parâmetro `scope: dict` recebido de fora, não lido neste trecho mas referenciado em `scope["production_units"]` e `scope["unidade_produtiva_id"]`).
- **Conclusão**: o DRE é uma boa base para estender — o join `Receita→Comercializacao→ProdutoColhido→PU` já existe e captura `produto_colhido_id`/`comercializacao_id` como metadado; falta apenas "descer" o cálculo de custo do nível PU para o nível lote. Não é uma aproximação grosseira que mistura tudo indistintamente — a estrutura de dados intermediária (safra × talhão via PU) já é razoavelmente fina. O gap é a última milha: PU → lote individual quando há N lotes por PU no mesmo período.

## 5. Complexidade real — quantos lotes por safra?

- Cardinalidade real: **N `ProdutoColhido` por `ProductionUnit`** — não há nada no schema limitando quantos lotes (romaneios de colheita) um PU (safra×talhão) pode gerar; colheita normalmente ocorre em múltiplos dias/talhões, cada romaneio gera 1+ `ProdutoColhido`.
- Cardinalidade `ComercializacaoCommodity` : `ProdutoColhido` também é N:1 — um lote colhido pode ser vendido fracionado em várias comercializações (linha 79-83, FK singular em `ComercializacaoCommodity` aponta para 1 `ProdutoColhido`, mas nada impede múltiplas `ComercializacaoCommodity` apontando para o mesmo `produto_colhido_id`).
- Portanto: **não é 1:1 lote↔safra**. Rateio de custo por lote é inerentemente um problema de rateio compartilhado (custo do PU dividido entre N lotes, proporcional a alguma base — quantidade é a candidata óbvia).

## 6. Rastreabilidade existente para rateio proporcional

- Sim — `ProdutoColhido.quantidade`/`peso_liquido_kg`/`peso_liquido_comercial_kg` (linhas 67-77) e `ComercializacaoCommodity.quantidade` (linha 50) já capturam volumes reais em cada etapa.
- O DRE já demonstra o padrão de proporcionalização: `allocation_service.py` linhas 114-120 usa `valor_rateado * area_ha / total_area` para ratear despesas entre PUs. O mesmo padrão (substituindo `area_ha` por `quantidade_colhida`) seria aplicável para ratear custo de PU entre lotes.
- `quantidade_comercializada` e `produtos_por_romaneio` (dre/service.py linhas 340-341, 377-378) já são dicts acumulados por `romaneio_id`/`produto_colhido_id` dentro do DRE — evidência de que a infraestrutura de agregação por quantidade a nível de lote já é parcialmente calculada ali, só não persistida nem usada para custo.

## 7. Alternativas de design (não implementadas)

**A. Rateio proporcional por quantidade movimentada, calculado sob demanda (view/query), sem novo campo persistente**
- Como: estender `CustosService`/DRE com uma query que, para cada PU, soma `CostAllocation.amount` no período e divide proporcionalmente entre os `ProdutoColhido` daquele PU pela razão `quantidade_lote / quantidade_total_pu_periodo`; depois atribui a cada `ComercializacaoCommodity` a fração do custo do seu `produto_colhido_id`.
- Prós: não requer migration; reaproveita 100% do que já existe (CostAllocation, ProductionUnit, ProdutoColhido, join do DRE); reversível/auditável por recomputação.
- Contras: cálculo é caro em runtime se replicado fora do DRE; não há "congelamento" de custo — se novos custos forem lançados depois (custos financeiros com lag), a margem de vendas já fechadas muda retroativamente.
- Esforço: **baixo/médio** — é essencially generalizar o padrão de `allocation_service.py` linha 114-120 para a dimensão lote.

**B. Snapshot de custo médio por unidade no momento da colheita/baixa (novo campo em `ProdutoColhido`, ex. `custo_unitario_producao`)**
- Como: ao fechar romaneio/gerar `ProdutoColhido`, calcular `CostAllocation` acumulado do PU até a data e gravar `custo_unitario_producao = custo_acumulado / quantidade_colhida_total_ate_a_data`; a comercialização herda esse valor via `produto_colhido_id`.
- Prós: performance (custo pré-calculado, não recomputado a cada consulta de margem); histórico estável (não muda com lançamentos futuros).
- Contras: exige novo campo + migration (fora do escopo desta investigação); custos lançados após a colheita (ex. despesas financeiras com lag de rateio, frete pós-venda) ficam fora do snapshot, subestimando custo; requer decisão de produto sobre "ponto de corte" temporal.
- Esforço: **médio** — model change + service novo, mas não altera fluxo de comercialização existente.

**C. FK direta lote→CostAllocation (tabela de junção `produto_colhido_cost_allocation` com peso/percentual)**
- Como: nova tabela associativa persistindo o rateio calculado (uma vez, explicitamente) entre `ProdutoColhido` e `CostAllocation`, com `percentual_atribuido`.
- Prós: auditável, versionável, permite ajuste manual (override) por caso excepcional; separa claramente "cálculo" de "registro contábil".
- Contras: maior superfície de schema; precisa de processo/job para popular e manter consistência quando novos CostAllocation chegam depois; risco de dessincronia entre a tabela de junção e a realidade se o job não rodar.
- Esforço: **alto** — nova tabela, migration, service, job de manutenção, backfill do histórico.

## 8. Riscos (aplicáveis a qualquer alternativa)

- **Dupla contabilização**: se `ComercializacaoCommodity` sem `produto_colhido_id` (campo nullable, linha 79-83) coexistir com comercializações vinculadas, o rateio por lote cobriria só um subconjunto, mascarando margem real do resto — necessário decidir se `produto_colhido_id` deve virar obrigatório antes de qualquer rateio de custo confiável.
- **Custos indiretos não rateados**: `CostAllocation` hoje cobre custos diretos por PU; overhead/administrativo não rateado (mencionado no DRE como `custos_operacionais_section` separado, linha 152, 172) não entraria no custo do lote sob nenhuma das 3 alternativas sem trabalho extra — margem de lote seria "margem de contribuição direta", não margem líquida real.
- **Lotes de safras/talhões diferentes misturados no mesmo silo/depósito**: `ProdutoColhido.armazem_id` (linha 91-93) não é FK e não força unicidade por safra; se dois `ProdutoColhido` de safras diferentes forem armazenados juntos e uma venda referenciar apenas um `produto_colhido_id`, fisicamente pode estar vendendo grão misturado sem que o sistema capture — risco de rastreabilidade, não só de custo.
- **Custos lançados com atraso (lag)**: `fin_rateios`/despesas financeiras frequentemente chegam depois da venda (nota fiscal de insumo, boleto). Snapshot (Alternativa B) fica desatualizado; cálculo sob demanda (Alternativa A) muda a margem de vendas já fechadas retroativamente — ambos exigem decisão de produto sobre "congelar" ou não.
- **Rateio por quantidade pode distorcer custo por qualidade**: um lote de qualidade PREMIUM e outro REPROVADO do mesmo PU teriam custo/unidade idêntico sob rateio simples por quantidade, quando na prática custos de pós-colheita (classificação, secagem) podem diferir — risco de simplificação excessiva sem segmentar por `classificacao_id`/`qualidade_laudo_id` (já existentes em `ProdutoColhido`, linhas 51-59).

## 9. Recomendação de próximo passo (ainda sem implementar)

Começar pela **Alternativa A (rateio sob demanda)** como MVP, estendendo diretamente `agricola/dre/service.py` (que já tem 90% do join necessário) ou `CustosService`, adicionando uma função `get_margem_lote(comercializacao_id)` que:
1. Resolve o PU de origem do `produto_colhido_id`;
2. Soma `CostAllocation` do PU até a data de referência;
3. Rateia proporcionalmente por `quantidade` entre os `ProdutoColhido` do mesmo PU no período;
4. Retorna margem bruta do lote como número informativo (não persistido, não usado em rateio contábil oficial ainda).

Antes disso, **decisão de produto prévia necessária**: tornar `ComercializacaoCommodity.produto_colhido_id` obrigatório em novos fluxos (hoje nullable), senão qualquer rateio por lote nasce incompleto. Migração para Alternativa B/C só se justifica depois que o MVP validar a demanda real por essa métrica.
