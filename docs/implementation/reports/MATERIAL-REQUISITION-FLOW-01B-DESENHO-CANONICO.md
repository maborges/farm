# MATERIAL-REQUISITION-FLOW-01B — Desenho Canônico do Fluxo de Requisição

**Data:** 2026-09-24
**Escopo:** desenho arquitetural somente leitura.
**Entrada obrigatória:** `docs/implementation/reports/MATERIAL-REQUISITION-FLOW-01A-AUDITORIA-E2E.md`
**Alterações realizadas:** somente este relatório; nenhuma alteração em código, banco, migrations, Web, Campo, Dexie, estoque, CostAllocation ou infraestrutura.

## 1. Resumo executivo

O contrato canônico proposto separa formalmente quatro fatos que hoje estão misturados:

```text
separar       = preparar fisicamente o item;
entregar      = transferir o item para fora do depósito;
receber       = o responsável confirmar o que efetivamente ficou sob sua responsabilidade;
consumir      = apropriar a quantidade utilizada na execução.
```

A saída física ocorrerá no evento de entrega, com `EstoqueMovimento` append-only. O recebimento não fará uma segunda baixa. O consumo será um evento operacional posterior, vinculado a `OperacaoExecucao`, e alimentará a reconciliação econômica oficial `OperacaoAgricola → OperacaoExecucao → CostAllocation`.

O desenho não cria depósito virtual nem um segundo estoque. A quantidade em posse será derivada dos eventos do item da requisição. Para tornar isso auditável são necessários:

1. um diário imutável de eventos por item da requisição, separado do ledger físico;
2. vínculo estruturado entre reserva, item da requisição e origem operacional;
3. autorização/histórico de responsável, delegado e recebedor;
4. comandos Campo offline com `client_operation_id`, versão e ACK idempotente;
5. reconciliação explícita antes do encerramento da requisição/operação.

O desenho é suficiente para iniciar implementação incremental, mas há decisões de política que precisam ser aprovadas antes das migrations: tratamento econômico de dano/extravio, bloqueio ou exceção no encerramento de tarefa não conciliada, regra para terceiro recebedor e mapeamento definitivo entre usuário autenticado e pessoa operacional.

## 2. Diagnóstico herdado do 01A

O 01A recebeu veredicto **NO-GO**. O estado encontrado foi:

- o planejamento possui produto, unidade e quantidade planejada em `PlanoOperacionalTarefaInsumo`;
- a aprovação do planejamento pode criar `ReservaEstoque`;
- a geração de OS cria `OperacaoAgricola`, `InsumoOperacao`, `TarefaCampo` e, em alguns casos, `RequisicaoMaterial`;
- a requisição atual possui somente solicitado, aprovado, entregue e devolvido;
- `ReservaEstoque` não possui FK canônica para `ItemRequisicao`;
- entrega/retirada registra `SAIDA` física, mas não existe consumo posterior por item da requisição;
- `RequisicaoConfirmacao` registra o cabeçalho da confirmação, sem quantidades/divergências por item;
- o Campo consulta a requisição online e não possui tabelas Dexie nem comando offline para esse domínio;
- o sistema não representa adequadamente material em posse, perda, dano, extravio ou ferramenta retornável;
- a operação pode realizar uma baixa FIFO própria, ou reutilizar uma saída de requisição entregue, mas não há reconciliação de consumo real;
- a saída de requisição passa por caminho financeiro legado, enquanto o caminho oficial de custo é `OperacaoExecucao → CostAllocation`.

As evidências principais permanecem em:

| Camada | Evidência da auditoria 01A |
|---|---|
| Requisição/estoque | `services/api/operacional/models/estoque.py:104-231`; `services/api/operacional/schemas/estoque.py:230-330`; `services/api/operacional/routers/estoque.py:351-471`; `services/api/operacional/services/estoque_service.py:1471-1849` |
| Planejamento | `services/api/agricola/planejamento_operacional/models.py:98-163`; migrations `20260726c` e `20260726d`; `PlanoOperacionalService.aprovar_item` |
| Operação | `services/api/agricola/operacoes/models.py:8-137`; `services/api/agricola/operacoes/service.py:475-615` e `738-1198` |
| Campo | `services/api/campo/models.py:11-128`; `services/api/campo/service.py:865-930` e `1277-1450`; `apps/campo/src/lib/db.ts:376-410`; `apps/campo/src/lib/requisicoes-api.ts:60-107`; `apps/campo/src/components/campo/requisicoes-section.tsx:104-283` |
| Econômico | `services/api/agricola/custos/models.py:11-41`; `services/api/agricola/custos/allocation_service.py`; `services/api/agricola/dre/service.py:585-620` |
| Eventos | `services/api/events/base.py`; `services/api/events/outbox_model.py`; `services/api/events/outbox_service.py` |

## 3. Princípios de domínio

1. **A entrega não é consumo.** A entrega encerra a disponibilidade no depósito; o consumo representa uso real.
2. **O recebimento não é uma baixa física.** Ele é confirmação de posse e divergência.
3. **O estoque físico continua sendo um ledger append-only.** Não será criado estoque virtual de “posse operacional”.
4. **Eventos por item são a fonte de quantidades de custódia.** Campos agregados podem existir como projeção, mas não como fatos mutáveis independentes.
5. **A origem operacional é estruturada.** `origem_tipo/origem_id` genérico continua somente para compatibilidade e integrações não operacionais.
6. **A autorização é validada no backend.** Filtro de tela, URL ou dispositivo não substitui autorização de domínio.
7. **Cada comando mutativo é idempotente.** Retry, duplo clique e dois envios do mesmo dispositivo não podem gerar segunda saída, consumo ou devolução.
8. **O custo novo segue a arquitetura econômica oficial.** Não haverá `LancamentoFinanceiro` paralelo para o mesmo fato.
9. **Não se inventa histórico.** Requisições antigas sem evidência de consumo permanecem legadas/não conciliadas.
10. **Ferramenta de baixo valor é item retornável por quantidade.** Máquina ou equipamento patrimonializado continua em seu domínio próprio.

## 4. Fluxo canônico proposto

```text
SafraTarefa
  → PlanoOperacionalTarefa
  → PlanoOperacionalTarefaInsumo
  → reserva vinculada ao item planejado
  → aprovação/programação da OS
  → OperacaoAgricola + TarefaCampo + responsável
  → RequisicaoMaterial PENDENTE
  → aprovação da requisição
  → ReservaEstoque vinculada ao ItemRequisicao
  → separação por item/lote/depósito
  → entrega física
  → EstoqueMovimento SAIDA_REQUISICAO
  → conferência no Campo/Web
  → posse operacional derivada
  → OperacaoExecucao
  → consumo, devolução, perda, dano ou extravio
  → EstoqueMovimento DEVOLUCAO_REQUISICAO para retornos físicos
  → reconciliação do item e da requisição
  → custo real da execução
  → CostAllocation oficial
```

