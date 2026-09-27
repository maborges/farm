# MATERIAL-REQUISITION-FLOW-01A — Auditoria E2E

**Data da auditoria:** 2026-09-24  
**Escopo:** leitura de código, models, schemas, routers, services, migrations, telas e testes existentes.  
**Alterações realizadas:** nenhuma alteração em código, banco, migrations, Web, Campo, Dexie ou infraestrutura.  
**Veredicto:** **NO-GO**

## 1. Resumo executivo

O DeepFarms possui uma implementação parcial do fluxo de requisição de materiais:

- o planejamento agronômico consegue registrar necessidades, produto, dose, unidade e quantidade planejada;
- a aprovação do planejamento pode criar uma `ReservaEstoque`;
- a geração da OS (`OperacaoAgricola`) dispara uma requisição inicial de materiais;
- o Web permite aprovar, iniciar separação, confirmar retirada e registrar devolução;
- o Campo/PWA lista requisições por OS e permite conferência online usando PIN do dispositivo;
- a retirada/devolução gera movimentos de estoque e registra quem confirmou.

Entretanto, o fluxo não é ponta a ponta para o domínio solicitado. Os bloqueios principais são:

1. a conferência do Campo depende de `fetch` síncrono; não há entidade Dexie, fila de operação, retry, idempotência ou reconciliação offline para retirada/devolução;
2. `quantidade_entregue` é usada como baixa física na entrega/conferência, mas não existe `quantidade_consumida` ligada à requisição;
3. a operação agrícola possui um consumo separado, e o sistema tenta evitar uma segunda baixa somente quando encontra uma requisição `ENTREGUE`; isso não representa consumo real posterior nem o balanço recebido = consumido + devolvido + perda/ajuste;
4. ferramentas reutilizáveis não possuem entidade, ciclo de posse, dano, extravio ou devolução própria; só há itens de produto/estoque;
5. a requisição não possui FK direta para plano, tarefa, fase, safra, responsável da tarefa ou execução; parte da origem é `origem_id` genérica e a safra pode ser inferida por fallback;
6. o Campo consulta por `operacao_agricola_id`, mas a consulta não filtra a requisição pelo usuário responsável pela tarefa;
7. não há status de atendimento parcial/conferência/devolução/finalização. Uma entrega parcial pode terminar com status `ENTREGUE`;
8. o custo da saída da requisição passa por `LancamentoFinanceiro` legado, enquanto a arquitetura econômica oficial usa `OperacaoExecucao`/`CostAllocation`. A requisição não cria `CostAllocation` vinculada ao movimento ou à execução.

Conclusão: o sistema consegue demonstrar um fluxo online simplificado de solicitação → aprovação → retirada → devolução de sobra consumível, mas não consegue comprovar a operação completa pedida com offline, responsável, conferência auditável por item, consumo real, ferramentas reutilizáveis, estoque e custo real reconciliados.

## 2. Arquitetura encontrada

### 2.1 Planejamento e execução

| Conceito | Evidência | Papel real |
|---|---|---|
| Safra/tarefa | `services/api/agricola/tarefas/models.py:9-161` | `SafraTarefa` pertence à safra, unidade produtiva, talhão e fase; possui `operacao_id`, mas não responsável de estoque/requisição. |
| Necessidade técnica | `services/api/agricola/tarefas/models.py:104-161` | `SafraTarefaNecessidade` registra categoria, unidade, dose e quantidade técnica antes da escolha do produto comercial. |
| Plano operacional | `services/api/agricola/planejamento_operacional/models.py:9-95` | Agrupa tarefas da safra; não é a requisição de estoque. |
| Insumo planejado | `services/api/agricola/planejamento_operacional/models.py:98-163` | `PlanoOperacionalTarefaInsumo` registra produto, depósito, unidade, dose, `quantidade_planejada`, snapshots e eventual `reserva_estoque_id`. |
| OS/operação | `services/api/agricola/operacoes/models.py:8-67` | `OperacaoAgricola` liga tenant, safra, talhão, tarefa, operador e `production_unit_id`. |
| Insumo da operação | `services/api/agricola/operacoes/models.py:103-137` | `InsumoOperacao` guarda produto, dose, unidade, quantidade total e custo, sem quantidade consumida posterior. |
| Execução econômica | `services/api/agricola/operacoes/models.py:70-101` | `OperacaoExecucao` possui quantidade executada/devolvida genérica e `custo_real`, mas não é item de consumo da requisição. |

### 2.2 Estoque e requisição

| Conceito | Evidência | Papel real |
|---|---|---|
| Requisição | `services/api/operacional/models/estoque.py:104-134` | `RequisicaoMaterial`: tenant, unidade produtiva, solicitante, aprovador, status, origem genérica e FK opcional para `OperacaoAgricola`. |
| Item | `services/api/operacional/models/estoque.py:137-151` | Produto, depósito, lote, solicitado, aprovado, entregue e devolvido. Não há consumido, perdido, divergência ou ferramenta. |
| Confirmação | `services/api/operacional/models/estoque.py:154-169` | `RequisicaoConfirmacao`: tipo retirada/devolução, usuário, método, e-mail e data. Não guarda quantidades por item nem motivo de divergência. |
| Reserva | `services/api/operacional/models/estoque.py:171-189` | `ReservaEstoque` é entidade separada, com referência genérica tipo/ID; não possui FK para `RequisicaoMaterial`. |
| Ledger | `services/api/operacional/models/estoque.py:192-231` | `EstoqueMovimento` é append-only e possui origem/origem_id, lote, depósito, operação e unidade produtiva. |

