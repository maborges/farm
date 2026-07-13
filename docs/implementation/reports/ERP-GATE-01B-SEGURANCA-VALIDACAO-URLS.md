# ERP-GATE-01B — Segurança e Validação de URLs ERP (SSRF Protection)

## 1. Resumo

Esta etapa resolveu o risco de SSRF identificado na auditoria `ERP-GATE-01`.
Implementamos a **Política A (Internet pública apenas)** com um validador central robusto que intercepta e valida as configurações de ERP antes de sua persistência e antes de qualquer chamada runtime. 
Com a abertura da configuração baseada em _schemas_ gerada em `ERP-GATE-01A`, o backend precisava validar rigidamente os endpoints que o Tenant pode informar.

## 2. Política Adotada
Foi adotada a **Política A — Internet pública apenas**.
- **Contexto:** Num ambiente multitenant (AgroSaaS), permitir o Gateway resolver para IPs privados ou redes locais do ambiente cloud introduziria um risco crítico de SSRF (Server-Side Request Forgery). Como não há restrição de escopo de rede do Tenant nativamente ligada, qualquer endereço interno seria alcançável. 
- A aplicação impõe validação baseada em resolução DNS. 
- **O piloto Safra Café** usará domínio público. Endereços públicos válidos seguem funcionando. 
- Redes privadas, caso necessitem ser mapeadas no futuro via túneis ou instâncias privadas dedicadas, poderão ser cadastradas através de uma evolução (Política B com allowlists declarativas), mas por default estão fechadas.

## 3. Ações Realizadas

### 3.1. Validador Centralizado
- Criada a biblioteca `services/api/integracoes/url_validator.py` (`validate_provider_url`).
- Ela executa resolução DNS não-bloqueante via `anyio.to_thread.run_sync(socket.getaddrinfo, ...)` para descobrir os IPs reais por trás do domínio.
- **Guardrails:**
  - `userinfo` (ex: usuário e senha na URL) é rejeitado.
  - O host/DNS não pode resolver para IP `is_loopback`, `is_private`, `is_link_local` (protege metadados AWS/GCP 169.254.169.254), `is_multicast`, `is_reserved`, `is_unspecified`.
  - São suportados nativamente `http`, `https`, `ws`, `wss`.
  - O timeout de DNS (5s) atua evitando exaustão.

### 3.2. Integração no `SyncService`
- O método `_normalize_config_values` do `SankhyaSyncService` (que processa a carga antes do save) foi tornado `async def` para permitir a checagem não-bloqueante de DNS.
- Três campos-chaves estão guardados pela função: `sankhya_api_base_url`, `sankhya_auth_url` e `ws_url`.
- Isso garante que tanto o processo de Teste de Conexão quanto o Sync Schedulado e o Save compartilham o mesmíssimo guardrail, rejeitando payloads injetados e alertando o Tenant adequadamente.

### 3.3. HTTPX e Redirecionamentos
- O `httpx.AsyncClient` usado no `SankhyaGatewayAuthService` foi explicitamente definido com `follow_redirects=False`. 
- Dessa forma, um atacante não consegue contornar a validação através de um domínio público que faça um redirect HTTP(301/302) para um `localhost` na hora da execução do pacote.

### 3.4. Cobertura de Testes
- Adicionado `services/api/tests/unit/integracoes/test_provider_url_validator.py` focado apenas na checagem dos bloqueios.
- Foram introduzidas 12 checagens unitárias específicas com mock assíncrono para os diferentes subcasos (loopback, IPv6, private, AWS metadata, timeout, credenciais na URL, domínios punycode).
- O arquivo global `conftest.py` teve o _fixture_ global `mock_dns_globally` injetado para garantir que os testes dos _services_ canônicos do sistema não realizem resoluções externas, agilizando a suíte e evitando _flakes_ de timeout de CI.

## 4. Arquivos Alterados
- `services/api/integracoes/url_validator.py` [NEW]
- `services/api/integracoes/sankhya/services/sync_service.py` [MODIFIED]
- `services/api/integracoes/sankhya/services/auth_service.py` [MODIFIED]
- `services/api/tests/unit/integracoes/test_provider_url_validator.py` [NEW]
- `services/api/tests/unit/integracoes/conftest.py` [MODIFIED]

## 5. Veredito Final
A proteção contra SSRF cobriu as lacunas de manipulação de URLs abertas em `ERP-GATE-01A`.
**Status:** GO. Autorizado prosseguimento para ERP-GATE-01C.