A entrega é o limite físico entre depósito e responsabilidade operacional. Se o recebedor recusar material após a entrega, a recusa não apaga a saída: gera divergência e, quando o item retornar fisicamente, um movimento de devolução ligado à saída original.

## 5. Máquina de estados

### 5.1 Estado persistido versus estado derivado

O cabeçalho da requisição deve persistir somente estados de workflow e comandos autorizados. Estados de quantidade parcial devem ser derivados dos itens/eventos para evitar duas verdades.

| Estado/resultado | Tratamento proposto | Regra |
|---|---|---|
| `PENDENTE` | Persistido | Criada, ainda não aprovada. |
| `APROVADA` | Persistido | Quantidades autorizadas; não significa estoque reservado. |
| `RESERVADA` | Persistido ou projeção de lifecycle | Todos os itens requeridos possuem reserva ativa suficiente. Recomenda-se expor como estado efetivo; a reserva é a fonte. |
| `EM_SEPARACAO` | Persistido | Picking iniciado; pode haver itens parciais. |
| `SEPARADA` | Persistido/projeção | Todos os itens entregáveis atingiram a quantidade que será entregue. |
| `ENTREGUE` | Persistido | Toda quantidade registrada como entregue saiu fisicamente do depósito. |
| `RECEBIDA` | Derivado/projeção | Todos os itens entregues foram aceitos ou tiveram divergência encerrada. |
| `PARCIALMENTE_RECEBIDA` | Derivado | Há recebimento parcial ou itens ainda aguardando conferência. |
| `EM_USO` | Derivado | Existe consumo e ainda há posse não conciliada. |
| `PARCIALMENTE_CONCILIADA` | Derivado | Alguns itens fecharam e outros ainda têm saldo sem destino. |
| `CONCILIADA` | Persistido após validação | Todos os itens fechados matematicamente e sem pendência de retorno/divergência. |
| `RECUSADA` | Resultado/evento e, se aplicável, estado de workflow | Recusa antes da aceitação; material deve ser devolvido fisicamente ou permanecer em pendência de retorno. |
| `CANCELADA` | Persistido | Permitida antes da entrega; depois dela somente encerramento por devolução/ajuste. |

`PARCIALMENTE_RECEBIDA`, `EM_USO` e `PARCIALMENTE_CONCILIADA` não devem ser armazenados como mutações independentes do cálculo dos itens. A API pode apresentar um `status_efetivo` derivado.

### 5.2 Transições canônicas

| Estado atual | Comando permitido | Validações principais | Próximo estado | Evento |
|---|---|---|---|---|
| inexistente | `criar_requisicao` | origem estruturada, tenant, UP, operação/tarefa e responsável válidos | `PENDENTE` | `MaterialRequestCreated` |
| `PENDENTE` | `aprovar` | papel autorizado, itens/quantidades válidos, sem duplicidade | `APROVADA` | `MaterialRequestApproved` |
| `APROVADA` | `reservar` | disponibilidade, item e plano compatíveis | `RESERVADA` efetiva | `MaterialReserved` |
| `APROVADA`/`RESERVADA` | `iniciar_separacao` | depósito, operador e versão atuais | `EM_SEPARACAO` | `MaterialPickingStarted` |
| `EM_SEPARACAO` | `registrar_separacao` | lote/depósito, quantidade ≤ aprovada/disponível, substituição autorizada | permanece ou `SEPARADA` | `MaterialSeparated` |
| `SEPARADA`/`EM_SEPARACAO` | `registrar_entrega` | handoff autorizado, item/lote, quantidade separada e saldo; transação única | `ENTREGUE` quando completo | `MaterialDelivered` |
| `ENTREGUE` | `conferir_recebimento` | recebedor autorizado, quantidade ≤ entregue, motivo de divergência | `RECEBIDA` efetiva ou parcial | `MaterialReceived` |
| `RECEBIDA`/parcial | `registrar_consumo` | execução compatível, quantidade ≤ posse, item não cancelado | `EM_USO` efetiva | `MaterialConsumptionRecorded` |
| `RECEBIDA`/`EM_USO` | `registrar_devolucao` | item/lote exatos, quantidade ≤ posse, depósito destino | parcial ou aguardando conciliação | `MaterialReturned` |
| `RECEBIDA`/`EM_USO` | `registrar_perda_dano_extravio` | motivo, evidência/papel, quantidade ≤ posse | parcial ou aguardando conciliação | `MaterialLossRecorded` |
| qualquer pré-entrega | `cancelar` | nenhuma saída física; autorização | `CANCELADA` | `MaterialRequestCancelled` |
| entregue/recebida/em uso | `conciliar` | fórmulas fecham e não há posse pendente | `CONCILIADA` | `MaterialRequestReconciled` |

Um comando fora da transição deve falhar com erro de domínio. O endpoint não deve permitir atualização arbitrária de status.

## 6. Modelo de quantidades

### 6.1 Fonte de cada quantidade

| Quantidade | Fonte canônica | Persistência proposta |
|---|---|---|
| `quantidade_solicitada` | comando de criação/item | Persistida em `ItemRequisicao`; imutável após aprovação, salvo revisão formal. |
| `quantidade_aprovada` | comando de aprovação | Persistida; nunca pode superar solicitada sem alteração autorizada registrada. |
| `quantidade_reservada` | soma de reservas ativas vinculadas ao item | Derivada de `ReservaEstoque`; pode ser projeção de leitura. |
| `quantidade_separada` | eventos `SEPARACAO` | Derivada do diário por item/lote. |
| `quantidade_entregue` | eventos `ENTREGA` | Derivada; corresponde à saída física. Campos atuais ficam como projeção legada/compatibilidade. |
| `quantidade_recebida` | eventos `RECEBIMENTO` | Derivada; não cria movimento físico. |
| `quantidade_consumida` | eventos `CONSUMO` | Derivada e vinculada a `OperacaoExecucao`. |
| `quantidade_devolvida` | eventos `DEVOLUCAO` | Derivada; cada devolução válida possui movimento físico correspondente. |
| `quantidade_perdida` | eventos `PERDA` | Derivada; não pode ser confundida com consumo. |
| `quantidade_danificada` | eventos `DANO` | Derivada; aplicável principalmente a retornáveis. |
| `quantidade_extraviada` | eventos `EXTRAVIO` | Derivada; exige motivo e autorização. |
| `quantidade_em_posse` | fórmula de eventos | Nunca digitada como fato independente. |

