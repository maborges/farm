# ERP-P0-02 — CHECK_INTEGRACAO_ERP Capabilities

## Resumo

O item `CHECK_INTEGRACAO_ERP` do Wizard deixou de ser dispensado por padrão e passou a consumir o runtime oficial de integrações ERP do tenant.

Nenhuma nova estrutura foi criada.

## Arquivos auditados

* `services/api/wizard/checklist_engine.py`
* `services/api/wizard/router.py`
* `services/api/integracoes/models.py`
* `services/api/integracoes/sankhya/services/canonical_adapter.py`
* `services/api/tests/unit/wizard/test_wizard_checklist_engine.py`
* `services/api/tests/unit/wizard/test_wizard_api.py`
* `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
* `docs/implementation/reports/ERP-P0-01-MATERIALIZACAO-PROVIDER-ATUAL.md`
* `docs/implementation/reports/ERP-P0-01B-CORRECAO-BACKOFFICE-GOVERNANCA.md`

## Arquivos alterados

* `services/api/wizard/checklist_engine.py`
* `services/api/wizard/router.py`
* `services/api/tests/unit/wizard/test_wizard_checklist_engine.py`
* `services/api/tests/unit/wizard/test_wizard_api.py`

## Regras reutilizadas

O checklist passou a reutilizar diretamente:

* `TenantIntegracao`
* `MarketplaceIntegracao`
* `IntegrationFeature`
* `IntegrationSyncPolicy`
* `IntegrationHealth`
* `ExternalRecordAssociation`
* `feature_schema` do provider
* `health_schema` do provider

## Duplicidades evitadas

Não foi criado:

* novo endpoint;
* novo domínio;
* nova tabela;
* nova migration;
* novo runtime;
* nova fonte de capability;
* nova fonte de health;
* nova policy paralela.

## Como o checklist passou a avaliar ERP

### 1. Declaração de uso

O Wizard agora distingue:

* tenant que opera sem ERP;
* tenant que declarou ERP no `escopo_modulos` ou no `diagnostico_inicial_snapshot`;
* tenant que já possui runtime ERP configurado.

### 2. Provider configurado

Quando ERP é declarado, o checklist procura configuração ERP canônica ativa do tenant em `TenantIntegracao` + `MarketplaceIntegracao`.

Sem configuração:

* retorna `PENDENTE`.

Sem ERP declarado nem configurado:

* retorna `DISPENSADO`.

### 3. Health mínimo

O checklist lê `IntegrationHealth`.

Regras aplicadas:

* health ausente → `PENDENTE`
* `AUTH_ERROR`, `CONFIG_ERROR`, `DISCONNECTED` → `FALHOU`
* `DEGRADED`, `PARTIAL_FAILURE`, `RATE_LIMITED` → permitido com ressalva, desde que o restante esteja OK

### 4. Capabilities P0

A validação usa a capability matrix do provider já materializada em `feature_schema.capability_matrix`.

No provider atual, o P0 restrito foi derivado de:

* `pessoas`
* `produtos`
* `financeiro`
* `nfe`

Além disso, o checklist exige:

* maturidade mínima compatível com piloto (`TESTED`, `PILOT_READY`, `PRODUCTION_READY`);
* requisitos de observabilidade mínimos em `observability_requirements`;
* diagnósticos mínimos em `health_schema.diagnostics`.

### 5. Policies mínimas

O checklist valida `IntegrationSyncPolicy` para as features P0 mínimas.

Sem policy ou com policy incompatível com os modos suportados:

* retorna `PENDENTE`.

### 6. Reconciliação e conflitos

O checklist consulta `ExternalRecordAssociation` por `tenant`, `config` e `provider`.

Regras aplicadas:

* associações em `CONFLICT` → `FALHOU`
* associações em `PENDING` → `PENDENTE`

## Cenários de teste cobertos

* tenant sem ERP declarado/configurado → `DISPENSADO`
* ERP configurado sem health → `PENDENTE`
* ERP configurado com health crítico → `FALHOU`
* ERP configurado com capabilities P0 incompletas → `FALHOU`
* ERP configurado com policies mínimas pendentes → `PENDENTE`
* ERP configurado com capabilities P0 e policies mínimas OK → `ATENDIDO`
* CTA do Wizard aponta para `/dashboard/settings/integracoes/erp`
* runtime ERP do checklist usa apenas escopos `TENANT` e `ESTABELECIMENTO`

## Lacunas remanescentes

* a validação de capabilities P0 ainda depende do contrato materializado do provider atual e, no Sankhya, a cobertura de `clientes` e `fornecedores` continua representada pela capability `pessoas`;
* a leitura de conflitos/reconciliação é agregada por configuração ERP, sem filtro por entidade funcional do piloto;
* não foi adicionada classificação mais fina de health além do runtime já persistido.

## Validações executadas

* `services/api/.venv/bin/python -m py_compile services/api/wizard/checklist_engine.py services/api/wizard/router.py services/api/tests/unit/wizard/test_wizard_checklist_engine.py services/api/tests/unit/wizard/test_wizard_api.py`
* `services/api/.venv/bin/pytest services/api/tests/unit/wizard/test_wizard_checklist_engine.py services/api/tests/unit/wizard/test_wizard_api.py -q`
* `git diff --check`

## Veredicto final

Status: **CONCLUÍDO**

Resultado:

* o Wizard agora consome provider, health, capabilities, policies e reconciliação do runtime oficial;
* operação sem ERP continua suportada;
* o CTA oficial permanece apontando para `/dashboard/settings/integracoes/erp`;
* não houve alteração arquitetural nem criação de infraestrutura paralela.
