# Domínio Hedge do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Hedge trata proteção de preço e exposição física versus financeira. Ele modela o instrumento, a operação executada e o snapshot de risco.

## 2. Objetivo

- Proteger margem e receita futura.
- Medir exposição aberta por safra e commodity.
- Registrar eventos de hedge com rastreabilidade.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Instrumento | Representar contrato futuro | `ContratoFuturo` | safra, commodity | IMPLEMENTADO |
| Operação | Registrar operação executada | `HedgeRegistro` | contrato futuro | IMPLEMENTADO |
| MtM / Snapshot | Fotografar a posição | `HedgePositionSnapshot` | cotação, commodity | IMPLEMENTADO |
| Exposição | Calcular cobertura física × financeira | serviço de exposição | agrícola, comercialização | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `ContratoFuturo` | Instrumento de hedge | Hedge | safra, commodity | Hedge |
| `HedgeRegistro` | Operação materializada | Hedge | contrato futuro | Hedge |
| `HedgePositionSnapshot` | Posição diária mark-to-market | Hedge | contrato futuro, cotação | Hedge |

## 5. Fluxos

```text
Contrato futuro
↓
Operação de hedge
↓
Snapshot diário
↓
Exposição consolidada
↓
Gestão de risco
```

## 6. Eventos

- `ContratoHedgeCriado`
- `HedgeRegistrado`
- `SnapshotMtMGerado`
- `ExposicaoCalculada`
- `AlertaHedgeVencimento`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Financeiro | Resultado e proteção | Alta | Risco e margem |
| Agrícola | Safra e commodity | Alta | Exposição física |
| Comercialização | Venda e preço | Alta | Cobertura de preço |
| Cotação / mercado | Preço de referência | Alta | MTM |

## 8. Regras de Negócio

1. Hedge é derivado financeiro e não altera a produção física.
2. Snapshot deve ser calculado a partir de cotação válida.
3. Contrato sem commodity ou preço não deve ser considerado válido no cálculo.
4. A exposição é calculada, não armazenada como posição persistente no MVP.
5. Hedge deve ser rastreável por safra e commodity.

## 9. Fronteiras

### Pertence

- Contratos futuros;
- Operações de hedge;
- Snapshots MTM;
- Exposição calculada;
- Alerta de vencimento.

### Não pertence

- Produção física;
- Estoque;
- Titularidade fundiária;
- Contabilização geral da empresa.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Contrato futuro | IMPLEMENTADO | Instrumento oficial existente. |
| Registros de hedge | IMPLEMENTADO | Operação materializada. |
| Snapshot diário | IMPLEMENTADO | MTM e auditoria. |
| Exposição consolidada | IMPLEMENTADO | Visão por safra e commodity. |

