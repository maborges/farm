# PILOT-ARCH-01 — Arquitetura Oficial de Implantação do Cliente

## 1. Resumo executivo

O AgroSaaS passa a adotar uma arquitetura oficial de implantação baseada exclusivamente nas arquiteturas oficiais já aprovadas:

- `ARC-00`
- `PERSON-ARCH-01`
- `ECONOMIC-ARCH-01`
- `TERRITORY-ARCH-01`
- `PRODUCT-ARCH-01`
- `EVENTS-ARCH-01`

Pergunta respondida por este documento:

**Qual é o processo oficial de implantação de um novo cliente no AgroSaaS, garantindo que todos os módulos sejam configurados na ordem correta, sem dependências quebradas, e produzindo uma operação consistente desde o primeiro dia?**

Resposta objetiva:

- a implantação oficial deve seguir uma sequência padronizada por fases;
- a base mínima obrigatória é `Tenant -> Administrador -> Onboarding -> UnidadeProdutiva`;
- a partir disso, a implantação evolui por camadas: territorial, cadastros mestres, financeiro, estoque, agricultura, pecuária, operação assistida e go-live;
- cada módulo entra em produção somente depois de cumprir dependências estruturais e critérios mínimos de homologação.

Classificação final: **Modelo B**.

A arquitetura já está pronta para orientar Wizard, implantação manual, consultoria e primeiro piloto, mas ainda depende de compatibilidades documentadas em alguns cadastros mestres e fluxos legados.

## 2. Fluxo oficial de implantação

Fluxo oficial macro:

```text
Pré-implantação
  ↓
Tenant
  ↓
Administrador
  ↓
Onboarding técnico
  ↓
UnidadeProdutiva
  ↓
Estrutura territorial
  ↓
Cadastros mestres
  ↓
Configuração financeira
  ↓
Estoque inicial
  ↓
Agricultura e/ou Pecuária
  ↓
Financeiro operacional
  ↓
Operação assistida
  ↓
Go-live
  ↓
Estabilização
```

Princípio oficial:

- primeiro nasce o ambiente;
- depois nasce a estrutura operacional mínima;
- depois entram os cadastros oficiais;
- só então começam operações reais.

## 3. Tipos oficiais de cliente

Tipos oficiais de implantação:

- Agricultura
- Pecuária
- Agricultura + Pecuária
- Grupo agrícola
- Cooperativa
- Revenda
- Prestador de serviços

Regras:

- `Agricultura` exige trilha territorial agrícola, culturas, safra, cultivo e `ProductionUnit`.
- `Pecuária` exige trilha territorial pecuária, lotes e animais.
- `Agricultura + Pecuária` exige núcleo comum único e ativação por ondas.
- `Grupo agrícola` exige múltiplas `UnidadeProdutiva` sob o mesmo `Tenant`.
- `Cooperativa`, `Revenda` e `Prestador de serviços` podem iniciar com núcleo administrativo e financeiro antes da operação rural completa.

## 4. Fase 0 — Pré-implantação

### 4.1 Informações obrigatórias

- razão social ou nome do cliente;
- tipo oficial de cliente;
- país, estado, município e fuso principal;
- moeda principal;
- contato do administrador inicial;
- escopo de módulos do piloto;
- quantidade inicial de unidades produtivas;
- existência ou não de agricultura;
- existência ou não de pecuária;
- estratégia de estoque inicial;
- estratégia de saldo inicial financeiro.

### 4.2 Informações opcionais

- imóveis rurais e documentos fundiários já consolidados;
- estrutura societária de propriedades;
- integração com ERP externo;
- arquivos CSV/Excel legados;
- base geoespacial SIG;
- histórico de estoque;
- histórico financeiro;
- lista de usuários secundários.

### 4.3 Pré-requisitos

- patrocinador do projeto definido;
- administrador funcional do cliente definido;
- escopo do piloto aprovado;
- decisão sobre módulos de onda 1 e onda 2;
- arquivos de importação minimamente saneados, se existirem;
- definição de quem cadastra o quê: cliente, consultor ou equipe interna.

## 5. Fase 1 — Criação do ambiente

