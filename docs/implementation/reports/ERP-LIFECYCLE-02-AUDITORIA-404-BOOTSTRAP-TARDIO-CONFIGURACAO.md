# ERP-LIFECYCLE-02 — Auditoria do Bootstrap Tardio, Estados 404 e Configuração ERP Pós-Implantação

## 1. Resumo executivo

- Auditoria exclusivamente documental e investigativa, sem alterações de código, testes, modelos, migrations, endpoints, router, services, adapters, frontend ou banco.
- O `404` principal observado no cenário de bootstrap tardio vem de `GET /api/v1/integracoes/erp/status`.
- A semântica atual desse `404` é: ausência de `TenantIntegracao` canônica **e** ausência de fallback legacy via `SankhyaConfig`.
- `GET /api/v1/integracoes/sankhya/config` também retorna `404`, mas esse caso é semântico e esperado para “configuração ainda não criada”.
- O schema do provider Sankhya continua disponível sem implantação, sem Wizard e sem `TenantIntegracao`: `GET /api/v1/integracoes/erp/providers/sankhya/schema` respondeu `200`.
- O backend atual **não mostra dependência de implantação nem de Wizard** para carregar schema ou para o primeiro save de configuração.
- O primeiro save **deveria** funcionar sem Wizard e sem implantação, porque `POST /api/v1/integracoes/sankhya/config` cria `SankhyaConfig` e depois materializa `TenantIntegracao` via adapter canônico. Esse ponto foi confirmado por leitura de código e testes, não por execução, pois o POST grava dados e foi vedado nesta auditoria.
- Existe drift legado real no banco: `farms.sankhya_config` possui registros, enquanto `farms.tenant_integracoes` está vazio.
- Classificação:
  - Semântica do `404` de `/erp/status`: `INCORRETO`
  - Bootstrap tardio: `QUEBRADO`
  - Piloto: `GO COM RESSALVAS`

## 2. Escopo e guardrails

- Não foi alterado nenhum arquivo produtivo.
- Não foi criado endpoint.
- Não foi alterado router, service, adapter, model, migration ou teste.
- Não houve insert, update ou delete manual no banco.
- Apenas consultas SQL de leitura e chamadas HTTP de leitura/teste sem persistência foram executadas.
- `POST /api/v1/integracoes/sankhya/config` não foi executado por restrição explícita desta auditoria.

## 3. Ambiente e método

### 3.1 Ambiente

- Workspace: `/opt/lampp/htdocs/farm`
- Backend local acessível em `http://127.0.0.1:8000`
- Banco consultado: schema `farms`
- Data da auditoria: `2026-07-14`

### 3.2 Fontes de evidência

- Código backend:
  - `services/api/integracoes/erp/router.py`
  - `services/api/integracoes/erp_readiness_service.py`
  - `services/api/integracoes/sankhya/routers/__init__.py`
  - `services/api/integracoes/sankhya/services/sync_service.py`
  - `services/api/integracoes/sankhya/services/canonical_adapter.py`
- Frontend:
  - `apps/web/src/components/integracoes/erp-console.tsx`
  - `apps/web/src/components/integracoes/erp/configuration-section.tsx`
