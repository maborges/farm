# AUDIT-02: Auditoria Multi-Tenant e Permissões

**Data:** 2026-06-08
**Status:** Concluída
**Auditor:** Antigravity (IA Sênior)

## Resumo Executivo
A varredura focada no isolamento de tenant, controle de acesso e permissões (RBAC) do AgroSaaS encontrou vulnerabilidades sistêmicas de alta criticidade. A principal descoberta é que, embora o frontend restrinja a navegação com base nos perfis de acesso dos usuários (`PerfilAcesso`), o **backend omite a validação de permissões granulares (`require_tenant_permission`) em quase todos os módulos core** (Financeiro, Agrícola, Operacional), confiando apenas na verificação de licença do módulo (`require_module`).

Isso configura um cenário crítico onde qualquer usuário autenticado pode executar ações destrutivas ou visualizar dados financeiros, desde que saiba o caminho da API.

---

## 1. Descobertas: Controle de Acesso e Permissões

### 1.1 Falha Sistêmica de RBAC no Backend (P0 Crítico)
* **Localização:** `services/api/financeiro/routers/*`, `services/api/agricola/*/router.py`, `services/api/operacional/routers/*`
* **Classificação:** Falha Comprovada
* **Descrição:** A imensa maioria dos roteadores de API que expõem os serviços de negócios utilizam `Depends(require_module("X"))` para verificar se o *Tenant* possui o módulo contratado. Contudo, ignoram por completo a validação de quem é o usuário usando `Depends(require_tenant_permission("modulo:recurso:acao"))`.
* **Impacto:** Qualquer usuário do sistema com uma sessão ativa (mesmo um operador básico) pode enviar uma requisição `PATCH /financeiro/receitas/{id}` ou `DELETE /agricola/safras/{id}` e a ação será bem-sucedida, uma vez que o backend não faz enforcement de seu `PerfilAcesso`.
* **Recomendação:**
  - Padronizar o uso da dependência `require_module_and_permission(modulo, permissao)` nos roteadores.
  - Criar um middleware ou hook de teste unitário que obrigue todo endpoint (exceto autenticação) a possuir verificação explícita de permissão no schema do FastAPI (`dependencies=...`).

### 1.2 Inconsistência UI vs API (P1 Alto)
* **Localização:** `apps/web/src/lib/sidebar-config.ts` vs Backend APIs.
* **Classificação:** Falha Comprovada
* **Descrição:** O frontend implementa corretamente verificações de permissões como `permission: 'backoffice:billing:view'` ou mapeamentos de permissões do tenant (via `isGranted`). Isso gera o cenário perigoso de "falsa segurança": os botões de ação e menus são escondidos do usuário sem privilégios na interface UI, levando os desenvolvedores a acreditarem que o sistema está seguro, quando os endpoints no backend estão desprotegidos.
* **Recomendação:** Sincronizar o `PERMISSION_CATALOG` do frontend com as rotas do backend. Refatorar os roteadores para espelhar as permissões exigidas pela UI.

### 1.3 Roteador Aberto e Vazamento de Dados no Growth (P1 Alto)
* **Localização:** `services/api/growth/router.py` (ex: `GET /growth/events/metrics`)
* **Classificação:** Falha Comprovada
* **Descrição:** Encontrados endpoints no módulo de Growth que sequer verificam `Depends(get_current_user_claims)` ou `Depends(get_tenant_id)`. Esses endpoints estão públicos e vazam métricas de negócios possivelmente de todos os tenants.
* **Recomendação:** Injetar as dependências de segurança corretas (`get_tenant_id` e permissão específica de owner/admin) nas rotas de `growth`.

---

## 2. Descobertas: Isolamento de Unidade Produtiva (Cross-UP)

### 2.1 Movimentações Cruzadas de Estoque (Info)
* **Localização:** `services/api/operacional/services/estoque_service.py` -> `registrar_transferencia`
* **Classificação:** Comportamento Correto
* **Descrição:** O sistema permite a transferência de saldo de estoque entre depósitos que pertencem a **Unidades Produtivas distintas** (fazendas diferentes) sob o mesmo tenant.
* **Evidência:** O código identifica ativamente essa condição (`dep_origem.unidade_produtiva_id != dep_destino.unidade_produtiva_id`) e loga um evento de auditoria `multi_up_stock_transfer_between_units`.
* **Conclusão:** O isolamento de Tenant está íntegro. O intercâmbio de recursos entre Unidades Produtivas da mesma empresa é um requisito operacional válido e está sendo auditado de forma satisfatória.

### 2.2 Depósitos sem Unidade Produtiva (Info)
* **Localização:** `services/api/operacional/models/estoque.py`
* **Classificação:** Comportamento Correto
* **Descrição:** Havia suspeita de depósitos flutuantes ("órfãos" de fazenda). Entretanto, a verificação no model ORM revela que o campo `unidade_produtiva_id` está mapeado como `nullable=False` (`Mapped[uuid.UUID]`).
* **Conclusão:** O banco de dados obriga que todo depósito pertença a uma unidade produtiva específica. Não há falha arquitetural neste quesito.

---

## 3. Descobertas: Isolamento de Tenant (Queries)

### 3.1 Queries de Serviço Aparentemente sem `tenant_id` (Falso Positivo)
* **Localização:** `services/api/agricola/eficiencia/service.py` e `agricola/dre/service.py`
* **Classificação:** Comportamento Correto (Falso Positivo)
* **Descrição:** A varredura estática inicial indicou que várias operações de busca não aplicavam diretamente `where(tenant_id=X)`. Após inspeção profunda, constatou-se que esses serviços herdam de `BaseService` ou injetam RLS (`Row-Level Security`), garantindo o escopo do tenant de forma abstraída. Além disso, as consultas em profundidade realizam joins implícitos (como `OperacaoAgricola` herdando o `tenant_id` atrelado na camada superior).
* **Conclusão:** O isolamento horizontal de tenants nos domínios centrais não foi quebrado.

---

## Conclusão e Próximos Passos
A infraestrutura de RLS e `tenant_id` funciona e impede o vazamento de dados entre empresas diferentes. **O grande risco iminente reside inteiramente no modelo de autorização interno de cada empresa (RBAC).** 

O sistema possui a classe de segurança `PerfilAcesso`, mas falha em utilizá-la nos roteadores do FastAPI. 

A recomendação urgente (AUDIT-FIX-02) é implementar as anotações granulares (`require_tenant_permission`) em todos os endpoints de `financeiro`, `operacional` e `agricola`.
