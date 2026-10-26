# DEEPFARMS-AGRO-PWA-MVP-02B1 — Simplificação e isolamento do MVP público

Data: 26/10/2026  
Escopo: somente navegação e metadados de apps/agro.  
Não foram alterados apps/web, apps/campo, services/api, bancos ou infraestrutura.

## 1. Resumo das alterações

- Header desktop: removidos os itens Comunidade e Minha Conta. Permanecem Início, Clima, Mercado e Calculadoras.
- Navegação inferior mobile: removida Conta. Permanecem Início, Clima, Mercado e Calculadoras.
- Home: removido o card Comunidade “Em Breve” e ajustada a descrição para não prometer uma funcionalidade futura.
- Metadados globais: descrição da aplicação limitada ao escopo clima, mercado e calculadoras.
- A rota /conta, o painel de conta/autenticação, /comunidade e seus componentes foram preservados.
- Não há componentes de comunidade/chat importados pelo layout global. A página de comunidade segue acessível somente por URL direta; nenhuma implementação de chat, mensagens, grupos ou diretório foi feita.

## 2. Arquivos alterados

1. apps/agro/src/components/layout/header.tsx
2. apps/agro/src/components/layout/bottom-nav.tsx
3. apps/agro/src/app/page.tsx
4. apps/agro/src/app/layout.tsx
5. docs/implementation/reports/DEEPFARMS-AGRO-PWA-MVP-02B1-SIMPLIFICACAO-ISOLAMENTO.md

Nenhum arquivo de Conta, Comunidade, autenticação, clima, mercado, calculadoras, manifest ou Service Worker foi editado.

## 3. Comportamento anterior e posterior

| Área | Antes | Depois |
|---|---|---|
| Header desktop | Quatro áreas do MVP + Comunidade; botão Minha Conta | Somente as quatro áreas públicas do MVP |
| Navegação mobile | Início, Clima, Mercado, Calculadoras e Conta | Somente Início, Clima, Mercado e Calculadoras |
| Home | Cards públicos e card de Comunidade futura | Cards somente para as áreas do MVP |
| Rotas diretas | /conta e /comunidade disponíveis | Continuam disponíveis sem alteração funcional |
| Layout global | SessionHeartbeat montado globalmente | Mantido globalmente; ver bloqueio abaixo |

As rotas públicas, seleção de localidade, stores localStorage, calculadoras, clima, indicadores de mercado, manifest, Service Worker e página offline não foram alterados.

## 4. Heartbeat: diagnóstico e bloqueio

O layout global monta SessionHeartbeat em todas as rotas. O componente agenda uma tentativa após dois segundos, e novas tentativas limitadas por interação/visibilidade. A chamada ocorre antes de saber se o usuário está autenticado; resposta negativa suspende as tentativas subsequentes.

Não existe estado global de sessão disponível no layout. O cookie de sessão é HttpOnly, portanto não é uma fonte legível pelo cliente. O único estado de usuário encontrado fica dentro de PainelConta, carregado por fetchCurrentAgroUser na página /conta. Usar esse estado apenas nessa página mudaria o alcance do heartbeat autenticado; fazer uma nova chamada /auth/me no layout adicionaria uma verificação de autenticação em toda visita anônima. Nenhuma dessas alternativas preservaria o comportamento atual sem custo ou sem um novo estado compartilhado.

Conforme a instrução de não improvisar autenticação quando não houver estado confiável, SessionHeartbeat não foi modificado nem removido do layout. **O requisito “usuário anônimo: nenhuma chamada de heartbeat” permanece pendente.** É o único critério de aceite funcional não concluído nesta fase; a mudança precisa de uma decisão/estado de sessão compartilhado aprovado antes de remover a chamada anônima sem degradar sessões autenticadas.

## 5. Isolamento de Conta e Comunidade

- Os links de Conta e Comunidade foram retirados das navegações principal e inferior. O card da Comunidade na home também foi removido.
- /conta permanece funcional como estava, incluindo o painel existente e suas chamadas de identidade quando aberto diretamente. Não é requisito para consultar áreas públicas e não aparece na navegação.
- /comunidade permanece uma página de planejamento “Em Breve”. Não implementa chat nem faz parte dos imports do layout global.
- O código de conta, autenticação e comunidade não foi removido ou alterado.
- Não foi encontrado menu hambúrguer adicional; as duas navegações existentes são header desktop e bottom nav mobile.

## 6. Testes executados

Executados a partir de apps/agro, sem iniciar API, PostgreSQL, Redis, Next dev/start ou Playwright:

| Verificação | Resultado |
|---|---|
| TypeScript: node_modules/.bin/tsc --noEmit | PASS, exit code 0 |
| ESLint: node_modules/.bin/eslint src --ext .ts,.tsx | PASS, exit code 0 |
| Vitest: node_modules/.bin/vitest run | PASS, 11 arquivos e 155 testes |
| Build: node_modules/.bin/next build --webpack | PASS; compilação, TypeScript, coleta de dados, prerender das rotas e traces. 10 páginas geradas. |
| Playwright/E2E | Não executado; os scripts iniciam um servidor Next e o E2E de laboratório pressupõe API. |

O build criou/atualizou artefatos gerados em apps/agro/.next. Nenhuma dependência foi instalada. Não foram feitas chamadas externas.

### Evidência de navegação

Inspeção estática confirma que as listas NAV_ITEMS do header e bottom nav contêm apenas os quatro destinos do MVP. O JSX da home não contém o card nem link da Comunidade. As páginas de Conta e Comunidade continuam presentes e foram prerenderizadas no build. Não foi feita validação interativa em navegador.

### Evidência de heartbeat

Inspeção do código confirma que SessionHeartbeat continua no layout global e ainda chama sendAgroHeartbeat após montagem/interação. Portanto não se declara que chamadas anônimas foram eliminadas; o controle ainda não foi atendido por bloqueio arquitetural descrito acima.

## 7. Riscos e pendências

1. **Bloqueio de aceite:** determinar sessão autenticada sem chamada adicional ou perda do heartbeat autenticado exige estado global de sessão que não existe hoje; nenhuma solução foi inventada.
2. Conta continua acessível por URL direta e pode apresentar operações de autenticação. Ela não é carregada nem obrigatória nas rotas do MVP.
3. A navegação foi validada por código/build, não por browser/device E2E.
4. O build pode atualizar apenas arquivos gerados de .next; fontes de apps/web e apps/campo não foram tocadas.

## 8. Veredicto

**NO-GO para declarar a fase integralmente concluída**, porque o requisito de heartbeat anônimo permanece pendente e não havia estado de sessão confiável disponível sem acrescentar uma chamada/abstração não autorizada.

**GO COM RESSALVAS para a simplificação de navegação:** header, home e navegação mobile agora apresentam somente as quatro áreas públicas; rotas e componentes futuros permanecem preservados; TypeScript, ESLint, Vitest e build passaram.

Nenhuma fase seguinte foi iniciada. Aguardar análise e autorização.
