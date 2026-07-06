# LAUNCH-W1 — Compra -> Estoque -> Financeiro

## Auditoria realizada

- Fluxo de compras materializa recebimento, lote, movimento e saldo em [services/api/operacional/services/compras_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/compras_service.py).
- Contas a pagar já existiam de forma oficial em [services/api/financeiro/models/despesa.py](/opt/lampp/htdocs/farm/services/api/financeiro/models/despesa.py) e [services/api/financeiro/services/despesa_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/despesa_service.py).
- Fluxo de caixa e indicadores financeiros já consumiam `fin_despesas` em [services/api/financeiro/services/relatorio_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/relatorio_service.py) e [services/api/financeiro/services/dashboard_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/dashboard_service.py).
- O gap real era a ausência de geração automática da `Despesa` no recebimento da compra.

## Lacunas encontradas

- `ComprasService.receber_pedido(...)` concluía estoque, mas não criava `Despesa`.
- `DespesaCreate` não expunha `origem_id` e `origem_tipo`, apesar do model persistir esses campos.
- O detalhamento de centro de custos por `Rateio` não podia ser inferido do fluxo atual de compras, porque `SolicitacaoCompra` só comprova `origem/origem_id` genéricos e não carrega contexto oficial de `safra/talhão`.

## Integrações reutilizadas

- `DespesaService.create_with_rateio(...)` para criação oficial de contas a pagar.
- `Fornecedor` legado + vínculo com `Pessoa` via [services/api/operacional/services/fornecedores_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/fornecedores_service.py).
- `PlanoConta` existente para classificar a despesa por tipo de produto com fallback para `CUSTEIO`.
- `RelatorioService.fluxo_caixa(...)` e `DashboardService` sem duplicação de lógica.

## Integrações implementadas

- Geração automática de `Despesa` com `origem_tipo="COMPRA"` e `origem_id=pedido.id` no recebimento do pedido.
- Idempotência financeira: se a despesa da compra já existe, o fluxo não duplica contas a pagar.
- Vínculo da despesa à `unidade_produtiva` do depósito de destino, preservando o estoque como hub transacional.
- Resolução do fornecedor oficial quando houver cadastro legado correspondente.
- Derivação de plano de contas por tipo do produto com fallback controlado.
- Reaproveitamento automático do fluxo de caixa e dos indicadores já existentes, porque ambos leem `fin_despesas`.

## Arquivos alterados

- [services/api/operacional/services/compras_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/compras_service.py)
- [services/api/financeiro/schemas/despesa_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/despesa_schema.py)
- [services/api/tests/test_operational_workflow_governance_step05.py](/opt/lampp/htdocs/farm/services/api/tests/test_operational_workflow_governance_step05.py)
- [services/api/tests/unit/operacional/test_compras_financeiro_integration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/operacional/test_compras_financeiro_integration.py)

## Testes e validações

- `services/api/.venv/bin/python -m compileall ...`:
  - ok
- `services/api/.venv/bin/pytest services/api/tests/unit/operacional/test_compras_financeiro_integration.py -q`:
  - `3 passed`
- `services/api/.venv/bin/ruff check ...`:
  - o arquivo novo de teste unitário passou;
  - os arquivos legados alterados já possuem dívida de lint pré-existente e o `ruff` do escopo amplo continua falhando por problemas anteriores ao patch.
- `git diff --check`:
  - executado ao final da implementação

## Validações funcionais

- Não houve duplicação de módulo financeiro, compras, estoque, models, routers ou endpoints.
- O estoque permaneceu como ponto oficial da materialização transacional.
- O financeiro foi integrado usando `Despesa`, `PlanoConta`, `DespesaService`, `DashboardService` e `RelatorioService` já existentes.
- A rastreabilidade foi preservada com `origem_tipo/origem_id` na despesa automática.
- A arquitetura orientada a eventos não foi removida nem substituída por acoplamento paralelo.

## Limitações remanescentes

- O rateio detalhado para centro de custos agrícola (`safra/talhão`) continua dependente de contexto de origem que o fluxo atual de compras não persiste de forma oficial.
- O teste de integração pesado em [services/api/tests/test_operational_workflow_governance_step05.py](/opt/lampp/htdocs/farm/services/api/tests/test_operational_workflow_governance_step05.py) iniciou execução, mas ficou preso no ambiente externo compartilhado; por isso a validação automatizada conclusiva deste ciclo ficou ancorada no teste unitário novo e na checagem de sintaxe.
