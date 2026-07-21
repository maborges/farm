# SOIL-PLAN-EXEC-04A — Auditoria do Fluxo OperacaoAgricola → Campo PWA → Sincronização

**Tipo:** Auditoria arquitetural e funcional, somente leitura. Nenhum código de produção, teste, migration ou configuração foi alterado.
**Data:** 2026-07-20
**Escopo:** `apps/campo` — analisado como aplicação própria (correção da auditoria anterior, que buscou apenas em `apps/web`).

**Correção da conclusão anterior:** o relatório `SOIL-PLAN-EXEC-04` classificou o elo `OperacaoAgricola → Campo PWA` como AUSENTE por ter buscado em `apps/web/src`. Essa conclusão está **invalidada**. `apps/campo` é uma aplicação Next.js separada, com Dexie, service worker real (build gerado em `public/sw.js`), fila de sincronização e idempotência por `client_id` no backend. O elo existe e é substancialmente mais completo do que a auditoria anterior concluiu.

---

## 1. Arquitetura real do aplicativo Campo

| Item | Situação | Evidência |
|---|---|---|
| Framework | Next.js `^16.1.6` (App Router), React 19 | `apps/campo/package.json:15,17` |
| Cliente HTTP | `fetch` nativo direto (não axios) | `src/lib/sync/pull.ts:210`, `src/lib/sync/push.ts:54,167` |
| Estado | Zustand (`session-store.ts`, `sync-store.ts`) | `src/lib/stores/session-store.ts:1,34`; `sync-store.ts:1,17` |
| Armazenamento offline | Dexie — banco `campo_db`, schema v14 | `src/lib/db.ts:364,382,627` |
| Service Worker | `next-pwa`, `register:true, skipWaiting:true`; artefatos de build confirmados (`public/sw.js`, `public/workbox-*.js`) | `next.config.ts:5-19` |
| Cache | `NetworkFirst`, 200 entradas, TTL 86400s, para qualquer URL | `next.config.ts:11-17` |
| Manifest PWA | `manifest.json` com ícones 192/512, `display:"standalone"` | `public/manifest.json` |

`@tanstack/react-query` está no `package.json` mas seu uso extensivo não foi confirmado em profundidade neste escopo — não afeta as conclusões centrais.

---

## 2. Entrada de operações agrícolas no Campo

**Situação: PARCIAL**

- Endpoint: `GET /api/v1/sync/pull?device_id=...&last_sync_at=...`, chamado via proxy Next (`src/app/api/v1/[...path]/route.ts`) → backend. Chamada real: `src/lib/sync/pull.ts:205-212`.
- Filtros no cliente: apenas `device_id` e `last_sync_at` (sync incremental). Não há `safra_id`/`talhao_id`/`tenant_id` explícitos no client — tenant/escopo são resolvidos no backend a partir do dispositivo autenticado (ver seção 13).
- **Resposta direta:** *o Campo não baixa `OperacaoAgricola` diretamente — recebe um modelo derivado, `tarefas_pendentes[]`, dentro do payload `SyncPullPayload`* (`pull.ts:6-164`).
- Campos tipados no topo do DTO de tarefa: `id, client_id, dispositivo_id, type, module, status, origem, status_execucao, titulo, data_programada, prioridade, operador_id, dados, unidade_produtiva_id, area_rural_id, lote_id, client_created_at, client_updated_at` (`pull.ts:~30-69`).
- **Campos ausentes no nível tipado do DTO:** `operacao_id`, `safra_id` (existe no payload geral `safras[]`, mas não como FK direta na tarefa), `talhao_id` (usa `area_rural_id`), `cultivo_id`, `analise_solo_id`, produto/dose/quantidade/área planejada — todos esses ficam dentro do blob livre não tipado `dados: Record<string, unknown>` (`pull.ts:69`).
- Download inicial vs incremental: confirmado — `last_sync_at` ausente = full pull; presente = incremental (`pull.ts:206-208`); cursor atualizado após aplicar (`pull.ts:521`).

**Risco:** o schema de detalhes agronômicos (dose, produto, quantidade planejada) não é tipado no client — é um `Record<string, unknown>` opaco. Isso enfraquece garantias de contrato entre backend e Campo (mudanças no backend não quebram o build do Campo, mas também não são pegas em typecheck).

