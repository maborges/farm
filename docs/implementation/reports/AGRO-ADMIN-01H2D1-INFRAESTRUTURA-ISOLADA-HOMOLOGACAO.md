# AGRO-ADMIN-01H2D1 — Preparação da Infraestrutura Isolada de Homologação

**Modalidade:** diagnóstico operacional e preparação controlada
**Resultado:** provisionamento tecnicamente viável em diretório de usuário se forem disponibilizados binários de servidor; **NO-GO para provisionar agora**

## 1. Inventário do host

Diagnóstico feito em 2026-10-25 por leitura do sistema, pacotes instalados, `/proc/net`, permissões e ferramentas locais. Não houve conexão a PostgreSQL/Redis, consulta a dados comerciais ou alteração de serviço.

| Item | Evidência | Avaliação |
|---|---|---|
| SO/kernel | Ubuntu 22.04.5 LTS (Jammy), kernel `6.18.54.1-microsoft-standard-WSL2`, x86_64 | Ambiente é uma distribuição WSL2, não host Linux bare-metal. |
| Usuário/permissões | UID 1000, grupos `borgus` e `nogroup`; não é root. `/var/lib` e `/opt/lampp/var` não são graváveis; `/opt/lampp/var/mysql` existe mas não é gravável. `/tmp` é gravável. | Não há permissão demonstrada para instalar pacotes ou criar clusters nas áreas de sistema. Não reutilizar o diretório MySQL do XAMPP. |
| PostgreSQL | `/usr/bin/psql` 16.14; pacotes client 14.22 e 16.14 instalados. `postgres`, `initdb`, `pg_ctl`, `pg_config` e `pg_lsclusters` não encontrados; pacotes server 14/16 não instalados. | Existe cliente, não há evidência de servidor ou utilitários de cluster no PATH. |
| Clusters/dados PostgreSQL | `/var/lib/postgresql`, `/run/postgresql` e `/var/log/postgresql` ausentes; `pg_lsclusters` indisponível. | Nenhum cluster PostgreSQL padrão visível. Isso não exclui clusters em caminhos customizados/fora do namespace WSL. |
| Redis | `redis-server` e `redis-cli` ausentes do PATH; pacotes `redis-server`/`redis-tools` não instalados. | Não é possível provisionar ou verificar Redis diretamente no estado atual. |
| Portas | `lsof` não mostrou listeners em TCP 5432, 5433, 6379 ou 6380 no momento da coleta; `/proc/net/tcp{,6}` não listou listeners. `ss -ltn` falhou por restrição de netlink. | Sem conflito visível no namespace WSL nesta coleta; não é garantia para o host Windows/outro namespace e deve ser rechecado antes de qualquer start. |
| Diretórios | Os diretórios-alvo verificados sob `/tmp` (`deepfarms-agro-hml-2026-10-25`, `deepfarms-agro-hml`, `agro-hml-pg`, `agro-hml-redis`) não existem. `/tmp` está em filesystem com cerca de 903 GB livres. `/opt/lampp/var` contém diretórios `mysql`, `perl`, `proftpd`, `log`, `run`. | Caminho temporário exclusivo é possível, sujeito a escolha de ID e preflight de inexistência imediatamente antes do provisionamento. Não usar `/opt/lampp/var`. |
| Recursos | 8 CPUs visíveis; memória 7,6 GiB, 4,1 GiB disponíveis na coleta; swap 2 GiB, aproximadamente 970 MiB livres; filesystem de 1.007 GiB, aproximadamente 903 GiB livres. | Recursos suficientes para prova local pequena, com limites conservadores; os valores variam e precisam ser rechecados. |

### Interferência com recursos existentes

Relatórios anteriores identificam `services/api/.env.local` como apontando ao PostgreSQL compartilhado no host/rede `192.168.0.3`, database `farms`. Esse destino é proibido. O relatório 01D registrou, em auditoria passada, só `farms` e `postgres` como databases visíveis e ausência de privilégio `CREATEDB`; isso não foi revalidado agora. O host atual ter `psql` não significa que tenha servidor local. Nenhum valor de credencial comercial deve ser usado ou copiado.

