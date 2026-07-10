# ERP-LEGACY-01 - Auditoria Sankhya Legado

## 1. Objetivo

Auditar todas as estruturas `sankhya_*` e referências `Sankhya` no banco, backend, frontend, testes e documentação para classificar:

- o que deve permanecer como provider-specific legítimo;
- o que já é conceito genérico de ERP, mas ainda está preso ao Sankhya;
- o que pode permanecer temporariamente por compatibilidade;
- o que deve entrar em trilha de depreciação.

Esta execução é apenas auditoria e plano. Não houve implementação de correções, remoção de tabelas, migrations novas ou alteração de endpoints.

## 2. Escopo e método

Auditoria feita sobre:

- migrations;
- models;
- tabelas físicas declaradas no código;
- schemas;
- services;
- routers;
- frontend;
- testes;
- seeds/fixtures;
- docs e relatórios.

Consultas base usadas:

- busca textual por `sankhya`, `sankhya_*`, `Sankhya*` e `/integracoes/sankhya`;
- leitura dos arquivos ativos em `services/api`, `apps/web` e `docs`;
- confronto com o runtime oficial de integrações em `services/api/integracoes/models.py`;
- confronto com o serviço oficial de prontidão ERP em `services/api/integracoes/erp_readiness_service.py`.

Limite da auditoria:

- não houve leitura de banco de produção ou piloto;
- quando o relatório fala em "há indício de dados reais/piloto", isso é inferência documental a partir de `docs/pilot/` e dos relatórios já existentes;
- a confirmação final de volume real de dados exige inspeção do banco alvo.

## 3. Conclusão executiva

Conclusão principal:

- `Sankhya` já está corretamente posicionado na arquitetura como provider `ERP`.
- o runtime canônico de integrações já existe e é genérico:
  - `MarketplaceIntegracao`
  - `TenantIntegracao`
  - `IntegrationFeature`
  - `IntegrationSyncPolicy`
  - `IntegrationJob`
  - `IntegrationHealth`
  - `ExternalRecordAssociation`
- apesar disso, o provider Sankhya ainda mantém um runtime paralelo relevante:
  - `SankhyaConfig`
  - `SankhyaSyncLog`
  - staging `sankhya_*`
  - rotas `/integracoes/sankhya/*`
  - componentes frontend `SankhyaConsole` e `SankhyaTimeline`

Diagnóstico objetivo:

- staging `sankhya_*` é majoritariamente provider-specific legítimo;
- `SankhyaConfig` e `SankhyaSyncLog` são provider-specific, mas capturam parcialmente conceitos genéricos já materializados no domínio oficial;
- o maior acoplamento residual não está nas tabelas de staging, e sim no console ERP genérico do frontend e nos endpoints provider-first usados como fluxo oficial de ERP;
- existe rota legada web `/integracoes/sankhya` apenas como redirect, o que é aceitável como compatibilidade;
- `sankhya_tabelas` aparece modelada, mas sem evidência operacional equivalente no fluxo atual, sendo o melhor candidato à depreciação controlada.

## 4. Runtime oficial de ERP já existente

Estruturas oficiais já materializadas no domínio de integrações:

- `MarketplaceIntegracao`: catálogo oficial de providers;
- `TenantIntegracao`: configuração canônica por tenant/escopo;
- `IntegrationCredential`: credencial canônica;
- `IntegrationFeature`: capability matrix oficial;
- `IntegrationSyncPolicy`: política oficial de sincronização;
- `IntegrationJob`: job oficial;
- `IntegrationHealth`: health oficial;
- `ExternalRecordAssociation`: associação oficial entre registro local e externo;
- `ErpReadinessService`: consolidação oficial de prontidão ERP.

Arquivos base:

- `services/api/integracoes/models.py`
- `services/api/integracoes/erp_readiness_service.py`

Implicação arquitetural:

- qualquer status geral de ERP, readiness, capability matrix, health, políticas e governança de associação deve convergir para o domínio oficial;
- provider Sankhya deve fornecer adapter, credenciais provider-specific, mapeamento de payload e staging técnico, não uma arquitetura ERP paralela.

## 5. Inventário técnico consolidado

### 5.1 Diretório provider-specific ativo

Backend ativo do provider:

- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/external_association_helper.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/subscribers.py`
- `services/api/integracoes/sankhya/README.md`

Migrations:

- `services/api/migrations/versions/fase3_sankhya.py`
- `services/api/migrations/versions/20260704_sankhya_gateway_auth.py`
- `services/api/migrations/versions/20260709_sankhya_legacy_gateway_login.py`

Frontend ativo:

- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/app/integracoes/sankhya/page.tsx`
- `apps/web/src/app/integracoes/page.tsx`

Pontos espalhados fora do módulo:

- `services/api/main.py`
- `services/api/core/config.py`
- `services/api/core/routers/configuration.py`
- `apps/web/src/app/page.tsx`

### 5.2 Tabelas físicas `sankhya_*`

Encontradas em model e migration:

1. `sankhya_config`
2. `sankhya_sync_logs`
3. `sankhya_pessoas`
4. `sankhya_produtos`
5. `sankhya_nfe`
6. `sankhya_lancamentos_financeiros`
7. `sankhya_tabelas`

### 5.3 Rotas backend provider-first

Montagem:

- `services/api/main.py` inclui `sankhya_router` em `/api/v1/integracoes`

Prefixo efetivo:

- `/api/v1/integracoes/sankhya`

Endpoints encontrados:

- `POST /config`
- `GET /config`
- `POST /config/testar-conexao`
- `GET /status`
- `GET /health`
- `POST /sync/pessoas`
- `POST /sync/produtos`
- `POST /sync/completo`
- `GET /logs`
- `GET /jobs`
- `GET /timeline`
- `GET /diagnostico`
- `GET /pessoas`
- `GET /produtos`
- `POST /nfe/exportar`
- `POST /nfe/importar-entrada`
- `GET /nfe`
- `POST /financeiro/exportar-contas-pagar`
- `POST /financeiro/exportar-contas-receber`
- `POST /financeiro/importar`
- `GET /financeiro`
- `GET /associacoes/pendentes`
- `POST /associacoes/{association_id}/reconciliar`

### 5.4 Frontend Sankhya

Estruturas encontradas:

- rota legada web:
  - `apps/web/src/app/integracoes/sankhya/page.tsx`
- console oficial atual do tenant:
  - `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
  - internamente usa `SankhyaConsole`
- console de acompanhamento do backoffice:
  - `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
  - internamente usa `SankhyaTimeline`
- catálogo geral de integrações:
  - `apps/web/src/app/integracoes/page.tsx`
  - item listado como `ERP Sankhya`

### 5.5 Testes

Testes provider-specific reais:

- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_governance_router.py`

Testes genéricos que ainda validam acoplamentos Sankhya:

- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`
- `services/api/tests/unit/integracoes/test_external_record_association_service.py`

### 5.6 Seeds e fixtures

Não foram encontrados seeds operacionais dedicados a produção para Sankhya.

Foram encontrados apenas fixtures/helpers de teste:

- `_seed_runtime`
- `_seed_sankhya_runtime`
- `_seed_pending_association`
- `_seed_active_local_association`

Conclusão:

- não há seed de negócio principal a preservar;
- há fixtures de teste importantes e legítimas.

### 5.7 Documentação e relatórios

Grupos documentais encontrados:

- arquitetura:
  - `docs/architecture/INTEGRATIONS-ARCH-01.md`
  - `docs/architecture/INTEGRATIONS-ARCH-02.md`
  - `docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md`
  - `docs/architecture/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md`
  - `docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md`
  - `docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md`
  - `docs/architecture/ERP-CONSOLIDATION-03-AUDITORIA-FINAL-ARQUITETURA-ERP.md`
- piloto:
  - `docs/pilot/PILOT-ERP-02-ROTEIRO-EXECUCAO-ASSISTIDA-CAFE-SANKHYA.md`
  - `docs/pilot/GUIA-USUARIO-IMPLANTACAO-SAFRA-CAFE.md`
  - `docs/pilot/PLANO-MESTRE-PILOTO-01.md`
  - `docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`
  - `docs/pilot/CHECKLIST-CLIENTE-01-PREPARACAO-IMPLANTACAO.md`
- contextos e ownership:
  - `docs/contexts/step47-existing-modules-inventory-context.md`
  - `docs/contexts/step48-cross-module-ownership-context.md`
- relatórios de implementação:
  - família `SANKHYA-*`
  - família `ERP-*` com referências Sankhya
  - família `INTEGRATION-*` com referências a staging e adapter Sankhya

Diagnóstico documental:

- a documentação de arquitetura já afirma corretamente que Sankhya é provider;
- a documentação de piloto assume compatibilidade real e uso ativo do provider;
- parte dos relatórios ainda documenta o console e as APIs provider-first como fluxo principal.

## 6. Classificação por item

## 6.1 Provider-specific legítimo

Podem permanecer com nome Sankhya:

- diretório `services/api/integracoes/sankhya/*`
- `SankhyaGatewayAuthService`
- `SankhyaWSClient`
- `SankhyaCanonicalAdapter`
- `SankhyaExternalAssociationHelper`
- `SankhyaSyncEventSubscriber`
- campos de autenticação e conexão específicos:
  - `sankhya_environment`
  - `sankhya_api_base_url`
  - `sankhya_auth_url`
  - `sankhya_client_id`
  - `sankhya_client_secret`
  - `sankhya_x_token`
  - `sankhya_token`
  - `sankhya_appkey`
  - `ws_url`
  - `username`
  - `password`
- payloads e códigos externos específicos:
  - `CODPARC`
  - `CODPROD`
  - `CHAVEACESSO`
  - `DESDOB`
  - `CODNEG`
- testes específicos do provider
- documentação específica do provider e do piloto Sankhya

Justificativa:

- tudo isso representa protocolo, autenticação, contrato técnico ou staging de um provider concreto;
- não há ganho em esconder esses nomes atrás de abstrações artificiais enquanto o adapter continuar específico.

## 6.2 Genérico ERP preso ao Sankhya

Devem migrar gradualmente:

- console ERP oficial do tenant que usa `SankhyaConsole`
- painel de backoffice ERP que usa `SankhyaTimeline` e tipos `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaDiagnosis`
- endpoints provider-first usados para responder conceitos genéricos:
  - `/integracoes/sankhya/status`
  - `/integracoes/sankhya/health`
  - `/integracoes/sankhya/jobs`
  - `/integracoes/sankhya/timeline`
  - `/integracoes/sankhya/diagnostico`
  - `/integracoes/sankhya/associacoes/pendentes`
  - `/integracoes/sankhya/associacoes/{id}/reconciliar`
- contratos de frontend e schema que já carregam dados canônicos misturados em tipos `Sankhya*`
- `SankhyaConfigResponse` porque mistura:
  - dados provider-specific;
  - `provider_definition`;
  - `connection_schema`;
  - `credential_schema`;
  - `feature_schema`;
  - `sync_schema`;
  - `health_schema`
- `SankhyaSyncStatusResponse` porque mistura:
  - status legado;
  - health canônico;
  - readiness ERP;
  - policies resumidas
- uso de `SankhyaConfig` e `SankhyaSyncLog` como fonte indireta para:
  - status geral ERP;
  - health geral ERP;
  - execução geral ERP;
  - timeline geral ERP
- `services/api/core/config.py` com env vars Sankhya como se fossem configurações gerais do sistema, e não apenas do provider instalado
- `services/api/core/routers/configuration.py` importando `SankhyaSyncService` no módulo de configurações gerais

Justificativa:

- readiness, capability matrix, health, jobs, policies e governança de pendências já são capacidades do domínio oficial de integrações;
- elas não devem depender semanticamente de nomes `Sankhya*` no fluxo genérico de ERP.

## 6.3 Legado tolerado

Podem permanecer temporariamente por compatibilidade:

- `SankhyaConfig`
- `SankhyaSyncLog`
- rota web legada `apps/web/src/app/integracoes/sankhya/page.tsx` que redireciona para `/dashboard/settings/integracoes/erp`
- campos legados de autenticação:
  - `ws_url`
  - `username`
  - `password`
  - `token`
  - `appkey`
- fallbacks legados em status/health no `SankhyaSyncService`
- tabelas de staging já consolidadas no piloto:
  - `sankhya_pessoas`
  - `sankhya_produtos`
  - `sankhya_nfe`
  - `sankhya_lancamentos_financeiros`

Justificativa:

- existem relatórios e documentos de piloto assumindo uso real dessas estruturas;
- há testes específicos cobrindo sua preservação;
- remover agora criaria risco direto de quebra de compatibilidade do piloto e da governança operacional já documentada.

## 6.4 Candidato à depreciação

Não deve receber novas funcionalidades:

- `sankhya_tabelas`
- qualquer nova rota ERP genérica criada sob `/integracoes/sankhya/*`
- qualquer novo componente genérico ERP batizado como `Sankhya*`
- qualquer nova tela genérica de observabilidade ERP consumindo diretamente endpoints Sankhya
- qualquer uso novo de `SankhyaConfig` para representar status/health/policy geral
- qualquer nova documentação tratando Sankhya como arquitetura base

Justificativa:

- `sankhya_tabelas` tem modelo e migration, mas não há evidência operacional equivalente no fluxo atual;
- expandir o console ERP genérico sobre endpoints provider-first aumenta dívida;
- o runtime canônico já existe e deve ser o ponto de expansão.

## 7. Matriz obrigatória por tabela `sankhya_*`

## 7.1 `sankhya_config`

Classificação:

- `Provider-specific legítimo`
- com partes `Genérico ERP preso ao Sankhya`
- e `Legado tolerado`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Ambos.
   - Específico: credenciais e formas de autenticação do Gateway/WS.
   - Genérico preso: `ativo`, `ultimo_teste`, `teste_status`, `sync_interval`, `ultimo_sync`.
2. Existe equivalente no runtime oficial?
   - Sim.
   - `TenantIntegracao`, `IntegrationCredential`, `IntegrationHealth`, `IntegrationSyncPolicy`.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Lida e escrita intensivamente por `SankhyaSyncService`, `canonical_adapter`, `auth_service`, `nfe_financeiro_service`, `external_association_helper` e testes.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
   - A documentação do piloto e múltiplos relatórios assumem configuração ativa do provider.
5. Pode ser migrada?
   - Sim, parcialmente.
   - Credenciais e conexão podem convergir para `TenantIntegracao` + `IntegrationCredential`.
   - Health/policy podem sair do legado.
6. Pode ser depreciada?
   - Sim, apenas após convergência e camada de compatibilidade.
7. Remover agora quebraria algo?
   - Sim.
   - Quebraria console, teste de conexão, sync manual, subscriber, adapter e testes.

Decisão recomendada:

- manter no curto prazo;
- não expandir responsabilidades genéricas;
- iniciar convergência do que é health, policy e lifecycle para o runtime oficial.

Risco:

- médio/alto.

## 7.2 `sankhya_sync_logs`

Classificação:

- `Provider-specific legítimo`
- `Legado tolerado`
- com partes `Genérico ERP preso ao Sankhya`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Misto.
   - É log operacional do provider, mas captura conceito genérico de execução de integração.
2. Existe equivalente no runtime oficial?
   - Sim.
   - `IntegrationJob` e parcialmente `IntegrationHealth`.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Escrita por `iniciar_sync_log` e `finalizar_sync_log`.
   - Lida por `/logs`, timeline, diagnósticos e correlação com jobs oficiais.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
   - A timeline, a documentação de monitoramento e os runbooks citam esse log.
5. Pode ser migrada?
   - Sim.
   - Pode virar trilha secundária ou view materializada/adapter sobre `IntegrationJob`.
6. Pode ser depreciada?
   - Sim, depois de manter a rastreabilidade operacional no domínio oficial.
7. Remover agora quebraria algo?
   - Sim.
   - Quebraria logs, timeline, parte do diagnóstico e testes.

Decisão recomendada:

- manter temporariamente;
- não criar novos conceitos genéricos em cima dela;
- migrar a visão principal de execução para `IntegrationJob`.

Risco:

- médio.

## 7.3 `sankhya_pessoas`

Classificação:

- `Provider-specific legítimo`
- `Legado tolerado`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Predominantemente específico do provider.
   - É staging/espelho técnico de parceiros do ERP.
2. Existe equivalente no runtime oficial?
   - Sim, mas não como staging.
   - Equivalente de entidade oficial é `Pessoa` no core e `ExternalRecordAssociation` para vínculo oficial.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Escrita por `SankhyaPessoaService.importar_pessoas`.
   - Lida por endpoints `/pessoas`, helper de associações e testes.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
5. Pode ser migrada?
   - Não no sentido de renomear agora.
   - O correto é manter staging e adicionar/usar vínculo oficial com `Pessoa`.
6. Pode ser depreciada?
   - Não no curto prazo.
   - Só quando o staging deixar de ser necessário, o que não é o caso atual.
7. Remover agora quebraria algo?
   - Sim.

Decisão recomendada:

- manter como staging provider-specific;
- proibir que vire fonte oficial de `Pessoa`.

