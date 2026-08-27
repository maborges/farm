# 05 — Integrações e Fluxos

## Entrada agrícola

```text
Safra/Cultivo/Talhão
  → RomaneioColheita
  → ProdutoColhido
  → QualitySample
  → QualityReport
  → QualityClassification
```

## Pós-colheita

```text
ProdutoColhido/Romaneio
  → LoteBeneficiamento
  → nova amostra/laudo
  → rendimento, perdas e classificação final
  → LoteEstoque
```

## Comercialização

```text
Classificação aprovada
  → QualityAdjustment
  → valuation do lote
  → contrato/comercialização
  → receita ou pagamento auditável
```

## Regras de integração

- qualidade nunca altera diretamente o ledger físico;
- estoque deve bloquear mistura incompatível ou exigir recálculo;
- comercialização deve consumir uma avaliação aprovada;
- reprovado não pode ser faturado/embarcado quando a política do comprador exigir;
- eventos assíncronos devem ser idempotentes;
- falha de integração não pode apagar o laudo.

## Importação

CSV/XLSX deve exigir mapeamento de colunas, unidade, identificador do lote, data, origem e protocolo. Linhas inválidas ficam em relatório de rejeição; não são descartadas.

## Equipamentos e laboratórios

Integrações devem possuir adapter por fornecedor, idempotency key, timestamp de medição, unidade, método, calibração e evidência original. Credenciais ficam no domínio oficial de Integrações.

## Rastreabilidade

O passaporte pode expor somente dados autorizados: origem, lote, classificação, certificações e evidências públicas. Valores comerciais, operadores e dados sensíveis permanecem privados.
