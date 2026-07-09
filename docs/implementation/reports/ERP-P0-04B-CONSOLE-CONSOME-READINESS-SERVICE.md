# ERP-P0-04B — Console ERP consome `ErpReadinessService`

## Resumo executivo

Esta execução fez o Console ERP consumir o readiness consolidado pelo backend, usando o mesmo ponto de decisão já adotado pelo Wizard.

A regra deixou de ser calculada no frontend. O console agora apenas renderiza o snapshot entregue pelo endpoint oficial de status.

## Arquivos auditados

### Backend e contrato Gateway Sankhya

- `services/api/integracoes/erp_readiness_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

### Frontend

- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`

## Confirmação do modelo Gateway Sankhya

A auditoria confirmou que o provider atual continua sendo tratado como Gateway Sankhya:

- autenticação via `/authenticate`;
- uso de `sankhya_environment`;
- uso de `sankhya_api_base_url`;
- uso de `sankhya_auth_url`;
- uso de `sankhya_client_id`;
- uso de `sankhya_client_secret`;
- uso de `sankhya_x_token`;
- `X-Token` tratado como credencial de Gateway;
- credenciais mascaradas nos contratos e respostas;
- health dependente da autenticação correta no Gateway.

Não houve exposição de token, secret ou X-Token em tela, logs ou relatório.

## Arquivos alterados

- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/wizard/test_wizard_checklist_engine.py`
- `services/api/wizard/checklist_engine.py`
- `services/api/integracoes/erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `apps/web/src/components/integracoes/sankhya-console.tsx`

## Como o Console passou a consumir o readiness consolidado

O endpoint existente `/integracoes/sankhya/status` passou a retornar um campo `readiness` calculado pelo backend.

Esse campo é produzido com base em `ErpReadinessService` e inclui:

- `status`
- `label`
- `variant`
- `summary`
- `pending`
- `block_reasons`
- `cta_url`
- `provider_code`
- `provider_display_name`
- `health_status`
- `capabilities_evaluated`
- `policies_evaluated`
- `pending_links`
- `conflict_links`

No frontend, `SankhyaConsole` deixou de calcular prontidão localmente e passou a usar `status.readiness`.

## Confirmação de ausência de regra paralela no frontend

O cálculo local de prontidão foi removido do componente do console.

O frontend ainda exibe:

- provider atual;
- capability matrix;
- policies;
- health;
- diagnóstico;
- associações pendentes.

Mas a decisão final do piloto restrito vem do backend.

## Confirmação de credenciais mascaradas

A revisão confirmou que:

- `SankhyaGatewayAuthService` mascara `client_secret`, `x_token` e senha legada;
- `SankhyaConfigSerializer` não expõe segredos brutos;
- o console mostra apenas máscaras e flags de presença;
- o payload de status e configuração mantém a mesma proteção.

## Testes executados

### Backend

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_erp_readiness_service.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -q
```

Resultado: `23 passed`

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py -q
```

Resultado: `27 passed`

### Frontend

```bash
npm run typecheck
```

Resultado: aprovado.

### Validação estrutural

```bash
git diff --check
```

Resultado: sem diferenças.

## Lacunas remanescentes

- o endpoint de status ainda combina dados de status, health, policies e readiness; isso é compatível com o Console, mas pode ser refinado em uma consolidação posterior;
- a UI ainda exibe o provider como Sankhya porque este é o provider ativo, embora o contrato seja genérico;
- o backoffice continua fora da responsabilidade principal da prontidão do tenant.

## Veredicto final

**APROVADO.**

O Console ERP passou a consumir o readiness consolidado do backend, sem regra paralela no frontend e sem quebrar o modelo Gateway Sankhya.
