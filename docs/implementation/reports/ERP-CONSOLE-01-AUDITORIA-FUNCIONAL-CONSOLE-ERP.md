# ERP-CONSOLE-01 - Auditoria Funcional do Console ERP

Data: 2026-07-09
Escopo: auditoria funcional e consolidacao arquitetural
Status: concluido

## 1. Objetivo

Auditar o que ja existe no repositório sobre integracoes ERP antes de definir a arquitetura funcional do console, evitando duplicidade de processo, tela, rota, model, tabela, servico ou conceito.

## 2. Arquivos auditados

### Arquitetura e relatorios

- `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
- `docs/implementation/reports/ERP-DOMAIN-01-DECISOES-PARA-PILOTO-ERP.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/implementation/reports/INTEGRATIONS-ARCH-01-ARQUITETURA-CANONICA-INTEGRACOES.md`
- `docs/implementation/reports/SANKHYA-GOV-01-AUDITORIA-GOVERNANCA-INTEGRACAO-SANKHYA.md`

### Frontend

- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/lib/permissions.ts`
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx`

### Backend

- `services/api/integracoes/models.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/wizard/router.py`
- `services/api/wizard/checklist_engine.py`

## 3. Achados principais

### 3.1 Ja existe console do tenant

Achado:

- a rota consolidada do tenant ja existe em `/dashboard/settings/integracoes/erp`;
- ela ja carrega `SankhyaConsole`.

Decisao:

- **reutilizar**

### 3.2 Ja existe tela de observabilidade em backoffice

Achado:

- existe uma tela separada em `/dashboard/backoffice/integracoes/erp`;
- ela ja consome `status`, `health`, `jobs`, `logs`, `timeline` e `diagnostico`;
- o proprio texto da tela indica que o backoffice observa e o tenant configura.

Decisao:

- **reutilizar**
- **nao transformar em console principal**

### 3.3 Ja existe runtime canonico de integracoes

Achado:

- o dominio `integracoes` ja materializa `MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationCredential`, `IntegrationVersion`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth` e `ExternalRecordAssociation`.

Decisao:

- **reutilizar**
- **estender apenas semanticamente via documentacao**

### 3.4 Ja existe configuracao de credencial, health, logs, jobs e reconciliacao

Achado:

- os endpoints Sankhya ja cobrem configuracao, teste de conexao, status, health, jobs, logs, diagnostico, timeline e reconciliacao manual de associacoes.

Decisao:

- **reutilizar**
- **nao criar endpoints paralelos**

### 3.5 O Wizard ja referencia ERP, mas com link legado

Achado:

- o Wizard ja possui estrategia `ERP`;
- ja coleta `erp_nome` e escopo de carga inicial;
- ja exibe CTA para integracoes;
- o link atual aponta para `/configuracoes/integracoes`, nao para a rota consolidada do dashboard.

Decisao:

- **consolidar**
- **depreciar link legado**
- **nao mover configuracao ERP para dentro do Wizard**

### 3.6 Nao existe configuracao ERP por Unidade Produtiva no modulo de integracoes

Achado:

- o modulo de integracoes usa escopo tenant;
- `ExternalRecordAssociation` ja suporta `scope_type` e `scope_id`;
- o Sankhya atual nao modela `UnidadeProdutiva` como escopo de credencial.

Decisao:

- **nao mexer**
- **reforcar deprecacao de qualquer ideia futura de ERP por Unidade Produtiva**

## 4. Riscos de duplicidade encontrados

1. Criar um "novo console ERP" paralelo ao `sankhya-console.tsx`.
2. Criar nova tabela de mapeamento externo paralela a `ExternalRecordAssociation`.
3. Criar nova camada de observabilidade paralela a `IntegrationJob`, `IntegrationHealth`, logs e timeline existentes.
4. Criar nova rota de tenant para ERP sem necessidade, fragmentando navegacao.
5. Manter links legados do Wizard para `/configuracoes/integracoes`, perpetuando divergencia de UX.
6. Deixar o nome "Configuracao do Sankhya" no menu como se fosse arquitetura final, quando o dominio ja e ERP generico.

## 5. Decisoes funcionais derivadas da auditoria

- o console oficial deve reutilizar a rota do tenant existente;
- o backoffice deve permanecer como observabilidade e suporte;
- `ExternalRecordAssociation` e a unica base oficial de mapeamentos;
- `IntegrationJob`, `IntegrationHealth` e `IntegrationSyncPolicy` devem ser a base oficial de observabilidade operacional;
- o Wizard nao deve configurar ERP;
- o onboarding nao deve configurar ERP;
- o console deve ser renomeado conceitualmente para ERP generico, mantendo Sankhya como primeiro provider ativo.

## 6. O que deve ser reutilizado, estendido, consolidado ou depreciado

### Reutilizar

- tenant console existente
- backoffice ERP existente
- runtime canonico de integracoes
- reconciliacao manual ja existente
- timeline ja existente

### Estender

- schema de provider para capability matrix
- semantica do console para multiplos providers
- versionamento funcional de URLs e endpoints

### Consolidar

- navegacao tenant
- CTA do Wizard
- nomenclatura do console

### Depreciar

- links `/configuracoes/integracoes`
- semantica de "console Sankhya" como se fosse regra geral

### Nao mexer

- adapters
- models
- rotas
- Wizard
- onboarding

## 7. Resultado da auditoria

Conclusao:

- ja existe base suficiente para o Console Administrativo de Integracoes ERP;
- o trabalho correto nesta fase e consolidar a arquitetura funcional e a nomenclatura;
- criar novos conceitos, tabelas, rotas ou telas agora seria duplicidade arquitetural.
