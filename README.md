# AgroSaaS - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focada em produtividade, isolamento de dados (Multi-tenancy) e interface de alta performance.

## Leitura Inicial Obrigatória

Antes de iniciar análise, implementação ou manutenção neste repositório, leia também `CONTEXTO.md`.

O arquivo `CONTEXTO.md` concentra o mapa operacional do projeto, incluindo:

- estrutura real do monorepo
- pontos de entrada de frontend e backend
- convenções ativas
- alertas sobre diretórios duplicados ou espelhados

Sempre que houver mudança relevante de arquitetura, stack, convenções ou organização de diretórios, atualize `CONTEXTO.md` junto com a mudança.

## 🏗️ Arquitetura do Sistema

O projeto é dividido em um monorepo contendo:
- **apps/web**: Interface Next.js 16 com shadcn/ui e Zustand.
- **services/api**: Backend Python com FastAPI, SQLAlchemy e banco de dados PostgreSQL.
- **packages/zod-schemas**: Definições de contratos compartilhados (Shared Schemas).

## 🚀 Funcionalidades (Features)

### 1. Sistema de Identidade e Multi-Tenancy (Fase 1 e 2)
- **Isolamento Absoluto**: Cada produtor (Tenant) possui seus dados cercados por segurança de nível de serviço.
- **Vincular Contextos**: Um único usuário pode ter acesso a múltiplas empresas rurais (Holdings) e transitar entre elas sem deslogar.
- **Perfis de Acesso**: Controle granular por papéis (Proprietário, Agrônomo, Gerente, Operador).

### 2. Onboarding e Expansão de Equipe (Fase 3)
- **Auto-Cadastro de Produtores**: Fluxo simplificado que cria Identidade + Tenant + Fazenda + Assinatura em uma única operação.
- **Sistema de Convites**: Donos de fazendas podem convidar técnicos e funcionários via e-mail.
- **Segurança de Convites**: Tokens expiráveis e vínculos automáticos de propriedade ao aceitar o acesso.

### 3. Gestão Agrícola e Pecuária (Módulos Base)
- **Meus Talhões**: Visualização geográfica de áreas produtivas com gestão de solo e irrigação.
- **Análise de Solo Inteligente**: Motor de diagnóstico que converte laudos laboratoriais em recomendações de calagem e adubação, incluindo **estimativa automática de custos**.
- **Automação de Tarefas**: Geração automática de ordens de serviço (SafraTarefa) baseada em prescrições técnicas com cálculo de investimento total.
- **Financeiro Rural**: DRE, Contas a Pagar/Receber com foco em custeio de safra.

### 4. Templates Agrícolas e Governança (Fase Atual)
- **Módulo de Templates**: Centralização de PhaseTemplates (Governança) e OperationTemplates (Operacional).
- **Instanciação Rápida**: Aplicação de checklists e tarefas padronizadas por cultura e fase da safra com um clique.
- **Regras de Gate**: Configuração de pré-requisitos para avanço de fase, garantindo compliance e padronização operacional entre diferentes propriedades.

### 5. Sistema de Alertas Inteligentes (Step 101)
- **UX Telemetry (IA)**: Sistema de rastreamento de eventos para medir a eficiência da tomada de decisão. Compara o Modo Essencial vs Modo Avançado em termos de tempo de resposta e taxa de conversão final, fornecendo insights automáticos para otimização da interface.
- **Alertas em Runtime**: Geração automática de alertas financeiros baseados em 3 regras de negócio — sem persistência em banco, calculados a cada requisição.
- **Regra CUSTO_REGISTRADO** (info): Dispara quando `custo_total > 0` na safra, informando quantos lançamentos existem.
- **Regra MARGEM_NEGATIVA** (danger): Dispara quando a margem do cenário base é negativa, exibindo o valor absoluto para revisão imediata.
- **Regra AUMENTO_CUSTO** (warning): Compara os dois últimos períodos da série temporal — alerta quando a variação supera 20%.

