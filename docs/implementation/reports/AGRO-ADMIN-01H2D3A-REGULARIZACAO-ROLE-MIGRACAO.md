# AGRO-ADMIN-01H2D3A — Regularização da Identidade de Migração

**Data:** 2026-10-25

**Laboratório:** `dbdcc24872aa2992`

**Escopo:** role de migração e ACLs exclusivamente no cluster dedicado do laboratório

**Veredicto:** **GO COM RESSALVAS para identidade/configuração; baseline continua aguardando autorização separada**

## 1. Identidade do laboratório

| Campo | Evidência |
|---|---|
| Raiz | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992` |
| PostgreSQL | `16.15 (Ubuntu 16.15-1.pgdg22.04+2)` |
| Endpoint | `127.0.0.1:5433` (`inet_server_addr()` retorna `127.0.0.1/32`) |
| PID/PGDATA | PID `1447173`; `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data`, confirmado por `pg_ctl status` |
| Database descartável | `agro_hml_dbdcc24872aa` |
| Owner preservado | `agro_hml_owner_dbdcc24872aa` |
| Role de aplicação | `agro_hml_dbdcc24872aa` |
| Gate de configuração/identidade existente | **PASS** antes da regularização; identidade repetida depois para confirmar que a role de aplicação e Redis continuam funcionais. |

O cluster é o da raiz exclusiva indicada. A consulta de catálogo encontrou apenas os databases do cluster dedicado: alvo, `postgres`, `template0` e `template1`. Não houve conexão a `192.168.0.2`, RDS ou serviços comerciais.

## 2. Diagnóstico de privilégios e requisitos da baseline

Antes da alteração, o role owner `agro_hml_owner_dbdcc24872aa` era `SUPERUSER` e tinha `CREATEDB`, `CREATEROLE`, `REPLICATION` e `BYPASSRLS`. Ele não é apropriado para executar a baseline porque seus poderes não ficam limitados ao database, embora seja o owner do alvo.

A inspeção de `20260908_baseline_deepfarms_v1.py` e `migrations/env.py` concluiu que a baseline não depende de superuser. O papel de execução precisa:

- conectar no database alvo;
- ter `CREATE` no database para criar o schema `farms`;
- ser owner do schema/objetos que criar para emitir ENUMs, sequences, tabelas, FKs, índices, funções, triggers, RLS e policies; os objetos criados sob sua sessão ficam sob seu ownership;
- usar `plpgsql`, linguagem trusted disponível no PostgreSQL, sem `CREATE EXTENSION` ou privilégio elevado;
- criar `farms.alembic_version` no schema configurado pelo `env.py`.

O contrato usa `PUBLIC` nas policies; não há role extra exigida para compilar as policies. A baseline não executa seed/DML direto; INSERT/UPDATE aparece nos corpos das funções de trigger para operações futuras. Os três triggers e três funções são DDL. O `downgrade()` contém DROP destrutivo, mas não foi executado. Não foi identificado acesso externo na revisão.

`FORCE ROW LEVEL SECURITY` é aplicável pelo owner da tabela sem superuser. O papel de migração será owner dos objetos que criar e não terá `BYPASSRLS`; o ownership ainda permite alterar DDL dos objetos próprios, portanto essa credencial deve ser usada somente em operação de migração aprovada e mantida separada da aplicação.

## 3. Role criada e permissões

Foi criada a role sintética exclusiva **`agro_hml_migrate_dbdcc24872aa`** com:

```text
LOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE,
NOREPLICATION, NOBYPASSRLS, CONNECTION LIMIT 5
```

Não pertence a grupos e não recebe membership de outra role. O role administrativo preexistente permaneceu intacto, com os mesmos atributos e ownership do database.

Grants diretos à role nova:

| Database | CONNECT | CREATE | TEMP | Observação |
|---|---:|---:|---:|---|
| `agro_hml_dbdcc24872aa` | Sim | Sim | Não | Concessão estritamente para o alvo. O database continua pertencendo à role admin. |
| `postgres` | Não | Não | Não | Conexão pública revogada no cluster de laboratório. |
| `template1` | Não | Não | Não | Conexão pública revogada no cluster de laboratório. |
| `template0` | Não | Não | Não | Privilégios públicos revogados; adicionalmente `datallowconn=false`. |

O database alvo tinha `TEMP` concedido a `PUBLIC`; esse privilégio foi revogado no alvo porque a baseline não o requer. Busca estática no código não encontrou uso de `CREATE TEMP/TEMPORARY TABLE`. A role da aplicação mantém seu `CONNECT` direto no alvo, não recebeu `CREATE` ou membership da role de migração, e passou novamente pelo gate de identidade.

Para que a role não herde acesso padrão a outros databases do cluster, foram removidas as ACLs de `PUBLIC` em `postgres`, `template0` e `template1`, todos internos ao cluster descartável. Essas alterações não alcançam bancos externos ao laboratório. A role admin é superuser e continua capaz de administrar o cluster.

**Ownership do alvo não foi alterado.** O grant `CREATE` no database é suficiente para a role criar `farms`; ela será owner do schema e dos objetos da baseline, sem ser owner do database nem receber poderes sobre outros databases.

## 4. Configuração privada Alembic

Foi criado `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/config/alembic-migration.env`, modo **`0600`**, contendo o ambiente sintético do laboratório com somente `DATABASE_URL` substituída pela URL da nova role. As demais variáveis coincidem com `api1.env`; provedores continuam sem credenciais. O valor da senha não aparece em logs, argumentos de processo, manifesto ou relatório.

A configuração aponta exclusivamente para `postgresql+asyncpg://…@127.0.0.1:5433/agro_hml_dbdcc24872aa`. O gate verifica modo, conjunto/valores das variáveis, role derivada do ID do laboratório, database, host e porta. O `migrations/env.py` lê `DATABASE_URL` do ambiente do processo; uma futura execução deve carregar somente esta configuração sintética em ambiente limpo. `agro_labctl.py migrate` continua bloqueado; nenhum comando de execução foi preparado ou liberado aqui.

