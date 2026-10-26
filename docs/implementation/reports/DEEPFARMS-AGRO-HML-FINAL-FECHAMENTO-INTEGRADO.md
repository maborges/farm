# DEEPFARMS Agro — Fechamento Integrado da Homologação

**Data:** 2026-10-25  
**Veredicto atual:** **GO COM RESSALVAS para o artefato estático de clean install; NO-GO para DDL real e homologação integrada.**  
**Escopo concluído:** implementação versionada de clean install, seeds e validação estática. Nenhum serviço foi iniciado e nenhum DDL foi executado. O adendo final detalha esta atualização.

## 1. Resumo executivo

As evidências anteriores comprovam que a infraestrutura isolada do laboratório foi preparada, que a baseline atual corrigida foi aplicada em PostgreSQL descartável D3D e que, naquele escopo, catálogo, sequences, probes ORM, constraints e RLS foram validados. A identidade exclusiva D3F e os gates `identity` e `migration-identity` também foram aprovados anteriormente. Esses resultados não comprovam, por si, que a baseline é um caminho Alembic seguro até o head atual nem autorizam DDL ou inicialização de serviços nesta etapa.

O banco D3F continua sem instalação da aplicação. O arquivo privado `migration-approval.json` não existe. Portanto, os gates prévios de execução definidos pelo próprio pedido não estão completos. Não foram executados migrations, DDL, `stamp`, FastAPI, Next.js, PWA ou testes E2E. D3B e D3D permanecem evidências preservadas.

## 2. Estratégia Alembic

### Grafo observado

- A revisão `baseline_deepfarms_v1` é uma raiz independente que descreve o schema derivado da metadata ORM atual.
- A revisão `20260915_merge_documentos_fiscais` une a baseline e a linhagem histórica `20260914_documentos_fiscais`.
- O head do checkout é `20261022_agro_admin_01b1`; alcançar esse head pelo grafo conectado à baseline também alcança a linhagem histórica, com centenas de revisões ancestrais (408 na perna histórica registrada em C2; 416 revisões na ancestralidade total reportada).
- A revisão `20260915` é um merge, não uma prova de equivalência ou uma instalação limpa independente.
- Há revisões históricas com DDL redundante ou incompatível com o schema já criado pela baseline, operações condicionais/destrutivas e efeitos de dados. A análise estática desta etapa identificou DML direto em 53 revisões alcançáveis; essa contagem ainda exige classificação por efeito e não significa que todas sejam dispensáveis.
- A revisão do head `20261022_agro_admin_01b1` altera a nulabilidade de `sessoes_ativas.tenant_id` e cria `usuario_byok_credenciais`. A metadata ORM atual observada contém esses efeitos, mas essa equivalência pontual não resolve os efeitos históricos não representados no ORM.

### Opções avaliadas

| Opção | Avaliação |
|---|---|
| Baseline e depois reproduzir toda a linhagem até o head | **Rejeitada.** Reexecutaria operações históricas sobre objetos já existentes, com risco de duplicidade, falhas e operações destrutivas. A presença do merge não elimina esse risco. |
| Instalação limpa a partir de snapshot do schema atual, em script location/linhagem de instalação separada, mantendo a linhagem existente para upgrades | **Estratégia-alvo selecionada, ainda não liberada.** Evita replay de DDL histórico e preserva o caminho de upgrades. Antes de implementá-la é obrigatório classificar e incorporar explicitamente seeds/dados globais ainda necessários e demonstrar compatibilidade com o contrato e com upgrades existentes. |
| `stamp`, ponte artificial, `upgrade heads` ou criação manual para satisfazer o grafo | **Rejeitada.** Não prova equivalência estrutural e pode marcar como aplicada uma revisão sem executar seus efeitos. |

#### Recontagem dos efeitos DML no checkout atual

Uma nova varredura AST do grafo efetivamente alcançável a partir de `20261022_agro_admin_01b1` encontrou 416 revisões e 58 revisões com chamadas diretas `INSERT`/`UPDATE`/`DELETE` em `upgrade()`. A contagem anterior de 53 não foi reconciliada: a diferença vem de critérios de extração/escopo ainda não documentados. A varredura foi restrita ao grafo carregado pelo Alembic, não a todos os arquivos órfãos; textos SQL de funções/triggers não foram contados como DML de upgrade.

A fonte já permite separar classes com segurança parcial: `step1_migrate_talhoes_to_areas_rurais`, `step15_production_units`, `step17_operacoes_execucoes`, `step19_cost_allocations`, `20260722b/h`, `20260723d`, `20260724c`, `20260725c`, `20260722e`, `20260527_field_core03` e `grupo_usuario_mandatory_grupo` consultam ou copiam linhas preexistentes e são backfills de legado; `265b28773962` preserva colunas históricas em tabela de backup e as remove, sendo uma transformação histórica condicional; updates de normalização/default em planos, cadernos, integrações, compras, clima, carbono e configuração de IA alteram linhas que existam e precisam ser comparados à metadata/defaults atuais.

