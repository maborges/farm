# DEEPFARMS-AGRO-FREE-01E2F-C3 — Cofre BYOK e Proxy Seguro de Cotações

**Data:** 20 de Outubro de 2026  
**Status:** CONCLUÍDO  
**Veredicto:** **GO** (Homologado para Integração e Avanço à Fase C4)  
**Ambiente:** Antigravity / DeepFarms Monorepo  
**Módulos Impactados:** `services/api/agro_identity`, `services/api/main.py`, `apps/agro`  

---

## 1. Sumário Executivo

A fase **DEEPFARMS-AGRO-FREE-01E2F-C3** implementou a infraestrutura completa, resiliente e criptograficamente protegida do **Cofre de Credenciais Externas (BYOK — Bring Your Own Key)** e do **Proxy Delegado Seguro de Cotações Agropecuárias**, viabilizando que usuários individuais do DeepFarms Agro conectem seus próprios provedores de mercado sem comprometer a identidade segregada, o acesso público gratuito ou o isolamento estrito contra o SaaS comercial.

### Principais Entregas Homologadas:
1. **Eliminação do Vazamento de JWT no Payload JSON**: Remoção definitiva do campo `token` no body de resposta das rotas de cadastro e login (`POST /api/v1/agro/auth/register` e `POST /api/v1/agro/auth/login`). A sessão individual é estabelecida e transmitida exclusivamente através do cookie seguro `HttpOnly` (`deepfarms_agro_session`), mitigando riscos de extração de credenciais via XSS.
2. **Cofre Segregado com Envelope Encryption (AES-256-GCM + KMS)**: Armazenamento de credenciais vinculadas ao UUID individual, com DEK (*Data Encryption Key*) de 256 bits individual e efêmera por segredo e KEK (*Key Encryption Key*) versionada gerenciada por KMS e derivada deterministicamente por usuário via HKDF-SHA256. Rotação de KEK instantânea ($O(1)$) sem decifração dos dados brutos.
3. **Migrações Versionadas Exclusivas do Banco Agro**: Criação da tabela de controle `agro_schema_versions` e migrações versionadas no banco SQLite segregado (`data/agro_identity/agro_identity.db`), sem alterar schemas ou consumir tabelas do PostgreSQL comercial.
4. **Proxy Delegado com Proteção Ativa contra SSRF**: Validação estrita de entradas contra catálogo fechado de provedores e commodities, com rejeição categórica de URLs arbitrárias, IPs privados (RFC1918), loopback e metadados de nuvem (`169.254.169.254`).
5. **Isolamento de Cache Privado e Rate Limiting**: Cache de cotações com chave vinculada ao usuário (`agro:byok:quote:{user_id}:{provider_slug}:{commodity}:{tipo_mercado}`) e TTL de 60 segundos, sem qualquer compartilhamento com o cache público (`agro:ptax:*`, `agro:public:mercado:*`). Rate limiting dedicado de 30 req/min por usuário/provedor com fallback resiliente em memória compartilhada.
6. **Compliance Contratual de Licenciamento**: Conectores comerciais reais (`TWELVE_DATA`, `POLYGON`, `IBKR`) mantidos estritamente desabilitados com HTTP 403 Forbidden e justificativas regulatórias detalhadas (restrições de redistribuição da CME Group, ICE Futures e B3). O conector `SIMULATED` foi homologado com contratos calibrados para testes completos sem contratação de serviços pagos.
7. **Contrato Padronizado de Cotações**: Separação mandatória entre Mercado FÍSICO nacional (ex: Soja Paranaguá R$/sc, Milho Campinas, Boi Gordo SP R$/@) e Mercado FUTURO internacional/B3 (CBOT ZS em US$ cents/bushel, B3 CCM, B3 BGI), com identificador explícito de titularidade (`titularidadeByok = f"BYOK-{user_id.hex[:8]}-{provider_slug}"`).

---

## 2. Decisões de Arquitetura e Segurança

