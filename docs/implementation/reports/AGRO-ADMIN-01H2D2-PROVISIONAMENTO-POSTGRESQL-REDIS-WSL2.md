# AGRO-ADMIN-01H2D2 — Provisionamento PostgreSQL e Redis no WSL2

**Fases concluídas:** A — diagnóstico e obtenção rootless dos binários; B — provisionamento e start isolados; gate de identidade executado.
**Veredicto atualizado:** **GO COM RESSALVAS para infraestrutura isolada**.
**Fases seguintes:** não iniciadas. O adendo ao final deste documento é o registro autoritativo da Fase B e substitui os estados “pendente/não provisionado” da fotografia inicial da Fase A.

## 1. Diagnóstico inicial

Relidos integralmente os relatórios AGRO-ADMIN-01H2D1, 01H2C e 01H2C2. O database compartilhado `farms` em `192.168.0.2` permaneceu fora do escopo. Nenhuma conexão PostgreSQL/Redis, consulta comercial, instalação, start/stop ou migration foi realizada.

| Verificação | Resultado desta coleta |
|---|---|
| SO/arquitetura | Ubuntu 22.04.5 LTS (Jammy), x86_64, kernel WSL2 `6.18.54.1-microsoft-standard-WSL2` |
| Permissões | Usuário UID 1000, sem root e sem grupos administrativos visíveis (`borgus`, `nogroup`). `/tmp` gravável; `/var/lib` e `/opt/lampp/var` não graváveis. |
| PostgreSQL client | `/usr/bin/psql`, versão 16.14; clients 14.22 e 16.14 constam instalados. |
| PostgreSQL Server 16 | `postgres`, `initdb`, `pg_ctl`, `pg_config` ausentes do PATH; pacote `postgresql-16` não instalado. |
| Redis | `redis-server` e `redis-cli` ausentes do PATH; `redis-server` e `redis-tools` não instalados. |
| Processos | `pgrep -x postgres` e `pgrep -x redis-server` não retornaram PIDs. Verificação limitada à namespace WSL e aos nomes de processo exatos. |
| Portas | `lsof` não retornou listeners em `5433` nem `6380`. O resultado é uma amostra local, não reserva de porta; revalidar imediatamente antes do start. |
| Memória/disco | 8 CPUs visíveis; 7,6 GiB de memória, aproximadamente 4,2 GiB disponíveis; swap 2 GiB; filesystem de `/tmp` com aproximadamente 903 GB disponíveis. Valores variam. |
| Diretórios | `/tmp` gravável. A coleta anterior documenta que os diretórios candidatos do laboratório não existiam. Não foram criados diretórios agora. |

## 2. Disponibilidade e método para os binários

`apt-cache policy` (somente leitura) encontrou candidatos nos índices configurados:

- PostgreSQL Server 16: `16.15-1.pgdg22.04+2`, repositório PostgreSQL PGDG para Jammy.
- Redis Server: `5:6.0.16-1ubuntu1.2`, repositórios Ubuntu Jammy updates/security.

Os pacotes foram baixados após autorização do usuário (“prossiga”) e aprovação do acesso à rede pelo sandbox. Não houve instalação via dpkg/APT, scripts de pacote ou alteração sistêmica.

### Método executado: download e extração rootless

Raiz criada exclusivamente para este lote: `/tmp/deepfarms-agro-hml-20261025-pkg-a0f4281d`. Os diretórios `packages`, `extracted` e `evidence` têm modo `0700`. A raiz não existia antes; não foi reutilizada.

Executado `apt-get download` (sem `install`) para PostgreSQL 16.15, Redis 6.0.16 e dependências runtime. A primeira tentativa no sandbox falhou por DNS restrito; após aprovação de rede, o download terminou. Os `.deb` vieram dos repositórios APT configurados. Para cada arquivo, o SHA-256 calculado coincidiu com o campo `SHA256` de `apt-cache show` para o mesmo pacote/versão/arquitetura. Não foi feita auditoria independente das fingerprints das chaves APT.

