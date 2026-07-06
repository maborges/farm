# PILOT-00B - Auditoria de Cadastros Mestres

## Resposta objetiva

O modelo atual de Cadastros Mestres do AgroSaaS **nao esta totalmente consistente como base definitiva de implantacao, operacao e evolucao futura**.

Ele esta **razoavelmente unificado para Produtos, Commodities e Unidades de Medida**, mas ainda possui **inconsistencias estruturais relevantes**, principalmente em:

- `Cultura` duplicada entre o fluxo legado de Agricola e o catálogo unificado novo;
- uso paralelo de caminhos legados e novos para `Produto`;
- `Centro de Custo` sem um modelo mestre explícito, aparecendo mais como agregacao/reporting do que como entidade oficial;
- mistura de conceito entre `Safra`, `Cultivo`, `Commodity` e `Romaneio` em alguns fluxos;
- `Fornecedor` proprio em Compras coexistindo com `Pessoa`, o que cria sobreposicao conceitual;
- `Comercializacao` e `Hedge` reutilizando `Commodity`, mas com campos textuais paralelos para o mesmo conceito.

Conclusao curta:

- **Sim, ha uma base funcional suficiente para o Wizard.**
- **Nao, a base ainda nao e plenamente consistente para ser considerada definitiva sem revisao de alguns pontos estruturais, principalmente Cultura e alguns cadastros de apoio.**

---

## Base da auditoria

Fontes principais consultadas:

- [/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/router.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/service.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/commodities/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/commodities/models.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/commodities/router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/commodities/router.py)
- [/opt/lampp/htdocs/farm/services/api/core/measurements/models.py](/opt/lampp/htdocs/farm/services/api/core/measurements/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/cadastros/models.py](/opt/lampp/htdocs/farm/services/api/agricola/cadastros/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/cadastros/router.py](/opt/lampp/htdocs/farm/services/api/agricola/cadastros/router.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/safras/models.py](/opt/lampp/htdocs/farm/services/api/agricola/safras/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/safras/service.py](/opt/lampp/htdocs/farm/services/api/agricola/safras/service.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/cultivos/models.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/colheita/models.py](/opt/lampp/htdocs/farm/services/api/agricola/colheita/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/romaneios/models.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/models.py)
- [/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/router.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/router.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/hedge/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/hedge/models.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/hedge/router.py](/opt/lampp/htdocs/farm/services/api/financeiro/hedge/router.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/hedge/schemas.py](/opt/lampp/htdocs/farm/services/api/financeiro/hedge/schemas.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py](/opt/lampp/htdocs/farm/services/api/operacional/models/estoque.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/models/compras.py](/opt/lampp/htdocs/farm/services/api/operacional/models/compras.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/routers/compras.py](/opt/lampp/htdocs/farm/services/api/operacional/routers/compras.py)
- [/opt/lampp/htdocs/farm/services/api/operacional/routers/estoque_implantacao.py](/opt/lampp/htdocs/farm/services/api/operacional/routers/estoque_implantacao.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/models.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/pessoas/router.py)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/animal/models.py](/opt/lampp/htdocs/farm/services/api/pecuaria/animal/models.py)
- [/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/animal_schema.py](/opt/lampp/htdocs/farm/services/api/pecuaria/schemas/animal_schema.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/models/plano_conta.py](/opt/lampp/htdocs/farm/services/api/financeiro/models/plano_conta.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/schemas/plano_conta_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/plano_conta_schema.py)
- [/opt/lampp/htdocs/farm/services/api/financeiro/schemas/relatorio_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/relatorio_schema.py)
- [/opt/lampp/htdocs/farm/services/api/core/models/crm_ofertas.py](/opt/lampp/htdocs/farm/services/api/core/models/crm_ofertas.py)
- [/opt/lampp/htdocs/farm/services/api/core/routers/backoffice_tabelas.py](/opt/lampp/htdocs/farm/services/api/core/routers/backoffice_tabelas.py)
- [/opt/lampp/htdocs/farm/services/api/core/cadastros/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/models.py)

---

## Inventário dos Cadastros Mestres