## 3. Fluxo real atual

O fluxo observado é:

```text
SafraTarefa / PlanoOperacionalTarefa
  -> PlanoOperacionalTarefaInsumo
  -> reserva opcional de estoque
  -> gerar_operacao_planejada()
  -> OperacaoAgricola + InsumoOperacao + TarefaCampo
  -> criar_requisicao_a_partir_de_operacao()
  -> RequisicaoMaterial PENDENTE
  -> Web aprova
  -> Web marca SEPARANDO
  -> Web ou Campo confirma retirada
  -> registrar_saida(): baixa física e movimento SAIDA
  -> RequisicaoMaterial ENTREGUE
  -> Campo/Web registra devolução de sobra
  -> incremento de saldo e movimento DEVOLUCAO
```

Não foi encontrado um passo operacional de consumo posterior da requisição. A operação pode possuir uma baixa FIFO própria quando é marcada como realizada, embora haja uma exceção para reutilizar a baixa da requisição quando ela está `ENTREGUE`.

## 4. Fluxo esperado versus fluxo encontrado

| Passo esperado | Implementação observada | Avaliação |
|---|---|---|
| Planejamento define necessidade | Necessidade técnica e insumo planejado existem | Parcial |
| Necessidade vira requisição | Só ao gerar a OS; criação manual também existe | Parcial |
| Requisição rastreia origem completa | FK para operação; origem genérica para os demais contextos | Parcial |
| Responsável recebe | `solicitante_id` é preenchido com operador ou usuário criador | Parcial |
| Estoque aprova/reserva/separa | Aprovação e status de separação existem; reserva é fluxo separado | Parcial |
| Estoque entrega | Entrega baixa saldo imediatamente | Parcial, com semântica conflada |
| Campo disponibiliza | Lista online por OS | Parcial |
| Trabalhador confere | Quantidade por item e PIN existem online | Parcial |
| Offline | Sem cache/fila para requisição | Ausente |
| Consumo | Não existe consumo da requisição | Ausente |
| Devolução de sobra | Existe para produto consumível | Parcial |
| Ferramenta reutilizável | Não há modelo/ciclo | Ausente |
| Custo real | Há CostAllocation da operação, mas não da requisição/consumo real | Parcial |

## 5. Matriz E2E obrigatória

| Etapa | Backend | Web | Campo | Estoque | Offline | Testes | Status |
|---|---|---|---|---|---|---|---|
| Necessidade planejada | `SafraTarefaNecessidade`, `PlanoOperacionalTarefaInsumo` | Planejamento operacional | Tarefa planejada é sincronizada | Snapshot/reserva opcional | Tarefa pode ser cacheada | Testes de planejamento pontuais | IMPLEMENTADO PARCIALMENTE |
| Geração da requisição | `TarefaService._gerar_requisicao_material()` e `EstoqueService.criar_requisicao_a_partir_de_operacao()` | Nova requisição manual | Não gera localmente | Cria itens solicitados | Não | Não foi localizado teste dedicado | IMPLEMENTADO PARCIALMENTE |
| Aprovação | `PATCH /estoque/requisicoes/{id}/aprovar` | `AprovarDialog` | Não | Não reserva automaticamente | Não | Sem teste dedicado de requisição | IMPLEMENTADO PARCIALMENTE |
| Separação | `PATCH .../separar` apenas altera status | Botão “Iniciar Separação” | Não | Sem picking/itens separados | Não | Sem teste dedicado | MODELO SEM FLUXO |
| Entrega | `PATCH .../entregar` chama `registrar_saida` | Confirmar retirada Web | Não há entrega offline | Baixa física e ledger SAIDA | Não | Estoque genérico testado; requisição não | IMPLEMENTADO PARCIALMENTE |
| Conferência | `POST .../confirmar-retirada` registra confirmação | Dialog de credencial | Dialog por quantidade e PIN | Baixa ocorre nessa etapa | Sem fila/retry/conflict | Sem teste Campo de requisição | IMPLEMENTADO PARCIALMENTE |
| Consumo | Não há consumo ligado à requisição | Campo informa quantidade usada na tarefa, fora da requisição | Não há operação offline específica de consumo | Operação pode baixar FIFO própria | Caderno offline é outro fluxo | Sem teste de reconciliação | AUSENTE |
| Devolução de sobra | `POST .../confirmar-devolucao`, item devolvido e ledger DEVOLUCAO | Dialog de devolução | Online por PIN | Reentrada no saldo | Não | Não há teste dedicado de requisição | IMPLEMENTADO PARCIALMENTE |
| Devolução ferramenta | Não há modelo ou endpoint | Não | Não | Não | Não | Ausente | AUSENTE |
| Atualização estoque | `SaldoEstoque`, `EstoqueMovimento`, lotes | Visualização de estoque | Não | SAIDA/DEVOLUCAO reais | Não | Movimentos genéricos testados | IMPLEMENTADO PARCIALMENTE |
| Apropriação de custo | `OperacaoExecucao`/`CostAllocation` e legado `LancamentoFinanceiro` | Sem visão de custo real da requisição | Sem vínculo do retorno | Movimento de requisição não cria CostAllocation | Não | Testes econômicos de outros fluxos | IMPLEMENTADO PARCIALMENTE |

## 6. Evidências por camada

### 6.1 Backend

