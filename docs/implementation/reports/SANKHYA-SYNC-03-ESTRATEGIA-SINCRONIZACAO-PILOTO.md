# SANKHYA-SYNC-03 - Auditoria da Estrategia de Sincronizacao do Piloto

## Escopo auditado

Auditoria documental da estrategia operacional de sincronizacao Sankhya x AgroSaaS para o piloto de cafe exportador, sem implementacao de nova sincronizacao, sem alterar endpoints, sem criar jobs, sem scheduler novo e sem modificar Domain Events ou Outbox.

### Componentes auditados

- `SankhyaCanonicalAdapter`
- `SankhyaGatewayAuthService`
- `SankhyaSyncService`
- `SankhyaWSClient`
- modelos persistidos Sankhya
- Integration Jobs e Integration Policies
- rotas existentes
- scheduler e worker genericos do ecosistema
- checkpoints, paginação, retry e reprocessamento
- observabilidade
- eventos de dominio
- Outbox
- testes e documentacao

## Base encontrada

### Sankhya ja existente

- Router com configuracao, teste de conexao, status, health, logs, jobs, timeline, diagnostico e syncs manuais. Referencia: `services/api/integracoes/sankhya/routers/__init__.py`
- Auth Gateway com chamada a `/authenticate`, cache de token, mascaramento e diagnostico sanitizado. Referencia: `services/api/integracoes/sankhya/services/auth_service.py`
- Sync service com configuracao, teste de conexao, logs, status, health, jobs, timeline e upsert das entidades ja suportadas. Referencia: `services/api/integracoes/sankhya/services/sync_service.py`
- WS client generico para envelopes SOAP e chamadas ao Gateway. Referencia: `services/api/integracoes/sankhya/services/sync_service.py`
- Servicos de NFe e financeiro com exportacao/importacao, usando jobs oficiais. Referencia: `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- Adapter oficial que materializa provider, credenciais, configuracao, features, policies, health e eventos. Referencia: `services/api/integracoes/sankhya/services/canonical_adapter.py`

### Infra de integracoes ja existente

- `IntegrationScope`, `IntegrationStatus`, `IntegrationSyncMode`, `IntegrationJobStatus`, `IntegrationJobTrigger`, `IntegrationHealthStatus`
- `TenantIntegracao`, `IntegrationCredential`, `IntegrationVersion`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`
- `DomainEventOutbox` e `DomainEventOutboxService`
- `DomainEventOutboxRelay` e `DomainEventOutboxWorker`
- `AlertSchedulerService` e `RecommendationSchedulerService` como padroes reutilizaveis de orquestracao

### Testes e documentacao existentes

- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py`
- `services/api/tests/unit/events/test_domain_event_outbox.py`
- `services/api/tests/unit/events/test_outbox_worker.py`
- `services/api/integracoes/sankhya/README.md`

## Classificacao por componente

### Scheduler

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Scheduler reutilizavel | EXISTE PARCIALMENTE | `sync_interval` em `SankhyaConfig`; `proximo_sync` derivado no status; `trigger_expression` em `IntegrationSyncPolicy`; scheduler oficial em Alert/Recommendations | Reutilizar o padrao de orquestracao existente no core de integracoes e os calculos de proximo ciclo ja existentes | Nao existe scheduler Sankhya dedicado; se a operacao exigir execucao automatica real, a integracao com um orquestrador externo ainda precisara ser ligada |
| Execucao manual | EXISTE E ATENDE | Rotas `/config/testar-conexao`, `/sync/pessoas`, `/sync/produtos`, `/sync/completo`, `/nfe/exportar`, `/nfe/importar-entrada`, `/financeiro/exportar-contas-pagar`, `/financeiro/exportar-contas-receber`, `/financeiro/importar` | Reutilizar integralmente | Nenhuma obrigatoria nesta fase |
| Execucao agendada | EXISTE PARCIALMENTE | README sugere Celery Beat; `IntegrationSyncMode.AGENDADO` existe; `RecommendationSchedulerService` e `AlertSchedulerService` mostram padrao de scheduler interno | Reutilizar apenas o contrato de politica e o padrao de scheduler de outros dominios | Falta ligar Sankhya a um scheduler real; nao criar um novo agora |
| Controle por tenant | EXISTE E ATENDE | `tenant_id` em config, jobs, logs, health e rotas via `Depends(get_tenant_id)` | Reutilizar | Nenhuma |
| Controle por Unidade Produtiva | NAO EXISTE | Testes de guardrail confirmam que Sankhya nao usa `unidade_produtiva_id` como escopo de configuracao | Manter como tenant scoped | Se futuramente houver filiais/estabelecimentos fiscalmente distintos, reavaliar escopo |

### Jobs

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Jobs existentes | EXISTE E ATENDE | `IntegrationJob` com `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`, `RETRYING`; `SankhyaSyncLog` como legado de audit trail | Reutilizar `IntegrationJob` como camada oficial e manter `SankhyaSyncLog` para compatibilidade | Nenhuma para o piloto |
| Reprocessamento | EXISTE PARCIALMENTE | `run_once` no Outbox worker; rotas manuais de sync; listas de logs/jobs com filtros | Reutilizar execucao manual por rota e o worker do Outbox como padrao de reexecucao de eventos | Falta um comando/rota especifica de reprocessamento por periodo/documento para Sankhya |
| Execucao incremental | EXISTE PARCIALMENTE | `ultimo_sync` em `SankhyaConfig`; `proximo_sync` calculado; filtros `tipo`/`status` nos logs | Reutilizar como base temporal | Falta checkpoint de cursor/continuation token para incremental fino por pagina |
| Execucao completa | EXISTE PARCIALMENTE | `/sync/completo` existe, mas retorna apenas mensagem de fila | Reutilizar como entrada de orquestracao | Falta implementar a semantica real; nesta etapa nao deve ser criada nova estrutura |
| Sincronizacao por dominio | EXISTE E ATENDE PARA O QUE JA ESTA IMPLEMENTADO | Pessoas, produtos, NFe e financeiro estao separados por servico e feature | Reutilizar por feature code | Nenhuma imediata; novos dominios ficam para fase posterior |

### Checkpoints

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Ultima sincronizacao | EXISTE E ATENDE | `SankhyaConfig.ultimo_sync`, `SankhyaSyncLog.started_at/completed_at`, `IntegrationHealth.last_success_at` | Reutilizar como referencia temporal do piloto | Nenhuma |
| Data/hora de execucao | EXISTE E ATENDE | `created_at`, `started_at`, `completed_at`, `finished_at`, `checked_at` em jobs/health/outbox | Reutilizar | Nenhuma |
| Cursor/token de continuacao | NAO EXISTE | Nao ha campo de cursor ou continuation token nos modelos Sankhya | Nao ha o que reaproveitar | Criar apenas se o piloto passar a exigir paginação incremental real |
| Paginacao incremental | EXISTE PARCIALMENTE | Filtros por periodo em NFe/financeiro; `limit`/`skip` nos endpoints de leitura | Reutilizar para cargas por periodo | Falta persistir estado incremental por lote/pagina |

### Paginacao

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Paginacao interna do app | EXISTE PARCIALMENTE | `skip`/`limit` em pessoas/produtos; `limit` em logs/jobs/timeline | Reutilizar para consulta operacional | Nao resolve a paginação do provider, apenas da UI/API local |
| Paginacao do Gateway Sankhya | NAO EXISTE NA BASE AUDITADA | `SankhyaWSClient.executar_ws` monta envelope SOAP generico; chamadas atuais usam `findAll` ou `findByPeriodo` | Reutilizar o client generico | Se o provider exigir paginação, isso sera extensao do proprio consumo, nao novo scheduler |
| Controle de lote | EXISTE PARCIALMENTE | `IntegrationSyncPolicy.batch_size`; `DomainEventOutboxService.claim_batch`; scheduler oficial em outros modulos usa `batch_size` | Reutilizar o padrao de lote | Falta o lote no Sankhya sync em fluxo real, apenas o contrato existe |
| Processamento parcial | EXISTE PARCIALMENTE | Outbox worker trabalha por batches; scheduler de recommendations trabalha por batches | Reutilizar como modelo de orchestracao | Sankhya ainda nao divide carga por lote no fluxo de dados de negocio |

### Idempotencia

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Upsert por chave externa | EXISTE E ATENDE PARA OS DOMINIOS JA IMPLEMENTADOS | `SankhyaPessoa.sankhya_id`, `SankhyaProduto.sankhya_id`, `SankhyaNFe.chave_acesso`, `SankhyaLancamentoFinanceiro.sankhya_id` | Reutilizar integralmente | Novos dominios ainda nao cobertos precisarao de chave externa propria |
| Prevenção de duplicidade | EXISTE E ATENDE | Unique constraints em `sankhya_id` e `chave_acesso`; `IntegrationJob` e `DomainEventOutbox` com unicidade de idempotencia | Reutilizar | Nenhuma |
| Tratamento de existentes | EXISTE E ATENDE | Upsert em `sync_service.py` e `nfe_financeiro_service.py`; credencial rotaciona sem perder snapshot oficial | Reutilizar | Nenhuma |
| Chaves externas do piloto | EXISTE PARCIALMENTE | `CODPARC`, `CODPROD`, `NUMDOC`, `DESDOB`, `CHAVEACESSO` aparecem nas cargas | Reutilizar as chaves ja mapeadas | `CODLOCAL` e `CODEMP` ainda nao possuem tratamento oficial dedicado |

### Retry

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Retry automatico | EXISTE PARCIALMENTE | `DomainEventOutboxService.max_attempts = 5`, `next_attempt_at`, `FAILED`/`DEAD_LETTER`, `backoff` do worker | Reutilizar o retry do Outbox para eventos de dominio | Sankhya sync de negocio nao implementa retry proprio hoje |
| Retry manual | EXISTE PARCIALMENTE | Rotas manuais de sync e worker CLI `run`; `SankhyaSyncService` permite refazer execucao por rota | Reutilizar manualmente para o piloto | Falta uma rota/CLI de reprocessamento especifica por periodo/documento |
| Backoff | EXISTE E ATENDE NO OUTBOX | `mark_failed` ajusta `next_attempt_at`; worker tem `DEFAULT_LOOP_BACKOFF_SECONDS` e max backoff | Reutilizar como padrao de resiliencia | Nao aplicar diretamente em Sankhya sem uma fila/worker dedicada ao dominio |
| Limite de tentativas | EXISTE E ATENDE NO OUTBOX | `max_attempts = 5` e transicao para `DEAD_LETTER` | Reutilizar para eventos | Nada a criar agora |

### Reprocessamento

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Reexecutar sincronizacoes | EXISTE PARCIALMENTE | Rotas manuais de sync; `IntegrationJob` reaproveitado; worker `run_once` no Outbox | Reutilizar como forma de reprocesso manual | Falta uma rotina formal de reprocessamento por entidade/perido/documento |
| Sincronizacao por periodo | EXISTE PARCIALMENTE | NFe e financeiro aceitam `periodo_inicio` e `periodo_fim` | Reutilizar para lotes temporais | Pessoas/produtos nao tem cursor temporal persistido |
| Sincronizacao por entidade | EXISTE E ATENDE PARA O QUE JA EXISTE | Features separadas por pessoas/produtos/nfe/financeiro | Reutilizar | Sem extensao imediata |
| Sincronizacao por documento | EXISTE PARCIALMENTE | `chave_acesso` na NFe, `numero_documento` nos lancamentos | Reutilizar como filtro de reprocesso em fase futura | Falta endpoint/worker dedicado para documento unitario |

### Observabilidade

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Logs | EXISTE E ATENDE | `SankhyaSyncLog`, logs estruturados do adapter, do worker e do relay | Reutilizar | Nenhuma |
| Health | EXISTE E ATENDE | `IntegrationHealth` e `obter_health_detalhado` | Reutilizar | Nenhuma |
| Status | EXISTE E ATENDE | `/status` em Sankhya; status oficial no adapter | Reutilizar | Nenhuma |
| Diagnosticos | EXISTE E ATENDE | `/diagnostico`, `/health`, `/timeline` | Reutilizar | Nenhuma |
| Eventos operacionais | EXISTE E ATENDE | `IntegrationConfigured`, `IntegrationCredentialRotated`, `IntegrationSyncStarted`, `IntegrationSyncCompleted`, `IntegrationSyncFailed`, `IntegrationHealthChanged` | Reutilizar integralmente | Nenhuma |
| Metricas | EXISTE PARCIALMENTE | Outbox metrics e health report existem; Sankhya usa logs/health mas nao tem metricas de dominio adicionais | Reutilizar observabilidade do Outbox | Nao criar novas metricas agora sem demanda operacional comprovada |

### Domain Events

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Eventos atuais atendem a estrategia | EXISTE E ATENDE | Adapter Sankhya publica eventos oficiais de configuracao, credencial, sync e health | Reutilizar sem criar novos eventos | Novos eventos apenas se houver novo dominio ou gatilho comprovado |
| Reuso de eventos | EXISTE E ATENDE | `publish_domain_event_safe` e `DomainEventOutboxService.enqueue` | Reutilizar | Nenhuma |
| Necessidade de eventos novos para o piloto | NAO EXISTE NECESSIDADE COMPROVADA | Os eventos de ciclo de vida cobrem o piloto atual | Nao criar novos eventos | Somente se aparecer checkpoint/cursor/job type novo em fase posterior |

### Outbox

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Outbox necessario nesta fase | EXISTE E ATENDE COMO INFRA E NAO COMO NOVA INICIALIZACAO | `DomainEventOutbox`, `DomainEventOutboxService`, `DomainEventOutboxRelay`, `DomainEventOutboxWorker` | Reutilizar o que ja existe | Nao alterar |
| Outbox para sink de sincronizacao Sankhya | EXISTE PARCIALMENTE | Sankhya ja publica eventos de dominio via helper, mas o transporte principal da sincronizacao e o WS/adapter | Reutilizar apenas para eventos derivados | Nao criar fila nova de Sankhya |
| Justificativa tecnica | EXISTE | Se o fluxo for Sankhya -> AgroSaaS e a persistencia local for a unica saida, o Outbox nao precisa virar novo pipeline de negocio | Reutilizar como protecao de eventos, nao como motor de sync | Manter preparado para fases futuras de eventos de escrita/push |

### Frequencia de sincronizacao

| Item | Situacao | Evidencia | Reuso | Extensao futura |
| --- | --- | --- | --- | --- |
| Sob demanda | EXISTE E ATENDE | Rotas manuais e teste de conexao | Reutilizar integralmente | Nenhuma |
| Manual | EXISTE E ATENDE | POSTs de sync e test connection | Reutilizar integralmente | Nenhuma |
| Agendada | EXISTE PARCIALMENTE | `sync_interval`, `trigger_expression`, padroes de scheduler de outros modulos | Reutilizar como contrato | Falta o agendador real ligado ao Sankhya |
| Automatica | EXISTE PARCIALMENTE | Documentacao menciona Celery Beat, mas nao ha scheduler Sankhya dedicado em execucao real | Reutilizar apenas o padrao conceitual | Nao criar scheduler novo nesta fase |

## Estrategia recomendada para o piloto

### Carga inicial

- Executar manualmente por tenant.
- Primeiro carregar pessoas e produtos.
- Em seguida carregar NFe e financeiro por janela de periodo validada com o negocio.
- Manter a execucao em lote via `IntegrationJob` e `SankhyaSyncLog`.
- Nao usar cursor persistido porque ele nao existe e nao ha prova de necessidade para o piloto inicial.

### Sincronizacao incremental

- Usar `ultimo_sync` como referencia temporal ate existir demanda real de cursor.
- Para NFe e financeiro, preferir janela de periodo.
- Para pessoas e produtos, manter upsert por `sankhya_id` e reexecucao manual/agendada.
- Se houver agendamento, ele deve chamar os endpoints/servicos existentes, nao um novo pipeline.

### Recuperacao apos falha

- Reutilizar `IntegrationJob` com `FAILED` e `RETRYING`.
- Reutilizar retry/backoff do Outbox apenas para eventos de dominio.
- Para sync de negocio, a recuperacao deve ser manual nesta fase.
- Falhas de conexao devem continuar sanitizadas pelo `SankhyaGatewayAuthService.test_connection`.

### Reprocessamento

- Reprocessamento por documento ou periodo deve ser manual e controlado.
- NFe e financeiro ja permitem recorte temporal; isso deve ser o caminho preferencial para reruns.
- Nao criar nova rota de reprocessamento agora.

### Sincronizacao manual

- Deve permanecer como o modo operacional principal do piloto.
- Os endpoints existentes ja cobrem teste de conexao, carga inicial e exportacao/importacao de documentos.
- O backoffice continua apenas como console de observacao, nao como motor principal do cliente.

## Componentes totalmente reutilizaveis

- `SankhyaGatewayAuthService`
- `SankhyaCanonicalAdapter`
- `SankhyaSyncService`
- `SankhyaWSClient`
- `IntegrationJob`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- `IntegrationFeature`
- `SankhyaSyncLog`
- `publish_domain_event_safe`
- `DomainEventOutboxService`
- `DomainEventOutboxRelay`
- `DomainEventOutboxWorker`
- `AlertSchedulerService`
- `RecommendationSchedulerService`
- testes unitarios de auth, teste de conexao, adapter e governanca

## Componentes parcialmente reutilizaveis

- `sync_interval` como contrato de periodicidade
- `proximo_sync` derivado de status
- `IntegrationSyncMode.AGENDADO`
- `IntegrationJobTrigger.SCHEDULED`
- `SankhyaSyncLog` como trilha legada
- `SankhyaConfig.ultimo_sync`
- paginação `limit/skip` na API local
- retry do Outbox como resiliencia de plataforma
- `ComercializacaoCommodity` e NFe/financeiro por periodo para reprocessos seletivos

## Componentes inexistentes

- Scheduler Sankhya dedicado
- Checkpoint/cursor/token persistido para incremental fino
- Reprocessamento formal por documento com comando proprio
- Paginacao do provider Sankhya com stateful continuation token
- Retry de negocio do Sankhya sync separado do Outbox
- Mecanismo de sync por Unidade Produtiva

## Riscos tecnicos

1. Confiar apenas em `ultimo_sync` sem cursor pode causar lacunas se o provider nao garantir janelas consistentes.
2. Usar `findAll` sem paginação do provider pode degradar carga inicial em bases grandes.
3. Reprocessar pessoas/produtos sem filtro de alteracao pode repetir chamadas sem ganho funcional.
4. Misturar retry do Outbox com retry de negocio pode criar falsa sensacao de resiliencia do fluxo Sankhya.
5. Tentar encaixar Sankhya em Unidade Produtiva pode quebrar o escopo de tenant e contrariar os guardrails ja consolidados.
6. Criar scheduler novo agora duplicaria a arquitetura que ja existe no core de integracoes e nos schedulers de alertas/recomendacoes.

## Recomendacao objetiva

Para o primeiro piloto operacional, a estrategia mais segura e:

- `manual first`
- `tenant scoped`
- `upsert based`
- `period based` para NFe e financeiro
- `full refresh` controlado para pessoas e produtos
- `no new scheduler`
- `no new outbox pipeline`
- `reuse oficial jobs, health and events`

Essa combinacao entrega o piloto sem duplicar arquitetura e sem introduzir checkpoints artificiais antes de haver necessidade real.

## Recomendações para a proxima etapa

- Formalizar a regra de janela temporal para NFe e financeiro.
- Validar com o negocio se pessoas e produtos entram como carga completa ou apenas incremental por alteracao.
- Definir se o piloto tera apenas leitura de Sankhya ou tambem exportacao de documentos em algum momento.
- Se o volume crescer, adicionar apenas o minimo necessario de checkpoint persistido, sem criar novo dominio paralelo.
- Manter o Outbox como infraestrutura de eventos, nao como mecanismo de sync de negocio.

## Validacao executada

- `git diff --check`

Resultado: sem divergencias de formato detectadas.

