# AUDIT-BUSINESS-03 — Estratégia de Qualidade e Classificação

## Resumo Executivo e Valor Estratégico

O **Motor de Qualidade Multicultura** é o primeiro domínio estratégico transversal do AgroSaaS que transcende a "gestão de fazenda" e entra no core business de "Originação e Trading". 
Ao implementar um modelo genérico baseado em `QualityProtocol` e `QualityAdjustment`, o AgroSaaS passa a ser capaz de processar romaneios de Soja (com desconto de umidade), avaliar lotes de Café (com prêmios de pontuação SCA) e classificar romaneios de Abate de Gado (com rendimento de carcaça) utilizando **exatamente a mesma base de código e banco de dados**.

Isso reduz drasticamente a manutenção arquitetural e aumenta exponencialmente o mercado endereçável do produto (TAM - Total Addressable Market).

---

## 1. Estratégia de Monetização

O módulo de qualidade gera um valor tangível imediato para o cliente, pois evita perdas financeiras (pagar por água/umidade) e viabiliza a captura de prêmios (cafés/cacaus especiais). A precificação deve refletir esse valor:

### 🥉 Básico (Tier 1)
- **Escopo:** Avaliação puramente informativa e Caderno de Campo.
- **Funcionalidades:** 
  - Cadastro manual de Laudos no Romaneio.
  - Campos abertos sem motor de cálculo automático.
- **Público:** Pequeno produtor que apenas guarda o laudo entregue pela cooperativa para histórico.

### 🥈 Profissional (Tier 2)
- **Escopo:** Automação de Descontos e Quebras Operacionais.
- **Funcionalidades:**
  - `QualityProtocol` ativo para Grãos (Soja/Milho).
  - Cálculo automático de `DISCOUNT_WEIGHT` (Desconto de peso por umidade e impureza no romaneio).
  - Cálculo automático de Taxa de Secagem/Limpeza.
  - Relatórios de rendimento por talhão.
- **Público:** Grandes produtores de grãos e pequenas cerealistas/algodoeiras.

### 🥇 Enterprise (Tier 3)
- **Escopo:** Modelos de Valorização Complexa, Qualidade Sensorial e Exportação.
- **Funcionalidades:**
  - `QualityProtocol` para Qualidade Sensorial (Café SCA, Cacau, HVI de Algodão).
  - Cálculo automático de `PREMIUM_FINANCIAL` (Prêmios e Ágios).
  - Bloqueios sistêmicos (Lotes reprovados não podem ser embarcados/faturados).
  - Tabela dinâmica de descontos (Construtor de fórmulas).
  - APIs para integração com Classificadores Digitais e IoT.
- **Público:** Exportadoras de Café, Trading de Soja, Frigoríficos, Cooperativas Gigantes.

---

## 2. Roadmap de Implementação

Para minimizar riscos e gerar valor rápido, a construção do Domínio de Qualidade deve seguir o roadmap abaixo:

### 🚀 MVP (Minimum Viable Product)
**Foco:** Resolver a dor do Romaneio e do Produtor de Grãos.
- **Entidades:** Criação das tabelas `QualityProtocol`, `QualityCriterion`, `QualityReport`, `QualityResult`.
- **Funcionalidade:** Permite criar um protocolo "Soja 14%", cadastrar os limites, e ao salvar um Romaneio, o usuário digita a umidade lida e o sistema salva o Laudo.
- **Faltante no MVP:** O sistema ainda não recalcula automaticamente o peso financeiro. O usuário anota o desconto na mão.

### ⚡ V2 (Motor de Cálculo Físico)
**Foco:** Automação de Quebra/Desconto de Peso (O Core da Cerealista).
- **Entidades:** Criação da tabela/entidade `QualityAdjustment`.
- **Funcionalidade:** O motor de qualidade lê o laudo (ex: Umidade 16%) e injeta no Romaneio um evento de Quebra (`DISCOUNT_WEIGHT`).
- **Integração:** O módulo Financeiro passa a pagar o produtor/fornecedor apenas pelo "Peso Líquido Comercial" e não pelo Peso Bruto.
- **Integração de Estoque:** O sistema impede mistura de estoques com qualidades incompatíveis (ex: Soja Ardida com Soja Padrão).

### 🌟 V3 (Motor Financeiro e Sensorial - Multicultura Total)
**Foco:** Agregações de Prêmio, Exportadoras e Pecuária.
- **Funcionalidade:** Suporte nativo a Enum e Strings (Ex: "Bebida Dura").
- **Integração Financeira:** O motor é capaz de gerar Contas a Pagar suplementares (Ágios e Prêmios de Qualidade) baseado na nota SCA de um café.
- **Integração Pecuária:** Suporte a laudos de frigorífico pós-abate (Rendimento de Carcaça) aplicando ajustes retrospectivos no romaneio de saída de gado vivo.
- **Rastreabilidade:** Exportação do Lote com o Laudo anexo via QRCode (Bean to Cup).
