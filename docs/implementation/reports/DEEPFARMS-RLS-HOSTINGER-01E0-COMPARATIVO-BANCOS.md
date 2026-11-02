# DEEPFARMS-RLS-HOSTINGER-01E0 — Comparativo PostgreSQL Desenvolvimento × Hostinger

**Data da coleta local:** 2026-10-31

**Status:** inventário local concluído; comparativo físico concluído dentro da cobertura dos metadados 01C
**Escopo:** consultas somente leitura ao PostgreSQL de desenvolvimento e leitura dos relatórios/extratos já existentes. Nenhum acesso à Hostinger foi feito nesta etapa.

## 1. Resumo executivo

O responsável pelo DeepFarms confirmou expressamente que `192.168.0.2` é o servidor PostgreSQL de desenvolvimento. A configuração efetiva carregada pelo backend apontou para esse host, database `farms`; a conexão confirmou database/schema `farms`, usuário e sessão `borgus`, porta 5432 e PostgreSQL 16.15. Nenhuma credencial foi impressa. O servidor reportou seu endereço de interface como `172.26.132.19/32`; a relação de rede entre esse endereço e o endpoint confirmado `192.168.0.2` não foi inspecionada de forma independente. A identificação do ambiente, portanto, se apoia na confirmação do responsável, no endpoint configurado e na identidade retornada pelo banco.

O schema de desenvolvimento `farms` **não é uma cópia física equivalente** à fotografia Hostinger do 01C. Há 355 tabelas locais e 350 na Hostinger: 343 nomes coincidem, 7 estão somente na fotografia Hostinger e 12 somente no desenvolvimento. No desenvolvimento há 52 tabelas com RLS/51 com FORCE, contra 49/48 na Hostinger. As três diferenças de estado são tabelas comuns que têm RLS e FORCE ativos no desenvolvimento, mas estavam sem RLS na fotografia Hostinger. Os 188 nomes de policies da Hostinger estão presentes no schema local, que também tem 12 policies adicionais em `farms`; há ainda 31 policies em um schema separado `tara`.

Outras diferenças materiais: o desenvolvimento tem 286 tabelas com `tenant_id` contra 275 na Hostinger; em 275 nomes comuns, tipo coincide, mas `frota_planos_manutencao` e `frota_registros_manutencao` são nullable localmente e `NOT NULL` na Hostinger. O catálogo local contém 936 FKs; 893 correspondem semanticamente às da Hostinger após normalizar a qualificação `farms.` e ignorar nomes de constraint, enquanto 31 relações observadas na Hostinger não aparecem semanticamente no local e 43 são locais sem equivalente na fotografia Hostinger.

O servidor PostgreSQL 16 de desenvolvimento pode servir como **hospedeiro técnico para um laboratório novo e descartável**, condicionado a um operador com privilégios administrativos criar banco e roles isolados. O database atual `farms` não deve ser usado diretamente como laboratório. O usuário `borgus` é owner das 355 tabelas do schema, não tem `CREATEDB` nem `CREATEROLE`; `admin_farms` tem `BYPASSRLS` e é membro de `borgus`, herdando privilégios de ownership. As diferenças de schema também impedem tratar o banco atual como réplica da Hostinger.

**Veredicto: GO COM RESSALVAS para preparar a 01E em banco novo, descartável e isolado no servidor PostgreSQL 16, após provisionamento por identidade administrativa autorizada. NO-GO para executar a 01E no database existente `farms` ou usar `borgus`/`admin_farms` como role runtime de prova.** Nenhum banco ou role de laboratório foi criado; a 01E não foi executada.

## 2. Fontes e método

