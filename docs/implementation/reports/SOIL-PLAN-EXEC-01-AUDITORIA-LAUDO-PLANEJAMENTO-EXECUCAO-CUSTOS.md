# SOIL-PLAN-EXEC-01 — Auditoria: Laudo Digital de Solo → Planejamento → Execução → Custos

> Auditoria exclusivamente de leitura. Nenhum código foi criado ou alterado.
> Data: 2026-07-20

## 1. Resumo executivo

O AgroSaaS já possui um fluxo real e majoritariamente funcional ligando **Laudo de Solo → Tarefa Planejada → Operação → Custo**, construído sobre módulos existentes (`agricola/analises_solo`, `agricola/tarefas`, `agricola/operacoes`, `agricola/custos`, `agricola/a1_planejamento`, `campo/`). O elo mais forte é `SafraTarefa` (tabela `safra_tarefas`): ela carrega `analise_solo_id`, `safra_id`, `talhao_id`, `cultivo_area_id`, `origem` (`SOLO|TEMPLATE|MANUAL`), `status` (`PENDENTE_APROVACAO|APROVADA|EM_EXECUCAO|CONCLUIDA|CANCELADA|INVALIDADA`), campos de aprovação e `custo_estimado`. O método `TarefasService.gerar_operacao_planejada()` converte a tarefa em `OperacaoAgricola` com `status="PLANEJADA"`, e o consumo real de estoque (FIFO) só ocorre quando `operacao.status == "REALIZADA"` — confirmando que planejamento não movimenta estoque nem gera custo real prematuramente.

Porém, o próprio `AnaliseSolo` (o "laudo" em si, tabela `analises_solo`) **não tem `safra_id`, não tem status/aprovação, não tem responsável técnico, não tem versionamento** — é um registro de dados brutos de laudo, sem diagnóstico estruturado nem geração automática visível de `RegraAgronomica`→`SafraTarefa` no código revisado (existe o model `RegraAgronomica`, mas a trilha de geração automática não foi encontrada de forma explícita nos arquivos lidos). O módulo `recomendacoes/` (nível agrícola) é, na prática, um motor de recomendações **econômicas/operacionais** (baseado em benchmark de safra), não agronômicas de solo — não deve ser confundido com "recomendação de correção de solo". O módulo `diagnostico/` também é econômico/DRE, não diagnóstico agronômico de solo. Há ainda 4 rotas de frontend distintas para "análises de solo" (duplicidade a resolver).

## 2. Veredicto

**SIM COM RESSALVAS** — a espinha dorsal do fluxo (laudo → tarefa vinculada ao talhão/safra → aprovação → operação planejada → custo estimado → execução → consumo real de estoque via FIFO apenas quando `REALIZADA` → comparação planejado×realizado) já existe e funciona de ponta a ponta no backend, mas com lacunas concretas: falta vínculo direto `AnaliseSolo.safra_id`/aprovação/versionamento no laudo, a geração automática recomendação-de-solo→tarefa não está plenamente evidenciada, não há eventos de domínio publicados para os marcos desse fluxo, e a integração com o Campo PWA passa por um caminho parcialmente paralelo (`TarefaCampo` não tem FK para `SafraTarefa`).

## 3. Mapa do fluxo atual

