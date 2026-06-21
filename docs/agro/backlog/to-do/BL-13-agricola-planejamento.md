# BL-13 — A1_PLANEJAMENTO

**Módulo:** `A1_PLANEJAMENTO`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`

## Contexto

Planejamento de safra, orçamento, fases e base para o ciclo agrícola.

## Gaps observados

- O módulo está funcional, mas depende de refinamento contínuo em orçamento, resumo e automações.
- Integrações com custos e colheita podem ser melhor amarradas.

## User Stories

### US-13.1 — Safra planejada
**Como** gestor, **quero** planejar safras por talhão, **para** organizar o ciclo produtivo.

**Critérios de aceite:**
- [x] Criar e editar safra
- [x] Avançar fase com validação
- [x] Resumo planejado vs realizado

### US-13.2 — Orçamento da safra
**Como** gestor, **quero** associar orçamento à safra, **para** controlar desvio financeiro.

**Critérios de aceite:**
- [x] Orçamento vinculado à safra
- [x] Integração com financeiro
- [x] Relatório de desvio

## Tarefas técnicas

- [x] Adicionar testes de transição de fase
- [x] Melhorar integração com custos e DRE
- [x] Revisar consistência dos templates agrícolas
