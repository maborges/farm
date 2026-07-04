# OPS-INTELLIGENCE-09 - Campo PWA Recomendações

## Auditoria inicial

| Área | Achado | Classificação |
| --- | --- | --- |
| `apps/campo/src/lib/sync/pull.ts` | Já existia sync pull e cache de recomendações climáticas, mas sem consumo do Recommendation Engine global. | EXISTE PARCIALMENTE |
| `apps/campo/src/lib/db.ts` | Já existia tabela Dexie para `recomendacoes_climaticas`, mas nenhuma estrutura para recomendações operacionais globais. | EXISTE PARCIALMENTE |
| `apps/campo/src/components/agricola/climatico/clima-operacional-card.tsx` | Havia leitura offline do cache climático local. | EXISTE E ATENDE |
| `apps/campo/src/app/(campo)/home/page.tsx` | Havia home com tarefas e sync, mas sem seção de inteligência operacional. | NÃO EXISTE |
| `apps/campo/src/app/(campo)/caderno/page.tsx` | Havia fluxo offline de registros e evidências, sem consumo de recomendações globais. | NÃO EXISTE |
| `services/api/campo/service.py` | O pull chamava `ClimaRecommendationService` direto e não lia `recommendation_results` persistidos. | EXISTE PARCIALMENTE |
| `services/api/recommendations/` | O engine global, providers, query layer, lifecycle e métricas já existiam. | EXISTE E ATENDE |

## Decisão de sync

- O Campo PWA passou a consumir recomendações a partir do payload oficial de `sync/pull`.
- O backend não chama providers no pull.
- O backend lê apenas `recommendation_results` persistidos.
- O pull continua resiliente: falha de leitura de recomendações é logada e não bloqueia o sync principal.
- O cache local de recomendações usa semântica de snapshot: a tabela é limpa e repovoada a cada pull bem-sucedido.

## Payload incluído

- `recomendacoes_operacionais`
  - Fonte: `recommendation_results` persistidos.
  - Filtro: tenant atual, `unidade_produtiva_id` autorizada, domínios `FIELD`, `AGRICULTURE`, `LIVESTOCK`, `OPERATIONS`, status ativos.
  - Limite: 30 itens por pull.
  - Campos: `id`, `tenant_id`, `unidade_produtiva_id`, `domain`, `status`, `priority`, `source_type`, `action_type`, `provider_name`, `rule_code`, `scope_type`, `scope_id`, `title`, `summary`, `rationale`, `dedupe_key`, `source_signal_ids`, `confidence`, `action_label`, `action_target`, `context`, `created_at`, `updated_at`, `expires_at`, `viewed_at`, `accepted_at`, `dismissed_at`, `postponed_until`, `executed_at`, `superseded_at`, `superseded_by_id`.
- `recomendacoes_climaticas`
  - Compatibilidade com a tela climática existente.
  - Derivadas de `recommendation_results` persistidos do provider climático global.
  - Sem chamada ao `ClimaRecommendationService` no pull.
  - Agrupadas por `unidade_produtiva_id` e por tipo operacional legado.

## Estrutura local Dexie

- Nova tabela: `recomendacoes_operacionais`.
- Índices: `id, unidade_produtiva_id, domain, status, priority, updated_at`.
- A tabela `recomendacoes_climaticas` foi mantida.
- O pull faz `clear()` + `bulkPut()` nas duas tabelas para manter o snapshot local consistente.
- A versão do banco Dexie foi incrementada para `12`.

## Tela e componentes

- Tela criada: `/recomendacoes`
- Arquivo: `apps/campo/src/app/(campo)/recomendacoes/page.tsx`
- Comportamento:
  - lista offline das recomendações sincronizadas;
  - filtros simples por domínio, status e prioridade;
  - detalhe com título, resumo, justificativa, ação recomendada, origem/regra e linha do tempo;
  - loading state, empty state e offline state;
  - exibição da última sincronização.
- Home atualizada:
  - seção de resumo em `apps/campo/src/app/(campo)/home/page.tsx`;
  - card com contagem e preview das recomendações operacionais;
  - atalho para a tela dedicada.

## Lifecycle

- Lifecycle offline de recomendações: `ADIADO`.
- Motivo: não existe fila offline segura já estabelecida para mutações de recomendações.
- Nenhuma mutação operacional foi criada no Campo.
- Nenhuma integração com `NotificationDispatcher` ou `Alert Engine` foi adicionada.

## Restrições preservadas

- Não foi criado novo Recommendation Engine.
- Não foi criado provider novo.
- Não foi criada tabela backend nova.
- Não houve mutação operacional automática.
- Não houve quebra do sync principal.
- Não houve dependência de conexão para abrir a tela com dados já sincronizados.
- Não foram usados mocks em produção.

## Validação executada

- `services/api/.venv/bin/python -m pytest services/api/tests/unit/campo -q`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/recommendations -q`
- `pnpm typecheck` em `apps/campo`
- `pnpm lint` em `apps/campo`
- `pnpm build` em `apps/campo`
- `git diff --check`

## Pendências futuras

- Implementar lifecycle offline real somente quando houver fila de mutações segura para recomendações.
- Considerar paginação/expansão do snapshot se o volume de recomendações crescer além do limite atual.
- Refinar o mapeamento legado de clima se a taxonomia operacional evoluir.
