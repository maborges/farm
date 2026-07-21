# CAMPO-DATA-ISOLATION-01 — Auditoria de Isolamento Local, Logout e Troca de Tenant

**Tipo:** Auditoria arquitetural e funcional, somente leitura. Nenhum código de produção, teste, migration, configuração PWA ou schema Dexie foi alterado nesta etapa.
**Data:** 2026-07-20
**Escopo:** `apps/campo/src/lib/db.ts`, `session-store.ts`, `lib/sync/*`, `task-factory.ts`, `apps/campo/src/app/**`, `services/api/campo/**`.

**Nota de contexto:** esta auditoria já encontra o código **pós-correção** aplicada na etapa anterior (`clearCacheTables()` em `session-store.ts`). O objetivo aqui é validar se essa correção é suficiente e mapear os riscos residuais.

---

## 1. Inventário completo do banco local (`campo_db`, v14)

| Tabela | Conteúdo | Chave primária | tenant_id | user_id | unidade produtiva | Deve sobreviver ao logout? |
|---|---|---|---|---|---|---|
| `session` | Sessão do dispositivo | `id` (singleton=1) | Sim (campo `tenant_id`) | Sim (`user_id`) | Não | Não — é a própria sessão, apagada por definição |
| `tasks` | Tarefas locais (PROGRAMADA/MANUAL) | `id` | **Não** | `operador_id` (não persistido, ver §2) | `fazenda_id` | Não |
| `sync_queue` | Fila de sincronização | `id` | **Não** | **Não** | Não | Não |
| `caderno_events` | Eventos offline do caderno (inclui `evidencias[]` embutidas) | `local_id` | **Sim** (índice dedicado) | Não direto | `talhao_id`/`safra_id` | Não |
| `caderno_server_events` | Eventos oficiais espelhados do servidor | `server_id` | **Não** | Não | `talhao_id`/`safra_id` | Não |
| `caderno_drafts` | Rascunhos de formulário do caderno | `id` | **Não** | `user_id` (índice) | Não | Não |
| `fazendas` | Cache de unidades produtivas | `id` | **Não** | Não | — (é a própria entidade) | Não |
| `talhoes` | Cache de talhões | `id` | **Não** | Não | `fazenda_id` | Não |
| `lotes` | Cache de lotes (pecuária) | `id` | **Não** | Não | `fazenda_id` | Não |
| `animais` | Cache de animais | `id` | **Não** | Não | via `lote_id` | Não |
| `insumos` | Catálogo de insumos | `id` | **Não** | Não | Não | Não |
| `safras` | Cache de safras | `id` | **Não** | Não | Indireto | Não |
| `colaboradores` | Cache de colaboradores | `id` | **Não** | Não | Não | Não |
| `recomendacoes_climaticas` | Cache de recomendações climáticas | `id` | **Não** | Não | Não | Não |
| `recomendacoes_operacionais` | Cache de recomendações operacionais | `id` | **Não** | Não | Não | Não |
| `pessoas_operacionais` | Cache de pessoas por unidade | `${unidade_produtiva_id}:${pessoa_id}` | **Não** | Não | Sim (chave composta) | Não |

Classificação por tipo:
- **SESSÃO:** `session`.
- **CACHE DERIVADO DO SERVIDOR** (recriável por pull): `fazendas, talhoes, lotes, animais, insumos, safras, colaboradores, recomendacoes_climaticas, recomendacoes_operacionais, pessoas_operacionais`, `caderno_server_events`.
- **DADO OPERACIONAL LOCAL NÃO SINCRONIZADO:** `tasks` (parcialmente — mistura registros já sincronizados com pendentes via campo `synced`), `caderno_events`, `caderno_drafts`.
- **FILA PENDENTE:** `sync_queue`.
- **EVIDÊNCIA LOCAL:** embutida em `caderno_events.evidencias[]` (`db.ts:180`) — não é tabela própria; fotos ficam dentro do próprio evento.
- **CONFIGURAÇÃO DO DISPOSITIVO:** nenhuma tabela dedicada encontrada além de `session`.
- **DADO PÚBLICO/NÃO SENSÍVEL:** nenhuma identificada — todo cache é potencialmente sensível por refletir operações de um tenant específico.

