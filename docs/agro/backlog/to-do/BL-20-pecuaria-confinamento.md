# BL-20 — P3_CONFINAMENTO

**Módulo:** `P3_CONFINAMENTO`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`, `P1_REBANHO`, `O2_ESTOQUE`

## Contexto

Confinamento, nutrição, TMR, cochos e ganho de peso.

## Gaps observados

- Módulo ainda está no plano.
- Não há interface operacional nem regras de lote específicas.

## User Stories

### US-20.1 — Gestão de dieta
**Como** gestor, **quero** definir dietas e TMR, **para** controlar performance do confinamento.

**Critérios de aceite:**
- [x] Cadastro de dietas
- [x] Consumo diário
- [x] Custo por arroba

### US-20.2 — Indicadores de confinamento
**Como** gestor, **quero** ver ganho de peso e conversão, **para** decidir manejo.

**Critérios de aceite:**
- [x] GMD
- [x] Conversão alimentar
- [x] Mortalidade e lotação

## Tarefas técnicas

- [x] Criar domínio, service e router
- [x] Integrar com estoque e financeiro
- [x] Criar dashboard específico
