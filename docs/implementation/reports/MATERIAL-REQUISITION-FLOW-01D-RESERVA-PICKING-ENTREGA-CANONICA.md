# MATERIAL-REQUISITION-FLOW-01D — Reserva, Picking e Entrega Canônica

## 1. Resumo executivo

Foi implementada uma trilha backend canônica separada do workflow legado:

`reserva → separação por item/lote → entrega/handoff → evento ENTREGA + movimento SAIDA`.

A reserva não altera o saldo físico. A separação não altera o saldo físico. A
entrega canônica é o único ponto em que o saldo e, quando informado, o lote são
baixados. O recebimento pelo trabalhador, consumo, devolução e apropriação
econômica permanecem fora do 01D.

O 01D recebeu **GO COM RESSALVAS**: a migration real foi validada em
PostgreSQL com downgrade/upgrade, os testes unitários da fundação/caminho
canônico passaram e os guardrails contra mistura legado/canônico foram
implementados. A prova E2E transacional com dados temporários foi preparada,
mas não pôde concluir por indisponibilidade/intermitência de conexão do
PostgreSQL durante a execução final. Portanto, a autorização formal para 01E
fica pendente dessa execução em ambiente de integração estável.

## 2. Escopo

Incluído:

- reserva vinculada ao `ItemRequisicao`;
- reserva parcial e idempotência da reserva;
- picking por item, lote e depósito;
- entrega por item, lote e depósito;
- baixa física única por entrega;
- evento operacional append-only por fato;
- movimento físico ligado explicitamente ao evento;
- versionamento e locks pessimistas;
- entrega parcial e múltiplos lotes;
- cancelamento anterior à entrega e liberação da reserva;
- proteção contra chamar a saída legada após início canônico;
- bloqueio do FIFO operacional quando existe entrega canônica parcial;
- compatibilidade dos endpoints legados sem cutover global.

Fora do escopo: recebimento Campo, offline/Dexie, consumo, devolução,
perda/dano/extravio, conciliação final, CostAllocation, DRE e cutover legado.

## 3. Arquivos alterados

- `services/api/operacional/services/requisicao_canonica_service.py` — comandos transacionais 01D.
- `services/api/operacional/routers/estoque.py` — endpoints canônicos por item.
- `services/api/operacional/models/estoque.py` — quantidade consumida da reserva, chave idempotente e unicidade evento/movimento.
- `services/api/operacional/schemas/estoque.py` — contratos de reserva, separação e entrega canônicas.
- `services/api/operacional/services/estoque_service.py` — validação de aprovação, escopo tenant e bloqueio de mistura com evento canônico.
- `services/api/agricola/operacoes/service.py` — operação não cai no FIFO quando há entrega canônica parcial.
- `services/api/migrations/versions/20260925_material_requisition_01d.py` — migration incremental.
- `services/api/tests/unit/operacional/test_requisicao_canonica_01d.py` — guardrails unitários.

## 4. Modelo de reserva

`ReservaEstoque.quantidade` continua sendo a quantidade originalmente
reservada. `quantidade_consumida` representa a parcela já utilizada pela
entrega física. O restante é derivado:

`quantidade restante = quantidade - quantidade_consumida`.

Estados aceitos pela migration 01D:

`ATIVA`, `PARCIALMENTE_CONSUMIDA`, `CONSUMIDA`, `LIBERADA`, `CANCELADA`.

`ReservaEstoque.tenant_id + client_operation_id` é único quando a chave é
informada. A reserva canônica exige item aprovado, depósito tenant-safe e
saldo disponível.

## 5. Planejamento → reserva → requisição

O serviço de geração automática de requisição procura uma única
`PlanoOperacionalTarefa` correspondente à `SafraTarefa` da OS. Quando existe
um `PlanoOperacionalTarefaInsumo` com `reserva_estoque_id` ativo e produto
inequívoco, ele liga a reserva ao item recém-criado e copia o depósito. Não
cria uma segunda reserva. Se a correspondência não for inequívoca, nenhuma
associação é inventada e a requisição continua aguardando reserva explícita.

## 6. Fórmula de disponibilidade

Para criar reserva:

`disponível = saldo.quantidade_atual - saldo.quantidade_reservada`.

Para entregar um item que possui reserva própria:

`disponível para este item = saldo físico - reservas de outros itens`.

A própria reserva não é descontada contra o item que a está consumindo. Saldo
de lote, quando informado, é validado e bloqueado por linha.