### Agricultura

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Cultura | `ProdutoCultura` em `core/cadastros/produtos/models.py` | `core.cadastros.produtos` + backoffice | Cadastro unificado atual |
| Cultura legada | `Cultura` em `agricola/cadastros/models.py` | `agricola.cadastros` | Legado ainda exposto por rota própria |
| Safra | `Safra` | `agricola.safras` | Contexto macro da produção |
| Cultivo | `Cultivo` + `CultivoArea` | `agricola.cultivos` | Unidade operacional real |
| Production Unit | Existem referências no módulo agrícola | `agricola.production_units` | Unidade operacional auxiliar de execução/custo |
| Talhão / Área | `AreaRural` | `core.cadastros.propriedades` | Estrutura territorial oficial |

### Estoque

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Produto | `Produto` em `core/cadastros/produtos/models.py` | `core.cadastros.produtos` | Cadastro unificado de entrada/insumo |
| Categoria de produto | `CategoriaProduto` | `core.cadastros.produtos` | Estrutura hierárquica |
| Marca | `Marca` | `core.cadastros.produtos` | Sistema + tenant |
| Modelo de produto | `ModeloProduto` | `core.cadastros.produtos` | Sistema + tenant |
| Unidade de medida | `UnidadeMedida` | `core.measurements` | Cadastro separado e oficial |
| Depósito | `Deposito` | `operacional.estoque` | Operacional, não master puro |
| Lote | `LoteEstoque` | `operacional.estoque` | Operacional |

### Comercialização

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Commodity | `Commodity` | `core.cadastros.commodities` | Cadastro oficial de mercado |
| Classificação de commodity | `CommodityClassificacao` | `core.cadastros.commodities` | Qualidade / padrão |
| Cotação de commodity | `CotacaoCommodity` | `core.cadastros.commodities` | Mercado / pricing |
| Conversão de unidade da commodity | `ConversaoUnidade` | `core.cadastros.commodities` + `core.measurements` | Complementar |
| Produto colhido | `ProdutoColhido` | `agricola.colheita` | Ponte entre produção e comercialização |
| Comercialização | `ComercializacaoCommodity` | `financeiro.comercializacao` | Contrato de venda |

### Hedge

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Contrato futuro | `ContratoFuturo` | `financeiro.hedge` | Instrumento de hedge |
| Operação de hedge | `HedgeRegistro` | `financeiro.hedge` | Evento materializado |
| Snapshot MTM | `HedgePositionSnapshot` | `financeiro.hedge` | Projeção calculada / materializada |

### Pecuária

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Espécie | enum `EspecieAnimal` | `pecuaria.animal` | Não é tabela mestre separada |
| Raça | não há tabela mestre oficial única no trecho auditado | `pecuaria` / `enterprise` | Há sinais de modelos legados/variações |
| Lote pecuário | `LoteAnimal` | `pecuaria.animal` | Estrutura operacional |
| Animal | `Animal` | `pecuaria.animal` | Ativo biológico |
| Evento animal | `EventoAnimal` | `pecuaria.animal` | Linha do tempo |

### Financeiro

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Plano de contas | `PlanoConta` | `financeiro.plano_conta` | Mestre oficial financeiro |
| Centro de custo | não há modelo mestre dedicado encontrado | `financeiro.relatorio` / rateios | Aparece como agregação e rateio |
| Categoria financeira | não há entidade própria dedicada encontrada | derivada de `PlanoConta.categoria_rfb` | Não existe como master separado |

### Compras

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Fornecedor | `Fornecedor` em `operacional.compras` | `operacional.compras` | Cadastro próprio e também ligado a `Pessoa` |
| Pedido de compra | `PedidoCompra` | `operacional.compras` | Operacional |
| Cotação de compra | `CotacaoCompra` / `CotacaoFornecedor` | `operacional.compras` | Operacional |

### Pessoas

| Cadastro | Modelo oficial | Owner funcional | Observação |
|---|---|---|---|
| Pessoa | `Pessoa` | `core.cadastros.pessoas` | Entidade base compartilhada |
| Documento / contato / endereço / bancário | tabelas associadas | `core.cadastros.pessoas` | Estrutura de apoio |
| Tipos de relacionamento | `TipoRelacionamento` | `core.cadastros.pessoas` | Papéis reutilizáveis |

