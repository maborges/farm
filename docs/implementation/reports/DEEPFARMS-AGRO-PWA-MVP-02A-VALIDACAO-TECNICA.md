# DEEPFARMS-AGRO-PWA-MVP-02A — Validação técnica do MVP

Data: 25/10/2026  
Escopo: validação local e estática de apps/agro, sem alterações de código/configuração, sem bancos ou serviços persistentes, sem chamadas a APIs externas e sem credenciais.  
Aplicativos apps/web e apps/campo: não alterados.

## 1. Resumo executivo

**Veredicto: NO-GO para publicar o MVP completo até confirmar configuração e runtime dos dados ao vivo; GO COM RESSALVAS para a qualidade estática do frontend.** A validação local passou: TypeScript, ESLint, 155 testes unitários e build de produção. O build prerenderizou 10 rotas. Nenhum teste de navegador, API ao vivo ou dispositivo foi executado.

Há um caminho simples e sem custo de licença inicial para avaliar clima: o plano gratuito da WeatherAPI lista uso comercial, até 100 mil chamadas mensais e previsão de 3 dias, com uptime publicado de 95,5%; os termos permitem uso em uma aplicação online/móvel, exigem crédito, e a chave deve permanecer confidencial. A implementação atual, no entanto, seleciona WeatherAPI por padrão enquanto a desabilita e deixa a chave vazia. Portanto, clima ao vivo não foi validado. Open-Meteo gratuito não é alternativa comercial equivalente: seus termos limitam o plano livre a uso não comercial; o plano pago licencia uso comercial. [Termos WeatherAPI](https://www.weatherapi.com/terms), [preços WeatherAPI](https://www.weatherapi.com/pricing), [termos Open-Meteo](https://open-meteo.com/en/terms), [planos Open-Meteo](https://open-meteo.com/en/pricing).

O mercado já permite entregar PTAX/indicadores BCB e séries estatísticas IBGE/SIDRA via os clientes e endpoints existentes, sujeito ao backend FastAPI e à confirmação operacional de limites, atualização e atribuição. O fluxo de preços DERAL é distinto: os endpoints atuais dependem de sessão PostgreSQL e sincronização do snapshot. Para evitar depender do clean install do DeepFarms, o corte inicial mais curto é não prometer preços DERAL dinâmicos até que essa dependência de runtime esteja resolvida; manter catálogo/links institucionais e dados BCB/IBGE no MVP se o ambiente API existente for aprovado.

## 2. Evidências de validação executada

Dependências locais estavam disponíveis em apps/agro/node_modules/.bin; nenhuma instalação foi feita.

| Verificação | Comando | Resultado |
|---|---|---|
| TypeScript | node_modules/.bin/tsc --noEmit (com apps/agro como diretório de trabalho) | PASS, exit code 0, sem saída de erro. |
| ESLint | node_modules/.bin/eslint src --ext .ts,.tsx | PASS, exit code 0, sem avisos/erros reportados. |
| Unitários Vitest | node_modules/.bin/vitest run | PASS: 11 arquivos, 155 testes. Duração reportada: 3,99 s. |
| Build de produção | node_modules/.bin/next build --webpack | PASS: Next.js 16.1.6; compilação webpack, TypeScript, coleta de dados, 10 páginas estáticas, traces concluídos. |
| Playwright/E2E | Não executado | A configuração iniciaria next start ou next dev; esta fase não autorizou iniciar serviços. A configuração E2E de laboratório também pressupõe API em loopback, ainda não validada nesta fase. |
| Provedores/fontes ao vivo | Não executado | Não houve chamadas externas, uso de chaves ou tráfego faturável. |

O build criou/atualizou artefatos locais de build sob apps/agro/.next; não alterou fontes ou configurações intencionalmente. O app já aparecia como diretório não rastreado antes da execução. Nenhuma tentativa de limpar artefatos foi feita.

## 3. Arquitetura e escopo técnico

- apps/agro é um frontend Next.js App Router independente, Next 16.1.6, React 19 e TypeScript 5.9, com scripts próprios typecheck, lint, test, build e Playwright.
- Rotas construídas: /, /calculadoras, /clima, /comunidade, /conta, /manifest.webmanifest, /mercado e /offline (mais /_not-found). Todas as 10 páginas estáticas apareceram no build.
- next.config.ts reescreve /api/v1/* para AGRO_API_INTERNAL_ORIGIN. Em desenvolvimento usa http://127.0.0.1:8000; em produção, se a variável estiver vazia, não define rewrite. O cliente também aceita NEXT_PUBLIC_AGRO_API_ORIGIN. Destino de produção precisa ser definido explicitamente.
- O mercado no server component tenta carregar /api/v1/public/mercado/catalogo, usa revalidação de 300 segundos e retorna PRODUTOS_CATALOGO estático em falha/ausência de origin. O build bem-sucedido não comprovou endpoint vivo.
- Calculadoras executam matemática no cliente e não exigem API, PostgreSQL, Redis ou auth.
- O frontend usa localStorage para localidade e último dado de clima, moeda, macro, estatísticas IBGE e preços. Stores versionadas e parsing têm testes unitários. São caches locais do navegador, sujeitos a limpeza/evicção; não são sincronização de dados.

## 4. Inventário das funcionalidades

| Funcionalidade | Estado após validação | Evidência / o que continua sem validação |
|---|---|---|
| Navegação, home e layout | Implementados; compilação/build aprovados | Build das rotas concluído. Não houve interação visual de navegador ou avaliação de acessibilidade. |
| Calculadoras e conversões | Implementadas; unitários aprovados | Cobertura testada inclui domínio das calculadoras/conversões. E2E de fluxo e resultado em navegador não executado. |
| Clima: parsing, localidade, cache e estados | Implementada em parte; unitários aprovados | clima-localidade e clima-previsao estão entre as suites aprovadas; E2E mocks cobre dashboard/localidade. Provider e dado ao vivo não testados. |
| Clima ao vivo | Não pronto por configuração comprovada | services/api/core/config.py defaults: clima_active_provider="WEATHERAPI", weatherapi_enabled=False, weatherapi_api_key="", weatherapi_max_forecast_days=3; Open-Meteo e OpenWeather começam sem licença habilitada e sem chave. Config dinâmica pode sobrepor defaults em ambiente runtime, mas não foi lida. |
| PTAX / BCB | Cliente, componentes e parsing implementados | Testes unitários aprovados; E2E com fixtures existe, mas não executado. Serviços externos e backend não acessados. |
| Indicadores macro BCB/SGS | Implementados | Backend possui endpoint público macro e cache com fallback single-worker configurado; necessidade operacional do API, freshness e limites ainda precisa ser verificada. |
| IBGE/SIDRA | Catálogo, localidade, séries e armazenamento local implementados | Testes unitários aprovados. Backend consulta SIDRA/IBGE; execução em produção e atualidade das tabelas/variáveis não testadas. O BCB trata dados abertos sob licença aberta, mas atribuição e metadados devem ser conferidos por dataset; [Dados Abertos do BCB](https://www.bcb.gov.br/acessoinformacao/dadosabertos). |
| Catálogo de mercado | Fallback estático implementado | Prerender/build passou com fallback. Catálogo pode conter destinos institucionais; cada link e status externo não foi aberto/testado nesta rodada. |
| Preços DERAL dinâmicos | Implementados parcialmente; backend exige PostgreSQL | services/api/public_mercado/router.py: endpoints /catalogo, /precos e /precos/{commodity_id} recebem AsyncSession = Depends(get_session) e chamam sincronizar_snapshot_ativo(session). Não se executou SQL nem se testou a fonte. |
| Gráficos | Presentes nos cards de mercado | Parser/dados passam unitários; fixtures E2E existentes. Escalas/unidades, tamanhos de tela e comportamento com séries vazias não foram verificados em navegador real. |
| Manifest/instalação | Implementados parcialmente | Manifest inclui standalone, scope /, ícones PNG 192/512 e metadata Apple; InstallPrompt trata Chromium beforeinstallprompt e instrução manual para iOS. Não foi testada instalação em dispositivo. |
| Service Worker/offline | Implementado parcialmente | Cache de app shell com cache.addAll, navegação network-first e bypass de /api/; specs E2E existentes esperam registro/ativação e navegação offline após cache. E2E não executado. APIs não são guardadas pelo SW; o último dado salvo depende do localStorage e de visita online anterior. Sem outbox ou sync offline. |
| Responsividade | Implementada visualmente, não homologada | Classes responsivas e Playwright fixtures/specs existem; sem execução E2E ou aparelho físico. |
| Cadastro, conta, comunidade | Código existente, não necessário ao MVP anônimo | /conta, cliente de auth, heartbeat global e comunidade “Em Breve” permanecem no layout/nav. Não foram implementados ou alterados nesta fase. A conta não deve ser exigida no fluxo público; recomenda-se deixá-la fora da navegação/promessa do MVP em fase autorizada, mantendo os componentes existentes isolados. |

As 155 aprovações Vitest cobrem apenas as suites unitárias listadas no vitest.config.ts; não equivalem a 155 testes de navegador nem a validação do FastAPI.

## 5. Provedores climáticos e recomendação

| Provedor | Estado no código/configuração | Termos/custo observados | Recomendação |
|---|---|---|---|
| WeatherAPI | Adapter existe. Defaults selecionam WEATHERAPI, mas weatherapi_enabled é falso, chave vazia, máximo de forecast 3 dias e quota mensal configurada localmente em 100.000. | Pricing oficial lista plano Free $0, uso comercial, 100 mil calls/mês, 3 dias e uptime publicado de 95,5%; termos permitem aplicação online/mobile, exigem crédito e chave protegida. A quota cessa entrega no excesso segundo FAQ dos termos/preços. [Pricing](https://www.weatherapi.com/pricing), [API Terms](https://www.weatherapi.com/terms). | **Alternativa mais simples para piloto** caso 3 dias e 100 mil chamadas/mês atendam: custo de licença listado como zero, mas exigir chave no servidor, atribuição/link, disclaimer de previsão probabilística, quota/alerta e prova de que parâmetros/agricultura não dependem de produtos premium. Não configurar ou adquirir nesta fase. |
| Open-Meteo | Adapter existe, mas open_meteo_licensed=False e open_meteo_allow_unlicensed_public=False por default. | Free/open-access é não comercial, sem garantia de disponibilidade; planos comerciais fornecem licença comercial, endpoint e chave. CC BY 4.0 exige atribuição. [Terms](https://open-meteo.com/en/terms), [Pricing](https://open-meteo.com/en/pricing). | Não usar endpoint gratuito para este app promocional comercial; comparar plano pago apenas se WeatherAPI não cobrir necessidades. |
| OpenWeather | Adapter existe; defaults sem chave, openweather_licensed=False, openweather_allow_unlicensed_public=False. | Uso depende de conta/plano/licença e quota do produto escolhido; nenhuma credencial/preço contratado foi inspecionado. | Não recomendar para o corte mínimo sem cotação/licença aprovada. |

Não contratar ou configurar credenciais foi parte explícita desta fase. A recomendação não substitui revisão jurídica/contratual, nem valida disponibilidade real da fonte.

## 6. Mercado: conteúdo possível sem clean install

1. **Calculadoras/conversões:** 100% cliente; sem backend.
2. **Catálogo institucional:** pode ser servido pelo fallback frontend estático já observado; não deve apresentar cotação atual quando só houver link.
3. **PTAX e BCB/SGS:** os clientes chamam rotas públicas do FastAPI. O public_mercado/router.py aplica cache e fallback de worker único (ptax_single_worker_fallback=True); essas rotas não demonstram dependência direta de get_session no caminho de consulta. Precisam da API e acesso externo à fonte, mas não implicam clean install do schema completo pelo frontend.
4. **IBGE/SIDRA:** clientes chamam endpoints públicos agregadores do backend; rotas têm cache local/Redis. Testes unitários atuais comprovam parsing/store, não a execução ao vivo. O portal BCB descreve datasets abertos sob licença que permite reutilização, mas cada conjunto precisa de metadados, atribuição e frequência registrados. O mesmo cuidado aplica-se a cada tabela SIDRA usada.
5. **DERAL/CONAB preços:** frontend oferece parser/cache e fixture tests. No backend, DERAL catálogo/preços exigem SQLAlchemy session e sincronizam snapshot ativo com a base. São excluídos do caminho curto até que o runtime API/PostgreSQL e os direitos de redistribuição da planilha estejam aprovados. Não usar os arquivos de snapshot no repositório como prova de atualização/licença.

**Não foi executado clean install, migration, consulta SQL ou chamada a fonte externa.** O laboratório PostgreSQL/Redis e os relatórios de clean install anteriores não são pré-requisito geral para a UI do MVP; também não autorizam acessar qualquer database nesta tarefa.

## 7. Anonimato e componentes fora do fluxo principal

- A home declara “Sem cadastro obrigatório”; funcionalidades públicas não precisam de identidade.
- layout.tsx monta SessionHeartbeat em todas as páginas. O componente tenta enviar heartbeat depois de interação/visibilidade e suspende quando a resposta falha, incluindo sessão anônima. Isso não parece bloquear a navegação, mas produz tentativa de endpoint de auth desnecessária ao usuário anônimo; em fase autorizada, manter o arquivo/código e isolar sua montagem somente quando uma sessão Agro autenticada estiver ativa, ou desativar a chamada no fluxo anônimo sem remover a implementação.
- Header/bottom navigation continuam expondo Conta e Comunidade; a segunda é explicitamente “Em Breve”. Para o MVP, o primeiro é uma distração/rota fora de escopo e o segundo uma promessa não entregue. Recomenda-se esconder os links da navegação pública, sem excluir módulos, e manter URL direta com estado claro, em alteração separada autorizada.
- Não foi encontrado chat/mensageria funcional. Não implementar cadastro, chat ou comunidade na fase 02A.

## 8. Plano mínimo de implementação

### P0 — bloqueia lançamento do MVP de três funcionalidades

| Correção/prova | Critério verificável | Complexidade |
|---|---|---|
| Configurar destino público de API e validar API/HTTPS sem apontar para ambiente comercial não autorizado | AGRO_API_INTERNAL_ORIGIN explícito no deploy isolado; smoke de clima e rotas BCB/IBGE com resposta controlada | Média, 1–2 dias além da fila de infra |
| Ativar WeatherAPI somente após aprovação e armazenar chave no servidor | Ver previsão real; atribuição/link e disclaimer presentes; 3 dias e orçamento/quota validados | Baixa/média, 0,5–1 dia técnico + decisão/credencial |
| Definir corte do mercado: BCB/IBGE live; DERAL dinâmico adiado sem runtime PostgreSQL aprovado | Telas identificam fonte, unidade, período/data, estado stale e link primário; sem preço sem prova | Baixa/média, 0,5–2 dias conforme ajustes |
| Smoke de lançamento do frontend já compilado | Fluxos home → clima → mercado → calculadoras sem cadastro; erros de API/fonte não quebram navegação | Média, 0,5–1 dia; requer ambiente efêmero autorizado |
| Aprovar URL, HTTPS e entrada pela landing | Domínio acessível, certificado válido, CTA da landing/QR aponta para app | Baixa/média, 0,5–2 dias conforme infraestrutura |

### P1 — logo após piloto controlado

- Executar Playwright em ambiente exclusivamente isolado e mockado; testes atuais incluem auth fora do MVP, então selecionar casos públicos e ajustar configuração em tarefa aprovada.
- Instalação, cache/offline, atualização do SW, tamanho de tela, leitor de tela e rede lenta em Android/iOS físicos.
- Monitorar chamadas/cotas do provider, erro/latência do API e idade das séries BCB/IBGE.
- Política/aviso de privacidade e retenção de localidade/logs.
- Verificar comportamento sem Redis: fallback single-worker cobre cache/limites? Confirmar que implantação inicial usa um worker e não promete cache distribuído. Se múltiplos workers, Redis compartilhado é necessário para coerência dos mecanismos configurados.

### P2 — evolução futura

- Autenticação opcional, preferências sincronizadas, cadastro.
- Comunidade, chat, mensagens, moderação e notificações.
- DERAL dinâmico após solução de persistência mínima e licenças.
- Push e sincronização de mutações offline; não estão implementados no Agro.

Estimativa do P0 técnico: **3–7 pessoa-dias**, sem prazo de contratação/aprovação de provider ou janela de publicação. Parte de infraestrutura (domínio, origin, TLS, operação API) pode exceder esse intervalo se ainda não existir.

## 9. Riscos e limites

- O build prerenderizou as páginas e compilou sem API, em parte pela estratégia de fallback do catálogo. Isto prova a geração do frontend, não o sucesso do endpoint público.
- Nenhum servidor Next/API, Postgres ou Redis foi iniciado; nenhum browser automatizado foi aberto.
- Nenhuma chamada WeatherAPI/Open-Meteo/BCB/IBGE/DERAL foi feita; status, latência, limites, CORS, origem, cotas e dados atuais permanecem sem validação.
- O plano gratuito de WeatherAPI declara no pricing uso comercial e 95,5% uptime; não apresenta SLA no nível Free. É adequado apenas como candidato a piloto de baixo volume, não como garantia de disponibilidade.
- Risco de cache offline: cache.addAll(APP_SHELL) é uma etapa de instalação conjunta; recursos /api/ ficam fora do cache SW e dados antigos sobrevivem apenas quando a store local os salvou antes. Não prometer dados dinâmicos offline.
- O build pode ter atualizado artefatos gerados em apps/agro/.next; fontes, configs, apps/web e apps/campo não foram alterados.

## 10. Veredicto

**GO COM RESSALVAS para o frontend em qualidade estática:** TypeScript, lint, unitários e build passaram sem alterações de fonte.

**NO-GO para publicação pública do MVP integral de clima + mercado dinâmico:** faltam configurar e validar o API de destino e o provedor climático, decidir os limites do plano gratuito, aprovar o fluxo de dados ao vivo e provar publicação/uso anônimo. DERAL dinâmico requer PostgreSQL no backend atual e pode ficar fora do primeiro corte; isso não implica que o app precise do clean install completo do DeepFarms. Para economizar, avaliar primeiro WeatherAPI Free (comercial listado, 100k chamadas/mês, 3 dias) e BCB/IBGE, deixando Open-Meteo free e DERAL dinâmico fora até licenças/runtime aprovados.

Não foram realizadas correções. Aguarda-se análise e autorização para a fase MVP-02B.
