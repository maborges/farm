# DEEPFARMS-HOSTINGER-01 — Auditoria de Capacidade para VPS KVM 4

**Data:** 27/10/2026  
**Escopo:** auditoria documental e observacional somente leitura. Nenhum banco remoto, recurso AWS ou serviço de produção foi acessado ou alterado.  
**Veredicto:** **GO COM RESSALVAS**, como avaliação preliminar para pilotos de baixa concorrência. Não há evidência para aprovar migração de produção nem desempenho sustentado na Hostinger.

## 1. Resumo executivo

O repositório confirma a arquitetura da aplicação: Next.js Web, Next.js Campo/PWA, FastAPI, PostgreSQL 16 com RLS, Redis 7 e processos worker. Contudo, não foi possível confirmar quais recursos AWS estão realmente em execução, suas dimensões e custos, nem obter métricas CloudWatch ou séries de 7/30 dias. Os documentos descrevem tanto uma implantação AWS planejada quanto um runbook para servidor próprio; nenhum comprova por si só o estado atual de produção.

Há um snapshot PostgreSQL datado de **31/03/2026**: banco de **15 MB** e cache hit informado de **99,90%**. É uma fotografia antiga, sem série temporal, portanto não prova tamanho atual, carga, crescimento ou capacidade. Não há métricas históricas de CPU, RAM, I/O, rede, Redis, API ou workers. O host deste workspace apresentou 7,6 GiB RAM, swap de 2 GiB e disco de 1.007 GiB; são números do ambiente de auditoria, não da produção, e não foram usados para dimensionar a VPS.

Estimativa inicial para KVM 4 (não medida): cerca de **10–12 GiB RAM** no cenário central, reservando **3–4 GiB** para picos e sistema; carga normal aproximada de **2 vCPU equivalentes**, com risco de saturação nos picos; e envelope de **91–181 GiB** para sistema, apps, banco, mídia e logs. Os valores dependem de uploads, crescimento do banco, concorrência e cache. Build Next.js deve ocorrer fora da VPS ou em janela isolada.

Como dado fornecido pelo solicitante, EC2 + RDS somaram **US$ 84 em dois meses**. À cotação informada de **R$ 5,60/US$**, equivalem a **R$ 470,40 no período**, média de **US$ 42 / R$ 235,20 por mês**. O valor não foi conferido na fatura nem dividido entre EC2 e RDS.

KVM 4 é candidata para homologação de piloto de baixa concorrência, com limites de workers/conexões, build externo, backup externo e monitoramento. A consolidação integral não está aprovada até medir a origem e testar carga representativa na própria VPS. A auditoria da AWS não comprova o desempenho da Hostinger.

## 2. Inventário da AWS e evidências de implantação

| Recurso | Resultado | Classe |
|---|---|---|
| EC2: tipo, vCPU, RAM, SO e volumes | Não obtidos. AWS CLI indisponível neste ambiente; nenhum inventário AWS fornecido. | NÃO DISPONÍVEL |
| RDS: classe, vCPU/RAM, armazenamento, engine/versão | Não obtidos por falta de acesso consultivo. PostgreSQL 16 consta da stack, mas não comprova engine/versão em execução no RDS. | NÃO DISPONÍVEL no runtime; MEDIDO na documentação/código |
| Redis | Redis 7 aparece no compose de desenvolvimento. Checklist AWS lista ElastiCache como etapa a provisionar/validar. Localização, classe, memória e uso de produção não confirmados. | NÃO DISPONÍVEL no runtime |
| Serviços de app | Código identifica FastAPI, Web, Campo, worker de automações, background worker e outbox worker. Compose de produção define API, Web e três workers, mas não Campo nem banco/Redis. Definições não provam execução. | MEDIDO nos artefatos; runtime NÃO DISPONÍVEL |
| systemd | README lista units `deepfarms-api`, `deepfarms-web`, `deepfarms-campo`, `deepfarms-worker`, `deepfarms-outbox` e `nginx`. Consulta no host da auditoria não encontrou units correspondentes ativas; host não comprovado como produção. | MEDIDO no host/documentação; produção NÃO DISPONÍVEL |
| Persistência, uploads e logs | Runbook de servidor próprio prevê `/srv/agrosaas/uploads`, `/var/log/agrosaas` e PostgreSQL local. Checklist AWS descreve S3 como planejado. Não se presume S3 implantado. Volumes e quantidades efetivas desconhecidos. | MEDIDO na documentação; runtime NÃO DISPONÍVEL |
| Docker | Compose local e de produção versionados; runbook prevê Docker para Redis e execução nativa via systemd. Docker em produção não confirmado. | MEDIDO nos arquivos; runtime NÃO DISPONÍVEL |
| Serviços AWS complementares | Route 53, ACM, Secrets Manager, RDS, ElastiCache, S3, ALB e CloudWatch estão em checklist com itens desmarcados. Uso efetivo não comprovado. | MEDIDO no checklist; estado NÃO DISPONÍVEL |
| Custos AWS | Solicitante informou gasto combinado de EC2 + RDS de US$ 84 em dois meses; convertido pela cotação informada de R$ 5,60/US$: R$ 470,40 no período, média US$ 42 / R$ 235,20 por mês. Sem fatura/Cost Explorer para validar, sem rateio entre serviços e sem histórico de créditos. | INFORMADO PELO SOLICITANTE (não verificado); rateio e custo por recurso NÃO DISPONÍVEIS |