| Pacote | Versão | SHA-256 conferido contra metadado APT |
|---|---|---|
| `postgresql-16` | `16.15-1.pgdg22.04+2` | `7c9ef4472262145d08d7263e6ba0dededa5a58e1ec71e58627d973c40c9eb59f` |
| `redis-server` | `5:6.0.16-1ubuntu1.2` | `73b290ff8e6ba230f29841a5d7effe72bb4537766b9f109d4a4b1e620f57b93e` |
| `redis-tools` | `5:6.0.16-1ubuntu1.2` | `58f0080318ac7eafb6338bab5f91e82de507cacf9bfa48b82e0faf595f1a075b` |
| `libjemalloc2` | `5.2.1-4ubuntu1` | `144eaa64b9da0319760c407ebe330b46d9d03ef9952fc067d48221cc9832e45c` |
| `liblua5.1-0` | `5.1.5-8.1build4` | `a8309a74f42109dea7c79c6c8216f4252d9f0c9f1fc1bd329a4885f417df1eda` |
| `liblzf1` | `3.6-3` | `033339fa56064777899e6f76d4ca6cf93b76930f0ce6d955b81f9907fc2b9c8a` |
| `lua-bitop` | `1.0.2-5` | `b4e7d0626c426ffa93a46b2b2366e806835c503d5381c85bf72158adb1dcca38` |
| `lua-cjson` | `2.1.0+dfsg-2.1` | `56c1216c591a7ebd2f2954cc18118097c0c32fb9f745d2e18b8c492e0d46a2e4` |

Os oito `.deb` foram extraídos com `dpkg-deb -x` em `<raiz>/extracted`. Nenhum `dpkg -i`, post-install ou gerenciador global foi executado. `ldd` dos executáveis não mostrou dependências `not found`. `postgres --version`, `initdb --version`, `pg_ctl --version`, `redis-server --version` e `redis-cli --version` executaram sem iniciar servidor; resultados: PostgreSQL 16.15 e Redis 6.0.16. A closure necessária para inicializar cluster não foi testada com `initdb`, pois isso criaria PGDATA e pertence à etapa seguinte.

Os binários usam dependências de runtime do sistema já presentes, sem alteração delas. Se a criação futura do cluster depender de root, instalação global ou configuração de pacote, abortar e solicitar nova autorização.

## 3. Aprovações obtidas

* Download e extração rootless dos pacotes PostgreSQL/Redis e dependências: autorização explícita do usuário (“prossiga”) e aprovação de rede do sandbox.
* Instalação sistêmica, execução de post-install, criação de cluster/database/roles/ACL e start/stop: **não autorizados nesta etapa**; Fase B requer aprovação operacional separada.

## 4. Isolamento planejado (ainda não provisionado)

ID de preparação dos pacotes: `20261025-pkg-a0f4281d`. Esta é somente a raiz dos binários, não um cluster de homologação. Após aprovação futura, usar ID de laboratório novo, sem reaproveitar esta raiz como PGDATA:

- raiz exclusiva nova e inexistente: `/tmp/deepfarms-agro-hml-<id>`, modo `0700`;
- pacotes e extração atuais: `/tmp/deepfarms-agro-hml-20261025-pkg-a0f4281d/{packages,extracted}`, sem instalação no sistema;
- PostgreSQL 16: `<raiz>/postgres/data`, socket/log/PID/config próprios, bind `127.0.0.1`, porta `5433`, SCRAM, database `agro_hml_<id>`;
- roles exclusivos: role owner/administrativo de laboratório e role da aplicação com privilégios mínimos; credenciais geradas por CSPRNG em arquivos `0600`, fora do Git e sem impressão em logs;
- Redis: config/ACL/PID/log/dados sob `<raiz>/redis`, bind `127.0.0.1`, porta `6380`, ACL dedicada, sem réplica/cluster/integração externa;
- nenhuma permissão, URL ou credential para `192.168.0.2`, `farms`, RDS ou serviços comerciais;
- FastAPI e frontends não serão iniciados nesta fase.

Nenhum serviço existente deve ser parado, reconfigurado ou removido. Portas ocupadas, path existente, identidade divergente ou permissão inesperada significam abortar, sem correção automática.

## 5. Comandos read-only efetivamente executados

Diagnóstico: `uname -m`, leitura de `/etc/os-release`, `id`, `command -v`, `psql --version`, `pgrep -x`, `lsof` nas portas 5433/6380, `free -h`, `df -h /tmp`, `test -w`, `dpkg-query` e `apt-cache policy`. Obtenção: `apt-get download` para oito pacotes; integridade: SHA-256 local versus `apt-cache show`; extração: `dpkg-deb -x`; validação sem start: `ldd` e cinco comandos `--version`. Nenhum comando conectou a banco ou iniciou serviço.

## 6. Procedimento futuro de provisionamento

Não executado. Os binários foram disponibilizados, mas a aprovação operacional da Fase B continua pendente:

1. Obter uma autorização operacional explícita para provisionar/start com um ID e escopo definidos; aprovação de download, se concedida, **não** implica autorização para iniciar serviços.
2. Confirmar `id`, versões/hashes dos pacotes, dependências e ausência de necessidade de root/instalação global.
3. Rechecar `lsof` nas portas `5433`/`6380`, CPU/memória/disco e inexistência da raiz escolhida. Se existir qualquer destino, abortar; nunca apagar ou reutilizar.
4. Criar raiz nova com `umask 077` e modo `0700`; gerar manifesto sintético e segredos exclusivos em arquivos `0600`.
5. Executar `initdb` pelo binário absoluto, com `PGDATA` novo, SCRAM e arquivos/configuração limitados à raiz. Configurar `listen_addresses=127.0.0.1`, `port=5433`, socket privado e logs/PID próprios.
6. Configurar Redis via arquivo exclusivo, `bind 127.0.0.1`, `port 6380`, ACL própria, sem replica/cluster, logs/PID/diretório próprios.
7. Iniciar somente pelos controladores dos diretórios exatos (`pg_ctl -D <PGDATA>` e `redis-server <config>`); sem `systemctl`, `service`, `pkill` ou instalação de unidade global.
8. Verificar identidades localmente: PostgreSQL `current_database()`, `current_user`, `inet_server_addr()`, `inet_server_port()`, `version()`, `SHOW data_directory`; Redis `ACL WHOAMI`, versão e `INFO server`. Garantir que ambos correspondem ao manifesto/raiz e não aceitam conexão não-loopback.
9. Provar que role da aplicação só acessa o database descartável e não possui grants no database compartilhado. Se identidade/permissão divergir, parar o processo exato do laboratório ou abortar; não tentar acessar o destino suspeito.
10. Só então preparar env sintético e executar o gate `scripts/homologacao/agro_labctl.py` com manifesto coerente. O gate de aplicação não substitui confirmação independente da identidade dos serviços.

## 7. Prova PostgreSQL posterior

Após instâncias isoladas disponíveis, vazio e identidade demonstrados, e aprovação específica da prova:

1. Confirmar ausência de objetos/schema/version table preexistente e permissões adequadas no database `agro_hml_<id>`.
2. Registrar versão PG/role/database/diretório e estado vazio, omitindo DSNs/segredos.
3. Executar somente o DDL/revisão baseline explicitamente autorizada para o teste. Não executar `upgrade head`, `upgrade heads`, `stamp` ou migrations históricas; a aprovação não resolve o bloqueio do caminho Alembic até o head.
4. Validar `farms.alembic_version`, tabelas/colunas ORM, constraints, índices, FKs, ENUMs, sequences/ownership, RLS/policies, funções e triggers contra inventário revisionado.
5. Provar isolamento RLS com dois tenants sintéticos e operações CRUD ORM mínimas; nenhuma credencial ou dado comercial.
6. Registrar evidências redigidas. Divergências bloqueiam o teste seguinte; não aplicar migrations corretivas.

## 8. Start, stop e descarte seguros

Não preparados como scripts executáveis nesta fase. O controlador futuro deverá recusar root paths não inéditos, validar manifesto e PIDs, e nunca atuar por nome global de serviço.

- PostgreSQL: status/stop apenas por `pg_ctl -D` apontando para o PGDATA exato e PID confirmado pelo `postmaster.pid` e command line.
- Redis: shutdown autenticado ou sinal somente ao PID cujo `/proc/<pid>/cmdline` e config apontem à raiz do ID; se divergirem, não sinalizar.
- Descarte: confirmação operacional por ID, serviços já encerrados, portas liberadas pelo PID identificado, e caminho absoluto dentro de `/tmp/deepfarms-agro-hml-<id>` com manifesto esperado. Remover apenas essa raiz; nunca remover diretórios de sistema ou do XAMPP.

## 9. Bloqueios e próxima ação

- **Pré-requisito sistêmico:** binários PostgreSQL 16.15 e Redis 6.0.16 foram extraídos no ambiente privado; ainda não são pacotes instalados pelo sistema. Se a operação do cluster exigir root ou instalação sistêmica, solicitar nova autorização; não improvisar.
- **Bloqueio de provisionamento:** autorização para download/extrair não autoriza criar/start dos serviços; fase B exige aprovação operacional independente.
- **Bloqueio funcional:** a baseline segue sem aprovação PostgreSQL real e o caminho Alembic até head permanece NO-GO conforme 01H2C2.

**Próxima ação recomendada:** autorizar separadamente o provisionamento dos clusters/daemons em raiz nova, com identidade e portas confirmadas. Os binários já estão disponíveis em `/tmp/deepfarms-agro-hml-20261025-pkg-a0f4281d/extracted`; o processo deve permanecer pausado até autorização da Fase B.

## 10. Veredicto

