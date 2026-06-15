# Auditoria – BUSINESS‑DOMAIN‑06.1 – Hardening de Contratos Agrícolas Multicultura

## PARTE 1 — Revisão Crítica do Modelo Atual

| Entidade | Continuidade? | Alteração Necessária? | Dividir? | Remover? | Comentários |
|----------|---------------|-----------------------|----------|----------|------------|
| **CommodityContract** | ✅ Sim | ➡️ Adicionar `counterparty_id`, `master_contract_id`, `tolerance_percent`. | ❌ Não | ❌ Não | Suporta contrapartes e hierarquia de contratos. |
| **ContractDelivery** | ✅ Sim | ➡️ Relacionar a `ContractDeliverySchedule`, novo campo `delivery_status`. | ❌ Não | ❌ Não | Necessário para controle de status e cronograma. |
| **ContractPosition** | ✅ Sim | ➡️ Tornar **view** derivada; persistir opcionalmente via `ContractPositionSnapshot`. | ❌ Não | ❌ Não | Elimina duplicação de estado. |
| **ContractFixation** | ✅ Sim | ➡️ Suporte a fixação parcial (`fixed_quantity`, `remaining_quantity`). | ❌ Não | ❌ Não | Permite múltiplas fixações dentro do mesmo contrato. |
| **ContractQualityAdjustment** | ✅ Sim | ➡️ Campo `adjustment_type`, vínculo a `QualityResult`. | ❌ Não | ❌ Não | Integração direta com módulo de qualidade. |
| **ContractSettlement** | ✅ Sim | ➡️ Separar de `FinancialSettlement`; adicionar `settlement_status`. | ❌ Não | ❌ Não | Clarifica responsabilidade financeira. |
| **ContractDocument** | ✅ Sim | ➡️ Metadados de compliance (`compliance_type`, `issued_by`). | ❌ Não | ❌ Não | Facilita auditoria regulatória. |

### Riscos Identificados no Modelo Atual
- **Duplicação de estado** – `ContractPosition` persiste estado que pode divergir de entregas/fixações.
- **Saldo inconsistente** – Falta de tolerâncias explícitas pode gerar divergência entre quantidade contratada e entregue.
- **Acoplamento excessivo** – `ContractSettlement` mistura lógica de contrato e geração de títulos financeiros.
- **Cálculo duplicado** – Ajustes de qualidade e preço são calculados em múltiplos serviços.

## PARTE 2 — Contrapartes

**Entidade nova:** `ContractCounterparty`
- **Papéis:** buyer, seller, agent, broker, trading, exporter, processor.
- **Responsabilidades:** manter identificação única, dados de contato, tipo (jurídico/natural), `tenant_id`.
- **Relacionamentos:** 1‑N com `CommodityContract` (um contrato pode ter duas contrapartes). Uma mesma entidade pode atuar como buyer em um contrato e seller em outro – permitido via múltiplas linhas na tabela.

## PARTE 3 — Contratos Guarda‑Chuva

- **Entidades:** `MasterContract` (guarda‑chapéu) e `CommodityContract` como `ChildContract`.
- **Quando usar:**
  - Contratos de longo prazo com entregas mensais/trimestrais.
  - Agrupamento de vários contratos de mesma commodity/cliente.
- **Quando NÃO usar:**
  - Contratos pontuais ou de única entrega.
- **Como evitar duplicidade:**
  - Metadados (preço, tolerância) centralizados no `MasterContract`.
  - `ChildContract` contém apenas referências ao `master_contract_id`.

## PARTE 4 — Fixação Parcial

- **Cenário:** 1 000 sacas total, 300 sacas fixas a US$ 0,12/kg, 200 sacas fixas a US$ 0,13/kg, 500 sacas abertas.
- **Regras:** Cada fixação tem `fixed_quantity` e `price`; restante permanece sujeito a preço spot.
- **Cálculo:** Valor total = Σ(fixed_quantity × price) + (remaining_quantity × price_spot).
- **Auditoria:** `ContractFixationHistory` registra alterações de preço/quantidade.
- **Persistência:** Não é necessário persistir a posição; pode‑se derivar a partir das fixações.
- **Justificativa:** Reduz complexidade e evita estado redundante.

## PARTE 5 — Tolerâncias Contratuais

- **Entidade:** `ContractTolerance` com `min_quantity` e `max_quantity` (calculados a partir de `tolerance_percent`).
- **Exemplo:** 1 000 sacas → min 950, max 1 050.
- **Impactos:**
  - **Entregas:** Aceitas dentro da faixa; fora geram penalidades.
  - **Liquidação:** Quantidade entregue ajustada ao limite se exceder.
  - **Saldo Contratual:** Mantido dentro da faixa, evitando over‑delivery.
  - **Multas/Penalidades:** Configuráveis por contrato (ex.: % do preço base). 

## PARTE 6 — Calendário de Entregas

