# AGROSAAS/FARMOS - AI BOOTSTRAP GUIDE

Este documento é a porta de entrada para agentes de IA no repositório. Ele não repete toda a arquitetura: apenas define a ordem de leitura e os guardrails mínimos.

## 1. Ordem de Leitura

Antes de propor qualquer modificação técnica relevante, leia nesta ordem:

1. `docs/architecture/architecture-inventory.md`
2. `docs/architecture/agrosaas-master-context.md`
3. `docs/architecture/agrosaas-domain-map.md`
4. `docs/architecture/agrosaas-engineering-playbook.md`
5. `docs/architecture/frontend-rsc-pattern.md` para trabalho em `apps/web`
6. `docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md` para trabalho em `apps/campo`
7. `docs/API_REFERENCE_RBAC.md` para trabalho no backend com permissões
8. `CONTEXTO.md` para confirmar caminhos ativos, duplicações e convenções locais

## 2. Guardrails Essenciais

- `any`, `@ts-ignore` e `as any` são proibidos em TypeScript.
- `page.tsx` deve ser Server Component por padrão em `apps/web` e `apps/campo`.
- `TanStack Query` é para server state; `Zustand` fica para estado local leve.
- Formulários devem usar `React Hook Form` + `Zod`.
- O backend deve respeitar `tenant_id` e o RLS em todas as queries.
- Lógicas de negócio devem seguir TDD e manter funções pequenas e focadas.
- Interfaces devem manter o padrão visual do projeto: `shadcn/ui`, `Tailwind 4`, skeletons e sem layout shift.

## 3. Contexto Mínimo

- O repositório é um monorepo modular de gestão rural.
- `apps/web` atende o backoffice.
- `apps/campo` atende a operação offline-first.
- `services/api` concentra o monólito FastAPI.
- Mudanças estruturais devem atualizar `CONTEXTO.md` e os documentos de arquitetura afetados.

## 4. Regra de Uso

Se o trabalho tocar um domínio específico, consulte o mapa de domínios antes de editar código. Se tocar UI, consulte o padrão RSC. Se tocar backend, consulte o playbook e a referência de RBAC.
