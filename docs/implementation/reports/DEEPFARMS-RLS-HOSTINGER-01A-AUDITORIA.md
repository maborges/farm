# DEEPFARMS-RLS-HOSTINGER-01A — Auditoria de isolamento multi-tenant

**Modalidade:** auditoria somente leitura. Nenhum banco de produção foi consultado nesta execução. Não executei comandos Docker/SSH, migrations, testes, DDL/DML, alterações de privilégios ou reinicializações. Não li arquivos `.env` nem registrei valores de conexão. As propriedades do ambiente Hostinger descritas abaixo são as confirmadas pelo solicitante; a análise do código e dos contratos locais é identificada como evidência do repositório.

**Veredicto:** **NO-GO para liberar novos assinantes na configuração informada.** O motivo impeditivo é que API e workers conectam como `SUPERUSER` e `BYPASSRLS`; para essas conexões o PostgreSQL ignora as políticas RLS, inclusive `FORCE ROW LEVEL SECURITY`. Isso não recomenda interromper os serviços em operação por esta auditoria; significa que o isolamento RLS não pode ser considerado uma barreira de segurança até a separação do papel operacional e a validação real com dois tenants.

## 1. Escopo e evidências

| Evidência | Origem | Uso neste relatório |
|---|---|---|
| PostgreSQL 16, banco/schema `farms`, 350 tabelas, 49 com RLS, 48 com FORCE, 188 políticas; `propriedade_imovel` sem FORCE; papel `deepfarms` superuser e bypass; serviços usando o mesmo papel | Contexto confirmado pelo solicitante | Tratado como estado de produção reportado, não como resultado de uma conexão realizada nesta auditoria. |
| `get_session`, `get_db`, engine/pool, middleware e workers | Código em `services/api` | Evidência da propagação de contexto e dos caminhos sem injeção automática. |
| Compose de produção | `docker-compose.prod.yml` | Serviços, comandos e referência a arquivo de ambiente; os valores desse arquivo não foram lidos. |
| 348 tabelas e 188 policies | Contrato versionado atual `services/api/migrations/baseline_contract.py` | Inventário estático para comparar com a fotografia de 350 tabelas fornecida pelo solicitante. |
| Testes existentes | `services/api/tests` e documentação de baseline | Avaliação estática de cobertura; nenhum teste foi executado. |

Há uma diferença a reconciliar: `baseline_contract.py` declara 348 tabelas no contrato atual; o inventário RLS estático contém **230 tabelas sem RLS com `tenant_id` direto**, **69 sem `tenant_id` direto** e 49 com RLS. Isso soma 348, enquanto a fotografia de produção informada soma 350 (301 sem RLS). Portanto, **duas tabelas da fotografia de produção não estão identificadas pelo contrato estático usado aqui**. Não atribuo nomes nem classificação a essas duas sem o inventário físico atual.

## 2. Diagnóstico executivo

1. `TenantRLSMiddleware` extrai o tenant do JWT e o põe em `request.state`; a configuração PostgreSQL só é feita por determinadas dependências/caminhos de serviço.
2. `get_session()` aplica `SET LOCAL app.current_tenant_id` quando consegue resolver tenant do JWT. `get_db()` e `get_db_session()` não fazem isso automaticamente.
3. A conexão compartilhada não configura tenant no evento de `connect`; esse evento define somente isolamento `READ COMMITTED`. Portanto o contexto não é uma propriedade persistente e garantida de cada conexão do pool.
4. O uso de `SET LOCAL` é apropriado para limitar contexto à transação, desde que a operação permaneça na mesma transação e o tenant seja definido novamente após `commit`/`rollback`. Há fluxos com commits intermediários e restauração explícita do contexto.
5. Dois schedulers usam `set_config(..., false)`, que estabelece contexto de sessão, e possuem helpers de `RESET`; eles exigem que o cleanup seja chamado em todas as saídas antes da conexão voltar ao pool.
6. O worker de automações consulta regras agendadas entre tenants e depois instancia serviço com `cfg.tenant_id`. Jobs de background e outbox também têm tarefas globais ou multi-tenant. Esses casos precisam ser mantidos, mas executados com escopo tenant por tarefa, não com papel PostgreSQL que ignora RLS.
7. As 188 policies no contrato local usam `current_setting('app.current_tenant_id', true)`; 14 expressões usam subconsulta relacional. Todas aparecem como `PERMISSIVE TO PUBLIC`. Isso não concede privilégios de tabela por si só, mas significa que a separação não é feita por role nas policies; ACLs e RLS efetivo dependem do papel e dos grants.
8. A fotografia informa 301 tabelas sem RLS. O contrato estático local classifica 230 delas como tendo `tenant_id` direto. As restantes sem coluna podem ser globais, técnicas ou filhas que herdam tenant pela FK; ausência de coluna não prova dado global.

