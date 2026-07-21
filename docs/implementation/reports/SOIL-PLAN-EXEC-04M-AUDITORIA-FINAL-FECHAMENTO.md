# SOIL-PLAN-EXEC-04M — Auditoria Final de Fechamento do Programa

## 1. Resumo executivo
Auditoria de leitura confirma que o fluxo de NOVAS operações agrícolas está blindado: resolução determinística de ProductionUnit, CostAllocation obrigatória, rollback integral em falha, sem escritor paralelo de `OperacaoAgricola`, DRE/dashboard sem duplicação de custo, financeiro genérico não poluído, Campo PWA cobre o mesmo caminho de serviço. Veredicto: **GO**.

## 2. Decisão sobre histórico
SOIL-PLAN-EXEC-04L permanece ENCERRADO SEM REPARO HISTÓRICO. Os 151 registros de 04J/04L0 são dados de dry run/teste; não foram tocados, migrados nem usados como fixture de aceite nesta auditoria.

## 3. Arquitetura econômica final
`OperacaoAgricola` (REALIZADA, custo>0) → `_resolve_production_unit_id` → `OperacaoExecucao` → `registrar_cost_allocation` (`CostAllocation`) → consumida por DRE (`agricola/dre/service.py`) e Dashboard (`agricola/dashboard/service.py`). Nenhuma `Despesa(OPERACAO_AGRICOLA)` é criada no fluxo novo.

## 4. Validação 04E
`agricola/dre/service.py:686` exclui explicitamente `despesa.origem_tipo == "COMPRA"` do custo operacional agrícola — confirmado por leitura de código, sem alteração.

## 5. Validação 04F
`agricola/dashboard/service.py:236-253`: por operação, usa soma de `CostAllocation` via `OperacaoExecucao` quando existente; senão fallback `op.custo_total`. Escolha é por `operacao_id` (dict lookup), não soma cumulativa — sem dupla contagem confirmada por leitura.

## 6. Validação 04G
`_reverter_efeitos_economicos_operacao` (service.py:354-397) reverte estoque, deleta `CostAllocation` vinculada (via `operation_execution_id`/`source_id`), neutraliza `Despesa` histórica (`ativo=False`, `status=CANCELADO`) e remove a execução — tudo na mesma transação/flush. Comentário no código já documenta idempotência.

## 7. Validação 04I
`_buscar_despesa_existente` (linha 403) e comentário linha 614 confirmam: leitura de compatibilidade apenas; nenhuma escrita de `Despesa(OPERACAO_AGRICOLA)` no fluxo de criação/atualização/allocation.

## 8. Validação 04K
`_resolve_production_unit_id` (linhas 262-330): sem `.first()`/ordenação por data para desambiguar; bloqueio explícito de ambiguidade e ausência via `BusinessRuleError` quando `REALIZADA`+`custo>0`. `_garantir_execucao_e_allocation_leves` (644-835): falha em `registrar_cost_allocation` é capturada e relançada como `BusinessRuleError` (linha ~825), garantindo rollback. `atualizar()` revalida PU via `validate_production_unit_context` ao trocar `production_unit_id` (linhas 1205-1217).

## 9. Caminhos de entrada
```
rg -n "OperacaoAgricola\(" services/api      → apenas agricola/operacoes/service.py:989 (produção) + seed.py (dev seed)
rg -n "OperacaoService\("                    → router.py, campo/service.py:298, agricola/tarefas/service.py:621
rg -n "\.criar\(" agricola campo             → campo/service.py:298 e tarefas/service.py:622 delegam a OperacaoService().criar()
rg -n "\.atualizar\(" agricola campo         → agricola/operacoes/router.py:295 único ponto de atualização de operação
```
Nenhum escritor paralelo de `OperacaoAgricola` fora de `OperacaoService`. Campo PWA (`campo/service.py:298`) e Tarefas (`tarefas/service.py:622`) reutilizam o mesmo `.criar()`.

## 10. Cenário positivo
Não foi criado dado novo isolado nesta auditoria (auditoria predominantemente de leitura); a garantia decorre da suíte de testes existente (seção 20), que já cobre criação com PU válida, execução única e allocation única, e passou integralmente (exceto falha de fixture pré-existente não relacionada).

## 11. Cenários de bloqueio (ausência/ambiguidade/cross-tenant/falha allocation)
Confirmados por leitura de código (seção 8) e por `tests/test_operacao_production_unit_enforcement.py` (suíte completa, 0 falhas nesta execução).

## 12. Atomicidade
`router.py` só chama `session.commit()` após retorno bem-sucedido do service; `atualizar()` executa `await self.session.rollback()` explicitamente ao capturar `BusinessRuleError` antes de propagar. `BaseService.update()` usa apenas `flush()`, nunca commit — consistente com o padrão do projeto.

## 13. Idempotência
`_reverter_efeitos_economicos_operacao` e `_garantir_execucao_e_allocation_leves` usam buscas por vínculo existente (`_buscar_execucao_existente`, `_buscar_allocation_existente`) antes de criar, evitando duplicidade em reentradas/retries — confirmado por leitura; validado indiretamente pelos testes de `test_operacao_reversao_economica.py` (passou).

