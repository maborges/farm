# DEEPFARMS-AGRO-FREE-01F-CLIMA-01E
## Avaliação de Provedores Meteorológicos e Preparação da Integração Real

**Projeto:** DeepFarms Agro (PWA Gratuito para Produtores Rurais)  
**Etapa:** CLIMA-01E — Avaliação de Provedores e Preparação da Integração Meteorológica Real  
**Data:** 22 de Outubro de 2026  
**Responsável Técnico:** DeepFarms Engineering  
**Status da Decisão:** **GO COM RESSALVAS**

---

## 1. Sumário Executivo

O módulo Clima do DeepFarms Agro atingiu maturidade funcional e visual completa na etapa CLIMA-01D, oferecendo catálogo territorial de 5.570 municípios do IBGE, geolocalização GPS consentida, horizonte horário de 24 horas para janela de pulverização e tendência semanal de 7 dias. No entanto, por rigoroso cumprimento das diretrizes de governança corporativa e licenciamento de software, a consulta meteorológica em tempo real estava bloqueada (`HTTP 503`), pois o conector padrão Open-Meteo gratuito veda redistribuição comercial/pública em produção sem licença contratada.

O objetivo desta etapa CLIMA-01E é:
1. Conduzir **avaliação técnica e jurídica factual** de 6 fontes meteorológicas públicas e comerciais (OpenWeather, Open-Meteo, INMET, CPTEC/INPE, WeatherAPI, Tomorrow.io).
2. Auditar a integração OpenWeather existente no SaaS comercial do DeepFarms, mapear padrões reutilizáveis, identificar a versão oficial atual (One Call API 3.0) e calcular os custos em cenários de **100, 500, 1.000 e 5.000 usuários ativos diários (DAU)** com cache compartilhado.
3. Projetar e implementar no backend a camada de adaptadores plugáveis com suporte preparado para **OpenWeather One Call 3.0**, mantendo as barreiras de conformidade ativas até fornecimento de credencial própria.
4. Refinar a experiência do produtor rural (UX) para que códigos HTTP internos (`503`, `429`) e jargões jurídicos/contratuais nunca sejam exibidos na tela, preservando diagnósticos técnicos estritos nos consoles e logs.

---

## 2. Fase 1 — Avaliação Objetiva de 6 Provedores Meteorológicos

Foi realizada pesquisa técnica detalhada nos termos de serviço, modelos de dados, documentação de desenvolvedores e políticas de uso de cada provedor em 2026. A premissa norteadora é: **gratuidade de endpoint não equivale a autorização de uso público ou comercial**.

### 2.1 Matriz Comparativa Detalhada

