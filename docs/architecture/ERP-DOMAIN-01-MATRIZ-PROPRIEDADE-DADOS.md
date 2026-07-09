# ERP-DOMAIN-01 - Matriz Oficial de Propriedade dos Dados AgroSaaS x ERPs

Status: APROVADA
Categoria: Arquitetura de Domínio
Tipo: Regra Arquitetural
Data: 2026-07-08

## 1. Objetivo

Definir a arquitetura oficial, genérica e agnóstica a provider para integração do AgroSaaS com ERPs.

Este documento separa explicitamente:

```text
ERP Domain Architecture
```

de:

```text
ERP Provider Adapter
```

Regra central:

- `ERP-DOMAIN-01` define as regras oficiais do domínio ERP;
- `SankhyaCanonicalAdapter` e futuros adapters apenas implementam essas regras;
- nenhuma decisão específica de Sankhya pode virar regra geral sem passar por esta matriz.

## 2. Princípios oficiais

### 2.1 Fronteiras de domínio

- o AgroSaaS é master do domínio operacional agrícola, pecuário, territorial e analítico;
- o ERP é master do domínio administrativo, fiscal, contábil e financeiro administrativo;
- integrações ERP não podem capturar para o ERP a autoria oficial da operação rural;
- integrações ERP não podem transformar `UnidadeProdutiva` em escopo administrativo de credencial.

### 2.2 Separação obrigatória

Separações mandatórias:

- estoque operacional versus estoque administrativo/contábil;
- financeiro operacional AgroSaaS versus financeiro administrativo ERP;
- rastreabilidade operacional versus rastreabilidade documental/fiscal;
- arquitetura do domínio ERP versus implementação do provider.

### 2.3 Escopo oficial

O escopo oficial do ERP é:

- `TENANT` quando o ERP representa a organização inteira;
- `ESTABELECIMENTO` quando existir contexto fiscal/administrativo distinto por empresa, matriz ou filial.

O escopo proibido para ERP é:

- `UNIDADE_PRODUTIVA`

### 2.4 Multi-ERP v1.0

Decisão oficial v1.0:

- o AgroSaaS deve suportar operação sem ERP;
- o AgroSaaS deve suportar um ERP principal por `TENANT`;
- o AgroSaaS deve suportar, como arquitetura-alvo, um ERP por `ESTABELECIMENTO`;
- multi-ERP simultâneo por domínio especializado do mesmo escopo fica como evolução futura;
- v1.0 não assume ERP financeiro e ERP fiscal distintos para o mesmo escopo operacional, embora a matriz já permita essa evolução;
- a resolução do provider deve sempre acontecer por escopo administrativo, nunca por talhão, lote, piquete ou unidade produtiva.

## 3. Papéis oficiais dos sistemas

### 3.1 AgroSaaS deve ser master de

- operação agrícola;
- operação pecuária;
- território operacional;
- unidade produtiva;
- propriedade operacional;
- área rural;
- talhão;
- safra;
- cultivo;
- operação agrícola executada;
- recomendação agronômica;
- aplicação de insumos;
- colheita;
- romaneio;
- produto colhido;
- custos operacionais;
- `CostAllocation`;
- DRE operacional;
- rentabilidade operacional;
- rastreabilidade operacional;
- clima;
- NDVI;
- alertas;
- produtividade.

### 3.2 ERP deve ser master de

- fiscal;
- contábil;
- financeiro administrativo;
- escrituração;
- faturamento fiscal;
- contas a pagar;
- contas a receber;
- pagamentos;
- recebimentos;
- baixas;
- conciliação bancária administrativa;
- bancos;
- contas correntes;
- documentos fiscais;
- impostos;
- CT-e;
- MDF-e;
- documentação financeira administrativa.

### 3.3 Compartilhados com regra explícita

Entidades que exigem regra explícita por matriz:

- pessoas;
- clientes;
- fornecedores;
- produtos de estoque;
- depósitos;
- centros de custo;
- centros de resultado;
- tipos de operação;
- estoque;
- contratos;
- pedidos;
- comercialização;
- NFe.

## 4. Donos, direções e políticas oficiais

### 4.1 Donos permitidos

- `AGROSAAS`
- `ERP`
- `COMPARTILHADO_COM_MASTER_AGROSAAS`
- `COMPARTILHADO_COM_MASTER_ERP`
- `NÃO_SE_APLICA`