As portas candidatas parecem livres apenas dentro da namespace WSL observada. Não se conectou a elas. A checagem deve ser repetida com `lsof` e `/proc/net` imediatamente antes de iniciar; se houver listener, abortar e escolher outro ID/ambiente após revisão, sem parar o processo encontrado.

## 2. Estratégia PostgreSQL

### Caminho preferido quando houver binários aprovados

Executar um cluster PostgreSQL **não gerenciado pelo serviço de sistema**, em diretório novo e pertencente ao usuário do laboratório, com `initdb`/`pg_ctl` apontando explicitamente para esse diretório. O cluster deve ser isolado de qualquer cluster padrão e iniciar apenas sob autorização manual. Usar `/tmp/deepfarms-agro-hml-<id>/postgres/data`, socket/log/config sob a mesma raiz e bind `127.0.0.1:5433`.

O usuário de SO atual pode gravar em `/tmp`, então não é obrigatório escrever em `/var/lib` se binários compatíveis forem disponibilizados fora do sistema. Eles não existem no estado inspecionado. Instalar pacotes nesta WSL pode exigir root e scripts de pacote podem criar/iniciar cluster padrão; **não** usar uma instalação genérica de pacote sem plano aprovado para impedir auto-start/cluster default e sem confirmação de permissão. Não foi executada instalação.

Configuração de segurança do cluster:

- `listen_addresses='127.0.0.1'`, porta 5433 e socket Unix exclusivo na raiz do laboratório;
- autenticação SCRAM local/rede; role administrativo de laboratório e role de aplicação separados;
- banco com nome `agro_hml_<id>`, encoding UTF-8, sem dados comerciais;
- logs, PID, config e data sob o diretório dedicado, todos com permissões `0700`/`0600`;
- limites de memória/conexões pequenos e explícitos, ajustados à memória disponível no momento;
- nenhuma conexão ao database compartilhado, RDS ou hostname externo;
- nenhuma cópia de `.env.local`, `.env.production`, roles, extensões/segredos comerciais.

O cluster vazio se destina à **prova isolada do DDL baseline**, por revisão explicitamente autorizada. Essa prova não libera migrations até o head nem substitui a análise do grafo da 01H2C2.

### Alternativa se binários/controle local não forem disponibilizados

Usar uma VM ou distribuição WSL2 separada, dedicada ao laboratório, com PostgreSQL e Redis nela e o processo de aplicação no mesmo ambiente. Limitar serviços a loopback interno e expor somente portas necessárias por encaminhamento controlado, após revisão de firewall. Não conectar essa VM à rede do banco comercial. Isso exige provisionamento/autorização do ambiente separado, não foi criado nesta fase e também não deve usar Docker.

Não se recomenda compartilhar a instância PostgreSQL do host em uma porta diferente: porta diferente não é isolamento lógico nem impede acesso ao database `farms`.

## 3. Estratégia Redis

Quando um binário Redis aprovado estiver disponível, executar daemon dedicado em `/tmp/deepfarms-agro-hml-<id>/redis`, porta 6380, `bind 127.0.0.1`, protected mode, ACL exclusiva e diretório/PID/log exclusivos. Não reutilizar database lógico de um Redis comercial na porta 6379. Desabilitar replicação e clustering; por ser laboratório descartável, a política de persistência deve ser declarada (recomendado sem persistência ou com RDB/AOF exclusivamente no diretório do ID).

Gerar senha aleatória sintética em arquivo `0600` fora do Git e configurar usuário de ACL exclusivo; não colocar segredo em argv, histórico, relatório ou logs. Verificar identidade com `INFO server`/`ACL WHOAMI` via conexão somente a `127.0.0.1:6380` usando autenticação carregada de arquivo protegido. O `redis-cli` não está instalado, então essa prova não pode ser feita agora.

## 4. Instruções de provisionamento preparadas (não executadas)

O provisionamento deve ser uma sequência fail-closed, executada manualmente somente após autorização específica:

1. **Aprovação:** registrar ID do laboratório, operador, período, revisão alvo (`baseline_deepfarms_v1` somente para eventual prova DDL), limites de recursos e autorização para criar/iniciar os processos. `agro_labctl.py migrate` continua bloqueado.
2. **Preflight de binários/permissões:** confirmar paths absolutos e versões de `initdb`, `pg_ctl`, `postgres`, `redis-server` e `redis-cli`; confirmar acesso de execução aos binários e escrita em `/tmp`; validar dono/permissões. Se faltar qualquer binário, abortar; não executar package manager.
3. **ID e raiz:** escolher ID aleatório não existente e resolver uma raiz absoluta sob `/tmp/deepfarms-agro-hml-<id>`. Exigir que a raiz e todos os subdiretórios não existam. Usar `umask 077`; criar raiz com modo `0700`. Se existir qualquer path, abortar; nunca reutilizar nem limpar automaticamente.
4. **Portas:** repetir `lsof -nP -iTCP:<porta> -sTCP:LISTEN` e leitura de `/proc/net/tcp{,6}` para 5433 e 6380 (e portas de app). Listener encontrado significa abortar, sem sinalizar/parar o PID.
5. **Credenciais:** gerar senhas e chaves aleatórias por CSPRNG em arquivos da raiz com modo `0600`; nenhuma vem de variáveis/configs existentes. Criar manifesto com ID, paths, portas e hashes de identidade, sem valores de senha.
6. **PostgreSQL:** após a autorização, executar `initdb` pelo path absoluto sobre o `PGDATA` novo, com auth SCRAM e role inicial exclusivo; escrever configuração exclusiva para `127.0.0.1:5433`, socket/log/PID na raiz. Validar `pg_ctl -D <PGDATA> status`/PID antes de start e nunca chamar `service postgresql`, `systemctl start postgresql` ou usar cluster padrão.
7. **Redis:** escrever config/ACL dentro da raiz e iniciar `redis-server` passando o arquivo de config exclusivo. Não executar `service redis-server` ou `systemctl start redis-server`.
8. **Identidade:** após start aprovado, testar apenas endpoints loopback dedicados. Confirmar com conexão PostgreSQL `current_database()`, `current_user`, `inet_server_addr()`, `inet_server_port()`, `version()` e `SHOW data_directory`; confirmar Redis user/server e `INFO server`. Recusar hostname, porta, database, diretório ou usuário divergente. Nunca imprimir DSN/password.
9. **Isolamento de rede:** garantir que os serviços aceitam somente loopback dentro da WSL/VM e que o Windows/host não esteja encaminhando essas portas publicamente. Não abrir firewall nem adicionar portproxy nesta fase.
10. **Banco novo:** só depois da identidade confirmada, criar o database descartável e role de aplicação próprios; provar que `farms` compartilhado não é acessível por esse role. Revalidar a revisão DDL específica e autorização antes de qualquer migration baseline. Sem GO formal, manter a instância vazia.

Estes comandos são um roteiro, não um script autorizado a modificar o host. Não existe garantia de que os binários poderão ser obtidos sem mudança sistêmica; essa disponibilidade é pré-requisito, não justificativa para instalar agora.

## 5. Pré-requisitos

- Autorização explícita para provisionar e iniciar instâncias locais descartáveis.
- Binários servidor PostgreSQL e Redis aprovados, com paths/versões compatíveis; hoje ausentes.
- Decisão operacional sobre disponibilizar os binários em área de usuário ou usar WSL/VM dedicado; o usuário atual não tem escrita nas áreas padrão do sistema e não é root.
- Rechecagem de portas e recursos na hora da execução.
- PostgreSQL dedicado em loopback e role/database próprios, sem qualquer grant ao banco `farms` compartilhado.
- Redis exclusivo em loopback, ACL própria e identidade verificável.
- Diretório novo com ID único, sem uploads ou segredos de operação comercial.
- Gate de isolamento aplicado às URLs de API e frontends antes de iniciar FastAPI/Next.js.
- Aprovação separada para a prova baseline em PostgreSQL vazio; nenhuma autorização implícita para alcançar head Alembic.

## 6. Procedimento de prova PostgreSQL (futuro, não executado)

Em um database descartável criado no cluster exclusivo:

1. Reconfirmar identidade, role, diretório de dados, bind/porta, permissões e vazio de `pg_namespace`, `pg_class`, sequences e tabela `alembic_version`. Se não estiver vazio, abortar e escolher outra instância nova.
2. Registrar `version()` e extensões presentes; comparar com requisitos do DDL sem tentar instalar extensões automaticamente.
3. Depois de autorização específica, aplicar **somente** o DDL da baseline aprovada (`baseline_deepfarms_v1`), sem `upgrade head(s)`, `stamp` ou caminho histórico. Fazer snapshot/log da execução, sem credenciais.
4. Confirmar que `farms.alembic_version` aponta somente à revisão executada.
5. Comparar catálogo PostgreSQL a inventário ORM/contrato: tabelas e colunas; defaults/nullability; UNIQUE/CHECK; 892 FKs conforme revisão do inventário atual; índices; 34 ENUMs e labels; 32 sequences requeridas/ownership; RLS enabled/forced; 188 policies do snapshot (com atualização de versão); funções/triggers.
6. Provar com papéis de aplicação sintéticos RLS para tenant A e B, leitura/escrita permitida e negação cruzada. Testar triggers e constraints com fixtures sintéticas, dentro de transações reversíveis.
7. Abrir session e fazer leitura/escrita ORM mínima usando modelos de autenticação/tenant e dependências do Agro; remover apenas dados de teste identificados ou descartar o database inteiro.
8. Registrar diffs e evidências redigidas. Qualquer divergência interrompe a prova; não criar uma migration corretiva automaticamente.

Essa prova mede a criação da baseline e comportamento no PostgreSQL. Não resolve nem libera o caminho Alembic da baseline ao head atual, que continua NO-GO pelo histórico paralelo.

## 7. Inicialização/encerramento seguros

Não usar gerenciadores globais (`systemctl`, `service`, `pkill`) para laboratório. O futuro controlador deve salvar PID e comando/arquivo de configuração esperados dentro da raiz exclusiva.

- PostgreSQL: `pg_ctl -D <PGDATA-exato> status|stop -m fast -w`; só aceitar o processo se `postmaster.pid` apontar para processo cujo command line contém o mesmo `PGDATA`.
- Redis: parar apenas o PID declarado pelo config exclusivo, depois de conferir `/proc/<pid>/cmdline` e path do config. Preferir shutdown autenticado sem expor password em argv; se a identidade divergir, abortar e não enviar sinal.
- App processes: encerramento somente por PID/manifesto do laboratório após validar command line e porta.
- Não apagar diretório se qualquer PID estiver ativo ou se a raiz resolvida não tiver o prefixo/ID e manifesto esperado.

## 8. Procedimento de descarte (futuro, não executado)

1. Registrar evidências necessárias com segredos e payloads removidos.
2. Parar FastAPI/Next.js pelos PIDs exatos registrados e validados.
3. Parar somente PostgreSQL/Redis com o `PGDATA` e config exatos da raiz deste ID; validar que portas não têm listener do processo e que o banco não está montado/usado por outro serviço.
4. Solicitar confirmação operacional de descarte para o ID provisionado. A aprovação deve identificar a raiz absoluta e database exclusivo.
5. Remover somente esse cluster/database, Redis e storage exclusivos; não remover `/opt/lampp/var/mysql`, `/var/lib/postgresql`, nem qualquer diretório compartilhado. Se ownership/path/manifesto divergirem, abortar.
6. Guardar relatório de descarte sem DSN, password ou tokens.

## 9. Critérios GO / NO-GO

**GO para provisionamento** exige binários servidor aprovados disponíveis, autorização explícita, paths novos, portas livres rechecadas, recursos suficientes, diretórios exclusivos e comprovação de que nenhum gerenciador/cluster existente será tocado. **GO para prova do baseline** exige adicionalmente banco vazio e dedicado, identidade confirmada, permissões restritas e autorização da revisão exata. **GO para iniciar a aplicação** exige a prova de schema aprovada e gate de isolamento dos processos.

**NO-GO atual:** PostgreSQL server/cluster e Redis não estão disponíveis no host examinado; o usuário não tem acesso de escrita às áreas de sistema; não existe prova de autorização para instalação/start; estado de portas deve ser rechecado pois `ss` foi bloqueado; clean install até head permanece bloqueado. A alocação em `/tmp` é apenas viabilidade de diretório, não substitui os binários nem o isolamento/autorizações.

Não foram instalados pacotes, iniciados/parados serviços, abertas conexões, executadas migrations, consultados dados comerciais ou alteradas configurações. Aguardar autorização para qualquer provisionamento.
