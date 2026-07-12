# ERP-UX-03B - Capability Center do Console ERP

Data da execucao: 2026-07-12

## 1. Resumo

Esta fase substituiu a tabela operacional anterior por um Capability Center responsivo dentro do `DynamicErpConsole`, usando exclusivamente o `ErpCapabilityViewModel` e a composicao centralizada de `buildErpCapabilityViewModels(...)`.

O resultado foi:

- o Capability Center virou a principal visao operacional do console do Tenant;
- sync manual por capability passou a aparecer somente quando o wrapper provider-specific o declara;
- a sincronizacao completa `completo` foi mantida como acao geral da integracao, fora dos cards;
- P2 continuou protegido para `pedidos` e `estoque`;
- nenhum backend, runtime, adapter ou contrato HTTP foi alterado.

## 2. Auditoria pre-codigo

Evidencias confirmadas antes da implementacao:

- a tabela atual de capabilities estava em `apps/web/src/components/integracoes/erp-console.tsx`;
- o projeto ja oferecia `Card`, `Badge`, `Button`, `Sheet`, `Tooltip`, `Skeleton` e `EmptyState`;
- o projeto ja usava grids de cards responsivos em modulos compartilhados como `StatCard`;
- o `DynamicErpConsole` ja carregava todos os dados necessarios antes do render;
- a logica de P2, status, maturidade, direcao, acoes e pendencias ja estava centralizada no view model criado na fase 03A;
- a tabela antiga podia ser substituida sem perder equivalencia funcional porque o view model ja expunha:
  - nome
  - descricao
  - status
  - maturidade
  - direcao
  - master system
  - modo
  - health
  - pendencias
  - acoes

## 3. Componentes reutilizados

- `Card`
- `Badge`
- `Button`
- `Alert`
- `Sheet`
- `Tooltip`
- `Skeleton`
- `EmptyState`
- `StatCard`

## 4. Componentes criados

- `apps/web/src/components/integracoes/erp/capability-center.tsx`
- `apps/web/src/components/integracoes/erp/capability-card.tsx`
- `apps/web/src/components/integracoes/erp/capability-status-badge.tsx`

## 5. Estrutura visual adotada

Ordem final do console:

1. resumo da conexao
2. readiness do piloto
3. Capability Center
4. health e regras da integracao
5. configuracao
6. sincronizacao geral
7. diagnostico operacional
8. associacoes pendentes
9. jobs, historico e timeline

O Capability Center usa:

- cabecalho com explicacao curta;
- cards de resumo;
- alerta semantico sobre health global;
- grid responsivo de cards por capability;
- painel lateral de detalhes sem criar nova rota.

## 6. Campos apresentados

Cada card exibe:

- nome
- descricao
- status operacional
- maturidade
- health da integracao
- sistema responsavel
- sentido da atualizacao
- forma de atualizacao
- situacao da integracao
- ultima execucao
- ultima atualizacao
- proxima atualizacao prevista
- pendencias e conflitos de associacao
- acoes disponiveis

## 7. Rotulos operacionais

Os rotulos foram centralizados em `capability-labels.ts` para:

- `ErpCapabilityOperationalStatus`
- `ErpSyncDirection`
- `ErpSyncMode`
- `ErpCapabilityMaturity`
- health global da integracao

Exemplos aplicados:

- `ACTIVE` -> `Ativa`
- `PARTIAL` -> `Parcialmente disponível`
- `DECLARED` -> `Planejada`
- `ERP_TO_AGROSAAS` -> `ERP para AgroSaaS`
- `NOT_CONFIGURED` -> `Não configurada`
- `CONNECTED` -> `Conector saudável`

## 8. Regras de acoes

As acoes respeitam apenas o view model:

- `canViewDetails`: abre sheet lateral com os dados ja disponiveis;
- `canSyncManually`: mostra botao somente para capabilities materializadas com acao real do wrapper;
- `canConfigure`: leva para a area de configuracao no proprio console;
- `canReconcile`: leva para a secao de associacoes pendentes;
- `canReprocess`: nao renderiza acao.

Para Sankhya, nesta fase:

- `pessoas` pode sincronizar manualmente;
- `produtos` pode sincronizar manualmente;
- `financeiro`, `nfe`, `pedidos` e `estoque` nao recebem sync manual por inferencia.

## 9. Tratamento de health global

- o card usa a linguagem `Situação geral da integração`;
- o badge de health nao afirma monitoramento individual por capability;
- o mesmo health pode aparecer em multiplas capabilities, mas a interface deixa isso explicito com alerta no topo do center.

## 10. Tratamento de proxima execucao

- o campo aparece como `Próxima atualização prevista`;
- o tooltip explica que a agenda pode ser compartilhada pela integracao;
- o texto nao promete agenda exclusiva por capability.

## 11. Tratamento de P2

### Pedidos

- continua `Planejada`;
- sem sync manual;
- sem reprocessamento;
- com detalhes apenas no painel lateral.

