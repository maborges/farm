# DEEPFARMS-RLS-HOSTINGER-01D — Plano de Correção Controlada

**Data:** 2026-10-31
**Status:** planejamento; nenhuma alteração implementada
**Base:** relatório 01C, leitura estática do código e Compose versionado local

## 1. Objetivo e limites

Este plano descreve a preparação e a execução futura, incremental, da separação de privilégios PostgreSQL e do isolamento de Tenant. Nesta etapa não foram alterados banco, roles, grants, policies, migrations, código funcional ou Compose; não houve conexão com a VPS Hostinger nem execução de testes.

A evidência Hostinger permanece a fornecida pelo operador e registrada no [01C — Inventário real](DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md). O arquivo efetivo informado na VPS (`/opt/deepfarms/farm/docker-compose.hostinger.yml`) não existe neste checkout. O Compose local [docker-compose.prod.yml](../../../docker-compose.prod.yml) foi lido sem abrir arquivos de ambiente; ele aponta API e os três workers para o mesmo `env_file`. Isso demonstra o desenho versionado local, não a configuração resolvida na Hostinger. O wiring e a gestão de segredos da VPS são pré-requisitos antes de aprovar cutover.

A arquitetura de domínio não muda: o Tenant é o assinante e pode possuir várias propriedades e usuários. `is_superuser` da aplicação é uma autorização de negócio e nunca deve se traduzir em `SUPERUSER` ou `BYPASSRLS` no PostgreSQL.

## 2. Decisões técnicas propostas

1. **Retirar privilégios de runtime por identidade, não por convenção.** API e workers deixam de autenticar como `deepfarms`. Nenhuma identidade runtime será `SUPERUSER`, `BYPASSRLS`, dona de tabelas, membro de role de deploy/owner, nem terá `CREATEROLE`, `CREATEDB` ou `REPLICATION`.
2. **Separar owner, deploy e operação.** Objetos pertencem a role `NOLOGIN`; migrations usam credencial de deploy controlada e temporária que pode assumir a role owner; processos persistentes usam logins operacionais distintos e sem membership elevável.
3. **Aplicar privilégio mínimo por consumidor.** Não usar `GRANT ALL TABLES`, `ALL SEQUENCES`, acesso ao schema inteiro por default privilege, ou a mesma permissão de escrita em todas as tabelas. A lista de grants será allowlist revisada por tabela, comando e serviço.
4. **Definir contexto na transação que executa SQL protegido.** Contexto deriva de JWT validado e membership verificada na API. Em workers, cada unidade de trabalho é associada a um Tenant resolvido pelo job confiável. Uma sessão não alterna entre Tenants; jobs diferentes usam sessão/transação separada.
5. **RLS por classe de dados, não pela presença isolada de `tenant_id`.** Dados privados usam policy por Tenant. Filhas sem coluna direta recebem isolamento relacional ou mecanismo equivalente comprovado. Catálogos globais preservam leitura global, mas escrita global fica separada. Dados de plataforma e objetos técnicos têm grants/policies administrativos específicos.
6. **Não ampliar policy com `OR tenant_id IS NULL` para todos os comandos.** Global legível não significa global editável. Policies permissivas antigas que autorizem escrita global devem ser substituídas ou limitadas antes de adicionar as novas; policies `PERMISSIVE` combinam permissões por OR.
7. **Não transformar `app.current_tenant_id` em fronteira contra SQL arbitrário.** O GUC é uma afirmação do backend confiável e protege contra queries esquecidas sem filtro; uma role PostgreSQL comum capaz de executar SQL também pode tentar definir um GUC customizado. Proteção contra injeção SQL, exposição de credenciais e autorização de código continua necessária. Nenhum plano presume que RLS autentique por si só o Tenant.

## 3. Roles e fronteiras de acesso

Os nomes abaixo são rótulos de projeto, não roles criadas. SQL na seção 5 é proposta para revisão em banco descartável, nunca para execução nesta etapa.

| Role proposta | Login | Uso | Limites obrigatórios |
|---|---|---|---|
| `df_object_owner` | Não | Owner de schema e objetos de aplicação; role de propriedade `NOLOGIN`. | Sem uso por processo; sem membership runtime. `NOBYPASSRLS`, `NOSUPERUSER`; ownership não é grant de runtime. |
| `df_deployer` | Credencial de uso controlado | Alembic e operações estruturais aprovadas, assumindo `df_object_owner` quando necessário. | Secret separado, sem montagem em API/workers; `NOINHERIT`; acesso auditado e fora da rotação cotidiana de aplicação. Não conceder `BYPASSRLS` por conveniência. |
| `df_api_runtime` | Sim | Requisições normais da API. | Sem ownership, bypass, superuser, membership de deploy ou grants de manutenção; DML por allowlist e policies. |
| `df_job_dispatcher` | Sim | Resolver quais Tenants ativos têm trabalho; selecionar apenas as colunas mínimas, inicialmente `tenants.id` e `tenants.ativo`. | Sem acesso a payload/outbox ou tabelas de negócio; sem DML. Cada job abre a conexão runtime própria e processa sob contexto tenant. |
| `df_outbox_runtime` | Sim | Claim/ack/retry de eventos e execução dos handlers autorizados. | Sem acesso global a payloads por padrão; dispatcher enumera Tenants e cada claim/handler é limitado ao Tenant. Grants de handler serão inventariados antes de definir a allowlist. |
| `df_automation_runtime` | Sim | Jobs de automação e tarefas agendadas. | Dispatcher pode enumerar apenas os identificadores/estado mínimo dos Tenants; configuração e dados são lidos em escopo por Tenant. |
| `df_background_runtime` | Sim | Jobs periódicos não cobertos pelos workers acima. | Dividir grants por jobs reais; leitura de tabela de Tenant sem contexto não é permitida por padrão. |
| `df_catalog_admin` | Sim, acesso separado | Escrita de registros globais nos catálogos explicitamente aprovados. | Sem bypass/ownership; policies só permitem linhas globais nos catálogos autorizados. Credencial/pool não compartilhado com os logins comuns; chamadas exigem permissão de aplicação e trilha de auditoria. |

