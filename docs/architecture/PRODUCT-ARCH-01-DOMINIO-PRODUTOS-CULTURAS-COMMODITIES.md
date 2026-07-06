# PRODUCT-ARCH-01 — ARQUITETURA OFICIAL DE PRODUTOS, CULTURAS E COMMODITIES

## 1. Resumo executivo

O AgroSaaS já possui uma arquitetura parcialmente convergida para produtos, culturas e commodities, mas ela ainda não está inteiramente limpa o bastante para ser classificada como totalmente consistente para a v1.0.

A leitura do código mostra a seguinte direção oficial:

- `Produto` é o catálogo mestre de itens físicos e serviços de entrada, usado por compras, estoque, operações agrícolas, frota e pecuária.
- `ProdutoAgricola`, `ProdutoEstoque` e `ProdutoEPI` são especializações técnicas de `Produto`, não cadastros paralelos.
- `ProdutoCultura` é o cadastro oficial de culturas agrícolas.
- `Commodity` é a entidade oficial de mercado para negociação, qualidade, cotação e hedge.
- `ProdutoColhido` é o lote físico/comercial da colheita, derivado da operação agrícola e lastreado por `Commodity`.
- `ComercializacaoCommodity` vende `Commodity`, opcionalmente rastreada a um `ProdutoColhido`.
- `Hedge` opera sobre `Commodity`, com vínculo de contexto por `Safra`.

Ao mesmo tempo, ainda existem sobreposições relevantes:

- `agricola.cadastros.Cultura` legado ainda existe em paralelo ao cadastro oficial `ProdutoCultura`.
- `Safra` e `Cultivo` continuam carregando campos texto de cultura para compatibilidade.
- Hedge ainda mantém `commodity` textual além de `commodity_id`.
- `RomaneioColheita` ainda cria `Receita` automática por compatibilidade, antes da comercialização formal.
- A UI ainda faz fallback entre `/cadastros/culturas` e `/agricola/cadastros/culturas`.
- `ProdutoColhido` funciona como estoque específico da produção agrícola, paralelo ao estoque operacional clássico baseado em `Produto`.

## 2. Inventário de produtos/culturas/commodities

