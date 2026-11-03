# DEEPFARMS-DEPLOY-01B — Inventário Real da Hostinger

**Data:** 03/11/2026

**Escopo:** inventário documental e local, somente leitura. Nenhuma conexão SSH à VPS foi feita.

**Veredicto:** **NO-GO para iniciar a implementação do deploy de produção até identificar e confirmar o endpoint Hostinger autorizado e concluir a coleta read-only.** O planejamento de CI pode ser detalhado localmente, mas a configuração de produção não deve ser inferida do Compose versionado.

## 1. Resumo executivo

Não foi possível estabelecer acesso à Hostinger de forma segura: há uma chave privada local chamada `~/.ssh/deepfarms_hostinger` (modo `0600`), mas não há `~/.ssh/config`, hostname/IP Hostinger associado, nem confirmação de que essa chave esteja instalada na KVM. Um relatório operacional de 30/10/2026 também registra que o endereço da KVM não foi identificado, que o domínio da API apontava para a EC2/AWS e que não foi tentado SSH nesse host. Como o solicitante condicionou a execução à confirmação de acesso autorizado, nenhum SSH foi tentado.

Assim, **não há inventário novo da máquina física**: branch/commit em produção, alterações locais, containers/imagens/digests, volumes, backups, usuários, permissões, portas, recursos e agentes de deploy ficam **NÃO VERIFICADOS** nesta rodada. Um snapshot informado pelo operador em 31/10/2026 registra nove containers no projeto `farm`, Compose `/opt/deepfarms/farm/docker-compose.hostinger.yml` e PostgreSQL 16 saudável, mas não fornece conteúdo completo do Compose nem é confirmação do estado de 03/11.

O checkout local também não contém o Compose `docker-compose.hostinger.yml`. O `docker-compose.prod.yml` versionado não corresponde ao inventário histórico de serviços: define API, Web e três workers; não define Campo PWA, Agro PWA, PostgreSQL nem Redis. Usa tags locais mutáveis `pilot`, não declara volumes, healthchecks ou registry. Os arquivos efetivos da KVM precisam ser obtidos antes de especificar um diff de produção seguro.

## 2. Confirmação de acesso e limites

### Evidência local consultada

- `ls -l ~/.ssh/deepfarms_hostinger ~/.ssh/deepfarms_hostinger.pub`: a identidade candidata existe; a chave privada tem modo `0600`, a chave pública `0644`. Os conteúdos não foram lidos.
- `rg --files ~/.ssh`: não há arquivo SSH `config`; aparece `known_hosts`, que por si só não mapeia o endereço à KVM.
- `docs/implementation/reports/AGRO-MVP-RELEASE-02-VERIFICACAO-HOSTINGER.md:8, 61–68` registra que em 30/10 o destino Hostinger não foi identificado, o endereço DNS consultado correspondia ao host EC2/AWS e não houve tentativa SSH. O relatório registra que a chave local não tinha hostname/IP Hostinger associado.
- `README.md:18–23` contém uma conexão SSH para EC2/AWS, não para Hostinger. Essa máquina não foi acessada.
- A fotografia Hostinger mais recente encontrada, `DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md:3–5, 18–29`, tem data de 31/10/2026 e explicita que foi informada pelo operador, sem acesso remoto direto do Codex nesta atualização.

A existência de uma chave com nome sugestivo não comprova identidade do servidor, host key, autorização operacional ou que a chave esteja autorizada no usuário `deepfarms` da VPS. Não foi feito DNS lookup, teste de porta, tentativa de autenticação nem conexão à Lauro, Flash, EC2 ou Hostinger.

### Resultado por item solicitado

