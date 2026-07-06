# SANKHYA-SYNC-02 - Auditoria do Mapeamento Canonico Sankhya x AgroSaaS

## Escopo auditado

Auditoria apenas documental da base de codigo para identificar o mapeamento canonico entre Sankhya e AgroSaaS, sem criar sync, endpoints, tabelas, migrations ou alterar contratos existentes.

### Areas auditadas

- Integracao Sankhya: configuracao, autenticacao Gateway e adapter canonico
- Estrutura organizacional
- Pessoas
- Produtos
- Financeiro
- Fiscal
- Estoque
- Comercializacao
- Chaves externas e idempotencia
- Conversoes de unidade e classificacoes fiscais

## Base encontrada

### Integracao Sankhya ja existente

- Router Sankhya com configuracao, teste de conexao, status, health, syncs por dominio e diagnostico. Referencia: `services/api/integracoes/sankhya/routers/__init__.py`
- Auth Gateway com `/authenticate`, validacao de config, mascaramento e diagnostic snapshot. Referencia: `services/api/integracoes/sankhya/services/auth_service.py`
- Adapter canonico com provider, credenciais, health, jobs, features e eventos. Referencia: `services/api/integracoes/sankhya/services/canonical_adapter.py`
- Modelos persistidos de configuracao, pessoas, produtos, NFe, financeiro e tabelas auxiliares. Referencia: `services/api/integracoes/sankhya/models/__init__.py`
- Servicos de pessoa, produto, NFe e financeiro ja operam upsert por `sankhya_id` ou `chave_acesso`. Referencia: `services/api/integracoes/sankhya/services/sync_service.py` e `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`

### Contexto canonico AgroSaaS ja existente

- `UnidadeProdutiva` como raiz operacional do tenant. Referencia: `services/api/core/models/unidade_produtiva.py`
- `Pessoa`, `PessoaDocumento`, `PessoaContato`, `PessoaEndereco`, `TipoRelacionamento`, `PessoaRelacionamento`. Referencia: `services/api/core/cadastros/pessoas/models.py`
- `Produto`, `ProdutoAgricola`, `ProdutoEstoque`, `UnidadeMedida` e `UnidadeMedidaConversao`. Referencias: `services/api/core/cadastros/produtos/models.py`, `services/api/core/measurements/models.py`, `services/api/core/routers/backoffice_uom.py`
- `Deposito`, `SaldoEstoque`, `LoteEstoque`, `EstoqueMovimento`. Referencia: `services/api/operacional/models/estoque.py`
- `PlanoConta`, `Despesa`, `Receita`, `NotaFiscal`. Referencias: `services/api/financeiro/models/plano_conta.py`, `services/api/financeiro/models/despesa.py`, `services/api/financeiro/models/receita.py`, `services/api/financeiro/models/nota_fiscal.py`
- `ComercializacaoCommodity` e `Commodity`/`CommodityClassificacao`/`CotacaoCommodity`. Referencias: `services/api/financeiro/comercializacao/models.py`, `services/api/core/cadastros/commodities/models.py`
- `ContratoFuturo` existe no modulo de hedge, mas nao e a entidade de comercializacao do piloto. Referencia: `services/api/enterprise/models/sprints_27_33.py`

## Classificacao por dominio

### Estrutura organizacional

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Empresa | Nenhuma entidade canonica dedicada | NAO EXISTE | `services/api/core/models/unidade_produtiva.py`, `services/api/core/models/auth.py` | Tenant e UnidadeProdutiva estruturam contexto, mas nao empresa/filial | Definir modelo canônico se o piloto exigir consolidacao societaria |
| Filial | Nenhuma entidade canonica dedicada | NAO EXISTE | `services/api/core/models/unidade_produtiva.py` | Contexto operacional por fazenda/UP, nao por filial | Mapear somente se houver multicarteira societaria no piloto |
| Unidade de Negocio | Nenhuma entidade canonica dedicada | NAO EXISTE | `services/api/core/models/unidade_produtiva.py`, `services/api/core/operational_context.py` | Contexto operacional depende de UnidadeProdutiva, area e safra | Criar apenas se a operacao precisar de centro empresarial formal |
| Deposito | `Deposito` | EXISTE E ATENDE | `services/api/operacional/models/estoque.py`, `services/api/core/operational_context.py` | Deposito vincula tenant, UnidadeProdutiva e tipo; saldo/lote/movimento ja usam deposito | Ajuste leve de mapeamento de `CODLOCAL`/localizacao |
| Local de Estoque | `Deposito.localizacao_desc` e `ProdutoEstoque.localizacao_default` | EXISTE PARCIALMENTE | `services/api/operacional/models/estoque.py`, `services/api/core/cadastros/produtos/models.py` | Existe como atributo de apoio, nao como master separado | Se Sankhya usar local granular, pode exigir extensao de cadastro |

