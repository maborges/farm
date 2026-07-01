# WIZARD-DOMAIN-01 — Modelo Canônico de Dados da Implantação Operacional

## 1. Visão geral

Este documento define o modelo canônico de dados que sustentará o Assistente de Implantação Operacional do AgroSaaS.

Pergunta central:

**Quais entidades oficiais devem representar a implantação operacional, suas etapas, checklist, pendências, histórico, progresso e critérios de go-live, sem misturar Wizard com Auth, Billing, Onboarding, Tenant provisioning ou gestão de equipe?**

Resposta objetiva:

- a implantação operacional deve ser representada por um agregado principal `ImplantacaoOperacional`;
- as etapas canônicas do Wizard devem ser registradas em `ImplantacaoEtapa`;
- itens verificáveis de avanço e go-live devem existir em `ImplantacaoChecklistItem`;
- riscos, bloqueios e pendências devem existir em `ImplantacaoPendencia`;
- toda transição material de estado deve ser auditada em `ImplantacaoHistorico`;
- o modelo deve ser multi-tenant, idempotente, retomável e compatível com execução manual e assistida.

## 2. Objetivos do modelo

Objetivos oficiais:

- representar uma implantação operacional ativa de um tenant;
- suportar progresso por etapas;
- suportar checklist derivado do estado real do tenant;
- suportar pausa, retomada, bloqueio e estabilização;
- impedir duplicação de implantação ativa;
- permitir auditoria completa;
- permitir go-live controlado com critérios objetivos;
- separar explicitamente Wizard de Auth, Billing, Onboarding e Equipe;
- preparar o terreno para `WIZARD-GOV-01` e futura implementação.

## 3. Princípios arquiteturais

Princípios obrigatórios:

- uma implantação pertence a um `Tenant`;
- `Owner/Admin` é ator responsável, não entidade criada pelo Wizard;
- `UnidadeProdutiva` é a âncora operacional mínima;
- checklist deve ser derivado do estado real sempre que possível;
- conclusão manual não pode mascarar ausência de dados obrigatórios;
- equipe adicional nunca é pré-requisito estrutural do go-live mínimo;
- o modelo deve preferir confirmação por evidência em vez de marcação cega;
- a implantação deve ser retomável após interrupção, pausa ou erro;
- a mesma arquitetura deve servir para Wizard guiado e implantação manual assistida.

## 4. Agregado principal

### 4.1 ImplantacaoOperacional

`ImplantacaoOperacional` é a entidade canônica que representa uma execução de implantação operacional dentro de um tenant.

Função oficial:

- coordenar o ciclo de vida da implantação;
- apontar tenant, owner responsável e unidade produtiva principal;
- consolidar status global, etapa atual, progresso e marcos do go-live;
- servir de raiz agregadora para etapas, checklist, pendências e histórico.

Campos conceituais mínimos:

| Campo | Tipo conceitual | Regra |
| --- | --- | --- |
| `id` | identificador único | identidade da implantação |
| `tenant_id` | FK lógica | obrigatório |
| `unidade_produtiva_id` | FK lógica opcional | opcional no início, obrigatório antes do go-live |
| `owner_usuario_id` | FK lógica | ator responsável principal |
| `status` | enum | estado global da implantação |
| `etapa_atual` | código canônico | etapa corrente do fluxo |
| `percentual_progresso` | número de 0 a 100 | progresso consolidado |
| `modo_implantacao` | enum conceitual | assistida, manual assistida, piloto, parceiro |
| `origem` | enum conceitual | novo assinante, upgrade de assinante, implantação interna, parceiro |
| `started_at` | timestamp | início efetivo |
| `paused_at` | timestamp opcional | pausa voluntária |
| `blocked_at` | timestamp opcional | bloqueio estrutural |
| `ready_for_go_live_at` | timestamp opcional | pronto para go-live |
| `go_live_at` | timestamp opcional | entrada em operação |
| `stabilization_started_at` | timestamp opcional | início da estabilização |
| `completed_at` | timestamp opcional | encerramento bem-sucedido |
| `cancelled_at` | timestamp opcional | encerramento cancelado |
| `created_at` | timestamp | auditoria |
| `updated_at` | timestamp | auditoria |

Campos conceituais recomendados:

- `diagnostico_inicial_snapshot`
- `escopo_modulos`
- `bloqueio_critico_aberto`
- `checklist_minimo_percentual`
- `go_live_aprovado_por_usuario_id`

## 5. Entidades auxiliares

### 5.1 ImplantacaoEtapa

`ImplantacaoEtapa` representa uma etapa canônica do Wizard dentro de uma implantação.