| Item | Evidência atual | Situação |
|---|---|---|
| Endpoint/host key Hostinger autorizado | Não identificado no checkout/configuração SSH local; relatório de 30/10 diz que faltava essa associação. | **NÃO VERIFICADO** |
| Branch, commit e alterações na VPS | Sem sessão SSH. | **NÃO VERIFICADO** |
| Compose efetivo | Snapshot operador cita `/opt/deepfarms/farm/docker-compose.hostinger.yml`; conteúdo não está no checkout nem foi lido da VPS. | **PARCIAL — nome histórico; conteúdo NÃO VERIFICADO** |
| Projeto e serviços Compose ativos | Snapshot de 31/10 informa projeto `farm` e nove containers: `web`, `api`, `outbox-worker`, `automations-worker`, `background-worker`, `agro`, `campo`, `postgres`, `redis`. Não revalidado. | **PARCIAL — snapshot histórico** |
| Imagens, tags, digests e versão em execução | Sem saída atual de `docker ps`/`docker inspect`. | **NÃO VERIFICADO** |
| Scripts, workflows remotos, webhook ou agente de atualização | Sem inspeção do host. | **NÃO VERIFICADO** |
| PostgreSQL saudável | Reportado no snapshot de 31/10; sem validação atual. | **PARCIAL — snapshot histórico** |
| Volumes, bind mounts, uploads e outros dados persistentes | Não informados pelo snapshot. | **NÃO VERIFICADO** |
| Rotina de backup | Não há evidência de timers, cron ou scripts de backup da KVM. Nenhum backup foi executado. | **NÃO VERIFICADO** |
| Recursos de CPU, RAM, swap, disco e containers | Não coletados na VPS. | **NÃO VERIFICADO** |
| Usuários e permissões dos env files | Usuário operacional `deepfarms` é contexto do solicitante, não foi inspecionado. Arquivos/valores não lidos. | **NÃO VERIFICADO** |
| Portas, isolamento de Tara e projetos Compose | Sem inspeção atual. | **NÃO VERIFICADO** |

## 3. Evidências locais do repositório

Branch e commit do **checkout de auditoria**, não da produção: `main`, `167db4bce669aa913d380226a6f1b4d442e20845`. O checkout está sujo: há alterações locais preexistentes em `README.md`, aplicações e API, além de teste não rastreado e do relatório 01A. Nada disso foi incorporado à VPS ou alterado por esta auditoria. O status não pode ser usado como evidência do checkout Hostinger.

Comandos locais de leitura usados nesta etapa: `git status --short`; `git branch --show-current`; `git rev-parse HEAD`; `rg --files` filtrando Compose, Dockerfiles e workflows; `rg` em documentação para referências SSH/Hostinger; `ls -l` apenas para metadados da chave local. Nenhum comando Docker, Compose, banco ou SSH foi executado.

### Compose e imagens versionados

- `docker-compose.prod.yml:1–75` declara `api`, `automations-worker`, `background-worker`, `outbox-worker` e `web`. Backend é `deepfarms-backend:pilot`; Web é `deepfarms-web:pilot`. Os três workers compartilham a imagem de backend com a API.
- O mesmo arquivo usa `restart: unless-stopped`, uma rede `deepfarms`, `expose` interno para API/Web e `services/api/.env.production` para API e workers (`docker-compose.prod.yml:5, 13–18, 20–75`). Isso descreve apenas o artefato local, não o conteúdo efetivo da VPS.
- O Compose local não contém `build`, registry, tags por commit/digest, healthchecks, volumes ou serviços PostgreSQL/Redis. Também não contém `campo` ou `agro`.
- `docker-compose.yml:4–28` é o Compose de desenvolvimento com `postgres_data` e `redis_data`; não demonstra persistência de produção.
- `infrastructure/staging/docker-compose.agro-staging.yml:13–25` declara volumes isolados para PostgreSQL, Redis e MinIO; a configuração de staging não prova a topologia da VPS.
- Dockerfiles encontrados no repositório: `Dockerfile.backend`, `Dockerfile.web` e `Dockerfile.agro`. Web e Agro têm estágios separados de build/runner; Backend é estágio único. Não foi encontrado Dockerfile específico de Campo na árvore do checkout (`rg --files` filtrado por `Dockerfile`).
- Há somente um workflow local, `.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`, de homologação/testes PostgreSQL. Não publica imagens nem conecta à produção; ver auditoria 01A para o detalhamento.
- `scripts/staging/up.sh` e `scripts/staging/down.sh` são exclusivos de staging. O segundo contém `down --volumes` e remoção de volumes de staging, portanto não deve ser reaproveitado na produção.

