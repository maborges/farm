# AGRO-ADMIN-01H2B1 — Replanejamento da Homologação Sem Docker

**Data:** 25 de outubro de 2026
**Modalidade:** Auditoria estática e replanejamento; nenhum serviço inicializado e nenhuma migration executada.
**Status:** Plano proposto; execução depende dos pré-requisitos e do GO descritos abaixo.

## Sumário executivo

O repositório contém artefatos Docker/MinIO para um laboratório futuro, mas não são necessários para homologar o Agro. A operação local documentada inicia FastAPI e Next.js como processos do host. A configuração local da API seleciona storage `local`; o serviço grava em disco sob `STORAGE_LOCAL_PATH`.

O bloqueio principal é o isolamento de dados: a configuração local existente aponta para um PostgreSQL compartilhado, identificado em documentação existente como banco local de desenvolvimento/teste. Não deve ser reutilizado pelo laboratório. Não há evidência nesta auditoria de PostgreSQL e Redis dedicados, nem de serviços ativos. Ambos precisam ser provisionados e verificados antes de executar qualquer processo. Nenhum segredo ou endereço de produção deve ser copiado para os arquivos do laboratório.

O grafo Alembic foi consultado estaticamente com `alembic heads` e `alembic branches`: existe um único head visível, `20261022_agro_admin_01b1`, rotulado `deepfarms_baseline`, e vários branchpoints/mergepoints no histórico. Isso atualiza a afirmação de 01H2A de que havia dois heads independentes. Um único head não prova, por si só, que todas as revisões sejam seguras para um banco vazio. Antes da primeira migration, é obrigatório auditar o caminho completo do head e gerar/revisar SQL offline contra o alvo isolado. Não executar `upgrade heads` nem migrations nesta fase.

## 1. Inventário do ambiente atual

| Componente | Evidência no repositório | Como funciona / estado conhecido |
|---|---|---|
| FastAPI | `services/api/main.py`, `services/api/start_server.sh`, README | Execução documentada em `services/api` por `./start_server.sh`; manualmente `./.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000`. Para laboratório, usar bind `127.0.0.1` e sem `--reload` em cada processo independente. Disponibilidade do executável/serviço no host não foi verificada. |
| Backoffice Next.js | `apps/web/package.json` | `pnpm --filter web dev -- --hostname 127.0.0.1 --port 3001` é a forma proposta; script existente `dev` usa `next dev --webpack` e porta padrão 3000, portanto a porta deve ser fornecida no comando. `BACKEND_URL` é usado em Server Components; chamadas do navegador passam pelo proxy same-origin. |
| PWA Agro | `apps/agro/package.json`, `apps/agro/next.config.ts` | `pnpm --filter agro dev -- --hostname 127.0.0.1 --port 3005` é a forma proposta; script existente fixa `-p 3004`, então na execução proposta deve ser usado `pnpm --dir apps/agro exec next dev --webpack --hostname 127.0.0.1 --port 3005` ou um processo com `PORT=3005` se suportado pelo script. O rewrite usa `AGRO_API_INTERNAL_ORIGIN` ou, em dev, `127.0.0.1:8000`. |
| PostgreSQL | `core/config.py`, `core/database.py`, `.env.local` | API utiliza SQLAlchemy async, `asyncpg` e schema `farms`; `DATABASE_URL` seleciona o alvo. Sem PostgreSQL válido, o código cai para SQLite local, que não serve para estes testes multi-processo. A configuração presente não é isolada e fica proibida para o laboratório. |
| Redis | `core/config.py` e serviços de cache/cotas/configuração | `REDIS_URL`, default `redis://localhost:6379/0`. Redis é usado por cotas climáticas, caches/invalidação Pub/Sub e rate limits com comportamentos de fallback diferentes. Não há evidência de instância dedicada ativa. |
| Storage | `core/services/storage_service.py`, `core/config.py` | `STORAGE_BACKEND=local`; `save_blob` cria diretórios e grava bytes em `STORAGE_LOCAL_PATH`, `read` lê e `delete` remove. O caminho configurado no `.env.local` é `/tmp/agrosaas_uploads`; laboratório deve fornecer diretório exclusivo novo. |
| Alembic | `services/api/alembic.ini`, `migrations/env.py` | O env importa `DB_URL` de `core.database`, registra os models e garante schema `farms`; `alembic heads` reportou um head no estado do checkout. A configuração de ambiente deve apontar explicitamente para o banco descartável dedicado. |
| URLs/proxy | `apps/web/src/lib/runtime-config.ts`, rotas `api/v1`, `apps/agro/next.config.ts` | Backoffice SSR usa `BACKEND_URL`, default `127.0.0.1:8000`; proxy do Web também possui fallbacks com `host.docker.internal` (legado, desnecessário no host). Browser usa paths same-origin. Agro usa rewrite para origem interna da API. |

