# MATERIAL-REQUISITION-FLOW-01F — Consumo, Devolução, Retornáveis e Conciliação

Data: 2026-09-25  
Escopo: implementação incremental posterior ao 01E  
Banco de validação: PostgreSQL de desenvolvimento `farms`, schema `farms`; nunca produção.

## 1. Resumo executivo

O ciclo posterior ao recebimento foi implementado no serviço canônico de posse operacional.

O desenho preserva a separação:

```text
ENTREGA física ≠ RECEBIMENTO ≠ CONSUMO
```

Consumo, perda, dano e extravio registram fatos no diário da requisição e não movimentam estoque. Devolução registra o fato operacional e, atomicamente, uma única entrada física vinculada ao evento de devolução.

Também foram implementados:

- posse derivada dos eventos;
- validação de posse disponível;
- consumo vinculado a `OperacaoExecucao` e à operação da requisição;
- proibição de consumo para `RETORNAVEL`;
- devolução por entrega/lote/depósito explícitos;
- retry idempotente;
- versionamento e lock da requisição;
- projeção Campo com consumo, devolução, perda, dano, extravio e conciliação;
- fila offline reutilizando o `sync_queue` existente;
- bloqueio normal de fechamento de operação não conciliada.

O resultado é `GO COM RESSALVAS`. A lógica principal foi validada em PostgreSQL real, incluindo concorrência de dois consumos, retry de devolução, ausência de segunda saída e cross-tenant da requisição. Permanecem duas provas de certificação pendentes antes do 01G: cenário PostgreSQL real completo de retornável e rollback provocado durante devolução.

## 2. Arquitetura encontrada e arquivos alterados

### Backend

- `services/api/operacional/services/requisicao_posse_service.py`
  - novo serviço canônico de consumo, devolução, perda, dano e extravio;
  - validação de posse, natureza, execução, identidade, versão e idempotência;
  - entrada física de devolução.
- `services/api/operacional/services/requisicao_recebimento_service.py`
  - projeção corrigida para não somar devolução/perda/dano/extravio como consumo;
  - projeção de conciliação e execuções disponíveis.
- `services/api/operacional/schemas/estoque.py`
  - `DestinacaoRequisicaoRequest`;
  - `DestinacaoCampoAck`;
  - quantidades operacionais e status de conciliação na projeção Campo.
- `services/api/campo/router.py`
  - endpoint canônico `POST /campo/requisicoes/{req_id}/destinar`.
- `services/api/agricola/operacoes/service.py`
  - guardrail no fechamento/criação como `REALIZADA`.

Não foi criada migration 01F. O schema 01C/01D já possuía tipos de evento, `operacao_execucao_id`, vínculo evento-entrega e vínculo evento-movimento suficientes para esta fase. O Alembic continua em `20260925_material_requisition_01e` (head único).

### Campo/PWA

- `apps/campo/src/lib/requisicoes-api.ts`
  - comando offline de destinação;
  - atualização local da projeção;
  - preservação de `client_operation_id`.
- `apps/campo/src/lib/db.ts`
  - campos da operação pendente e versão Dexie 17 para compatibilidade local.
- `apps/campo/src/lib/sync/push.ts`
  - suporte a `material_disposition` usando a fila existente;
  - ACK, conflito e retry.
- `apps/campo/src/lib/sync/worker.ts` e `pull.ts`
  - recuperação e cache da nova operação/projeção.
- `apps/campo/src/components/campo/requisicoes-section.tsx`
  - exibição de posse/destinações;
  - ações de consumo, devolução, perda, dano e extravio;
  - botão de consumo não aparece para retornável.

## 3. Modelo canônico de posse

`quantidade_em_posse` não é entrada livre. A projeção deriva:

```text
em_posse = recebida - consumida - devolvida - perdida - danificada - extraviada
```

O serviço trava a requisição/item antes de calcular a posse e rejeita qualquer comando que exceda o saldo operacional. A validação ocorre contra a entrega exata (`evento_entrega_id`), não contra o primeiro evento ou primeiro produto encontrado.

