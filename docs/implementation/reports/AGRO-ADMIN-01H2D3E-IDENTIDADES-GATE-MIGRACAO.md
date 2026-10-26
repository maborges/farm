# AGRO-ADMIN-01H2D3E — Regularização de Identidades por Database e Gate de Migração

**Data:** 2026-10-25  
**Escopo:** auditoria do cluster local, implementação dos guardrails e provisionador por database; nenhuma migration, role ou ACL de database foi alterada nesta fase.  
**Veredicto:** **GO COM RESSALVAS para os guardrails em código; NO-GO para declarar regularização operacional concluída.**

## 1. Diagnóstico

Foram lidos os relatórios AGRO-ADMIN-01H2D3A, 01H2D3B, 01H2D3C e 01H2D3D. Evidências de identidade já registradas para o cluster:

| Item | Valor conhecido |
|---|---|
| Endpoint | `127.0.0.1:5433` |
| PostgreSQL | `16.15` |
| PID | `1447173` |
| PGDATA | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` |
| Database original | `agro_hml_dbdcc24872aa` |
| Database da prova corrigida | `agro_hml_dbdcc24872aa_d3d` |
| Role migradora histórica | `agro_hml_migrate_dbdcc24872aa` |

Auditoria read-only durante esta fase reconfirmou, nos dois databases, endpoint loopback/porta 5433, PostgreSQL 16.15, revisão `baseline_deepfarms_v1`, 349 tabelas em `farms` incluindo `alembic_version`, e a role migradora histórica. A role não tem `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, `BYPASSRLS` ou `INHERIT`, e possui zero memberships. Entretanto, ela tem privilégios efetivos `CONNECT` e `CREATE` nos **dois** databases, sem `TEMP`:

`pg_ctl status -D /tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` confirmou read-only o PID `1447173`; a linha de comando observada referencia o mesmo PGDATA e `config/postgresql.conf` do laboratório.

| Role atual | Database | CONNECT | CREATE | TEMP |
|---|---|---:|---:|---:|
| `agro_hml_migrate_dbdcc24872aa` | `agro_hml_dbdcc24872aa` | Sim | Sim | Não |
| `agro_hml_migrate_dbdcc24872aa` | `agro_hml_dbdcc24872aa_d3d` | Sim | Sim | Não |

Isso confirma a causa do NO-GO de 01H2D3D: a mesma identidade de migration foi reutilizada entre bancos. As permissões globais estão restritas, mas a identidade não é exclusiva por database.

### Gate antes e depois

Antes das alterações de código, `migration-identity` no contexto `-d3d` já havia reprovado os grants no database adicional. Com o novo contrato por database, o gate foi executado read-only nos dois roots preservados e ambos retornaram:

```text
NO-GO: DATABASE_URL Alembic não corresponde ao role/database exclusivos do laboratório.
```

O gate agora rejeita a credencial legada antes da autenticação ao banco, pois seu nome não é o nome database-scoped esperado. A consulta de catálogo read-only confirmou separadamente os grants cruzados acima. Nenhum grant foi revogado.

## 2. Modelo por database

O nome da role migradora agora é derivado do ID completo do laboratório e do nome do database, com slug e digest SHA-256 de 64 bits. Isso mantém nomes diferentes para o mesmo laboratório/database distinto e limita o nome PostgreSQL a 63 caracteres.

Para os dois alvos preservados, os nomes esperados pelo novo modelo são distintos:

| Database | Role database-scoped esperada |
|---|---|
| `agro_hml_dbdcc24872aa` | `agro_hml_mig_dbdcc248_agrohmldbdcc24872aa_739524bd178f4904` |
| `agro_hml_dbdcc24872aa_d3d` | `agro_hml_mig_dbdcc248_agrohmldbdcc248aad_5732d23cbd4fbf1f` |

Cada role criada pelo provisionador recebe `LOGIN`, `NOINHERIT`, `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`, limite de conexão 5 e zero memberships. O DDL concede apenas `CONNECT` e `CREATE` no database confirmado e remove os privilégios de `PUBLIC` nesse database novo para evitar `TEMP`/`CONNECT` herdados. O gate consulta privilégios efetivos em todos os databases do cluster e rejeita qualquer acesso adicional.

