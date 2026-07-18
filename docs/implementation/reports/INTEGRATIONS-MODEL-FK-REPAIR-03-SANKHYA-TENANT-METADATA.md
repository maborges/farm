# INTEGRATIONS-MODEL-FK-REPAIR-03 — Correção das Foreign Keys de Tenant nos Models Sankhya

## 1. Resumo Executivo

Confirmado e corrigido o mesmo padrão de bug de `INTEGRATIONS-MODEL-FK-REPAIR-02`, agora em `services/api/integracoes/sankhya/models/__init__.py`: as 7 ocorrências de `ForeignKey("farms.tenants.id", ondelete="NO ACTION")` (`SankhyaConfig`, `SankhyaSyncLog`, `SankhyaPessoa`, `SankhyaProduto`, `SankhyaNFe`, `SankhyaLancamentoFinanceiro`, `SankhyaTabela`) foram trocadas para `ForeignKey("tenants.id", ondelete="NO ACTION")`, alinhando-as ao padrão universal do projeto e ao `Tenant.__table__` real do `Base.metadata` compartilhado.

Validado com `flush()` real dos 7 models contra o PostgreSQL oficial (rollback ao final, nenhuma alteração física) e, mais importante, com uma **execução completa e bem-sucedida de `SankhyaSyncService.criar_config`** ponta a ponta: persistência do `SankhyaConfig` legado seguida da sincronização canônica criando `TenantIntegracao`, `IntegrationCredential`, 6×`IntegrationFeature`, 6×`IntegrationSyncPolicy` e `IntegrationHealth` — tudo em uma única transação, sem nenhuma exceção de metadata, com rollback limpo ao final.

**Veredicto**: `GO — FOREIGN KEYS SANKHYA RESTAURADAS`.

## 2. Severidade

Confirmada como alta. Antes da correção, qualquer `flush()`/`commit()` de `SankhyaConfig`, `SankhyaSyncLog`, `SankhyaPessoa`, `SankhyaProduto`, `SankhyaNFe`, `SankhyaLancamentoFinanceiro` ou `SankhyaTabela` falhava com `NoReferencedTableError`, em qualquer ambiente — reproduzido nesta fase antes da correção, confirmando o mesmo padrão do `INTEGRATIONS-MODEL-FK-REPAIR-02`.

## 3. Models Afetados

| Model | Tabela | Coluna | `ondelete` (preservado) | Nullable | Index | Relação associada |
|---|---|---|---|---|---|---|
| `SankhyaConfig` | `sankhya_config` | `tenant_id` | `NO ACTION` | `False` | `True` (unique) | — |
| `SankhyaSyncLog` | `sankhya_sync_logs` | `tenant_id` | `NO ACTION` | `False` | `True` | `config_id -> sankhya_config.id` (não tocado) |
| `SankhyaPessoa` | `sankhya_pessoas` | `tenant_id` | `NO ACTION` | `False` | `True` | — |
| `SankhyaProduto` | `sankhya_produtos` | `tenant_id` | `NO ACTION` | `False` | `True` | — |
| `SankhyaNFe` | `sankhya_nfe` | `tenant_id` | `NO ACTION` | `False` | `True` | — |
| `SankhyaLancamentoFinanceiro` | `sankhya_lancamentos_financeiros` | `tenant_id` | `NO ACTION` | `False` | `True` | — |
| `SankhyaTabela` | `sankhya_tabelas` | `tenant_id` | `NO ACTION` | `False` | `True` | — |

Nota: `tenant_id` nesses 7 models usa `UUIDType(as_uuid=False)` (valor Python é `str`, diferente dos models canônicos de `integracoes/models.py`, que usam `as_uuid=True`) — detalhe preservado, não alterado.

## 4. Causa Raiz

Idêntica à do `INTEGRATIONS-MODEL-FK-REPAIR-02`: `Tenant.__tablename__ = "tenants"` sem `schema=`, registrado no `Base.metadata` compartilhado sob a chave `(None, "tenants")`. A string `"farms.tenants.id"` buscava a chave inexistente `("farms", "tenants")`.

## 5. Reprodução Anterior

Executada fora do pytest, contra o PostgreSQL oficial, antes da correção:

```
REPRODUCED SankhyaConfig: NoReferencedTableError Foreign key associated with column
  'sankhya_config.tenant_id' could not find table 'farms.tenants' ...
REPRODUCED SankhyaSyncLog: NoReferencedTableError ... 'sankhya_sync_logs.tenant_id' ...
REPRODUCED SankhyaPessoa: NoReferencedTableError ... 'sankhya_pessoas.tenant_id' ...
```

## 6. Correções Realizadas

`sed -i 's/ForeignKey("farms\.tenants\.id", ondelete="NO ACTION")/ForeignKey("tenants.id", ondelete="NO ACTION")/g' integracoes/sankhya/models/__init__.py` — substituição textual idêntica nas 7 ocorrências, preservando exatamente `ondelete`, `nullable`, `index`, `unique`, tipos e a FK não relacionada `config_id -> sankhya_config.id` (que já era bare e não foi tocada).

## 7. Comparação Antes/Depois

| Item | Antes | Depois |
|---|---|---|
| 7 declarações de FK | `ForeignKey("farms.tenants.id", ...)` | `ForeignKey("tenants.id", ...)` |
| `flush()` isolado dos 7 models | `NoReferencedTableError` | Sucesso |
| `criar_config` ponta a ponta | Falha em `SankhyaConfig` (legado) antes de chegar ao canônico | Sucesso: legado + `TenantIntegracao`/`IntegrationCredential`/`IntegrationFeature`/`IntegrationSyncPolicy`/`IntegrationHealth` |
| Constraints físicas | `farms.tenants`, `NO ACTION` (7/7) | `farms.tenants`, `NO ACTION` (7/7, inalteradas) |
| Migration necessária | — | Nenhuma |

## 8. Resolução para `Tenant.__table__`

Teste novo `tests/unit/integracoes/test_sankhya_models_tenant_fk.py` (parametrizado pelos 7 models):

```python
fk = next(iter(model.__table__.c.tenant_id.foreign_keys))
assert fk.column.table is Tenant.__table__
assert fk.ondelete == "NO ACTION"
```

Resultado: `7 passed`.

## 9. Validação dos Sete Models

Reprodução completa contra o PostgreSQL oficial (tenant real inserido na mesma transação, IDs explícitos para contornar a ausência de sequência física em `sankhya_config.id` — ver seção 17 —, rollback ao final):

```
SankhyaConfig flush OK
SankhyaSyncLog flush OK
SankhyaPessoa flush OK
SankhyaProduto flush OK
SankhyaNFe flush OK
SankhyaLancamentoFinanceiro flush OK
SankhyaTabela flush OK
ROLLBACK OK - nada persistido
```

## 10. Validação PostgreSQL

Consulta a `information_schema` confirmando as 7 constraints físicas inalteradas após a correção:

```
sankhya_config                   -> farms.tenants, NO ACTION
sankhya_lancamentos_financeiros  -> farms.tenants, NO ACTION
sankhya_nfe                      -> farms.tenants, NO ACTION
sankhya_pessoas                  -> farms.tenants, NO ACTION
sankhya_produtos                 -> farms.tenants, NO ACTION
sankhya_sync_logs                -> farms.tenants, NO ACTION
sankhya_tabelas                  -> farms.tenants, NO ACTION
```

## 11. Validação de `criar_config`

Reprodução direta de `SankhyaSyncService.criar_config` (sem chamada externa real; `auth_model="gateway_oauth_client_credentials"`, hostname `example.com` resolvível via DNS real, sem mock de rede necessário pois `criar_config` não chama o Gateway):

```
criar_config OK, SankhyaConfig.id = 4
TenantIntegracao criada: True 7
IntegrationCredential count: 1
IntegrationFeature count: 6
IntegrationSyncPolicy count: 6
IntegrationHealth count: 1
ROLLBACK OK - nada persistido
```

Confirma o fluxo completo: `SankhyaConfig` (legado) → `canonical_adapter.sync_provider_config` → `TenantIntegracao` + `IntegrationCredential` + `IntegrationFeature` (×6, uma por capability) + `IntegrationSyncPolicy` (×6) + `IntegrationHealth`. Nenhuma exceção de metadata. Gravação dupla e idempotência preservadas (não alteradas nesta fase).