### 6. Sistema de Recomendações (Step 102)
- **Recomendações Acionáveis**: Geração automática de orientações determinísticas para o usuário agir sobre os problemas identificados pelos alertas.
- **Regra REVISAR_CUSTOS**: Acionada quando margem < 0 — orienta o usuário a revisar custos e leva diretamente à tela de cenários da safra.
- **Regra ANALISAR_INSUMOS**: Acionada quando INSUMOS é a categoria de maior custo — orienta análise da estrutura de custos.
- **Regra VER_EVOLUCAO**: Acionada quando aumento > 20% no último período — leva o usuário à tela de operações por fase.
- **Fluxo**: `GET /api/v1/financeiro/lancamentos/recomendacoes?safra_id=` → `LancamentoService.gerar_recomendacoes()` → componente `RecomendacoesCard` no dashboard, abaixo do `AlertasCard`. Cada recomendação inclui botão com link direto para a tela de ação.

### 7. Agendamento Manual das Automações (Step 111)
- **Agendamento de Regras**: Permite definir uma frequência de execução (`DIARIA`, `SEMANAL`, `MENSAL` ou `MANUAL`) para cada regra de automação da safra.
- **Cálculo da Próxima Execução**: O backend calcula e armazena automaticamente a `proxima_execucao` com base na frequência selecionada. Frequência `MANUAL` não possui próxima execução predefinida.
- **Fluxo Funcional**: `PATCH /api/v1/automacoes/configuracoes/{regra}` recebe `frequencia` e atualiza a configuração no banco de dados. O frontend exibe um seletor e a próxima data/hora programada no componente `AutomacoesConfigCard`.

### 8. Gestão de Suprimentos e Compras (Step 147 e 148)
- **Reposição Automática**: Alertas de estoque crítico geram sugestões de reposição baseadas em estoque mínimo configurável por depósito.
- **Solicitações de Compra**: Permite converter alertas de reposição em solicitações formais (`ABERTA`) com um clique, rastreando a origem (`REPOSICAO_ESTOQUE`).
- **Análise e Auditoria Premium**: Interface dedicada em `/suprimentos/compras/solicitacoes` que utiliza a tabela padronizada `DataTable` com pesquisa textual e filtros avançados, suporte a exportação em PDF e Excel, e uma gaveta lateral interativa (`Sheet`) que mostra os detalhes da solicitação de compras de forma condensada, eliminando layout shifts.
- **Nova Solicitação Manual**: Suporte a criação manual de solicitações de compras via caixa de diálogo (`Dialog`) onde o usuário seleciona o produto (com autopreenchimento de unidade), depósito e quantidade.
- **Rota e Fluxo Padronizados (RSC)**: Página de pedidos de compra unificada em `/suprimentos/compras` funcionando como um Server-Side Component (RSC), eliminando duplicações antigas em `/suprimentos/compras/pedidos` (que agora redireciona com Next.js `redirect()`), com breadcrumbs perfeitamente alinhados.
- **Fluxo**: `POST /api/v1/compras/solicitacoes` (criação) → `PATCH /api/v1/compras/solicitacoes/{id}/status` (gestão) → Integração com fluxo de suprimentos.

### 9. Inteligência em Compras e Cotações (Steps 153, 154 e 155)
- **Histórico de Preços (Step 153)**: Consolidação automática de preços praticados em cotações e pedidos de compra para cada item.
- **Alertas de Preço (Step 154)**: Sistema de alerta visual que identifica cotações com valor 15% acima da média histórica, prevenindo compras superfaturadas.
- **Sugestão de Melhor Fornecedor (Step 155)**: Algoritmo determinístico que calcula um "Score de Melhor Compra" (Preço 50%, Frequência 30%, Recência 20%) para recomendar o fornecedor ideal.
- **Visualização de Tendência (Step 156)**: Gráfico interativo (Recharts) que exibe a evolução histórica dos preços do item, com identificação visual de alta (vermelho) ou queda (verde).
- **Sugestão de Preço Ideal (Step 157)**: Define uma faixa de referência (Mínimo, Ideal e Máximo Recomendado) baseada no histórico interno, com feedback em tempo real no formulário (ex: alerta de valor excessivo ou selo de "Boa Cotação").
- **Fluxo Funcional**: Ao registrar uma cotação (`CotacaoSolicitacaoDialog`), o sistema busca a melhor recomendação via `GET /api/v1/compras/precos/melhor-fornecedor`, exibe o gráfico de tendência e a faixa de preço ideal. O comprador recebe feedback visual imediato ao digitar o valor unitário.

