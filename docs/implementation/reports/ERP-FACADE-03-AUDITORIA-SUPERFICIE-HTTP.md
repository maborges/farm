# ERP-FACADE-03 - Auditoria da Superficie HTTP ERP-Generic

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: auditoria arquitetural, sem implementacao

## Resumo executivo

Conclusao: **GO, com restricoes fortes**.

E tecnicamente viavel criar uma superficie HTTP canonica para o dominio ERP sem criar novo runtime, novos modelos ou novas regras. A auditoria mostrou que o backend atual ja possui:

- runtime oficial consolidado em `MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth`, `IntegrationJob`, `ExternalRecordAssociation` e `ErpReadinessService`;
- um padrao de routers por provider sob `/api/v1/integracoes/{provider}`;
- respostas provider-first que ja carregam porcoes canonicamente ERP, especialmente em `status`, `health`, `jobs`, `timeline`, `diagnostico`, `config` e `associacoes`.

O principal problema remanescente nao e falta de infraestrutura HTTP. O problema e que o transporte ainda esta organizado por provider, e no caso de Sankhya existe mistura entre:

- compatibilidade legado/provider-specific;
- snapshot canonico do dominio ERP;
- operacao tecnica do provider;
- governanca de associacoes externas.

Portanto, a Fase B e justificavel **somente** como convergencia de consumo HTTP, reaproveitando os servicos existentes e mantendo compatibilidade com `/integracoes/sankhya/*`.

## Inventario dos endpoints usados pela UI ERP

