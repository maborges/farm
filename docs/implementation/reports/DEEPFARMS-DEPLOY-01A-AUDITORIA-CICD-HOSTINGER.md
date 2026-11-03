# DEEPFARMS-DEPLOY-01A — Auditoria de Deploy Automático na Hostinger

**Data:** 03/11/2026

**Escopo:** auditoria estática do checkout e consulta de evidências históricas versionadas. Sem alterações em aplicação, Compose, workflow, banco, VPS ou recursos remotos.

**Branch / commit local:** `main` / `167db4bc` (checkout com alterações locais preexistentes).
**Veredicto:** **NO-GO para ativar deploy automático na produção no estado de evidência atual.** A base de CI é parcial; deploy de produção não está automatizado, e a configuração efetiva da Hostinger precisa ser reconciliada com o Compose local antes de automatizar.

## 1. Resumo executivo

O repositório tem um workflow GitHub Actions de homologação PostgreSQL, executado manualmente ou em pull request, com testes contra banco descartável. Não há workflow de build/publicação de imagens nem de deploy para produção. O deploy documentado na raiz é manual e, segundo o README, nativo com `systemd`; isso diverge do contexto-alvo Hostinger, que informa Docker Compose.

Existe `docker-compose.prod.yml`, mas é um artefato parcial: referencia imagens locais com a tag mutável `pilot`, define API, Web e três workers, e não inclui Campo PWA, Agro PWA, PostgreSQL, Redis, healthchecks ou volumes persistentes. Não há script de deploy/rollback de produção. Há scripts de staging, mas eles não são fluxo de produção e seu script de descarte remove volumes.

Um relatório anterior registra dados informados pelo operador em 31/10/2026: projeto Compose `farm`, arquivo `/opt/deepfarms/farm/docker-compose.hostinger.yml`, nove containers e PostgreSQL 16 saudável. Não houve conexão remota nesta auditoria; portanto, isso é evidência histórica de terceiros, não confirmação do estado atual nem do conteúdo desse Compose.

Para uma VPS KVM 4 que poderá hospedar Tara, recomenda-se build e testes no GitHub Actions, publicação de imagens imutáveis em registry e atualização seletiva dos serviços via SSH restrito, usando o Compose efetivamente confirmado na VPS. Isso reduz CPU, memória, disco e interferência de build na VPS. A implementação deve bloquear migrations automáticas, preservar volumes e manter rollback da aplicação para os digests anteriores.

## 2. Escopo e segurança da auditoria

- Foram lidos arquivos versionados e documentação local, sem abrir arquivos de ambiente com valores de conexão ou credenciais.
- Não houve SSH, comandos na VPS, acesso ao banco `farms`, comandos Docker contra produção, migrations, testes, reinícios, DDL ou DML.
- Não foram feitas alterações remotas. O único arquivo criado por esta etapa é este relatório.
- O checkout já tinha modificações locais em diversos arquivos, inclusive `README.md`; elas foram preservadas. As descrições do README abaixo refletem o conteúdo encontrado no checkout e precisam ser comparadas com `main` remoto antes de tratar o README como fonte aprovada.

## 3. Inventário e classificação

