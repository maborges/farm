# CAMPO-DATA-ISOLATION-02 — Guardrails de Logout, Pendências Offline e Cache HTTP

**Tipo:** Implementação cirúrgica no frontend `apps/campo`. Backend, PostgreSQL, migrations Alembic, FIFO, custos, financeiro e ERP não foram tocados.
**Data:** 2026-07-20

---

## Diagnóstico anterior (resumo)

`CAMPO-DATA-ISOLATION-01` (auditoria) confirmou:
- `clearCacheTables()` já protegia contra vazamento visual/de sincronização entre tenants, mas de forma incondicional (sem avisar sobre perda de trabalho pendente) e sem cobrir o caminho de `validateDeviceSession()` para dispositivo revogado online.
- `sync_queue`/`tasks` não têm `tenant_id` — a defesa é 100% dependente da limpeza no ponto certo, sem redundância.
- O Service Worker (`next-pwa`) cacheava `NetworkFirst` para qualquer URL HTTP(S), incluindo `/api/v1/*`, sem invalidação no logout.

Esta etapa fecha essas três lacunas.

---

## Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `apps/campo/src/lib/stores/session-store.ts` | Comentário de invariante sobre `clearCacheTables()`; `getLocalPendingSummary()`; `SessionClearReason`/`SessionClearNotice`; `writeSessionClearNotice()`/`consumeSessionClearNotice()`; `clearAuthenticatedRuntimeCaches()`; `clearSession(reason)` e `saveSession()` reestruturados na ordem contar→limpar Dexie→remover sessão→limpar cache HTTP→resetar estado; `validateDeviceSession()` passa a rotear a revogação por `clearSession("DEVICE_REVOKED")` em vez de `db.session.delete(1)` direto |
| `apps/campo/src/lib/sync/push.ts` | `pushSync()` revalida a sessão a cada lote do loop (guardrail de concorrência) em vez de capturá-la uma única vez no início |
| `apps/campo/next.config.ts` | Regra `NetworkOnly` para `/api/v1/.*`, avaliada antes da regra genérica `NetworkFirst` |
| `apps/campo/src/components/campo/session-clear-notice.tsx` (novo) | Componente de aviso sanitizado (só contagens + motivo, sem payload de negócio) |
| `apps/campo/src/app/(auth)/activate/page.tsx` | Consome e exibe o aviso transitório ao chegar por revogação/invalidação |
| `apps/campo/src/app/(campo)/home/page.tsx` | Consome e exibe o aviso transitório ao chegar por troca de tenant/usuário |
| `apps/campo/src/lib/stores/__tests__/session-store.test.ts` (novo) | 6 testes cobrindo os guardrails |

Nenhuma migration Dexie, nenhuma tabela nova, nenhum `tenant_id` adicionado a tabelas existentes, nenhum banco por tenant.

---

## Comportamento implementado

### 1. Invariante documentada
Comentário técnico direto acima de `clearCacheTables()` (session-store.ts) explicando por que `tasks`/`sync_queue` sem `tenant_id` tornam essa função obrigatória e não removível sem substituição equivalente.

### 2. Contagem de pendências (`getLocalPendingSummary()`)
```ts
{ syncQueue, tasks, cadernoEvents, cadernoDrafts, total }
```
Regras de contagem, usando os enums reais já existentes (nenhum enum novo criado):
- **`syncQueue`**: `sync_queue.where("status").notEqual("DONE")` — cobre `PENDING`, `IN_FLIGHT` e `FAILED` (nenhum desses é terminal/seguro para descartar sem aviso).
- **`tasks`**: `tasks.filter(t => t.synced !== true)` — usa o campo real `synced: boolean` já existente; `.filter()` em vez de índice, para não depender do comportamento de índice booleano do IndexedDB.
- **`cadernoEvents`**: `caderno_events.where("sync_status").notEqual("SYNCED")` — conta apenas eventos locais (`caderno_events`); `caderno_server_events` (espelho oficial do servidor) nunca é contado.
- **`cadernoDrafts`**: `caderno_drafts.count()` — todos os rascunhos, pois representam trabalho local por definição.
- **`total`**: soma simples das quatro categorias. A mensagem ao usuário não afirma "operações únicas" — mostra contagem por categoria e um texto genérico ("dados locais pendentes"), evitando prometer uma deduplicação que a implementação não garante.

