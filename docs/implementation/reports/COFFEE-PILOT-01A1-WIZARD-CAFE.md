# Auditoria COFFEE-PILOT-01A.1 — Wizard de Implantação e Onboarding (Foco Café)

## Objetivo
Análise de redução de atrito (Time to Value) entre o primeiro login e a primeira safra operacional para um produtor de café que utiliza Sankhya.

---

## 1. Análise de Informações e Fluxo

### 1. Quais informações são realmente obrigatórias?
Para inicializar o sistema de forma íntegra, precisamos apenas de:
- Identidade do Tenant e Owner (já resolvido na etapa de registro).
- Ano Agrícola (para balizar as safras).
- Cultura alvo (para instanciar painéis e módulos específicos, como Beneficiamento).

### 2. Quais podem ser inferidas?
- **Fuso Horário:** Pode ser inferido diretamente do navegador (`Intl.DateTimeFormat().resolvedOptions().timeZone`).
- **Moeda:** Pode ser inferida como BRL (com suporte a USD para exportação configurado posteriormente em Settings).
- **Unidade de Área:** O padrão `HA` (Hectare) atende 99% dos relatórios iniciais, dispensando a pergunta obrigatória sobre Alqueires.

### 3. Quais podem ser preenchidas automaticamente?
- **Categorias Padrão:** Não é necessário perguntar se o usuário quer as categorias padrão. O sistema deve carregar uma estrutura de contas otimizada por default.
- **Ano Agrícola (Limites):** Sabendo que a safra no Brasil geralmente roda de Julho a Junho, o sistema pode pré-preencher essas datas.

### 4. Quais podem vir de templates da cultura Café?
Ao selecionar "Café" como cultura primária no início:
- Criação automática do **Calendário Fenológico** do café.
- Habilitação automática do submódulo de **Beneficiamento** (exclusivo do café).
- Árvore de operações base pré-carregada (Tratos Culturais, Arruação, Colheita, Secagem).
- Injeção das categorias padrão focadas na cultura (ex: Insumos Foliares, Mão de obra safrista).

### 5. Quais podem ser postergadas para depois do Go-Live?
- **Dados Cartoriais e Fundiários (CAR, NIRF, INCRA):** Apenas o polígono operacional (Talhões) é necessário para planejar a safra e custos. A formalidade de Imóveis Rurais pode ser preenchida sob demanda.
- **Configurações Regionais Finas:** Fuso horário, moeda secundária, conversão para alqueires.
- **Estruturas Complexas de Máquinas e Depósitos:** Pode iniciar com um "Depósito Geral" e "Frota Padrão" gerados automaticamente, que o produtor refina depois.

### 6. Quais telas podem ser unificadas?
As atuais 5 etapas presentes no frontend (`apps/web/src/app/onboarding/configurar/page.tsx`):
1. Ano Agrícola
2. Unidade de Área
3. Fuso e Moeda
4. Categorias Padrão
5. Revisão

**Unificação:** Todas essas telas podem ser unificadas em uma **única tela de Setup de Perfil** (ex: "Qual a sua cultura principal?" e "Qual ERP você utiliza?").

### 7. Quais passos podem ser eliminados?
Podem ser **eliminados do onboarding** os passos:
- Passo 2 (Unidade de Área)
- Passo 3 (Fuso e Moeda)
- Passo 4 (Categorias Padrão)
- Passo 5 (Revisão)

Eles geram atrito cognitivo em perguntas cujas respostas são 95% previsíveis. Esses campos devem ir para a rota estática de `/settings`.

### 8. Qual seria o fluxo ideal para um produtor de café exportador utilizando Sankhya?
1. **Login/Registro Inicial.**
2. **Setup One-Click (Wizard):** O usuário seleciona sua cultura matriz ("Café") e assinala que usa ERP ("Sankhya").
3. **Integração Imediata (Gateway-first):** O sistema exibe um painel de sync que puxa automaticamente do Sankhya:
   - Propriedades (Centros de Custo)
   - Talhões
   - Plano de Contas (Financeiro)
   - Insumos/Estoque
4. **Aplicação do Template:** O AgroSaaS aplica o *Coffee Template* por cima da estrutura importada, ativando módulos preditivos, IA e Beneficiamento.
5. **Dashboard Pronto:** O produtor cai no Dashboard da Safra já com dados reais do seu ERP, sem ter digitado nenhum cadastro manual.

---

## 2. Métricas e Resumo Executivo

- **Tempo estimado de implantação atual:** ~15 a 25 minutos (Passar pelos 5 steps + criar Propriedade + criar Safra + configurar categorias manualmente).
- **Tempo estimado após otimização:** < 3 minutos (Login -> Conectar Sankhya -> Template Aplicado).
- **Quantidade atual de passos:** 5 passos no Wizard + múltiplas telas de cadastros manuais (Propriedade, Safra, etc).
- **Quantidade ideal de passos:** 2 passos no Wizard (Cultura + Integração ERP). Todo o resto deve vir de templates ou da sincronização inicial (Gateway-first).

## Recomendação Final

**GO PARA REATORAÇÃO DO ONBOARDING.**
Para garantir o sucesso do piloto do café com clientes enterprise (usuários de Sankhya), o onboarding atual é excessivamente focado em configurações de sistema genéricas (Fuso, Área) e peca ao não aproveitar o contexto agrícola. A recomendação é substituir o wizard de 5 passos genéricos por um fluxo focado em **Cultura + ERP**, importando massivamente a fundação via integração (Sankhya) e complementando o comportamento via *PhaseTemplates* do café. O usuário deve cair no sistema vendo sua fazenda, não uma tela em branco.
