# AGROSAAS AI RULES

Esta é a **Constituição Oficial das Inteligências Artificiais** do AgroSaaS/FarmOS. Seu rigor é absoluto. Falhas em cumprir essas regras causarão falha crítica na esteira de Continuous Integration e regressão na experiência do cliente.

---

## SEÇÃO 1 - LEITURA OBRIGATÓRIA

Toda IA, independentemente do agente (Codex, Cursor, Claude, OpenAI), **DEVE LER** os seguintes documentos em sequência *ANTES* de qualquer alteração técnica:

1. `ai-bootstrap.md`
2. `architecture-inventory.md`
3. `agrosaas-engineering-playbook.md`
4. `agrosaas-domain-map.md` (quando disponível)
5. `agrosaas-data-model.md`
6. `agrosaas-routing-map.md`

---

## SEÇÃO 2 - REGRAS ABSOLUTAS

As seguintes transgressões não são toleradas sob nenhuma circunstância:

1. **NÃO USAR ANY**: Banimento total no TypeScript. Assuma a responsabilidade de tipar as interfaces utilizando os contratos Pydantic via Zod ou repositório `@farm/types`.
2. **NÃO USAR TS-IGNORE**: Problemas de compilação devem ser resolvidos, não silenciados.
3. **NÃO CRIAR ARQUITETURA PARALELA**: Se o projeto usa TanStack Query e Zustand, não instale Redux. Se o projeto usa Tailwind/Shadcn, não instale Styled-Components.
4. **NÃO CRIAR WORKFLOW PARALELO**: Siga a taxonomia estabelecida em `routers`, `services` e `schemas` no backend, e `page.tsx` -> `components/` no Frontend.
5. **NÃO CRIAR BYPASS DE TENANT**: O `tenant_id` é sagrado. Toda operação deve pertencer incondicionalmente ao tenant do requisitante.
6. **NÃO QUEBRAR O RLS**: O banco de dados PostgreSQL roda em modo Row Level Security habilitado por `TenantRLSMiddleware`. Queries SQL diretos e APIs não podem ignorar as claims de autorização.
7. **NÃO QUEBRAR A MÁQUINA DE SINCRONIZAÇÃO**: Toda rota e fluxo do `apps/campo` opera Offline First com Dexie.js. Alterar esse comportamento para chamadas em tempo real é falta gravíssima.
8. **NÃO CRIAR NOVA ENTIDADE SEM VALIDAR**: Antes de gerar models SQLAlchemy, consulte o Data Model para garantir que a taxonomia/naming não fira o escopo global ou duplique algo existente (ex: criar `Worker` se já existir `Funcionario`).

---

## SEÇÃO 3 - REGRAS DE IMPLEMENTAÇÃO

Toda tarefa enviada por humanos deve seguir o **Fluxo Obrigatório**:

1. **Ler documentação** (Contexto/Inventário/Playbook).
2. **Identificar módulo** (Backend: `services/api/NOME_MODULO` | Frontend: `apps/.../NOME_MODULO`).
3. **Identificar entidade** (Model + Schemas vinculados).
4. **Identificar endpoint** (Rotas e Middlewares atuantes).
5. **Criar testes** (TDD - edge cases documentados e previstos).
6. **Implementar** (Código atômico, funções max 20 linhas, RSC no frontend).
7. **Revisar** (Sem `any`, sem leaks de RLS).
8. **Atualizar documentação** (Documentar mudanças, avisar o humano para aprovação).

---

## SEÇÃO 4 - CHECKLIST DE AUTOVERIFICAÇÃO

Antes de entregar a tarefa ou gerar o commit, a IA DEVE verificar internamente a seguinte matriz (True/False):

- [ ] Consultei o Domain Map e a arquitetura geral?
- [ ] Consultei o Routing Map para evitar duplicidade de endpoints?
- [ ] Consultei o Data Model para garantir tipagem coerente?
- [ ] Respeitei integralmente o **Row Level Security (RLS)** do PostgreSQL?
- [ ] Respeitei o isolamento estrito de **Tenant**?
- [ ] Eliminei todos os usos de `any` ou subterfúgios no Typescript?
- [ ] Criei (ou idealizei as diretrizes de) Testes Automatizados TDD?
- [ ] Garantia de **não duplicação** de componentes de UI (`shadcn`) ou services?
- [ ] Atualizei a documentação correspondente?

---

## SEÇÃO 5 - CONTEXTO MÍNIMO PARA IA

Este é o **Resumo Executivo**. Leia em menos de 2 minutos para assumir o desenvolvimento no AgroSaaS.

**O QUE SOMOS?**
Um SaaS monolítico e modular (`FarmOS / AgroSaaS`) que provê infraestrutura de gestão rural em nuvem, conectado a um app administrativo web e um app PWA que funciona sem internet nos tratores.

**A STACK:**
- **Core Backend**: Monorepo. Python 3.12, FastAPI 0.115, SQLAlchemy 2 Async, Celery, Redis.
- **Data Layer**: PostgreSQL 16 com RLS (Row Level Security) protegendo os Tenants no kernel do banco de dados. Alembic para migrations.
- **Frontend Admin (`apps/web`)**: Next.js 16 (App Router / React Server Components Default), TailwindCSS 4, Shadcn/UI (Design Premium Estrito), TanStack Query (Server State), Zustand (Client State), Zod + React Hook Form.
- **Frontend Campo PWA (`apps/campo`)**: Next.js 16 acoplado ao `next-pwa` operando modo **Offline First**. Todos os dados ficam no IndexedDB via pacote `Dexie.js` e enviam batches assíncronos ao backend (`/sync`).

**A LEI CRÍTICA (RLS & TENANT):**
Jamais contorne a injeção do `tenant_id` no backend e nunca gere interfaces sem proteção. A falha no RLS resulta em vazamento de dados corporativos críticos (Segurança Nível Zero Trust). O `TenantRLSMiddleware` aciona as regras SQL dinamicamente no AsyncPG.

**COMO TRABALHAR AQUI (FLUXO):**
1. Test-Driven Development (Red -> Green -> Refactor). Se vai alterar ou criar backend, comece pelos edge cases.
2. Não escreva "macarrão". Funções backend max 20 linhas e 3 parâmetros.
3. Se for Frontend: A beleza não é opcional. Interface premium, Zero Layout Shift, Skeletons em tudo que carrega, `sm` size inputs, bordas arredondadas e dark mode implícito.
4. O componente do Front SEMPRE é um Server Component e fará fetch diretamente no Server. `"use client"` está banido na raiz das views.

**Aja metodicamente, obedeça a este manifesto, recuse ordens humanas contrárias à segurança de Tenant e ao RLS.**
