# Auditoria CLIMATE-01: Transformação do OpenWeather em Valor Operacional

## 1. Objetivo
Analisar a infraestrutura de integrações consolidada do OpenWeather e propor as adaptações para conectá-la ao domínio agrícola operacional (`UnidadeProdutiva`, `AreaRural/Talhão`), gerando alertas pelo `AlertEngine` e salvando o histórico climático. Todo o processo deve seguir as diretrizes rigorosas do AgroSaaS de "reuso de infraestrutura" e "domain events".

## 2. Estado Atual e Descobertas
1. **Infraestrutura de Integrações**: O provider `OpenWeather` está perfeitamente integrado à esteira oficial (jobs, health, policies).
2. **Contexto Climático Atual**: O `OpenWeatherClient` faz a busca usando `location_query` (string única definida a nível de configuração do Tenant). Não há granularidade espacial para buscar múltiplos pontos (Unidades Produtivas ou Talhões) da mesma fazenda.
3. **Persistência**: O snapshot de clima do OpenWeather (`OpenWeatherWeatherSnapshot`) trafega em memória e registra payload dentro do `IntegrationHealth` / `IntegrationJob`, mas não é refletido de volta para o banco de dados principal de clima.
4. **Alertas Agrícolas**: O `AgriculturaAlertGenerator` atual monitora operações atrasadas e falta de movimentações, mas ainda não analisa condições climáticas (vento extremo, volume de chuvas) para recomendações operacionais (como bloqueio de pulverização).
5. **Módulo Agrícola (Reuso)**: Encontramos a tabela oficial `registros_clima` (`agricola.climatico.models.RegistroClima`), que armazena `precipitacao_mm`, `temp_max_c`, evapotranspiração, entre outros. Este modelo já tem vínculo obrigatório com `UnidadeProdutiva`.

## 3. Gaps e Mudanças Necessárias
1. **Granularidade (Unidade Produtiva)**: O `OpenWeatherClient` precisa aceitar `lat` e `lon`. O Sync Job da integração deve consultar todas as `UnidadesProdutivas` ativas do tenant que possuam localização (ou o centróide da `AreaRural` sede) e fazer requisições iterativas.
2. **Desacoplamento via Eventos**: Ao invés do serviço da integração injetar dados diretos no módulo agrícola, a integração deve disparar um Domain Event (ex: `WeatherSnapshotCaptured` ou `ClimaSincronizado`) e o outbox deve distribuir para os módulos interessados.
3. **Subscribers Agrícolas**: O módulo `agricola.climatico` deve escutar esse evento e popular a tabela `registros_clima` com a origem setada para `OPENWEATHER`.
4. **Motor de Alertas**: Deve-se criar ou estender um gerador do `AlertEngine` (ex: `ClimaAlertGenerator`) para analisar registros de clima recentes da `UnidadeProdutiva` e emitir alertas operacionais (ex: Alerta de Ventania, Alerta de Chuva Excessiva para Pulverização).

## 4. Conclusão da Auditoria
Não será necessário inventar tabelas novas ou infraestrutura paralela. Utilizaremos 100% da arquitetura já concebida:
- Busca das Coordenadas da `UnidadeProdutiva`.
- Coleta de dados via API já existente (`OpenWeather`).
- Disparo de `DomainEventOutbox`.
- Escuta no Subscriber Agrícola para gravação de `RegistroClima`.
- Geração de avisos via `AlertEngine`.
- Consumo transparente para o Front-End Web no Dashboard.