## 4. Tipos de evento implementados

| Evento | Fato operacional | Movimento físico |
|---|---|---:|
| `CONSUMO` | material utilizado na execução | 0 |
| `DEVOLUCAO` | material retorna ao depósito | 1 `ENTRADA` |
| `PERDA` | consumível sob posse que deixou de estar disponível | 0 |
| `DANO` | item danificado sob custódia | 0 |
| `EXTRAVIO` | item não localizado sob custódia | 0 |

Todos os eventos possuem tenant, item, requisição, entrega de origem, quantidade, unidade, usuário, pessoa operacional, dispositivo, versão, timestamp, motivo quando aplicável e `client_operation_id`.

## 5. Consumíveis

`CONSUMIVEL` permite consumo, devolução, perda e dano quando semanticamente aplicável. O consumo exige:

- `operacao_execucao_id` explícito;
- execução no mesmo tenant;
- execução pertencente à `OperacaoAgricola` da requisição;
- execução não cancelada;
- quantidade menor ou igual à posse.

O lote da entrega é preservado como rastreabilidade operacional. O consumo não chama FIFO e não cria `EstoqueMovimento`.

## 6. Retornáveis

`RETORNAVEL` pode ser recebido, devolvido, danificado ou extraviado. Consumo é rejeitado no backend, independentemente da UI.

O fluxo pretendido é:

```text
recebido → posse temporária → devolução/dano/extravio
```

O Campo omite a ação `CONSUMO` quando a natureza do item é retornável. A regra também está coberta por teste unitário backend. A execução PostgreSQL real específica de 3 ferramentas recebidas, 2 devolvidas e 1 danificada permanece como prova complementar pendente.

## 7. Devolução física

Para devolução, o serviço:

1. autoriza o usuário operacional;
2. trava requisição/item e entrega;
3. calcula posse;
4. valida depósito de destino no tenant e na UP;
5. preserva o lote da entrega quando existente;
6. trava saldo e lote;
7. cria `RequisicaoItemEvento(DEVOLUCAO)`;
8. cria `EstoqueMovimento(ENTRADA)` com `requisicao_item_evento_id`;
9. atualiza `SaldoEstoque` e `LoteEstoque`;
10. registra Outbox;
11. confirma tudo na transação do endpoint.

O vínculo explícito e a constraint existente `tenant_id + requisicao_item_evento_id` impedem segunda entrada para o mesmo evento.

## 8. Autorização e autoria

O serviço reutiliza `IdentidadeOperacionalService` e `PessoaUsuario`.

```text
User autenticado
→ PessoaUsuario ativo no tenant
→ Pessoa operacional
→ responsável ou delegado vigente
→ comando autorizado
```

`usuario_id` identifica quem executou o comando. `pessoa_operacional_id` identifica a pessoa operacional. PIN e dispositivo não substituem a autorização backend.

## 9. Múltiplas requisições e execuções

O comando recebe simultaneamente:

- `requisicao_id`;
- `item_id`;
- `entrega_evento_id`;
- `operacao_execucao_id` para consumo.

Não há seleção por produto, primeira requisição ou primeiro lote. A execução é validada pela operação agrícola da requisição e pelo tenant.

## 10. Idempotência e concorrência

Cada comando usa `tenant_id + client_operation_id`. O retry:

- retorna o evento original;
- para devolução retorna também o movimento original;
- não cria novo evento;
- não cria nova entrada física.

A requisição é travada antes da validação da posse. O comando baseado em versão obsoleta é rejeitado. Na prova real 01F, duas sessões independentes tentaram consumir 60 sobre posse 100: um comando foi aplicado, o segundo foi rejeitado, a posse permaneceu 40 e não houve saldo físico alterado.

## 11. Campo offline

O 01F reutiliza o mecanismo certificado no 01E:

```text
Dexie → sync_queue → push → ACK/CONFLICT/ERROR → projeção canônica
```

