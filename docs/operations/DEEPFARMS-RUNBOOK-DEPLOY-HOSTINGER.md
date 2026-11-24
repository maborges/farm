# DeepFarms — Runbook de deploy de produção na Hostinger

**Versão:** 2.1  
**Data:** 23/11/2026  
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

### Como obter `base_sha` e `<NOVO_SHA>` (40 caracteres)

Cada ciclo de release usa **dois hashes diferentes** de 40 caracteres:
- **`base_sha`:** commit da **última release já publicada no GHCR** (usado pelo `publish-images.yml` para detectar quais componentes mudaram desde aquela publicação até o `HEAD` atual).
- **`<NOVO_SHA>`:** commit do **novo `HEAD` de `main`** que acabou de receber suas alterações e teve as novas imagens publicadas (passado ao `deploy_hostinger` na VPS).

#### 1) Como obter o `base_sha` (para preencher em `publish-images.yml`)

Escolha qualquer uma das fontes abaixo (todas apontam o mesmo commit):

1. **Diretamente na VPS (mais confiável — lê o label OCI gravado nas imagens em execução):**
   O workflow `publish-images.yml` grava `org.opencontainers.image.revision=<SHA>` em cada imagem publicada. Na VPS, execute:
   ```bash
   docker inspect farm-api-1 farm-web-1 farm-campo-1 farm-agro-1 \
     --format '{{.Name}}: {{ index .Config.Labels "org.opencontainers.image.revision" }}'
   ```
   *(Quando apenas alguns componentes foram atualizados na última release, use o **SHA mais recente** entre eles — correspondente à última publicação que gerou novas imagens.)*

2. **Pelo GitHub Actions (interface web ou `gh` CLI):**
   - Na interface web: abra **Actions → Publish DeepFarms images to GHCR**, clique na última execução **verde** em que o job **`publish`** realmente rodou (não pulado) e copie o SHA completo de 40 caracteres do commit no cabeçalho da execução *(ou os últimos 40 caracteres do artefato `release-<componente>-<SHA>`)*.
   - Via GitHub CLI (`gh`):
     ```bash
     gh run list --workflow publish-images.yml --branch main --status success --limit 5 \
       --json headSha,displayTitle,createdAt
     ```

3. **Pelo runbook ou histórico Git local:**
   - Consulte a **Seção 6 (`Histórico de releases e base_sha atual`)** deste runbook.
   - Ou confira localmente os commits recentes em `origin/main`:
     ```bash
     git log origin/main -n 5 --format='%H %ci %s'
     ```

> **Regras críticas do `base_sha`:**
> - Ele deve ser o SHA da **última publicação no GHCR** (mesmo se houver vários commits depois dele), **nunca** o `HEAD` recém-enviado — se `base_sha` for igual a `HEAD`, `changed-components` retorna `any=false` e o job **`publish`** é pulado.
> - Ele precisa ser ancestral do `HEAD` da `main`.
> - Apenas na **primeira publicação histórica** do repositório utiliza-se `0000000000000000000000000000000000000000` (40 zeros).

#### 2) Como obter o `<NOVO_SHA>` (para rodar `deploy_hostinger`)

1. **Na máquina local, logo após `git push origin main`:**
   ```bash
   git rev-parse HEAD
   # ou para confirmar exatamente o commit enviado no remoto:
   git rev-parse origin/main
   ```
2. **No GitHub Actions:** copie o SHA de 40 caracteres exibido na execução verde recém-finalizada de **Publish DeepFarms images to GHCR** (é o mesmo hash usado na tag `ghcr.io/maborges/deepfarms-<comp>:<NOVO_SHA>` e no artefato `release-<comp>-<NOVO_SHA>`).
3. **Diretamente na VPS (consultando `refs/heads/main` no GitHub via SSH):**
   ```bash
   git ls-remote git@github.com:maborges/farm.git refs/heads/main | awk '{print $1}'
   ```

> **Importante:** o `deploy_hostinger` exige o hash completo de **40 caracteres** (hashes abreviados de 7 a 39 caracteres são rejeitados).

