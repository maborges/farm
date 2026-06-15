# Auditoria – BUSINESS‑DOMAIN‑09.1 — Hedge Hardening & Ownership

## 1️⃣ Inventário completo do **HedgeRegistro**

| Arquivo | Tipo | Responsabilidade | Reutilizável? |
|---|---|---|---|
| `services/api/enterprise/models/sprints_27_33.py` (classe `HedgeRegistro`) | Model | Representa o registro de uma operação de hedge no banco de dados. | ✅ (pode ser reutilizado como entidade base para outras operações de hedge) |
| `services/api/enterprise/services/sprints_27_33_service.py` (método `registrar_hedge`) | Service | Orquestra a criação de um `HedgeRegistro` a partir dos parâmetros de entrada (tenant, contrato, tipo, quantidade, preço, data). | ✅ (lógica de registro pode ser reaproveitada por outros fluxos de criação) |
| `services/api/enterprise/routers/sprints_27_33_router.py` (endpoint `def registrar_hedge`) | Router | Exponibiliza a API HTTP `POST /hedge` (ou similar) que delega ao service acima. | ✅ (ponto de entrada pode ser mantido ou adaptado) |
| `services/api/migrations/versions/fase3_sprints27_33_final.py` (criação da tabela `hedge_registros` e índice) | Migration | Estrutura a tabela física no banco de dados. | ❌ (migração já foi revertida; a tabela foi removida) |
| `services/api/migrations/versions/c55e2c636a9b_performance_indexes.py` (referência a `hedge_registros` nos índices de performance) | Migration (index) | Planeja índices de performance para a tabela (`hedge_registros`). | ❌ (tabela inexistente atualmente). |
| **Testes** | — | Não há arquivos de teste que cubram `HedgeRegistro` ou o endpoint `registrar_hedge`. | ❌ |
| **Frontend** | — | Nenhum componente, página ou hook que consuma ou exiba `HedgeRegistro`. | ❌ |
| **Documentação** | — | Apenas menção ao registro em `docs/domains/hedge-domain.md` (avisa que há um protótipo). | ❌ |

> **Observação:** O código está presente tanto em `services/api/enterprise` quanto em `apps/web/services/api/enterprise` (duplicado). Essa duplicação indica um histórico de migração de código que ainda não foi consolidado.

---

## 2️⃣ Análise de Ownership – Qual deve ser o Aggregate Root?

| Pergunta | Resposta |
|---|---|
| **HedgeRegistro representa operação?** | Sim. Ele captura os dados de uma operação de registro de hedge (tipo, quantidade, preço, data). |
| **Representa posição?** | Não diretamente. Uma posição seria o agregado de várias operações ao longo do tempo. |
| **Representa instrumento?** | Não. O instrumento (futuro, opção, trava, barter…) seria um atributo, mas não o foco da entidade. |
| **É um evento?** | Parcialmente. Funciona como um evento persistido de que um hedge foi registrado, porém falta a semântica de evento de domínio (ex.: `HedgeOperationRegistered`). |
| **É um lançamento?** | Não. Não há conceito de “lançamento contábil” aqui. |

### Escolha do Aggregate Root
- **HedgeRegistro** – Muito próximo de um *Event* de domínio, mas carece de comportamento rico (cálculo de exposição, validações, atualização de MtM). Não deveria ser o root porque representa apenas um registro bruto.
- **HedgePosition** – Agrega múltiplas operações (incluindo HedgeRegistro) e contém o estado da posição (quantidade, preço médio, exposição). É o candidato natural para ser o *Aggregate Root*.
- **HedgeContract** – Seria um contrato futuro ou swap; não cobre a totalidade do domínio hedge (ex.: barter, CPR). 
- **HedgeOperation** – Poderia ser um root se o foco fosse histórico de eventos, mas ainda assim precisaria de um objeto “Position” para cálculo de exposição.

**Conclusão:** **`HedgePosition`** deve ser o Aggregate Root definitivo. `HedgeRegistro` pode ser convertido em um *Domain Event* (`HedgeOperationRegistered`) que altera o estado da `HedgePosition`.

---

## 3️⃣ Anti‑Duplicação – Necessidade das entidades propostas

