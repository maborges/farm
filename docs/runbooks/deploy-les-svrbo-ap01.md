# AgroSaaS - Runbook de Deploy no LES-SVRBO-AP01

Servidor:
- `LES-SVRBO-AP01`
- `Rocky Linux 9.8`
- `2 vCPUs`
- `4 GB RAM`
- `50 GB NVMe`
- IP público: `179.127.30.25`
- Portas públicas: `80` e `443`

Serviços já disponíveis no servidor:
- `Docker`
- `Nginx`
- `PostgreSQL`

Objetivo:
- subir a aplicação com o backend FastAPI, o frontend web Next.js, o frontend Campo PWA, o banco PostgreSQL e o proxy Nginx
- manter banco, Redis e aplicativos de aplicação sem exposição direta na internet
- deixar o passo a passo claro para quem está executando pela primeira vez

## 1. Mapa rápido do que roda em cada lugar

| Componente | Onde roda | Porta | Acesso externo |
|---|---|---:|---|
| Nginx | Servidor | 80 / 443 | Sim |
| Frontend Next.js | Servidor, localmente em `127.0.0.1` | 3000 | Não |
| Frontend Campo PWA | Servidor, localmente em `127.0.0.1` | 3002 | Não |
| Backend FastAPI | Servidor, localmente em `127.0.0.1` | 8000 | Não |
| PostgreSQL | Servidor, localmente em `127.0.0.1` | 5432 | Não |
| Redis | Docker no servidor, localmente em `127.0.0.1` | 6379 | Não |

## 2. Onde cada comando deve ser executado

Use esta legenda durante todo o procedimento:

- `No seu computador`: terminal local, de onde você abre o SSH
- `No servidor via SSH`: terminal aberto depois de conectar no `LES-SVRBO-AP01`
- `No servidor como root`: comandos com `sudo`
- `No servidor como usuário agrosaas`: comandos de aplicação
- `Dentro da pasta do projeto`: comandos executados na pasta do repositório

### Como mudar para o usuário `agrosaas`

Quando uma etapa disser `No servidor como usuário agrosaas`, não é necessário abrir outra conexão SSH. No terminal já conectado ao servidor, execute:

```bash
sudo -iu agrosaas
```

Confirme qual usuário está ativo:

```bash
whoami
```

O resultado esperado é:

```text
agrosaas
```

Para voltar ao usuário anterior, execute:

```bash
exit
```

Também é possível entrar diretamente pelo seu computador com `ssh agrosaas@179.127.30.25`, mas isso exige que uma senha ou chave SSH tenha sido configurada para o usuário. Para este procedimento, prefira `sudo -iu agrosaas`.

## 3. Sequência recomendada

1. Entrar no servidor por SSH.
2. Preparar o sistema operacional e criar o usuário da aplicação.
3. Garantir PostgreSQL, Nginx e Docker funcionando.
4. Subir Redis via Docker.
5. Baixar o código-fonte.
6. Criar os arquivos `.env.local`.
7. Instalar dependências do backend, do frontend web e do Campo PWA.
8. Rodar migrations do banco.
9. Build dos frontends.
10. Criar os serviços `systemd`.
11. Configurar o Nginx.
12. Testar os endpoints.

## 4. Acesso SSH

### Onde executar
- `No seu computador`

### Comando

```bash
ssh <usuario>@179.127.30.25
```

Se houver porta diferente da padrão `22`, adicione `-p <porta>`.

## 5. Preparar o servidor

### 5.1 Atualizar o sistema

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo dnf update -y
```

### 5.2 Instalar pacotes base

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo dnf install -y git curl wget tar unzip gcc gcc-c++ make openssl-devel libffi-devel zlib-devel bzip2-devel readline-devel sqlite-devel xz-devel firewalld
```

### 5.3 Habilitar serviços do sistema

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo systemctl enable --now firewalld
sudo systemctl enable --now nginx
sudo setsebool -P httpd_can_network_connect 1
```

Observação:
- `httpd_can_network_connect` é importante no Rocky Linux quando o Nginx faz proxy para serviços locais.
- O PostgreSQL será inicializado e habilitado separadamente na seção 9. Não tente iniciar o serviço antes de executar o `initdb`.

## 6. Criar o usuário da aplicação

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo useradd -m -s /bin/bash agrosaas
sudo passwd agrosaas
```

Se a empresa preferir usar outro usuário já existente, use esse mesmo usuário em todos os passos seguintes.

## 7. Criar a estrutura de diretórios

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo mkdir -p /opt/agrosaas
sudo mkdir -p /srv/agrosaas/uploads
sudo mkdir -p /var/log/agrosaas
sudo chown -R agrosaas:agrosaas /opt/agrosaas /srv/agrosaas /var/log/agrosaas
```

## 8. Instalar os runtimes da aplicação

O projeto precisa de:
- Python 3.12 para o backend
- Node.js 22 para o frontend
- `pnpm` para o workspace

### 8.1 Python 3.12 com `pyenv`

### Onde executar
- `No servidor como usuário agrosaas`

### Comandos

```bash
curl https://pyenv.run | bash
```

Depois, adicione as linhas abaixo ao final do arquivo `~/.bashrc` do usuário `agrosaas`:

```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Carregue o shell e instale o Python:

```bash
source ~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
pyenv --version
pyenv install 3.12.9
pyenv global 3.12.9
python --version
python -c "import bz2; print('bz2 OK')"
```

Se o Python já tiver sido instalado com o aviso `The Python bz2 extension was not compiled`, corrija assim:

### Onde executar primeiro
- `No servidor como root`

```bash
sudo dnf install -y bzip2-devel
```

### Onde executar depois
- `No servidor como usuário agrosaas`

```bash
sudo -iu agrosaas
source ~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
pyenv --version
pyenv install --force 3.12.9
pyenv global 3.12.9
python -c "import bz2; print('bz2 OK')"
```

O resultado esperado do último comando é `bz2 OK`.

Se aparecer `pyenv: command not found`, confirme primeiro que está como `agrosaas` usando `whoami` e execute novamente as três linhas de `export`/`eval` acima. A instalação deve estar em `/home/agrosaas/.pyenv`; não execute o `pyenv` como `root`.

### 8.2 Node.js 22 com `nvm`

### Onde executar
- `No servidor como usuário agrosaas`

### Comandos

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
node --version
```

### 8.3 Ativar `pnpm`

### Onde executar
- `No servidor como usuário agrosaas`

### Comando

```bash
corepack enable
pnpm --version
```

## 9. Banco PostgreSQL

O banco já está instalado no servidor. A recomendação é deixá-lo escutando apenas em `127.0.0.1`.
Use o banco do host, não o container do `docker-compose.yml` da raiz, porque no servidor já existe PostgreSQL instalado.

### 9.1 Identificar a instalação

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo dnf list installed | grep -E '^postgresql([0-9]+)?-server'
sudo systemctl list-unit-files | grep -E 'postgresql.*\.service'
```

O resultado define qual procedimento usar:

- Se aparecer `postgresql-server` e `postgresql.service`, use a seção 9.2.
- Se aparecer `postgresql16-server` e `postgresql-16.service`, por exemplo, use a seção 9.3, substituindo `16` pela versão exibida.

### 9.2 Inicializar o PostgreSQL padrão do Rocky Linux

### Onde executar
- `No servidor como root`

### Comandos

```bash
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
```

O comando `postgresql-setup --initdb` cria o cluster inicial em `/var/lib/pgsql/data`. Ele deve ser executado uma única vez. Se informar que o banco já está inicializado, não apague o diretório: verifique os logs conforme a seção 9.4.

### 9.3 Inicializar uma instalação PGDG versionada

Use esta alternativa somente se a seção 9.1 mostrar um serviço versionado. O exemplo abaixo usa PostgreSQL 16.

### Onde executar
- `No servidor como root`

### Comandos

```bash
sudo /usr/pgsql-16/bin/postgresql-16-setup initdb
sudo systemctl enable --now postgresql-16
sudo systemctl status postgresql-16 --no-pager
```

Substitua `16` pela versão instalada em todos os trechos do comando.

### 9.4 Se o serviço ainda não iniciar

### Onde executar
- `No servidor como root`

### Comandos

Para o pacote padrão do Rocky:

```bash
sudo systemctl status postgresql --no-pager -l
sudo journalctl -u postgresql -n 100 --no-pager
```

Para um pacote PGDG versionado, substitua o nome do serviço. Exemplo para a versão 16:

```bash
sudo systemctl status postgresql-16 --no-pager -l
sudo journalctl -u postgresql-16 -n 100 --no-pager
```

### 9.5 Criar o banco e o usuário

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo -u postgres psql
```

### Dentro do `psql`

```sql
CREATE USER agrosaas WITH PASSWORD 'TROQUE-ESTA-SENHA';
CREATE DATABASE agrosaas OWNER agrosaas;
\q
```

> **Nota — divergência real no `LES-SVRBO-AP01` (registrada em 2026-08-10):** nesta instalação específica o banco não se chama `agrosaas` nem o usuário de conexão é `agrosaas`. O `DATABASE_URL` real em produção é:
> ```
> postgresql+asyncpg://borgus:<senha>@127.0.0.1:5432/farms
> ```
> Banco `farms`, usuário `borgus`, schema de dados também chamado `farms` (não `public`). **Antes de rodar qualquer comando deste runbook que assuma `agrosaas`/`agrosaas` como nome de banco/usuário, confirme primeiro:**
> ```bash
> sudo -u agrosaas cat /opt/agrosaas/services/api/.env.local | grep DATABASE_URL
> sudo -u postgres psql -l
> ```
> Se as tabelas estiverem em um schema diferente de `public` (como `farms`), qualifique o schema nas queries: `select * from farms.alembic_version;` em vez de `select * from alembic_version;` — sem o prefixo, `psql` como `postgres` não encontra a tabela porque o `search_path` padrão do superusuário não inclui esse schema.

### 9.6 Restringir o acesso do PostgreSQL ao host local

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo grep -n "listen_addresses" /var/lib/pgsql/data/postgresql.conf
```

