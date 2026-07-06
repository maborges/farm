# Domínio Estoque do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Estoque é a camada de controle físico e gerencial de insumos, produtos e lotes. Ele registra saldo, reserva, movimentação, rastreabilidade de lote e saída para consumo operacional.

## 2. Objetivo

- Controlar disponibilidade e movimentação de estoque.
- Garantir rastreabilidade por lote.
- Conectar consumo operacional com compras, frota, agricultura e pecuária.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Depósitos | Organizar locais físicos de armazenamento | `Deposito` | Compras, Frota, Operacional | IMPLEMENTADO |
| Saldo | Manter saldo atual por produto e depósito | `SaldoEstoque` | Requisições, reservas, consumo | IMPLEMENTADO |
| Lotes | Controlar validade e rastreio de lote | `LoteEstoque` | Compras, beneficiamento, produção | IMPLEMENTADO |
| Movimentação | Ledger append-only de entrada/saída | `EstoqueMovimento` | Financeiro, operacional, frota | IMPLEMENTADO |
| Requisições | Fluxo de solicitação interna | `RequisicaoMaterial`, `ItemRequisicao` | Operações, frota, unidades | IMPLEMENTADO |
| Reservas | Bloqueio de saldo futuro | `ReservaEstoque` | OS, safra, pedido de compra | IMPLEMENTADO |
| Implantação | Entrada inicial de saldo | `estoque_implantacao` | Saneamento e migração de dados | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `Deposito` | Local físico de armazenagem | Estoque | tenant, unidade produtiva | Estoque |
| `SaldoEstoque` | Quantidade atual por produto | Estoque | depósito, produto | Estoque |
| `LoteEstoque` | Lote rastreável de produto | Estoque | produto, depósito, laudo | Estoque |
| `RequisicaoMaterial` | Pedido interno de material | Estoque | unidade produtiva, usuário | Estoque |
| `ItemRequisicao` | Itens requisitados | Estoque | requisição, lote, depósito | Estoque |
| `ReservaEstoque` | Saldo reservado para uso futuro | Estoque | produto, depósito, referência | Estoque |
| `EstoqueMovimento` | Ledger físico oficial | Estoque | origem, operação, unidade | Estoque |

## 5. Fluxos

```text
Compra / entrada inicial
↓
Depósito
↓
Lote
↓
Saldo
↓
Reserva / requisição
↓
Movimento
```

## 6. Eventos

- `LoteEstoqueCriado`
- `EstoqueEntradaRegistrada`
- `EstoqueSaidaRegistrada`
- `EstoqueReservado`
- `RequisicaoAprovada`
- `RequisicaoEntregue`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Compras | Recebimento, lote do fornecedor | Alta | Origem de entrada |
| Financeiro | Valuation e custos | Alta | Apuração econômica |
| Operações | Consumo de insumos | Alta | Baixa de estoque |
| Frota | Peças, combustível e manutenção | Alta | Consumo operacional |
| Agrícola | Insumos, safra e operação | Alta | Aplicação de campo |
| Pecuária | Ração, medicamentos e materiais | Média | Consumo animal |

## 8. Regras de Negócio

1. Todo movimento deve pertencer a um tenant.
2. Estoque é ledger append-only, com correções por novo movimento.
3. Lote é a unidade de rastreio física.
4. Reserva não altera saldo físico disponível.
5. Consumo operacional deve referenciar uma origem quando possível.
6. O valor de estoque alimenta apuração, mas não substitui o financeiro.

## 9. Fronteiras

### Pertence

- Saldo;
- Lote;
- Movimentação;
- Reserva;
- Depósito;
- Requisição;
- Implantação.

### Não pertence

- Receita e despesa do caixa;
- Titularidade fundiária;
- Gestão de compras como processo negocial primário;
- Operação de campo como execução em si.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Depósitos e saldos | IMPLEMENTADO | Núcleo do domínio. |
| Lotes e validade | IMPLEMENTADO | Base da rastreabilidade física. |
| Movimentos | IMPLEMENTADO | Ledger oficial. |
| Requisições | IMPLEMENTADO | Fluxo operacional ativo. |
| Reservas | IMPLEMENTADO | Controle preventivo de disponibilidade. |
| Implantação assistida | IMPLEMENTADO | Saneamento e onboarding de estoque. |

