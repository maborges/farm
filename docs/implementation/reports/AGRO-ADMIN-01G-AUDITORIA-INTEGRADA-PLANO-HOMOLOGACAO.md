# AGRO-ADMIN-01G — Relatório de Auditoria Técnica Integrada, Correção da Matriz de Homologação e Preparação para Staging

**Modelo:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High (Análise Forense e Arquitetural Estrita)  
**Modalidade:** Auditoria Independente Somente Leitura (Read-Only) — Sem Implementação de Código  
**Data:** 24 de Outubro de 2026  
**Status do Veredicto Global:** **GO COM RESSALVAS (Para Homologação em Staging Isolado) / NO-GO (Para Entrada Direta em Produção)**  

---

## 1. Resumo Executivo

A presente auditoria técnica independente foi executada em conformidade com as diretrizes da fase **AGRO-ADMIN-01G**, cobrindo o ecossistema integrado resultante das fases **AGRO-ADMIN-01B** (Identidade Unificada), **01D** (Gestão de Usuários), **01E2** (Configurações Dinâmicas), **01E3/01E3A** (Provedores Climáticos e Credenciais), **01E4/01E4A** (Mercado Oficial e Snapshots DERAL), **01E5** (Catálogos Globais, Avisos e Feature Flags) e **01F** (Dashboard Executivo e Observabilidade).

A inspeção baseou-se exclusivamente na análise do **código-fonte real**, schemas de banco de dados, middlewares, suítes de teste e logs de execução, rejeitando terminantemente alegações de conclusão não sustentadas por evidências verificáveis.

### Principais Conclusões:
1. **Solidez dos Mecanismos Transacionais e RBAC:** A fundação de controle de acesso (RBAC de Backoffice), as travas de concorrência com optimistic locking (`revision`), a segregação de credenciais por envelope encryption (AES-256-GCM + HKDF) e as validações de schemas Pydantic estão plenamente implementadas e testadas.
2. **Gap Crítico na Telemetria de Atividade (Heartbeat):** O middleware de heartbeat de sessão (`SessionHeartbeatMiddleware` em `main.py`) ignora propositalmente rotas `/api/v1/public/*` e `/api/v1/agro/*`, exige token `Authorization: Bearer` (enquanto o PWA utiliza cookies `HttpOnly`) e requer o cabeçalho `x-user-activity: true` (enviado pelo `apps/web`, mas ausente no `apps/agro`). Consequentemente, as métricas de "Usuários Ativos (Hoje / 7d)" no Dashboard 01F capturam apenas o instante de login, sem refletir a utilização contínua do PWA.
3. **Revisão Rigorosa da Matriz de Homologação (11 Itens):** Em contraste com os 63.6% de aprovação reportados na 01F (baseados em testes unitários locais com SQLite em memória e mocks de rede), a auditoria desclassificou itens onde validações parciais foram computadas como aprovações plenas. O percentual real homologado com evidência suficiente e reproduzível é de **27.3% (3 de 11)**, com **54.5% (6 de 11) PARCIAIS** e **18.2% (2 de 11) PENDENTES**.
4. **Verificação de Build de Produção:** Durante esta auditoria, foi executado pela primeira vez o build real de produção (`next build --webpack`) em ambos os frontends:
   - `apps/web`: Compilado com sucesso em 2.7 minutos (todas as 270 rotas validadas, 0 erros).
   - `apps/agro`: Compilado com sucesso em 11 segundos (10 rotas estáticas validadas, 0 erros).
   Isso permitiu elevar o Item 11 da Matriz de Homologação para **APROVADO**.
5. **Prontidão para Staging:** O sistema está funcionalmente maduro e apto para transição a um ambiente de **Staging Isolado** com PostgreSQL 16 e Redis 7 reais. O deploy direto em Produção é **NO-GO** até a resolução dos achados classificados como BLOCKER e HIGH.

---

## 2. Matriz de Conformidade das Fases 01B–01F

| Fase | Escopo Previsto | Implementação Encontrada no Código | Estado Auditado | Evidências / Arquivos |
|---|---|---|---|---|
| **01B** | Identidade Unificada e Sessões Sem Tenant | Modelo `Usuario` global em PostgreSQL. `SessaoAtiva` com `tenant_id` anulável. Guardrail comercial `verify_commercial_jwt_guardrail` rejeitando tokens `INDIVIDUAL_FREE`. | **CONFORME** | `core/models/auth.py`, `core/models/sessao.py`, `core/dependencies.py:246-270` |
| **01D** | Gestão de Produtores Agro no Backoffice | Listagem paginada com busca textual/CPF, filtros de status e BYOK, detalhes do usuário, bloqueio/desbloqueio e revogação de sessões. Conversão comercial desativada conforme 01D1. | **CONFORME** | `core/routers/backoffice_agro.py:240-520`, `tests/unit/core/test_backoffice_agro_01d.py` |
| **01E2** | Configurações Dinâmicas e Auditoria | Persistência na tabela `configuracoes_saas` com `version` e optimistic locking (`409 Conflict`). Trilha de auditoria em `admin_audit_logs`. Cache L1 em memória com invalidação. | **CONFORME** | `core/services/agro_config_service.py`, `core/models/configuration.py`, `core/models/admin_audit_log.py` |
| **01E3 / 01E3A** | Provedores Climáticos e Credenciais | `PlatformWeatherCredentialsService` com KEK v2 derivada via HKDF (AES-256-GCM). `DynamicWeatherOrchestrator` com fallback para Open-Meteo, WeatherAPI e INMET. `ClimaCache` com telemetria. | **CONFORME COM RESSALVA** *(Falta KMS dedicado e hard-limit de cotas)* | `core/services/platform_weather_credentials.py`, `public_clima/dynamic_orchestrator.py`, `public_clima/cache.py` |
| **01E4 / 01E4A** | Mercado Oficial e Hardening DERAL | Pipeline de upload `.xls` (BIFF8/OLE2 nativo com `xlrd`) e `.json`. Validação de 21 commodities. Segregação de integridade SHA-256, proveniência e aprovação. Sincronização multi-worker via DB. | **CONFORME COM RESSALVA** *(Storage de binários em tabela SaaS; proveniência baseada apenas em URL)* | `core/services/deral_snapshot_service.py`, `core/services/market_sources_service.py`, `public_mercado/precos_publicos.py` |
| **01E5** | Catálogos Globais, Avisos e Feature Flags | Gestão de Commodities e Unidades com `tenant_id = NULL` e `sistema = True`. Proteção contra exclusão física com 409 Conflict. Mensagens públicas com vigência e avisos invioláveis. Flags com efeito real na API. | **CONFORME** | `core/routers/backoffice_agro_catalogo.py`, `core/routers/backoffice_agro_config.py`, `tests/unit/core/test_backoffice_agro_01e5.py` |
| **01F** | Dashboard Executivo e Observabilidade | Endpoints de resumo, série temporal 30d, motor dinâmico de incidentes operacionais e matriz de pendências. Interface Next.js 16 Backoffice com 5 subconsoles e 6 abas. | **CONFORME COM GAP DE TELEMETRIA** *(Heartbeat inativo no PWA)* | `core/routers/backoffice_agro_dashboard.py`, `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/page.tsx` |