### Pessoas

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Cliente | `Pessoa` + `PessoaRelacionamento` + `Receita.pessoa_id` | EXISTE PARCIALMENTE | `services/api/core/cadastros/pessoas/models.py`, `services/api/financeiro/models/receita.py` | Pessoa central, documentos e relacionamentos por papel; contas a receber suportam `pessoa_id` | Consolidar regra de upsert por documento e papel |
| Fornecedor | `Pessoa` + `PessoaRelacionamento` + `Despesa.pessoa_id` + `Fornecedor` legado | EXISTE PARCIALMENTE | `services/api/core/cadastros/pessoas/models.py`, `services/api/financeiro/models/despesa.py`, `services/api/operacional/models/compras.py` | Despesa aceita `pessoa_id`; Fornecedor ainda existe como wrapper legado | Consolidar fornecedor no dominio de Pessoa e evitar duplicidade com `Fornecedor` |
| Transportadora | `Pessoa` + `TipoRelacionamento` | EXISTE PARCIALMENTE | `services/api/core/cadastros/pessoas/models.py` | TipoRelacionamento inclui papes configuraveis como `PRESTADOR`, `PARCEIRO`, `OUTRO` | Definir papel padrao de transportadora e regras de endereco/frete |
| Representante | `Pessoa` + `TipoRelacionamento` | EXISTE PARCIALMENTE | `services/api/core/cadastros/pessoas/models.py` | Papel configuravel por tenant | Pode ser reaproveitado sem novo master |
| Parceiro | `Pessoa` + `TipoRelacionamento` | EXISTE PARCIALMENTE | `services/api/core/cadastros/pessoas/models.py` | Papel configuravel por tenant | Precisa apenas de normalizacao do codigo de relacionamento |

### Produtos

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Produto | `Produto` | EXISTE E ATENDE | `services/api/core/cadastros/produtos/models.py` | Cadastro unificado, `codigo_interno` unico por tenant, tipos de produto, marca, modelo, categoria | Reaproveitar com mapeamento de `CODPROD` e campos fiscais |
| Insumo | `Produto` + `ProdutoAgricola` | EXISTE E ATENDE | `services/api/core/cadastros/produtos/models.py` | Tipos agricola/operacional ja suportam defensivos, sementes e fertilizantes | Normalizacao de classificacao vinda do ERP |
| Servico | `Produto` tipo `SERVICO` | EXISTE E ATENDE | `services/api/core/cadastros/produtos/models.py` | Tipo de produto ja contempla servicos | Pode exigir mapeamento de UOM e natureza fiscal do item |
| Combustivel | `Produto` tipo `COMBUSTIVEL` + `Deposito` tipo `COMBUSTIVEL` | EXISTE E ATENDE | `services/api/core/cadastros/produtos/models.py`, `services/api/operacional/models/estoque.py` | Produto e deposito ja cobrem o caso operacional | Ajuste apenas na estrategia de local/estoque |
| Peca | `Produto` tipo `PECA` | EXISTE E ATENDE | `services/api/core/cadastros/produtos/models.py` | Estoque e movimentacao suportados | Nenhuma estrutura nova necessaria |
| Unidade de Medida | `UnidadeMedida` | EXISTE E ATENDE | `services/api/core/measurements/models.py`, `services/api/core/routers/backoffice_uom.py` | UoM global canonica, escopo por dimensao e controle de unidade canonica | Reaproveitar para mapeamento de unidade Sankhya |
| Conversao de Unidade | `UnidadeMedidaConversao` | EXISTE E ATENDE | `services/api/core/measurements/models.py`, `services/api/core/routers/backoffice_uom.py` | Conversao unica por par origem/destino/cultura, com regra generica e especifica | Reaproveitar para equivalencias do piloto de cafe |
| NCM | `ProdutoEstoque.ncm`, `SankhyaProduto.ncm`, `NotaFiscal.ncm` | EXISTE PARCIALMENTE | `services/api/core/cadastros/produtos/models.py`, `services/api/integracoes/sankhya/models/__init__.py`, `services/api/financeiro/models/nota_fiscal.py` | O campo existe em varios pontos, mas nao ha master fiscal canonico unico | Consolidar tabela de referencia se a operacao exigir manutencao local |
| Classificacoes fiscais | `SankhyaTabela`, campos fiscais em produto/NF | EXISTE PARCIALMENTE | `services/api/integracoes/sankhya/models/__init__.py`, `services/api/financeiro/services/nfe_xml_generator.py` | CFOP/NCM/serie aparecem em modelos e geradores, mas sem master canonico unificado | Mapear apenas como referencia, sem criar estrutura nova agora |

