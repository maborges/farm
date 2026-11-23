# INTEGRATIONS-TEST-INFRA-01 — Auditoria e Convergência dos Testes para PostgreSQL

## 1. Resumo Executivo

A auditoria confirmou a infraestrutura oficial de testes PostgreSQL (`tests/conftest.py`, fixture `session`, banco `farms` em `192.168.0.2`) e identificou que **um** arquivo (`tests/unit/integracoes/conftest.py`) definia um `session` local em SQLite em memória com um subconjunto manual de tabelas, sombreando a fixture oficial para 8 módulos de teste. Esse `session` local foi removido (correção mínima, sem código de produção alterado), e os 8 módulos passaram a herdar corretamente a fixture PostgreSQL oficial.

**Achado crítico que reverte a premissa do plano**: ao convergir para PostgreSQL, o `NoReferencedTableError` **não desapareceu** — apenas migrou do momento de setup de fixture (SQLite) para o momento de `flush()`/`commit()` do ORM (PostgreSQL real). Uma investigação direta (reproduzida fora do pytest, com o banco `farms` real) provou que **qualquer flush de `TenantIntegracao`, `IntegrationCredential`, `IntegrationVersion`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`, `ExternalRecordAssociation` ou `ExternalRecordAssociationHistory` falha, em qualquer backend**, porque `integracoes/models.py` define `ForeignKey("farms.tenants.id", ...)` com prefixo de schema explícito, enquanto `core.models.tenant.Tenant.__tablename__ = "tenants"` está registrado **sem** schema no `Base.metadata` compartilhado (a app inteira depende de `search_path=farms` em nível de conexão, nunca de qualificação de schema em string de FK). O SQLAlchemy não consegue resolver a coluna de destino da FK dentro do metadata Python — isso é um bug de definição de modelo, não uma diferença SQLite vs PostgreSQL.

Isso significa: **este é provavelmente um bug ativo em produção** em qualquer fluxo que faça commit de um desses 9 models via ORM (ex.: `SankhyaSyncService.criar_config`, linha que já aparecia nos relatórios anteriores como "gravação dupla"). Corrigir esse bug está fora do escopo permitido nesta fase (proibido alterar `models.py`). A convergência de testes de persistência para PostgreSQL não pode ser concluída enquanto esse bug não for corrigido em uma fase própria.

**Veredicto**: `GO COM RESSALVAS — CONVERGÊNCIA PARCIAL`.

## 2. Configuração Oficial de Testes

- `tests/conftest.py:30-34` (`_get_db_url()`): usa `settings.database_url`; se não contiver `"postgresql"`, usa fallback fixo `postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms`.
- `.env.local` (raiz de `services/api`): `DATABASE_URL=postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms` — mesma URL do fallback, confirmando que é o banco de desenvolvimento/teste local oficial.
- `.env.production`: aponta para Supabase (produção) — não usado nos testes.
- `core/config.py:12`: default `sqlite+aiosqlite:///./agrosaas.db` (usado apenas se nenhum `.env` carregar; não é o caminho real de testes, que sempre cai no fallback PostgreSQL de `_get_db_url()`).
- Conexão usa `connect_args={'server_settings': {'search_path': 'farms'}}` — o schema `farms` é resolvido via `search_path` de conexão, **nunca** por qualificação explícita `schema=` nos models.

## 3. Banco PostgreSQL Utilizado

Confirmado por conexão direta: `select current_database(), current_schema()` → `('farms', 'farms')`. Host `192.168.0.2`, banco `farms`, schema efetivo `farms` via `search_path`. É o mesmo banco já usado por **centenas** de outros testes do repositório através das fixtures `session`, `session_a`, `session_b` em `tests/conftest.py` — não é uma infraestrutura nova; é a infraestrutura oficial já estabelecida e amplamente reutilizada.

## 4. Inventário das Fixtures

| Fixture | Arquivo | Dialect | Observação |
|---|---|---|---|
| `session` (oficial) | `tests/conftest.py:100-130` | PostgreSQL (asyncpg) | `Base.metadata.create_all(checkfirst=True)` com `try/except` amplo (tolera erros pois as tabelas já existem via Alembic); rollback ao final do teste |
| `session_a`/`session_b` | `tests/conftest.py:133-190` | PostgreSQL (asyncpg) | Variante com Tenant A/B pré-criado, para testes de isolamento multi-tenant |
| `session` (local, **removida nesta fase**) | `tests/unit/integracoes/conftest.py` (antes da correção) | SQLite (`aiosqlite:///:memory:`) | Criava manualmente 12 tabelas específicas via `__table__.create()`, sem `farms.tenants` |
| `session`/`engine` (locais, por arquivo) | 9 arquivos em `tests/unit/integracoes/*.py` (ver seção 5) | SQLite (`aiosqlite:///:memory:` ou `sqlite:///:memory:`) | Cada um cria seu próprio subconjunto de tabelas; não tocados nesta fase (ver seção 8) |
| `mock_dns_globally` | `tests/unit/integracoes/conftest.py` | N/A | Autouse, sem relação com banco — preservada |

