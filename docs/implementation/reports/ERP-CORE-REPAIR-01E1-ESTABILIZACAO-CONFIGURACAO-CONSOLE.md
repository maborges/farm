# ERP-CORE-REPAIR-01E1 — Estabilização da Configuração do Console ERP

## 1. Estado retomado

Ao retomar a fase, o repositório raiz estava com:

- `apps/web` marcado como subprojeto sujo;
- dois relatórios novos já presentes e **preexistentes** a esta fase:
  - `docs/implementation/reports/ERP-ARCH-REASSESSMENT-01-AUDITORIA-DEFINITIVA-MULTIPROVIDER.md`
  - `docs/implementation/reports/ERP-ARCH-REASSESSMENT-01B-AUDITORIA-CONSOLE-CONFIGURACAO-MAPEAMENTOS-APIS.md`

No subprojeto `apps/web`, o estado retomado continha alterações em andamento apenas no frontend do console ERP.

## 2. Diff revisado

### 2.1 Comandos executados

```bash
git status --short
git diff --stat
git diff

git -C apps/web status --short
git -C apps/web diff --stat
git -C apps/web diff
```

### 2.2 Alterações da fase

Arquivos alterados da fase em `apps/web`:

- `playwright.unit.config.ts`
- `src/components/integracoes/erp-console.tsx`
- `src/components/integracoes/erp/provider-config-payload.ts`
- `src/components/integracoes/erp/provider-config-payload.test.ts`
- `src/components/integracoes/erp/types.ts`

Arquivos novos da fase em `apps/web`:

- `src/components/integracoes/erp/configuration-section.tsx`
- `src/components/integracoes/erp/configuration-section.test.ts`
- `src/components/integracoes/erp/provider-config-fields.ts`
- `src/components/integracoes/erp/provider-config-fields.test.ts`
- `src/components/integracoes/erp/provider-console-endpoints.ts`
- `src/components/integracoes/erp/provider-console-endpoints.test.ts`
- `tests/e2e/erp-console-configuracao.spec.ts`

### 2.3 Mudanças preexistentes

- os dois relatórios `ERP-ARCH-REASSESSMENT-01*` no repositório raiz;
- nenhum backend em diff local;
- nenhum arquivo de wizard, IAM, billing, models ou migrations entrou nesta fase.

### 2.4 Alterações não relacionadas

Não foi encontrada alteração funcional fora do escopo no frontend desta fase.

## 3. Guardrails da revisão

Confirmado por inspeção do diff da fase:

- nenhuma nova página de configuração foi criada;
- nenhum fluxo paralelo foi introduzido;
- nenhum novo endpoint backend foi criado;
- nenhuma alteração foi feita no Wizard;
- nenhuma alteração foi feita em IAM;
- nenhuma alteração foi feita em billing;
- nenhuma alteração foi feita em models ou migrations;
- nenhuma ativação de Estoque/Pedidos P2 foi introduzida;
- nenhum início antecipado de contrato multiprovider foi feito;
- nenhum backend foi alterado.

Observação importante:

- o componente genérico continua exibindo alguns cards-resumo ainda com campos `sankhya_*`, mas isso **já era limitação prévia do console** e não foi introduzido por esta fase. Esta fase não expandiu esse acoplamento.

## 4. Problemas encontrados no code review

Foram encontrados três desvios reais da fase:

1. `sync_interval=0` persistido no backend era reidratado no formulário como `15`, o que quebrava a simetria de reload e poderia reenviar `900`.
2. Havia uso de `as unknown` em leitura dinâmica de config, reprovado pelo gate de revisão.
3. A cobertura E2E estava incompleta para `403`, `500 + retry` e preservação de valores já carregados.

## 5. Correções realizadas

- adicionado índice dinâmico em `ErpConsoleConfig` para remover `as unknown`;
- corrigida a normalização de `sync_interval` para preservar `0` na carga do formulário;
- mantida a conversão explícita minutos → segundos apenas no payload;
- ampliados testes unitários para `loading`, `schema 403`, `config 500`, `sync_interval=0` e ausência de multiplicação repetida;
- ampliada a spec E2E da configuração para `404 inicial`, `schema 500 + retry`, `config 403`, `config 500 + retry preservando valores`, `integração conectada + save`.

## 6. Componentes extraídos

Componentes/utilitários extraídos e mantidos:

- `configuration-section.tsx`
- `provider-config-fields.ts`
- `provider-console-endpoints.ts`

Resultado:

- `erp-console.tsx` ficou menor, mais legível e voltou a delegar a UI de configuração para um componente dedicado.

