# INTEGRATIONS-MODEL-FK-REPAIR-02 — Alinhamento da Foreign Key de Tenant ao Metadata Oficial

## 1. Resumo Executivo

Confirmada e corrigida a causa raiz identificada em `INTEGRATIONS-TEST-INFRA-01`: `integracoes/models.py`'s `_tenant_fk()` declarava `ForeignKey("farms.tenants.id", ondelete="NO ACTION")` — string com schema explícito — enquanto `core.models.tenant.Tenant` está registrado no `Base.metadata` compartilhado sob a chave bare `"tenants"` (sem schema), como os ~241 outros usos de `ForeignKey("tenants.id", ...)` em todo o restante da aplicação. A correção foi trocar a string para `"tenants.id"` (uma palavra, sem prefixo), restaurando a resolução de metadata do SQLAlchemy. Validado com `flush()` real contra o PostgreSQL oficial para os 9 models afetados — todos passaram, com `rollback()` ao final e nenhuma alteração física no banco.

**Achado adicional relevante, fora do escopo permitido**: o mesmo padrão de bug (`ForeignKey("farms.tenants.id", ...)`) existe, verbatim, em **7 outras ocorrências** em `services/api/integracoes/sankhya/models/__init__.py` (`SankhyaConfig`, `SankhyaSyncLog`, `SankhyaPessoa`, `SankhyaProduto`, `SankhyaNFe`, `SankhyaLancamentoFinanceiro`, `SankhyaTabela`). Como a correção desta fase foi restrita exclusivamente a `integracoes/models.py` (proibido alterar `SankhyaConfig`), esses 7 models **continuam quebrados** pelo mesmo motivo. Isso explica por que testes que envolvem `SankhyaConfig` (ex.: `test_sankhya_paridade_config.py`) continuam falhando com `NoReferencedTableError` mesmo após esta correção.

**Veredicto**: `GO COM RESSALVAS — METADATA CORRIGIDO, FLUXOS PARCIALMENTE VALIDADOS`.

## 2. Severidade

Alta, confirmada. O bug afetava (antes da correção) qualquer `flush()`/`commit()` ORM de `TenantIntegracao`, `IntegrationCredential`, `IntegrationVersion`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`, `ExternalRecordAssociation` e `ExternalRecordAssociationHistory`, em qualquer ambiente (dev, staging, produção), sempre que `integracoes.models` estivesse importado no processo — não é uma limitação de teste, é um bug de definição de modelo Python.

## 3. Causa Raiz

`ForeignKey._resolve_column()` busca a tabela de destino no `Base.metadata` compartilhado pela chave `(schema, tablename)`. `Tenant.__tablename__ = "tenants"` sem `schema=` é registrado sob a chave `(None, "tenants")`. A string `"farms.tenants.id"` faz o SQLAlchemy procurar a chave `("farms", "tenants")`, que não existe — o schema físico `farms` é resolvido inteiramente por `search_path` de conexão (`connect_args={'server_settings': {'search_path': 'farms'}}`), nunca por qualificação em string de FK, em nenhum outro lugar do código-base.

## 4. Reprodução Anterior (antes da correção)

Executada fora do pytest, direto contra o PostgreSQL oficial (`postgresql+asyncpg://borgus:...@192.168.0.2/farms`):

```
mi = MarketplaceIntegracao(...); session.add(mi); await session.flush()   # OK
ti = TenantIntegracao(tenant_id=uuid.uuid4(), integracao_id=mi.id)
session.add(ti); await session.flush()
# -> sqlalchemy.exc.NoReferencedTableError:
#    Foreign key associated with column 'tenant_integracoes.tenant_id'
#    could not find table 'farms.tenants' ...
```

Reproduzido de forma idêntica à investigação anterior, confirmando que o bug persistia antes desta correção.

## 5. Chave Real do Metadata

```python
from core.database import Base
import core.models.tenant
import integracoes.models
print('tenants' in Base.metadata.tables)       # True
print('farms.tenants' in Base.metadata.tables) # False
print(core.models.tenant.Tenant.__table__.key) # 'tenants'
```

