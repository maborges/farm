# DEEPFARMS-AGRO-PWA-MVP-02B2A — Preparação da integração climática

Data da auditoria: 26/10/2026  
Modalidade: análise estática, consulta a documentação oficial e testes unitários locais existentes.  
Resultado: nenhuma alteração funcional, credencial, configuração, migration, serviço ou chamada a API externa foi realizada.

## 1. Resumo executivo

O adaptador WeatherAPI e os componentes de clima já existem, e a normalização do payload é compatível com o contrato consumido pelo frontend. A integração está **preparada, mas não está comprovadamente ativada**: os defaults do código não incluem chave e desabilitam WeatherAPI; não lemos arquivos .env nem verificamos o ambiente ativo.

O plano Free é candidato comercial de custo inicial zero segundo os termos específicos da API e a tabela de preços atuais. Oferece 100.000 chamadas/mês, previsão de 3 dias e uptime publicado de 95,5%, sem SLA Free. Os termos permitem uso em uma aplicação online/móvel, exigem crédito WeatherAPI e chave confidencial, além de disclaimer explícito para consumidores finais. [Preços WeatherAPI](https://www.weatherapi.com/pricing), [termos da API WeatherAPI](https://www.weatherapi.com/terms).

**Veredicto: NO-GO para ativar neste estado.** Há bloqueadores concretos: o fluxo do orquestrador não honra a configuração WEATHERAPI_ENABLED ao reconstruir o adapter; o endpoint documenta previsão diária de 7 dias embora o Free entregue 3; o backend conserva resposta stale por até 7 dias e o navegador guarda envelope local sem expurgo, excedendo os limites de cache dos termos para o payload combinado atual + previsão; e o aviso do frontend não contém todo o disclaimer exigido pelo fornecedor. Além disso, embora a rota não dependa de sessão SQLAlchemy nem de autenticação FastAPI, o orquestrador tenta acessar PostgreSQL para configuração/credenciais e o teste existente de “sem PostgreSQL” substitui esse caminho dinâmico.

## 2. Estado real no checkout

### API e configuração

- Rotas públicas: GET /api/v1/public/clima/municipios e GET /api/v1/public/clima/previsao. As funções de rota não declaram dependência de usuário autenticado nem Depends(get_session).
- O catálogo municipal usa dados oficiais locais e não exige PostgreSQL.
- A previsão usa PublicClimaService e DynamicWeatherOrchestrator, compartilhado pelo router.
- Defaults em core/config.py: clima_active_provider=WEATHERAPI; weatherapi_enabled=False; weatherapi_api_key vazio; weatherapi_max_forecast_days=3; weatherapi_timeout_seconds=5; weatherapi_monthly_quota_limit=100000; clima_cache_ttl_seconds=1800; clima_single_worker_fallback=True.
- A chave pode vir da variável de ambiente weatherapi_api_key (Pydantic lê WEATHERAPI_API_KEY) ou do serviço de credenciais criptografadas consultado pelo orquestrador. O adaptador não é chamado pelo navegador: o backend monta a requisição externa. Nenhuma chave foi lida, configurada ou exibida.
- Configuração adicional relacionada: WEATHERAPI_BASE_URL, WEATHERAPI_ENABLED, WEATHERAPI_MAX_FORECAST_DAYS, WEATHERAPI_TIMEOUT_SECONDS, WEATHERAPI_MONTHLY_QUOTA_LIMIT, CLIMA_ACTIVE_PROVIDER, CLIMA_TIMEOUT_SECONDS, CLIMA_CACHE_TTL_SECONDS, CLIMA_GRID_STEP_DEGREES, CLIMA_SINGLE_WORKER_FALLBACK, DATABASE_URL e REDIS_URL. DATABASE_URL e REDIS_URL não foram consultadas em runtime.

### Adaptador e compatibilidade com o frontend

- WeatherAPIAdapter chama /v1/forecast.json no backend com coordenadas, dias, idioma pt, AQI/alertas desativados e a chave como parâmetro da requisição upstream.
- O payload é normalizado para ClimaPrevisaoResponse: temperatura Celsius, vento km/h, precipitação em mm, humidade/probabilidades em percentagem, timezone local, dados atuais, lista horária e lista diária.
- Os nomes e tipos canônicos são consumidos pelo parser TypeScript e pelos cards atuais. O teste backend existente simula o plano Free com 3 dias e prova que não preenche dias fictícios; outro teste simula 7 dias Starter. O frontend percorre os dias recebidos e aceita lista variável.
- O adaptador inclui chave em params somente na chamada server-side; a resposta canônica não tem campo de chave. __repr__/__str__ omitem o valor da credencial e existe teste unitário dessa propriedade.
- A descrição OpenAPI da rota promete “previsão diária de 7 dias” em router.py, mas o default WeatherAPI Free é 3 dias. É necessária decisão de produto: anunciar/assumir 3 dias, ou aprovar plano que forneça 7 dias e sua despesa.

### Controles e risco de ativação

- _init_weather_provider respeita WEATHERAPI_ENABLED, mas o serviço realmente montado usa DynamicWeatherOrchestrator. Em _rebuild_adapters o estado do adapter é definido por bool(chave), e verify_provider_public_authorization para WeatherAPI verifica existência de credencial. WEATHERAPI_ENABLED não aparece nesse caminho. Portanto, a variável “false” não é um bloqueio efetivo caso uma chave seja fornecida.
- A cadeia dinâmica inclui provedores de contingência. OpenWeather só passa pela autorização quando há credencial e licença; Open-Meteo exige licença/atestado de ambiente ou allow explícito. Nenhum fallback está habilitado por credencial nesta auditoria.
- Não há ativação efetuada nem se pode inferir a configuração efetiva de um serviço, pois não foram lidos arquivos .env nem iniciada API.

## 3. Dependências e cache

### PostgreSQL

A rota pública não recebe sessão PostgreSQL por dependency injection e não usa autenticação. Porém, quando a configuração dinâmica expira, DynamicWeatherOrchestrator.refresh_config abre async_session_maker para ler KEY_CLIMA e as credenciais de plataforma. A exceção é capturada e o código recorre a configuração/chaves de ambiente e mantém a configuração em memória. Logo:

- PostgreSQL não é uma dependência funcional obrigatória do formato da rota nem da normalização.
- O caminho de runtime ainda tenta acessar o banco para configuração/credenciais; sem conexão, o primeiro refresh pode atrasar a consulta até a falha/timeout de conexão. Não foi verificada essa latência.
- O teste existente test_11_ausencia_absoluta_acesso_postgresql injeta fixture_service com provider sintético. Ele comprova que essa fixture não acessa o banco, mas não comprova que o DynamicWeatherOrchestrator de produção funciona sem DB.
- Antes de afirmar “sem PostgreSQL”, é necessário teste unitário direcionado do orquestrador dinâmico, com banco inacessível mockado e credencial/config estática sintética; ou aprovar uma configuração estática que evite o refresh persistido. Não executar essa validação em ambiente com DATABASE_URL comercial.

### Redis e execução em múltiplos workers

- ClimaCache tenta Redis para cache recente/stale, rate limit por IP, single-flight/locks, métricas e reserva atômica de quota.
- Com clima_single_worker_fallback=True, ausência do Redis recorre a memória local. Em um único processo isso atende modo degradado, com cache e contadores voláteis.
- Memória não é compartilhada entre processos. Com Redis indisponível e mais de um worker, rate limits, deduplicação e contadores de quota deixam de ser globais. O fallback permite cada worker consumir até o limite configurado, potencialmente multiplicando a cota externa. A integração pública deve usar Redis compartilhado ou uma única instância de API enquanto esse fallback estiver ativo.

### Compatibilidade dos tempos de cache com termos WeatherAPI

Termos da API permitem cache de condições atuais por até 60 minutos e previsão por até 24 horas. O payload atual agrega ambos.

- Cache fresh do backend: TTL default 1.800 segundos (30 min), compatível com o limite mais curto de 60 min.
- Cache stale do backend: cache.py grava LAST_PREFIX no Redis com expiração de 7 dias e usa o valor stale quando a fonte falha. No fallback sem Redis, local_last não tem expiração em memória e permanece durante a vida do processo. Ambos excedem o máximo de cache para o payload que inclui condições atuais.
- Cache do navegador: localStorage salva a previsão com validade declarada, mas o envelope expirado continua armazenado e pode ser reutilizado em modo offline; não há expurgo pelo máximo contratual da fonte.
- O payload em cache não separa dados atuais da previsão para aplicar 60 min e 24 h diferentemente.

Esses limites exigem ajuste antes de usar a WeatherAPI. Recomendação mínima: para o envelope combinado, manter qualquer cópia servível dentro de 60 minutos, inclusive stale/offline, ou separar dados atuais e previsão com políticas e expiração independentes. A validade operacional do DeepFarms deve ainda ser menor ou igual ao limite da fonte.

## 4. Termos, atribuição e aviso ao usuário

### Licenciamento e plano candidato

- A tabela oficial lista Free a US$ 0/mês, uso comercial, 100k calls/mês, previsão de 3 dias e 95,5% uptime; Starter aparece a US$ 7/mês, 3M calls e previsão de 7 dias. Preços/limites são variáveis e devem ser reconfirmados no momento da ativação. [Tabela oficial de planos](https://www.weatherapi.com/pricing).
- Os termos específicos da API permitem uso pessoal/comercial incluindo uma aplicação web/móvel por chave/subscription; para usuários Free exigem crédito da WeatherAPI pelo nome/logo. A chave deve permanecer confidencial e não ser incorporada em código cliente. [Termos da API, licença e credenciais](https://www.weatherapi.com/terms).
- Termos limitam cache de current conditions a 60 minutos e forecast a 24 horas. Exigem disclaimer conspícuo dizendo, em resumo, que os dados são informativos/probabilísticos, podem não representar local/horário exatos, não devem ser base única de decisões críticas e que fontes meteorológicas oficiais devem ser consultadas. [Termos da API, cache e disclaimer](https://www.weatherapi.com/terms).
- A tabela/preços e a seção específica dos API Terms indicam uso comercial no Free. A página também contém termos gerais do site sobre material protegido; confirmar que o uso pretendido é abrangido pelo contrato API aplicável antes de ativar.
- Plano Free não apresenta SLA na tabela e o uptime publicado é 95,5%, portanto deve ser tratado como piloto de baixo volume sujeito a indisponibilidade, sem promessa de serviço contínuo.

### Implementação de UI observada

- CondicoesAtuaisCard mostra “WeatherAPI.com” como link quando provedor=WEATHERAPI; isso atende o crédito nominal visível no card, embora seja prudente garantir que ele apareça também junto a gráficos/diárias offline.
- AvisoAgronomicoCard já afirma que previsões são probabilísticas e que não substituem validação in-situ para operações críticas.
- O aviso atual não contém explicitamente todos os pontos requeridos nos termos da WeatherAPI: propósito informativo, possível imprecisão espacial/temporal, proibição de ser fonte única para segurança/emergência e recomendação de consultar serviço meteorológico oficial. A atribuição genérica inclui “WeatherAPI.com / Open-Meteo”, independentemente do provider ativo.

## 5. Ajustes mínimos recomendados (sem implementação)

### P0 — antes de ativar

1. Definir o limite de produto: 3 dias via Free ou 7 dias com plano pago. Atualizar a descrição OpenAPI e conteúdo promocional para o horizonte realmente disponível.
2. Corrigir o controle explícito de ativação para que a flag WEATHERAPI_ENABLED seja honrada também pelo DynamicWeatherOrchestrator; adicionar testes que demonstrem que key presente + flag false não faz requisição e que habilitação explícita controla o uso.
3. Compatibilizar cache backend, stale fallback e localStorage com os limites atuais do fornecedor. Cobrir expiração e offline sem exibir resposta após prazo permitido.
4. Completar o aviso ao usuário conforme o API Terms e apresentar crédito/branding por provider ativo em todas as visualizações relevantes.
5. Validar o caminho sem PostgreSQL com o provider dinâmico real e config/credenciais sintéticas, mockando async_session_maker para falha. O teste atual com SyntheticFixtureAdapter não satisfaz essa prova.
6. Se houver mais de um worker, exigir Redis compartilhado e validar reserva global da quota. Sem Redis, limitar deliberadamente a um worker até existir limitação distribuída.

### P1 — operação inicial

- Definir limiar interno de quota menor que 100.000 para deixar margem para chamadas não observadas e testar 80%/95%, esgotamento, retries e rollover mensal.
- Confirmar que uma requisição cache hit não consome quota upstream e que cache miss concorrente consome uma única chamada.
- Preparar alerta operacional, medição de chamada por mês, timeout, 401, 403, 429, 5xx e provider indisponível; sem expor query params ou chaves.
- Validar origem pública da API, CORS/rewrite e conexão HTTPS do frontend ao endpoint sem enviar credencial do fornecedor ao browser.
- Executar smoke controlado com conta/credencial autorizada só depois da aprovação específica. Esta tarefa não fez chamada real.

## 6. Testes e verificações realizadas

### Concluído

- Inspeção estática de router público, adapter WeatherAPI, orquestrador dinâmico, cache, schema, configuração, componentes e testes existentes.
- Testes unitários frontend: Vitest em clima-previsao.test.ts e clima-localidade.test.ts — **PASS, 2 arquivos, 28 testes**.
- Inspeção dos testes mockados existentes no backend: cobertura já escrita para adapter desabilitado/sem chave, segredo não presente em repr/str, mapeamento de erros upstream, payload Free de 3 dias, payload Starter de 7 dias, janela horária, quotas e HTTP 503. Esses testes não foram reescritos.

### Não concluído / não executado

- O comando da suite backend completa foi iniciado, mas não apresentou saída durante a janela de observação; foi interrompido por precaução. Uma segunda tentativa restrita aos casos WeatherAPI também não produziu saída no período observado e foi interrompida. **Nenhum resultado de aprovação backend é declarado.**
- Nenhuma requisição real ao WeatherAPI, BCB, IBGE ou outro provedor foi feita.
- Nenhuma API FastAPI, PostgreSQL, Redis ou Next.js foi iniciada; nenhum arquivo .env foi lido; nenhum segredo foi acessado.
- Não foram criados testes novos porque já existem casos simulados para os contratos centrais; permanece pendente completar o teste do orquestrador dinâmico sem PostgreSQL e da flag de ativação.

## 7. Plano de ativação controlada

1. Aprovar plano, horizonte (3 ou 7 dias), termos comerciais e atribuição.
2. Implementar e aprovar os bloqueios P0: flag explícita, cache compatível, disclaimer e caminho de config sem PostgreSQL.
3. Executar testes unitários isolados com fixture de payload; exigir PASS das suites backend sem conexão de banco/Redis e documentar o motivo de cada dependência.
4. Definir modo de operação: um worker sem Redis compartilhado, ou Redis dedicado para cache/quota distribuída. Fixar orçamento máximo e alertas.
5. Em autorização separada, configurar uma credencial sintética/fornecedor em segredo exclusivamente backend e executar smoke limitado com coordenada de teste; não fazer essa etapa nesta auditoria.
6. Validar anonimato, cache/freshness, comportamento offline, fonte e aviso nos dispositivos suportados.
7. Somente depois de evidências, autorizar ativação pública do provider.

## 8. Riscos e bloqueadores

- Retenção stale de 7 dias e retenção local sem expurgo podem violar limites contratuais de cache.
- Flag WEATHERAPI_ENABLED não é aplicada pelo caminho dinâmico usado pela rota.
- PostgreSQL não é exigido pela assinatura FastAPI da rota, mas o orquestrador tenta ler configuração/segredo no banco; sem DB há fallback para ambiente, porém latência e isolamento não foram testados.
- Teste “sem PostgreSQL” usa provider sintético e não valida a execução real do orquestrador dinâmico.
- Free limita previsão a três dias e oferece 95,5% uptime publicado sem SLA; anúncio de sete dias não é compatível com default.
- Disclaimer atual não cumpre literalmente todos os pontos exigidos pelo fornecedor.
- Redis local é fallback de worker único; quota pode ser multiplicada entre processos quando Redis está indisponível e o fallback fica habilitado.
- As suites backend não forneceram resultado nesta auditoria; esses contratos seguem não verificados em execução nesta fase.

## 9. Veredicto

**NO-GO para ativação da WeatherAPI neste checkout.** A integração técnica central existe e tem testes simulados escritos; a chave permanece backend-side. Antes de ativar são necessários: flag de habilitação realmente efetiva, política de cache dentro dos termos, escolha entre forecast de 3/7 dias, aviso completo, prova do caminho sem PostgreSQL e operação de quota compatível com o número de workers.

Não houve mudança de código/configuração, instalação, contratação, ativação, chamada externa ou conexão com banco/Redis. Nenhuma próxima etapa foi iniciada.