Nenhuma tabela fora das 16 já mapeadas foi encontrada em `db.ts`.

**Achado relevante:** apenas `caderno_events` tem `tenant_id` como campo/índice nativo. Todas as demais tabelas — incluindo `tasks` e `sync_queue`, que carregam o trabalho operacional mais sensível — não têm `tenant_id` nem `device_id` gravado no registro. O isolamento depende inteiramente de limpeza disciplinada na troca de sessão, não de filtro por dado.

---

## 2. Fluxo real de logout

```text
device_revoked/expired/invalid detectado (pin/page.tsx:26-28, session-store.ts:75-78)
→ clearSession() [session-store.ts:150-154]
  → clearCacheTables() [linhas 20-60] — limpa 15 tabelas em transação Dexie
  → db.session.delete(1)
  → set({session:null, isAuthenticated:false})
→ redirecionamento condicional (via useEffect de cada página que checa session)
```

- **Componente que dispara:** não há botão de logout manual na UI (confirmado na auditoria anterior — segue não encontrado). O único gatilho real é `validateDeviceSession()` falhando (401/403/404) dentro de `pin/page.tsx:19-30` e `loginWithPIN` (`session-store.ts:94-95`).
- **Função chamada:** `clearSession()` → `clearCacheTables()` + `db.session.delete(1)` (session-store.ts:150-154).
- **Stores resetadas:** `useSessionStore` (`session: null, isAuthenticated: false`). `useSyncStore` (fila/status de sync) **não é resetada explicitamente** — não encontrada chamada de reset nela dentro de `clearSession()`; seu estado (`pendingCount`, `syncStatus`) é derivado de `useLiveQuery` sobre `db.sync_queue`, então tende a zerar automaticamente após `sync_queue.clear()`, mas isso é reatividade indireta, não reset explícito.
- **Registros Dexie apagados:** as 15 tabelas de `clearCacheTables()` + `session`.
- **Registros que permanecem:** nenhum dentro do escopo de `clearCacheTables()` — cobertura completa das tabelas mapeadas na seção 1.
- **Token em memória:** `device_token` só existe dentro do objeto `session` do Zustand store — ao `set({session:null})`, a referência em memória do processo React é descartada, mas closures/handlers já montados que capturaram `session.device_token` antes do logout podem retê-lo até o componente ser desmontado (risco de baixa severidade, natural de qualquer SPA).
- **`device_id` permanece?** Não — está dentro do registro `session`, apagado.
- **`tenant_id` em alguma store?** Não encontrado fora de `session`/`LocalSession`.
- **Service Worker mantém respostas autenticadas em cache?** Sim, potencialmente — ver seção 10; `clearSession()` **não chama `caches.delete()`/invalidação do Workbox**.
- **Componentes montados continuam com dados em memória?** Sim, até desmontagem/rerender — comportamento padrão React, mitigado pelo fato de o redirecionamento (`router.replace`) geralmente desmontar a árvore.
- **Redirecionamento:** ocorre via `router.replace("/activate?reason=...")` nas páginas que chamam `validateDeviceSession` (`pin/page.tsx:27,49`), não dentro de `clearSession()` em si — a responsabilidade de navegar é da página chamadora.
- **Reload completo da aplicação?** Não encontrado — é navegação client-side (App Router), sem `window.location.reload()`.
- **Risco de "voltar" no navegador exibir dados anteriores?** Baixo-médio — como as tabelas já foram limpas de forma síncrona antes do redirecionamento, uma navegação de volta re-executaria os `useLiveQuery` contra tabelas vazias. O risco residual é o service worker (seção 10), não o Dexie.

---

## 3. Fluxo de login/ativação posterior

```text
nova ativação (activate/page.tsx:116) ou login por PIN (mesmo tenant)
→ saveSession() [session-store.ts:156-165]
  → compara previous.tenant_id/user_id com o novo
  → se mudou: clearCacheTables() ANTES de gravar a nova sessão
  → db.session.put(normalized)
→ hidratação de stores (loadSession, useLiveQuery reagem)
→ primeiro pull (pull.ts) repopula tabelas de cache
```

