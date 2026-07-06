# SANKHYA-DOMAIN-02 — API/UX Oficial de Status, Jobs e Health

## 1. Resumo Executivo

Esta execução adaptou a integração Sankhya para expor status, jobs e health oficiais quando disponíveis, mantendo fallback legado sem remover `SankhyaConfig` nem `SankhyaSyncLog`.

## 2. Arquivos alterados

- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/app/integracoes/page.tsx`

## 3. API de status

O endpoint `GET /integracoes/sankhya/status` permaneceu compatível e passou a retornar, de forma aditiva:

- `status_legado`
- `status_canonico`
- `status_origem`
- `health_origem`
- `config_id_canonico`
- `lifecycle_state`
- `health_status`
- `health_summary`
- `last_success_at`
- `last_failure_at`
- `consecutive_failures`
- `features_habilitadas`
- `policies_resumidas`

Os campos legados `configurado`, `ativo`, `ultimo_sync`, `proximo_sync` e `status_conexao` foram preservados.

## 4. API de jobs/logs

O endpoint `GET /integracoes/sankhya/logs` passou a enriquecer cada `SankhyaSyncLog` com correlação oficial quando houver `IntegrationJob` relacionado.

Foram adicionados:

- `origem_dados`
- `integration_job_id`
- `feature_code`
- `job_status`
- `trigger_type`
- `job_started_at`
- `job_finished_at`
- `result_payload`
- `error_payload`

Também foi criado `GET /integracoes/sankhya/jobs` para listar jobs oficiais recentes sem substituir os logs legados.

## 5. Health

Foi criado `GET /integracoes/sankhya/health`.

Comportamento:

- usa `IntegrationHealth` quando existir;
- usa fallback legado quando a camada oficial não estiver materializada;
- informa a origem do dado em `origem`;
- não falha apenas por ausência de snapshot oficial.

## 6. Frontend tenant

O console principal do tenant em `Administração → Integrações ERP → Sankhya` passou a exibir:

- lifecycle e health oficiais;
- origem do status/health;
- último sucesso e última falha;
- falhas consecutivas;
- features habilitadas;
- políticas resumidas;
- jobs oficiais recentes;
- logs legados enriquecidos.

O formulário de configuração existente foi preservado.

## 7. Frontend backoffice

O backoffice continuou com foco em observabilidade e suporte.

A tela passou a exibir:

- health oficial;
- origem oficial ou legada;
- jobs oficiais;
- logs legados enriquecidos;
- reforço explícito de que o backoffice não é o console primário de configuração.

## 8. Compatibilidade legado/oficial

- `SankhyaConfig` preservado.
- `SankhyaSyncLog` preservado.
- Contratos antigos mantidos.
- Novos campos adicionados de forma compatível.
- Fallback legado aplicado quando `TenantIntegracao`, `IntegrationHealth` ou `IntegrationJob` não existirem para o tenant.

## 9. Segurança

- Nenhum segredo bruto é retornado.
- Máscara aplicada em payloads com `password`, `token`, `secret`, `private_key` e `certificate`.
- A senha continua protegida no backend.
- Rotas tenant-scoped continuam usando `get_session()` com RLS e `get_tenant_id`.

## 10. Testes executados

- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q`
- `services/api/.venv/bin/ruff check services/api/integracoes/sankhya services/api/tests/unit/integracoes`

Cobertura adicionada:

- status oficial com fallback legado;
- health oficial e legado;
- enriquecimento de logs com `IntegrationJob`;
- mascaramento de payloads sensíveis;
- presença de rotas `/status`, `/health`, `/jobs` e `/logs`;
- reforço de governança no backoffice.

## 11. Limitações

- Não houve migração de dados legados para a camada oficial.
- O vínculo legado ↔ oficial continua complementar, não substitutivo.
- O console genérico de integrações ainda é uma tela simples e não implementa todo o catálogo futuro do domínio.

## 12. Próxima execução recomendada

`SANKHYA-DOMAIN-03` para aprofundar observabilidade operacional, correlação histórica e eventual convergência incremental de rotinas legadas para consumo prioritário da camada oficial, sem big bang.
