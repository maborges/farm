# MIGRATION-METADATA-01A — Auditoria de Registro de Models

**Fase:** 01A — Auditoria de registro de models e preparação da baseline  
**Data da auditoria:** 2026-09-08  
**Escopo:** somente leitura/análise de código, models e migrations.  
**Veredicto:** **NO-GO** para criação da baseline nesta fase.

## 1. Resumo executivo

O `services/api/migrations/env.py` usa `Base.metadata` como `target_metadata`, mas constrói esse metadata por meio de uma lista manual de imports. O resultado atual registra **309 tabelas**.

O inventário estático dos módulos de models do backend encontrou **373 tabelas declaradas**, e a importação controlada de todos esses módulos registrou **373 tabelas**, sem falhas de importação. Assim, há **64 tabelas de models ausentes do `env.py` atual**.

Das 42 tabelas apresentadas como presentes no banco funcional e ausentes do metadata atual:

- **30** são models ativos que não são importados pelo `env.py`;
- **1** é `alembic_version`, infraestrutura do Alembic;
- **2** são tabelas criadas por migration sem model ORM atual (`amostras`, `mapas_fertilidade`), candidatas a legado órfão;
- **1** é backup territorial explícito (`territory_legacy_backup_01h2`);
- **8** são tabelas `balanca_*` sem referência encontrada no DeepFarms atual, provavelmente legado de uma implementação acoplada ou pertencente à Plataforma Balança externa.

Conclusão: o metadata atual não representa de forma completa e confiável o schema funcional. A baseline não deve ser criada antes de definir o registry canônico, separar tabelas ORM ativas de tabelas DDL/legado e fechar a origem das tabelas antigas da Balança.

## 2. Estado atual verificado

| Item | Evidência |
|---|---|
| Banco funcional informado | 351 BASE TABLES no schema `farms` |
| `env.py` atual | `target_metadata = Base.metadata` |
| Metadata atual | 309 tabelas |
| Diferença física informada | 42 tabelas |
| Inventário estático de models | 373 `__tablename__` únicos fora de migrations, testes e `.venv` |
| Importação controlada de todos os módulos | 373 tabelas, 0 falhas |
| Alembic heads | `20260828_balanca_webhook_credentials` |
| Schema configurado pelo env | `farms`, via `CREATE SCHEMA IF NOT EXISTS` e `SET search_path TO farms` |

A contagem física de 351 foi tratada como evidência fornecida para esta auditoria. Não foi feita conexão ao RDS nem executado `upgrade`, `autogenerate`, `create_all`, `drop_all` ou alteração de banco.

## 3. Explicação do 351 × 309

Os números fecham exatamente:

```text
351 tabelas físicas
- 42 tabelas físicas ausentes do metadata atual
= 309 tabelas registradas no metadata atual
```

O número 309, portanto, não significa que o metadata seja o schema completo; significa apenas que ele coincide com o subconjunto físico depois de retirar as 42 divergências listadas. O inventário de código revela uma segunda diferença: existem mais 64 models declarados que também não são carregados pelo `env.py`, mesmo quando suas tabelas não aparecem no banco funcional atual.

## 4. Método e limitações

Foram analisados:

- `services/api/migrations/env.py`;
- todos os arquivos Python de `services/api`, excluindo `.venv`, `migrations`, `__pycache__` e testes para o inventário de models;
- declarações `__tablename__`, `Base`, `declarative_base`, `Table` e `metadata`;
- todas as migrations em `services/api/migrations/versions`;
- `services/api/seed.py`, `services/api/scripts/init_postgres_schema.py` e `services/api/scripts/sync_db.py`;
- referências de runtime em routers, services e `main.py`.

O carregamento completo foi feito por introspecção, sem executar o bloco final de execução do `env.py`. O import controlado adicionou 64 tabelas ao conjunto inicial de 309 e não encontrou exceções.

## 5. Inventário dos models

O inventário encontrou **373 tabelas únicas** declaradas por models de produção. O `env.py` atual carrega 309. O inventário completo está representado pelo conjunto de módulos abaixo; os 64 ausentes são detalhados na seção 7.

Principais grupos registrados atualmente:

- Core, autenticação, billing, pessoas, propriedades, produtos, commodities e equipamentos;
- Agrícola: safras, cultivos, operações, caderno, clima, NDVI, rastreabilidade, receituário, custos e beneficiamento;
- Operacional: estoque, compras, frota, abastecimento, apontamentos, qualidade e implantação;
- Financeiro, hedge, comercialização e lançamentos;
- Pecuária, manejo, produção leiteira e módulos avançados;
- IA, alertas, recomendações, automações e wizard;
- integrações canônicas, Sankhya e New Holland;
- RH, ambiental, certificações e imóveis.

### 5.1 Duplicidades de `__tablename__`

No inventário de produção, excluindo `.venv`, testes e migrations, não foi encontrada duplicidade de `__tablename__` entre dois models diferentes.

Foram observadas duplicidades semânticas ou coexistência de gerações:

- `HedgeRegistro` em `enterprise/models/sprints_27_33.py` (`hedge_registros`) coexistindo com o modelo moderno de hedge (`hedge_registros_v2`);
- models `enterprise/models/sprints_27_33.py` coexistindo com módulos modernos de pecuária e integrações;
- tabelas de carbono criadas em mais de uma migration histórica, com migrations posteriores usando verificações de existência;
- migrations de reparo que alteram tabelas criadas por migrations anteriores.

Isso não é uma colisão ORM direta, mas precisa ser resolvido explicitamente na baseline para evitar materializar entidades históricas incompatíveis.

## 6. Matriz obrigatória das 42 divergências

Legenda: **A** model ativo sem registro no `env.py`; **B** tabela estrutural criada por DDL/migration; **C** legado ainda suportado; **D** backup/transitória; **E** órfã/deprecada; **F** pertencente a outro sistema ou implementação externa.