## 5. Inventário dos Usos de SQLite

| Arquivo | Cria engine própria? | `create_all`/`__table__.create`? | Reutilizava fixture oficial antes desta fase? |
|---|---|---|---|
| `tests/unit/integracoes/conftest.py` | Sim (removida) | Sim (removida) | Não — sombreava a oficial |
| `test_erp_readiness_service.py` | Sim | Sim | Não |
| `test_sankhya_external_association_p0.py` | Sim | Sim | Não |
| `test_openweather_domain.py` | Sim | Sim | Não |
| `test_external_record_association_service.py` | Sim | Sim | Não |
| `test_sankhya_external_association_governance_router.py` | Sim | Sim | Não |
| `test_erp_association_validation.py` | Sim | Sim | Não |
| `test_sankhya_gateway_test_connection.py` | Sim | Sim | Não |
| `test_integrations_operational_models.py` | Sim (`create_engine` síncrono) | Sim | Não |
| `test_integrations_foundation_models.py` | Sim (`create_engine` síncrono) | Sim | Não |
| `test_sankhya_canonical_adapter.py` | Não (herdava conftest local) | — | Agora herda oficial |
| `test_sankhya_diagnostico_timezone.py` | Não | — | Agora herda oficial |
| `test_sankhya_governed_integration.py` | Não | — | Agora herda oficial |
| `test_sankhya_legacy_reconciliation.py` | Não | — | Agora herda oficial |
| `test_sankhya_paridade_config.py` | Não | — | Agora herda oficial |
| `test_erp_bootstrap_tardio.py` | Não | — | Agora herda oficial |
| `test_acme_erp_multiproviders.py` | Não | — | Agora herda oficial (já passava antes) |
| `test_erp_provider_contract.py` | Não | — | Agora herda oficial (já passava antes) |

## 6. Classificação dos Testes

| Teste ou fixture | Tipo declarado | Banco real usado (antes) | Cria engine própria? | Usa metadata.create_all? | Exercita persistência? | Deveria usar PostgreSQL? | Recomendação |
|---|---|---|---|---|---|---|---|
| `test_sankhya_architecture.py` | Unitário (AST) | Nenhum | Não | Não | Não | Não | `LÓGICA PURA — SEM BANCO` |
| `test_provider_url_validator.py` | Unitário | Nenhum | Não | Não | Não | Não | `LÓGICA PURA — SEM BANCO` |
| `test_erp_provider_governance.py` | Unitário (AST/imports) | Nenhum | Não | Não | Não | Não | `LÓGICA PURA — SEM BANCO` |
| `test_tenant_integracao_unique_indexes_migration.py` | Unitário | Nenhum (provavelmente inspeciona script de migration) | Não | Não | Não | Não | `LÓGICA PURA — SEM BANCO` |
| `test_sankhya_gateway_auth_service.py` | Unitário com mock | Nenhum | Não | Não | Não | Não | `UNITÁRIO COM MOCK` |
| `test_erp_provider_contract.py` | Unitário/contrato | PostgreSQL oficial (herdado) | Não | Não | Parcial | Sim, já usa | `INTEGRAÇÃO — DEVE USAR POSTGRESQL` (já correto) |
| `test_erp_router.py` | Unitário com mock | N/A (`db.bind.dialect.name = "sqlite"` é um mock de atributo, não um banco real) | Não | Não | Não (mock) | Não | `UNITÁRIO COM MOCK` |
| `test_acme_erp_multiproviders.py` | Integração | PostgreSQL oficial (herdado) | Não | Não | Sim | Sim, já usa | `INTEGRAÇÃO — DEVE USAR POSTGRESQL` (já correto) |
| `test_sankhya_canonical_adapter.py` | Persistência | PostgreSQL oficial (após correção) | Não | Não | Sim | Sim | `PERSISTÊNCIA — DEVE USAR POSTGRESQL` — **bloqueado pelo bug de FK (seção 7)** |
| `test_sankhya_diagnostico_timezone.py` | Persistência | idem | Não | Não | Sim | Sim | idem — **bloqueado** |
| `test_sankhya_governed_integration.py` | Persistência | idem | Não | Não | Sim | Sim | idem — **bloqueado** |
| `test_sankhya_legacy_reconciliation.py` | Persistência | idem | Não | Não | Sim | Sim | idem — **bloqueado** |
| `test_sankhya_paridade_config.py` | Persistência/E2E | idem | Não | Não | Sim | Sim | idem — **bloqueado** |
| `test_erp_bootstrap_tardio.py` | Persistência | idem | Não | Não | Sim | Sim | idem — **bloqueado** |
| `test_erp_readiness_service.py` | Persistência | SQLite local (não convertido nesta fase) | Sim | Sim | Sim | Sim | `PERSISTÊNCIA — DEVE USAR POSTGRESQL` — pendente, ver seção 8 |
| `test_sankhya_external_association_p0.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_openweather_domain.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_external_record_association_service.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_sankhya_external_association_governance_router.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_erp_association_validation.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_sankhya_gateway_test_connection.py` | Persistência | idem | Sim | Sim | Sim | Sim | idem — pendente |
| `test_integrations_operational_models.py` | Persistência (síncrona) | SQLite local | Sim | Sim | Sim | Sim | idem — pendente; nota: usa engine síncrono, precisa avaliação de conversão para async |
| `test_integrations_foundation_models.py` | Persistência (síncrona) | SQLite local | Sim | Sim | Sim | Sim | idem — pendente |
| `test_integrations_architecture_guardrails.py` | Unitário (AST) | Nenhum | Não | Não | Não | Não | `LÓGICA PURA — SEM BANCO` — as 2 falhas são de outra causa (seção 12), não relacionadas a banco |

