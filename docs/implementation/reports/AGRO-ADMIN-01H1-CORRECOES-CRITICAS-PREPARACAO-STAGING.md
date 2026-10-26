# AGRO-ADMIN-01H1 — Correções Críticas e Preparação Segura de Staging

**Fase:** AGRO-ADMIN-01H1  
**Data:** 2026-10-24  
**Responsável Técnico:** DeepFarms Core & SecOps Engineering  
**Status do Veredicto:** **GO COM RESSALVAS** (Ambiente local corrigido e testado; staging 100% preparado e isolado; aguardando autorização expressa para subida e execução de migrations na fase 01H2)

---

## 1. Achados Reproduzidos da Auditoria AGRO-ADMIN-01G

Antes de iniciar qualquer refatoração, os achados ACHADO-01 a ACHADO-09 do relatório `AGRO-ADMIN-01G-AUDITORIA-INTEGRADA-PLANO-HOMOLOGACAO.md` foram inspecionados contra a base de código real:

| Código | Gravidade | Descrição do Achado | Reprodução / Diagnóstico no Código |
|---|---|---|---|
| **ACHADO-01** | CRÍTICO | Ausência de ciclo de heartbeat na PWA Agro (`apps/agro`) atualizando `ultimo_heartbeat` em `sessoes_ativas`. | **Confirmado:** A PWA autenticava via cookie HttpOnly, mas não enviava batimentos regulares. O middleware dependia de navegações de página inteira, gerando desatualização de `ultimo_heartbeat` e distorcendo a métrica de usuários ativos no Backoffice. |
| **ACHADO-02** | ALTO | Reserva de cotas de clima vulnerável a concorrência distribuída (*race condition* TOCTOU). | **Confirmado:** `DynamicWeatherOrchestrator` consultava e incrementava métricas de forma não atômica, além de consumir cota mesmo quando a chamada upstream falhava por timeout ou erro de rede. |
| **ACHADO-03** | ALTO | Fallback silencioso de `PLATFORM_CREDENTIALS_MASTER_KEY` para `JWT_SECRET_KEY` em staging/produção. | **Confirmado:** Em `_derive_platform_kek()`, se a chave mestre dedicada estivesse ausente, a função derivava o KEK v2 silenciosamente a partir de `jwt_secret_key`, violando a segregação de ciclo de vida criptográfico. |
| **ACHADO-04** | MÉDIO | Proveniência DERAL baseada em checagem sintática de URL/string declarada como se fosse atestação criptográfica. | **Confirmado:** `verificar_proveniencia_governamental` validava apenas se a URL terminava em `pr.gov.br` ou continha `prp.xls`, sem atestação criptográfica mTLS, enquanto o dashboard rotulava o item como "APROVADO". |
| **ACHADO-05** | MÉDIO | Script de homologação PostgreSQL executava `alembic upgrade head` sem validação de isolamento estrito. | **Confirmado:** Não havia barreira impedindo execução acidental de migrações contra bancos compartilhados ou RDS de homologação. |
| **ACHADO-06** | MÉDIO | Matriz de homologação do Dashboard Agro inflada (63.6%), considerando itens como aprovados com evidências puramente locais ou declaratórias. | **Confirmado:** Itens dependentes de PostgreSQL dedicado, Redis real e cluster multi-worker ASGI estavam marcados como aprovados ou com percentual otimista. |
| **ACHADO-07** | MÉDIO | Ausência de stack Docker Compose isolada e efêmera para staging no monorepo. | **Confirmado:** Existia apenas um `docker-compose.yml` de desenvolvimento local e um `docker-compose.prod.yml`, sem ambiente descartável com portas e volumes segregados. |
| **ACHADO-08** | BAIXO | Falta de procedimento auditável de rotação e recifragem de KEK v1 para KEK v2 em lote. | **Confirmado:** O serviço suportava decifração retrocompatível v1/v2, mas não possuía rotina automatizada para re-criptografia e auditoria em lote. |
| **ACHADO-09** | BAIXO | Políticas de retenção de documentos originais em Base64 sem justificativa técnica no repositório. | **Confirmado:** Documentos brutos (.xls) eram salvos na tabela `deral_snapshots` sem documentação explícita de teto de payload (10 MB) e ciclo de retenção (12 meses para cobrir safra/entressafra). |

