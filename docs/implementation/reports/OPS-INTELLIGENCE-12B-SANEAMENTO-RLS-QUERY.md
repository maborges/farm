# OPS-INTELLIGENCE-12B — Saneamento do Contexto RLS na Query

Data: 2026-07-29  
Status: concluído — GO

## Causa raiz

`test_list_filters_by_period` prepara datas históricas por meio de `UPDATE` direto em `recommendation_results`. Cada chamada anterior a `_seed_recommendation` persiste com `commit()`. O `RecommendationLifecycleService` configura o tenant com `set_config('app.current_tenant_id', ..., true)`: o terceiro argumento `true` torna o valor local à transação.

Assim, após o `commit`, a sessão inicia uma nova transação sem `app.current_tenant_id`. O `UPDATE` de preparação era o primeiro acesso a uma tabela protegida nessa nova transação; a política RLS tentou converter o contexto vazio em UUID e PostgreSQL rejeitou a operação.

## Comportamento produtivo versus teste

O `RecommendationQueryService` reaplica o contexto RLS antes de `list_recommendations` e `get_recommendation`. A dependency de produção também ativa o tenant por request/transação. Não foi identificada execução produtiva do router ou do query service que acesse `recommendation_results` após um `commit` sem configurar o tenant.

O problema era, portanto, exclusivamente da preparação direta da fixture do teste, não do router, query service, middleware ou sessão compartilhada.

## Decisão e correção

Foi adotada a **Opção A — corrigir somente o teste**.

`_set_created_at` agora recebe `tenant_id` e, imediatamente antes do `UPDATE`, reutiliza `RecommendationLifecycleService._set_rls_context()`. Esse é o setter oficial já usado no domínio e aplica `set_config(..., true)` na nova transação. Após o `commit` da atualização, o contexto volta a expirar como projetado.

Não há `SET` global, UUID artificial, bypass, alteração de política, remoção de `FORCE ROW LEVEL SECURITY` ou substituição do PostgreSQL.

## Auditoria de padrões semelhantes

No diretório `tests/unit/recommendations/`, o único `UPDATE recommendation_results` após `commit` sem reaplicação de tenant era o helper de período deste arquivo. O helper de métricas atualiza timestamps antes do `commit` da mesma transação já contextualizada; não apresenta o defeito e não foi alterado.

## Arquivos alterados

- `services/api/tests/unit/recommendations/test_recommendations_query_router.py`
- `docs/implementation/reports/OPS-INTELLIGENCE-12B-SANEAMENTO-RLS-QUERY.md`

Não foram alterados scheduler, worker, advisory lock, providers, lifecycle funcional, registry, dedupe, tabelas, migrations, API pública, Web, Campo, notificações ou Event/Outbox.

## Validações

```text
.venv/bin/python -m pytest tests/unit/recommendations/test_recommendations_query_router.py -m integration -k "test_list_filters_by_period" -q
1 passed, 10 deselected in 3.35s

.venv/bin/python -m pytest tests/unit/recommendations/test_recommendations_query_router.py -m integration -q
11 passed in 20.31s

.venv/bin/python -m pytest tests/unit/recommendations -m integration -q
30 passed, 44 deselected in 54.78s

.venv/bin/python -m pytest tests/unit/recommendations -q
44 passed, 30 deselected in 1.32s
```

Foi executado `py_compile` no arquivo Python alterado. `ruff check` do arquivo expõe violações preexistentes fora do trecho modificado; as linhas alteradas estão conformes. `git diff --check` foi executado ao final.

## Veredicto OPS-INTELLIGENCE-12

**GO.** A ativação produtiva permanece inalterada; a última falha da suíte de integração de recommendations foi corrigida sem enfraquecer RLS.
