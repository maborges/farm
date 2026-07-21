# SOIL-PLAN-EXEC-04I — Remoção Coordenada da Criação de Despesa(OPERACAO_AGRICOLA)

## 1. Lógica anterior

`agricola/operacoes/service.py::criar()` (item "5. Registra Despesa no Financeiro"): sempre que
`custo_total_operacao > 0` e `status == "REALIZADA"`, criava um registro `Despesa` com
`origem_tipo="OPERACAO_AGRICOLA"`, `status="PAGO"`, `valor_pago` nunca preenchido, escolhendo
dinamicamente a primeira `PlanoConta` ativa de `categoria_rfb="CUSTEIO"`. Em seguida chamava
`validar_despesa_origem_leve` e `validar_despesa_automatica_unica_origem`.
`_sincronizar_efeitos_operacao` (chamado a cada `atualizar()`) buscava essa despesa via
`_buscar_despesa_existente` e reescrevia `descricao`, `valor_total`, `valor_pago`, datas,
`unidade_produtiva_id` e `cultivo_id` a cada edição da operação — mesmo quando a operação deixava
de ser `REALIZADA`.

## 2. Ponto removido

- `agricola/operacoes/service.py`, bloco "5. Registra Despesa no Financeiro" dentro de `criar()`
  (~30 linhas: query de `PlanoConta`, construção do `Despesa`, `session.add`/`flush`, e as duas
  chamadas de validação `validar_despesa_origem_leve`/`validar_despesa_automatica_unica_origem`).
- `_sincronizar_efeitos_operacao`: bloco que buscava e reescrevia a despesa a cada `atualizar()`.

## 3. Comportamento novo

Operações novas (criadas ou editadas a partir desta etapa) não criam nem atualizam
`Despesa(OPERACAO_AGRICOLA)` em nenhuma circunstância. O custo produtivo é representado
exclusivamente por `CostAllocation` (criada por `_garantir_execucao_e_allocation_leves`, já
existente e inalterada). `OperacaoAgricola.custo_total` permanece como fallback do dashboard
(04F) e, para dados históricos, da DRE (seção 6).

## 4. Alerta corrigido

`agricola/alertas/service.py::_detectar_allocation_sem_reflexo_economico`: removido o ramo
`op_stmt` (join `CostAllocation` → `OperacaoExecucao` → `OperacaoAgricola` com outer join em
`Despesa`, disparando quando não havia despesa ativa correspondente). Esse ramo tratava a
ausência de despesa como `RISCO_ECONOMICO`, o que se tornaria um falso positivo permanente para
toda operação nova. O ramo `estoque_stmt` (reconciliação `CostAllocation(INVENTORY_MOVEMENT)` x
`LancamentoFinanceiro`) foi preservado integralmente — continua sendo uma verificação econômica
válida, não relacionada a `Despesa(OPERACAO_AGRICOLA)`. O código do alerta
(`CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO`) foi mantido para não quebrar a taxonomia pública
(`core/services/analytics_taxonomy.py`) — apenas deixou de disparar pela condição aposentada.

## 5. Validadores ajustados

`validar_despesa_automatica_unica_origem` e `validar_despesa_origem_leve`
(`agricola/alertas/service.py`) **não foram alterados** — deixaram de ser chamados pelo fluxo de
criação de operação (as duas únicas chamadas foram removidas junto com o bloco de criação da
despesa), mas permanecem no código porque são genéricos (aceitam qualquer `origem_tipo`, via
`classificar_origem_despesa`) e continuam testados diretamente por
`tests/test_operational_workflow_governance_step03.py` e
`tests/test_operational_workflow_governance_step04.py`/`step09.py`, cobrindo outras origens
automáticas (ABASTECIMENTO, ORDEM_SERVICO, RH_DIARIA, RH_EMPREITADA). A detecção de duplicidade
em lote (`detectar_inconsistencias_reconciliacao_economica` → `DESPESA_AUTOMATICA_DUPLICADA_
MESMA_ORIGEM`, testada em `test_operational_workflow_governance_step08.py`) também não foi
alterada — continua válida como salvaguarda de qualidade de dados para qualquer despesa
automática existente, incluindo as históricas de `OPERACAO_AGRICOLA`.

