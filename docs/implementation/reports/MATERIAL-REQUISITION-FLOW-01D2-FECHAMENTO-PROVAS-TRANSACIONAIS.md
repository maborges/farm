# MATERIAL-REQUISITION-FLOW-01D2 — Fechamento das Provas Transacionais

## 1. Resumo executivo

As oito provas transacionais complementares foram persistidas em uma suíte de integração e executadas contra PostgreSQL real de desenvolvimento. A rodada completa concluída passou, incluindo concorrência, retry, rollback, bloqueios legado/FIFO e isolamento tenant.

Uma repetição posterior não iniciou por timeout de conexão ao abrir sessões asyncpg. Isso foi classificado como falha ambiental de disponibilidade/conectividade, não como falha de regra de negócio. Por esse motivo, a evidência funcional é positiva, mas a autorização imediata da 01E permanece retida até uma rodada repetível em ambiente PostgreSQL estável.

## 2. Estado herdado do 01D1

O 01D1 estava em `NO-GO` somente porque as provas de concorrência complementar, atomicidade, legado e FIFO não haviam terminado. O cenário principal já havia demonstrado reserva/picking sem baixa e entrega como baixa física.

## 3. Ambiente PostgreSQL

- Banco: `farms`
- Schema: `farms`
- PostgreSQL: `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)`
- Alembic: `20260925_material_requisition_01d (head)`
- Ambiente: desenvolvimento/teste; não produção.
- Isolamento: transações PostgreSQL independentes, duas sessões para concorrência e `SELECT ... FOR UPDATE` do serviço.

## 4. Diagnóstico da instabilidade asyncpg

Foram observados três fenômenos distintos:

1. execuções sem carregar `.env.local`, causando ausência de `DATABASE_URL`;
2. execução dentro do sandbox sem permissão para abrir o socket remoto;
3. timeouts intermitentes ao abrir novas conexões asyncpg, inclusive com runner reduzido.

No banco não foram encontrados deadlocks ou sessões `idle in transaction`. O PostgreSQL reportou `max_connections=100`, com 34 sessões no momento da inspeção; as sessões observadas estavam majoritariamente `idle / ClientRead`. Um probe sequencial com pool pequeno passou, e a suíte persistente passou em rodada completa. A causa operacional mais provável é latência/instabilidade na abertura de conexões remotas combinada ao padrão de criação de múltiplas sessões do runner; não há evidência de defeito transacional causado por deadlock.

O runner persistente usa pool limitado (`pool_size=2`, `max_overflow=0`, `pool_pre_ping=False`) para evitar a interação problemática observada com `pre_ping` e pools grandes.

## 5. Testes persistidos

Suíte criada:

`services/api/tests/integration/operacional/test_requisicao_canonica_01d2_integration.py`

Execução:

```text
DEEPFARMS_RUN_REAL_01D2=1 pytest -q tests/integration/operacional/test_requisicao_canonica_01d2_integration.py
```

Resultado da rodada completa concluída:

```text
1 passed in 6.13s
```

A suíte restaura o saldo original e remove os dados `T01D2-*` ao final. A preparação fixa o saldo controlado em 100 para impedir que resíduos de uma execução anterior alterem a semântica da concorrência.

## 6. Mesma `client_operation_id` concorrente

Resultado: **PASS**.

Duas sessões enviaram a mesma entrega de 30 unidades com a mesma chave. Ambas convergiram para o mesmo par `event.id`/`movement.id`.

Evidência quantitativa:

```text
eventos ENTREGA para 01D2-SAME = 1
movimentos vinculados ao evento = 1
baixa física = 30
```

Payload incompatível com chave já usada continua rejeitado pelo contrato de idempotência.

## 7. Duas requisições concorrentes

Resultado: **PASS**.

Duas requisições distintas tentaram reservar 70 + 70 sobre saldo físico controlado de 100. A competição foi testada no limite real de reserva, antes de picking/entrega, respeitando a semântica do domínio.

