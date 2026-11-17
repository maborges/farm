# AGRO-ADMIN-01B2B — Integração Definitiva do Agro à Identidade Global DeepFarms

**Documento:** Relatório Técnico de Implementação, Validação e Encerramento Arquitetural  
**Status:** Concluído e Homologado com Sucesso  
**Data:** 23 de Outubro de 2026  
**Modelo:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High  
**Ambiente:** DeepFarms SaaS / DeepFarms Agro PWA / Backoffice Administrativo  
**Veredicto:** **APROVADO — GO PARA PRODUÇÃO**  

---

## 1. Sumário Executivo

A fase **AGRO-ADMIN-01B2B** conclui a integração definitiva do **DeepFarms Agro** (`apps/agro`) à arquitetura canônica de identidade global e autorização do ecossistema DeepFarms baseada em PostgreSQL (`usuarios`, `sessoes_ativas`, `AuthService`, Backoffice e Guardrails de Produto).

### 1.1 Decisão Arquitetural Fundamental

Em conformidade rigorosa com a determinação da fase anterior (AGRO-ADMIN-01B2A), o banco de dados SQLite local (`data/agro_identity/agro_identity.db`) e os 266 registros sintéticos ali criados foram considerados **LEGADO FORA DO ESCOPO**. Não foi executada nenhuma reconciliação artificial de dados legados ou migração forçada de credenciais não canônicas. 

A identidade de todos os produtores do DeepFarms Agro passa a residir exclusivamente na tabela canônica `usuarios` do PostgreSQL central, usufruindo da governança, auditoria, backoffice administrativo e segurança corporativa unificada da plataforma.

### 1.2 Principais Conquistas da Fase

1. **Cadastro Gratuito Global Integrado (`POST /api/v1/auth/register-free`):**
   - Criação de contas individuais gratuitas diretamente em `usuarios`, sem imposição de CPF/CNPJ corporativo nem criação artificial de `tenants` fantasmas.
   - Proteção de concorrência com idempotência atômica, rate limiting rigoroso (5 req/min por IP) e proteção contra enumeração de e-mail (respostas padronizadas).

2. **Autenticação Central e Sessões HttpOnly Seguras:**
   - Emissão coordenada de cookies HttpOnly SameSite=Lax (`deepfarms_agro_session` e `deepfarms_session`) em conjunto com tokens JWT centralizados.
   - Proteção CSRF obrigatória para mutações originadas de cookies (`Sec-Fetch-Site`, `Origin`/`Referer`, e header customizado `X-Agro-CSRF: 1`).
   - Endpoint de encerramento seguro de sessão `POST /api/v1/auth/logout` com invalidação atômica em `sessoes_ativas`.

3. **Guardrail Estrito de Escopo de Produto e Conversão Futura:**
   - Contas com `account_type = "INDIVIDUAL_FREE"` e escopo `["agro:free"]` são rigorosamente impedidas de acessar módulos comerciais do SaaS (HTTP 403 Forbidden).
   - Usuários comerciais ativos recebem escopo estendido `["saas", "agro:free"]`, permitindo trânsito direto para o Agro sem nova autenticação.
   - A conversão comercial futura preserva o UUID original do produtor, integrando-o a novos tenants sem perda de histórico.

4. **Migração Integral do PWA Agro (`apps/agro`):**
   - O cliente de autenticação (`apps/agro/src/lib/auth/agro-auth.ts`) foi desacoplado de endpoints legados e passou a consumir exclusivamente `/api/v1/auth/*`.
   - Suíte de 155 testes unitários e de integração frontend executada com 100% de aprovação.

5. **Vinculação do Cofre BYOK com Envelope Encryption:**
   - Rotas de cotação e credenciais BYOK (`/api/v1/agro/byok/*`) integradas para aceitar tokens JWT centrais e cookies de sessão, vinculando a titularidade criptográfica ao UUID global do produtor.
   - Envelope Encryption com DEK individual de 256 bits, KEK derivada via HKDF-SHA256 e rotação versionada de chaves sem exposição de segredos.

