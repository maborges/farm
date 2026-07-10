# ERP-FACADE-03A - Relatorio de Execucao do Contrato da Superficie HTTP ERP

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: documentacao arquitetural, sem implementacao

## Resumo executivo

Esta execucao criou o documento normativo [ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-FACADE-03A-CONTRATO-SUPERFICIE-HTTP-ERP.md).

O contrato oficializa que a Superficie HTTP ERP:

- e uma camada fina de consumo e composicao;
- reutiliza integralmente o runtime oficial;
- nao cria novo runtime, novo dominio ou nova persistencia;
- nao substitui adapters;
- nao canoniza operacoes tecnicas provider-specific;
- preserva compatibilidade com `/api/v1/integracoes/sankhya/*`.

## Documentos revisados

### Relatorios de execucao

- [docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md)
- [docs/implementation/reports/ERP-FACADE-02-FASE-A-UI-ERP-GENERIC.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-02-FASE-A-UI-ERP-GENERIC.md)
- [docs/implementation/reports/ERP-FACADE-03-AUDITORIA-SUPERFICIE-HTTP.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-03-AUDITORIA-SUPERFICIE-HTTP.md)

### Documentos oficiais de arquitetura ERP

- [docs/architecture/ERP-ARCHITECTURE-INDEX.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-ARCHITECTURE-INDEX.md)
- [docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md)
- [docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md)
- [docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md)
- [docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md)
- [docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md)
- [docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md)

## Decisoes registradas

- a Superficie HTTP ERP foi registrada como camada fina de composicao, nunca como segundo runtime;
- o transporte HTTP ERP deve ficar acima do runtime oficial e abaixo dos consumidores genericos;
- as rotas candidatas ERP-generic foram documentadas apenas como alvo futuro da Fase B.1;
- `status`, `health`, `jobs`, `timeline`, `diagnostico`, `associacoes` e `readiness` foram definidos como conceitos validos da superficie ERP;
- autenticacao, gateway, OAuth, login legado, teste de conexao, sync tecnico, fiscal, financeiro, NFe, staging, payload mapping e erros especificos permaneceram oficialmente provider-specific;
- o conceito de resolvedor de provider ativo foi documentado sem implementacao;
- a compatibilidade com `/api/v1/integracoes/sankhya/*` foi preservada explicitamente.

## Itens fora de escopo

Nao foram criados:

- endpoints;
- routers;
- services;
- schemas;
- DTOs;
- migrations;
- models;
- adapters;
- jobs;
- runtime paralelo.

Nao foram alterados:

- backend;
- frontend;
- contratos HTTP em codigo;
- comportamento da plataforma.

## Riscos mitigados

### 1. Criacao de segunda arquitetura

Mitigacao:

- o documento proibe expressamente runtime paralelo, logica duplicada e persistencia propria da camada HTTP ERP.

### 2. Canonizacao indevida de operacoes provider-specific

Mitigacao:

- o contrato separa explicitamente leituras ERP genericas de operacoes tecnicas exclusivas do provider.

### 3. Contradicao com a arquitetura ERP existente

Mitigacao:

- o contrato foi alinhado com `ERP-DOMAIN-01`, `ERP-CONSOLE-01`, `ERP-GOV-02`, `ERP-CAPABILITY-01`, `ERP-PROVIDER-CONTRACT-02`, `ERP-CONSOLIDATION-03` e `ERP-ARCHITECTURE-INDEX`.

### 4. Depreciacao prematura de Sankhya

Mitigacao:

- o documento registra Sankhya como superficie de compatibilidade e fallback, sem depreciacao nesta fase.

## Proximos passos recomendados

- usar este contrato como base normativa da futura Fase B.1;
- implementar apenas endpoints ERP de composicao, com delegacao para servicos existentes;
- migrar `ErpConsole` e `ErpTimeline` gradualmente para a superficie HTTP ERP;
- manter convivio entre `/integracoes/erp/*` e `/integracoes/sankhya/*` enquanto houver consumidores ativos;
- adicionar testes de contrato quando a implementacao da Fase B.1 for iniciada.

## Comandos executados

```bash
sed -n '1,260p' docs/implementation/reports/ERP-FACADE-01-AUDITORIA-ARQUITETURAL.md
sed -n '1,260p' docs/implementation/reports/ERP-FACADE-02-FASE-A-UI-ERP-GENERIC.md
sed -n '1,320p' docs/implementation/reports/ERP-FACADE-03-AUDITORIA-SUPERFICIE-HTTP.md
rg --files docs/architecture | rg 'ERP-(DOMAIN-01|CONSOLE-01|GOV-02|CAPABILITY-01|PROVIDER-CONTRACT-02|CONSOLIDATION-03|ARCHITECTURE-INDEX)'
sed -n '1,260p' docs/architecture/ERP-ARCHITECTURE-INDEX.md
sed -n '1,260p' docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md
sed -n '1,260p' docs/architecture/ERP-GOV-02-GOVERNANCA-INTEGRACOES-ERP.md
sed -n '1,260p' docs/architecture/ERP-CAPABILITY-01-MODELO-CANONICO-CAPACIDADES-PROVIDERS-ERP.md
sed -n '1,260p' docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md
sed -n '1,260p' docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md
sed -n '1,220p' docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md
git diff --check
```

## Validacoes executadas

- validacao documental contra os relatorios `ERP-FACADE-01`, `ERP-FACADE-02` e `ERP-FACADE-03`;
- validacao normativa contra os documentos oficiais ERP em `docs/architecture`;
- nenhuma implementacao foi realizada;
- validacao final obrigatoria por `git diff --check`.
