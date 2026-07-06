# Domínio RH do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio RH gerencia colaboradores, departamentos, eSocial, diárias, empreitadas, segurança do trabalho e documentos de conformidade trabalhista.

## 2. Objetivo

- Organizar a estrutura de pessoas do trabalho.
- Controlar jornada, custo de mão de obra e eventos legais.
- Integrar segurança, operação e pagamento.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Estrutura Organizacional | Departamentos e lotação | `Departamento`, `ColaboradorRH` | Tenant, unidade produtiva | IMPLEMENTADO |
| eSocial | Eventos legais | `EsocialEvento` | Governo, certificado digital | IMPLEMENTADO |
| Remuneração Operacional | Diárias e empreitadas | `LancamentoDiaria`, `Empreitada` | Financeiro, safra | IMPLEMENTADO |
| Segurança do Trabalho | EPI/EPC e documentos | `ItemSegurancaRH`, `EntregaSegurancaRH`, `DocumentoSST` | Frota, operacional | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `Departamento` | Estrutura interna de RH | RH | tenant | RH |
| `ColaboradorRH` | Especialização de pessoa para trabalho | RH | pessoa, departamento, unidade | RH |
| `EsocialEvento` | Evento trabalhista oficial | RH | colaborador | RH |
| `LancamentoDiaria` | Pagamento por diária | RH | colaborador, safra | RH |
| `Empreitada` | Contratação por serviço | RH | colaborador, safra | RH |
| `ItemSegurancaRH` | Cadastro de EPI/EPC | RH | entregas | RH |
| `EntregaSegurancaRH` | Entrega de segurança | RH | colaborador, item | RH |
| `DocumentoSST` | Documento de SST | RH | colaborador, tenant | RH |

## 5. Fluxos

```text
Cadastro de colaborador
↓
Departamento / vínculo
↓
Diária / empreitada / evento eSocial
↓
Segurança do trabalho
↓
Pagamento e auditoria
```

## 6. Eventos

- `ColaboradorAdmitido`
- `ColaboradorDesligado`
- `DiariaLancada`
- `EmpreitadaCriada`
- `EsocialEnviado`
- `EpiEntregue`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Financeiro | Pagamento de diárias e empreitadas | Alta | Caixa e custo |
| Agrícola | Mão de obra de safra | Alta | Execução de campo |
| Frota | Segurança e operação | Média | Uso de equipamento |
| Operacional | Apontamentos e jornada | Alta | Controle de trabalho |
| Certificações | Segurança e conformidade | Média | Evidência auditável |

## 8. Regras de Negócio

1. Colaborador RH é especialização de pessoa.
2. Evento de eSocial deve ser auditável.
3. Diária e empreitada podem ser vinculadas a safra.
4. A segurança do trabalho deve preservar validade e entrega.
5. RH não é dono do financeiro corporativo, apenas da folha e da jornada operacional.

## 9. Fronteiras

### Pertence

- Colaboradores;
- Departamentos;
- eSocial;
- Diárias;
- Empreitadas;
- Segurança do trabalho;
- Documentos SST.

### Não pertence

- Receita, despesa e fluxo de caixa geral;
- Titularidade fundiária;
- Execução agrícola;
- Comercialização.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Colaboradores e departamentos | IMPLEMENTADO | Cadastro e organização ativos. |
| eSocial | IMPLEMENTADO | Fluxo e integração próprios. |
| Diárias e empreitadas | IMPLEMENTADO | Ligação com safra e unidade produtiva. |
| Segurança do trabalho | IMPLEMENTADO | EPI/EPC e documentos presentes. |
| Folha / relatórios ampliados | PARCIAL | Evolutivo, conforme integração com financeiro. |

