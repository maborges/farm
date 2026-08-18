# NESTLE-APTACONNECT-01 — Auditoria de aderência do DeepFarms

**Data da auditoria:** 2026-08-17  
**Escopo:** diagnóstico técnico, funcional, arquitetural, de dados e de produto.  
**Restrição:** nenhuma implementação, migration, alteração de banco, API ou modelo de IA foi realizada.

## 1. Resumo executivo

O arquivo `AptaHub-Conecta-Desafio-Nestle.pdf` não está presente no workspace auditado. A busca local encontrou somente PDFs comerciais do AgroSaaS. Portanto, não é tecnicamente responsável afirmar que o texto abaixo reproduz os requisitos específicos da Nestlé/APTA. A auditoria separa:

1. o que foi comprovado no repositório;
2. o que é capacidade parcial ou infraestrutura reaproveitável;
3. o que depende do conteúdo ausente do desafio;
4. o que falta para uma POC agrícola validável.

Mesmo com essa limitação, o diagnóstico da plataforma é claro: o DeepFarms possui uma base operacional agrícola significativamente mais ampla que um aplicativo isolado ou um modelo de IA desconectado. Há estrutura para `Tenant → UnidadeProdutiva → ÁreaRural/Talhão → Safra → Cultivo → Operação → Solo → Caderno → Colheita`, com RLS, APIs, dashboards e PWA offline. Essa base é adequada para instrumentar uma POC e coletar ground truth.

O maior gap não é, neste momento, a capacidade de cadastrar um talhão ou armazenar um indicador. É a transformação desses registros em um fluxo validado de inteligência agrícola: dados externos contextualizados espacial e temporalmente, histórico longitudinal confiável, ingestão de imagens/sensores, definição do alvo agronômico e modelo de previsão com validação fora da amostra e em campo.

O clima operacional possui regras e recomendações determinísticas, mas a sincronização agrícola direta ainda tem stub em `ClimaService.sync_open_meteo`. O NDVI possui entidade, consulta de série e tela, mas a captura Sentinel-2 é explicitamente mockada. A previsão de produtividade possui entidade e endpoint, mas `gerar_nova_previsao` retorna valores fixos (`65.5 sc/ha`, erro de `5%`, versão `rf_soja_v2`). Não há evidência de treinamento, artefato de modelo, dataset, backtest, métrica ou validação de campo.

**Veredicto:** `POC CONDICIONADA`.

O DeepFarms deve ser inscrito se a proposta puder ser apresentada como uma plataforma operacional e de coleta/contextualização para validar um caso agronômico específico com dados Nestlé/APTA. Não deve ser apresentado hoje como uma solução já validada de previsão de produtividade ou safra.

## 2. Interpretação do desafio Nestlé

### 2.1 Limitação documental crítica

Sem o PDF, não foi possível extrair de forma verificável:

- o problema textual apresentado pela Nestlé;
- a cultura ou culturas oficiais;
- o público-alvo e os usuários da solução;
- a decisão agronômica ou de negócio prioritária;
- os dados e fontes formalmente exigidos;
- critérios de sucesso, prazo, escala ou formato da POC.

Qualquer requisito Nestlé específico usado nesta versão deve ser tratado como **não auditável** até que o PDF seja disponibilizado. A matriz deste relatório usa, como eixo provisório, o conjunto de capacidades normalmente associado ao escopo solicitado na própria demanda: monitoramento agrícola, georreferenciamento, clima, histórico, imagens/sensoriamento, coleta de campo, IA/ML, previsão e dashboards.

### 2.2 Problema central que pode ser avaliado hoje

A decisão técnica que o DeepFarms consegue apoiar imediatamente é a decisão operacional contextualizada por talhão/safra: o que foi planejado, o que foi executado, em que área, com quais insumos, sob quais condições, com quais ocorrências e qual foi o resultado da colheita.

A decisão de **prever produtividade futura**, **estimar safra** ou **prescrever uma intervenção agronômica com acurácia comprovada** depende de uma etapa adicional de dados e validação. A plataforma tem pontos de captura para essa evolução, mas não há evidência de que essa capacidade preditiva esteja pronta.

## 3. Capacidades necessárias e evidência disponível

| Capacidade a verificar | Evidência no repositório | Maturidade auditada |
|---|---|---|
| Gestão territorial e menor unidade espacial | `AreaRural`, talhão, centroides, GeoJSON/KML/Shapefile/KMZ e geoprocessamento | **ATENDE**, com ressalvas de qualidade cadastral |
| Safra e cultura | `Safra`, `Cultivo`, `CultivoArea`, fases e datas | **ATENDE** |
| Operações agrícolas | `OperacaoAgricola`, `OperacaoExecucao`, insumos, operador, máquina, custo, clima e GPS | **ATENDE PARCIALMENTE** |
| Solo | `AnaliseSolo`, parâmetros por cultura/região, interpretação e recomendações | **ATENDE PARCIALMENTE** |
| Colheita e produtividade real | `RomaneioColheita`, `ProdutoColhido`, quantidade, peso, qualidade e vínculo a safra/talhão | **ATENDE PARCIALMENTE** |
| Coleta offline | Dexie, outbox, push/pull, caderno, tarefas, fotos e GPS | **ATENDE**, mas requer teste específico com piloto |
| Clima atual/histórico | `RegistroClima`, OpenWeather, alertas e recomendações por limiar | **ATENDE PARCIALMENTE** |
| NDVI/satélite | `ImagemNDVI`, série temporal, UI e contrato de integração Sentinel-2 | **BASE EXISTENTE** |
| Sensores IoT agrícolas | Migrações/modelos legados de sensores e estações; não há pipeline agrícola comprovado | **INTEGRAÇÃO FUTURA POSSÍVEL** |
| Previsão de produtividade | Entidade e endpoint; cálculo fixo/mock | **NÃO ATENDE** como ML validado |
| IA/ML agrícola treinado | Nenhum dataset, artefato, pipeline ou avaliação de modelo localizado | **NÃO ATENDE** |
| Multi-tenant e segurança | `tenant_id`, dependências, RLS, RBAC, sync com device token | **ATENDE PARCIALMENTE**; requer validação de dados parceiros |
| Integração multiprovider | Domínio oficial de Integrações, jobs, health, eventos e credenciais | **BASE EXISTENTE** |