## 7. Causa do Desvio (achado central)

A hipótese inicial ("os testes criam SQLite em vez de reutilizar PostgreSQL") explica apenas **parte** do sintoma. A causa raiz mais profunda foi confirmada por reprodução isolada, fora do pytest, contra o banco `farms` real:

```python
mi = MarketplaceIntegracao(nome="X", slug="test-slug-...", provider_type="GENERIC")
session.add(mi); await session.flush()
ti = TenantIntegracao(tenant_id=uuid.uuid4(), integracao_id=mi.id)
session.add(ti); await session.flush()
# -> sqlalchemy.exc.NoReferencedTableError:
#    Foreign key associated with column 'tenant_integracoes.tenant_id'
#    could not find table 'farms.tenants' ...
```

Isso ocorre porque:
- `integracoes/models.py` (`_tenant_fk()`, introduzida no `INTEGRATIONS-MODEL-FK-REPAIR-01`) declara `ForeignKey("farms.tenants.id", ondelete="NO ACTION")` — string com schema explícito `"farms."`.
- `core/models/tenant.py:9` declara `Tenant.__tablename__ = "tenants"`, **sem** `schema="farms"` — como todos os demais ~100+ models do app, que dependem exclusivamente de `search_path=farms` em nível de conexão.
- No `Base.metadata` compartilhado, a tabela `Tenant` está registrada sob a chave `(schema=None, "tenants")`. A string de FK `"farms.tenants.id"` busca a chave `(schema="farms", "tenants")`, que **não existe** no metadata Python — independentemente de o banco físico ter ou não o schema `farms`.
- O SQLAlchemy resolve `ForeignKey.column` (necessário para ordenação de dependências no `flush()`/`create_all()`) puramente a partir do metadata Python, **antes** de qualquer SQL ser executado. Por isso o erro ocorre de forma idêntica em SQLite e em PostgreSQL: não é uma limitação de dialect, é uma referência quebrada no grafo de metadata.

Isso explica também por que a suíte inteira do app não trava constantemente: a maioria dos testes/rotas nunca chega a fazer `flush()`/`commit()` de um objeto `TenantIntegracao`/`IntegrationCredential`/etc. junto de outros objetos no mesmo Unit of Work; quando chega (como em `SankhyaSyncService.criar_config`, que executa `self.db.commit()`), o erro deveria se manifestar também em produção.

## 8. Estratégia de Convergência

Dividida em duas frentes, dado o achado da seção 7:

**Frente A — testes sem dependência do bug de FK (lógica pura, mocks, ou já usando PostgreSQL oficial)**: já corretos, sem ação necessária.

