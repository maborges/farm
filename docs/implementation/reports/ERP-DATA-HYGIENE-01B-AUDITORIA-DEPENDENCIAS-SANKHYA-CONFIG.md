# ERP-DATA-HYGIENE-01B — Auditoria de Dependências do SankhyaConfig

## 1. Resumo Executivo
O presente relatório documenta a auditoria de leitura do `SankhyaConfig`, estrutura legada e provider-specific utilizada pelo provider Sankhya. O objetivo foi mapear todos os consumidores desta estrutura para viabilizar a migração completa e segura para as estruturas canônicas do Core ERP, tais como `TenantIntegracao` e `IntegrationCredential`. A auditoria demonstrou que o runtime do Sankhya ainda depende fortemente do `SankhyaConfig` para autenticação, sincronização e manutenção de estado.

## 2. Escopo Auditado
Foram analisados os seguintes componentes relacionados ao provider Sankhya:
- **Model**: `SankhyaConfig` e logs associados (`SankhyaSyncLog`).
- **Schemas**: Schemas do provider baseados no `SankhyaConfig`.
- **Serviços de Autenticação**: `SankhyaGatewayAuthService`.
- **Serviços de Sincronização**: `SankhyaSyncService`, `SankhyaWSClient`, `SankhyaNFeFinanceiroService`.
- **Adapters e Reconciliação**: `SankhyaCanonicalAdapter`, `SankhyaLegacyReconciliation`.
- **Rotas e Workers**: Endpoints do provider e scripts legados.
- **Testes**: Testes de integração, auth, canonical adapter e readiness.

## 3. Inventário Completo do Model
O model `SankhyaConfig` (`sankhya_config`) possui os seguintes campos:
- `id` (Integer, PK)
- `tenant_id` (String, UK)
- `environment` (String)
- `api_base_url` (String)
- `auth_url` (String)
- `client_id` (String)
- `client_secret` (String, criptografado)
- `x_token` (String, criptografado)
- `token` (String, legado, criptografado)
- `appkey` (String, legado, criptografado)
- `ws_url` (String, legado)
- `username` (String, legado)
- `password` (String, legado, criptografado)
- `ativo` (Boolean)
- `ultimo_teste` (DateTime)
- `teste_status` (String)
- `sync_interval` (Integer)
- `ultimo_sync` (DateTime)
- `created_at` (DateTime)
- `updated_at` (DateTime)

## 4. Mapa de Consumidores
Os principais consumidores mapeados que leem, instanciam ou gravam o model `SankhyaConfig` são:
1. **`SankhyaGatewayAuthService` (`auth_service.py`)**: Consumidor de Leitura. Utiliza as URLs e credenciais para compor a requisição de login e obter tokens do Gateway e Legacy.
2. **`SankhyaSyncService` (`sync_service.py`)**: Consumidor de Leitura e Gravação. Instancia novos configs, atualiza campos operacionais (`ultimo_teste`, `ultimo_sync`), e fornece o config para os clients.
3. **`SankhyaWSClient` (`sync_service.py`)**: Consumidor de Leitura (via auth_service). Depende dos campos para realizar as conexões de webservice.
4. **`SankhyaCanonicalAdapter` (`canonical_adapter.py`)**: Consumidor de Leitura/Migração. Lê do `SankhyaConfig` para povoar as estruturas canônicas.
5. **`SankhyaNFeFinanceiroService` (`nfe_financeiro_service.py`)**: Consumidor de Leitura para execução de rotinas de negócio.
6. **Rotas e API (`routers/__init__.py`)**: Consumem via injeção de dependência para endpoints do provider.

## 5. Matriz Campo por Campo

