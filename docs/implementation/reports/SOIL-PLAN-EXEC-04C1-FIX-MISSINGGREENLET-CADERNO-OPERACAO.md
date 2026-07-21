# SOIL-PLAN-EXEC-04C1 — Correção do MissingGreenlet no Evento de Caderno da Operação

**Tipo:** Correção cirúrgica de defeito de produção. Nenhuma migration, modelo financeiro, regra econômica, FIFO ou DRE foi alterado.
**Data:** 2026-07-20

---

## 1. Causa raiz

Em `services/api/agricola/caderno/service.py:680` (antes da correção), `CadernoCampoService.garantir_evento_operacao()` acessava:
```python
if operacao.execucoes:
    for execucao in sorted(operacao.execucoes, key=lambda e: e.data_execucao):
```
`OperacaoAgricola.execucoes` é declarado como `relationship(..., lazy="selectin")` (`agricola/operacoes/models.py:66`). Esse acesso é disparado dentro de `OperacaoService.criar()` (`agricola/operacoes/service.py:1070-1073`), imediatamente após:
```python
operacao = OperacaoAgricola(tenant_id=self.tenant_id, **dados_dict)
self.session.add(operacao)
await self.session.flush()
```
— ou seja, `operacao` nunca foi obtido via uma query `select(...)`, apenas construído em memória e persistido com `flush()`.

## 2. Por que `lazy="selectin"` não protege o objeto recém-criado

A estratégia `selectin` do SQLAlchemy dispara automaticamente uma segunda consulta (`SELECT ... WHERE parent_id IN (...)`) **quando o objeto pai é carregado por uma query** — o loader se encaixa no pipeline de execução da consulta original. Quando o objeto é apenas construído e adicionado à sessão (sem nunca ter sido lido de volta do banco), não há consulta "hospedeira" para o `selectin` se acoplar; o primeiro acesso ao atributo (`operacao.execucoes`) dispara um carregamento lazy pontual e implícito. Sob `AsyncSession`, esse carregamento implícito tenta fazer I/O de rede fora do contexto de `greenlet_spawn` estabelecido pela chamada assíncrona externa, resultando em:
```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.
```
Isso só se manifesta quando `operacao.status == "REALIZADA"` (`agricola/operacoes/service.py:1070`), que é o valor **default** de `OperacaoAgricolaCreate.status` (`agricola/operacoes/schemas.py:59`) — ou seja, o caminho mais comum de uso do `criar()`, não um caso extremo.

## 3. Solução escolhida

**Opção A (query explícita)** — substituição do acesso lazy por uma consulta assíncrona explícita, usando a mesma `AsyncSession` já recebida pelo serviço (`self.session`), sem abrir nova sessão, sem `run_sync`, sem `try/except MissingGreenlet`, sem alterar a estratégia de carregamento do relacionamento (que continua `lazy="selectin"` no modelo — inalterado).

## 4. Query implementada

```python
execucoes_stmt = (
    select(OperacaoExecucao)
    .where(
        OperacaoExecucao.tenant_id == self.tenant_id,
        OperacaoExecucao.operacao_id == operacao.id,
    )
    .order_by(OperacaoExecucao.data_execucao)
)
execucoes = (await self.session.execute(execucoes_stmt)).scalars().all()
for execucao in execucoes:
    if getattr(execucao, "operador_id", None):
        executor_herdado = execucao.operador_id
        break
```
Import adicionado: `OperacaoExecucao` em `from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao` (linha 42), reaproveitando `select` já importado no topo do arquivo (`from sqlalchemy.future import select`, linha 9) — nenhum import novo de infraestrutura.

## 5. Preservação de tenant/RLS

`OperacaoExecucao.tenant_id == self.tenant_id` incluído explicitamente na cláusula `WHERE`, junto com `OperacaoExecucao.operacao_id == operacao.id` — o modelo possui `tenant_id` como coluna própria (`agricola/operacoes/models.py:81`), então a query nunca filtra apenas por `operacao_id`. Mesma `AsyncSession` recebida pelo serviço (`self.session`, herdada de `BaseService`) — nenhuma sessão nova foi aberta.

## 6. Preservação da ordenação

Semântica original: `sorted(operacao.execucoes, key=lambda e: e.data_execucao)` — ordenação ascendente por `data_execucao`. Reproduzida exatamente via `.order_by(OperacaoExecucao.data_execucao)` na query SQL (ordenação ascendente é o padrão do `ORDER BY` sem `.desc()`). O primeiro `execucao` com `operador_id` não nulo, na ordem cronológica, continua sendo o critério de escolha do `executor_herdado` — laço `for` com `break` preservado sem alteração de lógica.

## 7. Comportamento sem execuções

Quando não há `OperacaoExecucao` para a operação (caso mais comum: operação recém-criada sem execuções registradas), a query retorna lista vazia — o `for` simplesmente não itera, e `executor_herdado` permanece `operacao.operador_id` (valor padrão já existente antes do bloco). Comportamento idêntico ao `if operacao.execucoes:` avaliando como falso na versão anterior — nenhum comportamento novo foi inventado; apenas a forma de obter a coleção mudou.

## 8. Arquivos alterados

```text
services/api/agricola/caderno/service.py   (2 blocos: import na linha 42; lógica nas linhas 673-698)
docs/implementation/reports/SOIL-PLAN-EXEC-04C1-FIX-MISSINGGREENLET-CADERNO-OPERACAO.md  (novo, este relatório)
```

