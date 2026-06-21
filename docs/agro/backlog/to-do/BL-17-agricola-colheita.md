# BL-17 — A5_COLHEITA

**Módulo:** `A5_COLHEITA`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `A1_PLANEJAMENTO`

## Contexto

Colheita, romaneios, produtividade e rastreabilidade do lote.

## Gaps observados

- Entrega existe, mas há espaço para aprofundar indicadores e integração fiscal.
- Beneficiamento e rastreabilidade seguem como áreas adjacentes a consolidar.

## User Stories

### US-17.1 — Romaneio de colheita
**Como** operador, **quero** registrar romaneios, **para** medir produtividade e receber produção.

**Critérios de aceite:**
- [x] CRUD de romaneios
- [x] KPIs de colheita
- [x] Cálculo de produtividade

### US-17.2 — Encadeamento com financeiro
**Como** gestor, **quero** que a colheita gere dados financeiros, **para** fechar o ciclo operacional.

**Critérios de aceite:**
- [x] Integração com receitas
- [x] Descontos de qualidade
- [x] Rastreabilidade por lote

## Tarefas técnicas

- [x] Cobrir cenário de integração com financeiro
- [x] Refinar métricas de colheita
- [x] Padronizar telas de resumo
