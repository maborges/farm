# DEEPFARMS-AGRO-FREE-01E2F-C2 — Identidade Individual Segregada

**Data:** 19/10/2026  
**Status:** CONCLUÍDO COM SUCESSO  
**Módulo:** `services/api/agro_identity/`, `apps/agro/`  
**Escopo:** Implementação da fundação de identidade individual do DeepFarms Agro, persistência segregada, segurança criptográfica, isolamento estrito contra o PostgreSQL comercial e interface no PWA.

---

## 1. Revisão Arquitetural e Decisões Estratégicas

### 1.1 Repositório Persistente e Engine Segregada
A aplicação DeepFarms SaaS opera com PostgreSQL comercial sob pool de conexões estritamente restrito (`pool_size=3`, `max_overflow=0`, `pool_timeout=1.0s`), dimensionado para a operação de fazendas contratantes e isolamento RLS multi-tenant.
Para atender aos produtores rurais usuários do aplicativo gratuito DeepFarms Agro sem comprometer a estabilidade do SaaS:
- **Repositório Segregado:** Banco SQLite assíncrono independente (`agro_identity.db`), gerenciado por engine e sessionmaker dedicados (`agro_identity_engine` e `agro_async_session_maker`).
- **Zero Consumo do Pool Comercial:** Nenhuma requisição de registro, login, renovação ou consulta de conta individual consome slots da engine PostgreSQL comercial (`core.database.engine`).
- **Ciclo de Vida Independente:** A inicialização (`init_agro_db()`) e encerramento (`close_agro_db()`) do repositório ocorrem no `lifespan` do FastAPI de forma assíncrona, criando automaticamente o schema segregado sem depender de migrações no banco comercial.

### 1.2 Modelo de Dados e Isolamento de Tenants
- **Tabela Segregada `agro_usuarios`:** Armazena apenas usuários individuais com identificador global estável (`UUIDv4`), nome, e-mail único em minúsculas, hash bcrypt de senha e data de criação.
- **Ausência de Tenants:** Um cadastro no DeepFarms Agro **NUNCA** cria registros nas tabelas `tenants` ou `tenant_usuarios`. O usuário individual não possui vínculo com nenhuma pessoa jurídica ou fazenda comercial corporativa.
- **Tabela Segregada `agro_sessoes`:** Mantém sessões revogáveis persistidas com `token_hash` (SHA-256), IP, User-Agent, carimbo de expiração (`expira_em`) e status (`ATIVA`, `REVOGADA`, `EXPIRADA`).
- **Tabela Segregada `agro_tokens_recuperacao`:** Tokens criptográficos unívocos gerados via `secrets.token_urlsafe(32)` com hash SHA-256 e validade estrita de 60 minutos para redefinição de credenciais.

### 1.3 Separação Criptográfica de Tokens e Guardrails
- **Assinatura e Segredo Exclusivo:** O JWT individual utiliza segredo próprio (`AGRO_JWT_SECRET_KEY`), isolado da chave comercial do SaaS (`settings.jwt_secret_key`).
- **Claims Identitárias e Metadados:**
  - `iss`: `"deepfarms:agro:auth"`
  - `aud`: `"deepfarms:agro:app"`
  - `account_type`: `"INDIVIDUAL_FREE"`
  - `tenant_id`: `None`
  - `role`: `"INDIVIDUAL_USER"`
  - `scope`: `["agro:profile", "agro:byok"]`
- **Bloqueio Mandatório no SaaS Comercial:** Em `services/api/core/dependencies.py` (`get_current_user_claims`), o sistema inspeciona as claims não verificadas antes de qualquer validação com a chave comercial ou consulta ao banco de dados:
  ```python
  unverified_claims = jwt.get_unverified_claims(token)
  if (
      unverified_claims.get("account_type") == "INDIVIDUAL_FREE"
      or unverified_claims.get("iss") == "deepfarms:agro:auth"
  ):
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Tokens de identidade individual do DeepFarms Agro não possuem acesso aos recursos comerciais do SaaS.",
      )
  ```
  Isso garante que um token `INDIVIDUAL_FREE` seja sumariamente rejeitado com **HTTP 403 Forbidden** ao tentar acessar qualquer rota comercial (`/api/v1/auth/me`, `/api/v1/auth/my-tenants`, `/api/v1/backoffice/*`, módulos de pecuária, lavoura e financeiro).

