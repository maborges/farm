# BL-22 — F1_TESOURARIA

**Módulo:** `F1_TESOURARIA`  
**Status atual:** Implementado  
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
- [ ] CRUD de receitas e despesas
- [ ] Parcelamento
- [ ] Rateio por centro de custo

### US-22.2 — Conciliação bancária
**Como** gestor, **quero** conciliar extrato com lançamentos, **para** manter caixa confiável.

**Critérios de aceite:**
- [ ] Importação OFX
- [ ] Sugestões de conciliação
- [ ] Aprovação manual

## Tarefas técnicas

- [ ] Revisar nomes de módulos fiscais correlatos
- [ ] Ampliar cobertura de relatórios
- [ ] Criar testes de integração de conciliação

