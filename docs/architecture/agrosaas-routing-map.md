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

---

## ROTAS FRONTEND

### `apps/web` (Painel Administrativo)
- Baseado no App Router (`src/app/`).
- **Páginas Base**: `/login`, `/dashboard`, `/agricola`, `/financeiro`. (Estrutura canônica baseada nas APIs).
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
| Financeiro | ✅ Parcial | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Agrícola / Safra | ✅ Sim | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Frota / Abastecimento | ✅ Sim | ✅ Sim | ✅ Sim (RLS) | ✅ Obrigatório | Operacional |
| Campo (PWA) | ✅ Sim (Dexie) | ✅ Sync API | ✅ Híbrido | ✅ E2E Req | Produção |
| Enterprise (SAP) | ❌ Inativo | ❌ Refatorando | NÃO IDENTIFICADO | Pendente | Em Hold |
