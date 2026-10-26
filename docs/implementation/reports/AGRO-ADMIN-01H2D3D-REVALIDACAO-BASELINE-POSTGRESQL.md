# AGRO-ADMIN-01H2D3D — Revalidação Real da Baseline PostgreSQL Corrigida

**Data:** 2026-10-25  
**Escopo:** aplicação exclusiva de `baseline_deepfarms_v1` em novo database descartável, comparação do catálogo PostgreSQL e probes ORM/RLS com dados sintéticos.  
**Veredicto:** **NO-GO para liberar a baseline/homologação integrada; GO COM RESSALVAS para a correção de sequences e a regressão do catálogo observadas nesta prova.**

## 1. Identidade e isolamento

| Item | Evidência observada |
|---|---|
| Laboratório | `dbdcc24872aa2992` |
| Raiz privada da prova | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3d` (permissão `0700`) |
| Cluster PostgreSQL | PostgreSQL `16.15 (Ubuntu 16.15-1.pgdg22.04+2)`; PID `1447173`; PGDATA `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` |
| Listener | `127.0.0.1:5433`; `inet_server_addr()` retornou `127.0.0.1/32` |
| Novo database | `agro_hml_dbdcc24872aa_d3d` |
| Role usada para baseline | `agro_hml_migrate_dbdcc24872aa` |
| Role de aplicação | `agro_hml_dbdcc24872aa` |
| Database anterior protegido | `agro_hml_dbdcc24872aa` |
| Redis | Redis `6.0.16`, PID `1455955`, `127.0.0.1:6380`; marcador lido correspondeu ao ID do laboratório |

O database novo era inexistente antes da criação e vazio de objetos de aplicação antes da migration. A identidade PostgreSQL foi confirmada imediatamente antes da aplicação. O gate `agro_labctl.py identity` passou na verificação final. Na primeira tentativa, o executável `redis-cli` não estava no `PATH`; a tentativa seguinte encontrou o binário, mas faltava `LD_LIBRARY_PATH` para `liblzf.so.1`. Com o caminho das bibliotecas extraídas e privadas do laboratório, o mesmo gate passou: PostgreSQL e Redis responderam e os identificadores conferiram. Nenhuma instalação sistêmica foi feita.

Não foram herdadas variáveis de conexão do shell: o Alembic foi executado com ambiente limpo construído da configuração sintética privada. Nenhum `.env.local`/`.env.production`, RDS, `192.168.0.2`, provedor comercial, FastAPI ou frontend foi acessado/iniciado.

## 2. Preflight, workspace e revisão aplicada

- A revisão existe, é raiz (`down_revision=None`), não declara dependências e a iteração Alembic para o alvo retornou somente `baseline_deepfarms_v1`.
- O hash SHA-256 de `services/api/migrations/versions/20260908_baseline_deepfarms_v1.py` no preflight e imediatamente antes da execução foi `b32da6be0f5f089c9d75fc2c0da4784e8dccaeb6303be5c03dbc6156c8275fbc`.
- A configuração Alembic privada do alvo estava em modo `0600`; o env e os diretórios do novo laboratório permaneceram privados. A role migradora tinha `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`, `NOINHERIT` e zero memberships.
- Estado do workspace: havia alterações preexistentes não relacionadas. Nesta etapa, nenhum código de aplicação/migration foi editado; foi criado somente este relatório no repositório.

**Limitação de gate:** `agro_labctl.py migration-identity --root ...-d3d` terminou em **NO-GO**, pois classifica o acesso de banco da role migradora fora do alvo como excesso de escopo. A consulta read-only mostrou que a role tem `CONNECT` e `CREATE` no database desta prova e no database descartável anterior; não tem `TEMP`, atributos globais nem memberships. O acesso no database anterior é preexistente e protegido nesta autorização. Não o revoguei nem alterei ACLs do database anterior. Assim, o gate migration-identity não ficou aprovado para o alvo novo. A execução abaixo foi feita após o gate de identidade PostgreSQL/Redis e o gate customizado de identidade/permissões do alvo terem passado, mas **não** após aprovação do gate nominal `migration-identity` para este database. Essa divergência é registrada como bloqueio, não como aprovação implícita.

## 3. Execução da baseline

Comando efetivamente executado, usando exclusivamente a configuração sintética do laboratório e a role migradora:

```text
services/api/.venv/bin/alembic -c services/api/alembic.ini upgrade baseline_deepfarms_v1
```

O processo reportou `Running upgrade -> baseline_deepfarms_v1` e terminou com código `0`. Não foi executado `upgrade head`, `upgrade heads`, `stamp`, downgrade ou revisão histórica. Não houve reparo automático do schema.

## 4. Validação das 33 sequences

A consulta direta ao catálogo PostgreSQL foi reconciliada com o `SEQUENCE_CONTRACT` atualizado no checkout. Resultado: **33/33 correspondências exatas**, sem órfãs, extras, nomes ausentes ou sufixos `seq1`.

| Propriedade | Resultado |
|---|---|
| Quantidade do contrato | 33 |
| Sequences encontradas | 33 |
| Nomes e schemas | 33/33 esperados em `farms` |
| Sequences órfãs/independentes não contratadas | 0 |
| Sufixos inesperados `seq1` | 0 |
| `pg_get_serial_sequence()` | 33/33 aponta para a sequence esperada da coluna |
| Defaults `nextval` | 33/33 correspondem ao nome canônico no schema `farms` |
| Ownership/dependency com coluna | 33/33 corretos |
| Tipos | 32 `SERIAL` (`integer`) e 1 `BIGSERIAL` (`bigint`) |
| Parâmetros de sequence | Início, incremento, limites, cache e ciclo conforme contrato |

`sankhya_sync_logs_id_seq` foi criada uma única vez e pertence a `sankhya_sync_logs.id`. Nenhuma das 32 sequences canônicas de SERIAL foi duplicada. Este é o resultado real PostgreSQL que confirma a correção introduzida na fase 01H2D3C.

## 5. Regressão do catálogo

O snapshot direto do catálogo no database novo registrou:

| Objeto/verificação | Resultado observado |
|---|---:|
| Tabelas de aplicação | 348 |
| Tabelas incluindo `farms.alembic_version` | 349 |
| Colunas de aplicação | 4.767; nomes e conjunto coincidem com metadata ORM |
| `farms.alembic_version` | `baseline_deepfarms_v1` |
| Constraints | 349 PK, 76 UNIQUE, 76 CHECK, 924 FK e 1 trigger de constraint |
| Índices | 1.488 no total: 1.063 ORM, 349 PK e 76 UNIQUE |
| ENUMs | 34; nomes e labels coincidentes |
| RLS | 49 enabled; 48 forced; flags coincidem por tabela com contrato |
| Policies | 188; nomes/roles/comandos e expressões semanticamente coincidentes após normalização de qualificação `farms.` |
| Functions/triggers | 3 funções e 3 triggers presentes; timing/eventos e definições esperadas |

As 924 FKs coincidiram por colunas, destino, ações e deferrability depois de aplicar as decisões de `FK_CONTRACT` (incluindo RESTRICT de tenant), não apenas pela contagem. As 76 UNIQUE coincidiram por assinatura semântica; constraints sem nome explícito do ORM recebem nomes canônicos pelo PostgreSQL. As 76 CHECKs estão presentes com nomes/semântica esperados; `pg_get_constraintdef()` imprime a forma normalizada pelo PostgreSQL, incluindo casts/parênteses e equivalências como `ANY(array)`. Os índices parciais também apresentam normalização textual das expressões, mas nomes, colunas, unicidade e predicados foram reconciliados. Tipos/defaults de coluna foram comparados considerando alias e representação canônica do PostgreSQL; não foi identificado objeto faltante ou divergência estrutural.

As definições observadas incluem: trigger append-only `BEFORE DELETE OR UPDATE` em `estoque_movimentos`; `AFTER INSERT/DELETE/UPDATE` para atualização de status de unidades produtivas; e trigger de constraint `AFTER INSERT/UPDATE`, `DEFERRABLE INITIALLY DEFERRED`, para validação da soma de unidades. O snapshot detalhado e a lista de FKs foram preservados sob a raiz privada do laboratório, sem credenciais.

## 6. Provas ORM, constraints e RLS

Após a reconciliação do catálogo, foram concedidos temporariamente à role de aplicação apenas `USAGE` no schema `farms` e `SELECT/INSERT/UPDATE/DELETE` nas tabelas `farms.tenants` e `farms.alert_indicators`. A role não é superuser, owner nem `BYPASSRLS`.

O probe usou os models SQLAlchemy `Tenant` e `AlertIndicator`, dois tenants sintéticos e uma transação que foi revertida. Resultado:

- Inserção ORM, leitura e atualização mínima: **PASS**.
- Tenant A vê somente o indicador A; tenant B vê somente o indicador B: **PASS**.
- Inserção cruzada sob contexto do tenant A para linha do tenant B: **negada por RLS**.
- FK inválida: **rejeitada**.
- slug duplicado: **rejeitado por UNIQUE**.
- Rollback e verificação posterior por role migradora: zero tenants de teste e zero indicadores de teste: **PASS**.

Um primeiro harness tinha tentado inserir indicadores dos dois tenants sem alternar o contexto RLS dentro da transação; o PostgreSQL o recusou como esperado e a transação foi revertida. Um runner inicial separado havia confirmado as asserções funcionais, mas cometeu fixtures antes de tentar rollback; isso foi detectado e os registros sintéticos foram removidos por nome exato antes da prova transacional corrigida. A prova corrigida descrita acima terminou com rollback confirmado. Nenhum dado comercial foi envolvido.

Os grants temporários foram revogados após a prova. Verificação final: a role de aplicação não tem `USAGE` no schema nem `SELECT`/`INSERT` nas duas tabelas, permanecendo somente com `CONNECT` no database. O catálogo continuou com 349 tabelas incluindo a version table e 33 sequences.

## 7. Gates e evidências de segurança

- `agro_labctl.py identity` final: **PASS**, após incluir no ambiente de processo o diretório de bibliotecas dos binários Redis extraídos. PING, versão `6.0.16`, PID `1455955` e marcador sintético conferem.
- Identidade SQL final: database `agro_hml_dbdcc24872aa_d3d`, usuário `agro_hml_migrate_dbdcc24872aa`, endpoint `127.0.0.1/32:5433`, versão 16.15.
- `agro_labctl.py migration-identity` no novo alvo: **NO-GO** por grants efetivos em database adicional, conforme seção 2. A role não tem privilégios globais/membership, mas mantém acesso ao database anterior; esse grant não foi alterado.
- Redis continua exclusivo, loopback, ACL do laboratório. Não foram iniciados serviços adicionais.
- Arquivos de configuração e logs privados da prova em `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3d`; arquivos sensíveis em modo `0600`. Nenhuma senha/DSN foi incluída no relatório.

## 8. Estado dos databases

Consultas finais foram somente leitura, com `SET TRANSACTION READ ONLY`:

| Database | Tabelas em `farms` (incl. version table) | Sequences | Revisão | OID do schema `farms` |
|---|---:|---:|---|---:|
| Novo `agro_hml_dbdcc24872aa_d3d` | 349 | 33 | `baseline_deepfarms_v1` | 25418 |
| Anterior `agro_hml_dbdcc24872aa` | 349 | 65 | `baseline_deepfarms_v1` | 16425 |

Os valores do database anterior coincidem com a coleta anterior à prova (349 tabelas, 65 sequences, mesma revisão e OID 16425). Não houve DDL, DML, alteração de role ou ACL nesse database. O database novo permanece criado com a baseline aplicada e sem fixtures de teste; não foi removido.

## 9. Artefatos e comandos de inspeção

Não houve alteração de código nesta fase. O artefato novo no workspace é este relatório. Evidências técnicas privadas:

- `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3d/logs/baseline_01h2d3d.log` — saída sanitizada do Alembic.
- `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3d/logs/catalog_01h2d3d.json` — snapshot de catálogo.
- `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3d/logs/fks_01h2d3d.json` — catálogo detalhado das FKs.

Foram executados: gates `identity` e `migration-identity`; inspeções read-only Alembic/catalog/roles; um upgrade explicitamente limitado à revisão; probes ORM/RLS/FK/UNIQUE em transação revertida; revogação dos grants temporários no novo database; consultas read-only finais de ambos os databases. Não foram executados testes de API/E2E, `head(s)`, stamp, downgrade, deploy, commit, push ou merge.

## 10. Pendências, riscos e veredicto

1. A role migradora conserva grants de CONNECT/CREATE no database descartável anterior. O gate oficial para o novo alvo reprova essa amplitude. Não é possível removê-los dentro do escopo sem alterar o database anterior; requer decisão/autorização separada para uma identidade migradora exclusiva do database novo ou ajuste aprovado do desenho de roles/gate.
2. O `CONTRACT_STATUS` permanece NO-GO conforme as pendências históricas da 01H2C2. Esta prova valida criação real da baseline e catálogo local, mas não valida a linhagem incremental até `20261022_agro_admin_01b1`, não resolve equivalência histórica do contrato nem libera a homologação integrada.
3. A prova de RLS abrangeu dois tenants e `alert_indicators`; não substitui a execução das suites completas ou auditoria de todas as políticas.
4. `pg_get_constraintdef()` e `pg_get_expr()` são representações canônicas do PostgreSQL; as diferenças textuais documentadas não foram tratadas como diferenças semânticas.
5. O database da prova permanece descartável, mas foi preservado para evidência. Não executar nele outra migration, downgrade ou reparo automático.

**Veredicto geral: NO-GO para liberar a baseline como caminho de instalação aprovado ou iniciar homologação integrada.** A correção de duplicação de sequences foi comprovada em PostgreSQL real: 33/33 nomes, defaults e ownerships corretos; não houve regressão estrutural detectada; os probes ORM/constraints/RLS passaram e as fixtures foram revertidas. A liberação permanece bloqueada pelo gate `migration-identity` não aprovado para o alvo novo e pelo estado NO-GO do contrato/caminho Alembic até o head. Nenhuma etapa seguinte foi iniciada.
