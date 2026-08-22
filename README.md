# AgroSaaS - Plataforma de Gestão Rural Modular

Sistema avançado para gestão de fazendas, focado em produtividade, isolamento de dados (multi-tenancy) e interface de alta performance.

## Leitura Inicial

A ordem oficial de leitura para agentes de IA vive em **`docs/architecture/ai-bootstrap.md`** — não repetida aqui.

Utilize português (pt-BR) para documentos e interações com o usuário, com acentuação correta e linguagem não técnica nas explicações.

> Cópias espelhadas em `apps/web/` existem para compatibilidade histórica. A fonte oficial fica na raiz do repositório — confirme o caminho ativo antes de editar (ver `CONTEXTO.md` → "Sinais de Atenção").

## Arquitetura do Sistema

Monorepo dividido em:
- **apps/web**: Interface Next.js 16 com shadcn/ui e Zustand.
- **apps/campo**: PWA de campo offline-first, extensão oficial do Caderno de Campo.
- **apps/balanca**: PWA de estação de balança offline-first (pesagem de carga e animais), desacoplado dos demais módulos.
- **services/api**: Backend Python com FastAPI, SQLAlchemy e PostgreSQL.
- **packages/zod-schemas**: Contratos compartilhados (Shared Schemas).2

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

Detalhamento de cada feature, decisões e histórico de implementação: `docs/CHANGELOG.md` (não faz parte da leitura padrão — consulte apenas quando precisar entender por que algo foi construído de determinada forma).

## Conceitos-Chave: Propriedade, Talhão e Unidade Produtiva

- **Propriedade / Unidade Produtiva**: cadastro mestre da fazenda (nome, tipo, documentos, endereço, áreas, geometria).
- **Área Rural / Talhão**: divisão física dentro da propriedade — base para solo, caderno de campo, NDVI etc.
- **Production Unit da safra**: vínculo `cultivo + área + participação` dentro de uma safra específica.
- **Fluxo**: cadastra-se a propriedade → gera/organiza talhões → a safra vincula em `production-units` → módulos agrícolas operam sobre esses vínculos.

Regras completas de fronteira territorial/fundiária: `docs/architecture/agrosaas-domain-map.md`.

## Referência Oficial FIELD-CORE

Arquitetura consolidada do Caderno de Campo (governança, cadeia documental, papel do PWA): `docs/architecture/field-core-final-governance.md`.

## Como Executar

Execute cada bloco em um terminal separado, mantendo o backend ativo antes dos workers e das aplicações web.

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

O que faz: executa o scheduler de automações do AgroSaaS usando o virtualenv oficial da API.

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
cd /opt/lampp/htdocs/farm/apps/balanca
pnpm run dev
```

### 9. Iniciar a ponte eletrônica da balança

O que faz: conecta o indicador físico ou simulador à aplicação da balança pela porta `8321`.

```bash
cd /opt/lampp/htdocs/farm/tools/balanca-bridge
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edite config.yaml com a porta serial ou host/porta TCP do indicador.
./.venv/bin/python -m balanca_bridge.main
```

Para usar o simulador em vez do indicador físico:

```bash
cd /opt/lampp/htdocs/farm/tools/balanca-bridge
./.venv/bin/python simulator.py
```

### 10. Executar o Outbox global no cron

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

### 11. Parar os processos de desenvolvimento

O que faz: encerra a API e os servidores Next.js iniciados por este workspace.

```bash
pkill -f "uvicorn|next dev"
```