**Registro original da Fase A (substituído pelo adendo da Fase B):** GO COM RESSALVAS para binários rootless; à época, provisionamento/start ainda aguardavam autorização.

---

## Adendo autoritativo — Fase B (2026-10-25)

### 1. Autorização e escopo executado

O usuário autorizou expressamente o provisionamento e start do laboratório local PostgreSQL 16.15 e Redis 6.0.16. Foi criada uma raiz inédita, sem reutilizar o diretório dos pacotes. Não foram instalados pacotes globalmente, usados `sudo`, `systemctl` ou `service`, nem alterados serviços preexistentes. Não houve conexão a `192.168.0.2`, RDS, provedores comerciais ou outros serviços externos. Não foram iniciados FastAPI/Next.js; não foram executados migrations, `stamp`, DDL DeepFarms, nem testes E2E.

### 2. Recursos provisionados e identidade

| Serviço | Identidade comprovada | Isolamento |
|---|---|---|
| PostgreSQL | 16.15; PID `1447173`; listener `127.0.0.1:5433`; database `agro_hml_dbdcc24872aa`; admin `agro_hml_owner_dbdcc24872aa`; role de aplicação `agro_hml_dbdcc24872aa` | Binário extraído em `/tmp/deepfarms-agro-hml-20261025-pkg-a0f4281d`; PGDATA `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data`; config, HBA, socket e logs próprios; autenticação SCRAM. A role de aplicação autenticou no database exclusivo e não tem atributos superuser, createdb, createrole, replication ou bypassrls. |
| Redis | 6.0.16; PID `1455955`; run ID `c94fe026e2fd78fded04c3363ccf0ba37b003849`; listener `127.0.0.1:6380`; ACL autenticada como `default`; `PING=PONG` | Binário extraído no mesmo diretório de pacotes; diretório `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/redis/data`; ACL e config exclusivos; `appendonly=no`; sem replicação. O marcador sintético do ID do laboratório foi lido e conferido. |

ID do laboratório: **`dbdcc24872aa2992`**. Raiz exclusiva: `/tmp/deepfarms-agro-hml-dbdcc24872aa2992`. Raiz dos binários: `/tmp/deepfarms-agro-hml-20261025-pkg-a0f4281d`.

O database foi inicializado e criado apenas para infraestrutura. A inspeção registrou zero tabelas/objetos de usuário, ausência do schema `farms` e de `farms.alembic_version`; nenhum DDL do produto ou migration foi aplicado. Isso não equivale à validação do baseline.

### 3. Permissões e segredos

A raiz do laboratório, config, PGDATA e diretório de dados Redis têm modo `0700`, pertencem ao usuário `borgus`. Configuração, ACL, envs sintéticos e arquivos de senha conferidos têm modo `0600`. Credenciais e chaves foram geradas para teste e permanecem somente sob a raiz privada em `/tmp`; este relatório e o manifesto não contêm os valores. Nenhum `.env.local` ou `.env.production` foi copiado.

O manifesto redigido está em `/tmp/deepfarms-agro-hml-dbdcc24872aa2992/config/manifest.json`; registra estado, versões, portas, PIDs, nomes de database/roles, hash dos segredos e resultados do gate, sem os segredos em claro.

### 4. Comandos e operações efetivamente realizados

- `agro_labctl.py prepare --root ...` para gerar config sintética e raiz inédita.
- `initdb` do binário PostgreSQL 16.15 para o PGDATA exclusivo, com SCRAM e checksums.
- `pg_ctl` no PGDATA/config do laboratório; status confirmou PID `1447173` e linha de comando apontando para a raiz exclusiva.
- DDL de infraestrutura estritamente limitado a criar as duas roles sintéticas e o database descartável, atribuir owner e restringir `CONNECT` público. Nenhuma tabela/schema da aplicação foi criado.
- `redis-server` com config exclusiva, `bind 127.0.0.1`, ACL própria e porta `6380`.
- Inspeções `lsof` confirmaram apenas listeners `127.0.0.1:5433` e `127.0.0.1:6380`, nos PIDs acima. O Redis também confirmou por protocolo versão, PID, run ID, ACL, bind, porta, diretório de dados, arquivo ACL e persistência desabilitada.
- A primeira execução do gate de identidade revelou que o PostgreSQL devolve loopback como `127.0.0.1/32`, enquanto o validador comparava somente a string literal `127.0.0.1`. O gate foi ajustado para normalizar o endereço e aceitar exclusivamente `127.0.0.1`/`127.0.0.1/32` ou `::1`/`::1/128`; endereços não loopback e máscaras mais amplas continuam rejeitados. Foram adicionados testes positivos e negativos.
- Durante a verificação Redis, a instância foi reiniciada somente pelo mecanismo autenticado de shutdown do próprio Redis. Como AOF/RDB estão desabilitados, o marcador sintético de identidade não persistiu e foi reposto após a reinicialização. Nenhum PID preexistente foi encerrado. Os scripts de teste usaram bibliotecas Lua e runtime dos pacotes extraídos via variáveis de processo, sem alteração global.

