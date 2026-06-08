# Manual do Usuário — Lançamentos de Campo, Consumo, Financeiro e Rastreabilidade

## Objetivo

Este manual explica como fazer lançamentos operacionais no AgroSaaS para testar:

- atividades de campo
- consumo de produto/insumo
- baixa de estoque
- reflexo financeiro
- evento no Caderno de Campo
- rastreabilidade da cadeia operacional

O foco aqui é uso prático da aplicação, não implementação técnica.

## Visão rápida dos fluxos

Existem dois fluxos principais no sistema:

### Fluxo 1 — Tarefa

Use quando quiser testar:

- planejamento de atividade
- execução operacional
- mudança de status
- invalidação documental da origem
- integração com PWA Campo

Esse fluxo é bom para testar operação do dia a dia, mas sozinho não é o melhor caminho para validar consumo de insumo e financeiro.

### Fluxo 2 — Operação agrícola

Use quando quiser testar a cadeia completa:

- operação executada
- consumo de insumos
- baixa automática no estoque
- custo operacional
- despesa financeira automática
- evento canônico no Caderno
- rastreabilidade

Se o objetivo é validar integrações ponta a ponta, este é o fluxo principal.

## Recomendação de teste

Para testar a aplicação de forma completa, siga esta ordem:

1. cadastrar ou garantir estoque disponível para o produto
2. criar uma tarefa da safra
3. lançar uma operação agrícola `REALIZADA` com insumos
4. validar os reflexos no caderno, estoque, financeiro, custos e rastreabilidade

---

## 1. Planejamento e execução por tarefa

### Página web

- `/agricola/safras/{safra_id}/tarefas`

Arquivo da tela:

- [apps/web/src/app/(dashboard)/agricola/safras/[id]/tarefas/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/safras/[id]/tarefas/page.tsx)

Componente principal:

- [apps/web/src/components/agricola/safra-tarefas.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/agricola/safra-tarefas.tsx)

### O que o usuário faz

1. abrir a safra
2. entrar em `Tarefas`
3. criar uma nova tarefa
4. preencher tipo, talhão, descrição, fase e prioridade
5. iniciar a tarefa
6. concluir a tarefa

### Rotas usadas

- `GET /api/v1/safras/{safra_id}/tarefas`
- `POST /api/v1/safras/{safra_id}/tarefas`
- `PATCH /api/v1/tarefas/{tarefa_id}`
- `PATCH /api/v1/tarefas/{tarefa_id}/iniciar`
- `PATCH /api/v1/tarefas/{tarefa_id}/concluir`
- `DELETE /api/v1/tarefas/{tarefa_id}/rejeitar?motivo=...`
- `PATCH /api/v1/tarefas/{tarefa_id}/invalidar?motivo=...`

### O que esse fluxo gera

- tarefa planejada
- status operacional
- auditoria
- possibilidade de invalidação documental

### O que esse fluxo não garante sozinho

- baixa de estoque
- despesa financeira automática
- apropriação econômica completa

---

## 2. Tarefas do módulo Campo/PWA

### Página web de gestão

- `/dashboard/operacional/campo/tarefas`

Arquivo:

- [apps/web/src/app/(dashboard)/dashboard/operacional/campo/tarefas/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/campo/tarefas/page.tsx)

### Páginas do app Campo

- `/campo/tarefa/[id]`
- `/caderno`
- `/sync`

Arquivos:

- [apps/campo/src/app/(campo)/campo/tarefa/[id]/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/campo/tarefa/[id]/page.tsx)
- [apps/campo/src/app/(campo)/caderno/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx)

### O que o usuário faz

1. cria a tarefa programada no web
2. sincroniza o dispositivo Campo
3. abre a tarefa no app Campo
4. inicia e conclui a tarefa
5. opcionalmente registra evidências e caderno

### Rotas web/backoffice

- `GET /api/v1/campo/tarefas?limit=500`
- `POST /api/v1/campo/tarefas`
- `PATCH /api/v1/campo/tarefas/{id}`
- `DELETE /api/v1/campo/tarefas/{id}`
- `POST /api/v1/campo/tarefas/{id}/invalidar`

### Rotas de sync do PWA

- `GET /api/v1/sync/pull`
- `POST /api/v1/sync/push`
- `POST /api/v1/caderno/offline-sync`

### Quando usar este fluxo

Use para testar:

- execução offline
- sincronização do app Campo
- reconciliação com o Caderno oficial
- invalidação documental no fluxo do dispositivo

### Limitação importante

Concluir tarefa no Campo não substitui o lançamento de operação agrícola com insumos. Para testar estoque e financeiro, faça também a operação agrícola.

