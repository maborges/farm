# DEEPFARMS-RLS-HOSTINGER-01C — Consolidação das Evidências Reais e Preparação para Correção

**Data da consolidação:** 2026-10-31
**Escopo:** documentação e análise estática somente. Nenhum acesso remoto do Codex à VPS ou ao banco foi realizado nesta atualização; nenhuma consulta, migration, alteração de role, grant, policy, dado, Compose, container ou código funcional foi executada.

## 1. Resumo executivo

O operador confirmou por comandos Docker e consultas PostgreSQL executados na VPS Hostinger que o projeto `farm` está em execução com nove containers, PostgreSQL 16 saudável e banco/schema `farms`. A role `deepfarms` tem `rolsuper=true`, `rolbypassrls=true` e `rolcanlogin=true`; API e os três workers configuram `DATABASE_URL` para essa identidade e banco. Portanto, **o bypass estrutural de RLS é risco P0 confirmado para os quatro serviços**: as políticas de linha não limitam essas conexões. Isso não prova que ocorreu acesso indevido, mas impede tratar o RLS como barreira efetiva enquanto essa identidade for usada.

A fotografia física reportada contém 350 tabelas, 49 com RLS, 48 com FORCE RLS, 301 sem RLS e 188 policies. A reconciliação nominal anterior permanece fechada: 348 candidatas ORM do Anexo A do 01B estão presentes no PostgreSQL; somente `deepfarms_install_manifest` e `deepfarms_install_version` são adicionais (estruturas técnicas); não há nome ORM ausente fisicamente. O novo extrato de 1.883 linhas fecha também o estado de RLS, owners/ACLs, roles, sequences, funções, views, defaults, colunas `tenant_id`, FKs e policies. Os estados de RLS (49/48) e as 188 policies coincidem com o contrato/snapshot local, mas isso não torna RLS efetivo para a role atual superuser/BYPASSRLS.

O banco contém 23 produtos e todos os 23 têm `tenant_id IS NULL`; o código atual descreve catálogo global legível pelos Tenants e mutável somente pela administração da plataforma, com cadastro de produtos particulares pelo Tenant. A agregação não prova que as regras de escrita funcionam.

**Decisão atual: GO para iniciar somente o planejamento da correção; NO-GO para implementação/cutover 01D ou liberação multi-tenant.** O inventário físico e a comparação nominal estão fechados. O planejamento deve priorizar a separação do papel superuser, matriz de privilégios, FKs sem escopo composto e autorização de registros globais; validação comportamental e conexões reais da aplicação continuam pendentes.

## 2. Evidências reais coletadas

A evidência física abaixo foi **fornecida pelo operador como resultado de comandos executados na VPS Hostinger**. Não foi obtida por acesso remoto direto do Codex. A abrangência dos comandos não equivale à inspeção integral do Compose ou de todos os parâmetros dos processos.

### 2.1. Ambiente e identidade

| Item | Resultado informado | Limite da evidência |
|---|---|---|
| Projeto / Compose | Projeto `farm`; Compose efetivo informado: `/opt/deepfarms/farm/docker-compose.hostinger.yml` | O arquivo integral e todos os parâmetros resolvidos não foram examinados. |
| Containers | `farm-web-1`, `farm-api-1`, `farm-outbox-worker-1`, `farm-automations-worker-1`, `farm-background-worker-1`, `farm-agro-1`, `farm-campo-1`, `farm-postgres-1`, `farm-redis-1` | Nove containers em execução no instante da coleta. |
| PostgreSQL | Versão 16; DB/schema `farms`; container saudável, conforme evidência anterior do operador | Snapshot da coleta. |
| Conexão do extrato | `current_database=farms`, `current_user=session_user=deepfarms` | Identidade da conexão usada para coletar metadados; não é introspecção das sessões abertas pelos processos. |
| Role `deepfarms` | `SUPERUSER`, `BYPASSRLS`, `CREATEROLE`, `CREATEDB`, `REPLICATION`, `LOGIN` e `INHERIT` habilitados | Consultado em `pg_roles`; não demonstra uso dessas capacidades em incidentes. |
| Configuração dos serviços | API, Outbox Worker, Automations Worker e Background Worker configurados com usuário `deepfarms`, DB `farms` | `DATABASE_URL` examinada separadamente sem revelar credenciais. Não prova cada conexão já aberta, `SET ROLE` ou caminho alternativo. |

O catálogo lista 15 roles, sendo `deepfarms` a única role de login da lista. Não há membership atribuído a `deepfarms`; as três memberships listadas são da role interna `pg_monitor` para roles de leitura/estatística. Portanto não existe role operacional ou papel de deploy separado evidenciado nesse catálogo.

### 2.2. Inventário físico, RLS e reconciliação individual

| Indicador | Evidência do extrato PostgreSQL | Contrato 01B | Reconciliação |
|---|---:|---:|---|
| Tabelas físicas em `farms` | 350; todas `relkind='r'` | 348 candidatas ORM | 348 nomes coincidentes + 2 tabelas técnicas físicas. Nenhuma partição (`p`) no extrato. |
| RLS habilitado | 49 | 49 | Os conjuntos nominais coincidem exatamente. |
| FORCE RLS | 48 | 48 | Coincidem exatamente. |
| Sem RLS | 301 | 299 candidatas ORM sem RLS | 299 candidatas sem RLS + 2 objetos técnicos adicionais sem RLS. |
| Tabelas cobertas por policies | 49 | 49 | Mesmo conjunto nominal de tabelas RLS. |
| Policies | 188 | 188 no snapshot local | Chaves e metadados reconciliados na seção 5.4. |
| Owner | `deepfarms` em todas as 350 tabelas | Contrato ORM não define owner físico | Um único owner superuser para domínio, plataforma e objetos técnicos. |
| ACL de tabelas | `relacl` NULL nas 350 linhas | Sem grant de runtime aprovado no contrato | Nenhuma ACL explícita aparece no extrato; isso não equivale ao cálculo de todos os privilégios efetivos. |

A única tabela habilitada para RLS sem FORCE é `propriedade_imovel`. A lista nominal das 49 tabelas e seu estado individual está na seção 5.3. Os dois objetos físicos adicionais são `deepfarms_install_manifest` e `deepfarms_install_version`; ambos têm `relkind='r'`, owner `deepfarms`, RLS/FORCE desligados e ACL explícita ausente no extrato. O código clean-install confirma que são recibo/metadado de instalação e controle de versão, não entidades ORM de domínio.

### 2.3. Colunas `tenant_id`

| Indicador físico | Resultado |
|---|---:|
| Tabelas com `tenant_id` direto | 275 |
| Colunas `tenant_id` UUID | 267 |
| Colunas `tenant_id` character varying | 8 |
| Nullable | 22 (todas UUID) |
| NOT NULL | 253 (245 UUID + 8 character varying) |
| Com RLS | 45 |
| Sem RLS | 230 |
| Sem `tenant_id` direto | 75 |

A lista de 275 nomes com `tenant_id` e a lista de 22 colunas nullable coincidem exatamente com a classificação do Anexo A 01B. Das 22 nullable, 20 estão sem RLS; `modelos_fitossanitarios` e `modelos_zoosanitarios` têm RLS e FORCE. As oito colunas `character varying NOT NULL` são `animal_genetica`, `cochos`, `confinamento_lotes`, `racoes_tmr`, `sugestoes_acasalamento` e as três tabelas `carbono_*`; isso coincide com os models que declaram `String(50)`. Esses oito nomes não têm FK `tenant_id -> tenants(id)` no extrato, ao contrário das 267 colunas UUID. É uma diferença de padrão e integridade referencial a revisar, sem prova de Tenant inválido nos dados.

### 2.4. Catálogo de produtos e políticas examinadas

Na tabela `farms.cadastros_produtos`: total 23; globais (`tenant_id IS NULL`) 23; particulares 0; Tenants com produtos particulares 0. Preservar a regra de produto: leitura global pelos Tenants, mutação dos globais pela administração da plataforma e cadastro de produtos próprios por cada Tenant. A contagem não prova a eficácia das autorizações de escrita.

O extrato traz todas as 188 policies físicas. A reconciliação integral com o snapshot de `baseline_contract.py` mostra igualdade de chaves e de comando, permissividade, roles e expressões `USING`/`WITH CHECK`; as únicas diferenças textuais são a qualificação `farms.` exibida pelo PostgreSQL e o whitespace. Não houve teste comportamental com role operacional restrita.

### 2.5. Owners, grants, roles e objetos auxiliares

| Classe de objeto | Estado encontrado |
|---|---|
| Roles | 15 no catálogo; `deepfarms` é a única role de login e tem atributos privilegiados descritos acima. |
| Memberships | 3 arestas apenas na cadeia interna `pg_monitor`; nenhuma membership de `deepfarms`. |
| Schema `farms` | Owner `deepfarms`; `nspacl` NULL (sem ACL explícita no extrato). |
| Tabelas | 350 owners `deepfarms`; todas `relacl` NULL. |
| Sequences | 33; todas owner `deepfarms`, `relacl` NULL. |
| Functions | 3, owner `deepfarms`, `SECURITY DEFINER=false`, `proacl` NULL. São helpers de triggers/constraints; não foi encontrado view no catálogo. |
| Views | 0 linhas. |
| Default privileges | 0 linhas registradas para o escopo consultado. Não há default grant customizado evidenciado. |

