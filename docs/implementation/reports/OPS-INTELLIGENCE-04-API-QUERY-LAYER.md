# OPS-INTELLIGENCE-04 - API / Query Layer

## 1. Auditoria Inicial

### EXISTE E ATENDE
- Nenhum endpoint global de recommendations existia antes desta entrega.
- O módulo `services/api/recommendations/` já tinha o núcleo oficial, lifecycle e persistência.

### EXISTE PARCIALMENTE
- `services/api/agricola/recomendacoes/` expõe recomendações assistidas, mas é um motor local do domínio agrícola.
- `services/api/financeiro/routers/lancamentos.py` expõe recomendações do contexto financeiro, mas sem contrato global persistido.
- `services/api/agricola/climatico/recommendation_service.py` existe como referência histórica, porém não é a camada oficial global.

### NÃO EXISTE
- Router global oficial de leitura para `recommendation_results`.
- Query service global read-only.
- Endpoints globais para lifecycle explícito de recomendações persistidas.

## 2. Endpoints Criados

- `GET /api/v1/recommendations`
- `GET /api/v1/recommendations/{recommendation_id}`
- `POST /api/v1/recommendations/{recommendation_id}/view`
- `POST /api/v1/recommendations/{recommendation_id}/accept`
- `POST /api/v1/recommendations/{recommendation_id}/dismiss`
- `POST /api/v1/recommendations/{recommendation_id}/postpone`
- `POST /api/v1/recommendations/{recommendation_id}/execute`
- `POST /api/v1/recommendations/{recommendation_id}/reopen`

## 3. Query Service Criado

- Arquivo: `services/api/recommendations/query_service.py`
- Responsabilidade:
  - leitura read-only das recomendações persistidas;
  - paginação;
  - filtros por `domain`, `status`, `priority`, `unidade_produtiva_id`, `scope_type` e `scope_id`;
  - ordenação por prioridade e data;
  - proteção por `tenant_id` e contexto RLS.

## 4. Lifecycle Actions Expostas

- `viewed`
- `accepted`
- `dismissed`
- `postponed`
- `executed`
- `reopened`

As ações apenas alteram lifecycle da recomendação. Não executam mutação operacional de negócio.

## 5. Restrições Preservadas

- Não alterei frontend.
- Não alterei Campo PWA.
- Não criei providers novos.
- Não integrei com Notificações.
- Não integrei com Alert Engine.
- Não chamei providers a partir da API de leitura.
- Não promovi recomendação global a mutação operacional automática.
- Mantive `tenant_id` em todas as rotas e consultas.
- Mantive isolamento por RLS/RBAC existentes.
- Não exponho dados cross-tenant.

## 6. Implementação Aplicada

- `services/api/recommendations/router.py`
- `services/api/recommendations/query_service.py`
- `services/api/recommendations/schemas.py` ampliado com payloads de lifecycle
- `services/api/recommendations/__init__.py` exportando a camada nova
- `services/api/main.py` com inclusão do router global

## 7. Validação Executada

Executado:
- `cd services/api && .venv/bin/python -m pytest tests/unit/recommendations -q`

Resultado:
- `35 passed in 163.02s`

Executado também:
- `cd services/api && .venv/bin/alembic heads`
- `git diff --check`

## 8. Comandos Para Validação Local

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -q
.venv/bin/alembic heads
git diff --check
```