## 4. Estado atual do DeepFarms

### 4.1 Infraestrutura existente

O repositório confirma monorepo com API FastAPI/SQLAlchemy/Alembic, Web Next.js e Campo PWA com Dexie. A arquitetura documenta RLS, tenant-aware, filas/jobs, eventos/outbox, integrações e sincronização offline.

Evidências principais:

- `docs/architecture/agrosaas-master-context.md`;
- `docs/architecture/architecture-inventory.md`;
- `docs/architecture/agrosaas-data-model.md`;
- `docs/architecture/INTEGRATIONS-ARCH-01.md`;
- `services/api/main.py`;
- `apps/campo/src/lib/db.ts`, `sync/push.ts` e `sync/pull.ts`.

### 4.2 Capacidade operacional versus capacidade analítica

Há diversos serviços chamados de inteligência, recomendações e IA. Eles não devem ser agrupados sob uma única afirmação de “IA agrícola pronta”. O repositório contém pelo menos quatro maturidades distintas:

- **registro operacional:** forte em safra, operações, solo, caderno e colheita;
- **regras determinísticas:** existentes em clima, solo, alertas e recomendações;
- **infraestrutura de dados externos:** parcialmente existente em clima e NDVI;
- **ML/predição agronômica validado:** não comprovado.

O `IAPredicaoRiscoService` encontrado é de risco financeiro, baseado em séries de custos/receitas e tendência simplificada; não é previsão de produtividade agrícola. O `IAGrowthService` trata growth, ofertas, telemetria e conversão; também não é modelo agronômico.

### 4.3 Duplicação/legado

Existe uma segunda árvore em `apps/web/services/api`, com cópias de módulos, modelos e migrations. Há também módulos `ndvi_avancado` e `amostragem_solo` com classes esqueleto/legadas, enquanto a implementação mais rica está em `services/api/agricola/ndvi` e `services/api/agricola/analises_solo`.

Isso não prova falha do runtime principal, mas reduz a confiabilidade de usar qualquer arquivo isolado como evidência de capacidade produtiva. Para a POC, será necessário fixar o runtime canônico, o conjunto de migrations aplicado e o contrato de dados que será usado.

## 5. Matriz principal de aderência

Como o PDF do desafio não está disponível, a coluna “Requisito Nestlé” usa requisitos provisórios derivados do escopo desta auditoria. A classificação não substitui uma releitura do documento original.

| Requisito Nestlé | DeepFarms | Status | Evidência | GAP | Esforço estimado |
|---|---|---|---|---|---|
| Representar propriedade, unidade produtiva e talhão | Hierarquia territorial e vínculos operacionais | ATENDE | `core/cadastros/propriedades`, `talhoes`, `AreaRural` | Validar qualidade dos polígonos piloto | Baixo |
| Georreferenciar a área de análise | Centroides, lat/lon, GeoJSON/KML/Shapefile/KMZ | ATENDE PARCIALMENTE | `geoprocessamento_service.py`, `AreaRural`, upload geoespacial | Normalização de CRS, validação geométrica e cobertura dos talhões | Médio |
| Registrar cultura, variedade e ciclo | Safra, cultivo, cultivar, datas, fases | ATENDE | `safras/models.py`, `cultivos/models.py` | Completar dados históricos e taxonomia parceira | Baixo/Médio |
| Registrar operações por talhão/safra | Operação, execução, insumo, operador, máquina e custo | ATENDE PARCIALMENTE | `operacoes/models.py` | Garantir completude, unidades e qualidade de execução | Médio |
| Registrar solo e associá-lo ao talhão/cultura | Análise física/química e regras por cultura/região | ATENDE PARCIALMENTE | `analises_solo/models.py`, `service.py` | Laudos, profundidade, pontos amostrais e séries históricas | Médio |
| Coletar observações de campo | Caderno, ocorrências, visitas, fotos, pragas/doenças | ATENDE PARCIALMENTE | `caderno`, `monitoramento`, `agronomo` | UX e protocolo de coleta específico da POC | Médio |
| Operar sem conexão | IndexedDB, outbox, push/pull, conflitos e uploads | ATENDE | `apps/campo/src/lib/db.ts`, `sync/*.ts` | Validar em aparelhos/rede do piloto | Médio |
| Capturar GPS e fotos | Campos lat/lon no evento/foto/operação e upload offline | ATENDE PARCIALMENTE | `caderno/models.py`, `CampoEventoOffline`, `evidence-upload.ts` | Política de precisão, consentimento e teste de permissões | Baixo/Médio |
| Consumir clima | OpenWeather, RegistroClima, alertas e recomendações | ATENDE PARCIALMENTE | `integracoes/openweather`, `agricola/climatico` | Sincronização agrícola real e vínculo temporal/espacial por talhão | Médio |
| Interpretar clima operacionalmente | Thresholds de vento, chuva, temperatura e umidade | ATENDE PARCIALMENTE | `recommendation_service.py`, `clima_provider.py` | Validar limiares com agrônomos e cultura-alvo | Médio |
| Consumir imagens de satélite | Entidade NDVI, série e tela; integração descrita | BASE EXISTENTE | `agricola/ndvi`, `ndvi-talhao.tsx` | Ingestão Sentinel-2 e processamento real | Alto |
| Usar drones/raster/multiespectral | Não localizado pipeline operacional | NÃO ATENDE | Busca em `services/api`, `apps` e `packages` | Provider, armazenamento, processamento e contrato | Alto |
| Receber sensores/estações | Modelos/migrations legados e domínio IoT genérico | INTEGRAÇÃO FUTURA POSSÍVEL | `fase2_ia_iot.py`, `fase3_sprints27_33_final.py`, `INTEGRATIONS-ARCH-01.md` | Provider agrícola real, device registry e série validada | Alto |
| Gerar previsão de produtividade | Endpoint com cálculo fixo | NÃO ATENDE | `previsoes/service.py` | Dataset, modelo, feature pipeline e validação | Muito alto |
| Estimar produção de safra | Campos de produtividade real/meta e colheita | ATENDE PARCIALMENTE | `Cultivo`, `ProdutoColhido`, romaneios | Conciliação de volume, área, unidade e fechamento de safra | Médio |
| Alertar riscos agrícolas | Alert Engine e Recommendation Engine | ATENDE PARCIALMENTE | `alert_engine`, providers | Cobertura específica da cultura e validação de falso positivo | Médio |
| Dashboard/relatórios | Dashboards agrícola, clima, NDVI, safra e inteligência | ATENDE PARCIALMENTE | `apps/web/src/app`, componentes agrícolas | Visão de POC e indicadores Nestlé/APTA | Médio |
| Expor APIs | REST `/api/v1`, rotas agrícolas e sync | ATENDE | `main.py`, routers agrícolas | Contratos de parceiro, autenticação e rate limit | Médio |
| Escalar múltiplos produtores/propriedades | Modular monolith, PostgreSQL, Redis, Celery e RLS | BASE EXISTENTE | playbook, `main.py`, modelos tenant-aware | Benchmark e operação com dados externos em volume | Médio/Alto |
| Proteger dados de produtores | JWT/RBAC/RLS/auditoria | ATENDE PARCIALMENTE | `agrosaas-engineering-playbook.md`, middleware, dependencies | DPA/LGPD, governança de compartilhamento e auditoria da POC | Médio |

