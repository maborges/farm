# Produto SaaS - Estrutura Comercial Step 94

**Data:** 2026-04-30  
**Base principal:** `docs/FECHAMENTO_TECNICO_CROSS_MODULO_STEP93.md`  
**Escopo:** estruturar o AgroSaaS como produto SaaS comercial vendavel com base na arquitetura consolidada nos Steps 46-93.  
**Restricao desta etapa:** nao altera backend. Este step define posicionamento, planos, limites e direcionamento comercial/landing.

## 1. Objetivo do produto

Transformar a consolidacao tecnica dos Steps 46-93 em uma oferta SaaS clara para mercado, com:

- tiers comerciais compreensiveis;
- modulos mapeados por plano;
- limites objetivos de contratacao;
- diferenciais tecnicos traduzidos em valor percebido;
- direcao de hero, planos e CTAs para landing.

O posicionamento resultante e:

> **AgroSaaS e uma plataforma operacional e gerencial para o agro que conecta producao, estoque, financeiro e governanca sem duplicidade de dados.**

## 2. Tese comercial

Os Steps 46-93 provaram que o sistema nao e apenas um conjunto de modulos. Ele tem uma arquitetura mais vendavel do que ERPs fragmentados porque:

- usa cadastro canônico unico para produto, pessoa, unidade produtiva e estoque;
- evita estoques paralelos por modulo;
- conecta origem operacional com impacto financeiro;
- sustenta crescimento do cliente do planejamento basico ate governanca multiempresa;
- entrega rastreabilidade real sem reconstruir planilhas nem reconciliacoes manuais.

Traducao comercial:

- **A1 Planejamento:** entrada rapida para operar sem caos.
- **Profissional:** operacao integrada com controle economico e fisico.
- **Enterprise:** governanca, auditoria, rastreabilidade profunda e escala.

## 3. Estrutura de planos

### 3.1 Visao geral

| Plano | Perfil comercial | Tese principal | Forma de venda |
|---|---|---|---|
| **A1 Planejamento** | produtor que quer sair da planilha e padronizar operacao | implantar rapido e centralizar a base operacional | ticket de entrada |
| **Profissional** | fazenda ou grupo com operacao estruturando custo, estoque e equipe | integrar campo, estoque e financeiro em rotina diaria | plano principal |
| **Enterprise** | grupos, holdings, operacoes multiunidade e alta exigencia de auditoria | escalar com governanca, rastreabilidade e integracoes | venda consultiva |

### 3.2 Regra de monetizacao

- O plano define a profundidade do produto.
- Os modulos definem os dominios operacionais habilitados.
- Core e embutido em todos os planos.
- Agricultura, Pecuaria, Financeiro, Estoque, Frota e CRM sao posicionados como dominios comerciais principais desta etapa.

## 4. Pacotes comerciais

### 4.1 A1 Planejamento

**Posicionamento:** plano de implantacao e organizacao operacional.

**Promessa comercial:**  
Colocar a fazenda para operar em um sistema unico, com planejamento, registro e visao inicial, sem depender de planilhas espalhadas.

**Entrega principal:**

- base cadastral unica;
- planejamento agricola e pecuario essencial;
- estoque simples;
- financeiro essencial;
- time inicial operando no mesmo contexto.

### 4.2 Profissional

**Posicionamento:** plano de operacao integrada.

**Promessa comercial:**  
Conectar producao, estoque, financeiro e frota com rastreabilidade transacional e controle gerencial real.

**Entrega principal:**

- operacao com rastreabilidade por `produto_id`;
- ledger unico de estoque;
- origem financeira integrada;
- visao de custo e consumo por safra, lote, atividade e unidade;
- dashboards gerenciais e comparativos.

### 4.3 Enterprise

**Posicionamento:** plano de governanca e escala.

**Promessa comercial:**  
Expandir para multiunidade, multiempresa, auditoria, integracoes e rastreabilidade exigida por grupos mais complexos.

**Entrega principal:**