Os três logins de worker são o alvo de privilégio mínimo. Se o inventário demonstrar que jobs não podem ser separados sem alteração ampla, uma role worker comum pode ser uma fase transitória **somente** com matriz de acesso compartilhada aprovada e sem capabilities de bypass; os limites de domínio ficam documentados como risco residual. O outbox é separado primeiro porque despacha payloads e toca muitos handlers.

Para administração de plataforma, a aplicação continua fazendo autorização RBAC. Impersonação validada seleciona o Tenant-alvo e usa `df_api_runtime` com aquele contexto; não recebe acesso transversal automático. Operações genuinamente globais (por exemplo, mutar catálogo global) usam o caminho `df_catalog_admin` apenas nas tabelas aprovadas. Leituras/alterações de outras tabelas de plataforma exigem inventário por endpoint, grants por coluna/objeto e policy dedicada; não se concede uma role “admin” com acesso irrestrito a todas as tabelas.

### Condição de ownership

As 350 tabelas, 33 sequences, três funções e schema estão atualmente owned por `deepfarms`, conforme 01C. A transição deve transferir ownership estrutural para `df_object_owner` e manter um principal de deploy sob controle separado. Não basta criar `df_api_runtime`: se continuar como owner ou herdar a role owner, poderá evitar policies ou usar privilégios implícitos. A única exceção observada a FORCE é `propriedade_imovel`; o runtime não deve ser owner. A decisão de habilitar FORCE nessa tabela será feita na migration da tabela, com teste e rollback, e não é necessária para tornar um runtime não-owner sujeito às policies atuais.

## 4. Matriz mínima de privilégios

A lista final deverá ser derivada de SQLAlchemy, SQL direto, rotas, workers, subscribers, jobs e migrations e validada em ambiente isolado. A tabela abaixo define o limite inicial, não presume que cada processo precise de todos os privilégios da classe.

| Recurso | API | Outbox | Automations | Background | Catalog admin / deploy |
|---|---|---|---|---|---|
| Database `farms` | `CONNECT` | `CONNECT` | `CONNECT` | `CONNECT` | `CONNECT`; deploy separado |
| Schema `farms` | `USAGE`; sem `CREATE` | `USAGE`; sem `CREATE` | `USAGE`; sem `CREATE` | `USAGE`; sem `CREATE` | Catalog: `USAGE`; deploy assume owner para DDL |
| Tabelas tenant-private | `SELECT/INSERT/UPDATE/DELETE` por uso comprovado e policies tenant | Somente outbox e tabelas chamadas pelos handlers mapeados | Tabelas de automação e domínio que cada job usa | Allowlist de cada job | Nenhuma por padrão |
| Filhas sem `tenant_id` | Só após definir regra via pai/FK ou policy relacional | Somente se handler exigir e policy relacional estiver testada | Somente escopo relacional validado | Idem | Nenhuma por padrão |
| Catálogos mistos global/tenant | `SELECT` global/tenant; DML apenas linhas do próprio Tenant | Leitura apenas quando handler usar | Leitura apenas quando job usar | Leitura apenas quando job usar | DML somente globais e apenas nos catálogos aprovados |
| Tabelas de plataforma | Grants por rota/coluna; sem leitura ampla por default | Nenhum por default | Dispatcher: somente `tenants.id/ativo`; runtime de domínio não enumera fora do escopo | Dispatcher: somente `tenants.id/ativo`; runtime de domínio não enumera fora do escopo | Allowlist separada; sem `BYPASSRLS` |
| Duas tabelas `deepfarms_install_*` | Nenhum | Nenhum | Nenhum | Nenhum | Deploy/instalação apenas |
| Sequences | `USAGE` somente onde insert usa `nextval`; `SELECT` apenas se código consulta sequence | Mesma regra por allowlist | Mesma regra | Mesma regra | Owner/deploy conforme migrations |
| Functions | `EXECUTE` só para chamada direta identificada | Idem, handlers | Idem | Idem | Deploy conforme criação. Views: nenhuma na fotografia do 01C. |
| Capabilities | Sem `CREATE`, `TRUNCATE`, DDL ou grant option | Sem capabilities elevadas | Sem capabilities elevadas | Sem capabilities elevadas | DDL apenas pelo processo de deploy aprovado; sem `SUPERUSER` por rotina. |

Detalhes para fechar antes de gerar GRANTs:

- `relacl`, `nspacl` e ACLs de sequences/functions aparecem NULL no snapshot, mas os privilégios efetivos ainda exigem expansão incluindo defaults PostgreSQL, `PUBLIC`, database-level, memberships e `has_*_privilege`.
- O extrato registrou zero default privileges customizados no escopo consultado. A proposta inicial é manter grants explícitos por migration/tabela; não usar default ACL global que dê DML a todo objeto futuro.
- Tabelas com IDs gerados por UUID não precisam de sequence. Das 33 sequences, conceder apenas as referenciadas por default/`nextval` nos objetos cujo runtime faz insert.
- As três funções encontradas são helpers de trigger/constraint e `SECURITY DEFINER=false`; identificar chamadas diretas. Não conceder `EXECUTE` em massa por serem funções de tabela.
- Migrations, repair/backfill, ownership, policy/grant e instalação não usam os logins persistentes de API ou workers.
- As tabelas técnicas de instalação não são candidatas ao runtime; consulta de saúde/versão deve usar mecanismo separado e explicitamente autorizado se houver necessidade operacional.

