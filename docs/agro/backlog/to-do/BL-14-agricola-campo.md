# BL-14 — A2_CAMPO

**Módulo:** `A2_CAMPO`  
**Status atual:** Implementado  
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
- [ ] CRUD de operações
- [ ] Baixa automática de estoque
- [ ] Registro de custos

### US-14.2 — Caderno de campo
**Como** gestor, **quero** exportar o caderno de campo, **para** auditoria e controle.

**Critérios de aceite:**
- [ ] Exportação em PDF
- [ ] Filtros por safra/fase
- [ ] Histórico consultável

## Tarefas técnicas

- [ ] Cobrir cenários de baixa de estoque em testes
- [ ] Revisar performance de listagens grandes
- [ ] Padronizar mensagens de validação

