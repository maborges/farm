# ERP-P0-01 — Materialização do Provider Atual

## Resumo

Materialização semântica do contrato canônico ERP no provider atual `Sankhya`, reutilizando exclusivamente a infraestrutura já existente:

* `MarketplaceIntegracao.provider_definition`
* `MarketplaceIntegracao.feature_schema`
* `MarketplaceIntegracao.sync_schema`
* `MarketplaceIntegracao.health_schema`
* `IntegrationFeature`
* `IntegrationSyncPolicy`
* `IntegrationHealth`
* `IntegrationJob`

Não houve criação de:

* nova tabela;
* novo model;
* migration;
* endpoint;
* runtime paralelo;
* policy paralela;
* schema paralelo.

## Arquivos auditados

### Arquitetura

* `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
* `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
* `docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md`
* `docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md`
* `docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md`
* `docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md`
* `docs/architecture/ERP-ARCHITECTURE-INDEX.md`

### Backend

* `services/api/integracoes/models.py`
* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/integracoes/sankhya/services/sync_service.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
* `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## Arquivos alterados

* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`

## Aderência ao contrato

### `provider_definition`

Enriquecido com:

* identificação canônica do provider;
* modelos de autenticação suportados;
* escopos suportados;
* capabilities suportadas;
* modos canônicos de sync;
* maturidade;
* notas de provider de referência.

### `feature_schema`

Mantido `supported_features` e adicionado `capability_matrix` com:

* `capability_code`;
* `status`;
* `maturity`;
* `direction`;
* `supported_scopes`;
* `supported_sync_modes`;
* dependências;
* restrições;
* requisitos de observabilidade;
* tier de piloto.

### `sync_schema`

Expandido semanticamente com:

* modos runtime e canônicos;
* gatilhos;
* retry;
* timeout;
* backoff;
* batch;
* polling;
* webhook;
* schedule;
* event-driven.

### `health_schema`

Expandido semanticamente com:

* severidade por estado;
* fontes de disponibilidade e latência;
* fontes de último sucesso e última falha;
* dependências;
* diagnóstico suportado;
* degradação por capability.

### `IntegrationFeature` e `IntegrationSyncPolicy`

Os payloads persistidos passaram a refletir o contrato:

* `IntegrationFeature.settings_payload` carrega semântica de capability;
* `IntegrationSyncPolicy.settings_payload` carrega semântica operacional de sync;
* sem substituir o runtime oficial.

## Duplicidades evitadas

* não foi criado novo catálogo de capabilities;
* não foi criada nova policy de sincronização;
* não foi criada nova estrutura de health;
* não foi criado novo mapeamento externo;
* não foi criado payload paralelo fora de `MarketplaceIntegracao` e dos modelos canônicos existentes.

## Aderência ao runtime

Implementação preservou:

* `ExternalRecordAssociation` como vínculo oficial;
* `IntegrationJob` como execução operacional;
* `IntegrationHealth` como health persistido;
* `IntegrationSyncPolicy` como política oficial;
* `SankhyaCanonicalAdapter` como adapter atual.

## Testes executados

### Aprovados

* `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py -q`
* `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -k 'not backoffice_nao_e_console_principal_da_configuracao' -q`
* `services/api/.venv/bin/python -m py_compile services/api/integracoes/sankhya/services/canonical_adapter.py services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
* `git diff --check`

### Falha pré-existente fora do escopo desta execução

* `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py::test_backoffice_nao_e_console_principal_da_configuracao -q`

Motivo:

* a tela `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx` não contém o texto esperado `"Jobs canônicos"`;
* esta execução não alterou frontend/backoffice;
* a falha não decorre da materialização do provider Sankhya.

## Resultado final

Status da execução: **CONCLUÍDA COM RESSALVA EXTERNA**

Conclusão técnica:

* o contrato canônico do provider ERP foi materializado no Sankhya sem criar estruturas paralelas;
* o runtime oficial foi preservado;
* os testes diretamente afetados pelo adapter materializado passaram;
* permanece uma falha estática pré-existente no teste de copy do backoffice, fora do escopo deste backend P0.
