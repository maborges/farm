# BL-27 — O2_ESTOQUE

**Módulo:** `O2_ESTOQUE`  
**Status atual:** Implementado  
**Prioridade:** Alta  
**Dependências:** `CORE`

## Contexto

Estoque multi-armazéns, lotes, reservas e movimentações.

## Gaps observados

- O domínio está amplo, mas precisa continuar alinhado com colheita, campo e pecuária.

## User Stories

### US-27.1 — Lote de estoque
**Como** operador, **quero** cadastrar lotes com validade, **para** manter rastreabilidade.

**Critérios de aceite:**
- [ ] Entrada/saída/transferência
- [ ] Alertas de validade
- [ ] Reservas e requisições

### US-27.2 — Saldo e reposição
**Como** gestor, **quero** ver saldo mínimo, **para** decidir compras e reposição.

**Critérios de aceite:**
- [ ] Saldos em tempo real
- [ ] Alertas de mínimo
- [ ] Vínculo com compras

## Tarefas técnicas

- [ ] Cobrir cenários de lote e validade
- [ ] Revisar performance de saldos
- [ ] Padronizar UX de movimentações