### 2.1. Envelope Encryption (AES-256-GCM + KMS)

A arquitetura do cofre BYOK foi concebida sob o padrão de **Envelope Encryption** de 2 camadas:

```
+--------------------------------------------------------------------------+
|                            ENVELOPE ENCRYPTION                           |
+--------------------------------------------------------------------------+
|  [Segredo Original (API Key)]                                            |
|         |                                                                |
|         +---> AES-256-GCM (DEK Efêmera de 256 bits)                      |
|         |     AAD: user_id (bytes) + provider_slug                       |
|         v                                                                |
|  [Ciphertext + Data Nonce]                                               |
|                                                                          |
|  [DEK Efêmera (32 bytes)]                                                |
|         |                                                                |
|         +---> AES-256-GCM (KEK do Usuário derivada via HKDF-SHA256)      |
|         |     AAD: user_id (bytes) + "dek:v{key_version}"                |
|         v                                                                |
|  [Encrypted DEK + DEK Nonce]                                             |
+--------------------------------------------------------------------------+
```

- **Isolamento de Chaves**: A KEK mestra (`AGRO_VAULT_MASTER_KEY`) é gerida por interface `IKmsKeyManager` e é completamente dissociada do segredo JWT do SaaS (`AGRO_JWT_SECRET_KEY` e `settings.jwt_secret_key`).
- **Derivação de KEK por Usuário**: Cada usuário possui uma KEK criptograficamente única derivada via HKDF-SHA256 com `salt=deepfarms:agro:byok:user_kek:v{version}` e `info=user_id.bytes`. Um comprometimento local da KEK de um usuário não expõe dados de outros usuários.
- **Autenticidade e AAD (Additional Authenticated Data)**: O AAD vincula rigidamente o segredo ao `usuario_id` e ao `provider_slug`. Se um registro cifrado for copiado para outro usuário no banco, a decriptação falhará imediatamente devido à violação da tag GCM de 128 bits.
- **Rotação de Chaves $O(1)$**: A rotação de versão de KEK (ex: v1 para v2) re-encapsula apenas a DEK sob a nova versão de KEK. O payload cifrado de dados brutos e seu nonce permanecem intactos, permitindo rotação instantânea sem sobrecarga de I/O ou decifração do segredo na memória.

### 2.2. Migrações Versionadas Exclusivas (`agro_schema_versions`)

O banco segregado SQLite (`data/agro_identity/agro_identity.db`) conta com motor de migrações independente implementado em `services/api/agro_identity/migrations.py`:
- **Tabela de Controle**: `agro_schema_versions (version INT PRIMARY KEY, name TEXT, applied_at TEXT)`.
- **Migração 1 (`initial_identity`)**: Criação de `agro_usuarios`, `agro_sessoes`, `agro_tokens_recuperacao`, `agro_tokens_verificacao` e índices.
- **Migração 2 (`byok_envelope_vault`)**: Criação da tabela `agro_user_byok_credentials` contendo `mascara_chave`, `ciphertext_b64`, `data_nonce_b64`, `dek_encrypted_b64`, `dek_nonce_b64`, `key_version`, `status`, `ultimo_uso`, com índice único `(usuario_id, provider_slug)`.

### 2.3. Isolamento Absoluto contra o SaaS Comercial

- **Zero Consumo de Conexões**: Nenhuma rota ou serviço do cofre BYOK ou proxy utiliza `core.database.async_session_maker` ou a engine PostgreSQL comercial (`pool_size=3`).
- **Guarda-Corpos de Middleware em `main.py`**:
  - `SessionHeartbeatMiddleware`: Atualizado para ignorar o prefixo completo `"/api/v1/agro/"`, impedindo execuções de heartbeat e consultas a `SessaoAtiva` no PostgreSQL comercial.
  - `TenantRLSMiddleware`: Atualizado em `_SKIP_PATHS` para incluir `"/api/v1/agro/"`, impedindo tentativas de decodificar tokens individuais com a chave JWT comercial e prevenindo ativação de RLS.

