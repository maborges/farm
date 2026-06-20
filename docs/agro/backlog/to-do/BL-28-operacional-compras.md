# BL-28 — O3_COMPRAS

**Módulo:** `O3_COMPRAS`  
**Status atual:** Implementado  
**Prioridade:** Média  
**Dependências:** `CORE`, `O2_ESTOQUE`

## Contexto

Compras, cotações, aprovação e recebimento.

## Gaps observados

- O núcleo existe, mas há espaço para automatizar melhor aprovação e integração financeira.

## User Stories

### US-28.1 — Pedido de compra
**Como** gestor, **quero** criar pedido e cotação, **para** adquirir insumos com controle.

**Critérios de aceite:**
- [ ] Pedido com itens
- [ ] Cotações por fornecedor
- [ ] Aprovação do pedido

### US-28.2 — Recebimento
**Como** operador, **quero** registrar o recebimento, **para** dar entrada no estoque.

**Critérios de aceite:**
- [ ] Entrada no estoque
- [ ] Integração com financeiro
- [ ] Status do pedido

## Tarefas técnicas

- [ ] Melhorar trilha de aprovação
- [ ] Cobrir integração com estoque e despesas
- [ ] Adicionar relatórios de lead time

