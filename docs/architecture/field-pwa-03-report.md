# FIELD-PWA-03 — Reconciliação Avançada, Conflitos e Estado Oficial no PWA

## Resumo executivo

O `apps/campo` passou a separar claramente:

- fila local offline do dispositivo
- eventos em atenção/revisão
- timeline oficial oficial vinda do servidor

A reconciliação agora relaciona `local_id`, `device_id` e `server_id`, evita duplicação de eventos de outros dispositivos, detecta conflito simples e bloqueia retries inseguros. O contrato de `pull` foi enriquecido com campos documentais suficientes para refletir rejeição, retificação e invalidação no PWA sem criar timeline paralela.

## Correções implementadas

### 1. Reconciliação inbound local ↔ servidor

- `pull` agora recebe `device_id`, `retifica_evento_id`, `retificado_por_evento_id` e `justificativa`
- o evento local só é reconciliado quando `local_id` e `device_id` conferem
- eventos oficiais de outro dispositivo aparecem apenas na timeline oficial
- o evento local reconciliado preserva `server_id`, `documental_status`, justificativa oficial e timestamp de reconciliação

Arquivos:

- [pull.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/pull.ts)
- [schemas.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/schemas.py)
- [service.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py)

### 2. Conflito simples

- conflito é marcado quando há divergência entre `server_id` local e oficial
- conflito também é marcado quando o servidor retorna status terminal incompatível com o estado local
- não há merge automático
- o operador recebe a mensagem: `Este registro possui divergência entre aparelho e servidor. Revise no sistema.`

Arquivos:

- [pull.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/pull.ts)
- [db.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/db.ts)

### 3. Retry seguro

- retry só é permitido para `ERROR` sem `server_id`
- retry é bloqueado para eventos já reconciliados, em conflito ou com status oficial terminal
- `last_sync_error` é limpo ao reenfileirar
- `sync_attempts` é preservado

Arquivos:

- [caderno-offline.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/caderno-offline.ts)
- [push.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts)
- [worker.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/worker.ts)

### 4. Evidências locais

- evidências agora carregam `upload_status`
- o PWA exibe visualmente `LOCAL`, `ENVIADA` e `ERRO_UPLOAD`
- o `push` atualiza o status das evidências conforme sucesso ou falha

Arquivos:

- [db.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/db.ts)
- [caderno-offline.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/caderno-offline.ts)
- [push.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts)

### 5. Leitura operacional do /caderno

- seção `Pendentes no Dispositivo`
- seção `Revisão Necessária`
- seção `Timeline Oficial`
- mensagens documentais para `PENDENTE_APROVACAO`, `REJEITADO`, `ORIGEM_INVALIDADA` e `RETIFICADO`

Arquivo:

- [page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx)

## Comandos executados

```bash
pnpm --filter @agro/campo exec tsc --noEmit
pnpm --filter @agro/campo lint
pnpm --filter @agro/campo build
services/api/.venv/bin/pytest services/api/tests/unit/campo/test_sync_pull_safra_mapper.py -q
services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py services/api/tests/unit/agricola/test_field_core03_caderno_status.py services/api/tests/unit/agricola/test_field_core05_caderno_retificacao.py services/api/tests/e2e/test_caderno_tenant_isolation.py -q
git diff --check
```

## Resultado das validações

- `apps/campo` typecheck: passou
- `apps/campo` lint: passou
- `apps/campo` build: passou
- pytest `test_sync_pull_safra_mapper.py`: `5 passed`
- pytest complementar `campo/caderno/offline/tenant`: `21 passed`
- `git diff --check`: passou

## Observações

- O IndexedDB do Campo subiu para `version(7)` para acomodar os novos campos de reconciliação e status de evidência sem reset local.
- O backend manteve o contrato oficial; apenas enriqueceu o payload de `pull` com metadados já existentes na cadeia documental.
- Permanecem as ressalvas globais já conhecidas do projeto, mas este ciclo não as agravou.

## Decisão final

Classificação: `APROVADO COM RESSALVAS`

Justificativa:

- os critérios funcionais do FIELD-PWA-03 foram atendidos
- a base ficou pronta para o próximo ciclo de reconciliação mais avançada
- as ressalvas remanescentes são estruturais do projeto e pré-existentes a este ciclo