Fluxo oficial:

```text
Tenant
  ↓
Administrador
  ↓
Onboarding
  ↓
UnidadeProdutiva
```

### 5.1 Obrigatório

- criar usuário administrador;
- criar `Tenant` ativo;
- vincular o administrador ao tenant;
- concluir onboarding técnico do tenant;
- criar ao menos uma `UnidadeProdutiva` ativa.

### 5.2 Pode ficar para depois

- usuários adicionais;
- perfis detalhados;
- permissões granulares por módulo;
- múltiplas unidades produtivas;
- propriedades e imóveis rurais formais;
- contas bancárias adicionais.

### 5.3 Regras

- sem `Tenant` ativo não existe implantação;
- sem onboarding concluído o dashboard permanece bloqueado;
- sem `UnidadeProdutiva` ativa não existe operação;
- a primeira `UnidadeProdutiva` é o gatilho do contexto operacional mínimo.

## 6. Fase 2 — Estrutura territorial

Fluxo oficial:

```text
Propriedade
  ↓
ImovelRural
  ↓
PropriedadeImovel
  ↓
AreaRural
  ↓
Talhões
  ↓
Piquetes
  ↓
Infraestrutura
```

### 6.1 Ordem obrigatória

Ordem territorial oficial:

1. `UnidadeProdutiva`
2. raízes automáticas de `AreaRural`
3. `Propriedade`, quando houver gestão patrimonial
4. `ImovelRural`, quando houver gestão legal/fundiária
5. `PropriedadeImovel`, quando a relação patrimonial precisar ser formalizada
6. detalhamento da árvore `AreaRural`
7. `Talhão` como `AreaRural.tipo = TALHAO`
8. `Piquete` como `AreaRural.tipo = PIQUETE`
9. infraestrutura operacional

### 6.2 O que pode ser criado automaticamente

- estruturas raiz de `AreaRural`;
- raiz de `INFRAESTRUTURA`;
- parte da estrutura inicial mínima da unidade produtiva.

### 6.3 Dependências

- `Propriedade` depende de `Tenant`.
- `ImovelRural` depende do contexto do tenant e, para implantação operacional, deve ser vinculado à realidade da unidade.
- `PropriedadeImovel` depende de `Propriedade` e `ImovelRural`.
- `AreaRural` depende de `UnidadeProdutiva`.
- `Talhão` depende da árvore `AreaRural`.
- `Piquete` depende da árvore `AreaRural`.
- `Infraestrutura` depende de `UnidadeProdutiva` e preferencialmente da árvore oficial.

### 6.4 Regra oficial

- operação nova usa `AreaRural` como árvore única;
- não se cria entidade paralela de talhão ou piquete;
- `pec_piquetes` permanece apenas como compatibilidade legada.

## 7. Fase 3 — Cadastros mestres

### 7.1 Ordem oficial

1. Pessoas
2. Usuários
3. Funcionários
4. Fornecedores
5. Clientes
6. Produtos
7. Culturas
8. Commodities
9. Máquinas e equipamentos
10. Depósitos
11. Animais e lotes
12. Categorias e unidades auxiliares
13. Plano de contas
14. Centro de custos e parâmetros financeiros

### 7.2 Classificação

| Cadastro | Classificação | Observação |
| --- | --- | --- |
| Pessoa | Obrigatório para operação madura | Fonte oficial de identidade |
| Usuário | Obrigatório | Pelo menos administrador |
| Funcionário | Opcional no início | Obrigatório antes de RH/apontamento |
| Fornecedor | Importável | Deve convergir para `Pessoa` |
| Cliente | Importável | Papel comercial, não master paralelo novo |
| Produto | Obrigatório para estoque/compras | Catálogo mestre |
| ProdutoCultura | Obrigatório para agricultura | Cultura oficial |
| Commodity | Obrigatório para comercialização/hedge | Mercado oficial |
| Máquina/Equipamento | Opcional | Obrigatório antes de frota |
| Depósito | Obrigatório para estoque | Estrutura operacional |
| Animal | Opcional por escopo | Obrigatório para pecuária individual |
| LoteAnimal | Obrigatório para pecuária | Organização do rebanho |
| Categorias auxiliares | Automático/importável | Conforme catálogo disponível |
| PlanoConta | Obrigatório para financeiro | Base financeira oficial |
| Centro de custos | Opcional na entrada mínima | Necessário para governança econômica madura |

