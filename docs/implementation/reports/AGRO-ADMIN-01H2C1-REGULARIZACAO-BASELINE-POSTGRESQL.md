# AGRO-ADMIN-01H2C1 — Regularização do Baseline PostgreSQL para Homologação

**Modalidade:** auditoria arquitetural e correções controladas, sem migrations  
**Veredicto:** **NO-GO para preparar ou executar migration em banco de homologação**

## Escopo e segurança

Foram inspecionados o relatório 01H2C, `baseline_contract.py`, a revisão `baseline_deepfarms_v1`, `migrations/env.py`, o histórico Alembic e os relatórios MIGRATION-METADATA 01C4A, 01C4B, 01C4C, 01D, 01D2, 01D4 e 01D5. A análise e geração SQL offline foram estáticas, com URL sintética; não houve conexão com banco, execução de migration, inicialização de serviço ou chamada a provedor. Nenhum schema, dado ou arquivo de configuração comercial foi alterado. Não foi feita correção de código: as falhas observadas dependem de decisão/validação PostgreSQL e alterar o caminho agora poderia esconder divergências.

## 1. Causa raiz do NO-GO

O `CONTRACT_STATUS = "NO-GO"` em `services/api/migrations/baseline_contract.py` não representa com precisão o estado dos fechamentos posteriores: ainda enumera como pendentes divergências já tratadas estaticamente (FK, tipo/default de compilação, RLS/policies, funções/triggers e índices ORM), ao mesmo tempo em que mantém pendências legítimas de UNIQUE/CHECK sem contrato por objeto. Não alterei o status nem os contadores.

O impeditivo real é mais amplo que esse contador:

1. **Não existe prova de instalação em PostgreSQL vazio.** O relatório MIGRATION-METADATA-01D registra que a conta disponível não tinha `CREATEDB`; RLS, policies, funções/triggers, constraints, permissões e comportamento do ORM não foram validados em servidor PostgreSQL descartável.
2. **O SQL offline diverge do caminho online para `alembic_version`.** `env.py` configura `search_path=farms` somente em `do_run_migrations()` online. A geração offline baseline-only examinada começa criando `alembic_version` sem schema (`CREATE TABLE alembic_version`, linha 3), só depois cria `farms` e altera `search_path`; ao final, o INSERT também é não qualificado. Portanto, o artefato não comprova criação/coerência da tabela de versão no schema pretendido em banco vazio.
3. **A integração baseline/head tem uma linhagem histórica adicional.** A revisão de merge `20260915_merge_documentos_fiscais` declara como pais `baseline_deepfarms_v1` e `20260914_documentos_fiscais`. Um banco iniciado apenas pelo baseline não contém automaticamente os efeitos da outra linhagem. O merge é vazio, não substitui esses efeitos.
4. **A tentativa de gerar SQL de baseline até o head não é prova de falha online**, mas falha no modo offline quando uma revisão histórica chama `sa.inspect(bind)` (`8c2e891d6ba9_caderno_campo.py`). O `MockConnection` do Alembic não oferece inspeção. A revisão pode funcionar online com conexão real; isso ainda precisa ser demonstrado em instância isolada.
5. **Há divergências funcionais sem reconciliação semântica final.** UNIQUE e CHECK seguem sem contratos explícitos por objeto. As contagens antigas vieram de comparação de referência de 2026-09-08 e não devem ser tratadas como fotografia alinhada ao ORM/head atual.

## 2. Inventário e classificação do contrato