Uma operação offline recebe sua chave no dispositivo e a mantém durante retry. `material_disposition` usa o mesmo fluxo de fila de `material_receipt`, sem mecanismo paralelo.

Foi validado em Vitest:

- operação offline de consumo;
- chave preservada;
- rota `/destinar`, não `/receber`;
- ACK aplicado;
- atualização local da posse.

Não foi alterada a política de logout/troca de usuário do 01E; a operação mantém o contexto original da fila e não é reatribuída silenciosamente.

## 12. Conciliação

Status derivado por item/entrega:

- `PENDENTE_DIVERGENCIA`: entregue ainda não coincide com recebido/recusado;
- `PENDENTE_RECUSA`: existe recusa física sem resolução posterior;
- `EM_POSSE`: existe material recebido ainda sem destino;
- `CONCILIADO`: posse zero e sem divergência/recusa pendente.

A requisição é `CONCILIADA` somente quando todos os itens entregues estão conciliados.

Para consumível:

```text
recebida = consumida + devolvida + perdida + danificada + extraviada
```

Para retornável:

```text
recebida = devolvida + danificada + extraviada
consumida = 0
```

## 13. Fechamento da operação

O ponto canônico de criação/alteração da operação como `REALIZADA` chama `validar_operacao_conciliada`. Há bloqueio quando existe requisição legada, requisição sem diário canônico, divergência de recebimento, recusa pendente ou posse diferente de zero.

O guardrail não implementa bypass administrativo. A integração econômica continua intocada e será tratada no 01G.

## 14. Estoque e ledger

Não foi criado ledger paralelo.

| Ação | `EstoqueMovimento` | Saldo/lote |
|---|---:|---:|
| Consumo | 0 | inalterado |
| Perda | 0 | inalterado |
| Dano | 0 | inalterado |
| Extravio | 0 | inalterado |
| Devolução | 1 entrada | incrementado |

A saída física continua sendo exclusivamente a `ENTREGA` do 01D.

## 15. Cenários validados

### PostgreSQL real 01F

O teste `test_requisicao_posse_01f_integration.py` passou isoladamente com:

```text
Entrega: 100
Recebimento: 100
Consumo concorrente: 60 aceito / 60 rejeitado
Posse após consumo: 40
Devolução: 40
Entrada física da devolução: 1
Retry da devolução: mesmo evento/movimento
Saídas físicas adicionais no consumo: 0
Cross-tenant da requisição: rejeitado
```

### Campo

```text
Vitest: 5 arquivos, 24 testes PASS
Typecheck: PASS
Build Campo: PASS
```

### Backend direcionado

```text
38 testes unitários direcionados: PASS
Py_compile dos arquivos alterados: PASS
git diff --check: PASS
```

### Regressão real isolada

```text
01D2: 1/1 PASS
01E: 1/1 PASS
01F: 1/1 PASS
Alembic current: 20260925_material_requisition_01e (head)
```

Uma execução conjunta das três suítes apresentou falha de conectividade/pool e fixture de identidade; as execuções isoladas, no runner PostgreSQL certificado, passaram. A falha conjunta foi registrada como instabilidade do runner, não como defeito funcional do 01F.

## 16. Migration

Nenhuma migration 01F foi criada. A decisão é intencional:

- o diário já possuía os tipos de evento;
- `evento_entrega_id` já existia;
- `operacao_execucao_id` já existia;
- `EstoqueMovimento` já possuía FK e unicidade por evento;
- natureza do item já era snapshot;
- tenant/RLS/FKs existentes foram reutilizados.

## 17. Riscos e pendências

### HIGH — certificação retornável real pendente

Ainda não foi executado no PostgreSQL real um cenário completo de ferramenta retornável com recebimento, devolução parcial e dano, embora o backend rejeite consumo de retornável e o modelo/projeção suportem os fatos.

### HIGH — rollback provocado pendente

A transação de devolução é única e o código registra evento, saldo/lote, movimento e Outbox no mesmo contexto transacional, mas não foi executado um teste de falha injetada antes do commit para comprovar o estado zero após rollback.