## 6. Compatibilidade histórica

`agricola/dre/service.py::_consolidar_despesas` **não foi alterado**. A regra de precedência
permanece: excluir a despesa apenas quando existe `CostAllocation` correspondente (via
`OperacaoExecucao`); na ausência de allocation, a despesa (se existir e estiver ativa) continua
entrando na DRE. Como despesas novas não são mais criadas, essa regra passa a servir
exclusivamente para dados pré-04I — documentado explicitamente por um novo teste
(`test_dre_v1_preserva_fallback_historico_despesa_operacao_sem_allocation`, seção 12) que cria uma
`Despesa(OPERACAO_AGRICOLA)` manualmente (simulando dado legado) sem `CostAllocation` e confirma
que ela ainda é reconhecida como custo.

## 7. Comportamento da DRE

Sem alteração de código. Cenários confirmados por teste (existentes + o novo do item 6):
- Operação nova com `CostAllocation`: custo vem exclusivamente da allocation (nenhuma despesa
  jamais existiu para competir).
- Operação histórica sem `CostAllocation` + despesa ativa: despesa entra (fallback preservado).
- Operação cancelada (04G): `CostAllocation` removida, despesa histórica neutralizada
  (`ativo=False`) — nenhuma das duas entra.

## 8. Comportamento da reversão

`_reverter_efeitos_economicos_operacao` (04G) **não foi alterado** — já era condicional
(`if despesa is not None: neutraliza`), portanto já lidava corretamente com a ausência de
despesa. Após 04I isso deixa de ser uma exceção e passa a ser o caminho comum: para operações
novas, a reversão apenas reverte estoque e remove `CostAllocation`; para operações com despesa
legada (dado pré-04I), a neutralização (`ativo=False`, `status="CANCELADO"`) continua ocorrendo,
coberta por um novo teste dedicado (Cenário I, seção 12).

## 9. Comportamento financeiro genérico

`financeiro/services/dashboard_service.py`, `financeiro/services/relatorio_service.py` e
`financeiro/services/integracao_service.py` **não foram alterados**, conforme restrição do plano —
a correção é a ausência da causa raiz (a despesa nunca é criada), não um filtro artificial nesses
serviços. Comprovado por novo arquivo de teste
(`tests/test_operacao_nao_polui_financeiro_generico.py`, seção 12): criar uma operação agrícola
nova com custo não altera `total_pago_mes`/`total_a_pagar` do `DashboardService.resumo()` nem
`total_despesas`/`grupos` do `RelatorioService.livro_caixa()`.

## 10. Impacto em tarefas

`agricola/tarefas/service.py` **não foi alterado**. O bloqueio de exclusão por
`Despesa(OPERACAO_AGRICOLA, ativo=True)` continua ativo no código, inalterado — permanece
relevante apenas para dados históricos (operações novas nunca terão essa despesa, então esse
ramo da checagem naturalmente não dispara para elas; `CostAllocation` cobre o caso novo). Não foi
criado teste dedicado para este método (não havia teste pré-existente nem fixture pronta para
`SafraTarefa`/avaliação de exclusão — criar a infraestrutura do zero foi julgado fora do escopo
mínimo desta etapa); a garantia vem de revisão de código: nenhuma linha de
`agricola/tarefas/service.py` foi tocada.

## 11. Arquivos alterados

Produção:
- `services/api/agricola/operacoes/service.py` — remoção do bloco de criação de despesa em
  `criar()`; remoção do bloco de sincronização de despesa em `_sincronizar_efeitos_operacao`.
- `services/api/agricola/alertas/service.py` — remoção do ramo `op_stmt` (CostAllocation x
  Despesa) de `_detectar_allocation_sem_reflexo_economico`; preservado o ramo de estoque.