- [01C — Inventário real Hostinger](DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md) e extrato `/tmp/deepfarms-rls-01c-metadados.txt` (1.883 linhas), fornecidos a partir de comandos executados pelo operador na Hostinger. A fotografia é limitada ao instante e à abrangência daquela coleta; não houve nova consulta à produção.
- [01D — Plano de correção controlada](DEEPFARMS-RLS-HOSTINGER-01D-PLANO-CORRECAO-CONTROLADA.md) e [01E — Prova de isolamento em laboratório](DEEPFARMS-RLS-HOSTINGER-01E-LABORATORIO-ISOLAMENTO.md), usados apenas como referência de escopo.
- Configuração do backend em `services/api/core/config.py`, `services/api/core/database.py` e configuração local carregada sem imprimir a URL ou credenciais. O objeto `settings` da própria aplicação foi usado para abrir a conexão; o host efetivo foi conferido como `192.168.0.2` sem exibir os demais componentes secretos.
- Consultas a `current_database()`, `current_schema()`, `current_user`, `session_user`, versão e catálogos PostgreSQL, executadas dentro de transação `READ ONLY`. Foram consultados nomes/definições de catálogo, ACLs, flags de roles e o valor de `alembic_version`. Nenhuma tabela de negócio foi lida e nenhum teste comportamental foi executado.
- Snapshot local temporário dos metadados em `/tmp/deepfarms-rls-01e0-dev-catalog.json`; não contém linhas de negócio nem credenciais.

Os conjuntos foram comparados pelo nome exato no schema `farms`. Para FKs, a comparação semântica normaliza o prefixo de schema `farms.` nas definições e não depende do nome da constraint. Os dados de Hostinger não contêm inventário completo de colunas, índices, PKs, uniques, checks, triggers ou extensões; não se inferiu paridade nessas áreas.

## 3. Identificação do PostgreSQL de desenvolvimento

| Propriedade | Resultado observado | Nota |
|---|---|---|
| Endpoint configurado | `192.168.0.2` | Confirmado como servidor de desenvolvimento pelo responsável; nenhuma conexão à Hostinger foi feita. |
| Database / schema atual | `farms` / `farms` | Retornados pela conexão efetiva. |
| Porta | `5432` | Retornada pelo servidor. |
| Usuário / sessão efetivos | `borgus` / `borgus` | Não são credenciais de produção. |
| PostgreSQL | `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)` | Hostinger foi informada como PostgreSQL 16; o minor da Hostinger não consta no extrato 01C. |
| `search_path` | `farms` | Coincide com a configuração SQLAlchemy lida. |
| Endereço de servidor reportado | `172.26.132.19/32` | Difere do endpoint configurado; possível interface/rede interna não comprovada. A confirmação do destino usa a declaração do responsável e o endpoint de conexão. |

O database tem schemas `farms`, `tara` e `test_schema`. A comparação principal abaixo restringe-se a `farms`, conforme solicitado. Há 33 tabelas e 31 policies adicionais em `tara`, fora do escopo físico da comparação Hostinger `farms`; `test_schema` não apresentou relações físicas no inventário consultado.

## 4. Matriz de diferenças físicas

Classes: **BLOQUEANTE** impede usar diretamente este database ou identidade como laboratório representativo e isolado; **RELEVANTE** precisa ser considerada na montagem/interpretação dos testes; **INFORMATIVA** registra diferença sem impacto imediato demonstrado no escopo da prova.