---

## 3. Proxy Delegado Seguro e Mitigações de Risco

### 3.1. Prevenção Ativa de SSRF (Server-Side Request Forgery)
- **Catálogo Fechado de Parâmetros**: O proxy aceita apenas provedores e commodities estritamente catalogados (`SIMULATED`, `SOJA`, `MILHO`, `BOI_GORDO`, `CAFE`, `TRIGO`).
- **Validador Preventivo `validar_ssrf_safety`**: Examina as entradas contra padrões regex que detectam URLs arbitrárias (`http://`, `https://`, `ftp://`, `file://`, `gopher://`), endereços de loopback (`localhost`, `127.0.0.1`, `::1`), metadados de instâncias em nuvem (`169.254.169.254`) e redes privadas RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), retornando `HTTP 400 Bad Request` antes de qualquer processamento de rede.
- **Endpoints Estáticos**: O servidor nunca concatena URLs fornecidas pelo cliente para chamadas de rede externas.

### 3.2. Rate Limiting por Usuário e Provedor
- Implementado via `ByokRateLimiter` com chave `agro:byok:ratelimit:{user_id}:{provider_slug}` e limite de 30 requisições por minuto.
- Resiliência: se o Redis estiver indisponível ou offline, o sistema ativa automaticamente um fallback em memória compartilhada do processo (`_SHARED_LOCAL_RATE_FALLBACK` com sliding window), evitando falhas em cascata ou negação de serviço.
- Exceder a quota gera `HTTP 429 Too Many Requests` com cabeçalho `Retry-After`.

### 3.3. Cache Privado Estritamente Isolado
- Chave Redis: `agro:byok:quote:{user_id}:{provider_slug}:{commodity}:{tipo_mercado}` com TTL de 60 segundos.
- **Zero Vazamento para o Cache Público**: As chaves do BYOK residem no namespace privado `agro:byok:quote:*`, nunca interagindo com `agro:ptax:*`, `agro:public:mercado:*` ou `agro:sidra:*`.
- O payload em cache contém o metadado `titularidadeByok = f"BYOK-{user_id.hex[:8]}-{provider_slug}"`, atestando documentalmente a titularidade da requisição.
- Fallback local compartilhado (`_SHARED_LOCAL_CACHE_FALLBACK`) garante cache consistente mesmo em ambientes de teste ou sem Redis.

### 3.4. Controle de Concorrência e Timeouts
- **Semáforo Global**: `asyncio.Semaphore(AGRO_BYOK_CONCURRENCY_LIMIT)` limita a no máximo 5 consultas externas simultâneas por worker.
- **Deduplicação Single-Flight**: Requisições simultâneas do mesmo usuário para o mesmo instrumento aguardam a conclusão da primeira chamada via lock atômico por instrumento, evitando rajadas repetidas ao provedor.
- **Timeout Estrito**: Todas as buscas possuem timeout de 5,0 segundos via `asyncio.wait_for`, retornando `HTTP 504 Gateway Timeout` em caso de lentidão externa.

---

## 4. Análise de Licenciamento e Compliance de Provedores

Antes de habilitar qualquer conector comercial, realizou-se auditoria documental e contratual:

| Provedor | Instrumentos Pretendidos | Exigências Contratuais e Restrições Oficiais | Status no DeepFarms Agro |
| :--- | :--- | :--- | :--- |
| **Simulated Homologado** | Soja, Milho, Boi Gordo, Café, Trigo | Dados sintéticos calibrados internamente sem consumo externo de APIs ou quotas pagas. | **ATIVO** (Homologado) |
| **Twelve Data** | Soja, Milho, Trigo, Café (CBOT/ICE) | Termos de Uso (Seção 4) proíbem cache para redistribuição em planos Basic/Developer e proxies multi-tenant. Dados em tempo real de commodities exigem taxas de bolsa adicionais da CME/ICE. | **DESABILITADO_LICENCA** (Bloqueio 403) |
| **Polygon.io** | Soja, Milho (CBOT/CME) | Planos de varejo/Starter não contemplam futuros agropecuários da CBOT; redistribuição exige contratação Enterprise direta. | **DESABILITADO_LICENCA** (Bloqueio 403) |
| **Interactive Brokers (IBKR)** | Soja, Milho, Boi, Café, Trigo | Acesso à API Client Portal exige execução contínua de gateway local autenticado com 2FA a cada 24 horas e subscrição individual de Market Data CME/B3. | **DESABILITADO_LICENCA** (Bloqueio 403) |

