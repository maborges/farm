# PILOT-DRYRUN-01 — Auditoria e Consolidação do Runbook do Dry Run

## 1. Resumo executivo

Foi localizada base documental suficiente para executar o primeiro Dry Run assistido sem criar um segundo runbook concorrente.

Decisão desta execução:

- documento oficial escolhido: [RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md);
- documento mestre preservado: [PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md);
- checklist auxiliar preservado: [CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md);
- `PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md` permanece como roteiro temático complementar, não como runbook oficial único.

Veredicto desta auditoria:

`GO COM RESSALVAS — runbook executável com ajustes operacionais registrados`

## 2. Documentos localizados

| Documento | Papel atual | Status | Sobreposição | Deve ser reutilizado? | Deve ser atualizado? |
| --------- | ----------- | ------ | ------------ | --------------------- | -------------------- |
| [docs/pilot/PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md) | documento mestre executivo | oficial | baixa | sim | não |
| [docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md) | runbook operacional | oficial | média | sim | sim |
| [docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md) | checklist pré-D-5 | oficial | baixa | sim | não |
| [docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md](/opt/lampp/htdocs/farm/docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md) | roteiro temático café+Sankhya | complementar | alta | sim, como apoio | não |
| [docs/implementation/reports/PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md) | parecer de prontidão | oficial | baixa | sim | não |
| [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md) | setup do Campo | complementar | baixa | sim | não |
| [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md) | runbook de estoque | complementar | baixa | sim | não |
| [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md) | observabilidade arquitetural | complementar | baixa | sim | não |
| [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md) | checklist de eventos | complementar | baixa | sim | não |
| [docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md) | auditoria documental anterior | histórico útil | média | sim, como referência | não |

## 3. Documento oficial escolhido

O documento oficial escolhido para consolidação foi [RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md), por quatro razões:

- já ocupava o papel explícito de runbook operacional;
- já apontava para o plano mestre como fonte superior;
- evita duplicação com o `PLANO-MESTRE`;
- permite separar núcleo genérico do piloto das extensões café e Sankhya.

## 4. Documentos reutilizados

- [docs/pilot/PLANO-MESTRE-PILOTO-01.md](/opt/lampp/htdocs/farm/docs/pilot/PLANO-MESTRE-PILOTO-01.md)
- [docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md](/opt/lampp/htdocs/farm/docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md)
- [docs/implementation/reports/PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-E2E-01-AUDITORIA-PRONTIDAO-OPERACIONAL-PONTA-A-PONTA.md)
- [docs/runbooks/field-pwa-local-setup.md](/opt/lampp/htdocs/farm/docs/runbooks/field-pwa-local-setup.md)
- [docs/runbooks/estoque-implantacao-assistida.md](/opt/lampp/htdocs/farm/docs/runbooks/estoque-implantacao-assistida.md)
- [docs/implementation/checklists/domain-events-operational-checklist.md](/opt/lampp/htdocs/farm/docs/implementation/checklists/domain-events-operational-checklist.md)
- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)

## 5. Documentos substituídos ou apenas históricos

- [docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md](/opt/lampp/htdocs/farm/docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md)
  Continua útil como roteiro temático do provider e do segmento café, mas não deve competir com o runbook oficial.
- [docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-04A-AUDITORIA-DOCUMENTACAO-OPERACIONAL.md)
  Permanece como base histórica da decisão de consolidação documental.

## 6. Auditoria de reutilização

Conclusão:

- o acervo já tinha documento mestre, runbook, checklist e parecer de prontidão;
- a principal lacuna não era ausência de documento, mas falta de um runbook com granularidade suficiente para executar os cenários A-E;
- a solução correta foi atualizar o `RUNBOOK-01`, não criar um novo runbook.

## 7. Auditoria arquitetural

O runbook atualizado respeita a arquitetura oficial ao exigir:

- governança via `Tenant`, `Usuario`, `TenantUsuario`, onboarding oficial e RLS;
- Wizard como fluxo oficial da implantação;
- `UnidadeProdutiva` como pré-condição;
- ERP comum via `/api/v1/integracoes/erp/*`;
- Sankhya apenas como provider-specific para suporte técnico e operações próprias;
- observabilidade técnica via backoffice/suporte, sem transformar logs brutos em superfície comum;
- engines assíncronos sem dependência síncrona indevida da transação principal.

Não foi mantido no runbook nenhum passo que:

- crie dados por caminho paralelo;
- trate Sankhya como domínio ERP;
- ignore o Wizard;
- dependa de dispatcher multiprovider;
- exija `/api/v1/integracoes/erp/logs`.

## 8. Auditoria da implementação atual

Matriz resumida de evidências:

| Passo do Dry Run | Interface | Endpoint | Serviço | Persistência | Teste/Evidência | Executável hoje? |
| ---------------- | --------- | -------- | ------- | ------------ | --------------- | ---------------- |
| Onboarding | Web | `/api/v1/onboarding/*` | `OnboardingService` | `Tenant`, `Usuario`, `TenantUsuario` | `core/routers/onboarding.py` | sim |
| Wizard | Web | `/api/v1/wizard/*` | `ImplantacaoService`, `ChecklistEngine` | `wizard_*` | `tests/unit/wizard/test_wizard_api.py` | sim |
| Campo offline | PWA | `/api/v1/sync/*` | sync push/pull + caderno | Dexie + tabelas oficiais | `test_field_pwa01_offline_sync.py` | sim |
| Estoque | Web | `/api/v1/estoque/*` | `EstoqueService` | saldo, lotes, movimentos | `estoque-implantacao-assistida.spec.ts` | sim |
| Romaneio | Web | `/api/v1/agricola/romaneios/*` | `RomaneioService` | romaneio + produto colhido | `test_romaneio_calculo.py` | sim |
| Comercialização mínima | Web | `/api/v1/comercializacoes/*` | `ComercializacaoService` | comercialização + receita | `test_comercializacao.py` | sim, com assistência |
| ERP comum | Web | `/api/v1/integracoes/erp/*` | runtime oficial + façade | health/jobs/associações | `test_erp_router.py` | sim |