Risco:

- baixo para manter;
- alto para remover.

## 7.4 `sankhya_produtos`

Classificação:

- `Provider-specific legítimo`
- `Legado tolerado`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Predominantemente específico do provider como staging.
2. Existe equivalente no runtime oficial?
   - Sim.
   - Entidade oficial: `Produto`.
   - Vínculo oficial: `ExternalRecordAssociation`.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Escrita por `SankhyaProdutoService.importar_produtos`.
   - Lida por endpoints `/produtos`, helper e testes.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
5. Pode ser migrada?
   - Não como rename imediato.
   - A evolução correta é manter staging e formalizar vínculo com `Produto`.
6. Pode ser depreciada?
   - Não no curto prazo.
7. Remover agora quebraria algo?
   - Sim.

Decisão recomendada:

- manter como staging;
- não usar como fonte oficial de produto.

Risco:

- baixo para manter;
- alto para remover.

## 7.5 `sankhya_nfe`

Classificação:

- `Provider-specific legítimo`
- `Legado tolerado`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Predominantemente específico do provider como staging fiscal.
2. Existe equivalente no runtime oficial?
   - Parcial.
   - Entidade oficial local: `NotaFiscal`.
   - Vínculo oficial ainda depende de associação externa persistida.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Lida e escrita por `SankhyaNFeService`.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
5. Pode ser migrada?
   - Não como rename imediato.
   - Deve coexistir com vínculo oficial por `CHAVEACESSO`.
6. Pode ser depreciada?
   - Não no curto prazo.
7. Remover agora quebraria algo?
   - Sim.

Decisão recomendada:

- manter staging fiscal;
- migrar o vínculo oficial para associação externa, não para renome de tabela agora.

Risco:

- médio.

## 7.6 `sankhya_lancamentos_financeiros`

Classificação:

- `Provider-specific legítimo`
- `Legado tolerado`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Predominantemente específico do provider como staging financeiro.
2. Existe equivalente no runtime oficial?
   - Parcial.
   - Entidades oficiais locais: `Despesa` e `Receita`.
   - Associação externa oficial ainda precisa ser a referência forte.
3. A tabela ainda é lida/escrita?
   - Sim.
   - Lida e escrita por `SankhyaFinanceiroService`.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Indício forte de sim.
5. Pode ser migrada?
   - Não no curto prazo.
   - Antes disso, precisa fortalecer a identidade externa além de `DESDOB`.
6. Pode ser depreciada?
   - Não agora.
7. Remover agora quebraria algo?
   - Sim.

Decisão recomendada:

- manter como staging financeiro;
- evitar expandir seu uso para representar financeiro oficial do ERP.

Risco:

- médio/alto.

## 7.7 `sankhya_tabelas`

Classificação:

- `Candidato à depreciação`

Resposta obrigatória:

1. Guarda dado específico do Sankhya ou genérico ERP?
   - Específico do provider e auxiliar.
2. Existe equivalente no runtime oficial?
   - Não diretamente.
   - Também não há evidência de uso real consolidado.
3. A tabela ainda é lida/escrita?
   - Não encontrei evidência operacional ativa.
   - Há model e migration, mas não fluxo de sync correspondente no backend ativo.
4. Há dados em produção ou piloto que exigem compatibilidade?
   - Não verificável localmente.
   - Indício documental fraco em comparação às demais tabelas.
5. Pode ser migrada?
   - Sim, se existir dado real.
6. Pode ser depreciada?
   - Sim, é o melhor candidato.
7. Remover agora quebraria algo?
   - Não há evidência forte de quebra imediata pelo código atual, mas sem inspeção do banco alvo não é seguro remover já.

Decisão recomendada:

- congelar;
- não adicionar novas features;
- auditar existência real de dados antes de qualquer remoção.

Risco:

- baixo/médio.

## 8. Classificação por rotas

## 8.1 Provider-specific legítimas

- `/integracoes/sankhya/config`
- `/integracoes/sankhya/config/testar-conexao`
- `/integracoes/sankhya/sync/pessoas`
- `/integracoes/sankhya/sync/produtos`
- `/integracoes/sankhya/sync/completo`
- `/integracoes/sankhya/pessoas`
- `/integracoes/sankhya/produtos`
- `/integracoes/sankhya/nfe/exportar`
- `/integracoes/sankhya/nfe/importar-entrada`
- `/integracoes/sankhya/nfe`
- `/integracoes/sankhya/financeiro/exportar-contas-pagar`
- `/integracoes/sankhya/financeiro/exportar-contas-receber`
- `/integracoes/sankhya/financeiro/importar`
- `/integracoes/sankhya/financeiro`