## 5. SQL proposto para revisão (não executar)

Os exemplos usam nomes de role ilustrativos, não incluem senhas e não constituem migration pronta. Devem primeiro ser testados no PostgreSQL 16 descartável com catálogo equivalente e submetidos a revisão de DBA/segurança. **Não executar em produção ou Hostinger.**

### 5.1. Roles sem privilégios elevados

```sql
-- Apenas proposta; credenciais de login devem vir do gestor de segredos.
CREATE ROLE df_object_owner
  NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE df_deployer
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE df_api_runtime
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE df_outbox_runtime
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE df_job_dispatcher
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE df_catalog_admin
  LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;

-- Validar a sintaxe de membership no PostgreSQL 16 isolado:
GRANT df_object_owner TO df_deployer
  WITH INHERIT FALSE, SET TRUE;
```

Criar os demais logins runtime com os mesmos atributos restritos após aprovação da matriz. A senha/secret é provisionada fora do SQL versionado. Nenhum runtime recebe membership de `df_object_owner` ou `df_deployer`. Não alterar a role `deepfarms` em produção como parte deste plano.

### 5.2. Grants nominativos

```sql
-- Database e schema: conferir ACLs existentes antes de qualquer REVOKE.
GRANT CONNECT ON DATABASE farms TO df_api_runtime;
GRANT USAGE ON SCHEMA farms TO df_api_runtime;
GRANT CONNECT ON DATABASE farms TO df_job_dispatcher;
GRANT USAGE ON SCHEMA farms TO df_job_dispatcher;

-- Dispatcher global só pode enumerar IDs e status ativo dos Tenants.
GRANT SELECT (id, ativo) ON TABLE farms.tenants TO df_job_dispatcher;

-- Exemplo ilustrativo: trocar pela allowlist analisada de uma tabela tenant.
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE farms.exemplo_tenant
  TO df_api_runtime;

-- Incluir apenas quando a coluna/default usa sequence.
GRANT USAGE ON SEQUENCE farms.exemplo_id_seq TO df_api_runtime;

-- Só quando um caminho chama a função diretamente.
GRANT EXECUTE ON FUNCTION farms.exemplo_funcao(uuid) TO df_api_runtime;
```

Não incluir `GRANT ALL ON ALL TABLES/SEQUENCES/FUNCTIONS`, não revogar `PUBLIC` de forma global e não aplicar `ALTER DEFAULT PRIVILEGES` genérico. Cada REVOKE precisa ser calculado contra usos de ferramentas, health checks e operações legítimas de outros serviços.

### 5.3. Contexto de Tenant por transação

```sql
-- Dentro da transação e antes do primeiro acesso tenant-scoped.
-- :tenant_id é bind parameter originado de identidade validada, nunca SQL interpolado.
SELECT set_config('app.current_tenant_id', CAST(:tenant_id AS text), true);

-- Inspeção de diagnóstico dentro da mesma transação isolada:
SELECT current_setting('app.current_tenant_id', true);
```

`true` dá escopo local à transação e elimina resíduo de GUC após commit/rollback. Cada transação subsequente precisa reaplicar contexto. O código atual usa `SET LOCAL` em `get_session()`/outbox e `set_config(..., false)` em schedulers ERP/recomendações. O trabalho futuro deve substituir o estado de sessão por helper/context manager comum ou hook transacional validado, sem permitir que uma mesma `AsyncSession` troque de Tenant. Queries com `get_db()`/`get_db_session()` precisam ou receber contexto pelo helper aprovado, ou ser justificadas como dispatch/global antes de qualquer SQL.

### 5.4. Forma-alvo de policies (esquemática)

```sql
-- Exemplo para tabela UUID tenant-private. Reproduzir apenas depois de revisar a tabela.
ALTER TABLE farms.exemplo_tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.exemplo_tenant FORCE ROW LEVEL SECURITY;

CREATE POLICY exemplo_select_tenant ON farms.exemplo_tenant
  FOR SELECT TO df_api_runtime
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY exemplo_insert_tenant ON farms.exemplo_tenant
  FOR INSERT TO df_api_runtime
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY exemplo_update_tenant ON farms.exemplo_tenant
  FOR UPDATE TO df_api_runtime
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY exemplo_delete_tenant ON farms.exemplo_tenant
  FOR DELETE TO df_api_runtime
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```

Para colunas `varchar`, políticas de comparação textual não devem fazer cast UUID. Para coluna nullable/global, a policy de `SELECT` pode permitir `(tenant_id IS NULL OR tenant_id = contexto)` se a semântica global estiver comprovada; `INSERT/UPDATE/DELETE` tenant devem exigir `tenant_id = contexto`. Mutação global pertence a policy exclusiva `TO df_catalog_admin`, com `USING` e `WITH CHECK` limitados a `tenant_id IS NULL`. Policies PostgreSQL `PERMISSIVE` combinam por OR: remover/reescrever a policy ampla anterior faz parte da mesma migration, não basta adicionar uma policy mais restrita.

Exemplo de semântica desejada para `cadastros_produtos` (esquemático; repetir apenas para catálogos cuja regra de domínio foi confirmada):

