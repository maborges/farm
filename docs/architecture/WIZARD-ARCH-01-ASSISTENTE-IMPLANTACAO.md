# WIZARD-ARCH-01 — Assistente de Implantação Operacional do AgroSaaS

## 1. Visão geral

Este documento define a arquitetura oficial do Assistente de Implantação do AgroSaaS para a versão 1.0.

Pergunta que este documento responde:

**Qual é o papel oficial do Wizard de Implantação no AgroSaaS e como ele deve conduzir a implantação operacional da fazenda sem assumir responsabilidades de identidade, billing, tenant ou equipe obrigatória?**

Resposta objetiva:

- o Wizard é o assistente oficial de implantação operacional da fazenda;
- ele começa depois de `Usuario`, `Tenant`, `Assinatura`, `Owner/Admin` e onboarding mínimo já existirem;
- ele organiza a sequência operacional da implantação até o go-live e estabilização inicial;
- ele não cria identidade, não cria billing, não cria tenant e não substitui o fluxo de convites;
- ele trata a equipe como trilha opcional e progressiva;
- ele deve ser idempotente, retomável e compatível com implantação manual e piloto controlado.

## 2. Papel oficial do Wizard

O Wizard existe para conduzir a implantação operacional da fazenda, não para provisionar a conta SaaS.

Arquitetura oficial:

```text
Auth / Cadastro / Billing / Tenant Provisioning
  ↓
Onboarding mínimo
  ↓
Wizard de Implantação Operacional
  ↓
Go-live assistido
  ↓
Estabilização
```

Definição oficial:

- o Wizard é a camada de coordenação da implantação;
- ele organiza dependências, etapas, checklist, retomada e critérios de prontidão;
- ele deve reutilizar as arquiteturas oficiais já aprovadas em `PERSON-ARCH-01`, `ECONOMIC-ARCH-01`, `TERRITORY-ARCH-01`, `PRODUCT-ARCH-01`, `EVENTS-ARCH-01` e `PILOT-ARCH-01`.

## 3. Responsabilidades

Responsabilidades oficiais do Wizard:

- diagnosticar o tipo de operação do cliente;
- conduzir a confirmação da primeira `UnidadeProdutiva`;
- guiar a criação da estrutura territorial mínima;
- orientar cadastros mestres mínimos por módulo contratado;
- conduzir parâmetros iniciais de agricultura, pecuária, estoque e financeiro;
- orquestrar checklist de prontidão;
- registrar progresso por etapas;
- permitir pausa, retomada e avanço incremental;
- consolidar critérios mínimos de go-live;
- apoiar operação assistida e estabilização inicial.

## 4. Não-responsabilidades

O Wizard não deve assumir responsabilidades fora da implantação operacional.

Proibições oficiais:

- não criar `Usuario`;
- não criar `Pessoa`;
- não criar credenciais, senha, MFA ou identidade de autenticação;
- não criar `Tenant`;
- não criar `Assinatura`;
- não criar `TenantUsuario`;
- não gerenciar billing;
- não conceder permissões globais;
- não substituir convites ou gestão de equipe;
- não exigir equipe completa para concluir a implantação mínima;
- não redefinir arquitetura canônica de domínios já aprovados.

## 5. Separação oficial entre Wizard e outros domínios

### 5.1 Relação com Auth

`Auth` continua responsável por:

- identidade global;
- autenticação;
- sessão;
- credenciais;
- recuperação de acesso;
- contexto do usuário.

Regra oficial:

- o Wizard nunca cria identidade;
- o Wizard assume que o usuário já existe e já está autenticado.

### 5.2 Relação com Billing

`Billing` continua responsável por:

- plano;
- assinatura;
- trial;
- cobrança;
- direito de uso do ambiente.

Regra oficial:

- o Wizard não cria nem altera assinatura como função principal;
- a assinatura libera direito de uso;
- o Wizard prepara a operação.

### 5.3 Relação com Onboarding

`Onboarding` continua responsável por:

- provisionamento inicial;
- configuração mínima do tenant;
- gate técnico inicial já existente;
- compatibilidade com o fluxo atual de entrada.

Regra oficial:

- o Wizard começa depois do onboarding mínimo;
- o Wizard não substitui o onboarding atual sem plano explícito de migração;
- enquanto coexistirem, o Wizard deve respeitar os gates já definidos em `PILOT-GOV-01`.

### 5.4 Relação com Tenant

`Tenant` é pré-requisito do Wizard.

Regra oficial:

- o Wizard não cria nem duplica tenant;
- o Wizard opera dentro de um tenant já existente e ativo.

### 5.5 Relação com UnidadeProdutiva

