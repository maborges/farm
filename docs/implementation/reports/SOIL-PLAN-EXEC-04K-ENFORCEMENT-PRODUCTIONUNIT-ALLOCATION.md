# SOIL-PLAN-EXEC-04K — Enforcement de ProductionUnit e bloqueio de novos custos sem CostAllocation

## 1. Fluxo anterior

`OperacaoService.criar`/`atualizar` resolviam `production_unit_id` via `_resolve_production_unit_id`
(match por `safra_id + talhao_id`, `ORDER BY status='ATIVA' DESC, created_at DESC`, `.first()`).
Quando nenhuma candidata existia, a operação era persistida com `production_unit_id = NULL`. Em
`_garantir_execucao_e_allocation_leves`, se `custo_total > 0` e `production_unit_id is None` e o tipo
exigia allocation, um finding `RISCO_ECONOMICO` era registrado com `allow_block=True`, mas como
`WORKFLOW_ENFORCEMENT_MODE = WARNING_ONLY` está hardcoded, `deve_bloquear_severidade` sempre
retornava `False` — nenhuma exceção era lançada. O mesmo valia para falha em `registrar_cost_allocation`.

## 2. Pontos de entrada mapeados

`OperacaoService.criar` (produção, `agricola/operacoes/service.py`), `OperacaoService.atualizar`
(edição/transição de status), ambos únicos escritores de `OperacaoAgricola` REALIZADA com custo.
Rotas web (`agricola/operacoes/router.py`) e Campo PWA (`campo/service.py::criar`, aplicação
agrícola) chamam esses métodos — nenhum caminho paralelo de escrita foi encontrado.

## 3. Resolução anterior (recapitulação de 04J)

Ver seção 1. Ambiguidade era resolvida silenciosamente por `created_at DESC` — nunca bloqueava.

## 4. Resolução determinística implementada

`_resolve_production_unit_id` agora: Caso A (informado) usa `validate_production_unit_context`
sem alterações (já validava tenant/safra/área/cultivo, sem fallback). Caso B (ausente): busca todas
as candidatas por `tenant+safra+área(+cultivo quando informado)`; se única, usa; se múltiplas,
reduz para as `ATIVA`; se ainda múltiplas, é ambiguidade. Nenhuma decisão por `first()`/`created_at`.

## 5. Regra de ambiguidade

Duas ou mais candidatas igualmente válidas (mesma prioridade) sem decisão determinística possível
= ambíguo. Se a operação será `REALIZADA` com `custo_total > 0`, lança `BusinessRuleError`
("múltiplas ProductionUnit válidas... informe production_unit_id"). Caso contrário (sem custo ou
não REALIZADA), preserva comportamento antigo (persiste `NULL`, loga warning) — não há mudança de
contrato para operações planejadas/sem custo.

## 6. Bloqueio direcionado

Dois pontos passaram a `raise BusinessRuleError` **incondicionalmente** (não dependem de
`WORKFLOW_ENFORCEMENT_MODE`, que permanece `WARNING_ONLY` global): (a) `custo>0` + `production_unit_id`
ausente + `regra.exige_cost_allocation`; (b) falha de `registrar_cost_allocation` mesmo com PU
presente. O finding/notificação de observabilidade (`registrar_e_aplicar_enforcement`) continua sendo
emitido antes do `raise` — preserva o rastro de auditoria existente.

## 7. Criação obrigatória de allocation

Sem mudança na chamada a `registrar_cost_allocation` em si; a diferença é que uma falha agora aborta
a transação (item 6b) em vez de apenas registrar finding e devolver `(execucao, None)`.

## 8. Atomicidade

`criar()` já envolvia todo o corpo em `try/except BusinessRuleError: rollback + raise` — as novas
exceções são cobertas automaticamente. `atualizar()` não tinha esse padrão; foi refatorado extraindo
a lógica de efeitos econômicos para `_atualizar_efeitos_operacao` (método auxiliar), chamado dentro de
um `try/except BusinessRuleError` que executa `await self.session.rollback()` antes de repropagar —
espelhando o padrão de `criar()`. Nenhum helper (`_garantir_execucao_e_allocation_leves`,
`_reverter_*`, etc.) executa commit — confirmado por leitura; commit é sempre do chamador
(`criar`/router) ou do teste.

