# Workflow Completo de Teste — Agricultura Café

## Objetivo

Versão derivada do workflow agrícola focada em café, cobrindo o ciclo operacional, monitoramento, colheita, beneficiamento e análise econômica de uma safra cafeeira.

Documento base relacionado:

- [workflow-agricultura.md](/opt/lampp/htdocs/farm/docs/guias/workflow-agricultura.md)

## Modelo de navegação esperado

Para café, o fluxo deve seguir 2 níveis:

- sidebar global do módulo para visão consolidada
- subnav da safra para operação diária

## Caminhos do menu no sidebar

Use sempre o menu lateral esquerdo como ponto de partida. Quando o documento citar um caminho, leia da esquerda para a direita como uma sequência de cliques no sidebar.

| Objetivo | Caminho no sidebar | Rota |
|---|---|---|
| Cadastrar ou revisar a fazenda | `Cadastros > Minha Propriedade > Propriedades` | `/cadastros/propriedades` |
| Cadastrar ou revisar talhões | `Cadastros > Minha Propriedade > Georreferenciamento` | `/cadastros/propriedades/talhoes` |
| Cadastrar produtos, fertilizantes e defensivos | `Cadastros > Insumos & Ativos > Catálogo de Produtos` | `/cadastros/produtos` |
| Cadastrar equipamentos e frota | `Cadastros > Insumos & Ativos > Equipamentos & Frota` | `/cadastros/equipamentos` |
| Cadastrar pessoas, operadores e parceiros | `Cadastros > Pessoas & Parceiros > Pessoas e Parceiros` | `/cadastros/pessoas` |
| Preparar e consultar o estoque de insumos | `Suprimentos > ② Estoque > Almoxarifado` | `/suprimentos/estoque` |
| Programar tarefas para execução no aplicativo | `Campo PWA > Dispositivos > Tarefas de Campo` | `/dashboard/operacional/campo/tarefas` |
| Cadastrar culturas e variedades | `Agricultura > ① Planejamento da Safra > Culturas e Variedades` | `/agricola/cadastros/culturas` |
| Abrir a lista de safras | `Agricultura > Visão Geral > Safras` | `/agricola/safras` |
| Criar a safra de café | `Agricultura > Visão Geral > Safras > Nova Safra` | `/agricola/safras` |
| Planejar orçamento geral | `Agricultura > ① Planejamento da Safra > Orçamento de Safra` | `/agricola/planejamento` |
| Registrar custos agrícolas | `Agricultura > ① Planejamento da Safra > Custeio Agrícola` | `/agricola/custos` |
| Consultar operações consolidadas | `Agricultura > ② Execução & Registros > Operações Consolidadas` | `/agricola/operacoes` |
| Registrar caderno de campo consolidado | `Agricultura > ② Execução & Registros > Caderno de Campo` | `/agricola/caderno` |
| Monitorar pragas e doenças | `Agricultura > ③ Monitoramento > Pragas & Doenças` | `/agricola/monitoramento` |
| Registrar fenologia | `Agricultura > ③ Monitoramento > Fenologia` | `/agricola/fenologia` |
| Registrar romaneios | `Agricultura > ④ Colheita & Pós-Colheita > Romaneios de Colheita` | `/agricola/romaneios` |
| Registrar beneficiamento | `Agricultura > ④ Colheita & Pós-Colheita > Beneficiamento` | `/agricola/beneficiamento` |
| Emitir relatórios | `Agricultura > ⑤ Gestão & Relatórios > Relatórios` | `/agricola/relatorios` |

Depois que a safra for criada e aberta, a aplicação também mostra uma navegação horizontal própria da safra. Essa navegação aparece no topo das páginas de `/agricola/safras/{id}` e deve ser usada para operar tudo que pertence somente àquela safra.

| Objetivo dentro da safra | Navegação interna da safra | Rota |
|---|---|---|
| Ver resumo da safra | `Resumo > Visão Geral` | `/agricola/safras/{id}` |
| Ver indicadores da safra | `Resumo > Dashboard` | `/agricola/safras/{id}/dashboard` |
| Montar orçamento da safra | `Planejamento > Orçamento` | `/agricola/safras/{id}/orcamento` |
| Conferir unidades/talhões da safra | `Planejamento > Unidades` | `/agricola/safras/{id}/production-units` |
| Registrar análise de solo da safra | `Planejamento > Solo` | `/agricola/safras/{id}/analises-solo` |
| Comparar cenários | `Planejamento > Cenários` | `/agricola/safras/{id}/cenarios` |
| Registrar execução por fase | `Execução > Execução` | `/agricola/safras/{id}/operacoes` |
| Criar tarefas | `Execução > Tarefas` | `/agricola/safras/{id}/tarefas` |
| Executar checklist | `Execução > Checklist` | `/agricola/safras/{id}/checklist` |
| Conferir estoque vinculado | `Execução > Estoque` | `/agricola/safras/{id}/estoque` |
| Registrar sanidade | `Monitoramento > Sanidade` | `/agricola/safras/{id}/monitoramento` |
| Registrar fenologia da safra | `Monitoramento > Fenologia` | `/agricola/safras/{id}/fenologia` |
| Consultar NDVI | `Monitoramento > NDVI` | `/agricola/safras/{id}/ndvi` |
| Registrar romaneios da safra | `Colheita > Romaneios` | `/agricola/safras/{id}/romaneios` |
| Registrar beneficiamento da safra | `Colheita > Beneficiamento` | `/agricola/safras/{id}/beneficiamento` |
| Conferir financeiro | `Gestão > Financeiro` | `/agricola/safras/{id}/financeiro` |
| Consultar caderno da safra | `Gestão > Caderno` | `/agricola/safras/{id}/caderno` |

### Entrada global

Usar o sidebar global para:

- abrir `Safras`
- consultar `Operações Consolidadas`
- acessar visão ampla de `Monitoramento`, `Romaneios` e `Relatórios`

### Operação da safra

Depois de abrir `/agricola/safras/{id}`, executar o fluxo principalmente por:

- `Resumo`
- `Planejamento`
- `Execução`
- `Monitoramento`
- `Colheita`
- `Gestão`

Para café, isso é importante porque a cultura perene exige leitura contínua de fase, monitoramento e pós-colheita no mesmo contexto operacional.

### Como interpretar as ações deste guia

Cada etapa informa três coisas separadamente:

