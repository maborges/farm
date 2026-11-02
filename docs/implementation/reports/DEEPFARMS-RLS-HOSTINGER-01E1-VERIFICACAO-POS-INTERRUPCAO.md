# DEEPFARMS-RLS-HOSTINGER-01E1 — Verificação Pós-Interrupção

**Data:** 2026-10-31  
**Escopo:** recuperação de estado, somente leitura no PostgreSQL; sem repetir testes de escrita  
**Destino consultado:** `192.168.0.2:5432`, database `deepfarms_rls_lab`  
**Veredicto:** **PARCIALMENTE CONCLUÍDO**

## 1. Resumo executivo

O laboratório existe e contém uma fixture sintética mínima `farms.rls_probe`, com RLS e `FORCE ROW LEVEL SECURITY` habilitados, policy vinculada a `deepfarms_rls_lab_runtime`, grants restritos e uma sequence de identity. A conexão desta verificação autenticou diretamente como `deepfarms_rls_lab_runtime`, sem privilégios `SUPERUSER`, `BYPASSRLS` ou ownership da tabela. As consultas somente leitura confirmaram que, sem contexto, a tabela retorna zero linhas; com `tenant-a` e `tenant-b`, cada contexto enxerga somente sua linha.

O histórico de execução desta conversa registra que a fixture foi criada e que, em execução anterior, o INSERT cruzado foi rejeitado pela policy e UPDATE/DELETE cruzados não encontraram linhas. Esta verificação não repetiu operações de escrita. Não foram encontrados transcript SQL, logs persistidos ou script de teste específico para a fixture. O relatório anterior 01E é histórico e antecede a criação do laboratório.

A prova confirma o mecanismo básico de RLS do PostgreSQL para uma tabela tenant-private sintética. Não comprova o helper nem o comportamento da aplicação, conexão reutilizada por pool, tabelas filhas, catálogos globais, workers, API ou as demais classes de tabela previstas em 01D. Portanto, **a 01E não está encerrada**.

## 2. Estado observado do laboratório

### Identidade e database

Consulta de catálogo em transação `READ ONLY`, conectada diretamente como runtime:

| Campo | Resultado |
|---|---|
| `current_database()` | `deepfarms_rls_lab` |
| `current_user` / `session_user` | `deepfarms_rls_lab_runtime` |
| Endereço informado pelo servidor | `172.26.132.19:5432` |
| PostgreSQL | `16.15` |
| Database | Existe, aceita conexão; owner `deepfarms_rls_lab_owner` |

A conexão foi estabelecida ao endpoint de desenvolvimento autorizado `192.168.0.2:5432`; `inet_server_addr()` reportou o endereço interno `172.26.132.19`. Nenhuma conexão à Hostinger foi feita.

### Roles e memberships

Os atributos foram consultados em `pg_roles`; memberships em `pg_auth_members`:

| Role | LOGIN | SUPERUSER | BYPASSRLS | CREATEDB | CREATEROLE | INHERIT | Membership observada |
|---|---:|---:|---:|---:|---:|---:|---|
| `deepfarms_rls_lab_owner` | Não | Não | Não | Não | Não | Não | Nenhuma |
| `deepfarms_rls_lab_deploy` | Sim | Não | Não | Não | Não | Não | `deepfarms_rls_lab_owner`, `SET` permitido, herança desabilitada |
| `deepfarms_rls_lab_runtime` | Sim | Não | Não | Não | Não | Não | Nenhuma |

Privilégios efetivos observados:

| Papel | CONNECT no database | CREATE no database | TEMP no database | `farms.USAGE` | `farms.CREATE` |
|---|---:|---:|---:|---:|---:|
| `owner` | Sim | Sim | Sim | Sim por ownership | Sim por ownership |
| `deploy` | Sim | Não | Não | Não | Não |
| `runtime` | Sim | Não | Não | Sim | Não |

O runtime não é owner do database, schema, tabela ou sequence. Não tem membership na role owner.

### Schema, objetos, constraints e grants

O schema `farms` pertence a `deepfarms_rls_lab_owner`. O schema `public` existe, pertence a `pg_database_owner`, e o runtime não tem `USAGE` nem `CREATE` nele.

| Objeto | Owner | Estado | Privilégios efetivos do runtime |
|---|---|---|---|
| `farms.rls_probe` | `deepfarms_rls_lab_owner` | RLS habilitado; FORCE RLS habilitado | SELECT, INSERT, UPDATE e DELETE; sem TRUNCATE |
| `farms.rls_probe_id_seq` | `deepfarms_rls_lab_owner` | Sequence de identity | USAGE e SELECT; sem UPDATE |