Função oficial:

- registrar o estado individual de cada etapa;
- permitir retomada granular;
- registrar snapshots contextuais por etapa;
- suportar etapas obrigatórias, opcionais e condicionais.

Campos conceituais mínimos:

| Campo | Tipo conceitual | Regra |
| --- | --- | --- |
| `id` | identificador único | identidade da etapa |
| `implantacao_id` | FK lógica | obrigatório |
| `codigo_etapa` | enum/código estável | canônico e imutável |
| `nome` | texto | legibilidade |
| `status` | enum | estado individual da etapa |
| `obrigatoria` | booleano | distingue etapa opcional |
| `ordem` | inteiro | ordenação oficial |
| `percentual_peso` | número | peso no progresso global |
| `started_at` | timestamp opcional | início |
| `completed_at` | timestamp opcional | conclusão |
| `skipped_at` | timestamp opcional | salto explícito |
| `blocked_at` | timestamp opcional | bloqueio específico |
| `dados_snapshot` | JSON conceitual | contexto da etapa |
| `observacoes` | texto opcional | comentário operacional |

Regra oficial:

- `Equipe` existe como etapa, mas com `obrigatoria = false`;
- etapas não aplicáveis ao escopo devem ser puláveis sem afetar os gates mínimos errados;
- conclusão da etapa deve depender de evidência verificável.

### 5.2 ImplantacaoChecklistItem

`ImplantacaoChecklistItem` representa um item verificável de avanço, revisão ou go-live.

Função oficial:

- transformar requisitos arquiteturais e operacionais em verificações explícitas;
- registrar se o item foi satisfeito automaticamente, manualmente confirmado ou ainda está pendente;
- suportar checklist por etapa e checklist global de go-live.

Campos conceituais mínimos:

| Campo | Tipo conceitual | Regra |
| --- | --- | --- |
| `id` | identificador único | identidade do item |
| `implantacao_id` | FK lógica | obrigatório |
| `etapa_id` | FK lógica opcional | opcional para item global |
| `codigo_item` | código estável | regra verificável |
| `descricao` | texto | explicação do item |
| `obrigatorio` | booleano | gate ou não gate |
| `status` | enum | pendente, atendido, dispensado, falhou |
| `severidade` | enum | informativo, atenção, crítico |
| `evidencia_tipo` | enum conceitual | automática, manual, documental, referencial |
| `evidencia_ref_id` | referência opcional | FK lógica/identificador externo |
| `checked_by_usuario_id` | FK lógica opcional | ator que confirmou |
| `checked_at` | timestamp opcional | momento da verificação |

Regra oficial:

- itens obrigatórios de go-live não podem ser “marcados como concluídos” sem evidência compatível;
- itens derivados do estado real devem ser recalculáveis;
- confirmação manual deve complementar, nunca substituir, requisito factual obrigatório.

### 5.3 ImplantacaoPendencia

`ImplantacaoPendencia` representa pendências, bloqueios, riscos ou tarefas manuais associadas à implantação.

Função oficial:

- tornar explícitos impedimentos de avanço;
- permitir classificação por severidade;
- distinguir risco observável de bloqueio efetivo;
- dar suporte a follow-up humano.

Campos conceituais mínimos:

| Campo | Tipo conceitual | Regra |
| --- | --- | --- |
| `id` | identificador único | identidade da pendência |
| `implantacao_id` | FK lógica | obrigatório |
| `etapa_id` | FK lógica opcional | quando a pendência for de etapa específica |
| `tipo` | enum | pendência, bloqueio, risco, tarefa manual |
| `severidade` | enum | baixa, média, alta, crítica |
| `status` | enum | aberta, em tratamento, resolvida, descartada |
| `titulo` | texto | resumo curto |
| `descricao` | texto | explicação operacional |
| `responsavel_usuario_id` | FK lógica opcional | dono da ação |
| `due_date` | data opcional | prazo operacional |
| `resolved_at` | timestamp opcional | encerramento |

Regra oficial:

- pendência crítica aberta impede `READY_FOR_GO_LIVE`;
- pendência de equipe não pode, por si só, impedir o go-live mínimo;
- bloqueios estruturais devem refletir o estado global da implantação.

### 5.4 ImplantacaoHistorico

`ImplantacaoHistorico` representa o log oficial de eventos e auditoria da implantação.

Função oficial:

- registrar transições materiais;
- suportar rastreabilidade;
- permitir explicação posterior de quem mudou o quê e por quê;
- sustentar governança e investigação.

Campos conceituais mínimos:

| Campo | Tipo conceitual | Regra |
| --- | --- | --- |
| `id` | identificador único | identidade do evento histórico |
| `implantacao_id` | FK lógica | obrigatório |
| `evento` | código estável | tipo de mudança |
| `status_anterior` | enum opcional | auditoria |
| `status_novo` | enum opcional | auditoria |
| `etapa_anterior` | código opcional | auditoria |
| `etapa_nova` | código opcional | auditoria |
| `ator_usuario_id` | FK lógica opcional | usuário ou ator de sistema |
| `payload_snapshot` | JSON conceitual | contexto da alteração |
| `created_at` | timestamp | auditoria |

Eventos esperados:

- criação da implantação;
- início de etapa;
- conclusão de etapa;
- pausa;
- bloqueio;
- desbloqueio;
- mudança para `READY_FOR_GO_LIVE`;
- execução de go-live;
- início de estabilização;
- conclusão;
- cancelamento.

## 6. Relacionamentos oficiais

Relacionamentos canônicos:

```text
Tenant
  ↓ 1:N
ImplantacaoOperacional
  ├── 1:N ImplantacaoEtapa
  ├── 1:N ImplantacaoChecklistItem
  ├── 1:N ImplantacaoPendencia
  └── 1:N ImplantacaoHistorico

ImplantacaoOperacional
  ├── N:1 Usuario (owner responsável)
  └── N:1 UnidadeProdutiva (principal, opcional no início)
```

Relações de referência, não de ownership:

- `ImplantacaoOperacional` referencia `Tenant`, mas não o cria;
- `ImplantacaoOperacional` referencia `Usuario`, mas não o gerencia;
- `ImplantacaoOperacional` referencia `UnidadeProdutiva`, mas não redefine sua arquitetura;
- itens e pendências podem apontar evidências em `AreaRural`, `Produto`, `PlanoConta`, `Safra`, `ProductionUnit`, `LoteAnimal`, `Deposito`, `Equipamento` e equivalentes canônicos.

## 7. Estados oficiais

