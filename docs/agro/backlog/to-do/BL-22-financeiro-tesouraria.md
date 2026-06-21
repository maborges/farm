# BL-22 — F1_TESOURARIA

**Módulo:** `F1_TESOURARIA`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`

## Contexto

Contas a pagar e receber, plano de contas, conciliação e integrações financeiras.

## Gaps observados

- Base funcional existe, mas há divergências pontuais entre módulos e nomenclaturas.
- Integrações e relatórios seguem em evolução.

## User Stories

### US-22.1 — Lançamentos financeiros
**Como** gestor, **quero** registrar receitas e despesas, **para** controlar o caixa.

**Critérios de aceite:**
- [x] CRUD de receitas e despesas
- [x] Parcelamento
- [x] Rateio por centro de custo

### US-22.2 — Conciliação bancária
**Como** gestor, **quero** conciliar extrato com lançamentos, **para** manter caixa confiável.

**Critérios de aceite:**
- [x] Importação OFX
- [x] Sugestões de conciliação
- [x] Aprovação manual

## Tarefas técnicas

- [x] Revisar nomes de módulos fiscais correlatos
- [x] Ampliar cobertura de relatórios
- [x] Criar testes de integração de conciliação
