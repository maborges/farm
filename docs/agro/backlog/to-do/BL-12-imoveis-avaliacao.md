# BL-12 — IMOVEIS_AVALIACAO

**Módulo:** `IMOVEIS_AVALIACAO`  
**Status atual:** Implementado  
**Prioridade:** Média  
**Dependências:** `CORE`, `IMOVEIS_CADASTRO`

## Contexto

Avaliação patrimonial de imóveis rurais para suporte a crédito, sucessão e gestão de ativos.

## Gaps observados

- Não há fluxo operacional completo no backend.
- Não há telas de avaliação no frontend.

## User Stories

### US-12.1 — Laudo de avaliação
**Como** gestor, **quero** gerar laudo de avaliação, **para** conhecer o valor patrimonial do imóvel.

**Critérios de aceite:**
- [x] Cadastro de laudo com data, método e valor
- [x] Histórico de avaliações por imóvel
- [x] Anexos e observações

### US-12.2 — Comparativo patrimonial
**Como** gestor, **quero** comparar avaliações ao longo do tempo, **para** acompanhar valorização.

**Critérios de aceite:**
- [x] Série histórica
- [x] Indicadores por hectare
- [x] Exportação PDF

## Tarefas técnicas

- [x] Criar models e router do módulo
- [x] Definir schema de laudo
- [x] Incluir menu e página de avaliação
