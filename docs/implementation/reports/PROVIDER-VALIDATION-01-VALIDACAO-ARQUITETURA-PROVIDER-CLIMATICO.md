# PROVIDER-VALIDATION-01 — Validação Arquitetural com Provider Climático

## 1. Resumo Executivo

Esta auditoria validou o domínio oficial de Integrações contra um provider climático sem implementar nova integração.

Conclusão executiva:

- a arquitetura oficial já suporta naturalmente um provider climático no escopo `TENANT`;
- o modelo de provider, config, credential, feature, policy, job, health, eventos e observabilidade é suficientemente genérico;
- não há dependência estrutural de `UnidadeProdutiva`;
- ainda existem pontos parcialmente acoplados ao primeiro caso real, o Sankhya, principalmente na semântica inicial de jobs, health e eventos;
- esses pontos não bloqueiam um provider climático, mas indicam pequenos ajustes de maturidade antes de materializar um segundo provider.

Veredicto:

- o domínio de Integrações já está maduro para suportar novos providers;
- ainda há alguns ajustes incrementais recomendáveis para deixar health, eventos e observabilidade menos ERP-centric.

## 2. Provider escolhido

Provider escolhido: **OpenWeather**

Justificativa:

- representa um provider climático típico de mercado;
- usa contrato HTTP/REST simples;
- usa autenticação por `API Key`, o que testa bem o envelope de credenciais;
- possui cenários reais de `rate limit`, indisponibilidade, timeout, consulta sob demanda e atualização periódica;
- cobre bem features climáticas comuns em agro: previsão, chuva, temperatura, umidade, vento e histórico.

A escolha é adequada para validar o domínio porque é tecnicamente muito diferente de um ERP:

- não representa empresa administrativa;
- não trabalha com pessoas, produtos, NFe ou financeiro;
- tende a operar por consultas e snapshots;
- depende de políticas de pull, cache e rate limit.

## 3. Auditoria dos contratos