---

## 3. Fluxos Integrados Auditados

### 3.1 Fluxo 1: Cadastro Gratuito → Autenticação → PWA Agro
```mermaid
sequenceDiagram
    autonumber
    actor Produtor as Produtor Rural (PWA)
    participant AuthAPI as API /auth
    participant DB as PostgreSQL (usuarios)
    participant SessDB as PostgreSQL (sessoes_ativas)
    participant App as PWA (apps/agro)

    Produtor->>AuthAPI: POST /api/v1/auth/register-free (nome, email, senha)
    Note over AuthAPI: FreeRegistrationRateLimiter (5 req / 15 min por IP)
    AuthAPI->>DB: SELECT id FROM usuarios WHERE email = ...
    alt Usuário já existe
        AuthAPI-->>Produtor: HTTP 202 Accepted (Mensagem genérica anti-enumeração)
    else Novo cadastro
        AuthAPI->>DB: INSERT INTO usuarios (is_superuser=False, ativo=True)
        AuthAPI-->>Produtor: HTTP 202 Accepted
    end
    Produtor->>AuthAPI: POST /api/v1/auth/login (email, senha)
    AuthAPI->>DB: SELECT * FROM usuarios + Verifica bcrypt
    AuthAPI->>SessDB: INSERT INTO sessoes_ativas (tenant_id=NULL, status="ATIVA")
    AuthAPI-->>Produtor: HTTP 200 OK + JWT (account_type=INDIVIDUAL_FREE) + Cookie HttpOnly
    Produtor->>App: Navegação no PWA Agro (Clima, Mercado, Calculadoras)
    Note over App,AuthAPI: GAP AUDITADO: PWA não envia Bearer nem x-user-activity.<br/>Middleware pula rotas públicas. Heartbeat NÃO é renovado!
```
- **Contratos:** `FreeUserCreateRequest`, `LoginRequest`, `TokenResponse`, `UsuarioMeResponse`.
- **Dependências:** `AuthService`, `LoginRateLimitService`, `cookie_service`.
- **Riscos Identificados:** Inatividade aparente de usuários legítimos no painel de observabilidade devido à ausência de renovação do heartbeat em rotas públicas.
- **Testes Existentes:** `test_free_registration.py`, `test_unified_identity_foundation.py`, `test_homologacao_01b2c_e2e_fluxos.py`.

---

### 3.2 Fluxo 2: Configuração Administrativa → Serviço Público → PWA Agro
- **Caminho:** Admin altera comunicados ou feature flags no Backoffice (`PUT /api/v1/backoffice/agro/configuracoes/*`) $\rightarrow$ Gravado em `configuracoes_saas` com optimistic lock (`revision`) $\rightarrow$ Cache L1 invalidado $\rightarrow$ Registro em `AdminAuditLog` $\rightarrow$ PWA consome `GET /api/v1/public/agro/config` $\rightarrow$ Salva em `localStorage` (`deepfarms_agro_config_v1`) $\rightarrow$ Exibe avisos e respeita flags.
- **Integridade Legal:** Os avisos legais do DERAL, PTAX, BCB e IBGE são injetados de forma imutável pelo backend, impedindo remoção acidental.
- **Testes Existentes:** `test_01e5_institutional_messages_crud_and_audit`, `test_01e5_public_agro_config_and_vigencia`.

---

### 3.3 Fluxo 3: Credencial Climática → Seleção de Provedor → Fallback
- **Caminho:** Admin cadastra chave no Backoffice (`POST /api/v1/backoffice/agro/provedores/clima/credenciais`) $\rightarrow$ `PlatformWeatherCredentialsService` cifra com AES-256-GCM (KEK v2) $\rightarrow$ `DynamicWeatherOrchestrator` decifra em memória sob demanda $\rightarrow$ Requisição pública de clima `GET /api/v1/public/clima/previsao` $\rightarrow$ Consulta `ClimaCache` (Redis L2 $\rightarrow$ Memória L1) $\rightarrow$ Se miss, chama Open-Meteo $\rightarrow$ Em caso de falha/timeout upstream, orquestrador aciona provedor de contingência configurado (WeatherAPI ou INMET) $\rightarrow$ Telemetria registra falhas e consumo em `ClimaCache`.
- **Gaps Identificados:**
  - Se a KEK for alterada sem execução prévia de rotação, todas as chaves existentes são invalidadas.
  - A contabilização de quotas no `ClimaCache` é puramente observacional; não há corte forçado (*hard-stop*) para impedir faturamento excedente por chamadas upstream abusivas.
- **Testes Existentes:** `test_platform_weather_credentials_rotation_reencryption`, `test_clima_publico.py`.

---

