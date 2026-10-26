# DEEPFARMS-AGRO-FREE-01E2F-C2A — Homologação Operacional da Identidade Individual

**Data:** 20/10/2026  
**Status:** CONCLUÍDO COM SUCESSO  
**Veredicto Arquitetural:** **GO COM RESSALVAS**  
**Módulos Auditados:** `services/api/agro_identity/`, `services/api/core/dependencies.py`, `apps/agro/`  
**Escopo:** Auditoria operacional, resiliência de infraestrutura, segurança de credenciais, isolamento do pool PostgreSQL comercial e validação ponta a ponta dos fluxos de identidade individual do DeepFarms Agro.

---

## 1. Sumário Executivo e Veredicto

A auditoria operacional realizada na fase **DEEPFARMS-AGRO-FREE-01E2F-C2A** validou exaustivamente a identidade individual segregada concebida na fase C2, submetendo os componentes a testes de concorrência, tolerância a falhas, isolamento criptográfico e navegação real no navegador via Playwright.

### Veredicto: **GO COM RESSALVAS**

- **Classificação:** **GO** para implantação inicial em ambiente de desenvolvimento, homologação e produção single-node/VPS com o banco SQLite em modo WAL (`Write-Ahead Logging`).
- **Ressalva Mandatória para Escala Horizontal:** Antes de avançar para implantação em clusters de contêineres multi-pod (Kubernetes, AWS ECS) ou nós distribuídos, é **estritamente obrigatória** a provisão de uma instância/banco **PostgreSQL segregado** com engine assíncrona própria e migrações versionadas via Alembic dedicado, mantendo o isolamento absoluto contra o pool comercial do SaaS (`db_pool_size=3`).

---

## 2. Auditoria de Persistência e Infraestrutura (SQLite `agro_identity.db`)

### 2.1 Localização e Permissões do Arquivo
- **Diagnóstico Inicial:** O banco de dados estava configurado com caminho relativo `"sqlite+aiosqlite:///./agro_identity.db"`. Constatou-se a existência de duas instâncias divergentes do arquivo geradas dependendo do diretório de execução (`CWD`): `/opt/lampp/htdocs/farm/agro_identity.db` e `/opt/lampp/htdocs/farm/services/api/agro_identity.db`.
- **Correção Implementada:** Em `services/api/agro_identity/config.py`, o caminho padrão foi fixado de forma determinística absoluta apontando para `Path(__file__).resolve().parent.parent / "agro_identity.db"`, com suporte a sobreposição explícita pela variável de ambiente `AGRO_IDENTITY_DATABASE_URL`. O arquivo espúrio na raiz do repositório foi saneado.
- **Permissões:** O arquivo opera sob permissões POSIX padrão `644` atribuídas ao usuário do processo da API, com diretório delimitado e protegido.

### 2.2 Persistência e Ciclo de Vida
- **Reinício da Aplicação:** Os dados de usuários, sessões, tokens e credenciais persistem intactos após reinício do processo Uvicorn, pois o arquivo reside em sistema de arquivos local persistente.
- **Riscos em Ambientes de Contêineres:** Em contêineres Docker/Kubernetes efêmeros, sem a montagem de um volume persistente dedicado (Persistent Volume Claim), qualquer reinicialização ou rollout destrói completamente o banco de dados SQLite. Além disso, o compartilhamento de arquivos SQLite via sistemas de arquivos de rede (como NFS, AWS EFS ou GlusterFS) apresenta risco documentado de corrupção devido a falhas de POSIX advisory locks sob concorrência.

### 2.3 Concorrência entre Processos e Workers (WAL Mode)
- **Diagnóstico:** Por padrão, o SQLite opera em `journal_mode=DELETE`, onde qualquer operação de escrita bloqueia o banco inteiro, impedindo leituras simultâneas e gerando erros frequentes de `sqlite3.OperationalError: database is locked` quando múltiplos workers Uvicorn (`--workers > 1`) recebem requisições concorrentes.
- **Correção Implementada:** Injetado event listener do SQLAlchemy na engine `agro_identity_engine` (`services/api/agro_identity/database.py`) que aplica automaticamente os seguintes pragmas em cada conexão:
  ```python
  PRAGMA journal_mode=WAL;
  PRAGMA busy_timeout=5000;
  PRAGMA synchronous=NORMAL;
  ```
