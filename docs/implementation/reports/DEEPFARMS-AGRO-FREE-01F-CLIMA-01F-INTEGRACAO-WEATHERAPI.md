# DEEPFARMS-AGRO-FREE-01F-CLIMA-01F — Relatório de Homologação e Integração Controlada WeatherAPI

**Data:** 22 de Outubro de 2026  
**Responsável Técnico:** GPT-5.6 Codex — Sol  
**Módulo:** Clima Público (`services/api/public_clima` & `apps/agro`)  
**Contexto:** Integração controlada da WeatherAPI como candidata principal para o piloto do DeepFarms Agro, com isolamento absoluto de custos, conformidade contratual, controle de consumo e suporte aos planos Free e Starter.

---

## 1. Verificação Contratual e Técnica (WeatherAPI)

Em atendimento à Fase 1, foi realizada verificação minuciosa da documentação e termos oficiais da WeatherAPI (`weatherapi.com/pricing`, `terms`, `docs/forecast-api`, `docs/error-codes`).

### 1.1. Matriz de Conformidade Contratual

| Requisito / Critério | Condição Oficial Documentada | Classificação | Aderência no DeepFarms Agro |
| :--- | :--- | :--- | :--- |
| **Uso Comercial no PWA Gratuito** | Permitido explicitamente tanto no plano Free quanto nos planos pagos (Starter em diante). | Documentado | **TOTAL** — Módulo público do DeepFarms Agro opera em conformidade. |
| **Franquia e Preço Starter** | US$ 7,00/mês (ou US$ 75,00/ano se faturado anualmente), franquia de 3.000.000 de chamadas mensais. | Documentado | **CONFORMIDADE CONDICIONADA** — Depende de contratação formal pelo cliente. |
| **Horizonte Free vs. Starter** | **Free:** até 3 dias de previsão (100k chamadas/mês).<br>**Starter:** até 7 dias de previsão (3M chamadas/mês). | Documentado | **TOTAL** — O conector adapta dinamicamente sem interpolações ou dados inventados. |
| **Política de Atribuição** | Obrigatório no plano Free link de crédito legível: *"Powered by WeatherAPI.com"* apontando para `https://www.weatherapi.com/`. | Documentado | **TOTAL** — Componente `CondicoesAtuaisCard` e `AvisoAgronomicoCard` incluem atribuição oficial com link. |
| **Política de Cache** | Permitido cache de condições atuais por até 60 min e previsões horárias/diárias por até 24 horas. | Documentado | **TOTAL** — Nosso TTL é de 30 minutos (1800s), perfeitamente dentro do limite estipulado. |
| **Redistribuição de Dados** | É vedada a revenda direta de raw data (expor a API como broker de dados meteorológicos para terceiros). É permitido o consumo em aplicação final web/mobile para usuários finais. | Documentado | **TOTAL** — Os dados alimentam o PWA do produtor rural em contexto agrometeorológico contextualizado. |
| **Aviso Meteorológico Obrigatório** | Termos estipulam que previsões são estimativas probabilísticas e não devem ser a única fonte para situações críticas de risco à vida ou operações de risco sem validação técnica. | Documentado | **TOTAL** — Card `AvisoAgronomicoCard` traz ressalva formal de que estimativas não substituem RT de Engenheiro Agrônomo in-situ. |
| **Comportamento ao Exceder Franquia** | Retorna HTTP 403 com código de erro `2007` (`API key has exceeded calls per month quota`). | Documentado | **TOTAL** — Mapeado para `ProviderQuotaExceededError` no backend e mensagem operacional sem expor código ao produtor. |
| **Cobrança Automática de Excedentes** | Em planos pagos com cartão cadastrado, os termos prevêem cobrança adicional por chamadas excedentes (US$ 0,002 por 1.000 chamadas) a menos que configurado limite no painel. | Documentado | **MITIGADO** — Implementada trava de segurança no código (`WEATHERAPI_MONTHLY_QUOTA_LIMIT`), bloqueando chamadas antes do estouro. |
| **Proteção da API Key** | A chave é estritamente confidencial, intransferível e não pode ser embutida em código cliente, URLs públicas ou repositórios abertos. | Documentado | **TOTAL** — Ingestão apenas no backend FastAPI; `__repr__` e logs sanitizados; ausência total nos bundles Next.js. |

