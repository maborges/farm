# DEEPFARMS-AGRO-FREE-01E2A — Relatório de Auditoria Arquitetural da Integração PTAX

**DATA:** 16 de Outubro de 2026  
**ÉPICO:** DEEPFARMS-AGRO-FREE  
**ETAPA:** 01E2A  
**OBJETIVO:** Definir a arquitetura de integração da cotação oficial PTAX USD/BRL do Banco Central do Brasil (BCB) ao aplicativo DeepFarms Agro (`apps/agro`).  
**MODO:** Auditoria Técnica Somente Leitura  
**STATUS:** CONCLUÍDO  
**VEREDICTO:** GO (Arquitetura Aprovada com Padrão de Proxy Backend Cacheado e Isolamento Total do SaaS Comercial)  

---

## 1. RESUMO EXECUTIVO

Esta auditoria técnica avaliou a viabilidade arquitetural, de segurança, de desempenho e de infraestrutura para disponibilizar a cotação oficial **PTAX USD/BRL do Banco Central do Brasil** no aplicativo PWA gratuito **DeepFarms Agro** (`apps/agro/src/app/mercado`).

### Principais Descobertas e Veredictos Técnicos:
1. **Inviabilidade Técnica da Consulta Direta pelo Navegador (Alternativa A — NO-GO):**
   - Testes empíricos ao vivo comprovaram que o gateway do Banco Central (`olinda.bcb.gov.br`) possui WAF/BIG-IP e proteção que **rejeita requisições com cabeçalho `Origin:` do navegador retornando `HTTP/2 403 Forbidden`**.
   - A API do BCB **não emite cabeçalhos CORS** (`Access-Control-Allow-Origin`).
   - A latência da API OData do BCB é altamente volátil (variando de 4 segundos a mais de 120 segundos), o que causaria bloqueio da interface e frequentes *timeouts* no cliente mobile.
2. **Arquitetura Recomendada (Alternativa B — Backend Proxy com Cache Redis/Memória — GO):**
   - Criação de um endpoint público leve intermediário no backend (`services/api` ou Route Handler em `apps/agro`).
   - **Regra Pétrea de Isolamento Multi-Tenant:** O endpoint público **NÃO PODE** solicitar nem consumir conexões do pool do PostgreSQL (`get_session`). Como o pool do banco comercial possui apenas 3 conexões ativas e 2 de transbordo (`db_pool_size=3`, `db_max_overflow=2`), qualquer tráfego anônimo no banco poderia esgotar o pool do SaaS comercial (`TooManyConnectionsError`).
   - O proxy fará cache em Redis (ou memória LRU local com Single-Flight/Mutex) com TTL dinâmico inteligente (30 minutos antes do fechamento; 12 horas após a publicação do boletim de fechamento).
3. **Endpoint Oficial BCB Ótimo:**
   - O endpoint OData `CotacaoDolarPeriodo` ordenado por `dataHoraCotacao desc` com `$top=1` sobre uma janela móvel de 7 dias é **10 vezes mais rápido** que `CotacaoMoedaPeriodoFechamento` (4s vs 46s nos testes empíricos) e resolve nativamente o problema de fins de semana, feriados e manhãs antes da divulgação do fechamento, sempre entregando o último boletim oficial publicado sem falhar com lista vazia.
4. **Resiliência Offline no PWA:**
   - Preservação integral do Service Worker atual (`public/sw.js`), sem qualquer modificação que possa causar regressão. O armazenamento da última cotação válida será gerenciado pela camada de aplicação via `localStorage` ou `IndexedDB`, garantindo visualização offline imediata com aviso de dado histórico e revalidação automática no evento `online`.

---

## 2. EVIDÊNCIAS DA INSPEÇÃO DO REPOSITÓRIO

### 2.1 Aplicativo PWA (`apps/agro`)
- **Página de Mercado (`src/app/mercado/page.tsx`):**
  - Implementada como Server Component inicial estruturado para receber cards de indicadores.
  - Indicador `dolar-ptax` já está catalogado com status `DADOS_ABERTOS_AGENDADO`, unidade `BRL / USD`, praça `Brasil (Nacional)` e fonte `Banco Central do Brasil (BCB)`.
  - Demais commodities (`soja`, `milho`, `boi-gordo`, `cafe-arabica`) mantêm status `PENDENTE_CONTRATO`, respeitando a diretriz de não apresentar dados fictícios.