Estados herdados de `WIZARD-ARCH-01`:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PAUSED`
- `READY_FOR_GO_LIVE`
- `GO_LIVE`
- `STABILIZATION`
- `COMPLETED`
- `CANCELLED`

### 7.1 Decisão sobre `BLOCKED`

Decisão recomendada: **sim, o modelo deve suportar `BLOCKED`**.

Justificativa:

- `PAUSED` e `BLOCKED` representam situações diferentes;
- a ausência desse estado força misturar suspensão voluntária com impedimento estrutural;
- go-live e retomada exigem distinção explícita.

Semântica oficial:

- `PAUSED`: implantação interrompida voluntariamente ou por conveniência operacional, sem impedimento crítico estrutural;
- `BLOCKED`: implantação impedida por requisito crítico ausente, dependência quebrada ou bloqueio operacional que inviabiliza avanço seguro.

Impacto sobre go-live:

- `PAUSED` não implica reprovação de go-live por si só;
- `BLOCKED` impede transição para `READY_FOR_GO_LIVE` e `GO_LIVE`.

Guardrail futuro:

- `WIZARD-GOV-01` deve impedir mudança para `READY_FOR_GO_LIVE` quando houver status global `BLOCKED` ou pendência crítica aberta.

## 8. Etapas canônicas

Etapas herdadas de `WIZARD-ARCH-01`:

1. Boas-vindas e diagnóstico inicial
2. Confirmação da UnidadeProdutiva
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

Regras de etapa:

- cada etapa deve possuir `codigo_etapa` estável;
- etapas podem ser obrigatórias, opcionais ou condicionais por escopo;
- a etapa `Equipe` é opcional;
- `Go-live assistido` e `Estabilização` devem existir explicitamente no modelo, não só como flags globais;
- ordem oficial é fixa, mas a aplicabilidade pode variar por tipo de operação.

## 9. Progresso

O progresso da implantação deve ser representado em dois níveis:

- progresso global em `ImplantacaoOperacional.percentual_progresso`;
- progresso granular por `ImplantacaoEtapa.percentual_peso`.

Regra oficial:

- percentual não deve ser apenas manual;
- o cálculo deve considerar peso de etapa, itens obrigatórios concluídos e elegibilidade real;
- etapa opcional não pode distorcer indevidamente a percepção de prontidão mínima;
- equipe adicional não deve reduzir artificialmente prontidão do go-live mínimo.

Recomendação conceitual:

- progresso global = soma dos pesos de etapas concluídas e validadas;
- itens obrigatórios críticos não atendidos impedem estados finais, mesmo com percentual alto.

## 10. Checklist

O checklist oficial deve servir para três camadas:

- avanço de etapa;
- revisão de implantação;
- go-live.

Tipos recomendados de item:

- estrutural;
- cadastral;
- operacional;
- financeiro;
- territorial;
- documental;
- validação manual;
- evidência de operação assistida.

Regra oficial:

- checklist deve ser recalculável;
- itens derivados do estado do tenant devem preferir verificação automática;
- itens de aceite humano devem registrar `checked_by_usuario_id` e `checked_at`;
- item crítico faltante impede go-live.

## 11. Pendências, bloqueios e evidências

Separação oficial:

- `ImplantacaoChecklistItem` verifica requisito;
- `ImplantacaoPendencia` registra problema, risco, bloqueio ou ação pendente;
- `evidencia_ref_id` aponta para a evidência ou entidade que suporta a verificação.

Exemplos de evidência:

- `UnidadeProdutiva` ativa;
- nó `AreaRural` criado;
- `Deposito` ativo;
- `PlanoConta` disponível;
- `ProdutoCultura` carregado;
- `ProductionUnit` criada para trilha agrícola;
- primeiro fluxo assistido registrado.

Regra oficial:

- evidência não precisa ser sempre um arquivo;
- a principal evidência do Wizard é o estado real das entidades canônicas do tenant.

## 12. Histórico e auditoria

O modelo deve permitir responder:

- quem iniciou a implantação;
- quem pausou, bloqueou, retomou ou concluiu;
- por que uma etapa foi pulada;
- quando o tenant ficou pronto para go-live;
- quais bloqueios existiram antes do go-live;
- qual era o snapshot do contexto em cada transição importante.

Regra oficial:

- `ImplantacaoHistorico` é obrigatório para governança;
- alterações críticas não devem depender apenas de `updated_at`.

## 13. Regras de unicidade

Regras oficiais:

- uma implantação pertence a um tenant;
- deve existir no máximo uma `ImplantacaoOperacional` ativa por `tenant_id`, salvo decisão futura explícita;
- estados ativos, para esse fim, incluem:
  - `NOT_STARTED`
  - `IN_PROGRESS`
  - `PAUSED`
  - `BLOCKED`
  - `READY_FOR_GO_LIVE`
  - `GO_LIVE`
  - `STABILIZATION`
- `COMPLETED` e `CANCELLED` liberam nova implantação futura, se a governança permitir.

Decisão oficial:

- v1.0 deve assumir uma única implantação operacional ativa por tenant.

## 14. Regras de idempotência

Regras oficiais:

- reiniciar o Wizard não deve criar uma segunda implantação ativa;
- reabrir etapa não deve duplicar etapa nem checklist base;
- confirmação manual não deve duplicar evidência factual;
- verificação automática deve ser reexecutável sem efeitos colaterais;
- avanço de etapa deve depender do estado real do tenant.

Estratégia conceitual:

- idempotência por `tenant_id + implantação ativa`;
- etapas indexadas por `implantacao_id + codigo_etapa`;
- checklist base indexado por `implantacao_id + codigo_item`;
- histórico sempre append-only;
- pendências resolvidas não devem ser sobrescritas silenciosamente.

## 15. Regras de go-live

Go-live mínimo exige:

- `Tenant` ativo;
- `Owner/Admin` ativo;
- pelo menos uma `UnidadeProdutiva` ativa;
- estrutura mínima compatível com o módulo contratado;
- checklist mínimo obrigatório concluído;
- ausência de bloqueios críticos;
- status global elegível para transição a `READY_FOR_GO_LIVE`.

Regras adicionais:

- ausência de equipe adicional não impede go-live mínimo;
- ausência de `UnidadeProdutiva` impede go-live sempre;
- conclusão manual não substitui requisito estrutural faltante;
- pendência crítica aberta impede go-live.

## 16. Relação com Tenant

`Tenant` é a fronteira de ownership da implantação.

Regra oficial:

- toda implantação existe dentro de um único tenant;
- o Wizard não modela tenant como agregado seu;
- ele apenas referencia o tenant como contexto obrigatório.

## 17. Relação com UnidadeProdutiva

`UnidadeProdutiva` é a âncora operacional mínima da implantação.

Regra oficial:

- `ImplantacaoOperacional.unidade_produtiva_id` pode ser nulo no início;
- antes de `READY_FOR_GO_LIVE`, uma `UnidadeProdutiva` principal deve estar definida;
- implantação multiunidade pode surgir no futuro, mas v1.0 deve operar com uma referência principal clara.

## 18. Relação com Owner/Admin

`Owner/Admin` é ator responsável, não artefato criado pelo Wizard.

Regra oficial:

- `owner_usuario_id` referencia o responsável principal;
- futuras interações podem envolver outros atores, mas a responsabilidade primária continua explícita;
- o Wizard não cria `Usuario`, não cria `TenantUsuario` e não redefine papéis globais.

## 19. Relação com Auth

`Auth` continua fora do domínio do Wizard.

Regra oficial:

- autenticação, credenciais e sessão não pertencem ao modelo `ImplantacaoOperacional`;
- o Wizard consome contexto autenticado, não o produz.

## 20. Relação com Billing

`Billing` continua fora do domínio do Wizard.

Regra oficial:

- assinatura, plano, trial e cobrança não pertencem ao agregado da implantação;
- o Wizard apenas pressupõe elegibilidade comercial já existente.

## 21. Relação com Onboarding

`Onboarding` continua sendo a camada anterior ao Wizard.

Regra oficial:

- o modelo do Wizard não substitui a modelagem do onboarding técnico;
- o início do Wizard pressupõe provisionamento mínimo já resolvido;
- futuras integrações devem preservar os gates mínimos já documentados em `PILOT-GOV-01`.

## 22. Relação com Equipe

Equipe é trilha opcional, não agregado central da implantação.

Regra oficial:

- o Wizard pode registrar etapa opcional de equipe;
- o modelo não deve ter campo ou regra que trate “equipe completa” como condição estrutural de conclusão mínima;
- vínculos de equipe continuam pertencendo a `TenantUsuario`, `UnidadeProdutivaUsuario` e fluxos de convite já existentes.

## 23. Decisões oficiais

Decisões normativas:

- `ImplantacaoOperacional` é a entidade raiz do domínio do Wizard;
- `ImplantacaoEtapa`, `ImplantacaoChecklistItem`, `ImplantacaoPendencia` e `ImplantacaoHistorico` são entidades auxiliares canônicas;
- o modelo deve suportar `BLOCKED` além dos estados já definidos em `WIZARD-ARCH-01`;
- v1.0 deve permitir no máximo uma implantação ativa por tenant;
- `UnidadeProdutiva` principal é obrigatória antes do go-live;
- equipe adicional não é requisito mínimo;
- o modelo deve ser compatível com Wizard guiado e implantação manual assistida;
- o modelo deve preferir evidência factual a marcação manual.

## 24. Riscos arquiteturais

Riscos a evitar:

- tratar implantação como extensão de onboarding comercial;
- misturar estado do Wizard com estado de assinatura;
- permitir múltiplas implantações ativas concorrentes por tenant;
- permitir conclusão manual sem evidência mínima;
- converter checklist em formulário cego;
- usar equipe como proxy indevido de prontidão operacional;
- esconder bloqueios críticos atrás de `PAUSED`.

## 25. Recomendações para WIZARD-GOV-01

Guardrails mínimos recomendados:

- garantir unicidade de implantação ativa por tenant;
- garantir presença de `owner_usuario_id` válido;
- garantir que `READY_FOR_GO_LIVE` e `GO_LIVE` exijam `unidade_produtiva_id` válida;
- garantir que etapa `Equipe` permaneça opcional;
- garantir que `BLOCKED` impeça go-live;
- garantir que checklist obrigatório não possa ser marcado como atendido sem evidência compatível;
- garantir que o Wizard não crie `Usuario`, `Tenant`, `Assinatura`, `TenantUsuario` ou convites;
- garantir que histórico de transição seja append-only e rastreável.

## 26. Recomendações para futura implementação

Diretrizes de implementação futura:

- começar pelo agregado `ImplantacaoOperacional`;
- materializar códigos estáveis para estados, etapas e itens de checklist;
- separar status global de status de etapa;
- modelar snapshots como apoio de auditoria, não como substituto das entidades canônicas;
- preferir resolvers/verificadores automáticos para checklist;
- manter compatibilidade com `onboarding/status` até migração explícita;
- prever serviços de reidratação e retomada por leitura do estado real do tenant;
- tratar histórico e pendências como componentes de governança desde a primeira implementação.

## 27. Resposta final

Após este documento, o AgroSaaS passa a ter um modelo canônico de dados claro para a implantação operacional: uma raiz `ImplantacaoOperacional`, cercada por etapas, checklist, pendências e histórico, ligada a `Tenant`, `Owner/Admin` e `UnidadeProdutiva`, com regras explícitas de unicidade, idempotência, bloqueio, go-live e separação arquitetural em relação a Auth, Billing, Onboarding e Equipe.
