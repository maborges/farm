# ERP-UX-03C - Capability Details do Console Operacional de Integracoes ERP

Data da execucao: 2026-07-12

## 1. Resumo

Esta fase evoluiu o painel lateral do Capability Center para um `Capability Details` operacional, sem criar rota nova, sem criar API nova e sem alterar backend.

O painel agora mostra, por capability selecionada:

- resumo operacional;
- ownership e limite operacional;
- direcao e forma de atualizacao;
- provider e executor sanitizados;
- health geral aplicavel;
- ultima sincronizacao, ultima execucao e proxima atualizacao prevista;
- jobs recentes relacionados ou gerais;
- timeline relacionada ou geral identificada como geral;
- pendencias e conflitos de associacao;
- operacoes internas sanitizadas;
- acoes realmente suportadas.

Resultado:

- a composicao continua puramente frontend;
- a correlacao de jobs e timeline ficou centralizada em view model dedicado;
- jobs globais nao sao atribuídos falsamente a uma capability;
- `sync completo` continua fora das capabilities;
- `reprocessamento` continua ausente;
- `pedidos` e `estoque` continuam P2 sem acoes.

## 2. Auditoria pre-codigo

Evidencias confirmadas antes das alteracoes:

- o `Sheet` do detalhe ainda estava dentro de `capability-card.tsx`, com conteudo minimo e responsabilidade misturada;
- o `DynamicErpConsole` ja carregava `status`, `health`, `jobs`, `timeline`, `diagnosis` e `pendingAssociations` antes do render;
- a correlacao segura disponivel para jobs, timeline e associacoes e `feature_code`;
- `IntegrationJob` ja chegava ao frontend como `ErpJob` com `feature_code`, `job_status`, `trigger_type`, `started_at` e `finished_at`;
- a timeline ja chegava ao frontend como `ErpTimelineItem` com `feature_code`, `status`, `resumo`, `occurred_at`, `processados` e `duracao_ms`;
- as associacoes pendentes ja chegavam como `ExternalAssociationPendingItem` com `feature_code`, `status`, `external_id`, `external_key` e `motivo`;
- havia componente reutilizavel de timeline em `sankhya-timeline.tsx`;
- havia componentes reutilizaveis de `Sheet`, `Accordion`, `Badge`, `Button`, `Separator`, `Card` e estados vazios.

Limitacoes confirmadas:

- o runtime nao garante health individual por capability;
- `nextRunAt` pode representar agenda compartilhada;
- jobs sem `feature_code` nao podem ser promovidos a exclusivos da capability;
- timeline sem `feature_code` deve permanecer claramente geral.

## 3. Componentes reutilizados

- `Sheet`
- `Accordion`
- `Badge`
- `Button`
- `Separator`
- `Card`
- `ErpTimeline`
- `ErpCapabilityStatusBadge`
- `ErpCapabilityMaturityBadge`
- `ErpCapabilityHealthBadge`
- `ErpCapabilitySyncModeBadge`

## 4. Componentes criados

- `apps/web/src/components/integracoes/erp/capability-details.tsx`

## 5. View models criados

- `ErpCapabilityDetailsViewModel`
- `ErpCapabilityJobViewModel`
- `ErpCapabilityTimelineItemViewModel`
- `ErpCapabilityAssociationItemViewModel`
- `ErpCapabilityAssociationSummaryViewModel`
- `BuildErpCapabilityDetailsInput`
- `buildErpCapabilityDetailsViewModels(...)`

Todos permanecem em `apps/web/src/components/integracoes/erp/types.ts` e `apps/web/src/components/integracoes/erp/capability-details-view-model.ts`.

## 6. Estrategia de correlacao

### Jobs

Regra adotada:

- `feature_code === capability.code` -> job relacionado;
- `feature_code` ausente -> job geral da integracao;
- nenhuma correlacao por texto livre, resumo ou semelhanca nominal.

Apresentacao:

- jobs relacionados aparecem na secao principal;
- jobs gerais aparecem em bloco separado com o rotulo `Execucoes gerais da integracao`;
- quando nao ha job relacionado, o painel informa `Nenhuma execucao relacionada foi encontrada.`

### Timeline

Regra adotada:

- `feature_code === capability.code` -> evento relacionado;
- `feature_code` ausente -> timeline geral da integracao;
- sem `feature_code`, nenhum item e promovido a capability exclusiva.

Apresentacao:

- a `ErpTimeline` existente foi reutilizada;
- quando nao ha timeline relacionada, mas ha timeline geral, o painel informa explicitamente que esta exibindo timeline geral;
- quando nao ha eventos aplicaveis, o painel mostra `Ainda nao ha eventos relacionados a este recurso.`

### Associacoes

Regra adotada:

- apenas `ExternalRecordAssociation`, projetado no frontend como `ExternalAssociationPendingItem`;
- `feature_code === capability.code` define associacao relacionada;
- referencias externas sao sanitizadas por mascaramento parcial;
- a secao mostra apenas resumo e amostra curta, sem editor nem novo fluxo.

## 7. Limitacoes de correlacao

