# AGRO-ADMIN-01B1 — Fundação Segura da Identidade Unificada

**Data da homologação local:** 23/10/2026  
**Escopo:** fundação aditiva, sem migração de usuários e sem cutover  
**Veredicto:** **GO COM RESSALVAS**

## Resultado

A identidade global existente em `usuarios` passou a admitir cadastro gratuito e sessão revogável sem tenant. O contrato comercial anterior `/api/v1/auth/register` foi preservado; o novo contrato é `POST /api/v1/auth/register-free`, com nome, e-mail e senha, sem CPF e sem criação de tenant.

O login central agora persiste `SessaoAtiva` mesmo quando `tenant_id` é nulo. Tokens novos incluem assinatura, expiração, `iss`, `aud`, `iat`, `jti`, versão, tipo de conta, escopo de produto e exigência de sessão persistida. Tokens `INDIVIDUAL_FREE` são rejeitados pelo guardrail comercial antes da aquisição do contexto comercial, inclusive quando contêm uma claim `tenant_id` indevida.

O fluxo ativo do PWA Agro, seu SQLite, cookies e endpoints `/api/v1/agro/auth/*` não foram alterados. Nenhum usuário, tenant, segredo BYOK ou registro real foi migrado.

## Componentes reutilizados

- `Usuario` como identidade canônica global, sem `tenant_id`.
- `AuthService`, bcrypt e as políticas de senha existentes.
- `SessaoAtiva`, hash SHA-256 do JWT, expiração por inatividade e revogação.
- `LoginRateLimitService` no login e um limitador específico de cadastro com Redis e fallback local.
- JWT e o segredo/algoritmo já configurados na plataforma.
- Recuperação de senha central, agora compatível com conta sem tenant e sem enumeração no campo `email` da resposta.
- Guardrail comercial, permissões, vínculo `TenantUsuario`, troca de tenant e convites existentes.
- Cookies HttpOnly e proteção CSRF do PWA Agro, mantidos sem mudança.

## Arquivos modificados nesta etapa

### Backend

- `services/api/core/config.py`
- `services/api/core/dependencies.py`
- `services/api/core/schemas/auth_schemas.py`
- `services/api/core/services/auth_service.py`
- `services/api/core/services/free_registration_rate_limit.py`
- `services/api/core/routers/auth.py`
- `services/api/core/routers/sessions.py`
- `services/api/core/services/onboarding_service.py`
- `services/api/core/routers/team.py`
- `services/api/core/cadastros/pessoas/router.py`
- `services/api/core/routers/support_ws.py`

### Migration e diagnóstico

- `services/api/migrations/versions/20261022_agro_admin_01b1_session_nullable.py`
- `services/api/scripts/diagnosticar_migracao_identidade_agro.py`

### Testes

- `services/api/tests/unit/core/test_auth.py`
- `services/api/tests/unit/core/test_free_registration.py`
- `services/api/tests/unit/core/test_unified_identity_foundation.py`

Nenhum arquivo do PWA Agro foi modificado por esta etapa.

## Cadastro gratuito

O endpoint novo retorna HTTP 202 e a mesma mensagem para criação e e-mail já existente. O serviço calcula bcrypt antes da decisão de duplicidade, não devolve identificador da conta e normaliza o e-mail para minúsculas.

O username é derivado da parte local do e-mail, normalizado para ASCII e limitado a 40 caracteres. A inserção ocorre em savepoint e depende das constraints únicas do banco; colisões de username recebem sufixo criptograficamente aleatório. O teste com seis requisições concorrentes para o mesmo e-mail criou exatamente um usuário.

O rate limit de cadastro usa chave derivada por SHA-256 do IP, limite padrão de cinco tentativas em 15 minutos, Redis compartilhado quando disponível e fallback conservador em memória. Nenhum IP puro é usado na chave.

Convites passaram a normalizar o e-mail e a procurar `Usuario` de forma case-insensitive. Assim, uma conta gratuita preexistente pode receber vínculo comercial posteriormente pelo fluxo de convite, sem duplicação da identidade.

## Migration

Revision criada:

```text
20260926_material_requisition_01g
  -> 20261022_agro_admin_01b1
```

Upgrade gerado para PostgreSQL:

```sql
ALTER TABLE farms.sessoes_ativas ALTER COLUMN tenant_id DROP NOT NULL;
```

O downgrade restaura `NOT NULL`, mas interrompe explicitamente se ainda existirem sessões globais com `tenant_id IS NULL`, evitando perda silenciosa de sessões. O ORM já declarava a coluna como nullable; a migration reconcilia o DDL físico.

Validações realizadas:

- `alembic heads`: uma única head, `20261022_agro_admin_01b1`.
- geração offline com dialeto PostgreSQL: aprovada.
- compilação Python da revision: aprovada.
- aplicação em banco comercial: **não executada**, conforme restrição.
- aplicação em PostgreSQL isolado: **pendente**; o ambiente não possui daemon Docker ativo nem binário de servidor PostgreSQL. A tentativa de iniciar daemon temporário em `/tmp` falhou por ausência de privilégio de daemon, sem acessar banco externo.

## JWT, sessões e isolamento comercial

Tokens v2 novos são validados com:

- assinatura HS256 configurada;
- expiração;
- emissor `deepfarms:identity`;
- audiência `deepfarms:platform`;
- `account_type` conhecido;
- `product_scope` coerente;
- contexto de tenant coerente;
- sessão persistida quando `session_required=true`.

Contas gratuitas recebem `account_type=INDIVIDUAL_FREE`, `product_scope=["agro:free"]` e `tenant_id=null`. Contas comerciais recebem escopo `saas`; administradores de plataforma recebem `backoffice`.

O guardrail comercial rejeita tokens gratuitos e tokens do emissor legado do Agro antes da dependência de sessão comercial. Além disso, `get_tenant_id` agora confirma o vínculo `TenantUsuario` ativo para usuários não superadministradores mesmo quando o JWT já contém `tenant_id`. Uma claim isolada não concede acesso comercial.

Tokens comerciais v1 já emitidos continuam aceitos temporariamente sem validação de `iss`/`aud`, para evitar cutover nesta fundação. Todos os tokens novos são v2 e seguem validação estrita. A retirada da compatibilidade v1 depende da expiração/revogação das sessões antigas.

Rotas de sessão do próprio usuário e logout usam a identidade global, permitindo listar e revogar sessões sem tenant. Rotas de equipe continuam protegidas pelas permissões comerciais e pelo tenant.

## Cookies, CSRF e precedência

O PWA Agro continua usando `deepfarms_agro_session`, HttpOnly, `SameSite=Lax`, `Secure` em produção e domínio configurável. Os guardrails existentes de `Origin`, `Referer` e `Sec-Fetch-Site` permanecem ativos para mutações.

O núcleo SaaS continua usando Bearer. Esta etapa não introduziu cookie compartilhado, domínio cruzado ou nova precedência cookie/Bearer, pois isso alteraria o login ativo do PWA. A definição dessa precedência permanece condição do cutover futuro; até lá, não existe ambiguidade entre os dois transportes.

## Diagnóstico de migração futura

O utilitário `diagnosticar_migracao_identidade_agro.py`:

- abre o SQLite com `mode=ro` e `PRAGMA query_only=ON`;
- usa transação PostgreSQL `READ ONLY` quando um DSN de destino é fornecido;
- compara colisões case-insensitive de e-mail e UUID;
- verifica formato UUID e compatibilidade bcrypt;
- contabiliza sessões, tokens de recuperação, tokens de verificação e credenciais BYOK;
- não imprime e-mail, hash de senha ou segredo; usa fingerprint de e-mail;
- não insere, atualiza ou exclui dados.

O cofre BYOK vincula tanto a KEK derivada quanto o AAD aos bytes do UUID do usuário. Portanto, preservar o UUID é a estratégia preferida. Qualquer remapeamento exige decifragem com o UUID antigo e recifragem controlada com o UUID novo. BYOK não pode ser copiado diretamente.

Não foi executado diagnóstico sobre dados reais nesta etapa.

## Isolamento operacional e concorrência

Clima e Mercado continuaram aprovados sem mudança de contrato. As configurações `db_pool_size=3` e `db_max_overflow=2` não foram alteradas.

O cadastro concorrente foi validado com seis sessões independentes em SQLite temporário. Para dimensionamento real, ainda é necessário repetir o cenário em PostgreSQL efêmero com concorrência crescente, registrar p50/p95/p99, espera por conexão e taxa de conflito, antes de ajustar o pool. Não há evidência nesta etapa que justifique aumento automático.

## Matriz de testes

