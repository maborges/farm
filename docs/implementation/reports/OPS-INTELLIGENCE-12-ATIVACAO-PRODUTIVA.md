# OPS-INTELLIGENCE-12 — Ativação Produtiva Controlada

## Resultado

O `RecommendationSchedulerService` foi ativado no worker periódico oficial, sem criar scheduler, worker, fila, API, tabela, registry, lifecycle ou fluxo de notificações paralelos.

## Ponto de integração

O ponto escolhido foi `services/api/core/background_jobs.py`, já utilizado pelo worker `services/api/background_worker.py` e pela sincronização ERP agendada. Foi incluído `run_recommendation_scheduler_loop`, executando o ciclo canônico a cada cinco minutos.

O ciclo produtivo fica em `services/api/recommendations/scheduler.py`, junto do scheduler que já existia. Ele:

1. obtém um advisory lock PostgreSQL para impedir ciclos concorrentes;
2. lista tenants ativos;
3. abre uma sessão nova por tenant;
4. fixa `app.current_tenant_id` e `session.info["tenant_id"]`;
5. expira recomendações vencidas quando não for `dry_run`;
6. invoca o `RecommendationSchedulerService` existente por tenant e lote;
7. confirma apenas o escopo daquele tenant;
8. limpa o contexto RLS antes de devolver a conexão ao pool.

Uma falha de provider já é isolada pelo scheduler existente. Uma falha não prevista no tenant faz rollback somente daquela sessão e permite que os demais tenants continuem.

## Arquitetura preservada

- Reutilizado `RecommendationSchedulerService` e `RecommendationExecutionRunner` existentes.
- Reutilizado o worker `core/background_jobs.py` existente.
- Reutilizado o padrão de advisory lock e RLS do scheduler ERP existente.
- Nenhuma rota, migration, tabela, fila, provider, registry ou read model foi criado.
- O Alert Engine não foi usado como scheduler de recomendações e os lifecycles continuam independentes.

## Arquivos alterados

- `services/api/core/background_jobs.py`
- `services/api/recommendations/scheduler.py`
- `services/api/recommendations/lifecycle_service.py`
- `services/api/tests/unit/recommendations/test_recommendations_productive_scheduler.py`
- `docs/implementation/reports/OPS-INTELLIGENCE-12-ATIVACAO-PRODUTIVA.md`

## Telemetria e idempotência

Os logs estruturados do ciclo e de cada provider incluem tenant, provider, duração, recomendações geradas, atualizadas, expiradas, falhas e `dry_run`.

A concorrência é bloqueada por advisory lock de PostgreSQL. A idempotência de conteúdo permanece no índice parcial único por `tenant_id + dedupe_key` e no `RecommendationLifecycleService`: execuções subsequentes atualizam a recomendação ativa em vez de duplicá-la.

## Validação

Executado em `services/api`:

```bash
.venv/bin/python -m py_compile recommendations/scheduler.py recommendations/lifecycle_service.py core/background_jobs.py tests/unit/recommendations/test_recommendations_productive_scheduler.py
.venv/bin/python -m pytest tests/unit/recommendations -q
```

Resultado: `44 passed, 28 deselected`.

Também foi executada a bateria marcada como integração do mesmo diretório. Ela chegou a `13 passed` antes de falhar em `test_agricultura_provider_generates_candidates_from_context`, que esperava a regra preexistente `AGRI_CUSTO_ACIMA_PREVISTO`. A falha está em `AgriculturaRecommendationProvider` e não percorre o worker, o ciclo produtivo, RLS de background ou a alteração desta entrega. Não foi alterada por estar fora do escopo de OPS-INTELLIGENCE-12.

Cobertura confirmada no domínio de recommendations:

- execução normal e por lote;
- múltiplos tenants;
- lock concorrente;
- contexto RLS e reset da conexão;
- `dry_run` sem expiração ou commit produtivo;
- lote sem providers;
- falha contida no tenant;
- falha isolada de provider e dedupe preservado pelos testes existentes.

## Limitações e próximos passos

- A periodicidade é fixa em cinco minutos no worker atual; políticas configuráveis por provider não fazem parte deste escopo.
- Não há subscriber Event/Outbox nesta entrega; permanece para OPS-INTELLIGENCE-13.
- Permissões RBAC específicas das ações de lifecycle permanecem para OPS-INTELLIGENCE-14.
- A retirada do `ClimaRecommendationService` legado continua condicionada à ausência de consumidores, em OPS-INTELLIGENCE-15.
- O rollout é **GO COM RESSALVAS**: os testes unitários do domínio estão verdes, mas a suíte de integração de providers possui a falha preexistente descrita acima e deve ser saneada antes de usar essa bateria como gate integral de release.
