# Checklist QA — Lançamentos de Campo, Consumo, Financeiro e Rastreabilidade

## Objetivo

Checklist rápido para validar a cadeia:

- tarefa
- operação
- estoque
- caderno
- financeiro
- custos
- rastreabilidade

## Pré-condições

- existe uma safra ativa
- existe pelo menos um talhão vinculado à safra
- existe pelo menos um produto/insumo ativo
- existe pelo menos um depósito ativo
- o produto possui saldo disponível em estoque

## 1. Tarefa

- [ ] Acessar `/agricola/safras/{safra_id}/tarefas`
- [ ] Criar tarefa com tipo, descrição, talhão e fase
- [ ] Confirmar que a tarefa aparece na lista
- [ ] Iniciar a tarefa
- [ ] Confirmar status `EM_EXECUCAO`
- [ ] Concluir a tarefa
- [ ] Confirmar status `CONCLUIDA`

## 2. Operação agrícola

- [ ] Acessar `/agricola/safras/{safra_id}/operacoes`
- [ ] Criar nova operação
- [ ] Informar talhão, data, tipo, fase e área aplicada
- [ ] Informar pelo menos um insumo
- [ ] Salvar com status realizado
- [ ] Confirmar que a operação aparece na fase correta
- [ ] Confirmar que custo total foi calculado

## 3. Estoque

- [ ] Acessar `/dashboard/operacional/estoque`
- [ ] Confirmar que existe movimentação de saída
- [ ] Confirmar que o saldo do produto foi reduzido
- [ ] Confirmar que a saída está ligada ao contexto operacional esperado

## 4. Caderno de Campo

- [ ] Acessar `/agricola/safras/{safra_id}/caderno`
- [ ] Confirmar que o evento oficial da operação foi criado
- [ ] Confirmar descrição, data e status do evento
- [ ] Confirmar vínculo documental com a operação

## 5. Financeiro

- [ ] Acessar `/agricola/safras/{safra_id}/financeiro`
- [ ] Confirmar reflexo no resumo financeiro
- [ ] Confirmar despesa na timeline financeira
- [ ] Confirmar lançamento em `Origem dos Lançamentos`

## 6. Custos

- [ ] Acessar `/dashboard/agricola/custos`
- [ ] Selecionar a safra
- [ ] Confirmar custo total realizado
- [ ] Confirmar custo por hectare
- [ ] Confirmar breakdown por categoria

## 7. Rastreabilidade

- [ ] Acessar `/dashboard/agricola/rastreabilidade`
- [ ] Confirmar que o lote aparece, se o cenário já tiver lote gerado
- [ ] Abrir a cadeia do lote
- [ ] Confirmar presença de safra, talhão, operações e insumos

## 8. Invalidação documental

- [ ] Invalidar uma tarefa concluída
- [ ] Confirmar que a tarefa passa para `INVALIDADA`
- [ ] Confirmar reflexo no caderno
- [ ] Confirmar que o evento continua existindo
- [ ] Confirmar sinalização documental de origem invalidada

## 9. Critério de aceite

- [ ] Nenhum dado operacional foi apagado
- [ ] O consumo de estoque ocorreu corretamente
- [ ] O financeiro refletiu a operação
- [ ] O caderno preservou rastreabilidade
- [ ] A invalidação preservou histórico
- [ ] A cadeia documental continua auditável
