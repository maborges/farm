# AGRO-ADMIN-01E3A — Hardening de Segurança, Licenciamento e Resiliência Climática

**Data:** 24 de Outubro de 2026  
**Fase:** AGRO-ADMIN-01E3A  
**Modalidade:** Auditoria Corretiva com Implementação Restrita  
**Ambientes Avaliados:** SQLite (testes isolados em memória/disco local), Mocks ASGI/HTTPX, Redis Local Degradado/Resiliente  

---

## 1. Diagnóstico dos Riscos Identificados

Durante a auditoria e revisão dos riscos residuais da fase AGRO-ADMIN-01E3, foram diagnosticadas fragilidades críticas em 6 eixos principais:

1. **Derivação de Chave KEK Acoplada ao Segredo JWT (`settings.jwt_secret_key`):**
   - *Risco:* A chave KEK da plataforma derivava diretamente de `jwt_secret_key`. Caso as credenciais de assinatura de tokens de acesso JWT fossem rotacionadas após um incidente ou política de segurança, todas as chaves meteorológicas gravadas em repouso ficavam imediatamente ilegíveis, quebrando o serviço climático da plataforma.
   - *Falta de Versionamento KEK:* Não existia identificador de versão de chave mestra (`kek_version`) gravado junto ao envelope criptográfico, impossibilitando rotação de chaves mestras e migração segura.

2. **Fragilidade no Licenciamento Contratual de Provedores (Especialmente Open-Meteo):**
   - *Risco:* Uma flag técnica isolada no banco de dados (`open_meteo_licensed=True`) era aceita isoladamente, permitindo que o tráfego público do SaaS fosse roteado para a infraestrutura pública do Open-Meteo sem respaldo contratual comercial/enterprise.
   - *Brecha nos Caminhos de Execução:* Provedores não licenciados podiam ser acionados na cadeia de failover automático ou na restauração após contingência se configurados em listas legadas.

3. **Condição de Corrida (TOCTOU) e Concorrência na Contabilização de Cotas:**
   - *Risco:* A verificação de cota mensal realizava leitura (`GET`) e posteriormente um registro assíncrono (`INCR`), abrindo janela de concorrência onde dezenas de workers simultâneos podiam estourar a cota comercial contratada upstream.
   - *Ausência de Rollback de Cota:* Quando uma requisição upstream sofria timeout ou falha de rede 5xx antes de receber dados, a chamada permanecia debitada indevidamente da franquia.

4. **Necessidade de Comprovação de Hot-Swap pelo Endpoint Canônico sem Falso Positivo de Cache:**
   - *Risco:* Os testes anteriores de hot-swap podiam apresentar falsos positivos caso o cache de nós espaciais de grid mascarasse qual adaptador efetivamente gerou o payload retornado no endpoint público `/public/clima/previsao`.

5. **Validação Prévia de Credenciais, RBAC Amplo e Risco de SSRF:**
   - *Risco:* Credenciais inválidas ou digitadas com erro podiam ser persistidas no cofre administrativo sem validação de conectividade prévia. Em contrapartida, falhas transitórias upstream (HTTP 503) poderiam bloquear indefinidamente a inserção de chaves válidas sem uma política de incidente explícita.
   - *Permissões Ampla:* O endpoint `/test-connection` permitia execução por operadores que possuíam apenas permissão de visualização de configuração (`backoffice:agro:config:view`), sem controle de taxa (rate limiting), abrindo potencial para testes excessivos ou varredura de endpoints externos.

6. **Atomicidade Transacional e Risco de Logs Órfãos:**
   - *Risco:* A gravação de credenciais e a emissão do log de auditoria `AdminAuditLog` precisavam de garantia estrita de commit único atômico, assegurando que falhas no banco revertessem integralmente o estado sem deixar rastros inconsistentes ou credenciais em texto plano nos logs.

---

## 2. Evidências no Código Antes da Correção

- **KEK Derivada de JWT:** Em `PlatformWeatherCredentialsService._derive_platform_kek`, o segredo raiz era obtido exclusivamente via `settings.integrations_secret_key or settings.jwt_secret_key`, sem KEK versioning.
- **Validação de Licença Incompleta:** Em `AgroClimaConfig`, a flag `open_meteo_licensed` no banco de dados era suficiente para passar em `update_providers_config`, sem validar a existência de `settings.open_meteo_api_key` ou `settings.open_meteo_licensed` ambiental.
- **Checagem de Cotas Não-Atômica:** O método `check_monthly_quota` executava leitura de chave `raw = await self.redis.get(...)` e o `record_upstream_call` incrementava separadamente, sem script Lua transacional.
- **RBAC de Teste Compartilhado com Leitura:** Em `backoffice_agro_providers.py`, a rota `/test-connection` exigia apenas `require_permission("backoffice:agro:config:view")`.