- `services/api/operacional/models/estoque.py:104-169`: models da requisição, itens e confirmações.
- `services/api/operacional/schemas/estoque.py:230-330`: contratos de criação, aprovação, entrega, conferência, devolução e resposta.
- `services/api/operacional/routers/estoque.py:351-471`: endpoints Web.
- `services/api/operacional/services/estoque_service.py:1471-1850`: criação, aprovação, entrega, retirada, devolução e alteração de status.
- `services/api/campo/router.py:534-617`: consulta por OS, retirada e devolução para device token/PIN.
- `services/api/agricola/tarefas/service.py:645-758`: geração de operação e vínculo com tarefa Campo.
- `services/api/agricola/tarefas/service.py:760-781`: geração best-effort da requisição.

Não foi encontrado evento de domínio/outbox específico para criação, aprovação, entrega, conferência, consumo ou devolução de requisição. As mudanças são feitas sincronicamente na mesma sessão transacional dos endpoints.

### 6.2 Web

- `apps/web/src/app/(dashboard)/suprimentos/requisicoes/page.tsx:54-239`: criação manual com fazenda, origem genérica, produto e quantidade.
- `apps/web/src/app/(dashboard)/suprimentos/requisicoes/page.tsx:253-350`: aprovação por item e depósito.
- `apps/web/src/app/(dashboard)/suprimentos/requisicoes/page.tsx:353-496`: confirmação online de retirada/devolução, com e-mail e senha.
- `apps/web/src/app/(dashboard)/suprimentos/requisicoes/page.tsx:500-677`: listagem e transições Web.
- `apps/web/src/app/(dashboard)/dashboard/operacional/requisicoes/page.tsx`: rota apenas delega à tela de suprimentos.

O Web não exibe nem edita tarefa, fase, safra, responsável da tarefa ou execução como campos estruturados da requisição. Quando `origem_tipo` é `ORDEM_SERVICO`, a tela seleciona uma tarefa, mas envia seu ID no campo genérico `origem_id`; a API de criação não transforma isso em FK de operação/tarefa.

### 6.3 Campo/PWA

- `apps/campo/src/app/(campo)/campo/tarefa/[id]/page.tsx:333-335`: a seção só aparece para tarefa com `operacaoAgricolaId` e status de execução `EM_EXECUCAO`.
- `apps/campo/src/lib/requisicoes-api.ts:60-107`: todos os três fluxos usam `fetch` direto: listar, confirmar retirada e confirmar devolução.
- `apps/campo/src/components/campo/requisicoes-section.tsx:104-159`: exibe status, produto e quantidade; ações dependem de `APROVADA`/`SEPARANDO`/`ENTREGUE`.
- `apps/campo/src/components/campo/requisicoes-section.tsx:185-283`: permite alterar quantidade por item e assinar com PIN.
- `apps/campo/src/lib/db.ts:376-410` e versões seguintes: Dexie possui tarefas, eventos, catálogos e `cached_images`, mas não possui tabela de requisições, itens de requisição ou operações de retirada/devolução.

O Campo mostra produto e unidade retornados pelo backend, mas não mostra lote de forma funcional, não mostra uma etapa separada de itens separados, não registra motivo/resultado da divergência e não oferece ferramenta reutilizável.

### 6.4 Migrations e banco

- `services/api/migrations/versions/20260726c_plano_operacional_tarefa_insumo.py:24-60`: tabela de insumos planejados, com quantidade e unidade.
- `services/api/migrations/versions/20260726d_plano_operacional_reserva.py:25-34`: FK de insumo planejado para `estoque_reservas`.
- `services/api/migrations/versions/20260803_requisicao_operacao_agricola.py:20-36`: FK opcional da requisição para `operacoes_agricolas`.
- `services/api/migrations/versions/20260803_estoque_mov_origem_requisicao.py:20-26`: permite `REQUISICAO` como origem do ledger.
- `services/api/migrations/versions/20260803_requisicao_confirmacoes.py:20-36`: cria confirmações e `quantidade_devolvida`.

Não foi encontrada migration para quantidade consumida, perda/ajuste da requisição, ferramentas, posse temporária, item separado, responsável da tarefa na requisição, conflito offline ou idempotência de comando Campo.

### 6.5 Testes

Foram encontrados testes gerais de estoque e valuation, por exemplo:

- `services/api/tests/integration/operacional/test_estoque.py` — entradas, saídas, transferências, ajustes, histórico, lotes e depósitos;
- `services/api/tests/unit/operacional/test_estoque_regras.py` — saldo insuficiente e FIFO em regras de estoque;
- `services/api/tests/unit/operacional/test_valuation_guardrails.py` — guardrails de saída/valuation;
- `services/api/tests/integration/operacional/test_ajuste_perda_gera_custo.py` — custo de perdas/ajustes;
- `services/api/tests/test_operational_workflow_governance_step06.py` — devolução de fornecedor, não devolução de requisição Campo.

Não foi localizado teste dedicado que percorra `planejamento → requisição → aprovação → separação → retirada Campo → consumo → devolução → custo`. Também não foi localizado teste de offline para retirada/devolução de requisição, de ferramenta ou de reconciliação de quantidades.

Não foram executados testes mutativos contra banco nesta auditoria, para preservar o caráter exclusivamente diagnóstico.

## 7. Integração Planejamento → Requisição

### 7.1 Como materiais são definidos

Há duas camadas de definição:

1. `SafraTarefaNecessidade` define a necessidade técnica: categoria, unidade de referência, unidade de medida, dose e quantidade técnica (`services/api/agricola/tarefas/models.py:104-161`);
2. `PlanoOperacionalTarefaInsumo` escolhe o produto comercial e registra unidade, dose, quantidade planejada, depósito, disponibilidade e custo (`services/api/agricola/planejamento_operacional/models.py:98-163`).

