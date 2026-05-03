# AgroSaaS - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focada em produtividade, isolamento de dados (Multi-tenancy) e interface de alta performance.

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
- **Alertas em Runtime**: Geração automática de alertas financeiros baseados em 3 regras de negócio — sem persistência em banco, calculados a cada requisição.
- **Regra CUSTO_REGISTRADO** (info): Dispara quando `custo_total > 0` na safra, informando quantos lançamentos existem.
- **Regra MARGEM_NEGATIVA** (danger): Dispara quando a margem do cenário base é negativa, exibindo o valor absoluto para revisão imediata.
- **Regra AUMENTO_CUSTO** (warning): Compara os dois últimos períodos da série temporal — alerta quando a variação supera 20%.
- **Fluxo**: `GET /api/v1/financeiro/lancamentos/alertas?safra_id=` → `LancamentoService.gerar_alertas()` → componente `AlertasCard` no dashboard. O card se auto-atualiza a cada 60 segundos e é invalidado após qualquer lançamento de custo.

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
- **Análise e Auditoria**: Interface dedicada em `/suprimentos/compras/solicitacoes` para que o setor de compras analise, aprove ou cancele solicitações, com histórico de status e enriquecimento de dados (nome do item, depósito, quantidade).
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
