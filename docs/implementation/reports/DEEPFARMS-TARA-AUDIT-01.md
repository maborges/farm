# DEEPFARMS-TARA-AUDIT-01 — Auditoria da interface de integração

**Veredicto: NO-GO para considerar o fluxo completo de integração pronto para produção.** Há implementação relevante de criação de ordens, consulta e recepção assinada de eventos, mas a conciliação ponta a ponta não foi validada e há riscos na identidade do cliente, na recuperação de eventos e no tratamento de pesagens repetidas ou fora de ordem.

Esta conclusão refere-se ao código DeepFarms examinado. Não foram acessados dados de produção, a VPS ou o repositório TARA; não foram executados testes, migrações ou alterações de código, banco, configuração ou infraestrutura. A compatibilidade efetiva com a TARA, a configuração implantada e o comportamento em produção permanecem não verificáveis.

Estados utilizados: **IMPLEMENTADO E VALIDADO** significa validação executada nesta auditoria; **IMPLEMENTADO SEM VALIDAÇÃO**, código identificado sem prova ponta a ponta; **PARCIALMENTE IMPLEMENTADO**, fluxo com limitação identificada; **NÃO IMPLEMENTADO**, ausência identificada; **NÃO VERIFICÁVEL**, dependência de evidência não acessada. Nenhum item foi classificado como implementado e validado nesta auditoria.

## Inventário e fontes de verdade

| Componente | Responsabilidade e evidência | Estado |
|---|---|---|
| Rotas | Proxy autenticado para configuração, ordens, operadores, pesagens, eventos, webhook e estações: `services/api/integracoes/tara/router.py`; montagem em `services/api/main.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Cliente HTTP | Chamadas `/v1`, cabeçalhos, idempotência e retry: `services/api/integracoes/tara/client.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Configuração e credenciais | Configuração por tenant e segredo criptografado: `services/api/integracoes/tara/service.py` e `services/api/integracoes/models.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Contratos | Ordem, cliente, operador e página de pesagens: `services/api/integracoes/tara/schemas.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Webhook | Entrada, assinatura, deduplicação e enfileiramento: `services/api/integracoes/balanca/webhook_router.py` e `webhook.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Segredo do webhook | Resolução por tenant e conta e rotação: `services/api/integracoes/balanca/webhook_credentials.py`. | IMPLEMENTADO SEM VALIDAÇÃO |
| Consumidores | Colheita, compras, comercialização e pecuária utilizam eventos normalizados em `services/api/integracoes/balanca/events.py`; exemplos em `services/api/agricola/romaneios/event_subscriber.py` e `services/api/pecuaria/event_subscriber_balanca.py`. | PARCIALMENTE IMPLEMENTADO |
| Interface | Configuração, operadores, estações e pesagens: `apps/web/src/components/balanca/tara-console.tsx` e `tara-weighings-table.tsx`. | PARCIALMENTE IMPLEMENTADO |
| Migrações | `services/api/migrations/versions/20260828_balanca_inbound_events.py` e `20260828_balanca_webhook_credentials.py`. | IMPLEMENTADO SEM VALIDAÇÃO da aplicação no ambiente |

O DeepFarms armazena seus processos e resultados aplicados aos próprios modelos; a consulta de ordens e pesagens é encaminhada à TARA. O webhook persiste o envelope recebido e o enfileira. Nos fluxos examinados, a criação de ordem retorna ID e status, mas não foi identificada persistência local da solicitação ou do vínculo com a ordem. Evidências: `services/api/integracoes/tara/router.py`, `services/api/agricola/romaneios/service.py::solicitar_pesagem_balanca` e `services/api/integracoes/balanca/webhook.py::accept_event`.

## Arquitetura atual

```text
Usuário / processo DeepFarms
  → romaneio, compra, comercialização ou animal solicita pesagem
  → DeepFarms monta identidade e referência externa
  → POST TARA /v1/orders + Idempotency-Key
  → retorna ID e status ao chamador

TARA executa pesagem [execução e offline não verificáveis]
  → POST DeepFarms /api/v1/integracoes/balanca/events
  → valida conta, envelope, HMAC e timestamp
  → grava evento de entrada e enfileira evento de domínio
  → consumidores normalizam referência externa
  → atualizam processo correspondente

