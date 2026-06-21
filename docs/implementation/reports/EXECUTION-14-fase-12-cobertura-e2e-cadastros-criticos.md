# EXECUTION-14 - Fase 12 - Cobertura E2E para Cadastros Críticos

## Objetivo

Expandir a cobertura E2E autenticada para os fluxos de `Cadastros` com maior impacto funcional:

- Propriedades
- Imóveis Rurais
- Visões agregadas relacionadas
- Navegação cruzada entre listagem, detalhe e visão consolidada

## Inventário de specs

Specs inventariadas em `apps/web/tests/e2e` com foco na fase:

- `tests/e2e/territorial-visao.spec.ts`
- `tests/e2e/agricola-dre-v1.spec.ts`
- `tests/e2e/agricola-rentabilidade-v1.spec.ts`
- `tests/e2e/agricola-safra-financeiro.spec.ts`
- `tests/e2e/estoque-implantacao-assistida.spec.ts`
- `tests/e2e/crm-kanban-cache.spec.ts`
- `tests/e2e/frota-rsc-migration.spec.ts`
- `tests/e2e/cadastros-propriedades.spec.ts`
- `tests/e2e/cadastros-imoveis.spec.ts`

## Specs migrados

Nesta fase, as specs críticas adicionadas para cobertura autenticada foram:

- `tests/e2e/cadastros-propriedades.spec.ts`
- `tests/e2e/cadastros-imoveis.spec.ts`

O spec territorial foi reexecutado como não regressão:

- `tests/e2e/territorial-visao.spec.ts`

## Fluxos cobertos

### Propriedades

- listagem
- filtro por busca
- estado vazio da listagem
- paginação
- abertura de detalhe
- acesso à visão territorial
- navegação territorial para visão fundiária via imóvel vinculado
- estado de erro da listagem

### Imóveis Rurais

- listagem
- filtro por situação
- estado vazio da listagem
- acesso à visão fundiária
- estados vazios de documentos e vínculos
- estado de erro da visão fundiária

### Visões agregadas

- territorial com loading, erro, vazio e leitura somente leitura
- fundiária com estados vazios e erro

## Arquivos criados

- `docs/implementation/reports/EXECUTION-14-fase-12-cobertura-e2e-cadastros-criticos.md`
- `tests/e2e/cadastros-propriedades.spec.ts`
- `tests/e2e/cadastros-imoveis.spec.ts`

## Arquivos alterados

- `tests/e2e/helpers/authenticated-context.ts`
- `tests/e2e/cadastros-propriedades.spec.ts`
- `tests/e2e/cadastros-imoveis.spec.ts`

## Testes executados

- `pnpm exec playwright test tests/e2e/cadastros-propriedades.spec.ts tests/e2e/cadastros-imoveis.spec.ts --project=chromium`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `pnpm exec tsc --noEmit`
- `git diff --check -- tests/e2e/helpers/authenticated-context.ts tests/e2e/cadastros-propriedades.spec.ts tests/e2e/cadastros-imoveis.spec.ts tests/e2e/territorial-visao.spec.ts`

## Resultado dos testes

- Playwright nos specs de cadastros: `5 passed`
- Playwright no territorial: `6 passed`
- `git diff --check`: sem problemas

## Resultado do TypeScript

- `pnpm exec tsc --noEmit`: sem erros

## Estratégia aplicada

- Reutilizei `setupAuthenticatedContext` e `mockAuthenticatedApi` do helper compartilhado.
- Os payloads de Propriedade, Imóvel Rural e visões agregadas ficaram no próprio spec.
- Para alguns pontos do DOM com texto duplicado, usei `first()` e escopo de tabela/bloco para evitar flaky selectors.

## Riscos encontrados

- Os `Select` do design system continuam sensíveis em Playwright; precisei ajustar o teste para o nome acessível real do trigger.
- Alguns textos aparecem duplicados na visão agregada, exigindo seleção mais estrita no teste.
- A navegação de detalhe foi validada por `goto` direto em vez de clique de linha, porque o link da tabela não é o ponto mais estável para essa cobertura.

## Pendências reais

- Expandir a mesma abordagem para outras rotas críticas de `cadastros` e módulos adjacentes.
- Se a equipe quiser validar o clique de linha como interação de UX, vale criar seletores dedicados nos componentes de tabela.

## Recomendação para a próxima fase

- Priorizar o mesmo padrão para `estoque`, `frota` e outros fluxos de cadastro com alto risco de regressão.
- Quando houver duplicidade de texto no DOM, padronizar `data-testid` nos blocos críticos antes de aumentar a cobertura.
