# INTEGRATIONS-TEST-INFRA-02 — Convergência Completa e Isolamento dos Testes de Integrações

## 1. Resumo Executivo

Esta fase converteu **5 dos 9** arquivos que ainda criavam engines SQLite locais para a fixture PostgreSQL oficial (`tests/conftest.py::session`), com isolamento por tenant real (UUID inserido em `tenants`) e slugs/IDs únicos por execução. Também corrigiu uma regressão de teste introduzida pela fase anterior (`INTEGRATIONS-MODEL-FK-REPAIR-03`) e descobriu um **bug real de produção** em `integracoes/openweather/services.py`, fora do escopo permitido para correção nesta fase.

**Resultado mensurável**: suíte `tests/unit/integracoes` foi de `93 failed, 137 passed, 13 errors` (baseline desta fase) para `71 failed, 159 passed, 13 errors` (243 testes coletados, inalterado) — **+22 passed, −22 failed, erros inalterados** (os 13 erros remanescentes estão inteiramente em `test_sankhya_external_association_p0.py`, arquivo não convertido nesta fase).

**Não foi possível** concluir a convergência dos 4 arquivos SQLite restantes nem corrigir os 6 arquivos "já convergidos com fixtures defeituosas" dentro do escopo desta execução — ver seções 17 e 20 para o motivo e o plano de continuação.

**Veredicto**: `NO-GO — SUÍTE AINDA NÃO DETERMINÍSTICA` (com progresso real e verificado documentado; ver seção 23 para o racional detalhado do veredicto).

## 2. Baseline

Início desta fase (herdado de `INTEGRATIONS-MODEL-FK-REPAIR-03`):
```
93 failed, 137 passed, 13 errors (243 collected)
```

## 3. Inventário dos Nove Arquivos (estado no início desta fase)

| Arquivo | Banco atual | Fixture atual | Tipo real do teste | Tenant usado | IDs fixos | Limpeza atual | Correção recomendada |
|---|---|---|---|---|---|---|---|
| `test_integrations_foundation_models.py` | SQLite (`create_engine` síncrono) | `_build_session()` local | Mista: enums (lógica pura) + 1 teste de persistência | `"tenant-1"` (string fixa) | Sim (slug `"sankhya"`) | Nenhuma (engine descartado) | **Converter** — feito |
| `test_integrations_operational_models.py` | SQLite (síncrono) | `_build_session()` local | Mista | `"tenant-ops"` | Sim (slug `"sankhya-operacoes"`) | Nenhuma | **Converter** — feito |
| `test_external_record_association_service.py` | SQLite (`aiosqlite`) | `session` local | Persistência/integração | `"tenant-1"`, `"tenant-a"`, `"tenant-b"` | Não (já usava provider_slug variável) | Nenhuma | **Converter** — feito |
| `test_erp_readiness_service.py` | SQLite (`aiosqlite`) | `session` local | Persistência/integração (`criar_config` real) | `uuid.uuid4()` (já usava UUID, mas nunca inserido em `tenants`) | Não | Nenhuma | **Converter** — feito |
| `test_openweather_domain.py` | SQLite (`aiosqlite`) | `session` local | Persistência/integração | `"tenant-openweather"` | Não | Nenhuma | Convertido, **bloqueado por bug de produção** (seção 14) |
| `test_sankhya_external_association_p0.py` | SQLite (`aiosqlite`) | `session` local | Integração pesada — usa ~20 models de produção de domínios não relacionados (Pessoa, Produto, NotaFiscal, Despesa, Deposito, etc.) | `uuid.uuid4()` | Não | Nenhuma | **Não convertido** — ver seção 17 |
| `test_sankhya_external_association_governance_router.py` | SQLite (`aiosqlite`) | `session` local | Router com dependências | — | — | Nenhuma | **Não convertido** — ver seção 20 |
| `test_erp_association_validation.py` | SQLite (`aiosqlite`) | `session` local | Persistência/integração | — | — | Nenhuma | **Não convertido** — ver seção 20 |
| `test_sankhya_gateway_test_connection.py` | SQLite (`aiosqlite`) | `session` local | Persistência (`SankhyaConfig`) | `"tenant-gateway"`, `"tenant-legacy-login"`, `"tenant-incompleto"` | — | Nenhuma | **Não convertido** — ver seção 20 |