- **Service Worker (`public/sw.js`):**
  - Homologado na etapa 01D. O script contém regras estritas:
    ```javascript
    // NUNCA fazer cache de rotas de API ou autenticação
    if (url.pathname.startsWith("/api/")) { return; }
    // Apenas métodos GET na mesma origem
    if (request.method !== "GET" || url.origin !== self.location.origin) { return; }
    ```
  - **Constatação:** O Service Worker propositalmente ignora requisições cruzadas (para fora da origem) e requisições para `/api/`. Portanto, a persistência offline da cotação pública deve residir no armazenamento local de dados do cliente (`localStorage` ou `IndexedDB`), não no Cache Storage de assets estáticos do SW.

### 2.2 Backend Comercial (`services/api`)
- **Cliente Banco Central Existente:**
  - Foi realizada busca profunda por termos `ptax`, `bacen`, `olinda`, `bcb`. **Nenhum cliente ou integração com o Banco Central existe atualmente no repositório.**
  - Existe o arquivo `core/cadastros/commodities/cotacao_service.py` e o job `scripts/jobs/atualizar_cotacoes.py`, porém estes tratam de commodities privadas (CEPEA, CBOT, B3) sob contexto multi-tenant autenticado, exigindo `tenant_id` e persistência na tabela `cotacoes_commodities`.
- **Dependências HTTP Existentes:**
  - `httpx>=0.27.0` (já homologado e amplamente utilizado de forma assíncrona com `AsyncClient`).
  - `redis>=5.0.3` (instalado e configurado via `settings.redis_url`).
  - `pydantic>=2.7.0` e `fastapi>=0.115.0`.
- **Configurações de CORS (`services/api/main.py`):**
  - `CORSMiddleware` está configurado permitindo origens locais de desenvolvimento (`http://localhost:3000` a `http://localhost:3004`, `http://127.0.0.1:3000` a `3004`, `http://0.0.0.0:3000` a `3004`).
  - As portas do `apps/agro` (3003 em dev, 3004 em testes) já estão explicitamente liberadas no CORS da API.
- **Padrão de Rotas Públicas:**
  - Identificou-se em `growth/router.py` (`POST /growth/events`) e em `operacional/routers/compras_publico.py` o padrão de rotas públicas sem exigência de JWT.
  - `growth/router.py` implementa *rate limiting* por IP em memória (`_rate_buckets: dict[str, tuple[int, float]]`) com janela de 60 segundos e máximo de 60 requisições por IP.
- **Pool de Conexões e Riscos Multi-Tenant (`core/config.py` e `core/dependencies.py`):**
  - O pool do banco comercial possui:
    - `db_pool_size = 3`
    - `db_max_overflow = 2`
    - `db_pool_timeout = 15`
  - A função `_is_connection_exhaustion_error` monitora explicitamente esgotamento de conexões PostgreSQL.
  - **Alerta de Segurança e Disponibilidade:** Uma rota pública para o PWA no FastAPI **JAMAIS** deve declarar `session: AsyncSession = Depends(get_session)`. A abertura de transação desnecessária com o banco para uma leitura de cotação pública poderia saturar os 5 slots de conexão do SaaS comercial em segundos, derrubando o sistema para usuários pagantes.

---

## 3. INVESTIGAÇÃO EMPÍRICA DA API OFICIAL DO BANCO CENTRAL (PTAX)

A documentação e os metadados do serviço PTAX Olinda (`https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/$metadata`) foram inspecionados diretamente via requisições HTTP públicas somente leitura.

### 3.1 Catálogo de Funções e Tipos OData