### Financeiro

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Plano de Contas | `PlanoConta` | EXISTE E ATENDE | `services/api/financeiro/models/plano_conta.py` | Hierarquia, tipo receita/despesa, natureza sintetica/analitica, categoria RFB | Reaproveitamento direto com mapeamento de conta externa |
| Centro de Custo | `Rateio` e vinculos por origem | EXISTE PARCIALMENTE | `services/api/financeiro/models/rateio.py`, `services/api/financeiro/models/despesa.py`, `services/api/financeiro/models/receita.py` | Existe rateio por safra/talhao, mas nao master de centro de custo | Se Sankhya exigir centro de custo proprio, sera preciso complementar o modelo |
| Natureza Financeira | Nenhuma entidade canonica dedicada | NAO EXISTE | `services/api/financeiro/models/plano_conta.py` | PlanoConta cobre a classificacao financeira, mas nao um master separado | Pode ser derivado de PlanoConta no piloto; sem nova estrutura agora |
| Contas a Pagar | `Despesa` | EXISTE E ATENDE | `services/api/financeiro/models/despesa.py` | Suporte a `pessoa_id`, parcela, origem, NF, serie e chave NFe | Reaproveitamento direto para exportacao/importacao financeira |
| Contas a Receber | `Receita` | EXISTE E ATENDE | `services/api/financeiro/models/receita.py` | Suporte a `pessoa_id`, parcela, origem, NF, serie e chave NFe | Reaproveitamento direto para exportacao/importacao financeira |
| Condicoes de Pagamento | `forma_pagamento`/`forma_recebimento` e texto livre em fornecedores | EXISTE PARCIALMENTE | `services/api/financeiro/models/despesa.py`, `services/api/financeiro/models/receita.py`, `services/api/operacional/models/compras.py` | Ha campos de forma de pagamento, prazo e condicoes textuais | Se Sankhya exigir tabela mestre, a extensao vira necessaria |

### Fiscal

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Notas Fiscais | `NotaFiscal` | EXISTE PARCIALMENTE | `services/api/financeiro/models/nota_fiscal.py`, `services/api/financeiro/services/nfe_transmissao.py` | Modelo contem chave, serie, status SEFAZ, protocolos e dados basicos | Bom para rastreio, mas nao cobre 100% da NF fiscal do ERP |
| Series | `NotaFiscal.serie`, `Despesa.serie_nf`, `Receita.serie_nf`, `SankhyaNFe.serie` | EXISTE PARCIALMENTE | `services/api/financeiro/models/nota_fiscal.py`, `services/api/financeiro/models/despesa.py`, `services/api/financeiro/models/receita.py`, `services/api/integracoes/sankhya/models/__init__.py` | Serie existe como atributo, nao como master de numeracao fiscal | Sem necessidade de nova tabela para o piloto |
| Chaves de Acesso | `NotaFiscal.chave_acesso`, `Despesa.chave_nfe`, `Receita.chave_nfe`, `SankhyaNFe.chave_acesso` | EXISTE E ATENDE | `services/api/financeiro/models/nota_fiscal.py`, `services/api/financeiro/models/despesa.py`, `services/api/financeiro/models/receita.py`, `services/api/integracoes/sankhya/models/__init__.py` | Chave de acesso ja e chave natural forte para deduplicacao | Reutilizar como idempotencia primaria para fiscal |
| Situacoes | `StatusSEFAZ`, `status_sankhya`, `SankhyaNFe.status_sankhya` | EXISTE PARCIALMENTE | `services/api/financeiro/models/nota_fiscal.py`, `services/api/integracoes/sankhya/models/__init__.py` | Estados fiscais e de integracao existem, mas o vocabulario nao e o mesmo do Sankhya | Necessita mapa de traducao de status, nao novo modelo |