Há seeds/catálogos globais identificáveis na fonte, incluindo unidades e conversões, tipos de serviço, categorias do plano de contas, fases de operação, tipos de relacionamento e defaults zoossanitários. A lista ainda não está fechada: parte dos inserts é mista (seed global mais backfill), parte depende de catálogo/linhas anteriores, e o estado final esperado não está definido por um contrato canônico único. `20260731_iso80000` também transforma unidades criadas por seeds anteriores. Não foi provado que copiar todos esses inserts seja idempotente, completo, tenant-safe ou equivalente às configurações atuais.

**Impedimento técnico demonstrado:** o alvo de 53 revisões não corresponde à contagem reproduzível no grafo do checkout (58); além disso, a classificação de seeds é incompleta e inclui dados com dependências em tabelas/catálogos precedentes. Gerar uma snapshot marcada como `20261022_agro_admin_01b1` sem fechar essa lista registraria um schema como head sem provar os efeitos de dados esperados. Por isso não foi criada nem habilitada uma nova linhagem Alembic. Não se alterou nem reescreveu migration histórica.

Inventário AST atual por classe de conteúdo (revisões listadas uma única vez):

| Classe | Revisões | Decisão para clean install |
|---|---|---|
| Contém seed/catálogo global candidato (algumas também fazem backfill/condicionamento) | `20260824_pecuaria_species_defaults`, `20260815_logistica_reversa_embalagens`, `20260815_receituario_agronomico`, `20260731_uom_periodo`, `20260731_uom_tempo2`, `20260731_uom_tempo`, `20260725d_tipo_servico_catalogo_global`, `20260723f_categoria_plano`, `20260724c_colab_pessoa`, `20260722e_fornecedor_sem_dup`, `step14_uom`, `f0a1b2c3d4e5`, `conversao_unidade_v1` | Extrair os dados finais para contrato idempotente e provar dependências e necessidade. Não executar os upgrades históricos. `20260731_uom_iso80000` deve ser incorporada ao valor final do seed, não reproduzida como update legado. |
| Migração/backfill/normalização dependente de linhas anteriores, ou operação legada condicional/destrutiva | `20260827_sane_passaporte_uuid_vazios`, `20260826_carbono_unidade_produtiva`, `20260820_clima_idempotency`, `20260818_clima_escopo_unidade`, `20260731_uom_iso80000`, `20260725c_backfill_cost_allocations`, `20260725a_orc_snapshot`, `20260723d_backfill_ped`, `20260723c_pedido_adto_zero`, `20260722h_compras_multi_item`, `20260722f_cotacao_fornecedor`, `20260722b_pedido_fornecedor`, `20260718_sankhya_endpoints`, `265b28773962`, `20260701_integrations_domain_03a`, `09df6fa43b49`, `grupo_usuario_mandatory_grupo`, `rbac_granular_permissions`, `grupo_assinatura_refactor`, `20260527_field_core04`, `20260527_field_core03`, `20260527_field_core02`, `20260508_campo_pwa_05`, `stepGrowth25`, `stepGrowth21`, `stepGrowth19`, `step29_lancamento_categoria`, `step27_tenant_documento_nullable`, `add_is_default_to_plano`, `step19_cost_allocations`, `step17_operacoes_execucoes`, `step16_pu_fks`, `step15_pu`, `0808ec16ef17`, `step1_talhoes_consolidation`, `rh_colaborador_nome_cpf`, `add_planejada_pulv`, `4492badc2748`, `b1c2d3e4f5a6`, `4e0b633ffb18`, `produto_colhido_v1`, `commodity_refactor_v1`, `ed0688180f35`, `f1569f5e75f7`, `a1b2c3d4e5f6` | Não reproduzir na instalação vazia. Confirmar caso a caso se o resultado é absorvido pelo schema/default atual ou se há seed separado obrigatório. Operações como cópia de `credenciais`/`webhook_secret`, remoção de colunas, `DELETE` e migrações de entidades de negócio nunca devem ser executadas cegamente num snapshot. |

As duas listas somam as 58 revisões alcançáveis com DML identificadas pelo analisador. “Seed candidato” ainda não significa “seed aprovado”; “backfill/normalização” não autoriza assumir que toda regra de negócio final está no ORM.

## 3. Evidências estruturais já disponíveis

O relatório D3D registra aplicação real de `baseline_deepfarms_v1` em database descartável separado do D3B, com:

- 348 tabelas de aplicação e 4.767 colunas, reconciliadas com a metadata ORM observada;
- 33 sequences do contrato com nomes, defaults e ownership validados;
- 924 foreign keys, 76 UNIQUE, 76 CHECK e 34 ENUMs;
- 49 tabelas com RLS habilitado, 48 com FORCE, e 188 policies;
- 3 funções e 3 triggers;
- probes ORM/constraints e isolamento RLS entre dois tenants sintéticos aprovados no escopo testado, com fixtures revertidas.

Essa prova é válida para a baseline e o catálogo observados em D3D. Ela não demonstra instalação até o head, equivalência dos efeitos de todas as revisões históricas, presença de seeds obrigatórios nem compatibilidade do caminho de upgrade em bancos existentes. O `CONTRACT_STATUS` permanece `NO-GO` conforme as pendências documentadas em C2.

## 4. Implementação estática realizada

