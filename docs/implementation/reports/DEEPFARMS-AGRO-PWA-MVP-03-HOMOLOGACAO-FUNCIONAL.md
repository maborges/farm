# DEEPFARMS Agro PWA — MVP-03 Homologação Funcional

**Data:** 27/10/2026  
**Escopo:** teste funcional somente leitura em Chromium real; nenhuma correção foi aplicada.

## Veredicto

**NO-GO para publicação do MVP nesta rodada.** O build de produção concluiu, mas dois cenários centrais de PWA/offline falharam no navegador real: o Service Worker não foi registrado e a calculadora não recalculou após reabrir a página sem rede. BCB/IBGE reais e a API de clima não foram validados; exigiriam o backend e consultas não autorizadas nesta execução.

## Segurança e ambiente de teste

- O `.env.local` da API contém variáveis de banco, Redis e provedores. Seus valores não foram exibidos. Como não foi comprovado que os destinos efetivos eram isolados, **FastAPI, PostgreSQL e Redis não foram iniciados**.
- Nenhum banco compartilhado, RDS, provedor comercial ou API externa foi acessado. Não houve migration, seed ou alteração de infraestrutura.
- O Next.js foi executado somente em loopback durante o Playwright. A origem do proxy API foi apontada para `127.0.0.1:18001`, sem serviço nessa porta. Chamadas ao backend foram, portanto, deliberadamente recusadas; testes com resposta usaram interceptações/fixtures sintéticas.
- O lock vazio de desenvolvimento em `apps/agro/.next/dev/lock` datava de 26/10, sem processo Next ativo e sem listener em 3004/3005. O arquivo gerado obsoleto foi removido para permitir o teste; nenhum arquivo-fonte/configuração foi alterado por isso.
- A execução Playwright encerrou o servidor web de teste ao terminar. Não foram encerrados processos preexistentes.

## Build e execução no navegador

| Verificação | Resultado | Evidência |
|---|---|---|
| Build de produção (`npm run build`) | PASS | Next.js 16.1.6 compilou, executou TypeScript e gerou as rotas estáticas `/`, `/calculadoras`, `/clima`, `/mercado`, `/offline`, `/manifest.webmanifest`, `/comunidade` e `/conta`. |
| Testes de calculadoras/PWA em desenvolvimento | 3 PASS / 2 FAIL | `npm run test:e2e:lab -- tests/e2e/pwa-calculadoras.spec.ts` — modo dev não foi usado para decidir o veredicto. |
| Testes de calculadoras/PWA no build de produção | 3 PASS / 2 FAIL | `npm run test:e2e -- tests/e2e/pwa-calculadoras.spec.ts`. |
| Mercado com fixtures e clima com mocks | 8 PASS / 2 FAIL | `npm run test:e2e -- tests/e2e/mercado-precos-fixture.spec.ts tests/e2e/clima-dashboard.spec.ts --grep 'carrega preços via mesma origem|exibe fonte, data|renderização completa|navegação e usabilidade|trata campos nulos|trata HTTP 429|trata HTTP 500|offline com cache local|offline sem cache|cache com validade expirada'`. |

## Resultados funcionais

### Aprovados

- O build de produção e o typecheck incluído nele passaram.
- Navegação pública com Início, Clima, Mercado e Calculadoras foi renderizada no browser.
- As cinco calculadoras funcionaram conectadas: conversões de sacas, áreas, frete, custo por hectare/break-even e conversor geral.
- Os cenários simulados de clima passaram para renderização desktop, viewport móvel, campos nulos, respostas 429/500 e contingência offline com cache existente/ausente.
- O catálogo de mercado com fixture passou na renderização desktop e mobile, incluindo fonte, data e unidade.
- A regra testada do Service Worker de não armazenar `/api/` passou.
- Os arquivos de manifest, ícones e `public/sw.js` existem no checkout; isso, isoladamente, não comprova instalação funcional.

### Reprovados — problemas observados

