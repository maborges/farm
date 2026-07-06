# Auditoria — BUSINESS-DOMAIN-09.2: Hedge MVP Boundary

> Data: 2026-06-14  
> Status: **CONCLUÍDA**  
> Regra: Somente inventário, análise e documentação. Nenhuma implementação.

---

## SEÇÃO 1 — Inventário completo com evidências

### Matriz de Status

| Funcionalidade | Status | Arquivo | Classe / Função | Endpoint | Migration | Observação |
|---|---|---|---|---|---|---|
| **HedgeRegistro** (model) | **EXISTE PARCIALMENTE** | `services/api/enterprise/models/sprints_27_33.py` L431 | `class HedgeRegistro(Base)` | — | Revertida (tabela removida do banco) | Campos existem; tabela não está ativa |
| **HedgeRegistro** (service) | **EXISTE PARCIALMENTE** | `services/api/enterprise/services/sprints_27_33_service.py` L247 | `HedgingService.registrar_hedge()` | — | — | Funcional, mas sem validação de negócio |
| **HedgeRegistro** (router/endpoint) | **EXISTE PARCIALMENTE** | `services/api/enterprise/routers/sprints_27_33_router.py` L223 | `def registrar_hedge(...)` | `POST /sprints27-33/hedging/registros` | — | Endpoint existe; depende de módulo `EXT_IA`; tabela inativa |
| **ContratoFuturo** (model) | **EXISTE PARCIALMENTE** | `services/api/enterprise/models/sprints_27_33.py` L399 | `class ContratoFuturo(Base)` | — | Revertida | Sem FK para `safra_id` ou `commodity_id` oficial |
| **ContratoFuturo** (endpoint) | **EXISTE PARCIALMENTE** | `services/api/enterprise/routers/sprints_27_33_router.py` L208 | `def criar_contrato_futuro(...)` | `POST /sprints27-33/hedging/contratos` | — | Sem vínculo com safra ou commodity cadastral |
| **Contratos** (gerais) | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Não há model/service de contrato agrícola geral fora da enterprise |
| **Comercialização** (model) | **EXISTE E ATENDE** | `services/api/financeiro/comercializacao/models.py` L20 | `class ComercializacaoCommodity(Base)` | — | Ativa | Possui `commodity_id`, `quantidade`, `status`, `produto_colhido_id` |
| **Comercialização** (service) | **EXISTE E ATENDE** | `services/api/financeiro/comercializacao/service.py` L25 | `class ComercializacaoService` | — | — | Funcional |
| **Estoque** (`SaldoEstoque`) | **EXISTE E ATENDE** | `services/api/operacional/models/estoque.py` L21 | `class SaldoEstoque(Base)` | — | Ativa | `quantidade_atual`, `quantidade_reservada`, FK para `produto_id` e `deposito_id` |
| **Estoque** (`EstoqueMovimento`) | **EXISTE E ATENDE** | `services/api/operacional/models/estoque.py` L115 | `class EstoqueMovimento(Base)` | — | Ativa | Ledger append-only; robusto |
| **Produção Estimada** | **EXISTE PARCIALMENTE** | `services/api/agricola/cultivos/models.py` L50 | `Cultivo.produtividade_meta_sc_ha` | — | Ativa | Campo `produtividade_meta_sc_ha` existe; área por `CultivoArea.area_ha`. Não há endpoint de consolidação por commodity/safra |
| **Safra** | **EXISTE E ATENDE** | `services/api/agricola/safras/models.py` L38 | `class Safra(Base)` + `SafraService` | Múltiplos | Ativa | Completa, com fases, talhões e histórico |
| **Qualidade** | **EXISTE E ATENDE** | `services/api/operacional/models/qualidade.py` | `QualidadeLaudo`, `QualidadeResultado`, `QualidadeAjuste` | Múltiplos | Ativa | Completo; não precisa ser consumido no MVP |
| **Originação** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Nenhuma classe `Originacao`, `RiskPolicy` ou similar encontrada |
| **CPR** (`CommodityPurchaseRight`) | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Sem model, schema, service ou router |
| **Barter** (`BarterAgreement`) | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Sem model, schema, service ou router |
| **RiskPolicy** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Sem model, schema ou referência direta em código |
| **CreditLimit** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Sem model ou service. Apenas documentação prévia |
| **HedgePosition** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Entidade a criar no MVP |
| **HedgeExposure** (cálculo) | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Lógica a implementar; dados-base já existem |
| **HedgeMarkToMarket** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Para V2 |
| **HedgeMarginCall** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Para V2 |
| **HedgePolicy** | **NÃO EXISTE NO CÓDIGO** | — | — | — | — | Para V3, extensão de `RiskPolicy` |