### 10. Dashboard de Economia - Savings (Step 163)
- **Cálculo de Ganhos**: O sistema calcula automaticamente a economia gerada ao aprovar uma cotação, comparando o preço escolhido com o pior preço disponível (Savings de Negociação).
- **Métricas Financeiras**: Os pedidos de compra armazenam de forma imutável a `economia_absoluta` e a `economia_percentual`.
- **Painel de Analytics**: Interface executiva que consolida a economia total acumulada, média percentual por compra e destaca a "Melhor Decisão" (item com maior economia gerada).
- **Fluxo Funcional**: `GET /api/v1/compras/analytics/economia` retorna os KPIs que alimentam o `EconomiaAnalyticsCard` no topo da lista de solicitações, fornecendo visibilidade imediata do ROI do sistema de compras.

### 11. Financeiro Operacional por Safra (Step 181)
- **Análise Consolidada**: Módulo para registrar e consultar lançamentos financeiros (Custos e Receitas) integrados ao ciclo produtivo (Safra).
- **Filtros Avançados**: Permite filtrar o histórico por Safra, Tipo (Custo/Receita), Categoria e Período, garantindo visibilidade granular do investimento operacional.
- **Resumo Executivo**: Backend calcula em tempo real o saldo (margem) e volume de lançamentos para o contexto selecionado, alimentando KPIs de performance.
- **Fluxo Funcional**: `GET /api/v1/financeiro/lancamentos` (listagem) e `GET /api/v1/financeiro/lancamentos/resumo` (KPIs) → Página dedicada em `/dashboard/financeiro/lancamentos`.

### 12. Módulo Frota (Gestão de Maquinários)
- **Gestão de Equipamentos**: Cadastro completo com horímetro/odômetro e planos de manutenção.
- **Controle de Manutenção**: Ordens de serviço, manutenções preventivas e corretivas com histórico de custos.
- **Gestão de Combustível**: Registro de abastecimentos com integração a estoques e controle de consumo (L/h ou km/L).
- **Integração Agrícola (FROTA-33)**: Atribuição automática de custos de máquinas a safras, talhões e operações através de jornadas integradas.
- **Inteligência Financeira (FROTA-34)**: Identificação proativa de talhões e operações com custos acima da média e detecção de ineficiência de equipamentos ("Onde você está perdendo dinheiro").
- **Ações Diretas (FROTA-35)**: Execução assistida ("Magic Actions") que permite abrir ordens de serviço ou analisar jornadas a partir de um insight com um único clique.
- **Regras Inteligentes (FROTA-36)**: Motor de automação configurável para geração automática de OS, alertas de desvios financeiros e auditoria completa de ações do sistema.
- **Confiança e Transparência (FROTA-37)**: Explicabilidade das ações do sistema, notificações em tempo real e modo assistido por padrão para uma adoção segura da automação.
- **Validação de Adoção (FROTA-38)**: Telemetria de uso real das automações, medindo taxas de aceitação, conversão para modo automático e KPIs de confiança do gestor.
- **Otimização de Conversão (FROTA-39)**: Cálculo de ROI (Economia Estimada) por ação, justificativas baseadas em impacto financeiro e sugestões proativas para automação total.
- **Benchmarks e Desempenho (FROTA-40)**: Comparação histórica de custos, ranking de eficiência por talhão e relatórios de impacto da automação na fazenda.
- **Checklists e Disponibilidade**: Inspeções pré-operacionais e status de disponibilidade em tempo real.
- **Consolidação de Custos Operacionais Reais (Step 03)**: Consolidação econômica confiável por equipamento, safra, unidade produtiva e operação/talhão. Utiliza rateio dinâmico baseado em jornadas concluídas, alocações ativas e fallbacks inteligentes. Fornece indicadores econômicos reais como custo por hora/km, disponibilidade operacional (%) e tempo parado para manutenção, com visualização unificada no dashboard da frota e endpoints de custos integrados.


