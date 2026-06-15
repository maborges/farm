# Diagnóstico Local: `dashboard/settings/roles/page.tsx`

Antes da migração para o padrão RSC, foi realizado o seguinte diagnóstico detalhado na página de permissões (RBAC) do sistema.

## 1. Métricas e Dimensões
- **Arquivo Alvo:** `apps/web/src/app/(dashboard)/dashboard/settings/roles/page.tsx`
- **Tamanho Total:** 729 linhas de código
- **Complexidade:** Alta (Classe C2)

## 2. Inventário de Funcionalidades (Client-Side)
### Hooks Identificados
- **React:** `useState`, `useCallback`
- **TanStack Query:** `useQuery`, `useMutation`, `useQueryClient`
- **DND Kit (Drag and Drop):** `useSensor`, `useSensors`, `useDroppable`, `useSortable`

### Componentização Interna
- `RoleForm`: Formulário interativo para definir perfis (nome e matriz de acesso).
- `RoleCardContent`: Corpo dos cards de perfil, renderizando contagem de permissões.
- `SystemRoleCard`: Card bloqueado para roles do sistema.
- `CustomRoleCard`: Card drag-and-drop para roles customizadas com botões de edição/exclusão.

### Data Fetching & Mutations
- **Queries:**
  - 1 `useQuery` principal (`/team/roles`)
- **Mutations:**
  - `saveRole`: para criar/editar perfis e suas permissões
  - `deleteRole`: para remover perfis customizados
  - `reorderRoles`: para atualizar ordenação após Drag-and-Drop

## 3. Estados Críticos Mapeados
1. `createOpen`: Controla abertura do modal principal de criação.
2. `editTarget`: Carrega o objeto `TenantRoleProfile` ativo para o formulário.
3. `cloneTarget` / `cloneName`: Gerenciam a cópia profunda de perfis existentes.
4. `orderedCustomIds`: Mantém a sincronia volátil do DnD kit antes de enviar ao servidor.
5. Matriz de Permissões (`getGranted` / `countGranted`): Utiliza os dados parciais do banco para assinalar a árvore de checks na tela.

## 4. O que Permaneceu no Client?
Toda a dinâmica visual foi movida de forma idêntica para o novo arquivo `RolesClient.tsx`:
- *Drag and drop*, *modais*, *mutations*, *estado de drag*, *notificações (toasts)* e *filtros*.
- A checagem de "System Roles vs Custom Roles" foi estritamente preservada para impedir corrupção das roles padrão do sistema.

## 5. O que foi Movido para o Server (RSC)?
- O arquivo raiz `page.tsx` se tornou um React Server Component.
- Passou a buscar os perfis iniciais através de `apiFetchServer("/team/roles")`.
- Passa o payload de inicialização via props para hidratação direta (`initialRoles`).

**Conclusão:** Nenhum ponto de segurança ou contrato RBAC foi quebrado e a página passa a ser _server-first_.
