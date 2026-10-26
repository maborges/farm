# AGRO-ADMIN-01H2D3C — Correção do Contrato e Geração de Sequences da Baseline

**Data:** 2026-10-25  
**Escopo:** correção estática do clean-install e testes automatizados; nenhum acesso ao PostgreSQL.  
**Veredicto:** **GO COM RESSALVAS para a correção estática; NO-GO para declarar a baseline PostgreSQL validada ou liberar a homologação.**

## 1. Causa raiz

A revisão `baseline_deepfarms_v1` criava explicitamente os 32 nomes de `REQUIRED_SEQUENCE_NAMES` antes de emitir `CreateTable()` para as tabelas ORM. As colunas `id` já são PKs inteiras autoincrementais; no PostgreSQL, o DDL SQLAlchemy as compila para `SERIAL`/`BIGSERIAL`, que cria a sequence correta e a associa à coluna.

Como os nomes já existiam, PostgreSQL evitava colisão escolhendo nomes alternativos terminados em `seq1` para os 32 defaults dos IDs. O catálogo da prova 01H2D3B confirmou 32 sequences explícitas órfãs, 32 sequences `seq1` owned por colunas e a sequence autogerada `sankhya_sync_logs_id_seq`. Total observado naquela prova: 65. O default de cada ID apontava para a sequence sufixada, não para o nome previsto no contrato antigo.

A falha era de autoridade duplicada: o baseline mantinha um inventário histórico como plano de DDL, embora o ORM já fosse responsável por gerar essas sequences. O database 01H2D3B não foi consultado nem alterado nesta fase; permanece no estado divergente registrado em seu relatório.

## 2. Inventário e classificação

### Sequences do clean-install conforme metadata ORM atual

As 33 PKs autoincrementais da baseline não possuem default `Sequence` Python nem `server_default` explícito. O tipo e a coluna vêm do ORM; PostgreSQL/SQLAlchemy emitem `SERIAL` ou `BIGSERIAL`, com default equivalente a `nextval('farms.<nome>_seq'::regclass)` e ownership da sequence pela coluna.

**32 `SERIAL` (`INTEGER`, ownership `tabela.id`):**

```text
animal_genetica_id_seq, balanca_webhook_credentials_id_seq,
carbono_emissoes_id_seq, carbono_projetos_id_seq, carbono_relatorios_id_seq,
case_ih_id_seq, cochos_id_seq, comparador_precos_id_seq,
confinamento_lotes_id_seq, diagnosticos_id_seq, integration_credentials_id_seq,
integration_features_id_seq, integration_health_snapshots_id_seq,
integration_sync_policies_id_seq, integration_versions_id_seq, john_deere_id_seq,
marketplace_integracoes_id_seq, modelos_ml_id_seq, pragas_doencas_id_seq,
racas_id_seq, racoes_tmr_id_seq, recomendacoes_id_seq, sankhya_config_id_seq,
sankhya_lancamentos_financeiros_id_seq, sankhya_nfe_id_seq,
sankhya_pessoas_id_seq, sankhya_produtos_id_seq, sankhya_tabelas_id_seq,
sugestoes_acasalamento_id_seq, tenant_integracoes_id_seq, tratamentos_id_seq,
whatsapp_id_seq
```

**1 `BIGSERIAL` (`BIGINT`, ownership `sankhya_sync_logs.id`):**

```text
sankhya_sync_logs_id_seq
```

O nome `sankhya_sync_logs_id_seq` não estava na lista histórica de 35 nomes. A tabela e a PK `BIGINT` existem na metadata atual; o PostgreSQL já o havia criado implicitamente na prova 01H2D3B. Ele agora consta do contrato limpo baseado no ORM.

### Referência histórica de 35 nomes

`SEQUENCE_NAMES` permanece como referência histórica usada pelo auditor de colisões, sem comando de criação. Seus 35 itens são: os 32 nomes `SERIAL` listados acima, mais `amostras_id_seq`, `mapas_fertilidade_id_seq` e `territory_legacy_backup_01h2_id_seq`. Esses três estão fora do conjunto de tabelas selecionadas para o baseline e seguem classificados como excluídos para clean install. Nenhum dos três é pré-criado.

### Classificação solicitada

| Classe | Quantidade | Decisão |
|---|---:|---|
| Autoincrement vinculada a coluna | 33 | Contrato gerado da metadata; `SERIAL`/`BIGSERIAL` pelo DDL ORM |
| Sequence explicitamente usada por default ORM | 0 | Nenhuma declaração `Sequence` nem default `nextval` explícito foi encontrada nos 348 modelos selecionados |
| Sequence independente requerida pelo clean-install | 0 | Não há objeto independente identificado na revisão baseline atual |
| Sequence implícita PostgreSQL/SQLAlchemy | 33 | Criada pela coluna serial; propriedade/ownership é da coluna |
| Referências históricas fora do baseline | 3 | Excluídas: `amostras`, `mapas_fertilidade`, `territory_legacy_backup_01h2` |

