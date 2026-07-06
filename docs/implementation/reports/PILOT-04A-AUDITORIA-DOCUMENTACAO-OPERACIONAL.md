# PILOT-04A - Auditoria da Documentação Operacional do Piloto

Data: 2026-07-05

## Objetivo

Auditar a documentação operacional existente relacionada ao primeiro piloto do AgroSaaS, identificar duplicidades, lacunas e documentos reaproveitáveis, e definir o conjunto mínimo de documentos oficiais necessário para a implantação controlada do primeiro cliente.

## Escopo auditado

Foram auditados documentos relacionados a:

- implantação controlada e assistida;
- onboarding comercial e operacional;
- go-live e estabilização;
- Field PWA;
- integração Sankhya;
- observabilidade;
- runbooks;
- checklists;
- relatórios de preparação do piloto.

## Conclusão executiva

A base documental do piloto já existe e cobre o essencial da operação.

O material está distribuído em relatórios de auditoria, plano operacional, guardrails, runbooks e checklists. Isso significa que o AgroSaaS não precisa criar uma nova camada documental paralela agora; o que precisa ser feito é consolidar e manter atualizado o conjunto existente.

O núcleo mais reutilizável para operação do piloto é:

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)
- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)

## Matriz de auditoria

| Documento | Situação | Reutilização | Observação |
| --- | --- | --- | --- |
| [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md) | EXISTE E ATENDE | Alta | É o melhor candidato a plano mestre do piloto. |
| [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md) | EXISTE E ATENDE | Alta | Serve como parecer de prontidão e referência de go/no-go. |
| [PILOT-00A-AUDITORIA-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-00A-AUDITORIA-IMPLANTACAO.md) | EXISTE PARCIALMENTE | Média | Base histórica útil, mas não fecha a operação atual do piloto. |
| [PILOT-00B-AUDITORIA-CADASTROS-MESTRES.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-00B-AUDITORIA-CADASTROS-MESTRES.md) | EXISTE PARCIALMENTE | Média | Reaproveitável como referência de cadastros, não como documento operacional final. |
| [PILOT-02-AUDITORIA-CAFE-EXPORTACAO-SANKHYA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-02-AUDITORIA-CAFE-EXPORTACAO-SANKHYA.md) | EXISTE PARCIALMENTE | Média | Boa base de contexto do cliente piloto, mas ainda é um documento de auditoria. |
| [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md) | EXISTE E ATENDE | Alta | Reutilizável como guardrail oficial de onboarding e assinatura. |
| [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md) | EXISTE E ATENDE | Alta | Complementa o fluxo de acesso e equipe do piloto. |
| [EXECUTION-WIZARD-07-GO-LIVE-ASSISTIDO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-WIZARD-07-GO-LIVE-ASSISTIDO-PILOTO.md) | EXISTE PARCIALMENTE | Alta | Reaproveitável, mas sobrepõe parte do plano operacional. |
| [SANKHYA-AUTH-01-GATEWAY-CREDENTIALS.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-01-GATEWAY-CREDENTIALS.md) | EXISTE PARCIALMENTE | Média | É útil para configuração, mas não fecha o fluxo operacional sozinho. |
| [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md) | EXISTE E ATENDE | Alta | Documento operacional objetivo para validar conectividade. |
| [SANKHYA-DOMAIN-01-ADAPTER-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-01-ADAPTER-CANONICO.md) | EXISTE PARCIALMENTE | Média | Bom para arquitetura, não para operação do piloto. |
| [SANKHYA-DOMAIN-02-API-UX-CANONICA-STATUS-JOBS-HEALTH.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-02-API-UX-CANONICA-STATUS-JOBS-HEALTH.md) | EXISTE PARCIALMENTE | Média | Ajuda na visão de status e jobs, mas é documentação técnica. |
| [SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md) | EXISTE PARCIALMENTE | Média | Relevante para diagnóstico, mas não substitui um runbook operacional. |
| [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md) | EXISTE E ATENDE | Alta | Define escopo mínimo e direção do fluxo. |
| [SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md) | EXISTE E ATENDE | Alta | Documento mestre do mapeamento padrão. |
| [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md) | EXISTE E ATENDE | Alta | Consolida a estratégia operacional de sincronização. |
| [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md) | EXISTE PARCIALMENTE | Média | Base boa de observabilidade, mas ainda em nível de arquitetura. |
| [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md) | EXISTE E ATENDE | Alta | Runbook operacional útil se estoque estiver no piloto. |
| [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md) | EXISTE E ATENDE | Alta | Relevante para preparação de dispositivos e campo. |
| [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md) | EXISTE E ATENDE | Alta | Checklist operacional útil para verificação de eventos. |