- **Login lê tarefas antigas antes do primeiro pull?** Não, se `tenant_id`/`user_id` mudou — `clearCacheTables()` roda de forma síncrona (`await`) antes de `db.session.put`, e as páginas só montam a árvore autenticada após `isAuthenticated:true` ser setado em seguida.
- **Pull inicial usa `last_sync_at` antigo?** Aqui está a lacuna real: `saveSession()` grava a nova sessão via `saveSession({..., last_sync_at: null, ...})` explicitamente no fluxo de `activate/page.tsx:125` (o payload de ativação já define `last_sync_at: null`). Ou seja, para o caminho de **ativação**, o cursor é corretamente resetado. Mas para o caminho de **apenas trocar de PIN/usuário dentro do mesmo tenant** (`loginWithPIN`, que não chama `saveSession`, apenas seta `isAuthenticated:true` sobre a sessão já existente — `session-store.ts:97-101`), não há pull forçado nem reset de cursor, porque a sessão (e portanto `last_sync_at`) é a mesma linha compartilhada — comportamento correto nesse caso, pois o tenant não mudou (ver Cenário F).
- **Cursor de sincronização por tenant?** Não existe cursor por tenant no backend — `DispositivoCampo.last_sync_at` é metadado informativo (`models.py:33-34`), não fonte de verdade; o cursor efetivo é sempre o parâmetro enviado pelo cliente (`router.py:503`). Como `saveSession()` já garante `last_sync_at: null` em toda nova ativação, este risco está coberto no caminho oficial de troca de tenant.
- **Pull substitui todos os dados ou só faz upsert?** Misto — `fazendas, talhoes, lotes, animais, insumos, safras, colaboradores, pessoas_operacionais, recomendacoes_climaticas, recomendacoes_operacionais` são `.clear()+.bulkPut()` a cada pull bem-sucedido (`pull.ts:243-375`) — mitigação redundante e bem-vinda. **`tasks` e `caderno_events` NÃO são recriados do zero** — apenas atualizados incrementalmente (`pull.ts:378-434, 444-496`). Se `clearCacheTables()` não tivesse rodado, essas duas tabelas reteriam registros do tenant anterior indefinidamente, mesmo após vários pulls.
- **Tombstones do novo tenant removem dados do tenant antigo?** Não — tombstones (`pull.ts`, payload `tombstones{talhoes,lotes,tarefas,insumos}`) são escopados ao tenant do token atual; não têm conhecimento de dados de outro tenant.
- **IDs iguais entre tenants podem sobrescrever registros?** Risco teórico presente nas tabelas de cache simples (`fazendas.id`, `talhoes.id` são UUIDs do backend, provavelmente globalmente únicos por serem PKs de tabelas com `tenant_id` próprio — colisão de UUID entre tenants é praticamente impossível na prática, não é o vetor real de risco).

---

## 4. Exposição visual

Verificado via `useLiveQuery` em `home/page.tsx:60-86` (padrão repetido em `sync/page.tsx`, `caderno/page.tsx`, `recomendacoes/page.tsx`, `campo/tarefa/[id]/page.tsx`, `campo/aplicacao|colheita|epi|pesagem|vacinacao/page.tsx`, `campo/reproducao/*`, `top-app-bar.tsx`):

```ts
const talhoes = useLiveQuery(() => db.talhoes.toArray(), []);
const tarefasPendentes = useLiveQuery(() => db.tasks..., []);
```

- **Nenhuma dessas queries filtra por `tenant_id`** — impossível filtrar, já que o campo não existe na maioria das tabelas.
- **Nenhuma verifica sessão ativa antes de consultar** — a leitura Dexie ocorre independente do estado de autenticação; a proteção é indireta (as tabelas estarem vazias após logout/troca).
- **Leitura antes da autenticação?** Tecnicamente as páginas `(campo)/*` estão sob o layout que checa sessão (`(campo)/layout.tsx`), mas a query Dexie em si não tem guarda própria.
- **Registros antigos podem aparecer brevemente?** Apenas na janela teórica entre uma falha parcial de `clearCacheTables()` (transação Dexie é atômica — falha total ou sucesso total, não parcial) e a próxima renderização — na prática, não há janela real dado que a transação é atômica e ocorre antes do novo `session.put`.
- **Permanecem indefinidamente?** Não, dado que `clearCacheTables()` está corretamente posicionado nos dois pontos de transição (`clearSession`, `saveSession` com mudança de tenant/user).