- **Entidade:** `ContractDeliverySchedule` (frequency, windows, expected_quantity).
- **Exemplo:** Jan 200, Feb 300, Mar 500.
- **Atrasos:** Marca entrega como `late` e gera evento `DeliveryDelay` para alertas.
- **Antecipações:** Marca como `early`; pode gerar desconto ou bônus, conforme regra de contrato.

## PARTE 7 — CPR e Barter

- **Entidades Necessárias:** `CommodityPurchaseRight` (para CPR) e `BarterAgreement` (para barter).
- **Entidades NÃO Necessárias:** Não há necessidade de criar novos tipos de `CommodityContract`; CPR/Barter são extensões que referenciam o contrato base.
- **Isolamento:** CPR/Barter ficam em módulos específicos; os contratos simples permanecem limpos.

## PARTE 8 — Exportação

- **Requisitos:** Incoterms (FOB, CIF), taxa de câmbio, documentos de exportação.
- **Modelagem:** Cria‑se um domínio **ExportContract** ligado a `CommodityContract` via `export_contract_id`.
- **Decisão:** O contrato base **não** precisa conhecer detalhes de exportação; a relação 1‑1 permite extensão sem poluir o modelo principal.

## PARTE 9 — Posições e Saldos

- **Recomendação:** `ContractPosition` como **view** derivada (não persistida). Caso haja necessidade de auditoria histórica, usar `ContractPositionSnapshot` (tabela de auditoria).
- **Benefícios:**
  - **Performance:** Cálculos em tempo real são leves; snapshots opcionais para relatórios.
  - **Consistência:** Sempre reflete o estado atual de entregas, fixações e ajustes.
  - **Manutenção:** Reduz complexidade de sincronização de estados.

## PARTE 10 — Roadmap Revisado

| Versão | Funcionalidades | Classificação |
|--------|----------------|---------------|
| **MVP** (Q4 2026) | Entidades base, `ContractCounterparty`, `ContractTolerance`, `ContractDeliverySchedule` simples. | **Básico** |
| **V2** (Q1 2027) | `MasterContract`, `ContractFixationPartial`, `ContractPositionSnapshot`, auditoria de qualidade. | **Profissional** |
| **V3** (Q3 2027) | Integração completa de CPR, Barter, módulo ExportContract, documentos de compliance. | **Enterprise** |
| **V4** (Q4 2027) | Hedge, instrumentos financeiros avançados, integração com portal do parceiro e origem de contratos. | **Enterprise** |

## PARTE 11 — Riscos Arquiteturais

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|----------------|----------|
| **Financeiro** | Perda de receita por cálculos errados de preço/fixação. | Médio | Centralizar lógica em `ContractEngine`; testes de integração extensivos. |
| **Modelagem** | Entidades excessivas podem gerar complexidade. | Baixo | Manter `ContractCounterparty` genérica; usar herança de domínio apenas quando necessário. |
| **Rastreabilidade** | Falha ao auditorar alterações de tolerância ou fixação. | Médio | Históricos (`ContractFixationHistory`, `ContractToleranceLog`) e audit log obrigatório. |
| **Regulatório** | Não atender requisitos de exportação ou compliance. | Baixo | Domínio `ExportContract` com metadados de Incoterm e validações. |
| **Fiscal** | Tributação incorreta em barter/CPR. | Médio | Definir regras fiscais nas camadas de cálculo financeiro, validar com contador. |
| **Performance** | Cálculos de posição em tempo real podem degradar sob alta carga. | Médio | Cache de snapshots; batching de eventos de entrega. |
| **Multi‑tenant** | Dados cruzados entre tenants. | Baixo | `tenant_id` obrigatório em todas as novas entidades; políticas de isolamento no ORM. |

---

## RESULTADO FINAL

1. **Permanece do BUSINESS‑DOMAIN‑06:** Entidades centrais (`CommodityContract`, `ContractDelivery`, `ContractFixation`, `ContractQualityAdjustment`, `ContractSettlement`, `ContractDocument`).
2. **Alterações:** Adição de `ContractCounterparty`, `MasterContract`, `ContractDeliverySchedule`, `ContractTolerance`, `ContractFixationPartial`, divisão de `ContractSettlement`/`FinancialSettlement`.
3. **Remoções:** nenhuma entidade original removida; apenas evitada persistência duplicada de `ContractPosition`.
4. **Novas Entidades:** `ContractCounterparty`, `MasterContract`, `ContractDeliverySchedule`, `ContractTolerance`, `ContractFixationPartial`, `ContractPositionSnapshot`, `ExportContract` (future), `CommodityPurchaseRight`, `BarterAgreement`.
5. **Arquitetura Recomendada para BUSINESS‑DOMAIN‑07:**
   - Utilizar o modelo endurecido como base.
   - Criar subsistema **Portal do Parceiro** que consome `CommodityContract` e `ContractCounterparty`.
   - Subdomínio **Originação** responsável por criar `MasterContract` e `ChildContract`.
   - Integração futura com **Hedge** e **Financeiro** via `FinancialSettlement`.

*Este documento serve como auditoria de hardening e ponto de partida para a evolução do domínio de contratos.*
