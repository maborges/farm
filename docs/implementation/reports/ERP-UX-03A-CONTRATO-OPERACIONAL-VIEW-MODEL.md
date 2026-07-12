# ERP-UX-03A - Contrato Operacional e View Model do Console ERP

Data da execucao: 2026-07-12

## 1. Resumo

Esta fase introduz uma camada tipada e puramente frontend para representar capabilities ERP no `DynamicErpConsole`, sem alterar runtime, APIs, adapters, backend ou fluxos P2.

O resultado principal foi:

- extracao dos tipos HTTP e operacionais que estavam embutidos no `erp-console.tsx`;
- criacao de um view model operacional especifico da interface;
- criacao de uma funcao pura de composicao para capabilities;
- adaptacao minima do `DynamicErpConsole` para consumir o novo contrato;
- manutencao do `SankhyaConsole` como wrapper provider-specific responsavel por expor acoes manuais reais.

## 2. Arquivos auditados

- `docs/implementation/reports/ERP-UX-03-AUDITORIA-CONSOLE-OPERACIONAL-ERP.md`
- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/package.json`

## 3. Tipos preexistentes encontrados

Antes da extracao, o `DynamicErpConsole` declarava inline:

- `ProviderFieldSelectOption`
- `ProviderFieldDefinition`
- `ProviderSchemaDefinition`
- `ProviderPublicIdentity`
- `ProviderSchemaResponse`
- `CapabilityMatrixItem`
- `ProviderDefinition`
- `SankhyaConfig`
- `SankhyaStatus`
- `SankhyaHealth`
- `SankhyaJob`
- `SyncLog`
- `ExternalAssociationHistoryItem`
- `ExternalAssociationPendingItem`
- `SankhyaDiagnosis`

Esses tipos misturavam:

- schema HTTP;
- payload provider-specific;
- dados canonicos ERP;
- e a futura experiencia operacional.

## 4. Tipos duplicados identificados

- Os contratos de status, health, jobs, diagnostico e timeline ja apareciam de forma semelhante no backoffice ERP.
- O tipo `ErpTimelineItem` ja estava separado em `sankhya-timeline.tsx`, mas os demais contratos continuavam presos ao `erp-console.tsx`.
- O console generico consumia payloads ainda nomeados como `Sankhya*`, mesmo quando acessava endpoints canonicos `/integracoes/erp/*`.

## 5. Inspecao curta pre-codigo

Resultado da releitura e localizacao obrigatoria:

- o relatorio `ERP-UX-03-AUDITORIA-CONSOLE-OPERACIONAL-ERP.md` foi relido antes das alteracoes;
- os tipos relevantes estavam concentrados no `apps/web/src/components/integracoes/erp-console.tsx`;
- o componente generico consumia diretamente contratos nomeados como `SankhyaConfig`, `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaDiagnosis` e `ExternalAssociationPendingItem`;
- os dados usados na tela ja vinham de `status`, `health`, `jobs`, `timeline`, `diagnostico`, `provider schema` e `associacoes pendentes`;
- a composicao de status operacional, maturidade, acoes, pendencias e sincronizacao manual podia ser feita exclusivamente no frontend com os dados ja carregados;
- nao existia modulo dedicado de tipos ERP nem modulo de view model para integracoes no frontend;
- o `SankhyaConsole` ja era o ponto correto para fornecer contratos provider-specific, inclusive endpoints de sync manual.

## 6. Contrato visual adotado

Arquivos criados:

- `apps/web/src/components/integracoes/erp/types.ts`
- `apps/web/src/components/integracoes/erp/capability-labels.ts`
- `apps/web/src/components/integracoes/erp/capability-view-model.ts`

Contrato operacional principal:

- `ErpCapabilityOperationalStatus`
- `ErpSyncDirection`
- `ErpSyncMode`
- `ErpCapabilityMaturity`
- `ErpCapabilityActionsViewModel`
- `ErpCapabilityTechnicalViewModel`
- `ErpCapabilityViewModel`
- `BuildErpCapabilityViewModelsInput`

O contrato adotado representa somente a experiencia operacional do console, sem introduzir nova fonte de verdade persistente.

## 7. Regras de composicao

Funcao central:

- `buildErpCapabilityViewModels(input)`

Regras implementadas:

- usa apenas dados ja carregados pelo console;
- nao executa fetch;
- nao acessa estado global;
- nao contem JSX;
- nao contem regra Sankhya hardcoded no modulo generico;
- recebe a lista de sincronizacoes manuais reais pelo wrapper provider-specific;
- calcula status operacional a partir de feature schema, features habilitadas, health, jobs e associacoes;
- diferencia capability materializada de capability apenas declarada;
- mantem `reprocessamento` sempre `false`;
- impede `estoque` P2 de ficar operacional mesmo se algum payload vier habilitado;
- nao inventa capability `comercializacao`;
- nao desmembra `pessoas` em `clientes` e `fornecedores`.

## 8. Fontes de cada campo

| Campo | Fonte principal |
| --- | --- |
| `code` | `capability_matrix.capability_code` |
| `name` | catalogo operacional interno com fallback para `display_name` |
| `description` | catalogo operacional interno com fallback para `description` |
| `providerSlug` | prop do console |
| `providerName` | `status.provider_definition.display_name` com fallbacks de config/schema |
| `status` | composicao de `capability_matrix`, `features_habilitadas`, `status.configurado` e `health.status` |
| `enabled` | `status.features_habilitadas` |
| `maturity` | `capability_matrix.status`, `capability_matrix.maturity` e `pilot_tier` |
| `direction` | `capability_matrix.direction` |
| `masterSystem` | catalogo operacional + fallback por direcao |
| `syncMode` | `policies_resumidas.mode` com fallback para `supported_sync_modes` |
| `healthStatus` | `health.status` com fallback para `status.health_status` |
| `lastSyncAt` | ultimo job bem-sucedido por capability, com fallback para `status.last_success_at` e `status.ultimo_sync` |
| `lastJobAt` | ultimo job por capability |
| `nextRunAt` | `status.proximo_sync` quando ha policy ativa para a capability |
| `pendingAssociations` | associacoes pendentes filtradas por `feature_code` |
| `conflictingAssociations` | associacoes em conflito filtradas por `feature_code` |
| `actions.canSyncManually` | wrapper provider-specific + capability implementada/habilitada |
| `actions.canConfigure` | existencia de schema/configuracao aplicavel |
| `actions.canReconcile` | existencia de pendencia ou conflito na capability |
| `technical.adapterLabel` | wrapper provider-specific |
| `technical.internalOperationLabels` | catalogo operacional sanitizado |
| `technical.externalSystemLabel` | nome do provider |

## 9. Capabilities representadas

Capabilities cobertas pelo contrato atual:

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`
- `estoque`

Capabilities nao criadas:

- `comercializacao`
- `clientes`
- `fornecedores`

## 10. Tratamento de capabilities declaradas e P2

- `pedidos` permanece capability declarada e P2.
- `estoque` permanece capability declarada e P2.
- ambas aparecem no contrato com maturidade `P2`.
- ambas ficam com `status` operacional `DECLARED`.
- ambas ficam com `enabled = false`.
- ambas ficam sem sync manual.
- `estoque` nunca recebe `ACTIVE`, `PARTIAL` ou `DEGRADED`.

## 11. Tratamento de acoes

- `Visualizar detalhes`: permitido no contrato para capabilities materializadas ou declaradas.
- `Sincronizar manualmente`: depende de capability implementada/habilitada e de lista explicita fornecida pelo wrapper.
- `Configurar`: depende da existencia de schema/campos de configuracao.
- `Reconciliar`: depende de pendencias ou conflitos reais da capability.
- `Reprocessar`: fixado em `false`.

No wrapper Sankhya foram declaradas como acoes reais:

- sync manual de `pessoas`
- sync manual de `produtos`
- sync completo `completo` como acao adicional do provider

## 12. Decisoes de linguagem

A composicao passou a privilegiar a linguagem operacional:

- Sistema responsavel
- Sentido da atualizacao
- Forma de atualizacao
- Ultima atualizacao
- Situacao da integracao
- Pendencias de associacao
- Executado pelo conector Sankhya

O campo tecnico preserva rotulos sanitizados e nao exibe:

- credenciais
- tokens
- payload bruto de runtime
- nomes de classes Python
- endpoints literais sensiveis

## 13. Arquivos alterados

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/erp/types.ts`
- `apps/web/src/components/integracoes/erp/capability-labels.ts`
- `apps/web/src/components/integracoes/erp/capability-view-model.ts`
- `apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts`
- `docs/implementation/reports/ERP-UX-03A-CONTRATO-OPERACIONAL-VIEW-MODEL.md`

## 14. Testes criados

- `apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts`

Cenarios cobertos:

- capability implementada e saudavel;
- capability com health critico;
- capability desabilitada;
- capability declarada;
- capability P2;
- associacao pendente;
- associacao em conflito;
- respostas parciais/ausentes;
- sync manual sem endpoint/provider contract;
- reprocessamento sempre indisponivel;
- estoque P2 nunca ativo;
- comercializacao nao inventada;
- clientes e fornecedores nao duplicados fora de `pessoas`.

## 15. Comandos executados

No frontend:

```bash
cd apps/web
npm run typecheck
npm run lint
```

Teste unitario da composicao:

```bash
apps/web/node_modules/.bin/tsc \
  apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts \
  apps/web/src/components/integracoes/erp/capability-view-model.ts \
  apps/web/src/components/integracoes/erp/capability-labels.ts \
  apps/web/src/components/integracoes/erp/types.ts \
  --module commonjs \
  --target es2020 \
  --moduleResolution node \
  --esModuleInterop \
  --skipLibCheck \
  --typeRoots apps/web/node_modules/@types \
  --types node \
  --outDir /tmp/erp-ux-03a-tests

node --test /tmp/erp-ux-03a-tests/tests/unit/integracoes/erp-capability-view-model.test.js
```

Validacao documental:

```bash
git diff --check
```

## 16. Resultados

- `npm run typecheck`: passou
- `npm run lint`: passou
- teste unitario da composicao: passou
- `git diff --check`: sem erros de whitespace ou conflitos de patch

## 17. Limitacoes

- o `apps/web` nao possui hoje um runner dedicado de testes unitarios TypeScript para modulos puros de composicao;
- por isso, o teste desta fase foi compilado de forma isolada com `tsc` e executado com `node --test`;
- o console ainda nao implementa o Capability Center completo, apenas passa a consumir o contrato operacional na tabela e nas acoes manuais basicas.

## 18. Riscos

- `nextRunAt` continua sendo uma aproximacao por capability, porque o runtime atual expoe `proximo_sync` de forma global e nao um cron materializado por capability;
- `healthStatus` continua sendo primariamente de integracao, nao um health isolado por capability;
- o sync completo `completo` continua como acao provider-specific fora do view model de capability, o que deve ser refinado na fase seguinte sem criar runtime paralelo.

## 19. Recomendacao para ERP-UX-03B

Prosseguir para o Capability Center reutilizando diretamente:

- `ErpCapabilityViewModel`
- `buildErpCapabilityViewModels`
- `capability-labels.ts`

Escopo recomendado de ERP-UX-03B:

- substituir a tabela atual por cards/listagem operacional baseados no view model;
- exibir status, forma de atualizacao, sistema responsavel, ultima execucao e pendencias por capability;
- manter o `SankhyaConsole` como unico fornecedor de acoes manuais provider-specific;
- nao criar endpoint agregado novo.