- rastreabilidade auditavel ponta a ponta;
- multi-cenario e comparacao executiva ampliada;
- integrações externas e processos mais sofisticados;
- controles adequados para operacoes com alta exigencia de governanca.

## 5. Modulos por plano

### 5.1 Matriz resumida

| Modulo | A1 Planejamento | Profissional | Enterprise |
|---|---|---|---|
| Agricultura | Essencial | Completo gerencial | Completo com automacao e rastreabilidade avancada |
| Pecuaria | Essencial | Completo gerencial | Completo com auditoria e escala |
| Financeiro | Essencial | Integrado e gerencial | Integrado com governanca ampliada |
| Estoque | Simples | Ledger, lotes, custo e controle fino | Ledger com rastreabilidade e integrações ampliadas |
| Frota | Basico | Custo e manutencao | Telemetria/governanca ampliada |
| CRM | Basico comercial | Operacao comercial recorrente | CRM para operacao consultiva e carteira complexa |

### 5.2 Detalhamento por modulo

#### Agricultura

| Plano | Escopo comercial |
|---|---|
| A1 | safra, cultivo, operacoes, caderno e visao inicial |
| Profissional | planejamento, custos, comparacao entre safra/unidade, rastreabilidade operacional e consumo integrado |
| Enterprise | rastreabilidade auditavel, automacao avancada, multi-cenario mais robusto e integrações |

#### Pecuaria

| Plano | Escopo comercial |
|---|---|
| A1 | lotes, manejos basicos, visao inicial de rebanho |
| Profissional | manejo com produto canônico, custos, integracao com estoque e financeiro |
| Enterprise | auditoria, escala, processos mais complexos e rastreabilidade ampliada |

#### Financeiro

| Plano | Escopo comercial |
|---|---|
| A1 | lancamentos basicos, fluxo de caixa e categorias |
| Profissional | contas a pagar/receber, origem operacional integrada, visao gerencial por centro de custo/contexto |
| Enterprise | governanca financeira ampliada, trilha mais auditavel e integrações externas mais intensas |

#### Estoque

| Plano | Escopo comercial |
|---|---|
| A1 | cadastro de produto, saldo e movimentacao simples |
| Profissional | ledger unico, lotes, validade, custo, consumo integrado por modulo |
| Enterprise | rastreabilidade aprofundada, governanca de inventario e integrações externas |

#### Frota

| Plano | Escopo comercial |
|---|---|
| A1 | cadastro de equipamento e apontamentos basicos |
| Profissional | manutencao, custo/hora, combustivel e apropriacao operacional |
| Enterprise | telemetria, escala operacional, governanca ampliada e integrações |

#### CRM

| Plano | Escopo comercial |
|---|---|
| A1 | captura de interesse e CTA comercial basico |
| Profissional | pipeline comercial, ofertas e operacao de upgrade recorrente |
| Enterprise | gestao de carteira complexa, propostas consultivas e ofertas customizadas |

## 6. Limites comerciais recomendados

### 6.1 Regra de desenho

Os limites devem servir a tres objetivos:

- proteger custo operacional do SaaS;
- deixar claro o degrau de upgrade;
- evitar que o cliente compre Enterprise apenas para usar volume que ainda cabe em Profissional.

### 6.2 Tabela de limites

| Limite | A1 Planejamento | Profissional | Enterprise |
|---|---|---|---|
| Usuarios ativos | ate 5 | ate 25 | sob contrato / escalavel |
| Areas/hectares monitorados | ate 3.000 ha | ate 20.000 ha | sob contrato / multiunidade |
| Volume de operacoes mensais | ate 2.000 eventos | ate 20.000 eventos | sob contrato / alto volume |
| Integracoes externas | 0-1 integracao padrao | ate 5 integracoes | integrações sob desenho comercial |

### 6.3 Interpretacao dos limites

#### Usuarios

- **A1:** equipe enxuta, dono + administrativo + operador-chave.
- **Profissional:** fazenda estruturada com gestores, tecnico, financeiro e operacao.
- **Enterprise:** grupos com multiplas frentes, unidades e papeis especializados.

