# INVENTÁRIO ARQUITETURAL - AGROSAAS/FARMOS

## 1. ESTRUTURA GERAL

- **Monorepo**: Sim (pnpm workspaces)
- **Estrutura de diretórios**:
```text
apps/
  campo/        # Frontend PWA offline
  web/          # Frontend Administrativo Web
docs/           # Documentação técnica e de negócio
  architecture/ # Decisões arquiteturais
packages/       # Bibliotecas compartilhadas (TS)
  types/
  utils/
  zod-schemas/
services/       # Serviços Backend
  api/          # Monolito principal Python/FastAPI
```
*Fonte da evidência*: `pnpm-workspace.yaml` e navegação na raiz do repositório.

---

## 2. BACKEND

- **Linguagem**: Python 3.12
- **Framework principal**: FastAPI 0.115.0 com Uvicorn
- **ORM**: SQLAlchemy 2.0.30 (Async mode)
- **Biblioteca de migrações**: Alembic 1.13.1
- **Sistema de autenticação**: JWT (via `python-jose` e `passlib`)
- **Sistema de autorização**: Middlewares globais e checagem de permissões via RBAC e sessão.
- **Banco de dados utilizado**: PostgreSQL 16 via driver `asyncpg`
- **Estratégia multi-tenant**: Isolamento lógico com **Row Level Security (RLS)** em banco de dados (`TenantRLSMiddleware` gerencia a injeção do contexto de tenant_id a cada request).
- **Sistema de cache**: Redis 7
- **Sistema de filas**: Celery + Redis
- **Scheduler**: Celery
- **Upload de arquivos**: Servido via `StaticFiles` localmente. (S3 presumido para nuvem/produção via integracoes cloud AWS).
- **Integrações externas**: Stripe, Asaas, Sankhya, John Deere, Case IH, New Holland, WhatsApp.

*Fonte das evidências*: `services/api/pyproject.toml`, `services/api/main.py`, `docker-compose.yml`.

---

## 3. FRONTEND WEB

- **Framework**: Next.js 16.1.6
- **Linguagem**: TypeScript
- **UI Framework**: TailwindCSS 4
- **Component Library**: shadcn/ui e `@base-ui/react`, `@radix-ui`
- **Gerenciamento de estado**: Zustand (estado local/UI)
- **Data Fetching**: TanStack React Query v5.90
- **Sistema de autenticação**: Gerenciamento próprio via cookies/stores (`app-store.ts`) + API Backend JWT.
- **Sistema de rotas**: App Router (evidência na estrutura `src/app/`).
- **Estrutura de componentes**: Baseada em slots e layouts pré-moldados (evidência `src/components/auth/`).

*Fonte das evidências*: `apps/web/package.json`, `docs/architecture/frontend-rsc-pattern.md`.

---

## 4. FRONTEND CAMPO / PWA

- **Framework**: Next.js 16.1.6 + `next-pwa`
- **Tecnologias offline**: IndexedDB
- **Cache local**: Gerenciado pela biblioteca **Dexie.js** e `dexie-react-hooks`.
- **Service Workers**: Sim (fornecido via plugin `next-pwa`).
- **Estratégia de sincronização**: Customizada. Rotas dedicadas como `/api/v1/sync` no backend e worker forms local.
- **Geolocalização / Captura de fotos**: NÃO IDENTIFICADO em dependências (Aparentemente utiliza APIs HTML5 nativas).
- **Modo offline**: Aplicação Offline-First real (Offline Capability).

*Fonte das evidências*: `apps/campo/package.json`, routers no `services/api/main.py`, `docs/CAMPO_PWA_01_ARQUITETURA_OFFLINE.md`.

---

## 5. BANCO DE DADOS