Assim, existe quantidade planejada, produto e unidade. Ferramentas não têm correspondente nesse modelo: `PlanoOperacionalTarefaMaquinario` trata máquina/implemento de custo, não uma retirada temporária por quantidade.

### 7.2 Evento que gera a requisição

O evento concreto é a chamada de `TarefaService.gerar_operacao_planejada()`:

- `services/api/agricola/tarefas/service.py:645-758` cria ou reaproveita `OperacaoAgricola`, `InsumoOperacao` e `TarefaCampo`;
- `services/api/agricola/tarefas/service.py:706-707` e `743-744` chamam `_gerar_requisicao_material()`;
- `services/api/agricola/tarefas/service.py:760-781` chama `EstoqueService.criar_requisicao_a_partir_de_operacao()`;
- `services/api/operacional/services/estoque_service.py:1499-1551` cria a requisição inicial a partir dos `InsumoOperacao`.

Essa geração é best-effort: se a unidade produtiva legada ou o solicitante não forem resolvidos, a OS continua sendo gerada sem requisição (`service.py:763-781`). Portanto, a requisição não é uma condição obrigatória para uma operação planejada chegar ao Campo.

Também existe criação manual via `POST /api/v1/estoque/requisicoes` (`routers/estoque.py:351-364`).

### 7.3 Duplicidade

Para a requisição inicial automática há uma checagem por tenant + `operacao_agricola_id` (`estoque_service.py:1511-1516`). Isso evita duplicar a geração inicial, mas o comentário permite requisições complementares e não há constraint única para a origem.

A criação manual não verifica se já existe requisição para a mesma tarefa/OS. A unicidade encontrada é somente tenant + número (`estoque.py:132-134`). Logo, duplicidade operacional permanece possível, sobretudo quando `origem_id` é usado manualmente.

## 8. Rastreabilidade da origem

| Informação | Como está representada | Resultado |
|---|---|---|
| Tenant | FK `RequisicaoMaterial.tenant_id` | Estruturado |
| Fazenda/UP | FK `unidade_produtiva_id` | Estruturado, porém modelo legado de UP |
| Safra | Não existe coluna na requisição; serviço resolve pela OS/tarefa ou safra ativa da UP | Inferido/fallback |
| Fase | Não existe coluna/FK | Ausente na requisição |
| Plano | Não existe coluna/FK | Ausente |
| Operação agrícola | FK opcional `operacao_agricola_id` | Estruturado somente para auto-geração |
| Tarefa | Não existe FK direta; pode aparecer em `origem_id` genérico | Convenção/campo livre |
| Responsável | `solicitante_id` | Criador/solicitante, não necessariamente responsável operacional |
| Origem | `origem_tipo` + `origem_id` | Tipo livre + UUID sem FK |
| Motivo | `observacoes` | Texto livre |

`_resolver_safra_contexto_requisicao()` (`estoque_service.py:908-953`) procura primeiro operação/tarefa e depois a safra não encerrada mais recente da UP. Essa resolução pode atribuir contexto econômico por fallback, não por vínculo inequívoco gravado na requisição.

Resposta à pergunta “por que este material está sendo retirado?”: para uma requisição auto-gerada, é possível chegar à OS pelo FK e ao produto pelo item; não é possível responder com a mesma força diretamente por plano, fase, tarefa responsável e execução. Para requisições manuais, a resposta pode depender de `origem_tipo`, `origem_id` e observação.

## 9. Responsável pela tarefa e vínculo usuário–aparelho

Existe vínculo do aparelho com usuário e tenant no fluxo Campo: `device.user_id` é recuperado por `_get_device_from_token()` e usado em `confirmar_retirada_requisicao_dispositivo()`/`confirmar_devolucao_requisicao_dispositivo()` (`services/api/campo/router.py:568-580` e `600-612`). O modelo de sessão local também guarda `user_id`, `tenant_id` e `device_id` (`apps/campo/src/lib/db.ts:73-82`).

Esse vínculo, contudo, não equivale ao vínculo de responsabilidade da requisição:

- a requisição guarda `solicitante_id`, não `responsavel_id` ou `recebedor_designado_id`;
- `solicitante_id` é preenchido pelo operador da OS ou pelo usuário criador (`estoque_service.py:1528-1530`), não por uma tabela de atribuição/delegação;
- não existe histórico de troca/delegação de responsável;
- o endpoint Campo lista por `operacao_agricola_id` e o service filtra somente tenant + operação (`campo/router.py:533-550`, `estoque_service.py:1553-1561`); não há filtro por `device.user_id`/responsável;
- o PIN confirma a identidade do usuário do aparelho, mas não prova que esse usuário esteja autorizado para aquela operação.

Risco: qualquer sessão de Campo válida que conheça o ID da operação pode, em princípio, consultar suas requisições no tenant e tentar confirmar com o PIN do aparelho, mesmo sem uma checagem explícita de atribuição à tarefa.

## 10. Integração Requisição → Estoque

### Estados reais encontrados

Os estados documentados no model e usados na UI são:

`PENDENTE`, `APROVADA`, `SEPARANDO`, `ENTREGUE`, `RECUSADA`, `CANCELADA`.

Não foram encontrados estados persistidos próprios para `PARCIAL`, `SEPARADA`, `RECEBIDA`, `DEVOLVIDA`, `CONSUMIDA`, `FINALIZADA`, `DIVERGENTE` ou `PERDA`.

### Aprovação

`aprovar_requisicao()` (`estoque_service.py:1582-1610`):