| Divergência/objeto | Evidência atual | Classificação | Consequência |
|---|---|---|---|
| FKs: antigo texto diz 248 tabelas divergentes | Relatório 01D4 fixa 892 FKs; zero alvo ausente, incompatibilidade de tipo PG, FK composta sem PK/UNIQUE ou CHECK referenciando coluna ausente. 01C4A/01D4 documentam as decisões Tenant Integrity. | **Compatibilidade histórica**; fechamento estático | O texto de `UNRESOLVED_STRUCTURAL_AREAS` é obsoleto. A criação real ainda requer PG. `animal_genetica.animal_id` sem FK é decisão histórica explicitada no contrato; não adicionar FK por inferência. |
| Nullable | Dez decisões explícitas conforme ORM/Tenant Integrity | **Diferença intencional documentada** | Não reproduzir nulabilidade antiga automaticamente. |
| Tipos: 489 diferenças históricas | 01C4C separa diferenças de representação (VARCHAR/CHARACTER VARYING, renderização FLOAT) dos blockers de CREATE; 01D4 corrige tipos UUID incompatíveis encontrados nos models | **Compatibilidade histórica**; bloqueador sintático reportado como zero | Isso não certifica equivalência semântica de todos os tipos nem runtime. |
| Defaults: relatórios registram 481 diferenças históricas; contrato antigo menciona 383 presença + 98 expressão | Defaults Python-side são excluídos do DDL; 01C4C reporta zero server defaults obrigatórios pendentes | **Compatibilidade histórica** | Divergência não prova paridade de defaults de produção. Não há decisão segura para aplicar correções históricas em massa. |
| UNIQUE: 11 tabelas no texto antigo; snapshot de referência antigo contém diferenças que variam conforme contagem por tabela/nome | `UNIQUE_CONTRACT = {}`; 01D4 valida pais de FKs compostas, não fecha equivalência completa de constraints UNIQUE | **Funcional e bloqueante** para declarar integridade equivalente | Fazer inventário atual objeto a objeto e classificar cada constraint antes da prova de criação. Não copiar uniques antigas cegamente. |
| CHECK: 39 tabelas no texto antigo | `CHECK_CONTRACT = {}`; 01D4/01D5 verificam referências/colunas inválidas, mas não demonstram paridade semântica integral contra um schema físico alinhado à versão atual | **Funcional e bloqueante** para declarar integridade equivalente | Validar expressão, comportamento e colunas em PG; não assumir que “coluna existe” significa equivalência funcional. |
| Índices: 327 tabelas divergentes no snapshot antigo | 01D5 verifica 1.029 índices declarados pelo ORM, sem nomes duplicados, colisões/redundância de unique ou colunas ausentes; corrige duplicação de `ix_campo_tarefas_type` | **Pendência não bloqueante** para criação estrutural; **compatibilidade histórica**/performance pendente | A contagem 327 é de referência antiga, não de índice ausente no baseline atual. Exigir revisão de performance antes de afirmar paridade física; não bloquear clean install apenas por contagem antiga. |
| ENUMs | Contrato registra 34 tipos/146 valores | **Diferença intencional documentada**, derivada do conjunto atual | Fechamento estático de catálogo; confirmação no PG permanece pendente. |
| Sequences | Inventário de 35 nomes; 32 requeridas; três explicitamente excluídas | **Diferença intencional documentada** | Validar ownership/defaults em PG vazio; não criar as três excluídas automaticamente. |
| RLS e policies | 49 tabelas com RLS habilitado, 48 com FORCE; 188 policies no snapshot 01C4B, todas dentro da baseline | **Diferença intencional documentada**/fechada estaticamente | `propriedade_imovel` habilitada sem FORCE é exceção documentada. Prova de isolamento por tenant é obrigatória no PostgreSQL real. |
| Functions e triggers | Revisão baseline emite três funções e três triggers; 01D5 considera esses objetos parte do DDL | **Diferença intencional documentada**/fechada quanto à emissão; runtime pendente | O texto antigo que diz “não emitidos” está obsoleto. Validação de compilação, semântica e execução exige PG. |
| `UNIQUE_CONTRACT`, `CHECK_CONTRACT`, `INDEX_CONTRACT` vazios | Presentes no contrato | **Funcional e bloqueante** para os dois primeiros; **pendência não bloqueante** de paridade/performance para o terceiro | Não confundir geração ORM com auditoria de equivalência física. |
| SQL offline: `alembic_version` sem schema | `env.py` offline sem `version_table_schema`; SQL observado cria tabela sem qualificação antes do schema `farms` | **Estrutural e bloqueante** para usar o SQL offline como plano executável de clean install | Corrigir/testar geração antes de aprovar o artefato. Não executar este SQL. |

### Leitura do status

O contrato mistura pendências atuais com texto histórico que deveria ter sido encerrado. Isso torna o motivo do NO-GO pouco confiável, mas **não autoriza removê-lo**: há pendências funcionais e falhas de comprovação independentes. A correção segura é revisar o contrato com proveniência/versionamento e prova PostgreSQL, sem zerar contadores para liberar o fluxo.