---

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
   - **`base_sha`:** colar o SHA completo de 40 caracteres da **última release publicada** obtido conforme a subseção **Como obter `base_sha` e `<NOVO_SHA>`** (ou na seção **6. Histórico de releases e `base_sha` atual**; usar 40 zeros somente na primeira publicação histórica).
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
<deploy_hostinger> <NOVO_SHA> backend web --dry-run
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

Utilizando o `<NOVO_SHA>` de 40 caracteres (obtido conforme a subseção **Como obter `base_sha` e `<NOVO_SHA>`**), execute o deploy informando os componentes publicados (ou apenas o SHA):

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

> **Próximo `base_sha` para o workflow `publish-images.yml`:** `678012d261e913544b6f8b228b16a58100d996b9`

### Release atual em produção — `23/11/2026`

- **Commit SHA (`base_sha` vigente):** `678012d261e913544b6f8b228b16a58100d996b9`
- **Migrations aplicadas:** nenhuma *(deploy somente de `campo` e `agro`, sem `--migrate`)*

| Componente | Ocorrências atualizadas | Digest SHA-256 em execução |
|---|---|---|
| `backend` (`api` + 3 workers) | 4 | `sha256:ad7c43b719197aeecdeb507056ab45c6c681b7189beec5893b38c707aa5b1737` *(mantido em `88ea65aae64328491c0484cb1d0c9d83437ab1a8`)* |
| `web` | 1 | `sha256:5813436027109010348edb078402a87a37cd0584c10c2343018bffdcffc1c349` *(mantido em `88ea65aae64328491c0484cb1d0c9d83437ab1a8`)* |
| `campo` | 1 | `sha256:7b385bec100c2c21d27db010372fe642b9bafd99264aa905396deaff7a7cf78c` *(atualizado em `678012d261e913544b6f8b228b16a58100d996b9`)* |
| `agro` | 1 | `sha256:59b03e789b704236f707b58875a810ff8a7d5b71a2e93ab09f4a105917c81548` *(atualizado em `678012d261e913544b6f8b228b16a58100d996b9`)* |

### Releases anteriores registradas

| Data | Commit SHA | Observação |
|---|---|---|
| 22/11/2026 | `88ea65aae64328491c0484cb1d0c9d83437ab1a8` | Coletor multi-fonte de cotações (`agro_collector`), acessibilidade em commodities e homologação Hostinger; migrations `20261119_rls_global_catalog_admin_write`, `20261120_pecuaria_lote_hibrido`, `20261122_agro_collector_foundation` *(via `--migrate`)*; `backend` `@sha256:ad7c43b719197aeecdeb507056ab45c6c681b7189beec5893b38c707aa5b1737`, `web` `@sha256:5813436027109010348edb078402a87a37cd0584c10c2343018bffdcffc1c349`, `campo` `@sha256:0fbb2da86e1a47a14827c19d3614a5c7e82e9eb6583e768c16cc467f33d62b3d`, `agro` `@sha256:12ac6266eaaa79d20c026b7f594d505d71e143aad7d95bf76010558c6c1dc7a5` |
| 19/11/2026 | `2f2acc104b60e3ee2ec4f0a2421ad2a27afb5165` | Release sem migration; `backend` `@sha256:a1d882054f0a73f579383c6df99ed14d2e9a6fb8cfc8ede35d28eedf3420e953`, `web` `@sha256:e89e401a9cf85b4954218c5405bf780427015ec72f7951af80632fc2a682f193` (`campo` e `agro` mantidos no commit `30fd5daebd1d5c511d02629d24d303dc878add8b`) |
| 18/11/2026 | `5e99b24ddc38f48ce41101e49027e86f944cec7a` | Viabilidade, Fluxo de Caixa, CapEx e Hectares ILPF; migration `20261118_plano_acao_capex`; backup `.bak.20261119012247`; `backend` `@sha256:3a261eefb8fdde9ff99198503d605cff049ebf40209662a2cb170a55e04c388f`, `web` `@sha256:2f068a75de57244980283585569f646ad3c44a340e2a1f80ec19d733b3f8b99d` |
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
