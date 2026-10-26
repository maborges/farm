# AGRO-ADMIN-01A — Auditoria Arquitetural do Backoffice DeepFarms

**Documento:** Relatório de Auditoria Arquitetural e Plano de Integração  
**Referência:** `AGRO-ADMIN-01A-AUDITORIA-BACKOFFICE-INTEGRACAO.md`  
**Data de Emissão:** 22 de Outubro de 2026  
**Responsável Técnico:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High  
**Modalidade:** Auditoria arquitetural — estritamente somente leitura  
**Princípio Orientador:** *Administração compartilhada, operação isolada.*

---

## 1. Sumário Executivo

### 1.1. Contexto e Motivação
O ecossistema DeepFarms é composto por duas plataformas com proposições e dinâmicas operacionais distintas:
1. **DeepFarms SaaS:** Plataforma comercial de gestão agropecuária multi-tenant, voltada para produtores e fazendas corporativas, com controle de estoque, caderno de campo, pecuária, financeiro, faturamento, integrações ERP e um Backoffice administrativo robusto.
2. **DeepFarms Agro:** Aplicação PWA de utilidade pública gratuita para produtores rurais (`apps/agro`), alimentada por um backend desacoplado (`services/api/public_clima` e `public_mercado`), com previsão do tempo microrregional, cotações agrícolas e calculadoras rurais, sem barreira de login obrigatório.

Foi demandada a avaliação do aproveitamento do Backoffice administrativo do DeepFarms SaaS como console central de administração do DeepFarms Agro, contemplando:
- Governança de provedores e credenciais (com foco imediato na ativação da chave WeatherAPI obtida para a fase `CLIMA-01G`);
- Controle de configurações de produto e feature flags;
- Monitoramento de cotas, desempenho, cache e custos upstream;
- Acompanhamento da adoção do PWA sem comprometer a privacidade do produtor rural;
- Canal voluntário e em conformidade com a LGPD para encaminhar produtores interessados no SaaS ao CRM comercial do Backoffice;
- Preservação estrita da segurança, estabilidade e disponibilidade de ambos os produtos.

### 1.2. Diagnóstico Central
A auditoria identificou que o Backoffice do DeepFarms SaaS possui uma fundação arquitetural sólida de frontend (`apps/web/src/app/(dashboard)/dashboard/backoffice/`) e backend (`services/api/core/routers/backoffice*.py`). No entanto:
1. **Impedimento no Domínio de Integrações Atual:** Os modelos canônicos de credenciais (`IntegrationCredential` e `TenantIntegracao` em `services/api/integracoes/models.py`) impõem `tenant_id` como chave estrangeira obrigatória (`nullable=False`, `ForeignKey("tenants.id")`). O DeepFarms Agro é um produto público sem tenant comercial. Tentar reutilizar esses modelos diretamente exigiria a criação de um "tenant fantasma", o que violaria o isolamento multi-tenant, falsearia métricas de receita/billing do SaaS e enfraqueceria as regras de segurança.
2. **Isolamento de Banco e Limitação de Recursos:** O pool de conexões do PostgreSQL do SaaS é conservador (`db_pool_size=3`, `db_max_overflow=2`, totalizando no máximo 5 conexões simultâneas em `services/api/core/config.py`). O backend público do Agro opera hoje com isolamento total desse banco, utilizando cache Redis de dois níveis com fallback em memória. Qualquer acoplamento síncrono do backend público ao banco do SaaS derrubaria a plataforma comercial sob picos de tráfego anônimo.
3. **Módulo CRM Real vs. Ingestão de Leads:** O Backoffice dispõe de um módulo CRM interno com Kanban, estágios (`PipelineEstagio`), leads (`LeadCRM`) e atividades (`AtividadeCRM`). Contudo, o CRM não possui nenhum endpoint público de ingestão de oportunidades e não contempla a origem de aquisição `deepfarms_agro`. No PWA Agro, o único link existente com o SaaS é uma tag estática `<a href="https://deepfarms.com.br">` em `apps/agro/src/app/page.tsx`, sem mensuração de conversão ou captura transparente de interesse.

### 1.3. Decisão Arquitetural Recomendada
Recomenda-se a **Alternativa A Otimizada (Armazenamento Canônico de Plataforma + Distribuição Desacoplada com Hot-Reload)**:
- O Backoffice administrará provedores e credenciais da plataforma através de uma entidade dedicada de escopo de plataforma (`PlatformProviderCredential`), persistida com criptografia simétrica Fernet (`integracoes/security.py`) e auditoria completa (`AdminAuditLog`).
- O backend público Agro consumirá a configuração ativa através de injeção desacoplada (cache local em memória sincronizado via evento/pub-sub ou TTL curto no Redis), **sem nenhuma consulta síncrona ao banco comercial do SaaS durante o fluxo de requisições meteorológicas do produtor rural**.
- Dessa forma, o Backoffice atua como plano de controle (*control plane*), enquanto o backend público do Agro atua exclusivamente no plano de dados (*data plane*), garantindo disponibilidade inabalável mesmo em caso de indisponibilidade temporária do Backoffice.

---

## 2. Inventário Real do Backoffice (Fase A)

A investigação percorreu a totalidade dos artefatos de código de frontend e backend responsáveis pela administração da plataforma.

### 2.1. Estrutura de Frontend do Backoffice
O frontend administrativo reside dentro da aplicação Next.js `apps/web`, sob a rota base agrupada `apps/web/src/app/(dashboard)/dashboard/backoffice/`. A navegação lateral e controle de visibilidade são governados por `apps/web/src/lib/sidebar-config.ts` (linhas 645–718) e testados em `apps/web/src/lib/sidebar-navigation.test.ts`.

