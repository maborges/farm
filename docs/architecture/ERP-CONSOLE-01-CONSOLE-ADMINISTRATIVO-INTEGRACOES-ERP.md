# ERP-CONSOLE-01 - Console Administrativo de Integracoes ERP

Status: APROVADA
Categoria: Arquitetura Funcional
Tipo: Regra Arquitetural
Data: 2026-07-09

## 1. Objetivo

Definir a arquitetura funcional do Console Administrativo de Integracoes ERP do AgroSaaS.

Este documento parte obrigatoriamente de:

- [ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md)
- [ERP-DOMAIN-01-DECISOES-PARA-PILOTO-ERP.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-DOMAIN-01-DECISOES-PARA-PILOTO-ERP.md)

Regra central:

- o console ERP nao e adapter;
- o console ERP nao e Wizard;
- o console ERP nao e onboarding;
- o console ERP e a camada administrativa oficial para configurar, validar, monitorar, diagnosticar, reconciliar, versionar e operar integracoes ERP.

## 2. Resultado da auditoria obrigatoria

### 2.1 Ativos existentes que devem ser reutilizados

Backoffice e tenant ja possuem ativos reais e nao devem ser duplicados:

- rota tenant consolidada: `/dashboard/settings/integracoes/erp`
- componente tenant existente: `apps/web/src/components/integracoes/sankhya-console.tsx`
- tela de observabilidade de backoffice existente: `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- timeline operacional existente: `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- runtime canonico existente:
  - `MarketplaceIntegracao`
  - `TenantIntegracao`
  - `IntegrationCredential`
  - `IntegrationVersion`
  - `IntegrationFeature`
  - `IntegrationSyncPolicy`
  - `IntegrationJob`
  - `IntegrationHealth`
  - `ExternalRecordAssociation`
  - `ExternalRecordAssociationHistory`
- endpoints tenant-scoped existentes:
  - `/integracoes/sankhya/config`
  - `/integracoes/sankhya/config/testar-conexao`
  - `/integracoes/sankhya/status`
  - `/integracoes/sankhya/health`
  - `/integracoes/sankhya/jobs`
  - `/integracoes/sankhya/logs`
  - `/integracoes/sankhya/timeline`
  - `/integracoes/sankhya/diagnostico`
  - `/integracoes/sankhya/associacoes/pendentes`
  - `/integracoes/sankhya/associacoes/{id}/reconciliar`

### 2.2 Ativos existentes que devem ser estendidos

- `MarketplaceIntegracao.provider_definition`
- `MarketplaceIntegracao.connection_schema`
- `MarketplaceIntegracao.credential_schema`
- `MarketplaceIntegracao.feature_schema`
- `MarketplaceIntegracao.sync_schema`
- `MarketplaceIntegracao.health_schema`
- `TenantIntegracao.connection_payload`
- `IntegrationVersion.snapshot_mascarado`
- `IntegrationFeature.settings_payload`
- `IntegrationSyncPolicy.settings_payload`
- `IntegrationHealth.details_payload`

### 2.3 Ativos existentes que devem ser consolidados

- console do tenant deve deixar de ser conceitualmente "console Sankhya" e passar a ser "console ERP" com provider atual Sankhya como primeira implementacao;
- a tela de backoffice deve permanecer somente como observabilidade e suporte, nunca como console principal de configuracao;
- o Wizard deve apontar para a rota consolidada do console ERP do tenant, nao para rota legada;
- `ExternalRecordAssociation` deve ser a unica base oficial de mapeamentos externos, sem tabela paralela.

### 2.4 Itens que devem ser depreciados

- links legados do Wizard para `/configuracoes/integracoes`
- semantica de "Configuracao do Sankhya" no menu quando a arquitetura oficial passa a ser ERP generico
- qualquer tentativa futura de configurar ERP por `UnidadeProdutiva`

### 2.5 Itens que nao devem ser mexidos nesta execucao

- adapters
- rotas existentes
- models
- Wizard
- onboarding
- migrations
- telas implementadas

## 3. Finalidade oficial do Console ERP

O Console ERP e a camada administrativa oficial para:

- configurar provider e escopo;
- validar conexao;
- monitorar health;
- inspecionar diagnostico;
- consultar jobs e logs;
- operar sincronizacoes permitidas;
- reconciliar pendencias;
- versionar parametros criticos;
- auditar mudancas;
- expor capacidade real do provider.

Ele nao deve:

- substituir o adapter;
- substituir o Wizard;
- substituir o onboarding;
- duplicar observabilidade do backoffice;
- criar fonte paralela de ownership de dados.

## 4. Posicionamento oficial na navegacao

Posicionamento conceitual oficial:

```text
Dashboard > Configuracoes > Integracoes > ERPs
```

Decisao v1:

- reutilizar a rota existente `/dashboard/settings/integracoes/erp`;
- tratar essa rota como console ERP generico;
- permitir que o provider ativo seja Sankhya no primeiro momento;
- nao criar nova rota paralela para `sankhya` como ponto principal de configuracao do tenant.

Backoffice:

- reutilizar `/dashboard/backoffice/integracoes/erp` apenas para observabilidade, health, diagnostico e suporte;
- nao usar backoffice como console primario de configuracao.

## 5. Separacao oficial entre Configuracao e Operacao

O console ERP deve ter duas areas funcionais.

### 5.1 Configuracao

Uso:

- itens criticos;
- baixa frequencia;
- alto impacto.

Responsabilidades:

- provider
- ambiente
- URL base
- URL de autenticacao
- URL de gateway
- URL de webhook, quando existir
- versao tecnica
- escopo
- estabelecimento, quando aplicavel
- credenciais
- certificados
- metodo de autenticacao
- capacidades habilitadas
- politicas de sincronizacao
- mapeamentos padrao
- versionamento

### 5.2 Operacao

Uso:

- rotina
- validacao recorrente
- suporte funcional
- troubleshooting controlado

Responsabilidades:

- health
- teste de conexao
- diagnostico
- jobs
- logs
- timeline
- sincronizacoes manuais permitidas
- falhas
- reprocessamentos
- reconciliacao manual
- historico
- alertas operacionais

Regra:

- configuracao e operacao devem coexistir no mesmo console funcional;
- a interface pode separar por abas, cards, secoes ou steps;
- a fronteira conceitual deve permanecer explicita.

## 6. Gestao oficial de URL e endpoints

O console deve prever explicitamente que URLs e endpoints do ERP podem mudar.

Normas:

- nenhuma URL critica deve ficar hardcoded no adapter como fonte primaria de configuracao do cliente;
- alteracoes de URL devem ser feitas no console;
- alteracoes devem ser testadas antes de salvar, quando o provider suportar;
- alteracoes devem gerar nova versao mascarada da configuracao;
- alteracoes devem ser auditadas;
- health e status devem refletir a configuracao vigente.

Campos conceituais minimos:

- `environment`
- `api_base_url`
- `auth_url`
- `gateway_url`
- `webhook_url`
- `api_version`
- `vigencia_inicio`
- `vigencia_fim`, quando houver transicao controlada
- `alterado_por`
- `resultado_ultimo_teste`
- `testado_em`

Persistencia:

- reutilizar `TenantIntegracao.connection_payload`
- reutilizar `IntegrationVersion.snapshot_mascarado`
- reutilizar `IntegrationHealth`

## 7. Provider Capability Matrix

Cada provider ERP deve declarar uma matriz explicita de capacidades.

Classificacoes oficiais:

- `SUPPORTED`
- `PARTIAL`
- `UNSUPPORTED`
- `UNKNOWN`

Cobertura minima esperada na matriz:

- pessoas
- produtos
- NFe
- contas a pagar
- contas a receber
- pagamentos
- recebimentos
- baixas
- depositos
- contas correntes
- centros de custo
- centros de resultado
- tipos de operacao
- CT-e
- MDF-e
- barter
- contratos
- comercializacao
- webhook
- sync incremental
- sync completo
- reconciliacao manual

Regras:

- capability matrix pertence ao provider e sua configuracao;
- nao pertence ao Wizard;
- nao deve ser inferida apenas pela existencia de um endpoint;
- deve refletir cobertura real de operacao.

