# ERP-FACADE-04C - Timeline, Diagnostico e Associacoes na Superficie HTTP ERP

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: expansao da borda HTTP ERP para `timeline`, `diagnostico` e governanca de associacoes externas, com migracao da UI quando o payload ja era compativel

## Resumo executivo

Esta execucao concluiu a Fase B.1 para os conceitos comuns restantes autorizados pelo contrato ERP:

- `GET /api/v1/integracoes/erp/timeline`
- `GET /api/v1/integracoes/erp/diagnostico`
- `GET /api/v1/integracoes/erp/associacoes/pendentes`
- `POST /api/v1/integracoes/erp/associacoes/{id}/reconciliar`

O router ERP permaneceu como camada fina de composicao. Nao houve criacao de runtime, services, schemas, models ou persistencia novos. A implementacao apenas resolve o provider ativo e delega para a infraestrutura oficial ja existente do provider atual.

Na UI, `ErpConsole` e o backoffice ERP migraram de Sankhya para a borda ERP em `timeline` e `diagnostico`. A governanca de associacoes do `ErpConsole` tambem migrou para `/integracoes/erp/associacoes/*`. `logs` permaneceu em `/integracoes/sankhya/logs`, conforme deliberado no escopo.

## Auditorias executadas

### 1. Auditoria de reutilizacao

Endpoints Sankhya equivalentes analisados:

- [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
  - `/timeline`
  - `/diagnostico`
  - `/associacoes/pendentes`
  - `/associacoes/{association_id}/reconciliar`

Services e contratos reutilizaveis confirmados:

- `SankhyaSyncService`
- `ExternalRecordAssociationService`
- `ExternalRecordAssociationGovernanceReconcileRequest`
- `ExternalRecordAssociationPendingItemResponse`
- `SankhyaTimelineItemResponse`
- `SankhyaOperationalDiagnosisResponse`
- `ErpReadinessService`

Conclusao:

- `timeline` e `diagnostico` ja estavam consolidados em `SankhyaSyncService`;
- a governanca de associacoes ja estava consolidada no fluxo Sankhya sobre `ExternalRecordAssociationService`;
- a menor implementacao coerente era delegar diretamente do router ERP para os handlers/servicos existentes.

### 2. Auditoria arquitetural

Documento confirmado:

- [docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md)

Confirmacoes:

- a superficie ERP expande apenas conceitos comuns de leitura e governanca;
- `logs` nao foi canonizado nem migrado;
- nao houve exposicao de autenticação, gateway, sync tecnico, fiscal, financeiro ou NFe pela borda ERP;
- nao houve logica paralela de diagnostico nem de reconciliacao.

### 3. Auditoria de compatibilidade

Rotas Sankhya preservadas:

- `/api/v1/integracoes/sankhya/timeline`
- `/api/v1/integracoes/sankhya/diagnostico`
- `/api/v1/integracoes/sankhya/associacoes/pendentes`
- `/api/v1/integracoes/sankhya/associacoes/{id}/reconciliar`
- `/api/v1/integracoes/sankhya/logs`

Nenhuma rota Sankhya foi removida, alterada ou depreciada.

### 4. Auditoria de impacto na UI

Consumidores encontrados antes da migracao:

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
  - `/integracoes/sankhya/timeline`
  - `/integracoes/sankhya/diagnostico`
  - `/integracoes/sankhya/associacoes/pendentes`
  - `/integracoes/sankhya/associacoes/{id}/reconciliar`

- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)
  - `/integracoes/sankhya/timeline`
  - `/integracoes/sankhya/diagnostico`

Conclusao:

- os payloads eram compativeis para migracao direta;
- nao foi necessario adaptar contratos internos da UI;
- `logs` permaneceu em Sankhya por decisao arquitetural e nao por incompatibilidade tecnica.

## Arquivos alterados

- [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)
- [services/api/tests/unit/integracoes/test_erp_router.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_router.py)
- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

## Endpoints criados

- `GET /api/v1/integracoes/erp/timeline`
- `GET /api/v1/integracoes/erp/diagnostico`
- `GET /api/v1/integracoes/erp/associacoes/pendentes`
- `POST /api/v1/integracoes/erp/associacoes/{id}/reconciliar`

## Endpoints preservados

- `GET /api/v1/integracoes/sankhya/timeline`
- `GET /api/v1/integracoes/sankhya/diagnostico`
- `GET /api/v1/integracoes/sankhya/associacoes/pendentes`
- `POST /api/v1/integracoes/sankhya/associacoes/{id}/reconciliar`
- `GET /api/v1/integracoes/sankhya/logs`

## Servicos reutilizados

### Resolucao de provider

- `ErpReadinessService.carregar_runtime`

Uso:

- identifica o provider ERP ativo;
- evita duplicar runtime ou regra de resolucao no router ERP.

### Timeline e diagnostico

- `SankhyaSyncService`

Uso:

- `timeline` e `diagnostico` permanecem montados pelo provider atual;
- a borda ERP apenas delega, preservando o contrato de resposta existente.