### Estoque

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Depositos | `Deposito` | EXISTE E ATENDE | `services/api/operacional/models/estoque.py` | Deposito ja e por tenant e unidade produtiva | Reaproveitar com mapeamento de `CODLOCAL`/deposito |
| Saldo | `SaldoEstoque` | EXISTE E ATENDE | `services/api/operacional/models/estoque.py` | Saldo por produto/deposito, com quantidade atual e reservada | Reaproveitar para espelhar saldo operacional |
| Lotes | `LoteEstoque` | EXISTE E ATENDE | `services/api/operacional/models/estoque.py` | Rastreamento por lote, validade, nota e status | Reaproveitar para importacao de lotes de Sankhya |
| Movimentacoes | `EstoqueMovimento` | EXISTE E ATENDE | `services/api/operacional/models/estoque.py` | Ledger append-only com `origem` e `origem_id` | Reaproveitar como trilha de integridade |
| Inventario | Nenhuma entidade canonica dedicada | NAO EXISTE | `services/api/operacional/models/estoque.py` | Movimentacoes cobrem o saldo, mas nao um processo formal de inventario | Se o piloto demandar fechamento fisico, isso fica para fase posterior |

### Comercializacao

| Entidade Sankhya | AgroSaaS correspondente | Situacao | Arquivos envolvidos | Regras existentes | Adaptacao necessaria |
| --- | --- | --- | --- | --- | --- |
| Contratos | `ComercializacaoCommodity` | EXISTE PARCIALMENTE | `services/api/financeiro/comercializacao/models.py`, `services/api/financeiro/comercializacao/service.py` | Possui numero_contrato, comprador, commodity, frete, entrega, NF e receita vinculada | Serve para piloto, mas nao e um espelho 1:1 de contrato ERP |
| Compradores | `Pessoa` + `ComercializacaoCommodity.comprador_id` | EXISTE PARCIALMENTE | `services/api/financeiro/comercializacao/models.py`, `services/api/core/cadastros/pessoas/models.py` | Comprador e uma Pessoa com papel comercial | Reaproveitar sem novo master |
| Commodities | `Commodity` + `CommodityClassificacao` + `CotacaoCommodity` | EXISTE E ATENDE | `services/api/core/cadastros/commodities/models.py` | Cadastro proprio de mercado, unidade padrao, classificacoes e cotacoes | Reaproveitamento direto; sem duplicar com produto operacional |
| Pedidos | `PedidoCompra` existe, mas nao como pedido comercial de Sankhya | EXISTE PARCIALMENTE | `services/api/operacional/models/compras.py` | O que existe e pedido de compra, nao pedido de venda/comercializacao | Se Sankhya tiver ordem comercial, isso ainda precisa modelagem especifica |
| Documentos relacionados | `NotaFiscal`, `Receita`, `Despesa`, `ComercializacaoCommodity` | EXISTE PARCIALMENTE | `services/api/financeiro/models/nota_fiscal.py`, `services/api/financeiro/models/receita.py`, `services/api/financeiro/models/despesa.py`, `services/api/financeiro/comercializacao/models.py` | Documentos ja carregam numeros, series, chaves e origem | Reaproveitar e complementar apenas o que faltar de rastreabilidade |

## Source of Truth

