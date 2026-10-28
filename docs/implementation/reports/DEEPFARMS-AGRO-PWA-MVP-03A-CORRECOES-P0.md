# DEEPFARMS Agro PWA — MVP-03A Correções P0

**Data:** 27/10/2026  
**Veredicto:** **GO para encerramento dos dois P0 testados.** Esta validação não representa GO geral para publicação nem cobre integrações externas.

## Causas e correções

### Service Worker

O registro era iniciado somente no evento `load`; o checkout não oferecia uma confirmação robusta de que o SW já controlava a primeira página antes de o usuário continuar. Além disso, os bundles Next carregados antes do controle não passavam pela regra de cache `/_next/`.

Em `apps/agro/src/components/pwa/service-worker-register.tsx`, o registro agora começa no efeito de hidratação. Quando o SW assume a página, o cliente faz um reload único, protegido por marcador de sessão `pending/done`; nesse reload os bundles são solicitados sob controle do SW e entram no cache de runtime. A instalação continua usando o app shell atual e a regra do SW que exclui `/api/` foi preservada.

### Calculadora offline

A lógica matemática e o estado React da calculadora não estavam defeituosos. O teste anterior recarregava com `waitUntil: "domcontentloaded"` e digitava antes da hidratação JavaScript. O snapshot mostrava o input alterado para `350`, mas os resultados SSR ainda em `100` sacas/`6.000 kg`.

O fluxo agora espera o controle do SW e o reload de estabilização. O cenário offline espera `load` e `networkidle` antes de interagir. Depois disso, `350` sacas recalcula para `21.000 kg` e a navegação offline entre calculadoras funciona.

## Arquivos alterados

- `apps/agro/src/components/pwa/service-worker-register.tsx`
- `apps/agro/tests/e2e/pwa-calculadoras.spec.ts`
- Este relatório.

Nenhum outro app, backend, banco, serviço ou configuração comercial foi alterado.

## Evidências de validação

- `npm run typecheck` — PASS.
- `npm run lint` — PASS.
- `npm run build` com `NODE_ENV=production` — PASS; build otimizado Next.js 16.1.6.
- `npm run test:e2e -- tests/e2e/pwa-calculadoras.spec.ts` — **5/5 PASS** em Chromium contra o build de produção.
  - Registro, ativação e controle do Service Worker — PASS.
  - Pré-cache do app shell — PASS.
  - Cinco calculadoras interativas online — PASS.
  - Reload offline, recálculo de 350 sacas para 21.000 kg e navegação offline — PASS.
  - `/api/status-teste` ausente de todos os CacheStorage — PASS.

O Playwright iniciou e encerrou apenas o servidor local de produção. `AGRO_API_INTERNAL_ORIGIN` permaneceu em `127.0.0.1:18001`, sem listener; não houve acesso a API, bancos ou serviços externos.

## Limites

Os cenários P1 de fallback offline de preços e cache climático expirado não foram executados nem alterados nesta fase. O veredicto é restrito aos dois P0 designados.