O runbook `deploy-les-svrbo-ap01.md` documenta um servidor LES-SVRBO-AP01 com Rocky Linux 9.8, 2 vCPU, 4 GB RAM e 50 GB NVMe, além de Nginx, PostgreSQL e Redis locais. Refere-se ao servidor daquele runbook e não foi atribuído à EC2 atual nem ao host desta auditoria.

## 3. Consumo por serviço

| Serviço/recurso | CPU/RAM | I/O, disco e rede | Jobs, erros e latência | Evidência |
|---|---|---|---|---|
| Web Next.js | Uso por processo indisponível. | Série indisponível. | Sem latência/erros históricos. | NÃO DISPONÍVEL |
| Campo Next.js/PWA | Uso por processo indisponível. | Upload de fotos/evidências pode crescer; volume desconhecido. | Sem métricas históricas. | NÃO DISPONÍVEL |
| FastAPI | Média, p95 e pico indisponíveis. | I/O e tráfego indisponíveis. | Sem histogramas históricos encontrados. | NÃO DISPONÍVEL |
| Workers | Consumo individual indisponível. Podem competir com API e banco. | I/O individual indisponível. | Código tem loops, scheduler e batches; duração e concorrência reais desconhecidas. | Implementação MEDIDA; consumo NÃO DISPONÍVEL |
| PostgreSQL | CPU, RAM, conexões e I/O do RDS indisponíveis. | Snapshot de 15 MB em 31/03/2026, sem IOPS/latência/crescimento. | Snapshot não registra consultas longas; nele `pg_stat_statements` não estava disponível. | MEDIDO (snapshot antigo); resto NÃO DISPONÍVEL |
| Redis | Memória, hits/misses, conexões e tráfego indisponíveis. | Indisponível. | Uso de cache/fila documentado, runtime não confirmado. | NÃO DISPONÍVEL |
| Host da auditoria | Snapshot: 7,6 GiB RAM; 3,1 GiB usada e 4,2 GiB disponível; swap 626 MiB/2 GiB; raiz 54 GiB/1.007 GiB usados; load average 1,23/0,57/0,43. | Instantâneo local, sem atribuição ao DeepFarms. | Não representa média, p95, pico ou AWS. | MEDIDO em 27/10/2026; não extrapolável |

Não foram localizadas séries de 7 ou 30 dias de CPU média/p95/pico, memória, swap/OOM, disco, rede, conexões, Redis, processos, jobs, latência ou erros. Ausência de evidência não significa consumo zero.

## 4. PostgreSQL e crescimento

### Evidências

- PostgreSQL 16 consta da stack e imagem de desenvolvimento; versão runtime AWS não confirmada.
- `performance_baseline_20260331_175020.json` informa banco `farms` de **15 MB** e cache hit **99,90%**, em 31/03/2026. É snapshot sem série comparável e sem janela informada para contadores cumulativos.
- O snapshot inclui estatísticas de tabelas e índices e aponta varreduras sequenciais dominantes em tabelas como `crm_leads`, `tenants` e `assinaturas_tenant`. A base aparentava pequena naquele momento; isso não projeta produção.
- `pg_stat_statements` aparece como indisponível nesse relatório. Consultas lentas, planos, CPU e I/O não foram caracterizados.
- RLS, policies e Alembic aparecem na arquitetura. Estado efetivo das policies, extensões, migrations aplicadas e parâmetros no RDS exigem consulta ao banco alvo.