### Comportamento da prova anterior

| Família | Resultado observado em 01H2D3B | Resultado esperado em instalação nova corrigida |
|---|---|---|
| 32 nomes `SERIAL` | Nome do contrato ficou órfão; a coluna usou `<nome>1` | O único nome `<tabela>_id_seq` é gerado e owned pela coluna |
| `sankhya_sync_logs_id_seq` | Criado pelo ORM e reportado como extra em relação à lista antiga | Nome reconhecido como `BIGSERIAL` de `sankhya_sync_logs.id` |
| Sufixos `seq1` | 32 observados e usados pelos defaults | Nenhum sufixo esperado; teste estático impede pré-criação concorrente |

Não há prova PostgreSQL da propriedade após a correção nesta fase; ownership/default são expectativas derivadas da metadata e da semântica SERIAL, a confirmar na nova prova real.

## 3. Investigação de `sankhya_sync_logs` e `seq1`

- `sankhya_sync_logs.id` é `BIGINT`, PK e `autoincrement=True`; `CreateTable` compila para `BIGSERIAL`.
- Não há default explícito no model. A sequence `sankhya_sync_logs_id_seq` é, portanto, um objeto gerado pelo PostgreSQL no DDL da tabela, não uma sequence independente.
- Nas outras 32 colunas int autoincrementais, a pré-criação do nome canônico provocava colisão e o PostgreSQL usava `<nome>1` para a sequence criada por `SERIAL`.
- Os `seq1` não são nomes aprovados ou desejados; nenhum código os inclui como exceção.

## 4. Estratégia e correções

Foi estabelecida uma única autoridade de geração: **DDL ORM/PostgreSQL das colunas autoincrementais**. O contrato `SEQUENCE_CONTRACT` agora é montado a partir das 348 tabelas selecionadas no registry e da `Table.autoincrement_column`. Para cada item registra schema, nome, tabela/coluna, tipo, geração, default esperado, ownership e fonte `ORM_TABLE_DDL`. A construção falha explicitamente caso uma coluna autoincremental também introduza um default concorrente.

Alterações:

1. Removida a criação explícita de sequences do `upgrade()` e o helper `_create_sequences()`.
2. Preservada a ordem schema → ENUMs → tabelas ORM → FKs → índices → funções/triggers → RLS/policies.
3. Removida a segunda tentativa de DROP das sequences no downgrade normal; sequences owned são removidas junto com as tabelas. Um `DROP SEQUENCE IF EXISTS farms.<nome>` guardado foi mantido após os drops de tabelas para limpar órfãs produzidas por instalações da versão anterior do baseline, caso um downgrade seja executado futuramente. Nenhum downgrade foi executado.
4. Mantida a lista histórica de 35 nomes para auditoria de colisões, mas ela deixou de dirigir o DDL. O contrato de instalação é agora a lista de 33 geradas pelo ORM, incluindo o `BIGSERIAL` de `sankhya_sync_logs`.
5. O database da prova 01H2D3B não foi reutilizado, corrigido ou conectado.

Nenhuma migration da linhagem histórica foi alterada. A revisão independente do clean-install `20260908_baseline_deepfarms_v1` foi ajustada para que uma instalação nova use uma única fonte de DDL. Como a versão anterior dessa revisão foi aplicada somente ao database descartável da prova 01H2D3B, esse database continua representando a execução anterior e não deve ser tratado como instalação corrigida nem sofrer downgrade automático.

## 5. Arquivos alterados

- `services/api/migrations/versions/20260908_baseline_deepfarms_v1.py` — remove criação duplicada e mantém limpeza de órfãs protegida no downgrade.
- `services/api/migrations/baseline_contract.py` — mantém referências históricas separadas e cria contrato atual a partir dos IDs autoincrementais ORM.
- `services/api/tests/unit/core/test_baseline_contract.py` — atualiza a expectativa do contrato limpo para 33 sequences ORM.
- `services/api/tests/unit/core/test_baseline_sequences.py` — novo teste focado em nomes, defaults esperados, ownership, tipo SERIAL/BIGSERIAL, ausência de pré-criação e exclusões históricas.
- Este relatório.

