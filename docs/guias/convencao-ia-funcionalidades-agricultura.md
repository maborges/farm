# Convenção de IA — Funcionalidades do Módulo Agricultura

## Objetivo

Definir um padrão único para exibir, explicar e validar o uso de IA nas funcionalidades do módulo Agricultura.

Este guia existe para evitar três problemas:

- IA invisível, em que o usuário não percebe que recebeu apoio assistido
- IA genérica, em que a recomendação não conversa com os dados da safra
- IA ornamental, em que há texto bonito, mas sem utilidade prática

## Princípio central

No módulo Agricultura, a IA deve ser apresentada como:

- apoio à decisão
- explicação contextual
- priorização prática

Ela não deve ser apresentada como “caixa-preta” nem como substituição do operador, técnico ou gestor.

## Estrutura padrão obrigatória

Toda funcionalidade com IA deve, preferencialmente, exibir estes quatro blocos:

### 1. Selo IA

Objetivo:

- deixar evidente que a funcionalidade está usando IA

Formato esperado:

- selo visual curto e consistente
- exemplos de rótulo:
  - `IA`
  - `Assistido por IA`
  - `Análise com IA`

Regras:

- o selo deve aparecer próximo ao título, insight ou card principal
- o selo não deve competir mais que o conteúdo principal
- o selo não deve existir se a tela não estiver efetivamente usando IA

## 2. Origem da análise

Objetivo:

- explicar de onde a IA tirou a recomendação

Formato esperado:

- texto curto e objetivo
- exemplos:
  - `Baseado nos monitoramentos dos talhões A1 e B1`
  - `Análise gerada a partir do cenário base e dos cenários otimista e pessimista`
  - `Leitura construída com dados de produtividade, custo e preço da safra`

Regras:

- sempre citar a fonte lógica da análise
- sempre preferir linguagem de negócio e operação
- nunca usar explicação vaga como `baseado em dados históricos` sem qualificar melhor

## 3. Por que estou vendo isso?

Objetivo:

- explicar o motivo do alerta, insight ou recomendação

Formato esperado:

- 1 a 3 frases
- linguagem clara, causal e específica

Exemplos:

- `Você está vendo este alerta porque a ferrugem registrada no talhão A2 atingiu nível acima do limite definido para a cultura.`
- `Este cenário merece atenção porque o custo por hectare subiu enquanto a produtividade projetada caiu.`
- `A recomendação aparece porque o cenário pessimista indica piora relevante da margem líquida.`

Regras:

- o motivo deve ter relação direta com o dado da tela
- o texto deve responder “o que aconteceu” e “por que isso importa”
- não usar resposta vazia, promocional ou abstrata

## 4. Próxima ação sugerida

Objetivo:

- transformar análise em ação

Formato esperado:

- CTA claro
- ação simples e verificável

Exemplos:

- `Revisar monitoramento do A2`
- `Abrir cenários`
- `Registrar nova pulverização`
- `Comparar custo por unidade produtiva`
- `Revisar lote beneficiado`

Regras:

- a ação precisa ser executável no próprio produto ou em fluxo muito próximo
- evitar CTA genérico como `Saiba mais`
- o texto deve ajudar o usuário a sair da análise para a decisão

## Blocos opcionais recomendados

### Nível de confiança

Usar quando a análise depender de qualidade ou quantidade mínima de dados.

Exemplos:

- `Confiança: alta`
- `Confiança: média`

Quando usar:

- cenários com poucas unidades
- monitoramentos com baixa amostragem
- análises que dependam de histórico incompleto

### Dados considerados

Usar quando a recomendação puder gerar dúvida.

Exemplos:

- `Dados considerados: 3 monitoramentos, 2 romaneios e cenário base recalculado`
- `Dados considerados: produtividade, preço, custo por hectare e IR`

## Padrão de texto

O texto de IA deve seguir estas regras:

- ser específico
- ser curto
- ser acionável
- usar o vocabulário do módulo agrícola
- refletir os dados reais da funcionalidade

Evitar:

- frases vagas
- jargão excessivo de IA
- marketing disfarçado de insight
- recomendação sem explicação

## Exemplos por funcionalidade

## 1. Monitoramento fitossanitário

### Estrutura recomendada