### 3.4 Fluxo 4: Upload DERAL → Validação → Aprovação → Publicação → Consumo
- **Caminho:** Admin envia planilha `.xls` ou `.json` (`POST /api/v1/backoffice/agro/mercado/deral/snapshots/upload`) $\rightarrow$ Validação de cabeçalho binário OLE2, decodificação BIFF8 via `xlrd`, extração de 21 commodities $\rightarrow$ Snapshot gravado com status `VALIDADO` e `estado_aprovacao = 'PENDENTE'` $\rightarrow$ Admin inspeciona itens $\rightarrow$ Admin aprova (`POST .../aprovar`) $\rightarrow$ Admin ativa (`POST .../ativar`) $\rightarrow$ Snapshot torna-se ativo no índice $\rightarrow$ Cache de preços é invalidado $\rightarrow$ Endpoints públicos `/api/v1/public/mercado/precos` e `/catalogo` entregam as novas cotações.
- **Gaps Identificados:**
  - Armazenamento dos bytes originais em base64 na tabela `configuracoes_saas` gera inchaço (*bloat*) no PostgreSQL.
  - A validação de proveniência checa apenas se o domínio informado na URL pertence a `*.pr.gov.br`, sem capacidade de verificar assinatura digital do arquivo original.
- **Testes Existentes:** `test_deral_snapshot_upload_and_strict_validation_success`, `test_deral_snapshot_atomic_activation_and_cache_invalidation`, `test_paridade_snapshot_deral.py`.

---

### 3.5 Fluxo 5: Catálogo Global → Consumidor Agro vs Consumidor Comercial
- **Caminho:** Admin cria ou altera Commodity/Unidade (`/api/v1/backoffice/agro/catalogo/*`) $\rightarrow$ Validação de unicidade de `codigo` e `nome` $\rightarrow$ Persistência estrita com `tenant_id = NULL` e `sistema = True` $\rightarrow$ Tentativa de exclusão de registro em uso é bloqueada com HTTP 409 Conflict $\rightarrow$ Agro PWA consome os registros canônicos para cálculos $\rightarrow$ Tenants comerciais utilizam os registros canônicos como biblioteca mestre para operações de campo (`caderno_campo`, `estoque`).
- **Gaps Identificados:** Inativação (`ativo = False`) de uma commodity global não gera aviso prévio aos tenants comerciais que possam ter plantios ativos atrelados a ela.
- **Testes Existentes:** `test_01e5_catalog_multi_tenant_isolation`, `test_01e5_referential_integrity_prevent_delete`.

---

## 4. Achados Classificados por Severidade

```mermaid
pie title Distribuição de Achados por Severidade
    "BLOCKER (0)" : 0
    "HIGH (2)" : 2
    "MEDIUM (4)" : 4
    "LOW (3)" : 3
```

### 4.1 Correções Obrigatórias Antes de Staging (Pré-Staging)
*Nenhum achado classificado como BLOCKER impede o deploy em ambiente de staging isolado.*

---

### 4.2 Correções Obrigatórias Antes de Produção (Pré-Produção)

#### [ACHADO-01] [HIGH] Telemetria de Sessões Ativas do Agro Não Atualizada Durante o Uso
- **Componente:** `services/api/main.py:186-245` (`SessionHeartbeatMiddleware`) e `apps/agro`.
- **Descrição:** O middleware de heartbeat ignora todas as rotas com prefixo `/api/v1/public/` e `/api/v1/agro/`, exige o cabeçalho `Authorization: Bearer` (o PWA opera com cookies `HttpOnly`) e requer a flag `x-user-activity: true` (ausente no frontend Agro). Com isso, sessões de usuários gratuitos mantêm `ultimo_heartbeat` congelado na data/hora do login.
- **Impacto no Dashboard:** Os indicadores "Produtores Ativos Hoje" e "Produtores Ativos 7d" no dashboard 01F medem apenas *logins realizados*, subnotificando drasticamente o engajamento real de produtores recorrentes.
- **Correção Necessária:**
  1. Habilitar extração de token de sessão via cookie `deepfarms_agro_session` no `SessionHeartbeatMiddleware`.
  2. Criar endpoint leve de heartbeat `POST /api/v1/auth/heartbeat` disparado pelo PWA Agro periodicamente (ex: a cada 10 min de navegação ativa) ou atualizar o heartbeat em requisições autenticadas a `/api/v1/auth/me`.

#### [ACHADO-02] [HIGH] Ausência de Execução de Testes em Instâncias Reais de PostgreSQL e Redis
- **Componente:** Infraestrutura de testes e CI/CD.
- **Descrição:** Todos os testes unitários e de integração das fases 01B a 01F foram executados utilizando SQLite em memória (`aiosqlite`) e emulações locais de cache (`ClimaCache` com dicionário Python interno).
- **Impacto:** Não há validação empírica de concorrência com locks transacionais do PostgreSQL, comportamento dos tipos nativos `UUID` e `JSONB`, execução real de RLS sob múltiplos workers, nem comportamento do Redis L2 contra *cache stampede* com múltiplos processos simultâneos.
- **Correção Necessária:** Execução da suíte completa de testes no ambiente de Staging configurado com containers dedicados de PostgreSQL 16 e Redis 7.

#### [ACHADO-03] [MEDIUM] Ausência de Bloqueio Rígido (*Hard-Stop*) de Quotas de APIs Upstream
- **Componente:** `services/api/public_clima/cache.py` e `public_clima/dynamic_orchestrator.py`.
- **Descrição:** O sistema contabiliza as chamadas upstream em `ClimaCache` e alerta no dashboard quando os limites configurados são atingidos. Contudo, não há mecanismo de interceptação que corte ou force contingência automática quando a cota mensal é estourada.
- **Impacto:** Risco financeiro de cobrança excedente de terceiros (ex: WeatherAPI) em caso de requisições anômalas ou scraping não detectado.
- **Correção Necessária:** Interceptar requisições no `DynamicWeatherOrchestrator` quando `upstream_calls_month >= monthly_limit`, acionando contingência para Open-Meteo (livre) ou emitindo resposta amigável de cota esgotada.

#### [ACHADO-04] [MEDIUM] Armazenamento de Arquivos Binários Grandes no Banco Relacional
- **Componente:** `services/api/core/services/deral_snapshot_service.py:320-360`.
- **Descrição:** Planilhas originais `.xls` e payloads `.json` do DERAL (de até 5 MB cada) são codificados em base64 e armazenados diretamente dentro da coluna JSON `valor` da tabela `configuracoes_saas`.
- **Impacto:** Inchaço desnecessário da tabela de configurações operacionais, saturação desnecessária de memória nos workers ao ler a chave de configuração e degradação de performance nos backups e WAL do PostgreSQL.
- **Correção Necessária:** Em produção, transferir o armazenamento dos bytes originais para um bucket de Object Storage (MinIO em staging / S3 em prod), mantendo no PostgreSQL apenas os metadados, o hash SHA-256 e a URL do objeto.

