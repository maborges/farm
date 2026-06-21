# BL-11 — IMOVEIS_ARRENDAMENTOS

**Módulo:** `IMOVEIS_ARRENDAMENTOS`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `IMOVEIS_CADASTRO`

## Contexto

Gestão de contratos de arrendamento e parceria rural.

## Gaps observados

- Existe service layer, router dedicado e cobertura de regressão do fluxo principal.
- O ciclo contratual agora expõe criação, listagem, resumo, reajuste, rescisão e parcelas vencidas.

## User Stories

### US-11.1 — Contrato de arrendamento
**Como** gestor, **quero** cadastrar contratos de arrendamento, **para** controlar uso de imóveis por terceiros.

**Critérios de aceite:**
- [x] Criar contrato com validações legais
- [x] Gerar parcelas automaticamente
- [x] Bloquear contrato sem documento habilitante

### US-11.2 — Acompanhamento de contratos
**Como** gestor, **quero** acompanhar status e vencimentos, **para** evitar perdas e inadimplência.

**Critérios de aceite:**
- [x] Lista de contratos ativos e encerrados
- [x] Alertas de vencimento
- [x] Histórico de reajustes

## Tarefas técnicas

- [x] Expor router público do módulo
- [x] Criar telas no frontend para contratos
- [x] Adicionar testes de regras de negócio e vencimento

## Evidências

- `services/api/imoveis/routers/arrendamento.py`
- `services/api/imoveis/services/arrendamento_service.py`
- `services/api/tests/unit/imoveis/test_arrendamento_router.py`
