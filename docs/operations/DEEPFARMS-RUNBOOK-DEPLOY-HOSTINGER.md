# DeepFarms — Runbook de deploy de produção na Hostinger

**Versão:** 1.0  
**Data:** 04/11/2026  
**Ambiente-alvo:** Hostinger VPS KVM 4, Ubuntu  
**Projeto Compose informado:** `farm`  
**Status:** procedimento documental com bloqueios operacionais pendentes

## 1. Objetivo e limites

Este documento orienta a preparação, publicação, atualização e validação das imagens DeepFarms na Hostinger, preservando banco de dados, volumes, configuração de ambiente e serviços fora do escopo da mudança.

O procedimento não executa migrations nem modifica schema/dados. Atualizar imagem não reverte mudanças de banco. Uma mudança que exija migration precisa de plano, revisão e autorização próprios.

**Estado de prontidão:** não executar deploy usando este runbook até fechar as pendências da seção 14. Em particular, o arquivo efetivo `/opt/deepfarms/farm/docker-compose.hostinger.yml` e a configuração do Web não estão no checkout auditado. O `docker-compose.prod.yml` versionado não é substituto para eles.

## 2. Ambientes e arquitetura informada

| Ambiente | Máquina/usuário | Diretório |
|---|---|---|
| Desenvolvimento | Lauro, WSL Ubuntu / `borgus` | `/opt/lampp/htdocs/farm` |
| Banco de desenvolvimento | Flash, WSL Borgus | ambiente separado |
| Produção | Hostinger VPS / `deepfarms` | `/opt/deepfarms/farm` |

O inventário fornecido para a migração GHCR descreve nove containers: Web (`farm-web-1`), Campo (`farm-campo-1`), Agro (`farm-agro-1`), API (`farm-api-1`), três workers (`farm-background-worker-1`, `farm-outbox-worker-1`, `farm-automations-worker-1`), PostgreSQL (`farm-postgres-1`) e Redis (`farm-redis-1`). Portas locais informadas: Web 3000, Campo 3002, Agro 3004 e API 8000. Esses nomes e bindings são dados do operador para a migração; não foram verificados no checkout nem na VPS nesta auditoria. Confirme-os em modo somente leitura antes de usar comandos operacionais.

Imagens da aplicação publicadas pelo workflow:

| Componente | Imagem GHCR | Dockerfile |
|---|---|---|
| Backend (API e workers) | `ghcr.io/maborges/deepfarms-backend` | `Dockerfile.backend` |
| Web | `ghcr.io/maborges/deepfarms-web` | `Dockerfile.web` |
| Campo | `ghcr.io/maborges/deepfarms-campo` | `Dockerfile.campo` |
| Agro | `ghcr.io/maborges/deepfarms-agro` | `Dockerfile.agro` |

`services/api/**` e `scripts/**` acionam o componente `backend`; alterações no backend afetam a mesma imagem usada pelos serviços API, background-worker, outbox-worker e automations-worker. Dependências compartilhadas do workspace (`package.json`, lockfile, workspace e `packages/**`) acionam Web, Campo e Agro.

## 3. Evidências e limitações da auditoria

Foram examinados os quatro Dockerfiles, `.github/workflows/ci.yml`, `.github/workflows/publish-images.yml`, o workflow de homologação PostgreSQL, os scripts `scripts/cicd/deploy_hostinger.py` e `release_manifest.py`, o overlay `docker-compose.hostinger.healthchecks.yml` e documentação técnica versionada.

O checkout **não contém** `docker-compose.hostinger.yml`. O arquivo `docker-compose.prod.yml` lista somente API, Web e os três workers, usa tags locais mutáveis `pilot`, não inclui Campo, Agro, PostgreSQL, Redis nem volumes e não comprova a configuração da Hostinger. O overlay versionado contém healthchecks de aplicações/Redis, mas não substitui o Compose principal. O conteúdo e a configuração resolvida do Compose real devem ser conferidos na VPS antes de qualquer atualização.

O CI constrói imagens sem publicar. O workflow `publish-images.yml` publica imagens, mas não faz SSH nem deploy. Os wrappers `scripts/cicd/deploy_hostinger.sh` e `rollback_hostinger.sh` chamam o controller guardado `deploy_hostinger.py`; não há workflow que os execute. A existência desses arquivos no Git não comprova que foram instalados ou homologados na VPS.

## 4. Gates de preparação e publicação

Na máquina de desenvolvimento:

1. Revisar alterações, testes pertinentes, migrations/RLS/autenticação e configurações sensíveis.
2. Conferir `git status` e `git log -1 --format='%H %s'`; selecionar arquivos explicitamente para o commit. Não usar `git add .` sem revisão.
3. Publicar o commit aprovado em `main` e aguardar os checks obrigatórios.
4. No GitHub Actions, executar manualmente **Publish DeepFarms images to GHCR**, selecionando `main`, `approve_publish=true` e `base_sha` como SHA completo (40 caracteres) do último release publicado. Na primeira publicação, o workflow admite 40 zeros e marca todos os componentes como alterados.
5. Confirmar sucesso da validação completa e da publicação para o SHA correto. O workflow exige `ghcr-publish`; confirmar que a proteção/revisores desse Environment estão efetivamente configurados nas settings do GitHub.
6. Baixar o artefato `release-<componente>-<SHA>` da execução aprovada e guardar o manifesto por digest. Ele registra `commit` e a referência imutável `ghcr.io/...@sha256:...`. O workflow também publica tag do SHA, mas deploy deve usar o digest do manifesto, nunca `latest`, `pilot` ou apenas uma tag mutável.

O CI de publicação chama a validação completa: typecheck/lint dos frontends, testes Agro, guardas Web, testes dos scripts CI, homologação do backend em PostgreSQL descartável e builds das quatro imagens sem push. A homologação usa banco temporário do runner; não autoriza execução de migration no banco de produção.

Antes da janela de deploy, registrar SHA, workflow/run, manifesto e digests novos; obter os digests atuais de forma verificável; confirmar espaço para imagem nova e rollback; confirmar os healthchecks e mounts no Compose resolvido sem registrar valores de env/secrets; confirmar backup/restore conforme seção 6. Não sincronizar a VPS com `git pull`, `git reset --hard` ou `git clean` automaticamente. Não imprimir `docker compose config` sem tratamento: a saída pode conter valores interpolados de ambiente.

## 5. Preflight somente leitura na VPS

Após fechar as pendências documentais e obter autorização operacional para a janela, confirmar o host e o estado sem alterar recursos:

```bash
cd /opt/deepfarms/farm
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
sudo docker compose -p farm -f docker-compose.hostinger.yml ps --all
sudo docker compose -p farm -f docker-compose.hostinger.yml config --quiet
```

O `config --quiet` valida o Compose sem mostrar a configuração expandida. Antes de usar o projeto `farm` ou esses nomes, comparar com a configuração efetiva em uso. Não fazer `pull`, `up`, `restart`, `down`, limpeza, edição ou `git` de sincronização durante o preflight.

Fazer cópia com nome único antes de qualquer edição operacional do Compose. A edição direta de `image:` não é o fluxo recomendado pelo controller do repositório, que aplica um override temporário limitado aos serviços selecionados. Se a operação manual for necessária, exigir revisão do diff e confirmar que só os serviços pretendidos mudaram.

## 6. Backup e rollback como pré-condição

O controller do repositório exige um recibo JSON de backup com: tarefa agendada verificada, manipulação segura de arquivos temporários verificada, teste recente de restauração isolada aprovado, timestamp ISO-8601 com timezone, caminho absoluto do artefato e SHA-256 correspondente. Tanto recibo quanto artefato precisam ter no máximo 24 horas. O script apenas valida esse recibo e checksum; não cria backup nem testa restauração.

Não fabricar recibo nem tratar um backup sem restore isolado verificado como aprovado. O formato do recibo não é exemplo de execução: deve ser produzido pelo procedimento operacional de backup validado. O processo de deploy falha fechado sem ele.

O rollback é somente da aplicação. O controller mantém as imagens anteriores como aliases locais de rollback e registra estado em `/var/lib/deepfarms-deploy`; confirme que o script foi instalado e que esse diretório é persistente e protegido antes do uso. Não remover imagens necessárias ao rollback. Nenhum passo deve executar `docker volume prune`, `docker system prune`, `down -v`, `--volumes` ou migrations.

## 7. Atualização de componentes gerenciados pelo controller

Este é o fluxo versionado em `scripts/cicd`. Só usar quando o controller, suas permissões, o Compose real, o overlay de healthchecks e o recibo estiverem reconciliados e homologados. O script exige Linux, variável `DEEPFARMS_DEPLOY_TARGET=hostinger` e flag `--confirm-production`. Também exige projeto Compose `farm`, serviços protegidos `postgres` e `redis`, healthcheck ativo nos serviços escolhidos e os volumes existentes/anexados: `farm_postgres_data`, `farm_redis_data` e `farm_uploads_data`.