### 4.2 Direções permitidas

- `AGROSAAS → ERP`
- `ERP → AGROSAAS`
- `BIDIRECIONAL_CONTROLADO`
- `SEM_SINCRONIZACAO`
- `SOMENTE_REFERENCIA`

### 4.3 Política de conflito oficial

Políticas admitidas:

- `MASTER_AGROSAAS`: alteração no ERP não sobrepõe o AgroSaaS;
- `MASTER_ERP`: alteração no AgroSaaS não sobrepõe o ERP;
- `AGROSAAS_GERA_ERP_REFERENCIA`: AgroSaaS cria ou dispara o registro, ERP materializa o administrativo;
- `ERP_GERA_EVIDENCIA_AGROSAAS`: ERP gera documento oficial que retorna ao AgroSaaS como evidência;
- `RECONCILIACAO_MANUAL`: conflito precisa de reconciliação explícita;
- `NAO_SE_APLICA`.

## 5. Matriz oficial

| Entidade | Dono oficial | Criado em | Alterado em | Sincronização | Direção | Política de conflito | Obrigatório para adapter ERP? | Prioridade | Observação |
| -------- | ------------ | --------- | ----------- | ------------- | ------- | -------------------- | ----------------------------- | ---------- | ---------- |
| Pessoas | COMPARTILHADO_COM_MASTER_ERP | ERP ou AgroSaaS com reconciliação | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Identidade civil pode nascer no AgroSaaS, mas o adapter ERP deve suportar associação externa e reconciliação. |
| Clientes | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Papel comercial de pessoa. |
| Fornecedores | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Papel administrativo/compra. |
| Produtos de estoque | COMPARTILHADO_COM_MASTER_ERP | ERP ou AgroSaaS conforme onboarding | ERP ou reconciliação | Sim | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | REQUIRED | P0 | Quando existir ERP, o catálogo administrativo/fiscal tende a convergir para master ERP. |
| Produtos agrícolas | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | O ERP pode referenciar, mas não governa semântica agronômica. |
| Commodities | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Commodity é domínio de comercialização e hedge do AgroSaaS. |
| Culturas | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Cultura é semântica agronômica. |
| Bancos | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Fonte administrativa oficial. |
| Contas Correntes | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Necessário para integração financeira administrativa. |
| Empresas | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Empresa administrativa/fiscal. |
| Filiais | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Filial e matriz pertencem ao domínio administrativo. |
| Estabelecimentos | COMPARTILHADO_COM_MASTER_ERP | ERP ou modelagem administrativa AgroSaaS | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Ponte correta entre escopo fiscal e operação. |
| Depósitos | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP e AgroSaaS por referência operacional | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Cadastro mestre administrativo, uso operacional no AgroSaaS. |
| Naturezas financeiras | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Obrigatório para títulos e classificação financeira administrativa. |
| Centros de custo | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | AgroSaaS pode consumir como dimensão analítica. |
| Centros de resultado | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | AgroSaaS pode mapear para safra, unidade ou operação. |
| Tipos de operação | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P1 | Tipo administrativo do documento, não operação agrícola. |
| Unidade Produtiva | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | NOT_SUPPORTED | NÃO_APLICÁVEL | Não é escopo de ERP. |
| Propriedade | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Domínio operacional territorial. |
| Imóvel Rural | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Domínio documental/fundiário interno do AgroSaaS. |
| Área Rural | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Base territorial operacional. |
| Talhão | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Base agronômica da execução. |
| Safra | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Pode ser usada em rateios ou rastreabilidade. |
| Cultivo | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Semântica agronômica. |
| Operação Agrícola | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | AGROSAAS → ERP | MASTER_AGROSAAS | OPTIONAL | P1 | Pode originar custo, consumo e apontamento econômico. |
| Recomendação Agronômica | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Inteligência agronômica exclusiva. |
| Aplicação de insumos | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por efeito econômico | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P1 | A execução nasce no AgroSaaS; o ERP recebe reflexo administrativo quando necessário. |
| Colheita | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Pode alimentar comercialização ou rastreabilidade. |
| Romaneio | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P1 | Documento operacional e de origem. |
| Produto Colhido | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Base de comercialização e rastreabilidade. |
| Rastreabilidade | AGROSAAS | AgroSaaS | AgroSaaS | Sim, documental por referência | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | O ERP não é fonte da rastreabilidade operacional. |
| Piquete | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Operação pecuária. |
| Pastagem | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Operação pecuária/territorial. |
| Lote Animal | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P2 | Pode refletir efeitos administrativos futuros. |
| Animal | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P2 | Identidade zootécnica oficial. |
| Pesagem | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Dado operacional. |
| Vacinação | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Dado sanitário operacional. |
| Reprodução | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Dado operacional zootécnico. |
| Manejo | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P2 | Pode gerar custos, não governança administrativa. |
| Sanidade | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NÃO_APLICÁVEL | NÃO_APLICÁVEL | Operação e compliance zootécnico. |
| Saldo operacional | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por reconciliação | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | OPTIONAL | P0 | Deve existir separado do saldo fiscal/contábil. |
| Consumo de insumos | AGROSAAS | AgroSaaS | AgroSaaS | Sim | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P0 | Baixa operacional nasce no AgroSaaS. |
| Baixa por aplicação | AGROSAAS | AgroSaaS | AgroSaaS | Sim | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P0 | Deve poder refletir em estoque administrativo quando adotado. |
| Movimentação de campo | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P1 | Movimento operacional pode gerar espelho administrativo. |
| FIFO operacional | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P1 | Regra de consumo físico/operacional. |
| Custo operacional de estoque | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por efeito econômico | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | Custo agrícola do consumo permanece no AgroSaaS. |
| Transferência operacional | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | AGROSAAS → ERP | AGROSAAS_GERA_ERP_REFERENCIA | OPTIONAL | P1 | Se gerar reflexo contábil, adapter deve mapear. |
| Entrada fiscal | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Dimensão administrativa/contábil. |
| Movimento contábil | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Livro administrativo. |
| Inventário fiscal | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Relevante para reconciliação de estoques. |
| Transferências administrativas | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Transferência entre depósitos/estabelecimentos. |
| Valorização contábil | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Resultado contábil do estoque. |
| Custos | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por referência | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | O custo operacional oficial nasce no AgroSaaS. |
| Apropriação por operação | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por referência | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | Pode alimentar analytics e rateios no ERP. |
| CostAllocation | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | Contrato econômico oficial. |
| DRE | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P0 | A DRE operacional não é governada pelo ERP. |
| Rentabilidade | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P0 | Métrica analítica interna. |
| Custo por talhão | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P0 | Analítico. |
| Custo por safra | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P0 | Analítico. |
| Custo por lote | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P1 | Analítico. |
| Custo por saca | AGROSAAS | AgroSaaS | AgroSaaS | Não | SEM_SINCRONIZACAO | MASTER_AGROSAAS | NOT_SUPPORTED | P1 | Analítico. |
| Contas a pagar | COMPARTILHADO_COM_MASTER_ERP | AgroSaaS ou ERP | ERP | Sim | BIDIRECIONAL_CONTROLADO | AGROSAAS_GERA_ERP_REFERENCIA | REQUIRED | P0 | Título administrativo oficial deve residir no ERP após materialização. |
| Contas a receber | COMPARTILHADO_COM_MASTER_ERP | AgroSaaS ou ERP | ERP | Sim | BIDIRECIONAL_CONTROLADO | AGROSAAS_GERA_ERP_REFERENCIA | REQUIRED | P0 | Receitas operacionais podem originar títulos administrativos. |
| Pagamentos | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Retorna ao AgroSaaS para status e evidência. |
| Recebimentos | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Retorna ao AgroSaaS para status e evidência. |
| Baixas | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Baixa administrativa oficial. |
| Conciliação | ERP | ERP | ERP | Opcional | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Pode ficar só no ERP em v1. |
| Adiantamentos | ERP | ERP | ERP | Opcional | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Importante para cenários agrícolas. |
| Documentos financeiros | ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Evidência administrativa. |
| Contrato agrícola | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS | AgroSaaS e ERP por reflexo | Sim | AGROSAAS → ERP | MASTER_AGROSAAS | OPTIONAL | P0 | Contrato operacional/negocial nasce no AgroSaaS quando amarra safra, origem e execução. |
| Contrato de café | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS | AgroSaaS e ERP por reflexo | Sim | AGROSAAS → ERP | MASTER_AGROSAAS | OPTIONAL | P0 | Em cenário exportador, o AgroSaaS deve preservar vínculo com origem do lote. |
| Pedido | COMPARTILHADO_COM_MASTER_ERP | ERP ou AgroSaaS conforme fluxo | ERP | Sim | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | OPTIONAL | P0 | Pedido administrativo tende ao ERP; pedido operacional pode nascer no AgroSaaS. |
| Comercialização | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS | AgroSaaS e ERP por faturamento | Sim | AGROSAAS → ERP | MASTER_AGROSAAS | OPTIONAL | P0 | Comercialização agrícola depende de rastreabilidade de produto colhido. |
| Barter | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS | AgroSaaS e ERP | Sim | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | PROVIDER_SPECIFIC | P0 | Fluxo complexo, depende de suporte do provider. |
| Entrega | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS ou ERP | Ambos | Sim | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | OPTIONAL | P1 | Entrega física deve manter vínculo com contrato e lote. |
| Faturamento | ERP | ERP | ERP | Sim | ERP → AGROSAAS | ERP_GERA_EVIDENCIA_AGROSAAS | REQUIRED | P0 | Documento fiscal oficial emitido no ERP. |
| Fixação de preço | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P1 | Estratégia comercial/agronômica. |
| Hedge | AGROSAAS | AgroSaaS | AgroSaaS | Opcional | SOMENTE_REFERENCIA | MASTER_AGROSAAS | PROVIDER_SPECIFIC | P1 | O ERP pode apenas referenciar. |
| Cliente/exportador | COMPARTILHADO_COM_MASTER_ERP | ERP | ERP | Sim | ERP → AGROSAAS | MASTER_ERP | REQUIRED | P0 | Papel comercial e fiscal da pessoa. |
| Lote comercializado | AGROSAAS | AgroSaaS | AgroSaaS | Sim, por referência documental | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | Essencial para rastreabilidade de exportação. |
| NFe | COMPARTILHADO_COM_MASTER_ERP | ERP ou AgroSaaS conforme fluxo | ERP | Sim | BIDIRECIONAL_CONTROLADO | ERP_GERA_EVIDENCIA_AGROSAAS | REQUIRED | P0 | A emissão fiscal oficial do documento pertence ao ERP. |
| CT-e | ERP | ERP | ERP | Opcional | ERP → AGROSAAS | ERP_GERA_EVIDENCIA_AGROSAAS | PROVIDER_SPECIFIC | P1 | Documentação logística fiscal. |
| MDF-e | ERP | ERP | ERP | Opcional | ERP → AGROSAAS | ERP_GERA_EVIDENCIA_AGROSAAS | PROVIDER_SPECIFIC | P1 | Documentação logística fiscal. |
| Documentos fiscais | ERP | ERP | ERP | Sim | ERP → AGROSAAS | ERP_GERA_EVIDENCIA_AGROSAAS | REQUIRED | P0 | AgroSaaS consome como prova administrativa. |
| Impostos | ERP | ERP | ERP | Opcional | ERP → AGROSAAS | MASTER_ERP | OPTIONAL | P1 | Cálculo e escrituração fiscais. |
| Transporte | ERP | ERP ou sistema logístico | ERP | Opcional | ERP → AGROSAAS | MASTER_ERP | PROVIDER_SPECIFIC | P1 | Pode existir integração logística separada do ERP. |
| Expedição | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS e ERP | Ambos | Sim | BIDIRECIONAL_CONTROLADO | RECONCILIACAO_MANUAL | OPTIONAL | P1 | Expedição física deve manter elo com rastreabilidade. |
| Documentos de exportação | ERP | ERP ou sistemas externos | ERP | Opcional | ERP → AGROSAAS | ERP_GERA_EVIDENCIA_AGROSAAS | PROVIDER_SPECIFIC | P1 | Nem todo ERP suporta exportação. |
| Rastreabilidade documental | COMPARTILHADO_COM_MASTER_AGROSAAS | AgroSaaS e ERP | Ambos por referência | Sim | SOMENTE_REFERENCIA | MASTER_AGROSAAS | OPTIONAL | P0 | O ERP fornece evidência, não a cadeia operacional completa. |
| ExternalRecordAssociation | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Contrato obrigatório do domínio de integração. |
| IntegrationJob | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Observabilidade e execução. |
| IntegrationSyncPolicy | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Política de direção, trigger e prioridade. |
| IntegrationHealth | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Health e diagnóstico. |
| Reconciliação | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | RECONCILIACAO_MANUAL | REQUIRED | P0 | Fluxo obrigatório para conflitos e pendências. |
| Staging | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Quando necessário | SEM_SINCRONIZACAO | NAO_SE_APLICA | OPTIONAL | P1 | Necessário para providers com payload instável ou operações em lote. |
| Logs | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Trilha operacional. |
| Eventos de sync | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Contrato canônico desacoplado. |
| Adapters | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Implementação específica de provider. |
| Provider-specific config | NÃO_SE_APLICA | AgroSaaS | AgroSaaS | Sim | SEM_SINCRONIZACAO | NAO_SE_APLICA | REQUIRED | P0 | Credenciais, autenticação, paginação, limites e features. |