- jobs globais continuam globais mesmo quando o tipo de operacao sugere afinidade com uma capability;
- eventos de timeline sem `feature_code` nao sao redistribuidos por inferencia;
- a contagem de `pendingAssociations` continua vindo do view model operacional e os itens detalhados usam apenas a amostra ja carregada;
- health continua geral da integracao, nao health por capability.

## 8. Estrutura visual

O painel foi reorganizado em secoes:

1. resumo operacional com badges;
2. descricao e limite operacional;
3. ownership, direcao, modo e executor;
4. datas de execucao;
5. acoes disponiveis;
6. jobs recentes;
7. timeline;
8. associacoes;
9. informacoes tecnicas sanitizadas em `Accordion`.

O `ErpCapabilityCard` manteve apenas a responsabilidade de abrir o `Sheet`. A composicao do detalhe foi movida para `ErpCapabilityDetails`.

## 9. Ownership por capability

Os textos de ownership e limite operacional foram centralizados no catalogo operacional em `capability-labels.ts`.

Cobertura:

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`
- `estoque`

Exemplos efetivos:

- `financeiro` explicita separacao entre financeiro administrativo do ERP e financeiro operacional do AgroSaaS;
- `estoque` explicita que a capability se refere ao estoque administrativo e que o estoque operacional continua no AgroSaaS;
- `pedidos` continua descrita como capability planejada sem operacao ativa no piloto.

## 10. Tratamento de provider

- `provider` principal exibido: `Sankhya`;
- `executor` exibido: `Conector Sankhya` ou rotulo sanitizado equivalente;
- o nome da classe `SankhyaCanonicalAdapter` nao e exibido;
- path de codigo, modulo Python, URL integral, credencial, token e payload bruto nao sao exibidos.

## 11. Operacoes internas

Fonte:

- `technical.internalOperationLabels` do `ErpCapabilityViewModel`;
- fallback para `technicalOperations` do catalogo operacional.

Exemplos exibiveis:

- `Importacao de pessoas`
- `Importacao de produtos`
- `Consulta de documentos fiscais`
- `Importacao financeira`

Nao houve exposicao de endpoint literal nesta fase.

## 12. Jobs

Campos exibidos quando disponiveis:

- status;
- relacao (`Relacionada` ou `Geral`);
- trigger;
- inicio;
- conclusao;
- duracao;
- processados;
- sucessos;
- erros.

Nao sao exibidos:

- stack trace;
- payload bruto;
- cabecalhos;
- credenciais;
- tokens.

## 13. Timeline

- a secao reutiliza `ErpTimeline`;
- a rotulacao deixa claro quando os eventos sao gerais da integracao;
- nao ha segunda timeline concorrente;
- o painel nao fabrica timeline por capability.

## 14. Associacoes

O painel exibe:

- quantidade de pendencias;
- quantidade de conflitos;
- lista resumida de itens relacionados;
- tipo da entidade;
- referencia externa mascarada;
- status;
- motivo sanitizado;
- atalho para a secao existente de associacoes.

Fora de escopo:

- filtros avancados;
- paginacao;
- editor;
- exclusao;
- reconciliacao inline;
- reprocessamento.

## 15. Health

Tratamento adotado:

- a secao usa o texto `Situacao geral do conector`;
- o detalhe mostra o label operacional do health geral;
- a descricao deixa explicito que a capability pode ter limitacoes proprias mesmo com integracao saudavel;
- nao foi criado health artificial por capability.

## 16. Proxima execucao

Tratamento adotado:

- o campo e apresentado como `Proxima atualizacao prevista`;
- quando presente, o painel explica que a agenda pode ser compartilhada pela integracao;
- o componente nao recalcula scheduler;
- P2 sem agenda continua sem promessa operacional.

## 17. Acoes

Regras implementadas:

- `canSyncManually` -> exibe sincronizacao manual;
- `canConfigure` -> navega para a area atual de configuracao;
- `canReconcile` -> navega para a area atual de associacoes;
- `canReprocess` -> nunca exibido;
- `sync completo` -> continua fora da capability.

## 18. P2

### Pedidos

- continua `Planejada`;
- sem sync manual;
- sem reprocessamento;
- sem secao falsa de operacao ativa.

### Estoque

- continua `Planejada`;
- explicita limite entre estoque administrativo e operacional;
- sem acoes;
- sem ativacao de evento, outbox ou endpoint;
- sem promessa adicional para o piloto.

## 19. Estados

Cobertura no painel:

- sem jobs relacionados;
- sem timeline relacionada;
- sem associacoes;
- resposta parcial com `Nao informado`;
- capability P2 sem acoes;
- health geral ausente sem transformar em falso erro.

## 20. Acessibilidade

Validacoes cobertas:

- titulo acessivel do detalhe por capability;
- acoes com `aria-label`;
- badges com texto, nao apenas cor;
- headings em ordem logica;
- secao tecnica recolhivel com `Accordion`;
- mensagens de vazio compreensiveis;
- conteudo rolavel dentro do `Sheet`.

## 21. Arquivos alterados

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/erp/capability-labels.ts`
- `apps/web/src/components/integracoes/erp/capability-center.tsx`
- `apps/web/src/components/integracoes/erp/capability-card.tsx`
- `apps/web/src/components/integracoes/erp/capability-details.tsx`
- `apps/web/src/components/integracoes/erp/capability-details-view-model.ts`
- `apps/web/src/components/integracoes/erp/types.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details.test.tsx`

