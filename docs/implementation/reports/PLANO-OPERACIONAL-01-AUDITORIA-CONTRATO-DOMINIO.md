# PLANO-OPERACIONAL-01 — Auditoria de Contrato de Domínio

> Auditoria arquitetural, somente leitura. Nenhum código, migration, modelo ou endpoint foi
> criado ou alterado neste trabalho. Todas as afirmações abaixo citam `arquivo:linha` do
> código real encontrado no repositório em 2026-07-26.

## 1. Resumo executivo — Veredicto: **GO COM RESSALVAS**

A camada `PlanoOperacional` é viável e não colide estruturalmente com o motor econômico já
consolidado (`SafraTarefa → OperacaoAgricola → OperacaoExecucao → CostAllocation`). O ponto de
integração real (`TarefaService.gerar_operacao_planejada`) já é a porta correta e única para
gerar OS a partir de tarefa — o plano deve chamá-la, não recriá-la.

Três ressalvas bloqueiam início direto de implementação sem ajuste de escopo:

1. **Reserva de estoque já existe parcialmente** — `ReservaEstoque`
   (`services/api/operacional/models/estoque.py:148-166`) já é a tabela mutável separada do
   ledger que o ponto A pede. Ela não deve ser recriada; deve ser estendida (produto+depósito já
   presentes; falta granularidade por item de plano/tarefa — ver §4).
2. **Ordem de lock entre `SafraTarefa.with_for_update()` e reserva de estoque** não tem hoje
   nenhuma convenção — porque hoje nada disputa lock com `gerar_operacao_planejada`. Precisa ser
   definida ANTES do primeiro código do plano (ponto B, §6).
3. **Preço hardcoded em análise de solo** (`PRECOS` dict) alimenta hoje `SafraTarefa.custo_estimado`
   e é usado por telas existentes — não pode ser removido sem plano de descontinuação (§7).

Não há motivo para NO-GO: nenhuma decisão fechada no escopo contradiz o código real. O ajuste de
maior impacto é reconhecer `ReservaEstoque` existente em vez de propor uma tabela nova do zero.

## 2. Estado atual comprovado (arquivo:linha)

- `SafraTarefa` (`agricola/tarefas/models.py:9-98`): sempre 1 talhão (`talhao_id`, linha 32-34,
  nullable mas semântica de 1:1), tem `dose_estimada_kg_ha`, `quantidade_total_estimada_kg`,
  `area_ha`, `custo_estimado` (linhas 65-68) — nenhum campo de produto comercial, nenhum
  `operador_id`, sem suporte a múltiplos insumos.
- `PlanejarOperacaoRequest` (`agricola/tarefas/schemas.py:83-88`): usuário escolhe
  `operador_id`, `maquina_id`, `implemento` e uma lista `insumos: list[PlanejarInsumoRequest]`
  (produto_id, dose_por_ha, unidade) inteiramente do zero — nenhuma leitura de
  `dose_estimada_kg_ha`/`quantidade_total_estimada_kg` da tarefa (confirmado lendo
  `gerar_operacao_planejada`, linhas 603-709: `tarefa.area_ha` só é usado para
  `area_aplicada`, nunca a dose estimada).
- `TarefaService.gerar_operacao_planejada` (`agricola/tarefas/service.py:603-709`):
  - Lock de linha via `with_for_update()` (linha 607-611) já existe, motivado por duplo-clique.
  - Exige `status == "APROVADA"` (614-618) e `talhao_id is not None` (619-623).
  - Idempotente: se já existe `OperacaoAgricola` PLANEJADA para a tarefa, reaproveita e só
    garante o vínculo `TarefaCampo` (636-663) — não gera duplicata.
  - Cria `OperacaoAgricola` via `OperacaoService.criar` (693-694) e espelha em
    `TarefaCampo` via `TarefaProgramadaService.criar_vinculada_operacao` (696-708).
