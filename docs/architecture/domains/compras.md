# Domínio Compras do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Compras organiza a aquisição de insumos, peças, materiais e serviços. Ele cobre a jornada da solicitação até o recebimento, incluindo cotação, pedido, entrega e devolução.

## 2. Objetivo

- Padronizar o processo de compra.
- Controlar fornecedor, cotação, pedido e recebimento.
- Integrar automaticamente com estoque, financeiro e frota.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Fornecedores | Cadastro e qualificação de parceiros | `Fornecedor` | Pessoas, financeiro | IMPLEMENTADO |
| Solicitação | Capturar necessidade interna | `SolicitacaoCompra` | Estoque, frota, unidade produtiva | IMPLEMENTADO |
| Cotação | Comparar propostas | `CotacaoCompra`, `CotacaoFornecedor` | Financeiro, suprimentos | IMPLEMENTADO |
| Pedido | Formalizar a compra | `PedidoCompra`, `ItemPedidoCompra` | Estoque, financeiro | IMPLEMENTADO |
| Recebimento | Registrar entrada física | `RecebimentoParcial`, `ItemRecebimento` | Estoque, financeiro | IMPLEMENTADO |
| Devolução | Registrar retorno ao fornecedor | `DevolucaoFornecedor`, `ItemDevolucao` | Estoque, financeiro | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `Fornecedor` | Cadastro de parceiro comercial | Compras | Pessoa, CNPJ/CPF | Compras |
| `SolicitacaoCompra` | Necessidade interna de compra | Compras | produto, depósito | Compras |
| `CotacaoCompra` | Comparativo de preço | Compras | solicitação, fornecedor | Compras |
| `PedidoCompra` | Pedido oficial emitido | Compras | solicitação, cotação, depósito | Compras |
| `ItemPedidoCompra` | Item do pedido | Compras | pedido, produto | Compras |
| `RecebimentoParcial` | Entrada parcial ou total | Compras | pedido, NF-e | Compras |
| `ItemRecebimento` | Item do recebimento | Compras | recebimento, pedido item, lote | Compras |
| `DevolucaoFornecedor` | Devolução de mercadoria | Compras | pedido, fornecedor | Compras |
| `ItemDevolucao` | Itens devolvidos | Compras | devolução, lote, estoque | Compras |

## 5. Fluxos

```text
Necessidade
↓
Solicitação
↓
Cotação
↓
Pedido
↓
Recebimento
↓
Estoque / Financeiro
```

## 6. Eventos

- `SolicitacaoCriada`
- `CotacaoRecebida`
- `PedidoEmitido`
- `RecebimentoRegistrado`
- `DevolucaoRegistrada`
- `FornecedorQualificado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Estoque | Entrada e lote | Alta | Disponibilidade e rastreio |
| Financeiro | Obrigações e liquidação | Alta | Contas a pagar |
| Frota | Peças e manutenção | Alta | Suprimento operacional |
| Agrícola | Insumos de safra | Média | Planejamento e execução |
| RH | Serviços terceirizados | Média | Mão de obra e empreitadas |

## 8. Regras de Negócio

1. Solicitação é a origem da necessidade.
2. Pedido é a formalização oficial da compra.
3. Recebimento pode ser parcial.
4. A devolução deve manter vínculo com o pedido ou fornecedor.
5. Compras não devem duplicar a fonte do estoque, apenas originá-lo.
6. Qualquer compra vinculada a operação deve preservar a origem documental.

## 9. Fronteiras

### Pertence

- Fornecedor;
- Solicitação;
- Cotação;
- Pedido;
- Recebimento;
- Devolução;
- Comparativo comercial.

### Não pertence

- Ledger de estoque;
- DRE e conciliação;
- Execução operacional;
- Cadastro territorial ou fundiário.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Solicitação e pedido | IMPLEMENTADO | Fluxo principal ativo. |
| Cotação | IMPLEMENTADO | Múltiplas respostas por fornecedor. |
| Recebimento | IMPLEMENTADO | Conecta com estoque. |
| Devolução | IMPLEMENTADO | Retorno controlado. |
| Fornecedor | IMPLEMENTADO | Base de cadastro consolidada. |