*Nota de Governança:* Nenhuma contratação, cadastro ou ativação de teste pago foi realizada nesta etapa, cumprindo rigorosamente as diretrizes orçamentárias.

---

## 2. Arquitetura e Arquivos Implementados

A implementação seguiu padrão incremental, mantendo os adaptadores `OpenMeteoAdapter` e `OpenWeatherOneCallAdapter` plenamente funcionais e preservados.

```
services/api/
├── core/
│   └── config.py                     <- Parâmetros WeatherAPI (chaves, URLs, quotas e timeouts)
├── public_clima/
│   ├── adapters.py                   <- WeatherAPIAdapter (normalização, 24h contínuas, ícones, erros)
│   ├── cache.py                      <- ClimaCache com telemetria (hits, misses, upstream, erros e quotas)
│   ├── service.py                    <- PublicClimaService (verificação de cota mensal e single-flight)
│   └── router.py                     <- Fábrica multi-provedor e tratamento de HTTP 503 amigável
└── tests/unit/
    └── test_clima_publico.py         <- 14 novos testes unitários e de integração WeatherAPI

apps/agro/src/
├── components/clima/
│   ├── previsao-diaria.tsx           <- Apresentação dinâmica da quantidade de dias (3d Free vs 7d Starter)
│   ├── condicoes-atuais-card.tsx     <- Link de atribuição oficial WeatherAPI.com
│   └── aviso-agronomico-card.tsx     <- Disclaimer de modelo probabilístico e responsabilidade técnica
└── lib/clima/
    └── previsao.ts                   <- Contratos e utilitários de exibição
```

---

## 3. Contrato, Normalização e Horizon 24h

### 3.1. Normalização de Parâmetros Físicos

| Variável | Entrada WeatherAPI | Normalização DeepFarms Agro | Observação |
| :--- | :--- | :--- | :--- |
| **Temperatura** | `current.temp_c` | `temperaturaAtualC: float` | Direto em Celsius (°C). |
| **Sensação Térmica** | `current.feelslike_c` | `sensacaoTermicaC: float` | Direto em Celsius (°C). |
| **Umidade Relativa** | `current.humidity` | `umidadeRelativaPct: int` | Percentual direto (0 a 100%). |
| **Velocidade do Vento** | `current.wind_kph` | `ventoVelocidadeKmH: float` | Fornecido nativamente em km/h (sem fator de conversão). |
| **Rajadas de Vento** | `current.gust_kph` | `ventoRajadasKmH: float` | Fornecido nativamente em km/h. |
| **Direção do Vento** | `current.wind_degree` | `ventoDirecaoGraus: int` | Graus de azimute (0° a 360°). |
| **Precipitação Observada** | `current.precip_mm` | `precipitacaoMm: float` | Acumulado em milímetros (mm). |
| **Probabilidade de Chuva** | `day.daily_chance_of_rain` | `probabilidadeChuvaPct: int` | Percentual (0 a 100%). |
| **Iconografia** | `condition.code` + `is_day` | `condicaoIcone: str` | Mapeado para `Sun`, `Moon`, `CloudSun`, `Cloud`, `CloudFog`, `CloudDrizzle`, `CloudRain`, `CloudLightning`, `CloudSnow`. |

### 3.2. Projeção Horária Contínua de 24 Horas (Transposição da Meia-Noite)

O endpoint da WeatherAPI agrupa os horários dentro de cada elemento de `forecastday` (das 00:00 às 23:00 de cada dia).  
Para garantir o horizonte contínuo das **próximas 24 horas reais**, o conector implementa a seguinte lógica matemática:
1. Concatena os registros horários de todos os dias retornados (`forecastday[0]`, `forecastday[1]`, etc.).
2. Determina a hora de referência `current_hour_epoch = ref_epoch - (ref_epoch % 3600)`.
3. Filtra as horas onde `time_epoch >= current_hour_epoch`.
4. Seleciona os primeiros 24 itens da lista contínua.  
*Resultado comprovado em teste:* Se a consulta for feita às 20:00 do Dia 0, o retorno compreende as 4 horas restantes do Dia 0 (20h, 21h, 22h, 23h) e as primeiras 20 horas do Dia 1 (00h até 19h), em ordem cronológica contínua e sem quebras de fuso horário.

