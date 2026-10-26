# DEEPFARMS-AGRO-FREE-01E2F-C2B — Hardening Final da Identidade

**Data:** 20/10/2026  
**Status:** CONCLUÍDO COM SUCESSO  
**Veredicto Arquitetural:** **GO** (com ressalva de escala horizontal multi-pod para fase C3/C4)  
**Módulos Auditados:** `services/api/agro_identity/`, `services/api/core/config.py`, `apps/agro/`  
**Escopo:** Hardening operacional e de segurança das pendências apontadas na homologação C2A: eliminação total de códigos em respostas públicas, segurança do armazenamento SQLite e permissões POSIX, rotina de backup online e restauração a quente com integridade, e proteção contra CSRF inter-subdomínios na topologia oficial do DeepFarms Agro.

---

## 1. Sumário Executivo e Veredicto

A fase **DEEPFARMS-AGRO-FREE-01E2F-C2B** aplicou todas as correções de endurecimento de segurança (*hardening*) identificadas na auditoria operacional C2A, garantindo que o subsistema de identidade individual segregada do DeepFarms Agro opere com padrões de segurança bancária e isolamento irrestrito.

### Veredicto: **GO**

- **Homologação:** Todas as pendências operacionais, de vazamento de credenciais em respostas e de concorrência/permissões de arquivo foram sanadas e atestadas com 100% de sucesso em testes automatizados.
- **Ressalva de Escala Horizontal:** Conforme firmado na C2A, a arquitetura com SQLite em modo WAL e permissões `0700`/`0600` está plenamente aprovada para implantações *single-node* (VPS, instância dedicada ou contêiner único com volume persistente). Para arquiteturas futuras em cluster multi-pod (Kubernetes/ECS), a migração para PostgreSQL segregado com connection pool próprio será executada nas fases C3/C4.

---

## 2. Hardening e Correções Realizadas

### 2.1 Código de Verificação e Tokens: Sigilo Estrito
- **Diagnóstico:** Na fase C2A, para facilitar testes iniciais, os campos `codigoVerificacao` e `tokenRecuperacao` eram retornados temporariamente no corpo JSON de `POST /register` e `POST /forgot-password`.
- **Endurecimento Implementado:**
  1. `services/api/agro_identity/schemas.py`: Removido `codigoVerificacao` de `AgroAuthResponse` e removido `tokenRecuperacao` de `AgroForgotPasswordResponse`. As respostas públicas retornam estritamente metadados funcionais (`sucesso`, `mensagem`, `token` de sessão, `usuario`).
  2. `services/api/agro_identity/router.py`: Os endpoints `register` e `forgot_password` deixaram de instanciar ou retornar qualquer código ou token nos payloads de resposta.
  3. `apps/agro/src/lib/auth/agro-auth.ts`: Removido o campo `codigoVerificacao` das tipagens `AgroUsuario` e `AgroAuthResponse`.
  4. `apps/agro/src/components/auth/painel-conta.tsx`: Removida qualquer exibição ou referência ao código na interface gráfica. O usuário insere o código numérico de 6 dígitos que recebe exclusivamente na sua caixa de entrada de e-mail.
  5. `apps/agro/tests/e2e/agro-identity.spec.ts`: Mocks atualizados para refletir o comportamento real onde a API pública nunca envia o código no JSON.
  6. **Captura Interna em Testes:** A suíte de integração e testes unitários (`test_agro_identity.py`) captura os códigos emitidos exclusivamente através da infraestrutura interna `get_sent_emails()` do módulo `email_dispatch`, sem nenhuma exposição externa.
  7. **Higiene de Logs:** Os logs estruturados do Loguru (`service.py`) registram apenas os identificadores de usuário (`user_id`), nunca os códigos de verificação ou tokens em claro.

