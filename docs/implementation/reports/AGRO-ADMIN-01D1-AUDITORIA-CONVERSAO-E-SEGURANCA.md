# AGRO-ADMIN-01D1 — Relatório de Auditoria de Segurança e Conversão Comercial

**Documento:** Relatório de Auditoria Técnica e Segurança  
**Referência:** AGRO-ADMIN-01D1  
**Auditor Responsável:** GPT-5.6 Codex — Sol (Modo de Raciocínio Profundo)  
**Modalidade:** Auditoria Somente Leitura (Read-Only)  
**Data:** 23 de Outubro de 2026  
**Status do Veredicto:** **GO COM RESSALVAS** (Operações Administrativas) / **NO-GO** (Conversão Comercial)  

---

## 1. Resumo Executivo e Escopo da Auditoria

A presente auditoria técnica foi executada em conformidade com as diretrizes do epíco **AGRO-ADMIN-01D1**, tendo como objetivo primário a inspeção minuciosa, estritamente em modo somente leitura (sem alterações de código, banco de dados ou configurações), das entregas realizadas na fase **AGRO-ADMIN-01D**.

O foco recai sobre dois pilares fundamentais:
1. **O Fluxo de Conversão Comercial (`POST /api/v1/backoffice/agro/usuarios/{id}/converter-comercial`):** Avaliação do provisionamento atômico de tenants, preservação de identidade, impacto nos tokens e compatibilidade com o ciclo de vida comercial da plataforma.
2. **A Segurança Administrativa e Governança Operacional:** Avaliação do controle de acesso baseado em funções (RBAC), proteção contra vazamento de segredos no cofre BYOK (Bring Your Own Key), minimização de dados sensíveis (LGPD), eficácia na revogação de sessões, atomicidade da trilha de auditoria e mitigação de concorrência.
3. **A Integridade da Homologação e Cobertura de Testes:** Exame forense sobre o ambiente de execução dos 27 testes automatizados reportados, discriminando o uso de SQLite em memória versus persistência em PostgreSQL real.

---

## 2. Auditoria do Fluxo de Conversão Comercial

O endpoint auditado é o [`POST /api/v1/backoffice/agro/usuarios/{usuario_id}/converter-comercial`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L621-L778), implementado no roteador [`services/api/core/routers/backoffice_agro.py`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py).

### 2.1 Preservação do UUID Global do Usuário
* **Evidência no Código:** [`backoffice_agro.py:710-716`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L710-L716)
  ```python
  tu = TenantUsuario(
      tenant_id=tenant.id,
      usuario_id=usuario_id,
      is_owner=True,
      status="ATIVO",
  )
  session.add(tu)
  ```
* **Parecer Técnico:** **CONFORME.** O identificador canônico global do usuário (`Usuario.id`) é preservado integralmente. Nenhuma nova conta de usuário é criada na tabela `usuarios`. O produtor passa a figurar como `is_owner=True` no novo `Tenant` através de um vínculo relacional direto em `tenant_usuarios`. Todos os históricos, credenciais BYOK e dados individuais permanecem vinculados ao mesmo UUID.

---

