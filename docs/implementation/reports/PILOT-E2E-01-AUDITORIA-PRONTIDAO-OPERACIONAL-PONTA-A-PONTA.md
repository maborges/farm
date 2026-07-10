# PILOT-E2E-01 — AUDITORIA DE PRONTIDÃO OPERACIONAL PONTA A PONTA

## 1. Resumo executivo

Veredicto desta auditoria: `GO COM RESSALVAS — pronto para Dry Run assistido`.

A base arquitetural oficial está efetivamente consolidada no repositório: multi-tenancy com isolamento por tenant, Wizard de implantação, domínios operacionais principais, Campo PWA offline-first, engines assíncronos, integrações ERP via superfície `/api/v1/integracoes/erp/*` e cobertura relevante de testes por domínio.

O repositório comprova viabilidade para um primeiro piloto controlado assistido, especialmente no fluxo:

`tenant -> onboarding -> wizard -> estrutura produtiva -> safra -> execução -> estoque -> custos -> colheita -> financeiro -> ERP`

As principais ressalvas encontradas não bloqueiam um Dry Run assistido, mas reduzem a margem para uma operação desacompanhada:

- comercialização e pós-colheita de café/exportação têm evidência parcial, não fim-a-fim completo;
- há dependências de suporte/backoffice e observabilidade técnica ainda mais fortes que a experiência self-service do tenant;
- a fachada ERP está correta para o provider atual, mas o router ainda resolve o provider de forma Sankhya-first internamente;
- parte da evidência ponta a ponta existe em testes dirigidos e contratos, mas não como suíte integrada única do piloto.

## 2. Escopo auditado

Foram auditados, com foco em evidência de código, contratos, rotas, modelos, testes e documentos:

- governança de tenant, onboarding, assinatura, `TenantUsuario`, RLS e isolamento;
- Wizard oficial em `/dashboard/implantacao/wizard` e `/api/v1/wizard`;
- estrutura territorial e produtiva;
- cadastros essenciais;
- planejamento/safra/operações;
- Campo PWA offline-first;
- estoque, implantação assistida, custos operacionais;
- romaneios, colheita, rastreabilidade inicial e comercialização;
- financeiro e efeitos econômicos;
- integração ERP oficial e provider Sankhya;
- Domain Events, Outbox, Alert Engine, Notification Engine e Recommendation Engine;
- superfícies Web, Campo PWA e Backoffice;
- testes e evidências automatizadas.

## 3. Metodologia

Critério adotado:

- `PRONTO`: fluxo funcional conectado com evidência suficiente de implementação e validação;
- `PARCIAL`: implementação relevante, mas com lacuna de cobertura, UX, integração final ou escopo incompleto;
- `AUSENTE`: não foi localizada evidência suficiente de implementação operacional;
- `NÃO APLICÁVEL AO PILOTO`: não é necessária para o piloto controlado inicial;
- `BLOQUEADOR`: impediria o início seguro do Dry Run.

Fontes priorizadas:

- routers, services, models, schemas e testes do backend;
- componentes, páginas e hooks do frontend web e Campo PWA;
- relatórios e contratos arquiteturais já aprovados;
- coleta leve de testes, sem executar suítes pesadas dependentes de infraestrutura externa.

## 4. Arquitetura reutilizada

Infraestrutura oficial já reutilizável e comprovada:

- multi-tenancy e RLS em [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py);
- onboarding/assinatura/owner em [services/api/core/services/onboarding_service.py](/opt/lampp/htdocs/farm/services/api/core/services/onboarding_service.py);
- Wizard oficial em [services/api/wizard/router.py](/opt/lampp/htdocs/farm/services/api/wizard/router.py), [services/api/wizard/services.py](/opt/lampp/htdocs/farm/services/api/wizard/services.py), [services/api/wizard/models.py](/opt/lampp/htdocs/farm/services/api/wizard/models.py), [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py) e [services/api/wizard/state_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/state_engine.py);
- ERP runtime oficial com `ErpReadinessService`, `MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationHealth`, `IntegrationJob`, `ExternalRecordAssociation` e superfície `/api/v1/integracoes/erp/*` em [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py);
- estoque e ledger canônicos em [services/api/operacional/services/estoque_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/estoque_service.py);
- apropriação de custos operacionais em [services/api/agricola/custos/operational_cost_service.py](/opt/lampp/htdocs/farm/services/api/agricola/custos/operational_cost_service.py);
- romaneios/colheita/rastreabilidade inicial em [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py);
- engines assíncronos e outbox em `services/api/events/*`, `services/api/alert_engine/*`, `services/api/notifications/*` e `services/api/recommendations/*`;
- Campo PWA offline-first em `apps/campo/src/lib/sync/*`, `apps/campo/src/lib/caderno-offline.ts` e store local.

