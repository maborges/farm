# OPS-INTELLIGENCE-10B - Risco de Spam, Dedupe e Policy

## Auditoria focada

Arquivos revisados:

- `services/api/recommendations/notification_bridge.py`
- `services/api/recommendations/engine.py`
- `services/api/notifications/dispatcher.py`
- `services/api/notifications/notification_policy.py`
- `services/api/notifications/notification_policy_service.py`
- `services/api/notifications/notification_deduplication.py`
- `services/api/tests/unit/recommendations/test_recommendation_notification_bridge.py`
- `services/api/tests/unit/recommendations/test_recommendations_registry_engine.py`

## Confirmações

- `HIGH` e `URGENT` são os únicos níveis elegíveis para a ponte.
- O bridge só chama o dispatcher quando a recommendation foi recém-criada.
- Update de recommendation não dispara nova notificação.
- `NotificationPolicyService` continua sendo a porta de entrada para policy, dedupe e silence window.
- Falha de policy, dedupe ou silêncio não quebra o `RecommendationEngine`.
- Não há participação de `Alert Engine` no fluxo.

## Avaliação de risco de spam

### Evitado

- Repetição por update:
  - O engine só chama o bridge quando `existing is None`.
  - O teste de update confirma que `recommendations_updated` não produz nova notificação.
- Repetição por dedupe:
  - O `NotificationPolicyService` aplica `NotificationDeduplicationStore.mark_if_new(tenant_id, dedupe_key)`.
  - O `dedupe_key` da ponte é estável: `recommendation:{recommendation.dedupe_key}`.
- Repetição por silêncio:
  - O dispatcher respeita a `NotificationSilenceWindow`.
  - `HIGH` e `CRITICAL` não são suprimidos por padrão, o que é coerente com o uso de alerta operacional crítico.

### Residual

- O dedupe atual é em memória. Após restart do processo, a memória é perdida e a primeira notificação pode ser reenviada se a recommendation ainda for elegível.
- Se houver necessidade de dedupe persistente entre processos/boots, isso deve ser tratado em etapa futura sem mudar a ponte atual.

## Ajuste feito nesta revisão

- Adicionei teste explícito garantindo que update não chama o bridge nem incrementa notificação indevida.

## Validação executada

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -q
.venv/bin/python -m pytest tests/unit/notifications -q
git diff --check
```

Resultado:

- `tests/unit/recommendations`: 38 passed
- `tests/unit/notifications`: 29 passed
- `git diff --check`: limpo

## Conclusão

A ponte `recommendations -> notifications` permanece controlada, sem spam por update dentro do processo, sem acoplamento com Alert Engine e sem quebrar o engine em caso de bloqueio por policy ou dedupe.
