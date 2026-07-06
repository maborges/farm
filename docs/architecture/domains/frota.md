# Domínio Frota do AgroSaaS

**Status:** Catálogo oficial do domínio  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md)

## 1. Visão Geral

O Domínio Frota organiza o uso, a manutenção, a disponibilidade e o custo de equipamentos e máquinas. Ele também registra jornadas operacionais e o consumo associado à agricultura e a outras áreas do tenant.

## 2. Objetivo

- Controlar o ciclo de vida dos equipamentos.
- Registrar manutenção preventiva e corretiva.
- Medir consumo e uso agrícola.
- Integrar a frota ao estoque, ao financeiro e ao agrícola.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades principais | Integrações | Status |
|---|---|---|---|---|
| Manutenção | Planejar e executar oficina | `PlanoManutencao`, `OrdemServico`, `RegistroManutencao` | Estoque, financeiro, RH | IMPLEMENTADO |
| Jornadas | Registrar operação do equipamento | `JornadaEquipamento` | Agrícola, apontamento, frota | IMPLEMENTADO |
| Consumo | Medir uso e insumos | serviços de consumo e custo | Estoque, agrícola, financeiro | IMPLEMENTADO |
| Disponibilidade | Controlar equipamento disponível | serviços de disponibilidade | Manutenção, operação | IMPLEMENTADO |
| Checklist e Automação | Apoiar execução padrão | checklist, automação | Oficina, segurança, operação | PARCIAL |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `PlanoManutencao` | Regra periódica de manutenção | Frota | equipamento | Frota |
| `OrdemServico` | Manutenção oficina | Frota | equipamento, safra, talhão | Frota |
| `ItemOrdemServico` | Peça/insumo consumido na OS | Frota | OS, produto, estoque | Frota |
| `RegistroManutencao` | Histórico da manutenção | Frota | equipamento, OS | Frota |
| `JornadaEquipamento` | Jornada operacional do equipamento | Frota | operador, unidade, safra, talhão | Frota |

## 5. Fluxos

```text
Uso do equipamento
↓
Jornada
↓
Consumo / apontamento
↓
Manutenção / OS
↓
Disponibilidade
```

## 6. Eventos

- `JornadaIniciada`
- `JornadaFinalizada`
- `OSAberta`
- `OSConcluida`
- `ManutencaoRegistrada`
- `ConsumoAgricolaConsolidado`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Agrícola | Jornada e operação em talhão | Alta | Custo e produtividade |
| Estoque | Peças e combustível | Alta | Baixa física e valuation |
| Financeiro | Rateio e custo | Alta | Apuração econômica |
| RH | Operador e segurança | Média | Alocação humana |
| Compras | Aquisição de peças | Média | Reposição |

## 8. Regras de Negócio

1. Um equipamento deve pertencer ao tenant.
2. Manutenção preventiva deve ser rastreável por equipamento.
3. Jornada deve ter início e, quando encerrada, fim.
4. Itens de OS devem consumir estoque quando aplicável.
5. O uso agrícola da frota pode vincular safra e talhão.

## 9. Fronteiras

### Pertence

- Equipamento operacional;
- Ordem de serviço;
- Jornada;
- Manutenção;
- Consumo e disponibilidade.

### Não pertence

- Compra do equipamento como ativo;
- Cadastro territorial;
- Titularidade fundiária;
- Comercialização agrícola.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Manutenção | IMPLEMENTADO | Amplo e consolidado. |
| Jornadas | IMPLEMENTADO | Base para custo e uso. |
| Consumo agrícola | IMPLEMENTADO | Integração explícita com safra/talhão. |
| Inteligência de frota | IMPLEMENTADO | Painéis e benchmark presentes. |
| Checklist / automação | PARCIAL | Evolutivo e ampliável. |