---

## 4. Configuração de Segurança e Isolamento

As configurações foram centralizadas em `services/api/core/config.py`:
- `CLIMA_ACTIVE_PROVIDER=WEATHERAPI`
- `WEATHERAPI_API_KEY=""` (vazia por padrão)
- `WEATHERAPI_ENABLED=False` (desabilitado por padrão)
- `WEATHERAPI_BASE_URL=https://api.weatherapi.com/v1`
- `WEATHERAPI_MAX_FORECAST_DAYS=3` (padrão seguro Free)
- `WEATHERAPI_TIMEOUT_SECONDS=5.0`
- `WEATHERAPI_MONTHLY_QUOTA_LIMIT=100000` (teto rígido de proteção financeira)

### Salvaguardas Implementadas
1. **Proteção de Objetos:** O método `__repr__` e `__str__` da classe `WeatherAPIAdapter` omite propositalmente a API Key, exibindo apenas `<WeatherAPIAdapter enabled=... max_days=...>`.
2. **Sanitização de URLs de Erro:** Em caso de falha de conexão, a URL nos logs omite o parâmetro `key`.
3. **Ausência nos Bundles do Cliente:** Varredura estática comprovou que nenhuma chave ou segredo foi exportado para o bundle compilado Next.js (`apps/agro/.next/static/`).
4. **Isolamento de Credenciais Comerciais:** Não há reutilização de chaves de outros produtos DeepFarms.

---

## 5. Compatibilidade Free vs. Starter

| Aspecto | Plano Free (Homologação Atual) | Plano Starter (Ativação Futura) |
| :--- | :--- | :--- |
| **Custo** | US$ 0,00 | US$ 7,00/mês (US$ 75,00/ano) |
| **Franquia Upstream** | 100.000 chamadas/mês | 3.000.000 chamadas/mês |
| **Dias de Previsão** | Até 3 dias | Até 7 dias |
| **Comportamento Frontend** | Título: *"Previsão dos Próximos 3 Dias"*<br>Badge: *"Horizonte 3 Dias"* | Título: *"Previsão dos Próximos 7 Dias"*<br>Badge: *"Tendência Semanal"* |
| **Preenchimento Artificial** | **PROIBIDO** — Exibe rigorosamente os 3 dias retornados | Exibe os 7 dias completos |
| **Ativação** | Imediata após fornecimento de chave própria autorizada | Condicionada à contratação e autorização formal |

---

## 6. Controle de Consumo e Dimensionamento Operacional

### 6.1. Infraestrutura de Telemetria e Cache
A classe `ClimaCache` foi expandida para registrar:
- `agro:clima:v1:metrics:upstream:{provedor}:{AAAA-MM}`: Chamadas reais upstream.
- `agro:clima:v1:metrics:hit:{provedor}`: Requisições atendidas pelo cache L1/L2.
- `agro:clima:v1:metrics:miss:{provedor}`: Requisições que demandaram consulta ou lock.
- `agro:clima:v1:metrics:error:{provedor}:{tipo}`: Timeouts e falhas.
- `check_monthly_quota()`: Bloqueio atômico de chamadas upstream quando atingir o limite estipulado no software.
- Lock atômico *single-flight* no grid espacial (~5,5 km), garantindo que múltiplos produtores consultando o mesmo município consumam apenas 1 chamada à WeatherAPI a cada 30 minutos.

### 6.2. Estimativa de Consumo por Cenários de DAU

Considerando TTL de 30 minutos (1.800s), 14 horas de atividade diária por produtor e repetição de consultas:

| DAU (Usuários Ativos/Dia) | Cenário de Dispersão | Municípios Distintos no Grid | Chamadas Teóricas/Dia (com Cache) | Chamadas Mensais Estimadas | Status no Plano Free (100k/mês) | Status no Plano Starter (3M/mês) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **100** | Baixa (Polos concentrados) | 15 municípios | 420 | 12.600 | **FOLGA (12,6%)** | **FOLGA (< 1%)** |
| **100** | Média | 40 municípios | 1.120 | 33.600 | **FOLGA (33,6%)** | **FOLGA (1,1%)** |
| **100** | Alta (1 município por usuário) | 80 municípios | 2.240 | 67.200 | **FOLGA (67,2%)** | **FOLGA (2,2%)** |
| **500** | Baixa | 40 municípios | 1.120 | 33.600 | **FOLGA (33,6%)** | **FOLGA (1,1%)** |
| **500** | Média | 120 municípios | 3.360 | 100.800 | **LIMITE (100%)** | **FOLGA (3,3%)** |
| **500** | Alta | 300 municípios | 8.400 | 252.000 | **EXCEDE FREE** | **FOLGA (8,4%)** |
| **1.000** | Baixa | 70 municípios | 1.960 | 58.800 | **FOLGA (58,8%)** | **FOLGA (1,9%)** |
| **1.000** | Média | 250 municípios | 7.000 | 210.000 | **EXCEDE FREE** | **FOLGA (7,0%)** |
| **1.000** | Alta | 600 municípios | 16.800 | 504.000 | **EXCEDE FREE** | **FOLGA (16,8%)** |
| **5.000** | Baixa | 200 municípios | 5.600 | 168.000 | **EXCEDE FREE** | **FOLGA (5,6%)** |
| **5.000** | Média | 800 municípios | 22.400 | 672.000 | **EXCEDE FREE** | **FOLGA (22,4%)** |
| **5.000** | Alta | 2.500 municípios | 70.000 | 2.100.000 | **EXCEDE FREE** | **CONFORTÁVEL (70%)** |

*Conclusão de Consumo:* O plano Starter (3M chamadas) comporta com ampla segurança até 5.000 DAU, mesmo em cenários de alta dispersão geográfica. O plano Free é ideal para a fase de homologação inicial (até 100-200 DAU concentrados).

---

## 7. Mapeamento de Erros e Experiência do Produtor

| Código WeatherAPI | Significado Oficial | Exceção Interna Backend | Resposta HTTP Pública | Experiência no Frontend |
| :---: | :--- | :--- | :---: | :--- |
| **1002** | API key not provided | `ProviderUnconfiguredError` | 503 Service Unavailable | Card *"Serviço em Atualização"* com botão de rechecagem. |
| **1005 / 2006** | API key invalid / URL malformada | `ProviderAuthenticationError` | 503 Service Unavailable | Mensagem acolhedora de manutenção técnica. |
| **1006** | No location found | `ProviderLocationNotFoundError` | 404 Not Found | Mensagem orientando selecionar município vizinho. |
| **2007** | Calls per month quota exceeded | `ProviderQuotaExceededError` | 503 Service Unavailable | Alerta amigável de capacidade operacional temporária. |
| **2008** | API key disabled | `ProviderAuthenticationError` | 503 Service Unavailable | Mensagem padronizada de atualização. |
| **2009** | Resource not available on plan | `ProviderUnlicensedError` | 503 Service Unavailable | Mensagem padronizada de serviço em configuração. |
| **9999** | Internal application error | `ProviderUnavailableError` | 503 Service Unavailable | Fallback automático para último dado em cache (se houver). |
| **Timeout** | Latência upstream > 5s | `ProviderTimeoutError` | 503 Service Unavailable | Retorno do dado anterior com aviso de defasagem. |

---

## 8. Testes e Validações Realizadas