1. **Laudo de solo** — `AnaliseSolo` criado via `agricola/analises_solo` (talhão + production_unit, sem safra_id). [FALTA: safra_id, status/aprovação, responsável técnico, versionamento]
2. **Diagnóstico/recomendação agronômica de solo** — `RegraAgronomica` existe como model; geração automática de `SafraTarefa` a partir da análise não foi confirmada em código lido (apenas o campo `origem="SOLO"` e comentário no docstring de `SafraTarefa` afirmando que "nasce PENDENTE_APROVACAO" quando gerada por análise de solo). [FALTA: confirmar/expor o motor que efetivamente cruza parâmetros do laudo com regras e cria a tarefa]
3. **Tarefa planejada vinculada ao talhão/safra/laudo** — `SafraTarefa` (tabela `safra_tarefas`), com `analise_solo_id`, `talhao_id`, `safra_id`, `cultivo_area_id`, `tipo` (CALAGEM/ADUBACAO_*/...), `custo_estimado`, `dose_estimada_kg_ha`. IMPLEMENTADO.
4. **Aprovação** — `TarefasService.aprovar()/rejeitar()`, status `PENDENTE_APROVACAO → APROVADA`. IMPLEMENTADO.
5. **Geração de operação planejada** — `TarefasService.gerar_operacao_planejada()` cria `OperacaoAgricola(status="PLANEJADA", tarefa_id=...)`. IMPLEMENTADO.
6. **Custo planejado consolidado** — `ItemOrcamentoSafra` (`agricola_orcamento_itens`, vinculado a `safra_id`/`cultivo_id`/`production_unit_id`) e `custo_estimado` em `SafraTarefa` alimentam `CustosService.get_resumo_safra()`, que retorna `orcamento_previsto_total` e `desvio_orcamento_pct`. IMPLEMENTADO.
7. **Conversão em execução / Campo PWA** — duas rotas observadas: (a) via `OperacaoService.criar()` diretamente; (b) via `campo/service.py::_materializar_aplicacao()`, que recebe uma `TarefaCampo` (tabela `campo_tarefas`) e cria `OperacaoAgricola(tarefa_id=task.id, ...)`. IMPLEMENTADO PARCIALMENTE — `TarefaCampo` não referencia `SafraTarefa` por FK; a costura entre "tarefa planejada de safra" e "tarefa que aparece no Campo PWA" não é uma FK direta, aparentando ser dois modelos de tarefa paralelos conectados por convenção/id de operação, não por chave declarada.
8. **Consumo real de estoque e custo real** — em `OperacaoService._aplicar_insumos_na_operacao()`, `consumir_lotes_fifo()` só é chamado se `operacao.status == "REALIZADA"`; senão nenhum lote é debitado. IMPLEMENTADO corretamente (planejamento não move estoque).
9. **Custo realizado e comparação planejado × realizado** — `CustosService.get_resumo_safra()` cruza `CostAllocation`/`OperacaoAgricola.custo_total` (realizado) contra `ItemOrcamentoSafra`/`Safra.custo_previsto_ha` (planejado), com fallback documentado. IMPLEMENTADO.
10. **Eventos de domínio** — nenhuma referência a outbox/publish_event encontrada em `analises_solo`, `tarefas`, `operacoes` ou `campo`. AUSENTE.

## 4. Arquivos e componentes encontrados

- `services/api/agricola/analises_solo/{models,schemas,service,router}.py` — laudo de solo (`AnaliseSolo`, `RegraAgronomica`).
- `services/api/agricola/amostragem_solo/models/{amostras,mapas_fertilidade,prescricoes_vra}.py` — amostragem e prescrição de agricultura de precisão (VRA), módulo correlato/paralelo.
- `services/api/agricola/prescricoes/models.py.bak` — arquivo `.bak` de `PrescricaoVRA`, indício de módulo desativado/duplicado.
- `services/api/agricola/tarefas/{models,schemas,service,router}.py` — `SafraTarefa`, motor de aprovação e conversão em operação.
- `services/api/agricola/operacoes/{models,schemas,service,router}.py` — `OperacaoAgricola`, `OperacaoExecucao`, `InsumoOperacao`.
- `services/api/agricola/custos/{models,service,operational_cost_service,allocation_service}.py` — `CostAllocation`, resumo planejado×realizado.
- `services/api/agricola/a1_planejamento/{models,service,router}.py` — `ItemOrcamentoSafra` (orçamento por safra/cultivo/production_unit).
- `services/api/agricola/recomendacoes/{schemas,service,router}.py` — motor de recomendação econômico-operacional (não agronômico de solo), Pydantic in-memory (`RecomendacaoAgricolaItem`, sem tabela própria confirmada).
- `services/api/agricola/diagnostico/service.py` — diagnóstico econômico/DRE, não diagnóstico de solo.
- `services/api/agricola/cultivos/models.py` — `Cultivo.analise_solo_id`, `regiao_analise` (vínculo laudo→cultivo).
- `services/api/campo/{models,service,router,schemas}.py` — `DispositivoCampo`, `TarefaCampo`, `SyncTombstone`; `_materializar_aplicacao`/`_materializar_colheita` convertem tarefa de campo em `OperacaoAgricola`.
- `services/api/atividades/{service,router}.py` — feed de atividades por safra (leitura agregada, não motor de planejamento).
- `services/api/migrations/versions/4b6b337b818f_analises_solo.py`, `step13_analise_solo_upgrade.py`, `step10_cultivo_area_analise_solo.py`, `step9_solo_parametros_cultura.py`, `step12_safra_tarefas.py`, `c73c38421889_add_agricola_orcamento_itens.py`, `20260606_campo_tarefas_invalidacao.py`, `3e5cb19a3727_add_fase_and_criticidade_to_safratarefa_.py`, `6d3bbf58bcc7_add_cancellation_fields_to_tarefas.py`, `step45_tarefas_invalidacao.py`.
- Frontend: `apps/web/src/app/(dashboard)/agricola/analises-solo/page.tsx`, `.../dashboard/agricola/analises-solo/page.tsx`, `.../dashboard/agricola/analises_solo/page.tsx` (3 rotas duplicadas), `.../agricola/safras/[id]/analises-solo/page.tsx` (integrada à safra), `.../agricola/safras/[id]/orcamento/page.tsx`, `.../agricola/planejamento/page.tsx`, `.../dashboard/agricola/recomendacoes/page.tsx`, `.../dashboard/inteligencia-operacional/recomendacoes/page.tsx`.