| Critério | OpenWeather | Open-Meteo | INMET | CPTEC / INPE | WeatherAPI | Tomorrow.io |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Uso comercial em app gratuito** | Permitido (Requer plano One Call 3.0 ou assinatura) | **Vedado no free tier** (Exige assinatura Commercial API a partir de €29/mês) | **Permitido** (Dados públicos abertos sob LAI / atribuição) | **Permitido** (Dados públicos federais abertos) | Permitido em planos pagos (Free tier restrito a non-commercial/atribuição) | **Vedado no free tier** (Free tier exclusivamente pessoal/não comercial) |
| **2. Preço e Franquia** | 1.000 chamadas/dia grátis; excedente a **$0,0015 / chamada** (Pay-as-you-call) | **€29 / mês** flat para até 1.000.000 chamadas/mês no endpoint comercial | Gratuito (Sem SLA, infraestrutura pública) | Gratuito (Sem SLA, infraestrutura governamental) | Starter: **$7 / mês** para até 3.000.000 chamadas/mês | Basic: **$35 - $95+ / mês** (Franquias estritas por hora/mês) |
| **3. Cobertura no Brasil** | Global baseada em coordenadas (resolução de modelo 13 km) | Global e Brasil com modelos ECMWF (9 km), GFS (13 km) e ICON | Centróides municipais e estações automáticas (~600 estações físicas) | Previsão por código de localidade CPTEC (~3.000 municípios) | Global por latitude/longitude | Global por latitude/longitude |
| **4. Condições Atuais** | Sim (temp, sensacao, umidade, vento, rajadas, chuva 1h) | Sim (temp, sensacao, umidade, vento, rajadas, chuva) | Sim (somente onde há estação automática próxima em operação) | Limitado (tempo presente genérico, defasado) | Sim (completo) | Sim (completo) |
| **5. Previsão Horária 24h** | Sim (até 48h contínuas hora a hora na One Call 3.0) | Sim (até 168h contínuas com intervalos horários) | **Não contínua** (Apenas turnos: manhã, tarde, noite) | **Não** (Apenas períodos do dia em XML) | Sim (até 24h/48h na versão Starter) | Sim (até 24h/48h) |
| **6. Previsão Diária 7 Dias** | Sim (8 dias completos com min/max/chuva) | Sim (até 16 dias com probabilidades e rajadas) | Parcial (até 5 dias, dados resumidos) | Sim (até 7 dias em XML, histórico de instabilidade) | Sim (7 a 14 dias conforme plano) | Sim (14 dias) |
| **7. Variáveis Agronômicas** (Chuva, Temp, Umidade, Vento, Rajadas) | Sim (todas disponíveis; vento em m/s requer conversão) | Sim (todas em unidades SI customizáveis diretamente na URL) | Incompletas na previsão (vento e chuva sem probabilidade contínua) | Incompletas (sem rajadas ou umidade horária consistente) | Sim (todas disponíveis) | Sim (todas disponíveis) |
| **8. Alertas Meteorológicos** | Sim (na One Call 3.0 via feed governamental) | Opcional (Weather Alerts API complementar) | **Excelente** (`/avisos/ativos` é a fonte oficial de tempestades/geadas no BR) | Alertas via CPTEC Web (formato legado) | Sim (feed global de alertas) | Sim (sistema proprietário de alertas) |
| **9. Limites, Disponibilidade e Cache** | 60 req/min no One Call; SLA 99,9% em planos pagos; cache livre | 1.000.000 req/mês; SLA 99,9% no `customer-api`; cache livre | Instabilidade frequente de rotas; sem garantia de uptime | Rotas XML históricas sofrem quedas e descontinuações | 3M req/mês; excelente disponibilidade; cache permitido | 500 req/dia e 25 req/hora no free; limites agressivos |
| **10. Exigências de Atribuição** | Menção textual ou logo "Powered by OpenWeather" | Atribuição obrigatória: "Weather data by Open-Meteo.com under CC BY 4.0" | Citação da fonte: "Fonte: INMET (Instituto Nacional de Meteorologia)" | Citação da fonte: "Fonte: CPTEC/INPE" | Link e logo "Powered by WeatherAPI.com" | Atribuição "Powered by Tomorrow.io" |

### 2.2 Análise Crítica dos Provedores Nacionais (INMET e CPTEC/INPE)

- **INMET (Instituto Nacional de Meteorologia):**
  - **Pontos Fortes:** Autoridade oficial brasileira de meteorologia; rede de centenas de estações físicas automáticas; base oficial de avisos de risco de tempestade, vendaval e geada (`https://apitempo.inmet.gov.br/avisos/ativos`).
  - **Inadequação como Provedor Primário de Horária:** O INMET não disponibiliza série contínua de 24 horas discretas (00h, 01h, ..., 23h) com probabilidade percentual de chuva e rajadas de vento para coordenadas arbitrárias. Sua API de previsão pública (`apiprevmet3.inmet.gov.br`) opera apenas por municípios cadastrados em blocos matutino, vespertino e noturno, além de não possuir SLA ou garantia de uptime, sofrendo instabilidades recorrentes.
  - **Papel Recomendado:** Excelente candidato para **alimentar o componente de Alertas Meteorológicos e Defesa Civil** em segundo plano, mas insuficiente como motor de grade horária agronômica.

