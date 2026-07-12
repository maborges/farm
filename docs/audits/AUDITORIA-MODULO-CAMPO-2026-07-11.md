# Auditoria do Módulo Campo

Data: 2026-07-11

## Conclusão executiva

O módulo Campo está **parcialmente implementado**. A fundação offline-first, ativação de dispositivos, PIN local, IndexedDB, fila de sincronização, caderno offline, evidências e parte dos manejos pecuários estão implementados. Entretanto, existem falhas críticas no contrato do pull, na distribuição de tarefas e no processamento da fila. Além disso, aplicação e colheita agrícolas sincronizam apenas como `TarefaCampo`: não são materializadas como operação agrícola ou romaneio e, portanto, não produzem automaticamente estoque, financeiro e indicadores oficiais.

Classificação atual: **não apto para declarar todas as funcionalidades implementadas ou para homologação ponta a ponta sem ressalvas**.

## Achados

### Crítico — Aplicação e colheita do PWA não chegam aos domínios agrícolas oficiais

As telas de aplicação e colheita usam `createTask()` e enviam entidades genéricas `task` com tipos `APLICACAO_DEFENSIVO` e `COLHEITA_REGISTRO`:

- `apps/campo/src/app/(campo)/campo/aplicacao/page.tsx:48`
- `apps/campo/src/app/(campo)/campo/colheita/page.tsx:48`

No backend, o push cria `TarefaCampo`, mas só agenda materialização para sete tipos pecuários. Não há materializador equivalente para operações agrícolas ou romaneios:

- `services/api/campo/service.py:671`
- `services/api/campo/service.py:695`
- `services/api/campo/router.py:506`

Impacto:

- aplicação sincronizada não cria `OperacaoAgricola`;
- não há baixa FIFO do insumo;
- não há custo realizado ou despesa automática;
- não há evento canônico de operação no caderno;
- colheita sincronizada não cria romaneio, produção, produtividade ou receita.

Correção requerida: implementar materializadores agrícolas idempotentes por `tarefa_campo_id`, com transação atômica e retorno do estado de materialização para o PWA/backoffice.

### Crítico — Animais e colaboradores são removidos da resposta HTTP do pull

O serviço monta `animais` e `colaboradores`:

- `services/api/campo/service.py:401`
- `services/api/campo/service.py:427`

Porém, `SyncPullResponse` não declara nenhum dos dois campos:

- `services/api/campo/schemas.py:190`

O endpoint usa esse modelo como `response_model`, portanto o FastAPI filtra os campos extras:

- `services/api/campo/router.py:474`

O cliente espera ambos para preencher o IndexedDB:

- `apps/campo/src/lib/sync/pull.ts:235`
- `apps/campo/src/lib/sync/pull.ts:280`

Impacto:

- seletores de animais ficam vazios em pesagem, vacinação e reprodução;
- entrega de EPI fica sem colaboradores;
- a interface existe, mas os fluxos não são utilizáveis com dados reais recebidos pelo endpoint.

Correção requerida: adicionar schemas de animal e colaborador ao contrato, cobrir a serialização HTTP real e limpar caches removidos em full pull.

### Crítico — Tarefa atribuída a um operador pode ser entregue a outro dispositivo

O pull filtra fazenda, data, status e dispositivo, mas não restringe tarefas por `operador_id == device.user_id` quando não há dispositivo explícito:

- `services/api/campo/service.py:320`
- `services/api/campo/service.py:324`

O PWA impede a execução na tela quando detecta outro operador, mas a tarefa e seus dados já foram transferidos e persistidos no dispositivo.

Impacto:

- exposição indevida de tarefas e dados operacionais entre trabalhadores da mesma fazenda;
- lista local pode exibir trabalho que não pertence ao usuário;
- quebra da expectativa de atribuição individual.

Correção requerida: filtrar no servidor por dispositivo e operador, definindo explicitamente a regra para tarefas sem atribuição.

