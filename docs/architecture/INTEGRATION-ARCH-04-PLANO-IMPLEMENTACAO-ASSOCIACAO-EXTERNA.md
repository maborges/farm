# INTEGRATION-ARCH-04 - Plano de Implementacao da Associacao Oficial com Sistemas Externos

Data: 2026-07-06

## 1. Objetivo

Definir o plano tecnico de implementacao da Associacao Oficial com Sistemas Externos no AgroSaaS.

Este documento transforma a decisao arquitetural de `INTEGRATION-ARCH-03` em uma sequencia segura de implementacao futura, priorizando o P0 necessario ao piloto Sankhya, sem acoplar a solucao ao Sankhya.

Este documento nao implementa codigo, nao cria migrations, nao altera contratos, nao altera endpoints, nao altera autenticacao Gateway-first e nao altera o sync atual.

## 2. Fontes auditadas

### Documentos

- `docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md`
- `docs/implementation/reports/SANKHYA-SYNC-04-AUDITORIA-VINCULO-REGISTROS-AGROSAAS-SANKHYA.md`
- `docs/implementation/reports/INTEGRATION-DOMAIN-01-AUDITORIA-ENTIDADES-INTEGRACAO.md`
- `docs/architecture/INTEGRATIONS-ARCH-01.md`
- `docs/architecture/INTEGRATIONS-ARCH-02.md`
- `docs/implementation/reports/INTEGRATIONS-DOMAIN-02-ESPECIFICACAO-MATERIALIZACAO.md`
- `docs/architecture/agrosaas-master-context.md`
- `docs/architecture/agrosaas-ai-rules.md`

### Codigo e artefatos tecnicos

- `services/api/integracoes/models.py`
- `services/api/integracoes/events.py`
- `services/api/integracoes/security.py`
- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py`
- `services/api/migrations/versions/20260701_integrations_domain_03b_operations.py`
- `services/api/migrations/versions/fase3_sankhya.py`
- `services/api/migrations/versions/20260704_sankhya_gateway_auth.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`
- `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## 3. Estruturas reaproveitaveis

| Estrutura atual | Papel atual | Reuso no plano |
| --- | --- | --- |
| `MarketplaceIntegracao` | Catalogo de providers | Referencia ao sistema externo, como Sankhya, TOTVS, SAP, Omie, banco ou fiscal. |
| `TenantIntegracao` | Configuracao da integracao por tenant/escopo | Referencia a conexao real usada pela associacao. |
| `IntegrationCredential` | Segredos criptografados e versionados | Nao deve ser lida pela associacao; apenas mantem a governanca da conexao. |
| `IntegrationVersion` | Snapshot versionado de configuracao | Ajuda a auditar qual configuracao estava vigente. |
| `IntegrationFeature` | Feature habilitada por configuracao | Permite vincular associacoes a dominios como pessoas, produtos, financeiro e NFe. |
| `IntegrationSyncPolicy` | Politica operacional por feature | Reaproveitada para deduplicacao, batch e modo de sync. |
| `IntegrationJob` | Execucao operacional de sync | Deve ser referenciado no historico da associacao. |
| `IntegrationHealth` | Health da integracao | Pode sinalizar conflitos e degradacao futura por associacoes pendentes. |
| `integracoes.events` | Eventos de integracao | Pode receber eventos futuros de associacao criada, conflito ou substituicao, se comprovada necessidade. |
| `sankhya_*` | Staging/espelho tecnico do Sankhya | Continua existindo; nao deve ser fonte oficial do vinculo local-externo. |

Conclusao da auditoria: nao foi encontrada estrutura generica existente para associacao oficial de registros externos. O dominio de Integracoes oferece a base de provider, configuracao, tenant, feature, job, health e credencial, mas falta o componente de vinculo registro-a-registro.

## 4. Modelo de dados planejado

### 4.1 Tabela principal planejada

Planejar uma estrutura transversal, por exemplo `integration_external_record_links`.

Campos planejados:

| Campo conceitual | Tipo esperado | Observacao |
| --- | --- | --- |
| `id` | UUID | Identificador interno da associacao. |
| `tenant_id` | string/UUID conforme padrao atual | Obrigatorio e protegido por RLS. |
| `provider_id` | FK para `marketplace_integracoes` | Sistema externo. |
| `config_id` | FK para `tenant_integracoes` | Configuracao/conexao real. |
| `feature_id` | FK opcional para `integration_features` | Dominios como pessoas, produtos, financeiro, NFe. |
| `environment` | string | Producao, homologacao, sandbox ou ambiente provider-specific. |
| `scope_type` | enum/string | `TENANT` ou `ESTABELECIMENTO` para ERP. |
| `scope_id` | string nullable | Estabelecimento quando aplicavel. |
| `external_company_id` | string nullable | `CODEMP` ou equivalente. |
| `external_branch_id` | string nullable | `CODFILIAL` ou equivalente. |
| `local_entity` | string | Ex.: `Pessoa`, `Produto`, `Despesa`, `Receita`, `NotaFiscal`. |
| `local_record_id` | string/UUID | ID do registro local. |
| `external_entity` | string | Ex.: `Parceiro`, `Produto`, `Titulo`, `NFe`, `Natureza`. |
| `external_record_id` | string | Identificador externo principal, como `CODPARC` ou `CODPROD`. |
| `secondary_keys` | JSONB | Chaves auxiliares: documento, chave de acesso, numero, serie, valor, vencimento. |
| `status` | enum/string | `ACTIVE`, `PENDING`, `CONFLICT`, `SUPERSEDED`, `INACTIVE`. |
| `origin` | enum/string | `IMPORT`, `EXPORT`, `MANUAL_RECONCILIATION`, `MIGRATION`, `SYNC_JOB`. |
| `confidence` | enum/string | `HIGH`, `MEDIUM`, `LOW`, `MANUAL_CONFIRMED`. |
| `last_sync_at` | datetime | Ultima vez em que a associacao foi usada/validada. |
| `last_job_id` | FK opcional para `integration_jobs` | Execucao relacionada. |
| `notes` | text nullable | Observacoes de conciliacao. |
| `metadata_json` | JSONB nullable | Dados nao estruturais do provider. |
| `created_by_usuario_id` | string nullable | Usuario que confirmou/criou manualmente, quando existir. |
| `created_at` | datetime | Criacao. |
| `updated_at` | datetime | Ultima atualizacao. |
| `deleted_at` | datetime nullable | Soft delete quando necessario. |

### 4.2 Historico planejado

Planejar uma segunda estrutura, por exemplo `integration_external_record_link_history`.

Campos planejados:

| Campo conceitual | Finalidade |
| --- | --- |
| `id` | Identificador do evento historico. |
| `tenant_id` | Isolamento por tenant e RLS. |
| `link_id` | Associacao afetada. |
| `event_type` | `CREATED`, `UPDATED`, `CONFLICT_MARKED`, `SUPERSEDED`, `DEACTIVATED`, `REACTIVATED`, `RECONCILED`. |
| `previous_external_record_id` | Identificador externo anterior, se mudou. |
| `new_external_record_id` | Novo identificador externo, se mudou. |
| `previous_status` | Status anterior. |
| `new_status` | Novo status. |
| `job_id` | Job que causou a mudanca, quando aplicavel. |
| `actor_usuario_id` | Usuario responsavel, quando manual. |
| `reason` | Motivo da alteracao. |
| `details_payload` | Dados complementares do conflito/reconciliacao. |
| `created_at` | Momento do evento. |

### 4.3 Restricoes planejadas

As restricoes devem ser compostas e sempre incluir tenant, provider/configuracao e ambiente.

Planejar:

- unicidade ativa por registro externo: `tenant_id + config_id + environment + external_entity + external_record_id + external_company_id + external_branch_id`, considerando apenas associacoes ativas;
- unicidade ativa por registro local: `tenant_id + config_id + environment + local_entity + local_record_id + external_entity`, considerando apenas associacoes ativas;
- indice de busca local por `tenant_id + local_entity + local_record_id`;
- indice de busca externa por `tenant_id + provider_id + external_entity + external_record_id`;
- indice de pendencias por `tenant_id + status`;
- RLS obrigatorio nas duas tabelas.

Observacao: para financeiro, `external_record_id` pode ser uma chave calculada a partir de uma chave composta validada. Os componentes originais devem permanecer em `secondary_keys`.