## 9. Auditoria de extensibilidade operacional

Separação definida no runbook:

- núcleo genérico do piloto:
  - governança;
  - Wizard;
  - estrutura produtiva;
  - Campo PWA;
  - estoque;
  - custos;
  - colheita;
  - comercialização mínima;
  - observabilidade;
  - cenários de falha.
- extensão do provider ERP:
  - Sankhya;
  - teste de conexão técnico;
  - logs provider-specific;
  - operações específicas de suporte.
- extensão do segmento café:
  - cultura foco do piloto;
  - escopo mínimo de colheita/romaneio;
  - exclusão explícita da exportação como bloqueador padrão.

Isso permite reutilização futura sem criar abstração prematura.

## 10. Lacunas do roteiro anterior

Antes da atualização, o `RUNBOOK-01` ainda não definia com precisão suficiente:

- critérios de entrada;
- massa de dados mínima;
- cenários A-E em ordem executável;
- critérios de interrupção imediata;
- estratégia formal de evidências;
- separação explícita entre tenant, backoffice e logs provider-specific;
- matriz de responsabilidades;
- distinção entre passos completos, assistidos e fora do escopo.

## 11. Cobertura dos cenários A-E

- Cenário A: coberto com governança, Wizard, estrutura mínima e readiness.
- Cenário B: coberto com operação offline, reabertura do app, retomada de rede, sync, idempotência, estoque e custo.
- Cenário C: coberto no escopo mínimo; cadeia avançada de café permanece fora do Dry Run base.
- Cenário D: coberto com superfície ERP comum e operações Sankhya provider-specific separadas.
- Cenário E: coberto com falhas controladas de Campo PWA, estoque, ERP, engines e Wizard.

## 12. Critérios de entrada, sucesso e interrupção

Foram consolidados no runbook:

- critérios objetivos de entrada;
- critérios de sucesso para aprovação do Dry Run;
- critérios de interrupção imediata por risco real;
- classificação final `GO`, `GO COM RESSALVAS` ou `NO-GO`.

## 13. Matriz de responsabilidades

O runbook atualizado passou a exigir papéis explícitos para:

- responsável técnico AgroSaaS;
- responsável funcional AgroSaaS;
- owner/admin do cliente;
- operador Web;
- operador Campo PWA;
- suporte/backoffice;
- responsável ERP;
- decisor GO/NO-GO.

## 14. Estratégia de evidências

Foi formalizado:

- padrão de nome `DRYRUN-[CENARIO]-[PASSO]-[AAAA-MM-DD]-[SEQ]`;
- tipos aceitos de evidência;
- proibição de segredos, credenciais e payloads sensíveis.

## 15. Observabilidade

Decisão operacional:

- tenant acompanha superfícies funcionais;
- suporte/backoffice acompanha health, jobs, timeline, diagnóstico e logs técnicos;
- logs seguem provider-specific e não entram como superfície ERP comum.

## 16. Contingência

O runbook consolidado passou a registrar:

- o que interrompe imediatamente;
- o que exige retorno a D-1;
- o que pode ser tratado como ressalva assistida;
- quem decide continuar ou interromper.

## 17. Riscos

- comercialização e pós-colheita seguem com cobertura fim a fim parcial;
- observabilidade técnica ainda depende de backoffice/suporte;
- o Dry Run continua manual-assistido, não automatizado ponta a ponta;
- a cadeia avançada do café permanece fora do escopo base.

Esses riscos foram tratados como restrições operacionais registradas, não como motivo para criar nova arquitetura ou novo runbook.

## 18. Alterações documentais realizadas

- atualização de [RUNBOOK-01-EXECUCAO-D-5-A-D+7.md](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md) para torná-lo o roteiro único executável do Dry Run;
- criação deste relatório em [PILOT-DRYRUN-01-AUDITORIA-CONSOLIDACAO-RUNBOOK.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-DRYRUN-01-AUDITORIA-CONSOLIDACAO-RUNBOOK.md).

## 19. Validações executadas

Comandos executados ou previstos para validação leve:

- `git status --short`
- `git diff --check`
- leitura dos documentos do pacote piloto e dos runbooks auxiliares
- coleta leve dos testes e peças centrais do runbook

## 20. Limitações

- não foram executadas suítes pesadas nem integrações externas reais;
- não foram validadas credenciais nem ambientes reais do cliente;
- a auditoria se apoia em documentação, código, rotas e coleta leve de testes, não em Dry Run real executado nesta sessão.

## 21. Veredicto

`GO COM RESSALVAS — runbook executável com ajustes operacionais registrados`

Justificativa:

- existe agora um único runbook oficial;
- o roteiro está em ordem cronológica;
- critérios de entrada, sucesso e interrupção foram explicitados;
- cenários A-E foram consolidados;
- responsabilidades e evidências foram definidas;
- as ressalvas do `PILOT-E2E-01` foram transformadas em instruções operacionais, sem exigir implementação funcional nova.
