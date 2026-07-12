# ERP-UX-03 - Auditoria do Console Operacional de Integracoes ERP

Data da execucao: 2026-07-12

## 1. Resumo executivo

O runtime ERP atual suporta a evolucao do Console Operacional sem redesenho arquitetural. A base canonica ja existe, a superficie HTTP ERP ja foi consolidada e o provider Sankhya ja expoe os dados operacionais principais.

O problema atual nao e de arquitetura critica. O gap esta em experiencia operacional, composicao visual e separacao clara entre:

- Console do Tenant
- Backoffice tecnico
- paginas legadas de compatibilidade

Veredicto preliminar:

- `GO COM RESSALVAS`

Motivo:

- os dados e contratos principais ja existem;
- faltam composicoes de UX para centralizar capability center, association center e sync center;
- ainda ha duplicacao de console e de rotas legadas;
- nao existe endpoint canonico para lista completa de associacoes nem tela unica de detalhes por capability;
- reprocessamento formal ainda nao existe como contrato dedicado.

## 2. Escopo auditado

Auditoria documental do console ERP atual, sem alterar runtime, schemas, migrations, adapters, rotas ou IAM.

Incluido nesta analise:

- Console do Tenant
- Backoffice tecnico
- rotas ERP canonicas
- rotas Sankhya legadas
- services de readiness, sync, adapter e association
- schemas de status, health, jobs, timeline, diagnostico e associacoes
- testes unitarios e de integracao existentes

## 3. Arquitetura encontrada

### 3.1 Camada de frontend

- A pagina oficial do Tenant e `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`.
- Ela renderiza `ErpConsole`, que hoje e um alias de `SankhyaConsole`.
- `SankhyaConsole` injeta endpoints provider-specific no `DynamicErpConsole`.
- Existe tambem uma pagina legada em `apps/web/src/app/integracoes/sankhya/page.tsx` que apenas redireciona para o console oficial.
- O backoffice tem sua propria pagina em `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`, focada em suporte e observabilidade.

### 3.2 Camada de backend

- O router canonico ERP esta em `services/api/integracoes/erp/router.py`.
- O router Sankhya legado continua em `services/api/integracoes/sankhya/routers/__init__.py`.
- Ambos sao registrados em `services/api/main.py` sob `/api/v1/integracoes`.
- O `ErpReadinessService` consolida configuracao, health, features, policies e conflitos.
- O `SankhyaCanonicalAdapter` materializa provider, credenciais, features, policies, jobs e health.
- `ExternalRecordAssociationService` e o contrato oficial de de-para.

### 3.3 Decisao estrutural confirmada

- O ERP administrativo pertence ao ERP.
- O estoque operacional continua com AgroSaaS.
- O estoque administrativo esta reservado ao ERP.
- O escopo de integracao continua sendo `TENANT` ou `ESTABELECIMENTO`.
- `UNIDADE_PRODUTIVA` nao e escopo valido.

## 4. Inventario de arquivos

### Frontend

- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/app/integracoes/page.tsx`
- `apps/web/src/app/integracoes/sankhya/page.tsx`
- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/erp-timeline.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/components/auth/onboarding-guard.tsx`

### Backend

- `services/api/main.py`
- `services/api/integracoes/erp/router.py`
- `services/api/integracoes/erp_readiness_service.py`
- `services/api/integracoes/models.py`
- `services/api/integracoes/services/external_record_association_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/external_association_helper.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/models/__init__.py`

### Testes relevantes

- `services/api/tests/unit/integracoes/test_erp_router.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_governance_router.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## 5. Inventario de paginas e componentes

### Pagina oficial do Tenant

- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx#L5-L18`
- Usa `ErpConsole` como componente operacional oficial.

### Console operacional

- `apps/web/src/components/integracoes/erp-console.tsx#L403-L1465`
- Carrega:
  - schema do provider
  - diagnosico
  - config
  - status
  - health
  - jobs
  - logs
  - timeline
  - associacoes pendentes

### Wrapper Sankhya

- `apps/web/src/components/integracoes/sankhya-console.tsx#L5-L20`
- Define endpoints provider-specific e exporta `ErpConsole`.

### Timeline

- `apps/web/src/components/integracoes/erp-timeline.tsx#L1-L4`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx#L1-L152`

