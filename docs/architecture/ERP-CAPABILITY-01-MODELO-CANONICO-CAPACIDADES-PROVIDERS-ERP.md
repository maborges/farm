# ERP-CAPABILITY-01 - Modelo Canonico de Capacidades de Providers ERP

Status: APROVADA
Categoria: Arquitetura Funcional
Tipo: Regra Arquitetural
Data: 2026-07-09

## 1. Objetivo

Definir o modelo oficial, generico e agnostico a provider para declarar, interpretar e utilizar capacidades de providers ERP no AgroSaaS.

Este documento parte obrigatoriamente de:

- `ERP-DOMAIN-01`
- `ERP-CONSOLE-01`
- `ERP-GOV-02`
- `INTEGRATIONS-ARCH-01`
- `INTEGRATIONS-ARCH-02`
- `INTEGRATIONS-LIFECYCLE-01`

Regra central:

- capability descreve suporte tecnico-funcional do provider;
- capability nao redefine ownership;
- capability nao redefine escopo ERP;
- capability nao cria segundo runtime;
- Sankhya e apenas o provider atual de referencia, nunca a regra geral.

## 2. Resultado da auditoria obrigatoria

### 2.1 Estruturas existentes que devem ser reutilizadas

O repositorio ja possui contratos suficientes para suportar um modelo canonico de capabilities sem criar nova tabela:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`
- `TenantIntegracao.connection_payload`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationJob`

### 2.2 Estruturas existentes que devem ser estendidas semanticamente