| Entidade | Source of Truth |
| --- | --- |
| Cliente | Sankhya |
| Fornecedor | Sankhya |
| Transportadora | Sankhya |
| Representante | Sankhya |
| Parceiro | Sankhya |
| Produto | Sankhya |
| Insumo | Sankhya |
| Servico | Sankhya |
| Combustivel | Sankhya |
| Peca | Sankhya |
| Unidade de Medida | AgroSaaS |
| Conversao de Unidade | AgroSaaS |
| Plano de Contas | Sankhya |
| Centro de Custo | Pendencia de definicao |
| Natureza Financeira | Pendencia de definicao |
| Contas a Pagar | Sankhya |
| Contas a Receber | Sankhya |
| Condicoes de Pagamento | Sankhya |
| Notas Fiscais | Sankhya |
| Series | Sankhya |
| Chaves de Acesso | Sankhya |
| Situacoes fiscais | Sankhya |
| Depositos | Sankhya |
| Saldo de estoque | AgroSaaS |
| Lotes | AgroSaaS |
| Movimentacoes | AgroSaaS |
| Inventario | Pendencia de definicao |
| Empresa | Pendencia de definicao |
| Filial | Pendencia de definicao |
| Unidade de Negocio | Pendencia de definicao |
| Talhoes | AgroSaaS |
| Areas operacionais | AgroSaaS |
| Safras | AgroSaaS |
| Clima | AgroSaaS |
| Alertas | AgroSaaS |
| Recomendacoes | AgroSaaS |
| Commodities | AgroSaaS |
| Contratos de comercializacao | AgroSaaS |

Observacao: para os itens de cadastro comercial/fiscal, a leitura do codigo mostra que Sankhya ja possui integrações e IDs externos prontos para upsert. Para itens operacionais agronomicos, AgroSaaS permanece como fonte canonica.

## Chaves externas e idempotencia

### Chaves ja existentes

| Entidade | Chave | Uso atual |
| --- | --- | --- |
| SankhyaConfig | `tenant_id` | 1 config por tenant |
| SankhyaPessoa | `sankhya_id` | Upsert de pessoas |
| SankhyaProduto | `sankhya_id` | Upsert de produtos |
| SankhyaNFe | `sankhya_id`, `chave_acesso` | Upsert e deduplicacao fiscal |
| SankhyaLancamentoFinanceiro | `sankhya_id` | Upsert de lancamentos |
| Produto | `codigo_interno` | Chave interna unica por tenant |
| Pessoa | documentos e relacionamentos | Base para dedupe por CPF/CNPJ e papel |
| Despesa/Receita/LancamentoFinanceiro | `origem_id`, `grupo_parcela_id`, `numero_nf`, `serie_nf`, `chave_nfe` | Rastreabilidade e anti-duplicidade |
| EstoqueMovimento | `origem`, `origem_id` | Ledger append-only e idempotencia operacional |
| UnidadeMedidaConversao | origem, destino, cultura | Controle de unicidade do par de conversao |
| Commodity | `codigo` global e `tenant_id + nome` | Deduplicacao de catalogo de mercado |

### Chaves Sankhya observadas na integracao

- `CODPARC` para parceiros/pessoas
- `CODPROD` para produtos
- `CODEMP` nao foi modelado como entidade canonica dedicada
- `CODLOCAL` nao aparece como master proprio; o destino natural e `Deposito`
- `NUMDOC` para numero documental financeiro
- `DESDOB` para identificacao de desdobramento/lancamento
- `CHAVEACESSO` para documento fiscal

### Estrategia de idempotencia recomendada para o piloto

| Fluxo | Chave principal | Chave secundária | Atualizacao | Anti-duplicidade |
| --- | --- | --- | --- | --- |
| Pessoa | `CODPARC` | CPF/CNPJ + papel | Upsert por `sankhya_id` | Unicidade por ID externo e validação documental |
| Produto | `CODPROD` | codigo_interno/sku | Upsert por `sankhya_id` | Unicidade por cadastro externo |
| Nota fiscal | `CHAVEACESSO` | numero + serie + emitente | Upsert por chave de acesso | Chave de acesso como identidade fiscal natural |
| Lancamento financeiro | `DESDOB` | NUMDOC + CODPARC | Upsert por `sankhya_id` | Chave externa de lancamento + origem |
| Deposito | `CODLOCAL` | nome + unidade_produtiva | Upsert por codigo externo se existir | Evitar duplicacao por localizacao |
| Unidade de medida | codigo oficial | dimensao + fator | Preferir tabela canonica do AgroSaaS | Reusar mapeamento global existente |