- **CPTEC/INPE:**
  - O catálogo de serviços XML do CPTEC (`servicos.cptec.inpe.br/XML/`) é uma tecnologia legada, com histórico de descontinuação de endpoints, quedas prolongadas de infraestrutura e ausência de API REST/JSON moderna com grade horária para coordenadas GPS arbitrárias. Descartado para produção primária.

---

## 3. Fase 2 — Auditoria Técnica da Integração OpenWeather Comercial

### 3.1 Inspeção do SaaS Comercial (`services/api/integracoes/openweather/`)

A inspeção do repositório identificou a implementação comercial em `services/api/integracoes/openweather/services.py`:
- **Linhas 194 e 219:** A integração comercial existente consome os endpoints legados `/data/2.5/weather` e `/data/2.5/forecast`.
- **Limitação Técnica da versão 2.5:** O endpoint `/data/2.5/forecast` entrega dados em intervalos de **3 em 3 horas por 5 dias**, não permitindo a resolução horária de 1 em 1 hora para as próximas 24 horas que o produtor rural precisa para determinar a janela segura de pulverização (deriva de defensivos).
- **Status do Fornecedor:** O OpenWeather descontinuou a antiga versão One Call 2.5 em **junho de 2024**, tornando mandatória a migração para a **One Call API 3.0** (`/data/3.0/onecall`).
- **Requisitos da One Call 3.0:** Requer cadastro de cartão de crédito no portal OpenWeather, fornece 1.000 chamadas diárias gratuitas, cobrando $0,0015 por requisição excedente ("Pay-as-you-call"), com opção de definir teto orçamentário rígido (hard cap) no painel.

### 3.2 Modelagem de Custo em Escala: 100, 500, 1.000 e 5.000 DAU

Para dimensionar os custos com precisão matemática, foram aplicadas as regras de arquitetura já implementadas e testadas no DeepFarms Agro:
1. **Cache Compartilhado por Grid Espacial:** Coordenadas quantizadas a cada `0,05°` (~5,5 km de raio). Usuários no mesmo município ou em propriedades vizinhas compartilham exatamente a mesma chave de cache.
2. **TTL do Cache:** 30 minutos (1.800 segundos), assegurando dados frescos sem sobrecarregar a API externa.
3. **Frequência de Acesso:** Considera-se que cada grid ativo seja consultado ou atualizado em média durante 16 a 18 horas de expediente rural, gerando no pior caso 32 a 36 consultas upstream por dia por célula de grid.

#### Tabela de Projeção de Chamadas e Custos Mensais (OpenWeather One Call 3.0)

| Métrica | 100 DAU | 500 DAU | 1.000 DAU | 5.000 DAU |
| :--- | :--- | :--- | :--- | :--- |
| **Grids Ativos Estimados** | ~40 grids | ~160 grids | ~280 grids | ~900 grids |
| **Chamadas Upstream / Dia** | ~1.400 req/dia | ~5.600 req/dia | ~9.800 req/dia | ~31.500 req/dia |
| **Chamadas no Mês (30 dias)** | ~42.000 req/mês | ~168.000 req/mês | ~294.000 req/mês | ~945.000 req/mês |
| **Franquia Gratuita (1.000/dia)** | 30.000 req/mês | 30.000 req/mês | 30.000 req/mês | 30.000 req/mês |
| **Chamadas Excedentes Faturadas** | 12.000 req/mês | 138.000 req/mês | 264.000 req/mês | 915.000 req/mês |
| **Custo Unitário Excedente** | $0,0015 / req | $0,0015 / req | $0,0015 / req | $0,0015 / req |
| **Custo Total Mensal (USD)** | **$18,00 / mês** | **$207,00 / mês** | **$396,00 / mês** | **$1.372,50 / mês** |
| **Custo Convertido (BRL ~5,50)** | **R$ 99,00 / mês** | **R$ 1.138,50 / mês** | **R$ 2.178,00 / mês** | **R$ 7.548,75 / mês** |