## 5. Mapa do fluxo ponta a ponta

Fluxo oficial comprovado no código:

`cadastro/assinatura -> owner -> onboarding -> wizard -> unidade produtiva -> território -> safra -> operação/execução -> estoque/custos -> romaneio/receita -> comercialização/financeiro -> ERP -> observabilidade`

Superfícies principais:

- Web tenant: dashboards, cadastros, agrícola, estoque, financeiro, ERP e wizard;
- Campo PWA: execução, cache local, sync pull/push, evidências e retomada offline;
- Backoffice: tenants, ERP, observabilidade técnica e suporte operacional;
- APIs oficiais: domínio por domínio e integrações ERP;
- APIs provider-specific: Sankhya e logs técnicos.

## 6. Matriz de prontidão

| Etapa | Status | Frontend | Endpoint | Serviço | Persistência | Evento/Efeito | Testes | Impacto no piloto |
| ----- | ------ | -------- | -------- | ------- | ------------ | ------------- | ------ | ----------------- |
| Entrada do cliente e governança | PRONTO | telas auth/onboarding e seleção de tenant | `/api/v1/onboarding/*`, auth | `OnboardingService` | `Tenant`, `Usuario`, `TenantUsuario`, assinatura | criação de owner e tenant sem fluxo paralelo | guardrails + E2E tenant | base segura para iniciar piloto |
| Wizard de implantação | PRONTO | `/dashboard/implantacao/wizard` | `/api/v1/wizard/*` | `ImplantacaoService`, `ChecklistEngine` | `wizard_*` | bloqueios, pendências, histórico, GO-LIVE | 20 testes coletados de API wizard | controla prontidão operacional |
| Estrutura territorial e produtiva | PRONTO | páginas de propriedades/talhões | cadastros de propriedades/imóveis | services de propriedades/imóveis/talhão | `unidades_produtivas`, `cadastros_areas_rurais`, `propriedade_imovel` | estrutura mínima para safra e operação | integração + unitários | habilita fazenda/talhão/safra |
| Cadastros essenciais mínimos | PARCIAL | múltiplas telas de cadastros | rotas por domínio | services específicos | tabelas de cadastros | liberam módulos e checklist | cobertura dispersa | suficiente para piloto assistido |
| Planejamento agrícola | PARCIAL | páginas de safras, tarefas, orçamento, checklist | `/api/v1/agricola/safras/*` e afins | services de safras/operações/tarefas | `safras`, `safra_talhoes`, etc. | avanço de fases e contexto produtivo | E2E safra completa | existe, mas evidência de consumo total pelo campo ainda é parcial |
| Campo PWA e execução offline | PRONTO | `apps/campo` | `/api/v1/sync/*`, `/api/v1/agricola/caderno/offline-sync` | sync push/pull + `CadernoCampoService` | Dexie + tabelas oficiais | idempotência, conflito, retry, retomada | 5 testes coletados offline sync | forte para operação assistida em campo |
| Estoque | PRONTO | páginas e implantação assistida | `/api/v1/estoque/*` | `EstoqueService` | saldos, lotes, movimentos, reservas | ledger, reserva, consumo, ajustes | integração e unitários | suporta consumo real e governança |
| Custos operacionais | PARCIAL | dashboards financeiro/agricola/frota custos | custos/agricola/financeiro | `OperationalCostAllocationService` | `CostAllocation`, `Despesa` | apropriação canônica e despesa | testes dedicados encontrados | motor canônico existe; evidência fim-a-fim total ainda parcial |
| Colheita e romaneio | PRONTO | páginas de romaneios/colheita | `/api/v1/agricola/romaneios/*` | `RomaneioService` | romaneio + `ProdutoColhido` | cálculo, produtividade, receita legada, produto colhido | E2E safra + unitários | suficiente para Dry Run |
| Beneficiamento/rastreabilidade café | PARCIAL | páginas de beneficiamento detectadas | parte das rotas existe indiretamente | serviços não auditados fim a fim nesta execução | lotes/romaneios/produto colhido | rastreabilidade inicial existe, cadeia café completa não comprovada | docs e páginas encontradas | exige operação assistida |
| Comercialização | PARCIAL | docs e telas encontradas | `/api/v1/comercializacoes/*` | `ComercializacaoService` | `ComercializacaoCommodity`, `Receita` | status `RASCUNHO -> CONFIRMADO -> EM_TRANSITO -> ENTREGUE -> FINALIZADO` | unitários encontrados | fluxo existe, mas integração total com estoque físico é parcial |
| Financeiro | PARCIAL | dashboards e custos/receitas | `/api/v1/financeiro/*` | services financeiros | receitas, despesas, planos, lançamentos | contas a receber/pagar e DRE parcial | testes financeiros e E2E safra | pronto para piloto assistido, não para autonomia total |
| Integração ERP | PRONTO | console ERP e backoffice ERP | `/api/v1/integracoes/erp/*` + `/sankhya/*` | readiness + sync Sankhya | runtime oficial de integrações | health, jobs, timeline, diagnóstico, associações | relatórios + testes ERP já existentes | adequado para provider atual |
| Engines operacionais | PRONTO | tenant + backoffice | rotas/dispatchers próprios | outbox, alerts, notifications, recommendations | outbox + modelos dos engines | assíncronos e desacoplados | testes anti-acoplamento e bridge | não devem bloquear transação principal |
| Observabilidade e suporte | PARCIAL | console ERP, backoffice, telas de sync | health/jobs/timeline/diagnóstico + logs Sankhya | serviços de integração e engines | `IntegrationJob`, `IntegrationHealth`, `SankhyaSyncLog` | suporte funcional + técnico | testes e relatórios | suficiente para suporte assistido |

