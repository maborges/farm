# 10 — Decisões em Aberto

## Produto

- Qual será a primeira commodity: café, soja, milho ou outra?
- O cliente quer qualidade na entrada, na saída do beneficiamento ou nas duas etapas?
- A decisão final é informativa, operacional, comercial ou regulatória?
- O responsável técnico aprova obrigatoriamente todos os lotes?

## Protocolo

- qual norma ou padrão será a fonte oficial?
- quais critérios são obrigatórios?
- limites são fixos, progressivos ou dependem do comprador?
- como tratar amostras compostas e múltiplas medições?
- qual política de arredondamento e conversão?

## Comercial

- desconto será em peso, preço, taxa de serviço ou combinação?
- bonificações podem gerar lançamento financeiro automático?
- quais situações bloqueiam estoque, venda ou embarque?
- o preço por qualidade pertence ao módulo ou à Comercialização?

## Operação

- quais equipamentos serão integrados primeiro?
- haverá coleta offline no MVP?
- quais documentos e fotos podem ser publicados?
- qual prazo de retenção dos laudos?

## Arquitetura

- `operacional_qualidade_*` será evoluído ou substituído por um namespace canônico?
- o módulo precisa de novas entidades ou algumas podem ser extensões de modelos existentes?
- quais rotas atuais de qualidade serão mantidas por compatibilidade?
- quais eventos já existem e quais precisam de outbox?

## Critério de lançamento

O lançamento só deve ser aprovado quando houver uma commodity, um protocolo, dados reais de teste, responsável técnico definido, matriz de permissões, testes de tenant/RLS e fluxo de reanálise documentado.
