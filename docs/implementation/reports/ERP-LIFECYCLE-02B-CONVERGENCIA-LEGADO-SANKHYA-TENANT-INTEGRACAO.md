# ERP-LIFECYCLE-02B — Reconciliação de `SankhyaConfig` Legado com `TenantIntegracao` Canônica

## 1. Resumo

- A fase adicionou uma reconciliação idempotente e sem endpoint para convergir tenants legados Sankhya.
- A estratégia escolhida foi serviço interno + comando administrativo com `dry-run` por padrão.
- Não houve alteração de frontend, Wizard, IAM, billing, models, migrations ou novos endpoints HTTP.

## 2. Drift encontrado

- Auditoria read-only do banco confirmou:
  - `farms.sankhya_config = 2`
  - `farms.tenant_integracoes = 0`
  - provider `sankhya` no Marketplace existe e está ativo.
- Os tenants auditados estavam em `LEGACY_ONLY`.

## 3. Estados

- Estados suportados pelo serviço:
  - `LEGACY_ONLY`
  - `CANONICAL_ONLY`
  - `BOTH_CONSISTENT`
  - `BOTH_DIVERGENT`
  - `LEGACY_SOFT_DELETED`
  - `CANONICAL_SOFT_DELETED`
  - `DUPLICATE_CANONICAL`
  - `NO_RECORDS`
- No banco real consultado nesta execução:
  - `7a034d03-bd2d-4de5-994a-405e282075ba` -> `LEGACY_ONLY`
  - `tenant-1` -> `LEGACY_ONLY`

## 4. Estratégia

- A reconciliação reutiliza `SankhyaCanonicalAdapter.sync_provider_config(...)`.
- Não cria materialização em GET.
- Não remove o fallback legado do router ERP nesta fase.

## 5. Momento da materialização

- Materialização ocorre apenas em operação de escrita ou via comando administrativo.
- O comando novo suporta:
  - `--tenant-id` repetido
  - `--all`
  - `--execute`
  - `--stop-on-error`
- `dry-run` é o padrão.

## 6. Serviço

- Arquivo criado: `services/api/integracoes/sankhya/services/legacy_reconciliation.py`
- Responsabilidades:
  - classificar estado legado/canônico;
  - bloquear divergência e provider inativo;
  - materializar apenas `LEGACY_ONLY` elegível;
  - ser idempotente;
  - não expor secrets.

## 7. Dry-run

- `dry-run` retorna a ação proposta sem persistir.
- No caso `LEGACY_ONLY`, a ação proposta é `MATERIALIZE_CANONICAL`.
- Nenhum GET foi alterado para criar registros.

## 8. Execução administrativa

- Arquivo criado: `services/api/scripts/reconcile_legacy_sankhya_integration.py`
- O comando executa reconciliação controlada e imprime resumo sanitizado.
- Não há endpoint público para essa operação.

## 9. Provider

- A reconciliação resolve o provider por:
  - `slug = sankhya`
  - `provider_type = ERP`
  - `ativa = True` para materializar.
- Provider inativo bloqueia a execução.

## 10. Scope

- O escopo materializado permanece:
  - `scope_type = TENANT`
  - `scope_id = NULL`
- Não há uso de `UNIDADE_PRODUTIVA`.

## 11. Configuração

- Campos não sensíveis são mapeados para a configuração canônica.
- `sync_interval` é preservado.
- `SankhyaConfig` não é apagada.

## 12. Auth model

- `auth_model` é preservado pelo gateway/auth service.
- Fallback silencioso não foi introduzido.
- Estado inválido ou ambíguo permanece bloqueado por divergência.

## 13. Credenciais

- Credenciais canônicas são criadas/reutilizadas pelo adapter.
- Segredos não são emitidos no relatório nem no retorno do serviço.
- `IntegrationCredential` permanece canônica.

## 14. Features

- A reconciliação valida o conjunto padrão do adapter:
  - `financeiro`
  - `estoque`
  - `nfe`
  - `pedidos`
  - `pessoas`
  - `produtos`
- Capabilities P2 continuam fora de ativação operacional.

## 15. Policies

- Policies canônicas são criadas/reutilizadas pelo adapter.
- A fase não criou fluxo novo de sync automático.

## 16. Health

- `IntegrationHealth` é materializada pelo adapter.
- O estado não é forçado a `CONNECTED` sem base.

## 17. Versions

- `IntegrationVersion` é criada e mantida idempotente pelo adapter.
- Snapshot mascarado é comparado na reconciliação.

## 18. Idempotência

- Reexecutar a reconciliação em `BOTH_CONSISTENT` não altera o banco.
- Teste validado com segunda execução sem mudanças.

## 19. Concorrência

