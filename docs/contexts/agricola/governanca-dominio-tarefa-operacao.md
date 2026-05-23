# AgroSaaS — Governança de Domínio — Tarefa × Operação × Atividade

## Objetivo

Eliminar ambiguidade de nomenclatura na camada de interface sem alterar:

- tabelas
- APIs
- regras de custo
- vínculo entre tarefa, operação, apontamento e apropriação econômica

## Termos oficiais

### Tarefa

Termo oficial para **planejamento e orquestração**.

Representa:

- intenção operacional
- ação planejada da safra
- item que organiza prioridade, fase, talhão e contexto

Contexto técnico atual:

- backend em `safra_tarefas`
- criada e gerida pelo módulo de tarefas da safra

### Operação

Termo oficial para **execução real de campo**.

Representa:

- operação agrícola efetivamente registrada
- aplicação, plantio, adubação, colheita e demais execuções
- origem do custo realizado no fluxo agrícola

Contexto técnico atual:

- backend em `OperacaoAgricola`
- integração com estoque, custos e financeiro

### Apontamento

Termo oficial para **medição operacional**.

Representa:

- registro de uso
- horas, área trabalhada, consumo e execução observada
- evidência operacional da execução

### Jornada

Termo oficial para **contexto temporal e de equipamento**.

Representa:

- janela operacional da máquina ou equipe
- contexto onde apontamentos são produzidos

### CostAllocation

Termo oficial para **apropriação econômica**.

Representa:

- distribuição do custo realizado
- consolidação econômica por unidade operacional

## Termo não oficial

### Atividade

`Atividade` não é entidade first-class no domínio agrícola atual.

Regra de governança:

- não usar `Atividade` como sinônimo de `Tarefa`
- não usar `Atividade` como sinônimo de `Operação`
- quando o contexto for planejamento, usar `Tarefa`
- quando o contexto for execução, usar `Operação`

`Atividade` só pode permanecer quando fizer parte de um texto legado, nome técnico ainda não migrado, ou contexto genérico fora do domínio operacional oficial.

## Fluxo operacional vigente

```text
Safra
-> Unidade Operacional
-> Tarefa
-> Operação
-> Apontamento / Jornada
-> Movimentos / Custos
-> CostAllocation
```

## Regras práticas de UI

- botões de planejamento: `Nova Tarefa`, `Editar Tarefa`, `Concluir Tarefa`, `Cancelar Tarefa`
- botões de execução: `Nova Operação`, `Registrar Operação`, `Operação Agrícola`
- relatórios de planejamento: `Tarefas Planejadas`
- relatórios de execução: `Operações`
- apontamentos devem referenciar `Operação`, não `Atividade`

## O que não muda neste step

- nenhuma tabela será renomeada
- nenhuma API será alterada
- `safra_tarefas` continua sendo a estrutura de planejamento
- `OperacaoAgricola` continua sendo a estrutura de execução
- `CostAllocation` continua sendo a estrutura de apropriação econômica
- não será criada entidade `Atividade`

## Decisão consolidada

- `Tarefa` = planejamento
- `Operação` = execução
- `Apontamento` = medição
- `Jornada` = contexto temporal/equipamento
- `CostAllocation` = apropriação econômica
- `Atividade` = termo deprecated na UI agrícola quando representar tarefa ou operação