Testes reescritos:
- `tests/test_operacao_despesa_webhook.py` — reescrito integralmente: todas as expectativas de
  criação de despesa substituídas por expectativas de ausência de despesa + presença de
  `CostAllocation` equivalente (rastreabilidade, tenant isolation, tipo inválido).
- `tests/test_operacao_reversao_economica.py` — Cenário A renomeado/simplificado para operação
  nova sem despesa; Cenário B (idempotência), D (multi-tenant) e o teste de transição de status
  ajustados para não esperar despesa; novo Cenário I criado para reversão de despesa legada.
- `tests/test_multi_up_hardening_step01.py` — teste de derivação de `unidade_produtiva_id` via
  despesa substituído por verificação equivalente sobre `CostAllocation.production_unit_id` →
  `AreaRural.unidade_produtiva_id`; fixture ajustada para criar `ProductionUnit` real (ver
  riscos residuais, seção 14).
- `tests/test_operational_workflow_governance_step07.py` — teste que esperava o alerta
  `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO` disparar para `CostAllocation` sem despesa foi
  renomeado e invertido: agora confirma que o alerta **não** dispara mais nesse cenário.
- `tests/test_dre_agricola_v1.py` — `sujeito_reconciliacao`/`warnings_relevantes` do teste de
  precedência ajustados (o alerta aposentado não aparece mais); novo teste de fallback histórico
  adicionado (seção 6).

Testes adicionados (novo arquivo):
- `tests/test_operacao_nao_polui_financeiro_generico.py` — prova ausência de vazamento para
  `DashboardService` e `RelatorioService.livro_caixa`.

## 12. Testes reescritos e adicionados (resumo)

| Arquivo | Ação |
|---|---|
| `test_operacao_despesa_webhook.py` | Reescrito (5 testes) |
| `test_operacao_reversao_economica.py` | 4 testes ajustados + 1 novo (Cenário I) → 9 testes |
| `test_multi_up_hardening_step01.py` | 1 teste reescrito |
| `test_operational_workflow_governance_step07.py` | 1 teste invertido |
| `test_dre_agricola_v1.py` | 1 teste ajustado + 1 novo |
| `test_operacao_nao_polui_financeiro_generico.py` | Novo arquivo, 2 testes |

## 13. Testes executados

Baseline (antes da implementação):
```bash
.venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_operacao_reversao_economica.py \
  tests/test_dre_agricola_v1.py tests/test_dashboard_financeiro_safra.py tests/test_operacoes_validacao_fase.py \
  -q --tb=short
```
Resultado: **42 passed / 3 failed** (as 3 falhas conhecidas de `receita_total`).

Pós-implementação:
```bash
.venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_operacao_reversao_economica.py \
  tests/test_multi_up_hardening_step01.py tests/test_operational_workflow_governance_step07.py \
  tests/test_operational_workflow_governance_step08.py tests/test_operational_workflow_governance_step10.py \
  tests/test_dre_agricola_v1.py tests/test_dashboard_financeiro_safra.py tests/test_operacoes_validacao_fase.py \
  tests/test_operacao_nao_polui_financeiro_generico.py tests/test_fifo_estoque.py -q --tb=short
.venv/bin/ruff check agricola/operacoes/service.py agricola/alertas/service.py
```

## 14. Resultados

- Suíte completa pós-implementação: **66 passed / 4 failed**.
- As 4 falhas são pré-existentes e não relacionadas a esta etapa:
  - `test_step10_relatorio_lista_inconsistencias_e_sugestoes` — `NoReferencedTableError` em
    `compras_pedidos`/`estoque_depositos`, reproduzido de forma idêntica no `HEAD` anterior a esta
    mudança (isolamento de metadata SQLAlchemy ao rodar este arquivo sem importar os models de
    compras primeiro).
  - As 3 falhas de `receita_total` em `test_dashboard_financeiro_safra.py` (poluição entre testes
    que compartilham `TENANT_A_ID` fixo), documentadas desde 04E–04H.