- Testes:
  - `services/api/tests/unit/integracoes/test_erp_router.py`
  - `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
  - `apps/web/tests/e2e/erp-console-configuracao.spec.ts`
- Banco:
  - `farms.marketplace_integracoes`
  - `farms.tenant_integracoes`
  - `farms.sankhya_config`
  - `farms.wizard_implantacoes_operacionais`

## 4. Tenants auditados

### 4.1 Tenant principal de bootstrap vazio

- Tenant: `Dry Run Fazenda`
- `tenant_id`: `94f5ca53-7b3e-49de-93af-d78a4488f30a`
- Estado observado:
  - sem `wizard_implantacoes_operacionais`
  - sem `tenant_integracoes`
  - sem `sankhya_config`

### 4.2 Tenant legado com config sem materialização canônica

- Tenant: `Grancafé`
- `tenant_id`: `7a034d03-bd2d-4de5-994a-405e282075ba`
- Estado observado:
  - sem `wizard_implantacoes_operacionais`
  - sem `tenant_integracoes`
  - com `sankhya_config`

## 5. Banco de dados

## 5.1 Marketplace

- Sankhya existe e está ativa em `farms.marketplace_integracoes`.
- Evidência observada:
  - `id = 2`
  - `slug = sankhya`
  - `provider_type = ERP`
  - `ativa = true`

## 5.2 Estruturas canônicas e legadas

- `SELECT COUNT(*) FROM farms.tenant_integracoes` => `0`
- `SELECT COUNT(*) FROM farms.sankhya_config` => `2`
- `SELECT COUNT(*) FROM farms.wizard_implantacoes_operacionais` => `0`

### Conclusão de banco

- O ambiente atual não contém nenhuma integração ERP canônica materializada.
- O ambiente atual contém configurações Sankhya legadas.
- Não existe evidência de implantação/Wizard ativa para os tenants auditados.
- Há drift legado real:
  - `LEGACY_DRIFT`
  - `TENANT_INTEGRATION_MISSING`

## 6. Erro reproduzido

## 6.1 Fluxo reproduzido

### Cenário principal reproduzido

`Tenant autenticado sem TenantIntegracao e sem SankhyaConfig`

1. Acesso ao Console ERP.
2. Chamada `GET /api/v1/integracoes/erp/status`.
3. Resposta `404 {"detail":"ERP não configurado"}`.
4. Chamada `GET /api/v1/integracoes/erp/providers/sankhya/schema`.
5. Resposta `200`.
6. Chamada `GET /api/v1/integracoes/sankhya/config`.
7. Resposta `404 {"detail":"Sankhya não configurado"}`.

### Ordem observada de requests auditadas

Para reproduzir e isolar a semântica, as requests foram executadas manualmente nesta ordem:

1. `GET /api/v1/integracoes/erp/status`
2. `GET /api/v1/integracoes/erp/providers/sankhya/schema`
3. `GET /api/v1/integracoes/sankhya/config`
4. `POST /api/v1/integracoes/sankhya/config/testar-conexao`
5. `GET /api/v1/integracoes/erp/health`
6. `GET /api/v1/integracoes/erp/jobs`
7. `GET /api/v1/integracoes/erp/diagnostico`
8. `GET /api/v1/integracoes/erp/timeline`

## 6.2 Endpoint que retorna 404

### Dry Run Fazenda

- `GET /api/v1/integracoes/erp/status` => `404 {"detail":"ERP não configurado"}`
- `GET /api/v1/integracoes/sankhya/config` => `404 {"detail":"Sankhya não configurado"}`
- `GET /api/v1/integracoes/erp/health` => `404 {"detail":"ERP não configurado"}`
- `GET /api/v1/integracoes/erp/jobs` => `404 {"detail":"ERP não configurado"}`
- `GET /api/v1/integracoes/erp/diagnostico` => `404 {"detail":"ERP não configurado"}`
- `GET /api/v1/integracoes/erp/timeline` => `404 {"detail":"ERP não configurado"}`

### Grancafé

- `GET /api/v1/integracoes/erp/status` => `200`
- `GET /api/v1/integracoes/sankhya/config` => `200`
- `GET /api/v1/integracoes/erp/health` => `200`
- `GET /api/v1/integracoes/erp/jobs` => `200`
- `GET /api/v1/integracoes/erp/timeline` => `200`
- `GET /api/v1/integracoes/erp/diagnostico` => `500`

## 6.3 Response bodies sanitizados

### Dry Run Fazenda

- `/erp/status`:
```json
{"detail":"ERP não configurado"}
```

- `/sankhya/config`:
```json
{"detail":"Sankhya não configurado"}
```

- `/sankhya/config/testar-conexao`:
```json
{
  "sucesso": false,
  "mensagem": "Configuração não encontrada",
  "token_obtido": false
}
```

### Grancafé

- `/erp/status`: `200` com payload de status configurado e origem canônica/health canônica.
- `/sankhya/config`: `200` com configuração mascarada.
- `/erp/diagnostico`: `500` com:
```json
{
  "detail": "Internal Server Error",
  "error": "can't compare offset-naive and offset-aware datetimes",
  "request_id": "unknown"
}
```

Observação: esse `500` não é o foco desta auditoria, mas foi encontrado incidentalmente.

## 7. Matriz obrigatória de endpoints

| Endpoint | Estado esperado sem ERP | Estado observado | Recurso procurado | Deve retornar 404? |
| --- | --- | --- | --- | ---: |
| `GET /api/v1/integracoes/erp/status` | Estado sem integração materializada, idealmente sem bloquear bootstrap | `404` no tenant vazio; `200` no tenant com `SankhyaConfig` legado | provider/config ERP ativa resolvida pelo router ERP | Não |
| `GET /api/v1/integracoes/erp/providers/sankhya/schema` | Schema disponível | `200` | `MarketplaceIntegracao` ativa do slug `sankhya` | Não |
| `GET /api/v1/integracoes/sankhya/config` | Config ainda não criada | `404` no tenant vazio; `200` no tenant legado | `SankhyaConfig` do tenant | Sim |
| `POST /api/v1/integracoes/sankhya/config` | Primeiro save cria config | Não executado por restrição de escrita | criação de `SankhyaConfig` e sync canônico | Não |
| `POST /api/v1/integracoes/sankhya/config/testar-conexao` | resposta operacional sem persistir | `200` em ambos os tenants | config Sankhya existente ou inexistente | Não |
| `GET /api/v1/integracoes/erp/health` | estado vazio ou não configurado sem quebrar console | `404` no tenant vazio; `200` no tenant legado | provider ERP ativo resolvido pelo router ERP | Não |
| `GET /api/v1/integracoes/erp/jobs` | lista vazia ou estado vazio | `404` no tenant vazio; `200` no tenant legado | provider ERP ativo resolvido pelo router ERP | Não |
| `GET /api/v1/integracoes/erp/diagnostico` | estado vazio ou diagnóstico vazio | `404` no tenant vazio; `500` no tenant legado | provider ERP ativo resolvido pelo router ERP | Não |
| `GET /api/v1/integracoes/erp/timeline` | lista vazia ou estado vazio | `404` no tenant vazio; `200` no tenant legado | provider ERP ativo resolvido pelo router ERP | Não |

## 8. Semântica formal dos 404

## 8.1 `/integracoes/erp/status`

### O que o código realmente implementa

Em `services/api/integracoes/erp/router.py`, `_resolve_active_erp_provider_slug`:

1. carrega runtime via `ErpReadinessService.carregar_runtime(...)`;
2. se houver `runtime.provider` e `runtime.config`, retorna o slug;
3. senão tenta fallback `sankhya_sync_service.get_config(tenant_id)`;
4. se existir `SankhyaConfig`, retorna `"sankhya"`;
5. caso contrário, lança `HTTPException(404, "ERP não configurado")`.

### Semântica atual real

- ausência de `TenantIntegracao` canônica **e**
- ausência de `SankhyaConfig` legacy

### Semântica correta esperada

- deveria representar “ainda não configurado” sem impedir bootstrap tardio;
- não deveria ser a barreira de entrada do console;
- deveria retornar estado vazio/pendente, não `404`.

### Classificação

- `BROKEN_BOOTSTRAP_404`
- `BACKEND_CONTRACT_ERROR`
- prioridade `P0`

## 8.2 `/integracoes/sankhya/config`

### O que o código realmente implementa

Em `services/api/integracoes/sankhya/routers/__init__.py`, `obter_config_sankhya(...)`:

- se `get_config(tenant_id)` não encontrar `SankhyaConfig`, retorna `404 "Sankhya não configurado"`.

### Semântica atual real

- ausência de `SankhyaConfig`

### Avaliação

- este `404` é coerente como “configuração provider-specific ainda não criada”.
- o frontend já o interpreta corretamente como formulário inicial.

### Classificação

- `EXPECTED_BOOTSTRAP_404`
- `PROVIDER_CONFIG_MISSING`
- prioridade `P3`

## 8.3 `/providers/{slug}/schema`

### O que o código realmente implementa

- consulta apenas `MarketplaceIntegracao` por slug;
- rejeita provider inexistente (`404`);
- rejeita provider não ERP (`400`);
- rejeita provider inativo (`400`);
- não consulta implantação;
- não consulta Wizard;
- não consulta `TenantIntegracao`;
- não consulta `SankhyaConfig`.

### Avaliação

- o schema do provider ativo está corretamente desacoplado do bootstrap do tenant.

## 9. Relação com implantação e Wizard

## 9.1 Resultado da auditoria

Perguntas obrigatórias:

1. Algum endpoint ERP consulta `ImplantacaoOperacional`?
   - Não no fluxo auditado do router ERP.
2. Algum service exige implantação ativa?
   - Não foi encontrado.
3. Algum service exige implantação concluída?
   - Não foi encontrado.
4. Algum service usa provider escolhido no Wizard?
   - Não no fluxo auditado.
5. Algum service falha sem registro de Wizard?
   - Não foi encontrado.
6. O Console depende de `marketplace_integracao_id` salvo no Wizard?
   - Não.
7. O provider pode ser escolhido diretamente no Console?
   - Sim, no frontend.
8. A configuração posterior altera implantação?
   - Não foi encontrado acoplamento.
9. O checklist ERP interfere?
   - O readiness service existe, mas o router ERP auditado usa um `_runtime_probe` artificial, não uma implantação real.
10. Existe redirect ou guard ligado ao onboarding?
   - Não no fluxo do Console ERP auditado.

## 9.2 Evidência

- `services/api/integracoes/erp/router.py` cria `_runtime_probe(tenant_id)` com `SimpleNamespace`, sem carregar implantação.
- No banco auditado, `farms.wizard_implantacoes_operacionais` está vazio e ainda assim:
  - `GET /integracoes/erp/providers/sankhya/schema` => `200`
  - `GET /integracoes/sankhya/config` => funciona semanticamente

### Conclusão

- `INSTALLATION_DEPENDENCY`: não comprovada.
- `WIZARD_DEPENDENCY`: não comprovada.

## 10. Relação com `TenantIntegracao`

## 10.1 Como `/erp/status` procura `TenantIntegracao`

`ErpReadinessService.carregar_runtime(...)` consulta `TenantIntegracao` com filtros:

- mesmo `tenant_id`
- `deleted_at IS NULL`
- `scope_type IN (TENANT, ESTABELECIMENTO)`
- `lifecycle_state NOT IN (REMOVED, REVOKED)`
- provider ativo do tipo ERP

### Observações

- o runtime ignora integração removida/revogada;
- o runtime exige materialização canônica para considerar provider/config;
- sem linha canônica, o router ERP cai no fallback legacy Sankhya ou no `404`.

## 10.2 Respostas obrigatórias

1. A ausência de `TenantIntegracao` é válida antes do primeiro save?
   - Sim.
2. O frontend consegue chegar ao formulário sem essa linha?
   - Sim, desde que consiga carregar schema e trate `GET /sankhya/config` como `404` esperado.
3. O POST da configuração cria a linha?
   - Pelo código, sim.
4. A criação é idempotente?
   - Sim, o adapter trata colisões únicas com reread.
5. O adapter ainda é a única camada que cria?
   - No fluxo auditado, sim.
6. O router ERP tenta descobrir Sankhya antes da criação?
   - Sim.
7. Existe dependência circular?
   - Parcialmente, sim na superfície ERP genérica:
     - `/erp/status` exige contexto ativo ou legacy;
     - o primeiro save deveria criar esse contexto;
     - logo, `/erp/status` não deveria ser gate de bootstrap.

### Classificação

- `TENANT_INTEGRATION_MISSING`
- `PROVIDER_RESOLUTION_FAILURE`
- prioridade `P0`

## 11. Relação com `SankhyaConfig`

## 11.1 GET

- `GET /sankhya/config` retorna `404` quando não existe.
- Isso está correto para o recurso provider-specific.

## 11.2 POST

Pelo código de `configurar_sankhya(...)` e `SankhyaSyncService.criar_config(...)`:

1. aceita inexistência de config prévia;
2. cria `SankhyaConfig`;
3. chama `adapter.sync_provider_config(...)`;
4. o adapter `_ensure_config(...)` cria `TenantIntegracao` se não existir.

### Respostas obrigatórias

1. `GET config` retorna 404 quando não existe: correto?
   - Sim.
2. `POST config` aceita inexistência?
   - Sim.
3. `POST config` cria `SankhyaConfig`?
   - Sim.
4. Depois cria `TenantIntegracao`?
   - Sim, via adapter.
5. Existe consulta prévia que exige `TenantIntegracao`?
   - Não para `POST /sankhya/config`.
6. Existe FK ou dependência de implantação?
   - Não encontrada.
7. Existe fallback que busca `SankhyaConfig` para resolver provider?
   - Sim, no router ERP.
8. O fallback causa ciclo ou ambiguidade?
   - Causa ambiguidade de contrato e mascaramento de bootstrap no router genérico.

## 12. Provider selecionado apenas no frontend

## 12.1 Auditoria do fluxo

No frontend:

- `ErpConsole` abre seletor quando `GET /integracoes/erp/status` devolve `404`.
- Após seleção visual do provider, `DynamicErpConsole` monta com `providerSlug = "sankhya"`.
- O slug selecionado é suficiente para:
  - carregar schema;
  - carregar `GET /sankhya/config`;
  - apontar `POST /sankhya/config`.

## 12.2 Respostas obrigatórias

- Algum endpoint exige provider persistido antes do POST?
  - Não no `POST /sankhya/config`.
- O slug no wrapper é suficiente?
  - Sim.
- O backend valida o provider pelo Marketplace?
  - Sim no endpoint de schema e no adapter/provider canônico.
- O POST Sankhya assume que o provider já está materializado?
  - Não. O adapter materializa canonicamente.

### Conclusão

- O frontend tardio está suficiente para bootstrap provider-specific.
- O gargalo é o contrato do router ERP genérico para superfícies operacionais antes da primeira materialização.

## 13. Auditoria do router ERP

## 13.1 `services/api/integracoes/erp/router.py`

### Achados

1. O router retorna `404` antes de permitir superfícies como `status`, `health`, `jobs`, `timeline` e `diagnostico`.
2. O router depende de fallback Sankhya.
3. O router não distingue:
   - não configurado;
   - provider indisponível;
   - integração inexistente;
   - bootstrap tardio.
4. O `404` não parece contrato deliberado de “estado vazio”, e sim efeito da ausência de contexto resolvível.
5. O router exige integração ativa ou fallback legacy para endpoints que deveriam tolerar bootstrap.

### Respostas obrigatórias

1. O router retorna 404 antes de permitir config?
   - Antes da config provider-specific, ele retorna 404 nas superfícies genéricas. O endpoint provider-specific continua acessível.
2. O router depende do fallback Sankhya?
   - Sim.
3. Ele distingue “não configurado” de “provider indisponível”?
   - Não adequadamente.
4. Ele deveria retornar estado vazio em vez de 404?
   - Sim para `/erp/status` e superfícies operacionais genéricas.
5. O 404 é contrato deliberado ou efeito de ausência?
   - Efeito de ausência.
6. O router exige integração ativa para endpoints que deveriam funcionar no bootstrap?
   - Sim.

## 14. Auditoria do router Sankhya

## 14.1 `services/api/integracoes/sankhya/routers/__init__.py`

### Achados

- `GET /config` usa `404` semântico de recurso ausente.
- `POST /config` suporta create/update.
- `POST /config/testar-conexao` não exige config materializada de antemão para responder; quando a config falta, retorna `200` com mensagem operacional de ausência.

### Conclusão

- O router Sankhya está semanticamente mais próximo do bootstrap tardio correto do que o router ERP genérico.

## 15. Service e adapter

## 15.1 `SankhyaSyncService`

### Achados

- `criar_config(...)` normaliza, persiste `SankhyaConfig` e chama `adapter.sync_provider_config(...)`.
- `atualizar_config(...)` também sincroniza canônico.
- `obter_config_console(...)` mascara segredos.
- `testar_conexao(...)` devolve `200` com diagnóstico, inclusive quando a configuração não existe.

## 15.2 `SankhyaCanonicalAdapter`

### Achados

- `sync_provider_config(...)` garante provider, credenciais, config canônica, features, policies, health e versionamento.
- `_ensure_config(...)` materializa `TenantIntegracao` caso ela não exista.
- Há tratamento explícito de idempotência para colisões únicas.

### Conclusão

- O primeiro save está desenhado para bootstrap tardio sem Wizard.

## 16. Auditoria do frontend

## 16.1 `ErpConsole`

- `GET /integracoes/erp/status` com `404` abre o seletor de provider.
- Isso significa que o `404` inicial do status não é fatal para chegar ao seletor.

## 16.2 `DynamicErpConsole`

- Depois da seleção do provider, o console chama em paralelo:
  - schema do provider
  - diagnóstico ERP
  - config provider-specific
  - status ERP
  - health ERP
  - jobs ERP
  - timeline ERP

- `GET /sankhya/config` com `404` é tratado com `allowNotFound: true`.
- `GET /erp/status` com `404` vira `not_found`, não bloqueia necessariamente o formulário.

## 16.3 `ConfigurationSection`

- `schema loading` => alerta explícito.
- `schema error/not_found` => alerta explícito + retry.
- `schema empty` => mensagem explícita.
- `config 403` => mensagem explícita sem interpretar como primeira configuração.
- `config 500` => mensagem explícita + retry.
- `config 404` => mensagem “ainda não possui configuração salva” e formulário visível.

### Conclusão

- O frontend está separando corretamente:
  - `404` de status para abrir seleção inicial;
  - `404` de config para abrir formulário inicial.
- O `404` observado no DevTools pode ser esperado ou não dependendo do endpoint.
- Neste caso:
  - `/sankhya/config` => esperado
  - `/erp/status` => semanticamente incorreto para bootstrap tardio

## 17. Diferenciação formal dos achados

### `EXPECTED_BOOTSTRAP_404`

- `GET /api/v1/integracoes/sankhya/config` quando a configuração ainda não existe.

### `BROKEN_BOOTSTRAP_404`

- `GET /api/v1/integracoes/erp/status` quando o tenant ainda não possui `TenantIntegracao` e também não possui `SankhyaConfig`.

### `MISSING_TENANT_INTEGRATION`

- Ausência válida antes do primeiro save.

### `MISSING_PROVIDER_CONFIG`

- Ausência válida antes do primeiro save provider-specific.

### `LEGACY_DRIFT`

- `SankhyaConfig` existente sem `TenantIntegracao`.

### `BACKEND_CONTRACT_ERROR`

- Surface ERP genérica usa `404` para um estado que deveria ser representável sem erro.

### `NON_BLOCKING`

- `GET /sankhya/config` com `404`, desde que o formulário continue aparecendo.

### `PILOT_BLOCKER`

- Bootstrap tardio quebrado no `/erp/status` é bloqueador quando impedir usuário de sair do estado vazio operacionalmente.

## 18. Cenários obrigatórios

| Cenário | Evidência | Resultado |
| --- | --- | --- |
| A — Tenant novo com ERP no Wizard | análise estática | Deve funcionar após materialização canônica; não havia massa pronta no banco |
| B — Tenant novo com “Configurar depois” | análise estática + tenant vazio real sem Wizard | Deve conseguir schema e primeiro save; hoje `/erp/status` ainda retorna `404` |
| C — Tenant legado sem Wizard | tenant real `Grancafé` | Funciona parcialmente via fallback legacy |
| D — Tenant implantado sem ERP | análise estática | Não há evidência de exigência de reabrir implantação/Wizard |
| E — Tenant com provider selecionado, mas sem config | análise estática + E2E frontend | Formulário deve abrir |
| F — Tenant sem `TenantIntegracao` e sem `SankhyaConfig` | tenant real `Dry Run Fazenda` | Cenário principal quebrado na superfície ERP genérica |
| G — Tenant com `SankhyaConfig`, mas sem `TenantIntegracao` | tenant real `Grancafé` | Compatibilidade legacy funciona no status/health/jobs/timeline |
| H — Tenant com `TenantIntegracao`, mas sem `SankhyaConfig` | análise estática | Não havia massa pronta; o runtime canônico deveria resolver status |
| I — Integração inativa | análise estática | runtime filtraria por lifecycle/estado; sem massa pronta |
| J — Integração soft-deleted | análise estática | runtime ignora `deleted_at` preenchido; sem massa pronta |

## 19. Matriz obrigatória de dados

| Cenário | Implantação | Wizard ERP | TenantIntegracao | SankhyaConfig | Status HTTP | Formulário possível |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Dry Run Fazenda (F) | 0 | 0 | 0 | 0 | `/erp/status` = 404, `/schema` = 200, `/sankhya/config` = 404 | Sim, pelo frontend |
| Grancafé (G/C) | 0 | 0 | 0 | 1 | `/erp/status` = 200, `/sankhya/config` = 200 | Sim |
| A | n/d | n/d | análise estática | análise estática | n/d | esperado sim |
| B | n/d | n/d | análise estática | análise estática | n/d | esperado sim |
| H | n/d | n/d | análise estática | análise estática | n/d | esperado sim |
| I | n/d | n/d | análise estática | análise estática | n/d | depende do contrato futuro |
| J | n/d | n/d | análise estática | análise estática | n/d | deveria voltar ao seletor/estado vazio |

## 20. Dependência de Unidade Produtiva

- Não foi encontrada dependência de `unidade_produtiva_id` no fluxo auditado de configuração ERP.
- Não foi encontrada exigência de primeira UP ou de implantação associada a UP.
- Não foi encontrada exigência de UP para o primeiro save de configuração.

### Conclusão

- `INSTALLATION_DEPENDENCY` por UP não foi comprovada.
- Qualquer dependência futura desse tipo deve ser tratada como defeito arquitetural.

## 21. Permissões

- Endpoints auditados usam `require_tenant_permission(...)`.
- O usuário autenticado utilizado na reprodução era owner do tenant.
- Não houve indício de `403` mascarado em `404` nos cenários reproduzidos.

### Conclusão

- `PERMISSION_MASQUERADE`: não comprovada no 404 principal auditado.

## 22. Logs e observabilidade

## 22.1 Observado

- O endpoint `GET /api/v1/integracoes/erp/diagnostico` retornou `500` com corpo estruturado incluindo `error` e `request_id`.
- Para o `404` de `/erp/status`, a evidência observada foi a própria resposta HTTP:
```json
{"detail":"ERP não configurado"}
```

## 22.2 Auditoria de logging

- Não foi encontrado logging estruturado específico no caminho de `services/api/integracoes/erp/router.py` para distinguir:
  - integração inexistente;
  - configuração inexistente;
  - provider inexistente;
  - implantação inexistente;
  - acesso negado.

### Conclusão

- A observabilidade do `404` genérico é fraca.
- O router ERP devolve `404`, mas não expõe no log do próprio fluxo qual recurso faltou.

## 23. Testes existentes

## 23.1 Backend

- `services/api/tests/unit/integracoes/test_erp_router.py`
  - cobre fallback legacy para status;
  - cobre `404 "ERP não configurado"` quando não há runtime nem legacy.
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
  - cobre criação de `SankhyaConfig` e materialização de `TenantIntegracao`;
  - cobre fluxo de status/health/timeline/jobs a partir do legado sincronizado.

## 23.2 Frontend

- `apps/web/tests/e2e/erp-console-configuracao.spec.ts`
  - cobre `status 404` com seletor;
  - cobre `config 404` com formulário visível;
  - cobre schema failure + retry;
  - cobre `403` e `500` específicos de configuração.

## 23.3 Lacunas

- Não foi localizada cobertura backend explícita para “tenant vazio + primeiro save tardio sem Wizard” como fluxo integrado fim a fim.
- Não foi localizada cobertura para drift real de produção com `SankhyaConfig` existente e `tenant_integracoes` vazio fora do path de fallback.
- Não foi localizada cobertura para contrato semântico alternativo de `/erp/status` representando estado vazio em vez de `404`.

## 24. Causa raiz

## 24.1 Causa raiz principal

- O router ERP genérico foi desenhado para delegar apenas quando já consegue resolver um provider ativo.
- Sem `TenantIntegracao` canônica e sem `SankhyaConfig` legacy, `_resolve_active_erp_provider_slug(...)` encerra o fluxo com `404`.
- Esse contrato transforma “tenant autenticado ainda sem ERP materializado” em erro HTTP, em vez de estado de bootstrap.

## 24.2 Causa raiz secundária

- Existe drift legado no banco:
  - `SankhyaConfig` existe;
  - `TenantIntegracao` não existe.
- O fallback legacy evita o erro em parte dos tenants, mas mantém ambiguidade arquitetural.

## 25. Impacto no piloto

### Classificação

- `Request 404 esperado`:
  - `/sankhya/config` não bloqueia, porque o formulário pode aparecer.
- `Bootstrap quebrado`:
  - `/erp/status` é bloqueador semântico do lifecycle genérico.
- `Drift legado`:
  - exige tratamento antes de ampliar o contrato multiprovider.

### Veredicto de impacto

- `GO COM RESSALVAS`

### Justificativa

- O frontend atual ainda consegue chegar ao formulário ao tratar `404` inicial de status e `404` de config.
- Porém o backend genérico ERP continua expressando bootstrap tardio como ausência de recurso, o que é contrato ruim e pode quebrar consumidores futuros, superfícies operacionais e diagnóstico.

## 26. Menor correção recomendada

## 26.1 Correção mínima definitiva

- Corrigir o contrato de bootstrap do router ERP genérico, começando por `/api/v1/integracoes/erp/status`, para representar:
  - tenant autenticado;
  - provider ainda não materializado;
  - configuração ainda não criada;
  - integração ausente antes do primeiro save

sem usar `404`.

### Forma recomendada

- preservar `404` apenas para recursos realmente inexistentes, como `GET /sankhya/config` antes do primeiro save;
- fazer `/erp/status` retornar estado vazio/pendente/não configurado;
- manter o provider schema desacoplado;
- preservar a criação de `TenantIntegracao` no primeiro save provider-specific;
- adicionar compatibilidade legada explícita para tenants com `SankhyaConfig` sem linha canônica.

## 26.2 O que não fazer

- Não reacoplar o Console ao Sankhya no componente genérico.
- Não transferir a responsabilidade de bootstrap para Wizard ou implantação.
- Não exigir criação manual de `TenantIntegracao` antes do primeiro save.

## 27. Plano incremental recomendado

### ERP-LIFECYCLE-02A — Correção do bootstrap tardio

- Remover a dependência indevida de contexto ativo para `/erp/status` e superfícies operacionais tolerantes ao vazio.
- Permitir primeiro save sem necessidade de materialização prévia.
- Preservar `404` esperado apenas em `GET /config` provider-specific.

### ERP-LIFECYCLE-02B — Compatibilidade legada

- Reconhecer e reconciliar `SankhyaConfig` sem `TenantIntegracao`.
- Materializar canônico de forma idempotente.
- Evitar duplicidade.

### ERP-LIFECYCLE-02C — Contrato semântico do status

- Distinguir formalmente:
  - não selecionado;
  - não configurado;
  - incompleto;
  - conectado;
  - inativo.

### ERP-CORE-REPAIR-01A

- Somente depois de estabilizar bootstrap e compatibilidade legada.

## 28. Arquivos prováveis de correção futura

- `services/api/integracoes/erp/router.py`
- `services/api/integracoes/erp_readiness_service.py`
- possivelmente `services/api/integracoes/sankhya/services/canonical_adapter.py` ou `sync_service.py` apenas se a reconciliação legada exigir ajuste explícito
- testes backend e E2E correlatos

## 29. Guardrails para a próxima fase

- Não alterar Wizard.
- Não acoplar bootstrap à implantação.
- Não introduzir inferência por slug no frontend genérico além do contrato já existente.
- Não reinstalar hardcode Sankhya no console genérico.
- Não quebrar o `404` esperado de `GET /sankhya/config`.
- Não criar dependência de `UnidadeProdutiva`.

## 30. Respostas objetivas às perguntas obrigatórias

1. Qual endpoint retorna o 404 observado?
   - Principalmente `GET /api/v1/integracoes/erp/status`.
2. O 404 é esperado?
   - Em `/erp/status`, não. Em `/sankhya/config`, sim.
3. Qual registro está ausente?
   - No cenário principal, faltam `TenantIntegracao` e `SankhyaConfig`.
4. A implantação influencia?
   - Não foi comprovado.
5. O Wizard influencia?
   - Não foi comprovado.
6. `TenantIntegracao` está ausente?
   - Sim, inclusive o ambiente auditado está com `tenant_integracoes` zerado.
7. `SankhyaConfig` está ausente?
   - No tenant principal, sim. No tenant legado, não.
8. O schema carrega?
   - Sim.
9. O formulário deveria aparecer?
   - Sim.
10. O POST de configuração funcionaria?
   - Pelo código e testes, sim.
11. O backend consegue criar a configuração sem implantação?
   - Sim, pelo código auditado.
12. O backend consegue criar `TenantIntegracao` no primeiro save?
   - Sim, via adapter.
13. Existe ciclo entre status e configuração?
   - Sim, na semântica do router ERP genérico.
14. Tenant legado funciona?
   - Parcialmente, via fallback legacy.
15. Tenant pós-implantação funciona?
   - Não há evidência de dependência de implantação; o problema é bootstrap de contrato, não de implantação.
16. O erro é frontend, backend ou contrato?
   - Primariamente backend/contrato.
17. É bloqueador do piloto?
   - Sim como risco de bootstrap/lifecycle; classificado `GO COM RESSALVAS`, não `NO-GO`, porque o frontend atual ainda contorna parte do problema.
18. Qual é a menor correção?
   - Corrigir `/erp/status` e superfícies correlatas para retornar estado vazio em vez de `404`.
19. A correção pertence ao core repair?
   - Sim, ao eixo lifecycle/bootstrap antes do multiprovider pleno.
20. O contrato 404 deve ser preservado?
   - Apenas para `GET /config` provider-specific. Não para `/erp/status`.

## 31. Veredictos

### Semântica do 404

- `/api/v1/integracoes/erp/status` => `INCORRETO`
- `/api/v1/integracoes/sankhya/config` => `ESPERADO`

### Bootstrap tardio

- `QUEBRADO`

### Piloto

- `GO COM RESSALVAS`

## 32. Veredicto final

- O 404 que sustenta a suspeita do incidente não é de schema nem de Wizard.
- O problema central é contratual no router ERP genérico:
  - ele exige contexto ativo cedo demais;
  - trata bootstrap tardio como ausência de recurso;
  - usa fallback legacy Sankhya para mascarar parte dos casos.
- O backend já contém a base para o primeiro save tardio:
  - schema desacoplado;
  - create provider-specific;
  - materialização canônica idempotente.
- A menor correção definitiva é estabilizar o bootstrap semântico de `/erp/status` e compatibilizar drift legado antes de avançar para `ERP-CORE-REPAIR-01A`.
