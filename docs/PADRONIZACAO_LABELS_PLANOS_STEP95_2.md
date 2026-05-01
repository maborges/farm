# Step 95.2 — Padronizacao de Labels Comerciais dos Planos SaaS

## Objetivo

Padronizar a nomenclatura exibida ao usuario para os planos SaaS, removendo inconsistencias entre `A1`, `Básico`, `Premium`, `Empresa` e nomes legados, sem alterar identifiers tecnicos, gates, billing ou backend.

## Regra aplicada

Separacao mantida entre camadas:

- tier tecnico: `BASICO`, `PROFISSIONAL`, `ENTERPRISE`
- modulos tecnicos: `A1_PLANEJAMENTO`, `A2_CAMPO`, `P1_REBANHO` etc.
- nome comercial do plano:
  - `A1 Planejamento`
  - `Profissional`
  - `Enterprise`

## O que foi padronizado

### 1. Nome comercial por tier

Foi explicitada a separacao entre:

- identificador tecnico do tier
- label comercial do plano
- descricao comercial do plano

Resultado:

- `BASICO` continua tecnico, mas passa a ser exibido como `A1 Planejamento`
- `PROFISSIONAL` continua tecnico e comercialmente exibido como `Profissional`
- `ENTERPRISE` continua tecnico e comercialmente exibido como `Enterprise`
- `PREMIUM` continua apenas como alias tecnico legado de leitura e nao aparece mais como nome de plano

### 2. Labels removidos da UI

Deixaram de ser exibidos como plano:

- `Básico`
- `Premium`
- `Essencial`
- `Bronze`
- `Prata`
- `Ouro`
- `Empresarial`
- `Empresa` como nome de plano

## Arquivos ajustados

Arquivos principais do escopo solicitado:

- `apps/web/src/lib/constants/planos.ts`
- `apps/web/src/lib/constants/pacotes.ts`
- `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx`
- `apps/web/src/components/shared/module-gate.tsx`
- `apps/web/src/app/page.tsx`

Ajustes complementares de UI para limpar termos legados visiveis durante a validacao:

- `apps/web/src/components/backoffice/plan-modal.tsx`
- `apps/web/src/app/(dashboard)/agricola/ajuda/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/profiles/page.tsx`
- `apps/web/src/lib/constants/modulos.ts`
- `apps/web/src/app/(dashboard)/dashboard/agricola/ndvi/page.tsx`

## Ajustes realizados

### `apps/web/src/lib/constants/planos.ts`

- adicionado mapa comercial canônico por tier
- `PlanTierMetadata.BASICO.label` alterado para `A1 Planejamento`
- criada funcao helper para recuperar nome comercial do plano sem tocar no tier tecnico

### `apps/web/src/lib/constants/pacotes.ts`

- pacote `BASICO` passou a ter nome comercial `A1 Planejamento`
- pacote `EMPRESA` passou a ter nome comercial `Enterprise`
- descricoes e comentarios comerciais foram alinhados para nao propagar `Básico` ou `Empresa` como plano

### `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx`

- textos hero/comparativo atualizados para `A1 Planejamento`, `Profissional`, `Enterprise`
- cards de planos passaram a renderizar nome comercial pelo tier, e nao o `plan.nome` bruto da API
- historico de faturamento passou a normalizar nomes legados vindos do backend para exibicao comercial consistente
- descricoes dos cards passaram a usar copy comercial unificada

### `apps/web/src/components/shared/module-gate.tsx`

- texto de upsell ajustado para citar os tres planos comerciais canônicos

### `apps/web/src/app/page.tsx`

- landing atualizada para exibir:
  - `A1 Planejamento`
  - `Profissional`
  - `Enterprise`
- removido uso visual de `A1` isolado como nome de plano
- removido uso de `premium` no contexto do plano/topo comercial

## Regras preservadas

Nenhuma regra de negocio foi alterada.

Permaneceu intacto:

- `require_tier`
- `useHasTier`
- `useHasModule`
- `modulos_inclusos`
- `plan_tier`
- backend
- banco
- migrations
- feature gates

## Validacoes executadas

### 1. Lint dos arquivos alterados

Comando executado:

- `pnpm exec eslint ...` no workspace `apps/web`

Resultado:

- sem erros
- 1 warning preexistente em `src/components/backoffice/plan-modal.tsx` relacionado a `react-hooks/incompatible-library` por uso de `watch()` do React Hook Form

Observacao:

- o warning nao foi introduzido por esta etapa e nao altera comportamento

### 2. Busca global por termos proibidos na UI ativa

Busca executada:

- `rg -n 'Básico|Premium|Essencial|Empresarial' apps/web/src`

Resultado final:

- apenas 1 ocorrencia residual em `apps/web/src/components/ui/DATA_TABLE_README.md`

Conclusao:

- nenhuma ocorrencia restante nas telas ativas ajustadas nesta etapa
- o residual esta em arquivo de documentacao interna de componente, fora da UI ativa

### 3. Integridade do diff

Comando executado:

- `git -C apps/web diff --check`

Resultado:

- sem problemas de whitespace ou formato de patch

## Resultado final para o usuario

Na UI padronizada, o usuario passa a ver apenas:

- `A1 Planejamento`
- `Profissional`
- `Enterprise`

## Conclusao

O Step 95.2 padronizou os labels comerciais dos planos sem tocar nos contratos tecnicos do sistema. A arquitetura de monetizacao continua baseada em `plan_tier` e `modulos_inclusos`, enquanto a camada visual/comercial agora apresenta naming consistente e alinhado com os Steps 94, 95 e 95.1.