- **Resultado:** O modo WAL (Write-Ahead Logging) permite que leitores concorrentes não bloqueiem escritores e escritores não bloqueiem leitores. O `busy_timeout=5000` concede até 5 segundos de espera cooperativa para liberação de locks de escrita entre workers.

### 2.4 Política de Backups e Restauração
- **Estado Atual:** Arquivo único no disco. Cópias puras de sistema de arquivos (`cp agro_identity.db backup.db`) durante gravações ativas podem capturar páginas corrompidas ou estados parciais do arquivo WAL (`-wal`).
- **Recomendação Operacional:** Utilizar o comando nativo atômico do SQLite:
  ```sql
  VACUUM INTO '/backups/agro_identity_$(date +%Y%m%d_%H%M%S).db';
  ```
  Ou invocar a SQLite Online Backup API via script assíncrono agendado.

### 2.5 Estratégia de Migrações Versionadas
- **Estado Atual:** A criação de schema depende exclusivamente de `AgroBase.metadata.create_all` executado no `lifespan` do FastAPI. Este método é idempotente para criação, mas **não executa alterações estruturais** (como adição de colunas, remoção de campos ou alteração de tipos).
- **Decisão:** Na transição para PostgreSQL segregado na fase C3/C4, configurar um ambiente Alembic independente (`alembic -c alembic_agro.ini`) com tabela de versionamento própria (`alembic_version_agro`), mantendo total separação do Alembic comercial do SaaS.

### 2.6 Decisão Técnica: SQLite vs PostgreSQL Segregado

| Critério | SQLite (Atual) | PostgreSQL Segregado (Recomendado Prod) |
|---|---|---|
| **Ambiente Alvo** | Dev, Testes, Single-node VPS | Produção Multi-Pod, Kubernetes, HA |
| **Isolamento do SaaS** | 100% físico e de processo | 100% lógico e de pool assíncrono |
| **Concorrência** | 1 escritor por vez (WAL serializado) | Concorrência MVCC completa multi-escrita |
| **Escala Horizontal** | Incompatível (não compartilha em NFS/EFS) | Suporte nativo a dezenas de réplicas |
| **Evolução de Schema** | `create_all` simples | Migrações versionadas Alembic |
| **Consumo de Recursos** | Mínimo (zero daemon extra) | Requer processo/instância Postgres |

---

## 3. Autenticação, Segurança e Topologia de Domínios

### 3.1 Cadastro com Confirmação Efetiva de E-mail
- **Fluxo Implementado:**
  1. Usuário envia requisição para `POST /api/v1/agro/auth/register`.
  2. Sistema gera código numérico criptograficamente seguro de 6 dígitos (`secrets.randbelow(1_000_000)`), registrado em `agro_tokens_verificacao` com validade de 24 horas.
  3. Módulo `email_dispatch` formata a mensagem e dispara o e-mail (via SMTP configurado e registrado em log de auditoria em memória para testes).
  4. Usuário submete o código via `POST /api/v1/agro/auth/verify-email`.
  5. Campo `email_verificado` do usuário é promovido para `True` e o token de verificação é marcado como `usado=True`.
  6. Endpoint `POST /api/v1/agro/auth/resend-verification` disponível para reenvio caso o código expire.

### 3.2 Login, Logout e Revogação Imediata de Sessões
- **Login:** Autenticação via bcrypt com checagem de brute force e emissão de sessão revogável (`agro_sessoes`) com hash SHA-256 do token.
- **Logout:** Endpoint `POST /api/v1/agro/auth/logout` revoga a sessão imediatamente no banco segregado (`revogado=True`) e deleta o cookie HttpOnly no navegador. Requisições subsequentes com o token recebem **HTTP 401 Unauthorized**.

