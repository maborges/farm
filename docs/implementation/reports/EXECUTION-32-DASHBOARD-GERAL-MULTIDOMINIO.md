# EXECUTION-32 — Dashboard Geral Multi-Domínio

## Resumo executivo

O Dashboard Geral atual ainda opera como um painel híbrido, mas com forte viés de safra, financeiro e IA. Ele não está modelado como um painel executivo neutro da fazenda. Hoje a página principal depende de `safra_id` para renderizar grande parte do conteúdo e dispara sincronizações e cards que pertencem mais ao fluxo financeiro/agronômico do que ao nível executivo geral.

O desenho recomendado para a próxima etapa é:

1. manter o Dashboard Geral como um painel de contexto da fazenda;
2. expor apenas indicadores consolidados e de baixa ambiguidade;
3. deixar métricas profundas de Agricultura e Pecuária nas telas especializadas;
4. usar seções condicionais por domínio, sem mostrar blocos vazios;
5. evitar que o dashboard dependa de uma safra ativa para ser útil.

## 1. Diagnóstico do Dashboard Atual

O ponto de entrada principal está em [apps/web/src/app/(dashboard)/dashboard/page.tsx:83](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:83). A página:

- carrega resumo financeiro em `/financeiro/lancamentos/resumo`;
- carrega insight financeiro/safra em `/financeiro/lancamentos/insight`;
- sincroniza plano de ação em `/financeiro/plano-acoes/sincronizar?safra_id=...`;
- sincroniza notificações em `/notificacoes/sincronizar?safra_id=...`;
- executa automações em `/automacoes/executar?safra_id=...`;
- exibe cards de IA, alertas e recomendações focados em safra;
- exibe lançamentos, histórico de automações e timeline de custos;
- exibe atalhos para Agricultura, Pecuária, Operacional e Financeiro;
- oferece um modo essencial de Copiloto IA.

O resultado prático é um dashboard que mistura:

- visão financeira;
- visão de safra;
- visão de copiloto/IA;
- navegação para módulos;
- poucos indicadores realmente executivos da fazenda.

Isso fica claro nos blocos de renderização da página: [apps/web/src/app/(dashboard)/dashboard/page.tsx:195](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:195), [apps/web/src/app/(dashboard)/dashboard/page.tsx:229](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:229) e [apps/web/src/app/(dashboard)/dashboard/page.tsx:239](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:239).

### Limitações atuais

- O dashboard depende de `safraId` para renderizar uma parte relevante dos cards.
- O conteúdo de IA é dominado por recomendação de safra, não por visão executiva multi-domínio.
- Não há uma seção pecuária executiva equivalente ao peso da seção agrícola/financeira.
- A página não separa claramente “indicador geral” de “indicador especializado”.
- Parte da experiência é mais “painel de trabalho” do que “painel executivo”.

## 2. Inventário

### 2.1 Dashboard geral atual

Arquivos principais:

- [apps/web/src/app/(dashboard)/dashboard/page.tsx:83](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/page.tsx:83)
- [apps/web/src/components/dashboard/user-performance-card.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/dashboard/user-performance-card.tsx:1)
- [apps/web/src/components/dashboard/resumo-diario-card.tsx:32](/opt/lampp/htdocs/farm/apps/web/src/components/dashboard/resumo-diario-card.tsx:32)
- [apps/web/src/components/dashboard/alertas-inteligentes-card.tsx:34](/opt/lampp/htdocs/farm/apps/web/src/components/dashboard/alertas-inteligentes-card.tsx:34)
- [apps/web/src/components/financeiro/insight-financeiro-card.tsx:38](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/insight-financeiro-card.tsx:38)
- [apps/web/src/components/financeiro/assistente-safra-card.tsx:34](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/assistente-safra-card.tsx:34)
- [apps/web/src/components/financeiro/plano-acao-card.tsx:31](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/plano-acao-card.tsx:31)
- [apps/web/src/components/financeiro/alertas-card.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/alertas-card.tsx:1)
- [apps/web/src/components/financeiro/recomendacoes-card.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/recomendacoes-card.tsx:1)
- [apps/web/src/components/financeiro/atividades-feed.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/atividades-feed.tsx:1)
- [apps/web/src/components/financeiro/automacoes-config-card.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/automacoes-config-card.tsx:1)
- [apps/web/src/components/financeiro/automacoes-historico-card.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/automacoes-historico-card.tsx:1)
- [apps/web/src/components/financeiro/cost-timeline-chart.tsx:1](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/cost-timeline-chart.tsx:1)
- [apps/web/src/components/ia/essential-card.tsx:47](/opt/lampp/htdocs/farm/apps/web/src/components/ia/essential-card.tsx:47)

