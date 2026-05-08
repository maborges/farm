# CAMPO PWA-06 — Validação Real: Tarefas Programadas

**Branch:** `feature/campo-pwa-06-validacao-tarefas`  
**Data:** 2026-05-08  
**Método:** Revisão estática de código (rastreamento fluxo a fluxo por arquivo)  
**Motivo:** Ambiente WSL2 sem browser/dispositivo disponível; Playwright não instalado por decisão do projeto.

---

## Ambiente de Teste

| Item | Valor |
|---|---|
| Método | Revisão estática de código + simulação de fluxo |
| Arquivos analisados | pull.ts, push.ts, task-factory.ts, home/page.tsx, tarefa/[id]/page.tsx, service.py, schemas.py, models.py |
| TypeScript | `tsc --noEmit` → 0 erros (apps/campo + apps/web) |
| Validação em dispositivo real | Pendente (necessário confirmar com Android/Chrome) |

---

## Bugs Encontrados e Corrigidos

| # | Severidade | Arquivo | Descrição | Correção |
|---|---|---|---|---|
| B1 | **P0** | `lib/sync/pull.ts` | Tombstone atualizava `status: "CANCELADA"` — campo ignorado pelas queries da home que filtram por `status_execucao`. Tarefa deletada no servidor continuava visível no PWA. | Corrigido para `status_execucao: "CANCELADA"` |
| B2 | **P1** | `app/(campo)/home/page.tsx` | Tarefa atrasada em `EM_EXECUCAO` aparecia em duas seções simultaneamente: "Atrasadas" e "Em Execução". | Filtro de atrasadas agora exige apenas `status_execucao === "PENDENTE"` |
| B3 | **P1** | `app/(campo)/home/page.tsx` | `filter().reverse()` sem índice não garantia ordem cronológica nos Registros Offline. | Corrigido para `orderBy("created_at").reverse().filter(...)` (fix aplicado no PWA-06) |

---

## Cenários de Teste

### GRUPO 1 — Criação no Backoffice

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 1.1 | Criar tarefa agrícola com todos os campos | ✅ APROVADO | `TarefaProgramadaCreate` valida campos obrigatórios; `POST /campo/tarefas` salva com `origem=PROGRAMADA`, `status_execucao=PENDENTE` |
| 1.2 | Criar tarefa com data futura | ✅ APROVADO | Data persiste corretamente; pull filtra `data_programada <= hoje`, então não aparece no PWA |
| 1.3 | Criar tarefa sem talhão | ✅ APROVADO | `area_rural_id` é nullable no schema e no model |
| 1.4 | Criar com dispositivo específico | ✅ APROVADO | `dispositivo_id` nullable; pull filtra `dispositivo_id == None OR dispositivo_id == device.id` |
| 1.5 | Validação de campos obrigatórios | ✅ APROVADO | Zod: `titulo min(3)`, `data_programada min(1)`, `unidade_produtiva_id uuid` — form bloqueia envio |

---

### GRUPO 2 — Recebimento no PWA (sync/pull)

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 2.1 | Pull com Wi-Fi — tarefa de hoje aparece | ✅ APROVADO | `data_programada <= hoje AND status_execucao IN (PENDENTE, EM_EXECUCAO)` — tarefa mapeada no IndexedDB com `id = String(server_id)` |
| 2.2 | Tarefa futura não aparece no PWA | ✅ APROVADO | Filtro backend `data_programada <= hoje` exclui tarefas futuras corretamente |
| 2.3 | Tarefa atrasada aparece em seção própria | ✅ APROVADO | Home filtra `data_programada < hoje AND status_execucao === PENDENTE` → seção "Atrasadas" |
| 2.4 | Pull manual via /sync | ✅ APROVADO | `runSync()` → `pushSync()` + `pullSync()` em sequência; `last_sync_at` atualizado após sucesso |
| 2.5 | Primeiro sync sem last_sync_at | ✅ APROVADO | `last_sync_at` nulo → sem filtro de tombstones; todas tarefas ativas carregadas |

---

