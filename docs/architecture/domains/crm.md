# Domínio CRM do AgroSaaS

**Status:** Catálogo canônico do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio CRM cobre aquisição, relacionamento e conversão comercial. No AgroSaaS ele aparece principalmente no backoffice, com leads, pipeline, atividades e ofertas comerciais.

## 2. Objetivo

- Organizar o funil comercial.
- Capturar e qualificar leads.
- Controlar atividade de relacionamento.
- Estruturar propostas, pacotes e ofertas.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Pipeline | Gerenciar etapas do funil | `PipelineEstagio` | backoffice, vendas | IMPLEMENTADO |
| Leads | Registrar prospects e oportunidades | `LeadCRM` | tenant convertido, admin users | IMPLEMENTADO |
| Atividades | Seguir interações e follow-ups | `AtividadeCRM` | pipeline, time comercial | IMPLEMENTADO |
| Ofertas | Precificação e bundles | `ModuloOferta`, `PlanoComercial`, `OfertaPersonalizada` | billing, planos, tenant | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `PipelineEstagio` | Etapa do funil | CRM | leads | CRM |
| `LeadCRM` | Prospect ou oportunidade | CRM | estágio, atividades | CRM |
| `AtividadeCRM` | Interação com lead | CRM | lead | CRM |
| `ModuloOferta` | Produto comercial vendável | CRM | plano comercial | CRM |
| `PlanoComercial` | Bundle comercial | CRM | módulos | CRM |
| `OfertaPersonalizada` | Oferta customizada por lead | CRM | lead, plano | CRM |

## 5. Fluxos

```text
Lead captado
↓
Qualificação
↓
Atividades / follow-up
↓
Oferta
↓
Conversão
```

## 6. Eventos

- `LeadCriado`
- `LeadQualificado`
- `AtividadeRegistrada`
- `OfertaGerada`
- `LeadConvertido`
- `PlanoComercialAtualizado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Backoffice / SaaS | Venda e conversão | Alta | Crescimento de receita |
| Billing | Planos e faturamento | Alta | Comercialização SaaS |
| Tenant / onboarding | Criação de organização | Alta | Conversão para cliente |
| IA / marketing | Priorização de lead | Média | Eficiência comercial |

## 8. Regras de Negócio

1. Lead é pré-tenant; conversão pode criar tenant.
2. Pipeline ordena o funil comercial.
3. Oferta personalizada deve manter rastreabilidade de vigência.
4. CRM não deve invadir a modelagem operacional do cliente.
5. CRM é domínio comercial de aquisição, não de gestão agrícola.

## 9. Fronteiras

### Pertence

- Leads;
- Pipeline;
- Atividades;
- Ofertas;
- Planos comerciais;
- Precificação.

### Não pertence

- Safras;
- Produção;
- Estoque;
- Titularidade fundiária;
- Operação do cliente.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Pipeline e leads | IMPLEMENTADO | Backoffice ativo. |
| Ofertas comerciais | IMPLEMENTADO | Bundle e customização presentes. |
| Atividades | IMPLEMENTADO | Follow-up estruturado. |
| Conversão para tenant | PARCIAL | Integrado ao onboarding, mas depende do fluxo comercial. |