- A convergência reutiliza as proteções já existentes do adapter.
- Não houve criação de novo lock ou novo mecanismo de serialização.

## 20. Divergências

- `BOTH_DIVERGENT` é bloqueado.
- O serviço compara:
  - provider
  - scope
  - connection payload
  - credenciais
  - health
  - features
  - policies
  - version snapshot

## 21. Soft delete

- `LEGACY_SOFT_DELETED` é suportado quando `SankhyaConfig.ativo = false`.
- `CANONICAL_SOFT_DELETED` é suportado quando a linha canônica está removida/soft-deleted.

## 22. Provider inativo

- Provider Sankhya inativo bloqueia reconciliação.
- Não há materialização silenciosa nesse caso.

## 23. P2

- `pedidos` e `estoque` permanecem fora do piloto operacional.
- A reconciliação não ativou capability indevida.

## 24. Fallback

- O fallback legado do router ERP foi preservado temporariamente.
- A fase apenas reduz a dependência operacional dele via comando de convergência.

## 25. Timezone issue

- O erro legado de timezone observado na auditoria anterior não foi alterado nesta fase.
- Não foi necessário para a reconciliação canônica.

## 26. Arquivos alterados

- Backend:
  - `services/api/integracoes/sankhya/services/legacy_reconciliation.py`
  - `services/api/integracoes/sankhya/services/__init__.py`
  - `services/api/scripts/reconcile_legacy_sankhya_integration.py`
  - `services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py`
- Mantidos de fases anteriores no mesmo ramo:
  - `services/api/integracoes/erp/router.py`
  - `services/api/tests/unit/integracoes/test_erp_router.py`
  - `services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py`

## 27. Testes

- Teste novo:
  - `8 passed`
- Bloco backend relevante:
  - `53 passed`
- O conjunto cobriu:
  - dry-run
  - execução
  - idempotência
  - `BOTH_CONSISTENT`
  - `BOTH_DIVERGENT`
  - `CANONICAL_ONLY`
  - `LEGACY_SOFT_DELETED`
  - `CANONICAL_SOFT_DELETED`
  - provider inativo

## 28. PostgreSQL

- A fase fez auditoria read-only no banco real por consulta.
- Não houve escrita manual no banco.

## 29. RLS

- A reconciliação reutiliza o adapter já compatível com RLS.
- Não foi criado mecanismo novo de bypass.

## 30. Comandos

- `services/api/.venv/bin/pytest -q services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py`
- `services/api/.venv/bin/pytest -q services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py`
- `cd services/api && .venv/bin/ruff check integracoes/erp/router.py tests/unit/integracoes/test_erp_router.py tests/unit/integracoes/test_erp_bootstrap_tardio.py integracoes/sankhya/services/legacy_reconciliation.py tests/unit/integracoes/test_sankhya_legacy_reconciliation.py scripts/reconcile_legacy_sankhya_integration.py integracoes/sankhya/services/__init__.py`
- `git diff --check`
- `git -C apps/web diff --check`

## 31. Resultados

- `ruff` nos arquivos alterados: passou.
- `git diff --check`: passou.
- `git -C apps/web diff --check`: passou.
- Bloco de testes backend: passou.

## 32. Dados antes

- `sankhya_config`: 2
- `tenant_integracoes`: 0
- provider Sankhya ativo no Marketplace: sim

## 33. Dados depois

- A inspeção sob contexto RLS mostrou que os tenants já tinham estrutura canônica materializada.
- `7a034d03-bd2d-4de5-994a-405e282075ba` possui:
  - `tenant_integracoes.id = 1`
  - `integration_credentials = 11` registros históricos
  - `integration_features = 6`
  - `integration_sync_policies = 6`
  - `integration_health_snapshots = 1`
  - `integration_versions = 15`
- `tenant-1` possui:
  - `tenant_integracoes.id = 2`
  - `integration_credentials = 3` registros históricos
  - `integration_features = 6`
  - `integration_sync_policies = 6`
  - `integration_health_snapshots = 1`
  - `integration_versions = 3`
- Ambos permaneceram classificáveis como `BOTH_DIVERGENT` no dry-run com contexto RLS explícito.

## 34. Riscos

- O fallback legado ainda existe temporariamente.
- Existe drift canônico residual em credenciais: `credential_bundle_mismatch` e `credential_mask_metadata_mismatch`.
- O comando CLI sem contexto RLS explícito ainda reporta `LEGACY_ONLY`, então não pode ser usado isoladamente como evidência final do estado.
- A operação não pode avançar para o próximo épico enquanto os tenants permanecerem `BOTH_DIVERGENT`.

## 35. Limitações

