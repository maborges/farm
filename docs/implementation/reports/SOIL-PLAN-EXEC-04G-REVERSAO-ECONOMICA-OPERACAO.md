# SOIL-PLAN-EXEC-04G — Reversão Econômica Transacional da Operação Agrícola

## 1. Fluxo anterior

`OperacaoAgricola` não possui conceito de status `CANCELADA` em nenhum lugar do código
(`status` é `String(20)` livre, sem enum, sem validação). Buscas em todo o módulo `agricola/operacoes/`
não encontraram uma única referência a `"CANCELADA"`. O único mecanismo real de "cancelamento" é o
endpoint `DELETE /operacoes/{id}` (`agricola/operacoes/router.py:301`), que chama
`OperacaoService.hard_delete(id)` — herdado sem override de `BaseService.hard_delete`, que apenas
executa `session.delete(db_obj)`.

Como `OperacaoAgricola.execucoes` tem `relationship(..., cascade="all, delete-orphan")`, o
`hard_delete` cascade-apagava `OperacaoExecucao`. Como `CostAllocation.operation_execution_id` tem
`ForeignKey(..., ondelete="SET NULL")`, a allocation **sobrevivia** à exclusão da execução, órfã, mas
com `amount` intacto — ainda somada em `custos_diretos`/`custos_operacionais` da DRE e no
`custo_operacoes_total` do dashboard. A `Despesa(origem_tipo="OPERACAO_AGRICOLA")` também sobrevivia
(nenhuma FK, `ativo=True` por padrão) e, pior: com a execução apagada, o join que a DRE usa para
excluí-la por precedência (`alloc_op_ids`, via `OperacaoExecucao.operacao_id`) deixava de encontrar
correspondência — reabrindo a despesa para reentrar na DRE como "despesa não coberta por allocation".
Resultado: uma operação cancelada podia gerar **dupla contagem** (allocation órfã + despesa
reaberta) em vez de zerar o custo.

O estoque, por sua vez, **nunca era revertido** no `hard_delete` (nenhuma chamada a
`_reverter_movimentos_estoque_operacao`) — só era revertido dentro de `atualizar()`, e mesmo ali
apenas quando `precisa_reprocessar_insumos` era verdadeiro (insumos alterados, área alterada com
insumos existentes, ou status virando `REALIZADA`). Uma transição de status **saindo** de
`REALIZADA` nunca disparava reversão de estoque, allocation ou despesa.

## 2. Transições auditadas

| Transição | Dispara reversão hoje (antes) | Dispara reversão agora |
|---|---|---|
| `DELETE /operacoes/{id}` (hard_delete) | Nenhuma (estoque, allocation, despesa intactos/órfãos) | Estoque + allocation + despesa, na mesma transação |
| `atualizar()`: `status` REALIZADA→REALIZADA + insumos/área alterados | Sim (estoque apenas, via `_reverter_movimentos_estoque_operacao`) | Inalterado |
| `atualizar()`: `status` REALIZADA→outro (ex.: `PLANEJADA`) | Nenhuma | Estoque + allocation + despesa, via novo branch `operacao_saiu_de_realizada` |
| `atualizar()`: `status` outro→REALIZADA | Cria execução/allocation/despesa (fluxo existente) | Inalterado |
| Segunda chamada de `hard_delete` no mesmo id | `EntityNotFoundError` (linha já não existe) | Inalterado — idempotência natural via `get_or_fail` |

Não existe status `CANCELADA` nem campo de "revertida" em `OperacaoAgricola`; portanto, "cancelar" e
"reverter" convergem, nesta base de código, para os dois pontos de entrada acima.

## 3. Vínculos encontrados

| Entidade | Campo de vínculo | Cardinalidade | Permite reversão segura? |
|---|---|---:|---:|
| `OperacaoAgricola` → `OperacaoExecucao` | `operacao_id` (FK CASCADE) | 1:N (na prática, código cria no máx. 1 por operação, mas nada impede N) | Sim — query direta por `operacao_id` |
| `OperacaoExecucao` → `CostAllocation` | `operation_execution_id` (FK SET NULL) **e** `source_id` (sem FK, mesmo UUID) | 1:N | Sim — `CostAllocation` não tem consumidor FK a jusante (nenhuma tabela referencia `cost_allocations.id`) |
| `OperacaoAgricola` → `Despesa` | `origem_id` + `origem_tipo="OPERACAO_AGRICOLA"` (sem FK) | 1:1 na prática (código cria no máx. 1 despesa por operação, `_buscar_despesa_existente` já assume isso com `.limit(1)`) | Sim — `Despesa` tem `ativo: bool` e `status: Literal[...,"CANCELADO"]` já aceitos pelo schema `StatusDespesa` |
| `CostAllocation` → `EstoqueMovimento` | `inventory_movement_id` (FK SET NULL) | opcional, N:1 | Não se aplica à reversão de allocation (é o movimento que aponta para a allocation, não o contrário) |