#### Estrutura de Telas Identificadas em `apps/web`:
```
apps/web/src/app/(dashboard)/dashboard/backoffice/
├── admin-users/              <- Gestão de contas de operadores administrativos do SaaS
├── assinantes/               <- Gestão operacional e visualização de tenants/produtores
├── audit/                    <- Visualização central de logs de auditoria e incidentes de segurança
├── bi/                       <- Indicadores de Business Intelligence (MRR, Churn, LTV, Coortes)
├── billing/                  <- Faturas, reconciliação financeira (Stripe e Asaas)
├── cadastros-auxiliares/     <- Marcas, modelos, categorias, culturas globais
├── configuracoes/            <- Parâmetros de sistema da plataforma (/config/saas)
├── crm/                      <- Funil comercial Kanban, leads e atividades (CrmClient.tsx)
├── cupons/                   <- Cupons de desconto e campanhas de marketing SaaS
├── dashboard/                <- Dashboard executivo geral (MRR, total de tenants e usuários)
├── email-templates/          <- Templates transacionais de e-mail (MJML/HTML)
├── ia-creditos/              <- Solicitações e auditoria de consumo de créditos de IA
├── integracoes/
│   └── erp/                  <- Console de observabilidade e timeline de integrações ERP
├── kb/                       <- Base de conhecimento interna para suporte
├── modules/                  <- Catálogo de módulos adicionais comercializados
├── ofertas/                  <- Ofertas comerciais personalizadas por lead
├── pipeline/                 <- Configuração e ordenação de estágios do funil de vendas
├── plans/                    <- Cadastro de planos (Básico, Profissional, Enterprise)
├── profiles/                 <- Perfis de permissão padrão atribuíveis a tenants
├── sessions/                 <- Monitoramento de sessões administrativas e bloqueios
├── support/                  <- Central de chamados de suporte técnico de clientes
├── tabelas/                  <- Visualizador e editor de tabelas padrão do sistema
├── tenants/                  <- Detalhes aprofundados, limites e bloqueio de tenants
└── usuarios/                 <- Listagem global de usuários finais vinculados aos tenants
```
Adicionalmente, existe a rota:
- `apps/web/src/app/(dashboard)/backoffice/clima/modelos/`: Interface de gestão de modelos fitossanitários base (`modelos-backoffice-client.tsx`).

### 2.2. Estrutura de Backend do Backoffice
O backend FastAPI (`services/api/main.py`) expõe os roteadores administrativos sob o prefixo `/api/v1/backoffice`:

| Roteador Backend (`services/api/core/routers/`) | Prefixo de Rota | Responsabilidade Principal |
| :--- | :--- | :--- |
| `backoffice.py` (1.085 linhas) | `/backoffice` | Dashboard stats, BI stats, lista/bloqueio de tenants, planos, módulos, faturas, usuários globais, chamados de suporte, desbloqueio de IP/brute-force e logs de impersonation. |
| `backoffice_admins.py` (299 linhas) | `/backoffice/admins` | CRUD completo de administradores (`AdminUser`), estatísticas por perfil e reset de credenciais. |
| `backoffice_audit.py` (224 linhas) | `/backoffice/audit` | Consulta paginada e filtros de logs de auditoria (`AdminAuditLog`) e incidentes de segurança (`TenantAuditLog`). |
| `backoffice_crm.py` (748 linhas) | `/backoffice/crm` | Gestão de estágios do funil, movimentação Kanban, CRUD de leads, follow-ups e conversão de lead em tenant. |
| `backoffice_crm_ofertas.py` | `/backoffice/crm-ofertas` | Cadastro de produtos/módulos de oferta (`ModuloOferta`) e precificação. |
| `backoffice_email_templates.py` | `/backoffice/email-templates` | Gestão de modelos de e-mail do sistema. |
| `backoffice_sessions.py` | `/backoffice/sessions` | Monitoramento e revogação forçada de sessões ativas. |
| `backoffice_tabelas.py` | `/backoffice/tabelas` | Gestão de tabelas agronômicas e commodities globais. |
| `backoffice_uom.py` | `/backoffice/uom` | Gestão global de Unidades de Medida e regras de conversão física. |
| `backoffice_plan_changes.py` | `/backoffice/plan-changes` | Aprovação e histórico de solicitações de upgrade/downgrade. |
| `backoffice_profiles.py` | `/backoffice/profiles` | Perfis padrão de acesso do SaaS. |
| `backoffice_ia_auditoria.py` | `/backoffice/ia` | Auditoria de consumo de tokens de LLM e solicitações de créditos adicionais. |
| `configuration.py` | `/config` | Consulta e atualização de parâmetros globais (`ConfiguracaoSaaS`). |

### 2.3. Autenticação, Autorização e Papéis (RBAC)
A segregação entre usuários de clientes e operadores do Backoffice é física e lógica:
1. **Entidade Administrativa (`AdminUser`):** Definida em `services/api/core/models/admin_user.py` (tabela `admin_users`), separada da tabela `usuarios`.
   - Campos: `id` (UUID), `email` (único), `senha_hash` (bcrypt), `nome`, `role`, `ativo`, `ultimo_acesso`, `timezone`, `locale`, `created_at`, `updated_at`.
2. **Papéis Administrativos Canônicos (`role`):**
   - `super_admin`: Acesso irrestrito a todas as rotas e recursos (`["*"]`).
   - `admin`: Gestão operacional completa de tenants, planos, usuários, configurações, suporte e cadastros.
   - `suporte`: Acesso ao dashboard, listagem de tenants e atendimento de chamados (`support:*`, `kb:*`).
   - `financeiro`: Acesso ao faturamento (`billing:*`), planos e relatórios financeiros.
   - `comercial`: Gestão do funil de vendas (`crm:*`), propostas, planos, cupons e assinaturas.
3. **Mecanismo de Verificação no Backend:**
   - `get_current_admin` (`services/api/core/dependencies.py`, linhas 462–469): Verifica se o token JWT possui a claim `is_superuser == True`.
   - `require_permission(permissao)` (`services/api/core/dependencies.py`, linhas 804–830): Avalia a permissão no formato `recurso:acao` contra `BackofficePermissions.PERMISSIONS_MAP` (`services/api/core/constants.py`, linhas 415–488) ou no método `AdminUser.tem_permissao`.
4. **Infraestrutura de Auditoria (`AdminAuditLog`):**
   - Definida em `services/api/core/models/admin_audit_log.py` (tabela `admin_audit_log`).
   - Registra de forma indelével: `admin_user_id`, `admin_email`, `acao` (ex: `tenant.toggle_status`), `entidade`, `entidade_id`, `descricao`, `dados_anteriores` (JSON), `dados_novos` (JSON), `ip_address`, `user_agent` e `created_at`.

### 2.4. Matriz de Maturidade do Backoffice