## 6. Respostas oficiais às questões críticas

### 6.1 Contrato agrícola nasce onde?

Decisão:

- no AgroSaaS quando o contrato amarra safra, lote, origem, entrega e rastreabilidade operacional;
- o ERP recebe reflexo administrativo, faturamento e financeiro quando aplicável.

### 6.2 Comercialização nasce onde?

Decisão:

- no AgroSaaS, porque depende da ligação com commodity, safra, produto colhido, entrega e rentabilidade operacional;
- o ERP consome os reflexos administrativos e fiscais.

### 6.3 Pedido nasce onde?

Decisão:

- pedido administrativo/fiscal nasce preferencialmente no ERP;
- pedido operacional, requisição ou intenção de compra/venda pode nascer no AgroSaaS;
- por isso a regra oficial é `BIDIRECIONAL_CONTROLADO`.

### 6.4 Barter nasce onde?

Decisão:

- no AgroSaaS como contrato negocial agrícola especializado;
- o ERP recebe espelhos financeiros, fiscais e títulos;
- suporte do adapter é `PROVIDER_SPECIFIC`.

### 6.5 Estoque operacional e contábil serão separados?

Sim. Esta separação é obrigatória.

### 6.6 Baixa de estoque por aplicação agrícola deve ir para o ERP?