| Verificação | Resultado | Evidência |
|---|---:|---|
| Cadastro gratuito sem tenant/CPF | PASS | endpoint e serviço em banco temporário |
| Resposta sem enumeração | PASS | criação e duplicidade retornam o mesmo HTTP 202 e corpo |
| Concorrência e unicidade | PASS | 6 tentativas simultâneas, 1 usuário persistido |
| Username com proteção por constraint/savepoint | PASS | caminho de colisão implementado e banco temporário |
| Login sem tenant | PASS | sessão criada com `tenant_id=None` |
| Login SaaS legado | PASS | suíte `test_auth.py` |
| Sessão global obrigatória e revogável | PASS | token de login sem sessão é rejeitado; rotas próprias usam identidade global |
| Token gratuito em rota comercial | PASS | HTTP 403 no guardrail |
| Claim de tenant sem vínculo | PASS | HTTP 403 antes da ativação do tenant |
| Emissor, audiência, expiração e escopo | PASS | testes JWT v2, incluindo audiência inválida |
| Convites comerciais | PASS | resolução case-insensitive da identidade global |
| Recuperação de senha | PASS | mesma resposta para conta existente/inexistente; Agro também aprovado |
| Cookies e CSRF Agro | PASS | suíte de identidade Agro aprovada, fluxo não alterado |
| BYOK e dependência criptográfica do UUID | PASS | suíte BYOK e inspeção do envelope/AAD |
| Clima, Mercado, PTAX, macro e IBGE/SIDRA | PASS | suíte pública focada |
| Backend focado final | **153 PASS** | 35 warnings de depreciação preexistentes |
| PWA Agro unitário | **155 PASS** | 11 arquivos de teste |
| PWA Agro lint/typecheck/build | PASS | Next.js 16.1.6 |
| SaaS lint/typecheck/build | PASS | build de 264 páginas; avisos de rotas dinâmicas não impediram build |
| Campo lint/typecheck/build | PASS | PWA e service worker compilados |
| Ruff dos arquivos novos | PASS | sem erro |
| `git diff --check` | PASS | sem whitespace inválido |
| Alembic SQL offline PostgreSQL | PASS | `DROP NOT NULL` gerado corretamente |
| Alembic upgrade/downgrade em PostgreSQL isolado | **PENDENTE** | servidor/daemon isolado indisponível |
| Suíte unitária backend completa | **INCONCLUSIVA** | interrompida em 19%; fixtures tentam integração e vários testes exigem PostgreSQL |

Na tentativa segura da suíte completa, `DATABASE_URL` foi forçada para SQLite temporário para impedir o fallback do `tests/conftest.py` ao PostgreSQL comercial. Foram observadas falhas preexistentes de dialeto e contratos de baseline, incluindo contagens esperadas 344/373 contra 347/376 e um teste legado de flush. A execução parou em testes com integração implícita. Nenhuma dessas falhas ocorreu nas 153 verificações focadas aprovadas.

## Riscos remanescentes

1. A migration ainda não foi executada em PostgreSQL efêmero; este é o principal bloqueio para GO definitivo.
2. O índice único atual de `usuarios.email` é case-sensitive no PostgreSQL. O novo cadastro sempre grava lowercase e consulta case-insensitive, mas o dry-run deve confirmar que não existem colisões históricas por caixa antes de considerar um índice funcional `lower(email)` em etapa própria.
3. Tokens comerciais v1 permanecem em modo de compatibilidade até a expiração/revogação planejada.
4. O rate limit em memória é por processo quando Redis está indisponível. Ambientes com múltiplos workers devem manter Redis saudável.
5. A suíte completa precisa de fixtures que proíbam por construção o fallback para banco comercial e provisionem PostgreSQL temporário.
6. Não foi realizado teste de carga PostgreSQL; somente concorrência funcional em banco temporário.

## Condições para migrar usuários

Antes de autorizar a migração controlada:

1. Provisionar PostgreSQL efêmero e executar upgrade, criação/login/logout sem tenant, downgrade após limpeza explícita das sessões nulas e novo upgrade.
2. Executar o diagnóstico read-only contra cópias isoladas dos dois bancos e resolver colisões de e-mail/UUID.
3. Preservar UUID quando houver BYOK; caso contrário, aprovar procedimento de recifragem com trilha de auditoria.
4. Definir preservação de `email_verificado` e mapeamento explícito de sessões/tokens, sem reaproveitar tokens ativos entre emissores.
5. Remover o fallback de testes para o banco comercial e aprovar a suíte completa em PostgreSQL descartável.
6. Planejar expiração dos JWTs v1 e somente então tornar `iss`/`aud` obrigatórios para todo token comercial.
7. Aprovar separadamente o cutover do PWA, incluindo cookie compartilhado, domínio, CSRF e precedência entre cookie e Bearer.

## Veredicto

**GO COM RESSALVAS para a fundação local.** O cadastro global gratuito, tokens v2, isolamento comercial, sessão nullable no código, revogação, convites e diagnóstico dry-run estão implementados e cobertos por testes. Não há autorização nem evidência suficiente para aplicar a migration ou migrar usuários. O GO definitivo para migração depende obrigatoriamente do ciclo Alembic em PostgreSQL isolado e da reconciliação read-only dos dados.

Não houve deploy, migration em produção, alteração do banco comercial, criação de tenant, cópia de SQLite, migração BYOK, commit ou push.
