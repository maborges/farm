# AGROSAAS MASTER CONTEXT
*(A Fonte Unificada da Verdade - Leitável em < 5 minutos)*

## O QUE É O AGROSAAS
Um ERP e sistema de gestão rural multilocatário (SaaS) no modelo *Modular Monolith*. Possui painel Web na sede e aplicativo PWA Offline-First para operação nas máquinas, focado na alta produtividade, estabilidade sem internet e segmentação estrita de dados (RLS).

---

## STACK OFICIAL
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 Async, Alembic, Celery, Redis.
- **Frontend Web**: Next.js 16 (App Router / RSC), TailwindCSS 4, Shadcn/UI, Zustand (Client), TanStack Query (Server).
- **Frontend Campo**: Next.js 16 (PWA), Dexie.js (IndexedDB local), Zustand, Fila de Sincronização offline.
- **Banco de Dados**: PostgreSQL 16 via driver `asyncpg`.

---

## MÓDULOS
Implementados e isolados:
1. Core & Admin SaaS
2. Agrícola & Previsões & NDVI
3. Pecuária
4. Financeiro & Comercialização & Hedge
5. Estoque & Compras
6. Frota & Manutenção
7. Integrações (IoT: John Deere, Case; Pagamentos: Stripe, Asaas)
8. RH & CRM & Ambiental & IA Diagnóstico

---

## REGRAS CRÍTICAS
1. **Nenhum bypass de RLS**: Todo select/insert deve propagar o `tenant_id` validado pelo `TenantRLSMiddleware`.
2. **Offline-First PWA**: No `apps/campo`, proíbe-se chamadas de fetch diretas bloqueantes. Tudo deve persistir no IndexedDB e enviar em background via `/api/v1/sync`.
3. **Sem TypeScript `any`**: Tipagem mandatória, preferencialmente usando Pydantic importados ou schemas de `@farm/zod-schemas`.
4. **React Server Components**: Todo `page.tsx` nasce e morre no servidor. Client hooks estritos aos componentes filhos (UI components).
5. **Estética Zero-Tolerance**: Interfaces feias, lentas ou com Layout Shift são rejeitadas. Use Skeletons.

---

## PADRÕES DE ENGENHARIA
- **TDD (Red-Green-Refactor)**: Criar cobertura das falhas e restrições antes da regra de negócio.
- **Clean Code (Backend)**: Funções de service limitadas a 20 linhas e 3 parâmetros. Usa-se Verbos nas ações.
- **Auditoria Transparente**: Quaisquer bugs de vazamento de dados geram um `TenantViolationError` armazenado via log estruturado json no `Loguru` e salvo assincronamente.
- **Commits Atômicos**: Um commit resolve um problema isolado.

---

## DATA MODEL RESUMIDO
- Raiz do Sistema: `Tenant`.
- Autenticação por Heartbeat: `SessaoAtiva` prolonga validade sem onerar o banco ativamente via cache.
- Estruturas Multi-Domínio (Propriedades, Produtos, Pessoas) conectam o Financeiro com o Agrícola através de chaves únicas de `tenant_id`.

---

## DOMÍNIO TERRITORIAL E FUNDIÁRIO

O AgroSaaS reconhece oficialmente o domínio territorial e fundiário como uma fronteira arquitetural crítica.

- `Propriedades` é o domínio operacional, territorial e produtivo.
- `Imóveis Rurais` é o domínio jurídico, patrimonial, documental e fiscal.
- A cardinalidade oficial entre ambos é `N:N`, com entidade de vínculo canônica `PropriedadeImovel`.
- Nenhum dado territorial ou fundiário pode possuir duas fontes oficiais.

### Norma obrigatória

Antes de qualquer alteração envolvendo propriedades, imóveis rurais, rastreabilidade, ESG ou certificações, consultar:

- [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)

---

## ROUTING MAP RESUMIDO
- **Frontend Web**: Rotas canônicas em `/agricola`, `/financeiro`, `/estoque`.
- **Frontend Campo**: Views de formulário off-line alimentando o Dexie.
- **Backend API**: Centralizado no prefixo `/api/v1/`. Dividido em dezenas de `routers` que apenas validam requisições e enviam para os `services` atômicos.

---

## ROADMAP
A plataforma encontra-se majoritariamente **IMPLEMENTADA** em escopo operacional (Agrícola, Estoque, Financeiro, IoT de base). Módulos Enterprise pesado (SAP, Integração Contábil complexa) estão em *Desenvolvimento / Refatoração* para aderência ao padrão AsyncSession do backend.

---

## CHECKLIST PARA IA (Antes do Pull Request)
- [ ] Entendi qual ambiente/app sofrerá impacto (Web, Campo ou API).
- [ ] O banco de dados PostgreSQL não teve seu RLS ignorado no código proposto.
- [ ] Os testes preveem o pior cenário.
- [ ] A interface proposta usa Next.js Server Components.
- [ ] Eu usei Tailwind e Shadcn/UI de forma compatível, estética e coerente.

---

## LEITURA OBRIGATÓRIA (EM CASO DE DÚVIDA)
- Detalhamento Frontend: `frontend-rsc-pattern.md`
- Detalhamento PWA: `CAMPO_PWA_01_ARQUITETURA_OFFLINE.md`
- Regras Backend & RLS: `agrosaas-engineering-playbook.md`
- Inventário Total: `architecture-inventory.md`
