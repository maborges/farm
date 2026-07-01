# INTEGRATIONS-ARCH-02 — Relatório de Providers, Conexões e Configurações

Data da execução: 2026-07-01

## 1. Resumo executivo

Foi criado o modelo canônico complementar do domínio de Integrações para resolver o problema central identificado nas auditorias anteriores:

- provedores reais, como Sankhya, possuem parâmetros específicos;
- esses parâmetros não podem contaminar o núcleo do domínio como se fossem universais.

Decisão central:

- o domínio de Integrações passa a separar `Provider`, `ProviderDefinition`, `Config`, `Connection`, `Credential`, `Feature`, `SyncPolicy` e `Health`.

## 2. Principais decisões arquiteturais

- `IntegrationProvider` é catálogo, não configuração do cliente.
- `IntegrationProviderDefinition` é a definição canônica dos schemas esperados.
- `IntegrationConnection` guarda parâmetros técnicos não secretos.
- `IntegrationCredential` guarda segredos e deve ter criptografia, masking, auditoria e rotação.
- `IntegrationFeature` representa capacidades habilitadas por configuração.
- `IntegrationSyncPolicy` representa como cada feature sincroniza.
- `IntegrationHealth` representa runtime operacional.
- Sankhya é apenas um provider, não a estrutura do domínio.

## 3. Como Sankhya se encaixa no modelo

Sankhya fica assim:

- `Provider`: Sankhya
- `ProviderDefinition`: declara schemas de conexão, credencial, feature, sync e health
- `Connection`: `gateway_url`, `service_urls`, `environment`, `timeout`, `company_code`
- `Credential`: `username`, `password`, `token`, se aplicável
- `Feature`: pessoas, produtos, financeiro, NFe, pedidos, estoque
- `SyncPolicy`: manual, agendado, por evento, outbox, conforme a feature
- `Health`: conexão, autenticação, último sync, erros recentes, falhas parciais

## 4. Como evitar acoplamento a um ERP específico

Regras oficiais definidas:

- campos como `gateway_url` não são universais do domínio;
- cada provider declara seu próprio schema;
- o domínio exige envelopes canônicos, não atributos fixos específicos;
- `Sankhya`, `SAP`, `TOTVS`, `SMTP`, `INMET` e `Banco do Brasil` usam a mesma arquitetura, mas com definições próprias.

## 5. Relação com INTEGRATIONS-ARCH-01

`INTEGRATIONS-ARCH-02` complementa `INTEGRATIONS-ARCH-01` sem contradizê-lo:

- mantém ERP por `TENANT` ou `ESTABELECIMENTO`;
- mantém ERP fora de `UnidadeProdutiva`;
- aprofunda somente a camada de modelagem canônica de configuração e runtime.

## 6. Limitações deliberadas da V1

- provedores existentes podem conviver com modelagem legada enquanto migram;
- health pode começar simplificado;
- policies podem começar com subset menor;
- versionamento detalhado de credenciais pode ser implementado em fases.

## 7. Próxima execução recomendada

Próxima execução:

**INTEGRATIONS-GOV-01 — Guardrails do Domínio de Integrações**

Objetivo sugerido:

- transformar `INTEGRATIONS-ARCH-01` e `INTEGRATIONS-ARCH-02` em regras de governança estática e operacional;
- proteger o domínio contra acoplamento a Sankhya ou qualquer outro provider específico;
- preparar a futura reestruturação governada da integração Sankhya.
