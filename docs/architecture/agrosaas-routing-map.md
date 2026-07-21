# AGROSAAS ROUTING MAP

Este documento lista e agrupa as rotas do Monolito Backend (FastAPI) e a estrutura base do Frontend (Next.js). A precisão está ancorada na extração feita via `services/api/main.py`.

## ROTAS BACKEND

### Core & Backoffice
**Módulo**: Global / Admin
- `/api/v1/auth`: Fluxos de Autenticação e Login.
- `/api/v1/onboarding`: Fluxo inicial de registro de tenant.
- `/api/v1/backoffice`: Administração geral do SaaS.
- `/api/v1/backoffice_tenants`: Gestão dos clientes (inquilinos).
- `/api/v1/billing` e `/api/v1/plan_changes`: Faturamento e upgrade de assinaturas.
- `/api/v1/sessions`: Gestão de Sessões Ativas.
- `/api/v1/team`: Gestão de equipe e convites.

**Permissões**: RBAC global e RLS ativado (exceto em rotas marcadas como bypass, ex: login).
**Tenant Aware**: Apenas rotas não-globais.
**Arquivo origem**: `services/api/main.py`
**Status**: Implementado.

### Agrícola & Agricultura de Precisão
**Módulo**: Agrícola / Campo
- `/api/v1/safras`, `/api/v1/cultivos`
- `/api/v1/talhoes`, `/api/v1/operacoes`
- `/api/v1/amostragem-solo/*`: (Amostras, Mapas Fertilidade, Prescrições VRA)
- `/api/v1/agricultura-precisao/*`: (NDVI, Irrigação, Meteorologia)
- `/api/v1/caderno`: Integração Caderno de Campo.
- `/api/v1/rastreabilidade`: Rastreio de lote (com versão pública sem auth).

**Tenant Aware**: Sim (RLS integral).

### Territorial & Fundiário
**Módulos**: Propriedades / Imóveis Rurais
- `/api/v1/cadastros/areas-rurais`
- `/api/v1/propriedades/{id}/visao-territorial`
- `/api/v1/imoveis`
- `/api/v1/imoveis-rurais/{id}/visao-fundiaria`
- `/api/v1/imoveis/arrendamentos`
- `/api/v1/imoveis/avaliacoes`

**Cobertura funcional**
- Propriedades: geometria, hierarquia territorial, infraestrutura, safras operacionais e áreas.
- Imóveis Rurais: titularidade, matrícula, cartório, CAR, CCIR, ITR, NIRF, contratos e avaliações.
- Visões agregadas: leitura consolidada read-only com dados operacionais, fundiários e de vínculo oficial.

**Observação**
- A relação entre os domínios deve seguir `AGRI-DOMAIN-001`.
- A cardinalidade oficial é `N:N` via entidade de vínculo oficial.

### Certificações & ESG
**Módulo**: Domínio consumidor territorial/fundiário
- `/api/v1/certificacoes-esg/evidencias`
- `/api/v1/certificacoes-esg/nao-conformidades`
- `/api/v1/certificacoes-esg/planos-acao`
- `/api/v1/certificacoes-esg/relatorios-esg`
- `/api/v1/certificacoes-esg/passaportes`

**Características**
- Escrita exclusiva de evidências, não conformidades e planos de ação do domínio de certificação.
- Consumo somente leitura da base territorial/fundiária oficial.
- Tenant-aware com isolamento via RLS e tenant atual extraído da sessão autenticada.

### Financeiro & Comercialização
**Módulo**: Financeiro
- `/api/v1/financeiro/despesas`, `/api/v1/financeiro/receitas`
- `/api/v1/financeiro/planos_conta`, `/api/v1/financeiro/conciliacao`
- `/api/v1/financeiro/notas_fiscais`, `/api/v1/financeiro/comercializacoes`
- `/api/v1/financeiro/hedge`

**Tenant Aware**: Sim (RLS integral).

### Operacional (Frota, Estoque, Compras)
**Módulo**: Operacional
- `/api/v1/frota`, `/api/v1/oficina`
- `/api/v1/abastecimento`, `/api/v1/apontamento`, `/api/v1/checklist`
- `/api/v1/estoque`, `/api/v1/estoque_implantacao`
- `/api/v1/compras`

**Tenant Aware**: Sim.

### Pecuária
**Módulo**: Pecuária
- `/api/v1/lotes`
- `/api/v1/manejos`

**Tenant Aware**: Sim.

### Integrações IoT & IA
**Módulo**: Máquinas / Diagnóstico
- `/api/v1/iot/john_deere`, `/api/v1/iot/case_ih`
- `/api/v1/ia-diagnostico/pragas_doencas`, `/api/v1/ia-diagnostico/tratamentos`