### 3. Motivo da limpeza (`SessionClearReason`)
```ts
"DEVICE_REVOKED" | "SESSION_INVALID" | "TENANT_CHANGED" | "USER_CHANGED" | "MANUAL_LOGOUT"
```
Usado apenas para compor a mensagem de aviso — nenhum módulo de telemetria/observabilidade novo foi criado. `clearSession()` aceita o motivo como parâmetro (default `"SESSION_INVALID"`); `logout()` passa `"MANUAL_LOGOUT"`; `validateDeviceSession()` passa `"DEVICE_REVOKED"`; `saveSession()` deduz `"TENANT_CHANGED"`/`"USER_CHANGED"` comparando a sessão anterior com a nova.

### 4. Aviso ao usuário
Fluxo: `contar pendências → limpar Dexie → remover/salvar sessão → limpar cache HTTP → resetar estado → (redirecionamento feito pela página chamadora) → exibir aviso`.

O aviso (componente `CampoSessionClearNotice`) informa:
- o motivo (mapeado para texto amigável);
- que havia dados locais não sincronizados e que foram removidos para proteger o isolamento entre organizações;
- a contagem por categoria (só as categorias com valor `>0`);
- que o usuário deve contatar administrador/suporte para recuperação manual.

Não promete recuperação automática, não afirma que os dados foram enviados, não persiste título/observação/foto/localização/conteúdo agronômico — apenas `{reason, summary (contagens), clearedAt}` via `sessionStorage` (`campo:session-clear-notice`), lido e removido uma única vez (`consumeSessionClearNotice()`) pela primeira tela que o usuário acessa após a limpeza:
- `activate/page.tsx` — caminho de revogação/sessão inválida (redireciona para `/activate`).
- `home/page.tsx` — caminho de troca de tenant/usuário via nova ativação (redireciona para `/home`).

Se não houver pendências (`total === 0`), nenhum aviso é gravado — evitando ruído em trocas de sessão "limpas".

### 5. `saveSession()` — troca de tenant/usuário
```ts
const tenantChanged = !!previous && previous.tenant_id !== session.tenant_id;
const userChanged = !!previous && previous.user_id !== session.user_id;
if (tenantChanged || userChanged) {
  const summary = await getLocalPendingSummary();
  await clearCacheTables();
  await clearAuthenticatedRuntimeCaches();
  if (summary.total > 0) writeSessionClearNotice(tenantChanged ? "TENANT_CHANGED" : "USER_CHANGED", summary);
}
```
`sync_queue` nunca é preservada entre tenants — é limpa incondicionalmente junto às demais tabelas dentro de `clearCacheTables()`, sem tentativa de reenvio. Login por PIN dentro do **mesmo** tenant/usuário (`loginWithPIN`) não passa por `saveSession()` e continua sem alteração — não foi reestruturada a autenticação.

### 6. Runtime caching restrito
`next.config.ts`:
```ts
runtimeCaching: [
  { urlPattern: /\/api\/v1\/.*/, handler: "NetworkOnly" },
  { urlPattern: /^https?.*/, handler: "NetworkFirst", options: { cacheName: "campo-api-cache", ... } },
]
```
A regra específica de `/api/v1/.*` é avaliada primeiro (Workbox aplica a primeira regra que casar, na ordem do array) — cobre o proxy same-origin (`src/app/api/v1/[...path]/route.ts`) usado por `pull.ts`/`push.ts`/`devices/*`, sem depender da URL original do backend. A regra genérica permanece como fallback para assets que não passam pelo precache padrão do `next-pwa` (fontes, ícones externos, etc.); JS/CSS/manifest do próprio build continuam servidos pelo precache do Service Worker, não afetado por esta mudança. Build validado: o `sw.js` gerado contém a estratégia `NetworkOnly` para `api/v1` (confirmado por inspeção do artefato de build, depois revertido do working tree por ser gerado).

