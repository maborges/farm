# ERP-CAPABILITY-01 - Auditoria de Capacidades de Providers ERP

Data: 2026-07-09
Escopo: auditoria arquitetural e funcional sem alteracao de codigo

## 1. Objetivo

Auditar o repositorio para verificar se ja existem estruturas, campos e contratos suficientes para representar capabilities de providers ERP sem criar duplicidade.

## 2. Arquivos auditados

Documentacao:

- `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
- `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
- `docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md`
- `docs/implementation/reports/ERP-ALIGN-03-CONSOLIDACAO-WIZARD-CONSOLE-RUNTIME.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`

Runtime e UX:

- `services/api/integracoes/models.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/wizard/checklist_engine.py`
- `services/api/wizard/router.py`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`

## 3. Conceitos existentes reutilizados

Ja existem e devem ser reutilizados:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`
- `TenantIntegracao.connection_payload`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`

## 4. Decisao por estrutura existente

### 4.1 Reutilizar

- `IntegrationFeature` como habilitacao concreta de capability por tenant;
- `IntegrationSyncPolicy` como modo operacional por capability;
- `IntegrationHealth` e `IntegrationJob` como evidencia observavel;
- `provider_definition` e `feature_schema` como catalogo declarativo do provider.

### 4.2 Estender semanticamente

- `provider_definition` para declarar status, maturidade, escopo, direcao, dependencias e restricoes;
- `feature_schema` para declarar catalogo detalhado de capabilities;
- `settings_payload` de feature e policy para metadados complementares;
- consumo do wizard para avaliar capability minima de piloto.

### 4.3 Consolidar

- capability matrix do provider com a UX do console ERP;
- leitura do wizard com provider, health, features e policies reais;
- classificacao de piloto restrito, ampliado e exportador com base em capability matrix.

### 4.4 Depreciar

Nao houve necessidade de depreciar estrutura de runtime.

Permanece como lacuna funcional, nao como alvo de deprecacao:

- `CHECK_INTEGRACAO_ERP` hoje ainda e simplificado e dispensado por padrao.

## 5. Duplicidades evitadas

Nao criar:

- nova tabela de capabilities;
- nova tabela de feature;
- nova politica de sync;
- novo modelo de provider definition;
- novo runtime de health;
- novo console de capability.

## 6. Evidencias encontradas no runtime

### 6.1 Provider definition e schemas

O adapter Sankhya ja materializa:

- `provider_definition={"provider": "sankhya", "version": 1}`
- `feature_schema={"supported_features": ...}`
- `sync_schema={"default_trigger": ...}`
- `health_schema={"states": ...}`

### 6.2 Features existentes no provider atual

O catalogo inicial do Sankhya ja declara:

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`
- `estoque`

Comportamento observado:

- `pessoas`, `produtos`, `financeiro`, `nfe` habilitadas;
- `pedidos` e `estoque` declaradas como futuras e desabilitadas;
- cada feature recebe `settings_payload` com `supported_modes`.

### 6.3 Policies existentes

O runtime ja suporta:

- modo;
- prioridade;
- retry;
- batch;
- backoff;
- timeout;
- idempotencia;
- trigger expression;
- payload extensivel.

### 6.4 UX existente

O console ERP do tenant ja mostra:

- `features_habilitadas`
- `policies_resumidas`
- status;
- health;
- jobs;
- logs;
- reconciliacao manual.

### 6.5 Lacuna no wizard

O `CHECK_INTEGRACAO_ERP` ainda retorna:

- `DISPENSADO`
- com mensagem de que nao ha ERP configurado para obrigatoriedade de sincronismo

Conclusao:

- o wizard ainda nao consome capability matrix, policy e health como criterio real de prontidao.

## 7. Aplicacao conceitual inicial ao Sankhya

### 7.1 Supported ou tested

- Pessoas
- Produtos
- Health
- Jobs
- Logs
- Reconciliacao manual

### 7.2 Partial

- Financeiro
- NFe

### 7.3 Unknown

- CT-e
- MDF-e
- documentos de exportacao
- barter
- contratos
- comercializacao ampliada

### 7.4 Unsupported ou not applicable

- operacao agricola como capability ERP
- operacao pecuaria como capability ERP
- escopo por unidade produtiva, talhao, safra ou cultivo

## 8. Conclusoes da auditoria

Conclusoes objetivas:

- o runtime atual ja suporta um modelo canonico de capabilities sem nova tabela;
- `IntegrationFeature` e `IntegrationSyncPolicy` sao suficientes como base operacional;
- a principal lacuna nao e estrutural, e semantica e de governanca de uso;
- Sankhya ja serve como implementacao inicial de referencia, mas ainda nao como matriz completa de capability madura para piloto ampliado ou exportador.

## 9. Recomendacao objetiva para a proxima etapa

Proxima execucao recomendada:

1. formalizar o contrato de `provider_definition` e `feature_schema` no provider atual;
2. evoluir o Wizard para consumir health, features e policies minimas P0;
3. definir a apresentacao funcional da capability matrix no console ERP e no backoffice, sem criar nova tela paralela.