```sql
ALTER TABLE farms.cadastros_produtos ENABLE ROW LEVEL SECURITY;
ALTER TABLE farms.cadastros_produtos FORCE ROW LEVEL SECURITY;

CREATE POLICY produto_select_global_ou_tenant ON farms.cadastros_produtos
  FOR SELECT TO df_api_runtime
  USING (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
  );
CREATE POLICY produto_insert_tenant ON farms.cadastros_produtos
  FOR INSERT TO df_api_runtime
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
CREATE POLICY produto_update_tenant ON farms.cadastros_produtos
  FOR UPDATE TO df_api_runtime
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
CREATE POLICY produto_delete_tenant ON farms.cadastros_produtos
  FOR DELETE TO df_api_runtime
  USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);

CREATE POLICY produto_global_admin ON farms.cadastros_produtos
  FOR ALL TO df_catalog_admin
  USING (tenant_id IS NULL)
  WITH CHECK (tenant_id IS NULL);
```

Este exemplo pressupõe grants de tabela para ambas as roles, credencial admin realmente separada e remoção de qualquer policy permissiva antiga que abra escrita global. A policy não substitui RBAC e auditoria na aplicação; não existe DML de Tenant sobre linha NULL.

## 6. Classificação de tabelas e proteção incremental

As 301 tabelas sem RLS não são um único risco nem um único lote. A classe e os privilégios devem ser registrados para cada uma das 350 tabelas físicas reconciliadas:

| Classe | Critério e tratamento | Prioridade |
|---|---|---|
| Tenant privada com `tenant_id NOT NULL` | 210 tabelas sem RLS têm coluna direta não nula. Confirmar consumidores e semântica; conceder DML só ao serviço necessário, ativar policy por tenant e FORCE quando apropriado. Validar todas as escritas, `tenant_id` imutável e índices. | Obrigatória antes de liberar acesso multi-tenant pelo novo runtime, se alcançável pela API/worker. |
| Tenant nullable | 20 sem RLS; duas outras nullable, `modelos_fitossanitarios` e `modelos_zoosanitarios`, já têm RLS/FORCE e policy NULL global nos quatro comandos. Classificar cada linha NULL como catálogo compartilhado, configuração da plataforma, ou associação ausente; ler global não deve implicar mutação global. | Semântica e grants de cada tabela são gate de lançamento para as acessíveis. As duas policies existentes exigem revisão específica de escrita global. |
| Filha tenant-scoped sem `tenant_id` direto | Aplicar policy relacional (`EXISTS` com pai e relação validada) ou constraint/estrutura composta apropriada. As 59 FKs a partir de 42 tabelas sem coluna direta são o primeiro conjunto; 38 dessas tabelas não têm RLS. Quatro tabelas filhas já têm policy relacional. | P1 nas filhas com PII, finanças, credenciais, documentos, estoque e acesso; não liberar se depender de filtros não testados. |
| Tenant associada sem FK estrutural ou referência `varchar` | Oito `tenant_id` varchar não têm FK para `tenants(id)`. Confirmar sintaxe/semântica de valores e todos os caminhos de leitura/escrita. | Gate de isolamento para as tabelas usadas por Tenants; padronização de tipo pode aguardar quando integridade for validada. |
| Catálogo global/misto | Tenants têm SELECT global e próprio; `INSERT/UPDATE/DELETE` limitado a suas linhas. Registros globais só são escritos por administração autorizada em login/policy dedicada. Inclui catálogo de produtos, preservando cadastro próprio do Tenant e leitura global. | Obrigatória para catálogo ativo antes de permitir DML de Tenant. |
| Plataforma/administração | `tenants`, backoffice, billing, impersonação, auditoria e controle de acesso são objetos de plataforma, não globais de leitura pública. Matriz de rotas/colunas e policies/grants administrativos estreitos. Impersonação usa Tenant-alvo validado e contexto comum. | Acesso direto pela API exige classificação e teste antes de role cutover; objetos sem uso operacional podem ficar sem grant runtime. |
| Técnica/instalação | `deepfarms_install_manifest` e `deepfarms_install_version` são auxiliares clean-install. | Excluir de todos os grants runtime; manter no fluxo deploy/install. |

### Fronteiras de lançamento

- **Obrigatório antes de lançamento multi-tenant:** nenhuma sessão de API/worker usa `deepfarms` ou outra role com bypass; todo dado privado alcançável tem RLS ou controle alternativo formalmente aprovado e testado; todas as 210 tabelas NOT NULL privadas acessíveis e todas as filhas sensíveis são cobertas; as 20 nullable acessíveis têm semântica e leitura/escrita decididas; catálogos globais não podem ser mutados por role Tenant; todas as 49 policies existentes passam sob runtime restrito; dispatch dos workers é funcional sem leitura desescopada de payload/dado privado.
- **Não é requisito aplicar a mesma policy às 301 sem RLS.** Semântica de dados globais, plataforma e técnico pode exigir policies distintas ou ausência de grant runtime.
- **As 464 FKs não exigem todas uma migration antes de lançar.** É requisito corrigir ou comprovar validação cross-tenant nas relações de dados sensíveis e nos fluxos que aceitam IDs de outro objeto. Relações restantes ficam em backlog priorizado e não podem ser declaradas seguras sem dono e mitigação documentados.
- **P0 atual é absoluto:** enquanto qualquer serviço exposto usar `SUPERUSER`/`BYPASSRLS`, RLS não constitui barreira de isolamento.

## 7. Contexto, transações, pool e jobs

### API