| Tabela | Model/módulo | `env.py` | Migration/DDL | Runtime | Classe |
|---|---|---:|---|---|:---:|
| `agricola_devolucoes_embalagens` | `DevolucaoEmbalagem` — `agricola/logistica_reversa_embalagens/models.py` | Não | `20260815_logistica_reversa_embalagens.py` | Router/service de logística reversa | A |
| `alembic_version` | Infraestrutura Alembic | Não aplicável | Gerenciada pelo Alembic | Controle de revisões | B |
| `amostras` | Sem model ORM localizado | Não | `09df6fa43b49_add_carbono_projetos.py` cria e remove | Nenhum uso de tabela; ocorrências são campos/variáveis | E |
| `animal_genetica` | `AnimalGenetica` — `enterprise/models/sprints_27_33.py` | Não | `67b25594e50e_add_animal_genetica.py` | `advanced_service.py` e rotas enterprise | A |
| `balanca_afericoes` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_avaliacoes_prestador` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_dispositivos` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_fisicas` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_operadores` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_ordens` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `balanca_pesagens` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso; o model antigo encontrado chama-se `pesagens` | F |
| `balanca_sync_tombstones` | Nenhum model/ref. localizado | Não | Nenhuma migration/ref. localizada | Nenhum uso no DeepFarms atual | F |
| `carbono_emissoes` | `CarbonoEmissao` — `iot_integracao/new_holland/models/__init__.py` | Não | `fase3_sprints26_34.py`, `20260901_carbono_schema.py`, lifecycle | Routers ambientais e services de carbono | A |
| `carbono_projetos` | `CarbonoProjeto` — mesmo módulo | Não | `09df6fa43b49`, `fase3_sprints26_34.py`, repairs e schema 20260901 | Routers ambientais e services de carbono | A |
| `carbono_relatorios` | `CarbonoRelatorio` — mesmo módulo | Não | `fase3_sprints26_34.py`, `20260901_carbono_schema.py` | Router ambiental de relatórios | A |
| `cochos` | `Cocho` — `enterprise/models/sprints_27_33.py` | Não | `fase3_sprints27_33_final.py` | Service/router enterprise de confinamento | A |
| `confinamento_lotes` | `ConfinamentoLote` — `enterprise/models/sprints_27_33.py` | Não | `67b25594e50e_add_confinamento_models.py` e final enterprise | Service/router enterprise | A |
| `estoque_contagem_itens` | `ContagemEstoqueItem` — `operacional/models/contagem_estoque.py` | Não | `20260815_estoque_contagens.py` | Operacional/estoque | A |
| `estoque_contagens` | `ContagemEstoque` — mesmo módulo | Não | `20260815_estoque_contagens.py` | Operacional/estoque | A |
| `imoveis_ordens_servico_benfeitoria` | `OrdemServicoBenfeitoria` — `imoveis/models/manutencao_benfeitoria.py` | Não | `20260815_manutencao_benfeitoria.py` | `main.py`, router e service de imóveis | A |
| `imoveis_planos_manutencao_benfeitoria` | `PlanoManutencaoBenfeitoria` — mesmo módulo | Não | `20260815_manutencao_benfeitoria.py` | `main.py`, router e service de imóveis | A |
| `imoveis_sistemas_irrigacao` | `SistemaIrrigacao` — `imoveis/models/irrigacao.py` | Não | `20260816_imoveis_irrigacao.py` | `main.py`, router e service de irrigação | A |
| `mapas_fertilidade` | Sem model ORM localizado | Não | `09df6fa43b49_add_carbono_projetos.py` | Nenhum model/service de tabela localizado | E |
| `planos_operacionais` | `PlanoOperacional` — `agricola/planejamento_operacional/models.py` | Não | `20260726a_plano_operacional.py` e repairs | `main.py`, router e services | A |
| `planos_operacionais_tarefas` | `PlanoOperacionalTarefa` — mesmo módulo | Não | `20260726a_plano_operacional.py` | Router/service de planejamento | A |
| `planos_operacionais_tarefas_insumos` | `PlanoOperacionalTarefaInsumo` — mesmo módulo | Não | `20260726c_plano_operacional_tarefa_insumo.py` | Router/service de planejamento | A |
| `planos_operacionais_tarefas_mao_obra` | `PlanoOperacionalTarefaMaoObra` — mesmo módulo | Não | `20260726e_plano_operacional_mao_obra.py` | Router/service de planejamento | A |
| `planos_operacionais_tarefas_maquinario` | `PlanoOperacionalTarefaMaquinario` — mesmo módulo | Não | `20260728_plano_operacional_maquinario.py` | Router/service de planejamento | A |
| `racas` | `Raca` — `enterprise/models/sprints_27_33.py` | Não | `67b25594e50e_add_animal_genetica.py` | Service/router enterprise | A |
| `racoes_tmr` | `RacaoTMR` — `enterprise/models/sprints_27_33.py` | Não | `fase3_sprints27_33_final.py` | Service/router de confinamento | A |
| `receitas_aplicacao` | `ReceitaAplicacao` — `agricola/receitas_aplicacao/models.py` | Não | `20260727_receitas_aplicacao.py` | `main.py`, router/service e uso real | A |
| `receitas_aplicacao_insumos` | `ReceitaAplicacaoInsumo` — mesmo módulo | Não | `20260727_receitas_aplicacao.py` | Router/service de receitas | A |
| `receitas_aplicacao_mao_obra` | `ReceitaAplicacaoMaoObra` — mesmo módulo | Não | `20260727_receitas_aplicacao.py` | Router/service de receitas | A |
| `sankhya_config` | `SankhyaConfig` — `integracoes/sankhya/models/__init__.py` | Não | `fase3_sankhya.py` e migrations de gateway | Adapter/routers Sankhya | A/C |
| `sankhya_lancamentos_financeiros` | `SankhyaLancamentoFinanceiro` — mesmo módulo | Não | `fase3_sankhya.py` e `20260718_sankhya_ids.py` | Staging/provider Sankhya | A/C |
| `sankhya_nfe` | `SankhyaNFe` — mesmo módulo | Não | `fase3_sankhya.py` e migrations de chaves | Staging/provider Sankhya | A/C |
| `sankhya_pessoas` | `SankhyaPessoa` — mesmo módulo | Não | `fase3_sankhya.py` e migrations de chaves | Adapter canônico e compatibilidade Sankhya | A/C |
| `sankhya_produtos` | `SankhyaProduto` — mesmo módulo | Não | `fase3_sankhya.py` e migrations de chaves | Adapter canônico e compatibilidade Sankhya | A/C |
| `sankhya_sync_logs` | `SankhyaSyncLog` — mesmo módulo | Não | `fase3_sankhya.py` e repairs de tenant | Logs de sincronização | A/C |
| `sankhya_tabelas` | `SankhyaTabela` — mesmo módulo | Não | `fase3_sankhya.py` e repairs de tenant | Staging/provider Sankhya | A/C |
| `sugestoes_acasalamento` | `SugestaoAcasalamento` — `enterprise/models/sprints_27_33.py` | Não | `67b25594e50e_add_animal_genetica.py` | Service/router enterprise | A |
| `territory_legacy_backup_01h2` | Sem model ORM por desenho | Não | `265b28773962_territory_convergence_remove_legacy_.py` | Backup usado em convergência/guardrails | D |

Observação: as classificações `A/C` de Sankhya significam que são models ativos, mas representam staging/provider-specific legado ainda suportado. Não devem ser removidos, renomeados ou consolidados nesta fase.

## 7. Models ativos ausentes do `env.py`

Além das 30 tabelas ausentes que já existem fisicamente, foram localizados outros models ativos não carregados pelo `env.py`. O import controlado de todos os módulos foi bem-sucedido e elevou o registro para 373 tabelas.

| Grupo | Tabelas e módulos |
|---|---|
| API pública | `api_keys`, `api_logs`, `api_versions` — `core/api_publica/models/` |
| Agrícola/NDVI | `balanco_hidrico`, `estacoes_meteorologicas`, `imagens_satelite`, `ndvi_registros` — `agricola/ndvi_avancado/models/` |
| CRM/Growth | `crm_ofertas_personalizadas`, `crm_planos_comerciais`, `crm_precificacao_modulo`, `crm_produtos` — `core/models/crm_ofertas.py`; `growth_landing_eventos` — `growth/models.py` |
| Enterprise | `arracoamentos`, `benchmarks`, `colaborador_apontamentos`, `contratos_futuros`, `enterprise_esg_relatorios`, `esg_indicadores`, `hedge_registros`, `ilpf_modulos`, `mrv_projetos`, `mrv_relatorios`, `pesagens`, `pontos`, `powerbi`, `preditivo`, `sap`, `sensores_iot`, `sensores_leituras`, `tanques_rede` — `enterprise/models/` |
| Integração New Holland | `integracao_new_holland`, `maquinas_new_holland`, `marketplace_avaliacoes`, além dos três models de carbono — `iot_integracao/new_holland/models/` |
| Operacional | `estoque_contagens`, `estoque_contagem_itens` — `operacional/models/contagem_estoque.py` |
| Imóveis | `imoveis_ordens_servico_benfeitoria`, `imoveis_planos_manutencao_benfeitoria`, `imoveis_sistemas_irrigacao` — `imoveis/models/` |
| Planejamento/receitas | cinco tabelas de `planos_operacionais*` — `agricola/planejamento_operacional/models.py`; três tabelas de `receitas_aplicacao*` — `agricola/receitas_aplicacao/models.py` |
| Sankhya | `sankhya_config`, `sankhya_lancamentos_financeiros`, `sankhya_nfe`, `sankhya_pessoas`, `sankhya_produtos`, `sankhya_sync_logs`, `sankhya_tabelas` — `integracoes/sankhya/models/__init__.py` |

Os models `animal_genetica`, `cochos`, `confinamento_lotes`, `racas`, `racoes_tmr` e `sugestoes_acasalamento` são consumidos por `pecuaria/advanced_service.py` e pelos routers enterprise, portanto não podem ser tratados automaticamente como código morto.

## 8. Tabelas físicas sem model atual

Com base na lista física informada e no inventário estático:

- `alembic_version`: infraestrutura do Alembic, não é model de domínio;
- `amostras`: criada por `09df6fa43b49_add_carbono_projetos.py`, mas sem model ou uso de tabela localizado;
- `balanca_afericoes`, `balanca_avaliacoes_prestador`, `balanca_dispositivos`, `balanca_fisicas`, `balanca_operadores`, `balanca_ordens`, `balanca_pesagens`, `balanca_sync_tombstones`: sem model/ref. no código atual;
- `mapas_fertilidade`: criada em migration, sem model ORM localizado;
- `territory_legacy_backup_01h2`: backup DDL explícito, sem model por desenho.

Não há evidência de que `amostras` seja uma entidade ORM ativa: as ocorrências atuais são campos/variáveis de contagem e amostras de diagnóstico. A migration histórica cria a tabela junto de estruturas de carbono e depois possui downgrade que a remove.

## 9. Models sem tabela física observada

Os 34 models ausentes da lista das 42 tabelas físicas são, por evidência disponível, models declarados no código sem correspondente entre as 351 BASE TABLES informadas. Isso não prova que sejam inválidos; significa que o banco funcional atual não contém essas tabelas.

São eles:

```text
api_keys, api_logs, api_versions,
arracoamentos, balanco_hidrico, benchmarks, colaborador_apontamentos,
contratos_futuros, crm_ofertas_personalizadas, crm_planos_comerciais,
crm_precificacao_modulo, crm_produtos, enterprise_esg_relatorios,
esg_indicadores, estacoes_meteorologicas, growth_landing_eventos,
hedge_registros, ilpf_modulos, imagens_satelite, integracao_new_holland,
maquinas_new_holland, marketplace_avaliacoes, mrv_projetos, mrv_relatorios,
ndvi_registros, pesagens, pontos, powerbi, preditivo, sap, sdks,
sensores_iot, sensores_leituras, tanques_rede
```

`pesagens` merece atenção especial: existe model enterprise com esse nome, mas a tabela física informada é `balanca_pesagens`, que não corresponde ao `__tablename__` encontrado.

## 10. Migrations e duplicidades de criação

Foram encontrados sinais de cadeia histórica não linear e DDL repetido/defensivo:

- `09df6fa43b49_add_carbono_projetos.py` cria `amostras`, `mapas_fertilidade` e estruturas de carbono;
- `fase3_sprints26_34.py` também cria estruturas de carbono;
- `27120602eeb5_create_missing_hedge_table.py` remove/recria `carbono_projetos` como parte de reparo;
- `20260901_carbono_schema.py` cria as tabelas de carbono somente quando não existem;
- `planos_operacionais*`, `receitas_aplicacao*`, Sankhya, confinamento e genética foram distribuídos em várias migrations e posteriores repairs;
- `001_notas_fiscais.py` é root histórico (`down_revision = None`) e cria ENUMs/tabela de notas fiscais sem estabelecer previamente todo o core.

Isso confirma que a linhagem histórica não deve ser reaplicada cegamente para gerar o banco piloto.

## 11. Diagnóstico específico da Balança

### 11.1 Tabelas antigas

As oito tabelas abaixo não possuem ocorrência em models, routers, services ou migrations atuais do DeepFarms:

```text
balanca_afericoes
balanca_avaliacoes_prestador
balanca_dispositivos
balanca_fisicas
balanca_operadores
balanca_ordens
balanca_pesagens
balanca_sync_tombstones
```

Classificação atual: **F — provável implementação antiga/acoplada ou objeto da Plataforma Balança externa**. A classificação deve ser confirmada por catálogo/metadata do banco funcional ou histórico de deployment, mas não há base de código atual que exija essas tabelas.

### 11.2 Integração atual

O DeepFarms atual usa HTTP para a Plataforma Balança e mantém apenas estruturas próprias de integração:

- `balanca_inbound_events`;
- `balanca_webhook_credentials`.

Essas duas tabelas possuem models em `integracoes/models.py`, migrations próprias em `20260828_balanca_inbound_events.py` e `20260828_balanca_webhook_credentials.py`, RLS e políticas. A cadeia atual termina em `20260828_balanca_webhook_credentials`.

Não há evidência de dependência atual das oito tabelas antigas. Não devem ser recriadas na baseline sem prova de ownership do DeepFarms.

## 12. Diagnóstico específico Sankhya

Os models em `services/api/integracoes/sankhya/models/__init__.py` existem e são importáveis, mas não são registrados pelo `env.py` atual. As tabelas são criadas historicamente por `fase3_sankhya.py` e alteradas por migrations de autenticação, IDs externos, numeric monetário e integridade de tenant.

O código atual possui adapter canônico, routers e jobs que referenciam essas estruturas. Portanto:

- devem ser consideradas estruturas provider-specific suportadas;
- não devem ser removidas, renomeadas ou consolidadas nesta auditoria;
- precisam entrar no registry da futura baseline, caso o escopo do piloto mantenha Sankhya ativo;
- `tenant_integracoes`/`TenantIntegracao` continuam sendo o core multiprovider oficial e não devem ser substituídos pelas tabelas de staging.

## 13. Estruturas PostgreSQL fora de `Base.metadata`

### Confirmadas no código/migrations

- schema `farms`, criado/garantido pelo `env.py`, com `SET search_path TO farms`;
- `alembic_version`, objeto de controle do Alembic;
- ENUMs PostgreSQL, incluindo `tiponotafiscal`, `statussefaz`, `tipodiagnostico` e ENUMs de certificação/ESG;
- RLS com `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL SECURITY`;
- `CREATE POLICY` e `DROP POLICY` em `propriedade_imovel`, certificações/ESG, integrações, links externos, alertas operacionais, clima e Balança;
- DDL manual via `op.execute`, incluindo alterações de constraints, índices, colunas, search-path e commits explícitos;
- índices e constraints criados manualmente que podem não ser reconstituídos por autogenerate;
- sequência/tabela de sequenciais de domínio, incluindo `core_sequenciais`.

### Não confirmadas nas migrations

Não foi encontrada nas migrations uma instrução `CREATE EXTENSION`, `CREATE FUNCTION`, `CREATE TRIGGER`, `CREATE VIEW` ou `MATERIALIZED VIEW`. Também não foi encontrada declaração de PostGIS (`Geometry`/`Geography`) nas migrations. Há uso de geometrias como GeoJSON/dados de aplicação e dependências geoespaciais em runtime, mas isso não prova a necessidade de extensão PostGIS no schema piloto.

`pg_stat_statements` aparece em scripts operacionais de performance (`setup_performance_db.py` e `performance_baseline.py`), não na linhagem Alembic; deve ser tratado como requisito de infraestrutura opcional do RDS, não como parte automática da baseline.

A baseline futura deverá inventariar no RDS, além de BASE TABLES:

- schemas e owners;
- ENUMs e seus valores;
- sequences;
- constraints e índices;
- políticas e flags RLS;
- extensões habilitadas;
- funções, triggers e views, caso existam no banco funcional;
- privilégios/grants necessários.

## 14. `env.py` como agregador manual

Sim. O arquivo contém uma longa sequência de imports explícitos por módulo, incluindo imports com `*`, e termina em `target_metadata = Base.metadata`. Isso faz do `env.py` um agregador manual de models, embora sua responsabilidade primária devesse ser configurar o ambiente de migration.

Consequências observadas:

- novos models podem existir e ser usados em runtime sem entrar no metadata;
- não há falha automática quando o registry fica incompleto;
- o número de tabelas do metadata pode coincidir parcialmente com o banco e mascarar ausências;
- imports históricos/enterprise e models modernos ficam sem política explícita de inclusão;
- o autogenerate não seria confiável mesmo que a cadeia histórica fosse executável.

## 15. Estratégia recomendada para registro

Recomendação arquitetural, sem implementação nesta fase:

1. Criar um ponto único e explícito de registro, preferencialmente um módulo dedicado como `core/model_registry.py` ou `core/models/registry.py`.
2. O registry deve importar somente models de produção aprovados, sem depender de imports incidentais de routers/services.
3. O registry deve expor uma função idempotente de carregamento e uma lista/relatório verificável de tabelas.
4. O `env.py` deve consumir esse registry, sem manter sua própria lista extensa de imports.
5. O registry deve separar explicitamente:
   - models ativos da aplicação;
   - tabelas DDL-only/infrastrutura;
   - legado suportado;
   - backups/transitórias excluídos da baseline;
   - objetos de outro sistema.
6. Deve existir um teste de guardrail que compare o registry esperado, os `__tablename__` de produção e as tabelas aprovadas para a baseline.

`core/models/__init__.py` é um candidato parcial, mas atualmente também agrega vários domínios e não representa sozinho todos os models do projeto; por isso, um registry explícito é mais seguro.

## 16. Diagnóstico de bootstrap e seed

### `services/api/seed.py`

Mistura responsabilidades:

- `prepare_schema()` executa `Base.metadata.drop_all` quando `SEED_FORCE=true`;
- executa `Base.metadata.create_all` sempre;
- depois insere tenant, plano, assinatura, fazendas, culturas, áreas, safra, operação, financeiro e pecuária fictícios.

Logo, mistura bootstrap estrutural, reset destrutivo e seed demo/dev.

### `services/api/scripts/init_postgres_schema.py`

Importa um subconjunto manual de models e executa `Base.metadata.create_all`. Não é um registry completo e não deve ser usado para bootstrap do RDS piloto.

### `services/api/scripts/sync_db.py`

Importa `core.models` e executa `Base.metadata.create_all`, novamente misturando sincronização estrutural fora do Alembic.

### Categorias de dados a separar futuramente

| Categoria | Exemplos | Deve estar na baseline? |
|---|---|---:|
| Bootstrap estrutural | schema, tabelas, ENUMs, índices, constraints, RLS, policies | Sim |
| Institucional obrigatório | catálogos mínimos e configurações necessárias ao funcionamento | Não; seed versionado separado |
| Catálogo/base | culturas, unidades, tipos e classificações | Não; seed controlado separado |
| Demo/dev | tenant demo, fazendas fictícias, dados de teste | Não |
| Usuários fictícios | usuários e credenciais de demonstração | Não |
| Dados reais de tenant | qualquer dado operacional/financeiro | Não |

O seed atual contém explicitamente dados fictícios e contas bancárias de `DRY RUN`; não deve ser executado como parte do bootstrap do piloto.

## 17. Riscos para `BASELINE-DEEPFARMS-V1`

1. Criar a baseline a partir de 309 tabelas omitirá models ativos.
2. Importar todos os 373 indiscriminadamente pode incluir tabelas enterprise/legadas que não pertençam ao escopo piloto.
3. Reaplicar migrations históricas pode encontrar dependências implícitas do root `001_notas_fiscais` e DDL duplicado.
4. ENUMs, RLS, policies, índices e DDL manual podem ser perdidos se a baseline for derivada apenas de ORM.
5. Recriar as oito tabelas antigas de Balança confundiria o limite entre DeepFarms e Plataforma Balança.
6. Remover as tabelas Sankhya quebraria provider-specific staging ainda suportado.
7. Usar `seed.py` no RDS pode executar `create_all`, reset destrutivo ou inserir dados demo.
8. O schema `farms` precisa ser tratado explicitamente; `public` não é o schema oficial informado.

## 18. Menor correção necessária antes da baseline

Sem alterar nesta fase, a menor intervenção necessária é:

1. aprovar a taxonomia de inclusão/exclusão das 373 tabelas de models;
2. localizar e classificar definitivamente os 34 models sem tabela física observada;
3. confirmar a ownership das oito tabelas antigas `balanca_*` no banco funcional;
4. criar um registry único de models aprovado;
5. fazer o registry registrar pelo menos os 30 models ativos das 42 divergências;
6. inventariar objetos PostgreSQL que não são representados por ORM;
7. separar bootstrap estrutural de seed em artefatos independentes;
8. testar a geração da baseline em PostgreSQL descartável, nunca diretamente no RDS piloto.

## 19. Critérios de aceite para iniciar a baseline

A fase de baseline só deve começar quando todos forem verdadeiros:

- [ ] O registry canônico possui lista aprovada de models de produção.
- [ ] O metadata esperado é reproduzível e a contagem está documentada.
- [ ] Os 30 models ausentes das 42 divergências estão no registry ou formalmente excluídos.
- [ ] Os 34 models sem tabela física foram classificados por escopo/adoção.
- [ ] As oito tabelas antigas da Balança têm ownership documentada.
- [ ] Sankhya está classificado como provider-specific suportado ou explicitamente fora do piloto, sem remoção de código.
- [ ] ENUMs, RLS, policies, constraints, índices, sequences e demais DDL manual estão inventariados.
- [ ] O root histórico antigo foi declarado fora da linhagem ativa da baseline.
- [ ] Nenhum artefato de seed chama `create_all` no fluxo de bootstrap.
- [ ] O bootstrap e o seed foram separados conceitualmente e operacionalmente.
- [ ] Um teste em PostgreSQL vazio descartável comprova `alembic upgrade head` da nova baseline.
- [ ] O RDS piloto ainda não foi alterado.

## 20. Veredicto final

### MIGRATION-METADATA-01A

**STATUS: NO-GO**

Resposta explícita à pergunta central:

> Hoje, o `Base.metadata` carregado pelo Alembic representa de forma completa e confiável o schema funcional atual do DeepFarms?

**Não.**

O metadata atual registra 309 tabelas, enquanto o carregamento controlado de todos os models de produção registra 373. Há 30 models ativos ausentes entre as 42 divergências físicas, outros 34 models sem tabela física observada, DDL-only/legado não representado por ORM, estruturas antigas da Balança sem ownership fechada e uma cadeia histórica com duplicidades e dependências implícitas.

### Próxima fase

**FASE 01B — Definição e implementação controlada do registry canônico de models e matriz de escopo da baseline.**

Essa próxima fase deverá continuar sem alterar migrations históricas ou o RDS até que o registry e a matriz de objetos PostgreSQL estejam aprovados. A criação da `BASELINE-DEEPFARMS-V1` deve ocorrer somente depois dos critérios de aceite desta auditoria serem atendidos.