## 9. Estoque/FIFO

Não houve mudança na ordem física de consumo (ainda ocorre antes da resolução final de allocation em
`criar`, por contrato existente), mas como qualquer falha de PU/allocation agora propaga
`BusinessRuleError`, o `rollback()` (explícito em `criar`, e via `_atualizar_efeitos_operacao` em
`atualizar`) desfaz o consumo FIFO/ledger na mesma transação. Testado explicitamente (cenário G/H).

## 10. Campo PWA

`campo/service.py` chama `OperacaoService.criar` sem tratamento especial de `BusinessRuleError` —
a exceção propaga até o `exception_handler(BusinessRuleError)` já registrado em `main.py:654`, que
mapeia para uma resposta HTTP controlada (não 500). Nenhuma alteração foi necessária no contrato
offline; o Campo, ao não enviar `production_unit_id`, já dependia da resolução automática (Caso B),
que agora é apenas mais estrita.

## 11. Idempotência

Reaproveitada a busca existente por `CostAllocation` (`_buscar_allocation_existente`) e por
`OperacaoExecucao` (`_buscar_execucao_existente`) — nenhuma mudança nesse mecanismo. Teste J confirma
que uma edição não-econômica após criação bem-sucedida não duplica allocation.

## 12. Arquivos alterados

- `services/api/agricola/operacoes/service.py` (produção): `_resolve_production_unit_id`
  reescrito; dois pontos de bloqueio direcionado em `_garantir_execucao_e_allocation_leves`;
  `atualizar()` refatorado com `_atualizar_efeitos_operacao` + rollback explícito; revalidação de
  `production_unit_id` explícito em edição.
- `services/api/tests/test_operacao_production_unit_enforcement.py` (novo).
- `services/api/tests/test_operational_workflow_governance_step02.py` e `..._step04.py`: ajustados
  (ver seção 16) — os dois únicos testes cujo comportamento antigo dependia do gap agora corrigido.
- Este relatório.

`agricola/alertas/service.py` **não** foi alterado — `WORKFLOW_ENFORCEMENT_MODE` continua
`WARNING_ONLY` global; o bloqueio é 100% local ao service de operações.

## 13. Testes adicionados

`test_operacao_production_unit_enforcement.py`, 11 testes cobrindo os cenários A, B, C, D, E, F,
G+H (combinados), I, J, K, N da especificação (M é coberto indiretamente pelo handler global de
`BusinessRuleError` já existente, validado por inspeção, não por teste HTTP dedicado — fora do
escopo de testes unitários de service).

## 14. Testes executados

```
tests/test_multi_up_hardening_step01.py tests/test_operacao_despesa_webhook.py
tests/test_operacao_reversao_economica.py tests/test_dre_agricola_v1.py
tests/test_dashboard_financeiro_safra.py tests/test_operacoes_validacao_fase.py
tests/test_fifo_estoque.py tests/test_operacao_production_unit_enforcement.py
tests/test_operational_workflow_governance_step01/02/03/04/07/08/09/10.py
tests/test_operacao_nao_polui_financeiro_generico.py
```

## 15. Resultados

Baseline (antes de 04K, suíte pedida na seção 20 da spec): 55 passed, 3 failed (pre-existentes,
`test_dashboard_financeiro_safra.py`). Após 04K, mesma suíte + arquivo novo: 79 passed, 3 failed
(mesmos 3 pre-existentes). Suíte de governança (`step01–step10`) + `test_operacao_nao_polui...`:
35 passed, 4 failed inicialmente — 2 eram regressões reais causadas por 04K (esperadas: o
comportamento antigo *era* o gap) e foram corrigidas ajustando os testes (`step02`,
`step04` — ver seção 16); as outras 2 (`step01`, `step10`) foram confirmadas **pre-existentes e
independentes de 04K** via `git stash` (falham identicamente sem as alterações, nesta combinação de
arquivos — erro de resolução de metadata SQLAlchemy por ordem de import, não relacionado a
ProductionUnit/CostAllocation). Novo arquivo: 11/11 passed.