ACL NULL significa ausência de ACL explícita armazenada, não que os privilégios efetivos estejam completamente avaliados. O extrato não expandiu ACLs padrão, `PUBLIC`, privilégios no database `farms`, nem `has_*_privilege` por objeto/role. Um novo runtime não receberia ownership: precisaria de `CONNECT`, `USAGE` no schema, DML nas tabelas autorizadas, `USAGE` (e `SELECT` quando necessário) nas sequences efetivamente usadas e `EXECUTE` apenas nas funções de runtime necessárias. A revisão deve calcular isso por API/worker; não conceder `CREATE`, ownership, `TRUNCATE`, DDL, alteração de roles/grants ou capabilities de replication/CREATEROLE/CREATEDB.

Como todas as tabelas/sequences/functions são owned pelo login superuser `deepfarms`, não usar essa role persistente como runtime. Planejar owner de objetos separado, preferencialmente `NOLOGIN`, papel de deploy/manutenção separado e papéis runtime sem `SUPERUSER`, `BYPASSRLS`, ownership ou membership elevável. Sem default privileges customizados, novos objetos podem também ficar inacessíveis ao runtime até que uma concessão explícita/deploy aprovada seja aplicada.

### 2.6. Foreign keys e integridade entre Tenants

O extrato contém **924 FKs físicas** em `farms`. Destas, 267 são `tenant_id -> tenants(id)`. Entre relações em que tabela origem e destino possuem `tenant_id` direto, há 490 constraints: **26** incluem o par `origem.tenant_id -> destino.tenant_id` na mesma FK composta; **464** referenciam apenas outra chave (em geral `id`) e não codificam igualdade de Tenant. Adicionalmente, 59 FKs de 42 tabelas sem `tenant_id` direto apontam para pais com `tenant_id`; 4 dessas 42 tabelas têm RLS relacional e 38 não têm RLS.

Isso confirma uma **possibilidade estrutural** de referência cruzada: uma FK por `id` garante que o pai exista, mas não que pertença ao Tenant da linha filha. Não foram consultadas linhas nem identificadas referências cruzadas efetivamente gravadas. FKs para catálogos globais nullable podem ser legítimas; cada relação precisa de classe funcional. Exemplos físicos incluem `cadastros_pessoas_pii.pessoa_id -> cadastros_pessoas.id`, `cadastros_pessoas_bancario.pessoa_id -> cadastros_pessoas.id`, `compras_itens_pedido.pedido_id -> compras_pedidos.id` e `estoque_lotes.deposito_id -> estoque_depositos.id`. As duas tabelas filhas de pessoas e muitas tabelas filhas de compras/estoque não têm RLS; a proteção atual depende de filtros/serviços e deve ser validada. Não presumir ausência de isolamento apenas por não haver `tenant_id`: 42 tabelas têm cadeia FK observável para pai tenant-scoped, mas a FK sozinha não implementa controle de leitura.

## 3. Matriz de riscos

Severidade é impacto possível. “Confirmado” qualifica o controle/estado observado, não ocorrência de exploração ou dados inconsistentes.

| ID | Nível | Achado | Estado e consequência | Falta para encerrar |
|---|---|---|---|---|
| R1 | **P0 — confirmado** | Os quatro processos backend foram configurados com `deepfarms`, role `SUPERUSER`, `BYPASSRLS`, `CREATEROLE`, `CREATEDB` e `REPLICATION`. | RLS/FORCE não limita essas conexões; controle sobre roles, database e replicação é excessivo para runtime. Não há prova de incidente. | Separar credenciais e comprovar identidades/conexões efetivas no cutover futuro. |
| R2 | **P1 — potencial** | 301 tabelas sem RLS, incluindo 230 com `tenant_id`; todas as 350 são owned pelo mesmo superuser. | Consultas da role atual podem ignorar qualquer proteção de linha; depois da role split, dados continuam dependendo de filtros nos 301 objetos sem policy. | Mapear consumidor/CRUD por tabela e testar autorização; nenhum dado foi lido nesta coleta. |
| R3 | **P1 — potencial** | 464 FKs entre tabelas tenant-scoped não incluem tenant no par referenciado; mais 38 tabelas filhas sem `tenant_id` e sem RLS apontam para pais tenant-scoped. | DDL permite referência cruzada por ID; pode haver validação de serviço, mas ela não está provada como completa. | Revisar constraints e queries por domínio; testes sintéticos cross-tenant fora de produção. |
| R4 | **P1 — potencial, policy confirmada** | Policies de `modelos_fitossanitarios` e `modelos_zoosanitarios` permitem NULL global em todos os comandos. | Uma role com DML pode gravar/alterar/excluir global via SQL; rotas comuns de zoossanitário hoje filtram Tenant e backoffice é admin, mas essa separação não está na policy. | Design de escrita global/admin e grants; ensaio com role restrita. |
| R5 | **P1 — potencial** | `get_db`/`get_db_session` não injetam Tenant automaticamente; há `SET LOCAL` e schedulers com `set_config(..., false)`. | A troca para role com RLS efetivo pode revelar GUC ausente após commit ou estado residual de conexão entre jobs. | Verificar commits, rollbacks, erros/cancelamentos e pool em API/workers. |
| R6 | **P1 — confirmado como dependência** | Nenhuma role operacional separada está listada; tabelas, schema, 33 sequences e 3 funções pertencem a `deepfarms`; ACL explícita e default ACL customizada não aparecem. | Mudança direta de credencial tende a falhar por falta de grants; dar ownership ou superuser para evitar lockout mantém o risco. | Expandir privilégios efetivos, grants no database e plano de proprietário/runtime. |
| R7 | **P2 — confirmado** | Oito tabelas usam `tenant_id varchar`; 267 usam UUID e têm FK para `tenants(id)`. As oito String(50) não têm esse FK. | Convenções e integridade referencial distintas; os tipos coincidem com os models, sem prova de identificadores inválidos. | Confirmar semântica/consumidores e decidir padronização futura. |
| R8 | **P2 — confirmado** | As 188 policies têm paridade integral com o snapshot; 140 com UUID, 48 com comparação textual, 52 com `NULLIF` e 14 com `EXISTS`. | Sem divergência encontrada; padrões variados aumentam custo de revisão e exigem cobertura para GUC vazio/malformado. | Testes futuros em role operacional restrita. |
| R9 | **P2 — pendente** | URL PostgreSQL literal indicada antes em `kill_idle_connections.py`; valor omitido. | Validade e privilégio desconhecidos; risco potencial de credencial versionada. | Responsável verifica e, se necessário, rotaciona/remove sem registrar valor. |
| R10 | **P2 — potencial** | `propriedade_imovel` sem FORCE, embora RLS esteja habilitado; owner atual é superuser. | Uma role operacional não-owner fica sob policy; owner sem FORCE pode ignorar RLS se a role operacional receber ownership indevida. | Preservar owner separado e confirmar necessidade de FORCE no desenho final. |
| R11 | **P3 — pendente semântica** | 20 tabelas sem RLS com `tenant_id` NULL; duas outras nullable têm policies com NULL global. | NULL pode ser referência compartilhada, ausência de associação ou dado sensível; não presumir leitura global. | Decisão funcional/CRUD por tabela, sem inferir pelos valores nulos. |


## 4. Tabelas nullable e semântica funcional

A coleta física confirma 20 tabelas sem RLS com `tenant_id` UUID nullable; seus nomes, classes e evidências estáticas estão nas linhas correspondentes da matriz de 230 candidatas na seção 5.3. Há mais duas tabelas físicas com `tenant_id` UUID nullable, `modelos_fitossanitarios` e `modelos_zoosanitarios`, ambas com RLS e FORCE, listadas na seção 5.2. Suas policies incluem explicitamente `tenant_id IS NULL` em todos os comandos; o predicado permite linhas globais também para escrita se a role tiver DML, sem distinção administrativa na policy. `tenant_id NULL` nas outras 20 **não prova compartilhamento público**. A classificação funcional é preliminar, baseada no contrato ORM e no código consultado; não prova todos os consumidores ativos nem substitui a validação CRUD por tabela.



## 5. Cobertura RLS e lacunas

### 5.1. Auditoria nominal do inventário ORM 01B