## 6. Estrutura territorial e geoespacial

### 6.1 Hierarquia

O modelo distingue corretamente fronteiras com semânticas diferentes:

```text
Tenant
  → Estabelecimento/escopo administrativo
  → UnidadeProdutiva
  → ÁreaRural / Talhão
  → Cultivo + Safra
  → Operações / Solo / Clima / Colheita
```

O domínio fundiário é separado por `ImovelRural` e `PropriedadeImovel`, com cardinalidade N:N conforme `AGRI-DOMAIN-001`. Isso é relevante para a POC porque o talhão operacional não deve ser confundido com o imóvel jurídico.

### 6.2 Menor unidade espacial

A menor unidade espacial operacional identificada é `AreaRural`, que pode representar talhão e possui `centroide_lat`/`centroide_lng`, área e hierarquia. Operações, análises de solo, imagens NDVI, previsões e produtos colhidos possuem `talhao_id` ou vínculo equivalente.

Há também geometrias e arquivos em GeoJSON/KML/KMZ/Shapefile, com cálculo de área em `core/services/geoprocessamento_service.py`. O ponto de atenção é que a existência de upload e centroide não garante que todos os talhões piloto tenham polígonos válidos, mesmo CRS, área coerente e cobertura suficiente para cruzamento com satélite.

**Conclusão:** capacidade espacial adequada para uma POC por talhão, condicionada à higienização e validação dos polígonos.

## 7. Safra, cultura e ciclo produtivo

`Safra` possui ciclo de vida e fases como planejamento, preparo de solo, plantio e desenvolvimento. `Cultivo` vincula safra, cultura/cultivar/commodity, datas de plantio/colheita, população, metas e produtividade real. `CultivoArea` liga o cultivo à área/talhão e permite associar análise de solo.

As operações possuem `safra_id`, `cultivo_id`, `talhao_id`, fase, data prevista/realizada, horário, área, operador, máquina, insumos, clima observado, GPS, custos e fotos. Colheita possui romaneio, produto colhido, peso, quantidade, qualidade e origem por safra/talhão.

**Capacidade:** suficientemente estruturada para formar a espinha dorsal de um dataset longitudinal.  
**Limitação:** histórico real, preenchimento consistente, unidades e fechamento de safra não foram medidos nesta auditoria. O modelo não equivale a um dataset pronto para ML.

## 8. Solo

O módulo canônico `agricola.analises_solo` é mais completo que os esqueletos legados encontrados em `apps/web/services/api/agricola/amostragem_solo`.

`AnaliseSolo` registra:

- talhão e, opcionalmente, unidade produtiva;
- data, laboratório, código e profundidade;
- textura: argila, silte e areia;
- pH, matéria orgânica, P, K, Ca, Mg, Al, H+Al e CTC;
- saturações e micronutrientes;
- irrigação, sistema de manejo, cultura atual e anterior;
- validade, laudo e observações.

`AnaliseSoloService` interpreta os dados com parâmetros por cultura/região e fallback agronômico documentado como Embrapa, gerando recomendações de calagem/fósforo/potássio e tarefas. Isso é inteligência agronômica baseada em regras/parâmetros, não ML.

O encadeamento desejável é representável:

`talhão → análise de solo → CultivoArea → safra/cultura → operações → clima → colheita`.

O risco é de qualidade e continuidade: o `cultura_nome` é textual na análise, há parâmetros opcionais e a associação a pontos amostrais detalhados não foi encontrada como uma malha espacial operacional. Para uma POC, laudos e amostras precisam ser normalizados e auditados antes de entrar em modelo.

## 9. Operações agrícolas

O modelo `OperacaoAgricola` é uma das partes mais fortes para a POC. Ele registra tipo/subtipo, descrição, safra, cultivo, talhão, tarefa, unidade produtiva, datas, horários, área, máquina, operador, clima observado, GPS, custo, fase, status, observações e fotos. `OperacaoExecucao` registra quantidades planejadas/executadas/devolvidas, unidade, custo, área e operador. `InsumoOperacao` registra produto, lote de estoque, dose, unidade, área, quantidade, custo, carência e EPI.

Isso possibilita gerar features futuras de calendário, intensidade de manejo, insumo/ha, atraso, custo/ha, janela climática, operador/máquina e sequência de operações.

