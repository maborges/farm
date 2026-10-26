# AGRO-ADMIN-01H2D3F — Validação do Provisionamento de Identidades PostgreSQL

**Data:** 2026-10-25  
**Modalidade:** provisionamento controlado; sem migrations  
**Veredicto inicial:** NO-GO enquanto a execução estava restrita ao sandbox.  
**Veredicto de fechamento:** **GO para encerrar a preparação de identidades do laboratório**

## 1. Identidade do cluster

O preflight e a verificação final identificaram o cluster autorizado:

| Propriedade | Valor observado |
|---|---|
| Host/porta | `127.0.0.1:5433` |
| PostgreSQL | `16.15 (Ubuntu 16.15-1.pgdg22.04+2)` |
| PGDATA | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` |
| Owner administrativo do laboratório | `agro_hml_owner_dbdcc24872aa` |
| Database novo | `agro_hml_dbdcc24872aa_d3f` |
| Raiz de configuração exclusiva | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3f` |

O PID e o `postmaster.pid` foram comparados ao manifesto do laboratório pelo provisionador. O listener observado foi restrito a `127.0.0.1:5433`. Nenhuma conexão foi feita ao PostgreSQL compartilhado ou ao RDS.

## 2. Database e role provisionados

O database D3F foi confirmado inexistente antes da criação e criado exclusivamente no cluster acima, com owner administrativo sintético. O catálogo permaneceu sem schema `farms`, tabelas, views ou sequences de aplicação. Não foram criados DDL da aplicação, dados, baseline ou revisão Alembic.

Role exclusiva criada:

`agro_hml_mig_dbdcc24872_agrohmldbdcc24872aad_c29db45af02e66f8`

Os atributos observados foram: `LOGIN`, `NOINHERIT`, `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`, sem memberships. A role possui `CONNECT` e `CREATE` somente em D3F e não possui `TEMP`. As verificações efetivas retornaram `CONNECT/CREATE/TEMP = false/false/false` para os dois databases anteriores. As credenciais da role ficaram em `config/alembic-migration.env`, modo `0600`; o arquivo administrativo sintético também está em `0600`. Segredos e DSNs não foram registrados.

O papel de aplicação existente recebeu apenas `CONNECT` em D3F; `CREATE` e `TEMP` permaneceram falsos. `PUBLIC` não recebeu `CONNECT` nem `TEMP` no alvo.

## 3. Preservação dos databases anteriores

As consultas finais foram somente de leitura. Os valores observados conferem com o estado conhecido das provas anteriores:

| Database | Owner | Tabelas/partições em `farms` | Sequences em `farms` | Revisão | OID do schema `farms` |
|---|---|---:|---:|---|---:|
| `agro_hml_dbdcc24872aa` | `agro_hml_owner_dbdcc24872aa` | 349 | 65 | `baseline_deepfarms_v1` | 16425 |
| `agro_hml_dbdcc24872aa_d3d` | `agro_hml_owner_dbdcc24872aa` | 349 | 33 | `baseline_deepfarms_v1` | 25418 |
| `agro_hml_dbdcc24872aa_d3f` | `agro_hml_owner_dbdcc24872aa` | 0 | 0 | ausente | ausente |

Os dois bancos anteriores não foram alterados. Nenhum database foi removido.

## 4. Gates e verificações

