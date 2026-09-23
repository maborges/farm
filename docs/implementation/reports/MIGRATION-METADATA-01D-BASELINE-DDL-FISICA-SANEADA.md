# MIGRATION-METADATA-01D — Baseline a partir da DDL física saneada

## Veredicto

```text
MIGRATION-METADATA-01D
STATUS: NO-GO
```

A DDL física do schema `farms` foi extraída com sucesso e usada como
evidência de saneamento. A migration independente foi validada em modo
offline, mas a execução física em PostgreSQL descartável ainda não foi
possível porque o usuário `borgus` não possui `CREATEDB`.

## DDL física extraída

Comando read-only:

```bash
PGPASSWORD='***' pg_dump --schema-only --schema=farms \
  --no-owner --no-privileges \
  --file=/tmp/deepfarms_farms_01d.sql \
  -h 192.168.0.2 -U borgus farms
```

Resultado: PostgreSQL 16.15, 31.141 linhas, sem dados extraídos.

Inventário observado no dump:

```text
ENUMs       = 34
sequences   = 35
tabelas     = 351
índices     = 1.016
policies    = 188
functions   = 3
triggers    = 3
views       = 0
matviews    = 0
```

O dump é uma fotografia do banco funcional e não será reaplicado cegamente.

## Saneamento aplicado

O artefato de baseline usa:

* registry oficial para selecionar exatamente 344 tabelas ORM;
* `baseline_contract.py` para FKs, RLS, policies, ENUMs e sequences;
* DDL histórica/física apenas como evidência pontual das functions/triggers
  e do contrato atual;
* cinco tabelas aprovadas ausentes da fotografia física, criadas pelo
  metadata: `crm_ofertas_personalizadas`, `crm_planos_comerciais`,
  `crm_precificacao_modulo`, `crm_produtos` e `growth_landing_eventos`.

Não entram na instalação nova as oito tabelas antigas da Balança,
`amostras`, `mapas_fertilidade` e
`territory_legacy_backup_01h2`. `alembic_version` permanece controle do
Alembic, não tabela de domínio.

## Migration criada

Arquivo:

`services/api/migrations/versions/20260908_baseline_deepfarms_v1.py`

```text
revision      = baseline_deepfarms_v1
down_revision = None
branch        = deepfarms_baseline
schema        = farms
```

Ordem implementada:

```text
schema → ENUMs → sequences → tabelas → FKs → índices
→ functions/triggers → RLS/FORCE → policies
```

As tabelas são criadas sem FKs inline e as 891 FKs aprovadas são adicionadas
depois. Isso evita dependência da ordem histórica das migrations.

## Objetos estruturais

```text
baseline ORM tables       = 344
ENUMs                     = 34 / 146 valores
sequences REQUIRED        = 32
FK constraints            = 891
FK elements               = 897
composite FKs             = 6
Tenant CASCADE            = 0
índices ORM emitidos      = 1.006
functions                 = 3
triggers lógicos          = 3
RLS ENABLE                = 49
FORCE RLS                 = 48
policies                  = 188
```

`propriedade_imovel` mantém ENABLE sem FORCE. Grants e owners específicos do
ambiente não foram incorporados.

## Validação offline

```bash
cd services/api
PYTHONPATH=. .venv/bin/alembic upgrade baseline_deepfarms_v1 --sql
```

Resultado: retorno 0 e emissão de SQL contendo os totais acima. Essa etapa
prova a geração SQL, não a aceitação física pelo PostgreSQL.

## Prova física bloqueada

Foi confirmado por SELECT que `farms` é o banco funcional e que não existe
database vazio disponível. A tentativa controlada de criar
`deepfarms_baseline_01d` falhou com:

```text
ERROR: permission denied to create database
```

Não foi usado `farms` como alvo. Portanto permanecem sem prova:

* primeira execução online;
* segunda criação limpa;
* introspecção final do database criado;
* `alembic current`/`heads` no alvo novo;
* startup da API;
* smoke de autenticação, tenant e Wizard;
* isolamento físico RLS entre dois tenants.

## Validações locais

```text
14 testes aprovados
Ruff aprovado
git diff --check aprovado
SQL offline emitido com sucesso
```

Nenhuma migration histórica, tabela, dado, RDS ou banco funcional foi
alterado.

## Bloqueio para GO

Provisionar um PostgreSQL/database descartável dedicado com permissão para o
usuário de execução. Depois repetir a aplicação da baseline do zero, destruir
somente o alvo descartável, executar a segunda criação e realizar os testes
físicos obrigatórios. Até isso ocorrer, a baseline não está comprovada para
produção.

```text
MIGRATION-METADATA-01D
STATUS: NO-GO
```