### Portas e URLs propostas

| Serviço | Bind host | URL |
|---|---:|---|
| PostgreSQL homologação | `127.0.0.1:5433` | `postgresql+asyncpg://<user>:<secret>@127.0.0.1:5433/<db>` |
| Redis homologação | `127.0.0.1:6380` | `redis://:<secret>@127.0.0.1:6380/0` |
| FastAPI 1 | `127.0.0.1:8001` | `http://127.0.0.1:8001` |
| FastAPI 2 | `127.0.0.1:8002` | `http://127.0.0.1:8002` |
| Backoffice | `127.0.0.1:3001` | `http://127.0.0.1:3001` |
| Agro PWA | `127.0.0.1:3005` | `http://127.0.0.1:3005` |

O bind é loopback-only. Se os frontends forem acessados através de seus proxies Next, CORS não deve ser necessário para esses fluxos: o navegador chama a mesma origem e Next encaminha ao backend. Se algum fluxo chamar a API diretamente do navegador, `http://localhost:3005` e `http://127.0.0.1:3005` precisam ser considerados separadamente em CORS; manter uma única origem canônica por teste evita ambiguidade.

## 2. Reclassificação dos achados 01H2A

| Achado anterior | Classe no laboratório sem Docker | Reavaliação |
|---|---|---|
| CORS não incluía porta 3005 | **Pendente de confirmação** | Com chamadas same-origin via rewrite/proxy, não bloqueia o fluxo normal. Só é aplicável se o navegador chamar a API diretamente. Confirmar no cenário E2E qual caminho está ativo antes de qualquer ajuste. Não alterar CORS por causa do Compose. |
| Variáveis MinIO/S3: `S3_BUCKET_NAME` vs `S3_BUCKET`, ausência de `STORAGE_BACKEND` | **Aplicável apenas ao laboratório Docker** | Irrelevante para esta homologação: usar `STORAGE_BACKEND=local` e diretório próprio; não configurar endpoint, bucket ou credenciais S3/MinIO. |
| `BACKEND_URL`/`AGRO_API_INTERNAL_ORIGIN` ausentes no Compose | **Aplicável apenas ao laboratório Docker** | No host, devem apontar a origens loopback dos processos selecionados. Para Backoffice, `BACKEND_URL=http://127.0.0.1:8001`; para Agro, `AGRO_API_INTERNAL_ORIGIN=http://127.0.0.1:8001`. Validar se Web/Agro acessam a API por proxy ou diretamente. |
| CORS/origens Docker | **Aplicável apenas ao laboratório Docker**, exceto acesso direto do browser | As portas e hostnames do compose não devem ser transplantados automaticamente. Necessidade de CORS em 3005 continua pendente conforme o fluxo real de chamadas. |
| Grafo Alembic com dois heads / recomendação `upgrade heads` | **Pendente de confirmação** | Inspeção atual mostra um head: `20261022_agro_admin_01b1` (branch label `deepfarms_baseline`) e vários branchpoints/mergepoints. A alegação de dois heads do 01H2A está desatualizada para o checkout atual. Auditar revisões ancestrais e efeitos em banco vazio; não usar `upgrade heads` sem essa decisão. |
| Throttling de heartbeat em memória | **Aplicável ao ambiente atual** | `SessionHeartbeatMiddleware` usa `_heartbeat_cache` em memória por processo e janela de 300s. Dois processos não compartilham a cache; requisições alternadas podem produzir updates extras no PostgreSQL. É conhecido e deve ser observado, sem migração para Redis no escopo do plano. |
| Gate de isolamento do staging | **Aplicável apenas ao laboratório Docker** | `scripts/staging/validate_isolation.py` permite hosts locais/container e exige variáveis de MinIO. Não é gate apropriado para este laboratório. Criar antes da execução um checklist/validador equivalente sem Docker, que aceite somente loopback para DB/Redis, diretório exclusivo e recuse URLs/hosts identificados como produção. Não reutilizar o script Docker sem adaptação. |

