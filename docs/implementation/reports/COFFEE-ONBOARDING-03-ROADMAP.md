# COFFEE-ONBOARDING-03: Roadmap de Evolução do Onboarding

## FASE 1: Pré-piloto (Foco Imediato)

**Objetivo:** Reduzir drasticamente o *Time to First Value* para viabilizar o primeiro piloto com produtores de café usuários de Sankhya. Sem alterar a arquitetura.

**Ações:**
1. Depreciar e substituir o formulário técnico (`configurar/page.tsx`) pela UI "Intent-Based" de 3 passos (Cultura, ERP, Objetivos).
2. Ajustar o endpoint de onboarding para inferir Fuso Horário (do navegador), Moeda (BRL) e Unidade (HA).
3. Conectar a escolha da cultura "Café" à chamada do serviço de `PhaseTemplates` já existente.
4. Conectar a escolha de "Sankhya" ao disparo da `SyncErpTask` para popular dados imediatamente.

**Entregável:** O produtor loga, dá 3 cliques, e cai num dashboard com dados integrados e cultura parametrizada.

---

## FASE 2: Pós-piloto

**Objetivo:** Expansão da inteligência de implantação via Templates Avançados e Assistentes contextuais.

**Ações:**
1. **Templates Inteligentes Expandidos:** Criar predefinições exatas para Soja, Milho e Pecuária, incluindo ciclos biológicos completos.
2. **Perfis por Cultura:** O `Alert Engine` e `Recommendation Engine` ajustam automaticamente seus *thresholds* (ex: limite de custo aceitável para café irrigado vs sequeiro).
3. **Assistentes de Dados Faltantes:** Em vez de forçar preenchimento inicial, usar notificações ("Toasts" e "In-App Cards") recomendando que o usuário preencha o CAR ou NIRF em um momento tranquilo.

**Entregável:** A plataforma passa a "conhecer" profundamente a dor do produtor de cada cultura específica, ajustando a interface inteira para aquele nicho (Adaptive UI).

---

## FASE 3: Longo prazo

**Objetivo:** Onboarding Hiper-Personalizado impulsionado por IA e Análise Comportamental.

**Ações:**
1. **Onboarding Adaptativo (IA):** Integração com o *Behavioral Engine*. Se o produtor demonstrar um perfil analítico severo na primeira semana, o sistema libera automaticamente *Dashboards Enterprise* e oculta dicas básicas.
2. **Personalização Automática:** Os módulos ativados mudam conforme o comportamento. Se o produtor só acessa Financeiro e ERP, o AgroSaaS colapsa as rotas de "Monitoramento NDVI" para limpar a UI.
3. **Copiloto de Setup:** A IA ajuda ativamente a reconciliar dados conflitantes vindos do Sankhya durante os primeiros dias de uso, sem depender do suporte humano.

**Entregável:** Um software que se molda dinamicamente ao nível de maturidade digital e perfil de risco do produtor, maximizando a retenção e a facilidade de uso.
