# DEEPFARMS-DEPLOY-01C — Preparação controlada do CI/CD Hostinger

**Data:** 03/11/2026

**Escopo:** preparação local de CI, build/publicação manual de imagens e scripts de deploy/rollback para revisão. Nenhuma conexão, mudança ou operação foi feita na VPS. Nenhum banco, migration, container, volume ou backup foi acessado.

**Veredicto:** **GO COM RESSALVAS para revisão e homologação isolada dos artefatos. NO-GO para ativar deploy na produção** até concluir os gates de backup, segurança de arquivos temporários, Compose real, permissões GHCR/SSH e healthchecks.

## 1. Resumo executivo

O checkout local estava em `main`, commit `8dd110b66a527844f6f304e6bc37adbf7573a2f7`. No início havia apenas um relatório 01B preexistente não rastreado; ele foi preservado. Não havia `docker-compose.hostinger.yml` no checkout. O Compose local de produção não foi alterado nem tratado como substituto da configuração Hostinger.

Foram preparados: workflow de CI para PR/push à `main`, workflow manual para publicar imagens alteradas no GHCR após validação e aprovação externa de Environment, Dockerfile multi-stage de Campo, detector de componentes alterados, manifesto por digest e scripts guardados de deploy/rollback seletivo. **Nenhum workflow executa SSH ou deploy.** A publicação também é manual, exige confirmação explícita e só aceita `main`.

O grupo `backend` mapeia uma única imagem para API e os três workers; deploy e rollback do grupo são coordenados. Web, Campo e Agro podem ser componentes isolados. Os scripts exigem digest GHCR, saúde dos serviços, três volumes persistentes existentes/anexados e um recibo recente de backup/restauração. O deploy usa overlay temporário, `pull` e `up -d --no-deps --no-build` somente nos serviços de aplicação selecionados. PostgreSQL e Redis não entram na lista de atualização.

O teste local cobriu 16 casos de segurança/manifesto, lint e typecheck dos três frontends, Vitest de Agro, guardas Web, sintaxe de shell e parsing YAML. **Não foram feitos builds Docker locais:** este ambiente não tem o plugin `docker buildx`. A validação de build está preparada em GitHub Actions, mas ainda depende de execução em runner.

## 2. Arquivos criados ou modificados

### Modificados

- `.gitignore` — passa a ignorar `.env.*` e preserva `.env.example`, incluindo a proteção local para `.env.production`.
- `.github/workflows/agro-admin-01b2d-postgres-homologacao.yml` — convertido em workflow reutilizável por `workflow_call`; continua usando PostgreSQL descartável e guardrail de host local. O novo CI é o chamador normal.

### Criados

- `.github/workflows/ci.yml` — CI para PR e push em `main`, também reutilizável pelo fluxo de publicação.
- `.github/workflows/publish-images.yml` — publicação manual e aprovada no GHCR; sem etapa de deploy.
- `Dockerfile.campo` — build multi-stage semelhante aos Dockerfiles Web/Agro existentes.
- `scripts/cicd/changed_components.py` — identifica imagens afetadas por caminhos alterados.
- `scripts/cicd/release_manifest.py` — valida SHA/digest, overlay limitado, Compose, volumes e recibo de backup.
- `scripts/cicd/write_release_manifest.py` — escreve manifesto por componente usando digest devolvido pelo Buildx.
- `scripts/cicd/deploy_hostinger.py` — executor com allowlist de aplicação e gates explícitos.
- `scripts/cicd/deploy_hostinger.sh` e `scripts/cicd/rollback_hostinger.sh` — wrappers operacionais.
- `scripts/cicd/tests/test_cicd_release.py` — testes unitários sem Docker ou banco.
- `docs/implementation/reports/DEEPFARMS-DEPLOY-01C-PREPARACAO-CICD-HOSTINGER.md` — este relatório.

Não foram modificados `docker-compose.prod.yml`, `docker-compose.yml`, nenhum Compose da VPS, configurações remotas, credenciais, banco ou dados persistentes. O relatório 01B que já existia no início permanece intacto.

## 3. Inventário técnico usado

