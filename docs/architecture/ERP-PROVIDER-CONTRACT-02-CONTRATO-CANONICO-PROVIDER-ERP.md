# ERP-PROVIDER-CONTRACT-02 - Contrato Canonico Provider ERP

Status: APROVADA
Categoria: Arquitetura Funcional
Tipo: Regra Arquitetural
Data: 2026-07-09

## 1. Objetivo

Definir o contrato funcional canonico para qualquer provider ERP do AgroSaaS, estabelecendo a estrutura conceitual obrigatoria dos objetos:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`

Este documento e normativo.

Ele nao cria novo runtime.

Ele consolida como os contratos ja existentes do dominio de Integracoes devem ser preenchidos por qualquer provider ERP.

## 2. Precedencia normativa

Este documento deve respeitar, nesta ordem:

1. `INTEGRATIONS-ARCH-01`
2. `INTEGRATIONS-ARCH-02`
3. `INTEGRATIONS-LIFECYCLE-01`
4. `ERP-DOMAIN-01`
5. `ERP-CONSOLE-01`
6. `ERP-GOV-02`
7. `ERP-CAPABILITY-01`
8. `ERP-PROVIDER-CONTRACT-02`

Regra:

- provider nao redefine dominio;
- provider nao redefine ownership;
- provider nao redefine escopo;
- provider nao cria segundo contrato equivalente.

## 3. Resultado da auditoria obrigatoria

### 3.1 Estruturas existentes que devem ser reutilizadas

O runtime atual ja materializa os contratos base e deve ser reutilizado:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.connection_schema`
- `MarketplaceIntegracao.credential_schema`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`

### 3.2 Estruturas existentes que devem ser estendidas

Devem ser estendidas semanticamente, sem redesign estrutural nesta execucao:

- `provider_definition`, hoje ainda minimo demais no adapter Sankhya;
- `feature_schema`, hoje reduzido a `supported_features`;
- `sync_schema`, hoje reduzido a `default_trigger`;
- `health_schema`, hoje reduzido a lista de estados;
- `IntegrationFeature.settings_payload`;
- `IntegrationSyncPolicy.settings_payload`.

### 3.3 Estruturas existentes que devem ser consolidadas

- `ERP-CAPABILITY-01` define capability; este documento define o envelope do provider que declara essas capabilities;
- `IntegrationFeature` continua sendo habilitacao concreta no tenant;
- `IntegrationSyncPolicy` continua sendo a policy concreta do tenant;
- `IntegrationHealth` continua sendo o runtime oficial de saude;
- `IntegrationJob` continua sendo a execucao observavel.

### 3.4 Estruturas que nao devem ser duplicadas

Nao criar:

- segundo `provider_definition`;
- segundo modelo de capability;
- segunda policy de sync;
- segundo modelo de health;
- nova tabela para contratos de provider;
- novo catalogo paralelo fora de `MarketplaceIntegracao`.

## 4. Principio central do contrato ERP

O contrato de provider ERP deve separar:

```text
definicao do provider
```

de:

```text
configuracao do tenant
```

e de:

```text
execucao runtime
```

Semantica oficial:

- `provider_definition` define o provedor como catalogo;
- `feature_schema` define as capabilities declaradas por esse provedor;
- `sync_schema` define o envelope oficial dos modos e restricoes de sincronizacao do provedor;
- `health_schema` define como a saude do provider deve ser interpretada;
- `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth` e `IntegrationJob` materializam a configuracao e a operacao reais.

## 5. Provider Definition

`provider_definition` e o contrato funcional que descreve a identidade e as capacidades estruturais do provider ERP.

### 5.1 Campos conceituais obrigatorios

Cada provider ERP deve declarar conceitualmente:

- `provider_code`
- `provider_name`
- `display_name`
- `vendor`
- `category`
- `supported_versions`
- `authentication_models`
- `supported_scopes`
- `supported_capabilities`
- `supported_sync_modes`
- `health_model`
- `documentation_url`
- `support_level`
- `maturity`
- `provider_notes`

### 5.2 Semantica dos campos

- `provider_code`: identificador canonico e estavel do provider.
- `provider_name`: nome interno oficial.
- `display_name`: nome funcional exibido ao usuario.
- `vendor`: fornecedor do ERP.
- `category`: deve ser `ERP`.
- `supported_versions`: versoes ou familias suportadas do provider.
- `authentication_models`: modelos de autenticacao aceitos.
- `supported_scopes`: apenas `TENANT` e `ESTABELECIMENTO`.
- `supported_capabilities`: referencia ao catalogo de capabilities declaradas.
- `supported_sync_modes`: modos que o provider pode declarar por capability.
- `health_model`: referencia ao contrato de health que o provider utiliza.
- `documentation_url`: documentacao oficial ou interna do provider.
- `support_level`: nivel oficial de suporte pela plataforma.
- `maturity`: maturidade geral do provider, distinta da maturidade de cada capability.
- `provider_notes`: observacoes gerais e restricoes amplas.

### 5.3 Regras obrigatorias

- nao incluir credencial de cliente;
- nao incluir ownership;
- nao incluir policy concreta do tenant;
- nao incluir estado runtime por tenant;
- nao incluir configuracao de conexao do cliente;
- nao incluir escopo operacional rural.

## 6. Feature Schema

`feature_schema` e o contrato funcional que declara como cada capability ERP deve ser descrita no catalogo do provider.

### 6.1 Campos conceituais obrigatorios por capability

Cada capability deve declarar:

- `capability_code`
- `display_name`
- `descricao`
- `status`
- `maturity`
- `direction`
- `supported_scopes`
- `supported_sync_modes`
- `dependencies`
- `restrictions`
- `observability_requirements`
- `pilot_tier`

### 6.2 Semantica

- `capability_code`: codigo canonico aderente a `ERP-CAPABILITY-01`.
- `display_name`: nome funcional legivel.
- `descricao`: descricao objetiva da responsabilidade.
- `status`: `SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `UNKNOWN`, `NOT_APPLICABLE`.
- `maturity`: `DECLARED`, `TESTED`, `PILOT_READY`, `PRODUCTION_READY`, `DEPRECATED`.
- `direction`: coerente com `ERP-DOMAIN-01`.
- `supported_scopes`: apenas `TENANT` e `ESTABELECIMENTO`.
- `supported_sync_modes`: modais declarativos do provider.
- `dependencies`: dependencias funcionais, tecnicas ou de modulo contratado.
- `restrictions`: limitacoes conhecidas do provider.
- `observability_requirements`: health, jobs, logs, reconciliacao e correlacao minima exigidos.
- `pilot_tier`: `RESTRITO`, `AMPLIADO`, `EXPORTADOR` ou `NAO_APLICAVEL`.