## 4. Diferença entre Compose versionado e fotografia Hostinger

| Aspecto | Checkout local | Hostinger (informado em 31/10) | Lacuna |
|---|---|---|---|
| Arquivo Compose | `docker-compose.prod.yml` | `/opt/deepfarms/farm/docker-compose.hostinger.yml` | Arquivo Hostinger ausente localmente e não lido. |
| Projeto/containers | Compose define cinco serviços de aplicação | Projeto `farm`, nove containers reportados | Não há comparação de configuração nem confirmação de execução atual. |
| Serviços de app | API, Web, três workers | API, Web, três workers, Agro e Campo | Compose versionado não cobre Agro/Campo. |
| Banco/cache | Nenhum no Compose prod | PostgreSQL e Redis reportados como containers | Volumes, configuração, rede e restart desconhecidos. |
| Imagens | Tags locais `pilot` | Tags/digests não informados | Não se sabe se Hostinger usa tag, build local, digest ou registry. |
| Healthchecks/persistência | Sem healthchecks/volumes no Compose prod | Não descritos na fotografia | Não se pode afirmar preservação do banco/uploads. |

## 5. Persistência e capacidade: achados e limites

### Persistência que deve ser protegida

Na futura implantação, devem permanecer intocados todos os volumes nomeados e bind mounts de PostgreSQL, Redis, uploads, mídia e demais dados; os diretórios de backup; e quaisquer volumes de Tara ou outros projetos. **Os nomes/caminhos reais da VPS não estão verificados**, então nenhum nome além dos volumes de desenvolvimento/staging acima pode ser atribuído à produção.

Antes de automatizar, inventariar mounts dos containers em execução e confrontar cada destino com o Compose. Confirmar também rotina e destino de backup por timer/cron/script e logs recentes, sem executar backup/restauração. Backup existente não pode ser presumido pela presença do container PostgreSQL.

### Recursos

Memória disponível, swap, espaço livre, tamanho do cache Docker, carga/CPU e consumo individual dos containers estão **NÃO VERIFICADOS**. O relatório de capacidade KVM 4 (`DEEPFARMS-HOSTINGER-01-AUDITORIA-CAPACIDADE-KVM4.md:9–17`) contém estimativas documentais anteriores, recomenda build fora da VPS e ressalva que não houve medição na Hostinger. Não é evidência de capacidade livre hoje nem de coexistência segura com Tara.

Sem coleta de RAM/carga em funcionamento, uso de disco de imagens, espaço para baixar layers temporárias e consumo combinado DeepFarms+Tara, não há base para aprovar build local ou para definir limites de concorrência de pull/restart. A recomendação provisória é construir fora da KVM e fazer pull de imagens uma por vez, preservando espaço para rollback.

## 6. Segurança

- **Acesso SSH:** há identidade local candidata em `~/.ssh/deepfarms_hostinger`, modo `0600`; não há alias/`HostName` em `~/.ssh/config` porque o arquivo não existe. Host key/endereço/instalação da chave na VPS não foram confirmados. Não foi tentada autenticação.
- **Usuário operacional:** `deepfarms` é informado pelo solicitante; existência, grupos, sudo e permissões não foram verificados remotamente.
- **Env files:** não foi listado nenhum arquivo da VPS nem lido qualquer valor. A permissão/owner dos arquivos continuam pendentes. No checkout, `.gitignore:18–23` não contém regra explícita para `.env.production`, embora o README diga que não deve ser versionado; `.dockerignore:5–11` o exclui do contexto de imagem. Corrigir/validar a proteção de Git é uma mudança local futura, separada do acesso à VPS.
- **Credencial técnica de deploy:** não verificada na VPS nem em GitHub Environments. A chave local com nome de Hostinger não prova que haja uma chave de deploy instalada/permitida para o pipeline.
- **Portas:** listeners atuais e conflitos com Tara não verificados. O Compose local da aplicação publica apenas `expose` em rede Docker, mas a topologia efetiva pode ser diferente.
- **Isolamento:** projetos Compose, redes, volumes, portas e limites de Tara não verificados. Até confirmar, comandos globais como `docker system prune`, `docker compose down` sem `-p/-f` explícitos e qualquer `down --volumes` devem ficar fora do procedimento de deploy.