| Entidade | Necessária? | Pode ser extensão? | Dono (domínio) |
|---|---|---|---|
| **HedgeInstrument** | ✅ – Necessária para descrever futuros, opções, swaps, NDF, travas, barter e CPR. | – | Financeiro (derivativos) / Comercialização (barter) |
| **HedgePosition** | ✅ – Aggregate Root que agrega múltiplas operações e calcula exposição. | – | Financeiro |
| **HedgeExposure** | ✅ – Cálculo consolidado da exposição (física, financeira, cambial, basis). Pode ser implementado como método da `HedgePosition`. | Pode ser incorporado na própria `HedgePosition` como sub‑entidade. | Financeiro |
| **HedgeMarkToMarket** | ✅ – Necessária para atualizar o valor de mercado das posições. Pode ser um serviço separado ou método da `HedgePosition`. | Pode ser método da `HedgePosition`. | Financeiro |
| **HedgeMarginCall** | ✅ – Necessária para gerenciar garantias quando a exposição excede limites. | Pode ser evento associado à `HedgePosition`. | Financeiro |
| **HedgePolicy** | ✅ – Define limites e regras de aprovação (origem). | Pode ser extensão de `RiskPolicy` já existente em Originação. | Originação |

---

## 4️⃣ Integração com domínios existentes

| Domínio | System of Record (SOR) | Quem consome? | Quem publica eventos? |
|---|---|---|---|
| **Contratos** | `services/api/contrato/models/contrato.py` (registro de contrato) | `HedgePosition` (para validar vínculo contrato‑hedge) | Evento `ContractCreated/Updated` publicado por Contratos. |
| **Comercialização** | `services/api/comercializacao/models/...` (vendas, barter) | `HedgePosition` (para usar barter como hedge natural) | Evento `BarterAgreementCreated`, `SaleCreated`. |
| **Financeiro** | `services/api/financeiro/models/...` (contas, limites, câmbio) | `HedgePosition` (cálculo de exposição, margem) | Evento `CreditLimitChanged`, `ExchangeRateUpdated`. |
| **Estoque** | `services/api/estoque/models/commodity.py` | `HedgePosition` (para exposição física e garantias) | Evento `StockAdjusted`, `CommodityAdded`. |
| **Qualidade** | `services/api/qualidade/models/...` | `HedgeRiskMetric` (ajuste de preço por qualidade) | Evento `QualityAssessmentCompleted`. |
| **Originação** | `services/api/origination/models/risk_policy.py` | `HedgePolicy` (definição de limites) | Evento `RiskPolicyUpdated`. |
| **CPR** | `services/api/cpr/models/...` | `HedgePosition` (garantia/colateral) | Evento `CprIssued`, `CprSettled`. |
| **Barter** | `services/api/barter/models/...` | `HedgePosition` (hedge natural) | Evento `BarterAgreementCreated`. |

---

## 5️⃣ MVP Real – Redefinição usando o que já existe

### O que já existe
- **Entidade `HedgeRegistro`** (registro bruto de operação).  
- **Endpoint `POST /registrar_hedge`** que persiste o registro.  
- **Migração** (removida) que já criou a tabela `hedge_registros` (pode ser re‑ativada).  

### O que precisa ser criado **mínimo**
1. **`HedgePosition`** – novo agregado que mantém a lista de `HedgeOperation` (ou `HedgeRegistro` convertido).  
2. **Evento `HedgeOperationRegistered`** – publicado pelo service ao registrar um hedge; atualiza a `HedgePosition`.  
3. **Serviço de cálculo de exposição** (`HedgeExposureService`) – método simples que soma estoque + contratos futuros + registros de hedge.  
4. **Dashboard resumido** (frontend) – somente leitura (ex.: lista de posições e exposição).  
5. **Testes unitários** para o fluxo de registro → atualização de posição.

### O que **não** será criado no MVP (evitando over‑engineering)
- Modelos complexos de derivativos (opções, swaps, NDF).  
- Mecanismo avançado de MtM, VaR ou cenários.  
- Integrações com corretoras ou APIs externas de bolsa.  
- UI de gerenciamento de políticas – reutilizar `RiskPolicy` existente.

---

## 6️⃣ Conclusão

| Pergunta | Resposta |
|---|---|
| **HedgeRegistro deve ser mantido?** | Sim, pode ser mantido **como evento** (`HedgeOperationRegistered`). Não como Aggregate Root. |
| **Deve ser evoluído?** | Sim – renomear/transformar em evento, adicionar payload suficiente (instrumento, quantidade, preço, data). |
| **Deve ser substituído?** | Não totalmente; será substituído como *entity* principal por `HedgePosition`. |
| **Aggregate Root definitivo** | **`HedgePosition`** (agrega múltiplas operações e mantém o estado da exposição). |
| **Entidades obrigatórias** | `HedgeInstrument`, `HedgePosition`, `HedgeExposure` (pode ser método da Position), `HedgeMarginCall`, `HedgePolicy` (extensão de `RiskPolicy`). |
| **Entidades que podem esperar** | `HedgeMarkToMarket` (pode ser adicionado como cálculo periódico em V2), `HedgeRiskMetric` (VaR, CVaR) para V3/V4. |

---

*Documento elaborado em conformidade com as diretrizes de auditoria e linguagem (pt‑BR).*
