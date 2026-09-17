# DeepFarms - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focado em produtividade, isolamento de dados (multi-tenancy) e interface de alta performance.

## Leitura Inicial

A ordem oficial de leitura para agentes de IA vive em **`docs/architecture/ai-bootstrap.md`** — não repetida aqui.

Manual operacional da Plataforma Balança: [docs/MANUAL_BALANCA.md](docs/MANUAL_BALANCA.md).

Utilize português (pt-BR) para documentos e interações com o usuário, com acentuação correta e linguagem não técnica nas explicações.

> A fonte oficial do frontend web é `apps/web/`. O backend principal fica em `services/api` e os contratos compartilhados em `packages/`.

## Acesso SSH e deploy em produção

O servidor de produção é acessado pelo usuário `ubuntu`, com a chave privada
local autorizada para o ambiente. O checkout do monorepo no servidor fica em
`/opt/deepfarms/farm`.

```bash
ssh -i ~/.ssh/deepfarms-pilot-key.pem ubuntu@ec2-56-126-104-183.sa-east-1.compute.amazonaws.com
```

Depois de conectado, confirme o checkout e os serviços antes de publicar:

```bash
cd /opt/deepfarms/farm
git fetch origin main
git status --short
systemctl is-active deepfarms-api deepfarms-web deepfarms-campo deepfarms-worker deepfarms-outbox nginx
```

Execute `git pull --ff-only origin main` somente depois de classificar e
preservar qualquer alteração local, configuração `.env.production` ou backup
operacional apresentado pelo `git status`.

Para alterações somente no Web, faça o build e reinicie apenas esse serviço:

```bash
NODE_OPTIONS=--max-old-space-size=1024 pnpm --filter web build
sudo systemctl restart deepfarms-web
curl -fsS http://127.0.0.1:3000/ >/dev/null && echo "Web OK"
```

Não execute `git reset --hard`, `git clean` ou remova arquivos `.env.production`
e backups operacionais do servidor. O procedimento completo, incluindo migrations,
rollback e verificações de saúde, está em
[docs/runbooks/deploy-les-svrbo-ap01.md](docs/runbooks/deploy-les-svrbo-ap01.md).

## Arquitetura do Sistema

Monorepo dividido em:
- **apps/web**: Interface Next.js 16 com shadcn/ui e Zustand.
- **apps/campo**: PWA de campo offline-first, extensão oficial do Caderno de Campo.
- **../balanca-platform/station**: PWA de estação de balança offline-first (pesagem de carga e animais), desacoplado dos demais módulos.
- **services/api**: Backend Python com FastAPI, SQLAlchemy e PostgreSQL.
- **../balanca-platform/service**: Serviço independente de pesagem, estações, operadores,
outbox Observer e conciliação; o DeepFarms fala com ele somente por contrato HTTP.
- **../balanca-platform/contracts**: Contratos próprios da integração da Balança.
- **packages/zod-schemas**: Contratos compartilhados do DeepFarms.

Inventário técnico completo (versões, libs, infra): `docs/architecture/architecture-inventory.md`.

## Módulos Implementados

- Identidade e Multi-Tenancy (auth, RBAC, onboarding, convites)
- Gestão Agrícola e Pecuária (talhões, safras, análise de solo, DRE por safra)
- Templates e Governança de fase de safra
- Alertas e Recomendações financeiras automáticas
- Suprimentos e Compras (reposição automática, cotações, análise de melhor fornecedor)
- Frota (manutenção preventiva, custos operacionais, benchmarks)
- Copiloto Financeiro e IA (simulação, plano de ação, autopilot adaptativo)
- Growth & A/B Testing, Telemetria de UX adaptativa
- Hedge de commodities (Mark-to-Market, exposição física × financeira)
- Vínculo territorial/fundiário (Propriedade ↔ Imóvel Rural)
- Balança (pesagem de carga e animais, offline-first, serviço desacoplado consumido por colheita/compras/vendas/pecuária)
- TARA (adapter HTTP versionado, ordens, pesagens, eventos, webhooks e ativação de estações)

Detalhamento de cada feature, decisões e histórico de implementação: `docs/CHANGELOG.md` (não faz parte da leitura padrão — consulte apenas quando precisar entender por que algo foi construído de determinada forma).