### 7.3 Regras

- pessoa nova deve seguir `PERSON-ARCH-01`;
- produto novo deve seguir `PRODUCT-ARCH-01`;
- cultura nova deve usar `ProdutoCultura`;
- commodity nova deve usar `Commodity`;
- centro de custo é tratado como camada de governança/agregação e não bloqueia o ambiente mínimo.

## 8. Fase 4 — Configuração financeira

Fluxo oficial:

```text
Plano de Contas
  ↓
Parâmetros
  ↓
Saldo Inicial
  ↓
Receita / Despesa
  ↓
Fluxo de Caixa
  ↓
DRE
```

### 8.1 Ordem correta

1. plano de contas
2. parâmetros financeiros do tenant
3. categorias e defaults aceitos
4. centros de custo, se usados
5. contas bancárias
6. saldos iniciais
7. início de receitas e despesas operacionais

### 8.2 Dependências

- `Receita` e `Despesa` dependem de `PlanoConta`.
- `Fluxo de Caixa` depende de `Receita` e `Despesa`.
- `DRE` depende de `Receita`, `Despesa` e `CostAllocation`, quando houver operação agrícola.
- `Rentabilidade` depende da `DRE agrícola v1`.

### 8.3 Regra oficial

- obrigação financeira entra por `Despesa`;
- receita operacional entra por `Receita`;
- custo operacional novo entra por `OperationalCostAllocationService -> CostAllocation`.

## 9. Fase 5 — Estoque inicial

Fluxo oficial:

```text
Produto
  ↓
Depósito
  ↓
LoteEstoque
  ↓
Inventário inicial
  ↓
Saldo / custo
```

### 9.1 Ordem correta

1. cadastrar `Produto`
2. cadastrar `Depósito`
3. definir unidade de medida e regras de lote, se usadas
4. criar `LoteEstoque`, quando aplicável
5. lançar inventário inicial
6. validar saldo e custo inicial

### 9.2 Regras

- compras e estoque usam `Produto`, nunca `ProdutoColhido`;
- lote é opcional no ambiente mínimo, mas obrigatório se o controle físico exigir;
- o estoque inicial deve estar reconciliado antes do primeiro consumo real;
- carga assistida por CSV/Excel é permitida, desde que validada.

## 10. Fase 6 — Agricultura

Fluxo oficial:

```text
Safra
  ↓
Cultivo
  ↓
ProductionUnit
  ↓
Planejamento
  ↓
Operações
  ↓
Caderno
  ↓
Colheita
```

### 10.1 Cadastros obrigatórios

- `UnidadeProdutiva`
- árvore `AreaRural`
- pelo menos um `Talhão`
- `ProdutoCultura`
- `Safra`
- `Cultivo`
- `ProductionUnit`

### 10.2 Dependências

- `Safra` depende de `UnidadeProdutiva` e área produtiva.
- `Cultivo` depende de `Safra` e de cultura oficial.
- `ProductionUnit` depende de `Cultivo` e área.
- planejamento depende de `ProductionUnit`.
- operações dependem de planejamento mínimo ou contexto de execução.
- caderno depende de operações registráveis.
- colheita e romaneio dependem do ciclo agrícola implantado.

### 10.3 Regra oficial

- novo fluxo agrícola analítico/econômico deve convergir para `ProductionUnit`;
- receita agrícola formal entra por `Receita`;
- custo operacional agrícola novo entra por `CostAllocation`.

## 11. Fase 7 — Pecuária

Fluxo oficial:

```text
Lotes
  ↓
Animais
  ↓
Pesagens
  ↓
Sanidade
  ↓
Reprodução
```

### 11.1 Ordem obrigatória

1. `UnidadeProdutiva`
2. área pecuária oficial
3. `LoteAnimal`
4. `Animal`
5. pesagens
6. sanidade
7. reprodução