O controller aceita `backend`, `web`, `campo` e `agro`; `backend` seleciona em conjunto API e os três workers. O `up` é seletivo, usa `--no-deps --no-build`, e não seleciona PostgreSQL ou Redis. A chamada agrupada de backend não corresponde à sequência histórica da migração; não existe ordem universal no workflow. Avaliar compatibilidade de API/workers e processamento crítico antes de selecionar o grupo. Se for necessário atualizar workers/API em etapas separadas, este controller não oferece essa granularidade: planejar procedimento específico antes da janela.

Após revisar o manifesto (SHA e digest) e preparar no host os scripts revisados, o comando documentado para o grupo de componentes é:

```bash
cd /opt/deepfarms/farm
export DEEPFARMS_DEPLOY_TARGET=hostinger
sudo --preserve-env=DEEPFARMS_DEPLOY_TARGET \
  scripts/cicd/deploy_hostinger.sh \
  --manifest /caminho/protegido/release-manifest.json \
  --components backend \
  --backup-receipt /caminho/protegido/backup-receipt.json \
  --confirm-production
```

Substitua `backend` por um componente validado (`web`, `campo`, `agro`) ou por uma lista separada por vírgulas, somente se todos os serviços selecionados forem compatíveis para uma atualização conjunta. Os caminhos são placeholders. O comando acima só é aplicável se o wrapper/script estiver instalado no host no caminho indicado, ownership/permissões e uso de `sudo` tiverem sido validados, e os gates da seção 14 estiverem fechados. Não conceder acesso irrestrito ao Docker a runner externo; acesso ao socket Docker é equivalente a root.

O controller valida a composição e volumes, captura a imagem anterior, aplica um override temporário de imagem por digest, faz pull e atualiza somente os serviços selecionados. Se o healthcheck falhar, tenta reaplicar as imagens anteriores do componente. Isso não valida todos os fluxos funcionais nem garante rollback quando a configuração Compose ou o próprio host está indisponível; acompanhar saída, estado e auditoria local.

O override de imagem é removido ao terminar a operação: o Compose principal não é atualizado. Uma recriação posterior com apenas o arquivo principal pode restaurar a imagem nele declarada. Antes da janela, definir e homologar como preservar o digest aprovado na configuração usada em futuras recriações, sem alterar o Compose de produção durante o ensaio. Até essa reconciliação, o controller não garante que o release sobreviva a uma operação Compose posterior.

## 8. Procedimento específico do Web (container criado manualmente)

O Web informado (`farm-web-1`) foi criado manualmente e sua configuração integral não está no checkout. `Dockerfile.web` declara runtime Next.js na porta 3000, mas não define a rede/alias, bind do host, política de restart, variáveis, mounts ou comando efetivamente usados em produção. O Compose local `docker-compose.prod.yml` define um serviço `web`, mas não prova equivalência com o container manual. O controller seleciona `web` como serviço Compose e **não deve ser usado para esse container até regularização e validação da equivalência**.

Antes de preparar uma atualização manual, um operador autorizado deve coletar e registrar, sem expor valores secretos:

- ID/imagem e digest atualmente executados;
- bindings de porta, política de restart, entrypoint/comando;
- redes e aliases, especialmente rede `deepfarms` e alias `web` informados;
- mounts, dependências e configuração runtime necessária;
- origem segura e versão das variáveis de ambiente, sem imprimir seu conteúdo;
- nome/container, processo de proxy e impacto da troca.

Procedimento para uma janela futura, após essa coleta e revisão:

1. Confirmar o digest GHCR do Web no manifesto publicado e puxar essa imagem imutável. Guardar a referência e o ID da imagem anterior; não remover a imagem anterior.
2. Preparar antecipadamente um comando de recriação fiel a todos os parâmetros observados, com env fornecido de forma segura e rede/alias/porta/restart iguais aos aprovados. Não inventar flags a partir apenas do Dockerfile nem colar saída completa de `docker inspect` em logs/tickets.
3. Revisar o comando e o plano de retorno antes da janela. Como duas instâncias não podem assumir simultaneamente o mesmo bind `127.0.0.1:3000`, decidir previamente como preservar o container antigo para rollback sem deixar dois donos da porta. Não remover o container antigo nem a imagem anterior antes de aprovar a instância nova.
4. Executar a substituição controlada somente na janela aprovada, validar rede e endpoints do Web, e registrar imagem/digest, estado e resultado.
5. Em falha, parar apenas a tentativa nova e restaurar a imagem anterior com a configuração registrada; validar novamente. Não tentar aplicar `docker compose up` ao serviço `web` como rollback do container manual.