#### [ACHADO-05] [MEDIUM] Derivação de KEK sem KMS Dedicado em Ambiente de Produção
- **Componente:** `services/api/core/services/platform_weather_credentials.py:48-77`.
- **Descrição:** A KEK v2 utilizada para cifrar as chaves de API climáticas deriva via HKDF da variável `platform_credentials_master_key` com fallback automático para `jwt_secret_key`.
- **Impacto:** Se o operador rotacionar a chave de JWT sem definir `platform_credentials_master_key`, as credenciais climáticas salvas tornam-se indecifráveis.
- **Correção Necessária:** Tornar obrigatória a presença de `PLATFORM_CREDENTIALS_MASTER_KEY` isolada no ambiente de staging/produção e desativar o fallback para `JWT_SECRET_KEY` fora de ambientes de teste local.

#### [ACHADO-06] [MEDIUM] Proveniência DERAL Restrita a Validação Heurística de Domínio
- **Componente:** `services/api/core/services/deral_snapshot_service.py:67-75`.
- **Descrição:** O DERAL/SEAB-PR não disponibiliza assinaturas digitais criptográficas (ICP-Brasil/X.509) em suas planilhas `.xls`. A verificação de proveniência limita-se a conferir se a URL declarada pertence a `*.pr.gov.br`.
- **Impacto:** O upload manual de planilhas depende criticamente da idoneidade e atenção do administrador que revisa e aprova o snapshot.
- **Mitigação Recomendada:** Preservar a exigência de aprovação manual em dois passos (`VALIDADO` $\rightarrow$ `APROVADO`) e registrar em auditoria forense o IP e ID do administrador que autorizou a publicação.

---

### 4.3 Melhorias Não Bloqueantes

#### [ACHADO-07] [LOW] Inexistência de Coluna de Soft-Delete para Usuários Gratuitos
- A inativação de contas ocorre via `ativo = False`, sem timestamp de auditoria de desativação (`desativado_em`).
- *Recomendação:* Adicionar coluna `desativado_em` em futuras migrations de governança cadastral.

#### [ACHADO-08] [LOW] Ausência de Notificação Prévia de Inativação de Commodities Globais
- Inativar uma commodity em `/dashboard/backoffice/agro/catalogo` afeta imediatamente os seletores sem alertar tenants que possam ter colheitas recentes registradas com aquele código.
- *Recomendação:* Exibir aviso na UI informando quantos tenants possuem registros associados à commodity antes de confirmar a inativação.

#### [ACHADO-09] [LOW] Inconsistência Menor na Série Temporal do Dashboard sob Virada de Mês
- O bucket de 30 dias utiliza `datetime.now(timezone.utc)` e janelas baseadas em dias corridos, o que pode apresentar ligeira variação visual em fusos horários extremos de produtores (ex: UTC-4 no Acre e Mato Grosso).
- *Recomendação:* Aceitar fuso horário opcional na query string para ajuste da agregação visual diária.

---

## 5. Divergências Entre Relatórios e Código Real

A auditoria forense identificou divergências entre as afirmações documentadas nos relatórios anteriores e a realidade comprovada no código:

| Item | Afirmação no Relatório Anterior | Realidade Comprovada no Código | Impacto / Gravidade |
|---|---|---|---|
| **Sessões e Heartbeat** | Relatório 01F: "Métricas baseadas no batimento de sessões (`SessaoAtiva`) com atualização a cada interação." | O `SessionHeartbeatMiddleware` ignora explicitamente `/api/v1/public/` e `/api/v1/agro/`, e não lê cookies. O heartbeat do PWA **nunca é atualizado** após o login. | **ALTO:** Usuários ativos 24h/7d refletem apenas novos logins, não o uso real. |
| **Sincronização Multi-Worker** | Relatório 01F: "APROVADO — Sincronização multi-worker comprovada em testes automatizados." | O teste `test_multiworker_db_discovery_reconciliation` instanciou 2 objetos Python dentro do **mesmo processo** compartilhando a mesma sessão SQLite em memória. Nunca foi testado com processos de SO independentes. | **MÉDIO:** Mecanismo arquitetural é correto, mas a aprovação foi prematura. |
| **Retenção de Documentos** | Relatório 01F: "APROVADO — Retenção dos documentos originais com integridade SHA-256." | Os documentos são salvos como strings base64 no campo JSON de uma tabela de configurações. Não há política de retenção (WORM, cold-storage, ciclo de expiração ou expurgo). | **MÉDIO:** Aprovação indevida de política de retenção quando apenas existia persistência em banco. |
| **Proveniência DERAL** | Relatório 01F: "APROVADO — Validação estrita de domínios governamentais homologados." | Validação limita-se a um regex de URL declarada pelo usuário. Não há validação da autenticidade intrínseca do documento binário. | **MÉDIO:** A rotulagem como "Aprovado" gerava falsa sensação de blindagem criptográfica. |
| **Build Integrado** | Relatório 01F: "APROVADO — Build e testes integrados aprovados (tsc --noEmit)." | Na fase 01F, apenas `tsc --noEmit` havia sido rodado. O build real de empacotamento (`next build`) não havia sido executado nem documentado. | **RESOLVIDO EM 01G:** Build real executado com sucesso em ambos os frontends durante esta auditoria. |

---

## 6. Revisão Crítica da Matriz de Homologação (11 Itens)

Seguindo estritamente a instrução mandatória da fase 01G:
- **APROVADO:** Somente itens com evidência cabal, suficiente e reproduzível.
- **PARCIAL:** Implementação existente no código, mas validação incompleta ou dependente de testes distribuídos reais.
- **PENDENTE:** Sem comprovação adequada no ambiente atual.
- **BLOQUEADO:** Dependência técnica não resolvida que impede o funcionamento.

### 6.1 Análise Detalhada Item a Item

