# Auditoria Executiva: EXECUTION-HEDGE-05

**Feature**: Alertas MVP de Hedge
**Status**: Concluído (APROVADA)

## Implementação Realizada
1. **Integração NotificacaoService:** Sem criar tabelas ou endpoints redundantes, injetamos alertas usando o serviço central de Notificações.
2. **Alertas Suportados:**
   - **HEDGE_CONTRACT_EXPIRING** (Vencimento próximo em 15 e 7 dias)
   - **HEDGE_MTM_PRICE_MISSING** (Ausência consecutiva de 2 dias de cotações)
   - **HEDGE_CRITICAL_PNL** (Perda teórica excedendo a barreira de 15% sobre o valor principal)
3. **Auditoria:** Eventos registrados na trilha de `TenantAuditLog` sob a categoria `HEDGE_ALERT_CREATED`.
4. **Visibilidade UI:** Cards nativos condicionados à existência de notificações de risco ativas (via cache do TanStack Query em `MtMClient`).

## Riscos Remanescentes e Recomendações
- O limite de Stop-Loss (PnL) é fixo em **15%**. É imperativo desenvolver na próxima fase um campo parametrizável pelo cliente em cada `ContratoFuturo`.
- Recomenda-se iniciar a arquitetura da fase **HEDGE-V2.3**, visto que ela abordará o desafio mais analítico de todos: O cruzamento do *Hedge* financeiro com as *Projeções Agrícolas* (Exposição Física / Over-hedging). O MTM agora tem infraestrutura total, faltando apenas a análise de exposição cruzada.
