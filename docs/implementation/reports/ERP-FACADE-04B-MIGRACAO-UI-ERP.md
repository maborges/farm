# ERP-FACADE-04B - Migracao da UI para a Superficie HTTP ERP

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: migracao dos consumidores HTTP de `status`, `health` e `jobs` da UI ERP para `/api/v1/integracoes/erp/*`

## Resumo executivo

Esta execucao concluiu a migracao da UI ERP para a nova borda HTTP canonica apenas nos conceitos comuns de leitura:

- `GET /api/v1/integracoes/erp/status`
- `GET /api/v1/integracoes/erp/health`
- `GET /api/v1/integracoes/erp/jobs`

A mudanca ficou restrita ao transporte HTTP consumido por `ErpConsole` e pela tela de backoffice ERP. Nao houve alteracao de layout, comportamento funcional, backend, runtime, adapters, contracts ou payloads.

As leituras provider-specific permaneceram em `/api/v1/integracoes/sankhya/*` por compatibilidade, especialmente `timeline`, `diagnostico`, `logs` e demais operacoes fora do escopo da etapa.

## Auditorias executadas

### 1. Auditoria de reutilizacao

Consumidores revisados antes da alteracao:

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

Busca executada:

```bash
rg -n '"/integracoes/sankhya/(status|health|jobs)|/integracoes/sankhya/(status|health|jobs)' apps/web/src
```

Conclusao:

- havia apenas dois consumidores diretos para `status`, `health` e `jobs`;
- ambos podiam migrar sem alterar contratos internos;
- nao havia hooks, React Query ou clients adicionais para esses tres conceitos.

### 2. Auditoria arquitetural

Documentos confirmados como referencia:

- [docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md)
- [docs/implementation/reports/ERP-FACADE-04A-ROUTER-ERP.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-04A-ROUTER-ERP.md)

Confirmacoes:

- nenhuma tela voltou a consumir conceitos comuns via Sankhya;
- a UI continua sem conhecer implementacao de runtime;
- a mudanca foi apenas de origem HTTP.

### 3. Auditoria de compatibilidade

Confirmacoes:

- `/api/v1/integracoes/sankhya/status` permanece publicado;
- `/api/v1/integracoes/sankhya/health` permanece publicado;
- `/api/v1/integracoes/sankhya/jobs` permanece publicado;
- nenhuma rota Sankhya foi removida, depreciada ou alterada.

### 4. Auditoria de impacto

Componentes avaliados:

- `ErpConsole` via [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- Backoffice ERP via [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)
- `ErpTimeline` como dependencia visual reaproveitada, sem alteracao de transporte proprio

Conclusao:

- o impacto ficou restrito a chamadas `fetch` e `apiFetchServer`;
- nao houve alteracao de props, estado ou renderizacao.

## Arquivos alterados

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

## Arquivos apenas analisados

- [docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md)
- [docs/implementation/reports/ERP-FACADE-04A-ROUTER-ERP.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-04A-ROUTER-ERP.md)
- [services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py)
- [services/api/tests/unit/integracoes/test_sankhya_governed_integration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_governed_integration.py)

## Consumidores encontrados

### Migrados

- `ErpConsole`
  - `status`: `/integracoes/sankhya/status` -> `/integracoes/erp/status`
  - `health`: `/integracoes/sankhya/health` -> `/integracoes/erp/health`
  - `jobs`: `/integracoes/sankhya/jobs?limit=5` -> `/integracoes/erp/jobs?limit=5`

- Backoffice ERP
  - `status`: `/integracoes/sankhya/status` -> `/integracoes/erp/status`
  - `health`: `/integracoes/sankhya/health` -> `/integracoes/erp/health`
  - `jobs`: `/integracoes/sankhya/jobs?limit=5` -> `/integracoes/erp/jobs?limit=5`

### Preservados por compatibilidade

- `ErpConsole`
  - `/integracoes/sankhya/diagnostico`
  - `/integracoes/sankhya/logs?limit=10`
  - `/integracoes/sankhya/timeline?limit=12`
  - endpoints de configuracao e acoes provider-specific

- Backoffice ERP
  - `/integracoes/sankhya/logs?limit=5`
  - `/integracoes/sankhya/timeline?limit=20`
  - `/integracoes/sankhya/diagnostico`

## Evidencias de compatibilidade

Busca final em `apps/web/src`:

```bash
rg -n '"/integracoes/sankhya/(status|health|jobs)"|"\/integracoes\/erp\/(status|health|jobs)' apps/web/src
```

Resultado:

- restaram apenas chamadas para `/integracoes/erp/status`, `/integracoes/erp/health` e `/integracoes/erp/jobs`;
- nao restaram consumidores diretos de Sankhya para esses tres conceitos;
- leituras provider-specific continuam apontando para Sankhya, conforme escopo aprovado.

## Divergencias encontradas

Nao foi identificada divergencia funcional de payload nos consumidores migrados.

Observacao:

- os tipos locais ainda usam nomes historicos como `SankhyaStatus`, `SankhyaHealth` e `SankhyaJob` em `sankhya-console.tsx`;
- nesta etapa isso foi mantido deliberadamente para evitar refatoracao estrutural fora do escopo.

## Evidencias tecnicas da migracao

### `ErpConsole`

Em [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx):

- `status` agora consome `/integracoes/erp/status`
- `health` agora consome `/integracoes/erp/health`
- `jobs` agora consome `/integracoes/erp/jobs?limit=5`

### Backoffice ERP

Em [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx):

- `status` agora consome `/integracoes/erp/status`
- `health` agora consome `/integracoes/erp/health`
- `jobs` agora consome `/integracoes/erp/jobs?limit=5`

## Riscos remanescentes

### 1. Nomenclatura historica ainda aparece em implementacoes internas

Risco:

- `sankhya-console.tsx` ainda concentra tipos e acoes com nomes herdados do provider atual.

Impacto:

- baixo nesta etapa, pois nao afeta o contrato HTTP nem a superficie visual ERP.

### 2. `timeline` e `diagnostico` continuam provider-first

Risco:

- ainda existe acoplamento HTTP parcial em leituras fora de `status`, `health` e `jobs`.

Impacto:

- esperado e aderente ao escopo da Fase 04B.

### 3. Suite ampla de integracao Sankhya possui falha nao relacionada

Risco:

- a validacao ampla em [services/api/tests/unit/integracoes/test_sankhya_governed_integration.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_governed_integration.py) falhou fora da area alterada.

Detalhe:

- falha em `test_criar_config_restaura_contexto_rls_antes_do_sync_canonico`
- expectativa: `_restore_rls_context` aguardado 1 vez
- resultado atual: aguardado 2 vezes

Impacto:

- nao bloqueia esta entrega de frontend, mas precisa ser tratado separadamente para manter a suite verde.

## Proximos passos recomendados (ERP-FACADE-04C)

- migrar `timeline` para superficie HTTP ERP quando a rota canonica existir;
- migrar `diagnostico` para superficie HTTP ERP sem recalculo na UI;
- avaliar `associacoes` e demais leituras comuns ainda expostas via Sankhya;
- reduzir a nomenclatura historica restante nos tipos internos da UI sem alterar comportamento.

## Validacoes executadas

### Typecheck frontend

Executado com sucesso:

```bash
cd apps/web
npm run typecheck
```

### Teste arquitetural relacionado aos arquivos alterados

Executado com sucesso:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py -q
```

Resultado:

- `13 passed`

### Busca de consumidores restantes

Executada:

```bash
rg -n '"/integracoes/sankhya/(status|health|jobs)"|"\/integracoes\/erp\/(status|health|jobs)' apps/web/src
```

Resultado:

- apenas consumidores ERP para `status`, `health` e `jobs`

### Suite adicional encontrada na area

Executada:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -q
```

Resultado:

- `1 failed, 17 passed`

Motivo:

- falha preexistente e nao relacionada a esta mudanca de transporte HTTP da UI

### Validacao final de diff

Executado com sucesso:

```bash
git diff --check
```
