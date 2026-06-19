# AGROSAAS ENGINEERING PLAYBOOK

Este é o Guia Oficial de Engenharia do AgroSaaS. Deve ser utilizado por desenvolvedores humanos e agentes de Inteligência Artificial (Codex, Cursor, Claude, OpenAI) para garantir o alinhamento arquitetural irrestrito em qualquer nova funcionalidade.

---

## SEÇÃO 1 — VISÃO GERAL DO SISTEMA

### Objetivo do AgroSaaS
Fornecer um sistema de gestão rural (SaaS) modular e resiliente que atende tanto o backoffice da fazenda (conectado) quanto o operador em campo (desconectado).

### Arquitetura Geral
O AgroSaaS adota a arquitetura de **Monolito Modular** no backend acoplada a dois frontends desacoplados servidos via Monorepo.

#### Fluxograma Textual:

```text
[ Usuário Backoffice ]       [ Operador no Campo ]
          |                             |
    (Navegador Web)              (App PWA Mobile)
          |                             |
  +----------------+            +----------------+
  |    apps/web    |            |   apps/campo   |
  | (Next.js RSC)  |            | (Offline First)|
  +-------+--------+            +-------+--------+
          |                             | (Sincronização via API /sync)
          +-------------+---------------+
                        |
                        v
              +-------------------+
              |   services/api    |
              | (FastAPI Modular) |
              +---------+---------+
                        |
          +-------------+-------------+
          |                           |
          v                           v
  +---------------+           +---------------+
  |  PostgreSQL   |           |     Redis     |
  | (RLS Ativo)   |           | (Cache/Queue) |
  +---------------+           +-------+-------+
                                      |
                                      v
                              +---------------+
                              |    Celery     |
                              | (Background)  |
                              +---------------+
```

---

## SEÇÃO 2 — ORGANIZAÇÃO DO MONOREPO

O projeto utiliza **pnpm workspaces** e possui uma estrutura estrita.

### `apps/`
**Responsabilidade:** Aplicações de interface voltadas ao usuário final.
- `apps/web`: Sistema administrativo (Next.js 16).
- `apps/campo`: Aplicação PWA para operadores (Next.js 16 + next-pwa).
- **Proibido:** Lógica de negócios pesada, manipulação direta de banco de dados, pacotes não relacionados a UI.

### `services/`
**Responsabilidade:** Serviços de backend e APIs.
- `services/api`: Monolito FastAPI contendo todos os módulos de negócios isolados.
- **Proibido:** Geração de HTML (views clássicas), estados globais em memória.

### `packages/`
**Responsabilidade:** Bibliotecas TS compartilhadas entre os apps.
- `packages/types`: Tipagens base do domínio.
- `packages/zod-schemas`: Schemas de validação compartilhados entre client e backend.
- `packages/utils`: Funções utilitárias sem dependências complexas.
- **Proibido:** Dependências exclusivas de frontend (React/DOM) no `types` ou `zod-schemas`.

### `docs/`
**Responsabilidade:** Documentação arquitetural, manuais de fluxo e playbooks.
- **Proibido:** Código executável ou binários não relacionados a tutoriais.

---

## SEÇÃO 3 — PADRÕES DE BACKEND

### Estruturas FastAPI
Cada módulo de negócios (ex: `agricola`, `financeiro`) segue uma taxonomia delimitada:
- **Routers (`routers.py`)**: Valida payload, aciona services, retorna Response. NENHUMA lógica de negócio deve residir aqui.
- **Services (`services/`)**: Regras de negócio puras. Funções com no máximo 20 linhas e 3 argumentos. Nomes revelam intenção.
- **Repositories**: Isolamento opcional de query se houver reaproveitamento massivo (ou acesso via SQLAlchemy direto no service).
- **Schemas (`schemas.py`)**: Pydantic models para Request/Response estritos.
- **Models (`models/`)**: Entidades SQLAlchemy exclusivas do banco.

### Como uma nova funcionalidade backend deve ser criada?

1. **Testes Red**: Escreva os testes no diretório `tests/` do módulo validando os edge cases antes de criar o código.
2. **Definição de Schema**: Crie os contratos `Pydantic` de entrada/saída no `schemas.py`.
3. **Criação da Model (se aplicável)**: Crie o modelo SQLAlchemy garantindo que o `tenant_id` seja mapeado.
4. **Implementação Service**: Crie a regra de negócios em um service isolado. Inclua docstrings descrevendo *Args*, *Return* e *Raises*.
5. **Integração no Router**: Injete o `AsyncSession` no endpoint, acesse a sessão com RLS ativo e chame o service.
6. **Passagem no Teste**: Execute `pytest` até alcançar Green, aplique refactor de clean code e conclua.

---

## SEÇÃO 4 — PADRÕES DE BANCO DE DADOS