A única constraint encontrada no schema é a primary key `rls_probe_pkey (id)`. Não há FK, UNIQUE ou CHECK na fixture. A única policy encontrada é `rls_probe_tenant_policy`, permissiva, `FOR ALL`, para `deepfarms_rls_lab_runtime`, com `USING` e `WITH CHECK` comparando `tenant_id` com `current_setting('app.current_tenant_id', true)`.

### Dados sintéticos

O transcript da criação registra `INSERT 0 2`, com uma linha para `tenant-a` (`dado A`) e uma para `tenant-b` (`dado B`). As consultas atuais, como runtime e em transações somente leitura, confirmaram uma linha visível em cada contexto. Sem contexto, `count(*)` retornou zero. As duas linhas sintéticas continuam presentes segundo o histórico e essas leituras por Tenant.

## 3. Evidências recuperadas

### Evidência persistida em arquivos

- `DEEPFARMS-RLS-HOSTINGER-01E-LABORATORIO-ISOLAMENTO.md` existe, mas registra o preflight anterior: banco e roles ainda ausentes, sem DDL/DML e prova não iniciada. Ele foi correto para aquele momento e está superado pelo estado posterior observado nesta verificação; não foi alterado.
- Não foi encontrado script de laboratório específico para `rls_probe`, transcript de `psql` ou arquivo de log dos testes desta fixture.
- `/tmp/deepfarms-rls-01e0-dev-catalog.json` e os artefatos 01C são inventários do banco de desenvolvimento `farms`/`tara`; não são evidência de execução no laboratório.
- `/tmp/rls_connection_audit.py` verifica relações tenant no schema existente `farms`; não implementa nem testa a fixture do laboratório.

### Evidência no transcript da execução anterior