## 14. Reversão
Ver seção 6. Segunda chamada é no-op (nenhuma execução/allocation remanescente a reverter).

## 15. DRE
`agricola/dre/service.py` usa `CostAllocation` como fonte oficial (`fonte_oficial="CostAllocation"`, linha 549) e emite alerta quando há movimento com custo sem allocation (linha 886) — não adiciona fallback à DRE, conforme exigido.

## 16. Dashboard
Ver seção 5. Fallback existe apenas por operação sem allocation, não somado.

## 17. Financeiro genérico
`test_operacao_nao_polui_financeiro_generico.py` passou integralmente — confirma que operação agrícola não cria Despesa nem Livro Caixa automaticamente.

## 18. Campo PWA
`campo/service.py:298` chama `OperacaoService(...).criar()` sem informar `production_unit_id`, dependendo 100% da resolução determinística do backend — mesmo caminho e mesmas garantias do fluxo web. Não há suíte de testes dedicada a "tests/test_campo_*operacao*" identificada no repositório; cobertura é por inspeção de código, não por execução de teste dedicado ao Campo.

## 19. Revisão de atualizar()/_atualizar_efeitos_operacao
Ordem: busca estado atual → valida calibração/sanitário → normaliza payload → revalida PU se trocada → `try/except BusinessRuleError: rollback` envolvendo `_atualizar_efeitos_operacao` → dentro dela, `super().update()` (flush) seguido de reversão de efeitos (se saiu de REALIZADA) ou reaplicação de insumos/allocation (se entrou/permanece REALIZADA), sincronização final. Nenhum commit no meio; erros não-`BusinessRuleError` propagam sem rollback explícito local, mas isso é responsabilidade legítima do router/middleware de sessão (não corrige, pois já é o padrão consistente do projeto — nenhuma commit precoce foi encontrada). **Classificação: APROVADO.**

## 20. Testes
```
tests/test_operacao_production_unit_enforcement.py, test_operacao_reversao_economica.py,
test_operacao_nao_polui_financeiro_generico.py, test_dre_agricola_v1.py, test_fifo_estoque.py,
test_operacoes_validacao_fase.py, test_multi_up_hardening_step01.py → 63 passed
test_dashboard_financeiro_safra.py → 3 failed (fixture, ver §21)
test_operational_workflow_governance_step02/04/07/08/09.py → 26 passed
```
Total: 89 passed, 3 failed.

## 21. Baseline
As 3 falhas em `test_dashboard_financeiro_safra.py` (`test_resumo_financeiro_safra_valido`, `test_resumo_financeiro_safra_sem_operacoes`, `test_resumo_roi_calculado`) apresentam `receita_total` inflada em exatamente +30000 em todos os casos — assinatura de poluição de fixture entre testes (vazamento de receita de romaneio entre casos), exatamente a falha conhecida citada na especificação. Classificação: **FALHA DE FIXTURE/ISOLAMENTO PRÉ-EXISTENTE**, não é regressão do SOIL-PLAN-EXEC (não relacionada a CostAllocation/PU). Não corrigida (fora de escopo — correção de fixture não é defeito objetivo do fluxo de operações).

## 22. Ruff
`ruff check agricola/operacoes/service.py agricola/dashboard/service.py agricola/dre/service.py` → 109 erros, todos pré-existentes (E501 line-too-long majoritário, mais E712/F541/UP017/I001 pontuais), nenhum introduzido por esta auditoria (nenhum código foi alterado). `git diff --check` limpo; `git status --short` mostra apenas alterações já presentes das etapas 04E-04L0.

## 23. Riscos residuais
(a) Falha de fixture em `test_dashboard_financeiro_safra.py` deve ser corrigida em manutenção futura de testes, sem risco econômico. (b) Ausência de suíte de teste automatizada dedicada ao Campo PWA para criação de operação (cobertura hoje é só por inspeção de código); recomenda-se item de backlog não bloqueante. (c) Débito de lint pré-existente (109 ocorrências, majoritariamente estilo) não bloqueia o encerramento.

## 24. Decisão final
```
SOIL-PLAN-EXEC
STATUS: CONCLUÍDO
```
```
HISTÓRICO: Não reparado por se tratar de dados de dry run/teste.
DADOS NOVOS: Protegidos por resolução determinística, enforcement local, CostAllocation obrigatória e rollback integral.
ARQUITETURA ECONÔMICA FINAL: OperacaoAgricola → OperacaoExecucao → CostAllocation → DRE e Dashboard. Despesa genérica não é criada para operação agrícola.
```

**Veredicto de 04M: GO COM RESSALVAS** — sem risco econômico novo; ressalvas são falha de fixture pré-existente (não corrigida, fora de escopo) e ausência de suíte de teste dedicada ao Campo PWA (cobertura por inspeção). Nenhuma correção de código foi realizada nesta etapa (nenhum defeito objetivo encontrado).