### GRUPO 3 — Execução Offline

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 3.1 | Iniciar tarefa offline | ✅ APROVADO | `executarTarefa(id, {status_execucao: "EM_EXECUCAO"})` → `db.tasks.update` + `enqueueSync("UPDATE", ...)` com `server_id`; `useLiveQuery` reatualiza UI |
| 3.2 | Concluir com obs + foto + GPS | ✅ APROVADO | `changes.fotos`, `changes.dados.obs_execucao`, `changes.localizacao_status`, `changes.concluida_em` todos preenchidos antes de `db.tasks.update` |
| 3.3 | Bloquear CONCLUIR sem INICIAR | ✅ APROVADO | `canFinish = status_execucao === "EM_EXECUCAO"` — botão "Concluir" só renderiza se `canFinish === true` |
| 3.4 | Cancelar tarefa PENDENTE | ✅ APROVADO | `handleCancelar` → `executarTarefa(id, {status_execucao: "CANCELADA"})` → `router.replace("/home")` |
| 3.5 | Cancelar tarefa EM_EXECUCAO | ✅ APROVADO | `isDone` = false enquanto EM_EXECUCAO; cancelamento permitido; enfileirado no outbox |
| 3.6 | Múltiplas tarefas offline | ✅ APROVADO | Cada `executarTarefa` adiciona item separado ao `sync_queue`; FIFO de 50 itens por push |
| 3.7 | Tarefa de outro operador — somente leitura | ✅ APROVADO | `isMinhasTarefa = !operador_id OR operador_id === session.user_id`; botões não renderizados quando false |

---

### GRUPO 4 — Sincronização (sync/push)

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 4.1 | Sync automático ao reconectar | ✅ APROVADO | `initSyncListeners` ouve `window.addEventListener("online")` → `runSync()`; `OfflineBanner` mostra "Conexão restaurada" por 3s |
| 4.2 | Sync manual via /sync | ✅ APROVADO | Botão chama `runSync()`; status muda `idle → syncing → success` via `useSyncStore` |
| 4.3 | Status atualizado no backoffice | ✅ APROVADO | `_process_task` UPDATE → `_aplicar_status_execucao` → flush; `GET /campo/tarefas` retorna status atualizado |
| 4.4 | Retry de item FAILED | ✅ APROVADO | `/sync/page.tsx` chama `db.sync_queue.update(id, {status: "PENDING", attempts: 0})` → `runSync()` |
| 4.5 | Conexão instável | ✅ APROVADO | Push falha → `catch` reverte `IN_FLIGHT → PENDING`; próximo sync retenta automaticamente |

---

### GRUPO 5 — Regras de Negócio

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 5.1 | PENDENTE → CONCLUIDA bloqueado (API) | ✅ APROVADO | `_aplicar_status_execucao`: `if task.status_execucao != "EM_EXECUCAO": raise BusinessRuleError(...)` → HTTP 422 |
| 5.2 | Tarefa atrasada na seção correta | ✅ APROVADO | `data_programada < hoje AND status_execucao === PENDENTE` → seção "Atrasadas" (após B2 corrigido) |
| 5.3 | Tarefa futura não aparece no PWA | ✅ APROVADO | Filtro pull `data_programada <= hoje` bloqueia no servidor; não entra no IndexedDB |
| 5.4 | Tarefas manuais isoladas | ✅ APROVADO | `origem === "MANUAL"` aparece apenas em "Registros Offline"; queries das seções programadas filtram `where("origem").equals("PROGRAMADA")` |
| 5.5 | Retrocompatibilidade — tarefas antigas | ✅ APROVADO | Migration UPDATE: `SET status_execucao = 'CONCLUIDA' WHERE origem = 'MANUAL'`; db.ts v2 upgrade: `if (!t.status_execucao) t.status_execucao = "CONCLUIDA"` |

---

### GRUPO 6 — Modo Totalmente Offline

| # | Cenário | Resultado | Observação |
|---|---|---|---|
| 6.1 | App abre sem internet | ✅ APROVADO | `OfflineBanner` ativo; tarefas do IndexedDB renderizadas via `useLiveQuery` sem HTTP |
| 6.2 | Ciclo completo offline | ✅ APROVADO | `executarTarefa` → `db.tasks.update` + `enqueueSync` → outbox acumula → sync ao reconectar |
| 6.3 | Crash recovery IN_FLIGHT | ✅ APROVADO | `recoverInFlight()` chamado no mount do layout; reseta `IN_FLIGHT → PENDING` antes do primeiro sync |
| 6.4 | Foto + obs chegam no servidor | ✅ APROVADO | `changes.fotos = [...task.fotos, ...payload.fotos]` antes de `db.tasks.update`; payload do push inclui `fotos` e `obs` |

---

## Pontos para Confirmação em Dispositivo Real

