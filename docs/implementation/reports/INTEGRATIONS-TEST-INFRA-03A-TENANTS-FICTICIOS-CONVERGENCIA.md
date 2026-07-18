# INTEGRATIONS-TEST-INFRA-03A — Convergência dos Arquivos com Tenants Fictícios

## 1. Resumo executivo

Convergidos os 6 arquivos de `tests/unit/integracoes/` identificados em `INTEGRATIONS-TEST-INFRA-02` como usando tenants fictícios/inexistentes (`"tenant-legado"`, `"tenant-1"`, `uuid.uuid4()` nunca persistido, etc.), eliminando IDs e slugs fixos, e consolidando o helper compartilhado `criar_tenant_real` em `tests/unit/integracoes/conftest.py`. RLS preservada em todos os casos. Durante a execução, duas fases de reparo de produção foram necessárias e executadas sob autorização explícita e escopo isolado: `SANKHYA-SCHEMA-REPAIR-01` (RLS/tenant UUID em `canonical_adapter.py`) e `SANKHYA-SCHEMA-REPAIR-02` (datetime naive/aware em `sync_service.py`). Nenhuma alteração de produção foi feita fora dessas duas fases dedicadas.

## 2. Helper compartilhado

`tests/unit/integracoes/conftest.py::criar_tenant_real(session, *, nome=...)`: insere um tenant real em `tenants` (UUID novo por chamada), ativa `SET app.current_tenant_id`, retorna o `tenant_id` como `str`. Usado em todos os 6 arquivos desta fase.

## 3. Arquivos convergidos

| Arquivo | Antes | Depois | Observações |
|---|---|---|---|
| `test_sankhya_legacy_reconciliation.py` | 9 falhando (tenant fictício) | **9 passed** | Também corrigido: `MarketplaceIntegracao.id=2` fixo → auto-increment; `SankhyaConfig.id=1` fixo → helper `_next_sankhya_config_id` (contorno de `max(id)+1`, mesmo usado em produção); `deleted_at=datetime.now(timezone.utc)` aware → naive no teste. |
| `test_sankhya_canonical_adapter.py` | 11 passed, 11 failed (tenant fictício + bug de produção) | **22 passed** | Exigiu `SANKHYA-SCHEMA-REPAIR-01` (RLS/tenant UUID). Também: `test_adapter_atualiza_schema_de_provider_existente` convertido para get-or-create do provider; `_next_sankhya_config_id` aplicado a 2 testes. |
| `test_erp_bootstrap_tardio.py` | 4 passed, 2 failed (tenant nunca persistido + bug de produção) | **6 passed** | Exigiu `SANKHYA-SCHEMA-REPAIR-02` (datetime no soft delete); `MarketplaceIntegracao.id=2` fixo removido. |
| `test_sankhya_diagnostico_timezone.py` | 3 testes com tenant fictício | **8 passed** | `MarketplaceIntegracao.id=2` fixo removido; `SankhyaSyncLog.id=501/502` fixos removidos, `config_id` passou a usar o id real retornado por `criar_config`. |
| `test_sankhya_governed_integration.py` | ~18 testes com `"tenant-1"`/`"tenant-2"` fictícios | **21 passed** | Asserção de FK obsoleta corrigida (`'ForeignKey("farms.tenants.id", ...)'` → `'ForeignKey("tenants.id", ...)'`, string já corrigida em produção por `INTEGRATIONS-MODEL-FK-REPAIR-03`, teste nunca atualizado); asserção de IDs absolutos (`first.id == 1`) trocada por relativa (`second.id == first.id + 1`), incompatível com PostgreSQL compartilhado/não resetado. |
| `test_sankhya_paridade_config.py` | 3 testes com tenant nunca persistido | **4 passed** | Conversão direta, sem bugs de produção adicionais. |

Total: **70 testes** nos 6 arquivos, todos passando, zero tenants fictícios remanescentes.