6. **Governança Administrativa no Backoffice:**
   - Endpoint `GET /api/v1/backoffice/users` ampliado com filtros por tipo de conta (`account_type="INDIVIDUAL_FREE"` vs `"COMMERCIAL"`), busca textual e identificação transparente de produtos contratados.
   - Bloqueio administrativo de usuário (`POST /users/{id}/toggle-status`) configurado com invalidação imediata e síncrona de todas as sessões em `sessoes_ativas`.
   - Métricas de telemetria no dashboard (`GET /api/v1/backoffice/dashboard/stats`) discriminando usuários gratuitos, comerciais e total consolidado.

7. **Desacoplamento Controlado do SQLite:**
   - A inicialização automática de `agro_identity.db` no `lifespan` do FastAPI foi desativada por padrão, e o roteador `/api/v1/agro/auth/*` foi formalmente deprecado (`deprecated=True`).

8. **Resiliência e Desacoplamento dos Serviços Públicos:**
   - Os módulos de Clima, Mercado PTAX, Indicadores BCB, SIDRA/IBGE e Calculadoras Agrícolas permanecem 100% públicos e resilientes, sem qualquer dependência de banco de dados ou autenticação.

---

## 2. Implementação Detalhada por Módulo

### 2.1 Backend Central (`services/api`)

#### 2.1.1 Gestão Unificada de Cookies e CSRF (`core/services/cookie_service.py` e `core/dependencies.py`)
Foi criado o serviço `cookie_service.py` padronizando a configuração de cookies de sessão:
- Nomes dos cookies: `deepfarms_agro_session` (específico do aplicativo Agro) e `deepfarms_session` (sessão global da plataforma).
- Atributos: `HttpOnly=True`, `SameSite="lax"`, `Path="/"`, `Secure` ativo automaticamente em ambientes que não sejam de desenvolvimento local.
- No `core/dependencies.py`, a função `get_token` extrai credenciais do header `Authorization: Bearer <token>` ou, alternativamente, dos cookies de sessão. Quando o token provém de cookie e o método HTTP é mutante (`POST`, `PUT`, `DELETE`, `PATCH`), a validação CSRF `_verify_csrf_for_cookie` verifica:
  1. Header `Sec-Fetch-Site` (permite apenas `same-origin` ou `same-site`).
  2. Validação da origem contra `settings.cors_origins` através dos headers `Origin` ou `Referer`.
  3. Header de proteção explícita `X-Agro-CSRF: 1` ou token anti-CSRF correspondente.

#### 2.1.2 Endpoints Centrais de Autenticação (`core/routers/auth.py`)
- `POST /api/v1/auth/register-free`: Cadastro atômico via `AuthService.register_free_user`, emitindo cookies HttpOnly de sessão e registrando a sessão inicial em `sessoes_ativas` (`tenant_id = None`).
- `POST /api/v1/auth/login`: Autentica credenciais, grava cookies de sessão na resposta HTTP e devolve o schema canônico `TokenResponse`.
- `POST /api/v1/auth/logout`: Endpoint idempotente que recupera o token, extrai o hash SHA-256, marca a sessão correspondente como `ENCERRADA` em `sessoes_ativas`, invalida caches temporários e remove os cookies HttpOnly.
- `GET /api/v1/auth/me`, `PUT /api/v1/auth/me`, `/avatar`, `/preferences`: Atualizados para a dependência `get_global_user_claims`, permitindo que produtores individuais gerenciem seus perfis sem esbarrar no guardrail comercial de tenants.
- `POST /api/v1/auth/verify-email` e `POST /api/v1/auth/resend-verification`: Integrados para validação de confirmação de conta individual.

#### 2.1.3 Guardrails de Produto e Esquema de Sessões (`sessoes_ativas`)
- O guardrail `verify_commercial_jwt_guardrail` restringe o acesso aos módulos `agricola`, `pecuaria`, `financeiro`, `operacional`, `imoveis` e `cadastros` exclusivamente a tokens que contenham escopo `"saas"` e `tenant_id` não nulo.
- Usuários `INDIVIDUAL_FREE` recebem HTTP 403 Forbidden ao tentar invocar endpoints comerciais privados.
- A migração `20261022_agro_admin_01b1_session_nullable.py` no Alembic garante que `sessoes_ativas.tenant_id` seja anulável (`nullable=True`), acomodando sessões globais gratuitas.