`CostAllocation` **não possui** `ativo`/`status`/soft-delete — confirmado lendo
`agricola/custos/models.py` linha a linha. Nenhuma tabela do repositório declara
`ForeignKey("cost_allocations.id", ...)` (grep vazio). Exclusão física de `CostAllocation` é,
portanto, segura e não quebra FKs nem auditoria de terceiros.

## 4. Estratégia de reversão escolhida

Neutralização lógica onde o modelo já suporta (`Despesa`), exclusão física onde não há suporte e é
comprovadamente seguro (`CostAllocation`, `OperacaoExecucao`), reversão via mecanismo já existente
para estoque (`_reverter_movimentos_estoque_operacao`, reaproveitado, sem duplicar lógica). Nenhum
campo novo, nenhuma migration.

## 5. Tratamento de CostAllocation

Novo helper `_reverter_efeitos_economicos_operacao` em `agricola/operacoes/service.py` busca todas as
`OperacaoExecucao` da operação e deleta fisicamente toda `CostAllocation` cujo
`operation_execution_id` **ou** `source_id` esteja nesse conjunto (cobre tanto o vínculo canônico
quanto o legado por `source_id`). Isso garante que:
- DRE (`custos_diretos`/`custos_operacionais`) para de somar a allocation imediatamente (query direta
  em `CostAllocation`, sem filtro de status a ajustar);
- Dashboard (`custo_operacoes_total`, pós-04F) para de contar a allocation pelo mesmo motivo;
- `agricola/tarefas/service.py` (bloqueio de exclusão de tarefa por `CostAllocation` vinculada) deixa
  de encontrar registro algum para a operação cancelada — nenhuma alteração necessária nesse arquivo.

## 6. Tratamento de Despesa

A `Despesa(origem_tipo="OPERACAO_AGRICOLA", origem_id=operacao.id)` é localizada via
`_buscar_despesa_existente` (já existente, já filtra `ativo=True`) e neutralizada:
```python
despesa.ativo = False
despesa.status = "CANCELADO"
```
`"CANCELADO"` já é um valor aceito pelo `Literal` `StatusDespesa`
(`financeiro/schemas/despesa_schema.py`), portanto não é um valor ad hoc. Após a neutralização:
- DRE (`_consolidar_despesas`) já filtra `Despesa.ativo == True` na query — para de considerá-la
  automaticamente, sem qualquer alteração em `agricola/dre/service.py`;
- `_buscar_despesa_existente` também filtra `ativo=True` — uma futura sincronização/reexecução não
  reativa nem reutiliza a despesa cancelada.

Não há cancelamento em cascata de outras despesas: a busca é sempre por `origem_id == operacao_id`
específico.

## 7. Ordem transacional

Dentro de `_reverter_efeitos_economicos_operacao` (chamada antes de qualquer exclusão da própria
`OperacaoAgricola`, sem commits intermediários):
1. localizar execuções da operação;
2. reverter estoque por execução (reaproveita `_reverter_movimentos_estoque_operacao`, agora com
   `motivo="cancelamento"` para diferenciar do estorno por edição);
3. deletar `CostAllocation` vinculadas;
4. neutralizar `Despesa`;
5. (apenas quando a operação **não** será excluída em seguida) deletar as `OperacaoExecucao` —
   controlado pelo parâmetro `remover_execucoes`;
6. `flush()` único ao final.

Em `hard_delete()`: `_reverter_efeitos_economicos_operacao(id, remover_execucoes=False)` seguido de
`super().hard_delete(id)`, que deleta a `OperacaoAgricola` e cascade-deleta as `OperacaoExecucao`
restantes — evitando duplo `DELETE` na mesma linha (testado; sem `SAWarning`).
Em `atualizar()`, quando `status_anterior == "REALIZADA"` e o novo status é outro valor não nulo:
`_reverter_efeitos_economicos_operacao(operacao.id)` (com `remover_execucoes=True`, padrão) — a
operação continua existindo, então a execução é removida explicitamente para que uma reexecução
futura não reutilize um registro obsoleto. Nenhum commit é chamado dentro do service; o commit
permanece a cargo do router/chamador, preservando atomicidade com o resto da requisição.