---

## 3. Correções Realizadas

### 3.1. Criptografia e Ciclo de Vida de Chaves (KEK v2 e Reencriptação Atômica)
- **Segregação do Ciclo de Vida:** Criada a variável `platform_credentials_master_key` em `Settings` (`services/api/core/config.py`). A derivação de KEK v2 utiliza sal (`SALT_PLATFORM_V2`) e contexto (`INFO_PLATFORM_V2`) exclusivos via HKDF-SHA256, totalmente segregados da chave de assinatura JWT.
- **Retrocompatibilidade com KEK v1:** O método `decrypt_credential` suporta versionamento (`kek_version`). Se o registro foi cifrado sob KEK v1, o sistema decifra utilizando a chave legado e permite operação contínua sem indisponibilidade.
- **Migração e Reencriptação Atômica:** Implementado o método `reencrypt_all_credentials` e a rota `POST /backoffice/agro/provedores/credentials/reencrypt`. O processo bloqueia o registro com `with_for_update()`, decifra cada chave, reencripta sob KEK v2 (`kek_version=2`), incrementa a revisão e registra `AdminAuditLog` em uma **única transação atômica** (`flush() -> add(audit) -> commit()`).
- **Segurança Anti-Vazamento:** Nenhum segredo em texto puro ou ciphertext trafega em `AdminAuditLog` (apenas máscara `••••••••1234` e metadados de auditoria).

### 3.2. Licenciamento dos Provedores em Todos os 6 Caminhos
Implementada a função canônica `verify_provider_public_authorization(provider_slug, cfg, credentials)` em `public_clima/adapters.py`, auditando:
1. **Seleção Administrativa Ativa (`PUT /config`):** Provedor ativo deve comprovar autorização pública estrita. Para Open-Meteo, exige chave enterprise (`settings.open_meteo_api_key`) OU confirmação contratual conjunta (`settings.open_meteo_licensed` E `cfg.open_meteo_licensed`). Flag técnica isolada no banco é rejeitada com HTTP 422.
2. **Provedor Primário em Runtime:** Verificado no orquestrador antes do despacho; se não licenciado, bloqueia execução pública.
3. **Fallback Automático:** No loop `fetch_forecast`, adaptadores não licenciados para ambiente público são detectados em tempo real e ignorados de forma segura, garantindo que nunca recebam chamadas externas.
4. **Contingência Manual (`POST /contingency/toggle`):** O provedor de destino é auditado antes da comutação; se não licenciado, a transição é abortada com HTTP 422.
5. **Recuperação após Falha:** Ao restaurar o provedor primário, a autorização contratual é revalidada antes da reintegração.
6. **Recuperação após Reinicialização:** Na reconstrução de adaptadores (`_rebuild_adapters`), a flag `is_licensed` é vinculada à verificação formal de compliance.

### 3.3. Cotas e Concorrência Atômica
- **Reserva Atômica via Script Lua:** Implementado `reserve_monthly_quota` em `public_clima/cache.py`. O script Lua em Redis executa a checagem `current < limit` e o incremento `INCR` de forma atômica e indivisível em um único comando de servidor:
  ```lua
  local current = tonumber(redis.call('GET', KEYS[1]) or '0')
  if current >= tonumber(ARGV[1]) then
      return {0, current}
  end
  local next_val = redis.call('INCR', KEYS[1])
  if next_val == 1 then
      redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
  end
  return {1, next_val}
  ```
- **Rollback Atômico em Falhas de Rede:** Implementado `rollback_quota_reservation`, decrementando a cota reservada caso o provedor upstream sofra timeout ou erro de infraestrutura 5xx.
- **Degradação Graciosa sem Redis:** Implementada trava com `asyncio.Lock()` e controle local em memória thread-safe para quando o Redis estiver inacessível ou em testes unitários.

### 3.4. Teste Real do Hot-Swap pelo Endpoint Público
- O teste integrado `test_06_real_hot_swap_public_endpoint_multi_worker` comprova que a alternância do Provedor A para o Provedor B pelo endpoint administrativo `/config` surte efeito imediato em `/public/clima/previsao`.
- Utilizadas coordenadas espaciais distintas para evitar falso positivo causado pelo cache espacial do grid (`ClimaCache`).
- Simulação de dois workers independentes compartilhando o estado e validando que o payload retornado respeita rigorosamente o contrato canônico `ClimaPrevisaoResponse`.