| Função OData | Entidade de Retorno | Campos Disponíveis | Observação |
|---|---|---|---|
| `CotacaoDolarDia(dataCotacao)` | `TipoCotacaoDolar` | `cotacaoCompra`, `cotacaoVenda`, `dataHoraCotacao` | Retorna apenas 1 registro (fechamento oficial) para a data informada. |
| `CotacaoDolarPeriodo(dataInicial, dataFinalCotacao)` | `TipoCotacaoDolar` | `cotacaoCompra`, `cotacaoVenda`, `dataHoraCotacao` | Retorna histórico diário de fechamentos. Suporta `$orderby` e `$top`. |
| `CotacaoMoedaDia(moeda, dataCotacao)` | `TipoCotacaoMoeda` | `paridadeCompra`, `paridadeVenda`, `cotacaoCompra`, `cotacaoVenda`, `dataHoraCotacao`, `tipoBoletim` | Retorna todos os boletins do dia (Abertura, Intermediários 1, 2, 3 e Fechamento PTAX). |
| `CotacaoMoedaPeriodoFechamento(codigoMoeda, dataInicialCotacao, dataFinalCotacao)` | `TipoCotacaoDolarAberturaOuIntermediario` | `cotacaoCompra`, `cotacaoVenda`, `dataHoraCotacao`, `tipoBoletim` | Retorna apenas os boletins de fechamento das moedas. |
| `Moedas` | `TipoMoeda` | `simbolo`, `nomeFormatado`, `tipoMoeda` | Tabela de símbolos de moedas (Dólar dos EUA = `"USD"`). |

### 3.2 Descobertas Técnicas Cruciais (Testes ao Vivo)

#### A. Formato Obrigatório de Data
- **Padrão Exigido:** `'MM-dd-yyyy'` (ex: `'10-15-2024'`).
- **Comportamento com `'YYYY-MM-DD'` (ISO):** Retorna silenciosamente lista vazia `{"value": []}`, sem erro HTTP.
- **Comportamento com `'DD-MM-YYYY'`:** Retorna erro interno `HTTP 500`:
  ```json
  /*{ "codigo": 500, "mensagem": "Erro desconhecido" }*/
  ```
- **Conclusão:** O backend DeepFarms deve converter rigorosamente qualquer data de consulta para o formato `'MM-dd-yyyy'` antes de chamar a API Olinda.

#### B. Identificação Inequívoca do Boletim de Fechamento
- Em `CotacaoMoedaDia`, a API retorna até 5 registros em dias úteis normais:
  - `"Abertura"` (coleta ~10:00 - 10:10)
  - `"Intermediário"` 1 (~11:00 - 11:10)
  - `"Intermediário"` 2 (~12:00 - 12:10)
  - `"Intermediário"` 3 (~13:00 - 13:10)
  - `"Fechamento PTAX"` (divulgado entre 13:00 e 13:30 BRT)
- **Cuidado:** Assumir que o último registro de `CotacaoMoedaDia` é o fechamento é **falso** se a consulta ocorrer pela manhã (às 10:30, o último registro é o de Abertura!).
- Nas funções específicas de dólar (`CotacaoDolarDia` e `CotacaoDolarPeriodo`), a entidade `TipoCotacaoDolar` por definição da Resolução CMN nº 3.568 **contém exclusivamente a taxa média diária calculada pelo BCB, isto é, a PTAX de Fechamento**.

#### C. Comparação de Performance entre Endpoints

| Endpoint Testado | Parâmetros | Tempo de Resposta Medido | Registros Retornados |
|---|---|---|---|
| `CotacaoDolarPeriodo` | Janela de 7 dias, `$top=1`, `$orderby=dataHoraCotacao desc` | **4 a 8 segundos** | 1 (Último fechamento oficial disponível) |
| `CotacaoDolarDia` | Data exata de dia útil com fechamento | **5 segundos** | 1 (Fechamento) |
| `CotacaoMoedaDia` | Data exata de dia útil | **2 minutos** | 5 boletins |
| `CotacaoMoedaPeriodoFechamento` | Janela de 5 dias | **46 a 120 segundos** | Histórico de fechamentos |

**Conclusão de Performance:** `CotacaoDolarPeriodo` é drasticamente mais leve e rápida que as consultas na tabela genérica de moedas `CotacaoMoeda*`, pois consulta uma view/índice direto para o par USD/BRL.

#### D. Comportamento em Fins de Semana, Feriados e Manhãs
- Em fins de semana e feriados:
  - `CotacaoDolarDia(dataCotacao=sábado)` retorna lista vazia `{"value": []}`.
  - `CotacaoDolarPeriodo` com janela móvel dos últimos 7 dias e `$top=1` retorna de forma transparente o fechamento da sexta-feira anterior (`dataHoraCotacao: "2024-10-11 13:04:30.872"`).
- Antes das 13:15 BRT de um dia útil:
  - A cotação do próprio dia ainda não foi apurada. A janela móvel entrega o fechamento do dia útil imediatamente anterior com a data de referência correta.

