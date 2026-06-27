# LAUNCH-CORE-01 — Motor Canônico de Custos Operacionais

## Auditoria realizada

Escopo auditado:

- `services/api/agricola/custos/`
- `services/api/agricola/dre/`
- `services/api/financeiro/services/lancamento_operacional_service.py`
- `services/api/operacional/services/`
- `services/api/rh/`
- `services/api/pecuaria/`
- testes de Frota, RH, DRE e `CostAllocation`

Constatações principais:

- `CostAllocation` já era a camada econômica oficial consumida por `CustosService`, DRE e Rentabilidade.
- Frota já gerava integração financeira parcial (`Despesa`) em abastecimento externo e fechamento de OS.
- Frota apontava custo manual via `registrar_cost_allocation`, mas com `source="MANUAL"` e sem contrato econômico canônico.
- RH criava `Despesa` para diárias/empreitadas, mas sem convergência consistente para `CostAllocation`.
- A DRE já tinha regra de precedência econômica, porém a supressão de `Despesa` não cobria as novas origens canônicas de Frota/RH.

## Decisão arquitetural

Foi criada uma camada interna de convergência em `services/api/agricola/custos/operational_cost_service.py`:

- `OperationalCostInput`
- `OperationalCostResult`
- `OperationalCostAllocationService`

Responsabilidades implementadas:

- receber entradas econômicas operacionais;
- resolver `ProductionUnit` quando houver contexto agrícola suficiente;
- criar ou atualizar `CostAllocation` de forma idempotente;
- criar ou atualizar `Despesa` quando aplicável;
- preservar rastreabilidade por `origem_tipo` e `origem_id`;
- reutilizar DRE e Rentabilidade sem duplicar cálculo.

## Serviços reutilizados

- `registrar_cost_allocation`
- `AlertasAgricolasService`
- `DREAgricolaV1Service`
- `EstoqueService`
- `get_equipamento_unidade_operacional`
- serviços existentes de Frota e RH

## Arquivos criados

- `services/api/agricola/custos/operational_cost_service.py`
- `services/api/tests/test_launch_core01_operational_cost_engine.py`
- `docs/implementation/reports/LAUNCH-CORE-01-MOTOR-CANONICO-CUSTOS-OPERACIONAIS.md`

## Arquivos alterados

- `services/api/agricola/custos/__init__.py`
- `services/api/agricola/alertas/service.py`
- `services/api/agricola/dre/service.py`
- `services/api/operacional/services/abastecimento_service.py`
- `services/api/operacional/services/frota_apontamento_service.py`
- `services/api/operacional/services/frota_service.py`
- `services/api/rh/service.py`
- `services/api/tests/test_frota_apontamentos_step08.py`

## Fluxos integrados

### Frota / Máquinas

- abastecimento interno -> `FROTA_COMBUSTIVEL` + `CostAllocation`
- abastecimento externo -> `FROTA_COMBUSTIVEL` + `CostAllocation` + `Despesa`
- apontamento de frota -> `FROTA_APONTAMENTO` + `CostAllocation`
- fechamento de OS -> `FROTA_PECAS` e `FROTA_MANUTENCAO` + `CostAllocation` + `Despesa`

### RH

- diária paga -> `RH_DIARIA` + `CostAllocation` quando houver contexto agrícola suficiente + `Despesa`
- empreitada paga -> `RH_EMPREITADA` + `CostAllocation` quando houver contexto agrícola suficiente + `Despesa`

### DRE

- mantida a lógica oficial baseada em `CostAllocation` e `Despesa`
- ajustada apenas a precedência para suprimir `Despesa` quando a nova alocação canônica equivalente já existir

## Testes

Adicionados/ajustados cenários para:

- apontamento derivando custo por `custo_por_ha`
- idempotência do serviço canônico
- abastecimento externo refletindo em `CostAllocation` e `Despesa`
- fechamento de OS refletindo peças e manutenção
- RH sem contexto agrícola não forçando rateio inválido
- DRE refletindo custos mecanizados e mão de obra sem dupla contagem

## Validações

Executado com sucesso:

- `python -m py_compile` no escopo alterado
- `git diff --check`

Limitações de validação nesta execução:

- `ruff check` não pôde ser executado porque `ruff` não está instalado no ambiente (`No module named ruff`).
- `pytest` em sandbox falhou ao abrir socket para o banco (`PermissionError: [Errno 1] Operation not permitted`).
- `pytest` fora da sandbox não retornou saída útil dentro do timeout aplicado; a execução precisa ser repetida no ambiente operacional padrão do projeto.

## Limitações remanescentes

- A convergência canônica foi aplicada aos fluxos auditados de Frota e RH.
- Não foi adicionada nova integração pecuária operacional porque, na auditoria deste escopo, não foi identificado fluxo equivalente de máquinas/RH pecuário já pronto para convergir sem ampliar o domínio.
- RH continua sem forçar apropriação quando não há contexto agrícola suficiente; nesse caso fica apenas a `Despesa`, preservando a integridade do rateio.

## Critérios de aceite

- Nenhum módulo duplicado foi criado.
- Nenhum cálculo de DRE foi duplicado.
- Nenhum financeiro paralelo foi criado.
- `CostAllocation` permaneceu como camada econômica canônica.
- `Despesa` continuou sendo reutilizada quando aplicável.
- RH e Máquinas passaram a convergir para a mesma camada econômica.
- A arquitetura orientada a eventos permaneceu intacta.
- Multi-tenant foi preservado por `tenant_id` em todas as consultas e reaproveitamento de RLS.
- Idempotência foi preservada por `source`/`source_id`/`production_unit_id` com atualização segura.

## Resposta objetiva

Após esta execução, os custos operacionais de máquinas, combustível, manutenção, peças, diárias, empreitadas e mão de obra passam a convergir para uma camada econômica canônica reutilizando `CostAllocation` e `Despesa`, sem criar módulos paralelos e sem depender exclusivamente de lançamento manual de `custo_total`.

Pontos ainda dependentes de validação final em ambiente real:

- confirmação por `pytest` completo no banco do projeto;
- confirmação final de eventuais fluxos pecuários operacionais adicionais que não apareceram na auditoria deste escopo.
