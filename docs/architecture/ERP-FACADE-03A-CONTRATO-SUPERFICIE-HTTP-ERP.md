# ERP-FACADE-03A - Contrato Oficial da Superficie HTTP ERP

Status: APROVADA  
Categoria: Arquitetura Funcional  
Tipo: Regra Arquitetural  
Data: 2026-07-09

## 1. Objetivo

Definir o contrato arquitetural oficial da Superficie HTTP ERP do AgroSaaS.

Este documento existe para orientar a futura Fase B.1 de convergencia HTTP sem criar:

- novo runtime;
- novo dominio;
- novo adapter;
- novo motor de sincronizacao;
- nova camada de regras;
- nova persistencia.

Regra central:

- a Superficie HTTP ERP e uma camada fina de consumo e composicao;
- ela reutiliza integralmente a arquitetura oficial ja aprovada;
- ela nao substitui o runtime, os adapters ou os contratos de provider;
- ela apenas organiza o transporte HTTP para consumidores ERP genericos.

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
9. `ERP-CONSOLIDATION-03`

Regra:

- a Superficie HTTP ERP nao pode contradizer nenhum documento acima;
- a Superficie HTTP ERP nao cria segunda arquitetura;
- qualquer implementacao futura deve ser interpretada como composicao sobre o runtime existente.

## 3. Decisao arquitetural

A Superficie HTTP ERP e uma camada oficial de consumo para UI, Wizard, backoffice e outros consumidores ERP genericos.

Ela:

- expoe apenas conceitos comuns de leitura e operacao administrativa do dominio ERP;
- delega para servicos oficiais ja existentes;
- pode combinar respostas canonicas e metadata de provider quando isso for necessario para a UX;
- nao persiste estado proprio;
- nao recalcula regras fora do runtime oficial.

Ela nao e:

- novo runtime;
- novo dominio;
- novo adapter;
- novo motor de sync;
- nova politica de health;
- novo resolvedor de ownership;
- nova estrategia de mapeamento externo;
- segunda camada de contrato canonico paralela ao provider contract.

## 4. Posicionamento oficial na arquitetura

Fluxo oficial:

```text
Provider Contract
  ↓
Provider Adapter
  ↓
Runtime oficial de Integracoes
  ↓
Superficie HTTP ERP
  ↓
UI / Wizard / Backoffice
```

Regras de fronteira:

- o adapter continua responsavel por autenticacao, traducao, sync tecnico e particularidades do provider;
- o runtime continua responsavel por configuracao, capabilities concretas, policies, health, jobs e associacoes;
- a Superficie HTTP ERP organiza o transporte para consumidores genericos;
- a UI nao deve depender de paths provider-first para conceitos comuns de leitura.

## 5. Responsabilidades da Superficie HTTP ERP

A Superficie HTTP ERP pode expor apenas conceitos comuns de consumo, incluindo:

- status ERP;
- situacao da integracao;
- funcoes disponiveis;
- regras de atualizacao;
- health consolidado;
- jobs;
- timeline;
- diagnostico;
- associacoes externas;
- readiness para piloto.

Interpretacao oficial:

- `status ERP` significa leitura consolidada de configuracao, ativacao, lifecycle e disponibilidade minima para o tenant;
- `situacao da integracao` significa como o ERP conectado se apresenta operacionalmente para a plataforma;
- `funcoes disponiveis` significa capabilities declaradas pelo provider e habilitadas para o tenant;
- `regras de atualizacao` significa politicas efetivamente ativas no runtime oficial;
- `health consolidado` significa leitura do runtime oficial de saude, com fallback controlado quando houver compatibilidade legada;
- `jobs`, `timeline` e `diagnostico` significam observabilidade do dominio ERP, nunca um segundo motor de operacao;
- `associacoes externas` significam governanca do de-para oficial entre registros internos e externos;
- `readiness` significa a avaliacao do runtime oficial para piloto e operacao inicial.

## 6. O que nao pertence a Superficie HTTP ERP

Continuam obrigatoriamente provider-specific:

- autenticacao;
- gateway;
- OAuth;
- login legado;
- teste de conexao;
- sincronizacao tecnica;
- fiscal;
- financeiro;
- NFe;
- staging;
- payload mapping;
- transformacao de dados;
- tratamento de erros especificos;
- endpoints operacionais exclusivos do provider.

Regra:

- a Superficie HTTP ERP nao canoniza fluxos tecnicos do provider;
- a Superficie HTTP ERP nao tenta esconder a existencia de operacoes provider-specific;
- a Superficie HTTP ERP so cobre o que e comum e reutilizavel entre consumers ERP.

## 7. Rotas candidatas ERP-generic

As seguintes rotas ficam declaradas como candidatas futuras para a Fase B.1:

```text
GET /api/v1/integracoes/erp/status
GET /api/v1/integracoes/erp/health
GET /api/v1/integracoes/erp/jobs
GET /api/v1/integracoes/erp/timeline
GET /api/v1/integracoes/erp/diagnostico
GET /api/v1/integracoes/erp/associacoes/pendentes
POST /api/v1/integracoes/erp/associacoes/{id}/reconciliar
```

Regra obrigatoria:

- estas rotas sao candidatas documentais;
- elas nao fazem parte desta execucao;
- a implementacao futura deve delegar para servicos existentes, sem copiar regras.

## 8. Regra oficial de composicao

A Superficie HTTP ERP deve apenas compor dados vindos de:

- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`
- `ExternalRecordAssociation`
- `ErpReadinessService`
- adapters existentes, quando necessario

Regras obrigatorias:

- nao duplicar logica de readiness;
- nao duplicar logica de health;
- nao duplicar logica de jobs;
- nao duplicar logica de associacoes externas;
- nao persistir estado proprio;
- nao criar segunda policy de sincronizacao;
- nao criar novo modelo de capability;
- nao criar novo contrato paralelo de provider.

Interpretacao:

- a camada HTTP ERP pode reorganizar o formato de consumo;
- ela nao pode redefinir a origem semantica da informacao.

## 9. Resolvedor conceitual de provider

A implementacao futura pode precisar de um resolvedor conceitual de provider ativo na borda HTTP.

Nesta execucao, ele fica apenas documentado como conceito.

Responsabilidades conceituais do resolvedor:

- identificar qual ERP esta conectado no escopo administrativo corrente;
- identificar qual provider atende o tenant ou estabelecimento;
- identificar quais funcoes estao disponiveis;
- identificar quais operacoes sao genericas;
- identificar quais operacoes permanecem especificas do provider.

Regra:

- o resolvedor nao cria runtime novo;
- o resolvedor nao decide ownership;
- o resolvedor nao substitui `MarketplaceIntegracao`, `TenantIntegracao` ou o adapter;
- ele apenas organiza a resolucao do provider ativo para a camada HTTP ERP.

## 10. Compatibilidade com Sankhya

`/api/v1/integracoes/sankhya/*` permanece valido como:

- compatibilidade;
- superficie provider-specific;
- suporte a autenticacao;
- suporte a sync tecnico;
- suporte a fiscal, financeiro e NFe;
- fallback durante migracao.

Regras:

- nenhuma rota Sankhya deve ser depreciada nesta fase documental;
- nenhuma remocao de compatibilidade e autorizada por este documento;
- a migracao futura da UI deve ocorrer de forma incremental e reversivel.

## 11. Politica para novos ERPs

SAP, TOTVS, Omie, Senior e futuros ERPs devem integrar-se via:

```text
Provider Contract
↓
Provider Adapter
↓
Runtime oficial
↓
Superficie HTTP ERP
↓
UI / Wizard / Backoffice
```

Regra oficial:

- a UI nao deve precisar conhecer endpoints especificos para leituras comuns;
- a UI pode continuar conhecendo operacoes provider-specific quando elas realmente forem tecnicas ou exclusivas;
- novos providers devem preencher `provider_definition`, `feature_schema`, `sync_schema` e `health_schema` segundo o contrato oficial;
- a camada HTTP ERP nao deve variar seu papel a cada provider.

## 12. Relacao com Wizard, Console e Backoffice

Regras oficiais:

- o Wizard deve continuar usando `ErpReadinessService`;
- o Console ERP deve migrar gradualmente para a Superficie HTTP ERP;
- o Backoffice deve migrar gradualmente para a Superficie HTTP ERP;
- nenhuma tela deve recalcular readiness, health ou jobs.

Interpretacao:

- o Wizard continua verificador, nao configurador;
- o Console ERP continua sendo a camada administrativa oficial do tenant;
- o Backoffice continua observando, diagnosticando e apoiando;
- a Superficie HTTP ERP organiza o consumo comum entre essas camadas.

## 13. Contratos conceituais por tipo de rota

### 13.1 Leitura consolidada

Rotas de leitura consolidada podem expor:

- identificacao do provider conectado;
- estado de ativacao;
- lifecycle;
- status de health;
- resumo de capabilities habilitadas;
- resumo de politicas ativas;
- readiness;
- metadata declarativa util para a UX.

### 13.2 Observabilidade

Rotas de observabilidade podem expor:

- health;
- jobs;
- timeline;
- diagnostico;
- logs somente quando houver justificativa clara de suporte e compatibilidade.

Regra:

- logs legados nao sao contrato obrigatorio da superficie ERP;
- timeline e diagnostico sao contratos mais adequados para consumo generico.

### 13.3 Governanca de associacoes

Rotas de governanca podem expor:

- pendencias;
- conflitos;
- reconciliacao manual;
- historico auditavel associado ao runtime oficial.

Regra:

- `ExternalRecordAssociation` continua sendo a unica fonte oficial;
- nenhuma segunda estrategia de de-para e permitida.

## 14. Politica de compatibilidade e migracao

Politica oficial:

- a introducao da Superficie HTTP ERP nao invalida a superficie provider-specific existente;
- a UI deve migrar por fases;
- a compatibilidade com Sankhya deve permanecer durante a convergencia;
- rollback para a superficie antiga deve ser simples.

Fases esperadas:

- Fase B.1: convergencia da superficie HTTP;
- Fase B.2: migracao gradual da UI;
- Fase B.3: convivencia e compatibilidade;
- Fase B.4: depreciacao controlada.

## 15. Criterios de implementacao futura

Criterios minimos para liberar a Fase B.1:

- nenhum novo runtime;
- nenhuma migration;
- nenhum modelo novo;
- nenhum job novo;
- endpoints apenas de composicao;
- delegacao para servicos existentes;
- testes de contrato;
- compatibilidade com rotas Sankhya;
- rollback simples para endpoints antigos.

Criterios adicionais obrigatorios:

- nenhuma logica nova de negocio no router;
- nenhuma duplicacao de readiness;
- nenhuma duplicacao de health;
- nenhuma duplicacao de jobs;
- nenhuma duplicacao de reconciliacao externa;
- nenhuma canonizacao indevida de operacoes tecnicas do provider.

## 16. Conclusao normativa

A Superficie HTTP ERP fica oficialmente definida como uma camada fina de consumo e composicao.

Ela:

- e autorizada arquiteturalmente;
- e coerente com a arquitetura ERP consolidada;
- e compativel com o runtime oficial;
- nao substitui adapters;
- nao cria arquitetura paralela;
- deve ser implementada futuramente apenas na borda HTTP, preservando integralmente a hierarquia arquitetural existente.