**Resposta direta:** *Após o Tenant A fazer logout, o Tenant B **não pode** visualizar dados locais do Tenant A pelas telas normais* — classificação: **IMPEDIDO PELO CÓDIGO**, condicionado à correção já aplicada em `clearCacheTables()`. Antes dessa correção (estado auditado em `SOIL-PLAN-EXEC-04A`), a classificação teria sido **CONFIRMADO**.

---

## 5. Risco de sincronização cruzada

- **Itens pendentes do Tenant A permanecem após logout?** Não — `sync_queue.clear()` faz parte de `clearCacheTables()` (session-store.ts:25,43).
- **O worker reprocessaria itens do Tenant A quando o Tenant B entra?** Não haveria itens para processar, pois a fila foi limpa.
- **O push usa o token atual ou o original?** Sempre o atual — `useSessionStore.getState().session` é lido em tempo real dentro de `pushSync()` (`push.ts:10`), nunca capturado antecipadamente.
- **O item da fila armazena `tenant_id`/`device_id`?** **Não** — confirmado em `db.ts:113-124` (tipo `SyncQueueItem`) e `push.ts:250-268` (`enqueueSync`). Esta é a lacuna de defesa em profundidade mais importante: a proteção real é 100% dependente da limpeza da fila na troca de sessão, sem nenhum campo redundante no próprio registro que permitisse ao backend (ou a uma auditoria futura) detectar um item "órfão" de outro tenant.
- **O backend rejeitaria um `server_id` de outro tenant?** Sim, confirmado — `_process_task` UPDATE filtra `TarefaCampo.id == server_id AND TarefaCampo.tenant_id == self.tenant_id` (`services/api/campo/service.py:1124-1129`); se não encontrar, retorna erro por item (`status="ERROR"`), sem vazamento.
- **Um item sem `server_id` (CREATE) poderia ser criado no Tenant B?** Sim, mas isso é o comportamento **correto e esperado** quando o item pertence de fato ao usuário atual — o ponto de risco não é a criação em si, mas sim se um `CREATE` com `client_id` remanescente do Tenant A (que nunca chegou a ser enviado) fosse reenviado sob o token do Tenant B: o backend simplesmente criaria uma **nova tarefa real no Tenant B**, com o conteúdo (payload de negócio) que pertencia ao contexto operacional do Tenant A. **Este é o pior cenário teórico** — e é justamente o que `clearCacheTables()` previne ao esvaziar `sync_queue` na troca de sessão.
- **`client_id` poderia ser aceito no tenant errado?** Sim — a deduplicação por `client_id` (`service.py:1049-1054`) é escopada dentro do tenant do token atual (a query já filtra por tenant implicitamente via `self.tenant_id` no service), então um `client_id` de um evento do Tenant A, se reenviado sob token do Tenant B, **não colidiria** com nada existente no Tenant B e seria aceito como uma criação nova e válida do ponto de vista do backend — sem forma de o backend saber que a informação pertencia a outro contexto.
- **Evidências/fotos antigas poderiam ser enviadas na sessão nova?** Sim, teoricamente, via o mesmo mecanismo — `caderno_events.evidencias[]` embutido seria enviado junto ao evento se o registro não tivesse sido limpo.
- **Erros de RLS são tratados como permanentes ou entram em retry?** Erros de negócio (incluindo "não encontrado" por violação de tenant) incrementam `attempts` e viram `FAILED` após 5 tentativas (`push.ts:98-104`) — não ficam em retry infinito, mas também não alertam o usuário sobre a causa real.

**Resposta direta à pergunta central da seção 6:** *A ausência de `tenant_id` nas filas, isoladamente (sem a limpeza), poderia criar dados reais no tenant autenticado incorreto* — não apenas causar rejeição. O RLS do backend protege contra **leitura/atualização** cruzada (`UPDATE` com `server_id` de outro tenant é rejeitado), mas **não protege contra `CREATE`**, porque um `CREATE` legítimo pelo tenant atual é indistinguível, do ponto de vista do backend, de um `CREATE` "vazado" de payload de outro contexto — o backend não tem como saber que o conteúdo do payload se originou de uma sessão anterior. A proteção real contra esse cenário está inteiramente no cliente (`clearCacheTables()`), não no servidor.