Se quiser travar o acesso no host local, ajuste o arquivo `/var/lib/pgsql/data/postgresql.conf` e deixe:

```conf
listen_addresses = '127.0.0.1'
port = 5432
```

Depois, ajuste o `pg_hba.conf` para aceitar somente o próprio servidor:

```conf
host    all     all     127.0.0.1/32    scram-sha-256
host    all     all     ::1/128         scram-sha-256
```

Reinicie depois da alteração:

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo systemctl restart postgresql
```

Se a instalação for versionada, use o nome correspondente, por exemplo:

```bash
sudo systemctl restart postgresql-16
```

### 9.7 Backup e restauração

### Onde executar
- `No servidor como root`

> **Atenção — mismatch de versão do `pg_dump` observado no `LES-SVRBO-AP01`:** o servidor tem dois PostgreSQL instalados (13.23 via pacote padrão do Rocky e 16.14 via PGDG, que é o realmente em uso — confirme com `sudo systemctl list-unit-files | grep postgresql`). O `pg_dump` do `PATH` (`/usr/bin/pg_dump`) é da versão 13 e falha com `server version mismatch` contra um servidor 16. **Sempre use o binário versionado correspondente:**
> ```bash
> ls /usr/pgsql-*/bin/pg_dump   # confirme qual versão existe
> ```
> e substitua `pg_dump` por `/usr/pgsql-16/bin/pg_dump` (ajuste o número conforme o resultado) em todos os comandos abaixo. O mesmo vale para `pg_restore`, `psql` e `createdb` dessa versão se necessário.

### Backup lógico

```bash
sudo -u postgres /usr/pgsql-16/bin/pg_dump -Fc agrosaas | sudo tee "/srv/agrosaas/backups/agrosaas-$(date +%F).dump" > /dev/null
```

Troque `agrosaas` pelo nome real do banco desta instalação (ver nota da seção 9.5 — no `LES-SVRBO-AP01` é `farms`).

### Restauração lógica

```bash
sudo -u postgres createdb agrosaas_restore
sudo -u postgres /usr/pgsql-16/bin/pg_restore -d agrosaas_restore /srv/agrosaas/backups/agrosaas-YYYY-MM-DD.dump
```

### Validação rápida no banco

```bash
sudo -u postgres psql -d agrosaas -c "select now();"
```

### 9.8 Ownership de tabelas — pré-requisito para migrations com `ALTER TABLE`

Se as tabelas do schema de dados pertencerem a um usuário diferente do usuário de conexão da aplicação (ex.: tabelas criadas por `postgres` enquanto a app conecta como `borgus`/`agrosaas`), qualquer migration Alembic que faça `ALTER COLUMN`/`ALTER TABLE` falha com:

```text
asyncpg.exceptions.InsufficientPrivilegeError: must be owner of table <nome_da_tabela>
```

DML (select/insert/update/delete) funciona normalmente mesmo sem ser owner — por isso o problema só aparece na hora de rodar uma migration com DDL, não no dia a dia da aplicação. Como o Postgres assume DDL transacional, uma migration que falha assim é revertida por completo (confirme com `select version_num from <schema>.alembic_version;` antes e depois — não deve ter avançado).

**Correção (rodar uma única vez, como root):**

```bash
sudo -u postgres psql -d <nome_do_banco> <<'EOF'
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '<schema>' LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO <usuario_da_app>', '<schema>', r.tablename);
  END LOOP;
  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = '<schema>' LOOP
    EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO <usuario_da_app>', '<schema>', r.sequencename);
  END LOOP;
  FOR r IN SELECT viewname FROM pg_views WHERE schemaname = '<schema>' LOOP
    EXECUTE format('ALTER VIEW %I.%I OWNER TO <usuario_da_app>', '<schema>', r.viewname);
  END LOOP;
END $$;
EOF
```

Valide com:

```bash
sudo -u postgres psql -d <nome_do_banco> -c "select tableowner, count(*) from pg_tables where schemaname='<schema>' group by tableowner;"
```

No `LES-SVRBO-AP01` (2026-08-10): banco `farms`, schema `farms`, usuário da app `borgus` — 322 tabelas transferidas de `postgres` para `borgus`. Depois dessa correção, novas migrations com DDL passam a funcionar sem erro de privilégio.

### 9.8 Copiar o banco local para produção

Use esta seção quando você quiser pegar uma base de desenvolvimento/local e carregar no servidor de produção.

### Passo 1. Exportar o banco local

### Onde executar
- `No seu computador`

### Comando

```bash
pg_dump -Fc -h 127.0.0.1 -U <usuario_local> -d <nome_do_banco_local> -f /tmp/agrosaas-local.dump
```

Se o banco local roda em Docker, execute o `pg_dump` dentro do container ou aponte `-h` e `-p` para o host/porta corretos.

### Passo 2. Enviar o dump para o servidor

### Onde executar
- `No seu computador`

### Comando

```bash
scp /tmp/agrosaas-local.dump agrosaas@179.127.30.25:/tmp/
```

Se o SSH usar outra porta, adicione `-P <porta>`.

### Passo 3. Preparar o banco no servidor

### Onde executar
- `No servidor como root`

### Comandos

```bash
sudo -u postgres dropdb --if-exists agrosaas
sudo -u postgres createdb -O agrosaas agrosaas
```

### Passo 4. Restaurar o dump no servidor

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo -u postgres pg_restore --clean --if-exists --no-owner --no-privileges -d agrosaas /tmp/agrosaas-local.dump
```

