# MIGRATION-METADATA-01D — Baseline experimental em PostgreSQL limpo

## Veredicto

```text
MIGRATION-METADATA-01D
STATUS: NO-GO
```

A migration independente foi construída e compilada em modo offline, mas a
prova física obrigatória não pôde ser executada. O usuário PostgreSQL
`borgus` não possui `CREATEDB` e não existe outro database vazio disponível.
O banco funcional `farms` não foi utilizado como substituto.

## Ambiente e segurança

Consultas realizadas, somente leitura, contra o servidor PostgreSQL
`192.168.0.3`:

```sql
SELECT current_database(), current_user, inet_server_addr();
SELECT datname, pg_get_userbyid(datdba), datallowconn
FROM pg_database
WHERE datistemplate = false
ORDER BY datname;
```

Resultado: `farms` e `postgres` são os únicos databases disponíveis; o
usuário é `borgus`. A tentativa de criar o database explicitamente separado
`deepfarms_baseline_01d` foi recusada com `permission denied to create
database`. Nenhum banco, tabela, dado, RDS ou migration histórica foi
alterado.

Não foram executados `create_all`, `drop_all`, `upgrade` online,
`downgrade`, `autogenerate` ou DDL no banco funcional.

## Artefato criado

A baseline independente está em:

`services/api/migrations/versions/20260908_baseline_deepfarms_v1.py`

```text
revision     = baseline_deepfarms_v1
down_revision = None
branch       = deepfarms_baseline
```

Ela consome o registry aprovado e `baseline_contract.py`; não concatena a
cadeia histórica e não chama `MetaData.create_all()`.

## Ordem DDL implementada

1. schema `farms` e `search_path`;
2. 34 ENUMs, com 146 valores na ordem contratada;
3. 32 sequences REQUIRED;
4. 344 tabelas ORM, sem FKs inline;
5. 891 Foreign Keys do contrato fechado;
6. índices declarados pelo ORM;
7. três functions e três triggers lógicos;
8. RLS/ FORCE RLS;
9. 188 policies.

As FKs são adicionadas após todas as tabelas para permitir dependências
entre tabelas sem depender de uma ordenação acidental. A contagem de tabelas
emitida no SQL offline é 345 porque inclui `alembic_version`; o conjunto de
domínio da baseline é 344.

## Validação offline

Comando:

```bash
cd services/api
PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql
```

Resultado:

```text
return code = 0
CREATE TYPE       = 34
CREATE SEQUENCE   = 32
CREATE TABLE      = 345 (344 + alembic_version)
FOREIGN KEY      = 891
CREATE INDEX      = 1006
CREATE FUNCTION   = 3
CREATE TRIGGER    = 3
CREATE POLICY     = 188
```

Essa validação prova a emissão SQL, não a aceitação pelo PostgreSQL nem o
comportamento de runtime.

## Correções aplicadas durante a construção

* Ajustada a emissão de `CreateEnumType`/`DropEnumType` para os construtores
  PostgreSQL corretos do SQLAlchemy.
* FKs foram separadas da criação de tabelas e recebem o `ondelete` fechado no
  contrato, preservando `tenant CASCADE = 0`.
* As definições das três functions/triggers foram incluídas na migration,
  incluindo o trigger de constraint deferred de `production_units` e a
  atualização defensiva da área anterior em UPDATE.
* Criado guardrail estático para confirmar revision independente, 344 tabelas
  e ausência de `create_all()`/`drop_all()` na migration.

## Critérios ainda não comprovados

Os itens abaixo exigem o database descartável e permanecem bloqueadores:

* primeira aplicação online em PostgreSQL vazio;
* destruição/recriação e segunda aplicação limpa;
* introspecção física final dos 344 objetos, ENUMs, sequences e FKs;
* confirmação física de RLS 49/48 e 188 policies;
* aceitação física das três functions e triggers;
* `alembic current` e `alembic heads` no banco criado;
* startup da API sem fallback `create_all()`;
* smoke de autenticação, tenant, Wizard e Unidade Produtiva;
* teste de isolamento entre tenants e `WITH CHECK`.

## Testes executados

```text
14 passed
ruff: All checks passed
git diff --check: passed
SQL offline: return code 0
```

Testes:

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  tests/unit/core/test_model_registry.py \
  tests/unit/core/test_baseline_ddl_contract.py \
  tests/unit/core/test_baseline_contract.py
```

## Riscos residuais

1. A criação online ainda pode revelar incompatibilidades de PostgreSQL que
   a compilação offline não detecta.
2. A aceitação das policies depende de expressões e objetos realmente
   existentes no database novo.
3. A dependência de `gen_random_uuid()` e demais funções nativas precisa ser
   confirmada no PostgreSQL descartável.
4. A baseline não autoriza seed nem deploy em produção.

## Próxima ação necessária

Provisionar um PostgreSQL descartável com permissão de criação de database
ou fornecer um database vazio dedicado ao piloto, explicitamente distinto de
`farms`. Depois disso, repetir a aplicação online, recriar o alvo e executar
os smoke tests previstos. A 01D não deve receber `GO` antes dessas provas.

## Veredicto final

```text
MIGRATION-METADATA-01D
STATUS: NO-GO
```

O próximo passo é somente disponibilizar o ambiente PostgreSQL descartável e
retomar a validação física da 01D. Nenhum deploy de produção foi iniciado.