| Funcionalidade / Recurso | Status Real no Repositório | Evidência Técnica |
| :--- | :--- | :--- |
| **Gestão de Tenants / Assinantes** | **Implementada** | `core/routers/backoffice.py:140`, `apps/web/.../assinantes/` |
| **Planos, Módulos e Faturamento** | **Implementada** | `core/routers/backoffice.py:184`, `core/routers/billing.py` |
| **Auditoria Administrativa** | **Implementada** | `core/models/admin_audit_log.py`, `core/routers/backoffice_audit.py` |
| **Gestão de Operadores do SaaS** | **Implementada** | `core/models/admin_user.py`, `core/routers/backoffice_admins.py` |
| **Modelos Fitossanitários Clima** | **Implementada** | `apps/web/.../backoffice/clima/modelos/`, `clima-api.ts:168` |
| **CRM Comercial (Pipeline & Kanban)** | **Implementada (Interno)** | `core/models/crm.py`, `core/routers/backoffice_crm.py`, `CrmClient.tsx` |
| **Observabilidade de Integrações ERP** | **Implementada (ERP/Tara)** | `integracoes/models.py`, `apps/web/.../backoffice/integracoes/erp/` |
| **Console Administrativo DeepFarms Agro** | **INEXISTENTE** | Nenhuma rota ou página de gestão dedicada ao PWA Agro |
| **Gestão de Chaves de Provedor Público** | **INEXISTENTE** | Chaves residem estáticas em variáveis de ambiente (`config.py:30`) |
| **Telemetria Operacional Clima Agro** | **PARCIAL** | Coleta existe no Redis (`cache.py`), mas **sem rota de consulta no Backoffice** |
| **Captura Pública de Leads do Agro** | **INEXISTENTE** | Link estático externo no PWA (`page.tsx:136`), sem ingestão no CRM |

---

## 3. Gestão de Integrações e Credenciais (Fase B)

### 3.1. Arquitetura Canônica Existente (`services/api/integracoes/`)
O subsistema de integrações do SaaS foi construído para cenários corporativos multi-tenant (ERP Sankhya, balança TARA e provider OpenWeather):
1. **Catálogo de Integrações (`MarketplaceIntegracao`):**
   - Tabela: `marketplace_integracoes` (`integracoes/models.py:155`).
   - Define o conector global (`slug`, `nome`, `provider_type`, `connection_schema`, `credential_schema`).
2. **Instância de Integração (`TenantIntegracao`):**
   - Tabela: `tenant_integracoes` (`integracoes/models.py:193`).
   - Relaciona o catálogo a um tenant específico: `tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False)`.
3. **Cofre Canônico de Credenciais (`IntegrationCredential`):**
   - Tabela: `integration_credentials` (`integracoes/models.py:265`).
   - Amarração rígida: `tenant_id` possui `ForeignKey("tenants.id")` com `nullable=False`.
   - Suporte a versionamento (`version_number`), rotação (`rotated_at`), desativação lógica (`deleted_at`) e metadados de mascaramento (`mask_metadata`).
4. **Criptografia Simétrica em Repouso (`integracoes/security.py`):**
   - Algoritmo: Fernet (AES-128-CBC + HMAC-SHA256).
   - Derivação de Chave: SHA-256 sobre `settings.integrations_secret_key` ou fallback para `settings.jwt_secret_key`.
   - Formato Persistido: Prefixo `enc::<token_b64>`.
5. **Mascaramento Protetivo (`integracoes/payload_masking.py`):**
   - Substituição recursiva de chaves sensíveis (`api_key`, `secret`, `token`, `password`) por `••••••••`.

### 3.2. Diagnóstico de Incompatibilidade: Escopo de Tenant vs. Produto Público
O modelo `IntegrationCredential` define um enum `IntegrationScope` com valores `PLATFORM`, `TENANT`, `UNIDADE_PRODUTIVA`, `ESTABELECIMENTO`, `USUARIO`.  
No entanto, na DDL física da tabela `integration_credentials`:
```python
# services/api/integracoes/models.py:280-285
id = Column(Integer, primary_key=True, index=True)
tenant_id = Column(UUIDType(as_uuid=True), _tenant_fk(), nullable=False, index=True)
provider_id = Column(Integer, ForeignKey("marketplace_integracoes.id"), nullable=False)
scope_type = Column(String(30), nullable=False, default=IntegrationScope.TENANT.value)
```
> [!CAUTION]
> **Conclusão Técnica Impeditiva:** `tenant_id` é estritamente **obrigatório (`nullable=False`)**. O DeepFarms Agro é um produto de utilidade pública gratuita para o produtor rural brasileiro, que **não possui e nem deve possuir um tenant comercial no PostgreSQL**.
> Criar um registro fictício na tabela `tenants` (ex: "Tenant Sistema Agro") seria um anti-pattern grave: poluiria o faturamento, violaria o princípio de tenant como pessoa jurídica contratante, introduziria falha em cascata em rotinas de expiração de assinaturas e exporia o Agro a falhas de RLS.

### 3.3. Proposta de Entidade para Credenciais de Plataforma
Para atender ao princípio "Administração compartilhada, operação isolada", propõe-se a criação da entidade `PlatformProviderCredential` (isolada do escopo multi-tenant):
- Tabela: `platform_provider_credentials`
- Campos:
  - `id`: UUID (Primary Key)
  - `product_slug`: String (ex: `"agro"`)
  - `service_module`: String (ex: `"clima"`, `"mercado"`)
  - `provider_slug`: String (ex: `"weatherapi"`, `"openweather"`)
  - `ambiente`: String (`"production"`, `"staging"`)
  - `segredo_criptografado`: Text (criptografado via `integracoes/security.py`)
  - `mascara_chave`: String (ex: `"••••••••1a4f"`)
  - `config_payload`: JSON (parâmetros como `max_days`, `timeout_seconds`, `monthly_quota_limit`)
  - `ativo`: Boolean (default `True`)
  - `version_number`: Integer
  - `rotated_at`: DateTime
  - `created_by_admin_id`: UUID (`ForeignKey("admin_users.id")`)
  - `created_at` / `updated_at`: DateTime

Essa modelagem aproveita 100% da biblioteca criptográfica existente (`encrypt_integration_secret`, `decrypt_integration_secret`, `mask_integration_secret`), vincula a autoria ao `AdminUser` e mantém a tabela `tenants` completamente intocada.

---

## 4. Diagnóstico da Arquitetura Agro (Fase C)

### 4.1. Superfície de Código Auditada
A auditoria inspecionou as implementações em:
- `services/api/public_clima/adapters.py` (983 linhas)
- `services/api/public_clima/service.py` (209 linhas)
- `services/api/public_clima/cache.py` (296 linhas)
- `services/api/public_clima/router.py` (214 linhas)
- `services/api/public_clima/grid.py` (52 linhas)
- `apps/agro/src/lib/clima/` e `apps/agro/src/components/clima/`

