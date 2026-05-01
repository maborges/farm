# Pricing e Conversao SaaS - Step 95

**Data:** 2026-04-30  
**Base principal:** `docs/PRODUTO_SAAS_ESTRUTURA_COMERCIAL_STEP94.md`  
**Escopo:** definir pricing, estrategia de upgrade e estrutura de conversao dos planos `A1 Planejamento`, `Profissional` e `Enterprise`.  
**Restricao desta etapa:** nao altera backend nem frontend.

## 1. Premissas desta etapa

Este step nao parte do zero. A plataforma ja possui elementos relevantes de billing e comercializacao:

- campos de `preco_mensal` e `preco_anual` no backoffice de planos;
- suporte a `trial` e `dias_trial` nas estruturas administrativas;
- fluxo de solicitacao de upgrade em billing;
- onboarding inicial ja existente;
- backoffice com planos, CRM, assinantes, ofertas e troca de plano.

Portanto, o objetivo aqui nao e criar um sistema novo de cobranca, e sim:

- simplificar a oferta comercial em 3 planos principais;
- alinhar o pricing ao posicionamento do Step 94;
- propor uma logica de conversao coerente com o que ja existe no produto.

## 2. Decisao de modelo comercial

### 2.1 Estrutura comercial adotada

O Step 94 consolidou o produto em:

- `A1 Planejamento`
- `Profissional`
- `Enterprise`

Esta deve ser a estrutura principal de venda em landing, CRM e billing comercial.  
Pacotes antigos mais fragmentados, como `Produtor`, `Gestao`, `Pecuaria`, `Lavoura` e `Rastreabilidade`, devem ser tratados como material historico/estrategico e nao como a narrativa principal da fase atual.

### 2.2 Papel de cada plano

| Plano | Papel comercial |
|---|---|
| `A1 Planejamento` | entrada real do funil |
| `Profissional` | plano principal de receita e conversao |
| `Enterprise` | plano consultivo de governanca e escala |

## 3. Pricing mensal sugerido

### 3.1 Tabela principal

| Plano | Pricing mensal sugerido | Pricing anual sugerido | Observacao |
|---|---:|---:|---|
| `A1 Planejamento` | **R$ 79/mês** | **R$ 790/ano** | entrada acessivel, acima de ticket simbólico e abaixo de suites mais robustas |
| `Profissional` | **R$ 249/mês** | **R$ 2.490/ano** | plano principal, ainda competitivo frente a ERPs/setoriais mais caros |
| `Enterprise` | **a partir de R$ 990/mês** | **a partir de R$ 9.900/ano** | base para proposta consultiva; pode subir por volume, integrações e suporte |

### 3.2 Justificativa

#### A1 Planejamento

O A1 precisa:

- ser barato o suficiente para destravar entrada;
- nao ser tao barato a ponto de parecer produto incompleto ou desvalorizar onboarding;
- manter espaco claro para upgrade.

`R$ 79/mês` posiciona o A1 como software de entrada serio, ainda acessivel para produtor em digitalizacao.

#### Profissional

O Profissional deve ser o plano mais vendavel e o centro do negocio.

Ele concentra:

- ledger unico de estoque;
- rastreabilidade por `produto_id`;
- origem financeira integrada;
- comparacao gerencial e profundidade operacional real.

`R$ 249/mês` o posiciona acima do A1, mas ainda abaixo de ERPs agricolas mais pesados, preservando argumento de custo-beneficio.

#### Enterprise

Enterprise nao deve ser ancorado so por volume.  
O ticket deve refletir:

- governanca;
- integracoes;
- complexidade de onboarding;
- suporte;
- exigencia de rastreabilidade e auditoria.

Por isso, a recomendacao e comunicar:

> **Enterprise a partir de R$ 990/mês**

e sempre tratar o valor final como composicao comercial por escopo.

## 4. Logica de upgrade

### 4.1 Regra geral

Upgrade deve ser orientado por:

- saturacao de limite;
- necessidade de profundidade funcional;
- aumento de complexidade operacional;
- aumento de exigencia comercial/governanca.

### 4.2 Gatilhos objetivos

| Gatilho | Plano atual | Proximo passo recomendado |
|---|---|---|
| mais de 5 usuarios ativos | A1 | subir para `Profissional` |
| mais de 3.000 ha monitorados | A1 | subir para `Profissional` |
| mais de 2.000 operacoes/mês | A1 | subir para `Profissional` |
| precisa estoque por lote/validade/custo | A1 | subir para `Profissional` |
| precisa origem financeira integrada e visao gerencial | A1 | subir para `Profissional` |
| mais de 25 usuarios ativos | Profissional | avaliar `Enterprise` |
| mais de 20.000 ha | Profissional | avaliar `Enterprise` |
| mais de 20.000 operacoes/mês | Profissional | avaliar `Enterprise` |
| mais de 5 integrações | Profissional | avaliar `Enterprise` |
| precisa multiunidade com governanca forte, auditoria ou projeto consultivo | Profissional | subir para `Enterprise` |

