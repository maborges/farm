# Épico: Integrações SICAR e Google Earth Engine/Sentinel-2

**Status:** Backlog — dependente de acessos externos e dados reais  
**Módulos:** Ambiental, Imóveis, Unidades Produtivas e Monitoramento  
**Última revisão:** 27/08/2026

## 1. Objetivo e premissas

Este épico permitirá consultar o SICAR/CAR e processar imagens Sentinel-2 no
Google Earth Engine (GEE), sempre vinculando o resultado à unidade produtiva,
imóvel rural e talhão corretos.

- Um produtor pode ter várias fazendas e uma fazenda várias unidades produtivas.
- O CAR pertence ao imóvel rural; o tratamento operacional pode ser filtrado
  pela unidade produtiva selecionada no topbar.
- Dados de SICAR/GEE são externos e não podem ser editados como se fossem
  dados cadastrais internos.
- Uma falha externa não apaga nem invalida o cadastro local.
- Nenhuma credencial ou chamada externa deve chegar ao navegador.

## 2. Situação atual

O produto já possui cadastros de imóvel rural com CAR, CCIR, NIRF, matrícula e
SIGEF, vínculos fundiários com unidades produtivas, registros CAR ambientais,
alertas e mapa MapLibre.

Rotas internas relacionadas:

```text
GET  /api/v1/ambiental/car
POST /api/v1/ambiental/car
POST /api/v1/ambiental/car/{id}/consultar-sicar
GET  /api/v1/ambiental/unidades/{unidade_id}/contexto-fundiario
GET  /api/v1/ambiental/alertas
GET  /api/v1/ambiental/dashboard
```

Essas rotas devem chamar adaptadores do backend, nunca o provedor externo
diretamente no frontend.

## 3. Referências e URLs oficiais

### SICAR/CAR

- Portal nacional: <https://www.car.gov.br/>
- Consulta pública e mapa: <https://consultapublica.car.gov.br/publico/>
- Central do proprietário/possuidor: <https://www.car.gov.br/#/consultar>
- Contatos dos órgãos estaduais: <https://www.car.gov.br/#/contatos>
- Manual do usuário: <https://www.car.gov.br/public/Manual.pdf>
- Regularização ambiental — SFB: <https://www.gov.br/florestal/pt-br/assuntos/regularizacao-ambiental>
- Serviço oficial de inscrição: <https://www.gov.br/pt-br/servicos/inscrever-imovel-rural-no-cadastro-ambiental-rural-car>

O portal público não deve ser presumido como uma API REST nacional estável.
Antes de implementar chamadas automáticas, confirmar com o SFB e com o órgão
estadual da UF:

- URL base autorizada, endpoints e versão;
- autenticação, limites e política de cache;
- campos que podem ser armazenados e redistribuídos;
- acesso a WMS/WFS, downloads ou demonstrativos;
- regras para uso comercial e indisponibilidade.

Se não houver API autorizada, o MVP deve usar consulta manual assistida ou
arquivo oficial fornecido pelo usuário/órgão. Não automatizar login, CAPTCHA
ou scraping da Central do Proprietário.

### Google Cloud / Earth Engine

- Seleção de projeto: <https://console.cloud.google.com/projectselector>
- Registro Earth Engine: <https://console.cloud.google.com/earth-engine>
- Guia de acesso: <https://developers.google.com/earth-engine/guides/access>
- Autenticação: <https://developers.google.com/earth-engine/guides/auth>
- Contas de serviço: <https://developers.google.com/earth-engine/guides/service_account>
- API REST: <https://developers.google.com/earth-engine/reference/rest>
- IAM: <https://console.cloud.google.com/iam-admin/iam>
- Credenciais OAuth: <https://console.cloud.google.com/apis/credentials>
- Biblioteca de APIs: <https://console.cloud.google.com/apis/library>
- Catálogo Sentinel-2 SR: <https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED>

Endpoint REST documentado:

```text
https://earthengine.googleapis.com
```

Preferir o cliente Python `earthengine-api` no backend. Usar REST diretamente
somente quando necessário.

## 4. Cadastros e acessos

### 4.1 SICAR

1. Identificar o responsável técnico e a empresa consumidora.
2. Contactar o SFB e o órgão estadual de cada UF atendida.
3. Solicitar documentação e credencial técnica, se existir.
4. Confirmar autorização para consultar e armazenar dados e geometrias.
5. Obter um CAR real válido, com autorização de uso em homologação.
6. Obter exemplos de sucesso, CAR inexistente, cadastro pendente e erro.
7. Registrar a URL efetivamente autorizada em configuração por ambiente.

Não usar credenciais pessoais do produtor no servidor. Se a fonte exigir a
Central do Proprietário, o fluxo deve ser assistido ou formalmente integrado.

### 4.2 Earth Engine