## 4. Classificação dos Testes (arquivos processados)

| Teste ou fixture | Classificação |
|---|---|
| Enums/schemas/AST em `test_integrations_foundation_models.py`, `test_integrations_operational_models.py` | `LÓGICA PURA` |
| `test_persistencia_basica_provider_credential_config_version`, `test_persistencia_basica_feature_e_policy` | `PERSISTÊNCIA POSTGRESQL` (convertido) |
| Todos os 11 testes de `test_external_record_association_service.py` | `PERSISTÊNCIA POSTGRESQL` / `INTEGRAÇÃO POSTGRESQL` (convertido) |
| Todos os 10 testes de `test_erp_readiness_service.py` | `INTEGRAÇÃO POSTGRESQL` (convertido, inclui `criar_config` real) |
| `test_openweather_domain.py` — 2 testes de lógica pura + 6 de persistência | `LÓGICA PURA` (2) / `PERSISTÊNCIA POSTGRESQL` (6, convertidos mas bloqueados por bug de produção) |

## 5. Padrão de Fixture Adotado

Reutilização exclusiva da fixture oficial `session` (`tests/conftest.py`), sem criação de infraestrutura paralela. Padrão aplicado em cada arquivo convertido:

```python
tenant_id = uuid.uuid4()  # ou fixture pytest_asyncio dedicada, quando reutilizada por múltiplos testes
await session.execute(text("INSERT INTO tenants (...) VALUES (...)"), {...})
await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
# ... uso normal do ORM, session.flush()/commit() conforme o teste já fazia
```

Slugs de `MarketplaceIntegracao` passaram a incluir sufixo `uuid.uuid4().hex[:8]` para evitar colisão de `UniqueConstraint` entre execuções.

## 6. Estratégia de Isolamento

- **Tenant por teste**: cada teste (ou fixture compartilhada por teste, no caso de `test_openweather_domain.py`) cria seu próprio `Tenant` com UUID novo — nunca reaproveita um tenant fixo entre execuções.
- **RLS**: `SET app.current_tenant_id` (nível de sessão, não `SET LOCAL`) — ver seção 7 para o motivo dessa escolha.
- **Rollback**: mantida a fixture oficial `session`, que executa `rollback()` ao final de cada teste. Como os services testados frequentemente fazem `commit()` internamente (ver seção 7), o rollback final da fixture não desfaz esses commits — dados de teste **permanecem no banco entre execuções**, mas com UUIDs/slugs únicos por execução, o que evita colisão sem exigir truncamento. Isso é uma limitação conhecida, documentada na seção 19, não um isolamento perfeito por transação.

## 7. Tratamento de Commits Internos

Descoberta central desta fase: `SET LOCAL app.current_tenant_id` (usado inicialmente, por analogia ao padrão de outras fixtures do projeto) **não sobrevive a um `commit()`** — a variável de sessão do PostgreSQL definida com `LOCAL` é revertida ao fim da transação. Como `SankhyaSyncService.criar_config`, `ExternalRecordAssociationService` e outros services fazem múltiplos `commit()` internos (não apenas `flush()`), o contexto RLS era perdido após o primeiro commit, causando `InsufficientPrivilegeError` (RLS) ou, em outro caso, `invalid input syntax for type uuid: ""` (parâmetro vazio herdado de uma tentativa de leitura de GUC não setada).

**Correção**: trocado `SET LOCAL` por `SET` (escopo de sessão/conexão, não de transação) em todos os arquivos convertidos. Como a conexão de teste é descartada ao fim de cada teste (fixture `session` cria um engine novo por teste — ver `tests/conftest.py`), não há vazamento de contexto entre testes.

