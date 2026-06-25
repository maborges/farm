# EXECUTION-PECUARIA-30 - Análise de Convergência Campo, Dashboard Geral e Copiloto IA

Escopo desta análise: leitura de código e recomendação arquitetural/produto. Nenhuma funcionalidade foi implementada.

## 1. Diagnóstico do sync Agricultura x Pecuária

Agricultura e Pecuária compartilham o mesmo pipeline offline-first no Campo. A criação local de tarefas usa a mesma fábrica e a mesma fila de sync, com diferenciação por `module` e `type` apenas.

Pontos observados:

- A criação local passa por [`createTask`](</opt/lampp/htdocs/farm/apps/campo/src/lib/task-factory.ts:19>) e grava em `db.tasks` com `module`, `type`, `fazenda_id`, `talhao_id`, `lote_id` e `dados`.
- O sync de envio usa a mesma outbox em [`pushSync`](</opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts:9>) e separa apenas por `entity_type` entre `task` e `caderno_event`.
- O sync de recebimento usa o mesmo `pullSync` e normaliza `module` para `agricola` ou `pecuaria` em [`pullSync`](</opt/lampp/htdocs/farm/apps/campo/src/lib/sync/pull.ts:134>).
- O backend pecuário só processa tarefas com `module == "pecuaria"` e `status_execucao == "CONCLUIDA"` em [`ManejoSyncService.processar_tarefa_campo`](</opt/lampp/htdocs/farm/services/api/pecuaria/services/manejo_sync_service.py:42>).
- O planejamento pecuário já é tenant-aware e domínio-aware em [`ManejoPlanejamentoService`](</opt/lampp/htdocs/farm/services/api/pecuaria/services/manejo_planejamento_service.py:31>).

Resposta objetiva:

- Agricultura e Pecuária usam o mesmo pipeline de sync? Sim, no Campo o pipeline é único; o domínio é discriminado por campos de tarefa e por rotas de backend.
- Existem diferenças de contrato entre tarefas agrícolas e pecuárias? Sim. Agricultura alimenta caderno/operações e usa `talhao_id`; Pecuária usa `lote_id`, `area_id`, `produto_id`, `dose`, `unidade_medida` e `via_aplicacao`.
- Existe risco de uma tarefa pecuária poluir a UX agrícola? Baixo no sync, moderado na UI se a home continuar a tratar tudo como uma lista única sem badges claros.
- Existe risco de uma tarefa agrícola poluir a UX pecuária? Baixo no sync, moderado na navegação rápida do Campo porque a experiência compartilhada ainda expõe atalhos cruzados.
- Como o PWA deve organizar tarefas mistas? Lista única de tarefas do dia, mas agrupada visualmente por domínio, com badge explícito `Agricultura`/`Pecuária`.
- O operador deve ver lista única ou agrupada por domínio? Lista única na entrada; agrupamento por domínio dentro dela.
- Mudanças de UX recomendadas sem quebrar o fluxo atual? Badge de domínio em toda tarefa, agrupamento por seção, e atalhos rápidos consistentes para ambos os módulos.

### Observações técnicas que sustentam a conclusão

- A home atual filtra atividades por módulo em [`home/page.tsx`](</opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/home/page.tsx:19>), mas ainda mistura as tarefas recentes e pendências sem agrupamento explícito.
- O menu inferior já é consciente de módulo, porém a branch mista não oferece `Vacinação` em [`CampoBottomNav`](</opt/lampp/htdocs/farm/apps/campo/src/components/campo/bottom-nav.tsx:27>).
- A execução pecuária já diferencia `PESAGEM` e `VACINACAO` em [`PecuariaTaskExecution`](</opt/lampp/htdocs/farm/apps/campo/src/components/campo/pecuaria-task-execution.tsx:33>).

## 2. Diagnóstico UX do PWA Campo

O Campo já suporta fazendas mistas do ponto de vista técnico, mas a superfície ainda não está otimizada para isso.

### Fazenda somente agrícola

- Funciona de forma previsível.
- O conjunto de ações rápidas fica concentrado em agricultura.
- Não há ruído de pecuária, desde que o tenant não tenha módulos mistos.

### Fazenda somente pecuária

- Funciona corretamente.
- O atalho rápido expõe `Pesagem` e `Vacinação` no bottom nav.
- A home exibe tarefas pecuárias no mesmo padrão da lista de tarefas.

### Fazenda mista

- Funciona tecnicamente.
- A experiência fica menos clara porque a home e o bottom nav ainda não deixam evidente a separação semântica entre módulos.
- O principal risco de UX está na descoberta: o usuário pode não perceber rapidamente qual tarefa pertence a qual domínio.