## 3. Estabelecimento e ciclo do contexto de Tenant

### 3.1. Requisições HTTP

Em `services/api/main.py:248-276`, `TenantRLSMiddleware` decodifica o token assinado, desativa somente a validação de expiração nessa etapa e grava `tenant_id` em `request.state.rls_tenant_id`. A autenticação/autorização efetiva é feita pelas dependências próprias. O middleware não obtém conexão SQL nem executa comando PostgreSQL.

Em `services/api/core/dependencies.py:62-69`, `_activate_session_tenant()` executa `SET LOCAL app.current_tenant_id = '<uuid>'` para PostgreSQL. `get_session()` chama essa função antes de entregar a sessão (`dependencies.py:138-175`). O tenant é resolvido de `request.state` ou do JWT (`dependencies.py:86-129`). A resolução autorizada do tenant também valida associação ativa do usuário e coerência de `X-Tenant-ID` em `dependencies.py:410-494`.

`SET LOCAL` dura até commit/rollback da transação PostgreSQL atual. O `async with` fecha a sessão HTTP e SQLAlchemy reverte transação ainda aberta; isso limpa o valor local ao devolver a conexão. Um `commit` dentro de serviço/endpoint encerra a transação e remove o GUC antes do próximo comando. O próprio código registra esse comportamento e reativa o tenant em `require_module()` após telemetria e commit (`dependencies.py:688-700`). Qualquer fluxo que faça commit/rollback intermediário precisa seguir a mesma regra.

**Falha fechada depende do papel operacional:** quando uma policy depende do GUC e ele não está definido, comparações `tenant_id = NULL` não autorizam linhas (há exceções explícitas, como linhas globais `tenant_id IS NULL` em algumas policies). No papel `deepfarms` informado, essa negação não acontece: superuser/BYPASSRLS ignora a policy mesmo sem contexto.

### 3.2. Sessões, pool e outros caminhos de banco

`services/api/core/database.py:21-40` cria uma engine por processo com `pool_size=settings.db_pool_size` (default 3), `max_overflow=settings.db_max_overflow` (default 2), `pool_pre_ping`, `pool_recycle=1800` e `pool_timeout`. Cada serviço/processo mantém sua própria engine/pool; os valores efetivos podem ser substituídos pelo ambiente. No default atual, os quatro processos backend do Compose poderiam manter até 20 conexões combinadas (5 por processo), sem contar engine legado ou réplicas.

O evento `connect` em `core/database.py:64-72` define `READ COMMITTED`; não instala nem remove `app.current_tenant_id`. Os três caminhos de sessão diferem:

| Caminho | Contexto automático | Observação de segurança |
|---|---|---|
| `core.dependencies.get_session()` | Sim, quando resolve tenant do request/JWT | Caminho preferido de endpoints tenant-scoped; contexto transacional local. |
| `core.database.get_db()` | Não (`core/database.py:74-88`) | Utilizado em pelo menos 28 arquivos de backend. Alguns endpoints podem ser globais ou aplicar contexto/filtros em outro ponto; cada um precisa de classificação própria antes de operar com RLS efetivo. |
| `core.database.get_db_session()` | Não (`core/database.py:91-100`) | Usado por workers, schedulers e rotinas. Deve receber contexto validado para cada tenant e transação. |

Existe também uma engine opcional de identidade legada em `agro_identity/database.py`; a configuração do serviço diz que está desativada por padrão. Não há evidência nesta auditoria de que ela participe dos quatro processos de produção mencionados.

`SET LOCAL` não precisa de `RESET` de sessão se a transação terminar corretamente. Já `set_config(..., false)` é sessão-scoped. `recommendations/scheduler.py:491-508` e `integracoes/erp/scheduler.py:245-263` implementam `RESET`, fazem commit da limpeza e invalidam a conexão se a limpeza falhar; esse padrão precisa ser coberto por teste de reutilização do pool. O código de produção pesquisado não registra um reset geral de GUC no checkout/checkin do pool.

### 3.3. Workers e tarefas entre tenants

O Compose `docker-compose.prod.yml:1-58` inicia API, `automations-worker`, `background-worker` e `outbox-worker`. Os quatro usam a mesma imagem backend e referenciam `./services/api/.env.production`; logo, pela configuração declarada, compartilham as credenciais/injeção de ambiente. O web só referencia a URL interna da API. O Compose versionado não declara um serviço PostgreSQL, portanto a topologia do container PostgreSQL não é inferida deste arquivo.