No código lido, `TenantRLSMiddleware` copia uma claim do JWT para `request.state`; `get_session()` usa `_resolve_request_tenant_id()` e `_activate_session_tenant()` para executar `SET LOCAL`. A dependência `get_tenant_id()` valida o tenant/associação e o header não deve prevalecer sobre a claim. A origem autoritativa para contexto deve continuar sendo a claim validada/membership verificada, não valor do body/header. `get_db()` e `get_db_session()` só criam sessões e não ativam contexto automaticamente. Endpoints que as usam precisam ser inventariados por chamada e classe de dados.

`SET LOCAL` expira ao encerrar a transação. Há reativação explícita após commit em `require_module`, mas não prova cobertura global de todos os commits internos. A ativação usa atualmente SQL interpolado com UUID; a implementação futura deve usar bind parameter `set_config(..., true)`. Plano de código: helper único com identidade de Tenant imutável na sessão, aplicado ao início de **cada** transação e testado após commit/rollback. Se uma transação nova for aberta, contexto deve ser reaplicado antes da consulta protegida. Falha de configuração deve encerrar o fluxo fechado, nunca continuar sem contexto.

### Workers e schedulers

- **Outbox:** `claim_batch()` permite `tenant_id=None`, o que remove o filtro tenant da query. Com role sem bypass, a policy da tabela deve impedir varredura global; para continuar processando, o dispatcher lista apenas IDs de Tenants ativos via privilégio estreito de coluna e faz claim/handler em transação por Tenant. Mapear cada subscriber e suas tabelas antes de autorizar o handler. Limitar leitura de payload a eventos do Tenant em execução.
- **Automations:** `automacoes/worker.py` seleciona configurações vencidas globalmente e, depois, passa `cfg.tenant_id` ao service; necessita de dispatch tenant-aware. Iterar por Tenant e buscar configurações dentro do contexto; transação por unidade de trabalho. A sessão compartilhada hoje sobrevive a commits no loop, portanto não alternar GUC de sessão.
- **Background:** jobs distintos usam `async_session_maker()` ou serviços/schedulers. Classificar cada loop; jobs de faturamento, envio/resumo, ERP, recomendação, vencimentos, depreciação e sync não recebem grants automaticamente iguais. Dispatcher global acessa o conjunto mínimo de IDs, operações por Tenant ocorrem em sessão isolada.
- **Schedulers ERP e recomendações:** hoje usam `set_config(..., false)` e `RESET`/invalidação em helpers. Migrar para contexto local por transação; se commits internos exigirem GUC de sessão, refatorar o escopo transacional ou rearmar contexto em cada transação. Erro no cleanup invalida conexão; provar via testes.
- **Evento transacional:** subscribers que fazem `set_config(..., true)` devem manter o contexto na mesma transação das escritas e não vazar a sessão para outra unidade.

O engine local configura `pool_size=3`, `max_overflow=2`, `pool_pre_ping`, `pool_recycle=1800`, timeout de pool e timeouts de PostgreSQL; são limites por processo. Quatro processos backend podem chegar nominalmente a 20 conexões simultâneas, além de sobreposição de deploy/instâncias e eventual `run_embedded_jobs`. O default de código para `run_embedded_jobs` é falso, mas o valor efetivo Hostinger precisa ser confirmado sem imprimir ambiente. Dimensionar pools e `max_connections` com a operação real; connection count não substitui isolamento.

## 8. Arquivos e artefatos previstos na implementação futura

Nenhum destes arquivos foi alterado nesta etapa. A revisão de implementação deve restringir mudanças a itens confirmados pelo mapa de consumidores:

| Área | Arquivos prováveis | Mudança planejada |
|---|---|---|
| Conexão e sessão | `services/api/core/config.py`, `core/database.py`, `core/dependencies.py`, possivelmente `main.py` | URLs por role/processo, helper/contexto transacional, fail-closed, contexto rearmado em toda transação, sem GUC de sessão. |
| Outbox | `services/api/events/outbox_service.py`, `outbox_worker.py`, `outbox_relay.py`, subscribers de domínio | Dispatch/claim por Tenant, evitar `tenant_id=None` em query de payload, grants e transações por handler. |
| Automação/background | `services/api/automacoes/worker.py`, `core/background_worker.py`, `core/background_jobs.py`, `recommendations/scheduler.py`, `integracoes/erp/scheduler.py` e outros jobs que o mapa identificar | Isolar sessão/transação por Tenant; separar dispatch e execução; cleanup após erro/cancelamento. |
| Catálogos / backoffice | Services, routers e dependencies dos catálogos e operações de plataforma tocadas pelo inventário | SELECT global/tenant; global write por autorização e caminho DB próprio; auditoria. |
| Schema/contrato de baseline | `services/api/migrations/baseline_contract.py`, próxima versão em `services/api/migrations/versions/` | Policies/grants/ownership graduais e reversíveis, revisadas contra catálogo físico; não criar migration nesta etapa. |
| Compose e segredos | `docker-compose.prod.yml` local e Compose efetivo da Hostinger em `/opt/deepfarms/farm/docker-compose.hostinger.yml` | URLs/segredos separados por processo; não colocar secret no Git nem compartilhar `deepfarms`; revisar health/deploy/rollback. O arquivo Hostinger não está neste checkout. |
| Testes | `services/api/tests/integrity/`, `tests/e2e/`, testes unitários de database/workers e fixture de Tenant | Testes SQL com role restrita em PostgreSQL isolado, fixtures A/B, pool e comportamento negativo. |

