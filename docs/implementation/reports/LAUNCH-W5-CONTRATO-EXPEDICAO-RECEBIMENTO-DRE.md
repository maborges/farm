# LAUNCH-W5 - Contrato, Expedição, Recebimento e DRE

## Auditoria realizada

Base da auditoria:

- `services/api/financeiro/comercializacao/models.py`
- `services/api/financeiro/comercializacao/service.py`
- `services/api/financeiro/comercializacao/router.py`
- `services/api/financeiro/services/receita_service.py`
- `services/api/financeiro/services/dashboard_service.py`
- `services/api/agricola/dre/service.py`
- `services/api/agricola/rastreabilidade/service.py`
- `services/api/agricola/romaneios/service.py`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/comercializacoes/page.tsx`
- `services/api/tests/unit/financeiro/test_comercializacao.py`

## Conclusão da auditoria

O fluxo comercial já existia em backend e frontend:

- contrato/comercialização com status `RASCUNHO -> CONFIRMADO -> EM_TRANSITO -> ENTREGUE -> FINALIZADO`
- reserva de `ProdutoColhido` no `CONFIRMADO`
- geração de `Receita` vinculada à comercialização
- rastreabilidade por `produto_colhido_id`, `origem_id` e `origem_tipo`
- consumo da comercialização pela DRE agrícola v1
- frontend operacional em `apps/web` para criar e avançar status

O gap comprovado era o fechamento automático do recebimento financeiro. A comercialização criava a receita, mas não baixava a receita de forma nativa ao concluir a jornada operacional.

## Integrações reutilizadas

- `ComercializacaoCommodity` como entidade oficial de contrato/venda
- `Receita` como contas a receber
- `ProdutoColhido` como lote físico rastreável
- `DREAgricolaV1Service` / DRE agrícola v1 como consumidor econômico oficial
- `DashboardService` financeiro para leitura de `RECEBIDO` e fluxo de caixa
- `RastreabilidadeService` para cadeia operacional

## Lacuna encontrada

- ausência de baixa automática da `Receita` ao finalizar comercializações com pagamento imediato
- ausência de preenchimento automático de `data_pagamento` em `ComercializacaoCommodity`

## Implementação realizada

- adicionado fechamento automático da receita no `FINALIZADO` para formas imediatas (`A_VISTA`, `PIX`, `TRANSFERENCIA`)
- a baixa automática preenche:
  - `Receita.status = RECEBIDO`
  - `Receita.valor_recebido = valor_total`
  - `Receita.data_recebimento = hoje`
  - `Receita.forma_recebimento`
  - `ComercializacaoCommodity.data_pagamento`
- preservada a idempotência: se a receita já estiver `RECEBIDO`, nada é refeito

## Arquivos alterados

- `services/api/financeiro/comercializacao/service.py`
- `services/api/tests/unit/financeiro/test_comercializacao.py`

## Testes executados

- `services/api/.venv/bin/pytest services/api/tests/unit/financeiro/test_comercializacao.py -q`
- `services/api/.venv/bin/ruff check services/api/financeiro/comercializacao/service.py services/api/tests/unit/financeiro/test_comercializacao.py`
- `git diff --check`

## Validações

- fluxo de comercialização confirmado com reserva de estoque e geração de receita
- baixa automática da receita confirmada no fechamento
- idempotência validada com chamada adicional ao helper de recebimento
- `ruff check` passou no escopo alterado
- `pytest` passou no escopo alterado
- `git diff --check` sem divergências

## Limitações remanescentes

- o fechamento automático foi aplicado apenas para formas de pagamento imediatas
- comercializações em prazo continuam dependentes de baixa financeira posterior, como já era esperado pelo modelo
- não houve alteração de frontend porque a tela operacional já existia e não havia lacuna funcional comprovada de interface
