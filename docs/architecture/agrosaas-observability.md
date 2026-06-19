# AGROSAAS OBSERVABILITY

Este documento rege as diretrizes de observabilidade, registro de logs e detecção de incidentes do AgroSaaS, baseadas na camada de Middlewares do `main.py`.

## LOGS

A plataforma utiliza o **Loguru** como engine primária no Backend.
- **Formato**: Estruturado (`serialize=True`) nativamente compatível com ingestão JSON (Grafana Loki, Datadog, ELK).
- **Dados Padrão**: Timestamp (Z), Level, Name, Function, Line, Message.
- **Registro Local**: Erros não tratados (Exception global) gravam fallback em arquivo físico temporário `error_debug.log`.

## MÉTRICAS

- **Latência e Perfomance**: Coletadas no `ObservabilityMiddleware` a cada request.
- **Healthchecks**: `/health`, `/health/ready` e `/health/live` avaliam continuamente banco de dados e disponibilidade do processo.

## TRACING

- **Request ID**: Implementado via header `X-Request-ID`. O `Loguru` injeta o Request ID via bind (`logger.bind(request_id=...)`) amarrando a execução completa de um erro.

## AUDITORIA

- **Segurança Global**: Exceções severas como `TenantViolationError` acionam o `audit_service.write_audit_log` para persistência assíncrona da violação de RLS (ip, rota, payload_before/after) sob flag `SECURITY_INCIDENT`.

## ALERTAS

- NÃO IDENTIFICADO (Ferramentas externas como PagerDuty ou Sentry não explícitas no `pyproject.toml`, devendo ser amarradas ao parse de logs do Loguru em nuvem).

---

## CHECKLIST DE INCIDENTES & DETECÇÃO (RUNBOOKS)

### Como detectar falha de sincronização PWA?
- Monitorar a fila de outbox presa no `Dexie.js` no client (via logs internos ou estado do Zustand).
- Analisar picos de HTTP 500 no endpoint `/api/v1/sync` e falhas de desserialização (Schema ValidationError).

### Como detectar falha no Celery?
- Monitorar o worker e o broker (`Redis`). Trabalhos agendados que expiram ou geram *Retry Limit Exceeded* aparecerão no log padrão do worker.

### Como detectar falha no Redis?
- Sessões expirarão precocemente (heartbeat do middleware falha em gravar estado ou falha de timeout assíncrono). Logs reportarão `ConnectionError` do broker.

### Como detectar falha no PostgreSQL?
- O endpoint `/health/ready` retornará `status: degraded` e HTTP 503.
- Logs do asyncpg exibirão `ConnectionRefusedError` no pool de conexões do SQLAlchemy.

### Como detectar falha de RLS?
- Log severo classificado como `CRITICAL: SECURITY_INCIDENT - TENANT_VIOLATION`. Indica tentativa de query cross-tenant sem permissão.

### Como detectar falha no Login?
- Alta taxa de HTTP 401 no `auth.router`. Aumento nos logs de tentativa inválida via `python-jose` exceptions.

### Como detectar falha nas Integrações (IoT/Stripe/Asaas)?
- Logs dos middlewares de webhooks falharão na validação de assinatura (ex: `stripe_webhooks`).
- Erros classificados como `BusinessRuleError` ou falha de rede externa (`httpx.TimeoutException`).