## 7. Tratamento do schema

Implementado em `configuration-section.tsx` com estado explícito:

- `loading`: mensagem visível, sem render prematuro do formulário;
- `error` e `not_found`: alerta visível + botão `Tentar novamente`;
- `forbidden`: mensagem específica de permissão;
- `empty`: mensagem explícita de provider sem campos editáveis.

Conclusão:

- o card não fica vazio silenciosamente;
- falha de schema não derruba as demais áreas do console.

## 8. Tratamento da config

Implementado no `loadConsole` do `erp-console.tsx`:

- `404`: primeira configuração, com formulário liberado;
- `403`: mensagem específica, sem tratar como inexistente;
- `500/rede`: mensagem específica e preservação do último `configState.data` carregado;
- `retry`: reexecuta `loadConsole`.

Conclusão:

- `403`, `404` e `500/rede` agora têm comportamento distinto;
- `500/rede` não apaga valores já carregados.

## 9. Comportamento 404

### Status 404

- `ErpConsole` continua exibindo `ErpProviderSelector`.

### Config 404

- a seção mostra mensagem de primeira configuração;
- o formulário é exibido quando o schema existe.

## 10. Comportamento 403

- `schema 403`: impede edição e mostra erro de permissão;
- `config 403`: mantém o formulário visível quando o schema carregou, mas informa que a configuração não pode ser acessada.

## 11. Comportamento 500/rede

- `schema 500/rede`: alerta explícito com `Tentar novamente`;
- `config 500/rede`: alerta explícito com `Tentar novamente`, preservando valores anteriores quando já existiam.

## 12. Retry

Validado:

- retry de schema via botão `Tentar novamente`;
- retry de config via botão `Tentar novamente`.

## 13. Endpoints GET/POST/teste

Contrato separado mantido em `provider-console-endpoints.ts`:

- `getConfig`
- `saveConfig`
- `testConnection`

No `erp-console.tsx`:

- GET usa `resolvedEndpoints.getConfig`;
- POST usa `resolvedEndpoints.saveConfig`;
- teste usa `resolvedEndpoints.testConnection`.

No `SankhyaConsole`:

- as rotas reais continuam sendo fornecidas pelo wrapper provider-specific.

Cobertura:

- unit test criado para `getConfig !== saveConfig`;
- E2E validou GET e POST reais do console Sankhya.

Limitação consciente:

- o cenário E2E com endpoints distintos **não foi representado no tenant route real**, porque o wrapper Sankhya atual usa a mesma rota real para leitura/escrita e criar página paralela de teste violaria os guardrails da fase.

## 14. Fields editáveis

Origem:

- os inputs vêm do schema do provider.

Regras:

- apenas campos editáveis entram no formulário;
- `select` usa valor técnico;
- `boolean` e `integer` preservam tipo no payload;
- `url` não sofre manipulação indevida.

## 15. Fields read-only removidos do formulário

Confirmado que **não aparecem como inputs**:

- `ultimo_teste`
- `teste_status`
- `ultimo_sync`

Também ficou fora da área editável:

- `legacy_auth_model`

## 16. `auth_model`

Confirmado:

- continua editável;
- opções vêm do schema;
- o valor técnico entra no payload;
- não foi adicionado fallback silencioso para OAuth;
- não há duplicidade visual de modo de autenticação nesta fase.

## 17. `legacy_auth_model`

Confirmado:

- não aparece como configuração independente quando não há persistência backend real;
- não entra no payload.

## 18. `sync_interval`

Verificação final:

- backend persiste em **segundos**;
- UI exibe em **minutos**;
- existe conversão explícita na carga e no save;
- a conversão ficou **simétrica**;
- `0` agora é preservado corretamente;
- foi eliminado o risco de multiplicação repetida após reload do formulário.

## 19. Secrets

Confirmado:

- campos sensíveis usam `password`;
- secrets mascarados não são reenviados;
- secret novo é enviado;
- o resumo visual continua mascarado.

## 20. Payload

`buildProviderConfigPayload` foi revalidado:

- envia somente campos declarados;
- descarta campo extra;
- ignora read-only;
- envia `auth_model`;
- suporta fields futuros sem prefixo Sankhya;
- não envia estado de UI;
- não reenvia segredo mascarado.

## 21. Ordem visual

Ordem atual validada no console:

```text
Cabeçalho
→ Readiness
→ Configuração
→ Capability Center
→ Sync Center
→ Association Center
→ Diagnóstico
→ Timeline
```

Conclusão:

- a configuração ficou facilmente localizável;
- a âncora de configuração permanece antes das áreas operacionais.