| Verificação | Resultado | Evidência/limite |
|---|---|---|
| Identidade do cluster durante provisionamento | PASS | O provisionador confirmou versão, endpoint, PGDATA, PID e owner do alvo. |
| Database novo vazio | PASS | Zero objetos de aplicação e ausência de schema `farms`. |
| Provisionamento da role por database | PASS | Provisionador concluiu; grants efetivos e role foram conferidos no catálogo. |
| `agro_labctl.py migration-identity` | PASS | Foi executado pelo provisionador após criar a credencial. Confirmou autenticação, escopo D3F, atributos e rejeição de databases não autorizados. |
| Login da role de aplicação no alvo | PASS isolado | Uma consulta `psql` direta autenticou no D3F e identificou usuário, database e endpoint esperados. |
| `agro_labctl.py identity` dentro do sandbox | NO-GO | O sandbox não permitiu acesso ao loopback; `pg_isready` reportou ausência de resposta e conexão direta retornou `PermissionError`. |
| `agro_labctl.py identity` fora do sandbox | **PASS** | PostgreSQL e Redis responderam; os identificadores conferem. |
| `agro_labctl.py migration-identity` fora do sandbox | **PASS** | Role autenticada; privilégios efetivos e databases não autorizados conferem. |
| Testes automatizados do controlador | **PASS** | `test_agro_labctl.py`: 45 testes passaram. |
| Ruff | **PASS** | Todos os arquivos do controlador e provisionador inspecionados passaram. |
| `py_compile` | **PASS** | Todos os arquivos Python do controlador, guard e provisionador compilaram. |
| `git diff --check` | RESSALVA externa | Reportou uma linha em branco no EOF preexistente em `services/api/core/routers/backoffice_sessions.py:170`; arquivo fora do escopo desta correção e não alterado. |

### Diagnóstico e fechamento

A comparação do `cmd_identity` com a conexão direta não identificou divergência de usuário, database, host, porta, arquivo privado ou senha. As variáveis usuais de conexão PostgreSQL herdadas (`PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGSERVICE`, `PGSERVICEFILE`, `PGOPTIONS`, `PGSSLMODE` e equivalentes verificadas) estavam ausentes. A falha ocorria porque o processo de validação estava dentro do sandbox, que não tinha permissão para acessar os serviços no loopback. A mensagem genérica do controlador ocultou a restrição do ambiente; não houve defeito de seleção de configuração ou autenticação.

Sem alterar código, roles, grants ou serviços, os dois gates foram executados fora do sandbox, com acesso ao loopback já autorizado para esta validação. `identity` passou nas verificações PostgreSQL e Redis; `migration-identity` confirmou a role exclusiva D3F e a negação de acesso aos outros databases. Portanto, nenhuma correção de controlador era necessária. Não foi enfraquecido nem contornado qualquer controle.

## 5. Artefatos e comandos operacionais

O provisionador existente `scripts/homologacao/provision_migration_identity.py` foi executado anteriormente com confirmação explícita do database D3F e produziu a credencial privada da role. Nesta etapa de fechamento, o provisionamento não foi repetido. Os comandos oficiais `identity` e `migration-identity` foram executados com acesso de rede ao loopback e concluíram com PASS.

O workspace já continha numerosas alterações e arquivos não rastreados antes desta tarefa. Elas foram preservadas. Este relatório é o único artefato criado no repositório nesta fase; nenhum teste de aplicação foi executado. Arquivos diagnósticos temporários foram mantidos fora do repositório, em `/tmp`.

Não foi criado `migration-approval.json`. Não houve migration, `stamp`, downgrade, DDL de aplicação, inicialização de serviços, alteração dos bancos anteriores, deploy ou operação Git de escrita.

## 6. Bloqueios e riscos remanescentes

1. `git diff --check` continua apontando a linha em branco no EOF de `services/api/core/routers/backoffice_sessions.py:170`, não relacionada ao laboratório e não alterada nesta tarefa.
2. A role migradora tem DDL permitido (`CREATE`) apenas no database novo; isso não autoriza migrations. Os databases anteriores e o D3F permanecem preservados.

## 7. Estado final e escopo de fechamento

O estado final dos três databases foi conferido somente por leitura: D3F continua vazio e sem revisão Alembic; os dois bancos anteriores mantêm as respectivas contagens, OIDs do schema `farms` e revisão `baseline_deepfarms_v1` já registradas. A role migradora continua exclusiva de D3F, sem memberships, privilégios globais ou `TEMP`, e com `CONNECT`/`CREATE` apenas no alvo. Nenhum `migration-approval.json` foi criado.

Não houve alteração de código nesta correção, pois a causa foi a restrição de loopback do sandbox, não o controlador. Também não houve migration, baseline, `stamp`, downgrade, API, Backoffice, PWA, deploy, commit, push ou merge.

**Veredicto final: GO para encerrar a preparação de identidades e a validação operacional da infraestrutura do laboratório.** Este resultado não aprova nem inicia migrations ou homologação integrada.
