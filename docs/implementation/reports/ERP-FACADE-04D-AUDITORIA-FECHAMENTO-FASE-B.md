# ERP-FACADE-04D - Auditoria de Fechamento da Fase B

Status: CONCLUIDA  
Data: 2026-07-09  
Escopo: auditoria final sobre `logs`, nomenclatura interna remanescente e prontidao multiprovider da borda HTTP ERP

## Resumo executivo

A Fase B pode ser considerada **encerrada** para os conceitos comuns de leitura e governanca ERP. A UI generica ja consome:

- `status`
- `health`
- `jobs`
- `timeline`
- `diagnostico`
- `associacoes`

via `/api/v1/integracoes/erp/*`.

Conclusoes de fechamento:

- **Logs**: devem permanecer **provider-specific** nesta fase. O endpoint atual `/integracoes/sankhya/logs` e uma superficie tecnica/historica, parcialmente legada, com enriquecimento canonico, mas nao e um conceito ERP comum suficientemente limpo para justificar `/integracoes/erp/logs`.
- **Console ERP**: nao precisa de logs brutos como dependencia principal. `timeline` e `diagnostico` ja cobrem a necessidade comum do tenant. O Backoffice ainda se beneficia de logs tecnicos provider-specific para suporte.
- **Nomenclatura `Sankhya*`**: a maior parte do que resta no frontend e **legado nominal sem acoplamento funcional**. O acoplamento funcional principal ja foi removido pela migracao para `/integracoes/erp/*`.
- **Multiprovider**: a borda ERP atual esta adequada como estagio transitório, mas ainda possui condicionais fixas para Sankhya. O `501` e aceitavel temporariamente. Criar um resolvedor formal agora seria **infraestrutura prematura**; a recomendacao e adiar isso ate a implementacao real do segundo provider ERP.

## Inventario de observabilidade

### Infraestrutura existente revisada

Fontes principais:

- [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py)
- [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py)
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
- [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)

Ativos encontrados:

- `IntegrationJob`
- `IntegrationHealth`
- `ErpReadinessService`
- `SankhyaSyncLog`
- `timeline` ERP
- `diagnostico` ERP
- `status` ERP
- `jobs` ERP
- `ExternalRecordAssociation`
- lifecycle em `TenantIntegracao.lifecycle_state`

### O que ja esta representado em `IntegrationJob`

Campos equivalentes ou semanticamente proximos:

- identificador da execucao
- `feature_code`
- `job_status`
- `trigger_type`
- `started_at`
- `finished_at`
- `processados`
- `sucessos`
- `erros`
- `correlation_id`
- `result_payload`
- `error_payload`

Evidencia:

- `listar_jobs` serializa `IntegrationJob` como superficie canonica em [sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

### O que ja aparece na timeline

A `timeline` atual compoe:

- jobs canonicos
- logs enriquecidos
- snapshot de health

Evidencia:

- `listar_timeline_operacional` usa `listar_logs_enriquecidos`, `listar_jobs` e `obter_health_detalhado` em [sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

### O que ja aparece no diagnostico

O `diagnostico` atual consolida:

- ultimo sucesso
- ultima falha
- falhas consecutivas
- jobs pendentes
- jobs falhos
- feature mais problematica
- recomendacao operacional

Ele usa:

- `status`
- `health`
- `jobs`
- `logs enriquecidos`

Evidencia:

- `obter_diagnostico_operacional` em [sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

### O que existe somente em `SankhyaSyncLog`

Campos ou semanticas especificamente legadas/tecnicas:

- `tipo`
- `operacao`
- `erro_mensagem`
- `tempo_execucao_ms`
- `periodo_inicio`
- `periodo_fim`
- granularidade de log legado por sincronizacao historica

Evidencia:

- modelo [SankhyaSyncLog](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py)

### Duplicidade funcional identificada

Ha duplicidade parcial entre:

- `logs` e `jobs`
- `logs` e `timeline`
- `logs` e `diagnostico`

Padrao observado:

- `jobs` e a superficie canonica de execucao
- `timeline` e a superficie consolidada para leitura comum
- `diagnostico` e a superficie consolidada para triagem
- `logs` preserva detalhamento tecnico/historico legado e correlacao retroativa

Conclusao:

- existe sobreposicao funcional suficiente para **nao** promover `logs` a conceito ERP comum nesta fase

## Analise detalhada de logs

### Endpoint auditado

- `GET /api/v1/integracoes/sankhya/logs`

Fontes:

- [router Sankhya](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py)
- [SankhyaSyncLogResponse](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/schemas/__init__.py)

### Classificacao campo a campo

| Campo | Classificacao | Observacao |
|---|---|---|
| `id` | legado | id do log historico, nao id canonico de job |
| `tenant_id` | auditoria funcional | escopo necessario, mas nao diferencia `logs` como contrato ERP |
| `tipo` | provider-specific / legado | taxonomia historica de sync Sankhya |
| `operacao` | provider-specific / suporte tecnico | import/export/sync do fluxo tecnico |
| `status` | legado | status do log, distinto do `job_status` canonico |
| `registros_processados` | informacao duplicada | ja existe correlato em `IntegrationJob.processados` |
| `registros_sucesso` | informacao duplicada | ja existe correlato em `IntegrationJob.sucessos` |
| `registros_erro` | informacao duplicada | ja existe correlato em `IntegrationJob.erros` |
| `tempo_execucao_ms` | suporte tecnico | util para suporte e tuning, nao essencial ao console ERP comum |
| `created_at` | auditoria funcional | historico do registro legado |
| `started_at` | informacao duplicada parcial | ja existe em job e timeline |
| `completed_at` | informacao duplicada parcial | ja existe em job e diagnostico |
| `origem_dados` | suporte tecnico | sinaliza `legacy` ou `canonical+legacy`, util para transicao |
| `integration_job_id` | canônico do runtime | ponte clara para `IntegrationJob` |
| `feature_code` | canônico do runtime | dado comum, ja exposto em `jobs` e `timeline` |
| `job_status` | canônico do runtime | duplicado do job canonico |
| `trigger_type` | canônico do runtime | duplicado do job canonico |
| `job_started_at` | canônico do runtime / duplicado | duplicado do job canonico |
| `job_finished_at` | canônico do runtime / duplicado | duplicado do job canonico |
| `result_payload` | suporte tecnico | util para suporte/backoffice |
| `error_payload` | suporte tecnico / provider-specific | pode carregar erro canonico ou `erro_mensagem` legado |

### Respostas objetivas sobre `logs`

1. `logs` e um conceito ERP comum?  
Nao. O contrato atual ainda e predominantemente tecnico e historico.

2. E apenas um historico tecnico do Sankhya?  
Majoritariamente sim, com enriquecimento canonico para correlacao.

3. Existe conteudo canonico suficiente para justificar `/integracoes/erp/logs`?  
Nao nesta fase. O conteudo canonico relevante ja esta melhor representado em `jobs`, `timeline` e `diagnostico`.

4. Timeline e diagnostico ja tornam a rota de logs desnecessaria para consumidores comuns?  
Sim, para o tenant e para leituras comuns de UX.

5. O Backoffice precisa de logs brutos provider-specific?  
Sim, como ferramenta de suporte tecnico e compatibilidade historica.

6. O tenant deve visualizar logs tecnicos?  
Nao como dependencia principal. Pode ver um resumo complementar, mas o contrato ideal para o tenant e `timeline` + `diagnostico`.

## Consumidores encontrados

### Runtime/UI

Consumidores reais do endpoint:

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx)

### Testes

Nao foi encontrado teste de UI consumindo `/integracoes/sankhya/logs` diretamente.

Foram encontrados testes e validacoes do backend em torno de:

- `listar_logs_enriquecidos`
- enriquecimento com `IntegrationJob`

### Scripts

Nao foram encontrados scripts operacionais consumindo `/integracoes/sankhya/logs`.

### Documentacao

Ocorrencias relevantes:

- [services/api/integracoes/sankhya/README.md](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/README.md)
- [docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-CONSOLE-01-CONSOLE-ADMINISTRATIVO-INTEGRACOES-ERP.md)
- [docs/implementation/reports/ERP-FACADE-03-AUDITORIA-SUPERFICIE-HTTP.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-FACADE-03-AUDITORIA-SUPERFICIE-HTTP.md)

### Classificacao por consumidor

| Consumidor | Necessidade funcional | Suporte | Compatibilidade historica | Substituivel por timeline | Substituivel por diagnostico | Provider-specific |
|---|---|---|---|---|---|---|
| Tenant ERP Console | baixa | baixa | media | sim, quase total | sim, para triagem | nao deveria depender |
| Backoffice ERP | media | alta | alta | parcial | parcial | sim |
| Documentacao Sankhya | baixa | media | alta | nao aplicavel | nao aplicavel | sim |

Conclusao:

- o Console ERP do tenant nao deveria evoluir sobre `logs`
- o Backoffice pode manter acesso a `logs` como superficie de suporte tecnico Sankhya

## Mapa de nomenclatura remanescente

### Ocorrencias revisadas

Frontend:

- [apps/web/src/components/integracoes/sankhya-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-console.tsx)
- [apps/web/src/components/integracoes/sankhya-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/sankhya-timeline.tsx)
- [apps/web/src/components/integracoes/erp-console.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)
- [apps/web/src/components/integracoes/erp-timeline.tsx](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-timeline.tsx)

Backend:

- `SankhyaTimelineItemResponse`
- `SankhyaHealthResponse`
- `SankhyaOperationalDiagnosisResponse`

### Classificacao das ocorrencias

| Ocorrencia | Classificacao | Justificativa |
|---|---|---|
| arquivo `sankhya-console.tsx` | B. Legado nominal sem acoplamento funcional | a tela consumida e `ErpConsole`; o arquivo ainda carrega nome historico |
| arquivo `sankhya-timeline.tsx` | B. Legado nominal sem acoplamento funcional | o componente exportado e `ErpTimeline`; o arquivo ainda carrega nome historico |
| alias `SankhyaConsole = ErpConsole` | B. Legado nominal sem acoplamento funcional | compatibilidade de import/export |
| alias `SankhyaTimeline = ErpTimeline` | B. Legado nominal sem acoplamento funcional | compatibilidade de import/export |
| tipos TS `SankhyaStatus`, `SankhyaHealth`, `SankhyaJob`, `SankhyaDiagnosis` no console | B. Legado nominal sem acoplamento funcional | os payloads ja vem de `/integracoes/erp/*` para os conceitos comuns |
| tipo `SankhyaConfig` | A. Provider-specific legitima | representa configuracao especifica do provider atual |
| imports de `sankhya-timeline` feitos por `erp-timeline.tsx` e `sankhya-console.tsx` | B. Legado nominal sem acoplamento funcional | implementacao concreta continua no arquivo historico |
| `SankhyaTimelineItemResponse` no backend ERP router | B. Legado nominal sem acoplamento funcional | a borda ERP reutiliza o schema do provider atual por compatibilidade |
| qualquer `sankhya_*` de autenticacao, gateway, sync, NFe, financeiro | A. Provider-specific legitima | responsabilidades exclusivas do provider |
| dependencia do router ERP em imports diretos de handlers Sankhya | C. Acoplamento indevido | a borda ERP continua semanticamente fixa no provider atual |

### Conclusao sobre nomenclatura

- no frontend, a maior parte do remanescente e **legado nominal**
- no backend ERP router, o principal acoplamento residual nao e o nome, e sim a **delegacao hardcoded para Sankhya**

## Analise multiprovider

### Fluxo atual auditado

```text
UI ERP
↓
/integracoes/erp/*
↓
_resolve_active_erp_provider_slug
↓
_assert_sankhya_provider
↓
delegacao direta para Sankhya
```

Fonte:

- [services/api/integracoes/erp/router.py](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)

### Respostas objetivas

1. A UI precisaria ser alterada para um segundo provider?  
Nao, desde que o segundo provider implemente os mesmos conceitos na borda ERP.

2. O router ERP possui condicionais fixas para Sankhya?  
Sim. Ha import direto de handlers Sankhya, fallback legado Sankhya e `_assert_sankhya_provider`.

3. O retorno `501` atual e adequado como estagio temporario?  
Sim. Ele deixa explicito que a borda existe, mas o provider ainda nao foi conectado a ela.

4. Existe contrato claro para registrar um novo provider?  
Sim, no nivel de arquitetura e runtime: `MarketplaceIntegracao`, `TenantIntegracao`, provider contract e schemas de provider.

5. Seria necessario criar um resolvedor formal agora?  
Nao.

6. A criacao de um resolvedor formal seria reutilizacao ou infraestrutura prematura?  
Neste momento seria **infraestrutura prematura**. Ainda nao existe segundo provider ERP real demandando isso.

7. Quais alteracoes minimas seriam necessarias para suportar o segundo provider?  
- implementar o provider no runtime oficial  
- expor `status`, `health`, `jobs`, `timeline`, `diagnostico` e, se aplicavel, `associacoes` no adapter/servico do novo provider  
- substituir a delegacao hardcoded do router ERP por um dispatch pequeno por `provider_slug`  
- manter `501` para o que ainda nao estiver materializado

## Riscos

### 1. `logs` pode prolongar acoplamento visual no tenant

Risco:

- o Console ERP ainda mostra uma caixa de "Histórico complementar" baseada em logs Sankhya.

Impacto:

- baixo para arquitetura, medio para pureza conceitual da UX.

### 2. Delegacao do router ERP ainda e fixa em Sankhya

Risco:

- a borda HTTP ERP ainda nao e pluggable no nivel do transporte.

Impacto:

- aceitavel com um provider unico, mas precisa ser revisto quando o segundo ERP real entrar.

### 3. Nomes historicos podem ser confundidos com acoplamento funcional

Risco:

- auditorias futuras podem superestimar o acoplamento apenas pelo nome do arquivo ou do tipo.

Impacto:

- baixo, mas gera ruido de governanca.

## Decisoes finais

### Decisao 1 - Logs

**Opcao A - Permanecer provider-specific**

Decisao:

- `GET /integracoes/sankhya/logs` deve permanecer como ferramenta tecnica e de suporte

Justificativa:

- o contrato atual nasce de `SankhyaSyncLog`
- parte relevante dos campos e legado ou suporte tecnico
- `jobs`, `timeline` e `diagnostico` ja cobrem o consumo ERP comum
- o que sobrou de valor em `logs` interessa mais ao backoffice/suporte do que ao console comum

GO/NO-GO:

- GO para manter provider-specific
- NO-GO para criar `/integracoes/erp/logs` nesta fase
- GO para retirar dependencia forte de logs na UX comum em fase futura

### Decisao 2 - Nomenclatura interna

**Manter como compatibilidade por enquanto, removendo apenas acoplamentos indevidos em fases futuras**

Decisao:

- nao ha urgencia tecnica para renomear todos os `Sankhya*` agora
- a refatoracao nominal deve ser controlada e posterior

Justificativa:

- a maioria das ocorrencias remanescentes no frontend e legado nominal
- o principal problema residual e a delegacao semantica fixa do router ERP, nao os nomes em si

GO/NO-GO:

- GO para manter nomes historicos por compatibilidade imediata
- GO para uma futura refatoracao nominal controlada
- NO-GO para uma renomeacao ampla antes de existir demanda funcional real

### Decisao 3 - Resolvedor multiprovider

**Adiar ate o segundo provider real**

Decisao:

- manter a resolucao atual enquanto existe apenas Sankhya como ERP real

Justificativa:

- `ErpReadinessService` ja encontra o provider ativo
- falta apenas um dispatch leve no router quando houver segundo provider
- criar resolvedor formal agora adicionaria abstracao sem caso real

GO/NO-GO:

- GO para manter a resolucao atual
- NO-GO para criar resolvedor formal agora
- GO para planejar o resolvedor na proxima fase em que TOTVS, SAP, Omie ou Senior entrarem de fato

## Recomendacao final por evolucao

| Evolucao | Recomendacao |
|---|---|
| Criar `/integracoes/erp/logs` agora | NO-GO |
| Manter `/integracoes/sankhya/logs` no backoffice | GO |
| Reduzir dependencia de logs no console comum | GO |
| Renomear toda nomenclatura `Sankhya*` agora | NO-GO |
| Refatoracao nominal controlada futura | GO |
| Criar resolvedor formal agora | NO-GO |
| Planejar dispatch multiprovider quando houver segundo ERP real | GO |

## Plano minimo para fase posterior

### Fase posterior minima recomendada

1. Reclassificar a UX de logs no tenant:
   - reduzir ou remover protagonismo do card de logs no `ErpConsole`
   - manter `timeline` e `diagnostico` como superfícies principais

2. Preservar logs no Backoffice:
   - manter `/integracoes/sankhya/logs` como ferramenta tecnica de suporte

3. Quando o segundo provider ERP existir:
   - trocar `_assert_sankhya_provider` por dispatch por `provider_slug`
   - manter a UI ERP sem mudanca de contrato

4. So depois disso:
   - avaliar renomeacao nominal de arquivos/tipos que permanecerem historicos

## Encerramento da Fase B

Conclusao final:

- a Fase B pode ser considerada **encerrada**
- a superficie HTTP ERP ja cobre os conceitos comuns relevantes para o piloto
- `logs` nao deve entrar na superficie ERP agora
- a nomenclatura remanescente nao bloqueia a arquitetura
- um resolvedor formal multiprovider deve esperar a entrada real do segundo ERP

## Validacao executada

```bash
git diff --check
```