- `OperacaoAgricola`/`OperacaoExecucao`/`InsumoOperacao` (`agricola/operacoes/models.py:8-125`):
  `OperacaoAgricola.tarefa_id` (linha 17) é o único vínculo formal com `SafraTarefa`.
  `InsumoOperacao` já tem `produto_id`, `lote_estoque_id`, `custo_unitario`, `custo_total`
  (linhas 107-118) — ou seja, a granularidade "produto real + custo real" já existe na OS, só
  não é alimentada a partir de nenhum planejamento agregado.
- `OperacaoService.hard_delete` (`agricola/operacoes/service.py:1202-1226`) e
  `_reverter_efeitos_economicos_operacao` (linhas 375-427): confirmado — operação com
  `OperacaoExecucao` que tem `EstoqueMovimento` vinculado (`_execucao_ids_com_ledger`,
  linhas 354-373) **nunca é excluída fisicamente**; `hard_delete` recusa com
  `BusinessRuleError` (linhas 1218-1223). Reversão de efeitos econômicos é feita via
  lançamento de estorno, não via DELETE/UPDATE no ledger.
- `CostAllocation` (`agricola/custos/models.py:11-41`): já desacoplado de `Despesa` genérica;
  aponta para `operation_execution_id`, `inventory_movement_id`, `fin_rateio_id` — confirma a
  decisão já fechada de não recriar `Despesa` para operação agrícola.
- `EstoqueMovimento` (`operacional/models/estoque.py:169-231`): ledger append-only confirmado
  por comentário de classe (linha 170) e pela trigger `tg_estoque_movimentos_append_only`
  (criada em `migrations/versions/step18_estoque_movimentos.py:130`, BEFORE UPDATE OR DELETE).
  Correção só via `ajuste_de` (linha 199-201).
- **`ReservaEstoque` já existe** (`operacional/models/estoque.py:148-166`): tabela separada,
  mutável, com `status` ATIVA/CONSUMIDA/CANCELADA (linha 164), `referencia_tipo`/`referencia_id`
  genéricos (161-162, já cobre "ORDEM_SERVICO"/"PEDIDO_COMPRA"/"SAFRA"), `produto_id`+
  `deposito_id`+`quantidade`. Implementada em
  `operacional/services/estoque_service.py:1446-1530` (`criar_reserva`, `cancelar_reserva`,
  `consumir_reserva`, `listar`). **Não há hoje nenhum caller em `agricola/` usando essa
  reserva** (grep confirma uso só dentro de `operacional/` e cadastro de produtos) — ou seja, a
  infraestrutura de reserva existe mas está desconectada do fluxo agrícola.
- `SaldoEstoque.quantidade_reservada` (`operacional/models/estoque.py:39`) já existe como campo
  agregado — mas não está confirmado neste código lido se `criar_reserva`/`consumir_reserva`
  mantêm esse campo sincronizado com a soma de `ReservaEstoque` ativas (fora do escopo desta
  leitura; sinalizar para fase de implementação).
- `agricola/analises_solo/service.py:195-200` e `:589` — dict `PRECOS` hardcoded (CALCARIO,
  P2O5, K2O, N), com comentário explícito `# TODO: Buscar de cadastros_produtos.preco_medio se
  possível` (linha 194). Usado para calcular `custo_cal`/`custo_p`/`custo_k`/`custo_n`
  (linhas 244, 269, 298, 359 e réplica em 601-679) — esse valor é o que hoje popula
  `SafraTarefa.custo_estimado` para tarefas de origem SOLO.
- `TipoServico` (`core/cadastros/tipos_servico/models.py:12-42`): catálogo mestre já existe,
  com `tenant_id` nullable (catálogo global, linha 21-24 — mesmo padrão de Produto),
  `custo_referencia` (Numeric). Já é referenciado como fonte de custo categoria SERVICO no
  orçamento de safra (`agricola/a1_planejamento`, conforme docstring linha 13-16) — mas
  `SafraTarefa` e `OperacaoAgricola` não têm nenhuma FK para `TipoServico` hoje.
  `operador_id` existe em `OperacaoAgricola` (linha 31-36, FK para `cadastros_pessoas`) e em
  `OperacaoExecucao` (linha 94) — mas sem custo/hora associado, sem `TipoServico`, sem
  `ColaboradorRH` explícito neste ponto.