Devem ser estendidos por contrato e documentacao, nao por redesign estrutural nesta execucao:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.feature_schema`
- `IntegrationFeature.settings_payload`
- `IntegrationSyncPolicy.settings_payload`
- `IntegrationHealth.details_payload`

### 2.3 Estruturas que devem ser consolidadas

- capability matrix do provider deve viver na definicao do provider, nao em planilha paralela;
- habilitacao concreta do tenant deve viver em `IntegrationFeature`;
- modo de sincronizacao concreto deve viver em `IntegrationSyncPolicy`;
- health e maturidade operacional observada devem ser correlacionados pelo runtime oficial.

### 2.4 Estruturas que nao devem ser duplicadas

Nao criar:

- nova tabela de capabilities;
- nova tabela de feature;
- nova politica paralela de sync;
- nova fonte de provider definition;
- novo runtime de health;
- novo modelo de escopo para ERP.

## 3. Conceito oficial de Capability

Capability ERP e a capacidade tecnico-funcional declarada de um provider para operar uma responsabilidade de integracao dentro dos limites do dominio ERP.

Capability:

- nao e modulo comercial;
- nao e permissao;
- nao e ownership;
- nao e tela;
- nao e policy de sync;
- nao e health;
- nao e mapeamento externo.

Capability responde:

- o provider suporta ou nao uma capacidade;
- em que nivel suporta;
- em qual direcao;
- em quais escopos administrativos;
- por quais modos de sincronizacao;
- com quais dependencias;
- com quais restricoes conhecidas;
- com qual maturidade.

Exemplos:

- sincronizar pessoas;
- importar produtos;
- receber contas a pagar;
- retornar NFe como evidencia;
- suportar webhook;
- suportar sync incremental;
- suportar CT-e;
- suportar MDF-e.

## 4. Taxonomia e identidade da Capability

Formato canonico recomendado:

```text
erp.<dominio>.<entidade>.<acao>
```

Exemplos:

- `erp.cadastros.pessoas.importar`
- `erp.cadastros.produtos.sincronizar`
- `erp.financeiro.contas_pagar.importar`
- `erp.financeiro.baixas.receber`
- `erp.fiscal.nfe.evidenciar`
- `erp.logistica.cte.consultar`

Regras:

- o prefixo `erp.` e obrigatorio para capabilities ERP;
- capability deve nomear a responsabilidade, nao o endpoint do provider;
- capability deve ser estavel mesmo se o provider mudar de API.

## 5. Classificacao oficial da Capability

Classificacoes permitidas:

- `SUPPORTED`
- `PARTIAL`
- `UNSUPPORTED`
- `UNKNOWN`
- `NOT_APPLICABLE`

Significado:

- `SUPPORTED`: capability materializada e suportada pelo provider dentro do dominio esperado.
- `PARTIAL`: existe suporte incompleto, com limitacoes relevantes de operacao, direcao, entidade ou sync.
- `UNSUPPORTED`: o provider nao suporta a capability de forma util.
- `UNKNOWN`: a plataforma ainda nao possui evidencia suficiente para classificar.
- `NOT_APPLICABLE`: a capability nao pertence ao dominio ERP ou nao faz sentido para aquele provider.

## 6. Maturidade oficial da Capability

Niveis permitidos:

- `DECLARED`
- `TESTED`
- `PILOT_READY`
- `PRODUCTION_READY`
- `DEPRECATED`

Significado:

- `DECLARED`: capability esta documentada, mas sem evidencia suficiente de uso real.
- `TESTED`: capability foi exercitada tecnicamente.
- `PILOT_READY`: capability tem suporte suficiente para piloto controlado.
- `PRODUCTION_READY`: capability sustenta operacao recorrente com observabilidade e reprocesso.
- `DEPRECATED`: capability ainda existe por compatibilidade, mas nao deve ser expandida.

Regra:

- status e maturidade sao eixos diferentes;
- uma capability pode ser `SUPPORTED` e ainda assim estar apenas em `TESTED`;
- uma capability `PARTIAL` nao pode ser tratada como pronta para piloto ampliado sem ressalvas.

## 7. Escopo oficial da Capability

Escopos ERP permitidos:

- `TENANT`
- `ESTABELECIMENTO`

Escopos proibidos:

- `UNIDADE_PRODUTIVA`
- `TALHAO`
- `SAFRA`
- `CULTIVO`
- qualquer escopo operacional rural

Regra:

- capability ERP herda o escopo administrativo oficial do dominio ERP;
- capability nao pode contornar `ERP-DOMAIN-01` nem `ERP-GOV-02`.

## 8. Direcao oficial da Capability

Direcoes permitidas:

- `ERP_TO_AGROSAAS`
- `AGROSAAS_TO_ERP`
- `BIDIRECTIONAL_CONTROLLED`
- `READ_ONLY`
- `WRITE_ONLY`
- `EVIDENCE_RETURN`

Semantica:

- `ERP_TO_AGROSAAS`: ERP e fonte principal da troca.
- `AGROSAAS_TO_ERP`: AgroSaaS envia para o ERP dentro do ownership oficial.
- `BIDIRECTIONAL_CONTROLLED`: trafego em duas direcoes, sempre governado por policy e conflito.
- `READ_ONLY`: o AgroSaaS apenas consulta.
- `WRITE_ONLY`: o AgroSaaS apenas envia.
- `EVIDENCE_RETURN`: o ERP devolve evidencia oficial, tipicamente fiscal ou administrativa.

Regra:

- capability nunca altera o owner oficial definido em `ERP-DOMAIN-01`;
- a direcao da capability deve ser coerente com a politica de conflito do dominio.

## 9. Modos oficiais de sincronizacao

Cada capability deve declarar modos suportados dentre:

- `MANUAL`
- `ON_DEMAND`
- `SCHEDULED`
- `POLLING`
- `EVENT_DRIVEN`
- `WEBHOOK`
- `DISABLED`

Regra de persistencia:

- o catalogo suportado da capability deve ser declarado em `provider_definition` e `feature_schema`;
- a ativacao concreta do tenant deve reutilizar `IntegrationSyncPolicy`;
- nao criar segunda politica de sync.

Mapeamento com runtime atual:

- `MANUAL` e `ON_DEMAND` orbitam `IntegrationSyncMode.MANUAL`;
- `SCHEDULED` orbita `IntegrationSyncMode.AGENDADO`;
- `EVENT_DRIVEN` orbita `IntegrationSyncMode.EVENTO`;
- `WEBHOOK` orbita `IntegrationSyncMode.WEBHOOK`;
- `POLLING` orbita `IntegrationSyncMode.PULL`;
- `READ_ONLY` ou envio ativo podem orbitar `IntegrationSyncMode.PUSH`, quando aplicavel.

## 10. Entidades relacionadas

Cada capability deve apontar as entidades que toca.

Exemplo:

```text
Capability: erp.financeiro.contas_pagar.importar
Entidades relacionadas:
- ContaPagar administrativa
- Pessoa
- Fornecedor
- NaturezaFinanceira
- CentroCusto
- ContaCorrente
```

Regra:

- capability deve apontar entidades de dominio;
- entity mapping nao substitui `ExternalRecordAssociation`;
- dependencias de entidades compartilhadas devem respeitar ownership oficial.

## 11. Dependencias

Cada capability pode declarar dependencias funcionais e tecnicas.

Exemplos:

- `baixas` dependem de `contas_pagar`, `contas_receber`, `contas_correntes`, `bancos`.
- `cte` depende de `documentos_fiscais`, `transporte`, `emitente`, `destinatario`.
- `estoque_administrativo` depende de `depositos`, `produtos`, `estabelecimentos`.

Tipos de dependencia:

- `hard_dependency`: bloqueia a capability dependente.
- `soft_dependency`: reduz escopo ou maturidade, mas nao bloqueia tudo.
- `provider_dependency`: capability exige modulo contratado no ERP.
- `mapping_dependency`: capability exige reconciliacao ou de-para previo.

## 12. Restricoes conhecidas

Cada capability deve permitir restricoes declaradas, por exemplo:

- consulta apenas;
- sem criacao;
- sem webhook;
- paginação obrigatoria;
- rate limit;
- campo obrigatorio ausente no AgroSaaS;
- endpoint incompleto;
- depende de modulo contratado no ERP;
- suporta apenas tenant;
- suporta apenas homologacao ou ambiente especifico.

Regra:

- restricao do provider nao vira regra da plataforma;
- restricao deve afetar status, maturidade ou escopo da capability, nunca ownership.

## 13. Provider Capability Matrix

Matriz oficial:

| Provider | Capability | Status | Maturidade | Direcao | Sync | Escopo |
| -------- | ---------- | ------ | ---------- | ------- | ---- | ------ |
| Sankhya | Pessoas | SUPPORTED | TESTED | ERP_TO_AGROSAAS | MANUAL/SCHEDULED/POLLING | TENANT |
| Sankhya | CT-e | UNKNOWN | DECLARED | ERP_TO_AGROSAAS | UNKNOWN | TENANT |
| Sankhya | Operacao Agricola | NOT_APPLICABLE | DECLARED | NOT_APPLICABLE | DISABLED | NOT_APPLICABLE |

Campos minimos da linha canonica:

- `provider`
- `capability_code`
- `status`
- `maturity`
- `direction`
- `supported_sync_modes`
- `supported_scopes`
- `entities`
- `dependencies`
- `constraints`
- `notes`

## 14. Relacao oficial com Provider Definition

Persistencia futura deve reutilizar:

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.feature_schema`
- `IntegrationFeature`
- `IntegrationSyncPolicy`