### 13. Receitas Operacionais Manuais (Step 182)
- **Registro de Entradas**: Permite o registro manual de receitas vinculadas à safra, como venda de produção ou outras receitas operacionais.
- **Validação Estrita**: Garantia de categorias válidas para o tipo RECEITA (`VENDA_PRODUCAO`, `OUTRAS_RECEITAS`) e valores positivos.
- **Step 183 (DRE Operacional):** Implementação de visão executiva por safra com agregação de receitas, custos, resultado e margem operacional.
- **Step 184 (IA Analisa Resultado):** Integração de inteligência artificial para interpretar o DRE, gerando resumos estratégicos, pontos de atenção e recomendações práticas para o produtor.
- **Impacto Econômico**: As receitas registradas alimentam automaticamente o cálculo de saldo e margem operacional da safra no dashboard.
- **Fluxo Funcional**: Botão "Registrar Receita" na tela de lançamentos abre um dialog para entrada de dados. Ao salvar, o sistema invalida os caches de resumo e listagem para atualização imediata dos KPIs.

### 14. DRE Operacional por Safra (Step 183)
- **Visão Executiva**: Relatório consolidado que apresenta a performance financeira da safra em formato de DRE simplificado (Receita Bruta, Custos Operacionais, Resultado e Margem %).
- **Breakdown por Categoria**: Detalhamento visual da composição de custos e receitas, permitindo identificar onde estão os maiores investimentos e entradas.
- **Isolamento de Gestão**: Foco total em métricas operacionais de campo, sem interferência de provisões contábeis, impostos corporativos ou depreciação.
- **Fluxo Funcional**: Acessível via sidebar em `/dashboard/financeiro/dre`, utiliza um seletor de safra para carregar os dados agregados via `GET /api/v1/financeiro/lancamentos/dre`.

### 14. Simulação de Resultado da Safra (What-if) (Step 185)
- **Cenários Preditivos**: Permite simular o resultado financeiro da safra ajustando percentualmente as receitas (-50% a +100%) e custos (-50% a +50%) via sliders interativos.
- **Análise de Impacto**: Visualização em tempo real da variação do resultado e margem simulada em comparação com os dados reais da safra.
- **IA de Apoio à Decisão**: Integração com IA para gerar análises estratégicas sobre o cenário simulado, identificando riscos e recomendando ações preventivas ou de otimização.
- **Fluxo Funcional**: Ativado pelo botão "Simular Cenário" na DRE. O backend processa a projeção via `POST /api/v1/financeiro/dre/simular` e a IA analisa via `POST /api/v1/ia/financeiro/simulacao`.

### 16. IA Recomenda Melhor Cenário (Step 187)
- **Análise Consultiva**: Motor de IA que avalia todos os cenários salvos e recomenda o melhor equilíbrio entre margem e risco.
- **Justificativa Estratégica**: Além da recomendação, a IA fornece justificativas técnicas e identifica pontos de risco para cada escolha.
- **Fluxo Funcional**: `POST /api/v1/ia/financeiro/recomendar-cenario` → Exibição do "Cenário Recomendado" com destaque visual no painel de comparação.

### 17. Tracking e Score de Acerto da IA (Step 188, 189 e 190)
- **Tracking Real vs Planejado (Step 188)**: Permite marcar um cenário como "Escolhido" e comparar automaticamente sua projeção com o resultado real consolidado da safra.
- **Aprendizado por Histórico (Step 189)**: A IA utiliza o histórico de desvios reais de decisões passadas para ajustar e melhorar as recomendações futuras.
- **Score de Confiabilidade (Step 190)**: Cálculo objetivo da taxa de acerto da IA baseado no desvio percentual (Acerto: ≤10%, Parcial: 10-25%, Erro: >25%).
- **Dashboard de Performance**: Interface em `/dashboard/settings/ia` que exibe a taxa de acerto global, distribuição de precisão e status de saúde do sistema de inteligência.
- **Fluxo Funcional**: `GET /api/v1/ia/financeiro/score` → Visualização de KPIs de confiabilidade para transparência e auditoria do usuário.