### 7. Invalidação de cache legado
```ts
async function clearAuthenticatedRuntimeCaches(): Promise<void> {
  if (typeof caches === "undefined") return;
  await Promise.all(
    AUTHENTICATED_RUNTIME_CACHE_NAMES.map((name) => caches.delete(name).catch(() => {}))
  );
}
```
`AUTHENTICATED_RUNTIME_CACHE_NAMES = ["campo-api-cache"]` — mesmo nome de cache usado por versões anteriores do PWA (antes desta correção, esse cache podia conter respostas de API autenticadas). Chamada em `clearSession()` e no ramo de `saveSession()` com troca de tenant/usuário. Tolera indisponibilidade de `caches` (SSR/teste) e falhas de `.delete()` sem lançar — nunca bloqueia a limpeza do Dexie/sessão.

### 8. Atomicidade e ordem
Ordem implementada em `clearSession()`:
```
1. getLocalPendingSummary()        (leitura, não destrutiva)
2. clearCacheTables()              (transação Dexie atômica)
3. db.session.delete(1)
4. clearAuthenticatedRuntimeCaches() (best-effort, catch por item)
5. writeSessionClearNotice() se total > 0
6. set({session:null, isAuthenticated:false})
```
`saveSession()` segue a mesma ordem lógica (sem o passo 3, pois a sessão é substituída, não removida). Cache Storage e Dexie **não** compartilham transação — a falha de `caches.delete()` é capturada por item e nunca interrompe os passos 2-3, conforme testado (Teste 5).

### 9. Concorrência com o worker de sincronização
`pushSync()` (push.ts) antes capturava a sessão uma única vez no início da função e a reutilizava em todas as iterações do loop `while(true)`. Agora:
```ts
while (true) {
  const session = useSessionStore.getState().session;
  if (!session) return;
  ...
}
```
Cada lote revalida a sessão em tempo real — se `clearSession()`/`saveSession()` limpar a sessão/fila entre lotes, o loop encerra sem reenviar com um token removido. Como `clearCacheTables()` já esvazia `sync_queue` por completo, a próxima consulta `db.sync_queue.where("status").equals("PENDING")` naturalmente retornaria vazio de qualquer forma — a mudança em `push.ts` é uma camada adicional de defesa, não a única. `recoverInFlight()` (worker.ts) não foi alterado: já opera sobre `toArray()` da tabela atual, então uma tabela limpa resulta em no-op automático, sem recriação de itens.

---

## Testes adicionados

`apps/campo/src/lib/stores/__tests__/session-store.test.ts` — 6 testes, todos usando `fake-indexeddb` (já configurado em `setup-tests.ts`), sem dependência de navegador real:

1. **Mudança de tenant limpa tudo** — semeia todas as tabelas de cache + pendências, troca tenant/user/device via `saveSession()`, valida que as 15 tabelas ficam vazias, a nova sessão persiste, e o aviso `TENANT_CHANGED` foi gravado com `summary.total > 0`.
2. **Mesma sessão não limpa cache** — `saveSession()` com mesmo `tenant_id`/`user_id`/`device_id` preserva o cache e não gera aviso.
3. **`clearSession()` detecta pendências** — 1 item em cada categoria (`sync_queue`, `tasks`, `caderno_events`, `caderno_drafts`); valida contagem exata no aviso, tabelas limpas e sessão removida.
4. **Itens concluídos não geram aviso falso** — item `DONE`/tarefa `synced:true`/evento `SYNCED` resultam em `summary.total === 0` e nenhum aviso é escrito.
5. **Falha no Cache Storage não bloqueia logout** — mocka `caches.delete()` rejeitando; confirma que Dexie e sessão são limpos mesmo assim.
6. **Nova sessão não herda a fila anterior** — após troca de tenant, `sync_queue` está vazia (nem `PENDING` nem qualquer outro registro).