Sim, quando o cliente operar estoque administrativo integrado.

Regra:

- a baixa operacional nasce no AgroSaaS;
- o ERP recebe o reflexo administrativo/contábil, não a autoria operacional.

### 6.7 Contas a pagar originadas por compra agrícola nascem onde?

Decisão:

- a origem operacional pode nascer no AgroSaaS;
- o título administrativo oficial deve existir no ERP;
- política: `AGROSAAS_GERA_ERP_REFERENCIA`.

### 6.8 NFe emitida no ERP deve retornar ao AgroSaaS?

Sim.

Regra:

- a NFe oficial pertence ao ERP;
- ela deve retornar ao AgroSaaS como evidência fiscal e documental.

### 6.9 Centros de custo e resultado serão importados de onde?

Decisão:

- do ERP, como master administrativo;
- o AgroSaaS pode mapear essas dimensões para sua semântica analítica própria.

### 6.10 Rastreabilidade de exportação deve depender do ERP?

Não.

Regra:

- a rastreabilidade operacional e territorial pertence ao AgroSaaS;
- o ERP apenas complementa com documentos fiscais e administrativos.

### 6.11 O que é obrigatório para qualquer adapter ERP?

- configuração de provider e escopo;
- autenticação segura;
- health check;
- teste de conexão;
- jobs, logs e diagnóstico;
- `ExternalRecordAssociation`;
- políticas de sync por entidade;
- reconciliação manual;
- tratamento de paginação, retry e rate limit;
- normalização de payload;
- declaração explícita do que suporta e do que não suporta.