| Classificação | Observação | Consequência |
|---|---|---|
| **BLOQUEADOR** | Em build de produção, `navigator.serviceWorker.getRegistration()` retornou `null` após carregar a página. | O fluxo de registro/ativação do Service Worker não está comprovado; o offline/PWA não pode ser considerado pronto para publicação. A causa exata não foi determinada nesta fase. |
| **BLOQUEADOR** | No cenário offline, após preencher `350` sacas, a tela manteve o resultado inicial de `6.000 kg`; o esperado era `21.000 kg`. O campo mostrava o novo valor, mas o resultado não acompanhou. | A calculadora de sacas não se manteve interativa após a navegação offline testada. O teste falhou tanto em dev como em produção. |
| **NÃO BLOQUEADOR para o uso online; pendência P1** | O teste de preço de mercado com fixture não encontrou o estado “Exibindo dado salvo” após reload offline. | Fallback offline de preços não passou. O escopo principal de consulta online com fixture passou, mas a contingência offline deve ser esclarecida antes de ser anunciada. |
| **PENDENTE DE CONFIRMAÇÃO; tratar como P1** | O teste de cache climático expirado esperava `#banner-dados-desatualizados`, mas a página mostrou “Sem conexão ... não há dados salvos”. | A fixture expirada não foi reconhecida nesse fluxo. Pode haver incompatibilidade de chave/formato da fixture ou defeito no carregamento do cache; a evidência não separa essas hipóteses. Não afirmar que previsão expirada é mostrada como atual. |

## Testes bloqueados por configuração/autorização

- **BCB/PTAX e séries SGS reais — BLOQUEADO:** foram testados apenas fluxos com fixtures. A API não foi iniciada e não houve consulta aos serviços externos.
- **IBGE/SIDRA real, inclusive a referência anual de cacau e pimenta-do-reino — BLOQUEADO:** chamadas do browser seriam encaminhadas ao backend local, propositalmente ausente na porta-alvo sem serviço. Não há evidência de valores reais, datas retornadas ou resposta da categoria de pimenta nesta execução.
- **Clima real — BLOQUEADO:** o backend/provedor não foi iniciado; cenários climáticos usaram somente dados simulados, sem chave WeatherAPI.
- **Instalação efetiva do PWA em dispositivo — PENDENTE:** Chromium headless não validou prompt/fluxo de instalação em Android, iOS ou desktop. A falha de registro do Service Worker já impede aprovar a experiência offline.
- **Console/rede com backend funcional — PARCIAL:** o Next reportou recusas esperadas em `127.0.0.1:8001/api/v1/public/agro/config` porque a API foi deliberadamente mantida desligada. Não houve diagnóstico de logs da API nem de respostas upstream reais.

## Problemas que impedem publicação

1. Corrigir e demonstrar registro/ativação do Service Worker no build de produção.
2. Fazer a calculadora de sacas recalcular valores quando a aplicação é recarregada em offline.
3. Reexecutar a suíte PWA em Chromium após as correções, incluindo instalação do SW, pré-cache, rota offline e cálculo.

## Pendências importantes, sem evidência suficiente para ampliar o bloqueio

- Validar o contrato/chave do cache climático expirado e confirmar que dados além da validade não são apresentados sem aviso.
- Confirmar a experiência offline de preço de mercado ou ajustar a expectativa do teste à política de cache vigente.
- Com autorização específica e ambiente isolado comprovado, iniciar backend local sem herdar os destinos do `.env.local`; então validar datas/valores e atribuição de BCB e IBGE/SIDRA, além de respostas de clima simuladas através da API.
- Testar instalação real em pelo menos um navegador/dispositivo móvel suportado.

## Resumo final

Build estático e uso conectado das calculadoras passaram. Os principais fluxos de layout responsivo e mocks de clima/mercado passaram. Porém, o teste de produção confirmou falhas de Service Worker e de recálculo offline, requisitos relevantes para este PWA. As integrações reais permaneceram sem validação por isolamento e autorização. **Veredicto final: NO-GO. Nenhuma correção foi feita; aguardar autorização antes de qualquer alteração.**