## Conceitos-Chave: Propriedade, Talhão e Unidade Produtiva

- **Propriedade / Unidade Produtiva**: cadastro mestre da fazenda (nome, tipo, documentos, endereço, áreas, geometria).
- **Área Rural / Talhão**: divisão física dentro da propriedade — base para solo, caderno de campo, NDVI etc.
- **Production Unit da safra**: vínculo `cultivo + área + participação` dentro de uma safra específica.
- **Fluxo**: cadastra-se a propriedade → gera/organiza talhões → a safra vincula em `production-units` → módulos agrícolas operam sobre esses vínculos.

Regras completas de fronteira territorial/fundiária: `docs/architecture/agrosaas-domain-map.md`.

### Integração TARA

O DeepFarms acessa a Plataforma TARA exclusivamente por HTTP em
`/api/v1/integracoes/tara`. A configuração por tenant é persistida no domínio
canônico de integrações; o segredo do API Client é armazenado criptografado e
nunca é retornado ao frontend ou aos logs. O cliente envia `X-Tenant-ID`,
`X-Balanca-Client-ID` e `X-Balanca-Client-Secret` em todas as chamadas.

Rotas principais: `PUT/GET /config`, `POST /clients`, `POST /orders`,
`GET /orders/{id}`, `GET /weighings`, `POST /weighings/sync`, `GET /events`,
`GET/PUT /webhooks`, `POST /webhooks/replay` e `POST /stations/activate`.
A sincronização de pesagens preserva o cursor opaco no banco e só o avança
após processar cada página com sucesso.

## Referência Oficial FIELD-CORE

Arquitetura consolidada do Caderno de Campo (governança, cadeia documental, papel do PWA): `docs/architecture/field-core-final-governance.md`.

## Como Executar

Execute cada bloco em um terminal separado, mantendo o backend ativo antes dos workers e das aplicações web.
Para a Balança, a ordem recomendada é: banco/migrations, backend DeepFarms,
serviço independente, configuração do conector, worker, backoffice web, PWA da
estação e Bridge do indicador.

### 1. Aplicar migrations do banco

O que faz: atualiza o schema PostgreSQL para o head atual antes de iniciar a API.

```bash
cd /opt/lampp/htdocs/farm/services/api
./.venv/bin/alembic upgrade head
```

### 2. Iniciar o backend FastAPI

O que faz: sobe a API em `http://localhost:8000` e disponibiliza a documentação em `/docs`.

```bash
cd /opt/lampp/htdocs/farm/services/api
./start_server.sh
```

Para iniciar manualmente sem o script:

```bash
cd /opt/lampp/htdocs/farm/services/api
./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Verificar a API

O que faz: confirma que o processo FastAPI está respondendo antes de iniciar os consumidores.

```bash
curl -fsS http://localhost:8000/docs >/dev/null && echo "API OK"
```

### 4. Iniciar o worker de automações

O que faz: executa o scheduler de automações do DeepFarms usando o virtualenv oficial da API.

```bash
cd /opt/lampp/htdocs/farm
./services/api/.venv/bin/python scripts/run_worker.py
```

### 5. Iniciar o Outbox em desenvolvimento

O que faz: processa continuamente os eventos pendentes de um tenant específico. Substitua o UUID pelo tenant desejado.

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python -m events.outbox_worker run --loop --tenant-id SEU_TENANT_ID
```

Não execute este modo simultaneamente com o cron global para o mesmo conjunto de tenants.

### 6. Iniciar o frontend Web

O que faz: sobe o painel administrativo em `http://localhost:3000`.

```bash
cd /opt/lampp/htdocs/farm/apps/web
pnpm run dev
```

Se houver lock antigo do Next.js:

```bash
rm -f /opt/lampp/htdocs/farm/apps/web/.next/dev/lock
```

### 7. Iniciar o PWA de Campo

O que faz: sobe a aplicação offline-first de campo em `http://localhost:3002`.

```bash
cd /opt/lampp/htdocs/farm/apps/campo
pnpm run dev
```

A primeira ativação usa `/activate` → `/pin`; depois, a aplicação abre em `/home`.

### 8. Iniciar o PWA de Balança

O que faz: sobe a aplicação de estação de pesagem em `http://localhost:3003`.