```text
saldo físico antes = 100
saldo físico depois = 100
reservas vencedoras = 1
quantidade reservada vencedora = 70
resultado = 1 SUCCESS + 1 BusinessRuleError
saldo negativo = não
```

## 8. Versionamento

Resultado: **PASS**.

Uma sessão aplicou comando com `base_version=V` e elevou a versão. Outra sessão, com comando diferente baseado em `V`, recebeu `BusinessRuleError` sem efeito físico. O retry do comando original, usando a mesma chave e versão antiga, retornou o evento original por idempotência.

## 9. Atomicidade e rollback

Resultado: **PASS**.

Foi injetada falha controlada antes do commit, após a preparação do evento/movimento. Após rollback:

```text
saldo físico: inalterado
reserva.quantidade_consumida: inalterada
versão da requisição: inalterada
evento 01D2-ATOMIC: 0
movimento físico: 0
outbox: inalterada
```

Não foi deixado evento órfão, movimento órfão ou baixa parcial.

## 10. Unicidade evento ↔ movimento

Resultado: **PASS**.

Uma entrega normal produziu exatamente:

```text
RequisicaoItemEvento(ENTREGA) = 1
EstoqueMovimento(SAIDA) = 1
movimento.requisicao_item_evento_id = evento.id
```

Tentativa direta de segundo movimento para o mesmo evento foi rejeitada pela constraint de unicidade. Tentativas de `UPDATE` e `DELETE` no diário append-only também foram rejeitadas pelos triggers.

## 11. Bloqueio do fluxo legado

Resultado: **PASS**.

Após a requisição canônica estar apta ao fluxo, a chamada do serviço legado `EstoqueService.entregar_requisicao` foi rejeitada. Antes e depois da tentativa legada:

```text
movimentos legados = 0
movimentos adicionais = 0
saldo físico alterado pela tentativa legada = não
```

A entrega canônica posterior criou uma única saída.

## 12. Bloqueio FIFO

Resultado: **PASS**.

Após entrega canônica parcial de 3 unidades, o caminho operacional que poderia aplicar FIFO foi executado. O guardrail rejeitou a operação.

```text
movimentos antes do FIFO = N
movimentos depois do FIFO = N
saldo antes = saldo depois
segunda baixa FIFO = não
```

## 13. Isolamento cross-tenant

Resultado: **PASS** na rodada concluída.

Com contexto do Tenant B, a tentativa de reservar requisição/item pertencente ao Tenant A foi rejeitada como recurso inexistente ou regra de negócio. Nenhum evento, reserva ou movimento do Tenant A foi criado pelo contexto B.

As FKs tenant-safe e os testes de RLS/FK da 01C/01C1 permanecem válidos. O teste direto de depósito de B usando contexto A não foi incluído na rodada final após os timeouts; essa lacuna é coberta pelos testes tenant-safe anteriores, mas deve ser repetida no ambiente estável antes do cutover operacional.

## 14. Regressão do ledger append-only

Resultado: **PASS**.

A entrega cria o evento antes do movimento e passa `requisicao_item_evento_id` diretamente ao construtor do `EstoqueMovimento`. Não há atualização posterior do ledger para completar a relação. O trigger append-only permanece ativo após a prova.

Arquivos relevantes:

- `services/api/operacional/services/requisicao_canonica_service.py`
- `services/api/operacional/services/estoque_ledger.py`
- `services/api/operacional/models/estoque.py`

## 15. Regressão da reserva parcial

Resultado: **PASS**.

No cenário de reserva 5 e entrega 3:

```text
reserva.quantidade = 5
reserva.quantidade_consumida = 3
reserva.status = PARCIALMENTE_CONSUMIDA
quantidade restante = 2
```

O status cabe na coluna PostgreSQL `VARCHAR(32)` e não é truncado.

## 16. Cenário principal/regressão 01D1

Resultado: **PASS** em runner estabilizado.