### 6.12 O que é específico de provider?

- protocolo técnico;
- autenticação;
- endpoints;
- paginação;
- eventos nativos;
- limites operacionais;
- objetos fiscais específicos;
- recursos proprietários, como barter nativo, exportação, CT-e, MDF-e ou workflows próprios.

## 7. Regras oficiais para adapters ERP

Todo adapter ERP deve declarar explicitamente:

- `provider`;
- `scope`;
- `environment`;
- `authentication_method`;
- `supported_entities`;
- `unsupported_entities`;
- `supported_directions_by_entity`;
- `required_fields_by_entity`;
- `external_id_strategy`;
- `composite_key_strategy`;
- `pagination_strategy`;
- `retry_policy`;
- `rate_limit_policy`;
- `supported_events`;
- `normalized_payload_contracts`;
- `health_check_contract`;
- `test_connection_contract`;
- `diagnosis_contract`;
- `logging_contract`;
- `staging_strategy`, quando existir;
- `manual_reconciliation_contract`.

Normas:

- nenhum adapter pode escrever diretamente em entidades oficiais sem passar pela política da matriz;
- nenhum adapter pode assumir que todas as entidades são bidirecionais;
- nenhum adapter pode promover provider-specific payload a contrato canônico;
- toda divergência entre provider e matriz deve ser explicitada como limitação ou extensão controlada.

