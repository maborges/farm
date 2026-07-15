# ERP-LIFECYCLE-02A — Correção do Bootstrap Tardio e do Contrato Semântico das Superfícies ERP

## 1. Resumo

- A fase corrigiu o bootstrap tardio do runtime ERP genérico para tenants autenticados sem integração materializada.
- `GET /api/v1/integracoes/erp/status`, `health`, `jobs`, `timeline` e `diagnostico` deixaram de retornar `404` no estado vazio.
- O contrato novo representa “tenant válido, autorizado, sem ERP configurado” como `HTTP 200` com estado semântico explícito de não configuração.
- `GET /api/v1/integracoes/sankhya/config -> 404` foi preservado.
- O primeiro save tardio continua criando `SankhyaConfig` e `TenantIntegracao` sem Wizard e sem implantação.
- O fallback legado via `SankhyaConfig` foi preservado, sem materialização automática em chamadas GET.

## 2. Contrato anterior

### Status

- `_resolve_active_erp_provider_slug(...)` lançava `HTTPException(404, "ERP não configurado")` quando não existia:
  - `TenantIntegracao` canônica;
  - nem fallback legado via `SankhyaConfig`.

### Health, jobs, timeline e diagnóstico

- Todas as superfícies dependiam do mesmo resolver.
- O tenant vazio recebia `404`, embora o schema e o fluxo de configuração inicial fossem válidos.

## 3. Contrato novo

### Estado vazio comum

- Resolver interno passou a retornar resolução semântica em vez de tratar bootstrap tardio como erro.
- Tenant autenticado sem ERP materializado agora recebe `HTTP 200` nas superfícies ERP genéricas.
- Nenhum provider é assumido por default.

### Status

Resposta vazia representativa:

```json
{
  "configurado": false,
  "ativo": false,
  "status_conexao": "NOT_CONFIGURED",
  "status_origem": "UNCONFIGURED",
  "health_origem": "UNCONFIGURED",
  "health_status": "NOT_CONFIGURED",
  "provider_definition": null,
  "features_habilitadas": [],
  "policies_resumidas": [],
  "readiness": {
    "status": "NOT_CONFIGURED",
    "label": "Não configurado",
    "variant": "secondary",
    "provider_code": null
  }
}
```

### Health

Resposta vazia representativa:

```json
{
  "configurado": false,
  "origem": "UNCONFIGURED",
  "status": "NOT_CONFIGURED",
  "summary": "Integração ainda não configurada."
}
```

### Jobs

Resposta vazia:

```json
[]
```

### Timeline

Resposta vazia:

```json
[]
```

### Diagnóstico

Resposta vazia representativa:

```json
{
  "origem": "UNCONFIGURED",
  "health_atual": "NOT_CONFIGURED",
  "status_degradacao": "NONE",
  "jobs_pendentes": 0,
  "jobs_falhos": 0,
  "recomendacao_operacional": "Selecione um provider no Console ERP e salve a configuração inicial para liberar a operação."
}
```

## 4. Status

- `GET /integracoes/erp/status` sem integração agora retorna `200`.
- O payload deixa claro que não há ERP configurado.
- O frontend passou a decidir bootstrap por conteúdo:
  - `configurado === false`
  - e ausência de provider resolvido
- Compatibilidade defensiva com o `404` antigo foi mantida temporariamente.

## 5. Health

- `GET /integracoes/erp/health` sem integração agora retorna `200`.
- Não cria snapshot, não persiste health e não simula “saudável”.
- O status é `NOT_CONFIGURED`.

## 6. Jobs

- `GET /integracoes/erp/jobs` sem integração retorna `[]`.
- Nenhum job é criado.

## 7. Timeline

- `GET /integracoes/erp/timeline` sem integração retorna `[]`.
- Nenhum evento artificial é gerado.

## 8. Diagnóstico

- `GET /integracoes/erp/diagnostico` sem integração retorna `200` com estado vazio.
- O diagnóstico não tenta delegar ao provider nesse caso.
- O erro legado observado na auditoria:
  - `can't compare offset-naive and offset-aware datetimes`
  continua fora do escopo desta fase e não foi alterado.

## 9. Resolver

- `services/api/integracoes/erp/router.py` ganhou resolução semântica de contexto:
  - canônico configurado;
  - fallback legado Sankhya;
  - runtime vazio;
  - runtime inconsistente continua erro.
- O fluxo normal de ausência deixou de usar `raise HTTPException(404, "ERP não configurado")`.

