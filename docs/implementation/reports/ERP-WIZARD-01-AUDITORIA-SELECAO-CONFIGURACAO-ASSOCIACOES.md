# Relatório de Auditoria — Seleção de ERP, Configuração e Associações

**Projeto**: ERP-WIZARD-01
**Tema**: Auditoria de reutilização, arquitetural e de implementação do domínio ERP
**Localização**: `docs/implementation/reports/ERP-WIZARD-01-AUDITORIA-SELECAO-CONFIGURACAO-ASSOCIACOES.md`

---

## 1. Resumo Executivo
Esta auditoria avalia a atual arquitetura de integração ERP do AgroSaaS (ERP-First), o fluxo do Wizard de implantação, a configuração de APIs externas e o ecossistema de associação de registros (`ExternalRecordAssociation`). O objetivo é mapear o que já está construído para garantir evolução sem código duplicado. Constatou-se que a infraestrutura canônica de integração (via `TenantIntegracao` e `MarketplaceIntegracao`) está madura e atende aos requisitos, embora algumas rotas delegadas (como o console ERP) ainda possuam resquícios *hardcoded* limitando a expansão para novos provedores. O Wizard atualmente utiliza JSONs *schemaless* para intenção de ERP, o que precisa evoluir para o uso do Marketplace.

---

## 2. Arquitetura Reutilizada
Toda a auditoria confirma que **nenhuma** nova tabela ou modelo de banco de dados precisará ser criado. O roadmap utilizará exclusivamente:
- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationCredential`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`
- `ExternalRecordAssociation`
- `ExternalRecordAssociationHistory`
- `ErpReadinessService`

---

## 3. Auditoria do Marketplace

O modelo `MarketplaceIntegracao` foi localizado em `integracoes/models.py`.

- **Quais integrações existem cadastradas?** O catálogo cadastra providers com diferentes `provider_type` (ex: "GENERIC", "ERP", etc).
- **Existe categoria ERP?** Sim, existe o campo `categoria` e o `provider_type`. O modelo permite filtrar por tipos específicos.
- **Existe provider_code?** Não como campo com este nome exato, mas existe `slug` que desempenha esse papel.
- **Existe provider_name?** Existe o campo `nome`.
- **Existe slug?** Sim, campo `slug` (String, unique).
- **Existe status?** Sim, campo `ativa` (Boolean).
- **Existe controle de disponibilidade?** Sim, via `ativa` e `oficial` (Boolean).
- **Existe ordenação?** Não existe uma coluna `ordem` explícita, mas a ordenação pode ser feita por `total_instalacoes` ou `avaliacao_media`.
- **Existe logotipo?** Sim, campos `fornecedor_logo` e `logo_url`.
- **Existe descrição?** Sim, `descricao` e `descricao_curta`.
- **Existe versionamento?** Sim, `versao`.
- **Existe capability?** Sim, gerida por meio de schemas JSON no provedor: `provider_definition`, `connection_schema`, `credential_schema`, `feature_schema`, `sync_schema` e `health_schema`.
- **O Marketplace já consegue fornecer uma lista de ERPs para o Wizard?** Sim. Basta uma consulta filtrando `provider_type == 'ERP'` e `ativa == True`. 

---

## 4. Auditoria do TenantIntegracao

Localizado em `integracoes/models.py`.

- **Como um tenant escolhe um ERP?** Através do instanciamento de um `TenantIntegracao`.
- **Quando TenantIntegracao é criado?** Na ativação ou configuração do aplicativo/integração no console/store.
- **Quem cria?** O usuário administrador/implantador do tenant ao iniciar a conexão de integração.
- **Quais estados possui?** Geridos por `IntegrationStatus` (`lifecycle_state`): `NOT_CONFIGURED`, `CONFIGURED`, `VALIDATING`, `VALID`, `ACTIVE`, `SYNCING`, `DEGRADED`, `SUSPENDED`, `REVOKED`, etc.
- **Quando deixa de existir?** Via *soft-delete* marcando `deleted_at` com a data/hora ou por meio da transição do status para `REMOVED`/`REVOKED`.
- **Como é vinculado ao Marketplace?** Via Foreign Key `integracao_id` referenciando `marketplace_integracoes.id`.

