# ERP-TENANT-ADMIN-01B - Validacao Operacional da Configuracao, Credenciais e Consistencia Canonica no Console do Tenant

## Resumo consolidado

As fases `ERP-TENANT-ADMIN-01B.1` e `ERP-TENANT-ADMIN-01B.2` foram executadas no tenant real:

* `tenant_id = 7a034d03-bd2d-4de5-994a-405e282075ba`
* tenant: `Grancafe`
* usuario validado: `erp.validation.console@example.com`

Resultado consolidado:

* autenticacao, cookies, proxy e contexto RLS ficaram estaveis no tenant real
* o `500` de `GET /api/v1/integracoes/erp/diagnostico` foi corrigido
* os endpoints ERP monitorados responderam `200` direto no backend e via proxy
* `save` oficial sem secret foi executado com sucesso e sem rotacao de credencial
* `testar-conexao` oficial executou com sucesso
* a reconciliacao legada terminou em `BOTH_CONSISTENT`

Limites ainda existentes:

* `tenant-1` continua invalido operacionalmente neste ambiente e nao deve ser usado como tenant real
* o console do provider Sankhya nao materializa formulario editavel porque o provider nao publica `connection_schema.fields`/`credential_schema.fields`; a configuracao aparece em resumo visual, mas o `save` precisou ser validado pela API oficial
* `pnpm run typecheck` no frontend continua falhando por referencias quebradas a `.next/types/**/*.ts` ausentes no `tsconfig`, condicao preexistente a esta correcao backend
* o ruido de notificacoes por `NEXT_PUBLIC_WS_URL=http://localhost:3000` persiste, sem impacto no diagnostico ERP

## ERP-TENANT-ADMIN-01B.1 — Contexto autenticado

### Ambiente validado

* Frontend: `http://127.0.0.1:3001`
* Backend: `http://127.0.0.1:8000`
* Proxy frontend: `apps/web/src/app/api/v1/[...path]/route.ts`
* Login UI: `apps/web/src/components/auth/login-form.tsx`
* Cliente HTTP frontend: `apps/web/src/lib/api.ts`
* Auth actions: `apps/web/src/app/actions/auth.ts`
* Bootstrap de sessao: `apps/web/src/components/auth/auth-bootstrap.tsx`
* Guard de sessao: `apps/web/src/components/auth/session-guard.tsx`
* Backend auth router: `services/api/core/routers/auth.py`
* Backend auth service: `services/api/core/services/auth_service.py`
* Dependencias de auth/tenant/permissao: `services/api/core/dependencies.py`
* CORS backend: `services/api/main.py`

### Usuario legitimo

* `erp.validation.console@example.com`
* vinculo ativo em `tenant_usuarios`
* `is_owner = true`
* pertencente ao tenant `7a034d03-bd2d-4de5-994a-405e282075ba`
* senha restabelecida pelo fluxo oficial de recuperacao

### Fluxo oficial confirmado

`/login`
-> `POST /api/v1/auth/login`
-> emissao de JWT
-> persistencia em cookie `token`
-> cookie `tenant_id`
-> cookie `unidade_produtiva_id`
-> chamadas frontend para `/api/v1/...`
-> proxy Next.js repassa `Cookie` e `Authorization`
-> backend resolve `request.state`
-> dependencias de tenant/permissao aplicam contexto
-> RLS permanece ativa

### Cookies observados

* `token`
* `tenant_id`
* `unidade_produtiva_id`

Atributos observados:

* dominio `127.0.0.1`
* `path=/`
* `HttpOnly=true`
* `SameSite=Lax`
* `Secure=false` no ambiente HTTP local

### Matriz de endpoints 401 auditados

| Metodo | Endpoint | Origem | Cookie/JWT enviado | Resultado final |
| ------ | -------- | ------ | ------------------ | --------------- |
| `GET` | `/api/v1/auth/me` | backend direto | nenhum | `401` esperado |
| `GET` | `/api/v1/auth/me` | backend direto | bearer valido | `200` |
| `GET` | `/api/v1/auth/me` | proxy | nenhum | `401` esperado |
| `GET` | `/api/v1/auth/me` | proxy | bearer valido | `200` |
| `GET` | `/api/v1/auth/me` | proxy | cookies validos | `200` |
| `GET` | `/api/v1/integracoes/erp/status` | backend direto | bearer valido | `200` |
| `GET` | `/api/v1/integracoes/erp/status` | proxy | bearer valido | `200` |
| `GET` | `/api/v1/integracoes/erp/status` | proxy | cookies validos | `200` |
| `GET` | `/api/v1/integracoes/sankhya/config` | backend direto | bearer valido | `200` |
| `GET` | `/api/v1/integracoes/sankhya/config` | proxy | bearer valido | `200` |
| `GET` | `/api/v1/integracoes/sankhya/config` | proxy | cookies validos | `200` |