O Compose versionado `docker-compose.prod.yml` envia o mesmo `./services/api/.env.production` aos quatro serviços. A implementação futura deve substituir essa configuração comum por fontes de segredo/URLs adequadas a cada role, com configuração efetiva validada em clone de implantação. Não editar o Compose Hostinger por suposição.

## 9. Plano de testes (ambiente isolado)

Usar PostgreSQL 16 descartável ou ambiente isolado restaurado com schema e dados sintéticos. Criar Tenants A/B e usuários distintos, sem copiar linhas sensíveis de produção. Os logins de teste devem ter `rolsuper=false`, `rolbypassrls=false`, não ser owners e não pertencer a roles eleváveis. Nenhum teste de escrita usa a Hostinger.

Os testes E2E existentes de tenant verificam parte do comportamento da API, mas não são prova de RLS enquanto a conexão puder usar a role privilegiada informada no 01C. A fixture `services/api/tests/fixtures/tenant_context.py` define GUC com `SET` de escopo de sessão; ela não comprova isolamento entre conexões de pool reutilizadas nem substitui uma fixture explicitamente conectada com runtime role não-owner. Os testes de integridade de FK existentes cobrem lotes determinados, não todas as 464 relações físicas sem tenant composto.

| Grupo | Cenário negativo/positivo | Critério de aceite |
|---|---|---|
| Identidade de role | Inspecionar `current_user`, `session_user`, `pg_roles`, membership, owner e privilégios efetivos de cada serviço | Nenhuma runtime role é superuser/bypass/owner nem consegue `SET ROLE` para owner/deploy/admin. `has_*_privilege` só retorna grants allowlisted. |
| SELECT | A lê próprios registros e globais aprovados; B tenta consultar ID de A; sem contexto tenta listar | A e B veem só linhas próprias/globais autorizadas; B e ausência de contexto não retornam dados de A. |
| INSERT | B insere linha com `tenant_id=A`; B tenta global `NULL`; A insere própria | Spoof e NULL global por runtime comum são negados; A próprio passa. |
| UPDATE/DELETE | B tenta alterar/excluir ID de A; Tenant tenta editar linha global; catalog admin altera global autorizada e tenta tabela/linha fora da allowlist | Operações cruzadas e escrita global do Tenant são negadas; administração global permitida apenas nos catálogos aprovados, sem acesso lateral. |
| Contexto de transação | A→commit→nova transação; A→rollback; exceção; cancelamento; troca para B; sessão devolvida ao pool e reusada sem contexto | Contexto é rearmado por transação; não persiste no pool; sessão de A não é reusada para B; cleanup falho invalida conexão. |
| GUC inválido | `NULL`, vazio e UUID malformado em policies UUID/texto | Ausência é deny-by-default; valor malformado não abre visibilidade (erro controlado quando policy exige cast); nenhuma query protegida prossegue sem contexto. |
| API e RBAC | JWT A pede ID de B, header/body tenant discordante, backoffice sem permissão e impersonação aprovada | Tenant vem de identidade validada; chamadas cross-tenant retornam 404/403 conforme contrato; impersonação seleciona só tenant autorizado e audita. |
| Workers | Outbox claim global, retries/dead-letter; automações de dois Tenants; background scheduler alterna A/B; erro em handler | Dispatch só enumera dados mínimos; payload/queries e mutações ficam em Tenant correto; falha de A não mantém contexto nem aborta incorretamente B. |
| Tabelas filhas/FKs | Tenant B usa ID de pai A em insert/update; tenta leitura direta da filha; testa linha global legítima | FK/policy ou validação de serviço rejeita vínculo cruzado; filha não expõe PII/financeiro/documento do pai A; catálogo global intencional funciona. |
| Catálogos | Tenant lê produto/categoria/tipo de serviço global; cadastra seu produto; tenta alterar global; catálogo admin altera global e tenta produto particular de outro Tenant | Leitura global mantida; operações de Tenant ficam na linha própria; escrita administrativa não atravessa escopo Tenant. |
| Regressão funcional | Fluxos API e worker essenciais, import/export, seeds, jobs e saúde do banco | Nenhum fluxo necessário depende de `deepfarms`, owner, DDL ou SELECT global acidental; filas/backlog avançam e erros são observáveis. |
| Carga/conexões | API e workers sob carga sintética, rotação/conexão perdida, restart/cancelamento | Pools respeitam limites; nenhum `idle in transaction`/context leak; capacidade suficiente com headroom e sem crescimento de backlog. |

Não usar apenas teste que confirma `SET LOCAL`: teste precisa observar resultado real das operações sob role não privilegiada. Instalar policy e fazer teste com superuser não é evidência de isolamento.

## 10. Ordem de implementação e critérios de avanço