---

## 6. Dados locais não sincronizados — perda de trabalho no logout

- **Limpar tudo no logout causaria perda de trabalho?** Sim — `clearCacheTables()` apaga incondicionalmente `sync_queue`, `caderno_events` e `caderno_drafts`, **sem checar se há itens pendentes não sincronizados** (`status != "DONE"`).
- **Há aviso ao usuário?** Não encontrado — nenhuma confirmação/diálogo antes da limpeza.
- **Logout é bloqueado com pendências?** Não — `clearSession()` executa incondicionalmente.
- **Existe exportação ou sincronização obrigatória antes de sair?** Não encontrada.
- **Existe indicador de itens pendentes?** Sim, via `useSyncStore`/`pendingCount` exibido em `top-app-bar.tsx` (indicador "SYNC"), mas não é usado como gate para `clearSession`.
- **Existe "sair e manter dados" vs "sair e apagar dados"?** Não — comportamento único e incondicional.
- **Diferença entre logout normal e revogação de dispositivo?** Não há logout normal na UI (confirmado na auditoria anterior) — o único caminho é a detecção de dispositivo revogado/inválido, que já é um cenário em que preservar dados locais não tem valor prático (o dispositivo não pode mais sincronizá-los legitimamente sob a sessão antiga).

**Avaliação:** a correção aplicada prioriza segurança de isolamento sobre preservação de trabalho pendente. Isso é apropriado para o cenário atual (o único gatilho é revogação/invalidação, onde os dados pendentes já não têm caminho de sincronização válido), mas se um botão de "logout manual" for adicionado no futuro (ausente hoje), essa mesma lógica incondicional causaria perda silenciosa de trabalho de campo ainda não sincronizado — cenário coberto na seção 8 (Cenário B) e na recomendação final.

---

## 7. Cenários obrigatórios

| Cenário | Comportamento atual | Risco residual |
|---|---|---|
| **A — logout com tudo sincronizado** | `clearCacheTables()` limpa cache já sincronizado; Tenant B entra sem exposição | Baixo |
| **B — logout com tarefas pendentes** | Pendências são apagadas silenciosamente junto com o cache — **perda de trabalho**, sem aviso | Médio (perda de dados, não de confidencialidade) |
| **C — token expirado** | `validateDeviceSession()` só invalida a sessão se o backend responder 401/403/404; offline, mantém sessão local (`session-store.ts:58-61`) — retomada no mesmo tenant, não há substituição | Baixo |
| **D — dispositivo revogado** | Detectado no próximo request online; `clearSession()` roda; dados pendentes são perdidos (mesmo caso do B) | Médio |
| **E — reinstalação/limpeza do navegador** | IndexedDB e cache do SW são apagados pelo próprio navegador; sem recuperação — comportamento esperado, fora do controle do app | Baixo (não é falha do app) |
| **F — mesmo tenant, usuário diferente** | `loginWithPIN` não dispara `clearCacheTables()` (só compara em `saveSession`, não usado nesse fluxo) — dados de tarefas/caderno permanecem visíveis entre operadores do mesmo tenant | Depende da política esperada (ver abaixo) |
| **G — mesmo prestador atende vários tenants** | Só é possível via nova ativação (novo `device_id`/`tenant_id`), que já dispara `clearCacheTables()` corretamente | Baixo, condicionado à seção 9 |

**Cenário F merece atenção separada:** hoje, dois operadores do mesmo tenant que compartilham o dispositivo (comum em operação de campo, PIN por pessoa) **compartilham todo o cache e a fila de sincronização** — não há isolamento por `user_id` dentro do mesmo tenant. Isso pode ser intencional (dispositivo da fazenda, não do indivíduo) ou não — não há decisão de produto documentada em código sobre isso. Do ponto de vista de **confidencialidade entre tenants**, não é um risco; do ponto de vista de **atribuição de autoria/privacidade entre colegas**, é uma questão de produto a esclarecer, não um bug de segurança.

---

## 8. Modelo de dispositivo no backend

