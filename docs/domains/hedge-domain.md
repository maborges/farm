# Hedge Domain – BUSINESS‑DOMAIN‑09 – Hedge Multicultura

## 1️⃣ Conceitos de negócio

| Conceito | Definição |
|---|---|
| **Hedge** | Estratégia de mitigação de risco de preço ou de margem, usando instrumentos financeiros (futuros, opções, swaps, NDF, travas) ou operações naturais (barter, CPR) para proteger a exposição de produção ou de receita. |
| **Trava** | Operação que fixa um intervalo de preço (floor e/or ceiling) em um contrato futuro ou em um swap, limitando perdas e ganhos. |
| **Fixação** | Bloqueio de preço em contrato futuro ou à vista, normalmente mediante pagamento antecipado ou garantia. |
| **Posição física** | Quantidade de commodity efetivamente disponível em estoque ou em produção. |
| **Posição contratada** | Volume já vendido ou comprado em contratos futuros, opções ou swaps. |
| **Posição aberta** | Diferença entre posição física e contratada que ainda não está coberta. |
| **Exposição líquida** | Valor monetário da posição aberta, considerando preço de mercado e custos de financiamento. |
| **Derivativo** | Instrumento financeiro cujo valor deriva de um ativo‑subjacente (commodity, taxa de câmbio, índice). |
| **Contrato futuro** | Acordo padronizado negociado em bolsa que obriga a compra/venda de uma commodity a preço e data futuros. |
| **Opção** | Direito, mas não obrigação, de comprar (call) ou vender (put) a um preço pré‑definido até uma data de vencimento. |
| **Swap** | Troca de fluxos de pagamento (ex.: preço fixo vs preço variável). |
| **NDF** | Non‑Deliverable Forward – contrato de câmbio futuro sem entrega física, liquidação em moeda de referência. |
| **Mark‑to‑Market (MtM)** | Reavaliação diária do valor de mercado dos derivativos, refletindo ganhos/perdas não realizados. |
| **Chamada de margem** | Solicitação de aporte de garantia adicional quando a posição perde valor de mercado. |
| **Base / Spread** | Diferença entre preço à vista da commodity e preço futuro (base) ou entre dois contratos (spread). |
| **Moeda** | Unidade monetária usada na negociação (ex.: USD, BRL). |
| **Indexador** | Indicador usado para correção de pagamentos (ex.: CDI, IPCA). |

### Diferenças principais

- **Hedge × Contrato** – O contrato futuro é um instrumento; o hedge é a estratégia que utiliza o contrato (ou outros instrumentos) para proteger a exposição. 
- **Hedge × Fixação** – Fixação trata apenas de garantir um preço; hedge pode envolver proteção contra variações de preço, câmbio e basis, podendo usar derivativos ou operações naturais. 
- **Hedge × Barter** – Barter troca insumos por produção; pode atuar como hedge natural, mas não oferece a mesma flexibilidade de derivativos. 
- **Hedge × CPR** – CPR (cédula) representa produção futura; hedge pode ser usado para proteger o preço da entrega da CPR, mas são conceitos distintos. 
- **Hedge × Seguro** – Seguro cobre eventos de risco (ex.: clima) mediante prêmio; hedge protege variações de preço de mercado. 
- **Hedge × Especulação** – Especulação busca ganho com variação de preço; hedge busca neutralizar risco.

---

## 2️⃣ Inventário do que já existe

| Funcionalidade | Status | Evidência (arquivo / classe / endpoint) | Lacuna |
|---|---|---|---|
| **Operação de Hedge (registro)** | EXISTE PARCIALMENTE EM CÓDIGO | `services/api/enterprise/models/sprints_27_33.py` → `class HedgeRegistro`; `services/api/enterprise/routers/sprints_27_33_router.py` → `def registrar_hedge`; `services/api/enterprise/services/sprints_27_33_service.py` → `def registrar_hedge` | Falta regras de negócio, cálculo de MtM, validações, UI, relatórios. |
| **Fixação / Trava** | NÃO EXISTE NO CÓDIGO | – | Nenhum modelo, serviço ou router implementado. |
| **Mark‑to‑Market** | NÃO EXISTE NO CÓDIGO | – | Não há cálculo MtM nem histórico de avaliações. |
| **Posição física / contrato futuro** | NÃO EXISTE NO CÓDIGO | – | Não há entidade que represente posição física ou contratos futuros. |
| **Exposição líquida (hedgeável)** | NÃO EXISTE NO CÓDIGO | – | Não há cálculo consolidado que una estoque, contratos, CPR e barter. |
| **Derivativos (opções, swaps, NDF)** | NÃO EXISTE NO CÓDIGO | – | Não há modelos ou serviços. |
| **Integração com Financeiro** | NÃO EXISTE NO CÓDIGO | – | Nenhum ponto de integração definido entre Hedge e módulo Financeiro. |

