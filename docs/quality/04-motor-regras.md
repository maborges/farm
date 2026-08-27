# 04 — Motor de Regras e Determinação

## Princípios

1. Resultado sempre reproduzível a partir do protocolo, versão e medições.
2. Nenhum limite deve ficar hardcoded no service.
3. Unidade e conversão são explícitas.
4. Regra mais restritiva vence em conflito.
5. Toda decisão informa motivos e critérios violados.
6. Dados ausentes produzem `PENDENTE`, não aprovação silenciosa.

## Tipos de critério

- `NUMERIC`: umidade, impureza, peso, pH, pontuação;
- `ENUM`: bebida, cor, padrão visual;
- `BOOLEAN`: presença de contaminação, aprovação documental;
- `TEXT`: observação, laudo externo;
- `PERCENTAGE`: defeitos, rendimento e composição.

## Operadores iniciais

`EQ`, `NE`, `LT`, `LTE`, `GT`, `GTE`, `BETWEEN`, `IN`, `REQUIRED`.

## Resultado

O avaliador deve retornar:

- classe de qualidade;
- status;
- critérios avaliados;
- critérios ausentes;
- regras aprovadas e violadas;
- ajustes físicos/comerciais sugeridos;
- protocolo e versão;
- explicação legível;
- versão do motor.

## Ajustes

- `DISCOUNT_WEIGHT`: reduz peso comercial, sem alterar saldo físico;
- `DISCOUNT_FINANCIAL`: deságio;
- `PREMIUM_FINANCIAL`: bonificação;
- `BLOCK_LOT`: impede venda, mistura ou expedição;
- `REPROCESS`: exige secagem, limpeza ou nova análise.

A aplicação financeira deve ser separada da classificação e exigir política ativa, autorização e auditoria.

## Exemplo de protocolo

```text
Soja — padrão interno v1
Umidade: máximo 14%
Impurezas: máximo 1%
Avariados: máximo 8%

Se todos atendidos: TIPO_1 / APROVADO
Se recuperável: PENDENTE_REPROCESSAMENTO
Se limite crítico violado: REPROVADO
```

## IA futura

A IA poderá sugerir classificação, detectar anomalias e interpretar imagens, mas deverá registrar modelo, versão, confiança, entradas e decisão humana. Não poderá publicar resultado aprovado sem política específica e validação técnica.
