# PILOT-03 — Auditoria do Processo de Implantação e Execução do Primeiro Piloto

## Escopo auditado

Auditoria documental da jornada completa do primeiro cliente piloto, desde assinatura até o início da operação assistida, sem implementar funcionalidades novas e sem alterar contratos.

Itens auditados:

- assinatura e ativação do tenant;
- onboarding comercial e operacional;
- criação e uso de `UnidadeProdutiva`;
- estrutura territorial mínima da fazenda;
- checklists e bloqueios de go-live;
- Campo PWA offline-first;
- monitoramento e diagnósticos;
- documentação operacional do piloto;
- testes de guardrail e integração.

## Conclusão executiva

O AgroSaaS já possui a espinha dorsal necessária para iniciar a implantação controlada do primeiro cliente.

O que existe hoje cobre:

- criação de tenant, owner/admin e assinatura;
- validação de ativação;
- onboarding técnico com bloqueio de dashboard;
- Wizard de implantação com estados, etapas, checklist, pendências e go-live;
- Campo PWA com ativação, sessão local, sync pull/push e recuperação de falhas;
- observabilidade básica suficiente para acompanhar o início do piloto;
- documentação de operação e guardrails do primeiro piloto.

O que ainda não existe como produto final:

- um onboarding completamente guiado e autoexplicativo do primeiro uso;
- automação total de preparação da estrutura operacional;
- monitoramento específico de piloto com KPI dedicado em uma única tela;
- um fluxo único e unificado para toda a implantação comercial, operacional e de campo.

Decisão recomendada:

- **GO para implantação controlada**
- **NO-GO para autoatendimento totalmente autônomo**

## Matriz de auditoria

| Item | Situação | O que existe | Reutilização | Lacuna real |
| --- | --- | --- | --- | --- |
| Assinatura / ativação | EXISTE E ATENDE | `POST /onboarding/assinante`, token de ativação, Stripe checkout, criação de tenant, owner e assinatura | Reutilizar `OnboardingService` e o fluxo de ativação | Nenhuma para o piloto controlado |
| Onboarding comercial | EXISTE E ATENDE | `GET /onboarding/ativar/{token}`, `POST /onboarding/ativar/{token}`, convite de equipe | Reutilizar o fluxo atual | Fragmentado, mas funcional |
| Onboarding operacional | EXISTE PARCIALMENTE | `GET /onboarding/status`, `apps/web/src/components/auth/onboarding-guard.tsx` | Reutilizar como guardrail de entrada | A tela `onboarding/configurar` é genérica e não conduz toda a implantação |
| Tenant / owner / plano | EXISTE E ATENDE | `Tenant`, `Usuario`, `TenantUsuario`, `AssinaturaTenant`, `Fatura` | Reutilizar modelos e services | Nenhuma para o piloto |
| `UnidadeProdutiva` | EXISTE E ATENDE | Modelo oficial com `tenant_id`, ativo, dados documentais e legados | Reutilizar como âncora operacional | Nenhuma crítica |
| Estrutura da fazenda | EXISTE E ATENDE | `AreaRural`, `MatriculaImovel`, hierarquia territorial e infraestrutura | Reutilizar para sede, gleba, talhão, área operacional, APP, reserva legal e depósitos | A profundidade da hierarquia é alta, mas já cobre o piloto |
| Cadastros básicos | EXISTE PARCIALMENTE | Pessoas, produtos, depósitos, equipamentos, plano de contas e áreas rurais já existem no backend e no web | Reutilizar onde já houver cadastro | Nem todos os cadastros têm a mesma maturidade de UX |
| Wizard de implantação | EXISTE E ATENDE | `ImplantacaoOperacional`, etapas, checklist, pendências, histórico e transições | Reutilizar integralmente | Nenhuma crítica para o piloto |
| Go-live | EXISTE E ATENDE | `READY_FOR_GO_LIVE`, `GO_LIVE`, `STABILIZATION`, bloqueio por checklist e `UnidadeProdutiva` | Reutilizar estado e validações | Nenhuma para o primeiro piloto |
| Checklists | EXISTE E ATENDE | Checklist automático com evidência e pendência crítica | Reutilizar `ChecklistEngine` e `ChecklistService` | Sem evidência, o go-live continua bloqueado corretamente |
| Campo PWA | EXISTE E ATENDE | Ativação via PIN, sessão local, sync pull/push, recuperação de `IN_FLIGHT`, fila local | Reutilizar `runSync`, `pullSync`, `pushSync`, `session-store` | Não existe wizard próprio do Campo para implantação |
| Monitoramento | EXISTE E ATENDE | Logs, healthchecks, auditoria, alertas e recomendações | Reutilizar observabilidade já consolidada | Não há dashboard único do piloto; a operação depende de páginas separadas |
| Documentação | EXISTE E ATENDE | Plano do piloto, guardrails do Wizard, observabilidade, runbooks e validações | Reutilizar a documentação já publicada | Está dispersa, mas suficiente |

