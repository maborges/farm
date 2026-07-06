# Plano Mestre Oficial do Primeiro Piloto

Data: 2026-07-05

## 1. Objetivo do piloto

O primeiro piloto operacional do AgroSaaS tem como finalidade validar a operação real de um cliente produtor de café exportador em ambiente controlado, com uso do Wizard como fluxo oficial de implantação e com a integração Sankhya tratada de forma segura e incremental.

### Propósito

- validar a implantação assistida de ponta a ponta;
- comprovar que a operação inicial pode ser conduzida sem criação de fluxo paralelo;
- confirmar a aderência entre o modelo padrão do AgroSaaS e o cadastro/fonte operacional do cliente;
- sustentar a entrada em produção assistida com guardrails claros.

### Escopo

- implantação controlada do primeiro cliente piloto;
- configuração e teste de conexão Sankhya;
- sincronização apenas dentro do escopo mínimo aprovado para o piloto;
- operação Campo offline-first;
- go-live assistido com monitoramento e estabilização inicial.

### Limites

- não cobre automação completa de implantação;
- não cobre escrita bidirecional Sankhya no MVP;
- não substitui runbook, checklist ou documento de encerramento;
- não autoriza criação de novas regras arquiteturais.

## 2. Cliente piloto

O cliente piloto é um produtor de café com perfil exportador e uso ativo do ERP Sankhya.

### Contexto operacional

- operação agrícola com necessidade de estrutura mínima bem definida;
- dependência de cadastros, financeiro e rastreabilidade em nível suficiente para a rotina do piloto;
- necessidade de validar a integração sem sincronizar domínio de negócio fora do escopo aprovado.

### Sistema de origem

Para este piloto, o Sankhya permanece como referência principal para os cadastros e documentos definidos na estratégia de sincronização.

Referências:

- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)

## 3. Premissas

As premissas abaixo foram consolidadas nas auditorias anteriores e permanecem válidas para o piloto:

- implantação assistida;
- uso obrigatório do Wizard como fluxo oficial de implantação;
- Sankhya como origem dos dados definidos para o escopo de integração;
- AgroSaaS como origem padrão dos dados agronômicos e operacionais;
- Campo operando em modo offline-first;
- go-live condicionado aos guardrails já definidos;
- sincronização controlada, sem automação de escrita reversa no MVP.

Referências:

- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)
- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)

## 4. Escopo do piloto

O escopo funcional do piloto deve ser lido a partir dos documentos Sankhya já consolidados, sem repetição de conteúdo neste plano.

### Componentes principais

- escopo mínimo de sincronização;
- mapeamento padrão de entidades;
- estratégia operacional de sincronização;
- teste de conexão e autenticação;
- integração com observabilidade.

Referências:

- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)
- [SANKHYA-DOMAIN-01-ADAPTER-OFICIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-01-ADAPTER-OFICIAL.md)
- [SANKHYA-DOMAIN-02-API-UX-OFICIAL-STATUS-JOBS-HEALTH.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-02-API-UX-OFICIAL-STATUS-JOBS-HEALTH.md)
- [SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md)

## 5. Papéis e responsabilidades

### Equipe AgroSaaS

- conduzir a implantação assistida;
- validar a integração Sankhya;
- acompanhar checklist, bloqueios e estabilização;
- apoiar a equipe do cliente durante o go-live;
- registrar evidências e decisões operacionais.

### Administrador do cliente

- aprovar etapas-chave da implantação;
- validar dados mínimos e cadastros críticos;
- decidir sobre avanço, bloqueio ou correção;
- manter disponibilidade para o go-live assistido.

### Usuários operacionais

- operar os fluxos já habilitados;
- respeitar o modo offline-first do Campo;
- informar pendências ou inconsistências observadas.

### Responsáveis pela validação

- validar checklist mínimo;
- validar prontidão para go-live;
- validar estabilização inicial e encerramento da implantação.

## 6. Critérios de Go-Live

O go-live somente pode ocorrer quando os critérios abaixo estiverem satisfeitos:

- `UnidadeProdutiva` ativa e vinculada ao tenant;
- checklist mínimo satisfeito;
- nenhuma pendência crítica aberta;
- implantação fora de estado bloqueado;
- teste de conexão Sankhya concluído com sucesso;
- configuração padrão válida para o piloto;
- fluxo operacional alinhado ao Wizard e aos guardrails.

Referências:

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)

## 7. Critérios de No-Go

O piloto deve ser interrompido ou mantido fora de go-live quando houver qualquer um dos seguintes pontos:

- ausência de `UnidadeProdutiva` válida;
- checklist mínimo insatisfeito;
- pendência crítica aberta;
- divergência entre estado real do tenant e o Wizard;
- falha de autenticação ou de teste de conexão Sankhya;
- necessidade de fluxo paralelo fora do Wizard;
- indisponibilidade do decisor do cliente;
- inconsistência estrutural relevante identificada durante a implantação.

## 8. Cronograma macro

O cronograma detalhado permanece no plano operacional e no runbook. Neste plano mestre, ficam apenas os marcos maiores:

- D-5 a D-1: saneamento final e validação pré-piloto;
- D0: go-live assistido;
- D1 a D7: operação assistida intensiva;
- D8 a D30: estabilização monitorada;
- D30: revisão executiva do piloto.

Referência:

- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)

## 9. Documentação oficial do piloto

O pacote oficial do piloto é composto pelos documentos abaixo:

1. [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
2. [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
3. [PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md)
4. [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
5. [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)
6. [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
7. [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
8. [SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md)
9. [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)
10. [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
11. [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
12. [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)
13. [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)

## 10. Próximos documentos

Os documentos abaixo devem existir como peças operacionais complementares, sem duplicar o plano mestre:

- Runbook Operacional do Piloto;
- Checklist Oficial do Cliente;
- Operação Assistida / acompanhamento dos primeiros dias;
- Encerramento do Piloto.

## Resumo executivo

Este plano mestre consolida a visão executiva do primeiro piloto e referencia os documentos já existentes como fonte de verdade para os detalhes operacionais, técnicos e de governança.

Ele não substitui runbook, checklist ou documentação Sankhya. Ele organiza o piloto, define o que está dentro e fora do escopo e aponta a documentação oficial que sustenta a execução controlada.