- **Menu/subnav**: caminho usado para chegar à tela.
- **Botão de abertura**: controle que abre o formulário ou inicia a ação.
- **Botão de confirmação**: controle que grava a informação e produz o efeito descrito.

Abrir um formulário não altera o processo. A alteração ocorre somente ao usar o botão de confirmação e receber a mensagem de sucesso. Nos avanços de fase, o sistema pode exigir a conclusão do checklist e das tarefas obrigatórias da fase atual.

## Capturas de referência

### Dashboard Agrícola

![Dashboard Agrícola](./assets/agricola-dashboard.png)

### Planejamento

![Planejamento](./assets/agricola-planejamento.png)

## Escopo do teste

O workflow cobre:

- criação da safra de café
- orçamento global e orçamento da safra
- manejo por fase no contexto da safra
- fenologia da safra
- monitoramento fitossanitário da safra
- caderno de campo da safra
- romaneios da safra
- beneficiamento da safra
- financeiro da safra
- cenários e comparativo
- dashboard executivo e dashboard agrícola

## Persona de teste

- tipo: produtor de café com suporte técnico
- Produtor: 1 produtor ativo e isolado
- perfil mínimo:
  - criar e editar safra
  - registrar operações
  - registrar fenologia
  - registrar monitoramento
  - registrar romaneios
  - acessar financeiro e cenários

## Pré-requisitos

- fazenda e talhões cafeeiros cadastrados
- usuário autenticado na conta do produtor correta
- planos de conta de despesa e receita ativos
- produtos e insumos cadastrados
- estoque inicial carregado, se aplicável
- ao menos um depósito ativo e um lote com saldo suficiente para cada insumo que será consumido
- plano de conta ativo com categoria RFB `CUSTEIO`, necessário para a despesa automática da operação
- dispositivo Campo ativado e associado ao produto, quando o cenário incluir execução offline
- operador com acesso ao aplicativo Campo e tarefa programada para a data atual ou anterior

### Checklist antes de criar a safra

Antes de clicar em `Nova Safra`, confirme estes cadastros. Sem eles, o usuário até pode abrir a tela de safras, mas terá dificuldade para vincular talhões, selecionar cultura ou executar o restante do workflow.

| Verificação | Caminho no sidebar | O que conferir |
|---|---|---|
| Produto correto | seletor de empresa/fazenda no topo da aplicação | a operação deve estar no produto da fazenda que será usada no teste |
| Fazenda cadastrada | `Cadastros > Minha Propriedade > Propriedades` | existe uma propriedade chamada `Fazenda Boa Esperança` |
| Talhões cadastrados | `Cadastros > Minha Propriedade > Georreferenciamento` | existem os talhões `Café A1`, `Café A2` e `Café B1`, todos como tipo `TALHAO` |
| Área dos talhões | `Cadastros > Minha Propriedade > Georreferenciamento` | A1 tem `20,00 ha`, A2 tem `25,00 ha` e B1 tem `30,00 ha` |
| Cultura cadastrada | `Agricultura > ① Planejamento da Safra > Culturas e Variedades` | existe a cultura `Café`; se houver variedade, usar `Catuaí 144` |
| Produtos cadastrados | `Cadastros > Insumos & Ativos > Catálogo de Produtos` | existem fertilizantes, defensivos e demais insumos que serão usados no planejamento; a lista do catálogo é descritiva e não deve ser usada como fonte de valuation |
| Pessoas cadastradas | `Cadastros > Pessoas & Parceiros > Pessoas e Parceiros` | existe ao menos um operador ou responsável técnico, se o fluxo de execução exigir |

## Estratégia do cenário

Usar uma safra de café em produção porque esse fluxo valida:

- cultura perene
- manejo entre safras
- monitoramento fenológico e fitossanitário
- romaneio de colheita por lote
- beneficiamento com perda de peso
- rastreabilidade da origem ao lote final

## Destaque de IA no fluxo

No café, a IA deve ser destacada porque ajuda muito na interpretação técnica e econômica de uma cultura perene. Ela deve apoiar o usuário principalmente em monitoramento, leitura de risco, qualidade do lote e comparação de cenários.

O esperado é que a IA:

- deixe claro que a funcionalidade está usando análise assistida
- explique o motivo da recomendação com base nos dados da safra
- transforme leitura técnica em decisão prática para o produtor, gestor ou agrônomo

## Massa de dados base

### Fazenda

| Campo | Valor |
|---|---|
| Fazenda | Fazenda Boa Esperança |
| Município | Patrocínio |
| Estado | MG |
| Área total | 150,00 ha |

### Talhões da safra

| Talhão | Área | Situação |
|---|---:|---|
| Café A1 | 20,00 ha | Produção adulta |
| Café A2 | 25,00 ha | Produção intermediária |
| Café B1 | 30,00 ha | Produção adulta |

Área total da safra:

- `75,00 ha`

### Safra de teste

| Campo | Valor |
|---|---|
| Ano agrícola | 2025/26 |
| Cultura | Café |
| Cultivar | Catuaí 144 |
| Status inicial | PLANEJADA |
| Data prevista de início | 2025-07-15 |
| Data prevista de colheita | 2026-06-10 |
| Produtividade meta | 42,00 sc/ha |
| Área plantada | 75,00 ha |

### Insumos sugeridos

| Produto | Tipo | Unidade | Valor unitário |
|---|---|---|---:|
| Ureia 45% | FERTILIZANTE | kg | R$ 3,20 |
| KCl | FERTILIZANTE | kg | R$ 3,55 |
| Superfosfato simples | FERTILIZANTE | kg | R$ 2,90 |
| Fungicida para ferrugem | DEFENSIVO | L | R$ 118,00 |
| Inseticida broca do café | DEFENSIVO | L | R$ 135,00 |
| Herbicida pós-emergente | DEFENSIVO | L | R$ 37,00 |

## Workflow específico

## Integrações transversais: tarefa, estoque e financeiro

Estas integrações não nascem em uma única tela. Para enxergar a cadeia completa, use o fluxo abaixo:

```text
Gestor programa tarefa no web
    -> dispositivo recebe a tarefa por sincronização
    -> operador inicia e conclui no Campo PWA
    -> dispositivo envia status, observação, fotos e GPS
    -> gestor confere o retorno em Tarefas de Campo
    -> operação agrícola REALIZADA é registrada com os insumos consumidos
    -> sistema baixa o estoque por FIFO
    -> sistema calcula o custo real e cria a despesa financeira
    -> operação também aparece no Caderno de Campo
```

### Onde cada registro é gerado

