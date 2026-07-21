# SOIL-PLAN-EXEC-04 — Auditoria do Fluxo Tarefa → Campo → Estoque → Custo → Financeiro

**Tipo:** Auditoria arquitetural e funcional, somente leitura. Nenhum código de produção ou teste foi alterado.
**Data:** 2026-07-20
**Escopo:** `AnaliseSolo → SafraTarefa → OperacaoAgricola → execução em campo → consumo FIFO → custo real → financeiro`

---

## 1. SafraTarefa → OperacaoAgricola

**Situação: PARCIAL**

- `TarefasService.gerar_operacao_planejada(tarefa_id, dados)` — `services/api/agricola/tarefas/service.py:572`.
- Exige `tarefa.status == "APROVADA"` (linhas 574-578), senão `BusinessRuleError` — regra confirmada.
- Idempotência simples: se já existe `OperacaoAgricola` com `tarefa_id` e `status="PLANEJADA"`, retorna a existente em vez de duplicar (linhas 584-591).
- Campos copiados para `OperacaoAgricolaCreate` (linhas 602-619): `safra_id`, `talhao_id`, `production_unit_id`, `tarefa_id` (vínculo com origem), `tipo`, `fase_safra`, `area_aplicada_ha` (de `tarefa.area_ha`), `maquina_id`, `operador_id`, insumos (`produto_id`, `dose_por_ha`).
- **Lacunas de rastreabilidade:**
  - `cultivo_id` é passado como `None` (linha 605) — não propagado da tarefa.
  - `analise_solo_id` **não é copiado** para `OperacaoAgricola`. O vínculo com a análise de solo original só existe em `SafraTarefa.analise_solo_id` (`tarefas/models.py:38`); para saber que uma operação nasceu de um laudo de solo, é preciso navegar `Operacao → tarefa_id → SafraTarefa → analise_solo_id` (join indireto de 2 saltos, sem índice dedicado para essa consulta).
  - Não há campo `custo_estimado` preenchido no momento da criação da operação planejada — custo só aparece na execução (via FIFO).

**Risco:** consultas de auditoria/BI que tentem responder "quais operações vieram de qual laudo de solo" exigem join em cadeia; não há garantia de índice otimizado para isso hoje.

---

## 2. OperacaoAgricola → Campo PWA

**Situação: AUSENTE (não existe PWA real)**

- A rota `apps/web/src/app/(dashboard)/dashboard/operacional/campo/tarefas/page.tsx` é uma página Next.js comum — **não** é um app PWA offline-first.
- **Dexie/IndexedDB:** não encontrado em `apps/web/src` (busca exaustiva sem resultados).
- **Service Worker / manifest.json:** não encontrado no projeto.
- **Idempotency-key / client_id de sincronização offline:** não encontrado no fluxo de campo (as únicas ocorrências desses termos pertencem ao módulo de integração ERP, contexto totalmente diferente).

**Resposta direta:** *Uma operação de adubação gerada por análise de solo NÃO chega a um "Campo PWA" no sentido de app offline com storage local e sync — o que existe é uma tela web convencional consumindo a API diretamente, dependente de conectividade.* Isso contradiz a premissa "confirmada" no contexto da tarefa; a auditoria não encontra suporte de código para PWA/offline.

---

## 3. Execução no Campo

**Situação: PARCIAL**

- Não existe endpoint dedicado `/concluir`; a transição de status é feita via `PATCH` genérico — `services/api/agricola/operacoes/router.py:281-300` → `OperacaoService.atualizar()` (`service.py:1113`).
- `atualizar()` captura `status_anterior` e estado prévio (linhas 1114-1120) antes de aplicar mudanças — proteção contra reprocessamento incorreto.
- Quando `status → "REALIZADA"`, grava `OperacaoExecucao` com `custo_real` (linha 579) e `status="REALIZADA"` (linha 581) — `_garantir_execucao_e_allocation_leves` (`service.py:552`).
- **Campos registrados:** produto/lote (via consumo FIFO), área aplicada (`_validar_area_aplicada`, linhas 1131-1135), operador/máquina (copiados desde o planejamento, não capturados na execução em si).
- **Execução parcial:** não encontrada — não há modelo de múltiplas baixas parciais acumulativas para uma mesma operação; a área aplicada pode ser corrigida via update, mas não há um "log de execuções parciais".
- **Estorno/cancelamento:** SIM, confirmado — `_reverter_movimentos_estoque_operacao` (`service.py:425-478`) reverte `EstoqueMovimento` do tipo `SAIDA`, reabre lotes `ESGOTADO → ATIVO`, e grava ledger reverso.