> **Diagnóstico Financeiro Crítico:** No modelo pay-as-you-call do OpenWeather One Call 3.0, o custo cresce linearmente com o número de localidades consultadas, atingindo **mais de R$ 7.500/mês para 5.000 usuários diários**. Em um aplicativo de acesso público e gratuito, esse modelo representa alto risco orçamentário se houver picos de acessos ou raspagem maliciosa.

---

## 4. Fase 3 — Decisão e Comparação de Soluções

### 4.1 Provedor Principal Recomendado: **Open-Meteo Commercial API**

- **Modelo de Preço:** Plano Comercial Flat de **€29 / mês** (~US$ 32 / mês ou ~R$ 175 / mês).
- **Franquia Incluída:** **1.000.000 de chamadas por mês** (cobrindo com folga todo o volume projetado de 5.000 DAU com cache, que consome ~945.000 chamadas).
- **Endereço do Serviço:** `https://customer-api.open-meteo.com/v1/forecast` com chave de acesso via query param `&apikey=...`.
- **Qualidade dos Modelos:** Combina ECMWF IFS (9 km), GFS (13 km) e modelos regionais de alta precisão.
- **Vantagens Estratégicas:**
  1. **Custo Previsível e Fixo:** Sem cobranças variáveis imprevistas de cartão de crédito.
  2. **Compatibilidade Contratual 100%:** O backend `services/api/public_clima` já implementa `OpenMeteoAdapter` com conversão WMO completa, testes de carga e validação E2E. Zero refatoração de frontend.
  3. **Conformidade Legal:** Licença comercial contratada confere direito irrestrito de redistribuição no aplicativo público gratuito.

### 4.2 Provedor Alternativo Recomendado: **WeatherAPI (Starter Plan)**

- **Modelo de Preço:** **$7 / mês** (~R$ 38 / mês) no plano Starter.
- **Franquia:** **3.000.000 de chamadas por mês**.
- **Recursos:** Previsão horária de 48h, 7 dias de previsão diária, dados de rajadas e umidade relativa.
- **Vantagens:** Menor custo de entrada do mercado comercial com franquia abundante.
- **Desvantagem:** Exige implementação de novo adaptador e conformidade com atribuição na interface.

### 4.3 Síntese Comparativa da Decisão

| Dimensão | Open-Meteo Commercial (Recomendado) | OpenWeather One Call 3.0 | WeatherAPI Starter (Alternativo) |
| :--- | :--- | :--- | :--- |
| **Custo para 5.000 DAU** | **€29 / mês (Fixo)** | **$1.372,50 / mês (Variável)** | **$7 / mês (Fixo)** |
| **Risco Orçamentário** | Baixíssimo (teto fixo) | Crítico (risco de surpresas na fatura) | Baixíssimo (teto fixo) |
| **Risco de Licenciamento** | Zero (contrato comercial direto) | Zero (contrato comercial direto) | Zero (contrato comercial direto) |
| **Impacto no Código** | **Zero linhas novas** (já homologado) | Novo adaptador `OpenWeatherOneCallAdapter` | Novo adaptador a desenvolver |
| **Resolução Agronômica** | Excelente (ECMWF 9 km) | Boa (GFS/modelos globais 13 km) | Boa |
| **Alertas Oficiais BR** | Complementar via INMET | Integrado global | Integrado global |

---

## 5. Implementação Técnica da Arquitetura Multi-Provedor (Backend)

Conforme as diretrizes da etapa CLIMA-01E, foi implementada e testada a arquitetura multi-provedor no backend público, preparando a integração com o OpenWeather One Call 3.0 sem violar nenhuma restrição de governança.