O diário proposto, `RequisicaoItemEvento`, deve registrar item, tipo, quantidade, unidade, lote, depósito, usuário, pessoa operacional, dispositivo, horário, motivo, versão e `client_operation_id`. Ele não é um segundo estoque; é o diário de custódia e apropriação do item.

### 6.2 Invariantes

Para todo item, em uma mesma unidade de medida normalizada:

```text
0 ≤ aprovada ≤ solicitada       (salvo revisão autorizada)
0 ≤ reservada ≤ aprovada
0 ≤ separada ≤ aprovada
0 ≤ entregue ≤ separada
0 ≤ recebida ≤ entregue
0 ≤ consumida ≤ recebida
0 ≤ devolvida + perdida + danificada + extraviada ≤ recebida
em_posse = recebida - consumida - devolvida - perdida - danificada - extraviada
em_posse ≥ 0
```

Para consumível:

```text
recebida = consumida + devolvida + perdida + danificada + extraviada + em_posse
```

Para retornável:

```text
recebida = devolvida + danificada + extraviada + em_posse
consumida = 0
```

`entregue - recebida` não é posse: é quantidade pendente de aceite, divergência ou retorno físico. Essa distinção evita atribuir ao trabalhador material que ele recusou.

## 7. Consumíveis

O item consumível deve guardar um snapshot de natureza `CONSUMIVEL`, além de produto, unidade e política de lote. O produto do catálogo pode ser a origem da classificação, mas o snapshot da requisição preserva o comportamento histórico caso o cadastro seja alterado.

Exemplos: fertilizante, defensivo, semente, combustível e peças consumíveis.

Fluxo:

```text
recebimento → em_posse
consumo     → reduz em_posse e alimenta a execução
devolução   → entrada física no depósito, reduz em_posse
perda       → encerra posse sem entrada física
```

Consumo exige item da requisição e `OperacaoExecucao`. Não deve ser inferido da quantidade planejada, solicitada, entregue ou do encerramento da tarefa.

## 8. Retornáveis

O item retornável deve guardar natureza `RETORNAVEL`. Para ferramentas de baixo valor, a unidade é controlada por quantidade no mesmo catálogo/estoque/requisição, sem criar patrimônio individual.

Fluxo:

```text
recebimento → posse temporária
devolução   → retorno ao depósito
dano        → não retorna como disponível; abre consequência definida
extravio    → encerra posse como perda
```

Para retornáveis, `CONSUMO` é proibido. A quantidade fica conciliada somente quando for devolvida, danificada ou extraviada, e a posse residual for zero. Máquinas e equipamentos patrimonializados permanecem no domínio de equipamentos/frota.

## 9. Responsabilidade operacional

Os papéis são diferentes:

| Papel | Significado | Evidência alvo |
|---|---|---|
| Solicitante | Criou a requisição ou originou o pedido | `RequisicaoMaterial.solicitante_id` e auditoria |
| Responsável da tarefa | Pessoa atribuída à execução | `OperacaoAgricola.operador_id`/`TarefaCampo.operador_id` |
| Recebedor autorizado | Pessoa autorizada a aceitar a entrega | atribuição da tarefa ou delegação ativa |
| Usuário da conferência | Conta que autenticou o comando | evento/confirmacão com `usuario_id` e dispositivo |
| Almoxarife/entregador | Usuário que separou/entregou | evento de separação/entrega |

Regra recomendada: o recebedor deve ser o responsável original ou um delegado explicitamente autorizado para aquela requisição/tarefa e janela de validade. Qualquer terceiro exige autorização prévia, motivo e trilha de quem concedeu.

O backend deve conferir, na mesma transação do comando:

- tenant do usuário, dispositivo, requisição e operação;
- vínculo da Unidade Produtiva e fazenda permitida ao dispositivo;
- responsabilidade vigente ou delegação vigente;
- estado/versionamento do item;
- papel suficiente para aprovar, entregar, receber, consumir, devolver ou ajustar.

Propõe-se `RequisicaoResponsabilidadeHistorico` somente porque o modelo atual não conserva histórico de delegação. Ele deve conter requisição, pessoa/usuário autorizado, papel, concedente, vigência, revogação e motivo. Não é um novo sistema de usuários; é uma trilha de autorização contextual.

## 10. Rastreabilidade da origem

Para uma requisição operacional, a origem canônica deve ser:

```text
tenant_id
unidade_produtiva_id
safra_tarefa_id
plano_operacional_tarefa_id (quando originada do planejamento)
operacao_agricola_id
responsavel_pessoa_id
```

`OperacaoExecucao` não deve ser FK única no cabeçalho, porque uma requisição pode ser consumida em mais de uma execução. O vínculo deve estar no evento `CONSUMO`.

`fase` deve ser derivada de `SafraTarefa.fase` quando esse for o modelo vigente; não é necessário criar uma FK de fase duplicada. `safra_id` e `unidade_produtiva_id` devem ser armazenados ou validados diretamente para impedir fallback silencioso para safra ativa.

Para requisição manual sem planejamento, `origem_tipo` e `origem_id` devem ser acompanhados por motivo estruturado, papel autorizado e, quando houver operação, o vínculo direto com `OperacaoAgricola`. Se a origem operacional for conhecida, não se deve usar somente JSON ou texto livre.

A pergunta “por que este material foi solicitado?” deve ser respondida pela cadeia estruturada até a tarefa/operação, ou por justificativa manual obrigatória e auditável.

## 11. Planejamento e geração da requisição

A sequência existente deve permanecer, com uma mudança de semântica:

```text
SafraTarefa
→ PlanoOperacionalTarefa
→ PlanoOperacionalTarefaInsumo
→ OperacaoAgricola programada
→ RequisicaoMaterial
```

### Quando a requisição nasce

Recomendação: no momento da programação/liberação da OS para execução, quando já existirem operação, unidade produtiva e responsável. A aprovação do planejamento deve reservar ou preparar disponibilidade, mas não deve necessariamente criar requisições físicas para toda necessidade ainda não programada.

A geração automática deve ser parte da transação de criação/liberação da operação quando houver insumos. O comportamento atual “criar requisição best-effort e seguir com a OS” deve ser substituído por falha explícita quando a requisição obrigatória não puder ser criada. Operações sem material não criam requisição.

Solicitação manual continua válida para exceções, mas precisa indicar a origem estruturada ou justificativa e impedir outra requisição aberta equivalente para a mesma operação/item sem confirmação de revisão.

### Proteção contra duplicidade

