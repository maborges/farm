# INTEGRATION-DOMAIN-01 - Auditoria de Entidades de Integracao AgroSaaS x Sankhya

Data: 2026-07-06

## Escopo

Auditoria arquitetural para identificar o universo completo de entidades que podem participar da integracao entre AgroSaaS e ERP Sankhya.

Esta auditoria nao implementa nada, nao cria migrations, nao altera codigo, nao altera contratos, nao altera autenticacao Gateway-first e nao altera a estrategia de sincronizacao.

## Fontes auditadas

### Documentacao Sankhya e Integracoes

- `docs/implementation/reports/integracao_sankhya_especificacao_tecnica.md`
- `services/api/integracoes/sankhya/README.md`
- `docs/qwen/SANKHYA_IMPLEMENTACAO_COMPLETA.md`
- `docs/implementation/reports/SANKHYA-AUTH-01-GATEWAY-CREDENTIALS.md`
- `docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md`
- `docs/implementation/reports/SANKHYA-AUTH-03-VALIDACAO-ESPECIFICACAO-TECNICA.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-01-ADAPTER-CANONICO.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-02-API-UX-CANONICA-STATUS-JOBS-HEALTH.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md`
- `docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md`
- `docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md`
- `docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md`
- `docs/implementation/reports/SANKHYA-SYNC-04-AUDITORIA-VINCULO-REGISTROS-AGROSAAS-SANKHYA.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/implementation/reports/INTEGRATIONS-DOMAIN-02-ESPECIFICACAO-MATERIALIZACAO.md`

### Codigo Sankhya e dominio de Integracoes

- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/models.py`
- `services/api/migrations/versions/fase3_sankhya.py`
- `services/api/migrations/versions/20260704_sankhya_gateway_auth.py`
- `services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py`
- `services/api/migrations/versions/20260701_integrations_domain_03b_operations.py`
- `services/api/tests/unit/integracoes/*`

### Entidades AgroSaaS auditadas

- Organizacao: `Tenant`, `UnidadeProdutiva`, `Propriedade`, `ExploracaoRural`
- Pessoas: `Pessoa`, `PessoaDocumento`, `PessoaRelacionamento`, `Fornecedor`, `ColaboradorRH`
- Produtos: `Produto`, `ProdutoAgricola`, `ProdutoEstoque`, `ProdutoEPI`, `Marca`, `CategoriaProduto`, `Commodity`
- Estoque: `Deposito`, `SaldoEstoque`, `LoteEstoque`, `EstoqueMovimento`
- Financeiro: `PlanoConta`, `ContaBancaria`, `Despesa`, `Receita`, `LancamentoFinanceiro`
- Fiscal: `NotaFiscal`, campos fiscais em `Despesa`, `Receita`, `ComercializacaoCommodity`
- Comercial: `PedidoCompra`, `SolicitacaoCompra`, `CotacaoCompra`, `ComercializacaoCommodity`, `ContratoFuturo`
- Producao rural: `Safra`, `SafraTalhao`, `AreaRural`, `RomaneioColheita`, `ProdutoColhido`
- Frota: `Equipamento`, `Abastecimento`, `PlanoManutencao`, `OrdemServico`, `RegistroManutencao`, `JornadaEquipamento`
- RH: `Departamento`, `ColaboradorRH`, `LancamentoDiaria`, `Empreitada`, `EsocialEvento`

## Resumo executivo

O modelo atual do AgroSaaS contempla o dominio de Integracoes como runtime governado: provider, configuracao, credenciais, features, policies, jobs, health, logs e eventos. Esse desenho atende bem a operacao, observabilidade e seguranca da integracao Sankhya.

O modelo atual tambem possui tabelas provider-specific do Sankhya para staging de:

- pessoas;
- produtos;
- NFe;
- lancamentos financeiros;
- tabelas auxiliares;
- configuracao e logs.

Porem, o modelo ainda nao contempla todo o universo de entidades mestre do ERP Sankhya com associacoes oficiais registro-a-registro. A lacuna principal permanece a identidade externa persistente por entidade de negocio.

Para o primeiro piloto, o escopo read-only/manual-first continua viavel com restricoes. Para Go-Live amplo ou evolucao bidirecional, ainda ha lacunas arquiteturais relevantes em empresa/filial, estabelecimento, centro de custo, natureza financeira, conta corrente, deposito/local, pedidos/documentos e vinculos de entidades canonicas.

## APIs Sankhya auditadas no projeto

| API/Servico | Finalidade | Entidades envolvidas | Situacao no AgroSaaS |
| --- | --- | --- | --- |
| Login/autenticacao Gateway | Obter token tecnico | Configuracao/credencial | Implementado via `SankhyaGatewayAuthService` |
| `DbExplorerSP.executeQuery` | Consulta controlada de dados mestres/documentos/saldos | Parceiros, produtos, contas, documentos, saldos | Previsto na especificacao; nao aparece como client funcional no modulo atual |
| `DatasetSP.save` | Inserir/atualizar entidades | Dados auxiliares, campos complementares | Previsto na especificacao; nao implementado como fluxo geral |
| `CACSP.incluirNota` | Criar documento no ERP | Pedido, contrato, documento operacional/fiscal | Previsto na especificacao; modulo atual usa abstrações legadas de `NFe.save`/`Lancamento.save` |
| `CACSP.incluirAlterarCabecalhoNota` | Alterar cabecalho | Parceiro, empresa, centro de custo, financeiro | Previsto; nao implementado |
| `CACSP.incluirAlterarItemNota` | Alterar itens | Produto, quantidade, valor | Previsto; nao implementado |
| `ServicosNfeSP.confirmarNotas` | Confirmar documento | NFe/documento/pedido | Previsto; nao implementado |
| `CACSP.cancelarNota` | Cancelar documento | Documento, motivo | Previsto; nao implementado |
| `SelecaoDocumentoSP.faturar` | Faturar documento base | Pedido/contrato/fatura | Previsto; nao implementado |
| `PessoaFisica.findAll`/`PessoaJuridica.findAll` | Importar parceiros | Pessoas/parceiros | Implementado em staging |
| `Produto.findAll` | Importar produtos | Produtos | Implementado em staging |
| `NFe.findEntradaByPeriodo` | Importar NFe | Fiscal | Implementado em staging |
| `Lancamento.findByPeriodo` | Importar financeiro | Titulos/lancamentos | Implementado em staging |

## Matriz completa de entidades

### Organizacao

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Organizacao | Tenant/ambiente de integracao | `Tenant` | Parcial: `tenant_id` em `sankhya_config` e `tenant_integracoes` | Sim | P0 |
| Organizacao | Empresa | Nao ha master dedicado; aproximacao por `Tenant`/futuro Estabelecimento | Nao | Condicional se piloto for monoempresa; sim se houver `CODEMP` relevante | P0/P1 |
| Organizacao | Filial | Nao ha master dedicado | Nao | Nao para piloto monoescopo; sim em multi-CNPJ | P1 |
| Organizacao | Unidade de Negocio | `UnidadeProdutiva` cobre operacao, nao unidade administrativa ERP | Nao | Nao | P2 |
| Organizacao | Estabelecimento/Matriz/Filial fiscal | Conceito arquitetural previsto, nao materializado como dominio completo | Nao | Nao no piloto tenant-scoped | P1 |
| Organizacao | Unidade Produtiva | `UnidadeProdutiva` | Nao deve ser escopo de ERP; sem de-para Sankhya | Nao | Fora do escopo do ERP |

### Pessoas

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Pessoas | Parceiro/Pessoa | `Pessoa` | Parcial: `sankhya_pessoas.sankhya_id = CODPARC`, sem FK para `Pessoa` | Sim | P0 |
| Pessoas | Cliente | `Pessoa` + `PessoaRelacionamento` + `Receita.pessoa_id` | Parcial via staging, sem papel oficial vinculado | Sim | P0 |
| Pessoas | Fornecedor | `Pessoa` + `Fornecedor` legado + `Despesa.pessoa_id` | Parcial via staging, sem FK para canonico | Sim | P0 |
| Pessoas | Transportadora | `Pessoa` + papel configuravel | Parcial se vier em `sankhya_pessoas.categoria` | Nao no piloto inicial | P1 |
| Pessoas | Representante | `Pessoa` + papel configuravel | Parcial se vier em `sankhya_pessoas.categoria` | Nao | P1 |
| Pessoas | Funcionario | `ColaboradorRH` + `Pessoa` | Nao | Nao | P2 |
| Pessoas | Prestador de Servico | `Pessoa` + papel/prestador | Parcial por estrutura local, sem de-para Sankhya | Nao | P1 |

### Produtos

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Produtos | Produto | `Produto` | Parcial: `sankhya_produtos.sankhya_id = CODPROD`, sem FK para `Produto` | Sim | P0 |
| Produtos | Insumo | `Produto` + `ProdutoAgricola`/`ProdutoEstoque` | Parcial via staging de produto | Sim | P0 |
| Produtos | Servico | `Produto` tipo `SERVICO` | Parcial via staging, sem mapeamento de tipo | Sim se servicos entrarem no financeiro | P1 |
| Produtos | Grupo de Produto | `CategoriaProduto`/`TipoProduto` | Nao | Nao | P1 |
| Produtos | Categoria | `CategoriaProduto` | Nao | Nao | P1 |
| Produtos | Unidade de Medida | `Produto.unidade_medida`, medidas canonicas | Parcial: `sankhya_produtos.unidade` textual | Sim para produtos | P0 |
| Produtos | NCM/CEST/CFOP auxiliares | `ProdutoEstoque.ncm`, `SankhyaTabela`, campos fiscais | Parcial | Nao como master no piloto | P1 |

### Estoque

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Estoque | Deposito | `Deposito` | Nao; `CODLOCAL` nao persistido | P1 no piloto, se houver saldo/recebimento | P1 |
| Estoque | Local de Estoque | `Deposito.localizacao_desc`/localizacao operacional | Nao | Nao | P1 |
| Estoque | Lote/controle | `LoteEstoque` | Nao | Nao no primeiro corte | P1 |
| Estoque | Saldo | `SaldoEstoque` | Nao | P1 se estoque entrar no piloto | P1 |
| Estoque | Movimento | `EstoqueMovimento` | Nao | Nao | P1 |
| Estoque | Inventario | Nao ha processo/master dedicado | Nao | Nao | P2 |

### Financeiro

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Financeiro | Plano de Contas | `PlanoConta` | Nao | Sim se financeiro for importado classificado | P0 |
| Financeiro | Conta Corrente | `ContaBancaria`/conciliacao | Nao | Nao no piloto inicial | P1 |
| Financeiro | Banco | `PessoaBancario`/`ContaBancaria` | Nao | Nao | P1 |
| Financeiro | Agencia | `PessoaBancario`/`ContaBancaria` | Nao | Nao | P1 |
| Financeiro | Carteira | Nao ha master claro | Nao | Nao | P2 |
| Financeiro | Centro de Resultado | Sem master dedicado; aproximacao por safra/UP/rateio | Nao | Condicional | P1 |
| Financeiro | Centro de Custo | `Rateio`/origens operacionais; sem master | Nao | Sim se Sankhya exigir `CODCENCUS` em titulos | P0/P1 |
| Financeiro | Natureza Financeira | Sem master dedicado; aproximacao por `PlanoConta` | Nao | Sim se importacao depender de `CODNAT` | P0 |
| Financeiro | Contas a Pagar | `Despesa`; staging `SankhyaLancamentoFinanceiro` | Parcial: staging por `DESDOB`, sem FK para `Despesa` | Sim | P0 |
| Financeiro | Contas a Receber | `Receita`; staging `SankhyaLancamentoFinanceiro` | Parcial: staging por `DESDOB`, sem FK para `Receita` | Sim | P0 |
| Financeiro | Baixas | Status/data pagamento em `Despesa`/`Receita`; staging financeiro | Nao como entidade/vinculo separado | P1 | P1 |
| Financeiro | Movimentacoes Financeiras | `LancamentoFinanceiro`, `LancamentoBancario` | Nao | Nao | P1 |

### Fiscal

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Fiscal | Nota Fiscal/NFe | `NotaFiscal`; staging `SankhyaNFe` | Parcial: `CHAVEACESSO` nos dois lados, sem FK | Sim | P0 |
| Fiscal | Serie | `serie`, `serie_nf`, `SankhyaNFe.serie` | Parcial como campo textual | Sim para NFe | P0 |
| Fiscal | Numero | `numero`, `numero_nf`, `numero_documento` | Parcial como campo textual | Sim para NFe/financeiro | P0 |
| Fiscal | Chave de Acesso | `chave_acesso`, `chave_nfe`, `nf_chave` | Sim para idempotencia fiscal por chave | Sim | P0 |
| Fiscal | Tipo de Operacao | Campo parcial em NFe/Sankhya payload; sem master | Parcial | Sim se documentos forem criados no ERP | P1 |
| Fiscal | Modelo Fiscal | `NotaFiscal.tipo`, `SankhyaNFe.modelo` | Parcial | Sim para NFe | P0 |
| Fiscal | Situacao Fiscal | `StatusSEFAZ`, `status_sankhya` | Parcial, vocabularios diferentes | Sim para NFe | P0 |
| Fiscal | CFOP/NCM/CST/CSOSN | Campos e `SankhyaTabela` | Parcial como referencia | Nao no piloto inicial | P1 |

### Comercial

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Comercial | Pedido | `PedidoCompra` para compra; pedido comercial de venda nao dedicado | Nao | Nao | P1 |
| Comercial | Contrato | `ComercializacaoCommodity`; `ContratoFuturo` para hedge | Nao | Nao | P2 |
| Comercial | Comercializacao | `ComercializacaoCommodity` | Nao | Nao | P2 |
| Comercial | Commodity | `Commodity` | Nao | Nao | P2 |
| Comercial | Barter | Parcial/nao identificado como entidade dedicada no escopo auditado | Nao | Nao | P2 |
| Comercial | Documento base/faturamento | NFe/Receita/Comercializacao | Nao | Nao no piloto read-only | P1 |

### Producao Rural

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Producao Rural | Safra | `Safra` | Nao; origem AgroSaaS | Nao para ERP | Fora do escopo Sankhya P0 |
| Producao Rural | Talhao | `AreaRural`/`SafraTalhao` | Nao; origem AgroSaaS | Nao | Fora do escopo Sankhya P0 |
| Producao Rural | Area Operacional | `AreaRural`, `ProductionUnit` | Nao; origem AgroSaaS | Nao | Fora do escopo Sankhya P0 |
| Producao Rural | Producao | `ProdutoColhido` | Nao | Nao | P2 |
| Producao Rural | Romaneio | `RomaneioColheita` | Nao | Nao | P2 |
| Producao Rural | Armazenagem | `Deposito`, `ProdutoColhido.armazem_id`, estoque | Nao | Nao | P1/P2 |
| Producao Rural | Colheita | `RomaneioColheita`, `ProdutoColhido` | Nao | Nao | P2 |

### Maquinas e Equipamentos

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Frota | Equipamentos/Maquinas | `Equipamento` | Nao | Nao | P2 |
| Frota | Abastecimentos | `Abastecimento` | Nao | Nao | P2 |
| Frota | Manutencoes | `PlanoManutencao`, `OrdemServico`, `RegistroManutencao` | Nao | Nao | P2 |
| Frota | Jornada/Apontamento de maquina | `JornadaEquipamento` | Nao | Nao | P2 |

### RH

| Dominio | Entidade Sankhya | Entidade AgroSaaS | Associacao Oficial Existe? | Obrigatoria no Piloto? | Prioridade |
| --- | --- | --- | --- | --- | --- |
| RH | Colaboradores | `ColaboradorRH` + `Pessoa` | Nao | Nao | P2 |
| RH | Equipes/Departamentos | `Departamento`; equipes nao identificadas como master Sankhya no conector atual | Nao | Nao | P2 |
| RH | Ordens de Servico | `OrdemServico` frota/operacional | Nao | Nao | P2 |
| RH | Apontamentos | `LancamentoDiaria`, `Empreitada`, `JornadaEquipamento` | Nao | Nao | P2 |
| RH/Fiscal | eSocial | `EsocialEvento` | Nao para Sankhya | Nao | Fora do escopo Sankhya atual |

## Associacao entre registros

| Entidade | ID AgroSaaS | ID Sankhya | Onde armazena associacao hoje | Dedupe atual | Mudanca de ID externo |
| --- | --- | --- | --- | --- | --- |
| Tenant/configuracao | `tenants.id` | Config/ambiente provider | `sankhya_config.tenant_id`, `tenant_integracoes.tenant_id` | Unique em `tenant_id` | Nao cobre `CODEMP`/`CODFILIAL` |
| Pessoa/parceiro | `cadastros_pessoas.id` | `CODPARC` | Apenas `sankhya_pessoas.sankhya_id` | Upsert por `sankhya_id` no staging | Pode duplicar staging/canonico |
| Produto | `cadastros_produtos.id` | `CODPROD` | Apenas `sankhya_produtos.sankhya_id` | Upsert por `sankhya_id` no staging | Pode duplicar staging/canonico |
| NFe | `fin_notas_fiscais.id` | `CHAVEACESSO`, `NUNOTA`/`CODNEG` se existir | `sankhya_nfe.chave_acesso`, `sankhya_nfe.sankhya_id` | Chave de acesso | Chave de acesso mitiga; sem FK local |
| Financeiro | `fin_despesas.id`/`fin_receitas.id` | `DESDOB`, `NUMDOC`, `CODPARC` | `sankhya_lancamentos_financeiros.sankhya_id` | Upsert por `DESDOB` no staging | Alto risco se `DESDOB` mudar ou repetir por tenant |
| Deposito | `estoque_depositos.id` | `CODLOCAL` | Nao existe | Nao existe | Nao tratado |
| Plano/Natureza | `fin_planos_conta.id` | `CODNAT`/conta ERP | Nao existe | Nao existe | Nao tratado |
| Centro de Custo/Resultado | Sem master completo | `CODCENCUS`/centro resultado | Nao existe | Nao existe | Nao tratado |
| Pedido/Documento | `compras_pedidos.id` ou documento futuro | `NUNOTA`/ID documento ERP | Nao existe | Nao existe | Nao tratado |
| Equipamento | `cadastros_equipamentos.id` | Codigo patrimonial/ativo ERP | Nao existe | Nao existe | Nao tratado |
| Colaborador | `rh_colaboradores.id`/`Pessoa.id` | Codigo funcionario/parceiro ERP | Nao existe | Documento local apenas | Nao tratado |

## Origem oficial da informacao

| Entidade | Origem recomendada/piloto | Direcao atual |
| --- | --- |
| Configuracao/credenciais | AgroSaaS | AgroSaaS configura e testa Gateway |
| Cliente/fornecedor/parceiro | Sankhya no piloto | Pull para staging |
| Produto/insumo/servico | Sankhya no piloto | Pull para staging |
| Unidade de medida/conversao | AgroSaaS, com de-para futuro | Parcial via campo textual |
| Plano de contas/natureza/centro de custo | Sankhya para piloto financeiro | Ainda sem de-para |
| Contas a pagar/receber | Sankhya no piloto | Pull para staging |
| NFe | Sankhya no piloto, chave fiscal como identidade | Pull/export parcial em staging |
| Depositos/local de estoque | Sankhya para deposito, AgroSaaS para ledger operacional | Sem sync/vinculo ativo |
| Safra/talhao/area/operacao agricola | AgroSaaS | Fora do ERP no piloto |
| Romaneio/producao/comercializacao | AgroSaaS inicialmente | Sem Sankhya no piloto |
| Equipamentos/frota | AgroSaaS | Sem Sankhya no piloto |
| RH operacional | AgroSaaS | Sem Sankhya no piloto |
| Empresa/filial/estabelecimento | Pendente; arquitetura indica `ESTABELECIMENTO` futuro | Sem materializacao completa |

## Dependencias por entidade principal

| Entidade principal | Dependencias necessarias |
| --- | --- |
| Pessoa/parceiro | Tenant, documento normalizado, papel/categoria, relacionamento comercial |
| Cliente | Pessoa/parceiro, papel cliente, condicao comercial, eventualmente representante |
| Fornecedor | Pessoa/parceiro, papel fornecedor, condicao pagamento, produtos/servicos fornecidos |
| Produto/insumo | Unidade de medida, categoria/grupo, NCM/CEST se fiscal, controle estoque |
| Servico | Unidade, natureza/conta, categoria fiscal se faturavel |
| Deposito/local | Tenant, estabelecimento/empresa/filial, unidade produtiva operacional, `CODLOCAL` |
| Saldo/lote | Produto, deposito/local, lote/controle, unidade, data/snapshot |
| Conta a pagar | Fornecedor, empresa/filial, natureza financeira, centro custo/resultado, conta corrente, documento, parcela/baixa |
| Conta a receber | Cliente, empresa/filial, natureza financeira, centro custo/resultado, conta corrente, documento, parcela/baixa |
| NFe | Empresa/filial, parceiro, tipo operacao, modelo, serie, numero, chave, itens/produtos, status fiscal |
| Pedido/documento | Empresa/filial, parceiro, tipo operacao, itens/produtos, centro custo, condicao pagamento |
| Comercializacao | Cliente/comprador, commodity, produto colhido, contrato, NF, receita |
| Romaneio/producao | Safra, talhao/area, commodity, equipamento, operador, deposito/armazem, qualidade |
| Equipamento | Tenant, unidade produtiva/alocacao, operador, abastecimento, manutencao |
| Manutencao/OS | Equipamento, produtos/pecas, deposito, tecnico/colaborador, financeiro/custo |
| Colaborador/apontamento | Pessoa, departamento/equipe, unidade produtiva, safra, pagamento/financeiro |

## Entidades totalmente prontas

Estas entidades estao prontas como runtime de integracao, nao necessariamente como de-para de negocio:

- `SankhyaConfig` por tenant.
- `TenantIntegracao` como configuracao canonica do provider.
- `IntegrationCredential` com segredo criptografado/versionado.
- `IntegrationVersion`.
- `IntegrationFeature`.
- `IntegrationSyncPolicy`.
- `IntegrationJob`.
- `IntegrationHealth`.
- `SankhyaSyncLog`.
- `SankhyaNFe` para idempotencia fiscal por `CHAVEACESSO` no staging.

## Entidades parcialmente prontas

- Pessoas/parceiros, clientes e fornecedores: staging existe, entidade canonica existe, de-para nao existe.
- Produtos/insumos/servicos: staging existe, entidade canonica existe, de-para nao existe.
- NFe: chave de acesso existe dos dois lados, mas a associacao nao e persistida por FK/de-para.
- Contas a pagar/receber: staging financeiro existe, entidades canonicas existem, de-para nao existe.
- Unidade de medida: modelo local existe, unidade Sankhya vem textual em produto.
- Depositos/estoque: modelo local existe, feature de estoque e futura/desabilitada, `CODLOCAL` nao existe.
- Plano de contas: modelo local existe, mas `CODNAT`/natureza Sankhya nao esta vinculado.
- Comercializacao/contratos: modelo local existe, sem representacao Sankhya.
- RH/frota/producao rural: modelos locais existem, sem Sankhya.

## Entidades ainda sem associacao oficial

- Empresa.
- Filial.
- Estabelecimento fiscal.
- Unidade de negocio administrativa.
- Unidade produtiva com heranca administrativa de estabelecimento.
- `Pessoa.id <-> CODPARC`.
- `Produto.id <-> CODPROD`.
- `Deposito.id <-> CODLOCAL`.
- `PlanoConta.id <-> CODNAT` ou equivalente.
- Centro de custo/resultado <-> `CODCENCUS`.
- Conta corrente/banco/agencia/carteira <-> cadastros financeiros do Sankhya.
- `Despesa.id`/`Receita.id <-> titulo Sankhya`.
- Pedido/contrato/documento <-> `NUNOTA`/documento ERP.
- Equipamento/maquina <-> ativo/patrimonio ERP.
- Colaborador <-> funcionario/parceiro ERP.

## Entidades fora do escopo do piloto

- Filial/estabelecimento, se o piloto operar monoempresa/tenant.
- Unidade de negocio administrativa.
- Inventario formal.
- Pedido/documento bidirecional.
- Contratos de comercializacao.
- Commodity/Barter.
- Safra, talhao, area operacional.
- Romaneio, colheita, producao e armazenagem avancada.
- Maquinas/equipamentos, abastecimentos e manutencoes.
- RH, equipes, apontamentos e eSocial.

## Riscos arquiteturais

1. **Universo mestre incompleto**: o runtime de integracao esta maduro, mas as entidades mestre vinculaveis ainda nao foram modeladas transversalmente.
2. **Falta de `Estabelecimento` materializado**: a arquitetura reconhece `ESTABELECIMENTO`, mas o piloto Sankhya segue tenant-scoped. Multiempresa/multifilial exigira resolucao antes do Go-Live amplo.
3. **Codigos externos sem escopo composto**: `CODPARC`, `CODPROD`, `DESDOB` e similares nao devem ser tratados como globais entre tenants/ambientes.
4. **Promocao de staging para canonico sem de-para**: pode criar duplicidade em `Pessoa`, `Produto`, `Despesa`, `Receita` e `Deposito`.
5. **Confusao entre centro de custo, centro de resultado e rateio**: o AgroSaaS tem rateios operacionais, mas nao um master equivalente ao ERP.
6. **Natureza financeira sem destino oficial**: `CODNAT` nao possui associacao canonica.
7. **Conta corrente/carteira bancaria ausentes do mapeamento Sankhya**: contas e baixas futuras dependem disso.
8. **Documentos Sankhya futuros exigem `NUNOTA`/ID documental**: a especificacao tecnica requer persistir identificador do documento no ERP, status, payload e retorno.
9. **Fiscal parcialmente seguro apenas por chave de acesso**: NFe tem melhor identidade natural, mas serie/numero/status/tipo operacao ainda precisam de vocabulário controlado.
10. **Estoque depende de semantica real de `CODLOCAL`**: local pode significar deposito fisico, armazem, localizacao interna ou estrutura fiscal.
11. **Bidirecionalidade futura sem idempotencia documental completa**: APIs de inclusao/alteracao/confirmacao/faturamento/cancelamento exigem estado persistente por transacao/documento.

## Recomendacoes de arquitetura

1. Manter o dominio canônico de Integracoes como fonte de runtime: provider, config, credential, feature, policy, job, health e versionamento.
2. Tratar `sankhya_*` como provider-specific staging, nao como fonte canonica de negocio.
3. Antes de qualquer nova implementacao, fechar uma matriz oficial de entidades vinculaveis por provider, com prioridade e source of truth.
4. Separar tres problemas: runtime da integracao, staging do provider e identidade externa dos registros de negocio.
5. Nao usar Unidade Produtiva como escopo de ERP. Para multiempresa/multifilial, usar o conceito arquitetural de `ESTABELECIMENTO`.
6. Validar com o usuario Sankhya quais identificadores sao estaveis para empresa, filial, parceiro, produto, local, natureza, centro de custo, titulo e documento.
7. Exigir que futuras associacoes considerem tenant, provider, ambiente e identificador externo; codigos numericos isolados nao sao suficientes para SaaS multi-tenant.
8. Para documentos criados no Sankhya, cumprir a especificacao tecnica: persistir identificador interno da transacao, identificador ERP, status local, status ERP, payload, resposta, tentativas e erro final.
9. Priorizar NFe e financeiro por janela controlada e chave natural forte antes de fluxos bidirecionais de pedido/documento.

## Recomendacoes para o primeiro piloto

1. Manter o piloto como `manual first`, `tenant scoped`, `read-only` e baseado em staging.
2. P0 real do piloto: configuracao/credencial, pessoas/parceiros, produtos/insumos, contas a pagar, contas a receber e NFe.
3. Nao promover automaticamente staging para cadastros canonicos sem regra aprovada de de-para.
4. Se o cliente Sankhya tiver uma unica empresa/filial no piloto, registrar esse pressuposto operacional explicitamente.
5. Se houver `CODEMP`/`CODFILIAL` relevante no piloto, considerar isso bloqueador arquitetural antes de Go-Live.
6. Para NFe, usar `CHAVEACESSO` como idempotencia primaria.
7. Para financeiro, nao aceitar `DESDOB` isolado como identidade duradoura sem validar chave composta real.
8. Estoque deve entrar apenas se `CODLOCAL`, produto, unidade e lote/saldo forem validados com o responsavel do ERP.

## Go-Live readiness

| Criterio | Resultado |
| --- | --- |
| Conexao Gateway-first | Pronto |
| Configuracao por tenant | Pronto |
| Credenciais criptografadas/versionadas | Pronto |
| Jobs, health, logs e timeline | Pronto |
| Staging de pessoas/produtos/NFe/financeiro | Parcialmente pronto |
| Associacao oficial registro-a-registro | Lacuna arquitetural |
| Empresa/filial/estabelecimento | Lacuna arquitetural |
| Centro de custo/natureza/conta corrente | Lacuna arquitetural |
| Estoque por deposito/local/lote/saldo | Lacuna arquitetural para Sankhya |
| Documentos bidirecionais | Lacuna arquitetural para Go-Live amplo |

Conclusao: o modelo de integracao do AgroSaaS contempla o runtime essencial e parte do staging do ERP Sankhya, mas ainda nao contempla todas as entidades relevantes do ERP com associacao oficial. Existem lacunas arquiteturais que precisam ser resolvidas antes de um Go-Live amplo ou bidirecional. Para o primeiro piloto controlado, o modelo atual atende com restricoes, desde que permaneça read-only/manual-first e com validacao manual dos dados importados.

## Validacao

Executar ao final:

```bash
git diff --check
```
