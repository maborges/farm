# INTEGRATIONS-ARCH-01 — Relatório de Arquitetura Canônica de Integrações

Data da execução: 2026-07-01

## 1. Resumo executivo

Foi criada a arquitetura canônica do domínio `Integrações` para reger integrações ERP, bancos, fiscal, satélite, clima, IoT, comunicação, armazenamento, webhooks, APIs externas e BI.

Decisão central:

- integrações passam a ter domínio próprio;
- ERP do cliente não é global da plataforma;
- ERP do cliente não é por Unidade Produtiva;
- o escopo correto é `TENANT` e, quando necessário, `ESTABELECIMENTO`.

## 2. Situação atual observada

- Sankhya já existe com backend majoritariamente tenant-scoped;
- a UI principal ainda está indevidamente posicionada no backoffice;
- não há domínio arquitetural oficial de integrações;
- não há modelagem oficial de `Estabelecimento`;
- há lacunas de governança de credenciais e de isolamento operacional.

## 3. Arquitetura oficial definida

Foram oficializados:

- domínio `Integrações`;
- taxonomia oficial;
- escopos `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`;
- papel oficial de `Estabelecimento`;
- papel oficial do Backoffice versus console do tenant;
- contratos canônicos de integração;
- posição oficial do ERP e aplicação ao Sankhya.

## 4. Principais decisões

- `Integrações` é um domínio arquitetural transversal do AgroSaaS.
- `ERP` representa empresa/estabelecimento, não operação territorial.
- `UnidadeProdutiva` não é escopo válido de configuração de ERP.
- `Estabelecimento` é o domínio administrativo correto entre `Tenant` e `UnidadeProdutiva`.
- a configuração principal do ERP deve morar na administração do tenant, não no backoffice.
- o backoffice deve concentrar observabilidade, diagnóstico, suporte e troubleshooting.
- segredos e credenciais devem ser tratados por contrato canônico separado.

## 5. Modelo oficial para Integrações

Modelo oficial:

```text
IntegrationProvider
  ↓
IntegrationScope
  ↓
IntegrationConfig
  ↓
IntegrationCredential
  ↓
IntegrationJob / IntegrationEvent / IntegrationLog / IntegrationHealth
```

Escopos oficiais:

- `PLATFORM`
- `TENANT`
- `ESTABELECIMENTO`
- `USUARIO`

## 6. Modelo oficial para ERP

Modelo oficial:

- escopo padrão: `TENANT`
- escopo estendido: `ESTABELECIMENTO`
- escopo proibido: `UNIDADE_PRODUTIVA`

Critério:

- ERP corporativo único do cliente: `TENANT`
- ERP por matriz/filial/CNPJ distinto: `ESTABELECIMENTO`

## 7. Modelo oficial para Estabelecimentos

`Estabelecimento` passa a ser conceito arquitetural oficial do domínio administrativo.

Semântica:

- `Tenant`: fronteira SaaS e de isolamento;
- `Estabelecimento`: fronteira administrativa/fiscal;
- `UnidadeProdutiva`: fronteira operacional.

Arquitetura:

```text
Tenant
  ↓
Estabelecimento
  ↓
UnidadeProdutiva
  ↓
Talhões / Piquetes / Áreas
```

## 8. Papel do Tenant

- dono das integrações corporativas do cliente;
- fronteira principal de segurança e RLS;
- casa padrão das integrações ERP da v1;
- responsável pela configuração administrativa do cliente.

## 9. Papel da Matriz/Filial

- representar empresa, CNPJ, IE, IM, endereço fiscal e contexto administrativo;
- concentrar integrações que variam por estabelecimento;
- ser o escopo recomendado quando um tenant tiver múltiplos contextos fiscais.

## 10. Papel da Unidade Produtiva

- continuar exclusivamente como âncora operacional da fazenda;
- não receber credenciais ou configuração administrativa de ERP;
- apenas herdar o contexto administrativo do estabelecimento ao qual pertence.

## 11. Decisão oficial para cenários de arrendamento

Decisão:

- o AgroSaaS não precisa conhecer automaticamente o ERP do proprietário da área;
- a integração relevante é a do agente econômico que opera a safra;
- o sistema deve controlar contrato, custos, produção, rastreabilidade, financeiro e acertos do operador.

## 12. O que pode esperar

- implementação formal do domínio `Estabelecimento`;
- guardrails `INTEGRATIONS-GOV-01`;
- refatoração da navegação Sankhya;
- endurecimento de segredos e RLS específico no módulo.

## 13. Próxima execução sugerida

Próxima execução recomendada:

**INTEGRATIONS-GOV-01 — Guardrails do Domínio de Integrações**

Foco sugerido:

- proteção de escopos válidos;
- separação tenant/backoffice;
- regras para credenciais e masking;
- exigência de RLS ativo;
- RBAC oficial para integrações;
- aplicação inicial ao Sankhya.
