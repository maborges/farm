# AGRO-ADMIN-01H2D3B — Execução Controlada e Validação Real da Baseline PostgreSQL

**Data:** 2026-10-25  
**Laboratório:** `dbdcc24872aa2992`  
**Veredicto:** **NO-GO** para provas funcionais e homologação integrada. A revisão isolada foi aplicada com sucesso, mas a baseline produziu sequences divergentes do contrato.

## 1. Identidade e isolamento

Identidade confirmada imediatamente antes da execução e novamente durante a validação:

| Item | Valor observado |
|---|---|
| PostgreSQL | 16.15 |
| Endpoint | `127.0.0.1:5433` |
| Database | `agro_hml_dbdcc24872aa` |
| PGDATA | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data` |
| PID | `1447173` |
| Role da migration | `agro_hml_migrate_dbdcc24872aa` |
| Configuração Alembic | `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/config/alembic-migration.env` |
| Modo do arquivo | `0600` |

O comando `identity` confirmou o cluster isolado. O comando `migration-identity` confirmou a role sem superuser, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, INHERIT, memberships ou privilégios em outros databases; confirmou também CONNECT/CREATE apenas no database alvo, TEMP revogado e separação da role de aplicação. O gate passou quando executado com acesso de loopback autorizado.

Uma primeira tentativa do gate pós-migration dentro da sandbox retornou erro de autenticação genérico porque a sandbox não permitiu a conexão local. A repetição fora da sandbox, sem alteração do gate ou das roles, passou. A conexão direta confirmou `current_database=agro_hml_dbdcc24872aa`, `session_user=current_user=agro_hml_migrate_dbdcc24872aa`, endereço `127.0.0.1`, porta `5433` e versão `16.15`.

O database estava sem schema `farms`, tabela de versão e relações de aplicação antes do DDL. A configuração usada veio exclusivamente do arquivo privado do laboratório; não foram usados `.env.local` ou `.env.production`. Nenhum database externo foi acessado.

## 2. Revisão e execução

A inspeção do grafo identificou `baseline_deepfarms_v1` como revisão existente, raiz independente (`down_revision=None`), sem dependências e com caminho de upgrade contendo somente essa revisão. A cadeia histórica não foi percorrida.

Foi executado apenas:

```text
alembic -c <configuração privada do laboratório>/services/api/alembic.ini upgrade baseline_deepfarms_v1
```

O log sanitizado está em `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/logs/baseline_01h2d3b.log`, modo privado. O resultado foi `Running upgrade -> baseline_deepfarms_v1`; a consulta posterior confirmou `farms.alembic_version = baseline_deepfarms_v1`.

Um primeiro runner de validação estática encerrou antes de abrir conexão por não incluir `services/api` no caminho de importação. Foi corrigido apenas o runner temporário, o grafo foi revalidado e a execução autorizada ocorreu uma vez. Essa falha não tocou o database.

Não foram executados `upgrade head`, `upgrade heads`, `stamp`, downgrade, revisões históricas, API, frontends ou testes E2E. A migration não contém seeds/DML de aplicação nem chamadas externas na função `upgrade`; os corpos das funções e triggers criados definem comportamento futuro. O downgrade destrutivo não foi executado.

## 3. Catálogo observado

Resumo consultado diretamente no PostgreSQL descartável, pela role migradora:

| Categoria | Observado | Comparação |
|---|---:|---|
| Schema `farms` | 1 | Presente |
| Tabelas da aplicação | 348 | Igual ao conjunto de 348 tabelas selecionadas pelo registry ORM |
| `farms.alembic_version` | 1 | Revisão exata confirmada |
| Colunas da aplicação | 4.767 | Igual ao ORM; nenhuma coluna ou tabela ausente/extra |
| Constraints FK | 924 | Igual à quantidade ORM |
| Constraints UNIQUE | 76 | Quantidade igual à declaração ORM |
| Constraints CHECK | 76 | Quantidade igual à declaração ORM |
| PK | 349 | 348 da aplicação mais a PK da tabela Alembic |
| Constraint trigger | 1 | Trigger de constraint da baseline |
| Índices PostgreSQL | 1.488 | 1.063 ORM + índices de PK/UNIQUE; contagem coerente |
| ENUMs | 34 | Nomes e labels iguais ao contrato |
| RLS habilitado | 49 | Igual ao contrato |
| RLS forced | 48 | Igual ao contrato; `propriedade_imovel` é enabled sem FORCE |
| Policies | 188 | Igual à contagem do contrato |
| Funções / triggers comuns | 3 / 3 | Nomes, linguagem/retorno e vínculos observados conforme os três objetos declarados |
| Sequences | **65** | **Divergente: contrato exige 32 sequences** |

As comparações de nomes de tabelas e colunas foram exatas: 348/348 tabelas e 4.767/4.767 colunas, sem ausências ou extras. As contagens de FKs, UNIQUE, CHECK e índices também coincidem. Isso não substitui a comparação semântica completa das expressões de cada UNIQUE/CHECK nem resolve as pendências históricas já registradas no contrato. O status `CONTRACT_STATUS` continua NO-GO.

### Divergência bloqueante: sequences

A migration chama `_create_sequences()` para criar explicitamente as 32 sequences de `REQUIRED_SEQUENCE_NAMES`, antes de criar as tabelas ORM. Em seguida, `CreateTable(table)` emite sequences serial do ORM. A prova no catálogo mostrou, por exemplo:

| Sequence | Ownership/uso observado |
|---|---|
| `farms.animal_genetica_id_seq` | Sem vínculo a tabela/coluna; não é a sequence retornada para o ID |
| `farms.animal_genetica_id_seq1` | Owned pelo `animal_genetica.id`; `pg_get_serial_sequence` retorna esta |

O mesmo padrão `*_id_seq` sem ownership e `*_id_seq1` owned foi observado em diversos objetos. O catálogo contém 65 sequences: as 32 names explicitamente requeridas, 32 sequences ORM renomeadas com sufixo `1` e a sequence adicional `sankhya_sync_logs_id_seq`. As sequences explicitamente requeridas não estão sendo consumidas pelos defaults seriais dos IDs. Também há divergência entre o inventário declarado e a sequência efetivamente ligada às colunas.

Essa evidência demonstra incompatibilidade real entre o DDL do baseline e o contrato de sequences. Não foi aplicado reparo, renomeação, ownership ou alteração de default.

## 4. Provas funcionais

Não executadas. O critério definido pelo pedido exige catálogo consistente antes de inserir fixtures. Como a divergência de sequences é estrutural e afeta os defaults/autoincrement dos IDs, foram suspensos:

- inserts sintéticos e provas de constraints;
- operações ORM;
- testes de RLS com dois tenants;
- testes com role de aplicação;
- limpeza de fixtures.

Não há evidência nesta fase de funcionamento transacional da baseline, comportamento das constraints em dados, execução das functions/triggers ou isolamento RLS em sessão. Esses itens seguem pendentes após correção arquitetural aprovada e nova execução em database descartável novo.

## 5. Estado final e segurança

O database descartável contém a baseline `baseline_deepfarms_v1` aplicada e os objetos descritos acima. Nenhum DML de fixture foi realizado; portanto, nenhum dado de negócio foi inserido. Não houve alteração de roles, privilégios, serviços, bancos externos ou arquivos de configuração comercial. O cluster PostgreSQL e Redis não foram iniciados ou encerrados nesta fase; permaneceram sob o estado operacional anterior.

O ambiente não deve ser tratado como aprovado para testes da aplicação. Esta prova não valida o caminho histórico até o head atual nem autoriza homologação integrada.

## 6. Próximos passos e veredicto

**NO-GO.** Antes de uma nova tentativa:

1. corrigir e revisar a relação entre `SEQUENCE_CONTRACT`, sequences explícitas e autoincrement/`SERIAL` do ORM, sem alterar migrations históricas aplicadas;
2. repetir a baseline em um database descartável novo, sem corrigir este database automaticamente;
3. validar individualmente sequences, defaults e ownership contra o ORM e o contrato;
4. somente com catálogo consistente, executar constraints, ORM e RLS com a role de aplicação;
5. manter o contrato global em NO-GO até resolver os gaps UNIQUE/CHECK e completar as provas PostgreSQL pendentes.

Esta execução não libera o comando `agro_labctl.py migrate`, o head Alembic ou a homologação E2E.
