# SOIL-PLAN-EXEC-04C0 — Correção Cirúrgica da Fixture de Teste da Despesa Operacional

**Tipo:** Correção exclusiva de infraestrutura de teste. Nenhum model, service, migration, banco de dados de produção ou comportamento produtivo foi alterado.
**Data:** 2026-07-20

---

## 1. Causa exata da falha original

```text
TypeError: 'talhao_id' is an invalid keyword argument for Safra
```

A fixture de `services/api/tests/test_operacao_despesa_webhook.py` instanciava:
```python
Safra(id=..., tenant_id=..., talhao_id=talhao_id, ano_safra=..., cultura=..., status=..., area_plantada_ha=50.0)
```
usando dois campos (`talhao_id`, `area_plantada_ha`) que **não existem mais** no modelo atual de `Safra` (`agricola/safras/models.py:38-67`).

## 2. Modelo antigo presumido pela fixture

Uma `Safra` monolítica com vínculo direto a um talhão (`talhao_id`) e área plantada própria (`area_plantada_ha`) — modelo pré-migração para o domínio territorial atual.

## 3. Modelo atual confirmado

```python
class Safra(Base):
    __tablename__ = "safras"
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    ano_safra: Mapped[str]
    cultura: Mapped[str | None]   # legado, mantido só como referência textual
    status: Mapped[str]
    observacoes: Mapped[str | None]
    ...
```
(`agricola/safras/models.py:38-67`) — sem `talhao_id`, sem `area_plantada_ha`. O vínculo territorial atual segue:
```text
Unidade Produtiva → AreaRural (talhão) → ProductionUnit(safra_id, cultivo_id, area_id) → Safra
```
confirmado em `agricola/operacoes/service.py:271-291` (`_resolve_production_unit_id`, que consulta `ProductionUnit` por `safra_id` + `area_id`) e em `core/operational_context.py:183-250` (`validate_safra_area_link`, que verifica `SafraTalhao`/`CultivoArea`, mas permite safras "legadas" sem vínculo explícito).

O helper `_criar_safra` já correto, usado por outros testes já verdes (`test_dre_agricola_v1.py`), confirma o padrão:
```python
# tests/test_operational_workflow_governance_step03.py:65-75
async def _criar_safra(session, tenant_id) -> Safra:
    safra = Safra(tenant_id=tenant_id, ano_safra=..., cultura="SOJA", status="PLANEJADA")
```

## 4. Alteração realizada

Em `services/api/tests/test_operacao_despesa_webhook.py`:

1. Removidos `talhao_id=talhao_id` e `area_plantada_ha=<valor>` das 7 instanciações de `Safra(...)` — os demais campos (`id`, `tenant_id`, `ano_safra`, `cultura`, `status`) foram preservados exatamente como estavam.
2. Adicionado import reaproveitando helpers **já existentes e já corrigidos** em `tests/test_operational_workflow_governance_step03.py` (mesmo padrão já usado por `test_dre_agricola_v1.py`):
   ```python
   from test_operational_workflow_governance_step03 import (
       _criar_cultivo,
       _criar_production_unit,
       _garantir_tenant,
   )
   ```
3. Nos 5 testes cujo fluxo depende de `OperacaoService.criar()` completar com sucesso (`test_operacao_com_custo_cria_despesa_automatica`, `test_operacao_sem_custo_nao_cria_despesa`, `test_rastreabilidade_operacao_despesa`, `test_despesa_descricao_inclui_tipo_e_safra`, `test_despesa_data_operacao`), foi adicionada a criação do vínculo territorial real logo após o commit da `Safra`:
   ```python
   cultivo_id = await _criar_cultivo(session, tenant_id, safra.id)
   await _criar_production_unit(session, tenant_id, safra.id, cultivo_id, talhao_id)
   ```
   Isso é necessário porque `_resolve_production_unit_id` (produção) busca `ProductionUnit` por `safra_id`+`area_id` — sem esse vínculo, a operação persiste com `production_unit_id=NULL`, alterando o comportamento exercitado pelo teste em relação ao caminho real (produção).
4. Em `test_tenant_isolation_operacao_despesa`, adicionado `await _garantir_tenant(session, outro_tenant_id)` antes de criar a `Safra` do outro tenant — a fixture `outro_tenant_id` do `conftest.py` retorna apenas um UUID constante e nunca insere a linha correspondente em `tenants`; isso nunca havia sido exercitado porque o `TypeError` original interrompia a execução antes de chegar a esse ponto.
5. Rodado `ruff check --fix` (ferramenta de lint já configurada no projeto) — corrigiu automaticamente apenas a ordenação de imports (regra `I001`), sem alterar lógica.

