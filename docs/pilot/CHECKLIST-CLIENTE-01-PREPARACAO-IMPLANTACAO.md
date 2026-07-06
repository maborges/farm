# Checklist Oficial do Cliente - Preparação para Implantação do Primeiro Piloto

Data: 2026-07-05

## Objetivo

Consolidar o checklist único de preparação do cliente antes do início do D-5 do primeiro piloto do AgroSaaS, sem duplicar verificações já cobertas pelo Plano Mestre, pelo Runbook Operacional e pelos documentos Sankhya.

## Documentos reutilizados

- [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md)
- [RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md)
- [PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md)
- [PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-03-AUDITORIA-EXECUCAO-IMPLANTACAO.md)
- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)
- [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md)
- [SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md)
- [SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md)
- [SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md)
- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)

## Escopo do checklist

Este checklist cobre apenas a preparação prévia ao D-5.

Não substitui:

- o Plano Mestre do piloto;
- o Runbook Operacional D-5 a D+7;
- os documentos Sankhya;
- os guardrails de onboarding e assinatura;
- o checklist técnico de eventos.

## 1. Informações da empresa

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Razão social | Cliente | Pendente | Dado cadastral obrigatório para validação inicial. |
| CNPJ | Cliente | Pendente | Usado para identificação e conferência documental. |
| Inscrição estadual, quando aplicável | Cliente | Pendente | Preencher apenas se aplicável ao perfil da operação. |
| Endereço principal | Cliente | Pendente | Sede e local de referência da operação. |
| Contatos principais | Cliente | Pendente | Incluir e-mail e telefone de operação. |
| Responsável legal | Cliente | Pendente | Responsável pela aprovação formal do piloto. |

## 2. Responsáveis pelo projeto

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Sponsor do projeto | Cliente | Pendente | Patrocínio executivo do piloto. |
| Owner/Admin do AgroSaaS | AgroSaaS | Pendente | Responsável pelo fluxo oficial da plataforma. |
| Responsável pelo ERP Sankhya | Cliente | Pendente | Ponto focal para integração e validação de origem. |
| Responsável financeiro | Cliente | Pendente | Apoio para cadastros e validações financeiras. |
| Responsável operacional da fazenda | Cliente | Pendente | Apoio para estrutura, campo e rotina diária. |
| Responsável pelo Campo PWA | Cliente / AgroSaaS | Pendente | Ponto focal para ativação e uso em campo. |
| Contatos de suporte | Cliente / AgroSaaS | Pendente | Lista de apoio durante implantação e estabilização. |

## 3. Estrutura da fazenda

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Propriedades | Cliente | Pendente | Base territorial principal. |
| Imóveis rurais | Cliente | Pendente | Confirmar documentos e vínculos. |
| Matrículas | Cliente | Pendente | Requisito de validação documental quando aplicável. |
| CAR | Cliente | Pendente | Informar quando a operação exigir. |
| Glebas | Cliente | Pendente | Necessárias para a estrutura territorial. |
| Talhões | Cliente | Pendente | Base de operação agronômica. |
| Áreas operacionais | Cliente | Pendente | Devem estar mapeadas se fizerem parte do piloto. |
| Depósitos | Cliente / AgroSaaS | Pendente | Conferir aderência com a estrutura do piloto. |
| Máquinas e equipamentos | Cliente | Pendente | Informações de apoio operacional. |
| Equipes | Cliente | Pendente | Lista de usuários e áreas responsáveis. |

## 4. Cadastros mestres

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Produtos | Cliente / AgroSaaS | Pendente | Base para carga inicial e operação. |
| Insumos | Cliente / AgroSaaS | Pendente | Conferir unidade de medida e códigos. |
| Clientes | Cliente / AgroSaaS | Pendente | Principalmente compradores quando houver. |
| Fornecedores | Cliente / AgroSaaS | Pendente | Conferir identificadores e duplicidades. |
| Plano de contas | Cliente / AgroSaaS | Pendente | Necessário para o piloto com financeiro. |
| Depósitos | Cliente / AgroSaaS | Pendente | Precisam estar alinhados ao piloto. |
| Estoque inicial, quando aplicável | Cliente / AgroSaaS | Pendente | Somente se o escopo do piloto exigir. |

