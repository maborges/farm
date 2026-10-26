# AGRO-ADMIN-01E2 — Fundação de Configurações Dinâmicas, RBAC e Auditoria

**Data:** 23 de Outubro de 2026  
**Auditor / Implementador:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High  
**Modalidade:** Implementação Incremental Controlada  
**Status da Etapa:** Concluído com Sucesso  

---

## 1. Arquivos Criados e Modificados

### Arquivos Criados
1. `services/api/core/schemas/agro_config_schemas.py`: Contratos tipados Pydantic (`AgroClimaConfig`, `AgroMercadoConfig`, `AgroMensagensAvisosConfig`, `AgroFeatureFlagsConfig`, `AgroConfigMetadata`, `AgroConfigItemResponse`, `AgroAllConfigsResponse`).
2. `services/api/core/services/config_masking.py`: Utilitário recursivo de mascaramento de segredos (senhas, tokens, API keys) para respostas de API e registros de auditoria.
3. `services/api/core/services/agro_config_service.py`: Motor central de configurações tipadas, versionamento persistente, concorrência otimista, cache local L1 (TTL 30s) e invalidação Redis.
4. `services/api/core/services/admin_audit_service.py`: Serviço central de resolução de identidade administrativa para auditoria, integrando a identidade global (`usuarios`) com operadores do SaaS (`admin_users`) e garantindo integridade referencial com a FK `admin_audit_log_admin_user_id_fkey`.
5. `services/api/core/routers/backoffice_agro_config.py`: Endpoints administrativos do Agro (`GET/PUT /api/v1/backoffice/agro/configuracoes`, `POST /api/v1/backoffice/agro/configuracoes/cache/clear`) protegidos por RBAC e auditoria compulsória.
6. `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/configuracoes/page.tsx`: Interface administrativa completa do Backoffice com abas para Avisos Legais, Feature Flags, Mercado e Políticas Climáticas (leitura orientada para 01E3).
7. `services/api/tests/unit/core/test_backoffice_agro_01e2.py`: Suíte de testes automatizados cobrindo segurança RBAC, integridade de validação, concorrência, auditoria, resolução de FK e resiliência de cache.

### Arquivos Modificados
1. `services/api/core/routers/configuration.py`:
   * Correção da vulnerabilidade histórica **SEC-03**: substituição de `claims: dict = Depends(get_current_user_claims)` por `require_permission("backoffice:config:view")` e `require_permission("backoffice:config:edit")`.
   * Mascaramento automático de segredos em `GET /config/saas`.
   * Auditoria compulsória em `AdminAuditLog` em `PUT /config/saas/{chave}`.
   * Delegação automática de chaves `agro:*` para o `AgroConfigService` com validação tipada e versionamento.
2. `services/api/core/constants.py`:
   * Atualização de `BackofficePermissions`: concessão de `backoffice:config:view` e `backoffice:config:edit` ao perfil `admin`; adição de `backoffice:agro:config:view` ao perfil `suporte`.
   * Preservação do isolamento: o perfil `comercial` e usuários gratuitos não obtiveram acesso a configurações da plataforma.
3. `services/api/core/models/admin_user.py`:
   * Correção do método `tem_permissao`: remoção de importação quebrada de `ADMIN_PERMISSIONS` e delegação canônica para `BackofficePermissions.has_permission(self.role, permissao)`.
4. `services/api/main.py`:
   * Inclusão do roteador `backoffice_agro_config.router` sob o prefixo `/api/v1`.
5. `apps/web/src/lib/sidebar-config.ts`:
   * Adição do item de navegação `"Configurações Globais"` sob o grupo `backoffice-agro`, condicionado à permissão `backoffice:agro:config:view`.

---

## 2. Vulnerabilidades de Configuração Global Corrigidas

