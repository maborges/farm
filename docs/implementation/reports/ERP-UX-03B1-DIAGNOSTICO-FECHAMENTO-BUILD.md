# ERP-UX-03B.1 - Diagnostico e Fechamento do Build do Console ERP

Data da execucao: 2026-07-12

## 1. Resumo executivo

O erro de build nao foi introduzido pela fase `ERP-UX-03B`.

Foi reproduzido no baseline limpo do repositório `apps/web`, sem as alteracoes do Capability Center, usando o mesmo conjunto de dependencias locais. Os arquivos da fase continuam tipando corretamente, `lint` continua passando, os testes do view model e do Capability Center continuam passando, e o build seletivo do caminho do console ERP compila com sucesso.

Conclusao:

- classificacao: `preexistente`, com componente `ambiental/infra do build webpack`
- veredicto final: `GO COM RESSALVA EXTERNA`

## 2. Estado inicial

Estado de entrada:

- Capability Center implementado e funcional;
- `typecheck`, `lint`, testes e `diff --check` ja haviam passado na fase 03B;
- `npm run build` falhava com a mensagem generica:

```text
Build failed because of webpack errors
```

## 3. Codigo de saida inicial

Build inicial observado nesta etapa:

- comando: `cd apps/web && rm -rf .next && rm -f tsconfig.tsbuildinfo && npm run build`
- codigo de saida observado: `1`

## 4. Log relevante do build

O log integral capturado em `/tmp/erp-ux-03b-build.log` teve apenas 10 linhas e nao trouxe stack ou modulo causador:

```text
> build
> next build --webpack

▲ Next.js 16.1.6 (webpack)
- Environments: .env.local, .env

  Creating an optimized production build ...

> Build failed because of webpack errors
```

O mesmo padrao foi reproduzido no baseline limpo.

## 5. Causa raiz

Causa raiz identificada no escopo possivel desta etapa:

- o erro e um colapso generico do pipeline `next build --webpack` no ambiente atual;
- ele ocorre tambem no baseline limpo do repositorio `apps/web`, sem o Capability Center;
- o build nao expõe stack, modulo, import ou arquivo causador nem com captura completa nem com `--debug`;
- o aumento de memoria com `NODE_OPTIONS=\"--max-old-space-size=4096\"` nao mudou o comportamento observavel;
- os arquivos alterados pela fase 03B permanecem compilando, tipando e testando corretamente fora do build global completo.

Em termos praticos:

- a causa nao foi localizada dentro dos arquivos da fase;
- a falha observada e externa ao escopo do Capability Center ou ja preexistia no baseline atual do `apps/web`.

## 6. Classificacao

- `preexistente`

Observacao:

- tambem existem sinais de limitacao ambiental do pipeline webpack, porque o erro global nao expõe diagnostico util e alguns comandos com `timeout` ficaram presos em `Creating an optimized production build ...`.
- ainda assim, como o baseline limpo falha igual, a classificacao principal registrada e `preexistente`.

## 7. Arquivos analisados

Arquivos da fase auditados:

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/erp/capability-labels.ts`
- `apps/web/src/components/integracoes/erp/capability-center.tsx`
- `apps/web/src/components/integracoes/erp/capability-card.tsx`
- `apps/web/src/components/integracoes/erp/capability-status-badge.tsx`

Configuracao analisada:

- `apps/web/tsconfig.json`
- `apps/web/next.config.ts`

## 8. Alteracoes realizadas

Nenhuma correcao de codigo produtivo foi necessaria nesta etapa.

Apenas foi restaurado o artefato incidental:

- `apps/web/next-env.d.ts`

Esse arquivo foi tocado pelo `next build`, mas foi revertido ao estado anterior da fase.

## 9. Alteracoes temporarias revertidas

Nao houve alteracao temporaria persistente em codigo produtivo.

As tecnicas temporarias usadas durante diagnostico ficaram restritas a:

- limpeza de `.next`
- limpeza de `tsconfig.tsbuildinfo`
- logs em `/tmp`
- baseline copiado para `/tmp`
- `tsconfig` temporario em `/tmp`
- execucao seletiva de build

Nenhuma delas permaneceu no projeto.

## 10. Comparacao com baseline

Como `apps/web` e um repositório aninhado, o baseline correto foi extraido com:

```bash
git -C apps/web archive HEAD | tar -x -C /tmp/apps-web-baseline
ln -s /opt/lampp/htdocs/farm/apps/web/node_modules /tmp/apps-web-baseline/node_modules
cd /tmp/apps-web-baseline
npm run build
```

## 11. Resultado do build no baseline

Resultado no baseline limpo:

- codigo de saida: `1`
- log:

```text
> build
> next build --webpack

