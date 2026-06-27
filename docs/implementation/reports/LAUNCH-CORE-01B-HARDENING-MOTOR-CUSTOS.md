# LAUNCH-CORE-01B — Hardening e Validação Operacional do Motor Canônico de Custos

## Escopo executado

Auditoria e hardening restritos aos módulos:

- `services/api/agricola/custos/`
- `services/api/financeiro/`
- `services/api/operacional/`
- `services/api/rh/`
- `services/api/tests/`

Sem criação de novos módulos, serviços econômicos, endpoints, models ou migrations.

## Resposta curta

Não.

O Motor Canônico de Custos **ainda não pode ser considerado operacionalmente validado para produção** nesta execução, porque a convergência econômica ativa foi confirmada no código, mas a validação operacional completa ficou bloqueada por limitações reais do ambiente de banco e por um bug de hardening encontrado durante os testes.

## Auditoria executada

### Camada econômica ativa

Fluxo ativo auditado:

- `OperationalCostAllocationService`
- `CostAllocation`
- `Despesa`
- `DREAgricolaV1Service`
- `RentabilidadeAgricolaV1Service`

Integrações auditadas:

- `operacional/services/abastecimento_service.py`
- `operacional/services/frota_service.py`
- `operacional/services/frota_apontamento_service.py`
- `rh/service.py`

Conclusão da auditoria:

- Frota e RH convergem para `OperationalCostAllocationService`.
- `DREAgricolaV1Service` consome `CostAllocation` como camada prioritária e exclui `Despesa` quando a origem já está representada por allocation canônica.
- `RentabilidadeAgricolaV1Service` deriva da DRE agrícola v1, preservando a cadeia econômica.
- Não encontrei caminho ativo chamando `LancamentoOperacionalService`.
- Existe um caminho paralelo **órfão** em `services/api/financeiro/services/lancamento_operacional_service.py`, mas sem referências ativas no código auditado.

### Precedência econômica

Confirmado no código:

- `CostAllocation` tem precedência sobre `Despesa` na DRE agrícola v1.
- As origens canônicas auditadas com supressão de dupla contagem são:
  - `ABASTECIMENTO -> FROTA_COMBUSTIVEL`
  - `ORDEM_SERVICO -> FROTA_PECAS | FROTA_MANUTENCAO`
  - `RH_DIARIA -> RH_DIARIA`
  - `RH_EMPREITADA -> RH_EMPREITADA`

## Correções aplicadas

### 1. Quebra de ciclo de importação

Problema encontrado:

- `agricola.alertas.service -> agricola.custos -> operational_cost_service -> allocation_service -> agricola.alertas.service`

Correção:

- `services/api/agricola/custos/__init__.py`
- Troca da importação ansiosa por export lazy via `__getattr__`.

Impacto:

- Remove erro de bootstrap em testes de integração.
- Mantém a API pública do pacote sem carregar `operational_cost_service` durante a inicialização do pacote.

### 2. Normalização da categoria persistida em `cost_allocations`

Problema encontrado:

- O novo motor gravava categorias detalhadas (`COMBUSTIVEL`, `PECAS`, `MANUTENCAO`, `DIARIA`, `EMPREITADA`, `MAQUINA`) em `CostAllocation`.
- O banco real aceita apenas:
  - `INSUMO`
  - `MAO_OBRA`
  - `MAQUINARIO`
  - `SERVICO`
  - `DESPESA_FINANCEIRA`
  - `OUTROS`
  - `SANITARIO`

Evidência:

- Falha real no teste `test_apontamento_valido_cria_allocacao_e_rastreabilidade`
- Erro: violação de `ck_cost_allocations_category`

Correção:

- `services/api/agricola/custos/operational_cost_service.py`
- Inclusão de mapeamento persistido:
  - `COMBUSTIVEL -> INSUMO`
  - `PECAS -> INSUMO`
  - `MANUTENCAO -> SERVICO`
  - `DIARIA -> MAO_OBRA`
  - `EMPREITADA -> MAO_OBRA`
  - `MAQUINA -> MAQUINARIO`

Impacto:

- Compatibiliza o motor novo com o schema real sem alterar migrations.
- Preserva a categoria detalhada do fluxo no nível funcional (`source`, descrição, origem), enquanto grava apenas buckets válidos no `CostAllocation`.

### 3. Ajuste do teste do motor

Arquivo:

- `services/api/tests/test_launch_core01_operational_cost_engine.py`

Correção:

- Assert de `allocation.cost_category` atualizado para refletir a taxonomia persistida real do banco.

## Testes executados

### Executados com sucesso

- `services/api/.venv/bin/pytest services/api/tests/test_dre_operacional_step183.py -q`
  - Resultado: `3 passed`

- `python -m py_compile`
  - Arquivos validados:
    - `services/api/agricola/custos/operational_cost_service.py`
    - `services/api/agricola/custos/__init__.py`
    - `services/api/tests/test_launch_core01_operational_cost_engine.py`
  - Resultado: sucesso

- `git diff --check`
  - Resultado: sem erros de whitespace/patch format

### Executados com falha útil

