# NAVIGATION-ARCH-02A — Correções Estruturais e Guardrails do Sidebar

**Data:** 2026-07-29  
**Status:** GO COM RESSALVAS

## Resumo executivo

Foram corrigidos os defeitos estruturais confirmados na auditoria
`NAVIGATION-ARCH-01`, sem reorganizar a árvore de navegação, alterar rotas
públicas ou modificar APIs, backend, Campo PWA, RLS ou permissões de backend.

O sidebar agora usa o catálogo oficial para Estoque/Suprimentos e Copiloto IA,
não expõe os links pecuários sem página correspondente e centraliza o
mapeamento de rota para autoexpansão. Um guardrail executável protege a
configuração contra novos `moduleId`, tiers, permissões, rotas e duplicações
inconsistentes.

## Achados confirmados e correções

| Achado | Evidência | Decisão | Resultado |
| --- | --- | --- | --- |
| Suprimentos usava `O1_FROTA` | Catálogos Web e API definem `O1_FROTA` como Frota, `O2_ESTOQUE` como Estoque e `O3_COMPRAS` como Compras | Gate-base do grupo alterado para `O2_ESTOQUE`; seção Compras recebe gate específico `O3_COMPRAS` | Estoque não depende de Frota; Compras continua condicionada ao módulo próprio |
| Copiloto usava `IA_COPILOT` | Catálogos e planos oficiais usam `EXT_IA` | Sidebar alterado para `EXT_IA`; alias de leitura explícito preserva contratos legados | Configuração canônica e tenants legados permanecem compatíveis |
| Pecuária apontava para três rotas sem página | Existe `/dashboard/pecuaria/manejo`; não existem `/manejos`, `/vacinas` ou `/nutricao` | `manejos` foi corrigida para `manejo`; Vacinação e Nutrição foram removidas do menu | Nenhum link quebrado conhecido permanece no sidebar |
| Autoexpansão incompleta | Lógica local não reconhecia Imóveis, Frota, IA e Campo | Mapa reutilizável `sidebar-navigation.ts` passou a ser usado pelo sidebar | Rota direta, detalhe e atualização preservam o módulo correto |

### Decisão das rotas de Pecuária

| Entrada anterior | Classificação | Decisão |
| --- | --- | --- |
| `/dashboard/pecuaria/manejos` | erro de pluralização | corrigida para `/dashboard/pecuaria/manejo` |
| `/dashboard/pecuaria/vacinas` | funcionalidade ainda não implementada | removida temporariamente do menu |
| `/dashboard/pecuaria/nutricao` | funcionalidade ainda não implementada | removida temporariamente do menu |

As rotas de planejamento de manejos existentes, como
`/dashboard/pecuaria/manejos/planejamento`, foram preservadas.

## Autoexpansão

O mapeamento oficial agora cobre Agricultura, Pecuária, Estoque/Suprimentos,
Frota, Imóveis Rurais, Financeiro, RH, Ambiental, IA, Campo e Cadastros. A
ordem prioriza prefixos específicos — Campo antes de Frota e Imóveis antes de
Cadastros — para que rotas filhas mantenham o contexto correto. Não houve
alteração da regra atual de manter um módulo aberto.

## Guardrails implementados

O comando `npm run test:sidebar` valida:

1. todo `moduleId` do sidebar contra o catálogo oficial ou alias explícito;
2. todos os tiers declarados;
3. todas as permissões contra o catálogo backend, exceto allowlist legada
   documentada;
4. cada `href` interno contra página existente ou redirect explicitamente
   allowlisted;
5. duplicação exata de `href`, com allowlist limitada para Imóveis e Segurança
   do Trabalho, já declarados em contextos distintos;
6. presença dos mapeamentos de autoexpansão dos domínios obrigatórios;
7. manutenção explícita do alias legado `IA_COPILOT -> EXT_IA`.

Os redirects permitidos são os seletivos de Safras para Orçamento e
Planejamento Operacional. Não há rota dinâmica do sidebar atual que exija
exceção adicional.

## Arquivos alterados

- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/lib/sidebar-navigation.ts`
- `apps/web/src/components/layout/app-sidebar.tsx`
- `apps/web/src/lib/constants/modulos.ts`
- `apps/web/src/hooks/use-has-module.ts`
- `apps/web/scripts/check-sidebar-guardrails.mjs`
- `apps/web/package.json`

Não houve alteração em backend, APIs, banco, RLS, Campo PWA, rotas públicas,
planos, preços ou catálogo comercial.

## Validações executadas

| Comando | Resultado |
| --- | --- |
| `cd apps/web && npm run test:sidebar` | aprovado — 134 `hrefs`, 12 gates |
| `cd apps/web && npm run typecheck` | aprovado |
| `cd apps/web && npm run lint` | aprovado (script oficial atual) |
| `cd apps/web && npm run build` | aprovado |
| `git diff --check` | aprovado no repositório raiz e no subprojeto Web |

## Riscos e limitações

- Existem 26 permissões já declaradas no sidebar que não aparecem literalmente
  no catálogo backend. Elas foram mantidas em allowlist explícita e limitada,
  para não mascarar novas divergências. A convergência do catálogo RBAC é
  trabalho próprio, fora deste escopo.
- O alias `IA_COPILOT` foi preservado somente para leitura de contratos antigos;
  nenhuma nova configuração deve utilizá-lo.
- Vacinação e Nutrição não ficam acessíveis por menu até que as funcionalidades
  possuam rotas reais e auditadas.

## Próximos passos

Prosseguir, separadamente, com `NAVIGATION-ARCH-02B` para reorganizar a jornada
de Agricultura. Esta execução não iniciou essa reorganização.

## Veredicto

**GO COM RESSALVAS.** Os defeitos de gate, rota e autoexpansão foram corrigidos
de forma cirúrgica, com guardrails automatizados. A ressalva é a divergência
legada e explicitamente controlada entre permissões de navegação e catálogo
backend, que não deve ser resolvida por alteração de RBAC nesta fase.