| Contrato | Classificação | Justificativa | Evidências |
| --- | --- | --- | --- |
| `IntegrationProvider` | ATENDE | O catálogo já suporta providers genéricos por `slug`, `provider_type`, `provider_definition` e schemas declarativos. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `MarketplaceIntegracao` |
| `IntegrationProviderDefinition` | ATENDE | O modelo já possui `connection_schema`, `credential_schema`, `feature_schema`, `sync_schema` e `health_schema`. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `MarketplaceIntegracao` |
| `IntegrationConfig` | ATENDE | `TenantIntegracao` já comporta provider, tenant, scope, lifecycle, connection e credencial referenciada. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `TenantIntegracao` |
| `IntegrationConnection` | ATENDE | `connection_payload` é genérico e não está acoplado a `ws_url`; suporta payload arbitrário por provider. | [docs/architecture/INTEGRATIONS-ARCH-02.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATIONS-ARCH-02.md), [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py) |
| `IntegrationCredential` | ATENDE | O modelo é separado, versionado, com masking e criptografia reutilizando `integracoes/security.py`. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationCredential`, [services/api/integracoes/security.py](/opt/lampp/htdocs/farm/services/api/integracoes/security.py) |
| `IntegrationFeature` | ATENDE | O conceito é genérico e comporta facilmente features meteorológicas. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationFeature` |
| `IntegrationSyncPolicy` | ATENDE | Já representa `MANUAL`, `AGENDADO`, `PULL`, retry, backoff, timeout e idempotência. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationSyncPolicy` |
| `IntegrationHealth` | ATENDE PARCIALMENTE | Atende runtime health e falhas consecutivas, mas não possui estado explícito para `TIMEOUT` e `API_UNAVAILABLE`; hoje isso precisaria mapear para `DEGRADED` ou `CONFIG_ERROR`. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationHealthStatus` |
| `IntegrationJob` | ATENDE PARCIALMENTE | Representa execuções e retries, mas `cache hit` e `cache miss` hoje entram melhor como payload/result do job do que como estado oficial explícito. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationJob` |
| `IntegrationVersion` | ATENDE | O snapshot mascarado e versionado suporta bem mudanças de config e credencial de provider climático. | [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py): `IntegrationVersion` |
| Domain Events | ATENDE PARCIALMENTE | A infraestrutura atende, mas os eventos oficiais atuais são mais focados em config/job/health; eventos específicos como `rate limit exceeded` ou `credential expired` dependeriam de payload ou evolução incremental. | [services/api/integracoes/events.py](/opt/lampp/htdocs/farm/services/api/integracoes/events.py), `publish_domain_event_safe(...)` via infraestrutura `events` |
| Outbox | ATENDE | O provider climático pode publicar eventos via infraestrutura já existente sem nova fila. | [docs/implementation/reports/INTEGRATIONS-DOMAIN-01-AUDITORIA-MATERIALIZACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/INTEGRATIONS-DOMAIN-01-AUDITORIA-MATERIALIZACAO.md), `events/outbox_*` citados no relatório |
| Alert Engine | ATENDE | O motor já é adequado para indisponibilidade, credencial inválida, rate limit e dados desatualizados. | [docs/implementation/reports/INTEGRATIONS-DOMAIN-01-AUDITORIA-MATERIALIZACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/INTEGRATIONS-DOMAIN-01-AUDITORIA-MATERIALIZACAO.md) |
| Notification Engine | ATENDE | O domínio já possui dispatcher, policies e adapters reutilizáveis. | pesquisa em `services/api/notifications/` |

## 4. Connection

O modelo atual comporta naturalmente um provider climático com:

- `api_base_url`
- `api_key` referenciada em `IntegrationCredential`
- `bearer_token`
- `timeout`
- `retry`
- `rate_limit`
- `cache_ttl`
- `environment`
- `api_version`

Justificativa:

- `connection_payload` em `TenantIntegracao` já é JSON genérico;
- `MarketplaceIntegracao` já possui `connection_schema`, permitindo declarar estrutura esperada do provider;
- `IntegrationSyncPolicy` já modela timeout, retry, backoff e batch;
- não existe coluna fixa ERP-only no envelope oficial.

Classificação: **ATENDE**

Observação:

- `cache_ttl` não possui campo dedicado; entraria naturalmente em `connection_payload` ou `settings_payload` da feature/policy. Isso não exige mudança estrutural.

## 5. Credential

O modelo atual suporta sem alteração estrutural:

- API Key
- Bearer Token
- OAuth Access Token
- Refresh Token
- Client Secret

Justificativa:

- `IntegrationCredential.segredo_criptografado` é envelope genérico;
- `mask_metadata` suporta apresentação mascarada;
- `version_number`, `ativo` e `rotated_at` suportam rotação;
- `integracoes/security.py` já criptografa e mascara o segredo;
- a arquitetura já prevê separação entre connection e credential.

Classificação: **ATENDE**

Limitação não estrutural:

- OAuth completo exigiria materializar a lógica de refresh e auditoria operacional do token, mas o modelo persistente já suporta isso.

## 6. Features

Features climáticas modeláveis no contrato atual:

- previsão do tempo
- chuva
- temperatura
- umidade
- vento
- evapotranspiração
- alertas meteorológicos
- séries históricas

`IntegrationFeature` é suficiente porque:

- cada feature já tem `codigo`, `nome`, `descricao`, `habilitada`, `obrigatoria` e `settings_payload`;
- um tenant pode habilitar apenas parte das capacidades do provider;
- features climáticas não exigem nova semântica estrutural.

Classificação: **ATENDE**

## 7. SyncPolicy

Políticas necessárias para clima:

- pull periódico
- atualização diária
- atualização horária
- atualização sob demanda
- cache

O modelo atual suporta isso com:

- `mode = PULL`, `MANUAL` ou `AGENDADO`
- `trigger_expression`
- `retry_limite`
- `backoff_seconds`
- `timeout_seconds`
- `idempotencia_ativa`
- `settings_payload`

Classificação: **ATENDE**

Limitação de detalhe:

- cache não é primeiro cidadão no modelo; entra como parâmetro de policy ou feature. Isso é suficiente arquiteturalmente.

## 8. Jobs

Cenários operacionais de um provider climático:

- consulta realizada
- erro de autenticação
- timeout
- rate limit
- cache hit
- cache miss
- retry

O modelo atual cobre bem:

- execução iniciada e concluída;
- falha e retry;
- contagem de processamento, sucessos, erros;
- `request_payload`, `result_payload`, `error_message`;
- correlação por `correlation_id` e `causation_id`.

Classificação: **ATENDE PARCIALMENTE**

Motivo do parcial:

- `cache hit` e `cache miss` não são estados oficiais próprios;
- `TIMEOUT` não é status explícito do job, mas cabe em `FAILED + error_message` ou payload;
- isso não bloqueia a integração, apenas reduz semântica pronta para diagnóstico.

## 9. Health

Estados desejáveis para clima:

- `CONNECTED`
- `RATE_LIMITED`
- `TIMEOUT`
- `AUTH_ERROR`
- `API_UNAVAILABLE`
- `DEGRADED`

O modelo atual já cobre:

- `CONNECTED`
- `RATE_LIMITED`
- `AUTH_ERROR`
- `DEGRADED`
- `CONFIG_ERROR`
- `PARTIAL_FAILURE`

Classificação: **ATENDE PARCIALMENTE**

Motivo:

- `TIMEOUT` e `API_UNAVAILABLE` não aparecem como estados dedicados;
- hoje precisariam ser mapeados para `DEGRADED` ou `CONFIG_ERROR`, com detalhe no payload.

Conclusão:

- suficiente para operar;
- ainda não ideal para expressividade máxima de um provider de consulta climática.

## 10. Eventos

Eventos esperados para clima:

- consulta iniciada
- consulta concluída
- consulta falhou
- provider indisponível
- credencial expirada
- limite excedido

Eventos atuais:

- `IntegrationConfigured`
- `IntegrationActivated`
- `IntegrationDisabled`
- `IntegrationCredentialRotated`
- `IntegrationSyncStarted`
- `IntegrationSyncCompleted`
- `IntegrationSyncFailed`
- `IntegrationHealthChanged`

Classificação: **ATENDE PARCIALMENTE**

Motivo:

- consulta iniciada/concluída/falhou cabe diretamente em `IntegrationSyncStarted/Completed/Failed`;
- `provider indisponível`, `credencial expirada` e `limite excedido` hoje cabem como causa em `IntegrationSyncFailed` e em `IntegrationHealthChanged`;
- não existe ainda evento oficial explícito para `credential expired` ou `rate limit exceeded`.

Conclusão:

- a infraestrutura e o envelope atendem;
- a taxonomia de eventos ainda pode ser refinada para providers não ERP.

## 11. Alertas

Alertas climáticos operacionais possíveis:

- API fora
- token expirado
- limite excedido
- dados desatualizados

O Alert Engine atual é suficiente porque:

- já é multi-tenant;
- já é desacoplado;
- já foi posicionado como motor transversal;
- integra bem com health, jobs e eventos.

Classificação: **ATENDE**

Observação:

- o que ainda faltaria seria apenas o generator específico do provider climático, não nova infraestrutura.

## 12. Observabilidade

A observabilidade já suporta naturalmente o provider climático com:

- timeline
- diagnóstico
- jobs
- health
- origem oficial/legacy

Justificativa:

- a camada de observabilidade construída no Sankhya é baseada em contratos genéricos (`IntegrationJob`, `IntegrationHealth`, timeline consolidada e diagnóstico);
- não depende semanticamente de pessoas, produtos ou NFe para existir;
- um provider climático não teria legado Sankhya, mas usaria diretamente a camada oficial.

Classificação: **ATENDE**

Limitação:

- parte da implementação atual de UX ainda usa texto e agrupamentos pensados no Sankhya; isso é acoplamento de apresentação, não estrutural.

## 13. Gap Analysis

### O que funciona sem alterações

- provider catalogado em `MarketplaceIntegracao`;
- provider definition por schema;
- config por `TenantIntegracao`;
- credential criptografada e mascarada;
- features genéricas;
- sync policy genérica;
- escopo `TENANT` com preparação para `ESTABELECIMENTO`;
- jobs oficiais;
- versionamento de configuração;
- outbox, alert engine e notification engine reutilizáveis;
- timeline e diagnóstico como observabilidade transversal.

### O que exige pequenos ajustes

- health com estados mais expressivos para `TIMEOUT` e `API_UNAVAILABLE`;
- taxonomia de eventos mais rica para `rate limit exceeded` e `credential expired`;
- explicitar cache hit/miss de forma mais semântica em observabilidade;
- tornar parte da UX menos textual/semântica de ERP.

### Limitações estruturais encontradas

Nenhuma limitação estrutural impeditiva foi encontrada.

As limitações observadas são de:

- semântica de enum/evento;
- refinamento de diagnóstico;
- especialização de provider;

e não de fundação arquitetural.

### Acoplamentos ao Sankhya identificados

Acoplamentos residuais:

- o primeiro adapter real foi ERP-centric;
- parte dos exemplos, textos e agrupamentos da camada de observabilidade ainda refletem Sankhya;
- alguns eventos e health statuses estão mais maduros para sync administrativo do que para consulta climática.

Conclusão:

- existe acoplamento de maturidade e nomenclatura;
- não existe acoplamento estrutural bloqueante.

## 14. Veredicto

**O domínio de Integrações já está maduro para suportar novos providers.**

Resposta objetiva à pergunta central:

- **não** foram encontradas dependências estruturais que obriguem novo redesign para um provider climático;
- **sim**, ainda existem pequenas heranças do Sankhya na semântica de health, eventos e UX;
- essas heranças pedem refinamento incremental, não reabertura arquitetural.

Classificação final de aderência:

- arquitetura: **alta aderência**
- implementação oficial: **aderência suficiente para novo provider**
- acoplamento residual ao Sankhya: **baixo a moderado, não bloqueante**

## 15. Próxima execução

Próxima execução recomendada:

**`PROVIDER-DOMAIN-01` — Materialização de um Provider Climático de Referência**

Escopo recomendado dessa próxima etapa:

- escolher um provider climático real;
- materializar provider definition;
- criar adapter oficial simples;
- validar `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`, timeline e alertas em um contexto não ERP;
- manter isso como prova arquitetural de generalidade do domínio.
