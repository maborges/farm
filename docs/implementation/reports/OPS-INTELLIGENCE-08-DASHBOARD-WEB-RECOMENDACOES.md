# OPS-INTELLIGENCE-08 - Dashboard Web de Recomendações Operacionais

## Auditoria inicial

- `apps/web/src/app/`: existiam dashboards próximos e reutilizáveis, mas não havia uma tela global de recomendações operacionais pronta.
- `apps/web/src/components/`: existiam `PageHeader`, `EmptyState`, `StatCard`, `Table`, `Sheet`, `Select`, `Textarea` e outros blocos reutilizáveis.
- `apps/web/src/hooks/` e `apps/web/src/lib/`: existiam padrões de hooks com TanStack Query e o client `apiFetch`, mas não havia hook global de recomendações.
- `services/api/recommendations/`: a API global já existia e atendia o consumo read-only, com listagem, detalhe, lifecycle e métricas. Foi necessário apenas o ajuste mínimo de contrato para filtro por período na listagem.

## Classificação dos achados

- `apps/web/src/app/`: **EXISTE PARCIALMENTE**
- `apps/web/src/components/`: **EXISTE PARCIALMENTE**
- `apps/web/src/hooks/`: **EXISTE PARCIALMENTE**
- `apps/web/src/lib/`: **EXISTE PARCIALMENTE**
- `services/api/recommendations/`: **EXISTE E ATENDE**, com ajuste mínimo de contrato para `start_date` e `end_date` na listagem

## Rota criada

- `GET /dashboard/inteligencia-operacional/recomendacoes`
- Foi adicionado redirect em `/dashboard/inteligencia-operacional` para essa rota.
- Foi incluído atalho no menu lateral em Copiloto IA.

## Componentes e hooks criados/reaproveitados

- Reaproveitados:
  - `PageHeader`
  - `EmptyState`
  - `StatCard`
  - `Sheet`
  - `Select`
  - `Table`
  - `Textarea`
  - `apiFetch`
  - `useAppStore`
- Criados:
  - `apps/web/src/components/recommendations/recommendations-dashboard-client.tsx`
  - `apps/web/src/hooks/use-recommendations.ts`

## Endpoints consumidos

- `GET /api/v1/recommendations`
- `GET /api/v1/recommendations/metrics/summary`
- `GET /api/v1/recommendations/metrics/by-domain`
- `GET /api/v1/recommendations/metrics/by-rule`
- `GET /api/v1/recommendations/metrics/lifecycle`
- `POST /api/v1/recommendations/{recommendation_id}/view`
- `POST /api/v1/recommendations/{recommendation_id}/accept`
- `POST /api/v1/recommendations/{recommendation_id}/dismiss`
- `POST /api/v1/recommendations/{recommendation_id}/postpone`
- `POST /api/v1/recommendations/{recommendation_id}/execute`
- `POST /api/v1/recommendations/{recommendation_id}/reopen`

## Ações de lifecycle expostas

- Visualizar
- Aceitar
- Descartar
- Adiar
- Marcar executada
- Reabrir

## Contrato mínimo ajustado no backend

- `services/api/recommendations/query_service.py`
  - adicionou filtro por `start_date` e `end_date`
  - aplica o recorte temporal sobre `RecommendationResult.created_at`
- `services/api/recommendations/router.py`
  - expôs `start_date` e `end_date` na listagem

## Restrições preservadas

- Não criou novo engine, provider, scheduler ou tabela.
- Não integrou Alert Engine.
- Não integrou NotificationDispatcher.
- Não mexeu com Campo PWA.
- Não executa mutação operacional além do lifecycle explícito da recomendação.
- Não recalcula recomendações no frontend.
- Não expõe dados cross-tenant.

## Validação executada

- `cd apps/web && pnpm exec eslint src/components/recommendations/recommendations-dashboard-client.tsx src/hooks/use-recommendations.ts 'src/app/(dashboard)/dashboard/inteligencia-operacional/page.tsx' 'src/app/(dashboard)/dashboard/inteligencia-operacional/recomendacoes/page.tsx' src/lib/sidebar-config.ts --no-warn-ignored`
  - passou
- `cd apps/web && pnpm exec playwright test tests/e2e/recomendacoes-operacionais.spec.ts`
  - passou, 8/8 testes
- `git diff --check`
  - passou
- `cd apps/web && pnpm --filter web typecheck`
  - falhou por erros pré-existentes fora deste escopo em:
    - `src/app/(dashboard)/dashboard/financeiro/hedge/mtm/page.tsx`
    - `src/app/(dashboard)/dashboard/financeiro/hedge/painel/page.tsx`
    - `src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
- `cd services/api && .venv/bin/python -m pytest tests/unit/recommendations/test_recommendations_query_router.py -m integration -q`
  - tentativa realizada, mas a suíte de integração não concluiu dentro da janela disponível nesta sessão

## Pendências para Campo PWA / notificações futuras

- Nenhuma integração foi criada aqui.
- Se o dashboard evoluir para ações assistidas, isso deve ser feito em camada separada e com contrato explícito, sem acoplar a visualização à notificação automática.

## Observação final

- A interface entregue é inicial e focada em consumo de API oficial, filtros, lista, detalhe e lifecycle explícito.
- A base está pronta para expandir com paginação, gráficos mais ricos e navegação contextual, sem mexer na lógica de recomendação.