### Integrações ERP
**Módulo**: Integrações / ERP canônico com adapter Sankhya
- `/api/v1/integracoes/erp/status`, `/health`, `/jobs`, `/timeline`: leitura operacional canônica.
- `GET /api/v1/integracoes/erp/policies`: políticas dos recursos do ERP ativo no tenant.
- `PATCH /api/v1/integracoes/erp/policies/{feature_code}`: modo, frequência e controles da política existente.
- `POST /api/v1/integracoes/erp/pessoas/lookup`: consulta uma pessoa pelo ID externo, sem persistência.
- `POST /api/v1/integracoes/erp/pessoas/import`: cria ou atualiza a `Pessoa` canônica e reconcilia o vínculo externo.
- Cada política publica a URL resolvida, o serviço e a entidade externa consumida; esses dados são derivados do contrato do adapter e não são editáveis pelo usuário.
- `/api/v1/integracoes/sankhya/sync/produtos`: execução manual legada preservada e governada pela política canônica.
- `/api/v1/integracoes/sankhya/sync/pessoas`: compatibilidade HTTP preservada, mas o modo manual orienta o usuário ao fluxo por ID e não autoriza carga em massa.

**Execução automática**
- O loop ERP reutiliza `core/background_jobs.py` e o registry de providers.
- Cada tenant recebe sessão e contexto RLS próprios antes da leitura ou execução.
- Somente políticas `AGENDADO`, ativas e declaradas pelo adapter em `runtime_sync_modes` são executadas.
- Para Pessoas, `LINKED_ONLY` atualiza somente vínculos existentes e `ALL_EXTERNAL` importa todo o cadastro do ERP; o segundo exige opção automática explícita.

**Persistência**
- Configuração e políticas: `tenant_integracoes`, `integration_features` e `integration_sync_policies`.
- Execuções: `integration_jobs`, mantendo correlação com os logs Sankhya legados.
- Staging Sankhya: chaves externas são únicas por `(tenant_id, identificador_externo)`, nunca globalmente.

---

## ROTAS FRONTEND

### `apps/web` (Painel Administrativo)
- Baseado no App Router (`src/app/`).
- **Páginas Base**: `/login`, `/dashboard`, `/agricola`, `/financeiro`. (Estrutura oficial baseada nas APIs).
- **Visões financeiras Hedge**:
  - `/dashboard/financeiro/hedge/contratos`
  - `/dashboard/financeiro/hedge/registros`
  - `/dashboard/financeiro/hedge/mtm`
  - `/dashboard/financeiro/hedge/exposicao`
- **Visões consolidadas**:
  - `/cadastros/propriedades/[id]/visao-territorial`
  - `/cadastros/imoveis/[id]/visao-fundiaria`
  - `/dashboard/certificacoes-esg`
- **Configuração ERP**:
  - `/dashboard/settings/integracoes`
  - O editor de regras altera `IntegrationSyncPolicy`; não cria configuração ou tabela paralela.
- **Cadastro de Pessoas**:
  - `/cadastros/pessoas` e `/cadastros/pessoas/{id}` consultam/importam pelo ID externo quando o recurso Pessoas do ERP está ativo.
  - Sem ERP configurado, o cadastro local continua disponível.
- **Origem dos dados**: Fetch server-side no `page.tsx` -> TanStack Query -> Client Components via `shadcn/ui`.
- **Status**: RSC implementado como default.

### `apps/campo` (PWA Offline First)
- Baseado no App Router (`src/app/`).
- **Rotas de Sincronização**: `/api/v1/sync` no frontend interceptada por Service Workers / Dexie.js para fila de envio.
- **Client Components**: Elevado uso de Client Components para interação formulário-Dexie (IndexedDB) sem internet.

---

## ROTAS ÓRFÃS

- **Enterprise**: Algumas rotas enterprise listadas no `main.py` estão inativas/comentadas aguardando migração para `AsyncSession` (ex: `sap_router`, `powerbi_router`, `contabilidade`).
- **Verificação Pendente pela IA**: Quando trabalhar nesses domínios, confirmar status de ativação no `main.py`.

---

## MATRIZ DE COBERTURA

| Módulo | Frontend | Backend | Permissões (RBAC) | Testes (TDD) | Status |
|---|---|---|---|---|---|
| Autenticação / Sessão | ✅ Sim | ✅ Sim | ✅ Global | ✅ Necessário | Produção |
| Territorial / Fundiário | ✅ Sim | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Financeiro | ✅ Parcial | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Agrícola / Safra | ✅ Sim | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Frota / Abastecimento | ✅ Sim | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Campo (PWA) | ✅ Sim (Dexie) | ✅ Sync API | ✅ Híbrido | ✅ E2E Req | Produção |
| Enterprise (SAP) | ❌ Inativo | ❌ Refatorando | NÃO IDENTIFICADO | Pendente | Em Hold |
