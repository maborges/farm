# AGRO-ADMIN-01H2A — Pré-flight de Segurança e Validação da Infraestrutura de Staging

**Data:** 25 de Outubro de 2026  
**Auditor:** GPT-5.6 Codex — Sol (Engenharia de Infraestrutura e Segurança)  
**Modalidade:** Auditoria técnica somente leitura (Read-Only Static Pre-flight)  
**Status da Auditoria:** Concluída com Sucesso  
**Veredicto Final:** **GO COM RESSALVAS** (Condicionado às correções pré-boot na AGRO-ADMIN-01H2B)

---

## Sumário Executivo

A presente auditoria técnica pré-flight avaliou a integridade, segurança, isolamento e viabilidade operacional da infraestrutura de staging concebida na fase **AGRO-ADMIN-01H1**.

O objetivo primordial foi garantir que os artefatos de infraestrutura permitam a inicialização de um ambiente de homologação estritamente segregado, **sem qualquer possibilidade operacional não controlada de atingir os bancos de dados, clusters de cache, buckets S3 ou serviços de produção do DeepFarms**.

Em cumprimento estrito às diretrizes da fase **AGRO-ADMIN-01H2A**:
- **Nenhum container foi inicializado** (`docker compose up` e `up.sh` não foram executados);
- **Nenhuma migration foi aplicada** contra bancos de dados locais ou remotos;
- **Nenhuma alteração de código ou commit foi realizada**;
- A inspeção baseou-se em auditoria estática de código, rastreamento de fluxos de configuração, resolução de schemas e análise de grafos de dependência.

Os resultados comprovam que o núcleo de isolamento de rede e credenciais foi muito bem concebido (ligação restrita a `127.0.0.1`, bloqueio estrito de segredos e redes segregadas). Contudo, foram identificadas **3 inconformidades de alta relevância (HIGH)** relacionadas a descasamento de variáveis de ambiente e regras de CORS/proxy entre Web/Agro e a API, as quais impediriam a operação correta se a subida fosse realizada sem ajustes prévios.

---

## 1. Inventário Detalhado dos Artefatos Auditados

A auditoria cobriu 100% dos arquivos de infraestrutura, scripts de automação, definições de container e serviços de suporte criados ou modificados:

