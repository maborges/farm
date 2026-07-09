# ERP-PROVIDER-CONTRACT-02 - Auditoria do Contrato de Provider ERP

Data: 2026-07-09
Escopo: auditoria arquitetural e documental sem alteracao de codigo

## 1. Objetivo

Verificar se o repositorio ja possui contratos equivalentes ou parciais para `provider_definition`, `feature_schema`, `sync_schema` e `health_schema`, evitando duplicidade.

## 2. Arquivos auditados

Documentacao:

- `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
- `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
- `docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md`
- `docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/architecture/INTEGRATIONS-LIFECYCLE-01.md`

Runtime:

- `services/api/integracoes/models.py`
- `services/api/integracoes/schemas.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/services/sync_service.py`

## 3. Estruturas encontradas

### 3.1 Ja existentes e reutilizadas

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.connection_schema`
- `MarketplaceIntegracao.credential_schema`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`

### 3.2 Ja existentes, mas parciais

No Sankhya:

- `provider_definition` existe com payload minimo: `provider` e `version`;
- `feature_schema` existe como lista de `supported_features`;
- `sync_schema` existe com `default_trigger`;
- `health_schema` existe com lista de `states`.

Conclusao:

- existe contrato parcial;
- nao existe ainda contrato ERP canonico consolidado;
- a necessidade era consolidar, nao recriar.

## 4. Decisao por estrutura

### 4.1 Reutilizar

- `MarketplaceIntegracao` como origem oficial dos contratos do provider;
- `IntegrationFeature` como habilitacao concreta;
- `IntegrationSyncPolicy` como policy concreta;
- `IntegrationHealth` como snapshot runtime;
- `IntegrationJob` como execucao observavel.

### 4.2 Estender

- `provider_definition` com identidade, maturidade, escopo, autenticacao e suporte;
- `feature_schema` com contrato completo de capability;
- `sync_schema` com envelope declarativo coerente com `IntegrationSyncPolicy`;
- `health_schema` com envelope declarativo coerente com `IntegrationHealth`.

### 4.3 Consolidar

- capability de `ERP-CAPABILITY-01` dentro de `feature_schema`;
- leitura do console ERP com base nesses contratos;
- leitura de wizard e backoffice com base nesses contratos.

### 4.4 Depreciar

Nao ha necessidade de depreciar estruturas de runtime.

O que deve ser considerado insuficiente, nao depreciado:

- payloads minimos do Sankhya como contrato definitivo.

## 5. Duplicidades evitadas

Nao criar:

- segundo `provider_definition`;
- segundo `feature_schema`;
- segundo `sync_schema`;
- segundo `health_schema`;
- segunda policy;
- segundo modelo de capability;
- novo runtime paralelo.

## 6. Aplicacao conceitual ao Sankhya

O Sankhya:

- comprova que o runtime suporta um provider ERP real;
- comprova que os quatro contratos ja existem como colunas oficiais;
- ainda nao preenche todos os campos funcionais que um contrato canonico ERP deveria exigir;
- deve ser tratado como implementacao de referencia, nao como formato final da plataforma.

## 7. Lacunas futuras

Lacunas objetivas:

- formalizar semanticamente os campos obrigatorios do `provider_definition`;
- enriquecer `feature_schema` para capability matrix completa;
- formalizar `sync_schema` sem depender apenas de `settings_payload` ad hoc;
- formalizar `health_schema` acima da lista de estados;
- alinhar console, backoffice e wizard para consumir o contrato consolidado.

## 8. Conclusao

Conclusao objetiva:

- o contrato parcial ja existe;
- nao havia espaco arquitetural para criar um segundo contrato;
- a execucao correta era consolidar o contrato canonico em documentacao oficial.

## 9. Recomendacao objetiva para a proxima etapa

Proxima execucao recomendada:

1. especificar a apresentacao funcional do contrato canonico no console ERP;
2. definir como o wizard vai consumir `feature_schema`, `sync_schema` e `health_schema` para checklist ERP real;
3. avaliar a necessidade futura de normalizar enums documentais do contrato para consumo transversal sem alterar o runtime atual.