**Risco:** ausência de execução parcial estruturada pode forçar workarounds (ex.: várias operações pequenas em vez de uma só com baixas incrementais).

---

## 4. Consumo de Estoque

**Situação: COMPLETO (na regra central) / PARCIAL (reserva)**

- Confirmado por código: consumo FIFO só dispara quando `operacao.status == "REALIZADA"` — checado explicitamente em dois pontos: `service.py:371` (dentro de `_aplicar_insumos_na_operacao`) e `service.py:911-912` (dentro de `criar()`).
- Não há caminho de código em que `PLANEJADA`, `APROVADA` ou `EM_EXECUCAO` disparem baixa — a condição é textual (`if operacao.status == "REALIZADA":`).
- **Reserva de estoque durante o planejamento:** não encontrada — não há soft-lock/reserva de saldo ao criar operação `PLANEJADA`. O risco é indireto: duas operações planejadas concorrentes podem ambas assumir saldo disponível e, na hora de executar, uma delas falhar por saldo insuficiente (comportamento aceitável, mas não é "reserva").
- Idempotência de reprocessamento: mitigada pela checagem de `operacao_execucao_existente` antes de reaplicar (`service.py:1114-1120`), mas não há teste explícito de "dupla execução simultânea" (race condition) nos arquivos revisados.

---

## 5. FIFO

**Situação: COMPLETO**

- `consumir_lotes_fifo()` — `services/api/operacional/services/estoque_fifo.py:28`.
- Ordem cronológica: `ORDER BY LoteEstoque.data_fabricacao ASC NULLS FIRST` (linha 72-73) — FIFO real, não preço médio.
- Custo unitário histórico por lote: `custo_do_lote = quantidade_do_lote * lote.custo_unitario` (linha 93).
- Saldo remanescente atualizado em `atualizar_saldo_apos_consumo()` (linhas 156-195), grava em `SaldoEstoque.quantidade_atual`.
- Testes dedicados cobrindo: consumo do lote mais antigo primeiro, custo histórico (não preço médio), erro de estoque insuficiente, consumo exato de todos os lotes, status `ESGOTADO`, ausência de depósito específico — `services/api/tests/test_fifo_estoque.py`.

**Resposta direta:** *Sim — o custo real do insumo aplicado é calculado com base nos lotes efetivamente consumidos pelo FIFO*, com custo histórico por lote (não médio), o que está architeturalmente correto.

---

## 6. Custo Planejado vs Custo Realizado

**Situação: PARCIAL**

- Custo estimado: não persistido como campo formal em `OperacaoAgricola` no momento do planejamento — só existe implicitamente (dose × preço estimado, se calculado no frontend/schema, não confirmado como persistido).
- Custo realizado: preenchido em `OperacaoExecucao.custo_real` a partir de `operacao.custo_total` (`service.py:498, 579`), e apropriado à safra/unidade operacional via `CostAllocation` (`agricola/custos/allocation_service.py`, chamado em `service.py:33, 689`).
- Guardrail de integridade: se há custo > 0 sem `production_unit_id` resolvível, a conclusão é **bloqueada** com erro de negócio explícito (linhas 615-726, mensagem "Não é possível concluir a operação com custo sem apropriação econômica") — proteção real contra custo órfão.
- **Comparação planejado × realizado:** não encontrada nos serviços revisados (`operacoes/service.py`, `custos/*`). Pode existir em módulo de rentabilidade não explorado a fundo, mas não há evidência direta.
- Mão de obra e máquinas: `test_launch_core01_operational_cost_engine.py` sugere que custo de máquinas/mão de obra é considerado em outro motor de custo operacional (RH/frota), não exclusivamente insumo — mas a integração exata com o fluxo de solo→tarefa não foi confirmada em código nesta auditoria.

**Resposta direta:** *Após a execução, o custo real fica visível e rastreável na safra via `CostAllocation`, mas não há comparação planejado × realizado automatizada visível no código auditado.*

---

## 7. Financeiro

**Situação: PARCIAL — separação existe, mas com ponto de atenção**