- `TarefaCampo` (`campo/models.py:48-125`): já tem `safra_tarefa_id` e `operacao_agricola_id`
  (linhas 107-112) — a ponte agrícola↔Campo PWA citada no contexto já está implementada e é
  usada por `gerar_operacao_planejada` (via `criar_vinculada_operacao`,
  `campo/service.py:1394`) e por `CampoAgricolaSyncService._concluir_operacao_vinculada`
  (`campo/service.py:244`).
- **`SnapshotCustoService` não está implementado** — existe apenas como plano salvo em
  `/home/borgus/.claude/plans/declarative-discovering-lollipop.md`, cobrindo
  `agricola/a1_planejamento/snapshot_service.py` (ainda inexistente no repo). O plano já
  resolve: captura de custo por origem (PRODUTO/MAQUINA/PESSOA/SERVICO/MANUAL), imutabilidade
  pós-criação, e troca do "realizado" para `CostAllocation`. Isso é diretamente reaproveitável
  pelo Planejamento Operacional (mesmo padrão de snapshot, mesma tabela de origem "SERVICO"
  cobrindo `TipoServico`).
- `operacional/routers/compras.py`: módulo maduro — `SolicitacaoCompra` com itens, cotações,
  alocação e geração de pedidos (`/solicitacoes/{id}/itens`, `/alocar`, `/gerar-pedidos`,
  linhas 391-561), fornecedores, histórico de preços. Nenhum vínculo hoje com
  `SafraTarefa`/`PlanoOperacional` — `origem_tipo`/`origem_id` de `RequisicaoMaterial`
  (`estoque.py:121-122`) é o padrão análogo mais próximo para rastreabilidade a implementar.

## 3. Lacunas identificadas

- **Tarefa**: sem múltiplos insumos, sem mão de obra, sem grupo de geração em lote.
- **Produto**: escolha de produto refeita do zero na OS; nenhuma leitura da dose técnica calculada.
- **Estoque**: sem visão agregada "necessidade de N tarefas vs. saldo disponível".
- **Reserva**: infraestrutura (`ReservaEstoque`) existe mas não é usada por nenhum fluxo agrícola;
  falta granularidade por item de plano e vínculo com `SafraTarefaNecessidade`.
- **Compras**: sem contrato formal ligando "necessidade do plano" a "item de solicitação de
  compra" — risco de duplicar solicitação se não houver idempotência (`origem_tipo`/`origem_id`).
- **Mão de obra**: `TipoServico` existe isolado do fluxo agrícola; `operador_id` sem custo.
- **Custos**: 3 fontes de custo estimado coexistirão (`SafraTarefa.custo_estimado` com preço
  hardcoded, `PlanoOperacionalTarefaInsumo.custo_total_estimado` com produto real,
  `SnapshotCustoService` ainda não implementado) — precisa de UI/regra explícita (ponto D).
- **Operações**: `gerar_operacao_planejada` não aceita hoje "múltiplos insumos pré-calculados
  vindos de um plano" de forma estruturada — hoje recebe `PlanejarOperacaoRequest.insumos`
  digitado manualmente; o plano precisa alimentar essa mesma lista, não substituí-la.
- **Campo**: nenhuma lacuna estrutural — a ponte `TarefaCampo` já suporta o padrão
  "tarefa individual gera 1 OS gera 1 TarefaCampo"; o plano não deve tocar essa ponte, apenas
  disparar `gerar_operacao_planejada` na hora certa.
- **Financeiro**: `CostAllocation` já é o destino correto; nenhuma lacuna, apenas necessidade de
  não duplicar (reafirma decisão já fechada nº 3).