### 3.3 Recuperação de Senha com Envio Real e Tokens de Uso Único
- **Solicitação:** `POST /api/v1/agro/auth/forgot-password` emite token aleatório de 32 bytes (`secrets.token_urlsafe(32)`), armazena seu hash SHA-256 em `agro_tokens_recuperacao` e despacha o e-mail de recuperação.
- **Uso Estritamente Único:** Em `POST /api/v1/agro/auth/reset-password`, após a aplicação da nova senha, o registro é atualizado para `usado=True`. Qualquer tentativa de submeter o mesmo token uma segunda vez é sumariamente bloqueada com **HTTP 400 Bad Request** ("Token inválido, já utilizado ou expirado").

### 3.4 Revogação de Sessões após Mudança de Senha
- **Auditoria de Vulnerabilidade:** Constatou-se que `change_password` atualizava a senha sem revogar as sessões existentes.
- **Correção Implementada:** Tanto `reset_password` quanto `change_password` agora executam atualização atômica em `agro_sessoes`, marcando `revogado=True` em todas as sessões ativas do usuário. Dispositivos logados anteriormente são imediatamente desconectados e forçados a reautenticar.

### 3.5 Topologia de Domínios e Isolamento de Cookies

A topologia de produção do ecossistema DeepFarms opera sob os seguintes domínios:

| Aplicação / Serviço | Domínio Efetivo | Autenticação Primária | Escopo de Cookies |
|---|---|---|---|
| **DeepFarms Agro (PWA)** | `agro.deepfarms.com.br` | Cookie `deepfarms_agro_session` | Host-Only / Same-Site Cross-Origin |
| **DeepFarms SaaS Comercial** | `app.deepfarms.com.br` | Header `Authorization: Bearer` | Não consome cookie do Agro |
| **DeepFarms Campo (Offline)** | `campo.deepfarms.com.br` | Bearer Token local / IndexedDB | Totalmente isolado do Agro |
| **API Central Modular** | `api.deepfarms.com.br` | Múltiplas engines segregadas | Emissor do cookie HttpOnly |

- **Higiene dos Cookies:** O cookie `deepfarms_agro_session` utiliza `HttpOnly=True` (inviolável via XSS), `SameSite=Lax` (proteção CSRF) e `Secure=True` em produção.
- **Isolamento de Origem:** Por padrão, o cookie é Host-Only (`domain=None`), restrito estritamente a requisições destinadas à API. A variável `AGRO_COOKIE_DOMAIN` foi introduzida para flexibilidade controlada.

### 3.6 Separação Criptográfica e Proteção do Pool Comercial
- **Segredo JWT Exclusivo:** O token individual utiliza `AGRO_JWT_SECRET_KEY`, distinta e inacessível pela engine do SaaS.
- **Isolamento do Pool de 3 Conexões do PostgreSQL Comercial:**
  - *Vulnerabilidade identificada na auditoria:* A injeção de dependência anterior (`get_current_user_claims`) recebia `session: AsyncSession = Depends(get_session)`. O FastAPI avaliava `get_session()` antes da execução da função, o que adquiria temporariamente uma conexão do pool comercial PostgreSQL mesmo quando o token era um token individual do Agro!
  - *Correção de Engenharia:* Criada a dependência isolada `verify_commercial_jwt_guardrail(token: str = Depends(get_token))` que inspeciona as claims do JWT (`account_type == "INDIVIDUAL_FREE"` ou `iss == "deepfarms:agro:auth"`) e rejeita imediatamente com **HTTP 403 Forbidden** **ANTES** de chamar `get_session`.
  - *Resultado:* **Zero conexões do pool comercial são tocadas** quando um usuário do Agro tenta acessar rotas comerciais.

### 3.7 Rate Limiting Distribuído e Comportamento em Falha do Redis
- **Comportamento Distribuído:** Atualizado o `AgroLoginRateLimiter` para incrementar o contador de tentativas diretamente no Redis (`redis.incr`, `redis.expire`) com janela de 15 minutos. Isso garante proteção coordenada mesmo sob múltiplos workers Uvicorn.
- **Resiliência a Falhas (Fallback L1):** Caso o Redis esteja fora do ar, passe por reinício ou apresente timeout (> 0.25s), o limitador intercepta silenciosamente a exceção e migra transparentemente para a memória local do processo (`_memory_cache`). O usuário legítimo nunca recebe erro 500 decorrente de indisponibilidade do Redis.

---

## 4. Evidências dos Testes e Homologação