| Registro gerado | Ação que gera | Menu e botão | Retorno para conferir |
|---|---|---|---|
| Tarefa enviada ao Campo PWA | programar tarefa | `Campo PWA > Dispositivos > Tarefas de Campo` > `Nova Tarefa` > `Programar Tarefa` | tarefa web com origem `PROGRAMADA` e status `PENDENTE`; após o pull, aparece no início do aplicativo em `Para Hoje` ou `Atrasadas` |
| Início da execução no campo | operador iniciar a tarefa recebida | aplicativo Campo > card da tarefa > `Iniciar Tarefa` | grava localmente `EM_EXECUCAO` e a data/hora de início; após sincronizar, o mesmo status aparece no web |
| Conclusão e evidências | operador concluir a tarefa | aplicativo Campo > tarefa > preencher observação/fotos > `Concluir Tarefa` | grava localmente `CONCLUIDA`, data/hora, observação, fotos e GPS; após sincronizar, esses dados aparecem na linha/detalhe da tarefa no web |
| Evento manual do caderno no campo | operador registrar uma ocorrência vinculada à tarefa | aplicativo Campo > tarefa > `Registrar no Caderno` | entrada fica na fila local e, após sincronização, é reconciliada com o Caderno oficial da safra |
| Operação, consumo e custo realizado | registrar operação com status `REALIZADA` e insumos | safra > `Execução > Execução` > `Nova Operação desta Safra` > `Adicionar` insumo > `Registrar nesta Safra` | operação aparece na fase; custo é calculado com o consumo real dos lotes de estoque |
| Movimentação automática de estoque | confirmação da operação `REALIZADA` com insumo e saldo disponível | não existe botão adicional: ocorre dentro de `Registrar nesta Safra` | safra > `Execução > Estoque` mostra uma `SAÍDA`; `Suprimentos > ② Estoque > Almoxarifado` mostra o histórico e o novo saldo |
| Despesa financeira automática | confirmação da operação `REALIZADA` com custo maior que zero e plano de conta de custeio ativo | não existe botão adicional: ocorre na mesma transação de `Registrar nesta Safra` | safra > `Gestão > Financeiro` mostra despesa `PAGO`, com origem `OPERACAO_AGRICOLA`; o custo realizado da safra é recalculado |
| Evento oficial no caderno | confirmação da operação `REALIZADA` | não existe botão adicional | safra > `Gestão > Caderno` mostra o evento canônico da operação |

### Duas telas de tarefas com finalidades diferentes

| Tela | Para que serve | Envia ao Campo PWA? | Gera estoque/financeiro? |
|---|---|---|---|
| safra > `Execução > Tarefas` | planejar e acompanhar tarefas internas da safra e suas pendências de fase | não é a tela de programação do dispositivo | não; tarefa sozinha não consome insumo nem cria despesa |
| `Campo PWA > Dispositivos > Tarefas de Campo` | programar trabalho para o operador receber e executar no aplicativo | sim, por sincronização | não; a conclusão retorna execução e evidências, mas não substitui a operação agrícola `REALIZADA` |

### Roteiro de sincronização da tarefa de campo

1. No web, abra `Campo PWA > Dispositivos > Tarefas de Campo`.
2. Clique em `Nova Tarefa` e preencha módulo `Agrícola`, safra `Café 2025/26`, talhão, operador, data programada, prioridade e descrição.
3. Clique em `Programar Tarefa`. Isso cria a tarefa como `PENDENTE`; ainda não cria operação, baixa ou despesa.
4. No aplicativo Campo, abra `Sincronização` e clique em `Sincronizar agora`. O pull traz tarefas com data programada até o dia atual e status `PENDENTE` ou `EM_EXECUCAO`.
5. Na página inicial do aplicativo, abra a tarefa em `Para Hoje` ou `Atrasadas` e clique em `Iniciar Tarefa`.
6. Execute o trabalho, registre observação, fotos e GPS e clique em `Concluir Tarefa`. O retorno permanece local enquanto estiver offline.
7. Abra `Sincronização` e clique em `Sincronizar agora`. Confirme `Na fila: 0`, `Com erro: 0` e a atualização de `Última sincronização`.
8. Volte ao web em `Campo PWA > Dispositivos > Tarefas de Campo`, atualize a lista e confira status `CONCLUIDA`, horários, observações e imagens.
9. Se houver item em `Com erro`, abra-o na tela de sincronização, revise a falha e reenvie. Não considere a execução consolidada no servidor enquanto a fila não estiver limpa.

> **Importante:** concluir a tarefa no aplicativo não cria automaticamente a operação agrícola com consumo. Para produzir baixa de estoque, custo e despesa, registre também a operação `REALIZADA` em `Execução > Execução`, vinculando a tarefa quando o campo estiver disponível.

### Cenário integrado de café para validar estoque e financeiro

Use uma das pulverizações da Etapa 7 para comprovar os reflexos:

| Dado | Valor de teste |
|---|---|
| Operação | `PULVERIZACAO` no talhão `Café A2` |
| Área aplicada | `25,00 ha` |
| Produto | `Fungicida para ferrugem` |
| Dose | `3,00 L/ha` |
| Consumo esperado | `75,00 L` |
| Saldo inicial sugerido | `100,00 L` |
| Custo unitário do lote | `R$ 118,00/L` |
| Custo de insumo esperado | `R$ 8.850,00` |
| Saldo final esperado | `25,00 L` |

#### Preparar o saldo antes da execução

1. Acesse `Suprimentos > ② Estoque > Almoxarifado`.
2. Se necessário, use `Novo Produto` e `Novo Depósito` para completar os cadastros.
3. Clique em `Entrada`, preencha produto, depósito, quantidade `100,00 L`, custo unitário `R$ 118,00` e lote.
4. Clique em `Confirmar Entrada`. Isso gera uma movimentação `ENTRADA` e disponibiliza o saldo para consumo.
5. Confirme no `Histórico de Movimentações` e na consulta de saldo que existem `100,00 L` disponíveis.

#### Gerar os reflexos automáticos

1. Na safra, acesse `Execução > Execução` e clique em `Nova Operação desta Safra`.
2. Informe status `REALIZADA` (ou mantenha o padrão realizado da tela), tipo `PULVERIZACAO`, talhão `Café A2`, área `25,00 ha`, custo manual `R$ 0,00` e uma data atual ou passada.
3. Na seção de insumos, clique em `Adicionar`, selecione `Fungicida para ferrugem` e informe dose `3,00 L/ha`.
4. Clique em `Registrar nesta Safra`.
5. A confirmação é atômica: se faltar saldo, lote válido, depósito compatível ou plano de conta de custeio, a operação deve falhar sem deixar baixa ou despesa parcial.

