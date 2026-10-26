# DEEPFARMS-AGRO-PWA-MVP-02B1A — Correção do heartbeat público

Data: 26/10/2026  
Escopo: somente apps/agro e este relatório. Nenhum backend, banco, serviço ou ambiente de produção foi acessado ou alterado.

## 1. Resumo

O SessionHeartbeat foi removido do layout global e movido para o ramo autenticado de PainelConta. Assim, as rotas públicas não montam o componente e não enviam POST para /api/v1/auth/heartbeat. Na rota /conta, o componente só existe depois que o estado local existente confirma um usuário, seja pelo carregamento da sessão atual ou após login/registro.

Não foi criado estado global, endpoint, polling de identificação nem leitura de cookie. O código do componente e do cliente de auth foi preservado.

## 2. Diagnóstico e impacto em sessão

O componente anterior agendava heartbeat dois segundos após a montagem e fazia novas tentativas controladas por visibilidade, conectividade e interação. A rota backend existente documenta que a operação atualiza ultimo_heartbeat e recalcula expira_em pelo timeout de inatividade. A autenticação das rotas é validada pela sessão/token, independentemente do heartbeat; não foi encontrada dependência do heartbeat como autorização para páginas públicas.

O estado AgroUsuario já é carregado pela própria PainelConta usando fetchCurrentAgroUser e mantido localmente:

- usuário anônimo ou página pública: SessionHeartbeat não é montado; não há chamada de heartbeat.
- usuário autenticado com /conta aberta: heartbeat mantém comportamento de renovação durante a permanência na área autenticada.
- usuário que sai de /conta e navega nas páginas públicas: heartbeat para; a sessão passa a expirar pelo limite normal de inatividade. Ao voltar à conta, poderá precisar autenticar novamente.
- logout: user passa a null e o ramo autenticado é desmontado, parando o heartbeat.

O efeito é restringir a extensão do timeout à área de conta aberta, sem enfraquecer autorização. Não manter o heartbeat ativo durante o uso anônimo também evita atividade de sessão sem necessidade para clima, mercado e calculadoras.

## 3. Arquivos alterados

1. apps/agro/src/app/layout.tsx — remove import e montagem global.
2. apps/agro/src/components/auth/painel-conta.tsx — monta SessionHeartbeat somente dentro do ramo if (user).
3. apps/agro/tests/unit/session-heartbeat-mount.test.ts — adiciona contrato estático para ausência no layout e montagem condicional na conta.
4. docs/implementation/reports/DEEPFARMS-AGRO-PWA-MVP-02B1A-HEARTBEAT-PUBLICO.md — este relatório.

## 4. Testes

Executados a partir de apps/agro; sem API, PostgreSQL, Redis, deploy ou Playwright:

| Check | Resultado |
|---|---|
| TypeScript: node_modules/.bin/tsc --noEmit | PASS, exit code 0 |
| ESLint: node_modules/.bin/eslint src --ext .ts,.tsx | PASS, exit code 0 |
| Vitest: node_modules/.bin/vitest run | PASS, 12 arquivos e 157 testes (antes: 11 arquivos/155 testes) |
| Build: node_modules/.bin/next build --webpack | PASS; compilação, TypeScript, geração estática e traces concluídos; 10 páginas geradas, incluindo /conta |
| Teste de ausência pública | PASS como teste estático: layout não importa nem monta SessionHeartbeat |
| Teste de montagem autenticada | PASS como teste estático: o componente aparece somente após o guard if (user) em PainelConta |
| Comportamento de /conta em navegador | Não executado; E2E exigiria iniciar um servidor Next e não foi solicitado nesta fase |

O teste direcionado comprova o contrato de montagem no código, não uma sessão real no backend. A preservação do fluxo de login foi verificada por inspeção de que os handlers e o estado de usuário permaneceram inalterados e de que a rota continua no build.

## 5. Segurança e limites

- O endpoint heartbeat continua protegido pelo fluxo existente de autenticação/CSRF; nenhum controle foi relaxado.
- As páginas públicas não precisam de sessão para navegação, clima, mercado ou calculadoras.
- A sessão autenticada pode expirar durante a navegação pública porque sua renovação agora ocorre somente enquanto /conta autenticada permanece aberta. Esse comportamento é deliberadamente mais restritivo e pode exigir novo login ao retornar.
- Nenhuma chamada de identificação foi adicionada. /conta continua usando sua busca de usuário pré-existente para renderizar a experiência de conta.
- Nenhum teste E2E ou conexão com serviços foi feito.

## 6. Veredicto

**GO COM RESSALVAS.** O heartbeat foi isolado das páginas públicas e permanece disponível na área autenticada existente. TypeScript, ESLint, testes e build passaram. A ressalva é que, ao sair de /conta, o heartbeat não renova a sessão; o usuário autenticado pode precisar entrar novamente após o timeout de inatividade. O comportamento real de login em navegador não foi exercitado nesta etapa.

Nenhuma fase posterior foi iniciada.