A extração foi feita do **Anexo A — Matriz estrutural por tabela do contrato ORM** em `DEEPFARMS-RLS-HOSTINGER-01B-PLANO-CORRECAO.md`, lendo a coluna `Tabela` das linhas de dados da tabela Markdown. Cabeçalho/legenda não contam como candidato. O critério declarado no código é `baseline_candidate_tables() = registered_tables() − BASELINE_EXCLUDED_TABLES` (`services/api/core/model_registry.py`); logo, a lista representa o subconjunto ORM aprovado como candidato à baseline, não todo objeto PostgreSQL nem toda tabela técnica. A validação tratou o nome entre crases como chave exata, encontrou **348 linhas e 348 nomes únicos, sem duplicidades**. O próprio 01B qualifica o anexo como contrato ORM local/candidato, não como inventário físico ou decisão semântica final.

| Partição estática do Anexo A 01B | Quantidade | Checagem |
|---|---:|---|
| Total de candidatas ORM | 348 | 348 linhas; 348 nomes únicos. |
| Sem RLS aprovado no contrato | 299 | 230 com `tenant_id` direto + 69 sem coluna direta. |
| RLS no contrato, com FORCE | 48 | Uma candidata é a exceção sem FORCE abaixo. |
| RLS no contrato, sem FORCE | 1 | `propriedade_imovel`. |
| Com `tenant_id` direto e RLS ausente no contrato | 230 | 210 NOT NULL + 20 nullable no ORM. |
| Sem `tenant_id` direto e RLS ausente no contrato | 69 | Classe exige distinguir filhas tenant-scoped, globais, plataforma e técnicas. |
| Com `tenant_id` direto e RLS no contrato | 45 | 43 NOT NULL + 2 nullable. |
| Sem `tenant_id` direto e RLS no contrato | 4 | RLS/relacionamento pode impor escopo sem coluna própria; conferir FKs e expressions. |
| Com `tenant_id` direto no total do contrato | 275 | 253 NOT NULL + 22 nullable. |
| Sem `tenant_id` direto no total do contrato | 73 | 69 sem RLS + 4 com RLS. |

As somas fecham: 299 + 48 + 1 = 348; 230 + 69 = 299; 45 + 4 = 49 com RLS; 275 + 73 = 348. Das 22 colunas nullable no contrato e no catálogo físico, 20 estão no grupo sem RLS e duas são `modelos_fitossanitarios` e `modelos_zoosanitarios`, com RLS + FORCE. O cruzamento dos metadados confirma os estados individuais e os nomes; a semântica das linhas NULL continua a exigir validação funcional.

O Anexo A já contém os 348 nomes, declarações de `tenant_id`, classe preliminar, estado RLS do contrato, referências estruturais e recomendação/consumidores candidatos. A matriz das 230 abaixo é o subconjunto nominal com `tenant_id` direto e RLS ausente no contrato. Os outros 118 nomes (69 sem coluna direta + 49 com RLS no contrato) permanecem nominalmente disponíveis no próprio Anexo A; ausência de `tenant_id` não os torna automaticamente globais.

**Reconciliação nominal da lista física atual:** o arquivo `/tmp/deepfarms-rls-01c-tabelas.txt`, fornecido pelo operador como extração do schema `farms` com `relkind IN ('r','p')`, contém 350 linhas não vazias e 350 nomes únicos, sem duplicidades. São nomes simples (`relname`), comparados por igualdade exata com a coluna `Tabela` do Anexo A; nenhuma normalização, alias ou correção ortográfica foi aplicada. O arquivo contém nomes, não `relkind`, colunas, RLS, owner ou grants por linha. Não houve conexão direta do Codex ao PostgreSQL. O relatório anterior `MIGRATION-METADATA-01A` descreve uma fotografia distinta de 351 objetos e não foi usado nesta comparação.

| Comparação por nome exato | Quantidade | Nomes / observação |
|---|---:|---|
| Presentes nos dois conjuntos | 348 | Todos os nomes do Anexo A 01B aparecem na lista física. |
| Somente PostgreSQL | 2 | `deepfarms_install_manifest`, `deepfarms_install_version`. |
| Somente ORM 01B | 0 | Nenhum. |
| União | 350 | 348 comuns + 2 somente físicos. |
| Diferença simétrica | 2 | Os dois objetos somente físicos. |

A cardinalidade é matematicamente consistente: `350 = 348 + 2`, `348 = 348 + 0`; a diferença de tamanho dos conjuntos é 2 e a diferença simétrica também é 2 porque a interseção comprovada tem 348 nomes.


**Nomes da interseção (348), ordenados lexicograficamente e comparados sem normalização:**

```text
admin_audit_log
admin_impersonations
admin_users
agricola_devolucoes_embalagens
agricola_lotes_beneficiamento
agricola_operacao_tipo_fase
agricola_orcamento_itens
agricola_produto_colhido_cost_allocations
agricola_produtos_colhidos
agricola_receituario_itens
agricola_receituarios_agronomicos
agricola_regras_agronomicas
alert_events
alert_indicators
alert_insights
alert_lifecycle_events
amb_alertas
amb_outorgas_hidricas
amb_registros_car
analises_solo
animal_genetica
assinaturas_tenant
automacoes_configuracoes
automacoes_execucoes
balanca_inbound_events
balanca_webhook_credentials
billing_solicitacoes_comerciais
billing_solicitacoes_comerciais_historico
cadastros_areas_registros_ambientais
cadastros_areas_rurais
cadastros_areas_valores_patrimoniais
cadastros_arquivos_geo
cadastros_categorias_produto
cadastros_commodities
cadastros_commodities_classificacoes
cadastros_commodities_cotacoes
cadastros_conversao_unidades
cadastros_culturas
cadastros_documentos_exploracao
cadastros_equipamentos
cadastros_equipamentos_calibracoes
cadastros_exploracoes_rurais
cadastros_infraestruturas
cadastros_marcas
cadastros_modelos_produto
cadastros_pessoa_relacionamentos
cadastros_pessoas
cadastros_pessoas_acesso_log
cadastros_pessoas_bancario
cadastros_pessoas_consentimentos
cadastros_pessoas_contatos
cadastros_pessoas_documentos
cadastros_pessoas_enderecos
cadastros_pessoas_pii
cadastros_pessoas_profissional_agronomo
cadastros_pessoas_usuarios
cadastros_produtos
cadastros_produtos_agricola
cadastros_produtos_epi
cadastros_produtos_estoque
cadastros_propriedades
cadastros_tipos_irrigacao
cadastros_tipos_relacionamento
cadastros_tipos_servico
cadastros_tipos_solo
caderno_campo_entradas
caderno_campo_fotos
caderno_evento_status_historico
caderno_exportacoes
caderno_lotes_comerciais
cafe_lote_beneficiamento_detalhes
cafe_lote_beneficiamento_romaneios
campo_dispositivos
campo_sync_tombstones
campo_tarefas
carbono_emissoes
carbono_projetos
carbono_relatorios
case_ih
categoria_custom
certificacao_avaliacoes
certificacao_checklists
certificacao_criterios
certificacao_evidencias
certificacao_nao_conformidades
certificacao_planos_acao
certificacao_programas
certificacoes_propriedade
chamados_suporte
cobrancas_asaas
cochos
comparador_precos
compras_alocacoes_item
compras_cotacoes
compras_cotacoes_itens
compras_devolucoes
compras_devolucoes_itens
compras_fornecedores
compras_itens_pedido
compras_pedidos
compras_pedidos_confirmacoes
compras_pedidos_cotacoes
compras_recebimentos
compras_recebimentos_itens
compras_solicitacoes
compras_solicitacoes_itens
configuracao_fazenda
configuracoes_saas
configuracoes_tenant
confinamento_lotes
conhecimento_artigos
conhecimento_categorias
contratos_futuros_v2
conversas_agronomo
convites_acesso
core_sequenciais
cost_allocations
crm_atividades
crm_leads
crm_ofertas_personalizadas
crm_pipeline_estagios
crm_planos_comerciais
crm_precificacao_modulo
crm_produtos
cultivo_areas
cultivos
culturas
cupons
diagnosticos
domain_event_outbox
email_logs
email_templates
epi_entregas
equipamento_alocacoes
esg_relatorio_evidencias
esg_relatorio_indicadores
esg_relatorios
estoque_contagem_itens
estoque_contagens
estoque_depositos
estoque_implantacao_itens
estoque_implantacao_sessoes
estoque_localizacoes
estoque_lotes
estoque_movimentos
estoque_requisicao_confirmacoes
estoque_requisicao_item_eventos
estoque_requisicao_responsabilidades
estoque_requisicoes
estoque_requisicoes_itens
estoque_reservas
estoque_saldos
faturas
fenologia_escalas
fin_contas_bancarias
fin_despesas
fin_itens_ordem_pagamento
fin_lancamentos_bancarios
fin_notas_fiscais
fin_ordens_pagamento
fin_planos_conta
fin_rateios
fin_receitas
financeiro_comercializacoes
financeiro_lancamentos
financeiro_plano_acoes
financeiro_safra_cenarios
frota_abastecimentos
frota_apontamentos_uso
frota_checklist_modelos
frota_checklists_operacionais
frota_checklists_operacionais_itens
frota_checklists_operacionais_respostas
frota_checklists_realizados
frota_documentos_equipamentos
frota_jornadas_equipamento
frota_logs_automacao
frota_ordens_servico
frota_os_itens
frota_planos_manutencao
frota_registros_manutencao
frota_regras_inteligentes
growth_landing_eventos
hedge_position_snapshots_v2
hedge_registros_v2
historico_bloqueios
historico_configuracao
ia_acoes_assistidas_historico
ia_alertas_historico
ia_autopilot_config
ia_compras_recomendacoes
ia_creditos_pacotes
ia_growth_assistente_interacoes
ia_growth_autopilot_acoes
ia_growth_config
ia_growth_config_historico
ia_growth_copy_cache
ia_growth_eventos
ia_growth_experimento_eventos
ia_growth_experimento_variantes
ia_growth_experimentos
ia_growth_incentivos
ia_growth_learning_weights
ia_growth_plano_recomendado_log
ia_growth_sugestoes
ia_growth_user_profiles
ia_prompt_versoes_historico
ia_prompts_versoes
ia_uso
ia_ux_telemetria
ia_ux_thresholds
imagens_ndvi
imoveis_arrendamento_parcelas
imoveis_arrendamento_reajustes
imoveis_arrendamentos
imoveis_avaliacoes
imoveis_benfeitorias
imoveis_cartorios
imoveis_documentos
imoveis_documentos_historico
imoveis_matriculas
imoveis_ordens_servico_benfeitoria
imoveis_planos_manutencao_benfeitoria
imoveis_rurais
imoveis_sistemas_irrigacao
insumos_operacao
integration_credentials
integration_external_record_link_history
integration_external_record_links
integration_features
integration_health_snapshots
integration_jobs
integration_sync_policies
integration_versions
john_deere
login_tentativas
lotes_rastreabilidade
marketplace_integracoes
mensagens_chamado
modelos_fitossanitarios
modelos_ml
modelos_zoosanitarios
module_usage_stats
monitoramento_catalogo
monitoramento_pragas
mudancas_plano
notificacoes
notificacoes_leituras
notificacoes_preferencias
operacional_apontamentos_mao_obra
operacional_qualidade_ajustes
operacional_qualidade_criterios
operacional_qualidade_laudos
operacional_qualidade_protocolos
operacional_qualidade_resultados
operacoes_agricolas
operacoes_execucoes
operation_dependencies
operation_template_items
operation_templates
operational_alerts
pec_animais
pec_eventos_animal
pec_lotes
pec_manejos_lote
pec_piquetes
pec_producao_leite
perfis_acesso
phase_gate_rules
phase_template_checklist_items
phase_template_tasks
phase_templates
plano_pricing
planos_assinatura
planos_operacionais
planos_operacionais_tarefas
planos_operacionais_tarefas_insumos
planos_operacionais_tarefas_mao_obra
planos_operacionais_tarefas_maquinario
pragas_doencas
prescricoes_vra
previsoes_clima
previsoes_produtividade
production_units
propriedade_imovel
racas
racoes_tmr
rastreabilidade_passaporte_eventos
rastreabilidade_passaporte_evidencias
rastreabilidade_passaportes
receitas_aplicacao
receitas_aplicacao_insumos
receitas_aplicacao_mao_obra
recomendacoes
recommendation_lifecycle_events
recommendation_results
registros_clima
relatorios_tecnicos
rh_colaboradores
rh_departamentos
rh_empreitadas
rh_esocial_eventos
rh_lancamentos_diarias
rh_seguranca_documentos
rh_seguranca_entregas
rh_seguranca_itens
romaneios_colheita
safra_cenarios
safra_cenarios_unidades
safra_checklist_itens
safra_fase_historico
safra_fenologia_registros
safra_talhao_grupo_itens
safra_talhao_grupos
safra_talhoes
safra_tarefa_necessidades
safra_tarefas
safras
sankhya_config
sankhya_lancamentos_financeiros
sankhya_nfe
sankhya_pessoas
sankhya_produtos
sankhya_sync_logs
sankhya_tabelas
sessoes_ativas
solo_parametros_cultura
status_consorcio_area
sugestoes_acasalamento
tenant_audit_log
tenant_integracoes
tenant_usuarios
tenants
tokens_recuperacao_senha
tratamentos
unidade_produtiva_usuarios
unidades_medida
unidades_medida_conversoes
unidades_produtivas
usuario_byok_credenciais
usuarios
visitas_tecnicas
whatsapp
wizard_implantacoes_checklist_itens
wizard_implantacoes_etapas
wizard_implantacoes_historico
wizard_implantacoes_operacionais
wizard_implantacoes_pendencias
```