### Governanca de associacoes

- `ExternalRecordAssociationService`

Uso:

- a listagem de pendencias e a reconciliacao continuam centralizadas no service oficial;
- a borda ERP apenas encaminha os parametros e devolve a resposta.

## Evidencias de delegacao

Em [router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py):

- a verificacao do provider ativo foi centralizada em `_assert_sankhya_provider`;
- `timeline` delega para `listar_timeline_sankhya_provider`;
- `diagnostico` delega para `obter_diagnostico_sankhya_provider`;
- `associacoes/pendentes` delega para `listar_associacoes_externas_pendentes_sankhya`;
- `associacoes/{id}/reconciliar` delega para `reconciliar_associacao_externa_sankhya`.

Conclusao:

- nao ha query nova no router ERP;
- nao ha logica nova de diagnostico;
- nao ha duplicacao de governanca de associacoes;
- nao ha manipulacao direta de banco na nova borda ERP.

## Consumidores migrados

### `ErpConsole`

Migrado em [sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx):

- `/integracoes/sankhya/diagnostico` -> `/integracoes/erp/diagnostico`
- `/integracoes/sankhya/timeline?limit=12` -> `/integracoes/erp/timeline?limit=12`
- `/integracoes/sankhya/associacoes/pendentes` -> `/integracoes/erp/associacoes/pendentes`
- `/integracoes/sankhya/associacoes/{id}/reconciliar` -> `/integracoes/erp/associacoes/{id}/reconciliar`

### Backoffice ERP

Migrado em [page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx):

- `/integracoes/sankhya/timeline?limit=20` -> `/integracoes/erp/timeline?limit=20`
- `/integracoes/sankhya/diagnostico` -> `/integracoes/erp/diagnostico`

## Consumidores mantidos

Mantidos por compatibilidade:

- `ErpConsole`: `/integracoes/sankhya/logs?limit=10`
- Backoffice ERP: `/integracoes/sankhya/logs?limit=5`

Motivo:

- `logs` continuam com natureza parcialmente legada/provider-specific e permaneceram fora do contrato ERP nesta etapa.

## Divergencias encontradas

Nao foi identificada divergencia de payload nos consumidores migrados.

Observacoes:

- os tipos locais da UI ainda carregam nomes historicos como `SankhyaDiagnosis` e `SankhyaStatus`;
- isso nao afeta a borda HTTP consumida e foi mantido para evitar refatoracao cosmetica fora do escopo.

## Riscos remanescentes

### 1. `logs` ainda seguem provider-first

Risco:

- a UI ainda depende de `/integracoes/sankhya/logs`.

Impacto:

- conhecido e deliberado; nao bloqueia a consolidacao dos conceitos ERP-generic previstos para esta fase.

### 2. O provider ativo continua sendo apenas Sankhya nesta superficie

Risco:

- a borda ERP continua retornando `501` para providers futuros ainda nao suportados.

Impacto:

- aderente ao contrato atual e ao plano incremental.

### 3. Nomenclatura historica ainda existe em implementacoes internas

Risco:

- alguns nomes de componentes e tipos ainda mencionam Sankhya internamente.

Impacto:

- baixo; o acoplamento de transporte HTTP para os conceitos comuns foi removido.

## Validacoes executadas

### Backend

Executado com sucesso:

```bash
cd services/api
.venv/bin/ruff check integracoes/erp tests/unit/integracoes/test_erp_router.py
.venv/bin/mypy --explicit-package-bases --follow-imports=silent integracoes/erp tests/unit/integracoes/test_erp_router.py
.venv/bin/pytest tests/unit/integracoes/test_erp_router.py -q
```

Resultados:

- `ruff`: OK
- `mypy`: OK
- `pytest`: `11 passed`

### Frontend

Executado com sucesso:

```bash
cd apps/web
npm run typecheck
```

Resultado:

- `typecheck`: OK

### Validacao de consumidores

Busca executada:

```bash
rg -n '"/integracoes/sankhya/(timeline|diagnostico|associacoes/pendentes)|/integracoes/sankhya/associacoes/.*/reconciliar|"/integracoes/sankhya/logs|"/integracoes/erp/(timeline|diagnostico|associacoes/pendentes)|/integracoes/erp/associacoes/.*/reconciliar' apps/web/src
```

Resultado:

- `timeline`, `diagnostico` e `associacoes` aparecem apenas na borda ERP;
- `logs` continuam em Sankhya, como planejado.

### Validacao final de diff

Executado com sucesso:

```bash
git diff --check
```

## Proximo passo recomendado

ERP-FACADE-04D:

- avaliar se `logs` devem receber uma superficie ERP propria ou permanecer explicitamente provider-specific;
- revisar a nomenclatura interna remanescente (`Sankhya*`) onde ela ja nao representa acoplamento funcional, apenas legado nominal;
- preparar a borda ERP para futuros providers sem alterar a UI consumidora dos conceitos comuns.