## 5. Entidades P0 do piloto

| P0 | Associacao planejada | Identificador externo | Regras de deduplicacao |
| --- | --- | --- | --- |
| Pessoa / Parceiro | `Pessoa.id <-> Parceiro` | `CODPARC` | Validar tambem CPF/CNPJ, nome e papel. Nao criar segunda pessoa local para o mesmo `CODPARC` ativo no mesmo tenant/config/ambiente. |
| Produto / Insumo | `Produto.id <-> Produto ERP` | `CODPROD` | Validar unidade, SKU/codigo interno, codigo de barras e descricao. |
| Plano de Contas / Natureza | `PlanoConta.id <-> Natureza` | `CODNAT` ou equivalente | Nao assumir que plano contabil e natureza financeira sao a mesma coisa sem regra do tenant. |
| Conta a Pagar | `Despesa.id <-> Titulo ERP` | chave financeira composta ou ID nativo | Nao usar `DESDOB` isolado; incluir `CODPARC`, `NUMDOC`, vencimento, valor, empresa/filial. |
| Conta a Receber | `Receita.id <-> Titulo ERP` | chave financeira composta ou ID nativo | Mesma regra de contas a pagar, com tipo de titulo no contexto. |
| NFe / Documento Fiscal | `NotaFiscal.id <-> Documento/NFe` | `CHAVEACESSO`, `NUNOTA`, `NUMNOTA`, `SERIE` | `CHAVEACESSO` como chave forte; `NUNOTA`/ID ERP como complemento. |
| Empresa / Filial | `Tenant/Estabelecimento <-> Empresa/Filial ERP` | `CODEMP`, `CODFILIAL` | P0 se piloto tiver mais de uma empresa/filial ou se documentos exigirem empresa. |
| Unidade de Medida | Unidade local <-> Unidade ERP | sigla/codigo da unidade | Validar conversao antes de usar em documento ou estoque. |

## 6. Entidades P1

| P1 | Associacao planejada | Observacao |
| --- | --- | --- |
| Deposito / Local de Estoque | `Deposito.id <-> CODLOCAL` | Depende de validar se `CODLOCAL` representa deposito, armazem, local fiscal ou localizacao interna. |
| Conta Corrente | `ContaBancaria.id <-> Conta Corrente ERP` | Necessaria para baixas, conciliacao e remessas. |
| Centro de Resultado | centro local/futuro <-> centro ERP | Nao confundir com safra, talhao ou unidade produtiva. |
| Centro de Custo | centro/rateio local <-> `CODCENCUS` | Necessario se titulos/documentos exigirem centro. |
| Tipo de Operacao | regra/cenario <-> tipo ERP | Deve ser regra de roteamento por cenario, nao apenas associacao simples. |
| Banco | banco local <-> banco ERP | Apoia conta corrente e cobranca. |
| Agencia | agencia local <-> agencia ERP | Apoia conta corrente e conciliacao. |
| Carteira | carteira local <-> carteira ERP | Apoia cobranca e recebiveis. |

## 7. Entidades P2

| P2 | Observacao |
| --- | --- |
| Pedido | Necessario para compra/venda bidirecional e faturamento. |
| Contrato | Necessario para contratos comerciais ou documentos base. |
| Comercializacao | Necessario para integrar comercializacao de commodities. |
| Barter | Exige modelagem especifica de operacao composta. |
| Equipamento | Futuro para ativo, manutencao e custos. |
| Colaborador | Futuro para RH, prestadores e apontamentos. |
| RH | Futuro para equipes, OS e apontamentos. |
| Frota | Futuro para abastecimento, manutencao e telemetria. |

## 8. Servicos planejados

Planejar um service transversal, por exemplo `ExternalRecordAssociationService`, no dominio `integracoes`.

Operacoes esperadas:

| Operacao | Responsabilidade |
| --- | --- |
| `create_association` | Criar associacao apos validar tenant, config, provider, ambiente e duplicidade. |
| `update_association` | Atualizar metadados, status, confianca ou chaves secundarias sem trocar identidade indevidamente. |
| `find_local_by_external` | Localizar registro local a partir de provider, ambiente, entidade externa e identificador externo. |
| `find_external_by_local` | Localizar identificador externo a partir de entidade local e ID local. |
| `mark_conflict` | Marcar conflito quando um externo aponta para dois locais ou um local aponta para dois externos ativos. |
| `replace_association` | Substituir associacao ativa por outra, preservando historico e marcando anterior como `SUPERSEDED`. |
| `deactivate_association` | Desativar associacao sem apagar historico. |
| `record_history` | Registrar evento historico para toda mudanca relevante. |
| `validate_duplicate` | Validar unicidade composta por tenant, config, ambiente, empresa, filial e entidades. |
| `reconcile_pending` | Confirmar ou rejeitar associacoes pendentes, com usuario e motivo. |

Regras de design:

- todas as consultas devem receber `tenant_id` explicitamente ou operar sob sessao com RLS ativo;
- nenhum metodo deve buscar por `external_record_id` isolado;
- nenhuma regra Sankhya deve entrar no service transversal;
- regras Sankhya devem ficar em adapter/helper provider-specific que chama o service transversal.

## 9. Integracao planejada com Sankhya

O Sankhya deve consumir a nova capacidade como primeiro provider, sem ser dono do modelo.

| Fluxo Sankhya | Uso planejado da associacao oficial |
| --- | --- |
| Pessoas | Ao importar `sankhya_pessoas`, criar/atualizar associacao `Pessoa <-> Parceiro` usando `CODPARC`. |
| Produtos | Ao importar `sankhya_produtos`, criar/atualizar associacao `Produto <-> Produto ERP` usando `CODPROD`. |
| NFe | Ao importar `sankhya_nfe`, associar `NotaFiscal <-> Documento/NFe` por `CHAVEACESSO` e identificador nativo se existir. |
| Financeiro | Ao importar `sankhya_lancamentos_financeiros`, associar `Despesa` ou `Receita` por chave composta validada. |
| Empresa/Filial | Registrar `CODEMP` e `CODFILIAL` no contexto da associacao quando aplicavel. |
| Unidade de Medida | Criar de-para de unidade textual/codigo Sankhya para unidade local antes de documentos/estoque. |
| Natureza Financeira | Associar `CODNAT` ou equivalente a `PlanoConta`/natureza local definida. |

Regras importantes:

- `sankhya_*` continua sendo staging/espelho tecnico.
- A associacao oficial passa a ser a referencia para saber qual registro local corresponde ao registro externo.
- O adapter Sankhya deve procurar associacao existente antes de criar registro local.
- Se houver conflito, o fluxo deve registrar associacao pendente/conflitante, nao criar duplicata silenciosa.
- O sync Gateway-first permanece inalterado.

## 10. Protecao contra duplicidade

Regras obrigatorias no plano:

1. Duas pessoas locais nao podem ficar ativas para o mesmo `CODPARC` no mesmo tenant, config, ambiente, empresa e filial.
2. Dois produtos locais nao podem ficar ativos para o mesmo `CODPROD` no mesmo tenant, config, ambiente, empresa e filial.
3. Dois titulos financeiros nao podem ficar ativos para a mesma chave externa composta.
4. O mesmo codigo externo pode existir em tenants diferentes sem colisao.
5. O mesmo codigo externo pode existir em producao e homologacao sem colisao.
6. O mesmo codigo externo pode existir em empresas/filiais distintas se o ERP permitir essa semantica e a associacao carregar esse contexto.
7. `DESDOB` isolado nao deve ser chave duradoura.
8. `CHAVEACESSO` deve ser priorizada para NF-e, mas a associacao ainda deve registrar o ID local da nota.
9. Mudanca de identificador externo deve usar substituicao com historico, nao insert simples.

## 11. Historico e auditoria

O historico deve permitir responder:

- quem criou a associacao;
- quando criou;
- por qual sincronizacao ou job;
- qual identificador externo anterior;
- qual identificador externo novo;
- se houve conflito;
- se foi substituida;
- se foi desativada;
- qual usuario confirmou uma conciliacao manual;
- qual provider/configuracao/ambiente estava envolvido.

Eventos historicos minimos:

- `CREATED`
- `UPDATED`
- `CONFLICT_MARKED`
- `RECONCILED`
- `SUPERSEDED`
- `DEACTIVATED`
- `REACTIVATED`

## 12. Schemas planejados

Planejar schemas Pydantic apenas quando a implementacao iniciar:

| Schema | Uso |
| --- | --- |
| `ExternalRecordAssociationCreate` | Entrada interna/service para criar associacao. |
| `ExternalRecordAssociationUpdate` | Atualizacao de status, chaves secundarias, confianca e observacoes. |
| `ExternalRecordAssociationResponse` | Resposta para consulta operacional futura. |
| `ExternalRecordAssociationLookupRequest` | Busca local por externo ou externo por local. |
| `ExternalRecordAssociationConflictResponse` | Expor conflito/pendencia para reconciliacao. |
| `ExternalRecordAssociationHistoryResponse` | Listagem de historico. |

No P0, esses schemas podem ser usados apenas internamente por services e testes. Endpoints publicos devem ser planejados apenas depois que a necessidade operacional estiver confirmada.

## 13. Testes necessarios

### Testes unitarios do modelo

- enum/status de associacao permanece estavel;
- colunas obrigatorias existem;
- `tenant_id`, `provider_id`, `config_id`, `environment`, `local_entity`, `external_entity` e `external_record_id` sao obrigatorios;
- historico referencia associacao e tenant;
- RLS aparece na migration planejada;
- indices e constraints compostas existem na migration.

### Testes unitarios do service

- cria associacao ativa;
- rejeita duplicidade externa ativa no mesmo tenant/config/ambiente;
- rejeita duplicidade local ativa no mesmo tenant/config/ambiente;
- permite mesmo `CODPARC` em tenants diferentes;
- permite mesmo `CODPROD` em ambientes diferentes;
- busca local por identificador externo;
- busca externo por ID local;
- atualiza `last_sync_at` e `last_job_id`;
- marca conflito;
- substitui associacao e cria historico;
- desativa associacao sem apagar historico;
- reconcilia associacao pendente com usuario e motivo.

### Testes Sankhya P0

- pessoa usa `CODPARC` com tenant/config/ambiente;
- produto usa `CODPROD` com tenant/config/ambiente;
- NFe usa `CHAVEACESSO` como chave forte;
- financeiro usa chave composta, nao `DESDOB` isolado;
- empresa/filial entram no contexto quando presentes;
- unidade de medida nao e assumida como equivalente sem de-para;
- natureza financeira exige associacao com plano/natureza local;
- staging `sankhya_*` nao e tratado como associacao oficial.

### Testes de seguranca e isolamento

- nenhuma busca por identificador externo ignora tenant;
- nenhuma busca por identificador externo ignora ambiente;
- associacoes de homologacao nao aparecem em producao;
- associacoes de outro tenant nao sao retornadas;
- RLS protege tabelas de associacao e historico;
- testes existentes de guardrails de integracao continuam passando.

## 14. Sequencia de implementacao sugerida

### Fase 1 - Fundacao

Objetivo: criar a capacidade transversal sem integrar ainda ao Sankhya produtivo.

Entregas planejadas:

- models de associacao e historico;
- migration com RLS, indices e constraints compostas;
- enums/status/origem/confianca;
- schemas internos;
- service transversal;
- testes unitarios do modelo e service;
- documentacao curta de uso interno.

Criterio de aceite:

- criar, buscar, atualizar, marcar conflito, substituir e desativar associacoes com historico;
- isolamento por tenant validado em testes;
- sem dependencia de Sankhya no modelo transversal.

### Fase 2 - Sankhya P0

Objetivo: conectar o Sankhya ao service transversal para entidades do piloto.

Entregas planejadas:

- helper/adapter Sankhya para montar chaves externas;
- integracao de pessoas com `CODPARC`;
- integracao de produtos com `CODPROD`;
- integracao de NFe com `CHAVEACESSO`;
- integracao financeira com chave composta validada;
- associacao de unidade de medida;
- associacao de natureza/plano financeiro;
- tratamento condicional de `CODEMP`/`CODFILIAL`;
- testes unitarios por entidade P0.

Criterio de aceite:

- sync Sankhya consulta associacao oficial antes de criar/promover registro local;
- duplicidade vira conflito/pendencia;
- staging continua separado do vinculo oficial.

### Fase 3 - Observabilidade

Objetivo: tornar conflitos e pendencias auditaveis.

Entregas planejadas:

- logs estruturados de associacao criada, conflito e substituicao;
- historico consultavel por tenant/provider/entidade;
- relatorio interno de associacoes pendentes;
- possivel health degradado quando houver conflitos P0;
- possiveis eventos de dominio se houver necessidade de automacao.

Criterio de aceite:

- suporte consegue responder quais registros estao vinculados, pendentes ou conflitantes;
- cada conflito aponta para job, provider, ambiente e registros envolvidos.

### Fase 4 - P1

Objetivo: expandir para entidades que desbloqueiam financeiro avancado, estoque e operacao fiscal.

Entregas planejadas:

- deposito/local de estoque;
- conta corrente;
- centro de resultado;
- centro de custo;
- tipo de operacao como regra de roteamento;
- banco;
- agencia;
- carteira.

Criterio de aceite:

- documentos, baixas, conciliacao e estoque passam a usar associacoes oficiais, quando habilitados.

### Fase 5 - Pos-piloto

Objetivo: preparar bidirecionalidade e dominios futuros.

Entregas planejadas:

- documentos bidirecionais;
- pedidos;
- contratos;
- comercializacao;
- barter;
- frota;
- equipamentos;
- RH;
- colaboradores.

Criterio de aceite:

- novos providers podem usar a mesma capacidade sem criar colunas especificas por ERP.

## 15. Riscos e mitigacoes

| Risco | Impacto | Mitigacao planejada |
| --- | --- | --- |
| Criar solucao Sankhya-specific | Baixa reutilizacao para outros ERPs | Modelo transversal em `integracoes`, adapter Sankhya separado. |
| Ignorar tenant/RLS | Vazamento de dados | `tenant_id` obrigatorio, RLS e testes de isolamento. |
| Usar codigo externo isolado | Duplicidade ou colisao entre tenants/ambientes | Chaves compostas por tenant, config, ambiente, empresa e filial. |
| Misturar staging com associacao oficial | Rastreabilidade fraca | `sankhya_*` permanece espelho tecnico; associacao oficial em tabela transversal. |
| `DESDOB` mudar ou repetir | Duplicidade financeira | Chave composta validada; historico de substituicao. |
| Empresa/filial ausentes | Erro fiscal/financeiro em multiempresa | `CODEMP`/`CODFILIAL` no contexto e bloqueio para piloto multiempresa sem associacao. |
| Criar endpoints antes da operacao precisar | Superficie publica prematura | Comecar com service interno e testes; endpoints ficam para fase operacional. |
| Tipo de operacao tratado como cadastro simples | Documento errado no ERP | Modelar como regra de roteamento na fase P1/escrita. |

## 16. Decisao de escopo para o primeiro piloto

O primeiro piloto deve priorizar a associacao P0 apenas onde ela protege duplicidade ou rastreabilidade:

- pessoas/parceiros;
- produtos/insumos;
- NFe/documento fiscal;
- contas a pagar;
- contas a receber;
- unidade de medida;
- natureza/plano financeiro;
- empresa/filial se o cliente nao for monoempresa/monofilial.

Deposito, conta corrente, centro de resultado, centro de custo, tipo de operacao, banco, agencia e carteira ficam como P1, exceto se o fluxo real do piloto exigir escrita, baixa, conciliacao, estoque ou documento fiscal com esses campos obrigatorios.

## 17. Resultado esperado da implementacao futura

Ao final das fases planejadas, o AgroSaaS deve conseguir responder, de forma persistente e auditavel:

- qual registro local corresponde ao registro externo;
- qual identificador externo esta ativo;
- em qual tenant, provider, ambiente, empresa e filial a associacao vale;
- quando foi criada;
- por qual job foi criada ou atualizada;
- se houve conflito;
- se o identificador externo mudou;
- qual associacao foi substituida;
- quais associacoes estao pendentes de reconciliacao.

Essa capacidade deve virar um recurso de plataforma para qualquer sistema externo, com Sankhya apenas como primeiro caso de uso.
