# Workflow Completo de Teste — Agricultura Café

## Objetivo

Versão derivada do workflow agrícola focada em café, cobrindo o ciclo operacional, monitoramento, colheita, beneficiamento e análise econômica de uma safra cafeeira.

Documento base relacionado:

- [workflow-atricultura.md](/opt/lampp/htdocs/farm/docs/guias/workflow-atricultura.md)

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
- tenant: 1 tenant ativo e isolado
- perfil mínimo:
  - criar e editar safra
  - registrar operações
  - registrar fenologia
  - registrar monitoramento
  - registrar romaneios
  - acessar financeiro e cenários

## Pré-requisitos

- fazenda e talhões cafeeiros cadastrados
- usuário autenticado no tenant correto
- planos de conta de despesa e receita ativos
- produtos e insumos cadastrados
- estoque inicial carregado, se aplicável

### Checklist antes de criar a safra

Antes de clicar em `Nova Safra`, confirme estes cadastros. Sem eles, o usuário até pode abrir a tela de safras, mas terá dificuldade para vincular talhões, selecionar cultura ou executar o restante do workflow.

| Verificação | Caminho no sidebar | O que conferir |
|---|---|---|
| Tenant correto | seletor de empresa/fazenda no topo da aplicação | a operação deve estar no tenant da fazenda que será usada no teste |
| Fazenda cadastrada | `Cadastros > Minha Propriedade > Propriedades` | existe uma propriedade chamada `Fazenda Boa Esperança` |
| Talhões cadastrados | `Cadastros > Minha Propriedade > Georreferenciamento` | existem os talhões `Café A1`, `Café A2` e `Café B1`, todos como tipo `TALHAO` |
| Área dos talhões | `Cadastros > Minha Propriedade > Georreferenciamento` | A1 tem `20,00 ha`, A2 tem `25,00 ha` e B1 tem `30,00 ha` |
| Cultura cadastrada | `Agricultura > ① Planejamento da Safra > Culturas e Variedades` | existe a cultura `Café`; se houver variedade, usar `Catuaí 144` |
| Produtos cadastrados | `Cadastros > Insumos & Ativos > Catálogo de Produtos` | existem fertilizantes, defensivos e demais insumos que serão usados no planejamento |
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
- transforme leitura técnica em decisão prática para produtor, gestor ou agrônomo

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

## Etapa 1 — Criar a safra de café

### Caminho no sidebar

`Agricultura > Visão Geral > Safras`

Rota direta:

- `/agricola/safras`

### Objetivo da etapa

Criar a safra `2025/26` de café e vincular os talhões `Café A1`, `Café A2` e `Café B1`, totalizando `75,00 ha`.

Ao final desta etapa, a safra deve existir na listagem, deve abrir o painel próprio da safra e deve estar pronta para receber orçamento, operações, monitoramento e colheita.

### Passo a passo para um usuário leigo

1. Abra a aplicação e confirme que está logado no tenant correto.
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
- safra visível na listagem e no dashboard agrícola
- safra aberta com subnav própria em `/agricola/safras/{id}`
- talhões `Café A1`, `Café A2` e `Café B1` vinculados à safra
- área total da safra igual a `75,00 ha`

## Etapa 2 — Planejamento e orçamento do café

### Onde testar

- `/agricola/planejamento`
- `/agricola/safras/{id}/orcamento`

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

- `/agricola/safras/{id}/operacoes`

### Ação

Avançar a safra para `PREPARO_SOLO`.

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

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| PODA | 2025-08-20 | A1 | 20,00 ha | R$ 7.800,00 |
| ADUBACAO | 2025-09-02 | B1 | 30,00 ha | R$ 12.600,00 |

### Resultado esperado

- safra evolui de fase corretamente
- timeline operacional registra o manejo

## Etapa 5 — Fenologia do café

### Onde testar

- `/agricola/safras/{id}/fenologia`

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

- `/agricola/safras/{id}/monitoramento`

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

- `/agricola/safras/{id}/operacoes`

### Ação

Avançar a safra para `DESENVOLVIMENTO` e registrar:

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

- `/agricola/safras/{id}/caderno`

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

### Ação

Avançar a safra para `COLHEITA`.

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

- `/agricola/safras/{id}/beneficiamento`

### Ação

Criar 1 lote de beneficiamento.

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

- `/agricola/safras/{id}/financeiro`

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

- `/agricola/safras/{id}/cenarios`

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

- `/agricola/safras/{id}/cenarios/comparativo`

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
- fenologia e monitoramento refletidos no fluxo
- romaneios e beneficiamento preservam rastreabilidade
- financeiro consolida custos e receitas
- cenários e comparativo operam sem falha
- dashboards mostram dados coerentes
- sempre que houver IA, a funcionalidade destacar seu uso e explicar claramente como ela ajuda a decisão

## Matriz Final

| Tela | Dado esperado | Regra validada |
|---|---|---|
| `/agricola/safras` | safra `Café 2025/26` criada e listada | cadastro de safra perene com talhões válidos |
| `/agricola/dashboard` | safra de café no acompanhamento | dashboard global reflete fase atual |
| `/agricola/planejamento` | planejamento macro disponível | entrada global do planejamento |
| `/agricola/safras/{id}/orcamento` | orçamento cafeeiro consolidado | cálculo previsto da safra |
| `/agricola/operacoes` | operações consolidadas disponíveis | visão global do histórico operacional |
| `/agricola/safras/{id}/operacoes` | manejo de calagem, adubação, poda e pulverização listado | coerência entre operação e fase da safra |
| `/agricola/safras/{id}/fenologia` | registros de floração, pegamento e granação | leitura fenológica da cultura café |
| `/agricola/safras/{id}/monitoramento` | ferrugem e broca registradas | monitoramento fitossanitário por talhão |
| `/agricola/safras/{id}/monitoramento` | quando houver IA, interpretação clara de risco e ação | apoio técnico assistido por IA |
| `/agricola/safras/{id}/caderno` | timeline com visitas, monitoramentos e entregas | consolidação do histórico da safra |
| `/agricola/safras/{id}/romaneios` | romaneios com produção, preço e receita | registro da colheita por lote |
| `/agricola/safras/{id}/beneficiamento` | lote beneficiado com quebra de peso | rastreabilidade pós-colheita |
| `/agricola/safras/{id}/beneficiamento` | quando houver IA, leitura da perda e da qualidade do lote | apoio de IA na pós-colheita |
| `/agricola/safras/{id}/financeiro` | custos, receitas e ROI positivos | integração agrícola-financeira do café |
| `/agricola/safras/{id}/cenarios` | cenário base e alternativos calculados | modelagem econômica da safra cafeeira |
| `/agricola/safras/{id}/cenarios` | quando houver IA, explicação útil do risco econômico | apoio de IA na análise cafeeira |
| `/agricola/safras/{id}/cenarios/comparativo` | comparação entre base, otimista e pessimista | consistência do comparativo econômico |
| `/agricola/safras/{id}/dashboard` | visão executiva com alertas e comparativos | consolidação operacional e econômica da safra |
| `/agricola/safras/{id}/dashboard` | quando houver IA, destaque visual e recomendação acionável | apoio executivo assistido por IA |