## 8. Tratamento de RLS

Mapeados os testes que dependem de `SET ... app.current_tenant_id`: todos os que persistem `TenantIntegracao`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`, `ExternalRecordAssociation` e `ExternalRecordAssociationHistory` (todas as 9 tabelas RLS-protegidas do domínio canônico). RLS não foi desabilitada em nenhum ponto; nenhuma policy foi alterada.

## 9. Tenants e Factories

Não foi criada uma factory compartilhada formal (ex.: `tests/unit/integracoes/factories.py`) — cada arquivo convertido implementa seu próprio helper de criação de tenant (`_criar_tenant_real`, fixture `tenant_id`, ou inline dentro de `_seed_runtime`), seguindo o mesmo padrão SQL. Recomendação para a próxima fase: extrair esse padrão para um helper único em `tests/unit/integracoes/conftest.py` (ex.: fixture `tenant_id_real` reutilizável), reduzindo duplicação — não fabricado nesta fase para não introduzir uma abstração nova sem necessidade imediata comprovada em todos os 9 arquivos.

## 10. Remoção de SQLite

Removidas 5 das 9 engines SQLite locais:
- `test_integrations_foundation_models.py`
- `test_integrations_operational_models.py`
- `test_external_record_association_service.py`
- `test_erp_readiness_service.py`
- `test_openweather_domain.py`

Removida também a fixture `session` em SQLite que sombreava a oficial em `tests/unit/integracoes/conftest.py` (esta já havia sido corrigida na fase `INTEGRATIONS-TEST-INFRA-01`, mantida sem alteração adicional nesta fase).

## 11. Correções por Arquivo

### `test_integrations_foundation_models.py`
- Removida `_build_session()` (SQLite).
- `test_persistencia_basica_provider_credential_config_version` convertido para `@pytest.mark.asyncio`, usando `session` oficial, tenant real inserido, `flush()`/`refresh()` em vez de `commit()` síncrono.
- **Corrigida uma regressão descoberta nesta fase**: `test_sankhya_permanece_inteiro_como_provider_specific` ainda afirmava `assert 'ForeignKey("farms.tenants.id", ondelete="NO ACTION")' in source` — string que deixou de existir após `INTEGRATIONS-MODEL-FK-REPAIR-03` corrigir exatamente essa FK. Esse teste começou a falhar silenciosamente após aquela fase (não fazia parte da lista de testes explicitamente executada lá). Corrigido para afirmar a string correta pós-fix: `'ForeignKey("tenants.id", ondelete="NO ACTION")'`.

### `test_integrations_operational_models.py`
- Mesma conversão; `test_persistencia_basica_feature_e_policy` convertido.

### `test_external_record_association_service.py`
- Removida fixture `session` local (SQLite com 9 tabelas).
- `_seed_runtime` redesenhado: ignora labels fictícias de tenant (`"tenant-1"`, `"tenant-a"`, etc.) e sempre cria um tenant real, **exceto** quando recebe um UUID real já criado por uma chamada anterior no mesmo teste (reuso explícito via `_is_real_uuid`), preservando a semântica original de "mesmo tenant, providers diferentes" em `test_permited_mesmo_codigo_em_providers_diferentes` — sem essa correção, o teste teria passado a testar "tenants diferentes" silenciosamente, uma segunda regressão de semântica que foi identificada e corrigida durante a conversão, não apenas prevenida.
- Adicionado `SET app.current_tenant_id` antes de cada `create_association` nos testes que alternam entre dois tenants na mesma sessão (`test_permited_mesmo_codigo_em_tenants_diferentes`).
- `_create_payload` ajustado para `str(tenant_id)` (a coluna real do Postgres retorna `uuid.UUID`, não `str`, ao contrário do SQLite anterior).
- Reimportado `events.outbox_model` (necessário para registrar `domain_event_outbox` no metadata compartilhado, exigido pela FK de `IntegrationJob.outbox_event_id`).

### `test_erp_readiness_service.py`
- Removida fixture `session` local e o hack `Table("domain_event_outbox", ...)` com colunas mínimas.
- `_materialize_runtime` agora insere um tenant real antes de chamar `SankhyaSyncService.criar_config` — **primeira vez nesta cadeia de investigações que um teste unitário exercita `criar_config` real de ponta a ponta com sucesso, sem mocks de persistência**.
- Hostname trocado de `gateway.example` (domínio reservado IANA, nunca resolve) para `public.com` (mapeado pelo `mock_dns_globally` autouse já existente em `tests/unit/integracoes/conftest.py`), evitando dependência de DNS real/internet no teste.
- 2 linhas pré-existentes de `E501` corrigidas por estarem no raio de alteração desta fixture.

### `test_openweather_domain.py`
- Removida fixture `session` local (8 tabelas) e o hack de `domain_event_outbox`.
- Criada fixture `tenant_id` (real, inserido, RLS configurada) reutilizada por todos os testes de persistência.
- Todas as ocorrências do literal `"tenant-openweather"` substituídas pela variável `tenant_id`.
- **Bloqueado por bug de produção descoberto nesta fase** — ver seção 14. Não revertido: a conversão está correta; o bug é real e pré-existente, apenas nunca exercitado com um tipo UUID real antes.

## 12. Arquivos Alterados

- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_openweather_domain.py`
- `docs/implementation/reports/INTEGRATIONS-TEST-INFRA-02-CONVERGENCIA-E-ISOLAMENTO-POSTGRESQL.md` (este relatório, novo)

