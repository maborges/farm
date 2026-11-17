# DEEPFARMS-RLS-HOSTINGER-01E2 — Complementação dos Testes de Isolamento

**Data:** 2026-10-31  
**Destino:** PostgreSQL de desenvolvimento `192.168.0.3:5432`, database `deepfarms_rls_lab`  
**Runtime de teste:** `deepfarms_rls_lab_runtime`, autenticado diretamente  
**Escopo:** somente fixtures e dados sintéticos do laboratório  
**Veredicto:** **GO COM RESSALVAS**

## 1. Resultado

Os cenários pendentes de transação, reuso de conexão, relacionamento pai/filha e catálogo global/misto foram executados no laboratório. Todos tiveram o resultado esperado sob a role `deepfarms_rls_lab_runtime`. A fixture original `farms.rls_probe` foi validada e preservada; não foi recriada.

As fixtures novas são `farms.rls_probe_parent`, `farms.rls_probe_child` e `farms.rls_probe_catalog`. As quatro tabelas têm RLS e FORCE RLS habilitados. A role runtime não é owner, não tem membership de owner, `SUPERUSER` ou `BYPASSRLS`; seus grants de tabela permitem SELECT/INSERT/UPDATE/DELETE, sem TRUNCATE. Os testes negativos produziram as negações previstas; não houve falha inesperada de isolamento.

**GO COM RESSALVAS** aplica-se somente às semânticas sintéticas abaixo. Não declara o DeepFarms integralmente protegido por RLS. A integração com API, workers, helper de tenant, tabelas reais e configuração de produção não fez parte desta execução.

## 2. Identidade e fixture original

Antes de qualquer alteração, a conexão runtime confirmou:

```sql
SELECT current_database(), current_user, session_user,
       inet_server_addr(), inet_server_port();
```

Resultado: database `deepfarms_rls_lab`; `current_user = session_user = deepfarms_rls_lab_runtime`; servidor reportado `172.26.132.19:5432`, PostgreSQL 16.15. Não houve conexão à Hostinger.

O gate de catálogo retornou `farms.rls_probe` existente e os nomes das três fixtures novas ausentes. A fixture original foi confirmada com owner `deepfarms_rls_lab_owner`, RLS e FORCE RLS ativos, PK `rls_probe_pkey`, policy `rls_probe_tenant_policy` para runtime e grants CRUD sem TRUNCATE. Nenhuma tabela, policy ou role existente foi recriada.

As novas fixtures foram criadas por `deepfarms_rls_lab_deploy` após `SET ROLE deepfarms_rls_lab_owner`. Toda DDL/DML deste relatório ficou em `deepfarms_rls_lab.farms`. As roles, o database, `farms` existente, `tara`, migrations e código funcional não foram alterados.

## 3. Transações e encerramento de contexto

### INSERT válido e COMMIT

Executado como runtime:

```sql
BEGIN;
SET LOCAL app.current_tenant_id = 'tenant-a';
INSERT INTO farms.rls_probe (tenant_id, dado)
VALUES ('tenant-a', '01e2_commit_20261031_01')
RETURNING id, tenant_id, dado;
COMMIT;
```

**Resultado:** `INSERT 0 1`, id `4`. Em transação de leitura posterior com contexto A, `committed_marker_visible = 1`. Fora da transação, `current_setting` estava limpo e a tabela privada retornou zero linhas sem contexto. **PASS.**

### INSERT válido e ROLLBACK

```sql
BEGIN;
SET LOCAL app.current_tenant_id = 'tenant-a';
INSERT INTO farms.rls_probe (tenant_id, dado)
VALUES ('tenant-a', '01e2_rollback_20261031_01')
RETURNING id, tenant_id, dado;
ROLLBACK;
```

**Resultado:** INSERT aceito dentro da transação (`id = 5`); em transação posterior com contexto A, `rolled_back_marker_visible = 0`. Fora da transação, o contexto estava limpo e não havia linhas visíveis sem contexto. **PASS.** A lacuna entre ids 4 e 5 decorre do comportamento não transacional de sequences PostgreSQL e não representa linha persistida.

### Alternância, conexão psql e erro SQL

Na mesma sessão autenticada como runtime, foi executado A → COMMIT → B → ROLLBACK → sem contexto. A viu só suas linhas, B viu só a sua, `current_setting` ficou limpo após commit/rollback e as consultas sem contexto retornaram zero linhas nas tabelas privadas.

Foi provocado `SELECT 1/0` dentro de transação com contexto A. O PostgreSQL respondeu `division by zero`; após `ROLLBACK`, contexto limpo e zero linhas sem contexto. O erro foi intencional e usado para verificar limpeza/recuperação; não houve erro inesperado.

### SQLAlchemy AsyncEngine com pool real

