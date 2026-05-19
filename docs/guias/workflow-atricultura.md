# Workflow Completo de Teste — Módulo Agricultura

## Objetivo

Este documento define um roteiro completo de validação funcional do módulo Agricultura, do cadastro inicial ao resultado final da safra, com foco em:

- fluxo operacional real
- dados mínimos necessários
- dados recomendados para teste rico
- resultados esperados por etapa
- pontos de integração com financeiro, estoque, monitoramento e cenários

O objetivo é permitir um teste end-to-end reproduzível por QA, produto, suporte ou implantação.

## Modelo de navegação esperado

O módulo Agricultura deve ser testado em 2 níveis:

- navegação global do módulo
- navegação contextual da safra

### Navegação global do módulo

Usar o sidebar global para entrar nas áreas amplas:

- `Visão Geral`
- `Safras`
- `Planejamento da Safra`
- `Execução & Registros`
- `Monitoramento`
- `Colheita & Pós-Colheita`
- `Gestão & Relatórios`

### Navegação contextual da safra

Depois de abrir `/agricola/safras/{id}`, a operação diária deve seguir no subnav da própria safra:

- `Resumo`
- `Planejamento`
- `Execução`
- `Monitoramento`
- `Colheita`
- `Gestão`

Regra prática:

- telas globais servem para visão consolidada, consulta e entrada no módulo
- a execução da safra deve acontecer preferencialmente dentro de `/agricola/safras/{id}/*`

## Escopo do teste

O workflow cobre as áreas visíveis hoje no módulo:

- dashboard agrícola global: `/agricola/dashboard`
- safras: `/agricola/safras`
- orçamento de safra: `/agricola/planejamento`
- operações consolidadas: `/agricola/operacoes`
- monitoramento global: `/agricola/monitoramento`
- romaneios globais: `/agricola/romaneios`
- beneficiamento global: `/agricola/beneficiamento`
- orçamento da safra: `/agricola/safras/{id}/orcamento`
- execução da safra: `/agricola/safras/{id}/operacoes`
- fenologia da safra: `/agricola/safras/{id}/fenologia`
- monitoramento da safra: `/agricola/safras/{id}/monitoramento`
- romaneios da safra: `/agricola/safras/{id}/romaneios`
- beneficiamento da safra: `/agricola/safras/{id}/beneficiamento`
- tarefas da safra: `/agricola/safras/{id}/tarefas`
- checklist da safra: `/agricola/safras/{id}/checklist`
- estoque da safra: `/agricola/safras/{id}/estoque`
- análises de solo da safra: `/agricola/safras/{id}/analises-solo`
- cenários econômicos: `/agricola/safras/{id}/cenarios`
- comparativo de cenários: `/agricola/safras/{id}/cenarios/comparativo`
- caderno de campo: `/agricola/safras/{id}/caderno`
- dashboard executivo da safra: `/agricola/safras/{id}/dashboard`
- financeiro da safra: `/agricola/safras/{id}/financeiro`

## Capturas de referência

### Dashboard Agrícola

![Dashboard Agrícola](./assets/agricola-dashboard.png)

### Safras

![Safras](./assets/agricola-safras.png)

### Planejamento

![Planejamento](./assets/agricola-planejamento.png)

## Persona de teste

- tipo: produtor com apoio técnico
- tenant: 1 tenant ativo e isolado
- perfil mínimo:
  - visualizar dashboard agrícola
  - criar e editar safra
  - criar operações
  - registrar monitoramentos
  - registrar romaneios
  - acessar cenários
  - acessar financeiro

## Estratégia recomendada

Executar o teste com uma safra principal de soja. Esse cenário simplifica o fluxo porque:

- a sequência `PLANEJADA -> PREPARO_SOLO -> PLANTIO -> DESENVOLVIMENTO -> COLHEITA` é intuitiva
- operações como adubação, pulverização e colheita fazem sentido direto
- produtividade em `sc/ha` encaixa naturalmente com romaneio e cenário

## Destaque de IA no fluxo

Quando a IA for usada em uma funcionalidade, isso deve estar explícito para o usuário. No módulo Agricultura, a IA deve aparecer como apoio à decisão com base nos dados da própria safra.

O comportamento esperado da IA é:

- explicar que a análise foi assistida por IA
- mostrar em qual dado da funcionalidade a recomendação se apoia
- orientar a próxima ação prática do usuário
- evitar respostas genéricas sem vínculo com a safra, o talhão ou o cenário

## Massa de dados base

### 1. Fazenda e estrutura física

Cadastrar uma fazenda com duas áreas produtivas:

| Campo | Valor sugerido |
|---|---|
| Fazenda | Fazenda Santa Helena |
| Município | Rio Verde |
| Estado | GO |
| Área total | 120,00 ha |

Criar os talhões:

| Talhão | Área | Uso no teste |
|---|---:|---|
| Talhão A1 | 30,00 ha | Produção principal |
| Talhão A2 | 25,00 ha | Produção principal |
| Talhão B1 | 20,00 ha | Produção complementar |

Área total da safra de teste:

- `75,00 ha`

### 2. Cadastros auxiliares

Garantir que existam:

- 1 agrônomo responsável
- 1 operador de máquina
- 1 fornecedor de insumos
- 1 comprador da produção
- 1 depósito de insumos
- 1 plano de conta de despesa de custeio
- 1 plano de conta de receita operacional

### 3. Produtos e insumos

Cadastrar os produtos abaixo:

| Produto | Tipo | Unidade | Preço unitário sugerido |
|---|---|---|---:|
| Semente Soja TMG 2383 | SEMENTE | kg | R$ 4,80 |
| Ureia 45% | FERTILIZANTE | kg | R$ 3,20 |
| KCl | FERTILIZANTE | kg | R$ 3,50 |
| Glifosato | DEFENSIVO | L | R$ 32,00 |
| Fungicida Triazol | DEFENSIVO | L | R$ 120,00 |
| Diesel S10 | COMBUSTIVEL | L | R$ 6,10 |

### 4. Estoque inicial sugerido

Se o tenant usar estoque, abastecer o depósito com:

| Produto | Quantidade |
|---|---:|
| Semente Soja TMG 2383 | 4.500 kg |
| Ureia 45% | 9.000 kg |
| KCl | 6.000 kg |
| Glifosato | 500 L |
| Fungicida Triazol | 250 L |
| Diesel S10 | 8.000 L |

### 5. Safra principal de teste

Criar 1 safra:

| Campo | Valor |
|---|---|
| Ano agrícola | 2025/26 |
| Cultura | Soja |
| Cultivar | TMG 2383 IPRO |
| Status inicial | PLANEJADA |
| Data prevista de plantio | 2025-10-05 |
| Data prevista de colheita | 2026-02-20 |
| Produtividade meta | 68,00 sc/ha |
| Área plantada | 75,00 ha |

Vincular os talhões:

- Talhão A1: `30,00 ha`
- Talhão A2: `25,00 ha`
- Talhão B1: `20,00 ha`

## Workflow de teste

## Etapa 0 — Pré-check técnico

Antes do teste funcional, validar:

- usuário autenticado
- tenant correto selecionado
- fazenda e talhões disponíveis
- plano de conta de despesa e receita ativos
- produtos e estoque cadastrados

Resultado esperado:

- a criação de safra é permitida
- operações com custo geram despesa
- romaneios com receita geram receita

## Etapa 1 — Criar a safra

### Onde testar

- `/agricola/safras`

### Ação

Criar a safra `Soja 2025/26` com os 3 talhões acima.

### Dados obrigatórios

- ano agrícola
- cultura
- ao menos 1 cultivo/talhão
- área por talhão respeitando a área real

### Validações

- a soma das áreas dos cultivos não pode ultrapassar a área real do talhão
- o cadastro deve aparecer na listagem imediatamente após salvar

### Resultado esperado

- safra criada com status `PLANEJADA`
- card ou linha da safra visível em `/agricola/safras`
- safra aparece no card `Acompanhamento de Safras` do dashboard agrícola

## Etapa 2 — Planejamento e orçamento

### Onde testar

- `/agricola/planejamento`
- `/agricola/safras/{id}/orcamento`

### Ação

Selecionar a safra criada e cadastrar o orçamento de custeio.

### Itens sugeridos

