# SANKHYA-SYNC-04 - Auditoria do Vinculo entre Registros AgroSaaS e ERP Sankhya

Data: 2026-07-06

## Escopo

Auditoria exclusivamente documental e de codigo para verificar como o AgroSaaS mantem a associacao oficial entre seus registros e os registros equivalentes no ERP Sankhya.

Nao foram implementados codigo, migrations, endpoints, contratos, autenticacao ou mudancas na estrategia Gateway-first/sync.

## Fontes auditadas

### Integracao Sankhya oficial

- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/README.md`
- `services/api/migrations/versions/fase3_sankhya.py`
- `services/api/migrations/versions/20260704_sankhya_gateway_auth.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`

### Dominio oficial de integracoes

- `services/api/integracoes/models.py`
- `services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py`
- `services/api/migrations/versions/20260701_integrations_domain_03b_operations.py`

### Entidades AgroSaaS relacionadas

- `services/api/core/models/tenant.py`
- `services/api/core/models/unidade_produtiva.py`
- `services/api/core/cadastros/propriedades/propriedade_models.py`
- `services/api/core/cadastros/pessoas/models.py`
- `services/api/core/cadastros/produtos/models.py`
- `services/api/core/cadastros/commodities/models.py`
- `services/api/operacional/models/estoque.py`
- `services/api/financeiro/models/plano_conta.py`
- `services/api/financeiro/models/lancamento.py`
- `services/api/financeiro/models/despesa.py`
- `services/api/financeiro/models/receita.py`
- `services/api/financeiro/models/nota_fiscal.py`
- `services/api/financeiro/comercializacao/models.py`
- `services/api/financeiro/hedge/models.py`

### Documentacao de estrategia anterior

- `docs/implementation/reports/SANKHYA-SYNC-01-ESCOPO-PILOTO-CAFE.md`
- `docs/implementation/reports/SANKHYA-SYNC-02-MAPEAMENTO-OFICIAL.md`
- `docs/implementation/reports/SANKHYA-SYNC-03-ESTRATEGIA-SINCRONIZACAO-PILOTO.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-01-ADAPTER-OFICIAL.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-02-API-UX-OFICIAL-STATUS-JOBS-HEALTH.md`
- `docs/implementation/reports/SANKHYA-DOMAIN-03-OBSERVABILIDADE-CORRELACAO-HISTORICA.md`
- `docs/implementation/reports/SANKHYA-GOV-01-AUDITORIA-GOVERNANCA-INTEGRACAO-SANKHYA.md`
- `docs/implementation/reports/SANKHYA-GOV-02-CORRECAO-GOVERNADA-INTEGRACAO-SANKHYA.md`

## Resumo executivo

O AgroSaaS esta preparado para manter configuracao, credenciais, features, jobs, health, logs e historico operacional da integracao Sankhya em escopo de tenant.

Tambem existem tabelas provider-specific de staging/espelho para pessoas, produtos, NFe, lancamentos financeiros e tabelas auxiliares do Sankhya. Essas tabelas persistem identificadores externos como `sankhya_id`, `CODPARC`, `CODPROD`, `DESDOB` e `CHAVEACESSO`.

Porem, a auditoria nao encontrou uma associacao oficial e reutilizavel entre os registros oficiais do AgroSaaS e os registros do ERP Sankhya para a maior parte das entidades. Em termos praticos:

- existe persistencia de registros Sankhya em tabelas `sankhya_*`;
- existe idempotencia dentro dessas tabelas de staging;
- existe rastreabilidade de execucao via `sankhya_sync_logs` e `integration_jobs`;
- nao existe, de forma geral, um vinculo persistente do tipo `cadastros_pessoas.id <-> CODPARC`, `cadastros_produtos.id <-> CODPROD`, `estoque_depositos.id <-> CODLOCAL`, `fin_planos_conta.id <-> CODNAT/CODCENCUS` ou equivalente.

Conclusao objetiva: para o primeiro piloto read-only/manual-first, a base atual e suficiente para importar e auditar dados no staging Sankhya, mas ainda nao e suficiente para garantir, durante toda a vida util da integracao, a identidade unica entre um registro oficial AgroSaaS e seu equivalente no Sankhya em todos os dominios.

## Distincao critica encontrada

| Camada | Existe hoje | O que resolve | O que nao resolve |
| --- | --- | --- | --- |
| Provider-specific Sankhya | `sankhya_config`, `sankhya_pessoas`, `sankhya_produtos`, `sankhya_nfe`, `sankhya_lancamentos_financeiros`, `sankhya_tabelas` | Guarda dados e IDs vindos do Sankhya | Nao aponta para IDs oficiais de Pessoa, Produto, Deposito, PlanoConta, Despesa, Receita, etc. |
| Dominio oficial de Integracoes | `marketplace_integracoes`, `tenant_integracoes`, `integration_credentials`, `integration_versions`, `integration_features`, `integration_sync_policies`, `integration_jobs`, `integration_health_snapshots` | Governanca, credenciais, features, jobs, policies, health e versoes de configuracao | Nao e um registro de de-para por entidade de negocio |
| Cadastros oficiais AgroSaaS | `cadastros_pessoas`, `cadastros_produtos`, `estoque_depositos`, `fin_*`, `financeiro_comercializacoes`, etc. | Fonte oficial interna do produto | Nao armazena identificadores Sankhya oficiais de forma padronizada |

## Tabela por entidade

### Estrutura organizacional

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Tenant | `tenants.id` UUID, `tenants.documento` | Configuracao do tenant no Sankhya; possiveis `CODEMP`/ambiente nao modelados | `sankhya_config.tenant_id` e `tenant_integracoes.tenant_id` associam o tenant a configuracao da integracao, nao a uma empresa/filial Sankhya especifica | EXISTE PARCIALMENTE |
| Empresa | Nao ha entidade oficial dedicada | `CODEMP` | Nao encontrada | NAO EXISTE |
| Filial | Nao ha entidade oficial dedicada | `CODFILIAL` ou equivalente | Nao encontrada | NAO EXISTE |
| Unidade de Negocio | Nao ha entidade oficial dedicada | Codigo de unidade/centro empresarial do ERP | Nao encontrada | NAO EXISTE |
| Unidade Produtiva | `unidades_produtivas.id` UUID | Nao modelado; possivel relacao futura com empresa/filial/local | Nenhuma associacao Sankhya; testes confirmam Sankhya tenant-scoped e sem `unidade_produtiva_id` | NAO EXISTE |
| Propriedade | `cadastros_propriedades.id` UUID | Nao modelado | Nenhuma associacao Sankhya | NAO EXISTE |

### Pessoas

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Pessoa | `cadastros_pessoas.id` UUID, documentos em `cadastros_pessoas_documentos` | `CODPARC` | `sankhya_pessoas.sankhya_id` recebe `CODPARC`; nao ha FK para `cadastros_pessoas.id` | EXISTE PARCIALMENTE |
| Cliente | `Pessoa` + `PessoaRelacionamento`/`Receita.pessoa_id` | `CODPARC` + categoria/papel | Apenas no staging `sankhya_pessoas`; nao ha vinculo oficial para `Receita.pessoa_id` | EXISTE PARCIALMENTE |
| Fornecedor | `Pessoa` + `PessoaRelacionamento`/`Despesa.pessoa_id`; fornecedor legado em compras | `CODPARC` + categoria/papel | Apenas no staging `sankhya_pessoas`; nao ha vinculo oficial para `Despesa.pessoa_id` ou fornecedor legado | EXISTE PARCIALMENTE |
| Transportadora | `Pessoa` + papel configuravel | `CODPARC` | Apenas no staging se vier como categoria; nao ha papel oficial Sankhya persistido | EXISTE PARCIALMENTE |
| Representante | `Pessoa` + papel configuravel | `CODPARC` | Apenas no staging se vier como categoria; nao ha papel oficial Sankhya persistido | EXISTE PARCIALMENTE |

### Produtos

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Produto | `cadastros_produtos.id` UUID, `codigo_interno`, `sku`, `codigo_barras` | `CODPROD` | `sankhya_produtos.sankhya_id` e `codigo` recebem `CODPROD`; nao ha FK para `cadastros_produtos.id` | EXISTE PARCIALMENTE |
| Insumo | `Produto` tipo agricola/operacional + detalhes | `CODPROD` | Apenas no staging `sankhya_produtos`; nao ha classificacao de equivalencia com `ProdutoAgricola` | EXISTE PARCIALMENTE |
| Servico | `Produto` tipo `SERVICO` | `CODPROD` ou codigo de servico do ERP | Apenas no staging `sankhya_produtos`; sem vinculo com `Produto` tipo servico | EXISTE PARCIALMENTE |
| Unidade de medida | Enum/cadastros de unidade no AgroSaaS e campos `unidade_medida`/`unidade` | Unidade Sankhya | Campo textual em `sankhya_produtos.unidade`; sem tabela de equivalencia Sankhya <-> unidade oficial | EXISTE PARCIALMENTE |
| Conversao | Tabelas oficiais de medidas/conversoes ja existentes | Fator/unidade do Sankhya | Nao encontrada associacao direta Sankhya | NAO EXISTE |

### Estoque

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Deposito | `estoque_depositos.id` UUID | `CODLOCAL` ou local/deposito do Sankhya | Nao encontrada; `SankhyaCanonicalAdapter` declara feature `estoque` futura e desabilitada | NAO EXISTE |
| Local de estoque | `Deposito.localizacao_desc` e possiveis detalhes do produto | `CODLOCAL`/localizacao | Nao encontrada | NAO EXISTE |
| Lote | `estoque_lotes.id`, `numero_lote` | Lote/controle Sankhya | Nao encontrada associacao Sankhya; lote local usa `nota_fiscal_ref` e `metadata_json` genericos | NAO EXISTE |
| Saldo | `estoque_saldos.id`, `produto_id`, `deposito_id` | Saldo por `CODPROD` + `CODLOCAL` | Nao encontrada associacao ou snapshot Sankhya | NAO EXISTE |
| Movimento | `estoque_movimentos.id`, `origem`, `origem_id` | Movimento/documento do ERP | Nao encontrada associacao Sankhya | NAO EXISTE |

### Financeiro

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Plano de Contas | `fin_planos_conta.id`, `codigo` | Pode corresponder a `CODNAT`, conta contabil ou plano ERP | Nao encontrada associacao Sankhya | NAO EXISTE |
| Centro de Custo | Rateio e vinculos por safra/talhao/origem; sem master dedicado | `CODCENCUS` | Nao encontrada associacao Sankhya | NAO EXISTE |
| Natureza Financeira | Sem master dedicado; aproximacao por `PlanoConta`/categorias | `CODNAT` | Nao encontrada associacao Sankhya | NAO EXISTE |
| Contas a Pagar | `fin_despesas.id`; `pessoa_id`, `numero_nf`, `serie_nf`, `chave_nfe` | `DESDOB`, `NUMDOC`, `CODPARC` | `sankhya_lancamentos_financeiros.sankhya_id` recebe `DESDOB`; nao ha FK para `fin_despesas.id` | EXISTE PARCIALMENTE |
| Contas a Receber | `fin_receitas.id`; `pessoa_id`, `numero_nf`, `serie_nf`, `chave_nfe` | `DESDOB`, `NUMDOC`, `CODPARC` | `sankhya_lancamentos_financeiros.sankhya_id` recebe `DESDOB`; nao ha FK para `fin_receitas.id` | EXISTE PARCIALMENTE |
| Lancamento financeiro simplificado | `financeiro_lancamentos.id`, `origem`, `origem_id` | Nao padronizado | Nao encontrada associacao Sankhya | NAO EXISTE |

### Fiscal

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Nota Fiscal oficial | `fin_notas_fiscais.id`, `chave_acesso`, `numero`, `serie` | `CHAVEACESSO`, `NUMNOTA`, `SERIE`, possivel `NUNOTA`/`CODNEG` | `fin_notas_fiscais.chave_acesso` e `sankhya_nfe.chave_acesso` podem deduplicar por chave, mas nao ha FK entre elas | EXISTE PARCIALMENTE |
| NFe staging Sankhya | `sankhya_nfe.id` | `sankhya_id`, `CHAVEACESSO` | Tabela `sankhya_nfe` tem unique em `sankhya_id` e `chave_acesso` | EXISTE E ATENDE para staging |
| Serie | `serie` em NF/receita/despesa | `SERIE` | Campo textual, sem master de serie | EXISTE PARCIALMENTE |
| Numero | `numero`, `numero_nf`, `numero_documento` | `NUMNOTA`, `NUMDOC` | Campos textuais/numericos, sem associacao oficial | EXISTE PARCIALMENTE |
| Chave de acesso | `chave_acesso`, `chave_nfe`, `nf_chave` | `CHAVEACESSO` | Chave natural forte em NF e staging; dedupe por chave em `sankhya_nfe` | EXISTE E ATENDE para idempotencia fiscal |

### Comercializacao

| Entidade | Identificador no AgroSaaS | Identificador no Sankhya | Como a associacao e armazenada | Situacao |
| --- | --- | --- | --- | --- |
| Contrato de comercializacao | `financeiro_comercializacoes.id`, `numero_contrato` | Pedido/contrato/documento ERP nao definido | Nao encontrada associacao Sankhya | NAO EXISTE |
| Commodity | `cadastros_commodities.id`, `codigo` | Codigo de produto/commodity do ERP, se aplicavel | Nao encontrada associacao Sankhya | NAO EXISTE |
| Comercializacao | `ComercializacaoCommodity.id`, `comprador_id`, `commodity_id`, `nf_chave`, `receita_id` | Documento/pedido/contrato ERP | Nao encontrada associacao Sankhya | NAO EXISTE |
| Hedge/contrato futuro | `contratos_futuros_v2.id`, `codigo_contrato` | Nao definido no escopo Sankhya atual | Nao encontrada associacao Sankhya | NAO EXISTE |

## Identificadores utilizados

| Identificador | Onde aparece | Uso atual | Dependencias |
| --- | --- | --- | --- |
| `tenant_id` | `sankhya_config`, `sankhya_sync_logs`, `sankhya_*`, `tenant_integracoes`, `integration_*`, entidades oficiais | Escopo multi-tenant e RLS/logica de isolamento | Todos os fluxos Sankhya |
| `sankhya_config.id` | `sankhya_config`, `sankhya_sync_logs.config_id` | Configuracao provider-specific | Logs legados |
| `tenant_integracoes.id` | `tenant_integracoes`, `integration_features`, `integration_sync_policies`, `integration_jobs`, `integration_health_snapshots`, `integration_versions` | Configuracao oficial da integracao | Jobs, health, features, policies |
| `IntegrationJob.id` | `integration_jobs`, health e timeline | Execucao operacional de sync | Logs enriquecidos, timeline, health |
| `SankhyaSyncLog.id` | `sankhya_sync_logs`; causation deterministica no adapter | Log legado de sync | Jobs oficiais por `legacy_log_id` |
| `CODPARC` | `sync_service.py` em pessoas; `nfe_financeiro_service.py` em payloads de NFe/lancamento | Importacao de pessoas para `sankhya_pessoas.sankhya_id`; payload de exportacao | Pessoas, clientes, fornecedores, NFe, financeiro |
| `CODPROD` | `sync_service.py` em produtos | Importacao para `sankhya_produtos.sankhya_id` e `codigo` | Produtos/insumos/servicos |
| `CODNEG` | `nfe_financeiro_service.py` em NFe de entrada | Usado como `sankhya_nfe.sankhya_id` | NFe staging |
| `DESDOB` | `nfe_financeiro_service.py` em lancamentos | Usado como `sankhya_lancamentos_financeiros.sankhya_id`; tambem enviado no payload | Financeiro staging |
| `NUMDOC` | `nfe_financeiro_service.py` em lancamentos | Usado como `numero_documento` no staging | Financeiro |
| `NUMNOTA` | `nfe_financeiro_service.py` em NFe | Usado como `numero` ou payload de exportacao | Fiscal |
| `SERIE` | `nfe_financeiro_service.py`, models fiscais | Usado como campo textual | Fiscal |
| `CHAVEACESSO` | `nfe_financeiro_service.py`, `sankhya_nfe.chave_acesso`, `fin_notas_fiscais.chave_acesso` | Dedupe fiscal e identificacao natural da NF-e | Fiscal, contas a pagar/receber por chave NFe |
| `CODEMP` | Documentado em relatorios anteriores, nao modelado no codigo Sankhya auditado | Nao utilizado | Empresa/filial pendente |
| `CODFILIAL` | Solicitado no escopo, nao encontrado no codigo auditado | Nao utilizado | Filial pendente |
| `CODLOCAL` | Documentado como necessidade futura, nao encontrado em model/service ativo | Nao utilizado | Depositos/estoque pendente |
| `CODNAT` | Solicitado/documentado como natureza financeira, nao encontrado em model/service ativo | Nao utilizado | Natureza/plano financeiro pendente |
| `CODCENCUS` | Solicitado/documentado como centro de custo, nao encontrado em model/service ativo | Nao utilizado | Centro de custo pendente |

## Atualizacao de registros

| Entidade | Como identifica existencia hoje | Quando atualiza | Quando cria novo | Como evita duplicidade | Se o ID Sankhya mudar |
| --- | --- | --- | --- | --- | --- |
| Configuracao Sankhya | `sankhya_config.tenant_id` unico | `atualizar_config` no mesmo tenant | `criar_config` quando nao existe | Unique em `tenant_id`; config oficial em `tenant_integracoes` por tenant/provider | Mantem configuracao por tenant; nao trata alteracao de empresa/filial porque esses IDs nao existem |
| Pessoas staging | Busca `SankhyaPessoa.sankhya_id == CODPARC` | Sobrescreve dados do staging | Insere novo `sankhya_pessoas` | Unique global em `sankhya_id` | Se `CODPARC` mudar, tende a criar outro staging; nao ha reconciliacao por documento + pessoa oficial |
| Produtos staging | Busca `SankhyaProduto.sankhya_id == CODPROD` | Sobrescreve dados do staging | Insere novo `sankhya_produtos` | Unique global em `sankhya_id` | Se `CODPROD` mudar, tende a criar outro staging; nao ha reconciliacao com produto oficial |
| NFe staging | Busca `SankhyaNFe.chave_acesso` | Atualiza staging existente | Insere nova `sankhya_nfe` | Unique em `chave_acesso` e `sankhya_id` | Se ID Sankhya mudar mas chave permanecer, a chave segura a identidade fiscal; se chave ausente, risco aumenta |
| Financeiro staging | Busca `SankhyaLancamentoFinanceiro.sankhya_id == DESDOB` | Atualiza staging existente | Insere novo staging | Unique global em `sankhya_id` | Se `DESDOB` mudar, tende a duplicar; nao ha chave composta `CODPARC + NUMDOC + DESDOB + tenant` persistida |
| Cadastros oficiais | Nao ha upsert Sankhya -> oficial auditado | Nao aplicavel | Nao aplicavel | Nao aplicavel | Nao ha trilha oficial para resolver mudanca de ID externo |

Observacao: os upserts de staging usam `sankhya_id` sem filtro por `tenant_id` nas buscas de pessoas/produtos/financeiro e as migrations criam unique global em `sankhya_id`. Isso e aceitavel apenas se os codigos Sankhya forem globalmente unicos na instalacao. Em ambiente SaaS multi-tenant, o desenho mais seguro normalmente seria unicidade composta por tenant/provider/identificador externo.

## Origem oficial da informacao

| Entidade | Origem aprovada para o piloto | Situacao encontrada |
| --- | --- | --- |
| Clientes, fornecedores, transportadoras, representantes | Sankhya | Alinhado como staging; falta vinculo duradouro com `Pessoa` |
| Produtos, insumos, servicos | Sankhya | Alinhado como staging; falta vinculo duradouro com `Produto` |
| Plano de contas | Sankhya, conforme SANKHYA-SYNC-02 | Falta associacao com `PlanoConta` |
| Contas a pagar/receber | Sankhya | Alinhado como staging; falta associacao com `Despesa`/`Receita` |
| Notas fiscais | Sankhya | Parcialmente alinhado; `chave_acesso` permite identidade fiscal forte |
| Depositos | Sankhya para deposito, AgroSaaS para saldo/lote/movimento segundo mapeamento anterior | Falta associacao com `Deposito` e falta consumo de `CODLOCAL` |
| Unidade de medida/conversao | AgroSaaS | Alinhado; falta de-para para unidade textual Sankhya |
| Talhoes, areas, safras, operacao agricola | AgroSaaS | Alinhado; fora do sync Sankhya atual |
| Commodities e contratos de comercializacao | AgroSaaS | Alinhado para piloto; sem vinculo Sankhya |
| Empresa, filial, unidade de negocio | Pendente de definicao | Nao modelado |

## Rastreabilidade

### Perguntas respondidas hoje

| Pergunta | Resposta atual |
| --- | --- |
| Qual tenant possui integracao Sankhya configurada? | Sim, por `sankhya_config.tenant_id` e `tenant_integracoes.tenant_id`. |
| Quando ocorreu a ultima sincronizacao? | Sim, por `sankhya_config.ultimo_sync`, `sankhya_sync_logs.completed_at` e `integration_jobs.finished_at`. |
| Por qual rotina foi sincronizado? | Sim, por `sankhya_sync_logs.tipo/operacao` e `IntegrationFeature.codigo`/`IntegrationJob.trigger_type`. |
| A sincronizacao falhou ou teve sucesso? | Sim, por `sankhya_sync_logs.status`, `integration_jobs.status` e `integration_health_snapshots.status`. |
| Qual registro Sankhya de pessoa/produto/NFe/lancamento foi importado para staging? | Sim, nas tabelas `sankhya_*`. |

### Perguntas nao respondidas de forma confiavel hoje

| Pergunta | Lacuna |
| --- | --- |
| Qual `cadastros_pessoas.id` corresponde ao `CODPARC`? | Nao ha FK, tabela de de-para ou campo externo na entidade oficial. |
| Qual `cadastros_produtos.id` corresponde ao `CODPROD`? | Nao ha FK, tabela de de-para ou campo externo na entidade oficial. |
| Qual `estoque_depositos.id` corresponde ao `CODLOCAL`? | `CODLOCAL` nao esta persistido. |
| Qual `fin_planos_conta.id` corresponde a `CODNAT` ou plano/natureza Sankhya? | Nao ha mapeamento persistido. |
| Qual centro de custo AgroSaaS corresponde a `CODCENCUS`? | Nao ha master de centro de custo nem mapeamento. |
| Qual `fin_despesas.id` ou `fin_receitas.id` corresponde a um titulo Sankhya? | Apenas existe staging financeiro; nao ha FK para despesa/receita. |
| Qual `fin_notas_fiscais.id` corresponde a `sankhya_nfe.id`? | Pode ser inferido por `chave_acesso`, mas nao ha associacao persistida. |
| Qual empresa/filial Sankhya esta associada ao tenant? | Nao ha `CODEMP`/`CODFILIAL` no modelo atual. |

## Riscos identificados

1. **Vinculo registro-a-registro nao oficializado**: a maior parte dos dominios tem staging Sankhya, mas nao tem associacao persistida com os cadastros oficiais.
2. **Unicidade global de IDs Sankhya**: `sankhya_id` e `chave_acesso` aparecem como unique global nas migrations/tabelas de staging, nao compostos por `tenant_id`. Isso pode bloquear ou misturar tenants caso dois ambientes Sankhya usem o mesmo codigo numerico.
3. **Risco de duplicidade ao promover staging para oficial**: sem de-para persistido, imports futuros podem criar nova `Pessoa`/`Produto` quando o registro ja existir por documento, nome ou codigo interno.
4. **Mudanca de codigo no Sankhya**: se `CODPARC`, `CODPROD` ou `DESDOB` mudar, o sistema tende a tratar como novo registro no staging.
5. **Fiscal parcialmente mitigado por chave de acesso**: NF-e e a area mais segura porque `CHAVEACESSO` e uma chave natural forte. Ainda assim, falta FK entre staging e `fin_notas_fiscais`.
6. **Empresa/filial ausentes**: nao ha como responder formalmente qual `CODEMP`/`CODFILIAL` esta associado ao tenant, empresa, propriedade ou unidade produtiva.
7. **Centro de custo e natureza financeira sem master equivalente**: `CODCENCUS` e `CODNAT` nao tem destino oficial persistido.
8. **Deposito/local de estoque sem de-para**: `CODLOCAL` nao esta armazenado e a feature `estoque` esta preparada como futura, mas desabilitada.
9. **Rastreabilidade operacional nao substitui rastreabilidade de entidade**: `IntegrationJob`, `IntegrationHealth` e `SankhyaSyncLog` dizem quando e como a sync rodou, mas nao qual registro oficial foi vinculado.
10. **Reprocessamento limitado**: para pessoas/produtos, o full refresh por `findAll` atualiza staging, mas nao resolve reconciliacao com oficiais nem divergencias de identidade.

## Associacoes totalmente implementadas

| Associacao | Evidencia | Observacao |
| --- | --- | --- |
| Tenant AgroSaaS -> configuracao Sankhya | `sankhya_config.tenant_id`; `tenant_integracoes.tenant_id` | Atende configuracao da integracao por tenant. |
| Configuracao Sankhya -> credencial/versionamento oficial | `integration_credentials`, `integration_versions` via `SankhyaCanonicalAdapter` | Atende governanca de credenciais e auditoria de configuracao. |
| Sync legado -> job oficial | `sankhya_sync_logs` + `integration_jobs` com `legacy_log_id`/causation deterministica | Atende rastreabilidade operacional. |
| Registro NFe staging -> NFe externa por chave de acesso | `sankhya_nfe.chave_acesso` unique e upsert por `CHAVEACESSO` | Atende idempotencia fiscal no staging; nao e FK oficial. |

## Associacoes parcialmente implementadas

| Associacao | Onde existe | Lacuna |
| --- | --- | --- |
| Pessoa/cliente/fornecedor/transportadora/representante -> Sankhya | `sankhya_pessoas.sankhya_id = CODPARC` | Falta vinculo com `cadastros_pessoas.id` e papel oficial. |
| Produto/insumo/servico -> Sankhya | `sankhya_produtos.sankhya_id = CODPROD` | Falta vinculo com `cadastros_produtos.id` e unidade oficial. |
| NFe AgroSaaS -> NFe Sankhya | `chave_acesso` nos dois lados | Associacao e inferivel por chave, nao persistida como relacao oficial. |
| Contas a pagar/receber -> Sankhya | `sankhya_lancamentos_financeiros.sankhya_id = DESDOB` | Falta vinculo com `fin_despesas.id`/`fin_receitas.id`; chave externa parece fraca isoladamente. |
| Tenant -> provider/health/jobs/features | Dominio oficial de Integracoes | Cobre integracao, nao registros de negocio. |

## Associacoes inexistentes

- Empresa Sankhya (`CODEMP`) -> Tenant/Empresa/Propriedade/UP AgroSaaS.
- Filial Sankhya (`CODFILIAL`) -> Tenant/UP/Propriedade AgroSaaS.
- Unidade de negocio Sankhya -> Unidade Produtiva ou contexto operacional.
- Deposito/local Sankhya (`CODLOCAL`) -> `estoque_depositos.id`.
- Lote/saldo/movimento de estoque Sankhya -> `estoque_lotes`, `estoque_saldos`, `estoque_movimentos`.
- Plano/natureza Sankhya (`CODNAT`) -> `fin_planos_conta.id`.
- Centro de custo Sankhya (`CODCENCUS`) -> centro/rateio AgroSaaS.
- Titulo Sankhya -> `fin_despesas.id`/`fin_receitas.id`.
- Contrato/pedido Sankhya -> `financeiro_comercializacoes.id`.
- Commodity/produto comercial Sankhya -> `cadastros_commodities.id`.

## Recomendacoes

### Reusar arquitetura existente primeiro

1. Manter `SankhyaConfig`, `SankhyaSyncLog` e `SankhyaCanonicalAdapter` como base operacional. Eles ja resolvem configuracao, health, jobs, timeline e auditoria de execucao.
2. Reusar `IntegrationJob`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth` e eventos oficiais para qualquer evolucao, sem criar scheduler/outbox paralelo.
3. Reusar as tabelas `sankhya_*` como staging/espelho de dados externos. Elas nao devem virar fonte oficial de Pessoas, Produtos, Financeiro ou Estoque.
4. Reusar chaves naturais existentes quando fortes, especialmente `CHAVEACESSO` para NF-e.