Até existir configuração fiel registrada, comando revisado e ensaio do método de troca/retorno, atualização ou rollback do Web é **NO-GO**. Essa lacuna é intencionalmente explícita: não há evidência suficiente neste checkout para fornecer com segurança um `docker run` ou uma recriação Compose exatos.

## 9. Homologação pós-deploy

Após cada atualização, validar o estado apenas dos serviços afetados e confirmar que banco, Redis, volumes e outros projetos permaneceram intocados:

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
sudo docker inspect farm-api-1 \
  --format 'Imagem={{.Config.Image}} Estado={{.State.Status}} Reinicializações={{.RestartCount}}'
```

O segundo comando é exemplo para API; confirmar o nome real antes. Verificar também `.State.Health.Status` nos serviços com healthcheck. O controller verifica healthchecks dos serviços selecionados por até 180 segundos por padrão (configurável entre 30 e 600); seus healthchecks incluem API `/health/ready`, workers por processo e probes HTTP na raiz das aplicações conforme `docker-compose.hostinger.healthchecks.yml`.

Os endpoints locais fornecidos pelo operador para a migração foram API `127.0.0.1:8000`, Web `127.0.0.1:3000`, Campo `127.0.0.1:3002` e Agro `127.0.0.1:3004`. Confirmar os bindings na configuração resolvida antes de usar. Quando confirmados, validar:

```bash
curl -fsS -o /dev/null -w 'live HTTP %{http_code}\n' http://127.0.0.1:8000/health/live
curl -fsS -o /dev/null -w 'ready HTTP %{http_code}\n' http://127.0.0.1:8000/health/ready
curl -fsS -o /dev/null -w 'mercado HTTP %{http_code}\n' \
  http://127.0.0.1:8000/api/v1/public/mercado/precos
curl -fsS -o /dev/null -w 'web HTTP %{http_code}\n' http://127.0.0.1:3000/login
curl -fsS -o /dev/null -w 'campo HTTP %{http_code}\n' http://127.0.0.1:3002/home
curl -fsS -o /dev/null -w 'agro HTTP %{http_code}\n' http://127.0.0.1:3004/
```

Validar rotas Agro necessárias (`/clima`, `/mercado`, `/calculadoras`) e fluxos funcionais relevantes para a mudança; revisar logs dos workers e integrações afetadas. HTTP 200/healthcheck saudável não substitui testes funcionais. Se qualquer verificação crítica falhar, parar a progressão e iniciar rollback apenas do componente atualizado.

## 10. Rollback dos componentes gerenciados

O wrapper consulta `/var/lib/deepfarms-deploy/previous.json`, portanto só pode restaurar um estado anterior gravado pelo controller. Confirmar que o manifesto corresponde exatamente aos componentes da falha e que as imagens locais de rollback existem. O script exige o mesmo alvo e confirmação explícita:

```bash
cd /opt/deepfarms/farm
export DEEPFARMS_DEPLOY_TARGET=hostinger
sudo --preserve-env=DEEPFARMS_DEPLOY_TARGET \
  scripts/cicd/rollback_hostinger.sh \
  --confirm-production
