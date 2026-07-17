# AGROSAAS/FARMS - AI BOOTSTRAP GUIDE

Este documento é a **única fonte oficial de ordem de leitura** para agentes de IA no repositório.
Nenhum outro arquivo (`README.md`, `CONTEXTO.md`, `SKILLS_INDEX.md`, `CLAUDE.md`) deve repetir esta lista —
todos devem apenas linkar para cá.

## 1. Leitura Sempre Obrigatória (curta, resumo executivo)

1. `docs/architecture/agrosaas-master-context.md` — visão geral em <5 min
2. `CONTEXTO.md` — caminhos ativos, duplicações conhecidas, convenções locais

## 2. Leitura Condicional (só se a tarefa tocar o tema)

| Tarefa envolve... | Leia também |
|---|---|
| Regra de negócio / fronteira de domínio | `docs/architecture/agrosaas-domain-map.md` |
| Dúvida de padrão de código (backend/frontend) | `docs/architecture/agrosaas-engineering-playbook.md` |
| Página nova ou refatoração em `apps/web` | `docs/architecture/frontend-rsc-pattern.md` |
| Trabalho em `apps/campo` (PWA offline) | `docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md` |
| Permissões, RBAC, JWT, multi-tenancy | `.claude/skills/CORE_MODULE_EXPERT.md` (fonte única do tema — ver §3) |
| Stack, versões, inventário técnico completo | `docs/architecture/architecture-inventory.md` |
| Módulo de negócio específico (agrícola, pecuária, financeiro, operacional, backoffice) | `SKILLS_INDEX.md` → skill do módulo |

Não leia o que a tarefa não toca. Ler os 7+ documentos sempre, para qualquer tarefa, é o principal ralo de tokens do projeto — evite.

## 3. Guardrails Essenciais (não repita em outro lugar — edite só aqui)

- `any`, `@ts-ignore` e `as any` são proibidos em TypeScript.
- `page.tsx` deve ser Server Component por padrão em `apps/web` e `apps/campo`.
- `TanStack Query` é para server state; `Zustand` fica para estado local leve.
- Formulários devem usar `React Hook Form` + `Zod`.
- O backend deve respeitar `tenant_id` e RLS em todas as queries (nunca bypass, sempre via `BaseService`).
- Lógicas de negócio devem seguir TDD e manter funções pequenas e focadas.
- Interfaces devem manter o padrão visual do projeto: `shadcn/ui`, `Tailwind 4`, skeletons e sem layout shift.

## 4. Contexto Mínimo

- Monorepo modular de gestão rural, multi-tenant.
- `apps/web` atende o backoffice/operação conectada.
- `apps/campo` atende a operação offline-first.
- `services/api` concentra o monólito FastAPI.
- Mudanças estruturais devem atualizar `CONTEXTO.md` e o documento de arquitetura afetado — só esse, não a lista inteira.

## 5. Documentos Históricos (NÃO fazem parte da leitura padrão)

`IMPLEMENTACAO_RBAC_MULTI_SUB.md` e `FRONTEND_MAINTENANCE_GUIDE.md` são registros de execução de fases já concluídas
(contêm checkboxes de progresso e estimativas de horas). Consulte-os apenas se a tarefa for entender uma decisão
passada de RBAC/multi-assinatura — não são referência de arquitetura atual.