## 5. Entidades e tabelas envolvidas

| Tabela | tenant_id | FK safra | FK talhão | Status/aprovação | Custo planejado | Custo real |
|---|---|---|---|---|---|---|
| `analises_solo` | sim | **não** | sim (`cadastros_areas_rurais`) | não | não | não |
| `safra_tarefas` | sim | sim | sim (nullable) | sim (`status`, `aprovado_por/em`) | `custo_estimado` | não (referencia `operacao_id`) |
| `operacoes_agricolas` | sim | sim | sim | `status` (PLANEJADA/REALIZADA/...) | não direto | `custo_total` |
| `operacoes_execucoes` | sim | via operação | não direto | `status` | não | sim |
| `insumos_operacao` | sim | via operação | não direto | não | não | `custo_total`/`custo_unitario` |
| `cost_allocations` | sim | via production_unit | não | não | não | `amount` |
| `agricola_orcamento_itens` | sim | sim | não (via cultivo/PU) | não | `custo_total` | não |
| `campo_tarefas` | sim | **não** (apenas `unidade_produtiva_id`/`area_rural_id` soltos) | soltos, sem FK declarada | `status`/`status_execucao` | não | não |

## 6. Endpoints

- `agricola/analises_solo/router.py` — CRUD de laudo (prefixo `/api/v1`, registrado em `main.py:467`).
- `agricola/tarefas/router.py` — 11 rotas: listar/criar (`GET/POST`), aprovar, rejeitar, iniciar, concluir, concluir-via-operação, invalidar, excluir, `gerar_operacao_planejada` (`POST`).
- `agricola/operacoes/router.py` — CRUD de operações agrícolas (`main.py:457`).
- `agricola/custos/router.py` — resumo de custos por safra (`main.py:468`).
- `agricola/a1_planejamento/router.py` — orçamento por safra (`main.py:477`).
- `agricola/recomendacoes/router.py` — recomendações econômicas por safra (`main.py:453`).
- `campo/router.py` — dispositivos, `campo_tarefas`, pull/push de sincronização offline.

## 7. Eventos

Nenhum evento de domínio (outbox/publisher) foi encontrado ligado a: laudo concluído, análise de solo registrada, recomendação criada/aprovada, tarefa planejada aprovada, operação planejada gerada, execução iniciada/concluída, estoque consumido ou orçamento atualizado, nos módulos `analises_solo`, `tarefas`, `operacoes` e `campo`. O sistema de eventos (`services/api/events/`) existe na arquitetura geral (outbox_service, outbox_relay, subscribers), mas **não é usado por este fluxo específico**. AUSENTE.

## 8. Telas Web