## 4. Modelo de domínio recomendado (ajustes ao modelo conceitual)

Mantém-se o modelo conceitual da tarefa, com 2 ajustes justificados por evidência de código:

1. **Reserva**: usar/estender `ReservaEstoque` (já existe) em vez de criar uma tabela nova do
   zero. Adicionar a essa tabela (via migration, fora do escopo deste relatório):
   `plano_operacional_tarefa_insumo_id` (nullable) para granularidade por item de plano, mantendo
   `referencia_tipo="PLANO_OPERACIONAL"` / `referencia_id=plano_operacional_tarefa_insumo.id`
   como já é o padrão genérico da tabela (linhas 160-162). Isso evita duplicar conceito.
2. **Custo de serviço/mão de obra**: `PlanoOperacionalTarefaMaoObra.tipo_servico_id` deve
   referenciar `cadastros_tipos_servico.id` (já existe), reaproveitando `custo_referencia` como
   `custo_hora_snapshot` inicial — consistente com o padrão de origem "SERVICO" já desenhado no
   plano do `SnapshotCustoService`.

Demais entidades do modelo conceitual (`PlanoOperacional`, `PlanoOperacionalTarefa`,
`SafraTarefaNecessidade`, `PlanoOperacionalTarefaInsumo`, `grupo_geracao_id` em `SafraTarefa`)
são viáveis sem alteração — nenhuma colide com FK/índice/trigger existente.

**Responsabilidades**: `PlanoOperacional` = decisão/programação agregada (não persiste dose
técnica, só referencia `SafraTarefaNecessidade`). `SafraTarefaNecessidade` = saída técnica pura
(não tem produto, não tem custo real). `PlanoOperacionalTarefaInsumo` = ponte comercial (produto
+ custo + disponibilidade). `TarefaService.gerar_operacao_planejada` continua sendo o único
gerador de `OperacaoAgricola`, agora invocado pelo `PlanoOperacional` passando os insumos já
resolvidos como `PlanejarOperacaoRequest.insumos`.

## 5. Fluxo de estados

- **Plano**: RASCUNHO (simulação, sem reserva) → EM_ANALISE → PARCIALMENTE_PRONTO/PRONTO →
  APROVADO (congela custo, pode gerar reservas) → EM_EXECUCAO → CONCLUIDO/CANCELADO.
- **PlanoOperacionalTarefa**: NAO_ANALISADA → AGUARDANDO_DEFINICAO → PRONTA |
  AGUARDANDO_COMPRA → PROGRAMADA (dispara `gerar_operacao_planejada`) → (segue ciclo de vida do
  `SafraTarefa`/`OperacaoAgricola` já existente) | REMOVIDA/CANCELADA.
- **Reserva** (`ReservaEstoque.status`): ATIVA (criada na aprovação/programação, dentro da mesma
  transação que revalida saldo) → CONSUMIDA (quando a OS gera `EstoqueMovimento` real via FIFO)
  | CANCELADA (replanejamento/cancelamento libera saldo).
- **Compra**: necessidade → confirmação explícita do usuário → item de
  `SolicitacaoCompra`/`ItemRequisicao` com `origem_tipo="PLANO_OPERACIONAL"`,
  `origem_id=plano_operacional_tarefa_insumo.id` — idempotência garantida checando se já existe
  item ativo com essa combinação antes de criar novo (mesmo padrão de
  `RequisicaoMaterial.origem_tipo/origem_id`).
- **Operação**: inalterado — `PLANEJADA → REALIZADA`, ciclo já existente em `OperacaoAgricola`.

## 6. Contrato de integração e resposta aos pontos A/B/C/D

**Fluxo**: `SafraTarefa` (+`SafraTarefaNecessidade`) → `PlanoOperacional`/
`PlanoOperacionalTarefa`/`PlanoOperacionalTarefaInsumo` (reserva via `ReservaEstoque`) →
`TarefaService.gerar_operacao_planejada` (inalterado, recebe insumos já resolvidos) →
`OperacaoAgricola`/`OperacaoExecucao` → consumo FIFO real → `CostAllocation`.