- `background-worker` executa ciclos de billing, alertas, ERP, recomendações, vencimentos, depreciação e sincronizações (`services/api/core/background_jobs.py:121-132`). Vários desses ciclos atendem todos os tenants.
- `automacoes/worker.py:13-61` abre `get_db_session()` sem tenant, consulta regras agendadas e depois cria o serviço com `cfg.tenant_id`; `run_alerts_check()` também dispara varreduras gerais (`automacoes/worker.py:74-110`).
- `outbox-worker` usa `get_db_session()` (`events/outbox_worker.py:19`) e expõe consultas agregadas que aceitam `tenant_id=None` (`outbox_worker.py:677-779`). A escrita tenant-scoped possui helper com `SET LOCAL` em `events/outbox_service.py:200-203`.
- O scheduler de recomendações enumera todos os tenants ativos sem contexto (`recommendations/scheduler.py:484-488`) e depois aplica contexto por tenant com `set_config(..., false)`. O scheduler ERP usa padrão semelhante.

Essas tarefas não exigem superuser por princípio. Precisam de um fluxo deliberado: enumerar alvos de modo restrito, abrir transação para cada tenant, definir `SET LOCAL`, processar só esse tenant e finalizar a transação. Para o outbox, uma opção mínima é iterar IDs de tenants ativos e ler/atualizar a fila sob o contexto de cada tenant. Tarefas realmente globais devem acessar somente tabelas globais específicas e ter finalidade/auditoria explícitas.

## 4. Como as policies usam o contexto

O contrato local está em `services/api/migrations/baseline_contract.py:196-247`; a baseline versionada aplica `ENABLE`/`FORCE` e recria as policies (`services/api/migrations/versions/20260908_baseline_deepfarms_v1.py:227-248`). O snapshot descreve 188 policies em 49 tabelas: 47 `SELECT`, 47 `INSERT`, 46 `UPDATE`, 46 `DELETE` e 2 `ALL`. As 188 são permissivas e listam `PUBLIC` como role; 188 consultam o GUC `app.current_tenant_id`, 52 usam `NULLIF`, e 14 incluem subconsultas relacionais.

O papel `PUBLIC` na policy **não** elimina a necessidade de `GRANT`: os privilégios de objeto são checados antes de uma operação; uma role sem `SELECT` ou `UPDATE` continua sem esse acesso. Porém, como as policies não distinguem o papel operacional do administrativo, os grants precisam ser mínimos e o runtime não pode ter `BYPASSRLS`, ser superuser ou possuir as tabelas.

Policies diretas normalmente filtram `tenant_id` em `USING` para leitura/alteração/exclusão e `WITH CHECK` para inserção e novo estado de update. As 14 policies com subconsulta indicam relações em que o tenant é derivado de entidade relacionada; essas expressões precisam ser verificadas com casos de FK cruzada e não podem ser substituídas por simples existência de `tenant_id` no ORM.

### O que `FORCE RLS` muda — e não muda

- `ENABLE ROW LEVEL SECURITY` ativa a policy para papéis comuns.
- `FORCE ROW LEVEL SECURITY` também sujeita o proprietário da tabela às policies, salvo exceções do PostgreSQL.
- Nenhuma dessas opções restringe superuser ou role com `BYPASSRLS`. Portanto a ausência de FORCE em `propriedade_imovel` **não é a causa principal do bypass atual**; com as credenciais confirmadas, ENABLE e FORCE são ambos ignorados.
- Para o futuro papel runtime `NOBYPASSRLS` que não seja dono da tabela, a policy de `propriedade_imovel` já se aplicaria mesmo sem FORCE. FORCE adiciona defesa caso o papel dono seja usado acidentalmente ou as ownerships mudem.

Há divergência histórica a reconciliar: `migrations/versions/add_propriedade_imovel.py:243-283` cria RLS, FORCE e quatro policies. Já o contrato do banco referência e o inventário local registram a tabela como ENABLE sem FORCE (`MIGRATION-METADATA-01C4B-FECHAMENTO-RLS-POLICIES.md:74-82`; `baseline_contract.py:214-220`). A razão funcional para remover FORCE não está documentada no contrato consultado. Antes de normalizar, confirmar propriedade da tabela e necessidade operacional; manter FORCE é recomendável se o runtime não for proprietário e não houver fluxo legítimo de owner que precise ignorar RLS.

## 5. Credenciais e necessidade de privilégios administrativos

O Compose de produção referencia um arquivo de ambiente compartilhado pelos quatro processos backend e não contém valores inline de conexão. O arquivo referenciado não foi lido. O usuário, database e schema do ambiente são os confirmados no contexto do solicitante. A conexão da engine define `search_path=farms` (`core/database.py:33-38`).

**Achado de segredo versionado:** há uma URL PostgreSQL literal em `services/api/scripts/kill_idle_connections.py:8`. O conteúdo foi omitido deste relatório e não foi usado. A validade/escopo dessa credencial não foram confirmados. Tratar como potencialmente exposta: em ação posterior aprovada, verificar se ainda é válida, revogá-la/rotacioná-la se ativa e remover o valor versionado sem reintroduzi-lo em logs ou relatórios.