- `services/api/.venv/bin/pytest services/api/tests/test_frota_apontamentos_step08.py::test_apontamento_valido_cria_allocacao_e_rastreabilidade -vv -s`
  - Evidência coletada:
    - falha real por `ck_cost_allocations_category`
  - Status:
    - corrigido no código nesta execução

- `services/api/.venv/bin/pytest services/api/tests/integration/test_rh.py -q -x`
  - Evidência coletada:
    - `503 Banco de dados indisponível ou pool de conexões esgotado`
    - `TimeoutError` ao adquirir sessão
  - Interpretação:
    - bloqueio de ambiente/pool, não evidência de regressão econômica direta

- `services/api/.venv/bin/pytest services/api/tests/test_launch_core01_operational_cost_engine.py::test_operational_cost_service_reprocessa_sem_duplicar -vv -s`
  - Evidência coletada:
    - `asyncpg.exceptions.TooManyConnectionsError`
    - `remaining connection slots are reserved for roles with the SUPERUSER attribute`
  - Interpretação:
    - bloqueio de ambiente compartilhado, impedindo validação final de idempotência em banco real

### Não executados ou indisponíveis

- `ruff check`
  - Motivo:
    - `ruff: command not found`
  - Impacto:
    - linting estático não validado neste ambiente
  - Reprodução:
    - instalar `ruff` no ambiente e executar:
    - `ruff check services/api/agricola/custos services/api/financeiro services/api/operacional services/api/rh services/api/tests`

## Evidências de validação

### Confirmado

- A convergência econômica ativa usa `OperationalCostAllocationService`.
- A DRE agrícola v1 aplica precedência de `CostAllocation` sobre `Despesa`.
- `Rentabilidade` continua derivada da DRE agrícola v1.
- RH e Frota convergem para a mesma camada econômica no código auditado.
- A arquitetura orientada a eventos não foi alterada nesta execução.
- O hardening revelou e corrigiu incompatibilidade real entre código e schema (`cost_category`).

### Não confirmado operacionalmente nesta execução

- Reprocessamento completo em banco real para:
  - abastecimento
  - diária
  - empreitada
  - fechamento de OS
- Validação ponta a ponta de multi-tenant sob carga de pool compartilhado.
- Validação final da trilha RH via API com banco estável.

## Limitações remanescentes

### 1. Banco compartilhado sem capacidade estável para a suíte

Evidências:

- `TooManyConnectionsError`
- `TimeoutError` ao adquirir sessão
- `503` em teste de integração RH

Impacto:

- A validação operacional completa do motor novo ficou inconclusiva.

### 2. `ruff` indisponível

Impacto:

- Hardening sem verificação estática completa de estilo/qualidade.

### 3. Helper paralelo órfão ainda existe

Arquivo:

- `services/api/financeiro/services/lancamento_operacional_service.py`

Estado:

- Não encontrei uso ativo.
- Não foi removido por estar fora do escopo permitido e por não haver evidência de execução no fluxo atual.

Impacto:

- Não representa caminho paralelo ativo confirmado, mas permanece como dívida de clareza arquitetural.

## Arquivos alterados nesta execução

- `services/api/agricola/custos/__init__.py`
- `services/api/agricola/custos/operational_cost_service.py`
- `services/api/tests/test_launch_core01_operational_cost_engine.py`

## Arquivos criados nesta execução

- `docs/implementation/reports/LAUNCH-CORE-01B-HARDENING-MOTOR-CUSTOS.md`

## Critérios de aceite: status

- O Motor Canônico de Custos está operacionalmente validado.
  - Não confirmado

- CostAllocation permanece como camada econômica única.
  - Parcialmente confirmado: única camada econômica ativa para Frota/RH auditados

- Não há dupla apropriação entre CostAllocation e Despesa.
  - Confirmado no desenho da DRE v1
  - Não homologado ponta a ponta em banco real para todos os cenários

- RH e Frota convergem corretamente para a mesma camada econômica.
  - Confirmado no código
  - Não homologado integralmente em ambiente real

- DRE consome corretamente as apropriações econômicas.
  - Confirmado por auditoria e teste `test_dre_operacional_step183.py`

- Rentabilidade reflete automaticamente os custos convergidos.
  - Confirmado por auditoria do serviço
  - Não revalidado ponta a ponta com banco estável nesta execução

- Multi-tenant permanece íntegro.
  - Sem evidência de quebra no código auditado
  - Não validado integralmente nesta execução

- Idempotência foi validada.
  - Não, por bloqueio do banco

- A arquitetura orientada a eventos permaneceu intacta.
  - Confirmado

## Recomendação final

Não liberar como “validado para produção” com base apenas nesta execução.

Antes da liberação, repetir em ambiente completo e estável:

- `services/api/tests/test_launch_core01_operational_cost_engine.py`
- `services/api/tests/test_frota_apontamentos_step08.py`
- `services/api/tests/integration/test_rh.py`
- suíte focada de frota/abastecimento/OS
- `ruff check`

Condição mínima para validação final:

- banco sem exaustão de conexões
- rerun da suíte crítica do motor
- confirmação explícita da idempotência em reprocessamento real