## 22. Testes

Testes criados:

- `apps/web/tests/unit/integracoes/erp-capability-details-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details.test.tsx`

Suites reexecutadas:

- `apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-center.test.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-details-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details.test.tsx`

Cobertura validada:

- details de capability ativa;
- details de capability parcial ou com resposta parcial;
- capability P2;
- limite operacional de estoque;
- ownership de financeiro;
- provider sanitizado;
- ausencia do nome da classe adapter;
- operacoes internas sanitizadas;
- jobs relacionados por `feature_code`;
- job geral nao atribuido falsamente;
- timeline relacionada;
- timeline geral identificada corretamente;
- associacoes pendentes e conflitos;
- ausencia de associacoes;
- ausencia de jobs;
- ausencia de timeline;
- health geral identificado como geral;
- proxima execucao como previsao compartilhada;
- sync manual disponivel;
- sync manual indisponivel;
- sync completo ausente;
- reprocessamento ausente;
- acessibilidade basica do painel.

## 23. Comandos executados

Validacao principal:

```bash
cd apps/web
npm run typecheck
npm run lint
```

Compilacao de testes com `tsconfig` temporario:

```bash
cd apps/web
./node_modules/.bin/tsc -p /tmp/erp-ux-03c-tests.tsconfig.json
```

Execucao dos testes:

```bash
node --test \
  /tmp/erp-ux-03c-tests/tests/unit/integracoes/erp-capability-view-model.test.js \
  /tmp/erp-ux-03c-tests/tests/unit/integracoes/erp-capability-center.test.js \
  /tmp/erp-ux-03c-tests/tests/unit/integracoes/erp-capability-details-view-model.test.js \
  /tmp/erp-ux-03c-tests/tests/unit/integracoes/erp-capability-details.test.js
```

Diff:

```bash
git diff --check
git -C apps/web diff --check
```

Build global:

```bash
cd apps/web
rm -rf .next
rm -f tsconfig.tsbuildinfo
timeout 90s npm run build
```

## 24. Resultados

- `npm run typecheck`: passou
- `npm run lint`: passou
- testes 03A + 03B + 03C: 4 suites executadas, 4 passaram
- `git diff --check`: passou
- `git -C apps/web diff --check`: passou

## 25. Recorrencia ou nao da ressalva de build

A ressalva externa foi recorrente.

Resultado observado nesta fase:

- `npm run build` voltou a parar em `Creating an optimized production build ...` e terminou novamente com:

```text
Build failed because of webpack errors
```

Nao surgiu stack, modulo ou erro novo relacionado aos arquivos alterados em 03C.

Classificacao mantida:

- recorrencia da ressalva externa aceita em `ERP-UX-03B1-DIAGNOSTICO-FECHAMENTO-BUILD.md`

## 26. Riscos

- o build global completo do `apps/web` continua com falha externa sem diagnostico detalhado;
- a qualidade da correlacao continua dependente da presenca de `feature_code` no runtime;
- capabilities sem `feature_code` em jobs ou timeline continuarao aparecendo apenas com visao geral.

## 27. Confirmacao de escopo

Confirmado:

- nenhum backend foi alterado;
- nenhum router, service, schema Python, model, migration, adapter ou runtime ERP foi alterado;
- nenhuma capability nova foi criada;
- nenhuma rota nova foi criada;
- nenhum endpoint agregado foi criado;
- nenhum fluxo de reprocessamento foi criado;
- `sync completo` permaneceu fora das capabilities;
- `estoque` P2 permaneceu protegido;
- `IAM`, `Wizard`, `Backoffice`, `Sankhya Gateway`, eventos e outbox nao foram alterados.

## 28. Recomendacao para ERP-UX-03D

Proxima fase recomendada: `ERP-UX-03D - Association Center`.

Direcao objetiva:

1. reutilizar `ExternalRecordAssociation` como unica fonte;
2. promover a secao atual de associacoes para experiencia operacional dedicada;
3. reaproveitar o mesmo contrato operacional e os atalhos ja expostos nos detalhes da capability;
4. manter reconciliacao, filtros e estados vazios dentro do console oficial, sem criar fluxo paralelo;
5. preservar a separacao entre UX operacional do Tenant e observabilidade tecnica do Backoffice.

## 29. Veredicto

`GO COM RESSALVA EXTERNA`

Justificativa:

- o Capability Details foi implementado no console oficial;
- a composicao continua tipada e pura;
- as correlacoes usam campos estruturados reais;
- os testes especificos passaram;
- `typecheck` e `lint` passaram;
- o `build` global repetiu apenas a ressalva externa ja comprovada em fase anterior, sem novo erro introduzido por 03C.
