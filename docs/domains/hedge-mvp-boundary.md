# Hedge MVP Boundary — BUSINESS-DOMAIN-09.2

> Versão: 1.0 | Data: 2026-06-14  
> Status: **APROVADO PARA REFERÊNCIA ARQUITETURAL**  
> Escopo: Somente análise, inventário, ownership e fronteiras do MVP. Nenhuma implementação.

---

## 1. Aggregate Root definitivo

**`HedgePosition`** é o Aggregate Root do domínio Hedge.

Justificativa:
- `HedgeRegistro` (existente) captura apenas uma operação pontual — um evento bruto.
- A posição de hedge é o estado acumulado (quantidade líquida, exposição, preço médio) resultante de N operações.
- Toda lógica de negócio (cálculo de cobertura, % protegido, resultado papel/físico) pertence à posição, não ao registro individual.
- `HedgePosition` pode existir sem `ContratoFuturo` (ex.: barter como hedge natural), mas `HedgeRegistro` sempre depende de um vínculo com `ContratoFuturo`.

---

## 2. O que é `HedgeRegistro` e o que ele se tornará

| Atributo | Situação atual | Situação MVP |
|---|---|---|
| Tipo | Entidade persistida (model) | Permanece como entidade, mas com papel de **domain event** materializado |
| Aggregate Root? | ❌ Não deveria ser | ❌ Não será |
| Vínculo | `contratos_futuros.id` (FK obrigatória) | Mantém FK com `ContratoFuturo`, adiciona FK opcional com `HedgePosition` |
| Campos essenciais | tipo, quantidade, preço, data_operacao, base, resultado_papel, resultado_físico | Mantidos |
| Lacuna atual | Sem vínculo com posição consolidada | MVP adiciona `hedge_position_id` |

---

## 3. Fronteiras do MVP

### ✅ O QUE ENTRA NO MVP

| Entidade / Funcionalidade | Motivo |
|---|---|
| `ContratoFuturo` (já existe) | Representa o instrumento de hedge (futuro) |
| `HedgeRegistro` (já existe, ajustar) | Operação de registro com vínculo à posição |
| `HedgePosition` (nova) | Aggregate Root — consolida operações e calcula cobertura |
| `Safra.producao_meta_sc_ha × CultivoArea.area_ha` (já existe) | Produção estimada — base do cálculo de exposição |
| `SaldoEstoque` (já existe) | Estoque físico disponível — compõe a exposição |
| `ComercializacaoCommodity` (já existe) | Vendas confirmadas — reduzem a exposição líquida |
| Cálculo de exposição líquida (novo, simples) | `exposicao = producao_estimada - estoque_vendido - hedge_coberto` |
| Endpoint `GET /hedge/posicoes` (novo) | Leitura somente — lista posições por tenant/commodity/safra |
| Endpoint `GET /hedge/posicoes/{id}/exposicao` (novo) | Retorna exposição calculada no momento da consulta |

### ⏳ O QUE FICA PARA V2

| Entidade / Funcionalidade | Motivo do adiamento |
|---|---|
| `HedgeMarkToMarket` | Requer integração com feed de preços externos (B3, CBOT) |
| `HedgeMarginCall` | Depende de MtM implementado |
| Atualização periódica automática de exposição | Requer job scheduler (Celery ou similar) |
| Barter como hedge natural | Depende da implementação de `BarterAgreement` em Comercialização |
| CPR como colateral | Depende da implementação de `CommodityPurchaseRight` |

### 🔮 O QUE FICA PARA V3

| Entidade / Funcionalidade | Motivo do adiamento |
|---|---|
| `HedgePolicy` / Regras de aprovação | Depende de `RiskPolicy` implementado em Originação |
| `HedgeRiskMetric` (VaR, CVaR, beta) | Alta complexidade estatística sem retorno claro no MVP |
| Multi-mercado (B3 + CBOT simultâneo) | Requer normalização de moeda e basis por mercado |

### 🚫 O QUE FICA PARA V4 OU FORA DO ESCOPO