### 4.2. Situação dos Adaptadores Meteorológicos
1. **Open-Meteo (`OpenMeteoAdapter`):** Implementado, porém bloqueado para uso em produção sem licença explícita (`allow_unlicensed_public=False`), em observância às diretrizes contratuais.
2. **OpenWeather (`OpenWeatherOneCallAdapter`):** Implementado para OneCall 3.0, também resguardado por validação de licença.
3. **WeatherAPI (`WeatherAPIAdapter`):** Totalmente implementado na fase `CLIMA-01F`.
   - Suporte dinâmico aos planos Free (3 dias) e Starter (7 dias).
   - Projeção horária contínua de 24 horas (transposição cronológica da meia-noite).
   - Mapeamento estrito de códigos de erro (`1002`, `2006`, `2007`, `2008`, `2009`) sem expor detalhes sensíveis.
   - Higiene de log: `__repr__` sanitizado omitindo o token.

### 4.3. Configuração Atual e Dependência Estática
No estado atual (`services/api/public_clima/router.py`, linhas 45–92):
- O conector ativo é instanciado em tempo de carregamento do módulo Python (`_adapter = _init_weather_provider()`).
- Os valores são lidos exclusivamente das variáveis de ambiente (`core/config.py`):
  ```python
  clima_active_provider: str = "WEATHERAPI"
  weatherapi_api_key: str = ""
  weatherapi_enabled: bool = False
  weatherapi_monthly_quota_limit: int = 100000
  ```
- **Limitação Operacional:** Alterar o provedor ou cadastrar a chave WeatherAPI atualmente exige editar o `.env` e reiniciar o processo FastAPI/Uvicorn, provocando downtime temporário e impedindo a governança direta por operadores no Backoffice.

### 4.4. Telemetria e Cache Existentes
O módulo `public_clima/cache.py` já dispõe de infraestrutura de telemetria de alta performance integrada ao Redis:
- Chaves de métricas:
  - Chamadas upstream: `agro:clima:v1:metrics:upstream:{provider}:{YYYY-MM}`
  - Hits de cache: `agro:clima:v1:metrics:hit:{provider}`
  - Misses de cache: `agro:clima:v1:metrics:miss:{provider}`
  - Erros e timeouts: `agro:clima:v1:metrics:error:{provider}:{type}`
- Trava de franquia mensal: método `check_monthly_quota` bloqueia chamadas upstream antes de estourar o teto contratado (`monthly_quota_limit`), entregando cache contingencial com aviso de "dado desatualizado".
- **Lacuna Diagnosticada:** As métricas são gravadas no Redis, mas **não existe nenhum endpoint de leitura para o Backoffice**, impedindo que a equipe administrativa visualize o consumo de franquia ou o volume de acessos em tempo real.

---

## 5. Comparativo de Alternativas Arquiteturais

Foram analisadas três alternativas para a comunicação entre o Backoffice (plano de controle) e o backend público Agro (plano de dados):

| Critério de Avaliação | Alternativa A: Banco Central + Cache & Hot-Reload | Alternativa B: Vault / Secrets Manager Central | Alternativa C: APIs Autenticadas no Backend Agro |
| :--- | :--- | :--- | :--- |
| **Descrição Resumida** | Backoffice grava credenciais criptografadas na tabela `platform_provider_credentials`. Backend Agro consome via cache Redis compartilhado com fallback em memória e hot-reload assíncrono. | Backoffice e Agro conectam-se a um cofre externo gerenciado (AWS Secrets Manager ou HashiCorp Vault) com credenciais de IAM / mTLS. | Backend Agro possui banco de dados próprio isolado. Backoffice gerencia o Agro enviando requisições REST autenticadas por API Key de serviço para o Agro. |
| **Segurança e Criptografia** | **Excelente.** Chave criptografada com Fernet em repouso, nunca exposta em APIs públicas, mascarada no Backoffice. | **Máxima.** Segredos gerenciados por KMS/HSM externo com auditoria granular de acesso por role. | **Boa.** Chave trafega via chamada inter-serviços, exigindo tokens seguros ou mTLS entre Backoffice e Agro. |
| **Simplicidade Técnica** | **Alta.** Reutiliza a infraestrutura de dados já existente (SQLAlchemy, Redis, rotas FastAPI). Não requer novos componentes de infra. | **Baixa.** Requer provisionar, manter e configurar novo serviço de infraestrutura, políticas de IAM e tokens de serviço. | **Média.** Requer implementar autenticação inter-serviços, endpoints administrativos no Agro e lidar com falhas de rede. |
| **Disponibilidade Operacional** | **Máxima (100% Desacoplada).** Se o Backoffice ou o PostgreSQL comercial caírem, o Agro continua servindo previsões meteorológicas sem interrupção através de sua memória/Redis. | **Alta.** Depende da disponibilidade contínua da API do serviço de segredos durante recargas e inicializações. | **Média.** Operações de atualização dependem de ambas as aplicações estarem sadias simultaneamente. |
| **Custo Operacional Adicional** | **Zero.** Opera dentro dos recursos de computação e persistência já contratados. | **Recorrente.** Custos de chamadas à API de segredos e licença de cofre em nuvem. | **Zero.** Custos de infraestrutura mantêm-se inalterados. |
| **Risco de Esgotamento do Banco** | **Nulo.** O backend Agro só lê a configuração na inicialização ou ao receber sinal de invalidação de cache (invalidação eventual). | **Nulo.** Não toca o banco do SaaS para leitura de credenciais. | **Nulo.** O Agro possui armazenamento próprio. |
| **Impacto no Código Existente** | **Mínimo.** Criação de um router administrativo, uma tabela enxuta e um método de recarga no serviço do Agro. | **Alto.** Reescrever provedores para injetar SDK de segredos de nuvem. | **Médio.** Criar camada de recebimento administrativo dentro do Agro. |

---

## 6. Arquitetura Recomendada

A solução recomendada é a **Alternativa A Otimizada (Administração Canônica de Plataforma com Distribuição Desacoplada)**.