Persistencia oficial:

- definicao estrutural no `provider_definition` e `feature_schema`
- ativacao concreta em `IntegrationFeature`

## 8. Ownership por entidade e por atributo

O ownership por entidade continua definido por `ERP-DOMAIN-01`.

O console deve apenas:

- exibir a regra vigente por entidade;
- exibir conflitos conhecidos;
- preparar o caminho para evolucao futura por atributo.

Exemplo futuro previsto:

Pessoa:

- CPF/CNPJ: ERP
- nome fiscal: ERP
- telefone operacional: compartilhado
- classificacao operacional: AgroSaaS

Regra:

- ownership por atributo nao deve ser implementado agora;
- deve ser previsto como extensao arquitetural futura;
- o console nao pode contradizer `ERP-DOMAIN-01`.

## 9. Modos oficiais de sincronizacao

O console deve trabalhar com os modos oficiais:

- `MANUAL`
- `ON_DEMAND`
- `SCHEDULED`
- `POLLING`
- `EVENT_DRIVEN`
- `WEBHOOK`
- `DISABLED`

Observacao de compatibilidade:

- o dominio atual ja materializa modos canonicos como `MANUAL`, `AGENDADO`, `EVENTO`, `WEBHOOK`, `PULL` e `PUSH`;
- o console funcional deve expor uma camada semantica mais clara ao usuario, sem criar segundo modelo persistente;
- mapeamentos conceituais podem existir entre o rotulo funcional do console e o enum tecnico atual.

Regra:

- cada entidade suportada por um provider deve declarar quais modos aceita;
- nenhuma sincronizacao deve existir sem politica explicita em `IntegrationSyncPolicy`.

## 10. Escopo funcional do console

Escopos oficiais:

- `TENANT`
- `ESTABELECIMENTO`

Normas:

- o console deve apresentar o escopo administrativo antes da configuracao tecnica;
- `ESTABELECIMENTO` deve ser opcao explicita quando essa arquitetura for materializada operacionalmente;
- o console nao deve permitir configuracao por `UNIDADE_PRODUTIVA`;
- se algum fluxo legado referenciar unidade produtiva em contexto ERP, isso deve aparecer apenas como item de auditoria e deprecacao futura.

## 11. Mapeamentos

A area de mapeamentos do console deve reutilizar obrigatoriamente `ExternalRecordAssociation`.

Nao pode existir tabela paralela de de-para ERP.

Mapeamentos minimos previstos:

- empresa
- filial
- estabelecimento
- deposito
- conta corrente
- banco
- natureza financeira
- centro de custo
- centro de resultado
- tipo de operacao
- produto
- pessoa
- cliente
- fornecedor

Fluxos funcionais:

- listar pendencias
- visualizar historico
- reconciliar manualmente
- registrar motivo
- mostrar origem, escopo, feature e ultimo job relacionado

Regras:

- mapeamento nao pode sobrescrever ownership;
- mapeamento so resolve identidade externa;
- conflito de mapeamento exige reconciliacao manual.

## 12. Observabilidade funcional

O console deve reutilizar obrigatoriamente:

- `IntegrationJob`
- `IntegrationHealth`
- `IntegrationSyncPolicy`
- logs existentes
- status existentes
- timeline existente

Experiencias funcionais obrigatorias:

- health check
- teste de conexao
- diagnostico
- jobs
- logs
- falhas
- reprocessamento controlado
- reconciliacao manual

Separacao oficial:

- tenant ve sua propria operacao e sua propria saude;
- backoffice ve suporte, correlação e troubleshooting;
- a fonte de dados pode ser a mesma, mas a visao funcional nao.

## 13. Permissoes oficiais

Permissoes minimas v1:

- `Owner`
- `Administrador do Tenant`

Permissoes funcionais a explicitar no dominio:

- visualizar integracao
- configurar integracao
- alterar credenciais
- alterar URL
- executar sincronizacao
- resolver conflito
- reprocessar job
- ver logs
- ver diagnostico

Compatibilidade com o estado atual:

- reutilizar o namespace ja existente `integrations:view`, `integrations:configure`, `integrations:test`, `integrations:sync`, `integrations:logs:view`;
- evoluir depois para granularidade mais fina sem quebrar o modelo atual.

## 14. Relacao com Wizard

Regra oficial:

- o Wizard nao configura ERP;
- o Wizard nao persiste credenciais ERP;
- o Wizard nao substitui o console ERP.

O Wizard apenas:

- verifica se a integracao ERP esta configurada quando necessario;
- mostra pendencias;
- aponta para o console ERP;
- bloqueia ou alerta conforme checklist;
- reavalia o status.

Item de consolidacao:

- links legados do Wizard para `/configuracoes/integracoes` devem ser tratados como legado funcional e consolidados para a rota oficial do console ERP do tenant.

## 15. Relacao com onboarding

Regra oficial:

- o onboarding `/register` nao configura ERP;
- a escolha de provider nao pertence ao onboarding inicial;
- o onboarding pode apenas registrar contexto comercial minimo no futuro, se necessario, mas nao credenciais nem configuracao tecnica.

## 16. Guardrails funcionais

- nao duplicar cadastro de provider
- nao duplicar credenciais
- nao duplicar mapeamentos externos
- nao criar escopo ERP por `UnidadeProdutiva`
- nao hardcodar URL do ERP como fonte primaria do cliente
- nao permitir adapter redefinir ownership de entidade
- nao permitir sync sem politica explicita
- nao permitir entidade compartilhada sem regra de conflito
- nao permitir mudanca critica sem historico
- nao permitir credencial exposta em tela, log ou relatorio
- nao permitir novo console paralelo no backoffice
- nao permitir que Wizard vire tela de configuracao ERP

## 17. Decisoes de reutilizacao, extensao e deprecacao

### Reutilizar

- `/dashboard/settings/integracoes/erp`
- `sankhya-console.tsx`
- `sankhya-timeline.tsx`
- `IntegrationCredential`
- `IntegrationVersion`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationJob`
- `IntegrationHealth`
- `ExternalRecordAssociation`

### Estender

- `MarketplaceIntegracao` para capability matrix generica
- `TenantIntegracao.connection_payload`
- `IntegrationVersion.snapshot_mascarado`
- camada visual do console para suportar multiplos providers

### Renomear conceitualmente

- "ERP Sankhya" -> "Integracoes ERP" como nome funcional do console
- "Configuracao do Sankhya" -> "Configuracao ERP do tenant"

### Consolidar

- console tenant como ponto principal de configuracao
- backoffice como observabilidade e suporte
- Wizard como orquestrador e apontador

### Depreciar

- links legados para `/configuracoes/integracoes`
- qualquer leitura de que o backoffice configura o ERP do tenant
- qualquer referencia futura a configuracao ERP por unidade produtiva

### Nao mexer nesta fase

- adapters reais
- Wizard implementado
- onboarding
- rotas existentes
- schema persistente atual

## 18. Arquitetura funcional alvo

Modelo conceitual:

```text
Console ERP do Tenant
  ├── Configuracao
  │   ├── Provider e escopo
  │   ├── Conexao e URLs
  │   ├── Credenciais e certificados
  │   ├── Capabilities
  │   ├── Politicas de sync
  │   ├── Versionamento
  │   └── Mapeamentos e reconciliacao
  ├── Operacao
  │   ├── Health
  │   ├── Teste de conexao
  │   ├── Diagnostico
  │   ├── Jobs
  │   ├── Logs
  │   ├── Timeline
  │   ├── Sincronizacoes
  │   └── Reprocessamentos controlados
  └── Governanca
      ├── Historico
      ├── Auditoria
      ├── Ownership visivel
      └── Guardrails
```

## 19. Resultado esperado desta arquitetura

Após esta norma:

- o AgroSaaS passa a ter uma arquitetura funcional unica para o console ERP;
- o sistema deixa de depender conceitualmente do nome Sankhya para definir a UX administrativa;
- o console do tenant, o backoffice e o Wizard passam a ter papeis distintos e nao concorrentes;
- o dominio de integracoes existente e reaproveitado sem criar tabelas, rotas ou conceitos paralelos.
