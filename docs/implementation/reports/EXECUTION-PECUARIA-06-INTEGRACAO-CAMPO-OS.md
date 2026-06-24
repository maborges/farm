# EXECUTION-PECUARIA-06 — ANÁLISE DE INTEGRAÇÃO PECUÁRIA × CAMPO × ORDENS DE SERVIÇO

## 1. INVENTÁRIO ATUAL

### Campo
A análise do backend revelou que o módulo **Campo** possui excelente maturidade estrutural. O model `TarefaCampo` (localizado em `campo/models.py`) suporta totalmente a operação distribuída e móvel:
* **Suporte a Formulários Customizados:** Já suporta coleta estruturada de dados usando uma coluna `dados` do tipo `JSONB`.
* **Fluxo Offline:** Conta com IDs de cliente (`client_id`), timestamps locais para mitigação de conflitos, geolocalização (`latitude`, `longitude`) e sincronização via tombstones (`SyncTombstone`).
* **Estrutura de Execução:** Possui coluna `module` que **já aceita o valor `'pecuaria'`**, indicando preparo prévio, e `origem` (`MANUAL` ou `PROGRAMADA`).
* **Execução em Lote:** É possível registrar múltiplos dados no JSON de uma única tarefa.

### Ordens de Serviço (OS)
O código demonstrou que no contexto do AgroSaaS, a entidade "Ordem de Serviço" (`OrdemServico` em `operacional/models/frota.py`) é **exclusiva para a Oficina/Manutenção de Frota** (vincula a horímetros, planos de manutenção e mecânicos). 
* **Resposta:** *Não existe "Ordem de Serviço" para manejo zootécnico.* Na agricultura, o equivalente a uma OS é a `Tarefa` agrícola (planejamento) que se torna uma `OperacaoAgricola` (execução). Para a pecuária, a execução a campo deve ser modelada via **Campo (`TarefaCampo`)**, e não via OS de Oficina.

### Equipes e Operadores
A vinculação de quem realiza a operação no campo já está estruturada:
* Em `TarefaCampo`, existe um vínculo direto com o `operador_id` e o `user_id`, além de rastreabilidade do dispositivo físico usado (`dispositivo_id`).

### EventoAnimal
* O model `EventoAnimal` atua como um ledger (append-only).
* Ele **já suporta** tipos de evento como `PESAGEM`, com uma coluna nativa `peso_kg`.
* Ele também possui `responsavel_id` (o usuário do sistema), mas atualmente não há uma FK forte ligando um `EventoAnimal` à sua respectiva `TarefaCampo` ou `operador_id` de campo.
* Vários animais pesados geram 1 evento para cada animal. Não há forma de salvar em um evento só, o que está arquiteturalmente correto (cada animal tem sua timeline).

---

## 2. LIMITAÇÕES E RISCOS ENCONTRADOS

1. **Ausência de Vínculo (Rastreabilidade):** O `EventoAnimal` não tem uma coluna `tarefa_campo_id` ou `origem_id` que prove a partir de qual planejamento/tabela do Campo a pesagem foi originada.
2. **Conflito de Nomenclatura:** Chamar a execução da pecuária de "Ordem de Serviço" confundirá os usuários e a base de código, visto que OS é estritamente de Oficina. O correto é usar o paradigma de "Tarefa de Campo de Pecuária".
3. **Limitação de Operador:** Hoje o EventoAnimal salva o usuário (backoffice), mas carece do rastro do operador real de campo.

---

## 3. COMPARAÇÃO DE CENÁRIOS OPERACIONAIS

### Cenário A: Lançamento Direto na Pecuária (Sem App de Campo)
* **Vantagens:** Mais rápido e simples para desenvolver agora. Sem preocupações com filas ou sincronização assíncrona.
* **Desvantagens:** Interfere no trabalho real. Um peão no curral não tem internet, nem usa interface web complexa. Gera duplicação, já que o peão anota no papel e o assistente digita no backoffice, criando um processo paralelo arcaico no sistema moderno.
* **Riscos:** Perda de dados, falta de georreferenciamento e incapacidade de medir a produtividade das equipes rurais.

