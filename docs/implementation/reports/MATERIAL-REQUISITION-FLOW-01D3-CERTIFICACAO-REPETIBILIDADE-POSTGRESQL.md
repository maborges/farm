# MATERIAL-REQUISITION-FLOW-01D3 — Certificação de Repetibilidade PostgreSQL

## 1. Resumo

O 01D3 certificou a repetibilidade da suíte transacional do fluxo 01D em PostgreSQL real de desenvolvimento.

```text
3/3 rodadas completas PASS
cross-tenant depósito PASS
cross-tenant lote PASS
cleanup PASS
```

O runner foi estabilizado sem alterar produção ou regras de negócio. A alteração foi restrita ao teste de integração: pool limitado, SSL explícito para o banco de desenvolvimento e pré-aquecimento sequencial das duas conexões necessárias para os cenários concorrentes.

## 2. Diagnóstico da conectividade

| Camada | Resultado |
|---|---|
| Configuração | `.env.local` precisava ser carregado/exportado; sem isso `DATABASE_URL` não existia |
| Sandbox | o sandbox bloqueava o socket remoto; a validação real foi executada com acesso de rede autorizado |
| Rede/aceitação de conexão | duas novas conexões asyncpg abertas simultaneamente apresentavam timeout intermitente |
| Pool/runner | a criação concorrente de conexões amplificava a falha; pré-aquecimento sequencial resolveu nas três rodadas |
| Aplicação | sem evidência de vazamento ou transação abandonada do runner após a estabilização |
| Banco/locks | PostgreSQL respondeu; não havia lock não concedido nem sessão `idle in transaction` após as rodadas |

Probe direto: cinco conexões sequenciais passaram; duas conexões simultâneas sem pré-aquecimento apresentaram falha intermitente; duas conexões pré-aquecidas sequencialmente passaram. Não foi reproduzida falha de regra de negócio, lock ou deadlock durante a suíte.

O contador cumulativo `pg_stat_database.deadlocks` estava em `5` na inspeção final. Como não havia baseline antes das rodadas, não é possível atribuir esse contador ao 01D3. Não houve lock não concedido, espera ativa ou falha transacional atribuível a deadlock durante a certificação.

## 3. Configuração do runner

Arquivo persistente:

`services/api/tests/integration/operacional/test_requisicao_canonica_01d2_integration.py`

Configuração exclusiva de teste:

```python
pool_size=2
max_overflow=0
pool_pre_ping=False
connect_args={"timeout": 30, "ssl": False, "server_settings": {"search_path": "farms"}}
```

Antes do primeiro uso, o runner abre duas conexões sequencialmente, executa `select 1`, fecha ambas e só então inicia os casos. Cada sessão é fechada por context manager; `engine.dispose()` ocorre no `finally`; rollback e limpeza são determinísticos.

Essa configuração não deve ser copiada para produção sem decisão específica de infraestrutura e segurança.

## 4. PostgreSQL utilizado

- PostgreSQL `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)`;
- database `farms`, schema `farms`;
- host de desenvolvimento `192.168.0.2:5432`;
- Alembic `20260925_material_requisition_01d (head)`;
- ambiente de desenvolvimento/teste, não produção;
- SQLAlchemy Async + asyncpg.

## 5. Rodadas completas

| Rodada | Resultado | Duração | Cross-tenant | Cleanup |
|---|---|---:|---|---|
| 1 | PASS — 1 passed | 7.96s | PASS | PASS |
| 2 | PASS — 1 passed | 6.11s | PASS | PASS |
| 3 | PASS — 1 passed | 7.30s | PASS | PASS |

Critério de repetibilidade: `3/3 PASS`. Não foi usado retry automático para converter falha em rodada aprovada.

## 6. Cross-tenant — depósito

O fixture criou temporariamente, no Tenant B, unidade produtiva existente, depósito B, saldo B e lote B. Com contexto do Tenant A, tentou:

1. reservar item A usando depósito B;
2. separar item A usando lote B;
3. entregar item A usando lote B.

Todos os comandos foram rejeitados por `EntityNotFoundError`, `BusinessRuleError` ou `TenantViolationError`, conforme o ponto de validação.

```text
saldo A alterado = não
saldo B alterado = não
reserva B alterada = não
eventos B criados = não
movimentos B criados = não
```

## 7. Cross-tenant — lote

O lote B temporário foi criado com quantidade `1`. O Tenant A não conseguiu utilizá-lo no picking nem na entrega:

```text
quantidade lote B antes = 1
quantidade lote B depois = 1
saída física = 0
evento operacional cross-tenant = 0
```

O depósito, saldo e lote B foram removidos pelo cleanup.

## 8. Provas executadas em cada rodada

Cada rodada executou integralmente:

- mesma `client_operation_id` concorrente;
- duas requisições competindo no limite de reserva;
- versionamento obsoleto e retry idempotente;
- rollback provocado;
- unicidade evento↔movimento;
- append-only de evento;
- bloqueio legado;
- bloqueio FIFO após entrega parcial;
- isolamento cross-tenant;
- reserva parcial;
- cenário principal/regressão 01D.

Métricas preservadas pela suíte:

```text
saldo de competição = 100
reservas vencedoras = 1 × 70
resultado competição = 1 SUCCESS + 1 BusinessRuleError
mesma chave concorrente = 1 evento + 1 movimento
rollback provocado = 0 evento, 0 movimento, saldo/versão/reserva inalterados
reserva parcial = 5 reservados, 3 consumidos, PARCIALMENTE_CONSUMIDA
```

## 9. Estado do PostgreSQL após as rodadas

Consulta final direta:

```text
idle_in_transaction = 0
active_waiting = 0
test_requests (T01D*) = 0
test_depots (T01D3-*) = 0
test_lots (T01D3-*) = 0
ungranted_locks = 0
```

Saldos originais foram restaurados.

## 10. Regressões e migration

Nenhum defeito funcional novo do 01D foi descoberto. Permaneceram válidas as correções anteriores: evento/movimento vinculados no `INSERT`, ledger append-only, status parcial sem truncamento, reserva/picking sem baixa, entrega como única saída e bloqueios legado/FIFO.

Não foi criada migration no 01D3. O head permaneceu `20260925_material_requisition_01d`.

## 11. Testes finais

| Validação | Resultado |
|---|---|
| 01D3 / integração real | PASS — 3/3 rodadas |
| 01D2 persistente | PASS em todas as rodadas |
| Unitários 01C/01C1/01D | PASS — 24 testes direcionados |
| Registry/migration static | PASS incluído nos 24 testes |
| Alembic current | PASS — `20260925_material_requisition_01d (head)` |
| App import | PASS — `APP_IMPORT_OK` |
| `git diff --check` | PASS |
| Ruff `--select F` direcionado | PASS |
| `py_compile` | PASS |

## 12. Riscos e pendências

- A conectividade remota apresentou latência intermitente para abertura concorrente de conexões; o runner pré-aquecido foi repetível nas três rodadas.
- `ssl=False` é exclusivo do runner de desenvolvimento e não é recomendação para produção.
- Recebimento Campo/offline, consumo, devolução e integração econômica continuam fora do escopo 01D3.
- O contador histórico de deadlocks do banco não foi atribuído ao teste por falta de baseline anterior.

Não há pendência transacional BLOCKING/HIGH no fluxo 01D após as três rodadas.

## 13. Perguntas obrigatórias

### A. A instabilidade estava no banco, rede, sandbox, pool, runner ou aplicação?

Houve combinação de carregamento/exportação de `.env.local`, bloqueio de socket pelo sandbox e aceitação intermitente de múltiplas conexões novas asyncpg. Pool/runner amplificava o problema; não foi reproduzida falha funcional da aplicação.

### B. A suíte PostgreSQL completou três execuções consecutivas?

Sim: `3/3 PASS`.

### C. Alguma execução deixou sessão `idle in transaction`?

Não. Consulta final: `0`.

### D. Alguma execução deixou dados temporários?

Não. Requisições `T01D*`, depósitos `T01D3-*` e lotes `T01D3-*`: `0`.

### E. Tenant A consegue utilizar depósito B?

Não. Reserva A com depósito B foi rejeitada e saldo/reserva permaneceram inalterados.

### F. Tenant A consegue utilizar lote B?

Não. Picking e entrega A com lote B foram rejeitados; lote B permaneceu com quantidade `1` e não houve saída.

### G. Algum defeito funcional do 01D foi descoberto?

Não no 01D3. As correções anteriores do ledger append-only e do status parcial permaneceram válidas.

### H. Existe alguma razão funcional/transacional para impedir o 01E?

Não.

### I. O ambiente de integração está suficientemente repetível para desenvolver e validar o 01E?

Sim, usando o runner pré-aquecido e mantendo falhas de infraestrutura separadas das falhas de negócio.

## 14. Resultado final

```text
MATERIAL-REQUISITION-FLOW-01D3
STATUS: GO

REPETIBILIDADE POSTGRESQL:
PASS

RODADAS COMPLETAS:
3/3 PASS

CROSS-TENANT DEPÓSITO:
PASS

CROSS-TENANT LOTE:
PASS

FLUXO 01D TRANSACIONALMENTE ENCERRADO:
SIM

AUTORIZAÇÃO PARA 01E:
SIM

PRÓXIMA FASE:
MATERIAL-REQUISITION-FLOW-01E — Campo Offline, Recebimento e Segurança
```