| Funcionalidade | Decisão |
|---|---|
| Integração direta com corretoras | Fora do escopo — cada corretora tem API própria e custos elevados |
| Integração com bolsa (B3 feed live) | Fora do escopo — requer contrato específico |
| Derivativos complexos (opções, NDF, swaps) | Fora do escopo — mercado de nicho no agro brasileiro |
| Simulação estocástica / Monte Carlo | Fora do escopo — ferramenta de gestora, não de produtor |

---

## 4. Por que o MVP pode operar SEM estas dependências

| Dependência | Necessária no MVP? | Justificativa |
|---|---|---|
| CPR Física | ❌ Não | O MVP calcula exposição apenas com produção estimada + estoque + vendas |
| CPR Financeira | ❌ Não | Idem — não afeta o cálculo de cobertura básico |
| Barter | ❌ Não | Pode ser modelado como venda comum (`ComercializacaoCommodity`) no MVP |
| Margin Call | ❌ Não | Requer MtM — que já foi adiado para V2 |
| MtM avançado | ❌ Não | Exposição básica não requer mark-to-market |

---

## 5. Fórmula de exposição do MVP (sem complexidade)

```
exposicao_bruta      = produtividade_meta_sc_ha × area_ha_total_cultivo
ja_vendido           = SUM(ComercializacaoCommodity.quantidade WHERE status IN ['CONFIRMADO','ENTREGUE','FINALIZADO'])
ja_hedgeado          = SUM(ContratoFuturo.quantidade WHERE status = 'aberto')
exposicao_liquida    = exposicao_bruta - ja_vendido - ja_hedgeado
percentual_cobertura = (ja_hedgeado / exposicao_bruta) × 100
```

Todos os dados necessários já existem no código. O MVP é apenas uma **query de consolidação**.

---

## 6. Integrações proibidas no MVP

As seguintes funcionalidades **NÃO devem ser implementadas** no MVP:

- Integração com corretoras externas (Rico, XP, BTG Agro)
- Integração com API de bolsa (B3 Market Data, CME Group, CBOT)
- VaR (Value at Risk)
- CVaR (Conditional Value at Risk)
- Simulação estocástica
- Derivativos complexos (opções, swaps, NDF)
- Precificação de opções (Black-Scholes ou similares)
- Motor de margem (margin engine)
- Liquidação automática de contratos futuros
- Netting de posições inter-mercados

---

## 7. Pré-requisitos antes da implementação

| Pré-requisito | Status | Domínio responsável |
|---|---|---|
| `ContratoFuturo` com FK para `safra_id` | ⚠️ Ausente | Hedge / Agricola |
| `ContratoFuturo` com FK para `commodity_id` | ⚠️ Ausente | Hedge |
| `Cultivo.producao_meta_sc_ha` e `CultivoArea.area_ha` existem | ✅ Existe | Agrícola |
| `SaldoEstoque` existe | ✅ Existe | Operacional |
| `ComercializacaoCommodity` existe com `commodity_id` e `status` | ✅ Existe | Financeiro |
| `HedgeRegistro` migração ativa | ⚠️ Migração revertida | Hedge |
| Tenant isolation em todos os modelos de hedge | ⚠️ `HedgeRegistro` tem `tenant_id`; `ContratoFuturo` também | Hedge |

---

## 8. Ownership definitivo (MVP)

| Entidade | Domínio dono | Justificativa |
|---|---|---|
| `ContratoFuturo` | **Hedge** (dentro de Enterprise) | Instrumento específico de hedge |
| `HedgeRegistro` | **Hedge** (dentro de Enterprise) | Operação de registro de hedge |
| `HedgePosition` | **Hedge** (dentro de Enterprise) | Aggregate Root — consolida operações |
| `ComercializacaoCommodity` | **Financeiro** | Já existe; Hedge só lê |
| `SaldoEstoque` | **Operacional** | Já existe; Hedge só lê |
| `Cultivo` (producao_meta) | **Agrícola** | Já existe; Hedge só lê |
| `RiskPolicy` | **Originação** | A implementar — para V3 |
| `BarterAgreement` | **Comercialização** | A implementar — para V2 |
| `CommodityPurchaseRight` | **Contratos / Financeiro** | A implementar — para V2 |