---

## SEÇÃO 2 — Revisão crítica do BUSINESS-DOMAIN-09.1

### 2.1 Confirmações

| Conclusão do 09.1 | Validada? | Evidência |
|---|---|---|
| `HedgePosition` como Aggregate Root | ✅ Confirmada | Não existe código equivalente; `HedgeRegistro` só captura evento |
| `HedgeRegistro` como evento/operação | ✅ Confirmada | `sprints_27_33.py` L431: armazena tipo, quantidade, preço, resultado |
| Ownership no domínio Enterprise/Hedge | ✅ Confirmada | Todo código hedge está em `enterprise/` |
| Estoque existe e atende | ✅ Confirmada | `SaldoEstoque`, `EstoqueMovimento` — robustos e com migration ativa |

### 2.2 Correções e Refinamentos

| Conclusão do 09.1 | Revisão |
|---|---|
| "Comercialização como possível hedge natural via barter" | ❌ Corrigido — `BarterAgreement` não existe no código. Comercialização existe, mas barter é entidade separada inexistente |
| Dependências de Originação e CPR no MVP | ❌ Corrigido — `RiskPolicy`, `CommodityPurchaseRight` e `Originacao` **não existem** no código. Nenhuma dependência real do MVP com esses domínios |
| "CPR como colateral para hedge" | ⚠️ Adiado — CPR não existe. Não é pré-requisito do MVP |

---

## SEÇÃO 3 — Hierarquia de Responsabilidades

### 3.1 Revisão da hierarquia proposta

A hierarquia proposta era:
```
RiskPolicy
   ↓
CreditLimit
   ↓
CreditExposure
```

**Reavaliação:**

| Entidade | Existe no código? | Domínio | Relação com Hedge |
|---|---|---|---|
| `RiskPolicy` | ❌ Não | Originação (futura) | Hedge **consulta** política de risco para definir % máximo de cobertura |
| `CreditLimit` | ❌ Não | Financeiro (futuro) | Hedge não depende de limite de crédito no MVP |
| `CreditExposure` | ❌ Não | Financeiro (futuro) | Exposição de crédito é diferente de exposição de preço de commodity |

**Conclusão:** A hierarquia `RiskPolicy → CreditLimit → CreditExposure` é válida para o domínio de **Crédito**, não para o domínio de **Hedge**. No contexto de Hedge, a hierarquia relevante é:

```
Safra (Agrícola)  +  SaldoEstoque (Operacional)  +  ComercializacaoCommodity (Financeiro)
                                    ↓
                          HedgePosition (Hedge)
                                    ↓
                          HedgeExposure (calculado)
```

---

## SEÇÃO 4 — Anti-Overengineering

| Entidade | Obrigatória MVP | V2 | V3 | Pode ser extensão? | Justificativa |
|---|---|---|---|---|---|
| `HedgeInstrument` | ❌ | ⚠️ | — | ✅ Sim — `ContratoFuturo.commodity` já é o instrumento | No MVP, `ContratoFuturo` já diferencia por `commodity` e `mercado` |
| `HedgePosition` | ✅ Obrigatória | — | — | ❌ Não — é nova | Aggregate Root sem equivalente no código atual |
| `HedgeExposure` | ✅ Obrigatória (como método/query) | — | — | ✅ Sim — pode ser método de `HedgePosition` | Cálculo simples com dados existentes |
| `HedgeMarkToMarket` | ❌ | ✅ | — | ✅ Pode ser método de `HedgePosition` | Depende de feed externo de preços |
| `HedgeMarginCall` | ❌ | ✅ | — | ✅ Pode ser evento de `HedgePosition` | Depende de MtM implementado |
| `HedgePolicy` | ❌ | — | ✅ | ✅ Extensão de `RiskPolicy` (inexistente) | Originação ainda não existe no código |

---

## SEÇÃO 5 — Eventos de Domínio Mínimos

