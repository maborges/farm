# BUSINESS-DOMAIN-08 — CPR / Barter

## Contexto

* O módulo **CPR** (Compensação de Produção Rural) e **Barter** permitem acordos de troca de produtos agrícolas por insumos ou serviços.
* Ainda não há implementação de contratos que suportem esse tipo de transação.

## Objetivo

Definir a modelagem de domínio que suporte:
1. **Tipos de Contrato** – `CPRContract`, `BarterContract`.
2. **Entidades Principais** – `Producer`, `Partner`, `Asset`, `CompensationPlan`.
3. **Fluxo de Negócio** – Registro, validação, cálculo de compensação, aceitação.
4. **Regras de Negócio** – Limites de volume, regras de preço, prazo de liquidação.

## Modelo de Domínio (Oficial)

```mermaid
classDiagram
    class Producer {
        +id: UUID
        +name: string
        +profile: ProducerProfile
    }
    class Partner {
        +id: UUID
        +name: string
    }
    class Asset {
        +id: UUID
        +type: enum {Produtor, Insumo, Serviço}
        +quantity: number
        +unit: string
    }
    class CompensationPlan {
        +id: UUID
        +description: string
        +validFrom: date
        +validTo: date
    }
    class CPRContract {
        +id: UUID
        +producer: Producer
        +partner: Partner
        +asset: Asset
        +plan: CompensationPlan
        +status: enum {Draft, Pending, Active, Completed, Cancelled}
    }
    class BarterContract {
        +id: UUID
        +producer: Producer
        +partner: Partner
        +producerAsset: Asset
        +partnerAsset: Asset
        +status: enum {Draft, Pending, Active, Completed, Cancelled}
    }
    Producer --> CPRContract
    Partner --> CPRContract
    Asset --> CPRContract
    CompensationPlan --> CPRContract
    Producer --> BarterContract
    Partner --> BarterContract
    Asset --> BarterContract
```

## Requisitos Funcionais

* **RF01** – Cadastro de contratos CPR/Barter.
* **RF02** – Cálculo automático de compensação baseada em peso e qualidade.
* **RF03** – Histórico de trocas e auditoria.
* **RF04** – Integração com módulo **Financeiro** para registro de pagamentos.

## Requisitos Não‑Funcionais

* **RNF01** – Segurança: validação de usuários via RBAC.
* **RNF02** – Performance: consultas via TanStack Query, cache em 5 min.
* **RNF03** – Escalabilidade: suporte a 10 k contratos simultâneos.

## Considerações de Segurança (SecureCoder)

* **Entrada de Dados** – Sanitização de campos free‑text.
* **Autorização** – Apenas usuários com role `contract_manager` podem criar ou editar contratos.
* **Auditoria** – Todos os eventos de criação/alteração devem ser registrados em `AuditLog`.

---

*Este documento segue o padrão de modelagem de domínio usado nos demais BUSINESS‑DOMAIN.*
