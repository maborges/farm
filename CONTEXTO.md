# CONTEXTO.md

## Objetivo

Este arquivo consolida o contexto operacional do AgroSaaS para evitar novo levantamento manual a cada sessão. Ele deve ser lido antes de alterações relevantes no projeto e atualizado sempre que a arquitetura, convenções ou pontos de entrada mudarem.

## Resumo Executivo

- Projeto: AgroSaaS
- Tipo: monorepo
- Domínio: gestão rural multi-tenant
- Frontend principal: `apps/web`
- Backend principal: `services/api`
- Pacotes compartilhados: `packages/*`

## Estrutura Real do Repositório

Na raiz do projeto:

- `apps/web`: aplicação web principal em Next.js 16
- `services/api`: API principal em FastAPI
- `packages/zod-schemas`: contratos compartilhados
- `packages/types`: tipos compartilhados
- `packages/utils`: utilitários compartilhados
- `docs`: documentação e anotações auxiliares
- `tests`: testes no nível do repositório

Workspace PNPM na raiz:

- `pnpm-workspace.yaml` inclui apenas `apps/*` e `packages/*`

## Frontend

Aplicação principal em `apps/web`.

### Stack

- Next.js 16 App Router
- React 19
- TypeScript 5
- TanStack Query v5
- Zustand
- shadcn/ui
- Tailwind CSS 4

### Estrutura ativa

O frontend ativo está sob `apps/web/src`, principalmente:

- `apps/web/src/app`: rotas App Router
- `apps/web/src/components`: componentes por domínio e UI base
- `apps/web/src/hooks`: hooks de acesso a dados e comportamento
- `apps/web/src/lib`: APIs, utilitários, permissões, analytics e config
- `apps/web/src/store`: stores globais

### Pontos de entrada importantes

- `apps/web/src/app/layout.tsx`: layout raiz
- `apps/web/src/app/page.tsx`: página inicial
- `apps/web/src/app/(dashboard)`: área autenticada principal
- `apps/web/src/app/api/v1/[...path]/route.ts`: proxy interno para backend
- `apps/web/src/lib/api.ts`: cliente HTTP do frontend
- `apps/web/src/lib/api-server.ts`: consumo server-side
- `apps/web/src/store/use-auth-store.ts`: estado de autenticação

### Áreas funcionais visíveis

- autenticação e onboarding
- dashboard
- agrícola
- suprimentos
- compras
- financeiro
- configurações
- backoffice
- integrações
- IA e growth

## Backend

Aplicação principal em `services/api`.

### Stack

- FastAPI
- SQLAlchemy 2 async
- Alembic
- PostgreSQL com fallback local em alguns cenários
- Pydantic v2

### Ponto de entrada principal

- `services/api/main.py`

Esse arquivo configura:

- instância FastAPI
- middlewares
- CORS
- arquivos estáticos
- lifespan com jobs em background
- registro de routers

### Organização por domínios

Os módulos principais observados no backend são:

- `core`
- `agricola`
- `operacional`
- `financeiro`
- `pecuaria`
- `imoveis`
- `notificacoes`
- `automacoes`

### Convenções estruturais importantes

- multi-tenancy é requisito central
- `tenant_id` é parte do modelo de isolamento
- há middleware para contexto de tenant e atualização de sessão
- o padrão esperado é usar services em vez de SQL cru em routers
- migrations ficam em `services/api/migrations`

## Convenções de Projeto Relevantes

Com base em `README.md` e `CLAUDE.md`:

- idioma de trabalho: pt-BR
- frontend deve preservar App Router e `page.tsx` como RSC sempre que aplicável
- server state: TanStack Query
- client state leve: Zustand
- formulários: React Hook Form + Zod
- tipagem estrita: evitar `any`
- confirmações de usuário: `AlertDialog`
- usar `Decimal` no backend para valores monetários e quantitativos sensíveis
- respeitar isolamento multi-tenant e RBAC

## Sinais de Atenção

Há indícios de duplicação ou espelhamento indevido dentro de `apps/web`, incluindo caminhos como:

- `apps/web/services/api`
- `apps/web/docs`
- arquivos de banco e artefatos auxiliares dentro de `apps/web`

Esses caminhos não parecem ser a fonte primária da aplicação principal. Antes de editar, confirmar se o arquivo está no caminho ativo do projeto e não em uma cópia espelhada.

## Fluxo Recomendado para Próximas Sessões

Antes de implementar mudanças:

1. Ler `README.md`, `CLAUDE.md` e este `CONTEXTO.md`
2. Confirmar o caminho ativo dos arquivos a serem alterados
3. Validar se existe duplicação de diretórios antes de editar

Após mudanças estruturais:

1. Atualizar este `CONTEXTO.md` se houver alteração de stack, arquitetura, convenções ou pontos de entrada
2. Ajustar o `README.md` se a orientação de leitura inicial precisar mudar

## Quando Atualizar Este Arquivo

Atualize `CONTEXTO.md` quando houver:

- criação ou remoção de apps/pacotes
- mudança de stack principal
- alteração nos pontos de entrada do frontend ou backend
- reorganização de diretórios
- adoção de novas convenções obrigatórias
- descoberta de novos diretórios espelhados, legados ou perigosos para edição
