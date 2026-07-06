# Domínio Financeiro do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Financeiro é a camada econômica oficial do AgroSaaS. Ele registra receitas, despesas, lançamentos, conciliações, plano de contas, relatórios, custeio, comercialização e proteção de preço.

Esse domínio é a fonte da verdade do resultado econômico. Ele não executa operação de campo e não substitui o domínio operacional ou agrícola.

## 2. Objetivo

- Registrar a realidade financeira do tenant.
- Consolidar contas a pagar, a receber, fluxo de caixa e DRE.
- Apurar custo e resultado com rastreabilidade.
- Integrar comercialização, hedge e conciliação.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Contas a Pagar e Receber | Controlar obrigações e recebimentos | `Despesa`, `Receita` | Compras, Comercialização, Bancos | IMPLEMENTADO |
| Plano de Contas | Organizar a classificação econômica | `PlanoConta` | DRE, relatórios, rateios | IMPLEMENTADO |
| Lançamentos e Rateios | Registrar evento contábil/gerencial | `LancamentoFinanceiro`, `Rateio` | Operacional, agrícola, estoque | IMPLEMENTADO |
| Conciliação | Reconciliar banco e lançamentos | `Conciliacao` | Extrato, ERP, bancos | IMPLEMENTADO |
| Relatórios e DRE | Apurar resultado e fluxo | `relatórios`, `DRE` | Gestão e auditoria | IMPLEMENTADO |
| Comercialização | Controlar venda de commodities | `ComercializacaoCommodity` | Agrícola, rastreabilidade | IMPLEMENTADO |
| Hedge | Proteger preço e medir exposição | `ContratoFuturo`, `HedgeRegistro`, `HedgePositionSnapshot` | Agricultura, commodities | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `Receita` | Lançamento de contas a receber | Financeiro | cliente, plano de conta, origem | Financeiro |
| `Despesa` | Lançamento de contas a pagar | Financeiro | fornecedor, cultivo, plano de conta | Financeiro |
| `LancamentoFinanceiro` | Ledger financeiro central | Financeiro | receitas, despesas, conciliação | Financeiro |
| `PlanoConta` | Classificação econômica | Financeiro | lançamentos, relatórios | Financeiro |
| `Rateio` | Distribuição de valores | Financeiro | despesas, custos, unidades | Financeiro |
| `Conciliacao` | Match bancário | Financeiro | extrato, lançamentos | Financeiro |
| `ComercializacaoCommodity` | Venda de commodity e nota de saída | Financeiro | produto colhido, receita | Financeiro |
| `ContratoFuturo` | Instrumento de hedge | Financeiro | safra, commodity | Financeiro |
| `HedgeRegistro` | Operação executada de hedge | Financeiro | contrato futuro | Financeiro |
| `HedgePositionSnapshot` | Foto do MTM | Financeiro | contrato futuro, cotação | Financeiro |

## 5. Fluxos

```text
Compra / Venda / Lançamento
↓
Plano de contas
↓
Rateio / conciliação
↓
DRE / fluxo de caixa
↓
Benchmark econômico
```

## 6. Eventos

- `ReceitaLancada`
- `DespesaLancada`
- `LancamentoConciliado`
- `DRECalculada`
- `ComercializacaoConfirmada`
- `HedgeRegistrado`
- `HedgeSnapshotGerado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Agrícola | Custos, produção, rentabilidade | Alta | Origem da apuração econômica |
| Estoque | Movimentações e custo de inventário | Alta | Valuation e consumo |
| Compras | Pedido, recebimento, fornecedor | Alta | Origem de despesa |
| Frota | Abastecimento, OS e manutenção | Alta | Custo operacional |
| RH | Folha, diárias, empreitadas | Alta | Mão de obra e encargos |
| Comercialização | Faturamento e receita | Alta | Receita reconhecida |
| Hedge | Proteção de preço | Alta | Exposição e cobertura |
| Bancos | Extratos e conciliação | Alta | Fonte de liquidez |

## 8. Regras de Negócio

1. Toda despesa deve pertencer ao tenant.
2. Toda receita deve possuir origem econômica.
3. Lançamentos econômicos não devem duplicar a operação.
4. A DRE deve ser derivada de fontes econômicas oficiais.
5. Hedge é instrumento financeiro e não altera produção física.
6. Comercialização financeira deve guardar rastreabilidade do produto colhido.
7. O plano de contas é a taxonomia financeira oficial.

## 9. Fronteiras

### Pertence

- Receita;
- Despesa;
- Lançamentos;
- Rateios;
- Conciliação;
- DRE;
- Comercialização;
- Hedge;
- Fluxo de caixa.

### Não pertence

- Execução de campo;
- Cadastro territorial;
- Titularidade rural;
- RH de segurança e jornada;
- Estoque físico como fonte primária de produção.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Receita e despesa | IMPLEMENTADO | Núcleo econômico ativo. |
| Plano de contas | IMPLEMENTADO | Taxonomia consolidada. |
| Conciliação | IMPLEMENTADO | Camada bancária e ledger. |
| DRE | IMPLEMENTADO | Já alimenta relatórios e analytics. |
| Comercialização | IMPLEMENTADO | Fecha o ciclo da produção. |
| Hedge | IMPLEMENTADO | Módulo próprio e ativo. |
| Livro caixa / relatórios avançados | IMPLEMENTADO | Cobertura ampla no backend e frontend. |

