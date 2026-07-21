-- SOIL-PLAN-EXEC-04L1 — PLANO DE REPARO (GERADO, NAO EXECUTADO)
-- Gerado a partir do dry-run SOIL-PLAN-EXEC-04L0 em 2026-07-21.
-- Fonte: docs/implementation/reports/data/SOIL-PLAN-EXEC-04L0-DRYRUN.csv
--
-- REGRAS DE SEGURANCA (spec secao 19):
--   * Cada bloco roda dentro de BEGIN;...ROLLBACK; -- NUNCA COMMIT.
--   * Precondicoes fortes: WHERE id=:operacao_id AND tenant_id=:tenant_id
--     AND status='REALIZADA' AND custo_total>0 AND production_unit_id IS NULL
--     (ou IS NOT NULL para o caso Grupo A) -- falha segura se o estado mudou
--     desde o dry-run.
--   * Inserts de CostAllocation usam NOT EXISTS cobrindo operation_execution_id,
--     source_id e tenant_id, para nao duplicar caso outro processo ja tenha
--     alocado o custo entre o dry-run e a execucao real (04L1).
--   * Apenas casos AUTO_* tem SQL executavel. Casos MANUAL_* aparecem
--     apenas como comentario informativo (nao geramos DML para eles).
--   * Nenhuma ProductionUnit e criada por este script (regra 04L0 secao 20).
--
-- Execucao real (fora de escopo desta etapa 04L0): remover ROLLBACK e trocar
-- por COMMIT somente apos revisao humana e reexecucao do dry-run para
-- confirmar que o estado do banco nao mudou (contagens antes/depois).

-- ============================================================
-- RESUMO DOS CASOS AUTO_* IDENTIFICADOS NO DRY-RUN (04L0)
-- ============================================================
-- AUTO_A : 1 caso  (PU presente, execucao presente, valor inequivoco)
-- AUTO_B : 0 casos (PU deterministica unica, execucao presente, valor inequivoco)
-- AUTO_C : 0 casos (PU deterministica unica, execucao ausente, criacao segura)
--
-- Todos os demais 150 registros do dry-run sao MANUAL_REVIEW (ver relatorio
-- 04L0, secao 11) e NAO tem DML gerado abaixo -- apenas o comentario de
-- contexto no final deste arquivo.

-- ============================================================
-- TENANT ef90c72c-b8c1-4f14-b67b-8ef15aff75ef
-- Caso AUTO_A: operacao 175c09fb-9487-4669-b847-f57e13f91d57
--   production_unit_id ja presente = f782fcc0-a89c-40f2-8baf-edcc2eacbb0a
--   execucao unica realizada = a0e29db2-a99e-4f65-b5a8-e9829d576223 (custo_real=500.00)
--   custo_total da operacao = 500.00 (convergente com custo_real da execucao)
--   Nenhum movimento de estoque associado (n_mov_estoque=0) -> sem risco FIFO
-- ============================================================
BEGIN;

-- Precondicao: reconfirma estado exato observado no dry-run antes de inserir.
-- Se a operacao mudou de estado (ex.: ja tem allocation, custo mudou, foi
-- cancelada), o INSERT abaixo simplesmente nao roda (WHERE NOT EXISTS +
-- filtro na propria condicao de origem via subselect).

INSERT INTO cost_allocations (
    id, tenant_id, production_unit_id, source, source_id,
    operation_execution_id, cost_category, amount, currency,
    allocation_date, allocation_method, allocation_basis, created_at
)
SELECT
    gen_random_uuid(),
    oa.tenant_id,
    oa.production_unit_id,
    'OPERATION_EXECUTION',
    NULL,
    oe.id,
    'OUTROS',              -- revisar categoria de custo real antes de executar (04L1)
    oa.custo_total,
    'BRL',
    oa.data_realizada,
    'DIRECT',
    NULL,
    CURRENT_TIMESTAMP
FROM operacoes_agricolas oa
JOIN operacoes_execucoes oe
    ON oe.operacao_id = oa.id
    AND oe.tenant_id = oa.tenant_id
    AND oe.status = 'REALIZADA'
WHERE oa.id = '175c09fb-9487-4669-b847-f57e13f91d57'
  AND oa.tenant_id = 'ef90c72c-b8c1-4f14-b67b-8ef15aff75ef'
  AND oa.status = 'REALIZADA'
  AND oa.custo_total > 0
  AND oa.production_unit_id = 'f782fcc0-a89c-40f2-8baf-edcc2eacbb0a'
  AND oe.id = 'a0e29db2-a99e-4f65-b5a8-e9829d576223'
  AND oe.custo_real = oa.custo_total
  -- garante que nao existe allocation por NENHUM dos dois vinculos historicos
  AND NOT EXISTS (
        SELECT 1 FROM cost_allocations ca
        WHERE ca.tenant_id = oa.tenant_id
          AND (ca.operation_execution_id = oe.id OR ca.source_id = oa.id)
  )
  -- exatamente uma execucao REALIZADA para a operacao (evita duplicidade
  -- se surgiu uma segunda execucao entre o dry-run e a execucao real)
  AND (SELECT count(*) FROM operacoes_execucoes oe2
       WHERE oe2.operacao_id = oa.id AND oe2.status = 'REALIZADA') = 1;

-- Verificacao pos-insercao (apenas leitura, dentro da mesma transacao):
-- SELECT * FROM cost_allocations WHERE operation_execution_id = 'a0e29db2-a99e-4f65-b5a8-e9829d576223';

ROLLBACK; -- NUNCA trocar por COMMIT nesta etapa (04L0 e somente dry-run).

-- ============================================================
-- CASOS MANUAL_REVIEW (150 registros) -- SEM DML, APENAS REFERENCIA
-- ============================================================
-- Ver CSV completo em SOIL-PLAN-EXEC-04L0-DRYRUN.csv para a lista integral
-- com tenant_id, operacao_id, categoria, motivo e risco de cada um.
--
-- Distribuicao por categoria (ver relatorio 04L0, secao 11):
--   MANUAL_CONTEXT_INCONSISTENT : 74  (PU presente mas sem OperacaoExecucao
--                                       REALIZADA valida -- nao ha valor
--                                       inequivoco para apropriar sem decisao
--                                       humana sobre a origem do custo)
--   MANUAL_MISSING_PU           : 68  (nenhuma ProductionUnit candidata
--                                       tenant+safra+area(+cultivo); 47 destes
--                                       concentrados no tenant de teste
--                                       aaaaaaaa-0000-0000-0000-000000000010)
--   MANUAL_REVERSED_OR_CANCELLED: 6   (execucoes canceladas ou origem
--                                       invalidada -- reparo automatico
--                                       proibido pela spec secao 13)
--   MANUAL_VALUE_DIVERGENCE     : 2   (custo_total diverge de soma das
--                                       execucoes/FIFO -- exige revisao de
--                                       qual valor e o correto, spec secao 11)
--
-- NENHUM destes casos deve ser reparado automaticamente. Qualquer SQL para
-- eles deve ser escrito manualmente em SOIL-PLAN-EXEC-04L1, apos decisao de
-- negocio registrada, um caso por vez, com evidencia própria.
