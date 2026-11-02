# DEEPFARMS-RLS-HOSTINGER-01E — Prova de Isolamento em Laboratório

**Data da retomada:** 2026-10-31
**Status:** BLOQUEADO para execução pelo Codex — sessão administrativa local do operador não está acessível neste executor
**Base lida:** relatórios 01C, 01D, 01E e 01E0; preflight somente leitura no PostgreSQL de desenvolvimento

## 1. Resultado executivo

A autorização para criar `deepfarms_rls_lab` e roles específicas foi considerada. O destino efetivo foi confirmado novamente como PostgreSQL de desenvolvimento em `192.168.0.2:5432`, database/schema `farms`; o usuário efetivo é `borgus`, PostgreSQL 16.15. A consulta de catálogo confirmou que o database `deepfarms_rls_lab` ainda não existe e que os nomes exclusivos de roles propostos estão livres.

A execução do Codex continua sem DDL/DML. A role `admin_farms` foi revalidada por catálogo: `BYPASSRLS=true`, `CREATEDB=false`, `CREATEROLE=false`, com membership herdável em `borgus`; não consegue provisionar e não serve como runtime da prova. Uma tentativa TCP do Codex como `postgres` para `192.168.0.2:5432` foi recusada (`28P01`). Em seguida, o operador forneceu saída de uma sessão que abriu no próprio servidor: `current_database=postgres`, `current_user=session_user=postgres`, PostgreSQL `16.15`, `inet_server_addr()` e porta nulos. Isso é compatível com conexão por socket Unix local; não demonstra uma sessão TCP de `192.168.0.2` acessível a este executor. A senha não foi incluída em comando, arquivo ou relatório. O operador tem caminho administrativo local, mas essa sessão não é controlável pelo Codex.

**Nenhum banco, role, tabela, grant ou policy foi criado ou alterado. Nenhum teste RLS ou de escrita foi executado.** O database `farms`, o schema `tara` e a Hostinger não foram modificados nem receberam DDL/DML. As consultas de preflight foram somente leitura, dentro de transação `READ ONLY`.

**Veredicto nesta execução: NO-GO para iniciar a prova até um operador disponibilizar uma sessão administrativa autenticada ou executar o provisionamento mínimo da seção 6.** O comportamento RLS permanece **não testado**; não há resultado PASS/FAIL funcional.

## 2. Ambiente e evidência da interrupção

| Gate de provisionamento | Evidência observada | Resultado |
|---|---|---|
| Servidor/endpoint autorizado | Endpoint efetivo configurado `192.168.0.2`; porta retornada `5432`; responsável já confirmou o host como desenvolvimento | Identidade aceita para este escopo. |
| Identidade da conexão | DB/schema `farms`/`farms`; `current_user=session_user=borgus`; PostgreSQL `16.15` | Confere com o servidor e database existentes explicitamente autorizados para o preflight. |
| Interface reportada pelo servidor | `172.26.132.19/32` | Difere do endpoint configurado; mapeamento de rede não foi inspecionado. A evidência de destino é a configuração confirmada e a declaração do responsável. |
| Existência de `deepfarms_rls_lab` | Nenhuma linha para o nome em `pg_database` | Não existe no momento do preflight; portanto não há database preexistente a sobrescrever. |
| Colisão de roles planejadas | Nenhuma linha para `deepfarms_rls_lab_owner`, `deepfarms_rls_lab_deploy`, `deepfarms_rls_lab_runtime` em `pg_roles` | Nomes livres no momento do preflight. |
| Capacidade da identidade configurada | `borgus`: `LOGIN=true`, `SUPERUSER=false`, `BYPASSRLS=false`, `CREATEDB=false`, `CREATEROLE=false` | Incapaz de criar o database e as roles; não foi tentado DDL. |
| Role `admin_farms` fornecida pelo responsável | `LOGIN=true`, `SUPERUSER=false`, `BYPASSRLS=true`, `CREATEDB=false`, `CREATEROLE=false`; membership herdável em `borgus` | Não consegue provisionar DB/roles e é inadequada como runtime; a senha não foi testada nem repetida. |
| Role `postgres` / caminhos de autenticação | TCP do Codex para `192.168.0.2:5432` recusou autenticação (`28P01`); operador forneceu saída da sessão local: DB `postgres`, `current_user=session_user=postgres`, versão `16.15`, endereço/porta nulos | O operador tem uma sessão administrativa local, compatível com socket Unix. A sessão não é compartilhada com este executor e não confirma o caminho TCP. |
| Fontes locais de credencial administrativa adicional | `.env.local` tem somente a chave `DATABASE_URL`; não existem `.pgpass`/`.pg_service.conf` no home nem variáveis de ambiente administrativas correspondentes | Não foi encontrada outra credencial. Os valores secretos não foram lidos/impressos. |
| Hostinger | Sem conexão ou comando | Não acessada. |