---

## 5. Auditoria das Credenciais

O modelo `IntegrationCredential` abriga os dados de acesso autenticados.

- **Como as credenciais são identificadas?** Via `tenant_id`, `provider_id` (FK), `scope_type`, `scope_id` e `version_number`.
- **Os campos auth_url, api_url, client_id, x-token são fixos ou dinâmicos?** São **dinâmicos**.
- **Onde são armazenados?** No campo `segredo_criptografado` (Text) de forma segura, com o layout guiado pelo `credential_schema` que reside na definição do `MarketplaceIntegracao`. 
- **Definidos por provider?** Sim. Cada provedor tem seu JSON Schema que dita o formato que a credencial precisa ter.

---

## 6. Auditoria das Capabilities (Features)

A entidade responsável é a `IntegrationFeature`.

- **Como o sistema sabe que o provider suporta NFe, financeiro, etc?** Através dos registros materializados de `IntegrationFeature`, que possuem o campo `codigo` (ex: "produtos", "pessoas", "financeiro", "nfe"). 
- **Existe cadastro?** Sim. Cada funcionalidade habilitada por um Tenant gera um registro na tabela vinculada ao `config_id` (`TenantIntegracao`).
- **Existe enum?** O núcleo do sistema conhece códigos padronizados (ex: na validação do `ErpReadinessService` existe um controle via array `_ERP_REQUIRED_FEATURE_CODES = ("pessoas", "produtos", "financeiro", "nfe")`).
- **Existe configuração dinâmica?** Sim, as capacidades e matriz de suporte (capability matrix) ficam no `feature_schema` (JSON) do `MarketplaceIntegracao`, permitindo que `settings_payload` receba opções dinâmicas por feature.

---

## 7. Auditoria das Políticas

O modelo `IntegrationSyncPolicy` determina como a sincronização ocorre para cada Feature.

- **Como o tenant escolhe importar ou sincronizar?** A política é instanciada e salva indicando o `mode` (`IntegrationSyncMode`), como `MANUAL`, `AGENDADO`, `EVENTO`, `PULL`, `PUSH`.
- Ela define também tentativas de falha (`retry_limite`), `batch_size`, `timeout_seconds`, `prioridade` e possui payload para *settings* dinâmicas de filtragem/comportamento daquela política específica.

---

## 8. Auditoria das Associações (ExternalRecordAssociation)

Implementado e transversal no AgroSaaS por meio do `ExternalRecordAssociationService` e do adaptador P0 (`SankhyaExternalAssociationHelper`).

Status de implementação para entidades externas/locais (Sankhya):
- **Produto**: Implementado.
- **Pessoa (Cliente/Fornecedor)**: Implementado (como `Parceiro`).
- **Conta Financeira (Conta Corrente)**: Implementado (`ContaBancaria` <-> `ContaCorrente`).
- **Depósito**: Implementado (`Deposito` <-> `LocalEstoque`).
- **Empresa**: Implementado (Criação de associação pendente, quando sem registro master confiável).
- **Filial**: Implementado.
- **Centro de Custo**: Parcial (Registra pendência financeira para associação manual/posterior).
- **Centro de Resultado**: Parcial (Registra pendência financeira para associação).
- **Unidade**: Implementado (`UnidadeMedida` <-> `Unidade`).
- Outros implementados: `NotaFiscal`, `Despesa`/`Receita` (`TituloFinanceiro`), `PlanoConta` (`NaturezaFinanceira`), `OperacaoTipoFase`.

O framework atende plenamente ao vínculo oficial local <-> externo com auditoria via `ExternalRecordAssociationHistory`.

---

## 9. Auditoria Arquitetural (O Wizard)