## 4. Reparos de produção associados (fases separadas, já com relatório próprio)

- `SANKHYA-SCHEMA-REPAIR-01-TENANT-RLS-UUID.md`: `_restore_rls_context` e `_tenant_uuid` em `canonical_adapter.py`.
- `SANKHYA-SCHEMA-REPAIR-02-SOFT-DELETE-TIMEZONE.md`: `_soft_delete_canonical_runtime` em `sync_service.py`.

Ambos seguiram o mesmo padrão das três fases `OPENWEATHER-SCHEMA-REPAIR-01/02/03`: descoberta durante a convergência de testes, pausa, autorização explícita do usuário, correção mínima e isolada, relatório dedicado.

## 5. Débitos conhecidos, não corrigidos nesta fase

- `sankhya_config.id` sem sequence/default no banco — contornado nos testes replicando o mesmo padrão `max(id)+1` já usado em produção (`SankhyaSyncService._next_config_id`); não corrigido estruturalmente (fora de escopo, já registrado em fases anteriores).

## 6. Validação da suíte completa

```bash
.venv/bin/pytest tests/unit/integracoes/ -v
```

Resultado: **214 passed, 16 failed, 13 errors** (232.77s). Todas as falhas e erros pertencem exclusivamente aos 4 arquivos ainda fora de escopo, pendentes de `INTEGRATIONS-TEST-INFRA-03B`:

- `test_sankhya_external_association_governance_router.py` — 4 falhas.
- `test_sankhya_gateway_test_connection.py` — 2 falhas.
- `test_sankhya_external_association_p0.py` — 13 erros (arquivo de maior risco, stubs SQLite incompletos).
- `test_erp_association_validation.py` — não apareceu na lista de falhas desta execução.

Nenhuma falha/erro nos 6 arquivos desta fase, nem regressão nos arquivos já convergidos em fases anteriores (`test_openweather_domain.py`, `test_erp_readiness_service.py`, `test_sankhya_architecture.py`, `test_sankhya_models_tenant_fk.py`, `test_integrations_foundation_models.py`, `test_integrations_operational_models.py`, `test_external_record_association_service.py`).

## 7. Isolamento determinístico

Não executado neste ciclo: dupla execução consecutiva + ordem invertida da suíte completa (item formal de `INTEGRATIONS-TEST-INFRA-03C`). A execução única confirma ausência de colisão entre os 6 arquivos convergidos nesta fase e o restante da suíte já convergida.

## 8. Arquivos alterados nesta fase

Testes: `test_sankhya_legacy_reconciliation.py`, `test_sankhya_canonical_adapter.py`, `test_erp_bootstrap_tardio.py`, `test_sankhya_diagnostico_timezone.py`, `test_sankhya_governed_integration.py`, `test_sankhya_paridade_config.py`, `conftest.py` (novo helper).

Produção (via fases dedicadas, não diretamente nesta): `integracoes/sankhya/services/canonical_adapter.py`, `integracoes/sankhya/services/sync_service.py`.

## 9. Próxima etapa

`INTEGRATIONS-TEST-INFRA-03B` — eliminar as 4 engines SQLite legadas restantes (`test_sankhya_external_association_p0.py`, `test_sankhya_external_association_governance_router.py`, `test_erp_association_validation.py`, `test_sankhya_gateway_test_connection.py`). Aguarda instrução explícita do usuário para início, dado o risco elevado já sinalizado em `test_sankhya_external_association_p0.py` (replica ~20 models de produção com stubs incompletos).

## 10. Veredicto

**GO — 03A CONCLUÍDA, ZERO TENANTS FICTÍCIOS NOS 6 ARQUIVOS DO ESCOPO**

70/70 testes passando nos 6 arquivos convergidos, sem regressão em nenhum arquivo já convergido em fases anteriores. Os únicos 16 failed + 13 errors da suíte completa pertencem integralmente ao escopo ainda não iniciado de `03B`.
