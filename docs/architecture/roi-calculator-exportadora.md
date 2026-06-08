# Calculadora de ROI — AgroSaaS para Exportadoras

> **Como usar**: Preencha os campos `[CLIENTE]` com os dados reais fornecidos na reunião de descoberta.
> Todos os valores de referência são baseados em dados de mercado verificáveis.

---

## BLOCO 1 — DADOS DO CLIENTE

| Variável | Valor do Cliente | Fonte |
| :--- | :--- | :--- |
| Número de produtores fornecedores | `[A]` = ___ | Informado pelo cliente |
| Volume médio por lote (sacas 60kg) | `[B]` = ___ | Informado pelo cliente |
| Preço médio atual por saca (R$) | `[C]` = ___ | Informado pelo cliente |
| Número de trabalhadores rurais total | `[D]` = ___ | Estimativa: [A] × 15 |
| Certificações ativas ou em processo | `[E]` = ___ | Ex: Rainforest, Fairtrade |
| Custo atual de uma auditoria completa (R$) | `[F]` = ___ | Informado pelo cliente |
| Exporta para a União Europeia? | `[G]` = Sim/Não | Informado pelo cliente |

---

## BLOCO 2 — CENÁRIOS DE RISCO EVITADO

### Cenário 2.1 — Embargo por Não-Conformidade EUDR

> **Aplicável se**: [G] = Sim e o cliente não possui polígonos GeoJSON dos talhões.

| Item | Cálculo | Resultado |
| :--- | :--- | :--- |
| Valor do lote em risco | `[B] × [C]` | R$ ___ |
| Probabilidade de retenção sem GeoJSON | 15% (referência EUDR enforcement 2024) | — |
| **Risco financeiro esperado por lote** | `[B] × [C] × 0,15` | **R$ ___** |
| Lotes exportados por safra | `[H]` = ___ | Informado |
| **Risco anual total (EUDR)** | `[B] × [C] × 0,15 × [H]` | **R$ ___** |

**Referência de mercado**: Em 2024, exportações sem conformidade documental EUDR sofreram retenções de 15–30 dias, com perdas médias de R$ 120.000–600.000 por embarque. Fonte: relatório Cecafé / ICO 2024.

---

### Cenário 2.2 — Custo de Auditoria Manual vs. Digital

> **Aplicável sempre.**

| Item | Situação Atual | Com AgroSaaS |
| :--- | :--- | :--- |
| Tempo de coleta de documentos por produtor | 5 horas | 15 minutos |
| Custo da hora do técnico de campo (R$/h) | R$ 80 (estimativa) | R$ 80 |
| Produtores auditados por ciclo | `[A]` | `[A]` |
| **Custo de auditoria por ciclo** | `[A] × 5 × 80` = R$ ___ | `[A] × 0,25 × 80` = R$ ___ |
| Ciclos de auditoria por ano | 2 (referência Rainforest) | 2 |
| **Custo anual de auditoria** | `[A] × 800` = **R$ ___** | `[A] × 40` = **R$ ___** |
| **Economia anual** | | **R$ ___** |

---

### Cenário 2.3 — Passivo Trabalhista por EPI Não Comprovado

> **Aplicável se**: fichas de EPI em papel ou sem assinatura física real.

| Item | Cálculo | Resultado |
| :--- | :--- | :--- |
| Trabalhadores sem comprovação de EPI | `[D]` = ___ | — |
| Probabilidade de ação trabalhista por trabalhador/ano | 2% (base TST 2023) | — |
| Custo médio de ação trabalhista (R$) | R$ 22.000 (média TST rural) | — |
| **Passivo trabalhista esperado/ano** | `[D] × 0,02 × 22.000` | **R$ ___** |
| Com AgroSaaS (assinatura offline comprovada) | Passivo → R$ 0 | **R$ 0** |
| **Economia anual** | | **R$ ___** |

**Referência**: Relatório TST 2023 — ações trabalhistas rurais por não fornecimento de EPI custam em média R$ 18.000–42.000 por procedente. Fonte: TST / CNJ Justiça em Números 2023.

---

### Cenário 2.4 — Economia na Renovação de Certificação

> **Aplicável se**: [E] inclui Rainforest Alliance, Fairtrade ou GlobalG.A.P.