`UnidadeProdutiva` é a âncora operacional mínima do Wizard.

Regra oficial:

- o Wizard pode conduzir a confirmação, criação ou parametrização da primeira `UnidadeProdutiva`, quando isso fizer parte da implantação operacional;
- o Wizard não redefine a natureza canônica de `UnidadeProdutiva` como unidade operacional mínima da plataforma.

### 5.6 Relação com equipe

A equipe não é a implantação; a equipe é uma trilha adjacente.

Regra oficial:

- apenas `Owner/Admin` é obrigatório para implantação mínima;
- equipe operacional é opcional e progressiva;
- convites continuam sendo o fluxo canônico de entrada de equipe;
- o Wizard pode orientar a inclusão de equipe, mas não deve bloquear o go-live mínimo por ausência dela.

## 6. Pré-requisitos para início do Wizard

O Wizard só pode iniciar quando já existirem:

- `Usuario` válido;
- `Tenant` ativo;
- `Assinatura` ou direito de uso ativo;
- vínculo `TenantUsuario` com `Owner/Admin`;
- autenticação e contexto válidos;
- onboarding mínimo/provisionamento inicial concluído ou apto para continuidade.

Pré-condições operacionais mínimas:

- tenant acessível;
- owner ativo;
- contexto operacional selecionável;
- ausência de bloqueio comercial ou de acesso.

## 7. O que o Wizard pode criar ou configurar

Dentro do seu escopo, o Wizard pode conduzir e configurar:

- `UnidadeProdutiva`;
- dados operacionais da fazenda;
- estrutura territorial mínima;
- `AreaRural`;
- talhões via `AreaRural.tipo = TALHAO`;
- piquetes/pastagens via `AreaRural.tipo = PIQUETE`;
- infraestrutura mínima;
- atividades produtivas habilitadas;
- cadastros mestres mínimos;
- parâmetros iniciais de agricultura;
- parâmetros iniciais de pecuária;
- parâmetros iniciais de estoque;
- parâmetros iniciais financeiros;
- depósitos;
- máquinas e equipamentos;
- operação assistida;
- checklist de go-live;
- plano inicial de estabilização.

Regra oficial:

- o Wizard só pode operar sobre entidades já definidas como canônicas pela arquitetura oficial;
- ele não pode inventar estruturas paralelas para “simplificar” a implantação.

## 8. O que o Wizard é proibido de criar ou configurar

O Wizard não pode criar ou orquestrar como responsabilidade própria:

- identidade da plataforma;
- contas duplicadas;
- equipe obrigatória;
- tenant paralelo;
- assinatura paralela;
- RBAC global novo fora dos fluxos oficiais;
- modelos territoriais paralelos;
- modelos econômicos paralelos;
- catálogos paralelos de produto, cultura ou commodity;
- mecanismos alternativos de go-live que ignorem os gates oficiais.

## 9. Estados oficiais do Wizard

Estados oficiais:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PAUSED`
- `READY_FOR_GO_LIVE`
- `GO_LIVE`
- `STABILIZATION`
- `COMPLETED`
- `CANCELLED`

Semântica oficial:

- `NOT_STARTED`: tenant elegível, implantação ainda não iniciada;
- `IN_PROGRESS`: implantação ativa com pelo menos uma etapa em execução;
- `PAUSED`: implantação interrompida voluntariamente ou por dependência não crítica;
- `READY_FOR_GO_LIVE`: critérios mínimos atingidos, aguardando ativação assistida;
- `GO_LIVE`: operação inicial liberada e acompanhada;
- `STABILIZATION`: período assistido pós-go-live;
- `COMPLETED`: implantação encerrada com sucesso e critérios de estabilização concluídos;
- `CANCELLED`: implantação abandonada, substituída ou invalidada.

## 10. Modelo de retomada e idempotência

O Wizard deve ser retomável por definição.

Normas oficiais:

- cada etapa deve ter status persistível e reexecutável;
- reabrir uma etapa não deve duplicar cadastros já concluídos;
- o Wizard deve operar por verificação de estado atual, não por suposição de execução linear;
- o avanço deve depender de evidência de dados já existentes, não apenas de marcação manual;
- etapas parcialmente concluídas devem poder ser retomadas sem reiniciar toda a implantação.

Modelo oficial:

```text
Diagnosticar estado atual
  ↓
Validar pré-condições da etapa
  ↓
Executar ou confirmar etapa
  ↓
Persistir progresso
  ↓