| Componente | Artefato atual | Observação para CI/CD |
|---|---|---|
| API FastAPI | `Dockerfile.backend` | Imagem única também contém os módulos usados pelos três workers. Instala bibliotecas Python/GDAL e PyTorch; build relativamente pesado. API expõe `/health/live` e `/health/ready` em `services/api/main.py:742–761`. |
| Workers | Mesma imagem backend | Serviços separados: automations, background e outbox. Devem ser selecionados como grupo quando houver mudança de código compartilhado. Healthcheck de processo/worker precisa existir no Compose real. |
| Web | `Dockerfile.web` | Multi-stage, Next.js/Node 22. Runtime recebe `BACKEND_URL` pelo Compose; nenhum valor/secreto de produção entra no build. |
| Campo PWA | **Novo** `Dockerfile.campo` | Não havia Dockerfile próprio no checkout. Build multi-stage e porta de aplicação 3002; validar a configuração efetiva e variáveis Next antes de publicar. |
| Agro PWA | `Dockerfile.agro` | Multi-stage, Next.js/Node 22, porta 3004; API pode usar `NEXT_PUBLIC_AGRO_API_ORIGIN` conforme `apps/agro/src/lib/api-url.ts`. |
| PostgreSQL/Redis | Imagens de dependência, não imagens DeepFarms | Não são alvo de build/publicação/deploy dos artefatos de aplicação. Volumes protegidos são verificados pelo script. |

O checkout contém `docker-compose.prod.yml`, mas ele não representa o inventário informado da Hostinger: lista API, Web e três workers; omite Campo, Agro, PostgreSQL e Redis, usa tags `pilot`, não define healthchecks nem volumes. O arquivo efetivo `/opt/deepfarms/farm/docker-compose.hostinger.yml` não está no checkout. Por isso os scripts apontam para o caminho efetivo informado e recusam operar se o arquivo, serviços, healthchecks ou volumes necessários estiverem ausentes/divergentes.

Variáveis são runtime: API/workers dependem do arquivo de ambiente privado definido no Compose real; Web usa `BACKEND_URL`; Campo aceita `BACKEND_URL` ou `NEXT_PUBLIC_API_URL`; Agro usa configuração de API da aplicação. Nenhuma variável de produção foi copiada para workflow, Dockerfile ou teste. `.dockerignore` já exclui `.env.*`; a regra Git foi reforçada.

## 4. Workflows preparados

### `ci.yml`

- Dispara em pull requests para `main` e push à `main`; pode ser chamado pelo workflow de publicação.
- Permissão global mínima: `contents: read`.
- Detector de mudanças evita validar/buildar imagens sem alteração de componente. Dependências compartilhadas do workspace acionam Web, Campo e Agro; `services/api/**` e `scripts/**` acionam backend.
- Frontends executam typecheck e lint; Agro também executa Vitest; Web executa o guard de sidebar.
- Backend chama o workflow PostgreSQL 16 existente, que guarda explicitamente contra banco fora de localhost e usa o service container descartável `farms_test`.
- Testa manifestos/scripts com unittest e constrói imagens alteradas com `push: false` em runner GitHub.
- O workflow não acessa GHCR, SSH, Hostinger ou `farms` de produção.

### `publish-images.yml`

- Acionamento somente `workflow_dispatch`; não publica em todo push e não faz deploy.
- Exige ref `main`, confirmação booleana `approve_publish`, `base_sha` completo do último release publicado e CI completo aprovado no mesmo SHA.
- O primeiro publish usa 40 zeros como `base_sha`, selecionando todas as imagens. Próximos publishes comparam o SHA aprovado anterior e constroem apenas componentes afetados.
- Requer GitHub Environment `ghcr-publish`; o job de publicação é o único com `packages: write`. Usa `GITHUB_TOKEN`, sem PAT no repositório.
- Publica `ghcr.io/<owner>/deepfarms-{backend,web,campo,agro}:<SHA completo>` e guarda um artefato de release contendo `image@sha256:digest` por componente.
- Usa `linux/amd64`; arquitetura da VPS precisa ser confirmada no inventário antes da ativação.
- `ghcr-publish` precisa ser configurado nas settings do GitHub com required reviewers e acesso do package ao repositório. Se Environment não tiver proteção configurada, a referência no YAML não cria aprovação por si só.

## 5. Scripts de deploy e rollback

Os wrappers chamam `deploy_hostinger.py`; nenhum workflow os invoca. Para qualquer execução futura, o script exige simultaneamente `DEEPFARMS_DEPLOY_TARGET=hostinger` e `--confirm-production`. Os defaults são Compose `/opt/deepfarms/farm/docker-compose.hostinger.yml`, projeto `farm` e estado `/var/lib/deepfarms-deploy`.

