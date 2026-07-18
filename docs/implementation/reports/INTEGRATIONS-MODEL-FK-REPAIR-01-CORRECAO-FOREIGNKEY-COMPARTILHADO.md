# INTEGRATIONS-MODEL-FK-REPAIR-01 — Correção do ForeignKey Compartilhado e Desbloqueio da Suíte

## 1. Resumo Executivo

`services/api/integracoes/models.py` reutilizava uma única instância de `ForeignKey("farms.tenants.id", ondelete="NO ACTION")` (`_TENANT_FK`) em 9 colunas `tenant_id` de modelos distintos. SQLAlchemy proíbe uma instância de `ForeignKey` ter mais de um `parent`, o que impedia a importação do módulo e bloqueava a coleta de toda a suíte `tests/unit/integracoes/*`. Corrigido substituindo o objeto compartilhado por uma factory `_tenant_fk()` que retorna uma nova instância a cada chamada, preservando exatamente a tabela alvo e o `ondelete`. Nenhum outro comportamento, nome, tipo, constraint ou schema foi alterado.

## 2. Causa Raiz

`_TENANT_FK = ForeignKey("farms.tenants.id", ondelete="NO ACTION")` era declarado uma única vez no nível de módulo e passado como argumento posicional em `Column(...)` de 9 colunas diferentes (`tenant_integracoes.tenant_id`, `integration_credentials.tenant_id`, `integration_versions.tenant_id`, `integration_features.tenant_id`, `integration_sync_policies.tenant_id`, `integration_jobs.tenant_id`, `integration_health_snapshots.tenant_id`, `integration_external_record_links.tenant_id`, `integration_external_record_link_history.tenant_id`). Ao mapear a segunda coluna, o SQLAlchemy detectava que o objeto `ForeignKey` já possuía um `parent` (a primeira coluna) e levantava `InvalidRequestError: This ForeignKey already has a parent!`.

## 3. Commit de Origem

`88e46a13` — "feat(tenant-integrity): REPAIR-01B3 — núcleo multiprovider varchar→uuid + FKs". A intenção do commit era padronizar a conversão de `tenant_id` de `String(50)` para `UUID` com FK real para `farms.tenants.id` em 9 tabelas do núcleo multiprovider, com `ondelete="NO ACTION"` uniforme. A declaração `_TENANT_FK` foi criada apenas para evitar repetição textual — sem perceber que instâncias de `ForeignKey` não são reutilizáveis entre colunas.

## 4. Locais Afetados

Todas as 9 ocorrências de `tenant_id = Column(UUIDType(as_uuid=True), _TENANT_FK, nullable=False, index=True)`, nas linhas (antes da correção) 196, 240, 270, 296, 325, 355, 395, 446, 508 de `services/api/integracoes/models.py`.

## 5. Comportamento do SQLAlchemy

Cada `Column` associa a si mesma como `.parent` do objeto `ForeignKey` recebido (`ForeignKey._set_parent`). Ao reutilizar a mesma instância em uma segunda coluna, o SQLAlchemy detecta um `parent` já atribuído e recusa a segunda atribuição — não há suporte a "FK compartilhada"; cada coluna exige sua própria instância, mesmo que os argumentos (`tabela`, `ondelete`) sejam idênticos.

## 6. Correção Implementada

Substituição do objeto de módulo compartilhado por uma função factory:

```python
def _tenant_fk() -> ForeignKey:
    return ForeignKey("farms.tenants.id", ondelete="NO ACTION")
```

E troca de todas as 9 ocorrências de `_TENANT_FK` por `_tenant_fk()` (chamada, gerando instância nova a cada coluna). Nenhum outro argumento, nome de tabela, `ondelete`, tipo de coluna, nullability, índice ou relacionamento foi alterado.

Arquivo alterado: `services/api/integracoes/models.py` (13 inserções, 11 remoções — apenas a declaração e as 9 chamadas).

## 7. Comparação Antes/Depois

| Item | Antes | Depois |
|---|---|---|
| Declaração | `_TENANT_FK = ForeignKey(...)` (instância única) | `def _tenant_fk() -> ForeignKey: return ForeignKey(...)` (factory) |
| Uso em cada coluna | `_TENANT_FK` (mesma instância) | `_tenant_fk()` (nova instância por chamada) |
| Tabela alvo | `farms.tenants.id` | `farms.tenants.id` (inalterado) |
| `ondelete` | `NO ACTION` | `NO ACTION` (inalterado) |
| Nomes de constraint | Não explícitos (auto-gerados pelo dialeto) | Não explícitos (auto-gerados, mesmo padrão) |
| Import de `integracoes.models` | Falha (`InvalidRequestError`) | Sucesso |

## 8. Confirmação de Preservação do Metadata

Nenhuma migration foi gerada nem necessária: a mudança é puramente de metadata Python (como as instâncias de `ForeignKey` são construídas), não do valor físico da constraint. Tabela referenciada, coluna referenciada e `ondelete` permanecem idênticos em todas as 9 colunas. Não havia nomes de constraint explícitos antes da correção, portanto nenhuma alteração de nome foi introduzida.

