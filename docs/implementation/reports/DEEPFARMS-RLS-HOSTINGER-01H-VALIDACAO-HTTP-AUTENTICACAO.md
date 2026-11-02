# DEEPFARMS-RLS-HOSTINGER-01H — Validação HTTP de Autenticação e Isolamento RLS

**Data:** 2026-10-31  
**Escopo:** request HTTP FastAPI com autenticação, sessão SQLAlchemy e consulta ORM RLS  
**Banco:** `deepfarms_rls_lab`  
**Runtime:** `deepfarms_rls_lab_runtime`  
**Veredicto:** **GO COM RESSALVAS**, limitado à prova HTTP sintética no laboratório

## 1. Síntese

O teste passou de ponta a ponta por uma aplicação FastAPI mínima com as dependências reais de `core.dependencies`, o engine/fábrica reais de `core.database`, SQLAlchemy AsyncSession e uma consulta ORM protegida por RLS. O token foi assinado com chave efêmera de teste; o hash correspondente existia em `sessoes_ativas`; a membership estava ativa em `tenant_usuarios`.

A resposta autenticada como Tenant A continha somente a linha sintética A; Tenant B continha somente a linha B. A leitura de `current_database()`, `current_user`, `session_user` e `app.current_tenant_id` foi feita pela mesma sessão da query ORM. A identidade foi `deepfarms_rls_lab` / `deepfarms_rls_lab_runtime` / `deepfarms_rls_lab_runtime`. Commit, rollback e erro SQL seguido de rollback preservaram o contexto na consulta seguinte.

Os cenários de token inválido/expirado, sessão revogada, membership ausente/inativa e seleção por header sem autorização foram negados como esperado. As fixtures temporárias foram removidas; a inspeção posterior encontrou somente a fixture preexistente `farms.rls_probe`, ainda com RLS e FORCE RLS.

## 2. Caminho HTTP exercitado

O harness usa uma aplicação FastAPI de teste com uma rota mínima `/lab/probe`. Ela não substitui a aplicação inteira nem muda código funcional. A resolução HTTP percorreu:

1. `get_token` obtém Bearer;
2. `verify_commercial_jwt_guardrail` aplica o guardrail existente;
3. `_decode_platform_token` valida assinatura e expiração;
4. `_validate_token_session` consulta `SessaoAtiva` pela hash SHA-256 do token e valida status/expiração;
5. `get_current_user_claims` confirma membership ativa antes de ativar Tenant;
6. `get_tenant_id` repete a validação da seleção autorizada e verifica eventual `x-tenant-id`;
7. FastAPI compartilha `get_session` entre as dependências e a função da rota;
8. a rota consulta a fixture por ORM e verifica o GUC efetivo no PostgreSQL.

Para provar identidade de sessão, o teste instrumentou `_activate_session_tenant` com um wrapper que registra o objeto e chama a implementação original. A rota confirmou que o objeto ativado é o mesmo objeto AsyncSession recebido para a consulta ORM.

O middleware geral de `main.app`, heartbeat e routers de produto não foram carregados. A requisição de teste chamou diretamente a aplicação FastAPI mínima, com Authorization HTTP real e dependências de autenticação reais. Isso mantém a prova pequena e evita disparar caminhos de aplicação fora do escopo.

## 3. Fixtures temporárias

A inspeção somente leitura anterior à DDL encontrou em `farms` apenas `rls_probe` entre os nomes verificados: não existiam `sessoes_ativas`, `tenant_usuarios` nem `rls_http_probe`. O runtime não tem privilégio `CREATE`; a role deploy fez `SET ROLE deepfarms_rls_lab_owner` para montar e remover as fixtures.

Foram criadas somente no banco de laboratório:

| Tabela | Finalidade e colunas mínimas |
|---|---|
| `farms.sessoes_ativas` | `id`, `usuario_id`, `tenant_id`, `token_hash`, `status`, `expira_em`; campos efetivamente lidos por `_validate_token_session`. |
| `farms.tenant_usuarios` | `id`, `tenant_id`, `usuario_id`, `status`; campos efetivamente consultados pelas validações de membership. |
| `farms.rls_http_probe` | `id`, `tenant_id`, `dado`; tabela sintética com policy SELECT por `app.current_tenant_id`, RLS e FORCE RLS. |

Não foi necessário criar as tabelas completas `usuarios` e `tenants`: o caminho HTTP selecionado autentica pelo JWT assinado, sessão ativa e membership e não consulta essas tabelas. UUIDs de usuário e Tenant foram gerados para o teste e usados nos claims, sessões, memberships e dados sintéticos. Nenhum usuário/token real foi usado.