---

## 3. Rastreabilidade da análise de solo

**Situação: PARCIAL**

- `tarefa_id`/`client_id` é recebido e persistido: `tarefas_pendentes[].id` (server id) mapeado para `LocalTask.server_id`; `client_id` vira a chave local `LocalTask.id` (`pull.ts:389,393`).
- É reenviado na sincronização: sim — `pushTaskSync` inclui `local_id: item.entity_id` e `server_id: item.server_id ?? null` (`push.ts:44-51`).
- `tarefa_id` também é campo dedicado em `CampoEventoOffline.tarefa_id` (`db.ts:159`) no fluxo de caderno.
- **`analise_solo_id`:** não encontrado como campo tipado em nenhuma camada do Campo (nem no DTO de pull, nem no Dexie, nem no payload de push). Como a auditoria anterior já confirmou que `analise_solo_id` não chega nem até `OperacaoAgricola` no backend, é esperado que também não chegue ao Campo — a lacuna é herdada do backend, não introduzida pelo Campo.
- **Não há evidência de DTO que "elimine" `tarefa_id"** — ao contrário, o `tarefa_id`/`client_id` é preservado de ponta a ponta (pull → Dexie → push).
- **Impacto na interface:** não confirmado se a origem "veio de análise de solo" é exibida ao operador — os campos de `dados` (blob opaco) poderiam conter essa info, mas não foi encontrado tratamento explícito disso na UI dentro do escopo revisado.

---

## 4. Persistência local (Dexie)

**Situação: INCONSISTENTE**

- Schema: 14 versões incrementais (`db.ts:383-646`), com `upgrade()` migrando dados em v2, v7, v8.
- Tabelas: `session, tasks, sync_queue, caderno_events, caderno_server_events, caderno_drafts, fazendas, talhoes, lotes, animais, insumos, safras, colaboradores, recomendacoes_climaticas, recomendacoes_operacionais, pessoas_operacionais` (`db.ts:364-379`).
- Chaves primárias: `session.id` (singleton fixo `1`), `tasks.id`, `sync_queue.id`, `caderno_events.local_id`, `pessoas_operacionais.id = "${unidade_produtiva_id}:${pessoa_id}"` (`db.ts:305,664-666`).
- **Índice de `tenant_id`: só existe em `caderno_events`** (`db.ts:388` e versões seguintes). As demais tabelas (`tasks, fazendas, talhoes, lotes, animais, insumos, safras`) **não têm campo/índice `tenant_id`**.
- **Isolamento por tenant/usuário: NÃO EXISTE.** Um único banco `campo_db` global por dispositivo (nome fixo, sem sufixo de tenant/usuário — `db.ts:382`). `LocalSession` é registro singleton `id:1` (`db.ts:69`) — só há uma sessão ativa por vez no dispositivo.
- **Troca de usuário/tenant:** `logout`/`clearSession` apaga apenas `db.session.delete(1)` (`session-store.ts:107-110`). As tabelas de cache (`tasks, fazendas, talhoes, caderno_events` etc.) **não são limpas** no logout — não encontrado nenhum `db.tasks.clear()` equivalente.

**Resposta direta às perguntas do escopo:**
- Operação salva localmente? Sim (tabela `tasks`).
- Isolamento entre tenants? **Não** — mesmo banco físico, sem índice de tenant na maioria das tabelas.
- Isolamento entre usuários? **Não** — sessão singleton, sem particionamento.
- Troca de usuário pode expor dados offline do usuário anterior? **Sim, potencialmente** — dados de tarefas/fazendas/talhões do tenant anterior permanecem no IndexedDB após logout, disponíveis para leitura até o próximo pull sobrescrever/expirar.
- Troca de tenant limpa ou separa o banco local? **Não limpa.**

**Este é o achado de maior severidade da auditoria.** Um dispositivo compartilhado entre operadores de tenants diferentes (cenário plausível em prestadores de serviço agrícola que atendem múltiplas fazendas/clientes) pode reter dados operacionais (tarefas, talhões, insumos) do tenant anterior no armazenamento local, mesmo sem tela mostrando-os ativamente — risco de vazamento de dados entre tenants no armazenamento do dispositivo.

---

## 5. Execução offline

| Capacidade | Classificação | Evidência |
|---|---|---|
| Conclusão de tarefa (status_execucao=CONCLUIDA) | SUPORTADA | `tarefa/[id]/page.tsx:132-140` |
| Observações | SUPORTADA | `obs` no payload, mesma linha |
| Fotos | SUPORTADA | `cam.fotos` via `useCamera`, mesma linha |
| Coordenadas GPS | SUPORTADA | `gps.status/latitude/longitude`, mesma linha |
| Produto/insumo aplicado | SUPORTADA (por tela específica) | ex. `campo/aplicacao/page.tsx:21,32,51-59` |
| Quantidade realmente aplicada | PARCIAL | capturado nas telas por tipo de operação, dentro do blob `dados`, não padronizado |
| Lote de estoque / depósito | AUSENTE | não encontrado no fluxo de execução do Campo |
| Operador / máquina / implemento | PARCIAL | `operador_id` presente no DTO de tarefa; máquina/implemento não confirmados na captura de execução |
| Início / pausa / retomada | PARCIAL | status local inclui `EM_ANDAMENTO`/`EM_EXECUCAO`, mas fluxo de pausa/retomada explícito não confirmado |
| Cancelamento | SUPORTADA (status local `CANCELADA`) | `db.ts:35,37` |
| Execução parcial (quantidade parcial vs planejada) | AUSENTE | não encontrada validação/captura de "parcial" distinta de conclusão total |
| Justificativa de divergência / insumo substituto | AUSENTE | não encontrado |

**Caminho completo confirmado:** componente `.tsx` → `executarTarefa()`/`createTask()` (`lib/task-factory.ts`) → grava em `db.tasks` (Dexie, `synced:false`) → `enqueueSync()` insere em `db.sync_queue` (`task-factory.ts:53,69-80,109-118`) → `requestSync()` → `runSync()` (`lib/sync/trigger.ts`, import dinâmico de `./worker`) → `pushSync()` (`lib/sync/push.ts:40-61`) → `POST /api/v1/sync/push`.

**Observação sobre lote/depósito:** consistente com o princípio de que o Campo não deve decidir FIFO — mas também significa que o Campo não escolhe lote/depósito, apenas produto e quantidade; a resolução de lote fica inteiramente no backend (ver seção 10), o que é o comportamento arquiteturalmente correto.

---

## 6. Estados locais e estados do backend

| Estado Campo | Estado backend (esperado) | Direção | Observação |
|---|---|---|---|
| `PENDENTE` (TaskStatus) | `PLANEJADA`/`APROVADA` | pull | Vocabulário próprio do Campo, sem tradução explícita encontrada no código lido |
| `EM_ANDAMENTO` | não confirmado equivalente direto em `OperacaoAgricola` | local | Estado majoritariamente local/UX |
| `CONCLUIDA` | `REALIZADA` | push | Mapeamento não encontrado como função/tabela explícita — parece implícito via `status_execucao` |
| `CANCELADA` | cancelamento/estorno (confirmado na auditoria 04) | push | Não confirmado se o Campo consegue disparar o fluxo de estorno documentado no backend |
| Caderno: `RASCUNHO/PENDENTE_SINCRONIZACAO/SYNCING/SINCRONIZADO` | estados exclusivamente locais (transitórios de sync) | local | `db.ts:164-173` |
| Caderno: `PENDENTE_APROVACAO/APROVADO/REJEITADO/CONSOLIDADO/CANCELADO` | espelham estados do backend (`eventos_caderno_oficiais.status_evento`) | pull/push | `pull.ts:166` |

**Situação: PARCIAL/INCONSISTENTE** — não foi encontrada, no código lido, uma função de tradução centralizada e explícita entre o vocabulário de status do Campo (`PENDENTE/EM_ANDAMENTO/CONCLUIDA/CANCELADA`) e os estados reais de `OperacaoAgricola`/`SafraTarefa` no backend (`PLANEJADA/APROVADA/REALIZADA`). Isso é um risco de mapeamento implícito — mudanças de nomenclatura em um lado podem não ser refletidas no outro sem quebra visível em teste, dado que `dados` é `Record<string, unknown>`.

**Risco de operação travada:** possível caso o backend rejeite a conclusão (ex. estoque insuficiente) — precisa confirmar se o item de fila retorna a `PENDING`/erro visível ou fica preso silenciosamente (ver seção 7 e 10).

---

## 7. Fila de sincronização

**Situação: COMPLETO (mecanismo básico) / PARCIAL (backoff)**

- Modelo: tabela `sync_queue` — `id, operation(CREATE/UPDATE/DELETE), entity_type, entity_id, server_id, payload, created_at, attempts, last_error, status(PENDING/IN_FLIGHT/DONE/FAILED)` (`db.ts:113-124,366`).
- Processamento: `pushSync()` em loop, lotes de até `MAX_BATCH=50` (`push.ts:7,13-20`), separando `task` e `caderno_event` (linhas 22-31).
- Retry: erro de rede/HTTP no push de task → item volta a `PENDING` sem incrementar `attempts` (retry ilimitado nesse caminho) (`push.ts:64`). Erro de negócio retornado pelo backend → incrementa `attempts`, `FAILED` ao atingir 5 tentativas (`push.ts:98-104`, mesmo padrão no caderno, linha 227).
- **Backoff exponencial: não encontrado** — retry depende apenas de `requestSync()`/eventos de rede, sem atraso incremental.
- Conflito de dados: retorna `CONFLICT`, marca item `DONE` (não reenvia), grava `sync_conflict` na tarefa (`push.ts:89-95`).
- Erro de negócio em caderno com status oficial terminal (`REJEITADO/CONSOLIDADO/CANCELADO`): bloqueia retry, marca `DONE` com mensagem (`push.ts:146-152`).

**Resposta direta:** *sim, uma execução permanece armazenada com segurança até ser confirmada pelo backend* — a fila persiste em Dexie (sobrevive a fechamento de app/navegador) e só é marcada `DONE` após confirmação do backend ou erro terminal de negócio. Falta apenas backoff exponencial, o que é uma lacuna de robustez, não de correção.

---

## 8. Idempotência

**Situação: COMPLETO**

- Client: `LocalTask.id`/`SyncQueueItem.entity_id` são UUIDs gerados no dispositivo via `crypto.randomUUID()` (`db.ts:657`, `task-factory.ts:23`, `push.ts:258`). `CadernoEvidenciaOffline.local_evidence_id` é UUID dedicado para idempotência de upload (`db.ts:127-128`).
- Backend: `services/api/campo/service.py:1049-1054` faz deduplicação explícita por `client_id` ("verificar duplicata por client_id"), filtra `TarefaCampo.client_id == item.local_id`; grava `client_id=item.local_id` na criação (linha 1070).
- Não encontrado ETag/versionamento otimista HTTP padrão — o "conflito" é tratado por lógica de negócio custom (comparação de `status_evento`/`server_id`, `pull.ts:169-199`, `push.ts:89-95`), não por optimistic locking genérico.

**Resposta direta:**
- O Campo pode enviar a mesma conclusão duas vezes? Tecnicamente sim (ex. reenvio após timeout), mas o backend reconhece pelo `client_id`.
- O backend reconhece que é a mesma execução? **Sim** — deduplicação confirmada em `campo/service.py:1049-1054`.
- Resposta perdida pode fazer o Campo reenviar? Sim (item permanece `PENDING`/retry no erro de transporte).
- Reenvio cria nova execução? **Não**, protegido por `client_id` no backend.
- Reenvio baixa estoque/duplica custo/despesa novamente? Não diretamente testado nesta auditoria, mas como a criação da `TarefaCampo` é deduplicada na entrada, o fluxo subsequente (FIFO/custo/despesa, auditado em 04) não deveria ser re-disparado para o mesmo `client_id`.
- Proteção é apenas na interface ou também no backend? **Também no backend** — é a proteção real; a idempotência não depende apenas de comportamento client-side.

---

## 9. Conflitos de sincronização

| Caso | Comportamento atual | Proteção existente | Risco | Necessita correção futura? |
|---|---|---|---|---|
| A — Operação alterada no backend após download | Não confirmado tratamento explícito de "operação mudou enquanto offline" para `tasks` (fora do caderno) | Caderno tem lógica de `CONFLICT`/status oficiais; `tasks` não confirmado com o mesmo nível | Médio — Campo pode executar sobre dado desatualizado | Sim, recomendável investigar |
| B — Dois dispositivos baixam a mesma operação | Pull não reserva/trava a operação | Nenhuma reserva encontrada (consistente com auditoria 04, que já apontou ausência de reserva de estoque) | Médio — duas execuções concorrentes possíveis | Sim |
| C — Dois operadores concluem a mesma operação offline | Cada um gera `client_id` próprio | Deduplicação por `client_id` não impede duas conclusões com `client_id` diferentes para a mesma tarefa de origem | Médio-Alto — pode gerar duas `TarefaCampo`/duas baixas de estoque se ambos client_ids forem aceitos | Sim, ponto crítico |
| D — Operação cancelada no backend enquanto offline no Campo | Pull traria tombstone/status atualizado na próxima sincronização | `tombstones` existe no payload (`pull.ts`) para talhões/lotes/tarefas/insumos | Baixo-Médio — janela entre cancelamento e próxima sincronização | Não crítico, comportamento aceitável |
| E — Estoque muda antes da sincronização | Backend revalida saldo no push (consistente com FIFO síncrono da auditoria 04) | Validação de saldo no backend, não no Campo | Baixo — comportamento correto por design | Não |
| F — Backend processa mas resposta não chega | Item de fila permanece `PENDING`, reenviado | Deduplicação por `client_id` evita duplicação na re-tentativa | Baixo | Não |

**Observação:** os casos B e C são os de maior risco real e não têm proteção de reserva/lock encontrada em código — coerente com a ausência de "reserva de estoque no planejamento" já identificada na auditoria 04.

---

## 10. Integração com estoque

**Situação: COMPLETO (separação correta)**

- Não encontrado cálculo de FIFO no Campo. Única ocorrência da palavra "FIFO" é um comentário sobre ordem de upload de evidências (`src/lib/sync/evidence-upload.ts:95`), não relacionado a estoque.
- Tela de vacinação exibe apenas aviso textual de UX ("sincronize os insumos para garantir estoque e custo") — sem cálculo (`campo/vacinacao/page.tsx:140`).
- O Campo envia produto e quantidade real, mas não escolhe lote/depósito — resolução de lote fica no backend (consistente com FIFO síncrono confirmado na auditoria 04).
- Rejeição por saldo insuficiente: o backend valida (confirmado na auditoria 04, `estoque_fifo.py`, erro de saldo insuficiente); no Campo, esse erro retornaria como falha de item na fila de push (`push.ts:98-104`, erro de negócio → `attempts++` → `FAILED` após 5 tentativas) — o item permanece pendente/falho, não é silenciosamente descartado.

**Resposta direta:** *sim, o consumo de estoque continua sendo responsabilidade exclusiva do backend.* O Campo apenas informa fatos operacionais (produto, quantidade); não há risco de cálculo econômico autoritativo no client.

---

## 11. Integração com custo e financeiro

**Situação: NÃO APLICÁVEL (confirmação de fronteira, não reauditoria)**

- Não encontrado no Campo: cálculo de custo, envio de preço/valor financeiro, criação de despesa, criação de conta a pagar, ou chamada a integração ERP.
- O fluxo observado é consistente com o esperado: Campo envia fatos operacionais → backend valida, consome estoque, calcula FIFO/custo, apropria e trata efeitos financeiros (confirmado na auditoria 04).
- **Nenhum risco de cálculo econômico no client foi identificado.**

---

## 12. API e contratos compartilhados

**Situação: AUSENTE (contratos compartilhados não usados)**

- Busca por `packages/types`, `packages/zod-schemas`, `@agro/types`, `@agro/schemas`, `@agro/utils` em `apps/campo/src` **não retornou nenhuma ocorrência**.
- O Campo define seus próprios tipos/DTOs localmente (`db.ts`, interface `SyncPullPayload` em `pull.ts`, `task-factory.ts`), com validação própria via `zod` (ex. `activate/page.tsx:14-22`).
- **Risco:** duplicação de contratos entre backend e Campo sem fonte única de verdade tipada — mudanças de schema no backend (ex. renomear campo em `dados`) não quebram o build do Campo (por ser `Record<string, unknown>`), o que reduz a chance de erros serem detectados em `typecheck`/CI.

---

## 13. Autenticação, tenant e RLS

**Situação: COMPLETO (backend não confia no cliente) / PARCIAL (cache local sem isolamento, ver seção 4)**

- Token: `device_token` armazenado em Dexie, tabela `session` (`db.ts:73`), não em localStorage/cookie. Enviado como `Authorization: Bearer` em todas as chamadas (`pull.ts:211`, `push.ts:58,171`, `session-store.ts:66`).
- `tenant_id` também persistido em `LocalSession.tenant_id` (`db.ts:71`), mas **não é enviado no payload de sync** — `pull`/`push` mandam apenas `device_id`/`device_token`.
- Backend resolve tenant a partir do dispositivo autenticado: `SyncService(session, device.tenant_id, device)` (`services/api/campo/router.py:507,524`), e valida que `device_id` da query bate com o `device_id` do token JWT (`router.py:168-170`).
- **O backend não confia em `tenant_id` vindo do cliente** — deriva do token/registro de dispositivo. Boa prática confirmada.

**Resposta direta:** *uma execução offline não pode ser sincronizada no tenant errado após troca de sessão*, porque o backend nunca usa `tenant_id` do payload — sempre deriva do device/token autenticado no momento do push. O risco residual não é de sincronização em tenant errado no servidor, mas sim **exposição de dados em cache local** de um tenant anterior no dispositivo compartilhado (ver seção 4) — são riscos distintos: um é de integridade de dados no backend (mitigado), o outro é de confidencialidade local no dispositivo (não mitigado).

---

## 14. Service Worker e instalação

| Classificação | Status |
|---|---|
| OFFLINE-FIRST | SIM — Dexie + fila de sync confirmados, app funciona sem rede para operações já baixadas |
| INSTALÁVEL | SIM — `manifest.json` com ícones e `display:standalone` confirmado |
| SERVICE WORKER ATIVO | SIM — `next-pwa` configurado e artefatos de build (`sw.js`, `workbox-*.js`) presentes, confirmando geração real, não apenas dependência declarada |
| SINCRONIZAÇÃO OFFLINE | SIM — fila `sync_queue` com retry e idempotência por `client_id` |

Não classificado como PWA apenas por usar Dexie — a classificação acima considera as quatro dimensões separadamente, todas com evidência de build/uso real, não apenas dependência no `package.json`.

---

## 15. Testes

| Área | Classificação | Evidência |
|---|---|---|
| Banco Dexie / schema | COBERTA | `src/lib/__tests__/db.test.ts` |
| Sync pull | COBERTA | `src/lib/sync/__tests__/pull.test.ts` |
| Sync push (fila) | NÃO COBERTA | não encontrado teste dedicado a `push.ts` |
| Fila / retry / backoff | NÃO COBERTA | não encontrado |
| Idempotência (client-side) | NÃO COBERTA | não encontrado teste específico no Campo (idempotência do backend está coberta indiretamente em `services/api/campo/`, fora deste escopo) |
| Conflito | NÃO COBERTA | não encontrado |
| Troca de tenant / isolamento local | NÃO COBERTA | consistente com a lacuna arquitetural identificada na seção 4 |
| Service worker / build PWA | NÃO COBERTA | não encontrado teste automatizado; validado nesta auditoria apenas via presença de artefatos de build |
| Integração real com backend | NÃO COBERTA | não encontrado teste de integração end-to-end Campo↔API |

**Nota:** não há script `test` no `package.json` do Campo apesar de `vitest.config.ts` e `fake-indexeddb` estarem configurados — os testes existentes (`db.test.ts`, `pull.test.ts`, `PessoaSelect.test.tsx`) precisam ser executados via `vitest` diretamente, não via `pnpm --filter @agro/campo test` (script inexistente).

---

## 16. Validações executadas

```bash
$ cat apps/campo/package.json   # scripts confirmados: dev, build, start, lint, typecheck (sem "test")
$ pnpm --filter @agro/campo typecheck
> tsc --noEmit
(sem erros)

