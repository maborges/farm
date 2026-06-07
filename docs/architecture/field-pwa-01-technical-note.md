# FIELD-PWA-01 - Nota Técnica

## Estrutura do documento

- Parte 1: arquitetura e decisões do PWA de Campo
- Runbook operacional separado em [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md:1)

---

## Parte 1 - Arquitetura do PWA de Campo

### Mapeamento do estado atual

### O que já existe

- `apps/campo/src/lib/db.ts` usa IndexedDB com `Dexie` para:
  - sessão local
  - tarefas locais
  - fila de sincronização genérica (`sync_queue`)
  - caches de fazendas, talhões, lotes e insumos
- `apps/campo/src/lib/sync/push.ts` envia a fila local para o backend em lotes e trata sucesso, conflito e falha.
- `apps/campo/src/lib/sync/pull.ts` hidrata o cache local com dados do backend.
- `apps/campo/src/lib/sync/worker.ts` executa sync automático ao ficar online e recupera itens `IN_FLIGHT`.
- `apps/campo/src/lib/task-factory.ts` cria tarefas locais primeiro e depois enfileira sync.
- `apps/campo/src/app/(campo)/layout.tsx` ativa listeners de sync e recuperação de fila.
- `apps/campo/src/app/(campo)/home/page.tsx` já opera como shell de campo, mas ainda orientado a tarefas e registros manuais.
- `apps/campo/src/app/(campo)/caderno/page.tsx` já oferece UI offline de caderno com:
  - captura de eventos locais
  - seleção de safra e talhão
  - anexos por câmera
  - uso de GPS
  - histórico local recente
- `apps/campo/src/lib/caderno-offline.ts` já mantém o fluxo local-first do caderno:
  - criação de evento offline
  - normalização mínima de payload
  - enfileiramento na outbox
  - retry de eventos com erro

### O que faltava originalmente para o FIELD-PWA-01

- contrato documental offline para eventos do caderno
- persistência local específica para eventos canônicos do caderno
- endpoint incremental para enviar eventos PWA_OFFLINE ao backend oficial
- resposta de sync por evento com `local_id`, `server_id`, `status` e erro
- persistência de `device_id`, `client_created_at` e `client_updated_at`
- contrato de idempotência por dispositivo + identificador local

### Decisão adotada

O PWA passa a manter uma outbox específica para eventos do caderno, sem substituir a fila de tarefas existente.

### Observações importantes

- O ciclo deixou de ser somente infra de sync.
- O Campo já possui UI funcional de caderno offline, embora ainda parcial em cobertura de casos.
- A proveniência offline é preservada como `PWA_OFFLINE` com técnica `SYNC_PWA`.
- Eventos críticos permanecem sujeitos à aprovação posterior no backend.

### Situação atual do FIELD-PWA-01

O objetivo estrutural do FIELD-PWA-01 foi parcialmente entregue.

Hoje o módulo Campo já possui:

- contrato offline para eventos do caderno
- persistência local dedicada em `caderno_events`
- outbox específica via `sync_queue`
- endpoint incremental de sincronização para o caderno
- UI operacional para captura offline e consulta do histórico local recente

O que ainda existe não é mais um gap arquitetural primário, e sim um conjunto de pendências de robustez, cobertura funcional e refinamento de UX offline.

### Gaps atuais que ainda precisam ser tratados

#### 1. Robustez do sync offline

- o bug que contaminava `caderno_events` durante `pushTaskSync()` foi corrigido
- a recuperação de `IN_FLIGHT` agora também restaura eventos do caderno presos em `SYNCING` para `PENDING`
- ainda faltam melhorias de observabilidade e operação:
  - telemetria de falhas
  - visibilidade de itens em quarentena
  - indicadores mais claros de retomada automática após interrupção

#### 2. Cobertura funcional do caderno

- a modelagem local suporta um conjunto maior de tipos canônicos, mas a UI atual expõe apenas um subconjunto em `PWA_CADERNO_EVENT_TYPES`
- isso é suficiente para um primeiro ciclo, mas ainda não cobre todo o espaço operacional esperado do caderno oficial
- falta definir quais tipos:
  - entram no próximo ciclo
  - exigem payload específico
  - dependem de validações adicionais antes da sincronização

#### 3. Multi-fazenda e contexto operacional

- o caderno agora já força a seleção explícita da unidade produtiva antes de avançar no fluxo
- isso resolve o erro mais crítico de contexto dentro do registro offline do caderno
- ainda falta avaliar se o Campo deve ter um contexto de fazenda ativa global, reaproveitado por outros módulos além do caderno

#### 4. Resiliência da experiência offline

- o formulário do caderno ainda não possui draft local ou autosave
- se o operador fechar o app durante o preenchimento, perde:
  - descrição
  - observações
  - anexos ainda não persistidos no evento final
- a recomendação é adicionar persistência transitória local para formulários em andamento

#### 5. Qualidade de produto e UX mobile

- a base mobile-first já está presente, mas ainda faltam melhorias de experiência para uso contínuo em campo:
  - persistência de rascunho entre etapas
  - feedback mais claro de sincronização por item
  - indicação mais forte de estados offline/online
  - retomada mais clara de registros com erro
  - redução de atrito para captura repetitiva no caderno
- o fluxo de ativação, shell principal e wizard do caderno já evoluíram, mas o restante do app ainda precisa do mesmo nível de acabamento visual e operacional

#### 6. Consistência do contrato local