### Ajustes conceituais antes de nova implementacao

1. Definir uma politica oficial de identidade externa por entidade antes de promover dados Sankhya para cadastros oficiais.
2. Definir se a associacao deve viver em campos especificos nos oficiais, em uma tabela generica de de-para por provider, ou em extensoes por dominio. A auditoria nao encontrou uma estrutura atual que resolva isso de forma transversal.
3. Garantir que qualquer chave externa seja escopada por `tenant_id` e provider/ambiente. Evitar unicidade global simples para codigos como `CODPARC`, `CODPROD`, `DESDOB`, `CODLOCAL`, `CODNAT` e `CODCENCUS`.
4. Para pessoas, usar uma estrategia composta: `tenant_id + provider + CODPARC` como identidade externa primaria, com documento normalizado e papel como reconciliacao secundaria.
5. Para produtos, usar `tenant_id + provider + CODPROD`, com `codigo_interno`/`sku`/`codigo_barras` e unidade como reconciliacao secundaria.
6. Para financeiro, nao usar `DESDOB` isolado como identidade duradoura. Preferir uma chave composta com os campos reais do Sankhya validados no piloto, como `CODPARC + NUMDOC + DESDOB + vencimento + valor` ou identificador nativo se disponivel.
7. Para estoque, validar semanticamente `CODLOCAL` com o usuario do ERP antes de associar automaticamente a `Deposito`.
8. Para empresa/filial, confirmar se o piloto e realmente monoempresa/monofilial. Se for, documentar esse pressuposto operacional; se nao for, a associacao CODEMP/CODFILIAL vira bloqueador.

