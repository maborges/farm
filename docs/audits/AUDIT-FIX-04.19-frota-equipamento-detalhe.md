# Auditoria e Diagnóstico — Detalhe do Equipamento (`[equipamentoId]/page.tsx`)

Este documento mapeia o comportamento técnico e dependências do componente original `page.tsx` de detalhes do equipamento da frota antes de realizar a refatoração para RSC Shell.

## 1. Mapeamento Geral do Componente

- **Roteamento e URL**: `[equipamentoId]/page.tsx`
  - Captura `equipamentoId` através de parâmetros de rota.
  - Filtro local de período (`periodo` via `useState` de string): opções `"30" | "90" | "180" | "all"`.
- **Estado de Tiers**:
  - `hasProfessionalTier`: Verificação do plano Profissional.
  - `hasEnterpriseTier`: Verificação do plano Enterprise.
- **Interatividade & Estados Locais**:
  - `periodo`: Define a janela de tempo dos indicadores (padrão: `"90"`).
- **Dependências de Janela/Navegador**:
  - Não há dependências diretas de `window`, `document` ou `localStorage`.
- **Mutations**:
  - Nenhuma mutation declarada.

## 2. Inventário de Queries (TanStack Query)

| Query Key / Endpoint | Plano Requerido | Parâmetros | Enabled |
| :--- | :--- | :--- | :--- |
| `["frota", "dashboard", "equipamento", equipamentoId, activeFazendaId, periodo]` <br> `/frota/dashboard/equipamentos/${equipamentoId}` | **Profissional** | `periodo_dias`, `unidade_produtiva_id` | `Boolean(equipamentoId) && hasProfessionalTier` |
| `["frota", "consumo", "equipamento", equipamentoId, activeFazendaId]` <br> `/frota/consumo/equipamentos/${equipamentoId}` | **Profissional** | `unidade_produtiva_id` | `Boolean(equipamentoId) && hasProfessionalTier` |
| `["frota", "disponibilidade", "equipamento", equipamentoId, activeFazendaId]` <br> `/frota/disponibilidade/equipamentos/${equipamentoId}` | **Profissional** | `unidade_produtiva_id` | `Boolean(equipamentoId) && hasProfessionalTier` |
| `["frota", "custos", "equipamento", equipamentoId, activeFazendaId, periodo]` <br> `/frota/custos/equipamentos/${equipamentoId}` | **Enterprise** | `periodo_dias`, `unidade_produtiva_id` | `Boolean(equipamentoId) && hasEnterpriseTier` |
| `["frota", "inteligencia", "equipamento", equipamentoId, activeFazendaId]` <br> `/frota/inteligencia/equipamentos/${equipamentoId}` | **Enterprise** | `unidade_produtiva_id` | `Boolean(equipamentoId) && hasEnterpriseTier` |
| `["frota", "agricultura", "equipamento", equipamentoId, activeFazendaId]` <br> `/frota/agricultura/equipamentos/${equipamentoId}` | **N/A** (Restringido em UI) | `unidade_produtiva_id` | `Boolean(equipamentoId)` |

## 3. Estratégia de Divisão (Server vs Client)

### No Servidor (`page.tsx`)
- Capturar `equipamentoId` através do argumento assíncrono `params`.
- Capturar `unidade_produtiva_id` a partir do `searchParams`.
- **Pré-carregamento Seguro**: Executar a chamada ao endpoint básico `/frota/dashboard/equipamentos/${equipamentoId}` com período padrão `90` dias.
- **Tratamento de Exceções**: A chamada deve ser envelopada em um bloco `try/catch`. Caso o usuário não tenha o plano Profissional, o endpoint do backend retornará um erro `402 Payment Required`. Capturaremos este erro no servidor definindo `initialData` como `null`, evitando a quebra geral da página.

### No Cliente (`EquipamentoDetalheClient.tsx`)
- Concentrar a lógica cliente de `useHasTier()`, controle de filtros locais de períodos (`useState`), e todas as 6 queries do TanStack Query.
- Se os dados do servidor estiverem preenchidos (`initialData !== null`) e os parâmetros de fazenda/período coincidirem com o padrão inicial, hidratar a query `/frota/dashboard/equipamentos` via prop `initialData` do `useQuery`.
- Renderizar a interface visual com as tabelas, resumos, e cards de upgrade pertinentes para planos inferiores.