- **Ponto A (confirmado)**: reserva NUNCA é linha em `estoque_movimentos` — confirmado pela
  trigger append-only (`step18_estoque_movimentos.py:130`). A tabela correta já existe
  (`ReservaEstoque`, `operacional/models/estoque.py:148-166`) e deve ser estendida, não
  recriada. Desenho da extensão: adicionar `plano_operacional_tarefa_insumo_id UUID NULL FK` e
  usar `referencia_tipo="PLANO_OPERACIONAL"` (compatível com o campo genérico já existente).

- **Ponto B (convenção proposta)**: adotar ordem fixa **lockar reserva/estoque primeiro,
  `SafraTarefa` depois**. Justificativa: `gerar_operacao_planejada` já lockeia
  `SafraTarefa` com `with_for_update()` no início do método (linha 607-611) e não pode ser
  reordenado sem tocar código de produção testado. Logo, o fluxo do plano deve: (1) abrir
  transação, (2) `SELECT ... FOR UPDATE` na(s) linha(s) de `ReservaEstoque`/`SaldoEstoque`
  relevantes e revalidar saldo, (3) só então chamar `gerar_operacao_planejada` (que por sua vez
  lockeia `SafraTarefa`). Essa ordem — reserva/estoque antes de tarefa — deve ser documentada
  como convenção obrigatória em todo código futuro que combine as duas operações, para evitar
  que uma segunda rotina implemente a ordem invertida e crie deadlock cruzado.

