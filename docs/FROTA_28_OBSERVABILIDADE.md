# Frota-28: Observabilidade Mínima e Monitoramento

## 1. Logging Estruturado
Implementado via `ObservabilityMiddleware` em `core/observability.py`.

### Dados Capturados:
- **Request-ID:** Identificador único da requisição (Header `X-Request-ID`).
- **Endpoint:** Método HTTP e Caminho.
- **Status:** Código de retorno HTTP.
- **Duração:** Tempo de processamento em segundos (Header `X-Process-Time`).
- **Tenant ID:** Identificação do cliente (extraído do JWT via `TenantRLSMiddleware`).
- **Timestamp:** ISO format UTC.

### Exemplo de Log:
`REQ | GET /api/v1/frota/dashboard | 200 | 0.3915s | Tenant: 678122a2-700d-4425-a779-043395c2246a`

## 2. Alertas em Produção (Logs Críticos)
O sistema emite alertas prefixados nos logs para captura por ferramentas de agregação (Loki/CloudWatch):

- **ERRO 500:** `ALERT: SERVER_ERROR | Path: /... | RequestID: ...`
- **LENTIDÃO (> 1s):** `ALERT: SLOW_REQUEST | Path: /... | Duration: 1.25s | RequestID: ...`

## 3. Healthcheck Avançado
Endpoint: `GET /health`

### Funcionalidades:
- Verifica status geral da aplicação.
- Testa conectividade com o banco de dados (Query: `SELECT 1`).
- Reporta versão e status degradado se o banco estiver inacessível.

## 4. Como Monitorar
1.  **Logs em tempo real:** `tail -f error_debug.log` (ou log do sistema).
2.  **Identificação de Gargalos:** Filtrar por `SLOW_REQUEST` para encontrar queries pesadas que precisam de otimização.
3.  **Rastreamento:** Utilizar o `X-Request-ID` retornado no frontend para correlacionar erros no backend.