### Backoffice tecnico

- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx#L116-L419`

### Navegacao e guardrails

- `apps/web/src/components/layout/app-sidebar.tsx#L302-L313`
- `apps/web/src/components/auth/onboarding-guard.tsx#L15-L27`

## 6. Inventario de APIs

### Superficie canonica ERP

- `GET /api/v1/integracoes/erp/providers/{provider_slug}/schema`
- `GET /api/v1/integracoes/erp/status`
- `GET /api/v1/integracoes/erp/health`
- `GET /api/v1/integracoes/erp/jobs`
- `GET /api/v1/integracoes/erp/timeline`
- `GET /api/v1/integracoes/erp/diagnostico`
- `GET /api/v1/integracoes/erp/associacoes/pendentes`
- `POST /api/v1/integracoes/erp/associacoes/{association_id}/reconciliar`

### Superficie Sankhya legada

- `POST /api/v1/integracoes/sankhya/config`
- `GET /api/v1/integracoes/sankhya/config`
- `POST /api/v1/integracoes/sankhya/config/testar-conexao`
- `GET /api/v1/integracoes/sankhya/status`
- `GET /api/v1/integracoes/sankhya/health`
- `POST /api/v1/integracoes/sankhya/sync/pessoas`
- `POST /api/v1/integracoes/sankhya/sync/produtos`
- `POST /api/v1/integracoes/sankhya/sync/completo`
- `GET /api/v1/integracoes/sankhya/logs`
- `GET /api/v1/integracoes/sankhya/jobs`
- `GET /api/v1/integracoes/sankhya/timeline`
- `GET /api/v1/integracoes/sankhya/diagnostico`
- `GET /api/v1/integracoes/sankhya/pessoas`
- `GET /api/v1/integracoes/sankhya/produtos`
- `GET /api/v1/integracoes/sankhya/nfe`
- `POST /api/v1/integracoes/sankhya/nfe/exportar`
- `POST /api/v1/integracoes/sankhya/nfe/importar-entrada`
- `GET /api/v1/integracoes/sankhya/financeiro`
- `POST /api/v1/integracoes/sankhya/financeiro/exportar-contas-pagar`
- `POST /api/v1/integracoes/sankhya/financeiro/exportar-contas-receber`
- `POST /api/v1/integracoes/sankhya/financeiro/importar`
- `GET /api/v1/integracoes/sankhya/associacoes/pendentes`
- `POST /api/v1/integracoes/sankhya/associacoes/{association_id}/reconciliar`

### Registro no app

- `services/api/main.py#L517-L520`

## 7. Inventario de services e contratos

### Services canonicos

- `ErpReadinessService`
- `ExternalRecordAssociationService`
- `SankhyaCanonicalAdapter`
- `SankhyaSyncService`
- `SankhyaNFeService`
- `SankhyaFinanceiroService`
- `SankhyaExternalAssociationHelper`

### Modelos canonicos

- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationCredential`
- `IntegrationVersion`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationJob`
- `IntegrationHealth`
- `ExternalRecordAssociation`
- `ExternalRecordAssociationHistory`

### Contratos de schema

- `ProviderSchemaResponse`
- `SankhyaConfigResponse`
- `SankhyaSyncStatusResponse`
- `SankhyaHealthResponse`
- `SankhyaIntegrationJobResponse`
- `SankhyaTimelineItemResponse`
- `SankhyaOperationalDiagnosisResponse`
- `ExternalRecordAssociationPendingItemResponse`
- `ExternalRecordAssociationGovernanceReconcileRequest`

## 8. Inventario de capabilities existentes