A lacuna é a garantia de completude para dados de treinamento: não basta o campo existir. Será necessário definir quais campos são obrigatórios na POC, controlar unidades, duplicidade, retificação, timezone/data e consistência entre planejamento, execução e estoque.

## 10. Campo PWA e ground truth

O Campo PWA é um candidato real a instrumento de coleta de ground truth.

Evidências em `apps/campo/src/lib/db.ts`:

- IndexedDB via Dexie;
- tarefas de preparo, plantio, aplicação, colheita, irrigação, monitoramento de praga, amostragem de solo e checklist;
- eventos de caderno como plantio, pulverização, aplicação, irrigação, colheita, inspeção, ocorrência, monitoramento, visita, clima e solo;
- `safra_id`, `talhao_id`, tarefa, operador e payload operacional;
- fotos com metadados, data e latitude/longitude;
- status de sincronização, conflito, retificação e revisão.

Evidências em `sync/push.ts` e `sync/pull.ts`:

- outbox local;
- lotes de até 50 itens;
- push de tarefas e caderno;
- retry e falha terminal após tentativas;
- pull incremental por `last_sync_at`;
- reconciliação de eventos oficiais;
- upload de evidências após criação do evento no servidor;
- caches locais de fazendas, talhões, safras, insumos, recomendações e tarefas.

**Conclusão:** o PWA atende a arquitetura offline e pode coletar ground truth de operações, observações, fotos, GPS e resultado de campo. A POC deve limitar o protocolo a um conjunto pequeno de eventos obrigatórios; não deve presumir que toda a UX existente já está adaptada ao formulário técnico da Nestlé/APTA. Precisam ser validados aparelho, permissões de localização, tamanho de fotos, sincronização em 4G intermitente, conflitos e auditoria de tenant.

## 11. Inteligência climática

### Camada 1 — aquisição e armazenamento

Há `OpenWeatherClient` com consulta atual por localização ou lat/lon, domínio de Integrações com credenciais, jobs, health, políticas e eventos. Há `RegistroClima` com temperatura, umidade, chuva, vento, fonte e unidade produtiva.

Entretanto, o fluxo `ClimaService.sync_open_meteo` em `services/api/agricola/climatico/service.py` contém apenas retorno textual de sucesso. O fato de o provider técnico consultar OpenWeather não prova que a rota agrícola esteja persistindo uma série histórica completa em `RegistroClima`.

### Camada 2 — contextualização

O registro climático está ligado a `unidade_produtiva_id`, e o motor usa esse escopo para alertas/recomendações. Existe latitude/longitude em eventos climáticos e operações. Não foi comprovada uma contextualização completa e automatizada `clima → talhão → safra → cultura`, nem uma estratégia de interpolação/estação mais próxima por talhão.

### Camada 3 — inteligência

Existe Alert Engine climático e Recommendation Engine com limiares de vento, chuva, temperatura, umidade e idade do dado. As recomendações de pulverização, colheita e adubação explicam o motivo e tratam ausência de dado.

Isso é **regra operacional determinística**. É útil para uma POC de janela operacional, mas não deve ser chamado de modelo preditivo agronômico nem de prescrição validada para qualquer cultura.

### Camada 4 — predição

Não foi encontrada previsão agronômica validada usando clima. A feature `forecast` do provider OpenWeather está desabilitada por padrão e marcada como futura em `integracoes/openweather/services.py`.

**Conclusão:** clima operacional parcial; predição climática/agronômica não comprovada.

## 12. Previsão de produtividade

A entidade `PrevisaoProdutividade` tem campos compatíveis com uma futura solução: safra, talhão, data, produtividade estimada, margem de erro, fatores de peso, histórico climático, NDVI, versão do modelo e `run_id` potencialmente associado a MLflow.

Mas o serviço é explícito:

```text
"Integração real fará fetch de Clima, NDVI, info do solo"
"Mock calculation"
produtividade_estimada_sc_ha = 65.5
margem_erro_pct = 5.0
modelo_ia_versao = "rf_soja_v2"
```

Essa ocorrência é classificada como **modelagem de domínio + mock**, não como ML real. Não foram localizados:

- dataset de treinamento;
- pipeline de features;
- código de treino;
- artefato serializado;
- registro de experimento agronômico;
- separação treino/validação/teste;
- backtest temporal;
- baseline comparativo;
- MAE/RMSE/MAPE/R² por cultura e região;
- validação de safra futura;
- validação de campo;
- monitoramento de drift;
- protocolo de explicabilidade agronômica.

O `IAPredicaoRiscoService` não preenche esse gap: trata tendência financeira de custos/receitas. O `IAGrowthService` também não é agronômico.

**Resposta técnica atual:** o DeepFarms pode hospedar o ciclo de dados e a interface de uma futura previsão, mas não pode afirmar que possui previsão de produtividade plenamente validada.

## 13. Sensoriamento remoto

### NDVI e satélite

`ImagemNDVI` possui talhão, data de captura, cobertura de nuvens, índice médio/mínimo/máximo, URL de imagem colorida, URL de dado bruto e satélite default Sentinel-2. Há série temporal e componente web `ndvi-talhao.tsx`.

O serviço `NDVIService.sync_sentinel2_data` descreve o fluxo Copernicus/Sentinel-2, filtro de nuvens, bandas B04/B08, cálculo NDVI e armazenamento S3/MinIO, mas termina em “Sincronização agendada com sucesso” e identifica a lógica como mock. Portanto:

- estrutura de domínio: **EXISTENTE**;
- série/visualização: **PARCIALMENTE EXISTENTE**;
- ingestão Sentinel-2 real: **AUSENTE/INCOMPROVADA**;
- processamento raster/GeoTIFF real: **AUSENTE/INCOMPROVADO**;
- EVI, índices adicionais, drones e multiespectral: **AUSENTE**.

### Reaproveitamento

A entidade por talhão e o geoprocessamento territorial são reaproveitáveis. O provider de satélite deve passar pelo domínio oficial de Integrações, não por chamadas ad hoc no frontend.

## 14. IoT e sensores