## Duplicidades e consolidações sugeridas

Não foi identificado um conflito inválido entre os documentos. O que existe é sobreposição de escopo em alguns pontos, o que recomenda consolidação futura, não criação paralela.

### Sobreposições principais

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md) e [EXECUTION-WIZARD-07-GO-LIVE-ASSISTIDO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/EXECUTION-WIZARD-07-GO-LIVE-ASSISTIDO-PILOTO.md)
- [SANKHYA-AUTH-01-GATEWAY-CREDENTIALS.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-01-GATEWAY-CREDENTIALS.md) e [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [SANKHYA-DOMAIN-01-ADAPTER-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-01-ADAPTER-CANONICO.md), [SANKHYA-DOMAIN-02-API-UX-CANONICA-STATUS-JOBS-HEALTH.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-02-API-UX-CANONICA-STATUS-JOBS-HEALTH.md) e [SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md)
- [PILOT-00A-AUDITORIA-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-00A-AUDITORIA-IMPLANTACAO.md), [PILOT-00B-AUDITORIA-CADASTROS-MESTRES.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-00B-AUDITORIA-CADASTROS-MESTRES.md) e [PILOT-02-AUDITORIA-CAFE-EXPORTACAO-SANKHYA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-02-AUDITORIA-CAFE-EXPORTACAO-SANKHYA.md)

## O que pode ser reaproveitado

### Reaproveitamento alto

- plano operacional e sequência do piloto;
- guardrails de onboarding e assinatura;
- escopo de sync e mapeamento padrão;
- conexão e autenticação Sankhya;
- runbook de estoque assistido;
- setup do Field PWA;
- checklist operacional de eventos;
- observabilidade básica já definida.

### Reaproveitamento médio

- relatórios mais antigos de auditoria;
- documentos técnicos de arquitetura Sankhya;
- documento de go-live assistido do Wizard.

## O que precisa apenas de atualização

- consolidar a narrativa operacional em um único pacote oficial;
- remover redundâncias entre plano, wizard e documentos Sankhya;
- atualizar eventuais referências para refletir o estado mais recente do piloto;
- explicitar melhor a fronteira entre documentação técnica e documentação operacional.

## O que realmente precisa ser criado

Com base na auditoria, o que ainda falta como documento oficial consolidado é:

1. um plano mestre do piloto, único e consolidado;
2. um checklist oficial de aceite do cliente;
3. um runbook operacional mestre para D-5 até D+7;
4. um documento de encerramento do piloto, com lições aprendidas e decisão de continuidade.

## Conjunto mínimo oficial recomendado

Para executar o primeiro piloto operacional com segurança documental, o pacote mínimo deve conter:

1. Plano Mestre do Piloto, consolidado a partir de [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md).
2. Checklist de prontidão e aceite, com base em [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md).
3. Trilha Sankhya operacional, cobrindo [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md), [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md), [SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-CANONICO.md) e [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md).
4. Guardrails de implantação e identidade, com [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md) e [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md).
5. Runbooks operacionais de apoio, principalmente [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md) e [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md).
6. Checklist de eventos e observabilidade, usando [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md) e [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md).

## Resposta objetiva

- O que foi auditado: toda a documentação operacional ligada ao piloto, incluindo implantação, onboarding, go-live, Sankhya, Field PWA, observabilidade, runbooks e checklists.
- O que já existia: um conjunto documental amplo, suficiente para suportar o piloto sem criar uma camada nova.
- O que pode ser reutilizado: o plano operacional, as auditorias Sankhya, os guardrails, a documentação de conexão e os runbooks já publicados.
- O que exige apenas extensão: a consolidação narrativa dos documentos e o refinamento de atualizações de versão e escopo.
- O que realmente precisa ser criado: o pacote oficial consolidado com plano mestre, checklist de aceite, runbook mestre e encerramento do piloto.
