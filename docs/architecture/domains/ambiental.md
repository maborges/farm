# Domínio Ambiental do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md), [AGRI-DOMAIN-001](../standards/AGRI-DOMAIN-001-territorial-fundiario.md)

## 1. Visão Geral

O Domínio Ambiental trata conformidade ambiental, monitoramento, CAR, outorgas, alertas, vegetação, risco e, de forma transversal, carbono e evidências para certificação.

## 2. Objetivo

- Registrar e monitorar requisitos ambientais.
- Centralizar dados de CAR, alertas e outorgas.
- Alimentar ESG, certificações e rastreabilidade.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| CAR | Guardar cadastro ambiental rural | `RegistroCAR`, `CAR` | territorial, fundiário, imagem | IMPLEMENTADO |
| Alertas Ambientais | Registrar e tratar risco e pendência | `AlertaAmbiental` | satélite, monitoramento, territorial | IMPLEMENTADO — manual |
| Outorgas | Controlar uso de água | `OutorgaHidrica` | irrigação, compliance | IMPLEMENTADO |
| Monitoramento APP | Acompanhar preservação | `MonitoramentoAPP` | CAR, NDVI, satélite | BASE PARCIAL |
| Carbono | Registrar emissões e projeto | `CarbonoEmissao`, `CarbonoProjeto`, `CarbonoRelatorio` | ESG, certificações | PARCIAL |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `RegistroCAR` | Registro de CAR por unidade | Ambiental | tenant, unidade produtiva | Ambiental |
| `CAR` | Modelo detalhado do cadastro ambiental | Ambiental | unidade produtiva, monitoramentos | Ambiental |
| `AlertaAmbiental` | Evento de risco ambiental | Ambiental | unidade produtiva, talhão | Ambiental |
| `OutorgaHidrica` | Uso legal de água | Ambiental | unidade produtiva | Ambiental |
| `MonitoramentoAPP` | Evolução de APP e NDVI | Ambiental | CAR | Ambiental |

## 5. Fluxos

```text
Cadastro ambiental
↓
Monitoramento
↓
Alerta / pendência
↓
Correção / conformidade
↓
Evidência ESG
```

## 6. Eventos

- `CARRegistrado`
- `AlertaAmbientalGerado`
- `OutorgaVencendo`
- `APPMonitorada`
- `CarbonoAtualizado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Territorial | Geometria, área e propriedade | Alta | Base do cadastro ambiental |
| Imóveis Rurais | Titularidade e documentação | Alta | Conformidade jurídica |
| Agrícola | Talhões, rastreabilidade, NDVI | Alta | Uso produtivo do território |
| Certificações | Evidência e auditoria | Alta | Prontidão de certificação |
| Projeto Raízes | Cadeia de custódia e origem | Alta | Exportação e due diligence |

## 8. Regras de Negócio

1. CAR é uma evidência ambiental e não substitui o domínio fundiário.
2. Alertas devem ser auditáveis.
3. Outorga deve ter vigência e status.
4. Carbono é transversal e não cria fonte paralela de território.
5. O domínio ambiental pode espelhar dados territoriais, mas não pode editá-los como origem.

## 9. Fronteiras

### Pertence

- CAR;
- APP;
- Reserva legal;
- Alertas;
- Outorgas;
- Carbono;
- Monitoramento ambiental.

### Não pertence

- Safra e produção;
- Titularidade fundiária;
- Execução operacional de campo;
- Financeiro corporativo.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| CAR | IMPLEMENTADO | Estrutura explícita no backend. |
| Alertas | IMPLEMENTADO | Risco e compliance ativos. |
| Outorgas | IMPLEMENTADO | Gestão hídrica presente. |
| Monitoramento APP | BASE PARCIAL | Serviços de imagem/NDVI existem, mas o fluxo satelital e o mapa ainda não estão integrados às rotas Ambientais. |
| Carbono | PARCIAL | Funcionalidade emergente e transversal. |

## 11. Fundação de dados e autorização

A Fase 1 consolidou o contrato das entidades existentes sem criar uma fonte territorial paralela:

- `unidade_produtiva_id` é o vínculo canônico das entidades Ambientais que representam uma propriedade/unidade;
- `tenant_id` é obrigatório e filtrado no service e na camada de RLS;
- CAR, alertas e outorgas exigem `unidade_produtiva_id`, garantindo tratamento por fazenda;
- os identificadores oficiais (`car_numero`, `ccir_numero`, `nirf`, `numero_matricula` e `sigef_codigo`) continuam no domínio Imóveis Rurais e são consultáveis via `GET /ambiental/unidades/{unidade_produtiva_id}/contexto-fundiario`, usando `PropriedadeImovel`;
- as rotas exigem contratação do módulo e permissão granular por ação;
- CAR, alertas, outorgas e carbono possuem schemas de entrada com enums e validações básicas;
- a migration `20260826_ambiental_foundation` normaliza o legado e aplica políticas RLS às tabelas Ambientais existentes;
- monitoramento satelital, APP/RL espacial, documentos, resíduos, CCIR e MRV completo permanecem nas fases seguintes.

As permissões seguem o formato `ambiental:<recurso>:<ação>`, com ações `view`, `list`, `create`, `edit`, `delete` e `export` conforme o fluxo.