**Classificação dos dois objetos somente físicos (evidência estática do código e metadados):** `deepfarms_install_version` é a tabela de controle de versão da linhagem clean-install (`services/api/migrations/clean_install/env.py`, README da linhagem); `deepfarms_install_manifest` é recibo singleton da instalação com versões e hashes da baseline/seeds e timestamp (`services/api/migrations/clean_install/versions/20261025_clean_install_v1.py`). Ambos são objetos técnicos de instalação, não entidades de negócio ORM candidatas do Anexo A. O extrato confirma owner `deepfarms`, RLS/FORCE desligados e `relacl` NULL; isso não equivale a afirmar ausência de privilégios efetivos nem dispensa revisão de acesso administrativo. Não foi encontrada divergência de nomenclatura entre os 348 nomes comuns.

### 5.2. Reconciliação física e estados individuais de RLS

| Fonte | Total | Com RLS | Sem RLS / outra classe | Interpretação |
|---|---:|---:|---:|---|
| PostgreSQL Hostinger | 350 | 49 | 301 sem RLS | Todas as tabelas são `relkind='r'`, owner `deepfarms`. |
| Candidatas ORM do Anexo A 01B | 348 | 49 | 299 sem RLS | Todas as 348 aparecem fisicamente; os dois extras são técnicos. |

Os 49 nomes físicos com `relrowsecurity=true` são exatamente iguais a `RLS_ENABLED_TABLES` em `baseline_contract.py`; o conjunto com `relforcerowsecurity=true` é igual a `RLS_FORCED_TABLES`. Não há diferença nominal de RLS entre PostgreSQL e 01B. O total de 301 sem RLS fecha como 299 candidatas ORM sem RLS mais `deepfarms_install_manifest` e `deepfarms_install_version`, ambos sem RLS e sem `tenant_id` direto.

| Tabela | RLS físico | FORCE físico | Owner |
|---|---|---|---|
| `alert_events` | enabled | enabled | deepfarms |
| `alert_indicators` | enabled | enabled | deepfarms |
| `alert_insights` | enabled | enabled | deepfarms |
| `alert_lifecycle_events` | enabled | enabled | deepfarms |
| `amb_alertas` | enabled | enabled | deepfarms |
| `amb_outorgas_hidricas` | enabled | enabled | deepfarms |
| `amb_registros_car` | enabled | enabled | deepfarms |
| `balanca_inbound_events` | enabled | enabled | deepfarms |
| `balanca_webhook_credentials` | enabled | enabled | deepfarms |
| `carbono_emissoes` | enabled | enabled | deepfarms |
| `carbono_projetos` | enabled | enabled | deepfarms |
| `carbono_relatorios` | enabled | enabled | deepfarms |
| `certificacao_avaliacoes` | enabled | enabled | deepfarms |
| `certificacao_checklists` | enabled | enabled | deepfarms |
| `certificacao_criterios` | enabled | enabled | deepfarms |
| `certificacao_evidencias` | enabled | enabled | deepfarms |
| `certificacao_nao_conformidades` | enabled | enabled | deepfarms |
| `certificacao_planos_acao` | enabled | enabled | deepfarms |
| `certificacao_programas` | enabled | enabled | deepfarms |
| `configuracao_fazenda` | enabled | enabled | deepfarms |
| `domain_event_outbox` | enabled | enabled | deepfarms |
| `esg_relatorio_evidencias` | enabled | enabled | deepfarms |
| `esg_relatorio_indicadores` | enabled | enabled | deepfarms |
| `esg_relatorios` | enabled | enabled | deepfarms |
| `integration_credentials` | enabled | enabled | deepfarms |
| `integration_external_record_link_history` | enabled | enabled | deepfarms |
| `integration_external_record_links` | enabled | enabled | deepfarms |
| `integration_features` | enabled | enabled | deepfarms |
| `integration_health_snapshots` | enabled | enabled | deepfarms |
| `integration_jobs` | enabled | enabled | deepfarms |
| `integration_sync_policies` | enabled | enabled | deepfarms |
| `integration_versions` | enabled | enabled | deepfarms |
| `modelos_fitossanitarios` | enabled | enabled | deepfarms |
| `modelos_zoosanitarios` | enabled | enabled | deepfarms |
| `operational_alerts` | enabled | enabled | deepfarms |
| `previsoes_clima` | enabled | enabled | deepfarms |
| `propriedade_imovel` | enabled | disabled | deepfarms |
| `rastreabilidade_passaporte_eventos` | enabled | enabled | deepfarms |
| `rastreabilidade_passaporte_evidencias` | enabled | enabled | deepfarms |
| `rastreabilidade_passaportes` | enabled | enabled | deepfarms |
| `recommendation_lifecycle_events` | enabled | enabled | deepfarms |
| `recommendation_results` | enabled | enabled | deepfarms |
| `registros_clima` | enabled | enabled | deepfarms |
| `tenant_integracoes` | enabled | enabled | deepfarms |
| `wizard_implantacoes_checklist_itens` | enabled | enabled | deepfarms |
| `wizard_implantacoes_etapas` | enabled | enabled | deepfarms |
| `wizard_implantacoes_historico` | enabled | enabled | deepfarms |
| `wizard_implantacoes_operacionais` | enabled | enabled | deepfarms |
| `wizard_implantacoes_pendencias` | enabled | enabled | deepfarms |