### 6.3 Relacao com runtime

- `feature_schema` define catalogo;
- `IntegrationFeature` habilita ou nao a capability para um tenant;
- `IntegrationFeature.settings_payload` pode carregar metadados complementares;
- o schema nao substitui a instancia concreta.

## 7. Sync Schema

`sync_schema` e o contrato funcional que define o envelope oficial das estrategias de sincronizacao suportadas pelo provider ERP.

### 7.1 O que o schema deve declarar

O contrato deve cobrir conceitualmente:

- `triggers`
- `retry`
- `timeout`
- `backoff`
- `batch`
- `polling`
- `webhook`
- `schedule`
- `event_driven`

### 7.2 Semantica

- `triggers`: disparos aceitos pelo provider.
- `retry`: capacidade e regra geral de retentativa.
- `timeout`: expectativa ou limite operacional.
- `backoff`: suporte e comportamento de espera entre retries.
- `batch`: suporte a lote e tamanho esperado.
- `polling`: se o provider aceita ou exige consulta periodica.
- `webhook`: se o provider emite ou recebe webhooks.
- `schedule`: se o provider admite execucao agendada.
- `event_driven`: se o provider aceita fluxo por evento, push ou outbox.

### 7.3 Regra de responsabilidade

- `sync_schema` nao substitui `IntegrationSyncPolicy`;
- `sync_schema` declara o que o provider suporta;
- `IntegrationSyncPolicy` materializa o que o tenant ativou.

### 7.4 Mapeamento com o runtime atual

O contrato deve orbitar:

- `IntegrationSyncMode`
- `retry_ativo`
- `retry_limite`
- `timeout_seconds`
- `backoff_seconds`
- `batch_size`
- `trigger_expression`
- `settings_payload`

Sem segunda policy.

## 8. Health Schema

`health_schema` e o contrato funcional que define como a saude da integracao ERP deve ser interpretada para aquele provider.

### 8.1 O que o schema deve declarar

Conceitualmente, deve cobrir:

- `possible_states`
- `severity_model`
- `availability_indicators`
- `latency_indicators`
- `authentication_indicators`
- `last_execution_indicators`
- `last_failure_indicators`
- `dependency_failure_indicators`
- `degraded_capability_indicators`

### 8.2 Semantica

- `possible_states`: estados reconhecidos pelo provider.
- `severity_model`: como classificar gravidade operacional.
- `availability_indicators`: evidencias de disponibilidade.
- `latency_indicators`: sinais de lentidao ou timeout.
- `authentication_indicators`: sinais de falha de credencial.
- `last_execution_indicators`: referencias da ultima execucao.
- `last_failure_indicators`: referencias de falha.
- `dependency_failure_indicators`: falhas decorrentes de servicos externos dependentes.
- `degraded_capability_indicators`: como reconhecer capability parcialmente degradada.

### 8.3 Regra de responsabilidade

- `health_schema` nao substitui `IntegrationHealth`;
- `health_schema` declara como interpretar health;
- `IntegrationHealth` materializa o snapshot real por tenant e escopo.

## 9. Relacao oficial entre os contratos

Encadeamento oficial:

```text
Provider Definition
  ↓
Feature Schema
  ↓
Sync Schema
  ↓
Health Schema
  ↓
IntegrationFeature
  ↓
IntegrationSyncPolicy
  ↓
IntegrationHealth
  ↓
IntegrationJob
```

Responsabilidades:

- `provider_definition`: identidade e envelope estrutural do provider.
- `feature_schema`: catalogo de capabilities declaradas.
- `sync_schema`: envelope declarativo dos modos de sincronizacao suportados.
- `health_schema`: envelope declarativo dos estados e sinais de saude.
- `IntegrationFeature`: habilitacao concreta da capability no tenant.
- `IntegrationSyncPolicy`: policy concreta da capability no tenant.
- `IntegrationHealth`: saude runtime do tenant.
- `IntegrationJob`: execucao operacional observavel.

Nenhum contrato pode assumir responsabilidade do outro.

## 10. Versionamento do provider

O provider deve poder evoluir sem quebrar adapters antigos.

Modelo conceitual:

```text
Provider v1
  ↓
Provider v2
  ↓
Provider v3
```

Regras:

- nova versao pode adicionar campos, capabilities e metadados;
- nova versao nao deve remover sem deprecacao clara;
- adapters existentes devem continuar interpretando pelo menos o subconjunto conhecido;
- breaking changes exigem novo ciclo arquitetural e revisao de compatibilidade.

## 11. Compatibilidade

Regras oficiais:

- provider antigo continua valido enquanto nao estiver `DEPRECATED` ou fora de suporte;
- provider novo deve preencher o mesmo contrato canonico;
- feature adicionada nao pode quebrar consumers antigos;
- feature removida deve passar por estado de deprecacao;
- feature depreciada nao deve ser tratada como P0 de piloto novo.

Compatibilidades minimas:

- backward-compatible para leitura de contrato;
- sem exigir remodelagem do runtime;
- sem exigir novo console paralelo.

## 12. Extensibilidade

Cada provider pode acrescentar metadados proprios.

Permitido:

- metadados de autenticacao especificos;
- notas de paginacao;
- limites de rate limit;
- codigos de erro conhecidos;
- observacoes de vendor;
- campos auxiliares de capability.

Proibido:

- alterar ownership;
- alterar capability matrix oficial do dominio;
- alterar policy oficial do runtime;
- alterar health oficial do runtime;
- criar escopo invalido;
- criar nomenclatura que contorne o contrato canonico.

## 13. Aplicacao conceitual ao Sankhya

O Sankhya hoje demonstra aderencia parcial:

### 13.1 Provider Definition

Ja existe, mas minimo:

- `provider`: `sankhya`
- `version`: `1`

Deve ser consolidado conceitualmente para incluir:

- vendor;
- modelos de autenticacao;
- scopes suportados;
- capabilities suportadas;
- maturidade;
- notas do provider.

### 13.2 Feature Schema

Ja existe, mas hoje reduzido a:

- `supported_features`

O provider atual ja materializa catalogo inicial com:

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`
- `estoque`

Esse catalogo deve ser interpretado como implementacao inicial de capabilities, nao como contrato completo.

### 13.3 Sync Schema

Ja existe, mas hoje reduzido a:

- `default_trigger`

O adapter tambem declara `supported_modes` dentro de `settings_payload` das features.

Isso mostra aderencia estrutural, mas ainda nao um contrato canonico consolidado.

### 13.4 Health Schema

Ja existe, mas hoje reduzido a:

- lista de `states`

O runtime de `IntegrationHealth` ja suporta muito mais do que o schema atualmente declara.

Conclusao:

- Sankhya e aderente ao runtime;
- Sankhya ainda nao preenche completamente o contrato funcional canonico deste documento;
- a lacuna principal e de consolidacao contratual, nao de fundacao estrutural.

## 14. Checklist oficial de conformidade

Todo novo provider ERP deve responder:

1. `provider_definition` esta completo?
2. `feature_schema` esta completo?
3. `sync_schema` esta completo?
4. `health_schema` esta completo?
5. capability matrix adere a `ERP-CAPABILITY-01`?
6. runtime oficial foi reutilizado?
7. houve duplicidade de contrato?
8. o provider esta conforme com escopo ERP?
9. o provider esta conforme com ownership?
10. o provider esta conforme com observabilidade minima?

Classificacao:

- `CONFORME`
- `CONFORME COM RESSALVAS`
- `NAO CONFORME`

## 15. Guardrails obrigatorios

Guardrails explicitos:

- provider nao redefine dominio;
- provider nao redefine ownership;
- provider nao redefine escopo;
- provider nao cria runtime paralelo;
- provider nao cria novo health;
- provider nao cria nova policy;
- provider nao cria novo modelo de capability;
- provider nao cria novo modelo de `provider_definition`;
- provider nao grava contrato paralelo fora de `MarketplaceIntegracao`;
- provider nao usa limitacao tecnica propria para reescrever regra da plataforma.

## 16. Veredicto arquitetural

O AgroSaaS ja possui a estrutura base necessaria para um contrato ERP canonico de provider.

Decisao oficial:

- reutilizar os campos atuais de `MarketplaceIntegracao`;
- consolidar semanticamente `provider_definition`, `feature_schema`, `sync_schema` e `health_schema`;
- manter `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth` e `IntegrationJob` como runtime oficial;
- evoluir os providers concretos para preencher este contrato, sem criar estrutura paralela.
