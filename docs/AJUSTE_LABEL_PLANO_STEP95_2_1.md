# Step 95.2.1 — Ajuste Final de Label Comercial do Plano

## Objetivo

Refinar a nomenclatura comercial da UI substituindo `A1 Planejamento` por `Planejamento`, mantendo intacta toda a estrutura tecnica de tiers, modulos e billing.

## Escopo aplicado

Arquivos ajustados:

- `apps/web/src/lib/constants/planos.ts`
- `apps/web/src/lib/constants/pacotes.ts`
- `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx`
- `apps/web/src/components/shared/module-gate.tsx`
- `apps/web/src/app/page.tsx`

Ajuste complementar para eliminar residuo visivel de UI:

- `apps/web/src/components/backoffice/plan-modal.tsx`

## O que mudou

Padrao comercial final na UI:

- `Planejamento`
- `Profissional`
- `Enterprise`

Substituicoes aplicadas:

- `A1 Planejamento` -> `Planejamento`

## O que permaneceu intacto

Nao houve alteracao em:

- `plan_tier`
- `modulos_inclusos`
- `require_tier`
- `useHasTier`
- identificadores tecnicos como `A1_PLANEJAMENTO` e `BASICO`
- backend
- banco
- migrations

## Resultado funcional

O comportamento do sistema permaneceu o mesmo.

O ajuste foi estritamente visual/comercial:

- tiers tecnicos continuam iguais
- gates continuam iguais
- lookup de modulos e permissões continua igual
- billing continua usando a mesma estrutura tecnica

## Validacoes executadas

### 1. Lint

Comando executado:

- `pnpm exec eslint src/lib/constants/planos.ts src/lib/constants/pacotes.ts 'src/app/(dashboard)/dashboard/settings/billing/page.tsx' src/components/shared/module-gate.tsx src/app/page.tsx`

Resultado:

- sem erros

### 2. Busca global por `A1 Planejamento`

Comando executado:

- `rg -n 'A1 Planejamento' apps/web/src`

Resultado:

- sem ocorrencias restantes

### 3. Integridade do diff

Comando executado:

- `git -C apps/web diff --check`

Resultado:

- sem problemas

## Conclusao

O ajuste final foi concluido com sucesso.

A UI ativa passa a exibir apenas:

- `Planejamento`
- `Profissional`
- `Enterprise`

Sem impacto funcional e sem qualquer alteracao na camada tecnica do produto.