### MEDIUM — integração econômica

CostAllocation/DRE não foram alterados. O 01G deve consumir os fatos `CONSUMO`, `PERDA`, `DANO`, `EXTRAVIO` e `DEVOLUCAO`, sem recalcular histórico.

### MEDIUM — operação fechada

O guardrail de fechamento foi implementado e coberto estaticamente; falta uma prova E2E dedicada com operação real tentando fechar enquanto há posse.

## 18. Respostas obrigatórias

### A. Consumo gera movimento físico?

Não. Gera somente evento operacional `CONSUMO`.

### B. Devolução gera exatamente qual movimento?

Uma `EstoqueMovimento` de tipo `ENTRADA`, vinculada ao evento `DEVOLUCAO`.

### C. Como é calculada a posse?

`recebida - consumida - devolvida - perdida - danificada - extraviada`.

### D. Como impedir destinação acima da posse?

Lock da requisição/item, soma dos eventos da entrega exata, validação de quantidade e versão; concorrência é serializada pelo lock.

### E. RETORNAVEL pode ser consumido?

Não. O backend rejeita, e o Campo não apresenta a ação.

### F. Diferença entre perda, dano, extravio e consumo?

Consumo é utilização na execução; perda é indisponibilidade de consumível; dano é deterioração sob custódia; extravio é item não localizado. Nenhum deles é consumo implícito.

### G. Como consumo se vincula à execução?

`operacao_execucao_id` é obrigatório e deve pertencer à `OperacaoAgricola` da requisição, no mesmo tenant.

### H. Como diferenciar múltiplas requisições?

Pelo `requisicao_id`, `item_id` e `entrega_evento_id` explícitos; não há fallback por produto.

### I. Retry de devolução duplica entrada?

Não. O teste PostgreSQL real passou com um evento e um movimento.

### J. Concorrência pode tornar posse negativa?

Não nos cenários reais validados; uma das duas destinações concorrentes foi rejeitada.

### K. Quando um item é conciliado?

Quando a posse é zero e não há divergência, recusa ou retorno pendente.

### L. Quando a requisição é conciliada?

Quando todos os seus itens entregues estão conciliados.

### M. Operação pode fechar com material em posse?

O guardrail implementado bloqueia o fechamento normal.

### N. Há caminho legado capaz de gerar segunda baixa?

O 01D bloqueia o FIFO/legado após início canônico; o 01F não introduz baixa no consumo. A regressão 01D2 isolada passou.

### O. Quais fatos ficam disponíveis para o 01G?

Eventos por item com quantidade, lote, execução, usuário, pessoa, dispositivo, timestamp, motivo, entrega de origem, consumo, devolução, perda, dano e extravio; além do movimento físico de devolução.

## 19. Veredicto

`GO COM RESSALVAS`.

O fluxo consumível principal, a entrada física de devolução, retry, concorrência de posse, Campo offline, isolamento do comando e ausência de segunda saída foram implementados e validados. A autorização para o 01G fica retida até a certificação real dos dois cenários pendentes: retornável completo e rollback provocado.

```text
MATERIAL-REQUISITION-FLOW-01F
STATUS: GO COM RESSALVAS

CONSUMO CANÔNICO:
PASS

DEVOLUÇÃO CANÔNICA:
PASS

RETORNÁVEIS:
PASS — regra e testes unitários; cenário PostgreSQL E2E pendente

CONCILIAÇÃO:
PASS

CAMPO OFFLINE:
PASS

POSSE NUNCA NEGATIVA:
PASS

SEGUNDA BAIXA FÍSICA NO CONSUMO:
ZERO

RETRY DE DEVOLUÇÃO:
PASS

ISOLAMENTO TENANT:
PASS

AUTORIZAÇÃO PARA 01G:
NÃO

PRÓXIMA FASE:
MATERIAL-REQUISITION-FLOW-01G — Apropriação Econômica do Consumo Real
```