Recomendações:

- A home deve permanecer única, mas com seções separadas por domínio.
- Deve existir badge visual de `Agricultura` e `Pecuária` em cards, títulos ou chips.
- A navegação rápida precisa ser simétrica no cenário misto; hoje a branch mista mostra `Aplicação` e `Pesagem`, mas não `Vacinação`.
- O operador deve continuar vendo uma lista operacional simples, não um fluxo duplicado por módulo.

Resposta objetiva:

- A home do PWA Campo suporta bem esses cenários? Tecnicamente sim, visualmente ainda de forma parcial.
- É necessário filtro por domínio? Sim, ao menos como agrupamento/ordenação visual.
- É necessário badge Agricultura/Pecuária? Sim, é a forma mais barata de reduzir ambiguidade.
- É necessário agrupamento por data, prioridade ou módulo? Sim, com prioridade e domínio como critérios principais; data como critério secundário.
- Como manter simplicidade operacional? Um único inbox de tarefas, poucas ações rápidas e contexto de domínio sempre visível.

## 3. Diagnóstico do Dashboard Geral

O Dashboard Geral hoje não é um painel neutro multi-domínio. Ele é um hub de `Copiloto IA` + financeiro + atalhos de módulos.

Evidências:

- O dashboard carrega primeiro resumo financeiro e insight financeiro em [`dashboard/page.tsx`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:89>).
- O modo visual alterna entre `Copiloto IA` e `Painel de Controle` em [`DashboardContent`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:151>).
- O conteúdo principal é dominado por cards financeiros, alertas, automações e módulo de Agricultura.
- A Pecuária já possui um dashboard dedicado em [`dashboard/pecuaria/page.tsx`](</opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:90>) com KPIs próprios de rebanho.

Resposta objetiva:

- O Dashboard Geral deve ser multi-domínio? Sim, mas por composição e contexto, não por mistura indiscriminada de métricas incompatíveis.
- Quais indicadores pecuários devem aparecer no Dashboard Geral? Apenas indicadores de alto nível e de baixa ambiguidade.
- Quais devem ficar apenas no módulo Pecuária? Indicadores zootécnicos detalhados e economia sanitária por lote.
- Como evitar cards vazios? Renderização condicional por presença real de dados e por módulo habilitado.
- Como evitar dashboard agrícola irrelevante em fazenda sem agricultura? O mesmo princípio: cards condicionais e fallback para módulos habilitados.

Conclusão de produto:

- O dashboard geral deve continuar sendo um ponto de entrada cross-domain.
- A profundidade analítica da Pecuária deve permanecer no dashboard próprio do módulo.
- Misturar tudo no dashboard geral aumenta ruído sem ganho proporcional.

## 4. Indicadores pecuários recomendados

Classificação sugerida para cada item:

| Indicador | Classificação | Motivo |
|---|---|---|
| Total de animais | Ambos | É um KPI de contexto útil tanto no dashboard geral quanto no módulo Pecuária. |
| Lotes ativos | Ambos | Serve como visão resumida da base produtiva. |
| Peso médio geral | Dashboard Pecuária | Exige contexto zootécnico e interpretação técnica. |
| GMD médio | Dashboard Pecuária | É indicador especializado e precisa de explicação de janela/método. |
| Custo sanitário total | Ambos | Bom candidato a visão resumida, desde que haja cobertura confiável. |
| Custo sanitário por cabeça | Dashboard Pecuária | Mais útil no contexto do rebanho/lote. |
| Custo sanitário por kg | Dashboard Pecuária | Muito analítico para o painel geral. |
| Custo sanitário por arroba | Não recomendado agora | Derivado e mais útil em análises específicas do módulo. |
| Tarefas pecuárias pendentes | Ambos | Alta utilidade operacional. |
| Vacinações realizadas | Ambos | Pode ser mostrado como volume resumido. |
| Alertas de manejo | Ambos | Deve ser resumido, com drill-down no módulo Pecuária. |
| Últimas pesagens | Dashboard Pecuária | Requer detalhe e sequência temporal. |
| Lotes com pior desempenho | Dashboard Pecuária | É análise comparativa; pode virar card avançado depois. |

Recomendação prática:

- No dashboard geral, mostrar no máximo 3 a 5 cards pecuários de alto sinal.
- No dashboard Pecuária, concentrar os indicadores técnicos, históricos e comparativos.

## 5. Papel do Copiloto IA na Pecuária

O Copiloto IA faz sentido primeiro como camada explicativa e de sugestão, não como executor.