Foi executado harness isolado temporário, sem alterar o produto, com SQLAlchemy 2.0.48, asyncpg 0.31.0, `pool_size=1`, `max_overflow=0` e `pool_pre_ping=True`. O harness conectou diretamente como runtime, chamou `pg_backend_pid()`, aplicou `set_config('app.current_tenant_id', ..., true)` em transações, fez checkout/checkin, rollback explícito após o erro SQL e consultou o estado após cada retorno ao pool.

| Checkout/cenário | Resultado observado |
|---|---|
| Tenant A | Linhas de A somente |
| Após COMMIT | Contexto limpo; zero linhas privadas sem contexto |
| Tenant B após novo checkout | Linha de B somente |
| Após ROLLBACK | Contexto limpo; zero linhas privadas sem contexto |
| Após erro SQL e rollback | Contexto limpo; zero linhas privadas sem contexto |
| Identidade da conexão | Database e `current_user`/`session_user` runtime |
| `pg_backend_pid()` nos quatro checkouts | `[122239, 122239, 122239, 122239]`; mesmo backend reutilizado |

**PASS:** não foi observado vazamento de contexto entre os checkouts do backend único. Isso prova o caso de um AsyncEngine descartável com pool unitário; não prova o pool configurado pela aplicação nem concorrência/cancelamento de workers.

## 4. Fixture sintética pai/filha

Estrutura criada:

- `rls_probe_parent(id identity PK, tenant_id NOT NULL, dado)` com linhas sintéticas dos Tenants A/B;
- `rls_probe_child(id identity PK, parent_id NOT NULL FK → rls_probe_parent(id), dado)`, sem `tenant_id` direto;
- policies `FOR ALL` para runtime em ambas. A policy da filha usa `EXISTS` sobre o pai, exigindo `parent_id` associado ao Tenant do contexto; `USING` e `WITH CHECK` aplicam a mesma condição;
- RLS e FORCE RLS habilitados nas duas tabelas.

Resultados como runtime:

| Cenário | Esperado | Observado | Resultado |
|---|---|---|---|
| Sem contexto, SELECT de pai/filha | Zero linhas | Zero / zero | **PASS** |
| Contexto A | Pai A e filha ligada ao pai id 1 | Somente pai A e filha `parent_id=1` | **PASS** |
| Contexto B | Pai B e filha ligada ao pai id 2 | Somente pai B e filha `parent_id=2` | **PASS** |
| A consulta filha ligada ao pai B | Zero linhas | Zero linhas | **PASS** |
| A insere filha ligada ao pai B | Negado pela policy | `new row violates row-level security policy`; transação revertida | **PASS** |

Os cenários cruzados foram executados com contexto A:

```sql
SELECT c.id, c.parent_id, c.dado
FROM farms.rls_probe_child c WHERE c.parent_id = 2; -- zero linhas

INSERT INTO farms.rls_probe_child (parent_id, dado)
VALUES (2, 'filha cruzada A para B'); -- policy violation
```

O teste verifica isolamento relacional da fixture e FK existente. Não representa validação de todas as tabelas filhas reais do produto.

## 5. Fixture sintética de catálogo global/misto

`rls_probe_catalog(id identity PK, tenant_id nullable, nome)` contém um registro global (`tenant_id IS NULL`) e registros privados A/B. RLS e FORCE RLS foram habilitados. Policies separadas permitem:

- SELECT global ou do próprio Tenant;
- INSERT somente com `tenant_id` igual ao contexto;
- UPDATE com linha visível e resultado ainda no Tenant do contexto;
- DELETE somente de linha do próprio Tenant.

O runtime recebeu CRUD na tabela e USAGE/SELECT na sequence, sem TRUNCATE. Resultados:

As operações negativas foram executadas sob `tenant-a` com os seguintes comandos representativos:

```sql
UPDATE farms.rls_probe_catalog
SET nome = 'global alterado por tenant'
WHERE tenant_id IS NULL RETURNING *; -- UPDATE 0

DELETE FROM farms.rls_probe_catalog
WHERE tenant_id IS NULL RETURNING *; -- DELETE 0

INSERT INTO farms.rls_probe_catalog (tenant_id, nome)
VALUES (NULL, 'global escrito por tenant'); -- policy violation

INSERT INTO farms.rls_probe_catalog (tenant_id, nome)
VALUES ('tenant-b', 'privado B inserido por A'); -- policy violation

UPDATE farms.rls_probe_catalog SET tenant_id='tenant-b'
WHERE nome='privado A' RETURNING *; -- policy violation via WITH CHECK
```

Cada comando que produziu erro de RLS foi seguido de `ROLLBACK`. UPDATE/DELETE globais retornaram zero linhas e a transação foi commitada sem alterar o registro. Uma sessão runtime nova, antes de definir contexto, mostrou `current_setting('app.current_tenant_id', true)` vazio e leu somente `catálogo global`.