## 5. Gate e testes

Foi estendido `scripts/homologacao/agro_labctl.py` com o subcomando `migration-identity`. Ele primeiro passa pela validação existente das configs e depois exige:

- role autenticada igual à derivada do ID; `session_user=current_user`;
- database/porta/loopback exatos;
- role login sem superuser, createdb, createrole, replication, bypassrls, inheritance ou memberships;
- ownership do database ainda com `agro_hml_owner_dbdcc24872aa`;
- `CONNECT` e `CREATE`, sem `TEMP`, no database alvo;
- nenhuma permissão efetiva CONNECT/CREATE/TEMP em qualquer outro database do cluster;
- role app separada, com CONNECT no alvo, sem CREATE/TEMP e sem membership da role de migração;
- atributos administrativos preexistentes preservados;
- tentativa real de conexão rejeitada em `postgres` e `template1` por ACL e em `template0` por `datallowconn=false`.

Resultado do gate pós-regularização: **PASS**. O gate de identidade da aplicação/Redis também passou.

Foi executado um probe de privilégios apenas em transação com `ROLLBACK`, usando objetos sintéticos num schema `agro_migration_probe_dbdcc24872aa`: schema, ENUM, sequence, tabelas, PK/UNIQUE/CHECK/FK, índice, função PL/pgSQL, trigger, RLS enabled/forced e policy. **Todas as operações passaram e o rollback removeu o schema.** A consulta final confirmou zero relações, funções e tipos de usuário, ausência de `farms`, `farms.alembic_version` e do schema de probe.

Validações de código do gate:

- `services/api/.venv/bin/pytest scripts/homologacao/test_agro_labctl.py -q`: **29 passed**.
- Ruff para `agro_labctl.py` e `test_agro_labctl.py`: **PASS**.
- Verificação de espaços finais e newline nos dois arquivos do gate e neste relatório: **PASS**.

## 6. Arquivos e estado do database

Arquivos do repositório alterados nesta fase:

- `scripts/homologacao/agro_labctl.py`: validador e subcomando de identidade least-privilege.
- `scripts/homologacao/test_agro_labctl.py`: testes de URL/role, permissões, máscaras e separação.
- Este relatório.

Artefatos privados do laboratório:

- `config/alembic-migration.env` — modo 0600, contém a URL e segredo sintético;
- `config/manifest.json` — atualizado sem credenciais em claro, com estado da role e resultados.

O database permanece vazio de objetos do produto. Nenhuma baseline, migration, `stamp`, downgrade ou DDL de aplicação foi executado. O DDL transacional descrito acima foi sintético e totalmente revertido.

## 7. Riscos e limitações

- O schema real, constraints completas, funções/triggers de produto, `alembic_version` e compatibilidade ORM ainda não foram provados pela baseline.
- As verificações de RLS cobriram somente a capacidade de criar RLS/FORCE/policy em DDL transacional; não testaram isolamento de dois tenants nem operações da aplicação.
- A role migradora poderá alterar/remover seus próprios objetos e schema durante uma futura migração. Não a usar na API nem persistir a credencial fora do laboratório.
- Os ACLs ajustados de `PUBLIC` afetam apenas os databases internos deste cluster isolado. A role administrativa superuser conserva acesso.
- O caminho de instalação até o head continua bloqueado por AGRO-ADMIN-01H2C2; esta regularização não classifica as 408 revisões históricas nem cria ponte Alembic.

## 8. Veredicto

**GO COM RESSALVAS para a identidade de migração do laboratório.** Role, grants, ownership, isolamento de outros databases, configuração privada e capacidade DDL não-superuser foram comprovados. A role administrativa existente não foi modificada.

**A execução de `baseline_deepfarms_v1` permanece pendente de autorização separada.** Nenhuma migration ou DDL de aplicação foi iniciada; encerrar nesta regularização.