## 8. Regras para múltiplos ERPs

### 8.1 Decisão v1.0

- um tenant pode operar sem ERP;
- um tenant pode ter um ERP principal por `TENANT`;
- um tenant pode ter ERP por `ESTABELECIMENTO`, quando o contexto administrativo/fiscal assim exigir;
- um mesmo tenant não deve, em v1.0, operar dois ERPs concorrentes para a mesma entidade e mesmo escopo sem uma camada formal de arbitragem;
- cenários de ERP financeiro separado de ERP fiscal ficam como evolução futura;
- a resolução de provider por escopo deve ser determinística e auditável.

### 8.2 Regra de resolução

Ordem oficial:

1. resolver `ESTABELECIMENTO`, quando existir vínculo administrativo;
2. se não existir escopo específico, herdar do `TENANT`;
3. nunca resolver a partir de `UNIDADE_PRODUTIVA` como escopo de credencial.

## 9. Sankhya como Provider Adapter de Referência

### 9.1 O que o Sankhya já cobre

- provider-specific config;
- autenticação Gateway-first com fallback legado;
- `SankhyaCanonicalAdapter`;
- `IntegrationCredential`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`;
- `ExternalRecordAssociation`;
- pessoas/parceiros;
- produtos;
- NFe;
- financeiro básico por títulos;
- logs, jobs, timeline, diagnóstico e health;
- governança de reconciliação manual.

### 9.2 O que o Sankhya ainda não cobre

- ciclo completo de pagamentos, recebimentos e baixas;
- estoque operacional x administrativo;
- contratos;
- comercialização;
- barter;
- CT-e;
- MDF-e;
- logística;
- documentos de exportação;
- suporte operacional maduro a centros, contas correntes, depósitos e naturezas como cadastros mestres dedicados.

### 9.3 O que é provider-specific no Sankhya

- autenticação Gateway Sankhya;
- nomenclaturas como `CODPARC`, `CODPROD`, `CODLOCAL`, `CODNAT`;
- estruturas de payload e staging específicas do provider;
- capacidades reais expostas pelo conector atual.

### 9.4 Gaps gerais de ERP versus gaps do Sankhya

Gaps gerais de arquitetura ERP:

- separação formal entre estoque operacional e contábil;
- separação formal entre financeiro operacional e administrativo;
- matriz de donos e conflitos;
- arbitragem para compartilhados;
- definição oficial de multi-ERP por escopo.

Gaps específicos do Sankhya:

- cobertura funcional parcial do adapter atual;
- evento desacoplado só para pessoas e produtos;
- UX do tenant ainda desalinhada ao Gateway-first;
- cobertura fiscal e comercial ainda restrita.

## 10. Normas finais

- nenhum provider adapter pode redefinir a propriedade oficial dos dados;
- comercialização agrícola, rastreabilidade operacional, custo operacional e rentabilidade permanecem no AgroSaaS;
- fiscal, financeiro administrativo e escrituração permanecem no ERP;
- compartilhados exigem `ExternalRecordAssociation`, política de conflito e regra explícita de direção;
- v1.0 deve priorizar escopos `TENANT` e `ESTABELECIMENTO`;
- `UnidadeProdutiva` nunca é escopo oficial de credencial ERP.

## 11. Resultado esperado desta arquitetura

Após esta norma:

- o AgroSaaS passa a ter uma matriz oficial agnóstica a provider para integração ERP;
- Sankhya passa a ser apenas o primeiro adapter real dessa arquitetura;
- futuros adapters como TOTVS, SAP, Omie, Senior ou integrações customizadas devem obedecer a esta matriz;
- decisões de dono, origem, direção, conflito e obrigatoriedade deixam de depender do provider específico.
