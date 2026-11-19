# DeepFarms — Runbook de deploy de produção na Hostinger

**Versão:** 2.0  
**Data:** 18/11/2026  
**Ambiente-alvo:** Hostinger VPS KVM 4, Ubuntu  
**Projeto Compose:** `farm` (`/opt/deepfarms/farm/docker-compose.hostinger.yml`)  
**Status:** procedimento operacional padrão ativo via CLI `deploy_hostinger` (`/usr/local/bin/deploy_hostinger`)

---

## 1. Objetivo e limites

Este documento define o procedimento oficial para publicar imagens no GitHub Container Registry (GHCR) e atualizar a aplicação DeepFarms na VPS Hostinger utilizando a CLI [`scripts/deploy_hostinger`](../../scripts/deploy_hostinger) (instalada em `/usr/local/bin/deploy_hostinger`), preservando banco de dados, volumes persistentes, arquivos de ambiente e serviços não selecionados.

Regras operacionais fundamentais:

- **Imagens imutáveis:** cada atualização aplica o digest `@sha256:...` exato da build publicada para o commit SHA aprovado. Nunca usar tags mutáveis como `latest` ou `pilot`.
- **Persistência no Compose e backup:** antes de atualizar qualquer serviço, o `deploy_hostinger` gera uma cópia de segurança `docker-compose.hostinger.yml.bak.YYYYMMDDHHMMSS` e grava os novos digests diretamente em `/opt/deepfarms/farm/docker-compose.hostinger.yml`, garantindo que recriações futuras do Compose não voltem para imagens antigas.
- **Política de migrations:** o deploy padrão **não** executa migrations nem altera schema/dados. Quando uma release incluir nova migration Alembic, ela deve ser revisada e testada previamente e aplicada explicitamente com a flag `-m` / `--migrate` (que executa `alembic upgrade head` no container `api` após `docker compose up -d`).
- **Limite de rollback:** rollback restaura apenas as imagens da aplicação; ele **não** reverte migrations Alembic, DDL ou DML já executados no PostgreSQL.

---

## 2. Ambientes e arquitetura verificada

| Ambiente | Máquina / usuário | Diretório |
|---|---|---|
| Desenvolvimento | Lauro, WSL Ubuntu / `borgus` | `/opt/lampp/htdocs/farm` |
| Banco de desenvolvimento | Flash, WSL Borgus | ambiente separado |
| Produção | Hostinger VPS / `deepfarms` | `/opt/deepfarms/farm` |

### Inventário confirmado em produção (`18/11/2026`)

Todos os nove containers abaixo são gerenciados pelo projeto Compose `farm` em `/opt/deepfarms/farm/docker-compose.hostinger.yml`:

| Serviço Compose | Container | Componente GHCR / Imagem base | Porta local |
|---|---|---|---|
| `web` | `farm-web-1` | `web` (`ghcr.io/maborges/deepfarms-web@sha256:...`) | `127.0.0.1:3000` |
| `campo` | `farm-campo-1` | `campo` (`ghcr.io/maborges/deepfarms-campo@sha256:...`) | `127.0.0.1:3002` |
| `agro` | `farm-agro-1` | `agro` (`ghcr.io/maborges/deepfarms-agro@sha256:...`) | `127.0.0.1:3004` |
| `api` | `farm-api-1` | `backend` (`ghcr.io/maborges/deepfarms-backend@sha256:...`) | `127.0.0.1:8000` |
| `automations-worker` | `farm-automations-worker-1` | `backend` (`ghcr.io/maborges/deepfarms-backend@sha256:...`) | interna (`8000/tcp`) |
| `background-worker` | `farm-background-worker-1` | `backend` (`ghcr.io/maborges/deepfarms-backend@sha256:...`) | interna (`8000/tcp`) |
| `outbox-worker` | `farm-outbox-worker-1` | `backend` (`ghcr.io/maborges/deepfarms-backend@sha256:...`) | interna (`8000/tcp`) |
| `postgres` | `farm-postgres-1` | `postgres:16` (protegido; nunca recriado sem plano próprio) | interna (`5432/tcp`) |
| `redis` | `farm-redis-1` | `redis:7-alpine` | interna (`6379/tcp`) |

