# EXECUÇÃO — CLIMATE-02

## Fluxo de Ingestão Desacoplado de Dados Climáticos

---

## 1. Arquitetura Consolidada

Foi implementada a ingestão desacoplada de dados climáticos utilizando OpenWeather como provider técnico e emitindo Domain Events (`ClimaSyncRealizado`) para propagação ao domínio agrícola.

A lógica agora permite consultas via coordenadas geográficas (`lat`, `lon`) baseadas no cadastro de cada `UnidadeProdutiva`.

### 1.1 Provider OpenWeather Atualizado

- O arquivo `client.py` (`OpenWeatherClient.fetch_current_weather`) foi alterado para suportar `lat` e `lon` como prioridade na query, mantendo `location_query` apenas como fallback histórico (legacy).
- O arquivo `services.py` (`OpenWeatherCanonicalAdapter._execute_current_weather`) foi reescrito para:
  1. Carregar a lista de `UnidadeProdutiva` ativas associadas ao Tenant.
  2. Caso as unidades tenham `coordenadas_sede` válidas e parsiáveis, é feita uma chamada direta passando as coordenadas para a API da OpenWeather.
  3. Caso o Tenant não possua Unidades Produtivas ativas ou configuradas, mantém o comportamento de fallback buscando pelo `location_query` cadastrado globalmente nas configurações da integração.
  4. Para cada `UnidadeProdutiva` processada, é emitido via `DomainEventOutbox` o evento `ClimaSyncRealizado`.

### 1.2 Eventos de Domínio Climático

- **`agricola/climatico/events.py`**: Criado para isolar a definição de eventos agrícolas de clima, em especial o `ClimaSyncRealizado` que propaga não só o payload raw mas os dados estruturados de medições vitais como precipitacao (chuva), umidade, vento, etc.
- **`agricola/climatico/subscribers.py`**: Criado e registrado no startup do módulo. Contém o `ClimaEventSubscriber` que escuta ativamente o evento `agricola.climatico.sync_realizado`. O Subscriber converte os dados e realiza Upsert no modelo `RegistroClima`, sendo **totalmente idempotente** (garantia via chave `tenant_id` + `unidade_produtiva_id` + `data_registro` + `fonte`).

## 2. Check de Governança

- **Isolamento**: O client HTTP e os serviços do OpenWeather continuam não conhecendo o modelo `RegistroClima`.
- **Desacoplamento**: O módulo `climatico` não importa componentes do pacote OpenWeather; ele reage a eventos padronizados.
- **Idempotência**: `RegistroClima` não será duplicado graças à lógica de update `where data_registro = x and fonte = y`.
- **Escopo**: Foco total em Unidades Produtivas, atendendo a granularidade macro pedida.

## 3. Próximos Passos

O fluxo de ingestão base para as tabelas do Agrícola/Climático agora é funcional end-to-end. O próximo passo de negócio pode ser o provisionamento de inteligência sobre essa nova base de dados rica ou configuração de Alertas Agronômicos.