**Conclusão**: O DeepFarms Agro mantém os conectores externos reais desabilitados com bloqueio explícito via `HTTP 403 Forbidden` informando o motivo regulatório. O provedor `SIMULATED` garante testes completos, robustez operacional e estabilidade funcional contínua.

---

## 5. Contrato Padronizado de Cotações

O contrato `ByokCotacaoResponse` distingue categoricamente mercados físicos nacionais de mercados futuros internacionais e da B3:

```json
{
  "commodity": "SOJA",
  "instrumento": "SOJA_BR_PARANAGUA_CEPEA",
  "tipoMercado": "FISICO",
  "valor": 138.50,
  "moeda": "BRL",
  "unidade": "saca 60kg",
  "bolsaOuRegiao": "Porto de Paranaguá/PR",
  "dataReferencia": "2026-10-20T20:54:30.123456Z",
  "fonte": "CEPEA/ESALQ (Homologado)",
  "provedor": "SIMULATED",
  "situacao": "FECHAMENTO",
  "titularidadeByok": "BYOK-d2d2cd3c-SIMULATED",
  "cached": false
}
```

```json
{
  "commodity": "SOJA",
  "instrumento": "CBOT:ZS",
  "tipoMercado": "FUTURO",
  "valor": 1025.25,
  "moeda": "USD_CENT",
  "unidade": "bushel",
  "bolsaOuRegiao": "CBOT - Chicago Board of Trade",
  "dataReferencia": "2026-10-20T20:54:30.123456Z",
  "fonte": "CBOT/CME Simulado",
  "provedor": "SIMULATED",
  "situacao": "TEMPO_REAL",
  "titularidadeByok": "BYOK-d2d2cd3c-SIMULATED",
  "cached": false
}
```

---

## 6. Resultados e Evidências dos Testes

### 6.1. Suíte Unitária e de Integração BYOK (`test_agro_byok.py`)
- **Arquivo**: `services/api/tests/unit/test_agro_byok.py`
- **Execução**: `services/api/.venv/bin/pytest services/api/tests/unit/test_agro_byok.py -v`
- **Resultado**: **11 passed in 21.48s**

| ID | Teste | Cenário Validado | Resultado |
| :--- | :--- | :--- | :--- |
| **01** | `test_01_envelope_encryption_e_decriptacao` | Cifra com DEK efêmera + KEK KMS; decifra segredo; rejeita tag GCM adulterada | **PASS** |
| **02** | `test_02_rotacao_de_kek_kms` | Rotação KEK v1 para v2; preserva dados brutos e re-cifra DEK; decifra na v2 | **PASS** |
| **03** | `test_03_isolamento_de_credenciais_entre_usuarios` | Usuário A cadastra; Usuário B vê cofre vazio; B não pode excluir credencial de A | **PASS** |
| **04** | `test_04_bloqueio_criptografico_de_acesso_cruzado` | Tentativa de decifrar segredo de A usando ID de B falha no AAD do AES-GCM | **PASS** |
| **05** | `test_05_catalogo_de_provedores_e_bloqueio_de_licenca` | Twelve Data, Polygon e IBKR retornam status DESABILITADO e HTTP 403 Forbidden | **PASS** |
| **06** | `test_06_prevencao_estrita_de_ssrf` | Rejeição de IPs privados, localhost, AWS metadata e esquemas file/gopher | **PASS** |
| **07** | `test_07_contrato_cotacoes_separacao_fisico_vs_futuro` | Respostas padronizadas para Soja, Milho, Boi, Café e Trigo (Físico vs Futuro) | **PASS** |
| **08** | `test_08_cache_privado_estritamente_isolado` | Usuário 1 obtém cache privado (cached=True); Usuário 2 não compartilha cache | **PASS** |
| **09** | `test_09_rate_limiting_por_usuario` | Bloqueio com HTTP 429 Too Many Requests e cabeçalho Retry-After no excesso | **PASS** |
| **10** | `test_10_revogacao_e_exclusao_de_credenciais` | Revogação impede novas cotações (404); exclusão remove permanentemente | **PASS** |
| **11** | `test_11_rotacao_de_chaves_via_api` | `POST /credentials/rotate-keys?nova_versao=2` rotaciona versão no cofre e consulta | **PASS** |