### 2.2 Segurança de Arquivo e Diretório do SQLite
- **Diagnóstico:** O arquivo SQLite residia na pasta de código-fonte `services/api/agro_identity.db` com permissões herdadas do umask padrão do sistema (`0022`), o que tornava o arquivo legível por outros usuários do sistema (`0644`).
- **Endurecimento Implementado:**
  1. **Diretório Persistente Isolado:** Definido caminho persistente fora do código-fonte em `/opt/lampp/htdocs/farm/data/agro_identity/` (configurável pela variável de ambiente `AGRO_IDENTITY_DB_DIR`).
  2. **Permissões POSIX Estritas (0700 / 0600):**
     - O diretório `data/agro_identity/` é criado e mantido com permissões `0700` (`drwx------`): somente o processo proprietário tem acesso de leitura, escrita e travessia.
     - O arquivo principal `agro_identity.db` e os arquivos auxiliares de log WAL (`agro_identity.db-wal`) e memória compartilhada (`agro_identity.db-shm`) recebem permissões `0600` (`-rw-------`): inacessíveis a qualquer outro usuário ou processo do sistema operacional.
  3. **Umask Restrito em Tempo de Execução:** Em `database.py`, as chamadas de inicialização e criação de tabelas operam sob `os.umask(0o077)`, assegurando que qualquer arquivo criado pelo SQLite nasça com permissões restritas.
  4. **Auditoria de Usuário:** O processo da API executa sob o usuário `borgus` (uid 1000, gid 1000). A inspeção confirmou que os diretórios e arquivos gerados pertencem exclusivamente a este usuário.

### 2.3 Procedimento Seguro de Backup Online e Restauração
- **Módulo Implementado:** Criado `services/api/agro_identity/backup.py`.
- **Tecnologia:** Utiliza a API nativa de backup a quente do SQLite (`Connection.backup`), que realiza a cópia atômica página por página sem travar escritores ou leitores em modo WAL.
- **Garantias Operacionais:**
  1. `create_sqlite_backup(dest_dir, src_path)`: Executa backup online em snapshot nomeado com timestamp UTC (`agro_identity_backup_YYYYMMDD_HHMMSS.db`), ajusta permissões para `0600` e roda imediatamente `PRAGMA integrity_check`. Se a integridade falhar, o arquivo é deletado e uma exceção é disparada.
  2. `restore_sqlite_backup(backup_file, target_path)`: Valida a integridade do backup antes de restaurar, aplica a restauração atômica, expurga arquivos WAL/SHM residuais para arranque limpo, restringe as permissões a `0600` e valida a integridade do banco restaurado.
  3. `cleanup_old_backups(dest_dir, retention_days)`: Procedimento de retenção automática expurgando arquivos de snapshot anteriores à janela de 30 dias.
  4. **Proteção em Produção:** Documentada política para que backups periódicos sejam cifrados com AES-256 ou GPG e sincronizados com bucket S3/Cloud Storage segregado com Server-Side Encryption (SSE-KMS).

### 2.4 Topologia de Domínios, Cookies, CORS e Proteção CSRF Inter-Subdomínios
- **Topologia Oficial Homologada:**
  - `https://agro.deepfarms.com.br` (PWA Produtor Rural)
  - `https://api.deepfarms.com.br` (API Gateway / Backend FastAPI)
  - `https://app.deepfarms.com.br` (SaaS Comercial Corporativo)
  - `https://campo.deepfarms.com.br` (PWA Operações Offline de Campo)

- **Análise do Risco de CSRF Inter-Subdomínios:**
  - Por compartilharem o mesmo domínio registrável (*registrable domain* ou eTLD+1: `deepfarms.com.br`), requisições originadas de scripts em `app.deepfarms.com.br` ou `campo.deepfarms.com.br` em direção a `api.deepfarms.com.br` são tratadas pelos navegadores como **Same-Site**.
  - Consequentemente, o atributo `SameSite=Lax` no cookie de sessão, por si só, **não impede** que um script malicioso ou vulnerável em outro subdomínio execute requisições com credenciais anexadas.