Endpoints já usados por esse dashboard:

- `/financeiro/lancamentos/resumo`
- `/financeiro/lancamentos/insight`
- `/financeiro/plano-acoes/sincronizar?safra_id=...`
- `/notificacoes/sincronizar?safra_id=...`
- `/automacoes/executar?safra_id=...`
- `/ia/financeiro/resumo-diario?safra_id=...`
- `/financeiro/lancamentos/alertas-inteligentes?safra_id=...`
- `/financeiro/lancamentos/resumo-consultivo?safra_id=...`
- `/financeiro/plano-acoes/?safra_id=...`
- `/financeiro/lancamentos/alertas?safra_id=...`
- `/financeiro/lancamentos/recomendacoes?safra_id=...`
- `/atividades/?safra_id=...`
- `/automacoes/configuracoes?safra_id=...`
- `/automacoes/execucoes?safra_id=...`
- `/financeiro/lancamentos/serie-temporal?safra_id=...`
- `/ia/essencial?safra_id=...`

### 2.2 Dashboard agrícola especializado

O dashboard agrícola já é um painel próprio, com endpoint dedicado e lógica de domínio específica:

- [apps/web/src/app/(dashboard)/agricola/dashboard/page.tsx:390](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/dashboard/page.tsx:390)
- [apps/web/src/app/(dashboard)/agricola/dashboard/page.tsx:421](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/dashboard/page.tsx:421)

Ele usa `/agricola/dashboard/` e `/agricola/dashboard/verificar-alertas`, além de cards e rotas próprias do domínio agrícola. Isso confirma que o dashboard geral não deve duplicar métricas profundas já consolidadas no módulo agrícola.

### 2.3 Dashboard pecuário especializado

O dashboard pecuário já possui seu próprio painel executivo de rebanho:

- [apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:90](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:90)
- [apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:94](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:94)
- [apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:118](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:118)
- [apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:195](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/pecuaria/page.tsx:195)

Ele calcula e mostra:

- total de cabeças;
- lotes ativos;
- piquetes;
- peso médio;
- UA estimada;
- composição do rebanho;
- cabeças por raça;
- manejos recentes.

Isso é suficiente para classificar indicadores zootécnicos detalhados como especializados, não como núcleo do dashboard geral.

## 3. Classificação dos Indicadores

### 3.1 Geral

Devem poder aparecer no Dashboard Geral, desde que respeitem o contexto da fazenda:

- receitas;
- despesas;
- resultado;
- fluxo de caixa;
- tarefas pendentes;
- tarefas atrasadas;
- tarefas concluídas;
- tarefas em execução;
- quantidade de animais ativos;
- lotes ativos;
- área cultivada;
- safras ativas;
- operações pendentes;
- operações em andamento.

### 3.2 Especializado

Devem permanecer nos módulos especializados:

- GMD por lote;
- ranking de talhões;
- custo por arroba;
- composição do rebanho;
- cabeças por raça;
- DRE agrícola detalhado;
- cenários agrícolas;
- custo por animal em nível de lote;
- automações de safra;
- alertas inteligentes orientados por safra;
- análise diária com IA;
- visão operacional zootécnica de detalhe.

### 3.3 Condicional

Só devem aparecer quando o domínio existir na fazenda e quando houver dado útil para mostrar:

- animais ativos;
- lotes ativos;
- safras ativas;
- área cultivada;
- manejos pendentes;
- vacinações programadas;
- custo sanitário acumulado;
- últimas pesagens;
- atividade recente.

## 4. Recomendação de desenho

### 4.1 Seção financeira

Manter como primeira seção do dashboard geral.

Recomendação:

- manter um resumo financeiro consolidado;
- manter receita, despesa, resultado e fluxo de caixa;
- evitar puxar cards de detalhe de safra como conteúdo central;
- tratar o `InsightFinanceiroCard` como um bloco de apoio, não como o coração do painel.

Arquiteturalmente, o que existe hoje em [apps/web/src/components/financeiro/insight-financeiro-card.tsx:38](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/insight-financeiro-card.tsx:38) é aceitável como resumo, mas o restante do ecossistema de safra/IA deve ser deslocado para telas especializadas.

### 4.2 Seção agricultura

Exibir apenas se existir atividade agrícola.

Exemplos de cards recomendados:

