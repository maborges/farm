# OPS-INTELLIGENCE-07A - Estabilização da suíte `recommendations`

## Objetivo

Separar testes unitários puros de testes que dependem de banco/integração no módulo `recommendations`, sem alterar regra de negócio, API pública, providers ou migrations.

## Auditoria dos testes

### `TESTE UNITÁRIO PURO`

- [`services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py)
- [`services/api/tests/unit/recommendations/test_recommendations_models_schemas.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_models_schemas.py)
- [`services/api/tests/unit/recommendations/test_recommendations_registry_engine.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_registry_engine.py)
- [`services/api/tests/unit/recommendations/test_recommendations_providers_restantes.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_providers_restantes.py)
- [`services/api/tests/unit/recommendations/test_recommendations_scheduler_runner.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_scheduler_runner.py)

### `TESTE UNITÁRIO COM DEPENDÊNCIA INDEVIDA DE BANCO`

- Nenhum após a refatoração.

### `TESTE DE INTEGRAÇÃO`

- [`services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py)
- [`services/api/tests/unit/recommendations/test_recommendations_metrics.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_metrics.py)
- [`services/api/tests/unit/recommendations/test_recommendations_query_router.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_query_router.py)
- [`services/api/tests/unit/recommendations/test_recommendations_providers_real.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_providers_real.py)

### `TESTE INSTÁVEL / PRECISA AJUSTE`

- Nenhum no conjunto unitário após a separação.

## Ajustes realizados

- Reescrevi [`test_recommendations_registry_engine.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_registry_engine.py) para usar `SimpleNamespace` e `AsyncMock` em vez de persistência real.
- Reescrevi [`test_recommendations_scheduler_runner.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_scheduler_runner.py) para validar orquestração, batch, `dry_run` e isolamento de erro com fakes.
- Ajustei [`test_recommendations_providers_restantes.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_providers_restantes.py) para remover o último caso que dependia de banco real.
- Marquei os testes realmente integrados com `pytest.mark.integration`.
- Adicionei [`services/api/tests/unit/recommendations/conftest.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/conftest.py) para excluir os testes de integração da execução padrão da suíte unitária.

## O que foi mantido como integração

- Persistência e lifecycle real.
- Métricas agregadas em banco.
- Router/query com FastAPI + sessão real.
- Providers reais com dados seedados.

## Validação executada

- `cd services/api && .venv/bin/python -m pytest tests/unit/recommendations -q`
- Resultado: `29 passed, 27 deselected`
- `cd services/api && .venv/bin/alembic heads`
- Resultado: `20260703_ops_intelligence_02_recommendations_foundation (head)`
- `git diff --check`
- Resultado: limpo

## Próximos riscos técnicos

- Os testes marcados como integração ainda dependem de disponibilidade de banco e dados seedados do ambiente.
- Se a intenção for executar a suíte de integração de recommendations no mesmo pipeline, será necessário um job separado com banco acessível e tempo adequado.
- A separação atual evita timeout na suíte unitária, mas não substitui a execução de integração em ambiente apropriado.