## Conversoes e riscos de mapeamento

### Conversoes ja suportadas

- Unidades de medida e conversoes globais ja existem no AgroSaaS e suportam escopo generico e especifico por cultura.
- Produtos ja possuem unidade, unidade de conteudo, NCM e controle de estoque.
- Estoque ja diferencia deposito, lote, saldo e movimento.
- Financeiro ja separa despesa, receita e plano de contas.

### Pontos que exigem cuidado

- `CODLOCAL` pode representar deposito fisico ou local operacional; nao assumir equivalencia automatica com qualquer registro de estoque.
- `CODEMP` e `CODFILIAL` nao possuem master canonico equivalente no AgroSaaS atual.
- `Centro de Custo` em Sankhya nao deve ser confundido com `Rateio`; o primeiro e cadastro, o segundo e distribuicao.
- `Natureza Financeira` nao existe como master proprio; o melhor encaixe atual e `PlanoConta`, mas isso e apenas aproximacao.
- `ComercializacaoCommodity` cobre contrato de venda de commodity, mas nao substitui um ERP de pedidos/fiscal completo.
- `NotaFiscal` do AgroSaaS e suficiente para rastreio e integracao, mas nao para todos os detalhes fiscais do Sankhya.

## Itens que ja atendem completamente

- `Deposito`
- `SaldoEstoque`
- `LoteEstoque`
- `EstoqueMovimento`
- `Produto`
- `ProdutoAgricola`
- `ProdutoEstoque`
- `UnidadeMedida`
- `UnidadeMedidaConversao`
- `PlanoConta`
- `Despesa`
- `Receita`
- `Commodity`
- `CommodityClassificacao`
- `CotacaoCommodity`
- `SankhyaGatewayAuthService` para autenticacao Gateway e teste controlado de conexao
- `SankhyaCanonicalAdapter` para configuracao, health e jobs canonicamente integrados

## Itens que exigem apenas extensao

- `Pessoa` como master unico para cliente, fornecedor, transportadora, representante e parceiro
- `TipoRelacionamento` para codigos de papel sincronizados com Sankhya
- `Rateio` como aproximacao de centro de custo
- `NotaFiscal` como snapshot fiscal
- `ComercializacaoCommodity` como contrato comercial do piloto
- `SankhyaTabela` como apoio para tabelas fiscais/referencia

## Itens realmente inexistentes

- Empresa como entidade canonica separada
- Filial como entidade canonica separada
- Unidade de Negocio como entidade canonica separada
- Natureza Financeira como master separado
- Inventario como master/processo canonico separado

## Riscos tecnicos identificados

1. Duplicidade de pessoas se o upsert nao usar `CODPARC` + documento + papel.
2. Duplicidade de produtos se o cadastro interno for tratado como dono do mesmo dado que Sankhya.
3. Divergencia de unidade de medida se a conversao nao respeitar a unidade canonica global.
4. Confusao entre centro de custo e rateio.
5. Confusao entre deposito e localizacao interna de estoque.
6. Mistura entre contrato comercial, pedido e documento fiscal no mesmo objeto.
7. Leitura excessiva de notas fiscais sem validar chave de acesso e serie.
8. Cracao de duplicidade arquitetural ao tentar modelar empresa/filial sem necessidade operacional real.

## Recomendacoes para a proxima etapa

- Usar o presente mapeamento como contrato mestre antes de qualquer sync de negocio.
- Reaproveitar os masters existentes primeiro e adicionar extensoes apenas onde o dado externo nao cabe no modelo atual.
- Tratar `Pessoa`, `Produto`, `PlanoConta`, `Deposito`, `UnidadeMedida` e `Commodity` como bases canonicas ja maduras.
- Manter Sankhya como origem para cadastro comercial/fiscal do piloto e AgroSaaS como origem para contexto agronomico e operacional.
- Definir explicitamente a politica de centro de custo e natureza financeira antes de qualquer importacao financeira em volume.
- Validar a semantica de `CODLOCAL`, `CODEMP` e `CODFILIAL` com o usuario de negocio antes da fase de sincronizacao.

## Validacao executada

- `git diff --check`

Resultado: sem divergencias de formato detectadas.