#### Conferir os retornos

| Conferência | Caminho | Resultado esperado |
|---|---|---|
| Operação | safra > `Execução > Execução` | pulverização listada como `REALIZADA`, com consumo `75,00 L` e custo calculado |
| Estoque da safra | safra > `Execução > Estoque` | movimentação `SAÍDA` vinculada à execução da operação |
| Estoque global | `Suprimentos > ② Estoque > Almoxarifado` > `Histórico de Movimentações` | saída de `75,00 L`; saldo passa de `100,00 L` para `25,00 L` |
| Financeiro | safra > `Gestão > Financeiro` | despesa automática de aproximadamente `R$ 8.850,00`, pois o cenário usa custo manual zero; status `PAGO` e origem `OPERACAO_AGRICOLA` |
| Custo agrícola | sidebar `Agricultura > ① Planejamento da Safra > Custeio Agrícola` | custo realizado e custo por hectare recalculados |
| Caderno | safra > `Gestão > Caderno` | evento oficial da pulverização na linha do tempo |

O valor financeiro usa o custo FIFO dos lotes efetivamente consumidos. Portanto, pode diferir do preço do catálogo ou do valor sugerido neste guia quando houver lotes com custos diferentes.

### Como a mão de obra gera custo

Mão de obra gera custo, mas a seleção do operador não define esse valor automaticamente. Na operação agrícola, os campos têm efeitos diferentes:

| Campo/ação | Efeito |
|---|---|
| `Operador` | identifica quem executou o trabalho e melhora a rastreabilidade; sozinho não calcula horas, diária, salário nem encargo |
| `Custo Total (R$)` | informa o componente manual da operação, que pode representar mão de obra, serviço contratado, combustível ou outro custo ainda não integrado |
| `Adicionar` insumo | calcula o consumo pela dose e área e acrescenta ao custo o valor FIFO dos lotes consumidos |
| `Registrar nesta Safra` com status `REALIZADA` | soma `custo manual + custo FIFO dos insumos`, atualiza o custo realizado e cria uma única despesa financeira pelo total da operação |
| Concluir tarefa no Campo PWA | retorna execução e evidências, mas não calcula nem lança mão de obra automaticamente |

#### Exemplo com mão de obra na pulverização

Se a pulverização do cenário integrado tiver `R$ 1.200,00` de mão de obra:

| Componente | Valor |
|---|---:|
| Mão de obra informada em `Custo Total (R$)` | R$ 1.200,00 |
| Fungicida consumido por FIFO | R$ 8.850,00 |
| Custo total da operação | R$ 10.050,00 |
| Despesa financeira automática | R$ 10.050,00 |

Para testar somente a integração do insumo, mantenha `Custo Total (R$)` em `R$ 0,00`, como no cenário anterior. Para testar a composição completa da operação, informe nesse campo o valor da mão de obra antes de clicar em `Registrar nesta Safra`.

> **Limite atual:** a operação não possui campos próprios de quantidade de trabalhadores, horas, valor/hora ou encargos. Portanto, o valor de mão de obra precisa ser previamente calculado e informado como custo manual. Se a mão de obra já tiver sido lançada por outro fluxo financeiro/RH, não repita o valor na operação sem verificar a regra de apropriação, para evitar duplicidade.

## Etapa 1 — Criar a safra de café

### Caminho no sidebar

`Agricultura > Visão Geral > Safras`

Rota direta:

- `/agricola/safras`

### Objetivo da etapa

Criar a safra `2025/26` de café e vincular os talhões `Café A1`, `Café A2` e `Café B1`, totalizando `75,00 ha`.

Ao final desta etapa, a safra deve existir na listagem, deve abrir o painel próprio da safra e deve estar pronta para receber orçamento, operações, monitoramento e colheita.

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Abrir o cadastro | sidebar `Agricultura > Visão Geral > Safras` > botão `Nova Safra` | abre o dialog `Nova Safra`; ainda não cria nenhum registro |
| Vincular outro talhão | dialog `Nova Safra` > botão `Talhão` | adiciona outra linha de ocupação para selecionar o talhão e a área; o vínculo só é persistido ao criar a safra |
| Criar a safra | dialog `Nova Safra` > botão `Criar Safra` | cria o ciclo em `PLANEJADA`, vincula os talhões informados e habilita a navegação interna da safra |
| Abrir a safra | lista `Safras` > card da safra `2025/26` | abre `Resumo > Visão Geral`; não altera dados nem a fase |

### Passo a passo para um usuário leigo

1. Abra a aplicação e confirme que está logado no produtor correto.
2. No menu lateral esquerdo, clique em `Agricultura`.
3. Dentro de `Agricultura`, localize o grupo `Visão Geral`.
4. Clique em `Safras`.
5. Confira se a tela abriu com o título `Safras`.
6. Se aparecer uma lista de safras, verifique se já existe uma safra `2025/26`. Se ela já existir, não crie outra com o mesmo ano agrícola para o mesmo contexto de teste.
7. Clique no botão `Nova Safra`.
8. Aguarde abrir o dialog chamado `Nova Safra`.
9. No campo `Ano Agrícola`, digite `2025/26`.
10. Na seção `Cultivos`, preencha o primeiro cultivo.
11. No campo `Cultura`, selecione `Café`.
12. No campo `Cultivar`, digite `Catuaí 144`.
13. Clique no botão `Talhão`.
14. No campo `Talhão`, selecione `Café A1`.
15. No campo `Plantar (ha)`, informe `20,00`.
16. Clique novamente no botão `Talhão`.
17. Selecione `Café A2`.
18. No campo `Plantar (ha)`, informe `25,00`.
19. Clique novamente no botão `Talhão`.
20. Selecione `Café B1`.
21. No campo `Plantar (ha)`, informe `30,00`.
22. No campo `Meta de Produtividade`, informe `42,00`.
23. Não marque `Consorciado`, porque este cenário usa somente café ocupando os talhões.
24. No campo `Início da ocupação`, informe `2025-07-15`.
25. No campo `Fim da ocupação`, informe `2026-06-10`.
26. Revise os dados antes de salvar.
27. Clique em `Criar Safra`.
28. Aguarde a mensagem de sucesso.
29. Confirme que a safra `2025/26` aparece na listagem de `Safras`.
30. Clique no card da safra para abrir o painel da safra.
31. Confirme que a navegação interna da safra aparece no topo com os grupos `Resumo`, `Planejamento`, `Execução`, `Monitoramento`, `Colheita` e `Gestão`.

