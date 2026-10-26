# AGRO-ADMIN-01H2C — Preparação do Laboratório de Homologação

**Data:** 25 de outubro de 2026
**Modalidade:** Implementação controlada e validação estática; nenhum serviço foi iniciado e nenhuma migration foi executada.
**Veredicto:** **NO-GO para inicialização ou migrations** até resolver o blocker Alembic e provisionar PostgreSQL/Redis dedicados.

## 1. Arquivos criados e alterados

Arquivos novos desta fase:

- [`.env.example`](/opt/lampp/htdocs/farm/infrastructure/agro-homologacao/.env.example): modelo de configuração, com placeholders e sem segredos reais.
- [`agro_labctl.py`](/opt/lampp/htdocs/farm/scripts/homologacao/agro_labctl.py): controlador fail-closed com subcomandos separados para preparar configuração, validar o gate, verificar identidade, iniciar cada processo, smoke HTTP, encerrar processos registrados e recusar migrations enquanto houver blocker.
- [`test_agro_labctl.py`](/opt/lampp/htdocs/farm/scripts/homologacao/test_agro_labctl.py): testes unitários do gate e da precedência de variáveis de ambiente.
- Este relatório.

Nenhum arquivo comercial existente foi alterado. O workspace já continha diversas mudanças e arquivos não rastreados anteriores a esta tarefa; foram preservados.

## 2. Arquitetura executável proposta

| Serviço | Endereço local | Configuração/controle |
|---|---|---|
| PostgreSQL dedicado | `127.0.0.1:5433` | Database e usuário descartáveis com prefixo `agro_hml_` ou `deepfarms_hml_`; identidade verificada antes da API. |
| Redis dedicado | `127.0.0.1:6380` | Database 0, senha sintética e marcador de identidade da instância; identidade verificada antes da API. |
| FastAPI 1 e 2 | `127.0.0.1:8001`, `:8002` | Mesmo DB, Redis e diretório exclusivo; `WORKER_ID` individual; sem `--reload`. |
| Backoffice Next.js | `127.0.0.1:3001` | `BACKEND_URL=http://127.0.0.1:8001`; chamadas de browser pelo proxy same-origin. |
| PWA Agro Next.js | `127.0.0.1:3005` | `AGRO_API_INTERNAL_ORIGIN=http://127.0.0.1:8001`; proxy/rewrite local. |
| Storage local | `/tmp/deepfarms-agro-hml-<id>/uploads` | Pasta nova, exclusiva e criada com modo restrito; `STORAGE_BACKEND=local`. |

PostgreSQL e Redis não são provisionados pelo controlador. O controlador também não inicia nem reinicia esses serviços. Eles precisam ser instalados/configurados por procedimento operacional separado, com bind loopback e identidade de homologação demonstrável.

O subcomando `prepare` gera segredos sintéticos e arquivos `api1.env`, `api2.env`, `web.env`, `agro.env` e `manifest.json` sob `config/`, todos com permissão `0600` e diretórios `0700`. A geração só cria uma pasta nova sob `/tmp`; falha se o destino já existir. Segredos não são impressos. Não executei esse subcomando nesta fase, portanto nenhum segredo de laboratório foi materializado.

## 3. Pré-requisitos ainda não disponíveis ou não comprovados

Verificação de presença dos executáveis no host (sem iniciar processos): `psql`, `pg_isready`, `node` e `pnpm` foram encontrados. `redis-cli` e `redis-server` não foram encontrados no `PATH`; a etapa de gate exigirá `redis-cli`. Não foi verificado se PostgreSQL ou Redis estão ativos nem se existem instâncias dedicadas nas portas 5433/6380.

Também permanecem sem comprovação: Database de homologação vazio e isolado, usuário de banco sem acesso comercial, Redis exclusivo, marcador Redis pré-provisionado, ausência de colisão operacional de portas, dependências Next instaladas e aptidão dos endpoints FastAPI para autenticação/cotas com dados sintéticos.

## 4. Resultado do gate de isolamento

O gate implementado valida, sem registrar valores secretos:

- `ENVIRONMENT=staging` e `APP_ENV=staging`;
- substituição explícita de **todas** as variáveis cujos nomes aparecem no `services/api/.env.local` atual; o arquivo é consultado apenas para extrair nomes, nunca para copiar valores;
- DB PostgreSQL apenas em loopback na porta 5433 e nome de database com identificação de homologação; SQLite, host remoto, nomes associados a produção/compartilhamento e destino sem usuário/senha são rejeitados;
- Redis autenticado apenas em loopback na porta 6380;
- `STORAGE_BACKEND=local` e `STORAGE_LOCAL_PATH` exatamente igual à pasta `uploads` da instância;
- ausência de configuração S3/MinIO e de credenciais não vazias de provedores externos, incluindo segredos herdados do ambiente pai;
- fingerprint dos segredos sintéticos contra `manifest.json` criado pelo gerador;
- origens CORS e URLs internas dos frontends limitadas às origens loopback e portas previstas;
- processos de aplicação executados somente após gate, identidade de DB/Redis e porta livre do componente.

**Resultado operacional do gate: NÃO APROVADO ainda.** Os testes unitários aprovam casos de configuração válida e rejeições, mas a configuração não foi gerada e o `redis-cli` não está disponível. O gate não comprova serviço ou database até o pré-requisito estar instalado e a verificação de identidade ser executada. Nenhum segredo ou valor de `.env.local` foi exibido.

O script `scripts/staging/validate_isolation.py` permanece exclusivo do laboratório Docker e não é utilizado.

## 5. Estratégia Alembic e revisão alvo

Foram inspecionados os 416 arquivos de revisão e executados os comandos estáticos `alembic heads --verbose` e `alembic branches` no diretório da API:

- Head apresentado pelo checkout: `20261022_agro_admin_01b1`, com parent `20260926_material_requisition_01g` e branch label exibido como `deepfarms_baseline`.
- Revisão independente intitulada baseline: `baseline_deepfarms_v1`, `down_revision=None`, em `20260908_baseline_deepfarms_v1.py`.
- O histórico apresenta muitos branchpoints/mergepoints. O nome de branch label não foi suficiente para garantir caminho offline até o head atual.

Foi feita geração offline (com URL sintética em `127.0.0.1:5433`; sem conexão de banco):

1. `alembic upgrade deepfarms_baseline@head --sql` percorreu a cadeia histórica desde `001_notas_fiscais` e parou na revisão `8c2e891d6ba9_caderno_campo.py`, que chama `sa.inspect()` sobre a conexão mock de Alembic offline. Portanto, a cadeia completa não produziu SQL revisável em modo offline.
2. `alembic upgrade baseline_deepfarms_v1 --sql` gerou SQL isolado de aproximadamente 11 mil linhas (arquivo temporário `/tmp/agro-admin-01h2c-baseline-only.sql`). Ele cria schema `farms`, tipos, sequences, tabelas, índices, FKs, funções, triggers e políticas RLS; inclui `sessoes_ativas.tenant_id` nullable e `usuario_byok_credenciais`. Não foi executado contra banco.
3. O contrato do baseline, em `migrations/baseline_contract.py`, declara `CONTRACT_STATUS = "NO-GO"` e lista divergências estruturais não resolvidas (incluindo UNIQUE, CHECK, índices, políticas, funções e triggers). O downgrade do baseline remove tabelas, sequences, enums e schema, logo não deve ser tratado como rollback seguro.

**Conclusão Alembic: BLOCKER. Não há revisão aprovada para banco novo e nenhum comando automático de `upgrade` é preparado.** `baseline_deepfarms_v1` é apenas candidato de clean install: embora seu SQL offline seja gerável, o contrato NO-GO impede certificar cobertura funcional/estrutural do banco vazio. `20261022_agro_admin_01b1` não é alvo de criação independente; depende de revisão histórica anterior. O subcomando `migrate` falha fechado com o blocker e não invoca Alembic, mesmo que alguém o execute. Resolver exige fechar o contrato do baseline e provar os objetos da aplicação, ou corrigir as revisões históricas para geração/revisão offline, seguido de autorização específica.

## 6. Scripts preparados

Uso, somente depois do GO e provisionamento:

```bash
python3 scripts/homologacao/agro_labctl.py prepare --root /tmp/deepfarms-agro-hml-<id>
python3 scripts/homologacao/agro_labctl.py gate --root /tmp/deepfarms-agro-hml-<id>
python3 scripts/homologacao/agro_labctl.py identity --root /tmp/deepfarms-agro-hml-<id>
python3 scripts/homologacao/agro_labctl.py migrate --root /tmp/deepfarms-agro-hml-<id>  # falha intencionalmente: BLOCKER
python3 scripts/homologacao/agro_labctl.py start --root /tmp/deepfarms-agro-hml-<id> api1
python3 scripts/homologacao/agro_labctl.py start --root /tmp/deepfarms-agro-hml-<id> api2
python3 scripts/homologacao/agro_labctl.py start --root /tmp/deepfarms-agro-hml-<id> web
python3 scripts/homologacao/agro_labctl.py start --root /tmp/deepfarms-agro-hml-<id> agro
python3 scripts/homologacao/agro_labctl.py smoke --root /tmp/deepfarms-agro-hml-<id>
python3 scripts/homologacao/agro_labctl.py stop --root /tmp/deepfarms-agro-hml-<id>
```

O arquivo `identity` usa `psql` com arquivo temporário de senha modo `0600` (removido ao sair) e `REDISCLI_AUTH`; não inclui credenciais nos argumentos nem na saída. Redis precisa ter previamente o marcador `deepfarms:hml:<id>:identity` com o ID esperado, criado somente no Redis dedicado por quem o provisionar. O lançador está preparado, mas o subcomando `start` falha intencionalmente com BLOCKER Alembic até haver revisão de banco vazio aprovada e registrada em alteração posterior. PIDs seriam registrados por instância; `stop` envia SIGTERM apenas se `/proc/<pid>/cmdline` corresponder ao comando esperado. Ele não encerra serviços de banco/cache e não apaga diretório ou dados.

O subcomando `smoke` consulta health live das duas APIs e HTTP dos dois frontends; não faz mutações de domínio.

## 7. Testes previstos e existentes

O projeto já possui suites reutilizáveis para cadastro/auth (`services/api/tests/unit/core/test_free_registration.py`, testes de identidade 01B2C e `apps/agro/tests/e2e/agro-identity.spec.ts`), clima/cotas (`services/api/tests/unit/test_clima_publico.py`), sincronização de campo (`tests/unit/agricola/test_field_pwa01_offline_sync.py` e testes PWA), mercado/DERAL com fixtures (`apps/agro/tests/e2e/mercado-ptax.spec.ts`, `mercado-precos-reais.spec.ts` e testes API), dashboard/configuração (suites `test_backoffice_agro_01*.py`) e storage (`tests/unit/campo/test_field_pwa04_evidencia_upload.py`). Os E2E do navegador devem ser ajustados para `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3005`; o `playwright.config.ts` atual inicia Next em `:3004`, portanto não é seguro usá-lo no laboratório sem configuração adicional explícita.

Os testes existentes não provam por si só concorrência de cotas entre dois processos FastAPI reais, Redis compartilhado nem failover no laboratório. Esses cenários permanecem na matriz de homologação da 01H2B1 e exigirão ambiente disponível; não são simulados como sucesso nesta preparação. Em `apps/agro/public/sw.js` há pré-cache do app shell, fallback de navegação e cache de assets; módulos Agro persistem alguns dados de leitura em `localStorage`. Não foi encontrado mecanismo de fila de mutações/background sync na PWA Agro. Portanto, o teste real desta PWA deve cobrir app shell e dados de leitura já armazenados offline; não deve afirmar sincronização posterior de alterações que não são enfileiradas. Sincronização de campo do app Campo é fluxo separado e não comprova sync no Agro.

O teste existente de cadastro `test_free_registration.py` escolhe `TEST_DATABASE_URL` ou `DATABASE_URL` quando encontra PostgreSQL; não deve ser executado até ser adaptado para URL temporária explicitamente SQLite ou DB dedicado. Ele não foi executado nesta fase.

Testes executados nesta fase: `cd services/api && .venv/bin/pytest ../../scripts/homologacao/test_agro_labctl.py -q` — **12 passaram**. Cobrem configuração segura, rejeição de DB compartilhado/SQLite/Redis remoto/S3/credenciais de provedor, origem frontend inválida, precedência de env do processo sobre `.env.local`, remoção de segredos herdados no ambiente Next e recusa fechada dos subcomandos de migration e inicialização. `py_compile` do controlador e teste passou; `.venv/bin/ruff check` nos dois arquivos Python passou; `--help` foi inspecionado.