- `DispositivoCampo.tenant_id` é FK obrigatória (`models.py:15-17`) — todo dispositivo pertence a exatamente um tenant.
- `device_fingerprint` é `unique=True` globalmente, `nullable=True` (`models.py:23`) — impede dois registros **ativos** simultâneos com o mesmo fingerprint, mas não impede que o fingerprint seja liberado (`= None`) e reutilizado por um **novo registro de outro tenant**.
- **O dispositivo NÃO pode ser reativado para outro tenant** — confirmado: `reativar()` filtra por `tenant_id == self.tenant_id` do chamador autenticado (`service.py:166-171`); `ativar()` reafirma `device.tenant_id == self.tenant_id` do próprio registro encontrado pelo `activation_code` (`service.py:120-121`). Nenhum método altera `device.tenant_id`.
- O mesmo aparelho físico **pode** acabar com múltiplos registros `DispositivoCampo` ao longo do tempo (um por tenant que o utilizou), desde que o fingerprint tenha sido liberado — cada um é um `device_id` lógico distinto.
- Existe revogação (`status="REVOGADO"`, não detalhado nesta leitura mas coerente com o enum em `models.py:27-28`).
- **Não existe reset remoto/wipe local** — não encontrado nenhum comando do backend para instruir o Campo a limpar Dexie remotamente; a única forma de o cliente saber que precisa limpar é a detecção local de mudança de `tenant_id`/`user_id` em `saveSession()`.
- **O pull não carrega identificador de tenant/versão de escopo para comparação local** — o cliente nunca recebe de volta um `tenant_id` no payload de pull para autoconferência; confia inteiramente no que já tem localmente em `LocalSession`.

**Determinação:** o risco já é estruturalmente mitigado no nível certo — pelo **vínculo imutável do dispositivo a um tenant** no backend (opção 5, já é o contrato real) combinado com a **limpeza no ponto de troca de sessão local** (opção 1/2 parcial, já implementada). Não há evidência de que o backend precise de mudança para este risco específico.

---

## 9. Cache do Service Worker

`apps/campo/next.config.ts:10-19`:
```js
runtimeCaching: [{
  urlPattern: /^https?.*/,
  handler: "NetworkFirst",
  options: { cacheName: "campo-api-cache", networkTimeoutSeconds: 10, expiration: {...} }
}]
```

- O padrão `/^https?.*/` cacheia **qualquer requisição HTTP(S)**, sem exclusão de rotas de API — inclui `/api/v1/sync/pull`, `/api/v1/sync/push`, `/api/v1/campo/devices/me`, etc.
- **A chave de cache do Workbox não incorpora o header `Authorization`** — não encontrada nenhuma configuração de `cacheKeyWillBeUsed` ou plugin equivalente em `next.config.ts`. A chave padrão do Workbox é a URL completa (incluindo querystring).
- Como `pull.ts:205` inclui `device_id` e `last_sync_at` na querystring, requisições de dispositivos diferentes não colidem na mesma chave de cache — mas requisições do **mesmo `device_id`** (cenário de reativação dentro do mesmo tenant, ou teoricamente se o fingerprint fosse reaproveitado) poderiam, em tese, servir uma resposta cacheada anteriormente com um token diferente, caso a URL (incluindo `last_sync_at`) coincida.
- **`clearSession()`/`saveSession()` NÃO chamam `caches.delete()` ou qualquer API de invalidação do Workbox** — confirmado por ausência de qualquer referência a `caches.` ou `workbox` fora de `next.config.ts`.

**Resposta direta:** *sim, mesmo com o Dexie limpo, o service worker pode teoricamente devolver uma resposta em cache do tenant anterior*, se a aplicação estiver offline no momento da nova sessão e a URL requisitada coincidir com uma já cacheada (cenário de baixa probabilidade prática, dado que `device_id` normalmente muda entre tenants, mas não é impossível — ex.: mesmo `device_id` reativado dentro do mesmo tenant com outro usuário, cenário F). Este risco é **separado e não coberto** pela correção já aplicada em `clearCacheTables()`.

---

## 10. Opções de correção avaliadas

