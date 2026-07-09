# SANKHYA-AUTH-03 - Contrato de autenticação Sankhya via Gateway

## Resumo executivo

O contrato de autenticação do provider Sankhya foi explicitado para suportar dois modos oficiais de Gateway:

* `gateway_oauth_client_credentials`, com autenticação em `/authenticate` usando `client_id`, `client_secret` e `X-Token`;
* `gateway_legacy_login`, com autenticação em `/login` usando `token`, `appkey`, `username` e `password`.

O fluxo OAuth atual foi preservado. A compatibilidade histórica com login WS legado permaneceu apenas como fallback técnico para configurações antigas, sem substituir o contrato canônico do Gateway.

Não houve exposição de credenciais em frontend, logs, diagnóstico ou respostas de API.

## Arquivos auditados

* `services/api/integracoes/sankhya/services/auth_service.py`
* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/integracoes/sankhya/schemas/__init__.py`
* `services/api/integracoes/sankhya/routers/__init__.py`
* `services/api/integracoes/sankhya/models/__init__.py`
* `apps/web/src/components/integracoes/sankhya-console.tsx`
* `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
* `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`

## Arquivos alterados

* `services/api/integracoes/sankhya/services/auth_service.py`
* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/integracoes/sankhya/schemas/__init__.py`
* `services/api/integracoes/sankhya/routers/__init__.py`
* `services/api/integracoes/sankhya/models/__init__.py`
* `apps/web/src/components/integracoes/sankhya-console.tsx`
* `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
* `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`

## O que foi corrigido

### 1. Auth Service

* o serviço passou a distinguir explicitamente:
  * `gateway_oauth_client_credentials`
  * `gateway_legacy_login`
  * `legacy_ws_basic_auth` como compatibilidade histórica
* a autenticação OAuth continua usando `/authenticate`;
* o login legado via Gateway agora usa `/login` com `token`, `appkey`, `username` e `password`;
* o mascaramento foi mantido para `client_secret`, `x_token`, `token`, `appkey` e `password`;
* `test_connection()` passou a refletir o modelo de autenticação ativo.

### 2. Sync Service

* a configuração passou a aceitar e persistir `sankhya_token` e `sankhya_appkey`;
* a inferência de modelo de auth foi ajustada para não confundir login legado com OAuth apenas por causa de `auth_url`;
* a serialização do console agora expõe flags e máscaras de `token` e `appkey`;
* o updater preserva o modelo atual quando o tenant apenas atualiza campos auxiliares;
* o router foi alinhado para repassar os novos campos.

### 3. Provider Contract

* o `provider_definition` do Sankhya passou a declarar explicitamente os modelos de autenticação suportados;
* o contrato do provider passou a documentar o login legado do Gateway;
* `connection_schema` e `credential_schema` passaram a contemplar os novos campos de compatibilidade.

### 4. Console ERP

* a tela passou a aceitar e exibir `token` e `appkey` do login legado;
* o texto de autenticação agora diferencia OAuth Gateway, login legado Gateway e compatibilidade histórica;
* as máscaras de credencial continuam protegidas.

### 5. Testes

* foram adicionados testes para login legado via Gateway;
* os testes de contrato foram atualizados para os novos rótulos explícitos;
* os testes de sanitização de credenciais foram mantidos.

## Regras confirmadas

* OAuth atual não foi removido;
* o tenant não passa a depender apenas de `client_id`, `client_secret` e `X-Token`;
* `token`, `appkey`, `username` e `password` são contemplados no login legado do Gateway;
* segredos não são expostos em payloads de resposta;
* o console continua genérico, com Sankhya como provider atual.

## Validações executadas

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py -q
```

Resultado: `38 passed`

```bash
npm run typecheck
```

Resultado: aprovado.

```bash
git diff --check
```

Resultado: aprovado.

## Lacunas remanescentes

* o login WS legado continua suportado apenas como compatibilidade técnica para base histórica;
* a configuração de login legado do Gateway ainda depende de contrato correto no provedor externo Sankhya;
* eventuais diferenças entre ambientes do Gateway continuam fora do alcance desta execução.

## Veredicto

**APROVADO**

O contrato de autenticação foi explicitado, o fallback legado foi preservado sem ambiguidade arquitetural e a suíte afetada ficou verde.