### Passo 5. Validar a importação

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo -u postgres psql -d agrosaas -c "select count(*) from tenants;"
```

Se o seu banco tiver outro nome de tabela inicial para validação, troque `tenants` por uma tabela já conhecida do projeto.

## 10. Redis via Docker

O `Redis` não foi listado como instalado, então a forma mais simples é subir um container local.

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo docker run -d \
  --name agrosaas-redis \
  --restart unless-stopped \
  -p 127.0.0.1:6379:6379 \
  redis:7-alpine
```

### Verificação

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo docker ps
```

Se aparecer `permission denied while trying to connect to the docker API`, confirme que o comando foi executado com `sudo`.

## 11. Baixar o código-fonte

Backend e frontend são publicados pelo mesmo repositório monorepo:

| Componente | Caminho no repositório | Destino no servidor |
|---|---|---|
| Backend e estrutura principal | `services/api` | `/opt/agrosaas/services/api` |
| Frontend web | `apps/web` | `/opt/agrosaas/apps/web` |

O frontend faz parte do monorepo e não deve ser clonado ou atualizado separadamente.

### 11.1 Primeira instalação

### Onde executar
- `No servidor como usuário agrosaas`

### Comando

```bash
cd /opt/agrosaas
git clone https://github.com/maborges/farm.git .
```

Confirme os dois repositórios:

```bash
git remote -v
```

### 11.2 Se o repositório principal já foi clonado sem o frontend

### Onde executar
- `No servidor como usuário agrosaas`

```bash
cd /opt/agrosaas
git pull --ff-only
```

### 11.3 Atualizar backend e frontend

### Onde executar
- `No servidor como usuário agrosaas`

Atualize primeiro o repositório principal e depois coloque o frontend exatamente no commit referenciado por ele:

```bash
cd /opt/agrosaas
git pull --ff-only
```

Não execute `git pull` dentro de `/opt/agrosaas/apps/web`: esse diretório pertence ao monorepo.

Se os repositórios forem privados, configure no servidor uma chave SSH técnica com acesso somente de leitura e substitua as URLs HTTPS pelas URLs SSH fornecidas pelo GitHub.

## 12. Arquivos de ambiente

### 12.1 Backend

### Onde executar
- `No servidor como usuário agrosaas`
- arquivo: `/opt/agrosaas/services/api/.env.local`

### Conteúdo sugerido

```env
DATABASE_URL=postgresql+asyncpg://agrosaas:TROQUE-ESTA-SENHA@127.0.0.1:5432/agrosaas
REDIS_URL=redis://127.0.0.1:6379/0
FRONTEND_URL=http://179.127.30.25
ALLOW_ORIGINS=["http://179.127.30.25","https://179.127.30.25"]
storage_backend=local
storage_local_path=/srv/agrosaas/uploads
run_embedded_jobs=false
storage_public_base_url=http://179.127.30.25
```

Observação:
- se houver domínio e certificado válidos, troque `http://179.127.30.25` por `https://seu-dominio`.
- `run_embedded_jobs=false` é o modo correto quando o worker roda separado.
- depois de subir a aplicação, valide também o acesso do PWA em `Campo PWA > Dispositivos`. É ali que ficam os aparelhos de campo; para o primeiro uso, clique em `Novo dispositivo` e cadastre/ative o tablet ou celular do operador.

### 12.2 Frontend web

### Onde executar
- `No servidor como usuário agrosaas`
- arquivo: `/opt/agrosaas/apps/web/.env.local`

### Conteúdo sugerido

```env
BACKEND_URL=http://127.0.0.1:8000
```

## 13. Instalar dependências da aplicação

### 13.1 Backend

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas/services/api`

### Comandos

```bash
cd /opt/agrosaas/services/api
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

### 13.2 Frontend

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas`

### Comandos

```bash
cd /opt/agrosaas
pnpm install
```

Se aparecer `[ERR_PNPM_IGNORED_BUILDS]`, autorize somente as dependências conhecidas listadas pelo projeto:

```bash
pnpm approve-builds
```

Na tela interativa:

1. Use as setas para navegar.
2. Pressione a barra de espaço para marcar `core-js`, `msw`, `sharp` e `unrs-resolver`.
3. Pressione `Enter` para confirmar.
4. Responda `y` se o `pnpm` pedir confirmação final.

Depois execute os scripts autorizados e repita a instalação para validar:

```bash
pnpm rebuild
pnpm install
```

Não autorize automaticamente pacotes diferentes desses sem revisão. O `pnpm approve-builds` registra a autorização no `pnpm-workspace.yaml`; a configuração deve ser revisada e posteriormente versionada no repositório principal para que os próximos deploys não dependam dessa interação manual.

### 13.3 Campo PWA

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas`