### 11.2 Regras

- piquete novo deve usar `AreaRural.tipo = PIQUETE`;
- rebanho sem lotes só é aceitável como compatibilidade temporária, não como direção oficial;
- vacina, medicamento, ração e mineral usam `Produto`.

## 12. Fase 8 — Financeiro operacional

Fluxo oficial:

```text
Receitas
  ↓
Despesas
  ↓
Fluxo de Caixa
  ↓
DRE
  ↓
Rentabilidade
```

### 12.1 Como iniciar

1. concluir plano de contas
2. revisar parâmetros e contas bancárias
3. lançar saldo inicial
4. ativar receitas e despesas correntes
5. validar fluxo de caixa
6. validar DRE oficial
7. validar rentabilidade, quando houver agricultura

### 12.2 Regra oficial

- a primeira operação financeira real só acontece depois de plano de contas validado;
- DRE agrícola oficial é `agricola.dre.v1`;
- rentabilidade oficial deriva da DRE agrícola v1.

## 13. Fase 9 — Operação assistida

Fluxos obrigatórios da operação assistida:

- primeiro plantio
- primeira aplicação
- primeira requisição
- primeira compra
- primeira colheita
- primeira comercialização
- primeiro abastecimento
- primeira pesagem
- primeira vacinação
- primeira OS

### 13.1 Indicadores mínimos por fluxo

| Fluxo | Indicador de operação |
| --- | --- |
| Primeiro plantio | operação registrada em área válida e vinculada a `ProductionUnit` |
| Primeira aplicação | consumo de insumo rastreável e custo alocado |
| Primeira requisição | movimentação de estoque concluída sem saldo negativo indevido |
| Primeira compra | pedido, recebimento, estoque e `Despesa` consistentes |
| Primeira colheita | romaneio e/ou produto colhido criado sem quebra de rastreabilidade |
| Primeira comercialização | `Commodity` e `Receita` consistentes |
| Primeiro abastecimento | equipamento, produto combustível e custo operacional coerentes |
| Primeira pesagem | animal/lote atualizado e evento persistido |
| Primeira vacinação | produto sanitário, animal/lote e custo coerentes |
| Primeira OS | ativo/equipamento, material e custo operacional rastreáveis |

## 14. Fase 10 — Go-live

### 14.1 Checklist obrigatório

- usuário administrador ativo
- tenant ativo
- onboarding concluído
- ao menos uma unidade produtiva ativa
- árvore territorial mínima pronta
- produtos mínimos cadastrados
- estoque inicial validado, se o módulo for usado
- plano de contas validado, se o financeiro for usado
- safra/cultivo/production unit, se agricultura estiver na onda 1
- lotes/animais, se pecuária estiver na onda 1
- usuários e permissões mínimas revisados
- sincronização Campo validada, se o PWA estiver no escopo
- health checks operacionais básicos validados
- rotina de backup definida

### 14.2 Critérios de aptidão

O cliente está apto para produção quando:

- consegue operar os fluxos da onda 1 sem planilha paralela obrigatória;
- os cadastros oficiais mínimos estão completos;
- não há dependência estrutural bloqueante aberta;
- os usuários críticos foram treinados;
- os primeiros fluxos reais passaram pela operação assistida.

## 15. Cadastros obrigatórios e opcionais

### 15.1 Obrigatórios

- usuário administrador
- tenant
- onboarding
- unidade produtiva
- área mínima por escopo
- produto, se houver estoque/compras
- plano de contas, se houver financeiro
- safra/cultivo/production unit, se houver agricultura
- lote animal, se houver pecuária

### 15.2 Opcionais

- múltiplas propriedades
- múltiplos imóveis rurais
- centros de custo avançados
- hedge
- comercialização avançada
- RH completo
- frota completa

### 15.3 Automáticos

- estrutura raiz de áreas;
- parte das categorias/defaults aceitas em onboarding;
- estrutura mínima da unidade produtiva.

### 15.4 Importáveis

- pessoas
- fornecedores
- clientes
- produtos
- culturas
- commodities
- estoque inicial
- animais
- saldos financeiros, quando o layout estiver saneado