O repositório contém integrações de máquinas John Deere, Case IH e New Holland, telemetria legada e migrations para `sensores_iot`, `sensores_leituras`, `estacoes_meteorologicas` e `leituras_meteorologicas`. Também existe a arquitetura transversal de Integrações com categoria `IoT`, jobs, health, eventos e observabilidade.

Isso demonstra **capacidade arquitetural reaproveitável**, não uma estação meteorológica ou sensor de solo agrícola operacional já conectado ao DeepFarms. Não foi encontrada uma cadeia verificável `device → leitura → talhão/safra → qualidade → dashboard/modelo` para sensores de solo ou pluviômetros.

Classificação:

- provider externo de IoT: **INTEGRAÇÃO FUTURA POSSÍVEL**;
- telemetria de máquinas: **BASE EXISTENTE/PARCIAL**;
- sensores agrícolas de solo: **AUSENTE como capacidade comprovada**;
- estação meteorológica própria: **AUSENTE como fluxo operacional comprovado**.

## 15. Arquitetura de integrações

O documento `INTEGRATIONS-ARCH-01.md` já prevê categorias `Satélite`, `Clima`, `IoT`, `APIs Externas`, `Armazenamento` e `Business Intelligence`. Também define escopos, credenciais, jobs, health, logs, métricas, eventos e isolamento tenant-aware.

A arquitetura pode receber providers de meteorologia, satélite, IoT ou modelo externo sem criar outro framework. O caminho correto para uma POC é reutilizar:

1. cadastro de provider e escopo;
2. credencial segura;
3. `IntegrationJob`;
4. `IntegrationHealth`;
5. evento/outbox;
6. subscriber do domínio agrícola;
7. persistência em entidade canônica;
8. consumo pelo Web/PWA/analytics.

O fato de a arquitetura suportar o caminho não significa que cada provider da lista esteja implementado.

## 16. Dataset agrícola disponível

| Dimensão | Entidade/origem | Granularidade | Histórico | Qualidade esperada | Uso futuro em IA |
|---|---|---|---|---|---|
| Propriedade/UP | `Propriedade`, `UnidadeProdutiva` | tenant/UP | Cadastro acumulado | Média; depende de preenchimento | Contexto e agrupamento |
| Talhão | `AreaRural` | talhão/centroide/polígono | Cadastro + alterações | Média; geometria precisa ser validada | Unidade espacial e máscara |
| Cultura/variedade | `Safra`, `Cultivo`, catálogo de culturas | cultivo/talhão/safra | Datas e safras | Boa estruturalmente; histórico desconhecido | Segmentação do modelo |
| Solo | `AnaliseSolo`, parâmetros agronômicos | talhão/data/profundidade | Datas de laudos | Parcial; amostras e cobertura desconhecidas | Features de fertilidade |
| Clima | `RegistroClima`, OpenWeather | UP/data; operação com observado | Histórico não comprovado | Parcial; sync agrícola tem stub | Variáveis agrometeorológicas |
| NDVI | `ImagemNDVI` | talhão/data | Estrutura existe; ingestão real não provada | Baixa até provar pipeline | Vigor e trajetória |
| Operações | `OperacaoAgricola`, execução, insumos | operação/talhão/safra/data | Registrável; volume desconhecido | Boa estrutura, preenchimento crítico | Manejo e causalidade operacional |
| Mão de obra | `operador_id`, pessoas, caderno | operação/evento/pessoa | Existente onde informado | Parcial | Intensidade e execução |
| Máquinas | `maquina_id`, telemetria/frota | operação/máquina | Parcial | Parcial | Janela, eficiência e custo |
| Ocorrências | `CadernoCampoEntrada`, monitoramento, visitas | evento/talhão/data/GPS/foto | Registrável | Parcial; taxonomia precisa ser fechada | Labels e explicações |
| Colheita | romaneio, `ProdutoColhido` | lote/talhão/safra/data | Estruturada | Boa para ground truth, se conciliada | Target de produção/produtividade |
| Qualidade | laudos e atributos do produto colhido | lote/data | Parcial | Depende de medição | Qualidade/predição secundária |

### Dataset longitudinal

O esquema é suficiente para **começar** a construir um dataset longitudinal por talhão/safra. Não há evidência de que já exista um dataset longitudinal limpo e com volume suficiente para treinar um modelo. O mínimo para afirmar isso exigiria contagem real de linhas, cobertura temporal, taxa de preenchimento, consistência das chaves e número de safras fechadas por cultura.

## 17. GAPs classificados

### GAP de plataforma

- protocolo específico de dataset agrícola/feature store não foi identificado;
- governança de versões de modelo, métricas e lineage agronômico não foi identificada;
- processamento raster e séries de sensoriamento remoto ainda não estão comprovados;
- qualidade/normalização geoespacial para análise por talhão requer validação.

Não há evidência de necessidade de redesenhar o monólito ou criar uma arquitetura paralela.

### GAP de integração

- sincronização real do Open-Meteo/RegistroClima na camada agrícola;
- ingestão Sentinel-2/Copernicus e armazenamento/processamento de imagens;
- provider de sensores de solo/estações, se o desafio os exigir;
- eventual integração com dados Nestlé/APTA e contratos de importação/exportação.

### GAP de dados

- número e qualidade de safras fechadas por cultura;
- labels confiáveis de produtividade por talhão;
- série climática alinhada à época e à geometria;
- séries NDVI reais e sem nuvens;
- histórico de solo com profundidade e amostragem consistentes;
- protocolo de ground truth de campo;
- metadados de unidade, conversão e timezone.

### GAP de inteligência

- modelo de produtividade/estimativa de safra real;
- definição do alvo: sc/ha, kg/ha, produção total, janela de colheita ou risco;
- feature engineering temporal/espacial;
- baseline estatístico e comparação com modelo ML;
- explicação agronômica e regras de segurança;
- alertas calibrados para a cultura piloto.

### GAP de validação