| # | Ponto | Por quê confirmar |
|---|---|---|
| D1 | GPS capturado dentro de 8s no campo | `useGps` tem timeout de 8s; em áreas rurais a captura pode ser mais lenta |
| D2 | Câmera abre corretamente no Android Chrome | `useCamera` usa `capture="environment"`; comportamento varia por fabricante |
| D3 | PWA instalável (manifest + service worker) | Verificar se o Chrome oferece "Adicionar à tela inicial" |
| D4 | Sync automático ao reconectar no 4G | Evento `online` em rede celular pode ser atrasado em alguns dispositivos Android |
| D5 | Dexie v2 upgrade não trava app em primeira abertura | Upgrade migra tasks existentes; testar com volume > 100 registros |

---

## Conclusão — Revisão Estática

- [x] Grupo 1 (Criação backoffice): **APROVADO**
- [x] Grupo 2 (Recebimento PWA): **APROVADO**
- [x] Grupo 3 (Execução offline): **APROVADO**
- [x] Grupo 4 (Sincronização): **APROVADO**
- [x] Grupo 5 (Regras de negócio): **APROVADO**
- [x] Grupo 6 (Modo offline total): **APROVADO**

**Resultado geral:** APROVADO COM RESSALVAS

**Ressalvas:** 3 bugs corrigidos (B1–B3). 5 pontos (D1–D5) requerem confirmação em dispositivo Android real antes de release para produção.

**Método:** Revisão estática de código  
**Data:** 2026-05-08

---

## GRUPO 7 — Validação em Dispositivo Android Real

> **Instruções ao testador:**  
> 1. Prepare o backend com o script: `python scripts/campo_seed_validacao.py --base-url http://<IP_LOCAL>:8000/api/v1 --token <JWT> --fazenda-id <UUID>`  
> 2. Abra o PWA no Chrome Android: `http://<IP_LOCAL>:3002`  
> 3. Instale o PWA ("Adicionar à tela inicial") antes dos testes D3 e D4  
> 4. Preencha a tabela abaixo com os resultados reais  

### Informações do Dispositivo

| Campo | Valor |
|---|---|
| Dispositivo | _(ex: Samsung Galaxy A54)_ |
| Versão Android | _(ex: Android 14)_ |
| Versão Chrome | _(ex: Chrome 124.0)_ |
| Rede | _(ex: Wi-Fi 5GHz / 4G LTE)_ |
| Data do teste | __________________ |
| Testador | __________________ |

---

### Cenários D1–D5

| # | Cenário | Procedimento | Resultado | Observações |
|---|---|---|---|---|
| D1 | GPS capturado em até 15s no campo | Abrir tarefa → aguardar badge GPS ficar verde → cronometrar | ⬜ APROVADO / ⬜ REPROVADO / ⬜ PARCIAL | Tempo observado: ____s |
| D2 | Câmera abre corretamente no Android Chrome | Abrir tarefa → tocar "Adicionar Foto" → verificar câmera traseira abre | ⬜ APROVADO / ⬜ REPROVADO / ⬜ PARCIAL | Fabricante pode precisar de permissão manual |
| D3 | PWA instalável (manifest + service worker) | Chrome menu → "Adicionar à tela inicial" → confirmar ícone aparece | ⬜ APROVADO / ⬜ REPROVADO / ⬜ PARCIAL | Chrome deve exibir banner de instalação |
| D4 | Sync automático ao reconectar no 4G | (a) Desligar Wi-Fi+dados → executar tarefa offline → (b) religar dados → aguardar sync automático | ⬜ APROVADO / ⬜ REPROVADO / ⬜ PARCIAL | Evento `online` pode demorar 5–10s em 4G |
| D5 | Dexie v2 upgrade não trava em primeira abertura | Limpar dados do site → abrir PWA → verificar home carrega sem tela branca | ⬜ APROVADO / ⬜ REPROVADO / ⬜ PARCIAL | Checar Console DevTools por erros de upgrade |

---

### Falhas Encontradas

| # | Severidade | Descrição | Reprodução | Status |
|---|---|---|---|---|
| — | — | _(preencher se houver)_ | — | — |

---

### Conclusão Final (Android)

- [ ] D1 GPS: ________________
- [ ] D2 Câmera: ________________
- [ ] D3 PWA instalável: ________________
- [ ] D4 Sync 4G: ________________
- [ ] D5 Dexie upgrade: ________________

**Resultado Android:** ⬜ APROVADO  ⬜ APROVADO COM RESSALVAS  ⬜ REPROVADO

**Release autorizado para produção:** ⬜ SIM  ⬜ NÃO — aguardar correção de: ________________

**Assinatura do testador:** ________________  **Data:** __________________