| Área | Hostinger — fotografia 01C | Desenvolvimento — schema `farms` | Diferença e classe |
|---|---|---|---|
| Versão | PostgreSQL 16; minor não informado | PostgreSQL 16.15 | Mesmo major observado; minor Hostinger desconhecido. **INFORMATIVA**, pendente apenas para paridade exata. |
| Relações físicas | 350 tabelas, todas `relkind='r'` | 355 tabelas, todas `relkind='r'` | Conjuntos nominais distintos; detalhe na seção 5. **RELEVANTE** para fidelidade do fixture. |
| RLS / FORCE | 49 / 48 | 52 / 51 | Três tabelas comuns têm RLS/FORCE local, mas estavam sem RLS na Hostinger. **RELEVANTE**; a fotografia não representa o estado local atual. |
| Policies | 188 em `farms` | 200 em `farms`; 231 no DB contando 31 policies de `tara` | As 188 identidades (tabela + nome) da fotografia aparecem localmente; 12 policies locais adicionais cobrem as três tabelas com RLS local acrescido. As expressões integrais não foram reconciliadas entre os dois dumps nesta etapa. **RELEVANTE**. |
| `tenant_id` | 275 tabelas; 22 nullable | 286 tabelas; 25 nullable | Os 275 nomes da Hostinger estão presentes localmente. Há 11 locais adicionais e duas diferenças de nullability em nomes comuns. **RELEVANTE** para fixtures/schema dependente de Tenant. |
| FKs | 924 | 936 | Após normalizar schema e nomes de constraints: 893 equivalentes semanticamente; 31 presentes apenas na fotografia Hostinger e 43 apenas no desenvolvimento. Diferença líquida +12 local. **RELEVANTE**; conferir relações escolhidas para a prova. |
| Constraints além de FK | Inventário completo não consta no extrato Hostinger | 355 PK, 77 UNIQUE, 173 CHECK e 1 constraint do tipo `t` no catálogo local | Não é possível produzir diff produção × desenvolvimento. **LACUNA RELEVANTE**, sem classificar os objetos locais como defeitos. |
| Índices | Inventário não consta no extrato 01C | 1.517 índices em `farms` | Sem base Hostinger para comparação. **LACUNA RELEVANTE** se o laboratório depender de índice específico; não bloqueia teste mínimo sintético de RLS. |
| Ownership de tabelas | As 350 tabelas owned por `deepfarms` | As 355 tabelas owned por `borgus` | Diferença confirmada; `admin_farms` é membro de `borgus` e herda seus privilégios de owner. **BLOQUEANTE** para executar prova com essa identidade/papel como runtime. |
| ACLs e grants | `relacl` NULL nas 350 tabelas; schema `farms` ACL NULL; efetividade completa não avaliada na coleta 01C | 296 das 355 tabelas e 26 das 36 sequences têm ACL explícita; schema ACL inclui `PUBLIC USAGE` e grant de `USAGE` a `admin_farms`; há 3 default ACLs no catálogo do database | Modelos de concessão não são equivalentes. `admin_farms` herda ownership de `borgus` e tem `BYPASSRLS`. **BLOQUEANTE** para usar as identidades atuais como prova de runtime restrito. ACL bruta da Hostinger não prova privilégios efetivos. |
| Roles / memberships | 15 roles; `deepfarms` é login superuser/BYPASSRLS; 3 memberships internas | 17 roles; `borgus`, `admin_farms`, `postgres`; 4 memberships | `deepfarms` não existe localmente; `admin_farms` é login com `BYPASSRLS=true`, membro de `borgus`; `postgres` é superuser. `borgus` é login sem superuser/BYPASSRLS, mas owner das tabelas e tem `CREATEDB=false`, `CREATEROLE=false`. **BLOQUEANTE** para criar/usar laboratório com a identidade atual. |
| Sequences | 33, owner `deepfarms`, ACL NULL | 36, owner `borgus`; 26 têm ACL explícita | Três sequences locais adicionais associadas a tabelas locais adicionais. **RELEVANTE** para grants de uma futura role de prova. |
| Funções | 3 funções listadas, owner `deepfarms`, não `SECURITY DEFINER` | 4 funções em `farms`, owner `borgus`, nenhuma `SECURITY DEFINER` | Três nomes coincidem; adicional local `fn_estoque_requisicao_item_evento_append_only`. ACL das quatro é NULL localmente. **RELEVANTE**; Hostinger não informa triggers. |
| Triggers | Não inventariados no extrato Hostinger | 4 triggers não internos em `farms` | Sem comparação possível. **LACUNA INFORMATIVA** para RLS, a menos que a fixture use um desses objetos. |
| Views | 0 na fotografia Hostinger | 0 no schema local | Coincidem no escopo consultado. **INFORMATIVA**. |
| Extensões | Não inventariadas no extrato Hostinger | `plpgsql` 1.0 | Sem comparação possível. **INFORMATIVA** para a prova RLS básica. |
| Default privileges | 0 registros na fotografia Hostinger | 3 registros: um em `test_schema` e dois para owner `postgres` no schema `farms` | Diferença confirmada; os dois grants em `farms` são para tabelas e sequences futuras de `postgres` ao papel `admin_farms`. **RELEVANTE** ao desenhar owner/deploy do laboratório. |
| Alembic | Revisão aplicada não estabelecida no 01C | `alembic_version.version_num=20261022_agro_admin_01b1` | Estado de produção desconhecido; não declarar igualdade ou divergência de migration. **LACUNA RELEVANTE**. |
| Dados | Não copiados; fotografia não usada para fixture | Nenhum dado de negócio consultado | A contagem de estrutura não caracteriza dados locais. Fixtures 01E devem ser sintéticas. **INFORMATIVA**. |

