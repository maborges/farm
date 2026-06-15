# Auditoria – **BUSINESS‑DOMAIN‑05 – Comercialização Multicultura baseada em Qualidade**

## 1️⃣ Escopo
Modelar regras de preço que consideram atributos de qualidade (umidade, impurezas, defeitos, etc.) e gerar ajustes (prêmios/deságios) por lote.

## 2️⃣ Entidades Criadas
- `CommercialQualityRule`
- `CommercialAdjustment`
- `CommercialPriceTable`
- `CommercialLotValuation`
- `CommercialContractPricing`

## 3️⃣ Integrações Planejadas
- **Qualidade** → avaliação de atributos
- **Romaneio** → fornece lote‑id e peso bruto
- **Beneficiamento** → atualiza perdas físicas
- **Estoque** → persiste `CommercialLotValuation`
- **Comercialização** → consome valuation para contrato
- **Contratos**, **CPR**, **Barter**, **Hedge**, **Exportação**, **Portal do Parceiro**

## 4️⃣ Roadmap
| Fase | Funcionalidades | Classificação |
|------|------------------|---------------|
| MVP (Q3 2026) | Regras de qualidade → ajustes de preço; valuation por lote; visualização no portal | **Básico** |
| V2 (Q1 2027) | `CommercialPriceTable` por região/contrato; suporte a hedge simples; auditoria de ajustes | **Profissional** |
| V3 (Q3 2027) | Integração completa com Barter/CPR; engine de regras avançada; exportação via API | **Enterprise** |

## 5️⃣ Riscos Arquiteturais
- **Modelagem:** regras conflitantes → prioridade de regras mais restritiva.
- **Acoplamento:** dependência forte entre Qualidade e Comercial → usar eventos assíncronos.
- **Cálculo Duplicado:** centralizar lógica em `CommercialLotValuationService`.
- **Financeiro:** deságios incorretos → audit log detalhado.
- **Regulatório:** prêmios podem ser regulamentados → metadata de compliance.
- **Performance:** indexação e cálculo incremental.

## 6️⃣ Próximos Passos
1. Aprovar o modelo de domínio.
2. Implementar as entidades nas próximas sprints (MVP → V2 → V3).
3. Definir política de auditoria e logs.