| Opção | Segurança | Complexidade | Risco de perda | Compatibilidade offline | Recomendação |
|---|---|---|---|---|---|
| 1 — `db.delete()`/clear total no logout | Alta | Baixa | Alta (destrói tudo, inclusive pendências) | Ruim se houver pendências | Não recomendado isoladamente |
| 2 — limpar só cache derivado, preservar fila/rascunhos | Média (fila sem tenant_id é um risco se preservada entre tenants) | Baixa-Média | Baixa | Boa | **Não recomendado como está** — preservar fila sem `tenant_id` é inseguro no cenário de troca de tenant; aceitável apenas se aplicado exclusivamente ao Cenário F (mesmo tenant) |
| 3 — banco por tenant/dispositivo (`campo_db_<tenant_id>_<device_id>`) | Muito alta | Alta (migração de todos os dados existentes, gestão de múltiplos bancos Dexie simultâneos) | Baixa | Boa | Excessivo para o risco residual atual |
| 4 — `tenant_id` em todas as tabelas + filtro obrigatório | Alta (defesa em profundidade real) | Média (migration Dexie v15, alterar todos os `useLiveQuery`) | Baixa | Boa | **Recomendado como melhoria futura**, não urgente dado que a limpeza já cobre o caso principal |
| 5 — dispositivo fixo a um tenant | Já é o contrato real (confirmado seção 9) | N/A | N/A | N/A | **Já implementado no backend** — apenas formalizar como invariante documentado |
| 6 — logout bloqueado com pendências | Média (não resolve confidencialidade, resolve perda de dados) | Baixa | Nenhuma (força sincronização antes) | Ruim se offline (usuário fica preso) | Recomendado combinar com aviso, não bloqueio duro |
| 7 — wipe seguro após confirmação (sincronizar → confirmar zero pendências → limpar → logout) | Alta | Baixa-Média | Nenhuma se online; requer fallback offline | Precisa de tratamento explícito para logout offline com pendências | **Melhor opção para cobrir a lacuna do Cenário B/D sem reabrir risco de confidencialidade** |

---

## 11. Testes existentes

| Área | Classificação | Evidência |
|---|---|---|
| `session-store.ts` / `clearCacheTables()` / troca de tenant | **NÃO COBERTO** | Nenhum arquivo `session-store.test.ts` encontrado |
| `db.ts` — schema/upgrade Dexie | COBERTO | `apps/campo/src/lib/__tests__/db.test.ts` |
| Isolamento por unidade produtiva (não tenant) | PARCIALMENTE COBERTO | `db.test.ts` — teste "não retorna Pessoas de outra Unidade" |
| `pull.ts` — merge/parsing de payload | COBERTO | `apps/campo/src/lib/sync/__tests__/pull.test.ts` |
| `pull.ts` — reset de cursor em nova sessão/tenant | NÃO COBERTO | Não encontrado |
| `push.ts` / fila / retry | NÃO COBERTO | Nenhum teste dedicado |
| Cache do Service Worker / Workbox | NÃO COBERTO | Nenhum teste encontrado |
| Dispositivo revogado / token expirado | NÃO COBERTO | Nenhum teste no client; backend fora do escopo desta leitura |
| Reativação para outro tenant (ponta a ponta) | NÃO COBERTO | Nenhum teste automatizado |

---

## 12. Matriz de risco

| Risco | Probabilidade | Impacto | Evidência | Severidade |
|---|---|---|---|---|
| Exposição visual de cache antigo (Dexie) | Baixa (mitigado por `clearCacheTables`) | Alto | §4, §0 | **BAIXA** (pós-correção; era CRÍTICA antes) |
| Envio de fila no tenant errado | Baixa (mitigado, mas sem defesa em profundidade — `sync_queue` sem `tenant_id`) | Crítico | §5 | **MÉDIA** (mitigado no ponto único de falha; sem redundância) |
| Perda de trabalho no logout (pendências apagadas) | Média (todo logout hoje é via revogação, mas cenário se agrava se logout manual for adicionado) | Médio | §6, §8 Cenário B/D | **MÉDIA** |
| Resposta antiga do Service Worker | Baixa-Média (depende de coincidência de URL + estar offline) | Médio | §9 | **MÉDIA** (risco não coberto pela correção existente) |
| Mistura de registros no pull (`tasks`/`caderno_events` sem full-replace) | Baixa (coberto pela limpeza na troca de sessão) | Médio | §3 | **BAIXA** |
| Vazamento de fotos/evidências | Baixa (evidências embutidas em `caderno_events`, limpo junto) | Alto | §0, §5 | **BAIXA** |
| Cursor incremental reaproveitado entre tenants | Baixa (ativação sempre reseta `last_sync_at: null`) | Médio | §3 | **BAIXA** |