### Comandos

```bash
cd /opt/agrosaas
pnpm --filter @agro/campo install
```

Se preferir, `pnpm install` na raiz do workspace já instala `apps/web` e `apps/campo` juntos. O comando acima serve para validar só o app Campo.

## 14. Aplicar migrations

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas/services/api`

### Comando

```bash
cd /opt/agrosaas/services/api
source .venv/bin/activate
.venv/bin/alembic upgrade head
```

## 15. Build do frontend

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas`

### Comando

```bash
cd /opt/agrosaas
pnpm --filter web build
```

## 15.1 Build do Campo PWA

### Onde executar
- `No servidor como usuário agrosaas`
- dentro da pasta `/opt/agrosaas`

### Comando

```bash
cd /opt/agrosaas
pnpm --filter @agro/campo build
```

## 16. Primeiro teste manual

### Onde executar
- `No servidor como usuário agrosaas`

### Comandos

```bash
cd /opt/agrosaas/services/api
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```bash
cd /opt/agrosaas/apps/web
pnpm start --hostname 127.0.0.1 --port 3000
```

Para o Campo PWA, em outro terminal:

```bash
cd /opt/agrosaas/apps/campo
pnpm start
```

O `apps/campo` já sobe em `3002` pelo próprio `package.json`.

Enquanto esses dois processos estiverem ativos, teste:

### Onde executar
- `No servidor como root` ou `No seu computador` via navegador

### Comandos

```bash
curl -I http://127.0.0.1:8000/health
curl -I http://127.0.0.1:8000/health/ready
curl -I http://127.0.0.1:3000/
```

## 17. Criar os serviços systemd

Depois que os testes manuais funcionarem, transforme os comandos em serviços automáticos.

### 17.1 Backend

### Onde executar
- `No servidor como root`
- arquivo: `/etc/systemd/system/agrosaas-api.service`

### Conteúdo

```ini
[Unit]
Description=AgroSaaS Backend API
After=network.target postgresql.service docker.service

[Service]
Type=simple
User=agrosaas
WorkingDirectory=/opt/agrosaas/services/api
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/agrosaas/services/api/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 17.2 Frontend

### Onde executar
- `No servidor como root`
- arquivo: `/etc/systemd/system/agrosaas-web.service`

### Conteúdo

```ini
[Unit]
Description=AgroSaaS Frontend Web
After=network.target agrosaas-api.service

[Service]
Type=simple
User=agrosaas
WorkingDirectory=/opt/agrosaas/apps/web
Environment=NODE_ENV=production
Environment=BACKEND_URL=http://127.0.0.1:8000
Environment=PATH=/home/agrosaas/.nvm/versions/node/v22.23.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/bin/bash -lc 'exec pnpm start --hostname 127.0.0.1 --port 3000'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 17.3 Campo PWA

### Onde executar
- `No servidor como root`
- arquivo: `/etc/systemd/system/agrosaas-campo.service`

### Conteúdo

```ini
[Unit]
Description=AgroSaaS Campo PWA
After=network.target

[Service]
Type=simple
User=agrosaas
WorkingDirectory=/opt/agrosaas/apps/campo
Environment=NODE_ENV=production
Environment=BACKEND_URL=http://127.0.0.1:8000
Environment=PATH=/home/agrosaas/.nvm/versions/node/v22.23.1/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/bin/bash -lc 'exec pnpm start'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 17.4 Worker de automações

### Onde executar
- `No servidor como root`
- arquivo: `/etc/systemd/system/agrosaas-worker.service`

### Conteúdo

```ini
[Unit]
Description=AgroSaaS Worker de Automações
After=network.target postgresql.service redis.service docker.service

[Service]
Type=simple
User=agrosaas
WorkingDirectory=/opt/agrosaas/services/api
ExecStart=/opt/agrosaas/services/api/.venv/bin/python automacoes/worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Se o ambiente também precisar do worker do outbox, crie um segundo serviço com:

```bash
python -m events.outbox_worker run --loop
```

## 18. Recarregar o systemd

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now agrosaas-api
sudo systemctl enable --now agrosaas-web
sudo systemctl enable --now agrosaas-campo
sudo systemctl enable --now agrosaas-worker
```

## 19. Configurar o Nginx

Como o acesso público será feito só pelas portas `80` e `443`, o Nginx deve ser o ponto de entrada.

> **Nota — configuração real observada no `LES-SVRBO-AP01` (2026-08-10):** o arquivo `/etc/nginx/conf.d/agrosaas.conf` em produção é mais enxuto que o exemplo abaixo — só tem `location /api/` (proxy para o backend, sem strip de prefixo) e `location /` (proxy para o frontend). **Não existem blocos `/health`, `/health/ready`, `/docs` nem `/openapi.json`** — esses endpoints não são expostos publicamente nessa instalação, só via `127.0.0.1:8000` diretamente no servidor. Portanto:
> - `curl http://<ip-publico>/health` retorna 404 (cai na rota `/` do Next.js) — isso é esperado, não é falha de deploy.
> - Para checar a saúde do backend publicamente, use `curl http://<ip-publico>/api/health` **somente se** a rota estiver de fato montada sob `/api/` no `main.py`; caso contrário, valide sempre via SSH direto em `127.0.0.1:8000/health`.
> - Antes de assumir que o exemplo abaixo bate com a config real, rode `sudo cat /etc/nginx/conf.d/agrosaas.conf` e compare.