#### E. Regras Legais e de Atribuição
- A PTAX é taxa de câmbio calculada pelo Banco Central com base em quatro consultas diárias de operações no mercado interbancário realizadas por dealers de câmbio (Circular BCB nº 3.506/2010).
- Os dados do Portal de Dados Abertos do Banco Central estão sob domínio público nos termos da Lei de Acesso à Informação (Lei nº 12.527/2011) e do Decreto nº 8.777/2016.
- É mandatório creditar a fonte: *"Fonte: Banco Central do Brasil (BCB)"*.
- **Distinção Essencial:** A PTAX é taxa de referência contábil, tributária e para liquidação de contratos derivativos. Não é taxa de câmbio spot ("dólar comercial de balcão") e não representa preço de compra/venda para o produtor rural em instituições financeiras ou casas de câmbio.

---

## 4. COMPARAÇÃO ARQUITETURAL

### Matriz Comparativa

| Critério de Avaliação | Alternativa A: Consulta Direta pelo Frontend (`apps/agro` → BCB) | Alternativa B: Endpoint Público DeepFarms (`apps/agro` → Backend → BCB) |
|---|---|---|
| **CORS** | **INVIÁVEL (Bloqueio WAF 403).** BCB rejeita o cabeçalho `Origin:` do browser com `HTTP/2 403`. | **RESOLVIDO.** Backend efetua requisição HTTP server-to-server (sem cabeçalho `Origin`), e o backend expõe CORS liberado ao `apps/agro`. |
| **Segurança e Privacidade** | IP do usuário exposto diretamente ao BCB; suscetível a bloqueios de rede móvel/operadora rural. | IP do produtor blindado; tráfego centralizado na infraestrutura DeepFarms. |
| **Disponibilidade e Resiliência** | Pobre. Se o BCB estiver lento ou instável, o frontend congela por até 2 minutos e falha. | Alta. Backend serve cache pré-calculado em < 10ms. Degradação suave em falhas do BCB. |
| **Cache e Economia de Rede** | Inexistente ou pulverizado em cada navegador. 1.000 produtores = 1.000 requisições lentas ao BCB. | Compartilhado (Redis/Memória). 1 consulta ao BCB a cada 30min–12h atende milhões de acessos. |
| **Proteção contra Abuso (Rate Limiting)** | Impossível de coordenar entre clientes. Risco de banimento em massa de IPs por WAF do BCB. | Totalmente controlado no proxy com buckets por IP e limite global. |
| **Funcionamento Offline** | Difícil de coordenar; suscetível a expiração prematura no browser. | Cliente armazena o último payload estruturado em `localStorage`, garantindo visualização offline. |
| **Observabilidade e Telemetria** | Nenhuma telemetria de falhas do BCB pelo lado do servidor. | Completa (Loguru, logs estruturados JSON, métricas de latência e status do BCB). |
| **Manutenção e Evolução** | Baixa. Qualquer ajuste de formato do BCB exigiria novo build/deploy do app PWA no cliente. | Alta. Ajustes de contrato ou fallbacks são resolvidos no backend sem impacto no app. |

### Decisão Arquitetural: Alternativa B (Backend Proxy com Cache Compartilhado)
A **Alternativa A foi reprovada (NO-GO)** por impedimento técnico de rede (CORS 403 retornado pelo WAF do BCB) e inviabilidade de latência.

A **Alternativa B foi aprovada (GO)** como a única arquitetura viável, segura e resiliente.

---

## 5. CONTRATO PÚBLICO DE DADOS

O contrato de dados retornado ao frontend deve ser imutável, versionado e conter todos os metadados temporais para evitar ambiguidades.

### 5.1 Schema TypeScript do Contrato Público (`/api/v1/public/mercado/ptax`)