> **Observação:** As ocorrências encontradas nas migrações (`hedge_registros`) indicam que houve um trabalho preliminar, porém o código foi removido nas versões posteriores. Não há implementação funcional presente.

---

## 3️⃣ Modelo conceitual (proposta)

| Entidade | Responsabilidade | Domínio dono | Ciclo de vida | Relacionamentos | Exemplo real |
|---|---|---|---|---|---|
| **HedgeStrategy** | Define política de hedge (instrumentos, limites, aprovação). | Originação | Criação ao cadastrar contrato de produção; atualização quando políticas mudam. | Refere‑se a **RiskPolicy** (Originação) e a **Commodity** (Estoque). | Estratégia “Proteção de preço de soja – trava de 5 %”. |
| **HedgeInstrument** | Representa o derivativo ou operação natural (futuro, opção, swap, NDF, trava, barter). | Financeiro (para derivativos) / Comercialização (para barter) | Registro ao executar operação; encerramento na data de vencimento ou liquidação. | Possui **HedgePosition**; associa‑se a **Contrato** (Financeiro) ou **BarterAgreement**. | Futuro de café ICE – contrato “ICF2027”. |
| **HedgePosition** | Quantidade e preço da posição (aberta/fechada). | Financeiro | Atualizada a cada trade ou ajuste de margem. | Relaciona‑se a **HedgeInstrument** e a **Commodity** (Estoque). | 100 barris de café a US$ 1,30 / bbl. |
| **HedgeTransaction** | Evento de compra/venda, ajuste de margem, liquidação. | Financeiro | Criado ao executar operação; pode gerar **MarginCall**. | Liga‑se a **HedgePosition**. | Compra de contrato futuro 10 contratos. |
| **HedgeExposure** | Cálculo da exposição agregada por commodity, safra e produtor. | Financeiro | Recalculado diariamente (MtM). | Consome dados de **Estoque**, **ContratoFuturo**, **CPR**, **BarterAgreement**. | Exposição de US$ 2 M em soja. |
| **HedgeMarkToMarket** | Valor diário de mercado das posições. | Financeiro | Atualizado a cada fechamento de bolsa. | Alimenta **HedgeExposure** e gera **MarginCall**. | MtM de –US$ 150 k. |
| **HedgeMarginCall** | Solicitação de aporte de garantia. | Financeiro | Gerado quando **HedgeExposure** excede limites. | Refere‑se a **Collateral** (Financeiro). | Pedido de R$ 200 k. |
| **HedgeRiskMetric** | Métricas de risco (VaR, CVaR, sensibilidade). | Originação | Calculado periodicamente para decisões de aprovação. | Usa **HedgeExposure** e **RiskPolicy**. | VaR de 5 % = US$ 100 k. |
| **HedgePolicy** | Regras de limites por commodity, safra, produtor, instrumento. | Originação | Definida em **RiskPolicy**; pode ser atualizada pelo PO. | Aplica‑se a **HedgeStrategy**. | Limite de 10 % do valor da produção. |

---

## 4️⃣ Exposição hedgeável

### Cálculo proposto (MVP)

1. **Exposição física** – Quantidade de commodity disponível em estoque (`Commodity`) menos a quantidade já comprometida em contratos físicos (`Contrato`).
2. **Exposição financeira** – Valor de posições abertas em derivativos (`HedgePosition`) convertido para a moeda base usando taxa de câmbio corrente.
3. **Exposição cambial** – Diferença entre valor em moeda estrangeira e equivalente em BRL usando taxa spot.
4. **Exposição de basis/spread** – Diferença entre preço à vista e preço futuro (base) ou entre dois futuros (spread).

### Escopo MVP vs V2/V3

| Escopo | Inclui | MVP | V2 | V3 |
|---|---|---|---|---|
| **Posição física** | Estoque + contratos físicos | ✅ | – | – |
| **Exposição líquida** | Soma das exposições acima | ✅ | – | – |
| **Contratos futuros** | Registro de futuros negociados | ✅ (simples) | ✅ (com detalhe de margem) | ✅ (com integração bolsa) |
| **Derivativos avançados** (opções, swaps, NDF) | – | – | ✅ | ✅ |
| **Travas de preço/câmbio** | – | – | ✅ | ✅ |
| **Mark‑to‑Market avançado** | Histórico diário, ajuste de juros | – | ✅ (MtM básico) | ✅ (MtM com curva de volatilidade) |
| **Integração com CPR/Barter** | Uso de CPR física/financeira e acordos de barter como hedge natural | – | ✅ | ✅ |

---

## 5️⃣ Instrumentos de hedge (proposta)

