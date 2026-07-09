# ERP Architecture Index

Status: APROVADA
Categoria: Indice Arquitetural
Tipo: Organizacao de Leitura
Data: 2026-07-09

## 1. Objetivo

Organizar a leitura da arquitetura ERP do AgroSaaS sem criar regra nova.

Este indice apenas informa:

- ordem de leitura;
- funcao de cada documento;
- dependencias entre documentos;
- status atual;
- visao geral da arquitetura ERP.

## 2. Ordem oficial de leitura

1. `docs/architecture/INTEGRATIONS-ARCH-01.md`
2. `docs/architecture/INTEGRATIONS-ARCH-02.md`
3. `docs/architecture/INTEGRATIONS-LIFECYCLE-01.md`
4. `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
5. `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
6. `docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md`
7. `docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md`
8. `docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md`
9. `docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md`

## 3. Funcao de cada documento

### 3.1 Base do dominio Integracoes

- `INTEGRATIONS-ARCH-01`
  - define o dominio Integracoes e os escopos oficiais.
- `INTEGRATIONS-ARCH-02`
  - define o runtime generico de providers, features, policies e health.
- `INTEGRATIONS-LIFECYCLE-01`
  - define lifecycle e operacao oficial das integracoes.

### 3.2 Especializacao ERP

- `ERP-DOMAIN-01`
  - define ownership, direcao, conflito e prioridade por entidade ERP.
- `ERP-CONSOLE-01`
  - define o console administrativo de integracoes ERP.
- `ERP-GOV-02`
  - define guardrails obrigatorios para qualquer integracao ERP.

### 3.3 Semantica funcional do provider

- `ERP-CAPABILITY-01`
  - define capability matrix, maturidade e tiers de piloto.
- `ERP-PROVIDER-CONTRACT-02`
  - define como o provider deve declarar `provider_definition`, `feature_schema`, `sync_schema` e `health_schema`.

### 3.4 Consolidacao final

- `ERP-CONSOLIDATION-03`
  - fecha a auditoria final da arquitetura ERP.

## 4. Dependencias entre documentos

Fluxo oficial:

```text
INTEGRATIONS-ARCH-01
  ↓
INTEGRATIONS-ARCH-02
  ↓
INTEGRATIONS-LIFECYCLE-01
  ↓
ERP-DOMAIN-01
  ↓
ERP-CONSOLE-01
  ↓
ERP-GOV-02
  ↓
ERP-CAPABILITY-01
  ↓
ERP-PROVIDER-CONTRACT-02
  ↓
ERP-CONSOLIDATION-03
```

## 5. Status dos documentos

| Documento | Status | Funcao |
| --------- | ------ | ------ |
| `INTEGRATIONS-ARCH-01` | APROVADA | Dominio Integracoes |
| `INTEGRATIONS-ARCH-02` | APROVADA | Runtime generico |
| `INTEGRATIONS-LIFECYCLE-01` | APROVADA | Lifecycle oficial |
| `ERP-DOMAIN-01` | APROVADA | Ownership e dominio ERP |
| `ERP-CONSOLE-01` | APROVADA | Console ERP |
| `ERP-GOV-02` | APROVADA | Guardrails ERP |
| `ERP-CAPABILITY-01` | APROVADA | Capability matrix ERP |
| `ERP-PROVIDER-CONTRACT-02` | APROVADA | Contrato do provider ERP |
| `ERP-CONSOLIDATION-03` | APROVADA | Auditoria final da arquitetura ERP |

## 6. Visao geral

A arquitetura ERP do AgroSaaS esta organizada em tres camadas:

- dominio e runtime de integracoes;
- especializacao ERP;
- consolidacao de capability e contrato do provider.

Conclusao atual:

- a arquitetura ERP esta consolidada;
- Sankhya e apenas provider de referencia;
- o runtime atual e suficiente para guiar implementacao;
- a proxima fase e implementacao, nao nova arquitetura.
