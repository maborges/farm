# Domínio: Contratos Agrícolas Multicultura – Versão Endurecida (v2)

Este documento apresenta o modelo de domínio revisado e endurecido para contratos agrícolas multicultura, baseado no **BUSINESS‑DOMAIN‑06** original e nas análises de hardening.

---

## 1️⃣ Modelo Endurecido (Entidades Principais)

| Entidade | Continuidade | Alterações / Extensões | Comentários |
|----------|--------------|------------------------|------------|
| **CommodityContract** | ✅ Mantida | - Adição de `counterparty_id` (referência a `ContractCounterparty`).<br>- Campo `master_contract_id` opcional para hierarquias de contratos guarda‑chapéu.<br>- `tolerance_percent` padronizado (ex.: 5, 10, 15). | Suporta contrapartes múltiplas e contratos guarda‑chapéu. |
| **ContractDelivery** | ✅ Mantida | - Relacionamento explícito com `ContractDeliverySchedule`.
- Campo `delivery_status` (pending, completed, rejected, partial). | Controle de entregas programadas e status detalhado. |
| **ContractPosition** | ✅ Mantida | - Tornada uma **view** lógica derivada (não persistida), calculada a partir de `CommodityContract`, `ContractDelivery` e `ContractFixation`.
- Persistência opcional via `ContractPositionSnapshot` para auditoria. | Evita duplicação de estado, assegura consistência. |
| **ContractFixation** | ✅ Mantida | - Suporte a **fixação parcial** (`fixed_quantity`, `remaining_quantity`).
- Histórico de fixações (`ContractFixationHistory`). | Permite múltiplas fixações dentro do mesmo contrato. |
| **ContractQualityAdjustment** | ✅ Mantida | - Campo `adjustment_type` (premium / discount).<br>- Vinculação a `QualityResult` via `quality_result_id`. | Integração direta com módulo de qualidade. |
| **ContractSettlement** | ✅ Mantida | - Separação de `FinancialSettlement` (títulos financeiros) e `ContractSettlement` (lógica de contrato).
- Campo `settlement_status`. | Clarifica responsabilidades financeiras. |
| **ContractDocument** | ✅ Mantida | - Metadados de compliance (`compliance_type`, `issued_by`). | Suporte a auditoria regulatória. |
| **ContractCounterparty** *(Nova)* | ✅ Nova | - Representa qualquer entidade que participe do contrato (produtor, cooperativa, exportadora, trading, corretora, etc.).<br>- Campos: `party_type`, `role` (buyer/seller/agent), `tenant_id`.
- Relacionamento 1‑N com `CommodityContract`.
- Pode assumir múltiplos papéis em contratos diferentes. | Centraliza informações de contrapartes. |
| **MasterContract** *(Nova)* | ✅ Nova | - Representa contratos guarda‑chapéu que agregam **ChildContracts**.
- Campos: `name`, `validity_period`, `total_quantity`, `status`.
- Relacionamento 1‑N com `CommodityContract` (como child). | Facilita gestão de contratos de longo prazo. |
| **ContractDeliverySchedule** *(Nova)* | ✅ Nova | - Define cronograma de entregas (frequency, windows, quantities).<br>- Relacionamento 1‑N com `ContractDelivery`. | Gerencia entregas mensais, semanais, janelas. |
| **ContractTolerance** *(Nova)* | ✅ Nova | - Representa tolerâncias contratuais (`min_quantity`, `max_quantity`).
- Associada a `CommodityContract`. | Usa para validações de entrega e liquidação. |
| **ContractFixationPartial** *(Nova)* | ✅ Nova | - Modela fixações parciais de quantidades dentro de um contrato.
- Campos `fixation_id`, `quantity_fixed`, `remaining_quantity`, `price`. | Suporta cenários de preço fixado parcial. |

---

## 2️⃣ Principais Mudanças de Hardening

1. **Contraparte Unificada** – Introduz `ContractCounterparty` para evitar a proliferação de tipos de parte em diferentes módulos.
2. **Hierarquia de Contratos** – `MasterContract` permite agrupar contratos mensais/temporais sob um guarda‑chapéu, reduzindo duplicação de metadados.
3. **Posição Derivada** – `ContractPosition` deixou de ser persistida; sua fonte de verdade vem de entregas e fixações, eliminando risco de estado inconsistente.
4. **Fixação Parcial** – Nova entidade `ContractFixationPartial` permite múltiplas fixações dentro do mesmo contrato sem criar novos contratos.
5. **Tolerâncias Contractuais** – `ContractTolerance` parametriza `±%` e é usada nas validações de entrega e liquidação.
6. **Calendário de Entregas** – `ContractDeliverySchedule` centraliza regras de frequência e janelas, facilitando o controle de atrasos/antecipações.
7. **Separação de Financeiro** – `FinancialSettlement` isolado de `ContractSettlement` para evitar acoplamento com lógica de domínio.
8. **Auditoria e Compliance** – Metadados de compliance adicionados a documentos e ajustes de qualidade.

---

## 3️⃣ Riscos Mitigados

| Risco | Como o modelo endurecido mitiga |
|------|--------------------------------|
| Duplicação de estado (posição) | `ContractPosition` derivada, snapshots opcionais. |
| Saldo inconsistente | Cálculos centralizados via domínio services; tolerâncias explícitas. |
| Acoplamento excessivo | Separação clara entre contratos, finanças e qualidade. |
| Cálculo duplicado | Funções de serviço única (`ContractEngine`) que orquestram ajustes, entregas e fixações. |
| Falta de rastreabilidade | Históricos (`ContractFixationHistory`, `ContractDeliverySchedule`) e audit logs. |
| Multi‑papel de entidade | `ContractCounterparty` permite múltiplos papéis sem criar entidades distintas. |

---

## 4️⃣ Roadmap Revisado (Versões)

| Versão | Funcionalidades | Classificação |
|--------|----------------|---------------|
| **MVP** (Q4 2026) | Modelo base (entidades mantidas), `ContractCounterparty`, `ContractTolerance`, `ContractDeliverySchedule` básico. | **Básico** |
| **V2** (Q1 2027) | `MasterContract`, `ContractFixationPartial`, `ContractPositionSnapshot`, auditoria de qualidade. | **Profissional** |
| **V3** (Q3 2027) | CPR/Barter integrados (`CommodityPurchaseRight`, `BarterAgreement`), exportação (FOB/CIF) com domínio separado. | **Enterprise** |
| **V4** (Q4 2027) | Hedge e instrumentos financeiros avançados, integração completa com portal do parceiro e originação. | **Enterprise** |

---

## 5️⃣ Dependências Obrigatórias

- **Qualidade** – `QualityResult` e `CommercialQualityRule` para ajustes.
- **Estoque** – `LoteEstoque` para controle de quantidade entregue.
- **Financeiro** – `FinancialSettlement` para emissão de títulos.
- **Portal do Parceiro** – Exposição de contratos, saldo, entregas.

---

*Este documento serve como base para a próxima fase de implementação (BUSINESS‑DOMAIN‑07). Todas as alterações propostas são puramente de modelagem e documentação, sem impactos de código ou migrações.*