### 18. Performance e Gamificação do Usuário (Step 191)
- **Dashboard de Impacto**: Card central no painel de controle que quantifica a economia gerada e o sucesso das decisões do usuário.
- **Métricas de Sucesso**: Avalia o desvio entre planejamento e real (Acertos) e as negociações de compra mais vantajosas.
- **Níveis de Progressão**: Sistema de gamificação (Iniciante, Profissional, Experiente, Lendário) baseado no volume de decisões e economia total.
- **Fluxo Funcional**: `GET /api/v1/financeiro/lancamentos/performance-usuario` → Exibição dinâmica de badges, ranking e destaque da melhor decisão no dashboard principal.

### 19. Copiloto Financeiro e IA (Steps 192 - 209)
- **Alertas Proativos**: Identificação automática de riscos (baixa rentabilidade, desvios de plano, ineficiência de custos).
- **IA Adaptativa (Behavioral)**: Ajuste do tom e agressividade das recomendações com base no perfil de risco detectado do usuário (Conservador, Equilibrado, Agressivo).
- **Execução Assistida (Magic Actions)**: Botão "Executar Sugestão" que prepara simulações e ajustes automaticamente, fechando o ciclo de decisão.
- **Step 202: Dashboard de Performance e ROI do Copiloto IA** — Centralização de métricas de economia, taxas de acerto e conversão.
- **Step 203: Recomendação de Upgrade baseada em ROI** — Motor de regras comerciais que sugere upgrades de plano ou créditos baseados no valor gerado pela IA.
- **Step 204: Recomendação de Upgrade no Resumo Diário**: Inclusão de insights de ROI comercial no briefing matinal.
- **Step 205: IA Preditiva de Risco Financeiro**: Antecipação de riscos de margem e tendências de custo com alertas proativos.
- **Step 206: Simulação de Estresse Financeiro**: Motor de simulação de cenários extremos para antecipar riscos de insolvência.
- **Step 207: Plano de Ação Automático**: Geração de estratégias estruturadas de recuperação com ações prioritárias e impacto em R$.
- **Step 208: Plano de Ação Visual**: Componente `IAPlanoAcaoCard` que permite execução individual assistida de cada recomendação.
- **Step 209: Execução Assistida em Lote (Batch Actions)**: Botão "Executar Plano Completo" que agrega todas as recomendações em uma única simulação consolidada no DRE.
- **Step 211: Métricas e ROI do Autopilot**
    - Implementação de dashboard de performance para o Autopilot.
    - Cálculo de impacto financeiro simulado e taxa de aceitação implícita.
    - Exposição de métricas de ROI e confiança do sistema.
- **Step 212: Autopilot Adaptativo (Auto-Tuning)**
    - Criação do `IAAutopilotAdaptiveService` para ajuste dinâmico de autonomia.
    - Análise automática de taxas de reversão e aceitação para calibrar limites.
    - Interface de sugestão nas configurações da IA para expansão ou redução de limites com base em dados reais.

### 20. Growth & A/B Testing (Steps Growth-08 a Growth-10)
- **Growth-08: Experimentos A/B**: Motor de testes para variações de configuração e copy em CTAs de upgrade. Permite distribuir tráfego entre variantes (A, B, C...) e medir conversão (SHOWN -> CLICKED) de forma isolada por tenant.
- **Growth-09: Auto-Experimentos**: O sistema identifica contextos com baixa performance e inicia automaticamente experimentos A/B baseados em sugestões de otimização, permitindo aprendizado contínuo sem intervenção manual.
- **Growth-10: Geração Dinâmica de Copy**: Sistema de otimização de comunicação que gera automaticamente variações de copy (Título, Descrição, Botão) baseadas em abordagens psicológicas (Urgência, Prova Social, Ganho, Perda e Educativo).
- **Growth-11: LLM Growth Copy**: Geração de copy hiper-personalizada via IA (Claude) baseada no perfil comportamental, estágio da safra e histórico do produtor. Inclui motor de cache (12h) para latência zero e fallback robusto para templates heurísticos.
- **Inteligência de Abordagem**: Analytics granular que identifica qual "tom de voz" converte melhor para cada perfil de uso (ex: ROI alto -> abordagem de Ganho; uso excessivo -> abordagem de Urgência).
- **Fluxo Funcional**: `GET /ia/growth/recomendacao-upgrade` retorna o CTA com variantes dinâmicas (LLM ou Heurística) → Acompanhamento de performance por origem (`origem_copy`).