## 3. Arquitetura proposta para laboratório sem Docker

Executar tudo como processos locais dedicados, com dependências isoladas por porta, database e diretório. Não reaproveitar banco, Redis, storage, `.env.local` nem secrets de execução comercial.

```text
Navegador
 ├─ Backoffice http://127.0.0.1:3001 ── proxy/SSR ─┐
 └─ Agro PWA   http://127.0.0.1:3005 ── rewrite ──┤
                                                  ├─ API 1 :8001
                                                  └─ API 2 :8002
                                                       │
                               PostgreSQL isolado :5433 ├─ Redis isolado :6380
                               Storage local dedicado em /tmp/deepfarms-agro-hml-<id>/uploads
```

As duas APIs compartilham somente o PostgreSQL e o Redis dedicados do laboratório. Para o teste determinístico de alternância, configurar proxies/clientes ou chamadas explícitas para alternar entre 8001 e 8002. Cada processo precisa de `WORKER_ID` distinto, se o código/telemetria consumir essa variável. Não foi encontrada necessidade de Docker para este desenho.

## 4. Variáveis e isolamento

Criar arquivos efêmeros fora do repositório, com permissões restritas, por exemplo `/tmp/deepfarms-agro-hml-<id>/api1.env`, `api2.env`, `web.env` e `agro.env`. Usar valores aleatórios exclusivos de teste. Não copiar `.env.local`, `.env.production`, configurações de servidor ou credenciais de provedores.

Variáveis mínimas:

```dotenv
ENVIRONMENT=staging
APP_ENV=staging
DATABASE_URL=postgresql+asyncpg://<user>:<senha-de-teste>@127.0.0.1:5433/<db-nova>
REDIS_URL=redis://:<senha-de-teste>@127.0.0.1:6380/0
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=/tmp/deepfarms-agro-hml-<id>/uploads
JWT_SECRET_KEY=<segredo-aleatorio-exclusivo>
PLATFORM_CREDENTIALS_MASTER_KEY=<chave-fernet-de-teste>
INTEGRATIONS_SECRET_KEY=<segredo-aleatorio-exclusivo>
```

Adicionar `BACKEND_URL=http://127.0.0.1:8001` para SSR/proxy do Backoffice e `AGRO_API_INTERNAL_ORIGIN=http://127.0.0.1:8001` para o rewrite do Agro. O frontend não deve usar hostname `host.docker.internal`. Nenhum secret real de OpenWeather, WeatherAPI, pagamento, TARA, Sankhya ou outro provedor: usar stubs/mocks ou chamadas explicitamente desativadas. Se `ENVIRONMENT=staging` exigir chaves mestras válidas, gerar apenas chaves criptográficas descartáveis; dados de teste criptografados não devem ser exportados ao ambiente comercial.

Pré-condições de rede: DB e Redis devem escutar somente em `127.0.0.1` nas portas definidas. Confirmar a identidade do DB por nome, host, porta e `SELECT current_database(), current_user, inet_server_addr()` antes de qualquer migration; não registrar senha na saída. A conexão recusada ou resposta de identidade divergente implica NO-GO.

## 5. Estratégia segura para Alembic

1. Verificar o checkout e registrar `alembic heads --verbose` e `alembic branches` (já consultados nesta auditoria). Head atual único: `20261022_agro_admin_01b1`; há múltiplos branchpoints/mergepoints ancestrais.
2. Revisar do head até as raízes todo `down_revision`, `branch_labels`, `depends_on`, operações de DDL/DML, SQL raw, referências externas, schemas e pressupostos de dados preexistentes. Em especial, confirmar que o baseline é realmente autocontido em banco vazio, e não apenas nomeado como baseline.
3. Criar banco vazio dedicado e usuário sem acesso a qualquer outro database; não usar o database comercial ou de desenvolvimento compartilhado.
4. Com `DATABASE_URL` injetada explicitamente para o alvo dedicado, gerar SQL offline da revisão escolhida usando `alembic upgrade <revision-alvo> --sql` (ou intervalo equivalente) e revisar o SQL e o destino. SQL offline é revisão, não prova de execução.
5. Aprovar uma única revisão alvo canônica após revisão técnica. `alembic upgrade heads` não é recomendado automaticamente; embora haja um head reportado agora, o alvo deve ser explícito para evitar mudança silenciosa do grafo.
6. Nesta fase nenhuma migration deve ser executada. A primeira execução exige autorização específica após o plano, confirmação visual da identidade do banco e backup/possibilidade de descarte do database de homologação.