- **Banco Primário**: PostgreSQL.
- **ORM**: SQLAlchemy Async (`asyncpg`).
- **Migrações**: Alembic.

### Padrões Identificados
- **Schema**: Esquemas lógicos (ou `public` compartilhado) organizados por módulo.
- **Estratégia Multi-Tenant**: Inquilinos operam no mesmo banco, totalmente isolados por Row Level Security (RLS) associado ao `tenant_id`.

### ✔ Permitido
- Recuperar a sessão no FastAPI sabendo que o Middleware injetou o RLS de forma automática.
- Consultas utilizando SQLAlchemy Async Session.
- Constraints e chaves compostas incluindo `tenant_id`.

### ✘ Proibido
- Criar rotas ou serviços que contornem (bypass) o RLS (exceto módulos estritos de sistema e root admin).
- Compartilhar session lógicas de tenants diferentes no mesmo scope.
- Escrever SQL nativo suscetível a SQL Injection sem parametrização.

---

## SEÇÃO 5 — PADRÕES DE FRONTEND WEB

- **Framework**: Next.js App Router.
- **Padrão de Renderização**: Server Components (RSC) por padrão.
- **Data Fetching (Server)**: Fetch no Node, injetado via initialData.
- **State Mgmt**: TanStack Query (Server State), Zustand (Client UI State).
- **Formulários**: React Hook Form + Zod (importado de `packages/zod-schemas`).

### Como uma nova página deve ser criada?
1. Crie `page.tsx` como Server Component (não use `"use client"`).
2. O componente base faz fetch server-side usando métodos da API ou fetch direto.
3. Repasse os dados para Client Components via props.

### Como uma nova tabela deve ser criada?
1. Use AG Grid para volume alto (>10k linhas) ou data-table do `shadcn/ui` para tabelas simples.
2. Exija paginação e campo de pesquisa. Botões de ação devem ficar na última coluna (sem header visível), cor pertinente e sem bordas.

### Como um novo formulário deve ser criado?
1. Declare o schema Zod (ou reimporte de `packages/`).
2. Utilize `useForm` com `@hookform/resolvers/zod`.
3. Implemente no padrão `shadcn/ui` os campos (`<Form>`, `<FormField>`, `<Input size="sm">`).
4. Utilize Server Actions ou TanStack Mutations e libere feedback via Toast (`sonner`).

---

## SEÇÃO 6 — PADRÕES DO PWA CAMPO

- **Core**: Offline First. Nenhuma operação depende de conexão em tempo real.
- **Cache Local**: IndexedDB manipulado pelo `Dexie.js`.
- **Sync Engine**: Lógica dedicada de envio de payloads armazenados no IndexedDB quando a rede volta.
- **Workers**: Service Workers via `next-pwa` para caching estático.

### Como implementar funcionalidade sem quebrar o modo offline?
1. **Nunca faça `fetch()` direto para a API dentro das ações do usuário.**
2. A ação salva no IndexedDB via Dexie e atualiza a view via Zustand.
3. Registre o payload do evento em uma tabela interna de "Outbox" ou "SyncQueue".
4. O Worker de sincronização consumirá o payload enviando para a rota `/api/v1/.../sync` quando a internet estiver estabelecida.

---

## SEÇÃO 7 — PADRÕES DE TESTES

A regra de ouro é **TDD (Red/Green/Refactor)**.

### Checklist Obrigatório de Testes
- [ ] Testes de falhas provocadas (edge cases como string vazia, datas retroativas).
- [ ] Tratamento de arrays vazios e nulos explícitos.
- [ ] Limites numéricos (pesagem excessiva/negativa).
- [ ] Isolamento: Serviços que chamam APIs externas ou outros módulos usam `mocks` ou containers injetados.
- [ ] Simulação de falhas transversais (ex: falha do `api-financeiro` se chamado por `api-pecuaria`).
- [ ] Checagem do isolamento do Tenant (se Tenant B consultar dado de Tenant A, deve retornar Not Found ou 403).

---

## SEÇÃO 8 — PADRÕES DE SEGURANÇA

- **Autenticação**: Baseada em tokens JWT (`python-jose`).
- **Autorização**: RBAC com funções injetadas e aplicadas às rotas.
- **Sessões**: Heartbeat gerenciado via `SessionHeartbeatMiddleware`.
- **Auditoria**: Monitoramento global salvando ações no banco assincronamente em casos de anomalias (`SECURITY_INCIDENT`).

### ERROS CRÍTICOS QUE A IA NUNCA DEVE COMETER
1. Bypass global do `tenant_id` em listagens padrão no backend.
2. Injetar `use client` no root do App Router (`page.tsx`) matando os benefícios de RSC.
3. Usar `.env` diretamente no frontend sem prefixo seguro (`NEXT_PUBLIC_`) ou subir secrets reais no código-fonte.
4. Modificar middlewares de segurança (RLS, CORS, RBAC) ou baixar proteções de API.

