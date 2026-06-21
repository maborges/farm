# BL-27 — O2_ESTOQUE

**Módulo:** `O2_ESTOQUE`  
**Status atual:** Concluído
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
- [x] Entrada/saída/transferência
- [x] Alertas de validade
- [x] Reservas e requisições

### US-27.2 — Saldo e reposição
**Como** gestor, **quero** ver saldo mínimo, **para** decidir compras e reposição.

**Critérios de aceite:**
- [x] Saldos em tempo real
- [x] Alertas de mínimo
- [x] Vínculo com compras

## Tarefas técnicas

- [x] Cobrir cenários de lote e validade
- [x] Revisar performance de saldos
- [x] Padronizar UX de movimentações