### 21. IA UX — Telemetria e Interface Adaptativa (Série UX)
- **UX-03: Telemetria de Decisão**: Rastreamento granular de eventos (tempo de decisão, modo de visualização, taxa de conversão) para medir a eficácia da IA.
- **UX-04: Feedback Imediato**: Sistema de reforço positivo com toasts premium que quantificam o impacto financeiro e a agilidade da decisão no momento da ação.
- **UX-05: Essencial Dinâmico (Adaptive UI)**: A interface adapta automaticamente sua densidade e nível de detalhe com base no perfil comportamental detectado (Confiante, Analítico ou Inseguro), otimizando a experiência para cada tipo de usuário.
- **UX-06: Auto-Calibração de Thresholds**: O sistema recalibra dinamicamente os limites de classificação de perfil baseando-se em percentis da distribuição real de uso, garantindo que as definições de "Confiante" ou "Analítico" evoluam com a base de usuários.
- **UX-07: Transparência e Explicabilidade**: Implementação de interfaces que explicam "por que" a IA se adaptou. Inclui badge de perfil no card essencial com tooltip educativo e uma nova seção na página de configurações detalhando métricas e thresholds.

### 22. Manutenção Preventiva Inteligente (Step 04)
- **Planos de Manutenção Preventiva**: Criação e atualização de planos preventivos contendo categorias e checklists específicos para as inspeções.
- **Cálculo Dinâmico de Vencimento**: Processamento inteligente de proximidade e vencimento de planos com base em dias corridos, quilometragem acumulada ou horas de horímetro, retornando os status `EM_DIA`, `PROXIMO_VENCIMENTO` ou `VENCIDO`.
- **Geração Assistida de OS Preventiva**: Abertura de ordens de serviço preventivas, importando automaticamente o checklist preventivo padrão para o campo `checklist_aplicado` do maquinário, além de transicionar o status do equipamento para `EM_MANUTENCAO` e impedir ordens de serviço duplicadas para o mesmo plano preventivo em aberto.
- **Encerramento de OS e Apropriação Econômica**: Conclusão de ordens de serviço, restaurando o status da máquina para `ATIVO`, salvando o histórico no `RegistroManutencao` e gerando uma `Despesa` integrada no módulo financeiro vinculada adequadamente à Safra, à Unidade Produtiva (UP) e ao Cultivo de forma rastreável.
- **Indicadores do Dashboard de Frota**: Atualização do painel executivo de frota com a computação consolidada do Tempo Médio Entre Falhas (MTBF) e a distribuição percentual de custos de manutenção preventivos vs corretivos.

## 🐛 Correções de Layout e UX (Bugfixes)

### 1. Padronização do Alinhamento das Páginas de Compras
- **Problema**: As páginas de Solicitações de Compra (`SolicitacoesClient.tsx`) e Pedidos de Compra (`PedidosClient.tsx`) continham um container com largura máxima forçada (`max-w-7xl mx-auto w-full`), gerando um desalinhamento visual e posicionamento fora do padrão (centralizado) em relação às demais páginas do sistema, que seguem o alinhamento responsivo natural do grid principal.
- **Comportamento Esperado**: Utilização da classe de container padrão `p-6 space-y-6` para que as telas herdem o comportamento fluido, responsivo e alinhado do grid da aplicação.

### 2. Erro de Conexão no Servidor (RSC SSR) na Rota de Compras
- **Problema**: As páginas de `/suprimentos/compras/solicitacoes` e `/suprimentos/compras` utilizavam `apiFetch` (apenas cliente) no servidor, disparando um erro de conexão com a API no SSR devido a URLs relativas sem origem.
- **Comportamento Esperado**: Utilização de `apiFetchServer` de `@/lib/api-server` no servidor (RSC) para carregar os dados de forma segura resolvendo o endereço de backend (`BACKEND_URL`).