## 22. CTA e âncora

Validado:

- ID `#erp-configuracao` único;
- foco e scroll programático via `focusSection`;
- links/targets já existentes continuam apontando para a âncora correta;
- heading da seção permanece acessível pelo título do card;
- layout continua responsivo em mobile e desktop.

Cobertura:

- unit tests legados já validavam `href="#erp-configuracao"` em capability center/details;
- E2E desta fase validou a presença e visibilidade da seção alvo.

## 23. Acessibilidade

Confirmado:

- alertas visíveis em estados de erro;
- título de seção preservado;
- foco programático na seção de configuração;
- controles seguem `label`/`htmlFor`.

## 24. Responsividade

Confirmado por inspeção da estrutura:

- grids usam `md:` e `xl:` coerentes;
- ações ficam em `flex-wrap`;
- não foi criada dependência de layout desktop-only.

## 25. Testes unitários da fase

Executado com sucesso:

```bash
pnpm exec playwright test \
  src/components/integracoes/erp/provider-config-payload.test.ts \
  src/components/integracoes/erp/provider-config-fields.test.ts \
  src/components/integracoes/erp/provider-console-endpoints.test.ts \
  src/components/integracoes/erp/configuration-section.test.ts \
  --config=playwright.unit.config.ts
```

Resultado:

- `32 passed`

## 26. E2E

Executado com sucesso:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3003 \
pnpm exec playwright test tests/e2e/erp-console-configuracao.spec.ts --project=chromium
```

Resultado:

- `5 passed`

Cenários cobertos:

- configuração inicial com `status 404`;
- schema indisponível com retry;
- config `403`;
- config `500` com preservação de valores e retry;
- integração conectada com save e secrets mascarados.

## 27. Specs ERP existentes afetados

Tentativa executada para os testes legados em `tests/unit/integracoes/*erp*`.

Resultado:

- o workspace não expõe runner configurado para `.ts/.tsx` nesses arquivos;
- `node --test` falha por extensão desconhecida;
- `tsx` não está disponível como binário no pacote atual.

Conclusão:

- isso foi registrado como **limitação de tooling do workspace**, não como regressão funcional da fase.

## 28. Typecheck

Executado:

```bash
pnpm run typecheck
```

Resultado:

- `passou`

## 29. Lint

Executado:

```bash
pnpm run lint
pnpm exec eslint <arquivos alterados da fase>
```

Resultado:

- `passou`

## 30. Build

Executado:

```bash
pnpm run build
```

Resultado:

- `passou`

Observação:

- o build tocou `next-env.d.ts` com import gerado de `.next/types`, mas o arquivo foi restaurado ao conteúdo original por ser artefato incidental fora do escopo.

## 31. Diff

Executado:

```bash
git diff --check
git -C apps/web diff --check
```

Resultado:

- ambos passaram

## 32. Riscos

Riscos remanescentes:

- o resumo visual ainda referencia campos `sankhya_*` no componente genérico;
- o cenário E2E com endpoints distintos permaneceu coberto em unit, não em tenant route real;
- os testes legados `tests/unit/integracoes/*erp*` seguem sem runner oficial exposto no pacote.

## 33. Limitações

- não foi criado harness/página paralela para simular provider com `getConfig !== saveConfig` em E2E, por violar o guardrail de não introduzir fluxo paralelo;
- não foi feita correção arquitetural multiprovider nesta fase;
- nenhum backend foi tocado.

## 34. Confirmação frontend-only

Confirmado:

- esta fase ficou **100% frontend-only**;
- nenhum arquivo backend foi alterado no diff local desta fase.

## 35. Veredicto

`GO`

Justificativa:

- sem vazamento de escopo funcional;
- schema error explícito;
- `403`, `404` e `500` diferenciados;
- retry funcionando;
- `saveConfig` usado corretamente;
- read-only removidos do formulário;
- `sync_interval` corrigido com simetria de unidade;
- testes unitários da fase passaram;
- E2E segmentado da configuração passou;
- typecheck, lint, build e diff passaram;
- nenhum backend foi alterado.

## 36. Recomendação para `ERP-CORE-REPAIR-01A`

Autorizado seguir para `ERP-CORE-REPAIR-01A` após commit desta fase.

Recomendação de sequência:

1. commitar esta estabilização como fechamento de `01E.1`;
2. tratar em `01A` a remoção progressiva dos resumos `sankhya_*` remanescentes do componente genérico;
3. formalizar runner oficial para os testes legados `tests/unit/integracoes/*erp*`.
