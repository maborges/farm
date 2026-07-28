# Épico: Planejamento Operacional de Tarefas (produto + estoque + mão de obra)

> Status: **capturado em brainstorming, aguardando priorização**. Não tem desenho de banco/UI ainda —
> este documento é o ponto de partida para retomar o assunto depois.

## Contexto / dor identificada

Hoje o pipeline de tarefas agrícolas tem uma lacuna estrutural entre "o que a tarefa precisa"
(sabido em texto/dose) e "o que será de fato consumido" (decidido manualmente, tarefa por tarefa,
só na hora de gerar a OS):

- `SafraTarefa` (origem SOLO) já carrega dose estruturada (`dose_estimada_kg_ha`,
  `quantidade_total_estimada_kg`, `custo_estimado`), mas **não tem `produto_id`** — nenhuma FK para
  `cadastros_produtos`. Custo estimado usa preços de mercado hardcoded no service
  (`agricola/analises_solo/service.py`, dict `PRECOS`), não o catálogo real.
- Na geração da OS (`PlanejarOperacaoRequest` → `TarefaService.gerar_operacao_planejada`,
  `agricola/tarefas/service.py`), o usuário escolhe produto e digita dose **do zero** — a dose já
  calculada na tarefa não é lida nem usada para pré-preencher nada.
- Não existe nenhum conceito de "planejamento agregado": cada tarefa é tratada isoladamente. Não há
  visão consolidada de quanto de cada produto será necessário somando várias tarefas da mesma
  safra/UP/talhão, nem checagem de disponibilidade em estoque, nem disparo de solicitação de compra,
  nem estimativa de mão de obra necessária.
- `SafraTarefa` não tem `operador_id` nem custo de mão de obra — operador só aparece depois, em
  `PlanejarOperacaoRequest.operador_id`, sem cálculo de custo associado.

## Decisões já validadas nesta conversa

1. **Produto não é padrão automático** — o usuário sempre escolhe manualmente qual produto usar
   (não existe, e não deve existir por ora, um "produto preferido por nutriente" automático).
2. **Momento da escolha do produto**: não é na criação da tarefa nem isoladamente na aprovação —
   é dentro de uma etapa própria de **planejamento**, onde o usuário já vê a disponibilidade em
   estoque antes de decidir.
3. **Escopo do planejamento é em LOTE, não por tarefa individual**: uma tela nova onde o usuário
   seleciona um conjunto de tarefas aprovadas (ex.: mesma safra/UP, "próxima semana") e o sistema
   mostra de cara:
   - total consolidado de cada produto necessário (somando as tarefas selecionadas);
   - o que falta comprar (comparando com estoque disponível);
   - mão de obra total estimada.
4. **Planejamento parcial é uma feature, não um caso de borda**: o usuário deve poder aprovar/
   programar só as tarefas cujo material já está disponível, deixando as demais aguardando compra —
   ou seja, o lote selecionado não precisa ser "tudo ou nada".
5. **Um talhão continua sendo uma tarefa própria — o agrupamento é só na camada de planejamento**:
   quando várias tarefas (ex.: da mesma análise de solo, ou de um mesmo evento de manejo) se aplicam
   a vários talhões — às vezes todos com o mesmo tratamento, às vezes com pequenas variações por
   talhão —, o sistema continua criando **N `SafraTarefa` individuais (uma por talhão)**, nunca uma
   tarefa "guarda-chuva" cobrindo vários talhões. Isso preserva histórico, performance e gestão de
   equipe por talhão individualmente (inclusive no PWA de campo, onde a execução é sempre por
   talhão). O que muda é que a tela de **planejamento em lote** (item 3) precisa saber agrupar/
   consolidar visualmente N tarefas-irmãs (mesma origem/evento, talhões diferentes) para mostrar o
   total de produto necessário somado — a agregação é uma visão, não uma nova entidade que substitui
   a tarefa por talhão.

## Perguntas em aberto para quando o épico for retomado

- O planejamento em lote gera algum registro próprio no banco (ex.: "PlanoOperacional" agrupando
  N tarefas) ou é só uma tela de agregação em cima de tarefas que continuam sendo entidades
  independentes?
- Como fica a integração com Compras (`operacional/routers/compras.py`) — a solicitação de compra
  disparada a partir do planejamento é automática (cria requisição) ou só sugere e o usuário decide?