### Orçamento inicial para banco local

Na KVM 4, reservar **4–6 GiB RAM** para PostgreSQL, definindo `shared_buffers` e `work_mem` após conhecer concorrência e consultas. `work_mem` pode ser usado por operação e sessão; valor elevado multiplicado por conexões pode superar a reserva. Limitar pool e `max_connections`; não expor PostgreSQL publicamente e preservar o papel RLS por conexão. Planejar **50–80 GiB NVMe** para dados, índices, WAL e crescimento é envelope estimado, não projeção baseada no banco atual. Snapshot de 15 MB não dimensiona uploads, WAL, crescimento nem backups.

Banco e apps no mesmo disco compartilham IOPS e latência. Checkpoints, autovacuum, índices, uploads e jobs pesados podem degradar respostas. Backups devem ser criptografados e externos à VPS, com retenção e teste de restauração em homologação.

### Consultas SQL somente leitura pendentes

Executar apenas com role de leitura autorizada. Não criar extensões nem rodar migrations em produção; não usar `EXPLAIN ANALYZE` na auditoria.

```sql
-- Tamanho e tabelas maiores, índices e TOAST
SELECT current_database(), pg_size_pretty(pg_database_size(current_database()));
SELECT schemaname, relname,
       pg_size_pretty(pg_total_relation_size(relid)) AS total,
       pg_size_pretty(pg_relation_size(relid)) AS heap,
       pg_size_pretty(pg_indexes_size(relid)) AS indexes,
       n_live_tup, n_dead_tup
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC LIMIT 25;

-- Conexões e parâmetros
SELECT state, count(*) FROM pg_stat_activity GROUP BY state ORDER BY state;
SHOW max_connections;
SHOW shared_buffers;
SHOW work_mem;
SHOW maintenance_work_mem;
SHOW effective_cache_size;
SHOW temp_file_limit;

-- Extensões e RLS/policies
SELECT extname, extversion FROM pg_extension ORDER BY extname;
SELECT schemaname, tablename, rowsecurity, forcerowsecurity
FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')
ORDER BY schemaname, tablename;
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies ORDER BY schemaname, tablename, policyname;

-- Só se pg_stat_statements já estiver instalado/habilitado
SELECT queryid, calls, total_exec_time, mean_exec_time, rows,
       shared_blks_read, shared_blks_hit
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;
```

## 5. Orçamento consolidado preliminar — KVM 4

Faixas abaixo são **ESTIMADAS**, sem telemetria dos serviços. RAM representa envelope residente. Os máximos individuais não são previsão estatística nem pressupõem coincidência integral.

| Componente | RAM planejada | CPU normal planejada | Disco planejado |
|---|---:|---:|---:|
| SO, Nginx e serviços base | 1,5–2,0 GiB | 0,1–0,3 vCPU | 15–25 GiB |
| PostgreSQL | 4–6 GiB | 0,4–1,0 vCPU | 50–80 GiB |
| Redis | 0,25–0,75 GiB | 0,05–0,2 vCPU | 1–3 GiB |
| FastAPI | 1,5–2,5 GiB | 0,4–0,8 vCPU | 3–8 GiB |
| Next.js Web | 1,0–1,8 GiB | 0,2–0,5 vCPU | 5–10 GiB |
| Next.js Campo | 0,8–1,5 GiB | 0,2–0,5 vCPU | 5–10 GiB |
| Workers/jobs | 1,0–2,0 GiB | 0,3–0,8 vCPU | 2–5 GiB |
| Uploads, logs, cache e WAL | 0,5–1,0 GiB | 0,1–0,3 vCPU | 10–40 GiB, sem crescimento de mídia |
| **Envelope total** | **10,6–17,6 GiB** | **1,75–4,4 vCPU** | **91–181 GiB** |

Planejamento central: **10–12 GiB RAM** e cerca de **2 vCPU equivalentes**, mantendo pelo menos 3–4 GiB livres para picos, cache do SO e manutenção. Faixa alta excede 16 GiB e pode também exceder 4 vCPU. Restringir workers/conexões e não fazer build local podem manter a operação ordinária dentro da margem; precisa ser provado por telemetria e benchmark.

