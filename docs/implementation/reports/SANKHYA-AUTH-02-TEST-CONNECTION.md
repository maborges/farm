# SANKHYA-AUTH-02 - Test Connection

Data: 2026-07-05

## Objetivo

Validar o fluxo real de autenticação do Sankhya Gateway com um teste controlado de conexão, sem sincronizar dados de negócio e sem persistir dados externos.

## Auditoria

- Existe endpoint Sankhya no backend em `POST /api/v1/integracoes/sankhya/config/testar-conexao`.
- Não encontrei CLI nem doctor dedicado para Sankhya no repositório.
- O módulo já possuía padrões de diagnóstico em outras integrações, especialmente OpenWeather, que foram reaproveitados como referência estrutural.
- O fluxo anterior de `testar_conexao` persistia `ultimo_teste`/`teste_status` e usava o cliente WS legado. Isso foi substituído pelo teste controlado de autenticação Gateway.

## O que foi implementado

- A resposta de teste de conexão Sankhya passou a incluir:
  - `ambiente`
  - `base_url`
  - `auth_url`
  - `client_id_mask`
  - `x_token_mask`
  - `token_obtido`
  - `token_expires_at`
  - `auth_model`
  - `sucesso`
  - `mensagem`
- O `SankhyaGatewayAuthService` ganhou um teste de conexão específico para Gateway.
- A autenticação chama o endpoint `/authenticate` com payload controlado e headers sanitizados.
- O teste de conexão não grava dados externos e não persiste estado do teste em banco.
- O endpoint existente em `/config/testar-conexao` foi mantido, mas agora retorna o diagnóstico sanitizado.

## Arquivos principais

- [`services/api/integracoes/sankhya/services/auth_service.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py)
- [`services/api/integracoes/sankhya/services/sync_service.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [`services/api/integracoes/sankhya/schemas/__init__.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/schemas/__init__.py)
- [`services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py)

## Validação

Executado em `services/api`:

- ` .venv/bin/python -m pytest tests/unit/integracoes/*sankhya* -q `
- ` .venv/bin/alembic heads `
- ` git diff --check `

Resultado:

- `34 passed`
- `20260704_sankhya_gateway_auth (head)`
- `git diff --check` sem erros

## Observações

- Não foram criados fluxos de sync de clientes, produtos, financeiro, estoque ou notas.
- Não foi adicionada persistência de token ou resultado externo do teste.
