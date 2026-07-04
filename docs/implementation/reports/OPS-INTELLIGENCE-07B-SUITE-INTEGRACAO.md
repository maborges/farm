# OPS-INTELLIGENCE-07B - Suite explícita de integração para `recommendations`

## Objetivo

Criar um comando explícito para executar apenas testes de integração do módulo `recommendations`, mantendo a suíte unitária padrão isolada e sem alterar regra de negócio.

## Auditoria

### Configuração atual

- Não havia `pytest.ini` específico para `recommendations`.
- O repositório já usa o padrão de integração em `services/api/tests/integration/`, com fixtures e helpers próprios.
- Para `recommendations`, a separação foi feita por marcação `integration` em testes que dependem de banco real.

### Padrão existente no projeto

- Diretório [`services/api/tests/integration/`](/opt/lampp/htdocs/farm/services/api/tests/integration/) já é o padrão canônico de integração.
- Arquivo [`services/api/tests/integration/conftest.py`](/opt/lampp/htdocs/farm/services/api/tests/integration/conftest.py) fornece fixtures compartilhadas de integração.
- Há testes unitários em outros módulos que explicitamente dizem que certos caminhos são testados em `integration/`.

## Ajuste realizado

- Mantive [`services/api/tests/unit/recommendations/conftest.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/conftest.py) como filtro padrão para excluir marcados `integration` da suíte unitária.
- Os testes realmente dependentes de banco no módulo `recommendations` foram marcados com `pytest.mark.integration`:
  - [`services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py)
  - [`services/api/tests/unit/recommendations/test_recommendations_metrics.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_metrics.py)
  - [`services/api/tests/unit/recommendations/test_recommendations_query_router.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_query_router.py)
  - [`services/api/tests/unit/recommendations/test_recommendations_providers_real.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_providers_real.py)

## Comandos explícitos

### Suíte unitária padrão

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -q
```

### Apenas integração

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -m integration -q
```

## Validação executada

### Unitários

- Comando executado com sucesso.
- Resultado: `29 passed, 27 deselected`

### Integração

- Comando executado:
  - `.venv/bin/python -m pytest tests/unit/recommendations -m integration -q`
- Resultado observado:
  - falha em [`services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py)
  - primeira falha visível: `test_create_recommendation_and_lifecycle_event`
  - segunda falha visível: `test_dedupe_updates_active_recommendation_without_duplication`
- Tipo de falha:
  - `infraestrutura / banco indisponível ou lento para conexão`
  - o traceback mostrou timeout de conexão `asyncpg` durante a criação da sessão no fixture `session`

### Outros comandos

- `cd services/api && .venv/bin/alembic heads` -> `20260703_ops_intelligence_02_recommendations_foundation (head)`
- `git diff --check` -> limpo

## Observações técnicas

- O marker `integration` está registrado localmente via [`services/api/tests/unit/recommendations/conftest.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/conftest.py), sem introduzir nova regra de negócio.
- A suíte unitária padrão permanece estável e não tenta abrir banco real para os casos marcados como integração.
- O comando de integração está explícito e reproduz o comportamento esperado; a falha atual é ambiental, não de contrato do marker.

## Próximos riscos técnicos

- Os testes de integração ainda dependem de um banco PostgreSQL disponível e responsivo no ambiente.
- Se o pipeline exigir esse comando, ele precisa de um estágio com DB acessível e tempo suficiente para fixtures.
- Se quiser separar por caminho físico em vez de marker, o próximo passo seria mover os testes para `services/api/tests/integration/recommendations/`, mas isso não foi feito porque a marcação já resolve o critério pedido sem churn extra.