O histórico desta conversa contém as saídas do `psql` da criação: `CREATE TABLE`, `INSERT 0 2`, `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `CREATE POLICY` e grants de tabela/sequence. Também contém as saídas dos testes anteriores, executados como `deepfarms_rls_lab_runtime`:

- SELECT sem contexto: zero linhas.
- Contexto `tenant-a`: somente `dado A`.
- Contexto `tenant-b`: somente `dado B`.
- UPDATE cruzado sob `tenant-a`: zero linhas afetadas.
- INSERT de linha `tenant-b` sob `tenant-a`: erro `new row violates row-level security policy`; a transação foi revertida.
- DELETE cruzado sob `tenant-a`: zero linhas afetadas.
- Após os commits dos contextos, SELECT sem contexto voltou a zero linhas.

Essas saídas são evidência objetiva de execução registrada no transcript, mas não constituem log independente persistido em arquivo. A consulta atual de catálogo e as leituras somente leitura confirmam que os objetos e os resultados de leitura ainda existem. Nenhum teste de escrita foi repetido nesta recuperação.

## 4. Matriz de testes previstos

| Teste | Estado | Evidência / limite |
|---|---|---|
| 1. SELECT entre Tenants A/B | **CONFIRMADO** | Transcript anterior registra A vendo só `dado A` e B vendo só `dado B`; leitura somente leitura atual repetiu a confirmação. |
| 2. INSERT com Tenant incorreto | **CONFIRMADO** | Transcript anterior registra violação de policy ao inserir B sob contexto A, seguida de rollback. Não repetido nesta execução. |
| 3. UPDATE e DELETE entre Tenants | **CONFIRMADO** | Transcript anterior registra `UPDATE 0` e `DELETE 0` de linha B sob contexto A. Não repetidos nesta execução. |
| 4. Ausência de contexto Tenant | **CONFIRMADO** | Transcript anterior e consulta atual retornaram zero linhas sem contexto. |
| 5. Contexto transacional `SET LOCAL` ou equivalente | **CONFIRMADO, limitado à fixture** | Transcript registra `set_config(..., true)` dentro de transações; leitura atual usou `SET LOCAL` dentro de `BEGIN READ ONLY`. Não testa helper da aplicação. |
| 6. Commit e rollback | **INCOMPLETO** | Há commits após leituras A/B e rollback da transação cujo INSERT foi rejeitado. Não há prova de DML permitido seguido de rollback nem de confirmação de DML válido por commit. |
| 7. Reutilização de conexão sem vazamento | **INCOMPLETO** | A mesma sessão `psql` foi usada em comandos subsequentes; após commit, ausência de contexto voltou a zero. Não houve teste de checkout/reuso de conexão por pool, alternância entre sessões ou rollback no pool. |
| 8. Isolamento de tabela filha por relacionamento | **NÃO COMPROVADO** | Não há tabela filha, FK ou policy relacional na fixture. |
| 9. Leitura compartilhada de catálogo global | **NÃO COMPROVADO** | Não há catálogo global ou linha global sintética. |
| 10. Escrita global bloqueada para runtime comum | **NÃO COMPROVADO** | Não há tabela global/mista nem role de administração de catálogo na fixture. |
| 11. Role efetiva sem BYPASSRLS, SUPERUSER ou ownership | **CONFIRMADO** | Catálogo atual: runtime sem `SUPERUSER`/`BYPASSRLS`, sem membership de owner e sem ownership da tabela. Conexão atual autenticou diretamente como runtime. |
| 12. Compatibilidade com o plano 01D | **INCOMPLETO** | Confirma a semântica básica tenant-private da policy e do contexto local. Não cobre helper da aplicação, tabelas existentes, filhas, catálogos, workers, API, pool ou regressão previstos em 01D. |

## 5. Pendências e erros

### Concluído

- Database e as três roles existem com atributos de menor privilégio observados.
- Membership deploy → owner permite `SET`, sem herança automática; runtime não tem membership.
- Schema `farms`, tabela sintética, sequence, primary key, grants e policy existem.
- RLS e FORCE RLS estão habilitados na tabela.
- SELECT sem contexto e visibilidade A/B foram comprovados.
- Transcript anterior comprova rejeição de INSERT cruzado e invisibilidade para UPDATE/DELETE cruzados.
- Estado foi consultado nesta execução dentro de transações `READ ONLY`; nenhum teste de escrita, migration ou alteração de objeto foi executado agora.

### Parcial / sem comprovação

- Rollback de uma escrita válida, commit de escrita válida e persistência após commit não foram testados.
- Reuso de conexão pelo pool após commit, rollback, erro/cancelamento e alternância A/B não foi testado.
- Não há fixtures de filha relacional, catálogo global/misto ou role catalog-admin.
- O contexto foi configurado manualmente no `psql`; integração com `core.dependencies`, helper aprovado, API ou workers não foi executada.
- A fixture tem apenas uma tabela e não demonstra o inventário físico das 350 tabelas, as 49 tabelas com RLS/188 policies citadas em 01C/01D, nem o comportamento operacional completo.
- Não foi localizado log de teste independente; parte da evidência da criação e dos testes negativos depende do transcript da conversa.

### Erros identificados

- O INSERT cruzado falhou como esperado pela policy; é o resultado esperado do teste negativo, não uma falha funcional da fixture.
- Não há evidência de outro erro de execução no transcript consultado.

## 6. Menor repetição necessária para encerrar a 01E

Não executar novamente a criação de roles, database, schema, tabela ou policy. Preservar a fixture atual. Em execução posterior, exclusivamente no laboratório:

1. Persistir um transcript de teste sem credenciais, ou relatório de saída que registre identidade e resultado de cada cenário.
2. Completar somente os casos ausentes da fixture: rollback e commit de uma escrita válida; reuso da mesma conexão após commit/rollback e alternância A/B. Não repetir os negativos INSERT/UPDATE/DELETE já registrados, salvo se for necessário produzir um transcript durável.
3. Para compatibilidade com 01D, acrescentar fixtures sintéticas de filha relacional e catálogo global/misto e provar leitura global/escrita global restrita sob runtime comum.
4. Tratar integração de helper, API, workers e pool como etapa própria de laboratório. A prova atual não autoriza cutover nem comprova segurança do DeepFarms completo.

Não acessar ou alterar o banco principal `farms`, schema `tara`, Hostinger, código funcional, migrations ou configuração de produção para fechar essas pendências.

## 7. Veredicto final

**PARCIALMENTE CONCLUÍDO.** O laboratório existe e a prova básica A/B de uma policy tenant-private está confirmada, inclusive com uso direto de runtime sem bypass, superuser ou ownership. A 01E permanece aberta porque há cenários previstos em 01D sem fixture ou evidência, além de lacunas de commit/rollback e pool. A existência da fixture não é tratada como aprovação das classes não testadas.

**Esta execução de recuperação foi somente leitura no banco.** Nenhuma role, tabela, grant ou policy foi criada, removida ou alterada; nenhum teste de escrita foi repetido; nenhuma migration ou conexão à Hostinger foi executada. Nenhum segredo ou senha foi incluído neste relatório.