O papel administrativo não é criado, alterado ou promovido. Antes do provisionamento, o script confirma owner esperado, versão, endpoint, PGDATA, PID/`postmaster.pid`, processo em `/proc`, banco vazio, inexistência da role e atributos administrativos preexistentes. O provisionador exige arquivo administrativo local em modo `0600`, database idêntico ao env sintético, `--confirm-database` com o mesmo nome e `--apply` explícito. Nunca sobrescreve configuração Alembic já existente.

## 3. Guardrails contra migrations

### Controlador

`agro_labctl.py migrate` agora chama primeiro o gate oficial `migration-identity`. Só depois valida `--revision` exata e o arquivo privado `config/migration-approval.json`, que deve ter modo `0600` e conter exatamente:

```json
{
  "instance_id": "<id do laboratório>",
  "database": "<database alvo>",
  "revision": "<revision Alembic exata>",
  "authorization_id": "<referência de autorização>"
}
```

`head`, `heads`, `base`, ranges e revisões divergentes são recusados. Mesmo com gate e registro de aprovação válidos, o comando permanece bloqueado pelo estado arquitetural do grafo Alembic; nenhuma autorização de migration foi criada nesta fase.

### Entradas Alembic auxiliares

Foi adicionado `scripts/homologacao/agro_lab_migration_guard.py` e sua chamada central em `services/api/migrations/env.py`. A proteção cobre Alembic CLI e chamadas programáticas porque todas passam pelo `env.py`. Para database `agro_hml_*`, `deepfarms_hml_*`, `agro_staging_*` ou staging local em 5433, a execução falha antes do DDL se faltar qualquer requisito:

- `AGRO_LAB_ROOT` aponta para a configuração privada do laboratório;
- env efetivo de Alembic corresponde exatamente à URL privada/role/database;
- uma única revisão explícita foi solicitada e ela existe no grafo do checkout;
- `migration-approval.json` autoriza o mesmo ID, database e revision;
- o gate oficial `migration-identity` autentica a identidade e retorna PASS.

Assim, o runner auxiliar `services/api/scripts/homologar_postgresql_ci.py` não pode aplicar `upgrade head` em databases do laboratório: sua chamada programática não fornece uma revisão exata e termina no guard. O script de staging que chama `upgrade head` também não tem a raiz/approval privada exigidas e é recusado ao entrar no `env.py`. Nenhum desses runners foi iniciado nesta fase.

O guard rejeita fallback SQLite no contexto staging do laboratório: o alvo é reconhecido pelo ID/config ou prefixo, então URL efetiva não-PostgreSQL ou divergente não corresponde ao env privado e termina em erro antes da execução. `validate_all` continua recusando segredos herdados de provedores e o gate exige os envs sintéticos.

## 4. Arquivos criados/alterados

- `scripts/homologacao/agro_labctl.py` — role esperada por database, autorização de migration vinculada a database/revision, chamada obrigatória do gate antes do bloqueio e manifesto de `prepare` com database/role-alvo.
- `scripts/homologacao/agro_lab_migration_guard.py` — proteção central do ambiente Alembic contra execução local de lab sem gate/approval.
- `scripts/homologacao/provision_migration_identity.py` — provisionador explícito para um database novo e vazio; não foi executado.
- `scripts/homologacao/test_agro_labctl.py` — testes de isolamento por database, rejeição de role legada, autorização exata, falha fechada, detecção de runner/local target e DDL least-privilege.
- `services/api/migrations/env.py` — chamada ao guard antes dos modos online/offline. Alterações anteriores de version table/schema foram preservadas; nesta fase foi acrescentada somente a chamada/import do guard.
- Este relatório.

## 5. Provisionamento e identidade real

**Nenhuma role nova foi criada e nenhum grant foi alterado.** As duas databases nomeadas são provas já utilizadas e devem permanecer como evidência; ambas contêm o schema `farms`, e a role antiga continua com acesso cruzado. O provisionador exige alvo vazio, role ainda inexistente e manifesto de cluster coerente, portanto recusaria ambos.

Não foi indicado um terceiro database novo para provisionamento. Criar uma role e conceder `CREATE` em um dos dois alvos alteraria ACLs da evidência protegida. Por esse motivo, não foi executado o provisionador. Consequentemente:

- não há gate PostgreSQL real PASS para uma role nova database-scoped;
- a prova positive de `validate_migration_identity_record` é unitária/sintética, não prova de role no PostgreSQL;
- o gate oficial continua NO-GO nos dois roots legados;
- as credenciais privadas antigas permanecem sem alteração e não são aceitas pelo novo gate.