Gates implementados:

1. Manifesto usa SHA completo e referências GHCR por digest sob o owner autorizado (`maborges` por padrão; configurável no host); tags mutáveis como `latest` são rejeitadas.
2. A seleção aceita somente `backend`, `web`, `campo`, `agro`. `backend` expande para API + automations-worker + background-worker + outbox-worker.
3. Compose precisa conter `postgres` e `redis`, todos os serviços selecionados e healthcheck ativo em cada serviço atualizado.
4. Os volumes nomeados `farm_postgres_data`, `farm_redis_data`, `farm_uploads_data` devem estar declarados/anexados corretamente e já existir no Docker host.
5. Um recibo com no máximo 24 horas precisa confirmar: tarefa automática de backup verificada, manipulação segura de temporários verificada, teste de restauração isolada aprovado, caminho absoluto e checksum SHA-256 do artefato existente.
6. O digest GHCR anterior precisa estar disponível e ser inequívoco para todos os serviços do grupo. Se a versão atual só existir como build local/tag sem digest, o primeiro deploy é bloqueado até preparar um rollback verificável.
7. A atualização usa overlay JSON temporário com apenas os serviços selecionados; faz `docker compose pull` e `docker compose up -d --no-deps --no-build <serviços>`. Não chama migrations, `down`, `--volumes`, `prune`, nem seleciona banco/cache.
8. Um lock local serializa chamadas. Versões anteriores são registradas em `/var/lib/deepfarms-deploy/previous.json`; o histórico resumido vai para `deployments.jsonl` sem variáveis ou credenciais.
9. Se healthchecks não ficarem saudáveis no timeout, o script tenta reaplicar os digests anteriores apenas nas imagens selecionadas. `rollback_hostinger.sh` repete o rollback de forma manual e mantém o digest da versão revertida para recuperação posterior.

### Limite de privilégio do Docker

Acesso ao socket Docker equivale, na prática, a privilégios de root. Não foi criado usuário nem concedida associação ao grupo `docker`. Antes de instalar o script, definir um executor SSH com chave/command forçado e superfície restrita, manter wrapper/Compose usados por executor privilegiado protegidos contra alteração pelo próprio usuário remoto e revisar a política de sudo. Não liberar shell root nem Docker irrestrito ao runner. O modelo de executor depende da revisão das permissões reais do host.

### Condição de backup atual

O backup manual recuperado em 03/11 é informação do solicitante, não validação feita nesta etapa. Cron de root, teste de restauração, propriedade/permissões do arquivo e correção do uso de temporários continuam pendentes. O script não faz backup/restauração nem consulta o banco; requer recibo pós-verificação e falha fechado sem ele. O recibo não substitui revisão do procedimento por DBA/operador.

## 6. Secrets e permissões necessários

Nenhum secret real foi criado, lido ou gravado.

| Local | Permissão/configuração futura |
|---|---|
| CI | `contents: read`; sem secrets de produção. PostgreSQL local é service container descartável com credenciais de teste. |
| GHCR publisher | `GITHUB_TOKEN` efêmero e `packages: write` apenas no job protegido. Pacotes privados devem autorizar o repositório. |
| Environment `ghcr-publish` | Required reviewers, restrição de branch a `main` e aprovação antes da publicação. Configuração é externa ao repositório e ainda não existe evidência de que esteja criada. |
| Host pull de imagens | Credencial GHCR somente `read:packages`, guardada por credential helper/arquivo protegido no host; nunca token de publicação. |
| SSH para futuro deploy | Chave exclusiva em Environment `production`, host key verificada por canal confiável, usuário restrito/forced command e concorrência serial. Não existe workflow de deploy nem secret SSH configurado agora. |
| Aplicação | Arquivos env continuam runtime-only, fora do Git e fora do contexto Docker. Nenhum valor foi exposto. |

## 7. Testes executados e resultados

