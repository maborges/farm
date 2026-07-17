# CONTEXTO.md

## Objetivo

Consolida o contexto operacional do AgroSaaS para evitar novo levantamento manual a cada sessão.
Ler junto com `docs/architecture/ai-bootstrap.md` (que define a ordem completa de leitura — não repetida aqui).

## Resumo Executivo

- Projeto: AgroSaaS — monorepo, gestão rural multi-tenant
- Frontend principal: `apps/web` | Backend principal: `services/api`
- Pacotes compartilhados: `packages/*`

## Estrutura Real do Repositório

- `apps/web`: aplicação web principal (Next.js 16)
- `apps/campo`: PWA de campo offline-first (Next.js 16)
- `services/api`: API principal (FastAPI)
- `packages/zod-schemas`, `packages/types`, `packages/utils`: contratos e utilitários compartilhados
- `docs`: documentação técnica e de negócio
- `tests`: testes no nível do repositório
- `pnpm-workspace.yaml` inclui apenas `apps/*` e `packages/*`

## Pontos de Entrada Importantes

**Frontend** (`apps/web/src`):
- `app/layout.tsx` — layout raiz
- `app/(dashboard)` — área autenticada principal
- `app/api/v1/[...path]/route.ts` — proxy interno para backend
- `lib/api.ts` / `lib/api-server.ts` — clientes HTTP (client/server-side)
- `store/use-auth-store.ts` — estado de autenticação

**Backend** (`services/api`):
- `main.py` — instância FastAPI, middlewares, CORS, lifespan, registro de routers
- `run_embedded_jobs` controla se a API roda jobs periódicos no mesmo processo; worker separado em `background_worker.py`
- Storage local e S3/MinIO passam pelo mesmo contrato de `StorageService`
- Domínios principais: `core`, `agricola`, `operacional`, `financeiro`, `pecuaria`, `imoveis`, `notificacoes`, `automacoes`
- Migrations em `services/api/migrations`

## Convenções de Projeto

Regras completas de stack, segurança, RBAC e padrões de código vivem em `CLAUDE.md` e
`docs/architecture/agrosaas-engineering-playbook.md` — não duplicadas aqui.

## Sinais de Atenção (⚠️ único neste documento)

Há indícios de duplicação ou espelhamento indevido dentro de `apps/web`, incluindo caminhos como:
- `apps/web/services/api`
- `apps/web/docs`
- arquivos de banco e artefatos auxiliares dentro de `apps/web`

Esses caminhos **não são a fonte primária** da aplicação. Antes de editar, confirme se o arquivo está no
caminho ativo do projeto e não em uma cópia espelhada.

**Nota de duplicação conhecida:** `API_REFERENCE_RBAC.md` apareceu cadastrado em dois caminhos idênticos
durante auditoria — verificar se há espelhamento real no repositório e, se sim, eliminar uma das cópias.

## Fluxo Recomendado

**Antes de implementar:**
1. Seguir `docs/architecture/ai-bootstrap.md`
2. Confirmar o caminho ativo dos arquivos a serem alterados (ver "Sinais de Atenção")
3. Consultar `agrosaas-domain-map.md` se a mudança tocar domínio ou fronteira

**Depois de mudanças estruturais:**
1. Atualizar este `CONTEXTO.md` se houver alteração de stack, pontos de entrada ou convenções
2. Ajustar `ai-bootstrap.md` apenas se a ordem/condição de leitura mudar

## Quando Atualizar Este Arquivo

- Criação/remoção de apps ou pacotes
- Mudança de stack principal
- Alteração nos pontos de entrada do frontend ou backend
- Reorganização de diretórios
- Descoberta de novos diretórios espelhados, legados ou perigosos para edição