`propriedade_imovel` é a única com RLS habilitado e FORCE desabilitado. Como o owner atual é superuser/BYPASSRLS, FORCE não neutraliza a identidade atual. Uma role operacional não-owner e sem bypass será sujeita às policies mesmo nessa tabela; FORCE continua defesa adicional se owner for usado acidentalmente.

Os dois objetos físicos extras são objetos técnicos de clean-install: `deepfarms_install_version` controla a revisão dessa linhagem; `deepfarms_install_manifest` guarda versão/hash da baseline/seeds e timestamp em registro singleton. Não são catálogos globais de negócio nem tabelas tenant-scoped. Ainda assim, devem ficar fora do DML runtime salvo dependência comprovada.

### 5.3. Matriz das 230 candidatas estáticas com `tenant_id` e sem RLS

As colunas de nulabilidade, classe e referências consumidoras vêm do Anexo A do 01B; RLS, FORCE, owner e tipo/nulabilidade física de `tenant_id` vêm do extrato PostgreSQL fornecido pelo operador. Os 230 nomes desta matriz estão presentes nos dois conjuntos por igualdade exata e foram reconciliados individualmente com o metadado físico: todos têm RLS/FORCE desligados, owner `deepfarms` e ACL bruta NULL. “Referências consumidoras” são relações/dependências registradas no contrato, não um call graph exaustivo nem prova de execução em produção.