## 7. Análise por domínio

### 7.1 Entrada do cliente e governança

Evidências:

- [services/api/core/services/onboarding_service.py](/opt/lampp/htdocs/farm/services/api/core/services/onboarding_service.py) cria `Usuario`, `Tenant`, `TenantUsuario` com `is_owner=True` e `AssinaturaTenant`;
- [services/api/core/routers/onboarding.py](/opt/lampp/htdocs/farm/services/api/core/routers/onboarding.py) concentra o fluxo oficial de onboarding e convites;
- [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py) aplica contexto de tenant, sessão ativa e RLS;
- [services/api/tests/e2e/test_tenant_isolation.py](/opt/lampp/htdocs/farm/services/api/tests/e2e/test_tenant_isolation.py) cobre isolamento entre tenants;
- [services/api/tests/unit/test_pilot_onboarding_governance_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/test_pilot_onboarding_governance_guardrails.py) protege contra fluxos paralelos indevidos.

Classificação: `PRONTO`.

### 7.2 Wizard de implantação

Evidências:

- estados oficiais `READY_FOR_GO_LIVE`, `GO_LIVE`, `STABILIZATION` e bloqueio por ausência de `unidade_produtiva_id` em [services/api/wizard/models.py](/opt/lampp/htdocs/farm/services/api/wizard/models.py);
- máquina de estados com validação de checklist mínimo e pendência crítica em [services/api/wizard/state_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/state_engine.py);
- checklist automático integrado a `ErpReadinessService`, depósitos, plano de contas, catálogo e unidade produtiva em [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py);
- API e resumo operacional em [services/api/wizard/router.py](/opt/lampp/htdocs/farm/services/api/wizard/router.py);
- 20 testes coletados em `services/api/tests/unit/wizard/test_wizard_api.py`.

Classificação: `PRONTO`.

### 7.3 Estrutura territorial e produtiva

Evidências:

- módulos próprios de propriedades e visão `propriedade_imovel`;
- `UnidadeProdutiva` e `AreaRural` usados como pré-condição em Wizard, estoque, safra e ERP;
- separação arquitetural entre domínio fundiário/documental e operacional/produtivo visível nos pacotes `core/cadastros/propriedades`, `core/cadastros/propriedade_imovel` e `imoveis`.

Classificação: `PRONTO`.

### 7.4 Cadastros essenciais

Há evidência de cadastros e dependências para produtos, depósitos, pessoas, propriedades, culturas, talhões, safras, equipamentos e plano de contas. O ponto fraco é a comprovação uniforme de UX e fluxo único para todos os cadastros do piloto.

Classificação: `PARCIAL`.

### 7.5 Planejamento agrícola

Evidências:

- módulos de safras, checklist, operações, tarefas, cenários, orçamento e financeiro agrícola em `apps/web/src/app/(dashboard)/agricola/safras/*`;
- services e models em `services/api/agricola/safras/*`;
- E2E de safra completa em [services/api/tests/e2e/test_safra_completa.py](/opt/lampp/htdocs/farm/services/api/tests/e2e/test_safra_completa.py).

