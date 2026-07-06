# ECONOMIC-GOV-01 — Guardrails do Domínio Econômico

## Resumo

Esta execução adiciona proteção mínima de governança sobre a arquitetura oficial definida em `ECONOMIC-ARCH-01`, sem alterar cálculo, contrato público, dado operacional ou legado ativo.

## Guardrails criados

- Comentários inline em pontos legados que ainda podem ser confundidos com fonte oficial:
  - `services/api/financeiro/services/lancamento_service.py`
  - `services/api/agricola/custos/service.py`
  - `services/api/agricola/romaneios/service.py`
  - `services/api/pecuaria/services/manejo_service.py`
  - `services/api/operacional/services/estoque_service.py`
- Teste estático de governança em `services/api/tests/unit/agricola/test_economic_arch_guardrails.py` cobrindo:
  - Regra 1: `OperationalCostAllocationService` continua sendo a porta oficial para custos operacionais e `CostAllocation` segue sendo a persistência oficial.
  - Regra 2: `agricola.dre.v1` continua sendo a DRE operacional oficial.
  - Regra 3: `RentabilidadeAgricolaV1Service` continua derivando da DRE agrícola v1.
  - Regra 4: a DRE legada baseada em `LancamentoFinanceiro` segue explicitamente marcada como compatibilidade.
  - Regra 5: `OperacaoAgricola.custo_total` segue explicitamente marcado como fallback legado.
  - Regra 6: `Despesa` e `CostAllocation` continuam preservados como camadas distintas por documentação e por arquitetura já auditada.

## Legado explicitamente preservado

- `LancamentoService.gerar_dre()` continua ativo como DRE legada baseada em `LancamentoFinanceiro`.
- `CustosService.get_resumo_safra()` continua aceitando fallback por `OperacaoAgricola.custo_total`.
- `RomaneioService.criar()` continua podendo gerar `Receita` automática.
- `ManejoLoteService` continua criando `Despesa` e `Receita` diretas em alguns eventos.
- `EstoqueService._criar_lancamento_insumo()` continua registrando `LancamentoFinanceiro` legado para estoque.

## Proibido para novos fluxos

- Criar DRE operacional nova baseada primariamente em `LancamentoFinanceiro`.
- Usar `OperacaoAgricola.custo_total` como fonte primária de custo operacional.
- Tratar romaneio como fonte oficial de receita fora da camada `Receita`.
- Criar custo operacional novo fora de `OperationalCostAllocationService` + `CostAllocation`.
- Misturar `Despesa` e `CostAllocation` como se fossem a mesma camada econômica.

## Observações de auditoria

- O arquivo solicitado em pré-leitura `docs/implementation/reports/ECONOMIC-ARCH-01-DOMINIO-ECONOMICO.md` não existe neste workspace.
- A leitura foi feita com base em:
  - `docs/architecture/ECONOMIC-ARCH-01-DOMINIO-ECONOMICO.md`
  - `docs/implementation/reports/ECONOMIC-ARCH-01-DOMINIO-ECONOMICO1.md`

## Validações executadas

- `services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_economic_arch_guardrails.py -q`
  - Resultado: `4 passed`
- `services/api/.venv/bin/pytest services/api/tests/test_legacy_dre_conceptual_step214.py -q`
  - Resultado: `2 passed`
- `services/api/.venv/bin/pytest services/api/tests/test_launch_core01_operational_cost_engine.py -q`
  - Resultado: falhou no ambiente por `asyncpg.exceptions.InvalidColumnReferenceError` ao inserir em `production_units`, antes de qualquer asserção dos guardrails desta execução.
- `services/api/.venv/bin/pytest services/api/tests/test_rentabilidade_agricola_v1.py -q`
  - Resultado: falhou no ambiente pelo mesmo problema estrutural em `production_units`, antes de qualquer asserção relacionada às alterações desta execução.
- `services/api/.venv/bin/ruff check services/api/tests/unit/agricola/test_economic_arch_guardrails.py`
  - Resultado: `All checks passed!`
- `services/api/.venv/bin/ruff check services/api/financeiro/services/lancamento_service.py services/api/agricola/custos/service.py services/api/agricola/romaneios/service.py services/api/pecuaria/services/manejo_service.py services/api/operacional/services/estoque_service.py`
  - Resultado: escopo não está limpo no repositório atual por dívida histórica pré-existente de lint nos próprios arquivos auditados; os comentários desta execução não alteram comportamento nem introduzem nova lógica.
- `git diff --check`
  - Resultado: sem erros

## Resultado esperado desta execução

- Nenhum legado removido.
- Nenhuma migration criada.
- Nenhum endpoint criado.
- Nenhum cálculo econômico alterado.
- Nenhum contrato público alterado.
- Guardrails mínimos adicionados para evitar regressão arquitetural.