### 2.2 Preservação do Acesso Gratuito ao Agro
* **Evidência no Código:** [`services/api/core/services/auth_service.py:85-88`](file:///opt/lampp/htdocs/farm/services/api/core/services/auth_service.py#L85-L88) e [`services/api/core/dependencies.py:389-402`](file:///opt/lampp/htdocs/farm/services/api/core/dependencies.py#L389-L402)
  ```python
  elif account_type == "COMMERCIAL":
      product_scope = ["saas", "agro:free"]
  ```
* **Parecer Técnico:** **CONFORME.** O design de autorização garante que clientes comerciais recebam o escopo cumulativo `["saas", "agro:free"]`. Os endpoints do Agro PWA (calculadoras, clima, cotações de mercado e cofre BYOK) utilizam a dependência `get_global_user_claims`, que aceita tanto tokens individuais (`INDIVIDUAL_FREE`) quanto comerciais (`COMMERCIAL` com escopo `agro:free`). Portanto, o usuário convertido mantém pleno acesso às ferramentas gratuitas do Agro.

---

### 2.3 Tratamento de `account_type` e `product_scope`
* **Evidência no Código:** [`backoffice_agro.py:372-382`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L372-L382) e [`services/api/core/models/auth.py:8-35`](file:///opt/lampp/htdocs/farm/services/api/core/models/auth.py#L8-L35)
* **Parecer Técnico:** **CONFORME NA MODELAGEM, COM RESSALVA DE TRANSIÇÃO DE SESSÃO.** A tabela `usuarios` não possui coluna física `account_type`. O tipo de conta é uma propriedade calculada dinamicamente:
  - Presença de vínculo ativo em `tenant_usuarios` $\rightarrow$ Classificado como `COMMERCIAL`.
  - Ausência de vínculo em `tenant_usuarios` $\rightarrow$ Classificado como `INDIVIDUAL_FREE`.
  - Flag `is_superuser == True` $\rightarrow$ Classificado como `PLATFORM_ADMIN`.
  Dessa forma, a criação da linha em `tenant_usuarios` altera imediatamente a classificação do usuário nas consultas administrativas (excluindo-o da listagem de produtores Agro). No entanto, tokens JWT já emitidos antes da conversão permanecem com as claims estáticas anteriores.

---

### 2.4 Criação de Tenant e Vínculo de Proprietário
* **Evidência no Código:** [`backoffice_agro.py:700-716`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L700-L716)
* **Parecer Técnico:** **CONFORME COM GAP FUNCIONAL.** O provisionamento gera a linha em `tenants` com slug sanitizado e verificação de colisão (`slug-2`, `slug-3`).
  * **Gap Identificado 1:** O `TenantUsuario` é criado com `perfil_id = None`. Embora `is_owner=True` contorne a checagem de permissões na maioria dos endpoints via `if tenant_usuario.is_owner: return True`, métodos que buscam a role nominal do perfil caem no fallback `"operador"`.
  * **Gap Identificado 2:** Não há criação de `UnidadeProdutiva` (Fazenda) inicial padrão. Sem isso, o novo cliente comercial não possui fazenda associada (`fazendas_auth` fica vazia), o que impede operações agrícolas de campo até que uma fazenda seja cadastrada manualmente.

---

### 2.5 Integração com o Ciclo de Vida Comercial Existente
* **Evidência no Código:** Comparação entre [`backoffice_agro.py:699-739`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L699-L739) e [`auth_service.py:601-723`](file:///opt/lampp/htdocs/farm/services/api/core/services/auth_service.py#L601-L723) (`create_tenant_for_user`).
* **Parecer Técnico:** **NÃO CONFORME (DESVIO ARQUITETURAL).** A conversão no backoffice reimplementou de forma paralela e incompleta o fluxo comercial canônico estabelecido em `AuthService.create_tenant_for_user`:
  1. **Ausência de Fatura Inicial:** Em `AuthService`, quando o plano é pago com trial, uma `Fatura` com status `ABERTA` e valor correspondente é imediatamente gerada com vencimento para `trial_expires_at + 1 dia`. O endpoint do backoffice omitiu a criação da `Fatura`.
  2. **Ausência de Notificação por E-mail:** O serviço comercial canônico dispara `email_service.send_trial_notice(...)`. A conversão administrativa não envia e-mail ao produtor informando os dados do plano, termos de adesão e período de trial.
  3. **Ausência de Integração com Gateway:** Não há vinculação de cadastro de cliente em gateway financeiro (ex: Asaas/Stripe).

---

### 2.6 Validação de Plano e Ciclo de Cobrança
* **Evidência no Código:** [`backoffice_agro.py:663-686`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L663-L686)
* **Parecer Técnico:** **PARCIALMENTE CONFORME (VULNERABILIDADE DE VALIDAÇÃO).**
  - O endpoint valida a existência do plano e `ativo == True`.
  - Normaliza e valida formalmente o CPF/CNPJ via algoritmo matemático de dígitos verificadores (`validar_cpf_ou_cnpj`).
  - **Falha 1:** O campo `ciclo` não possui validação de enum (`{"MENSAL", "ANUAL"}`). Qualquer string arbitrária enviada pelo cliente (ex: `"SEMESTRAL"`, `"INVALIDO"`) é persistida em `AssinaturaTenant.ciclo_pagamento`.
  - **Falha 2:** A query de seleção do plano não filtra `PlanoAssinatura.is_free == False`. Se for injetado o ID de um plano gratuito, o sistema converterá o usuário para um plano comercial com custo zero sem emitir erro de validação.

---

### 2.7 Atomicidade e Rollback em Caso de Falha
* **Evidência no Código:** [`backoffice_agro.py:700-766`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L700-L766)
* **Parecer Técnico:** **CONFORME.** Todas as mutações (`Tenant`, `TenantUsuario`, `AssinaturaTenant` e `AdminAuditLog`) são gerenciadas sob uma única sessão assíncrona (`AsyncSession`). O `await session.commit()` só ocorre após a adição de todos os registros. Qualquer exceção ou erro de restrição no banco resulta em rollback total pelo gerenciador de contexto do FastAPI.

---

### 2.8 Idempotência e Prevenção de Conversões Duplicadas
* **Evidência no Código:** [`backoffice_agro.py:653-697`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L653-L697)
* **Parecer Técnico:** **NÃO CONFORME (CRÍTICO).** O endpoint **NÃO POSSUI IDEMPOTÊNCIA NEM TRAVA DE DUPLICIDADE**:
  - Não há checagem prévia validando se o produtor já possui um tenant comercial vinculado como proprietário (`select(TenantUsuario).where(TenantUsuario.usuario_id == usuario_id, TenantUsuario.is_owner == True)`).
  - A restrição de unicidade `uq_tenant_usuarios_tenant_usuario` em banco é composta por `(tenant_id, usuario_id)`. Como cada chamada gera um novo `tenant_id`, a restrição do banco **não impede** que o mesmo usuário seja vinculado a dezenas de tenants diferentes.
  - Se um operador realizar duplo clique ou disparar requisições concorrentes, o sistema criará múltiplos tenants (`fazenda`, `fazenda-2`), múltiplas assinaturas e múltiplos registros de owner para o mesmo usuário.

---

### 2.9 Permissões RBAC para Realizar a Conversão
* **Evidência no Código:** [`backoffice_agro.py:625, 632`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L625) e [`services/api/core/constants.py:424-470`](file:///opt/lampp/htdocs/farm/services/api/core/constants.py#L424-L470)
* **Parecer Técnico:** **PARCIALMENTE CONFORME (DESALINHAMENTO DE PERFIS).**
  - O endpoint está protegido pela permissão `backoffice:agro:users`.
  - Na matriz de permissões (`BackofficePermissions`):
    - `super_admin`: Concedido via wildcard `*`.
    - `admin`: Concedido via wildcard `backoffice:agro:*`.
    - `suporte`: Negado (possui apenas `backoffice:agro:users:view`).
    - `comercial`: **NEGADO** (possui apenas `backoffice:agro:users:view`).
  - **Incongruência:** O operador com perfil `comercial` está impedido de converter o usuário. Apenas administradores globais podem fazê-lo. Além disso, a ação de conversão não possui permissão granular própria (ex: `backoffice:agro:users:convert`), ficando agregada à mesma permissão de bloqueio de contas.

---

### 2.10 Comportamento de Sessões e Tokens Pós-Conversão
* **Evidência no Código:** [`backoffice_agro.py:627-778`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L627-L778)
* **Parecer Técnico:** **CONFORME COM RESSALVA DE UX.**
  - A conversão não revoga as sessões ativas do usuário no app Agro. O produtor continua navegando no aplicativo rural sem interrupções.
  - No entanto, o token atual do usuário permanece com as claims `account_type: "INDIVIDUAL_FREE"` e `tenant_id: None`. Se o usuário tentar acessar imediatamente o SaaS comercial (`apps/web`), ele será barrado pelo `verify_commercial_jwt_guardrail` com `403 Forbidden`.
  - O acesso comercial só se torna funcional após o usuário realizar um novo login ou invocar o endpoint de troca de tenant, ocasião em que o `AuthService` emitirá um token v2 com `account_type: "COMMERCIAL"` e o `tenant_id` correspondente.

---

## 3. Auditoria de Segurança Administrativa

### 3.1 Eficácia do RBAC por Endpoint
* **Evidências:**
  - `GET /api/v1/backoffice/agro/usuarios`: `require_permission("backoffice:agro:view")`
  - `GET /api/v1/backoffice/agro/usuarios/{id}`: `require_permission("backoffice:agro:view")`
  - `POST /api/v1/backoffice/agro/usuarios/{id}/toggle-status`: `require_permission("backoffice:agro:users")`
  - `DELETE /api/v1/backoffice/agro/usuarios/{id}/sessions`: `require_permission("backoffice:agro:users")`
  - `GET /api/v1/backoffice/agro/planos`: `require_permission("backoffice:agro:view")`
  - `POST /api/v1/backoffice/agro/usuarios/{id}/converter-comercial`: `require_permission("backoffice:agro:users")`
* **Parecer Técnico:** **TOTALMENTE CONFORME.** A autorização é aplicada de maneira declarativa em cada rota na camada de transporte do FastAPI, sem qualquer dependência de ocultação visual no frontend.

---

### 3.2 Proteção Contra Exposição de Segredos BYOK
* **Evidência no Código:** [`backoffice_agro.py:41-53, 301-313, 393-410`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L41-L53)
* **Parecer Técnico:** **TOTALMENTE CONFORME (EXCELENTE).**
  - A tabela física `usuario_byok_credenciais` armazena `ciphertext_b64`, `data_nonce_b64`, `dek_encrypted_b64` e `dek_nonce_b64`.
  - O contrato Pydantic `AgroByokMeta` expõe unicamente: `id`, `provider_slug`, `mascara_chave`, `key_version`, `status`, `ultimo_uso` e `created_at`.
  - Na listagem geral (`/usuarios`), apenas a lista de slugs (`byok_providers`) é trafegada.
  - Nenhum segredo criptográfico, chave simétrica ou vetor de inicialização vaza para a API do Backoffice.

---

### 3.3 Minimização de Dados Pessoais (LGPD)
* **Evidência no Código:** [`backoffice_agro.py:78-95, 106-126`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L78-L95)
* **Parecer Técnico:** **CONFORME COM RESSALVA MODERADA.**
  - Os contratos `AgroUserListItem` e `AgroUserDetailResponse` retornam o CPF e telefone em texto claro para qualquer operador com acesso de leitura (`backoffice:agro:view`), abrangendo analistas de suporte e operadores comerciais.
  - Recomenda-se a aplicação de mascaramento nos DTOs de listagem (ex: `***.456.789-**`), liberando a consulta desmascarada apenas mediante ação explícita com registro de auditoria específico.
  - Nos logs de auditoria (`AdminAuditLog`), a minimização foi rigorosamente cumprida: nenhum CPF, senha ou segredo é gravado nos campos `descricao` ou `dados_novos`.

---

### 3.4 Revogação Efetiva de Sessões e Tokens
* **Evidência no Código:** [`backoffice_agro.py:483-494, 551-561`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L483-L494) e [`dependencies.py:322-350`](file:///opt/lampp/htdocs/farm/services/api/core/dependencies.py#L322-L350)
* **Parecer Técnico:** **TOTALMENTE CONFORME.**
  - As rotas de bloqueio (`toggle-status`) e revogação (`/sessions`) executam `UPDATE farms.sessoes_ativas SET status = 'ENCERRADA' WHERE usuario_id = :id AND status = 'ATIVA'`.
  - A dependência de validação de token `_validate_token_session` consulta a tabela `sessoes_ativas` a cada requisição (a verificação do cache negativo `cached is False` ocorre antes, e sessões ativas são validadas contra o banco).
  - Constatando `sessao_status != 'ATIVA'`, a sessão é marcada como `_cache_set(token_hash, False)` e rejeitada imediatamente com `HTTP 401 Unauthorized`.
  - O bloqueio de novas autenticações via `/auth/login` é garantido pela checagem de `user.ativo == False`.

---

### 3.5 Atomicidade da Auditoria Administrativa
* **Evidência no Código:** [`backoffice_agro.py:496-512, 562-576, 741-766`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L496-L512)
* **Parecer Técnico:** **TOTALMENTE CONFORME.**
  - O registro de auditoria `AdminAuditLog` é inserido na mesma transação SQLAlchemy que a operação de negócio.
  - Se a inserção de auditoria falhar (ex: violação de constraint ou falha de conexão), o `await session.commit()` falha e a alteração de status/sessão é abortada. Garantia estrita de não-repúdio.

---

### 3.6 Proteção Contra Ações Concorrentes
* **Evidência no Código:** [`backoffice_agro.py:469, 653`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py#L469)
* **Parecer Técnico:** **NÃO CONFORME (AUSÊNCIA DE LOCK PESSIMISTA).**
  - As operações utilizam `await session.get(Usuario, usuario_id)` sem bloqueio pessimista (`with_for_update`).
  - No `toggle-status`, requisições concorrentes disputam o mesmo valor booleano sem corrupção, mas geram múltiplos logs de auditoria inconsistentes.
  - No `converter-comercial`, a concorrência resulta na criação indesejada de múltiplos tenants e assinaturas para o mesmo usuário.

---

## 4. Auditoria dos Testes e Homologação (Forense de Testes)

A fase AGRO-ADMIN-01D reportou a execução com sucesso de 27 testes automatizados:
- `test_backoffice_agro_01d.py` (5 testes)
- `test_backoffice_identity_integration.py` (8 testes)
- `test_homologacao_01b2c_e2e_fluxos.py` (14 testes)

### 4.1 Persistência Real vs. SQLite em Memória
A inspeção do código-fonte dos testes revelou um **achado crítico de infraestrutura**:
* **`test_backoffice_agro_01d.py:34-50`:**
  ```python
  db_file = tmp_path / "test_agro_backoffice_01d.db"
  engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
  ...
  await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
  ```
  $\rightarrow$ **Executado 100% em SQLite via `aiosqlite`.**
* **`test_backoffice_identity_integration.py:30-45`:**
  ```python
  db_file = tmp_path / "test_backoffice_identity.db"
  engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
  ...
  await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
  ```
  $\rightarrow$ **Executado 100% em SQLite.**
* **`test_homologacao_01b2c_e2e_fluxos.py:46-65`:**
  Possui chave de ativação para PostgreSQL condicional a `CI_POSTGRESQL == "true"` ou `GITHUB_ACTIONS == "true"`. Em execuções locais sem essas variáveis, o teste faz fallback para SQLite em arquivo temporário (`homologacao_01b2c.db`).
  $\rightarrow$ **Executado 100% em SQLite na máquina local.**

### 4.2 Causa Raiz do Erro 500 no PostgreSQL
A execução exclusiva dos testes em SQLite explica por que a ausência física da tabela `usuario_byok_credenciais` no PostgreSQL compartilhado (`192.168.0.2/farms`) não foi detectada pela suíte de 27 testes.  
No SQLite, o método `Base.metadata.create_all` sintetiza as tabelas diretamente a partir dos modelos Python, contornando completamente a cadeia de migrations do Alembic (`alembic upgrade head`). Somente quando a API real foi acionada via HTTP é que o PostgreSQL retornou:
```text
UndefinedTableError: relation "usuario_byok_credenciais" does not exist
```
A falha foi sanada no turno anterior com a aplicação controlada de `alembic upgrade head`, mas o processo evidenciou a fragilidade de considerar testes SQLite como homologação de produção.

### 4.3 O que Depende Exclusivamente de PostgreSQL Isolado
1. **Migrations Alembic:** Verificação real de histórico de migrações (`alembic_version`), tipos nativos (`UUID`, `JSONB`) e constraints relacionais.
2. **Políticas de RLS (Row Level Security):** `SET LOCAL app.current_tenant_id`, inexistente no SQLite.
3. **Comportamento Concorrente e Isolamento:** Transações `READ COMMITTED`, bloqueios de linha `SELECT ... FOR UPDATE` e timeouts de pool de conexões.
4. **Foreign Keys em Schemas Distintos:** Integridade entre o schema `farms` e tabelas públicas.

---

## 5. Matriz Consolidada de Riscos e Severidade

| ID | Risco Identificado | Categoria | Severidade | Impacto |
| :--- | :--- | :--- | :---: | :--- |
| **RSK-01** | Ausência de idempotência e trava de conversões duplicadas em `converter-comercial` | Negócio / Dados | **ALTA** | Multiplicação de tenants e assinaturas para o mesmo usuário em caso de duplo clique ou concorrência. |
| **RSK-02** | Omissão da esteira comercial canônica (faturamento, envio de termos e primeira fatura) | Financeiro / Operações | **ALTA** | Inconsistência contábil quando expirar o período de trial da assinatura comercial. |
| **RSK-03** | Falso positivo na cobertura de testes (27 testes executados exclusivamente sobre SQLite) | Engenharia / QA | **ALTA** | Migrations Alembic não validadas em pipeline automatizado local, mascarando incompatibilidades com o PostgreSQL. |
| **RSK-04** | Perfil `comercial` sem permissão RBAC para executar a conversão comercial | Governança | **MÉDIA** | Operadores comerciais não conseguem promover clientes, sobrecarregando o perfil `admin`. |
| **RSK-05** | Ausência de validação rigorosa de ciclo de cobrança e planos gratuitos no payload | Segurança de Dados | **MÉDIA** | Possibilidade de persistência de strings inválidas em `ciclo_pagamento` ou promoção indevida para planos com custo zero. |
| **RSK-06** | Ausência de criação de `UnidadeProdutiva` inicial no tenant comercial convertido | Funcional / UX | **MÉDIA** | Usuário promovido não possui fazenda cadastrada e não consegue operar módulos agrícolas no SaaS. |
| **RSK-07** | Exibição de CPF em texto claro nas listagens e detalhes administrativos | Privacidade (LGPD) | **BAIXA** | Exposição excessiva de dados pessoais para operadores sem necessidade fiscal estrita. |

---

## 6. Correções Estritamente Necessárias (Backlog Recomendado)

As correções abaixo devem ser implementadas antes da liberação definitiva do fluxo de conversão em ambiente de produção:

1. **Bloqueio Temporário do Endpoint de Conversão:**
   - Desabilitar a rota `POST /api/v1/backoffice/agro/usuarios/{id}/converter-comercial` ou ocultar a ação no frontend até a aprovação formal do fluxo comercial completo.
2. **Implementação de Trava de Idempotência e Unicidade:**
   - Adicionar verificação atômica garantindo que o usuário não possua nenhum `TenantUsuario` com `is_owner == True` antes de permitir a conversão.
   - Utilizar bloqueio pessimista (`SELECT id FROM usuarios WHERE id = :id FOR UPDATE`) durante o processo de conversão.
3. **Integração com `AuthService.create_tenant_for_user`:**
   - Refatorar a conversão para invocar o serviço canônico unificado, gerando a `Fatura` correspondente, criando a fazenda padrão e disparando o e-mail transacional de trial.
4. **Validação Rígida do Payload:**
   - Limitar `ciclo` a `Literal["MENSAL", "ANUAL"]` e validar explicitamente `PlanoAssinatura.is_free == False`.
5. **Ajuste na Matriz RBAC:**
   - Criar permissão granular `backoffice:agro:users:convert` e concedê-la aos papéis `admin` e `comercial`.
6. **Evolução da Suíte de Testes com PostgreSQL Isolado:**
   - Estabelecer runner de testes de integração com container descartável PostgreSQL para validação de migrations Alembic e integridade referencial.
7. **Mascaramento de CPF nos DTOs de Visualização:**
   - Mascarar o CPF (`***.456.789-**`) no retorno de `AgroUserListItem`, liberando consulta integral apenas em rota com auditoria específica.

---

## 7. Veredicto Final

Com base nas evidências de código inspecionadas e na avaliação técnica de riscos, o parecer da auditoria é categorizado em dois blocos:

### 7.1 Operações Administrativas e Governança Operacional do Agro
* **Veredicto:** **GO COM RESSALVAS**
* **Justificativa:** As operações de listagem, consulta de perfil, inspeção do cofre BYOK (com zero vazamento de chaves), bloqueio/desbloqueio com encerramento síncrono de sessões e auditoria transacional estrita estão tecnicamente sólidas, seguras e em conformidade arquitetural. As ressalvas referem-se ao mascaramento preventivo de CPF e à dependência de testes em PostgreSQL.

### 7.2 Fluxo de Conversão Comercial (`converter-comercial`)
* **Veredicto:** **NO-GO**
* **Justificativa:** A conversão comercial foi implementada além do escopo autorizado da fase 01D, carece de garantias de idempotência e trava de concorrência, e encontra-se desacoplada da esteira comercial canônica (faturamento, envio de notificações e geração de fazenda inicial).
* **Determinação:** A funcionalidade de conversão comercial **deve permanecer desabilitada** no ambiente operacional até que as correções de integridade comercial e idempotência sejam submetidas a homologação formal.

---
*Relatório concluído e assinado digitalmente nos termos da governança técnica DeepFarms.*