Chave lógica recomendada para a geração automática:

```text
tenant_id + operacao_agricola_id + origem_planejamento + versão da necessidade
```

O comando também deve possuir idempotency key. Reprocessamento da geração retorna a requisição existente, não cria nova saída nem novos itens.

## 12. Reserva

`ReservaEstoque` continua sendo a reserva física; não deve haver reserva órfã nem reserva paralela dentro da requisição.

Relação alvo:

```text
PlanoOperacionalTarefaInsumo 1 ── N ReservaEstoque
ItemRequisicao               1 ── N ReservaEstoque
```

Uma reserva pode nascer no planejamento e ser associada ao item da requisição na liberação da OS. Complementos ou reservas divididas geram linhas adicionais ligadas ao mesmo item. A FK para `ItemRequisicao` deve ser explícita; `reference_type/reference_id` fica para legado.

Estados de reserva sugeridos: `ATIVA`, `PARCIALMENTE_CONSUMIDA`, `CONSUMIDA`, `LIBERADA`, `CANCELADA`. A soma ativa é a quantidade reservada. Na entrega, a quantidade utilizada da reserva é consumida/liberada na mesma transação do movimento físico. Se houver atendimento parcial, o restante permanece ativo ou é liberado conforme decisão de estoque.

Não se deve permitir entrega de item reservado sem vincular a reserva consumida, nem liberar uma reserva que já tenha sustentado uma saída sem registrar a relação.

## 13. Separação/picking

Separação deixa de ser apenas mudança para `SEPARANDO`. Cada item separado deve preservar:

- quantidade;
- unidade normalizada;
- lote;
- depósito/localização;
- responsável pelo picking;
- timestamp;
- substituição e autorização, quando houver;
- divergência ou falta.

O estado `SEPARADA` somente é efetivo quando os itens entregáveis atingirem a quantidade aprovada a ser entregue. `20 L solicitados, 18 L separados` permanece parcial e não perde a informação ao chegar ao Campo.

Substituição de produto exige autorização, motivo e item substituto rastreável. Não deve sobrescrever silenciosamente o produto original.

## 14. Entrega física

`ENTREGA` significa o handoff físico:

```text
depósito → responsabilidade operacional
```

O `EstoqueMovimento SAIDA_REQUISICAO` ocorre neste momento, não na separação e não na conferência. A transação deve incluir:

1. validação de estoque/lote/depósito;
2. gravação do evento `ENTREGA` por item;
3. gravação do movimento físico;
4. consumo/liberação da reserva correspondente;
5. atualização da versão e estado;
6. outbox após a operação atômica.

Se o responsável recusar depois do handoff, a saída não é apagada. Registra-se `RECUSA`/`DIVERGENCIA`; o retorno físico gera `DEVOLUCAO_REQUISICAO` apontando para o evento e movimento de entrega. Assim não existe rollback invisível nem dupla baixa.

## 15. Recebimento/conferência

O Campo/Web deve permitir conferência item a item:

```text
quantidade entregue
quantidade recebida
unidade
lote
resultado
motivo/divergência
usuário
pessoa recebedora
device_id
data/hora do dispositivo e do servidor
```

Resultados recomendados:

- `RECEBIDO_INTEGRAL`;
- `RECEBIDO_PARCIAL`;
- `RECUSADO`;
- `DIVERGENTE`.

São resultados do comando/evento, não necessariamente quatro estados persistidos do cabeçalho. A quantidade recebida nunca deve substituir a quantidade entregue; ambas permanecem auditáveis.

O recebimento não altera saldo de estoque. Ele confirma o que ficou em posse. Quantidade entregue mas não recebida permanece como pendência de aceite/retorno, não como consumo nem como posse aceita.

## 16. Consumo real

O consumo é informado durante a execução ou no fechamento, preferencialmente item a item, sempre com:

- `requisicao_item_id`;
- `operacao_execucao_id`;
- quantidade e unidade normalizada;
- lote efetivamente usado;
- usuário/pessoa e timestamp;
- device e `client_operation_id`;
- observação quando houver desvio.

O backend valida:

```text
quantidade_consumo ≤ quantidade_em_posse
```

e verifica que a execução pertence à mesma operação/origem da requisição. Consumo excedente exige comando complementar de ajuste autorizado; não é aceito como efeito colateral.

Quando existirem várias requisições para a mesma operação, o consumidor seleciona explicitamente o item. O servidor não deve escolher silenciosamente “a primeira requisição aberta”. Uma operação pode consumir itens de várias requisições, cada evento mantendo sua própria origem.

O consumo não gera uma segunda saída física se a entrega já retirou o material do depósito. Ele gera evento operacional e valor de custo a reconciliar.

## 17. Devolução

Cada devolução possui item, quantidade, lote, depósito destino, responsável, data/hora, motivo e referência à posse/evento de origem. O movimento físico é:

```text
EstoqueMovimento DEVOLUCAO_REQUISICAO
ajuste_de = evento/movimento de ENTREGA específico
```

Não é seguro procurar apenas a primeira saída por produto/requisição. A associação deve ser por item, lote e evento/movimento de origem. Uma devolução parcial pode ser registrada em várias operações, desde que a soma não exceda a posse.

Para consumível:

```text
recebido 100; consumido 92; devolvido 8; posse 0.
```

Para retornável:

```text
recebido 5; devolvido 4; danificado 1; posse 0.
```

## 18. Perda, dano e extravio

São eventos distintos:

| Evento | Semântica | Estoque físico após entrega | Custo |
|---|---|---|---|
| `PERDA` | Consumível que não foi consumido nem retornou | Não há nova saída; o item já saiu | Deve seguir política de perda operacional ou estoque, definida antes da implementação |
| `DANO` | Retornável/material que não volta utilizável | Não entra como disponível; pode exigir ajuste/triagem | Não deve ser confundido com consumo; política de impairment/manutenção precisa de decisão |
| `EXTRAVIO` | Item não localizado | Não há entrada física | Deve ter causa, responsável e tratamento econômico/auditável |
| `AJUSTE` | Correção autorizada de divergência | Movimento somente se houver impacto físico real | Não substitui eventos originais |

Recomendação de política: perda/dano/extravio ocorridos após a entrega ficam registrados na requisição e podem compor uma categoria de perda da execução quando atribuíveis à operação; perdas anteriores à entrega pertencem ao estoque e não à operação. Dano patrimonializado ou manutenção não deve ser inventado neste fluxo.

## 19. Conciliação

A conciliação é por item e depois por requisição. O item somente fecha quando:

```text
em_posse = 0
```

e não há divergência, retorno ou aprovação de ajuste pendente.

Para consumíveis:

```text
recebida = consumida + devolvida + perdida + danificada + extraviada
```

Para retornáveis:

```text
recebida = devolvida + danificada + extraviada
consumida = 0
```

Uma requisição é `CONCILIADA` quando todos os itens estão fechados. A operação pode ser impedida de ser encerrada se houver requisição não conciliada, ou pode aceitar uma exceção formal aprovada; esta é uma decisão humana pendente, com recomendação de bloqueio por padrão.

## 20. Ledger de estoque

O ledger físico permanece único e append-only.

| Evento | Reserva | Saída física | Entrada física | Impacta saldo |
|---|---:|---:|---:|---:|
| Solicitação | Não | Não | Não | Não |
| Aprovação | Não | Não | Não | Não |
| Reserva | Aumenta | Não | Não | Saldo disponível/reservado conforme regra atual |
| Separação | Mantém/ajusta | Não | Não | Não, salvo política explícita de picking físico |
| Entrega | Consome/libera a reserva correspondente | Sim, `SAIDA_REQUISICAO` | Não | Sim |
| Recebimento | Não | Não | Não | Não |
| Consumo | Não | Não | Não | Não, pois a saída já ocorreu |
| Devolução | Não | Não | Sim, `DEVOLUCAO_REQUISICAO` | Sim |
| Perda/dano/extravio após entrega | Não | Não | Não | O saldo já foi reduzido na entrega; ajuste adicional só se existir fato físico novo |
| Ajuste de estoque | Conforme caso | Conforme caso | Conforme caso | Sim |

Cada movimento de entrega/devolução deve apontar para o item/evento exato. A proteção contra dupla baixa é formada por:

- uma transação que grava evento e movimento juntos;
- chave idempotente por comando;
- restrição/consulta de quantidade disponível sob lock;
- `version` otimista do item/requisição;
- proibição de consumo de estoque no fechamento da operação quando a quantidade já foi entregue;
- testes de retry, concorrência e duplo dispositivo.

## 21. Integração econômica

O caminho oficial permanece:

```text
OperacaoAgricola
→ OperacaoExecucao
→ CostAllocation
→ DRE/Dashboard
```

O custo de material não deve ser criado na entrega. Na entrega, cada item/movimento guarda custo unitário/lote para rastreabilidade. No consumo, o valor é calculado pela quantidade consumida e pelo custo efetivo do lote/movimento de origem.

O serviço de reconciliação da execução deve somar os custos dos eventos `CONSUMO` e, conforme política aprovada, eventos de perda atribuíveis à operação. Esse valor compõe `OperacaoExecucao.custo_real`; a alocação oficial é uma `CostAllocation` idempotente com origem `OPERATION_EXECUTION`.

Não deve existir simultaneamente:

```text
CostAllocation da execução
+ CostAllocation independente da entrega
+ LancamentoFinanceiro da mesma saída
```

Para o cenário de 100 kg recebidos, 92 kg consumidos e 8 kg devolvidos, o custo de material da operação é o custo dos 92 kg, não dos 100 kg. A devolução reduz o saldo físico, mas não gera custo da operação. FIFO/custo médio deve seguir o custo efetivo do lote selecionado; o critério precisa ser uniforme com o ledger atual.

## 22. Campo offline

O fluxo deve reutilizar a infraestrutura existente do Campo, mas não o `fetch` direto atual para mutações.

### 22.1 Cache local

Adicionar conceitualmente ao Dexie:

- `requisicoes`: projeção do cabeçalho, tenant, UP, operação, tarefa, responsável, versão e status efetivo;
- `requisicao_itens`: quantidades, natureza, lote, resumo dos eventos e versão;
- `requisicao_operacoes_pendentes`: comandos locais, ou equivalente integrado à `sync_queue`, com payload, sequência, estado, tentativas, erro e ACK.

As tabelas de requisição são cache/projeção; não são fonte de verdade. A operação pendente deve conter `tenant_id`, `user_id`, `device_id`, `unidade_produtiva_id`, `requisicao_id`, `item_id`, `command_type`, `client_operation_id`, `base_version`, `created_at`, `sequence_no` e estado local.

### 22.2 Pull/push

O `pull` deve trazer somente requisições autorizadas para o dispositivo/responsável, com itens e versão. O `push` deve suportar uma entidade/comando de requisição pela fila existente, em vez de criar um segundo mecanismo de sincronização.

Fluxo:

```text
pull server
→ cache Dexie
→ usuário confirma offline
→ grava comando pendente
→ UI aplica projeção local
→ push FIFO
→ validação transacional no servidor
→ ACK CREATED/UPDATED ou CONFLICT/ERROR
→ reconciliação da projeção
```

`client_operation_id` é gerado uma vez, permanece no retry e possui unicidade por tenant. Não deve ser recriado a cada tentativa.

### 22.3 Isolamento e logout

O servidor valida tenant, usuário, dispositivo, UP e autorização em todo push. Troca de usuário no mesmo dispositivo deve limpar ou isolar o cache por usuário/tenant e não pode enviar pendências de outro usuário com nova identidade. Logout com pendências deve bloquear a troca até sincronizar ou colocar as operações em quarentena auditável.

## 23. Idempotência e concorrência

Casos protegidos:

| Caso | Estratégia |
|---|---|
| Duplo clique | `client_operation_id` único e UI com estado pendente |
| Retry HTTP | servidor devolve ACK original para a mesma chave |
| Sync repetido | evento/comando único por tenant + chave |
| Dois dispositivos | lock/versão e validação de posse disponível |
| Web + Campo simultâneos | comando que vencer a versão é aplicado; outro recebe conflito/revisão |
| Devoluções concorrentes | lock do item/quantidade em posse e transação única |
| Consumos concorrentes | lock/versão e limite de posse |
| Entregas concorrentes | lock de estoque/lote e idempotência da saída |

O item deve possuir versão otimista ou a requisição deve possuir versão monotônica. Operações de estoque utilizam também o mecanismo transacional/lock já adotado pelo ledger. A ordem de comandos do mesmo item deve ser preservada; consumo offline anterior à confirmação de recebimento não deve ser aceito sem política explícita de sequência.

## 24. Domain Events/Outbox

A infraestrutura existente em `services/api/events` deve ser reutilizada. Os comandos de estoque e custódia continuam transacionais; Outbox não deve ser usado para deixar a baixa física eventual.

Eventos úteis, somente quando houver consumidor:

| Evento | Consumidor/valor |
|---|---|
| `MaterialRequestCreated` | auditoria, notificações e integração operacional |
| `MaterialRequestApproved` | notificações/planejamento |
| `MaterialReserved` | disponibilidade e alertas |
| `MaterialSeparated` | acompanhamento do almoxarifado |
| `MaterialDelivered` | notificações e auditoria; não executa nova baixa |
| `MaterialReceived` | acompanhamento da tarefa |
| `MaterialConsumptionRecorded` | reconciliação de custo e indicadores |
| `MaterialReturned` | estoque e auditoria; o movimento físico já foi gravado na transação |
| `MaterialLossRecorded` | auditoria/alerta e política econômica |
| `MaterialRequestReconciled` | fechamento e indicadores |

Cada evento deve carregar tenant, UP, origem, item, operação, versão, `event_id`, `correlation_id` e `idempotency_key`. A alocação econômica pode ser recalculada pelo serviço de reconciliação, mas não deve depender de uma entrega assíncrona para que o ledger físico fique correto. Consumidores Outbox devem ser idempotentes.

## 25. Compatibilidade com dados existentes

Não se deve fabricar consumo histórico.

| Classe | Interpretação segura | Tratamento alvo |
|---|---|---|
| `LEGACY_OPEN` | `PENDENTE`, `APROVADA` ou `SEPARANDO` sem handoff comprovado | Mantém status legado; pode ser encerrada/reaberta por processo de compatibilidade antes de entrar no fluxo novo. |
| `LEGACY_DELIVERED` | `ENTREGUE` e `quantidade_entregue` existente | Interpretar como quantidade fisicamente entregue/baixada, não como consumida nem necessariamente recebida por item. Marcar não conciliada. |
| `LEGACY_RETURNED` | `quantidade_devolvida` existente e/ou confirmação de devolução | Preservar devolução conhecida; não inferir consumo, lote, motivo ou usuário ausente. |

`quantidade_entregue` atual deve virar projeção de eventos de entrega somente quando houver evidência suficiente. Uma confirmação antiga pode comprovar que houve uma ação de retirada, mas não permite inventar quantidade recebida por item, divergência ou consumo.

Quando houver movimento de devolução e origem identificável, uma representação de compatibilidade pode apontar para o legado com `provenance=LEGACY`. Se não houver evidência de movimento, não se cria entrada no estoque para “corrigir” o histórico.

CostAllocation/LancamentoFinanceiro existentes não devem ser recalculados retroativamente apenas para tentar estimar consumo. O custo histórico permanece histórico; somente o fluxo novo aplica a regra de consumo real.

## 26. Cenário E2E principal

### 26.1 Dados

```text
Tarefa: aplicação agrícola
Solicitado: A 100 kg; B 20 L; Tesoura 3
Separado:  A 100 kg; B 18 L; Tesoura 3
Recebido:  A 100 kg; B 18 L; Tesoura 3
Executado: A consumido 92 kg; B consumido 17 L
Final: A devolvido 8 kg; B devolvido 1 L; Tesouras devolvidas 2; danificada 1
```

### 26.2 Evolução

1. `RequisicaoMaterial=PENDENTE`; três `ItemRequisicao` com natureza consumível, consumível e retornável.
2. Aprovação: A=100, B=20, tesoura=3. Reservas vinculadas aos itens.
3. Picking: eventos de separação A=100, B=18, tesoura=3. B permanece abaixo do solicitado; estado efetivo é parcial em separação.
4. Entrega: eventos A=100, B=18, tesoura=3 e três movimentos `SAIDA_REQUISICAO`. O saldo do depósito baixa uma única vez.
5. Recebimento: eventos aceitos A=100, B=18, tesoura=3. Não há movimento de estoque. `em_posse`: A=100, B=18, tesoura=3.
6. Execução: consumo A=92 e B=17, ambos com `OperacaoExecucao`. `em_posse`: A=8, B=1, tesoura=3.
7. Devolução: A=8 e B=1 geram eventos e movimentos `DEVOLUCAO_REQUISICAO` ligados às saídas correspondentes. `em_posse`: A=0, B=0.
8. Ferramentas: devolução=2, dano=1. Não há consumo. `em_posse=0`.
9. Conciliação: A `100=92+8`; B `18=17+1`; tesoura `3=2+1`. Todos os itens fecham.
10. Economia: CostAllocation oficial da execução inclui custo de 92 kg A + 17 L B, além dos demais componentes econômicos aplicáveis. Não inclui A devolvido, B devolvido, nem as três tesouras como consumo.

O cenário fecha matematicamente. A quantidade B solicitada de 20 L não é convertida em entregue/recebida; ficam registrados solicitado=20, separado/entregue/recebido=18.

## 27. Cenário offline

1. O responsável sincroniza a operação e a requisição. Dexie grava cabeçalho/itens, versão `v10`.
2. Sem conexão, registra confirmação para A=100 e B=18. A fila cria `client_operation_id=op-abc`, `base_version=v10`, sequência 1 e aplica projeção local.
3. O usuário pressiona confirmar novamente. A UI não cria nova operação; reutiliza `op-abc` ou bloqueia por estado pendente.
4. A conexão retorna. O push envia `op-abc`. O servidor valida autorização, versão, quantidades e grava eventos/confirmacão/movimentos em uma única transação.
5. O servidor retorna `CREATED`/ACK com estado canônico. A fila marca DONE e atualiza Dexie.
6. Se o mesmo payload for enviado novamente, a chave única devolve o ACK original. Não há segunda confirmação, segunda saída ou segundo evento.

O estado final é uma confirmação, uma saída por item e uma versão incrementada. O segundo envio é idempotente, não uma nova operação de negócio.

## 28. Cenário de conflito

O Web altera quantidade ou lote enquanto o Campo está offline com versão anterior.

O comando offline leva `base_version=v10`. O Web grava a alteração e o item passa a `v11`.

Política:

- alteração apenas informativa: pode ser mesclada;
- alteração de quantidade, produto, lote, depósito, estado ou responsabilidade: não há merge automático;
- o servidor responde `CONFLICT` com projeção canônica v11;
- o Campo mantém a operação pendente em estado de conflito, sem baixa/recebimento parcial escondido;
- o usuário precisa revisar e confirmar novamente contra v11;
- se o material já tiver sido entregue/consumido por outro dispositivo, a revisão pode ser rejeitada definitivamente.

Essa política é mais segura que `server-wins` cego para quantidade e lote. `server-wins` continua válido para campos não materiais, conforme a infraestrutura offline existente.

## 29. Modelo alvo

### 29.1 `RequisicaoMaterial`