Não identifiquei requisito de superuser para operações normais da API ou dos workers: a aplicação faz consultas e DML via SQLAlchemy, define GUC customizado, e o comando de produção da API inicia Uvicorn; Compose não executa Alembic nem DDL no startup. Migrations, criação de schema e tarefas de manutenção são atividades administrativas/de deploy e devem usar uma credencial distinta, não a mesma credencial dos processos persistentes. O `is_superuser` de claims/usuário da aplicação é uma autorização de negócio; não deve ser traduzido em `SUPERUSER` PostgreSQL.

`core/database.py` também faz fallback para SQLite quando a URL não parece PostgreSQL ou `asyncpg` não está disponível (`:8-19`), e `core/config.py:8-13` tem SQLite como default. Como a configuração de produção confirmada usa PostgreSQL, isso não prova falha atual; é risco de configuração silenciosa em deploy futuro. O processo de produção deve falhar fechado se o driver/backend não corresponder ao ambiente.

## 6. Classificação das tabelas sem RLS

**Não se presume que as 301 tabelas sejam todas vulneráveis.** A triagem precisa olhar finalidade, ownership, relações e consumidores, e não somente presença de `tenant_id`.

| Grupo | Contagem/evidência | Exemplos locais | Tratamento de segurança recomendado |
|---|---|---|---|
| Tabelas com `tenant_id` direto e sem RLS | 230 no contrato estático de 348 tabelas; a fotografia Hostinger contém 301 tabelas sem RLS e duas ainda não mapeadas pelo contrato. | `cadastros_pessoas`, `cadastros_propriedades`, `caderno_campo_entradas`, `campo_tarefas`, `faturas`, `assinaturas_tenant`, dados operacionais/financeiros e várias integrações. | Candidatas prioritárias a policy direta. Confirmar se `tenant_id` realmente define ownership, se há `tenant_id IS NULL` sistêmico e quais roles/jobs precisam de cada comando. Sem RLS, a role operacional pode ler todas as linhas que seus SQL consultarem. |
| Filhas tenant-scoped sem `tenant_id` próprio | Parte das 69 sem coluna direta. A FK aponta para entidade tenant-scoped; o contrato `tenant_scope_mode=GLOBAL` não captura essa herança semântica. | `cadastros_pessoas_pii`, `cadastros_pessoas_bancario`, documentos/contatos/endereço apontam para `cadastros_pessoas`; `compras_itens_pedido` aponta para pedido; recebimentos/itens apontam para pedidos/itens. | Não classificar como global. Preferir policy relacional que valida tenant no pai, ou outro mecanismo estrutural aprovado. PII/documentos/contas bancárias e detalhes financeiros têm alta prioridade. Garantir também consistência das FKs para impedir referências a pai de outro tenant. |
| Globais de negócio/catálogos | Parte das 69 sem coluna direta, confirmada individualmente por semântica e uso. | Catálogos de conhecimento, templates globais, plano de assinatura e tabelas de configuração/catálogo SaaS podem ser globais por produto. | Acesso global pode ser correto, mas conceder apenas leitura para runtime se possível; escrita só a operações administrativas necessárias. Dados de leads/ofertas não são automaticamente públicos por não terem tenant_id. |
| Identidade, suporte e auditoria global | Parte das tabelas sem tenant; não é sinônimo de baixa sensibilidade. | `usuarios`, `login_tentativas`, `admin_users`, `admin_audit_log`, tokens de recuperação. | Restringir ACL por função e expor por serviços autenticados. Login/rate-limit pode precisar de lookup global, mas API operacional não deve obter leitura irrestrita de credenciais, PII ou audit log sem necessidade. |
| Técnicas/controle de schema | Inclui objetos fora da baseline e as duas tabelas não reconciliadas. | `alembic_version` é explicitamente fora da baseline contratual; metadados de instalação e tabelas auxiliares precisam ser confirmados por nome no catálogo alvo. | A role runtime normalmente não precisa de DDL nem leitura de histórico de migrations; conceder a migrator/deploy. Não presumir que tabela técnica seja segura se guardar payload, identificadores ou dados por tenant. |

No código estático, o contrato marca tabelas sem política aprovada como `RLS_NOT_REQUIRED`, com motivo genérico “no approved RLS policy in reference contract” (`baseline_contract.py:223-247`). Essa marcação não documenta por si só que uma tabela é global nem justifica ausência de RLS. Além disso, o classificador local considera `tenant_scope_mode` como `DIRECT` se há coluna `tenant_id`, caso contrário `GLOBAL`; as tabelas-filhas acima mostram que essa regra é insuficiente para um veredicto de sensibilidade.