- Adicionado `apps/agro/playwright.lab.config.ts`, exclusivo do laboratório: exige PWA em `127.0.0.1:3005` e API interna em `127.0.0.1:8001`; inicia o Next dev somente quando o operador executar o Playwright; não reutiliza servidor preexistente; limpa variáveis com nomes de credenciais no ambiente do processo web e restringe a resolução de hosts Chromium a loopback.
- Adicionado script `test:e2e:lab` em `apps/agro/package.json`; o comando apenas roda se for invocado, não foi executado nesta fase.
- Substituído e renomeado `apps/agro/tests/e2e/mercado-precos-fixture.spec.ts`: fixture sintética interceptada em `/api/v1/public/mercado/precos`, incluindo teste de cache/offline. O payload declara que não é cotação real; nenhum provedor externo é chamado por esse spec.
- Corrigido o hook `useAgroConfig` para fazer o carregamento inicial após agendamento assíncrono e manter `refresh` explícito; isso remove erro do lint React encontrado durante a validação.
- O teste `services/api/tests/unit/core/test_alembic_offline_version_schema.py` usa ambiente de subprocesso isolado e URL PostgreSQL sintética fora do alvo do laboratório; continua gerando SQL offline e não abre conexão.

Na redação original deste relatório, o caminho Alembic não havia sido implementado devido ao contrato de seeds incompleto. Essa pendência foi tratada no adendo final: existe agora um script location independente, contrato de seeds e runner estático fail-closed. Migrations históricas, `baseline_contract.py`, roles, bancos e configurações comerciais continuam preservados.

O workspace continha numerosas alterações e arquivos não rastreados antes/durante esta tarefa, abrangendo outras frentes do produto. Foram preservados; não foram revertidos, limpos ou incorporados a este relatório.

## 5. Validações executadas

| Verificação | Resultado |
|---|---|
| Testes direcionados de contrato baseline, sequences, versão Alembic offline e guardrails do controlador | **59 passed** |
| Ruff nos módulos Python de guardrails e testes Alembic relacionados | **PASS** |
| Typecheck Python da API | **Não configurado no pacote.** Não há mypy/pyright declarado; Ruff foi a verificação estática Python executada. |
| Testes unitários da Agro PWA (Vitest) | **155 passed em 11 arquivos** |
| Typecheck de `apps/agro` | **PASS** |
| ESLint de `apps/agro` | **PASS** após correção em `useAgroConfig` |
| Typecheck de `apps/web` | **Não concluído.** Excedeu 90 s sem resultado e expirou. |
| Guardrails Backoffice (`test:sidebar`) | **4 checks passed** |
| Probe diagnóstico da API em SQLite temporário | **1 passed**; `DATABASE_URL`, `TEST_DATABASE_URL` e flags CI foram removidos do ambiente do processo. |
| Testes de cadastro gratuito + suíte Backoffice Agro 01F em SQLite | **Não concluídos.** Sem saída por mais de 30 s; interrompidos, sem resultado atribuível. |
| Testes Vitest do Backoffice | **Indisponíveis neste workspace:** `apps/web` não declara Vitest nem possui executável local; o comando exploratório falhou antes de iniciar testes. |
| Configuração Playwright do laboratório (`--list`) | **PASS; 42 cenários listados em 7 arquivos**, sem iniciar webServer. |
| Reconciliação do inventário AST DML com as listas do relatório | **PASS; 58 revisões, 58 IDs únicos, sem omissões ou extras** no grafo do head atual. |
| Build Next.js | **Não executado.** Os diretórios `.next` já existiam antes da execução; sobrescrevê-los poderia interferir em artefatos/processos preexistentes. |
| `git diff --check` global | Há falha preexistente registrada em `services/api/core/routers/backoffice_sessions.py:170` (linha em branco final); arquivo fora do escopo da correção estática desta tarefa. |
| Gates `identity` e `migration-identity` | **PASS previamente registrado em D3F**; não reexecutados nesta etapa. |
| Instalação limpa / catálogo no D3F | **Não executada.** Falta `migration-approval.json` e aprovação explícita para DDL. |
| Testes integrados ou E2E | **Não executados.** Serviços não iniciados e banco D3F sem schema aplicado. |

## 6. Homologação integrada: estado e bloqueios concretos

### Estado de serviços e dados

- PostgreSQL dedicado do laboratório: `127.0.0.1:5433`; Redis dedicado: `127.0.0.1:6380`, ambos reportados operacionais nas fases D2/D3F. Não foram iniciados, parados ou reconfigurados nesta etapa; sua disponibilidade atual não foi revalidada.
- D3B e D3D permanecem databases de evidência e não foram alterados nesta etapa.
- D3F (`agro_hml_dbdcc24872aa_d3f`) não recebeu migrations/DDL nesta etapa; a prova D3F reporta-o vazio de objetos da aplicação e sem revisão Alembic. Nenhuma conexão comercial/RDS foi feita.
- FastAPI, Backoffice e Agro PWA não foram iniciados.

### Bloqueios para integração

