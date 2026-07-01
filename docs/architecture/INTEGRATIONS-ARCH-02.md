# INTEGRATIONS-ARCH-02 — Modelo Canônico de Providers, Conexões e Configurações

## 1. Objetivo

Refinar a arquitetura oficial do domínio de Integrações com o modelo canônico de:

- `IntegrationProvider`
- `IntegrationProviderDefinition`
- `IntegrationConnection`
- `IntegrationCredential`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationConfig`

Este documento define como o AgroSaaS deve representar provedores e configurações de integrações sem acoplar o domínio a um ERP específico.

## 2. Motivação

Situação atual:

- `INTEGRATIONS-ARCH-01` já definiu Integrações como domínio oficial;
- `Sankhya` já existe como integração real;
- cada provider possui parâmetros próprios de conexão, autenticação, feature e sync.

Problema:

- se o domínio tentar transformar parâmetros do Sankhya em campos universais, ele se acopla a um provider específico;
- isso inviabiliza um modelo genérico para SAP, TOTVS, Omie, bancos, clima, satélite, SMTP ou WhatsApp.

Decisão:

- o domínio de Integrações será orientado a contratos genéricos;
- cada provider declarará seu próprio schema;
- a configuração do cliente será composição de contratos, e não um único model com colunas fixas universais.

## 3. Relação com INTEGRATIONS-ARCH-01

`INTEGRATIONS-ARCH-01` definiu:

- Integrações como domínio transversal;
- escopos `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`;
- ERP por `TENANT` ou `ESTABELECIMENTO`;
- ERP nunca por `UnidadeProdutiva`;
- backoffice como console de observabilidade e suporte;
- tenant como console de configuração do cliente.

`INTEGRATIONS-ARCH-02` complementa essa arquitetura com o modelo conceitual de configuração e runtime.

Regra:

- `INTEGRATIONS-ARCH-02` não contradiz `INTEGRATIONS-ARCH-01`;
- ele apenas aprofunda a modelagem canônica do domínio.

## 4. Provider

`IntegrationProvider` é o catálogo oficial de tipos de integração.

Exemplos:

- Sankhya
- TOTVS
- SAP
- Omie
- Banco do Brasil
- Sicoob
- INMET
- Sentinel
- WhatsApp
- SMTP

Semântica oficial:

- `IntegrationProvider` representa o provedor/tipo;
- ele não representa a configuração do cliente;
- ele não contém o segredo do cliente;
- ele não é a conexão ativa do cliente.

Decisão:

- provider é metadado canônico do domínio;
- configuração do cliente sempre deve referenciar um provider, nunca copiar sua identidade conceitual para um model paralelo.

## 5. Provider Definition

`IntegrationProviderDefinition` é a definição arquitetural do provider.

Ela contém os schemas esperados para o provider:

- `connection_schema`
- `credential_schema`
- `feature_schema`
- `sync_schema`
- `health_schema`

Função:

- dizer quais campos são esperados;
- dizer quais são obrigatórios;
- dizer quais são opcionais;
- dizer quais features o provider suporta;
- dizer quais políticas de sync o provider aceita;
- dizer como health e status devem ser interpretados.

Exemplo conceitual:

```text
IntegrationProviderDefinition
  provider = "SANKHYA"
  category = "ERP"
  scope = ["TENANT", "ESTABELECIMENTO"]
  connection_schema = {...}
  credential_schema = {...}
  feature_schema = {...}
  sync_schema = {...}
  health_schema = {...}
