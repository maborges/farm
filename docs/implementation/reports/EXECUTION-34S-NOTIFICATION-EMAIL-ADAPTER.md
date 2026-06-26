# EXECUTION-34S - Notification Email Adapter

## Objetivo

Implementar o primeiro adapter real de notificações do AgroSaaS, usando SMTP configurável por ambiente e acionado exclusivamente via `NotificationDispatcher`.

## Escopo

- criar `EmailNotificationAdapter`
- criar configuração SMTP defensiva
- registrar o adapter no registry existente
- preservar `LOG` e `NOOP`
- manter o dispatcher como único ponto de acionamento
- documentar operação e troubleshooting

## Arquivos criados

- `services/api/notifications/email_adapter.py`
- `services/api/notifications/notification_config.py`
- `services/api/tests/unit/notifications/test_email_adapter.py`
- `services/api/tests/unit/notifications/test_notification_dispatcher_email.py`
- `docs/operations/notifications-email.md`
- `docs/implementation/reports/EXECUTION-34S-NOTIFICATION-EMAIL-ADAPTER.md`

## Arquivos alterados

- `services/api/notifications/adapters.py`
- `services/api/notifications/__init__.py`
- `services/api/notifications/dispatcher.py`

## Decisões Técnicas

- O adapter lê configuração do processo em tempo de execução.
- `NOTIFICATIONS_EMAIL_ENABLED=false` gera `SKIPPED` e não abre SMTP.
- Configuração incompleta gera falha controlada no resultado do adapter.
- O template é texto puro.
- O dispatcher foi ajustado para continuar com outros canais quando um canal falha.
- `LOG` e `NOOP` continuam operacionais.
- O canal `EMAIL` é registrado de forma segura no carregamento padrão do módulo.

## Validações Executadas

- testes unitários do pacote `notifications`
- lint com `ruff`
- checagem de diff com `git diff --check`

## Limitações

- Não há envio real em testes.
- Não há persistência de preferências por tenant.
- Não há HTML.
- Não há retry por canal.
- Não há histórico persistente de entrega.

## Próximos Passos

- Persistir políticas e preferências por tenant.
- Criar adapter real de Push.
- Criar abstraction layer para WhatsApp.
- Evoluir retry e observabilidade por canal.
