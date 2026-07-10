# ERP-FACADE-04A - Router ERP Canonico (Fase B.1, Etapa 1)

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: implementacao da borda HTTP ERP para `status`, `health` e `jobs`

## Resumo executivo

Esta execucao implementou a infraestrutura inicial da Superficie HTTP ERP sem alterar consumidores, sem remover rotas Sankhya e sem introduzir runtime, services, models ou persistencia novos.

Foram criados:

- `GET /api/v1/integracoes/erp/status`
- `GET /api/v1/integracoes/erp/health`
- `GET /api/v1/integracoes/erp/jobs`

Esses endpoints funcionam como camada fina de composicao:

- resolvem o provider ERP ativo com o runtime oficial;
- delegam integralmente para `SankhyaSyncService` no provider atual;
- preservam fallback de compatibilidade para configuracao legada Sankhya quando ainda nao houver runtime canonico materializado.

## Auditorias executadas

### 1. Auditoria de reutilizacao

Itens revisados antes da implementacao:

- router Sankhya em [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- service Sankhya em [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- runtime oficial em [services/api/integracoes/erp_readiness_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp_readiness_service.py)
- contrato aprovado em [docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md)
- padrao de router por provider em [services/api/integracoes/openweather/routers.py](/opt/lampp/htdocs/farm/services/api/integracoes/openweather/routers.py)

Conclusao:

- todos os componentes necessarios ja existiam;
- nao houve necessidade de criar service, schema, DTO ou query nova;
- o menor incremento coerente era um router ERP que apenas resolve provider e delega.

### 2. Auditoria arquitetural

Confirmacoes de aderencia ao contrato:

- a camada ERP foi implementada apenas como transporte HTTP;
- nao ha regra de negocio nova;
- nao ha recalculo de readiness, health ou jobs;
- nao ha acesso direto ao banco no router;
- nao ha persistencia propria;
- nao ha alteracao de UI, Wizard, runtime ou adapters.

### 3. Auditoria do runtime

Reutilizacao confirmada de:

- `ErpReadinessService`
- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`

Observacao:

- o router nao toca diretamente nessas estruturas;
- ele reaproveita o runtime oficial por meio de `ErpReadinessService.carregar_runtime` e dos services existentes.

### 4. Auditoria de compatibilidade

Confirmacoes:

- `/api/v1/integracoes/sankhya/status` permanece inalterado;
- `/api/v1/integracoes/sankhya/health` permanece inalterado;
- `/api/v1/integracoes/sankhya/jobs` permanece inalterado;
- nenhuma rota Sankhya foi removida ou depreciada.

## Arquivos alterados

- [services/api/integracoes/erp/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/__init__.py)
- [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)
- [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py)
- [services/api/tests/unit/integracoes/test_erp_router.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_router.py)

## Componentes reutilizados

- `ErpReadinessService`
- `SankhyaSyncService`
- `get_session`
- `get_tenant_id`
- `require_tenant_permission`
- runtime canonico carregado por `ErpReadinessService.carregar_runtime`

## Endpoints criados

- `GET /api/v1/integracoes/erp/status`
- `GET /api/v1/integracoes/erp/health`
- `GET /api/v1/integracoes/erp/jobs`

## Endpoints preservados

- `GET /api/v1/integracoes/sankhya/status`
- `GET /api/v1/integracoes/sankhya/health`
- `GET /api/v1/integracoes/sankhya/jobs`

## Servicos reutilizados

### Runtime oficial

- `ErpReadinessService.carregar_runtime`

Uso:

- resolve o provider ERP ativo sem query no router;
- evita duplicacao de regra de resolucao do runtime.

### Provider atual

- `SankhyaSyncService.get_config`
- `SankhyaSyncService.obter_status_detalhado`
- `SankhyaSyncService.obter_health_detalhado`
- `SankhyaSyncService.listar_jobs`

Uso:

- fallback de compatibilidade legada;
- delegacao de `status`, `health` e `jobs` sem reimplementacao.

## Evidencias de delegacao

Fonte principal: [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)

Evidencias:

- o router monta apenas um probe minimo para `ErpReadinessService`;
- a resolucao do provider ocorre por `carregar_runtime`;
- quando o provider ativo e `sankhya`, a resposta sai diretamente de `SankhyaSyncService`;
- o router nao monta payload proprio de `status`, `health` ou `jobs`;
- o fallback legado usa `SankhyaSyncService.get_config`, nao query propria.

## Evidencias de ausencia de duplicacao

- nenhum novo service foi criado;
- nenhum novo schema foi criado;
- nenhum DTO paralelo foi criado;
- nenhuma query de banco foi adicionada ao router;
- nenhuma regra de readiness foi copiada;
- nenhuma regra de health foi copiada;
- nenhuma regra de jobs foi copiada.

## Riscos encontrados

### 1. Surface generic ainda delega apenas para Sankhya

Risco:

- nesta etapa, apenas o provider ERP atual esta materialmente conectado a nova borda.

Mitigacao:

- isso esta aderente ao escopo da etapa;
- o resolvedor ja devolve `501` para providers ERP ainda nao suportados pela superficie.

### 2. Fallback legado ainda existe

Risco:

- tenants sem runtime ERP canonico, mas com configuracao Sankhya legada, continuam dependendo da superficie antiga internamente.

Mitigacao:

- o fallback foi mantido por compatibilidade deliberada;
- ele evita regressao durante a transicao.

### 3. `main.py` possui ruido historico de lint

Risco:

- validacao ampla de `ruff` em `main.py` gera varias falhas preexistentes e nao relacionadas a esta execucao.

Mitigacao:

- a validacao de lint foi executada com foco nos arquivos novos da area ERP;
- a alteracao em `main.py` foi limitada a um import e um `include_router`.

## Proximos passos recomendados (ERP-FACADE-04B)

- migrar `ErpConsole` para consumir `/api/v1/integracoes/erp/status`;
- migrar `ErpConsole` para consumir `/api/v1/integracoes/erp/health`;
- migrar `ErpConsole` e backoffice para consumir `/api/v1/integracoes/erp/jobs`;
- manter `/api/v1/integracoes/sankhya/*` como fallback durante a transicao;
- iniciar `timeline` e `diagnostico` apenas na etapa seguinte, ainda como composicao.

## Validacoes executadas

### Lint

Executado com sucesso:

```bash
cd services/api && .venv/bin/ruff check integracoes/erp tests/unit/integracoes/test_erp_router.py
```

Observacao:

- houve tentativa inicial de incluir `main.py` no `ruff`, mas o arquivo possui volume relevante de violacoes historicas preexistentes e nao relacionadas a esta mudanca.

### Typecheck

Executado com sucesso:

```bash
cd services/api && .venv/bin/mypy --explicit-package-bases --follow-imports=silent integracoes/erp tests/unit/integracoes/test_erp_router.py
```

### Testes automatizados

Executado com sucesso:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_erp_router.py -q
```

Resultado:

- `7 passed`

### Validacao final de diff

```bash
git diff --check
```
