# AGRO-ADMIN-01B2D — Validação PostgreSQL e Prontidão de Produção

**Data:** 23 de outubro de 2026  
**Escopo:** Fechamento das pendências AGRO-ADMIN-01B2C e homologação PostgreSQL via CI na AGRO-ADMIN-01B2D  
**Veredicto:** **NO-GO para produção (Aguardando execução remota do workflow GitHub Actions com PostgreSQL 16)**

---

## 1. Resumo Executivo

A integração definitiva do DeepFarms Agro à Identidade Global foi concluída no código-fonte, acompanhada da infraestrutura completa de homologação automatizada em PostgreSQL 16:
- Segregação de produtos e escopos (`INDIVIDUAL_FREE`, `COMMERCIAL`, `PLATFORM_ADMIN`).
- Guardrails mandatórios bloqueando acessos comerciais por contas gratuitas.
- Autenticação e persistência do cofre BYOK unificadas na sessão global e no banco central.
- Desacoplamento da inicialização e rotas do SQLite legado (`enable_legacy_agro_db=False` por padrão).
- Proteção estrita de downgrade Alembic (impedindo remoção de credenciais ou restauração de `tenant_id NOT NULL` com sessões órfãs).
- **Workflow de CI preparado** (`.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`) com contêiner de serviço `postgres:16-alpine`.
- **Script de homologação automatizada** (`services/api/scripts/homologar_postgresql_ci.py`) para validar upgrade Alembic, constraints, downgrade protegido e rollback.
- **Fixtures de teste adaptadas**: bloqueio estrito de fallback para SQLite quando em CI (`CI_POSTGRESQL=true` gera erro fatal caso PostgreSQL isolado esteja inacessível).

Bateria local consolidada: **28 testes aprovados (100%)**.

Em cumprimento irrestrito às restrições de segurança do projeto (*"Não utilizar Docker local"*, *"Não acessar o banco compartilhado ou RDS"*, *"Não executar commit ou push sem autorização"*), o workflow foi preparado e testado estaticamente no workspace, restando a autorização do operador para publicação do branch e execução remota na esteira do GitHub Actions.

---

## 2. Diagnóstico de Infraestrutura e Isolamento (Tarefa 1)

| Item Verificado | Status | Detalhes Técnicos |
| :--- | :--- | :--- |
| **Docker Local** | **Não Utilizado** | Diretriz do operador mantida: Docker local desabilitado para execução. |
| **PostgreSQL Local** | Client-only | Apenas utilitários clientes (`psql`); sem daemon servidor no host. |
| **Banco Compartilhado (`farms`)** | **Intocado / Preservado** | Instância `192.168.0.3:5432/farms` mantida intacta; zero DDLs ou testes destrutivos. |
| **RDS / Produção** | **Intocado / Preservado** | Nenhuma conexão aberta ou alterada. |
| **Estratégia Escolhida** | **GitHub Actions CI** | Serviço efêmero `postgres:16-alpine` provisionado em runner isolado da nuvem. |

---

## 3. Preparação do Workflow de Homologação CI (Atividades 2, 3 e 4)