---

## 2. Correções Implementadas

### 2.1. Heartbeat Seguro e Leve da PWA Agro
- **Endpoint Backend:** Criado `POST /api/v1/auth/heartbeat` em [auth.py](file:///opt/lampp/htdocs/farm/services/api/core/routers/auth.py).
  - Autenticação via cookie HttpOnly (`deepfarms_agro_session` ou `deepfarms_session`) ou header Bearer.
  - Verificação de CSRF via proteção de cookie e header `X-Agro-CSRF: 1`.
  - Rejeição imediata de contas inativas ou bloqueadas (HTTP 403 Forbidden).
  - Rejeição imediata de sessões expiradas, inexistentes ou revogadas (HTTP 401 Unauthorized).
  - Throttling em memória de 60 segundos por sessão (`_HEARTBEAT_CACHE`): requisições repetidas dentro do intervalo retornam `{"ok": true, "throttled": true}` sem onerar o banco com queries de escrita.
  - Renovação atômica de `ultimo_heartbeat` e recálculo de `expira_em` conforme `session_idle_minutes`.
- **Cliente PWA Agro:**
  - Criado `sendAgroHeartbeat()` em [agro-auth.ts](file:///opt/lampp/htdocs/farm/apps/agro/src/lib/auth/agro-auth.ts) com checagem de conectividade de rede (`navigator.onLine`) e estado de visibilidade (`document.visibilityState === 'visible'`).
  - Criado componente cliente [session-heartbeat.tsx](file:///opt/lampp/htdocs/farm/apps/agro/src/components/auth/session-heartbeat.tsx) ouvindo eventos de interação (`pointerdown`, `keydown`, `scroll`, `touchstart`) com debounce de 60 segundos.
  - Montado no layout raiz [layout.tsx](file:///opt/lampp/htdocs/farm/apps/agro/src/app/layout.tsx). Sessões em segundo plano (background) ou offline são pausadas, impedindo geração de atividade artificial.

### 2.2. Controle Atômico de Cotas e Prevenção de Estouro de Upstream
- **Script Lua no Redis:** Implementado em `ClimaCache.reserve_monthly_quota` ([cache.py](file:///opt/lampp/htdocs/farm/services/api/public_clima/cache.py)) com script atômico que avalia `current < limit` antes de incrementar a chave mensal.
- **Rollback em Falha Upstream:** `ClimaCache.rollback_quota_reservation` estorna a cota reservada via Lua caso a chamada ao provedor resulte em `TimeoutException`, `ProviderUnavailableError` ou erro de rede.
- **Integração no Orquestrador:** [dynamic_orchestrator.py](file:///opt/lampp/htdocs/farm/services/api/public_clima/dynamic_orchestrator.py) ajustado para respeitar limites específicos (WeatherAPI com cota contratada, OpenWeather com 30k, Open-Meteo e INMET com 0 por serem abertos).
- **Licenciamento Público:** Bloqueio mandatório de fallback para provedor alternativo não licenciado via `is_provider_authorized_for_public()`.

### 2.3. Isolamento Estrito de Chave Mestra e Recifragem
- **Eliminação de Fallback Silencioso:** Em [platform_weather_credentials.py](file:///opt/lampp/htdocs/farm/services/api/core/services/platform_weather_credentials.py), `_derive_platform_kek(version=2)` valida se o ambiente é `staging` ou `production` e levanta `RuntimeError` caso `settings.platform_credentials_master_key` não esteja configurada.
- **Validador de Startup:** Criado `PlatformWeatherCredentialsService.validate_master_key_configuration()`, exigindo chave mínima de 16 caracteres nesses ambientes.
- **Migração e Rotação:** Criado `reencrypt_all_credentials_to_canonical_kek()`, que decifra registros legados (v1 ou v2 antiga) e os recifra atomicamente com o KEK canônico v2, gerando trilha de auditoria em `admin_audit_logs`.

### 2.4. Recalibração da Matriz de Homologação
- **Dashboard Executivo:** [backoffice_agro_dashboard.py](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro_dashboard.py) atualizado:
  - Percentual de conclusão recalculado estritamente para **27.3%** (3 de 11 aprovados).
  - **Aprovados (3):** Item 5 (Parser XLS Oficial BIFF8/OLE2), Item 10 (Integridade dos Catálogos Globais) e Item 11 (Tipagem Estrita TypeScript e Testes Web/Agro).
  - **Em Validação (6):** Item 1 (Chave Mestra física), Item 2 (Licenciamento Provedores), Item 3 (Reserva Atômica Cotas), Item 4 (Proveniência DERAL), Item 8 (Sincronização Multi-Worker) e Item 9 (Retenção Base64).
  - **Pendentes (2):** Item 6 (PostgreSQL 16 Dedicado) e Item 7 (Redis 7 Real).

### 2.5. Esclarecimento de Proveniência e Política de Retenção DERAL
- **Docstrings e Contratos:** Em [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py):
  - Documentada a distinção entre proveniência declarada (URL terminando em `pr.gov.br`) e atestação criptográfica de origem (ausente, pendente de staging).
  - Formalizado o teto de 10 MB para documentos Base64 persistidos na tabela `deral_snapshots`.
  - Definida política de retenção ativa de 12 meses (ciclo agrícola anual de safra/entressafra), afastando imposições infundadas de guarda de 5 anos para boletins públicos semanais.

---

## 3. Arquivos Criados e Alterados

| Arquivo | Ação | Finalidade |
|---|---|---|
| `services/api/core/routers/auth.py` | Alterado | Adicionado endpoint `POST /api/v1/auth/heartbeat` com validação de sessão, CSRF e throttling. |
| `apps/agro/src/lib/auth/agro-auth.ts` | Alterado | Adicionado despachador de heartbeat com detecção de visibilidade e estado de rede. |
| `apps/agro/src/components/auth/session-heartbeat.tsx` | Criado | Componente cliente de heartbeat baseado em interação do usuário e foco de aba. |
| `apps/agro/src/app/layout.tsx` | Alterado | Injeção do `<SessionHeartbeat />` no layout global da PWA Agro. |
| `services/api/public_clima/cache.py` | Alterado | Adicionada reserva atômica via Lua (`reserve_monthly_quota`) e estorno (`rollback_quota_reservation`). |
| `services/api/public_clima/dynamic_orchestrator.py` | Alterado | Integração de reserva de cotas antes de upstream, rollback em exceção e checagem de licença pública. |
| `services/api/core/services/platform_weather_credentials.py` | Alterado | Bloqueio de fallback em staging/prod, validador de chave mestra e método de recifragem KEK v2. |
| `services/api/core/routers/backoffice_agro_dashboard.py` | Alterado | Correção da matriz de homologação para 27.3% e detalhamento de evidências auditadas. |
| `services/api/core/services/deral_snapshot_service.py` | Alterado | Documentação forense de proveniência declarada, limites de payload e política de retenção. |
| `Dockerfile.agro` | Criado | Imagem conteinerizada da PWA Agro (Next.js 16) para staging isolado. |
| `infrastructure/staging/docker-compose.agro-staging.yml` | Criado | Stack descartável de staging (Postgres 16, Redis 7, MinIO, 2 workers API, Web, Agro) vinculados a `127.0.0.1`. |
| `infrastructure/staging/.env.staging.example` | Criado | Template de variáveis de ambiente sem segredos hardcoded. |
| `scripts/staging/validate_isolation.py` | Criado | Script de validação que impede conexão de staging com RDS, ElastiCache ou S3 de produção. |
| `scripts/staging/up.sh` | Criado | Script de inicialização controlada de staging (validação + subida + migrations). |
| `scripts/staging/down.sh` | Criado | Script de descarte e destruição completa dos volumes e containers de staging. |
| `services/api/tests/unit/core/test_backoffice_agro_01h1.py` | Criado | Suíte com 15 testes cobrindo heartbeat, CSRF, cotas, chaves mestras e isolamento. |
| `services/api/tests/unit/core/test_backoffice_agro_01f.py` | Alterado | Alinhamento de asserções para o status auditado EM VALIDAÇÃO na proveniência DERAL. |
| `README.md` | Alterado | Documentação da feature e bugfixes na seção `## Features`. |

---

## 4. Evidências dos Testes Locais

### 4.1. Suíte Dedicada AGRO-ADMIN-01H1 (15 Testes)
Executada via comando:
```bash
PYTHONPATH=services/api services/api/.venv/bin/python3.10 -m pytest services/api/tests/unit/core/test_backoffice_agro_01h1.py -v
```
**Resultado:** **15 passed in 7.49s (100% de sucesso)**

```text
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_heartbeat_com_cookie_httponly_sucesso PASSED [  6%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_heartbeat_rate_limiting_memoria PASSED [ 13%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_heartbeat_rejeita_csrf_invalido PASSED [ 20%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_heartbeat_rejeita_sessao_expirada PASSED [ 26%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_heartbeat_rejeita_usuario_bloqueado PASSED [ 33%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_clima_cache_atomic_quota_reservation_and_rollback PASSED [ 40%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_clima_cache_quota_limit_exceeded PASSED [ 46%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_provider_public_authorization PASSED [ 53%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_master_key_strict_requirement_in_staging_and_production PASSED [ 60%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_master_key_allowed_in_development PASSED [ 66%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_reencrypt_credentials_kek_migration PASSED [ 73%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_matriz_homologacao_estrita_27_pct PASSED [ 80%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_validate_staging_config_rejeita_producao PASSED [ 86%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_validate_staging_config_rejeita_rds_ou_elasticache PASSED [ 93%]
services/api/tests/unit/core/test_backoffice_agro_01h1.py::test_validate_staging_config_valido PASSED [100%]
```

### 4.2. Regressão Integrada das Fases Afetadas (01F + 01H1 — 20 Testes)
```bash
PYTHONPATH=services/api services/api/.venv/bin/python3.10 -m pytest services/api/tests/unit/core/test_backoffice_agro_01f.py services/api/tests/unit/core/test_backoffice_agro_01h1.py -v
```
**Resultado:** **20 passed in 10.81s (100% de sucesso)**

### 4.3. Typecheck Estrito TypeScript (Frontends)
```bash
pnpm --filter agro exec tsc --noEmit && pnpm --filter web exec tsc --noEmit
```
**Resultado:** **Código de saída 0 (zero erros de tipagem em ambos os projetos Next.js 16.1.6)**

---

## 5. Arquitetura do Staging Preparado

A topologia preparada em [docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml) é totalmente efêmera e autocontida:

```mermaid
graph TD
    subgraph Staging_Isolado ["Staging Isolado (127.0.0.1 / Rede staging_agro_net)"]
        Web["Backoffice Web (Next.js)<br/>Porta 127.0.0.1:3001"]
        Agro["PWA Agro (Next.js)<br/>Porta 127.0.0.1:3005"]
        Worker1["API Worker 1 (FastAPI)<br/>Porta 127.0.0.1:8001"]
        Worker2["API Worker 2 (FastAPI)<br/>Porta 127.0.0.1:8002"]
        PG["PostgreSQL 16 Dedicado<br/>Porta 127.0.0.1:5433"]
        RD["Redis 7 Dedicado<br/>Porta 127.0.0.1:6380"]
        MinIO["MinIO Storage Local<br/>Portas 127.0.0.1:9002 / 9003"]
    end

    Web --> Worker1
    Agro --> Worker1
    Worker1 --> PG
    Worker1 --> RD
    Worker1 --> MinIO
    Worker2 --> PG
    Worker2 --> RD
    Worker2 --> MinIO
```

### Características de Isolamento:
1. **Network Binding:** Todos os mapeamentos de portas estão explicitamente vinculados a `127.0.0.1` (sem binding em `0.0.0.0`), impedindo acessos externos a partir da rede local ou internet.
2. **Volumes Nomeados:** Volumes segregados `deepfarms_staging_postgres_data`, `deepfarms_staging_redis_data` e `deepfarms_staging_minio_data`.
3. **Limites de Recursos (cgroups):** Cada serviço possui tetos de CPU (0.5 a 1.0) e memória (512 MB a 1024 MB).
4. **Healthchecks Nativos:** Todos os serviços possuem probes de saúde (`pg_isready`, `redis-cli ping`, `curl`) com dependências orquestradas via `service_healthy`.

---

## 6. Inventário de Variáveis e Segredos de Staging

O arquivo [.env.staging.example](file:///opt/lampp/htdocs/farm/infrastructure/staging/.env.staging.example) padroniza os parâmetros necessários:

| Variável | Obrigatória | Finalidade | Regra de Segurança |
|---|---|---|---|
| `ENVIRONMENT` | Sim | Identificador de ambiente | Deve ser estritamente `staging`. |
| `APP_ENV` | Sim | Identificador da aplicação | Deve ser estritamente `staging`. |
| `STAGING_DB_USER` | Sim | Usuário PostgreSQL | Padrão: `staging_agro`. |
| `STAGING_DB_PASSWORD` | Sim | Senha do banco staging | Gerada aleatoriamente (mínimo 16 caracteres). |
| `STAGING_DB_NAME` | Sim | Nome da base de dados | Padrão: `deepfarms_agro_staging`. |
| `STAGING_DB_HOST` | Sim | Host do PostgreSQL | Restrito a `127.0.0.1` ou `staging-postgres`. |
| `STAGING_DB_PORT` | Sim | Porta local do banco | `5433` (evita conflito com dev 5432). |
| `STAGING_REDIS_PASSWORD` | Sim | Senha do Redis 7 | Mínimo 16 caracteres, auth compulsória. |
| `STAGING_REDIS_HOST` | Sim | Host do Redis | Restrito a `127.0.0.1` ou `staging-redis`. |
| `STAGING_REDIS_PORT` | Sim | Porta local do Redis | `6380` (evita conflito com dev 6379). |
| `STAGING_JWT_SECRET_KEY` | Sim | Assinatura JWT | Mínimo 32 caracteres gerados com `openssl rand -hex 32`. |
| `STAGING_PLATFORM_CREDENTIALS_MASTER_KEY` | Sim | KEK mestra v2 da plataforma | Mínimo 32 caracteres gerados com `openssl rand -hex 32`. |
| `STAGING_INTEGRATIONS_SECRET_KEY` | Sim | Assinatura de integrações | Mínimo 32 caracteres. |
| `STAGING_MINIO_USER` | Sim | Root user do MinIO | `staging_minio_admin`. |
| `STAGING_MINIO_PASSWORD` | Sim | Senha do MinIO | Mínimo 16 caracteres. |

---

## 7. Verificação de Isolamento e Segurança

O script [validate_isolation.py](file:///opt/lampp/htdocs/farm/scripts/staging/validate_isolation.py) foi testado e aprovado com as seguintes proteções:
- **Rejeição de Hosts de Nuvem:** Expressões regulares rejeitam strings que contenham `*.rds.amazonaws.com`, `*.cache.amazonaws.com`, `*.s3.amazonaws.com` ou termos contendo `production`, `prod-db` e `prod-redis`.
- **Rejeição de Buckets de Produção:** Rejeita qualquer bucket contendo `prod` ou `production`.
- **Validação de Força de Chaves:** Rejeita chaves mestras e JWT com menos de 32 caracteres ou que ainda contenham o texto de placeholder (`gerar_com`).
- **Validação de Portas:** Assegura que staging opere em portas dedicadas (5433, 6380, 8001, 8002, 3001, 3005).

---

## 8. Procedimento de Inicialização Segura (01H2)

> **ATENÇÃO:** O comando abaixo NÃO foi executado na fase 01H1, em cumprimento estrito às restrições do projeto. Fica documentado para execução exclusiva na fase 01H2 após autorização.

### Pré-requisitos:
1. Copiar o modelo de ambiente:
   ```bash
   cp infrastructure/staging/.env.staging.example infrastructure/staging/.env.staging
   ```
2. Gerar segredos fortes no arquivo `infrastructure/staging/.env.staging`:
   ```bash
   # Gerar senhas e chaves com openssl
   openssl rand -hex 24 # para senhas de banco e redis
   openssl rand -hex 32 # para JWT e PLATFORM_CREDENTIALS_MASTER_KEY
   ```

### Execução via Script Automatizado:
```bash
./scripts/staging/up.sh
```

### O que o script realiza de forma sequencial e controlada:
1. Executa `python3 scripts/staging/validate_isolation.py --env-file infrastructure/staging/.env.staging`.
2. Sobe os containers de infraestrutura: `staging-postgres`, `staging-redis` e `staging-minio`.
3. Aguarda os healthchecks estarem saudáveis (`pg_isready` e `redis-cli ping`).
4. Executa as migrações Alembic estritamente apontadas para a base de staging:
   ```bash
   PYTHONPATH=services/api DATABASE_URL="postgresql+asyncpg://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@127.0.0.1:5433/${STAGING_DB_NAME}" \
   services/api/.venv/bin/alembic -c services/api/alembic.ini upgrade head
   ```
5. Inicializa os containers de aplicação: `staging-api-worker-1`, `staging-api-worker-2`, `staging-web` e `staging-agro`.

---

## 9. Procedimento de Rollback e Descarte

Para descartar o ambiente de staging a qualquer momento, sem deixar resíduos:
```bash
./scripts/staging/down.sh
```
O script executa:
1. `docker compose -f infrastructure/staging/docker-compose.agro-staging.yml down --volumes --remove-orphans`.
2. Remoção forçada dos volumes Docker isolados (`deepfarms_staging_postgres_data`, `deepfarms_staging_redis_data`, `deepfarms_staging_minio_data`).
3. Restauração imediata do estado original da máquina.

---

## 10. Pendências Não Resolvidas

As seguintes pendências foram conscientemente mantidas para resolução na fase 01H2 (Homologação Integrada):
1. **Instância PostgreSQL Real em Execução:** O schema e as migrações foram validados sintaticamente, mas o container real não foi iniciado em 01H1 por restrição de escopo.
2. **Concorrência em Cluster Redis Real:** A lógica atômica em Lua foi coberta por testes unitários com mocks; a validação contra o daemon Redis 7 real em múltiplos containers ocorrerá em staging.
3. **Multi-Worker ASGI Concorrente:** Os dois processos Uvicorn (portas 8001 e 8002) estão configurados na stack de staging para testar a invalidação de cache via Pub/Sub na fase 01H2.
4. **Upload de Planilha DERAL Real em Staging:** Importação de planilha oficial conectada com rede real de homologação.

---

## 11. Critérios de Entrada para AGRO-ADMIN-01H2

Para autorizar o início da fase **AGRO-ADMIN-01H2**, os seguintes critérios devem estar satisfeitos:
1. [x] Heartbeat seguro da PWA Agro implementado e testado localmente.
2. [x] Reserva atômica de cotas climáticas via script Lua implementada e testada.
3. [x] Fallback de `JWT_SECRET_KEY` eliminado em staging/produção com teste de recusa.
4. [x] Matriz de homologação do dashboard ajustada com rigor para 27.3%.
5. [x] Artefatos de staging (`docker-compose`, `.env.staging.example`, scripts de validação, `up.sh` e `down.sh`) criados e validados.
6. [x] Suítes de testes unitários locais aprovadas com 100% de sucesso (15/15 em 01H1 e 20/20 em 01F+01H1).
7. [x] Verificação estrita de TypeScript em `apps/agro` e `apps/web` sem nenhum erro.
8. [ ] **Autorização expressa da liderança técnica para inicialização dos containers de staging e execução de migrações (requisito de liberação da 01H2).**

---

## 12. Veredicto Final

### **GO COM RESSALVAS**

- **Justificativa do GO:** Todas as falhas críticas e desvios de segurança identificados na auditoria AGRO-ADMIN-01G foram plenamente corrigidos, isolados e validados por suítes de testes unitários automatizados. Os frontends Next.js compilam perfeitamente sem erros de tipagem. A infraestrutura de staging foi estruturada com isolamento rigoroso (rede privada, binding em loopback, volumes nomeados descartáveis e script validador anti-vazamento).
- **Ressalvas:**
  1. Nenhum container de staging foi subido e nenhuma migration foi executada contra banco externo nesta fase, em cumprimento às regras de governança.
  2. A promoção de qualquer um dos 8 itens pendentes da matriz de homologação para o estado `APROVADO` só poderá ocorrer após a execução e comprovação na fase 01H2.

> **PARADA DE EXECUÇÃO:** Conforme determinado nas restrições da fase AGRO-ADMIN-01H1, o trabalho é interrompido neste ponto. Não foram realizados deploys, commits, pushes ou inicializações automáticas. A transição para a fase AGRO-ADMIN-01H2 aguarda autorização formal.