## 7. Picking

Endpoint canônico:

`POST /estoque/requisicoes/{req_id}/itens/{item_id}/separar-canonico`

Cada comando cria um `RequisicaoItemEvento` `SEPARACAO` com quantidade, produto,
depósito, lote, usuário, versão, correlação e `client_operation_id`. Não cria
`EstoqueMovimento` e não altera `SaldoEstoque` ou `LoteEstoque`.

Separação parcial é preservada pela soma dos eventos. Separação por lotes não é
colapsada em um único lote.

## 8. Entrega

Endpoint canônico:

`POST /estoque/requisicoes/{req_id}/itens/{item_id}/entregar-canonico`

Uma entrega valida, sob lock:

1. tenant, requisição e item;
2. versão esperada;
3. status e aprovação;
4. reserva ativa do próprio item;
5. separação disponível no mesmo lote/depósito;
6. saldo físico e saldo do lote;
7. receituário obrigatório existente;
8. idempotência do comando.

Na mesma transação são gravados:

1. movimento `EstoqueMovimento(tipo_movimento='SAIDA', origem='REQUISICAO')`;
2. evento `RequisicaoItemEvento(tipo_evento='ENTREGA')`;
3. referência `EstoqueMovimento.requisicao_item_evento_id`;
4. atualização do saldo físico;
5. atualização do lote, quando usado;
6. consumo parcial ou total da reserva;
7. versão, status e Outbox.

O ledger atual normaliza o tipo físico para `SAIDA`; a semântica canônica é
identificada por `origem='REQUISICAO'` e pelo vínculo obrigatório ao evento.

## 9. Atomicidade

O serviço não chama `EstoqueService.registrar_saida()` para entrega canônica,
pois esse método é legado e não conhece a reserva própria nem o vínculo
evento↔movimento. O ledger é criado diretamente na mesma sessão transacional.

Falha em validação, insert, constraint, lock ou Outbox aborta a transação. Não
há commit intermediário entre evento, movimento, saldo e reserva.

## 10. Evento ↔ movimento

A migration cria `uq_estoque_movimentos_tenant_req_item_evento`. Assim, mesmo
que um bug de aplicação tente repetir a associação, o banco não permite dois
movimentos físicos para o mesmo evento de entrega.

O retry localiza o evento pelo par `tenant_id + client_operation_id` e devolve
o movimento já associado. Payload diferente com a mesma chave é rejeitado.

## 11. Versionamento

`RequisicaoMaterial.version` é o único agregado versionado. Separação, entrega,
reserva e cancelamento incrementam a versão sob lock. `base_version` divergente
gera `BusinessRuleError`; retry idempotente é resolvido antes da validação de
versão para não transformar repetição após commit em conflito falso.

## 12. Concorrência

O fluxo bloqueia a requisição/item, o saldo e o lote aplicável. A entrega
consome a reserva sob lock e verifica novamente quantidade separada, aprovada,
reservada e física. Portanto, dois comandos de 60 para a última disponibilidade
não podem ambos vencer; um deve ser rejeitado depois que o primeiro confirma.

A prova concorrente real foi preparada em script temporário com dois clientes e
limpeza controlada, mas não concluiu na última tentativa por timeout de conexão
do PostgreSQL de desenvolvimento. Isso permanece uma ressalva de validação,
não uma autorização para afirmar PASS de E2E.

## 13. Status

O status do cabeçalho é recalculado pelas quantidades dos eventos:

- `SEPARANDO`: há separação parcial ou ainda incompleta;
- `SEPARADA`: toda a aprovação está separada, mas ainda falta entrega;
- `ENTREGUE`: todos os itens aprovados foram entregues.

Uma entrega parcial não marca `ENTREGUE`. A quantidade entregue no item é
acumulada, e `lote_id` é mantido apenas quando não há ambiguidade entre lotes.

## 14. Cancelamento e liberação

`PATCH /estoque/requisicoes/{req_id}/cancelar-canonico` libera o restante das
reservas antes de qualquer entrega e marca a requisição como `CANCELADA`.
Depois de existir entrega física, cancelamento é rejeitado; retorno físico fica
para a fase 01F.

## 15. Consumível e retornável

Ambos usam o mesmo caminho de reserva, picking e entrega. O snapshot
`ItemRequisicao.natureza_item` não altera a saída física. A distinção só será
aplicada no consumo, devolução e dano da fase 01F.