### Quando considerar nova estrutura

Somente recomendar nova estrutura apos confirmar que os mecanismos atuais nao atendem. A conclusao desta auditoria e que os mecanismos atuais atendem integracao operacional, mas nao atendem vinculo registro-a-registro. Portanto, se a proxima etapa exigir promover/importar dados para os cadastros oficiais com garantia de identidade, sera necessario introduzir uma forma persistente de de-para por provider ou extensoes equivalentes nos dominios.

## Impacto para o primeiro piloto

### O que esta seguro para o piloto inicial

- Configurar e testar conexao Sankhya por tenant.
- Executar sincronizacao manual de staging para pessoas, produtos, NFe e financeiro.
- Auditar status, jobs, logs, timeline e health da integracao.
- Usar `CHAVEACESSO` para evitar duplicidade fiscal em NFe.
- Operar em modo `manual first`, `tenant scoped`, `read-only`/pull controlado, conforme SANKHYA-SYNC-03.

### O que exige cuidado no piloto

- Nao assumir que uma pessoa importada em `sankhya_pessoas` ja corresponde a uma `Pessoa` oficial.
- Nao assumir que um produto importado em `sankhya_produtos` ja corresponde a um `Produto` oficial.
- Nao importar estoque/deposito como oficial sem validar `CODLOCAL` e sem definir associacao.
- Nao conciliar financeiro em `Despesa`/`Receita` apenas por `DESDOB`.
- Nao tratar `sankhya_id` global como seguro para multiplos tenants sem validar unicidade real entre ambientes Sankhya.