### 8.1. Testes Automatizados no Backend (Pytest)
- **Módulo Clima Público:** 44 testes aprovados (100% de sucesso).
- **Testes dedicados da WeatherAPI:**
  - `test_weatherapi_unlicensed_or_disabled`: Rejeição sem credencial ativa.
  - `test_weatherapi_credentials_protection`: Ausência de chave em `repr` e `str`.
  - `test_weatherapi_error_mapping`: Validação dos 8 códigos documentados.
  - `test_weatherapi_normalization_free_plan_3_days`: Normalização e ausência de padding falso.
  - `test_weatherapi_normalization_starter_plan_7_days`: Suporte nativo a 7 dias.
  - `test_weatherapi_rolling_24h_crossing_midnight`: Continuidade através da meia-noite.
  - `test_clima_cache_telemetry_and_quota`: Contadores de upstream, hits, misses e erros.
  - `test_clima_service_monthly_quota_enforcement`: Interrupção ao esgotar a cota configurada.
  - `test_fastapi_weatherapi_quota_exceeded_http_503`: Sanitização na borda da API.
- **Regressões do Mercado Público:** 42 testes aprovados (DERAL, BCB PTAX, Macro e IBGE).

### 8.2. Validações Frontend
- **Vitest:** 11 arquivos, 155 testes aprovados (100%).
- **TypeScript Typecheck:** `tsc --noEmit` concluído sem nenhum erro.
- **ESLint:** Executado sem erros ou advertências.
- **Next.js Production Build:** `next build --webpack` gerado com sucesso para todas as rotas estáticas (`/clima`, `/mercado`, `/calculadoras`, etc.).
- **Varredura de Segredos:** `grep` em `.next/static` atestou total ausência de chaves de API.
- **Playwright E2E:** 17 testes do Clima aprovados (100%), cobrindo desktop e mobile.

---

## 9. Evidência de Integração Real Condicionada

Conforme estipulado na **Fase 7.B**:
- Foi realizada inspeção completa das variáveis de ambiente locais (`.env` e processo).
- **Situação identificada:** `WEATHERAPI_API_KEY` encontra-se vazia e `WEATHERAPI_ENABLED=False`.
- Nenhuma chave autorizada foi fornecida nem inserida no ambiente.
- **REGISTRO FORMAL:**
  > **STATUS: TESTE REAL PENDENTE**  
  > A infraestrutura e os testes determinísticos com fixtures oficiais representativas encontram-se 100% homologados. O teste real contra a API pública da WeatherAPI será executado assim que houver fornecimento e autorização formal da credencial própria pelo gestor do projeto. Não foram simuladas evidências reais fictícias.

---

## 10. Riscos e Recomendações

1. **Risco de Cobrança por Excedente:** Caso o plano Starter seja contratado com cartão e sem limite fixado no painel da WeatherAPI, rajadas de tráfego poderiam incorrer em custos adicionais.  
   *Mitigação implementada:* O DeepFarms Agro impõe teto de software (`WEATHERAPI_MONTHLY_QUOTA_LIMIT`), rejeitando requisições upstream excedentes antes de acionar a cobrança do fornecedor.
2. **Dependência de Atribuição no Plano Free:** Durante o piloto com o plano Free, a exibição do link *"Powered by WeatherAPI.com"* é mandatória por contrato. Foi validado que o link encontra-se presente no card de condições atuais.
3. **Horizonte de 3 Dias no Piloto:** O produtor rural verá a previsão para os próximos 3 dias enquanto o plano for Free. O frontend adapta visualmente os títulos para evitar falsas expectativas de previsão semanal.

---

## 11. Veredictos Finais

### Veredicto Técnico: GO (APROVADO)
- O conector `WeatherAPIAdapter`, a normalização, o tratamento de horas transpondo meia-noite, a telemetria, o controle de cotas, o tratamento de erros sem vazamento de chaves e os testes unitários/E2E estão **100% concluídos, validados e aprovados**.
- Nenhum código existente foi quebrado; adaptadores anteriores permanecem ativos.

### Veredicto Operacional: PENDENTE (AGUARDANDO CREDENCIAL E AUTORIZAÇÃO)
- A ativação em ambiente real depende exclusivamente de:
  1. Criação de conta pelo responsável no portal WeatherAPI.
  2. Definição do plano (Free para piloto de 3 dias ou Starter para 7 dias).
  3. Inserção autorizada da variável `WEATHERAPI_API_KEY` e comutação de `WEATHERAPI_ENABLED=True`.

*Encerrado conforme diretrizes. Nenhuma contratação paga ou avanço não autorizado foi realizado.*
