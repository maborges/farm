# BL-18 — P1_REBANHO

**Módulo:** `P1_REBANHO`  
**Status atual:** Implementado  
**Prioridade:** Alta  
**Dependências:** `CORE`

## Contexto

Controle de rebanho, lotes, piquetes e eventos.

## Gaps observados

- O fluxo essencial funciona, mas precisa de evolução em diagnóstico e produtividade.
- É a base para genética, confinamento e leite.

## User Stories

### US-18.1 — Lote de animais
**Como** gestor, **quero** criar lotes e movimentações, **para** controlar o rebanho.

**Critérios de aceite:**
- [ ] CRUD de lotes
- [ ] Eventos append-only
- [ ] Piquetes vinculados

### US-18.2 — Histórico zootécnico
**Como** gestor, **quero** consultar eventos do lote, **para** auditoria e manejo.

**Critérios de aceite:**
- [ ] Lista de manejos
- [ ] Histórico por lote
- [ ] Filtros por tipo de evento

## Tarefas técnicas

- [ ] Reforçar testes de evento append-only
- [ ] Melhorar dashboard de indicadores
- [ ] Cobrir integração com financeiro

