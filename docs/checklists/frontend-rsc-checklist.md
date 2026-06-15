# Checklist de Homologação RSC — Frontend AgroSaaS

Este checklist deve ser obrigatoriamente preenchido e anexado ao Pull Request de qualquer nova página ou refatoração para a arquitetura React Server Components (RSC) no AgroSaaS.

---

## 1. Estrutura e Arquivos
- [ ] O arquivo da rota (`page.tsx`) **NÃO** possui a diretiva `"use client"` no topo.
- [ ] A lógica interativa do cliente está isolada em um arquivo `*Client.tsx` no mesmo diretório (ex: `MeuModuloClient.tsx`).
- [ ] O arquivo `*Client.tsx` possui `"use client"` explicitamente declarado na primeira linha.
- [ ] Os nomes de arquivos e componentes seguem o padrão **PascalCase** (ex: `MeuModuloClient.tsx` e `export function MeuModuloClient`).

## 2. Data Fetching no Servidor (`page.tsx`)
- [ ] Todas as chamadas ao backend no servidor utilizam `apiFetchServer` (nunca imports clientes como `apiFetch`).
- [ ] Parâmetros dinâmicos e filtros de URL são obtidos por meio do `searchParams` e `params` assíncronos (ex: `const searchParams = await props.searchParams`).
- [ ] Requisições paralelas são feitas via `Promise.allSettled` (evitando cascatas/waterfalls no servidor).
- [ ] Cada promessa no `Promise.allSettled` é validada individualmente e possui um fallback seguro (ex: array vazio `[]` ou objeto `null`) em caso de falha de conexão ou erro HTTP.
- [ ] Não há vazamento de segredos, cookies manuais do navegador ou variáveis sensíveis de desenvolvimento no código do servidor.

## 3. Prevenção de Falhas (Anti-Crash 500)
- [ ] As consultas do servidor estão envolvidas em blocos `try/catch`.
- [ ] Se o backend retornar `402 Payment Required` (erro de tier), `404 Not Found` ou `500 Internal Error`, a falha é capturada e passada para o cliente de forma amigável (como dado `null` ou flag de erro) em vez de causar um crash de servidor geral (500).

## 4. Hidratação e React Query no Cliente (`Client.tsx`)
- [ ] Os dados pré-carregados pelo servidor são passados como props (`initialData`) e injetados diretamente na propriedade `initialData` do `useQuery`.
- [ ] O `initialData` só é associado à query key caso o estado do filtro atual do cliente (ex: `activeFazendaId` e período ativo) seja exatamente o mesmo parâmetro que o servidor usou para realizar o fetch inicial.
- [ ] As mutations (`useMutation`) estão inteiramente localizadas no Client Component ou em seus diálogos filhos.
- [ ] O `useQueryClient` invalida as queries corretamente após mutations bem-sucedidas.

## 5. Bloqueio por Planos (Tier-Based Loading)
- [ ] Consultas restritas aos planos Professional ou Enterprise têm a propriedade `enabled` condicionada aos resultados do hook `useHasTier()`.
- [ ] Se o usuário não possuir o plano requerido, a query correspondente não é executada no cliente e o componente padrão `TierUpgradeCard` é exibido no lugar do recurso.

## 6. Layout, Design e Componentização
- [ ] Os botões de ação e inputs de formulário seguem os tamanhos pequenos (`sm`) do design system.
- [ ] As bordas dos cartões, tabelas e botões utilizam a propriedade `rounded-sm` (borda pequena padronizada).
- [ ] O layout possui placeholders de carregamento (`loading.tsx` ou `Skeleton` local) para evitar layout shifts bruscos durante a hidratação.

## 7. Qualidade de Código e Tipagem
- [ ] O TypeScript compila sem erros (`tsc --noEmit` executado localmente na pasta `apps/web`).
- [ ] O código passa no linter sem alertas (`eslint` executado localmente na pasta `apps/web`).
- [ ] Não há uso de tipagens genéricas proibidas (`any` ou `@ts-ignore`).
- [ ] Imports estão ordenados respeitando a taxonomia (`react -> bibliotecas -> componentes -> utilitários`).

## 8. Testes E2E (Playwright)
- [ ] Um spec de teste E2E correspondente foi criado na pasta `tests/e2e/`.
- [ ] O teste automatizado simula a sessão de autenticação injetando cookies e o estado do Zustand no `localStorage`.
- [ ] O teste valida o render inicial do dashboard, interações básicas (como filtros de período ou abas), transições de página e estados de fallback em caso de IDs inexistentes (404).