| Item | Situação | Evidência e leitura |
|---|---|---|
| GitHub Actions / CI | **PARCIAL** | Há apenas `.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`. Dispara por `workflow_dispatch` ou `pull_request` para `main`, instala dependências e executa homologação/testes em PostgreSQL descartável (linhas 1–9, 14–32, 47–92). Não é uma suíte geral para todos os componentes. |
| Deploy automático de produção | **AUSENTE** | O workflow existente não tem gatilho de push aprovado à `main`, publicação de imagens, SSH ou etapa de deploy. `rg --files` não encontrou outros workflows. O procedimento de produção descrito no README usa comandos manuais de Git, build e `systemctl` (README.md:16–124). |
| Scripts de deploy de produção | **AUSENTE** | Não foi encontrado script de deploy de produção. `scripts/staging/up.sh` inicializa staging isolado, executa migration nesse banco de staging e inicia seus containers (linhas 19–70); não é deploy da Hostinger. |
| Dockerfiles | **PARCIAL** | Existem `Dockerfile.backend`, `Dockerfile.web` e `Dockerfile.agro`. Web/Agro têm estágios `deps`, `builder` e `runner` (`Dockerfile.web:1–68`; `Dockerfile.agro:1–68`). Backend é uma imagem de estágio único (`Dockerfile.backend:1–42`). Não há Dockerfile versionado para Campo identificado nesta auditoria. |
| Docker Compose de produção | **PARCIAL** | `docker-compose.prod.yml` define API, automations-worker, background-worker, outbox-worker e web (linhas 1–75), mas não define Campo/Agro PWA, PostgreSQL ou Redis. O arquivo usa imagens locais `deepfarms-backend:pilot` e `deepfarms-web:pilot`, sem `build`, registry ou tag por commit/digest (linhas 2–3, 20–21, 32–33, 45–47, 60–62). |
| Docker Compose de desenvolvimento | **IMPLEMENTADO** | `docker-compose.yml` define PostgreSQL e Redis com volumes nomeados `postgres_data` e `redis_data` (linhas 4–28). `.gitignore:70–71` declara que esse Compose é de desenvolvimento e o exclui das imagens/uso de produção; ele não deve ser confundido com o Compose da VPS. |
| Compose de staging | **IMPLEMENTADO** | `infrastructure/staging/docker-compose.agro-staging.yml` possui volumes isolados, builds locais e healthchecks para banco, Redis, MinIO, API, Web e Agro (linhas 13–25, 30–50, 60–82, 87–108, 117–150, 203–255). Esse ambiente é explicitamente separado e não comprova configuração de produção. |
| Atualização automática de containers | **AUSENTE** | Não há Renovate/Watchtower, webhook ou agente de atualização identificado nos artefatos examinados. `restart: unless-stopped` em `docker-compose.prod.yml` reinicia processos encerrados, não busca uma nova versão da imagem (linhas 5, 23, 35, 48, 63). |
| Estratégia de versão de imagens | **AUSENTE** para releases de produção | O Compose de produção usa a tag fixa e mutável `pilot`; não há tags SHA, releases, digest ou política de retenção no workflow/Compose. O runbook legado menciona tags versionadas e recomenda evitar `latest`, mas é um procedimento manual de exemplo para outro contexto (`docs/runbooks/deploy-les-svrbo-ap01.md:1265–1277`, `1465–1502`). |
| Healthchecks na produção | **AUSENTE** no Compose versionado | `docker-compose.prod.yml` não define `healthcheck` nos serviços. O README usa `systemctl is-active` e chamadas `curl` como smoke checks no deploy nativo (README.md:59–67, 104–113), mas isso não é healthcheck do Compose nem gate automatizado. Staging possui healthchecks. |
| Rollback de aplicação | **PARCIAL** | O runbook legado descreve restaurar manualmente tags anteriores e recriar serviços, observando que isso não reverte migrations (`docs/runbooks/deploy-les-svrbo-ap01.md:1486–1502`). Não há automação, registro de release/digest anterior ou mecanismo confirmado para o Compose Hostinger. O README de produção nativa não documenta rollback de release. |
| Persistência e volumes de produção | **AUSENTE / NÃO COMPROVADO** | O Compose versionado de produção não declara volumes nem bind mounts (linhas 1–75), nem inclui o banco/cache. O Compose de desenvolvimento declara volumes do PostgreSQL/Redis, mas isso não prova volumes na VPS. O Compose efetivo Hostinger não foi obtido nesta execução. |
| Variáveis e secrets | **PARCIAL** | O Compose de produção referencia `services/api/.env.production` para API e workers (linhas 13–14, 27–28, 40–41, 55–56); o README orienta não versionar esse arquivo (linhas 142–145). Porém, `.gitignore:18–23` cobre `.env.local` e `.env` exato, não contém regra geral para `.env.production`. `.dockerignore:5–11` exclui `.env.*` do contexto Docker. O workflow usa credenciais estáticas de teste em texto claro para banco e JWT (linhas 19–45); são valores de homologação descartável, não secrets de produção, mas indicam que a configuração CI não usa secrets de Actions para esse fixture. |
| Migrations em deploy | **PARCIAL** | `docker-compose.prod.yml` não executa Alembic no comando de inicialização. O README manda rodar `alembic upgrade head` manualmente antes do restart de API (README.md:57–67). O script de staging executa `upgrade head` somente contra o banco isolado configurado no ambiente de staging (`scripts/staging/up.sh:54–66`). Um runbook legado de servidor próprio descreve migration manual durante atualização. Não há gate automático que impeça alguém de adicionar migration ao pipeline futuro. |
| Serviços systemd na Hostinger | **NÃO VERIFICADO** | O README registra units `deepfarms-*` em outro processo de deploy nativo, mas não comprova que existam na Hostinger. O registro histórico do Hostinger descreve containers em Compose. |
| Separação build/execução | **PARCIAL** | Web e Agro usam estágios separados para dependências, build e execução. API é buildada em estágio único. Não há pipeline que produza e publique artefatos antes da execução em produção; o procedimento raiz documenta build na máquina de produção para frontends (README.md:69–90). |