---

## 3. Lançamento de operação agrícola com consumo de insumo

Este é o fluxo mais importante para integração completa.

### Página web

- `/agricola/safras/{safra_id}/operacoes`

Arquivo:

- [apps/web/src/app/(dashboard)/agricola/safras/[id]/operacoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/safras/[id]/operacoes/page.tsx)

### O que o usuário faz

1. abrir a safra
2. entrar em `Execução por Fase`
3. clicar em `Nova Operação desta Safra`
4. preencher:
   - talhão
   - data realizada
   - tipo
   - fase
   - área aplicada
   - custo manual, se houver
   - operador, máquina e observações, se aplicável
   - insumos
5. salvar a operação como realizada

### Dados mínimos recomendados para teste

- safra válida
- talhão válido
- tipo de operação compatível com a fase
- data não futura
- área aplicada maior que zero
- produto em estoque suficiente

### Rotas usadas

- `GET /api/v1/operacoes/safra/{safra_id}/por-fase`
- `GET /api/v1/operacoes/safra/{safra_id}/fase/{fase}`
- `GET /api/v1/operacoes/tipos`
- `POST /api/v1/operacoes/`
- `PATCH /api/v1/operacoes/{id}`
- `GET /api/v1/operacoes?safra_id={safra_id}`
- `GET /api/v1/operacoes/export/pdf?safra_id={safra_id}`

### O que esse fluxo gera automaticamente

- operação agrícola
- consumo FIFO dos lotes de estoque
- baixa de estoque
- custo real da operação
- despesa financeira automática
- evento canônico no Caderno
- conclusão da tarefa vinculada, se a operação tiver `tarefa_id`

### O que validar após salvar

- a operação aparece na lista da fase
- o custo total foi calculado
- os insumos ficaram vinculados à operação
- o caderno recebeu o evento
- o estoque foi reduzido
- o financeiro recebeu a despesa

---

## 4. Estoque — preparar e validar consumo

### Página

- `/dashboard/operacional/estoque`

Arquivo:

- [apps/web/src/app/(dashboard)/dashboard/operacional/estoque/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/estoque/page.tsx)

### O que fazer antes da operação

Se quiser testar consumo de insumo corretamente:

1. garantir que exista depósito
2. garantir que o produto exista
3. fazer uma entrada de estoque do produto
4. confirmar saldo disponível

### Rotas usadas

- `GET /api/v1/estoque/depositos`
- `POST /api/v1/estoque/depositos`
- `GET /api/v1/estoque/saldos`
- `GET /api/v1/estoque/movimentacoes`
- `GET /api/v1/estoque/alertas`
- `POST /api/v1/estoque/movimentacoes/entrada`
- `POST /api/v1/estoque/movimentacoes/saida`
- `POST /api/v1/estoque/movimentacoes/ajuste`
- `POST /api/v1/estoque/movimentacoes/transferencia`

### O que validar depois da operação agrícola

- houve movimentação de saída
- o saldo do produto diminuiu
- o custo médio e a auditoria da movimentação permanecem íntegros

---

## 5. Caderno de Campo — validar o reflexo documental

### Página

- `/agricola/safras/{safra_id}/caderno`

Arquivo:

- [apps/web/src/app/(dashboard)/agricola/safras/[id]/caderno/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/safras/[id]/caderno/page.tsx)

### O que validar

Depois da operação agrícola `REALIZADA`, deve existir um evento canônico no Caderno.

Verifique:

- tipo do evento
- descrição
- status do evento
- vínculo com a operação
- fotos/evidências, se houver

### Rotas usadas

- `GET /api/v1/caderno/safra/{safra_id}/timeline`
- `GET /api/v1/caderno/timeline`
- `POST /api/v1/caderno/entradas`
- `GET /api/v1/caderno/entradas/{entrada_id}`
- `PATCH /api/v1/caderno/entradas/{entrada_id}`
- `PATCH /api/v1/caderno/{entrada_id}/status`
- `DELETE /api/v1/caderno/entradas/{entrada_id}`
- `POST /api/v1/caderno/entradas/{entrada_id}/reprocessar`
- `POST /api/v1/caderno/exportar`
- `GET /api/v1/caderno/exportacoes/{id}/download`

### Casos adicionais para teste

- aprovar ou rejeitar o evento
- retificar o evento
- invalidar a tarefa de origem
- confirmar que a timeline mostra a invalidação documental

---

## 6. Financeiro — validar a despesa gerada

### Página

- `/agricola/safras/{safra_id}/financeiro`

Arquivo:

- [apps/web/src/app/(dashboard)/agricola/safras/[id]/financeiro/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/safras/[id]/financeiro/page.tsx)

### O que validar

Depois de lançar a operação com custo:

- a despesa deve aparecer no resumo financeiro
- a timeline financeira deve refletir a operação como despesa
- os lançamentos por origem devem mostrar a rastreabilidade do lançamento

### Rotas usadas

- `GET /api/v1/agricola/dashboard/safras/{id}/resumo-financeiro`
- `GET /api/v1/agricola/dre/v1?safra_id={id}`
- `GET /api/v1/financeiro/lancamentos/origens?safra_id={id}`
- `PATCH /api/v1/financeiro/lancamentos/{id}`

### Componentes úteis na tela

- [apps/web/src/components/agricola/transacao-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/agricola/transacao-timeline.tsx)
- [apps/web/src/components/financeiro/lancamentos-origem-card.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/financeiro/lancamentos-origem-card.tsx)

---

## 7. Custos agrícolas — validar apropriação

### Páginas

- `/agricola/custos`
- `/dashboard/agricola/custos`

Arquivos:

- [apps/web/src/app/(dashboard)/agricola/custos/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/agricola/custos/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/agricola/custos/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/custos/page.tsx)

### O que validar

- custo total realizado da safra
- custo por hectare
- breakdown por categoria
- divergência entre orçamento e realizado

### Rota usada

- `GET /api/v1/custos/safra/{safra_id}`

---

## 8. Rastreabilidade — validar cadeia completa

### Página

- `/dashboard/agricola/rastreabilidade`

Arquivo:

- [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx)

### O que validar

Após existir produção/lote vinculado ao processo, verifique a cadeia:

- lote
- safra
- talhão
- operações
- insumos aplicados
- colheita
- certificações

### Rotas usadas

- `GET /api/v1/rastreabilidade/lotes`
- `GET /api/v1/rastreabilidade/certificacoes?unidade_produtiva_id=...`
- `GET /api/v1/rastreabilidade/lotes/{lote_id}/cadeia`

---

## 9. Roteiro mínimo de teste ponta a ponta

### Cenário recomendado

1. entrar em `/dashboard/operacional/estoque`
2. criar depósito, se necessário
3. fazer entrada de estoque para um produto
4. entrar em `/agricola/safras/{safra_id}/tarefas`
5. criar uma tarefa da safra
6. entrar em `/agricola/safras/{safra_id}/operacoes`
7. criar operação `REALIZADA` com:
   - talhão
   - área aplicada
   - custo manual, se houver
   - pelo menos um insumo
   - vínculo com a tarefa, se disponível no fluxo
8. abrir `/agricola/safras/{safra_id}/caderno`
9. confirmar evento gerado
10. abrir `/dashboard/operacional/estoque`
11. confirmar saída de estoque
12. abrir `/agricola/safras/{safra_id}/financeiro`
13. confirmar despesa lançada
14. abrir `/dashboard/agricola/custos`
15. confirmar custo consolidado
16. abrir `/dashboard/agricola/rastreabilidade`
17. confirmar a cadeia, se já houver lote/produto rastreável associado

---

## 10. O que observar em caso de erro

### Se a operação não salvar

Verifique:

- fase incompatível com o tipo
- data futura
- área aplicada maior que a área do talhão
- produto sem estoque suficiente
- depósito/lote inconsistentes

### Se o estoque não baixar

Verifique:

- se a operação realmente teve insumos
- se havia saldo para consumo
- se a operação foi salva como `REALIZADA`

### Se o financeiro não refletir

Verifique:

- se a operação ficou com `custo_total > 0`
- se existe conta contábil de custeio ativa
- se o lançamento foi gerado como despesa de origem `OPERACAO_AGRICOLA`

### Se o caderno não refletir

Verifique:

- se a operação foi criada/atualizada para `REALIZADA`
- se a timeline da safra está filtrada corretamente

---

## 11. Resumo final

### Para testar só operação de campo

Use:

- `/agricola/safras/{safra_id}/tarefas`
- `/dashboard/operacional/campo/tarefas`
- app Campo

### Para testar integração completa

Use principalmente:

- `/dashboard/operacional/estoque`
- `/agricola/safras/{safra_id}/operacoes`
- `/agricola/safras/{safra_id}/caderno`
- `/agricola/safras/{safra_id}/financeiro`
- `/dashboard/agricola/custos`
- `/dashboard/agricola/rastreabilidade`

### Regra prática

Se você precisa validar consumo de produto, custo, despesa financeira e rastreabilidade, faça o teste pela tela de `Operações`.