1. **Gate DDL incompleto:** não há `migration-approval.json` válido vinculado ao D3F; a autorização geral de fechamento não substitui o arquivo e os critérios de aprovação definidos para execução. O comando oficial de migration continua bloqueado.
2. **Clean install real ainda não foi executado:** o caminho separado está implementado conforme o adendo, mas depende de autorização privada vinculada ao D3F e de prova PostgreSQL real dessa nova linhagem. A baseline/head histórico continua sem ponte e sem replay.
3. **Contrato não aprovado:** `baseline_contract.py` ainda registra NO-GO em pendências históricas/funcionais. O teste real D3D não as fecha automaticamente.
4. **Backoffice E2E:** a aplicação web não possui specs Playwright de Backoffice identificados, e não há runner Vitest declarado no pacote. Os guardrails sidebar passam, mas não cobrem fluxos autenticados ou RBAC integrado.
5. **Specs E2E existentes:** o cenário de preços foi convertido para fixture. Os specs de clima/localidade e PTAX ainda contêm casos descritos como integração real; o bloqueio de resolução de hosts Chromium não substitui fixtures upstream do processo FastAPI. Esses casos devem ser revisados antes da execução; a suíte E2E não foi rodada.
6. **Escopo offline:** a Agro PWA tem service worker/cache da rota offline e testes de visualização/cálculo offline. Não foi encontrada fila de mutações com sincronização offline na PWA Agro (não há indicação de IndexedDB/outbox); a homologação não deve declarar sincronização de gravações offline como capacidade existente sem evidência/implementação.
7. **Validação de frontend incompleta:** o typecheck do Backoffice não terminou. Não há evidência de build ou E2E integrados nesta etapa.

### DDL pendente e autorização

Não há comando DDL seguro para submeter agora. A revisão `20261022_agro_admin_01b1` é head da linhagem conectada, cujo upgrade percorre histórico; o alvo de snapshot independente ainda não foi implementado. O controlador `agro_labctl.py migrate` também contém bloqueio explícito para esse caminho. Executar `--revision 20261022_agro_admin_01b1` nele não seria uma autorização válida e não deve ser tentado.

Quando houver revisão de clean install implementada e aprovada estaticamente, o alvo deverá identificar exatamente essa revisão no script location separado. Os efeitos previstos serão DDL do snapshot baseline, seeds aprovados pelo contrato e gravação transacional da revisão executada em `farms.alembic_version` (sem `stamp`). Os riscos atuais são omitir seeds, duplicar/copyar dados sensíveis de integrações, ou declarar o head sem equivalência estrutural/funcional. A autorização atual não deve ser solicitada até esses efeitos e hash de migration existirem.

## 7. Sequência mínima para retomar

1. Obter autorização explícita para a instalação limpa exata no D3F e criar, pelo operador autorizado, `migration-approval.json` privado e válido vinculado à revisão `deepfarms_clean_install_v1`; o comando e os efeitos estão no adendo.
2. Executar somente o runner clean install sob os gates; não usar `agro_labctl.py migrate`, `stamp`, `upgrade heads` ou a linhagem histórica.
3. Se a prova real concluir e o catálogo/RLS passarem, solicitar autorização específica para iniciar serviços do laboratório e então executar E2E preparado com fixtures.

## 8. Decisão

**NO-GO para homologação técnica integrada e instalação real nesta etapa.** A implementação estática do clean install foi concluída no adendo e os testes de contrato pertinentes passaram. Ainda faltam autorização formal de DDL no D3F, prova real da instalação separada e execução autorizada de serviços/E2E. O head histórico não é marcado como aplicado. Não houve acesso à infraestrutura comercial, alteração dos bancos de evidência, execução de migration ou inicialização de serviços.

Este relatório encerra o ciclo solicitado. Nenhuma etapa adicional foi iniciada automaticamente.

---

## Adendo — Clean install independente implementado (2026-10-25)

Este adendo atualiza as afirmações anteriores de que ainda não havia caminho executável de instalação limpa. O caminho está implementado e aprovado estaticamente. Ele **não** altera o veredicto de homologação integrada: DDL real no D3F continua pendente de aprovação privada e de execução controlada; serviços e E2E também não foram iniciados.

### Arquivos adicionados

- `services/api/clean_install/__init__.py`: identificador versionado da instalação.
- `services/api/clean_install/seed_contract.py`: contrato ordenado, determinístico e idempotente dos catálogos globais obrigatórios.
- `services/api/clean_install/manifest.py`: hashes fixados da baseline e do contrato de seeds para evitar alteração silenciosa do snapshot V1.
- `services/api/clean_install/catalog_validation.py`: validação pós-instalação somente leitura do catálogo PostgreSQL.
- `services/api/migrations/clean_install/alembic.ini`, `env.py` e `versions/20261025_clean_install_v1.py`: script location e raiz Alembic independentes.
- `services/api/migrations/clean_install/README.md`: regra de evolução da linhagem limpa e compatibilidade com upgrades históricos.
- `scripts/homologacao/agro_clean_install.py`: runner fail-closed, vinculado ao root/database D3F.
- `services/api/tests/unit/core/test_clean_install_contract.py`: testes do plano, seeds, hashes, grafo e guardrails locais.

Nenhuma migration histórica, baseline, banco, role ou configuração comercial foi modificada. `agro_labctl.py migrate` permanece bloqueado e não foi enfraquecido.

### Revisões DML e decisão dos catálogos

O inventário adotado é o já registrado acima: 58 revisões DML alcançáveis, das quais 13 candidatos a catálogos e 45 revisões restantes. As 45 permanecem classificadas na tabela de inventário existente como backfills dependentes de linhas anteriores, normalizações, transformações históricas condicionais/destrutivas ou operações legadas. Nenhuma delas é reproduzida pelo clean install. Isso inclui cópia de credenciais/webhooks, remoções de colunas, exclusões, backfills de pessoas/fornecedores, dados de integração e transformações de linhas comerciais.