As consultas do Codex ao PostgreSQL foram de identidade e catálogo, sempre em transação `READ ONLY`. O login TCP como `postgres` falhou antes de abrir sessão SQL; a saída da sessão local veio do operador e não executou comandos por este agente. Não foram executados `CREATE`, `ALTER`, `GRANT`, `REVOKE`, DML, migrations, comandos Docker ou conexões à Hostinger.

## 3. Implementação experimental

**Nenhuma implementação experimental foi iniciada.** Não há helper, módulo, fixture, role, schema, policy ou grants criados. O helper proposto no 01D continua apenas proposta: `set_config('app.current_tenant_id', ..., true)` com bind parameter, aplicado em cada transação protegida.

Também não foram alterados os arquivos funcionais previstos no 01D (`core/database.py`, `core/dependencies.py`, API, workers, migrations, Compose ou configuração). Isso evita deixar código de laboratório sem uma base PostgreSQL isolada para validar o comportamento.

### Fixture mínima prevista para quando o ambiente estiver disponível

As seguintes tabelas são candidatas representativas com base no inventário 01C e no contrato ORM; esta seleção é planejamento, não evidência de teste executado:

| Classe de teste | Candidata | Motivo e limite |
|---|---|---|
| Tenant-private com RLS existente | `tenant_integracoes` | Tabela direta por Tenant, presente no conjunto atual com RLS; usar somente colunas e valores sintéticos. |
| Tenant-private sem RLS | `tenant_audit_log` | Candidata direta com `tenant_id` e sem RLS no inventário. Criar estrutura mínima compatível e validar os grants/policy da fixture. |
| Filha relacional | `cadastros_pessoas_pii` → `cadastros_pessoas` | Exemplo de filha sem `tenant_id` direto apontando a pai tenant-scoped. Criar pai e filha sintéticos e policy relacional explícita. |
| Catálogo global/misto | `cadastros_produtos` | Preserva leitura global e registros próprios; criar ao menos duas linhas globais sintéticas e linhas privadas A/B. O snapshot Hostinger tinha produtos globais, mas isso não substitui a fixture de laboratório. |

O banco de laboratório deverá ser descartável e sem bind mount de dados, credenciais ou diretórios da Hostinger. Um schema reduzido compatível apenas com estas quatro classes comprova o comportamento do PostgreSQL e do helper; não comprova por si só o mapeamento completo de ORM, todos os relacionamentos ou o conjunto de 350 tabelas.

## 4. Testes e resultados

| Teste / gate | Resultado | Evidência ou motivo |
|---|---|---|
| Conexão ao servidor de desenvolvimento autorizado | **PASS — somente preflight** | Endpoint configurado `192.168.0.2:5432`; database/schema corrente `farms`; usuário `borgus`; PostgreSQL 16.15. Interface reportada: `172.26.132.19/32`, sem mapeamento independente. |
| Banco `deepfarms_rls_lab` ausente | **PASS — somente preflight** | Catálogo não encontrou database com esse nome. Nenhum banco foi criado. |
| Nomes das roles de laboratório livres | **PASS — somente preflight** | Catálogo não encontrou as três roles propostas. Nenhuma role foi criada. |
| Identidade administrativa disponível ao Codex | **FAIL / bloqueador de execução remota** | `borgus` e `admin_farms` não têm `CREATEDB`/`CREATEROLE`; `admin_farms` tem `BYPASSRLS`; login TCP de `postgres` recusado. O operador demonstrou uma sessão local administrativa, mas ela não é acessível ao executor. |
| Identidade das roles (`rolsuper`, `rolbypassrls`, owner e memberships) | **NOT RUN** | As roles de laboratório ainda não existem. |
| Helper parametrizado e aplicação por transação | **NOT RUN** | Nenhum SQL de fixture/helper nem alteração de código foram executados. |
| SELECT A/B e contexto ausente | **NOT RUN** | Dependem de role restrita e fixture sintética. |
| INSERT/UPDATE/DELETE cruzado | **NOT RUN** | Nenhum teste de escrita foi executado em qualquer banco. |
| Commit, rollback e nova transação | **NOT RUN** | Nenhuma sessão/conexão de teste com Tenant foi aberta. |
| Reutilização da conexão/pool sem vazamento de GUC | **NOT RUN** | Pool local da aplicação não foi ligado a banco de teste. |
| Leitura de produto global e escrita global negada ao Tenant | **NOT RUN** | Sem policies/grants de laboratório nem linhas sintéticas. |
| Leitura/escrita em filha relacional com pai de outro Tenant | **NOT RUN** | Nenhuma estrutura sintética de FK/policy foi criada. |
| API/workers usando papel restrito | **NOT RUN** | Os serviços não foram executados contra laboratório. |

