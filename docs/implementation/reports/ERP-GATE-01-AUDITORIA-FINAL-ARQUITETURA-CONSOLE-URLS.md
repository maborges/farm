# ERP-GATE-01 - Auditoria Final: Arquitetura, Console e Configuração de URLs

## 1. Resumo Executivo
A infraestrutura backend (APIs canônicas, capability center, schemas e adapters) está consistente e alinhada à arquitetura ERP-First do AgroSaaS. O fluxo usa a configuração persistida para as rotas e testes, sem divergência oculta de fallback perigoso no runtime.

Contudo, a auditoria detectou um **Bloqueador de Piloto** (`PILOT_BLOCKER`) puramente no Frontend: a tela oficial `DynamicErpConsole` consome e renderiza o schema perfeitamente, **mas realiza um filtro hardcode** das chaves durante o salvamento (`handleSave()`). Campos essenciais (como `auth_model` e `ws_url`) e quaisquer configurações futuras de outros provedores são **ignoradas pelo backend porque nunca são enviadas**.

---

## 2. Escopo
* **Frontend:** `apps/web/src/components/integracoes/erp-console.tsx` e `sankhya-console.tsx`
* **Router:** `services/api/integracoes/erp/router.py`
* **Auth & Sync Services:** `services/api/integracoes/sankhya/services/auth_service.py` e `sync_service.py`
* **Adapter:** `services/api/integracoes/sankhya/services/canonical_adapter.py`

Nenhum código produtivo foi modificado nesta execução.

---

## 3. Arquitetura Atual
* **UI Config:** Console dinâmico de ERP com abas de diagnóstico, timeline e formulário schema-driven.
* **Schema Provider:** Backend fornece metadados (JSON) contendo quais campos são necessários (ex: URL, client_id).
* **Testes & Auth:** A autenticação e o `SankhyaSyncService` buscam de `SankhyaConfig` e `TenantIntegracao`.
* **Centralização:** O teste de conexão chama a mesma fábrica de configuração que o próprio runtime (SSOT).

---

## 4. Fluxo Oficial e 5. Inventário de Telas
A jornada oficial é confirmada:
`/dashboard/settings/integracoes/erp` → `ErpProviderSelector` → `SankhyaConsole` → `DynamicErpConsole`.

**Componentes:**
* `DynamicErpConsole` (`erp-console.tsx`): Console oficial principal.
* `SankhyaConsole` (`sankhya-console.tsx`): Wrapper que instila o `providerSlug="sankhya"` e endpoints específicos.
* **Telas paralelas concorrentes?** Nenhuma encontrada, tudo converge para o `ErpConsole`.
* **Backoffice?** Existem wrappers antigos possivelmente listando endpoints, mas a configuração RLS e persistência canônica do Tenant ocorrem via `ErpConsole`.

---

## 6. Inventário de Campos e Schema do Provider
Obtidos no `canonical_adapter.py` (`connection_schema` e `credential_schema`):

| Campo | Tipo | Obrigatório | Sensível | Editável | Exibido na UI | Persistido | Utilizado no runtime |
|---|---|---|---|---|---|---|---|
| sankhya_environment | Select | Sim | Não | Sim | Sim | Sim | Sim |
| sankhya_api_base_url | URL | Sim | Não | Sim | Sim | Sim | Sim |
| sankhya_auth_url | URL | Sim | Não | Sim | Sim | Sim | Sim |
| auth_model | Select | Não | Não | Sim | Sim | **NÃO** | *Fallback (Default)* |
| sync_interval | Int | Sim | Não | Sim | Sim | Sim | Sim |
| ws_url | URL | Não | Não | Sim | Sim | **NÃO** | *Ignorado* |
| sankhya_client_id | String | Sim | Não | Sim | Sim | Sim | Sim |
| sankhya_client_secret | String | Não | Sim | Sim | Sim | Sim | Sim |
| sankhya_x_token | String | Não | Sim | Sim | Sim | Sim | Sim |

*Nota sobre a persistência:* Embora o backend aceite as propriedades omitidas, o frontend aplica um filtro que barra seu envio na função `handleSave()`.

---

## 7. URLs Encontradas e Classificação
1. `sankhya_api_base_url`: `TENANT_CONFIGURABLE` (Para os casos onde cada cliente pode ter seu MGE).
2. `sankhya_auth_url`: `TENANT_CONFIGURABLE` (Não derivada no backend; exige payload explícito).
3. `ws_url`: `LEGACY_TOLERATED` (Descontinuado via gateway, mas essencial para compatibilidade retroativa, retido no client filter).

---

## 8. Gateway OAuth e 9. Login Legado
Os fluxos reais processados pelo `SankhyaGatewayAuthService` dependem de:
* `gateway_oauth_client_credentials`: Necessita de client ID, Secret e X-Token (Default).
* `gateway_legacy_login`: Necessita de credenciais de login legadas (Usuário/Senha/Token/Appkey).

Como a UI descarta a escolha em `auth_model`, ele não é salvo. Consequentemente, o Tenant legados nunca conseguirão operar.

---

## 10. Jornada de Configuração de URLs
**Provider schema** → Envia `sankhya_api_base_url`, `auth_model`, etc.  
**Campo aparece no DynamicErpConsole** → Evidência: `fields.map(renderField)`  
**Usuário informa valor** → Set no `formData`  
**Frontend envia payload** → **FALHA (Lacuna)**. `handleSave()` força `sankhya_...` keys e ignora as demais (`auth_model` / `ws_url`).  
**Backend valida e persiste** → Funciona para os campos enviados.  
**Teste de conexão** → Funciona lendo do que foi salvo, mas não diagnostica a escolha correta.

