# BL-24 — F3_FISCAL

**Módulo:** `F3_FISCAL`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `F1_TESOURARIA`

## Contexto

NF-e, NFP-e, compliance fiscal e obrigações relacionadas.

## Gaps observados

- O router de notas fiscais está enquadrado em `F3_FISCAL`.
- O endpoint principal possui cobertura de regressão para o gate do módulo.

## User Stories

### US-24.1 — Emissão fiscal
**Como** gestor, **quero** emitir notas fiscais, **para** atender as obrigações legais.

**Critérios de aceite:**
- [x] CRUD de notas fiscais
- [x] Status SEFAZ
- [x] Cancelamento e autorização

### US-24.2 — Conformidade
**Como** gestor, **quero** acompanhar compliance fiscal, **para** reduzir risco tributário.

**Critérios de aceite:**
- [x] Rotas protegidas com o módulo correto
- [x] Integração com livros e relatórios
- [x] Testes de regressão

## Tarefas técnicas

- [x] Corrigir `MODULE` para `F3_FISCAL`
- [x] Amarrar emissão a fluxo de negócio real
- [x] Adicionar testes end-to-end

## Evidências

- `services/api/financeiro/routers/notas_fiscais.py`
- `services/api/tests/integration/core/test_feature_gates.py`