`services/api/tests/test_operacao_despesa_webhook.py` **não foi alterado nesta etapa** — permanece exatamente como deixado por `SOIL-PLAN-EXEC-04C0`. `services/api/tests/test_operacoes_validacao_fase.py` também não precisou de nenhuma alteração — a correção em produção foi suficiente para destravá-lo.

Diff total do arquivo de produção (confirmado via `git diff`): 19 inserções, 7 remoções, restrito exatamente aos dois pontos acima.

## 9. Testes executados

```bash
$ .venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py -q --tb=short
7 passed in 13.88s

$ .venv/bin/python -m pytest tests/test_operacoes_validacao_fase.py -q --tb=short
7 passed in 12.77s

$ .venv/bin/python -m pytest \
  tests/test_operacao_despesa_webhook.py \
  tests/test_operacoes_validacao_fase.py \
  tests/test_fifo_estoque.py \
  tests/test_dre_agricola_v1.py \
  -q
28 passed in 57.13s
```
Contagem exata confere com o esperado (7 + 7 + 6 + 8 = 28), sem divergência de parametrização/coleta.

## 10. Resultados

Todos os 28 testes do conjunto de regressão passaram. `MissingGreenlet` eliminado nos dois arquivos onde era reproduzido (`test_operacao_despesa_webhook.py`, `test_operacoes_validacao_fase.py`), sem qualquer alteração nesses arquivos de teste.

**Qualidade:**
```bash
$ .venv/bin/ruff check agricola/caderno/service.py tests/test_operacao_despesa_webhook.py tests/test_operacoes_validacao_fase.py
163 erros encontrados — todos pré-existentes no arquivo services/api/agricola/caderno/service.py
(E501 linha longa, F401 import não usado, I001 ordenação de import, E712 comparação a False),
distribuídos por todo o arquivo (2700+ linhas), nenhum nas linhas efetivamente alteradas
por esta correção (42, 673-698) — confirmado por filtro direcionado às faixas de linha tocadas,
sem resultado.
```
Conforme a instrução explícita da etapa ("não aplicar `ruff --fix` em arquivos de produção sem revisar o diff; não formatar arquivos inteiros sem necessidade"), **nenhuma correção de lint pré-existente foi aplicada** — o débito técnico do arquivo já existia antes desta etapa e está fora do escopo autorizado.

```bash
$ git diff --check
(sem saída — limpo)
```

## 11. Riscos residuais

- O restante do arquivo `agricola/caderno/service.py` mantém um volume relevante de débito de lint pré-existente (163 ocorrências) — não corrigido por estar fora do escopo desta etapa cirúrgica.
- O padrão de bug corrigido aqui (acesso a relacionamento `lazy="selectin"` em objeto recém-criado sem re-query, sob `AsyncSession`) é uma classe de problema que **pode existir em outros pontos do código-base** que também chamem `.criar()`-like em objetos recém-flushados e acessem relacionamentos lazy na mesma unit-of-work. Esta correção resolveu apenas a instância confirmada em `garantir_evento_operacao()`; uma varredura mais ampla por esse padrão não foi realizada (fora do escopo desta etapa cirúrgica).
- Nenhum teste de regressão automatizado foi adicionado especificamente para "objeto recém-criado sem re-query" como caso isolado — a cobertura existente (`test_operacao_despesa_webhook.py`, `test_operacoes_validacao_fase.py`) já exercita esse cenário via o fluxo real (`OperacaoService.criar()` → status `REALIZADA` default), o que foi considerado suficiente (seção 9 do prompt: "preferir validar por meio do fluxo real ... não remover asserções econômicas existentes").

## 12. Decisão final

A correção elimina completamente o acesso lazy implícito identificado, preserva tenant/RLS, ordenação e semântica de fallback do executor, e não introduz nenhuma mudança de comportamento econômico, financeiro ou de schema. Todos os critérios de aceite foram atendidos com evidência de execução real contra o PostgreSQL de testes.

---

## Veredicto

```text
SOIL-PLAN-EXEC-04C1
STATUS: GO
```

- Nenhum acesso lazy implícito a `operacao.execucoes` remanescente nesse fluxo: **atendido**.
- `test_operacao_despesa_webhook.py` integralmente verde: **atendido** (7/7).
- `test_operacoes_validacao_fase.py` integralmente verde: **atendido** (7/7).
- FIFO verde: **atendido** (6/6).
- DRE verde: **atendido** (8/8).
- Nenhuma migration criada: **atendido**.
- Nenhum modelo financeiro alterado: **atendido**.
- Nenhuma regra econômica alterada: **atendido**.
- `ruff` sem novas ocorrências nas linhas alteradas: **atendido**.
- `git diff --check` limpo: **atendido**.
- PostgreSQL oficial de testes usado em toda a execução: **atendido**.

## Próximo passo

Prosseguir para `SOIL-PLAN-EXEC-04C` — auditoria de consumidores reais de `Despesa(origem_tipo="OPERACAO_AGRICOLA")` fora da DRE, agora com a suíte de teste desbloqueada e executável de ponta a ponta para validar qualquer decisão sobre manter, remover, reclassificar a despesa operacional ou corrigir a consolidação de `Despesa(COMPRA)`.