## 16. Identidade operacional

O usuário autenticado que executa a saída é gravado em
`RequisicaoItemEvento.usuario_id`. O responsável operacional é o snapshot
`RequisicaoMaterial.responsavel_pessoa_id`. O 01D não inventa um vínculo novo
nem exige a identidade do recebedor, pois o aceite pelo responsável é 01E.

## 17. Outbox

Separação publica `operational.material_request.item_separated`; entrega publica
`operational.material_request.delivered`. A Outbox é inserida na transação,
mas não executa a baixa. A baixa já ocorre sincronamente antes do commit.

## 18. Proteção contra dupla baixa e legado

O endpoint canônico não compartilha a rota `/entregar` nem chama
`registrar_saida()`. Além disso:

- a rota legada recusa requisição que já tenha evento canônico;
- `registrar_saida()` recusa `origem_tipo='REQUISICAO'` quando já existe entrega canônica;
- operação agrícola com entrega canônica parcial é bloqueada antes do FIFO;
- operação com requisição totalmente entregue reutiliza o movimento existente,
  como já fazia o guardrail legado.

Assim, o caminho canônico não possui uma segunda baixa física para o mesmo
evento/item. O fluxo legado continua disponível para requisições sem evento
canônico, por compatibilidade e sem cutover global.

## 19. Tenant/RLS

Todas as consultas canônicas filtram `tenant_id`. As referências estruturais
usam FKs compostas já instaladas no 01C/01C1 para requisição/item/evento e a
reserva mantém FK composta para o item. Lote e depósito são validados por
contexto tenant antes de qualquer alteração. As tabelas de eventos e
responsabilidade permanecem com RLS FORCE da fundação.

O ledger mantém a FK composta para o evento e a nova unicidade também inclui
tenant. Não foi criado estoque virtual nem ledger paralelo.

## 20. Migration

Arquivo: `20260925_material_requisition_01d.py`.

Alterações:

- `estoque_reservas.quantidade_consumida`;
- `estoque_reservas.client_operation_id`;
- constraints de quantidade e estados da reserva;
- unique tenant+client operation da reserva;
- unique tenant+evento no movimento.

Validação realizada em PostgreSQL de desenvolvimento:

- upgrade `01C1 → 01D`: PASS;
- head final `20260925_material_requisition_01d`: PASS;
- downgrade `01D → 01C1`: PASS após correção do script de reversão;
- upgrade novamente `01C1 → 01D`: PASS;
- constraints e colunas inspecionadas no banco: PASS;
- RLS FORCE de eventos/responsabilidade: presente.

Não houve backfill de eventos, movimentos, consumo ou custos.

## 21. Compatibilidade legada

Endpoints legados não foram removidos. Requisições classificadas como
`LEGACY_*` não podem iniciar o fluxo canônico. O histórico não recebe picking
ou entrega inventados. A migration não recalcula saldo econômico nem cria
`CostAllocation`, `LancamentoFinanceiro` ou DRE.

## 22. Testes

Passaram:

- `test_requisicao_canonica_01d.py`: 5 testes;
- testes direcionados da fundação 01C e identidade 01C1: 12 testes;
- import da aplicação e registro do router canônico;
- `py_compile` dos serviços, router e migration;
- migration upgrade/downgrade/upgrade real;
- inspeção real de constraints e RLS.

Falhas preexistentes não atribuídas ao 01D:

- suíte ampla de compras com fixture sem `solicitante_id`;
- guardrail legado sobre `fix_imports.py`/`MovimentacaoEstoque`;
- violações gerais de tenant integrity já registradas no 01C1.

## 23. Cenário principal obrigatório

Contrato implementado para:

`100 kg aprovado/reservado → picking L1=60 + L2=40 → entrega L1=60 → entrega L2=40`.

Resultado esperado e garantido pelo código:

- após reserva: saldo físico inalterado, reserva 100;
- após picking: saldo físico inalterado, eventos de separação 60 e 40;
- após primeira entrega: saldo -60, reserva restante 40, dois fatos separados;
- após segunda entrega: saldo acumulado -100, reserva `CONSUMIDA`, dois movimentos;
- retry da segunda entrega: mesmo evento e mesmo movimento.

A execução final com dados temporários ficou pendente por indisponibilidade
intermitente do PostgreSQL; não foi classificada como PASS.

## 24. Cenário parcial obrigatório