```

Por padrão, rollback restaura o último conjunto gravado em `previous.json`, que pode conter mais de um componente. Revise o arquivo com ferramenta que não exponha credenciais e confirme escopo antes de executar. Não editar esse arquivo às cegas nem usar o wrapper para rollback do Web manual não gerenciado.

Cada nova tentativa de deploy sobrescreve `previous.json` antes da aplicação; um rollback manual saudável também o substitui pelo estado que estava ativo antes do rollback. Preserve e revise os registros e aliases de cada janela antes de outra tentativa: o wrapper não é um histórico de releases e uma segunda execução pode inverter o alvo do rollback.

Se o deploy ainda não foi executado pelo controller, ou o script não foi instalado, o wrapper não é um rollback genérico. Nesse caso, interromper novas atualizações, registrar estado/logs e seguir o procedimento específico revisado do host, restaurando apenas as imagens dos serviços afetados. Rollback de imagem não desfaz migrations, DDL/DML ou alteração de schema; este runbook não autoriza nenhuma dessas ações.

## 11. Baseline informado da migração — 04/11/2026

Os digests abaixo foram fornecidos como resultado consolidado da migração; não foram confirmados no registry nem na VPS durante a auditoria documental. O SHA do commit correspondente não constava no material recebido. Tratar os digests como registro histórico, não como estado atual garantido. Antes de cada deploy, identificar o digest realmente em execução e obter o digest e commit do artefato da publicação aprovada.

| Aplicação | Digest SHA-256 informado |
|---|---|
| Web | `a442620a9ec89714db8c609df11a052b3312bb21223092b93414986a09ba3d73` |
| Campo | `53644851660b1a4340826dfff892982088e83a171c1e71894a4e8da689d58900` |
| Agro | `53f68032d9f3b31472383d0a04ad37a7122a4566f7449bcdf4d722f8dbc0f1d6` |
| Backend e workers | `bb81cb9c502051b6710212c5b6dbf199a3b7e31fee8fbd80d7b25023f72473dc` |

O resultado consolidado informado foi GO, nove serviços em execução e dez endpoints locais aprovados. A publicação externa por DNS/HTTPS foi uma homologação separada. Esta documentação não revalida esses resultados.

## 12. Segurança e preservação

Durante um deploy comum, não executar sem autorização e plano específicos:

- DDL/DML manual no banco principal `farms`, criação/alteração de roles ou políticas RLS;
- migrations em produção;
- `docker volume prune`, `docker system prune`, `down -v`, `--volumes` ou remoção de imagens de rollback;
- impressão/commit/envio de arquivos `.env`, saídas com valores interpolados ou credenciais GHCR;
- sincronização destrutiva da árvore de produção;
- alteração do mecanismo de descoberta de Tenants ou ativação de `RECOMMENDATION_DISPATCHER_DATABASE_URL`.

Preservar uploads e volumes existentes de PostgreSQL e Redis. Nunca atualizar serviços não selecionados, bancos, cache, containers de outros projetos ou infraestrutura Tara por comandos globais.

## 13. Registro do deploy

| Campo | Informação |
|---|---|
| Data/hora e fuso | |
| Responsável | |
| Host/projeto Compose confirmado | |
| Commit Git | |
| Workflow e URL/run | |
| Componentes/serviços selecionados | |
| Digests anteriores e novos | |
| Recibo de backup e restore verificado | |
| Resultado dos healthchecks/endpoints | |
| Resultado funcional e logs relevantes | |
| Reinicializações inesperadas? | |
| Rollback necessário? | |
| Veredicto | GO / GO COM RESSALVAS / NO-GO |

## 14. Pendências que bloqueiam o uso em produção

1. Obter e revisar o conteúdo efetivo do Compose Hostinger e sua configuração resolvida de forma segura; reconciliar nomes de serviços, binds, redes, variáveis, volumes e healthchecks. Não substituir pelo `docker-compose.prod.yml`.
2. Confirmar estado atual da VPS, versões/digests em execução e identidade do projeto Compose. Dados da migração e inventários antigos não bastam para afirmar o estado atual.
3. Fechar o processo do Web manual: registrar configuração sem segredos, validar método de troca/rollback e decidir como/de quando migrar para gerenciamento Compose equivalente. Até então, não atualizar via controller.
4. Confirmar instalação/versão dos scripts de deploy, ownership, permissões, sudo, armazenamento do estado, credencial GHCR somente leitura e host Linux; validar todos os gates contra o Compose real. O workflow não instala nem chama esses scripts.
5. Comprovar backup agendado e restauração isolada recente; fechar manipulação segura de arquivos temporários e definir produtor/proteção do recibo exigido pelo controller.
6. Confirmar espaço em disco, arquitetura da VPS (`linux/amd64` é a plataforma publicada) e retenção das imagens anterior/nova.
7. Homologar deploy/rollback e falhas em ambiente não produtivo equivalente, incluindo volumes preservados e comportamento dos workers. CI de build não é ensaio de deploy.
8. Confirmar proteção real do Environment `ghcr-publish` e branch/checks obrigatórios no GitHub.
9. Homologar a persistência do digest após a remoção do override temporário e as operações Compose posteriores; confirmar o alvo de rollback antes de cada tentativa.

Até fechar essas pendências: **NO-GO para executar o procedimento de produção**. A publicação GHCR aprovada é etapa de criação de artefato; não equivale a autorização nem execução de deploy.

## 15. Regra operacional

Publicar imagens imutáveis, confirmar o alvo e o backup, atualizar somente componentes compatíveis, validar cada etapa e manter uma imagem anterior restaurável. Se configuração real ou estado anterior forem incertos, interromper o deploy e resolver a divergência antes da janela.