## 6. Padrão de FKs do Projeto

```bash
rg -c 'ForeignKey\("tenants\.id"' . -g '*.py'   # soma: 241 ocorrências
rg -n 'ForeignKey\("farms\.tenants\.id"'         # 1 ocorrência em integracoes/models.py (antes da correção) +
                                                   # 7 ocorrências em integracoes/sankhya/models/__init__.py
rg -n 'schema\s*=\s*.farms.|schema="farms"'      # nenhum model Python declara schema="farms";
                                                   # todas as ocorrências de schema="farms" são em migrations Alembic (op.*), não em models
```

Nenhum model do projeto usa `__table_args__ = {"schema": "farms"}`. O padrão universal é `ForeignKey("tenants.id", ...)` bare, com resolução de schema via `search_path`.

## 7. Correção Implementada

`services/api/integracoes/models.py`:

```diff
 def _tenant_fk() -> ForeignKey:
-    return ForeignKey("farms.tenants.id", ondelete="NO ACTION")
+    return ForeignKey("tenants.id", ondelete="NO ACTION")
```

Uma única linha alterada. `ondelete="NO ACTION"` preservado. Nenhuma outra linha do arquivo tocada. `Tenant`, `Base`, `search_path`, migrations, constraints físicas e RLS não foram alterados.

## 8. Comparação Antes/Depois

| Item | Antes | Depois |
|---|---|---|
| `_tenant_fk()` retorna | `ForeignKey("farms.tenants.id", ...)` | `ForeignKey("tenants.id", ...)` |
| `flush()` de `TenantIntegracao` isolado | `NoReferencedTableError` | Sucesso |
| Constraint física no PostgreSQL | `farms.tenants`, `NO ACTION` | `farms.tenants`, `NO ACTION` (inalterada) |
| Migration necessária | — | Nenhuma |

## 9. Confirmação da Resolução para `Tenant.__table__`

```python
fk = next(iter(TenantIntegracao.__table__.c.tenant_id.foreign_keys))
print(fk.column.table is Tenant.__table__)  # True
print(fk.ondelete)                          # 'NO ACTION'
```

Teste adicionado (não apenas comparação de string) em `test_integrations_foundation_models.py::test_tenant_fk_resolve_para_tenant_table_no_metadata_compartilhado`, cobrindo os 9 models afetados via loop — `PASSED`.

## 10. Validação dos Nove Models

Reprodução completa contra o PostgreSQL oficial, com `Tenant` real inserido na mesma transação, `SET LOCAL app.current_tenant_id` configurado para satisfazer RLS, e `rollback()` ao final:

```
TenantIntegracao flush OK
IntegrationCredential flush OK
IntegrationFeature flush OK
IntegrationSyncPolicy flush OK
IntegrationHealth flush OK
IntegrationJob flush OK
ExternalRecordAssociation flush OK
IntegrationVersion flush OK
ExternalRecordAssociationHistory flush OK
ROLLBACK OK - nada persistido
```

Todos os 9 models resolvem e persistem corretamente agora.

## 11. Validação PostgreSQL

Confirmado por consulta direta a `information_schema` que as 9 constraints físicas permanecem intactas após a correção (nenhuma migration executada, nenhuma alteração física):

```
integration_credentials                        -> farms.tenants, NO ACTION
integration_external_record_link_history        -> farms.tenants, NO ACTION
integration_external_record_links               -> farms.tenants, NO ACTION
integration_features                            -> farms.tenants, NO ACTION
integration_health_snapshots                    -> farms.tenants, NO ACTION
integration_jobs                                -> farms.tenants, NO ACTION
integration_sync_policies                       -> farms.tenants, NO ACTION
integration_versions                            -> farms.tenants, NO ACTION
tenant_integracoes                              -> farms.tenants, NO ACTION
```

## 12. Validação de `criar_config`

