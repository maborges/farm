# MATERIAL-REQUISITION-FLOW-01D1 — Validação Transacional E2E

**Data:** 2026-09-25  
**Escopo:** validação do 01D em PostgreSQL real de desenvolvimento.  
**Ambiente:** não produção; database `farms`, schema `farms`, PostgreSQL 16.15, usuário sem bypass de RLS.

## 1. Resumo executivo

A prova principal de reserva, picking, múltiplos lotes, entrega parcial por
lote, retry e concorrência de saldo foi executada em PostgreSQL real e passou.

Durante a execução foram encontrados e corrigidos dois defeitos diretamente do
01D:

1. o movimento era inserido e depois atualizado para apontar ao evento; o
   trigger append-only do ledger rejeitou essa atualização;
2. `PARCIALMENTE_CONSUMIDA` excedia o `VARCHAR(20)` de `ReservaEstoque.status`.

A entrega agora cria o evento antes e insere o movimento já vinculado, na mesma
transação; o status da reserva foi ampliado para `VARCHAR(32)`.

Os cenários complementares obrigatórios — mesma chave concorrente, duas
requisições concorrentes, atomicidade provocada, bloqueio legado/FIFO,
append-only direto e isolamento tenant no mesmo ciclo — não foram concluídos em
uma execução íntegra porque a conexão asyncpg voltou a falhar durante a prova.
Consequentemente, não há autorização para 01E.

## 2. Ambiente

| Item | Evidência |
|---|---|
| PostgreSQL | 16.15 Ubuntu |
| Database/schema | `farms` / `farms` |
| Produção | Não; conexão de desenvolvimento/teste |
| Alembic head | `20260925_material_requisition_01d` |
| ORM | SQLAlchemy Async + asyncpg |
| Isolamento | transações PostgreSQL reais; concorrência com duas sessões no cenário principal |

`alembic current` foi executado e retornou o head acima.

## 3. Alembic head

O ciclo de migration foi executado novamente após a correção do tamanho do
status:

```text
20260925_material_requisition_01d
→ downgrade
20260925_material_requisition_01c1
→ upgrade
20260925_material_requisition_01d (head)
```

Resultado: PASS.

Inspeção final no banco:

- `estoque_reservas.status`: `character varying(32)`;
- `quantidade_consumida`: presente;
- `client_operation_id`: `varchar(120)`;
- triggers append-only de movimento e evento: habilitados;
- grupos duplicados `(tenant_id, requisicao_item_evento_id)`: `0`.

## 4. Dados de teste

Foram criados registros temporários com prefixo `T01D-`, usando tenant,
usuário, unidade produtiva, produto, depósito, saldo e lotes existentes apenas
como contexto controlado. O saldo foi incrementado artificialmente dentro do
cenário e restaurado na limpeza.

Não foram usados dados históricos como evidência de requisição. A limpeza foi
confirmada; não restaram requisições com prefixo `T01D-` ou `T01D1-`.

## 5. Reserva

No cenário principal:

```text
Requisição 1: aprovado 100 kg, reservado 100 kg
Requisição 2: aprovado 60 kg, reservado 60 kg
```

Após a reserva, o fluxo não gerou `EstoqueMovimento` de saída. O saldo físico
permaneceu inalterado pela reserva. A implementação usa
`SaldoEstoque.quantidade_reservada` e `ReservaEstoque.quantidade_consumida`;
esta última permaneceu zero antes das entregas.

## 6. Picking

Foram registrados os fatos:

```text
Lote L1: separação 60 kg
Lote L2: separação 40 kg
```

O picking gerou eventos `SEPARACAO` e nenhum movimento físico. O saldo dos
lotes não foi baixado durante a separação.

Evidência de implementação: `RequisicaoCanonicaService.separar_item` e o
endpoint canônico em
`services/api/operacional/routers/estoque.py`.

## 7. Entrega L1

