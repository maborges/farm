# EXECUTION-12 - Fase 10: padronização de fixture de autenticação E2E

## Objetivo

Centralizar o padrão de autenticação controlada usado nos testes Playwright para permitir reutilização em outras rotas críticas sem duplicação de mocks por spec.

## Estratégia adotada

Foi criado um helper genérico de autenticação E2E que concentra apenas o bootstrap comum:

- injeção de `token`
- configuração de `agrosaas-auth-storage`
- mock de:
  - `GET /api/v1/auth/me`
  - `GET /api/v1/auth/my-tenants`
  - `GET /api/v1/unidades-produtivas`
  - `GET /api/v1/onboarding/status`

Os payloads específicos da visão territorial/fundiária ficaram no spec, como callback separado, sem misturar regra genérica de auth com dados da feature.

## Helper criado

- [apps/web/tests/e2e/helpers/authenticated-context.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/helpers/authenticated-context.ts)

## Spec refatorado

- [apps/web/tests/e2e/territorial-visao.spec.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/territorial-visao.spec.ts)

## O que mudou

- A autenticação comum foi extraída para `mockAuthenticatedApi` e `setupAuthenticatedContext`.
- O spec territorial passou a registrar somente:
  - o callback da feature para visão territorial/fundiária
  - os asserts de loading, erro, vazio, sem vínculos e somente leitura
- O cenário de erro também passou a usar o helper genérico, sem duplicar mocks de auth.

## Validações preservadas

O spec continua cobrindo:

- visão territorial
- visão fundiária
- loading
- erro
- estados vazios
- sem vínculos
- sem documentos disponíveis
- somente leitura
- ausência de chamadas `POST/PATCH/DELETE`

## Testes executados

- `git status --short`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `pnpm exec tsc --noEmit`
- `git diff --check -- 'tests/e2e/helpers/authenticated-context.ts' 'tests/e2e/territorial-visao.spec.ts'`

## Resultado dos testes

- Playwright: `6 passed`
- TypeScript: sem erros
- `git diff --check`: sem problemas

## Riscos encontrados

- O helper cobre o bootstrap autenticado comum, mas ainda depende de payloads específicos por rota para cada feature.
- A suíte continua baseada em mocks E2E, não em sessão real contra backend real.
- Mudanças de copy na UI podem exigir ajuste de seletores.

## Pendências reais

- Não houve alteração de frontend funcional nesta fase.
- Não foi criado um conjunto mais amplo de fixtures compartilhadas além do bootstrap autenticado.

## Recomendação para a próxima fase

1. Reutilizar `mockAuthenticatedApi` em outras suítes E2E críticas.
2. Consolidar os payloads de feature em handlers pequenos por domínio, mantendo auth comum separado.
3. Se houver aumento de cobertura, considerar uma camada adicional de helpers para rotas que usam o mesmo bootstrap e apenas mudam o payload principal.
