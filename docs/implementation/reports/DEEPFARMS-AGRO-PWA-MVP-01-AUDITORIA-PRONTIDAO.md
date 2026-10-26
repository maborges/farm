# DEEPFARMS-AGRO-PWA-MVP-01 — Auditoria de prontidão para lançamento

Data: 25/10/2026  
Modalidade: análise estática do repositório e revisão de termos/fontes oficiais.  
Escopo: PWA gratuito de consulta para produtores, em `apps/agro`.  
Resultado: não foram executados testes, builds, chamadas a serviços, migrations ou operações em bancos. Nenhum código, configuração ou infraestrutura foi alterado nesta auditoria; este relatório é o único arquivo criado.

## 1. Resumo executivo

**Recomendação: NO-GO para publicar agora o MVP anunciado com clima e indicadores/preços atuais.** O código de interface existe e há cobertura automatizada preparada, mas não foi obtida evidência de execução real. Além disso, no código inspecionado, a seleção padrão de clima é `WEATHERAPI` enquanto o provedor está desabilitado e sem chave; o uso comercial do Open-Meteo gratuito não é permitido pelos termos atuais; os endpoints DERAL exigem sessão SQLAlchemy e sincronizam um snapshot no banco; e a configuração de produção do frontend não define destino de API por padrão. Não há prova nesta auditoria de domínio, HTTPS, integração pública entre landing e Agro ou operação do runtime do API.

O caminho curto é manter o produto pequeno: **calculadoras locais + catálogo institucional com links e dados BCB/IBGE onde a operação e atribuição forem confirmadas**, e decidir se o clima e os preços atuais ficam no primeiro corte. Se ambos forem parte obrigatória do MVP, é necessário primeiro resolver a licença/configuração do provedor climático e comprovar o backend necessário para as rotas escolhidas. Isso não exige, por si só, clean install do banco completo, Docker, S3 ou MinIO. Para a tela de preços DERAL atualmente implementada, porém, existe dependência concreta de PostgreSQL no backend público.

Cadastro, conta autenticada e comunidade/chat não são necessários para a consulta pública descrita e ficam fora do escopo do MVP. A existência de código de autenticação no app não prova que cadastro deva ser condição de acesso.

## 2. Localização e arquitetura atual

| Área | Evidência | Leitura para o MVP |
|---|---|---|
| Aplicação | `apps/agro/` | Aplicação Next.js App Router, Next 16.1.6, React 19 e TypeScript 5.9. É um pacote frontend separado dos apps `web` e `campo`. |
| Rotas | `apps/agro/src/app/` | `/`, `/clima`, `/mercado`, `/calculadoras`, `/comunidade`, `/conta` e `/offline`. A home anuncia uso gratuito e sem cadastro obrigatório. |
| Serviço | `apps/agro/next.config.ts` | Reescreve `/api/v1/*` para `AGRO_API_INTERNAL_ORIGIN`; em desenvolvimento usa `127.0.0.1:8000`, mas em produção sem variável não cria rewrite. `NEXT_PUBLIC_AGRO_API_ORIGIN` também é aceito pelo cliente. |
| Backend | `services/api/public_clima`, `services/api/public_mercado` | Fachadas públicas dentro do monólito FastAPI, com adaptadores, cache, limites e integrações oficiais/externas. Não é um backend Agro totalmente independente. |
| Persistência local | `apps/agro/src/lib/**` | Preferências e snapshots de consulta usam `localStorage`; calculadoras executam localmente. Não se observou requisito de PostgreSQL/Redis no pacote frontend. |
| PWA | `apps/agro/src/app/manifest.ts`, `apps/agro/public/sw.js` | Manifest e Service Worker próprios. A aplicação `apps/campo` é outro produto, com arquitetura operacional/offline própria; sua documentação não comprova offline do Agro. |
| Site/landing | `apps/web/src/app/page.tsx` | Landing pública principal divulga o SaaS e PWA de Campo. A inspeção estática não encontrou um CTA/link direto para `apps/agro` na landing principal. Relatório arquitetural anterior previa `agro.deepfarms.com.br` e CTA/QR, sem comprovação operacional atual. |