1. Criar projetos separados para HML e produção.
2. Registrar cada projeto no Earth Engine.
3. Habilitar Earth Engine API e, se necessário, Cloud Storage.
4. Criar service account exclusiva da API.
5. Conceder apenas os papéis mínimos necessários.
6. Preferir Application Default Credentials em VM/Cloud Run.
7. Se usar chave JSON, guardá-la no Secret Manager, nunca no Git.
8. Configurar quota e orçamento do projeto.
9. Testar um polígono pequeno e período curto.
10. Definir retenção, custo máximo e alertas de quota.

Variáveis sugeridas:

```dotenv
SICAR_ENABLED=false
SICAR_BASE_URL=
SICAR_API_TOKEN_SECRET_NAME=
GEE_ENABLED=false
GEE_PROJECT_ID=agrosaas-gee-hml
GEE_SERVICE_ACCOUNT_EMAIL=
GEE_CREDENTIALS_SECRET_NAME=
GEE_BUCKET_NAME=
GEE_MAX_CLOUD_PERCENTAGE=30
GEE_DEFAULT_LOOKBACK_DAYS=30
GEE_REQUEST_TIMEOUT_SECONDS=60
```

## 5. Escopo funcional SICAR

1. Usuário seleciona a unidade produtiva no topbar.
2. Sistema lista imóveis vinculados à unidade e exibe o aviso de contexto.
3. Usuário confirma o imóvel e o CAR já cadastrado.
4. Backend valida tenant, unidade, imóvel e vínculo fundiário.
5. Adaptador consulta o endpoint autorizado, com timeout e correlation ID.
6. Resposta é normalizada para o contrato interno.
7. Sistema grava/atualiza `amb_registros_car`, sem editar o cadastro de origem.
8. Sistema registra origem, situação, data, hashes e divergências.
9. Interface diferencia `CONSULTADO`, `NAO_CONSULTADO`, `INDISPONIVEL` e
   `DIVERGENTE`.

Contrato normalizado mínimo:

```json
{
  "codigo_car": "SP-0000000-0000000000000000000000",
  "situacao_sicar": "ATIVO",
  "uf": "SP",
  "municipio": "Exemplo",
  "area_total_ha": 0,
  "area_app_ha": 0,
  "area_rl_ha": 0,
  "area_vegetacao_nativa_ha": 0,
  "area_uso_consolidado_ha": 0,
  "geometria": null,
  "consultado_em": "2026-08-27T12:00:00Z",
  "fonte": "SICAR"
}
```

## 6. Escopo funcional GEE/Sentinel-2

1. Usuário seleciona unidade, imóvel ou talhão.
2. Backend obtém e valida o GeoJSON interno.
3. Sistema valida CRS, área, complexidade e período.
4. Backend cria job assíncrono idempotente.
5. Worker consulta `COPERNICUS/S2_SR_HARMONIZED`.
6. Worker aplica máscara de nuvens e escala de reflectância.
7. Worker calcula NDVI e/ou composição RGB.
8. Resultado é salvo com coleção, cenas, parâmetros, geometria e hash.
9. Frontend acompanha o job e mostra a camada no mapa.

Fórmula inicial:

```text
NDVI = (B8 - B4) / (B8 + B4)
```

Na coleção oficial, B4 é vermelho, B8 é infravermelho próximo e a
reflectância é escalada por 10000. O produto deve guardar a coleção e os
parâmetros para permitir auditoria e reprocessamento.

## 7. Arquitetura técnica

```text
Frontend autenticado
  -> API Ambiental
      -> Service com tenant/RLS
          -> SicarClient / SicarAdapter
          -> GeeClient / GeeAdapter
          -> fila de jobs e normalizadores
              -> persistência e auditoria
```

Estrutura sugerida:

```text
services/api/ambiental/integrations/
  sicar_client.py
  sicar_schemas.py
  gee_client.py
  gee_schemas.py
  exceptions.py
services/api/ambiental/jobs/
  sicar_sync.py
  gee_analysis.py
```

Regras: timeout obrigatório; retry apenas para timeout, 429 e 5xx; backoff;
circuit breaker; limite de payload; idempotency key; nenhum segredo em logs;
chamadas externas somente em services/workers; respostas externas isoladas dos
schemas de domínio.

## 8. Persistência

Reaproveitar `amb_registros_car` para o consolidado. Criar, se necessário,
`amb_consultas_externas` com:

```text
id, tenant_id, unidade_produtiva_id, imovel_rural_id, registro_car_id,
provedor, endpoint_referencia, solicitado_em, concluido_em, status,
request_hash, response_hash, http_status, erro_codigo, erro_mensagem,
payload_normalizado, payload_bruto_referencia, created_by
```

Para GEE, criar execução com unidade, imóvel/talhão, `geometria_hash`, produto,
coleção, período, nuvens, status, `gee_task_id`, URI do resultado, parâmetros,
erro e timestamps. O payload bruto só deve ser retido quando permitido.

## 9. Plano de implementação

### Fase 0 — autorização