| Candidato / origem | Chave natural e escopo | Decisão no clean install | Integridade e dependências |
|---|---|---|---|
| `step14_unidades_medida.py` + `20260731_seed_unidades_tempo`, `20260731_seed_unidades_tempo_extra`, `20260731_seed_unidades_periodo_dia`, `20260731_iso80000_codigos_tempo` | `unidades_medida.codigo`, global (`tenant_id IS NULL`) | **Seed obrigatório: 24 unidades.** Valores refletem o estado final ISO de códigos de tempo (`h`, `s`, `min`, `d`, `a`), não os códigos intermediários pré-normalização. | Confere chaves naturais, ID determinístico, dimensões, referências e fatores. Códigos globais duplicados com conteúdo divergente causam erro, sem update silencioso. |
| `add_conversao_unidades.py` / `conversao_unidade_v1` | Conversão por commodity e par de unidades | **Não semeado.** | O migration antigo depende de commodities de sistema e fatores agronômicos específicos; o clean install não cria catálogo de commodities/preços demonstrativos. A tabela ORM moderna `unidades_medida_conversoes` também fica sem linhas iniciais. |
| `20260725d_tipo_servico_catalogo_global.py` | Nome do serviço, global | **Opcional, excluído.** | São sugestões, não requisito de instalação. Algumas unidades históricas (`KM`, `SC`) não existem no conjunto canônico atual (`SC60`/`SC50`), portanto copiá-las criaria referências textuais inconsistentes. |
| `20260723f_categoria_produto_plano_contas.py` | Nome em raiz global; IDs fixos da fonte histórica preservados | **Seed obrigatório: 15 categorias globais.** | Valida unicidade natural e ID determinístico. Não executa o backfill de `cadastros_produtos` nem altera planos de contas existentes. |
| `f0a1b2c3d4e5_create_operacao_tipo_fase_lookup.py` | `tipo_operacao`, global | **Seed obrigatório: 9 fases/tipos.** | Fonte final é `DEFAULT_TIPO_FASES`/`DEFAULT_TIPO_DESCRICOES` do serviço atual, incluindo `OUTROS` e `PLANEJADA`; não reproduz o seed histórico desatualizado de oito entradas. |
| `seed_tipos_relacionamento.py`, `20260724c_colaborador_rh_papel_sobre_pessoa.py`, `20260722e_fornecedor_remove_colunas_redundantes.py`, `20260815_receituario_agronomico.py`, `20260815_logistica_reversa_embalagens.py` | `codigo`, global (`tenant_id IS NULL`) | **Seed obrigatório: 11 tipos globais**, incluindo `AGRONOMO` e `POSTO_RECEBIMENTO`. | Valida código natural, nome e flags de sistema. Só os registros globais são extraídos; backfills de pessoas, CPF e fornecedores não são executados. |
| `20260824_pecuaria_species_defaults.py` | Espécie + tipo de risco, global | **Opcional, excluído nesta versão.** | Os cinco padrões têm fontes científicas, mas são presets de domínio não necessários para criar o schema. Exigem decisão técnica veterinária própria; nenhum dado de demonstração é inserido. |

Os quatro catálogos aprovados contêm **59 linhas globais** (24 unidades, 15 categorias, 9 tipos/fases de operação e 11 tipos de relacionamento). A ordem é explícita. Os registros têm IDs estáveis; execução repetida reconhece registros iguais e recusa divergências. A execução Alembic envolve baseline, seeds, manifest e checks em uma transação PostgreSQL; qualquer falha reverte a instalação inteira.

### Instalação e versionamento

- Versão independente: `deepfarms_clean_install_v1`.
- Script location: `services/api/migrations/clean_install`.
- Raiz Alembic única: `deepfarms_clean_install_v1`, sem ancestralidade histórica.
- Tabela Alembic exclusiva: `farms.deepfarms_install_version`.
- Recibo do snapshot: `farms.deepfarms_install_manifest`, contendo versão, revisão `baseline_deepfarms_v1`, hash da baseline, versão/hash dos seeds e timestamp.
- A tabela histórica `farms.alembic_version` **não** é criada nem recebe o head histórico por `stamp`.
- A revisão chama a implementação existente da baseline por importação controlada; não duplica as centenas de definições ORM. Antes do DDL, verifica os hashes fixados da baseline e seeds.
- Um lock transacional advisory serializa tentativas concorrentes. O runner verifica identidade e alvo vazio; o ambiente Alembic repete a verificação de schema vazio sob o lock.
- Os checks finais validam 348 tabelas ORM, 33 sequences e ownership/defaults, FKs, UNIQUE/CHECK, índices ORM, 34 ENUMs e labels, RLS/FORCE e 188 policies, funções/triggers, manifest e versão própria. O contrato completo no banco continua sujeito à prova real; `CONTRACT_STATUS` segue NO-GO e não foi alterado.