| Tabela candidata | Declaração `tenant_id` no contrato | Classe funcional preliminar 01B | Referências/consumidores do contrato 01B | Estado físico individual |
|---|---|---|---|---|
| `admin_impersonations` | sim; NOT NULL; model NOT NULL; validar produção | PLATFORM_PRIVATE (candidato) | admin_users, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_devolucoes_embalagens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, cadastros_produtos, compras_recebimentos_itens, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_lotes_beneficiamento` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cultivos, estoque_lotes, production_units, romaneios_colheita (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_orcamento_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cultivos, production_units, safras, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_produto_colhido_cost_allocations` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_produtos_colhidos, cost_allocations, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_produtos_colhidos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_commodities, cadastros_commodities_classificacoes, operacional_qualidade_laudos, romaneios_colheita (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_receituario_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_receituarios_agronomicos, cadastros_produtos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_receituarios_agronomicos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_pessoas, operacoes_agricolas, safras, tenants (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `agricola_regras_agronomicas` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `analises_solo` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, production_units, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `animal_genetica` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | racas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id character varying NOT NULL; ACL explícita NULL. |
| `assinaturas_tenant` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | planos_assinatura, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `automacoes_configuracoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `automacoes_execucoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `billing_solicitacoes_comerciais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `billing_solicitacoes_comerciais_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_areas_rurais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_tipos_irrigacao, cadastros_tipos_solo, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_arquivos_geo` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_categorias_produto` | sim; nullable; NULL padrão/global documentado ou tratado pelo service; validar distribuição e regra admin | GLOBAL_READ_TENANT_WRITE (código explícito) | cadastros_categorias_produto, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_commodities` | sim; nullable; Service consulta NULL e próprio; significado de escrita/NULL pendente | GLOBAL_READ_TENANT_WRITE? (candidato) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_culturas` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_documentos_exploracao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_exploracoes_rurais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_equipamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_equipamentos_calibracoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_exploracoes_rurais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_propriedades, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_infraestruturas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_marcas` | sim; nullable; NULL padrão/global documentado ou tratado pelo service; validar distribuição e regra admin | GLOBAL_READ_TENANT_WRITE (código explícito) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_modelos_produto` | sim; nullable; NULL padrão/global documentado ou tratado pelo service; validar distribuição e regra admin | GLOBAL_READ_TENANT_WRITE (código explícito) | cadastros_marcas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_pessoas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_pessoas_profissional_agronomo` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_pessoas_usuarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, tenant_usuarios, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_produtos` | sim; nullable; NULL padrão/global documentado ou tratado pelo service; validar distribuição e regra admin | GLOBAL_READ_TENANT_WRITE (código explícito) | cadastros_categorias_produto, cadastros_marcas, cadastros_modelos_produto, cadastros_produtos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_propriedades` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cadastros_tipos_relacionamento` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `cadastros_tipos_servico` | sim; nullable; NULL padrão/global documentado ou tratado pelo service; validar distribuição e regra admin | GLOBAL_READ_TENANT_WRITE (código explícito) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `caderno_campo_entradas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_receituarios_agronomicos, cadastros_areas_rurais, cadastros_pessoas, caderno_campo_entradas, operacoes_agricolas (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `caderno_evento_status_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | caderno_campo_entradas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `caderno_exportacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `caderno_lotes_comerciais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_lotes_beneficiamento, agricola_produtos_colhidos, financeiro_comercializacoes, lotes_rastreabilidade, tenants (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cafe_lote_beneficiamento_detalhes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_lotes_beneficiamento, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cafe_lote_beneficiamento_romaneios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_lotes_beneficiamento, romaneios_colheita, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `campo_dispositivos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `campo_sync_tombstones` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `campo_tarefas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | campo_dispositivos, operacoes_agricolas, safra_tarefas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `case_ih` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `categoria_custom` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | categoria_custom, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `certificacoes_propriedade` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `chamados_suporte` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cobrancas_asaas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | assinaturas_tenant, mudancas_plano, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cochos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | confinamento_lotes, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id character varying NOT NULL; ACL explícita NULL. |
| `comparador_precos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_cotacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | compras_fornecedores, compras_solicitacoes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_devolucoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | compras_fornecedores, compras_pedidos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_fornecedores` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_pedidos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | compras_cotacoes, compras_fornecedores, compras_solicitacoes, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_pedidos_confirmacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | compras_pedidos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `compras_solicitacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `configuracoes_tenant` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `confinamento_lotes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id character varying NOT NULL; ACL explícita NULL. |
| `contratos_futuros_v2` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_commodities, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `conversas_agronomo` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `convites_acesso` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | perfis_acesso, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `core_sequenciais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cost_allocations` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | estoque_movimentos, estoque_requisicao_item_eventos, fin_rateios, operacoes_execucoes, production_units (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cultivo_areas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | analises_solo, cadastros_areas_rurais, cultivos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `cultivos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_commodities, cadastros_culturas, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `culturas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `diagnosticos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `email_logs` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | email_templates, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `epi_entregas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `equipamento_alocacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, cadastros_pessoas, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_contagem_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_contagens, estoque_movimentos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_contagens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | estoque_depositos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_depositos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_implantacao_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, estoque_implantacao_sessoes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_implantacao_sessoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_localizacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_movimentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, compras_fornecedores, estoque_depositos, estoque_lotes, estoque_movimentos (+5) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_requisicao_confirmacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | campo_dispositivos, estoque_requisicoes, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_requisicao_item_eventos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, estoque_requisicao_item_eventos, estoque_requisicoes, estoque_requisicoes_itens, operacoes_agricolas (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_requisicao_responsabilidades` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, cadastros_pessoas_usuarios, estoque_requisicoes, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_requisicoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, operacoes_agricolas, planos_operacionais_tarefas, safra_tarefas, safras (+3) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_requisicoes_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, estoque_lotes, estoque_requisicoes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `estoque_reservas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, estoque_requisicoes_itens, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `faturas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | assinaturas_tenant, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fenologia_escalas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_contas_bancarias` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_despesas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, cultivos, fin_contas_bancarias, fin_planos_conta, tenants (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_itens_ordem_pagamento` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | fin_despesas, fin_ordens_pagamento, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_lancamentos_bancarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | fin_contas_bancarias, fin_despesas, fin_receitas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_notas_fiscais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_ordens_pagamento` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | fin_contas_bancarias, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_planos_conta` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_categorias_produto, fin_planos_conta, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_rateios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, fin_despesas, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `fin_receitas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, fin_planos_conta, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `financeiro_comercializacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | agricola_produtos_colhidos, cadastros_commodities, cadastros_pessoas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `financeiro_lancamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `financeiro_plano_acoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `financeiro_safra_cenarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_abastecimentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_equipamentos, cadastros_pessoas, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_apontamentos_uso` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_equipamentos, cadastros_pessoas, frota_jornadas_equipamento, operacoes_agricolas (+4) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_checklist_modelos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_checklists_operacionais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_checklists_operacionais_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | frota_checklists_operacionais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_checklists_operacionais_respostas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, cadastros_pessoas, frota_checklists_operacionais, frota_checklists_operacionais_itens, frota_jornadas_equipamento (+4) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_checklists_realizados` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, cadastros_pessoas, frota_checklist_modelos, frota_ordens_servico, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_documentos_equipamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_jornadas_equipamento` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_equipamentos, cadastros_pessoas, safras, tenants (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_logs_automacao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | frota_regras_inteligentes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_ordens_servico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_equipamentos, frota_planos_manutencao, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_os_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, estoque_lotes, estoque_movimentos, frota_ordens_servico (+3) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_planos_manutencao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_registros_manutencao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_equipamentos, frota_ordens_servico, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `frota_regras_inteligentes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `hedge_position_snapshots_v2` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_commodities, contratos_futuros_v2, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `hedge_registros_v2` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | contratos_futuros_v2, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `historico_bloqueios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | admin_users, assinaturas_tenant, mudancas_plano, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `historico_configuracao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_acoes_assistidas_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_alertas_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_autopilot_config` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_compras_recomendacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_creditos_pacotes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_assistente_interacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_autopilot_acoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_config` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_config_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_copy_cache` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_eventos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_experimento_eventos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | ia_growth_experimento_variantes, ia_growth_experimentos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_experimentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_incentivos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_learning_weights` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_plano_recomendado_log` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_growth_sugestoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_prompt_versoes_historico` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | ia_prompts_versoes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `ia_prompts_versoes` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `ia_uso` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `ia_ux_telemetria` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imagens_ndvi` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_arrendamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, imoveis_rurais, tenants, unidades_produtivas, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_avaliacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_rurais, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_cartorios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_documentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_documentos, imoveis_rurais, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_matriculas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_cartorios, imoveis_rurais, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_ordens_servico_benfeitoria` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, imoveis_benfeitorias, imoveis_planos_manutencao_benfeitoria, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_planos_manutencao_benfeitoria` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_benfeitorias, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_rurais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_cartorios, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `imoveis_sistemas_irrigacao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | imoveis_rurais, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `insumos_operacao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_lotes, operacoes_agricolas, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `john_deere` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `lotes_rastreabilidade` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `modelos_ml` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `module_usage_stats` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `monitoramento_catalogo` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `monitoramento_pragas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, monitoramento_catalogo, safra_fenologia_registros, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `mudancas_plano` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | admin_users, assinaturas_tenant, planos_assinatura, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `notificacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `notificacoes_leituras` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | notificacoes, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `notificacoes_preferencias` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacional_apontamentos_mao_obra` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_pessoas, operacoes_agricolas, production_units, safras (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacional_qualidade_ajustes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | operacional_qualidade_criterios, operacional_qualidade_laudos, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacional_qualidade_laudos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, operacional_qualidade_protocolos, production_units, romaneios_colheita, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacional_qualidade_protocolos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_commodities, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacoes_agricolas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_pessoas, cultivos, production_units, safra_tarefas (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operacoes_execucoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, operacoes_agricolas, production_units, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `operation_templates` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `pec_animais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | pec_animais, pec_lotes, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pec_eventos_animal` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_pessoas, cadastros_produtos, campo_tarefas, pec_animais (+3) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pec_lotes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pec_manejos_lote` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, pec_lotes, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pec_piquetes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pec_producao_leite` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, pec_animais, pec_lotes, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `perfis_acesso` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `phase_templates` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `planos_operacionais` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | production_units, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `planos_operacionais_tarefas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | planos_operacionais, safra_tarefas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `planos_operacionais_tarefas_insumos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, estoque_reservas, planos_operacionais_tarefas, planos_operacionais_tarefas_insumos (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `planos_operacionais_tarefas_mao_obra` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, cadastros_tipos_servico, planos_operacionais_tarefas, safra_tarefa_necessidades, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `planos_operacionais_tarefas_maquinario` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_equipamentos, planos_operacionais_tarefas, safra_tarefa_necessidades, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `pragas_doencas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `prescricoes_vra` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `previsoes_produtividade` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `production_units` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cultivo_areas, cultivos, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `racoes_tmr` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | — | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id character varying NOT NULL; ACL explícita NULL. |
| `receitas_aplicacao` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `receitas_aplicacao_insumos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_produtos, estoque_depositos, receitas_aplicacao, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `receitas_aplicacao_mao_obra` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_tipos_servico, receitas_aplicacao, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `recomendacoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `relatorios_tecnicos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_colaboradores` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_pessoas, rh_departamentos, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_departamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_empreitadas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | rh_colaboradores, safras, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_esocial_eventos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | rh_colaboradores, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_lancamentos_diarias` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | rh_colaboradores, safras, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_seguranca_documentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | rh_colaboradores, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_seguranca_entregas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | rh_colaboradores, rh_seguranca_itens, tenants, unidades_produtivas | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `rh_seguranca_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `romaneios_colheita` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, cadastros_commodities, cadastros_pessoas, campo_tarefas, cultivos (+4) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_cenarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_cenarios_unidades` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | production_units, safra_cenarios, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_checklist_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | estoque_requisicoes, estoque_reservas, operacoes_agricolas, phase_template_checklist_items, safras (+1) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_fase_historico` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_fenologia_registros` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, fenologia_escalas, safra_talhao_grupos, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_talhao_grupo_itens` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safra_talhao_grupos, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_talhao_grupos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_talhoes` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_tarefa_necessidades` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | safra_tarefas, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safra_tarefas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | analises_solo, cadastros_areas_rurais, cultivo_areas, operacoes_agricolas, production_units (+2) | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `safras` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_config` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_lancamentos_financeiros` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_nfe` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_pessoas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_produtos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_sync_logs` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | sankhya_config, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sankhya_tabelas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sessoes_ativas` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants, unidades_produtivas, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `solo_parametros_cultura` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | cadastros_culturas, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `status_consorcio_area` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `sugestoes_acasalamento` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | — | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id character varying NOT NULL; ACL explícita NULL. |
| `tenant_audit_log` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `tenant_usuarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | perfis_acesso, tenants, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `tratamentos` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `unidade_produtiva_usuarios` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | perfis_acesso, tenants, unidades_produtivas, usuarios | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `unidades_medida` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `unidades_medida_conversoes` | sim; nullable; nullable no ORM; significado de NULL pendente | TENANT_PRIVATE (candidato; validar NULL) | cadastros_commodities, tenants, unidades_medida | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NULL; ACL explícita NULL. |
| `unidades_produtivas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `visitas_tecnicas` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | cadastros_areas_rurais, safras, tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |
| `whatsapp` | sim; NOT NULL; NOT NULL no ORM; validar nullability física | TENANT_PRIVATE (candidato; validar NULL) | tenants | Físico: relkind r; RLS off/FORCE off; owner deepfarms; tenant_id uuid NOT NULL; ACL explícita NULL. |

**Leitura de risco dessa matriz:** nomes com dados cadastrais, financeiros, credenciais, sessão, PII, documentos, estoque e operações agrícolas são prioritários para provar controle de linha. A classificação `GLOBAL_READ_TENANT_WRITE`, `TENANT_PRIVATE`, `TENANT_INHERITED` ou `GLOBAL` é hipótese/contrato estático, não decisão de policy. As 69 candidatas sem `tenant_id` direto também exigem análise: parte pode ser filha tenant-scoped por FK, parte sistema/global e parte identidade/admin. Não declarar qualquer grupo isento sem conferir FKs, grants e consumidores.

### 5.4. Reconciliação das 188 policies

O inventário físico contém 188 policies em 49 tabelas e coincide integralmente com o snapshot de `POLICY_CONTRACT` em `baseline_contract.py`: 188/188 chaves (`schema`, tabela e nome), comandos, `PERMISSIVE`, `TO PUBLIC` e expressões `USING`/`WITH CHECK`. Para comparação textual, normalizei whitespace e removi a qualificação `farms.` que `pg_policies` inclui nas subqueries; após isso, houve **zero divergências de expressão**. A tabela `propriedade_imovel` e `tenant_integracoes` continuam dentro desse conjunto, não são as únicas policies auditadas nesta rodada.

| Propriedade física | Quantidade |
|---|---:|
| SELECT / INSERT / UPDATE / DELETE / ALL | 47 / 47 / 46 / 46 / 2 |
| `PERMISSIVE TO PUBLIC` | 188 |
| Policies com comparação UUID (`::uuid`) | 140 |
| Policies com comparação via texto (`tenant_id::text`) | 48 |
| Policies com `NULLIF` | 52 |
| Policies com subquery `EXISTS` | 14 |
| Divergências contra snapshot local após normalização | 0 |

As formas UUID/texto são diferentes, mas coincidem com o snapshot capturado. A variação é uma questão de consistência/manutenção e deve ser testada com contexto ausente/malformado; não há, nesta comparação, sinal de policy física divergente. `TO PUBLIC` não concede `SELECT`/DML: privilégios ACL seguem obrigatórios. Sem grant, a policy não dá acesso; com grant, todos os comandos autorizados pela policy ficam disponíveis a roles comuns.

**Exceção global de escrita:** as policies de `modelos_fitossanitarios` e `modelos_zoosanitarios` usam `(tenant_id::text = NULLIF(current_setting(...), '') OR tenant_id IS NULL)` em SELECT, INSERT, UPDATE e DELETE (UPDATE também em `WITH CHECK`). Portanto, uma role comum com DML pode inserir linha NULL global e pode atualizar/excluir linha global segundo essas policies. Isso não prova que a API permita a um Tenant fazê-lo: no código observado, rotas tenant-scoped de `modelos_zoosanitarios` fixam `tenant_id` ao Tenant e o CRUD global está sob `get_current_admin`; a policy de banco, contudo, não separa essa autorização de plataforma. A proteção de escrita global dependeria hoje da aplicação e dos grants. Nenhum teste comportamental foi executado.

### 5.5. FKs e risco estrutural entre Tenants

O catálogo lista 924 FKs. Há 490 relações entre tabelas que possuem `tenant_id` direto; em 26 delas, a constraint composta inclui `tenant_id` dos dois lados. Nas outras 464, o FK não exige a igualdade dos Tenants. Mais 59 constraints ligam 42 tabelas sem `tenant_id` direto a pais com a coluna; quatro dessas tabelas filhas têm policies relacionais `EXISTS` e FORCE, enquanto 38 não têm RLS.

Isso confirma lacuna estrutural potencial, não inconsistência de dados demonstrada. Por exemplo, `cadastros_pessoas_pii` e `cadastros_pessoas_bancario` referenciam `cadastros_pessoas(id)` sem escopo Tenant na FK; `compras_itens_pedido` referencia `compras_pedidos(id)` e outros pais por ID. Queries/serviços podem aplicar filtro via pai, mas o banco não exige a relação tenant-aware nestas constraints. Há 48 das 464 relações apontando a pais `tenant_id` nullable, para as quais NULL pode representar catálogo global legítimo; classificar uma a uma antes de decidir constraint/policy. Não leram-se valores de negócio para detectar referências cruzadas existentes.

## 6. Dependências de API, workers e contexto SQLAlchemy

### 6.1. Consumidores por classe

| Classe/tarefa | Consumidores encontrados no código/01A/01B | Dependência de isolamento |
|---|---|---|
| API HTTP | Rotas e serviços usam `core.dependencies.get_session()` ou `core.database.get_db()`; dezenas de módulos usam caminho genérico. Catálogos de produtos, tipos de serviço e commodities são lidos em services específicos. | `get_session()` configura tenant quando resolvido pelo JWT/request; `get_db()` não injeta contexto. Cada endpoint precisa de classificação por rota e primeira query protegida. |
| Automations Worker | `automacoes/worker.py`: busca configurações agendadas via `get_db_session()`, depois executa serviço com `cfg.tenant_id`; varreduras de alertas são gerais. | Despacho global mínimo, execução por Tenant e transação; impedir que configuração de B invoque serviço com contexto A. |
| Background Worker | `core/background_jobs.py`: billing, alertas, ERP, recomendações, vencimentos/depreciação e sincronizações multi-tenant. | Enumerar alvos com escopo mínimo; cada unidade tenant-scoped executa em contexto separado. |
| Outbox Worker | `events/outbox_worker.py` usa `get_db_session()` e tem caminhos com `tenant_id=None`; `outbox_service.py` define contexto local em escrita tenant-scoped. | Claim/ack/retry precisa de projeto específico; não ler payload entre Tenants sem controle. |
| Schedulers de recomendação e ERP | Enumeração multi-tenant; implementam `set_config(..., false)` e helpers `RESET` em caminhos de scheduler. | Estado atual é de sessão, depende de limpeza em todos os caminhos. Preferir contexto transacional por tarefa; validar commits internos e erro/cancelamento. |
| Catálogos globais | Produtos, marcas, modelos, categorias, tipos de serviço e commodities consultam linhas globais e/ou próprias em fluxos documentados. | Leitura global somente nas referências aprovadas; mutação global requer autorização funcional de plataforma e privilégio administrativo estreito. |
| Tabelas sem `tenant_id` direto | Tabelas filhas de pessoas, compras, estoque e produto aparecem no 01A/01B; domínio e workers consomem as cadeias. | Confirmar FK física/raiz. Não classificar como global por ausência da coluna. |

Este mapa identifica classes de consumidor e fluxos conhecidos, mas **não prova exaustividade por tabela ou execução em produção**. A matriz do Anexo A do 01B retém a referência estática por tabela.

### 6.2. Como `app.current_tenant_id` é definido e limpo

A leitura estática do código no 01A e a rechecagem localizada mostram:

1. `TenantRLSMiddleware` em `main.py` extrai tenant de JWT e guarda em `request.state.rls_tenant_id`; não abre conexão nem instala variável no PostgreSQL.
2. `core.dependencies.get_session()` resolve tenant da request/JWT e `_activate_session_tenant()` usa `SET LOCAL app.current_tenant_id` antes de entregar a sessão em rotas que resolvem Tenant. A resolução de autorização valida associação/seleção; não se deve aceitar ID arbitrário do body/header como autoridade.
3. `SET LOCAL` vale somente na transação corrente e termina em commit/rollback. Se o fluxo inicia outra transação depois de commit/rollback, precisa definir contexto antes da próxima query protegida. O código documenta reativação após commit em caminhos específicos (`require_module`), mas não existe prova de consistência global em todo serviço.
4. `core.database.get_db()` e `get_db_session()` criam sessões sem tenant automático. São usados por endpoints, workers, scripts e schedulers; cada consumidor precisa estabelecer o escopo explicitamente ou demonstrar ser global/identidade/dispatch de privilégio mínimo.
5. Engine/pool por processo não define tenant em evento `connect`. `set_config(..., true)` é transacional; `set_config(..., false)` fica no escopo da sessão. Schedulers de recomendação e ERP implementam `RESET` e invalidam conexão em falha de limpeza, mas isso não certifica todos os retornos/erros/cancelamentos nem toda conexão usada.
6. Com a role física atual informada, mesmo contexto ausente ou corretamente definido não restaura a barreira RLS, pois `SUPERUSER` e `BYPASSRLS` a ignoram.

Validação necessária: uma conexão reutilizada A→B→sem contexto não pode herdar visibilidade anterior; cobrir commit, rollback, exceção e cancelamento, e todas as novas transações devem definir novamente Tenant antes de SQL protegido. Validar API e três workers com a role operacional em ambiente separado.

## 7. Evidências pendentes e limites restantes

**Fechado nesta atualização com o extrato `/tmp/deepfarms-rls-01c-metadados.txt`:** conjunto físico de 350 nomes já reconciliado nominalmente com 348 candidatas 01B; estados individuais de RLS/FORCE em paridade com contrato; 188 policies comparadas ao snapshot; owners/ACLs declaradas, roles/memberships, sequences, functions/views/default privileges; lista de 275 colunas tenant; e inventário das 924 FKs.

**Ainda pendente:**

- revisão/imagem implantada e timestamp exato da captura dos metadados; o arquivo não identifica commit ou digest;
- ACLs efetivas expandidas para cada role/objeto, `PUBLIC`, privilégios no database, grants herdados e `has_*_privilege`; o extrato mostra ACLs brutas NULL, não a expansão;
- sessões/conexões já abertas pela API e workers, roles assumidas, credenciais alternativas e configuração integral do Compose;
- comportamento das policies sob uma role operacional sem `SUPERUSER`, sem `BYPASSRLS` e não-owner;
- validação das transações/pool A→B→sem Tenant em sucesso, commit, rollback, erro e cancelamento nos quatro serviços;
- presença efetiva de referências cruzadas em dados (não consultados) e exaustão dos consumidores/queries por FK;
- semântica CRUD de todas as nullable, produtos globais e especificamente modelos fito/zoossanitários;
- decisão de política/constraint para 464 relações sem igualdade de Tenant, 38 filhas sem RLS, e os 8 IDs `varchar` sem FK para Tenant;
- validade/escopo da URL literal previamente apontada em `kill_idle_connections.py`, sem imprimir seu valor;
- grants mínimos por API e workers, incluindo database CONNECT, tabelas, 33 sequences e funções; manter scripts/deploy/manutenção fora do papel runtime.



Coleta futura somente por operador com acesso aprovado, sem executar neste relatório ou contra produção pelo Codex. Exemplos de metadados PostgreSQL read-only; usar transação `READ ONLY`, não selecionar linhas de negócio nem valores de credenciais:

```sql
BEGIN READ ONLY;
SELECT current_database(), current_schema(), current_user, session_user;
SELECT c.relname, pg_get_userbyid(c.relowner) AS owner,
       c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='farms' AND c.relkind IN ('r','p') ORDER BY c.relname;
SELECT table_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='farms' AND column_name='tenant_id' ORDER BY table_name;
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname='farms' ORDER BY tablename, policyname;
SELECT member.rolname AS member, granted.rolname AS granted_role,
       m.admin_option, m.inherit_option, m.set_option
FROM pg_auth_members m JOIN pg_roles member ON member.oid=m.member
JOIN pg_roles granted ON granted.oid=m.roleid ORDER BY 1,2;
COMMIT;
```

Para infraestrutura, consultar sem ambiente/segredos: `docker ps --format 'table {{.Names}}	{{.Image}}	{{.Status}}'` e `docker inspect --format` limitado a nome, imagem e labels Compose (`project`, `service`, `working_dir`, `config_files`). Não usar `env`, `printenv`, `docker inspect .Config.Env`, `docker compose config` sem mascaramento, nem imprimir `DATABASE_URL`. A identidade pode ser confirmada dentro de cada container por query controlada que mostre apenas `current_user`, `session_user`, DB/schema e flags públicas da role; a URL não deve ser serializada nem aparecer em traceback/log.

## 8. Plano mínimo de correção (não executar nesta fase)

| Etapa | Dependências e trabalho | Critério de aceite | Risco se avançar sem fechar |
|---|---|---|---|
| 1. Inventário de privilégios | Inventário nominal, owners, ACLs brutas, memberships, sequences, functions/views/default privileges, RLS/policies e FKs já coletados. Completar ACLs efetivas, grants database-level, versão implantada e conexões dos processos; desenhar crosswalk de consumo/grants por tabela. | Interseção 348, extras técnicos 2 e ORM-only 0 fechados; RLS/policies conciliados. ACLs efetivas e direitos necessários por serviço ainda documentados e revisados antes de conceder. | Escolher role insuficiente ou privilegiada e manter rotas de bypass não vistas. |
| 2. Definir role operacional | Projetar role de login operacional sem `SUPERUSER`, `BYPASSRLS`, ownership indevida nem memberships capazes de elevar privilégio; grants mínimos por API/worker; decidir estratégia separada de manutenção e CRUD de catálogo global. | Matriz de grants por serviço/tabela/comando aprovada; migrations/manutenção fora das credenciais persistentes; nenhum acesso global implícito não justificado. | Lockout funcional, privilégio herdado ou owner escapando de policies. |
| 3. Validar contexto | Auditar consumidores de `get_session`, `get_db`, `get_db_session`, SQL direto, commits, rollback e schedulers; decidir dispatch global mínimo e execução por Tenant nos três workers. | Contexto autenticado definido antes da primeira operação; cada transação nova reaplica contexto; sem estado de sessão residual em sucesso/erro/cancelamento. | Falha de isolamento por GUC ausente ou contexto de outro job no pool. |
| 4. Testes isolados | Ambiente separado de produção, Tenants sintéticos A/B, role restrita igual à pretendida. Testar SELECT/INSERT/UPDATE/DELETE, FK cruzada, NULL global, sem contexto, troca de contexto, workers e catálogos. | B não lê/altera A; A/B leem apenas globais permitidos; Tenant não muta global; admin funcional não alcança dados privados alheios; rollback e pool limpos. | Vazamento ou bloqueio silencioso de fluxos legítimos em produção. |
| 5. Implementar políticas gradualmente | Lotes por domínio/criticidade e comportamento comprovado; começar por dados privados; global/reference com regras específicas; proteger filhas com FK/escopo relacional; evitar regra única baseada em nullable. | Cada lote tem owner/grants, policy/expressões revisadas, migrations reversíveis, testes e telemetria; catálogos globais preservados. | Regressão em API/jobs, exposição de tabelas filhas ou bloqueio de seed/admin. |
| 6. Validação e rollback | Fazer ensaio completo no ambiente separado, backup/restore verificado e plano por migration; definir stop conditions e rollback operacional antes do cutover. | Verificação funcional/API/workers, isolamento, observabilidade e rollback exercitado; aprovação de mudança separada antes de produção. | Dano de disponibilidade ou impossibilidade de retornar ao estado funcional. |

Operações que requerem privilégios administrativos/manutenção e **não devem usar a role operacional persistente da API**: DDL e migrations, ownership, criação/alteração de roles, grants/policies, repair/backfill, manutenção de índices/estrutura, inspeção global de metadados restritos e gestão de catálogos globais fora do escopo funcional permitido. Despacho de jobs multi-tenant deve usar caminho mínimo separado; não justificar `BYPASSRLS` para conveniência. O papel `is_superuser` da aplicação é autorização de negócio e não pode ser equiparado a `rolsuper` PostgreSQL.

A relação de assinatura permanece inalterada: o assinante é o Tenant, que pode possuir múltiplas propriedades e usuários. Esta auditoria não propõe mudança de titularidade.

## 9. Critérios de GO/NO-GO para 01D

### Decisão nesta etapa

**GO para iniciar o planejamento documental da correção.** O inventário agora permite desenhar papéis/grants e priorizar policies/FKs com nomes e estados físicos reconciliados. Planejamento deve permanecer sem DDL/DML em produção.

**NO-GO para iniciar a implementação 01D, migrations, alterações de grants/policies ou cutover.** O P0 atual, a ausência de ACL efetiva mínima e a falta de teste com role operacional restrita permanecem bloqueadores.

### GO para implementação somente quando todos forem comprovados

- Reconciliação nominal e explicada das 350 tabelas físicas contra as 348 candidatas e revisão/imagem implantada identificada.
- Owners, ACLs, grants herdados, memberships, functions/views/sequences, FKs e conexões efetivas revisados.
- Role operacional desenhada sem superuser/BYPASSRLS, não proprietária de tabelas protegidas (ou FORCE e ownership justificados), com grants mínimos aprovados.
- Contexto transacional e limpeza validados em API, Outbox, Automations e Background Worker, inclusive commits, rollback, erro e cancelamento.
- Semântica e operações das 20 nullable e demais registros globais aprovadas; leitura global separada de escrita administrativa.
- As 188 policies reconciliadas com o snapshot e a semântica de NULL/global revisadas; comportamento de ausência de contexto, casts e permissões validado com role operacional restrita.
- Testes com Tenants sintéticos em ambiente separado passam para leitura/escrita, referências cruzadas, filas e catálogo global; nenhuma escrita de teste em produção.
- Migrations graduais, validação funcional, backup/restore e rollback aprovados e exercitados.

**NO-GO enquanto qualquer gate acima estiver aberto.** A coleta fechou reconciliação nominal, ownership declarado, memberships, FKs e paridade das 188 policies com o snapshot; permanecem abertos os privilégios efetivos, conexões/roles realmente usadas em cada processo, semântica de tabelas e relações, validação transacional com papel restrito e testes comportamentais. A role `deepfarms` configurada nos quatro serviços mantém o bloqueio P0. Não iniciar cutover de segurança, não declarar isolamento multi-tenant liberado e não iniciar a implementação 01D.

## Referências de reconciliação

- [01A — Auditoria de isolamento multi-tenant](DEEPFARMS-RLS-HOSTINGER-01A-AUDITORIA.md): contexto de Tenant, pools, workers, papéis e riscos.
- [01B — Plano de correção e matriz de isolamento](DEEPFARMS-RLS-HOSTINGER-01B-PLANO-CORRECAO.md): contrato estático e Anexo A por tabela (348 candidatas).
- `services/api/migrations/baseline_contract.py`: baseline RLS estática; não representa por si só o estado vivo da Hostinger.
- `/tmp/deepfarms-rls-01c-metadados.txt`: extrato sanitizado de catálogo, 1.883 linhas, fornecido pelo operador; sem linhas de negócio.
- `services/api/migrations/clean_install/env.py`, `migrations/clean_install/README.md`, `migrations/clean_install/versions/20261025_clean_install_v1.py`: finalidade dos dois objetos técnicos físicos adicionais.
- `services/api/migrations/versions/20260823_clima_inteligencia_integrity.py`, `services/api/pecuaria/climatico/service.py`, `services/api/pecuaria/climatico/router.py`: policies com NULL global e separação atual entre CRUD Tenant e backoffice de modelos zoossanitários.
- `services/api/core/dependencies.py`, `core/database.py`, `main.py`: ciclo de contexto e dependências SQLAlchemy.
- `services/api/automacoes/worker.py`, `core/background_jobs.py`, `events/outbox_worker.py`: consumidores workers identificados no código.
- `services/api/core/cadastros/produtos/{models.py,service.py,schemas.py}`, `core/cadastros/tipos_servico/service.py`, `core/cadastros/commodities/service.py`: catálogos e fluxo de registros globais.
- `services/api/scripts/kill_idle_connections.py`: referência anterior à URL literal; seu valor foi omitido e não foi validado.
