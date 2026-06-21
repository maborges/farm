# BL-29 — RH1_REMUNERACAO

**Módulo:** `RH1_REMUNERACAO`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`

## Contexto

Colaboradores, diárias, empreitadas e pagamento por produção.

## Gaps observados

- O módulo funciona, mas precisa de harmonização com a visão de pessoas e fluxo financeiro.

## User Stories

### US-29.1 — Cadastro de colaborador
**Como** gestor, **quero** cadastrar colaboradores, **para** registrar vínculos de trabalho.

**Critérios de aceite:**
- [x] CRUD de colaboradores
- [x] Departamentos
- [x] Status ativo/inativo

### US-29.2 — Pagamento de diárias
**Como** gestor, **quero** pagar diárias em lote, **para** agilizar fechamento.

**Critérios de aceite:**
- [x] Lançamento de diárias
- [x] Pagamento em lote
- [x] Integração com financeiro

## Tarefas técnicas

- [x] Reforçar testes de lote de pagamento
- [x] Melhorar relatórios de RH
- [x] Consolidar telas de equipe