- `ruff check agricola/operacoes/service.py agricola/alertas/service.py`: **93 erros**, contra
  baseline de **100** (medido via `git stash` do estado imediatamente anterior a esta etapa) —
  nenhuma violação nova; a contagem caiu porque código foi removido.
- Todos os arquivos de teste novos/reescritos: **0 violações novas** de `ruff` (comparado por
  diff de mensagens contra o baseline por arquivo).
- `git diff --check`: limpo.
- `git status --short`: apenas os arquivos listados na seção 11 e o relatório desta etapa.

## 15. Falhas pré-existentes

Confirmadas idênticas ao baseline via `git stash`, não corrigidas nesta etapa (fora de escopo,
conforme item 16 do plano): as 3 de `receita_total` e a de metadata em `test_operational_
workflow_governance_step10.py`.

## 16. Riscos residuais

- **Operações sem `ProductionUnit` resolvível ficam com custo produtivo sem representação
  econômica alguma.** Durante a reescrita de `test_multi_up_hardening_step01.py`, foi confirmado
  que quando `_resolve_production_unit_id` não encontra uma `ProductionUnit` para
  `(safra_id, talhao_id)` (cenário do fixture original do teste, que usava apenas `SafraTalhao`
  legado, sem `ProductionUnit`), `_garantir_execucao_e_allocation_leves` não cria `CostAllocation`
  — e, antes de 04I, a `Despesa(OPERACAO_AGRICOLA)` ainda era criada mesmo nesse caso (ela dependia
  apenas de `unidade_produtiva_id`, resolvido via `AreaRural`, não de `ProductionUnit`). Após 04I,
  essa mesma operação passa a não ter **nenhum** registro econômico — nem despesa, nem allocation.
  Isso não é uma regressão introduzida por 04I em termos de correção de dados (o custo real
  continua em `OperacaoAgricola.custo_total`, usado pelo fallback do dashboard), mas é uma
  **perda de visibilidade**: a DRE, que depende de `CostAllocation` ou de despesa para exibir
  custo por operação, deixa de mostrar qualquer valor para essas operações específicas. Trata-se
  de uma característica pré-existente do sistema de resolução de `ProductionUnit` (não modificado
  aqui, conforme restrição explícita do plano — "não ampliar escopo para redesenhar a criação de
  allocations, salvo defeito diretamente causado pela remoção") tornada mais visível pela remoção
  do fallback financeiro que a mascarava. Registrado aqui para avaliação futura; não corrigido.
- Nenhuma migration foi criada; nenhum dado histórico foi alterado; nenhuma alteração em ERP,
  Campo PWA, FIFO, `Despesa(COMPRA)`, ou nos três serviços financeiros genéricos.
- `validar_despesa_automatica_unica_origem`/`validar_despesa_origem_leve` seguem no código sem
  chamador para `OPERACAO_AGRICOLA` — não removidos por atenderem outras origens; nenhuma ação
  necessária a menos que uma limpeza de código morto seja priorizada no futuro (fora de escopo).

## 17. Decisão final

```
SOIL-PLAN-EXEC-04I
STATUS: GO
```

```
REGRA FINAL:
Operações agrícolas novas não criam Despesa(OPERACAO_AGRICOLA).
O custo produtivo é representado exclusivamente por CostAllocation.
Despesas operacionais históricas permanecem apenas para compatibilidade e podem ser
neutralizadas pela reversão econômica.
```

```
PRÓXIMO PASSO:
Executar auditoria final de fechamento do programa SOIL-PLAN-EXEC, incluindo
consistência econômica, fluxos históricos, falhas pré-existentes de testes e riscos
residuais fora do escopo — incluindo o risco de visibilidade de custo para operações
sem ProductionUnit resolvível (seção 16 deste relatório).
```