- **SGBD**: PostgreSQL 16 (Imagem docker `postgres:16-alpine`)
- **Schemas existentes**: NÃO IDENTIFICADO (Provável uso do esquema `public` predominante com RLS, sem uso estrito de schemas Postgres apartados, ou criação dinâmica não evidenciada diretamente).
- **Schema principal**: NÃO IDENTIFICADO
- **Estratégia multi-tenant**: Múltiplos inquilinos no mesmo banco isolados por políticas RLS na camada de banco e garantidos via Middleware no FastAPI.
- **Principais tabelas**: SessaoAtiva, Tenants, Produtos, Atividades, Propriedades, EstoqueMovimentos (deduzido das models citadas nos routers e middlewares).
- **Principais relacionamentos**: NÃO IDENTIFICADO estruturalmente.

*Fonte das evidências*: `docker-compose.yml`, `services/api/main.py`.

---

## 6. INFRAESTRUTURA

- **Docker**: Sim.
- **Docker Compose**: Sim. Orquestração local do BD e Cache.
- **Kubernetes / Vercel / Railway**: NÃO IDENTIFICADO explicitamente no código-fonte em raiz.
- **AWS**: Sim (Suportado para deploy principal).
- **CI/CD / Github Actions**: Oculto/Inexistente localmente.
- **Ambiente de Desenvolvimento**: Local com `docker-compose up` para `db` e `redis`, FastAPI via Uvicorn e `next dev` em monorepo local.
- **Ambiente de Homologação/Produção**: Deploy em nuvem (AWS primária), exigindo banco separado estritamente.

*Fonte das evidências*: `docker-compose.yml`, `docs/AWS_DEPLOYMENT_CHECKLIST.md`.

---

## 7. SEGURANÇA

- **JWT**: Sim, com validade e assinaturas (python-jose).
- **OAuth**: NÃO IDENTIFICADO nativamente (Possivelmente custom ou não ativo).
- **Session**: Tabela de sessão em banco atrelada a Heartbeat e expiração. Middleware monitora inatividade e renova cache de token.
- **RBAC**: Sim, implementação madura na estrutura Core.
- **Permissões**: Hierárquicas e checadas ativamente no tenant atual.
- **Auditoria**: Rotinas de audit tracking nos backoffices e tracking assíncrono para anomalias de acesso a Tenants cruzados (`TenantViolationError` reporta incidente direto na tabela de auditoria via task agendada).
- **Logs**: Sistema centralizado via **Loguru**, serializado em JSON nativamente para agregar com Grafana/Loki/CloudWatch.

*Fonte das evidências*: Tratamento de Erros e Middlewares globais em `services/api/main.py`.

---

## 8. DOMÍNIO DE NEGÓCIO

Módulos Identificados:

- **Backoffice / Core SaaS**: Status: Implementado (Fonte: routers `backoffice.*`, `billing`, `plan_changes`)
- **Agrícola**: Status: Implementado (Fonte: `agricola.safras`, `agricola.talhoes`, `agricola.dashboard`)
- **Amostragem de Solo / Agricultura Precisão**: Status: Implementado (Fonte: `agricola.amostragem_solo`, `agricola.ndvi_avancado`)
- **Ambiental**: Status: Implementado (Fonte: `ambiental.router`)
- **CRM**: Status: Implementado (Fonte: `backoffice_crm`)
- **Compras**: Status: Implementado (Fonte: `operacional.routers.compras`)
- **Estoque**: Status: Implementado (Fonte: `operacional.routers.estoque`)
- **Financeiro**: Status: Implementado (Fonte: routers `despesas`, `receitas`, `conciliacao`, `notas_fiscais`)
- **Comercialização / Hedge**: Status: Implementado (Fonte: `financeiro.comercializacao`, `financeiro.hedge`)
- **Frota / Oficina**: Status: Implementado (Fonte: `operacional.routers.frota`, `oficina`)
- **Pecuária**: Status: Implementado (Fonte: `pecuaria.routers.lotes`, `pecuaria.routers.manejos`)
- **IA Diagnóstico**: Status: Implementado (Fonte: `ia_diagnostico.routers`)
- **RH**: Status: Implementado (Fonte: `rh.router`)

---

## 9. DOCUMENTAÇÃO ARQUITETURAL

