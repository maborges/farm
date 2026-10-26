# AGRO-ADMIN-01H2C2 — Engenharia do Clean Install PostgreSQL

**Escopo:** implementação técnica e validação estática, sem conectar a bancos existentes  
**Veredicto:** **NO-GO para executar instalação ou liberar `agro_labctl.py migrate`**

## 1. Causa raiz consolidada

A tentativa de tratar `baseline_deepfarms_v1` como caminho direto para o head corrente é inválida. O grafo converge em `20260915_merge_documentos_fiscais`, mas a outra perna possui 408 revisions ancestrais e operações históricas dependentes do estado/schema anterior. O baseline é gerado do ORM atual (348 tabelas) e já inclui objetos que algumas dessas revisions podem criar, modificar ou remover. Em particular, `8c2e891d6ba9_caderno_campo` condicionalmente remove `prescricoes_vra`, tabela que o baseline atual cria. A revisão `20260914_documentos_fiscais` também adiciona `gestao` e `xml_original`, ambas declaradas hoje no model `fin_notas_fiscais` e portanto incluídas no DDL atual.

Não é seguro aplicar todas as migrations históricas depois do baseline, nem marcar a linhagem como aplicada sem comprovar cada efeito. Há também limitações sem conexão: a referência física dos relatórios é de 2026-09-08, e não existe prova PostgreSQL da nova instalação, do runtime de RLS ou do caminho de upgrade.

## 2. Contrato reconciliado e inventário por objeto

`baseline_contract.py` foi atualizado para distinguir evidência histórica de decisão atual. `CONTRACT_STATUS` permanece `NO-GO`.

| Família/objeto | Inventário atual | Evidência e decisão | Estado |
|---|---:|---|---|
| Registry ORM | 377 models; 348 tabelas selecionadas para baseline | `core.model_registry` + metadata ORM carregado pelo registry; os antigos números 373/344 estavam defasados | Corrigido no contrato; sem prova física |
| UNIQUE | 76 constraints em 71 tabelas | Inventário agora lista tabela, nome, colunas, `ORM_CURRENT` e decisão `INCLUDE_FROM_CURRENT_ORM`; divergência histórica continua sem mapeamento objeto-a-objeto | Pendente de equivalência funcional/PG |
| CHECK | 76 constraints em 22 tabelas | Inventário lista tabela, nome e expressão ORM; divergência histórica não pode ser ligada a objetos específicos com a evidência arquivada | Pendente de equivalência funcional/PG |
| Índices | 1.063 índices ORM | Inventário lista tabela, nome, colunas e unicidade. 01D5 tinha 1.029, fotografia anterior; não é contagem atual | Inclusão ORM definida; paridade de performance histórica pendente |
| Foreign keys | 892 no fechamento 01D4 | 01C4A/01D4: alvos presentes, colunas compatíveis, FKs compostas com chave pai válida e Tenant Integrity; `animal_genetica.animal_id` é explicitamente sem FK pela migration/histórico | Decisão estática fechada; execução PG pendente |
| Nullable | 10 decisões explícitas | ORM/Tenant Integrity sobre diferenças históricas da referência | Intencional; validar operações PG |
| Tipos | 489 diferenças históricas; blockers de compilação reportados como zero em 01C4C | VARCHAR/FLOAT e correções UUID registradas em 01D4; não copiar tipos históricos automaticamente | Compatibilidade histórica; runtime pendente |
| Defaults | 481 diferenças históricas no registro consolidado; server default obrigatório pendente = 0 em 01C4C | Defaults Python-side não são DDL; decisão de clean install segue o ORM e contrato atual | Compatibilidade histórica; comportamento PG pendente |
| ENUMs | 34 tipos, 146 labels | `ENUM_CONTRACT` | Inclusão explícita; catálogo PG pendente |
| Sequences | 35 inventariadas; 32 requeridas; 3 excluídas explicitamente | `SEQUENCE_CONTRACT` | Decisão explícita; ownership/catalog PG pendente |
| RLS | 49 enabled, 48 forced | `RLS_CONTRACT` para cada uma das 348 tabelas; `propriedade_imovel` é enabled sem FORCE por decisão documentada | Inclusão estática; isolamento de dois tenants pendente |
| Policies | 188 | snapshot `pg_policies` 01C4B; 0 inválidas e 0 fora da baseline naquele snapshot | Contrato presente; runtime PG pendente |
| Functions / triggers | 3 / 3 | DDL emitido por `20260908_baseline_deepfarms_v1.py`; 01D5 confirma emissão offline | Inclusão estática; compilação e execução PG pendentes |
| `alembic_version` | 1 tabela de versão | Corrigido nesta fase para schema explícito `farms`, com schema criado antes da tabela no modo offline | SQL offline validado; comparação online ainda requer PG |