| Conceito | Model/Tabela | Owner | Função | É oficial? | Consumidores | Risco |
| -------- | ------------ | ----- | ------ | ----------: | ------------ | ----- |
| Produto | `core.cadastros.produtos.models.Produto` / `cadastros_produtos` | Core/Cadastros | Catálogo mestre de itens de entrada, insumos, peças, EPI e serviços | Sim | Compras, estoque, operações agrícolas, frota, pecuária | Médio |
| ProdutoAgricola | `ProdutoAgricola` / `cadastros_produtos_agricola` | Core/Cadastros | Extensão técnica/regulatória de uso agrícola | Sim | Cadastro de produtos, operações agrícolas | Baixo |
| ProdutoEstoque | `ProdutoEstoque` / `cadastros_produtos_estoque` | Core/Cadastros | Extensão física/logística para estoque | Sim | Estoque, compras | Baixo |
| ProdutoEPI | `ProdutoEPI` / `cadastros_produtos_epi` | Core/Cadastros | Extensão regulatória de EPI | Sim | RH, segurança, cadastro | Baixo |
| ProdutoCultura | `ProdutoCultura` / `cadastros_culturas` | Core/Cadastros | Cadastro oficial de culturas agrícolas | Sim | Cultivos, resolução de cultura, UI agrícola | Médio |
| Cultura legada | `agricola.cadastros.models.Cultura` / `culturas` | Agrícola legado | Cadastro antigo de cultura | Não | Fallback de rotas e clientes antigos | Alto |
| Commodity | `core.cadastros.commodities.models.Commodity` / `cadastros_commodities` | Core/Cadastros | Padrão de mercado para comercialização e hedge | Sim | Romaneios, produto colhido, comercialização, hedge, qualidade | Médio |
| CommodityClassificacao | `CommodityClassificacao` / `cadastros_commodities_classificacoes` | Core/Cadastros | Classes de qualidade da commodity | Sim | Produto colhido, qualidade, comercialização | Baixo |
| CotacaoCommodity | `CotacaoCommodity` / `cadastros_commodities_cotacoes` | Core/Cadastros | Histórico de preços de mercado | Sim | Hedge MTM, projeções | Baixo |
| ConversaoUnidade | `ConversaoUnidade` / `cadastros_conversao_unidades` | Core/Cadastros | Conversão de unidades por commodity | Sim | Hedge, comercialização, relatórios | Baixo |
| ProdutoColhido | `agricola.colheita.models.ProdutoColhido` / `agricola_produtos_colhidos` | Agrícola/Colheita | Lote colhido, padronizado e comercializável | Sim | Comercialização, rastreabilidade, dashboards, qualidade | Médio |
| RomaneioColheita | `agricola.romaneios.models.RomaneioColheita` / `romaneios_colheita` | Agrícola/Romaneios | Evento operacional de colheita e classificação inicial | Sim | ProdutoColhido, dashboards, qualidade | Médio |
| ComercializacaoCommodity | `financeiro.comercializacao.models.ComercializacaoCommodity` / `financeiro_comercializacoes` | Financeiro/Comercialização | Contrato de venda de commodity | Sim | Receita, rastreabilidade, DRE agrícola | Médio |
| ContratoFuturo/Hedge | `financeiro.hedge.models.ContratoFuturo` / `contratos_futuros_v2` | Financeiro/Hedge | Instrumento de proteção de preço | Sim | HedgeRegistro, snapshots MTM, exposição | Médio |
| Cultivo | `agricola.cultivos.models.Cultivo` / `cultivos` | Agrícola | Unidade de negócio agrícola por safra | Sim | Safra, hedge, operações, rentabilidade | Médio |
| Safra | `agricola.safras.models.Safra` / `safras` | Agrícola | Contexto agrícola superior | Sim | Cultivos, romaneios, hedge, dashboards | Médio |
| EstoqueMovimento | `operacional.models.estoque.EstoqueMovimento` / `estoque_movimentos` | Operacional/Estoque | Ledger de estoque operacional | Sim | Estoque, compras, consumo operacional | Baixo |
| LoteEstoque | `operacional.models.estoque.LoteEstoque` / `estoque_lotes` | Operacional/Estoque | Lote de estoque de `Produto` | Sim | Compras, FIFO, consumo, qualidade | Baixo |
| ItemPedidoCompra | `operacional.models.compras.ItemPedidoCompra` / `compras_itens_pedido` | Operacional/Compras | Item comprado vinculado a `Produto` | Sim | Compras, recebimento, despesa, estoque | Baixo |
| Produtos pecuários | `Produto` + `pecuaria.models.manejo.ManejoLote.produto_id` | Pecuária + Core/Cadastros | Vacina, medicamento, ração, mineral usados em manejo | Sim | Manejo, estoque, compras, custo | Médio |

## 3. Entidades oficiais

### Produto

`Produto` é o cadastro mestre físico de entrada da plataforma. Ele concentra identificação, tipo, unidade, conteúdo por embalagem e dados-base de custo e estoque.

Pelo código, ele foi desenhado explicitamente para:

- insumos agrícolas;
- insumos pecuários;
- almoxarifado e manutenção;
- EPI;
- serviços.

Não foi desenhado para:

- commodity negociada em mercado;
- produto colhido da safra;
- ativo biológico/animal.

Conclusão: `Produto` é o cadastro oficial de item comprado, estocado, consumido e usado operacionalmente.

### Commodity

`Commodity` não é um item físico de almoxarifado. É a categoria padronizada de mercado usada para:

- unidade comercial;
- classificação de qualidade;
- cotação;
- comercialização;
- hedge.