## 3. Grafo Alembic validado

`alembic heads --verbose` identifica `20261022_agro_admin_01b1` como único head e `20260926_material_requisition_01g` como pai. `alembic show baseline_deepfarms_v1` confirma que a baseline é uma raiz independente (`down_revision = None`, branch label `deepfarms_baseline`).

O caminho se une em:

```text
baseline_deepfarms_v1 ───────────────────┐
                                         ├─ 20260915_merge_documentos_fiscais → … → 20261022_agro_admin_01b1
001_notas_fiscais → … → 20260914_documentos_fiscais ─┘
```

`20260914_documentos_fiscais` adiciona `gestao` e `xml_original` a `fin_notas_fiscais`; seu pai é `20260913_repair_estoque_movimentos_origem`. A revisão merge não executa DDL/DML próprio. Logo, a baseline está integrada no grafo, mas não é por si só a única linhagem ancestral do head.

Foi inspecionado `alembic history --verbose` e foram consultados os alvos offline baseline-only e baseline→head com URL sintética. O primeiro gerou SQL estático, porém com o problema de schema da tabela de versão descrito acima. O segundo falhou na geração offline ao alcançar revisão histórica que usa `sa.inspect(bind)`. Isso **não** demonstra falha online nem autoriza ignorar a revisão. Não foi executado `upgrade heads`, não foi testado `stamp` e não se recomenda nenhum dos dois.

## 4. Estratégias de banco novo

| Estratégia | Avaliação |
|---|---|
| **A. Baseline completa e atualizada para clean install** | É a direção arquitetural preferível: baseline reproduz o contrato atual de ORM e objetos não ORM; instalações novas partem de uma definição canônica atual e migrations futuras são incrementais. Hoje ainda não está provada a equivalência da linhagem irmã histórica, nem o SQL offline/online de `alembic_version`, constraints funcionais e RLS em PG real. **Selecionada como destino arquitetural, não liberada para execução.** |
| **B. Baseline seguida por migrations incrementais existentes** | Não é segura sem ponte verificada. O grafo exige a linhagem `20260914_documentos_fiscais` além da baseline. Aplicar essa revisão diretamente pode duplicar objetos já materializados pela baseline; não aplicá-la pode deixar objetos ausentes. Revisões anteriores podem conter DDL/DML dependente do schema físico antigo. Uma ponte/stamp só seria aceitável depois de comparar todos os efeitos por objeto. **Não selecionada.** |
| **C. Gerador alternativo/manual de schema** | Poderia evitar parte da história, mas duplicaria o contrato Alembic e ampliaria risco de drift em ENUM, sequence, RLS, policy, FK, trigger e defaults. `MetaData.create_all` não inclui o contrato completo. **Não selecionada.** |

A decisão única é **A como arquitetura-alvo**, com gate NO-GO até que haja prova física e uma resolução explícita da linhagem paralela. Não se escolheu alvo Alembic operacional (`revision`) nesta fase.

## 5. Correções realizadas e arquivos

**Nenhum arquivo de implementação foi alterado.** Não foi tecnicamente seguro corrigir `env.py`, `baseline_contract.py` ou revisões históricas sem primeiro fixar a semântica do version table e resolver a linhagem. Isso preserva migrations históricas e evita que uma edição aparentemente cosmética libere um caminho incompleto.

Este relatório é o único arquivo criado nesta fase:

- `docs/implementation/reports/AGRO-ADMIN-01H2C1-REGULARIZACAO-BASELINE-POSTGRESQL.md`

## 6. Validações e evidências

- Inspeção do grafo/head e código das revisões merge e `20260914`.
- Geração/inspeção estática de SQL baseline-only já produzida no escopo de auditoria; sem conexão ao banco.
- Geração offline até o head tentou alcançar revisões históricas e parou em `sa.inspect(bind)` sobre conexão mock do modo offline; interpretado exclusivamente como limitação da geração offline.
- Relatório 01D5 documenta 1.029 índices ORM sem duplicatas, 892 FKs, ausência de alvos inválidos e correção de duplicação de índice.
- Relatórios 01C4A/01C4B/01C4C e 01D4/01D5 usados para separar o que foi fechado estaticamente do que ainda exige runtime.
- Não se executou teste conectado, migration, `stamp`, `upgrade`, serviço, Docker ou chamada externa.

