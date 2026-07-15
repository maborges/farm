# ERP-ARCH-REASSESSMENT-01 — Auditoria Definitiva da Arquitetura, Runtime e Dependências Provider-Specific das Integrações ERP

## 1. Resumo executivo

### Veredicto

`GO COM RESSALVAS` para o piloto Sankhya atual.

`NO-GO MULTIPROVIDER` para introdução de um segundo ERP sem core repair prévio.

### Síntese objetiva

A arquitetura atual não é multi-provider em runtime, embora já exista uma base canônica relevante no domínio `integracoes`.

O repositório possui:

- persistência genérica real;
- catálogo genérico real de providers ERP;
- governança genérica real de associações;
- readiness parcialmente genérico;
- surface HTTP ERP nominalmente genérica, mas operacionalmente acoplada ao Sankhya;
- console frontend extensível em formato, porém ainda com contrato de configuração e fallback Sankhya.

Hoje, o Sankhya ainda atua em três papéis distintos:

1. provider específico legítimo;
2. provider default implícito;
3. fonte de verdade operacional de partes do runtime ERP.

O núcleo multi-provider existe como intenção arquitetural e como parte da persistência, mas ainda não existe como contrato de execução plenamente desacoplado.

### Decisão principal

Se um segundo ERP fosse iniciado hoje, não bastaria implementar apenas adapter, wrapper e schema provider-specific. Seriam necessárias mudanças indevidas em componentes centrais nominalmente genéricos, especialmente:

- `services/api/integracoes/erp/router.py`
- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/erp/erp-provider-registry.ts`
- `apps/web/src/components/integracoes/erp/capability-view-model.ts`
- `apps/web/src/components/integracoes/erp/sync-center-view-model.ts`
- `apps/web/src/components/integracoes/erp-timeline.tsx`

## 2. Contexto

Esta auditoria reavaliou a arquitetura ERP-First após os épicos anteriores de consolidação, com foco exclusivo em evidência estática de código, sem alteração de runtime produtivo, models, migrations, endpoints, adapters, testes ou documentação pré-existente.

Escopo auditado:

- backend `services/api/integracoes`
- frontend `apps/web/src/components/integracoes` e páginas correlatas
- wizard
- backoffice
- testes unitários/e2e de integração ERP
- documentação e guardrails associados

## 3. Metodologia

Critérios de classificação usados:

- imports e dependências reais;
- tipos públicos usados nos endpoints;
- serviços efetivamente chamados;
- tabelas e models consultados;
- fallback e defaults;
- branches provider-specific;
- fonte real de leitura e escrita;
- possibilidade de sobrevivência do componente sem a pasta Sankhya.

Validação documental executada:

- `git status --short`
- `git diff --check`
- `git -C apps/web diff --check`

Resultado durante esta auditoria antes da criação deste relatório:

- `git status --short`: sem modificações listadas;
- `git diff --check`: sem inconsistências;
- `git -C apps/web diff --check`: sem inconsistências.

## 4. Arquitetura real encontrada

## 4.1 Camadas reais

### Core ERP real

- `services/api/integracoes/models.py`
- `services/api/integracoes/schemas.py`
- `services/api/integracoes/marketplace_router.py`
- `services/api/integracoes/services/external_record_association_service.py`
- parte de `services/api/integracoes/erp_readiness_service.py`

### Superfície ERP nominal

- `services/api/integracoes/erp/router.py`
- `apps/web/src/components/integracoes/erp-console.tsx`

### Runtime provider-specific efetivo

- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`

### Persistência híbrida