**Nenhuma asserção existente foi removida, enfraquecida ou convertida em mock.** Todos os testes continuam validando via banco PostgreSQL real, através do fluxo real de `OperacaoService.criar()`.

## 5. Arquivos alterados

```text
services/api/tests/test_operacao_despesa_webhook.py   (único arquivo de produção/teste alterado)
docs/implementation/reports/SOIL-PLAN-EXEC-04C0-FIXTURE-TESTE-DESPESA-OPERACAO.md   (novo, este relatório)
```

Nenhum arquivo de suporte compartilhado (`conftest.py`, `test_operational_workflow_governance_step03.py`) foi alterado — apenas reaproveitado via import, como já fazia `test_dre_agricola_v1.py`.

## 6. Por que a alteração não muda produção

- `agricola/safras/models.py`, `agricola/operacoes/service.py`, `agricola/operacoes/schemas.py`, `core/operational_context.py`: **não tocados**.
- Nenhuma migration criada ou executada.
- A alteração apenas faz a fixture de teste refletir o domínio territorial que já existe em produção (`ProductionUnit`, `Cultivo`) — não adiciona nem restaura nenhum campo/relacionamento no lado de produção.
- `_criar_cultivo`, `_criar_production_unit`, `_garantir_tenant` já existiam, já eram usados por outro teste em produção-de-teste (`test_dre_agricola_v1.py`), e não foram modificados nesta etapa.

## 7. Achado adicional — defeito de produção genuíno e pré-existente (fora do escopo desta etapa)

Após corrigir integralmente o drift de fixture (item 4), **5 dos 7 testes ainda falham** — mas por uma causa **completamente diferente e não relacionada a fixture**:

```text
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call
await_only() here. Was IO attempted in an unexpected place?
```

Origem: `agricola/caderno/service.py:680`, dentro de `CadernoCampoService.garantir_evento_operacao()`:
```python
if operacao.execucoes:              # linha 680 — lazy-load síncrono problemático
    for execucao in sorted(operacao.execucoes, ...):
```
`OperacaoAgricola.execucoes` é declarado com `lazy="selectin"` (`agricola/operacoes/models.py:66`). Esse carregamento automático funciona quando o objeto é obtido via uma query (`select(OperacaoAgricola)...`), mas **falha** quando o objeto foi apenas construído em memória e persistido via `session.add()` + `flush()` (exatamente o que `OperacaoService.criar()` faz, `agricola/operacoes/service.py:886-891`) e, em seguida, `.execucoes` é acessado na mesma requisição — o acesso tardio ao atributo lazy dispara uma tentativa de I/O fora do contexto de greenlet assíncrono esperado pelo SQLAlchemy.

Esse gatilho só ocorre quando `operacao.status == "REALIZADA"` (`agricola/operacoes/service.py:1070`), que é justamente o valor **default** de `OperacaoAgricolaCreate.status` (`agricola/operacoes/schemas.py:59`, `Field(default="REALIZADA", ...)`) — ou seja, é o caminho **normal e mais comum** de uso do `criar()`, não um caso extremo.

**Confirmação de que é pré-existente e independente desta etapa:** o mesmo erro, na mesma linha, foi reproduzido rodando um arquivo de teste totalmente diferente e **não tocado nesta sessão**:
```bash
$ .venv/bin/python -m pytest tests/test_operacoes_validacao_fase.py -q
3 failed, 4 passed
FAILED test_operacao_colheita_em_fase_colheita_deve_suceder — MissingGreenlet (mesma linha)
FAILED test_operacao_snapshot_fase_safra — MissingGreenlet (mesma linha)
FAILED test_operacao_lookup_table_multiplas_fases — MissingGreenlet (mesma linha)
```
Isso prova que o defeito já existe no código de produção **antes** de qualquer alteração desta etapa, e não é causado pela fixture corrigida aqui.

**Conforme a instrução da etapa** ("classificar cada falha; separar drift de fixture de defeito de produção; corrigir somente drift da fixture; não alterar produção sem nova autorização"), **este defeito não foi corrigido**. `agricola/caderno/service.py` não foi tocado.

## 8. Testes executados

