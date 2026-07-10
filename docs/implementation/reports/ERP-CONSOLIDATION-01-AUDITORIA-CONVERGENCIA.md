# Relatório: Auditoria de Convergência e Eliminação de Duplicidades (ERP-CONSOLIDATION-01)

**Projeto**: ERP-CONSOLIDATION-01
**Tema**: Auditoria de Convergência da Arquitetura ERP
**Data da Auditoria**: 2026-07-10

---

## 1. Arquitetura Atual
A arquitetura de integrações do AgroSaaS foi originada com o framework ERP-First focado primeiramente no Sankhya, mas, nos últimos ciclos (ERP-UX-01 e 02), nós preparamos o terreno para a multi-integração e configurações genéricas através do `MarketplaceIntegracao`. Neste momento, o projeto está em uma transição onde possuímos componentes agnósticos (rotas `/erp/*`) convivendo lado a lado com as rotas monolíticas antigas (`/sankhya/*`). 

## 2. Fluxos Existentes e Duplicidades Encontradas

### Seleção do ERP
**Duplicidade:** Nenhuma.
O fluxo de seleção no Wizard foi consolidado corretamente. O texto livre foi extirpado, e hoje a escolha do ERP é gravada de forma estruturada.

### Configuração
**Duplicidade (Parcial):** 
No **backend**, o contrato declarativo injeta perfeitamente os schemas em `MarketplaceIntegracao`. Não criamos um segundo caminho de gravação (persistência).
No **frontend**, existe uma grande duplicidade. O arquivo `sankhya-console.tsx` ainda possui todos os inputs HTML (`sankhya_client_secret`, `sankhya_x_token`, etc.) hardcoded em tela. Ou seja, o schema declarativo criado na Fase ERP-UX-02A não está sendo utilizado para renderização dinâmica ainda, gerando duplicidade da "fôrma" de dados (uma no DB e outra na UI).

### Teste de Conexão
**Duplicidade (Endpoint):** 
Hoje o frontend aponta estaticamente para `POST /integracoes/sankhya/config/testar-conexao`. Não construímos um endpoint novo e genérico (ex: `/erp/testar-conexao`), e a UI está acoplada à URL direta do Sankhya.

### Readiness e Health
**Duplicidade:** Nenhuma.
O health e o readiness são atualizados centralmente no `ErpReadinessService` e `IntegrationHealth`. Não construímos fluxos duplicados aqui.

### Associação
**Duplicidade (Endpoint):** 
As associações sempre gravam usando o `ExternalRecordAssociation`, mas há uma duplicidade de superfície HTTP. O router genérico expõe `GET /erp/associacoes/pendentes` e `POST /erp/associacoes/{id}/reconciliar`. Contudo, o router do Sankhya `services/api/integracoes/sankhya/routers/__init__.py` mantém cópias de `GET /sankhya/associacoes/pendentes` e `POST /sankhya/associacoes/{id}/reconciliar`.

## 3. Código Morto e Obsoleto

Durante a auditoria, catalogamos o seguinte código sem propósito futuro:

- **Telas Incorretas:** O arquivo `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx` viola a regra arquitetural primária (`console de configuração não deve morar no backoffice`). A governança ocorre dentro do tenant.
- **Componentes React:** `erp-console.tsx` hoje faz um mero re-export de `sankhya-console.tsx`. O ideal é que `erp-console.tsx` torne-se o `DynamicErpConsole` universal e oficial, inutilizando a renderização manual presente em `sankhya-console`.
- **Endpoints Legados:** As rotas expostas em `/sankhya/timeline`, `/sankhya/diagnostico`, `/sankhya/jobs`, `/sankhya/associacoes/pendentes`, `/sankhya/associacoes/{id}/reconciliar` já são integralmente tratadas pela malha delegada oficial do `/erp/*`.
- **State Properties:** Propriedades como `escopo_carga_erp` (que o Wizard legava) foram depuradas pelo ERP-UX-01 e são lixo informacional se aparecerem em logs/payloads.

## 4. Responsabilidades Consolidadas e Fluxo Oficial Único

Para o futuro próximo, estas são as âncoras obrigatórias (SINGLE SOURCE OF TRUTH):

- **Seleção**: Utiliza exclusivamente `MarketplaceIntegracao` + Wizard (seleção estruturada).
- **Configuração**: Frontend genérico (`DynamicErpConsole` a ser construído no ERP-UX-02D) consome `/api/v1/integracoes/erp/providers/{slug}/schema`. Ao salvar, fará POST para um futuro `/api/v1/integracoes/erp/configuracao` comum, que resolve o adapter e orquestra a gravação de `IntegrationCredential` e `TenantIntegracao`. Nenhuma tela deve ter hardcode de propriedades (ex: "sankhya_client_id").
- **Persistência**: Existe e existirá apenas via Service agnóstico, protegendo credenciais usando a camada core de RLS.
- **Teste**: O teste de conexão precisará ser feito chamando `POST /api/v1/integracoes/erp/testar-conexao`, delegando ao adapter instanciado. O endpoint legado deve sumir.
- **Readiness**: O `ErpReadinessService` e suas rotas genéricas `/erp/status` e `/erp/health` são oficiais.
- **Associação**: Uso exclusivo das rotas de associação via `/api/v1/integracoes/erp/associacoes/*` orquestrando com a service `ExternalRecordAssociation`.
- **Sincronização**: Os pushes manuais de carga (sync pessoas, produtos) deverão ser movidos das URLs do Sankhya para `/api/v1/integracoes/erp/sync/{entity}` e delegados ao Canonical Adapter.
- **Observabilidade**: `/erp/timeline` e `/erp/jobs` são os guardiões exclusivos da telemetria, não devendo o frontend acessar rotas específicas de provider.

## 5. Recomendações e Conclusões

**O que permanece:**
- A arquitetura de base de dados: `MarketplaceIntegracao`, `TenantIntegracao`, `IntegrationCredential`, `ExternalRecordAssociation`.
- Todo o framework core `ErpReadinessService`.
- Os endpoints criados em `services/api/integracoes/erp/router.py`.

**O que deve ser adaptado:**
- A página do Console (frontend) precisa abandonar o formulário fixo estático (`sankhya-console.tsx`) e passar a ler, iterar e renderizar dinamicamente os inputs mapeados pelo schema (`ERP-UX-02D`).

**O que deve ser removido futuramente:**
- Todo e qualquer endpoint acessório da namespace `/sankhya/*` que possua correspondente genérico no `/erp/*` (`timeline`, `jobs`, `diagnostico`, `associacoes`, e eventualmente `/config`).
- A página de configuração no Backoffice.

**O que nunca deveria ter sido criado:**
- Endpoints de governança dentro do router nativo de um provider, pois criaram duplicação visual na documentação da API e acoplamento desnecessário, além de telas no módulo administrativo violando governança de Tenant.

**Conclusão Final:**
O fluxo oficial existe e está na superfície `/api/v1/integracoes/erp/*`. Daqui para frente, **qualquer** evolução (gravação de configuração, teste de conexão, disparo de sync) deve ocorrer exclusivamente inserindo rotas nesta superfície genérica, injetando o provider via Factory/Resolution interna do backend. 

Fim do Relatório. (GO - Pode avançar com os ajustes e próximas tasks sem gerar duplicações).