## 7. Arquitetura CI/CD recomendada após completar o inventário

### Imagens

Com base apenas na fotografia histórica de serviços e nos artefatos locais, a hipótese inicial é publicar:

1. `backend`: uma imagem compartilhada pela API e pelos workers de automações, background e outbox. `Dockerfile.backend` existe.
2. `web`: `Dockerfile.web` existe.
3. `agro`: `Dockerfile.agro` existe.
4. `campo`: PWA consta na fotografia Hostinger, mas falta Dockerfile identificado neste checkout. Definir/construir a imagem de Campo é pré-requisito, após validar a build atual e dependências compartilhadas.

PostgreSQL e Redis não devem ser rebuildados pelo pipeline de app. Se usam imagens oficiais, a atualização de versão dessas dependências deve ser mudança separada e aprovada. A lista de imagens acima precisa ser confirmada contra o Compose efetivo; não é prova de que cada container atual usa esses Dockerfiles.

### GHCR e fluxo de publicação

- GitHub Actions executa validações de PR; somente push aprovado em `main`, com CI verde, publica imagens.
- Publicar em GHCR privado, pelo menos com tag imutável do SHA do commit e registrar digests. Habilitar `packages: write` somente no job de publicação; não conceder credencial de escrita ao host.
- A VPS recebe uma credencial read-only do registry e uma chave SSH de deploy exclusiva. A chave do runner deve usar Environment protegido e usuário remoto limitado a um script allowlistado; primeiro deployment com aprovação manual.
- Serializar deployments do ambiente de produção e não cancelar uma atualização já iniciada. Não disparar deploy para alterações de documentação sem imagem afetada.
- Atualizar somente os serviços afetados no Compose confirmado. Backend code compartilhado pode pedir rebuild da imagem comum, mas reiniciar apenas API/worker(s) que consumam a parte alterada, segundo matriz de dependências validada.
- Usar Compose com imagens imutáveis e release manifest/env operacional sem secrets. O deploy seleciona digest, faz pull e `up -d --no-deps` apenas para o conjunto aprovado. Se o SHA/digest e configuração não mudaram, não reinicia.
- Definir healthcheck para cada serviço de aplicação (workers precisam de mecanismo de heartbeat/health apropriado) e smoke checks HTTP da API/Web/Campo/Agro. Falha após timeout reimplanta os digests anteriores da aplicação.
- Nunca executar `down -v`, `down --volumes`, recriar banco/cache, remover volumes, `docker system prune` ou migration no caminho normal. Rollback volta imagens/código; não reverte schema PostgreSQL automaticamente.

### Deploy independente e Tara

Web, Campo e Agro podem ser candidatos a atualização independente, sujeitos às dependências de pacotes compartilhados e rotas da API. API e os três workers compartilham uma imagem backend, mas cada serviço consumidor pode ser iniciado seletivamente após avaliar compatibilidade. PostgreSQL/Redis não fazem parte do deploy de app.

Antes da coexistência com Tara, confirmar projetos Compose separados, nomes explícitos, redes, volumes, portas do proxy, limites de CPU/RAM, capacidade de disco para duas versões de imagem e rotinas de backup independentes. Usar sempre `-p farm` (ou nome confirmado) e `-f /opt/deepfarms/farm/docker-compose.hostinger.yml` explicitamente; não executar operações globais em todos os containers.

## 8. Lista de alterações necessárias para etapa futura

Esta lista é proposta, não foi aplicada:

1. **Acesso/inventário:** confirmar IP/hostname Hostinger e fingerprint da host key por canal confiável; confirmar que a chave candidata é autorizada para o usuário `deepfarms`. Fazer a coleta read-only da seção 9 e revisar volumes/backup/Tara.
2. **Git:** adicionar regra explícita que impeça versionar `.env.production`/envs de produção e verificar que nenhum segredo real está rastreado; não imprimir valores ao revisar.
3. **Imagens:** manter/revisar `Dockerfile.backend`, `Dockerfile.web` e `Dockerfile.agro`; criar/revisar Dockerfile de Campo, atualmente ausente na árvore local; validar contextos e dependências do monorepo.
4. **Compose efetivo:** alterar o arquivo que realmente opera na VPS (somente após identificar se é o `docker-compose.hostinger.yml`) para referências GHCR por SHA/digest, healthchecks adequados e dependências; não substituir o Compose por `docker-compose.prod.yml` sem reconciliação. Preservar exatamente mounts/volumes existentes.
5. **CI:** ampliar workflow com CI para API/workers e builds/testes dos frontends relevantes, filtros por caminhos, permissões mínimas e bloqueio de publicação em caso de falha.
6. **Publicação:** job condicionado a push de `main` publica backend/web/agro/campo quando necessário no GHCR e guarda digests/releases anteriores.
7. **Credenciais:** configurar Environment de produção com aprovação inicial, chave SSH exclusiva, usuário remoto restrito e credencial GHCR read-only no host. Credenciais de publicação ficam só no `GITHUB_TOKEN` do job correspondente.
8. **Deploy controlado:** criar script allowlistado de atualização seletiva com preflight, serialização, no-op quando digest não muda, pull limitado, healthchecks, logs e rollback de imagem anterior.
9. **Runbook:** documentar deploy manual de emergência e rollback, incluindo confirmação do projeto Compose, SHA/digests e validação dos serviços, sem migrations e sem remoção de volumes.
10. **Homologação:** provar em ambiente isolado deploy parcial, atualização de vários serviços, falha de healthcheck/rollback, preservação dos volumes e coexistência dos projetos, antes de habilitar produção.

## 9. Comandos de leitura para coleta posterior

**Não executados.** Só devem ser usados depois de o operador confirmar endpoint/IP, fingerprint SSH por canal confiável e autorização. O comando SSH abaixo exige host key já confiável (`StrictHostKeyChecking=yes`); substituir o placeholder pelo endpoint confirmado. Não conectar ao endpoint da EC2, Lauro ou Flash.

```bash
ssh -i ~/.ssh/deepfarms_hostinger \
  -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
  deepfarms@<HOSTINGER_IP_OU_HOSTNAME_CONFIRMADO> 'bash -s' <<'READ_ONLY'
set -eu
cd /opt/deepfarms/farm

printf '%s\n' '=== Checkout ==='
git status --short
git branch --show-current
git rev-parse HEAD

printf '%s\n' '=== Arquivos Compose e scripts (somente caminhos) ==='
find . -maxdepth 4 -type f \( -iname '*compose*.yml' -o -iname '*compose*.yaml' -o -iname '*deploy*' -o -iname '*rollback*' \) -print

printf '%s\n' '=== Projeto e serviços ==='
docker compose ls --all --format json
docker compose -p farm -f docker-compose.hostinger.yml ps --all

printf '%s\n' '=== Configuração estrutural redigida ==='
docker compose -p farm -f docker-compose.hostinger.yml config --format json |
  jq '{services:(.services | with_entries(.value |= {image,build:(.build|{context,dockerfile}),container_name,depends_on,volumes,networks,healthcheck,restart,ports,expose,env_file})),volumes,networks}'

printf '%s\n' '=== Containers / imagem configurada / digest local / health / mounts ==='
docker ps --all --no-trunc --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.service"}}\t{{.Image}}\t{{.Status}}'
docker inspect --format '{{.Name}} image={{.Config.Image}} image_id={{.Image}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}{{range .Mounts}} mount={{.Type}}:{{.Name}}:{{.Source}}->{{.Destination}}{{end}}' $(docker ps --all -q --filter label=com.docker.compose.project=farm)
docker image ls --digests --no-trunc

printf '%s\n' '=== Recursos do host ==='
uptime
free -h
swapon --show
df -hT / /opt/deepfarms
nproc
cat /proc/loadavg
docker system df -v
docker stats --no-stream $(docker ps -q --filter label=com.docker.compose.project=farm)

printf '%s\n' '=== Identidade, permissões e listeners (sem conteúdo de env) ==='
id deepfarms
getent passwd deepfarms
find /opt/deepfarms/farm -maxdepth 4 -type f -name '.env*' -exec stat -c '%a %U:%G %n' {} \;
sudo ss -lntup

printf '%s\n' '=== Timers e units (nomes/estado) ==='
systemctl list-timers --all --no-pager
systemctl list-unit-files --type=service --no-pager | grep -Ei 'deepfarms|docker|tara|backup' || true

printf '%s\n' '=== Crontabs e possíveis artefatos de backup (não abrir conteúdo) ==='
crontab -l 2>/dev/null | awk '!/^#/ && NF {if ($1 ~ /^@/) print $1, "<command redacted>"; else if (NF >= 6) print $1, $2, $3, $4, $5, "<command redacted>"}'
find /var/backups /opt/deepfarms /srv -maxdepth 4 -type f \( -iname '*backup*' -o -iname '*.dump' -o -iname '*.sql*' \) -printf '%M %u:%g %TY-%Tm-%Td %p\n' 2>/dev/null
READ_ONLY
```

