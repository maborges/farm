# EXECUTION-11 - Fase 9: validação autenticada e hardening da visão territorial/fundiária

## Objetivo

Validar as telas somente leitura de:

- `/cadastros/propriedades/[id]/visao-territorial`
- `/cadastros/imoveis/[id]/visao-fundiaria`

com sessão autenticada controlada, cobrindo loading, erro e estados vazios, sem abrir escrita agregada.

## Estratégia de autenticação usada

Foi usada uma sessão mockada controlada no Playwright:

- `token` JWT sintético em cookie e `localStorage`
- `agrosaas-auth-storage` preenchido no `addInitScript`
- mocks explícitos para:
  - `GET /api/v1/auth/me`
  - `GET /api/v1/auth/my-tenants`
  - `GET /api/v1/unidades-produtivas`
  - `GET /api/v1/onboarding/status`
  - endpoints de visão territorial/fundiária

Isso evitou o redirecionamento para login no ambiente local sem remover guards reais.

## Ajustes feitos

### Frontend

- Corrigido o contrato das páginas dinâmicas para `params: Promise<{ id: string }>` e `await params`:
  - `/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/visao-territorial/page.tsx`
  - `/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/[id]/visao-fundiaria/page.tsx`
- Corrigido import ausente de `Badge` em:
  - `/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/pipeline/page.tsx`

### E2E

- Reescrito e fortalecido:
  - `/opt/lampp/htdocs/farm/apps/web/tests/e2e/territorial-visao.spec.ts`
- Coberturas incluídas:
  - loading
  - erro
  - estado vazio
  - sem vínculos
  - sem documentos disponíveis
  - ausência de controles de escrita
  - ausência de chamadas `POST/PATCH/DELETE` nas rotas da tela

## Testes executados

- `git status --short`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `pnpm exec tsc --noEmit`
- `git diff --check -- 'src/app/(dashboard)/cadastros/propriedades/[id]/visao-territorial/page.tsx' 'src/app/(dashboard)/cadastros/imoveis/[id]/visao-fundiaria/page.tsx' 'src/app/(dashboard)/dashboard/backoffice/pipeline/page.tsx' 'tests/e2e/territorial-visao.spec.ts'`

## Resultado dos testes

- Playwright: aprovado, `6 passed`
- TypeScript: aprovado, sem erros
- Whitespace check: aprovado

## Erro legado de TypeScript

- O erro legado apontado na fase anterior em `src/app/(dashboard)/dashboard/ia/performance/page.tsx` não foi reproduzido nesta execução.
- Não foi necessário alterar esse arquivo.
- O bloqueio real de typecheck nesta rodada veio de:
  - tipos gerados para as novas páginas territoriais
  - import ausente de `Badge` no pipeline

## Riscos e pendências reais

- A validação autenticada ainda é mockada no Playwright, não uma sessão real contra backend real.
- Os seletores do E2E dependem de textos da UI; mudanças de copy podem exigir ajuste fino.
- O worktree continua com outras mudanças não relacionadas da aplicação e do backend fora do escopo desta fase.

## Recomendação para a próxima fase

- Levar a mesma estratégia de sessão controlada para outras rotas críticas que dependem de `auth/me` + contexto de tenant/fazenda.
- Se houver regressão, preferir primeiro um fixture centralizado de auth para reduzir duplicação nos specs.
- Antes de ampliar escopo, estabilizar o worktree e separar os demais diffs grandes desta linha de entrega.
