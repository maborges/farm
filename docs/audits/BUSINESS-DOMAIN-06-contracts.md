# Domínio: Contratos Agrícolas Multicultura

## PARTE 1 — Conceitos de Negócio

| Conceito | Definição | Observações |
|----------|-----------|-------------|
| **Contrato Spot** | Compra/venda para entrega **imediata** (ou dentro de poucos dias). O preço é definido no momento da negociação. | Usado para atender necessidades de curtíssimo prazo. |
| **Contrato a Termo** | Acordo para entrega futura em **data especificada**, mas o preço é definido **no momento da assinatura**. | Garante preço ao produtor e ao comprador. |
| **Contrato Futuro** | Similar ao a termo, porém **negociado em bolsa** e padronizado (tamanho de lote, qualidade mínima, data de vencimento). | Exige margem de garantia e pode ser liquidado financeiramente. |
| **Contrato de Exportação** | Acordo que inclui **logística internacional**, requisitos fitossanitários e variação cambial. | Normalmente envolve cláusulas de entrega FOB/CIF. |
| **CPR Física** (*Commodity Purchase Right*) | Direito de comprar a commodity **fisicamente** em uma data futura, respeitando condições de qualidade. | Geralmente usado por processadores que precisam garantir volume. |
| **CPR Financeira** | Direito de comprar a commodity **financeiramente** (settlement cash‑settled) sem movimentar o produto físico. | Baseia‑se em índices de preço. |
| **Barter** | Troca de **commodities por outras commodities ou serviços** em vez de pagamento em dinheiro. | Necessita de contrato que descreva a taxa de troca e qualidade mínima. |
| **Fixação de Preço** | Acordo que **trava** o preço da commodity por um período, independentemente da variação de mercado. | Pode ser feita via contrato a termo ou swap. |
| **Entrega Física** | Transporte e transferência do **produto físico** ao comprador. | Pode ocorrer em lote único ou em entregas parciais. |
| **Liquidação Financeira** | Pagamento **em dinheiro** (ou compensação bancária) que encerra a obrigação financeira do contrato. | Pode ser imediata (spot) ou na data de vencimento (a termo/futuro). |

### Diferenças chave
- **Contrato × Entrega** – O contrato estabelece **quem, quanto e a que preço**; a entrega cumpre a parte **logística/quantitativa**. Um contrato pode prever múltiplas entregas (parciais) ou nenhuma entrega física (ex.: CPR financeira). 
- **Contrato × Fixação** – Fixação refere‑se ao **preço**; o contrato pode ou não conter fixação. Um contrato a termo já fixa preço, mas a fixação pode ser feita separadamente via swap. 
- **Contrato × Hedge** – Hedge é uma **estratégia de mitigação de risco** que usa instrumentos financeiros (futuros, opções, swaps). O contrato em si não é hedge, mas pode ser **coberto** por um hedge. 
- **Contrato × Barter** – Barter troca **commodities** ao invés de dinheiro. É um tipo especial de contrato onde a contraparte aceita a entrega de outra commodity ou serviço como pagamento. 

---

## PARTE 2 — Modelo Genérico Multicultura

### Entidades Conceituais

