# ERP-FACADE-01 - Auditoria Arquitetural da Camada de Fachada ERP

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: auditoria arquitetural, sem implementacao

## Resumo executivo

Conclusao: **GO, com restricoes claras**.

Existe acoplamento direto entre consumidores do dominio ERP e o provider Sankhya. Esse acoplamento ocorre principalmente no frontend do console ERP do tenant, na tela de observabilidade de backoffice e em alguns pontos transversais do backend que ainda importam servicos Sankhya fora da borda ideal do adapter.

Ao mesmo tempo, a auditoria confirma que o runtime oficial de integracoes ERP ja esta consolidado e cobre configuracao, credenciais, feature flags, politicas de sincronizacao, jobs, health, associacoes externas e readiness. Portanto, uma futura Fachada ERP **nao precisa recriar infraestrutura, modelos, contratos ou runtime**. Ela so e tecnicamente justificavel se for uma camada fina de orquestracao e composicao para consumidores, reaproveitando integralmente a arquitetura oficial existente.

Risco principal: transformar a Fachada ERP em uma segunda arquitetura, duplicando contratos, readiness, health, jobs, configuracao ou observabilidade ja existentes.

Recomendacao tecnica: **GO somente para uma camada fina de consumo ERP-generic**, mantendo:

- o adapter Sankhya como provider-specific;
- o runtime oficial como fonte unica de verdade;
- as rotas Sankhya como compatibilidade enquanto os consumidores migram.

## Situacao atual

O codigo-fonte ja contem o dominio ERP consolidado no runtime oficial de integracoes:

- catalogo de providers e definicoes em `MarketplaceIntegracao`;
- configuracao por tenant em `TenantIntegracao`;
- credenciais segregadas em `IntegrationCredential`;
- capacidades em `IntegrationFeature`;
- politicas de sincronizacao em `IntegrationSyncPolicy`;
- observabilidade em `IntegrationHealth` e `IntegrationJob`;
- reconciliacao em `ExternalRecordAssociation`;
- prontidao funcional em `ErpReadinessService`.

O provider Sankhya tambem ja possui adapter canonico e servicos tecnicos especificos. O problema encontrado nao e ausencia de arquitetura ERP, e sim permanencia de componentes consumidores que ainda operam em modo provider-first.

## Inventario dos componentes reutilizados

### Runtime oficial reutilizavel integralmente

Fonte principal: [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py), [services/api/integracoes/erp_readiness_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp_readiness_service.py)

- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationCredential`
- `IntegrationVersion`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`
- `ExternalRecordAssociation`

### Servicos oficiais reutilizaveis

Fonte principal: [services/api/integracoes/erp_readiness_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp_readiness_service.py), [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py)

- `ErpReadinessService`
- `ErpChecklistRuntime`
- uso do readiness pelo Wizard via `ChecklistEngine.erp_readiness_service`

### Contratos e metadata oficiais reutilizaveis

