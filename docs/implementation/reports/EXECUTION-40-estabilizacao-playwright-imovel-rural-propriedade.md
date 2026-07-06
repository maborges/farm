# EXECUTION-40 - Estabilização Playwright do fluxo Imóvel Rural ↔ Propriedade

## Causa raiz do E2E

A falha do teste novo tinha duas causas reais:

1. o helper de mock de API de `apps/web/tests/e2e/helpers/authenticated-context.ts` bloqueava toda requisição `POST` antes do handler específico do spec, devolvendo `405` e impedindo a captura do payload de criação;
2. o formulário de Imóveis Rurais não tinha binding acessível suficiente para o campo `Município`, e os `Select` do Radix exigiam scoping correto para o portal de opções no Playwright.

Também foi necessário ajustar o mock de autenticação para o padrão de permissões do app, mantendo o usuário não-superuser com `custom_permissions` explícitas para exibir o botão `Novo Imóvel`.

## Arquivos alterados

Frontend / E2E:

- `apps/web/tests/e2e/helpers/authenticated-context.ts`
- `apps/web/tests/e2e/cadastros-imoveis.spec.ts`
- `apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx`

Documentação:

- `docs/implementation/reports/EXECUTION-40-estabilizacao-playwright-imovel-rural-propriedade.md`

## Ajustes em mocks

- o helper de autenticação passou a permitir que o handler específico do teste receba requisições não-GET/HEAD, inclusive `POST`;
- o mock do spec de imóveis passou a usar `custom_permissions` para `tenant:imoveis:create`, sem depender de `is_superuser`;
- o mock continua cobrindo `auth/me`, `auth/my-tenants`, `unidades-produtivas` e `onboarding/status`.

## Ajustes em UI

- adicionado `htmlFor`/`id` para o campo `Município`;
- adicionados `htmlFor`/`id` para `NIRF`, `CAR` e `CCIR`, melhorando a acessibilidade do formulário;
- os selects permaneceram com o padrão existente, mas o teste passou a interagir com o portal de opções de forma explícita.

## Regra implementada no CREATE

Nenhuma regra de backend foi alterada nesta execução.

O fluxo validado no frontend foi:

- abrir o formulário de novo imóvel;
- preencher `Nome`, `Município`, `UF`, `Área Total`;
- selecionar a Propriedade existente no campo opcional de vínculo;
- enviar o payload oficial sem `tenant_id`;
- usar `numero_matricula` como campo oficial.

## Regra implementada no UPDATE

Nenhuma regra de backend foi alterada nesta execução.

## Comportamento frontend

- o botão `Novo Imóvel` ficou exposto com o mock de permissões correto;
- o formulário de criação passou a ser acessível de forma estável no Playwright;
- o teste novo valida seleção de Propriedade existente e o envio do payload oficial;
- a navegação para `visao-fundiaria` foi mantida no spec existente.

## Testes executados

- `pnpm exec tsc --noEmit`
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts -g "cria imóvel vinculando" --project=chromium`
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts --project=chromium`
- `git diff --check`

## Resultado dos testes

- `pnpm exec tsc --noEmit`: passou
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts -g "cria imóvel vinculando" --project=chromium`: passou
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts --project=chromium`: `4 passed`
- `git diff --check`: passou

## Resultado TypeScript

Sem erros.

## Houve alteração de backend?

Não.

## Riscos encontrados

- o spec de imóveis depende de mocks de autenticação e de API bem alinhados com o bootstrap real do app;
- os `Select` do formulário usam portal, então o teste precisa continuar apontando para o `listbox` correto;
- qualquer mudança futura no `PermissionGuard` ou no `OnboardingGuard` pode quebrar a exposição do botão `Novo Imóvel`.

## Pendências reais

Não há pendência funcional aberta nesta execução.

## Compatibilidade preservada

- o backend não foi alterado;
- nenhum contrato foi quebrado;
- a cobertura existente foi mantida;
- o fluxo de listagem e o fluxo inverso Imóvel Rural ↔ Propriedade continuam validados.
