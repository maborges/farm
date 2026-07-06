# Domain Events Operational Checklist

## Adicionar Um Novo Evento

1. Defina um `event_type` existente na fundação oficial.
2. Construa um `DomainEvent` com `tenant_id`, `unidade_produtiva_id`, `domain`, `event_type`,
   `source_type`, `entity_type`, `entity_id`, `correlation_id`, `causation_id` e `metadata`.
3. Publique somente após o `commit` principal.
4. Use `publish_domain_event_safe(...)` para isolar falhas.
5. Escreva testes para o caminho feliz e para falha de publicação.

## Registrar Um Novo Subscriber

1. Implemente `EventSubscriber`.
2. Preencha `subscriber_name` e `event_types`.
3. Registre o subscriber no registry oficial.
4. Garanta que o subscriber não carregue payloads grandes em logs ou metadata.
5. Cubra o contrato com teste unitário.

## Conectar Um Evento Ao Alert Engine

1. Registre o `event_type` no `AlertEngineEventSubscriber`.
2. Confirme que o subscriber converte o `DomainEvent` em `AlertDomainEvent`.
3. Confirme que o dispatcher resolve generators corretamente.
4. Verifique idempotência do alerta gerado.

## Validar Que O Serviço Não Ficou Acoplado Ao Dispatcher

1. Faça uma leitura estática do arquivo do Domain Service.
2. Verifique que não existem imports ou chamadas para `AlertDispatcherService`.
3. Verifique que o serviço conhece apenas `DomainEvent` e `publish_domain_event_safe(...)`
   ou helper equivalente.

## Testar Idempotência

1. Publique o mesmo evento duas vezes.
2. Confirme que o subscriber alerta apenas consolida estado e não duplica alertas ativos.
3. Confirme que o dispatcher e os generators preservam o comportamento esperado.

## Testar Falha De Subscriber

1. Force uma exceção no subscriber.
2. Confirme que o publisher isola a falha.
3. Confirme que a publicação segura registra log estruturado e não interrompe o fluxo principal.

## Preparar Evento Para Futura Outbox

1. Mantenha o evento oficial enxuto.
2. Evite snapshots completos e payloads grandes.
3. Mantenha a publicação separada da mutação principal.
4. Não introduza dependência direta do Alert Engine no Domain Service.