- `agricola/safras/[id]/analises-solo` — tela integrada à safra (parece ser a canônica).
- `agricola/safras/[id]/orcamento` — tela de orçamento por safra.
- `agricola/planejamento` — tela de planejamento (não inspecionado o conteúdo em profundidade).
- `dashboard/agricola/recomendacoes` e `dashboard/inteligencia-operacional/recomendacoes` — duas telas de recomendações (possível duplicidade a confirmar).
- `agricola/analises-solo` (raiz), `dashboard/agricola/analises-solo`, `dashboard/agricola/analises_solo` — 3 rotas adicionais de análise de solo fora do contexto de safra, sugerindo telas legadas/duplicadas.
- Não foi localizada tela específica de "aprovação de tarefa" nem de "geração de operação planejada a partir de tarefa" nem de "comparação planejado × realizado" visual — o backend (`gerar_operacao_planejada`, `get_resumo_safra`) parece ir além do que está exposto/confirmado na UI. SOMENTE BACKEND para esses pontos, a confirmar com uma varredura de componentes React (não realizada em profundidade nesta auditoria).

## 9. Integração com Campo PWA

`TarefaCampo` (`campo_tarefas`) suporta `origem` MANUAL/PROGRAMADA, `client_id` com `UniqueConstraint(tenant_id, client_id)` (evita duplicidade em reenvio offline), `status_execucao`, timestamps de cliente para resolução de conflito. `CampoTarefaService._materializar_aplicacao()` converte a tarefa de campo em `OperacaoAgricola` vinculando `tarefa_id=task.id` — mas esse `tarefa_id` aponta para `operacoes_agricolas.tarefa_id`, que por sua vez é FK para `safra_tarefas.id`; não há, porém, no model `TarefaCampo`, nenhuma coluna que referencie `SafraTarefa` diretamente. Ou seja: a tarefa PROGRAMADA no Campo PWA aparentemente é criada a partir de outra origem (não localizada explicitamente a rotina que copia `SafraTarefa` aprovada → `TarefaCampo`), e a ligação de volta à tarefa de planejamento de safra não é uma FK — é reconstruída via lógica de aplicação. IMPLEMENTADO PARCIALMENTE.

## 10. Tratamento dos custos planejados

- `SafraTarefa.custo_estimado`, `dose_estimada_kg_ha`, `quantidade_total_estimada_kg` — planejamento por tarefa.
- `ItemOrcamentoSafra` — orçamento consolidado por safra/cultivo/production_unit (`custo_total`).
- `CustosService.get_resumo_safra()` consolida `orcamento_previsto_total` a partir de `ItemOrcamentoSafra`, com fallback para `Safra.custo_previsto_ha × área`.
- Nada disso movimenta estoque ou gera lançamento financeiro real — confirmado (ver seção 12).

## 11. Tratamento dos custos reais

- `OperacaoAgricola.custo_total`, `InsumoOperacao.custo_total/custo_unitario` — calculados via FIFO (`consumir_lotes_fifo`) apenas quando `status == "REALIZADA"`.
- `CostAllocation` — alocação de custo real por `production_unit`, com origem em `operacoes_execucoes`/`estoque_movimentos`/`fin_rateios`.
- `CustosService.get_resumo_safra()` calcula `custo_total_realizado`, `custo_realizado_por_ha` e `desvio_orcamento_pct = (realizado - planejado) / planejado`. IMPLEMENTADO.
- Não foi confirmado registro estruturado de horas de mão de obra/máquina, combustível ou perdas dentro do fluxo de solo especificamente (podem existir em outros módulos como `frota`/`rh`, não cobertos nesta auditoria por estarem fora do escopo do laudo→tratamento).

## 12. Vínculo com estoque

Confirmado no código (`operacoes/service.py::_aplicar_insumos_na_operacao`): o débito de estoque (`consumir_lotes_fifo`, `atualizar_saldo_apos_consumo`) só executa dentro do bloco `if operacao.status == "REALIZADA":`. Quando a operação está `PLANEJADA` (originada de `SafraTarefa` via `gerar_operacao_planejada`), nenhum lote é debitado — o registro em `InsumoOperacao` é criado com `custo_unitario=0.0` e `custo_total=0.0` até a operação transicionar para `REALIZADA`. Isso está alinhado ao requisito de não movimentar estoque real durante o planejamento.

## 13. Vínculo com ERP

Não foi encontrada nenhuma referência a Sankhya/ERP nos módulos `operacoes`, `tarefas` ou `custos` — o fluxo de laudo→planejamento→execução→custo não depende de integração ERP em nenhum ponto revisado. Consistente com o requisito de ERP opcional/não bloqueante.

## 14. Matriz de cobertura