```

Decisão:

- schemas do provider pertencem à definição do provider;
- não pertencem diretamente à configuração do tenant;
- não devem ser espalhados como regras implícitas em serviços soltos.

## 6. Connection

`IntegrationConnection` representa parâmetros técnicos de conexão não secretos.

Exemplos possíveis:

- `gateway_url`
- `service_url`
- `service_urls`
- `api_base_url`
- `environment`
- `api_version`
- `timeout`
- `retry_policy`
- `ssl_required`
- `proxy`
- `tenant_code`
- `company_code`

Regra central:

- os campos concretos variam por provider;
- o domínio não deve exigir que todos os providers tenham os mesmos campos;
- o domínio exige apenas a existência de um envelope canônico de conexão.

Semântica:

- `Connection` não contém senha, token, chave privada ou certificado secreto;
- `Connection` contém endpoints, ambiente, versão, timeouts e parâmetros técnicos não sensíveis.

## 7. Credential

`IntegrationCredential` representa segredos e credenciais.

Exemplos:

- `username`
- `password`
- `token`
- `app_key`
- `app_secret`
- `certificate`
- `private_key`
- `refresh_token`

Regras obrigatórias:

- nunca persistir em texto puro;
- nunca retornar segredo bruto no frontend;
- mascarar valores;
- versionar credenciais;
- auditar alteração;
- permitir rotação;
- separar segredos de parâmetros não secretos.

Decisão oficial:

- `IntegrationCredential` é contrato canônico próprio;
- credencial nunca deve ser confundida com `IntegrationConnection`;
- a leitura de credenciais deve ser excepcional e auditada.

## 8. Feature

`IntegrationFeature` representa capacidades habilitadas para uma configuração específica.

Exemplos:

- pessoas
- produtos
- financeiro
- NFe
- pedidos
- estoque

Semântica:

- uma integração pode estar configurada e ativa;
- mesmo assim, apenas parte das features pode estar habilitada;
- habilitar um provider não significa habilitar todas as capacidades.

Decisão:

- feature é parte da configuração do cliente;
- feature não é atributo fixo universal de todos os providers;
- o provider definition declara o catálogo possível; a configuração do cliente declara o subconjunto ativo.

## 9. Sync Policy

`IntegrationSyncPolicy` representa como cada feature sincroniza.

Modos oficiais:

- manual
- agendado
- por evento
- via outbox
- webhook
- pull
- push

Campos conceituais esperados:

- periodicidade
- batch size
- retry
- backoff
- idempotência
- deduplicação
- prioridade

Regras:

- a política pode variar por feature;
- `pessoas` pode ser manual ou agendado;
- `financeiro` pode ser por evento ou agendado;
- `NFe` pode ser push, pull, webhook ou híbrido.

Decisão:

- sync policy pertence ao runtime configurável da integração;
- não pertence ao catálogo estático do provider;
- `ProviderDefinition` apenas declara o que é suportado.

## 10. Health

`IntegrationHealth` representa o estado operacional da integração.

Estados conceituais mínimos:

- `CONNECTED`
- `DISCONNECTED`
- `DEGRADED`
- `AUTH_ERROR`
- `RATE_LIMITED`
- `CONFIG_ERROR`
- `PARTIAL_FAILURE`

Health deve refletir:

- conexão
- autenticação
- último sync
- falhas recentes
- retries
- backlog/fila
- feature failures parciais

Decisão:

- health não é apenas “conectou ou não conectou”;
- health precisa suportar degradação parcial por feature e por job.

## 11. Configuração final do cliente

Composição oficial:

```text
IntegrationProviderDefinition
  ↓
IntegrationConfig
  ↓
IntegrationConnection
  ↓
IntegrationCredential
  ↓
IntegrationFeature
  ↓
IntegrationSyncPolicy
  ↓