## Fluxos auditados em detalhe

### 1. Assinatura

O fluxo de contratação existe e cria a base mínima do cliente.

Evidências:

- [services/api/core/routers/onboarding.py](/opt/lampp/htdocs/farm/services/api/core/routers/onboarding.py#L60)
- [services/api/core/services/onboarding_service.py](/opt/lampp/htdocs/farm/services/api/core/services/onboarding_service.py#L40)
- [services/api/core/models/tenant.py](/opt/lampp/htdocs/farm/services/api/core/models/tenant.py#L8)

O que já atende:

- valida CPF/CNPJ e duplicidade;
- cria `Usuario`, `Tenant`, `TenantUsuario` e `AssinaturaTenant`;
- gera `Fatura` quando aplicável;
- faz ativação com token;
- entrega autenticação imediata após cadastro.

O que exige apenas extensão:

- unificar a história visual do fluxo comercial com o fluxo operacional;
- tornar mais explícita a transição entre pagamento e início da implantação.

### 2. Onboarding

O onboarding existe em duas camadas:

- comercial/ativação;
- operacional via status e guard.

Evidências:

- [apps/web/src/components/auth/onboarding-guard.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/auth/onboarding-guard.tsx#L15)
- [services/api/core/routers/onboarding.py](/opt/lampp/htdocs/farm/services/api/core/routers/onboarding.py#L260)
- [docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md#L53)

O que já atende:

- o guard do web consulta `/onboarding/status`;
- o backend bloqueia acesso quando o onboarding não está completo;
- há compatibilidade com tenants legados;
- há uma página de configuração inicial.

O que é parcial:

- a página `onboarding/configurar` é útil, mas não é um wizard completo de implantação da fazenda;
- a conclusão do onboarding não conduz automaticamente o cliente por toda a estrutura operacional.

### 3. Unidade Produtiva

`UnidadeProdutiva` é o centro da implantação operacional.

Evidências:

- [services/api/core/models/unidade_produtiva.py](/opt/lampp/htdocs/farm/services/api/core/models/unidade_produtiva.py#L8)
- [services/api/wizard/state_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/state_engine.py#L131)
- [docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-01-PLANO-OPERACIONAL-CONTROLADO.md#L72)

O que já atende:

- existe modelo oficial com `tenant_id`;
- a transição para `READY_FOR_GO_LIVE` e `GO_LIVE` exige `UnidadeProdutiva`;
- o web e o wizard tratam `UnidadeProdutiva` como âncora do go-live.

### 4. Estrutura da fazenda

A hierarquia territorial e operacional já existe.

Evidências:

- [services/api/core/cadastros/propriedades/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/models.py#L15)
- [apps/web/src/components/propriedade/estrutura-hierarquia.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/propriedade/estrutura-hierarquia.tsx#L1)

O que já atende:

- `AreaRural` cobre área rural, gleba, talhão, área operacional, área ambiental e infraestrutura;
- `MatriculaImovel` cobre documentação fundiária;
- a UI já mostra a hierarquia para a fazenda.

O que é parcial:

- a estrutura é oficial, mas a experiência ainda depende de múltiplas telas;
- a implantação do piloto não se reduz a uma única etapa de cadastro territorial.

### 5. Checklists e go-live

O núcleo de bloqueio operacional já está consolidado.

Evidências:

- [services/api/wizard/router.py](/opt/lampp/htdocs/farm/services/api/wizard/router.py#L75)
- [services/api/wizard/state_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/state_engine.py#L131)
- [services/api/wizard/models.py](/opt/lampp/htdocs/farm/services/api/wizard/models.py#L118)

O que já atende:

- o Wizard calcula checklist mínimo;
- `BLOCKED` impede avanço para `READY_FOR_GO_LIVE` e `GO_LIVE`;
- o histórico é append-only;
- o go-live só avança com `UnidadeProdutiva` e prontidão real.

### 6. Campo PWA

O Campo já está em modo offline-first real.

Evidências:

- [apps/campo/src/app/(auth)/activate/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(auth)/activate/page.tsx#L63)
- [apps/campo/src/app/(campo)/sync/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/sync/page.tsx#L28)
- [apps/campo/src/lib/sync/worker.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/sync/worker.ts#L16)
- [apps/campo/src/lib/stores/session-store.ts](/opt/lampp/htdocs/farm/apps/campo/src/lib/stores/session-store.ts#L33)

O que já atende:

- ativação do dispositivo com PIN;
- sessão persistida localmente;
- validação do device token;
- sync automático quando online;
- sync inicial ao montar;
- recuperação de `IN_FLIGHT`;
- push/pull com fila local e logs.

O que é parcial:

- não existe um “wizard de implantação do Campo” separado;
- a operação depende de sessão e sincronização já preparadas antes do uso em campo.

### 7. Monitoramento

Existe observabilidade suficiente para iniciar o piloto controlado.

Evidências:

- [docs/architecture/agrosaas-observability.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-observability.md)
- [services/api/alert_engine/scheduler.py](/opt/lampp/htdocs/farm/services/api/alert_engine/scheduler.py#L1)
- [services/api/recommendations/scheduler.py](/opt/lampp/htdocs/farm/services/api/recommendations/scheduler.py#L1)

O que já atende:

- logs estruturados;
- healthchecks;
- auditoria de incidentes;
- alertas e recomendações com execução agendada por tenant/unidade;
- exportação de diagnóstico no Campo.

O que é parcial:

- não há uma única tela de cockpit do piloto que consolide tudo;
- a operação exigirá navegação entre Wizard, Campo, logs e relatórios.

## Testes e validações

Testes e guardrails já existentes sustentam os fluxos críticos:

- [services/api/tests/unit/test_pilot_onboarding_governance_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/test_pilot_onboarding_governance_guardrails.py)
- [services/api/tests/unit/test_wizard_governance_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/test_wizard_governance_guardrails.py)
- [services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py](/opt/lampp/htdocs/farm/services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py)

Esses testes confirmam:

- criação de tenant/owner/assinatura no onboarding;
- bloqueio do dashboard sem onboarding ou sem propriedade ativa;
- unicidade da implantação por tenant;
- go-live condicionado a `UnidadeProdutiva`;
- comportamento offline-first do Campo;
- idempotência de sync local.

## Fluxos completamente prontos

- criação de tenant, owner/admin, assinatura e ativação;
- guard de onboarding com bloqueio real;
- Wizard com estados, etapas, checklist, pendências e histórico;
- go-live assistido com bloqueios estruturais;
- Campo PWA com ativação, sessão local e sync offline-first;
- observabilidade e diagnósticos básicos;
- documentação operacional do piloto.

## Fluxos parcialmente prontos

- onboarding como experiência de primeira entrada;
- preparação guiada da estrutura da fazenda em uma única sequência;
- cockpit consolidado do piloto;
- experiência de operação inicial sem alternar entre várias telas.

## Fluxos inexistentes

- um wizard único que faça toda a implantação comercial + operacional + campo;
- automação total de saneamento da estrutura inicial;
- uma tela única de acompanhamento do piloto com todos os KPIs;
- autoatendimento totalmente autônomo para o primeiro cliente.

## Riscos operacionais

1. Fragmentação entre onboarding comercial, onboarding operacional, Wizard e Campo PWA.
2. Dependência de Owner/Admin para decisões em pré-go-live.
3. Estrutura da fazenda muito rica para um primeiro cliente sem saneamento prévio.
4. Falta de cockpit único pode aumentar esforço de acompanhamento nos primeiros dias.
5. Se o cliente exigir automação total antes do go-live, o escopo atual não cobre isso.

## Lacunas que impedem ou não impedem a implantação

### Impedem

- ausência de `UnidadeProdutiva` ativa;
- checklist mínimo não satisfeito;
- pendência crítica aberta;
- implantação em `BLOCKED`;
- dependência de customização estrutural antes do go-live.

### Não impedem

- ausência de cockpit único;
- fluxo visual do onboarding ainda ser genérico;
- necessidade de navegar entre Wizard, Campo e relatórios;
- falta de automação total de preparação inicial.

## Recomendação objetiva

O AgroSaaS está pronto para iniciar a implantação controlada do primeiro cliente, desde que o escopo permaneça no formato já documentado:

- usar o Wizard como fluxo oficial;
- tratar `UnidadeProdutiva` como âncora mínima;
- manter o go-live condicionado ao checklist e às pendências críticas;
- iniciar o Campo PWA somente após ativação e sincronização inicial;
- operar com acompanhamento humano nos primeiros dias.

Recomendação final:

- **GO para implantação controlada**
- **NO-GO apenas se o requisito for implantação totalmente autônoma e unificada**

## Próximas recomendações

1. Consolidar um runbook operacional único para D-5 até D+7.
2. Definir quem valida checklist, bloqueios e go-live em cada etapa.
3. Usar o Wizard como fonte oficial de prontidão.
4. Manter o Campo em operação offline-first sem alterar o fluxo de ativação.
5. Acompanhar os primeiros dias com logs, healthchecks e status do Wizard.