| Etapa | Situação | Evidência | Lacuna |
|---|---|---|---|
| Laudo vinculado ao talhão | IMPLEMENTADO | `AnaliseSolo.talhao_id` FK `cadastros_areas_rurais` | — |
| Laudo vinculado à safra | AUSENTE | `AnaliseSolo` não tem `safra_id`; só tem `production_unit_id` | Laudo não sabe a qual safra pertence diretamente |
| Resultado estruturado | IMPLEMENTADO | Campos químicos/físicos/micronutrientes tipados em `AnaliseSolo` | Sem campo de "diagnóstico calculado" persistido (CTC/V%/m% são colunas, mas não há tabela de "diagnóstico" derivado versionado) |
| Recomendação agronômica (de solo) | IMPLEMENTADO PARCIALMENTE | `RegraAgronomica` (model existe); `SafraTarefa.origem="SOLO"` documentado no docstring | Motor que cruza laudo × regra × gera tarefa não foi localizado explicitamente no código lido |
| Aprovação da recomendação | IMPLEMENTADO | `SafraTarefa.status`, `TarefasService.aprovar/rejeitar` | — |
| Geração de atividade planejada | IMPLEMENTADO | `SafraTarefa` é a própria atividade planejada | — |
| Custo planejado | IMPLEMENTADO | `custo_estimado` (tarefa) + `ItemOrcamentoSafra` (orçamento) | Falta granularidade custo/talhão explícita em `ItemOrcamentoSafra` (vínculo é cultivo/PU) |
| Conversão em execução | IMPLEMENTADO | `gerar_operacao_planejada()` → `OperacaoAgricola(status="PLANEJADA")` | — |
| Envio ao Campo PWA | IMPLEMENTADO PARCIALMENTE | `TarefaCampo` existe e sincroniza offline | Sem FK declarada `TarefaCampo → SafraTarefa`; rastreabilidade reconstruída via `operacao.tarefa_id` |
| Consumo real de estoque | IMPLEMENTADO | Débito FIFO só quando `status == "REALIZADA"` | — |
| Custo realizado | IMPLEMENTADO | `InsumoOperacao.custo_total`, `CostAllocation`, `custo_total_realizado` | — |
| Planejado versus realizado | IMPLEMENTADO | `CustosService.get_resumo_safra()` → `desvio_orcamento_pct` | Comparação é agregada por safra, não por talhão/tarefa individual |
| Rastreabilidade ponta a ponta | IMPLEMENTADO PARCIALMENTE | `analise_solo_id → SafraTarefa → operacao_id → InsumoOperacao/CostAllocation` | Quebra na etapa Campo PWA (sem FK) e ausência de eventos de domínio para auditoria/timeline |

## 15. Lacunas reais

1. `AnaliseSolo` sem `safra_id` — impede consultar "laudos desta safra" diretamente (hoje depende de `talhao_id`/`production_unit_id` + range de datas).
2. `AnaliseSolo` sem `status`/aprovação/versionamento/responsável técnico — o laudo em si nunca é "aprovado"; só a tarefa gerada a partir dele passa por aprovação.
3. Motor de geração automática regra-agronômica → `SafraTarefa` (origem `SOLO`) não localizado com evidência de código direta — pode existir em `alertas`/`alert_engine`/`inteligencia_operacional`, não cobertos a fundo nesta auditoria; recomenda-se confirmação dirigida.
4. `TarefaCampo` sem FK para `SafraTarefa` — rastreabilidade planejamento→campo depende de convenção de aplicação, não de integridade referencial.
5. Nenhum evento de domínio publicado nos marcos do fluxo (laudo, aprovação, operação planejada, execução concluída, custo atualizado) — dificulta auditoria/timeline e integrações futuras (notificações, caderno de campo automatizado).
6. Comparação planejado×realizado é agregada por safra; não há endpoint/visão explícita por talhão ou por tarefa individual.

## 16. Duplicidades ou conflitos