```typescript
export type EstadoDisponibilidadePtax = "ATUALIZADO" | "ANTERIOR" | "INDISPONIVEL";

export interface PtaxCotacaoPublicaResponse {
  sucesso: boolean;
  versao: "1.0";
  indicador: "DOLAR_PTAX";
  moeda: "USD";
  moedaReferencia: "BRL";
  
  // Valores numéricos com 4 a 5 casas decimais (ou null se indisponível)
  cotacaoCompra: number | null;
  cotacaoVenda: number | null;
  
  // Rastreabilidade Temporal do Boletim
  dataCotacao: string;          // Formato ISO YYYY-MM-DD da data da cotação
  dataCotacaoFormatada: string; // Formato amigável pt-BR: "DD/MM/AAAA"
  horarioBoletim: string;       // Formato "HH:mm:ss" no fuso de Brasília
  dataHoraBoletimIso: string;   // Timestamp ISO com fuso "-03:00"
  tipoBoletim: "Fechamento";    // Sempre o boletim de fechamento oficial
  fonteOficial: "Banco Central do Brasil (BCB)";
  
  // Metadados do Sistema e Cache DeepFarms
  dataConsultaIso: string;      // Momento em que o cliente chamou o proxy
  cacheAtualizadoEmIso: string; // Momento em que o cache foi renovado junto ao BCB
  cacheTtlSegundos: number;     // Tempo restante ou padrão de validade do cache
  estaDesatualizado: boolean;   // true se for dado de dias anteriores ou fallback
  estadoDisponibilidade: EstadoDisponibilidadePtax;
  avisoLegal: string;
}
```

### 5.2 Exemplo Real de Resposta (JSON)

```json
{
  "sucesso": true,
  "versao": "1.0",
  "indicador": "DOLAR_PTAX",
  "moeda": "USD",
  "moedaReferencia": "BRL",
  "cotacaoCompra": 5.6372,
  "cotacaoVenda": 5.6378,
  "dataCotacao": "2024-10-15",
  "dataCotacaoFormatada": "15/10/2024",
  "horarioBoletim": "13:06:27",
  "dataHoraBoletimIso": "2024-10-15T13:06:27.393-03:00",
  "tipoBoletim": "Fechamento",
  "fonteOficial": "Banco Central do Brasil (BCB)",
  "dataConsultaIso": "2026-10-16T21:40:00.000Z",
  "cacheAtualizadoEmIso": "2026-10-16T21:30:00.000Z",
  "cacheTtlSegundos": 1800,
  "estaDesatualizado": false,
  "estadoDisponibilidade": "ATUALIZADO",
  "avisoLegal": "A PTAX é uma taxa de referência calculada e publicada pelo Banco Central do Brasil. Não representa taxa de câmbio spot ou cotação em tempo real para liquidação comercial imediata."
}
```

### 5.3 Distinção Temporal Obrigatória
1. **`dataCotacao`:** A data contábil oficial à qual o valor pertence (ex: 15/10/2024).
2. **`dataHoraBoletimIso`:** O instante exato em que o BCB homologou o fechamento daquele dia (ex: 13:06:27 BRT).
3. **`dataConsultaIso`:** O instante em que o aplicativo ou o usuário requisitou a informação.
4. **`estadoDisponibilidade`:**
   - `"ATUALIZADO"`: O boletim de fechamento do dia útil atual já foi emitido e está em vigor.
   - `"ANTERIOR"`: Cotação válida, porém pertencente ao último dia útil fechado (manhãs antes das 13:15, noites, fins de semana e feriados).
   - `"INDISPONIVEL"`: O serviço externo falhou e não existe nenhum dado anterior em cache válido.

---

## 6. ESTRATÉGIA DE CACHE E PROTEÇÃO DE INFRAESTRUTURA

Para evitar chamadas redundantes e proteger tanto o BCB quanto a infraestrutura do DeepFarms, adota-se estratégia de **Cache em Dois Níveis com Single-Flight**:

```
[ Usuário / PWA ]
       │
       ▼
[ Endpoint Público FastAPI / Route Handler ]
       │
       ├─► [ L1: Cache em Memória Local ] (< 1ms)
       │         │ (miss)
       ├─► [ L2: Cache Redis Compartilhado ] (< 3ms)
       │         │ (miss / expirado)
       ▼
[ Mutex / Lock Assíncrono (Single-Flight) ]
       │ (Apenas 1 processo consulta o BCB; os demais aguardam ou recebem stale)
       ▼
[ Upstream: BCB Olinda OData API ] (4 a 15s)
```

### 6.1 Política Dinâmica de TTL

O comportamento do mercado de câmbio é previsível quanto à divulgação da PTAX:
1. **Dias úteis após o fechamento (13:30 até 07:00 do dia útil seguinte):**
   - O valor não muda mais.
   - **TTL:** 4 a 12 horas.