**Manter e alterar:** preservar o cabeçalho, acrescentando origem estruturada mínima: `safra_id`, `safra_tarefa_id`, `plano_operacional_tarefa_id` quando aplicável, `operacao_agricola_id`, UP e responsável operacional. Manter `origem_tipo/origem_id` para legado, mas não como fonte para requisição originada de operação. Adicionar versão, estado de compatibilidade e motivo manual quando necessário.

### 29.2 `ItemRequisicao`

**Manter e alterar:** preservar produto, UOM, solicitado/aprovado e referências legadas. Acrescentar snapshot `natureza_item` (`CONSUMIVEL`/`RETORNAVEL`) e permitir múltiplos lotes por eventos. Não adicionar os doze campos de quantidade como fatos mutáveis duplicados; expor projeções derivadas do diário.

### 29.3 `RequisicaoItemEvento` — nova entidade indispensável

**Criar:** o modelo atual não registra quantidade, lote, motivo, dispositivo, comando e vínculo de execução por fato. A entidade é um diário operacional, não um estoque.

Campos conceituais: tenant, requisição, item, tipo de evento, quantidade, unidade, produto/lote/depósito efetivos, operação/execution quando aplicável, usuário, pessoa, dispositivo, timestamp do dispositivo/servidor, motivo, versão, correlação e `client_operation_id` único por tenant.

Tipos: `SEPARACAO`, `ENTREGA`, `RECEBIMENTO`, `RECUSA`, `CONSUMO`, `DEVOLUCAO`, `PERDA`, `DANO`, `EXTRAVIO`, `AJUSTE_AUTORIZADO`.

### 29.4 `RequisicaoResponsabilidadeHistorico`

**Criar, se confirmada a necessidade de delegação histórica:** o modelo atual possui responsável da tarefa, mas não histórico de delegação contextual. A entidade registra autorizado, papel, concedente, vigência, revogação e motivo. Reutiliza usuários/pessoas existentes; não cria identidade nova.

### 29.5 `RequisicaoConfirmacao`

**Manter e alterar:** continuar como registro de comando/conferência de cabeçalho, adicionando `device_id`, `client_operation_id`, versão, resultado e vínculo ao lote de eventos por item. Não deve continuar sendo a única prova de quantidade.

### 29.6 `ReservaEstoque`

**Manter e alterar:** adicionar FK nullable para `ItemRequisicao`, suportar parcialidade e estados de liberação/consumo. Preservar a ligação existente ao insumo planejado. A reserva é consumida/liberada junto à entrega.

### 29.7 `EstoqueMovimento`

**Manter:** ledger append-only. Recomenda-se FK direta opcional para `RequisicaoItemEvento` e referência explícita ao movimento de origem em devoluções. Não criar ledger paralelo.

### 29.8 `OperacaoAgricola`

**Manter:** continuar como origem da execução e da responsabilidade. A requisição aponta para a operação; a operação não deve realizar nova baixa quando o item já saiu pela entrega.

### 29.9 `OperacaoExecucao`

**Manter e integrar:** eventos de consumo apontam para a execução. `custo_real` passa a incorporar reconciliação de consumo real, sem usar quantidade planejada/entregue como substituto.

### 29.10 `CostAllocation`

**Manter:** uma alocação econômica oficial por execução/fonte idempotente. O consumo de itens alimenta a composição do custo; não criar alocação de entrega que depois seria somada novamente.

### 29.11 Campo/Dexie

**Alterar:** adicionar caches de requisições/itens e operações pendentes; reutilizar `sync_queue`, dispositivo, sessão e estados de retry existentes. Remover, em fase posterior, mutações diretas síncronas do fluxo de requisição.

## 30. Matriz de impacto

| Área | Alteração necessária | Impacto | Risco |
|---|---|---:|---|
| Banco | Diário de eventos, vínculo reserva/item, origem estruturada, versão e autorização | CRÍTICO | Backfill incorreto e duplicidade de fatos |
| Models | Novos relacionamentos e projeções de quantidades | ALTO | Duas fontes de verdade |
| Estoque | Entrega como única saída, devolução ligada à saída exata, locks/idempotência | CRÍTICO | Dupla baixa ou saldo inconsistente |
| Planejamento | Transferir reserva para item de requisição e geração na liberação da OS | ALTO | Reserva órfã ou requisição duplicada |
| Operações | Consumo por `OperacaoExecucao`, sem FIFO/baixa duplicada | CRÍTICO | Custo ou estoque duplicado |
| Web | Workflow, picking, entrega, divergência, reconciliação e autorização | ALTO | Comandos fora de estado |
| Campo | Conferência item a item e projeção offline | ALTO | Usuário vê estado obsoleto |
| Dexie | Tabelas/cache, fila, client operation e conflito | ALTO | Perda/duplicidade em troca de usuário |
| Sync | Pull/push de comandos de requisição, ACK e conflito | CRÍTICO | Retry não idempotente |
| CostAllocation | Reconciliar custo de consumo real por execução | CRÍTICO | Dupla contabilização |
| DRE | Nenhuma arquitetura paralela; consumir alocação oficial | MÉDIO | Retroatividade em legado |
| Outbox | Eventos de lifecycle após transação, consumidores idempotentes | MÉDIO | Evento duplicado ou ordem incorreta |
| Testes | Unitários, integração, offline, concorrência, tenant e E2E | ALTO | Contrato aparentemente implementado sem prova |

## 31. Estratégia incremental 01C+

### 01C — Fundação de domínio e compatibilidade

Criar contrato/enums, diário de eventos, versão/idempotência, vínculo reserva/item, origem estruturada e classificação de legado. Critério de GO: invariantes e restrições testados sem alterar comportamento histórico.

### 01D — Reserva, separação e entrega

Implementar reserva ligada ao item, picking por lote, handoff e única saída física. Critério de GO: cenários total/parcial/substituição e nenhum segundo movimento em retry.

### 01E — Campo offline e segurança

Adicionar pull/cache, comandos Dexie, push, ACK, conflitos, troca de usuário e autorização de responsável/delegado. Critério de GO: cenário offline obrigatório e isolamento tenant/UP.

### 01F — Consumo, devolução e retornáveis

Implementar eventos de consumo, devolução, perda, dano, extravio, fórmulas e conciliação. Critério de GO: cenário A/B/tesouras fecha sem posse residual.

### 01G — Integração econômica

Reconciliar consumo real com `OperacaoExecucao` e `CostAllocation`, desativando o caminho duplicado para requisições novas. Critério de GO: DRE não dobra valores e devolução não vira custo.

### 01H — Validação E2E e cutover

Executar testes de segurança, concorrência, legado, tenant, offline, conflito, auditoria e operação completa. Critério de GO: evidência automatizada e plano de tratamento das requisições legadas.

## 32. Riscos