200 GB nominais não são 200 GB livres: sistema, versões de release, WAL, uploads, logs e artefatos ocupam espaço. Não contar backup integral no mesmo volume. Planejar alertas aos 70% e intervenção antes de 80%. Os 16 TB/mês são especificação informada, não tráfego medido; verificar contrato, throughput, e impacto de imagens/anexos.

### Hipóteses de simultaneidade

- **Normal:** tráfego moderado, poucas rotinas ao mesmo tempo, sem build; orçamento central de 10–12 GiB e aproximadamente 2 vCPU.
- **Pico de usuário:** API, SSR dos dois Next.js e consultas PostgreSQL podem coincidir; CPU pode aproximar-se de 4 vCPU e filas crescer.
- **Pico operacional:** job em lote, sincronização/upload de Campo, autovacuum/checkpoint e SSR podem coincidir. Envelope alto excede memória/CPU; latência e OOM são riscos.
- Picos individuais não foram somados como se necessariamente ocorressem juntos. Sobreposição acima é hipótese de teste, não medição.

## 6. Cenários de crescimento

Assinantes não equivalem a usuários simultâneos. Dimensionar por requisições concorrentes, operações de banco, uploads simultâneos e jobs por janela.

| Cenário | Premissas estimadas | Adequação preliminar | Dados necessários |
|---|---|---|---|
| **A — pilotos e poucos clientes** | Poucos usuários ativos simultaneamente, administração esporádica, uploads pequenos, jobs espaçados, build fora da VPS. | KVM 2 pode atender homologação/piloto limitado. KVM 4 dá margem melhor para stack completa com limites e monitoração. | Sessões simultâneas, tamanho e ritmo de anexos, conexões PostgreSQL e janela/duração dos jobs. |
| **B — operação inicial, crescimento moderado** | Mais sessões coincidentes, sincronizações de Campo em lote, jobs diários, banco e mídia crescendo. | KVM 4 somente se p95, memória livre e I/O passarem homologação. KVM 8 dá mais margem vertical, sem equivalência garantida por vCPU. | Séries 7/30 dias, uploads mensais, retenção, banco/WAL e concorrência de pico por endpoint/job. |
| **C — expansão comercial, maior concorrência** | Mais consultas, SSR, uploads e jobs coincidentes, sazonalidade e bursts de sync. | KVM 4 tem alto risco de contenção e ponto único de falha. KVM 8 aumenta capacidade vertical, mas mantém todos os componentes na mesma VPS. Considerar separar banco/workers conforme benchmark. | Perfil de carga, SLO, taxa de crescimento e proporção de sessões simultâneas. |

Cenários são envelopes qualitativos, não metas de usuários ou garantias.

## 7. Riscos e gargalos

1. **Ponto único de falha:** Web, Campo, API, banco, Redis e workers compartilham indisponibilidade e recuperação.
2. **CPU compartilhada:** vCPU não garante clock, crédito ou ausência de contenção de vizinhos, nem equivale à EC2. Medir desempenho sustentado na Hostinger.
3. **I/O compartilhado:** banco, WAL, logs, cache, uploads e builds disputam NVMe; IOPS, latência e throttling do plano não foram verificados.
4. **RAM:** SSR, API, workers, conexões e cache podem consumir 16 GB; swap não deve entrar no orçamento operacional. OOM afeta o host inteiro.
5. **Builds:** `next build`, dependências e releases consomem CPU, RAM e disco. Gerar artefatos em CI ou máquina de build separada.
6. **Banco/conexões:** pooling, `work_mem`, sessões ociosas e manutenção precisam de limites. Validar RLS, policies, extensões e migrations em cópia de homologação.
7. **Uploads e retenção:** fotos/evidências podem crescer mais que o banco. Mídia não inventariada; backup local não protege de perda da VPS.
8. **Redis/filas:** memória, persistência e tolerância a perda da fila são desconhecidas. Cache e jobs podem ter necessidades distintas.
9. **DR e operação:** backup, retenção, restore, alertas, logs e DR não comprovados.
10. **Transferência:** 16 TB anunciados não são tráfego medido; volume real e política contratual desconhecidos.

## 8. Comparação KVM 2, KVM 4 e KVM 8

Planos conforme especificação fornecida pelo solicitante. Não se presume equivalência de desempenho entre vCPUs de fornecedores.