---

## Comandos executados e resultados

```bash
$ pnpm --filter @agro/campo typecheck
> tsc --noEmit
(sem erros)

$ pnpm --filter @agro/campo lint
> eslint src --ext .ts,.tsx
(sem erros)

$ pnpm --filter @agro/campo exec vitest run src/lib/stores/__tests__/session-store.test.ts
 Test Files  1 passed (1)
      Tests  6 passed (6)

$ pnpm exec vitest run   # suíte completa do Campo
 Test Files  4 passed (4)
      Tests  21 passed (21)   # nenhuma regressão nos testes pré-existentes (db.test.ts, pull.test.ts, PessoaSelect.test.tsx)

$ pnpm --filter @agro/campo build
✓ Compiled successfully
✓ Generating static pages (18/18)
(sw.js gerado confirmado contendo a estratégia NetworkOnly para api/v1; artefatos de build — sw.js, workbox-*.js, next-env.d.ts — revertidos do working tree após a validação, por serem gerados)

$ git diff --check
(sem saída — limpo)

$ git status --short apps/campo/
 M apps/campo/next.config.ts
 M apps/campo/src/app/(auth)/activate/page.tsx
 M apps/campo/src/app/(campo)/home/page.tsx
 M apps/campo/src/lib/stores/session-store.ts
 M apps/campo/src/lib/sync/push.ts
?? apps/campo/src/components/campo/session-clear-notice.tsx
?? apps/campo/src/lib/stores/__tests__/session-store.test.ts
```

---

## Riscos residuais

- **Defesa em profundidade ainda ausente em `sync_queue`/`tasks`** — a proteção continua sendo a limpeza no ponto certo (agora documentada e reforçada), não um campo `tenant_id` redundante no próprio registro. Fora do escopo desta etapa por decisão explícita (nenhuma migration Dexie).
- **Troca de usuário dentro do mesmo tenant (Cenário F da auditoria anterior)** — permanece sem isolamento por usuário, comportamento inalterado por decisão explícita do escopo ("não reestruturar toda a autenticação nesta fase").
- **Aviso só é exibido na primeira tela após a limpeza** — se o usuário fechar o app antes de ver `/activate` ou `/home`, o `sessionStorage` (escopado à aba/sessão do navegador) pode ser perdido sem o aviso ter sido lido; os dados já foram removidos de qualquer forma, então não há risco de segurança, apenas de comunicação.
- **`sessionStorage` como transporte** — funciona bem para o caso de uso (mesma aba, navegação client-side), mas não sobrevive a uma nova aba/janela; aceitável dado que ativação/PIN ocorrem na mesma sessão de navegador.

---

## Decisão final

```text
CAMPO-DATA-ISOLATION-02
STATUS: GO
```

Todos os critérios de aceite foram atendidos: `clearCacheTables()` permanece o único ponto central e agora está documentado como invariante; pendências são contadas antes de qualquer limpeza; o usuário recebe aviso sanitizado (sem payload sensível) quando há perda de dados; nenhuma pendência é preservada entre tenants; `/api/v1/*` está fora do runtime cache (`NetworkOnly`, confirmado no `sw.js` gerado); o cache legado `campo-api-cache` é invalidado nos mesmos pontos de troca de sessão; falha no Cache Storage não impede o logout seguro (testado); typecheck, lint e os 6 testes novos (mais os 15 pré-existentes) passam; `git diff --check` está limpo; nenhuma migration Dexie ou mudança de backend foi introduzida.

Pronto para retomar `SOIL-PLAN-EXEC-04B`.