## 16. Dependências entre módulos

### 16.1 Matriz oficial resumida

| Módulo | Depende de |
| --- | --- |
| Usuário | Tenant |
| UnidadeProdutiva | Tenant |
| AreaRural | UnidadeProdutiva |
| Propriedade | Tenant |
| ImovelRural | Tenant e contexto territorial |
| PropriedadeImovel | Propriedade + ImovelRural |
| Produto | Tenant |
| ProdutoCultura | Tenant |
| Commodity | Tenant |
| Depósito | UnidadeProdutiva |
| Estoque inicial | Produto + Depósito |
| Safra | UnidadeProdutiva + Área/Talhão |
| Cultivo | Safra + ProdutoCultura |
| ProductionUnit | Cultivo + Área |
| LoteAnimal | UnidadeProdutiva e preferencialmente Área/Piquete |
| Animal | LoteAnimal ou contexto pecuário válido |
| PlanoConta | Tenant |
| Receita | PlanoConta |
| Despesa | PlanoConta |
| Fluxo de Caixa | Receita + Despesa |
| DRE agrícola | Receita + Despesa + CostAllocation |
| Rentabilidade | DRE agrícola v1 |

### 16.2 Regra geral

- nenhum módulo operacional nasce antes do núcleo `Tenant -> UnidadeProdutiva`;
- nenhum fluxo econômico novo nasce fora da arquitetura econômica oficial;
- nenhum fluxo agrícola analítico nasce fora de `ProductionUnit`;
- nenhuma notificação ou alerta de implantação futura deve fugir da arquitetura de eventos oficial.

## 17. Ordem oficial de implantação

1. Pré-implantação
2. Criação do ambiente
3. Estrutura territorial
4. Cadastros mestres
5. Configuração financeira
6. Estoque inicial
7. Agricultura
8. Pecuária
9. Financeiro operacional
10. Operação assistida
11. Go-live
12. Estabilização

Regra:

- ondas podem ser escalonadas por módulo;
- a ordem estrutural não pode ser invertida.

## 18. Maturidade da implantação

| Nível | Objetivo | Critérios | Entregáveis | Dependências | Indicadores |
| --- | --- | --- | --- | --- | --- |
| 0 | Ambiente criado | tenant e admin ativos | acesso liberado | usuário e tenant | `% ambiente provisionado` |
| 1 | Estrutura territorial pronta | unidade e árvore mínima criadas | unidade produtiva e áreas base | nível 0 | `% estrutura territorial` |
| 2 | Cadastros mestres completos | masterdata mínimo por escopo | pessoas, produtos, culturas, contas | nível 1 | `% cadastros completos` |
| 3 | Primeiras operações reais | fluxo assistido executado | primeiras transações reais | nível 2 | `% fluxos homologados` |
| 4 | Operação integrada | módulos se conversam sem retrabalho estrutural | estoque, agrícola, pecuária e financeiro coerentes | nível 3 | `% módulos integrados` |
| 5 | Go-live | checklist de produção concluído | cliente em produção | nível 4 | `% aptidão go-live` |
| 6 | Operação estabilizada | 30 a 90 dias sem quebra estrutural relevante | operação monitorada | nível 5 | `% aderência operacional`, incidentes |
| 7 | Excelência operacional | uso consistente, governado e auditável | operação madura e otimizada | nível 6 | `% adoção`, `% usuários treinados`, qualidade de dados |

## 19. Importação de dados

### 19.1 Pode importar

- CSV
- Excel
- ERP
- SIG
- API

### 19.2 Deve ser preferencialmente manual ou validado com curadoria

- parâmetros do tenant
- documentos legais
- permissões
- usuários
- vínculos patrimoniais/fundiários críticos
- políticas operacionais de implantação

### 19.3 Regra oficial

- importação acelera carga, não substitui validação arquitetural;
- dados importados devem convergir para as entidades oficiais;
- importação que reforça legado paralelo não é direção futura.

## 20. Checklist de implantação

### 20.1 Administrador

- definir escopo do piloto
- aprovar usuários críticos
- aprovar unidades produtivas
- aprovar parâmetros gerais
- aprovar janela de go-live