Conclusao:

* o `401` relatado anteriormente deixou de se reproduzir no fluxo real do tenant
* o proxy nao removeu `Cookie` nem `Authorization`
* o contexto de tenant e RLS foi preservado

### Primeiro tenant

Validado:

* dashboard acessivel
* Console ERP acessivel em `/dashboard/settings/integracoes/erp`
* reload autenticado preservado
* status/config/schema/health/jobs/timeline/associacoes responderam

Screenshots:

* `/tmp/erp-console-authenticated-final.png`
* `/tmp/erp-console-authenticated-reload-final.png`

### Segundo tenant

`tenant-1` permanece:

* inexistente na tabela de tenants
* sem vinculo real
* nao UUID
* invalido operacionalmente neste ambiente

## ERP-TENANT-ADMIN-01B.2 — Diagnostico e fechamento operacional

### Causa do erro de timezone

Erro reproduzido no tenant real:

* endpoint: `GET /api/v1/integracoes/erp/diagnostico`
* arquivo: `services/api/integracoes/sankhya/services/sync_service.py`
* funcao: `SankhyaSyncService.obter_diagnostico_operacional`
* linha da falha observada: `1361`
* helper de comparacao: `SankhyaSyncService._resolve_latest_timestamp`
* linha da comparacao observada: `1742` antes da correcao
* excecao: `TypeError: can't compare offset-naive and offset-aware datetimes`

Stack real capturada:

* `obter_diagnostico_operacional()` chamou `_resolve_latest_timestamp(...)`
* `_resolve_latest_timestamp()` fazia `max(valid)` sobre datetimes mistos

### Campos envolvidos e origem

| Campo | Origem | Tipo no banco | Valor Python observado | Timezone |
| ----- | ------ | ------------- | ---------------------- | -------- |
| `status_payload.last_success_at` | `IntegrationHealth.last_success_at` | `DateTime(timezone=True)` | aware | `UTC` |
| `status_payload.last_failure_at` | `IntegrationHealth.last_failure_at` | `DateTime(timezone=True)` | aware | `UTC` |
| `health_payload.checked_at` | `IntegrationHealth.checked_at` | `DateTime(timezone=True)` | aware | `UTC` |
| `job.finished_at` | `IntegrationJob.finished_at` | `DateTime(timezone=True)` | aware | `UTC` |
| `log.completed_at` | `SankhyaSyncLog.completed_at` | `DateTime` legado | naive | `None`, historicamente UTC |

Valores reais sanitizados observados no tenant:

* aware exemplo: `2026-07-14T02:38:22.697133+00:00`
* aware exemplo: `2026-07-14T14:31:36.565385+00:00`
* naive legado exemplo: `2026-07-14T02:38:22.406299`
* naive legado exemplo: `2026-07-10T17:36:33.467015`

Comparacao que quebrava:

* `max([aware UTC, ..., naive historico UTC])`

### Politica adotada

Politica unica aplicada ao diagnostico e timeline:

* comparacoes internas em UTC timezone-aware

Contrato usado:

* timestamps canônicos `IntegrationHealth` e `IntegrationJob` ja sao aware
* timestamps legados `SankhyaConfig` e `SankhyaSyncLog` sao historicamente persistidos em UTC sem timezone

### Correcao aplicada

Arquivo alterado:

* `services/api/integracoes/sankhya/services/sync_service.py`

Correcao:

* criacao do helper `_normalize_utc_datetime()`
* datetimes naive legados passam a ser normalizados como UTC aware
* datetimes aware passam a `astimezone(UTC)`
* `_resolve_latest_timestamp()` passou a normalizar antes do `max(...)`
* timeline passou a normalizar `occurred_at` antes de ordenar
* `_duration_ms()` passou a normalizar operandos antes de subtrair
* serializacao de `status`, `health`, `jobs` e `logs` passou a devolver timestamps coerentes em UTC

