# BL-21 — P4_LEITE

**Módulo:** `P4_LEITE`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`, `P1_REBANHO`

## Contexto

Produção leiteira, qualidade e destino da produção.

## Gaps observados

- Existe modelo de produção leiteira, mas falta o pacote operacional completo.
- Não encontrei router dedicado exposto para o fluxo principal.

## User Stories

### US-21.1 — Registro de produção
**Como** gestor, **quero** registrar produção diária, **para** controlar volume e qualidade.

**Critérios de aceite:**
- [x] Produção por vaca ou lote
- [x] Turnos de ordenha
- [x] Qualidade do leite

### US-21.2 — Comercialização do leite
**Como** gestor, **quero** acompanhar o destino do leite, **para** fechar receita e rastreabilidade.

**Critérios de aceite:**
- [x] Destino comercial
- [x] Preço por litro
- [x] Integração com financeiro

## Tarefas técnicas

- [x] Expor router do módulo
- [x] Cobrir qualidade e destino
- [x] Criar telas de dashboard