## 7. Pendências para PostgreSQL real

Em instância PostgreSQL descartável e dedicada, fora dos ambientes comerciais:

1. Corrigir e regenerar SQL offline para que criação e atualização de `alembic_version` usem explicitamente o schema acordado; comparar seu resultado com a execução online.
2. Aplicar baseline em banco genuinamente vazio somente após autorização específica, inspecionar catálogo inteiro e comparar com contrato atualizado.
3. Testar Alembic online no caminho de banco vazio até head e demonstrar como a linhagem `20260914` é satisfeita sem duplicação nem omissão. Revisar DDL/DML de todas as revisions da outra linhagem antes de qualquer bridge/stamp.
4. Comparar UNIQUE/CHECK por tabela, nome e semântica, atualizando contrato com decisões e referência alinhada à versão atual.
5. Verificar schema `farms`, 344 tabelas ORM, 34 ENUMs/146 valores, sequences requeridas e ownership, FKs (892), índices (1.029), defaults, functions/triggers e colunas esperadas pelo Backoffice, Agro e autenticação.
6. Testar RLS habilitada/forçada e as 188 policies com dois tenants, incluindo `USING`, `WITH CHECK` e a exceção `propriedade_imovel`.
7. Rodar smoke de escrita/leitura real com papéis da aplicação e provar que objetos/efeitos do baseline são utilizáveis, não apenas criáveis.

SQLite e mocks não satisfazem esses critérios.

## 8. Riscos de compatibilidade

- Declarar a baseline como equivalente à produção com base apenas em compilação de metadata pode omitir restrições funcionais ou efeitos históricos.
- Executar toda a linhagem histórica após criar baseline pode duplicar colunas/objetos; pular ou marcar a linhagem como aplicada pode omitir transformações/DML.
- `alembic_version` no schema inesperado pode produzir banco cuja versão não é reconhecida pelo processo subsequente.
- Diferenças históricas de índices podem afetar desempenho; devem ser analisadas por workload, sem transplantar automaticamente diferenças de catálogo.
- RLS, funções e triggers podem compilar e ainda ter comportamento de tenant/concorrência incorreto; validação catalog-only não prova segurança.
- Os números de divergência da referência de 2026-09-08 estão desatualizados frente ao head atual; não devem ser usados como contagem exata atual sem nova comparação versionada.

## 9. Integração futura com `agro_labctl.py`

O controlador existente deve continuar bloqueando `migrate`. Quando houver aprovação futura, o subcomando deverá receber um **target explícito e revisado**, nunca assumir `heads` nem calcular um alvo variável. O manifesto de autorização deve registrar, no mínimo:

```json
{
  "plan_id": "AGRO-ADMIN-01H2C1-PG-PROOF",
  "baseline_revision": "baseline_deepfarms_v1",
  "target_revision": "<revisão aprovada após prova>",
  "graph_digest": "<digest revisado>",
  "database_identity": "<identidade do banco descartável verificada>",
  "approval_reference": "<autorização explícita>"
}
```

O controlador deve recusar ausência de target, divergência de digest, URL fora do banco PostgreSQL dedicado e qualquer target sem allowlist aprovada. **Não preencher valores fictícios, não liberar o subcomando e não adicionar um comando automático nesta fase.**

## 10. Critérios de liberação e veredicto

**GO para migration** somente após: (a) resolução revisada do version table offline/online; (b) parecer de grafo provando caminho limpo e efeitos de ambas as linhagens sem duplicação/perda; (c) decisão por objeto de UNIQUE/CHECK; (d) PostgreSQL vazio dedicado com catálogo/RLS/runtime aprovados; (e) target explícito e digestado, aprovado para o controlador; (f) revisão de segurança atestando que a conexão é exclusivamente o banco de laboratório.

**Veredicto desta fase: NO-GO.** A baseline continua sendo o destino arquitetural preferido para clean install, porém não há revisão operacional segura autorizada. `agro_labctl.py migrate` deve permanecer bloqueado. Nenhum banco foi criado ou alterado; aguardar autorização e disponibilidade de PostgreSQL dedicado para a prova seguinte.