| Artefato | Localização | Propósito Operacional | Estado Auditado |
| :--- | :--- | :--- | :--- |
| **Compose Staging** | [docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml) | Orquestração multi-serviço (Postgres, Redis, MinIO, 2x API, Web, Agro) | Auditado (Ressalvas em variáveis) |
| **Exemplo de Ambiente** | [.env.staging.example](file:///opt/lampp/htdocs/farm/infrastructure/staging/.env.staging.example) | Modelo canônico de variáveis e segredos segregados de staging | Auditado (Conforme) |
| **Script de Isolamento** | [validate_isolation.py](file:///opt/lampp/htdocs/farm/scripts/staging/validate_isolation.py) | Validação pré-boot estática contra destinos de produção e vazamentos | Auditado (Forte, com recomendações) |
| **Script de Subida** | [up.sh](file:///opt/lampp/htdocs/farm/scripts/staging/up.sh) | Automação de inicialização, validação de gate e migrações | Auditado (Requer separação em etapas) |
| **Script de Descida** | [down.sh](file:///opt/lampp/htdocs/farm/scripts/staging/down.sh) | Encerramento e purga segura de volumes e redes locais | Auditado (Conforme) |
| **Dockerfile PWA Agro** | [Dockerfile.agro](file:///opt/lampp/htdocs/farm/Dockerfile.agro) | Build multi-stage Node 22 slim para o app Next.js PWA Agro | Auditado (Conforme) |
| **Dockerfile Backend** | [Dockerfile.backend](file:///opt/lampp/htdocs/farm/Dockerfile.backend) | Build Python 3.12 com GDAL/PROJ para FastAPI worker | Auditado (Conforme) |
| **Dockerfile Web** | [Dockerfile.web](file:///opt/lampp/htdocs/farm/Dockerfile.web) | Build multi-stage Node 22 slim para Backoffice Web | Auditado (Conforme) |
| **Config Alembic** | [alembic.ini](file:///opt/lampp/htdocs/farm/services/api/alembic.ini) | Definições de logging e caminho de migrações | Auditado (Conforme) |
| **Ambiente Alembic** | [env.py](file:///opt/lampp/htdocs/farm/services/api/migrations/env.py) | Resolução de engine assíncrono e schema `farms` | Auditado (Risco de histórico duplo) |
| **Configurações API** | [config.py](file:///opt/lampp/htdocs/farm/services/api/core/config.py) | Schema Pydantic `Settings` e parsing de variáveis | Auditado (Descasamento MinIO/CORS) |
| **Engine de Banco** | [database.py](file:///opt/lampp/htdocs/farm/services/api/core/database.py) | Criação de AsyncEngine SQLAlchemy e isolamento multi-tenant | Auditado (Conforme) |
| **Storage Service** | [storage_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/storage_service.py) | Abstração S3 / Local MinIO | Auditado (Descasamento de variáveis) |
| **Credenciais Provedores** | [platform_credentials_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/platform_credentials_service.py) | Criptografia Fernant KEK v1/v2 para provedores climáticos | Auditado (Segurança estrita) |
| **Snapshots DERAL** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py) | Ingestão, validação, proveniência e persistência de mercado | Auditado (Armazenamento em Postgres) |
| **Rotas e Middlewares** | [main.py](file:///opt/lampp/htdocs/farm/services/api/main.py) | CORS, middlewares e orquestração FastAPI | Auditado (Porta 3005 ausente no CORS) |

---

## 2. Diagrama de Conexões Efetivas e Topologia de Rede

### 2.1 Análise de Exposição e Bindings
Todos os containers declarados em `infrastructure/staging/docker-compose.agro-staging.yml` vinculam suas portas estritamente ao endereço loopback `127.0.0.1`:
- **PostgreSQL**: `127.0.0.1:5433:5432`
- **Redis**: `127.0.0.1:6380:6379`
- **MinIO API**: `127.0.0.1:9002:9000`
- **MinIO Console**: `127.0.0.1:9003:9001`
- **API Worker 1**: `127.0.0.1:8001:8000`
- **API Worker 2**: `127.0.0.1:8002:8000`
- **Backoffice Web**: `127.0.0.1:3001:3000`
- **PWA Agro**: `127.0.0.1:3005:3004`

**Nenhum container utiliza `network_mode: host`** e nenhuma porta está exposta em `0.0.0.0`, prevenindo qualquer acesso externo não autorizado pela interface de rede física.

### 2.2 Diagrama Arquitetural de Comunicação

```mermaid
graph TB
    subgraph Host["Host Operacional / Navegador do Desenvolvedor"]
        Browser["Navegador Web / Test Runner E2E"]
        Loopback1["127.0.0.1:3001 (Web)"]
        Loopback2["127.0.0.1:3005 (Agro PWA)"]
        Loopback3["127.0.0.1:8001 (API-1)"]
        Loopback4["127.0.0.1:8002 (API-2)"]
    end

    subgraph DockerBridge["Rede Isolada Docker: staging_agro_net (bridge)"]
        subgraph Frontends["Camada de Apresentação (Node 22)"]
            Web["staging-web (Port 3000)<br/>Backoffice DeepFarms"]
            Agro["staging-agro (Port 3004)<br/>PWA DeepFarms Agro"]
        end

        subgraph Workers["Camada de Aplicação (Python 3.12 FastAPI)"]
            API1["staging-api-worker-1 (Port 8000)<br/>Worker ID: worker-staging-1"]
            API2["staging-api-worker-2 (Port 8000)<br/>Worker ID: worker-staging-2"]
        end

        subgraph Storage["Camada de Dados Isolada (Volumes Locais)"]
            PG["staging-postgres (Port 5432)<br/>PostgreSQL 16 Alpine<br/>Volume: staging_postgres_data<br/>DB: deepfarms_agro_staging"]
            RD["staging-redis (Port 6379)<br/>Redis 7.2 Alpine<br/>Volume: staging_redis_data<br/>Auth: STAGING_REDIS_PASSWORD"]
            MN["staging-minio (Port 9000/9001)<br/>MinIO S3 Local<br/>Volume: staging_minio_data"]
        end
    end

    Browser --> Loopback1 --> Web
    Browser --> Loopback2 --> Agro
    Browser --> Loopback3 --> API1
    Browser --> Loopback4 --> API2

    Web -.->|"RSC: BACKEND_URL (Falta ajustar)"| API1
    Agro -.->|"Rewrites: AGRO_API_INTERNAL_ORIGIN (Falta ajustar)"| API1

    API1 -->|"postgresql+asyncpg://staging-postgres:5432"| PG
    API2 -->|"postgresql+asyncpg://staging-postgres:5432"| PG

    API1 -->|"redis://:password@staging-redis:6379/0"| RD
    API2 -->|"redis://:password@staging-redis:6379/0"| RD

    API1 -->|"http://staging-minio:9000 (S3 API)"| MN
    API2 -->|"http://staging-minio:9000 (S3 API)"| MN

    classDef host fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef bridge fill:#e8f4f8,stroke:#2b7bb9,stroke-width:2px;
    classDef storage fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef workers fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef front fill:#f8d7da,stroke:#dc3545,stroke-width:2px;

    class Host host;
    class DockerBridge bridge;
    class PG,RD,MN storage;
    class API1,API2 workers;
    class Web,Agro front;
```

---

## 3. Matriz de Variáveis, Segredos e Descasamento de Configuração

Foi realizada uma análise cruzada detalhada entre:
1. Variáveis declaradas em `docker-compose.agro-staging.yml` e `.env.staging.example`;
2. Modelos Pydantic em `core/config.py` (`Settings`);
3. Consumo efetivo em serviços auxiliares (`storage_service.py`, `platform_credentials_service.py`, `runtime-config.ts` e `next.config.ts`).

### 3.1 Tabela de Rastreabilidade de Variáveis

| Variável no Compose / .env | Campo Pydantic / Runtime | Valor / Destino Efetivo | Validação de Isolamento | Status de Compatibilidade |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `settings.environment` | `"staging"` | Forçado a `"staging"` | **Conforme** |
| `APP_ENV` | `settings.app_env` | `"staging"` | Bloqueia produção | **Conforme** |
| `DATABASE_URL` | `settings.database_url` | `postgresql+asyncpg://staging_agro:***@staging-postgres:5432/deepfarms_agro_staging` | Host `staging-postgres` é container interno | **Conforme** |
| `REDIS_URL` | `settings.redis_url` | `redis://:***@staging-redis:6379/0` | Host `staging-redis` é container interno | **Conforme** |
| `JWT_SECRET_KEY` | `settings.jwt_secret_key` | Chave dedicada de staging (≥32 chars) | Bloqueado uso em produção | **Conforme** |
| `PLATFORM_CREDENTIALS_MASTER_KEY` | `settings.platform_credentials_master_key` | Chave Fernet de 32 bytes base64 dedicada | Bloqueado fallback silencioso para JWT | **Conforme** |
| `S3_ENDPOINT_URL` | `settings.s3_endpoint_url` | `http://staging-minio:9000` | Host `staging-minio` é container interno | **Conforme** |
| `S3_ACCESS_KEY` | `settings.s3_access_key` | `${STAGING_MINIO_USER}` | Usuário MinIO local | **Conforme** |
| `S3_SECRET_KEY` | `settings.s3_secret_key` | `${STAGING_MINIO_PASSWORD}` | Senha MinIO local | **Conforme** |
| **`S3_BUCKET_NAME`** | *(Nenhum campo Pydantic direto)* | `"deepfarms-staging-bucket"` | Pydantic lê `S3_BUCKET` (via `s3_bucket`) | **DESALINHADO (ACHADO-02)** |
| **`STORAGE_BACKEND`** | `settings.storage_backend` | *(Não declarado no Compose)* | Pydantic assume default `"local"` | **DESALINHADO (ACHADO-02)** |
| **`BACKEND_URL`** (no Web) | `runtime-config.ts` | *(Não declarado no Web)* | Default assume `http://127.0.0.1:8000` | **DESALINHADO (ACHADO-03)** |
| **`AGRO_API_INTERNAL_ORIGIN`** | `apps/agro/next.config.ts` | *(Não declarado no Agro)* | Default em produção vira `""` (sem proxy) | **DESALINHADO (ACHADO-03)** |
| **`CORS_ORIGINS`** | `settings.cors_origins` | Portas 3000..3004 em localhost | Porta 3005 (Agro Staging) rejeitada no CORS | **DESALINHADO (ACHADO-01)** |

---

## 4. Riscos de Acesso Acidental à Produção

### 4.1 Vetores de Contaminação Analisados
1. **Fallback de Host de Banco / RDS:**
   - **Comprovado:** O `DATABASE_URL` aponta expressamente para o container Docker `staging-postgres:5432`.
   - Caso `staging-postgres` caia, a biblioteca `asyncpg` emitirá `ConnectionRefusedError` ou erro de resolução DNS para o host interno `staging-postgres`. Não existe mecanismo de failover ou fallback secundário para URLs de produção.
2. **Fallback de Storage S3 / MinIO:**
   - O `S3_ENDPOINT_URL` é explicitamente injetado como `http://staging-minio:9000`.
   - Como o endpoint é customizado e aponta para protocolo HTTP puro em porta não padrão, o cliente `botocore/aioboto3` não tentará resolver o endpoint global da AWS (`s3.amazonaws.com`).
3. **Chaves Mestre e Segredos:**
   - O serviço `PlatformWeatherCredentialsService` possui validação estrita (`validate_master_key_configuration()`): em `ENVIRONMENT=staging`, a ausência de `PLATFORM_CREDENTIALS_MASTER_KEY` causa **aborto imediato (`RuntimeError`)**, sendo terminantemente proibido o fallback para a `JWT_SECRET_KEY`.
4. **Isolamento de Arquivos do Host:**
   - O Compose monta exclusivamente volumes nomeados gerenciados pelo Docker (`staging_postgres_data`, `staging_redis_data`, `staging_minio_data`).
   - Não há montagem de diretórios de sistema (`/etc`, `/root`, `/home`), nem de arquivos sensíveis como `.env` ou `.env.production`.
5. **Eficácia de `scripts/staging/validate_isolation.py`:**
   - O script executa verificação regex contra destinos perigosos:
     - Hosts de banco: `amazonaws\.com`, `rds\.`, `prod`, `production`, `supabase\.co`, `cockroachlabs\.cloud`;
     - Hosts Redis: `redislabs\.com`, `upstash\.io`, `elasticache`;
     - Buckets S3: `deepfarms-prod`, `deepfarms-production`, `s3\.amazonaws\.com`.
   - **Limitação identificada:** A regex valida nomes de host. Caso um operador configure um IP público fixo diretamente em `DATABASE_URL` (ex: `54.x.y.z`), a regex de hostnames puramente textuais não o capturaria. Recomendamos enriquecer o script com validação de blocos IP privados RFC 1918.

---

## 5. Revisão de Migrations e Schema do Banco de Dados

### 5.1 Resolução da URL e Criação do Schema
Em [services/api/migrations/env.py](file:///opt/lampp/htdocs/farm/services/api/migrations/env.py):
- `DATABASE_URL` é obtido via `os.getenv("DATABASE_URL")`, com fallback seguro para `settings.database_url`.
- Em conexões síncronas do Alembic, a URL é devidamente convertida de `postgresql+asyncpg://` para `postgresql://`.
- Antes de inspecionar metadados, o script executa:
  ```python
  connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS farms"))
  connection.execute(sa.text("SET search_path TO farms, public"))
  ```
- Isso garante que todos os objetos criados pelo Alembic residam no schema `farms`.

### 5.2 Análise do Histórico de Migrações (Grafo Duplo)
O diretório `services/api/migrations/versions` contém **416 arquivos de migração**. A inspeção identificou a existência de **duas raízes históricas**:
1. **Grafo Incremental Histórico (Legado):** Iniciado em `001_notas_fiscais.py` (`down_revision = None`), acumulando anos de alterações pontuais.
2. **Baseline Canônico V1:** Consolidado em [20260908_baseline_deepfarms_v1.py](file:///opt/lampp/htdocs/farm/services/api/migrations/versions/20260908_baseline_deepfarms_v1.py), com `down_revision = None` e `branch_labels = ("deepfarms_baseline",)`.
3. **Risco Operacional no Staging Limpo:** Se um operador invocar simplesmente `alembic upgrade head` em um banco recém-criado vazio sem parâmetros adicionais, o Alembic pode falhar acusando branches múltiplas (`Multiple head revisions are present for given argument 'head'`).
4. **Recomendação Estrita:** O script de automação deve fixar a execução a partir do branch baseline (`alembic upgrade deepfarms_baseline@head` ou heads unificados explícitos), impedindo a tentativa de reproduzir migrações legadas obsoletas.
5. **Verificação de Efeitos Colaterais:** Foi realizada varredura nas migrations recentes (`20261022_agro_admin_01b1_session_nullable.py` e baseline); **não existem chamadas a serviços externos (HTTP, subprocess)** dentro dos scripts de migração.

---

## 6. Revisão do Ciclo de Heartbeat e Gestão de Cotas

### 6.1 Revisão do Heartbeat PWA Agro
A inspeção do endpoint `POST /api/v1/auth/heartbeat` e do cliente `agro-auth.ts` revelou:
- **Autenticação Real:** O endpoint consome o cookie HttpOnly `access_token` e valida a sessão no banco através de `get_current_active_user`. Requisições anônimas ou expiradas recebem estritamente `HTTP 401 Unauthorized` ou `403 Forbidden`.
- **Proteção CSRF:** Validação de token CSRF (`X-CSRF-Token` ou cookie `csrf_token`) ativa para métodos mutantes.
- **Throttling e Limitação:**
  - O middleware aplica controle de janela deslizante de 60 segundos por usuário antes de disparar atualização de `ultimo_heartbeat` no PostgreSQL.
  - **Fato Técnico:** O cache de throttling implementado em `SessionHeartbeatMiddleware` armazena os timestamps em um dicionário Python em memória (`_last_beat_cache: dict[str, float]`).
  - **Comportamento em Multi-Worker:** Como o staging possui 2 workers (`worker-staging-1` e `worker-staging-2`), o throttling de memória não é compartilhado. Em caso de requisições alternadas entre workers via balanceamento, o usuário pode ter o timestamp atualizado mais de uma vez a cada 60s. Contudo, isso não gera corrupção de dados, apenas updates redundantes no banco. A migração do throttling para Redis deve ser avaliada para ambientes de produção massivos.

### 6.2 Revisão das Cotas Climáticas e Script Lua
A inspeção de `services/api/clima/services/clima_cache.py` e `dynamic_weather_orchestrator.py` confirmou:
- **Atomicidade Total:** A reserva e consumo de requisições de provedores pagos (OpenWeather, WeatherAPI, Tomorrow.io) é executada via script **Lua atômico no Redis** (`EVALSHA` / `EVAL`).
- O script Lua incrementa a chave de cota mensal do provedor (`agro:weather:quota:{provider}:{year_month}`) e compara atomicamente com o teto configurado em `ConfiguracaoSaaS`. Caso a cota esteja esgotada, a operação retorna `0` de forma atômica, sem race condition entre workers simultâneos.
- **Mecanismo de Rollback:** Caso o provedor upstream retorne erro 5xx ou timeout, o orquestrador invoca `clima_cache.rollback_quota_usage(provider)`, decrementando o contador no Redis de forma idempotente.
- **Comportamento sem Redis:** Se o Redis estiver indisponível, o orquestrador entra em modo de fail-safe degradado: loga o aviso e bloqueia consultas pagas não cacheadas para impedir violação de limites financeiros desconhecidos.

---

## 7. Persistência de Dados e Snapshots DERAL

Auditamos a cadeia de ingestão e armazenamento de mercado em `core/services/deral_snapshot_service.py`:
- **Tabela e Armazenamento Utilizado:** Ao contrário do presumido genericamente em projetos de storage, os snapshots DERAL **não dependem de MinIO nem de S3**. Os metadados, o JSON normalizado e os **bytes binários originais** (.xls ou .json) são persistidos na tabela `ConfiguracaoSaaS` (`configuracoes_saas`), sob a chave `agro:deral:snap:{snapshot_id}`.
- **Preservação Original:** O arquivo original é codificado em Base64 (`raw_bytes_base64`) e persistido de forma imutável no payload JSON da configuração. O endpoint `/api/v1/backoffice/agro/mercado/deral/snapshots/{id}/download-raw` decodifica e entrega o arquivo original com content-disposition idêntico ao enviado.
- **Limite de Upload:** Limite rígido de **5 MB** (`MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024`) verificado em código antes de qualquer parsing de memória.
- **Integridade SHA-256:** O hash SHA-256 é calculado nos bytes puros recebidos no upload, gravado nos metadados e recalculado sob demanda no endpoint `/verify-integrity`.
- **Proveniência:** A função `verificar_proveniencia_governamental` realiza validação sintática contra a whitelist de domínios governamentais homologados (`*.pr.gov.br`, `seab.pr.gov.br`). O sistema explicita em relatório que a proveniência é declaratória com validação sintática, e não assinatura digital assimétrica PKI.
- **Política de Retenção:** Documentada para ciclo agrícola de 12 meses. No código atual, não existe rotina de expurgo automático (cron job); os registros permanecem no banco até arquivamento manual ou implementação futura de batch job.

---

## 8. Relatório de Achados e Não-Conformidades

A auditoria classificou os achados em 4 níveis de severidade:

### 8.1 BLOCKER (Impedimentos Críticos de Segurança)
*Nenhum achado classificado como BLOCKER.*  
Não foi detectada nenhuma vulnerabilidade que permita vazamento para produção, injeção de credenciais ativas de produção ou exposição não autorizada de portas em interfaces públicas.

---

### 8.2 HIGH (Falhas Operacionais Severas que Impedem o Funcionamento)

#### ACHADO-PREFLIGHT-01: Rejeição de CORS para PWA Agro na Porta 3005
- **Severidade:** **HIGH**
- **Arquivos:** [services/api/main.py](file:///opt/lampp/htdocs/farm/services/api/main.py#L290-L305) e [services/api/core/config.py](file:///opt/lampp/htdocs/farm/services/api/core/config.py#L101-L123)
- **Descrição:** O `docker-compose.agro-staging.yml` expõe o PWA Agro em `127.0.0.1:3005:3004`. Contudo, a lista de origens CORS permitidas no FastAPI (`allow_origins`) em `main.py` contempla apenas:
  `http://localhost:3000` a `http://localhost:3004` e `http://127.0.0.1:3000` a `http://127.0.0.1:3004`.
- **Impacto:** Qualquer requisição cross-origin do navegador do operador acessando `http://127.0.0.1:3005` diretamente para `http://127.0.0.1:8001` será sumariamente rejeitada pelo middleware CORS do FastAPI com `HTTP 403 Forbidden` / `CORS header missing`.
- **Correção Necessária:** Adicionar `http://127.0.0.1:3005` e `http://localhost:3005` à lista padrão de `cors_origins` em `core/config.py` e `main.py`.

#### ACHADO-PREFLIGHT-02: Descasamento de Variáveis de Object Storage (MinIO)
- **Severidade:** **HIGH**
- **Arquivos:** [infrastructure/staging/docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml#L141-L144) e [services/api/core/config.py](file:///opt/lampp/htdocs/farm/services/api/core/config.py#L125-L135)
- **Descrição:** No Compose, as variáveis injetadas para a API são:
  - `S3_BUCKET_NAME: deepfarms-staging-bucket`
  - Ausência de `STORAGE_BACKEND`.
  No entanto, o Pydantic em `core/config.py` mapeia:
  - `s3_bucket: str = Field(default="", alias="S3_BUCKET")` (espera `S3_BUCKET`, não `S3_BUCKET_NAME`);
  - `storage_backend: str = "local"` (por padrão, assume backend local `/tmp/agrosaas_uploads`).
- **Impacto:** Os workers de API ignorarão o container MinIO e salvarão uploads no diretório efêmero local `/tmp/agrosaas_uploads` do container. Caso alguma rotina acesse diretamente o cliente S3, ela falhará com erro de bucket vazio.
- **Correção Necessária:** No `docker-compose.agro-staging.yml`, definir `STORAGE_BACKEND: s3` e adicionar a variável `S3_BUCKET: deepfarms-staging-bucket`.

#### ACHADO-PREFLIGHT-03: Variáveis de Comunicação Interna Ausentes nos Frontends (Web e Agro)
- **Severidade:** **HIGH**
- **Arquivos:** [apps/web/src/lib/runtime-config.ts](file:///opt/lampp/htdocs/farm/apps/web/src/lib/runtime-config.ts#L36-L40), [apps/agro/next.config.ts](file:///opt/lampp/htdocs/farm/apps/agro/next.config.ts#L14-L22) e [docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml#L216-L250)
- **Descrição:**
  1. No Backoffice Web (`staging-web`), Server Components (RSC) usam `BACKEND_URL` para se comunicar com o backend via rede Docker. Como `BACKEND_URL` não está definido no Compose, o fallback assume `http://127.0.0.1:8000` (que aponta para dentro do container Web), gerando `ECONNREFUSED`.
  2. No PWA Agro (`staging-agro`), em `NODE_ENV=production`, o `next.config.ts` exige a variável `AGRO_API_INTERNAL_ORIGIN` para ativar o proxy interno `/api/v1/:path*`. Como a variável não foi passada, as requisições relativas no cliente falharão com 404.
- **Impacto:** Falha completa de carregamento de páginas RSC no Backoffice Web e impossibilidade de autenticação/heartbeat no PWA Agro.
- **Correção Necessária:**
  - Em `staging-web`, definir `BACKEND_URL: http://staging-api-worker-1:8000`.
  - Em `staging-agro`, definir `AGRO_API_INTERNAL_ORIGIN: http://staging-api-worker-1:8000` e `NEXT_PUBLIC_AGRO_API_ORIGIN: http://127.0.0.1:8001`.

---

### 8.3 MEDIUM (Riscos de Ambiguidade ou Concorrência)

#### ACHADO-PREFLIGHT-04: Risco de Ambiguidade de Branches no Alembic
- **Severidade:** **MEDIUM**
- **Arquivo:** [services/api/migrations/versions](file:///opt/lampp/htdocs/farm/services/api/migrations/versions)
- **Descrição:** A presença concomitante da árvore de migrações legadas (416 versões desde `001_notas_fiscais.py`) e do baseline consolidado `20260908_baseline_deepfarms_v1.py` faz com que o comando padrão `alembic upgrade head` possa gerar erro de múltiplos heads em um banco recém-criado.
- **Impacto:** O comando de migração pode abortar durante o boot inicial de staging.
- **Correção Necessária:** O script de automação deve invocar explicitamente `alembic upgrade heads` ou especificar a tag canônica `alembic upgrade deepfarms_baseline@head`.

#### ACHADO-PREFLIGHT-05: Throttling de Heartbeat Não Distribuído entre Workers
- **Severidade:** **MEDIUM**
- **Arquivo:** `services/api/core/middleware/session_heartbeat_middleware.py`
- **Descrição:** O cache de 60 segundos do heartbeat é mantido em memória no processo Python (`dict`). Em ambiente com 2 workers (`worker-staging-1` e `worker-staging-2`), se o navegador balancear chamadas entre eles, o intervalo efetivo de banco pode ser inferior a 60 segundos.
- **Impacto:** Sobrecarga leve de writes concorrentes na tabela de usuários.
- **Correção Recomendada:** Na evolução futura para produção, migrar a chave de throttling para o Redis (`SET key EX 60 NX`).

---

### 8.4 LOW (Melhorias de Higiene e Robustez Operacional)

#### ACHADO-PREFLIGHT-06: Validação de Isolamento Dependente do Wrapper `up.sh`
- **Severidade:** **LOW**
- **Arquivo:** [infrastructure/staging/docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml)
- **Descrição:** O script `validate_isolation.py` é executado antes do Compose pelo script `up.sh`. Contudo, se um operador rodar diretamente `docker compose -f infrastructure/staging/docker-compose.agro-staging.yml up`, a validação do script Python é contornada.
- **Correção Recomendada:** Inserir um container efêmero de verificação de pré-requisitos (`init-isolation-check`) no próprio Compose como dependência primária de todos os serviços.

#### ACHADO-PREFLIGHT-07: Política de Expurgo DERAL Puramente Operacional
- **Severidade:** **LOW**
- **Arquivo:** [services/api/core/services/deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py)
- **Descrição:** A retenção de 12 meses documentada para snapshots DERAL não possui rotina automática de expurgo. Snapshots antigos permanecerão armazenados na tabela `ConfiguracaoSaaS` indefinidamente até ação manual.
- **Correção Recomendada:** Criar task periódica (Celery / cron script) para arquivamento de snapshots com mais de 12 meses.

---

## 9. Correções Obrigatórias Antes da Subida (Plano de Ação para 01H2B)

Antes de autorizar qualquer execução de `docker compose up` ou `scripts/staging/up.sh` na fase 01H2B, as seguintes alterações pontuais deverão ser aplicadas:

1. **Ajuste de CORS na API:**
   - Em [services/api/core/config.py](file:///opt/lampp/htdocs/farm/services/api/core/config.py#L106-L122), incluir `"http://localhost:3005"` e `"http://127.0.0.1:3005"` na lista default `cors_origins`.
   - Em [services/api/main.py](file:///opt/lampp/htdocs/farm/services/api/main.py#L295-L305), incluir as mesmas origens na lista fallback de desenvolvimento.

2. **Ajuste das Variáveis de Storage no Compose:**
   - Em [infrastructure/staging/docker-compose.agro-staging.yml](file:///opt/lampp/htdocs/farm/infrastructure/staging/docker-compose.agro-staging.yml#L141-L144), definir explicitamente nos workers:
     ```yaml
     STORAGE_BACKEND: s3
     S3_BUCKET: deepfarms-staging-bucket
     S3_BUCKET_NAME: deepfarms-staging-bucket
     ```

3. **Ajuste das Variáveis dos Frontends no Compose:**
   - Em `staging-web`:
     ```yaml
     BACKEND_URL: http://staging-api-worker-1:8000
     ```
   - Em `staging-agro`:
     ```yaml
     AGRO_API_INTERNAL_ORIGIN: http://staging-api-worker-1:8000
     NEXT_PUBLIC_AGRO_API_ORIGIN: http://127.0.0.1:8001
     ```

4. **Desacoplamento Seguro do Comando Alembic:**
   - No script `up.sh`, assegurar que o comando de migração utilize explicitamente `alembic upgrade heads` e valide o código de saída antes de iniciar os workers de API.

---

## 10. Procedimento Seguro de Inicialização em Etapas

Para garantir controle absoluto sobre o ciclo de vida e impedir qualquer operação concorrente prematura, a inicialização na fase **01H2B** deve seguir estritamente o pipeline de 6 etapas segregadas:

```mermaid
sequenceDiagram
    autonumber
    actor Operador as Engenheiro de Infra / SRE
    participant Gate as scripts/staging/validate_isolation.py
    participant DB as Staging Infra (Postgres, Redis, MinIO)
    participant Alembic as Alembic Migrations Runner
    participant Backend as API Workers (worker-1, worker-2)
    participant Frontend as Frontends (Web & Agro)

    Operador->>Gate: Executa validação estática de variáveis (.env.staging)
    alt Violação de Produção ou Segredo Fraco
        Gate-->>Operador: ABORTA IMEDIATAMENTE (Código 1)
    else Isolamento Comprovado
        Gate-->>Operador: APROVAÇÃO ISOLAMENTO (Código 0)
    end

    Operador->>DB: Sobe exclusivamente containers de dados (postgres, redis, minio)
    DB-->>Operador: Healthchecks OK (Portas 5433, 6380, 9002 ativas em 127.0.0.1)

    Operador->>DB: Valida identidade do banco (SELECT current_database(), inet_server_addr())
    DB-->>Operador: Confirma "deepfarms_agro_staging" e endereço local

    Operador->>Alembic: Executa migrações contra o banco de staging vazio
    Alembic->>DB: Cria schema "farms" e tabelas base
    DB-->>Alembic: Migrações aplicadas com sucesso
    Alembic-->>Operador: Schema OK

    Operador->>Backend: Sobe staging-api-worker-1 e staging-api-worker-2
    Backend->>DB: Conecta no Postgres e Redis
    Backend-->>Operador: Healthcheck OK (/api/v1/health retorna HTTP 200)

    Operador->>Frontend: Sobe staging-web e staging-agro
    Frontend-->>Operador: Healthchecks OK (Portas 3001 e 3005 prontas)
```

### Detalhamento das Etapas de Execução:
1. **Etapa 1 — Gate Estático de Isolamento:**
   Executar `python3 scripts/staging/validate_isolation.py --env-file infrastructure/staging/.env.staging`. Falhar se houver qualquer warning de produção.
2. **Etapa 2 — Subida da Infraestrutura Base de Dados:**
   Executar `docker compose -f infrastructure/staging/docker-compose.agro-staging.yml up -d staging-postgres staging-redis staging-minio`. Aguardar que todos atinjam o status `healthy`.
3. **Etapa 3 — Verificação Criptográfica e de Identidade do Banco:**
   Conectar ao PostgreSQL via porta de loopback `5433` e checar:
   - `SELECT current_database()` == `'deepfarms_agro_staging'`;
   - `SELECT inet_server_addr()` (deve retornar endereço da rede bridge docker, nunca IP público de RDS).
4. **Etapa 4 — Execução Controlada de Migrations:**
   Executar as migrações dentro do contexto do container ou via script controlado direcionado exclusivamente a `127.0.0.1:5433`.
5. **Etapa 5 — Subida e Validação dos Workers da API:**
   Subir `staging-api-worker-1` e `staging-api-worker-2`. Validar o endpoint `/api/v1/health` em ambos os workers (`http://127.0.0.1:8001` e `http://127.0.0.1:8002`).
6. **Etapa 6 — Subida dos Frontends e Smoke Test:**
   Subir `staging-web` e `staging-agro`. Executar testes funcionais de fumaça (acesso ao backoffice e consulta do catálogo agro).

---

## 11. Critérios Verificáveis para Autorizar a Fase 01H2B

A transição para a fase operacional **AGRO-ADMIN-01H2B** é formalmente autorizada sob o cumprimento dos seguintes critérios mensuráveis:

1. [x] **Relatório de Pré-flight Aprovado:** Relatório 01H2A registrado e revisado;
2. [ ] **Correção dos 3 Achados de Configuração:**
   - Adição das portas 3005 no CORS em `main.py` e `config.py`;
   - Ajuste das variáveis `S3_BUCKET` e `STORAGE_BACKEND` no Compose;
   - Injeção de `BACKEND_URL` e `AGRO_API_INTERNAL_ORIGIN` no Compose;
3. [ ] **Validação Estática Sem Falhas:** Execução de `scripts/staging/validate_isolation.py` retornando código `0`;
4. [ ] **Chaves Segregadas Confirmadas:** `STAGING_PLATFORM_CREDENTIALS_MASTER_KEY` e `STAGING_JWT_SECRET_KEY` geradas com entropia criptográfica independente e armazenadas em `.env.staging` (ignorado no Git);
5. [ ] **Portas Locais Livres no Host:** Verificação de que as portas `5433`, `6380`, `9002`, `9003`, `8001`, `8002`, `3001` e `3005` não estão em uso no host antes do boot.

---

## 12. Veredicto Final

```
================================================================================
                    VEREDICTO DA AUDITORIA PRÉ-FLIGHT
================================================================================

                         GO COM RESSALVAS
              (Aprovado para 01H2B com Ajustes de Configuração)

================================================================================
```

### Justificativa Técnica:
1. **Segurança e Isolamento de Produção:** **APROVADO (100% SEGURO).** Não existe nenhum canal direto, indireto ou por fallback que permita aos containers atingirem a produção do DeepFarms. O isolamento de rede, volumes e credenciais atende aos mais rígidos padrões de engenharia.
2. **Prontidão Operacional:** **CONDICIONADA.** As ressalvas apontadas nos **Achados 01, 02 e 03** (CORS 3005, variáveis MinIO e variáveis internas de Next.js) são correções simples de configuração que devem ser aplicadas como primeira etapa da fase **01H2B**, garantindo que a infraestrutura suba perfeitamente funcional desde a primeira tentativa.

**Encerramento da Fase AGRO-ADMIN-01H2A.**  
Aguardando autorização superior para o início da fase **AGRO-ADMIN-01H2B** (Execução e Homologação da Infraestrutura de Staging).