## 4. Situação da Hostinger

**Estado desta execução: NÃO VERIFICADO diretamente.** O repositório não informa endpoint SSH/usuário específico da Hostinger. O README contém um endereço SSH para uma instância EC2 AWS, que não foi usado porque não identifica a VPS solicitada (`README.md:18–23`).

Há uma fotografia histórica próxima, registrada no relatório `docs/implementation/reports/DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md`, datada de 31/10/2026:

| Verificação pedida | Resultado disponível | Classificação atual |
|---|---|---|
| Diretório `/opt/deepfarms/farm` | Relatório histórico informa esse caminho como diretório do projeto e cita o Compose efetivo `/opt/deepfarms/farm/docker-compose.hostinger.yml` (01C:3–5, 22–25). Diretório não inspecionado diretamente agora. | **PARCIAL — evidência histórica** |
| Branch e commit implantados | Não constam na fotografia citada. | **NÃO VERIFICADO** |
| Containers | Operador informou nove containers em execução no instante da coleta de 31/10: Web, API, três workers, Agro, Campo, PostgreSQL e Redis (01C:22–26). | **PARCIAL — snapshot informado, não revalidado** |
| Compose usado e conteúdo resolvido | Nome do arquivo efetivo informado, mas conteúdo integral e parâmetros resolvidos não foram examinados (01C:22–25). | **PARCIAL — nome histórico; conteúdo não verificado** |
| Scripts de atualização | Não há inventário histórico suficiente. | **NÃO VERIFICADO** |
| Units systemd associadas | Não há evidência Hostinger suficiente; documentação de `systemd` refere-se a outro fluxo/servidor. | **NÃO VERIFICADO** |
| Crontabs, webhooks ou agentes CI/CD | Não há evidência coletada. | **NÃO VERIFICADO** |
| Healthchecks atuais | O relatório anterior registra PostgreSQL saudável na coleta, mas não fornece healthchecks dos demais serviços nem estado atual. | **PARCIAL — PostgreSQL no snapshot; demais não verificados** |
| Volumes, uploads e política de backup | A fotografia de containers não registra mounts, volumes ou backups. | **NÃO VERIFICADO** |

O registro histórico não é suficiente para afirmar que a VPS continua no mesmo commit ou configuração. Não foram executados comandos remotos nesta etapa.

## 5. Lacunas e riscos principais

1. **Fonte operacional divergente:** o README do checkout descreve uma produção AWS/native `systemd`, mas o Hostinger histórico usa `docker-compose.hostinger.yml`. Automatizar com `docker-compose.prod.yml` sem comparar o Compose efetivo pode recriar ou substituir serviços errados.
2. **Serviços ausentes no Compose local de produção:** Campo, Agro, PostgreSQL e Redis não estão definidos nele. A composição real deve ser confirmada antes de um pipeline selecionar serviços ou presumir dependências.
3. **Persistência não demonstrada:** não há volume de banco/cache nem bind mount de arquivos persistentes no Compose local. Um `down -v` no staging remove dados de propósito (`scripts/staging/down.sh:17–24`); esse comando deve ser proibido no procedimento de produção.
4. **Tag mutável `pilot`:** não permite identificar inequivocamente qual imagem foi promovida ou restaurar por versão reproduzível.
5. **Sem verificação de saúde integrada:** o Compose prod não declara healthchecks nem condição saudável antes de considerar sucesso. Smoke checks manuais são insuficientes para liberar automaticamente a próxima etapa.
6. **Build concorreria com Tara:** build de API/Web/Agro na KVM consome CPU, RAM, disco e I/O. A análise preliminar de capacidade KVM 4 no relatório `DEEPFARMS-HOSTINGER-01-AUDITORIA-CAPACIDADE-KVM4.md:9–17` recomenda build fora da VPS e estima margem limitada; são estimativas documentais, não medição atual.
7. **Cobertura de testes CI limitada:** o único workflow cobre um conjunto específico de homologação da API. Não há evidência de teste/build de Web, Campo, Agro ou todos os workers antes de produção.
8. **Proteção incompleta do nome de ambiente:** `.env.production` é intencionalmente mantido fora do versionamento segundo o README, mas a regra atual do `.gitignore` não o exclui explicitamente. A configuração de produção na VPS e seus modos de arquivo continuam não verificados.
9. **Rollback da aplicação não resolve incompatibilidade de schema:** documentação legada alerta que restaurar tag não reverte banco. A futura automação não deve rodar migration nem tentar rollback do banco automaticamente.

## 6. Comparação das opções de build