## 16. Falhas pré-existentes (não corrigidas, fora de escopo)

- `test_dashboard_financeiro_safra.py` (3 testes): poluição de fixture de tenant compartilhado,
  documentada em relatórios anteriores.
- `test_operational_workflow_governance_step01.py::test_detector_classifica_inconsistencias_operacionais`
  e `step10.py::test_step10_relatorio_lista_inconsistencias_e_sugestoes`: `NoReferencedTableError`
  de metadata SQLAlchemy (tabelas de frota/estoque não registradas nessa combinação de imports de
  teste) — confirmado idêntico antes e depois de 04K via `git stash`.
- `step02.py::test_operacao_realizada_com_custo_sem_allocation_gera_warning` e
  `step04.py::test_warning_only_nao_bloqueia_risco_economico_novo`: **ajustados** (não são mais
  falhas) — seu comportamento antigo assumia exatamente o gap que 04K fecha (operação REALIZADA com
  custo sem PU deveria apenas gerar warning). Atualizados para `pytest.raises(BusinessRuleError)`,
  com comentário explicando a mudança de contrato.

## 17. Riscos residuais

- Os 47/103 registros históricos identificados em 04J permanecem intocados (fora de escopo — 04L).
- Resolução automática ainda depende de `ProductionUnit` pré-cadastrada; tenants operando apenas com
  `SafraTalhao` legado (sem `CultivoArea`/`ProductionUnit`) passam a ser bloqueados ao tentar
  concluir operações com custo — esperado e intencional (é exatamente o gap fechado), mas pode
  gerar atrito operacional para esses tenants até que cadastrem `ProductionUnit`.
- `atualizar()` foi refatorado (extração de método); comportamento externo preservado e coberto por
  toda a suíte de regressão, mas é uma mudança estrutural não trivial — revisão adicional de código
  recomendada antes de produção.
- Ambiguidade em Caso B com `cultivo_id` ausente no payload mas presente nas `ProductionUnit`
  cadastradas pode bloquear cenários de consórcio legítimos que antes "funcionavam" por sorte
  (primeira candidata por `created_at`); é o comportamento correto pretendido pela spec, mas requer
  comunicação ao time de suporte/onboarding.

## 18. Decisão final

Bloqueio direcionado implementado sem tocar `WORKFLOW_ENFORCEMENT_MODE` global, sem criar migration,
sem alterar DRE/dashboard/dados históricos, com atomicidade garantida em `criar` e `atualizar`,
11 testes novos cobrindo os cenários centrais da spec, e apenas 2 testes existentes ajustados
(ambos por dependerem do próprio gap). Regressões pré-existentes documentadas e não tocadas.

```
SOIL-PLAN-EXEC-04K
STATUS: GO
```

**REGRA FINAL:** Nenhuma nova operação agrícola pode ficar `REALIZADA` com `custo_total > 0` sem
`ProductionUnit` resolvida deterministicamente (sem ambiguidade, sem cross-tenant) **e** sem
`CostAllocation` criada com sucesso — qualquer falha nesse caminho aborta a transação inteira
(rollback total: estoque, execução, allocation, status). O bloqueio é local ao domínio de operações
agrícolas e independe do modo global `WORKFLOW_ENFORCEMENT_MODE` (que continua `WARNING_ONLY`).

**PRÓXIMO PASSO:** SOIL-PLAN-EXEC-04L — reparo controlado dos 103 registros históricos
(`REALIZADA` + custo sem `CostAllocation`, 47 dos quais também sem `ProductionUnit`) identificados
em 04J, com estratégia explícita de mapeamento seguro e sem migração automática/implícita de
`ProductionUnit`.