---

## 13. Veredicto

**Opção C + E — exposição local impedida pelo código atual, mas com estratégia de transição incompleta.**

- A correção aplicada em `clearCacheTables()` **resolve o risco central** identificado nas auditorias anteriores: não há mais exposição visual nem envio cruzado de dados entre tenants no caminho oficial (ativação/revogação). Confirmado com evidência de código em todos os pontos de transição de sessão.
- Permanece uma **lacuna de perda de trabalho** (Opção E) — a limpeza é incondicional e não avisa/bloqueia quando há pendências reais não sincronizadas, o que é aceitável hoje (único gatilho é revogação/invalidação, onde as pendências já não têm caminho válido), mas é uma bomba-relógio caso um botão de logout manual seja adicionado sem essa consideração.
- Permanece uma **lacuna de defesa em profundidade**: `sync_queue`/`tasks`/a maioria das tabelas não carregam `tenant_id` próprio — a proteção é 100% pontual (limpeza no momento certo), sem redundância que pegue uma falha de outro tipo (ex. um dev remover `clearCacheTables()` num refactor futuro sem perceber a implicação de segurança).
- O **Service Worker/Workbox permanece fora do escopo da correção aplicada** — risco médio, separado do Dexie, não tratado.

---

## 14. Próximo passo recomendado (menor correção segura, não implementar)

**Prioridade 1 (segurança, defesa em profundidade — baixo custo):** adicionar comentário/invariante documentado no código (`session-store.ts`, próximo a `clearCacheTables()`) explicitando que a ausência de `tenant_id` em `sync_queue`/`tasks` torna essa função o único ponto de proteção contra vazamento cruzado — para que futuras alterações não a removam inadvertidamente. Não é uma mudança de schema, apenas reforço de intenção no código existente.

**Prioridade 2 (perda de dados — Cenário B/D):** antes de `clearCacheTables()` rodar dentro de `clearSession()`, verificar se `sync_queue`/`caderno_events` têm itens pendentes (`status != "DONE"`) e, se houver, expor essa contagem para a tela de ativação/revogação avisar o usuário que dados serão perdidos — sem bloquear o fluxo (pois o dispositivo já foi invalidado pelo backend, não há alternativa segura de preservação). Arquivo provável: `session-store.ts` (nova checagem antes do clear) + tela `activate/page.tsx` (exibir aviso vindo de `reasonMessage`).

**Prioridade 3 (cache HTTP, risco médio separado):** avaliar restringir o `runtimeCaching` de `next.config.ts` para não usar `NetworkFirst` em rotas `/api/v1/*` sensíveis (ou usar `NetworkOnly` para elas), preservando cache apenas para assets estáticos. Isso é mudança de configuração PWA — fora do que foi pedido para implementar nesta etapa, apenas mapeado como próximo passo.

**Não é necessária:** migration Dexie (schema v15), banco por tenant, nem mudança no backend — o modelo de dispositivo já garante o vínculo imutável a um tenant (Opção 5 já é o contrato real), e a correção já aplicada no frontend cobre o vetor de risco principal. Testes mínimos recomendados para cobrir a lacuna da seção 11: um teste de `session-store.ts` simulando troca de `tenant_id`/`user_id` e verificando que todas as 15 tabelas ficam vazias após `saveSession`/`clearSession`.

Nenhuma dessas três prioridades foi implementada nesta etapa — apenas mapeadas, conforme solicitado.

---

## Validações executadas

```bash
$ pnpm --filter @agro/campo typecheck
> tsc --noEmit
(sem erros)

$ pnpm --filter @agro/campo lint
> eslint src --ext .ts,.tsx
(sem erros)

$ git status --short
 M apps/campo/src/lib/stores/session-store.ts   # alteração da etapa anterior, não desta auditoria
 (demais arquivos modificados são pré-existentes ao início desta sessão)

$ git diff --check
(sem saída — sem problemas de whitespace/conflito)
```

O único arquivo novo criado nesta etapa é este relatório.
