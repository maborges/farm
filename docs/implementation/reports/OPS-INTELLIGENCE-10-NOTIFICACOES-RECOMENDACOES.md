# OPS-INTELLIGENCE-10 - Notificações de Recomendações

## Auditoria inicial

### O que já existia

- `services/api/notifications/dispatcher.py`: existe e atende o papel de orquestração de entrega.
- `services/api/notifications/notification_policy.py`: existe e atende o contrato de policy.
- `services/api/notifications/notification_policy_service.py`: existe e atende policy, dedupe e silêncio.
- `services/api/notifications/notification_deduplication.py`: existe e atende deduplicação em memória.
- `services/api/notifications/notification_preferences.py`: existe e atende preferências via metadata.
- `services/api/notifications/notification_silence_window.py`: existe e atende janela de silêncio.
- `services/api/recommendations/`: existe o engine canônico, mas sem qualquer ponte para notificações.
- `services/api/events/`: existe o barramento de eventos e subscribers, mas sem integração de recommendations para notifications.
- `services/api/alert_engine/`: existe e atende seu próprio domínio, mas não é parte deste fluxo.

### O que não existia

- Ponte entre `RecommendationResult` persistido e `NotificationDispatcher`.
- Policy específica para notificações de recomendações.
- Gatilho no engine de recommendations para notificar apenas itens elegíveis.

### Classificação

- `notifications/dispatcher.py`: EXISTE E ATENDE
- `notifications/policy*`: EXISTE E ATENDE
- `notifications/preferences*`: EXISTE E ATENDE
- `notifications/deduplication`: EXISTE E ATENDE
- integração recommendations -> notifications: NÃO EXISTE
- recommendation-specific notification policy/bridge: NÃO EXISTE

## Integração criada

### Arquivos alterados

- `services/api/recommendations/notification_bridge.py`
- `services/api/recommendations/engine.py`
- `services/api/tests/unit/recommendations/test_recommendation_notification_bridge.py`
- `services/api/tests/unit/recommendations/test_recommendations_registry_engine.py`

### Bridge implementado

- Criei `RecommendationNotificationBridge` como ponto opcional de tradução de recommendation persistida em `NotificationEvent`.
- Criei `RecommendationOperationalNotificationPolicy` com `event_type = "recommendations.operational"`.
- O bridge registra a policy no `NotificationPolicyRegistry` existente.
- O bridge usa `NotificationDispatcher` existente, sem criar motor novo.

### Critérios de elegibilidade

A notificação só é tentada quando:

- a recommendation acabou de ser criada pelo engine;
- o status está ativo/criado;
- a prioridade é `HIGH` ou `URGENT`;
- não está expirada;
- existe `tenant_id`;
- existe `dedupe_key` estável.

### Dedupe e anti-spam

- O `dedupe_key` de notificação foi fixado como `recommendation:{recommendation.dedupe_key}`.
- O fluxo respeita `NotificationPolicyService`, `NotificationDeduplicationStore` e `NotificationSilenceWindow`.
- Se a policy bloquear, o dispatcher não chama adapter.
- Se a dedupe indicar repetição, o dispatcher suprime a entrega.

### Canais

- O bridge usa metadata `notification_preferences` para o policy resolver canais e dedupe.
- Sem destinatários conhecidos, o fallback fica em `LOG`.
- Se houver destinatários em `context.notification_recipients`, o bridge permite `EMAIL` e `LOG`.

## Restrições preservadas

- Não alterei Campo PWA.
- Não alterei frontend web.
- Não criei novo Notification Engine.
- Não criei novo provider.
- Não chamei Alert Engine.
- Não transformei recommendation em alerta.
- Não executei mutação operacional.
- Não alterei lifecycle para `accepted` ou `executed`.
- Não adicionei tabela nova nem migration nova.

## Lifecycle

- Lifecycle automático de recommendation não foi alterado.
- O bridge é somente comunicação.
- Se o dispatcher falhar, o engine continua e a recommendation segue persistida normalmente.

## Validação executada

Comandos executados:

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -q
.venv/bin/python -m pytest tests/unit/notifications -q
.venv/bin/alembic heads
git diff --check
```

Resultado:

- `tests/unit/recommendations`: 37 passed
- `tests/unit/notifications`: 29 passed
- `alembic heads`: `20260703_ops_intelligence_02_recommendations_foundation (head)`
- `git diff --check`: limpo

## Pendências futuras

- Se surgir um canal oficial de inbox no Campo ou no web dashboard, o bridge pode passar a usar recipientes reais.
- Se houver preferência persistida por tenant/unidade, o bridge pode ler isso do contexto sem mudar o contrato atual.
- Se aparecer um store persistente de dedupe para notificações, ele pode substituir o dedupe em memória sem alterar a bridge.