```bash
cd /opt/lampp/htdocs/balanca-platform
pnpm install
cd station
pnpm run dev
```

Para encaminhar a estação ao serviço independente, crie
`/opt/lampp/htdocs/balanca-platform/station/.env.local` a partir de
`/opt/lampp/htdocs/balanca-platform/station/.env.example` e preencha:

    BALANCA_SERVICE_URL=http://127.0.0.1:8010
    BALANCA_SERVICE_CLIENT_ID=client-id-do-agrosaas
    BALANCA_SERVICE_CLIENT_SECRET=segredo-do-agrosaas
    BALANCA_TENANT_ID=UUID_DO_TENANT_DA_ESTACAO

As credenciais não devem usar o prefixo NEXT_PUBLIC e não devem ser enviadas
ao navegador. O proxy Next.js adiciona os headers no servidor.

### 9. Iniciar o serviço independente da Balança

O que faz: disponibiliza a API consumida pela estação e pelo DeepFarms. A
instalação pode ser feita separadamente do backend principal.

Comandos:

    cd /opt/lampp/htdocs/balanca-platform/service
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt
    cp .env.example .env
    set -a; source .env; set +a
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/000_platform_foundation.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/001_service_tables.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/002_security_identity.sql
    psql --set=ON_ERROR_STOP=1 "$BALANCA_DATABASE_URL" -f migrations/003_contingency.sql
    ./start_server.sh

### 9.1. Configurar o DeepFarms para usar a Balança independente

No arquivo de ambiente do backend, informe a URL e as credenciais de cliente
emitidas pelo backoffice da Balança.
Esses valores ficam somente no servidor:

    BALANCA_SERVICE_URL=http://127.0.0.1:8010
    BALANCA_SERVICE_CLIENT_ID=client-id-do-agrosaas
    BALANCA_SERVICE_CLIENT_SECRET=segredo-emitido-pelo-backoffice

Reinicie o backend depois de alterar o ambiente. Sem essas três variáveis, as
operações de pesagem do DeepFarms são recusadas e nenhum banco local de Balança
é utilizado como fallback.

Para receber as confirmações por webhook, configure também o segredo HMAC da
Conta no DeepFarms e aponte o destino da Conta na TARA para:

    BALANCA_WEBHOOK_ACCOUNT_SECRETS_JSON={"account_uuid":"segredo-compartilhado-com-a-tara"}
    POST /api/v1/integracoes/balanca/events

O endpoint valida a assinatura sobre método, caminho, timestamp e corpo bruto,
deduplica por `event_id` e só confirma com `204` após publicar o evento nos
subscribers internos. Falhas de processamento retornam erro para que a TARA
faça retry; reentregas já registradas continuam sendo aceitas como sucesso.

O primeiro usuário do backoffice é criado com
`/opt/lampp/htdocs/balanca-platform/service/bootstrap_admin.py`.
Depois do login em `/v1/auth/login`, o administrador emite uma credencial para
cada consumidor em `/v1/admin/api-clients`; o DeepFarms recebe somente seu
`client_id` e segredo, que devem ser rotacionados ou revogados pelo backoffice
quando necessário.

### 9.2. Contingência por pendrive

O serviço Balança aceita pacotes físicos assinados em
`POST /v1/contingency/import`. A estação pode exportar o arquivo para um
pendrive; o backoffice importa o arquivo pela interface que consuma essa API
ou pelo utilitário `/opt/lampp/htdocs/balanca-platform/service/import_contingency.py`. O recurso pertence
ao serviço Balança e pode ser utilizado por qualquer cliente integrado, não
somente pelo DeepFarms. O lote original, a assinatura, a sequência e o resultado
de cada pesagem são preservados para auditoria e reprocessamento.

### 9.3. Iniciar o worker da Balança

O worker entrega os eventos Observer pendentes por HTTP ou arquivo JSONL.
Configure no .env do serviço BALANCA_OUTBOX_TENANT_ID e um dos destinos:

    BALANCA_OUTBOX_TARGET_URL=https://cliente.exemplo/api/eventos
    BALANCA_OUTBOX_TARGET_API_KEY=chave-do-consumidor

ou:

    BALANCA_OUTBOX_FILE_PATH=/var/lib/balanca/outbox/eventos.jsonl