```text
Entrega L1: 60 kg
Eventos ENTREGA: 1
Movimentos SAIDA: 1
Reserva consumida: 60 kg
Reserva restante: 40 kg
```

O movimento foi criado com `requisicao_item_evento_id` no próprio `INSERT`.
Essa ordem foi necessária porque o ledger possui trigger append-only.

## 8. Retry L1/L2

O script principal repetiu exatamente a segunda entrega (`L2 = 40 kg`) com a
mesma chave. O resultado foi o mesmo evento/movimento, sem segunda baixa.

Resultado final do cenário principal:

```text
eventos relacionados: 6
movimentos físicos relacionados: 3
```

Os seis eventos são quatro da requisição principal (duas separações e duas
entregas) e dois da segunda requisição concorrente (uma separação e uma
entrega). Os três movimentos são duas entregas da principal e uma entrega da
segunda requisição.

O retry concorrente da mesma `client_operation_id` não foi aprovado nesta fase,
pois o ciclo complementar não conseguiu completar por indisponibilidade do
PostgreSQL.

## 9. Entrega L2

```text
Lote L2: 40 kg
Saída física acumulada da requisição principal: 100 kg
Reserva consumida acumulada: 100 kg
Reserva restante: 0 kg
Status da reserva: CONSUMIDA
```

O cenário principal fechou com dois lotes rastreáveis e dois movimentos de
saída, não três ou quatro.

## 10. Parcialidade

O teste complementar foi preparado para:

```text
aprovado 20 L
separado 18 L
entregue 18 L
```

mas a execução integral não terminou por indisponibilidade de conexão antes da
conclusão dos asserts. Portanto, o comportamento parcial permanece sustentado
por testes unitários/código do 01D, mas não recebe PASS transacional nesta
rodada.

## 11. Concorrência de saldo

O cenário principal abriu duas sessões reais e tentou entregar 60 kg na mesma
requisição, com chaves diferentes:

```text
resultado: SUCCESS / REJECTED (BusinessRuleError)
movimentos físicos do cenário concorrente: 1
saldo negativo: não observado
```

Isso prova a concorrência de duas entregas sobre a mesma disponibilidade. A
prova específica de duas requisições distintas competindo pelo mesmo saldo não
foi concluída no ciclo complementar.

## 12. Concorrência de idempotência

Não foi possível declarar PASS para duas conexões enviando simultaneamente a
mesma `client_operation_id`. O runner complementar sofreu timeout asyncpg
antes de produzir o resumo verificável.

A proteção estrutural permanece presente:

- `UNIQUE (tenant_id, client_operation_id)` no evento/reserva;
- segunda leitura da chave após lock do agregado;
- `UNIQUE (tenant_id, requisicao_item_evento_id)` no movimento.

Isso é evidência de implementação, não substitui a prova transacional exigida.

## 13. Concorrência entre requisições

Não validada integralmente em PostgreSQL nesta rodada. O cenário principal
validou concorrência entre comandos sobre a mesma requisição; o caso de duas
requisições diferentes pelo mesmo saldo ficou pendente devido à instabilidade
da conexão.

## 14. Versionamento

O teste complementar de versão foi preparado para:

```text
base_version = V
primeiro comando → V+1
comando diferente baseado em V → conflito
retry da chave original com V antigo → ACK original
```

A execução não completou os asserts finais por indisponibilidade asyncpg. O
teste unitário 01D continua PASS para versão obsoleta, mas não é apresentado
como prova E2E.

## 15. Atomicidade

O desenho transacional foi corrigido para que evento, movimento, saldo, lote,
reserva, versão e Outbox permaneçam na mesma transação. A falha encontrada no
primeiro teste real confirmou que o trigger append-only impede o padrão de
“inserir e depois atualizar” o movimento.

O teste de falha provocada após a preparação do movimento não concluiu por
indisponibilidade da sessão complementar. Assim, a atomicidade E2E provocada
fica pendente, apesar da ordem transacional corrigida no código.

## 16. Evento ↔ movimento