- aceita somente `PENDENTE`;
- grava aprovador e status `APROVADA`;
- atualiza quantidades aprovadas apenas para os itens enviados;
- não exige que todos os itens sejam informados;
- não valida quantidade aprovada contra quantidade solicitada;
- não cria reserva automaticamente.

### Reserva

O planejamento pode chamar `POST /{plano}/tarefas/{item}/insumos/{insumo}/reservar` (`planejamento_operacional/router.py:407-430`). A reserva atualiza `ReservaEstoque` e `SaldoEstoque.quantidade_reservada`, com vínculo no insumo planejado (`20260726d_plano_operacional_reserva.py:25-34`).

Não há vínculo equivalente entre a reserva e `RequisicaoMaterial`. Ao entregar, `registrar_saida()` calcula disponibilidade como saldo atual menos reservado (`estoque_service.py:974-985`), mas não consome/cancela/resolve a reserva da tarefa correspondente.

### Separação

`PATCH /requisicoes/{id}/separar` (`routers/estoque.py:397-408`) somente chama `atualizar_status_requisicao(..., "SEPARANDO")`. Não existe seleção de lote, item separado, quantidade separada, responsável pela separação, timestamp ou divergência de picking.

### Entrega e baixa

`entregar_requisicao()` (`estoque_service.py:1612-1657`) para cada item informado:

1. exige depósito;
2. chama `registrar_saida()` com origem `REQUISICAO`;
3. reduz `SaldoEstoque.quantidade_atual`;
4. registra `EstoqueMovimento` `SAIDA`;
5. grava `quantidade_entregue`;
6. ao final define a requisição como `ENTREGUE`.

Não valida `quantidade_entregue <= quantidade_aprovada` ou `<= quantidade_solicitada`. Se o payload omitir itens ou entregar somente parte, o status ainda é `ENTREGUE`. Isso torna possível representar uma quantidade parcial, mas com estado final semanticamente integral.

## 11. Integração Estoque → Campo e conferência

O Campo só busca materiais quando a tarefa programada já possui `operacaoAgricolaId` e está em execução (`apps/campo/src/app/(campo)/campo/tarefa/[id]/page.tsx:333-335`). Ele não recebe a requisição no pull offline geral.

A resposta apresenta produto, unidade, solicitado, aprovado, entregue e devolvido (`apps/campo/src/lib/requisicoes-api.ts:5-32`). Há ação explícita “Confirmar Retirada” para `APROVADA`/`SEPARANDO` e “Registrar Devolução” para `ENTREGUE` (`requisicoes-section.tsx:104-159`).

A conferência é por quantidade por item e PIN (`requisicoes-section.tsx:185-283`). O backend registra usuário e horário em `RequisicaoConfirmacao`, mas não registra:

- snapshot item a item da conferência;
- motivo da divergência;
- item recusado/não recebido;
- item substituído;
- avaria;
- assinatura do responsável da tarefa separada da assinatura do usuário do dispositivo;
- lote informado na conferência Campo, pois o fluxo dispositivo monta `ItemEntregaUpdate(..., lote_id=None)` (`estoque_service.py:1705-1714`).

O resultado é uma confirmação agregada por chamada, não um documento de recebimento detalhado.

## 12. Operação offline

### O que existe

Dexie possui `tasks`, `sync_queue`, eventos do caderno, rascunhos, catálogos e imagens (`apps/campo/src/lib/db.ts:376-410` e migrações posteriores). O caderno usa `enqueueSync`/`sync/push` para eventos offline.

### O que não existe para requisição

Não há tabela local para:

- `RequisicaoMaterial`;
- `ItemRequisicao`;
- conferência de retirada;
- devolução;
- comando idempotente de estoque;
- conflito ou versão da requisição.

`apps/campo/src/lib/requisicoes-api.ts:60-107` executa GET/POST diretamente. Se o usuário estiver offline:

1. a lista de requisições não é carregada do cache;
2. a conferência não é gravada localmente;
3. não há operação pendente para retry;
4. não há idempotency key ou `local_id` para impedir duplicidade após retry;
5. não há reconciliação de mudanças feitas pelo Web/estoque;
6. o retorno da conexão não dispara sincronização desse domínio.

Portanto, o cenário “material entregue offline → trabalhador confere → conexão retorna” não é suportado de ponta a ponta.

## 13. Consumo durante a tarefa

O domínio da requisição guarda quatro quantidades: solicitada, aprovada, entregue e devolvida (`estoque.py:145-149`). Não existe `quantidade_consumida`.

A operação possui outra baixa de estoque:

- ao criar operação `REALIZADA`, `OperacaoService` calcula `quantidade_total` por dose × área e consome FIFO (`operacoes/service.py:1090-1154`);
- ao atualizar para realizada, `_aplicar_insumos_na_operacao()` também pode consumir FIFO (`operacoes/service.py:514-615`);
- quando encontra uma requisição `ENTREGUE`, reutiliza a quantidade entregue e o custo do movimento da requisição, evitando uma segunda baixa (`operacoes/service.py:475-561`).

Essa exceção evita parte da dupla baixa, mas altera a semântica: o custo/quantidade da `InsumoOperacao` passa a ser o que foi entregue, não o que foi efetivamente consumido na execução. Não há campo para registrar, por exemplo, 92 kg consumidos de 100 kg recebidos.

Também não há referência da requisição na `OperacaoExecucao` ou da execução no item de requisição. O movimento de saída da requisição possui `origem=REQUISICAO`, enquanto o consumo próprio da operação possui `origem=OPERACAO_EXECUCAO`.

## 14. Devolução de materiais

Há suporte parcial a sobra de consumíveis:

- `ItemRequisicao.quantidade_devolvida` e `RequisicaoConfirmacao(tipo=DEVOLUCAO)` foram introduzidos em `20260803_requisicao_confirmacoes.py:20-36`;
- `_confirmar_devolucao_interno()` exige status `ENTREGUE` e impede devolver acima do entregue (`estoque_service.py:1748-1779`);
- incrementa saldo e grava ledger `DEVOLUCAO` (`estoque_service.py:1801-1823`);
- a UI mostra saldo entregue menos devolvido (`requisicoes-section.tsx:104-115`).

Gaps:

- não existe quantidade consumida, perdida ou ajustada;
- não existe equação persistida `recebido = consumido + devolvido + perda/ajuste`;
- não existe motivo da devolução;
- não existe usuário/data por linha de item, apenas confirmação agregada;
- o depósito é o depósito do item, sem escolha de destino na devolução;
- não há fechamento/status `DEVOLVIDA` ou `CONCILIADA`;
- a busca da saída original filtra requisição/produto/tipo, mas não lote e escolhe a primeira saída (`estoque_service.py:1784-1795`), o que é frágil com múltiplos lotes ou múltiplas entregas;
- o movimento de devolução usa o lote do item, mas a retirada Campo não preenche lote (`estoque_service.py:1710-1714`).

## 15. Devolução de ferramentas

O cenário de ferramentas reutilizáveis não está implementado como domínio:

- `ItemRequisicao` referencia apenas `produto_id` de catálogo;
- não há `ferramenta_id`, ativo, patrimônio, quantidade em posse, estado ou responsável;
- não há evento `ENTREGA → POSSE_TEMPORARIA → DEVOLUÇÃO`;
- não há quantidade pendente de devolução de ferramenta;
- não há motivo/categoria para dano, perda ou extravio;
- não há devolução parcial específica;
- não há tratamento de custo patrimonial ou manutenção.

É possível cadastrar uma tesoura como produto e devolvê-la numericamente como se fosse consumível, mas isso não registra posse temporária, dano ou a diferença entre cinco entregues, quatro devolvidas e uma danificada. Isso não satisfaz a decisão arquitetural de controlar ferramentas de baixo valor por quantidade com rastreabilidade de posse.

## 16. Impacto no estoque

| Evento | Reserva | Saída física | Entrada física | Impacta saldo | Comportamento real |
|---|---:|---:|---:|---:|---|
| Solicitação | Não | Não | Não | Não | Cria requisição e itens; nenhum movimento. |
| Aprovação | Não automaticamente | Não | Não | Não | Grava aprovado e status; reserva existe em fluxo separado do plano. |
| Separação | Não | Não | Não | Não | Só muda para `SEPARANDO`. |
| Entrega Web | Não | Sim | Não | Sim | `PATCH /entregar` chama `registrar_saida`. |
| Recebimento/conferência Campo | Não | Sim | Não | Sim | Conferência chama internamente `entregar_requisicao`; não é mero aceite. |
| Consumo | Não na requisição | Sim, mas por operação | Não | Sim | `OperacaoService` pode consumir FIFO por `OPERACAO_EXECUCAO`; não é consumo da requisição. |
| Devolução | Não | Não | Sim | Sim | Gera `DEVOLUCAO` e incrementa saldo; sem consumo/perda conciliados. |

Riscos comprovados no código:

- **dupla baixa:** mitigada apenas quando a operação encontra uma requisição `ENTREGUE`; se a requisição não existir, não estiver entregue ou não cobrir o produto, a operação baixa FIFO própria;
- **saldo negativo:** `registrar_saida` bloqueia saldo disponível insuficiente, mas não bloqueia quantidade de entrega acima do aprovado/solicitado;
- **devolução duplicada:** há limite cumulativo por item, mas não há idempotency key; duas requisições HTTP concorrentes não têm proteção explícita por lock/unique de comando;
- **consumo superior ao recebido:** não existe regra de consumo contra recebido; o consumo da operação pode seguir a dose planejada/FIFO;
- **requisição duplicada:** criação manual não possui deduplicação de origem;
- **movimentação sem origem forte:** ledger exige origem textual e `origem_id` pode ser requisição, operação ou outro UUID, sem FK polimórfica que garanta o alvo;
- **devolução no lote errado:** a saída original não é selecionada por lote e a conferência Campo não envia lote.

## 17. Integração econômica

### 17.1 Caminho canônico

O caminho consolidado é:

```text
OperacaoAgricola
  -> OperacaoExecucao
  -> CostAllocation(source=OPERATION_EXECUTION)
  -> DRE/Dashboard
```

Evidências:

- `services/api/agricola/custos/models.py:11-41`: `CostAllocation` pode referenciar `operation_execution_id` ou `inventory_movement_id`;
- `services/api/agricola/operacoes/service.py:738-884`: operação realizada cria/atualiza `OperacaoExecucao` e `CostAllocation` com custo total da operação;
- `services/api/agricola/dre/service.py:585-620`: DRE lê `CostAllocation`.

### 17.2 Caminho da requisição

Na saída da requisição, `registrar_saida()`:

- cria `EstoqueMovimento` `SAIDA` com origem `REQUISICAO` (`estoque_service.py:955-1015`);
- resolve uma safra por OS/tarefa ou fallback da UP (`estoque_service.py:908-953`);
- chama `_criar_lancamento_insumo()` quando há safra e custo (`estoque_service.py:1007-1014`).