- canônica: `TenantIntegracao`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth`, `IntegrationJob`, `IntegrationVersion`, `ExternalRecordAssociation`
- provider-specific/legada: `SankhyaConfig`, `SankhyaSyncLog`, tabelas staging Sankhya

## 4.2 Conclusão arquitetural

A arquitetura real é híbrida:

- o modelo de dados central já foi parcialmente canonicalizado;
- a resolução operacional do ERP ainda está concentrada no Sankhya;
- o router ERP ainda não é um dispatcher multi-provider;
- o frontend ainda não é um console realmente agnóstico.

## 5. Mapa de componentes

| Arquivo / grupo | Classificação | Responsabilidade observada |
| --- | --- | --- |
| `services/api/integracoes/models.py` | `CORE_ERP` | Modelos canônicos de integração |
| `services/api/integracoes/schemas.py` | `CORE_ERP` | Contratos públicos genéricos, inclusive schema de provider |
| `services/api/integracoes/marketplace_router.py` | `CORE_ERP` | Catálogo oficial de ERPs ativos |
| `services/api/integracoes/services/external_record_association_service.py` | `CORE_ERP` | Governança genérica de associações |
| `services/api/integracoes/erp_readiness_service.py` | `CORE_ERP` | Readiness canônico com regras fixas de capability |
| `services/api/integracoes/erp/router.py` | `GENERIC_NOMINAL` | Fachada HTTP ERP que delega só para Sankhya |
| `services/api/integracoes/sankhya/services/canonical_adapter.py` | `SANKHYA_SPECIFIC` + `CORE_TO_PROVIDER_LEAK` | Adapter Sankhya e lifecycle canônico acoplado |
| `services/api/integracoes/sankhya/services/sync_service.py` | `SANKHYA_SPECIFIC` + `SANKHYA_AS_SOURCE_OF_TRUTH` | Runtime operativo e ponte entre legado e canônico |
| `services/api/integracoes/sankhya/routers/__init__.py` | `SANKHYA_SPECIFIC_LEGITIMATE` | Endpoints do provider Sankhya |
| `services/api/integracoes/sankhya/models/__init__.py` | `SANKHYA_SPECIFIC_LEGITIMATE` | Configuração e staging provider-specific |
| `services/api/integracoes/sankhya/services/external_association_helper.py` | `SANKHYA_SPECIFIC_LEGITIMATE` | Associação provider-specific baseada em entidades Sankhya |
| `apps/web/src/components/integracoes/erp/erp-provider-selector.tsx` | `FRONTEND_GENERIC` | Seleção por catálogo Marketplace |
| `apps/web/src/components/integracoes/erp/erp-provider-registry.ts` | `FRONTEND_PROVIDER_WRAPPER` | Registro frontend de wrappers, hoje só Sankhya |
| `apps/web/src/components/integracoes/sankhya-console.tsx` | `FRONTEND_PROVIDER_WRAPPER` | Wrapper provider-specific legítimo |
| `apps/web/src/components/integracoes/erp-console.tsx` | `GENERIC_NOMINAL` | Console “dinâmico” com vazamentos Sankhya |
| `apps/web/src/components/integracoes/erp/capability-view-model.ts` | `GENERIC_NOMINAL` | Catálogo de capability ainda fixo |
| `apps/web/src/components/integracoes/erp/sync-center-view-model.ts` | `GENERIC_NOMINAL` | Interpretação genérica com hipóteses Sankhya |
| `apps/web/src/components/integracoes/erp/capability-details.tsx` | `GENERIC_NOMINAL` | Usa timeline reexportada de Sankhya |
| `apps/web/src/components/integracoes/erp-timeline.tsx` | `POSSIBLE_DUPLICATION` | Alias direto para timeline Sankhya |
| `apps/web/src/components/integracoes/sankhya-timeline.tsx` | `SANKHYA_SPECIFIC_LEGITIMATE` | Timeline concreta hoje reutilizada como “ERP” |
| `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx` | `BACKOFFICE` + `GENERIC_NOMINAL` | Observabilidade com dependência explícita de Sankhya |
| `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx` | `WIZARD` | Seleção de provider via Marketplace |
| `services/api/tests/unit/integracoes/test_erp_router.py` | `TEST` | Fixa delegação do router ERP para Sankhya |
| `services/api/tests/unit/integracoes/test_erp_readiness_service.py` | `TEST` | Fixa readiness canônico |
| `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py` | `TEST` | Fixa lifecycle canônico dentro do adapter Sankhya |
| `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py` | `TEST` | Guardrails arquiteturais e convivência |

## 6. Mapa de dependências

## 6.1 Backend

Fluxo principal atual:

`ERP router`  
→ `ErpReadinessService` para descobrir contexto  
→ fallback em `SankhyaSyncService.get_config()`  
→ assert explícito de provider `sankhya`  
→ delegação para `SankhyaSyncService` ou router Sankhya

Fluxo canônico de configuração:

`Sankhya router/config`  
→ `SankhyaSyncService.criar_config/atualizar_config`  
→ `SankhyaConfig`  
→ `SankhyaCanonicalAdapter.sync_provider_config()`  
→ `MarketplaceIntegracao` / `TenantIntegracao` / `IntegrationCredential` / `IntegrationFeature` / `IntegrationSyncPolicy` / `IntegrationHealth` / `IntegrationVersion`

## 6.2 Frontend

`ErpConsole`  
→ tenta descobrir provider via `/integracoes/erp/status`  
→ usa `ERP_PROVIDER_CONSOLES`  
→ renderiza `SankhyaConsole`  
→ `SankhyaConsole` injeta endpoints/config no `DynamicErpConsole`  
→ `DynamicErpConsole` ainda conhece campos Sankhya

## 7. Backend

## 7.1 Tabela de endpoints ERP reais

| Endpoint ERP | Implementação real | Service chamado | Provider específico? | Sankhya obrigatório? |
| --- | --- | --- | ---: | ---: |
| `/providers/{slug}/schema` | leitura direta em `MarketplaceIntegracao` | nenhum service provider-specific | não | não |
| `/status` | delegação após `_assert_sankhya_provider` | `SankhyaSyncService.obter_status_detalhado` | sim | sim |
| `/health` | delegação após `_assert_sankhya_provider` | `SankhyaSyncService.obter_health_detalhado` | sim | sim |
| `/jobs` | delegação após `_assert_sankhya_provider` | `SankhyaSyncService.listar_jobs` | sim | sim |
| `/timeline` | delegação ao router Sankhya | `listar_timeline_sankhya_provider` | sim | sim |
| `/diagnostico` | delegação ao router Sankhya | `obter_diagnostico_sankhya_provider` | sim | sim |
| `/associacoes/pendentes` | service genérico com gate Sankhya | `ExternalRecordAssociationService.list_pending_associations` | parcialmente | sim |
| `/associacoes` | service genérico com gate Sankhya | `ExternalRecordAssociationService.list_associations` | parcialmente | sim |
| `/associacoes/resumo` | service genérico com gate Sankhya | `ExternalRecordAssociationService.get_association_summary` | parcialmente | sim |
| `/associacoes/{id}/reconciliar` | service genérico com gate Sankhya | `ExternalRecordAssociationService.reconcile_pending` | parcialmente | sim |

## 7.2 Conclusão

O router ERP só é genericamente funcional para `/providers/{slug}/schema`.

Todo o restante depende explicitamente do Sankhya no runtime atual.

## 8. Router ERP

Arquivo auditado:

- `services/api/integracoes/erp/router.py`

### Respostas objetivas

1. Resolve provider dinamicamente: `parcialmente`
2. Consulta `TenantIntegracao`: `indiretamente`, via `ErpReadinessService`
3. Consulta `MarketplaceIntegracao`: `sim`, no endpoint de schema
4. Usa registry de providers: `não`
5. Instancia serviços provider-specific: `sim`
6. Chama diretamente classes Sankhya: `sim`
7. Possui imports Sankhya: `sim`
8. Possui condicionais por provider: `sim`, via `_assert_sankhya_provider`
9. Possui fallback Sankhya: `sim`, via `SankhyaSyncService.get_config()`
10. Possui schemas Sankhya no contrato público: `sim`
11. Retorna dados construídos exclusivamente a partir de `SankhyaConfig`: `parcialmente`
12. O endpoint continuaria funcionando para outro ERP: `não`, exceto schema do provider

### Classificação por endpoint

- `/providers/{slug}/schema`: `GENERIC_REAL`
- `/status`: `FACHADA_NOMINAL_SOBRE_SANKHYA`
- `/health`: `FACHADA_NOMINAL_SOBRE_SANKHYA`
- `/jobs`: `FACHADA_NOMINAL_SOBRE_SANKHYA`
- `/timeline`: `ACOPLAMENTO_CRITICO`
- `/diagnostico`: `ACOPLAMENTO_CRITICO`
- associações: `GENÉRICO_COM_DELEGAÇÃO_INCOMPLETA`

### Achado principal

O router ERP ainda não é um router multi-provider. Ele é um gateway Sankhya com nome canônico.

## 9. Services

## 9.1 `ErpReadinessService`

Arquivo:

- `services/api/integracoes/erp_readiness_service.py`

### Usa

- `TenantIntegracao`
- `MarketplaceIntegracao`
- `IntegrationHealth`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `ExternalRecordAssociation`

### Provider resolution

Resolve o provider canônico pelo `TenantIntegracao` ativo de tipo `ERP`.

### Problema

O readiness não importa Sankhya, mas contém regra fixa `_ERP_REQUIRED_FEATURE_CODES = ("pessoas", "produtos", "financeiro", "nfe")`.

Conclusão:

- `GENERIC_REAL` na persistência e no runtime base;
- `GENERIC_NOMINAL` na política de capability obrigatória;
- `SECOND_PROVIDER_BLOCKER` se outro ERP tiver matriz de capability diferente.

## 9.2 `ExternalRecordAssociationService`

Arquivo:

- `services/api/integracoes/services/external_record_association_service.py`

Conclusão:

- `GENERIC_REAL`
- não importa Sankhya;
- não conhece `CODPARC`, `CODPROD`, auth, URLs ou endpoints provider-specific;
- é reutilizável sem alteração estrutural.

## 9.3 `SankhyaSyncService`

Arquivo:

- `services/api/integracoes/sankhya/services/sync_service.py`

Conclusão:

- provider-specific legítimo;
- também atua como agregador de runtime ERP atual;
- mistura leitura de `SankhyaConfig` e leitura canônica;
- concentra a lógica efetiva de status, health, jobs, timeline e diagnóstico.

## 10. SankhyaCanonicalAdapter

Arquivo:

- `services/api/integracoes/sankhya/services/canonical_adapter.py`

### Respostas objetivas

1. Apenas traduz o provider: `não`
2. Também implementa lifecycle genérico: `sim`
3. Responsabilidades que deveriam estar no core ERP:
   - ensure de `MarketplaceIntegracao`
   - ensure de `TenantIntegracao`
   - ensure de `IntegrationCredential`
   - ensure de `IntegrationFeature`
   - ensure de `IntegrationSyncPolicy`
   - ensure de `IntegrationHealth`
   - ensure de `IntegrationVersion`
4. Responsabilidades que devem permanecer no adapter:
   - schema Sankhya
   - defaults Sankhya
   - auth models Sankhya
   - payloads Sankhya
   - mapeamento operacional Sankhya
5. Outro adapter repetiria estruturas genéricas: `sim`
6. Existe código reutilizável preso no Sankhya: `sim`
7. Há risco de duplicação ao adicionar outro ERP: `alto`

### Conclusão

`SankhyaCanonicalAdapter` é o principal ponto onde o core ainda vaza para dentro do provider.

Classificação:

- `CORE_TO_PROVIDER_LEAK`
- `SECOND_PROVIDER_BLOCKER`

## 11. Provider resolution

Estado atual:

- registry backend formal: `não`
- factory backend formal: `não`
- protocolo/interface em runtime: `não`
- mapa fixo: `não formalizado`
- `if/elif`: `na prática sim`, por `provider_slug != "sankhya"`
- provider desconhecido tratado: `sim`, com `501`
- provider inativo tratado: `sim` no schema route e via Marketplace/Readiness
- provider sem adapter tratado: `indiretamente`, como não suportado
- provider sem wrapper tratado no frontend: `sim`, botão indisponível

Conclusão:

Criar um segundo ERP hoje exige modificar o router ERP.

## 12. Provider contract

Contrato formal encontrado:

- schema público em `services/api/integracoes/schemas.py`
- modelos canônicos em `services/api/integracoes/models.py`
- definição de provider via `MarketplaceIntegracao.provider_definition`, `feature_schema`, `sync_schema`, `health_schema`

Contrato faltante:

- interface/ABC/protocol runtime para adapter/service provider ERP
- registry backend para resolução do provider
- contrato explícito de capabilities, status, health, jobs, timeline e diagnóstico

### Respostas

1. Existe contrato formal de provider: `parcial`
2. É usado em runtime: `parcial`
3. É apenas documentação: `não`, mas incompleto
4. O Sankhya implementa o contrato: `parcialmente`
5. O router depende desse contrato: `não`
6. O Console depende dele: `parcialmente`
7. Um segundo ERP saberia exatamente o que implementar: `não`
8. Métodos obrigatórios: `implícitos`
9. Retornos padronizados: `parciais`
10. Responsabilidades implícitas: `muitas`

## 13. Lifecycle de TenantIntegracao

Fluxo mapeado:

`SankhyaConsole`  
→ endpoints Sankhya de configuração  
→ `SankhyaSyncService.criar_config/atualizar_config`  
→ `SankhyaCanonicalAdapter.sync_provider_config()`  
→ criação/reativação de `TenantIntegracao` e demais estruturas canônicas

### Respostas

- camada que cria: adapter Sankhya
- camada que consulta: readiness, sync service, router ERP
- camada que reativa: adapter Sankhya
- camada que define scope: adapter Sankhya/defaults provider
- camada que cria credentials: adapter Sankhya
- camada que cria features: adapter Sankhya
- camada que cria policies: adapter Sankhya
- camada que cria health: adapter Sankhya
- camada que implementa idempotência: `SankhyaSyncService` + adapter
- camada que conhece índices físicos: serviço/adapter ao lidar com colisões e uniqueness

Classificação:

- `CORE_GENERIC_PARTIAL`
- `ACOPLAMENTO_CRITICO`

Conclusão:

O lifecycle de `TenantIntegracao` não deveria estar majoritariamente dentro do adapter Sankhya.

## 14. Models

## 14.1 Models genéricos

Arquivo:

- `services/api/integracoes/models.py`

Status:

- `MarketplaceIntegracao`: `GENERIC_REAL`
- `TenantIntegracao`: `GENERIC_REAL`
- `IntegrationCredential`: `GENERIC_REAL`
- `IntegrationFeature`: `GENERIC_REAL`
- `IntegrationSyncPolicy`: `GENERIC_REAL`
- `IntegrationHealth`: `GENERIC_REAL`
- `IntegrationJob`: `GENERIC_REAL`
- `IntegrationVersion`: `GENERIC_REAL`
- `ExternalRecordAssociation`: `GENERIC_REAL`

## 14.2 Models Sankhya

Arquivo:

- `services/api/integracoes/sankhya/models/__init__.py`

Status:

- `SankhyaConfig`: `SANKHYA_SPECIFIC_LEGITIMATE`, mas também `DUPLICATE_DATA`
- `SankhyaSyncLog`: `SANKHYA_SPECIFIC_LEGITIMATE`
- staging Sankhya: `SANKHYA_SPECIFIC_LEGITIMATE`

## 14.3 Fonte de verdade por dado

| Dado | Fonte oficial | Legado paralelo | Consumidores |
| --- | --- | --- | --- |
| Provider selecionado | `TenantIntegracao` + `MarketplaceIntegracao` | `SankhyaConfig` implicitamente | readiness, status, frontend |
| URLs | `IntegrationCredential.connection_payload` e `TenantIntegracao` derivado | `SankhyaConfig` | console, testes, status |
| Auth model | payload canônico | `SankhyaConfig` | console, save/update Sankhya |
| Credenciais | `IntegrationCredential` | `SankhyaConfig` | adapter, console |
| Features | `IntegrationFeature` | defaults embutidos no adapter | readiness, status, UI |
| Policies | `IntegrationSyncPolicy` | defaults embutidos no adapter | readiness, sync center |
| Health | `IntegrationHealth` | `SankhyaConfig.teste_status/ultimo_teste` | status, health, timeline |
| Jobs | `IntegrationJob` | `SankhyaSyncLog` | jobs, timeline, diagnóstico |
| Logs | `SankhyaSyncLog` | n/a | backoffice, timeline, diagnóstico |
| Associations | `ExternalRecordAssociation` | helpers Sankhya e staging como insumo | association center, helpers |

## 15. SankhyaConfig versus TenantIntegracao

### Respostas

1. Campos em ambos: provider, URLs, auth model, estado de configuração, ativação, intervalos e material de credenciais sob formas diferentes
2. Fonte real no save: `SankhyaConfig`, seguida de sincronização canônica
3. Fonte no reload: ambas; console lê `SankhyaConfig` enriquecido por canônico
4. Fonte no teste de conexão: `SankhyaConfig`
5. Fonte no sync: híbrida
6. Fonte no status: híbrida
7. Fonte no readiness: canônica
8. Fonte no health: canônica quando existe, legado em fallback
9. O adapter copia dados entre estruturas: `sim`
10. Existe risco de divergência: `sim`
11. Outro ERP precisaria de tabela equivalente a `SankhyaConfig`: `hoje provavelmente sim ou precisaria adaptar o fluxo`
12. A tabela Sankhya é configuração provider-specific legítima ou fonte paralela indevida: `ambos`

### Conclusão

`SankhyaConfig` é legítima como configuração provider-specific, mas hoje também funciona como fonte paralela de runtime, especialmente em bootstrap, save e fallback de status/health.

## 16. Credentials

Achado:

- o domínio canônico já tem `IntegrationCredential`;
- o fluxo operacional ainda preserva credenciais relevantes em `SankhyaConfig`;
- o console frontend ainda consome flags `sankhya_client_secret_configured`, `sankhya_x_token_configured`, `sankhya_token_configured`, `sankhya_appkey_configured`.

Conclusão:

- `DUPLICATE_DATA`
- necessário convergir sem big bang

## 17. Features

Achados:

- `IntegrationFeature` é a estrutura oficial;
- defaults de capability continuam codificados dentro do `SankhyaCanonicalAdapter`;
- readiness e frontend usam listas fixas de capability ERP.

Conclusão:

- estrutura genérica real;
- catálogo operacional ainda ancorado no Sankhya atual.

## 18. Policies

Achados:

- `IntegrationSyncPolicy` é genérico;
- políticas default nascem no adapter Sankhya;
- `Sync Center` interpreta modos genéricos, mas com descrição de casos ancorados em capabilities atuais.

Conclusão:

- persistência genérica real;
- bootstrap e semântica ainda centralizados no provider Sankhya atual.

## 19. Health

Achados:

- `IntegrationHealth` é genérico;
- `SankhyaSyncService.obter_health_detalhado()` usa `IntegrationHealth` quando existe;
- fallback usa `SankhyaConfig` quando não existe health canônico.

Conclusão:

- `GENERIC_REAL` no modelo;
- `SANKHYA_AS_SOURCE_OF_TRUTH` no fallback operacional.

## 20. Jobs

Achados:

- `IntegrationJob` é genérico;
- `SankhyaSyncService.listar_jobs()` lê jobs canônicos apenas para `TenantIntegracao` do slug `sankhya`;
- logs enriquecidos dependem de correlação com `SankhyaSyncLog`.

Conclusão:

- `IntegrationJob` é genérico;
- a surface `/jobs` ainda é provider-bound.

## 21. Timeline

Achados:

- backend ERP usa response model `SankhyaTimelineItemResponse`;
- `apps/web/src/components/integracoes/erp-timeline.tsx` é apenas reexport de `sankhya-timeline`;
- `capability-details.tsx` usa a timeline “ERP” que na prática é a Sankhya.

Conclusão:

- `POSSIBLE_DUPLICATION`
- `PROVIDER_TO_CORE_LEAK`

## 22. Associations

Achados:

- `ExternalRecordAssociation` e service são agnósticos;
- helpers Sankhya alimentam as associações com chaves e mapeamentos Sankhya (`CODPARC`, `CODPROD`, etc.);
- router ERP ainda bloqueia tudo para provider `sankhya`.

Conclusão:

- núcleo de associação: `GENERIC_REAL`
- orquestração HTTP atual: `GENERIC_NOMINAL`

## 23. Readiness

Achados:

- não importa Sankhya;
- consulta modelos canônicos;
- resolve provider ativo por `TenantIntegracao`;
- usa capability matrix do provider, mas exige conjunto fixo de features mínimas.

Conclusão:

- readiness é o componente mais próximo do core real;
- ainda precisará revisão antes do segundo provider.

Classificação:

- `NON_BLOCKING` para piloto Sankhya;
- `SECOND_PROVIDER_BLOCKER` para multiprovider pleno.

## 24. Configuration

Achados:

- existe endpoint genérico `/integracoes/erp/providers/{slug}/schema`;
- o save efetivo continua provider-specific via endpoints Sankhya;
- `DynamicErpConsole` conhece campos Sankhya diretamente.

Conclusão:

O schema provider-specific está correto como conceito, mas o console e o contrato de config ainda não são realmente agnósticos.

## 25. Auth

Achados:

- auth models são definidos e normalizados no fluxo Sankhya;
- o core ERP não possui contrato formal de autenticação provider-specific;
- o frontend conhece descrições de `gateway_oauth_client_credentials`, `gateway_legacy_login`, `legacy_ws_basic_auth`.

Conclusão:

- autenticação deveria ser exclusivamente provider-owned;
- hoje ainda vaza para o console genérico.

## 26. Sync

Achados:

- ações manuais e sync completo residem nos endpoints Sankhya;
- `Sync Center` lê jobs genéricos, mas as operações reais ainda são as do Sankhya;
- `feature_code` e triggers nascem do fluxo Sankhya atual.

### Respostas

1. Sync Center mostra contratos reais ou interpreta jobs Sankhya: `interpreta jobs canônicos ainda originados do Sankhya`
2. `IntegrationJob` é realmente genérico: `sim`
3. Quem cria os jobs: `runtime Sankhya/adapter/service`
4. Quem define `feature_code`: `defaults e fluxos Sankhya`
5. Quem define trigger: `policies e rotinas Sankhya`
6. Jobs Sankhya possuem campos próprios: `sim, via correlação com log legado`
7. O core ERP conhece nomes de sync Sankhya: `indiretamente`
8. Outro provider conseguiria criar jobs iguais: `sim no modelo, não no runtime atual sem ajustes`
9. A ação sync completo é tratada como provider-specific: `sim`
10. O frontend genérico conhece ações Sankhya: `parcialmente`

## 27. Capabilities

Origem observada:

- `IntegrationFeature`
- `feature_schema.capability_matrix`
- catálogo fixo frontend
- defaults do adapter Sankhya

Classificação:

| Capability | Classificação |
| --- | --- |
| `pessoas` | `capability do domínio ERP`, hoje implementada pelo Sankhya |
| `produtos` | `capability do domínio ERP`, hoje implementada pelo Sankhya |
| `financeiro` | `capability do domínio ERP`, hoje implementada pelo Sankhya |
| `nfe` | `capability do domínio ERP`, hoje implementada pelo Sankhya |
| `pedidos` | `capability declarada para futuro` no frontend/core atual |
| `estoque` | `capability declarada para futuro` no frontend/core atual |

Achado crítico:

`apps/web/src/components/integracoes/erp/capability-view-model.ts` constrói fallback visual a partir de um catálogo fixo, mesmo se o provider não declarar todas as capabilities.

## 28. Frontend

## 28.1 Fluxo oficial

`ErpConsole`  
→ selector por Marketplace  
→ registry de wrappers  
→ `SankhyaConsole`  
→ `DynamicErpConsole`

### Respostas

- registry suporta novos wrappers sem alterar o Console: `parcialmente`
- wrapper contém toda lógica provider-specific: `não`
- Dynamic Console conhece Sankhya: `sim`
- tipos genéricos possuem campos Sankhya: `sim`
- callbacks são realmente injetados: `sim`
- endpoints são fornecidos: `sim`
- existe fallback Sankhya: `sim`
- provider desconhecido é seguro: `sim`
- provider sem wrapper é seguro: `sim`, com indisponibilidade controlada

## 29. DynamicErpConsole

Arquivo:

- `apps/web/src/components/integracoes/erp-console.tsx`

Ocorrências críticas encontradas:

- comentário explícito de compatibilidade com “Integração Sankhya”
- `providerSlug = "sankhya"`
- campos `config?.sankhya_*`
- label fallback `"Sankhya"`
- auth labels Sankhya/gateway legado

### Respostas

- existem imports Sankhya: `indiretos`, via registry/wrapper
- existem campos Sankhya: `sim`
- existem textos Sankhya: `sim`
- existem fallbacks Sankhya: `sim`
- existem rotas Sankhya: `sim`, via wrapper
- existem assumptions de capabilities: `sim`
- existem assumptions de auth: `sim`
- existe lógica provider-specific escondida: `sim`

Conclusão:

`DynamicErpConsole` é `GENERIC_NOMINAL`.

## 30. SankhyaConsole

Arquivo:

- `apps/web/src/components/integracoes/sankhya-console.tsx`

Conclusão:

- injeta endpoints e callbacks;
- é relativamente fino;
- o problema não está no wrapper em si, mas no fato de o “core dinâmico” ainda conhecer Sankhya.

## 31. Capability Center

Achados:

- usa view models derivados de `capability-view-model.ts`;
- aceita capability matrix do backend;
- porém possui ordenação e fallback fixos.

Conclusão:

- provider-agnostic parcial;
- não plenamente agnóstico para catálogo desconhecido.

## 32. Capability Details

Achados:

- depende de `erp-timeline.tsx`, que reexporta `sankhya-timeline`;
- correlação principal por `feature_code` é genérica;
- labels e semântica ainda seguem o catálogo atual.

Conclusão:

- `GENERIC_NOMINAL`

## 33. Association Center

Achados:

- consome apenas endpoints ERP;
- não assume `CODPARC` ou `CODPROD` no componente;
- depende de payload canônico de associação.

Conclusão:

- frontend de associação é o componente mais agnóstico;
- o bloqueio está no backend/router, não no rendering.

Classificação:

- `GENERIC_REAL` no frontend
- `GENERIC_NOMINAL` na superfície backend atual

## 34. Sync Center

Achados:

- mostra jobs e políticas canônicas;
- ainda embute descrições fixas e pressupostos das capabilities atuais.

Conclusão:

- `GENERIC_NOMINAL`

## 35. Backoffice

Arquivo:

- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`