**Próxima evidência necessária para fechar as 301:** export read-only dos nomes das 350 tabelas e colunas `tenant_id`, FKs até raiz tenant, RLS/FORCE, policies, grants/owners e dependências por tabela no PostgreSQL `farms`. Mapear explicitamente as duas tabelas fora do contrato, e classificar cada objeto como `TENANT_DIRECT`, `TENANT_INHERITED`, `GLOBAL_REFERENCE`, `GLOBAL_ADMIN/SENSITIVE` ou `TECHNICAL`. Nenhuma leitura de dados de clientes é necessária para esse inventário.

## 7. `propriedade_imovel`: exceção sem FORCE

Estado confirmado pelo solicitante: RLS habilitado e FORCE desabilitado. O contrato static de 2026-09-08 registra a mesma exceção como `RLS_REQUIRED_NO_FORCE`; a migration inicial declara FORCE, indicando possível divergência de deployment ou decisão posterior não representada como justificativa explícita.

Impacto separado por papel:

- **Papel atual informado (`SUPERUSER` + `BYPASSRLS`):** policy não limita nada, com ou sem FORCE. A correção desta tabela isoladamente não restabelece isolamento.
- **Papel operacional `NOBYPASSRLS`, não proprietário:** a policy aplica-se mesmo sem FORCE. FORCE não é pré-requisito para este caso.
- **Papel operacional proprietário sem FORCE:** proprietário pode ignorar policy. Portanto, separar ownership e runtime é necessário; FORCE é uma defesa adicional recomendada depois de confirmar que não existe job legítimo usando owner como runtime.
- **Papel de migração/owner:** DDL deve usar essa credencial em janela controlada; não deve ser a credencial de API/workers.

As quatro policies locais usam `app.current_tenant_id`. A validação real deve cobrir leitura, tentativa de inserir/alterar `tenant_id` de outro tenant e exclusão entre tenants, primeiro com role runtime não proprietário e sem bypass. A alteração de FORCE fica para uma implementação posterior aprovada; não foi realizada nesta auditoria.

## 8. Lacunas dos testes existentes

Há testes de isolamento HTTP e de relações tenant-scoped:

- `services/api/tests/e2e/test_tenant_isolation.py`: lista de safras e receitas, acesso por ID direto e token sem tenant.
- `services/api/tests/e2e/test_caderno_tenant_isolation.py`: leitura de entradas, acesso por ID e outros recursos do caderno.
- `services/api/tests/e2e/test_reports_agricola_tenant_isolation.py`: relatórios, talhões e detalhe entre tenants.
- `services/api/tests/integrity/test_tenant_fk_guardrails.py`: FKs, índices e alguns cruzamentos/guardrails estruturais; não comprova enforcement RLS em todas as tabelas.
- `services/api/tests/fixtures/tenant_context.py`: define contexto de teste com `SET app.current_tenant_id` e tenta `RESET` ao final.
- `services/api/migrations/baseline_contract.py` e testes do contrato: validam estaticamente nomes/contagem das policies, não seu efeito em runtime.

Limitações relevantes:

1. Os E2E verificam comportamentos de endpoints e filtros; não constituem prova de policy PostgreSQL se a conexão de teste for superuser/BYPASSRLS. Não encontrei assertion nesses testes que exija `rolsuper=false`, `rolbypassrls=false` e usuário diferente do owner.
2. A fixture de sessão em `services/api/tests/conftest.py:104-133` usa `Base.metadata.create_all`/setup de teste e captura falhas de setup. Isso é conveniente para integração, mas não demonstra que uma instalação Hostinger com grants mínimos funcione.
3. Testes podem pular operações quando preparação/endpoint de Tenant B falha; uma suite verde pode perder cobertura se skips não forem tratados como bloqueadores.
4. Não há prova localizada de ciclo SQL direto em role sem bypass que tente `SELECT`, `INSERT`, `UPDATE` e `DELETE` cross-tenant para cada classe de policy.
5. Não há teste de uma única conexão física reutilizada alternando A→B→sem contexto→A após commit, rollback e exceção.
6. Não há cobertura clara de acesso child-table por FK (por exemplo, PII/pagamentos e itens de compras) sem filtrar o pai pelo tenant.
7. `lixo/scripts/testes/test_rls.py` fica fora da suite ativa e não substitui validação no PostgreSQL com role operacional.
8. O próprio contrato de baseline mantém `POSTGRESQL_VALIDATION_PENDING` para RLS/policy/tenant isolation (`baseline_contract.py`); isso é confirmação documental de que a validação real ainda é gate separado.

## 9. Proposta mínima de separação e permissões

Manter PostgreSQL, schema, API, workers, Compose e políticas tenant existentes. A mudança necessária é separar credenciais/ownership e passar o runtime a respeitar o contexto; não é adicionar serviço ou banco.

### Papel administrativo de schema/deploy