---

## SEÇÃO 9 — PADRÕES DE UI/UX

A estética do AgroSaaS deve ser "Premium e Inovadora" (Tons verde esmeralda, temas Terra, dark mode elegante, rounded-sm nas bordas). 

### Checklist de UX Obrigatório
- [ ] **Zero Layout Shift**: Espaços definidos fixamente para imagens ou cards antes do load.
- [ ] **Skeletons**: Uso do `loading.tsx` ou Suspense skeleton para toda e qualquer carga de tela.
- [ ] **Estado Vazio (Empty State)**: Toda tabela/lista possui design específico (imagem amigável/ícone) de "Nada Encontrado".
- [ ] **Botões/Inputs**: Tamanho `sm`, tipografia harmônica, contornos `rounded-sm`. Botões de ação destrutiva sinalizados, preferência por estilos *outline*.

---

## SEÇÃO 10 — FLUXO DE IMPLEMENTAÇÃO

**Passo a passo oficial:**
1. **Analisar domínio**: Ler `domain-map` e regras.
2. **Criar testes**: TDD mandatório. Edge cases previstos na falha.
3. **Criar backend**: Services (max 20 linhas), Schemas, integração RLS na rota.
4. **Criar frontend**: PWA (via Dexie SyncQueue) ou Web (via TanStack Mutation + RSC).
5. **Criar integração**: Bind dos frontends com a API via endpoints autorizados.
6. **Validar RLS**: Certificar de que o Tenant 2 não vê o Tenant 1.
7. **Validar offline** (Se `campo/`): Desligar network devtools e testar persistência local.
8. **Atualizar documentação**: O `README.md` (Features e Fluxos).
9. **Executar checklist**: Código limpo, testes em verde, dependências fresquinhas.
10. **Aprovar**: Finalizar o escopo da ferramenta em um commit atômico (`feat:`, `fix:`).

---

## SEÇÃO 11 — CHECKLIST DE CODE REVIEW

Antes de enviar ou dar a tarefa por completa, a IA / Desenvolvedor deve verificar:

- [ ] Sem `any` no Typescript (Tipagem forte).
- [ ] Sem bypasses de compilador (`@ts-ignore`, `as unknown`).
- [ ] Regras de RLS integralmente respeitadas nos queries/SQLAlchemy.
- [ ] Permissões de Tenant asseguradas em manipulação de entidades.
- [ ] Testes automatizados criados e passando.
- [ ] Arquitetura estrita seguida: Sem repetição (`DRY`) utilizando módulos da stdlib onde possível.
- [ ] Segue fielmente o UI Design System (Shadcn/UI, Tailwind 4, botões sm, border rounded-sm).
- [ ] Segue o `agrosaas-domain-map` e taxonomia correta de diretórios.
- [ ] Variáveis soltas ou códigos mortos/comentados apagados. Commits Atômicos.

---

# CONTEXTO MÍNIMO PARA IA

Este bloco contém a essência do que uma IA deve saber ao acordar neste projeto:

1. **Stack**: Monorepo. Backend em Python 3.12 (FastAPI, AsyncPG, Celery, Redis). Frontend Administrativo e Frontend Campo/PWA em Next.js 16 (App Router, Tailwind 4, Shadcn/UI, Zustand, TanStack Query).
2. **Engenharia**: TDD obrigatório (Test-first approach). Componentes de servidor como default no React (RSC). `Strict Mode` em Typescript abolindo `any` e supressões de erro.
3. **Padrões**: 
   - No Backend, tudo funciona sobre Row Level Security (RLS) PostgreSQL baseando-se no `tenant_id` do JWT.
   - O PWA do campo opera puramente como **Offline First**, persistindo requisições via IndexedDB (`Dexie.js`) e enviando à API num Worker de Sync quando há rede.
   - Design System Premium: Zero Layout Shift tolerado, uso mandatório de Skeletons, componentes estéticos com `rounded-sm` e `size sm` nos formulários.
4. **Isolamento**: O sistema deve prever a falha em APIs dependentes e manter integridade das rotinas. Bancos de dados são severamente separados por ambientes (dev, prod). Nunca vaze envs ou compartilhe dados cross-tenant.
5. **Arquitetura de Modificações**:
   - Para novas UIs: Use Next.js RSC `page.tsx` para fetch, enviando a client components restritos.
   - Para formulários: RHF + Zod referenciando `packages/zod-schemas`.
   - Para serviços Python: Máximo 20 linhas, docstrings em toda função complexa, 3 argumentos limite por função.

> Ao ler estas regras, a Inteligência Artificial aceita irrevogavelmente operar sob tais restrições, impedindo regressão de código, débitos técnicos arquiteturais e quebras de padronagem.