| Instrumento | Quando usar | Dados exigidos | Riscos cobertos | Complexidade | MVP? |
|---|---|---|---|---|---|
| **Contrato futuro** | proteção de preço de commodity com alta liquidez. | Preço futuro, data de vencimento, volume. | Risco de preço. | Baixa | ✅ |
| **Opção** | necessidade de proteção com upside limitado. | Strike, vencimento, premium, volatilidade. | Risco de preço, permite participação em alta. | Média | ❌ (V2) |
| **Swap** | troca de fluxo de preço fixo vs variável ou cambial. | Notional, taxa fixa, taxa variável, datas. | Risco de preço e taxa de juros. | Média | ❌ (V2) |
| **NDF** | hedge cambial quando a moeda não é negociada localmente. | Taxa de câmbio acordada, data de liquidação. | Risco cambial. | Média | ❌ (V2) |
| **Trava de preço** | definição de faixa (floor‑ceiling). | Preço floor, preço ceiling, volume. | Limita perdas e ganhos. | Baixa | ✅ (MVP) |
| **Trava cambial** | proteger contra variação cambial em importação/exportação. | Taxas spot, forward, limites. | Risco cambial. | Média | ❌ (V2) |
| **Collar** | combinação de trava de preço + trava cambial. | Floor, ceiling, taxa cambial. | Risco de preço e câmbio. | Média | ❌ (V3) |
| **Hedge natural (Barter / CPR)** | usar produção física ou troca de insumos como cobertura. | Quantidade de produção, contrato de barter/CPR. | Risco de preço, risco de disponibilidade. | Baixa | ✅ (MVP) |

---

## 6️⃣ Mark‑to‑Market (conceitual)

- **Preço de referência** – Preço de fechamento da bolsa (B3/ICE) para o contrato futuro correspondente. 
- **Moeda** – USD para commodities internacionais; conversão para BRL usando taxa spot do dia. 
- **Data de avaliação** – Ao final de cada dia de negociação (horário de fechamento). 
- **Câmbio** – Aplicar taxa de compra/venda do dia; se houver contrato em outra moeda, usar taxa de conversão. 
- **Contratos parcialmente fixados** – Calcular MtM apenas sobre a parte não fixada; a parte fixada permanece como contrato fechado. 
- **Histórico** – Persistir cada avaliação diária em tabela `hedge_mtm_history` (a ser criada no futuro). 

> **Nota:** Fórmula exata será detalhada na fase de implementação (não feita aqui).

---

## 7️⃣ Integração com domínios existentes

| Domínio | Quem fornece dados | Quem consome dados | Sistema de registro (System of Record) | Eventos esperados |
|---|---|---|---|---|
| **Contratos** | Dados de contrato de fornecimento, volumes, datas. | **HedgeStrategy**, **HedgeExposure** | `services/api/contrato/models/contrato.py` (registro de contrato). | `ContractCreated`, `ContractUpdated`.
| **Comercialização** | Preços de venda, acordos de barter. | **HedgeInstrument** (Barter), **HedgeExposure**. | `services/api/comercializacao/models/...` | `SaleCreated`, `BarterAgreementCreated`.
| **Financeiro** | Limites de crédito, saldo de contas, taxas de câmbio. | **HedgeExposure**, **HedgeMarginCall**. | `services/api/financeiro/models/...` | `CreditLimitChanged`, `ExchangeRateUpdated`.
| **Estoque** | Quantidade de commodity disponível, localização. | **HedgeExposure**, **HedgeStrategy**. | `services/api/estoque/models/commodity.py`. | `StockAdjusted`, `CommodityAdded`.
| **Qualidade** | Qualidade da produção (impacta preço). | **HedgeRiskMetric** (ajuste de preço). | `services/api/qualidade/models/...` | `QualityAssessmentCompleted`.
| **Originação** | Política de risco, score de produtor. | **HedgePolicy**, **HedgeStrategy**. | `services/api/origination/models/risk_policy.py`. | `RiskPolicyUpdated`.
| **CPR** | Dados de cédulas físicas/financeiras. | **HedgeExposure** (garantia). | `services/api/cpr/models/...` | `CprIssued`, `CprSettled`.
| **Barter** | Acordos de troca de insumos. | **HedgeExposure** (garantia natural). | `services/api/barter/models/...` | `BarterAgreementCreated`.
| **Portal do Parceiro** | Visão resumida de posições, margens, relatórios. | Usuário (produtor/partner). | Não é system of record – apenas leitura. | `PartnerViewRequested`.

---

## 8️⃣ Limites e governança