### 19.1 Criar o arquivo de site

### Onde executar
- `No servidor como root`
- arquivo: `/etc/nginx/conf.d/agrosaas.conf`

### Conteúdo sugerido

Sem domínio ainda, publique só o `web` no IP público e mantenha o `Campo PWA` interno em `127.0.0.1:3002`. Quando houver domínio/subdomínio, será possível criar um `server` próprio para o Campo.

```nginx
server {
    listen 80;
    server_name 179.127.30.25;
    client_max_body_size 50m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health/ready {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
    }
}
```

### 19.2 Se houver certificado HTTPS

Se ainda não existir domínio, você pode usar HTTP para o primeiro teste.

Se houver domínio apontado para esse IP, crie ou instale o certificado e depois adicione outro `server` com `listen 443 ssl;`.

### 19.3 Como acessar (chamar) o Campo PWA sem domínio

Sem um domínio (apenas IP), não é recomendado publicar o `Campo PWA` na mesma porta `80` (raiz ou subpasta) que o sistema principal (`web`), pois ocorrerão conflitos nos arquivos de `manifest.json` e `service worker`.

Para acessar e testar o Campo PWA temporariamente, você pode expô-lo em uma porta diferente no Nginx (por exemplo, `8080`). Adicione este bloco extra no final do seu arquivo `/etc/nginx/conf.d/agrosaas.conf`:

```nginx
server {
    listen 8080;
    server_name 179.127.30.25;

    location / {
        proxy_pass http://127.0.0.1:3002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Após reiniciar o Nginx (no próximo passo), você poderá **chamar o Campo PWA** acessando: `http://179.127.30.25:8080`

Quando houver subdomínio próprio (ex: `campo.seudominio.com.br`), você alterará este bloco mudando o `listen` para `80`/`443` e ajustando o `server_name`.

### 19.4 Validar a configuração do Nginx

### Onde executar
- `No servidor como root`

### Comando

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 20. Abrir o firewall

### Onde executar
- `No servidor como root`

### Comandos

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

Não abra `5432`, `6379`, `8000` nem `3000` para a internet.

## 21. Smoke test final

### Onde executar
- `No seu computador` ou `No servidor`

### Comandos

```bash
curl -I http://179.127.30.25/
curl -I http://179.127.30.25/health
curl -I http://179.127.30.25/health/ready
```

Se HTTPS estiver ativo:

```bash
curl -kI https://179.127.30.25/
curl -kI https://179.127.30.25/health
curl -kI https://179.127.30.25/health/ready
```

## 22. Comandos úteis de operação

### Onde executar
- `No servidor como root`

### Status dos serviços

```bash
sudo systemctl status agrosaas-api
sudo systemctl status agrosaas-web
sudo systemctl status agrosaas-worker
sudo systemctl status nginx
sudo systemctl status postgresql
```

### Reiniciar tudo

```bash
sudo systemctl restart agrosaas-api
sudo systemctl restart agrosaas-web
sudo systemctl restart agrosaas-worker
sudo systemctl restart nginx
```

### Ver logs

```bash
sudo journalctl -u agrosaas-api -f
sudo journalctl -u agrosaas-web -f
sudo journalctl -u agrosaas-worker -f
sudo journalctl -u nginx -f
```

## 23. Atualização de versão

### Passos

0. **Como root:** backup do banco antes de qualquer migration (seção 9.7/9.8 — confirme nome do banco e binário `pg_dump` da versão certa primeiro).
1. **Como usuário `agrosaas`:** entre no diretório do projeto.
2. Faça `git pull --ff-only` no repositório principal.
3. O frontend em `apps/web` já é atualizado junto com o monorepo.
4. Atualize dependências se necessário.
5. Rode `alembic upgrade head`. Se falhar com `InsufficientPrivilegeError: must be owner of table ...`, veja a seção 9.8 (ownership) — **como root**, corrija o ownership e repita o `alembic upgrade head`.
6. Rode `pnpm --filter web build`.
7. **Como root:** reinicie os serviços.

### Comandos

```bash
# 0. Backup — como root, ANTES de tudo
sudo -u postgres /usr/pgsql-16/bin/pg_dump -Fc <nome_do_banco> | sudo tee "/srv/agrosaas/backups/<nome_do_banco>-antes-deploy-$(date +%F-%H%M).dump" > /dev/null

# 1-6. Como usuário agrosaas
sudo -iu agrosaas
cd /opt/agrosaas
git pull --ff-only

cd /opt/agrosaas/services/api
source .venv/bin/activate
alembic upgrade head

cd /opt/agrosaas
pnpm --filter web build
exit   # volta a root

# 7. Restart — como root
sudo systemctl restart agrosaas-api agrosaas-web agrosaas-worker nginx
```