Consulta alternativa: DeepFarms → GET TARA /v1/weighings ou /v1/events
```

O diagrama representa o caminho pretendido pelo código, não uma execução observada. O estado do processamento de eventos na VPS é NÃO VERIFICÁVEL.

## Matriz de integração e contrato

| Funcionalidade | Origem → destino / endpoint | Estado e evidência |
|---|---|---|
| Configuração | DeepFarms: `GET/PUT /api/v1/integracoes/tara/config` | IMPLEMENTADO SEM VALIDAÇÃO; `integracoes/tara/router.py`. |
| Diagnóstico e registro | DeepFarms → `POST /v1/clients` | PARCIALMENTE IMPLEMENTADO: testar conexão registra ou recupera cliente e pode gravar seu ID; `integracoes/tara/service.py::diagnose_connection`. |
| Ordem | DeepFarms → `POST /v1/orders`, `GET /v1/orders/{id}` | IMPLEMENTADO SEM VALIDAÇÃO; `integracoes/tara/client.py`. |
| Pesagens e eventos | DeepFarms → `GET /v1/weighings`, `GET /v1/events`, com limite e cursor opaco | IMPLEMENTADO SEM VALIDAÇÃO; `integracoes/tara/client.py`. |
| Sincronização | `POST /api/v1/integracoes/tara/weighings/sync` → páginas TARA | PARCIALMENTE IMPLEMENTADO: retorna itens e salva cursor, sem aplicá-los aos processos no método examinado; `integracoes/tara/service.py::sync_weighings`. |
| Receber webhook | TARA → `POST /api/v1/integracoes/balanca/events` | IMPLEMENTADO SEM VALIDAÇÃO ponta a ponta; `integracoes/balanca/webhook_router.py`. |
| Administrar webhook e replay | DeepFarms → `GET/PUT /v1/webhooks`, `POST /v1/webhooks/replay` | IMPLEMENTADO SEM VALIDAÇÃO; payloads livres; `integracoes/tara/router.py`. |
| Operadores e estação | DeepFarms → `/v1/client/operators` e `/v1/stations/activate` | IMPLEMENTADO SEM VALIDAÇÃO da compatibilidade TARA; `integracoes/tara/client.py`. |

A ordem exige `client_system`, `client_tenant_id`, `external_reference`, `correlation_id`, tipo de sujeito e tipo de pesagem; há validação específica para `MULTIPLA`. O envelope aceita `balanca.pesagem.concluida.v1`, versão `v1`, identidade, referências e `payload` livre. Evidências: `services/api/integracoes/tara/schemas.py` e `services/api/integracoes/balanca/schemas.py`.

O cliente usa `X-Balanca-Client-ID` e `X-Balanca-Client-Secret`. Erros 401 e 403 recebem mensagens específicas; erros transitórios são repetidos até três tentativas para GET ou operações com chave de idempotência. Outras mutações não recebem retry automático. Evidência: `services/api/integracoes/tara/client.py::_request`.

## Frontend

- Configuração e diagnóstico: formulário de URL, cliente, segredo e identidade, com carregamento e resultado. IMPLEMENTADO SEM VALIDAÇÃO; `apps/web/src/components/balanca/tara-console.tsx`.
- Operadores e estações: sincronização e revogação de operadores e solicitação de ativação de estação. IMPLEMENTADO SEM VALIDAÇÃO; `tara-console.tsx`.
- Início de pesagem: ações para romaneio, compra, comercialização e animal. IMPLEMENTADO SEM VALIDAÇÃO ponta a ponta; exemplos em `apps/web/src/components/agricola/romaneios-colheita.tsx` e `apps/web/src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`.
- Consulta: tabela somente de leitura solicita até 100 itens; não utiliza `next_cursor` para buscar páginas seguintes. PARCIALMENTE IMPLEMENTADO; `apps/web/src/components/balanca/tara-weighings-table.tsx`.
- Acompanhamento e conciliação por solicitação: não foi identificada nas interfaces examinadas visão que associe persistentemente ordem, evento, processamento e divergência ao processo de origem. Cobertura integral da interface não verificada.

## Segurança

As rotas usam permissões de tenant; a configuração é buscada por tenant, o segredo da API é criptografado e a resposta informa apenas se está configurado. Evidências: `integracoes/tara/router.py` e `service.py`.

O webhook valida HMAC-SHA256 sobre método, caminho, timestamp e corpo bruto, verifica janela temporal e IDs nos cabeçalhos e resolve o segredo pelo par tenant/conta. Eventos são deduplicados por `event_id` e gravados com o evento de domínio na mesma transação. Evidências: `integracoes/balanca/webhook.py` e `webhook_credentials.py`.

A autorização real na TARA e as políticas RLS implantadas são NÃO VERIFICÁVEIS. O modelo armazena `idempotency_key`, mas a restrição apresentada é por `event_id`; eventos distintos que representem a mesma operação não são deduplicados por essa chave. Evidência: `services/api/integracoes/models.py::BalancaInboundEvent`.

## Inconsistências e riscos

1. **Alta — identidade pode divergir.** A configuração aceita texto arbitrário para `client_system` e `client_tenant_id`; o formulário sugere valores textuais. Os fluxos de negócio enviam `client_system="agrosaas"` e UUID do tenant, enquanto a ingestão exige UUID em `client_tenant_id`. Uma configuração diferente pode registrar uma identidade e criar ordens com outra, ou produzir retorno rejeitado. O efeito concreto depende da TARA. Evidências: `integracoes/tara/schemas.py`, `tara-console.tsx`, `agricola/romaneios/service.py::solicitar_pesagem_balanca`, `integracoes/balanca/webhook.py::_uuid_or_bad_request`.
2. **Alta — referência fixa por animal.** A ordem usa `pecuaria:animal:{animal_id}` e a chave deriva da referência, sistema e tenant. Solicitações sucessivas para o mesmo animal geram a mesma chave; o efeito depende da política TARA. Evidências: `pecuaria/routers/animais.py::solicitar_pesagem_balanca`, `integracoes/tara/client.py::order_idempotency_key`.
3. **Alta — recuperação não concilia automaticamente.** `sync_weighings` percorre páginas, salva cursor e retorna itens, mas não chama consumidores nem persiste cada resultado de negócio. Evidência: `integracoes/tara/service.py::sync_weighings`.
4. **Alta — eventos atrasados podem atualizar peso atual.** O consumidor de pecuária usa `date.today()` e não `occurred_at` para ordenar capturas. Uma entrega antiga processada depois pode ser tratada como atual. Evidência: `pecuaria/event_subscriber_balanca.py::PecuariaBalancaEventSubscriber.handle`.
5. **Média — `processed_at` não prova conciliação concluída.** É preenchido após enfileirar, antes da demonstração de sucesso dos consumidores. Evidência: `integracoes/balanca/webhook.py::accept_event`.
6. **Média — configuração de ambiente legada pode induzir erro.** Existem variáveis de segredo de webhook no exemplo e na configuração, mas a resolução usada exige credencial persistida e não usa fallback de ambiente. Evidências: `services/api/core/config.py`, `services/api/.env.example` e `integracoes/balanca/webhook_credentials.py::resolve_webhook_secret`.

## Lacunas e infraestrutura

- Offline e entrega tardia: execução offline e sincronização na TARA são NÃO VERIFICÁVEIS. No DeepFarms, não foi identificada garantia geral de ordenação por captura; a recuperação por consulta não demonstrou aplicação aos processos.
- Conciliação: vínculo local durável, estado de aplicação por solicitação e tratamento visível de divergências são PARCIALMENTE IMPLEMENTADOS ou não identificados no fluxo examinado.
- Dependências: URL e credenciais TARA por tenant, chave de criptografia de integrações, segredo HMAC por conta, janela de timestamp, conectividade HTTP, tabelas correspondentes e processamento dos eventos de domínio. Evidências: `integracoes/tara/service.py`, `integracoes/balanca/webhook_credentials.py`, `core/config.py`.
- Hostinger: existência, versão e estado dessas dependências na VPS são NÃO VERIFICÁVEIS sem inspeção autorizada do ambiente.

## Testes

Foram identificados testes de cliente, chave de idempotência, erros de credencial, operadores, contrato de ordem, normalização de evento e assinatura em `services/api/tests/unit/integracoes/test_tara_client.py`, `test_balanca_contracts.py` e `test_balanca_webhook_contract.py`. Também existe `services/api/tests/test_romaneio_receita_webhook.py`.

Resultado verificável nesta auditoria: os arquivos e casos existem; **não foram executados**. Permanecem sem validação demonstrada aqui: contrato contra TARA real, isolamento entre tenants em execução, múltiplas pesagens do mesmo animal, webhook perdido seguido de recuperação, eventos duplicados com IDs distintos, ordenação offline e fluxo completo até atualização de negócio.

## Plano mínimo de correção

1. Definir e validar uma única identidade por integração, preservando `client_system="agrosaas"` nos contratos existentes e garantindo correspondência entre registro, ordem e webhook.
2. Distinguir cada solicitação de pesagem, mantendo referência estável por solicitação e registrando vínculo entre processo, ordem e estado.
3. Completar recuperação e conciliação para aplicar eventos ou resultados recuperados com idempotência de negócio e estado observável.
4. Tratar captura tardia e fora de ordem usando data efetiva do evento e regras explícitas para atualização do peso atual.
5. Validar o fluxo ponta a ponta em ambiente isolado, incluindo assinatura, tenants, duplicidade, indisponibilidade, replay e paginação; conferir configuração e operação na VPS sob autorização apropriada.
6. Alinhar documentação e configuração de webhook ao mecanismo de credenciais efetivamente usado.

Nenhuma correção foi executada no âmbito da auditoria.