| Categoria | Item | Quantidade | Unidade | Valor unitário | Valor total |
|---|---|---:|---|---:|---:|
| SEMENTE | Semente Soja TMG 2383 | 4.125 | kg | R$ 4,80 | R$ 19.800,00 |
| FERTILIZANTE | Ureia 45% | 6.000 | kg | R$ 3,20 | R$ 19.200,00 |
| FERTILIZANTE | KCl | 3.750 | kg | R$ 3,50 | R$ 13.125,00 |
| DEFENSIVO | Glifosato | 225 | L | R$ 32,00 | R$ 7.200,00 |
| DEFENSIVO | Fungicida Triazol | 112,5 | L | R$ 120,00 | R$ 13.500,00 |
| COMBUSTIVEL | Diesel S10 | 2.000 | L | R$ 6,10 | R$ 12.200,00 |
| MAO_DE_OBRA | Equipe operacional | 1 | lote | R$ 18.000,00 | R$ 18.000,00 |

Total estimado sugerido:

- `R$ 103.025,00`

### Resultado esperado

- KPIs de orçamento carregados
- custo total previsto visível
- margem bruta projetada calculada
- ponto de equilíbrio exibido
- safra continua navegável no subnav contextual

## Etapa 3 — Avançar para preparo do solo

### Onde testar

- detalhe da safra
- dashboard executivo da safra

### Ação

Avançar a safra para `PREPARO_SOLO`.

### Resultado esperado

- status atualizado na safra
- dashboard agrícola move a safra de coluna/fase
- checklist da fase pode refletir a mudança

## Etapa 4 — Registrar operações de preparo

### Onde testar

- `/agricola/operacoes`
- `/agricola/safras/{id}/operacoes`
- `/agricola/safras/{id}/caderno`

### Ações recomendadas

Registrar 2 operações.

#### Operação 1

| Campo | Valor |
|---|---|
| Tipo | CALAGEM |
| Data | 2025-08-20 |
| Safra | Soja 2025/26 |
| Talhão | A1 |
| Área aplicada | 30,00 ha |
| Custo total | R$ 9.000,00 |
| Observação | Correção de solo talhão A1 |

#### Operação 2

| Campo | Valor |
|---|---|
| Tipo | ADUBACAO |
| Data | 2025-09-02 |
| Safra | Soja 2025/26 |
| Talhão | A2 |
| Área aplicada | 25,00 ha |
| Custo total | R$ 11.250,00 |
| Observação | Adubação de base A2 |

### Resultado esperado

- operações aparecem na listagem
- entradas são refletidas no caderno de campo
- despesas financeiras automáticas são criadas se houver integração ativa
- resumo financeiro da safra passa a considerar os custos

## Etapa 5 — Avançar para plantio

### Ação

Avançar a safra para `PLANTIO`.

### Operações sugeridas

Registrar 2 operações adicionais:

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| PLANTIO | 2025-10-05 | A1 | 30,00 ha | R$ 12.500,00 |
| PLANTIO | 2025-10-06 | A2 | 25,00 ha | R$ 10.300,00 |

### Resultado esperado

- a fase da safra passa a permitir operações de plantio
- custo acumulado da safra sobe
- timeline operacional cresce no caderno

## Etapa 6 — Registrar fenologia

### Onde testar

- `/agricola/safras/{id}/fenologia`

### Ação

Criar registros fenológicos para a safra.

### Registros sugeridos

| Data | Talhão | Estágio | Percentual da área | Observação |
|---|---|---|---:|---|
| 2025-10-25 | A1 | Emergência | 90% | Emergência uniforme |
| 2025-11-05 | A2 | V2-V3 | 80% | Desenvolvimento regular |
| 2025-11-12 | B1 | V4-V5 | 75% | Pequena desuniformidade |

### Resultado esperado

- registros aparecem na listagem
- o dashboard agrícola passa a exibir estado fenológico atual
- filtros por safra funcionam

## Etapa 7 — Registrar monitoramento fitossanitário

### Onde testar

- `/agricola/safras/{id}/monitoramento`
- `/agricola/safras/{id}/caderno`

### Ação

Registrar 2 ocorrências de monitoramento.

### Dados sugeridos

| Data | Talhão | Agente | Severidade | Nível | Ação recomendada |
|---|---|---|---|---:|---|
| 2025-11-18 | A1 | Lagarta | AVISO | 2 | Reavaliar em 3 dias |
| 2025-12-02 | B1 | Ferrugem | CRITICO | 4 | Pulverização imediata |

### Resultado esperado