| Código | Descrição da Vulnerabilidade Original | Risco Mitigado | Solução Implementada |
| :--- | :--- | :--- | :--- |
| **SEC-03** | `GET/PUT /config/saas` usava apenas `get_current_user_claims`, permitindo acesso por qualquer usuário autenticado (incluindo produtores gratuitos e operadores de tenants). | Crítico (Elevação de privilégio e adulteração global). | Bloqueio no backend: `GET` exige `backoffice:config:view`; `PUT` exige `backoffice:config:edit`. Usuários comuns e comerciais sem permissão recebem `403 Forbidden`. |
| **SEC-VAL** | `PUT /config/saas/{chave}` aceitava payloads JSON arbitrários sem validação de tipos, limites ou namespaces. | Alto (Injeção de parâmetros corrompidos e corrupção de estado). | Chaves do namespace `agro:*` são interceptadas e estritamente validadas contra schemas Pydantic tipados antes da persistência. |
| **SEC-LEAK**| `GET /config/saas` retornava senhas SMTP e chaves de API externas em texto claro no campo `valor`. | Alto (Vazamento de credenciais da infraestrutura). | Sanitização recursiva via `mask_sensitive_data`: senhas e tokens são mascarados como `********` ou `prefix***...suffix`. |
| **AUD-GAP** | Alterações em `ConfiguracaoSaaS` não geravam nenhum registro na tabela `admin_audit_log`. | Alto (Perda de rastreabilidade regulatória e administrativa). | Gravação compulsória e atômica em `AdminAuditLog` contendo autor, e-mail, IP, user-agent e diff sanitizado (antes/depois). |

---

## 3. Contratos e Schemas Implementados

Os schemas foram definidos com `ConfigDict(extra="ignore")` e validação estrita em `core/schemas/agro_config_schemas.py`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ESQUEMAS TIPADOS AGRO                           │
├───────────────────────────┬────────────────────────────────────────────┤
│ Schema                    │ Propriedades e Regras                      │
├───────────────────────────┼────────────────────────────────────────────┤
│ AgroClimaConfig           │ • active_provider: WEATHERAPI |            │
│ (agro:clima:config)       │   OPENWEATHER | OPEN_METEO                 │
│                           │ • fallback_chain: lista deduplicada        │
│                           │ • timeout_seconds: 1.0 a 15.0s (def: 5.0s) │
│                           │ • cache_ttl_seconds: 300 a 86400s          │
│                           │ • monthly_quota_limit: 0 a 10.000.000      │
│                           │ • force_contingency_mode: boolean          │
├───────────────────────────┼────────────────────────────────────────────┤
│ AgroMercadoConfig         │ • ptax_cache_ttl_seconds: 300 a 14400s     │
│ (agro:mercado:config)     │ • macro_cache_ttl_seconds: 300 a 86400s    │
│                           │ • max_defasagem_dias: 1 a 60 dias (def: 14)│
│                           │ • deral_active_snapshot: pattern           │
│                           │   ^deral-prp-\d{4}-\d{2}-\d{2}\.json$      │
├───────────────────────────┼────────────────────────────────────────────┤
│ AgroMensagensAvisosConfig │ • aviso_precos_deral: min 10, max 500 chars│
│ (agro:mensagens:avisos)   │ • aviso_ptax: min 10, max 500 chars        │
│                           │ • aviso_macro_bcb: min 10, max 500 chars   │
│                           │ • aviso_ibge: min 10, max 500 chars        │
│                           │ • banner_urgente: optional max 300 chars   │
├───────────────────────────┼────────────────────────────────────────────┤
│ AgroFeatureFlagsConfig    │ • clima_enabled: boolean (def: True)       │
│ (agro:feature_flags)      │ • mercado_enabled: boolean (def: True)     │
│                           │ • byok_enabled: boolean (def: True)        │
│                           │ • ibge_enabled: boolean (def: True)        │
│                           │ • calculadoras_enabled: boolean (def: True)│
└───────────────────────────┴────────────────────────────────────────────┘
```

> **Nota de Isolamento:** Os contratos foram criados para administração segura; nesta fase, eles **não ativam** comportamento dinâmico nos endpoints públicos de Clima ou Mercado, preservando a estabilidade da aplicação.

---

## 4. Modelo de Permissões (RBAC)

A autorização foi integrada ao sistema canônico de permissões administrativas (`BackofficePermissions`):

| Permissão | Papéis Autorizados | Propósito |
| :--- | :--- | :--- |
| `backoffice:config:view` | `super_admin`, `admin` | Visualizar configurações globais da plataforma SaaS (`/api/v1/config/saas`). |
| `backoffice:config:edit` | `super_admin`, `admin` | Alterar configurações globais da plataforma SaaS (`/api/v1/config/saas/{chave}`). |
| `backoffice:agro:config:view` | `super_admin`, `admin`, `suporte` | Visualizar configurações, avisos e feature flags do DeepFarms Agro. |
| `backoffice:agro:config:edit` | `super_admin`, `admin` | Salvar alterações de parâmetros, avisos e feature flags do Agro. |

* **Garantia contra Elevação Indevida:**
  * O perfil `comercial` e usuários de tenants comuns **não possuem** nenhuma das permissões acima.
  * O perfil `suporte` possui permissão somente de leitura (`view`), sendo bloqueado com `403 Forbidden` caso tente submeter qualquer alteração de configuração.

---

## 5. Estratégia Efetiva de Versionamento e Cache

```
[Escrita Administrativa via Backoffice]
                 │
                 ▼
  1. Validação Pydantic Estrita
                 │
                 ▼
  2. Checagem de Concorrência: expected_revision == current_revision?
     ├── NÃO ──> Retorna HTTP 409 Conflict (impede sobrescrita silenciosa)
     └── SIM
          │
          ▼
  3. Incrementa Revisão: revision = current_revision + 1
     Atualiza Metadados: updated_at, updated_by
                 │
                 ▼
  4. Transação Atômica no Banco (farms.configuracoes_saas + farms.admin_audit_log)
                 │
                 ▼
  5. Atualiza Cache Local L1 (TTL 30s)
                 │
                 ▼
  6. Notifica Redis Pub/Sub (Canal: agro:config:events)
     ├── Redis OK ───────> Workers invalidam caches instantaneamente
     └── Redis Offline ──> Degradação graciosa: workers convergem via TTL de 30s