`SankhyaSyncService.criar_config` cria primeiro um `SankhyaConfig` (ORM legado, definido em `integracoes/sankhya/models/__init__.py`) e, na sequência, sincroniza para `TenantIntegracao`/`IntegrationCredential`/etc. via `canonical_adapter`. Esta fase corrigiu apenas o lado canônico (`integracoes/models.py`). O lado legado (`SankhyaConfig`) **continua com o mesmo bug** (seção 1), pois está fora do escopo permitido (`SankhyaConfig` explicitamente proibido de alterar nesta fase). Portanto: `test_sankhya_paridade_config.py` (que exercita o fluxo E2E completo de `criar_config`) continua falhando com `NoReferencedTableError` em `sankhya_config.tenant_id` — não por regressão desta fase, mas porque a correção não podia, por escopo, alcançar esse arquivo.

Confirmado por execução direcionada:

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_paridade_config.py -v
# 2 failed (NoReferencedTableError em sankhya_config.tenant_id), 2 passed
```

## 13. Impacto Físico e Migrations

Nenhuma migration foi criada ou é necessária — a alteração é puramente de resolução de metadata Python (string de destino da `ForeignKey`), não de DDL físico. `git diff --check` limpo. Nenhum diff físico inesperado encontrado (seção 11 confirma constraints idênticas antes/depois).

## 14. Arquivos Alterados

- `services/api/integracoes/models.py` (1 linha)
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py` (1 teste novo + imports necessários, nenhum teste existente modificado)
- `docs/implementation/reports/INTEGRATIONS-MODEL-FK-REPAIR-02-ALINHAMENTO-TENANT-METADATA.md` (este relatório, novo)

Nenhum outro arquivo tocado. `Tenant`, `Base`, `search_path`, migrations, constraints físicas, `ondelete`, tipos UUID, índices, unique constraints, RLS, services, routers, provider registry, lifecycle, readiness, Console ERP, `SankhyaConfig`, `SankhyaConnectionData`, canonical adapter e os 9 arquivos SQLite pendentes permanecem inalterados.

## 15. Testes Executados

```bash
.venv/bin/python -c "import integracoes.models"
```
→ sucesso.

```bash
.venv/bin/pytest tests/unit/integracoes/test_integrations_foundation_models.py -v
```
→ `10 passed, 1 failed` (a falha remanescente é `test_persistencia_basica_provider_credential_config_version`, causa distinta e pré-existente: o teste usa `tenant_id="tenant-1"` — string — contra uma coluna `UUID`, incompatível desde a migração varchar→uuid de `REPAIR-01B3`; não relacionado a esta correção).

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py -v
```
→ `8 passed, 14 failed` — todas as 14 falhas remanescentes citam `sankhya_config.tenant_id` (bug remanescente da seção 1, fora de escopo).

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_legacy_reconciliation.py -v
```
→ `9 failed` — causa distinta desta vez: `UniqueViolationError` em `marketplace_integracoes_pkey` (dados residuais de execuções anteriores no PostgreSQL real, que não é truncado entre execuções — risco de isolamento entre execuções já sinalizado em `INTEGRATIONS-TEST-INFRA-01`, não uma regressão desta fase nem relacionado ao bug de FK).

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_paridade_config.py -v
```
→ `2 passed, 2 failed` — as 2 falhas seguem citando `sankhya_config.tenant_id` (bug remanescente da seção 1).

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
```
→ `3 passed` (guardrail intacto, conforme exigido).

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ `78 failed, 133 passed, 25 errors` (236 testes coletados; +1 em relação à linha de base por causa do teste novo).

## 16. Comparação da Suíte

| Métrica | Antes (INTEGRATIONS-TEST-INFRA-01) | Depois (esta fase) |
|---|---|---|
| Passed | 131 | 133 (+2: 1 teste novo + 1 teste que passou a rodar sem erro de fixture) |
| Failed | 52 | 78 (+26) |
| Errors | 52 | 25 (−27) |
| Total | 235 | 236 |