### 1.4 Higiene de Sessões e Cookies HttpOnly
- O backend injeta a sessão individual através de cookie seguro `deepfarms_agro_session`:
  - `HttpOnly`: inacessível via JavaScript (imunidade contra roubo de sessão via XSS).
  - `SameSite=Lax`: mitigação de ataques CSRF mantendo navegabilidade externa fluida.
  - `Path=/`: escopo unificado para o aplicativo.
  - `Secure`: ativado automaticamente em ambientes de produção (`APP_ENV=production`).
- **Zero LocalStorage:** Nenhum token sensível é persistido no `localStorage` do frontend. O cliente transmite o cookie automaticamente via `credentials: "include"`.

---

## 2. Implementação do Módulo `services/api/agro_identity/`

O módulo foi estruturado com arquitetura limpa, tipagem estrita e testes abrangentes:

| Arquivo | Responsabilidade |
|---|---|
| `config.py` | Configurações do banco SQLite segregado, parâmetros JWT, cookies e chaves de envelope. |
| `database.py` | Engine SQLAlchemy assíncrona dedicada (`agro_identity_engine`), base declarativa `AgroBase` e ciclo de vida. |
| `models.py` | Entidades ORM: `AgroUsuario`, `AgroSessao`, `AgroTokenRecuperacao`, `AgroTokenVerificacao` e `AgroUserByokCredential`. |
| `schemas.py` | Schemas Pydantic v2 estritos para requisições e respostas de cadastro, login, perfil e recuperação. |
| `security.py` | Hashing com bcrypt, geração/validação de tokens JWT, manipulação de cookies e rate limiter contra força bruta. |
| `service.py` | Regras de negócio de identidade: cadastro com verificação de duplicidade, login, revogação de sessões e redefinição de senhas. |
| `dependencies.py` | Resolução do usuário individual autenticado via cookie ou cabeçalho Bearer com checagem de revogação. |
| `router.py` | Endpoints FastAPI expostos em `/api/v1/agro/auth` (`/register`, `/login`, `/logout`, `/me`, `/forgot-password`, `/reset-password`, `/change-password`, `/account`). |
| `vault_contracts.py` | Contratos e implementação de referência para Envelope Encryption (AES-256-GCM + KMS) do futuro cofre BYOK. |

### 2.1 Proteção Contra Força Bruta
Implementado o `AgroLoginRateLimiter`:
- Limite de **5 tentativas incorretas** consecutivas.
- Aplicação de **bloqueio temporário de 15 minutos** com retorno de **HTTP 429 Too Many Requests**.
- Suporte a contagem distribuída via Redis com fallback transparente em memória local (singleton thread-safe).
- Reset automático do contador após autenticação com credenciais válidas.

---

## 3. Arquitetura e Contrato do Futuro Cofre Segregado (BYOK)

Definido o contrato formal do cofre no arquivo `services/api/agro_identity/vault_contracts.py`:

### 3.1 Envelope Encryption e Criptografia Autenticada
- **Master Key (KEK - Key Encryption Key):** Gerenciada via KMS (AWS KMS, Google Cloud KMS ou HashiCorp Vault). Em ambiente local de desenvolvimento, utiliza chave mestra simétrica de 256 bits (`AGRO_VAULT_MASTER_KEY`).
- **Data Encryption Key (DEK):** Chave efêmera de 256 bits gerada sob demanda via gerador de números pseudoaleatórios criptograficamente seguro (`secrets.token_bytes(32)`) para cada segredo.
- **Cifra:** **AES-256-GCM** (Galois/Counter Mode), garantindo simultaneamente confidencialidade e integridade criptográfica.
- **AAD (Additional Authenticated Data):** O UUID estável do usuário individual (`user_id.bytes`) é obrigatoriamente injetado como dado adicional autenticado no bloco GCM. Qualquer tentativa de descriptografar a chave sob a identidade de outro usuário resulta em falha imediata de autenticação criptográfica (`InvalidTag`).