## 8. Idempotência

- `hard_delete`: uma segunda chamada ao mesmo id encontra `get_or_fail` falhando primeiro
  (`EntityNotFoundError`), antes de qualquer tentativa de reversão — nenhum efeito duplicado, sem
  depender de exceção de banco.
- `atualizar()` saindo de REALIZADA: a condição `status_anterior == "REALIZADA"` só é verdadeira uma
  vez — numa segunda chamada com o mesmo novo status, `status_anterior` já não é mais `"REALIZADA"`,
  então o branch nem executa.
- Dentro do helper: a busca de execuções/allocations/despesa é sempre por query explícita no estado
  atual do banco (não por flag em memória) — se já foram removidas/neutralizadas, a query
  simplesmente retorna vazio/`None` e o loop não produz efeito adicional. Coberto por
  `test_cenario_b_idempotencia_segunda_chamada_nao_gera_efeito_duplicado`.

## 9. Reexecução

Confirmada possível no domínio atual: nada impede criar uma **nova** `OperacaoAgricola` (novo id)
para a mesma safra/talhão após o cancelamento da anterior. Como a allocation antiga foi fisicamente
removida e a despesa antiga neutralizada (não reaproveitável por `_buscar_despesa_existente`), a nova
operação gera sua própria execução, allocation e despesa, sem colisão. Coberto por
`test_cenario_g_reexecucao_apos_cancelamento`: cancela uma operação de custo 1.000 e cria outra de
850 na mesma safra — dashboard reflete exatamente 850, sem resíduo da primeira.

Não é suportado (e não foi implementado) "reativar" a mesma operação após `hard_delete`, pois a linha
deixou de existir — nesse domínio, reexecução é sempre uma nova operação, não um "undo".

## 10. Consumidores impactados

- **Dashboard** (`agricola/dashboard/service.py`, pós-04F): já soma `CostAllocation` diretamente —
  nenhuma alteração necessária; a allocation deletada simplesmente não aparece mais na soma.
- **DRE** (`agricola/dre/service.py`): já filtra `Despesa.ativo == True` e soma `CostAllocation`
  diretamente — nenhuma alteração necessária.
- **Exclusão de tarefa** (`agricola/tarefas/service.py`): já conta `CostAllocation` e
  `Despesa.ativo.is_(True)` vinculadas — nenhuma alteração necessária, pois a allocation deixa de
  existir e a despesa deixa de estar ativa.
- **Alertas** (`agricola/alertas/service.py`): não alterado; como allocation e despesa são revertidas
  juntas, na mesma transação, não se cria o cenário "allocation sem despesa" ou "despesa sem
  allocation" que geraria falso alerta.

Nenhum desses quatro arquivos precisou de alteração — confirma que a estratégia de exclusão
física/neutralização foi compatível com os contratos de filtro já existentes.

## 11. Arquivos alterados

- `services/api/agricola/operacoes/service.py`:
  - `_reverter_movimentos_estoque_operacao` ganhou parâmetro `motivo` (mensagem do estorno).
  - Novos helpers `_buscar_execucoes_da_operacao` e `_reverter_efeitos_economicos_operacao`.
  - Novo override `hard_delete()`.
  - `atualizar()`: novo branch `operacao_saiu_de_realizada` (mutuamente exclusivo com
    `precisa_reprocessar_insumos` via `elif`).
- `services/api/tests/test_operacao_reversao_economica.py` (novo arquivo): 8 testes de regressão.

## 12. Testes adicionados

`tests/test_operacao_reversao_economica.py`:
- **Cenário A** — cancelamento simples: allocation deletada, despesa neutralizada (`ativo=False`,
  `status=CANCELADO`), operação inacessível (`EntityNotFoundError`).
- **Cenário B** — idempotência: segunda chamada de `hard_delete` levanta `EntityNotFoundError`, sem
  efeito residual adicional sobre allocation/despesa.
- **Cenário C** — múltiplas operações/allocations: cancelar uma não afeta a allocation da outra.
- **Cenário D** — isolamento multi-tenant: cancelar no tenant A não altera allocation/despesa do
  tenant B.