- **Ponto C (guardrail nomeado: "NO-HARD-DELETE-COM-LEDGER")**: confirmado lendo
  `_execucao_ids_com_ledger` e `hard_delete` (`agricola/operacoes/service.py:354-373,
  1202-1226) — uma `OperacaoAgricola`/`OperacaoExecucao` com `EstoqueMovimento` real vinculado
  nunca pode ser excluída fisicamente (a FK `ON DELETE SET NULL` geraria UPDATE bloqueado pela
  trigger). **Guardrail NO-HARD-DELETE-COM-LEDGER**: qualquer operação de "cancelar plano",
  "remover tarefa do plano" ou "replanejar" deve, ao encontrar uma `OperacaoAgricola` já com
  execução real, usar transição de status (ex.: manter `REALIZADA`, apenas desvincular do plano
  ou marcar a `PlanoOperacionalTarefa` como CANCELADA) — nunca invocar `hard_delete` sobre ela.
  Isso deve ser um teste automatizado obrigatório (ver §11).

- **Ponto D (resposta com justificativa)**: **mostrar os dois valores lado a lado durante a
  transição**, com rótulos explícitos "estimativa agronômica" (`SafraTarefa.custo_estimado`) e
  "estimativa de planejamento" (`PlanoOperacionalTarefaInsumo.custo_total_estimado`) — não
  ocultar o campo antigo. Justificativa: `SafraTarefa.custo_estimado` é gravado no momento da
  criação da tarefa (muitas vezes antes de qualquer plano existir) e serve hoje a telas/relatórios
  fora do escopo desta auditoria; ocultá-lo silenciosamente quebraria consumidores não mapeados.
  Quando a tarefa entra em um `PlanoOperacionalTarefa`, a UI deve destacar visualmente a
  estimativa de planejamento como a "mais confiável" (fonte: produto real) sem apagar a outra.
  Descontinuação de `SafraTarefa.custo_estimado` fica condicionada à resolução do preço
  hardcoded (§7) — dois problemas com a mesma causa raiz (preço não confiável), não devem ser
  resolvidos com uma decisão isolada de UI.

## 7. Estratégia de compatibilidade

- `SafraTarefa.custo_estimado` continua sendo calculado como hoje (preço hardcoded) até que
  exista alternativa; nenhuma migração de dados históricos é necessária porque o campo não muda
  de significado.
- Preço hardcoded (`PRECOS` dict, `agricola/analises_solo/service.py:195-200,589-592`): manter
  como fallback explícito e **sinalizar `CUSTO_INCOMPLETO`** (novo campo/flag na recomendação,
  não um novo motor de custo) quando não houver `preco_medio` cadastrado em `cadastros_produtos`.
  Migração incremental: (1) tentar `ProdutoService` por nutriente/categoria antes de cair no
  dict; (2) manter o dict só como último recurso, já sinalizado; (3) remover o dict somente
  quando 100% dos tenants tiverem produtos correspondentes cadastrados (medir antes de remover).
  Não descontinuar de uma vez — hoje o dict é a única fonte de custo para SafraTarefa de origem
  SOLO; remover sem fallback quebraria a criação de tarefas de solo.
- `grupo_geracao_id` em `SafraTarefa`: coluna nova nullable, não quebra nada existente; tarefas
  antigas ficam com `NULL` (histórico não teve geração em lote — correto).
- `PlanoOperacional` é aditivo: tarefas fora de qualquer plano continuam funcionando exatamente
  como hoje (fluxo individual direto tarefa→`gerar_operacao_planejada`, sem plano).
- Implantação incremental sugerida: Fase 1 modelos+CRUD sem reserva nem compra (cabeçalho e
  associação de tarefas); Fase 2 `SafraTarefaNecessidade`+múltiplos insumos; Fase 3 reserva
  (extensão de `ReservaEstoque`); Fase 4 integração com compras; Fase 5 mão de obra; Fase 6
  snapshot de custo (reaproveitando `SnapshotCustoService` do plano já existente).

## 8. Guardrails

- **Concorrência**: convenção de ordem de lock do ponto B, nomeada e documentada em código
  (docstring do método que orquestra plano→OS).
- **Idempotência**: reuso do padrão `origem_tipo`/`origem_id` já usado em `RequisicaoMaterial`
  e `CostAllocation` para evitar solicitação de compra duplicada; reuso do padrão de
  `_tarefa_solo_ativa_existente` (`agricola/tarefas/service.py:165-180`) como precedente de
  "idempotência por chave lógica" já aceito no projeto.
- **Tenant/RLS**: todo novo modelo segue o padrão obrigatório (`tenant_id` FK CASCADE,
  `BaseService` injeta filtro), sem exceção.
- **Integridade**: `SafraTarefa` continua sempre 1 talhão — nenhuma FK nova a talhão múltiplo.
- **Guardrail nomeado NO-HARD-DELETE-COM-LEDGER** (ponto C, §6): obrigatório em qualquer rotina
  de cancelamento/replanejamento do plano.
- **Guardrail LOCK-RESERVA-ANTES-DE-TAREFA** (ponto B, §6): obrigatório em qualquer rotina que
  combine reserva de estoque e `gerar_operacao_planejada` na mesma transação.

## 9. Plano de implementação em fases pequenas e auditáveis

1. Migration + modelos: `PlanoOperacional`, `PlanoOperacionalTarefa` (sem reserva/compra ainda).
2. `SafraTarefaNecessidade` + `grupo_geracao_id` em `SafraTarefa` (migration separada, aditiva).
3. `PlanoOperacionalTarefaInsumo` com saldo/disponibilidade (leitura de `SaldoEstoque`, sem
   reserva ainda — só simulação em RASCUNHO).
4. Extensão de `ReservaEstoque` (nova coluna `plano_operacional_tarefa_insumo_id`) + serviço de
   aprovação parcial (reserva real, revalidação de saldo na transação, lock conforme ponto B).
5. Integração com compras: geração de item de solicitação com confirmação explícita e
   idempotência via `origem_tipo`/`origem_id`.
6. `PlanoOperacionalTarefaMaoObra` + vínculo com `TipoServico`.
7. Snapshot de custo: implementar `SnapshotCustoService` (conforme plano já existente) e
   reaproveitar para congelar custo do plano na aprovação.
8. UI: comparação "estimativa agronômica" × "estimativa de planejamento" (ponto D).

## 10. Arquivos previstos por fase (estimativa)

- `services/api/migrations/versions/<nova>_plano_operacional.py`
- `services/api/agricola/planejamento_operacional/models.py` (novo submódulo)
- `services/api/agricola/planejamento_operacional/schemas.py`
- `services/api/agricola/planejamento_operacional/service.py`
- `services/api/agricola/planejamento_operacional/router.py`
- `services/api/migrations/versions/<nova>_safra_tarefa_necessidade_grupo_geracao.py`
- `services/api/agricola/tarefas/models.py` (add `grupo_geracao_id`)
- `services/api/migrations/versions/<nova>_reserva_estoque_plano_operacional.py`
- `services/api/operacional/models/estoque.py` (extensão `ReservaEstoque`)
- `services/api/operacional/services/estoque_service.py` (métodos de reserva por plano)
- `services/api/operacional/routers/compras.py` (endpoint de vínculo necessidade→item)
- `services/api/agricola/a1_planejamento/snapshot_service.py` (implementação do plano já salvo)
- `services/api/main.py` (registro de router)
- `apps/web/.../agricola/planejamento-operacional/*` (telas)

## 11. Testes previstos (PostgreSQL, nunca SQLite)

- Unitário: cálculo de `quantidade_faltante`, transições de status do plano/tarefa-do-plano.
- Integração: aprovação parcial (subconjunto pronto vs. aguardando compra no mesmo plano).
- Integração: reserva revalida saldo na mesma transação (2 planos concorrentes disputando o
  mesmo produto — teste de deadlock/ordem de lock, ponto B).
- Integração: `NO-HARD-DELETE-COM-LEDGER` — cancelar plano cuja tarefa já gerou
  `OperacaoExecucao`+`EstoqueMovimento` real deve falhar softly (transição de status), nunca
  tentar `hard_delete`.
- Integração: idempotência de solicitação de compra (chamar 2x não duplica item).
- Isolamento de tenant obrigatório em todos os novos endpoints (`pytest -k tenant_isolation`).
- Regressão: tarefa fora de qualquer plano continua gerando OS via
  `gerar_operacao_planejada` sem alteração de comportamento.

## 12. Veredicto final

**GO COM RESSALVAS.** A base de código suporta a camada de Planejamento Operacional sem
recriar fluxo econômico paralelo e sem transformar `SafraTarefa` em entidade multi-talhão. As
três ressalvas (reaproveitar `ReservaEstoque` existente, fixar convenção de lock do ponto B, e
não remover o preço hardcoded sem fallback) devem ser resolvidas no desenho de cada fase, não
bloqueiam o início do trabalho.

---

### Confirmações finais

- Nenhum código foi alterado; nenhuma migration foi criada.
- Este documento foi baseado no código real encontrado no repositório, com paths e linhas
  citados em cada afirmação (§2).
- A solução recomendada não cria um segundo motor econômico paralelo — reaproveita
  `OperacaoAgricola`/`OperacaoExecucao`/`CostAllocation` e o `SnapshotCustoService` já planejado.
- Cada `SafraTarefa` continua individual, por um único talhão.
- O Planejamento Operacional (`PlanoOperacional`) é uma camada persistida de decisão/programação
  agregada, não um substituto de `SafraTarefa`/`OperacaoAgricola`.
- `git status --short` e `git diff --check` foram executados após a escrita deste relatório e
  confirmam que nenhum arquivo além deste relatório foi criado ou alterado por esta auditoria
  (as alterações pré-existentes de `git status` no início da sessão — `campo/models.py`,
  `campo/service.py`, `tarefas/router.py`, `tarefas/service.py` — são anteriores a este trabalho
  e não foram tocadas por esta auditoria).