Em desenvolvimento:

    cd /opt/lampp/htdocs/balanca-platform/service
    ./.venv/bin/python run_worker.py

Em produção, instale balanca-outbox.service.example como serviço systemd.

### 10. Iniciar a ponte eletrônica da balança

O que faz: conecta o indicador físico ou simulador à aplicação da balança pela porta `8321`.

```bash
cd /opt/lampp/htdocs/balanca-platform/bridge
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edite config.yaml com a porta serial ou host/porta TCP do indicador.
./.venv/bin/python -m balanca_bridge.main
```

Para usar o simulador em vez do indicador físico:

```bash
cd /opt/lampp/htdocs/balanca-platform/bridge
./.venv/bin/python simulator.py
```

Para instalar a Bridge como serviço no computador da balança:

    cd /opt/lampp/htdocs/balanca-platform/bridge
    sudo ./install.sh

Em uma rede sem internet, prepare previamente o wheelhouse em uma máquina
conectada:

    cd /opt/lampp/htdocs/balanca-platform/bridge
    ./prepare-offline-bundle.sh /tmp/balanca-bridge-wheelhouse

Transfira o diretório para a estação e instale usando:

    BALANCA_BRIDGE_WHEELHOUSE=/caminho/wheelhouse sudo -E ./install.sh

O instalador preserva o config.yaml existente. Para atualizar, execute o
mesmo instalador; a configuração local e a fila do PWA não são apagadas.

### 11. Executar o Outbox global no cron

O que faz: percorre os tenants ativos, ativa o contexto RLS de cada tenant e processa lotes de 50 eventos. Retorna `0` sem falhas e `1` quando algum tenant falha.

Validar sem processar eventos:

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python -m events.outbox_worker --help
PYTHONPATH=. .venv/bin/python -m py_compile scripts/run_outbox_global.py
```

Executar manualmente:

```bash
cd /opt/lampp/htdocs/farm/services/api
PYTHONPATH=. .venv/bin/python scripts/run_outbox_global.py
echo "exit_code=$?"
```

Configurar o log e o cron:

```bash
sudo install -d -o borgus -g borgus /var/log/farm
crontab -e
```

Adicione a linha abaixo. A execução a cada 5 minutos evita sobreposição em ambientes com muitos tenants; `flock` impede duas execuções simultâneas:

```cron
*/5 * * * * /usr/bin/flock -n /tmp/farm-outbox.lock /bin/bash -lc 'cd /opt/lampp/htdocs/farm/services/api && PYTHONPATH=. .venv/bin/python scripts/run_outbox_global.py >> /var/log/farm/outbox.log 2>&1'
```

Confirmar instalação e acompanhar logs:

```bash
crontab -l
tail -f /var/log/farm/outbox.log
```

### 11.1. Gerar o pacote offline da estação

Com a máquina de empacotamento conectada:

    cd /opt/lampp/htdocs/balanca-platform/station
    npm run package:offline

Transfira o diretório gerado em `/opt/lampp/htdocs/balanca-platform/station/dist` para a estação. A primeira
ativação e a sincronização inicial precisam ocorrer com rede disponível. Não
apague o IndexedDB durante uma atualização, pois ele contém as pesagens
pendentes.

### 11.2. Verificar a instalação completa

Execute as verificações abaixo:

    curl -fsS http://127.0.0.1:8000/docs >/dev/null && echo "DeepFarms API OK"
    curl -fsS http://127.0.0.1:8010/healthz && echo "Balanca service OK"
    curl -fsS http://127.0.0.1:8010/readyz && echo "Balanca database OK"
    curl -I http://127.0.0.1:3000
    curl -I http://127.0.0.1:3003
    systemctl status balanca-bridge.service --no-pager

Na estação, confirme: ativação do terminal, login do operador, leitura estável
da Bridge, criação do ticket offline, fila pendente e reprocessamento após
restaurar a rede.

### 12. Parar os processos de desenvolvimento

O que faz: encerra a API e os servidores Next.js iniciados por este workspace.

```bash
# mata processo na porta
lsof -i :8000
kill 12345

# força kill
lsof -i :8000
kill -9 12345

# mata processos pelo nome
pkill -f "uvicorn|next dev"
```