O isolamento é razoável no frontend: pacote, rotas, manifest, cache e porta de desenvolvimento próprios. O isolamento de runtime é parcial: a aplicação consome o FastAPI compartilhado e inclui rotas de conta/heartbeat. Isso não obriga login no fluxo público, mas a origem/destino e a implantação do backend precisam ser definidas.

## 3. Inventário de funcionalidades

Classificação baseada no código e na existência de testes; “implementada” não significa homologada em navegador/dispositivo nesta auditoria.

| Funcionalidade | Classificação | Evidência e limite |
|---|---|---|
| Home e navegação | Implementada; validação visual externa pendente | `apps/agro/src/app/page.tsx`, header e bottom navigation apresentam as áreas principais. Nenhum teste/build foi executado nesta fase. |
| Calculadoras e conversões | Implementada; cobertura automatizada existente, execução pendente | `src/lib/calculadoras` e componentes locais. Não dependem de API, banco ou autenticação para cálculo. Há suites Vitest/E2E existentes, mas seus resultados não foram reexecutados. |
| Clima — interface, localidade e estados de falha | Implementada parcialmente | Página, seletor, previsões e armazenamento local existem. Testes E2E cobrem estados mockados, cache/localidade e stale data. |
| Clima — dados ao vivo | Dependente de correção/configuração e validação externa | `services/api/core/config.py` define `clima_active_provider="WEATHERAPI"`, `weatherapi_enabled=False` e chave vazia por padrão; Open-Meteo e OpenWeather também começam sem licença/habilitação. Não há fonte operacional provada. |
| Mercado — catálogo de referências e links oficiais | Implementada | Catálogo frontend possui fallback estático; a página de Mercado apresenta política de não exibir cotações sem homologação/redistribuição explícita. |
| Mercado — câmbio PTAX, macro e IBGE/SIDRA | Implementada parcialmente; dependente de serviços externos | Clientes e componentes existem, com cache local e testes com fixtures. O API agrega os dados BCB/IBGE; conectividade, limites, disponibilidade e tratamento em dispositivos reais não foram testados. O BCB publica dados abertos sob licença que permite uso/reutilização conforme seu programa; confirmar metadados/licença do conjunto efetivamente consumido e atribuição apresentada. |
| Mercado — preços DERAL ativos | Implementada parcialmente; backend e publicação bloqueadores | Os endpoints públicos de catálogo/preços dependem de `get_session` e executam `sincronizar_snapshot_ativo(session)` (`services/api/public_mercado/router.py`, linhas 244–307). Um JSON versionado no repositório não substitui automaticamente essa necessidade operacional. Uso/distribuição dos dados extraídos deve seguir autorização/atribuição da fonte. |
| Gráficos/indicadores visuais | Implementada parcialmente; validação externa pendente | Cards e gráficos SVG próprios existem para PTAX/mercado. Fixtures cobrem alguns cenários, mas legibilidade, escalas, unidades e responsividade não foram avaliadas em aparelhos reais. |
| Responsividade | Implementada parcialmente | Há classes responsivas `sm`/`md` e specs de viewport; não houve validação manual em Android/iOS, telas pequenas, fonte ampliada ou conexão lenta. |
| Manifest/ícones/instalação | Implementada parcialmente | Manifest com standalone, scope `/`, ícones PNG 192/512 e metadados Apple; `InstallPrompt` trata `beforeinstallprompt` e mostra instrução de instalação manual no iOS. Instalação real e critérios de cada navegador não foram comprovados nesta rodada. |
| Service Worker/cache offline | Implementada parcialmente; defeito de resiliência a validar | `public/sw.js` pré-cacheia shell e rotas com `cache.addAll` (falha de um item pode rejeitar instalação inteira), usa network-first para navegação e ignora `/api/`. Os dados de consulta são salvos separadamente em localStorage; respostas de API não são cacheadas pelo SW. Requer teste real após visita online, cache vencido/ausente e atualização. |
| Offline | Parcial e condicionado a dados previamente carregados | Calculadoras continuam locais; páginas e alguns últimos snapshots podem ser exibidos. Não há outbox, mutações offline nem sincronização do Agro. Esses recursos de `apps/campo` não devem ser prometidos para `apps/agro`. |
| Integração da landing ao Agro | Não implementada / não comprovada | A landing em `apps/web` não apresenta CTA/QR encontrado para Agro. O domínio `agro.deepfarms.com.br` aparece em relatórios/configuração de CORS, mas isso não comprova DNS, certificado, rota ou deploy. |
| Cadastro/autenticação | Implementado parcialmente; fora do MVP de consulta | Existem `/conta`, cliente de auth e heartbeat global no layout. Não é requisito para clima/catálogo/calculadoras anônimos; pode ser excluído da promessa inicial. Não foi feita auditoria completa do fluxo autenticado nesta tarefa. |
| Comunidade/chat/mensagens | Não implementada | A página e card são marcados “Em Breve”/planejamento. Explicitamente fora do MVP atual. |