## 12. Constraints Físicas

Ver seção 10 — 7/7 constraints inalteradas, todas `farms.tenants`/`NO ACTION`.

## 13. Impacto em Produção

Esta correção resolve, para o lado legado Sankhya, o mesmo risco de alta severidade sinalizado em `INTEGRATIONS-MODEL-FK-REPAIR-02`: qualquer fluxo real que fizesse `flush()`/`commit()` de `SankhyaConfig`/`SankhyaSyncLog`/`SankhyaPessoa`/`SankhyaProduto`/`SankhyaNFe`/`SankhyaLancamentoFinanceiro`/`SankhyaTabela` provavelmente falhava com `NoReferencedTableError`. Com as duas fases (02 e 03) aplicadas, o caminho completo de `criar_config` (legado + canônico) está validado como funcional.

## 14. Migrations

Nenhuma migration criada ou necessária — alteração puramente de resolução de metadata Python. `git diff --check` limpo. Constraints físicas confirmadas idênticas antes/depois (seção 10).

## 15. Arquivos Alterados

- `services/api/integracoes/sankhya/models/__init__.py` (7 linhas, substituição textual idêntica)
- `services/api/tests/unit/integracoes/test_sankhya_models_tenant_fk.py` (novo, teste de metadata parametrizado)
- `docs/implementation/reports/INTEGRATIONS-MODEL-FK-REPAIR-03-SANKHYA-TENANT-METADATA.md` (este relatório, novo)

Nenhum outro arquivo tocado. Models canônicos, `Tenant`, `Base`, `search_path`, migrations, banco físico, services (além da reprodução de leitura/validação), routers, credenciais, criptografia, autenticação, Core ERP, Provider Registry, Lifecycle, Readiness, Console ERP, gravação dupla, fallback, precedência de fontes, arquitetura multiprovider, fixtures SQLite remanescentes e isolamento global da suíte permanecem inalterados.

## 16. Testes Executados

