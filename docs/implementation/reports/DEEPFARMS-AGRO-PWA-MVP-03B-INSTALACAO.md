# DeepFarms Agro PWA — MVP-03B Convite de Instalação

**Data:** 27/10/2026  
**Veredicto:** **GO COM RESSALVAS** para o convite e seus cenários automatizados. A instalação efetiva em dispositivo físico não foi simulada nem declarada como aprovada.

## O que já existia

A página inicial já montava `InstallPrompt`. O componente tratava `beforeinstallprompt`, o evento `appinstalled`, modo standalone e instruções básicas para iPhone/iPad. Porém, o banner só era mostrado depois do evento nativo ou em dispositivos Apple, a dispensa era apenas temporária, faltavam instruções manuais para outros navegadores e o texto prometia “funcionamento offline na lavoura”, o que poderia sugerir disponibilidade offline de clima e mercado.

O registro do Service Worker já estava corrigido na fase MVP-03A em `service-worker-register.tsx`. Essa correção foi preservada. O comportamento de cache e exclusão de `/api/` também não foi alterado.

## Implementação

O convite agora aparece na página inicial para visitantes que ainda não o dispensaram e não estão usando o PWA em modo standalone. Usa o texto solicitado, adapta o ícone e as instruções a iPhone/iPad, incluindo iPadOS com user agent de desktop, e oferece instruções manuais para navegadores sem `beforeinstallprompt`.

Quando o navegador disponibiliza `beforeinstallprompt`, o botão chama o prompt nativo. A escolha do prompt não é tratada como instalação concluída; o convite só é ocultado por detecção de standalone ou pelo evento `appinstalled`. Fechar o convite grava uma preferência local e a dispensa persiste após recarregar. Se o armazenamento estiver bloqueado, a dispensa ainda vale durante a sessão atual.

A renderização inicial mantém snapshots compatíveis com SSR, evitando diferenças entre HTML do servidor e cliente. Nenhuma biblioteca, endpoint, autenticação ou chamada externa foi adicionada.

## Arquivos desta fase

- `apps/agro/src/components/pwa/install-prompt.tsx` — revisão do componente existente.
- `apps/agro/tests/e2e/pwa-install.spec.ts` — cenários Chromium do convite e instalação.
- Este relatório.

Os arquivos de registro do Service Worker e dos testes offline constavam como modificados antes desta fase e foram preservados sem alteração. `apps/agro/next-env.d.ts` também já estava modificado antes da tarefa; não foi alterado intencionalmente nesta fase. Nenhum outro app, backend, banco ou infraestrutura foi tocado.

## Validação

- `npm run typecheck` — **PASS**.
- `npm run lint` — **PASS**.
- `npm test` — **PASS**, 161 testes em 12 arquivos.
- `AGRO_API_INTERNAL_ORIGIN=http://127.0.0.1:18001 NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 npm run build` — **PASS**, build Next.js de produção.
- `AGRO_API_INTERNAL_ORIGIN=http://127.0.0.1:18001 npm run test:e2e -- tests/e2e/pwa-install.spec.ts tests/e2e/pwa-calculadoras.spec.ts` — **PASS**, 12/12 no Chromium contra o build de produção.
- `git diff --check` — **PASS**.

Os sete cenários do convite cobriram: fallback manual, chamada de prompt nativo simulado sem declarar instalação, instruções iPhone, identificação de iPadOS, ocultação em standalone, reação a `appinstalled` e persistência da dispensa. Os cinco cenários da fase 03A também passaram: registro/controle do Service Worker, app shell, calculadoras, recarga e cálculo offline de 350 sacas para 21.000 kg, e ausência de `/api/` no CacheStorage.

Na primeira execução Playwright, dois testes dispararam eventos sintéticos antes de os efeitos React registrarem os listeners. O teste foi ajustado para aguardar essa inscrição; a execução final passou integralmente. Não foi necessário alterar o código do Service Worker.

## Limitações

O `beforeinstallprompt` foi testado por evento simulado no Chromium. A apresentação do prompt nativo real depende do navegador, dos critérios de instalabilidade e de interação do usuário. Os passos do iOS/iPadOS foram verificados com user agents emulados; a instalação pela folha de compartilhamento requer validação manual em dispositivo Apple. Os testes não comprovam instalação física.

O convite não afirma que dados de clima ou mercado estarão sempre atualizados offline. As funcionalidades públicas, calculadoras e regras existentes do Service Worker permaneceram fora do escopo de alteração.