Em `ImplantacaoOperacional` (que orquestra o Wizard em `wizard/models.py` e `wizard/checklist_engine.py`):
- **Existe campo onde o usuário informa ERP?** Sim, porém não normalizado.
- **Onde fica / Como é persistido?** Fica em colunas JSON (`diagnostico_inicial_snapshot` ou `escopo_modulos`). 
- **É texto livre, Enum ou FK?** Atualmente, é **texto livre** ou **booleano**. As propriedades mapeadas pelo core (no `ErpReadinessService`) buscam por `integracao_erp` (bool), `erp_nome` (texto), `estrategia_carga`.
- **A seleção do ERP deveria apontar para MarketplaceIntegracao ou TenantIntegracao?** 
Deveria apontar para **MarketplaceIntegracao** durante o Wizard.
*Justificativa*: No estágio de Wizard/Diagnóstico, o usuário indica intenção (ex: "Uso Sankhya"). O `TenantIntegracao` só existirá de fato (ou com lifecycle correto) ao realizar o setup (configuração e auth). Guardar no Wizard o `marketplace_integracao.id` normaliza os dados e possibilita montar telas de setup corretas usando o `credential_schema` do Provider sem confiar em strings de texto livre propensas a erro.

---

## 10. Auditoria do Console ERP e Duplicidades

**Quem configura o ERP, credenciais, features, etc?**
As rotas do **Console ERP** (`services/api/integracoes/erp/router.py`) expõem operações como status, health, jobs, timeline e reconciliação. A interface para configuração oficial (Credenciais, Políticas) é o Console/Integrações.

**Existem duplicidades?** 
Do ponto de vista de banco e serviços (`ErpReadinessService` já abstrai validações), não há duplicação no backend.
A duplicação pode ocorrer se o Frontend tentar colocar formulários de autenticação de ERP ou vinculação diretamente dentro do Wizard de forma paralela ao Console.

**Fluxo quebrado**:
Existe *hardcode* limitante no `erp/router.py` (Console ERP): `if provider_slug != "sankhya": raise _unsupported_provider_error()`. Se o console tentar gerenciar outra ferramenta, a request será rejeitada. 

---

## 11. Auditoria da Configuração das APIs (Fluxo Externo)

**Como o AgroSaaS identifica qual API externa deve chamar?**
```text
Tenant -> (ErpReadinessService / Router) -> TenantIntegracao -> MarketplaceIntegracao (slug)
    -> Recupera IntegrationCredential e IntegrationFeature
    -> Adapter (ex: SankhyaCanonicalAdapter ou SankhyaSyncService)
    -> Gateway (Chamada HTTP segura baseada na auth decriptada) -> API externa
```
**Classes que implementam**: `ErpReadinessService` (discovery do slug ativo), `SankhyaCanonicalAdapter` / `SankhyaSyncService` (execução do negócio).
**Desacoplado?** O banco e a modelagem estão 100% genéricos. Contudo, o router oficial do ERP injeta o `SankhyaSyncService` explicitamente no FastApi (Depends) e força uma verificação contra a slug "sankhya", quebrando o Factory Pattern para múltiplos provedores.

---

## 12. Auditoria das Associações (Fluxo de Vínculo)

**Como um Produto é associado?**
```text
Produto AgroSaaS (Tabela: produtos)
       ↓ (local_entity='Produto', local_record_id=produto.id)
ExternalRecordAssociation (Status: ACTIVE ou PENDING)
       ↓ (external_entity='Produto', external_record_id='CODPROD')
Produto Sankhya/ERP (Sistemas remotos)
```

Este fluxo é mantido na íntegra pelo `ExternalRecordAssociationService`, que realiza:
- Criação e atualização;
- Verificações ativas de conflitos (detecção de duplicidade);
- Rastreio de eventos com `ExternalRecordAssociationHistory`;
- API unificada para Reconciliação (`reconcile_pending`).

---

## 13. Análise de Duplicidades e 14. Lacunas Encontradas
1. **Omissão de FK no Wizard**: O fluxo de ImplantaçãoOperacional depende de checar strings não estruturadas em campos JSON, em vez de suportar uma chave explícita para o ERP escolhido do Marketplace.
2. **Hardcode no Router HTTP do Console ERP**: O router universal finge ser agnóstico, mas invoca diretamente os Adapters e Schemas do módulo *Sankhya*.
3. **Ausência de formulários dinâmicos**: A interface de credenciais provavelmente é fixa, quando poderia se apoiar inteiramente em `credential_schema` contido no `MarketplaceIntegracao`.