---

## Proprietário de cada cadastro

### Cadastro único e oficial

- Produtos: `core.cadastros.produtos`
- Commodities: `core.cadastros.commodities`
- Culturas unificadas: `core.cadastros.produtos` via `ProdutoCultura`
- Unidade de medida: `core.measurements`
- Plano de contas: `financeiro.plano_conta`
- Pessoas: `core.cadastros.pessoas`

### Cadastro compartilhado entre módulos

- Produto:
  - Estoque
  - Compras
  - Pecuária
  - Operações
  - Partes do agrícola
- Commodity:
  - Agricultura
  - Comercialização
  - Hedge
  - Romaneio / Colheita
- Pessoa:
  - Compras
  - Comercialização
  - Financeiro
  - Pecuária
  - CRM

### Cadastro com dono difuso ou não explicitado

- Centro de custo
- Categoria financeira como entidade própria
- Raça como entidade mestre oficial única
- Fornecedor como conceito independente de Pessoa

---

## Produto

### Existe apenas um cadastro oficial?

**Sim, com ressalva de legado.**

O cadastro oficial atual é `Produto` em `core/cadastros/produtos/models.py`.

O arquivo `core/cadastros/models.py` apenas reexporta esse modelo como `ProdutoCatalogo` para compatibilidade:

- `ProdutoCatalogo = Produto`
- `ProdutoAgricolaDetalhe = ProdutoAgricola`
- `ProdutoEstoqueDetalhe = ProdutoEstoque`

### Existem produtos duplicados em módulos diferentes?

**Nao como entidade mestre diferente.**

O que existe é:

- o mesmo `Produto` sendo consumido em vários módulos;
- serviços legados ainda importando `ProdutoCatalogo`;
- extensões do produto por domínio:
  - `ProdutoAgricola`
  - `ProdutoEstoque`
  - `ProdutoEPI`

### Há especializações ou cópias?

Há especializações, não cópias:

- agrícola: sementes, defensivos, fertilizantes, inoculantes
- estoque: validade, peso, NCM, controle de lote
- EPI: CA, proteção, vida útil

Isso é coerente com o domínio.

---

## Commodities

### Existe apenas um cadastro?

**Sim.**

O cadastro oficial é `Commodity` em `core/cadastros/commodities/models.py`.

Ele é usado por:

- agricultura
- romaneio
- produto colhido
- comercialização
- hedge
- conversões e cotações

### Quem é o dono da Commodity?

O dono funcional é `core.cadastros.commodities`.

Backoffice também administra tabelas sistêmicas, mas a entidade oficial é a mesma.

### Agricultura, Comercialização ou Hedge?

Os três compartilham a mesma entidade:

- Agricultura: `Cultivo.commodity_id`
- Colheita: `ProdutoColhido.commodity_id`
- Comercialização: `ComercializacaoCommodity.commodity_id`
- Hedge: `ContratoFuturo.commodity_id` e `HedgeRegistro`

### Existe duplicidade?

**Nao de tabela, mas existe duplicidade de representação textual.**

Exemplos:

- `ContratoFuturo.commodity` é texto
- `Safra.cultura` é texto
- `Cultivo.cultura` é texto

Ao mesmo tempo existem FKs para `Commodity` e `ProdutoCultura`.

Isso gera sobreposição conceitual.

---

## Culturas

### A Cultura gera Commodity?

**Nao como regra oficial.**

### Commodity gera Cultura?

**Nao como regra oficial.**

### Sao entidades independentes?

**Na modelagem atual, sim, mas com acoplamentos parciais.**

Evidências:

- `ProdutoCultura` é um catálogo de culturas agrícolas.
- `Commodity` é um catálogo de mercado.
- `Cultivo` possui:
  - `cultura` como texto
  - `cultivar_id` apontando para `cadastros_culturas`
  - `commodity_id` apontando para `cadastros_commodities`
- `Safra` guarda `cultura` como texto legado.

Conclusão:

- cultura e commodity **são independentes na origem**;
- o sistema liga as duas por `Cultivo`;
- a safra ainda conserva um campo textual legado para cultura.

