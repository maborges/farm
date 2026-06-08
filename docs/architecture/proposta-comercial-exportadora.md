# Proposta Comercial — AgroSaaS para Exportadoras de Café

---

**[EXPORTADORA]**
A/C: [Nome do Decisor]
Cargo: [Cargo]
Data: [Data]
Proposta Nº: [000]
Válida por: 30 dias

---

## 1. Entendimento do Contexto

Com base na nossa conversa de [data da reunião], identificamos os seguintes pontos críticos para a operação de **[Nome da Exportadora]**:

- [ ] Ausência de polígonos GeoJSON dos talhões dos fornecedores para conformidade EUDR
- [ ] Processo de auditoria de certificação manual e custoso
- [ ] Fichas de EPI em papel sem validade documental comprovada
- [ ] Falta de rastreabilidade formal do blend — do talhão ao lote exportado
- [ ] Calibração de equipamentos sem registro auditável

> *Preencher os itens aplicáveis após a reunião de descoberta.*

---

## 2. O Que Entregamos

### Funcionalidades Incluídas no Plano Proposto

Todas as funcionalidades abaixo estão implementadas e em produção no AgroSaaS:

| Funcionalidade | Descrição | Padrão de Certificação Atendido |
| :--- | :--- | :--- |
| **GeoJSON dos Talhões** | Polígono cartográfico de cada talhão com área calculada | EUDR 2023/1115 |
| **Passaporte de Rastreabilidade** | Snapshot JSON do lote com hash SHA-256 imutável | Rainforest Alliance, GlobalG.A.P. |
| **QR Code Público** | URL pública do passaporte — sem login | Comprador europeu, Fairtrade |
| **Mapa de Satélite** | Talhão visualizável no mapa pelo comprador via QR | EUDR |
| **Caderno de Campo Canônico** | Trilha imutável de todas as operações com GPS e timestamp | GlobalG.A.P., Certifica Minas |
| **Assinatura Offline de EPI** | Canvas HTML5 no PWA — manuscrita, sem internet | Fairtrade, NR-31 |
| **Calibração de Equipamentos** | Registro com bloqueio operacional preventivo | GlobalG.A.P. |
| **Liberação Sanitária** | Checklist integrado ao ciclo operacional | Rainforest Alliance |
| **Auditoria SHA-256** | Log imutável de cada operação com hash antes/depois | LGPD, Compliance |
| **PWA Offline** | Aplicativo de campo funciona sem internet | Operação rural |
| **Multi-Tenancy** | Cada produtor com dados isolados, painel central | LGPD |

---

## 3. Escopo Proposto

### Opção A — Plano Certificação

**Para**: Produtores que precisam de conformidade regulatória completa.

| Item | Detalhe |
| :--- | :--- |
| Produtores incluídos | [X] produtores fornecedores da [Exportadora] |
| Talhões mapeados | Ilimitado por produtor |
| Lotes comerciais | Ilimitado |
| Passaportes SHA-256 | Ilimitado |
| QR Codes | Ilimitado |
| PWA Offline | Incluído para todos os operadores |
| Assinatura de EPI | Incluído |
| Calibração de Equipamentos | Incluído |
| Suporte | E-mail + WhatsApp em horário comercial |
| **Preço por produtor/mês** | **R$ 490** |
| **Total mensal ([X] produtores)** | **R$ [X × 490]** |
| **Total anual** | **R$ [X × 5.880]** |

---

### Opção B — Plano Enterprise (Exportadora como Hub)

**Para**: Exportadoras que gerenciam um pool de produtores e precisam de visão consolidada.

| Item | Detalhe |
| :--- | :--- |
| Painel centralizado da exportadora | 1 conta de gestão com visão de todos os produtores |
| Produtores incluídos | [X] produtores (preço por faixa) |
| Onboarding conduzido pela equipe AgroSaaS | Incluído |
| SLA de resposta | 4 horas úteis |
| Exportação de relatórios para auditoria | Incluído |
| Integração com ERP da exportadora | Sob consulta |
| **Preço mensal** | **Sob consulta** |

> Para proposta Enterprise, agendar call técnica com equipe de produto.

---

## 4. Prova de Conceito — 30 Dias Sem Custo

Antes do contrato, propomos uma PoC de 30 dias para validar o valor real na sua operação:

| Item | Meta |
| :--- | :--- |
| Produtores onboardados | 5 (indicados pela exportadora) |
| Talhões com GeoJSON | ≥ 20 |
| Lote comercial com passaporte | 1 |
| Assinaturas de EPI | ≥ 10 |
| QR Code funcional ao vivo | 1 |

**Custo da PoC**: R$ 0,00 — sem contrato, sem cartão.

**Critério de aprovação**: Se 4 dos 5 critérios acima forem atingidos, a proposta de contrato é apresentada na reunião de encerramento da PoC.

---

## 5. Projeção de ROI para [Exportadora]

Com base nos dados compartilhados na reunião:

| Cenário | Risco Atual | Com AgroSaaS | Economia |
| :--- | :--- | :--- | :--- |
| Lote retido por EUDR (500 sacas × R$ 1.200) | R$ 90.000 (15% prob.) | R$ 0 | **R$ 90.000/lote** |
| Auditoria manual ([X] produtores × 5h × R$ 80) | R$ [X × 400] | R$ 1.250 | **R$ [X × 400 - 1.250]** |
| Passivo trabalhista EPI ([Y] trabalhadores) | R$ [Y × 15.000] | R$ 0 | **R$ [Y × 15.000]** |
| Prêmio de mercado EUDR (1.000 sacas × R$ 120) | R$ 0 | R$ 120.000 extra | **R$ 120.000** |
| **Custo AgroSaaS/ano ([X] produtores)** | — | **R$ [X × 5.880]** | — |
| **ROI estimado** | — | — | **[Calcular ao vivo]** |

> *Preencher com dados reais fornecidos pelo cliente na reunião de descoberta.*

---

## 6. Cronograma de Implantação

| Fase | Prazo | Atividade |
| :--- | :--- | :--- |
| **PoC** | Dias 1–30 | 5 produtores, 20 talhões, 1 passaporte |
| **Onboarding Pleno** | Dias 31–60 | Todos os produtores, treinamento, talhões mapeados |
| **Operação Plena** | A partir do Dia 61 | Caderno, EPI, calibração e passaportes ativos |
| **Primeira Auditoria** | [Data da próxima auditoria] | Sistema pronto para auditoria completa |

---

## 7. Termos Comerciais

| Item | Condição |
| :--- | :--- |
| Validade da proposta | 30 dias a partir da data de emissão |
| Forma de pagamento | Mensal, via boleto ou PIX |
| Contrato mínimo | 12 meses (após PoC aprovada) |
| Cancelamento | Aviso com 30 dias de antecedência |
| PoC | Gratuita, sem vínculo de contrato |
| Suporte durante PoC | Ilimitado — equipe AgroSaaS conduz o onboarding |

---

## 8. Próximo Passo

Para dar início à PoC de 30 dias:

1. **[Exportadora]** indica os 5 produtores participantes
2. **AgroSaaS** entra em contato com os produtores para onboarding
3. Reunião de kick-off agendada para: **[Data]**

---

*Esta proposta foi preparada exclusivamente para [Exportadora] com base nas informações fornecidas em reunião de [data]. As funcionalidades descritas estão implementadas e em produção no AgroSaaS.*

*Contato comercial: [email] | [WhatsApp] | agrosaas.com.br*