| Verificação local | Resultado |
|---|---|
| `python3 -m unittest discover -s scripts/cicd/tests -v` | **17 testes passaram**: filtro de componentes, digest imutável, owner GHCR autorizado, agrupamento backend, proteção de serviços/volumes, gates de backup e recusa de deploy sem confirmação. |
| `python3 -m py_compile scripts/cicd/*.py scripts/cicd/tests/*.py` | **Passou**. |
| `bash -n scripts/cicd/deploy_hostinger.sh scripts/cicd/rollback_hostinger.sh` | **Passou**. |
| Parsing YAML com PyYAML `BaseLoader` nos três workflows | **Passou** para o workflow reutilizável PostgreSQL, `ci.yml` e `publish-images.yml`. Não substitui validação pelo runner GitHub/actionlint. |
| Web: typecheck, lint, `test:sidebar` | **Passaram**; sidebar reportou 4 guardas. |
| Campo: typecheck e lint | **Passaram**. |
| Agro: typecheck, lint e Vitest | **Passaram**; 13 arquivos e 175 testes. |
| `git diff --check` | **Passou**. |
| Docker Buildx / builds locais | **Não executados**: `docker buildx version` retornou `docker: unknown command: docker buildx`. A validação de imagem está no workflow, mas ainda precisa de execução em GitHub Actions. |
| Teste PostgreSQL CI local | **Não executado**. O workflow usa migrations de homologação somente no service container descartável do runner. Nenhuma migration foi executada nesta tarefa. |

Os testes de manifesto/recibo usam arquivos sintéticos em diretório temporário. Não leram nem modificaram `farms`, dados persistentes, containers ou volumes.

## 8. Pendências para ativação

1. Revalidar em modo read-only o Compose real e preencher/ajustar o mapeamento de services, healthchecks e anexos dos volumes. Não copiar cegamente `docker-compose.prod.yml`.
2. Confirmar arquitetura CPU da VPS, conectividade/credencial read-only do GHCR e disponibilidade de disco para imagem nova + rollback.
3. Corrigir e comprovar cron root de backup e proteção de arquivos temporários; executar restauração recente em instância isolada, gerar recibo e garantir que o executor consiga validar o artefato sem ampliar acesso aos dados.
4. Definir formato/caminho real e retenção dos recibos e backups; manter arquivos privados e sem conteúdo nos logs.
5. Revisar o usuário executor, chave SSH, host key, wrapper restrito, ownership do Compose/scripts e privilégio de acesso ao Docker.
6. Criar/proteger Environment `ghcr-publish`, required reviewers, branch policy, permissões dos pacotes GHCR e política de retenção das tags/digests.
7. Executar o CI em PR e conferir builds reais das quatro imagens; publicar primeiro de forma manual, sem deploy.
8. Homologar deploy/rollback em ambiente não produtivo com Compose equivalente, healthchecks ativos, no-op, falha simulada e prova de que os três volumes e outros projetos não mudam.
9. Só então preparar workflow separado de deploy com aprovação `production`; permanece fora desta alteração e deve ser autorizado em etapa própria.

## 9. Riscos residuais e esforço restante

- O Compose real ainda não foi comparado, então o script pode falhar fechado até adaptar nomes/volume aliases e healthchecks reais.
- O estado atual das imagens pode não ter digests GHCR, impedindo rollback no primeiro uso.
- O recibo depende de uma verificação operacional honesta; ainda não há ferramenta local que audite o cron root ou valide a segurança dos temporários.
- A publicação via GHCR só tem aprovação de verdade se Environment required reviewers for configurado externamente.
- Build do backend é pesado por PyTorch/GDAL e dependências Python com intervalos de versão; runner e tempo de cache precisam ser observados.
- Build publica `linux/amd64`; verificar `uname -m` na VPS antes de ativar.
- Acesso Docker é root-equivalente. A restrição SSH precisa ser testada contra o modelo real de ownership/permissões.
- Actions estão referenciadas por tags major (`@vN`), não por SHA imutável. Para ambiente de alta garantia, fixar os SHAs oficiais revisados antes da ativação.

Estimativa restante: **1–2 dias de engenharia** para integrar ao Compose real, healthchecks e teste de rollback; **0,5–1 dia operacional** para backup/temporários e GHCR/Environment/SSH; **0,5–1 dia** para homologar falhas e coexistência Tara. Não inclui correções de aplicação ou mudanças de banco.

## 10. Veredicto

**GO COM RESSALVAS para revisão dos workflows/scripts e homologação isolada.** Há validações locais para manifests, allowlist, healthchecks, backups e preservação dos serviços persistentes.

**NO-GO para ativar publicação automática ou deploy em produção.** Publicação está manual; não existe job de deploy. O deploy continua condicionado a Compose real e gates operacionais, em especial confirmação do cron root, correção de temporários, backup/restauração recente, healthchecks, credencial read-only do GHCR e executor SSH de privilégio mínimo.