### 3.2 Estrutura do Payload Cifrado
```json
{
  "provider": "TWELVE_DATA",
  "keyVersion": 1,
  "ciphertextB64": "...",
  "nonceIvB64": "...",
  "dekEncryptedB64": "...",
  "maskedHint": "••••••••••••••••••••••••••••••••••••2345",
  "createdAt": "2026-10-19T22:30:00Z"
}
```

### 3.3 Auditoria, Backup e Isolamento
- **Versionamento e Rotação:** Cada registro suporta incremento de versão de chave (`key_version`). No momento da rotação, uma nova DEK é gerada e cifrada sob a KEK ativa.
- **Backups e Exclusão Segura:** Ao excluir a conta individual (`DELETE /api/v1/agro/auth/account`), todos os registros cifrados vinculados ao usuário são destruídos (`crypto-shredding`). Sem a chave e o AAD do usuário, os blocos residuais tornam-se indecifráveis.
- **Restrição da Fase C2:** Conforme exigido nas diretrizes, **nenhuma chave real de fornecedor (Twelve Data, Polygon, IBKR) foi cadastrada ou persistida**.

---

## 4. Frontend no PWA DeepFarms Agro (`apps/agro`)

### 4.1 Preservação do Acesso Público e Anônimo
- Todas as funcionalidades gratuitas (`/`, `/mercado` com PTAX, BCB e IBGE/SIDRA, `/clima` e `/calculadoras`) continuam 100% acessíveis e operacionais sem exigir autenticação.
- O banner institucional na nova área `/conta` destaca explicitamente que o cadastro é facultativo e destinado exclusivamente a recursos individuais futuros (BYOK e customizações).

### 4.2 Nova Página de Conta Individual (`/conta`)
Implementada em conformidade rigorosa com a regra `03-frontend-web.md` e o Design System:
- **Server Component (RSC):** `apps/agro/src/app/conta/page.tsx` provê metadados estáticos, título semântico e SEO.
- **Client Component:** `apps/agro/src/components/auth/painel-conta.tsx` gerencia estados reativos, formulários com feedback imediato e cards informativos.
- **Aba Anônima:**
  - Alternância fluida entre "Entrar", "Cadastrar" e "Esqueceu a senha".
  - Feedback visual e mensagens informativas com badges e ícones de segurança.
- **Aba Autenticada:**
  - Apresentação do perfil individual com identificador global estável (UUIDv4), data de adesão e status de e-mail.
  - Indicador de segurança confirmando: *Sessão HttpOnly Segregada* e *Zero Tenants Comerciais*.
  - Seção técnica explicando o contrato do futuro cofre BYOK com envelope encryption.
  - Botão de logout seguro com limpeza sincronizada de cookies.
- **Navegação Integrada:**
  - **Desktop:** Botão "Minha Conta" integrado ao `Header` ao lado do seletor de tema.
  - **Mobile:** Item "Conta" adicionado ao `BottomNav` para acesso tátil direto em smartphones.

---

## 5. Bateria de Testes e Evidências de Homologação

### 5.1 Testes Unitários e de Integração Backend (Pytest)
Executados no ambiente Python 3.10 com virtualenv oficial:
```bash
.venv/bin/pytest tests/unit/test_ptax_publico.py \
                 tests/unit/test_macro_publico.py \
                 tests/unit/test_ibge_sidra_publico.py \
                 tests/unit/test_agro_identity.py -v
```
**Resultado:** **44 testes executados, 44 aprovados (100% de sucesso)**.