#### Areas/hectares

- **A1:** produtor ou operacao em inicio de digitalizacao.
- **Profissional:** unidade ou grupo com porte medio e rotina gerencial.
- **Enterprise:** grupos grandes, operacoes multiempresa ou contrato por capacidade.

#### Volume de operacoes

O termo "operacoes" deve considerar a soma de eventos relevantes, como:

- operacoes agricolas;
- manejos pecuarios;
- movimentos de estoque;
- lancamentos financeiros de origem operacional.

#### Integracoes

- **A1:** sem dependencia forte de ecossistema externo.
- **Profissional:** integrações recorrentes com ferramentas padrao.
- **Enterprise:** integrações criticas, legado corporativo, BI ou parceiros externos.

## 7. Diferenciais vendaveis

Os diferenciais abaixo devem aparecer em discurso comercial, planos e landing.

### 7.1 Ledger de estoque unico

**Base tecnica:** consolidacao de `estoque_movimentos` como ledger oficial unico.  
**Traducao comercial:**  
O cliente nao precisa reconciliar saldos entre modulos diferentes. O estoque tem uma trilha unica e confiavel.

**Mensagem de venda:**  
"Um unico historico de estoque para compras, consumo, ajustes e producao."

### 7.2 Rastreabilidade por `produto_id`

**Base tecnica:** padronizacao do catalogo canônico e eliminacao do nome legado `insumo_id`.  
**Traducao comercial:**  
Cada consumo ou uso de insumo/produto passa a falar a mesma lingua em Agricultura, Pecuaria e Estoque.

**Mensagem de venda:**  
"O mesmo produto acompanha compra, estoque, aplicacao e manejo sem cadastro paralelo."

### 7.3 Origem financeira integrada

**Base tecnica:** consolidacao de origem operacional ligada a receitas, despesas e movimentos integrados.  
**Traducao comercial:**  
O cliente deixa de ter financeiro sem contexto. Cada valor pode ser explicado pela operacao que o gerou.

**Mensagem de venda:**  
"Nao e so lancamento: e financeiro conectado ao que aconteceu no campo."

### 7.4 Comparacao multi-cenario

**Base tecnica:** arquitetura consolidada para contexto produtivo, financeiro e comparacao por unidade/safra/lote.  
**Traducao comercial:**  
O produto suporta comparacao real entre operacoes, nao apenas relatorios soltos.

**Mensagem de venda:**  
"Compare cenario, safra, unidade e resultado com o mesmo criterio de dados."

## 8. Proposta de posicionamento por plano

### 8.1 A1 Planejamento

**Headline de venda:**  
Organize a operacao e pare de depender de planilhas.

**Provas de valor:**

- cadastro unico e contexto por fazenda/unidade;
- agricultura e pecuaria em nivel essencial;
- estoque e financeiro basicos no mesmo ambiente;
- onboarding comercial simples.

### 8.2 Profissional

**Headline de venda:**  
Integre campo, estoque e financeiro em uma rotina unica.

**Provas de valor:**

- ledger unico de estoque;
- rastreabilidade por produto;
- origem financeira ligada a operacao;
- dashboards e comparativos gerenciais;
- melhor relacao entre profundidade funcional e ticket.

### 8.3 Enterprise

**Headline de venda:**  
Escala com governanca, rastreabilidade e integrações de alto impacto.

**Provas de valor:**

- multiunidade e multiempresa;
- auditoria e trilha operacional ampliada;
- integrações externas;
- desenho comercial sob contrato;
- potencial para expansao consultiva.

## 9. Ajuste de landing recomendado

Esta etapa nao implementa mudancas em frontend. Ela define o direcionamento da landing.

### 9.1 Hero recomendado

**Objetivo:** sair de uma mensagem genérica de "gestao rural premium" para um argumento comercial tecnicamente sustentado.

**Headline recomendada:**

> **Do campo ao financeiro, uma unica plataforma com estoque confiavel, rastreabilidade real e operacao integrada.**

