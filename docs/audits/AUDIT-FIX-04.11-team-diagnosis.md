# Diagnóstico Local: `dashboard/settings/team/page.tsx`

Antes da migração RSC controlada (AUDIT-FIX-04.11), realizamos o mapeamento do estado atual.

## 1. Métricas e Dimensões
- **Arquivo Alvo:** `apps/web/src/app/(dashboard)/dashboard/settings/team/page.tsx`
- **Tamanho Total:** 853 linhas de código
- **Complexidade:** Alta (Classe C2)

## 2. Inventário de Funcionalidades (Client-Side)
### Hooks e Bibliotecas Identificados
- **React:** `useState`
- **TanStack Query:** `useQuery`, `useMutation`, `useQueryClient`
- **React Hook Form & Zod:** Gerenciamento de formulários (`useForm`, `zodResolver`)
- **UI Components:** `DataTable`, `Dialog`, `AlertDialog`, `Tooltip`, `Select`, `Avatar`
- **Data/Hora:** `date-fns` para formatação (`formatDistanceToNow`, etc.)
- **Hooks Customizados:** `useTenantLoginTentativas`, `useDesbloquearTenantUsuario`

### Data Fetching (Queries)
A página dispara **5 requisições iniciais paralelas** que provocam Waterfall client-side:
1. `GET /team/stats` (TeamStats)
2. `GET /team/users` (TeamMember[])
3. `GET /team/invites` (TeamInvite[])
4. `GET /team/roles` (TenantRoleProfile[])
5. `GET /unidades-produtivas` (Fazenda[])

### Mutações Mapeadas (Mutations)
1. `Convidar Usuário`: Form/Action (`Send`)
2. `Editar Papel/Role do Membro`: Modal Form
3. `Remover Membro` / `Cancelar Convite`: AlertDialogs
4. `Desbloquear Usuário`: Ação direta via custom hook

## 3. Estados Locais e Lógica Crítica
- `inviteOpen`, `editOpen`: Controle de Modais.
- `selectedUser`, `selectedInvite`: Armazena o membro alvo de uma ação na UI.
- Filtros e Tabelas: Configurações de colunas via `DataTable` e custom renders.

## 4. O que Permanece no Client (`TeamClient.tsx`)
- Toda a lógica de Data Table.
- Gerenciamento reativo de modais e forms (React Hook Form).
- React Query com `initialData` garantindo *stale-while-revalidate*.
- Todos os Toasts e Invalidations (`queryClient.invalidateQueries`).
- Integração RBAC (`PermissionGuard`).
- Os hooks customizados (como verificação de login blocks) que dependem de estado de UI contínuo.

## 5. O que Será Movido para o Server (`page.tsx` como RSC)
- O Container `TeamPage`.
- As chamadas das 5 APIS de base serão paralelizadas com `Promise.allSettled`.
- Injeção das propriedades iniciais (InitialData) para o ClientComponent folha.

**Risco Mapeado:** Manter o Typescript síncrono e garantir que a re-injeção do React Query não quebre em caso de 401 ou rotas onde o usuário não possua autorização total (ex: Ele pode listar, mas não tem permissão de ver `stats`). Usaremos `Promise.allSettled` para contornar requisições parcialmente falhas.
