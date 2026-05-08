# CAMPO PWA-06 — Validação Real: Tarefas Programadas

**Branch:** `feature/campo-pwa-06-validacao-tarefas`  
**Data:** 2026-05-08  
**Objetivo:** Validar o fluxo completo gestor → operador → sincronização em dispositivo real.

---

## Ambiente de Teste

| Item | Valor |
|---|---|
| Dispositivo principal | Android (Chrome) |
| Dispositivo secundário | — |
| Versão do app | PWA-05 |
| Backend | http://localhost:8000 |
| Rede | Wi-Fi + simulação offline |

---

## Ajustes Aplicados Antes dos Testes

| # | Arquivo | Problema | Correção |
|---|---|---|---|
| A1 | `home/page.tsx` | `filter().reverse()` sem índice → ordem de criação não garantida | Substituído por `orderBy("created_at").reverse().filter(...)` |

---

## Cenários de Teste

### GRUPO 1 — Criação no Backoffice

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 1.1 | Criar tarefa agrícola | apps/web → /operacional/campo/tarefas → Nova Tarefa → preencher título, tipo Aplicação, fazenda, data de hoje, prioridade Alta → Salvar | Tarefa aparece na lista com status "Pendente" e prioridade "Alta" | | |
| 1.2 | Criar tarefa com data futura | Mesmo fluxo com data +3 dias | Aparece em "Futuras" na lista do backoffice | | |
| 1.3 | Criar tarefa sem talhão | Deixar campo Talhão em branco → Salvar | Salva sem erro | | |
| 1.4 | Criar tarefa com dispositivo específico | Selecionar dispositivo no drawer | `dispositivo_id` preenchido; só esse dispositivo recebe no pull | | |
| 1.5 | Validação de campos obrigatórios | Tentar salvar sem título | Mensagem de erro no campo | | |

---

### GRUPO 2 — Recebimento no PWA (sync/pull)

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 2.1 | Pull com Wi-Fi | Abrir PWA com Wi-Fi → aguardar sync automático | Tarefa de hoje aparece na seção "Para Hoje" da Home | | |
| 2.2 | Tarefa futura não aparece | Criar tarefa com data +5 dias → pull | NÃO deve aparecer na Home do PWA | | |
| 2.3 | Tarefa atrasada aparece | Criar tarefa com data -1 dia → pull | Aparece na seção "Atrasadas" com destaque | | |
| 2.4 | Pull manual via /sync | Ir em /sync → "Sincronizar Agora" | Seção pendentes zerada; tarefa aparece na Home | | |
| 2.5 | Pull sem last_sync_at | Primeiro sync do dispositivo | Todas as tarefas ativas carregadas | | |

---

### GRUPO 3 — Execução Offline

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 3.1 | Iniciar tarefa offline | Desativar Wi-Fi → Home → tocar tarefa → "Iniciar Tarefa" | Status muda para "Em Execução" na Home; `iniciada_em` preenchido localmente | | |
| 3.2 | Concluir tarefa com obs + foto + GPS | Na tarefa EM_EXECUCAO → preencher observação → tirar foto → aguardar GPS → "Concluir Tarefa" | Tela retorna para Home; tarefa some das seções ativas; item enfileirado no outbox | | |
| 3.3 | Concluir sem iniciar (regra de negócio) | Tentar concluir tarefa PENDENTE (sem clicar Iniciar) | Botão "Concluir" não aparece; apenas "Iniciar" visível | | |
| 3.4 | Cancelar tarefa | Tarefa PENDENTE → "Cancelar tarefa" | Tarefa some da Home; item de cancelamento enfileirado | | |
| 3.5 | Cancelar tarefa EM_EXECUCAO | Iniciar tarefa → Cancelar | Tarefa cancelada; item enfileirado | | |
| 3.6 | Múltiplas tarefas offline | Desativar Wi-Fi → iniciar e concluir 3 tarefas diferentes | Todas enfileiradas no outbox sem perda de dados | | |
| 3.7 | Tarefa de outro operador | Criar tarefa com `operador_id` diferente do dispositivo logado | Badge "Minha tarefa" ausente; botões de ação bloqueados | | |