**Subheadline recomendada:**

> Planeje safras e manejos, movimente estoque em ledger unico, conecte custos a origem operacional e compare cenarios sem reconciliar dados em planilhas.

**Bullets de prova no hero:**

- ledger unico de estoque;
- rastreabilidade por produto_id;
- origem financeira integrada;
- comparacao multi-cenario por unidade, safra ou lote.

### 9.2 Secao de planos

A secao de planos deve trocar descricoes muito amplas por uma estrutura orientada a compra:

| Plano | Mensagem curta | CTA |
|---|---|---|
| A1 Planejamento | comecar a operar rapido | Comecar implantacao |
| Profissional | integrar e ganhar controle gerencial | Ver demonstracao |
| Enterprise | escalar com governanca e integrações | Falar com especialista |

**Estrutura sugerida por card:**

- titulo do plano;
- perfil do cliente ideal;
- 3 a 5 capacidades mais vendaveis;
- limites principais;
- CTA coerente com ticket.

### 9.3 CTAs recomendados

Os CTAs da landing devem ser separados por intencao:

- **A1:** `Comecar implantacao`
- **Profissional:** `Ver demonstracao`
- **Enterprise:** `Falar com especialista`

CTAs secundarios:

- `Comparar planos`
- `Entender os modulos`
- `Falar com comercial`

### 9.4 Secoes recomendadas para a landing

1. Hero com tese central de integracao.
2. Bloco de diferenciais tecnicos traduzidos em valor.
3. Matriz simples de planos.
4. Bloco de modulos por plano.
5. CTA final com duas trilhas:
   - autoentrada para A1
   - vendas consultivas para Profissional/Enterprise

## 10. Narrativa comercial por persona

### 10.1 Produtor em digitalizacao

**Dor:** planilhas, retrabalho e baixa visibilidade.  
**Oferta mais aderente:** A1 Planejamento.  
**Argumento central:** comecar rapido, registrar bem e criar base para crescer.

### 10.2 Fazenda com operacao estruturando controle

**Dor:** operacao existe, mas estoque, financeiro e campo nao se explicam entre si.  
**Oferta mais aderente:** Profissional.  
**Argumento central:** integrar rotina operacional e ganhar controle economico real.

### 10.3 Grupo, holding ou operacao complexa

**Dor:** governanca, rastreabilidade, auditoria e integrações.  
**Oferta mais aderente:** Enterprise.  
**Argumento central:** escalar sem fragmentar cadastros, rastros e controles.

## 11. Riscos comerciais a evitar

- vender Enterprise por volume quando o problema real e onboarding ou parametrizacao;
- prometer integracao total sem enquadrar o cliente em limite/modulo/tier;
- tratar modulo como pacote isolado quando o valor central do produto e a integracao;
- comunicar "premium" sem citar os diferenciais tecnicos que justificam premium;
- deixar o Profissional fraco demais, porque ele deve ser o plano principal de crescimento.

## 12. Recomendacao final

Para comercializacao imediata, o desenho mais forte e:

- **A1 Planejamento** como porta de entrada;
- **Profissional** como plano principal e mais vendavel;
- **Enterprise** como venda consultiva de governanca e escala.

O principal diferencial competitivo do AgroSaaS nao deve ser comunicado como "tem muitos modulos", e sim como:

> **Uma arquitetura unica que conecta operacao, estoque e financeiro com rastreabilidade consistente.**

## 13. Referencias

- `docs/FECHAMENTO_TECNICO_CROSS_MODULO_STEP93.md`
- `docs/contexts/step46-cross-module-integration-monetization-context.md`
- `docs/contexts/step48-cross-module-ownership-context.md`
- `docs/ESTOQUE_CANONICO_LEDGER_2026-04-28.md`
- `docs/AUDITORIA_PRODUTO_CANONICO_FINAL_STEP87.md`
- `docs/VALIDACAO_CROSS_MODULO_STEP92.md`
- `apps/web/src/app/page.tsx`