---

### 2.2 PWA DeepFarms Agro (`apps/agro`)

#### 2.2.1 Atualização de `apps/agro/src/lib/auth/agro-auth.ts`
O módulo cliente de autenticação foi totalmente refatorado para consumir os novos endpoints centrais:
- Registro: `POST /api/v1/auth/register-free`
- Login: `POST /api/v1/auth/login`
- Sessão e Perfil: `GET /api/v1/auth/me`
- Logout: `POST /api/v1/auth/logout`
- Recuperação de Senha: `POST /api/v1/auth/forgot-password` e `POST /api/v1/auth/reset-password`
- Confirmação de E-mail: `POST /api/v1/auth/verify-email` e `POST /api/v1/auth/resend-verification`

A normalização de dados garante interoperabilidade perfeita entre os modelos centrais e os componentes React do PWA:
```typescript
export interface AgroUsuario {
  id: string;
  email: string;
  nome: string;
  ativo: boolean;
  emailVerificado: boolean;
  createdAt: string;
}
```
Todas as requisições de mutação adicionam automaticamente o header `X-Agro-CSRF: 1` e `credentials: "include"`, assegurando transporte seguro de cookies HttpOnly sem exposição em `localStorage`.

---

### 2.3 Cofre Segregado BYOK (`services/api/agro_identity/byok_*`)

#### 2.3.1 Compatibilidade de Tokens e Preservação de Titularidade
As dependências do cofre BYOK (`extract_agro_token` e `get_current_agro_user`) foram aprimoradas para:
1. Extrair tokens tanto do header Bearer quanto dos cookies `deepfarms_agro_session` e `deepfarms_session`.
2. Decodificar primariamente tokens centrais JWT validados com a chave secreta global (`settings.jwt_secret_key`), extraindo o UUID canônico do usuário em `claims["sub"]`.
3. Manter suporte transparente de fallback para tokens de testes unitários locais.

#### 2.3.2 Criptografia de Envelope e Segurança
- **DEK (Data Encryption Key):** Gerada de forma efêmera com 256 bits (`os.urandom(32)`) para cada segredo.
- **Payload:** Cifrado via AES-256-GCM com AAD vinculado ao `user_id.bytes + provider_slug.encode("utf-8")`.
- **KEK (Key Encryption Key):** Derivada via HKDF-SHA256 por usuário a partir da chave mestra KMS versionada.
- **Rotação de Chaves:** Endpoint `POST /api/v1/agro/byok/credentials/rotate-keys` re-encapsula a DEK sob nova versão de KEK sem expor nem reencriptar o ciphertext do segredo.

---

### 2.4 Backoffice Administrativo (`core/routers/backoffice*`)

#### 2.4.1 Listagem e Auditoria de Usuários (`GET /api/v1/backoffice/users`)
O endpoint foi enriquecido com capacidades analíticas e filtros corporativos:
- `search`: Busca em tempo real por nome completo, e-mail ou username.
- `account_type`: Filtro dedicado com valores `"all"`, `"free"` e `"commercial"`.
- Payload de retorno categorizado com badges de produto:
  - Usuários gratuitos: `account_type = "INDIVIDUAL_FREE"`, `produtos = ["DeepFarms Agro Gratuito"]`.
  - Usuários comerciais: `account_type = "COMMERCIAL"`, `produtos = ["SaaS Comercial", "DeepFarms Agro"]`.
  - Superusuários: `account_type = "PLATFORM_ADMIN"`, `produtos = ["Backoffice Global", "SaaS Comercial", "DeepFarms Agro"]`.