- Não foi criada migração.
- Não houve alteração de frontend.
- Não houve remoção do fallback legado.
- Não houve reconciliação completa e idempotente dos tenants legados nesta janela.
- A divergência atual parece concentrada no bundle de credenciais canônicas, não na ausência da linha canônica.

## 36. Impacto no piloto

- A fase não liberou o piloto para avanço.
- O risco principal passou a ser drift canônico ativo em tenants já materializados, com credencial canônica não coerente com o legado atual.
- `ERP-CORE-REPAIR-01A` não deve iniciar até haver reconciliação consistente ou uma correção específica do reconciliador.

## 37. Veredicto

- Reconciliacão técnica: `GO COM RESSALVAS`
- Operação no banco real nesta sessão: `NO-GO`

## 38. Recomendação para remoção futura do fallback

- Remover o fallback legado do router ERP somente depois da janela de reconciliação e da validação dos tenants `LEGACY_ONLY` zerada.

## 39. Autorização para `ERP-CORE-REPAIR-01A`

- Não autorizado iniciar `ERP-CORE-REPAIR-01A` nesta execução.

## 40. Execução Operacional ERP-LIFECYCLE-02B.1

- Ambiente: backend `services/api` do workspace, com acesso ao PostgreSQL do domínio `farms`.
- Janela: 2026-07-14, com leituras operacionais entre 11:42 e 14:38 BRT.
- Revision Alembic: `6e6fda192744 (head)`.
- Backup/snapshot: não executado nesta sessão.
- Responsável técnico: Codex.
- Responsável pela aprovação: não informado na execução.
- Tenants elegíveis observados: `7a034d03-bd2d-4de5-994a-405e282075ba` e `tenant-1`.
- Primeiro dry-run global:
  - o CLI sem contexto RLS reportou `LEGACY_ONLY` para ambos;
  - a inspeção sob contexto RLS mostrou `BOTH_DIVERGENT` para ambos;
  - portanto o CLI isolado não foi considerado evidência suficiente para prosseguir.
- Aprovação para prosseguir com execução em massa: negada após confirmação do drift.
- Execução do primeiro tenant:
  - comando `--tenant-id 7a034d03-bd2d-4de5-994a-405e282075ba --execute --stop-on-error` foi disparado previamente;
  - a classificação operacional posterior permaneceu `BOTH_DIVERGENT`;
  - a linha canônica existe, mas o bundle de credenciais não está coerente com o legado atual.
- Validação do primeiro tenant:
  - `tenant_integracoes.id = 1`;
  - `credential_ref_id = 12`;
  - `integration_features = 6`;
  - `integration_sync_policies = 6`;
  - `integration_health_snapshots = 1`;
  - `integration_versions = 15`.
- Execução do segundo tenant:
  - não executado;
  - bloqueado pelo critério de interrupção ao encontrar `BOTH_DIVERGENT`.
- Validação do segundo tenant:
  - `tenant_integracoes.id = 2`;
  - `integration_credentials = 3`;
  - `integration_versions = 3`;
  - o estado operacional também permanece `BOTH_DIVERGENT`.
- Idempotência:
  - não ficou comprovada como concluída para convergência;
  - o re-dry-run reproduz o mesmo drift.
- Duplicidades:
  - não há duplicidade ativa de `TenantIntegracao`;
  - há histórico de múltiplas credenciais/versions canônicas por tenant.
- Credenciais:
  - a divergência central está em `credential_bundle_mismatch` e, no tenant principal, também em `credential_mask_metadata_mismatch`.
- Features:
  - `pessoas`, `produtos`, `financeiro`, `nfe`, `pedidos` e `estoque` estão presentes.
- Policies:
  - 6 políticas por tenant, coerentes com as features materializadas.
- Health:
  - 1 snapshot por tenant; o tenant principal continua com `CONNECTED`.
- Versions:
  - 15 e 3 snapshots, respectivamente.
- P2:
  - não houve ativação operacional indevida.
- RLS:
  - preservado; nenhuma alteração de policy foi feita.
- Fallback:
  - preservado.
- Diagnóstico:
  - o issue de timezone não foi alterado nesta execução.
- Achados:
  - `BOTH_DIVERGENT`;
  - `credential_bundle_mismatch`;
  - `credential_mask_metadata_mismatch`;
  - múltiplas credenciais históricas.
- Bloqueadores:
  - divergência canônica residual;
  - segunda materialização interrompida corretamente;
  - CLI sem contexto RLS não foi suficiente para certificar elegibilidade.
- Rollback:
  - não executado.
- Diff:
  - sem alterações de código; apenas este relatório foi atualizado.
- Veredicto:
  - `NO-GO`.
- Autorização para o próximo épico:
  - não autorizada para `ERP-CORE-REPAIR-01A`.