### 4.1. Roles, ownership e efetividade local

Flags relevantes observadas no catálogo local:

| Role | LOGIN | SUPERUSER | BYPASSRLS | CREATEDB | CREATEROLE | Relação com objetos |
|---|---:|---:|---:|---:|---:|---|
| `borgus` | sim | não | não | não | não | Owner das 355 tabelas físicas de `farms`; owner do schema; concede/recebe membership conforme catálogo. |
| `admin_farms` | sim | não | **sim** | não | não | Membro de `borgus` com `INHERIT`; herda privilégios de ownership. |
| `postgres` | sim | **sim** | **sim** | sim | sim | Papel superuser do servidor; não foi usado para alterar objetos. |

As verificações de privilégios efetivos retornaram `true` para `admin_farms`, `borgus` e `postgres` em `USAGE`/`CREATE` do schema, `SELECT`/`INSERT` em `farms.tenants`, `UPDATE` em `farms.cadastros_produtos` e `USAGE` em uma sequence consultada. Isso confirma que a identidade `admin_farms` não serve de runtime isolado; ela herda do owner e ainda tem `BYPASSRLS`. Pela semântica do PostgreSQL, um owner pode ignorar RLS salvo quando FORCE estiver ativo; essa consequência estrutural não foi testada por leitura de linhas. `borgus` é owner e a tabela local `propriedade_imovel` está com RLS sem FORCE. Para a prova, a role runtime deve ser nova, sem membership que herde owner/admin e sem ownership.

As ACLs explicitamente armazenadas foram contadas sem inferir privilégios a partir de `relacl NULL`. Na Hostinger o extrato não expandiu ACLs padrão, `PUBLIC`, grants de database ou privilégios efetivos; por isso os dados não permitem afirmar que todos os acessos efetivos entre ambientes diferem apenas pelos números acima.

## 5. Reconciliação nominal de tabelas

Comparação de nomes exatos, apenas no schema `farms`:

| Conjunto | Quantidade |
|---|---:|
| Hostinger | 350 |
| Desenvolvimento | 355 |
| Presentes em ambos | 343 |
| Somente Hostinger | 7 |
| Somente desenvolvimento | 12 |
| União | 362 |

Consistência matemática: `343 + 7 = 350`, `343 + 12 = 355` e `350 + 355 − 343 = 362 = 343 + 7 + 12`.

**Somente na fotografia Hostinger:**

- `crm_ofertas_personalizadas`
- `crm_planos_comerciais`
- `crm_precificacao_modulo`
- `crm_produtos`
- `deepfarms_install_manifest`
- `deepfarms_install_version`
- `growth_landing_eventos`