A redução material de "errors" (52→25) e o aumento de "passed" confirmam que a correção restaurou a persistência dos 9 models canônicos. O aumento de "failed" reflete testes que agora avançam mais fundo (passam da fase de setup/flush e chegam à asserção real, ou a um segundo obstáculo distinto — o bug remanescente em `SankhyaConfig`, ou colisão de dados residuais no banco real) — não uma regressão introduzida por esta correção.

## 17. Riscos Remanescentes

- **Bug idêntico ainda ativo em `integracoes/sankhya/models/__init__.py`** (7 ocorrências: `SankhyaConfig`, `SankhyaSyncLog`, `SankhyaPessoa`, `SankhyaProduto`, `SankhyaNFe`, `SankhyaLancamentoFinanceiro`, `SankhyaTabela`) — fora do escopo permitido nesta fase, mas com a mesma severidade alta descrita na seção 2. Recomenda-se uma fase `INTEGRATIONS-MODEL-FK-REPAIR-03` dedicada a esses 7 models.
- Dados residuais em execuções anteriores do PostgreSQL real (`marketplace_integracoes_pkey` colidindo) indicam que os testes de persistência ainda não têm isolamento determinístico entre execuções — risco já sinalizado em `INTEGRATIONS-TEST-INFRA-01`, ainda não tratado.
- Os 9 arquivos com engines SQLite locais (Frente B de `INTEGRATIONS-TEST-INFRA-01`) continuam pendentes de conversão.

## 18. Impacto em Produção

**Escalação recomendada, alta prioridade**: se `SankhyaSyncService.criar_config` (ou qualquer outro fluxo que faça flush de `SankhyaConfig`/`SankhyaSyncLog`/`SankhyaPessoa`/`SankhyaProduto`/`SankhyaNFe`/`SankhyaLancamentoFinanceiro`/`SankhyaTabela`) é exercido em produção hoje, é provável que também falhe com `NoReferencedTableError`, pela mesma causa raiz agora comprovada nesta fase para os models canônicos. Esta fase corrigiu apenas o lado canônico; o lado legado Sankhya permanece com o bug ativo e deve ser verificado/corrigido com urgência, independentemente da sequência do programa `ERP-DATA-HYGIENE`.

## 19. Próxima Etapa

Antes de `INTEGRATIONS-TEST-INFRA-02` (convergência dos 9 arquivos SQLite restantes) ou de `ERP-DATA-HYGIENE-01E1`, recomenda-se abrir com prioridade:

`INTEGRATIONS-MODEL-FK-REPAIR-03` — aplicar a mesma correção (`ForeignKey("farms.tenants.id", ...)` → `ForeignKey("tenants.id", ...)`) nas 7 ocorrências de `integracoes/sankhya/models/__init__.py`, com a mesma disciplina de auditoria/reprodução/validação usada aqui. Somente depois disso o fluxo completo de `criar_config` (legado + canônico) poderá ser validado de ponta a ponta, e a conversão dos 9 arquivos SQLite remanescentes fará sentido sem reproduzir os mesmos falsos-negativos já vistos duas vezes nesta investigação.

## 20. Veredicto

`GO COM RESSALVAS — METADATA CORRIGIDO, FLUXOS PARCIALMENTE VALIDADOS`

A correção da FK de tenant em `integracoes/models.py` foi comprovada: a chave real de `Tenant` no metadata foi confirmada, a causa foi reproduzida antes da correção, a FK passou a resolver para `Tenant.__table__`, os 9 models canônicos deixaram de gerar `NoReferencedTableError` e tiveram `flush()` real validado no PostgreSQL oficial, nenhuma migration foi necessária, nenhum diff físico inesperado foi encontrado, o guardrail da 01D permanece `3 passed`, e a suíte apresentou redução material de erros (52→25). Nenhum código fora do escopo autorizado foi alterado. O fluxo `criar_config` **não pôde ser validado de ponta a ponta** porque `SankhyaConfig` carrega o mesmo bug, fora do escopo permitido nesta fase — daí as ressalvas. `ruff` e `git diff --check` aprovados; banco de teste íntegro após rollback em todas as reproduções.