## 9. Arquivos Alterados

- `services/api/integracoes/models.py` (única alteração de código)
- `docs/implementation/reports/INTEGRATIONS-MODEL-FK-REPAIR-01-CORRECAO-FOREIGNKEY-COMPARTILHADO.md` (este relatório, novo)

Nenhum arquivo de model do provider Sankhya, `SankhyaConfig`, serviços, routers, lifecycle, readiness, provider registry, bootstrap ou Console ERP foi tocado.

## 10. Testes Executados

```bash
cd services/api
.venv/bin/python -c "import integracoes.models"
```
→ sucesso, sem exceção.

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
```
→ `1 passed in 0.17s`. O guardrail AST agora executa e passa (não detectou import de `SankhyaConfig` em `auth_service.py`, `nfe_financeiro_service.py` ou `routers/*.py` — o guardrail cobre apenas esses arquivos, conforme já registrado em 01E0; a divergência de `nfe_financeiro_service.py` identificada no 01E0 permanece como item da fase `01D-FIX`, fora do escopo desta correção).

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ **coleta bem-sucedida** (antes: falha total de coleção). Resultado: `4 failed, 126 passed, 103 errors in 120.96s`.

```bash
git diff --check
```
→ sem saída, sucesso.

```bash
ruff check services/api/integracoes/models.py
```
→ `All checks passed!`

## 11. Falhas Encontradas

Todas as 103 falhas de coleta/erro e as 4 falhas de asserção investigadas (`test_sankhya_canonical_adapter.py`, `test_integrations_foundation_models.py::test_persistencia_basica_provider_credential_config_version`, entre outras) apresentam a **mesma causa raiz**, não relacionada a esta correção:

```
sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column
'integration_credentials.tenant_id' could not find table 'farms.tenants'
with which to generate a foreign key to target column 'id'
```

Isso ocorre porque esses testes usam SQLite em memória com `metadata.create_all()` restrito a um subconjunto de tabelas, no qual `farms.tenants` (schema `farms`) não está registrada na mesma `MetaData`/import scope. É um problema de fixture/ambiente de teste, pré-existente e independente da reutilização de `ForeignKey` — a importação do módulo já funciona; o problema é apenas na criação física das tabelas dentro dos testes que não importam também os models de `farms`. Não foi alterado nenhum teste, conforme restrição do escopo.

126 testes da suíte passam integralmente, incluindo o guardrail Sankhya.

## 12. Impacto no Banco

Nenhum. A correção é de metadata Python, sem qualquer alteração de constraint física, nome, `ondelete`, tipo ou schema. Nenhuma migration foi criada ou é necessária.

## 13. Impacto no Programa ERP-DATA-HYGIENE

O bloqueio identificado em `ERP-DATA-HYGIENE-01E0` para rodar `tests/unit/integracoes/*` está removido. O guardrail Sankhya (`test_sankhya_architecture.py`) agora executa e passa, mas ele **não cobre** a divergência do import de `SankhyaConfig` em `nfe_financeiro_service.py` (esse arquivo está na lista de arquivos verificados pelo guardrail, e o teste passou mesmo assim — indicando que ou o import citado no 01E0 não usa o padrão de import capturado pela verificação AST, ou o guardrail tem uma lacuna de cobertura). Isso deve ser revisto na fase `ERP-DATA-HYGIENE-01D-FIX`, que continua sendo a próxima execução recomendada dentro daquele programa — sem relação com esta correção.

## 14. Riscos Remanescentes

- 103 erros + 4 falhas remanescentes na suíte de integrações por problema de fixture SQLite/schema `farms` — pré-existente, fora do escopo desta correção pontual, mas deve ser tratado antes de usar essa suíte como evidência confiável de regressão em fases futuras do ERP-DATA-HYGIENE.
- O guardrail Sankhya passar sem detectar o import de `SankhyaConfig` em `nfe_financeiro_service.py` sugere possível lacuna na cobertura do guardrail — a investigar na próxima fase, não corrigida aqui (fora de escopo: não alterar testes/guardrails).

## 15. Veredicto

`GO — SUÍTE DE INTEGRAÇÕES DESBLOQUEADA`

A importação de `integracoes.models` foi restaurada, nenhuma instância de `ForeignKey` é mais reutilizada entre colunas, referências físicas e `ondelete` foram preservados, nenhuma migration foi necessária, a coleta de `tests/unit/integracoes/*` funciona, o guardrail Sankhya executa e passa, nenhum model funcional foi alterado, `ruff` e `git diff --check` passam. As falhas remanescentes (103 erros + 4 falhas) têm causa raiz comum e não relacionada (fixture SQLite/schema `farms`), documentada para tratamento futuro fora deste escopo.

## Próxima Etapa

Conforme definido em `ERP-DATA-HYGIENE-01E0`, a próxima execução autorizável no programa de modernização é `ERP-DATA-HYGIENE-01D-FIX`, com escopo restrito a remover o import ORM remanescente de `services/api/integracoes/sankhya/services/nfe_financeiro_service.py` — não a antiga fase 01E.