Detalhamento da suíte `test_agro_identity.py`:
1. `test_01_cadastro_login_e_perfil`: validação de registro, geração de cookie HttpOnly e consulta ao `/me`.
2. `test_02_protecao_forca_bruta_e_lockout`: simulação de 5 falhas consecutivas e bloqueio com HTTP 429.
3. `test_03_logout_e_revogacao_sessao`: encerramento de sessão, deleção de cookie e invalidação imediata no banco.
4. `test_04_recuperacao_senha`: emissão de token de recuperação e troca segura de senha.
5. `test_05_rejeicao_de_token_individual_no_saas_comercial`: comprovação de rejeição com **HTTP 403 Forbidden** nas rotas comerciais `/api/v1/auth/me`, `/api/v1/auth/my-tenants` e `/api/v1/backoffice/tenants`.
6. `test_06_ausencia_de_tenants_comerciais`: auditoria direta na base PostgreSQL comercial comprovando que nenhum registro foi criado em `tenants` ou `tenant_usuarios`.
7. `test_07_envelope_encryption_vault_contracts`: validação da cifra AES-256-GCM com AAD e rejeição de descriptografia cruzada.

### 5.2 Testes Unitários de Frontend (Vitest)
Executados via `pnpm test` no workspace `apps/agro`:
```bash
pnpm test
```
**Resultado:** **88 testes executados, 88 aprovados (100% de sucesso)** em 6 arquivos de teste (`agro-auth.test.ts`, `macro.test.ts`, `ibge.test.ts`, `ptax.test.ts`, `catalogo-mercado.test.ts`, `calculadoras.test.ts`).

### 5.3 Testes E2E no Navegador Real (Playwright Desktop e Mobile)
Executados via `pnpm exec playwright test tests/e2e/agro-identity.spec.ts`:
```bash
Running 5 tests using 1 worker
  5 passed (4.5s)
```
1. Usuário anônimo acessa `/`, `/mercado` e `/calculadoras` sem barreiras.
2. Navegação para `/conta` via Header no viewport desktop (1280x800).
3. Navegação para `/conta` via BottomNav no viewport mobile (375x667).
4. Alternância entre formulários de Login, Cadastro e Recuperação de Senha.
5. Verificação da declaração HttpOnly e garantia de **zero tokens sensíveis em localStorage**.

### 5.4 Build de Produção e Tipagem Estrita
- `pnpm typecheck`: verificação de tipos TypeScript aprovada com zero advertências.
- `pnpm build`: compilação estática do Next.js 16.1.6 com sucesso (rotas prerenderizadas, incluindo `/conta`).

---

## 6. Limitações e Restrições Homologadas

1. **Ausência de Conectores Reais BYOK:** Conforme a restrição contratual da fase C2, não foram implementados os conectores para Twelve Data, Polygon ou Interactive Brokers.
2. **Ausência de Armazenamento de Credenciais Reais:** Apenas a especificação criptográfica e os contratos de envelope encryption foram disponibilizados; nenhuma chave real de usuário foi solicitada ou persistida.
3. **Ambiente Local SQLite:** A identidade individual está configurada por padrão em SQLite assíncrono (`agro_identity.db`). Em ambiente de produção de larga escala, o repositório segregado poderá apontar para uma instância PostgreSQL dedicada, preservando a segregação física e lógica sem compartilhar conexões com o SaaS comercial.

---

## 7. Veredicto Conclusivo

A fase **DEEPFARMS-AGRO-FREE-01E2F-C2** atinge **100% de conformidade** com todas as diretrizes funcionais, de segurança e arquiteturais estabelecidas:
- Repositório de identidades 100% segregado do banco comercial.
- Sessões protegidas por cookies HttpOnly SameSite=Lax.
- Zero tenants e zero consumo do pool de conexões do SaaS.
- Tokens individuais barrados com 403 Forbidden em recursos comerciais.
- Funcionalidades públicas mantidas 100% anônimas e livres de atrito.
- Baterias de testes de backend, frontend e Playwright E2E completamente verdes.

**A fundação de identidade individual está homologada e pronta para as etapas de integração BYOK.**