▲ Next.js 16.1.6 (webpack)
- Environments: .env

  Creating an optimized production build ...

> Build failed because of webpack errors
```

Isso comprova que o erro ja existia sem as alteracoes da fase 03B.

## 12. Resultado do build final

Resultado do build no workspace atual:

- comportamento observado 1: falha rapida com `Build failed because of webpack errors`
- comportamento observado 2: em execucao com `timeout`, o processo permaneceu preso em `Creating an optimized production build ...` ate `exit_code=124`

Diagnostico final para o build:

- o build global completo permanece nao-confiavel neste ambiente;
- nao foi encontrada evidencia de que os arquivos da fase 03B sejam a causa.

## 13. Resultado do typecheck

- `cd apps/web && npm run typecheck`
- resultado observado nesta execucao: passou

## 14. Resultado do lint

- `cd apps/web && npm run lint`
- resultado observado nesta execucao: passou

## 15. Resultado dos testes

Testes executados nesta etapa:

- `ErpCapabilityViewModel`
- `ErpCapabilityCenter`

Estrategia utilizada:

- o comando sugerido com `tsc -p apps/web/tsconfig.json` nao emite os testes porque o `tsconfig` oficial exclui `tests/`;
- por isso foi usado um `tsconfig` temporario em `/tmp`, estendendo o oficial e incluindo apenas:
  - `src/components/integracoes/erp/**`
  - `tests/unit/integracoes/erp-capability-view-model.test.ts`
  - `tests/unit/integracoes/erp-capability-center.test.tsx`

Resultado:

- 2 testes executados
- 2 testes passaram

## 16. Resultado do `git diff --check`

- `git diff --check`: passou
- `git -C apps/web diff --check`: passou

## 17. Riscos

- o build global do `apps/web` continua sem diagnostico util do webpack;
- portanto ainda existe risco externo no pipeline de producao local desta workspace;
- esse risco nao esta concentrado nos arquivos do Capability Center, mas ainda precisa ser conhecido antes de ampliar escopo visual em fases futuras.

## 18. Limitacoes

- `git worktree` nao pôde ser usado por restricao de escrita em `.git/worktrees`;
- a comparacao precisou usar copia isolada em `/tmp`;
- o build do Next nao expôs stack nem modulo causador, mesmo com captura integral e `--debug`;
- o `tsconfig` oficial do app exclui `tests/`, o que exigiu `tsconfig` temporario para repetir os testes.

## 19. Confirmacao de preservacao do escopo

Confirmado:

- Capability Center permanece presente;
- Pessoas, Produtos, Financeiro, NFe, Pedidos e Estoque permanecem listados pelo view model;
- sync manual continua apenas para Pessoas e Produtos;
- sync completo continua fora dos cards;
- reprocessamento continua ausente;
- Estoque P2 continua sem acoes e com separacao administrativa/operacional;
- painel lateral de detalhes permanece;
- navegacao para configuracao e associacoes permanece;
- nenhum backend foi alterado;
- nenhum runtime ERP foi alterado;
- nenhum adapter, capability, IAM, Wizard ou fluxo de estoque P2 foi alterado.

## 20. Veredicto final

- `GO COM RESSALVA EXTERNA`

Motivo:

- o baseline limpo do `apps/web` falha do mesmo jeito;
- os arquivos da fase 03B continuam tipando e testando corretamente;
- nao ha evidencia concreta de regressao introduzida pelo Capability Center;
- o bloqueio restante e do build webpack global do projeto/ambiente atual, nao da fase entregue.