Esse lançamento é o caminho legado `LancamentoFinanceiro`, enquanto o comentário do próprio service indica que o fluxo novo deveria usar `CostAllocation`. A saída de requisição não chama `registrar_cost_allocation()` com `inventory_movement_id`, nem preenche `operacao_execucao_id`.

### 17.3 Qual quantidade representa o custo atual

Não existe uma única quantidade real do fluxo:

- no lançamento da requisição: quantidade entregue/conferida;
- no `InsumoOperacao` quando há requisição entregue: quantidade entregue;
- sem requisição entregue: quantidade planejada calculada por dose × área e consumida FIFO;
- no `OperacaoExecucao`: quantidade executada é a área/quantidade genérica da operação, não o consumo de cada material.

Portanto, o custo atual não representa de forma confiável a quantidade consumida real do exemplo solicitado. Há risco de divergência e de dupla representação entre lançamento legado de saída, custo da operação e CostAllocation.

## 18. Teste conceitual obrigatório

### Cenário

| Item | Planejado/solicitado | Recebido | Consumido | Devolvido | Resultado esperado |
|---|---:|---:|---:|---:|---|
| Produto A | 100 kg | 100 kg | 92 kg | 8 kg | Conciliado |
| Produto B | 20 L | 18 L | 17 L | 1 L | Divergência de entrega + conciliado |
| Ferramentas | 3 | 3 | N/A | 2 | 1 danificada/presente como pendência |

### Resultado no sistema atual

| Ponto | Consegue? | GAP |
|---|---|---|
| Planejar A=100 kg e B=20 L | Sim, se produtos/unidades forem configurados | Não há garantia de que a requisição herde todos os dados do plano; depende da OS. |
| Gerar requisição | Sim, ao gerar OS com `InsumoOperacao` | Geração é best-effort e não ocorre diretamente no plano. |
| Registrar 3 ferramentas | Não como ferramentas | Só seria possível tratar como três produtos, sem posse/dano. |
| Aprovar 100 kg A e 20 L B | Sim | Quantidade aprovada não é validada contra solicitada. |
| Separar 100 kg A e 18 L B | Parcialmente | Não há item/quantidade separada; status não é parcial. |
| Entregar ao Campo | Sim, online | A baixa física ocorre antes/de modo indistinto do consumo. |
| Conferir A=100 e B=18 | Sim, online por quantidade | Campo não funciona offline; lote e motivo não são registrados. |
| Registrar divergência B | Parcialmente | O número 18 é aceito, mas não há estado/motivo/histórico de divergência formal. |
| Registrar consumo A=92 e B=17 | Não pela requisição | Não há quantidade consumida nem comando de consumo ligado à requisição. |
| Devolver A=8 e B=1 | Sim, como sobra de produto | Funciona como entrada, mas sem conciliação com consumo e com risco de lote original incorreto. |
| Devolver duas ferramentas | Não como ferramenta | Não há entidade nem ciclo de posse. |
| Registrar uma ferramenta danificada | Não | Sem motivo/categoria/status de dano. |
| Atualizar estoque corretamente | Parcialmente | SAIDA na entrega e DEVOLUCAO na sobra existem; consumo/ferramenta não. |
| Apropriar custo real | Não de forma completa | Requisição usa caminho legado; CostAllocation é da operação e pode usar quantidade entregue/planejada. |

**Conclusão do teste conceitual:** o DeepFarms não consegue registrar corretamente todo o cenário.

## 19. GAPs classificados

### BLOCKING

- **GAP-B01 — Offline inexistente para retirada/devolução:** o Campo usa `fetch` direto e não possui cache/fila/idempotência/retry/conflito para requisição.
- **GAP-B02 — Sem consumo real vinculado:** não existe `quantidade_consumida` por item nem comando de consumo da requisição; recebido e consumido não são conceitos persistidos separadamente.
- **GAP-B03 — Ferramentas fora do fluxo:** não há suporte para entrega, posse temporária, devolução, dano, perda, extravio ou pendência.
- **GAP-B04 — Apropriação econômica não fecha com o consumo real:** saída da requisição usa lançamento legado; `CostAllocation` da operação usa uma quantidade/custo que não é o consumo real da requisição.
- **GAP-B05 — Autorização por responsável não demonstrada:** o aparelho está vinculado a usuário/tenant, mas a listagem Campo não verifica responsabilidade do usuário pela tarefa/requisição.

### HIGH

- **GAP-H01 — Entrega parcial com status integral:** qualquer entrega informada finaliza como `ENTREGUE`; não há `PARCIAL`/`SEPARADA`/`RECEBIDA`.
- **GAP-H02 — Sem validação de limite aprovado/solicitado:** entrega pode exceder o aprovado ou solicitado, limitada apenas pelo saldo físico.
- **GAP-H03 — Origem incompleta:** não há FK para plano, tarefa, fase, safra ou execução; `origem_id` é genérico e safra pode ser fallback.
- **GAP-H04 — Reserva não integrada à requisição:** reserva do planejamento não é consumida, reconciliada ou ligada ao item entregue.
- **GAP-H05 — Risco de dupla baixa/divergência:** entrega baixa o estoque e operação pode baixar FIFO, com mitigação dependente de encontrar requisição `ENTREGUE`.
- **GAP-H06 — Devolução não é rastreada por lote/movimento exato:** busca a primeira SAIDA por requisição/produto e a conferência Campo não informa lote.
- **GAP-H07 — Geração automática best-effort:** ausência de UP legada ou solicitante permite OS sem requisição.

### MEDIUM