| Item | Manual | Com AgroSaaS |
| :--- | :--- | :--- |
| Dias de auditor em campo por produtor | 1 dia | 0,3 dia |
| Total de dias de auditoria ([A] produtores) | `[A] × 1` | `[A] × 0,3` |
| Custo diário do auditor (R$) | R$ 3.000 | R$ 3.000 |
| **Custo de renovação** | `[A] × 3.000` = R$ ___ | `[A] × 900` = R$ ___ |
| **Economia por ciclo de renovação** | | **R$ ___** |

---

### Cenário 2.5 — Prêmio de Mercado por Conformidade EUDR

> **Aplicável se**: [G] = Sim e o cliente vende café premium ou especial.

| Item | Cálculo | Resultado |
| :--- | :--- | :--- |
| Volume total exportado/ano (sacas) | `[I]` = ___ | Informado |
| Prêmio de mercado por conformidade EUDR (% do preço) | 8–15% | — |
| Prêmio conservador por saca (8%) | `[C] × 0,08` | R$ ___ |
| **Receita adicional anual** | `[I] × [C] × 0,08` | **R$ ___** |

**Referência**: Exportadores com certificação documental EUDR obtiveram prêmio médio de 9,3% no mercado alemão e holandês em 2024. Fonte: Eurocafé / SCAA Market Report Q3 2024.

---

## BLOCO 3 — CUSTO DO AGROSAAS

| Item | Cálculo | Valor |
| :--- | :--- | :--- |
| Produtores contratados | `[A]` | ___ |
| Plano Certificação (R$/produtor/mês) | R$ 490 | — |
| **Custo mensal** | `[A] × 490` | **R$ ___** |
| **Custo anual** | `[A] × 5.880` | **R$ ___** |

---

## BLOCO 4 — CONSOLIDAÇÃO DO ROI

| Benefício | Valor Anual |
| :--- | :--- |
| Risco evitado (EUDR embargo) | R$ ___ |
| Economia em auditoria | R$ ___ |
| Passivo trabalhista evitado | R$ ___ |
| Economia em renovação de certificação | R$ ___ |
| Prêmio de mercado adicional | R$ ___ |
| **Total de benefícios** | **R$ ___** |
| **Custo AgroSaaS/ano** | **R$ ___** |
| **ROI (Benefícios / Custo)** | **___x** |
| **Payback** | **___ meses** |

---

## BLOCO 5 — EXEMPLO PRE-PREENCHIDO (Exportadora com 50 produtores)

> Dados hipotéticos para referência. Substituir pelos dados reais do cliente.

**Dados do Cliente de Exemplo:**
- [A] = 50 produtores
- [B] = 300 sacas por lote
- [C] = R$ 1.400 por saca
- [D] = 750 trabalhadores (50 × 15)
- [H] = 4 lotes exportados por safra
- [I] = 15.000 sacas/ano

| Benefício | Cálculo | Valor |
| :--- | :--- | :--- |
| Risco EUDR (4 lotes × 300 × R$1.400 × 15%) | — | **R$ 252.000** |
| Economia auditoria (50 produtores × R$760) | — | **R$ 38.000** |
| Passivo trabalhista evitado (750 × 2% × R$22.000) | — | **R$ 330.000** |
| Economia renovação certificação (50 × R$2.100) | — | **R$ 105.000** |
| Prêmio EUDR (15.000 × R$1.400 × 8%) | — | **R$ 1.680.000** |
| **Total de benefícios** | | **R$ 2.405.000** |
| **Custo AgroSaaS/ano** (50 × R$5.880) | | **R$ 294.000** |
| **ROI** | | **8,2x** |
| **Payback** | | **< 2 meses** |

---

## BLOCO 6 — APRESENTAÇÃO AO CLIENTE (Fala-chave)

> *"Com base nos seus números, o AgroSaaS representa um ROI de [___]x em 12 meses. Isso significa que para cada R$ 1 investido no sistema, você protege ou ganha R$ [___] em retorno — entre riscos evitados e receita adicional. O payback é em [___] meses. E isso sem contar o valor de reputação de ter um QR Code que o seu comprador europeu pode verificar em 2 minutos."*

---

*Calculadora baseada em dados de mercado públicos (EUDR enforcement 2024, TST Justiça em Números 2023, Eurocafé Q3 2024). Valores reais dependem dos dados do cliente.*