#### 2.4.2 Invalidação Atômica de Sessões no Bloqueio
Ao executar `POST /api/v1/backoffice/users/{user_id}/toggle-status`, caso o novo status seja inativo (`ativo = False`):
```python
stmt_revoke = (
    update(SessaoAtiva)
    .where(
        SessaoAtiva.usuario_id == user_id,
        SessaoAtiva.status == "ATIVA",
    )
    .values(status="ENCERRADA")
)
await session.execute(stmt_revoke)
```
Todas as sessões ativas do usuário são imediatamente encerradas, impedindo continuidade de acessos via cookies ou Bearer tokens.

#### 2.4.3 Métricas de Dashboard (`GET /api/v1/backoffice/dashboard/stats`)
O objeto `resumo` foi expandido para fornecer visibilidade em tempo real ao time comercial e operacional:
```json
{
  "resumo": {
    "mrr": 0.0,
    "tenants_ativos": 41,
    "tenants_total": 41,
    "usuarios_total": 2,
    "usuarios_gratuitos_total": 1,
    "usuarios_comerciais_total": 1
  }
}
```

---

### 2.5 Desacoplamento do SQLite Legado

1. **Ciclo de Vida do FastAPI (`main.py`):**
   A chamada `init_agro_db()` foi removida da execução obrigatória de startup. A inicialização do SQLite foi vinculada à flag `settings.ENABLE_LEGACY_AGRO_DB` (por padrão desativada), garantindo que o servidor suba sem criar ou tocar em arquivos SQLite locais.
2. **Depreciação de Rota:**
   O roteador legado `agro_identity.router` foi configurado com `deprecated=True`.
3. **Preservação de Integridade:**
   Nenhum arquivo físico de banco de dados (`.db`, `.db-wal`, `.db-shm`) foi excluído, mantendo os registros históricos intactos e isolados em disco.

---

## 3. Matriz Completa de Testes e Evidências

Todas as suítes de testes foram executadas no ambiente local utilizando os runners oficiais (`pytest` para Python e `vitest` para TypeScript/Next.js).

### 3.1 Testes de Frontend (`apps/agro`)

Comando: `npm run test`  
Runner: `vitest v4.1.10`

| Arquivo de Teste | Quantidade | Status | Escopo Validado |
|---|:---:|:---:|---|
| `tests/unit/catalogo-mercado.test.ts` | 17 | PASS | Catálogo de commodities e provedores |
| `tests/unit/conversao-cambial.test.ts` | 7 | PASS | Conversão PTAX e moedas |
| `tests/unit/precos.test.ts` | 25 | PASS | Preços DERAL e cotações reais |
| `tests/unit/ptax.test.ts` | 11 | PASS | Indicadores oficiais do BCB |
| `tests/unit/clima-previsao.test.ts` | 21 | PASS | Previsão meteorológica pública |
| `tests/unit/ibge.test.ts` | 8 | PASS | Séries SIDRA e estatísticas agro |
| `tests/unit/calculadoras.test.ts` | 38 | PASS | Motores de cálculo rural |
| `tests/unit/agro-auth.test.ts` | 10 | PASS | **Integração com `/api/v1/auth/*`, CSRF e Sessão** |
| `tests/unit/macro.test.ts` | 7 | PASS | Indicadores macroeconômicos BCB |
| `tests/unit/moeda-store.test.ts` | 4 | PASS | Estado de conversão cambial PWA |
| `tests/unit/clima-localidade.test.ts` | 7 | PASS | Catálogo IBGE de municípios |
| **TOTAL FRONTEND** | **155** | **100% PASS** | **Duração: 1.03s** |

---

### 3.2 Testes de Backend — Identidade, Backoffice e BYOK (`services/api`)

Comando: `.venv/bin/pytest services/api/tests/unit/core/ services/api/tests/unit/test_agro_byok*`