Para evoluções futuras, bancos criados por esta instalação avançarão somente por novas revisões lineares no script location `migrations/clean_install/versions`, usando `deepfarms_install_version`. Instalações existentes continuam pela linhagem histórica atual. Cada alteração futura que precise atender ambos os grupos deve ter implementação compatível nos dois caminhos e teste de paridade estrutural/dados antes da release. Não há ponte automática, replay retroativo ou conversão de versão criada nesta entrega; essa política é deliberada para não marcar o head histórico sem equivalência comprovada.

### Validação estática executada

- **22 testes passaram**: contrato baseline, sequences, geração offline de schema da tabela histórica e novos testes de catálogo, IDs, ordem, escopo global, idempotência, rejeição de drift, grafo independente e hashes fixados. Os testes novos de seeds usam conexão em memória simulada; não equivalem a execução PostgreSQL.
- Ruff: **PASS** nos módulos e testes adicionados.
- `compileall`: **PASS**.
- `alembic history` do script location limpo: **PASS**, saída única `<base> -> deepfarms_clean_install_v1`; nenhum serviço ou banco foi acessado.
- `git diff --check` dos caminhos alterados: **PASS**.
- PostgreSQL real, probes ORM/RLS pós-clean-install, instalação no D3F e E2E: **pendentes**. Nenhum DDL, migration, serviço ou conexão foi iniciado nesta tarefa.

### Autorização operacional pendente

Database alvo fixado: `agro_hml_dbdcc24872aa_d3f`, em `127.0.0.1:5433`, root `/tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3f`. O runner rejeita outro root/database, exige `identity = PASS`, `migration-identity = PASS`, aprovação privada de revisão exata, confirmação do banco vazio e configuração sintética exclusiva. A aprovação não foi criada.

Comando exato a submeter **somente após autorização explícita e criação pelo operador de `config/migration-approval.json` válido, modo 0600, vinculado ao ID/database/revisão acima**:

```bash
services/api/.venv/bin/python scripts/homologacao/agro_clean_install.py --root /tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3f
```

Efeitos esperados: criação dos objetos da baseline atual (348 tabelas ORM, 33 sequences, constraints, índices, enums, RLS/policies, funções/triggers), 59 registros globais dos quatro catálogos, tabela `farms.deepfarms_install_version` com a revisão limpa e recibo `farms.deepfarms_install_manifest`. Não haverá seed de usuário, tenant, preço, commodity, integração, provedor, credencial ou dado demonstrativo. Se target, role, hashes, catálogos, políticas ou contrato diferirem, a transação falha; não há reparo automático.

Hashes SHA-256 dos artefatos no checkout desta entrega:

| Artefato | SHA-256 |
|---|---|
| Runner | `9e2266a5fb564185690c4da4c17713b5ed6e4292e9b0649896feb949b80fdceb` |
| Revisão limpa | `48c5d1593df585b78edb493c9f5fcd13f1cd388ed642f03856b78aa74d04ed7a` |
| Ambiente Alembic | `c434751d78b2973e1fec9366bf7f82f7a576e761f5230c821b43bf3c4743bb67` |
| Configuração Alembic | `5b6570fa1f6b493ce00731e8c4f31a966b3b45bcaf76bc9221965382b4d4f96f` |
| Contrato de seeds | `1e6a717dc70effdc9cbc65407bbf4126ed2f59b36f2a6b0c7f8d37a61507b4fe` |
| Validador de catálogo | `02a4c53e27c2ef49a36b2190d22de020534bc8ef4d3bcd8690ccf826d8d5315f` |
| Manifest/hash pins | `b2ef28e90810d986f0fd6fd243da43d9c08be93ea4c612c4792eb3f114d4deaf` |
| Baseline reutilizada | `b32da6be0f5f089c9d75fc2c0da4784e8dccaeb6303be5c03dbc6156c8275fbc` |

### Veredicto atualizado

**GO COM RESSALVAS para a implementação estática do clean install; NO-GO para instalação real e homologação integrada até autorização e prova PostgreSQL no D3F.** Os bloqueios concretos restantes são: aprovação privada explícita ainda ausente; validação real do snapshot/seeds/manifest/catálogo/RLS em PostgreSQL limpo; `CONTRACT_STATUS` histórico segue NO-GO para pendências de paridade; e os serviços/E2E ainda não foram autorizados ou executados. D3B e D3D não foram tocados. Não foram criados `migration-approval.json`, novos databases/roles ou segredos.

---

## Adendo — Tentativa autorizada de clean install D3F interrompida no gate (2026-10-25)

O usuário autorizou a instalação exata `deepfarms_clean_install_v1` no database D3F, com execução dos gates oficiais, aprovação privada `0600`, validação PostgreSQL e probes sintéticos. A autorização foi tratada como escopo para esse alvo, sem ampliar para D3B/D3D, bancos comerciais, histórico Alembic ou serviços de aplicação.

### Preflight e resultado