| Critério | A. Build na VPS | B. Build em GitHub Actions e pull pela VPS |
|---|---|---|
| Segurança | Simples de configurar, mas exige checkout/toolchain/dependências de build na produção e dá à rotina de deploy acesso ao contexto-fonte. | Pipeline separa credencial de publicação e credencial de pull; token de registry somente leitura na VPS. Requer proteger secrets do Actions e restringir chave/usuário SSH. |
| Recursos da VPS | Builds Python/Next.js competem com API, banco, workers e Tara por CPU, RAM, disco e I/O; risco de pressão durante deploy. | VPS apenas faz pull e troca containers, reduzindo impacto de CPU/RAM e espaço temporário. |
| Tempo de deploy | Pode ser mais lento por dependências e compilação no host; varia com cache. | Builds podem ocorrer em paralelo e ser cacheados no runner; VPS baixa layers alteradas. Primeiro build/pull pode ser maior. |
| Complexidade | Menos infraestrutura externa inicialmente; scripts e ambiente local precisam ser idênticos e reproduzíveis. | Acrescenta registry, workflow, tags/digests, política de limpeza e credencial read-only. Mais peças, maior rastreabilidade e separação. |
| Custos | Sem custo de registry/runner externo, mas consome capacidade da KVM compartilhada e pode reduzir disponibilidade de Tara/serviços. | Pode haver consumo de minutos/storage/egress conforme plano e registry escolhido. GHCR/Actions e quotas devem ser conferidos na conta antes da implementação; não se assume custo zero nem preço fixo. |
| Adequação a KVM 4 + Tara | **Baixa** para builds completos frequentes. | **Preferida**, desde que o custo/limites do plano e o espaço para imagens sejam medidos. |

**Recomendação:** opção B. Fixar cada imagem por SHA do commit e, idealmente, digest; evitar `latest` e `pilot` para releases. Usar GHCR privado ou registry equivalente com autenticação do host de pull restrita a leitura. Não conceder ao servidor credencial de publicação.

## 7. Arquitetura mínima recomendada

1. Confirmar com leitura na VPS o Compose efetivo, projeto Compose, nomes dos serviços, tags atuais, volumes/bind mounts, diretórios de uploads, healthchecks, espaço livre, backup e mecanismo atual de restart. Comparar com `docker-compose.prod.yml`; manter a configuração da VPS como referência até uma decisão explícita de convergência.
2. Criar workflow de CI para PR e push aprovado à `main`: instalar dependências travadas e executar testes relevantes da API/workers e builds de Web/Campo/Agro conforme arquivos alterados. Falha bloqueia publicação/deploy. A cobertura de testes de cada serviço deve ser acordada.
3. Depois de CI verde, construir imagens para arquitetura da VPS em runners GitHub Actions e publicar somente imagens alteradas com tag imutável do commit e registro dos digests. Conservar digest imediatamente anterior por serviço.
4. Disparar deploy somente para `main`, com concorrência serial por ambiente (`cancel-in-progress: false` ou equivalente). Usar GitHub Environment `production` e aprovação manual inicial, removível apenas após o processo provar estabilidade.
5. Autenticar à VPS com usuário técnico separado e chave SSH exclusiva, sem login root. Restringir a chave a um script allowlistado de deploy e aos comandos necessários de Docker Compose; não dar acesso irrestrito a shell. No host, manter token do registry somente leitura com permissões de arquivo restritas. Proteger secrets em Environment, nunca imprimir env ou saída de `docker compose config` que expanda segredos.
6. O script compara a versão atualmente ativa com o manifesto pretendido; se digest e configuração não mudaram, não reinicia o serviço. Faz `pull` apenas das imagens necessárias e atualiza seletivamente os serviços afetados com `docker compose up -d --no-deps <serviços>`, sem `down`, sem `--volumes` e sem recriar banco/cache.
7. Confirmar healthchecks reais de cada app e executar smoke checks pós-atualização por endpoint local. Se falhar ou exceder timeout, reaplicar os digests anteriores da aplicação e verificar saúde. Registrar deployment SHA, digests, resultado e logs resumidos no GitHub Actions e no host.
8. Nenhuma migration automática. Se migration for necessária, abrir etapa separada com revisão/aprovação e procedimento próprio de backup, compatibilidade e execução autorizada. Rollback automatizado limita-se às imagens/código; não reverte banco.
9. Documentar deploy manual de emergência: identificar release/digest anterior, autenticar ao host, aplicar somente o manifesto aprovado, validar saúde, registrar a operação. Não usar `git reset --hard`, `docker system prune` nem comandos que removam volumes.
10. Isolar Tara e DeepFarms em projetos Compose, redes, nomes de recursos, volumes e limites independentes. Definir janelas/limites de pull, armazenamento e CPU; não usar comandos globais de limpeza nem operações que afetem containers de outros projetos.

