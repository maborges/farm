# BL-25 — F4_HEDGING

**Módulo:** `F4_HEDGING`  
**Status atual:** Implementado  
**Prioridade:** Média  
**Dependências:** `CORE`, `F1_TESOURARIA`

## Contexto

Contratos futuros, proteção de preço, exposição e visão de risco.

## Gaps observados

- O módulo está presente, mas a maturidade depende de dados e cenários reais.
- Os limites financeiros/tiers precisam permanecer coerentes.

## User Stories

### US-25.1 — Contrato futuro
**Como** gestor, **quero** registrar contrato futuro, **para** proteger preço de venda.

**Critérios de aceite:**
- [ ] CRUD de contratos
- [ ] Registro de operações
- [ ] Regras de status

### US-25.2 — Exposição consolidada
**Como** gestor, **quero** ver exposição física e financeira, **para** medir risco.

**Critérios de aceite:**
- [ ] Posição consolidada
- [ ] Exposição por safra/commodity
- [ ] Classificação de risco

## Tarefas técnicas

- [ ] Cobrir cenários de risco com testes
- [ ] Revisar dependência de tiers
- [ ] Melhorar documentação operacional