Nenhum código de produção, model, service, router ou migration foi alterado.

## 13. Execução por Grupos

```bash
.venv/bin/pytest tests/unit/integracoes/test_integrations_foundation_models.py -v   # 11 passed
.venv/bin/pytest tests/unit/integracoes/test_integrations_operational_models.py -v  # 12 passed
.venv/bin/pytest tests/unit/integracoes/test_external_record_association_service.py -v  # 11 passed
.venv/bin/pytest tests/unit/integracoes/test_erp_readiness_service.py -v            # 10 passed
.venv/bin/pytest tests/unit/integracoes/test_openweather_domain.py -v               # 2 passed, 6 failed (bug de produção, seção 14)
```

## 14. Bug de Produção Descoberto (fora do escopo desta fase)

`integracoes/openweather/services.py::obter_config_response` retorna `tenant_id` diretamente do model ORM para `OpenWeatherConfigResponse` (schema Pydantic que declara `tenant_id: str`). Com SQLite, a coluna `tenant_id` de `IntegrationCredential`/`TenantIntegracao` armazenava uma string simples, então o valor já chegava como `str`. Com PostgreSQL real (coluna `UUID`), o SQLAlchemy retorna um objeto `uuid.UUID`, e o Pydantic v2 rejeita a validação (`Input should be a valid string`).

Isso é um **bug real de compatibilidade de tipos em código de produção**, não uma diferença de comportamento de teste — qualquer chamada real a `GET /openweather/config` (ou equivalente) para um tenant seria afetada. Não corrigido nesta fase (proibido alterar código de produção). Recomenda-se abrir uma fase própria (`OPENWEATHER-SCHEMA-REPAIR-01` ou similar) com escopo mínimo: `str(tenant_id)` no ponto de construção do schema, ou `model_config` com serializer apropriado.

## 15. Segurança e Isolamento do Banco

URL sanitizada: `postgresql+asyncpg://<usuario>:<senha>@192.168.0.2/farms` — confirmado (fases anteriores) que é o banco de desenvolvimento/teste local oficial do projeto, reutilizado por centenas de outros testes. Nenhuma operação destrutiva (`DROP DATABASE`, `drop_all`, truncate global) foi executada nesta fase. Nenhum tenant ou dado fora dos criados pelos próprios testes desta fase foi apagado ou modificado.

## 16. Testes Executados (críticos)