- não há evidência de acurácia de previsão;
- não há validação fora da amostra nem por safra futura;
- não há validação com agrônomo Nestlé/APTA;
- não há teste de campo com ground truth coletado sob protocolo;
- não há benchmark de latência, volume ou sincronização em rede rural para o cenário da POC.

### GAP de UX

- falta uma visão específica da POC com linha do tempo talhão/safra;
- falta tornar explícita a proveniência, idade e confiança de cada dado;
- falta fluxo de revisão/aceite do técnico para labels e recomendações;
- o PWA tem capacidades genéricas, mas não foi comprovado como formulário específico do desafio.

## 18. Proposta de POC

### 18.1 Escopo recomendado

Uma POC deve escolher uma cultura, uma decisão e uma escala pequena. O menor incremento tecnicamente validável seria:

1. selecionar propriedades e talhões piloto;
2. importar e validar polígonos, cultura, safra, área e datas;
3. definir um contrato de dados Nestlé/APTA;
4. sincronizar clima real por coordenada e registrar a fonte/idade;
5. conectar uma fonte de imagem real ou começar apenas com dados fornecidos pelo parceiro;
6. configurar coleta obrigatória no Campo PWA para operações, ocorrências, fotos/GPS e colheita;
7. fechar o protocolo de ground truth;
8. entregar dashboard temporal por talhão/safra;
9. iniciar com baseline explicável — por exemplo, meta histórica ou média por estágio — antes de declarar ML;
10. somente com dados suficientes, treinar e avaliar modelo exploratório;
11. comparar previsão com colheita observada e registrar erro, confiança e limitações.

### 18.2 Componentes utilizáveis imediatamente

- cadastro territorial e talhão;
- safra/cultivo e fases;
- registro de operações e insumos;
- análises de solo e recomendações por regras;
- caderno de campo e fotos/GPS;
- offline/sync do Campo PWA;
- registro de colheita e qualidade;
- alertas e recomendações climáticas determinísticas;
- RLS/RBAC e integração multiprovider como fundação;
- dashboards Web já existentes como base de composição.

### 18.3 Componentes que exigem desenvolvimento específico da POC

- ingestão/normalização dos dados Nestlé/APTA;
- ingestão climática e satélite real, se exigidas;
- formulário de coleta e dicionário de dados da cultura;
- pipeline de qualidade e dataset longitudinal;
- dashboard de monitoramento e proveniência;
- modelo exploratório e avaliação, se o objetivo exigir previsão;
- autenticação, exportação e governança de acesso para parceiros;
- critérios de sucesso e relatório final comparando previsão versus observado.

### 18.4 O que não deve entrar na primeira POC

- várias culturas e regiões simultaneamente;
- drones, IoT, Sentinel, ML e integrações corporativas todos ao mesmo tempo;
- promessa de prescrição agronômica autônoma;
- previsão de produtividade sem ground truth;
- claims de acurácia sem janela de validação definida;
- reabertura da arquitetura ERP/Sankhya;
- criação de uma segunda arquitetura de integrações;
- escopo completo de ERP, financeiro, pecuária ou ESG que não seja necessário à decisão escolhida.

## 19. Perguntas prováveis da banca/Nestlé/APTA

| Pergunta | Resposta que o DeepFarms pode dar hoje | Evidência | Risco/GAP |
|---|---|---|---|
| O que já funciona hoje? | Gestão operacional agrícola, safra, talhão, operações, solo, colheita, caderno offline, alertas/recomendações e dashboards parciais. | Módulos em `services/api/agricola`, `apps/campo`, `apps/web`. | Necessário demonstrar o fluxo completo em ambiente piloto. |
| O que ainda precisa ser desenvolvido? | Integração real de dados externos, dataset, protocolo de coleta, visão da POC e validação da inteligência. | Stubs de clima/NDVI e previsão mockada. | Escopo e prazo dependem da cultura e dos dados parceiros. |
| Qual o diferencial? | Contextualizar dados no ciclo operacional e coletar o evento real no campo, inclusive offline, em vez de entregar somente um modelo ou dashboard. | `AreaRural`, `Safra`, `OperacaoAgricola`, caderno PWA, colheita. | Deve ser demonstrado com dados reais; não afirmar unicidade de mercado. |
| Quais dados são utilizados? | Dados territoriais, safra/cultura, operações, insumos, solo, observações, clima, colheita e qualidade, quando preenchidos. | Modelos e schemas agrícolas. | Disponibilidade histórica e qualidade ainda não foram medidas. |
| Qual a granularidade espacial? | Talhão/`AreaRural` é a unidade operacional mínima; UP é o fallback para clima. | FKs `talhao_id`, centroides e geoprocessamento. | Polígonos e CRS dos pilotos precisam ser validados. |
| Funciona offline? | O Campo PWA tem IndexedDB, outbox, push/pull, retry, conflito e upload de evidências. | `apps/campo/src/lib/db.ts`, `sync/push.ts`, `sync/pull.ts`. | Validar em dispositivos e redes do piloto. |
| Como os dados são coletados? | Formulários/tarefas/eventos no Campo PWA; fotos e GPS; sincronização quando a conectividade retorna. | `CampoEventoOffline`, `LocalTask`, `CadernoEvidenciaOffline`. | O protocolo Nestlé/APTA ainda não foi configurado. |
| Existe histórico? | O modelo suporta histórico de safras, operações, solo, clima e colheita; o volume real não foi auditado. | Entidades e filtros temporais. | Não declarar histórico suficiente sem contagem e profiling. |
| Existe previsão de produtividade? | Existe endpoint e entidade de previsão, mas hoje a geração é mockada e fixa. | `agricola/previsoes/service.py`. | Não há ML, acurácia ou validação. |
| Qual a acurácia? | Não há acurácia agronômica comprovada para informar. | Ausência de métricas, treino e backtest. | Alto risco se houver promessa comercial. |
| Como será validada? | Por comparação temporal e espacial entre previsão, baseline e colheita real, com avaliação técnica do parceiro e registro de erro por talhão/safra. | Estrutura de colheita e previsão permite o protocolo. | O protocolo ainda precisa ser definido. |
| Quais dados Nestlé/APTA seriam necessários? | Polígonos, cultura/cultivar, calendário, histórico de produtividade/colheita, manejo, solo, clima/satélite disponível e definição do target. | Necessidade derivada do dataset e não do PDF ausente. | Confirmar no desafio original e em reunião técnica. |
| Como integrar satélite/sensores? | Usando o domínio oficial de Integrações, jobs, health, eventos e persistência canônica. | `INTEGRATIONS-ARCH-01.md`, OpenWeather. | Satellite/IoT agrícola ainda não têm pipeline comprovado. |
| Qual capacidade de escala? | A base usa monólito modular, PostgreSQL, Redis, Celery e RLS; uma POC pequena é plausível. | Inventário arquitetural e `main.py`. | Fazer benchmark antes de escala corporativa. |
| Como funciona multi-tenant? | `tenant_id`, dependências de tenant, RBAC e RLS protegem escopos; PWA usa sessão/device token. | Playbook, routers e modelos. | Dados compartilhados com Nestlé exigem DPA, escopos e auditoria. |
| Como trata LGPD/segurança? | Há isolamento, RBAC, JWT, auditoria e separação de credenciais de integração. | Arquitetura e middleware. | Definir minimização, base legal, retenção e exportação para a POC. |
| Existem APIs? | Há REST em `/api/v1`, rotas agrícolas e endpoints de sync. | `services/api/main.py` e routers. | Contrato externo, rate limit e versionamento precisam ser fechados. |
| Quanto tempo para a POC? | Não é possível estimar com segurança sem PDF, cultura, dados e critérios de sucesso. | Documento do desafio ausente. | Não apresentar prazo fechado sem discovery técnico. |
| Qual o número mínimo de propriedades/talhões? | Deve ser definido por objetivo estatístico e logística; tecnicamente a plataforma suporta piloto pequeno. | Multi-tenant e vínculos por talhão. | Amostra insuficiente inviabiliza validação de ML. |
| Quais critérios de sucesso? | Cobertura de coleta, sincronização, completude, rastreabilidade, adoção e erro da previsão versus baseline/colheita. | Capacidades de telemetria, PWA e colheita. | A Nestlé/APTA precisa aprovar métricas e janela. |