1. **Frontend**: 3 rotas distintas de "análises de solo" fora do contexto de safra (`agricola/analises-solo`, `dashboard/agricola/analises-solo`, `dashboard/agricola/analises_solo`) além da rota correta `agricola/safras/[id]/analises-solo`. DUPLICADO — candidatas a consolidação/depreciação.
2. **Frontend**: duas rotas de "recomendações" (`dashboard/agricola/recomendacoes` e `dashboard/inteligencia-operacional/recomendacoes`) — não confirmado se são a mesma feature ou features distintas; requer checagem.
3. **Backend**: `agricola/prescricoes/models.py.bak` (arquivo desativado) coexiste com `agricola/amostragem_solo/models/prescricoes_vra.py` (`PrescricaoVRA` ativo) — mesmo nome de classe/tabela em dois lugares, um deles morto. Risco de confusão para quem for estender agricultura de precisão.
4. **Conceitual**: módulos `agricola/recomendacoes` e `agricola/diagnostico` usam nomenclatura que sugere "recomendação/diagnóstico agronômico", mas são na verdade motores econômico-operacionais (benchmark de safra/DRE) — não devem ser reaproveitados como se fossem o motor de recomendação de correção de solo, sob risco de sobrepor conceitos diferentes com o mesmo nome.

## 17. Riscos

- Se o motor de geração automática de tarefa a partir do laudo (`origem="SOLO"`) não existir de fato (apenas o campo/enum preparado), a promessa "laudo → tarefa automática" é hoje apenas manual (o agrônomo cria a `SafraTarefa` manualmente referenciando `analise_solo_id`), o que muda a resposta ao veredicto de "SIM" para "parcial" nesse sub-fluxo específico.
- Ausência de eventos de domínio é um risco de rastreabilidade/observabilidade, não um bloqueio funcional.
- A falta de FK `TarefaCampo → SafraTarefa` é um risco de integridade: nada impede que uma tarefa de campo "solta" gere uma operação sem qualquer origem de planejamento formal, quebrando a exigência de rastreabilidade ponta a ponta em parte dos casos.
- Duplicidade de telas de análise de solo pode levar usuários a cadastrar laudos em uma tela não conectada à safra, quebrando a cadeia de rastreabilidade na prática (mesmo que o backend suporte o vínculo corretamente pela tela certa).

## 18. Recomendação do próximo passo

Não implementar nada agora. Caso a decisão seja avançar, plano proposto reaproveitando 100% da arquitetura existente (sem processo paralelo):

1. **Confirmar** (antes de qualquer código) se existe hoje algum job/service que consome `AnaliseSolo` + `RegraAgronomica` e cria `SafraTarefa(origem="SOLO")` automaticamente — buscar em `agricola/alertas`, `agricola/alert_engine` (raiz `alert_engine/`) e `agricola/inteligencia_operacional`, que não foram varridos em profundidade nesta auditoria.
2. Se não existir, adicionar esse motor como um `service` dentro do próprio `agricola/analises_solo` (ex.: `AnaliseSoloService.gerar_tarefas_recomendadas()`), reutilizando `RegraAgronomica` já modelada e o construtor `SafraTarefa(origem="SOLO", analise_solo_id=..., status="PENDENTE_APROVACAO")` já existente em `tarefas/service.py`.
3. Adicionar `safra_id` (nullable, FK `safras.id`, `ondelete=SET NULL`) e `status`/`aprovado_por`/`aprovado_em` a `AnaliseSolo` via migration Alembic incremental, seguindo o padrão do projeto (`op.execute("COMMIT")` após `run_sync`).
4. Adicionar `safra_tarefa_id` (nullable, FK `safra_tarefas.id`, `ondelete=SET NULL`) a `TarefaCampo`, populando-o no fluxo que hoje cria tarefas PROGRAMADA a partir de operações planejadas — sem alterar o modelo de sincronização offline existente.
5. Publicar eventos de domínio nos pontos-chave já instrumentáveis (`TarefasService.aprovar`, `gerar_operacao_planejada`, `OperacaoService.criar` quando `status=REALIZADA`) usando o `events/outbox_service.py` já existente no monorepo — sem criar um sistema de eventos paralelo.
6. Expor endpoint de comparação planejado×realizado por talhão (variação de `CustosService.get_resumo_safra`, agrupando por `talhao_id` em vez de só por safra).
7. Consolidar as 3 rotas duplicadas de "análises de solo" no frontend em uma única, redirecionando/depreciando as demais.

Nenhuma dessas ações requer reabrir a arquitetura multiprovider de ERP, TenantIntegracao, estoque operacional, separação planejamento/execução, Campo PWA offline-first ou hierarquia territorial — todas reaproveitam tabelas, services e padrões já existentes.