### 4.3 Gatilhos qualitativos

#### Upgrade de A1 para Profissional

O cliente deve subir quando:

- sai de organizacao basica para controle gerencial;
- quer parar de operar com estoque e financeiro parcialmente desconectados;
- passa a exigir rastreabilidade mais confiavel para custo e consumo.

#### Upgrade de Profissional para Enterprise

O cliente deve subir quando:

- a operacao deixa de ser apenas "mais volume" e passa a ser "mais governanca";
- surgem integrações, compliance, multiplas unidades ou estrutura corporativa;
- o custo de nao ter trilha/auditoria passa a ser maior que o ticket do upgrade.

## 5. Modelo de cobranca

### 5.1 Mensal vs anual

Recomendacao:

- manter os dois ciclos disponiveis;
- usar o anual como opcao default recomendada para `Profissional`;
- manter `mensal` como friccao baixa de entrada para `A1`.

### 5.2 Desconto anual

Recomendacao padrao:

- **2 meses de desconto no anual**, equivalente a aproximadamente **16,7%** sobre 12 mensalidades.

Aplicacao sugerida:

| Plano | Mensal | Anual | Equivalencia |
|---|---:|---:|---|
| `A1 Planejamento` | R$ 79 | R$ 790 | 10 meses pagos |
| `Profissional` | R$ 249 | R$ 2.490 | 10 meses pagos |
| `Enterprise` | a partir de R$ 990 | a partir de R$ 9.900 | base contratual; negociar acima disso conforme escopo |

### 5.3 Setup

Recomendacao:

- **A1:** sem setup
- **Profissional:** setup opcional
- **Enterprise:** setup recomendado/quase obrigatorio

Tabela sugerida:

| Plano | Setup |
|---|---|
| `A1 Planejamento` | **R$ 0** |
| `Profissional` | **R$ 0 self-service** ou **R$ 1.500 onboarding assistido** |
| `Enterprise` | **a partir de R$ 5.000** conforme escopo, parametrizacao e integrações |

Justificativa:

- A1 precisa entrar sem barreira alta.
- Profissional pode fechar self-service, mas deve abrir espaco para receita de implantacao assistida.
- Enterprise sem setup tende a subprecificar custo real de ativacao.

## 6. Estrategia de entrada

### 6.1 Trial ou nao

Recomendacao:

- **A1:** sim, com trial curto e orientado
- **Profissional:** trial seletivo
- **Enterprise:** nao comunicar trial aberto; usar discovery + demo + proposta

Modelo sugerido:

| Plano | Trial recomendado |
|---|---|
| `A1 Planejamento` | **7 dias** |
| `Profissional` | **7 a 14 dias sob criterio comercial** |
| `Enterprise` | **sem trial aberto** |

Observacao importante:

O sistema ja suporta `dias_trial`, inclusive com referencias a `15 dias`.  
Mesmo assim, para conversao comercial, `7 dias` e mais disciplinado para:

- reduzir conta ociosa;
- acelerar onboarding;
- diminuir trial longo sem ativacao.

Se o time comercial quiser preservar `15 dias` por restricao operacional atual, o documento recomenda tratar `7 dias` como alvo comercial futuro e `15 dias` como compatibilidade temporaria.

### 6.2 Onboarding assistido vs self-service

| Plano | Modelo recomendado |
|---|---|
| `A1 Planejamento` | **self-service com onboarding guiado** |
| `Profissional` | **self-service assistido opcional** |
| `Enterprise` | **onboarding assistido obrigatorio** |

### 6.3 Entry point real

O entry point real do produto deve ser:

> **A1 Planejamento**

Motivo:

- menor friccao de compra;
- narrativa simples;
- boa porta para conversao posterior;
- encaixa com o onboarding ja existente.

O `Profissional` deve ser tratado como:

> **plano principal de monetizacao**

## 7. Estrutura de conversao

### 7.1 Fluxo recomendado

Fluxo principal:

1. `Landing`
2. `CTA do plano`
3. `Cadastro`
4. `Ativacao`
5. `Onboarding inicial`
6. `Primeiro valor percebido`
7. `Upgrade contextual`

### 7.2 Fluxo detalhado por etapa

#### 1. Landing

Cada visitante deve encontrar:

- tese clara do produto;
- diferenciais tecnicos traduzidos em valor;
- comparacao simples entre 3 planos;
- CTA coerente com o nivel do plano.