`20 L aprovado/reservado → separado 18 → entregue 18` permanece como 18
separado/entregue, com 2 não atendidos. A requisição não é marcada como
`ENTREGUE`, a reserva restante não é liberada silenciosamente e nenhum consumo
é criado.

## 25. Retry obrigatório

O evento entrega é único por `tenant_id + client_operation_id`; o movimento
também é único por `tenant_id + requisicao_item_evento_id`. Retry idêntico
retorna os mesmos registros. Payload divergente é rejeitado.

## 26. Regressões

O fluxo legado continua compilável e os endpoints antigos permanecem. A única
mudança deliberada de comportamento é a recusa de misturar uma requisição que
já iniciou o diário canônico com a rota de entrega legada, necessária para
impedir uma segunda saída física.

## 27. Riscos

- A prova E2E concorrente precisa ser repetida em runner PostgreSQL estável.
- O fluxo legado ainda existe para requisições sem evento canônico; o cutover
  completo pertence a 01H.
- A operação parcial fica bloqueada até consumo/conciliação da fase 01F.
- Não há substituição automática de produto/lote.

## 28. Pendências

- executar e registrar a prova transacional real dos dois lotes, retry e
  concorrência em ambiente de integração estável;
- implementar recebimento autorizado no Campo/01E;
- implementar consumo, devolução e retornáveis/01F;
- concluir integração econômica/01G;
- executar cutover e E2E final/01H.

## 29. Prontidão para 01E

A API canônica está estruturalmente pronta para receber a camada de Campo,
mas a autorização de início formal da 01E fica **NÃO** até a execução
transacional real pendente ser concluída, porque o critério de aceite exige
prova de retry e concorrência em PostgreSQL.

## 30. Respostas obrigatórias

### A. Qual é exatamente o único ponto de baixa física?

O comando `entregar-canonico` cria `EstoqueMovimento` `SAIDA` com origem
`REQUISICAO`, dentro da mesma transação do evento `ENTREGA`.

### B. Separação altera saldo físico?

Não.

### C. Como a reserva do planejamento é vinculada sem duplicar?

O item do plano e sua `ReservaEstoque` ativa são localizados apenas quando a
correspondência é única; o `item_requisicao_id` é preenchido na mesma reserva.

### D. Como entrega parcial afeta a reserva?

`quantidade_consumida` aumenta apenas pela entrega, o status vira
`PARCIALMENTE_CONSUMIDA` e o saldo reservado diminui somente pela parcela
entregue. Na última parcela vira `CONSUMIDA`.

### E. Como múltiplos lotes são preservados?

Cada separação e entrega informa o lote e gera evento próprio; a entrega exige
quantidade previamente separada no mesmo lote.

### F. Como retry não gera segunda saída?

Chave idempotente do evento e unique evento↔movimento, com retorno do movimento
já existente.

### G. Como duas entregas concorrentes não geram saldo negativo?

Lock de requisição/item, saldo, lote e reserva; revalidação após lock e rejeição
da segunda quantidade sem reserva/saldo. A confirmação real ainda precisa ser
reexecutada no PostgreSQL estável.

### H. Como a entrega canônica evita a baixa legado adicional?

Rota separada, sem chamada a `registrar_saida`, bloqueio da rota legada após
evento canônico e bloqueio do FIFO para entrega parcial.

### I. Como requisição parcial evita status falso `ENTREGUE`?

O status é recalculado por soma dos eventos; só vira `ENTREGUE` quando todos os
itens aprovados foram entregues.

### J. Existe caminho restante capaz de realizar segunda baixa no fluxo canônico?

Para o mesmo evento/item canônico, não: a rota canônica é idempotente, o ledger
tem unique evento↔movimento e os caminhos legado/FIFO são bloqueados quando o
diário canônico já começou. O legado continua capaz de baixar requisições que
não iniciaram o fluxo canônico, por compatibilidade deliberada; isso não é uma
segunda baixa do mesmo item canônico.

## 31. Veredicto

`MATERIAL-REQUISITION-FLOW-01D`

`STATUS: GO COM RESSALVAS`

`ÚNICA BAIXA FÍSICA COMPROVADA: SIM — por implementação, constraints e locks; prova E2E concorrente real pendente`

`AUTORIZAÇÃO PARA 01E: NÃO`

`PRÓXIMA FASE: MATERIAL-REQUISITION-FLOW-01E — Campo Offline, Recebimento e Segurança, após concluir a prova PostgreSQL pendente`
