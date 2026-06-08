# Cenário de Teste — Lançamentos de Campo, Consumo, Financeiro e Rastreabilidade

## Objetivo

Executar um teste manual ponta a ponta com dados exemplo para validar:

- operação agrícola
- consumo de insumo
- baixa de estoque
- despesa financeira
- evento no caderno
- custo da safra
- rastreabilidade

## Dados exemplo

Substitua os IDs pelos dados reais do seu ambiente.

### Safra

- safra: `2025/2026`
- cultura: `Soja`

### Talhão

- nome: `Talhão 01`
- área: `25 ha`

### Produto

- nome: `Herbicida Teste`
- unidade: `L`

### Depósito

- nome: `Depósito Central`

### Operação

- tipo: `PULVERIZAÇÃO`
- descrição: `Aplicação de herbicida pós-emergente`
- data realizada: usar a data de hoje ou uma data passada
- fase: `DESENVOLVIMENTO`
- área aplicada: `10 ha`

### Insumo da operação

- produto: `Herbicida Teste`
- dose por hectare: `2`
- unidade: `L`

### Resultado esperado do insumo

- quantidade total consumida: `20 L`

### Tarefa opcional para vínculo

- título: `Aplicar herbicida no Talhão 01`
- tipo: `APLICACAO_DEFENSIVO`

---

## Passo 1 — Preparar estoque

Tela:

- `/dashboard/operacional/estoque`

### Ações

1. confirmar que existe depósito
2. se necessário, criar `Depósito Central`
3. registrar entrada de estoque para `Herbicida Teste`

### Exemplo de entrada

- quantidade: `100`
- custo unitário: `35,00`
- observação: `Carga inicial para teste operacional`

### Resultado esperado

- saldo disponível do produto = `100 L`

---

## Passo 2 — Criar tarefa agrícola

Tela:

- `/agricola/safras/{safra_id}/tarefas`

### Ações

1. criar tarefa
2. preencher:
   - tipo: `APLICACAO_DEFENSIVO`
   - descrição: `Aplicar herbicida no Talhão 01`
   - talhão: `Talhão 01`
   - fase: `DESENVOLVIMENTO`
3. salvar
4. iniciar
5. concluir

### Resultado esperado

- tarefa criada
- tarefa concluída

---

## Passo 3 — Criar operação agrícola

Tela:

- `/agricola/safras/{safra_id}/operacoes`

### Ações

1. clicar em `Nova Operação desta Safra`
2. preencher:
   - talhão: `Talhão 01`
   - data realizada: data atual ou passada
   - tipo: `PULVERIZAÇÃO`
   - fase: `DESENVOLVIMENTO`
   - descrição: `Aplicação de herbicida pós-emergente`
   - área aplicada: `10`
   - custo manual: `0` ou deixar conforme fluxo
3. adicionar insumo:
   - produto: `Herbicida Teste`
   - dose por hectare: `2`
   - unidade: `L`
4. salvar

### Resultado esperado

- quantidade consumida = `20 L`
- custo do insumo = `20 × 35,00 = 700,00`
- operação salva na fase correta

---

## Passo 4 — Validar estoque após a operação

Tela:

- `/dashboard/operacional/estoque`

### Resultado esperado

- saldo do produto passa de `100 L` para `80 L`
- existe movimentação de saída
- a movimentação reflete consumo operacional

---

## Passo 5 — Validar caderno

Tela:

- `/agricola/safras/{safra_id}/caderno`

### Resultado esperado

- existe evento canônico da operação
- a descrição da operação está visível
- o evento está na timeline da safra

---

## Passo 6 — Validar financeiro

Tela:

- `/agricola/safras/{safra_id}/financeiro`

### Resultado esperado

- aparece uma despesa ligada à operação
- valor esperado aproximado: `R$ 700,00`
- a timeline financeira mostra a despesa
- a origem do lançamento aponta para o processo operacional

---

## Passo 7 — Validar custos

Tela:

- `/dashboard/agricola/custos`

### Resultado esperado

- custo total realizado da safra aumenta
- custo por hectare é recalculado
- categoria da operação aparece no breakdown

---

## Passo 8 — Validar rastreabilidade

Tela:

- `/dashboard/agricola/rastreabilidade`

### Resultado esperado

- se o ambiente já tiver lote rastreável associado à safra, a cadeia deve refletir:
  - safra
  - talhão
  - operação
  - insumos

Observação:

Se o ambiente ainda não tiver lote gerado, a rastreabilidade completa do lote pode não aparecer neste cenário isolado. Ainda assim, a base operacional da cadeia já estará registrada.

---

## Passo 9 — Teste de invalidação documental

Tela:

- `/agricola/safras/{safra_id}/tarefas`

### Ações

1. localizar a tarefa concluída
2. invalidar a tarefa com motivo

### Motivo sugerido

- `Execução registrada incorretamente para teste de invalidação`

### Resultado esperado

- tarefa com status `INVALIDADA`
- evento no caderno continua existindo
- timeline do caderno indica origem invalidada
- histórico permanece auditável

---

## Resultado final esperado

Ao final do cenário, você deve conseguir comprovar:

1. o estoque baixou corretamente
2. a operação apareceu na safra
3. o caderno recebeu o evento
4. o financeiro refletiu a despesa
5. os custos foram consolidados
6. a invalidação documental preservou o histórico