### Go/no-go objetivo

| Criterio | Resultado |
| --- | --- |
| Piloto de conexao, observabilidade e staging Sankhya | GO |
| Piloto read-only com cargas controladas e validacao manual | GO com restricoes |
| Promocao automatica para cadastros oficiais com garantia de identidade | NO-GO ate existir de-para oficial |
| Sync bidirecional ou escrita AgroSaaS -> Sankhya | NO-GO para esta fase |
| Multiempresa/multifilial Sankhya | NO-GO ate modelar/registrar `CODEMP`/`CODFILIAL` |

## Conclusao

O AgroSaaS esta parcialmente preparado para manter associacoes Sankhya durante o primeiro piloto: a infraestrutura de integracao, autenticacao, configuracao, health, jobs, logs e staging esta implementada e e reutilizavel.

O AgroSaaS ainda nao esta plenamente preparado para manter, durante toda a vida util da integracao, a associacao oficial entre cada registro oficial AgroSaaS e seu equivalente no ERP Sankhya. A lacuna principal nao e de Gateway, scheduler ou observabilidade; e de identidade externa persistente por entidade de negocio.

Para o piloto, a recomendacao e manter o recorte aprovado: leitura controlada, staging, validacao manual, sem escrita bidirecional e sem promocao automatica irreversivel para os cadastros oficiais enquanto nao houver politica oficial de de-para.

## Validacao

Executar ao final:

```bash
git diff --check
```