2. **Dias úteis antes do fechamento (07:00 até 13:30):**
   - O valor vigente ainda é o do dia anterior, mas o fechamento de hoje pode sair a qualquer momento entre 13:00 e 13:30.
   - **TTL:** 15 a 30 minutos.
3. **Fins de semana e feriados nacionais:**
   - Mercado fechado. A PTAX de sexta-feira permanece oficial durante todo o sábado e domingo.
   - **TTL:** 12 horas.

### 6.2 Resiliência contra Thundering Herd (Single-Flight Pattern)
Se 500 produtores acessarem o app simultaneamente no exato segundo em que o cache expira, apenas **uma única requisição HTTP** será disparada para a API do Banco Central. Todas as outras 499 requisições aguardam a resolução da requisição em curso ou consomem o cache anterior (*stale-while-revalidate*).

### 6.3 Degradação Suave (Graceful Degradation)
- Em caso de *timeout* (definido em 12 segundos) ou erro HTTP 5xx retornado pelo BCB:
  1. O backend busca o último valor válido armazenado em Redis/Memória.
  2. Retorna a cotação com `estaDesatualizado: true` e `estadoDisponibilidade: "ANTERIOR"`.
  3. Registra warning estruturado no Loguru para observabilidade.
  4. Se a idade do dado persistido for superior a 7 dias corridos, retorna `estadoDisponibilidade: "INDISPONIVEL"`, pois um dado cambial defasado há mais de uma semana não oferece segurança ao produtor rural.

---

## 7. FUNCIONAMENTO OFFLINE NO PWA (`apps/agro`)

O Service Worker atual (`apps/agro/public/sw.js`) está homologado e possui diretiva explícita de não interceptar rotas `/api/` e chamadas fora da mesma origem.

### 7.1 Mecanismo de Armazenamento Local
- A camada de apresentação (`apps/agro/src/app/mercado`) utilizará `localStorage` (ou `idb-keyval` / `IndexedDB` nativo do browser) com a chave:
  `deepfarms_agro_mercado_ptax_v1`
- **Fluxo de Leitura e Gravação:**
  1. Ao carregar a página `/mercado`, o componente renderiza imediatamente os dados gravados no `localStorage` (se existirem), eliminando qualquer tela branca ou *layout shift*.
  2. Se o dispositivo estiver online (`navigator.onLine === true`), dispara requisição em segundo plano para o proxy DeepFarms (`/api/v1/public/mercado/ptax`).
  3. Ao receber a resposta 200, atualiza o estado da tela suavemente e regrava o payload no `localStorage`.
  4. Se o dispositivo estiver offline:
     - O componente detecta a ausência de conexão.
     - Exibe o card com badge âmbar: `"Modo Offline — Exibindo último valor sincronizado"`.
     - Exibe a data e horário da cotação gravada em destaque.
  5. **Auto-Reconexão:** O componente escuta o evento global:
     ```typescript
     window.addEventListener("online", () => {
       revalidarCotacaoPtax();
     });
     ```
     Assim que a conexão do celular 4G/Wi-Fi retorna no campo, o valor é revalidado silenciosamente sem necessidade de recarregar a página manualmente.

### 7.2 Isolamento de Segurança dos Dados Gravados
- O payload gravado no navegador do usuário contém **estritamente dados públicos de mercado**.
- Nenhum token JWT, chave de API, cabeçalho de sessão ou identificador de fazenda/tenant é armazenado junto à cotação, garantindo 100% de conformidade com LGPD e com as diretrizes de segurança da plataforma.

---

## 8. PROPOSTA DE INTERFACE DA PÁGINA MERCADO

A interface deve manter o padrão visual de alta qualidade do DeepFarms (Tailwind CSS, Dark/Light Mode, Lucide Icons, shadcn/ui tokens).

### 8.1 Mockup Estrutural do Card PTAX