Contrato oficial:

- `provider_definition` declara capability catalog, maturidade base, escopos validos e restricoes estruturais;
- `feature_schema` declara catalogo suportado e metadados por capability;
- `IntegrationFeature` representa habilitacao concreta da capability para uma configuracao do tenant;
- `IntegrationSyncPolicy` representa o modo operacional ativo daquela capability;
- `IntegrationHealth` e `IntegrationJob` trazem a evidencia observavel do que realmente aconteceu.

Decisao:

- capabilities nao exigem nova tabela enquanto os campos existentes suportarem catalogo declarativo mais payloads;
- se futuramente faltar estrutura, isso deve voltar para arquitetura antes de migration.

## 15. Modelo canonico minimo de capability

Modelo funcional minimo:

```text
capability_code
display_name
description
status
maturity
direction
supported_scopes
supported_sync_modes
related_entities
dependencies
constraints
observability_requirements
pilot_tier
provider_specific_notes
```

Alocacao recomendada:

- definicao estrutural: `provider_definition` + `feature_schema`
- habilitacao por tenant: `IntegrationFeature`
- modo operacional: `IntegrationSyncPolicy`
- saude observada: `IntegrationHealth`
- execucao real: `IntegrationJob`

## 16. Relacao com o Wizard

O Wizard:

- nao configura capability;
- nao cria provider;
- nao define policy;
- nao substitui o Console ERP.

O Wizard pode consumir capability para decidir:

- ERP configurado;
- provider apto ao piloto restrito;
- provider apto ao piloto ampliado;
- bloqueios criticos;
- alertas operacionais;
- pendencias opcionais.

Evolucao oficial para `CHECK_INTEGRACAO_ERP`:

ele nao deve depender apenas de “existe configuracao”.

Ele deve evoluir para verificar:

- provider configurado;
- health minimo valido;
- capabilities P0 requeridas;
- policies minimas ativas;
- sem conflitos criticos de reconciliacao;
- sem capability `UNKNOWN` em itens obrigatorios do piloto.

## 17. Relacao com o Console ERP

O Console ERP deve exibir a capability matrix de modo funcional.

Estados visiveis esperados:

- suportado;
- parcial;
- nao suportado;
- desconhecido;
- nao se aplica;
- pronto para piloto;
- pronto para producao;
- pendente de configuracao;
- pendente de mapeamento;
- pendente de credencial.

Regra:

- o console mostra capability;
- a configuracao concreta continua em `IntegrationFeature` e `IntegrationSyncPolicy`;
- o console nao pode inventar capacidade que o provider nao declarou.

## 18. Relacao com o Backoffice

Backoffice pode consumir capability para:

- suporte;
- diagnostico;
- comparacao entre tenants;
- leitura de limitacoes do provider;
- recomendacao de escopo de piloto.

Backoffice nao deve:

- configurar capability do tenant como fluxo principal;
- reclassificar manualmente ownership;
- liberar piloto ampliado ignorando capability desconhecida ou parcial critica.

## 19. Relacao com Pilot Scope

### 19.1 Piloto Restrito

Capabilities minimas:

- pessoas
- clientes
- fornecedores
- produtos
- NFe
- financeiro basico
- health
- jobs
- logs
- reconciliacao manual

