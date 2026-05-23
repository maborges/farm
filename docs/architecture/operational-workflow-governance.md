# AgroSaaS — Governança de Workflow Operacional

## Objetivo

Formalizar a primeira camada de governança operacional do AgroSaaS sem ruptura de legado, sem novas tabelas e sem bloquear usuários.

Este documento consolida:

- workflow oficial
- critérios de fechamento
- regras por tipo de tarefa
- fluxos paralelos legítimos
- inconsistências observáveis

## Princípios

- evoluir o domínio existente
- não duplicar engine, dashboard, serviço ou entidade
- distinguir planejamento de execução
- distinguir valuation operacional de apropriação econômica
- tornar inconsistências visíveis antes de bloquear comportamento

## Fluxo Oficial

```text
Tarefa
-> Operação
-> Execução
-> Movimentos
-> Custos
-> CostAllocation
-> Fechamento
```

## Papéis Oficiais

- `Tarefa` representa planejamento e orquestração
- `Operação` representa execução real
- `OperacaoExecucao` representa evidência operacional da execução
- `EstoqueMovimento` representa a trilha física e o valuation
- `Despesa` representa a consequência financeira rastreável
- `CostAllocation` representa apropriação econômica
- `Apontamento` e `Jornada` representam medição e contexto operacional

## Estados Oficiais Propostos

### Tarefa

- `PENDENTE_APROVACAO`
- `PLANEJADA`
- `EM_EXECUCAO`
- `PARCIAL`
- `CONCLUIDA`
- `CANCELADA`

Observação:
- no domínio atual, `APROVADA` pode ser tratada como equivalente funcional de `PLANEJADA`

### Operação

- `PLANEJADA`
- `EM_EXECUCAO`
- `REALIZADA`
- `VALIDADA`
- `CANCELADA`

### Apropriação

- `PENDENTE`
- `APROPRIADA`
- `INCONSISTENTE`

## Regras Por Tipo de Tarefa

### Operacional agrícola

- deve gerar `OperacaoAgricola`
- pode gerar `OperacaoExecucao`
- pode gerar consumo de estoque
- pode gerar custo
- deve gerar `CostAllocation` quando houver custo direto e `production_unit_id`

### Administrativa

- pode não gerar operação
- pode não gerar custo
- pode concluir por justificativa administrativa

### Inspeção

- pode gerar checklist, monitoramento ou apontamento
- pode não gerar custo
- pode não exigir operação agrícola quando o evento for apenas observacional

### Manutenção / frota

- pode gerar `OrdemServico`, `Jornada` e `Apontamento`
- pode gerar movimento de estoque
- pode gerar despesa e apropriação
- não substitui operação agrícola

### Financeira / comercial

- pode gerar `Despesa`, `Receita` ou `Rateio`
- não exige operação agrícola
- exige rastreabilidade de origem quando o lançamento for automático

## Critérios de Fechamento

### Quando a tarefa pode concluir

- tarefa operacional agrícola não deve concluir sem operação vinculada
- tarefa operacional não deve concluir com operação ainda `PLANEJADA` ou `EM_EXECUCAO`
- tarefa administrativa pode concluir sem operação
- tarefa de inspeção pode concluir sem custo
- fechamento administrativo excepcional deve ter justificativa rastreável

### Quando a operação pode concluir

- operação `REALIZADA` deve ter ao menos uma `OperacaoExecucao`
- operação com custo direto e `production_unit_id` deve gerar `CostAllocation`
- operação com consumo de insumo deve deixar trilha em `EstoqueMovimento`
- operação sem custo é legítima apenas quando não houver evento econômico direto

### Quando o apontamento é obrigatório

- obrigatório quando a medição operacional é parte da evidência de execução
- opcional em operação manual simplificada, desde que haja outra trilha suficiente
- apontamento com custo não deve ficar sem contexto operacional mínimo

### Quando a apropriação é obrigatória

- obrigatória para custo operacional direto com `production_unit_id`
- opcional para custo indireto ainda sem contexto agrícola resolvido
- proibido tratar `Despesa` ou `LancamentoFinanceiro` como substitutos de `CostAllocation`

## Fluxos Paralelos Legítimos

### Ordem de serviço

- fluxo oficial de manutenção
- pode gerar estoque, despesa e apropriação
- não substitui `OperacaoAgricola`

### Financeiro

- despesas contratuais, fiscais, administrativas ou indiretas podem nascer fora da operação
- quando automáticas, devem ter `origem_tipo` e `origem_id`

### Rateio

- mecanismo legítimo para custos indiretos
- não deve competir com apropriação direta do mesmo fato gerador

### Apontamento manual

- legítimo para medição ou retroalimentação operacional
- problemático quando gera custo sem operação, jornada ou contexto agrícola suficiente

## Fluxos Considerados Inconsistentes

- tarefa operacional concluída sem operação
- operação realizada sem execução
- operação com custo e `production_unit_id` sem `CostAllocation`
- apontamento com custo sem operação, jornada ou contexto mínimo
- pedido recebido sem trilha completa de movimento/lote
- despesa automática sem origem rastreável
- `CostAllocation` duplicada para a mesma origem operacional

## Classificação de Severidade

### Warning leve

- situação permitida pelo domínio atual, mas que merece atenção

### Inconsistência moderada

- quebra de sequência operacional sem impacto econômico direto imediato

### Risco econômico

- afeta custo, apropriação ou rastreabilidade financeira

### Risco crítico

- compromete valuation, rastreabilidade patrimonial ou pode duplicar custo

## Observabilidade no Step 01

Neste step, a visibilidade deve reutilizar:

- `AlertasAgricolasService`
- `AlertasEngine`
- `NotificacaoService`
- `TenantAuditLog`
- centros de notificação e auditoria já existentes

Sem fazer ainda:

- bloqueio de fechamento
- alteração de schema
- criação de dashboard paralelo
- reescrita dos serviços de domínio

## Próximo Passo Recomendado

- ativar validações leves apenas em novos registros
- usar os achados observados neste step para calibrar exceções legítimas
- só depois introduzir bloqueios direcionados por tipo de tarefa e origem de custo