| Cenário | Esperado | Observado | Resultado |
|---|---|---|---|
| Contexto A lê catálogo | Global + privado A | Global, `privado A`, `privado A 01e2` | **PASS** |
| Contexto B lê catálogo | Global + privado B | Global + `privado B`; sem linha A | **PASS** |
| Sem contexto em sessão runtime nova | Somente global | Contexto exibido vazio; somente `catálogo global` | **PASS** |
| A insere linha privada A | Permitido | `INSERT 0 1`; linha visível para A após commit | **PASS** |
| A insere linha privada B | Negado | Violação de RLS; rollback | **PASS** |
| A transfere linha privada A para B | Negado por WITH CHECK | `new row violates row-level security policy`; rollback | **PASS** |
| A atualiza/exclui linha global | Sem linha alvo mutável | `UPDATE 0`, `DELETE 0`; global permaneceu visível e inalterado | **PASS** |
| A insere linha global (`tenant_id NULL`) | Negado | Violação de RLS; rollback | **PASS** |

## 6. Matriz consolidada PASS/FAIL

| Teste solicitado | Resultado | Evidência principal |
|---|---|---|
| Integridade da fixture existente, sem recriação | **PASS** | Gate `to_regclass`, owner, colunas, PK, policy e RLS/FORCE consultados antes do DDL. |
| INSERT válido + COMMIT | **PASS** | Marker id 4 persistiu e foi encontrado em nova transação A. |
| INSERT válido + ROLLBACK | **PASS** | Marker id 5 não apareceu na transação A seguinte. |
| Contexto encerrado após COMMIT | **PASS** | `NULLIF(current_setting(...), '') IS NULL`; consulta privada sem contexto = zero. |
| Contexto encerrado após ROLLBACK | **PASS** | Mesmo teste após rollback; marker revertido ausente. |
| Alternância A → B → sem contexto | **PASS** | Teste manual e pool real; cada Tenant viu apenas seu escopo. |
| Reuso após COMMIT/ROLLBACK | **PASS** | Mesmo backend no AsyncEngine unitário; contexto limpo em checkouts seguintes. |
| Comportamento após erro SQL | **PASS** | `division by zero`, rollback, conexão devolvida e reusada sem contexto residual. |
| Pai/filha, FK e policy relacional | **PASS** | A/B veem somente filhos de seus pais; consulta cruzada vazia e insert cruzado negado. |
| Catálogo global/misto | **PASS** | Global legível por A/B/sem contexto; linhas privadas isoladas. |
| Escrita global por runtime comum | **PASS** | UPDATE/DELETE global sem linha elegível; INSERT NULL negado. |
| Escrita privada por Tenant | **PASS** | INSERT próprio A confirmado; INSERT B e troca A→B negados sob contexto A. |
| Runtime sem bypass/superuser/ownership | **PASS** | Consulta atual: LOGIN=t, SUPERUSER=f, BYPASSRLS=f, CREATEDB=f, CREATEROLE=f, sem membership de owner; owner da tabela é distinto. DDL foi feita separadamente como deploy/owner. |

Não houve FAIL inesperado. Os erros de RLS e o erro de divisão por zero foram resultados negativos intencionais previstos nos cenários e terminaram com rollback.

## 7. Limitações e ressalvas

- O mecanismo foi exercitado em tabelas sintéticas no PostgreSQL 16; nenhuma policy ou tabela real do DeepFarms foi avaliada nesta fase.
- O harness AsyncEngine comprova reuso de uma conexão em pool unitário. Não cobre pool da aplicação, concorrência, múltiplos processos, cancelamento, retries ou workers.
- O Tenant foi definido manualmente por `SET LOCAL`/`set_config` no SQL de teste. Custom GUC pode ser definido por uma sessão SQL com acesso direto; esta prova não demonstra que a aplicação obtenha o Tenant de JWT/associação confiável, valide authorization ou impeça um cliente de escolher arbitrariamente o GUC.
- Não foram testados helper transacional da aplicação, API, workers, queries sem contexto em todo o produto, funções/triggers, catálogos reais, outras tabelas filhas ou os 350 objetos inventariados em 01C.
- As linhas de teste commitadas permanecem no laboratório: marker `01e2_commit_20261031_01` em `rls_probe` e `privado A 01e2` em `rls_probe_catalog`, além das sementes A/B e global. Os casos de rollback/negação não deixaram linhas novas. Nenhuma limpeza destrutiva foi executada.
- O log detalhado é este relatório. O harness de pool foi temporário em `/tmp`; nenhum segredo ou senha foi gravado nele ou neste relatório.

## 8. Próximo passo indispensável

Validar no laboratório o helper transacional e o pool efetivamente usados pela aplicação, incluindo origem confiável do Tenant. Até essa prova, manter esta conclusão restrita às fixtures sintéticas; não liberar cutover nem declarar o DeepFarms integralmente protegido por RLS.