| Plano | Recursos | Avaliação | Margem / uso |
|---|---|---|---|
| **KVM 2** | 2 vCPU, 8 GB RAM, 100 GB NVMe | Apertada: orçamento central da stack completa excede RAM disponível quando se somam SO, banco, dois Next.js, API e workers. Alto risco de swap/OOM em build e pico. | Piloto leve/homologação com workers reduzidos e limites rígidos ou serviços externos. Pouca margem. |
| **KVM 4** | 4 vCPU, 16 GB RAM, 200 GB NVMe, 16 TB/mês anunciados | Candidata para piloto/baixa concorrência com builds externos. Envelope alto ultrapassa CPU/RAM/disco; carga sustentada precisa validação. | Margem moderada no cenário central, pequena com picos combinados. Não aprovar expansão sem benchmark. |
| **KVM 8** | 8 vCPU, 32 GB RAM, 400 GB NVMe | Melhor margem vertical para banco, apps e workers; depende de desempenho real do host/disco. Continua ponto único de falha. | Mais apropriada se consolidação integral for requisito e benchmark mostrar gargalo vertical. Requer backup externo e recuperação testada. |

Preço Hostinger não avaliado: o valor contratual do plano KVM 4 não foi fornecido nem verificado. Para AWS há referência informada pelo solicitante de US$ 42 (R$ 235,20) mensais para EC2 + RDS combinados, ainda sem validação em fatura, rateio por recurso ou ajuste por créditos/impostos.

### Comparação com AWS Free Tier (página consultada em 27/10/2026)

O AWS Free Tier **não é um plano de VPS equivalente à KVM 4**. É uma oferta para novas contas, com créditos e limites por produto/região/uso. A página atual anuncia até **US$ 200 em créditos** (US$ 100 ao abrir a conta e até US$ 100 por atividades elegíveis), mais de 30 ofertas com cotas gratuitas e experiência do plano Free por até **6 meses**. O plano termina quando acabam os créditos ou ao completar seis meses, o que ocorrer primeiro. Após o fim, a conta Free é fechada; é necessário migrar para o plano pago para manter acesso aos recursos/dados. Assim, não é base de custo recorrente para serviço comercial.

| Oferta AWS | O que significa para esta arquitetura | Comparação com KVM 4 |
|---|---|---|
| EC2 no programa atual | Para contas novas a partir de 15/07/2025, a documentação lista tipos elegíveis como `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`, `c7i-flex.large` e `m7i-flex.large`, durante até 6 meses ou enquanto houver créditos. Elegibilidade não significa que qualquer configuração seja sem custo: consumo além das cotas/créditos é tarifado após upgrade. | Não equivale a 4 vCPU/16 GB/200 GB. São instâncias EC2 específicas e a escolha depende do plano da conta, região e crédito disponível. Não agrupar instâncias presumindo custo zero. |
| RDS PostgreSQL | Oferta atual para novas contas permite explorar RDS/Aurora por até 6 meses com créditos. A página do RDS lista instâncias micro elegíveis (`db.t3.micro` e `db.t4g.micro`) para PostgreSQL e outros engines; classe, armazenamento, backup e tráfego continuam limitados pelo crédito/condições. | Pode manter banco separado e gerenciado, mas uma instância micro não é prova de capacidade para produção; os créditos cobrem uso elegível e são finitos. |
| Redis gerenciado | ElastiCache pode ser usado nas ofertas/créditos conforme plano e elegibilidade. A antiga cota de 750 horas de nó micro é legado, não deve ser assumida para conta nova. | Pode manter cache/fila como serviço separado, mas depende de crédito e não compõe uma VPS gratuita permanente. |
| Armazenamento e transferência | Serviços selecionados têm cotas/créditos próprios; não se deve inferir que os 200 USD cubram o volume de uploads, backups, tráfego ou solicitações do DeepFarms. | Não comparável diretamente aos 200 GB NVMe e 16 TB anunciados da KVM; são modelos e limites distintos. |
| Conta anterior a 15/07/2025 | Regras legadas podem conceder até 750 h/mês de instâncias micro EC2 e RDS selecionado por até 12 meses após cadastro; RDS legado inclui até 20 GB de armazenamento de banco e 20 GB de backup. O uso elegível agrega instâncias/regiões. | Só se aplica se a conta for elegível e ainda estiver no prazo/limite. Não presumir elegibilidade para a conta AWS atual do DeepFarms. |