- **Política de hedge** – Definida em **RiskPolicy** (Originação). Controla limites por commodity, safra, produtor e tipo de instrumento.
- **Alçadas de aprovação** – Até 5 % do limite total pode ser aprovado por gestor de risco; acima disso requer aprovação do comitê financeiro.
- **Responsabilidade** – Financeiro executa cálculos; Originação define políticas; Comercialização lança instrumentos; Estoque fornece garantias.

### Pertencimento

| Item | Pertence a |
|---|---|
| Definição de limites e aprovação | **Originação** (RiskPolicy) |
| Cálculo de exposição e MtM | **Financeiro** |
| Registro de contratos futuros / swaps | **Financeiro** |
| Operações de barter como hedge natural | **Comercialização** |
| Garantias físicas (commodity) | **Estoque** |
| Consumo por Hedge (exposição) | **Financeiro** (dados) + **Originação** (políticas) |

---

## 9️⃣ Portal do parceiro

- **Deve enxergar**:
  - Travas vinculadas ao contrato do produtor.
  - Preço fixado (floor/ceiling) e preço médio da posição.
  - Saldo aberto de hedge (exposição ainda não coberta).
  - Data de vencimento dos instrumentos.
- **Não deve enxergar**:\n  - Estratégias internas de risco (RiskPolicy).
  - Detalhes de margem de garantia de terceiros.
  - Dados de contratos futuros que não estejam vinculados ao seu produtor.

---

## 🔟 Roadmap

| Versão | Itens incluídos | Público | Comentários |
|---|---|---|---|
| **MVP** | Pos. física, exposição líquida, contratos futuros simples, trava de preço, MtM básico (preço de fechamento), UI Dashboard resumida. | **Enterprise** | Entrega de proteção de preço essencial. |
| **V2** | Integração de CPR (física/financeira) como hedge natural, inclusão de barter, cálculo de margem cambial, MtM aprimorado (inclui juros). | **Professional** | Expansão para produção diversificada. |
| **V3** | Opções, NDF, swaps, cenários de stress, cálculo de VaR/CVaR, suporte a múltiplas moedas. | **Enterprise** | Cobertura de risco avançada. |
| **V4** | Automação de execução via corretoras, integração direta com bolsas (API), alertas inteligentes por IA, relatórios regulatórios completos. | **Enterprise** | Estratégia de diferenciação de mercado. |

---

## 11️⃣ Riscos arquiteturais

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| **Financeiro – cálculo incorreto** | Perdas financeiras graves. | Média | Implementar validações unitárias, testes de cálculo, auditoria externa. |
| **Regulatório** | Multas, bloqueio de operação. | Baixa | Garantir compliance (CVM, BM&F), documentação de processos. |
| **Especulação inadvertida** | Exposição inesperada. | Média | Limitar alçadas, monitorar KPIs de risco. |
| **Acoplamento com Financeiro** | Duplicação de lógica de crédito. | Média | Usar interfaces bem definidas; evitar replicação de modelos. |
| **Duplicação de contratos** | Inconsistência de dados. | Média | Sistema de eventos único (event bus) para atualização. |
| **Multi‑tenant** | Vazamento de dados entre produtores. | Alta | Isolamento por tenant_id; criptografia em repouso. |
| **Performance** | Cálculo MtM em grande volume (milhares de contratos). | Média | Cache de preços, batch jobs off‑peak, escalabilidade horizontal. |
| **Segurança** | Injeção de dados e acesso não‑autorizado. | Alta | Aplicar *mandatory‑secure‑web‑skills* nas APIs futuras; validar entradas. |

---

## 📌 Resultado esperado (resumo)

1. **O que já existe e atende** – Registro básico de operação de hedge (`HedgeRegistro`).
2. **O que existe parcialmente** – Modelo e serviços de registro, sem regras de negócio, cálculo MtM, UI ou relatórios.
3. **O que realmente precisa ser criado** – Modelos de **HedgeInstrument**, **HedgePosition**, **HedgeExposure**, **HedgeMarkToMarket**, **HedgeMarginCall**, **HedgePolicy**; serviços de cálculo, UI de dashboard, integração com Estoque, Contratos, CPR e Barter.
4. **Extensão de Contratos** – Vinculação de hedge a contratos de fornecimento (ver `ContractCreated`).
5. **Extensão do Financeiro** – Cálculo de exposição, MtM, margem, garantias.
6. **Extensão da Comercialização** – Barter como hedge natural.
7. **O que NÃO deve ser criado** – Módulo financeiro paralelo; módulos autônomos de Crédito, CPR ou Barter.
8. **Escopo Hedge MVP** – Pos. física, exposição líquida, futuros simples, trava de preço, MtM básico, dashboard resumido.
9. **V2/V3/V4** – Conforme roadmap acima.

---

*Documento gerado em conformidade com as regras de linguagem (pt‑br) e as políticas de auditoria.*