### Smoke test pós-deploy

```bash
# no servidor via SSH (127.0.0.1 só funciona ali, não da máquina cliente)
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready

# da máquina cliente
curl -I http://<ip-publico>/
```

Use `curl` sem `-I` para checar o corpo da resposta de `/health` — os endpoints de health não implementam `HEAD`, então `curl -I` retorna `405 Method Not Allowed` mesmo com o serviço saudável (falso alarme conhecido).

## 24. Reversão rápida

Se a nova versão falhar:

1. Pare os serviços novos.
2. Volte para o commit anterior.
3. Refaça o build.
4. Reinicie os serviços.

### Comandos

```bash
cd /opt/agrosaas
git checkout <commit_anteriores_ou_tag>

cd /opt/agrosaas/services/api
source .venv/bin/activate
.venv/bin/alembic upgrade head

cd /opt/agrosaas
pnpm --filter web build

sudo systemctl restart agrosaas-api agrosaas-web agrosaas-worker nginx
```

## 25. Alternativa: instalar sem copiar os fontes para o servidor

Nesta modalidade, o código é compilado e empacotado em imagens Docker fora do `LES-SVRBO-AP01`. O servidor recebe somente as imagens prontas, os arquivos de configuração e os dados persistentes.

Fluxo:

```text
Computador do desenvolvedor ou CI -> registro Docker privado -> LES-SVRBO-AP01
```

Importante:

- O repositório ainda não possui Dockerfiles de produção para API, worker e frontend. A equipe de desenvolvimento deve criá-los e validá-los antes de usar esta modalidade.
- Use um registro privado, como GitLab Container Registry, GitHub Container Registry, Harbor ou o registro privado da empresa.
- O PostgreSQL continua instalado no host e não deve ser colocado no `compose.prod.yml`.
- O Redis continua no container `agrosaas-redis` criado na seção 10.
- Um administrador do Docker ainda pode inspecionar o conteúdo das imagens. Esta opção evita o clone do repositório no servidor, mas não transforma Python ou JavaScript em código impossível de extrair.

### 25.1 Pré-requisitos das imagens

As imagens de produção devem ser preparadas para atender a este contrato:

| Imagem | Conteúdo | Processo padrão |
|---|---|---|
| `agrosaas-api` | Backend e Alembic | Uvicorn em `127.0.0.1:8000` |
| `agrosaas-worker` | Backend e worker de automações | `python automacoes/worker.py` |
| `agrosaas-web` | Build de produção do Next.js | Next.js em `127.0.0.1:3000` |

O backend e o worker devem aceitar `DATABASE_URL`, `REDIS_URL` e demais configurações por variáveis de ambiente. O frontend deve aceitar `BACKEND_URL`.

### 25.2 Gerar e publicar as imagens

### Onde executar
- `No computador do desenvolvedor ou no pipeline de CI, dentro do repositório`

Substitua `registry.empresa.com` pelo endereço real do registro e `1.0.0` pela versão da aplicação.

```bash
docker login registry.empresa.com
docker build -t registry.empresa.com/agrosaas-api:1.0.0 -f services/api/Dockerfile .
docker build -t registry.empresa.com/agrosaas-worker:1.0.0 -f services/api/Dockerfile.worker .
docker build -t registry.empresa.com/agrosaas-web:1.0.0 -f apps/web/Dockerfile .
docker push registry.empresa.com/agrosaas-api:1.0.0
docker push registry.empresa.com/agrosaas-worker:1.0.0
docker push registry.empresa.com/agrosaas-web:1.0.0
```

Não use a tag `latest` em produção. Uma tag fixa permite identificar e restaurar exatamente a versão anterior.

### 25.3 Criar o diretório de implantação

### Onde executar
- `No servidor como root`

```bash
sudo mkdir -p /opt/agrosaas-deploy
sudo chown agrosaas:agrosaas /opt/agrosaas-deploy
sudo chmod 750 /opt/agrosaas-deploy
```

Esse diretório conterá apenas os arquivos operacionais, não o repositório da aplicação.

### 25.4 Criar o ambiente da API e do worker

### Onde executar
- `No servidor como usuário agrosaas`

```bash
sudo -iu agrosaas
cd /opt/agrosaas-deploy
nano .env.api
```

Conteúdo sugerido:

```env
DATABASE_URL=postgresql+asyncpg://agrosaas:TROQUE-ESTA-SENHA@127.0.0.1:5432/agrosaas
REDIS_URL=redis://127.0.0.1:6379/0
FRONTEND_URL=http://179.127.30.25
ALLOW_ORIGINS=["http://179.127.30.25","https://179.127.30.25"]
storage_backend=local
storage_local_path=/srv/agrosaas/uploads
```

Salve no `nano` com `Ctrl+O`, pressione `Enter` e saia com `Ctrl+X`. Proteja o arquivo:

```bash
chmod 600 /opt/agrosaas-deploy/.env.api
```

### 25.5 Criar o ambiente do frontend

### Onde executar
- `No servidor como usuário agrosaas`