### Dados que devem ser preenchidos

#### Identificação da safra

| Campo na tela | Valor a usar | Observação |
|---|---|---|
| Ano Agrícola | `2025/26` | o campo aceita o formato `AAAA` ou `AAAA/AA` |

#### Cultivo

| Campo na tela | Valor a usar | Observação |
|---|---|---|
| Cultura | `Café` | vem do cadastro `Agricultura > ① Planejamento da Safra > Culturas e Variedades` |
| Cultivar | `Catuaí 144` | campo opcional, mas deve ser preenchido neste teste |
| Meta de Produtividade | `42,00` | unidade esperada: sacas por hectare |
| Consorciado | desmarcado | marcar somente quando houver duas culturas compartilhando a mesma área |
| Início da ocupação | `2025-07-15` | início operacional da safra |
| Fim da ocupação | `2026-06-10` | data prevista para encerramento/colheita |

#### Talhões

| Talhão | Plantar (ha) | Observação |
|---|---:|---|
| Café A1 | `20,00` | produção adulta |
| Café A2 | `25,00` | produção intermediária |
| Café B1 | `30,00` | produção adulta |
| Total | `75,00` | soma usada no planejamento e indicadores |

### Conferência depois de salvar

Depois de clicar em `Criar Safra`, confira:

- a safra aparece na lista com o ano `2025/26`
- o card mostra a cultura `Café` ou `Multi-cultivo`, dependendo da forma como a API retorna o resumo
- o status inicial aparece como `Planejada`
- ao clicar no card, a rota muda para `/agricola/safras/{id}`
- a navegação interna da safra é exibida no topo da página
- em `Planejamento > Unidades`, os talhões vinculados aparecem como unidades da safra

### Erros comuns e como corrigir

| Sintoma | Causa provável | Correção |
|---|---|---|
| Campo `Cultura` aparece vazio | cultura ainda não cadastrada | ir em `Agricultura > ① Planejamento da Safra > Culturas e Variedades` e cadastrar `Café` |
| Lista de `Talhão` aparece vazia | talhões não estão cadastrados como tipo `TALHAO` | ir em `Cadastros > Minha Propriedade > Georreferenciamento` e revisar o tipo dos talhões |
| Área do talhão não preenche automaticamente | talhão está sem área cadastrada | editar o talhão e preencher `area_hectares` |
| Sistema não deixa salvar | algum campo obrigatório ficou vazio | revisar `Ano Agrícola`, `Cultura`, ao menos um `Talhão`, `Plantar (ha)` e `Início da ocupação` |
| Área informada é recusada | valor maior que a área cadastrada do talhão | informar uma área igual ou menor que a área real do talhão |
| Safra duplicada na lista | usuário criou mais de uma safra para o mesmo ano | manter somente a safra correta para o teste, se a regra operacional permitir exclusão ou inativação |

### Resultado esperado

- safra criada com status `PLANEJADA`
- safra visível na listagem e na visão global do módulo agrícola
- safra aberta com subnav própria em `/agricola/safras/{id}`
- talhões `Café A1`, `Café A2` e `Café B1` vinculados à safra
- área total da safra igual a `75,00 ha`

## Etapa 2 — Planejamento e orçamento do café

### Onde testar

- sidebar `Agricultura > ① Planejamento da Safra > Orçamento de Safra`, para a visão global (`/agricola/planejamento`)
- dentro da safra, subnav `Planejamento > Orçamento` (`/agricola/safras/{id}/orcamento`)

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Incluir um custo previsto | `Planejamento > Orçamento` > botão `Adicionar item` | abre o dialog `Novo item`; ainda não altera o orçamento |
| Gravar o item | dialog `Novo item` > botão `Salvar` | inclui o item no custeio previsto e recalcula custo previsto, receita esperada, margem bruta e ponto de equilíbrio |
| Corrigir um item | ação de edição na linha do item > dialog `Editar item` > botão `Salvar` | substitui os valores planejados e recalcula os indicadores; não cria uma operação realizada |

Repita `Adicionar item > Salvar` para cada linha da tabela abaixo. Esta etapa registra previsão. O custo realizado nasce das operações registradas na Etapa 3 em diante.

O item `MAO_DE_OBRA` abaixo pertence somente ao orçamento previsto. Para virar custo realizado, a mão de obra deve ser informada no campo `Custo Total (R$)` de uma operação `REALIZADA` ou chegar por um fluxo financeiro/RH integrado. Criar o item orçamentário não gera despesa nem pagamento.

### Itens sugeridos

| Categoria | Item | Quantidade | Unidade | Valor unitário | Valor total |
|---|---|---:|---|---:|---:|
| FERTILIZANTE | Ureia 45% | 22.500 | kg | R$ 3,20 | R$ 72.000,00 |
| FERTILIZANTE | KCl | 11.250 | kg | R$ 3,55 | R$ 39.937,50 |
| FERTILIZANTE | Superfosfato simples | 6.000 | kg | R$ 2,90 | R$ 17.400,00 |
| DEFENSIVO | Fungicida para ferrugem | 225 | L | R$ 118,00 | R$ 26.550,00 |
| DEFENSIVO | Inseticida broca do café | 150 | L | R$ 135,00 | R$ 20.250,00 |
| DEFENSIVO | Herbicida pós-emergente | 180 | L | R$ 37,00 | R$ 6.660,00 |
| MAO_DE_OBRA | Colheita manual e manejo | 1 | lote | R$ 280.000,00 | R$ 280.000,00 |

Total sugerido:

- `R$ 462.797,50`

### Resultado esperado

- custo total previsto exibido
- receita esperada e margem projetada calculadas
- ponto de equilíbrio exibido
- subnav da safra permanece coerente com a etapa

## Etapa 3 — Preparo e manejo inicial

### Onde testar

- avanço de fase: subnav `Resumo > Visão Geral` (`/agricola/safras/{id}`)
- registro de manejo: subnav `Execução > Execução` (`/agricola/safras/{id}/operacoes`)

### Ação