## 6. Plano de testes E2E

Executar somente depois do GO de infraestrutura e migrations. Usar contas, dados, tokens e credenciais sintéticos.

| Cenário | Verificações principais |
|---|---|
| Cadastro gratuito e autenticação | Cadastro com dados sintéticos; limites de tentativas; login/logout; cookies/CSRF; sessão gravada apenas no banco de homologação. |
| Sessões e heartbeat | Cookie/token válido, heartbeat autenticado, rejeição anônima, atualização de `ultimo_heartbeat`; frequência de update e comportamento com atividade real. |
| Dois processos FastAPI | Enviar requisições alternadas diretamente a :8001 e :8002; verificar mesmo estado no PostgreSQL/Redis, identificação distinta do worker e ausência de arquivos compartilhados acidentais. |
| Cotas climáticas concorrentes | Com provedor stub e limite baixo, disparar chamadas concorrentes contra ambos os workers; confirmar reserva atômica única no Redis, limite nunca excedido e rollback em falha simulada. Sem credencial real ou tráfego faturável. |
| Redis indisponível | Interromper apenas a instância dedicada durante teste controlado; verificar fail-safe de cotas, fallback documentado de rate-limit/cache e degradação reportada no dashboard. Reiniciar e confirmar recuperação. Não parar Redis compartilhado. |
| Configurações e feature flags | Ler flags públicas e administrativas, alterar valor de teste, observar invalidação por Pub/Sub nos dois processos e persistência no DB. |
| Mercado e snapshots DERAL | Consultar fixture/snapshot versionado, validar proveniência, datas, idempotência e persistência. Bloquear ingestão externa durante E2E ou usar fixture para evitar dependência e carga não controlada. |
| Bibliotecas globais | CRUD/leitura de itens globais e isolamento entre usuários/tenants de teste; permissões administrativas e efeitos somente no database de homologação. |
| Dashboard e matriz de homologação | Abrir dashboard, validar indicadores dos dois processos, status Redis, sessões, cotas, avisos e texto de evidência sem afirmar integração real não testada. |
| PWA offline e sincronização | Instalar/abrir PWA, retirar rede do navegador, criar operações offline, restaurar conexão e validar sincronização, deduplicação/idempotência e resolução de conflitos. |
| Storage local | Upload, read e delete de arquivo sintético; comprovar caminho sob diretório exclusivo e que nada aparece no diretório comercial. |

## 7. Riscos e pré-requisitos

- **Bloqueador:** provisionar PostgreSQL novo, dedicado, loopback-only; garantir que não é RDS nem banco compartilhado. A configuração existente não pode ser reaproveitada.
- **Bloqueador:** provisionar Redis novo, dedicado, loopback-only, com autenticação exclusiva de teste; fallback não substitui teste de concorrência real.
- **Bloqueador:** diretório local de uploads novo e vazio, com espaço e permissões adequadas; não compartilhar o `/tmp/agrosaas_uploads` atual.
- **Bloqueador:** chave JWT, chave mestra Fernet e segredos de integração sintéticos; desativar todos os provedores pagos/reais.
- **Bloqueador:** auditoria de migrations do banco vazio; um head único não demonstra que baseline não depende de dados legados.
- **Risco conhecido:** throttle de heartbeat é local ao processo. Em dois workers haverá updates redundantes, potencialmente aumentando escrita; validar impacto e limites do pool.
- **Risco conhecido:** várias rotinas Redis podem ter fallback com semânticas distintas; caso Redis falhe, resultado esperado deve ser registrado por domínio, não generalizado.
- **Pendente:** conferir disponibilidade/versões de Python, dependências, Node/pnpm, PostgreSQL e Redis no host. Esta auditoria não verificou instalação nem estado de execução.
- **Pendente:** conferir as rotas reais de mercado/snapshots e modo de fixture para garantir que E2E não invoque provedores externos.

## 8. Procedimento de inicialização proposto (não executado)

