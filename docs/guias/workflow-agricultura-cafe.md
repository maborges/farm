# Workflow Completo de Teste — Agricultura Café

## Objetivo

Versão derivada do workflow agrícola focada em café, cobrindo o ciclo operacional, monitoramento, colheita, beneficiamento e análise econômica de uma safra cafeeira.

Documento base relacionado:

- [workflow-atricultura.md](/opt/lampp/htdocs/farm/docs/guias/workflow-atricultura.md)

## Capturas de referência

### Dashboard Agrícola

![Dashboard Agrícola](./assets/agricola-dashboard.png)

### Planejamento

![Planejamento](./assets/agricola-planejamento.png)

## Escopo do teste

O workflow cobre:

- criação da safra de café
- orçamento
- manejo por fase
- fenologia
- monitoramento fitossanitário
- caderno de campo
- romaneios
- beneficiamento
- financeiro
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

### Onde testar

- `/agricola/safras`

### Ação

Criar a safra `Café 2025/26` vinculando A1, A2 e B1.

### Resultado esperado

- safra criada com status `PLANEJADA`
- safra visível na listagem e no dashboard agrícola

## Etapa 2 — Planejamento e orçamento do café

### Onde testar

- `/agricola/planejamento`

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

## Etapa 3 — Preparo e manejo inicial

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

- `/agricola/fenologia`

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

- `/agricola/monitoramento`

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

- `/agricola/beneficiamento`

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
| `/agricola/planejamento` | orçamento cafeeiro consolidado | cálculo previsto da safra |
| `/agricola/operacoes` | manejo de calagem, adubação, poda e pulverização listado | coerência entre operação e fase da safra |
| `/agricola/fenologia` | registros de floração, pegamento e granação | leitura fenológica da cultura café |
| `/agricola/monitoramento` | ferrugem e broca registradas | monitoramento fitossanitário por talhão |
| `/agricola/monitoramento` | quando houver IA, interpretação clara de risco e ação | apoio técnico assistido por IA |
| `/agricola/safras/{id}/caderno` | timeline com visitas, monitoramentos e entregas | consolidação do histórico da safra |
| `/agricola/romaneios` | romaneios com produção, preço e receita | registro da colheita por lote |
| `/agricola/beneficiamento` | lote beneficiado com quebra de peso | rastreabilidade pós-colheita |
| `/agricola/beneficiamento` | quando houver IA, leitura da perda e da qualidade do lote | apoio de IA na pós-colheita |
| `/agricola/safras/{id}/financeiro` | custos, receitas e ROI positivos | integração agrícola-financeira do café |
| `/agricola/safras/{id}/cenarios` | cenário base e alternativos calculados | modelagem econômica da safra cafeeira |
| `/agricola/safras/{id}/cenarios` | quando houver IA, explicação útil do risco econômico | apoio de IA na análise cafeeira |
| `/agricola/safras/{id}/cenarios/comparativo` | comparação entre base, otimista e pessimista | consistência do comparativo econômico |
| `/agricola/safras/{id}/dashboard` | visão executiva com alertas e comparativos | consolidação operacional e econômica da safra |
| `/agricola/safras/{id}/dashboard` | quando houver IA, destaque visual e recomendação acionável | apoio executivo assistido por IA |