| Fase | Trabalho futuro | Gate de saída |
|---|---|---|
| 0 — Fechar evidência | Em clone/ambiente autorizado, expandir ACLs (database, schema, tabelas, sequences, funções, `PUBLIC`, memberships), identificar objetos acessados por cada processo e validar Compose/config efetiva sem imprimir segredos. | Matriz exata de objetos/comandos/consumidores; revisão de build/digest implantado; nenhum segredo em relatório/log. |
| 1 — Especificar semântica | Classificar as 350 tabelas como tenant-private, filha/inherited, global/mista, plataforma ou técnica; mapear nullability, CRUD, FK parent e rota/job. Resolver os 20 nullable e os dois policies globais de modelos. | Cada tabela alcançável tem owner funcional, regra de leitura e escrita e teste esperado. Nenhuma classe inferida só por ausência de `tenant_id`. |
| 2 — Provar contexto em laboratório | Ajustar helper transacional e os três trabalhadores; montar DB descartável, roles restritas, tenants A/B e testar A→B/sem contexto, commits/rollbacks e handlers. | Grupo de testes da seção 9 passa; sem SQL de contexto interpolado ou GUC de sessão residual; jobs completam no Tenant correto. |
| 3 — Preparar roles e ownership em staging | Criar owner/deploy/runtime; mover ownership no clone; grants nominativos; validar DDL real da cadeia Alembic e tarefas de instalação; configurar segredos separados. | Nenhum runtime é owner/bypass/elevável; migrations executam pelo deploy; runtime conecta e executa os fluxos aprovados; deny-by-default confirmado. |
| 4 — Lote zero: políticas atuais | Com os novos logins, testar as 49 tabelas e 188 policies como estão; resolver `propriedade_imovel`/FORCE; adicionar grants precisos; medir falhas por serviço. | Testes positivos/negativos passam nas 49; nenhuma policy divergente; nenhum acesso depende do superuser atual. |
| 5 — Lotes de dados sem RLS | Adicionar policies e grants por domínio, começando por PII/credenciais/financeiro/acesso/estoque e demais privadas alcançáveis. Migrar filhas e catálogos com regra própria. Usar migrations pequenas e auditáveis. | Cada lote tem classificação aprovada, validação de dados/constraint, testes de role e caminho de rollback; funcionalidade essencial preservada. |
| 6 — Canary isolado e soak | Subir instâncias/processos de staging com cada URL/role proposta; tráfego sintético; observar API, backlog, erros, pool e logs. | Período de soak acordado sem cross-tenant, regressão crítica ou crescimento anormal de fila/conexões. |
| 7 — Plano de mudança de produção | Só após aprovação separada: backup/restore ensaiado, change window, migration order, compatibilidade aplicação/schema, rollback owner/deploy e comandos revisados. O 01D não autoriza execução em Hostinger. | GO formal de mudança, todas as gates desta seção satisfeitas e responsáveis on-call designados. |

## 11. Deploy e rollback

### Sequência de ativação futura

1. Backup/PITR confirmado e restore ensaiado em ambiente separado; salvar snapshot de grants, owners, políticas e estado Alembic.
2. Aplicar mudanças de schema/ownership/grants em lote pequeno pelo deploy aprovado. Não mudar `DATABASE_URL` dos serviços antes da validação do role canário.
3. Ativar policies antes de conceder DML/cortar runtime, validando `ENABLE`/`FORCE`, permissões e leitura/escrita global. A role `deepfarms` superuser não serve como canário, pois atravessa RLS.
4. Fazer deploy compatível com contexto transacional; iniciar primeiro um processo worker canário sem consumir tarefas irreversíveis (ou com fila/test data isolada), depois workers individualmente e por último API com tráfego controlado. Se worker não puder ser canariado sem tocar em dados reais, validar somente em staging e incluir health gate da operação antes da janela.
5. Substituir credenciais por processo sem imprimir URL, validar `current_user/session_user`, pool e erros. Nunca manter fallback silencioso para `deepfarms` caso a nova role falhe.
6. Observar autorização, 5xx, falha de `permission denied`, fila, lock, latência, conexão e dead-letter. Pausar o próximo lote diante de qualquer diferença inesperada.
7. Concluir por domínio somente após smoke funcional, negativos A/B, catálogo global e jobs aprovados. Encerrar/remove login antigo de runtime apenas após provar que não há processos/sessões usando-o; a credencial superuser permanece break-glass controlada, não em env de app.

### Gatilhos de rollback/pausa

- Qualquer dado de Tenant A retornado ou mutado pela identidade B, inclusive em filha, cache de sessão SQL ou worker.
- Leitura/escrita global fora da matriz aprovada, ausência de contexto aceita ou contexto residual após pool reuse.
- Worker perde payload/evento, duplica ação não idempotente, acumula backlog além do limite acordado ou processa com tenant divergente.
- Erro de privilégio bloqueia fluxo essencial, sequência/function necessária não autorizada, migration não reversível ou ownership inesperado.
- Pools excedem headroom do PostgreSQL, deadlocks/locks de DDL, aumento sustentado de latência/erro ou falha de recuperação.

Pausa: retirar tráfego/consumo do canário e preservar logs/metadados sem payloads sensíveis; não ampliar grants “até funcionar”. Corrigir em staging e repetir os testes.

Rollback de código/configuração volta ao artefato anterior compatível, mas mantém roles runtime sem bypass. Rollback de schema usa downgrade reversível ou migration compensatória previamente exercitada; restaurar backup/PITR apenas conforme RPO/RTO e decisão de incidente. **Não é estratégia de rollback reconectar aplicação como `deepfarms` superuser.** Se não houver caminho funcional seguro, suspender o fluxo afetado/entrar em manutenção e manter o bloqueio de lançamento até correção.

## 12. Obrigatório antes de lançamento versus backlog

### Bloqueadores obrigatórios antes do lançamento multi-tenant

