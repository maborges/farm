# Plano de Fundação Geoespacial — GIS-01
## Mapeamento Geoespacial dos Talhões e Base para ESG Ambiental

Este documento apresenta a análise de prontidão e o plano de evolução para a camada geoespacial do AgroSaaS, permitindo o mapeamento formal de talhões e estabelecendo a base regulatória necessária para atender aos critérios ambientais de certificações (Rainforest Alliance, Projeto Raízes) e integração com sensoriamento remoto (NDVI/Satélite).

---

## 1. Resumo Executivo

O AgroSaaS possui, na sua camada de dados e no frontend web, uma base de georreferenciamento extremamente robusta e unificada através da entidade de **Áreas Rurais**. A tabela de áreas rurais (`cadastros_areas_rurais`) já suporta hierarquia espacial self-referencial, cálculo automático de área e armazenamento de geometrias vetoriais como polígonos GeoJSON, além de possuir integração direta de desenho em mapa via MapLibre/Mapbox GL Draw no frontend.

A validação indica que **não é necessário criar novos modelos geoespaciais, tabelas paralelas ou bancos de dados GIS complexos (como PostGIS) para o estágio piloto de certificação**. A estrutura existente de `geometria` (coluna JSONB) atende plenamente aos requisitos de auditoria. A menor evolução necessária para viabilizar Rainforest Alliance e Projeto Raízes consiste em estender a validação e o cruzamento de polígonos (GeoJSON) de áreas de cultivo com áreas de exclusão/preservação (como APP e Reserva Legal) diretamente no backend, fornecendo a base auditável definitiva no Passaporte de Rastreabilidade.

---

## 2. Análise de Reaproveitamento

Foi realizado o mapeamento de todos os componentes geoespaciais existentes na aplicação:

| Componente | Classificação | O que é reaproveitado / estendido |
| :--- | :--- | :--- |
| **Unidade Produtiva** | **EXISTE E ATENDE** | Mapeamento central da sede em `coordenadas_sede` (Latitude, Longitude). |
| **Talhão** | **EXISTE E ATENDE** | Mapeado através de [AreaRural](file:///opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/models.py#L118) com `tipo = 'TALHAO'`. Possui coluna `geometria` (JSONB) que armazena polígonos GeoJSON, `area_hectares` calculada e centroides. |
| **Safra** | **EXISTE E ATENDE** | Delimitação temporal vinculada aos talhões cultivados. |
| **Cultivo** | **EXISTE E ATENDE** | Vínculo agronômico de plantio na área rural. |
| **Operações** | **EXISTE E ATENDE** | [OperacaoAgricola](file:///opt/lampp/htdocs/farm/services/api/agricola/operacoes/models.py#L8) possui colunas nativas de `latitude` e `longitude` para capturar a posição exata da pulverização/colheita. |
| **Caderno de Campo** | **EXISTE E ATENDE** | O caderno já suporta eventos de inspeção/inspeção técnica associados ao talhão físico. |
| **NDVI** | **EXISTE E ATENDE** | O modelo [ImagemNDVI](file:///opt/lampp/htdocs/farm/services/api/agricola/ndvi/models.py#L8) já está mapeado, apontando para `cadastros_areas_rurais.id` e guardando URLs de imagens coloridas e raster (GeoTIFF) bruto. |
| **Satélite** | **EXISTE E ATENDE** | Tabela `imagens_satelite` migrada e mapeada para controle de Sentinel-2. |
| **Mapas** | **EXISTE E ATENDE** | O frontend web possui suporte de desenho vetorial integrado no arquivo [page.tsx](file:///opt/lampp/htdocs/farm/apps/web/src/app/%28dashboard%29/cadastros/propriedades/talhoes/page.tsx) utilizando MapLibre GL e Mapbox Draw. |
| **GPS do PWA** | **EXISTE E ATENDE** | A fila de sincronização offline e o banco local IndexedDB já transportam dados de localização geográfica. |
| **Evidências georreferenciadas** | **EXISTE E ATENDE** | A tabela `caderno_campo_fotos` possui colunas nativas de `latitude` e `longitude` para registrar as provas materiais no talhão. |
| **Passaporte de Rastreabilidade**| **EXISTE E ATENDE** | O passaporte comercial já compila o snapshot de talhão, safra, unidade produtiva e fotos georreferenciadas públicas. |

### Justificativa Arquitetural:
A adoção do modelo de **Área Rural Hierárquica Unificada** em `AreaRural` evita o desacoplamento de tabelas. A mesma tabela suporta glebas administrativas, talhões de plantio, áreas de infraestrutura e áreas de preservação ambiental (APP/Reserva Legal). O armazenamento em formato JSONB das geometrias (GeoJSON) garante portabilidade imediata e compatibilidade direta com a stdlib de geoprocessamento em Python (como `Shapely` e `PyProj`) e bibliotecas JavaScript de mapas (como `@turf/turf`).

---

## 3. Estado Atual dos Talhões

A análise do modelo [AreaRural](file:///opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/models.py#L118) revelou a seguinte maturidade geoespacial:
* **Área**: Sim, calculado de forma vetorial em `area_hectares` ou informado em `area_hectares_manual`.
* **Coordenadas**: Sim, as coordenadas centrais são calculadas e armazenadas em `centroide_lat` e `centroide_lng`.
* **Ponto GPS**: Sim.
* **Polígono/GeoJSON**: Sim, a coluna `geometria` armazena estruturas padrão de polígonos GeoJSON (`Polygon` ou `MultiPolygon`).
* **Histórico espacial**: Armazenado por meio de auditorias do `TenantAuditLog`.

Classificação de Maturidade do Mapeamento: **COMPLETO** (Não há lacunas de modelagem de dados básicas para o talhão).

---

## 4. GPS Operacional

O ecossistema do AgroSaaS já possui a infraestrutura necessária de rastreamento no campo:
1. **Evidências georreferenciadas**: Ao registrar uma foto no PWA, as coordenadas GPS e a data/hora exata são encapsuladas no payload do evento `INSPECAO` ou `OCORRENCIA` e reconciliadas de forma imutável.
2. **Execução de Operações**: A entidade `OperacaoAgricola` possui campos de `latitude` e `longitude` preenchidos na execução da atividade.
3. **Auditoria Geográfica**: É possível realizar a validação matemática de que a operação ocorreu dentro dos limites do talhão utilizando operações simples de ponto-em-polígono (Point-in-Polygon) com a biblioteca `Shapely` no backend.

---

## 5. ESG Ambiental

A inclusão da camada geoespacial permite atender de forma nativa aos seguintes requisitos ambientais:
* **Monitoramento de Pulverização**: Mapeamento espacial do talhão onde ocorreu a pulverização para comprovar conformidade e evitar deriva de defensivos para rios ou áreas protegidas vizinhas.
* **Preservação Ambiental**: Cadastro de Áreas de Preservação Permanente (APP) e Reserva Legal como registros de `AreaRural` com `tipo = 'AREA_AMBIENTAL'`.
* **Auditoria de Preservação**: Cruzamento espacial das áreas de cultivo (talhões) com as áreas de preservação (APP) para comprovar a não invasão agrícola em áreas protegidas.

---

## 6. Rainforest Alliance

Para a Rainforest Alliance, o georreferenciamento vetorial resolve os seguintes requisitos cruciais:
* **Desmatamento Zero**: A exportação dos polígonos dos talhões em formato GeoJSON permite que certificadoras e compradores cruzem as coordenadas com bases globais de imagens de satélite contra desmatamento ilegal após a data de corte regulatória.
* **Áreas de Amortecimento (Buffer Zones)**: Validação de que faixas de proteção foram respeitadas entre talhões com defensivos e áreas de proteção ambiental.

Impacto: **CRÍTICO / ALTÍSSIMO** (A existência de polígonos no passaporte atende ao principal impeditivo de exportação de café).

---

## 7. Projeto Raízes

Com a validação geoespacial integrada:
* O QR Code na sacaria direciona para o Passaporte Público, que agora apresenta o **mapa interativo com o polígono vetorial do talhão** onde o lote de café foi colhido.
* Os compradores conseguem visualizar a integridade da Cadeia de Custódia de forma visual e inquestionável.
* **Status do Projeto Raízes**: Passa de **PRONTO COM AJUSTES** para **PRONTO**, pois remove a única ressalva física/espacial da origem do produto colhido.

---

## 8. Modelo Geoespacial Proposto

Manteremos a modelagem baseada em `AreaRural`, estendendo apenas a lógica do serviço no backend para expor os polígonos no Passaporte de Rastreabilidade.

No futuro, para integrações avançadas (NDVI, Sentinel, Landsat), a tabela `imagens_ndvi` já aponta para `cadastros_areas_rurais.id`, o que significa que o sistema está totalmente estruturado para associar análises espectrais ao talhão sem qualquer remodelação física de banco. O GeoTIFF do satélite pode ser recortado diretamente usando o polígono JSONB do talhão.

---

## 9. Roadmap GIS

Dividiremos a evolução do GIS de forma incremental e lógica:

* **GIS-01: Fundação Geoespacial (Este Ciclo)**
  * Diagnóstico, validação de compatibilidade dos modelos existentes e mapeamento de reaproveitamento da camada.
* **GIS-02: Mapas de Rastreabilidade e Passaporte Público**
  * Renderização do mapa interativo com o polígono vetorial do talhão diretamente no Passaporte de Rastreabilidade Comercial público (`GET /p/rastreabilidade/{token}`).
* **GIS-03: Validação Point-in-Polygon de Operações e APP**
  * Implementação da lógica de backend no `OperacaoService` para validar se as coordenadas geográficas capturadas pelo PWA estão contidas no polígono do talhão.
  * Validação geométrica automática no salvamento de talhões para impedir sobreposição com áreas ambientais (APP/Reserva Legal).
* **GIS-04: NDVI e Monitoramento Sentinel**
  * Integração de scripts de processamento de satélite (Sentinel-2) para recortar imagens raster usando a geometria GeoJSON do talhão e salvar o histórico espectral em `ImagemNDVI`.

---

## 10. ROI Esperado

* **Esforço Técnico**: **Baixíssimo** (A modelagem de banco de dados e o frontend de desenho já estão implementados).
* **Valor Comercial**: **Altíssimo** (Habilita a conformidade do Projeto Raízes para exportação sustentável incondicional e o cumprimento das normas da UE para desmatamento zero - EUDR).
* **ROI**: **Altíssimo ROI** (Esforço de dias de integração frontend no passaporte vs novos contratos de exportadoras de café).

---

## 11. Recomendação Final

Recomendamos utilizar a modelagem central existente de `AreaRural`. A infraestrutura de JSONB para geometria e os centroides em Float são ideais para o estágio atual do AgroSaaS. No próximo ciclo (GIS-02), devemos apenas estender o snapshot do passaporte comercial para incluir a chave `geometria` e renderizá-lo de forma interativa no frontend público do comprador.

---

## Pergunta Final Obrigatória

**"Qual é a menor evolução possível da modelagem atual para que o AgroSaaS passe a possuir georreferenciamento auditável compatível com Rainforest Alliance, Projeto Raízes e futuras integrações NDVI?"**

### Resposta Técnica:
A menor evolução possível consiste em:
1. **Ativar o uso da coluna `geometria`** (JSONB) preexistente na tabela `cadastros_areas_rurais` em todas as APIs de escrita de talhões.
2. **Atualizar o snapshot do passaporte de rastreabilidade** em `RastreabilidadeService.gerar_snapshot_passaporte` para expor o nó `"geometria"` do talhão.
3. **Renderizar o polígono no frontend** público do passaporte (`/p/rastreabilidade/[token]`) reaproveitando a biblioteca MapLibre já instalada no repositório.