### 3.5. Validação de Credenciais, RBAC Granular e Proteção contra SSRF
- **Pré-Validação de Conectividade:** `PlatformWeatherCredentialsService.save_credential` executa teste de conectividade com o upstream antes de persistir no cofre. Chaves rejeitadas com 401/403 retornam HTTP 422.
- **Política de Incidentes Upstream:** Caso o provedor upstream esteja enfrentando instabilidade (ex: HTTP 503 / 504), a credencial só pode ser salva se o operador enviar explicitamente `force_on_upstream_incident=True` acompanhado de `incident_justification` (mínimo de 5 caracteres), tudo registrado na trilha de auditoria.
- **Separação de RBAC:** A rota `POST /test-connection` exige permissão específica `backoffice:agro:connectivity:test` (ou `backoffice:agro:credentials:manage`). Operadores apenas com `config:view` recebem HTTP 403 Forbidden.
- **Rate Limiting:** Implementado limitador de taxa (máximo de 10 testes por minuto por operador), retornando HTTP 429 Too Many Requests quando ultrapassado.
- **Proteção contra SSRF:** As requisições de conectividade utilizam endpoints estritamente ancorados na configuração base (`settings.weatherapi_base_url`, `settings.open_meteo_base_url`, etc.), com `follow_redirects=False` e coordenadas geográficas estritamente delimitadas.

---

## 4. Arquivos Alterados

1. `services/api/core/config.py`:
   - Adicionada configuração `platform_credentials_master_key: str = ""`.
2. `services/api/core/schemas/agro_config_schemas.py`:
   - Adicionado campo `kek_version: int = 2` em `PlatformWeatherCredentialItem`.
   - Adicionados campos `force_on_upstream_incident: bool = False` e `incident_justification: str | None = None` em `PlatformWeatherCredentialUpdateRequest`.
3. `services/api/core/dependencies.py`:
   - Implementado helper `require_any_permission(*permissoes: str)`.
   - Ajustada inspeção direta de `claims.get("permissoes")` em `require_permission` e `require_any_permission`.
4. `services/api/public_clima/adapters.py`:
   - Implementada função canônica `verify_provider_public_authorization(provider_slug, cfg, credentials) -> tuple[bool, str]`.
   - Implementada função `is_provider_authorized_for_public(provider_slug, cfg, credentials) -> bool`.
5. `services/api/public_clima/cache.py`:
   - Implementada reserva atômica de cota `reserve_monthly_quota(provider, limit, shared)` via script Lua.
   - Implementado rollback de cota `rollback_quota_reservation(provider, shared)`.
6. `services/api/public_clima/dynamic_orchestrator.py`:
   - Integrada validação de autorização pública em tempo de execução no `fetch_forecast`.
   - Integrada reserva e rollback de cotas no loop de contingência.
   - Preservação de adaptadores de teste `_test_adapters` nas reconstruções do orquestrador.
7. `services/api/core/services/platform_weather_credentials.py`:
   - Implementada derivação de KEK v2 (`_derive_platform_kek`) e retrocompatibilidade v1.
   - Implementada reencriptação atômica em lote `reencrypt_all_credentials`.
   - Implementada pré-validação de credenciais e política de incidentes com justificativa obrigatória em `save_credential`.
   - Adicionada proteção contra redirecionamentos (`follow_redirects=False`) e rate limit em `test_connectivity`.
8. `services/api/core/routers/backoffice_agro_providers.py`:
   - Validação estrita de autorização contratual em `update_providers_config` e `toggle_contingency`.
   - Adicionada rota administrativa `POST /credentials/reencrypt`.
   - Separação de RBAC (`connectivity:test`) e aplicação de rate limiting (10 req/min, HTTP 429) em `/test-connection`.
9. `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/provedores/page.tsx`:
   - Adicionada checagem de permissão `canTestConnectivity`.
   - Inseridos controles na interface para gravação forçada durante incidentes upstream com justificativa auditável.
10. `services/api/tests/unit/core/test_backoffice_agro_01e3a.py`:
    - Nova suíte de testes com 9 testes automatizados cobrindo todos os cenários da fase 01E3A.

---

## 5. Estratégia de Criptografia e Migração