### Mapeamento de componentes publicados pelo CI/CD

| Componente | Imagem GHCR | Dockerfile | Ocorrências no Compose | Gatilho em `changed_components.py` |
|---|---|---|---|---|
| `backend` | `ghcr.io/maborges/deepfarms-backend` | `Dockerfile.backend` | **4** (`api` + 3 workers) | `services/api/**`, `scripts/**`, `Dockerfile.backend` |
| `web` | `ghcr.io/maborges/deepfarms-web` | `Dockerfile.web` | **1** (`web`) | `apps/web/**`, `Dockerfile.web`, `packages/**`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml` |
| `campo` | `ghcr.io/maborges/deepfarms-campo` | `Dockerfile.campo` | **1** (`campo`) | `apps/campo/**`, `Dockerfile.campo`, `packages/**`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml` |
| `agro` | `ghcr.io/maborges/deepfarms-agro` | `Dockerfile.agro` | **1** (`agro`) | `apps/agro/**`, `Dockerfile.agro`, `packages/**`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml` |

Alterações somente em `docs/**` ou `README.md` não acionam build de imagens.

---

## 3. Passo a passo completo do deploy padrão (`deploy_hostinger`)

### Etapa 1 — Máquina local (`/opt/lampp/htdocs/farm`): Commit e Push para `main`

1. Revisar alterações, suítes de testes pertinentes, eventual migration Alembic (`alembic heads` com head único), regras de RLS/autenticação e ausência de segredos ou `.env`.
2. Conferir os arquivos modificados e preparar o(s) commit(s) selecionando caminhos explicitamente (evitar `git add .` sem revisão):
   ```bash
   git status -s
   git add <arquivos-revisados>
   git commit -m "feat(modulo): descricao objetiva da alteracao"
   ```
3. Enviar para `main` e anotar o SHA completo de 40 caracteres (`<NOVO_SHA>`):
   ```bash
   git push origin main
   git rev-parse HEAD
   ```

---

### Etapa 2 — GitHub Actions: Build e publicação das imagens no GHCR

O CI comum (`ci.yml`) apenas valida e constrói imagens sem push. A publicação no GHCR é feita manualmente pelo workflow [`.github/workflows/publish-images.yml`](../../.github/workflows/publish-images.yml), que também não faz SSH na VPS.

1. No GitHub, acessar **Actions → Publish DeepFarms images to GHCR → Run workflow**.
2. Preencher os campos do formulário:
   - **Use workflow from:** `Branch: main`
   - **`approve_publish`:** marcar **`true`** *(o valor padrão é `false`; se permanecer desmarcado, o job `publish` é ignorado)*
   - **`base_sha`:** colar o SHA completo de 40 caracteres da **última release publicada** (ver seção **6. Histórico de releases e `base_sha` atual**; utilizar `0000000000000000000000000000000000000000` apenas na primeira publicação inicial).
3. Acompanhar a execução:
   - O job `validate` executa a suíte completa (`ci.yml` com `full_validation: true`, incluindo lint/typecheck e homologação do backend em PostgreSQL descartável do runner — sem contato com o banco de produção).
   - O job `changed-components` executa `scripts/cicd/changed_components.py` entre `base_sha` e `HEAD`, definindo a matriz apenas para os componentes alterados.
   - Se o Environment **`ghcr-publish`** solicitar aprovação manual, clicar em **Review deployments → Approve and deploy**.
4. Aguardar todos os jobs (inclusive **`publish`**) finalizarem em verde. Cada componente alterado publica `ghcr.io/maborges/deepfarms-<comp>:<NOVO_SHA>` e envia o artefato `release-<comp>-<NOVO_SHA>` (retido por 90 dias).

---

### Etapa 3 — VPS Hostinger: Instalação ou atualização do `deploy_hostinger`

*(Necessário somente na primeira instalação na VPS ou quando houver alteração em [`scripts/deploy_hostinger`](../../scripts/deploy_hostinger).)*

**Pré-requisitos na VPS:** `docker` (com plugin `docker compose`), `python3`, permissão de acesso ao Docker e login ativo no GHCR (`docker login ghcr.io`).

#### Opção A — Recomendada quando a VPS possui o repositório clonado em `/opt/deepfarms/farm`

Não execute `git pull` diretamente em `/opt/deepfarms/farm` se a árvore local contiver arquivos legados ou *untracked* de deploys anteriores (o merge será abortado para proteger os arquivos locais). Extraia **apenas** o script atualizado diretamente de `FETCH_HEAD` para `/usr/local/bin/deploy_hostinger` sem modificar o checkout da VPS:

```bash
cd /opt/deepfarms/farm
git fetch origin main
git show FETCH_HEAD:scripts/deploy_hostinger | sudo tee /usr/local/bin/deploy_hostinger > /dev/null
sudo chmod 755 /usr/local/bin/deploy_hostinger
```

#### Opção B — Alternativa quando a VPS não possui clone Git

```bash
# 1. Na máquina local:
scp /opt/lampp/htdocs/farm/scripts/deploy_hostinger usuario@IP_DA_VPS:/tmp/deploy_hostinger

# 2. Na VPS:
sudo install -m 755 /tmp/deploy_hostinger /usr/local/bin/deploy_hostinger
rm -f /tmp/deploy_hostinger
```

---

### Etapa 4 — Preflight somente leitura e simulação (`--dry-run`) na VPS

Antes de alterar qualquer container, confirme a saúde atual do host em modo somente leitura:

```bash
cd /opt/deepfarms/farm
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker compose -p farm -f docker-compose.hostinger.yml ps --all
docker compose -p farm -f docker-compose.hostinger.yml config --quiet
```

> Não imprima `docker compose config` sem filtro em terminais ou logs, para evitar exposição de variáveis interpoladas do `.env`.

Em seguida, teste a resolução do comando com `--dry-run` (não baixa imagens e não edita o Compose):

```bash
deploy_hostinger <NOVO_SHA> backend web --dry-run
```

*(Ajuste a lista de componentes para aqueles efetivamente publicados na Etapa 2, ou omita os componentes para detecção automática.)*

#### Referência da CLI `deploy_hostinger`

```text
Uso: deploy_hostinger [COMMIT_SHA] [COMPONENTES...] [OPCOES]
```

| Parâmetro / Opção / Variável | Comportamento |
|---|---|
| `COMMIT_SHA` | Hash SHA completo de **40 caracteres** (hashes curtos de 7–39 chars são rejeitados). Se omitido, o script tenta resolver o `HEAD` da `main` via `git ls-remote "$REPO_URL" refs/heads/main`. **Na VPS, recomenda-se informar o SHA explicitamente** porque o padrão de `DEEPFARMS_REPO_URL` é HTTPS (`https://github.com/maborges/farm.git`) enquanto a VPS utiliza SSH (`git@github.com:maborges/farm.git`). |
| `COMPONENTES` | Lista opcional entre `backend`, `web`, `campo`, `agro`. **Informados explicitamente:** modo estrito — falha se alguma imagem informada não existir no GHCR para aquele SHA. **Omitidos:** verifica os 4 componentes e atualiza apenas os que possuem imagem publicada para o SHA, mantendo os demais intactos. |
| `-m`, `--migrate` | Executa `docker compose -p "$PROJECT" -f "$COMPOSE_FILE" exec -T api alembic upgrade head` logo após `up -d`. Usar somente quando a release incluir migration revisada e aprovada. |
| `-c`, `--compose <caminho>` | Informa caminho alternativo para o `docker-compose`. |
| `-n`, `--dry-run` | Valida argumentos e exibe commit alvo, Compose e componentes sem alterar a VPS. |
| `-h`, `--help` | Exibe a ajuda completa da CLI. |
| `DEEPFARMS_REPO_URL` | Padrão `https://github.com/maborges/farm.git`. Exporte `git@github.com:maborges/farm.git` caso deseje omitir `COMMIT_SHA` na VPS. |
| `DEEPFARMS_GHCR_OWNER` | Padrão `maborges`. |
| `DEEPFARMS_COMPOSE_FILE` | Padrão `/opt/deepfarms/farm/docker-compose.hostinger.yml`. |
| `DEEPFARMS_PROJECT` | Padrão `farm`. |

---

### Etapa 5 — Execução do deploy na VPS

Execute o deploy informando os componentes publicados (ou apenas o SHA):

- **Release sem nova migration de banco:**
  ```bash
  deploy_hostinger <NOVO_SHA> backend web
  ```
- **Release com nova migration Alembic aprovada:**
  ```bash
  deploy_hostinger <NOVO_SHA> backend web --migrate
  ```

O que o `deploy_hostinger` executa automaticamente em sequência:

1. `docker pull ghcr.io/maborges/deepfarms-<comp>:<NOVO_SHA>` para cada componente selecionado/detectado.
2. Extração do digest imutável `@sha256:...` via `docker inspect --format='{{index .RepoDigests 0}}'`.
3. Criação de backup com timestamp: `/opt/deepfarms/farm/docker-compose.hostinger.yml.bak.YYYYMMDDHHMMSS`.
4. Substituição em Python de todas as ocorrências `ghcr.io/maborges/deepfarms-<comp>@sha256:...` no `docker-compose.hostinger.yml` pelo novo digest.
5. Subida controlada dos serviços atualizados com `docker compose -p farm -f /opt/deepfarms/farm/docker-compose.hostinger.yml up -d`.
6. *(Se `--migrate`)* Execução de `docker compose ... exec -T api alembic upgrade head`.
7. Exibição do estado final com `docker compose ... ps`.

---

### Etapa 6 — Homologação pós-deploy e atualização do `base_sha`

Após o término do script:

1. Confirmar que os containers afetados estão `Up` com os novos digests e que `postgres`, `redis`, volumes e demais serviços permaneceram preservados:
   ```bash
   docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
   docker inspect farm-api-1 \
     --format 'Imagem={{.Config.Image}} Estado={{.State.Status}} Reinicializacoes={{.RestartCount}}'
   docker inspect farm-web-1 \
     --format 'Imagem={{.Config.Image}} Estado={{.State.Status}} Reinicializacoes={{.RestartCount}}'
   ```
2. Validar healthchecks e endpoints HTTP locais na VPS:
   ```bash
   curl -fsS -o /dev/null -w 'live HTTP %{http_code}\n' http://127.0.0.1:8000/health/live
   curl -fsS -o /dev/null -w 'ready HTTP %{http_code}\n' http://127.0.0.1:8000/health/ready
   curl -fsS -o /dev/null -w 'mercado HTTP %{http_code}\n' \
     http://127.0.0.1:8000/api/v1/public/mercado/precos
   curl -fsS -o /dev/null -w 'web HTTP %{http_code}\n' http://127.0.0.1:3000/login
   curl -fsS -o /dev/null -w 'campo HTTP %{http_code}\n' http://127.0.0.1:3002/home
   curl -fsS -o /dev/null -w 'agro HTTP %{http_code}\n' http://127.0.0.1:3004/
   ```
3. Validar funcionalmente em produção os fluxos alterados na release (incluindo rotas Agro `/clima`, `/mercado`, `/calculadoras` quando aplicável) e inspecionar logs de `api` e workers para garantir ausência de erros.
4. Registrar o `<NOVO_SHA>` e os novos digests na **Seção 6** deste runbook para que ele seja utilizado como `base_sha` na próxima execução do workflow `publish-images.yml`.

---

## 4. Rollback no fluxo `deploy_hostinger`

Como cada execução bem-sucedida de `deploy_hostinger` cria um backup completo do `docker-compose.hostinger.yml` com os digests anteriores imutáveis, o rollback de aplicação restaura o arquivo de backup e reaplica o Compose:

```bash
cd /opt/deepfarms/farm
ls -lt docker-compose.hostinger.yml.bak.*
cp docker-compose.hostinger.yml.bak.<TIMESTAMP> docker-compose.hostinger.yml
docker compose -p farm -f docker-compose.hostinger.yml up -d
docker compose -p farm -f docker-compose.hostinger.yml ps
```

Alternativamente, sabendo o SHA da release anterior cujas imagens ainda estão no GHCR, também é possível executar `deploy_hostinger <SHA_ANTERIOR> <COMPONENTES>`.

**Atenção:**
- Rollback de imagem **não** desfaz migrations Alembic já aplicadas (`alembic upgrade head`). Se a release problemática alterou o schema de forma incompatível com a versão anterior, execute primeiro um plano específico e revisado de banco antes de retornar a imagem da API.
- Não execute `docker image prune` antes de confirmar a estabilidade da nova versão, para manter as imagens anteriores disponíveis no cache local em caso de rollback imediato.

---

## 5. Fluxo alternativo com controller estrito (`scripts/cicd`)

O repositório também mantém o controller estrito [`scripts/cicd/deploy_hostinger.py`](../../scripts/cicd/deploy_hostinger.py) com wrappers [`scripts/cicd/deploy_hostinger.sh`](../../scripts/cicd/deploy_hostinger.sh) e [`scripts/cicd/rollback_hostinger.sh`](../../scripts/cicd/rollback_hostinger.sh). Diferenças principais em relação ao fluxo padrão (`scripts/deploy_hostinger`):

- Exige execução como root/`sudo` em Linux, `DEEPFARMS_DEPLOY_TARGET=hostinger`, `--confirm-production`, manifesto JSON (`release-<comp>-<SHA>.json`), recibo JSON de backup gerado há menos de 24h (com validação de tarefa agendada, manipulação segura de temporários, teste recente de restore isolado, caminho absoluto e SHA-256 do artefato) e overlay `docker-compose.hostinger.healthchecks.yml`.
- Exige projeto `farm`, serviços protegidos `postgres` e `redis`, healthchecks nos serviços selecionados e volumes `farm_postgres_data`, `farm_redis_data` e `farm_uploads_data`.
- Aceita `backend`, `web`, `campo`, `agro` (sem suporte a `migrations` ou execução de Alembic).
- Grava estado de rollback em `/var/lib/deepfarms-deploy/previous.json` e utiliza um **override temporário** removido ao final — ou seja, **não** persiste os digests novos dentro do `docker-compose.hostinger.yml`.

Caso seja utilizado em uma janela com governança estrita:

```bash
# Deploy
cd /opt/deepfarms/farm
export DEEPFARMS_DEPLOY_TARGET=hostinger
sudo --preserve-env=DEEPFARMS_DEPLOY_TARGET \
  scripts/cicd/deploy_hostinger.sh \
  --manifest /caminho/protegido/release-manifest.json \
  --components backend \
  --backup-receipt /caminho/protegido/backup-receipt.json \
  --confirm-production

# Rollback (restaura /var/lib/deepfarms-deploy/previous.json)
sudo --preserve-env=DEEPFARMS_DEPLOY_TARGET \
  scripts/cicd/rollback_hostinger.sh \
  --confirm-production
```

---

## 6. Histórico de releases e `base_sha` atual

> **Próximo `base_sha` para o workflow `publish-images.yml`:** `5e99b24ddc38f48ce41101e49027e86f944cec7a`

### Release atual em produção — `18/11/2026`

- **Commit SHA (`base_sha` vigente):** `5e99b24ddc38f48ce41101e49027e86f944cec7a`
- **Backup do Compose criado:** `/opt/deepfarms/farm/docker-compose.hostinger.yml.bak.20261119012247`
- **Migration aplicada:** `20261116_planos_acao_maturidade -> 20261118_plano_acao_capex` (`--migrate`)

| Componente | Ocorrências atualizadas | Digest SHA-256 em execução |
|---|---|---|
| `backend` (`api` + 3 workers) | 4 | `sha256:3a261eefb8fdde9ff99198503d605cff049ebf40209662a2cb170a55e04c388f` |
| `web` | 1 | `sha256:2f068a75de57244980283585569f646ad3c44a340e2a1f80ec19d733b3f8b99d` |
| `campo` *(mantido)* | — | `sha256:63ba1917e309d777c76e09e06eabd6034affc4d248f8c0a8d80d8d43945416ad` |
| `agro` *(mantido)* | — | `sha256:442595fe4e57a1c7f6da4f04da473dfc802655d5d1c3a922fcbcd17bb490eb19` |

### Releases anteriores registradas

| Data | Commit SHA | Observação |
|---|---|---|
| Anterior a 18/11/2026 | `d97e0a36891af84ee276fef8cd39cbbbf020c709` | `feat: adicionar gerenciamento de alterações de plano pendentes e tratamento de upgrade automático` |

### Baseline histórico da migração GHCR — `04/11/2026`

Digests consolidados na migração inicial para GHCR (registro histórico):

| Aplicação | Digest SHA-256 histórico |
|---|---|
| Web | `a442620a9ec89714db8c609df11a052b3312bb21223092b93414986a09ba3d73` |
| Campo | `53644851660b1a4340826dfff892982088e83a171c1e71894a4e8da689d58900` |
| Agro | `53f68032d9f3b31472383d0a04ad37a7122a4566f7449bcdf4d722f8dbc0f1d6` |
| Backend e workers | `bb81cb9c502051b6710212c5b6dbf199a3b7e31fee8fbd80d7b25023f72473dc` |

---

## 7. Segurança e preservação

Durante qualquer deploy, é **proibido** executar sem plano específico revisado e autorização explícita:

- DDL/DML manual no banco de produção `farms`, criação ou alteração manual de roles ou políticas RLS;
- comandos destrutivos do Docker: `docker volume prune`, `docker system prune`, `down -v`, `--volumes`;
- impressão, commit ou envio de arquivos `.env`, tokens GHCR ou saída expandida de `docker compose config`;
- sincronização destrutiva na árvore da VPS (`git reset --hard`, `git clean -fd`, `git pull` forçado);
- alteração do mecanismo de descoberta de tenants ou ativação indevida de `RECOMMENDATION_DISPATCHER_DATABASE_URL`.

Preservar integralmente `farm-postgres-1`, `farm-redis-1`, volumes de banco, cache e uploads, bem como outros projetos eventualmente hospedados na VPS.

---

## 8. Registro do deploy

| Campo | Informação |
|---|---|
| Data/hora e fuso | |
| Responsável | |
| Host / projeto Compose | |
| Commit Git (`<NOVO_SHA>`) | |
| Workflow e URL/run | |
| Componentes atualizados | |
| Migration Alembic aplicada (`--migrate`?) | |
| Digests anteriores e novos | |
| Arquivo de backup Compose (`.bak.*`) | |
| Resultado dos healthchecks / endpoints | |
| Resultado funcional e logs relevantes | |
| Reinicializações inesperadas? | |
| Rollback necessário? | |
| Veredicto | GO / GO COM RESSALVAS / NO-GO |

---

## 9. Melhorias e pendências de governança contínua

Itens já resolvidos em relação à versão 1.0:
- `farm-web-1` já está integrado e gerenciado diretamente em `/opt/deepfarms/farm/docker-compose.hostinger.yml`.
- CLI `deploy_hostinger` instalada em `/usr/local/bin/deploy_hostinger`, persistindo digests `@sha256:...` no Compose e criando backup automático `.bak.<timestamp>` antes de cada alteração.

Pendências operacionais de endurecimento contínuo:
1. Manter rotina agendada de backup lógico/físico do PostgreSQL de produção com ensaios periódicos de restauração isolada (e emissão de recibo caso se opte por adotar o controller estrito `scripts/cicd`).
2. Revisar periodicamente as proteções da branch `main` e os revisores obrigatórios do Environment `ghcr-publish` no GitHub.
3. Monitorar espaço em disco da VPS para retenção segura de imagens anteriores de rollback e arquivos `.bak.*` antigos.
4. Opcionalmente, realizar limpeza controlada dos arquivos locais/untracked legados em `/opt/deepfarms/farm` (após inspeção de diff e backup) caso haja necessidade de alinhar o checkout da VPS com `origin/main`.
5. Opcionalmente, definir `DEEPFARMS_REPO_URL=git@github.com:maborges/farm.git` no ambiente da VPS para permitir resolução automática de `HEAD` ao omitir `COMMIT_SHA`.

---

## 10. Regra operacional

Publicar imagens imutáveis pelo GitHub Actions, simular com `--dry-run`, usar `--migrate` somente após revisão de schema/migration, validar healthchecks e fluxos funcionais após cada janela e manter o último backup do Compose e imagens locais preservados para rollback rápido.