Conclusão: `Commodity` é a entidade oficial de negociação e mercado, não substitui `Produto`.

### ProdutoColhido

`ProdutoColhido` é o lote real da colheita já classificado e padronizado. Ele não substitui `Produto` e também não substitui `Commodity`.

Ele representa:

- o lote físico da produção;
- o lastro comercial da venda;
- a ponte entre romaneio, qualidade, armazenagem e comercialização.

Conclusão: `ProdutoColhido` é a entidade oficial da produção agrícola colhida.

## 4. Especializações de Produto

`ProdutoAgricola`, `ProdutoEstoque` e `ProdutoEPI` são especializações claras de `Produto`.

Evidências:

- usam FK única para `cadastros_produtos.id`;
- são carregados como `detalhe_agricola`, `detalhe_estoque` e `detalhe_epi`;
- `ProdutoService` cria e atualiza esses detalhes como extensões do mesmo aggregate.

Portanto:

- `ProdutoAgricola` não é cadastro paralelo;
- `ProdutoEstoque` não é cadastro paralelo;
- `ProdutoEPI` não é cadastro paralelo.

## 5. Cultura e ProdutoCultura

`ProdutoCultura` é o cadastro oficial atual de culturas. Ele vive em `cadastros_culturas` e é usado por:

- `CulturaResolutionService`;
- `Cultivo.cultivar_id`;
- UI moderna em `/cadastros/culturas`.

Mas ainda existe legado relevante:

- `agricola.cadastros.models.Cultura` continua existindo;
- a UI `useCulturas()` faz fallback para `/agricola/cadastros/culturas`;
- `Safra.cultura` e `Cultivo.cultura` continuam como texto de compatibilidade;
- `SafraCreate` aceita `cultura`, `cultivar_id`, `cultivar_nome` e `commodity_id` na raiz.

Conclusão:

- `ProdutoCultura` é a cultura oficial.
- `Cultura` antiga é compatibilidade legada.
- `Safra.cultura` e `Cultivo.cultura` ainda são campos de convivência, úteis para clientes antigos e resolução textual.

## 6. Commodity

`Commodity` é independente de `ProdutoCultura`.

Ela responde a outra pergunta:

- `ProdutoCultura`: o que está sendo cultivado agronomicamente.
- `Commodity`: como o resultado será padronizado e negociado no mercado.

Isso fica explícito em:

- `Cultivo.commodity_id`;
- `RomaneioColheita.commodity_id`;
- `ProdutoColhido.commodity_id`;
- `ComercializacaoCommodity.commodity_id`;
- `ContratoFuturo.commodity_id`.

Risco atual:

- hedge e frontend ainda precisam resolver commodity por texto quando faltam vínculos fortes;
- o contrato de hedge ainda guarda `commodity` textual além de `commodity_id`.

## 7. ProdutoColhido

`ProdutoColhido` não é `Produto`.

Ele é:

- um lote físico de produção agrícola;
- originado do romaneio ou de entrada manual;
- associado a uma `Commodity`;
- classificado por qualidade;
- usado como lastro de comercialização.

Ele também não é equivalente à `Commodity`:

- `Commodity` define o padrão de mercado;
- `ProdutoColhido` materializa um lote concreto daquela commodity.

## 8. Estoque

O estoque operacional clássico usa `Produto`.

Fluxo real:

`Produto` → `PedidoCompra`/`SolicitacaoCompra` → `LoteEstoque` → `EstoqueMovimento` → consumo operacional.

Isso vale para:

- sementes;
- defensivos;
- fertilizantes;
- ração;
- vacinas;
- medicamentos;
- peças;
- combustíveis;
- materiais gerais.

`ProdutoColhido` tem um estoque separado, mais agrícola/comercial, controlado em sua própria tabela e em seus próprios status.

Conclusão:

- estoque operacional = `Produto`;
- estoque de produção colhida = `ProdutoColhido`.