Os dois objetos `deepfarms_install_*` já haviam sido identificados no 01C como técnicos. As cinco relações CRM/growth são objetos de produto/plataforma, não se deve inferir que sejam dados de Tenant apenas pelo nome.

**Somente no desenvolvimento:**

- `alembic_version`
- `amostras`
- `balanca_afericoes`
- `balanca_avaliacoes_prestador`
- `balanca_dispositivos`
- `balanca_fisicas`
- `balanca_operadores`
- `balanca_ordens`
- `balanca_pesagens`
- `balanca_sync_tombstones`
- `mapas_fertilidade`
- `territory_legacy_backup_01h2`

`alembic_version` é técnica; `territory_legacy_backup_01h2` aparenta ser backup legado pelo nome, mas seu conteúdo e finalidade não foram consultados. As tabelas `balanca_*`, `amostras` e `mapas_fertilidade` são estruturas adicionais locais; várias têm `tenant_id` e FKs, então não devem ser consideradas globais ou dispensáveis sem análise funcional. Classificação baseada só no nome é indicativa, não semântica comprovada.

## 6. RLS, policies, tenant_id e integridade relacional

### 6.1. Estados individuais de RLS

As 49 tabelas com RLS registradas na Hostinger estão presentes localmente com o mesmo estado RLS/FORCE. Além delas, três tabelas comuns estão protegidas localmente, mas estavam sem RLS na fotografia 01C:

- `cadastros_pessoas_usuarios`
- `estoque_requisicao_item_eventos`
- `estoque_requisicao_responsabilidades`

Em desenvolvimento: 52 tabelas com RLS e 51 com FORCE. Portanto, essas três diferenças explicam integralmente os totais 49→52 e 48→51. Isso não demonstra quando ou por qual migration o estado local mudou; Hostinger é uma fotografia anterior/independente, e a ordem temporal das alterações não foi comprovada.

### 6.2. Policies

| Schema/ambiente | Policies | Tabelas cobertas |
|---|---:|---:|
| Hostinger, `farms` | 188 | 49 |
| Desenvolvimento, `farms` | 200 | 52 |
| Desenvolvimento, schema `tara` | 31 | Fora do escopo da comparação Hostinger `farms` |
| Desenvolvimento, banco inteiro | 231 | Mais de um schema |

As 188 chaves Hostinger `(tabela, policyname)` estão presentes localmente. As 12 chaves adicionais em `farms` são quatro policies cada para `cadastros_pessoas_usuarios`, `estoque_requisicao_item_eventos` e `estoque_requisicao_responsabilidades`. As 31 policies `tara` são de outro schema e não foram misturadas à contagem `farms`. O dump Hostinger em formato alinhado/wrapped não permitiu uma reconciliação independente e integral das expressões locais `USING`/`WITH CHECK` nesta atualização; igualdade de nomes não equivale a igualdade comportamental.

### 6.3. Colunas `tenant_id`

- 275 nomes da Hostinger também possuem `tenant_id` no desenvolvimento e todos têm o mesmo tipo (`uuid` ou `character varying`) nos dois catálogos.
- Desenvolvimento tem 11 tabelas adicionais com `tenant_id`: `amostras`, `balanca_afericoes`, `balanca_avaliacoes_prestador`, `balanca_dispositivos`, `balanca_fisicas`, `balanca_operadores`, `balanca_ordens`, `balanca_pesagens`, `balanca_sync_tombstones`, `mapas_fertilidade` e `territory_legacy_backup_01h2`.
- A coluna `tenant_id` é nullable localmente em 25 tabelas, contra 22 na Hostinger. Além de três nomes locais adicionais nullable, há duas divergências entre nomes compartilhados: `frota_planos_manutencao` e `frota_registros_manutencao` são `NOT NULL` na Hostinger e nullable no desenvolvimento.
- A lista Hostinger de 22 nullable está preservada no 01C. Nenhuma semântica de `NULL`, globalidade ou uso foi inferida a partir da nullability.

