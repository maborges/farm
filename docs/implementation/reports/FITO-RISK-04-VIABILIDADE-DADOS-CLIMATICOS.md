# FITO-RISK-04 — Viabilidade dos dados climáticos históricos

**Data:** 2026-10-30
**Escopo:** inventário de código e documentação oficial dos provedores. Nenhuma sincronização, consulta a banco, mudança de configuração, assinatura ou alteração de código foi realizada.

## 1. Conclusão executiva

Há fontes capazes de oferecer os campos meteorológicos retrospectivos, mas o pipeline atual do DeepFarms não as coleta como histórico diário utilizável. A integração de persistência OpenWeather usa endpoints de clima atual e previsão, e grava um snapshot por dia; os adaptadores WeatherAPI e Open-Meteo encontrados na aplicação servem previsão para o clima público, não alimentam `RegistroClima`. O repositório não contém integração INMET.

Para preparar dados de validação retrospectiva, a alternativa mínima recomendada é baixar os arquivos históricos horários das estações automáticas do **INMET**, mapear cada lavoura para estações representativas e processar a série fora do banco de produção, preservando origem, hora UTC, lacunas e qualidade. O INMET publica dados horários anuais das estações automáticas desde 2000. Isso fornece observações de estação, mas não garante cobertura próxima de cada unidade nem qualidade sem tratamento. [Dados históricos anuais do INMET](https://portal.inmet.gov.br/dadoshistoricos/), [BDMEP](https://bdmep.inmet.gov.br/)

**Veredicto: GO COM RESSALVAS para avançar à preparação de uma base histórica de validação; NO-GO para homologar o modelo ou expor o cálculo fitossanitário.** Primeiro é necessário confirmar cobertura das estações, definições diárias e dados faltantes. Esta conclusão não altera o NO-GO de implementação científica do FITO-RISK-03.

## 2. Inventário do repositório

| Provedor | Evidência no código | Função atual | Alimenta histórico fitossanitário? |
|---|---|---|---|
| **OpenWeather** | `services/api/integracoes/openweather/{services.py,worker.py}`; `services/api/public_clima/adapters.py`; `services/api/core/config.py` | Integração de tenant consulta `/data/2.5/weather` e `/data/2.5/forecast`; adaptador público usa One Call 3.0 para clima atual/previsão | **Parcial e insuficiente.** O primeiro fluxo persiste snapshot atual; não consulta o histórico oficial nem guarda série horária. One Call 4.0, com timeline histórica, não está implementado. |
| **WeatherAPI** | `services/api/public_clima/adapters.py`, `dynamic_orchestrator.py`, `core/config.py`; credencial administrada em `core/services/platform_weather_credentials.py` | Adaptador público chama `forecast.json` e normaliza condições atuais e previsão; há verificação de conectividade por `forecast.json` | **Não.** O código consultado não chama `history.json` nem persiste dados WeatherAPI em `RegistroClima`. |
| **Open-Meteo** | `services/api/public_clima/adapters.py`, `dynamic_orchestrator.py`, `core/config.py` | Adaptador público chama `/v1/forecast`, retornando atual e previsão horária/diária; há guardas de autorização/licença para uso público | **Não.** Não foi encontrado cliente para `/v1/archive` nem ingestão do histórico em `RegistroClima`. |
| **INMET** | Busca de arquivos e módulos de provedores no repositório não encontrou cliente/integração meteorológica INMET | Fonte oficial externa, sem pipeline próprio no DeepFarms | **Não integrada.** Dados são acessados externamente por arquivos históricos e solicitação no BDMEP. |

`WEATHERAPI`, `OPENWEATHER` e `OPEN_METEO` aparecem na configuração do orquestrador público. Isso comprova código de adaptador/configuração, não comprova que chaves estejam configuradas, que a chamada esteja licenciada no ambiente, nem que aquele provedor gere registros históricos por tenant. Não foram lidos valores de `.env`, credenciais, cofres ou bancos.

## 3. Capacidades oficiais e limites

### OpenWeather

- **Implementado hoje no fluxo persistente:** clima atual no endpoint 2.5 e previsão de cinco dias em intervalos de três horas. Há dados de temperatura atual, umidade atual e precipitação reportada na janela do snapshot. Não há consulta retroativa nesse cliente.
- **Possibilidade atual do fornecedor:** One Call API 4.0 oferece timeline horária e diária com mais de 47 anos de histórico e previsão. A amostra documentada da timeline diária inclui temperatura mínima e umidade relativa (%); há também valores horários de temperatura e umidade. A timeline diária aceita paginação, com até 10 dias por resposta. A página de preços informa 1.000 chamadas/dia incluídas e `US$ 0,0015` por chamada adicional; chamadas paginadas contam separadamente. Assim, 60 dias em agregação diária exigiriam cerca de seis respostas por coordenada, antes de retries/limites, se a API e os termos atenderem ao caso. [One Call 4.0 e paginação diária](https://openweathermap.org/api/one-call-4), [preço One Call](https://openweathermap.org/price), [FAQ oficial sobre histórico e cobrança](https://openweathermap.org/faq)
- **Licença/uso:** a página de preço lista ODbL nos planos Weather API; a assinatura One Call 4.0 tem fluxo comercial próprio. Os termos de armazenamento, redistribuição, atribuição e eventual obrigação ODbL precisam ser confirmados no contrato aplicável antes de expor dados/derivados a clientes.
- **Aderência científica:** oferece mínima e RH média diárias, mas a compatibilidade da convenção diária e a metodologia/fonte que formam o histórico local precisam ser confirmadas para as datas/regiões do piloto. É dado de fornecedor/modelo, não a medição da estação Procafé que calibrou a regra.
- **Conclusão:** tecnicamente possível após novo adaptador/persistência e verificação de plano/termos, mas não reaproveita automaticamente a integração atual.

### WeatherAPI

- O `history.json` oficial fornece dados horários e diários a partir de 1º de janeiro de 2010, conforme o plano. No elemento diário documenta `mintemp_c` e `avghumidity`; os elementos horários incluem `humidity`. [History API oficial](https://www.weatherapi.com/docs/history-api/)
- A tabela oficial consultada lista: Free, 100 mil chamadas/mês, histórico de 1 dia; Starter, `US$ 7/mês`, 3 milhões/mês, 7 dias de histórico; Pro+, `US$ 25/mês`, 5 milhões/mês, 365 dias; Business, `US$ 65/mês`, 10 milhões/mês, histórico desde 2010; Enterprise sob consulta. A janela retrospectiva de 30–60 dias caberia no alcance Pro+ ou superior, **mas** o fornecedor esclarece que seu histórico é arquivo da previsão emitida, não observações meteorológicas reais. Se o limite mensal for excedido, chamadas deixam de ser atendidas até a renovação. [Preços, limites e natureza do histórico](https://www.weatherapi.com/pricing)
- O endpoint tem granularidade horária e diária, e os dados do plano são comercialmente disponibilizados segundo a tabela; condições específicas de armazenamento/redistribuição precisam ser verificadas nos termos contratuais.
- **Aderência científica:** não recomendado para reproduzir/validar retrospectivamente um modelo ajustado com observações, pois “histórico” aqui significa previsão arquivada. É adequado para verificar o desempenho histórico das previsões do próprio WeatherAPI, uma pergunta diferente.
- **Conclusão:** há endpoint e cobertura suficiente em planos pagos, mas sua semântica torna-o inadequado como fonte primária de clima observado para este piloto.

### Open-Meteo

- A API histórica oficial `/v1/archive` disponibiliza reanálise: ERA5 desde 1940 (0,25°), ERA5-Land desde 1950 (0,1°) e IFS desde 2017 (9 km). Expõe temperatura mínima diária, umidade relativa média diária e umidade relativa horária. A variável diária de RH está documentada como média; ainda é necessário comparar a convenção temporal/fuso da API com a do estudo científico antes de usá-la na regra. [Documentação do Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- A fonte é reanálise/modelagem que combina observações e modelos, não uma observação pontual feita na lavoura; a grade de ERA5-Land é aproximadamente 11 km, ERA5 aproximadamente 25 km. São boas séries espacialmente contínuas para avaliação de cobertura e comparação, mas não automaticamente equivalentes à estação próxima ou ao microclima do dossel.
- A licença dos dados é CC BY 4.0 com atribuição; porém o uso da API gratuita é limitado a fins não comerciais (10 mil chamadas/dia, 5 mil/hora, 600/minuto). Aplicação comercial requer assinatura. O plano Professional é o primeiro que inclui Historical Weather; a página oficial indica 5 milhões de chamadas/mês e custos fixos sem excedentes por chamada, mas o preço mensal não ficou exposto no conteúdo estático consultado. **Valor exato: NÃO CONFIRMADO; verificar no portal oficial antes de qualquer contratação.** Requests com mais de duas semanas ou muitas variáveis/localizações contam como múltiplas unidades de chamada. [Termos](https://open-meteo.com/en/terms), [planos e quotas](https://open-meteo.com/en/pricing)
- **Conclusão:** tecnicamente promissor para backfill espacial e comparação, com custo/licença comercial que deve ser aprovado e discrepância de natureza (reanálise versus estação observada).

### INMET — fonte pública oficial

- O portal do INMET publica pacotes anuais de dados horários das estações automáticas desde 2000. Para dados observados recentes, a carta de serviços indica atualização horária e acesso aos últimos 90 dias; o BDMEP é a porta de acesso às séries históricas. O portal disponibiliza arquivos para download sem tarifa indicada na página; não foi localizada licença nominal que esclareça redistribuição em produto comercial. [Arquivos anuais](https://portal.inmet.gov.br/dadoshistoricos/), [Estações automáticas — serviço INMET](https://portal.inmet.gov.br/servicos/esta%C3%A7%C3%B5es-autom%C3%A1ticas), [BDMEP](https://bdmep.inmet.gov.br/)
- A página de serviço oficial BDMEP também descreve séries diárias históricas de estações convencionais. A cobertura, período e variável disponível devem ser confirmados por estação. [BDMEP — dados históricos](https://portal.inmet.gov.br/servicos/bdmep-dados-hist%C3%B3ricos)
- **Variáveis:** os arquivos horários e o catálogo da estação devem ser inspecionados antes do uso para confirmar disponibilidade de temperatura e umidade, alterações de sensor, unidade, horário UTC e faltas. Temperatura mínima diária pode ser derivada do conjunto horário íntegro; RH média diária pode ser calculada de todas as medições válidas, documentando método. Para o modelo Hinnah, comparar esse método com a definição da fonte científica; não assumir automaticamente que toda série `RH` é a mesma média diária.
- **Custo/uso:** não há tarifa indicada para baixar os arquivos públicos; não foi identificada licença nominal explícita autorizando redistribuir os arquivos incorporados a um produto comercial. A permissão de reuso/redistribuição e atribuição deve ser confirmada com o INMET antes de publicar dados brutos/derivados a usuários. Não há cota de API a estimar; acesso em lote exige download, seleção e processamento dos arquivos.
- **Qualidade/confiabilidade:** são medições de estação, mais alinhadas com a classe de entrada do modelo publicado que uma previsão arquivada ou grade de reanálise, mas representam o entorno da estação, não necessariamente a lavoura. Disponibilidade, relocação e lacunas variam por estação e precisam ser auditadas; não foi confirmado um SLA de disponibilidade para este download.
- **Conclusão:** melhor fonte inicial de custo baixo para investigação/validação retrospectiva, condicionada a cobertura da estação e autorização de uso do dado no produto.

## 4. Auditoria do pipeline existente

### Coleta e eventos

O worker `services/api/integracoes/openweather/worker.py` agenda sincronizações OpenWeather e previsões. `OpenWeatherService` obtém condição atual e, separadamente, previsão. O snapshot atual emite `ClimaSyncRealizado`; o evento inclui timestamp, temperatura, umidade e chuva do provider. Não existe evento de leitura histórica retroativa no código encontrado.

O adaptador público usa WeatherAPI/OpenWeather/Open-Meteo para responder consultas públicas com previsão normalizada e cache; esse caminho não é o pipeline de `RegistroClima`. Portanto, alternar o provedor do endpoint público não cria histórico fitossanitário por tenant/unidade.

### Persistência e agregação

`RegistroClima` (`services/api/agricola/climatico/models.py`) tem colunas para temperatura mínima/máxima/média, umidade relativa, precipitação e fonte, mas não guarda timestamp por amostra, coordenada/estação, método de agregação, indicador de qualidade nem payload bruto. A chave única é `(tenant_id, unidade_produtiva_id, data_registro, fonte)`.

O `ClimaEventSubscriber` (`services/api/agricola/climatico/subscribers.py`) converte `occurred_at` para `.date()`, salva a temperatura instantânea em `temp_media_c`, a umidade instantânea em `umidade_rel_pct` e a chuva atual. Em reexecuções na mesma data/fonte, atualiza a mesma linha, substituindo a leitura anterior. A frequência do worker pode ser muito maior que diária, mas as amostras não são retidas como série: permanece o valor mais recente para aquela data. O timestamp é UTC no evento e a extração de data não converte explicitamente para o fuso local da lavoura; isso também pode mudar a atribuição do dia perto da meia-noite local.

`PrevisaoClima` retém previsões futuras diárias com `periodos`, incluindo amostras horárias/3-horárias conforme o provider. Não é armazenamento de histórico observado e o motor fitossanitário lê `RegistroClima`, não usa esses períodos futuros.

### Histórico, fonte, qualidade e isolamento

- A rota de histórico apenas lê registros já persistidos; não aciona backfill externo.
- A fonte é gravada como texto, normalmente `OPENWEATHER`; não há registro de estação física, dataset/modelo, versão, offset, método do agregado ou completude.
- Valores são nullable, mas o pipeline não conserva série amostral nem contagem de leituras que permitiria dizer se uma média diária é completa.
- O subscriber verifica que a unidade ativa pertence ao tenant do evento, e a procura/upsert inclui tenant, unidade, data e fonte. Os serviços de clima consultam por tenant/unidade. O desenho atual oferece isolamento básico na persistência, mas qualquer importação em lote precisaria preservar a mesma chave e escopo; não se deve compartilhar dados identificáveis de um tenant como se fossem medição de outro.
- A lacuna principal não é simplesmente uma opção de plano: no fluxo atual os endpoints históricos não são chamados e a aplicação não conserva amostras horárias. Mesmo uma chave/plano atual que tivesse dados históricos não preencheria automaticamente o banco.

## 5. Comparação das alternativas

| Alternativa | Cobertura e aderência | Custo/licença | Esforço e riscos | Avaliação |
|---|---|---|---|---|
| **A. Aproveitar OpenWeather** | One Call 4 oferece mínimo diário, RH e histórico paginado; disponível globalmente. Dados do provider/modelo não são as observações da estação usada no modelo científico. | 1.000 chamadas/dia inclusas e `US$ 0,0015` por chamada adicional; 60 dias diários correspondem a cerca de 6 páginas por localização. Confirmar licença/armazenamento da assinatura atual. | Médio: novo endpoint/versão, paginação, normalização, timezone, proveniência e backfill idempotente. A integração corrente usa 2.5/3.0, não 4.0. | Tecnicamente viável para preencher série retrospectiva do provider; não é a primeira escolha para validação baseada em dados observados. |
| **B. Aproveitar WeatherAPI** | Tem mínimo e RH médio diários, mais hourly. Plano Pro+ já cobre 365 dias e endpoints de 30 dias por chamada; porém a própria empresa define histórico como arquivo de previsões, não observações. | `US$ 25/mês` Pro+ (5M chamadas); histórico 365 dias. Quota esgotada interrompe chamadas no mês. | Baixo/médio para protótipo do dado, médio para integrar persistência; exigiria `history.json`, inexistente no pipeline. Validação científica por arquivo de previsão seria enviesada em relação ao insumo original. | Não recomendada como base de validação observacional; pode servir a estudo separado de histórico de forecast. |
| **C. Fonte pública oficial (INMET)** | Medições horárias desde 2000 em estações automáticas e histórico de estações convencionais; permite derivar Tmin e RH diárias, se a série estiver completa e a estação representar a lavoura. | Download divulgado como gratuito; permissão de redistribuição em serviço comercial precisa confirmação. | Baixo para baixar/analisar lote de validação; médio para automatizar ingestão. Precisa mapear estações, metadados, controle de qualidade, UTC e lacunas. | **Mais indicada para a primeira base retrospectiva de validação**, sem compromisso de implementar integração em produto agora. |
| **D. Iniciar coleta contínua própria** | Cria histórico prospectivo. O snapshot OpenWeather atual não basta: amostras diárias se sobrescrevem e não são médias diárias completas. | Sem custo de histórico API adicional se reaproveitar chamadas já licenciadas, mas frequência maior pode elevar custos/quotas; custo de desenvolvimento e armazenamento. Sensores próprios têm custo não estimado. | Médio: persistir amostras com timestamp/fonte e agregar com controle de completude/fuso; alternativamente adotar medições de estação/sensor local. Não resolve validação retrospectiva imediatamente. | Complemento para validação prospectiva futura, não substituto do histórico inicial. |

## 6. Recomendação mínima

1. **Preparar a validação retrospectiva fora do banco de produção:** baixar dados horários oficiais do INMET para regiões das fazendas que participarão do piloto e montar inventário estação↔lavoura (distância, altitude, período ativo, variáveis e completude). Não importar os CSVs direto em `RegistroClima`.
2. **Derivar diários com proveniência:** computar Tmin a partir de observações horárias válidas e a média diária de RH com protocolo explícito. Preservar série bruta, UTC, localidade e flags em artefatos de análise; não preencher falhas sem regra previamente validada. Conferir se a definição diária coincide com Hinnah et al.; se não coincidir, registrar como adaptação a validar.
3. **Usar Open-Meteo ERA5-Land somente como série de comparação/apoio onde não houver estação adequada**, identificando a grade e sem misturar reanálise com estação no mesmo cálculo sem protocolo. A assinatura e o direito comercial precisam ser aprovados antes de qualquer uso automatizado em produção.
4. **Em paralelo, planejar coleta contínua própria somente após aprovar o protocolo:** mudança futura precisa manter registros horários separados ou outra estrutura que retenha amostras e agregue por fuso/completude. A tabela atual, com uma linha atualizada por dia, não é histórico de amostras.
5. **Antes de uma integração de produção:** validar termos de reutilização com INMET/provedor, dimensionar chamadas pela quantidade real de unidades e frequência, definir fonte e qualidade por registro e decidir estrutura de persistência. Não contratar WeatherAPI/Open-Meteo ou adicionar coluna/migration nesta investigação.

Essa sequência atende a preparar um conjunto de validação sem criar integração meteorológica ampla ou alterar o banco. A cobertura e adequação real dependem das coordenadas e estações da população de piloto, que não foram consultadas nesta análise.

## 7. Esforço e custos

- **Preparação retrospectiva INMET para prova de viabilidade:** baixo a médio esforço de dados (download de arquivos anuais, seleção de estação, parser, timezone, flags e diagnóstico de lacunas). Custo de acesso publicado: gratuito. Custo de eventual revisão jurídica/agrônoma não estimado.
- **Prova comparativa com Open-Meteo histórico:** esforço baixo/médio para pedir ERA5-Land e derivar RH diária; API Professional é obrigatória para histórico em uso comercial. Quota publicada: 5 milhões de unidades/mês, sem excedente por chamada. Preço exato não foi confirmado na página pública consultada e deve ser verificado no portal de contratação.
- **Backfill OpenWeather 4.0:** seis chamadas de timeline diária por localização para 60 dias, no limite de 10 dias/resposta. Com franquia de 1.000 chamadas/dia, custo incremental de referência `US$ 0,0015` por chamada acima dela; reter clima horário para média RH poderá aumentar chamadas. Não inclui impostos nem eventuais condições contratuais.
- **WeatherAPI histórico:** 60 dias cabem no plano Pro+ (365 dias), anunciado a `US$ 25/mês`, com 5 milhões chamadas/mês; mas a natureza é arquivo de previsão, inadequado para reproduzir observação meteorológica real.
- **Coleta própria contínua:** custo de API depende de frequência/unidades e credencial/plano; a integração atual já opera em frequência configurável, mas não retém cada medição. O esforço de implementação da retenção/agregação é médio; sensores de campo não foram orçados.

Valores e planos são referência da documentação oficial consultada em 2026-10-30, podem mudar e não representam contratação ou autorização para uso.

## 8. Riscos remanescentes e decisão

- A cobertura das estações INMET próximas às lavouras não foi geoespacialmente verificada; para algumas unidades pode não existir estação representativa.
- Média de RH derivada de dados horários não pode ser declarada idêntica à convenção do estudo sem verificar o protocolo científico e a medição usada.
- Reanálise, histórico de forecast e estação observada têm naturezas diferentes; uma série sem rótulo de fonte/metodologia prejudicaria a avaliação.
- Os arquivos públicos do INMET não exibem tarifa de download, mas o direito de republicar/redistribuir no produto ainda exige confirmação de termos.
- O pipeline de produção atual não possui amostras horárias históricas ou agregações diárias completas; melhorar somente a frequência de chamadas sem mudar a persistência ainda sobrescreveria os dados do dia.
- O modelo fitossanitário continua sem aprovação; este trabalho valida apenas viabilidade de preparação climática.

**Veredicto: GO COM RESSALVAS** para preparar um conjunto retrospectivo de validação, começando pelo INMET e mapeamento de cobertura. **NO-GO** para considerar o histórico pronto para o motor, contratar uma fonte comercial, alterar o pipeline de produção ou homologar regra fitossanitária sem os passos pendentes.

## 9. Referências oficiais consultadas

- [INMET — arquivos de dados históricos automáticos](https://portal.inmet.gov.br/dadoshistoricos/)
- [INMET/BDMEP — dados históricos](https://portal.inmet.gov.br/servicos/bdmep-dados-hist%C3%B3ricos)
- [OpenWeather — One Call API 4.0](https://openweathermap.org/api/one-call-4) e [preço](https://openweathermap.org/price)
- [WeatherAPI — History API](https://www.weatherapi.com/docs/history-api/), [preços](https://www.weatherapi.com/pricing) e [natureza dos dados históricos](https://www.weatherapi.com/pricing)
- [Open-Meteo — Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), [preços](https://open-meteo.com/en/pricing) e [termos de uso](https://open-meteo.com/en/terms)