- **Proteção Implementada (Defesa em Profundidade):**
  1. **CORS Central (`services/api/core/config.py`):** Inclusão explícita de `https://agro.deepfarms.com.br`, `https://api.deepfarms.com.br`, `https://app.deepfarms.com.br` e `https://campo.deepfarms.com.br` na lista `allow_origins`.
  2. **Guardrail CSRF Dedicado (`verify_agro_csrf` em `security.py`):**
     - Intercepta todas as operações que alteram estado (`POST`, `PUT`, `PATCH`, `DELETE`) autenticadas por cookie de sessão (`deepfarms_agro_session`).
     - Inspeciona o cabeçalho `Origin` (com fallback para `Referer`). Rejeita sumariamente com **HTTP 403 Forbidden** qualquer requisição originada de outros subdomínios (como `app.deepfarms.com.br` ou `campo.deepfarms.com.br`) ou de domínios externos.
     - Valida os metadados do navegador `Sec-Fetch-Site` (RFC Fetch Metadata), bloqueando requisições marcadas como `cross-site`.
  3. **Header Anti-CSRF no Frontend:** O cliente `apps/agro/src/lib/auth/agro-auth.ts` anexa o cabeçalho customizado `"X-Agro-CSRF": "1"` em todas as chamadas de mutação, impedindo submissões automáticas via formulários HTML tradicionais (`<form method="POST">`).
  4. **Atributos de Cookie Seguros:** Cookie `deepfarms_agro_session` emitido como `HttpOnly=True` (imune a leitura via XSS), `SameSite=Lax`, `Secure=True` em produção e escopo Host-Only (`domain=None`), impedindo vazamento para nós irmãos.

---

## 3. Matriz de Testes e Evidências

### 3.1 Backend — Pytest Unitário e de Integração
Comando executado:
```bash
services/api/.venv/bin/pytest services/api/tests/unit/test_agro_identity.py -v
```
**Resultado:** **13 testes executados, 13 aprovados (100% de sucesso)** em 18.30s.

| Teste | Objetivo | Status |
|---|---|---|
| `test_01_cadastro_login_e_perfil` | Cadastro, emissão de sessão, código NÃO exposto na API pública, validação por e-mail | **APROVADO** |
| `test_02_protecao_forca_bruta_e_lockout` | Bloqueio temporário (429) após 5 tentativas incorretas | **APROVADO** |
| `test_03_logout_e_revogacao_sessao` | Encerramento atômico e invalidação imediata no cliente | **APROVADO** |
| `test_04_recuperacao_senha` | Redefinição com token NÃO exposto na API pública, uso único estrito | **APROVADO** |
| `test_05_rejeicao_de_token_individual_no_saas_comercial` | HTTP 403 Forbidden imediato ao tentar acessar rotas comerciais | **APROVADO** |
| `test_06_ausencia_de_tenants_comerciais` | Auditoria na base comercial: zero tenants ou tenant_usuarios criados | **APROVADO** |
| `test_07_envelope_encryption_vault_contracts` | Cifra autenticada AES-256-GCM + AAD via contrato KMS | **APROVADO** |
| `test_08_mudanca_de_senha_e_revogacao_de_sessoes` | Revogação em massa de todas as sessões anteriores ativas | **APROVADO** |
| `test_09_rate_limiting_distribuido_e_resiliencia_redis` | Contagem distribuída e fallback resiliente em memória sob falha do Redis | **APROVADO** |
| `test_10_guardrail_zero_conexoes_postgres_comercial` | Bloqueio 403 ocorre antes de get_session (0 conexões comerciais gastas) | **APROVADO** |
| `test_11_protecao_csrf_e_isolamento_subdominios` | Bloqueio 403 para requests de app.deepfarms.com.br e liberação para agro | **APROVADO** |
| `test_12_seguranca_permissoes_sqlite_e_diretorio` | Validação de permissões POSIX 0700 no diretório e 0600 nos arquivos | **APROVADO** |
| `test_13_backup_online_restauracao_e_integridade` | Criação de backup online, restauração e checagem PRAGMA integrity_check | **APROVADO** |

### 3.2 Backend — Regressão Completa de Mercado e Indicadores
Comando executado:
```bash
services/api/.venv/bin/pytest services/api/tests/unit/test_agro_identity.py \
                             services/api/tests/unit/test_ptax_publico.py \
                             services/api/tests/unit/test_macro_publico.py \
                             services/api/tests/unit/test_ibge_sidra_publico.py
```
**Resultado:** **50 testes executados, 50 aprovados (100% de sucesso)** em 23.92s.

### 3.3 Frontend Vitest (`apps/agro`)
Comando executado:
```bash
pnpm --filter agro test
```
**Resultado:** **90 testes executados, 90 aprovados (100% de sucesso)** em 6 suites.