- Credencial distinta, protegida e usada somente em deploy/manutenção autorizados.
- Responsável por migrations e DDL; sem uso em API, automations-worker, background-worker ou outbox-worker.
- Se houver role owner `NOLOGIN`, conceder membership/`SET ROLE` ao migrator só para a janela de mudança. Não compartilhar essa membership com runtime.
- Não requer superuser para CRUD normal. Conceder privilégios elevados apenas se uma migration específica e revisada realmente precisar; nunca armazenar a credencial em imagem ou log.

### Papel operacional compartilhado pelos quatro processos backend

- `LOGIN`, `NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE`; não ser owner de tabelas nem membro de role que seja owner/BYPASS.
- `CONNECT` ao database e `USAGE` no schema `farms`.
- `SELECT/INSERT/UPDATE/DELETE` somente nas tabelas necessárias ao runtime; `USAGE`/`SELECT` em sequences necessárias; `EXECUTE` apenas nas funções utilizadas.
- Sem `CREATE` no schema, `TRUNCATE`, alteração de policy, ownership, DDL ou acesso a outros schemas sem necessidade comprovada.
- Nas tabelas tenant-scoped com policy, respeitar contexto `SET LOCAL` por transação e `WITH CHECK`. Tabelas globais devem receber grants limitados; tabelas child devem ter policy relacional ou outra proteção estrutural validada.
- Não conceder `BYPASSRLS` aos workers para facilitar jobs globais. Reescrever a operação em iteração tenant por tenant usando mesmo papel runtime. Se uma exceção sistêmica for inevitável, tratá-la como serviço administrativo separado, limitado, auditado e fora do pool geral da API.

O conjunto acima é uma proposta de privilégio-alvo, não a constatação dos grants efetivos. A consulta de `pg_roles`, `pg_auth_members`, `pg_class.relowner`, `information_schema.role_table_grants` e `pg_default_acl` precisa ser read-only e versionada como evidência antes de implantar.

## 10. Plano de testes reais entre dois tenants

Executar futuramente em clone de homologação que reproduza schema/policies/grants, nunca contra o banco de produção. Usar Tenant A e B, dois usuários válidos, a role runtime real não proprietária e `NOBYPASSRLS`. Confirmar a identidade SQL usada no teste sem imprimir URL/segredo.

1. **Preflight da role:** verificar que `rolsuper=false`, `rolbypassrls=false`, a role não é owner e não herda membership privilegiada. Confirmar RLS/FORCE/policies dos alvos pelo catálogo.
2. **Fixtures:** criar um registro marcador por tenant em tabela direta com RLS; criar também registro em tabela child que deriva tenant por FK. Fazer setup com papel de fixture controlado, fora do papel testado; nenhum seed compartilhado entre A e B.
3. **Leitura:** em transação A, executar `SET LOCAL app.current_tenant_id = A`; SELECT lista e consulta por ID devem retornar apenas A e zero linhas de B. Repetir para B. Sem contexto, SELECT deve retornar zero linhas onde policy exige tenant.
4. **Inserção:** A insere linha A com sucesso; A tenta inserir `tenant_id=B` e deve receber violação de policy. B não deve enxergar nem referenciar linha de A por chave direta.
5. **Atualização:** A altera registro A com sucesso; update por ID de B deve afetar zero linhas. Tentativa de trocar `tenant_id` A→B deve falhar por `WITH CHECK`.
6. **Exclusão:** A deleta a própria linha; delete por ID de B deve afetar zero linhas. Confirmar que nenhum cascade/trigger remove dados do outro tenant.
7. **Tenant herdado por FK:** repetir SELECT/INSERT/UPDATE/DELETE sobre PII, documento/banco de pessoa e item/recebimento de compra, garantindo que filtro do pai é aplicado pela policy/estrutura e que FK cruzada A→B é negada.
8. **Reuso de conexão:** forçar pool de uma conexão. Alternar A → commit → B → rollback → sem contexto → exceção dentro da transação → A. Após cada fronteira, consultar `current_setting('app.current_tenant_id', true)` e provar que a linha de tenant anterior não está visível. Repetir com `close()` e checkout seguinte.
9. **Workers:** enfileirar uma tarefa por tenant e executar dispatcher/worker. Cada lote deve processar só o tenant corrente, com payload/outbox de B invisível ao ciclo A e vice-versa; confirmar cleanup ao falhar um item.
10. **`propriedade_imovel`:** realizar CRUD cross-tenant com papel runtime não owner; testar também owner sem FORCE em clone para demonstrar a diferença e então validar a decisão de FORCE. O teste não usa superuser como resultado de segurança.
11. **API:** repetir listagem, ID direto, payload com ID de propriedade/pessoa de outro tenant e atualização/exclusão via endpoints, usando a role de produção-alvo.
12. **Pass criteria:** zero leitura/escrita/exclusão cross-tenant; todas as operações próprias funcionam; sem contexto falha fechada; nenhuma conexão do pool retém tenant anterior; zero bypass/owner privilégio no runtime; todos os skips documentados e tratados como falha de cobertura quando escondem o caso-alvo.

