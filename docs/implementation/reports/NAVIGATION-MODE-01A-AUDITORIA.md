# NAVIGATION-MODE-01A-AUDITORIA

## 1. Objetivo
Auditar a infraestrutura atual de navegação baseada no Sidebar e identificar o que pode ser reaproveitado para a implementação do Mega Menu. Definir a arquitetura técnica, como persistir as preferências do usuário, mapear os arquivos que serão impactados e levantar riscos antes da execução.

## 2. Contexto
O sistema DeepAgro já possui um Sidebar modular, com hierarquias de navegação configuráveis baseadas em módulos, tiers de planos, permissões (RBAC), guards de navegação (ModuleGate) e resolução de rotas ativas. Com o épico `NAVIGATION-MODE-01`, introduziremos a preferência de usuário para um **Mega Menu**, preservando totalmente os mecanismos de controle e a árvore de navegação original. O objetivo desta fase é garantir que não haja duplicação lógica nem técnica, e definir a fundação (Phase B) para acomodar a nova UI.

## 3. Arquivos Alterados
Nenhum código será alterado nesta fase. No entanto, os seguintes arquivos foram auditados para subsidiar este relatório:
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/lib/sidebar-navigation.ts`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/components/layout/app-mega-menu.tsx` (a criar)
- `apps/web/src/components/layout/navigation-shell.tsx` (a criar/ajustar)
- `apps/web/src/app/(dashboard)/layout.tsx`
- `apps/web/src/lib/permissions.ts`
- `apps/web/src/components/shared/module-gate.tsx`
- `apps/web/src/lib/stores/app-store.ts`
- Backend Auth Models e Schemas (e.g., `services/api/core/models/auth.py`, `services/api/core/schemas/auth_schemas.py`)

## 4. Decisões Técnicas

**Fonte Única de Verdade da Navegação:**
A configuração contida em `apps/web/src/lib/sidebar-config.ts` (`CORE_CADASTROS`, `MODULOS_OPERACIONAIS`, `BACKOFFICE_SECTIONS`) e os resolvers em `apps/web/src/lib/sidebar-navigation.ts` já exportam tudo que precisamos: grupos, seções, ícones, rotas, dependências de permissões (`permission`), módulos (`moduleId`) e validações de tiers.
O Mega Menu consumirá exatamente os mesmos arrays e a mesma lógica de "match" das rotas.

**Local de Persistência (User Preferences):**
Após auditoria, identificamos que o backend (`Usuario` no db) ainda não possui uma coluna genérica de "Preferences" e as mutações (`UserUpdateRequest`) limitam-se aos dados básicos (nome, telefone, etc). 
Por prioridade das regras, devemos "Evoluir estrutura pessoal existente". Sendo assim, **recomendamos adicionar um campo genérico `preferencias_ui (JSON)` na tabela `usuarios` no Backend** ou, alternativamente, utilizar inicialmente o Zustand (`app-store.ts`) para cache local otimista e salvar na tabela com migração assim que viável. O app-store.js usa local storage e não deve ser "única fonte". Portanto, parte das próximas etapas incluirá a migração do banco para salvar essas preferências via API.

## 5. Arquitetura
A arquitetura se baseará na extração da lógica agnóstica de iterar menus para hooks/seletores, consumida por dois renderers:
```text
(Fonte: sidebar-config.ts + permissions.ts + app-store.ts)
                    │
            useNavigationMenu (Hook a criar)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   AppSidebar              AppMegaMenu
```
O arquivo `layout.tsx` conterá um switch (ou `NavigationShell`) que lê a preferência `navigationMode` (`sidebar` | `mega-menu`) e renderiza o respectivo componente.

## 6. UX
- O Sidebar será mantido como padrão.
- O Mega Menu usará navegação visual e semântica com dropdowns ou painel modal ocupando a largura total (ou max-width) no topo.
- O Topbar será ajustado quando no modo Mega Menu, incorporando links para abrir o painel e os mesmos contextos de "Safra" originais.

## 7. Acessibilidade
O AppMegaMenu implementará ARIA roles específicos de navegação (menu, menuitem, aria-expanded), controle via teclado (ESC para fechar, setas/Tab para navegação) e gerenciamento de foco rigoroso (Focus Trap ao abrir no formato fullscreen).

## 8. Persistência
Como mencionado, será feita de forma otimista no cliente (Zustand `useAppStore` salva no Storage), disparando um `PATCH /auth/me/preferences` (endpoint e coluna novos a serem incluídos na fase backend, se autorizado, caso contrário ficaremos limitados à persistência no Store).

## 9. Permissões
100% idênticas ao Sidebar, resolvidas pelo mesmo utilitário e funções de filtro (usando `hasTenantPermission`).

## 10. Tiers
As tags `minimumTier` continuam sendo respeitadas. Módulos que não atingem a versão contratada sequer aparecerão, mantendo a paridade visual em ambos os modos.

## 11. ModuleGate
Não haverá necessidade de duplicar. O Mega Menu utilizará as lógicas de verificação da conta do usuário. Elementos que exigem `ModuleGate` continuam sendo roteados normalmente para as páginas, e as páginas se encarregam do restante. Para exibição de UI do link do menu, o menu usa a chave `moduleId` e checa via hook (`useHasModule`).

## 12. Testes Necessários
- **Unitários:** Verificar renderização do componente condicional, hooks de preferência, persistência local e integridade de roteamento entre os dois modos.
- **E2E:** Login, validação da persistência (refresh), navegação e troca do componente. Teste de regressão para verificar se o modo Sidebar continua intocado. Acessibilidade (teclado e ARIA). Mobile behavior.

## 13. Validação Visual
Deverá ser rodada nos breakpoints estipulados (Mobile 390x844 até Desktop 1440x900). O Mega Menu precisará converter-se em Drawer listado/accordion nativo no mobile (reaproveitando o mesmo Drawer que o Sidebar ou adaptando).

## 14. Riscos
- **Mobile Regression:** O Mega Menu pode ter um layout denso no desktop, que não fica bom em mobile. **Mitigação:** No mobile, independente da escolha (Sidebar ou Mega Menu), ambos se transformam em um Drawer modal unificado.
- **Acoplamento Layout:** A extração do Topbar e Sidebar do layout pode quebrar layouts específicos como o `SafraContextHeader`. **Mitigação:** Modularização cuidadosa com um NavigationShell (container).
- **Backend Sync:** Adição da persistência real de usuário demanda back-end migration. Se o backend estiver bloqueado, dependemos do local storage/store localmente temporário.

## 15. Itens Não Alterados
- API de Domínios
- Estrutura de Tenant e Permissões core
- Roteamento Next.js (pages/layout logic)
- Rota Ativa (os matchers em `sidebar-navigation.ts` continuam sendo 100% utilizados)

## 16. Impacto no Piloto
Sem impactos críticos de produção, visto que o default fallback para quem não tem preferência configurada será o `Sidebar` clássico (comportamento atual). Apenas impactará early adopters que engajarem no painel de configurações para testar o modo Mega Menu.

## 17. Veredicto
**GO**. A infraestrutura atual no frontend é bastante coesa, exportando metadados de navegação dissociados do componente visual `AppSidebar`. Há paridade e flexibilidade para montar a Fase B sem grandes sustos. 
Como próximo passo, sugiro aprovar o Implementation Plan, onde passaremos para a fase `NAVIGATION-MODE-01B`.