| Campo ou uso atual | Consumidor | Operação realizada | Estrutura canônica de destino | Pode migrar agora? | Bloqueios ou pré-condições | Observações |
| ------------------ | ---------- | ------------------ | ----------------------------- | ------------------ | -------------------------- | ----------- |
| `id` / `tenant_id` | `SankhyaSyncService`, Adapters | Identidade e vinculo do tenant | `TenantIntegracao` | Sim | Necessita que os fluxos confiem no id de `TenantIntegracao` | Categoria TENANT_INTEGRATION_LIFECYCLE. |
| `environment` | `auth_service.py`, `sync_service.py` | Configuração técnica e payload de testes | `TenantIntegracao` (config_data) | Sim | Alterar leitura no construtor de clients/auth. | Categoria PROVIDER_CONFIGURATION. |
| `api_base_url` | `auth_service.py`, `SankhyaWSClient` | Base URL para requisições do Gateway/WS | `TenantIntegracao` (config_data) | Sim | O client precisará receber configurações canônicas em vez do model. | Categoria PROVIDER_CONFIGURATION. |
| `auth_url` | `auth_service.py` | Endpoint de login | `TenantIntegracao` (config_data) | Sim | Idem acima. | Categoria PROVIDER_CONFIGURATION. |
| `client_id` | `auth_service.py` | Identificador no Gateway OAuth | `IntegrationCredential` | Não | Depende da migração da lógica de auth para não receber `SankhyaConfig`. | Categoria CREDENTIAL. |
| `client_secret` | `auth_service.py` | Segredo (Gateway OAuth) | `IntegrationCredential` | Não | Idem acima. A gravação dupla pelo `canonical_adapter` está ativa. | Categoria CREDENTIAL. |
| `x_token` | `auth_service.py` | Token adicional (Gateway OAuth) | `IntegrationCredential` | Não | Idem acima. | Categoria CREDENTIAL. |
| `token`, `appkey` | `auth_service.py` | Auth para legacy login | `IntegrationCredential` | Não | Compatibilidade de legado. Alguns bancos SQLite podem não ter essas colunas ativas. | Categoria LEGACY_COMPATIBILITY. |
| `ws_url`, `username`, `password` | `auth_service.py` | Autenticação legada e WS Básico | `IntegrationCredential` e `TenantIntegracao` | Não | Necessidade de suportar tenants antigos não migrados. | Categoria LEGACY_COMPATIBILITY. |
| `ativo` | Rotas, `sync_service.py` | Filtro de tenants e status geral | `TenantIntegracao.status` | Sim | Migrar queries do sync_service para filtrar por `TenantIntegracao`. | Categoria TENANT_INTEGRATION_LIFECYCLE. |
| `ultimo_teste`, `teste_status` | `auth_service.py`, `canonical_adapter.py` | Cache visual do ultimo diagnostico | `IntegrationHealth` | Sim | A tabela de health já foi povoada via canonical adapter, mas a UI legada pode ainda consultar. | Categoria HEALTH_STATE. |
| `sync_interval` | `sync_service.py` (jobs schedule) | Define de quanto em quanto tempo o poll roda | `IntegrationSyncPolicy.trigger_expression` | Não | O worker/agendador legado ainda depende do `sync_interval` na tabela. | Categoria SYNC_POLICY. |
| `ultimo_sync` | `sync_service.py` | Verifica a ultima rodada bem sucedida | `IntegrationJob` | Não | Depende da consolidação total dos `IntegrationJob` no orchestrator. | Categoria JOB_STATE. |
| `created_at`, `updated_at` | Diversos | Auditoria básica | `TenantIntegracao` | Sim | Equivalente direto. | Categoria TENANT_INTEGRATION_LIFECYCLE. |

## 6. Fluxos Atuais de Leitura e Gravação
- **Gravação**: `SankhyaSyncService.criar_config` e updates no final de processos de sincronização (atualizando `ultimo_sync`). O `canonical_adapter.py` também realiza gravações secundárias simulando um trigger (cria canonical logs/health baseado nas configurações).
- **Leitura**: Em praticamente todo ciclo de sincronização ou auth (jobs de pessoas, produtos, financeiro). O config é lido e passado para o `SankhyaGatewayAuthService` ou instâncias de client API.
- **Gravação Dupla**: Identificou-se através do `canonical_adapter.py` (`_get_operational_config`) que há sync bidirecional/duplo onde os valores canônicos chegam a sobreescrever configurações operacionais do config legado no runtime.