Esse desenho é válido, mas exige governança clara para evitar misturar os dois.

## 9. Compras

Compras usam `Produto`, não cadastro paralelo.

Evidências:

- `PedidoCompra.item_id` aponta para `cadastros_produtos`;
- `ItemPedidoCompra.produto_id` aponta para `cadastros_produtos`;
- `SolicitacaoCompra.produto_id` aponta para `cadastros_produtos`;
- o recebimento cria `LoteEstoque` e integra `Despesa`.

Conclusão:

- `Produto` é a fonte oficial de compras.

## 10. Comercialização

Comercialização usa `Commodity` como objeto principal de contrato e `ProdutoColhido` como lastro opcional de rastreabilidade.

Fluxo real:

`ProdutoColhido` → `ComercializacaoCommodity` → `Receita`

Mas o modelo também permite comercialização por `commodity_id` sem exigir `produto_colhido_id`.

Conclusão:

- contrato comercial: `Commodity`;
- rastreabilidade física: `ProdutoColhido`;
- receita financeira: `Receita`.

Risco:

- itens comerciais ainda podem nascer sem vínculo obrigatório ao lote físico.

## 11. Hedge

Hedge usa `Commodity` como referência oficial de mercado e `Safra` como contexto produtivo.

Fluxo real:

`Safra`/`Cultivo` → resolução de `Commodity` → `ContratoFuturo` → `HedgeRegistro` → `HedgePositionSnapshot`

Pontos observados:

- prioridade para `Cultivo.commodity_id`;
- fallback para resolução por cultura;
- fallback textual no frontend e backend;
- contrato ainda guarda `commodity` textual.

Conclusão:

- hedge oficial = `Commodity`;
- safra/cultivo fornecem contexto e exposição;
- ainda existe compatibilidade textual relevante.

## 12. Pecuária

Produtos pecuários compartilham `Produto`.

Isso vale para:

- vacina;
- medicamento;
- ração;
- mineral.

`ManejoLote.produto_id` aponta para `cadastros_produtos`, consolidando o uso oficial do catálogo unificado.

Não compartilham `Produto`:

- animal;
- lote animal;
- produção zootécnica em si.

Sobre leite e carne, a auditoria não mostrou um domínio oficial tão consolidado quanto o agrícola de `ProdutoColhido`; portanto, não devem ser tratados automaticamente como equivalentes ao fluxo agrícola.

## 13. Fluxos reais

### Insumo comprado

`Produto`
↓
`Compra`
↓
`Recebimento`
↓
`LoteEstoque`
↓
`EstoqueMovimento`
↓
`Consumo`
↓
`CostAllocation`

### Cultura agrícola

`ProdutoCultura`
↓
`Cultivo`
↓
`Safra`
↓
`CultivoArea`
↓
`ProductionUnit`

Observação: no código, `Safra` é contexto superior e `Cultivo` é a unidade de negócio agrícola. O fluxo lógico oficial é `Safra` contendo `Cultivo`, mas arquiteturalmente a cultura oficial entra por `ProdutoCultura` e materializa-se nos cultivos.

### Colheita

`Safra` / `Cultivo`
↓
`RomaneioColheita`
↓
`ProdutoColhido`
↓
`Commodity`

Na prática, o romaneio já nasce com `commodity_id` e gera automaticamente um `ProdutoColhido`.

### Comercialização

`ProdutoColhido`
↓
`ComercializacaoCommodity`
↓
`Receita`

### Hedge

`Safra` / `Cultivo`
↓
`Commodity`
↓
`ContratoFuturo`
↓
`Snapshot MTM`

### Pecuária

`Produto`
↓
`Vacina` / `Medicamento` / `Ração` / `Mineral`
↓
`Estoque`
↓
`Manejo`
↓
`Custo`

## 14. Duplicidades

As duplicidades relevantes encontradas foram:

- `ProdutoCultura` versus `agricola.cadastros.Cultura`.
- `ProdutoCultura` versus campos texto `Safra.cultura` e `Cultivo.cultura`.
- `Commodity` versus resolução textual de commodity por cultura.
- `Produto` versus `ProdutoColhido` para usuários que enxergam ambos apenas como “produto”.
- estoque operacional de `Produto` versus estoque agrícola/comercial de `ProdutoColhido`.
- comercialização com `commodity_id` sem obrigatoriedade de `produto_colhido_id`.

## 15. Compatibilidades legadas

Compatibilidades que devem permanecer, mas não devem ser ampliadas:

- `ProdutoCatalogo` como alias backward-compatible de `Produto`.
- rota legada `/agricola/cadastros/culturas`.
- fallback frontend de culturas entre cadastro novo e legado.
- `Safra.cultura` como cultura principal textual.
- `Cultivo.cultura` como campo textual ainda aceito.
- `ContratoFuturo.commodity` textual em paralelo a `commodity_id`.
- criação automática de `Receita` a partir de `RomaneioColheita`.
- entrada manual de `ProdutoColhido` sem romaneio.

## 16. Arquitetura alvo oficial

A arquitetura que o código atual mais fortemente aponta é:

```text
Produto
  ├── ProdutoAgricola
  ├── ProdutoEstoque
  └── ProdutoEPI
```

para catálogo físico de entrada;

```text
ProdutoCultura
  ↓
Cultivo
  ↓
Safra
  ↓
CultivoArea
  ↓
ProductionUnit
```

para contexto agronômico;

```text
Commodity
  ↓
RomaneioColheita
  ↓
ProdutoColhido
  ↓
ComercializacaoCommodity
  ↓
Receita
```

para produção comercializável;

```text
Safra / Cultivo
  ↓
Commodity
  ↓
ContratoFuturo
  ↓
HedgeRegistro
  ↓
HedgePositionSnapshot
```

para hedge e exposição.

## 17. Decisão

**Modelo C**

Existem fontes oficiais identificáveis, mas ainda há sobreposições relevantes demais para declarar o domínio plenamente consolidado antes da v1.0 sem guardrails e adapters adicionais.

## 18. O que entra na v1.0

- `Produto` como catálogo mestre de compras, estoque e consumo.
- `ProdutoAgricola`, `ProdutoEstoque`, `ProdutoEPI` apenas como extensões de `Produto`.
- `ProdutoCultura` como cultura oficial.
- `Commodity` como entidade oficial de mercado.
- `ProdutoColhido` como lote colhido oficial.
- `ComercializacaoCommodity` como venda oficial de commodity.
- `Hedge` baseado em `Commodity`.
- `Produto` compartilhado pela pecuária para insumos veterinários e nutricionais.

## 19. O que pode ficar para v1.1

- Encerrar fallback de UI para culturas legadas.
- Remover dependência de `agricola.cadastros.Cultura`.
- Tornar `commodity_id` obrigatório em todos os fluxos agrícolas relevantes.
- Reduzir ou eliminar `ContratoFuturo.commodity` textual.
- Revisar necessidade de `Safra.commodity_id` versus `Cultivo.commodity_id`.
- Reforçar vínculo obrigatório entre comercialização e `ProdutoColhido` quando houver estoque físico.
- Definir explicitamente o tratamento oficial para produtos pecuários de saída como leite/carne.

## 20. Plano recomendado

1. Formalizar `Produto`, `ProdutoCultura`, `Commodity` e `ProdutoColhido` como quatro camadas semânticas distintas.
2. Tratar `agricola.cadastros.Cultura`, `Safra.cultura`, `Cultivo.cultura` e `ContratoFuturo.commodity` como compatibilidades, não direção futura.
3. Impor guardrails para que novos fluxos de compras/estoque usem sempre `Produto`.
4. Impor guardrails para que novos fluxos de comercialização e hedge usem sempre `Commodity`.
5. Impor guardrails para que produto colhido comercializável seja representado por `ProdutoColhido`, não por `Produto`.
6. Revisar a inconsistência entre migration/schema/service de `Safra.commodity_id` e o model ORM auditado.