Notas de segurança para a coleta:

- O `jq` acima seleciona somente campos estruturais do Compose e descarta `environment`, labels arbitrárias e valores interpolados. Não imprimir `docker compose config` bruto, `docker inspect` completo, `env`, `printenv` ou conteúdo de arquivos de ambiente.
- A linha de crontab acima mostra somente o agendamento e oculta integralmente o comando. Não compartilhar comandos completos sem revisão local. Não coletar crontab de root sem necessidade e autorização explícita.
- Para webhooks/agentes externos, além dos caminhos locais, consultar somente a lista de units/processos necessária; não exibir argumentos de processo que possam conter tokens. O inventário de secrets GitHub deve limitar-se a nomes/configuração de Environment, sem revelar valores.
- `docker system df -v` e listagem de imagens são leituras; não executar `prune`, `pull`, `build`, `compose up/down` ou `compose config` sem redaction.

## 10. Pendências que bloqueiam a implementação

1. Endereço Hostinger e fingerprint SSH confirmados por canal confiável, com autorização para o usuário `deepfarms`.
2. Snapshot atualizado do checkout, projeto Compose, containers, imagens/digests e origem das imagens.
3. Compose efetivo com serviços/dependências, healthchecks, env-file paths, redes, restart e mounts confirmados sem revelar valores secretos.
4. Mapeamento inequívoco de volumes PostgreSQL/Redis, uploads e dados de outros serviços; backup recente/existente e rotina identificados.
5. RAM/swap/disco/carga e uso Docker atuais, além dos limites e recursos de Tara, para validar espaço de pull e rollback.
6. Owners/permissões de arquivos env, portas e isolamento entre projetos; confirmar credential scope para deploy.
7. Definir matriz de testes e resolver lacuna de Dockerfile de Campo.

## 11. Veredicto final

**NO-GO para iniciar mudanças de produção do CI/CD nesta etapa**, pois o endpoint/host key autorizado não foi confirmado e o Compose efetivo não foi inspecionado. Não se presume ausência de volumes, backups, agentes ou recursos: todos permanecem **NÃO VERIFICADOS** na VPS.

**GO COM RESSALVAS para preparar a implementação local após** disponibilizar o resultado read-only da coleta e reconciliar o Compose efetivo. A direção recomendada continua sendo GHCR com imagens imutáveis construídas no GitHub Actions, deploy seletivo por SSH restrito, healthchecks, rollback somente de aplicação e proteção explícita de todos os mounts. Nenhuma dessas mudanças foi implementada.