---

### GRUPO 4 — Sincronização (sync/push)

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 4.1 | Sync automático ao reconectar | Executar ações offline → reativar Wi-Fi | Banner verde "Conexão restaurada" → sync automático dispara → pendentes zeram | | |
| 4.2 | Sync manual | Ir em /sync → "Sincronizar Agora" | Status muda para "Sincronizando..." → "Sincronizado" | | |
| 4.3 | Status atualizado no backoffice | Após sync bem-sucedido → apps/web → /campo/tarefas | Status da tarefa = "Concluída" com `concluida_em` preenchido | | |
| 4.4 | Retry de item FAILED | Forçar falha de rede durante push → ir em /sync → clicar "Tentar novamente" | Item reenviado e processado | | |
| 4.5 | Conexão instável (3G fraco) | Ativar throttling no DevTools → executar sync | Não perde dados; retry automático se necessário | | |

---

### GRUPO 5 — Regras de Negócio

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 5.1 | Transição inválida PENDENTE → CONCLUIDA | Via API: `PATCH /campo/tarefas/{id}/execucao` com `status_execucao=CONCLUIDA` em tarefa PENDENTE | HTTP 422 "Só é possível CONCLUIR uma tarefa que está EM_EXECUCAO" | | |
| 5.2 | Tarefa atrasada aparece corretamente | Data programada = ontem, status = PENDENTE | Aparece na seção "Atrasadas" (não em "Para Hoje") | | |
| 5.3 | Tarefa futura não aparece no PWA | Data programada = amanhã | NÃO aparece na Home do PWA (filtro data_programada <= hoje) | | |
| 5.4 | Tarefas manuais inalteradas | Registrar aplicação manualmente | Aparece em "Registros Offline"; NÃO aparece em seções de tarefas programadas | | |
| 5.5 | Retrocompatibilidade pull | Tarefas manuais criadas antes do PWA-05 | `status_execucao=CONCLUIDA` retroativo; não aparecem mais no pull | | |

---

### GRUPO 6 — Modo Totalmente Offline

| # | Cenário | Passos | Esperado | Resultado | Observação |
|---|---|---|---|---|---|
| 6.1 | App abre sem internet | Desativar Wi-Fi → abrir PWA frio | Banner offline visível; tarefas cacheadas aparecem normalmente | | |
| 6.2 | Ciclo completo offline | Sem internet desde o início → ver tarefas → iniciar → concluir | Tudo funciona localmente; outbox acumula | | |
| 6.3 | Crash recovery | Iniciar tarefa → forçar fechamento do app | Ao reabrir, item IN_FLIGHT volta para PENDING automaticamente | | |
| 6.4 | Dados não perdidos após sync | Concluir offline com foto → reconectar → sync | Foto e obs chegam no servidor | | |

---

## Problemas Encontrados

| # | Data | Descrição | Severidade | Status | Correção |
|---|---|---|---|---|---|
| P1 | 2026-05-08 | `filter().reverse()` na home sem índice → ordem não garantida | Média | ✅ Corrigido (A1) | `orderBy("created_at").reverse().filter(...)` |
| | | | | | |

---

## Conclusão

- [ ] Grupo 1 (Criação backoffice): APROVADO / REPROVADO
- [ ] Grupo 2 (Recebimento PWA): APROVADO / REPROVADO
- [ ] Grupo 3 (Execução offline): APROVADO / REPROVADO
- [ ] Grupo 4 (Sincronização): APROVADO / REPROVADO
- [ ] Grupo 5 (Regras de negócio): APROVADO / REPROVADO
- [ ] Grupo 6 (Modo offline total): APROVADO / REPROVADO

**Resultado geral:** — / APROVADO / REPROVADO COM RESSALVAS / REPROVADO

**Testador:** ___________  
**Data:** ___________  
**Dispositivo:** ___________