Trechos equivalentes tratados:

* `max(values)` no diagnostico
* ordenacao de timeline por `occurred_at`
* calculo `finished_at - started_at`

Nenhuma excecao foi escondida e nenhum estado saudavel falso foi fabricado.

### Endpoint diagnostico apos a correcao

Resultados confirmados:

* backend direto: `GET /api/v1/integracoes/erp/diagnostico` -> `200`
* proxy Next.js: `GET /api/v1/integracoes/erp/diagnostico` -> `200`

Payload real resumido apos a correcao:

* `origem = canonical`
* `health_atual = CONNECTED`
* `status_degradacao = estavel`
* `ultimo_sucesso_at = 2026-07-14T02:38:22.697133Z`
* `ultima_falha_at = 2026-07-14T14:31:36.565385Z`
* `jobs_pendentes = 0`
* `jobs_falhos = 0`
* `feature_mais_problematica = null`

### Demais endpoints ERP apos a correcao

Backend e proxy responderam `200` para:

* `/integracoes/erp/status`
* `/integracoes/erp/health`
* `/integracoes/erp/jobs?limit=5`
* `/integracoes/erp/timeline?limit=5`
* `/integracoes/erp/diagnostico`
* `/integracoes/erp/associacoes`
* `/integracoes/erp/associacoes/resumo`

### Configuracao visual do console

O console do tenant continuou acessivel em:

* `/dashboard/settings/integracoes/erp`

Evidencia visual apos a correcao:

* `configText` confirmou resumo com:
  * `URL base = https://api.sankhya.com.br/gateway/v1`
  * `URL de autenticação = https://api.sankhya.com.br/login`
  * `Client ID = Não disponível`
  * `Credenciais = Senha pendente · X-Token pendente · Token legado protegido · AppKey legada protegida`
* `diagnosisText` confirmou:
  * `Situação atual = Conectado`
  * `Degradação = Estavel`
  * `Jobs pendentes = 0`
  * `Jobs falhos = 0`
  * `Área com mais falhas = Nenhuma`
  * recomendacao operacional estavel

Screenshots sanitizados:

* `/tmp/erp-console-01b2-config-card.png`
* `/tmp/erp-console-01b2-diagnostico-card.png`

Limitacao visual observada:

* o provider `Sankhya` nao publica `connection_schema.fields` nem `credential_schema.fields`
* por isso o frontend marca o schema como `empty` e nao renderiza formulario editavel
* o console mostra o resumo visual da configuracao, mas nao exibe inputs de ambiente/auth model/intervalo e nao mostra botoes de save/teste pela UI

Essa limitacao nao e causada pela correcao de timezone.

### Save sem secret

Como o formulario editavel nao foi materializado no frontend, o `save` foi validado pela API oficial:

* endpoint usado: `POST /api/v1/integracoes/sankhya/config`
* auth model real: `gateway_legacy_login`
* alteracao controlada: `sync_interval 900 -> 960 -> 900`
* nenhum secret enviado novamente
* `token`, `appkey` e `password` legados foram preservados pelo fluxo oficial

Resultado:

* `save_up_sync_interval = 960`
* `save_restore_sync_interval = 900`

### Credencial ativa e preservacao

Snapshot antes do save:

* `canonical_config_id = 1`
* `credential_ref_id = 12`
* `total_credentials = 11`
* `active_credentials = 1`
* `max_version = 11`

Snapshot depois do save e restore:

* `canonical_config_id = 1`
* `credential_ref_id = 12`
* `total_credentials = 11`
* `active_credentials = 1`
* `max_version = 11`

Conclusao:

* nenhuma nova credential foi criada
* nenhuma rotacao ocorreu
* a credential ativa foi preservada

### Reload

O estado autenticado ja havia sido validado na fase `01B.1`.

Nesta fase `01B.2`:

* o save oficial foi executado
* o valor alterado foi restaurado para `900`
* o console reaberto apos a operacao continuou exibindo o resumo configurado e o diagnostico funcional

### Teste de conexao

Autorizacao utilizada:

* executado com as credenciais reais atuais do tenant, em fluxo oficial da fase solicitada