1. Criar diretório novo `/tmp/deepfarms-agro-hml-<id>` e subdiretório `uploads`; criar arquivos env de teste com permissões restritas. Não editar arquivos do repositório nem copiar `.env.local`.
2. Provisionar PostgreSQL e Redis dedicados no host, limitados a loopback e às portas 5433/6380. Criar database e usuários próprios; não compartilhar instância lógica comercial, ainda que a porta local seja diferente.
3. Verificar `pg_isready`, `redis-cli` autenticado e a identidade de database/usuário/host; verificar portas com `ss`/`lsof`. Confirmar que 3001, 3005, 8001, 8002, 5433 e 6380 não colidem.
4. Executar o gate pré-boot proposto (somente leitura): conferir allowlist de hosts loopback, rejeitar referências conhecidas de produção, exigir `ENVIRONMENT=staging`, chaves exclusivas, `STORAGE_BACKEND=local`, diretório novo e ausência de S3/MinIO/provedores reais. O gate atual em `scripts/staging/validate_isolation.py` não se aplica.
5. Fazer a revisão de migration descrita na seção 5; obter aprovação para execução antes de qualquer `upgrade`.
6. Após autorização, inicializar uma instância dedicada de Redis e PostgreSQL, aplicar a revisão Alembic explícita ao banco novo, verificar schema/version e iniciar API 1 em `127.0.0.1:8001` e API 2 em `127.0.0.1:8002`, cada uma com seus envs e worker ID distintos, usando o mesmo DB/Redis/storage de homologação.
7. Iniciar Backoffice em `127.0.0.1:3001` com `BACKEND_URL` e PWA em `127.0.0.1:3005` com `AGRO_API_INTERNAL_ORIGIN`; confirmar requests via proxy e não abrir acesso público.
8. Rodar smoke checks não mutantes (health/docs, leitura de feature flags, status de conexão); só então executar os E2E aprovados.
9. Ao encerrar, parar somente os processos e serviços identificados como homologação; arquivar logs sem tokens/segredos e reter ou eliminar dados de teste conforme decisão operacional.

Comandos indicativos para os processos da aplicação, após aprovação e com variáveis isoladas já exportadas:

```bash
cd services/api
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8002
cd apps/web && pnpm exec next dev --webpack --hostname 127.0.0.1 --port 3001
cd apps/agro && pnpm exec next dev --webpack --hostname 127.0.0.1 --port 3005
```

Os comandos são proposta documental, não foram executados. Cada API deve receber configuração isolada via ambiente do processo. Como o Pydantic carrega `services/api/.env.local`, variáveis de ambiente explicitamente exportadas precisam sobrepor esses valores; antes da execução, verificar essa precedência e abortar se qualquer processo puder herdar o endpoint existente.

## 9. Critérios GO / NO-GO

### GO para iniciar o laboratório

- PostgreSQL e Redis dedicados foram provisionados e confirmados como loopback-only; os endpoints não correspondem a operação comercial nem a produção.
- Database novo, usuário restrito e storage vazio exclusivo foram confirmados por identificadores e caminhos.
- Não há segredos reais de provedores, JWT, Fernet, billing ou integração; todas as chamadas externas pagas estão desativadas ou stubadas.
- Revisão do caminho Alembic e SQL offline concluiu que o alvo explícito cria o schema requerido em banco vazio; aprovação registrada para aplicar migrations.
- Portas livres e todos os processos usam `127.0.0.1`; gate local sem Docker passou.
- URLs internas dos frontends apontam somente para API 1/2 do laboratório e o fluxo CORS/proxy foi definido.

### NO-GO

- Qualquer URL/credencial de produção ou database compartilhado permanece em uso ou não pode ser identificado.
- Redis não é dedicado, fallback foi confundido com prova de concorrência, ou não há autenticação/isolamento suficiente.
- `STORAGE_LOCAL_PATH` aponta para caminho comercial/compartilhado, ou S3/MinIO está configurado.
- Há dúvida sobre migration alvo, múltiplos caminhos não auditados, ou SQL offline contém pressuposto de schema/dados ausentes.
- Portas públicas, colisão de portas, proxies apontando para API/hosts fora do laboratório ou secrets reais de provedores.
- A aplicação cai silenciosamente para SQLite ou algum E2E gera tráfego real de cobrança/provedor.

**Resultado desta fase:** somente plano estático concluído. **Não há autorização implícita para provisionar serviços, executar migrations, iniciar APIs/frontends ou rodar E2E. Aguardar autorização explícita para a próxima fase.**