## 8. Estimativa de esforço

Estimativa preliminar, sujeita à auditoria da VPS e à escolha de registry:

| Fase | Estimativa |
|---|---:|
| Reconciliação de Compose, volumes, uploads, healthchecks e serviços na Hostinger | 0,5–1 dia |
| Fechar imagens e CI para testes/build, publicação SHA/digest e permissões mínimas | 1–1,5 dia |
| Script remoto restrito, atualização seletiva, healthcheck e rollback de aplicação | 1 dia |
| Homologação do deploy, falha simulada, preservação de volumes, documentação de emergência | 0,5–1 dia |
| **Total inicial** | **3–4,5 dias de engenharia** |

Não inclui investigação/correção de divergências grandes no Compose Hostinger, cobertura de testes ausente, alterações de plano/registry nem ensaio de backup/restore.

## 9. Plano objetivo de implementação futura

1. Solicitar/usar procedimento autorizado de acesso read-only à VPS para coletar o inventário pendente desta auditoria.
2. Revisar o Compose Hostinger completo e identificar cada serviço, volume e arquivo persistente; confirmar owner/permissões dos env files sem exibir seus conteúdos.
3. Escolher registry e confirmar quotas/custo; criar usuário/token de pull read-only e credenciais GitHub Environment.
4. Definir contratos de testes e mapear paths do monorepo para construir/testar componentes adequados.
5. Preparar release manifest versionado por SHA/digest e script allowlistado com preflight, seleção de serviços, healthcheck, logs e rollback da aplicação.
6. Exercitar em homologação: no-op sem restart, atualização parcial, atualização conjunta, healthcheck falho, rollback de imagem, volumes preservados e falha de registry/SSH.
7. Ativar deploy de produção com aprovação manual inicial, concorrência serial e migrations fora do pipeline.
8. Após ciclos monitorados, avaliar retirada da aprovação manual sem retirar branch protection, checks obrigatórios ou trilha de auditoria.

## 10. Pendências para confirmação na VPS

- Branch, SHA e estado de alterações locais em `/opt/deepfarms/farm`.
- Conteúdo e configuração resolvida de `/opt/deepfarms/farm/docker-compose.hostinger.yml`.
- Nomes dos serviços atuais, incluindo os nove containers mencionados no snapshot de 31/10/2026.
- Imagens/tags/digests em execução e se algum agente/webhook de atualização já opera.
- Volumes nomeados, bind mounts, diretório de uploads/storage, configuração e rotina de backup.
- Healthchecks/health status e endpoints de aplicação efetivamente servidos.
- Scripts, crontabs, units systemd, timers e credenciais de deploy configurados.
- Arquivos de ambiente: existência, proprietário e permissões, sem ler/imprimir valores.
- Espaço de disco e limites de recursos para coexistência com Tara e cache de imagens.
- Política efetiva de migrations e caminho de emergência/rollback já usado pelo operador.

## 11. Veredicto final

**NO-GO para habilitar deploy automático da produção agora.** O checkout não implementa CD. O único CI é de homologação parcial. O Compose local de produção é incompleto para os serviços conhecidos, usa tags mutáveis e não comprova persistência ou healthchecks. A Hostinger efetiva foi descrita em um snapshot informado pelo operador de 31/10/2026, mas o Compose integral, a versão implantada e os mecanismos de atualização não foram inspecionados nesta execução.

**GO para iniciar a implementação planejada após** reconciliar a configuração real da VPS, volumes/uploads, rollback e limites de Tara; então usar build externo e publicação de imagens imutáveis, deploy serial por SSH restrito, sem migrations automáticas e com healthchecks de produção.

### Referências principais

- `.github/workflows/agro-admin-01b2d-postgres-homologacao.yml`
- `docker-compose.prod.yml`, `docker-compose.yml`
- `Dockerfile.backend`, `Dockerfile.web`, `Dockerfile.agro`
- `infrastructure/staging/docker-compose.agro-staging.yml`
- `scripts/staging/up.sh`, `scripts/staging/down.sh`
- `README.md` (checkout com mudanças locais preexistentes)
- `docs/runbooks/deploy-les-svrbo-ap01.md`
- `docs/implementation/reports/DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md` (registro informado pelo operador; fotografia de 31/10/2026)
- `docs/implementation/reports/DEEPFARMS-HOSTINGER-01-AUDITORIA-CAPACIDADE-KVM4.md` (avaliação documental, não medição atual da VPS)
