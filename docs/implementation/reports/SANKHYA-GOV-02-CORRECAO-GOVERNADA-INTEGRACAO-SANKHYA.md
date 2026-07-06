# SANKHYA-GOV-02 — Correção Governada da Integração Sankhya

## 1. Resumo executivo

Esta execução corrigiu a governança da integração Sankhya sem ampliar o escopo funcional do provider. A configuração principal saiu da navegação implícita de backoffice e passou a ter console explícito no contexto do tenant, as rotas tenant-scoped foram alinhadas ao padrão de `AsyncSession` com `get_session()` compatível com RLS, e a credencial do ERP deixou de ser persistida em texto puro.

## 2. Alterações realizadas

- Backend Sankhya migrado para `AsyncSession` e consultas com `select(...)`.
- Rotas Sankhya tenant-scoped migradas de `get_db()` para `get_session()`.
- Escopo do tenant corrigido para `get_tenant_id`, sem uso de `UnidadeProdutiva`.
- Proteção real de credenciais adicionada com criptografia simétrica derivada de `integrations_secret_key` ou `jwt_secret_key`.
- Respostas de configuração passaram a expor apenas `password_configured` e `password_mask`.
- Atualização sem nova senha preserva a credencial existente.
- Rotação de senha passou a ser suportada no mesmo endpoint de configuração.
- Navegação do tenant ganhou entrada própria para `Administração -> Integrações ERP`.
- Rota legada `/integracoes/sankhya` preservada via redirect para o console do tenant.
- Backoffice mantido apenas como observabilidade e suporte, com texto explícito de governança.

## 3. Como ficou o console do tenant

Console principal:

`/dashboard/settings/integracoes/erp`

Função:

- configurar conexão do Sankhya;
- atualizar credenciais;
- testar conexão;
- executar sincronizações manuais;
- visualizar logs operacionais do próprio tenant.

Permissão principal:

- `integrations:view`
- `integrations:configure`
- `integrations:test`
- `integrations:sync`
- `integrations:logs:view`

## 4. Como ficou o backoffice

Backoffice permaneceu em:

`/dashboard/backoffice/integracoes/erp`

Função após a correção:

- observabilidade;
- health;
- status resumido;
- diagnóstico;
- suporte;
- atalho para o console do tenant.

O backoffice deixou de se apresentar como casa principal da configuração do ERP do cliente.

## 5. Como ficou o RBAC

Frontend:

- adicionadas permissões de tenant para integrações ERP;
- adicionadas permissões específicas de backoffice para observação e suporte.

Backend:

- rotas Sankhya protegidas por `require_tenant_permission(...)` com permissões de integrações;
- configuração do tenant não depende mais de permissões de backoffice.

## 6. Como ficou Connection × Credential

Sem criar migration, a separação foi aplicada no desenho do código:

- `ws_url`, `username`, `sync_interval` permanecem tratados como parâmetros operacionais de conexão;
- `password` passou a ser tratado como credencial protegida;
- serializer de configuração expõe apenas estado mascarado da credencial.

Limitação deliberada:

- a tabela física ainda mantém os campos na mesma entidade `SankhyaConfig`;
- a separação estrutural completa entre `Connection` e `Credential` depende de evolução futura do domínio Integrações, não desta correção governada.

## 7. Como ficou a segurança de credenciais

- senha não é mais persistida em texto puro;
- senha não retorna ao frontend;
- resposta expõe apenas `password_configured` e `password_mask`;
- atualização sem senha nova mantém a atual;
- rotação de senha substitui a credencial criptografada;
- compatibilidade legada preservada para registros antigos em texto puro durante a transição.

## 8. Como ficou RLS/sessão

- rotas tenant-scoped do Sankhya passaram a usar `get_session()`;
- o contexto de tenant segue o mecanismo oficial do projeto para `SET LOCAL app.current_tenant_id`;
- filtros por `tenant_id` foram mantidos como defesa complementar.

## 9. Compatibilidade preservada

Fluxos preservados:

- configuração;
- teste de conexão;
- status;
- logs;
- sync de pessoas;
- sync de produtos;
- NFe;
- financeiro.

Compatibilidades mantidas:

- rota legada web `/integracoes/sankhya` agora redireciona;
- registros legados com senha antiga continuam legíveis para uso operacional até rotação.

## 10. Limitações restantes

- não foi implementado domínio de `Estabelecimento`;
- o escopo continua `TENANT`, apenas preparado documentalmente para futura extensão por `ESTABELECIMENTO`;
- não houve refatoração completa do provider para `IntegrationConnection` e `IntegrationCredential` persistentes separados;
- o backoffice ainda consome status/logs do provider atual, sem um subdomínio oficial de observabilidade de integrações.

## 11. Testes executados

- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py -q`
- `services/api/.venv/bin/ruff check services/api/integracoes/sankhya services/api/integracoes/security.py services/api/tests/unit/integracoes`
- `cd apps/web && pnpm exec eslint src/components/integracoes/sankhya-console.tsx src/components/layout/app-sidebar.tsx src/lib/permissions.ts src/lib/sidebar-config.ts 'src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx' src/app/integracoes/sankhya/page.tsx 'src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx'`
- `cd apps/web && pnpm exec tsc --noEmit`
- `git diff --check`

## 12. Próxima execução recomendada

`INTEGRATIONS-EXEC-01` ou equivalente de implementação oficial do domínio Integrações, com foco em:

- modelo persistente genérico de `IntegrationConfig`, `IntegrationConnection`, `IntegrationCredential`, `IntegrationHealth` e `IntegrationLog`;
- observabilidade oficial separada do provider Sankhya;
- preparação para escopo por `ESTABELECIMENTO` sem quebrar o tenant atual.