Motivo:

- são operações do adapter e do staging do provider atual.

## 8.2 Genérico ERP preso ao Sankhya

- `/integracoes/sankhya/status`
- `/integracoes/sankhya/health`
- `/integracoes/sankhya/jobs`
- `/integracoes/sankhya/timeline`
- `/integracoes/sankhya/diagnostico`
- `/integracoes/sankhya/associacoes/pendentes`
- `/integracoes/sankhya/associacoes/{association_id}/reconciliar`

Motivo:

- representam conceitos genéricos de operação ERP, observabilidade e governança de associação;
- hoje existem porque o provider Sankhya foi o primeiro caso real, mas já não deveriam ser o único contrato consumido pelas telas genéricas de ERP.

## 8.3 Legado tolerado

- rota web `/integracoes/sankhya` com redirect para `/dashboard/settings/integracoes/erp`

## 9. Classificação por services e models

## 9.1 Permanecer provider-specific

- `SankhyaGatewayAuthService`
- `SankhyaWSClient`
- `SankhyaCanonicalAdapter`
- `SankhyaExternalAssociationHelper`
- `SankhyaPessoaService`
- `SankhyaProdutoService`
- `SankhyaNFeService`
- `SankhyaFinanceiroService`
- `SankhyaSyncEventSubscriber`
- models de staging:
  - `SankhyaPessoa`
  - `SankhyaProduto`
  - `SankhyaNFe`
  - `SankhyaLancamentoFinanceiro`

## 9.2 Devem convergir

- `SankhyaConfigSerializer`
- `SankhyaConfigResponse`
- `SankhyaSyncStatusResponse`
- `SankhyaHealthResponse`
- `SankhyaOperationalDiagnosisResponse`
- partes de `SankhyaSyncService` que calculam:
  - status geral;
  - health geral;
  - readiness;
  - timeline consolidada;
  - correlação com `IntegrationJob` e `IntegrationHealth`

Motivo:

- esses objetos já vivem na fronteira entre provider-specific e domínio ERP canônico;
- devem ser consumidos por uma camada ERP genérica, mesmo que internamente ainda consultem Sankhya por compatibilidade.

## 10. Classificação por frontend

## 10.1 Provider-specific legítimo

- `apps/web/src/app/integracoes/sankhya/page.tsx`
  - apenas compatibilidade/redirect
- item "ERP Sankhya" no catálogo de integrações
- marketing/copy que cita Sankhya como exemplo de provider real

## 10.2 Genérico ERP preso ao Sankhya

- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`

Motivo:

- o nome da tela já é ERP genérico;
- a experiência continua inteiramente ancorada em componente, tipos e endpoints `Sankhya*`.

Decisão recomendada:

- o console ERP do tenant deve virar componente genérico, por exemplo `ErpProviderConsole`, com provider atual `sankhya`;
- `SankhyaConsole` deve sobreviver apenas como adapter/view provider-specific até a migração.

## 11. Classificação por testes

## 11.1 Provider-specific legítimos

- toda suíte `test_sankhya_*`

Motivo:

- valida adapter, auth, staging, rotas do provider e governança de associações do provider.

## 11.2 Genéricos ERP ainda com acoplamento Sankhya

- `test_erp_readiness_service.py`
- partes de `test_integrations_architecture_guardrails.py`
- partes de `test_integrations_foundation_models.py`
- partes de `test_integrations_operational_models.py`

Motivo:

- readiness e guardrails ERP não deveriam depender nominalmente do provider atual para sempre;
- a cobertura é válida, mas o naming e parte das expectativas devem migrar junto com o console e os endpoints genéricos.

## 12. Riscos de migração

### Baixo risco

- texto de UI que ainda fala "console Sankhya" dentro de telas genéricas ERP;
- links e breadcrumbs;
- documentação que ainda descreve o fluxo genérico como Sankhya-first;
- nome técnico de tipos TS internos do frontend;
- inclusão de avisos claros de compatibilidade/depreciação.

### Médio risco

- trocar telas genéricas ERP para consumir um façade/endpoint genérico mantendo proxy para Sankhya;
- reduzir dependência direta de `SankhyaConfig` para status, health e readiness;
- mover parte da visão de jobs/timeline para `IntegrationJob` e `IntegrationHealth`;
- manter as rotas `/integracoes/sankhya/*` apenas como compatibilidade/adapter.

### Alto risco

- migrar dados de `sankhya_config` para `tenant_integracoes` e `integration_credentials` sem lacuna;
- migrar ou aposentar `sankhya_sync_logs`;
- tentar renomear tabelas `sankhya_*`;
- remover rotas atuais antes de trocar consumidores;
- alterar a identidade de staging fiscal e financeiro antes de consolidar `ExternalRecordAssociation`.

## 13. Plano de correção em fases

## Fase A - Baixo risco

- renomear textos de UI genérica de ERP para não depender de "Sankhya" quando a tela é multi-provider;
- evitar novas referências `Sankhya-first` em componentes genéricos, rotas genéricas e documentação genérica;
- documentar formalmente:
  - `SankhyaConfig` e `SankhyaSyncLog` como legado tolerado;
  - `sankhya_tabelas` como congelada/deprecação candidata;
  - `/integracoes/sankhya` web como compatibilidade;
- registrar guideline:
  - staging provider-specific pode continuar;
  - conceitos de readiness, health, jobs e governança devem nascer no domínio ERP oficial.

## Fase B - Médio risco

- criar camada de leitura ERP genérica para:
  - readiness;
  - status;
  - health;
  - jobs;
  - timeline;
  - pendências de associação;
- fazer as telas `/dashboard/settings/integracoes/erp` e `/dashboard/backoffice/integracoes/erp` consumirem contrato ERP genérico;
- manter internamente Sankhya como provider atual por adapter;
- manter rotas `/integracoes/sankhya/*` funcionando como compatibilidade;
- reduzir dependência direta de `SankhyaConfigResponse` como contrato principal da tela genérica.

## Fase C - Alto risco

- migrar o que for genérico de `SankhyaConfig` para `TenantIntegracao` + `IntegrationCredential` + `IntegrationHealth` + `IntegrationSyncPolicy`;
- reduzir `SankhyaSyncLog` a papel estritamente provider/audit trail ou substituí-lo por visão unificada oficial;
- avaliar remoção controlada de campos legados:
  - `ws_url`
  - `username`
  - `password`
  - `token`
  - `appkey`
- auditar existência real de dados em `sankhya_tabelas` e decidir desativação/remoção;
- só depois disso considerar remoção de endpoints antigos e eventual simplificação de models legados.

## 14. Decisões recomendadas por item-chave

### `SankhyaConfig`

- manter agora;
- não expandir;
- convergir gradualmente para runtime oficial.

### `SankhyaSyncLog`

- manter agora;
- parar de tratá-lo como modelo principal de execução ERP;
- convergir visão principal para `IntegrationJob`.

### Staging `sankhya_pessoas`, `sankhya_produtos`, `sankhya_nfe`, `sankhya_lancamentos_financeiros`

- manter com nome Sankhya;
- continuar como staging técnico;
- proibir promoção a fonte oficial de negócio.

### `sankhya_tabelas`

- congelar;
- não ampliar;
- auditar banco real antes de qualquer remoção.

### Console ERP do frontend

- hoje é genérico no rótulo, mas Sankhya no contrato;
- deve ser o primeiro alvo de generalização sem quebrar compatibilidade.

## 15. Resposta objetiva: o que é legado, o que é específico e o que precisa generalizar

Específico do provider e correto:

- adapter;
- autenticação;
- staging técnico;
- códigos externos;
- testes técnicos do provider;
- documentação do piloto Sankhya.

Legado tolerado:

- `SankhyaConfig`;
- `SankhyaSyncLog`;
- campos de login legado;
- rota web legada com redirect.

Precisa generalizar:

- status ERP;
- health ERP;
- jobs/timeline ERP;
- readiness ERP;
- capability matrix ERP;
- console ERP do tenant;
- painel ERP do backoffice;
- governança genérica de associações quando exibida por telas ERP genéricas.

Candidato claro à depreciação:

- `sankhya_tabelas`;
- qualquer nova materialização genérica feita diretamente sob `Sankhya*`.

## 16. Validação

Alteração realizada nesta execução:

- criação deste relatório documental.

Validação obrigatória a executar após a criação do arquivo:

- `git diff --check`