| Entidade | Responsabilidade | Ciclo de Vida | Relacionamentos | Exemplo Real | Regras de Negócio |
|----------|-------------------|---------------|-----------------|--------------|-------------------|
| **CommodityContract** | Representa o **acordo comercial** entre duas partes (produtor/cooperativa × comprador). | Criação → Ativação → Execução → Encerramento. | 1‑N **ContractDelivery**, 1‑N **ContractFixation**, 1‑N **ContractQualityAdjustment**, 1‑1 **ContractSettlement**, 1‑N **ContractDocument**, N‑1 **Commodity** (referência da commodity negociada). | Contrato de 500 t de soja a preço fixo R$ 120/kg, com cláusula de preço mínimo de 115 kg. | • Só pode ser criado por usuários com permissão **contract_manager**.<br>• Não pode referenciar commodity de outro *tenant*.<br>• Deve conter **tenant_id**, **start_date**, **end_date**, **price_type** (spot/term/future). |
| **ContractDelivery** | Registro da **entrega física** de parte ou total do volume contratado. | Criação → Atualização (status) → Conclusão. | N‑1 **CommodityContract**, N‑1 **LoteEstoque**, N‑1 **Romaneio**. | Entrega de 200 t de soja em 03/2026, vinculada ao lote #L123. | • Quantidade entregue ≤ quantidade contratada ainda não entregue.<br>• Deve validar qualidade mínima conforme contrato. |
| **ContractPosition** | Posição aberta de um contrato que ainda não foi totalmente entregue/ liquidado. | Atualização a cada entrega ou ajuste. | 1‑N **ContractDelivery**, 1‑1 **CommodityContract**. | Após 2 entregas de 200 t cada, resta 100 t a ser entregue. | • Mantém saldo de quantidade e valor restante. |
| **ContractFixation** | Registro da **fixação de preço** (ex.: swap, preço mínimo garantido). | Criação → Eventual rescisão. | 1‑N **CommodityContract**. | Fixação de preço de US$ 15/Bushel por 12 meses. | • Não pode fixar preço acima de limite regulatório.<br>• Deve ser auditada. |
| **ContractQualityAdjustment** | Ajustes (prêmio ou deságio) decorrentes da **qualidade** dos lotes entregues. | Criação ao validar entrega → Atualização se a qualidade mudar. | 1‑N **ContractDelivery**, 1‑N **CommercialQualityRule** (re‑uso de regras já definidas). | Prêmio de + R$ 0,05/kg por café SCA ≥ 85. | • Aplicar somente se a entrega atender requisitos da regra.<br>• Não pode gerar ajuste negativo maior que 100 % do preço base. |
| **ContractSettlement** | Representa a **liquidação financeira** (pagamento, débito, crédito) do contrato. | Criação após última entrega ou data de vencimento → Conclusão. | 1‑1 **CommodityContract**, N‑1 **ContractDelivery**. | Pagamento de R$ 60 M em 05/2026 via boleto. | • Deve gerar título financeiro correspondente.<br>• Não pode ser emitido se houver pendência de qualidade. |
| **ContractDocument** | Armazena documentos legais (PDF, XML, etc.) vinculados ao contrato. | Upload → Versionamento → Arquivamento. | 1‑N **CommodityContract**. | PDF do contrato assinado digitalmente. | • Tipo de documento (contrato, anexo, laudo) deve ser registrado.<br>• Só usuários com permissão **document_manager** podem excluir. |

> **Modelo genérico** – Todas as entidades possuem `tenant_id` e são projetadas para serem reutilizadas por qualquer commodity (café, soja, milho, algodão, cacau, pecuária, etc.).

---

## PARTE 3 — Integração com Qualidade

1. **Como a qualidade afeta**
   - **Quantidade contratada** – Não é alterada; o contrato fixa a quantidade máxima acordada.
   - **Quantidade entregue** – Pode ser reduzida por *desconto de peso* (perda física) detectada no laudo de qualidade.
   - **Quantidade liquidada** – Baseia‑se na **quantidade entregue** após descontos de peso e ajustes de qualidade.
   - **Preço final** – Calculado como `price_base + sum(prêmios) – sum(deságios)` onde os prêmios/deságios são gerados por `ContractQualityAdjustment` usando `CommercialQualityRule`.
   - **Prêmio** – Valor adicional positivo quando atributos (ex.: SCA, baixa umidade) atendem a limites superiores.
   - **Deságio** – Valor negativo quando atributos estão abaixo do mínimo (ex.: alta umidade, mofo).

2. **Perguntas de cenário**
   - **Um lote pode ser entregue e sofrer deságio?** Sim. O lote é aceito, mas o `ContractQualityAdjustment` gera um deságio que reduz o valor a ser pago.
   - **Um lote pode ser rejeitado?** Sim. Caso a qualidade não atenda ao requisito mínimo estabelecido no contrato, o lote pode ser *rejeitado* (status *rejected*). Não há consuma‑ção de estoque e não gera saldo contractual.
   - **Um lote pode ser parcialmente aceito?** Sim. O sistema registra a quantidade aceita e a quantidade rejeitada; o saldo contractual diminui apenas da parte aceita.
   - **Como isso afeta o saldo contratual?** O **saldo de quantidade** diminui apenas pela quantidade aceita; o **saldo financeiro** é ajustado por prêmios/deságios associados à parte aceita. Rejeições não alteram saldo.

---

## PARTE 4 — Integração com Estoque

| Evento | Quando consome estoque? | Quando **não** consome? |
|--------|------------------------|------------------------|
| **Entrega parcial aceita** | Apenas a **quantidade aceita** (após descontos de peso) é debitada do estoque. | Quantidade rejeitada permanece no estoque. |
| **Entrega total rejeitada** | Nenhum débito – estoque permanece intacto. |
| **Contrato cancelado antes da entrega** | Nenhum débito. |
| **Entrega com ajuste de qualidade** | O estoque é debitado pelo **peso líquido comercial** (já descontado física). |

### Rastreabilidade (sem romper trilha)
```
Contrato (CommodityContract)
  ↓
Entrega (ContractDelivery)
  ↓
Lote (LoteEstoque)
  ↓
Romaneio (Romaneio)
  ↓
Talhão
  ↓
Safra
```
* Cada entidade guarda uma referência ao seu *pai* (`contract_id`, `delivery_id`, `lote_id`, etc.).
* Os logs de eventos (audit) registram **data/hora**, **usuário**, **motivo** (ex.: “desconto de peso 1,5 % por umidade”).
* A cadeia permite consultas de origem → *qual was the original field* para auditoria regulatória.