### 6.1. Topologia de Funcionamento

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             PLANO DE CONTROLE (SaaS)                             │
│                                                                                  │
│   Administrador Backoffice                                                       │
│             │                                                                    │
│             ▼                                                                    │
│   [Apps/Web - Backoffice UI]                                                     │
│             │                                                                    │
│             ▼ HTTPS + JWT Admin                                                  │
│   [Services/API - /backoffice/agro/provedores]                                   │
│             │                                                                    │
│             ├───────────────► Persiste Criptografado (Fernet)                    │
│             │                 na tabela `platform_provider_credentials`          │
│             │                 (PostgreSQL Comercial)                             │
│             │                                                                    │
│             ├───────────────► Registra Ação em `admin_audit_log`                 │
│             │                                                                    │
│             └───────────────► Publica Invalidação no Redis:                      │
│                               PUBLISH "agro:config:reload" '{"module":"clima"}' │
└───────────────────────────────────────┬──────────────────────────────────────────┘
                                        │ Assíncrono (Pub/Sub ou TTL 5 min)
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            PLANO DE DADOS PÚBLICO (Agro)                         │
│                                                                                  │
│   Produtor Rural (PWA)                                                           │
│             │                                                                    │
│             ▼ HTTPS Anônimo                                                      │
│   [Services/API - /public/clima/previsao]                                        │
│             │                                                                    │
│             ▼                                                                    │
│   [PublicClimaService] ────► Consulta Cache L1 (Memória) / L2 (Redis)           │
│             │                                                                    │
│             │ (Cache Miss)                                                       │
│             ▼                                                                    │
│   [WeatherAPIAdapter]  ◄──── Credencial descriptografada mantida em MEMÓRIA      │
│             │                (NUNCA consulta o Postgres comercial nesta etapa!)  │
│             ▼                                                                    │
│   Upstream WeatherAPI (weatherapi.com)                                           │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2. Garantias Arquiteturais Obrigatórias
1. **Zero Consulta Síncrona no Fluxo Crítico:** Toda requisição de previsão meteorológica (`/public/clima/previsao`) consulta unicamente o cache de dados e, se necessário, a instância do provedor mantida em memória no processo. Em nenhuma circunstância haverá consulta ao PostgreSQL comercial durante uma requisição do produtor rural.
2. **Hot-Reload de Credencial sem Restart:** Ao atualizar a chave da WeatherAPI no Backoffice, um sinal leve é disparado via Redis Pub/Sub (`agro:config:reload`) ou via revalidação por TTL curto (5 minutos) na chave de configuração em cache `agro:config:clima:active`. O adaptador recarrega a chave em memória de forma transparente, permitindo homologar a `CLIMA-01G` em segundos.
3. **Resiliência contra Queda do Backoffice:** Se o Backoffice, o PostgreSQL do SaaS ou a rede corporativa caírem, o backend do DeepFarms Agro permanece 100% operacional servindo as previsões com a última configuração válida retida em memória.

---

## 7. Indicadores Operacionais e Observabilidade (Fase D)

### 7.1. Matriz de Métricas e Controles de Privacidade (LGPD)

| Métrica | Finalidade | Origem dos Dados | Classificação LGPD | Tratamento Protetivo Obrigatório |
| :--- | :--- | :--- | :--- | :--- |
| **Consultas de Clima por Nó** | Monitorar demanda regional | `public_clima/service.py` | Dado Estatístico Anônimo | Agrupado por geo-grid quantizado de 0.05° (~5.5 km). **Nunca armazenar coordenadas GPS precisas da fazenda.** |
| **Municípios Mais Pesquisados** | Avaliar expansão territorial | `public_clima/router.py` | Dado Público | Contagem agregada por Código IBGE do município. |
| **Taxa de Cache Hit / Miss / Stale** | Eficiência da infraestrutura | `public_clima/cache.py` | Dado de Performance | Métricas de sistema sem correlação com usuário. |
| **Chamadas Upstream por Provedor** | Controle de custo e fatura | `public_clima/cache.py` | Dado Financeiro | Contadores mensais persistidos no Redis (`upstream:weatherapi:YYYY-MM`). |
| **Consumo da Franquia WeatherAPI** | Evitar estouro orçamentário | `public_clima/cache.py` | Dado Financeiro | Alertas visuais no Backoffice: 70% (atenção), 85% (alerta), 95% (crítico). |
| **Latência e Erros Upstream** | SLA do fornecedor externo | `public_clima/cache.py` | Dado Técnico | Registro anônimo de HTTP status e códigos WeatherAPI. |
| **Acessos Anônimos (DAU/MAU Estimado)**| Acompanhar adoção do PWA | Hash SHA256 do IP do cliente | Dado Técnico Protegido | Hash irreversível com sal diário truncado em 24 caracteres (`bucket`). **O IP original nunca é persistido em disco.** |
| **Contas Agro Identity Criadas** | Adoção de recursos avançados | `agro_usuarios` (SQLite) | Dado Pessoal (Identificado) | Consentimento voluntário nos termos de uso da conta Agro. Banco segregado. |
| **Leads Comerciais Voluntários** | Oportunidades para o SaaS | `crm_leads` (PostgreSQL) | Dado Pessoal (Consentido) | Base Legal: Consentimento expresso (LGPD Art. 7º, I). Opt-in ativo no formulário. |

> [!IMPORTANT]
> **Diretriz Absoluta de Privacidade:** Usuários anônimos navegando no DeepFarms Agro **NÃO são considerados leads comerciais**. É expressamente vedado rastrear histórico individual de localização ou correlacionar endereços IP com identidade pessoal sem consentimento formal prévio.

---

## 8. Diagnóstico do CRM e Oportunidades Comerciais (Fase E)

### 8.1. Auditoria da Implementação Real do CRM
O módulo de CRM no Backoffice foi investigado a partir de:
- `services/api/core/models/crm.py`:
  - `PipelineEstagio` (tabela `crm_pipeline_estagios`): Estágios ordenados do Kanban comercial.
  - `LeadCRM` (tabela `crm_leads`): Cadastro do prospect (`nome`, `email`, `telefone`, `empresa`, `documento`, `origem`, `valor_estimado`, `plano_interesse`, `status`, `tags`, etc.).
  - `AtividadeCRM` (tabela `crm_atividades`): Histórico de ligações, e-mails, notas e tarefas.
- `services/api/core/routers/backoffice_crm.py`:
  - Endpoints administrativos completos: `/backoffice/crm/kanban`, `/backoffice/crm/leads`, `/backoffice/crm/stats`, e conversão para tenant via `/leads/{id}/converter`.
- `services/api/core/models/solicitacoes_comerciais.py` e `core/routers/backoffice_ia_auditoria.py`:
  - A função `_mock_enviar_crm` (linha 624) retorna deliberadamente `False` com aviso de que *"Nenhuma integração real com CRM externo está implementada"*. As solicitações de IA utilizam esse mock e não alimentam a tabela interna `crm_leads`.

### 8.2. Gaps Identificados no CRM para Atendimento ao Agro
1. **Ausência de Origem Agro:** O campo `LeadCRM.origem` aceita apenas `"manual"`, `"site"`, `"indicacao"`, `"evento"`, `"social"`, `"parceiro"`. Falta a categoria canônica `"agro_pwa"`.
2. **Inexistência de Rota Pública de Captura:** Todos os endpoints em `backoffice_crm.py` exigem `require_permission("backoffice:crm:view")` e autenticação JWT de administrador. Não há endpoint para receber demonstrações voluntárias de interesse vindas do PWA.
3. **PWA Agro com Link Cego:** O card promocional em `apps/agro/src/app/page.tsx` (linhas 135–144) é apenas um link estático externo que redireciona para a home institucional da DeepFarms, sem captura de dados e sem rastreabilidade de ROI.

