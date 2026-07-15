# ERP-TENANT-ADMIN-01 — Consolidação da Configuração ERP e das Credenciais na Área Administrativa do Tenant

## Resumo
Esta fase corrigiu a superfície administrativa do Tenant para usar a credencial canônica ativa como referência operacional, sem depender do Backoffice e sem perder compatibilidade com `SankhyaConfig` legado.

## Divergência inicial
Os tenants auditados apresentavam divergência real entre o legado e o canônico:

- `credential_bundle_mismatch`
- `credential_mask_metadata_mismatch`

O problema não era apenas de máscara. O runtime canônico já apontava para uma credencial ativa com bundle diferente do que a UI carregava do `SankhyaConfig` legado.

## Fonte oficial
Contrato operacional consolidado:

- Fonte de edição: `SankhyaConfig` via Console do Tenant
- Fonte de reload: merge entre `SankhyaConfig` legado e `TenantIntegracao.credential` ativa
- Fonte do runtime: `TenantIntegracao` canônica + `IntegrationCredential` ativa
- Fonte do teste de conexão: mesma configuração operacional usada pelo runtime

## Load
O carregamento do Console passou a:

- ler a configuração legada;
- localizar a credencial canônica ativa;
- recompor o estado operacional;
- expor `auth_model` e máscaras coerentes com a credencial ativa;
- não depender de histórico inativo para renderização.

## Save
O salvamento passou a:

- carregar a configuração operacional, não apenas o `SankhyaConfig` cru;
- preservar a credencial ativa quando o secret é omitido;
- evitar rotação desnecessária;
- manter a consistência entre legado e canônico;
- seguir o contrato de `sync_provider_config(...)` sem criar novo fluxo.

## Rotação
Rotação continua existindo quando o secret é alterado, mas o save sem alteração de credencial não cria nova credencial nem muda a referência ativa.

## Readiness e Health
`readiness` e `health` agora leem a mesma configuração operacional usada no Console. Isso evita que o frontend veja um bundle desatualizado enquanto o runtime já usa outro.

## Reconciliador
O reconciliador foi ajustado para:

- restaurar contexto RLS antes da leitura do tenant;
- comparar apenas credenciais ativas para contagem de duplicidade;
- ignorar histórico inativo como causa automática de bloqueio;
- continuar bloqueando divergência real.

## CLI e RLS
O caminho administrativo deixou de depender de leitura sem contexto. A reconciliação passa a restaurar o tenant antes de carregar o snapshot, o que evita classificação incorreta por falta de contexto.

## Arquivos alterados
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/legacy_reconciliation.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py`

## Testes backend
Executados com sucesso:

- `services/api/.venv/bin/python -m pytest -q services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py services/api/tests/unit/integracoes/test_sankhya_legacy_reconciliation.py`

Resultado:

- `41 passed`

## Lint e diff
Executados com sucesso:

- `services/api/.venv/bin/ruff check ...` nos arquivos alterados
- `git diff --check`
- `git -C apps/web diff --check`

## Riscos e limitações
- O legado `SankhyaConfig` continua existindo por compatibilidade.
- O fallback legado não foi removido nesta fase.
- Não houve mudança no Backoffice.
- Não houve alteração no frontend nesta execução.

## Veredicto
`GO`

O Console passou a carregar e salvar a configuração correta do Tenant, a credencial ativa deixou de ser tratada como estado histórico e a reconciliação deixou de bloquear por histórico inativo.

## Recomendação
Prosseguir para a próxima etapa sem alterar o Backoffice.