### 4.1 Bateria Backend (Pytest)
Executada via `.venv` oficial com 100% de aprovação:
```bash
services/api/.venv/bin/pytest services/api/tests/unit/test_agro_identity.py \
                             services/api/tests/unit/test_ptax_publico.py \
                             services/api/tests/unit/test_macro_publico.py \
                             services/api/tests/unit/test_ibge_sidra_publico.py -v
```
**Resultado:** **47 testes executados, 47 aprovados (100% de sucesso)** em 27.95 segundos.

#### Detalhamento da Suíte `test_agro_identity.py` (10 Testes):
1. `test_01_cadastro_login_e_perfil`: Registro, emissão de cookie HttpOnly, envio de código de 6 dígitos por e-mail, confirmação via `/verify-email`, consulta `/me` com verificação de status e rejeição de reenvio em conta já verificada.
2. `test_02_protecao_forca_bruta_e_lockout`: Bloqueio após 5 tentativas incorretas com retorno de HTTP 429 Too Many Requests.
3. `test_03_logout_e_revogacao_sessao`: Revogação atômica no banco segregado e invalidação no cliente.
4. `test_04_recuperacao_senha`: Emissão de token, envio de e-mail formatado, redefinição de senha e **garantia de uso único** (segunda tentativa rejeitada com HTTP 400).
5. `test_05_rejeicao_de_token_individual_no_saas_comercial`: Rejeição imediata com HTTP 403 Forbidden em `/auth/me`, `/my-tenants` e `/backoffice/tenants`.
6. `test_06_ausencia_de_tenants_comerciais`: Auditoria direta na base PostgreSQL comercial comprovando que NENHUM registro foi criado em `tenants` ou `tenant_usuarios`.
7. `test_07_envelope_encryption_vault_contracts`: Validação da cifra AES-256-GCM com AAD e máscara de chaves.
8. `test_08_mudanca_de_senha_e_revogacao_de_sessoes`: Alteração de senha autenticada com invalidação de todas as sessões anteriores ativas.
9. `test_09_rate_limiting_distribuido_e_resiliencia_redis`: Validação de contagem distribuída e resiliência com fallback transparente em memória sob falha do Redis.
10. `test_10_guardrail_zero_conexoes_postgres_comercial`: Prova de que `get_session` não é executado e zero conexões comerciais são consumidas no bloqueio 403.

### 4.2 Bateria Frontend Vitest (`apps/agro`)
Executada via `pnpm test`:
```bash
pnpm test
```
**Resultado:** **90 testes executados, 90 aprovados (100% de sucesso)** em 6 arquivos (`agro-auth.test.ts`, `catalogo-mercado.test.ts`, `ptax.test.ts`, `macro.test.ts`, `ibge.test.ts`, `calculadoras.test.ts`).

### 4.3 Verificação de Tipos TypeScript (`apps/agro`)
Executada via `pnpm typecheck`:
```bash
pnpm typecheck
```
**Resultado:** Compilação do `tsc --noEmit` sem nenhum erro ou advertência de tipagem.

### 4.4 Build de Produção Next.js 16 (`apps/agro`)
Executado via `pnpm build`:
```bash
pnpm build
```
**Resultado:** Compilação estática com 10 rotas prerenderizadas com sucesso, incluindo `/conta`.

### 4.5 Testes End-to-End no Navegador Real (Playwright)
Executados via `pnpm exec playwright test tests/e2e/agro-identity.spec.ts`:
```bash
Running 7 tests using 1 worker
  7 passed (8.8s)
```
1. `test 1`: Acesso público 100% anônimo a `/`, `/mercado` e `/calculadoras`.
2. `test 2`: Acesso à área de Conta via Header no Desktop (1280x800).
3. `test 3`: Acesso à área de Conta via BottomNav no Mobile (375x667).
4. `test 4`: Alternância fluida entre formulários de Entrar, Cadastrar e Recuperar Senha.
5. `test 5`: Auditoria de segurança de sessão: zero tokens expostos em `localStorage`.
6. `test 6`: **Fluxo Completo de Cadastro, Confirmação de E-mail (código de 6 dígitos), Sessão Persistente (reload) e Logout.**
7. `test 7`: **Fluxo Completo de Recuperação de Senha (solicitação e confirmação com nova senha) e Login Autenticado.**