### 8.3. Desenho de Fluxo de Conversão Agro -> CRM Comercial
Para transformar a audiência gratuita do Agro em funil comercial qualificado sem ferir a privacidade nem as diretrizes da LGPD, desenha-se o seguinte fluxo funcional:

```
[Produtor Rural no PWA Agro]
      │
      ▼ Navega em Clima, Mercado ou Calculadoras
[Ponto de Conversão Contextual / CTA Voluntário]
(Ex: "Deseja gerenciar seus custos de safra e talhões?")
      │
      ▼ Clique consciente do produtor
[Modal de Demonstração / Interesse Comercial]
- Nome completo
- WhatsApp / E-mail
- Município / UF da propriedade
- Porte aproximado (opcional: <100ha, 100-500ha, >500ha)
- Checkbox obrigatório: "Aceito receber contato da equipe DeepFarms"
      │
      ▼ POST /api/v1/public/crm/interesse (Rate Limit estrito + Turnstile/hCaptcha)
[Backend Público - Endpoint de Ingestão]
      │
      ▼ Validação de Schema (Zod / Pydantic)
[Inserção Canônica em `crm_leads`]
- Nome / Contato preenchidos
- Origem: "agro_pwa"
- Estágio: Primeiro estágio ativo do Kanban ("Novo Lead")
- Tags: {"produto_origem": "agro", "modulo_interesse": "gestao_safra", "municipio": "Cascavel/PR"}
- Status: "ativo"
      │
      ▼ Push / Atualização no Backoffice
[Equipe Comercial do SaaS]
- Lead surge instantaneamente no Kanban (/dashboard/backoffice/crm)
- Notificação na central administrativa
- SDR realiza contato consultivo qualificado
- Mapeamento de conversão de produtor gratuito em assinante comercial pagante
```

---

## 9. Segurança, Governança e LGPD (Fase F)

### 9.1. Matriz de Riscos de Segurança e Confiabilidade

| Código | Risco Identificado | Severidade | Impacto Técnico / Operacional | Mitigação Arquitetural Mandatória |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Esgotamento do pool de banco (`db_pool_size=3`) por chamadas públicas do Agro | **BLOCKING** | Queda completa da API comercial e do Backoffice do SaaS por saturação de conexões PostgreSQL. | Manter isolamento estrito: backend público Agro **NUNCA** acessa o banco comercial durante requisições de usuários finais. |
| **SEC-02** | Exposição da API Key da WeatherAPI nos bundles Next.js do PWA | **BLOCKING** | Vazamento de credencial contratada, consumo indevido por terceiros e cobrança externa. | Ingestão exclusiva no backend FastAPI (`services/api`). O conector é backend-to-backend; chaves nunca vão para bundles web. |
| **SEC-03** | Falha de autorização na rota global `/config/saas` | **HIGH** | O router `configuration.py` checa `get_current_user_claims` sem exigir `is_superuser`, permitindo acesso por token de tenant comum. | Proteger `/config/saas` com `require_permission("backoffice:config:view")` ou `get_current_admin`. |
| **SEC-04** | Estouro de franquia da WeatherAPI por perda de estado volátil | **HIGH** | Se o Redis reiniciar, contadores de cota em memória local podem resetar, ultrapassando os 100k chamadas. | Persistir snapshots periódicos de consumo mensal ou manter contagem consolidada em armazenamento durável. |
| **SEC-05** | Spam ou Denial of Service no endpoint público de captação de leads | **MEDIUM** | Injeção maciça de leads falsos no CRM corporativo poluindo a base comercial. | Aplicar rate limiting severo por IP (5 req/hora), validação de e-mail/telefone e proteção bot (Turnstile). |
| **SEC-06** | Violação de LGPD por geolocalização contínua ou não consentida | **MEDIUM** | Não conformidade legal por armazenamento de dados de localização pessoal sem finalidade clara. | Não salvar coordenadas GPS precisas em logs ou banco analítico; utilizar apenas centroides municipais IBGE. |
| **SEC-07** | Ausência da permissão `backoffice:crm:view` para perfil comercial | **LOW** | Usuários administrativos com papel `comercial` tomam 403 Forbidden no CRM caso não sejam `super_admin`. | Incluir `"backoffice:crm:*"` na lista de permissões do perfil comercial em `core/constants.py`. |

---

## 10. Gaps Classificados por Severidade

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                          MAPA DE GAPS DE INTEGRAÇÃO                           │
│                                                                               │
│  [BLOCKING]  GAP-01: Incompatibilidade de tenant_id em IntegrationCredential  │
│  [BLOCKING]  GAP-02: Instanciação estática do provedor meteorológico          │
│                                                                               │
│  [HIGH]      GAP-03: Rota /config/saas sem trava estrita de AdminUser         │
│  [HIGH]      GAP-04: Ausência de rota para exposição de telemetria no Admin   │
│                                                                               │
│  [MEDIUM]    GAP-05: CRM sem rota pública de ingestão e sem origem "agro_pwa" │
│  [MEDIUM]    GAP-06: BackofficePermissions sem permissões granulares de CRM   │
│                                                                               │
│  [LOW]       GAP-07: CTA do PWA Agro é link estático sem parâmetros UTM       │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Detalhamento dos Gaps Identificados:
1. **GAP-01 (BLOCKING — Arquitetura de Dados):**  
   - *Fato:* `IntegrationCredential.tenant_id` possui `nullable=False` e `ForeignKey("tenants.id")` (`integracoes/models.py:281`).  
   - *Impacto:* Não é possível cadastrar credenciais globais de produto público sem criar tenant falso.  
   - *Solução:* Modelar a tabela independente `platform_provider_credentials`.
2. **GAP-02 (BLOCKING — Runtime de Clima):**  
   - *Fato:* `_init_weather_provider()` é invocado no import de `public_clima/router.py:73`, lendo valores estáticos do `.env`.  
   - *Impacto:* Trocar de provedor ou atualizar chave requer reinicialização física da aplicação.  
   - *Solução:* Implementar padrão fábrica com recarga dinâmica (hot-reload) via cache de configuração.