O cenário de dois lotes e requisição retornável foi executado novamente:

```text
resultado concorrente retornável = 1 SUCCESS + 1 REJECTED/BusinessRuleError
movimentos físicos = 3
eventos operacionais = 6
```

O cenário preservou múltiplos lotes, retry e ausência de consumo para retornável.

## 17. Correções realizadas

Não foi necessária nova correção de regra de negócio durante o 01D2. As correções diretamente relacionadas ao 01D e revalidadas foram:

- associação do evento ao movimento no `INSERT`, eliminando `UPDATE` posterior no ledger append-only;
- ampliação conservadora do status da reserva para comportar `PARCIALMENTE_CONSUMIDA`.

O 01D2 adicionou somente a suíte de prova e ajustes de preparação/limpeza do runner.

## 18. Migration

Não foi criada migration no 01D2. O banco foi validado no head existente:

```text
20260925_material_requisition_01d (head)
```

Não houve alteração de histórico, backfill econômico ou mudança de dados produtivos.

## 19. Validações finais

| Validação | Resultado |
|---|---|
| Suíte 01D2 em PostgreSQL real | PASS em rodada completa; reexecuções posteriores tiveram timeout ambiental antes do setup |
| Cenário principal 01D | PASS — `movements=3`, `events=6` |
| Testes unitários 01C/01C1/01D | PASS — 18 testes |
| Registry/migration static | PASS — 6 testes |
| Alembic current | PASS — head 01D |
| App import | PASS — `APP_IMPORT_OK` em 20,9 s |
| `git diff --check` | PASS |
| Ruff `--select F` direcionado | PASS |
| Ruff completo | ressalvas de formatação/E501 preexistentes e linhas longas nos arquivos do fluxo; sem erros F |

## 20. Riscos

- A conectividade remota do PostgreSQL não é suficientemente repetível: duas reexecuções posteriores falharam ao abrir conexão, inclusive com timeout de 90 s.
- O runner deve continuar usando pool pequeno e sem `pre_ping` até a causa de infraestrutura/conectividade ser sanada.
- O bloqueio de depósito/lote cross-tenant adicional deve ser repetido na mesma rodada estável antes do cutover global.
- O 01D ainda não implementa recebimento/conferência Campo; isso permanece escopo da 01E.

## 21. Pendências

1. Repetir a suíte completa em PostgreSQL estável, incluindo a variante explícita de depósito/lote cross-tenant.
2. Não iniciar recebimento offline enquanto a repetibilidade da prova concorrente não for garantida no ambiente oficial de integração.
3. Não interpretar a aprovação 01D2 como autorização para consumo, devolução ou CostAllocation.

## 22. Prontidão para 01E

A lógica transacional 01D demonstrou reserva sem baixa, picking sem baixa, entrega como baixa única, idempotência, concorrência, rollback, bloqueio legado/FIFO e isolamento por tenant na rodada completa concluída.

Entretanto, a instabilidade de abertura de conexões PostgreSQL voltou a impedir uma reexecução final completa. Portanto, a recomendação é aguardar uma rodada estável adicional antes de liberar o recebimento Campo/offline.

## 23. Veredicto

```text
MATERIAL-REQUISITION-FLOW-01D2
STATUS: GO COM RESSALVAS

PROVAS TRANSACIONAIS COMPLEMENTARES: PASS (rodada completa concluída)
ÚNICA BAIXA FÍSICA E2E: SIM
IDEMPOTÊNCIA CONCORRENTE: PASS
BLOQUEIO LEGADO/FIFO: PASS
ISOLAMENTO TENANT: PASS
AUTORIZAÇÃO PARA 01E: NÃO
```

A autorização permanece `NÃO` exclusivamente pela falta de repetibilidade do ambiente PostgreSQL e pela necessidade de repetir a variante cross-tenant de depósito/lote em uma rodada estável; não foi identificado defeito transacional funcional nas provas concluídas.
