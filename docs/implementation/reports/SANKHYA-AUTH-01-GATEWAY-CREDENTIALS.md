# SANKHYA-AUTH-01 - Gateway Credentials

## Auditoria inicial

### Escopo auditado
- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/README.md`
- `services/api/core/config.py`
- `services/api/migrations/versions/fase3_sankhya.py`
- `services/api/tests/unit/integracoes/*sankhya*`

### Classificação encontrada
- Modelo legado `ws_url` / `username` / `password`: EXISTE E PARCIALMENTE ATENDE
- Suporte atual a `client_id` / `client_secret` / `x_token` / `gateway/base_url` / `/authenticate`: NÃO EXISTE
- Configurações de ambiente Sankhya em `core/config.py`: NÃO EXISTE
- `.env.example` no backend: NÃO EXISTE
- Documentação com contrato Gateway: NÃO EXISTE

## Decisão técnica

- O modelo legada foi preservado somente como compatibilidade histórica.
- O caminho padrão passou a ser Gateway Sankhya.
- A configuração agora aceita e persiste:
  - `sankhya_environment`
  - `sankhya_api_base_url`
  - `sankhya_auth_url`
  - `sankhya_client_id`
  - `sankhya_client_secret`
  - `sankhya_x_token`
- Os campos legados continuam disponíveis apenas para leitura/compatibilidade:
  - `ws_url`
  - `username`
  - `password`

## Implementação entregue

### Persistência
- `SankhyaConfig` ganhou colunas Gateway.
- Colunas legadas foram mantidas como compatibilidade e tornadas opcionais no modelo.
- Nova migração criada para materializar o contrato:
  - `services/api/migrations/versions/20260704_sankhya_gateway_auth.py`

### Configuração e contratos
- `services/api/core/config.py` recebeu as variáveis Sankhya.
- Criado `services/api/.env.example` com os parâmetros Gateway.
- `services/api/integracoes/sankhya/schemas/__init__.py` passou a expor o contrato Gateway primeiro.
- `services/api/integracoes/sankhya/README.md` foi atualizado para o fluxo de autenticação atual.

### Autenticação
- Criado `services/api/integracoes/sankhya/services/auth_service.py`.
- O serviço:
  - valida configuração completa
  - autentica em `/authenticate`
  - usa `X-Token`
  - envia `client_id` e `client_secret`
  - mantém cache defensivo de `access_token`
  - mascara segredos em diagnóstico

### Integração com o fluxo existente
- `SankhyaWSClient` passou a usar Gateway quando a configuração estiver completa.
- O fluxo legado permanece apenas como fallback compatível.
- `SankhyaCanonicalAdapter` agora materializa:
  - `connection_payload` com contrato Gateway
  - `credenciais` com metadados mascarados
  - `IntegrationCredential` com bundle criptografado quando o Gateway está ativo

## Compatibilidade preservada

- Não houve implementação de sync de dados nova.
- Não houve alteração de jobs.
- Não houve mudança de backend funcional fora do contrato de autenticação/configuração.
- Segredos não são logados.
- O legado não passou a ser o fluxo padrão.

## Validação executada

### Executado com sucesso
- `cd services/api && .venv/bin/python -m pytest tests/unit/integracoes/test_sankhya_gateway_auth_service.py tests/unit/integracoes/test_sankhya_governed_integration.py tests/unit/integracoes/test_sankhya_canonical_adapter.py tests/unit/integracoes/test_integrations_architecture_guardrails.py -q`
  - Resultado: `44 passed`
- `cd services/api && .venv/bin/alembic heads`
  - Resultado: `20260704_sankhya_gateway_auth (head)`
- `git diff --check`
  - Resultado: sem diferenças de whitespace/formatting

### Validação ampla com bloqueios pré-existentes
- `cd services/api && .venv/bin/python -m pytest tests/unit -q`
  - Bloqueado por erro de coleta pré-existente em testes com basename duplicado:
    - `tests/unit/certificacoes_esg/test_router.py`
    - `tests/unit/certificacoes_esg/test_service.py`
    - `tests/unit/propriedade_imovel/test_service.py`
- `cd services/api && .venv/bin/python -m pytest tests/unit/integracoes -q`
  - Encontrou falhas pré-existentes fora do Sankhya em `tests/unit/integracoes/test_openweather_domain.py`
  - Erro observado: tabela `unidades_produtivas` ausente no setup do teste

## Pendências futuras

- Se houver necessidade de migração gradual do legado para Gateway, criar rotina de backfill/normalização.
- Se o endpoint `/authenticate` exigir contrato diferente de JSON/Form, ajustar apenas o `auth_service` sem tocar no restante.
- O bloqueio de coleta em `tests/unit` precisa ser tratado separadamente para permitir suíte global verde.