### Inconsistência estrutural

Existe uma duplicidade real de catálogo de cultura:

1. `agricola/cadastros/models.py` com tabela `culturas`
2. `core/cadastros/produtos/models.py` com tabela `cadastros_culturas`

O código mostra que o caminho novo/unificado é `cadastros_culturas`, mas o legado ainda é exposto por rota própria em `agricola/cadastros/router.py`.

Esse é o ponto estrutural mais relevante antes de um Wizard.

---

## Safra

### Safra depende de Cultura?

**Nao diretamente.**

`SafraCreate` exige:

- `ano_safra`
- `cultivos` ou `talhao_ids`

O campo `cultura` existe, mas é legado.

### Safra depende de Cultivo?

**Sim, no fluxo novo.**

`SafraService.criar()` cria a safra com:

- `Cultivo`
- `CultivoArea`

### Safra depende de Commodity?

**Nao obrigatoriamente.**

Commodity é opcional por cultivo/safra, embora seja amplamente usada nos fluxos de colheita, comercialização e hedge.

### Safra depende de Área?

**Sim, obrigatoriamente no fluxo real.**

O código valida talhão/área:

- safra precisa de pelo menos um `talhao_id` ou área no cultivo
- duplicidade é validada por `CultivoArea.area_id`

### Existe outro fluxo oficial?

Sim, o fluxo novo é:

`Safra` -> `Cultivo` -> `CultivoArea`

O fluxo legado ainda existe:

`Safra` -> `SafraTalhao` + `cultura` textual

---

## Produto x Commodity x Cultura x Safra

### Grafo real encontrado

`Produto`

↓

`ProdutoAgricola` / `ProdutoEstoque` / `ProdutoEPI`

↓

`ProdutoCultura` ou `Cultura` legada

↓

`Safra`

↓

`Cultivo`

↓

`CultivoArea`

↓

`AreaRural`

↓

`RomaneioColheita`

↓

`ProdutoColhido`

↓

`ComercializacaoCommodity`

↓

`Receita` / `PlanoConta`

### Caminhos alternativos

Sim:

- `Safra` pode nascer pelo legado `talhao_ids`
- `Romaneio` pode derivar `commodity_id` da safra
- `Hedge` pode resolver commodity a partir da safra
- `Comercializacao` pode vincular `ProdutoColhido` ou apenas `Commodity`

Isso mostra que o grafo é funcional, mas não linear o suficiente para um Wizard totalmente determinístico sem regras de priorização.

---

## Produtos Agrícolas

### Semente, fertilizante, defensivo, grão, palha, silagem

O sistema trata essas categorias em camadas diferentes:

- `Produto.tipo` cobre:
  - `SEMENTE`
  - `DEFENSIVO`
  - `FERTILIZANTE`
  - `INOCULANTE`
  - `ADJUVANTE`
  - `RACAO`
  - `MEDICAMENTO`
  - `VACINA`
  - `MINERAL`
  - `PECA`
  - `LUBRIFICANTE`
  - `COMBUSTIVEL`
  - `MATERIAL_GERAL`
  - `EPI`
  - `SERVICO`
- `ProdutoAgricola` especializa o produto para uso agrícola.
- `Commodity` representa o produto negociado no mercado.
- `ProdutoColhido` representa o resultado físico da colheita.

### São tratados pelo mesmo cadastro?

**Não todos.**

- Insumos e materiais de entrada: `Produto`
- Mercado / negociação: `Commodity`
- Resultado colhido: `ProdutoColhido`

### Ou existem modelos diferentes?

Sim. O desenho é intencionalmente separado.

O ponto de atrito é que o usuário pode ver "produto" em mais de uma tela com semânticas diferentes.

---

## Produtos Pecuários

### Vacinas, medicamentos, rações, minerais

Compartilham o mesmo cadastro mestre de `Produto`.

Evidência:

- `TipoProduto` inclui `RACAO`, `MEDICAMENTO`, `VACINA`, `MINERAL`
- `ProdutoAgricola` não cobre pecuária
- `ProdutoEstoque` é compartilhado pelo almoxarifado

### Animais

**Não** compartilham o cadastro de produto.

