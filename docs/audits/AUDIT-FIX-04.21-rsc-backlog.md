# Backlog de Migração e Consolidação RSC — AgroSaaS

Este documento consolida o inventário de migrações efetuadas para Server Components (RSC) no AgroSaaS, aponta as divergências identificadas e organiza o backlog remanescente para as próximas sprints.

---

## 1. Inventário de Páginas Migradas

Até o momento, **34 páginas** foram refatoradas com sucesso para o modelo de RSC Shell + Client Component separado:

| Categoria | Rota (Caminho Relativo) | Client Component Associado | Status |
| :--- | :--- | :--- | :--- |
| **Classe A** | `/integracoes/dominio` | `DominioClient.tsx` | Concluído |
| **Classe A** | `/dashboard/settings/sessoes` | `SessoesClient.tsx` | Concluído |
| **Classe A** | `/dashboard/ambiental/monitoramento/alertas` | `AlertasClient.tsx` | Concluído |
| **Classe A** | `/dashboard/ambiental/outorgas` | `OutorgasClient.tsx` | Concluído |
| **Classe A** | `/dashboard/ambiental/car/lista` | `ListaCarClient.tsx` | Concluído |
| **Classe A** | `/dashboard/rh/esocial` | `EsocialClient.tsx` | Concluído |
| **Classe A** | `/dashboard/rh/departamentos` | `DepartamentosClient.tsx` | Concluído |
| **Classe A** | `/backoffice/tabelas/tipos-operacao` | `TiposOperacaoClient.tsx` | Concluído |
| **Classe A** | `/backoffice/tabelas/commodities` | `CommoditiesClient.tsx` | Concluído |
| **Classe A** | `/backoffice/tabelas/culturas` | `CulturasClient.tsx` | Concluído |
| **Classe A** | `/dashboard/agricola/custos` | `CustosClient.tsx` | Concluído |
| **Classe B** | `/cadastros/pessoas` | `PessoasClient.tsx` | Concluído |
| **Classe B** | `/cadastros/produtos` | `ProdutosClient.tsx` | Concluído |
| **Classe B** | `/cadastros/imoveis` | `ImoveisClient.tsx` | Concluído |
| **Classe B** | `/(auth)/forgot-password` | `ForgotPasswordClient.tsx` | Concluído |
| **Classe B** | `/dashboard/operacional/manutencoes` | `ManutencoesClient.tsx` | Concluído |
| **Classe B** | `/dashboard/operacional/fornecedores` | `FornecedoresClient.tsx` | Concluído |
| **Classe B** | `/dashboard/settings/smtp` | `SmtpClient.tsx` | Concluído |
| **Classe B** | `/dashboard/settings/team` | `TeamClient.tsx` | Concluído |
| **Classe B** | `/dashboard/settings/seguranca` | `SegurancaClient.tsx` | Concluído |
| **Classe B** | `/dashboard/settings/roles` | `RolesClient.tsx` | Concluído |
| **Classe B** | `/dashboard/rh/ponto` | `PontoClient.tsx` | Concluído |
| **Classe B** | `/dashboard/rh/colaboradores` | `ColaboradoresClient.tsx` | Concluído |
| **Classe B** | `/dashboard/rh/folha-pagamento` | `FolhaPagamentoClient.tsx` | Concluído |
| **Classe B** | `/dashboard/financeiro/contas-pagar` | `ContasPagarClient.tsx` | Concluído |
| **Classe B** | `/dashboard/financeiro/contas-bancarias` | `ContasBancariasClient.tsx` | Concluído |
| **Classe B** | `/dashboard/pecuaria/piquetes` | `PiquetesClient.tsx` | Concluído |
| **Classe B** | `/dashboard/agricola/beneficiamento` | `BeneficiamentoClient.tsx` | Concluído |
| **Classe B** | `/dashboard/agricola/apontamentos` | `ApontamentosClient.tsx` | Concluído |
| **Classe B** | `/suprimentos/compras` | `PedidosClient.tsx` | Concluído |
| **Classe B** | `/suprimentos/compras/solicitacoes` | `SolicitacoesClient.tsx` | Concluído |
| **Estoque** | `/suprimentos/estoque` | `EstoqueClient.tsx` | Concluído |
| **Frota** | `/dashboard/operacional/frota` | `FrotaClient.tsx` | Concluído |
| **Frota** | `/dashboard/operacional/frota/[equipamentoId]` | `EquipamentoDetalheClient.tsx` | Concluído |

---

## 2. Divergências Identificadas no Código Migrado

Durante a auditoria arquitetural, foram encontradas as seguintes inconsistências entre as páginas que já haviam passado pela refatoração:

1. **Inconsistência de Tratamento de Erros no Servidor (Anti-Crash 500)**:
   - *Divergência*: Páginas como `cadastros/pessoas/page.tsx` envolvem chamadas de API do servidor em blocos `try/catch` seguros, garantindo que em caso de queda de banco ou erro 500, a página inicialize um estado vazio (`[]` ou `null`) no cliente.
   - *Risco*: Páginas como `backoffice/tabelas/tipos-operacao/page.tsx` e `dashboard/backoffice/tenants/page.tsx` chamavam `apiFetchServer` de forma síncrona sem tratamento de erros. Se o endpoint `/operacoes/tipos` cair, o Next.js dispara uma página geral 500 para o produtor.
