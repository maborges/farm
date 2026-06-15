# Auditoria de Execução: EXECUTION-HEDGE-04C

**Feature**: Reprocessamento Controlado de Mark-to-Market
**Status**: Concluído

## Escopo Realizado
1. **API**: Criado endpoint `POST /snapshots/reprocessar` sob blindagem `require_tenant_permission("financeiro:*")` para assegurar acesso gerencial.
2. **Camada de Serviço**: Adicionado método que varre janelas retroativas de até 31 dias executando o UPSERT idempotente de cálculo MTM para todos os contratos abertos aplicáveis.
3. **Auditoria**: Mapeado log customizado `HEDGE_MTM_REPROCESS` integrando os filtros e a justificativa fornecidos na ação administrativa.
4. **Testes**: Executada bateria unitária de `test_hedge_mtm_snapshot.py` que garantiu bloqueios temporais e exigência de preenchimento do motivo.
5. **Painel de Usuário**: Integração no `MtMClient.tsx` (Next.js/React) exibindo um dialog Modal (padrão shadcn/ui) no Header da página.

As documentações relativas à rotina do MTM em `docs/runbooks/hedge-mtm.md` foram atualizadas em conformidade.
