# ADR — Plataforma Balança independente

**Status:** Em implementação incremental  
**Data:** 2026-08-24  
**Escopo:** Plataforma Balança, estação offline e integração AgroSaaS

## Contexto

O módulo atual de Balança vive dentro de `services/api` e já possui ordens,
pesagens, estações, operadores, sincronização offline, aferição e eventos de
outbox. Entretanto, os clientes ainda importam services da Balança diretamente
e algumas projeções conhecem tabelas de Pecuária. Isso impede que a Balança
preste o mesmo serviço para outros sistemas.

## Decisão

A Balança será extraída gradualmente para uma plataforma independente, com:

- backend próprio e banco próprio;
- backoffice operacional próprio;
- estação local offline-first;
- Bridge de hardware local;
- operadores próprios da Balança;
- API pública versionada;
- Observer baseado em eventos e Outbox;
- adaptadores de entrega por API, webhook, rede e arquivo físico.

Durante a transição, o módulo atual continua operando no AgroSaaS por meio de
um adaptador de compatibilidade. Nenhum cliente poderá importar diretamente
o antigo módulo interno após a migração do primeiro contrato externo.

## Fronteiras de propriedade

### Plataforma Balança

É a fonte oficial de:

- equipamentos, aferições e estações;
- operadores da balança;
- ordens e etapas de pesagem;
- eventos físicos de pesagem;
- tickets, auditoria e reconciliação técnica;
- outbox e entrega dos eventos.

### AgroSaaS

É consumidor da Balança. Solicita pesagens, envia referências externas,
consome eventos e aplica o resultado em Compras, Agrícola, Financeiro ou
Pecuária. Não grava diretamente pesagens na base da Balança.

## Identidade e tenant

O tenant da Plataforma Balança e o tenant do sistema consumidor não são
assumidos como o mesmo UUID. A integração terá um vínculo explícito:

```text
balanca_account_id
cliente_integracao_id
sistema_origem
tenant_externo_id
```

Toda entidade da Plataforma Balança terá isolamento próprio por tenant e RLS.
Toda requisição externa terá credencial, escopo e contexto de conta explícitos.

## Contrato mínimo de ordem

Uma ordem externa deverá carregar, além do identificador interno da Balança:

- `client_system`;
- `client_tenant_id`;
- `external_reference`;
- `correlation_id`;
- `subject_type`;
- `tipo_pesagem`;
- `contexto` versionado;
- `callback_policy` ou assinatura de eventos.

`external_reference` será idempotente dentro do cliente e da conta Balança.

## Operador

O operador da Balança será um cadastro próprio, com identidade, PIN, status,
revogação e histórico. A associação a uma pessoa do cliente será opcional e
será mantida como vínculo de integração, não como dependência do cadastro
interno do consumidor.

```text
operador_balanca_id obrigatório
pessoa_cliente_id opcional
```

## Observer e entrega

Os eventos serão versionados e publicados pela Outbox:

- `balanca.ordem.criada.v1`;
- `balanca.pesagem.registrada.v1`;
- `balanca.pesagem.concluida.v1`;
- `balanca.pesagem.cancelada.v1`;
- `balanca.pesagem.reconciliada.v1`;
- `balanca.pesagem.ajuste_aplicado.v1`.

Cada consumidor terá estado de entrega, tentativas, erro, confirmação e
idempotência por `event_id` + `consumer_id`.

O mesmo envelope de evento será usado por API, webhook, rede local e arquivo.

Os transportes já previstos no núcleo são `ApiTransport`, `WebhookTransport` e
`FileTransport`. O arquivo é JSONL acompanhado de manifesto lateral com versão
do contrato, quantidade, último evento e SHA-256; a entrega mantém o mesmo
`idempotency_key` do envelope.

O worker pode ser executado por `services/api/scripts/run_balanca_outbox.py`.
Sua configuração usa `BALANCA_OUTBOX_*`, e há um modelo systemd no mesmo
diretório. Nenhum token de transporte deve ser gravado no repositório.

## Arquivo de contingência

O serviço define o contrato `balanca.contingency.v1` para contingência por
mídia física. Qualquer estação, PWA, Bridge ou aplicação cliente pode produzir
um pacote JSON assinado com ECDSA P-256. O pacote possui `package_id`, sequência
por estação, tenant, estação, chave pública, registros locais, assinatura e
hash canônico.

O endpoint `POST /v1/contingency/import`, protegido pelo RBAC do backoffice,
valida a assinatura, identidade da estação, tenant, sequência e idempotência.
O lote bruto e o resultado de cada item são preservados em
`contingencia_lotes` e `contingencia_itens`, sem executar SQL direto no banco
do cliente. Repetições retornam o lote já processado e não duplicam pesagens.

## Estratégia de migração

1. Publicar contratos e adaptador no AgroSaaS.
2. Migrar consumidores internos de imports diretos para o adaptador.
3. Extrair modelos, services e migrations para a Plataforma Balança.
4. Redirecionar o conector AgroSaaS para a API externa.
5. Executar período de compatibilidade e reconciliação dupla.
6. Remover o núcleo legado somente após os testes E2E e aceite operacional.

## Não objetivos

- duplicar entidades de Compras, Pecuária ou Agrícola na Balança;
- permitir gravação direta do cliente nas tabelas da Balança;
- transformar a estação em um segundo backend de negócio;
- usar o Service Worker como único mecanismo de disponibilidade;
- aceitar eventos sem tenant, conta ou correlação.

## Critérios de aceite arquitetural

- nenhum import direto de domínio cliente para o núcleo da Balança;
- todas as integrações passam por contrato versionado;
- operador pode existir sem Pessoa do cliente;
- evento pode ser entregue por API e arquivo com o mesmo envelope;
- reenvio não duplica ordem, pesagem ou consumo;
- RLS e isolamento são testados entre contas e tenants;
- estação pode ser instalada e atualizada offline sem perder a fila local.
