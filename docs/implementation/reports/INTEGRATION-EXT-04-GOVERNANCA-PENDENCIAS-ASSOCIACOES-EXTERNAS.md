# INTEGRATION-EXT-04 - Governanca Operacional das Associacoes Externas Pendentes

## Auditoria realizada

Revisados:

- `docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md`
- `docs/architecture/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md`
- dominio `integracoes`
- `ExternalRecordAssociationService`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/schemas.py`
- `services/api/integracoes/sankhya/services/external_association_helper.py`
- telas Sankhya existentes em `apps/web/src/components/integracoes/sankhya-console.tsx`
- testes unitarios do dominio de Integracoes e Sankhya

## O que ja existia

- Modelo transversal `integration_external_record_links` com status, confidencia, origem, empresa/filial externas, metadados e historico.
- `ExternalRecordAssociationService` com criacao, atualizacao, deteccao de duplicidade, conflito, substituicao, desativacao, reconciliacao e historico.
- Helper Sankhya P0/P1 ja usando a associacao oficial.
- Router Sankhya ja consolidado no dominio de integracoes.
- Console web Sankhya para configuracao, health, jobs, logs e sincronizacao.

## O que foi reaproveitado

- `ExternalRecordAssociationService` como unica camada de negocio para persistencia e historico.
- Dependencias de RBAC existentes via `require_tenant_permission`.
- Router Sankhya ja montado em `/api/v1/integracoes/sankhya`.
- Console web Sankhya existente.
- Estrutura de historico ja persistida em `integration_external_record_link_history`.

## O que foi estendido

- `services/api/integracoes/schemas.py`
  - respostas internas para listagem de pendentes e historico
  - request explicito de reconciliacao manual com `local_entity_type` e `local_entity_id`
- `services/api/integracoes/services/external_record_association_service.py`
  - listagem de associacoes pendentes com filtros por tenant, provider, feature, entidade local, entidade externa, ambiente, config e paginação
- `services/api/integracoes/sankhya/routers/__init__.py`
  - endpoints operacionais para consultar pendentes e reconciliar manualmente
  - validacao de tenant do contexto
  - preservacao da regra de duplicidade antes da reconciliacao
- `apps/web/src/components/integracoes/sankhya-console.tsx`
  - secao operacional para listar pendencias e reconciliar manualmente

## O que precisou ser criado

- Nenhum novo modelo de integracao.
- Nenhum novo staging.
- Nenhuma escrita bidirecional.
- Nenhum dominio paralelo de de-para Sankhya.
- Apenas os contratos internos e endpoints de governanca para operar a estrutura ja existente.

## Contrato operacional entregue

### Listagem

- `GET /api/v1/integracoes/sankhya/associacoes/pendentes`
- Filtra por:
  - `provider_id`
  - `feature_id`
  - `feature_code`
  - `entity_type`
  - `external_entity_type`
  - `environment`
  - `tenant_id` em contexto explicitamente validado

### Reconciliacao manual

- `POST /api/v1/integracoes/sankhya/associacoes/{association_id}/reconciliar`
- Exige explicitamente:
  - `local_entity_type`
  - `local_entity_id`
- Mantem:
  - verificacao de duplicidade
  - historico da mudanca
  - status final ativo

### Resposta operacional

Expõe:

- `external_id`
- `external_key`
- `external_payload` sanitizado
- `status`
- `motivo`
- `history`

## RBAC

- Leitura: `integrations:view`
- Reconciliacao: `integrations:sync`
- O controle continua dentro do modelo de permissao de tenant ja existente.

## Resultados de teste

Executado com sucesso:

- `git diff --check`
- `timeout 120s .venv/bin/python -m pytest tests/unit/integracoes/test_external_record_association_service.py tests/unit/integracoes/test_sankhya_external_association_p0.py tests/unit/integracoes/test_sankhya_external_association_governance_router.py -q`
- `timeout 60s .venv/bin/alembic heads`
- `timeout 60s .venv/bin/alembic current`

Resultado da suite:

- `28 passed`

Estado do Alembic:

- `20260706_integrations_external_record_links_pending_local (head)`

## Conclusao

A governanca operacional de associacoes externas pendentes foi adicionada sem criar infraestrutura nova, sem alterar o staging Sankhya e sem implementar bidirecionalidade.

O AgroSaaS agora consegue consultar pendencias PENDING, filtrar por contexto operacional e reconciliar manualmente apenas quando o vinculo local e informado de forma explicita.