3. **GAP-03 (HIGH — Segurança do SaaS):**  
   - *Fato:* Rotas `/config/saas` em `core/routers/configuration.py:45` utilizam `claims: dict = Depends(get_current_user_claims)`.  
   - *Impacto:* Um usuário logado de qualquer fazenda/tenant comum possui claims JWT válidas e teoricamente acessa configs globais da plataforma.  
   - *Solução:* Substituir a dependência por `admin: dict = Depends(get_current_admin)`.
4. **GAP-04 (HIGH — Observabilidade):**  
   - *Fato:* O método `ClimaCache.get_metrics` existe e é testado, mas não está conectado a nenhuma rota administrativa do Backoffice.  
   - *Impacto:* Os dados de chamadas upstream, hits, misses e erros da WeatherAPI ficam invisíveis no Backoffice.  
   - *Solução:* Criar rota `GET /backoffice/agro/telemetria` retornando o consolidado do Redis.
5. **GAP-05 (MEDIUM — Comercial/CRM):**  
   - *Fato:* `origem` em `core/models/crm.py:57` não inclui `"agro_pwa"` e o CRM só recebe escrita por endpoints autenticados de administradores.  
   - *Impacto:* Impossível receber contatos espontâneos de produtores rurais que usam o PWA.  
   - *Solução:* Adicionar origem `"agro_pwa"` e criar rota pública com proteção contra spam para manifestação de interesse.
6. **GAP-06 (MEDIUM — Governança RBAC):**  
   - *Fato:* Em `core/constants.py:424`, `BackofficePermissions.PERMISSIONS_MAP` omite `backoffice:crm:*` nos perfis `admin` e `comercial`.  
   - *Impacto:* Apenas operadores com `super_admin` (`["*"]`) conseguem acessar `/backoffice/crm` sem erro 403.  
   - *Solução:* Normalizar as permissões de CRM no mapa de permissões administrativas.
7. **GAP-07 (LOW — Marketing/Atribuição):**  
   - *Fato:* Link de "Conhecer Planos" em `apps/agro/src/app/page.tsx:136` aponta para URL pura sem parâmetros de campanha.  
   - *Impacto:* Perda de rastreabilidade de cliques originados do PWA no Analytics.  
   - *Solução:* Inserir tags `utm_source=agro_pwa&utm_medium=banner_home&utm_campaign=conhecer_planos`.

---

## 11. Plano Incremental de Implementação (Fase G)

Para executar a convergência de forma disciplinada, segura e sem quebras, propõe-se o faseamento em 4 etapas evolutivas:

```
┌────────────────────────┐      ┌────────────────────────┐
│     AGRO-ADMIN-01B     │ ───► │     AGRO-ADMIN-01C     │
│ Credenciais Provedores │      │ Telemetria Indicadores │
└───────────┬────────────┘      └───────────┬────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐
│     AGRO-ADMIN-01D     │ ───► │     AGRO-ADMIN-01E     │
│   Integração com CRM   │      │  Governança de Produto │
└────────────────────────┘      └────────────────────────┘
```

---

### Fase AGRO-ADMIN-01B — Administração de Provedores e Credenciais
**Objetivo Prioritário:** Fornecer o menor caminho seguro para cadastrar e gerenciar a chave WeatherAPI pelo Backoffice e destravar a homologação real da fase `CLIMA-01G` sem reiniciar os servidores.

- **Escopo Mínimo:**
  - Criação da tabela `platform_provider_credentials` (desacoplada de tenant).
  - Roteador `backoffice_agro_providers.py` no backend com permissão restrita a `super_admin` e `admin`.
  - Mecanismo de hot-reload no `PublicClimaService` para ler a chave ativa do Redis/banco sem restart.
  - Tela administrativa em shadcn/ui no Backoffice: seleção do provedor ativo (WeatherAPI, Open-Meteo, OpenWeather), inserção/atualização da API Key com mascaramento (`••••••••`), configuração de cota mensal e limite de dias.
  - Registro de auditoria indelével em `admin_audit_log` para toda alteração de credencial ou troca de provedor.
- **Dependências:** `services/api/core/models/admin_audit_log.py`, `services/api/integracoes/security.py`, `services/api/public_clima`.
- **Componentes Reaproveitados:**
  - Criptografia: `encrypt_integration_secret` e `decrypt_integration_secret` (`integracoes/security.py`).
  - Auditoria: `AdminAuditLog` (`core/models/admin_audit_log.py`).
  - Autenticação: `get_current_admin` (`core/dependencies.py`).
  - Adaptador Clima: `WeatherAPIAdapter` (`public_clima/adapters.py`).
  - Design System: shadcn/ui (`apps/web`).
- **Componentes Novos:**
  - Model: `PlatformProviderCredential` (`services/api/core/models/platform_credential.py`).
  - Migration Alembic: criação da tabela `platform_provider_credentials`.
  - Backend Router: `services/api/core/routers/backoffice_agro_providers.py`.
  - Frontend Page: `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/provedores/page.tsx`.
- **Alterações no Banco / Migrações:**
  - Criação de 1 tabela (`platform_provider_credentials`). Nenhuma alteração em tabelas existentes.
- **Riscos Identificados:**
  - Falha ao decodificar a chave em repouso caso `INTEGRATIONS_SECRET_KEY` mude. (Mitigação: validação prévia de integridade no startup).
- **Testes Obrigatórios:**
  - Teste unitário de CRUD e mascaramento de chaves de plataforma.
  - Teste de auditoria garantindo criação de registro em `AdminAuditLog`.
  - Teste de recarga dinâmica comprovando que o `WeatherAPIAdapter` assume a nova chave sem reiniciar o Uvicorn.
  - Teste de isolamento comprovando que `public_clima` funciona mesmo com PostgreSQL offline (após carga em cache).
- **Critérios de Aceite:**
  - Administrador cadastra a chave da WeatherAPI no formulário do Backoffice.
  - O valor em repouso no banco é verificado com prefixo `enc::`.
  - A interface exibe apenas os 4 últimos dígitos (`••••••••1a4f`).
  - O conector meteorológico realiza chamada real bem-sucedida para WeatherAPI (`CLIMA-01G`).

---

### Fase AGRO-ADMIN-01C — Telemetria e Indicadores Operacionais
**Objetivo:** Permitir ao time do Backoffice acompanhar o consumo de cotas da WeatherAPI, custos, taxas de cache e volume de acessos rurais.

- **Escopo Mínimo:**
  - Exposição das métricas do Redis através da rota autenticada `GET /api/v1/backoffice/agro/telemetria`.
  - Painel no Backoffice com cards de KPI: Chamadas upstream no mês, Consumo vs Franquia WeatherAPI (gráfico de progresso percentual), Taxa de Cache Hit/Miss, Latência média e Histórico de erros.
  - Alertas preventivos visuais de consumo de cota (70%, 85%, 95%).