- Inspecionado o contrato: `migration-approval.json` deve conter exatamente `instance_id`, `database`, `revision`, `authorization_id`; o guard exige modo `0600` e revisão exata. O runner está fixado ao root D3F e ao database `agro_hml_dbdcc24872aa_d3f`.
- A primeira tentativa do gate `identity` parou antes de conectar porque `redis-cli` não estava no `PATH`. O binário já extraído foi localizado na área de pacotes rootless previamente documentada. O gate oficial foi repetido, sem modificar seu código e sem instalar pacotes, usando apenas o diretório existente no `PATH`.
- Na repetição, o `identity` confirmou a identidade PostgreSQL prevista e chegou à checagem Redis; falhou com `Redis não comprovou o marcador de identidade previamente provisionado`. Portanto o gate completo `identity` é **NO-GO**. O estado observado não prova se o marcador Redis está ausente, divergente ou se a instância/ACL não corresponde à configuração do laboratório; a mensagem do gate não expõe o valor observado.
- `migration-identity` não foi executado: o comando foi encadeado após `identity` e parou na falha, conforme a regra fail-closed. O runner e qualquer DDL não foram chamados.

### Preservação e veredicto

- **Não criado** `config/migration-approval.json`; nenhuma autorização foi fabricada antes dos gates.
- **Não executados** clean install, DDL, migrations, `stamp`, probes ORM/RLS, nem serviços FastAPI/Next.js/PWA.
- Nenhuma alteração em D3B, D3D, bancos comerciais ou RDS. Nenhuma credencial foi impressa.
- Os hashes não foram reavaliados nesta tentativa; como o gate de identidade falhou, o preflight não avançou para aprovação nem execução.

**Veredicto desta tentativa: NO-GO.** Bloqueio objetivo: a identidade Redis não foi comprovada pelo gate oficial. A autorização de clean install não altera nem permite contornar esse requisito. Nenhuma correção ou nova tentativa foi iniciada.

---

## Adendo — Recuperação Redis e tentativa D3F (2026-10-25)

### Diagnóstico e gates

- Redis do laboratório foi identificado como o processo Redis 6.0.16 já ativo em `127.0.0.1:6380`, com configuração/ACL e diretório exclusivos sob a raiz autorizada. O binário `redis-cli` rootless precisava tanto do diretório `bin` no `PATH` quanto das bibliotecas do pacote em `LD_LIBRARY_PATH`; somente ajustar o `PATH` não bastava.
- Com os caminhos rootless corretos, a consulta autenticada read-only confirmou que o marcador de identidade existe e corresponde ao ID do laboratório. Não foi recriado marcador, reiniciado processo, alterada ACL nem limpa a base Redis.
- Gates oficiais: `identity = PASS` (PostgreSQL e Redis) e `migration-identity = PASS` (role migradora e limites de database).
- O preflight extra corrigiu um falso negativo no meu assert: a role real do D3F é o nome exclusivo completo derivado pelo provisionador, não a abreviação presumida pelo assert. A conexão reportou database `agro_hml_dbdcc24872aa_d3f`, role migradora do D3F, endereço `127.0.0.1/32` e porta `5433`.
- Os oito hashes registrados para runner, revisão limpa, env/ini Alembic, contrato de seeds, validador, manifest pins e baseline passaram antes da instalação. O contrato privado de autorização exigido pelo código foi criado sob `config/migration-approval.json`, modo `0600`, exclusivamente para a instância do laboratório, database D3F e revisão `deepfarms_clean_install_v1`; sua validação permaneceu PASS no encerramento.

### Execução interrompida antes de DDL

- A invocação autorizada do runner passou novamente pelos dois gates oficiais, mas terminou antes de criar engine/conexão PostgreSQL. Erro concreto: `ModuleNotFoundError: No module named 'clean_install'`, causado por o runner não incluir `services/api` no caminho de importação quando chamado da raiz do repositório.
- A consulta read-only posterior confirmou que o schema `farms` não existe no D3F e contém zero objetos. Nenhuma tabela, seed, revisão de instalação ou DDL foi aplicado. Os databases D3B e D3D não foram consultados nem modificados nesta tentativa.
- Corrigido o runner para acrescentar `services/api` ao `sys.path` antes da importação do validador; foi acrescentado teste dessa configuração. Testes unitários do contrato clean install: **8 passaram**. Ruff e `git diff --check`: **PASS**.
- Hash atual do runner corrigido: `ffa9de7c948b4b89867c2eb5cb55143303965f99c11906599f7bd61ce50a2bc9`. Os hashes fixados da baseline e do contrato de seeds continuam válidos. A instalação não foi repetida: a autorização operacional anterior limitava a execução a uma invocação, que já ocorreu e falhou antes da conexão. Uma nova execução precisa de autorização específica para repetir o runner corrigido.

### Estado final e veredicto

- Redis e PostgreSQL do laboratório continuam em seus processos existentes; não foram iniciados ou encerrados serviços nesta etapa.
- D3F permanece vazio de objetos DeepFarms. A aprovação privada existe com modo `0600`, mas não houve consumo automático do arquivo nem execução DDL.
- API, Backoffice, PWA, probes ORM/RLS pós-instalação e E2E continuam pendentes.

**Veredicto: NO-GO para clean install nesta execução; GO COM RESSALVAS para a recuperação do gate Redis e correção estática do runner.** Bloqueio objetivo restante: uma nova execução controlada do runner corrigido requer autorização explícita, após validar novamente os gates e hashes atuais. Nenhum caminho histórico Alembic foi executado.

---

## Adendo — Segunda invocação autorizada do clean install D3F (2026-10-25)

### Preflight

