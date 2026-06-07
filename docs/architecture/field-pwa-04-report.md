# FIELD-PWA-04 — Evidências Offline Resilientes e Upload Confiável

## Resumo executivo

O PWA (`apps/campo`) e o Backend (`services/api`) foram aperfeiçoados para lidar com o upload de fotos/evidências de forma resiliente em ambientes com conectividade rural intermitente ou offline.

As principais conquistas deste ciclo foram:
1. **Identidade própria para evidências**: Cada evidência agora possui um `device_local_id` (UUID gerado no client) que permite seu rastreamento individual e idempotência no backend.
2. **Upload desacoplado**: O envio de eventos (texto/dados) foi desacoplado do envio dos binários das mídias. O evento é sincronizado primeiro e as mídias são transmitidas posteriormente, de forma individualizada, reduzindo o payload e a vulnerabilidade de conexões instáveis.
3. **Gerenciamento de fila de upload**: Introdução do status `ENVIANDO` no IndexedDB, controle de tentativas de upload (`upload_attempts` limitado a 5) e suporte a retransmissão individual com botão de retry manual no PWA.
4. **Endpoint idempotente e seguro**: Criação de rota dedicada `POST /entradas/{id}/evidencias` protegida com token de dispositivo (`device_token`), garantindo que apenas mídias no escopo do aparelho sejam armazenadas, prevenindo vazamentos entre tenants e reentradas duplicadas.

## Correções implementadas

### 1. Modelo e Persistência no Backend

- `CadernoCampoFoto` recebeu novos campos: `device_local_id` (identificador único local), `device_id` (aparelho que gerou), `mime_type`, `size_bytes` e `storage_path`.
- Adicionada a constraint única `uq_caderno_foto_device_local_id` na combinação de `(entrada_id, device_local_id)`.
- Criada a migração correspondente no Alembic.

Arquivos:
- [models.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/models.py)
- [20260607_field_pwa04_evidencia_upload.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260607_field_pwa04_evidencia_upload.py)

### 2. Serviço e Rotas de API (Backend)

- Novo endpoint `/entradas/{id}/evidencias` no roteador do caderno de campo.
- Validação se a entrada de caderno pertence ao tenant do dispositivo e se a unidade produtiva está no escopo permitido do device token.
- Tratamento de idempotência: se a evidência com o mesmo `device_local_id` já existe na entrada, retorna o registro existente imediatamente sem reenviar para o storage (retorno idempotente bem-sucedido).
- Reutilização do `StorageService` padrão para persistência dos arquivos no disco/provedor sob a estrutura de diretórios do tenant (`static/fotos_caderno/{tenant_id}/{uuid}.jpg`).

Arquivos:
- [router.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/router.py)
- [service.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/service.py)
- [schemas.py](/opt/lampp/htdocs/farm/services/api/agricola/caderno/schemas.py)

### 3. Banco Local IndexedDB (PWA)

- Versão do banco local alterada para `8`.
- Estrutura de evidências estendida para conter: `local_evidence_id`, `upload_status` ("LOCAL" | "ENVIANDO" | "ENVIADA" | "ERRO_UPLOAD"), `upload_attempts` e `error_message`.
- Lógica de migração no upgrade de banco preservando registros pré-existentes.

Arquivos:
- [db.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/db.ts)

### 4. Ciclo de Vida e Estados das Evidências (PWA)

- Métodos auxiliares para gerenciar transições de estado de fotos locais (`markEvidenciaUploading`, `markEvidenciaUploaded`, `markEvidenciaUploadError`).
- Desacoplamento de envio de fotos no `push`: os eventos offline são sincronizados primeiro. Quando o evento atinge o status `SYNCED`, suas evidências associadas em estado `LOCAL` são promovidas para upload.
- Implementação de um módulo dedicado para requisições de upload multipart.
- Orquestração no Sync Worker: o fluxo de sincronização foi dividido em três etapas claras:
  1. Sincronização de metadados e eventos (`push`).
  2. Upload de evidências promovidas pendentes de upload individualmente.
  3. Atualização da timeline local (`pull`).
- Recuperação de falhas de rede e travamentos: no reinício do worker, evidências travadas no status `ENVIANDO` são redefinidas para `LOCAL` para permitir nova tentativa.

Arquivos:
- [caderno-offline.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/caderno-offline.ts)
- [evidence-upload.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/evidence-upload.ts)
- [push.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/push.ts)
- [worker.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/worker.ts)

### 5. Interface do Usuário (PWA)

- A página do caderno exibe um sumário detalhado das evidências (enviando, pendentes e falhas de upload).
- Renderização de badges indicando o status em tempo real de cada mídia (`ENVIANDO`, `LOCAL`, `ERRO_UPLOAD`).
- Fornecimento de botão de retry manual ("Reenviar") ao lado de cada foto que falhou após as 5 tentativas automáticas, permitindo reprocessamento sem reinício do formulário.

Arquivos:
- [page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx)

## Comandos executados

```bash
pnpm --filter @agro/campo exec tsc --noEmit
pnpm --filter @agro/campo lint
pnpm --filter @agro/campo build
services/api/.venv/bin/pytest services/api/tests/unit/campo/test_field_pwa04_evidencia_upload.py -q
```

## Resultado das validações

- `apps/campo` typecheck: passou
- `apps/campo` lint: passou
- `apps/campo` build: passou
- pytest `test_field_pwa04_evidencia_upload.py`: `6 passed`

## Observações

- O IndexedDB do campo subiu para a versão `8` e a migração de dados locais garante retrocompatibilidade.
- A idempotência baseada no `device_local_id` impede qualquer duplicação física e lógica de fotos em casos de desconexão no meio do upload multipart.

## Decisão final

Classificação: `APROVADO`

Justificativa:
- A resiliência de mídia atendeu integralmente aos requisitos offline do cenário de campo rural.
- Desacoplamento físico e lógico entre evento e mídias reduz os gargalos de uploads em redes móveis instáveis de baixa velocidade.