### Capabilities oficialmente materializadas no adapter

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`  - declarado, P2, nao materializado no piloto
- `estoque`  - declarado, P2, nao materializado e proibido neste episodio

### Matriz capability x provider x direcao x master x maturidade

| Capability | Provider | Direcao | Master | Maturidade | Status operacional |
| --- | --- | --- | --- | --- | --- |
| `pessoas` | Sankhya | `ERP_TO_AGROSAAS` | ERP | `TESTED` | Implementada |
| `produtos` | Sankhya | `ERP_TO_AGROSAAS` | ERP | `TESTED` | Implementada |
| `financeiro` | Sankhya | `ERP_TO_AGROSAAS` | ERP administrativo | `TESTED` | Parcial |
| `nfe` | Sankhya | `EVIDENCE_RETURN` | ERP fiscal | `TESTED` | Parcial |
| `pedidos` | Sankhya | `BIDIRECTIONAL_CONTROLLED` | Controlado | `DECLARED` | P2 |
| `estoque` | Sankhya | `BIDIRECTIONAL_CONTROLLED` | ERP administrativo | `DECLARED` | P2 proibido aqui |

### Leitura do que o negocio pediu

- Pessoas existe como capability unica, nao como subcapabilities separadas de cliente e fornecedor.
- Produtos existe.
- Fornecedores e clientes nao estao materializados como capabilities separadas no contrato atual.
- Financeiro existe.
- NFe existe.
- Estoque administrativo existe apenas como declaracao P2.
- Comercializacao nao esta exposta como capability operacional oficial neste runtime.

## 9. Matriz informacao x fonte x API x frontend x lacuna

| Informacao | Fonte/modelo atual | API atual | Frontend atual | Lacuna |
| --- | --- | --- | --- | --- |
| Status da capability | `IntegrationFeature` + `provider.feature_schema.capability_matrix` | `GET /integracoes/erp/status` | tabela de funcoes em `DynamicErpConsole` | `UX_ONLY` |
| Direcao | `provider.feature_schema.capability_matrix.direction` | `GET /integracoes/erp/status` | tabela de funcoes | `UX_ONLY` |
| Sistema master | `provider_definition`, `readiness`, `IntegrationSyncPolicy` | `GET /integracoes/erp/status`, `GET /integracoes/erp/diagnostico` | cards e tabela, sem nocao de master explicita por capability | `UX_ONLY` |
| Provider | `MarketplaceIntegracao`, `provider_definition` | `GET /integracoes/erp/providers/{slug}/schema`, `GET /integracoes/erp/status` | card "ERP conectado" | `UX_ONLY` |
| Adapter | `SankhyaCanonicalAdapter` | indireto via `/status`, `/health`, `/jobs`, `/timeline` | nao exposto no console | `BACKEND_EXPOSURE` |
| Ultimo job | `IntegrationJob` | `GET /integracoes/erp/jobs` | card "Atualizacoes registradas" | `UX_ONLY` |
| Ultima sincronizacao | `TenantIntegracao.ultimo_sync`, `IntegrationHealth.last_success_at` | `GET /integracoes/erp/status`, `GET /integracoes/erp/health` | card "Regras" e status | `UX_ONLY` |
| Health | `IntegrationHealth` | `GET /integracoes/erp/health` | card "Situacao" | `UX_ONLY` |
| Pendencias | `ExternalRecordAssociation` status `PENDING`/`CONFLICT` + readiness | `GET /integracoes/erp/status`, `GET /integracoes/erp/associacoes/pendentes` | lista de associacoes pendentes | `UX_ONLY` |
| Associacoes | `ExternalRecordAssociation` + history | `GET /integracoes/erp/associacoes/pendentes`, `POST /reconciliar` | lista pendente + edicao basica | `API_COMPOSITION` |
| Politica de sync | `IntegrationSyncPolicy` | `GET /integracoes/erp/status` | card de regras | `UX_ONLY` |
| Proxima execucao | derivada de `ultimo_sync + sync_interval` | `GET /integracoes/erp/status` | nao apresentada como agenda clara no console | `UX_ONLY` |
| Reprocessamento | manual sync endpoints e jobs | `POST /integracoes/sankhya/sync/*` | botoes de sync do console | `NOT_IMPLEMENTED` |

## 10. Mapa do fluxo atual do Console ERP

### Tenant Console

1. Usuario entra em `/dashboard/settings/integracoes/erp`.
2. A pagina renderiza `ErpConsole`.
3. `ErpConsole` aponta para `SankhyaConsole`.
4. `SankhyaConsole` injeta os endpoints Sankhya no `DynamicErpConsole`.
5. `DynamicErpConsole` carrega schema, status, health, jobs, logs, timeline, diagnostico e pendencias.
6. O usuario consegue salvar configuracao, testar conexao, sincronizar pessoas, produtos e carga completa.
7. O usuario consegue reconciliar vinculos pendentes.

### O que esta bom

- o console centraliza o ciclo de configuracao e observacao;
- nao expoe segredo em texto puro;
- usa permissao de integracoes;
- evita criar runtime paralelo.

### O que ainda falta

- detalhes por capability em painel dedicado;
- fonte unica para system master, adapter e endpoint interno;
- comandos de reprocessamento formais;
- visao de conflito e pendencia mais clara;
- lista de associacoes alem das pendentes.

## 11. Mapa do fluxo atual de associacoes

1. A rota canonica `GET /integracoes/erp/associacoes/pendentes` chama `ExternalRecordAssociationService.list_pending_associations`.
2. O backend enriquece a resposta com `feature_code` e `history`.
3. O console lista apenas pendencias.
4. O usuario preenche entidade local, id local e motivo.
5. O frontend chama `POST /integracoes/erp/associacoes/{id}/reconciliar`.
6. O backend valida tenant, status `PENDING` e duplicidade.
7. O service marca `ACTIVE` e grava history `RECONCILED`.

### Limitacoes observadas

- nao existe endpoint oficial para listar todas as associacoes com filtros amplos no console do tenant;
- conflitos aparecem como contagem na readiness, nao como centro operacional dedicado;
- edicao/correcao depende do contrato de `reconcile_pending` e nao de um editor operacional completo.

## 12. Mapa do fluxo atual de jobs e sincronizacao

1. O console le `GET /integracoes/erp/jobs` e `GET /integracoes/erp/timeline`.
2. O backend canonico delega para o provider Sankhya.
3. O provider Sankhya retorna jobs do `IntegrationJob` e logs legados enriquecidos.
4. O status agrega `ultimo_sync`, `proximo_sync`, `health_status`, `features_habilitadas` e `policies_resumidas`.
5. O console mostra botoes manuais de sync.
6. O `sync/completo` ainda e um atalho operacional, nao um motor novo.

### O que existe de fato

- sincronizacao manual
- sincronizacao por tipo
- diagnostico
- jobs
- health
- timeline

### O que existe como contrato, mas nao como experiencia unica

- `proximo_sync`
- `trigger_expression`
- `IntegrationSyncPolicy`
- `IntegrationJobTrigger`

### O que nao existe nesta etapa

- reprocessamento formal
- fila/progressao dedicada de estoque administrativo
- pipeline novo de outbox para este console

## 13. Duplicacoes encontradas

### 13.1 Console do tenant x console Sankhya

- Implementacao que deve permanecer: `apps/web/src/components/integracoes/erp-console.tsx`
- Reutilizacao: `apps/web/src/components/integracoes/sankhya-console.tsx`
- Redirecionamento: `apps/web/src/app/integracoes/sankhya/page.tsx`
- Descontinuidade gradual: nenhuma neste episodio
- Tipo de duplicacao: nominal e funcional
- Risco: baixo
- Impacto no piloto: baixo

### 13.2 Console do tenant x backoffice tecnico

- Implementacao que deve permanecer: console do tenant
- Reutilizacao: backoffice apenas para leitura e diagnostico
- Redirecionamento: backoffice deve continuar apontando para o tenant quando a acao for operacional do cliente
- Descontinuidade gradual: qualquer acao de configuracao duplicada no backoffice
- Tipo de duplicacao: funcional parcial
- Risco: medio
- Impacto no piloto: medio

### 13.3 Timeline genérica x timeline Sankhya

- Implementacao que deve permanecer: `ErpTimeline`
- Reutilizacao: `SankhyaTimeline`
- Redirecionamento: aliases mantidos
- Descontinuidade gradual: nenhuma agora
- Tipo de duplicacao: nominal
- Risco: baixo
- Impacto no piloto: baixo

### 13.4 Rotas ERP canonicas x rotas Sankhya legadas

- Implementacao que deve permanecer: rotas canonicas ERP para status/health/jobs/timeline/diagnostico/associacoes
- Reutilizacao: rotas Sankhya para configuracao, sync e logs legados
- Redirecionamento: pagina legada Sankhya para console oficial
- Descontinuidade gradual: duplicacao de leitura em backoffice e paginas auxiliares
- Tipo de duplicacao: funcional e de compatibilidade
- Risco: medio
- Impacto no piloto: medio

### 13.5 Hub de integracoes x console operacional

- Implementacao que deve permanecer: hub como catalogo
- Reutilizacao: card do ERP apontando para o console oficial
- Redirecionamento: catalogo nao deve virar console
- Descontinuidade gradual: rotas que fazem parecer que existe um segundo console operacional
- Tipo de duplicacao: nominal
- Risco: baixo
- Impacto no piloto: baixo

## 14. Lacunas de UX

### `UX_ONLY`

- falta um Capability Center com cards por capability mostrando status, direcao, master, provider, adapter, ultima execucao, health, pendencias e acoes
- falta um Association Center com visao operacional completa do de-para
- falta um Sync Center que diferencie manual, automatico, evento, outbox, desabilitado e proxima execucao
- falta uma tela de detalhes por capability
- falta timeline com leitura mais clara por contexto operacional
- falta separar visualmente acao de suporte e acao do tenant

### `FRONTEND_CONTRACT`

- o `DynamicErpConsole` consome tipos Sankhya diretamente e ainda carrega fallback provider-specific
- nao existem hooks dedicados para capability center e association center
- a composicao do front ainda e feita por fetchs diretos dentro do componente

### `DUPLICATION`

- console oficial e wrapper Sankhya convivem como aliases
- backoffice e tenant compartilham leituras parecidas
- timeline tem wrapper duplo

## 15. Lacunas de contrato

### `API_COMPOSITION`

- nao existe endpoint canonico unico para associacoes completas e conflitos
- nao existe endpoint canonico unico para detalhes de capability por card
- nao existe composicao oficial para reprocessamento

### `BACKEND_EXPOSURE`

- adapter nao aparece como entidade operacional no console, apenas como efeito indireto
- endpoint interno por capability nao e exposto de forma legivel ao tenant

### `NOT_IMPLEMENTED`

- reprocessamento formal
- lista completa de associacoes com edicao ampla
- tela de detalhamento por capability
- capability separada para comercializacao

### `P2_FORBIDDEN`

- estoque administrativo via evento/outbox
- qualquer ativacao de estoque P2 neste episodio

## 16. Riscos de seguranca

### `SECURITY_RISK`

- nao foi encontrado vazamento intencional de segredo em texto puro no console oficial
- o schema e a resposta de config usam mascaramento
- o backoffice mostra apenas leituras consolidadas
- risco residual existe se alguem expuser URL externa ou payload tecnico bruto em telas futuras

### Controles observados

- `require_tenant_permission("integrations:view")`
- `require_tenant_permission("integrations:configure")`
- `require_tenant_permission("integrations:test")`
- `require_tenant_permission("integrations:sync")`
- `ExternalRecordAssociation` valida tenant e status antes de reconciliar
- `onboarding-guard` permite o console do ERP no fluxo de implantacao

### Pontos de atencao

- nao criar nova exposicao de credencial em tela
- nao transformar o backoffice em espelho de configuracao do tenant
- sanitizar qualquer endpoint externo exibido futuramente

## 17. Separacao Tenant Console x Backoffice

### Tenant Console

- fonte oficial de configuracao
- fonte oficial de teste de conexao
- fonte oficial de acao operacional do cliente
- foco em usabilidade

### Backoffice

- observacao tecnica
- suporte
- diagnostico
- leitura de health, jobs, timeline e status
- nao deve substituir o console do tenant

### Evidencia

- a pagina de backoffice possui CTA para abrir o console do tenant e reforca que configuracao fica na administracao do tenant.

## 18. Itens proibidos ou P2 identificados

### `P2_FORBIDDEN`

- sincronizacao de estoque administrativo
- ativacao de fluxo de estoque por evento/outbox

### `ARCHITECTURE_VIOLATION`

- criar novo runtime
- criar novo adapter generico
- criar nova fachada
- criar novo mecanismo de de-para
- alterar Wizard
- alterar IAM

### `NOT_IMPLEMENTED`

- reprocessamento formal
- center de associacoes completo
- center de capability com detalhes por card

## 19. Plano incremental recomendado

### Fase 1 - Contrato visual e inventario

- consolidar os dados que ja existem
- definir view model do Capability Center
- definir fontes oficiais por campo
- manter runtime atual

### Fase 2 - Capability Center

- apresentar as capabilities existentes
- destacar estado, direcao, master, provider, adapter e health
- reutilizar dados ja expostos por status e readiness

### Fase 3 - Capability Details

- detalhar health, jobs, timeline e pendencias por capability
- expor endpoints internos ja existentes em formato legivel
- sanitizar tudo o que for externo

### Fase 4 - Association Center

- operar sobre `ExternalRecordAssociation`
- listar, filtrar, reconciliar e visualizar conflitos
- sem novo mecanismo de de-para

### Fase 5 - Sync Center

- organizar manual, automatico, evento, outbox e desabilitado
- expor proxima execucao quando aplicavel
- nao ativar estoque P2

### Fase 6 - Consolidacao

- remover duplicacoes de UX quando seguro
- manter backoffice tecnico
- redirecionar paginas legadas com seguranca

## 20. Arquivos que provavelmente serao alterados em cada fase

### Fase 1

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/erp-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`

### Fase 2

- `apps/web/src/components/integracoes/erp-console.tsx`
- possivel novo componente de capability center
- possivel novo hook ou client HTTP do dominio integracoes

### Fase 3

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- possivel novo endpoint de composicao no router canonico ERP

### Fase 4

- `apps/web/src/components/integracoes/erp-console.tsx`
- `services/api/integracoes/erp/router.py`
- `services/api/integracoes/services/external_record_association_service.py`

### Fase 5

- `services/api/integracoes/erp/router.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`

## 21. Testes existentes reutilizaveis

- `services/api/tests/unit/integracoes/test_erp_router.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_governance_router.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## 22. Testes que deverao ser criados nas fases seguintes

- teste de composicao do Capability Center
- teste de detalhes por capability
- teste de Association Center completo
- teste de reprocessamento formal quando existir contrato
- teste de separacao tenant x backoffice para a nova UX
- teste de redirecionamento de paginas legadas

## 23. Riscos de regressao

- confundir console do tenant com backoffice tecnico
- duplicar regras de status entre `erp/router.py` e `sankhya/routers/__init__.py`
- acoplar o front novamente a rotas provider-specific
- expor payload tecnico bruto em tela de tenant
- criar uma lista concorrente de associacoes fora de `ExternalRecordAssociation`
- permitir que a futura UX encoste em estoque P2

## 24. Impacto esperado sobre o piloto

### Baixo impacto tecnico

- nenhum novo runtime
- nenhum novo adapter
- nenhuma nova tabela
- nenhuma mudanca de IAM

### Alto impacto de usabilidade

- leitura unica do console
- menos ida e volta entre backoffice e tenant
- menos ambiguidade sobre capability, health e associacoes

### Impacto operacional

- melhor entendimento do que esta ativo
- melhor reconhecimento de pendencias
- melhor condução de reconciliacao manual

## 25. Veredicto final

`GO COM RESSALVAS`

### Justificativa

- o runtime existente suporta a evolucao;
- a arquitetura canonica ja esta consolidada;
- o Console do Tenant ja centraliza configuracao, status, health, jobs, timeline e pendencias;
- as lacunas sao principalmente de UX, composicao de API e consolidacao de navegação;
- nao ha bloqueio arquitetural que obrigue novo runtime;
- reprocessamento formal e estoque P2 continuam fora desta fase.

## 26. Resposta objetiva solicitada

- Arquivo criado: `docs/implementation/reports/ERP-UX-03-AUDITORIA-CONSOLE-OPERACIONAL-ERP.md`
- Veredicto: `GO COM RESSALVAS`
- Principais componentes reutilizaveis: `DynamicErpConsole`, `SankhyaConsole`, `ErpReadinessService`, `SankhyaCanonicalAdapter`, `SankhyaSyncService`, `ExternalRecordAssociationService`, `IntegrationJob`, `IntegrationHealth`, `IntegrationFeature`, `IntegrationSyncPolicy`
- Principais duplicacoes: console tenant x Sankhya alias, tenant x backoffice tecnico, timeline alias, rotas canonicas x legadas
- Principais lacunas: capability center, association center, sync center, detalhes por capability, reprocessamento formal
- Primeira fase recomendada: contrato visual e inventario
- Confirmacao: nenhum codigo produtivo foi alterado, apenas este relatorio foi criado
- `git diff --check`: sera reportado apos a validacao final do workspace