2. **Uso Indevido de `Promise.all` em vez de `Promise.allSettled`**:
   - *Divergência*: Em `/backoffice/assinantes/page.tsx`, o carregamento paralelo usou `Promise.all` direto para as três chamadas ao backend.
   - *Risco*: Se o endpoint `/backoffice/tenants/stats` falhar, toda a requisição de assinantes é derrubada, mesmo que os dados cadastrais principais de tenants e plans estejam disponíveis.
3. **Nomenclaturas de Arquivos e Componentes Clientes**:
   - *Divergência*: A grande maioria dos arquivos clientes usa PascalCase (`MeuModuloClient.tsx`) e exportação nomeada. Porém, foram identificados alguns arquivos kebab-case como `assinantes-client.tsx`, `tenants-client.tsx`, `ia-settings-client.tsx`, `tenant-settings-client.tsx` e `propriedades-client.tsx` utilizando `export default`.

---

## 3. Backlog de Próximas Migrações (165+ páginas restantes)

Para as próximas fases, as páginas restantes da aplicação foram classificadas segundo complexidade, riscos e interatividade:

### A. Pronto para Migrar (Ganhos Rápidos - Baixa Complexidade)
*Telas com listagem de dados simples e ações de leitura:*
1. `/dashboard/pecuaria/rebanho` (Tabela de listagem de animais e rebanhos com filtro de lote)
2. `/dashboard/financeiro/receitas` (Tabela de receitas financeiras, sem mutações em massa)
3. `/suprimentos/compras/solicitacoes/[id]` (Página de detalhe de uma solicitação de compras)
4. `/dashboard/operacional/campo/dispositivos` (Tabela de inventário de sensores IoT e coletores)
5. `/dashboard/rh/esocial/tabelas` (Listagem estática de baselines e eventos de conformidade)

### B. Exige Discovery (Alta Complexidade ou Alta Concorrência)
*Telas pesadas, gráficos dinâmicos ou múltiplas APIs acopladas:*
1. `/dashboard/financeiro/dre` (Consolidação de DRE com fórmulas matemáticas complexas, necessitando `Promise.allSettled` com 7 queries)
2. `/dashboard/ia/performance` (2129 linhas, dashboard analítico complexo com Recharts)
3. `/dashboard/backoffice/crm` (CRM interno com drag-and-drop de kanban e manipulação de leads)
4. `/agricola/safras/[id]/operacoes` (Lista densa de operações com 9 queries paralelas em cascata)
5. `/agricola/safras/[id]/cenarios` (Estudo de cenários e simulações complexas de insumos com forms multipasso)

### C. Não Migrar (Manter Totalmente Client-Side / Redesign Necessário)
*Páginas com forte dependência de APIs do navegador, mapas WebGL ou editores visuais:*
1. `/cadastros/propriedades/talhoes` (Editor interativo de polígonos de talhões integrado com Mapbox)
2. `/agricola/planejamento` (Quadro Gantt de planejamento agrícola com manipulação de drag-and-drop intensa no DOM)
3. `/cadastros/propriedades/[id]` (Desenho espacial e cálculo geométrico de áreas rurais)
4. `/agricola/safras/[id]/dashboard` (Workspace de mapas operacionais com telemetria de trator em tempo real)
5. `/dashboard/agricola/relatorios` (Pivot-table dinâmica de relatórios processada localmente em JS)

---

## 4. Classificação Estratégica de Candidatos

### Top 5 Ganhos Rápidos (Quick Wins)
1. **`/dashboard/operacional/jornadas`**: Histórico simples de jornadas e apontamentos da frota (leitura massiva, ótima para RSC).
2. **`/dashboard/operacional/frota/manutencao-preventiva`**: Checklist de prazos e planos preventivos em formato tabular.
3. **`/dashboard/operacional/frota/consumo`**: Dashboard simples de consumo médio e eficiência da frota.
4. **`/dashboard/operacional/frota/custos`**: Distribuição acumulada de custos operacionais das máquinas.
5. **`/dashboard/operacional/frota/disponibilidade`**: Lista de liberação e checklist dos motoristas.

### Top 5 Maiores Riscos (High Risk)
1. **`/dashboard/financeiro/dre`**: Erro de cálculo ou falha na hydração do DRE impacta diretamente a diretoria da fazenda.
2. **`/dashboard/ia/performance`**: Tamanho do arquivo (>2000 linhas) exige refatoração visual profunda antes de aplicar RSC.
3. **`/dashboard/backoffice/crm`**: Eventos intensos de drag-and-drop podem quebrar se a hydração React Query falhar.
4. **`/agricola/safras/[id]/cenarios`**: Simulador financeiro altamente dependente de estado local volátil.
5. **`/agricola/safras/[id]/operacoes`**: Quantidade excessiva de queries simultâneas (9) exige cuidado para evitar timeouts no servidor.

### Top 5 Páginas que Nunca Deveriam ser RSC
1. **`/cadastros/propriedades/talhoes`** (Mapbox / Desenho de coordenadas)
2. **`/agricola/planejamento`** (Quadro Gantt interativo de safras)
3. **`/cadastros/propriedades/[id]`** (Mapa de demarcação de fazendas)
4. **`/agricola/safras/[id]/dashboard`** (Telemetria ao vivo de telemetria)
5. **`/dashboard/agricola/relatorios`** (Dynamic Pivot Table)