## 10. Estado vazio

- O estado vazio não significa:
  - provider inexistente;
  - provider inativo;
  - erro de permissão;
  - erro de banco;
  - provider não suportado.
- Esses casos continuam sendo tratados como erro real.

## 11. Fallback legado

- O fallback via `SankhyaConfig` sem `TenantIntegracao` foi preservado.
- Em `status`, quando o fallback legado é usado, o router injeta `readiness.provider_code = "sankhya"` se ausente.
- Isso permite ao frontend abrir o wrapper legado sem materializar nada em GET.
- A convergência definitiva fica para `ERP-LIFECYCLE-02B`.

## 12. Ausência de efeitos colaterais

Cobertura criada para provar que GETs não criam:

- `TenantIntegracao`
- `SankhyaConfig`
- credenciais
- features
- policies
- health
- jobs

No tenant vazio auditado em teste, as contagens antes e depois dos GETs permaneceram:

```text
SankhyaConfig = 0
TenantIntegracao = 0
```

## 13. Primeiro save

Fluxo validado em teste com banco em memória:

1. `GET /erp/status` -> `200 NOT_CONFIGURED`
2. `GET /erp/providers/sankhya/schema` -> `200`
3. `GET /sankhya/config` -> `404`
4. `POST /sankhya/config` -> `201`
5. uma `SankhyaConfig` criada
6. uma `TenantIntegracao` criada
7. `GET /erp/status` -> `200 configurado`
8. `GET /erp/health` -> estado coerente

Sem Wizard e sem implantação.

## 14. Tenant legado

Fluxo validado:

- `SankhyaConfig` existente
- `TenantIntegracao` ausente

Resultado:

- `status` continua `200`
- `health`, `jobs` e `timeline` continuam respondendo
- nenhum registro canônico é criado em GET

## 15. Drift inverso

Fluxo validado:

- `TenantIntegracao` existente
- `SankhyaConfig` ausente

Resultado:

- `status` resolve o provider canônico
- `GET /sankhya/config` continua `404`
- o tenant não cai em estado “sem provider”
- nenhuma segunda integração é criada

## 16. Integração inativa

Fluxo validado com `lifecycle_state = SUSPENDED`:

- `status` continua `200`
- integração não é confundida com “nunca configurada”
- `lifecycle_state` continua exposto

## 17. Soft delete

Fluxo validado:

- `TenantIntegracao.deleted_at` preenchido
- `SankhyaConfig` ausente

Resultado:

- `status` volta para estado vazio `200 NOT_CONFIGURED`
- a linha removida não é reutilizada em GET
- nada é materializado automaticamente

## 18. Backend

### Arquivos alterados nesta fase

- `services/api/integracoes/erp/router.py`
- `services/api/tests/unit/integracoes/test_erp_router.py`
- `services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py`

### Models e migrations

- Nenhum model alterado.
- Nenhuma migration criada.

## 19. Frontend

### Arquivos alterados nesta fase

- `apps/web/src/components/integracoes/erp-console.tsx`
- `apps/web/src/components/integracoes/erp/sync-center-view-model.ts`
- `apps/web/src/components/integracoes/erp-console.test.ts`
- `apps/web/src/components/integracoes/erp/sync-center-view-model.test.ts`
- `apps/web/tests/e2e/erp-console-configuracao.spec.ts`

### Ajustes realizados

- `ErpConsole` passou a reconhecer bootstrap também por `200` semântico.
- O seletor não abre em `401/403/500`.
- O `Sync Center` não habilita ações manuais quando `configurado=false`.

## 20. Schemas

- Foram reutilizados os schemas existentes sempre que possível.
- Não houve remoção de campos.
- O estado vazio usa os próprios envelopes atuais com valores explícitos.

## 21. Arquivos alterados x preexistentes

### Alterados nesta fase

- Backend:
  - `services/api/integracoes/erp/router.py`
  - `services/api/tests/unit/integracoes/test_erp_router.py`
  - `services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py`
- Frontend:
  - `src/components/integracoes/erp-console.tsx`
  - `src/components/integracoes/erp/sync-center-view-model.ts`
  - `src/components/integracoes/erp-console.test.ts`
  - `src/components/integracoes/erp/sync-center-view-model.test.ts`
  - `tests/e2e/erp-console-configuracao.spec.ts`

### Mudanças preexistentes em `apps/web` não atribuídas a esta fase

