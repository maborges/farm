# COFFEE-PILOT-02A — Auditoria de Planejamento Operacional (Primeira Safra)

**Data:** 06 de Julho de 2026
**Objetivo:** Auditar o arcabouço técnico referente à jornada do produtor no "Planejamento das Operações", avaliando a completude e viabilidade da execução real do Piloto do Café, sob as óticas de gestão agronômica, logística e financeira.

## 1. O que foi Auditado
Foram dissecadas as entidades do domínio de `tarefas` (`SafraTarefa`) e `operacoes` (`OperacaoAgricola`), além dos serviços de apoio (Cultivos e Safras), para avaliar se o AgroSaaS atende ao gerenciamento de um planejamento diário (tático).

**Classificação por Processo:**

- **Calendário Operacional / Cronograma:** `[EXISTE E ATENDE]` - Gerenciado perfeitamente pelo campo `data_prevista` e pela hierarquia temporal da tarefa.
- **Fases da Cultura / Operações Previstas:** `[EXISTE E ATENDE]` - Estruturas de faseamento e checklist integram-se organicamente via modelagem de `fase` nas tarefas e no domínio central da Safra.
- **Planejamento por Talhão / Área:** `[EXISTE E ATENDE]` - A estrutura aloca tarefas granulares apontando para `talhao_id` e calculando `area_ha`.
- **Insumos Previstos:** `[EXISTE PARCIALMENTE]` - O sistema registra intenções quantitativas ("dose estimada", "quantidade total kg"), **porém falta a ligação logístico-comercial.** O produtor não consegue apontar o `produto_id` exato do planejamento na tabela `safra_tarefas`. Sem o Produto associado, não há como prever esgotamento de estoque na semana.
- **Equipes Previstas (Operadores):** `[NÃO EXISTE]` - A `SafraTarefa` não dispõe da propriedade `operador_id` (existente apenas no momento da consolidação em `OperacaoAgricola`). Impossível alocar ou reservar agenda de pessoas no planejamento.
- **Máquinas / Implementos Previstos:** `[NÃO EXISTE]` - Idem ao anterior. Ausência de `maquina_id` impossibilita gestão de ocupação de maquinários e bloqueio de conflitos de agenda na fazenda.
- **Custos Previstos:** `[EXISTE PARCIALMENTE]` - O valor de `custo_estimado` é isolado e fixo. Como a plataforma não suporta um "Bill of Materials" (lista de materiais atrelada à tarefa), o cálculo financeiro é manual e não integrado à cadeia de custos do Sankhya antes da execução.
- **Metas de Produção:** `[EXISTE E ATENDE]` - Abordado no escopo global da `Safra` (`produtividade_meta_sc_ha`).

## 2. Experiência de Uso (UX) e Intuitividade
- **Excesso de campos / Complexidade:** O desenho é estritamente limpo e foca-se na agronômia. 
- **O Produtor entenderia?** Sim, como agenda agronômica. Não, como agenda tática. O produtor de café não planeja dizendo *"Pulverizar com 10L/ha"* (como o sistema exige). Ele planeja: *"Amanhã o João [Operador] pega o Trator Valtra [Máquina] com o RoundUp [Produto] e pulveriza o Talhão 3"*. 
- A ausência dos relacionamentos de "Pessoas", "Máquinas" e "Produtos" na intenção (`SafraTarefa`) quebra a naturalidade do planejamento D-5.

## 3. Matriz Final de GAPs e Integrações

| Processo | Situação | UX | Estoque | Financeiro | Custos | Campo | Recommendation | Prioridade |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Calendário/Fases** | EXISTE E ATENDE | Simples | N/A | N/A | N/A | Sim | Sim | Baixo |
| **Talhões/Área** | EXISTE E ATENDE | Simples | N/A | N/A | N/A | Sim | Sim | Baixo |
| **Insumos Previstos** | EXISTE PARCIALMENTE | Incompleto | FALTANTE | FALTANTE | Raso | N/A | Sim | **CRÍTICO** |
| **Equipes Previstas** | NÃO EXISTE | N/A | N/A | N/A | FALTANTE | N/A | N/A | **ALTO** |
| **Máquinas Previstas**| NÃO EXISTE | N/A | N/A | N/A | FALTANTE | N/A | N/A | **ALTO** |
| **Custos Previstos** | EXISTE PARCIALMENTE | Raso | N/A | N/A | Raso | N/A | N/A | MÉDIO |

## 4. Critério de Encerramento (Decisão de Piloto)

1. **O produtor consegue planejar operacionalmente uma safra completa?**
   **Não.** Ele consegue mapear o planejamento _agronômico_ intencional. O planejamento _logístico/operacional real_ é impossível (falta gestão de máquina, tratorista e insumo atrelado ao cronograma).

2. **Existe algum bloqueio crítico?**
   **Sim.** A falta de `produto_id` no planejamento anula qualquer proatividade do motor de integrações com o estoque (Sankhya) antes que o evento ocorra. O estoque irá furar no dia da operação real se o armazém não for municiado com antecedência.

3. **Quais gaps realmente impedem a execução?**
   É tecnicamente impossível montar um romaneio de serviço coerente sem estender as tabelas relacionadas à `SafraTarefa` (necessário adicionar dependência logísticas / lista de produtos ou atributos diretos para maquinário).

4. **Quais melhorias podem ficar para o pós-piloto?**
   Mecanismos complexos de custeio ABC pré-execução e controle de ociosidade de implementos pequenos. A reserva básica, no entanto, é inegociável.

5. **Recomendação final:**
   **GO COM RESSALVAS**
   A arquitetura está firme e coesa. Contudo, antes de abrirmos a funcionalidade na interface do produtor, a entidade `SafraTarefa` e seus schemas precisam **urgentemente** ser estendidos (ex: suporte opcional à previsão de `maquina_id`, `operador_id` e uma subtabela `SafraTarefaInsumo` ligada aos `produtos`), caso queiramos testar os pilares de Integração ERP. Se o piloto focar estritamente em Diário de Bordo pelo PWA, é possível avançar como está, assumindo a surpresa do estoque no D+0.
