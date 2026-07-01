# PILOT-01 — PLANO OPERACIONAL DO PRIMEIRO PILOTO CONTROLADO

## Objetivo do piloto

O primeiro piloto controlado tem como objetivo validar o AgroSaaS em operação real usando o Wizard como fluxo oficial de implantação operacional da fazenda.

Objetivos específicos:

* confirmar que a sequência `Tenant -> Owner/Admin -> Onboarding -> UnidadeProdutiva -> Wizard -> Go-live assistido` funciona de ponta a ponta;
* validar se o checklist automático, as pendências críticas e os bloqueios de go-live refletem corretamente o estado real do tenant;
* comprovar que a implantação mínima da fazenda pode ocorrer sem exigir equipe completa cadastrada;
* coletar evidências operacionais suficientes para decidir avanço, ajustes ou rollback controlado.

## Perfil ideal do primeiro cliente

Perfil recomendado para o piloto:

* cliente com escopo moderado, preferencialmente uma única operação principal;
* Owner/Admin com alta disponibilidade e poder de decisão;
* operação com uma primeira `UnidadeProdutiva` bem definida;
* baixa complexidade de integrações externas na onda inicial;
* pelo menos um módulo operacional claramente prioritário:
  * Agricultura; ou
  * Pecuária; ou
  * Estoque + Financeiro como base.

Evitar no primeiro piloto:

* grupo com múltiplas unidades produtivas simultâneas;
* operação fortemente dependente de ERP externo antes da estabilização;
* cenário com baixa disponibilidade do Owner/Admin;
* cliente que exija customização estrutural antes do go-live.

## Pré-requisitos antes do piloto

Pré-requisitos obrigatórios:

* `Tenant` ativo;
* `Usuario` Owner/Admin ativo e autenticado;
* vínculo válido do Owner/Admin ao tenant;
* onboarding mínimo concluído;
* pelo menos uma `UnidadeProdutiva` ativa ou pronta para ser confirmada no Wizard;
* módulos do piloto já definidos;
* dados mínimos disponíveis para a trilha contratada;
* equipe interna e consultor do piloto com janela operacional reservada.

Pré-requisitos recomendados:

* estrutura territorial mínima previamente saneada ou com insumos para cadastro;
* lista mínima de produtos/culturas/depósitos/plano de contas, conforme o escopo;
* definição de responsável por evidências e aceite operacional.

## Sequência de implantação usando o Wizard

Sequência oficial do piloto:

1. Validar acesso do Owner/Admin ao tenant.
2. Confirmar que o onboarding técnico já foi concluído.
3. Acessar `Configurações -> Wizard de Implantação`.
4. Iniciar ou retomar a implantação do tenant.
5. Confirmar a `UnidadeProdutiva` principal.
6. Executar a trilha territorial mínima.
7. Executar as trilhas de atividades produtivas aplicáveis.
8. Executar cadastros mínimos por módulo contratado.
9. Reavaliar checklist automático.
10. Resolver pendências críticas abertas.
11. Avançar para `READY_FOR_GO_LIVE`.
12. Executar `GO_LIVE` assistido.
13. Operar em `STABILIZATION`.
14. Concluir quando o piloto estiver estável e sem bloqueios estruturais.

## Checklist de validação pré-go-live

Checklist mínimo obrigatório antes do go-live:

* `UnidadeProdutiva` ativa e vinculada à implantação;
* checklist mínimo satisfeito pelo backend;
* nenhuma pendência crítica aberta;
* implantação fora de `BLOCKED`;
* etapa atual compatível com avanço para `READY_FOR_GO_LIVE`;
* dados mínimos da trilha contratada presentes no tenant.

Checklist operacional complementar:

* Owner/Admin entende os motivos de bloqueio e o que falta;
* telas do Wizard carregam status, etapas, checklist e pendências;
* reavaliação do checklist atualiza corretamente os bloqueios;
* sequência de transição oficial está íntegra:
  * `IN_PROGRESS -> READY_FOR_GO_LIVE -> GO_LIVE`

## Checklist de validação pós-go-live

Após o go-live assistido, validar:

* tenant em `GO_LIVE` ou `STABILIZATION`;
* Owner/Admin consegue acompanhar pendências e checklist remanescente;
* operação mínima do módulo contratado foi iniciada sem bloqueio estrutural;
* reavaliação do checklist continua consistente;
* histórico de transições do Wizard permaneceu íntegro;
* não houve necessidade de criar fluxo paralelo fora do Wizard.

## Critérios de sucesso

O piloto será considerado bem-sucedido quando:

* a implantação for executada pelo Wizard sem bypass estrutural;
* o go-live assistido ocorrer com `UnidadeProdutiva` válida;
* o go-live ocorrer com checklist mínimo satisfeito;
* o go-live ocorrer sem pendência crítica aberta;
* a operação mínima do cliente começar dentro da sequência arquitetural oficial;
* o Owner/Admin conseguir entender e operar o processo sem ambiguidade estrutural;
* a estabilização inicial ocorrer sem criação de fluxo paralelo.

## Critérios de bloqueio

O piloto deve ser bloqueado quando houver:

* ausência de `UnidadeProdutiva` ativa;
* checklist mínimo insatisfeito;
* pendência crítica aberta;
* implantação em `BLOCKED`;
* indisponibilidade do Owner/Admin para decisão operacional;
* necessidade de customização estrutural antes da validação do fluxo padrão;
* divergência entre estado real do tenant e leitura do Wizard.

## Critérios de rollback

Rollback do piloto deve ser considerado quando:

* o cliente não consegue avançar no fluxo oficial por bloqueio estrutural relevante;
* a operação real depende de fluxo externo não suportado pela arquitetura oficial;
* o checklist automático aponta inconsistência persistente sem resolução imediata segura;
* a equipe de implantação conclui que o tenant não está apto para estabilização controlada.

Rollback nesta fase significa:

* interromper avanço para `GO_LIVE` ou manter implantação fora de `COMPLETED`;
* retornar a operação para acompanhamento manual controlado;
* corrigir dados, estrutura ou configuração antes de nova tentativa;
* registrar a causa raiz e a ação corretiva necessária.

## Plano de acompanhamento

Janela recomendada de acompanhamento:

* D-5 a D-1: saneamento final e validação pré-piloto;
* D0: execução do go-live assistido;
* D1 a D7: operação assistida intensiva;
* D8 a D30: estabilização monitorada;
* D30: revisão executiva do piloto.

Ritmo operacional sugerido:

* checkpoint diário durante a primeira semana;
* checkpoint 2x por semana até D30;
* revisão formal de pendências, checklist e evidências em cada checkpoint.

## KPIs mínimos

KPIs mínimos do piloto:

* tempo total até `READY_FOR_GO_LIVE`;
* tempo total até `GO_LIVE`;
* quantidade de reavaliações de checklist;
* quantidade de pendências críticas abertas no ciclo;
* tempo médio de resolução de pendências críticas;
* percentual de etapas concluídas sem intervenção extraordinária;
* percentual de itens mínimos validados automaticamente;
* número de bloqueios de transição evitados pelo backend;
* tempo até entrada em `STABILIZATION`;
* tempo até fechamento do piloto.

## Evidências a coletar

Evidências mínimas:

* captura do status do Wizard antes do go-live;
* checklist mínimo atendido;
* ausência de pendências críticas no momento do go-live;
* confirmação de `UnidadeProdutiva` ativa;
* histórico da transição para `READY_FOR_GO_LIVE`;
* histórico da transição para `GO_LIVE`;
* histórico da transição para `STABILIZATION`, quando aplicável;
* registro dos bloqueios encontrados e das ações corretivas executadas.

## Riscos e mitigação

Risco: cliente com escopo amplo demais para o primeiro piloto.
Mitigação:
reduzir a onda inicial para uma única trilha operacional prioritária.

Risco: ausência do Owner/Admin no momento de decisão.
Mitigação:
reservar agenda formal para pré-go-live, go-live e D+1.

Risco: dados mínimos insuficientes para checklist satisfatório.
Mitigação:
executar revisão prévia e saneamento antes de iniciar o Wizard.

Risco: tentativa de operar fora do Wizard.
Mitigação:
formalizar o Wizard como fluxo oficial e registrar qualquer desvio como bloqueio.

Risco: excesso de pendências críticas próximo ao go-live.
Mitigação:
congelar avanço e priorizar resolução estrutural antes da transição.

## Próximos passos após o piloto

Após o primeiro piloto:

1. consolidar evidências e lições aprendidas;
2. classificar gaps entre arquitetura prevista e operação real;
3. priorizar ajustes seguros no Wizard sem criar arquitetura paralela;
4. definir critérios de repetibilidade para o segundo piloto;
5. preparar material operacional para equipe interna e parceiros.

## Decisão operacional

Decisão oficial deste plano:

* o primeiro piloto controlado deve usar o Wizard como fluxo único de implantação operacional;
* a equipe adicional continua opcional;
* o go-live só ocorre com `UnidadeProdutiva` ativa, checklist mínimo satisfeito e ausência de pendência crítica;
* qualquer desvio estrutural deve bloquear o piloto antes do avanço para produção controlada.