- `Selo IA: Assistido por IA`
- `Origem da análise: Baseado no monitoramento do talhão A2 em 05/11/2025`
- `Por que estou vendo isso?: A broca do café foi registrada acima do nível de dano da cultura.`
- `Próxima ação sugerida: Registrar controle fitossanitário`

### Valor para o usuário

- prioriza risco agronômico
- reduz dúvida sobre urgência
- ajuda a transformar observação em manejo

## 2. Cenário econômico

### Estrutura recomendada

- `Selo IA: Análise com IA`
- `Origem da análise: Baseado no cenário base e nas production units da safra`
- `Por que estou vendo isso?: O custo por hectare subiu mais rápido que a receita projetada.`
- `Próxima ação sugerida: Revisar custos por unidade produtiva`

### Valor para o usuário

- resume leitura econômica
- mostra o principal fator de pressão no resultado
- reduz tempo de interpretação da tela

## 3. Comparativo de cenários

### Estrutura recomendada

- `Selo IA: Assistido por IA`
- `Origem da análise: Comparação entre Base, Otimista e Pessimista`
- `Por que estou vendo isso?: O cenário pessimista reduz a margem líquida e piora o ponto de equilíbrio.`
- `Próxima ação sugerida: Abrir cenário pessimista`

### Valor para o usuário

- acelera leitura comparativa
- ajuda a identificar melhor equilíbrio entre risco e retorno
- melhora tomada de decisão

## 4. Dashboard executivo da safra

### Estrutura recomendada

- `Selo IA: IA`
- `Origem da análise: Dados da safra, monitoramentos, romaneios e cenário base`
- `Por que estou vendo isso?: A safra apresenta pressão de custo e alerta agronômico relevante no A2.`
- `Próxima ação sugerida: Revisar monitoramento e abrir cenários`

### Valor para o usuário

- organiza prioridades
- conecta operação e financeiro
- evita navegação desnecessária entre múltiplas telas

## Regras de exibição

### Quando mostrar IA

Mostrar IA quando houver:

- interpretação
- classificação
- recomendação
- resumo inteligente
- priorização de risco

### Quando não mostrar IA

Não mostrar IA quando a tela só exibe:

- CRUD puro
- cálculo determinístico simples sem camada interpretativa
- listagem simples
- consulta sem explicação analítica

## Regras de UX

- a IA nunca deve esconder o dado bruto
- a recomendação deve estar perto do dado que a originou
- o usuário precisa conseguir entender o contexto sem abrir modal complexo
- a IA deve complementar o fluxo, não interrompê-lo

## Regras de QA

Uma funcionalidade com IA só deve ser considerada aprovada se:

- o uso de IA estiver claramente identificado
- a origem da análise estiver compreensível
- o motivo do insight estiver claro
- a próxima ação sugerida fizer sentido
- a mensagem estiver aderente aos dados reais da tela
- o texto não parecer genérico, repetitivo ou promocional

## Checklist rápido de validação

- [ ] Há selo ou identificação visível de IA
- [ ] O texto explica de onde veio a análise
- [ ] O usuário entende por que está vendo a recomendação
- [ ] Existe ação sugerida clara
- [ ] A recomendação faz sentido com os dados carregados
- [ ] A IA não substitui nem esconde o dado operacional

## Modelo de referência

Template curto recomendado:

```text
[Selo IA]
Origem da análise: ...
Por que estou vendo isso? ...
Próxima ação sugerida: ...
```

Template expandido recomendado:

```text
[Assistido por IA]
Origem da análise: Baseado em [dados da funcionalidade].
Por que estou vendo isso? [motivo específico e contextual].
Próxima ação sugerida: [ação objetiva].
```

## Relação com os guias do módulo

Este documento complementa:

- [workflow-atricultura.md](/opt/lampp/htdocs/farm/docs/guias/workflow-atricultura.md)
- [checklist-qa-agricultura.md](/opt/lampp/htdocs/farm/docs/guias/checklist-qa-agricultura.md)
- [workflow-agricultura-cafe.md](/opt/lampp/htdocs/farm/docs/guias/workflow-agricultura-cafe.md)

## Resultado esperado

Após adotar esta convenção, qualquer funcionalidade agrícola com IA deve deixar claro:

- que está usando IA
- por que isso importa
- como isso ajuda o usuário
- qual decisão ou ação ela destrava