```

* **Resiliência a Falhas do Redis:** Se o cluster Redis estiver fora do ar ou sofrer timeout, a escrita administrativa é concluída com sucesso no PostgreSQL e no cache local, emitindo um log estruturado `WARNING` sem lançar erro para o operador.

---

## 6. Evidências de Auditoria

Toda atualização grava atomicamente na tabela `farms.admin_audit_log` na mesma transação de banco.

* **Exemplo de Registro Persistido:**
  * `acao`: `"agro.config.update"` (ou `"saas.config.update"` para chaves da plataforma).
  * `entidade`: `"configuracoes_saas"`.
  * `admin_user_id`: UUID do operador autenticado.
  * `admin_email`: E-mail corporativo auditável (ex.: `admin@deepfarms.com`).
  * `dados_anteriores`: Payload anterior com valores sensíveis mascarados.
  * `dados_novos`: Novo payload persistido com valores sensíveis mascarados.
  * `ip_address`: IP de origem da requisição.
  * `user_agent`: Identificador do navegador/cliente HTTP.

---

## 7. Interface Administrativa Entregue

A interface foi implementada em `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/configuracoes/page.tsx` seguindo o Design System corporativo:

1. **Cabeçalho Contextual:**
   * Título, descrição e ícone `Settings` em tom Esmeralda.
   * Botões de ação rápida: *"Recarregar"* (com spinner) e *"Limpar Cache"* (com chamada atômica para invalidação de Redis e memória).
2. **Cards Superiores de Resumo Operacional:**
   * *Revisão Geral:* Número de revisão atual consolidado e timestamp da última alteração.
   * *Feature Flags Ativas:* Contador de módulos operacionais ativos (X / 5).
   * *Cache de Mercado:* TTL configurado em segundos e margem de defasagem aceitável em dias.
   * *Provedor de Clima:* Nome do provedor ativo e franquia mensal contratada.
3. **Abas Interativas com Formulários Validados:**
   * **Aba 1 (Avisos Legais & Mensagens):** Edição dos textos de DERAL, PTAX, Macro SGS, IBGE e banner de utilidade pública urgente para o topo do PWA.
   * **Aba 2 (Feature Flags):** Switches para ligar/desligar Clima, Mercado, BYOK, SIDRA e Calculadoras.
   * **Aba 3 (Mercado & Cache):** Configuração de TTLs e nome do arquivo de snapshot DERAL com aviso visual sobre a imutabilidade dos dados oficiais.
   * **Aba 4 (Políticas Climáticas):** Visualização dos parâmetros de clima com alerta institucional indicando que o hot-swap dinâmico e gestão de credenciais serão ativados na subfase **01E3**.
4. **Governança de Concorrência e Feedback:**
   * Envio automático do campo `expected_revision` em cada salvamento.
   * Em caso de conflito concorrente (HTTP 409), exibe notificação Toast explicativa e recarrega os dados mais recentes.
   * Desabilitação automática de inputs e botões caso o usuário autenticado não possua a permissão `backoffice:agro:config:edit`.

---

## 8. Resultados Detalhados dos Testes

### Suíte Específica 01E2 (`test_backoffice_agro_01e2.py`): **8/8 Aprovados (100%)**

| Teste | Categoria | Resultado | Evidência / Validação |
| :--- | :--- | :---: | :--- |
| `test_security_rbac_free_user_and_read_only_access` | Segurança | **PASSED** | Usuário gratuito e usuário comercial sem privilégio recebem `403 Forbidden` em `/config/saas` e `/backoffice/agro/configuracoes`. Operador `suporte` lê normalmente mas recebe `403` ao tentar mutação. |
| `test_security_masking_secrets_no_raw_leak` | Segurança | **PASSED** | Chaves secretas e senhas SMTP salvas em banco retornam com máscara (`***`) na API e nunca em texto claro. |
| `test_integrity_typed_validation_and_rejection` | Integridade | **PASSED** | Payload com timeout de 30s (máximo 15s) ou snapshot DERAL com nome inválido é rejeitado com `422 Unprocessable Content`. Payload válido persiste com revisão incrementada. |
| `test_integrity_concurrency_control_optimistic_locking` | Integridade | **PASSED** | Submissão com `expected_revision` desatualizada rejeita com `409 Conflict`. Submissão com revisão correta avança a versão. |
| `test_audit_atomicity_and_logging` | Auditoria | **PASSED** | Toda alteração grava registro na tabela `admin_audit_log` contendo operador, IP, user-agent e diffs mascarados. |
| `test_cache_and_redis_offline_resilience` | Cache | **PASSED** | Escrita e leitura funcionam normalmente mesmo com conexão de Redis indisponível (`ConnectionError` simulada). Endpoint `/cache/clear` executa com sucesso. |
| `test_saas_global_config_regression_secured` | Regressão | **PASSED** | Endpoint original `/api/v1/config/saas` opera com RBAC estrito, mascaramento e auditoria para chaves genéricas da plataforma. |
| `test_audit_foreign_key_resolution_for_global_user` | Integridade / FK | **PASSED** | Validação ponta a ponta da resolução de identidade entre `usuarios` e `admin_users`, garantindo conformidade com a FK `admin_audit_log_admin_user_id_fkey` mesmo quando o JWT contém apenas o UUID do usuário global. |

### Suíte de Regressão Geral: **82/82 Aprovados (100%)**

* `test_backoffice_agro_01d.py`: 5/5 aprovados (gestão de produtores e contenção comercial preservadas).
* `test_backoffice_identity_integration.py`: 3/3 aprovados.
* `test_homologacao_01b2c_e2e_fluxos.py`: 1/1 aprovado.
* `test_agro_byok.py`: 13/13 aprovados (cofre BYOK inalterado).
* `test_clima_publico.py`: 20/20 aprovados (contrato público de clima preservado).
* `test_precos_publicos.py`: 24/24 aprovados (contrato público de mercado preservado).
* `test_macro_publico.py`: 16/16 aprovados (PTAX e indicadores macroeconômicos preservados).

### Verificação de Tipagem Estrita do Frontend

* Comando executado: `pnpm --filter web exec tsc --noEmit`
* Resultado: **Código de saída 0 (Zero erros de compilação TypeScript)**.

---

## 9. Pendências de PostgreSQL Real

A presente validação foi executada utilizando o mecanismo de testes isolados assíncronos com SQLite e mock de conexões. Para o corte definitivo de produção, permanecem as seguintes validações:
1. Validar a inicialização do listener de pub/sub em ambiente multi-worker Uvicorn no cluster de staging/produção com Redis real.
2. Confirmar que a política de RLS do PostgreSQL (`farms.configuracoes_saas`) não bloqueia a leitura por conexões com pool restrito.

---

## 10. Riscos Residuais

| Risco Residual | Probabilidade | Impacto | Mitigação Vigente |
| :--- | :--- | :--- | :--- |
| **Operador editar banner urgente com texto incorreto** | Baixa | Médio | Validação de comprimento máximo (300 caracteres) e auditoria imediata registrando o responsável. |
| **Divergência temporária entre workers em caso de perda de evento Redis** | Baixa | Baixo | TTL local de 30 segundos garante convergência eventual de todos os workers em menos de meio minuto. |

---

## 11. Veredicto Técnico Final

### Decisão: **GO**

A fundação de configurações dinâmicas, controle de acesso RBAC, validação Pydantic, versionamento concorrente e trilha de auditoria do DeepFarms Agro foi **plenamente implementada e homologada com 100% de aprovação nos testes automatizados e zero quebra de contratos legados**.

A subfase **AGRO-ADMIN-01E3 (Provedores Climáticos, Credenciais e Contingência)** **NÃO** foi iniciada e aguarda a avaliação e aprovação formal deste relatório.