#### Item 1: Chave Mestra Dedicada e Rotação
- **Requisito Original:** Segregação criptográfica da chave mestra da plataforma, com suporte a rotação de versão e decifração sem downtime de credenciais salvas.
- **Implementação Encontrada:** [`PlatformWeatherCredentialsService:48-77`](file:///opt/lampp/htdocs/farm/services/api/core/services/platform_weather_credentials.py#L48-L77) com KEK v2 derivada via HKDF (`SALT_PLATFORM_V2`, `INFO_PLATFORM_V2`) e suporte a re-encriptação de v1 para v2.
- **Teste Existente:** `test_platform_weather_credentials_rotation_reencryption` em `test_backoffice_agro_01e3a.py`.
- **Ambiente Utilizado:** Pytest local com chaves de teste em memória.
- **Evidência Verificável:** Algoritmo AES-256-GCM com HKDF comprovado via unit tests.
- **Lacuna Residual:** Não há integração com serviço de KMS externo (AWS KMS / HashiCorp Vault) e o código aceita fallback para `jwt_secret_key` se a chave dedicada não for informada.
- **Ação para Aprovação:** Configurar chave mestra dedicada obrigatória em Staging/Produção sem fallback e documentar o procedimento operacional de rotação.
- **Classificação:** **PARCIAL**

#### Item 2: Licenciamento dos Provedores
- **Requisito Original:** Conformidade jurídica, termos de uso e licenciamento comercial dos provedores de dados climáticos (Open-Meteo CC-BY 4.0, WeatherAPI, INMET).
- **Implementação Encontrada:** Atribuição textual CC-BY 4.0 embutida no frontend e adapters modulares implementados para múltiplos fornecedores.
- **Teste Existente:** Validação de strings de atribuição e respostas nos testes unitários de clima.
- **Ambiente Utilizado:** Testes unitários com mocks HTTP.
- **Evidência Verificável:** Código-fonte dos adaptadores meteorológicos.
- **Lacuna Residual:** A conformidade com termos comerciais de redistribuição da WeatherAPI para o modelo de SaaS e a formalização dos limites corporativos não foram validadas pelo time jurídico/comercial.
- **Ação para Aprovação:** Assinatura formal de planos empresariais junto aos provedores pagos.
- **Classificação:** **PARCIAL**

#### Item 3: Contabilização de Cotas
- **Requisito Original:** Medição atômica e distribuída do volume de chamadas upstream consumidas, com prevenção de faturamento excessivo.
- **Implementação Encontrada:** Contadores atômicos em `ClimaCache` (`record_upstream_call`) operando em Redis com fallback em memória.
- **Teste Existente:** `test_clima_cache_metrics` em suíte unitária.
- **Ambiente Utilizado:** Local (Redis desligado, testado no fallback em memória).
- **Evidência Verificável:** Métodos de incremento e leitura implementados em `cache.py`.
- **Lacuna Residual:** Ausência de teste sob carga concorrente com Redis real e inexistência de corte forçado (*hard-cutoff*) na exaustão da cota.
- **Ação para Aprovação:** Implementar trava ativa de esgotamento de quota e testar concorrência distribuída no Redis de Staging.
- **Classificação:** **PARCIAL**

#### Item 4: Proveniência de Documentos DERAL
- **Requisito Original:** Garantir a autenticidade e procedência governamental oficial dos levantamentos de preços do DERAL/SEAB-PR.
- **Implementação Encontrada:** Filtro de domínios governamentais homologados (`pr.gov.br`, `agricultura.pr.gov.br`, `seab.pr.gov.br`) e segregação de proveniência em `deral_snapshot_service.py:67-75`.
- **Teste Existente:** `test_verificar_proveniencia_governamental_unitario` em `test_backoffice_agro_01e4a.py`.
- **Ambiente Utilizado:** Testes unitários sintéticos.
- **Evidência Verificável:** Rejeição de URLs fora dos domínios oficiais.
- **Lacuna Residual:** Checagem restrita a string de URL; arquivos `.xls` não possuem assinatura digital da SEAB-PR.
- **Ação para Aprovação:** Manter fluxo de aprovação administrativa em duas etapas com auditoria do operador responsável.
- **Classificação:** **PARCIAL**

#### Item 5: Teste com XLS Oficial Válido
- **Requisito Original:** Decodificação fiel da planilha binária oficial BIFF8/OLE2 (`prp.xls`) com extração das 21 commodities.
- **Implementação Encontrada:** Parser nativo com `xlrd` validando magic number `\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1`, inspeção da aba `Rav`, cabeçalho "Rav!X2" == "MÉDIA", e quantização decimal com `ROUND_HALF_UP`.
- **Teste Existente:** `test_deral_snapshot_upload_and_strict_validation_success`, `test_rejeicao_de_xls_ole2_corrompido`, `test_paridade_snapshot_deral.py`.
- **Ambiente Utilizado:** Suíte automatizada com amostras binárias reais do DERAL.
- **Evidência Verificável:** Extração comprovada célula a célula com 100% de paridade.
- **Lacuna Residual:** Nenhuma técnica impeditiva.
- **Ação para Aprovação:** Nenhuma ação adicional requerida.
- **Classificação:** **APROVADO**

#### Item 6: PostgreSQL Real
- **Requisito Original:** Validação completa das entidades, relacionamentos, constraints, RLS e concorrência sobre instância real do PostgreSQL 15+.
- **Implementação Encontrada:** Modelos mapeados via SQLAlchemy para dialeto PostgreSQL (`Uuid(as_uuid=True)`, `JSON`, tipos nativos). Script isolado `homologar_postgresql_ci.py` existente.
- **Teste Existente:** Script `homologar_postgresql_ci.py` (requer `TEST_DATABASE_URL`).
- **Ambiente Utilizado:** Todos os testes das fases 01B–01F rodaram em SQLite em memória (`aiosqlite`).
- **Evidência Verificável:** Nenhuma evidência de execução da suíte completa de Backoffice contra PostgreSQL real.
- **Lacuna Residual:** Execução e validação da suíte em container PostgreSQL dedicado.
- **Ação para Aprovação:** Executar suíte completa no ambiente de Staging contra PostgreSQL descartável.
- **Classificação:** **PENDENTE**

#### Item 7: Redis Real
- **Requisito Original:** Validação de cache L2 distribuído, controle de expiração (TTL), lock assíncrono (*single-flight*) e invalidação multi-processo sobre Redis real.
- **Implementação Encontrada:** Clientes assíncronos implementados em `ClimaCache`, `macro_cache.py`, `sidra_cache.py` e `deral_snapshot_service.py`.
- **Teste Existente:** Testes unitários com Redis mockado ou operando em modo de fallback L1.
- **Ambiente Utilizado:** Local (sem Redis ativo na porta 6379 durante os testes).
- **Evidência Verificável:** Nenhuma evidência de teste sob cluster ou instância real de Redis.
- **Lacuna Residual:** Teste de invalidação distribuída e partição de rede com Redis real ativo.
- **Ação para Aprovação:** Executar testes em Staging com container Redis 7 ativo.
- **Classificação:** **PENDENTE**

#### Item 8: Sincronização Multi-Worker
- **Requisito Original:** Garantir que múltiplos workers FastAPI independentes reconciliem e invalidem caches de configuração e snapshots DERAL sem divergência.
- **Implementação Encontrada:** Método `sync_active_snapshot_from_db` consultando `ConfiguracaoSaaS` diretamente no banco em caso de cache miss ou reinicialização.
- **Teste Existente:** `test_multiworker_db_discovery_reconciliation` em `test_backoffice_agro_01e4a.py`.
- **Ambiente Utilizado:** Processo Python único instanciando dois objetos de serviço sequencialmente.
- **Evidência Verificável:** Lógica de reconciliação presente no código.
- **Lacuna Residual:** Não foi testado com múltiplos processos concorrentes (múltiplos workers Uvicorn / containers) competindo por escrita e invalidação.
- **Ação para Aprovação:** Teste de carga com 2 workers Uvicorn independentes no ambiente de Staging.
- **Classificação:** **PARCIAL**

#### Item 9: Retenção dos Documentos Originais
- **Requisito Original:** Política de retenção, integridade e imutabilidade dos documentos oficiais brutos para auditoria forense.
- **Implementação Encontrada:** Armazenamento dos bytes em base64 na tabela `configuracoes_saas` e recálculo de hash em `GET /deral/snapshots/{id}/verify-integrity`.
- **Teste Existente:** `test_snapshot_verify_integrity_and_download_raw` em `test_backoffice_agro_01e4a.py`.
- **Ambiente Utilizado:** SQLite em memória.
- **Evidência Verificável:** Recálculo e conferência exata do hash SHA-256.
- **Lacuna Residual:** Não há política formal de retenção (prazos de guarda, expurgo legal, WORM ou separação para Object Storage).
- **Ação para Aprovação:** Migrar o payload bruto para Object Storage e formalizar a política de guarda de 5 anos para documentos públicos oficiais.
- **Classificação:** **PARCIAL**

#### Item 10: Integridade dos Catálogos Globais
- **Requisito Original:** Blindagem contra duplicidade de códigos/nomes, proteção referencial contra exclusão física de itens em uso e isolamento multi-tenant (`tenant_id = NULL`).
- **Implementação Encontrada:** [`backoffice_agro_catalogo.py`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro_catalogo.py) com validação prévia de conflito, conferência em tabelas dependentes (`UnidadeMedidaConversao`, `Insumo`, etc.) com rejeição HTTP 409 Conflict, e registro em `AdminAuditLog`.
- **Teste Existente:** `test_01e5_duplicate_code_protection`, `test_01e5_referential_integrity_prevent_delete`, `test_01e5_catalog_multi_tenant_isolation`.
- **Ambiente Utilizado:** Pytest local com validações transacionais completas.
- **Evidência Verificável:** 4 testes unitários dedicados cobrindo todos os cenários de barreira e integridade.
- **Lacuna Residual:** Nenhuma técnica impeditiva.
- **Ação para Aprovação:** Nenhuma ação adicional requerida.
- **Classificação:** **APROVADO**

#### Item 11: Build e Testes Integrados Web/Agro
- **Requisito Original:** Build determinístico de produção, typecheck estrito (zero erros) e empacotamento completo de todas as aplicações sem erros de SSR ou bundling.
- **Implementação Encontrada:**
  - `pnpm --filter web exec tsc --noEmit`: 0 erros.
  - `pnpm --filter web build`: Next.js 16.1.6 compilado em 2.7 minutos com 270 rotas validadas com sucesso (código 0).
  - `pnpm --filter agro build`: Next.js 16.1.6 compilado em 11 segundos com 10 rotas validadas com sucesso (código 0).
  - Suíte de 33 testes unitários no backend: 100% aprovados.
- **Teste Existente:** Execução real dos comandos de build dos pacotes durante esta auditoria (tasks `3356` e `3425`).
- **Ambiente Utilizado:** Ambiente de desenvolvimento do monorepo.
- **Evidência Verificável:** Bundles gerados em `.next` e logs dos processos com exit code 0.
- **Lacuna Residual:** Nenhuma técnica impeditiva.
- **Ação para Aprovação:** Nenhuma ação adicional requerida.
- **Classificação:** **APROVADO**

---

### 6.2 Quadro Comparativo e Recálculo Objetivo do Percentual de Homologação

| Item | Descrição do Requisito | Status Reportado na 01F | Status Recalculado na 01G | Justificativa da Reclassificação |
|:---:|---|:---:|:---:|---|
| **1** | Chave Mestra Dedicada e Rotação | `EM VALIDAÇÃO` | **PARCIAL** | KEK v2 implementada; falta KMS em nuvem e cron de rotação. |
| **2** | Licenciamento dos Provedores | `EM VALIDAÇÃO` | **PARCIAL** | Adapters implementados; pendente formalização contratual corporativa. |
| **3** | Contabilização de Cotas | `EM VALIDAÇÃO` | **PARCIAL** | Telemetria funcional; falta trava ativa (*hard-cutoff*) e teste concorrente. |
| **4** | Proveniência de Documentos DERAL | `APROVADO` | **PARCIAL** | Reclassificado: validação é apenas heurística de URL, sem assinatura digital. |
| **5** | Teste com XLS Oficial Válido | `APROVADO` | **APROVADO** | Parser BIFF8 OLE2 nativo validado célula a célula com dados reais. |
| **6** | PostgreSQL Real | `PENDENTE` | **PENDENTE** | Testes rodaram em SQLite em memória; validação em PG aguarda Staging. |
| **7** | Redis Real | `EM VALIDAÇÃO` | **PENDENTE** | Reclassificado: 100% dos testes rodaram com Redis desligado / fallback L1. |
| **8** | Sincronização Multi-Worker | `APROVADO` | **PARCIAL** | Reclassificado: testado apenas em processo único; falta validação multi-processo. |
| **9** | Retenção dos Documentos Originais | `APROVADO` | **PARCIAL** | Reclassificado: bytes em tabela SaaS não configuram política de retenção/WORM. |
| **10** | Integridade dos Catálogos Globais | `APROVADO` | **APROVADO** | Integridade referencial, bloqueio de conflito e isolamento 100% comprovados. |
| **11** | Build e Testes Integrados Web/Agro | `APROVADO` | **APROVADO** | Comprovado em 01G com `next build` e typecheck exit 0 em ambos os apps. |

```mermaid
pie title Matriz de Homologação Recalculada (AGRO-ADMIN-01G)
    "APROVADO (3)" : 3
    "PARCIAL (6)" : 6
    "PENDENTE (2)" : 2
    "BLOQUEADO (0)" : 0
```

- **Percentual Efetivamente APROVADO:** **27.3% (3 de 11)**  
  *(Aprovação plena restrita aos itens 5, 10 e 11, onde a evidência é cabal e irrevogável).*
- **Percentual em Estado PARCIAL:** **54.5% (6 de 11)**  
  *(Funcionalidade implementada no código, aguardando validação de infraestrutura ou processos externos).*
- **Percentual PENDENTE:** **18.2% (2 de 11)**  
  *(PostgreSQL e Redis reais, cuja validação requer o ambiente isolado de Staging).*
- **Percentual BLOQUEADO:** **0.0% (0 de 11)**  
  *(Nenhum impedimento arquitetural insolúvel).*

---

## 7. Evidências Técnicas Verificáveis

1. **Compilação Completa de Produção do Backoffice (`apps/web`):**
   ```bash
   pnpm --filter web build
   # Saída:
   # ▲ Next.js 16.1.6 (webpack)
   # ✓ Compiled successfully in 2.7min
   # ✓ Collecting page data using 7 workers in 4.2s
   # ✓ Generating static pages (270/270)
   # Exit Code: 0
   ```
2. **Compilação Completa de Produção do PWA Agro (`apps/agro`):**
   ```bash
   pnpm --filter agro build
   # Saída:
   # ▲ Next.js 16.1.6 (webpack)
   # ✓ Compiled successfully in 6.2s
   # ✓ Finished TypeScript in 8.2s
   # ✓ Generating static pages (10/10)
   # Exit Code: 0
   ```
3. **Execução Integral da Suíte de Regressão Pytest (33 Testes):**
   ```bash
   services/api/.venv/bin/python3.10 -m pytest \
     services/api/tests/unit/core/test_backoffice_agro_01e4.py \
     services/api/tests/unit/core/test_backoffice_agro_01e4a.py \
     services/api/tests/unit/core/test_backoffice_agro_01e5.py \
     services/api/tests/unit/core/test_backoffice_agro_01f.py -v
   # Saída:
   # ========================= 33 passed in 18.73s =========================
   ```
4. **Isolamento de Identidade na Camada de Dados:**
   - Comprovado em `services/api/core/routers/backoffice_agro_dashboard.py:80-90`:
     ```python
     subq_commercial = select(TenantUsuario.usuario_id).distinct()
     base_filter = [
         Usuario.is_superuser == False,
         Usuario.id.not_in(subq_commercial),
     ]
     ```
   - Garante que nenhum usuário de tenant comercial contratado ou superusuário de plataforma seja computado nas estatísticas de produtores gratuitos.

---

## 8. Plano de Homologação em Staging Isolado

O plano de homologação tem por finalidade validar todos os componentes em ambiente descartável idêntico à produção, sem compartilhar bancos de dados comerciais ou instâncias de mensageria.

### 8.1 Topologia de Staging Isolada (Docker Compose)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   STAGING ENVIRONMENT (ISOLADO)                        │
│                                                                        │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │   PostgreSQL 16  │    │     Redis 7      │    │  MinIO (Storage) │  │
│  │   Porta 5433     │    │    Porta 6380    │    │    Porta 9000    │  │
│  │  DB: staging_db  │    │  Auth: testpass  │    │  Bucket: deral   │  │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘  │
│           │                       │                       │            │
│  ┌────────┴───────────────────────┴───────────────────────┴─────────┐  │
│  │                     API Core (2 Workers Uvicorn)                 │  │
│  │                  Porta 8001 (Worker A) / Porta 8002 (Worker B)   │  │
│  └────────┬───────────────────────────────────────────────┬─────────┘  │
│           │                                               │            │
│  ┌────────┴──────────────────┐                ┌───────────┴─────────┐  │
│  │    Backoffice Web         │                │     DeepFarms Agro  │  │
│  │   Next.js (Porta 3001)    │                │   Next.js (Porta 3005)│  │
│  └───────────────────────────┘                └─────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Passos Executáveis de Preparação:
1. **Subir Infraestrutura Isolada:**
   ```bash
   docker run -d --name pg-agro-staging -e POSTGRES_DB=agro_staging -e POSTGRES_PASSWORD=stagingpass -p 5433:5432 postgres:16-alpine
   docker run -d --name redis-agro-staging -p 6380:6379 redis:7-alpine
   ```
2. **Executar Migrations Alembic no Banco de Staging:**
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres:stagingpass@localhost:5433/agro_staging" \
   alembic upgrade head
   ```
3. **Iniciar Duas Instâncias da API (Simulação Multi-Worker Real):**
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres:stagingpass@localhost:5433/agro_staging" \
   REDIS_URL="redis://localhost:6380/0" \
   PLATFORM_CREDENTIALS_MASTER_KEY="staging_master_key_32_bytes_hex_mock!!" \
   uvicorn main:app --port 8001 &

   DATABASE_URL="postgresql+asyncpg://postgres:stagingpass@localhost:5433/agro_staging" \
   REDIS_URL="redis://localhost:6380/0" \
   PLATFORM_CREDENTIALS_MASTER_KEY="staging_master_key_32_bytes_hex_mock!!" \
   uvicorn main:app --port 8002 &
   ```

---

## 9. Testes E2E Necessários em Staging

| ID | Cenário de Teste E2E | Passos de Execução | Critério Objetivo de Sucesso |
|---|---|---|---|
| **E2E-01** | Ciclo Completo de Snapshot DERAL com Multi-Worker | 1. Upload e aprovação de planilha `.xls` no Worker A (porta 8001).<br/>2. Ativação do snapshot no Worker A.<br/>3. Consulta imediata de catálogo no Worker B (porta 8002). | Worker B entrega imediatamente os 21 preços novos sem reinicialização de processo, comprovando reconciliação distribuída via Redis/DB. |
| **E2E-02** | Resiliência contra Indisponibilidade de Redis | 1. Pausar container do Redis (`docker pause redis-agro-staging`).<br/>2. Realizar consulta de cotações e clima no Agro PWA.<br/>3. Acessar Dashboard Executivo no Backoffice. | APIs respondem sem HTTP 500 recorrendo ao fallback de memória L1. Dashboard exibe alerta `INFRA-REDIS-OFFLINE`. Retorno normal após `unpause`. |
| **E2E-03** | Validação de Heartbeat de Produtor no PWA | 1. Criar novo usuário gratuito e logar no Agro PWA.<br/>2. Navegar por 15 minutos em Clima e Mercado.<br/>3. Verificar timestamp de `ultimo_heartbeat` em `sessoes_ativas`. | `ultimo_heartbeat` avança dinamicamente; produtor é contabilizado em "Ativos Hoje" no Dashboard 01F. |
| **E2E-04** | Contingência Climática Automática | 1. Configurar Open-Meteo como primário e simular falha (bloqueio de saída DNS).<br/>2. Requisitar previsão no PWA.<br/>3. Inspecionar telemetria. | Sistema retorna dados via WeatherAPI (contingência) de forma transparente. Dashboard registra 1 evento de falha e badge de contingência. |
| **E2E-05** | Isolamento Estrito de RLS em PostgreSQL Real | 1. Autenticar usuário `INDIVIDUAL_FREE`.<br/>2. Tentar invocar rota comercial privada com injeção manual de `tenant_id` no cabeçalho. | Rejeição imediata com HTTP 403 Forbidden antes da aquisição de sessão RLS. Zero vazamento de dados de clientes comerciais. |

---

## 10. Estimativa de Esforço por Correção

| ID | Tarefa de Correção | Prioridade | Esforço Estimado | Complexidade |
|---|---|---|:---:|:---:|
| **CORR-01** | Ajustar `SessionHeartbeatMiddleware` e PWA para atualizar heartbeat via cookie ou rota `/auth/heartbeat` | **HIGH** | 4 horas | Baixa |
| **CORR-02** | Implementar corte forçado (*hard-cutoff*) de quotas upstream no `DynamicWeatherOrchestrator` | **MEDIUM** | 3 horas | Baixa |
| **CORR-03** | Configurar ambiente Docker Compose de Staging com PostgreSQL 16 e Redis 7 | **HIGH** | 4 horas | Média |
| **CORR-04** | Execução e homologação dos testes E2E multi-worker em Staging | **HIGH** | 6 horas | Média |
| **CORR-05** | Tornar `PLATFORM_CREDENTIALS_MASTER_KEY` estritamente obrigatória em staging/prod | **MEDIUM** | 2 horas | Baixa |
| **CORR-06** | Desacoplar payload binário do DERAL de `configuracoes_saas` para Object Storage | **MEDIUM** | 8 horas | Média |
| **CORR-07** | Adicionar coluna `desativado_em` para histórico de soft-delete de produtores | **LOW** | 2 horas | Baixa |
| **TOTAL** | **Esforço Total Estimado para Prontidão de Produção:** | — | **29 horas** | — |

---

## 11. Critérios Objetivos de GO / NO-GO

### Critérios para GO em Staging:
- [x] Ausência de erros de compilação ou empacotamento em `apps/web` e `apps/agro` (`next build` = 0).
- [x] 100% de aprovação na suíte de testes unitários de regressão (33/33).
- [x] Isolamento comprovado entre dados de usuários gratuitos e tenants comerciais.
- [x] Roteamento de Backoffice íntegro com RBAC granular ativo.
- **Veredicto para Staging:** **GO**

### Critérios para GO em Produção:
- [ ] Correção do heartbeat de sessões no PWA Agro implementada e validada (ACHADO-01).
- [ ] Suíte de testes E2E executada com sucesso contra PostgreSQL 16 e Redis 7 reais em Staging (ACHADO-02).
- [ ] Trava ativa (*hard-cutoff*) de quotas climáticas implementada (ACHADO-03).
- [ ] Chave mestra dedicada `PLATFORM_CREDENTIALS_MASTER_KEY` configurada em cofre seguro sem fallback para JWT (ACHADO-05).
- [ ] Formalização jurídica e limites corporativos aprovados para os provedores climáticos (Item 2).
- **Veredicto para Produção:** **NO-GO (Até conclusão do ciclo de Staging)**

---

## 12. Recomendação de Próxima Execução

Recomenda-se avançar para a fase **AGRO-ADMIN-01H — Correções Cirúrgicas e Homologação E2E em Staging**, com o seguinte roteiro de trabalho:

1. **Sprint 1 (Correções Cirúrgicas):**
   - Aplicar a correção do heartbeat de sessões no middleware e PWA (CORR-01).
   - Implementar o *hard-cutoff* de quotas meteorológicas upstream (CORR-02).
   - Tornar a chave mestra KEK mandatória sem fallback para JWT em staging/prod (CORR-05).
2. **Sprint 2 (Subida e Validação de Staging):**
   - Inicializar ambiente Docker Compose com PostgreSQL 16 e Redis 7 descartáveis.
   - Rodar a migration Alembic completa contra o banco PostgreSQL real.
   - Executar os testes E2E distribuídos multi-worker (E2E-01 a E2E-05).
3. **Sprint 3 (Auditoria Final e Go-Live):**
   - Atualizar a Matriz de Homologação para 100% dos itens técnicos como APROVADO com base nos logs de Staging.
   - Emitir o relatório final de prontidão de produção.

---
*Fim do Relatório AGRO-ADMIN-01G. Em estrita conformidade com as restrições da fase, nenhuma alteração de código, migration, commit, push, deploy ou modificação de dados compartilhados foi realizada.*
