# Validação Frota-15.1 — Tracking da Landing

Data da validação: 2026-05-07 / 2026-05-08

## Objetivo

Validar funcionalmente o tracking público da landing page, confirmando:

- persistência dos eventos públicos
- gravação dos campos esperados
- manutenção de sessão e variante A/B/C
- funcionamento do rate limit
- consistência do endpoint `GET /api/v1/growth/events/metrics`

## Comandos executados

```bash
cd services/api
.venv/bin/alembic upgrade head

curl -s -o /tmp/backend_health_tracking.out -w '%{http_code}' http://127.0.0.1:8000/docs

rm apps/web/.next/dev/lock

/bin/bash -lc 'BACKEND_URL=http://127.0.0.1:8000 pnpm exec next dev --webpack --hostname 127.0.0.1 --port 3002'

curl -I http://127.0.0.1:3002/

node /tmp/frota15_tracking_validate.js

cd services/api
.venv/bin/python - <<'PY'
import pathlib
import py_compile

root = pathlib.Path('/opt/lampp/htdocs/farm/services/api')
files = [p for p in root.rglob('*.py') if '.venv' not in p.parts and '__pycache__' not in p.parts]
for path in files:
    py_compile.compile(str(path), doraise=True)
print(len(files))
PY

cd services/api
.venv/bin/alembic upgrade head

pnpm -C apps/web exec tsc --noEmit

pnpm -C apps/web exec eslint src/app/page.tsx src/lib/landing-tracking.ts src/components/landing/ScrollTracker.tsx
```

## Pré-condições e destravamentos

Para viabilizar a subida real da API, foi necessário corrigir dois imports quebrados no módulo novo de tracking:

- `services/api/growth/router.py`
  - de `from core.database import get_session`
  - para `from core.dependencies import get_session`
- `services/api/growth/models.py`
  - de `from core.models.base import Base`
  - para `from core.database import Base`

Sem essas correções a API não iniciava, então a validação end-to-end ficava bloqueada.

## Eventos testados

Stamp da execução principal:

```text
20260508003322
```

Sessões usadas:

- `sid-A-20260508003322`
  - visitante sem login
  - sem UTM
  - variante `A`
  - scroll até fim da página
  - refresh da página
  - clique em `plan_select`
- `sid-B-20260508003322`
  - visitante sem login
  - com UTM `utm_source=google`, `utm_medium=cpc`, `utm_campaign=frota15-20260508003322`
  - variante `B`
  - clique em `cta_test_click`
- `sid-C-20260508003322`
  - visitante sem login
  - com UTM `utm_source=linkedin`, `utm_medium=social`, `utm_campaign=frota15-20260508003322`
  - variante `C`
  - clique em `cta_demo_click`
- `sid-RATE-20260508003322`
  - usado apenas no teste de rate limit

Eventos confirmados no banco:

- `landing_view`
- `scroll_50`
- `scroll_90`
- `cta_test_click`
- `cta_demo_click`
- `plan_select`

## Persistência de campos

Consulta no banco confirmou gravação de:

- `sessao_id`
- `headline_variant`
- `utm_source`
- `utm_campaign`
- `utm_medium`
- `path`
- `device`
- `user_agent`
- `ip_hash`

Exemplos confirmados:

```text
sid-B-20260508003322 | landing_view   | B | google   | frota15-20260508003322 | cpc    | /                  | desktop | ip_hash present
sid-B-20260508003322 | cta_test_click | B | google   | frota15-20260508003322 | cpc    | /                  | desktop | ip_hash present
sid-C-20260508003322 | landing_view   | C | linkedin | frota15-20260508003322 | social | /                  | desktop | ip_hash present
sid-C-20260508003322 | cta_demo_click | C | linkedin | frota15-20260508003322 | social | /                  | desktop | ip_hash present
sid-A-20260508003322 | plan_select    | A | null     | null                   | null   | /?plan=Planejamento | desktop | ip_hash present
```

`user_agent` foi persistido como browser headless no teste de navegação e como `node` no teste de rate limit.

## Sessão e variante

Refresh validado na sessão `sid-A-20260508003322`:

```json
{
  "beforeRefresh": {
    "sid": "sid-A-20260508003322",
    "variant": "A"
  },
  "afterRefresh": {
    "sid": "sid-A-20260508003322",
    "variant": "A"
  }
}
```

Resultado:

- mesma `sessao_id` mantida após refresh
- mesma `headline_variant` mantida após refresh
- variantes `A`, `B` e `C` persistidas conforme forçadas em `localStorage` por sessão de teste

## Rate limit

Teste executado com 70 `POST /api/v1/growth/events` sequenciais para o mesmo IP:

```json
{
  "accepted": 48,
  "limited": 22,
  "first429At": 49
}
```

Interpretação:

- o rate limit está funcionando e retornando `429`
- o primeiro `429` ocorreu na requisição 49 porque a mesma janela de 60 segundos já tinha consumido 12 requests das navegações anteriores na landing

## Métricas

Retorno validado em `GET /api/v1/growth/events/metrics`:

```json
{
  "visitas": 53,
  "cta_clicks": 3,
  "conversion_rate": 5.66,
  "por_variant": {
    "A": {
      "visitas": 51,
      "cta_clicks": 1,
      "conversion_rate": 1.96
    },
    "B": {
      "visitas": 1,
      "cta_clicks": 1,
      "conversion_rate": 100.0
    },
    "C": {
      "visitas": 1,
      "cta_clicks": 1,
      "conversion_rate": 100.0
    }
  },
  "periodo_dias": 30
}
```

Conferência via banco:

```text
visitas = 53
cta_clicks = 3
visitas_a = 51 | cta_a = 1
visitas_b = 1  | cta_b = 1
visitas_c = 1  | cta_c = 1
```

As métricas agregadas bateram com os registros persistidos.

## Verificações técnicas finais

Resultados:

- `py_compile` backend: `FILES=988`, `ERRORS=0`
- `alembic upgrade head`: sem erro
- `pnpm -C apps/web exec tsc --noEmit`: sem erro
- `pnpm -C apps/web exec eslint src/app/page.tsx src/lib/landing-tracking.ts src/components/landing/ScrollTracker.tsx`: sem erro

## Problemas encontrados

1. A API não subia inicialmente por imports incorretos no módulo novo de growth/tracking.
2. O frontend não subiu na primeira tentativa por `lock` stale em `apps/web/.next/dev/lock`.
3. O bind local do frontend exigiu execução fora do sandbox na porta `3002`.
4. A ordem temporal dos eventos não é estritamente garantida.
   Exemplo: em uma sessão houve `scroll_50` persistido antes de um `landing_view` subsequente, o que é compatível com múltiplos `fetch(..., keepalive: true)` assíncronos.

## Conclusão final

O tracking público da landing ficou validado funcionalmente após destravar os imports do módulo novo.

Status final:

- persistência dos eventos: OK
- persistência dos campos obrigatórios: OK
- visitante sem login: OK
- visitante com UTM: OK
- refresh mantendo sessão: OK
- variante A/B/C persistida por sessão: OK
- rate limit: OK
- endpoint `GET /api/v1/growth/events/metrics`: OK

Risco residual:

- se a ordem exata entre eventos for requisito analítico, o modelo atual baseado em múltiplos `fetch` assíncronos pode produzir ordenação diferente da ordem de interação do usuário.