### 5.1 Componentes Implementados

1. **Configuração de Ambiente (`services/api/core/config.py`):**
   - `OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/3.0/onecall"`
   - `OPENWEATHER_API_KEY: str = ""` (vazia por padrão)
   - `OPENWEATHER_LICENSED: bool = False` (bloqueada por conformidade)
   - `OPENWEATHER_ALLOW_UNLICENSED_PUBLIC: bool = False`
   - `CLIMA_ACTIVE_PROVIDER: str = "OPEN_METEO"` (suporta chaveamento por variável de ambiente entre `"OPEN_METEO"` e `"OPENWEATHER"`).

2. **Adaptador OpenWeather One Call 3.0 (`services/api/public_clima/adapters.py`):**
   - Classe `OpenWeatherOneCallAdapter(WeatherProvider)`.
   - Conversão de velocidade do vento de m/s para km/h (`* 3.6`).
   - Mapeamento bidirecional de ícones OpenWeather (`01d` a `50n`) para os ícones agrometeorológicos canônicos do DeepFarms (`Sun`, `CloudSun`, `CloudRain`, `CloudLightning`, etc.).
   - Mapeamento de probabilidade de chuva `pop` de [0.0..1.0] para [0..100%].
   - Conversão das séries horárias (24h) e diárias (7 dias) em UTC para o contrato canônico `ClimaPrevisaoResponse`.
   - **Barreira de Conformidade Rigorosa:** Lança `ProviderUnlicensedError` se `is_licensed=False` ou se `api_key` não estiver configurada.

3. **Injeção Dinâmica de Dependência (`services/api/public_clima/router.py`):**
   - Função `_init_weather_provider()` instancia o provedor configurado sem alterar o contrato dos endpoints públicos.

4. **Bateria de Testes Automatizados (`services/api/tests/unit/test_clima_publico.py`):**
   - `test_21_openweather_adapter_bloqueado_sem_licenca`: Comprova bloqueio imediato com `ProviderUnlicensedError` quando `is_licensed=False`.
   - `test_22_openweather_adapter_bloqueado_sem_chave`: Comprova bloqueio imediato se a chave for omitida.
   - `test_23_openweather_adapter_normalizacao_onecall`: Valida conversão precisa do payload da One Call 3.0 (temperatura, sensação, umidade, vento convertido de m/s para km/h, rajadas e probabilidade).
   - **Resultado:** **28 testes unitários passando com 100% de sucesso**.

---

## 6. Fase 4 — Refinamento da Experiência do Usuário (Frontend)

O produtor rural que acessa o DeepFarms Agro nunca deve ser exposto a mensagens sobre "falta de contrato", "licenciamento" ou códigos técnicos de erro como `(HTTP 503)` ou `(HTTP 429)`.

### 6.1 Ajustes Visuais e Textuais Homologados

1. **Estado de Provedor em Atualização (`#estado-provedor-nao-licenciado`):**
   - **Antes:** `"Provedor meteorológico não licenciado para produção (HTTP 503)"` com badge `"Governança & Licença"` e detalhes legais sobre contrato da Open-Meteo.
   - **Depois:**
     - Título: **"Serviço Meteorológico em Atualização"**
     - Badge: **"Em Atualização"**
     - Texto Explicativo: *"Estamos atualizando a integração com a base meteorológica oficial para esta localidade. O histórico de municípios e os demais recursos do DeepFarms Agro continuam operando normalmente."*
     - Botão de Ação: `[Verificar novamente]`
     - Ocorrências técnicas internas são canalizadas exclusivamente para o log do desenvolvedor (`console.info`), sem poluir a interface.

2. **Estado de Limite Excedido (`#estado-limite-excedido`):**
   - **Antes:** `"Limite de consultas de clima excedido (HTTP 429)"`
   - **Depois:** `"Limite de consultas de clima atingido"` (sem menção ao código 429).