---

## 15. Proposta de Evolução Incremental (Experiência do Usuário e Ideal)

**Fluxo Esperado Sem Associação no Wizard:**
1. **Wizard**: "Sua empresa utiliza ERP?" (Sim/Não).
2. Se Sim -> **Lista de ERPs** (vinda do `MarketplaceIntegracao` onde `provider_type="ERP"` e `ativa=True`).
3. **ERP selecionado** -> Salva FK do Marketplace no Wizard, eliminando texto livre.
4. "Deseja configurar agora?" 
5. **Configuração de credenciais** -> Usa schemas dinâmicos do Marketplace para renderizar a UI.
6. **Teste de conexão** -> Endpoint invoca Health Check (Adapter agnóstico via Factory).
7. **Readiness** -> Valida features.
8. Concluir Wizard. 

*As associações de registros (Produtos, Fornecedores, etc) NÃO DEVEM ocorrer dentro do Wizard, mas sim de forma assíncrona/governada na tela do "Console ERP" -> "Governança/Reconciliação".* O Wizard apenas exigirá (Readiness) que esses vínculos, quando críticos, sejam resolvidos antes do Go Live.

---

## 16. Roadmap Recomendado

**ERP-WIZARD-01 (Seleção do ERP)**
- Alterar o frontend e estado do Wizard para consumir o catálogo do Marketplace.
- Normalizar o armazenamento do provedor ERP para apontar formalmente ao registro do catálogo em vez de texto livre no snapshot JSON.

**ERP-CONFIG-01 (Configuração dinâmica por provider)**
- Refatorar o fluxo de inserção de credenciais, renderizando formulários *schema-driven* a partir de `credential_schema` e `connection_schema` definidos no Marketplace.

**ERP-READINESS-01 (Validação da integração)**
- Aprofundar as verificações do Readiness exibindo um relatório visual proativo, expondo "Capabilities Atendidas" vs "Requisitos do Piloto".

**ERP-ASSOCIATION-01 (Associação de registros)**
- Estender telas exclusivas de Reconciliação no Console ERP, listando pendências retornadas pelo `ExternalRecordAssociationService` e permitir links guiados. Não tocar no Wizard.

**ERP-SYNC-01 (Primeira sincronização assistida)**
- Refatorar `erp/router.py` introduzindo uma camada de abstração com *Factory Pattern* (ex: `ErpProviderFactory.get_adapter(provider_slug)`), substituindo o acoplamento fixo com `SankhyaSyncService`.

---

## 17. Comandos executados
- `ls -la /opt/lampp/htdocs/farm/services/api/integracoes`
- `ls -la /opt/lampp/htdocs/farm/services/api/wizard`
- `grep_search("MarketplaceIntegracao")`
- `grep_search("ExternalRecordAssociation")`
- Inspeção ativa nos arquivos: `integracoes/models.py`, `wizard/models.py`, `integracoes/erp_readiness_service.py`, `integracoes/erp/router.py`, `integracoes/services/external_record_association_service.py`, e `integracoes/sankhya/services/external_association_helper.py`.

## 18. Validações
- A infraestrutura já comporta a escalada. Nenhuma tabela é requerida.
- O mapeamento atestou conformidade no desacoplamento da camada de tabelas, contudo acusou a necessidade urgente de limpeza do router e dos schemas do Wizard.

## 19. Conclusão
A arquitetura `ERP-First` existente com `MarketplaceIntegracao`, `TenantIntegracao` e `ExternalRecordAssociation` demonstra **altíssima maturidade**, oferecendo controle refinado de status de integração, resiliência na associação de chaves externas e detecção de conflitos de banco de dados. Para atingir a conformidade plena, a evolução deve focar em desvincular strings *hardcoded* nos fluxos de serviço do Router (abrindo espaço para o modelo Multi-Provider real) e substituir os inputs em texto livre por escolhas validadas contra o Marketplace. Com esses ajustes incrementais, o AgroSaaS expandirá rapidamente seu ecossistema sem incorrer em débito técnico arquitetural.