Ao runtime foi concedido somente SELECT nas três tabelas da fixture. As linhas de teste A/B foram semeadas como owner antes de habilitar RLS na tabela probe. No teardown, o teste removeu as três tabelas que havia criado. A consulta de catálogo posterior confirmou que nenhuma permaneceu; `farms.rls_probe` original permaneceu intacta.

## 4. Matriz de cenários

| Cenário | Esperado | Observado | Resultado |
|---|---|---|---|
| Token A assinado, hash com sessão `ATIVA`, membership A `ATIVO` | HTTP 200 e somente dados A | 200; somente `synthetic-A` | **PASS** |
| Token B assinado, hash com sessão `ATIVA`, membership B `ATIVO` | HTTP 200 e somente dados B | 200; somente `synthetic-B` | **PASS** |
| Mesma sessão nas dependências e na query ORM | Objeto ativado é o usado pela rota | `session_identity_confirmed=true` | **PASS** |
| Identidade PostgreSQL na requisição | Banco/role de laboratório | `deepfarms_rls_lab`; runtime como `current_user` e `session_user` | **PASS** |
| Contexto GUC antes da query | UUID do Tenant autorizado | UUID A/B correspondente | **PASS** |
| Commit seguido de nova query | GUC reaplicado; linhas do Tenant original | UUID e somente linha A/B | **PASS** |
| Rollback seguido de nova query | GUC reaplicado; linhas do Tenant original | UUID e somente linha A/B | **PASS** |
| Erro SQL, rollback e query seguinte | Sessão recuperável e contexto correto | `division by zero` capturado; contexto e linha do Tenant reaplicados | **PASS** |
| Token de usuário sem membership | HTTP 403 | 403 | **PASS** |
| Membership `SUSPENSO` | HTTP 403 | 403 | **PASS** |
| Token com assinatura/formato inválido | HTTP 401 | 401 | **PASS** |
| JWT expirado | HTTP 401 | 401 | **PASS** |
| Sessão com status `ENCERRADA` | HTTP 401 | 401 | **PASS** |
| Token A com header Tenant B | HTTP 403; header não sobrepõe claim autorizado | 403 | **PASS** |
| Token sem Tenant com header B sem membership B | HTTP 403 | 403 | **PASS** |
| Sessão sem Tenant em backend reutilizado | GUC vazio e nenhuma linha privada | GUC vazio; zero linhas | **PASS**, regressão 01G |

## 5. Execução e falhas

- Teste HTTP + regressões de integração da 01G: **3 passed** (`test_rls_http_auth_lab.py` e os dois casos de `test_rls_tenant_session_lab.py`).
- Regressões unitárias 01G de tenancy, listener e guardrail: **19 passed, 1 skipped**. O teste de laboratório separado foi pulado nessa rodada sem URL; foi executado na rodada integrada acima.
- `compileall` dos dois arquivos de integração: **PASS**.
- `git diff --check`: **PASS**.
- Uma rodada intermediária expirou ao abrir uma conexão isolada apenas para consultar a identidade PostgreSQL, antes de qualquer DDL. A checagem foi movida para dentro da própria sessão HTTP; a rodada final integrada passou. Não houve alteração persistente nessa tentativa.

## 6. Limitações

1. A policy RLS da rota é uma fixture sintética e a tabela consultada é um ORM mínimo de teste; não foram criadas policies nem tabelas de negócio reais.
2. O teste prova a regra executada pelas dependências selecionadas. Não valida o estado de `Usuario.ativo`, pois `get_current_user_claims` não consulta `usuarios`; também não usa `get_current_user` nem `get_current_tenant`.
3. O teste usa FastAPI/ASGI com uma rota mínima e não inclui middleware de observabilidade, heartbeat ou a tabela de sessões completa da produção. Não dispara worker ou integração externa.
4. Policies, grants, tabelas e configuração de produção permanecem fora do escopo. O teste não prova que todos os endpoints de produto usem a mesma dependência nem cobre caminhos globais/admin.
5. As fixtures são criadas no começo da execução de integração e removidas em `finally`; o relatório registra evidência do resultado, não mantém as fixtures como artefato permanente.

## 7. Veredicto

**GO COM RESSALVAS para a validação HTTP sintética no laboratório.** Os cenários definidos passaram sob a role runtime restrita, com o contexto Tenant instalado após validação de token, sessão e membership, e com a query ORM na mesma sessão.

O resultado não declara a aplicação pronta para produção. Continuam fora do escopo workers, operações globais, middleware completo, políticas e tabelas reais, além da validação de usuário ativo. Não autoriza deploy nem cutover.