O contrato antigo citava 11 tabelas com divergência UNIQUE, 39 com CHECK e 327 com índices divergentes. Esses números são de comparação histórica e não estão alinhados à metadata atual; foram preservados como proveniência `2026-09-08`, não como contagens atuais. A divergência UNIQUE/CHECK continua bloqueadora para declarar equivalência funcional porque falta inventário do lado físico alinhado à revisão atual. Os novos mapas UNIQUE/CHECK/índice inventariam cada objeto **do ORM atual**; eles não afirmam paridade com o database de referência.

### Correção no contrato

`BASELINE_ORM_TABLE_COUNT` e `DISCOVERED_MODEL_COUNT` foram atualizados de 344/373 para 348/377 conforme a metadata carregada e o teste. `UNRESOLVED_STRUCTURAL_AREAS` deixou de declarar falsamente como abertas as famílias FK, tipos, defaults, índices ORM, policies, functions e triggers já fechadas em relatórios posteriores. As pendências funcionais de runtime e da linhagem irmã passaram a ser explícitas em `UNRESOLVED_FUNCTIONAL_AREAS` e `POSTGRESQL_VALIDATION_PENDING`. `UNRESOLVED_COUNTS` mantém UNIQUE/CHECK históricos abertos e não promove o status.

## 3. Versionamento Alembic

Antes da correção, a geração offline escrevia `CREATE TABLE alembic_version` sem schema antes de criar `farms`, e o INSERT era não qualificado. Online, `env.py` cria `farms`, define `search_path` e só então executa Alembic. Isso fazia o SQL offline depender do `search_path` da sessão que o aplicasse.

Correção mínima em `services/api/migrations/env.py`:

1. Define `ALEMBIC_VERSION_SCHEMA = "farms"`.
2. No modo offline PostgreSQL, configura `version_table_schema="farms"` e escreve `CREATE SCHEMA IF NOT EXISTS farms` antes de `context.run_migrations()` (quando Alembic emite a tabela de versão).
3. No modo online PostgreSQL, preserva a criação de schema e o `search_path` já existente, passando também o schema explícito ao Alembic.
4. Para SQLite de testes, mantém `version_table_schema=None`.

O SQL offline foi regenerado com uma URL PostgreSQL **sintética**, sem conectar: a ordem é schema → `farms.alembic_version` → DDL baseline e o INSERT final referencia `farms.alembic_version`. A revisão baseline repete `CREATE SCHEMA IF NOT EXISTS farms`, operação idempotente no PostgreSQL. A equivalência online e a compatibilidade com qualquer banco existente cuja versão esteja fora de `farms` ainda precisam de inspeção em instância descartável. Nenhum banco foi consultado.

## 4. Duas linhagens: comparação e estratégia

O head corrente é `20261022_agro_admin_01b1`. A revisão merge `20260915_merge_documentos_fiscais` tem pais `baseline_deepfarms_v1` e `20260914_documentos_fiscais`; o segundo pai desce de `20260913_repair_estoque_movimentos_origem`. A ancestralidade estática dessa perna contém 408 revisions.