Avançar a safra para `PREPARO_SOLO`.

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Avançar a fase | `Resumo > Visão Geral` > card da linha do tempo > botão `Próxima Fase` > botão `Avançar para Preparo do Solo` | muda o status da safra para `PREPARO_SOLO` e registra a transição na linha do tempo; pode ser bloqueado por pendências obrigatórias |
| Abrir uma operação | `Execução > Execução` > botão `Nova Operação desta Safra` | abre o formulário já contextualizado na safra; ainda não gera custo nem histórico |
| Vincular insumo | formulário da operação > seção de insumos > botão `Adicionar` | adiciona uma linha de insumo à operação; o efeito só é persistido com o registro da operação |
| Gravar a operação | formulário > botão `Registrar nesta Safra` | cria o evento operacional, compõe o custo realizado e o disponibiliza no financeiro e no caderno da safra |

Repita `Nova Operação desta Safra > Registrar nesta Safra` para cada operação sugerida.

Na coluna `Custo` da tabela abaixo, informe em `Custo Total (R$)` somente a parcela manual da operação, como mão de obra ou serviço. Não some novamente o custo dos produtos adicionados na seção `Insumos Aplicados`, pois o sistema acrescenta esses valores automaticamente pelo consumo FIFO.

### Operações sugeridas

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| CALAGEM | 2025-07-20 | A1 | 20,00 ha | R$ 6.200,00 |
| ADUBACAO | 2025-08-01 | A2 | 25,00 ha | R$ 10.500,00 |
| ROÇAGEM | 2025-08-08 | B1 | 30,00 ha | R$ 5.700,00 |

### Resultado esperado

- operações aceitas e listadas
- custos refletidos no financeiro da safra
- registros refletidos no caderno

## Etapa 4 — Plantio/manutenção do café

### Observação

Em café adulto, a fase `PLANTIO` representa manejo estrutural da lavoura, não necessariamente implantação de mudas.

### Ação

Avançar para `PLANTIO` e registrar:

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Avançar a fase | `Resumo > Visão Geral` > `Próxima Fase` > `Avançar para Plantio` | muda o status para `PLANTIO` e registra a transição; não cria uma operação de plantio automaticamente |
| Registrar poda ou adubação | `Execução > Execução` > `Nova Operação desta Safra` > `Registrar nesta Safra` | adiciona o manejo à timeline operacional e incorpora seu custo ao realizado da safra |

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| PODA | 2025-08-20 | A1 | 20,00 ha | R$ 7.800,00 |
| ADUBACAO | 2025-09-02 | B1 | 30,00 ha | R$ 12.600,00 |

### Resultado esperado

- safra evolui de fase corretamente
- timeline operacional registra o manejo

## Etapa 5 — Fenologia do café

### Onde testar

- subnav `Monitoramento > Fenologia` (`/agricola/safras/{id}/fenologia`)

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Abrir o registro | aba `Registros por Talhão` > botão `Registrar Estágio` | abre o dialog `Registrar Estágio Fenológico`; ainda não altera o estágio observado |
| Gravar o estágio | dialog > botão `Registrar Estágio` | cria uma observação fenológica para o talhão e atualiza a visão de fenologia atual da safra |

Repita a ação para cada talhão e data da tabela.

### Registros sugeridos

| Data | Talhão | Estágio | Percentual | Observação |
|---|---|---|---:|---|
| 2025-09-18 | A1 | Floração | 85% | Florada uniforme |
| 2025-10-10 | A2 | Pegamento | 78% | Boa formação de frutos |
| 2025-11-12 | B1 | Granação | 80% | Desenvolvimento regular |

### Resultado esperado

- registros carregados na listagem
- visão de fenologia atual atualizada

## Etapa 6 — Monitoramento fitossanitário

### Onde testar

- subnav `Monitoramento > Sanidade` (`/agricola/safras/{id}/monitoramento`)

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Abrir o apontamento | botão `Registrar` | abre o dialog `Novo Registro de Monitoramento`; ainda não gera alerta |
| Gravar o apontamento | dialog > botão `Salvar` | persiste agente, severidade e nível para o talhão; o risco passa a compor a listagem e pode repercutir no dashboard e no caderno |

O monitoramento registra a constatação de campo. Ele não cria automaticamente uma pulverização; quando houver tratamento, registre-o em `Execução > Execução`.

### Registros sugeridos

| Data | Talhão | Agente | Severidade | Nível | Observação |
|---|---|---|---|---:|---|
| 2025-10-22 | A1 | Ferrugem | AVISO | 2 | Início de incidência |
| 2025-11-05 | A2 | Broca do café | CRITICO | 4 | Ação imediata recomendada |

### Resultado esperado

- alertas e registros persistidos
- caderno e dashboard podem refletir risco operacional

### Como a IA pode ajudar aqui

- interpretar gravidade de ferrugem, broca ou desuniformidade
- sugerir priorização de manejo
- contextualizar o risco com a fase da lavoura

## Etapa 7 — Operações de desenvolvimento

### Onde testar

- avanço de fase: subnav `Resumo > Visão Geral`
- operações: subnav `Execução > Execução` (`/agricola/safras/{id}/operacoes`)

### Ação

Avançar a safra para `DESENVOLVIMENTO` e registrar:

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Avançar a fase | `Resumo > Visão Geral` > `Próxima Fase` > `Avançar para Desenvolvimento` | muda o status para `DESENVOLVIMENTO` e registra a transição da safra |
| Registrar adubação ou pulverização | `Execução > Execução` > `Nova Operação desta Safra` > `Registrar nesta Safra` | cria a operação, aumenta o custo realizado e atualiza os históricos financeiro e de campo |

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| PULVERIZACAO | 2025-11-06 | A2 | 25,00 ha | R$ 5.400,00 |
| ADUBACAO | 2025-12-01 | A1 | 20,00 ha | R$ 7.200,00 |
| PULVERIZACAO | 2025-12-15 | B1 | 30,00 ha | R$ 6.900,00 |

### Resultado esperado

- custo acumulado cresce
- operações ficam visíveis no financeiro e caderno

## Etapa 8 — Caderno de campo

### Onde testar

- subnav `Gestão > Caderno` (`/agricola/safras/{id}/caderno`)

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Criar anotação ou monitoramento manual | botão `Novo Registro` > dialog `Novo Registro no Caderno` > botão `Registrar` | adiciona uma entrada manual à linha do tempo, sem criar operação ou custo agrícola |
| Registrar visita técnica | botão `Registrar Visita` > botão `Registrar Visita` no dialog | adiciona a visita e seus dados técnicos ao histórico da safra |
| Registrar entrega de EPI | botão `Registrar Entrega` > botão `Registrar Entrega` no dialog | registra a entrega para rastreabilidade e auditoria; não movimenta estoque de insumos |
| Gerar documento | botão `Exportar oficial` ou `Exportar auditoria` | gera a versão correspondente do caderno; não modifica os registros de origem e pode exigir plano `ENTERPRISE` |