### Estoque

- continua `Planejada`;
- o texto explicita estoque administrativo do ERP;
- o texto tambem deixa claro que o estoque operacional continua no AgroSaaS;
- nenhuma acao operacional foi exibida;
- nenhum evento, outbox ou endpoint foi criado.

## 12. Tratamento de estados

- `loading`: skeletons do proprio center;
- `error`: `EmptyState` com retry e atalho para configuracao;
- `sem configuracao`: CTA para a configuracao existente;
- `sem capabilities`: estado defensivo sem fallback inventado;
- `resposta parcial`: usa `Não informado` para datas ausentes.

## 13. Responsividade

- cards de resumo em grid `sm` e `xl`;
- cards de capability em grid de uma ou duas colunas;
- sem tabela larga no mobile;
- detalhes tecnicos em `Sheet` lateral;
- botoes quebram linha em telas menores.

## 14. Acessibilidade

- badges principais receberam `aria-label`;
- botoes de sync e navegacao usam nomes explicitos;
- o tooltip nao e a unica fonte de informacao sobre agenda;
- a configuracao e associacoes podem ser acessadas por ancora textual e foco programatico;
- o Capability Center mantem ordem de leitura logica.

## 15. Arquivos alterados

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/erp/capability-labels.ts`
- `apps/web/src/components/integracoes/erp/capability-center.tsx`
- `apps/web/src/components/integracoes/erp/capability-card.tsx`
- `apps/web/src/components/integracoes/erp/capability-status-badge.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-center.test.tsx`
- `docs/implementation/reports/ERP-UX-03B-CAPABILITY-CENTER.md`

## 16. Testes criados

- `apps/web/tests/unit/integracoes/erp-capability-center.test.tsx`

Cobertura registrada:

- capability ativa
- capability parcial
- capability desabilitada
- capability declarada/P2
- estoque com separacao administrativo vs operacional
- pendencias
- sync manual presente
- sync manual ausente
- reprocessamento ausente
- sync completo ausente do card
- resposta parcial
- loading
- erro
- ausencia de capabilities
- ausencia de cards para clientes/fornecedores
- ausencia de comercializacao
- navegacao para associacoes
- acessibilidade basica

## 17. Comandos executados

```bash
cd apps/web
npm run typecheck
npm run lint
npm run build
```

Compilacao e execucao dos testes unitarios:

```bash
apps/web/node_modules/.bin/tsc -p apps/web/tsconfig.json --noEmit false --outDir /tmp/erp-ux-03b-tests
node --test /tmp/erp-ux-03b-tests/tests/unit/integracoes/erp-capability-view-model.test.js /tmp/erp-ux-03b-tests/tests/unit/integracoes/erp-capability-center.test.js
```

Validacao de patch:

```bash
git diff --check
git -C apps/web diff --check
```

Tentativas adicionais para isolar o build:

```bash
npx next build --webpack --debug
npx next build --webpack --debug-build-paths "src/app/**/settings/integracoes/erp/page.tsx"
```

## 18. Resultados

- `npm run typecheck`: passou
- `npm run lint`: passou
- testes unitarios do view model e do Capability Center: passaram
- `git diff --check`: passou
- `git -C apps/web diff --check`: passou
- `npm run build`: falhou com a saida generica `Build failed because of webpack errors`

## 19. Limitacoes

- o `apps/web` continua sem runner dedicado para teste unitario de componentes React;
- os testes desta fase foram compilados com `tsc` do app e executados em Node sobre HTML estatico;
- o build completo do Next nao exibiu stack ou modulo causador do erro, mesmo com `--debug`;
- a tentativa com `--debug-build-paths` nao reproduziu a rota especifica do console ERP de forma util, portanto o erro global do build nao pode ser atribuido com precisao por este ambiente.

## 20. Riscos

- o painel lateral de detalhes ainda e uma antecipaçao minima do futuro `Capability Details`, sem timeline detalhada ou jobs por capability;
- o health ainda e semanticamente global;
- `nextRunAt` continua sendo inferido a partir da integracao atual, nao de um scheduler por capability.

## 21. Evidencias de que nenhum backend foi alterado

Todos os arquivos alterados nesta fase estao sob:

- `apps/web/src/components/integracoes/`
- `apps/web/tests/unit/`
- `docs/implementation/reports/`

Nenhum arquivo em:

- `services/api/`
- `services/api/integracoes/`
- models
- routers
- services
- schemas Python

foi modificado.

## 22. Recomendacao para ERP-UX-03C

Prosseguir para `Capability Details` reaproveitando:

- `ErpCapabilityCenter`
- `ErpCapabilityCard`
- `ErpCapabilityStatusBadge`
- `ErpCapabilityViewModel`

Escopo recomendado:

- aprofundar o painel lateral atual para virar a base de `Capability Details`;
- incluir timeline, jobs recentes, endpoints internos sanitizados e pendencias no detalhe;
- manter o mesmo view model, sem criar contrato de runtime paralelo.