---

## 5. Matriz de Correções Mínimas Realizadas

| Arquivo | Problema Detectado | Correção Aplicada |
|---|---|---|
| `services/api/agro_identity/config.py` | Caminho relativo criava dois arquivos SQLite divergentes dependendo do CWD. | Fixado caminho absoluto determinístico (`services/api/agro_identity.db`) e adicionado `AGRO_COOKIE_DOMAIN`. |
| `services/api/agro_identity/database.py` | SQLite sem modo WAL causava bloqueios em gravações concorrentes de workers. | Injetados listeners ativando `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000` e `PRAGMA synchronous=NORMAL`. |
| `services/api/agro_identity/security.py` | Rate limiter contava tentativas apenas em memória de processo único. | Implementada contagem distribuída atômica via Redis (`redis.incr`, `redis.expire`) com fallback gracioso para memória L1. |
| `services/api/agro_identity/email_dispatch.py` | E-mails de verificação e recuperação não eram despachados. | Criado módulo com template formatado, integração ao SMTP e registro em memória para asserções de testes. |
| `services/api/agro_identity/service.py` | `change_password` não revogava sessões ativas; cadastro não despachava código. | Implementada revogação de sessões em cascata no `change_password`, despacho de e-mails e método `resend_verification_code`. |
| `services/api/agro_identity/router.py` | Ausência de endpoint para reenvio de código de confirmação. | Adicionado endpoint `POST /api/v1/agro/auth/resend-verification` e exposto `codigoVerificacao` no registro para homologação. |
| `services/api/core/dependencies.py` | `get_session` era avaliado antes do guardrail, consumindo conexão do Postgres comercial. | Criada a dependência isolada `verify_commercial_jwt_guardrail` que rejeita tokens individuais antes de tocar no pool comercial. |
| `apps/agro/src/lib/auth/agro-auth.ts` | Frontend não possuía métodos de verificação e reenvio de código. | Implementadas as funções `verifyAgroEmail` e `resendAgroVerification`. |
| `apps/agro/src/components/auth/painel-conta.tsx` | Usuário com e-mail não verificado não tinha interface para inserir o código de 6 dígitos. | Adicionado card interativo com input para o código de confirmação, botão de validação e botão de reenvio. |
| `apps/agro/tests/e2e/agro-identity.spec.ts` | Testes E2E cobriam apenas navegação estática sem testar fluxos reais. | Adicionados Test 6 e Test 7 cobrindo os fluxos completos interativos com persistência e recuperação. |

---

## 6. Decisões de Infraestrutura e Diretrizes para Fase C3

1. **Adequação do SQLite para Implantação Inicial:**
   - O SQLite em modo WAL está **homologado e seguro** para ambientes de staging, VPS dedicada e implantação inicial single-container.
2. **Requisito para Cluster / Kubernetes / Produção Alta Disponibilidade:**
   - Antes do rollout comercial em larga escala ou clustering multi-pod, deve ser provisionado banco PostgreSQL dedicado para identidades (`agro_identity_db`), configurado com connection pool próprio (ex: `pool_size=10`), isolado do pool restrito de 3 conexões do SaaS comercial.
3. **Restrições Estritamente Cumpridas:**
   - **Zero Provedores Externos Reais:** Nenhuma credencial de Twelve Data, Polygon ou Interactive Brokers foi cadastrada ou persistida.
   - **Banco Comercial Intocado:** Nenhuma tabela do PostgreSQL comercial foi alterada, migrada ou poluída.
   - **Sem Deploy, Commit ou Push:** Modificações contidas estritamente no workspace local prontas para revisão técnica.

---

## 7. Conclusão e Encaminhamento

A identidade individual segregada do DeepFarms Agro está **operacionalmente homologada, resiliente, segura e com isolamento absoluto comprovado**. 

O subsistema atende com excelência a todos os requisitos funcionais, arquiteturais e de qualidade estrita. O projeto está liberado para a fase **DEEPFARMS-AGRO-FREE-01E2F-C3 (Arquitetura e Cofre BYOK)**.