### 19.2 Piloto Ampliado

Adiciona:

- depositos
- contas correntes
- centros de custo
- centros de resultado
- naturezas financeiras
- pagamentos
- recebimentos
- baixas
- estoque administrativo
- pedidos
- contratos
- comercializacao

### 19.3 Piloto Exportador

Adiciona:

- CT-e
- MDF-e
- logistica integrada
- documentos de exportacao
- cadeia fiscal/exportadora
- evidencias fiscais completas

Regra:

- capability `UNKNOWN` ou `PARTIAL` em item P0 bloqueia classificacao automatica como piloto ampliado ou exportador;
- `NOT_APPLICABLE` nao conta contra o provider quando a capability nao pertence ao dominio ERP daquele fluxo.

## 20. Guardrails especificos

Guardrails obrigatorios:

- capability nao redefine ownership;
- capability nao autoriza escopo invalido;
- capability nao substitui policy;
- capability nao substitui health;
- capability nao substitui mapeamento;
- capability nao transforma limitacao do provider em regra da plataforma;
- capability parcial nao pode ser exibida como pronta;
- capability desconhecida nao pode liberar piloto ampliado;
- capability sem observabilidade nao pode receber maturidade `PRODUCTION_READY`.

## 21. Checklist oficial de avaliacao de provider

Todo novo ERP deve responder:

1. Provider identificado?
2. Capability catalog declarada?
3. Capabilities P0 presentes?
4. Status por capability definido?
5. Maturidade por capability definida?
6. Modos de sync declarados?
7. Dependencias documentadas?
8. Restricoes documentadas?
9. Health disponivel?
10. Jobs e logs disponiveis?
11. Reconciliacao manual disponivel?
12. Pilot scope classificado?

Sem esse checklist:

- o provider nao deve ser tratado como apto ao piloto oficial.

## 22. Aplicacao conceitual inicial ao Sankhya

### 22.1 Supported ou tested

Com base no runtime atual auditado:

- `erp.cadastros.pessoas.importar`: `SUPPORTED` / `TESTED`
- `erp.cadastros.produtos.importar`: `SUPPORTED` / `TESTED`
- `erp.financeiro.movimentos.importar`: `PARTIAL` / `TESTED`
- `erp.fiscal.nfe.consultar_ou_evidenciar`: `PARTIAL` / `TESTED`
- `erp.integracao.health.monitorar`: `SUPPORTED` / `PRODUCTION_READY`
- `erp.integracao.jobs.observar`: `SUPPORTED` / `PRODUCTION_READY`
- `erp.integracao.logs.observar`: `SUPPORTED` / `PRODUCTION_READY`
- `erp.integracao.reconciliacao.manual`: `SUPPORTED` / `TESTED`

### 22.2 Partial

Parciais pela evidencia atual:

- financeiro, porque a feature existe, mas a cobertura funcional nao prova todos os fluxos administrativos;
- NFe, porque existe integracao e retorno de dados, mas nao ha evidencia de cobertura fiscal ampla do piloto exportador;
- pedidos e estoque, porque o adapter ja os declara como futuros e desabilitados no catalogo inicial.

### 22.3 Unknown

Sem evidencia suficiente no runtime auditado:

- CT-e
- MDF-e
- documentos de exportacao
- contratos
- barter
- comercializacao exportadora

### 22.4 Unsupported ou not applicable

- operacao agricola: `NOT_APPLICABLE`
- operacao pecuaria: `NOT_APPLICABLE`
- talhao, safra, cultivo, unidade produtiva como escopo ERP: `NOT_APPLICABLE`

### 22.5 Gaps do provider atual versus gaps da plataforma

Gaps do provider Sankhya ou de sua implementacao atual:

- catalogo inicial de features ainda pequeno;
- falta de classificacao explicita para CT-e, MDF-e e exportacao;
- pedidos e estoque declarados como futuros, nao ativos.

Gaps da plataforma:

- runtime ainda nao materializa status e maturidade de capability como contrato explicito no console;
- `CHECK_INTEGRACAO_ERP` do wizard ainda nao usa capability matrix, policy e health reais;
- falta classificacao oficial de piloto restrito/ampliado/exportador consumindo capability matrix.

## 23. Veredicto arquitetural

O AgroSaaS ja possui base estrutural suficiente para um modelo canonico de capabilities sem nova tabela.

Decisao oficial:

- reutilizar o runtime atual;
- tratar capability como catalogo declarativo do provider;
- tratar `IntegrationFeature` como habilitacao concreta;
- tratar `IntegrationSyncPolicy` como politica operacional;
- tratar `IntegrationHealth` e `IntegrationJob` como evidencia runtime;
- evoluir Wizard e Console ERP para consumir capability matrix, sem criar dominio paralelo.
