# EXECUTION-32 — FASE 30 FRONTEND MVP RELATÓRIO ESG E PASSAPORTE DE RASTREABILIDADE

## Contexto

A Fase 29 expôs a API pública protegida para Relatório ESG e Passaporte de Rastreabilidade. A Fase 30 teve como objetivo criar um frontend MVP autenticado para consultar e operar essas entidades.

## Resumo das Alterações

1.  **Interfaces e Hooks Frontend:**
    *   Criados tipos `RelatorioESG`, `PassaporteRastreabilidade`, e tipos auxiliares no `apps/web/src/services/certificacoes-esg/service.ts`.
    *   Criados métodos no serviço `apiFetch` para as rotas da API exposta (`criarRelatorioESG`, `listarRelatoriosESG`, `criarPassaporte`, `listarPassaportes`).
    *   Implementados hooks TanStack Query em `apps/web/src/hooks/use-relatorios-passaportes.ts` garantindo caching e "optimistic updates" para as consultas.

2.  **UI MVP Autenticada:**
    *   Criada a página Next.js App Router (RSC) em `apps/web/src/app/(dashboard)/dashboard/certificacoes-esg/relatorios-passaportes/page.tsx`.
    *   Criado o Client Component `RelatoriosPassaportesClient.tsx` que utiliza `Tabs` (shadcn) para alternar entre "Relatórios ESG" e "Passaportes".
    *   A tela permite visualizar os registros em formato de tabela, possuindo Badges de status para indicação visual rápida.
    *   A tela possui modals (`Dialog` do shadcn) e formulários (`react-hook-form` via states locais) para criação de novos Relatórios ESG e Passaportes, invocando os mutation hooks criados e provendo feedback em tela usando `toast` (sonner).

3.  **Navegação e Integração no Sidebar:**
    *   A página foi integrada ao sidebar global alterando `apps/web/src/lib/sidebar-config.ts`.
    *   Adicionado o link "Relatórios & Passaportes" sob o módulo de Compliance Ambiental (AM1) para facilitação de navegação.

4.  **Testes e Qualidade:**
    *   Criados testes end-to-end com Playwright em `apps/web/tests/e2e/certificacoes-esg-relatorios-passaportes.spec.ts` para garantir o carregamento correto da página, a navegação entre abas e o funcionamento do fluxo de abertura e fechamento de modais.
    *   Validação estrita de tipagem (strict mode do TypeScript) assegurando zero violações de "any" implícito nos novos artefatos do frontend.

## Observações

*   **Não Houve Alteração no Backend:** Nenhuma migração ou alteração nos models SQLAlchemy/Pydantic foi feita; todo o trabalho foi no consumidor frontend.
*   **Regras de Tenant Respeitadas:** Como o payload não exige `tenant_id` explicitamente (o backend infere a partir do auth token), os models de formulário contêm estritamente os campos necessários, seguindo a Lei 13 e garantindo segurança multi-tenant no frontend.

## Status: SUCCESS
A tarefa foi concluída de acordo com as especificações da EXECUTION-32 e diretrizes de Front-End (AGRO-03).