### Entradas manuais sugeridas

| Tipo | Data | Conteúdo |
|---|---|---|
| VISITA_TECNICA | 2025-11-06 | Reforço de controle da broca no A2 |
| MONITORAMENTO | 2025-11-20 | Florada tardia pontual no B1 |
| ENTREGA | 2025-12-02 | Recebimento de 100 L de fungicida |

### Resultado esperado

- linha do tempo consolidada
- exportação do caderno funcionando

## Etapa 9 — Colheita

### Onde testar

- avanço de fase: subnav `Resumo > Visão Geral`
- romaneios: subnav `Colheita > Romaneios` (`/agricola/safras/{id}/romaneios`)

### Ação

Avançar a safra para `COLHEITA`.

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Avançar a fase | `Resumo > Visão Geral` > `Próxima Fase` > `Avançar para Colheita` | muda o status para `COLHEITA` e registra a transição; não lança produção automaticamente |
| Abrir um romaneio | `Colheita > Romaneios` > botão `Novo Romaneio` | abre o dialog `Novo Romaneio de Colheita`; ainda não altera produção ou receita |
| Gravar um romaneio | dialog > botão `Registrar Romaneio` | registra a produção do talhão e recalcula produção, produtividade e receita dos KPIs da colheita |

Repita `Novo Romaneio > Registrar Romaneio` para A1, A2 e B1. A exclusão posterior do romaneio não remove automaticamente uma receita financeira já associada; essa conciliação deve ser revisada manualmente.

### Romaneios sugeridos

| Data | Talhão | Quantidade | Unidade | Sacas 60 kg | Preço por saca | Receita total |
|---|---|---:|---|---:|---:|---:|
| 2026-05-28 | A1 | 760 | sc | 760 | R$ 1.080,00 | R$ 820.800,00 |
| 2026-06-02 | A2 | 980 | sc | 980 | R$ 1.040,00 | R$ 1.019.200,00 |
| 2026-06-07 | B1 | 1.180 | sc | 1.180 | R$ 1.060,00 | R$ 1.250.800,00 |

Totais sugeridos:

- produção total: `2.920 sc`
- produtividade média: `38,93 sc/ha`
- receita total: `R$ 3.090.800,00`

### Resultado esperado

- romaneios persistidos
- receita refletida no financeiro
- produção e produtividade recalculadas

## Etapa 10 — Beneficiamento do café

### Onde testar

- subnav `Colheita > Beneficiamento` (`/agricola/safras/{id}/beneficiamento`), disponível a partir do plano `PROFISSIONAL`

### Ação

Criar 1 lote de beneficiamento.

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Abrir o lote | botão `Novo Lote` | abre o dialog `Novo Lote de Beneficiamento`; ainda não consome nem transforma a origem |
| Gravar o lote | dialog > botão `Registrar` | cria o lote, vincula as origens selecionadas e calcula saída líquida/rendimento a partir da entrada e das perdas informadas |
| Atualizar o processamento | ação de edição do lote > dialog `Atualizar Lote` > botão `Salvar` | atualiza dados e status do lote, preservando sua rastreabilidade com a origem |

### Dados sugeridos

| Campo | Valor |
|---|---|
| Lote | CAFE-BEN-2026-001 |
| Origem | Romaneios A1 + A2 + B1 |
| Entrada bruta | 2.920 sc |
| Quebra/perda | 5,2% |
| Saída líquida | 2.768,16 sc |
| Observação | Secagem + limpeza + classificação |

### Resultado esperado

- rastreabilidade lote-origem preservada
- perda registrada
- lote final disponível para análise

### Como a IA pode ajudar aqui

- explicar se a perda do beneficiamento está dentro do esperado
- relacionar resultado final com qualidade da entrada e do processo
- facilitar leitura gerencial da eficiência do lote

## Etapa 11 — Financeiro da safra

### Onde testar

- subnav `Gestão > Financeiro` (`/agricola/safras/{id}/financeiro`)

### Ações, botões e efeitos

Esta tela é de consolidação e conferência. Não há botão para criar custos agrícolas nela.

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Consultar o consolidado | `Gestão > Financeiro` | carrega custos das operações e receitas relacionadas à colheita para calcular resultado e ROI; não cria lançamentos |
| Corrigir custo operacional | voltar a `Execução > Execução` > editar a operação > `Salvar Ajustes` | atualiza a operação de origem e, após recarregar os dados, seus reflexos financeiros |
| Corrigir produção ou preço | voltar a `Colheita > Romaneios` > ação de edição do romaneio | altera a origem do indicador; exclusões exigem atenção à conciliação financeira associada |

### Custos operacionais sugeridos neste fluxo

- R$ 6.200,00
- R$ 10.500,00
- R$ 5.700,00
- R$ 7.800,00
- R$ 12.600,00
- R$ 5.400,00
- R$ 7.200,00
- R$ 6.900,00

Subtotal:

- `R$ 62.300,00`

### Resultado esperado

- total de operações maior que zero
- total de romaneios igual a 3
- receita total muito superior à despesa total
- ROI positivo

## Etapa 12 — Cenário econômico do café

### Onde testar

- subnav `Planejamento > Cenários` (`/agricola/safras/{id}/cenarios`), disponível a partir do plano `PROFISSIONAL`

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Abrir uma simulação | botão `Novo Cenário` | abre o dialog `Novo Cenário Econômico`; ainda não calcula nem salva um cenário |
| Gravar a simulação | dialog > botão `Criar Cenário` | cria o cenário e calcula seus indicadores com as premissas informadas |
| Recalcular | ação `Recalcular` no card do cenário | refaz os indicadores com os dados atuais do cenário e das unidades vinculadas |

Na interface, os tipos criáveis são `OTIMISTA`, `PESSIMISTA` e `CUSTOM` (`Personalizado`). Para representar o cenário base deste teste, use `CUSTOM` e mantenha no nome `Cenário Base Café 2025/26`.

### Cenário base sugerido

| Campo | Valor |
|---|---|
| Nome | Cenário Base Café 2025/26 |
| Tipo | BASE |
| Produtividade default | 38,93 sc/ha |
| Preço default | R$ 1.058,49 |
| Custo ha default | R$ 830,67 |
| IR alíquota | 15,00% |