Eles são `Animal` e `LoteAnimal`, com enums próprios:

- `EspecieAnimal`
- `SexoAnimal`
- `CategoriaAnimal`
- `StatusAnimal`

### Leite e carne

Não aparecem como cadastro mestre próprio no trecho auditado.

O que existe é o domínio zootécnico e os eventos/resultado operacional, não um catálogo de "produtos pecuários" formal separado.

### Compartilham infraestrutura?

Sim, em parte:

- `Produto` para insumos
- `LoteAnimal` / `Animal` para o rebanho
- `EventoAnimal` para registro

---

## Compras

### Compras reutilizam Produto?

**Sim.**

`PedidoCompra.item_id`, `ItemPedidoCompra.produto_id`, `ItemRecebimento.lote_id` e `SolicitacaoCompra.produto_id` usam o catálogo de produto.

### Possuem cadastro próprio?

**Sim, para fornecedores e documentos de compra.**

Mas não para o produto comprado.

### Fornecedor é duplicado?

Há duas camadas:

- `Pessoa` é o cadastro base de entidades;
- `Fornecedor` em compras é um cadastro operacional próprio.

Isso é uma redundância funcional.

No código, `Fornecedor` já possui `pessoa_id`, então o sistema assume sobreposição entre os dois.

---

## Estoque

### Todo item movimentado pertence ao cadastro oficial de Produtos?

**Sim, no fluxo atual.**

Evidência:

- `EstoqueMovimento.produto_id` aponta para `cadastros_produtos.id`
- `LoteEstoque.produto_id` aponta para `cadastros_produtos.id`
- `SaldoEstoque.produto_id` aponta para `cadastros_produtos.id`
- `Deposito` não é produto; é infraestrutura de estoque

### Existem exceções?

O sistema possui integração com:

- `ProdutoColhido`
- `ProdutoCatalogo` como alias legado
- importação assistida

Mas não existe outro cadastro mestre concorrente de produto físico.

---

## Comercialização

### A venda utiliza Produto?

**Não como cadastro principal.**

### A venda utiliza Commodity?

**Sim.**

`ComercializacaoCommodity.commodity_id` é obrigatório.

### A venda utiliza Produto Colhido?

**Sim, opcionalmente e de forma importante para rastreabilidade.**

`produto_colhido_id` existe para vincular o lote colhido.

### Mistura conceitos?

**Sim.**

O contrato de venda tem:

- `commodity_id` obrigatório
- `produto_colhido_id` opcional
- `comprador_id` obrigatório

Isso é funcional, mas mistura:

- objeto de mercado
- lote físico
- parceiro comercial

No front e no negócio isso pode confundir o usuário.

---

## Hedge

### Commodity do Hedge é a mesma do restante do sistema?

**Sim.**

O hedge referencia `cadastros_commodities.id`.

### Existe duplicidade?

**Não de tabela, mas existe duplicidade de representação.**

O hedge também usa:

- `commodity` como texto livre
- `safra_id`
- `commodity_id`

Então o mesmo conceito aparece em forma estruturada e textual.

### Conclusão

O hedge está integrado ao catálogo oficial de commodities, mas ainda preserva fallback textual para compatibilidade e flexibilidade.

---

## Dependências entre cadastros

### Grafo oficial resumido

`Tenant`

↓

`Pessoa`

↓

`Fornecedor` / `Cliente` / `Parceiro`

↓

`Produto`

↓

`CategoriaProduto` + `Marca` + `ModeloProduto`

↓

`UnidadeMedida`

↓

`Estoque` / `Compras`

↘

`ProdutoCultura`

↓

`Cultivo`

↓

`Safra`

↓

`RomaneioColheita`

↓

`ProdutoColhido`

↓

`ComercializacaoCommodity`

↓

`Receita`

↓

`PlanoConta`

↓

`DRE` / relatórios

Paralelos:

`Commodity`

↓

`Cultivo`

↓

`RomaneioColheita`

↓

`ProdutoColhido`

↓

`ComercializacaoCommodity`

↓

`Hedge`

### Dependências ocultas