### Testes já presentes no repositório — não executados nesta auditoria

Há testes unitários de calculadoras, clima, PTAX, mercado, IBGE, macro e stores locais; specs Playwright cobrem instalabilidade/cache, cálculos, estados de clima, fixtures de preços e PTAX e alguns cenários offline. Esses arquivos mostram intenção de cobertura, não resultado de execução. `playwright.lab.config.ts` restringe a execução planejada a PWA `127.0.0.1:3005` e API `127.0.0.1:8001`, limpa variáveis de segredos e bloqueia egress do Chromium; não foi invocado.

## 4. Dependências e necessidade real

| Dependência | Necessidade real | Decisão de escopo |
|---|---|---|
| PostgreSQL | Não é requisito do frontend, das calculadoras nem do catálogo estático. É dependência explícita atual dos endpoints DERAL públicos por sessão e sincronização de snapshot no banco. | Evitar atrelar MVP a instalação limpa do schema completo. Se DERAL dinâmico for obrigatório, documentar/provisionar somente backend e persistência compatíveis. Não executar nada nesta auditoria. |
| Redis | O cache público de clima/PTAX/macro/SIDRA usa Redis e possui fallback single-worker configurado como `true` em `services/api/core/config.py`. Isso sugere que Redis pode ser dispensável para operação unitária com fallback habilitado, mas não prova segurança de escala, limites compartilhados ou comportamento do runtime. | Não tratar Redis como pré-requisito universal. Confirmar topologia, limites e cache antes de tráfego público; Redis compartilhado será relevante para múltiplos workers/quotas consistentes. |
| FastAPI | Necessário para os caminhos atualmente servidos pelo API: clima e indicadores agregados; preços DERAL usam também PostgreSQL. | O produto mínimo de calculadoras + links institucionais pode funcionar sem API; produto com dados dinâmicos atuais depende de uma origem servida e monitorada. |
| Autenticação | Não é necessária para consulta anônima, cálculos ou navegação pública. O layout instala heartbeat e o bundle contém recursos de conta. | Não exigir cadastro/login para o lançamento público. Cadastro e sessão ficam fora do MVP definido pelo usuário. |
| Provedor climático | Necessário para previsão ao vivo. O padrão atual aponta para WeatherAPI, mas está desabilitado/sem chave. Open-Meteo gratuito não pode ser presumido permitido: termos limitam o uso gratuito a não comercial e incluem produto comercial/atividade promocional como uso comercial. WeatherAPI permite uso em apps online/mobile sob seus termos, exige crédito para usuário free, proíbe exposição da chave no cliente e impõe limites de plano/cache e disclaimer. | Obter validação comercial/termos e credencial adequada, configurar no servidor e comprovar política de cache/atribuição/disclaimer antes da publicação com clima. [Termos Open-Meteo](https://open-meteo.com/en/terms), [Termos WeatherAPI](https://www.weatherapi.com/terms). |
| BCB/IBGE | São fontes públicas integradas pelo backend; o BCB publica datasets abertos com reutilização permitida conforme metadados/licença do dataset. | Validar conjunto, atribuição, frequência, limites e continuidade; manter indicação de fonte/data e fallback informativo. Referência: [Dados Abertos BCB](https://www.bcb.gov.br/acessoinformacao/dadosabertos) e [FAQ do Portal](https://dadosabertos.bcb.gov.br/pages/perguntas-frequentes). |
| Fontes DERAL/CONAB/CEPEA/B3 | Catálogo de links pode funcionar como diretório. Valores, documentos e redistribuição não têm todos o mesmo regime de direitos. | No MVP curto, preferir links a fontes primárias até haver autorização/contrato para replicar dados. Não exibir número sem proveniência, data, unidade e direito de uso confirmados. |

## 5. Bloqueadores reais para lançamento

### P0 — impede lançar a promessa atual de clima + dados dinâmicos

1. **Clima não está operacional por configuração padrão demonstrada.** Provedor selecionado desabilitado e credencial ausente. Open-Meteo gratuito é não comercial; os termos classificam produtos comerciais e atividades promocionais como uso comercial. Como o Agro promove a marca/serviço DeepFarms, não se deve presumir uso não comercial. É necessário contrato/plano comercial válido ou outra fonte com licença compatível, atribuição, segredo somente no servidor, limites e texto de incerteza apropriado.
2. **Rota de API do frontend sem alvo de produção comprovado.** Sem `AGRO_API_INTERNAL_ORIGIN`, o rewrite de produção é vazio; a URL pública de API, DNS/TLS/proxy e CORS não foram comprovados. `/mercado` também faz chamada server-side direta ao origin interno opcional.
3. **Preços DERAL exigem PostgreSQL no backend atual.** As rotas públicas passam por `get_session` e `sincronizar_snapshot_ativo`; portanto o banco não pode ser descartado se o MVP mantiver esse fluxo sem alteração futura. Nenhuma instância ou configuração operacional para o MVP foi validada nesta auditoria.
4. **Distribuição e acesso público não comprovados.** Não há evidência verificada de domínio Agro, HTTPS, processo/hosting próprio, monitoramento, orçamento ou rollback. A landing principal não direciona o produtor ao app na inspeção estática.
5. **Sem prova de runtime.** Nenhum teste, build, serviço ou dispositivo foi executado nesta tarefa. O código e testes existentes não substituem smoke test de publicação.

Se o primeiro corte for reduzido a calculadoras e links/catálogos institucionais sem dados climáticos ou cotações dinâmicas, os itens 1 e 3 deixam de bloquear essa versão reduzida. Os itens 2, 4 e 5 continuam necessários para publicar um aplicativo utilizável e acessível.

### P1 — importante no primeiro ciclo pós-publicação controlada

- Validar em Android/Chrome e iOS/Safari instalação, abertura standalone, atualização do SW, quota/evicção de cache e cenário sem conexão.
- Medir responsividade em aparelhos de baixo/médio porte, acessibilidade, contraste, navegação por teclado/leitor de tela e desempenho em rede lenta.
- Exercitar timeouts, 429, erros parciais, resposta antiga e observabilidade de frescor dos dados; mostrar claramente fonte e horário da atualização.
- Revisar aviso de que previsões são probabilísticas e não devem ser base única para decisões de segurança; respeitar as exigências aplicáveis do provedor escolhido.
- Validar privacidade: localização consultada vai ao backend; publicar política/aviso de tratamento adequado e minimizar retenção/logs de coordenadas.
- Verificar se a inicialização do heartbeat global, embora suspenda após 401/403, gera chamada anônima desnecessária em cada sessão pública; não é bloqueador se não impedir o uso.

### P2 — futuro e fora do MVP

- Cadastro, recuperação de conta e preferências sincronizadas.
- Comunidade, chat, mensagens, moderação, denúncias e notificações.
- Alertas push, tarefas de fundo, sincronização de mutações ou offline-first operacional.
- Preços além das fontes com direito de redistribuição confirmado e funções personalizadas por produtor.

## 6. Plano mínimo de conclusão e esforço

Estimativas são ordem de grandeza para uma pessoa familiarizada com a base; não incluem aprovação de fornecedor, fila operacional ou deploy de produção.

| Prioridade | Atividade | Critério de saída | Complexidade |
|---|---|---|---|
| P0 | Fixar escopo do lançamento: app de consulta sem cadastro/chat; decidir se clima ao vivo e preços dinâmicos são obrigatórios | Lista de telas/indicadores prometidos e política de dados aprovada | Baixa, 0,5–1 dia |
| P0 | Fechar domínio/hosting e origem da API; configurar pipeline/deploy isolado do Agro sem tocar no principal | HTTPS e rota públicas verificadas; destino API explicitamente configurado; rollback e health check | Média, 1–3 dias, depende de DevOps |
| P0 (se clima incluído) | Aprovar provedor comercial, chave, cotas, atribuição, disclaimer e cache | Credencial no servidor; chamada real de ponta a ponta e limites documentados | Média, 1–3 dias técnicos + prazo de contrato |
| P0 (se DERAL atual incluído) | Escolher runtime API/DB mínimo e provar rota de snapshot | API atende catálogo/preço com freshness e sem dependência do clean install completo não aprovada; destino isolado definido | Média/alta, 2–5 dias conforme ambiente existente |
| P0 | Fazer smoke funcional controlado: navegadores, API, indisponibilidade e dados desatualizados | Evidências reproduzíveis sem segredos; nenhum erro crítico em caminhos anunciados | Média, 1–2 dias |
| P0 | Integrar CTA/link de entrada da landing e instruções públicas | Produtor chega ao domínio certo a partir do site e QR/link funciona | Baixa, 0,5–1 dia |
| P1 | Homologar PWA e acessibilidade em dispositivos físicos e rede lenta | Lista de aparelhos/versões, instalação e cenários offline documentados | Média, 2–4 dias |
| P1 | Acompanhar performance, erros, quotas e idade dos dados | Alertas e operação de contingência revisados | Média, 1–2 dias |
| P2 | Avaliar conta, comunidade/chat, notificações e sincronização | Decisão de produto e projeto separados | Alta, descoberta futura |

## 7. Delimitação de produto

**Dentro do MVP gratuito:** acesso anônimo; ferramentas locais de cálculo/conversão já implementadas; catálogo de referências oficiais e indicadores públicos cuja fonte, data, licença e operação estejam confirmadas; clima apenas quando provedor/termos/configuração estiverem aprovados. Exibir fonte, unidade, data de referência, atualização e estado stale/indisponível.

**Fora do MVP:** cadastro obrigatório, criação de tenant, chat, mensagens, comunidade interativa, favoritos sincronizados, alertas push, sincronização de dados de campo e alegação de que todas as telas funcionam sem conexão. Comunidade já aparece como “Em Breve”.

## 8. Veredicto

**NO-GO para publicação ampla do MVP com clima e preços dinâmicos no estado comprovado por esta auditoria.** A experiência de frontend está substancialmente construída; os bloqueios estão em disponibilidade/licenciamento/configuração do dado e na comprovação do runtime e publicação. PostgreSQL/Redis não devem ser tratados como requisito geral do PWA: PostgreSQL é uma dependência real do caminho DERAL atual; Redis tem fallback single-worker configurado, sujeito a confirmação de operação e escala; API é dispensável para calculadoras e catálogo estático, mas necessária para dados dinâmicos.

Uma versão estritamente reduzida — calculadoras locais e links institucionais, sem prometer clima ou preços ao vivo — pode receber **GO COM RESSALVAS** após confirmar domínio/HTTPS, ligação da landing, smoke test do build publicado e aviso de privacidade/fonte. Isso não equivale ao MVP anunciado completo.

## 9. Limites da auditoria

- Não foram executados testes unitários, E2E, typecheck, build ou chamadas a provedores.
- Não foram iniciados serviços ou consultados bancos, Redis, AWS/RDS ou produção.
- Não foi verificada uma publicação real, domínio, certificado, DNS, capacidade ou configuração efetiva do ambiente.
- Classificações refletem código/configurações versionadas e arquivos de teste, não a resposta de um ambiente ativo.
- As condições dos fornecedores podem mudar; os links acima foram consultados em 25/10/2026. A decisão jurídica/comercial final cabe ao responsável pelo produto.
