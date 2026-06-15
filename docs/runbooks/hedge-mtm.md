# Runbook: Gerador de Snapshots de MTM (Hedge)

Este documento detalha a infraestrutura de Snapshots do Mark-to-Market de Hedge V2.

## Visão Geral
O MTM é reavaliado diariamente na data de fechamento para contratos futuros `ABERTO`s, sem impactar o ledger contábil de contas a receber/pagar, operando estritamente como projeção de lucro/prejuízo não realizado (PnL).

## O Job: `gerar_snapshots_mtm.py`
**Local:** `services/api/scripts/jobs/gerar_snapshots_mtm.py`
**Frequência Recomendada:** Diária (Cron), sugerido fim do dia ou madrugada.
`30 0 * * * cd /opt/lampp/htdocs/farm/services/api && .venv/bin/python scripts/jobs/gerar_snapshots_mtm.py`

### Mecânica de Preço:
1. **D-0:** Busca `CotacaoCommodity` referente à data de processamento.
2. **Fallback (D-1+):** Caso o mercado estivesse fechado (feriado/fds), pega a última cotação anterior disponível.
3. **Skip:** Se não existir preço em todo o histórico, ele pula o contrato e registra em auditoria `SNAPSHOT_SKIPPED_NO_PRICE` para alertar o Backoffice. Nunca usar zero.

### Fórmulas Aplicadas:
- Posição Vendida (Short): `MtM = (preco_contratado - preco_mercado) * quantidade_aberta`
- Posição Comprada (Long): `MtM = (preco_mercado - preco_contratado) * quantidade_aberta`

### Upserts e Reprocessamento
O job foi desenhado para ser **idempotente**. Ele insere ou atualiza (Upsert) o `HedgePositionSnapshot` baseado na chave única `(tenant_id, contrato_futuro_id, data_referencia)`.
Se precisar corrigir um fechamento do passado:
1. Atualize a `CotacaoCommodity` na data passada.
2. Execute o job com a flag `--data YYYY-MM-DD`.

### Auditoria
Todas as operações do `HedgeSnapshotService` gravam logs rastreáveis em `tenant_audit_log` sob o resource `hedge_position_snapshots_v2`.
- `SNAPSHOT_CREATED`: Primeiro cálculo do dia.
- `SNAPSHOT_UPDATED`: Retificações do mesmo dia.

## Consumo no Frontend (UI)
**Endpoint Oficial:** `GET /api/v1/financeiro/hedge/snapshots`
**Rota no Frontend:** `/dashboard/financeiro/hedge/mtm`

O painel de visualização utiliza `Server Components` (`apiFetchServer`) na carga inicial e `TanStack Query` (`MtMClient.tsx`) para paginação e ordenação de tabelas dinâmicas.

Apesar da natureza auditável das projeções, a UI agora oferece a funcionalidade restrita de **Reprocessamento de MtM** (adicionada na fase EXECUTION-HEDGE-04C). Esta funcionalidade permite:
- Executar recálculos retroativos com limite máximo de 31 dias por chamada.
- O acesso exige permissões administrativas (`financeiro:*`).
- Todas as ações disparam auditoria sob a chave `HEDGE_MTM_REPROCESS` informando o intervalo de datas e a justificativa fornecida pelo gestor.
- Não existem exclusões (DELETE), apenas inserções ou atualizações (UPSERT).

### Troubleshooting Reprocessamento
- **"Periodo muito longo"**: Há trava máxima de 31 dias por reprocessamento na API para não estourar a memória.
- **Auditoria**: O log gerado será `HEDGE_MTM_REPROCESS` indicando a quantidade de dias e snapshots afetados.

## 4. Alertas de Risco (V2.2)

O AgroSaaS Hedge avalia três regras de risco no fechamento de MTM (após `processar_tenant`):
1. **Risco Operacional (Missing Price)**: Ausência de cotações (`MTM_SKIPPED`) por 2 dias seguidos. (Severidade: WARNING).
2. **Risco de Vencimento**: Contratos futuros faltando exatamente 15 e 7 dias. (Severidade: INFO).
3. **Risco Financeiro (PnL Crítico)**: PnL Negativo não realizado ultrapassou o teto fixo de 15% sobre a receita teórica total. (Severidade: DANGER).

Estes alertas dependem do **NotificacaoService** nativo e respeitam a configuração do usuário (E-mail/App/WhatsApp). Todos os disparos geram auditoria `HEDGE_ALERT_CREATED`.