Liberar próxima etapa elegível
```

Princípio:

- Wizard bom é idempotente por leitura do estado real do tenant.

## 11. Etapas canônicas do Wizard

Sequência oficial sugerida:

1. Boas-vindas e diagnóstico inicial
2. Confirmação da `UnidadeProdutiva`
3. Estrutura territorial mínima
4. Atividades produtivas
5. Agricultura, se aplicável
6. Pecuária, se aplicável
7. Estoque mínimo
8. Financeiro mínimo
9. Máquinas e equipamentos, se aplicável
10. Equipe, opcional
11. Revisão da implantação
12. Go-live assistido
13. Estabilização

## 12. Dependências e critérios de avanço por etapa

### 12.1 Boas-vindas e diagnóstico inicial

Objetivo:

- identificar tipo de cliente, módulos contratados e escopo da onda inicial.

Depende de:

- tenant ativo;
- owner autenticado;
- assinatura válida.

Avança quando:

- escopo operacional inicial estiver definido.

### 12.2 Confirmação da UnidadeProdutiva

Objetivo:

- garantir pelo menos uma `UnidadeProdutiva` ativa.

Depende de:

- tenant;
- owner;
- direito de uso ativo.

Avança quando:

- existir pelo menos uma `UnidadeProdutiva` ativa e apta ao contexto operacional.

### 12.3 Estrutura territorial mínima

Objetivo:

- garantir base espacial compatível com o módulo contratado.

Depende de:

- `UnidadeProdutiva`;
- arquitetura oficial de `AreaRural`.

Avança quando:

- existir árvore mínima de áreas;
- houver talhão para operação agrícola, se agricultura estiver habilitada;
- houver piquete/pastagem para operação pecuária, se pecuária estiver habilitada.

### 12.4 Atividades produtivas

Objetivo:

- definir quais trilhas operacionais serão ativadas.

Depende de:

- diagnóstico inicial;
- estrutura territorial mínima.

Avança quando:

- agricultura, pecuária, estoque, financeiro e frota tiverem escopo inicial definido.

### 12.5 Agricultura

Objetivo:

- preparar a operação agrícola mínima.

Depende de:

- `ProdutoCultura`;
- território agrícola;
- safra/cultivo, quando aplicável.

Avança quando:

- existirem cadastros mínimos de cultura;
- existir contexto mínimo de safra/cultivo/área para a onda inicial.

### 12.6 Pecuária

Objetivo:

- preparar a operação pecuária mínima.

Depende de:

- território pecuário;
- lotes/animais, quando fizer parte do escopo inicial.

Avança quando:

- existirem áreas/ piquetes mínimos;
- houver estrutura pecuária mínima compatível com a operação contratada.

### 12.7 Estoque mínimo

Objetivo:

- garantir catálogo e estrutura de estoque essenciais.

Depende de:

- `Produto`;
- depósito;
- política de estoque inicial.

Avança quando:

- existir ao menos um depósito ativo;
- catálogo mínimo de produtos estiver carregado;
- saldo inicial, se exigido, estiver consistente.

### 12.8 Financeiro mínimo

Objetivo:

- habilitar operação financeira mínima sem criar arquitetura econômica paralela.

Depende de:

- `PlanoConta`;
- parâmetros financeiros;
- regras mínimas de `Receita`, `Despesa` e `CostAllocation`.

Avança quando:

- plano de contas mínimo estiver disponível;
- parâmetros mínimos estiverem configurados;
- o cliente puder iniciar `Receita` e `Despesa` sem romper a arquitetura oficial.

### 12.9 Máquinas e equipamentos

Objetivo:

- preparar a camada de ativos operacionais, se houver uso de frota ou manutenção.

Depende de:

- `UnidadeProdutiva`;
- equipamento e, quando aplicável, estoque/abastecimento.

Avança quando:

- ativos críticos estiverem cadastrados.

### 12.10 Equipe opcional

Objetivo:

- orientar inclusão progressiva da equipe sem transformar isso em gate estrutural.

Depende de:

- owner ativo;
- fluxo de convites disponível.

Avança quando:

- o tenant decidir encerrar a etapa opcional ou tiver incorporado o grupo mínimo desejado.

Regra oficial:

- ausência de equipe adicional não impede conclusão da implantação mínima.

### 12.11 Revisão da implantação

Objetivo:

- consolidar pendências, riscos e prontidão operacional.

Depende de:

- execução das trilhas relevantes do escopo.

Avança quando:

- checklist mínimo estiver concluído;
- bloqueios críticos estiverem resolvidos ou explicitamente aceitos.

### 12.12 Go-live assistido

Objetivo:

- liberar a primeira operação real com acompanhamento.

Depende de:

- estado `READY_FOR_GO_LIVE`.

Avança quando:

- operação inicial estiver liberada;
- monitoramento inicial estiver ativo;
- não existirem bloqueios críticos abertos.

### 12.13 Estabilização

Objetivo:

- acompanhar os primeiros ciclos reais de uso.

Depende de:

- go-live executado.

Avança quando:

- primeiros fluxos críticos estiverem operando com consistência;
- pendências remanescentes estiverem classificadas fora do caminho crítico.

## 13. Critérios mínimos de go-live

Critérios oficiais:

- `Tenant` ativo;
- `Owner/Admin` ativo;
- pelo menos uma `UnidadeProdutiva` ativa;
- estrutura operacional mínima compatível com o módulo contratado;
- checklist mínimo concluído;
- ausência de bloqueios críticos.

Leitura oficial:

- go-live é uma decisão de prontidão operacional;
- não é sinônimo de billing ativo apenas;
- não exige equipe completa;
- não exige maturidade total de todos os módulos.

## 14. Critérios de conclusão do Wizard

O Wizard pode ser considerado concluído quando:

- a implantação mínima entrou em go-live;
- a estabilização inicial foi executada;
- os bloqueios críticos foram encerrados, mitigados ou formalmente aceitos;
- a operação básica do escopo contratado funciona de forma consistente;
- o tenant pode evoluir por operação normal, sem depender do Wizard para existir.

## 15. Relação com piloto controlado

O Wizard é a espinha dorsal recomendada do piloto controlado.

Funções no piloto:

- padronizar sequência de implantação;
- reduzir variação entre clientes;
- tornar dependências auditáveis;
- tornar o progresso mensurável;
- reduzir o risco de operação incompleta.

Regra oficial:

- piloto controlado deve preferir a mesma sequência canônica do Wizard;
- qualquer exceção deve ser tratada como compatibilidade temporária, não como nova arquitetura.

## 16. Relação com implantação manual

O Wizard não elimina implantação manual.

Regra oficial:

- implantação manual, consultoria e parceiros devem seguir a mesma arquitetura do Wizard;
- o Wizard é a expressão guiada da arquitetura oficial, não uma lógica paralela.

## 17. Riscos arquiteturais

Riscos que o Wizard deve evitar:

- virar novo onboarding comercial;
- recriar auth ou billing por conveniência;
- transformar equipe em pré-requisito obrigatório;
- criar atalhos com entidades não canônicas;
- considerar “configuração preenchida” como sinônimo de “operação pronta”;
- ignorar os gates mínimos já definidos em `PILOT-ARCH-01`, `PILOT-GOV-01` e `PILOT-GOV-01B`;
- duplicar lógica de domínio em vez de consumir serviços e fluxos oficiais.

## 18. Decisões oficiais

Decisões normativas:

- o Wizard é exclusivamente o assistente de implantação operacional da fazenda;
- o Wizard começa depois de `Usuario`, `Tenant`, `Assinatura`, `Owner/Admin` e onboarding mínimo;
- o Wizard não cria identidade nem billing;
- o Wizard não exige equipe completa;
- o Wizard trata `Owner/Admin` como único ator obrigatório da implantação mínima;
- o Wizard deve operar por etapas retomáveis e idempotentes;
- o Wizard deve ser compatível com implantação manual e piloto controlado;
- o Wizard deve reutilizar apenas entidades canônicas já aprovadas.

## 19. Recomendações para WIZARD-GOV-01

Guardrails mínimos recomendados:

- validar que o Wizard não cria `Usuario`, `Tenant`, `Assinatura` ou `TenantUsuario`;
- validar que o Wizard exige `Owner/Admin` e `Tenant` ativo antes de iniciar;
- validar que o Wizard não considera equipe completa como pré-requisito;
- validar que `UnidadeProdutiva` continua sendo o gate operacional mínimo;
- validar que trilhas agrícola e pecuária respeitam `AreaRural`, `Talhão`, `Piquete` e `ProductionUnit` canônicos;
- validar que o Wizard não cria catálogos paralelos de `Produto`, `ProdutoCultura`, `Commodity` ou estruturas econômicas paralelas;
- validar que estados do Wizard permaneçam estáveis e retomáveis;
- validar que go-live só ocorra com checklist mínimo e sem bloqueio crítico.

## 20. Resposta final

Após este documento, o AgroSaaS passa a ter uma arquitetura oficial clara para o Assistente de Implantação: o Wizard é a camada de coordenação da implantação operacional da fazenda, posterior ao provisionamento comercial e à identidade, compatível com piloto controlado, centrado em `UnidadeProdutiva` e estrutura operacional mínima, com equipe opcional e evolução progressiva até go-live e estabilização.