- API e todos os workers utilizam logins sem `SUPERUSER`, `BYPASSRLS`, ownership ou membership elevável; sessão/role efetiva confirmada por processo.
- Ownership de objetos separado do runtime e deploy separado; ACL efetiva e grant mínimo revisados, inclusive database, schema, sequences, functions, PUBLIC e privilégios herdados.
- Todas as tabelas que o usuário/worker pode alcançar estão classificadas. Dado tenant-private tem RLS sob role efetiva ou alternativa formalmente justificada e demonstrada; tabelas filhas sensíveis não dependem de FK por `id` como se fosse isolamento.
- As 210 candidatas `tenant_id NOT NULL` sem RLS e acessíveis a runtime são protegidas por policy testada ou removidas dos grants de runtime até serem protegidas. As nullable expostas têm semântica resolvida e leitura/escrita separadas.
- Os 49 objetos com RLS/188 policies são provados sob role operacional restrita; `propriedade_imovel` e global NULL em modelos são aprovados com comportamento e política de administração definidos.
- Catálogos globais permanecem legíveis onde o produto exige; usuários de Tenant não alteram nem excluem linhas globais. Escrita global é restrita à administração autenticada e auditada.
- `app.current_tenant_id` vem de JWT/associação validada ou job confiável, é aplicado em todas as transações protegidas e não vaza após commit, rollback, falha ou cancelamento.
- Outbox, automations e background jobs enumeram Tenants com acesso mínimo e executam unidade por Tenant; retries, lock/claim e handlers continuam funcionais.
- Testes negativos/positivos sintéticos e regressão funcional passam em PostgreSQL 16 isolado; restore, rollback e observabilidade foram ensaiados.
- Compose e secrets efetivos da Hostinger são revisados; nenhuma URL privilegiada fica compartilhada por todos os serviços ou aparece em log/repositório.

### Backlog permitido, com risco/dono registrado

- Tornar todas as **464** FKs tenant-aware em uma única entrega não é requisito; priorizar relações sensíveis e caminhos reais. Demais constraints podem evoluir em lotes se validação de ownership estiver coberta, testada e documentada.
- Normalizar os oito `tenant_id varchar` para UUID pode ficar no backlog se os valores atuais forem validados, as policies/comparações forem corretas e a integridade referencial não for requisito de lançamento. Falha de validação de tenant nesses objetos bloqueia seus consumidores.
- Padronização textual das 188 policies pode ocorrer depois se as expressões existentes passarem semântica, ausência de contexto e testes de role. A divergência estilística sozinha não é bloqueador.
- Aplicar RLS às tabelas globais/técnicas/plataforma sem usuário runtime pode aguardar, desde que não recebam grant de runtime e o fluxo administrativo esteja definido.
- Revisão semântica de relações/constraints comprovadamente fora dos fluxos de lançamento e sem dados sensíveis pode permanecer backlog com owner e prazo; não declarar como coberta por RLS antes de implementar.
- Refatorações amplas de ORM, nova arquitetura de identidade, mudança de titularidade da assinatura e alteração geral de `search_path` não fazem parte deste plano.

## 13. Estimativa de esforço

Estimativa em esforço de engenharia/revisão, sujeita a ajuste após o mapeamento por endpoint e descoberta de integrações. Não inclui janela operacional, espera de aprovação, correção de dados nem incidentes de migration.

| Etapa | Estimativa |
|---|---:|
| ACL efetiva, consumers e Compose/roles por processo | 1–2 dias-pessoa |
| Semântica/classificação das tabelas e matriz CRUD | 2–4 dias-pessoa |
| Helper de contexto transacional + API/worker fixes | 2–4 dias-pessoa |
| Roles, ownership e grant matrix em ambiente isolado | 1–3 dias-pessoa |
| Policies e migrations graduais: lote atual e domínios prioritários | 4–8 dias-pessoa |
| Testes A/B, jobs, FKs prioritárias e regressão funcional | 3–6 dias-pessoa |
| Soak, backup/restore, ensaio de cutover e rollback | 1–3 dias-pessoa |
| **Total indicativo** | **14–30 dias-pessoa** |

O intervalo aumenta se houver dados órfãos, muitos handlers globais, dependência de credencial compartilhada em scripts ou migration não reversível. O maior driver de incerteza é mapear CRUD/consumidor nos 348 objetos ORM, não escrever a sintaxe das policies.

## 14. GO/NO-GO para iniciar em ambiente isolado

**GO condicionado para iniciar implementação em ambiente isolado e descartável**, limitada primeiro à role owner/deploy/runtime, contexto por transação e testes sintéticos do lote de policies já existente. Condições de início: PostgreSQL 16 isolado, sem URL/segredo/dado da Hostinger; fixture A/B; código/commit sob teste identificado; snapshots sintéticos de schema/policies; e role de teste efetivamente sem superuser, bypass ou ownership. Se qualquer conexão apontar para produção, parar antes de executar.

**NO-GO para iniciar migrations ou mudanças em Hostinger/produção, e NO-GO para cutover**, até todos os bloqueadores da seção 12 serem encerrados e o Compose efetivo ser revisado. Este documento não aprova nem executa mudanças na infraestrutura real.

## Referências

- [01C — Consolidação das evidências Hostinger](DEEPFARMS-RLS-HOSTINGER-01C-INVENTARIO-REAL.md)
- [01B — Plano de correção e matriz estrutural ORM](DEEPFARMS-RLS-HOSTINGER-01B-PLANO-CORRECAO.md)
- `services/api/core/database.py`, `core/dependencies.py`, `main.py`
- `services/api/events/outbox_service.py`, `events/outbox_worker.py`, `automacoes/worker.py`, `core/background_jobs.py`, `recommendations/scheduler.py`, `integracoes/erp/scheduler.py`
- `docker-compose.prod.yml` (versão local; não comprovada como Compose efetivo Hostinger)
- `/opt/deepfarms/farm/docker-compose.hostinger.yml` (caminho informado pelo operador; ausente deste checkout)
- `services/api/migrations/baseline_contract.py` e histórico Alembic; contrato de policies não substitui a fotografia física 01C