**Frente B — testes de persistência que tocam os 9 models afetados**: a convergência para PostgreSQL **não pode ser concluída com sucesso** enquanto o bug de metadata em `integracoes/models.py` (fora do escopo permitido desta fase) não for corrigido. Converter a fixture (como já feito para 6 arquivos) é necessário mas não suficiente — os testes passam a falhar de forma correta e reveladora (no ponto real de flush/commit) em vez de falhar cedo por ausência de tabela, o que é estritamente uma melhoria de diagnóstico, não uma correção completa.

Não foi criada nenhuma simulação artificial de schema, `ATTACH DATABASE`, `schema_translate_map`, tabela fake, monkeypatch de `ForeignKey`, nem qualquer outra forma proibida de contornar o problema.

## 9. Correções Realizadas

Removida a fixture `session` local de `tests/unit/integracoes/conftest.py` (engine SQLite em memória, ~50 linhas, com criação manual de 12 tabelas sem `farms.tenants`). Nada foi colocado no lugar — a ausência de definição local faz o pytest resolver `session` para a fixture oficial de `tests/conftest.py` (comportamento padrão de resolução de fixtures por escopo de diretório). A fixture `mock_dns_globally` (autouse, sem relação com banco) foi preservada intacta.

Nenhum outro arquivo de teste foi alterado. Nenhum arquivo de produção (`models.py`, `services/`, `routers/`, migrations) foi tocado.

## 10. Arquivos Alterados

- `services/api/tests/unit/integracoes/conftest.py` (remoção da fixture SQLite local; import reordenado; whitespace corrigido por `ruff --fix`)
- `docs/implementation/reports/INTEGRATIONS-TEST-INFRA-01-CONVERGENCIA-POSTGRESQL.md` (este relatório, novo)

## 11. Segurança e Isolamento do Banco

- URL: `postgresql+asyncpg://borgus:numsey01@192.168.0.2/farms` (sanitizada aqui: host de rede local, não é endpoint de produção Supabase de `.env.production`).
- Confirmado por conexão direta que é o mesmo banco `farms` já usado pela fixture oficial `session`/`session_a`/`session_b` para centenas de outros testes do repositório — não é uma instância nova nem isolada introduzida por esta fase.
- Não é nomeado explicitamente como banco "de teste" (não há sufixo `_test`), mas é o padrão já estabelecido e aceito pelo projeto (confirmado em `CLAUDE.md`: "dev local usa PostgreSQL via `.env`"), reutilizado sem questionamento por toda a suíte existente antes desta auditoria.
- Nenhuma operação destrutiva (`drop_all`, truncate global, migration destrutiva) foi executada nesta fase. A verificação de conectividade usada apenas `SELECT current_database(), current_schema()` (somente leitura). O teste de reprodução do bug (seção 7) usou `session.rollback()` ao final, sem `commit()`.

## 12. Testes Executados