- Confirmado: `services/api/agricola/operacoes/service.py:1024-1042` cria `Despesa` automaticamente quando `custo_total_operacao > 0` **e** `status == "REALIZADA"`.
- `Despesa` é criada já com `status="PAGO"`, `origem_tipo="OPERACAO_AGRICOLA"`, `origem_id=operacao.id` (linhas 1042-1054) — **não** é uma "conta a pagar em aberto", é lançamento de despesa já liquidada.
- Import direto de `financeiro.models.despesa.Despesa` dentro de `agricola/operacoes/service.py:36` — acoplamento síncrono direto entre camada agrícola e financeira (não via evento/outbox).
- **A execução NÃO cria conta a pagar** (não há chamada a `ContaPagar`/módulo de compras/fornecedores/ERP nesse fluco) — está alinhado ao princípio "aplicação de insumo já em estoque não deve gerar nova conta a pagar".
- Não há ligação entre "necessidade planejada" e "solicitação de compra automática" (ver item 8) — logo, o cenário de aquisição (compra → conta a pagar) e o cenário de aplicação (baixa → despesa PAGO) estão de fato desacoplados no código, mas a *entrada* do insumo em estoque (que deveria gerar a conta a pagar) não foi localizada like integrada automaticamente ao módulo de compras.
- Testes cobrindo isso: `services/api/tests/test_operacao_despesa_webhook.py` (7 testes, incluindo isolamento de tenant e "sem custo não cria despesa").

**Risco de dupla contabilização:** baixo diretamente na execução (código não cria conta a pagar duplicada), mas a `Despesa` já nascer `PAGO` sem vínculo formal ao título de compra original é um ponto que merece confirmação — se a compra também gerar uma despesa/conta a pagar na entrada do insumo, poderia haver duas despesas para o mesmo insumo (uma na compra, outra na aplicação). Isso não foi confirmado nem descartado com evidência de código nesta auditoria (recomenda-se investigação dedicada no módulo `compras_service.py` + `financeiro`).

---

## 8. Necessidade de Compra

**Situação: AUSENTE**

- Busca por `necessidade_compra`, `necessidade_aquisicao`, `NecessidadeCompra` no código-fonte não retornou resultados.
- `operacional/services/compras_service.py` implementa fluxo manual clássico: `criar_solicitacao` (646) → `criar_cotacao` (732) → `aprovar_cotacao` (819) → `receber_pedido` (909).
- Não há gatilho automático de "estoque insuficiente → solicitação de compra" vindo do fluxo agrícola/planejamento.

**Resposta direta:** *A análise "quantidade necessária − estoque disponível = necessidade de aquisição" não existe hoje como serviço automatizado. O processo de compra existe, mas é isolado e manual, sem ligação com o planejamento de safra/tarefas.*

---

## 9. Papel da Unidade Operacional

**Situação: parcialmente esclarecido**

- `_resolve_production_unit_id()` (`agricola/operacoes/service.py:253`) resolve a unidade operacional da operação a partir do talhão (prioriza unidade `ATIVA`, linha 279).
- Uso confirmado: chave de `CostAllocation` (centro de custo/rateio financeiro — linhas 545, 572, 675) e como pré-condição de bloqueio ("Operação com custo sem contexto suficiente para apropriação", linhas 616-626).
- **Não há evidência** de que `production_unit_id` determine diretamente o depósito de estoque (`LoteEstoque`/`deposito_id`) nos trechos revisados.

**Resposta direta:** *O vínculo talhão→unidade operacional parece necessário principalmente como centro de custo para rateio financeiro (CostAllocation), não claramente como determinante de depósito/estoque físico. Não recomendamos remoção — apenas confirmar todos os consumidores antes de qualquer simplificação, conforme instrução do escopo.*

---

## 10. Eventos e Transações

**Situação: COMPLETO (transação síncrona única) / outbox não usado aqui**

- Toda a cadeia — status → FIFO → `OperacaoExecucao` → `CostAllocation` → `Despesa` — ocorre na **mesma `AsyncSession`**, dentro do mesmo método `atualizar()`/`criar()` de `OperacaoService` (flush em linhas 951-954, 1053-1054).
- Outbox pattern (`services/api/events/outbox_*.py`) existe no repositório, mas **não é usado** no fluxo agrícola/estoque/financeiro — está restrito a integrações ERP/Sankhya.
- **Resposta direta:** *Não é possível, pelo código atual, uma operação ficar `REALIZADA` sem estoque baixado ou com estoque baixado sem custo apropriado* — a atomicidade vem da sessão compartilhada, não de um outbox transacional. Isso é consistente, porém cria acoplamento direto de camadas (import cruzado agrícola→financeiro).

---

## 11. Testes