## 11. Estratégia de implantação segura na Hostinger

Fase futura, condicionada à aprovação; nenhuma ação desta lista foi executada:

1. Atualizar o inventário somente com consultas `SELECT` ao catálogo na produção: 350 nomes, colunas/FKs, RLS/FORCE/policies, owner, grants, memberships e `alembic_version`. Não consultar payloads/dados de clientes para classificar schema.
2. Reconciliar as duas tabelas fora do contrato de 348 e a diferença entre o catálogo efetivo e migrations/baseline. Reclassificar as 301 sem RLS em tabela com justificativa, owner funcional, dados, consumidor e controle alternativo.
3. Auditar chamadas de `get_db`, `get_db_session`, SQL direto, jobs e commits intermediários por endpoint/job; converter/validar os fluxos tenant-scoped para estabelecer contexto antes do primeiro acesso protegido.
4. Aplicar a proposta de roles/grants em clone Hostinger representativo; rodar os testes da seção 10 e smoke de login, billing, onboarding, API, automations, background jobs e outbox com workers isolados.
5. Resolver a credencial versionada e estabelecer armazenamento seguro das URLs de runtime/deploy, sem valor em imagem, compose renderizado, logs ou saída de comandos.
6. Fazer backup recuperável e registrar revisão/owner/ACLs antes de qualquer DDL/grant. Preferir role operacional nova e canário por serviço, sem alterar a role administrativa existente e sem conceder privilégio excessivo por etapas longas.
7. Migrar primeiro workers individualmente, observando erros de policy, tarefas pendentes, conexões e telemetria; depois API canário e demais réplicas/processos. Não trocar todos os serviços simultaneamente.
8. Verificar imediatamente `current_user`, atributos da role, acesso A/B, filas/outbox e taxa de 403/permission errors. Só ampliar rollout após passar cada gate.
9. Aplicar policies/FORCE em lotes pequenos por domínio após validar ownership, consultas e backfills. Nenhuma tabela entra em RLS “por contagem”: tabela global fica explicitamente justificada; tabela tenant herdada recebe policy relacional ou proteção aprovada.
10. Encerrar com auditoria read-only de roles, owners, grants, 350 tabelas e 188 policies, confirmação de que runtime não é superuser/bypass/owner e repetição dos testes críticos.

Não requer novo PostgreSQL, Redis, serviço, cluster ou worker. O Compose existente pode continuar sendo o meio de entrega; o segredo é trocar credenciais de runtime por papel com privilégio mínimo e rollout por processo.

## 12. Procedimento de rollback

1. Interromper a expansão do canário e registrar imagem, role usada, revisão de migration e erro, sem copiar URL de banco para ticket/log.
2. Reverter primeiro a configuração/imagem do processo afetado para o último artefato aprovado. Manter o banco e dados intactos; evitar downgrade de migrations estruturais durante incidente.
3. Se um grant/policy aditivo causar indisponibilidade, usar scripts de rollback revisados e transacionais para restaurar grants/policies anteriores; não remover role enquanto houver sessões/owners dependentes.
4. Revalidar com a role operacional alvo e dois tenants antes de continuar. Se não for possível recuperar disponibilidade com papel mínimo, tratar retorno temporário à credencial privilegiada como **exceção de incidente**: aprovação explícita, janela curta, credencial protegida, monitoramento, novos cadastros/billing de assinantes suspensos e plano de retorno obrigatório. Esse fallback reabre o bypass RLS e não é condição aceitável para GO.
5. Fazer reconciliação posterior de grants, jobs, eventos outbox e operações tentadas na janela; preservar auditoria e revogar a credencial temporária.

O plano é viável porque propõe role paralela e grants/policies revisados antes de trocar os containers; não depende de alterar dados de negócio nem de descartar a arquitetura atual.

## 13. Riscos classificados

