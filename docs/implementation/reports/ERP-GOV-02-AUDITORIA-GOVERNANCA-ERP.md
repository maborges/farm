# ERP-GOV-02 - Auditoria de Governanca das Integracoes ERP

Data: 2026-07-09
Escopo: auditoria documental e funcional sem alteracao de codigo

## 1. Objetivo

Auditar o repositorio antes da consolidacao de `ERP-GOV-02`, identificando guardrails, contratos e ativos ja existentes para evitar duplicidade conceitual, documental e tecnica.

## 2. Documentos auditados

- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/architecture/INTEGRATIONS-LIFECYCLE-01.md`
- `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
- `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
- `docs/implementation/reports/SANKHYA-PILOT-03-AUDITORIA-COBERTURA-INTEGRACAO.md`
- `docs/implementation/reports/SANKHYA-GOV-01-AUDITORIA-GOVERNANCA-INTEGRACAO-SANKHYA.md`
- `docs/implementation/reports/ERP-CONSOLE-01-AUDITORIA-FUNCIONAL-CONSOLE-ERP.md`

## 3. Ativos tecnicos auditados

- `services/api/integracoes/models.py`
- `services/api/integracoes/schemas.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `apps/web/src/lib/permissions.ts`
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`
- `services/api/wizard/router.py`
- `services/api/wizard/checklist_engine.py`

## 4. Guardrails ja existentes e reutilizados

### 4.1 Dominio e runtime

Ja existem e devem ser reutilizados:

- escopos oficiais do dominio Integracoes;
- lifecycle oficial da integracao;
- runtime canonico de provider/configuracao/feature/policy/health;
- `ExternalRecordAssociation` como mecanismo de de-para oficial;
- `IntegrationJob` como trilha operacional oficial;
- `IntegrationHealth` como saude runtime oficial;
- `IntegrationSyncPolicy` como politica oficial de sincronizacao.

### 4.2 Governanca de escopo

Ja existem e devem ser consolidados:

- arquitetura generica aceita `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`;
- arquitetura ERP restringe o dominio ERP para `TENANT` e `ESTABELECIMENTO`;
- relatorios e arquiteturas anteriores ja vedam ERP por `UnidadeProdutiva`.

### 4.3 Governanca de permissoes

Ja existem e devem ser reutilizados:

- permissoes tenant `integrations:view`, `integrations:configure`, `integrations:test`, `integrations:sync`, `integrations:logs:view`;
- permissoes backoffice `backoffice:integrations:observe` e `backoffice:integrations:support`;
- protecao por `require_tenant_permission(...)` nas rotas Sankhya.

### 4.4 Governanca de configuracao e observabilidade

Ja existem e devem ser estendidos:

- console do tenant para configuracao ERP;
- backoffice para observabilidade e suporte;
- endpoints de teste de conexao, health, status, jobs, logs, timeline, diagnostico e reconciliacao;
- `IntegrationVersion.snapshot_mascarado` para historico mascarado.

## 5. Duplicidades evitadas por ERP-GOV-02

O documento criado evita criar:

- segunda arquitetura de ownership, porque reutiliza `ERP-DOMAIN-01`;
- segundo console de configuracao, porque reutiliza `ERP-CONSOLE-01`;
- segundo runtime de integracao, porque reutiliza `INTEGRATIONS-ARCH-02` e `services/api/integracoes/models.py`;
- segunda regra de lifecycle, porque reutiliza `INTEGRATIONS-LIFECYCLE-01`;
- segunda estrategia de mapeamento, porque oficializa `ExternalRecordAssociation` como fonte unica;
- segunda matriz de permissao, porque reutiliza RBAC ja existente.

## 6. Divergencias arquiteturais identificadas

### 6.1 Divergencias de UX e naming

- a rota tenant ja e generica de ERP, mas a pagina ainda se apresenta como `ERP Sankhya`;
- o componente principal ainda e `sankhya-console`, o que indica naming provider-first em uma arquitetura ja consolidada como ERP generico;
- o menu lateral ainda exibe dica `Configuracao do Sankhya` para a entrada generica de ERP.

### 6.2 Divergencias de fluxo

- o Wizard ainda aponta para `/configuracoes/integracoes`, rota legada, em vez do console oficial `/dashboard/settings/integracoes/erp`;
- a verificacao de ERP no Wizard ainda nao representa uma governanca completa baseada em provider/capability/policy.

### 6.3 Divergencias de consolidacao

- o runtime generico ja existe, mas a experiencia funcional ainda esta fortemente Sankhya-first;
- a governanca de lifecycle ja existe no dominio Integracoes, mas ainda nao estava consolidada como regra obrigatoria especifica para ERP.

## 7. Classificacao da base atual

- Fundacao de governanca: `CONFORME COM RESSALVAS`
- Runtime de integracoes: `CONFORME`
- Escopo ERP: `CONFORME COM RESSALVAS`
- Console ERP: `CONFORME COM RESSALVAS`
- Observabilidade: `CONFORME`
- Mapeamentos externos: `CONFORME`

## 8. Conclusoes da auditoria

Conclusoes objetivas:

- o repositorio ja possui runtime e contratos suficientes para governanca ERP sem criar novos conceitos centrais;
- a necessidade principal era consolidar regras obrigatorias, nao criar nova arquitetura;
- os maiores riscos atuais sao de consolidacao de fluxo e naming, nao de ausencia total de fundacao tecnica;
- `ERP-GOV-02` deve atuar como camada normativa sobre ativos ja existentes.

## 9. Recomendacao objetiva para a proxima etapa

Proxima execucao recomendada:

- auditoria e consolidacao de aderencia entre Wizard, Console ERP e runtime oficial, com foco em rotas legadas, naming Sankhya-first e criterios de checklist do tenant.