Fonte principal: [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx), [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

### Endpoints atualmente consumidos

| Endpoint | Consumidor atual | Classificacao | Reutilizacao |
|---|---|---|---|
| `/integracoes/sankhya/config` | tenant ERP console | misto: config provider + metadata canonica | parcial |
| `/integracoes/sankhya/config/testar-conexao` | tenant ERP console | provider-specific | nao deve migrar como contrato canonico principal |
| `/integracoes/sankhya/status` | tenant ERP console, backoffice ERP | ERP parcial em contrato Sankhya | alta |
| `/integracoes/sankhya/health` | tenant ERP console, backoffice ERP | ERP parcial em contrato Sankhya | alta |
| `/integracoes/sankhya/jobs` | tenant ERP console, backoffice ERP | majoritariamente canonico | alta |
| `/integracoes/sankhya/logs` | tenant ERP console, backoffice ERP | legado + enriquecimento canonico | media |
| `/integracoes/sankhya/timeline` | tenant ERP console, backoffice ERP | ERP parcial em contrato Sankhya | alta |
| `/integracoes/sankhya/diagnostico` | tenant ERP console, backoffice ERP | composicao ERP/provider | alta |
| `/integracoes/sankhya/associacoes/pendentes` | tenant ERP console | governanca ERP generic com path Sankhya | alta |
| `/integracoes/sankhya/associacoes/{id}/reconciliar` | tenant ERP console | governanca ERP generic com path Sankhya | alta |
| `/integracoes/sankhya/sync/pessoas` | tenant ERP console | provider-specific tecnico | manter provider-specific |
| `/integracoes/sankhya/sync/produtos` | tenant ERP console | provider-specific tecnico | manter provider-specific |

## Analise de reutilizacao

### Endpoints que ja retornam informacao canonicamente ERP

Fonte principal: [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

- `GET /integracoes/sankhya/status`
  - usa `TenantIntegracao`
  - usa `MarketplaceIntegracao`
  - usa `IntegrationHealth`
  - usa `IntegrationFeature`
  - usa `IntegrationSyncPolicy`
  - usa `ErpReadinessService`
  - retorna `provider_definition`, `feature_schema`, `sync_schema`, `health_schema`, `readiness`

- `GET /integracoes/sankhya/health`
  - usa `IntegrationHealth`
  - cai para legado apenas quando o health canonico nao existe

- `GET /integracoes/sankhya/jobs`
  - usa `IntegrationJob`
  - usa `IntegrationFeature`
  - serializa dados essencialmente canonicos

- `GET /integracoes/sankhya/timeline`
  - compoe `jobs` canonicos, `health` canonico/legado e logs enriquecidos
  - e uma superficie de observabilidade potencialmente reaproveitavel

- `GET /integracoes/sankhya/diagnostico`
  - compoe status, health, jobs e logs
  - e um agregador de consumo, nao uma regra exclusiva do provider

- `GET /integracoes/sankhya/associacoes/pendentes`
  - usa `ExternalRecordAssociationService`
  - usa `ExternalRecordAssociation`
  - usa `IntegrationFeature`
  - apesar do path Sankhya, a responsabilidade e genericamente ERP

- `POST /integracoes/sankhya/associacoes/{id}/reconciliar`
  - usa `ExternalRecordAssociationService`
  - regra de reconciliacao e generica

### Endpoints que retornam informacao provider-specific

- `POST /integracoes/sankhya/config/testar-conexao`
  - depende de `SankhyaGatewayAuthService`
  - usa regras de auth, gateway e login legado
  - nao deve se tornar contrato canonico neutro nesta fase

- `POST /integracoes/sankhya/sync/pessoas`
- `POST /integracoes/sankhya/sync/produtos`
- `POST /integracoes/sankhya/sync/completo`
- `POST /integracoes/sankhya/nfe/exportar`
- `POST /integracoes/sankhya/nfe/importar-entrada`
- `POST /integracoes/sankhya/financeiro/exportar-contas-pagar`
- `POST /integracoes/sankhya/financeiro/exportar-contas-receber`
- `POST /integracoes/sankhya/financeiro/importar`

Esses endpoints representam sincronizacao tecnica, transporte, gateway, operacoes de adapter ou capacidades funcionais diretamente materializadas pelo provider atual. Nao devem migrar para uma superficie HTTP ERP-generic na Fase B.

### Endpoints que sao mistos

- `GET /integracoes/sankhya/config`
  - parte provider-specific: campos `sankhya_*`, auth model, masks legadas
  - parte canonica: `provider_definition`, `connection_schema`, `credential_schema`, `feature_schema`, `sync_schema`, `health_schema`
  - forte candidato a futura composicao HTTP, sem reaproveitamento literal do contrato atual

- `GET /integracoes/sankhya/logs`
  - parte legada: `SankhyaSyncLog`
  - parte canonica: enriquecimento com `IntegrationJob`
  - pode permanecer como compatibilidade/diagnostico historico, nao necessariamente como contrato ERP principal

## Mapa da arquitetura HTTP atual

### Router principal em producao

Fonte: [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)

- `app.include_router(sankhya_router, prefix="/api/v1/integracoes")`
- `app.include_router(openweather_router, prefix="/api/v1/integracoes")`

Conclusao:

- o entrypoint HTTP de integracoes ja esta estruturado por provider;
- nao foi encontrada rota HTTP ERP-generic dedicada para o dominio ERP.

### Router Sankhya

Fonte: [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)

Caracteristicas:

- superficie explicitamente provider-first: `APIRouter(prefix="/sankhya")`;
- concentra configuracao, status, health, jobs, logs, timeline, diagnostico, sync, cadastros, fiscal, financeiro e associacoes externas;
- router usa servicos distintos:
  - `SankhyaSyncService`
  - `SankhyaPessoaService`
  - `SankhyaProdutoService`
  - `SankhyaNFeService`
  - `SankhyaFinanceiroService`
  - `ExternalRecordAssociationService`

Conclusao:

- hoje existe sim uma superficie HTTP provider-first;
- varias responsabilidades heterogeneas estao concentradas sob o mesmo router.

### Router OpenWeather

Fonte: [services/api/integracoes/openweather/routers.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/routers.py)

Caracteristicas:

- mesma forma provider-first com `/openweather`;
- tambem expoe `config`, `testar-conexao`, `status`, `health`, `jobs`, `timeline`, `diagnostico`;
- opera sobre runtime canonico via `OpenWeatherService`.

Conclusao:

- ha um padrao de transporte repetido entre providers;
- isso sugere oportunidade real de camada HTTP de composicao para conceitos comuns, sem tocar nos adapters.

## Analise arquitetural

### Existe hoje uma superficie HTTP provider-first?

Sim.

Evidencias:

- paths `/api/v1/integracoes/sankhya/*` e `/api/v1/integracoes/openweather/*`;
- schemas `Sankhya*Response` e `OpenWeather*Response`;
- routers separados por provider.

### Existe uma superficie HTTP ERP-generic parcial?

Sim, mas apenas no conteudo dos payloads, nao no transporte.

Evidencias:

- `status` Sankhya ja devolve `readiness`, `provider_definition`, `feature_schema`, `sync_schema`, `health_schema`, `features_habilitadas` e `policies_resumidas`;
- `health` usa `IntegrationHealth` quando disponivel;
- `jobs` ja serializa `IntegrationJob`;
- `associacoes` ja usam `ExternalRecordAssociationService`, com schemas genericos em [services/api/integracoes/schemas.py](/opt/lampp/htdocs/farm/services/api/integracoes/schemas.py).

### Quais responsabilidades estao misturadas?

No router e no service Sankhya, hoje se misturam:

- configuracao e credenciais do provider;
- contratos canonicos de provider (`provider_definition`, `feature_schema`, etc.);
- readiness ERP;
- observabilidade canonica (`IntegrationHealth`, `IntegrationJob`);
- observabilidade legada (`SankhyaSyncLog`);
- associacoes externas genericas;
- operacoes tecnicas exclusivas do provider;
- cadastros e fluxos funcionais especificos do adapter.

## Avaliacao tecnica obrigatoria

### 1. Existe duplicidade de endpoints?

Sim, em nivel de conceito entre providers.

Exemplos:

- `/integracoes/sankhya/status` e `/integracoes/openweather/status`
- `/integracoes/sankhya/health` e `/integracoes/openweather/health`
- `/integracoes/sankhya/jobs` e `/integracoes/openweather/jobs`
- `/integracoes/sankhya/timeline` e `/integracoes/openweather/timeline`
- `/integracoes/sankhya/diagnostico` e `/integracoes/openweather/diagnostico`

Nao e duplicidade de runtime, mas ha repeticao de superficie HTTP por provider para os mesmos conceitos.

### 2. Existem respostas HTTP diferentes para o mesmo conceito?

Sim.

Exemplos:

- `SankhyaSyncStatusResponse` inclui `readiness`, `provider_definition`, schemas canonicamente ERP e campos legados;
- `OpenWeatherStatusResponse` tambem expoe conceito equivalente, mas com campos diferentes como `latest_weather`;
- `SankhyaConfigResponse` e fortemente provider-specific;
- `OpenWeatherConfigResponse` e muito mais aderente ao runtime canonico.

### 3. Existe logica repetida em controllers?

Sim, parcialmente.

Padroes repetidos:

- dependencia de `tenant_id`;
- permissoes `integrations:view`, `integrations:logs:view`, `integrations:sync`, `integrations:test`;
- roteamento de `config`, `status`, `health`, `jobs`, `timeline`, `diagnostico`;
- translacao quase direta para service methods equivalentes.

### 4. Existe logica repetida em services?

Sim, parcialmente.

Padroes repetidos:

- `obter_status_detalhado`
- `obter_health_detalhado`
- `listar_jobs`
- `listar_timeline_operacional`
- `obter_diagnostico_operacional`

No entanto, isso nao autoriza recriar runtime. A repeticao esta mais na camada de exposicao e composicao do que na base de persistencia.

### 5. Existe oportunidade de criar apenas uma camada HTTP de composicao?

Sim.

A auditoria indica que a melhor direcao para Fase B e:

- manter endpoints provider-specific para operacoes tecnicas;
- criar apenas endpoints ERP de leitura/composicao para a UI;
- fazer essa camada delegar para servicos oficiais ja existentes.

### 6. Essa camada pode reutilizar completamente os ativos oficiais?

Sim.

Pode reutilizar integralmente:

- `ErpReadinessService`
- `MarketplaceIntegracao`
- `IntegrationHealth`
- `IntegrationJob`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `ExternalRecordAssociation`
- adapters existentes

Com uma restricao:

- `config` e `testar-conexao` nao devem ser tratados como contratos completamente neutros sem estrategia de composicao, porque carregam material fortemente provider-specific.

## Endpoints que devem continuar provider-specific

Fonte principal: [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py), [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

- `POST /integracoes/sankhya/config/testar-conexao`
- `POST /integracoes/sankhya/sync/pessoas`
- `POST /integracoes/sankhya/sync/produtos`
- `POST /integracoes/sankhya/sync/completo`
- `POST /integracoes/sankhya/nfe/exportar`
- `POST /integracoes/sankhya/nfe/importar-entrada`
- `POST /integracoes/sankhya/financeiro/exportar-contas-pagar`
- `POST /integracoes/sankhya/financeiro/exportar-contas-receber`
- `POST /integracoes/sankhya/financeiro/importar`
- `GET /integracoes/sankhya/pessoas`
- `GET /integracoes/sankhya/produtos`
- `GET /integracoes/sankhya/nfe`
- `GET /integracoes/sankhya/financeiro`

Motivo:

- autenticacao, gateway, login legado, staging, sync tecnico, payload transformation, fiscal/financeiro do adapter e particularidades da API Sankhya nao pertencem a uma superficie HTTP ERP-generica.

## Analise de extensibilidade

### SAP, TOTVS, Senior e Omie

No desenho atual, a UI precisaria conhecer endpoints especificos se quisesse operar cada provider diretamente:

- `/integracoes/sap/status`
- `/integracoes/totvs/status`
- `/integracoes/senior/status`
- `/integracoes/omie/status`

Isso manteria a camada consumidora dependente de nomes de provider.

Com uma superficie HTTP ERP de composicao, a UI poderia consumir conceitos como:

- status ERP;
- health ERP;
- jobs ERP;
- timeline ERP;
- diagnostico ERP;
- associacoes ERP;

e delegar a resolucao do provider conectado ao backend.

Conclusao:

- para providers futuros, a UI nao deveria conhecer endpoints especificos para leitura operacional comum;
- ela so precisaria conhecer superficie ERP e, quando necessario, acionar operacoes explicitamente provider-specific.

## Beneficios

- reduz acoplamento da UI aos nomes de provider no transporte HTTP;
- reaproveita integralmente o runtime oficial;
- preserva adapters e regras tecnicas onde pertencem;
- facilita onboarding de novos providers sem reescrever telas ERP;
- reduz divergencia entre conceitos equivalentes (`status`, `health`, `jobs`, `timeline`, `diagnostico`).

## Riscos

### Risco 1. Criar segunda arquitetura HTTP

Se a camada ERP reimplementar status, health, jobs ou associacoes em vez de compor os servicos existentes, ela passara a competir com o runtime atual.

### Risco 2. Duplicar contratos desnecessariamente

Se cada endpoint novo tiver schemas ricos demais e independentes dos servicos existentes, o custo de manutencao dobra.

### Risco 3. Misturar leitura generica com operacao tecnica

Se a Fase B tentar canonizar `testar-conexao`, `sync/*`, `nfe/*` e `financeiro/*`, a arquitetura volta a vazar particularidades do provider.

### Risco 4. Romper compatibilidade cedo demais

As telas atuais ainda dependem de `/integracoes/sankhya/*`. A descontinuidade prematura quebraria a UI e o suporte operacional.

## Impacto na arquitetura

Se executada corretamente, a Fase B:

- nao altera models;
- nao altera runtime;
- nao altera adapters;
- nao altera persistencia;
- introduz apenas uma borda HTTP mais coerente para consumidores ERP.

Se executada incorretamente, a Fase B:

- duplica controllers e schemas;
- espalha logica de composicao entre routers novos e antigos;
- aumenta acoplamento em vez de reduzi-lo.

## Conclusao

E possivel criar uma superficie HTTP ERP-generic sem duplicar runtime, modelos ou regras centrais.

A auditoria encontrou base tecnica suficiente porque:

- o backend ja possui runtime oficial consolidado;
- o endpoint `status` Sankhya ja consome readiness, health, features, policies e provider metadata canonicamente ERP;
- `jobs` e `associacoes` ja operam sobre ativos canonicos;
- ha padrao semelhante em outro provider (`OpenWeather`), provando que o problema esta no transporte por provider, nao na falta de runtime.

A recomendacao e **GO** para uma futura implementacao incremental da Fase B, desde que ela seja estritamente uma camada HTTP de composicao sobre os servicos atuais.

## Plano tecnico incremental da Fase B

### Fase B.1 - Convergencia da superficie HTTP

Objetivo:

- introduzir endpoints ERP-generic apenas para leitura/composicao comum.

Escopo conceitual:

- status ERP
- health ERP
- jobs ERP
- timeline ERP
- diagnostico ERP
- associacoes ERP

Riscos:

- sobreposicao semantica com endpoints Sankhya existentes;
- criacao de contratos grandes demais.

Impactos:

- novos consumidores poderao depender da camada ERP;
- endpoints Sankhya permanecem intocados.

Rollback:

- manter a UI consumindo `/integracoes/sankhya/*` enquanto a nova superficie estiver em validacao.

Criterios de conclusao:

- cada endpoint ERP novo deve delegar exclusivamente a servicos oficiais existentes;
- nenhuma regra de negocio nova no router.

### Fase B.2 - Migracao gradual da UI

Objetivo:

- mover `ErpConsole` e `ErpTimeline` para a superficie HTTP ERP.

Riscos:

- divergencia entre payload antigo e novo;
- regressao em textos e estados da tela.

Impactos:

- UI deixa de conhecer `/integracoes/sankhya/*` para leituras comuns;
- o provider atual continua sendo Sankhya apenas como dado.

Rollback:

- feature flag, troca de import de client API ou retorno ao endpoint antigo por tela.

Criterios de conclusao:

- tenant e backoffice consumindo endpoints ERP para leituras comuns;
- comportamento funcional preservado.

### Fase B.3 - Compatibilidade entre endpoints antigos e novos

Objetivo:

- garantir convivio entre rotas ERP-generic e rotas provider-first.

Riscos:

- dupla manutencao temporaria;
- desalinhamento de contratos.

Impactos:

- suporte e operacao continuam funcionando durante a transicao;
- integracoes futuras ja podem nascer no modelo ERP.

Rollback:

- manter endpoints Sankhya como fallback da UI e do suporte.

Criterios de conclusao:

- documentacao clara de quais rotas sao canonicas e quais sao compatibilidade;
- telemetria mostrando uso decrescente das rotas antigas pela UI ERP.

### Fase B.4 - Depreciacao controlada

Objetivo:

- retirar o uso da superficie provider-first apenas onde ela representa leitura ERP comum.

Riscos:

- remocao prematura de rotas ainda usadas por suporte, scripts ou telas residuais;
- perda de informacao legada relevante.

Impactos:

- arquitetura HTTP de consumo fica mais limpa;
- providers futuros exigem menos acoplamento na UI.

Rollback:

- manter rotas antigas publicadas enquanto houver consumidor conhecido;
- rollback por roteamento do client para o endpoint anterior.

Criterios de conclusao:

- nenhuma tela ERP comum dependendo de `/integracoes/sankhya/*` para leitura operacional;
- rotas antigas marcadas como compatibilidade e sem novas features.

## Arquivos analisados

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)
- [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)
- [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [services/api/integracoes/sankhya/schemas/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/schemas/__init__.py)
- [services/api/integracoes/openweather/routers.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/routers.py)
- [services/api/integracoes/openweather/services.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/services.py)
- [services/api/integracoes/openweather/schemas.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/schemas.py)
- [services/api/integracoes/schemas.py](/opt/lampp/htdocs/farm/services/api/integracoes/schemas.py)
- [services/api/integracoes/services/external_record_association_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/services/external_record_association_service.py)
- [docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md)
- [docs/implementation/reports/ERP-FACADE-02-FASE-A-UI-ERP-GENERIC.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-02-FASE-A-UI-ERP-GENERIC.md)

## Comandos executados

```bash
sed -n '1,260p' /home/borgus/.codex/skills/agrosaas-backend/SKILL.md
sed -n '1,260p' docs/architecture/agrosaas-engineering-playbook.md
rg -n "APIRouter|@router\\.|Sankhya.*Response|ErpReadinessService|MarketplaceIntegracao|IntegrationHealth|IntegrationJob|ExternalRecordAssociation" services/api/integracoes/sankhya services/api/integracoes
sed -n '1,320p' services/api/integracoes/sankhya/routers/__init__.py
sed -n '220,520p' services/api/integracoes/sankhya/services/sync_service.py
rg -n "obter_status_detalhado|obter_health_detalhado|listar_jobs|listar_logs|listar_timeline|obter_diagnostico_operacional|obter_config_console|testar_conexao|listar_associacoes_pendentes|reconciliar" services/api/integracoes/sankhya/services/sync_service.py services/api/integracoes/sankhya/routers/__init__.py services/api/integracoes/services services/api/integracoes
sed -n '316,700p' services/api/integracoes/sankhya/routers/__init__.py
sed -n '1180,1425p' services/api/integracoes/sankhya/services/sync_service.py
sed -n '1,240p' services/api/integracoes/schemas.py
sed -n '1,240p' apps/web/src/components/integracoes/sankhya-console.tsx
sed -n '899,1145p' services/api/integracoes/sankhya/services/sync_service.py
sed -n '1,230p' services/api/integracoes/openweather/routers.py
sed -n '1560,1635p' services/api/integracoes/openweather/services.py
rg -n "APIRouter\\(|prefix=.*erp|/erp|ErpReadinessService|TenantIntegracao|MarketplaceIntegracao|IntegrationHealth|IntegrationJob|ExternalRecordAssociation" services/api/integracoes services/api/main.py
sed -n '1,260p' services/api/integracoes/services/__init__.py
sed -n '1,280p' services/api/integracoes/services/external_record_association_service.py
sed -n '1,220p' services/api/main.py
rg -n "sankhya_router|openweather.*router|include_router\\(.*integracoes" services/api/main.py
sed -n '430,530p' services/api/main.py
sed -n '1,220p' services/api/integracoes/openweather/schemas.py
```

## Validacoes realizadas

- auditoria por leitura de codigo e documentacao;
- nenhuma alteracao em endpoints, routers, services, schemas, runtime ou persistencia;
- validacao final obrigatoria por `git diff --check`.