### 6.4. Foreign keys

O catálogo local `farms` tem 936 FKs; a fotografia Hostinger tem 924. Comparando origem e definição sem qualificação de schema/nome da constraint, 893 são semanticamente equivalentes, 31 aparecem apenas na Hostinger e 43 apenas no desenvolvimento. Os números fecham: `893 + 31 = 924` e `893 + 43 = 936`.

Exemplos de diferença de ação referencial em tabela comum: nas quatro tabelas `agricola_devolucoes_embalagens`, `agricola_produto_colhido_cost_allocations`, `agricola_receituario_itens` e `agricola_receituarios_agronomicos`, a FK `tenant_id -> tenants(id)` aparece com `ON DELETE RESTRICT` na Hostinger e `ON DELETE CASCADE` no desenvolvimento. Exemplos de FKs presentes apenas na produção pertencem a tabelas CRM/growth também exclusivas da fotografia Hostinger; exemplos locais incluem FKs das tabelas `balanca_*` locais. As diferenças não provam registros inconsistentes, mas afetam o comportamento de deleção e integridade no ambiente de teste.

## 7. Cobertura e limitações do comparativo

| Evidência | Desenvolvimento | Hostinger no pacote 01C | Comparação alcançada |
|---|---|---|---|
| Relações e RLS/FORCE | Inventário completo em `farms` | Inventário nominal completo | Comparação nominal e de estado concluída. |
| Policies | 200 com expressões locais capturadas | 188 linhas em extrato psql; 01C reconcilia-as com contrato estático | Comparadas as 188 identidades; expressões locais × produção continuam pendentes. |
| Colunas | 4.846 colunas em `farms`, com tipo/nullability/default-presence | Apenas inventário específico de `tenant_id` utilizável para comparação | Comparação nominal/tipo/nullability concluída só para `tenant_id`; restante pendente. Nenhuma expressão de default foi exportada. |
| Constraints | PK, FK, UNIQUE, CHECK e validação consultados | Inventário completo de FK (924); demais tipos ausentes | FKs comparadas; PK/UNIQUE/CHECK sem contraparte Hostinger. |
| Índices | 1.517 em `farms` | Não listados no extrato | Sem comparação. |
| Roles, memberships, ACL e owner | Catálogo, ACLs armazenadas e amostra de privilégios efetivos | Roles, memberships, owners e ACL bruta do extrato | Diferenças principais registradas; grants efetivos Hostinger não calculados. |
| Sequences/funções/views/default ACL | 36 / 4 / 0 / 3 no escopo pertinente | 33 / 3 / 0 / 0 | Nomes e contagens comparados quando presentes; novos default privileges locais registrados. |
| Triggers/extensões | 4 triggers, extensão `plpgsql` | Não listados no extrato | Sem comparação de produção. |
| Alembic | revisão `20261022_agro_admin_01b1` | revisão aplicada não identificada | Não comparável. |

Pendências da fotografia de produção continuam sendo diferenças que não podem ser declaradas concluídas: inventário integral de colunas, índices, PK/UNIQUE/CHECK, triggers, extensões, expressões das policies no comparativo banco-a-banco, privilégios efetivos por role e versão Alembic aplicada. Nenhuma tentativa de preencher essas lacunas por inferência foi feita.

## 8. Adequação para a prova 01E

### Pode ser reaproveitado

- A instância confirmada é PostgreSQL 16.15, mesmo major reportado na Hostinger.
- Há catálogo local suficiente para escolher estruturas e compreender diferenças antes de montar fixtures.
- A fotografia local demonstra mecanismos reais de RLS e políticas em tabelas comuns, mas esse comportamento ainda não foi testado com role restrita.

### Não pode ser reaproveitado diretamente