**Implicação econômica:** o solicitante informa gasto combinado EC2 + RDS de **US$ 84/2 meses**, ou **US$ 42 (R$ 235,20) mensais** à cotação declarada de R$ 5,60/US$. É uma referência nominal, sem validação de fatura, impostos, créditos, rateio ou sazonalidade. Sem data/estado da conta, saldo de créditos, elegibilidade e uso Free Tier, não se pode afirmar que a AWS atual seja gratuita. Também não é possível declarar economia com KVM sem preço Hostinger e sem contabilizar backup externo, operação e serviços eventualmente mantidos na AWS. Os créditos não alteram a capacidade técnica exigida: AWS pode distribuir a carga entre EC2, RDS e Redis; na KVM os componentes compartilham CPU, RAM e disco. Comparar custo recorrente pós-crédito e risco operacional, não apenas a oferta inicial.

Fontes oficiais consultadas: [AWS Free Tier](https://aws.amazon.com/pt/free/), [FAQ do Free Tier](https://aws.amazon.com/pt/free/free-tier-faqs/), [elegibilidade Free Tier do EC2](https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html), [Free Tier do RDS](https://aws.amazon.com/pt/rds/free/) e [preços do RDS](https://aws.amazon.com/pt/rds/pricing/). As ofertas variam conforme data de abertura da conta; confirmar no Billing Console antes de qualquer decisão financeira.

### Comparação direta dos recursos

| Recurso | Hostinger KVM 4 | AWS Free Tier / componentes elegíveis | Leitura para DeepFarms |
|---|---|---|---|
| **CPU** | 4 vCPU contínuas contratadas no plano. Desempenho efetivo depende do host e da política de compartilhamento. | Não há cota Free Tier fixa de 4 vCPU. Para contas novas após 15/07/2025, a lista de tipos EC2 elegíveis inclui `t3.micro`, `t3.small`, `t4g.micro`, `t4g.small`, `c7i-flex.large` e `m7i-flex.large`; no modelo legado, `t2.micro`/`t3.micro`. Tipo elegível usa crédito/cota e não significa instância gratuita sem limite. | KVM 4 oferece alocação nominal mais direta. AWS pode distribuir carga em várias instâncias, mas isso deixa de ser comparação de uma única máquina e pode consumir créditos rapidamente. |
| **RAM** | 16 GB no mesmo host para SO, PostgreSQL, Redis, API, dois Next.js e workers. | Tipos micro do EC2 têm RAM muito inferior (por exemplo, `t3.micro`: 1 GiB; `t3.small`: 2 GiB). Outros tipos elegíveis têm capacidades diferentes e consomem o crédito; não existe garantia de 16 GB gratuitos contínuos. | Para a stack unificada estimada em 10–12 GiB no cenário central, micros isoladas são insuficientes. Uma instância maior pode acomodar mais, mas não equivale a custo zero recorrente. |
| **Armazenamento de sistema/app** | 200 GB NVMe local incluídos conforme plano; capacidade e I/O precisam ser confirmados por homologação. | EC2 usa volumes EBS separados, dimensionáveis e tarifados por tipo/tamanho/IOPS conforme elegibilidade/créditos. Não são parte de uma cota fixa equivalente a 200 GB NVMe para todos os usuários atuais. | KVM dá capacidade nominal integrada; EBS permite ajustar volume, mas adiciona recurso/custo e pode ter perfil de I/O distinto. |
| **PostgreSQL** | Pode rodar localmente, dividindo RAM, CPU e disco com aplicações; operação, backup e HA ficam a cargo do operador. | RDS é um recurso separado. A oferta atual lista `db.t3.micro` e `db.t4g.micro` como classes elegíveis para PostgreSQL; classe/armazenamento/backup e uso além dos créditos limitam o benefício. Na tabela oficial, `db.t3.micro` tem 2 vCPU e 1 GiB RAM. Oferta legada para conta criada antes de 15/07/2025: até 750 h/mês e 20 GB de armazenamento e backup elegíveis por até 12 meses. | RDS separa a carga e administra tarefas do banco; micro com 1 GiB não é capacidade comparável aos 4–6 GiB estimados para PostgreSQL local na KVM 4. A classe real do RDS do DeepFarms é desconhecida. |
| **Redis** | Redis local pode compartilhar o mesmo host; memória compete com banco e apps. | ElastiCache é componente separado e elegibilidade/cobertura dependem do plano/conta; a oferta antiga de 750 h de nó micro por 12 meses não deve ser aplicada automaticamente a conta nova. | AWS preserva isolamento de recursos gerenciados, sujeito a cobrança após crédito/limite. A KVM reduz número de serviços faturados, mas agrega contenção e responsabilidade operacional. |
| **Rede/transferência** | Plano anuncia 16 TB/mês; throughput, política de uso e tráfego real precisam ser confirmados. | AWS não concede uma cota geral fixa equivalente a 16 TB para a solução completa Free Tier atual. Limites e créditos variam por serviço; transferência entre serviços, saída à internet e regiões pode ter tratamento/cobrança diferente. | Não comparar o teto anunciado a uma única cota AWS; medir tráfego de uploads, páginas, API e backups e calcular no modelo regional efetivo. |
| **Duração/custo** | Recurso reservado enquanto o plano Hostinger estiver contratado, com valor contratual não avaliado aqui. | Até US$ 200 em créditos para novos clientes e plano Free por até seis meses (crédito esgotado ou prazo, o que vier primeiro). Conta legada pode ter benefícios limitados por 12 meses. Depois, recursos precisam de plano pago para continuidade. | Gasto informado para EC2 + RDS: US$ 84 em dois meses, média US$ 42 / R$ 235,20 mensais à cotação indicada. Saldo/elegibilidade de créditos e custo Hostinger não disponíveis. |

**Comparação de ordem de grandeza (sem equivalência de desempenho):** a KVM 4 concentra em uma máquina 4 vCPU + 16 GB + 200 GB. A oferta micro de referência comum do AWS Free Tier (`t3.micro`/`db.t3.micro`) é **2 vCPU burstable e 1 GiB RAM por instância**, com armazenamento separado; não cabe executar toda a stack em uma dessas instâncias. Mesmo somando EC2 + RDS + Redis, as cotas gratuitas não viram uma VPS de 16 GB: são recursos distribuídos com limites e créditos. A AWS pode fornecer recursos maiores conforme a oferta e os créditos elegíveis, mas a capacidade sem custo não é garantida por mês/ano sem consultar a conta, região, serviço e consumo.

Os números de classe e elegibilidade acima vêm da [tabela de tipos EC2](https://docs.aws.amazon.com/pt_br/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html), das [especificações EC2 T3](https://aws.amazon.com/pt/ec2/instance-types/t3/), das [classes RDS](https://aws.amazon.com/pt/rds/instance-types/) e da página [Free Tier do RDS](https://aws.amazon.com/pt/rds/free/). Valores de capacidade de disco/rede AWS não foram convertidos para equivalentes Hostinger porque são configuráveis, dependem da classe/volume/região e não há inventário do ambiente DeepFarms.

## 9. Lacunas de medição

- Inventário de recursos comprovadamente pertencentes ao DeepFarms; EC2, volumes, RDS, Redis e serviços auxiliares ativos.
- CloudWatch de 7 e 30 dias: CPU média/p95/pico, RAM (se agente), swap/OOM, disco, rede e latência.
- Fatura/Cost Explorer para verificar o total informado de US$ 84 por dois meses e ratear custo por EC2/RDS; saldo/uso de créditos e impostos.
- Preço efetivo da KVM 4 e eventuais serviços externos que continuariam ativos, para calcular economia e ponto de equilíbrio.
- Conexões e limites PostgreSQL; tamanho atual de tabelas/índices, WAL, extensões, policies RLS, parâmetros e migrations.
- Queries caras/longas, CPU/I/O, locks, deadlocks, autovacuum e taxa de crescimento.
- Redis: serviço/classe, memória, evictions, hits/misses, conexões, persistência e filas.
- Consumo, quantidade de réplicas, limites, reinícios e OOM de cada processo Web/Campo/API/worker.
- Duração, concorrência, backlog e periodicidade de jobs; p50/p95/p99 e taxa de erros por endpoint.
- Espaço e crescimento de uploads, logs, artefatos e retenção.
- Plano de backup/restore, retenção, armazenamento externo e DR.
- Garantias contratuais e limites de CPU compartilhada, NVMe, rede e transferência Hostinger.

## 10. Consultas pendentes e recomendação de homologação

Comandos abaixo são instruções de consulta e **não foram executados**. Usar perfil AWS read-only autorizado e filtrar recursos com tags de projeto verificadas. Não registrar IDs, endpoints ou dados sensíveis no relatório.

```bash
aws sts get-caller-identity
aws ec2 describe-instances --filters Name=tag:Project,Values=DeepFarms Name=instance-state-name,Values=running
aws rds describe-db-instances
aws elasticache describe-cache-clusters --show-cache-node-info
aws s3api list-buckets
aws elbv2 describe-load-balancers
aws route53 list-hosted-zones
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<INSTANCE_ID> --start-time <UTC_INICIO> --end-time <UTC_FIM> \
  --period 300 --statistics Average Maximum
aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<DB_INSTANCE> --start-time <UTC_INICIO> --end-time <UTC_FIM> \
  --period 300 --statistics Average Maximum
```

Repetir em janelas separadas de 7 e 30 dias para `FreeableMemory`, `FreeStorageSpace`, `ReadIOPS`, `WriteIOPS`, `ReadLatency`, `WriteLatency`, `DatabaseConnections`, throughput e bytes de rede. Métricas de RAM EC2 podem depender do CloudWatch Agent. Para Redis, consultar memória, evictions, conexões e hits/misses conforme o serviço. Validar tags/contas para não atribuir à DeepFarms recursos alheios. Consultas SQL read-only pendentes estão na seção 4.

Homologar em ambiente isolado, com dados sintéticos ou anonimizados e sem carga na produção:

1. Registrar versões, limites CPU/RAM, características de disco/rede e artefatos de deploy.
2. Medir baseline e testar por etapas Web, Campo, API, banco, workers e depois concorrência combinada.
3. Simular fluxos medidos de login, leitura/escrita, sync/upload e job demorado junto de API e PostgreSQL, usando sessões simultâneas observadas.
4. Registrar CPU média/p95/pico, RAM, swap/OOM, latência/IOPS/throughput do disco, rede, conexões, filas, p50/p95/p99 e erros em teste sustentado e pico curto.
5. Confirmar que build/publicação não compete com produção; testar CPU/I/O sustentados e possível throttling.
6. Validar migrations, extensões, RLS/policies em banco descartável. Testar restauração isolada e integridade dos uploads.
7. Fixar SLO antes do teste. Critério preliminar para KVM 4: 3–4 GiB RAM livres, sem OOM/swap, p95 dentro do SLO, filas controladas, sem saturação sustentada de CPU/I/O e disco projetado abaixo de 70% no período de retenção.

Nenhum serviço foi iniciado e nenhum benchmark executado nesta auditoria. A validação definitiva depende de teste na VPS; auditoria AWS sozinha não prova desempenho Hostinger.

## 11. Veredicto final

**GO COM RESSALVAS para homologação de piloto na KVM 4.** O snapshot de banco de 15 MB, datado de 31/03/2026, é pequeno, mas antigo e insuficiente para representar banco, mídia ou carga atuais. O orçamento estimado prevê 10–12 GiB RAM em cenário central e até 17,6 GiB no envelope alto; picos concorrentes podem exceder 4 vCPU. A margem não foi comprovada por medições históricas.

**Sem GO para migração integral ou operação comercial sustentada.** Faltam inventário real AWS, histórico de 7/30 dias, medições de banco/Redis/jobs/uploads e benchmark Hostinger. Aprovação final depende de consultas read-only autorizadas na origem, SLO acordado e homologação isolada com carga combinada. KVM 2 não é recomendada para a stack completa. KVM 8 tem margem vertical maior se os testes confirmarem necessidade, mas não remove o ponto único de falha.

### Fontes locais consultadas

- `docs/architecture/architecture-inventory.md` — stack documentada.
- `docs/architecture/agrosaas-deployment-architecture.md` — topologia conceitual, com componentes presumidos.
- `docs/AWS_DEPLOYMENT_CHECKLIST.md` — recursos AWS em checklist planejado.
- `docs/runbooks/deploy-les-svrbo-ap01.md` — dimensões de servidor próprio, sem comprovação de EC2 atual.
- `docker-compose.yml` e `docker-compose.prod.yml` — definições versionadas, não prova de runtime.
- `services/api/scripts/reports/performance_baseline_20260331_175020.json` — snapshot PostgreSQL de 31/03/2026.
- `README.md` — units e procedimentos documentados.