IntegrationHealth
```

Diferenças oficiais:

- `ProviderDefinition`: definição canônica do provedor.
- `IntegrationConfig`: configuração do cliente para aquele provider e escopo.
- `Connection`: parâmetros técnicos não secretos.
- `Credential`: segredos e autenticação.
- `Feature`: capacidades habilitadas.
- `SyncPolicy`: política operacional por feature.
- `Health`: fotografia runtime da integração.

## 12. Exemplo Sankhya

Sankhya é apenas um provider do tipo `ERP`.

### 12.1 Provider

```text
provider = SANKHYA
category = ERP
supported_scopes = [TENANT, ESTABELECIMENTO]
```

### 12.2 Connection

Exemplo conceitual:

- `gateway_url`
- `service_urls`
- `environment`
- `timeout`
- `company_code`

Observação:

- `gateway_url` é válido para Sankhya;
- ele não deve virar campo universal obrigatório do domínio.

### 12.3 Credential

Exemplo conceitual:

- `username`
- `password`
- `token`, quando aplicável

### 12.4 Features

Exemplo conceitual:

- pessoas
- produtos
- financeiro
- NFe
- pedidos
- estoque

### 12.5 Sync

Exemplo conceitual:

- pessoas: manual ou agendado
- produtos: manual ou agendado
- financeiro: por evento, agendado ou pull
- NFe: manual, agendado, push ou integração híbrida
- pedidos: por evento/outbox quando aplicável
- estoque: agendado ou por evento, conforme suporte

### 12.6 Health

Exemplo conceitual:

- conexão
- autenticação
- último sync
- erros recentes
- feature failures

### 12.7 Aplicação arquitetural

Sankhya deve se encaixar no padrão assim:

```text
IntegrationProviderDefinition(SANKHYA)
  ↓
IntegrationConfig(scope=TENANT ou ESTABELECIMENTO)
  ↓
Connection(gateway_url, service_urls, environment, timeout, company_code)
  ↓
Credential(username, password, token?)
  ↓
Features(pessoas, produtos, financeiro, nfe, pedidos, estoque)
  ↓
SyncPolicies(por feature)
  ↓
Health(runtime)
```

## 13. Exemplos de outros providers

### 13.1 SMTP

- `Connection`: host, port, ssl_required
- `Credential`: username, password
- `Features`: envio_transacional, envio_marketing
- `SyncPolicy`: não se aplica como sync clássico; usa delivery policy
- `Health`: connected, auth_error, degraded

### 13.2 INMET

- `Connection`: api_base_url, api_version, timeout
- `Credential`: token se houver
- `Features`: previsao, historico, alertas
- `SyncPolicy`: pull agendado
- `Health`: connected, rate_limited, partial_failure

### 13.3 Sentinel

- `Connection`: api_base_url, workspace, timeout
- `Credential`: token/app_key/app_secret
- `Features`: imagem, ndvi, mosaico
- `SyncPolicy`: agendado/pull
- `Health`: connected, degraded, auth_error

### 13.4 Banco do Brasil

- `Connection`: api_base_url, environment, api_version
- `Credential`: client_id, client_secret, certificate, private_key
- `Features`: extrato, pagamento, cobranca
- `SyncPolicy`: push/pull/webhook
- `Health`: connected, auth_error, rate_limited, partial_failure

## 14. Decisões arquiteturais

- `Provider` é catálogo, não configuração do cliente.
- `ProviderDefinition` declara schemas e capacidades, não segredos do cliente.
- `Connection` é envelope técnico não secreto.
- `Credential` é envelope secreto com rotação e auditoria.
- `Feature` representa capacidades ativas, não apenas capacidades possíveis.
- `SyncPolicy` é configurável por feature.
- `Health` é runtime, não metadado estático.
- nenhum campo específico do Sankhya se torna campo universal obrigatório do domínio.

## 15. Limitações deliberadas da V1

- o domínio pode começar com schemas flexíveis por provider antes de validação mais sofisticada;
- alguns providers existentes podem continuar com modelagem legada enquanto não migrarem para os contratos canônicos;
- health pode nascer simplificado por provider e amadurecer em fases;
- sync policy pode começar apenas com modos essenciais;
- versionamento e rotação de credenciais podem ser implementados incrementalmente.

## 16. Próximas execuções

Próxima execução recomendada:

**INTEGRATIONS-GOV-01 — Guardrails do Domínio de Integrações**

Base obrigatória:

- `INTEGRATIONS-ARCH-01`
- `INTEGRATIONS-ARCH-02`

Foco sugerido:

- impedir acoplamento a providers específicos;
- proteger separação `Connection` x `Credential`;
- exigir masking e rotação;
- exigir escopos corretos;
- proteger `ERP != UnidadeProdutiva`;
- aplicar o padrão ao Sankhya.