- Estimativa de mão de obra: baseada em quê (histórico de horas por tipo de operação × área? uma
  tabela de referência por tipo de serviço)? Isso depende do `TipoServico` mencionado no plano
  já existente de snapshot de custo (`~/.claude/plans/declarative-discovering-lollipop.md`), que
  também ainda não foi implementado.
- Esse planejamento em lote deveria reaproveitar o `SnapshotCustoService` desenhado no plano de
  orçamento (snapshot de custo unitário de Produto/Máquina/Pessoa), para manter uma única fonte de
  cálculo de custo estimado em todo o sistema, em vez de duas lógicas paralelas?
- Como identificar "tarefas-irmãs" (mesmo evento/origem, um talhão cada) para agrupar na tela de
  planejamento? Confirmado no código: `AnaliseSolo.talhao_id` é obrigatório e único por análise
  (`agricola/analises_solo/models.py`) — uma amostra de solo é sempre de um talhão específico. Ou
  seja, analisar 5 talhões gera **5 registros `AnaliseSolo` diferentes**, cada um com seu próprio
  `analise_solo_id` amarrado às `SafraTarefa` que ele gera. **Não existe hoje nenhum campo que ligue
  essas 5 tarefas entre si** como "vieram da mesma rodada de planejamento" — o sistema sabe que a
  tarefa X veio da análise A (talhão 1) e a tarefa Y veio da análise B (talhão 2), mas não sabe que
  A e B foram feitas juntas, pela mesma decisão de manejo. Duas opções para resolver isso:

  **Opção 1 — campo explícito de lote (`lote_geracao_id` ou similar)**
  - O quê: ao gerar tarefas para vários talhões na mesma ação/tela (ex.: "gerar tarefas para os
    talhões selecionados a partir das análises de solo"), todas as `SafraTarefa` resultantes recebem
    um mesmo `lote_geracao_id` (novo `UUID`, gerado uma vez por chamada em lote).
  - Prós: agrupamento é exato e sem ambiguidade — reflete literalmente "o usuário pediu isso junto".
    Funciona igual para qualquer origem de tarefa (SOLO, TEMPLATE, MANUAL em lote), não só solo.
    Consulta trivial (`WHERE lote_geracao_id = X`).
  - Contras: exige migration (nova coluna + índice em `safra_tarefas`) e mexer em todos os pontos que
    hoje criam tarefa a partir de análise de solo (e possivelmente outros fluxos de criação em lote),
    para passar/gerar esse ID.
  - Quando escolher: se o fluxo de "planejar vários talhões de uma vez" for uma ação de UI clara e
    deliberada (usuário seleciona N talhões, clica um botão, tarefas nascem juntas) — o que parece
    ser exatamente o caso aqui.

  **Opção 2 — heurística sem campo novo (agrupar por coincidência de atributos)**
  - O quê: na tela de planejamento em lote, agrupar tarefas por combinação de `safra_id` + `tipo` +
    janela de tempo de criação (ex.: mesma safra, mesmo tipo de operação, criadas no mesmo dia ou
    dentro de uma janela de poucas horas).
  - Prós: não exige migration nem alterar os fluxos de criação — é só uma query/lógica na tela nova.
  - Contras: frágil. Pode juntar tarefas que não deveriam estar juntas (duas rodadas de análise de
    solo diferentes, feitas em datas próximas, mesmo tipo de tarefa) ou deixar de juntar tarefas que
    deveriam estar juntas (usuário aprova os talhões em dias diferentes, ou o lote é gerado ao longo
    de uma janela maior que a heurística prevê). Também não generaliza bem para origens que não sejam
    SOLO.
  - Quando escolher: só como atalho temporário se o custo de uma migration for inaceitável no curto
    prazo — não recomendado como solução definitiva.

  **Inclinação registrada nesta conversa**: Opção 1 (campo explícito) é a mais robusta, mas a decisão
  final depende de como a tela de geração de tarefas em lote for desenhada (ainda não desenhada).

## Relacionado

- Plano já desenhado (não implementado): `~/.claude/plans/declarative-discovering-lollipop.md`
  (Snapshot de custo no orçamento de safra — mesma ideia de vincular Produto/Máquina/Pessoa com
  snapshot imutável, só que no lado financeiro/orçamento em vez do operacional/tarefa).
- `docs/brainstorm-analise-solo-evolucao.md` — pode já ter contexto de evolução do módulo de
  análise de solo relevante para este épico.