### 3.1 Arquivo do Workflow
Criado em [`.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`](file:///opt/lampp/htdocs/farm/.github/workflows/agro-admin-01b2d-postgres-homologacao.yml):
- **Gatilhos:** `workflow_dispatch` (manual) e `pull_request` para `main`.
- **Serviço de Banco:**
  ```yaml
  services:
    postgres:
      image: postgres:16-alpine
      env:
        POSTGRES_USER: deepfarms_test
        POSTGRES_PASSWORD: test_secure_password_ci_2026
        POSTGRES_DB: farms_test
      ports:
        - 5432:5432
      options: >-
        --health-cmd pg_isready
        --health-interval 5s
        --health-timeout 5s
        --health-retries 5
  ```

### 3.2 Mapeamento de Variáveis Efetivas
Inspecionadas e configuradas no workflow:
- `APP_ENV`: `test`
- `CI_POSTGRESQL`: `"true"` (ativa bloqueio fatal de fallback SQLite)
- `DATABASE_URL`: `"postgresql+asyncpg://deepfarms_test:test_secure_password_ci_2026@localhost:5432/farms_test"`
- `TEST_DATABASE_URL`: `"postgresql+asyncpg://deepfarms_test:test_secure_password_ci_2026@localhost:5432/farms_test"`
- `JWT_SECRET_KEY`: Chave efêmera de teste (>= 32 chars)
- `JWT_ALGORITHM`: `HS256`
- `JWT_ISSUER`: `deepfarms:identity`
- `JWT_AUDIENCE`: `deepfarms:platform`
- `ENABLE_LEGACY_AGRO_DB`: `"false"`
- `AGRO_VAULT_MASTER_KEY`: Chave AES-256 de 32 bytes para o KMS do cofre BYOK
- `FRONTEND_URL`: `"http://localhost:3000"`

### 3.3 Guardrails Anti-Vazamento
O workflow valida programaticamente que o host é estritamente `localhost` ou `127.0.0.1` e rejeita qualquer substring contendo `192.168.` ou `rds.amazonaws.com`.

---

## 4. Script de Homologação Autônoma (Atividades 5 e 9)

Implementado em [`services/api/scripts/homologar_postgresql_ci.py`](file:///opt/lampp/htdocs/farm/services/api/scripts/homologar_postgresql_ci.py):
1. **Validação de Isolamento:** Rejeita execução se o host não for local (`localhost`/`127.0.0.1`/`postgres`).
2. **Upgrade Head:** Executa `alembic upgrade head` até `20261022_agro_admin_01b1_session_nullable`.
3. **Verificação de Constraints:**
   - Schema `farms` criado com sucesso.
   - `farms.sessoes_ativas.tenant_id` verificado como `is_nullable = 'YES'`.
   - `farms.usuario_byok_credenciais` verificado com colunas e integridade referencial.
4. **Verificação de Downgrade e Rollback:**
   - Inserção de credencial BYOK ativa -> tentativa de `alembic downgrade -1` DEVE falhar com `RuntimeError`.
   - Remoção de credencial e inserção de sessão com `tenant_id IS NULL` -> tentativa de downgrade DEVE falhar com `RuntimeError`.
   - Limpeza de dados órfãos -> `alembic downgrade -1` executa e restaura `tenant_id` para `NOT NULL` e remove a tabela BYOK.
   - Re-execução de `alembic upgrade head` para restaurar o estado final atualizado.

---

## 5. Adaptação das Fixtures e Eliminação de Fallback (Atividade 6)

As fixtures de teste foram atualizadas:
- [test_homologacao_01b2c_e2e_fluxos.py](file:///opt/lampp/htdocs/farm/services/api/tests/unit/core/test_homologacao_01b2c_e2e_fluxos.py)
- [test_agro_byok.py](file:///opt/lampp/htdocs/farm/services/api/tests/unit/test_agro_byok.py)
- [test_free_registration.py](file:///opt/lampp/htdocs/farm/services/api/tests/unit/core/test_free_registration.py)

**Comportamento em CI:**
Quando `CI_POSTGRESQL=true` ou `GITHUB_ACTIONS=true` está ativo, se `TEST_DATABASE_URL` não for fornecido ou não apontar para PostgreSQL, o teste lança `RuntimeError` imediatamente:
```text
RuntimeError: CI detectada (CI_POSTGRESQL ou GITHUB_ACTIONS ativo), mas nenhum PostgreSQL foi fornecido via TEST_DATABASE_URL/DATABASE_URL. Fallback para SQLite é proibido.
```
Comprovado localmente em 23/10/2026.

---

## 6. Evidência Local dos Testes (Atividades 7 e 8)

Comando executado:
```bash
services/api/.venv/bin/pytest \
  services/api/tests/unit/core/test_homologacao_01b2c_e2e_fluxos.py \
  services/api/tests/unit/test_agro_byok.py \
  services/api/tests/unit/test_agro_byok_migration.py \
  services/api/tests/unit/test_agro_admin_01b2d_safety.py \
  services/api/tests/unit/core/test_free_registration.py
```

Resultado:
```text
========================== test session starts ==========================
platform linux -- Python 3.10.12, pytest-9.0.2, pluggy-1.6.0
rootdir: /opt/lampp/htdocs/farm/services/api
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1, cov-7.1.0
collected 28 items

services/api/tests/unit/core/test_homologacao_01b2c_e2e_fluxos.py . [  3%]
services/api/tests/unit/test_agro_byok.py .............           [ 50%]
services/api/tests/unit/test_agro_byok_migration.py .....         [ 67%]
services/api/tests/unit/test_agro_admin_01b2d_safety.py .....     [ 85%]
services/api/tests/unit/core/test_free_registration.py ....       [100%]

=================== 28 passed, 35 warnings in 31.16s ====================
```

---

## 7. Ação Necessária do Operador para Liberação

Em cumprimento à restrição *"Não executar commit ou push sem autorização"*, os arquivos estão prontos no workspace:
1. `.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`
2. `services/api/scripts/homologar_postgresql_ci.py`
3. Fixtures em `services/api/tests/unit/`

Para acionar a execução na esteira do GitHub Actions com o PostgreSQL 16 efêmero:
```bash
git add .github/workflows/agro-admin-01b2d-postgres-homologacao.yml \
        services/api/scripts/homologar_postgresql_ci.py \
        services/api/tests/unit/ \
        docs/implementation/reports/AGRO-ADMIN-01B2D-PRONTIDAO-PRODUCAO.md
git commit -m "ci(agro-identity): add postgresql 16 homologation workflow and scripts"
git push origin <branch-name>
```

Após o disparo da action, o workflow:
1. Sobe contêiner `postgres:16-alpine`.
2. Executa `homologar_postgresql_ci.py` (Alembic upgrade head, constraints, downgrade guardrail, re-upgrade).
3. Executa a suíte de 28 testes contra o PostgreSQL 16 real.

---

## 8. Veredicto

**NO-GO para produção nesta fase.**

Todos os artefatos de código, testes, scripts de validação e pipeline de CI foram implementados e aprovados estaticamente. Conforme a regra de ouro do épico (*"Somente declarar GO para a homologação quando houver evidência real de execução bem-sucedida no PostgreSQL 16 isolado"*), o veredicto final será convertido para **GO** imediatamente após o encerramento com sucesso do workflow remoto no GitHub Actions.