### 20.2 Consultor

- mapear módulos da onda 1
- validar dados de origem
- revisar dependências
- conduzir operação assistida
- registrar pendências e aceite

### 20.3 Cliente

- fornecer cadastros e documentos
- validar dados importados
- executar fluxos assistidos
- indicar responsáveis por módulo
- aceitar go-live

### 20.4 Sistema

- permitir onboarding completo
- garantir criação da unidade produtiva
- garantir estrutura territorial mínima
- validar cadastros obrigatórios
- expor health checks operacionais necessários

## 21. Checklist de homologação

Um módulo é considerado homologado quando:

- suas dependências estruturais foram cumpridas;
- o cadastro oficial mínimo está completo;
- ao menos um fluxo real assistido foi executado com sucesso;
- não há erro bloqueante aberto;
- o responsável funcional validou o resultado.

Checklist:

- dependências confirmadas
- dados mínimos carregados
- fluxo assistido executado
- resultado econômico e/ou operacional coerente
- aceite funcional registrado

## 22. Checklist de go-live

A fazenda está pronta para operar exclusivamente pelo AgroSaaS quando:

- ambiente, usuários e permissões mínimas estão ativos;
- estrutura territorial está suficiente para o escopo;
- cadastros mestres mínimos estão consistentes;
- estoque inicial foi reconciliado, se aplicável;
- financeiro inicial foi configurado, se aplicável;
- agricultura e/ou pecuária passaram pela operação assistida;
- relatórios básicos e saúde operacional foram conferidos;
- plano de suporte dos primeiros dias está definido.

## 23. Rollback

Plano oficial de rollback durante implantação:

- interromper ativação do módulo que ainda não homologou;
- manter operação híbrida temporária apenas no módulo afetado;
- preservar cadastros oficiais já validados;
- reabrir operação assistida após correção de dados ou processo;
- evitar rollback estrutural de tenant/unidade produtiva já produtivos.

Regra:

- rollback é de entrada em operação, não de arquitetura oficial.

## 24. Estabilização

### 24.1 Primeiros 30 dias

- suporte diário
- correção de dados de operação
- reforço de treinamento
- acompanhamento de fluxos críticos

### 24.2 Primeiros 60 dias

- consolidação de aderência
- ativação de módulos da onda 2
- revisão de indicadores
- fechamento das pendências de implantação

### 24.3 Primeiros 90 dias

- revisão executiva de uso
- auditoria de qualidade de dados
- fechamento do plano de estabilização
- transição para operação recorrente

## 25. KPIs da implantação

- `% implantação concluída`
- `% cadastros mestres concluídos`
- `% módulos ativos`
- `% usuários treinados`
- `% estoque implantado`
- `% financeiro implantado`
- `% agricultura implantada`
- `% pecuária implantada`
- `% fluxos assistidos homologados`
- `% unidades produtivas implantadas`
- tempo até go-live
- incidentes críticos por fase

## 26. Plano recomendado

- usar implantação em ondas, nunca por ativação total indiscriminada;
- tratar `Tenant -> UnidadeProdutiva -> AreaRural -> Masterdata` como espinha dorsal única;
- ativar financeiro antes do primeiro lançamento real;
- ativar agricultura e pecuária somente após estrutura territorial válida;
- usar operação assistida como gate obrigatório antes do go-live.

## 27. Decisão final

Classificação: **Modelo B**.

Existe uma arquitetura oficial suficientemente clara para implantação, Wizard futuro e piloto, mas a implantação ainda deve respeitar compatibilidades documentadas de masterdata e alguns pontos legados de apoio.

## 28. Pergunta final obrigatória

Resposta objetiva: **sim**.

Após esta execução, o AgroSaaS passa a possuir uma Arquitetura Oficial de Implantação suficientemente completa para servir de base ao futuro Wizard de Implantação, à equipe de implantação, aos parceiros e ao primeiro projeto piloto, garantindo uma sequência padronizada, auditável e repetível de implantação até o Go-live, sem criar dependências quebradas ou variações operacionais entre clientes.