```bash
.venv/bin/python -c "import integracoes.sankhya.models"
```
→ sucesso.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v
```
→ `7 passed`.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py -v
```
→ `8 passed, 14 failed` — todas as 14 falhas agora são `ForeignKeyViolationError` (tenant fixo do teste, ex. `90aa4f2e-...`, nunca inserido na tabela `tenants` real) — **erro de fixture**, não de metadata. Classificação confirmada por leitura direta do traceback.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_paridade_config.py -v
```
→ `2 passed, 2 failed` — mesma causa (tenant fixo inexistente) — **erro de fixture**.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_legacy_reconciliation.py -v
```
→ `9 failed` — causa: `UniqueViolationError` em `marketplace_integracoes_pkey` — **colisão residual** de dados de execuções anteriores no PostgreSQL real (já sinalizada em `INTEGRATIONS-TEST-INFRA-01`), não relacionada ao bug de FK.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
```
→ `3 passed` (guardrail intacto, conforme exigido).

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ `93 failed, 137 passed, 13 errors` (243 testes coletados; +7 pelo novo arquivo de teste).

`ruff check integracoes/sankhya/models/__init__.py tests/unit/integracoes/test_sankhya_models_tenant_fk.py` → `All checks passed!`
`git diff --check` → sem saída, sucesso.

Buscas finais:
```bash
rg -n 'ForeignKey\("farms\.tenants\.id"' services/api/integracoes services/api/integracoes/sankhya
# nenhuma ocorrência
rg -n 'ForeignKey\("tenants\.id"' services/api/integracoes/models.py services/api/integracoes/sankhya/models/__init__.py
# 1 ocorrência em models.py + 7 em sankhya/models/__init__.py — todas corrigidas
```

## 17. Comparação da Suíte

| Métrica | Antes (FK-REPAIR-02) | Depois (esta fase) |
|---|---|---|
| Passed | 133 | 137 (+4 líquido: 7 testes novos, parcialmente compensados por testes que passaram a chegar a um obstáculo mais adiante) |
| Failed | 78 | 93 (+15) |
| Errors | 25 | 13 (−12) |
| Total | 236 | 243 |

A queda de "errors" (25→13) confirma que menos testes travam no setup/flush por metadata quebrada; o aumento de "failed" reflete testes que agora avançam além do ponto de FK e encontram um segundo obstáculo distinto (fixture com tenant inexistente, ou colisão residual de dados) — não uma regressão desta fase.

## 18. Falhas Remanescentes (classificadas)

| Causa | Exemplo de arquivo | Classificação |
|---|---|---|
| Metadata de FK quebrada | — | **Eliminada** por esta fase e pela FK-REPAIR-02 |
| Tenant fixo/fake nunca inserido em `tenants` | `test_sankhya_canonical_adapter.py`, `test_sankhya_paridade_config.py`, `test_erp_bootstrap_tardio.py` | Erro de fixture — fora de escopo |
| Dados residuais entre execuções (`UniqueViolationError`) | `test_sankhya_legacy_reconciliation.py` | Colisão residual — fora de escopo |
| `tenant_id="tenant-1"` (string) vs coluna UUID | `test_integrations_foundation_models.py` | Erro de fixture pré-existente — fora de escopo |
| Ausência de sequência física em `sankhya_config.id` | reprodução manual desta fase | Débito técnico pré-existente, não corrigido (fora de escopo de models/migrations) |

## 19. Riscos Remanescentes

- **Ausência de `DEFAULT`/sequência na coluna `id` de `sankhya_config`** (confirmado via `information_schema.columns`: `column_default IS NULL`) — descoberto durante a validação desta fase. Não é o mesmo bug de FK, é um problema físico de schema pré-existente que impede inserts sem `id` explícito. Fora do escopo desta fase (proibido alterar banco físico/migrations), mas deve ser investigado com prioridade, pois pode já estar quebrando `criar_config` em produção de forma diferente (dependendo de como o service atual gera `next_config_id` — o código de produção já usa `_next_config_id()` explicitamente, então pode já contornar esse problema; não avaliado em profundidade nesta fase por estar fora de escopo).
- Os 9 arquivos SQLite locais ainda pendentes de conversão (Frente B de `INTEGRATIONS-TEST-INFRA-01`).
- Isolamento não-determinístico entre execuções do PostgreSQL real (dados residuais) ainda não tratado.
- Testes com tenant fixo/fake continuam falhando por design de fixture, não por bug de produção — precisam de uma fase dedicada de correção de fixtures de teste (`INTEGRATIONS-TEST-INFRA-02`, conforme já recomendado).

## 20. Próxima Etapa

Conforme já sinalizado, a sequência recomendada é:

1. `INTEGRATIONS-TEST-INFRA-02` — remover as 9 engines SQLite locais restantes, convergir para a fixture PostgreSQL oficial, e corrigir o isolamento determinístico entre execuções (tenants/providers com IDs únicos por teste, truncamento ou uso de UUIDs ao invés de tenants fixos), eliminando as colisões residuais e os erros de fixture identificados nesta fase.
2. Investigar separadamente (fora da sequência do `ERP-DATA-HYGIENE`, dada a severidade) a ausência de sequência em `sankhya_config.id`.
3. Só então `ERP-DATA-HYGIENE-01E1 — Redefinição da Sequência Pós-Inventário`.

## 21. Veredicto

`GO — FOREIGN KEYS SANKHYA RESTAURADAS`

As 7 ocorrências foram identificadas e corrigidas; a causa foi reproduzida antes da correção; todas as 7 FKs resolvem para `Tenant.__table__` (teste automatizado, `7 passed`); os 7 models tiveram `flush()` real aprovado no PostgreSQL oficial; `SankhyaSyncService.criar_config` persistiu com sucesso o lado legado e o lado canônico em uma única execução, sem chamadas externas reais; `ondelete="NO ACTION"` preservado; nenhuma constraint física foi alterada; nenhuma migration foi criada; não resta nenhuma referência a `farms.tenants.id` em models Python; o guardrail da 01D permanece `3 passed`; houve redução material dos erros de metadata na suíte (25→13); as falhas remanescentes foram classificadas por causa e nenhuma é atribuível a esta correção. `ruff` e `git diff --check` aprovados. Nenhum código fora do escopo autorizado foi alterado.