### Cenário B: Execução Integrada (Via `TarefaCampo`)
* **Vantagens:** 100% offline-first. Uso do módulo Campo (já desenhado para currais sem internet). Rastreabilidade absoluta. Mede produtividade da equipe e operador. Reduz o fluxo para um só aplicativo móvel para o peão, seja para colher soja ou pesar boi.
* **Desvantagens:** Requer criar parsers assíncronos (Ex: o app sincroniza a TarefaCampo concluída -> o backend lê o JSONB -> gera 50 `EventoAnimal` automaticamente). Maior complexidade arquitetural inicial.

---

## 4. ARQUITETURA RECOMENDADA

A integração deve seguir inquestionavelmente o **Cenário B** (Via Módulo Campo e TarefaCampo). 

1. **Quem deve ser dono da execução da pesagem?** O módulo **Campo** (via `TarefaCampo`). O aplicativo offline é o "dono" da coleta.
2. **Quem deve ser dono do armazenamento?** O módulo **Pecuária** (via `EventoAnimal`). Após a sincronização, a Pecuária processa e detém o dado zootécnico final.
3. **Quem deve gerar EventoAnimal?** Um serviço reativo/assíncrono no Backend. Ao receber a finalização de uma `TarefaCampo` do tipo Pecuária, ele itera sobre os `dados` JSONB e faz um *bulk insert* em `EventoAnimal`.
4. **Quem deve atualizar GMD?** O próprio módulo de Pecuária (em cascata no mesmo momento do registro do `EventoAnimal`).
5. **Quem deve registrar operador responsável?** O Módulo **Campo** (a `TarefaCampo` retém o dispositivo e o `operador_id`). Recomenda-se adicionar um `tarefa_id` no `EventoAnimal` para ligar o GMD ao peão responsável pela pesagem.

---

## 5. OUTROS MANEJOS E ESCALABILIDADE

A beleza desta arquitetura está em sua escalabilidade. Ao resolver a mecânica de Pesagem usando a tríade `Planejamento de Manejo` -> `TarefaCampo (JSONB)` -> `EventoAnimal`, este exato mesmo fluxo cobrirá instantaneamente sem mudanças de infraestrutura:
- Vacinação (Muda o Type e os campos do JSON, gerando eventos `VACINACAO`)
- Inseminação (JSON com Reprodutor)
- Diagnóstico de Prenhez
- Transferência de Lotes

**Conclusão:** A arquitetura é totalmente agnóstica e reaproveitável, consolidando o AgroSaaS como ERP e evitando "puxadinhos" por tipo de manejo.

---

## 6. ROADMAP DE IMPLEMENTAÇÃO ESTRATÉGICA

**Fase 1: Conexão Estrutural Básica (Alta Prioridade, Baixo Risco)**
* **Ação:** Criar migrations adicionando a FK `tarefa_campo_id` (UUID, nullable) no model `EventoAnimal` em Pecuária e, se necessário, `operador_id`.
* **Benefício:** Permite rastreabilidade técnica exata antes do frontend entrar em cena.

**Fase 2: Motor de Processamento Reativo (Complexidade Média)**
* **Ação:** Desenvolver em `pecuaria/services` um `ManejoSyncService` que escute quando uma `TarefaCampo` de Pecuária ganha status `CONCLUIDA`. Ele lê os `dados` do formulário offline e materializa nos eventos finais (atualizando GMD ou subtraindo vacina do Estoque).
* **Dependência:** Contratos bem definidos dos payloads JSON no módulo Campo.

**Fase 3: Aplicativo de Campo e Interface Gerencial (Maior Esforço)**
* **Ação:** Disponibilizar no Backoffice web o Planejamento de Manejo (Gerar TarefasProgramadas de Pecuária) e no Frontend Móvel o Formulário Específico.
* **Risco Arquitetural Acabado:** Esta fase pode ser longa, porém perfeitamente isolada e não causará riscos de regressão no cálculo de GMD que já se encontra estável e funcional no backend de pecuária hoje.
