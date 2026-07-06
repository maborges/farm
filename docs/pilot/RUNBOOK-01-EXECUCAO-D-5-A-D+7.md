# Runbook Operacional do Primeiro Piloto

Data: 2026-07-05

## Objetivo

Orientar a equipe de implantação e operação durante a janela D-5 até D+7 do primeiro piloto do AgroSaaS, sem duplicar o Plano Mestre e sem recriar procedimentos já aprovados.

## Como usar este runbook

- Este documento executa o plano mestre em rotina diária.
- Os detalhes de negócio, integração Sankhya, observabilidade e Campo PWA permanecem referenciados nos documentos oficiais.
- Quando houver conflito entre este runbook e o plano mestre, prevalece o [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md).

## Documentos de referência

- [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md)
- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md)
- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)
- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)

## Responsáveis

### Equipe AgroSaaS

- coordenar a execução diária;
- validar checkpoints;
- acompanhar integração Sankhya;
- acompanhar sincronizações e logs;
- registrar incidentes e ações corretivas.

### Cliente piloto

- manter disponibilidade do owner/admin;
- aprovar decisões de go/no-go;
- validar pendências de cadastro e operação;
- confirmar início da operação assistida.

### Usuários operacionais

- executar a operação do Campo e as rotinas liberadas;
- reportar inconsistências;
- respeitar os fluxos e limites aprovados.

## D-5 - Preparação

### Atividades

- validar contrato e assinatura;
- validar tenant, owner e plano ativo;
- confirmar `UnidadeProdutiva` vinculada;
- conferir configuração inicial do Wizard;
- validar credenciais Sankhya;
- executar teste de conexão;
- confirmar disponibilidade do Gateway;
- confirmar acesso de todos os responsáveis.

### Evidências esperadas

- tenant ativo;
- owner autenticado;
- assinatura ativa;
- `UnidadeProdutiva` presente;
- teste de conexão com retorno sanitizado;
- acessos confirmados.

### Responsável

- Equipe AgroSaaS.

### Documentos de referência

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)

## D-4 - Estrutura Operacional

### Atividades

- validar propriedades e vínculos territoriais;
- conferir imóveis rurais e glebas;
- validar talhões, áreas operacionais e depósitos;
- conferir produtos, fornecedores e clientes;
- conferir plano de contas;
- validar estoque inicial quando aplicável ao escopo do piloto.

### Evidências esperadas

- estrutura territorial consistente;
- depósitos relacionados ao contexto da unidade produtiva;
- cadastros básicos presentes para o piloto;
- estoque inicial conferido quando fizer parte da onda inicial.

### Responsável

- Equipe AgroSaaS com apoio do administrador do cliente.

### Documentos de referência

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)

## D-3 - Integração

### Atividades

- executar a autenticação Sankhya conforme documentação oficial;
- confirmar que o teste de conexão foi bem-sucedido;
- validar a carga inicial aprovada para o piloto;
- conferir os dados importados;
- registrar inconsistências e decidir correções ou bloqueio.

### Evidências esperadas

- retorno do teste de conexão;
- configuração padrão válida;
- inconsistências classificadas;
- aprovação ou bloqueio registrado.

### Responsável

- Equipe AgroSaaS.

### Documentos de referência

- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)

## D-2 - Campo PWA

### Atividades

- preparar dispositivos;
- validar ativação com PIN;
- confirmar sincronização inicial;
- executar teste offline;
- executar teste online;
- testar recuperação de sincronização;
- confirmar que a operação em campo depende do fluxo já validado.

### Evidências esperadas

- dispositivo ativado;
- sessão local persistida;
- sincronização inicial concluída;
- teste offline e online validado;
- recuperação de sync observada.

### Responsável

- Equipe AgroSaaS com apoio dos usuários operacionais.

### Documentos de referência

- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)

## D-1 - Pré Go-Live

### Atividades

- executar o checklist mínimo;
- validar pendências abertas;
- validar o Wizard e o estado atual da implantação;
- validar a `UnidadeProdutiva`;
- decidir GO ou NO-GO;
- se houver bloqueio, registrar motivo e ação corretiva.

### Evidências esperadas

- checklist mínimo satisfeito ou bloqueado com causa registrada;
- Wizard com status coerente;
- decisão GO/NO-GO formalizada;
- responsável do cliente ciente.