Fonte principal: [docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md), [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.connection_schema`
- `MarketplaceIntegracao.credential_schema`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`

### Provider atual ja adaptado ao runtime oficial

Fonte principal: [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)

- `SankhyaCanonicalAdapter`
- publicacao de eventos oficiais de integracao
- materializacao de provider, credencial, config, features, policies, health e version
- preenchimento de `provider_definition`, `feature_schema`, `sync_schema`, `health_schema`

### Evidencia adicional de extensibilidade real

Fonte principal: [services/api/integracoes/openweather/services.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/services.py)

O provider `OpenWeather` reutiliza o mesmo runtime canonico (`MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth`, `IntegrationJob`). Isso demonstra que o padrao de extensao por provider ja existe e que uma futura Fachada ERP nao precisa inventar novo runtime para suportar outros providers.

### Provider Resolver

Nao foi identificado um `Provider Resolver` ERP dedicado no codigo auditado. A ausencia dele **nao bloqueia** a conclusao desta auditoria, porque os contratos e metadata de provider ja estao embutidos no runtime oficial e no adapter canonico.

## Mapeamento completo dos acoplamentos

### 1. Console ERP do tenant acoplado diretamente ao provider Sankhya

Fonte: [apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)

Evidencia:

- rota conceitualmente generica `Integracoes ERP`;
- import direto de `SankhyaConsole`;
- renderizacao direta de `<SankhyaConsole />`.

Diagnostico:

- consumidor ERP generico conhece explicitamente o provider atual;
- o ponto de entrada do console ERP ainda esta preso ao primeiro adapter.

### 2. Backoffice ERP acoplado a tipos, componente e endpoints Sankhya

Fonte: [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

Evidencias:

- import direto de `SankhyaTimeline`;
- tipos locais `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaLog`, `SankhyaDiagnosis`;
- chamadas diretas para:
  - `/integracoes/sankhya/status`
  - `/integracoes/sankhya/health`
  - `/integracoes/sankhya/jobs`
  - `/integracoes/sankhya/logs`
  - `/integracoes/sankhya/timeline`
  - `/integracoes/sankhya/diagnostico`
- texto funcional: `ERP atual: Sankhya.`

Diagnostico:

- a tela de observabilidade ERP conhece o provider, os endpoints e os contratos de resposta do provider atual;
- esse e o exemplo mais forte de acoplamento consumidor-provider.

### 3. Componente de console ERP reaproveita o runtime canonico, mas exposto sob superficie Sankhya

Fonte: [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)

Evidencias:

- tipos `SankhyaConfig`, `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaDiagnosis`;
- import de `SankhyaTimeline`;
- consumo de dados canonicamente ERP:
  - `provider_definition`
  - `feature_schema`
  - `sync_schema`
  - `health_schema`
  - `readiness`
  - `policies_resumidas`
- superficie de API ainda provider-first.

Diagnostico:

- a logica de console ERP ja conversa com o runtime oficial;
- o acoplamento restante esta no nome da superficie, nos tipos e no contrato HTTP legado/provider-first;
- isso reforca que a futura Fachada ERP pode ser fina e reaproveitar o runtime existente.

### 4. Timeline operacional genericamente util ainda nomeada como Sankhya

Fonte: [apps/web/src/components/integracoes/sankhya-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-timeline.tsx)

Evidencias:

- componente `SankhyaTimeline`;
- tipo `SankhyaTimelineItem`;
- filtros e renderizacao genericos para eventos operacionais, health e jobs.

Diagnostico:

- responsabilidade funcional e generica de observabilidade ERP;
- nomenclatura e superficie ainda provider-specific.

### 5. Configuracao global do backend ainda conhece Sankhya fora da borda ideal do provider

Fonte: [services/api/core/config.py](/opt/lampp/htdocs/farm/services/api/core/config.py)

Evidencias:

- `sankhya_environment`
- `sankhya_api_base_url`
- `sankhya_auth_url`
- `sankhya_client_id`
- `sankhya_client_secret`
- `sankhya_x_token`

Diagnostico:

- configuracao provider-specific vazando para um modulo central de configuracao;
- esse acoplamento e tecnico e transversal, nao de regra de negocio ERP.

### 6. Roteador de configuracoes gerais importa servico Sankhya diretamente

Fonte: [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)

Evidencia:

- import direto de `SankhyaSyncService` em um roteador de configuracoes centrais.

Diagnostico:

- modulo transversal ainda conhece servico especifico do provider;
- isso amplia o raio de acoplamento fora da fronteira esperada de `integracoes/sankhya/*`.

### 7. Wizard ja consome readiness ERP, nao o provider diretamente

Fonte: [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py)

Evidencias:

- import de `ErpReadinessService`;
- composicao em `self.erp_readiness_service = ErpReadinessService(session)`;
- checklist `CHECK_INTEGRACAO_ERP` no mesmo motor.

Diagnostico:

- o Wizard ja esta no lado correto da fronteira conceitual;
- isso reduz o escopo da futura Fachada ERP: ela nao precisa substituir o readiness oficial.

## Fluxo atual

```text
Console ERP do tenant / Backoffice ERP
  -> componentes SankhyaConsole e SankhyaTimeline
  -> endpoints /integracoes/sankhya/*
  -> SankhyaSyncService
  -> SankhyaCanonicalAdapter
  -> runtime oficial de integracoes
  -> tabelas canonicas e tabelas legadas Sankhya
```

Caracteristica principal:

- os consumidores ERP ainda entram pelo provider;
- o provider ja reencaminha parte relevante do fluxo para o runtime canonico.

## Fluxo proposto

```text
Console ERP do tenant / Backoffice ERP / modulos futuros
  -> superficie ERP generica de consumo
  -> runtime oficial de integracoes
  -> resolucao do provider ativo
  -> adapter especifico do provider
  -> APIs e particularidades do provider
```

Regras obrigatorias para esse fluxo:

- sem novos modelos canonicos;
- sem duplicar readiness, jobs, health ou policies;
- sem substituir adapters;
- mantendo rotas Sankhya existentes como compatibilidade durante transicao.

## Responsabilidades do dominio ERP

Devem permanecer no dominio ERP generico:

- catalogo e definicao de provider;
- configuracao de integracao por tenant;
- armazenamento de credenciais;
- declaracao de capacidades;
- politicas de sincronizacao;
- health consolidado;
- jobs e historico operacional;
- associacoes externas e reconciliacao;
- readiness ERP;
- fluxo oficial do console ERP;
- observabilidade consumida por backoffice.

## Responsabilidades dos providers

Devem permanecer exclusivas do provider Sankhya:

- autenticacao Sankhya;
- Gateway Sankhya;
- OAuth e login legado;
- `SankhyaCanonicalAdapter`;
- staging e sincronizacao tecnica;
- transformacao de payload;
- tratamento de erros especificos;
- compatibilidade com tabelas e respostas legadas Sankhya;
- particularidades da API Sankhya.

Fonte principal: [services/api/integracoes/sankhya/services/auth_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/auth_service.py), [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py), [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)

## Beneficios de uma futura Fachada ERP

- elimina conhecimento direto de Sankhya dos consumidores ERP;
- reduz impacto para adicionar SAP, TOTVS, Omie, Senior e outros providers;
- preserva o runtime oficial e evita reimplementacao;
- cria uma fronteira explicita entre consumo ERP generico e adapters provider-specific;
- padroniza a superficie dos modulos tenant, backoffice e fluxos futuros.

## Riscos

### Risco 1. Criar segunda arquitetura

Se a futura Fachada ERP recriar:

- contratos de provider;
- readiness;
- health;
- jobs;
- policies;
- mapeamentos;
- configuracao;

entao ela passara a competir com a arquitetura oficial ja aprovada.

### Risco 2. Genericidade falsa

Se a camada apenas renomear Sankhya para ERP sem mudar a fronteira de consumo, o sistema continuara provider-first com outro nome.

### Risco 3. Duplicidade funcional

Ja existe duplicidade parcial na superficie de consumo:

- console ERP generico renderizando `SankhyaConsole`;
- observabilidade ERP consumindo endpoints Sankhya;
- contratos ERP canonicos encapsulados em tipos `Sankhya*`.

### Risco 4. Migracao prematura de responsabilidades tecnicas

Mover autenticacao, gateway, staging ou transformacao de payload para uma camada ERP seria erro arquitetural. Essas responsabilidades continuam no adapter/provider.

## Impacto sobre a arquitetura existente

Se feita corretamente, a Fachada ERP:

- preserva integralmente o runtime oficial;
- reduz acoplamento em consumidores;
- nao altera ownership do provider;
- nao substitui `ErpReadinessService`;
- nao exige novos modelos, migrations ou jobs.

Se feita incorretamente, ela:

- compete com a arquitetura atual;
- duplica contratos;
- introduz nova camada de verdade paralela;
- aumenta custo de manutencao.

## Impacto sobre futuras integracoes

Para SAP, TOTVS, Omie, Senior e outros ERPs, a camada faz sentido apenas como fronteira de consumo. O ganho esperado e permitir que:

- Console ERP;
- Wizard;
- Backoffice;
- fluxos oficiais;

permaneçam estaveis enquanto novos adapters implementam:

- autenticacao;
- payloads;
- politicas tecnicas;
- mapeamentos provider-specific;
- particularidades de API.

Essa extensibilidade ja e coerente com o runtime atual e com o padrao visto em `OpenWeather`, onde um provider diferente materializa o mesmo conjunto de ativos canonicos.

## Conclusao

Respostas objetivas aos objetivos da auditoria:

1. Existe acoplamento direto entre consumidores e o provider Sankhya.  
Sim. O acoplamento aparece de forma explicita no console ERP do tenant, no backoffice ERP, em componentes compartilhados e em alguns pontos transversais do backend.

2. Onde esse acoplamento ocorre?  
Principalmente em `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`, `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`, `apps/web/src/components/integracoes/sankhya-console.tsx`, `apps/web/src/components/integracoes/sankhya-timeline.tsx`, `services/api/core/config.py` e `services/api/core/routers/configuration.py`.

3. Quais responsabilidades pertencem ao dominio ERP?  
Config, credenciais, features, sync policies, health, jobs, associacoes externas, readiness e superficie generica de console/observabilidade.

4. Quais responsabilidades pertencem exclusivamente ao provider?  
Auth, gateway, adapter, payload mapping, staging, tratamento de erros e particularidades de API.

5. Uma Fachada ERP eliminaria esse acoplamento?  
Sim, se for uma camada fina de consumo ERP-generico sobre o runtime oficial.

6. Essa Fachada pode reutilizar integralmente o runtime oficial existente?  
Sim. A auditoria encontrou todos os ativos necessarios ja implementados.

7. Existe alguma funcionalidade atualmente duplicada?  
Existe duplicidade parcial de superficie: consumidores ERP usam componentes, tipos e endpoints Sankhya para operar dados que ja sao canonicamente ERP.

8. Ha risco de criar uma segunda arquitetura?  
Sim, e esse e o principal risco desta proposta.

9. Quais componentes seriam consumidores da Fachada?  
Console ERP do tenant, backoffice ERP, possiveis telas de suporte operacional e fluxos de UI que hoje leem status/readiness/health/logs/timeline do provider atual.

10. Quais componentes continuariam exclusivos dos adapters?  
Auth, gateway, sincronizacao tecnica, parser de payload, tradutores, tratamento de erro e particularidades do provider.

## Recomendacao tecnica

**GO**

Condicoes obrigatorias do GO:

- a futura Fachada ERP deve ser somente uma camada de consumo e composicao;
- deve reutilizar `MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth`, `IntegrationJob`, `ExternalRecordAssociation` e `ErpReadinessService`;
- nao deve criar novo runtime, novo contrato canonico ou nova persistencia;
- deve manter o adapter Sankhya isolado como provider-specific;
- deve manter rotas Sankhya existentes como compatibilidade enquanto os consumidores migram.

## Plano tecnico incremental para futura implementacao

### Fase A - Baixo risco

- trocar imports e nomes conceituais provider-first nas camadas consumidoras;
- expor componentes de UI como ERP-generic sem alterar runtime;
- documentar Sankhya como provider atual, nao como arquitetura.

### Fase B - Medio risco

- fazer telas ERP consumirem uma superficie generica baseada no runtime oficial;
- manter endpoints Sankhya como camada de compatibilidade;
- reduzir imports diretos de `Sankhya*` em modulos ERP.

### Fase C - Alto risco

- consolidar contratos HTTP ERP-generic quando houver maturidade;
- remover dependencias provider-first remanescentes nas camadas consumidoras;
- depreciar superficies antigas somente depois de observabilidade e compatibilidade confirmadas.

## Arquivos analisados

- [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py)
- [services/api/integracoes/erp_readiness_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp_readiness_service.py)
- [services/api/integracoes/sankhya/services/canonical_adapter.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [services/api/integracoes/sankhya/schemas/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/schemas/__init__.py)
- [services/api/integracoes/openweather/services.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/services.py)
- [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py)
- [services/api/core/config.py](/opt/lampp/htdocs/farm/services/api/core/config.py)
- [services/api/core/routers/configuration.py](/opt/lampp/htdocs/farm/services/api/core/routers/configuration.py)
- [apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)
- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/components/integracoes/sankhya-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-timeline.tsx)
- [docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md)
- [docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md)

## Comandos executados

```bash
rg -n "sankhya|Sankhya|/integracoes/sankhya|ErpReadinessService|MarketplaceIntegracao|TenantIntegracao|IntegrationCredential|IntegrationFeature|IntegrationSyncPolicy|IntegrationHealth|IntegrationJob|ExternalRecordAssociation|provider_definition|connection_schema|credential_schema|feature_schema|sync_schema|health_schema" services/api apps/web/src docs
sed -n '1,260p' services/api/integracoes/models.py
sed -n '1,260p' services/api/integracoes/erp_readiness_service.py
sed -n '1,220p' services/api/wizard/checklist_engine.py
sed -n '1,260p' services/api/integracoes/sankhya/services/canonical_adapter.py
sed -n '1,220p' services/api/integracoes/sankhya/services/sync_service.py
sed -n '1,260p' services/api/integracoes/sankhya/schemas/__init__.py
sed -n '1,260p' services/api/integracoes/openweather/services.py
sed -n '1,220p' services/api/core/config.py
sed -n '1,220p' services/api/core/routers/configuration.py
sed -n '1,220p' 'apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx'
sed -n '1,300p' 'apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx'
sed -n '1,320p' apps/web/src/components/integracoes/sankhya-console.tsx
sed -n '1,260p' apps/web/src/components/integracoes/sankhya-timeline.tsx
```

## Validacoes realizadas

- auditoria realizada apenas por leitura de codigo e documentacao;
- nenhum endpoint, modelo, migration ou comportamento foi alterado;
- nenhuma nova infraestrutura foi criada;
- validacao final obrigatoria por `git diff --check`.
