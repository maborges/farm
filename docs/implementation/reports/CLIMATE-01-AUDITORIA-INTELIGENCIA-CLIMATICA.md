# Auditoria CLIMATE-01: Inteligência Climática

## 1. Resumo Executivo
O AgroSaaS possui uma fundação arquitetural extremamente robusta (Integrações, Alert Engine, Domain Events). O provedor `OpenWeather` já foi integrado na camada técnica. No entanto, a Inteligência Climática como funcionalidade de negócio (módulo Agrícola) encontra-se em estágio incipiente. Os modelos de banco de dados (`RegistroClima`) existem, mas a lógica de captura, armazenamento real, disparo de alertas operacionais e consumo no frontend (Web e PWA) ainda não foi implementada. A fundação está pronta, mas o ciclo de negócio está interrompido.

## 2. Estado Atual
- **Camada Técnica**: A integração com o `OpenWeather` existe, possui schema canônico e executa sync, mas é estritamente técnica (apenas string `location_query` a nível de tenant).
- **Camada Operacional (Backend)**: Existem os modelos e roteadores em `services/api/agricola/climatico`, porém a implementação no serviço (`ClimaService.sync_open_meteo`) é apenas um mock.
- **Camada Visual/Frontend**: O aplicativo Web possui apenas redirecionamentos (ex: `agricola/climatico/page.tsx`). Não há telas ou componentes visuais consumindo o clima.
- **Camada Offline (PWA)**: Não há presença de dados climáticos no `apps/campo`.

## 3. Evidências
- `/opt/lampp/htdocs/farm/services/api/integracoes/openweather/services.py`: Mostra que o provider técnico existe e gera snapshot em memória.
- `/opt/lampp/htdocs/farm/services/api/agricola/climatico/service.py`: `sync_open_meteo` retorna apenas string mockada ("Sincronização do clima executada com sucesso").
- `/opt/lampp/htdocs/farm/services/api/agricola/climatico/models.py`: Presença da tabela `RegistroClima`.
- `/opt/lampp/htdocs/farm/services/api/alert_engine/generators/agricultura_generator.py`: Não contém lógica para clima.

## 4. Backend
- **Models**: EXISTE (`RegistroClima`, `PrevisaoProdutividade`).
- **Services**: EXISTE PARCIALMENTE (apenas assinatura de métodos mockados).
- **Repositories**: EXISTE PARCIALMENTE.
- **Routers**: EXISTE PARCIALMENTE (mockados).
- **Jobs/Scheduler/Workers**: NÃO EXISTE na camada agrícola (apenas o job canônico genérico de integrações).
- **Events**: NÃO EXISTE eventos de domínio para o Clima.
- **Alertas**: NÃO EXISTE integração climática no `AlertEngine`.
- **Health/Observabilidade**: EXISTE E ATENDE (herdado da engine de integrações).

## 5. Frontend
- **apps/web**: NÃO EXISTE (apenas stub em `page.tsx`).
- **apps/campo**: NÃO EXISTE.
- Cards climáticos, dashboards, widgets, mapas, timeline: NÃO EXISTE.

## 6. Campo PWA
- **Sincronização, consulta offline, recomendações, alertas**: NÃO EXISTE.

## 7. Agricultura
- **Planejamento, plantio, pulverização, adubação, irrigação, colheita**: NÃO EXISTE integração climática com os fluxos operacionais.

## 8. Pecuária
- **Conforto térmico, pastejo, manejo, sanidade, reprodução**: NÃO EXISTE.

## 9. Máquinas
- **Ordens de serviço, bloqueios por chuva, janela operacional**: NÃO EXISTE.

## 10. Estoque
- **Consumo, planejamento, reposição, aplicação**: NÃO EXISTE influência climática implementada.

## 11. Financeiro
- **Custos, rentabilidade, previsões, perdas, riscos**: NÃO EXISTE.

## 12. ESG
- **Certificações, sustentabilidade, rastreabilidade**: NÃO EXISTE.

## 13. Providers
- **OpenWeather**: EXISTE E ATENDE (Integrado tecnicamente).
- **INMET, WeatherAPI, NOAA, Tomorrow.io, Meteomatics, Estações IoT**: NÃO EXISTE.

## 14. Alert Engine
- Regras para chuva, vento, temperatura, pulverização: NÃO EXISTE.

## 15. Notification Engine
- Notificações relacionadas ao clima: NÃO EXISTE.