Evidência real do cenário principal:

```text
RequisicaoItemEvento(ENTREGA) → EstoqueMovimento(SAIDA)
```

O vínculo é criado no insert em
`services/api/operacional/services/requisicao_canonica_service.py:385-400`.
O ledger recebe o parâmetro em
`services/api/operacional/services/estoque_ledger.py:99-121`.

Inspeção posterior encontrou zero grupos duplicados por evento. A tentativa
direta de violar a unicidade no ciclo complementar não concluiu como teste
isolado por causa da falha de conexão.

## 17. Bloqueio legado

O serviço legado contém guardrail para rejeitar uma requisição que já iniciou o
fluxo canônico, e a rota canônica não chama `registrar_saida()`.

A prova transacional do bloqueio legado no ciclo complementar não foi concluída.
O status é, portanto, **não validado E2E nesta rodada**, não PASS.

## 18. Bloqueio FIFO

`OperacaoService._aplicar_insumos_na_operacao` contém bloqueio quando encontra
entrega canônica parcial, evitando uma baixa FIFO adicional.

O teste com operação real estava preparado, mas não concluiu por instabilidade
da conexão. A prova FIFO permanece pendente e impede autorizar 01E.

## 19. Tenant isolation

O isolamento estrutural das novas tabelas e FKs foi validado no 01C1 em
PostgreSQL real. O novo ciclo 01D1 não concluiu a prova cruzada adicional do
serviço canônico por causa da indisponibilidade do banco.

Não há evidência de alteração cross-tenant produzida pelo cenário principal.
As consultas canônicas continuam filtrando `tenant_id`; depósitos e lotes são
validados pelo contexto do tenant.

## 20. Retornável

A segunda requisição do cenário principal foi criada com
`natureza_item=RETORNAVEL` e percorreu reserva, separação e entrega física.
Não foi criado evento de consumo nem devolução. Isso confirma, no escopo 01D,
que retornável compartilha a saída física sem ser tratado como consumível.

## 21. Correções realizadas

Somente correções diretamente reveladas pela validação 01D foram aplicadas:

- `estoque_ledger.registrar_ledger_estoque` aceita
  `requisicao_item_evento_id` na criação do movimento;
- a entrega cria e faz flush do evento antes de inserir o movimento;
- `ReservaEstoque.status` foi ampliado para 32 caracteres;
- migration 01D altera e reverte esse tamanho no ciclo incremental.

Não foram implementados Campo, Dexie, recebimento, consumo, devolução,
CostAllocation ou DRE.

## 22. Testes

| Validação | Resultado |
|---|---|
| Cenário principal em PostgreSQL real | PASS |
| Retry da segunda entrega | PASS |
| Concorrência de duas entregas no mesmo item | PASS: SUCCESS/REJECTED |
| Migration downgrade → upgrade | PASS |
| Head Alembic | PASS |
| Inspeção de triggers/colunas | PASS |
| Grupos duplicados evento↔movimento | PASS: 0 |
| Unitários 01C/01C1/01D | PASS: 18 passed |
| Import da aplicação | PASS: `APP_IMPORT_OK` |
| `py_compile` | PASS |
| `git diff --check` | PASS |
| Mesma chave concorrente | NÃO VALIDADO |
| Duas requisições concorrentes | NÃO VALIDADO |
| Atomicidade provocada | NÃO VALIDADO |
| Bloqueio legado E2E | NÃO VALIDADO |
| Bloqueio FIFO E2E | NÃO VALIDADO |
| Tenant isolation adicional 01D1 | NÃO VALIDADO |

Falhas de conexão asyncpg e timeouts foram classificadas como `AMBIENTE`, mas
impedem transformar os casos acima em PASS.

## 23. Regressões

As duas falhas encontradas na primeira execução foram regressões funcionais
introduzidas pelo 01D e foram corrigidas antes da prova principal final:

1. `UPDATE` proibido pelo append-only do ledger;
2. truncamento do status de reserva parcial.