## 20. Diferenciais competitivos verificáveis

O diferencial técnico defensável é a combinação de:

- contexto territorial por talhão;
- ciclo produtivo e operações com datas e insumos;
- integração de solo, clima, ocorrência e colheita;
- coleta offline com fotos/GPS e reconciliação;
- rastreabilidade e custos conectados à operação;
- RLS/multi-tenant e governança de integração;
- possibilidade de transformar a operação em ground truth.

Isso permite que um modelo futuro não seja apenas uma caixa-preta que recebe imagem e devolve score. O modelo pode ser confrontado com o que realmente aconteceu no campo. Essa é uma vantagem arquitetural potencial sobre um dashboard isolado, uma estação meteorológica sem contexto ou uma startup que tenha apenas um modelo.

O diferencial ainda é **potencial e demonstrável por arquitetura**, não uma vantagem de acurácia. Não há base para alegar superioridade preditiva, número de clientes, redução de custo ou acurácia de mercado.

## 21. Riscos

1. **Risco documental:** o PDF do desafio não está disponível; requisitos, cultura e critérios podem alterar o scoring.
2. **Risco de overclaim:** entidade `PrevisaoProdutividade` e `modelo_ia_versao` podem ser confundidos com ML real.
3. **Risco de dados:** registros existem, mas cobertura histórica e completude não foram quantificadas.
4. **Risco de integração:** OpenWeather e NDVI têm componentes técnicos, porém os fluxos agrícolas/imagéticos relevantes ainda têm stubs ou flags futuras.
5. **Risco espacial:** centroides e upload geográfico não garantem polígonos válidos, CRS uniforme ou cobertura por talhão.
6. **Risco operacional:** PWA offline precisa ser validado no hardware, browser, permissões e rede do piloto.
7. **Risco de governança:** dados Nestlé/APTA exigem contrato, minimização, autorização, retenção, segregação e auditoria.
8. **Risco de duplicidade:** árvore legada em `apps/web/services/api` pode causar confusão sobre o runtime canônico.
9. **Risco agronômico:** regras de limiar não são prescrição universal; devem ser aprovadas para a cultura e região.
10. **Risco estatístico:** poucos talhões/safras podem gerar overfitting e falsa confiança.

## 22. Scoring

Notas provisórias, considerando o escopo descrito na demanda e a ausência do PDF. Não representam aderência formal ao edital.

| Dimensão | Nota (0–10) | Justificativa |
|---|---:|---|
| Aderência ao problema | 6 | A plataforma cobre o ciclo operacional, mas a decisão Nestlé não pôde ser confirmada sem PDF. |
| Aderência funcional | 6 | Há ampla base agrícola; sensores, satélite real e previsão avançada são incompletos. |
| Aderência arquitetural | 8 | Modular monolith, RLS, eventos, integrações e PWA suportam evolução. |
| Dados agrícolas disponíveis | 6 | Modelo longitudinal é forte; volume/qualidade históricos são desconhecidos. |
| Coleta de dados em campo | 8 | PWA, offline, tarefas, caderno, fotos e GPS são concretos. |
| Capacidade offline | 8 | Dexie, outbox, push/pull e conflitos estão implementados; falta validação específica. |
| Georreferenciamento | 7 | Talhão, centroides, arquivos geográficos e geoprocessamento; qualidade dos polígonos ainda é risco. |
| Inteligência climática | 5 | Regras/alertas existem; ingestão agrícola e previsão climática não estão totalmente comprovadas. |
| Previsão de produtividade | 1 | Entidade/endpoint, mas cálculo mockado e fixo. |
| IA/ML agrícola | 2 | Há infraestrutura de IA geral e campos de modelo, sem pipeline agronômico validado. |
| Sensoriamento remoto | 4 | NDVI modelado e UI, ingestão Sentinel/processamento real não comprovados. |
| IoT | 4 | Arquitetura e legados existem; provider agrícola operacional não comprovado. |
| Integrações | 7 | Domínio multiprovider, OpenWeather e governança existem. |
| Escalabilidade | 7 | Stack e isolamento suportam POC; não há benchmark deste caso. |
| Segurança/multi-tenant | 8 | RLS/RBAC/JWT e contratos tenant-aware são fundação forte. |
| Prontidão para POC | 6 | Pronta como plataforma de coleta/contexto; não pronta como previsão validada. |