Não foram executados testes que possam usar PostgreSQL configurado, testes E2E que iniciem Next, testes de integração com Redis, migrations, builds ou servidores. Typecheck/build não se aplicam às mudanças (somente Python/documentação/configuração) e podem escrever artefatos Next já presentes no workspace.

## 8. Procedimento de inicialização proposto

1. Obter autorização para resolver e executar uma fase posterior; este documento não aprova iniciar serviços.
2. Instalar/identificar Redis e provisionar Redis exclusivo em `127.0.0.1:6380`; provisionar PostgreSQL exclusivo em `127.0.0.1:5433`, database novo e usuário restrito. Não reutilizar instância lógica comercial, RDS ou Redis comercial.
3. Gerar configuração em diretório novo sob `/tmp` com `prepare`; conferir permissões e IDs sem imprimir segredos. Provisionador registra marcador de identidade no Redis dedicado.
4. Executar `gate` e `identity`. Qualquer variável não sobrescrita, host divergente, fallback SQLite, credencial externa, configuração S3, colisão ou identidade não comprovada significa NO-GO.
5. Resolver o BLOCKER Alembic e aprovar revisão exata. Nesta preparação `migrate` fica bloqueado; não substituir por `alembic upgrade heads`.
6. Após autorização específica de migration, aplicar somente revisão aprovada ao banco descartável e conferir schema/version.
7. Iniciar API1/API2, depois Backoffice e PWA pelos subcomandos. Validar `smoke` antes dos testes de domínio.
8. Executar E2E somente com dados sintéticos, providers mockados e Redis/DB confirmados como dedicados.

## 9. Procedimento de descarte

`stop` encerra somente processos de aplicação que tenham PID registrado na instância e cuja linha de comando ainda corresponda ao tipo esperado. PostgreSQL/Redis ficam fora da responsabilidade do script. Depois de coletar logs sanitizados, o operador deve parar as instâncias de banco/cache usando o gerenciador com que foram provisionadas e decidir retenção/descarte do database e da pasta `/tmp/deepfarms-agro-hml-<id>`. Não há comando de remoção automática de dados.

## 10. Bloqueadores e riscos

- **BLOCKER Alembic:** geração offline da cadeia baseline até head falha numa revisão histórica dependente de inspection; contrato baseline continua explicitamente NO-GO.
- **BLOCKER Redis:** `redis-cli`/`redis-server` não estão disponíveis no PATH verificado e não há serviço dedicado comprovado.
- **BLOCKER PostgreSQL:** binários de cliente estão presentes, mas não há instância/database dedicado comprovado.
- **Risco de alteração local preexistente:** o `.env.local` contém nomes de variáveis de credenciais e endpoint de operação; o gate exige overrides e não revela valores. Alterações futuras nesse dotenv adicionam nomes automaticamente ao conjunto exigido.
- **Risco de browser tests:** Playwright Agro inicia Next em porta 3004 por padrão; não executar no laboratório sem configuração que desabilite o webServer automático e use 3005.
- **Limite de offline:** PWA Agro mantém app shell e caches de leitura; não há fila/sincronização de mutações offline comprovada no código inspecionado.
- **Risco multi-processo:** throttle de heartbeat permanece em memória por processo; alternância pode aumentar updates SQL. Cotas climáticas dependem de Redis compartilhado real; unit tests/mocks não provam a atomicidade operacional de dois processos.
- **Risco de shutdown:** somente os PIDs iniciados pelo controlador serão sinalizados; serviços auxiliares não são encerrados automaticamente, por desenho.

## 11. Veredicto GO / NO-GO

**NO-GO para iniciar laboratório, executar migrations ou testes E2E integrados.** Os artefatos de preparação e testes unitários do gate estão prontos, mas faltam serviços dedicados comprovados e a estratégia Alembic não tem alvo seguro aprovado. Após fechar esses blockers e obter autorização específica, o plano poderá avançar sem Docker, S3 ou MinIO.

**Limites desta fase cumpridos:** nenhum serviço iniciado; nenhuma migration ou deploy executado; nenhuma configuração de produção alterada; nenhum commit, push ou merge realizado. Encerrar aqui e aguardar autorização.