### Alto — Iniciar e concluir offline pode deixar item preso em `IN_FLIGHT`

Cada transição cria uma entrada independente na fila com o mesmo `entity_id`:

- `apps/campo/src/lib/task-factory.ts:121`

Ao processar os resultados, o cliente usa `find()` somente por `entity_id`. Dois retornos da mesma tarefa localizam sempre o primeiro item, que é marcado duas vezes; o segundo permanece em `IN_FLIGHT`:

- `apps/campo/src/lib/sync/push.ts:71`
- `apps/campo/src/lib/sync/push.ts:72`
- `apps/campo/src/lib/sync/push.ts:77`

A recuperação ocorre apenas na inicialização:

- `apps/campo/src/lib/sync/worker.ts:108`

Impacto:

- fila não zera no fluxo offline normal `Iniciar -> Concluir -> Sincronizar`;
- item pode permanecer preso até reiniciar o aplicativo;
- reenvio posterior pode gerar conflito ou transição inválida.

Correção requerida: usar um identificador único de item de fila no contrato ou compactar transições pendentes da mesma entidade antes do push.

### Alto — Tombstones estão modelados e consumidos, mas não são produzidos

O pull lê `campo_sync_tombstones` e o PWA aplica exclusões:

- `services/api/campo/service.py:347`
- `apps/campo/src/lib/sync/pull.ts:460`

Não foi encontrada criação de `SyncTombstone` nos fluxos de exclusão/cancelamento de tarefas, talhões, lotes ou insumos.

Impacto:

- registros removidos no servidor permanecem no dispositivo;
- tarefas canceladas fora da janela incremental podem continuar visíveis;
- seletores podem apresentar cadastros obsoletos.

Correção requerida: publicar tombstones em toda exclusão relevante e adicionar expiração/retenção compatível com o maior período offline aceito.

### Alto — Push processa somente os primeiros 50 itens por execução

O cliente limita a fila a 50 itens e executa um único push antes do pull:

- `apps/campo/src/lib/sync/push.ts:7`
- `apps/campo/src/lib/sync/push.ts:13`
- `apps/campo/src/lib/sync/worker.ts:33`

Não há laço para drenar lotes adicionais. Ainda assim, o worker marca a sincronização como concluída com sucesso.

Impacto:

- jornadas longas offline exigem várias sincronizações manuais;
- o usuário pode interpretar `Pronto` como sincronização completa mesmo com itens pendentes.

Correção requerida: drenar a fila em lotes até zerar ou atingir limite controlado, exibindo estado parcial quando restarem itens.

### Médio — Falha de materialização pecuária não falha o resultado do push

O push confirma a tarefa e só depois tenta materializar o evento pecuário. Erros são registrados em `dados.sync_pecuaria`, mas o resultado já retornado continua como sucesso:

- `services/api/campo/router.py:500`
- `services/api/campo/router.py:506`
- `services/api/campo/router.py:514`

Impacto:

- dispositivo marca a tarefa como sincronizada mesmo sem evento pecuário oficial;
- o operador não recebe indicação direta de que a integração de domínio falhou;
- depende do backoffice/alertas para detectar inconsistência.

Correção requerida: expor estado de materialização (`PENDING`, `SUCCESS`, `ERROR`) no contrato e permitir reprocessamento idempotente.

### Médio — Cache incremental não remove entidades ausentes sem tombstone

Safras, fazendas, talhões, lotes, animais e insumos são atualizados com `bulkPut`, sem limpeza em um pull completo. Colaboradores são a exceção:

- `apps/campo/src/lib/sync/pull.ts:242`
- `apps/campo/src/lib/sync/pull.ts:257`
- `apps/campo/src/lib/sync/pull.ts:262`
- `apps/campo/src/lib/sync/pull.ts:275`
- `apps/campo/src/lib/sync/pull.ts:280`
- `apps/campo/src/lib/sync/pull.ts:285`

Impacto: combinado com a ausência de tombstones, o banco local acumula registros inativos ou removidos.