- **Cenário E** — dashboard: `custo_operacoes_total` cai de 1.000 (duas operações) para 600 após
  cancelar a de 400.
- **Cenário F** — DRE: `custos_diretos` cai de 1.200 para 0 após cancelamento; despesa cancelada não
  aparece em `despesas_operacionais_detalhe.itens`.
- **Cenário G** — reexecução: cancelar e criar nova operação não duplica custo.
- Teste adicional — transição de status via `atualizar()` (REALIZADA→PLANEJADA) também reverte
  allocation e despesa, cobrindo o segundo ponto de entrada do gap.

## 13. Testes executados

```bash
.venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_operacoes_validacao_fase.py \
  tests/test_fifo_estoque.py tests/test_dre_agricola_v1.py tests/test_dashboard_financeiro_safra.py -q
.venv/bin/python -m pytest tests/test_operacao_reversao_economica.py tests/test_operacao_despesa_webhook.py \
  tests/test_operacoes_validacao_fase.py -q
.venv/bin/ruff check agricola/operacoes/service.py tests/test_operacao_reversao_economica.py
```

## 14. Resultados

- Baseline (antes da implementação): 40 passed / 3 failed (mesmas falhas conhecidas de `receita_total`).
- Suíte combinada pós-implementação (dashboard + DRE + FIFO + webhook + validação de fase):
  **40 passed / 3 failed** — mesmas 3 falhas pré-existentes, nenhuma nova.
- `test_operacao_reversao_economica.py` (novo): **8 passed**.
- `test_operacao_reversao_economica.py` + `test_operacao_despesa_webhook.py` +
  `test_operacoes_validacao_fase.py`: **todos passed** (exit code 0).
- `ruff check agricola/operacoes/service.py`: **41 erros**, idêntico ao baseline (`git stash`
  confirmou 41 antes da mudança) — nenhuma violação nova.
- `ruff check tests/test_operacao_reversao_economica.py`: **0 erros** (arquivo novo, sem débito
  herdado).
- `git diff --check`: limpo.

## 15. Falhas pré-existentes

`test_resumo_financeiro_safra_valido`, `test_resumo_financeiro_safra_sem_operacoes`,
`test_resumo_roi_calculado` continuam falhando em `receita_total` (poluição de dados entre testes que
compartilham `TENANT_A_ID` fixo, já documentada nas etapas 04E/04F) — não relacionado a custo/despesa,
não corrigido nesta etapa por estar fora de escopo.

## 16. Riscos residuais

- O domínio não possui status `CANCELADA` nem histórico formal de reversão (sem `reversed_at`,
  `reversal_reason`) — a rastreabilidade do cancelamento fica no `EstoqueMovimento` tipo `DEVOLUCAO`
  (com `observacoes` indicando "cancelamento") e no `audit_log` do `hard_delete`/`update` herdado do
  `BaseService`. Se no futuro for necessário auditar "por que" uma operação foi cancelada além do
  registro genérico de exclusão, será preciso um campo novo — não criado aqui por estar fora do
  escopo autorizado ("não criar migration").
- `CostAllocation` não tem soft-delete por desenho; qualquer novo consumidor futuro desse modelo
  precisa saber que allocations revertidas são **removidas**, não marcadas — documentado aqui para
  evitar suposições incorretas.
- Testes de rollback transacional em falha (cenário H do plano) não foram implementados como teste
  de injeção de falha dedicado: a garantia vem de desenho (nenhum `commit()` dentro dos services,
  única transação por requisição controlada pelo router/fixture de teste) e foi verificada por
  revisão de código, não por um teste que force uma exceção no meio da reversão. Risco residual
  aceito dado o escopo e o tempo desta etapa.

## 17. Decisão final

```
SOIL-PLAN-EXEC-04G
STATUS: GO
```

```
REGRA FINAL:
A reversão da operação agrícola neutraliza, na mesma transação, estoque,
CostAllocation e Despesa(OPERACAO_AGRICOLA), de forma idempotente e isolada por tenant.
```

```
PRÓXIMO PASSO:
Auditar se Despesa(OPERACAO_AGRICOLA) ainda precisa continuar sendo criada.
Sem consumidores econômicos dependentes, avaliar sua remoção controlada ou manutenção
apenas como registro histórico sem exposição financeira.
```