| Evento | Produtor | Consumidor | Payload mínimo | Motivo |
|---|---|---|---|---|
| `HedgeOperationRegistered` | `HedgingService` | `HedgePosition` | `{tenant_id, contrato_futuro_id, tipo, quantidade, preco, data_operacao}` | Atualiza a posição consolidada ao registrar nova operação |
| `HedgePositionUpdated` | `HedgePosition` | Dashboard / Relatórios | `{hedge_position_id, exposicao_liquida, percentual_cobertura, updated_at}` | Notifica consumidores que a posição foi recalculada |
| `ExposureRecalculated` | `HedgeExposureService` | `HedgePosition` | `{safra_id, commodity_id, producao_estimada, ja_vendido, ja_hedgeado, exposicao_liquida}` | Recalcula a exposição quando safra, estoque ou vendas mudam |

> **Nota sobre implementação no MVP:** os eventos podem ser implementados como chamadas diretas (sem broker de mensagens) no MVP. A extração para eventos assíncronos (ex.: Redis Streams, Celery) fica para V2.

---

## SEÇÃO 6 — Integrações proibidas no MVP

As seguintes funcionalidades **NÃO devem ser implementadas** no MVP:

| Funcionalidade | Categoria | Motivo |
|---|---|---|
| Integração com corretoras (Rico, XP, BTG) | Infraestrutura externa | Alto custo, contrato específico |
| Feed de preços da B3 (live) | Infraestrutura externa | Requer subscrição paga |
| Feed CBOT / CME Group | Infraestrutura externa | USD, fuso, contrato específico |
| VaR (Value at Risk) | Análise quantitativa | Requer série histórica e modelo estatístico |
| CVaR (Conditional Value at Risk) | Análise quantitativa | Dependente de VaR |
| Simulação estocástica / Monte Carlo | Análise quantitativa | Alta complexidade |
| Derivativos complexos (opções) | Instrumento financeiro | Mercado de nicho; modelo de precificação distinto |
| NDF (Non-Deliverable Forward) | Instrumento financeiro | Cambial; fora do escopo agro MVP |
| Swaps de commodities | Instrumento financeiro | Alta complexidade contratual |
| Liquidação automática de futuros | Processo operacional | Dependente de integração com corretora |
| Netting multi-mercado | Posição | Dependente de multi-moeda |

---

## SEÇÃO 7 — Conclusão Objetiva

| Questão | Resposta |
|---|---|
| **Aggregate Root definitivo?** | `HedgePosition` |
| **`HedgeRegistro` permanece?** | Sim — como operação/evento materializado |
| **`HedgeRegistro` evolui para quê?** | Evento `HedgeOperationRegistered`; ganha FK opcional para `hedge_position_id` |
| **Entidades obrigatórias no MVP?** | `HedgePosition` (nova), `ContratoFuturo` (ajustado) + leitura de `SaldoEstoque`, `ComercializacaoCommodity`, `Cultivo` |
| **Entidades V2?** | `HedgeMarkToMarket`, `HedgeMarginCall`, `BarterAgreement` como hedge natural |
| **Entidades V3?** | `HedgePolicy` (extensão de `RiskPolicy`), `HedgeRiskMetric` |
| **Domínio pronto para implementação?** | ⚠️ **Não totalmente** — faltam pré-requisitos |
| **Pré-requisitos faltantes?** | 1) Reativar migration de `hedge_registros` e `contratos_futuros`; 2) Adicionar `safra_id` e `commodity_id` oficial em `ContratoFuturo`; 3) Criar model e migration de `HedgePosition`; 4) Criar endpoint de consolidação de exposição |

---

## SEÇÃO 8 — Pré-requisitos para início da implementação

| # | Pré-requisito | Responsável | Impacto se ausente |
|---|---|---|---|
| 1 | Reativar/recriar migration de `hedge_registros` | Hedge | Tabela inexistente — nada funciona |
| 2 | Reativar/recriar migration de `contratos_futuros` | Hedge | Sem instrumento para registrar |
| 3 | Adicionar `safra_id` (FK) em `ContratoFuturo` | Hedge | Sem contexto agrícola para cálculo de exposição |
| 4 | Adicionar `commodity_id` oficial em `ContratoFuturo` | Hedge | Sem ligação com commodities cadastrais |
| 5 | Criar `HedgePosition` (model + migration) | Hedge | Aggregate Root ausente |
| 6 | Criar `HedgeExposureService` (query de consolidação) | Hedge | Exposição não calculável |
| 7 | Mover módulo hedge de `require_module("EXT_IA")` para módulo próprio | Plataforma | Hedge não deve depender de módulo de IA |