## 16. Dashboard
- Dashboard climático, timeline, histórico, diagnóstico, previsão: NÃO EXISTE.

## 17. Estrutura Territorial
- O clima pode ser aplicado em dois níveis baseando-se nos modelos atuais (`AreaRural` e `UnidadeProdutiva`):
  - **UnidadeProdutiva**: Adequado para clima regional geral (possui `coordenadas_sede`). Ideal para fase 1.
  - **Talhão (AreaRural tipo TALHAO)**: Adequado para agricultura de precisão (possui `centroide_lat` / `centroide_lng`).

## 18. Gap Analysis

| Área | Existe | Parcial | Não Existe | Evidências |
|---|---|---|---|---|
| Modelagem Base | | X | | `RegistroClima` e `PrevisaoProdutividade` existem. Faltam sensores e riscos severos. |
| Provider OpenWeather | X | | | Integrações canônicas maduras, mas consumo apenas técnico. |
| Serviços Agrícolas (Backend) | | | X | `ClimaService` mockado, não conecta com a engine de integração. |
| Eventos (Domain Events) | | | X | Ausência de eventos do tipo `WeatherSnapshotCaptured`. |
| Alertas Operacionais | | | X | `AlertEngine` não tem gerador de clima. |
| Frontend Web (Dashboard) | | | X | Apenas rotas stub/redirect. |
| Campo PWA (Offline) | | | X | Sem referências à funcionalidade climática no App de campo. |
| Modulos (Máquinas, Pecuária) | | | X | Nenhuma lógica de bloqueio operacional por chuva implementada. |

## 19. Riscos
- **Integrações Redundantes**: Se uma equipe implementar chamadas REST direto no frontend para o OpenWeather, isso quebrará o padrão de Integração (que roda no Backend) e ignorará o armazenamento do histórico.
- **Desconexão de Eventos**: Fazer o Provider técnico persistir direto na tabela `RegistroClima` (acoplamento forte), em vez de usar `DomainEventOutbox`.
- **Granularidade Excessiva**: Chamar API climática para cada Subtalhão pode exaurir os rate limits (429) do OpenWeather. Devemos agrupar consultas por `UnidadeProdutiva` inicialmente.

## 20. Recomendações
**Curto Prazo:**
- Interligar o `OpenWeather` ao módulo `agricola.climatico` usando `Domain Events` (`ClimaSincronizado`).
- Ajustar `OpenWeatherClient` para usar coordenadas (`lat/lon`) extraídas da `UnidadeProdutiva`.

**Médio Prazo:**
- Criar o `ClimaAlertGenerator` no `AlertEngine` para gerar bloqueios operacionais (ex: chuva alta -> bloqueio de pulverização).
- Criar os Widgets/Cards Climáticos no Dashboard do `apps/web`.

**Longo Prazo:**
- Integrar os Alertas Climáticos no PWA (`apps/campo`) para uso offline.
- Integrar com Pecuária e Máquinas.

## 21. Roadmap

- **CLIMATE-02**: Fluxo de Ingestão de Dados
  - Atualizar `OpenWeatherClient` para suportar `lat/lon`.
  - Job da integração varre `UnidadeProdutiva` e dispara Domain Event (`ClimaSyncRealizado`).
  - Subscriber Agrícola escuta e grava em `RegistroClima`.

- **CLIMATE-03**: Alertas Operacionais Básicos
  - Criar `ClimaAlertGenerator` no `AlertEngine`.
  - Disparar `OperationalAlert` por limites de vento e chuva.

- **CLIMATE-04**: Dashboard Climático Web
  - Criação dos endpoints reais em `ClimaService`.
  - Desenvolvimento dos cards no Next.js (`apps/web`).

- **CLIMATE-05**: Inteligência Agronômica
  - Cruzar clima com Planejamento Agrícola (Janela de Plantio).

- **CLIMATE-06**: Offline / Campo
  - Sincronização do último snapshot para o `apps/campo`.

## 22. Veredicto Final
A maturidade da inteligência climática do AgroSaaS é **Fundacional**. A base técnica (integração, mensageria e tabelas) existe, mas a inteligência de negócio é inexistente. O sistema está perfeitamente pavimentado para que a implementação funcional aconteça sem necessidade de criar arquitetura paralela. A próxima frente (CLIMATE-02) deve conectar o provedor técnico ao banco de dados agrícola através de eventos de domínio.
