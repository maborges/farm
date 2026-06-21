# EXECUTION-25 - FASE 23 FRONTEND MVP CERTIFICAÇÕES/ESG LOTE 2

Data: 2026-06-21

## Objetivo

Entregar um MVP autenticado e somente leitura para o domínio de Certificações/ESG no frontend web, consumindo evidências, não conformidades e planos de ação, com cobertura E2E usando o helper autenticado já existente.

## Estratégia adotada

- Reutilização do helper de autenticação E2E já padronizado em `apps/web/tests/e2e/helpers/authenticated-context.ts`.
- Consumo somente leitura via `apiFetch` para:
  - `GET /api/v1/certificacoes-esg/evidencias`
  - `GET /api/v1/certificacoes-esg/nao-conformidades`
  - `GET /api/v1/certificacoes-esg/planos-acao`
- Atualização de status apenas para não conformidades e planos de ação.
- Mantida a separação entre autenticação genérica e payloads específicos da feature nos testes.

## Arquivos criados

- `apps/web/src/services/certificacoes-esg/service.ts`
- `apps/web/src/lib/hooks/use-certificacoes-esg.ts`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/loading.tsx`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/CertificacoesEsgClient.tsx`
- `apps/web/tests/e2e/certificacoes-esg.spec.ts`

## Arquivos alterados

- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `docs/architecture/agrosaas-routing-map.md`
- `apps/web/tests/e2e/certificacoes-esg.spec.ts`

## Funcionalidades implementadas

- Rota autenticada `/dashboard/certificacoes-esg`.
- Cards de resumo:
  - total de evidências
  - não conformidades abertas
  - planos pendentes/vencidos
  - evidências públicas
- Listagens separadas para:
  - evidências
  - não conformidades
  - planos de ação
- Estados de:
  - loading
  - erro
  - vazio
- Atualização de status de não conformidades e planos de ação.
- Garantia de que a tela não usa `PlanoAcaoItem` legado nem aceita `tenant_id` manual.

## Testes executados

- `pnpm exec tsc --noEmit`
- `pnpm exec playwright test tests/e2e/certificacoes-esg.spec.ts --project=chromium`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `git diff --check -- <arquivos desta fase>`

## Resultado dos testes

- TypeScript: aprovado.
- Playwright `certificacoes-esg.spec.ts`: 4 passed.
- Playwright `territorial-visao.spec.ts`: 6 passed.
- `git diff --check`: sem problemas.

## Resultado TypeScript

- Sem erros.

## Riscos encontrados

- A página depende de mocks autenticados controlados nos testes E2E para validar os fluxos de leitura e atualização de status.
- O estado do worktree contém mudanças pré-existentes fora do escopo desta fase; não foram alteradas.

## Pendências reais

- Não foram criados formulários de criação para o MVP.
- Não foram adicionados fluxos avançados de auditoria ou relatórios.
- Não foi expandida a navegação para outros módulos.

## Recomendação para a próxima fase

Prosseguir para endurecimento do domínio de Certificações/ESG com validação de fluxos adicionais, caso necessário, e consolidar a observabilidade de estado/erro em telas relacionadas.