- [ ] Contrato SICAR confirmado por UF.
- [ ] URL, autenticação, limites e retenção documentados.
- [ ] CAR válido de homologação autorizado.
- [ ] Projetos GEE HML/produção registrados.
- [ ] Service account, secret, quota e orçamento configurados.

### Fase 1 — adaptadores

- [ ] Schemas externos e normalizadores.
- [ ] `SicarClient` com timeout, retry e tratamento de indisponibilidade.
- [ ] `GeeClient` com ADC/Secret Manager.
- [ ] Mocks e respostas gravadas para desenvolvimento.
- [ ] Health checks sem expor credenciais.

### Fase 2 — jobs e banco

- [ ] Migração de auditoria.
- [ ] Idempotência, cache e circuit breaker.
- [ ] Jobs CAR/GEE assíncronos.
- [ ] Status `PENDENTE`, `PROCESSANDO`, `CONCLUIDO`, `ERRO` e `INDISPONIVEL`.
- [ ] Reprocessamento manual controlado.

### Fase 3 — API e frontend

- [ ] Endpoints internos por unidade/imóvel/talhão.
- [ ] Histórico de consultas e jobs.
- [ ] Aviso explícito da unidade selecionada.
- [ ] Origem, data e validade visíveis.
- [ ] Campos externos somente leitura.
- [ ] Progresso e resultado GEE no mapa.

### Fase 4 — testes e produção

- [ ] Unitários de clientes e normalizadores.
- [ ] Contrato com respostas oficiais anonimizadas.
- [ ] Testes de 404, 429, 5xx, timeout, quota e payload inválido.
- [ ] Testes RLS entre dois tenants.
- [ ] Homologação com CAR real autorizado.
- [ ] Smoke test pós-deploy, métricas e runbook.

## 10. Testes obrigatórios

Fixtures: dois tenants, duas fazendas, duas unidades produtivas, imóveis
vinculados, talhão com GeoJSON válido, CAR válido e respostas externas de
sucesso/ausência/indisponibilidade.

Casos de aceite:

1. Unidade A não acessa imóvel da unidade B.
2. CAR local continua visível sem conexão externa.
3. Indisponibilidade não apaga nem invalida dado local.
4. Consulta repetida não duplica registros.
5. CAR inexistente não retorna 500.
6. Geometria inválida não cria job GEE.
7. Quota excedida apresenta estado operacional compreensível.
8. Resultado contém origem, coleção, período, parâmetros e hash.
9. Nenhuma credencial aparece em resposta ou log.
10. As telas mostram a unidade produtiva selecionada.

## 11. Segurança, métricas e rollback

- Aplicar RLS e validar todos os vínculos antes da chamada externa.
- Usar TLS, Secret Manager/ADC, rotação e princípio do menor privilégio.
- Redigir tokens, cookies e payloads sensíveis dos logs.
- Medir requisições, latência, cache hit, retries, jobs, custo, quota e falhas.
- Desabilitar feature flags em caso de incidente sem apagar histórico.
- Revogar credencial comprometida e reprocessar somente após correção.

## 12. Critérios de aceite do épico

- [ ] Integração SICAR formalmente autorizada ou fluxo assistido documentado.
- [ ] Um CAR válido consultado em homologação.
- [ ] Resultado vinculado ao imóvel/unidade corretos.
- [ ] Dados externos somente leitura e com origem/data visíveis.
- [ ] Earth Engine autenticado sem segredo no código.
- [ ] Sentinel-2 processado em polígono de teste.
- [ ] Resultado NDVI/RGB auditável e reprocessável.
- [ ] RLS, timeout, retry, logs e métricas validados.
- [ ] Runbook de produção e rollback aprovados.

## 13. Backlog rastreável

- **SICAR-01:** autorização e contrato por UF.
- **SICAR-02:** cliente e normalização.
- **SICAR-03:** auditoria e sincronização.
- **SICAR-04:** fluxo manual assistido.
- **GEE-01:** projeto Cloud e registro Earth Engine.
- **GEE-02:** autenticação de produção.
- **GEE-03:** cliente Sentinel-2.
- **GEE-04:** jobs NDVI/RGB.
- **GEE-05:** camadas e histórico MapLibre.
- **QA-01:** fixtures reais autorizadas.
- **QA-02:** testes de contrato/integração.
- **OPS-01:** custos, quotas, métricas e runbook.

## 14. Fontes

- [SFB — Regularização Ambiental](https://www.gov.br/florestal/pt-br/assuntos/regularizacao-ambiental)
- [Portal SICAR](https://www.car.gov.br/)
- [Consulta Pública SICAR](https://consultapublica.car.gov.br/publico/)
- [Earth Engine — Access](https://developers.google.com/earth-engine/guides/access)
- [Earth Engine — Authentication](https://developers.google.com/earth-engine/guides/auth)
- [Earth Engine — Service Accounts](https://developers.google.com/earth-engine/guides/service_account)
- [Earth Engine — REST API](https://developers.google.com/earth-engine/reference/rest)
- [Sentinel-2 SR Harmonized](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED)
