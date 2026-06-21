# BL-19 — P2_GENETICA

**Módulo:** `P2_GENETICA`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`, `P1_REBANHO`

## Contexto

Genética reprodutiva, IATF, genealogia e diagnóstico de prenhez.

## Gaps observados

- Não há fluxo operacional completo.
- Não há exposição consistente no backend nem no frontend.

## User Stories

### US-19.1 — Ciclo reprodutivo
**Como** gestor, **quero** registrar eventos reprodutivos, **para** acompanhar taxa de prenhez e partos.

**Critérios de aceite:**
- [x] IATF e monta natural
- [x] Diagnóstico de prenhez
- [x] Linha do tempo reprodutiva

### US-19.2 — Seleção genética
**Como** gestor, **quero** consultar genealogia e índices, **para** melhorar o plantel.

**Critérios de aceite:**
- [x] Pedigree
- [x] DEPs / índices
- [x] Planejamento de acasalamento

## Tarefas técnicas

- [x] Criar models, schemas e router
- [x] Criar telas de manejo reprodutivo
- [x] Definir integrações com rebanho