- `identity = PASS`: PostgreSQL e Redis responderam, identificadores conferidos.
- `migration-identity = PASS`: role migradora autenticada e escopo de database confirmado.
- Banco D3F verificado vazio: schema `farms` ausente, zero objetos de aplicação.
- Runner corrigido confirmou o SHA-256 esperado `ffa9de7c948b4b89867c2eb5cb55143303965f99c11906599f7bd61ce50a2bc9`; hashes da revisão limpa, env/ini, validador, manifest pins, baseline e contrato de seeds passaram.
- `migration-approval.json` permaneceu válido, modo `0600`, vinculado à instância do laboratório, D3F e `deepfarms_clean_install_v1`.

### Resultado da única invocação

A invocação passou novamente pelos gates oficiais e então parou no preflight de identidade do próprio runner com `NO-GO: Identidade PostgreSQL efetiva diverge do D3F loopback autorizado.` O PostgreSQL retorna `inet_server_addr()::text` como `127.0.0.1/32`, mas o runner compara essa string com `127.0.0.1` literal. O endereço efetivo, verificado separadamente com `host(inet_server_addr())`, é o loopback autorizado.

A divergência ocorreu antes de qualquer chamada Alembic ou DDL. A exceção saiu do bloco transacional e a transação foi revertida. Verificação read-only posterior confirmou novamente que o schema `farms` não existe e há zero objetos de aplicação em D3F. Não foram criados tabelas, seeds, sequences ou manifesto; D3B, D3D, bancos comerciais e RDS não foram acessados.

### Correção necessária e encerramento

A comparação interna deve validar o endereço IP sem a máscara CIDR, por exemplo usando `host(inet_server_addr())`, mantendo iguais as verificações do database e da porta. Esta execução foi limitada a uma única invocação e não houve repetição. O runner e seu hash esperado permanecem sem alteração depois do erro; nenhuma nova autorização foi criada.

Como a instalação não concluiu, validações de catálogo pós-instalação, contagem dos 59 seeds/33 sequences, probes ORM e isolamento multi-tenant não foram executadas. API, Backoffice, PWA e E2E continuam não iniciados.

**Veredicto: NO-GO para clean install D3F.** Evidências reais confirmam gates PASS e banco ainda vazio; o bloqueio é a comparação textual CIDR no preflight interno do runner. É necessária correção do código e nova autorização para uma próxima invocação. Nenhuma migration histórica, `stamp` ou DDL foi executado.

---

## Adendo — Correção definitiva e cobertura dos preflights (2026-10-25)

### Implementação

- Corrigido `scripts/homologacao/agro_clean_install.py`: a identidade efetiva consulta `host(inet_server_addr())`, e o validador aceita somente os valores exatos `127.0.0.1` ou `127.0.0.1/32`, além de exigir database D3F, role esperada e porta 5433. Não há comparação por prefixo.
- O preflight agora recusa schema `farms` preexistente, qualquer relação/sequência de aplicação em schema não sistêmico e tabelas de versão já existentes. A verificação de hashes fixados foi antecipada para antes da conexão e repetida antes de chamar Alembic.
- Acrescentados testes de identidade positiva/negativa, database/schema ocupado, divergência de hash, falha de import, falha de autenticação Redis e falha em cada gate oficial. Os testes de aprovação existentes foram ampliados para autorização ausente, modo incorreto, database/instância/revisão incorretos e identificador inválido.
- Baseline, migrations históricas e contrato de seeds não foram alterados.

### Validação estática

- Testes direcionados: **76 passaram** — `test_agro_clean_install_preflight.py`, `test_clean_install_contract.py` e `test_agro_labctl.py`.
- Ruff: **PASS** nos quatro arquivos Python da alteração.
- `compileall`: **PASS** nos mesmos arquivos.
- Grafo clean-install lido sem conexão: `<base> -> deepfarms_clean_install_v1`, raiz e head únicos.
- `git diff --check`: **PASS**.
- Nenhuma migration ou DDL foi executado. Os gates oficiais não foram reexecutados nesta fase; os testes para falha deles são unitários com respostas controladas.

### Estado operacional e próxima autorização

- A consulta PostgreSQL somente leitura confirmou que o alvo continua sendo `agro_hml_dbdcc24872aa_d3f` em loopback:5433, schema `farms` ausente e zero relações de aplicação.
- A aprovação privada existente foi validada sem exibir conteúdo: modo `0600`, vinculada ao D3F e `deepfarms_clean_install_v1`. O hash atual do runner (`scripts/homologacao/agro_clean_install.py`) é `8990b5d1fd10d8175fdd6bd2d354aef23dbdd7ee50b728eb312d8b6ae6677985`. Os pins da baseline e seeds permanecem válidos.
- Comando oficial, para execução após autorização explícita e novos gates operacionais:

```bash
services/api/.venv/bin/python scripts/homologacao/agro_clean_install.py --root /tmp/deepfarms-agro-hml-dbdcc24872aa2992-d3f
```

- Antes dessa execução, repetir `identity` e `migration-identity`, verificar o hash acima, validar novamente aprovação `0600`/target/revisão e confirmar que D3F permanece vazio. Não são necessários novos bancos, roles, permissões ou alterações de infraestrutura.

**Veredicto desta fase: GO COM RESSALVAS para os preflights estáticos e testes; instalação PostgreSQL real permanece pendente de nova autorização.** API, Backoffice, PWA e E2E não foram iniciados.