Achados:

- usa endpoints ERP para status/health/jobs/timeline/diagnóstico;
- usa endpoint Sankhya direto para logs: `/integracoes/sankhya/logs?limit=5`
- texto explícito: “ERP atual: Sankhya, como provider conectado nesta fase.”

Conclusão:

- não é fonte principal de configuração;
- não substitui o console do tenant;
- ainda tem observabilidade acoplada ao provider atual.

## 36. Wizard

Arquivo:

- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`

Achados:

- consulta `"/integracoes/marketplace/erps?ativa=true"`
- persiste `marketplace_integracao_id`, `marketplace_integracao_slug`, `erp_nome`
- não cria configuração técnica do provider

Conclusão:

- `Wizard` não conhece Sankhya estruturalmente;
- é um dos componentes mais preparados para multiprovider.

## 37. Marketplace

Achados:

- `MarketplaceIntegracao` e `/marketplace/erps` formam catálogo real;
- fornecem slug, tipo, schemas, metadata e definição suficiente para selector/schema route;
- não resolvem adapter backend nem wrapper frontend sozinhos.

Conclusão:

- Marketplace é catálogo real;
- ainda não é o registry de runtime.

## 38. Rotas legadas

Rotas paralelas observadas:

- `/integracoes/erp/*`
- `/integracoes/sankhya/*`

Decisão:

- manter por compatibilidade no piloto;
- não expandir o padrão paralelo;
- consolidar gradualmente em fases futuras.

## 39. Duplicações

| Duplicação | Motivo atual | Fonte oficial | Risco | Decisão |
| --- | --- | --- | --- | --- |
| rotas ERP x Sankhya | transição de superfície | indefinida por endpoint | médio | consolidar depois |
| status ERP x status Sankhya/legacy | bootstrap compatível | canônico com fallback legado | médio | manter temporariamente |
| health ERP x health legado | compatibilidade | `IntegrationHealth` | médio | manter temporariamente |
| timeline ERP x timeline Sankhya | ausência de contrato genérico | indefinida | alto | consolidar |
| config canônica x `SankhyaConfig` | migração parcial | híbrida | alto | convergir |
| credenciais genéricas x campos legados | compatibilidade | híbrida | alto | convergir |
| jobs genéricos x sync logs | observabilidade/histórico | híbrida | médio | manter com plano |
| Association Center x helpers Sankhya | provider feeding genérico | `ExternalRecordAssociation` | baixo | manter |
| Console tenant x Backoffice | governança separada | console do tenant | baixo | manter |
| schema genérico x schema Sankhya | provider contract parcial | provider schema do Marketplace | baixo | manter |
| readiness genérico x readiness implícito Sankhya | transição | `ErpReadinessService` | médio | revisar |

## 40. Acoplamentos legítimos

Legítimos e aceitáveis:

- autenticação Sankhya;
- payloads Sankhya;
- endpoints Sankhya;
- staging Sankhya;
- mapeamento de entidades Sankhya;
- logs técnicos Sankhya;
- schemas provider-specific do Sankhya;
- helper de associação Sankhya.

## 41. Acoplamentos indevidos

Indevidos no core ou na fachada genérica:

- `erp/router.py` importando schemas e routers Sankhya;
- `erp/router.py` suportando apenas Sankhya;
- fallback do router ERP para `SankhyaConfig`;
- lifecycle canônico preso no `SankhyaCanonicalAdapter`;
- `DynamicErpConsole` contendo `sankhya_*`;
- timeline ERP sendo alias da timeline Sankhya;
- readiness impondo capability set fixo do piloto atual.

## 42. Sankhya como default

Sankhya ainda é provider padrão implícito em:

- `apps/web/src/components/integracoes/erp-console.tsx`: `providerSlug = "sankhya"`
- fallback visual de labels no console
- `erp/router.py`: única implementação suportada
- `erp-provider-registry.ts`: único wrapper registrado

Classificação:

- `SANKHYA_AS_DEFAULT`

## 43. Sankhya como fonte de verdade

Sankhya ainda é fonte de verdade operacional em:

- save e reload de configuração via `SankhyaConfig`
- fallback de detecção do provider ativo no router ERP
- fallback de status e health quando canônico não existe
- timeline e diagnóstico ERP
- logs operacionais do backoffice

Classificação:

- `SANKHYA_AS_SOURCE_OF_TRUTH`

## 44. Exercício de segundo ERP (`erp_exemplo`)

Provider fictício:

- `provider_slug = "erp_exemplo"`
- API key
- capabilities: `pessoas`, `produtos`, `contas_a_pagar`
- sem NFe
- endpoints próprios
- jobs próprios
- associações via `ExternalRecordAssociation`

### Arquivos que precisariam ser alterados hoje

#### Esperado provider-specific

- novo package `services/api/integracoes/<provider>/...`
- novo wrapper frontend `apps/web/src/components/integracoes/<provider>-console.tsx`
- registro no `MarketplaceIntegracao`

#### Registro legítimo

- `apps/web/src/components/integracoes/erp/erp-provider-registry.ts`

#### Alteração indevida no core

- `services/api/integracoes/erp/router.py`
- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/erp/types.ts`
- `apps/web/src/components/integracoes/erp/capability-view-model.ts`
- `apps/web/src/components/integracoes/erp/sync-center-view-model.ts`
- `apps/web/src/components/integracoes/erp-timeline.tsx`

#### Bloqueador arquitetural

- `services/api/integracoes/sankhya/services/canonical_adapter.py` precisaria deixar de ser o lugar onde nasce o lifecycle genérico
- `services/api/integracoes/erp_readiness_service.py` precisaria deixar de impor `nfe` e `financeiro` como requisito universal

#### Duplicação inevitável se nada for corrigido

- novo adapter copiando lifecycle canônico inteiro hoje contido no Sankhya
- novo fluxo equivalente a `SankhyaConfig`

#### Ausência de contrato

- falta contrato backend de status/health/jobs/timeline/diagnóstico/configuração provider ERP

## 45. Teste conceitual sem Sankhya

Se toda a pasta Sankhya fosse removida, análise estática:

1. backend inicia: `não`
2. router ERP importa: `não`
3. status funciona: `não`
4. Marketplace funciona: `sim`
5. Tenant sem integração acessa o Console: `parcialmente`, mas o console dinâmico tem default Sankhya
6. provider selector funciona: `sim`
7. Association Center funciona: `frontend sim, backend ERP não`
8. Capability Center funciona: `frontend parcialmente`
9. Sync Center funciona: `frontend parcialmente, backend não`
10. readiness funciona: `sim`
11. health funciona: `não`
12. migrations funcionam: `não auditado por execução`, mas modelos Sankhya fazem parte do runtime atual
13. testes genéricos passam: `não`

## 46. Matriz de genericidade

| Componente | Nome genérico | Implementação genérica | Depende do Sankhya | Segundo ERP exige alteração |
| --- | ---: | ---: | ---: | ---: |
| Router ERP | sim | não | sim | sim |
| ErpReadinessService | sim | parcial | não direto | sim |
| DynamicErpConsole | sim | não | sim | sim |
| Capability Center | sim | parcial | indireto | sim |
| Capability Details | sim | parcial | sim | sim |
| Association Center | sim | sim no frontend / parcial no backend | indireto | sim no backend |
| Sync Center | sim | parcial | indireto | sim |
| Status | sim | não | sim | sim |
| Health | sim | parcial | sim | sim |
| Jobs | sim | parcial | sim | sim |
| Timeline | sim | não | sim | sim |
| Diagnóstico | sim | não | sim | sim |
| TenantIntegracao lifecycle | sim | não | sim | sim |

## 47. Achados classificados

| ID | Achado | Classificação | Prioridade |
| --- | --- | --- | --- |
| A01 | Router ERP suporta apenas Sankhya | `SECOND_PROVIDER_BLOCKER` | `P0` |
| A02 | Router ERP importa schemas/routers Sankhya | `PROVIDER_TO_CORE_LEAK` | `P0` |
| A03 | Fallback do provider ativo consulta `SankhyaConfig` | `SANKHYA_AS_DEFAULT` | `P1` |
| A04 | Lifecycle canônico reside no `SankhyaCanonicalAdapter` | `CORE_TO_PROVIDER_LEAK` | `P0` |
| A05 | `SankhyaConfig` continua fonte paralela de configuração/runtime | `DUPLICATE_DATA` | `P1` |
| A06 | `DynamicErpConsole` conhece `sankhya_*` | `PROVIDER_TO_CORE_LEAK` | `P1` |
| A07 | `erp-timeline.tsx` reexporta timeline Sankhya | `DUPLICATE_RUNTIME` | `P1` |
| A08 | Readiness impõe capabilities fixas | `SECOND_PROVIDER_BLOCKER` | `P1` |
| A09 | Association service é verdadeiramente genérico | `GENERIC_REAL` | `P3` |
| A10 | Marketplace ERP é catálogo real | `GENERIC_REAL` | `P3` |
| A11 | Wizard ERP é provider-agnostic na seleção | `GENERIC_REAL` | `P3` |
| A12 | Backoffice ainda chama `/integracoes/sankhya/logs` | `LEGACY_TOLERATED` | `P2` |

## 48. Riscos

- duplicação silenciosa entre canônico e legado;
- regressão ao introduzir segundo ERP sem contrato runtime;
- repetição de lifecycle genérico dentro de adapters provider-specific;
- falsa sensação de multiprovider por nomenclatura “ERP” e “Dynamic”;
- acoplamento crescente se novos recursos forem adicionados diretamente no fluxo Sankhya atual.

## 49. Impacto no piloto Sankhya

Classificação:

- `não bloqueia`
- `exige monitoramento`
- `exige correção antes de ampliar volume multi-provider`

Justificativa:

O piloto atual está coerente porque a aplicação inteira opera assumindo Sankhya. O risco é arquitetural de expansão, não de colapso imediato do piloto já escolhido.

## 50. Impacto em segundo ERP

Classificação:

- `bloqueia`

Justificativa:

Adicionar outro ERP hoje exigiria alterar core nominalmente genérico, replicar lifecycle canônico em novo adapter ou criar nova fachada paralela, o que esta auditoria considera proibido.

## 51. Decisões recomendadas

1. Manter o piloto Sankhya.
2. Não iniciar implementação produtiva de segundo ERP antes de core repair.
3. Preservar modelos canônicos existentes.
4. Preservar `MarketplaceIntegracao` como catálogo oficial.
5. Preservar `ExternalRecordAssociationService` como núcleo agnóstico.
6. Revisar primeiro resolução de provider e lifecycle canônico.
7. Não expandir o router ERP com novos `if provider == ...`.
8. Não copiar o padrão `SankhyaCanonicalAdapter` para novos providers.

## 52. Plano incremental

### ERP-CORE-REPAIR-01A — Contrato formal de provider

- definir contrato runtime para:
  - status
  - health
  - jobs
  - timeline
  - diagnóstico
  - config save/load/test
- criar registry backend explícito
- sem mover implementação ainda

### ERP-CORE-REPAIR-01B — Resolução real de provider

- reescrever `services/api/integracoes/erp/router.py` para resolver provider por registry
- remover imports diretos Sankhya do router ERP
- manter compatibilidade externa dos endpoints

### ERP-CORE-REPAIR-01C — Lifecycle genérico de TenantIntegracao

- mover ensure/create/update reusável para core ERP
- deixar no adapter apenas tradução provider-specific
- preservar idempotência e comportamento atual

### ERP-CORE-REPAIR-01D — Convergência de configuração

- definir fronteira entre `SankhyaConfig` e `IntegrationCredential`/`TenantIntegracao`
- reduzir `SankhyaConfig` ao que for estritamente provider-specific
- manter fallback temporário

### ERP-CORE-REPAIR-01E — Consolidação frontend

- retirar `sankhya_*` de `DynamicErpConsole`
- fazer `types.ts` refletir schema provider-specific genérico
- manter wrappers provider-specific

### ERP-CORE-REPAIR-01F — Timeline e observabilidade

- criar contrato genérico de timeline/diagnóstico
- eliminar alias `erp-timeline -> sankhya-timeline`
- manter logs técnicos provider-specific separados

### ERP-CORE-REPAIR-01G — Teste arquitetural de segundo provider

- provar em branch técnica que `erp_exemplo` só exige:
  - adapter
  - wrapper
  - registro
  - schema
- sem mudança adicional em core

## 53. Arquivos prováveis em futura correção

Core prioritário:

- `services/api/integracoes/erp/router.py`
- `services/api/integracoes/erp_readiness_service.py`
- `services/api/integracoes/schemas.py`
- novo módulo de contract/registry ERP

Frontend prioritário:

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/erp/types.ts`
- `apps/web/src/components/integracoes/erp/erp-provider-registry.ts`
- `apps/web/src/components/integracoes/erp/capability-view-model.ts`
- `apps/web/src/components/integracoes/erp/sync-center-view-model.ts`
- `apps/web/src/components/integracoes/erp-timeline.tsx`

Provider Sankhya a ser adaptado com compatibilidade:

- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`

## 54. Testes de caracterização necessários

Testes localizados:

- `services/api/tests/unit/integracoes/test_erp_router.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_erp_association_validation.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_governance_router.py`
- `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py`
- `apps/web/tests/unit/integracoes/erp-capability-center.test.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-details.test.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details-view-model.test.ts`
- `apps/web/tests/e2e/wizard-erp-selection.spec.ts`

Lacunas principais:

- contrato backend de provider resolution multiprovider;
- ausência de testes que provem que o router ERP não importa provider específico;
- ausência de testes que provem console realmente schema-driven e sem `sankhya_*`;
- ausência de testes de segundo provider dummy sem alteração de core;
- ausência de testes de convergência entre `SankhyaConfig` e `IntegrationCredential`.

## 55. Guardrails de correção

Correção futura deve respeitar:

- sem big bang;
- sem trocar runtime inteiro de uma vez;
- sem criar nova fachada paralela ERP2;
- sem copiar lifecycle canônico para novo provider;
- sem remover `SankhyaConfig` abruptamente;
- sem quebrar o piloto Sankhya;
- sem quebrar o console atual durante a transição;
- sem alterar Wizard;
- sem alterar IAM;
- sem ativar novos módulos/capabilities fora do escopo;
- com testes de caracterização antes de cada extração.

## 56. Veredicto

### Respostas obrigatórias

1. A arquitetura ERP é realmente multi-provider: `não`
2. O Sankhya ainda é o provider padrão implícito: `sim`
3. Onde o Sankhya é fonte de verdade: `configuração, fallback de provider, status/health fallback, timeline, diagnóstico e logs`
4. Onde o Sankhya apenas implementa contrato legítimo: `auth, payloads, staging, logs técnicos, helpers e schemas provider-specific`
5. O router ERP é genérico: `não`
6. O readiness é genérico: `parcialmente`
7. O lifecycle de TenantIntegracao pertence ao core: `sim`
8. O schema provider-specific está correto: `sim como conceito, não como uso final no console`
9. O Console é realmente dinâmico: `não`
10. O Capability Center é provider-agnostic: `parcialmente`
11. O Association Center é provider-agnostic: `parcialmente, com núcleo forte`
12. O Sync Center é provider-agnostic: `parcialmente`
13. O status e health são provider-agnostic: `não`
14. Quais duplicações são perigosas: `config, credenciais, timeline, router ERP e lifecycle no adapter`
15. Quais legados podem permanecer: `SankhyaConfig`, `SankhyaSyncLog`, staging e rotas provider-specific durante transição controlada`
16. Quais mudanças seriam necessárias para um segundo ERP: `contrato runtime, registry, desacoplamento do router, extração do lifecycle, limpeza do console`
17. Quais arquivos do core precisariam ser alterados: `router ERP, readiness, console dinâmico, types e view models centrais`
18. Qual correção deve ser feita primeiro: `contrato formal + registry + router ERP`
19. É seguro iniciar o piloto Sankhya antes da correção: `sim, com ressalvas`
20. É seguro iniciar um segundo ERP antes da correção: `não`

### Veredicto final

`GO COM RESSALVAS`

para o piloto Sankhya.

`NO-GO MULTIPROVIDER`

para introdução de segundo ERP sem `ERP-CORE-REPAIR-01A` e `ERP-CORE-REPAIR-01B` pelo menos.