- O database `farms` é o banco de desenvolvimento existente, não um laboratório novo comprovadamente descartável; nenhum dado de negócio foi consultado para qualificá-lo como sintético.
- `borgus` possui ownership de todas as tabelas `farms`; `admin_farms` tem `BYPASSRLS` e herda os privilégios de `borgus`. Usar qualquer um para a prova de isolamento invalidaria o teste.
- `borgus` não tem `CREATEDB` nem `CREATEROLE`. A disponibilidade de credencial administrativa independente para provisionar outro banco/roles não foi verificada nem tentada.
- Há diferença de tabelas, RLS/policies, nullability e FKs em relação à Hostinger; uma fixture derivada do schema local não deve ser apresentada como clone físico de produção.

### Recomendação objetiva

**GO COM RESSALVAS para usar a instância PostgreSQL 16 como plataforma de um novo laboratório**, somente se o responsável provisionar antes um database descartável e isolado, com roles owner/deploy/runtime próprias e fixtures sintéticas. Preferir fixture mínima explicitamente aprovada pela 01E; copiar somente DDL mínimo necessário, não o database nem seus dados.

**NO-GO para executar 01E dentro do database existente `farms`, criar objetos nele ou usar as roles `borgus`/`admin_farms` como runtime.** A aprovação desta comparação não provisiona laboratório e não inicia a 01E.

## 9. Condições de GO/NO-GO antes da 01E

### GO quando todos os itens abaixo forem comprovados

1. Operador disponibilizar um database novo, descartável e separado do `farms` atual, na instância PostgreSQL 16 identificada.
2. Provisionamento usar identidade administrativa explicitamente aprovada; não reutilizar `borgus` ou `admin_farms` como runtime.
3. Inventário do laboratório confirmar roles owner/deploy/runtime separadas; runtime sem `SUPERUSER`, `BYPASSRLS`, ownership, `CREATEDB`, `CREATEROLE` e memberships que herdem privilégios elevados.
4. Fixture conter apenas estrutura mínima e dados sintéticos dos casos definidos na 01E; nenhuma cópia de dado Hostinger ou do banco de desenvolvimento.
5. Antes dos testes, confirmar versão/DB/schema/roles do laboratório e que a identidade runtime efetiva é a restrita.

### NO-GO se

- Só houver acesso ao `farms` existente por `borgus`/`admin_farms`.
- Não for possível comprovar o isolamento do novo database e a ausência de acesso aos dados existentes.
- A role runtime possuir ownership, bypass ou herança administrativa.
- Fixtures dependerem de tabelas/estados cuja diferença local × Hostinger não foi reconciliada e afetar o caso testado.

## 10. Atividades realizadas e não realizadas

- Executadas consultas somente leitura de identidade e catálogo no endpoint de desenvolvimento confirmado; todas em transação `READ ONLY`.
- Consultada apenas a versão da linha de controle Alembic, como metadado. Nenhuma outra linha de aplicação foi consultada.
- Lidos o relatório 01C e seu extrato Hostinger local já fornecido; não houve acesso remoto à produção.
- Atualizado somente este relatório Markdown no repositório.
- Não foram criados banco, roles, policies ou grants; não houve DDL/DML, migrations, alterações de configuração, testes de escrita, teste RLS funcional ou execução da 01E.

## Referências

- [01C — Inventário real Hostinger](DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md)
- [01D — Plano de correção controlada](DEEPFARMS-RLS-HOSTINGER-01D-PLANO-CORRECAO-CONTROLADA.md)
- [01E — Prova de isolamento em laboratório](DEEPFARMS-RLS-HOSTINGER-01E-LABORATORIO-ISOLAMENTO.md)
- Extrato Hostinger fornecido pelo operador: `/tmp/deepfarms-rls-01c-metadados.txt`
- Snapshot local de catálogo: `/tmp/deepfarms-rls-01e0-dev-catalog.json`
- Configuração/código consultados sem revelar credenciais: `services/api/core/config.py`, `services/api/core/database.py`, `services/api/.env.local`