- `Safra` precisa de área/talhão, mesmo quando isso não aparece como FK explícita na raiz.
- `Romaneio` deriva parâmetros de qualidade da `Commodity`, ou usa fallback por cultura.
- `Romaneio` cria `ProdutoColhido` automaticamente.
- `Romaneio` tenta criar `Receita` com `PlanoConta` de receita da atividade rural.
- `Hedge` tenta resolver commodity a partir da safra.
- `Comercializacao` pode ligar commodity e produto colhido ao mesmo tempo.
- `Compras` e `Estoque` ainda usam camadas legadas por compatibilidade.

---

## Ordem ideal de cadastros mestres

Com base na codebase, a sequência mais coerente é:

1. Tenant
2. Pessoas
3. Unidades de Medida
4. Categorias de Produto
5. Marcas
6. Modelos de Produto
7. Produtos
8. Culturas unificadas (`ProdutoCultura`)
9. Commodities
10. Plano de Contas
11. Centros de Custo operacionais / rateios, se usados
12. Propriedade / Imóvel / Áreas, se o fluxo patrimonial for necessário
13. Depósitos
14. Estoque inicial / lotes
15. Safras
16. Cultivos
17. Produto colhido
18. Comercialização
19. Hedge
20. Pecuária

### Observação importante

A ordem acima é a sequência mais coerente para o modelo atual, mas não é perfeitamente linear porque:

- cultura e commodity podem ser cadastradas antes ou depois da safra;
- produto pode nascer sem marca/modelo;
- plano de contas pode ser seedado e depois ajustado.

---

## Redundâncias encontradas

### 1. Cultura duplicada

Existe um catálogo legado `culturas` e um catálogo unificado `cadastros_culturas`.

Esse é o principal ponto de redundância estrutural.

### 2. Produto com alias legado

`ProdutoCatalogo` em `core/cadastros/models.py` é apenas reexportação de `Produto`.

Não é duplicidade de tabela, mas é um duplo caminho de importação e leitura.

### 3. Fornecedor vs Pessoa

`Fornecedor` em compras já contém `pessoa_id`.

Isso sugere dois cadastros para a mesma entidade, dependendo do contexto.

### 4. Commodity com texto livre paralelo

Em hedge, safra e comercialização, `commodity` aparece como texto e como FK.

### 5. Centro de custo sem mestre explícito

O sistema trabalha com rateios e agregações, mas não com uma entidade mestre claramente modelada.

### 6. Categoria financeira não isolada

No financeiro, a classificação parece estar embutida no `PlanoConta.categoria_rfb`.

---

## Conflitos de nomenclatura

### "Cultura"

Conflito entre:

- `agricola.cadastros.Cultura`
- `core.cadastros.produtos.ProdutoCultura`

### "Produto"

Conflito semântico entre:

- produto de entrada/insumo
- produto colhido
- produto de oferta no CRM

### "Commodity"

Conflito semântico entre:

- commodity de mercado
- referência textual de safra/cultura em alguns fluxos

### "Fornecedor"

Conflito entre:

- entidade de compras
- pessoa jurídica base

### "Centro de custo"

Conflito entre:

- entidade contábil clássica
- agregação de custo por safra/talhão/plano de conta

---

## Impactos no Wizard

### Cadastros que devem ser obrigatórios

- Tenant
- Pessoa responsável / usuário
- Unidade de Medida
- Produto mínimo
- Cultura unificada
- Commodity, se a operação envolver colheita/comercialização/hedge
- Plano de Contas, se o financeiro for ativado
- Depósito, se estoque for ativado

### Cadastros que podem ser adiados

- Marcas e modelos
- Classes de commodity
- Cotações
- Parametrizações de solo
- Fornecedores e clientes completos
- Hedge
- Comercialização
- Produto colhido
- Lotes pecuários
- Detalhamento de centro de custo

### Cadastros que podem ser criados automaticamente

- Estrutura base da unidade produtiva
- Categorias padrão de produto
- Categorias padrão de cultura, quando aceitáveis
- Plano de contas seedado
- Marca/modelo default, se houver catálogo do sistema

### Cadastros que podem ser importados

- Produtos
- Culturas
- Commodities
- Fornecedores
- Clientes
- Lotes de estoque
- Estrutura territorial