- safras ativas;
- área cultivada;
- operações pendentes;
- operações em andamento.

Não recomendado para o dashboard geral:

- DRE agrícola detalhado;
- alertas de safra;
- cenários de safra;
- análises agronômicas profundas;
- cards de IA que dependem de `safra_id`.

### 4.3 Seção pecuária

Exibir apenas se existir atividade pecuária.

Exemplos de cards recomendados:

- animais ativos;
- lotes ativos;
- manejos pendentes;
- vacinações pendentes ou recentes;
- custo sanitário acumulado.

Não recomendado para o dashboard geral:

- GMD por lote;
- custo por arroba;
- ranking de lotes;
- composição do rebanho;
- análise detalhada de piquetes;
- relatório zootécnico completo.

### 4.4 Seção operacional

Criar uma visão transversal e neutra:

- tarefas pendentes;
- tarefas atrasadas;
- tarefas concluídas;
- tarefas em execução.

Essa seção é a melhor candidata para responder “como está a operação da fazenda neste momento?” sem cair em viés agrícola ou pecuário.

### 4.5 Seção de alertas

Não implementar agora.

A estrutura deve ser planejada para suportar:

- talhão sem operação;
- safra sem movimentação;
- lote sem pesagem;
- vacinação pendente;
- lote sem manejo;
- tarefas atrasadas.

O dashboard geral só deve reservar espaço semântica e visualmente para isso, sem introduzir a lógica ainda.

## 5. Compatibilidade multi-domínio

### Fazenda agrícola

Exibir:

- financeiro;
- agricultura;
- operacional.

Ocultar:

- pecuária.

### Fazenda pecuária

Exibir:

- financeiro;
- pecuária;
- operacional.

Ocultar:

- agricultura.

### Fazenda mista

Exibir:

- financeiro;
- agricultura;
- pecuária;
- operacional.

Sem mistura de métricas incompatíveis e sem blocos vazios.

## 6. Performance e riscos

### 6.1 Pontos baratos

Esses blocos tendem a ser baratos e fáceis de manter:

- contadores simples de tarefas;
- contadores simples de lotes;
- contadores simples de safras;
- resumo financeiro consolidado;
- cards condicionais com dados já agregados.

### 6.2 Pontos caros

Esses blocos tendem a ter custo alto ou risco de acoplamento:

- múltiplos fetches independentes em cards separados;
- sincronizações automáticas executadas ao abrir a página;
- cards safra-específicos com IA;
- histórico e timeline com muitas séries;
- agregações que dependem de varrer várias tabelas em tempo de requisição.

### 6.3 Riscos atuais

- excesso de queries no carregamento inicial;
- dependência forte de `safraId`;
- mistura de conteúdo executivo com conteúdo de execução;
- possível repetição de informação entre dashboard geral e dashboards especializados;
- baixa utilidade do dashboard para fazendas sem safra ativa;
- UX de fazenda mista sem separação semântica suficiente.

### 6.4 Direção recomendada

- consolidar dados de alto nível em menos blocos;
- condicionar seções por domínio;
- evitar cards de detalhe no dashboard geral;
- cachear agregações sempre que possível;
- manter painéis especializados como destino para drill-down.

## 7. Roadmap recomendado

### EXECUTION-32A — Cards

Objetivo:

- reorganizar o dashboard geral em cartões executivos;
- introduzir seções condicionais por domínio;
- manter conteúdo financeiro no topo;
- expor operacional transversal;
- reduzir o viés safra/IA.

### EXECUTION-33 — Central de alertas

Objetivo:

- transformar os alertas em uma central própria;
- consolidar alertas agrícolas, pecuários e operacionais;
- evitar misturar alertas com indicadores executivos.

### EXECUTION-34 — Copiloto IA

Objetivo:

- usar IA como camada analítica e sugestiva;
- permitir explicações e recomendações;
- impedir ações automáticas sem aprovação humana;
- manter o copiloto fora do caminho crítico de execução.

## 8. Conclusão

O Dashboard Geral precisa sair do papel de “dashboard de safra com extras” e virar um painel executivo de fazenda. A arquitetura correta é:

- financeiro primeiro;
- operacional transversal em seguida;
- agricultura e pecuária como seções condicionais;
- detalhes e inteligência profunda apenas nos módulos especializados;
- IA como apoio, não como fonte primária de decisão.

Isso preserva o que já funciona, evita duplicação de métricas e prepara o sistema para fazendas agrícolas, pecuárias e mistas sem comprometer a UX.