```bash
cd /opt/agrosaas-deploy
nano .env.web
```

Conteúdo:

```env
NODE_ENV=production
BACKEND_URL=http://127.0.0.1:8000
```

Depois proteja o arquivo:

```bash
chmod 600 /opt/agrosaas-deploy/.env.web
```

### 25.6 Criar o Compose de produção

### Onde executar
- `No servidor como usuário agrosaas`

```bash
cd /opt/agrosaas-deploy
nano compose.prod.yml
```

Conteúdo, substituindo o registro e a versão:

```yaml
services:
  api:
    image: registry.empresa.com/agrosaas-api:1.0.0
    container_name: agrosaas-api
    network_mode: host
    env_file:
      - .env.api
    volumes:
      - /srv/agrosaas/uploads:/srv/agrosaas/uploads
    restart: unless-stopped

  worker:
    image: registry.empresa.com/agrosaas-worker:1.0.0
    container_name: agrosaas-worker
    network_mode: host
    env_file:
      - .env.api
    volumes:
      - /srv/agrosaas/uploads:/srv/agrosaas/uploads
    restart: unless-stopped
    depends_on:
      - api

  web:
    image: registry.empresa.com/agrosaas-web:1.0.0
    container_name: agrosaas-web
    network_mode: host
    env_file:
      - .env.web
    restart: unless-stopped
    depends_on:
      - api
```

O uso de `network_mode: host` é intencional neste servidor Linux. Assim, os containers acessam PostgreSQL e Redis por `127.0.0.1`, e os aplicativos continuam escutando somente nas portas locais `8000` e `3000`.

### 25.7 Autenticar o servidor no registro

### Onde executar
- `No servidor como root`

Use uma conta técnica com permissão somente para leitura das imagens:

```bash
sudo docker login registry.empresa.com
```

Informe o usuário e o token do registro quando solicitado. Não coloque o token dentro do `compose.prod.yml`.

### 25.8 Baixar as imagens

### Onde executar
- `No servidor como root`

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml pull
```

### 25.9 Executar as migrations do PostgreSQL

### Onde executar
- `No servidor como root`

Faça um backup antes da migration:

```bash
sudo -u postgres pg_dump -Fc agrosaas | sudo tee /srv/agrosaas/backups/agrosaas-antes-deploy.dump > /dev/null
```

Execute a migration usando a imagem da API:

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml run --rm api alembic upgrade head
```

Esse comando pressupõe que a imagem `agrosaas-api` inicia no diretório que contém o arquivo de configuração do Alembic.

### 25.10 Subir a aplicação

### Onde executar
- `No servidor como root`

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml up -d
sudo docker compose -f compose.prod.yml ps
```

Os três serviços devem aparecer com estado `Up` ou `running`.

### 25.11 Verificar logs e endpoints

### Onde executar
- `No servidor como root`

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml logs --tail=100 api
sudo docker compose -f compose.prod.yml logs --tail=100 worker
sudo docker compose -f compose.prod.yml logs --tail=100 web
curl -I http://127.0.0.1:3000/
curl -I http://127.0.0.1:8000/health
curl -I http://179.127.30.25/
```

O Nginx permanece configurado conforme a seção 19, encaminhando `/api` para a API e as demais rotas para o frontend.

### 25.12 Atualizar para uma nova versão

1. Publique as três imagens com uma nova tag, por exemplo `1.0.1`.
2. No servidor, altere as três tags no `compose.prod.yml`.
3. Faça backup do PostgreSQL.
4. Baixe as novas imagens.
5. Execute as migrations.
6. Recrie os containers.

### Onde executar
- `No servidor como root`

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml pull
sudo -u postgres pg_dump -Fc agrosaas | sudo tee /srv/agrosaas/backups/agrosaas-antes-atualizacao.dump > /dev/null
sudo docker compose -f compose.prod.yml run --rm api alembic upgrade head
sudo docker compose -f compose.prod.yml up -d
sudo docker compose -f compose.prod.yml ps
```

### 25.13 Voltar para a versão anterior

1. Edite o `compose.prod.yml` e restaure as tags anteriores.
2. Baixe as imagens antigas, caso não estejam mais no cache.
3. Recrie os containers.

### Onde executar
- `No servidor como root`

```bash
cd /opt/agrosaas-deploy
sudo docker compose -f compose.prod.yml pull
sudo docker compose -f compose.prod.yml up -d
sudo docker compose -f compose.prod.yml ps
```

Reverter a imagem não reverte automaticamente o banco. Se a nova versão tiver migrations incompatíveis, siga o procedimento de rollback definido pela equipe de desenvolvimento antes de restaurar qualquer backup.

## 26. Observações finais

- Os arquivos `.env.local` ficam no backend e no frontend, cada um no seu próprio diretório.
- O backend deve ficar escutando só em `127.0.0.1`.
- O frontend também deve ficar em `127.0.0.1`.
- O único ponto exposto para fora deve ser o Nginx nas portas `80` e `443`.
- Redis e PostgreSQL não devem ficar expostos publicamente.
- Se houver domínio, é melhor usar HTTPS real em vez de IP.