**ADERÊNCIA GERAL PROVISÓRIA: 6,0/10.**

O número é deliberadamente limitado pela ausência do desafio e pelo gap de inteligência preditiva. Não é uma nota de qualidade geral do produto.

## 23. Recomendação executiva

### 1. Devemos inscrever o DeepFarms no desafio?

**Sim, com posicionamento condicionado.** A inscrição faz sentido se o desafio aceitar uma plataforma para instrumentar e validar a solução, e não exigir que um modelo de produtividade já esteja comprovadamente pronto. Antes da submissão final, o PDF deve ser recuperado e a matriz recalculada.

### 2. O que já possuímos que atende ao problema?

Temos representação territorial por talhão, ciclo de safra/cultura, operações, solo, caderno de campo, fotos/GPS, PWA offline, colheita, qualidade, alertas, recomendações determinísticas, APIs, integração multiprovider, RLS e base para dashboards.

### 3. Qual é o maior GAP?

O maior gap é **inteligência/validação**, precedido por dados: não existe modelo agronômico de produtividade/safra treinado, avaliado e validado em campo, nem dataset longitudinal comprovadamente suficiente.

### 4. O GAP exige evolução ou redesenho arquitetural?

Exige principalmente evolução de dados, integrações, pipeline de análise e validação. Não há evidência de necessidade de redesenho arquitetural. O domínio oficial de Integrações e o monólito modular devem ser reutilizados.

### 5. O que deveria fazer parte de uma POC?

Uma cultura, uma decisão agronômica, poucas propriedades/talhões, polígonos validados, dados parceiros, coleta PWA de ground truth, clima real, eventualmente uma fonte de satélite, dashboard temporal, baseline e protocolo de validação.

### 6. O que NÃO deveria fazer parte da POC?

Escopo multi-cultura, drones, IoT, satélite e ML simultaneamente; prescrição autônoma; promessa de acurácia; ERP/Sankhya; módulos não relacionados à decisão piloto.

### 7. O que podemos afirmar para a Nestlé hoje?

Que o DeepFarms é uma plataforma agrícola operacional e multi-tenant, com unidade espacial por talhão, gestão de safra/operação/solo/colheita, PWA offline para coleta de dados e arquitetura para integrar clima, satélite e IoT. Pode ser usado para estruturar uma POC e gerar ground truth rastreável.

### 8. O que não devemos afirmar ainda?

Não afirmar modelo de IA agronômica validado, previsão de produtividade pronta, estimativa de safra com acurácia conhecida, ingestão Sentinel-2 operacional, cobertura histórica suficiente ou integração de sensores agrícolas pronta.

### 9. Qual a melhor proposta de valor técnica?

“Usar uma plataforma operacional por talhão, com coleta offline e rastreável no campo, para integrar dados de solo, clima, manejo, sensoriamento e colheita e validar progressivamente uma inteligência agronômica explicável.”

### 10. Qual o próximo passo recomendado?

Obter o PDF original e realizar uma sessão de alinhamento com Nestlé/APTA para fixar cultura, decisão, target, dados disponíveis, propriedades piloto, janela temporal e critérios de sucesso. Em seguida, fazer profiling dos dados reais e uma prova de fluxo ponta a ponta antes de assumir qualquer compromisso de ML.

## 24. Próximo passo técnico recomendado

Sem implementar nesta etapa, a sequência de decisão deveria ser:

1. disponibilizar `AptaHub-Conecta-Desafio-Nestle.pdf` no workspace;
2. revisar os requisitos formais e substituir os requisitos provisórios desta auditoria;
3. escolher a decisão agronômica única da POC;
4. inventariar dados reais de propriedades/talhões/safras;
5. definir o dicionário de dados e o ground truth;
6. confirmar o runtime canônico entre `services/api` e cópias em `apps/web/services/api`;
7. só então estimar evolução de integração, coleta e inteligência.

## Conclusão

O DeepFarms não é um projeto vazio diante do desafio: a camada operacional, territorial e de coleta é uma base relevante e potencialmente diferenciadora. Porém, também não é correto apresentá-lo como uma solução de IA preditiva agronômica pronta. A distância entre a base existente e uma POC validável é principalmente uma distância de dados, integração e validação científica/operacional — não um motivo, pelas evidências atuais, para redesenhar a arquitetura.

**Veredicto final: `POC CONDICIONADA`.**

### Evidências principais consultadas

- `docs/architecture/agrosaas-master-context.md`
- `docs/architecture/agrosaas-ai-rules.md`
- `docs/architecture/architecture-inventory.md`
- `docs/architecture/agrosaas-data-model.md`
- `docs/architecture/agrosaas-routing-map.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `services/api/agricola/safras`, `cultivos`, `operacoes`, `analises_solo`, `climatico`, `ndvi`, `previsoes`, `caderno`, `monitoramento` e `colheita`
- `services/api/integracoes/openweather`
- `services/api/recommendations/providers/clima_provider.py`
- `apps/campo/src/lib/db.ts`, `sync/push.ts`, `sync/pull.ts`
- `docs/implementation/reports/CLIMATE-01-AUDITORIA-INTELIGENCIA-CLIMATICA.md`
- `docs/implementation/reports/CLIMATE-05-RECOMENDACOES-OPERACIONAIS-MVP.md`
- `docs/implementation/reports/CLIMATE-GOV-01-AUDITORIA-FECHAMENTO-PRONTIDAO.md`