### 6.2. Regressão da Identidade Individual (`test_agro_identity.py`)
- **Arquivo**: `services/api/tests/unit/test_agro_identity.py`
- **Resultado**: **13 passed in 20.63s** (Cadastro, login, HttpOnly, ausência de JWT no body, lockout anti-força bruta, guardrail 403 contra pool comercial, integridade SQLite WAL).

### 6.3. Regressão de Módulos Públicos de Mercado
- **Arquivos**: `test_ptax_publico.py`, `test_macro_publico.py`, `test_ibge_sidra_publico.py`
- **Resultado**: **37 passed in 17.56s** (PTAX diário BCB, Meta Selic, IPCA mensal/12M, PAM, PPM e LSPA do IBGE).

### 6.4. Frontend Web Vitest (`apps/agro`)
- **Comando**: `pnpm --filter agro test`
- **Resultado**: **6 test files passed, 90 tests passed in 667ms**.

### 6.5. Testes E2E Playwright (`apps/agro`)
- **Comando**: `pnpm --filter agro test:e2e`
- **Resultado**: **20 passed in 17.9s** (Navegação anônima, calculadoras rurais, PTAX, fluxo completo de autenticação individual via cookies HttpOnly e Service Worker PWA).

### 6.6. Qualidade de Código (Lint, Typecheck e Build)
- **Typecheck**: `pnpm --filter agro typecheck` -> **0 erros (TypeScript 5.9.3)**.
- **ESLint**: `pnpm --filter agro lint` -> **0 erros e 0 warnings**.
- **Next.js Build**: `pnpm --filter agro build` -> **Compilado com sucesso em 5.1s (Next.js 16.1.6 webpack, 10 páginas estáticas otimizadas)**.

---

## 7. Limitações e Salvaguardas

1. **Conectores Reais Bloqueados por Compliance**: Conectores comerciais reais (`TWELVE_DATA`, `POLYGON`, `IBKR`) continuam bloqueados a nível de código no backend. Sua ativação futura exigirá validação formal de termos de redistribuição institucional junto à CME Group, ICE e B3.
2. **Infraestrutura Sem Custos**: O provedor `SIMULATED` garante testes completos, desenvolvimento seguro e homologação contínua de ponta a ponta sem qualquer contratação de serviços pagos.
3. **Escopo Restrito à Infraestrutura (C3)**: A interface de usuário para configuração do cofre BYOK e visualização gráfica de cotações delegadas pertence à fase **C4** e não foi antecipada, respeitando os limites da tarefa.

---

## 8. Veredicto Final

### **GO**

A infraestrutura do **Cofre BYOK com Envelope Encryption** e do **Proxy Seguro de Cotações Agropecuárias** está implementada, testada e homologada com sucesso, mantendo segregação absoluta contra o SaaS comercial e conformidade integral com as Leis Fundamentais do DeepFarms Agro. O sistema está pronto para a fase seguinte (**C4 — Interface e Conexão de Provedores pelo Usuário**).