- **GAP-M01 — Conferência sem evento item a item:** confirmação guarda usuário/data, mas não o snapshot das quantidades e divergências.
- **GAP-M02 — Sem estado final de conciliação:** requisição permanece `ENTREGUE` depois de devoluções; não há encerramento.
- **GAP-M03 — Separação é apenas status:** não há picking, item separado, lote separado ou responsável.
- **GAP-M04 — Sem perda/ajuste ligado à requisição:** a equação de conservação não é persistida.
- **GAP-M05 — Sem histórico de delegação/troca:** solicitante não é histórico de responsável operacional.
- **GAP-M06 — Sem testes E2E do domínio:** os testes existentes cobrem estoque/custos genéricos, não o fluxo completo.

### LOW

- **GAP-L01 — Unidade é enriquecida do catálogo, não snapshot do item:** alteração de cadastro pode mudar a apresentação histórica.
- **GAP-L02 — Status livres:** `atualizar_status_requisicao()` aceita novo status sem máquina de estados completa (`estoque_service.py:1839-1849`).
- **GAP-L03 — Complementos não possuem política de consolidação:** a própria documentação permite mais de uma requisição por OS, mas não há visão consolidada de saldo total.

### OBSERVAÇÃO

- **OBS-01:** o vínculo device → usuário → tenant existe e permite auditar o usuário que confirmou, mas não substitui uma regra de responsabilidade/atribuição operacional.
- **OBS-02:** `ReservaEstoque` já possui estrutura suficiente para ser reutilizada, mas sua relação atual é com o insumo planejado e não com a requisição.
- **OBS-03:** o ledger append-only e os movimentos `REQUISICAO`/`DEVOLUCAO` são bases úteis para uma futura implementação, mas não comprovam o fluxo E2E por si só.
- **OBS-04:** imagens/avatar/fazenda são infraestrutura de cache separada do domínio de requisição; não foram consideradas evidência de material recebido.

## 20. Riscos

1. **Risco operacional:** trabalhador sem conectividade não consegue consultar ou confirmar material entregue.
2. **Risco de estoque:** entrega e consumo podem ser confundidos; uma mesma necessidade pode produzir saídas em origens diferentes.
3. **Risco de auditoria:** não é possível provar por item quem recebeu qual lote, em qual quantidade e qual divergência foi aceita.
4. **Risco de segurança:** usuário autenticado no dispositivo não é necessariamente o responsável pela OS consultada.
5. **Risco econômico:** o DRE pode refletir custo de entrega/planejamento, enquanto a operação real utilizou quantidade diferente.
6. **Risco de ativo:** ferramentas podem desaparecer no fluxo porque não há posse, pendência, dano ou extravio.
7. **Risco de duplicidade:** requisições manuais para a mesma origem não possuem proteção estrutural.
8. **Risco de integridade:** devoluções em múltiplos lotes podem ser atribuídas ao primeiro movimento, e não ao lote efetivamente retornado.

## 21. Recomendações para eventual fase 01B

Esta seção é recomendação diagnóstica; nenhuma recomendação foi implementada nesta auditoria.

1. Definir contrato canônico da requisição com FKs para a origem operacional necessária: tenant, UP, safra, fase, plano, tarefa, operação, execução e responsável.
2. Separar formalmente os estados de solicitação, aprovação, reserva, separação, entrega, recebimento, divergência, consumo, devolução e encerramento.
3. Persistir por item as quantidades solicitada, aprovada, separada, entregue, recebida, consumida, devolvida, perdida/ajustada e pendente.
4. Integrar reserva, requisição, movimento de estoque e consumo com chaves idempotentes e movimentos reversíveis/append-only.
5. Escolher uma semântica única para baixa: entrega ao trabalhador, consumo na operação e devolução de sobra devem ser eventos distintos.
6. Criar domínio de ferramenta por quantidade/ativo, incluindo posse, devolução parcial, dano, extravio e pendência.
7. Implementar no Campo cache Dexie, fila de comandos, idempotency key, retry, conflito e reconciliação por tenant/UP/usuário.
8. Fazer o backend validar a responsabilidade do usuário pela tarefa/OS, além de validar tenant e token do dispositivo.
9. Ligar o custo do consumo real ao caminho oficial `OperacaoExecucao → CostAllocation`, evitando contabilização paralela legada.
10. Criar testes E2E para o cenário 100 kg/20 L/3 ferramentas, incluindo online, offline, retry duplicado, divergência, lotes e tenant isolation.

## 22. Veredicto final

**NO-GO** para afirmar que o fluxo completo de requisição originada de tarefa planejada está implementado ponta a ponta.

O sistema está apto apenas para uma validação limitada do fluxo online de materiais consumíveis:

```text
OS gerada -> requisição -> aprovação -> separação nominal -> retirada online -> devolução nominal de sobra
```

Essa validação não deve ser confundida com o fluxo completo esperado, porque faltam offline, consumo real, ferramentas, rastreabilidade completa, autorização por responsável e apropriação econômica reconciliada.

### Resposta explícita

> O DeepFarms atualmente consegue executar ponta a ponta uma requisição originada de uma tarefa planejada, entregar os materiais ao responsável, permitir sua conferência no Campo, registrar consumo e devolução de sobras/ferramentas, atualizar corretamente o estoque e apropriar o custo real à operação?

**Não.** O DeepFarms consegue gerar e atender parcialmente requisições de materiais consumíveis online, com conferência por quantidade e devolução de sobra. Não consegue, no estado atual comprovado pelo código, completar todo o cenário com conferência offline, consumo real separado do recebido, devolução de ferramentas/dano, vínculo inequívoco ao responsável e apropriação econômica do consumo real sem os gaps classificados acima.