| ID | Criticidade | Risco | Evidência/impacto |
|---|---|---|---|
| R1 | **Crítica / bloqueadora** | Runtime usa superuser e BYPASSRLS | PostgreSQL ignora todas as policies para API e três workers, inclusive FORCE; uma query sem filtro pode atravessar tenants. |
| R2 | **Crítica** | Tabelas tenant-scoped sem RLS | 230 objetos no mapa estático sem RLS e `tenant_id` direto; fotografia de produção aponta 301 sem RLS, com duas tabelas não reconciliadas. Filtros ORM sozinhos não garantem isolamento. |
| R3 | **Alta** | Tabelas child sem `tenant_id` confundidas com globais | PII bancária, documentos e itens de compras dependem de FK. Sem RLS relacional, grants e consulta com pai correto são barreiras frágeis. |
| R4 | **Alta** | Nem todo caminho estabelece GUC | `get_db`/`get_db_session` não injetam tenant; workers/rotas manuais podem usar pool sem contexto. Com superuser, falta de GUC não bloqueia; depois da troca para NOBYPASS, endpoints não migrados falham fechados (indisponibilidade) ou, se RLS faltar, continuam sem barreira. |
| R5 | **Alta** | Jobs fazem varredura cross-tenant | Automação, recomendações, ERP, billing e outbox precisam processar muitos tenants. Uma role bypass resolve conveniência, não segurança; falha de filtro pode expor/alterar tenant errado. |
| R6 | **Alta** | Credencial PostgreSQL literal no código | `services/api/scripts/kill_idle_connections.py:8` contém uma URL de conexão. Valor e validade omitidos/não confirmados; se ativo, possibilita acesso fora do Compose. |
| R7 | **Alta** | Prova insuficiente em role operacional | E2E testam endpoints, fixtures podem criar schema e engolir erros; sem prova com NOBYPASS não certificam RLS físico. Sem reuso de pool A/B, não detectam contexto sessão residual. |
| R8 | **Média/Alta** | Divergência de inventário e razão da ausência de RLS | Contrato 348 versus produção 350; `RLS_NOT_REQUIRED` tem razão genérica e classifica qualquer tabela sem `tenant_id` como GLOBAL. Há risco de tabela sensível não catalogada. |
| R9 | **Média** | `propriedade_imovel` sem FORCE | Com superuser atual, não muda o bypass. Com futuro papel não owner, RLS aplica; com runtime owner, a ausência de FORCE permitiria bypass de owner. Motivo da diferença migration/snapshot ainda precisa ser conciliado. |
| R10 | **Média** | Contexto session-scoped em schedulers | Há `set_config(..., false)` com RESET/invalidate helpers; exceção sem cleanup e conexão reutilizada poderiam levar contexto entre jobs. |
| R11 | **Média** | Fallback silencioso de PostgreSQL para SQLite | Engine substitui backend se `DATABASE_URL` inválida/ausente ou driver indisponível; ambiente atual confirmado usa PostgreSQL, mas futura configuração errada pode iniciar processo sem contrato esperado. |

## 14. Veredicto e gates para liberar assinantes

**NO-GO** sob o estado de produção descrito. A principal barreira anunciada (RLS) está neutralizada pelo usuário de conexão da API e de todos os workers; além disso, há cobertura incompleta nas tabelas sem RLS e duas tabelas fora do contrato estático.

Para reavaliar como GO, exigir no mínimo:

1. API e workers usando role operacional `NOBYPASSRLS`, não superuser e não owner; papel administrativo separado e nunca carregado nos serviços persistentes.
2. Inventário das 350 tabelas reconciliado; as 301 sem RLS justificadas individualmente como globais/técnicas ou protegidas por RLS direto/relacional e grants mínimos.
3. Contexto tenant validado em todos os caminhos HTTP, SQLAlchemy, workers e tarefas cross-tenant; cleanup comprovado em commit, rollback, erro e reutilização de conexão.
4. Decisão documentada para `propriedade_imovel` e owners das tabelas.
5. Credencial versionada verificada e revogada/rotacionada se válida; segredos de produção protegidos e ausentes de imagens/logs.
6. Testes PostgreSQL reais da seção 10 passando com papel operacional equivalente ao de produção, sem skips nos casos críticos e com read/insert/update/delete entre dois tenants.
7. Rollback ensaiado em clone, sem usar role privilegiada como configuração final.

**Não houve alteração de código, banco, grants, policies, credenciais, containers ou infraestrutura. Este relatório é entregue para aprovação antes de qualquer implementação.**

## Referências principais do repositório

- `services/api/core/database.py:8-100` — engine, pool, `get_db` e `get_db_session`.
- `services/api/core/dependencies.py:62-175,410-494,688-700` — GUC, dependência, resolução e restauração após commit.
- `services/api/main.py:248-283` — extração do tenant pelo middleware.
- `docker-compose.prod.yml:1-75` — processos backend e referências de ambiente (valores não lidos).
- `services/api/core/background_jobs.py:121-138`; `services/api/automacoes/worker.py:13-126`; `services/api/events/outbox_worker.py:677-779` — processamento e varredura multi-tenant.
- `services/api/recommendations/scheduler.py:484-508`; `services/api/integracoes/erp/scheduler.py:245-263` — contexto session-scoped e cleanup.
- `services/api/migrations/baseline_contract.py:196-251` — inventário e contrato RLS/policies.
- `services/api/migrations/versions/add_propriedade_imovel.py:243-283` — RLS, FORCE e policies da tabela fundiária.
- `services/api/tests/e2e/test_tenant_isolation.py`; `test_caderno_tenant_isolation.py`; `test_reports_agricola_tenant_isolation.py`; `services/api/tests/integrity/test_tenant_fk_guardrails.py` — testes existentes e seus escopos.