- `next-env.d.ts`
- `playwright.unit.config.ts`
- `src/components/integracoes/erp/provider-config-payload.test.ts`
- `src/components/integracoes/erp/provider-config-payload.ts`
- `src/components/integracoes/erp/types.ts`
- arquivos novos já presentes do subprojeto:
  - `src/components/integracoes/erp/configuration-section.tsx`
  - `src/components/integracoes/erp/configuration-section.test.ts`
  - `src/components/integracoes/erp/provider-config-fields.ts`
  - `src/components/integracoes/erp/provider-config-fields.test.ts`
  - `src/components/integracoes/erp/provider-console-endpoints.ts`
  - `src/components/integracoes/erp/provider-console-endpoints.test.ts`

## 22. Testes backend

Executado:

```bash
services/api/.venv/bin/pytest -q \
  services/api/tests/unit/integracoes/test_erp_router.py \
  services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py \
  services/api/tests/unit/integracoes/test_sankhya_governed_integration.py \
  services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py
```

Resultado:

```text
63 passed
```

## 23. Testes frontend

Executado com config dedicada para os testes puros em `src/components/integracoes`:

```text
38 passed
```

Cobertura adicionada:

- `status 200 configured=false` abre bootstrap
- compatibilidade com `404`
- provider legado resolvido
- provider configurado
- desabilitação de ações manuais no `Sync Center`

## 24. E2E

Executado:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3003 \
pnpm exec playwright test tests/e2e/erp-console-configuracao.spec.ts --project=chromium
```

Resultado:

```text
9 passed
```

Observação:

- a execução sandboxed do Chromium falhou por restrição do host Linux;
- a spec foi rerodada fora do sandbox e passou integralmente.

## 25. Typecheck

Executado:

```bash
cd apps/web && pnpm run typecheck
```

Resultado:

```text
passou
```

## 26. Lint

Executado:

```bash
cd apps/web && pnpm run lint
```

Resultado:

```text
passou
```

## 27. Build

Executado:

```bash
cd apps/web && pnpm run build
```

Resultado:

```text
passou
```

## 28. Ruff

Executado conforme solicitado:

```bash
cd services/api
ruff check integracoes/erp integracoes/erp_readiness_service.py tests/unit/integracoes
```

Resultado:

- falhou por dívida preexistente em múltiplos arquivos históricos fora do escopo desta fase;
- não foi introduzida nova falha de `ruff` nos arquivos alterados nesta fase.

Executado adicionalmente no escopo alterado:

```bash
ruff check \
  integracoes/erp/router.py \
  tests/unit/integracoes/test_erp_router.py \
  tests/unit/integracoes/test_erp_bootstrap_tardio.py
```

Resultado:

```text
passou
```

## 29. Diff

Executado:

```bash
git diff --check
git -C apps/web diff --check
```

Resultado:

```text
passou
```

## 30. Riscos

- O `ruff` amplo solicitado continua impedindo fechamento “100% limpo” do escopo backend por problemas históricos fora desta fase.
- O diagnóstico legado com erro de timezone permanece aberto e deve ser tratado separadamente se priorizado.

## 31. Limitações

- Esta fase não removeu o fallback legado Sankhya.
- Esta fase não reconciliou automaticamente `SankhyaConfig` legado com `TenantIntegracao`.
- Esta fase não introduziu contrato multiprovider completo.

## 32. Impacto no piloto

- O bootstrap tardio deixou de depender de `404` semântico incorreto.
- O console agora tolera tenant vazio de forma explícita.
- O primeiro save tardio permanece funcional.
- O risco do piloto cai de “bootstrap quebrado” para “bootstrap funcional com fallback legado ainda temporário”.

## 33. Veredicto

- Funcionalmente: `GO`
- Formalmente na validação ampla: `GO COM RESSALVAS`

### Justificativa

- Todos os critérios funcionais da fase foram atendidos.
- Backend, frontend e E2E segmentado passaram.
- O único ponto pendente de validação ampla é o `ruff` no escopo histórico solicitado, por dívida anterior não introduzida nesta fase.

## 34. Recomendação para `ERP-LIFECYCLE-02B`

- Prosseguir com `ERP-LIFECYCLE-02B` para compatibilidade legada e convergência canônica:
  - reconhecer `SankhyaConfig` legado sem `TenantIntegracao`;
  - materializar canônico de forma idempotente quando apropriado;
  - reduzir dependência do fallback específico no router ERP.