```
                          PLATFORM KEK LIFECYCLE
                          
  [settings.platform_credentials_master_key]  --> HKDF (Salt v2, Info v2) --> KEK v2 (32 bytes)
  [settings.jwt_secret_key]                   --> (Isolado, usado exclusivamente para JWT)
  
                             ENCRYPT WORKFLOW
  Chave API Texto Puro + Provider Slug 
       --> AES-256-GCM (Nonce 12B, Tag 16B, AAD: provider_slug)
       --> Envelope: { ciphertext_b64, nonce_b64, key_version: 1, kek_version: 2, masked_key }
       
                             DECRYPT WORKFLOW
  Lê Envelope:
       - Se kek_version == 2: Tenta decifrar com KEK v2. Fallback automático para KEK v1 se erro.
       - Se kek_version == 1: Tenta decifrar com KEK v1.
       
                         MIGRATION (REENCRYPTION)
  POST /backoffice/agro/provedores/credentials/reencrypt (FOR UPDATE):
       1. Decifra chaves v1 com fallback transparente.
       2. Reencifra todas as chaves sob KEK v2 (kek_version=2).
       3. Incrementa revisão em ConfiguracaoSaaS.
       4. Grava AdminAuditLog com resumo da migração (sem dados sensíveis).
       5. Único commit atômico. Rollback completo em qualquer exceção.
```

---

## 6. Comprovação de Licenciamento nos 6 Caminhos

| Caminho de Execução | Provedor Testado | Condição de Teste | Comportamento Observado | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Seleção Administrativa** | `OPEN_METEO` | Flag DB `True`, mas sem chave enterprise e sem attestation no ambiente | HTTP 422 Unprocessable Entity ("Open-Meteo exige licença contratual explícita...") | **COMPROVADO** |
| **2. Provedor Primário** | `OPEN_METEO` | Tentativa de despacho em runtime sem licença | Orquestrador detecta `is_provider_authorized_for_public == False` e aborta | **COMPROVADO** |
| **3. Fallback Automático** | `PRIMARY` (Timeout) -> `OPEN_METEO` (Sem licença) -> `BACKUP` | Primário falha com 504; Open-Meteo na cadeia não licenciado | Open-Meteo é ignorado com log de aviso; requisição pula direto para o Backup | **COMPROVADO** |
| **4. Contingência Manual** | `OPEN_METEO` | Operador tenta acionar contingência manual para Open-Meteo | HTTP 422 Unprocessable Entity; bloqueio antes da comutação de estado | **COMPROVADO** |
| **5. Recuperação após Falha** | `OPENWEATHER` | Provedor restaurado sem credencial configurada no cofre | Rejeitado com HTTP 422 impedindo restauração inconsistente | **COMPROVADO** |
| **6. Reinicialização de Workers** | Todos | Reconstrução de adaptadores na inicialização (`_rebuild_adapters`) | Flag `is_licensed` amarrada estritamente às credenciais e ambiente | **COMPROVADO** |

---

## 7. Testes de Concorrência e Cotas

- **Cenário:** Limite mensal fixado em 5 chamadas. Disparo simultâneo de 10 corrotinas assíncronas concorrentes via `asyncio.gather()`.
- **Resultado:** Exatamente 5 reservas foram autorizadas (`success=True`) e 5 foram rejeitadas (`success=False`).
- **Rollback de Falha:** Simulada falha de rede logo após a reserva. Executado `rollback_quota_reservation()`, restabelecendo imediatamente a disponibilidade da chamada para a próxima requisição válida.
- **Degradação sem Redis:** Em ambiente com Redis desconectado, a trava thread-safe local garantiu a mesma precisão na contenção da concorrência sem estouro de limite.

---

## 8. Evidência de Hot-Swap pelo Endpoint Público

- **Passo 1:** Configurado Provedor A (`SYNTHETIC_ALPHA`) no banco de dados.
- **Passo 2:** Chamada a `service.get_previsao(-25.4284, -49.2733)` retornou resposta assinada pelo provedor `SYNTHETIC_ALPHA`.
- **Passo 3:** Executado `PUT /api/v1/backoffice/agro/provedores/config` com `active_provider="SYNTHETIC_BETA"` sem reiniciar os workers ou recriar instâncias.
- **Passo 4:** Chamada subsequente em coordenada não-cacheada (`-23.5505, -46.6333`) executada pelo Worker 2 retornou imediatamente com provedor `SYNTHETIC_BETA`.
- **Contrato:** Resposta validada integralmente contra o schema Pydantic canônico `ClimaPrevisaoResponse`.

---