`FAIL` aplica-se somente ao gate de identidade administrativa. Os `PASS` são pre-checks de catálogo, não provas de isolamento. `NOT RUN` significa que o cenário não foi executado; não deve ser interpretado como PASS ou como falha funcional do produto.

## 5. Dependências estáticas que impediriam adoção direta

Na leitura do código associada ao 01D, já existem pontos que exigem mudanças antes de operar com o novo runtime. São dependências estáticas; não foram confirmadas em execução neste laboratório:

- `core.database.get_db()` e `get_db_session()` criam sessões sem instalar automaticamente `app.current_tenant_id`; consumidores precisam classificar o escopo antes da primeira query.
- `core.dependencies.get_session()` usa `_activate_session_tenant()` com `SET LOCAL`. O contexto termina no commit/rollback e há reativação explícita em caminhos selecionados, não prova para todos os commits internos.
- `events.outbox_service.claim_batch()` permite `tenant_id=None`, removendo o filtro tenant explícito. Sob RLS restrito, o dispatcher precisa descobrir o trabalho sem expor payloads e cada claim/handler deve operar por Tenant.
- `automacoes/worker.py` busca configurações vencidas globalmente e depois chama serviço com `cfg.tenant_id`; precisa separar enumeração do processamento tenant-scoped.
- `recommendations/scheduler.py` e `integracoes/erp/scheduler.py` usam `set_config(..., false)` e limpeza `RESET`/invalidação. Um GUC de sessão não é equivalente ao contexto local exigido; commit interno, erro e cancelamento devem ser cobertos.
- Os workers e API usam uma factory de engine por processo. O código tem `pool_size=3` e `max_overflow=2`; cada processo requer credencial própria ou matriz aprovada e prova de que conexões reutilizadas não carregam contexto anterior.
- O Compose versionado local compartilha o mesmo env_file nos quatro serviços. O Compose efetivo da Hostinger não está neste checkout e não foi acessado; o teste de role por processo depende de uma configuração local isolada e sintética.
- Os testes E2E atuais e a fixture `tenant_context.py` não demonstram, por si só, RLS sob role não-owner sem BYPASSRLS; a fixture existente define GUC de escopo de sessão. A prova precisa conectar explicitamente com runtime role restrita e verificar flags/ownership antes dos cenários.

## 6. Comandos mínimos para o operador

O operador já demonstrou uma sessão local como `postgres` no servidor. Para concluir sem compartilhar senha, execute os comandos abaixo nessa sessão local ou disponibilize ao executor um canal remoto aprovado que use a mesma identidade de desenvolvimento e permita autenticação sem registrar segredo. A role `admin_farms` não possui `CREATEDB`/`CREATEROLE` e tem `BYPASSRLS`; não a usar para provisionar nem testar runtime. `borgus` também não pode executar os comandos abaixo. Nenhum deles foi executado pelo Codex.

### 6.1. Conexão e repetição do gate

```bash
psql -h 192.168.0.2 -p 5432 -U <ROLE_ADMIN_AUTORIZADA> -d farms -W -v ON_ERROR_STOP=1
```

Dentro do `psql`, confirme identidade/versão e repita as verificações imediatamente antes de criar qualquer objeto:

```sql
SELECT current_database(), current_user, session_user,
       inet_server_port(), current_setting('server_version');

SELECT datname FROM pg_database
WHERE datname = 'deepfarms_rls_lab';

SELECT rolname FROM pg_roles
WHERE rolname IN ('deepfarms_rls_lab_owner',
                  'deepfarms_rls_lab_deploy',
                  'deepfarms_rls_lab_runtime');
```

Se o database ou qualquer role já existir, interromper sem apagar, renomear ou sobrescrever. Confirmar que a sessão é `192.168.0.2:5432`, database `farms`, ambiente de desenvolvimento. Não usar a sessão para executar migrations.

### 6.2. Provisionamento autorizado, somente após o gate

Este bloco é uma instrução para o operador autenticado, não uma execução feita pelo Codex. `CREATE DATABASE` deve ser executado fora de uma transação explícita. Os nomes estavam livres no preflight, mas o operador precisa repetir o gate.

```sql
CREATE ROLE deepfarms_rls_lab_owner
  NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE deepfarms_rls_lab_deploy
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE deepfarms_rls_lab_runtime
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

GRANT deepfarms_rls_lab_owner TO deepfarms_rls_lab_deploy;

CREATE DATABASE deepfarms_rls_lab
  OWNER deepfarms_rls_lab_owner
  TEMPLATE template0;
```

Definir senhas somente pelo prompt interativo do `psql` (`\password deepfarms_rls_lab_deploy` e `\password deepfarms_rls_lab_runtime`), sem colocá-las nos comandos ou histórico. O runtime não recebe membership. A membership deploy → owner permite ao deploy assumir explicitamente a role owner para DDL no laboratório; o deploy não deve ser usado em API/worker.

No database novo, restringir o uso do database e criar o schema isolado:

```sql
\connect deepfarms_rls_lab
REVOKE CONNECT, TEMPORARY ON DATABASE deepfarms_rls_lab FROM PUBLIC;
GRANT CONNECT ON DATABASE deepfarms_rls_lab
  TO deepfarms_rls_lab_deploy, deepfarms_rls_lab_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA farms AUTHORIZATION deepfarms_rls_lab_owner;
GRANT USAGE ON SCHEMA farms TO deepfarms_rls_lab_runtime;
```

Não conceder privilégios aos papéis do laboratório em `farms` ou `tara`, nem criar objetos nesses schemas. Antes das fixtures, o DBA deve verificar privilégios efetivos herdados de `PUBLIC` em ambos os schemas (tabelas, sequences, funções e `CREATE`). O comparativo 01E0 registrou `PUBLIC USAGE` no schema `farms` e ACL `proacl NULL` nas funções locais; isso pode resultar em `EXECUTE` efetivo de `PUBLIC` e precisa ser confirmado para as novas roles. Se encontrar privilégio efetivo em objeto existente, parar: `REVOKE` específico ao novo papel não cancela concessão herdada de `PUBLIC`. Remover concessões herdadas exigiria alterar ACLs existentes de `farms`/`tara` ou a configuração de acesso do servidor, fora desta autorização. `CONNECT` ao database deve ser reportado separadamente; não equivale, por si só, a privilégio de leitura/escrita nos objetos.

Após provisionar e validar o laboratório, a continuação deve conectar diretamente ao database novo como deploy, criar somente as fixtures sintéticas, aplicar grants/policies restritos e realizar todos os testes como runtime. Preservar o laboratório para inspeção posterior; não executar `DROP DATABASE` ou `DROP ROLE` automaticamente.

## 7. Recomendação

**NO-GO para a execução pelo Codex nesta sessão**, pois a única rota administrativa demonstrada é um socket local acessível no servidor ao operador, enquanto o executor não dispõe de sessão remota autenticada; a tentativa TCP foi recusada. **GO para o operador provisionar localmente** usando a sessão `postgres` demonstrada e os comandos da seção 6, após repetir os gates de database/roles. A autorização cobre o laboratório, mas não transforma `admin_farms` em identidade de provisionamento nem em runtime segura. Nenhum DDL/DML foi executado.

**GO para retomar após o operador/DBA executar ou disponibilizar o provisionamento da seção 6 e confirmar que as roles runtime não recebem acesso efetivo a objetos de `farms`/`tara`.** O database `farms`, o schema `tara`, a Hostinger e o código funcional permanecem intactos. Até que os cenários sejam executados como runtime restrito, nenhum resultado de isolamento é PASS e o critério de sucesso da 01E permanece não demonstrado.