- existe drift entre parte do schema IndexedDB e algumas tipagens auxiliares
- o caso mais claro hoje é a divergência entre `categoria` e `tipo` em estruturas relacionadas a insumos
- isso não bloqueia o FIELD-PWA-01, mas aumenta risco de inconsistência futura em filtros, índices e serialização

### Prioridade recomendada

Ordem sugerida de implementação:

1. adicionar draft/autosave no formulário do caderno
2. ampliar gradualmente os tipos de evento suportados pela UI
3. reforçar feedback operacional de sync e retomada de erro
4. decidir se haverá contexto global de fazenda ativa no Campo
5. revisar consistência entre schema local, tipagens e contratos de sync

### Estado do backlog de migrations e branches

- o problema de conexão do Alembic no ambiente local foi corrigido em `services/api/migrations/env.py`, removendo a combinação de `NullPool` com `server_settings` que fazia a conexão expirar
- o ambiente ainda pode apresentar múltiplos heads de migration, pois o histórico do projeto ficou dividido em branches distintos
- no estado observado durante esta análise, os heads relevantes eram:
  - `20260524_frota_step08`
  - `20260527_field_pwa01`
  - `step45_tarefas_invalidacao`
- esse backlog não representa um novo gap arquitetural do Campo; ele reflete a necessidade de aplicar e alinhar a árvore de migrations em uma janela controlada
- a branch `step45_tarefas_invalidacao` pertence à governança documental de tarefas e deve ser tratada separadamente do escopo FIELD-PWA-01
- a nota técnica do PWA não deve misturar:
  - entrega funcional do app Campo
  - integridade documental de tarefas
  - estado operacional do banco de migrations

### Atualização do PWA já instalado sem perder validação

O aplicativo de Campo pode ser atualizado sem reinstalação e sem perder a validação do dispositivo, desde que a atualização preserve o armazenamento local do navegador e o mesmo endereço de publicação.

#### O que precisa permanecer estável

- mesmo domínio e protocolo do PWA instalado
- mesmo `start_url` e mesmo escopo do aplicativo
- mesma base local do navegador:
  - `IndexedDB`
  - `localStorage`
  - caches do `service worker`
- mesma estrutura de persistência da sessão local

No estado atual, a validação local do dispositivo depende principalmente de:

- `apps/campo/src/lib/db.ts`
  - store `session`
  - stores de tarefas, caderno e fila offline
- `apps/campo/src/lib/stores/session-store.ts`
  - leitura e persistência de `device_id`, `device_token`, `pin_hash`, `tenant_id`, `user_id`, `user_name`, `fazenda_ids`, `modules`

Na prática, isso significa que publicar um novo build no mesmo endereço **não deve exigir nova ativação**, desde que os dados locais não sejam apagados e que o backend continue aceitando o `device_token`.

#### O que não deve ser feito em uma atualização

- não pedir para o usuário desinstalar o PWA
- não orientar limpeza de dados do site ou do navegador
- não mudar o domínio ou subdomínio do Campo sem plano de migração
- não trocar o nome do banco local ou das stores sem migração explícita
- não apagar o `IndexedDB` em rotinas de bootstrap ou upgrade
- não invalidar sessão local por falha transitória de rede ou `5xx`

Essas ações podem remover:

- sessão do dispositivo
- fila offline pendente
- tarefas ainda não sincronizadas
- eventos do caderno ainda locais

#### Como a atualização deve ser publicada

1. gerar novo build do PWA
2. publicar no mesmo domínio e no mesmo caminho do aplicativo
3. manter `manifest`, `start_url` e escopo compatíveis
4. permitir que o `service worker` baixe a nova versão
5. reabrir o app instalado para ativar o build atualizado

No projeto atual:

- `apps/campo/next.config.ts` usa `next-pwa`
- o `service worker` é registrado automaticamente
- o modo recomendado para teste de instalação continua sendo `build` + `start`, ou `ENABLE_PWA_DEV=true` para cenário controlado de desenvolvimento

#### Regras para evolução do banco local

Atualizações que alteram persistência local devem ser feitas por migração incremental, nunca por recriação do banco.

Regras:

- usar `db.version(...).stores(...)` em `apps/campo/src/lib/db.ts`
- adicionar stores ou índices por nova versão do Dexie
- migrar dados existentes com `upgrade(...)` quando necessário
- manter compatibilidade de leitura com a versão anterior durante a transição
- nunca chamar exclusão total do banco como estratégia de upgrade

Objetivo da migração:

- preservar `session`
- preservar `tasks`
- preservar `caderno_events`
- preservar `sync_queue`
- preservar caches locais usados pelo PWA

#### Comportamento esperado no dispositivo já validado

Quando a atualização é publicada corretamente:

1. o usuário mantém o app instalado
2. o app continua usando a mesma sessão local
3. o `service worker` detecta a nova versão
4. o código atualizado passa a ser servido na próxima abertura ou refresh controlado
5. o dispositivo continua validado sem nova ativação

#### Quando a reativação pode voltar a ser exigida

Mesmo com atualização correta, a nova ativação pode ser necessária se:

- o dispositivo foi revogado no backend
- o token realmente expirou
- os dados locais do site foram apagados
- o PWA foi desinstalado
- houve mudança de domínio
- uma alteração de schema removeu ou corrompeu a store de sessão

#### Orientação operacional

Para atualizar o Campo em produção sem perder validação:

- publique por cima no mesmo endereço
- preserve `IndexedDB` e `localStorage`
- trate mudanças de schema com migração
- não use reinstalação como procedimento padrão
- só peça nova ativação quando houver invalidação real da credencial do dispositivo