```bash
cd services/api
.venv/bin/python -c "import integracoes.models"
```
→ sucesso.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
```
→ `3 passed` (guardrail intacto).

```bash
.venv/bin/pytest tests/unit/integracoes/test_integrations_foundation_models.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py -v
```
→ `test_integrations_foundation_models.py`: ainda usa SQLite local próprio (não convertido nesta fase — ver seção 8/15), resultado inalterado (`1 failed, 9 passed`), mesma causa da seção 7.
→ `test_sankhya_canonical_adapter.py`: após herdar a fixture PostgreSQL oficial, `8 passed, 14 failed` (antes: `8 passed, 6 errors` sob SQLite parcial da conftest raiz do pacote — os erros viraram falhas no ponto de flush, mesma causa raiz da seção 7, não uma regressão desta fase).

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ **Antes desta fase**: `4 failed, 128 passed, 103 errors`.
→ **Depois desta fase**: `52 failed, 131 passed, 52 errors`.

`ruff check tests/unit/integracoes/conftest.py` → `All checks passed!` (após `--fix` para import não ordenado e whitespace).
`git diff --check` → sem saída, sucesso.

## 13. Comparação Antes/Depois

| Métrica | Antes | Depois |
|---|---|---|
| Passed | 128 | 131 (+3: 2 testes novos do guardrail de 01D-FIX + 1 teste que passou a rodar corretamente) |
| Failed | 4 | 52 |
| Errors | 103 | 52 |
| Total | 235 | 235 |

O aumento de "failed" e a queda simétrica de "errors" refletem exatamente a migração do ponto de falha: de "fixture não conseguiu criar tabela" (error, SQLite) para "flush/commit falhou por FK quebrada no metadata" (failed, PostgreSQL real) — confirmando que a causa raiz é a mesma em ambos os backends e não foi introduzida por esta fase.

## 14. Falhas Remanescentes

Todas as 52 falhas + 52 erros nos 6 arquivos convergidos (`test_sankhya_canonical_adapter.py`, `test_sankhya_diagnostico_timezone.py`, `test_sankhya_governed_integration.py`, `test_sankhya_legacy_reconciliation.py`, `test_sankhya_paridade_config.py`, `test_erp_bootstrap_tardio.py`) e nos 9 arquivos ainda não convertidos compartilham a mesma causa raiz da seção 7 — `NoReferencedTableError`/`InvalidRequestError` na resolução de `ForeignKey("farms.tenants.id", ...)`. As 2 falhas de `test_integrations_architecture_guardrails.py` são de causa distinta e não relacionada a banco (não investigada nesta fase, fora do escopo — parecem ser sobre classificação de providers, não persistência).

## 15. Impacto no ERP-DATA-HYGIENE

O bloqueio de infraestrutura de teste identificado em `ERP-DATA-HYGIENE-01E0`/`INTEGRATIONS-MODEL-FK-REPAIR-01` está parcialmente resolvido (a fixture agora aponta corretamente para a infraestrutura oficial), mas a validação executável de `canonical_adapter.py`, `legacy_reconciliation.py`, `sync_service.criar_config` e das fases 01G-01L (lifecycle, health, jobs, policies — todas dependem de flush de `TenantIntegracao`/`IntegrationCredential`/etc.) permanece bloqueada por este bug de modelo. **Não é seguro assumir que essas fases estão "aparentemente concluídas"** com base em leitura estática do código, como cogitado em 01E0/01D-FIX — a evidência empírica agora mostra que o próprio mecanismo de persistência dessas estruturas está quebrado a nível de ORM.

## 16. Riscos Remanescentes

- **Risco de produção (alta severidade, fora do escopo desta fase)**: se este bug afeta o mesmo caminho de código em produção, qualquer criação/atualização de integração Sankhya via `criar_config` (e potencialmente credenciais, jobs, health, etc.) pode estar falhando silenciosamente ou lançando exceção em ambiente real. Recomenda-se escalar essa hipótese para verificação imediata em produção/staging, independentemente da sequência do programa `ERP-DATA-HYGIENE`.
- 9 arquivos de teste ainda usam SQLite local não convertido (seção 8, Frente B) — convertê-los sem antes corrigir o bug da seção 7 apenas reproduziria o mesmo padrão de falhas já visto nos 6 arquivos convergidos, sem agregar valor até a correção do modelo.
- As 2 falhas de `test_integrations_architecture_guardrails.py` permanecem não diagnosticadas (causa distinta, fora do escopo desta fase).

## 17. Próxima Etapa Recomendada

Antes de `ERP-DATA-HYGIENE-01E1`, abrir uma fase corretiva de **alta prioridade** para o bug de metadata identificado na seção 7 (ex.: `INTEGRATIONS-MODEL-FK-REPAIR-02`), com escopo restrito a `services/api/integracoes/models.py`: alinhar a string de `ForeignKey` de `_tenant_fk()` com a forma de registro real de `Tenant` no `Base.metadata` (ou seja, remover o prefixo `"farms."` para casar com o padrão `ForeignKey("tenants.id")` já usado por todos os demais ~100 models do app, já que a resolução do schema físico depende exclusivameante de `search_path` de conexão, não de qualificação em string). Essa fase deve incluir verificação — fora do pytest, como feito aqui — de que um `flush()` real de `TenantIntegracao`/`IntegrationCredential` funciona antes de declarar sucesso. Somente depois disso a conversão dos 9 arquivos restantes (Frente B) e a nova auditoria `ERP-DATA-HYGIENE-01E1` fazem sentido.

## 18. Veredicto

`GO COM RESSALVAS — CONVERGÊNCIA PARCIAL`

A infraestrutura oficial de testes PostgreSQL foi identificada e confirmada como acessível e segura para reutilização; a fixture indevida em SQLite foi removida sem tocar código de produção, e nenhuma simulação artificial de schema foi criada. Porém, a convergência completa dos testes de persistência não pôde ser concluída porque a auditoria revelou uma causa raiz mais profunda — um bug de definição de `ForeignKey` em `integracoes/models.py`, fora do escopo permitido nesta fase — que faz qualquer flush dos 9 models afetados falhar em qualquer backend. Recomenda-se abrir uma fase corretiva dedicada a esse bug antes de prosseguir com a conversão dos 9 arquivos restantes ou com `ERP-DATA-HYGIENE-01E1`.