| Efeito conhecido | Classificação para instalação nova | Impacto/limite |
|---|---|---|
| DDL representado por models atuais, incluindo os 348 objetos de tabela e seus constraints/índices | **Já incluído no baseline atual**, conforme metadata | Não executar migrations históricas de CREATE/ALTER cegamente; validação contra cada revision ainda necessária para achar objetos não ORM |
| `20260914_documentos_fiscais`: adiciona `fin_notas_fiscais.gestao` e `xml_original` | **Já incluído no ORM/baseline; obsoleto para clean install**, sujeito à prova física | Necessário no caminho histórico de bancos existentes. Executá-la após baseline pode duplicar colunas |
| `8c2e891d6ba9_caderno_campo`: inspeciona e pode remover `prescricoes_vra` e índice de `cadastros_areas_rurais` | **Obsoleto/incompatível para clean install**, pendente de prova do estado histórico | Baseline atual contém `prescricoes_vra`; essa revisão pode destruí-la. Não executá-la depois do baseline |
| `20260913_repair_estoque_movimentos_origem`: substitui CHECK por `NOT VALID` via SQL | **Pendente de prova PostgreSQL** | Comparar com CHECK atual e decidir se a semântica do baseline é a correta; não reaplicar automaticamente |
| Revisões históricas com DML, backfills e seeds | **Dependente de dados legados** para backfills; seeds podem ser necessários para banco vazio | AST encontrou 174 arquivos candidatos a `execute`/DML (heurística inclui SQL DDL) e não prova quais são seeds obrigatórios. É necessária classificação individual antes de omitir ou transferir qualquer seed |
| Revisões com inspeção condicional do catálogo | **Pendente de prova PostgreSQL** | 39 arquivos ancestrais fazem referência a `inspect()`; comportamento varia conforme estado e algumas não geram SQL offline |
| `20260915_merge_documentos_fiscais` | **Merge sem efeito próprio** | Não fornece nem substitui os efeitos da perna histórica |

Foi selecionada como intenção a **baseline canônica atual, seguida somente por migrations novas e aprovadas**. Não há, entretanto, uma sequência Alembic operacional segura até o head. As opções “executar a perna histórica”, “pular/`stamp` a perna” e “merge artificial” foram rejeitadas. Para liberar clean install é necessário desenhar e revisar uma topologia de instalação que preserve o upgrade atual e não crie ambiguidade de head, além de classificar todos os efeitos não representados no ORM e os seeds necessários. Isso não pode ser resolvido por inferência apenas do grafo.

O caminho atual de upgrade para bancos existentes não foi modificado; migrations históricas permanecem intactas. A mudança em `env.py` mantém o `search_path` online já utilizado, mas deve ser validada contra uma instalação existente em clone antes de adoção geral.

## 5. Arquivos alterados/criados

- Alterado `services/api/migrations/env.py`: schema explícito e ordenação do version table offline/online.
- Alterado `services/api/migrations/baseline_contract.py`: contagem atual, proveniência histórica e inventários ORM por objeto de UNIQUE, CHECK e índices, sem promover GO.
- Alterado `services/api/tests/unit/core/test_baseline_contract.py`: verifica contagens atuais, fontes dos inventários e gates que continuam abertos.
- Criado `services/api/tests/unit/core/test_alembic_offline_version_schema.py`: gera SQL offline com URL sintética e afirma a ordem/qualificação do version table.
- Criado este relatório.

O `scripts/homologacao/agro_labctl.py` não foi alterado; `migrate` continua bloqueado.

## 6. Testes estáticos executados

- `pytest tests/unit/core/test_baseline_contract.py tests/unit/core/test_alembic_offline_version_schema.py -q`: **9 passed**. A geração offline usa `127.0.0.1:5433` com usuário/senha/database sintéticos e `--sql`; não abre socket nem conecta.
- `ruff check` nos quatro arquivos de código/teste alterados: **aprovado**.
- `git diff --check` restrito aos arquivos alterados: **aprovado**.
- `alembic upgrade baseline_deepfarms_v1 --sql` com URL sintética: **geração offline aprovada**, 348 tabelas ORM e version table em `farms`.
- Inspeção estática do graph: 408 revisions ancestrais de `20260914`; 39 referências a inspeção de schema; 174 arquivos candidatos a SQL/DML pela heurística AST. As duas últimas contagens são indicadores de revisão, não uma classificação semântica concluída.

Não foram executados testes de PostgreSQL, migrations, `stamp`, serviços, Docker ou chamadas externas. O teste de integração do Alembic comprova somente a forma do SQL emitido.

## 7. Testes PostgreSQL pendentes

Em um PostgreSQL descartável, sem credenciais/provedores reais:

- confirmar `current_database()`, `current_user`, host, porta e permissões; recusar qualquer alvo compartilhado;
- confirmar banco e schema vazios e usuário com permissões exatas necessárias;
- executar somente após autorização explícita e aprovação do target/manifesto;
- inspecionar tabelas, colunas, constraints, índices, FKs, ENUMs, sequences/ownership, RLS, policies, funções, triggers e `farms.alembic_version` contra inventário versionado;
- comparar a execução online com o SQL offline;
- fazer prova RLS com dois tenants sintéticos e papéis reais de aplicação;
- testar operações mínimas de escrita e leitura pelo ORM, rollback e cleanup;
- validar que uma segunda execução falha fechada em vez de repetir instalação num banco não vazio.

SQLite/mocks não substituem esta prova.

## 8. Procedimento descartável proposto (não executado)

1. Obter autorização registrada para a instalação e para a revisão exata; `agro_labctl.py migrate` permanece bloqueado até existir gate específico.
2. Provisionar PostgreSQL descartável dedicado, sem rede/credenciais de RDS ou banco comercial; usar porta/usuário/database novos e credenciais sintéticas. Não compartilhar Redis/storage/uploads do laboratório comercial.
3. Usar conexão informada por arquivo protegido fora do repo; não exportar o DSN completo nem imprimir senha. O gate deve rejeitar host que não seja o loopback aprovado e confirmar identidade com `current_database()`, `current_user`, `inet_server_addr()`, `inet_server_port()` e `version()`.
4. Verificar `pg_namespace`, `pg_class`, `alembic_version` e ausência de objetos/dados; se não estiver inequivocamente vazio, abortar e descartar/recriar a instância.
5. Validar privilégios do role, incluindo criação de schema e objetos requeridos; não usar superuser de produção.
6. Salvar evidência redigida da identidade/permissões e digest do target. Exigir aprovação explícita imediatamente antes de aplicar.
7. Executar somente o instalador/target aprovado após resolver a topologia das linhagens; nenhum `upgrade heads`, `stamp` ou comando implícito.
8. Comparar catálogo com o inventário de contrato; executar RLS com tenants A/B, CRUD mínimo, constraints, sequences e triggers; salvar resultados sem DSNs, tokens ou dados pessoais.
9. Em falha, parar, preservar logs redigidos, descartar o banco inteiro e não improvisar downgrade. Em sucesso, guardar evidências aprovadas e remover a instância e seu volume/storage dedicados conforme autorização.

## 9. Riscos para upgrades existentes

- Mudanças nas contagens refletem novos models em metadata; o baseline é executável sobre a metadata atual, mas a referência física usada para decisions é antiga.
- Aplicar baseline e depois a história causa duplicação, remoções ou DDL condicional incompatível; `8c2e891d6ba9` é prova concreta de risco.
- Pular uma migration pode omitir seed, DML ou constraint que o ORM não modela.
- `version_table_schema="farms"` representa o comportamento online atualmente pretendido (`search_path=farms`), mas um banco legado com version table em `public` precisa de diagnóstico/clone antes de qualquer migração.
- 76 UNIQUE e 76 CHECK são objetos do ORM atual, não aprovação semântica contra o banco referência. RLS/functions/triggers também exigem runtime.
- A criação/upgrade pode depender de roles, extensões PostgreSQL, privilégios ou settings de sessão não demonstrados offline.

## 10. Critérios GO / NO-GO

**GO para prova descartável** somente após: inventário atual versionado; resolução de equivalência UNIQUE/CHECK por objeto; classificação individual de efeitos DDL/DML e seeds das 408 revisions; topologia de instalação que não execute nem omita efeitos e mantenha upgrade existente sem ambiguidade; análise do schema/version table; autorização explícita e confirmação automatizada da identidade/permissões de um PostgreSQL vazio dedicado.

**GO para uso do clean install** requer também catálogo/runtime PostgreSQL aprovados, RLS com dois tenants, smoke CRUD ORM e evidência redigida revisada.

**Veredicto desta fase: NO-GO.** Foram corrigidos e testados os problemas estáticos de version table e de contagem/inventário ORM. A estratégia arquitetural preferida continua sendo baseline canônica atual com migrations futuras incrementais, mas a ponte segura ao head e os efeitos históricos ainda não foram comprovados. Não executar procedimento, migrations ou `agro_labctl.py migrate`; aguardar autorização posterior.