$ pnpm --filter @agro/campo lint
> eslint src --ext .ts,.tsx
(sem erros)

$ git status --short
(sem alterações introduzidas por esta auditoria; alterações preexistentes no repo não tocadas)

$ git diff --check
(sem saída — sem problemas de whitespace/conflito)
```

`build` e `test` não foram executados: `build` é demorado e não essencial às conclusões (artefatos de SW já confirmados fisicamente em `public/`); `test` não existe como script — rodá-lo exigiria invocar `vitest` diretamente, fora do padrão de scripts documentado, e não foi necessário para as conclusões desta auditoria.

---

## 17. Matriz final

| Etapa | Situação | Evidência | Risco |
|---|---|---|---|
| Operação planejada → API Campo | PARCIAL | `pull.ts:6-164` (`tarefas_pendentes[]`, campos agronômicos em blob opaco `dados`) | Contrato não tipado enfraquece detecção de quebras |
| API → armazenamento local | COMPLETO | `pull.ts:389,393` → `db.ts` tabela `tasks` | Baixo |
| Persistência offline | INCONSISTENTE | `db.ts:382` (banco único sem tenant/user scoping), `session-store.ts:107-110` (logout não limpa cache) | **Alto — vazamento de dados entre tenants em dispositivo compartilhado** |
| Execução no dispositivo | PARCIAL | `tarefa/[id]/page.tsx:132-140`; sem execução parcial estruturada, sem lote/depósito | Médio |
| Execução → fila | COMPLETO | `task-factory.ts:53,69-80,109-118` | Baixo |
| Fila → backend | PARCIAL | `push.ts:40-104` (sem backoff exponencial) | Baixo-Médio |
| Idempotência | COMPLETO | `services/api/campo/service.py:1049-1070`, `db.ts:657` | Baixo |
| Conflitos | PARCIAL | ausência de reserva/lock para casos B/C (dois dispositivos/operadores) | Médio-Alto |
| Backend → FIFO | COMPLETO (fronteira respeitada) | ausência de FIFO no Campo confirmada; FIFO real no backend (auditoria 04) | Baixo |
| Tenant/RLS (servidor) | COMPLETO | `campo/router.py:168-170,507,524` (backend não confia em tenant do cliente) | Baixo |
| Tenant/RLS (dispositivo local) | AUSENTE | ver "Persistência offline" acima | Alto |
| Service Worker | COMPLETO | `next.config.ts:5-19`, `public/sw.js`, `public/workbox-*.js` | Baixo |
| Instalação PWA | COMPLETO | `public/manifest.json` | Baixo |

---

## 18. Veredicto

**Classificação: Opção B — offline funcional com ressalvas.**

O fluxo principal — download de tarefas, execução offline com Dexie, fila de sincronização persistente, e idempotência real garantida pelo backend via `client_id` — **existe e funciona**, contrariando a conclusão AUSENTE da auditoria anterior (Opção E descartada). A separação de responsabilidades com estoque/custo/financeiro está correta (Campo não calcula FIFO nem valores financeiros).

As ressalvas que impedem a Opção A (fluxo offline completo sem lacunas) são:
1. **Ausência de isolamento de tenant/usuário no armazenamento local** — risco de confidencialidade em dispositivo compartilhado (achado mais severo).
2. Ausência de proteção contra conflito em cenário de dois dispositivos/operadores concluindo a mesma operação (caso B/C).
3. Contrato de dados agronômicos não tipado (`dados: Record<string,unknown>`), sem uso de pacotes de contrato compartilhados do monorepo.
4. Cobertura de testes concentrada em pull/Dexie; push, fila, retry, idempotência client-side e conflito não têm teste automatizado.
5. Rastreabilidade de `analise_solo_id` continua ausente no Campo — mas essa é uma lacuna herdada do backend (já registrada na auditoria 04), não introduzida pelo Campo.

---

## 19. Próximo passo recomendado (menor passo, não implementar)

Investigar (somente leitura, sem correção) se o logout/troca de sessão em `session-store.ts` deveria limpar as tabelas de cache do Dexie (`tasks, fazendas, talhoes, lotes, animais, insumos, safras, caderno_events`, etc.) além do registro `session` — esse é o achado de maior risco (exposição de dados de um tenant no armazenamento local após troca de usuário/dispositivo) e o mais barato de confirmar/corrigir isoladamente, sem tocar em backend, FIFO, custo ou financeiro.

Não implementar a correção agora. Não propor reconstrução do Campo, novo PWA, migração de funcionalidades para `apps/web`, nem alteração do backend agrícola.