| Área | Classificação | Evidência |
|---|---|---|
| Aprovação tarefa→operação | PARCIALMENTE COBERTA | `test_operacoes_schemas.py`, `test_operacoes_validacao_fase.py`, `test_safra_fases.py` — não confirmado teste específico de `gerar_operacao_planejada` end-to-end |
| Execução em campo / governança | COBERTA | `test_operational_workflow_governance_step01..10.py`, `test_field_core02/03/05_*.py` |
| Sincronização offline / PWA | NÃO COBERTA | não existe funcionalidade a testar (item 2) |
| Mudança para REALIZADA | COBERTA | dentro dos testes de governança operacional |
| Consumo FIFO | COBERTA | `test_fifo_estoque.py` (6 testes: lote mais antigo, custo histórico, saldo insuficiente, consumo exato, status esgotado, sem depósito) |
| Idempotência | PARCIALMENTE COBERTA | reprocessamento sem duplicar custo é testado (`test_operational_cost_service_reprocessa_sem_duplicar`), mas não há teste de concorrência real (múltiplas requisições simultâneas) |
| Saldo insuficiente | COBERTA | `test_fifo_erro_estoque_insuficiente` |
| Custo real | COBERTA | `test_launch_core01_operational_cost_engine.py` (5 testes) |
| Planejado × realizado | NÃO COBERTA | não localizada comparação nem teste |
| Estorno | PARCIALMENTE COBERTA | reversão de movimento de estoque implementada (`_reverter_movimentos_estoque_operacao`), teste dedicado não confirmado nominalmente |
| Financeiro (Despesa automática) | COBERTA | `test_operacao_despesa_webhook.py` (7 testes, incl. isolamento de tenant) |
| Compra | PARCIALMENTE COBERTA | `test_compras_lote_integration.py` cobre fluxo de compras isoladamente, sem ligação com necessidade planejada |

---

## 12. Matriz Final

| Etapa | Situação | Evidência | Risco |
|---|---|---|---|
| Laudo → tarefa | PARCIAL | `tarefas/models.py:38` (`analise_solo_id`); vínculo existe na tarefa mas não propaga à operação | Rastreabilidade exige join em cadeia |
| Tarefa → aprovação | COMPLETO | `tarefas/service.py:317-338`, `service.py:23-26` (TRANSICOES) | Baixo |
| Aprovação → operação | PARCIAL | `tarefas/service.py:572-619` | `cultivo_id`/`analise_solo_id` não copiados; custo estimado não persistido |
| Operação → Campo (PWA) | AUSENTE | busca por Dexie/SW/manifest sem resultado | Premissa de PWA offline não confirmada em código |
| Campo → REALIZADA | PARCIAL | `operacoes/router.py:281-300`, `service.py:1113` | Sem execução parcial estruturada |
| Realizada → FIFO | COMPLETO | `service.py:371, 911-912`; `estoque_fifo.py:28-107` | Baixo |
| FIFO → custo real | COMPLETO | `estoque_fifo.py:93`; `OperacaoExecucao.custo_real` (`service.py:498,579`) | Baixo |
| Custo → safra | PARCIAL | `CostAllocation` via `allocation_service.py` | Sem comparação planejado×realizado |
| Execução → financeiro | PARCIAL | `service.py:1024-1054` (Despesa automática, status PAGO) | Possível dupla despesa (compra + aplicação) não descartada |
| Necessidade → compra | AUSENTE | busca sem resultado; `compras_service.py` manual e isolado | Sem automação; risco de ruptura de estoque não antecipada |

---

## 13. Decisão Final

**Classificação: Opção B — operacional completo, econômico parcial**, com uma ressalva adicional: o elo "Operação → Campo PWA" descrito no contexto da tarefa **não tem suporte de código** (não existe PWA offline com Dexie/Service Worker) — o que a aproxima também da Opção C nesse ponto específico. Resumindo:

- O núcleo **Laudo → Tarefa → Aprovação → Operação Planejada → Execução → FIFO → Custo Real** está funcional e tecnicamente correto (transação única, guardrails de custo sem apropriação, FIFO com custo histórico real).
- O elo **Campo PWA/offline** é uma lacuna: a premissa do contexto não está confirmada em código — o que existe é uma tela web comum, não um app offline-first.
- O lado **econômico** está parcialmente separado (despesa automática correta, sem conta a pagar direta na execução), mas falta: comparação planejado×realizado, cálculo de necessidade de compra, e confirmação de que a compra de insumo não gera uma segunda despesa duplicada com a aplicação.

---

## 14. Próximo Passo Recomendado (menor passo, não implementar)

Investigar e confirmar, com leitura de código (sem implementar nada ainda), **se a entrada de um insumo comprado gera uma `Despesa`/conta a pagar no módulo `compras_service.py`/financeiro**, e comparar com a `Despesa` automática criada em `agricola/operacoes/service.py:1024-1054` na execução — para descartar ou confirmar o risco de dupla contabilização apontado no item 7. Esse é o ponto de maior incerteza econômica identificado e o mais barato de esclarecer antes de qualquer decisão de correção.

Não propor novo módulo, não integrar ERP ao estoque operacional, não transformar análise de solo em fato financeiro — nenhuma dessas ações é necessária; os componentes já existem, faltando apenas confirmar/ajustar a integração entre eles.