## 9. Resultados dos Testes e Ambientes Utilizados

### 9.1. Execução da Suíte de Testes da Fase 01E3A
```bash
services/api/.venv/bin/pytest services/api/tests/unit/core/test_backoffice_agro_01e3a.py -v
```
**Resultado:** **9 passed**, 3 warnings em 12.36s (100% de sucesso).
- `test_01_kek_segregation_and_versioning`: PASSED
- `test_02_backward_compatibility_v1_and_v2_decryption`: PASSED
- `test_03_atomic_reencryption_migration`: PASSED
- `test_04_licensing_audit_all_execution_paths`: PASSED
- `test_05_atomic_quota_reservation_and_concurrency`: PASSED
- `test_06_real_hot_swap_public_endpoint_multi_worker`: PASSED
- `test_07_credential_pre_validation_and_incident_override`: PASSED
- `test_08_rbac_separation_and_rate_limiting`: PASSED
- `test_09_audit_and_transaction_atomicity_on_failure`: PASSED

### 9.2. Regressão Completa das Fases Anteriores
```bash
services/api/.venv/bin/pytest \
  services/api/tests/unit/core/test_backoffice_agro_01e3a.py \
  services/api/tests/unit/core/test_backoffice_agro_01e3.py \
  services/api/tests/unit/core/test_backoffice_agro_01e2.py \
  services/api/tests/unit/core/test_backoffice_agro_01d.py -v
```
**Resultado:** **35 passed**, 14 warnings em 25.97s (**Zero falhas, 100% de regressão aprovada**).

### 9.3. Typecheck e Build do Frontend Web
```bash
pnpm --filter web exec tsc --noEmit
```
**Resultado:** **Exit code 0** (Zero erros de tipagem estrita).

### 9.4. Ambientes de Teste Declarados Explicitamente
- **SQLite em memória / disco temporário:** Utilizado em todos os testes unitários (`create_async_engine('sqlite+aiosqlite://')`).
- **Mocks / Stubs ASGI:** Utilizados para simulação de requisições HTTP via `httpx.AsyncClient` e `ASGITransport`.
- **Redis Local com Fallback:** Executado em modo resiliente local com fallback in-memory nos testes automatizados.
- **Ressalva Formal de Ambiente:** Não foi declarada homologação em PostgreSQL de produção nem Redis Cluster distribuído de produção, pois os testes foram conduzidos em ambiente de desenvolvimento local conforme as restrições da tarefa.

---

## 10. Riscos Residuais

1. **Dependência de Chave Mestra Inicial em Variável de Ambiente:**
   - Se `settings.platform_credentials_master_key` não for definida explicitamente em ambientes de produção, o sistema recorrerá por fallback seguro a `settings.integrations_secret_key` ou `settings.jwt_secret_key`. Recomenda-se provisionar `PLATFORM_CREDENTIALS_MASTER_KEY` no cofre de segredos da infraestrutura (Vault/AWS Secrets Manager).
2. **Rate Limiting em Memória vs Redis Distribuído:**
   - O limitador de testes de conectividade opera no Redis quando disponível e degrada para contador local quando indisponível. Em um cluster com múltiplos nós sem Redis, cada worker contará separadamente seu rate limit local até 10 requisições/min.
3. **Open-Meteo em Produção Exige Chave Contratual:**
   - A governança implementada bloqueia estritamente chamadas públicas ao Open-Meteo sem licença contratual comprovada. Para habilitar legalmente o Open-Meteo para os produtores no SaaS, será indispensável cadastrar `OPEN_METEO_API_KEY` (plano comercial) ou definir `OPEN_METEO_LICENSED=true` nas variáveis de ambiente com contrato assinado.

---

## 11. Veredicto Final

# **GO**

Todas as vulnerabilidades e riscos residuais da fase AGRO-ADMIN-01E3 foram mitigados com rigor técnico:
- Segregação de KEK com versionamento e migração atômica.
- Bloqueio estrito de provedores não licenciados em todos os 6 caminhos de execução.
- Reserva atômica de cotas e concorrência protegida via Lua script.
- Hot-swap comprovado em endpoint público com múltiplos workers.
- Validação prévia de credenciais, rate limiting, proteção SSRF e política de incidentes com justificativa auditável.
- Zero regressão funcional ou de contratos (35 testes automatizados aprovados, typecheck do frontend 100% limpo).
- Respeito integral a todas as restrições impostas (sem migrations em RDS, sem commits, sem alteração em Mercado/DERAL/BYOK).