Lacuna:

- não foi comprovado nesta auditoria que todo o planejamento entra no Campo PWA sem caminhos paralelos ou simplificações por módulo.

Classificação: `PARCIAL`.

### 7.6 Execução operacional pelo Campo PWA

Evidências:

- `push`, `pull`, `worker`, fila local, recuperação de `IN_FLIGHT`, contagem de pendências e retomada online em `apps/campo/src/lib/sync/*`;
- `createOfflineCadernoEvent` e evidências offline em [apps/campo/src/lib/caderno-offline.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/caderno-offline.ts);
- detecção de conflitos, retry limitado, quarentena `FAILED`, idempotência por `device_id`/`local_id` e sync independente de upload de evidências;
- testes de sync offline em [services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py](/opt/lampp/htdocs/farm/services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py).

Classificação: `PRONTO`.

### 7.7 Estoque

Evidências:

- domínio oficial em [services/api/operacional/routers/estoque.py](/opt/lampp/htdocs/farm/services/api/operacional/routers/estoque.py) e [services/api/operacional/services/estoque_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/estoque_service.py);
- validação de contexto por tenant/unidade/deposito/lote;
- suporte a lotes, validade, reservas, consumo, transferências, ajustes, auditoria e estoque mínimo;
- implantação assistida com teste de fluxo HTTP em [services/api/tests/integration/operacional/test_estoque_implantacao.py](/opt/lampp/htdocs/farm/services/api/tests/integration/operacional/test_estoque_implantacao.py);
- E2E Playwright em [apps/web/tests/e2e/estoque-implantacao-assistida.spec.ts](/opt/lampp/htdocs/farm/apps/web/tests/e2e/estoque-implantacao-assistida.spec.ts).

Classificação: `PRONTO`.

### 7.8 Custos operacionais

Evidências:

- camada canônica de custos em [services/api/agricola/custos/operational_cost_service.py](/opt/lampp/htdocs/farm/services/api/agricola/custos/operational_cost_service.py);
- apropriação via `CostAllocation` e criação opcional de `Despesa`;
- existência de serviços de custo de frota (`frota_custo_service.py`, `frota_custo_consolidado_service.py`) e convergência arquitetural declarada.

Lacuna:

- a convergência fim-a-fim entre todos os lançamentos operacionais, frota, RH e rentabilidade não foi comprovada com um cenário único de teste nesta auditoria.

Classificação: `PARCIAL`.

### 7.9 Colheita, café e rastreabilidade

Evidências:

- `RomaneioService` calcula peso padrão, descontos, produtividade e receita em [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py);
- criação automática de `ProdutoColhido` para rastreabilidade inicial por safra/talhão/romaneio;
- router oficial em [services/api/agricola/romaneios/router.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/router.py).

Lacuna:

- beneficiamento específico de café, classificação avançada e exportação aparecem como estrutura/páginas/documentação, mas não foram comprovados como fluxo completo e integrado ao piloto nesta execução.

Classificação:

- colheita e romaneio: `PRONTO`;
- cadeia café/beneficiamento/exportação: `PARCIAL`.

### 7.10 Comercialização e financeiro

Evidências:

- status oficiais e efeitos colaterais em [services/api/financeiro/comercializacao/service.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/service.py);
- transições `RASCUNHO -> CONFIRMADO -> EM_TRANSITO -> ENTREGUE -> FINALIZADO`;
- geração de receita e reserva/venda de `ProdutoColhido`.

Lacuna:

- comercialização existe, mas a evidência de encadeamento total com estoque físico, entrega e rentabilidade analítica não está consolidada em um teste único do piloto;
- parte do efeito ainda é mais econômico/documental do que logístico.

Classificação: `PARCIAL`.

### 7.11 Integração ERP

Evidências:

- superfície ERP oficial em [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py);
- readiness, health, jobs, timeline, diagnóstico e associações disponíveis para UI genérica;
- provider Sankhya preservado para operações técnicas e logs em `/api/v1/integracoes/sankhya/*`.

Ressalva:

- o router ERP ainda delega internamente de forma Sankhya-first e devolve `501` para outros providers. Isso é aceitável no estágio atual porque ainda não existe segundo provider real.

Classificação: `PRONTO` para o piloto com Sankhya atual.

### 7.12 Engines operacionais

Evidências:

- Outbox em `services/api/events/outbox_*`;
- Alert Engine em `services/api/alert_engine/*`;
- Notification Engine em `services/api/notifications/*`;
- Recommendation Engine em `services/api/recommendations/*`;
- teste antiacoplamento em [services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py](/opt/lampp/htdocs/farm/services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py);
- bridge HIGH/URGENT entre recomendações e notificações em [services/api/tests/unit/recommendations/test_recommendation_notification_bridge.py](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendation_notification_bridge.py).

Classificação: `PRONTO`.

## 8. Web versus Campo PWA versus Backoffice

Web tenant:

- concentra onboarding, wizard, cadastros, agrícola, estoque, custos, financeiro e console ERP;
- é a principal superfície do piloto assistido.

Campo PWA:

- concentra execução, captura offline, sincronização, evidências e recomendações locais;
- possui desenho offline-first real e não apenas responsivo.

Backoffice:

- concentra suporte, tenants, ERP técnico e observabilidade mais profunda;
- ainda é importante para suporte assistido do primeiro piloto.

Conclusão:

- o piloto não depende só do tenant self-service;
- o modo operacional recomendado é assistido, com apoio de backoffice em incidentes, configuração e diagnóstico.

## 9. Análise dos engines

Pontos comprovados:

- engines não devem invalidar a transação principal;
- outbox e publisher permanecem como ponto comum de integração;
- recomendações e notificações possuem deduplicação e regras de elegibilidade;
- há proteção explícita contra acoplamento direto entre alertas, notificações e serviços de domínio.

Classificação: `PRONTO`.

## 10. Análise da integração ERP

Arquitetura oficial observada:

- leituras comuns em `/api/v1/integracoes/erp/*`;
- operações técnicas e provider-specific em `/api/v1/integracoes/sankhya/*`;
- `logs` permanecem provider-specific, coerente com o fechamento da Fase B.

Conclusão:

- para o primeiro piloto com ERP externo atual, a arquitetura está adequada;
- não há motivo técnico para introduzir dispatcher multiprovider agora;
- a operação pode seguir Sankhya como provider atual e adapter técnico.

## 11. Análise dos testes

Evidência localizada:

- testes E2E e de integração para tenant isolation;
- testes unitários e de API do Wizard;
- testes unitários de sync offline do Campo;
- testes de implantação assistida de estoque;
- testes de safra completa;
- testes de custos, estoque, recomendações, notificações e outbox.

Limitação:

- não existe, nesta auditoria, uma suíte única que execute integralmente os cenários A-E do piloto;
- a confiança vem de cobertura distribuída por domínio, não de um runbook automatizado único.

## 12. Lacunas P0, P1, P2 e P3

### P0

Nenhum bloqueador P0 foi comprovado no repositório para um `Dry Run assistido`.

### P1

- cadeia café/beneficiamento/classificação/exportação não tem evidência ponta a ponta suficiente;
- comercialização existe, mas a amarração total com logística/estoque final e rentabilidade ainda é parcial;
- operação do piloto depende de suporte de backoffice para observabilidade e incidentes mais técnicos.

### P2

- ausência de suíte automatizada única cobrindo os cenários do piloto do início ao fim;
- cadastros essenciais aparecem distribuídos em vários domínios e telas, sem comprovação uniforme de fluxo único assistido;
- ERP router ainda com resolução Sankhya-first interna, embora isso não seja bloqueador com provider único.

### P3

- multiprovider real no ERP;
- abstrações adicionais de observabilidade para tenant;
- exportação e fluxos enterprise não essenciais ao piloto controlado.

## 13. Riscos do piloto

- risco de dependência de operação assistida em fluxos de café mais específicos;
- risco de ajuste manual/backoffice em incidentes de integração ERP ou sincronização de dados mestres;
- risco de cobertura desigual entre módulos financeiros/comercialização e o fluxo agrícola principal;
- risco baixo de isolamento multi-tenant, pois há evidência forte de governança e testes.

## 14. Cenários que podem ser executados imediatamente

### Cenário A — preparação do cliente

`PRONTO`

Baseado em onboarding, owner, tenant, wizard, unidade produtiva e bloqueios de prontidão.

### Cenário B — operação agrícola

`PRONTO`

Baseado em safra, PWA offline, sync, estoque e custos canônicos, com ressalva de operação assistida em incidentes.

### Cenário D — integração ERP

`PRONTO`

Baseado na superfície ERP genérica já criada e migrada, com provider Sankhya preservado.

## 15. Cenários que exigem operação assistida