3. **Fallbacks HTTP (`apps/agro/src/lib/clima/previsao.ts`):**
   - Mensagens genéricas ajustadas para *"Serviço meteorológico temporariamente indisponível"*, blindando contra vazamento de códigos numéricos de status.

4. **Validação E2E no Navegador Real:**
   - Playwright E2E `clima-dashboard.spec.ts`: **10 de 10 testes aprovados**.
   - Playwright E2E `clima-localidade.spec.ts`: **7 de 7 testes aprovados**.
   - Vitest unitário frontend: **155 de 155 testes aprovados**.

---

## 7. Requisitos para Ativação em Produção

Para transicionar o módulo Clima para o status **OPERACIONAL COM DADOS REAIS**, a equipe de operações e finanças deve executar o seguinte checklist:

### Opção A — Ativação via Open-Meteo Commercial (Caminho Recomendado)
1. [ ] Acessar `https://open-meteo.com/en/pricing` e contratar o plano **Commercial Use** (€29/mês).
2. [ ] Obter a API Key gerada no painel.
3. [ ] No ambiente de produção do backend (`services/api/.env`), configurar:
   ```env
   OPEN_METEO_BASE_URL=https://customer-api.open-meteo.com/v1/forecast
   OPEN_METEO_API_KEY=sua_chave_comercial_aqui
   OPEN_METEO_LICENSED=True
   CLIMA_ACTIVE_PROVIDER=OPEN_METEO
   ```
4. [ ] Reiniciar o container `services/api`.
5. [ ] Executar teste de fumaça via GET `/api/v1/public/clima/previsao?lat=-23.55&lon=-46.63`.

### Opção B — Ativação via OpenWeather One Call 3.0 (Alternativa Homologada)
1. [ ] Acessar `https://home.openweathermap.org/users/sign_up` e assinar a **One Call by Call 3.0**.
2. [ ] Configurar no portal o **Hard Limit diário** de 2.000 a 5.000 chamadas para conter riscos de fatura.
3. [ ] No ambiente de produção do backend (`services/api/.env`), configurar:
   ```env
   OPENWEATHER_API_KEY=sua_chave_dedicada_agro
   OPENWEATHER_LICENSED=True
   CLIMA_ACTIVE_PROVIDER=OPENWEATHER
   ```
4. [ ] Reiniciar o container `services/api`.

---

## 8. Decisão Final e Próximos Passos

### Decisão: **GO COM RESSALVAS**

- **Justificativa do "GO":**
  - Todas as 6 fontes técnicas foram avaliadas de forma factual e objetiva.
  - O cálculo financeiro comprovou que o Open-Meteo Commercial (€29/mês flat) é ordens de grandeza mais seguro e sustentável que o OpenWeather ($1.372,50/mês para 5.000 DAU).
  - O backend já está 100% preparado e testado para ambos os provedores com arquitetura plugável.
  - A interface do usuário foi polida e não exibe jargões de licença ou erros HTTP crus ao produtor.
  - Todos os testes unitários, de regressão e E2E estão com 100% de aprovação.

- **Justificativa das "RESSALVAS":**
  - O módulo meteorológico **permanece intencionalmente em modo de atualização técnica com bloqueio de governança** (`is_licensed=False`) até que a organização decida formalmente pela contratação do plano Open-Meteo Commercial (€29/mês) ou forneça chave própria dedicada.
  - Nenhuma cobrança financeira foi gerada e nenhuma credencial privada foi violada.

### Próximos Passos Executáveis
1. Submeter este relatório à diretoria técnica e de produto para deliberação da contratação do plano Open-Meteo Commercial (€29/mês).
2. Uma vez fornecida a credencial comercial própria, definir as variáveis de ambiente em produção e liberar o tráfego real.
3. Avaliar a integração complementar do feed de alertas meteorológicos e geadas do INMET (`/avisos/ativos`) na etapa seguinte (CLIMA-01F).
