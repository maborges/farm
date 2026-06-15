# Auditoria Discovery: HEDGE-V2.2-DISCOVERY (Alertas)

**Fase:** Discovery e Planejamento (Pré-Execução)
**Objetivo:** Estabelecer a modelagem base para os alertas de Hedge, Exposição e MTM baseados em snapshots.

## 1. Avaliação de Viabilidade (Inventário)

Durante a fase de discovery, o código base foi inspecionado em `/services/api/notificacoes`. 
Foi atestado que o AgroSaaS já possui a infraestrutura base (Tabelas: `notificacoes`, `notificacoes_preferencias`), que conta com os campos necessários de Severidade (`nivel`), Estado (`lida`), e Direcionamento (`tenant_id`, `usuario_id`).

O disparo dos alertas poderá ser facilmente injetado ao final do script cron `gerar_snapshots_mtm.py` (ou em um job subsequente `processar_alertas_mtm.py`).

## 2. Decisões de Arquitetura Aprovadas (Roadmap)

### MVP - V2.2 (Próxima Fase - EXECUTION-HEDGE-05)
- **Gatilhos de Integridade:** Alerta quando houver `MTM_SKIPPED` repetido (falta de cotação).
- **Gatilho de Vencimento:** Alerta visual 15 dias antes da expiração do `ContratoFuturo`.
- **Gatilho de PnL Crítico:** Envio de In-App notification se o PnL for negativo acima de uma trava percentual pré-definida no momento da criação do contrato (ex: 15%).
- **UI:** Injeção de alertas no topo do painel `MtMClient.tsx` ou em uma aba dedicada `Alertas`.

### Futuro - V2.3
- **Exposição (Over-hedging):** Cruzamento da produção física lançada no módulo `Agricola` vs Posição Travada. Requer dependência pesada de outro módulo, por isso fica fora da V2.2.
- **Relatório Semanal de Hedge:** E-mail com a exposição agregada.

### Fora de Escopo Permanente (V3+)
- Integrações diretas de liquidação compulsória (Margin Call) com B3 ou Corretoras via FIX Protocol.

## 3. Riscos Mitigados
- **Ansiedade Financeira:** Evitada com o envio de notificação apenas D+1 (via snapshot noturno), impedindo alertas intraday (flutuações irreais de curtíssimo prazo).
- **Falso Positivo de Cotação:** A tolerância D-1 e D-2 do Snapshot previne que feriados bancários gerem alarmes falsos de "Sem Cotação".
- **Spam:** Resolvido pela infraestrutura de `notificacoes_preferencias`, garantindo apenas o envio por In-App na categoria MEDIO/BAIXO, ou limitando e-mails a resumos diários dependendo da flag do usuário.

## 4. Conclusão da Discovery
A base técnica atual suporta de forma aderente a criação dos alertas, exigindo mínimo esforço na camada de notificação. Todo o desenvolvimento focará em lógica matemática no Job Cron, e em Componentes de visualização no Dashboard Next.js.

> **Status Final:** O EXECUTION-HEDGE-05 (Desenvolvimento dos Alertas MVP) está oficialmente **AUTORIZADO** a começar, focando apenas nos três gatilhos definidos na V2.2.
