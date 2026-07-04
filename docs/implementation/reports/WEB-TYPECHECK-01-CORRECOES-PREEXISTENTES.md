# WEB-TYPECHECK-01 - Correcoes Preexistentes

## Objetivo
Corrigir erros preexistentes de `typecheck` em `apps/web` sem alterar comportamento funcional.

## Auditoria Inicial

### 1) `src/app/(dashboard)/dashboard/financeiro/hedge/mtm/page.tsx`
- Erro identificado: `TS2719` em `line 50`.
- Causa raiz: contrato de tipo de `SafraOption` divergente entre a `page` e o `MtMClient`.
- Classificacao: **contrato de API / componente / tipo compartilhado**.
- Detalhe: a `page` declarava `SafraOption` sem `ano_safra`, enquanto o client espera `SafraOption` com `ano_safra` e `cultura`.

### 2) `src/app/(dashboard)/dashboard/financeiro/hedge/painel/page.tsx`
- Erro identificado: `TS2719` em `line 44`.
- Causa raiz: mesmo conflito de contrato de `SafraOption` entre `page` e `PainelClient`.
- Classificacao: **contrato de API / componente / tipo compartilhado**.
- Detalhe: o tipo local da `page` não batia com o shape consumido pelo client.

### 3) `src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
- Erro identificado: `TS2345` em `line 158`.
- Causa raiz: o payload da mutacao estava levando `dados_extras`, que possui objeto aninhado e nao cabe no contrato `AnimalSubmitPayload`.
- Classificacao: **dado opcional / contrato de payload**.
- Detalhe: o payload esperado pela mutacao aceita somente valores escalares no index signature atual.

## Correcao Aplicada

- Unifiquei o tipo de safra usado nas pages de hedge com o tipo compartilhado em `contratos/commodity-resolution.ts`.
- Removi `dados_extras` do payload enviado no cadastro/edicao de animais antes de chamar `mutation.mutate`.

## Validacao

- `pnpm --filter web typecheck`
- `pnpm --filter web lint`
- `git diff --check`

## Resultado

- `typecheck`: OK
- `lint`: OK
- `diff --check`: OK