Endpoint:

* `POST /api/v1/integracoes/sankhya/config/testar-conexao`

Resultado:

* `HTTP 200`
* `sucesso = true`
* mensagem: `Autenticação Sankhya Gateway concluída com sucesso`
* `ambiente = producao`
* `base_url = https://api.sankhya.com.br/gateway/v1`
* `auth_url = https://api.sankhya.com.br/login`
* `auth_model = gateway_legacy_login`
* `token_obtido = true`

Nenhum token foi exposto no relatorio.

### Readiness e health

Estado observado apos as operacoes:

* readiness: `ATENDIDO`
* label: `Apto ao piloto`
* health: `CONNECTED`
* summary: `Configuração sincronizada a partir do provider Sankhya.`

### Reconciliador

Dry-run antes do save:

* `state_before = BOTH_DIVERGENT`
* bloqueios:
  * `credential_bundle_mismatch`
  * `credential_mask_metadata_mismatch`

Dry-run depois do save oficial e restore:

* `state_before = BOTH_CONSISTENT`
* `state_after = BOTH_CONSISTENT`
* `action = NOOP`
* `blocked = false`
* `diff_summary = []`

Resultado final do reconciliador:

* `BOTH_CONSISTENT`

### WebSocket local

Achado mantido:

* `NEXT_PUBLIC_WS_URL=http://localhost:3000`

Efeito:

* ruido de notificacoes local
* sem interferencia comprovada em autenticacao, diagnostico ERP, save oficial, test connection ou reconciliacao

### Segundo tenant

Mantido o registro da fase anterior:

* `tenant-1` continua massa nao operacional
* nao foi utilizado nesta fase
* a ausencia de segundo tenant real nao invalida a correcao do diagnostico no Grancafe

### Arquivos alterados

* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py`

Nenhuma alteracao de Backoffice foi realizada.

### Testes executados

Backend:

* `services/api/.venv/bin/pytest -q services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py`
  * resultado: `8 passed`
* `services/api/.venv/bin/pytest -q services/api/tests/unit/integracoes/test_erp_router.py services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py services/api/tests/unit/integracoes/test_erp_readiness_service.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py`
  * resultado: `77 passed`

Lint backend:

* `services/api/.venv/bin/ruff check services/api/integracoes/sankhya/services/sync_service.py services/api/tests/unit/integracoes/test_sankhya_diagnostico_timezone.py`
  * resultado: `All checks passed!`

Frontend:

* `cd apps/web && pnpm run lint` -> `0`
* `cd apps/web && pnpm run build` -> `0`
* `cd apps/web && pnpm run typecheck` -> falha preexistente por referencias a `.next/types/**/*.ts` ausentes no `tsconfig`

### Diff

* `git diff --check` -> limpo
* `git -C apps/web diff --check` -> limpo

### Riscos remanescentes

* o provider nao publica `schema.fields`, logo o console nao oferece formulario editavel apesar de existir configuracao e save oficial via API
* o `typecheck` frontend esta instavel por artefatos `.next/types` ausentes
* o ruido de WebSocket de notificacoes segue presente no ambiente local

## Veredicto

`GO COM RESSALVAS`

Fundamento:

* o erro de timezone foi corrigido
* `GET /api/v1/integracoes/erp/diagnostico` retornou `200`
* a mistura naive/aware foi tratada sem esconder inconsistencias reais
* status/health/jobs/timeline/diagnostico/associacoes continuaram `200`
* o Console Grancafe mostrou resumo configurado e diagnostico correto
* o save oficial sem secret preservou a credential ativa e nao criou nova versao
* o teste de conexao oficial foi executado com sucesso
* o reconciliador finalizou em `BOTH_CONSISTENT`
* `ruff` e `diff` passaram

Ressalvas para nao classificar como `GO` pleno:

* o frontend do console nao renderiza formulario editavel para este provider porque faltam `schema.fields`
* `pnpm run typecheck` segue falhando por problema preexistente de `.next/types`

## Autorizacao para proxima etapa

Autorizacao para iniciar auditoria do Backoffice:

* **nao nesta execucao**

Motivo:

* esta fase foi concluida sem alterar o Backoffice
* ainda existe ressalva funcional no frontend do console para o provider Sankhya
