# BL-10 — IMOVEIS_CADASTRO

**Módulo:** `IMOVEIS_CADASTRO`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`

## Escopo concluído

- Cadastro de imóveis rurais
- Documentos legais
- Cartórios
- Benfeitorias
- Listagem geral por tenant
- Atualização com validação de NIRF e área

## Fechamento da rodada

O módulo já possuía a base funcional. Nesta rodada foram fechados os pontos de estabilização:
- listagem geral sem `unidade_produtiva_id`
- teste de listagem geral do service
- teste de atualização de imóvel com NIRF e área

## Critérios de aceite

- [x] CRUD completo com validação de NIRF/CAR/CCIR
- [x] Situação cadastral recalculada automaticamente
- [x] Exclusão lógica preservando histórico
- [x] CRUD de cartórios
- [x] CRUD de benfeitorias
- [x] Associação correta ao imóvel
- [x] Listagem geral por tenant quando não há filtro de fazenda
- [x] Teste de atualização de área e NIRF

## Evidências técnicas

- [x] `services/api/imoveis/services/imovel_service.py`
- [x] `services/api/tests/unit/imoveis/test_imovel_service.py`
- [x] `services/api/tests/test_imoveis_integration.py` cobre NIRF/CAR/listagem por fazenda/situação

## Observação

Validações mais profundas de documentos podem continuar evoluindo em backlog futuro, mas o comportamento base do módulo está fechado para esta entrega.