### Unidades produtivas sugeridas

| Unidade | Área | Produtividade | Preço | Custo/ha |
|---|---:|---:|---:|---:|
| A1 | 20,00 ha | 38,00 sc/ha | R$ 1.080,00 | R$ 810,00 |
| A2 | 25,00 ha | 39,20 sc/ha | R$ 1.040,00 | R$ 840,00 |
| B1 | 30,00 ha | 39,33 sc/ha | R$ 1.060,00 | R$ 842,00 |

### Resultado esperado

- receita, custo, margem e resultado líquido calculados
- dashboard executivo consome o cenário

### Como a IA pode ajudar aqui

- explicar se a safra está saudável financeiramente
- apontar quais unidades sustentam ou pressionam a margem
- resumir impacto de preço, produtividade, depreciação e IR

## Etapa 13 — Comparativo de cenários do café

### Cenários alternativos sugeridos

#### Otimista

- produtividade `+6%`
- preço `+4%`
- custo `+2%`

#### Pessimista

- produtividade `-9%`
- preço `-7%`
- custo `+6%`

### Onde testar

- subnav `Planejamento > Cenários` (`/agricola/safras/{id}/cenarios`)

### Ações, botões e efeitos

| Ação | Onde clicar | O que causa no processo |
|---|---|---|
| Selecionar cenários | caixas de seleção à esquerda dos cards | prepara a seleção para comparação; não recalcula nem altera os cenários |
| Abrir o comparativo | selecionar ao menos 2 cenários > botão `Comparar (N)` | abre `/agricola/safras/{id}/cenarios/comparativo` com os cenários selecionados e apresenta os indicadores lado a lado |
| Exportar PDF | botão `Exportar PDF` | atualmente não causa efeito, pois o controle está desabilitado e marcado como disponível em breve |

### Resultado esperado

- comparativo carrega sem erro
- depreciação, IR e resultado líquido aparecem por cenário
- cenário otimista lidera em resultado líquido
- cenário pessimista apresenta pior margem

### Como a IA pode ajudar aqui

- transformar o comparativo em recomendação de decisão
- destacar o cenário com melhor equilíbrio entre risco e retorno
- simplificar a comunicação da análise para o gestor e para o técnico

## Critérios de aceite

- safra de café concluída do planejamento à colheita
- tarefa programada no web recebida no Campo PWA após sincronização
- tarefa iniciada e concluída offline retorna ao web com status, horários e evidências após o push
- tela de sincronização termina com `Na fila: 0` e `Com erro: 0`
- operação `REALIZADA` com insumo gera saída de estoque e reduz o saldo pela quantidade calculada
- operação `REALIZADA` com custo gera uma única despesa financeira rastreável à origem `OPERACAO_AGRICOLA`
- falha na integração não deixa operação, estoque ou financeiro parcialmente gravados
- fenologia e monitoramento refletidos no fluxo
- romaneios e beneficiamento preservam rastreabilidade
- financeiro consolida custos e receitas
- cenários e comparativo operam sem falha
- dashboards mostram dados coerentes
- sempre que houver IA, a funcionalidade deve destacar seu uso e explicar claramente como ela ajuda a decisão

## Matriz Final

| Tela | Dado esperado | Regra validada |
|---|---|---|
| `/agricola/safras` | safra `Café 2025/26` criada e listada | cadastro de safra perene com talhões válidos |
| `/agricola/dashboard` | visão global do módulo agrícola com a safra de café em acompanhamento | dashboard global reflete fase atual |
| `/agricola/planejamento` | planejamento macro disponível | entrada global do planejamento |
| `/agricola/safras/{id}/orcamento` | orçamento cafeeiro consolidado | cálculo previsto da safra |
| `/agricola/operacoes` | operações consolidadas disponíveis | visão global do histórico operacional |
| `/agricola/safras/{id}/operacoes` | manejo de calagem, adubação, poda e pulverização listado | coerência entre operação e fase da safra |
| `/dashboard/operacional/campo/tarefas` | tarefa concluída com horários, observações e imagens retornadas pelo aplicativo | sincronização da execução de campo com o backoffice |
| aplicativo Campo `/sync` | fila zerada e nenhuma falha pendente | push e pull concluídos com sucesso |
| `/agricola/safras/{id}/estoque` | saída FIFO vinculada à execução da operação | consumo automático do insumo realizado |
| `/suprimentos/estoque` | histórico de saída e saldo final do fungicida em `25,00 L` | consistência entre ledger e saldo global |
| `/agricola/safras/{id}/fenologia` | registros de floração, pegamento e granação | leitura fenológica da cultura café |
| `/agricola/safras/{id}/monitoramento` | ferrugem e broca registradas | monitoramento fitossanitário por talhão |
| `/agricola/safras/{id}/monitoramento` | quando houver IA, interpretação clara de risco e ação | apoio técnico assistido por IA |
| `/agricola/safras/{id}/caderno` | timeline com visitas, monitoramentos e entregas | consolidação do histórico da safra |
| `/agricola/safras/{id}/romaneios` | romaneios com produção, preço e receita | registro da colheita por lote |
| `/agricola/safras/{id}/beneficiamento` | lote beneficiado com quebra de peso | rastreabilidade pós-colheita |
| `/agricola/safras/{id}/beneficiamento` | quando houver IA, leitura da perda e da qualidade do lote | apoio de IA na pós-colheita |
| `/agricola/safras/{id}/financeiro` | custos, receitas e ROI positivos | integração agrícola-financeira do café |
| `/agricola/safras/{id}/financeiro` | despesa da pulverização com origem `OPERACAO_AGRICOLA` | rastreabilidade financeira sem duplicidade |
| `/agricola/safras/{id}/cenarios` | cenário base e alternativos calculados | modelagem econômica da safra cafeeira |
| `/agricola/safras/{id}/cenarios` | quando houver IA, explicação útil do risco econômico | apoio de IA na análise cafeeira |
| `/agricola/safras/{id}/cenarios/comparativo` | comparação entre base, otimista e pessimista | consistência do comparativo econômico |
| `/agricola/safras/{id}/dashboard` | visão executiva com alertas e comparativos | consolidação operacional e econômica da safra |
| `/agricola/safras/{id}/dashboard` | quando houver IA, destaque visual e recomendação acionável | apoio executivo assistido por IA |