## 6. Testes executados

- `services/api/.venv/bin/pytest scripts/homologacao/test_agro_labctl.py -q` — **45 passed**.
- Ruff nos quatro arquivos de controlador/guard/provisionador/teste e `services/api/migrations/env.py` — **PASS**.
- `py_compile` dos módulos Python alterados — **PASS**.
- `git diff --check` nos arquivos desta etapa — **PASS**.
- Auditoria read-only dos dois databases e das permissões efetivas da role — confirmou ambos os grants `CONNECT`/`CREATE` e zero privilégios globais/memberships.
- `migration-identity` nos dois roots legados — **NO-GO** esperado para o contrato de role por database; nenhuma migration foi chamada.

Não foram executados DDL de aplicação, migrations, `stamp`, downgrade, testes PostgreSQL mutantes, serviços, Docker, deploy, commit, push ou merge.

## 7. Compatibilidade e riscos

- A implementação não reescreve nem apaga as roles/provas históricas. As configurações antigas agora são detectadas e rejeitadas; para um alvo novo, o provisionador gera outra identidade e outra configuração `0600`.
- O database por si só não é a fronteira global de uma role PostgreSQL: roles são cluster-wide. O gate verifica permissões efetivas em todos os databases e memberships, incluindo grants via `PUBLIC`.
- O `migration-approval.json` é um registro operacional privado, não uma assinatura criptográfica. A proteção também depende das permissões do diretório privado do laboratório e do gate PostgreSQL efetivo.
- O provisionador não tenta corrigir ACLs de outros databases. Se existir acesso efetivo por `PUBLIC` ou configuração de cluster, o gate recusa e o operador precisa de autorização separada para a causa específica.
- Em falha ambígua durante execução do DDL de provisionamento, o arquivo temporário de credencial permanece com modo `0600` para diagnóstico; o script não apaga role/grants automaticamente.
- O guard só rege entradas Alembic que carregam `services/api/migrations/env.py`; SQL executado fora de Alembic requer controle operacional próprio. Não foi encontrado outro runner Alembic no repositório além dos paths auditados que evite esse `env.py`.
- O histórico Alembic continua impedindo liberação de upgrade até o head. O guard não resolve essa pendência.

## 8. Procedimento futuro de provisionamento

Após designar explicitamente um **database descartável novo, vazio e não utilizado**:

1. Preparar uma raiz inédita pelo controlador e provisionar a infraestrutura dedicada de acordo com seu manifesto.
2. Criar, sem copiar `.env.local`/`.env.production`, `config/postgres-admin.env` com apenas `DATABASE_URL` sintética do owner administrativo, modo `0600`.
3. Confirmar que env de API, manifesto, database, PGDATA, PID e PostgreSQL real correspondem à mesma instância.
4. Executar `scripts/homologacao/provision_migration_identity.py` com `--root`, `--admin-env`, `--database`, `--confirm-database` repetindo literalmente o nome e `--apply`.
5. O script recusará database com relações/schema de aplicação, owner ou processo divergente, role existente, arquivo de migration preexistente ou falha de gate. Ele não inicia serviços nem executa migration.
6. Exigir `agro_labctl.py migration-identity` **PASS** para a role recém-criada. Se for NO-GO, preservar estado e interromper sem revogar grants de outros databases.
7. Só uma autorização futura separada poderá criar `migration-approval.json` e autorizar uma revisão; o caminho atual continuará bloqueado até resolução arquitetural do grafo.

## 9. Veredicto

**GO COM RESSALVAS para os guardrails de código:** 45 testes direcionados passaram; o controlador exige o gate oficial; Alembic CLI e runners programáticos que alcancem o `env.py` não prosseguem em databases do laboratório sem identidade aprovada, database/revision exatos e approval privado; o provisionador é explícito, least-privilege e recusa destinos usados.

**NO-GO para regularização operacional completa:** as duas provas antigas continuam usando a mesma role com `CONNECT`/`CREATE` em ambos os databases e, corretamente, o gate oficial retorna NO-GO para as configurações legadas. Nenhum database novo foi designado para criar uma role exclusiva e comprovar o gate real PASS. Os databases, roles e ACLs existentes permanecem preservados. Não houve migrations ou serviços iniciados; encerrar nesta fase.