Documentos Encontrados em `docs/` e `docs/architecture/`:

| Nome | Objetivo | Importância | Deve ser lido por IA? |
|---|---|---|---|
| `AgroSaaS-Dev-Rules.docx` | Regras de engenharia do time. | Alta | Sim (se em markdown) |
| `docs/architecture/frontend-rsc-pattern.md` e `docs/architecture/agrosaas-engineering-playbook.md` | Guidelines estritos de front, TDD e arquitetura. | Crítica | Sim |
| `ADMIN_SAAS_ESTRUTURA.md` | Estrutura central do módulo backoffice. | Alta | Sim |
| `CAMPO_PWA_01_ARQUITETURA_OFFLINE.md` | Detalhes sobre a arquitetura do IndexedDB e sincronização. | Alta | Sim |
| `UI_DESIGN_SYSTEM.md` | Parâmetros de UI / Componentes. | Alta | Sim |
| `API_REFERENCE_RBAC.md` | Como perfis/funções funcionam no backend. | Alta | Sim |
| `AWS_DEPLOYMENT_CHECKLIST.md` | Regras de infra para produção. | Média | Não (exceto tarefas de devops) |
| `docs/architecture/frontend-rsc-pattern.md` | Regras sobre Server e Client components no Next.js | Alta | Sim |
| `docs/architecture/agrosaas-domain-map.md` | Mapeamento dos contextos delimitados (DDD) do sistema | Alta | Sim |

---

## 10. REGRAS ARQUITETURAIS

Regras extraídas a partir dos manifestos de arquitetura e contexto global:

1. **Server Components por padrão**: Todo componente `page.tsx` no Next.js deve ser RSC e acessar dados via API Server/Server Actions, delegando o cliente apenas quando interativo (`use client`).
2. **Estética Premium**: Requisito de UX severo (uso de shadcn, grids customizados AG Grid não oficiais ou robustos similares, cores refinadas, Skeletons nativos, e tolerância zero com layout shift).
3. **TDD e Testes**: Obrigatório o uso do Red/Green/Refactor. As lógicas de negócios não sobem sem cobertura com edge cases cobertos.
4. **Ausência do tipo Any**: Uso estrito no TypeScript (`any` é banido, assim como supressões indevidas do compiler).
5. **Atomicidade de Commits**: Cada commit resolve exclusivamente um escopo utilizando semântica `feat()`, `fix()`, `refactor()`.
6. **Zero Side-effects Ocultos e Demeter**: Serviços com 20 linhas no máximo e até 3 argumentos. Cadeias extensas de classes não permitidas.
7. **Isolamento de Banco via RLS**: Sempre extrair o tenant e propagar pelas transações usando o middleware nativo, proibido bypass global exceto no Backoffice root.
8. **Ambientes Segregados**: Bancos dev, staging e prod NUNCA se comunicam. Scripts validam `APP_ENV`.

---

## 11. STACK OFICIAL

**Backend:**
- Python 3.12
- FastAPI 0.115.0 (ASGI via Uvicorn)
- SQLAlchemy 2.0.30 + Alembic 1.13.1
- Loguru (Logging em JSON)
- Celery (Background Workers / Schedulers)
- python-jose (JWT) + Passlib (Bcrypt)

**Frontend Web:**
- Next.js 16.1.6 (App Router / RSC)
- React 19
- TailwindCSS 4
- Shadcn UI / Base UI / Radix UI
- Zustand (Client State) + TanStack Query v5 (Server State / Cache Local)
- React Hook Form + Zod (Schemas compartilhados)

**Frontend Campo (PWA):**
- Next.js 16.1.6 + next-pwa
- React 19
- TailwindCSS 4
- Dexie.js (IndexedDB)
- Zustand + TanStack Query v5

**Banco de Dados:**
- PostgreSQL 16 (driver assíncrono asyncpg) com Row Level Security
- Redis 7 (Cache e Fila do Celery)

**Infra:**
- AWS (EC2/RDS/S3)
- Docker + Docker Compose (Ambiente Local)
