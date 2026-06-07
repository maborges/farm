# FIELD-REMEDIATION-01

## Resultado

- Status final: `APROVADO COM RESSALVAS`
- Head Alembic final: `20260606_field_remediation_01_snapshot`
- Objetivo principal cumprido:
  - merge de migrations
  - reconciliação inbound do caderno no Campo
  - separação entre fila offline e timeline oficial no PWA
  - sincronização de estados `CANCELADA` e `INVALIDADA`
  - assinatura documental com snapshot persistido
  - limpeza dos remanescentes `SQLAlchemy 2` com `.astext`

## Implementado

### 1. Migrations

- Merge revision criada:
  - `20260606_field_remediation_01_merge`
- Migration estrutural criada:
  - `20260606_field_remediation_01_snapshot`

### 2. Reconciliação inbound do caderno

- `SyncService.pull()` agora entrega `eventos_caderno_oficiais`.
- Payload oficial inclui:
  - `server_id`
  - `local_id` quando houver proveniência PWA
  - `status_evento`
  - `documental_status`
  - `versao_vigente`
  - `retificado`
  - `retificador`
  - `invalidado`
  - `origem_invalidada`
  - `updated_at`

### 3. Campo / PWA

- O banco local do Campo ganhou store dedicada para eventos oficiais:
  - `caderno_server_events`
- O `pull` agora:
  - persiste a timeline oficial
  - reconcilia eventos locais por `local_id`
  - atualiza `status_evento` e `server_id` quando o servidor já conhece o evento
- A UI do Campo passou a separar:
  - `Eventos Locais`
  - `Eventos Oficiais`

### 4. Assinatura documental forte

- `caderno_exportacoes` agora persiste:
  - `snapshot_documental`
  - `snapshot_hash`
  - `protocolo_documental`
  - `usuario_assinatura_id`
- A assinatura passa a derivar de um envelope com:
  - `snapshot_hash`
  - `protocolo_documental`
  - identidade do signatário
  - timestamp de assinatura
- O `payload_before` da auditoria de assinatura foi corrigido para capturar o estado anterior real.

### 5. UI web documental

- A timeline e o drawer do caderno agora exibem:
  - `origem_invalidada`
  - `documental_status`
  - `motivo_invalidacao_origem`

### 6. SQLAlchemy 2

- Busca completa por `.astext` no backend ativo concluída.
- Remanescentes removidos, inclusive no domínio `ia/growth`.

## Testes executados

- `services/api/tests/unit/campo/test_sync_pull_safra_mapper.py`
- `services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py`
- `services/api/tests/unit/agricola/test_field_core04_caderno_exportacao.py`
- `services/api/tests/unit/agricola/test_field_core05_caderno_retificacao.py`
- `services/api/tests/unit/agricola/test_tarefas_integridade_documental.py`
- `services/api/tests/unit/campo/test_tarefa_programada_integridade.py`

Resultado:

- `36 passed`

## Ressalvas

### 1. Drift arquitetural ainda existe

- O espelho em `apps/web/services/api` continua divergente do backend ativo em `services/api`.
- Neste ciclo foram corrigidos apenas os fluxos ativos e as divergências seguras de apresentação.
- O espelho deve ser tratado em uma limpeza dedicada para evitar manutenção dupla.

### 2. Frontend sem validação de build completa neste ciclo

- Os contratos do Campo e do web foram atualizados.
- A validação forte executada neste ciclo foi:
  - testes backend
  - `py_compile`
  - `git diff --check`
- Build completo de frontend/e2e ainda é recomendado antes de FIELD-PWA-03.

## Conclusão

O bloqueio arquitetural que impedia o início do `FIELD-PWA-03` foi removido no núcleo documental e no contrato de sincronização. O sistema está apto a avançar, mas com ressalva operacional sobre o drift do espelho `apps/web/services/api` e sobre a ausência de validação completa de build/e2e dos frontends neste ciclo.