- monitoramentos aparecem no módulo
- o caderno de campo registra o evento
- o dashboard da safra pode exibir alerta executivo

### Como a IA pode ajudar aqui

- interpretar o nível de risco com base no evento registrado
- contextualizar severidade e urgência
- apoiar a decisão entre monitorar, controlar ou reavaliar

## Etapa 8 — Operações de desenvolvimento

### Onde testar

- `/agricola/safras/{id}/operacoes`

### Ação

Registrar operações coerentes com a fase `DESENVOLVIMENTO`.

### Operações sugeridas

| Tipo | Data | Talhão | Área | Custo |
|---|---|---|---:|---:|
| PULVERIZACAO | 2025-12-03 | B1 | 20,00 ha | R$ 4.800,00 |
| ADUBACAO | 2025-12-10 | A1 | 30,00 ha | R$ 8.400,00 |
| PULVERIZACAO | 2025-12-18 | A2 | 25,00 ha | R$ 4.200,00 |

### Resultado esperado

- operações salvas com sucesso
- custo total da safra e custo por hectare recalculados
- dashboard financeiro da safra reflete aumento de despesa

## Etapa 9 — Caderno de campo

### Onde testar

- `/agricola/safras/{id}/caderno`

### Ação

Validar que o caderno concentre:

- operações
- monitoramentos
- visitas
- entregas
- exportação

### Inserções manuais sugeridas

| Tipo de entrada | Data | Conteúdo |
|---|---|---|
| MONITORAMENTO | 2025-12-02 | Ferrugem observada no B1 |
| VISITA_TECNICA | 2025-12-04 | Recomendado reforço de fungicida |
| ENTREGA | 2025-12-05 | Recebidos 80 L de fungicida |

### Resultado esperado

- linha do tempo consolidada
- exportação do caderno disponível
- assinatura, quando aplicável, concluída sem erro

## Etapa 10 — Avançar para colheita

### Ação

Avançar a safra para `COLHEITA`.

### Resultado esperado

- safra movida para a fase de colheita
- dashboard agrícola reflete a nova posição
- romaneios tornam-se a principal entrada de produção

## Etapa 11 — Registrar romaneios

### Onde testar

- `/agricola/safras/{id}/romaneios`

### Ação

Registrar pelo menos 3 romaneios.

### Dados sugeridos

| Data | Talhão | Quantidade | Unidade | Sacas 60 kg | Preço por saca | Receita total |
|---|---|---:|---|---:|---:|---:|
| 2026-02-10 | A1 | 1.620 | sc | 1.620 | R$ 128,00 | R$ 207.360,00 |
| 2026-02-12 | A2 | 1.250 | sc | 1.250 | R$ 126,00 | R$ 157.500,00 |
| 2026-02-15 | B1 | 980 | sc | 980 | R$ 124,00 | R$ 121.520,00 |

Receita total sugerida:

- `R$ 486.380,00`

Produção total sugerida:

- `3.850 sc`

Produtividade aproximada:

- `51,33 sc/ha`

### Resultado esperado

- romaneios aparecem na listagem
- receita financeira é criada automaticamente se a integração estiver ativa
- dashboard financeiro mostra produção e receita
- rastreabilidade por safra/talhão fica disponível

## Etapa 12 — Beneficiamento

### Onde testar

- `/agricola/safras/{id}/beneficiamento`

### Ação

Criar 1 lote de beneficiamento a partir dos romaneios.

### Dados sugeridos

| Campo | Valor |
|---|---|
| Lote | LOTE-BEN-2026-001 |
| Origem | Romaneios A1 + A2 |
| Entrada bruta | 2.870 sc |
| Quebra/perda | 3,5% |
| Saída líquida | 2.769,55 sc |
| Observação | Secagem e limpeza padrão |

### Resultado esperado

- lote beneficiado vinculado à origem
- perdas registradas
- rastreabilidade preservada entre romaneio e lote final

## Etapa 13 — Financeiro da safra

### Onde testar

- `/agricola/safras/{id}/financeiro`

### Ação

Validar agregação financeira.

### Esperado com a massa sugerida

Custos operacionais lançados no workflow:

- R$ 9.000,00
- R$ 11.250,00
- R$ 12.500,00
- R$ 10.300,00
- R$ 4.800,00
- R$ 8.400,00
- R$ 4.200,00

Subtotal de operações:

- `R$ 60.450,00`

Receita total de romaneios:

- `R$ 486.380,00`

Indicadores esperados:

- total de operações maior que zero
- total de romaneios igual a 3
- receita total maior que despesa total
- lucro bruto positivo
- ROI positivo

### Resultado esperado

- KPIs do financeiro consistentes com operações e romaneios
- timeline financeira com origens rastreáveis
- produtividade calculada por área

## Etapa 14 — Cenário econômico base

### Onde testar

- `/agricola/safras/{id}/cenarios`

### Ação

Criar ou validar o cenário base da safra.

### Dados sugeridos

| Campo | Valor |
|---|---|
| Nome | Cenário Base 2025/26 |
| Tipo | BASE |
| Produtividade default | 51,33 sc/ha |
| Preço default | R$ 126,33 |
| Custo ha default | R$ 806,00 |
| IR alíquota | 15,00% |

### Production units sugeridas

| Unidade | Área | Produtividade | Preço | Custo/ha |
|---|---:|---:|---:|---:|
| A1 | 30,00 ha | 54,00 sc/ha | R$ 128,00 | R$ 820,00 |
| A2 | 25,00 ha | 50,00 sc/ha | R$ 126,00 | R$ 790,00 |
| B1 | 20,00 ha | 49,00 sc/ha | R$ 124,00 | R$ 805,00 |

### Resultado esperado

- cenário calcula receita bruta
- custo total e margem são exibidos
- depreciação, IR e resultado líquido aparecem quando aplicáveis
- dashboard executivo da safra consome esse cenário

### Como a IA pode ajudar aqui

- resumir se o cenário base está saudável ou pressionado
- apontar as variáveis que mais pesam no resultado
- explicar o efeito de custo, produtividade, depreciação e IR no resultado líquido

## Etapa 15 — Criar cenários alternativos

### Ação

Criar mais 2 cenários:

#### Cenário otimista

- nome: `Otimista`
- produtividade: `+8%`
- preço: `+5%`
- custo: `+3%`

#### Cenário pessimista

- nome: `Pessimista`
- produtividade: `-10%`
- preço: `-6%`
- custo: `+7%`

### Resultado esperado

- três cenários visíveis na listagem
- duplicação, exclusão e edição funcionando
- cards e KPIs refletindo a diferença de resultado

## Etapa 16 — Comparativo de cenários

### Onde testar

- `/agricola/safras/{id}/cenarios/comparativo`

### Ação

Comparar `Base`, `Otimista` e `Pessimista`.

### KPIs a validar

- receita bruta total
- custo total
- margem de contribuição
- depreciação total
- IR total
- resultado líquido total
- ponto de equilíbrio

### Resultado esperado

- comparativo carrega sem erro
- colunas completas por cenário
- detalhe por unidade produtiva consistente
- cenário otimista deve superar o base
- cenário pessimista deve ser o pior do conjunto

### Como a IA pode ajudar aqui

- resumir diferenças entre os cenários em linguagem de negócio
- destacar qual cenário combina melhor retorno e risco
- apontar qual unidade produtiva está pressionando o resultado

## Etapa 17 — Dashboard executivo da safra

### Onde testar

- `/agricola/safras/{id}/dashboard`

### Ação

Validar os blocos principais após o fluxo completo.

### Itens esperados

- cards com números da safra
- alertas executivos
- resumo do cenário base
- comparativo executivo sob demanda
- ranking por production unit
- ações recomendadas

### Resultado esperado

- a safra tem dados suficientes para preencher o dashboard
- não há estado vazio indevido
- alertas fazem sentido com os dados lançados

### Como a IA pode ajudar aqui

- transformar muitos dados em prioridades executivas
- explicar o motivo dos alertas e recomendações
- orientar o gestor sobre a próxima análise ou ação sugerida

## Etapa 18 — Dashboard agrícola global

### Onde testar

- `/agricola/dashboard`

### Ação

Revisar o impacto geral da safra no dashboard.

### Resultado esperado

- `Acompanhamento de Safras` mostra a safra em `COLHEITA` ou fase equivalente
- produção x meta reflete avanço da safra
- dados financeiros exibem receita de colheita
- alertas e fenologia refletem a jornada executada

## Critérios de aceite do workflow

O teste é considerado aprovado se:

- a safra for criada e avançar pelas fases esperadas
- o orçamento for salvo e exibido corretamente
- operações forem registradas e refletidas no caderno
- monitoramento e fenologia forem persistidos
- romaneios gerarem produção e receita
- beneficiamento preservar rastreabilidade
- financeiro da safra consolidar custos e receitas
- cenários forem calculados sem erro
- comparativo de cenários carregar corretamente
- dashboard executivo da safra apresentar dados coerentes
- dashboard agrícola global refletir a safra em andamento
- sempre que houver IA, a funcionalidade destacar seu uso e explicar sua utilidade para a decisão

## Casos negativos mínimos

Além do fluxo feliz, executar pelo menos estes testes:

- criar safra com área maior que a do talhão: deve bloquear
- registrar operação em fase não permitida: deve bloquear
- registrar operação com data futura: deve bloquear
- registrar romaneio sem safra válida: deve bloquear
- acessar safra de outro tenant: deve retornar erro de autorização ou não encontrado
- abrir comparativo sem cenários suficientes: deve mostrar estado controlado

## Resultado final esperado do workflow

Ao final do teste, o tenant deve possuir:

- 1 safra agrícola completa
- 3 talhões vinculados
- orçamento consolidado
- 7 operações registradas
- 3 registros fenológicos
- 2 monitoramentos
- 3 romaneios
- 1 lote de beneficiamento
- 3 cenários econômicos
- 1 comparativo funcional

E o sistema deve demonstrar, na prática:

- rastreabilidade da safra
- integração agrícola-financeira
- visão operacional e executiva
- capacidade de simulação e apoio à decisão

## Observações

- O nome do arquivo foi mantido como solicitado: `workflow-atricultura.md`.
- Se quiser uma segunda versão, eu posso derivar este roteiro para:
  - café
  - milho safrinha
  - cana
  - algodão
  - roteiro QA em checklist puro

## Matriz Final

| Tela | Dado esperado | Regra validada |
|---|---|---|
| `/agricola/safras` | Safra `Soja 2025/26` criada e listada | cadastro de safra, vínculo com talhões e validação de área |
| `/agricola/dashboard` | Safra aparece em `Acompanhamento de Safras` | dashboard global reflete status atual da safra |
| `/agricola/planejamento` | planejamento macro disponível | entrada global do planejamento |
| `/agricola/safras/{id}/orcamento` | orçamento com custo previsto, margem e ponto de equilíbrio | cálculo orçamentário por safra |
| `/agricola/operacoes` | operações consolidadas disponíveis | visão global de histórico e consulta |
| `/agricola/safras/{id}/operacoes` | operações de preparo, plantio e desenvolvimento listadas | operação só pode existir com safra válida e fase coerente |
| `/agricola/safras/{id}/fenologia` | registros fenológicos por talhão | persistência e filtro por safra |
| `/agricola/safras/{id}/monitoramento` | ocorrências leves e críticas salvas | monitoramento agronômico vinculado à safra |
| `/agricola/safras/{id}/monitoramento` | se houver IA, recomendação vinculada ao risco observado | uso de IA com contexto agronômico |
| `/agricola/safras/{id}/caderno` | timeline com operações, monitoramentos e entradas manuais | consolidação cronológica do histórico da safra |
| `/agricola/safras/{id}/romaneios` | 3 romaneios com produção e receita | produção, preço e origem por safra/talhão |
| `/agricola/safras/{id}/beneficiamento` | lote final com quebra registrada | rastreabilidade entre origem e lote beneficiado |
| `/agricola/safras/{id}/financeiro` | custos, receitas, lucro e ROI | integração agrícola-financeira |
| `/agricola/safras/{id}/cenarios` | cenário base, otimista e pessimista calculados | simulação econômica por safra |
| `/agricola/safras/{id}/cenarios` | se houver IA, leitura clara de risco e impacto | apoio à decisão econômica |
| `/agricola/safras/{id}/cenarios/comparativo` | colunas com receita, custo, margem, depreciação, IR e resultado | comparativo multi-cenário completo |
| `/agricola/safras/{id}/dashboard` | cards, alertas e comparativo executivo preenchidos | visão executiva da safra baseada em dados reais e simulados |
| `/agricola/safras/{id}/dashboard` | se houver IA, destaque visual e explicação útil | apoio executivo assistido por IA |
