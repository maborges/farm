# AGROSAAS/FARMOS - AI BOOTSTRAP GUIDE

Este documento serve como o **Guia Definitivo de Contexto** para inicialização e compreensão de qualquer inteligência artificial (agentes, copilots ou LLMs locais) atuando neste repositório. O objetivo é reduzir a repetição de análise, evitando regressões ou violações das regras do sistema.

## 1. ORDEM DE LEITURA (DOCUMENTOS OBRIGATÓRIOS PARA A IA)

Antes de propor qualquer modificação técnica relevante, a IA DEVE ler e processar os seguintes documentos na seguinte ordem:

1. **`docs/architecture/architecture-inventory.md`**
   - *Por quê?* Fornece um mapa detalhado da stack tecnológica (Python 3.12, FastAPI, Next.js 16, Postgres RLS, Dexie.js offline) evitando que a IA crie bibliotecas ou padrões concorrentes e compreenda as premissas estritas do Monorepo.

2. **`docs/architecture/agrosaas-domain-map.md`** (Se existente) ou Mapeamento de Domínios do Inventário.
   - *Por quê?* Define o vocabulário de negócio e a interligação de módulos (Agrícola, Pecuária, Financeiro, CRM, PWA de Campo).

3. **Arquivos de Regras de Prompt/Sistema (`03-frontend-web.md` e `04-workflow-quality.md`)**
   - *Por quê?* São as regras imutáveis da engenharia local (ex: Server Components por padrão, TDD obrigatório, design premium, banimento de `any` e supressões TypeScript, isolamento de bancos RLS).

4. **`docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md`** *(Apenas se atuar na pasta apps/campo)*
   - *Por quê?* A arquitetura Offline First com Dexie.js, Service Workers e TanStack requer cuidados profundos. Modificações aleatórias quebram a sincronização da fazenda.

5. **`docs/API_REFERENCE_RBAC.md`** *(Apenas se atuar no Backend)*
   - *Por quê?* As permissões e injeções de Tenant via Middlewares (RLS) são críticas e geram exceções `TenantViolationError` em caso de código descuidado.

---

## 2. REGRAS ARQUITETURAIS IMUTÁVEIS PARA A IA

Para trabalhar neste projeto, você (IA) está **terminantemente proibida** de ignorar as seguintes regras:

- **PROIBIÇÃO DE `ANY`:** Todo TypeScript produzido deve ser fortemente tipado e validado. É proibido o uso de `@ts-ignore` ou `as any`.
- **RSC COMO PADRÃO:** Em `apps/web/src/app` e `apps/campo/src/app`, todo componente `page.tsx` é Server Component. Diretiva `"use client"` só é permitida nas folhas da árvore (componentes que usam hooks ou interatividade de clique).
- **SEM ORMS FALSOS NO FRONTEND:** Todo dado vindo do Frontend deve usar `TanStack Query v5` para Server State, e Zustand apenas para Client State leve. Formulários devem sempre usar React Hook Form associado a validações Zod provenientes do `packages/zod-schemas`.
- **PADRÃO SHADCN/TAILWIND 4:** Na criação de interfaces gráficas, priorize sempre bibliotecas padronizadas da stack como `@base-ui` e `shadcn/ui` customizados localmente. Botões devem adotar padronagens menores (`size sm`) e cantos `rounded-sm`. O sistema exige extrema estética (zero Layout Shifts, uso de Skeletons).
- **ROW LEVEL SECURITY (RLS) DO POSTGRES:** No FastAPI (Backend), **não modifique middlewares de acesso**, e não faça queries globais bypassando o `tenant_id`. Todo SQL ou SQLAlchemy rodará restrito ao RLS inserido na conexão.
- **TDD (Red/Green/Refactor):** Ao implementar lógicas de negócios, é imperativo que testes falhos sejam providenciados (ou levados em conta via pensamento lógico) antes da solução do negócio (cobrindo arrays vazios, nulos, e dependências entre APIs).
- **VERBOSIDADE FUNCIONAL:** Funções atômicas e com responsabilidade única. No backend, use `docstrings` documentando *Args*, *Return* e *Raises*.

---

## 3. CONTEXTO MÍNIMO NECESSÁRIO

- **Monorepo**: Você está no repositório `AgroSaaS / FarmOS`, um ecossistema modular para fazendas.
- As aplicações principais são duas pontas separadas: O `apps/web` (Backoffice na sede) e o `apps/campo` (PWA que funciona offline nos tratores e áreas sem sinal).
- O motor principal é único e atende todas as pontas (O *Modular Monolith* em `services/api` escrito em Python).
- O backend baseia-se em Eventos/Background Tasks e Middlewares fortes de isolamento para operar em Nuvem (AWS). Não execute operações longas na thread da requisição, escale para Celery Workers.

> Ao iniciar uma nova thread de contexto, **releia este arquivo** e declare tacitamente a assimilação dos frameworks citados para alinhar seu gerador de código.