### 3.4 Tipagem TypeScript Estrita (`apps/agro`)
Comando executado:
```bash
pnpm --filter agro typecheck
```
**Resultado:** `tsc --noEmit` concluído com **0 erros de tipagem**.

### 3.5 Build de Produção Next.js 16 (`apps/agro`)
Comando executado:
```bash
pnpm --filter agro build
```
**Resultado:** Compilação concluída com sucesso; 10 rotas estáticas pré-renderizadas sem advertências.

### 3.6 Testes End-to-End no Navegador Real (Playwright)
Comando executado:
```bash
pnpm --filter agro exec playwright test tests/e2e/agro-identity.spec.ts
```
**Resultado:** **7/7 testes aprovados (100% de sucesso)** em 8.0s:
1. Acesso anônimo a `/`, `/mercado` e `/calculadoras`.
2. Acesso à área de Conta via Desktop.
3. Acesso à área de Conta via Mobile.
4. Alternância entre formulários de Login, Cadastro e Recuperação.
5. Auditoria de sessão segura: zero tokens no `localStorage`.
6. Fluxo completo E2E de cadastro, confirmação de código e persistência pós-reload.
7. Fluxo completo E2E de recuperação de senha e login autenticado.

---

## 4. Matriz de Arquivos Modificados / Criados

| Arquivo | Ação | Descrição da Mudança |
|---|---|---|
| `services/api/agro_identity/schemas.py` | Modificado | Removidos campos `codigoVerificacao` e `tokenRecuperacao` dos schemas públicos. |
| `services/api/agro_identity/router.py` | Modificado | Removido retorno de códigos nas rotas `register` e `forgot_password`; aplicado `verify_agro_csrf` em endpoints de mutação. |
| `services/api/agro_identity/config.py` | Modificado | Configurado diretório persistente protegido `data/agro_identity/` fora do código-fonte e lista de origens homologadas. |
| `services/api/agro_identity/database.py` | Modificado | Injetado controle de umask `0o077` e listener para garantia de permissões `0600`/`0700` no SQLite e arquivos WAL/SHM. |
| `services/api/agro_identity/backup.py` | Criado | Implementação da rotina de backup online a quente (`sqlite3.backup`), restauração e checagem de integridade física. |
| `services/api/agro_identity/security.py` | Modificado | Implementada dependência `verify_agro_csrf` com validação de `Origin`, `Referer` e metadados de requisição. |
| `services/api/core/config.py` | Modificado | Adicionados explicitamente os 4 subdomínios da topologia na lista `allow_origins`. |
| `apps/agro/src/lib/auth/agro-auth.ts` | Modificado | Removido `codigoVerificacao` das tipagens e adicionado cabeçalho `"X-Agro-CSRF": "1"` nas requisições mutantes. |
| `apps/agro/src/components/auth/painel-conta.tsx` | Modificado | Removido badge de teste do código de confirmação na UI. |
| `apps/agro/tests/e2e/agro-identity.spec.ts` | Modificado | Atualizados mocks dos testes E2E sem o código exposto na resposta. |
| `services/api/tests/unit/test_agro_identity.py` | Modificado | Adicionados testes 11 (CSRF inter-subdomínios), 12 (permissões POSIX) e 13 (backup online e restauração). |
| `.gitignore` | Modificado | Adicionados `data/`, `var/`, `*.db`, `*.db-shm` e `*.db-wal` para higiene de versionamento. |
| `README.md` | Modificado | Documentado o fluxo homologado e as garantias de segurança da Identidade Individual na seção `## Features`. |

---

## 5. Diretrizes e Encaminhamento para a Fase C3

Com a homologação e o endurecimento de segurança (C2A + C2B) concluídos com êxito:
1. **Restrições Cumpridas:**
   - Nenhum provedor de cotações em tempo real (Twelve Data, Polygon, IBKR) foi cadastrado com chaves reais.
   - Nenhuma tabela do PostgreSQL comercial foi alterada.
   - Nenhum comando de deploy, commit ou push foi executado.
2. **Próximo Passo:**
   - O projeto está **100% preparado e homologado** para iniciar a fase **DEEPFARMS-AGRO-FREE-01E2F-C3 (Arquitetura e Cofre BYOK)**, na qual implementaremos a gestão de chaves do usuário (Envelope Encryption com KMS e cofre segregado).