---

## UX

### Cadastros repetitivos

- Cultura em dois caminhos diferentes
- Produto com múltiplas camadas de compatibilidade
- Fornecedor espelhado em Pessoa
- Commodity texto + FK

### Passos desnecessários

- Criar marca e modelo antes do primeiro produto, quando o catálogo ainda não existe
- Criar fornecedor separado quando `Pessoa` já cobre a entidade
- Criar centro de custo manual quando o sistema já agrega por safra/talhão

### Telas redundantes

- Tela de cultura antiga e tela de cultura unificada
- Telas de cadastro de produto com foco distinto mas mesma base
- Telas de comercialização/hedge com campos de commodity e texto livre duplicados

### Oportunidades de simplificação

- Unificar a cultura no fluxo unificado e aposentar o legado
- Reduzir o uso de texto livre quando houver FK disponível
- Reaproveitar `Pessoa` como entidade base de fornecedor/cliente em vez de manter duas leituras para o mesmo agente
- Expor a árvore de produto com extensões, em vez de separar mentalmente por módulo

---

## Dependências ocultas

1. `core/cadastros/models.py` não é um segundo catálogo de produto; é um alias de compatibilidade.
2. O produto unificado exige várias visões complementares no frontend, o que pode dar sensação de duplicidade.
3. A cultura antiga ainda é um caminho navegável.
4. O financeiro usa `categoria_rfb` do plano de contas como eixo de classificação, e não uma tabela de categoria separada.
5. Hedge e comercialização dependem da commodity oficial, mas não eliminam os textos livres.
6. O romaneio pode materializar `ProdutoColhido` e receita automaticamente.

---

## Recomendações de simplificação

Sem implementar nada, a codebase mostra que os ajustes mais importantes para consolidar o modelo seriam:

1. Encerrar a duplicidade de cultura e concentrar o domínio em um único catálogo.
2. Reduzir os caminhos legados de compatibilidade em `Produto` e `Cultura`.
3. Formalizar o papel de `Fornecedor` em relação a `Pessoa`.
4. Decidir se `Centro de Custo` será entidade mestre ou apenas agregação analítica.
5. Padronizar `Commodity` como FK única nos fluxos de colheita, comercialização e hedge.
6. Explicitar a diferença entre produto de entrada, commodity, produto colhido e oferta CRM na UX.

---

## Critérios de aceite

### Existe um único cadastro oficial de Produtos?

**Sim, com alias legado.**

### Existe um único cadastro oficial de Commodities?

**Sim.**

### Existe um único cadastro oficial de Culturas?

**Nao.**

Este é o principal ponto de inconsistência.

### Hedge, Comercialização, Agricultura e Estoque compartilham os mesmos cadastros?

**Parcialmente.**

- Produto: sim
- Commodity: sim
- Cultura: não plenamente
- Pessoa: sim
- Unidade de Medida: sim

### Há duplicação de conceitos?

**Sim.**

Principalmente em:

- cultura
- fornecedor
- produto em camadas distintas
- commodity com texto paralelo

### A ordem atual de implantação é coerente?

**Sim, mas com fricções.**

### Há cadastros que podem ser criados automaticamente pelo Wizard?

**Sim.**

Principalmente:

- estruturas raiz
- categorias padrão
- plano de contas seedado
- marca/modelo base

### Existe alguma inconsistência estrutural que deva ser corrigida antes da implantação do Assistente de Implantação?

**Sim.**

A inconsistência mais importante é a duplicidade de cultura e a coexistência de fluxos legados e unificados para o mesmo domínio.

---

## Conclusão final

O AgroSaaS já tem uma base funcional forte e, em boa parte, unificada para produto, commodity e unidade de medida.

Mas o modelo **ainda não é suficientemente consistente para ser considerado definitivo sem revisão**, porque:

- existe duplicidade real de cultura;
- existem camadas legadas convivendo com as novas;
- alguns conceitos operacionais continuam sem mestre explícito;
- alguns módulos misturam FK com texto livre para a mesma entidade.

Portanto:

**A base é boa o suficiente para começar um Wizard, mas não está limpa o bastante para ser considerada a versão final do master data.**
