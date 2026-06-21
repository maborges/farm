# BL-14 — A2_CAMPO

**Módulo:** `A2_CAMPO`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `A1_PLANEJAMENTO`, `O2_ESTOQUE`

## Contexto

Caderno de campo, operações agrícolas, apontamentos e baixa de insumos.

## Gaps observados

- Fluxo principal existe, mas precisa de endurecimento de UX e testes de integração.
- Exportação e reconciliação operacional podem ser aprofundadas.

## User Stories

### US-14.1 — Registrar operação
**Como** operador, **quero** registrar operações de campo, **para** manter o histórico agronômico.

**Critérios de aceite:**
- [x] CRUD de operações
- [x] Baixa automática de estoque
- [x] Registro de custos

### US-14.2 — Caderno de campo
**Como** gestor, **quero** exportar o caderno de campo, **para** auditoria e controle.

**Critérios de aceite:**
- [x] Exportação em PDF
- [x] Filtros por safra/fase
- [x] Histórico consultável

## Tarefas técnicas

- [x] Cobrir cenários de baixa de estoque em testes
- [x] Revisar performance de listagens grandes
- [x] Padronizar mensagens de validação