Após as correções, os testes unitários direcionados passaram e o cenário
principal foi repetido com sucesso. Não foi observado dado temporário residual.

## 24. Riscos

- a concorrência da mesma idempotency key ainda não tem prova real concluída;
- a competição entre requisições distintas ainda não tem prova real concluída;
- atomicidade provocada e bloqueio FIFO/legado não foram fechados em PostgreSQL;
- a conexão asyncpg permanece instável e pode mascarar falhas adicionais;
- o fluxo legado ainda existe para requisições que não iniciaram o caminho
  canônico, por decisão de compatibilidade do 01D.

## 25. Pendências

Reexecutar em runner PostgreSQL estável, preferencialmente com teste de
integração persistido no repositório, os cenários:

1. mesma chave concorrente;
2. duas requisições distintas pelo mesmo saldo;
3. versão obsoleta e retry em sessões separadas;
4. rollback após falha provocada;
5. unicidade direta evento↔movimento;
6. bloqueio legado;
7. bloqueio FIFO após entrega parcial;
8. isolamento cross-tenant do comando canônico.

Até isso, 01E não deve iniciar.

## 26. Veredicto

### Perguntas obrigatórias

**A. A reserva altera saldo físico?**  
Não. Ela altera disponibilidade/reserva, não o saldo físico.

**B. O picking altera saldo físico?**  
Não. O cenário real registrou separações sem movimentos físicos.

**C. A entrega é realmente o único ponto de saída?**  
Sim no cenário principal validado: a entrega criou as únicas `SAIDA` físicas.
As demais rotas concorrentes/legadas não foram todas fechadas por prova E2E
nesta rodada.

**D. Retry produz segunda saída?**  
Não no retry repetido da segunda entrega validada; o mesmo evento/movimento foi
reutilizado.

**E. Duas entregas concorrentes conseguem exceder o saldo?**  
Não no cenário real executado: uma venceu e uma foi rejeitada.

**F. Duas requisições concorrentes conseguem exceder o saldo?**  
Não foi possível concluir essa prova específica nesta rodada.

**G. A mesma idempotency key concorrente produz mais de um evento/movimento?**  
Não foi possível concluir a prova concorrente; não declarar PASS.

**H. É possível existir evento ENTREGA sem movimento correspondente após commit?**  
O retry real encontrou o movimento associado e não houve evento órfão no
cenário principal. A prova de falha provocada/rollback ainda não foi concluída.

**I. É possível existir movimento canônico sem evento correspondente?**  
O movimento agora nasce com a FK do evento; o primeiro teste demonstrou que a
tentativa de corrigir a associação por `UPDATE` é rejeitada pelo ledger. A prova
de rollback completo permanece pendente.

**J. A rota legada consegue baixar novamente uma requisição que iniciou o fluxo
canônico?**  
Há guardrail implementado no serviço, mas o teste E2E correspondente não foi
concluído nesta rodada.

**K. O FIFO operacional consegue realizar segunda baixa depois de entrega
canônica parcial?**  
Há guardrail implementado no serviço, mas a prova com operação real não foi
concluída.

**L. Existe BLOCKING/HIGH restante especificamente no 01D?**  
Sim: faltam as provas transacionais complementares obrigatórias em PostgreSQL
estável. Isso é BLOCKING para autorizar 01E, não uma autorização para cutover.

## 27. Resultado final

```text
MATERIAL-REQUISITION-FLOW-01D1
STATUS: NO-GO

PROVA E2E TRANSACIONAL:
FAIL

ÚNICA BAIXA FÍSICA COMPROVADA EM POSTGRESQL:
SIM — no cenário principal; validação complementar ainda pendente

AUTORIZAÇÃO PARA 01E:
NÃO

PRÓXIMA FASE:
MATERIAL-REQUISITION-FLOW-01E — Campo Offline, Recebimento e Segurança,
somente após concluir as provas complementares em PostgreSQL estável
```