- **Dependências:** Conclusão da AGRO-ADMIN-01B, Redis em execução.
- **Componentes Reaproveitados:** `ClimaCache.get_metrics` (`public_clima/cache.py`), Recharts (`apps/web`).
- **Componentes Novos:** Endpoint `/backoffice/agro/telemetria`, página frontend `apps/web/.../dashboard/backoffice/agro/telemetria/page.tsx`.
- **Alterações no Banco:** Nenhuma. Leituras efetuadas diretamente do Redis.
- **Riscos:** Sobrecarga no Redis por polling agressivo do frontend. (Mitigação: cache de 30 segundos no endpoint de telemetria).
- **Testes Obrigatórios:** Testes de agregação de contadores e assertividade no cálculo de percentual de franquia.
- **Critérios de Aceite:** O Backoffice exibe contadores reais idênticos aos registrados pelo Redis durante consultas meteorológicas.

---

### Fase AGRO-ADMIN-01D — Integração com CRM
**Objetivo:** Capturar o interesse espontâneo de produtores do Agro e integrá-los diretamente ao pipeline de vendas do Backoffice.

- **Escopo Mínimo:**
  - Ajuste no modelo `LeadCRM` para suportar `origem="agro_pwa"`.
  - Criação da rota pública `POST /api/v1/public/crm/interesse` com rate limit severo por IP e validação de schema.
  - Modal interativo no PWA Agro ("Conhecer Soluções DeepFarms Gestão") com consentimento LGPD explícito.
  - Apresentação visual destacada no Kanban do Backoffice para leads originados do Agro.
- **Dependências:** `services/api/core/models/crm.py`, `apps/agro`.
- **Componentes Reaproveitados:** `LeadCRM`, `PipelineEstagio`, `CrmKanbanBoard.tsx`, Zod schemas.
- **Componentes Novos:** Endpoint público de interesse, componente modal de captura no PWA Agro.
- **Alterações no Banco:** Adição do valor enum/check `"agro_pwa"` na coluna `origem` da tabela `crm_leads`.
- **Riscos:** Inserção de dados inválidos ou spam. (Mitigação: sanitização estrita e rate limiting).
- **Testes Obrigatórios:** Teste de submissão do formulário, validação de payload inválido e confirmação de surgimento do lead no estágio inicial do Kanban.
- **Critérios de Aceite:** O produtor preenche o formulário no PWA e o lead surge em tempo real no Kanban comercial do Backoffice com a tag `agro_pwa`.

---

### Fase AGRO-ADMIN-01E — Administração Geral do Produto
**Objetivo:** Gestão centralizada de anúncios, avisos agronômicos e feature flags do DeepFarms Agro.

- **Escopo Mínimo:**
  - Controle de feature flags por módulo (ex: ativar/desativar módulo Mercado ou Calculadoras remotamente).
  - Gestão de avisos agronômicos emergenciais (ex: alertas de geada ou estiagem exibidos no topo do PWA).
- **Dependências:** Conclusão das fases 01B e 01C.
- **Componentes Novos:** Rota de avisos/flags e banner dinâmico no PWA.
- **Critérios de Aceite:** Operador do Backoffice cadastra um aviso agronômico e ele passa a ser exibido no cabeçalho do PWA Agro em até 60 segundos.

---

## 12. Critérios de GO / NO-GO

Para autorizar a abertura e execução da fase **AGRO-ADMIN-01B**, a engenharia do DeepFarms estabelece os seguintes critérios mandatários:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                          CRITÉRIOS DE APROVAÇÃO (GO)                          │
├───────────────────────────────────────────────────────────────────────────────┤
│ [ ] GO-1: Isolamento de Dados                                                 │
│     O modelo proposto NÃO vincula o produto Agro a nenhum registro da tabela  │
│     `tenants`. O isolamento multi-tenant do SaaS permanece 100% íntegro.     │
│                                                                               │
│ [ ] GO-2: Preservação de Performance                                          │
│     O fluxo crítico de previsão do tempo (/public/clima/previsao) é 100%      │
│     desacoplado do PostgreSQL comercial, sem consulta síncrona a banco.       │
│                                                                               │
│ [ ] GO-3: Segurança Criptográfica                                             │
│     Nenhuma chave de API de terceiro trafega em texto puro na rede ou reside  │
│     desprotegida em repouso no banco de dados.                                │
│                                                                               │
│ [ ] GO-4: Transparência e LGPD                                                │
│     Nenhum produtor anônimo é importado ou cadastrado automaticamente como    │
│     lead no CRM sem manifestação voluntária de interesse e opt-in explícito.  │
│                                                                               │
│ [ ] GO-5: Rastreabilidade e Auditoria                                         │
│     Toda e qualquer alteração de credencial ou provedor gera registro         │
│     automático em `admin_audit_log` com ID e e-mail do operador responsável.  │
└───────────────────────────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> **Condição de NO-GO:** Se qualquer proposta de implementação exigir transformar o DeepFarms Agro em um tenant comercial ou criar consultas síncronas ao banco do SaaS a cada requisição de clima, o projeto deve ser **IMEDIATAMENTE BLOQUEADO (NO-GO)** até readequação arquitetural.

---

## 13. Próxima Etapa Recomendada

Com a conclusão favorável desta auditoria e a definição clara da arquitetura recomendada, a próxima ação prioritária é o início da fase:

### **AGRO-ADMIN-01B — Administração de Provedores e Credenciais**

#### Roteiro Imediato de Execução:
1. **Modelagem e Persistência:** Criar o model `PlatformProviderCredential` e respectiva migration Alembic de criação de tabela isolada.
2. **API de Gestão no Backend:** Implementar `services/api/core/routers/backoffice_agro_providers.py` com operações de listagem mascarada, atualização de credencial criptografada e auditoria automática.
3. **Mecanismo de Hot-Reload:** Implementar recarga desacoplada da chave no `PublicClimaService`, permitindo que o conector meteorológico assuma a credencial atualizada sem reinicialização de servidor.
4. **Interface no Backoffice:** Construir a tela de gestão em `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/provedores/page.tsx` com formulário outline/sm (padrão shadcn/ui do projeto).
5. **Homologação CLIMA-01G:** Cadastrar a chave real da WeatherAPI já disponibilizada pelo responsável através do novo console e validar a entrega de dados meteorológicos reais no PWA.

---
*Relatório concluído e registrado em conformidade com as Leis de Engenharia de Software DeepFarms e restrições de governança.*