#### 2. Cadastro

Recomendacao:

- A1 leva para cadastro direto;
- Profissional pode levar para cadastro ou demonstracao;
- Enterprise leva para contato comercial/demonstracao.

#### 3. Ativacao

A ativacao deve aproveitar o fluxo ja existente de onboarding e configuracao inicial:

- criacao da conta;
- configuracao do ambiente;
- definicao de dados basicos;
- entrada no dashboard.

#### 4. Primeiro valor percebido

O sistema precisa mostrar valor rapido:

- A1: criar primeira safra/unidade/operacao;
- Profissional: demonstrar integracao campo + estoque + financeiro;
- Enterprise: demonstrar governanca, escopo e trilha.

#### 5. Upgrade

Upgrade deve ser disparado por:

- banners de limite;
- CTA em billing;
- eventos de saturacao;
- recomendacao contextual por uso.

### 7.3 CTAs ideais por plano

| Plano | CTA principal | CTA secundario |
|---|---|---|
| `A1 Planejamento` | `Comecar gratis` ou `Comecar implantacao` | `Ver como funciona` |
| `Profissional` | `Ver demonstracao` | `Falar com comercial` |
| `Enterprise` | `Falar com especialista` | `Solicitar proposta` |

### 7.4 Conversao recomendada por plano

#### A1

- entrada por landing;
- cadastro direto;
- trial curto;
- onboarding guiado;
- conversao por ativacao e uso.

#### Profissional

- entrada por landing ou inside sales;
- demonstração curta ou trial seletivo;
- upgrade para plano pago com base em dor operacional concreta.

#### Enterprise

- entrada por vendas;
- call diagnostica;
- proposta;
- setup;
- ativacao assistida.

## 8. Risco de churn por plano

### 8.1 A1 Planejamento

**Risco:** alto.

**Motivos principais:**

- cliente ainda sem rotina estabelecida;
- compra por curiosidade ou impulso;
- baixo switching cost inicial;
- maturidade operacional menor.

**Mitigacao:**

- onboarding guiado;
- trial curto;
- ativacao de valor nos primeiros 3 dias;
- foco em primeira safra/unidade/operacao criada.

### 8.2 Profissional

**Risco:** medio.

**Motivos principais:**

- cliente exige retorno tangivel;
- se a integracao nao for percebida, pode ver o plano como "mais caro que o necessario";
- risco de uso parcial de modulos.

**Mitigacao:**

- demonstrar ledger unico, origem financeira e rastreabilidade;
- onboarding assistido opcional;
- relatorios de valor percebido;
- recomendacao de uso por rotina.

### 8.3 Enterprise

**Risco:** baixo para churn acidental, medio para churn politico/comercial.

**Motivos principais:**

- contratos maiores e maior inercia operacional;
- porem maior exigencia de entrega, SLA e relacionamento;
- risco concentrado em projeto, nao em usabilidade simples.

**Mitigacao:**

- discovery forte;
- escopo comercial claro;
- setup estruturado;
- acompanhamento executivo;
- governanca de conta.

## 9. Estrategia de pricing recomendada

### 9.1 Papel de cada plano no funil

| Plano | Papel |
|---|---|
| `A1 Planejamento` | aquisicao |
| `Profissional` | monetizacao principal |
| `Enterprise` | expansao de ticket |

### 9.2 Regra de comunicacao

Na comunicacao comercial:

- A1 precisa parecer simples e acionavel;
- Profissional precisa parecer o "plano certo" para quem quer operar de verdade;
- Enterprise precisa parecer serio, nao inflado.

### 9.3 Plano recomendado em destaque

O plano em destaque deve ser:

> **Profissional**

porque:

- e o melhor equilibrio de margem e valor percebido;
- traduz melhor os diferenciais do produto;
- evita posicionar o A1 como produto final para todos os perfis.

## 10. Recomendacao final

O modelo mais coerente com o estado atual do produto e:

- `A1 Planejamento`: **R$ 79/mês** ou **R$ 790/ano**
- `Profissional`: **R$ 249/mês** ou **R$ 2.490/ano**
- `Enterprise`: **a partir de R$ 990/mês** ou **a partir de R$ 9.900/ano**

Com operacao de conversao:

- A1 como porta de entrada real;
- Profissional como plano principal de upgrade e receita;
- Enterprise como venda consultiva com setup e discovery.

## 11. Referencias

- `docs/PRODUTO_SAAS_ESTRUTURA_COMERCIAL_STEP94.md`
- `docs/strategy/bundle-packages.md`
- `docs/ADMIN_SAAS_GUIA_IMPLEMENTACAO.md`
- `apps/web/src/app/onboarding/configurar/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/billing/page.tsx`