Os arquivos de contrato e teste já continham alterações de fases anteriores nesta worktree. As alterações desta fase nesses arquivos limitam-se ao contrato/expectativas de sequences e ao novo teste; decisões prévias sobre tabelas, FKs, UNIQUE/CHECK, índices, RLS e outros objetos foram preservadas.

## 6. Testes executados

Somente verificações locais estáticas, sem conexão ao banco e sem serviços:

- `pytest services/api/tests/unit/core/test_baseline_contract.py services/api/tests/unit/core/test_baseline_sequences.py services/api/tests/unit/core/test_alembic_offline_version_schema.py -q` — **14 passed**.
- `ruff check` nos quatro arquivos de código/teste alterados — **PASS**.
- `git diff --check` nos arquivos de código/teste alterados — **PASS**.

Os testes conferem a correspondência exata entre as 33 entradas e as colunas ORM selecionadas, o tipo SERIAL/BIGSERIAL, nome esperado, default canônico, ownership esperado, ausência de defaults `Sequence` concorrentes, ausência de `CREATE SEQUENCE` no baseline e existência de cleanup `IF EXISTS` apenas no downgrade. O teste offline Alembic continua verificando a tabela de versão qualificada em `farms`.

Não houve geração offline integral específica desta revisão, conexão PostgreSQL, migration, teste de catálogo real, serviço ou E2E nesta fase. Contagem estática não é apresentada como prova de ownership real.

## 7. Riscos e pendências

- A prova real corrigida ainda precisa confirmar 33 sequences exatas, seus tipos, defaults `pg_get_serial_sequence()` e ownership; não deve reutilizar o database 01H2D3B.
- `CONTRACT_STATUS` permanece `NO-GO`. A nova correção não resolve equivalência histórica/semântica das 76 UNIQUE e 76 CHECK, teste real de RLS entre tenants, funções/triggers em execução ou caminho das linhagens Alembic até o head.
- A lista antiga de 35 itens continua como histórico de referência; consumidores futuros não devem interpretá-la como plano DDL. `REQUIRED_SEQUENCE_NAMES` agora deriva do contrato ORM atual.
- A mudança no downgrade é somente uma limpeza guardada. Não foi validada em PostgreSQL nem executada em qualquer banco.
- A baseline foi aplicada com o código anterior no database descartável da prova real. Seu catálogo permanece divergente; não execute nele a nova revisão, downgrade ou reparo ad hoc.

## 8. Procedimento proposto para a nova prova PostgreSQL

Após autorização separada:

1. Criar um database descartável novo no cluster isolado, com nome/identificador diferente do `agro_hml_dbdcc24872aa`; conferir loopback, versão, PID, PGDATA, role least-privilege e ausência de objetos.
2. Confirmar por identidade que o alvo não é o database da prova anterior, banco compartilhado ou RDS; usar exclusivamente o arquivo sintético privado do laboratório.
3. Revalidar estaticamente que o caminho Alembic continua sendo somente `baseline_deepfarms_v1` e registrar o digest/revisão de código corrigida.
4. Aplicar, somente com autorização explícita para essa revisão, a baseline no banco vazio novo. Não usar `upgrade head`, `heads`, `stamp` ou migrations históricas.
5. Consultar o catálogo e exigir igualdade exata com `SEQUENCE_CONTRACT`: 33 sequences; nenhuma sequência em duplicidade/sufixo inesperado; para cada entrada, `pg_get_serial_sequence('farms.<table>', '<column>') = 'farms.<name>'`, tipo correto, default correto e dependency/ownership da coluna.
6. Conferir colunas/defaults dos 33 IDs e garantir que nenhuma sequence independente não contratada apareceu. Confirmar também que os objetos não relacionados da baseline (FKs, UNIQUE/CHECK, índices, ENUMs, RLS/policies, functions/triggers e `farms.alembic_version`) continuam presentes.
7. Se o catálogo estiver consistente, executar somente então operações ORM/constraints e probes RLS sintéticos pela role de aplicação, em transações e com cleanup verificado. Qualquer diferença encerra a prova sem reparo automático.

Esse procedimento é uma proposta; nenhuma etapa foi executada nesta fase.

## 9. Veredicto

**GO COM RESSALVAS para a correção estática:** a duplicação explícita foi removida, o contrato de instalação acompanha os 33 IDs gerados pelos models e os testes estáticos direcionados passaram.

**NO-GO para declarar a baseline PostgreSQL íntegra ou liberar homologação:** a correção ainda requer uma nova prova real em database vazio descartável. O database 01H2D3B mantém a fotografia antiga e não foi tocado. `CONTRACT_STATUS` continua NO-GO pelas pendências UNIQUE/CHECK, runtime RLS/functions/triggers e linhagem Alembic.