### Médio — Cobertura automatizada não representa a jornada completa do PWA

Há boa cobertura unitária/backend para caderno, evidências e pecuária, mas não foram encontrados testes automatizados do cliente Dexie para:

- duas transições da mesma tarefa no mesmo batch;
- drenagem de mais de 50 itens;
- contrato HTTP de `animais` e `colaboradores`;
- aplicação agrícola até estoque/financeiro;
- colheita até romaneio/receita;
- propagação real de tombstones.

A documentação marca todos os critérios de tarefas como concluídos em `docs/CAMPO_PWA_05_TAREFAS_PROGRAMADAS.md:100`, embora o cenário offline de início e conclusão tenha a falha de correlação da fila.

## Matriz funcional

| Área | Estado | Observação |
|---|---|---|
| Cadastro, ativação e revogação de dispositivo | Implementado | API e telas web presentes; há testes de reativação |
| Autenticação local por PIN | Implementado | validação local e continuidade offline presentes |
| Seleção de fazenda autorizada | Implementado | sessão restringe a seleção aos IDs autorizados |
| IndexedDB e fila offline | Parcial | persistência e recuperação existem; falha com múltiplas mutações e batches maiores que 50 |
| Pull de fazendas, talhões, safras e insumos | Parcial | contrato principal existe; remoções ficam obsoletas sem tombstones |
| Pull de animais e colaboradores | Não funcional via HTTP | dados montados pelo service são filtrados pelo response model |
| Tarefas programadas web -> PWA | Parcial | criação e pull existem; distribuição por operador é incorreta |
| Início/conclusão offline -> web | Parcial | transições existem; fila pode ficar presa com duas atualizações |
| Fotos e GPS em tarefas | Implementado com ressalvas | persistência existe; depende da integridade da fila |
| Caderno offline e reconciliação | Implementado | fila separada, conflitos, evidências e estado oficial presentes |
| Entrega de EPI | Parcial | evento de caderno implementado; seletor de colaborador quebra pelo contrato do pull |
| Aplicação agrícola | Somente captura | sincroniza `TarefaCampo`, sem operação, estoque ou financeiro |
| Colheita agrícola | Somente captura | sincroniza `TarefaCampo`, sem romaneio, produção ou receita |
| Pesagem e manejos pecuários | Parcial | materializadores existem, mas animais não chegam pelo response model e falhas pós-push não retornam ao dispositivo |
| Recomendações operacionais/climáticas | Implementado com teste vermelho | código de pull/cache existe; suíte falha por configuração RLS do teste |
| Tela de diagnóstico de sincronização | Parcial | mostra pendentes, falhas e conflitos; pode declarar `Pronto` com itens restantes |

## Verificações executadas

- `npm run typecheck` em `apps/campo`: aprovado.
- `npm run lint` em `apps/campo`: aprovado.
- Testes selecionados de Campo, caderno offline e EPI: 35 aprovados e 1 falhou.
- Falha observada: `test_sync_pull_inclui_recomendacoes_persistidas_sem_recalcular`, bloqueado pela política RLS ao inserir `recommendation_results` no fixture. A falha não prova defeito do recurso em produção, mas impede considerar a suíte verde.
- Dois warnings de `AsyncMock` não aguardado em testes de upload de evidência.

## Prioridade recomendada

1. Corrigir `SyncPullResponse` para entregar animais e colaboradores e adicionar teste do endpoint HTTP.
2. Restringir tarefas por operador/dispositivo no pull.
3. Corrigir correlação/compactação da fila para múltiplas mutações da mesma tarefa.
4. Implementar materialização agrícola para aplicação e colheita, com estoque, financeiro, caderno e romaneio.
5. Produzir tombstones nos domínios de origem e drenar a fila em múltiplos batches.
6. Expor falhas de materialização pecuária ao dispositivo e criar reprocessamento.
7. Criar testes E2E offline reais do PWA, incluindo perda/restauração de conexão e volume acima de 50 itens.