---

## 11. Comparação Teste × Sync
**Sem divergência.** O `testar_conexao` acessa `await sync_service.testar_conexao(str(tenant_id))` e a API sequer recebe body do payload da interface para testar um "estado não salvo". Ele usa o estado canonizado no Banco de Dados. Isso previne falsos positivos, mas reforça que a edição só testa depois de salva.

---

## 12. Ambientes
É possível configurar `PRODUCAO`, `HOMOLOGACAO` e `SANDBOX` via `sankhya_environment`, refletido em UI. Não detectada trava no backend que restrinja o consumo cruzado, exceto a isolação lógica.

---

## 13. Segurança e SSRF
Risco classificado como **SECURITY_RISK (Moderado/SSRF)**. Como `api_base_url` e `auth_url` são inputados abertamente sem validação de URL interna/IP, o servidor pode efetuar chamadas (via `httpx` no Auth Service) a localhost/hosts privados. 

---

## 14. Hardcodes Encontrados
- **PILOT_BLOCKER / HARDCODE_RISK:** `erp-console.tsx:300` - `handleSave()` cria um objeto literal fechado:
  ```javascript
  sankhya_environment: formData.sankhya_environment,
  sankhya_api_base_url: formData.sankhya_api_base_url,
  // ignora auth_model e todos os demais dinâmicos!
  ```
Isso aniquila o suporte ao 2º ERP (exigiria alteração no `DynamicErpConsole` inteiro) e impossibilita o login legado no Sankhya.

---

## 15. Duplicações
`sankhya_api_base_url` e `sankhya_auth_url` estão desnormalizados perante a unificação (não estão centralizados como genéricos no schema universal), porém classificado como `PROVIDER_SPECIFIC` tolerável por hora para este estágio do ERP.

---

## 16. Segundo ERP
Adicionar o segundo ERP **EXIGIRIA ALTERAÇÃO NO CONSOLE**. O `DynamicErpConsole` (que deveria ser genérico) tem as keys do Sankhya amarradas ao seu fluxo de Save (`handleSave`), sendo classificado como **Bloqueio Arquitetural** no Frontend.

---

## 17. Matriz de Prontidão

| Área | Implementada | Interface existente | API existente | Runtime utiliza | Lacuna |
|---|---|---|---|---|---|
| Seleção de provider | Sim | Sim | Sim | Sim | - |
| Configuração de ambiente | Sim | Sim | Sim | Sim | - |
| URL base Gateway | Sim | Sim | Sim | Sim | - |
| URL de autenticação | Sim | Sim | Sim | Sim | - |
| Login legado | **Não (Bloqueio UI)** | Sim | Sim | Sim | Hardcode em `handleSave` descarta a variável |
| OAuth Gateway | Sim | Sim | Sim | Sim | Funciona por ser fallback nativo da API. |
| Credenciais | Parcial | Sim | Sim | Sim | Ocultas e renderizadas, mas fields extras bloqueados |
| Teste de conexão | Sim | Sim | Sim | Sim | Usa db e não formData (sem falsos-positivos) |

---

## 18. Veredicto Final

**NO-GO**

Embora o backend seja perfeitamente modelado e orquestre as responsabilidades adequadamente (SSOT para Testes, Auth e Sync), as falhas contundentes na interface inviabilizam testes piloto em Tenants que não adiram ao Default Gateway OAuth. O acoplamento provider-specific no core do `DynamicErpConsole` desqualifica a promessa de plugar um 2º ERP (como Protheus) sem novas quebras.

## 19. Correção Imediata Recomendada (ERP-GATE-01A)
Modificar o frontend (`apps/web/src/components/integracoes/erp-console.tsx`) para enviar a carga inteira ou filtrar iterando sobre as chaves do schema.
```javascript
// Onde lê-se o destructuring manual:
const payload = formData; // (com filtros adequados baseados no schema.fields)
```

## 20. Validação Documental
Nenhum código do Backend foi alterado. Nenhum endpoint adicionado. O repositório segue em integridade, comprovando que o problema tem natureza estrita de integração UI/Payload.

## Atualização Pós-Correções (ERP-GATE-01A, 01B, 01C)

As lacunas identificadas pela auditoria inicial (NO-GO) foram integralmente sanadas através do pacote de correções subsequentes:
- **ERP-GATE-01A:** O frontend abandonou a interceptação manual hardcoded e passou a enviar as URLs e o `auth_model` extraídos nativamente do _Schema_ da Capability.
- **ERP-GATE-01B:** Um forte validador antimanipulação (`validate_provider_url`) blindou contra URLs maliciosas e tráfego SSRF a rede privada.
- **ERP-GATE-01C:** O schema base do Backend `SankhyaConfigCreate` foi consertado para honrar e processar o `auth_model` em vez de adivinhá-lo pelo conjunto de credenciais. A paridade total foi aferida em testes E2E do Console ao Sync Schedulado.

**Novo Veredicto do Gate ERP:** `GO COM RESSALVAS`
Ressalva: Permanece documentado o TOCTOU residual referente ao DNS Rebinding de baixíssimo TTL, mitigado pela impossibilidade de trânsito em produção fora do range validado.

O Gate de Arquitetura e Configurações para a implantação do Piloto Safra Café (ERP-PILOT-01) está formalmente aberto.
