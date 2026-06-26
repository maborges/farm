# EXECUTION-34R - Notification Policies

## Objetivo

Criar a fundação de `Notification Policies` para controlar elegibilidade de envio, prioridade, canais, destinatários, deduplicação e janela de silêncio antes da entrega pelos adapters existentes.

## Arquitetura

### Fluxo operacional

`NotificationEvent` -> `NotificationDispatcher` -> `NotificationPolicyService` -> `NotificationPolicyRegistry` -> `NotificationPolicy` -> `NotificationPolicyResult` -> `NotificationAdapterRegistry` -> adapters `LOG` / `NOOP`

### Decisões técnicas

- A camada foi implementada em memória, sem migration e sem persistência nova.
- O `NotificationDispatcher` continua sendo o ponto único de decisão antes dos adapters.
- O `Alert Engine` não foi alterado.
- O contrato de `NotificationEvent` foi preservado.
- A deduplicação é por tenant, para evitar vazamento cross-tenant.
- A janela de silêncio é configurável em memória e permite `HIGH`/`CRITICAL` quando habilitado.
- O canal `NOOP` foi adicionado ao enum e ao `NoopNotificationAdapter` para manter compatibilidade conceitual com o contrato pedido.

## Arquivos criados

- `services/api/notifications/notification_policy.py`
- `services/api/notifications/notification_policy_service.py`
- `services/api/notifications/notification_policy_registry.py`
- `services/api/notifications/notification_preferences.py`
- `services/api/notifications/notification_deduplication.py`
- `services/api/notifications/notification_silence_window.py`
- `services/api/tests/unit/notifications/test_notification_policies.py`
- `docs/implementation/reports/EXECUTION-34R-NOTIFICATION-POLICIES.md`

## Arquivos alterados

- `services/api/notifications/base.py`
- `services/api/notifications/adapters.py`
- `services/api/notifications/dispatcher.py`
- `services/api/notifications/__init__.py`
- `services/api/tests/unit/notifications/test_notification_dispatcher.py`

## Testes

### Verificações executadas

- `pytest services/api/tests/unit/notifications -q`
- `ruff check services/api/notifications services/api/tests/unit/notifications`

### Resultado

- `pytest`: 20 passed
- `ruff`: all checks passed

## Limitações conhecidas

- A validação global de `mypy` no repositório ainda encontra erros legados fora do escopo desta tarefa, especialmente em `core/` e `events/`.
- A deduplicação segue em memória e só vale no processo atual.
- A janela de silêncio não depende de armazenamento persistente nem de timezone por tenant.
- Não há envio real para Email, Push ou WhatsApp nesta etapa.

## Próximos passos para 34S

- Persistir policies e preferências por tenant.
- Introduzir configuração de janelas de silêncio por perfil/tenant.
- Expandir a resolução de destinatários para perfis, grupos e regras explícitas.
- Preparar adapters reais para Email, Push e WhatsApp.
- Cobrir os fluxos com testes de integração do dispatcher em cenários multi-tenant mais complexos.
