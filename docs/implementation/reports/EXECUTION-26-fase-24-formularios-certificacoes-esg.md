# EXECUTION-26 - FASE 24 FORMULÁRIOS MÍNIMOS CERTIFICAÇÕES/ESG

Data: 2026-06-21

## Objetivo

Adicionar formulários mínimos para criação de evidências, não conformidades e planos de ação no MVP autenticado de Certificações/ESG, sem aceitar `tenant_id` manual e sem misturar dados territoriais/fundiários no payload.

## Entregue

- Formulários mínimos para:
  - evidência
  - não conformidade
  - plano de ação
- Mutations/hook frontend para criação e invalidação das listas.
- Feedback inline de sucesso e erro.
- Botões com estado de carregamento durante o submit.
- E2E autenticado cobrindo criação, erro e atualização das listas.

## Arquivos criados

- `docs/implementation/reports/EXECUTION-26-fase-24-formularios-certificacoes-esg.md`

## Arquivos alterados

- `apps/web/src/services/certificacoes-esg/service.ts`
- `apps/web/src/lib/hooks/use-certificacoes-esg.ts`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/CertificacoesEsgClient.tsx`
- `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/loading.tsx`
- `apps/web/tests/e2e/certificacoes-esg.spec.ts`

## Hooks/services adicionados

- `criarEvidencia`
- `criarNaoConformidade`
- `criarPlanoAcao`
- `useCriarEvidencia`
- `useCriarNaoConformidade`
- `useCriarPlanoAcao`

## Formulários criados

- Nova evidência
- Nova não conformidade
- Novo plano de ação

## Validações implementadas

- `programa_id` obrigatório nos três formulários.
- Campos textuais obrigatórios com mensagem de erro.
- Enum de tipo de evidência, severidade, status e prioridade.
- `publico` como checkbox controlado.
- `detectada_em` e `prazo` em `datetime-local`.
- Nenhum payload envia `tenant_id`.
- Nenhum payload envia dados de Propriedade, Imóvel Rural ou PropriedadeImovel.

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

- O loading inicial é sensível ao timing de navegação e precisou de asserção ajustada para `skeleton`.
- O checkbox customizado precisou de interação forçada no E2E por conta do empacotamento visual do componente.
- O worktree contém mudanças pré-existentes fora do escopo desta fase.

## Pendências reais

- Não foram criados fluxos avançados de auditoria.
- Não foram criados `RelatorioESG` ou `PassaporteRastreabilidade`.
- Não houve alteração de backend.

## Recomendação para a próxima fase

- Prosseguir com endurecimento de UX dos formulários e, se necessário, expandir o domínio com rotas/fluxos adicionais somente após consolidar uso real das criações mínimas.