---

## PARTE 5 — Integração com Financeiro Futuro (Modelagem)

| Conceito | Modelo de Dados (entidade fictícia) | Evento que gera título financeiro |
|----------|------------------------------------|-----------------------------------|
| **Contas a Receber** | `FinancialAccount` (tenant, contract, amount, due_date). | Criação após `ContractSettlement` ou após **liquidação parcial** de entrega. |
| **Adiantamentos** | `AdvancePayment` (contract, amount, date, status). | Quando o comprador paga antes da entrega (ex.: *pre‑pay*). |
| **Liquidação** | `FinancialSettlement` (contract, total_amount, settled_at). | No fechamento da `ContractSettlement`. |
| **Descontos** | `FinancialDiscount` (settlement, amount, reason). | Aplicado quando há *desconto de peso* ou *deságio*. |
| **Prêmios** | `FinancialPremium` (settlement, amount, reason). | Aplicado quando há *prêmio* por qualidade. |
| **CPR** | `CommodityPurchaseRight` (contract, type{physical,financial}, quantity, price). | Gera título de pagamento futuro (cash‑settled) ou reserva de estoque. |
| **Barter** | `BarterAgreement` (contract, commodity_given, commodity_received, rate). | Cria dois títulos: débito da commodity entregue e crédito da commodity recebida. |

*Eventos que devem gerar títulos futuros* – assinatura de contrato com fixação, entrega aceita, ajuste de qualidade, adiantamento, fechamento de contrato.

---

## PARTE 6 — Portal do Parceiro (Visão do Produtor)

| Seção | Informações exibidas |
|-------|----------------------|
| **Meus Contratos** | Lista de `CommodityContract` ativos, status (ativo, em execução, encerrado), volume total contratado, saldo a entregar. |
| **Saldo a Entregar** | Quantidade restante por contrato, prazo de entrega, alerta de vencimento. |
| **Entregas Realizadas** | Histórico de `ContractDelivery` (data, lote, quantidade aceita, quantidade rejeitada, qualidade registrada). |
| **Qualidade** | Resultado de laudos associados a cada entrega, prêmios/deságios aplicados. |
| **Descontos & Prêmios** | Totais financeiros acumulados por contrato. |
| **Documentos** | Links para PDFs de contrato, laudos, notas fiscais. |

A UI deve usar **shadcn/ui** (outline buttons sm, inputs sm, rounded‑sm) e seguir a paleta “Verde Esmeralda / Tons Terra” com modo dark/light.

---

## PARTE 7 — Roadmap

| Versão | Funcionalidades | Classificação |
|--------|----------------|---------------|
| **MVP** (Q4 2026) | Modelagem de entidades (Contract, Delivery, Settlement), registro de entregas, cálculo de prêmios/deságios, visualização no portal. | **Básico** |
| **V2** (Q2 2027) | Fixação de preço, CPR física/financeira, adiantamentos, relatórios de saldo, integração com módulo de contas a receber. | **Profissional** |
| **V3** (Q4 2027) | Barter, hedge via swaps, exportação (documentos internacionais), auditoria regulatória avançada, exportação API para parceiros. | **Enterprise** |

---

## PARTE 8 — Riscos Arquiteturais

| Tipo de Risco | Descrição | Mitigação |
|----------------|-----------|-----------|
| **Modelagem** | Entidades podem ficar muito acopladas ou gerar redundância de informações (ex.: preço base duplicado). | Definir camada de *Domain Services* que centraliza cálculos e mantém entidades *thin*. |
| **Financeiro** | Prêmios ou deságios incorretos podem gerar perdas monetárias ou reclamações regulatórias. | Auditoria automática (`audit_log`) e validação de regras antes de gerar `FinancialSettlement`. |
| **Regulatório** | Contratos agrícolas podem estar sujeitos a normas da CVM, Anvisa, etc. | Incluir metadados de compliance em `ContractDocument` e validar contra catálogos regulatórios. |
| **Fiscal** | Erros de contabilização (ex.: tributação de barter) podem gerar multas. | Modelo de taxação configurável por tipo de contrato e geração de relatórios fiscais. |
| **Rastreabilidade** | Rastreio perdido se os IDs não forem propagados corretamente. | Uso de UUIDs globais e logs de eventos (event sourcing). |
| **Acoplamento** | Integrações com qualidade e estoque podem criar dependências circulares. | Comunicação baseada em *domain events* (ex.: `QualityEvaluated`, `StockReserved`). |

---

*Este documento serve como referência para a criação das futuras APIs, tabelas e fluxos de negócio. Nenhum código foi alterado.*
