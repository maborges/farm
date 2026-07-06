# PRODUCT-GOV-01 — Guardrails de Produtos, Culturas e Commodities

## Resumo

Esta execução adiciona guardrails mínimos de governança para proteger a arquitetura oficial definida em `PRODUCT-ARCH-01`, sem remover legado, sem migrar dados e sem alterar contratos públicos ou regras de negócio.

## Guardrails criados

- Teste estático `services/api/tests/unit/test_product_governance_guardrails.py` cobrindo:
  - `Produto` como catálogo mestre operacional.
  - `ProdutoAgricola`, `ProdutoEstoque` e `ProdutoEPI` como extensões de `Produto`.
  - `ProdutoCultura` como cultura oficial.
  - `Commodity` como camada oficial de mercado para comercialização e hedge.
  - `ProdutoColhido` como lote físico colhido distinto de `Produto`.
  - compras, estoque e pecuária sanitária/nutricional usando `Produto`.
  - aliases e campos textuais preservados apenas como compatibilidade.
- Comentários inline de compatibilidade em:
  - `services/api/core/cadastros/models.py`
  - `services/api/agricola/cadastros/models.py`
  - `services/api/agricola/safras/models.py`
  - `services/api/agricola/cultivos/models.py`
  - `services/api/financeiro/hedge/models.py`
  - `services/api/agricola/colheita/models.py`

## Arquivos tocados

- `services/api/core/cadastros/models.py`
- `services/api/agricola/cadastros/models.py`
- `services/api/agricola/safras/models.py`
- `services/api/agricola/cultivos/models.py`
- `services/api/financeiro/hedge/models.py`
- `services/api/agricola/colheita/models.py`
- `services/api/tests/unit/test_product_governance_guardrails.py`
- `docs/implementation/reports/PRODUCT-GOV-01-GUARDRAILS-PRODUTOS-CULTURAS-COMMODITIES.md`

## Legado explicitamente preservado

- `agricola.cadastros.Cultura` permanece como compatibilidade histórica.
- `Safra.cultura` permanece como campo textual legado.
- `Cultivo.cultura` permanece como campo textual legado.
- `ContratoFuturo.commodity` textual permanece preservado.
- `ProdutoCatalogo` permanece como alias histórico de `Produto`.

## Proibido para novos fluxos

- Criar cadastro paralelo para item comprado/estocado/consumido fora de `Produto`.
- Criar cultura agronômica oficial fora de `ProdutoCultura`.
- Criar cadastro paralelo de commodity para comercialização, cotação ou hedge.
- Usar `Produto` como substituto de `ProdutoColhido` em fluxos de produção colhida.
- Tratar `Produto`, `ProdutoCultura`, `Commodity` e `ProdutoColhido` como a mesma camada semântica.

## Validações executadas

- `pytest services/api/tests/unit/test_product_governance_guardrails.py -q`
- `ruff check services/api/tests/unit/test_product_governance_guardrails.py services/api/core/cadastros/models.py services/api/agricola/cadastros/models.py services/api/agricola/safras/models.py services/api/agricola/cultivos/models.py services/api/financeiro/hedge/models.py services/api/agricola/colheita/models.py` foi tentado, mas o binário `ruff` não está disponível neste ambiente.
- `git diff --check`

## Limitações

- Os guardrails são mínimos e majoritariamente estáticos; eles reduzem regressões estruturais, mas não substituem revisão arquitetural de fluxos maiores.
- As compatibilidades documentadas continuam ativas e ainda exigem disciplina para não serem ampliadas.
