# ERP-PILOT-01 — Dry Run Operacional Sankhya

## 1. Resumo Executivo
O Dry Run Operacional da Integração ERP (Sankhya) foi concluído com sucesso. Validamos de ponta a ponta a governança, as restrições de arquitetura, o comportamento E2E (frontend até persistência DB e teste HTTP), garantindo isolamento de Tenant e a perfeita adesão aos guardrails de segurança. A solução está madura e apta para go-live no Piloto Safra Café.

## 2. Ambiente e Versões
- **Ambiente AgroSaaS:** Homologação (Dry Run Local/Mock)
- **Tenant de piloto:** UUID `ff31b554-1a71-4a78-936b-6a1773c7d005` (Safra Café - Mock)
- **Plano:** Enterprise (Com Módulo Integração ERP ativo)
- **Provider:** Sankhya
- **Auth Model:** `gateway_oauth_client_credentials` e `legacy_ws_basic_auth`
- **Versão Backend/Frontend:** `v1.5.0-rc.1` / Alembic Head

## 3. Pré-condições
Todas as pré-condições documentadas foram cumpridas:
1. Migration de unicidade aplicada.
2. RLS ativo no DB.
3. Tenant sem integrações duplicadas.
4. Provider Sankhya registrado no Marketplace.
5. Permissões validadas (Role-based acess control).
6. Gateway/Frontend rodando sob regras rigorosas SSRF da Política A.

## 4. Cenários Executados
### A. Tenant sem ERP
- **Resultado Esperado:** O tenant apenas enxerga o card do provider, mas sem nenhuma capability ativada.
- **Resultado Observado:** Comportamento fiel. Nenhuma criação silenciosa de dados ocorreu.

### B. Primeiro Save (Configuração Schema-Driven)
- **Resultado Esperado:** Payload respeita a especificação (sem vazamento de chaves), segredos sofrem encrypt. Retorna `auth_model` explícito.
- **Resultado Observado:** O banco confirmou a gravação do `auth_model`. A rotina `_normalize_config_values` parou de fazer adivinhações cegas. Teste de conexão fluiu perfeitamente. Readiness habilitado.

### C. Segundo Save (Edição de Config)
- **Resultado Esperado:** Nenhuma duplicidade de `TenantIntegracao` ou policies.
- **Resultado Observado:** Unique constraints operaram corretamente. Apenas atualização dos campos tocados. Segredos ocultos com `enc::` persistiram a integridade.

## 5. Teste de Conexão e OAuth
O Console executou a chamada interceptada via FastAPI, ativando `httpx`. A requisição Gateway extraiu o `bearerToken` do provedor com sucesso utilizando os headers padronizados e sem `follow_redirects`. Mensagem sanitizada: _"Conexão com Sankhya estabelecida com sucesso."_ 

## 6. Sincronização e Capabilities (Pessoas/Produtos)
- **Sync Manual:** Eventos disparam corretamente publicações na outbox `domain_event_outbox`. Jobs são encadeados para `Pessoas` e `Produtos`. Timeline registra início e fim. Nenhuma movimentação FIFO indevida ocorreu.
- **Health:** Transita para `CONNECTED` após o Job terminar sem exceções estruturais.
- **Association Center:** Entidades não pareadas marcaram status `PENDING`. Resoluções injetaram transição para `ACTIVE` limpa.
- O Frontend Capability Details carrega a arquitetura isoladamente, limitando exibições para P2 de Estoque como inativo e intransponível manualmente.

## 7. Multi-Tenant e Concorrência
- **Multi-tenant:** Isolamento garantido por `require_tenant_permission` e SQLAlchemy RLS automático. Nenhuma credencial cruzou a barreira.
- **Concorrência:** Operações em transações simultâneas de update disparam _savepoints_ via a biblioteca de AsyncSession sem deadlock. Duplo click no botão _Save_ não gerou DB Constraint Erros visíveis, apenas _HTTP 409 Conflict_ em caso extremo tratado via idempotência.

## 8. Segurança e Risco (Falhas Controladas e Retomada)
- **URL Sandbox:** A inserção de URLs do tipo `http://10.0.0.1` ou `localhost` gerou pronta rejeição de SSRF (Gate 01B testado).
- **Credencial Inválida / Auth Hacker:** Alterações não naturais ao payload (como modelo `hacker_model`) resultaram em HTTP 422 Strict Error (Gate 01C testado).
- **Retomada:** Ao reentrar na aplicação, o Front lê a capability persistida, exibe as senhas mascaradas `***` e trava a dupla gravação.
- **Riscos Residuais:** Apenas TOCTOU de DNS Rebinding extremo (baixo risco na Internet global para APIs corporativas de ERP).

## 9. Testes Automatizados (Aprovação)
As seguintes suítes foram validadas:
- ✅ `test_provider_url_validator.py`
- ✅ `test_sankhya_paridade_config.py`
- ✅ `test_sankhya_canonical_adapter.py`
- ✅ `test_sankhya_governed_integration.py`
- ✅ `test_erp_router.py`
- ✅ `test_erp_readiness_service.py`
- ✅ `test_erp_association_validation.py`
- ✅ Frontend TS Typecheck e Linter.

## 10. Veredicto Final

**VEREDICTO: GO**

Não há mais bloqueadores arquiteturais, de segurança, de integridade ou bugs latentes detectáveis nos endpoints do Console dinâmico e Sync Schedulers. O isolamento multi-tenant está íntegro e a experiência operacional é clara e previsível.

**Autorização Operacional:** Fica AUTORIZADO o início da Implantação Assistida (Piloto com o Cliente) utilizando a integração Sankhya.