### Cenário C — colheita e comercialização

`PARCIAL`

Romaneio e receita estão evidentes; comercialização e cadeia café avançada exigem suporte assistido.

### Cenário E — falha operacional controlada

`PARCIAL`

Há evidência de comportamento esperado para perda de conexão, repetição de push, conflitos e indisponibilidade parcial dos engines, mas não como runbook único automatizado.

## 16. Cenários ainda não suportados de forma comprovada

- exportação e requisitos avançados não essenciais do café;
- multiprovider ERP real;
- autonomia total do tenant para toda a observabilidade técnica sem backoffice.

## 17. Plano incremental recomendado

Sem criar nova arquitetura, o próximo incremento recomendado é operacional, não estrutural:

1. consolidar um runbook de Dry Run assistido reutilizando Wizard, ERP console, implantação assistida de estoque e cenários de sync offline;
2. reforçar cenários automatizados de comercialização/financeiro/café sobre os serviços já existentes;
3. preparar playbook de suporte do piloto usando timeline/diagnóstico ERP, jobs e logs Sankhya provider-specific;
4. só depois ampliar cobertura de beneficiamento/classificação/exportação se o piloto realmente exigir.

## 18. Comandos de validação executados

Leitura e inventário:

```bash
rg --files services/api apps/campo apps/web | rg 'wizard|onboarding|tenant|rls|outbox|alert_engine|notifications|recommend|estoque|comercializacao|cost|cust|romaneio|safra|talhao|unidade_produtiva|propriedade|imovel|dexie|sync|offline|job|health'
git status --short
sed -n '1,240p' services/api/wizard/router.py
sed -n '1,260p' services/api/wizard/services.py
sed -n '1,260p' services/api/wizard/models.py
sed -n '1,260p' services/api/wizard/state_engine.py
sed -n '1,260p' services/api/wizard/checklist_engine.py
sed -n '1,260p' services/api/core/dependencies.py
sed -n '1,260p' services/api/core/routers/onboarding.py
sed -n '1,260p' services/api/core/services/onboarding_service.py
sed -n '1,260p' apps/campo/src/lib/sync/push.ts
sed -n '1,260p' apps/campo/src/lib/sync/pull.ts
sed -n '1,260p' apps/campo/src/lib/sync/worker.ts
sed -n '1,260p' apps/campo/src/lib/caderno-offline.ts
sed -n '1,260p' services/api/operacional/routers/estoque.py
sed -n '1,260p' services/api/operacional/services/estoque_service.py
sed -n '1,260p' services/api/agricola/custos/operational_cost_service.py
sed -n '1,260p' services/api/financeiro/comercializacao/router.py
sed -n '1,260p' services/api/financeiro/comercializacao/service.py
sed -n '1,280p' services/api/agricola/romaneios/service.py
sed -n '1,260p' services/api/integracoes/erp/router.py
```

Coleta leve de testes:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/wizard/test_wizard_api.py --collect-only -q
services/api/.venv/bin/pytest services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py --collect-only -q
services/api/.venv/bin/pytest services/api/tests/integration/operacional/test_estoque_implantacao.py --collect-only -q
```

Validação final documental:

```bash
git diff --check
```

## 19. Limitações da auditoria

- não foi executada suíte completa ponta a ponta;
- não foram simuladas integrações externas reais, credenciais reais ou banco externo de produção;
- a auditoria privilegiou evidência local de código, contratos, testes e telas;
- algumas áreas enterprise e de café foram classificadas como `PARCIAL` por insuficiência de comprovação fim a fim, não por ausência total de implementação.

## 20. Veredicto final

Resultado final:

`GO COM RESSALVAS — pronto para Dry Run assistido`

Fundamentação objetiva:

- não foi localizado bloqueador P0 inequívoco para um primeiro piloto controlado assistido;
- a espinha dorsal do fluxo operacional existe e está conectada no código;
- Wizard, governança, isolamento multi-tenant, PWA offline, estoque, custos canônicos, colheita e ERP estão presentes;
- as maiores lacunas remanescentes concentram-se em cobertura ponta a ponta de comercialização/café/exportação e no grau de autonomia operacional sem suporte.

Conclusão prática:

- o AgroSaaS já está em condição de executar um primeiro Dry Run assistido com produtor de café e ERP externo;
- a recomendação não é abrir operação totalmente desassistida ainda;
- qualquer correção futura deve reutilizar os componentes oficiais já existentes, sem nova arquitetura paralela.