Casos de uso recomendados agora:

- Explicar variações de GMD.
- Apontar lotes com custo sanitário acima do esperado.
- Comparar lotes entre si.
- Resumir vacinação por período.
- Identificar animais ou lotes sem pesagem recente.
- Sinalizar ausência de manejo sanitário recente.

Casos que dependem de mais dados:

- Comparação estatística robusta entre lotes.
- Benchmark por raça, sexo, categoria e regime de manejo.
- Sugestões de corte ou destino econômico.
- Recomendações ligadas a preços de mercado.

Casos perigosos e que devem ser proibidos agora:

- Criar tarefa automaticamente.
- Alterar estoque automaticamente.
- Alterar `EventoAnimal` automaticamente.
- Alterar custo/valoração automaticamente.
- Executar baixa de estoque sem confirmação humana.

Resposta objetiva:

- Quais casos de uso fazem sentido agora? Análise, explicação, alerta e resumo.
- Quais dependem de mais dados? Comparativos, benchmark e recomendações econômicas finas.
- Quais são perigosos? Execução autônoma e qualquer escrita em estoque/zootecnia/financeiro.
- Como o Copiloto deve apresentar recomendações? Como cards, justificativas curtas e links para a tela de origem.
- O Copiloto pode gerar rascunhos de manejo para aprovação humana? Sim, e esse é o caminho seguro para a próxima fase.

## 6. Regras de governança da IA

Regras recomendadas:

- A IA pode analisar.
- A IA pode resumir.
- A IA pode sugerir.
- A IA pode gerar rascunhos.
- A IA não pode executar sem confirmação humana.
- A IA não pode alterar dados zootécnicos diretamente.
- A IA não pode criar baixa de estoque diretamente.
- A IA não pode criar custo financeiro diretamente.

Regras complementares:

- Toda ação gerada por IA deve ser auditável.
- Toda sugestão deve apontar origem dos dados e intervalo temporal.
- Toda ação operacional precisa de confirmação explícita.

## 7. Riscos de UX

- Mistura visual de agricultura e pecuária sem agrupamento explícito.
- Bottom nav inconsistente em fazenda mista.
- Dashboard geral com excesso de cards financeiros e pouca sinalização pecuária.
- Cards vazios quando o tenant não tiver os dados de um domínio.
- Indicadores pecuários avançados aparecerem fora do contexto do módulo.

Mitigações recomendadas:

- Badges de domínio.
- Seções separadas por módulo.
- Renderização condicional.
- Copys curtas e operacionais.
- Drilling down claro para o dashboard Pecuária.

## 8. Riscos de arquitetura

- Acoplamento de UX do dashboard geral com dados financeiros já existentes.
- Crescimento de páginas genéricas com KPI de múltiplos domínios sem uma camada de composição.
- Regra de sync compartilhada exigir disciplina forte de `module` e `type`.
- Ampliação do escopo do Copiloto sem governança explícita.
- Cards de pecuária consumirem dados que ainda não têm densidade suficiente em todos os tenants.

Mitigações recomendadas:

- Manter `module` como chave primária de segregação semântica.
- Manter dashboards especializados por domínio.
- Usar dados somente quando houver cobertura suficiente.
- Versionar qualquer novo contrato de IA.

## 9. Roadmap recomendado

### Fase A - Convergência Campo

- Harmonizar home do Campo para fazendas mistas.
- Incluir badges de domínio.
- Corrigir atalhos rápidos simétricos.
- Validar lista única com agrupamento por módulo.

### Fase B - Dashboard Geral multi-domínio

- Adicionar cards condicionais por módulo habilitado.
- Expor apenas indicadores de alto sinal.
- Preservar cards agrícolas e financeiros existentes.
- Evitar telas vazias em tenants sem Pecuária.

### Fase C - Dashboard Pecuária

- Fortalecer indicadores por lote.
- Ranking de lotes.
- Custo sanitário e GMD.
- Histórico sanitário resumido.

### Fase D - Copiloto IA Pecuária

- Explicações de GMD.
- Alertas inteligentes.
- Resumos sanitários.
- Rascunhos de manejo com aprovação humana.

## 10. Próxima execução sugerida

Sugerir a próxima execução como uma iniciativa de UX e contrato de dados, não de automação:

- Primeiro, corrigir a convergência do Campo para fazendas mistas.
- Em seguida, transformar o dashboard geral em um hub cross-domain com cards condicionais.
- Só depois, iniciar um Copiloto Pecuária que gere rascunhos e explicações, sem escrita automática em estoque ou zootecnia.

