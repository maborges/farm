# EXECUTION-27 - FASE 25 HARDENING UX, ACESSIBILIDADE E ESTABILIDADE E2E DO MVP CERTIFICAÇÕES/ESG

Data: 2026-06-21

## Objetivo

Endurecer a UX, a acessibilidade e a estabilidade dos testes E2E do MVP de Certificações/ESG, sem mudar regras de negócio nem ampliar escopo funcional.

## Melhorias realizadas

- Formulários com alvos estáveis de teste por `data-testid`.
- Loading do cliente marcado com `data-testid` no skeleton real.
- Checkbox da evidência tornado clicável sem `force: true` no Playwright.
- Feedback de sucesso/erro isolado por formulário com `role="status"` e `data-testid`.
- E2E migrado para seletores mais estáveis e menos dependentes de texto duplicado.

## Arquivos criados

- `docs/implementation/reports/EXECUTION-27-fase-25-hardening-ux-e2e-certificacoes-esg.md`

## Arquivos alterados

- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/CertificacoesEsgClient.tsx`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/loading.tsx`
- `apps/web/src/components/ui/checkbox.tsx`
- `apps/web/tests/e2e/certificacoes-esg.spec.ts`

## Melhorias de UX

- Estados de carregamento mais previsíveis.
- Feedback visual e textual consistente nos formulários.
- Estrutura mais clara para a interação dos formulários.

## Melhorias de acessibilidade

- Feedback dos formulários em `role="status"`.
- Labels mantendo associação com campos controlados.
- Checkbox com wrapper clicável estável, sem interação forçada no E2E.
- Botões com nomes acessíveis já existentes e preservados.

## Ajustes E2E

- Remoção do `force: true` no checkbox.
- Uso de `data-testid` para:
  - loading
  - cards dos formulários
  - feedback de criação/erro
- Redução de dependência de `nth()` e textos duplicados.

## Testes executados

- `pnpm exec tsc --noEmit`
- `pnpm exec playwright test tests/e2e/certificacoes-esg.spec.ts --project=chromium`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `git diff --check`

## Resultado dos testes

- TypeScript: aprovado.
- `certificacoes-esg.spec.ts`: 6 passed.
- `territorial-visao.spec.ts`: 6 passed.
- `git diff --check`: sem problemas.

## Riscos encontrados

- O loading ainda depende do ciclo de renderização do React Query, mas agora possui alvos estáveis e observáveis.
- O worktree segue com alterações pré-existentes fora do escopo.

## Pendências reais

- Não foram adicionadas novas features de negócio.
- Não houve alteração de backend ou contratos da API.

## Recomendação para a próxima fase

- Seguir apenas para endurecimento incremental ou expansão funcional claramente justificada, preservando a separação entre o domínio de certificação e a base territorial/fundiária canônica.
