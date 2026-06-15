# Hedge Alerts Domain V2.2

## 1. Visão Geral
A modelagem de Alertas do Módulo de Hedge V2.2 atua como um sistema de monitoramento assíncrono que observa os **Snapshots Diários de Mark-to-Market (MtM)** e os **Volumes de Exposição** dos Contratos Futuros, notificando o gestor financeiro sobre riscos de PnL (Lucro/Prejuízo) ou falhas na integridade de dados (falta de cotação).

Este sistema **não executa liquidações** nem bloqueia caixa automaticamente (Margin Call real). É uma ferramenta de apoio a decisão.

## 2. Inventário de Funcionalidades Base do AgroSaaS

| Recurso | Status | Notas Técnicas |
| :--- | :---: | :--- |
| Módulo de Notificações | **EXISTE E ATENDE** | Serviço `NotificacaoService` e model `Notificacao` operacionais na API. |
| Preferências de Usuário | **EXISTE E ATENDE** | Model `NotificacaoPreferencia` permite filtrar níveis e canais. |
| Canais de Notificação | **EXISTE PARC.** | In-App (Sistema) e E-mail atendem. WhatsApp consta no model, mas não implementado. |
| Dashboard de Alertas | **NÃO EXISTE** | Painel específico de alertas de hedge precisará ser construído na UI. |
| Jobs/Cron | **EXISTE E ATENDE** | Job diário `gerar_snapshots_mtm.py` pode ser o gatilho para os cálculos de alerta. |

## 3. Classificação de Alertas

### 3.1 Níveis e Tipos
- **Informativo:** Operação concluída ou aviso sem risco direto (Ex: "Contrato X expira em 30 dias").
- **Aviso de Integridade:** `MTM_SKIPPED` devido a falha na obtenção de `CotacaoCommodity` (Preço Ausente).
- **Crítico (Risco/PnL):** Variação abrupta de PnL Diário ou PnL global ultrapassando o "Stop-Loss" (Ex: "PnL Negativo de Soja excedeu 15% do valor do contrato").
- **Exposição (Over-hedging):** A quantidade de `sc` (sacas) travadas em contratos futuros excede o volume físico colhido ou esperado na Safra associada.

### 3.2 Diferença entre Alerta de Risco e Margin Call
- **Alerta de Risco:** Envia uma notificação visual ou e-mail avisando: "Seu prejuízo na posição Vendida bateu R$ 50.000". O usuário toma ação manual.
- **Margin Call:** Fluxo financeiro onde a Corretora subtrai saldo da conta garantidora compulsoriamente. **Não será implementado na V2.2.**

## 4. Regras Candidatas para o MVP (V2.2)

1. **Variação MTM Negativa (Stop Loss Teórico):** Se o `mtm_valor` (negativo) representar mais que `X%` do volume financeiro total (`preco_contratado * quantidade`).
2. **Cotação Ausente (Integridade):** Disparado quando o HedgeSnapshotService emite log `MTM_SKIPPED` por falta de `CotacaoCommodity` há mais de 2 dias úteis consecutivos.
3. **Vencimento Próximo:** Contrato expira em 15 e 7 dias.

## 5. Arquitetura de Anti-Spam e Ownership

- **Ownership:** O domínio `Financeiro/Hedge` é o produtor do evento (Publisher). O domínio `Notificações` é o consumidor/distribuidor (Subscriber). O usuário é o Owner da visualização.
- **Deduplicação:** Regras de PnL devem ser disparadas apenas 1x ao dia, pós-fechamento do mercado (integradas ao `gerar_snapshots_mtm.py`). Não deve haver re-aviso contínuo na mesma faixa de perda.
- **Severidade e Leitura:** Alertas críticos aparecem em "Badges" vermelhos no topo do `MtMClient.tsx`. O descarte ("Marcar como Lido") no in-app desativa o alerta para o usuário.

## 6. O que NÃO FAZ PARTE da V2.2
- Margin Call Automática.
- Trigger B3 Live (Intraday alerts).
- Bloqueio operacional de novas vendas.
- Disparo via WhatsApp.
