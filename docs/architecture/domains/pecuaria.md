# Domínio Pecuária do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Pecuária concentra a gestão operacional do rebanho, dos piquetes, dos lotes, dos manejos e das rotinas produtivas de origem animal. Ele organiza a operação pecuária como um fluxo rastreável de área, animal, manejo, produção e resultado.

Esse domínio consome a base territorial do AgroSaaS, mas não é dono da titularidade fundiária nem da geometria oficial da propriedade.

## 2. Objetivo

- Organizar a operação pecuária por unidade produtiva.
- Controlar lotes, piquetes e manejos.
- Registrar produção animal e eventos de manejo.
- Integrar a pecuária ao financeiro, ao estoque, à frota e ao ambiental.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Lotes e Piquetes | Estruturar a unidade espacial do rebanho | `Lote`, `Piquete`, `Animal` | Propriedades, Ambiental, Frota | IMPLEMENTADO |
| Manejos | Registrar rotinas de manejo e movimentação | `Manejo`, eventos de manejo | Produção, Frota, RH | IMPLEMENTADO |
| Produção Animal | Controlar resultados produtivos | `Producao` / leite / genética / confinamento | Financeiro, Comercialização, Estoque | PARCIAL |
| Genética | Organizar linhagem e reprodutividade | cadastros e eventos genéticos | Produção, RH | PARCIAL |
| Confinamento e Leite | Apoiar sistemas intensivos | registros específicos de confinamento e leite | Financeiro, Estoque, Frota | PARCIAL |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `Piquete` | Subdivisão operacional da fazenda para pastejo | Pecuária | `Tenant`, `UnidadeProdutiva` | Pecuária |
| `Lote` | Agrupamento operacional de animais | Pecuária | rebanho, manejos, produção | Pecuária |
| `Manejo` | Registro de evento de manejo animal | Pecuária | `Lote`, `Piquete`, `Animal` | Pecuária |
| `Animal` | Unidade individual de rebanho | Pecuária | lote, genealogia, produção | Pecuária |
| `Leite` | Produção leiteira e suas medições | Pecuária | tanque, lote, período | Pecuária |
| `Confinamento` | Gestão intensiva do rebanho | Pecuária | lote, dieta, desempenho | Pecuária |

## 5. Fluxos

```text
Cadastro do rebanho
↓
Lote / Piquete
↓
Manejo
↓
Produção
↓
Apuração de custo
↓
Resultado operacional
```

## 6. Eventos

- `LoteCriado`
- `AnimalMovimentado`
- `ManejoRegistrado`
- `ProducaoAnimalLancada`
- `PiqueteAtualizado`
- `ConfinamentoFechado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Propriedades | Área física e piquetes | Alta | Base espacial do rebanho |
| Financeiro | Custo, receita e resultado | Alta | Apuração econômica |
| Estoque | Ração, insumos, medicamentos | Alta | Consumo e reposição |
| Frota | Transporte, manutenção e abastecimento | Média | Suporte operacional |
| RH | Manejo, tratadores e equipe | Média | Mão de obra e segurança |
| Ambiental | Pastagem, APP, outorga e carbono | Média | Conformidade e risco |

## 8. Regras de Negócio

1. Um lote deve pertencer a um tenant.
2. Um manejo deve estar associado a um lote ou piquete.
3. Piquete é referência operacional e não substitui o domínio territorial.
4. O domínio pecuário pode consumir área rural, mas não pode redefinir a área oficial.
5. Produção pecuária deve ser rastreável por lote e período.

## 9. Fronteiras

### Pertence

- Lotes;
- Piquetes;
- Manejos;
- Produção animal;
- Indicadores zootécnicos;
- Confinamento e leite.

### Não pertence

- Titularidade fundiária;
- Matrícula, CAR, CCIR e contratos rurais;
- Cadastro territorial oficial;
- Contabilidade corporativa.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Piquetes | IMPLEMENTADO | Base operacional clara no código. |
| Manejos | IMPLEMENTADO | Fluxo operacional ativo. |
| Lotes | IMPLEMENTADO | Núcleo do rebanho. |
| Animal | IMPLEMENTADO | Especialização do rebanho. |
| Leite | PARCIAL | Superfície presente no frontend e no backend, mas varia por subfluxo. |
| Genética | PARCIAL | Forte no front/back office, ainda evolutivo. |
| Confinamento | PARCIAL | Modelo funcional, mas dependente da operação. |