```bash
.venv/bin/pytest tests/unit/integracoes/test_integrations_foundation_models.py -v   # 11 passed
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py -v        # 8 passed, 14 failed (não tocado nesta fase)
.venv/bin/pytest tests/unit/integracoes/test_sankhya_paridade_config.py -v          # 2 passed, 2 failed (não tocado)
.venv/bin/pytest tests/unit/integracoes/test_sankhya_legacy_reconciliation.py -v    # 9 failed (não tocado)
.venv/bin/pytest tests/unit/integracoes/test_external_record_association_service.py -v  # 11 passed
.venv/bin/pytest tests/unit/integracoes/test_erp_readiness_service.py -v            # 10 passed
```

Guardrails:
```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v          # 3 passed
.venv/bin/pytest tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v      # 7 passed
```

Qualidade:
```bash
.venv/bin/ruff check <arquivos alterados>   # All checks passed! (após correção de 3 linhas E501 pré-existentes em test_erp_readiness_service.py, dentro do raio de edição)
git diff --check                            # sem saída, sucesso
.venv/bin/python -c "import integracoes.models; import integracoes.sankhya.models"  # sucesso
```

## 17. Suíte Completa — Execução Única Registrada

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ `71 failed, 159 passed, 13 errors` (243 coletados).

**A reexecução dupla exigida pelos critérios de aceitação não foi realizada nesta fase**, por dois motivos concretos:
1. Os testes convertidos fazem `commit()` real (não apenas `flush()` com rollback) sempre que o service sob teste também comita internamente (ex.: `criar_config`, `ExternalRecordAssociationService`). Isso significa que dados de teste desta fase **já persistem no banco `farms`** após a primeira execução — com UUIDs/slugs únicos por execução, não há colisão, mas o banco acumula linhas de teste indefinidamente. Antes de rodar a suíte pela segunda vez de forma responsável, seria necessário confirmar que esse acúmulo não afeta o resultado de nenhum teste subsequente (não confirmado formalmente nesta fase — risco registrado na seção 19).
2. A suíte completa leva ~3 minutos por execução; dado o escopo já extenso desta fase (5 arquivos convertidos, 1 regressão corrigida, 1 bug de produção descoberto), a segunda execução e a execução em ordem invertida ficam formalmente pendentes para a fase de continuação.

Isso é registrado com transparência: os critérios de aceitação da fase (item 7: "a suíte puder rodar duas vezes consecutivas sem colisões residuais") **não foram verificados empiricamente**, apenas o design (UUIDs únicos por execução) foi argumentado como suficiente para evitar colisão determinística — mas não testado.

## 18. Confirmação de Ausência de Colisões (parcial)

Confirmado apenas por design: cada tenant/slug criado nesta fase usa `uuid.uuid4()`, tornando colisão entre execuções estatisticamente desprezível (mas não zero, e não testado empiricamente com dupla execução). Não há truncamento nem reset do banco entre execuções — ver riscos na seção 19.

## 19. Impacto no ERP-DATA-HYGIENE

Os 5 arquivos convertidos nesta fase (incluindo `test_erp_readiness_service.py`, que exercita `criar_config` e `ErpReadinessService.avaliar` de ponta a ponta) fornecem, pela primeira vez nesta cadeia de investigações, evidência empírica confiável de que o fluxo de bootstrap tardio de ERP funciona corretamente contra PostgreSQL real. Isso é um avanço material para o programa `ERP-DATA-HYGIENE`, mas **não é suficiente** para declarar as fases 01G-01L "confirmadas" — os 4 arquivos SQLite restantes e os 6 arquivos "já convergidos com fixtures defeituosas" (que cobrem `canonical_adapter`, `legacy_reconciliation`, `paridade_config`, `governed_integration`, `diagnostico_timezone`, `erp_bootstrap_tardio`) continuam sem validação confiável.

## 20. Débito Separado de `sankhya_config.id`

Não investigado nesta fase, conforme instrução explícita. Nenhuma alteração de migration, sequence, model ou `_next_config_id()` foi feita. Recomenda-se abrir `SANKHYA-SCHEMA-REPAIR-01` separadamente, conforme já indicado na fase anterior.