## 7. Duplicidades com Estruturas Canônicas
1. **Credenciais**: Todos os tokens e senhas já possuem representação no `IntegrationCredential` (identificado pela lógica do `_apply_canonical_credential`).
2. **Health**: `ultimo_teste` e `teste_status` estão 1:1 duplicados em `IntegrationHealth`.
3. **Ambiente e URLs**: Duplicados dentro de propriedades JSON de `TenantIntegracao.config_data` via Schema.
4. **Agendamento**: `sync_interval` está semanticamente sobreposto a `IntegrationSyncPolicy.trigger_expression` (mas não efetivamente migrado).

## 8. Lacunas Encontradas (Unresolved)
- O agendador de jobs atual (workers) provavelmente ainda faz varreduras em `sankhya_config` onde `ativo = True` e compara `ultimo_sync` com `sync_interval` ao invés de usar o Lifecycle/Bootstrap Core.
- As credenciais mascaradas legadas dificultam a portabilidade 100% para o canônico sem ferir ambientes que ainda dependem do Basic Auth WS.

## 9. Riscos de Migração
- **Perda de Configuração de Autenticação**: O provider Sankhya tem 3 modelos de autenticação suportados simultaneamente (`gateway_oauth_client_credentials`, `gateway_legacy_login`, `legacy_ws_basic_auth`). Migrar abruptamente credenciais de autenticação pode romper clients existentes.
- **Rompimento de Jobs em Background**: O worker que executa a importação (pull) em intervalos baseados no `sync_interval` de `SankhyaConfig` irá parar se o model for removido sem adaptar o agendador.

## 10. Sequência Recomendada de Modernização
Recomenda-se a seguinte ordem:
1. **Etapa 1: Substituição do Health/Status**
   - **Escopo**: Substituir `ultimo_teste` e `teste_status` pelas leituras de `IntegrationHealth`.
   - **Critério**: O Dashboard do console acessa exclusivamente health canônico.
2. **Etapa 2: Migração de Leitura de Configuração Técnica**
   - **Escopo**: Alterar as fábricas de client HTTP e `auth_service.py` para receber um objeto `TenantIntegracao` em vez de `SankhyaConfig`.
   - **Riscos**: Interrupção temporária de login se o mapping for incorreto.
3. **Etapa 3: Consolidação de Credenciais**
   - **Escopo**: Alterar o `auth_service.py` para consultar apenas `IntegrationCredential` nativo via core ERP, sem fazer "fallback" bidirecional via adapter.
4. **Etapa 4: Eliminação do Sync Interval (Políticas)**
   - **Escopo**: Migrar a arquitetura de workers de poll do `SankhyaConfig` para as políticas canônicas em `IntegrationSyncPolicy`.
5. **Etapa 5: Eliminação do Legacy Compatibility e Tabela**
   - **Escopo**: Desativar a gravação dupla do adapter, remover a tabela `sankhya_config`.
   - **Possibilidade de Rollback**: Apenas recuperando o schema legado, os dados já estarão nas tabelas canônicas.

## 11. Critérios para considerar SankhyaConfig sem consumidores legítimos
O `SankhyaConfig` só poderá ser removido do código e os arquivos associados limpos quando:
1. A busca por `SankhyaConfig` no projeto retornar apenas o schema do SQLAlchemy/Migration (ou for completamente vazio).
2. O agendador rodar com base em `IntegrationJobTrigger` e `IntegrationSyncPolicy`.
3. Todos os clients (`SankhyaWSClient` etc.) aceitarem interfaces canônicas de credencial.
4. Nenhum teste unitário referenciar ou injetar dependência de config legado.

## 12. Veredicto Final
**GO PARA PLANEJAMENTO DA MIGRAÇÃO**

A auditoria mapeou as dependências e não há bloqueadores estruturais para a migração, mas existe forte acoplamento no runtime e nos agendadores. Uma execução faseada é obrigatória.