## Respostas objetivas às perguntas obrigatórias

### 1. O que é Produto?

Cadastro mestre físico de entrada. Abrange insumo, item de estoque, item comprado, item consumido e serviço. Não é commodity e não é produto colhido.

### 2. ProdutoAgricola é especialização de Produto ou cadastro paralelo?

Especialização de `Produto`.

### 3. ProdutoEstoque é especialização de Produto ou cadastro paralelo?

Especialização de `Produto`.

### 4. ProdutoCultura é Cultura oficial ou produto agrícola?

É a cultura oficial.

### 5. Commodity é produto?

Não. É cadastro de mercado e negociação.

### 6. ProdutoColhido é Produto?

Não. É lote físico colhido, resultado de romaneio ou entrada manual, lastro comercial e de rastreabilidade.

### 7. Insumos pertencem a Produto?

Sim. Sementes, defensivos, fertilizantes, adjuvantes, inoculantes, vacinas, medicamentos, rações, minerais, peças e combustível usam `Produto`.

### 8. Produtos pecuários compartilham Produto?

Sim para vacina, medicamento, ração e mineral. Não para animal. Leite/carne não apareceram ainda tão consolidados quanto o fluxo agrícola.

### 9. Comercialização usa Produto, Commodity ou ProdutoColhido?

Usa `Commodity` como objeto contratual e `ProdutoColhido` como lastro opcional de rastreabilidade.

### 10. Hedge usa Produto, Commodity, Cultura ou Safra?

Usa `Commodity`, contextualizada por `Safra` e resolvida preferencialmente a partir de `Cultivo`.

### 11. Estoque usa Produto ou ProdutoColhido?

Os dois, mas em camadas diferentes: estoque operacional usa `Produto`; estoque da produção agrícola usa `ProdutoColhido`.

### 12. Compras usa Produto ou cadastro próprio?

Usa `Produto`.

### 13. Existe duplicidade entre Cultura, ProdutoCultura e Commodity?

Sim. `ProdutoCultura` é cultura oficial, `Cultura` antiga ainda existe, e `Commodity` pode espelhar semanticamente a mesma cultura em contexto de mercado.

### 14. Existe risco de o usuário cadastrar a mesma coisa em mais de um lugar?

Sim. Exemplo típico: soja como `ProdutoCultura`, soja como `Commodity`, semente de soja como `Produto`, e soja colhida como `ProdutoColhido`.

## Critérios de aceite

- A função de `Produto` foi definida.
- A função de `ProdutoAgricola` foi definida.
- A função de `ProdutoEstoque` foi definida.
- A função de `ProdutoCultura` foi definida.
- A função de `Commodity` foi definida.
- A função de `ProdutoColhido` foi definida.
- A relação entre Cultura, Commodity e Cultivo foi definida.
- A relação entre Produto, Estoque e Compras foi definida.
- A relação entre ProdutoColhido, Comercialização e Hedge foi definida.
- Produtos pecuários foram considerados.
- Duplicidades foram identificadas.
- O que fica para v1.0 e v1.1 foi separado.
- Nenhuma alteração operacional foi feita.

## Pergunta final obrigatória

**Não integralmente ainda. Após esta execução, a referência arquitetural fica clara em documentação, mas a codebase ainda possui sobreposições relevantes de cultura legada, resolução textual e fluxos híbridos entre `Commodity`, `ProdutoCultura`, `Safra`, `Romaneio` e `ProdutoColhido`. Portanto, novos desenvolvimentos já podem seguir uma direção oficial clara, mas a plataforma ainda precisa consolidar compatibilidades antes de considerar o domínio livre de duplicidades estruturais.**