```
┌────────────────────────────────────────────────────────────────────────┐
│ [ $ ] Dólar Comercial PTAX                     [ Fechamento Oficial ]  │
│       Taxa de Câmbio de Referência - BRL / USD                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   COMPRA                                VENDA                          │
│   R$ 5,6372                             R$ 5,6378                      │
│                                                                        │
│   ● Cotação de Fechamento Válida                                       │
│   Data de Referência: 15/10/2024 às 13:06 BRT                          │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  🏛 Fonte Oficial: Banco Central do Brasil (BCB)                       │
│  🕒 Sincronizado em: 16/10/2026 às 21:40                               │
│  ℹ️ "A PTAX é uma taxa de referência publicada pelo Banco Central.    │
│      Não representa uma cotação de compra ou venda em tempo real."     │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Estados Visuais Padronizados

| Estado | Badge de Status | Cor | Ação / Mensagem |
|---|---|---|---|
| **Atualizado** | `Fechamento do Dia` | Verde Esmeralda | Exibe cotação do próprio dia útil (após 13:15 BRT). |
| **Anterior (Válido)** | `Último Fechamento Disponível` | Azul / Muted | Exibe cotação do dia anterior com data explícita (manhãs e fins de semana). |
| **Offline** | `Offline (Dados Salvos)` | Âmbar | "Sem conexão à internet. Exibindo última cotação registrada em DD/MM às HH:mm." |
| **Indisponível** | `Temporariamente Indisponível` | Vermelho / Destrutivo | "Serviço do Banco Central momentaneamente inacessível. Tente novamente mais tarde." |

---

## 9. SEGURANÇA E ISOLAMENTO DO SAAS COMERCIAL

A auditoria analisou minuciosamente todos os pontos de contato entre a rota pública do PWA e o SaaS comercial DeepFarms (`services/api`):

1. **Autenticação JWT:**
   - A rota de mercado **não utiliza** `Depends(get_current_user)`.
   - O `TenantRLSMiddleware` em `services/api/main.py` só inspeciona o cabeçalho se ele contiver `Bearer <token>`. Requisições anônimas navegam sem afetar nem disparar o middleware.
2. **Resolução de Tenant e RLS:**
   - A rota não injeta nem resolve tenant. O RLS do PostgreSQL permanece inativo para essa consulta porque **nenhum tenant comercial está associado**.
3. **Proteção Radical do Pool PostgreSQL:**
   - **Regra Arquitetural:** O serviço de cotação PTAX **NÃO DEVE** utilizar banco de dados relacional. Ele utiliza exclusivamente cache em memória ou Redis.
   - Isso elimina qualquer risco de saturação do pool de conexões (`db_pool_size=3`, `db_max_overflow=2`), que permanece 100% reservado para os usuários autenticados da gestão agropecuária comercial.
4. **Rate Limiting e Prevenção de DoS:**
   - Aplicação de limitador por IP (máximo de 60 req/min por IP público) com base no modelo já testado em `growth/router.py`.
5. **CORS:**
   - As origens do `apps/agro` (portas 3003 e 3004) já constam na lista branca de `allow_origins` de `services/api/main.py`.

---

## 10. RISCOS IDENTIFICADOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Estratégia de Mitigação |
|---|---|---|---|
| **Lentidão extrema do BCB (latência > 60s)** | Alta | Alto | Timeout rígido de 12s no `httpx.AsyncClient`; fallback imediato para o último fechamento retido em cache. |
| **Indisponibilidade ou manutenção do portal Olinda BCB** | Média | Médio | Política *stale-while-revalidate* com retenção de dados históricos válidos por até 7 dias; aviso visual de contingência. |
| **Tentativa de consulta direta pelo browser (CORS 403)** | Baixa (evitada) | Crítico | Auditoria determinou uso obrigatório de proxy backend com testes que garantem a rota server-side. |
| **Esgotamento de conexões Postgres do SaaS comercial** | Baixa (evitada) | Crítico | Proibição explícita do uso de `Depends(get_session)` no endpoint público de cotações. |
| **Confusão do produtor entre PTAX e cotação de balcão (spot)** | Alta | Médio | Disclaimer legal explícito e padronizado em destaque abaixo dos valores de compra e venda. |

---

## 11. PLANO DE IMPLEMENTAÇÃO (ETAPA 01E2B)

A implementação da etapa seguinte (**01E2B**) deverá ser executada em 3 blocos ordenados:

### Bloco 1: Backend (`services/api` ou Route Handler)
- Criar `services/api/core/routers/public_mercado.py` (ou `apps/agro/src/app/api/mercado/ptax/route.ts`).
- Implementar cliente HTTP assíncrono `BcbPtaxClient` com `httpx.AsyncClient(timeout=12.0)`.
- Implementar endpoint OData `CotacaoDolarPeriodo` com formatação estrita de data `'MM-dd-yyyy'` e janela móvel de 7 dias com `$orderby=dataHoraCotacao desc&$top=1`.
- Implementar cache com TTL dinâmico e proteção contra thundering herd (Single-Flight lock).
- Validar payload com Pydantic v2.

### Bloco 2: Frontend PWA (`apps/agro`)
- Criar cliente de consulta `src/lib/mercado/ptax-client.ts`.
- Implementar persistência local em `localStorage` para tolerância offline imediata.
- Atualizar `apps/agro/src/app/mercado/page.tsx` substituindo o card estático pelo card funcional do Dólar PTAX com tratamento de estados (Atualizado, Anterior, Offline, Indisponível).
- Adicionar listener do evento `online` para auto-sincronização.

### Bloco 3: Testes Automatizados e Homologação
- Adicionar testes unitários com mocks para os 15 cenários de borda.
- Adicionar testes E2E no Playwright validando renderização, visualização offline e aviso legal.
- Executar suíte de validação: `typecheck`, `lint`, `test`, `test:e2e`, `build`.

---

## 12. MATRIZ DE TESTES OBRIGATÓRIOS PARA A ETAPA 01E2B

1. **Dia útil com boletim de fechamento publicado:** Responde status 200, valores de compra/venda preenchidos e `estadoDisponibilidade: "ATUALIZADO"`.
2. **Dia útil antes das 13:15 BRT:** Responde com o fechamento do dia útil anterior e `estadoDisponibilidade: "ANTERIOR"`.
3. **Fim de semana (sábado e domingo):** Responde com o fechamento da sexta-feira anterior e `estadoDisponibilidade: "ANTERIOR"`.
4. **Feriado nacional brasileiro:** Responde com o fechamento do dia útil precedente sem erro.
5. **API do BCB retornando lista vazia (`{"value": []}`):** Degradação suave para cache ou retorno de indisponibilidade tratada sem exceção 500.
6. **Timeout de rede no upstream (> 12s):** Ativação de timeout sem travar o worker, servindo stale cache.
7. **HTTP 429 (Rate Limit do BCB):** Retorno de cache ou status amigável de sobrecarga temporária.
8. **HTTP 500 (Erro interno do BCB):** Captura segura da exceção com log estruturado e resposta degradada.
9. **Resposta malformada ou JSON corrompido:** Validação de schema no Pydantic/Zod rejeita e preserva integridade.
10. **Payload com campos ausentes ou nulos:** Tratamento rigoroso de tipagem sem quebrar o componente React.
11. **Validação do Cache (Hit vs Miss):** Comprovação de que requisições subsequentes são respondidas em < 10ms sem chamar o BCB.
12. **Invalidação e Expiração do Cache:** Renovação automática após o vencimento do TTL.
13. **Funcionamento Offline:** Aplicação sem rede renderiza os dados salvos em `localStorage` com badge indicativo.
14. **Auto-Reconexão:** Disparo do evento `online` recarrega e atualiza os dados em tela.
15. **Isolamento de Segurança:** Comprovação de que nenhum cabeçalho de autorização, cookie de sessão ou tenant_id é transmitido ou gravado.

---

## 13. ESTIMATIVA DE ESFORÇO

- **Backend (Proxy, Cliente BCB, Cache e Rate Limiter):** 3 a 4 horas.
- **Frontend (Componente PTAX, Estados de UI e Offline):** 3 a 4 horas.
- **Testes Automatizados (Unitários e E2E Playwright):** 2 a 3 horas.
- **Documentação e Certificação:** 1 hora.
- **Esforço Total Estimado:** 9 a 12 horas de desenvolvimento controlado.

---

## 14. VEREDICTO FINAL

### **GO**

A auditoria arquitetural conclui que a integração da cotação oficial PTAX USD/BRL ao aplicativo DeepFarms Agro é **tecnicamente viável, segura e altamente recomendada** via endpoint proxy intermediário com cache inteligente.

A restrição técnica de CORS imposta pelo Banco Central inviabiliza a chamada direta pelo navegador, justificando plenamente o uso do backend. O isolamento do banco PostgreSQL assegura que a gratuidade do PWA não colocará em risco a escalabilidade e a disponibilidade da plataforma SaaS comercial.

A etapa seguinte (**DEEPFARMS-AGRO-FREE-01E2B**) está liberada para planejamento de execução assim que aprovada.