## 5. Integração Sankhya

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Gateway instalado | Cliente / TI | Pendente | Validar instalação e disponibilidade. |
| Credenciais disponíveis | Cliente / TI | Pendente | Não incluir secrets neste checklist. |
| Acesso autorizado | Cliente / TI | Pendente | Confirmar permissão formal de uso. |
| Ambiente homologado | Cliente / TI | Pendente | Confirmar ambiente correto para o piloto. |
| Teste de conexão executado com sucesso | AgroSaaS | Pendente | Referência: [SANKHYA-AUTH-02-TEST-CONNECTION.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-AUTH-02-TEST-CONNECTION.md). |

## 6. Infraestrutura

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Acesso à internet na sede | Cliente | Pendente | Necessário para operação e sincronização. |
| Conectividade nas áreas de operação | Cliente | Pendente | Verificar alcance real nas áreas do piloto. |
| Wi-Fi, quando houver | Cliente | Pendente | Importante para onboarding e suporte. |
| Dispositivos móveis para o Campo PWA | Cliente | Pendente | Confirmar quantidade e estado. |
| Carregadores e suporte operacional | Cliente | Pendente | Garantir autonomia dos dispositivos. |

## 7. Campo PWA

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Usuários definidos | Cliente | Pendente | Informar quem usará o Campo. |
| Dispositivos disponíveis | Cliente | Pendente | Confirmar modelos e quantidade. |
| Ativação planejada | AgroSaaS | Pendente | Deve ocorrer no período operacional previsto. |
| Sincronização inicial programada | AgroSaaS | Pendente | Deve estar alinhada ao D-2/D0. |

## 8. Critérios para início do D-5

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Todos os responsáveis definidos | Cliente / AgroSaaS | Pendente | Nenhuma área crítica sem ponto focal. |
| Documentos obrigatórios entregues | Cliente / AgroSaaS | Pendente | Incluir contratos, dados e informações de acesso. |
| Acessos concedidos | Cliente / TI | Pendente | ERP, plataforma e Campo quando aplicável. |
| Integração Sankhya validada | AgroSaaS | Pendente | Depende do teste de conexão aprovado. |
| Dados mínimos disponíveis | Cliente | Pendente | Base para iniciar a implantação. |
| Cronograma confirmado | Cliente / AgroSaaS | Pendente | Janela D-5 a D+7 precisa estar reservada. |

## 9. Matriz consolidada

| Item | Responsável | Situação | Observações |
| --- | --- | --- | --- |
| Informações da empresa completas | Cliente | Pendente | Consolidado a partir das validações de assinatura e onboarding. |
| Responsáveis do projeto definidos | Cliente / AgroSaaS | Pendente | Consolidado a partir dos guardrails e do plano mestre. |
| Estrutura da fazenda documentada | Cliente | Pendente | Consolidado com base na estrutura territorial já validada. |
| Cadastros mestres disponíveis | Cliente / AgroSaaS | Pendente | Consolidado com base no escopo do piloto. |
| Integração Sankhya pronta para o D-5 | AgroSaaS | Pendente | Consolidado com os documentos Sankhya existentes. |
| Infraestrutura mínima confirmada | Cliente | Pendente | Necessária para o Campo e para a implantação assistida. |
| Campo PWA preparado | Cliente / AgroSaaS | Pendente | Consolidado com o runbook do Campo PWA. |
| Aptidão para iniciar o D-5 | Cliente / AgroSaaS | Pendente | Marcar somente quando todos os itens obrigatórios estiverem validados. |

## 10. Resumo de consolidação

### Checklists reutilizados

- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)
- [PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01-GUARDRAILS-IMPLANTACAO-ONBOARDING-ASSINATURA.md)
- [PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-GOV-01B-IDENTIDADE-CONVITES-EQUIPE.md)

### Itens consolidados

- informações da empresa;
- responsáveis pelo projeto;
- estrutura da fazenda;
- cadastros mestres;
- integração Sankhya;
- infraestrutura;
- Campo PWA;
- critérios de início do D-5.

### Itens adicionados

- matriz única de responsabilidade por item;
- consolidação da situação em formato operacional;
- confirmação formal de aptidão para o início do D-5.

## Confirmação final

Este checklist consolida apenas verificações já aprovadas e referencia os documentos oficiais para detalhes complementares. Não há duplicação desnecessária de verificações; o documento serve como lista única de preparação do cliente antes da implantação.