### 5. Resultado dos gates e verificações

- Gate de configuração existente: **PASS** — configuração isolada e ferramentas necessárias presentes.
- Gate de identidade existente: **PASS** — role e database PostgreSQL corresponderam ao env isolado, endereço/porta foram loopback/5433, e o marcador Redis autenticado correspondeu ao ID do laboratório.
- Identidade de processo: **PASS** — `pg_ctl status`, PID file/INFO Redis e listeners exclusivos correspondem aos processos iniciados para este laboratório.
- Bind: **PASS** — ambos os sockets TCP foram observados em loopback IPv4, sem listener em interface externa.
- Permissões: **PASS** — modos `0700` para raiz/dados e `0600` para arquivos sensíveis conferidos.
- PostgreSQL vazio para a aplicação: **PASS** — database exclusivo sem schema/tabelas da aplicação ou version table.
- Redis: **PASS** — autenticação ACL, `PING`, versão, identidade, config, marcador, modo sem replicação/persistência e teste de `cjson`.
- Teste unitário do controlador: **22 passed** (`services/api/.venv/bin/pytest scripts/homologacao/test_agro_labctl.py -q`).
- Ruff nos dois arquivos do controlador/gate: **PASS**.
- `git diff --check` no workspace todo reportou uma linha vazia no EOF em `services/api/core/routers/backoffice_sessions.py:170`, fora dos arquivos desta etapa e já alterado no workspace. Não foi editado para evitar tocar trabalho alheio. Ruff e os testes direcionados passaram.

O gate de configuração informa explicitamente que não comprova identidade nem aprovação Alembic; por isso a identidade foi verificada separadamente. O gate de identidade não aprova migrations.

### 6. Estado atual, operação e descarte

Os dois serviços permanecem **iniciados** conforme autorização. PIDs confirmados: PostgreSQL `1447173`; Redis `1455955`. O endpoint Redis é volátil; reinícios descartam o marcador e quaisquer dados não persistidos. Não iniciar APIs ou frontends até autorização separada e até o caminho de banco estar aprovado.

Para uma parada futura, identificar novamente os processos pela raiz/config/PGDATA e PID antes de agir; PostgreSQL deve ser parado somente por `pg_ctl -D /tmp/deepfarms-agro-hml-dbdcc24872aa2992/postgres/data stop`, e Redis por `SHUTDOWN` autenticado ao listener confirmado como laboratório. Não usar comandos globais por nome. Descarte da raiz só após aprovação, serviços parados, portas liberadas e confirmação do ID; não foi descartado nada nesta etapa.

### 7. Bloqueios, riscos e veredicto

- O clean install continua bloqueado pelo histórico/contrato Alembic conforme AGRO-ADMIN-01H2C2; o banco está vazio de aplicação e nenhuma migration foi executada.
- Ainda não houve prova PostgreSQL do baseline, teste RLS, autenticação da aplicação, concorrência de cotas, sessão/heartbeat, integração Backoffice/PWA ou E2E.
- O Redis não persiste dados por desenho do laboratório; a disponibilidade e os dados do teste cessam no restart.
- O log Redis pode registrar aviso do kernel sobre `vm.overcommit_memory`; nenhum sysctl global foi alterado. O aviso é risco operacional conhecido para tarefas de fork/persistência, não impede a identidade local atualmente testada.
- O ACL Redis usa usuário sintético local `default` com senha exclusiva; por ser laboratório de host único e sem dados comerciais, a exposição de rede continua limitada ao loopback. Não reutilizar esta ACL fora do laboratório.
- A prova de isolamento limita-se à configuração efetiva e aos listeners loopback observados neste host. Não constitui prova de clean install nem garantia sobre políticas externas ao WSL.

**Veredicto: GO COM RESSALVAS para a infraestrutura isolada PostgreSQL/Redis.** Os serviços reais estão ativos e suas identidades, permissões, loopback, funcionamento básico e gate foram comprovados. **NO-GO para migrations, baseline, FastAPI/Next.js e homologação E2E** até aprovação explícita e resolução dos bloqueios de clean install. Encerrado nesta fase; nenhuma próxima etapa foi iniciada.
