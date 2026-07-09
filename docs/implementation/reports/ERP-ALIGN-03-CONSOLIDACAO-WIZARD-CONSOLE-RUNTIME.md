# ERP-ALIGN-03 - Consolidacao entre Wizard, Console ERP e Runtime Oficial

Data: 2026-07-09
Escopo: alinhamento funcional, navegacional e de nomenclatura sem criar novo dominio, rota, tabela, endpoint ou runtime

## 1. Objetivo

Consolidar a aderencia entre:

- Wizard de implantacao;
- Console ERP do tenant;
- Backoffice ERP;
- runtime oficial de integracoes;
- guardrails definidos em `ERP-GOV-02`.

## 2. Arquivos auditados

Documentacao:

- `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
- `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
- `docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md`
- `docs/implementation/reports/ERP-GOV-02-AUDITORIA-GOVERNANCA-ERP.md`

Frontend:

- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/lib/permissions.ts`
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`

Backend:

- `services/api/wizard/router.py`
- `services/api/wizard/checklist_engine.py`

## 3. Arquivos alterados

- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`
- `services/api/wizard/router.py`

## 4. Duplicidades evitadas

Nenhuma estrutura paralela foi criada.

Foi mantido e reutilizado:

- rota tenant oficial `/dashboard/settings/integracoes/erp`;
- rota backoffice oficial `/dashboard/backoffice/integracoes/erp`;
- runtime oficial com `ExternalRecordAssociation`, `IntegrationJob`, `IntegrationHealth`, `IntegrationSyncPolicy` e `IntegrationVersion`;
- matriz atual de permissoes `integrations:*` e `backoffice:integrations:*`;
- endpoints existentes do provider Sankhya.

Nao foi criado:

- nova rota ERP;
- novo console;
- nova tabela;
- nova migration;
- novo endpoint;
- novo runtime;
- novo de-para;
- novo processo paralelo.

## 5. Divergencias corrigidas

### 5.1 Naming Sankhya-first na UX tenant

Corrigido:

- titulo da pagina tenant passou de `ERP Sankhya` para `Integracoes ERP`;
- breadcrumbs passaram a refletir o console ERP generico;
- console do tenant passou a se apresentar como console ERP com `Provider atual: Sankhya`.

### 5.2 Link legado do Wizard

Corrigido:

- o wizard deixou de apontar para `/configuracoes/integracoes`;
- a navegacao e a acao recomendada agora apontam para `/dashboard/settings/integracoes/erp`;
- o backend do wizard passou a devolver o alvo oficial `Abrir console ERP`.

### 5.3 Papel do backoffice

Corrigido:

- o texto do backoffice passou a reforcar explicitamente que ele observa, diagnostica e apoia;
- a tela deixa claro que o backoffice nao substitui o console principal do tenant.

### 5.4 Navegacao lateral

Corrigido:

- a dica do menu lateral do tenant deixou de ser `Configuracao do Sankhya` e passou a ser `Configuracao ERP do tenant`.

## 6. Divergencias remanescentes

Ainda permanecem, de forma deliberada nesta execucao:

- nomes tecnicos internos como `SankhyaConsole`, `SankhyaTimeline` e tipos TS `Sankhya*`;
- endpoints provider-specific sob `/integracoes/sankhya/...`;
- pagina de backoffice consumindo diretamente os contratos do provider Sankhya.

Esses pontos nao geram duplicidade funcional, mas mantem naming tecnico provider-first no codigo. A mudanca deles exige uma execucao especifica de consolidacao tecnica para evitar churn desnecessario.

## 7. Validacao executada

Executado:

- `git diff --check`
- `npm run typecheck` em `apps/web`

## 8. Recomendacao objetiva para a proxima etapa

Proxima execucao recomendada:

1. consolidar naming tecnico interno do frontend para componentes ERP genericos, mantendo Sankhya apenas como provider;
2. revisar o criterio do checklist `CHECK_INTEGRACAO_ERP` para refletir provider, capability e policy reais do runtime;
3. auditar o backend do wizard para remover dependencias remanescentes de fluxo por `UnidadeProdutiva` quando a trilha for exclusivamente ERP.