### 3. Falha ao Listar Produtos Registrados na Criação de Solicitação
- **Problema**: O dialog "Criar Solicitação de Compra" consultava o endpoint inexistente `/estoque/produtos`, fazendo com que a listagem de itens no select de produto ficasse vazia.
- **Comportamento Esperado**: Consulta ao catálogo oficial `/cadastros/produtos?ativo=true&incluir_sistema=true` para carregar e exibir corretamente todos os produtos ativos.

## 🛠️ Como Executar

### Backend
1. Navegue até `services/api`.
2. Ative o venv: `source .venv/bin/activate`.
3. Rode: `uvicorn main:app --reload`.

cd services/api
source .venv/bin/activate
./start_server.sh

uvicorn main:app --reload

### Worker de Automações (scheduler)

No diretório raiz do projeto:
```bash
    source .venv/bin/activate
    python scripts/run_worker.py
```


### Frontend
1. Navegue até `apps/web`.
2. Rode: `pnpm run dev`.

cd apps/web
pnpm run dev


### Matar processo do servidor
pkill -f "uvicorn main:app" && sleep 2 && echo "✅ Processo uvicorn parado" (Parar processo uvicorn travado)

# AGRO-03: Frontend Web (Next.js 16 & UI)

**CONTEXTO:** Interface premium, performance RSC e estado sincronizado para gestão rural.

### 1. SERVER VS CLIENT COMPONENTS
- **RSC Default**: Todo componente é Server Component por padrão.
- **"use client"**: Restrito a: Interatividade (forms, click), Client Browser APIs, TanStack Query hooks.
- **Page Rules**: `page.tsx` DEVE ser RSC — busca dados no servidor e passa para Client Components via props.

### 2. ESTADO E CACHE
- **Server State**: Use TanStack Query (v5) para cache, revalidação automática e optimistic updates.
- **Client State**: Use Zustand para estados leves (tenant ativo, módulo aberto).
- **Formulários**: React Hook Form + Zod (schemas compartilhados com backend no `packages/zod-schemas`).

### 3. UX & PERFORMANCE
- **Skeletons**: Use `loading.tsx` para Suspense nativo em telas pesadas (Dashboard Agricola).
- **Data Grids**: AG Grid para planilhas com 10k+ linhas (Rebanho/Financeiro).
- **Zero Layout Shift**: Definir alturas fixas ou placeholders de imagem (`generate_image`).

### 4. DESIGN SYSTEM (shadcn/ui)
- **Componentes**: 
* Use prioritariamente bibliotecas padronizadas da stack, como `/components/ui/` (shadcn), Componentes Nativos do React. 
* Código customizado SOMENTE se o usuário solicitar explicitamente.
* User toast para apresentar mensagens ao usuário. 
* Botões devem ser outline e size sm
* Utilize ícones que signifiquem a ação nos botões 
* Input devem ter tamanho small
* Todas as sombras com a blasse shadow-xm
* As bordas dos componentes devem ser rounded-xm 
* Usar sidebar para os menus separando os itens por módulo e seus submodulos que devem expandir conforme selecionados  
* Usar sidebar para navegação de menus que pode ser retraidos 
* Procure sempre usar o datatables com pesquisa, ordenação de colunas, exportação para pdf e excel. Quando houver a coluna de ações não colocar header na coluna, botões de ação sem bordas, sem texto, gap-0, cor e ícone pertinente à ação e tooltips curto.

- **Estética Agro**: Use paletas harmoniosas (Verde Esmeralda, Tons Terra) e Dark/Light Mode premiun e o usuário pode mudar.

### 5. TIPAGEM E QUALIDADE ESTRITA (TS)
- **Strict Mode**: Habilitado e rigorosamente cumprido na `tsconfig.json`.
- **Abolição do `any`**: PROIBIDO o uso de tipagem `any` ou subterfúgios como `@ts-ignore` e `as unknown as Type`.
- **Importação Ordenada**: Respeitar a taxonomia: `react -> libs -> components -> utils`.

```tsx
// page.tsx (RSC)
export default async function Page() {
    const data = await getAnimais(); // Busca direta no servidor
    return <AnimaisGrid initialData={data} />;
}
