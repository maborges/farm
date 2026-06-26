# Notificações por Email

## Visão Geral

O canal de email do AgroSaaS é acionado exclusivamente pelo `NotificationDispatcher`, depois da avaliação de `Notification Policies`.

Nesta fase:

- somente o canal `EMAIL` usa SMTP real
- `LOG` e `NOOP` continuam como adapters locais
- nenhum envio real acontece em testes

## Variáveis de Ambiente

- `NOTIFICATIONS_EMAIL_ENABLED`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `SMTP_USE_TLS`
- `SMTP_TIMEOUT_SECONDS`

## Exemplo Local

```env
NOTIFICATIONS_EMAIL_ENABLED=true
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USERNAME=dev-user
SMTP_PASSWORD=dev-pass
SMTP_FROM_EMAIL=noreply@agrosaas.local
SMTP_FROM_NAME=AgroSaaS
SMTP_USE_TLS=true
SMTP_TIMEOUT_SECONDS=10
```

## Exemplo Produção

```env
NOTIFICATIONS_EMAIL_ENABLED=true
SMTP_HOST=smtp.seudominio.com
SMTP_PORT=587
SMTP_USERNAME=service-account
SMTP_PASSWORD=senha-segura
SMTP_FROM_EMAIL=notificacoes@seudominio.com
SMTP_FROM_NAME=AgroSaaS
SMTP_USE_TLS=true
SMTP_TIMEOUT_SECONDS=15
```

## Comportamento Desabilitado

Quando `NOTIFICATIONS_EMAIL_ENABLED=false`:

- o adapter não abre conexão SMTP
- a entrega é marcada como `SKIPPED`
- o dispatcher continua processando os demais canais

## Troubleshooting

- Verifique se `SMTP_HOST` está preenchido quando o email estiver habilitado.
- Confirme `SMTP_PORT` maior que zero.
- Confirme se `SMTP_FROM_EMAIL` está configurado.
- Se `SMTP_USERNAME` e `SMTP_PASSWORD` existirem, o adapter tenta autenticação.
- Se `SMTP_USE_TLS=true`, o adapter chama `STARTTLS`.
- Se o evento não tiver destinatários resolvidos, a entrega é `SKIPPED`.

## Riscos

- A deduplicação continua em memória e vale apenas no processo atual.
- Não existe retry por canal nesta fase.
- Não há persistência de histórico de entrega.
- Não há template HTML.

## Próximos Passos

- Persistir preferências e políticas por tenant.
- Introduzir retry por canal.
- Criar adapters reais para Push e WhatsApp.
- Evoluir templates para HTML opcional.