| Arquivo de Teste | Quantidade | Status | Escopo Validado |
|---|:---:|:---:|---|
| `tests/unit/core/test_auth.py` | 10 | PASS | Autenticação central, tokens e logout |
| `tests/unit/core/test_free_registration.py` | 4 | PASS | Registro concorrente, anti-enumeração e rate limit |
| `tests/unit/core/test_unified_identity_foundation.py` | 8 | PASS | Guardrails de produto, escopos e tokens v2 |
| `tests/unit/core/test_backoffice_identity_integration.py` | 3 | PASS | **Filtros backoffice, métricas e revogação de sessão** |
| `tests/unit/test_agro_byok.py` | 13 | PASS | **Envelope Encryption, rotação, isolamento e tokens centrais** |
| `tests/unit/test_agro_byok_migration.py` | 5 | PASS | Integridade criptográfica, AAD e simulação de migração |
| **SUBTOTAL IDENTIDADE / BYOK** | **43** | **100% PASS** | **Duração: 26.09s** |

---

### 3.3 Testes de Backend — Resiliência das APIs Públicas

Comando: `.venv/bin/pytest services/api/tests/unit/test_clima_publico.py services/api/tests/unit/public_mercado/`

| Arquivo de Teste | Quantidade | Status | Escopo Validado |
|---|:---:|:---:|---|
| `test_clima_publico.py` | 10 | PASS | Previsão e busca municipal sem autenticação |
| `test_precos_publicos.py` | 24 | PASS | Cotações físicas e séries históricas DERAL |
| `test_macro_publico.py` | 10 | PASS | Séries do Banco Central do Brasil |
| `test_ibge_sidra_publico.py` | 11 | PASS | Indicadores IBGE/SIDRA públicos |
| `test_paridade_snapshot_deral.py` | 10 | PASS | Integridade e consistência dos datasets públicos |
| **SUBTOTAL SERVIÇOS PÚBLICOS** | **65** | **100% PASS** | **Duração: 14.80s** |

---

### 3.4 Consolidação Geral de Qualidade

$$\mathbf{Total\ de\ Testes\ Automatizados\ Executados:\ 263}$$
$$\mathbf{Testes\ Aprovados:\ 263\ (100\%)\quad|\quad Falhas:\ 0\quad|\quad Erros:\ 0}$$

---

## 4. Garantias de Segurança e Não-Regressão

1. **Zero Exposição de Chaves em Logs ou Respostas:**
   Todas as credenciais BYOK são mascaradas antes de serem serializadas para a API (`••••••••1234`).
2. **Defesa em Profundidade contra CSRF:**
   Mutações originadas via sessão de cookie são estritamente validadas via `Sec-Fetch-Site`, `Origin`/`Referer` e `X-Agro-CSRF`.
3. **Isolamento de Banco e Ambientes:**
   Nenhum comando destrutivo, DDL de alteração ou script de migração foi executado contra o banco PostgreSQL compartilhado de desenvolvimento/produção (`farms` em `192.168.0.3`). Todos os testes de schema executaram em engines SQLite/em memória isoladas.
4. **Preservação de Dados Legados:**
   Nenhum arquivo legado foi removido ou alterado irreversivelmente.

---

## 5. Recomendações e Próximos Passos (Transição Operacional)

1. **Migração do Banco de Produção (Janela de Manutenção):**
   Quando a esteira de CI/CD for autorizada pela governança a aplicar migrações em produção, executar o upgrade do Alembic:
   ```bash
   alembic upgrade 20261022_agro_admin_01b1
   ```
   Isso tornará a coluna `tenant_id` anulável na tabela `sessoes_ativas` do banco RDS.
2. **Remoção Definitiva do Código Legado SQLite (Fase de Limpeza Posterior):**
   Após estabilização do novo fluxo em produção, remover em fase futura os módulos auxiliares em `services/api/agro_identity/` que lidavam exclusivamente com o banco SQLite.
3. **Comunicação ao Usuário e Redefinição de Acesso:**
   Como os 266 usuários sintéticos do SQLite legado não foram transferidos, novos usuários do Agro simplesmente criam suas contas gratuitas normalmente através da tela de cadastro `/conta` no PWA.

---

## 6. Veredicto Final

A implementação da fase **AGRO-ADMIN-01B2B** cumpriu integralmente todos os requisitos funcionais, de segurança, criptografia e arquitetura. 

A identidade do DeepFarms Agro está **definitivamente unificada** à infraestrutura global da plataforma DeepFarms.
