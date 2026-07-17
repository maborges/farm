# TENANT-INTEGRITY-REPAIR-01D — Execução Final

## Estado anterior

- Banco posicionado em `tenant_integrity_repair_01b5_sankhya`.
- Grafo auditado com head único em `tenant_fk_repair_01d`.
- Encadeamento presente no checkout: `01B4 → 01B5 → 01D`.
- Migration carregada com:
  - `revision = tenant_fk_repair_01d`;
  - `down_revision = tenant_integrity_repair_01b5_sankhya`.
- FKs diretas para `farms.tenants(id)`:
  - `CASCADE = 200`;
  - `NO ACTION = 31`;
  - `RESTRICT = 0`;
  - pendentes de validação: `0`;
  - duplicadas: `0`.
- As 200 FKs-alvo tinham exclusivamente a forma
  `farms.<tabela>.tenant_id → farms.tenants(id)`.
- Nenhuma sessão utilizava as tabelas-alvo e não havia lock pendente.

## Mecanismo de execução

A tentativa convencional foi realizada primeiro:

```bash
.venv/bin/alembic upgrade tenant_fk_repair_01d
```

O carregamento falhou antes da execução da migration com o erro conhecido:

```text
sqlalchemy.exc.InvalidRequestError: This ForeignKey already has a parent
```

A migration existente foi então carregada diretamente e sua função
`upgrade()` foi executada por `Alembic Operations`. Um proxy transacional
suprimiu exclusivamente o `op.execute("COMMIT")` interno. Todo o DDL, as
validações e a atualização de `farms.alembic_version` permaneceram na mesma
transação externa.

Não foi executado SQL manual substituindo a lógica da migration. Não houve
alteração no conteúdo da `tenant_fk_repair_01d`.

## Execução e atomicidade

Duas tentativas de controle anteriores à aplicação efetiva foram abortadas:

1. uma asserção de snapshot posterior usou a lista de tabelas ainda `CASCADE`,
   já vazia após o upgrade; a exceção provocou rollback integral;
2. uma consulta de snapshot parametrizou incorretamente o tipo interno
   `pg_constraint.confdeltype`; o erro ocorreu antes de chamar `upgrade()`.

Após cada falha, o banco permaneceu em `01B5`, com `CASCADE = 200`,
`NO ACTION = 31`, `RESTRICT = 0` e zero FK inválida.

A execução final ocorreu com `lock_timeout = 10s` e concluiu em uma única
transação. Antes do commit foram confirmados:

- 200 constraints recriadas;
- um `COMMIT` interno suprimido;
- zero FK inválida;
- zero duplicata;
- identidade de schema, tabela, nome, coluna, `ON UPDATE`, `MATCH` e
  deferrabilidade preservada nas 200 FKs;
- versão Alembic atualizada somente após todos os asserts de schema e dados.

## Contagem de FKs antes e depois

| Regra | Antes | Depois |
|---|---:|---:|
| `ON DELETE CASCADE` | 200 | 0 |
| `ON DELETE RESTRICT` | 0 | 200 |
| `ON DELETE NO ACTION` | 31 | 31 |
| Não validadas | 0 | 0 |
| Duplicadas | 0 | 0 |

As 29 FKs `NO ACTION` implantadas em `01B2`–`01B5` foram preservadas. As sete
FKs compostas da `01C` permaneceram presentes e validadas.

## Versão Alembic

| Momento | `farms.alembic_version` |
|---|---|
| Antes | `tenant_integrity_repair_01b5_sankhya` |
| Depois | `tenant_fk_repair_01d` |

O pós-check confirmou head único em `tenant_fk_repair_01d`.

## Preservação de schema, RLS e dados

- As definições das 232 colunas `tenant_id` do schema foram comparadas antes e
  depois e permaneceram idênticas.
- O estado de RLS/FORCE RLS das 297 tabelas físicas do schema foi comparado
  antes e depois e permaneceu idêntico.
- As contagens exatas das 200 tabelas afetadas foram comparadas dentro da
  transação: 1.697 linhas antes e depois.
- Digest do mapa de contagens:
  `a5b8c025a60d7fc0d6a1e92c528047ebce2102eade40d625265f03cb2e0d04be`.
- Nenhum dado de negócio foi inserido, atualizado ou removido.

## Arquivos alterados

Nesta execução não houve alteração de migration, model, runtime, RLS ou código
de domínio. Foi criado somente este relatório:

- `docs/implementation/reports/TENANT-INTEGRITY-REPAIR-01D-EXECUCAO-FINAL.md`.

As alterações locais provenientes das fases anteriores foram preservadas sem
edição nesta execução.

## Comandos executados

```bash
.venv/bin/alembic upgrade tenant_fk_repair_01d
.venv/bin/alembic heads
.venv/bin/alembic history -r tenant_integrity_repair_01b4_iot_auxiliares:tenant_fk_repair_01d
.venv/bin/pytest tests/integrity/test_tenant_fk_guardrails.py \
  -m 'phase_01b2 or phase_01b3 or phase_01b4 or phase_01b5 or phase_other' -q
services/api/.venv/bin/pytest \
  services/api/tests/integrity/test_tenant_fk_guardrails.py::test_g1_nenhuma_fk_cascade_para_tenants -q
services/api/.venv/bin/ruff check services/api
services/api/.venv/bin/python -m compileall -q services/api \
  -x 'services/api/.venv|node_modules'
git diff --check
```

Também foram executadas consultas de catálogo e o runner controlado de
`Alembic Operations` por `.venv/bin/python`, incluindo preflight, snapshots,
aplicação atômica e pós-check.

## Resultados dos testes

- Pós-check físico: aprovado.
- Guardrail específico `01D/G1`: `1 passed`.
- Guardrails acumulados: `118 passed`, `1 failed`, `19 deselected`.
- A única falha acumulada foi `G3`, por oito tabelas sem índice em `tenant_id`;
  débito preexistente e não relacionado à alteração `CASCADE → RESTRICT`.
- Smoke test de runtime: exclusão de tenant bloqueada por FK com
  `SQLSTATE 23503`; savepoint e transação revertidos.
- `python -m compileall`: aprovado.
- `git diff --check`: aprovado.
- `ruff check services/api`: executado; encontrou 25.807 violações
  preexistentes no repositório, sem alteração automática.

## Riscos e limitações

- O lint global e o guardrail G3 permanecem com débitos anteriores e não foram
  alterados, conforme a restrição de não reabrir fases encerradas.
- O `downgrade()` não foi executado.
- A execução ocorreu sobre o checkout auditado; o arquivo `01B5` e o
  encadeamento para `01D` ainda precisam permanecer presentes no artefato usado
  em qualquer reprodução futura.

## Pendência isolada de infraestrutura

O carregamento convencional do Alembic continua bloqueado pela reutilização de
uma instância de `ForeignKey` em `services/api/integracoes/models.py`. O defeito
é preexistente, não pertence à migration `01D` e não afetou a execução
controlada nem os pós-checks. Ele permanece registrado separadamente como bug
de infraestrutura.

## Veredicto final

Os critérios de encerramento foram atendidos:

```text
CASCADE = 0
RESTRICT = 200
NO ACTION = 31
farms.alembic_version = tenant_fk_repair_01d
```

```text
TENANT-INTEGRITY-REPAIR
STATUS: CONCLUÍDO
```

Não deve ser criada nova fase de Tenant Integrity.