```bash
$ .venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py -q --tb=short
# Antes da correção de fixture: 7 failed (TypeError em todos, coleta falhava na fixture)
# Após remover talhao_id/area_plantada_ha (sem vínculo territorial): 6 failed, 1 passed
# Após adicionar Cultivo/ProductionUnit + tenant do outro_tenant_id: 5 failed, 2 passed

$ .venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_fifo_estoque.py tests/test_dre_agricola_v1.py -q
5 failed, 16 passed
  (2 do arquivo-alvo passam; 6/6 FIFO passam; 8/8 DRE passam; 5 falhas = defeito de produção confirmado independentemente, seção 7)

$ git diff --check
(sem saída — limpo)

$ .venv/bin/ruff check tests/test_operacao_despesa_webhook.py
All checks passed! (após --fix aplicado apenas para ordenação de imports)
```

## 9. Falhas preexistentes encontradas (fora do escopo de correção desta etapa)

1. **`MissingGreenlet` em `agricola/caderno/service.py:680`** — defeito de produção genuíno, confirmado independentemente em `test_operacoes_validacao_fase.py` (arquivo não tocado). Afeta qualquer chamada a `OperacaoService.criar()` que resulte em `status="REALIZADA"` (o caminho default do schema). Impacta diretamente os 5 testes de `test_operacao_despesa_webhook.py` que validam o fluxo completo de criação de operação com despesa automática.
2. As falhas de metadata SQLAlchemy em `test_compras_lote_integration.py`, `test_launch_core01_operational_cost_engine.py` e o drift original de `test_operacao_despesa_webhook.py`, já classificadas na auditoria `SOIL-PLAN-EXEC-04B`, permanecem fora do escopo desta etapa (conforme instrução explícita de não incluí-las).

## 10. Conclusão

**O drift de fixture foi integralmente corrigido** — nenhuma instanciação de `Safra` no arquivo usa mais `talhao_id`/`area_plantada_ha`; a fixture agora reflete corretamente o domínio territorial atual (`Unidade Produtiva → AreaRural → ProductionUnit → Safra`), reaproveitando helpers já existentes e validados por outro teste (`_criar_cultivo`, `_criar_production_unit`, `_garantir_tenant`). As asserções econômicas originais (criação/ausência de `Despesa`, `origem_tipo`, `valor_total`, `status="PAGO"`, datas, isolamento de tenant, rastreabilidade) foram preservadas sem enfraquecimento.

**Resposta à pergunta da seção 1:** *Não* — o teste não passa integralmente contra o modelo e o serviço atuais, mas **não por causa de drift de fixture** (esse problema está resolvido). A causa remanescente é um defeito de produção genuíno e independente (`MissingGreenlet` em `agricola/caderno/service.py:680`), confirmado por reprodução em outro arquivo de teste não relacionado. Corrigi-lo exigiria alterar código de produção, o que está fora do escopo autorizado desta etapa.

---

## Veredicto

```text
SOIL-PLAN-EXEC-04C0
STATUS: PARCIAL — drift de fixture corrigido; teste bloqueado por defeito de
produção pré-existente e não relacionado, fora do escopo autorizado desta etapa.
```

- `Safra(..., talhao_id=...)` não permanece na fixture: **atendido**.
- Nenhum model de produção alterado: **atendido**.
- Nenhuma migration criada: **atendido**.
- Asserções econômicas preservadas: **atendido**.
- `test_operacao_despesa_webhook.py` passar integralmente: **não atendido** — 2/7 passam; 5/7 bloqueados por `MissingGreenlet` em `agricola/caderno/service.py:680` (defeito de produção pré-existente, confirmado independentemente).
- FIFO continua verde: **atendido** (6/6).
- DRE continua verde: **atendido** (8/8).
- `git diff --check` limpo: **atendido**.
- PostgreSQL como banco oficial da execução: **atendido**.
- Relatório criado: **atendido**.

## Próxima etapa recomendada

Não prosseguir automaticamente para `SOIL-PLAN-EXEC-04C` sem antes decidir, com nova autorização explícita, se o defeito `MissingGreenlet` em `agricola/caderno/service.py:680` deve ser corrigido (fora do escopo desta etapa) antes ou em paralelo à auditoria de consumidores da `Despesa(origem_tipo="OPERACAO_AGRICOLA")` — sem essa correção, qualquer novo teste de integração que exercite `OperacaoService.criar()` com status `REALIZADA` (o caminho default) continuará falhando por esse motivo, independentemente da qualidade da fixture.