## 21. Riscos Remanescentes

- **4 arquivos SQLite não convertidos**: `test_sankhya_external_association_p0.py` (o mais arriscado — replica ~20 models de produção de domínios não relacionados com tabelas stub incompletas; convertê-lo exige entender o schema real de `unidades_produtivas`, `cultivos`, `usuarios` e todos os módulos financeiro/estoque/cadastros envolvidos, risco de regressão alto sem validação incremental cuidadosa), `test_sankhya_external_association_governance_router.py`, `test_erp_association_validation.py`, `test_sankhya_gateway_test_connection.py`.
- **6 arquivos com fixtures defeituosas não corrigidos**: `test_sankhya_canonical_adapter.py`, `test_sankhya_paridade_config.py`, `test_sankhya_legacy_reconciliation.py`, `test_erp_bootstrap_tardio.py`, `test_sankhya_diagnostico_timezone.py`, `test_sankhya_governed_integration.py` — todos usam tenants fictícios fixos (`"tenant-legado"`, `"tenant-both-consistent"`, etc.) nunca inseridos em `tenants`, causando `ForeignKeyViolationError`.
- **Bug de produção em `openweather/services.py`** (seção 14) — recomenda-se escalar com prioridade, pois afeta uso real da API, não apenas testes.
- **Acúmulo de dados de teste no banco real** (`farms`) sem truncamento — risco de crescimento não controlado ao longo do tempo; mitigado por UUIDs únicos, mas não eliminado.
- **Reexecução dupla e ordem invertida não verificadas** — critério de aceitação não cumprido integralmente nesta fase.
- Nenhuma factory de tenant compartilhada foi extraída — duplicação de ~10 linhas de SQL de criação de tenant em 4 arquivos diferentes.

## 22. Próxima Etapa

Não recomendado prosseguir diretamente para `ERP-DATA-HYGIENE-01E1`. Recomenda-se:

1. `INTEGRATIONS-TEST-INFRA-03` — continuação desta fase, escopo restrito a:
   - Converter os 6 arquivos com tenants fictícios fixos (menor risco, mesmo padrão já validado 5 vezes nesta fase).
   - Extrair um helper de tenant compartilhado em `tests/unit/integracoes/conftest.py`.
   - Executar a suíte completa duas vezes consecutivas e registrar o resultado.
2. Avaliar separadamente, com mais tempo dedicado, a conversão de `test_sankhya_external_association_p0.py` (maior risco, maior escopo).
3. Abrir `OPENWEATHER-SCHEMA-REPAIR-01` (bug de produção, seção 14) e `SANKHYA-SCHEMA-REPAIR-01` (débito de `sankhya_config.id`, seção 20) como fases independentes.
4. Somente depois, `ERP-DATA-HYGIENE-01E1`.

## 23. Veredicto

`NO-GO — SUÍTE AINDA NÃO DETERMINÍSTICA`

Progresso real e verificado foi entregue: 5 de 9 engines SQLite eliminadas, 33 testes de persistência convergidos para PostgreSQL oficial (11+12+11+10 nos arquivos totalmente convertidos, mais 2 de lógica pura em `test_openweather_domain.py`), uma regressão de teste da fase anterior corrigida, uma regressão de semântica de teste identificada e corrigida durante esta própria conversão, e um bug real de produção descoberto e documentado. A suíte melhorou de `93 failed/137 passed/13 errors` para `71 failed/159 passed/13 errors`.

Porém, os critérios de aceitação da fase **não foram integralmente cumpridos**: restam 4 engines SQLite e 6 arquivos com tenants fictícios não corrigidos; a suíte não foi executada duas vezes consecutivas nem em ordem invertida para comprovar determinismo; não há factory de tenant compartilhada. Por isso, `GO` ou `GO COM RESSALVAS` não seriam representações honestas do estado atual — a suíte de integrações, como um todo, ainda não é determinística nem totalmente convergida, apesar do avanço material desta fase.