- Reaproveitar `quantidade_entregue` como consumo perpetuaria custo superestimado.
- Manter baixa FIFO da operação depois da entrega causaria dupla baixa física.
- Derivar autorização somente no Campo permitiria recebimento indevido por API.
- Backfill agressivo poderia fabricar consumo histórico e alterar DRE retroativamente.
- Usar lote/produto sem evento exato de origem repetiria a fragilidade da devolução atual.
- Permitir consumo offline sem versão poderia exceder a posse real.
- Criar uma tabela de posse/depósito virtual separada duplicaria o estoque e aumentaria reconciliações.
- Tratar ferramenta retornável como consumível eliminaria a pendência de devolução e dano.
- Emitir Outbox antes do commit deixaria eventos publicados sem movimento físico correspondente.

## 33. Decisões arquiteturais

1. A saída física ocorre na entrega/handoff.
2. Recebimento é confirmação, não saída.
3. Consumo é posterior, por item e execução.
4. `em_posse` é derivado; não há estoque virtual.
5. Eventos por item são a fonte de custódia; o ledger continua fonte física.
6. Consumível e retornável compartilham item/estoque, mas têm invariantes diferentes.
7. A requisição nasce na liberação/programação da OS, quando a responsabilidade é conhecida.
8. Reserva deve estar ligada explicitamente ao item da requisição.
9. Devolução aponta para entrega específica, lote e depósito.
10. O custo oficial é o custo real reconciliado na execução, via `CostAllocation`.
11. Offline usa a fila existente e `client_operation_id`, sem endpoint mutativo paralelo.
12. Conflito material de quantidade/lote exige nova conferência; não há merge cego.
13. Histórico legado não recebe consumo inferido.

## 34. Questões que dependem de decisão humana

As seguintes escolhas não devem ser silenciosamente fixadas durante a implementação:

1. **Terceiro recebedor:** aprovar somente responsável/delegado pré-cadastrado, ou permitir terceiro com aprovação do almoxarifado? Recomendação: pré-autorização contextual.
2. **Encerramento da operação:** bloquear até todas as requisições conciliadas, ou permitir exceção com aprovação? Recomendação: bloquear por padrão e exigir exceção auditável.
3. **Perda/dano/extravio:** decidir se o valor pós-entrega compõe custo da operação, perda operacional separada ou impairment/maintenance. Recomendação: perda atribuível à execução compõe categoria separada na alocação da execução; dano patrimonializado segue domínio próprio.
4. **Usuário versus pessoa:** confirmar a relação oficial entre conta autenticada e `operador_id`/pessoa para autorização e auditoria.
5. **Ferramentas de baixo valor:** confirmar controle exclusivamente por quantidade ou necessidade futura de lote/série para alguma classe.
6. **Legado entregue:** confirmar se uma confirmação histórica de retirada é suficiente para marcar “recebido” ou se todos permanecerão `LEGACY_DELIVERED` não conciliados. Recomendação: não inferir recebimento por item sem evidência.

Essas decisões não invalidam o contrato técnico principal, mas devem ser registradas como decisões de produto/domínio antes da migration correspondente.

## 35. Veredicto

O contrato canônico está suficientemente definido para iniciar uma implementação incremental, desde que as decisões humanas da seção 34 sejam aprovadas antes de alterar o banco e que cada fase tenha seu próprio GO/NO-GO. O desenho preserva tenant/RLS, ledger append-only, PWA offline, `OperacaoExecucao → CostAllocation`, Outbox global e migrations existentes.

**MATERIAL-REQUISITION-FLOW-01B**
**STATUS: GO COM RESSALVAS**
**PRÓXIMA FASE RECOMENDADA: 01C — Fundação de domínio, idempotência, origem estruturada, eventos por item e compatibilidade legada.**

### Respostas obrigatórias

**A. Em qual momento o material deve deixar fisicamente o estoque disponível?**
No commit do evento `ENTREGA`/handoff, quando o almoxarifado entrega fisicamente ao responsável autorizado. Nesse mesmo commit ocorre uma única `SAIDA_REQUISICAO`.

**B. Em qual momento ele deve ser considerado consumido pela operação?**
Somente quando um comando `CONSUMO` for registrado para o item, vinculado a uma `OperacaoExecucao`, validado contra a quantidade em posse.

**C. Qual quantidade deve alimentar o custo real da operação?**
A quantidade efetivamente consumida, valorizada pelo custo/lote aplicável, acrescida somente das perdas que a política aprovada atribuir à execução. Não a quantidade solicitada, aprovada, entregue ou recebida por si só.

**D. Como representar material entregue mas ainda não consumido?**
Como `recebida - consumida - devolvida - perdida - danificada - extraviada`, derivado no item/evento, sem novo estoque. Essa quantidade é `em_posse`.

**E. Como ferramentas retornáveis devem compartilhar o fluxo sem virar consumíveis?**
Como `ItemRequisicao.natureza_item=RETORNAVEL`, com recebimento, posse, devolução, dano ou extravio; `CONSUMO` é proibido e a conciliação usa a fórmula própria de retornável.

**F. Como impedir dupla baixa de estoque?**
Baixar somente na entrega, gravar movimento/evento/reserva em transação única, usar `client_operation_id`, versão/lock e impedir a baixa FIFO adicional no fechamento da operação.

**G. Como impedir dupla contabilização econômica?**
Não criar custo na entrega e não usar `LancamentoFinanceiro` paralelo. Reconciliar consumo real na `OperacaoExecucao` e gerar/atualizar uma única `CostAllocation` oficial por execução/fonte idempotente.

**H. Como garantir que somente o responsável ou delegado possa receber?**
Validar no backend vínculo da tarefa/operação, delegação vigente, tenant, UP, dispositivo e papel; registrar usuário, pessoa, dispositivo, vigência e motivo. O frontend não é mecanismo de segurança.

**I. Como o mesmo fluxo funcionará offline sem duplicidade?**
Cache Dexie, comando na fila existente, `client_operation_id` estável, `base_version`, FIFO por item, retry, ACK original para repetição, conflito explícito e reconciliação server-canonical após o push.

**J. Quais mudanças mínimas são necessárias para transformar o estado atual no modelo canônico?**
Criar o diário `RequisicaoItemEvento`; ligar reservas a itens; estruturar origem/responsabilidade; separar entrega, recebimento e consumo; registrar saída somente na entrega; adicionar devolução exata por evento/lote; integrar consumo a `OperacaoExecucao`/`CostAllocation`; adicionar cache/fila offline de requisição; aplicar idempotência/versão; classificar legado sem inventar consumo; e cobrir tudo com testes E2E, offline, concorrência e tenant.