### Responsável

- Equipe AgroSaaS e administrador do cliente.

### Documentos de referência

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)

## D0 - Go-Live

### Atividades

- liberar oficialmente a operação;
- executar a primeira sincronização operacional;
- validar o primeiro acesso ao Campo;
- registrar a primeira operação;
- verificar alertas e recomendações;
- validar logs e health do ambiente;
- registrar qualquer incidente imediato.

### Evidências esperadas

- go-live registrado;
- primeira operação confirmada;
- logs e health consultados;
- alertas e recomendações verificados;
- incidentes iniciais registrados, se houver.

### Responsável

- Equipe AgroSaaS com apoio do cliente.

### Documentos de referência

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)

## D+1 a D+7 - Operação assistida

### Atividades diárias

- revisar sincronizações;
- revisar logs;
- revisar health;
- revisar estoque;
- revisar financeiro;
- revisar Campo PWA;
- revisar alertas e recomendações;
- revisar pendências;
- revisar incidentes;
- executar ações corretivas aprovadas.

### Rotina mínima

- checkpoint diário;
- consolidação de evidências;
- classificação de pendências;
- decisão sobre correções imediatas ou retorno a D-1;
- comunicação formal do status.

### Evidências esperadas

- status diário registrado;
- pendências classificadas;
- ações corretivas vinculadas a incidentes ou alertas;
- consistência entre operação, sync e observabilidade.

### Responsável

- Equipe AgroSaaS.

### Documentos de referência

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)

## Escalonamento

### Interromper a implantação quando

- o teste de conexão Sankhya falhar de forma recorrente;
- a `UnidadeProdutiva` deixar de estar válida;
- o checklist mínimo ficar bloqueado sem correção segura;
- houver divergência estrutural relevante entre documento e estado real;
- a operação depender de fluxo paralelo não aprovado.

### Abrir incidente quando

- houver falha de sincronização;
- houver erro de health, logs ou recomendações críticas;
- houver inconsistência de estoque, financeiro ou Campo PWA;
- houver falha de acesso ou de permissão em etapa crítica;
- houver incidentes repetidos no mesmo dia.

### Retornar para D-1 quando

- o go-live ainda não tiver sido concluído de forma segura;
- o checklist mínimo continuar bloqueado;
- o cliente precisar corrigir dados antes da ativação oficial;
- a equipe decidir adiar a liberação por risco operacional.

### Cancelar o go-live quando

- a equipe concluir que não há condições seguras de estabilização;
- houver quebra de premissa estrutural do piloto;
- o cliente não puder manter o compromisso de operação assistida;
- a correção exigida sair do escopo aprovado do piloto.

## Encerramento da primeira semana

Ao final de D+7 registrar:

- objetivos atingidos;
- problemas encontrados;
- ações corretivas executadas;
- backlog gerado;
- recomendação de continuidade;
- necessidade ou não de extensão da operação assistida.

### Evidências de encerramento

- consolidação do status dos checkpoints;
- relatório de incidentes e ações corretivas;
- decisão de continuidade documentada.

### Responsável

- Equipe AgroSaaS, com validação do cliente quando aplicável.

## Consolidação de procedimentos reutilizados

### Reutilizados integralmente

- validação de contrato, assinatura, tenant, owner, plano e `UnidadeProdutiva`;
- teste de conexão Sankhya;
- sequência Sankhya de autenticação, carga e validação;
- ativação e teste do Campo PWA;
- checklist mínimo do Wizard;
- observabilidade e leitura de health/logs;
- implantação assistida de estoque quando aplicável.

### Reutilizados com adaptação

- estrutura territorial do D-4;
- validação de inconsistências importadas no D-3;
- rotina de acompanhamento diário D+1 a D+7;
- escalonamento para retorno a D-1;
- encerramento da semana com backlog e decisão de continuidade.

### Criados neste runbook

- ordenação operacional única por dia do piloto;
- consolidação da janela D-5 a D+7 em um só fluxo;
- matriz de evidências por etapa;
- critérios de escalonamento no contexto do piloto.

## Confirmação final

Este runbook consolida procedimentos já aprovados e referencia os documentos oficiais existentes como fonte de verdade. Não há duplicação desnecessária de procedimentos; apenas organização operacional para uso diário da equipe no primeiro piloto.
