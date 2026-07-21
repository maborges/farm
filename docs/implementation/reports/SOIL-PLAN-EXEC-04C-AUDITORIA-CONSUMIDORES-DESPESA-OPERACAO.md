# SOIL-PLAN-EXEC-04C — Auditoria de Consumidores da Despesa de Operação Agrícola

**Tipo:** Auditoria arquitetural e funcional, somente leitura. Nenhum código de produção, teste, migration ou modelo financeiro foi alterado.
**Data:** 2026-07-20

---

## 1. Resumo executivo

Existem **3 consumidores reais** de `Despesa(origem_tipo="OPERACAO_AGRICOLA")` além da DRE agrícola (que já a exclui corretamente via `CostAllocation`):

1. **`agricola/dashboard/service.py`** (`resumo_financeiro_safra`) — usa o `valor_total` somado dessa Despesa para calcular ROI/margem de uma safra, com uma deduplicação manual e frágil (`min(custo_operacoes, despesa_total)`), e expõe ambos os números (`custo_operacoes_total` e `despesa_total`) na tela.
2. **`agricola/tarefas/service.py`** (`_avaliar_exclusao_tarefa`) — bloqueia a exclusão de uma tarefa se existir Despesa ativa vinculada à operação derivada. **Porém este bloqueio já é redundante**: a mesma função bloqueia pela existência de `CostAllocation` equivalente, algumas linhas acima, produzindo o mesmo resultado (`blockers.append("financeiro")`) independentemente da Despesa existir.
3. **`agricola/alertas/service.py`** (`_detectar_allocation_sem_reflexo_economico`) — usa a **ausência** da Despesa (não sua presença) como sinal de auditoria/governança, detectando `CostAllocation` órfãos sem despesa reflexa.

Nenhum consumidor real foi encontrado em: frontend Web (tela genérica de despesas mistura tudo sem distinção), Campo PWA (nenhuma referência), webhooks HTTP reais (não existem — "webhook" é só o nome do teste/conceito interno), ou integração ERP (associação inbound genérica por NF/valor/vencimento, sem relação confirmada com despesas de operação, que não carregam número de NF).

O gap mais grave confirmado nesta etapa: **nenhum consumidor, nem o próprio fluxo de cancelamento, trata a Despesa quando a operação é revertida** — ela permanece `ativo=True`/`status=PAGO` indefinidamente, distorcendo o dashboard de margem (consumidor 1) mesmo após a reversão do estoque.

**Veredicto: DIREÇÃO RECOMENDADA — E** (separar compra financeira de custo agrícola: `CostAllocation` como fonte exclusiva do custo aplicado; neutralizar/eliminar o efeito financeiro de `Despesa(OPERACAO_AGRICOLA)`), com a ressalva de que o consumidor 1 (dashboard de margem) precisa ser migrado para consumir `CostAllocation`/`custo_total` diretamente antes de qualquer remoção — não pode ser feito de forma abrupta.

---

## 2. Mapa de escrita (criação/atualização/cancelamento)

| Ponto | Arquivo:linha | Ação | Status gravado |
|---|---|---|---|
| Criação inicial | `agricola/operacoes/service.py:1023-1054` (dentro de `criar()`) | Cria `Despesa` se `custo_total_operacao > 0` e `status == "REALIZADA"` | `"PAGO"` |
| Idempotência de criação | `agricola/operacoes/service.py:305-314` (`_buscar_despesa_existente`) | Usada apenas dentro de `_sincronizar_efeitos_operacao` (caminho de `atualizar()`), não no `criar()` | — |
| Atualização | `agricola/operacoes/service.py:479+` (`_sincronizar_efeitos_operacao`, chamada por `atualizar()`) | Reatualiza valor da Despesa existente ao reprocessar operação | mantém/atualiza |
| Cancelamento/estorno | **Não encontrado** — `_reverter_movimentos_estoque_operacao` (linhas 425-478) só reverte `LoteEstoque`/`EstoqueMovimento`. Nenhuma referência a `Despesa` ou `status="CANCELADO"`/`ativo=False` nesse trecho | — |
| Exclusão/soft-delete | **Não encontrado** — nenhum escritor de `Despesa.ativo = False` associado a `origem_tipo="OPERACAO_AGRICOLA"` em todo o grep realizado | — |
| Sincronização/webhook externo | **Não existe** — não há chamada HTTP nem evento de domínio disparado nesse bloco | — |

**Resposta à pergunta da seção 4:** *Sim, existe mais de um ponto que cria/atualiza* — `criar()` (sem checagem de duplicidade) e `atualizar()`→`_sincronizar_efeitos_operacao` (com checagem via `_buscar_despesa_existente`). Nenhum ponto cancela/reverte.

---

## 3. Mapa de leitura (consumidores)

### 3.1 `agricola/dre/service.py` (já conhecido, confirmado nesta etapa)
- Linhas 654, 684, 698 — soma `Despesa` em `_consolidar_despesas`, mas **exclui** quando `origem_tipo == "OPERACAO_AGRICOLA"` e existe `CostAllocation` correspondente (`alloc_op_ids`, linha 684). Efeito real: evita dupla contagem, mas **só entre esse par**; não resolve a duplicidade com `Despesa(COMPRA)` já identificada em `SOIL-PLAN-EXEC-04B`.

### 3.2 `agricola/dashboard/service.py:238-311` (`resumo_financeiro_safra`) — **CONSUMIDOR REAL**
Confirmado por leitura direta:
```python
stmt_despesas = select(Despesa).where(
    Despesa.tenant_id == self.tenant_id,
    Despesa.origem_tipo == "OPERACAO_AGRICOLA",
    Despesa.origem_id.in_(operacao_ids) if operacao_ids else False
)
despesas = list((await self.session.execute(stmt_despesas)).scalars().all())
despesa_total = sum(float(d.valor_total or 0) for d in despesas)
...
# Custo: usar o menor entre custo_operacoes e despesa_total (evitar dupla contagem)
custo_base = min(custo_operacoes, despesa_total) if despesa_total > 0 else custo_operacoes
lucro_bruto = receita_total - custo_base
roi_pct = (lucro_bruto / custo_base * 100) if custo_base > 0 else None
```
- `despesa_total` **afeta diretamente** `custo_base`, `lucro_bruto`, `roi_pct`, `margem_bruta`, `margem_pct` — todos expostos no schema `SafraResumoFinanceiro`/`FinanceiroResumo` (`agricola/dashboard/schemas.py`) consumido por tela de dashboard.
- A deduplicação usa `min()` como proteção manual **ad-hoc**, comentada explicitamente como "evitar dupla contagem" — mas é frágil: se `despesa_total` divergir de `custo_operacoes` (ex.: edição manual da despesa, rateio parcial, despesa cancelada mas nunca desativada), o ROI muda silenciosamente. Além disso, `custo_operacoes_total` (de `OperacaoAgricola.custo_total`) e `despesa_total` (da Despesa) são **ambos** expostos separadamente no schema — uma tela que renderize os dois pode mostrar dois números diferentes para o "mesmo" custo.
- **Este é o único consumidor que de fato mudaria de resultado se a Despesa fosse removida sem substituição** — ele não tem fallback equivalente a `CostAllocation` hoje.

### 3.3 `agricola/tarefas/service.py:245-266` (`_avaliar_exclusao_tarefa`) — **CONSUMIDOR REAL, MAS REDUNDANTE**
```python
# Bloqueio 1 (linhas ~230-252): via CostAllocation
if allocation_count:
    blockers.append("financeiro")

# Bloqueio 2 (linhas 254-265): via Despesa
despesa_count = await self.session.execute(
    select(func.count(Despesa.id)).where(
        Despesa.tenant_id == self.tenant_id,
        Despesa.origem_tipo == "OPERACAO_AGRICOLA",
        Despesa.origem_id.in_(operacao_ids),
        Despesa.ativo.is_(True),
    )
).scalar_one()
if despesa_count:
    blockers.append("financeiro")
```
Confirmado por leitura direta: como `CostAllocation` e `Despesa(OPERACAO_AGRICOLA)` são criados **juntos**, na mesma condição (`custo_total_operacao > 0`), o bloqueio por `Despesa` nunca produz um resultado diferente do bloqueio por `CostAllocation` — ambos adicionam a mesma string `"financeiro"` ao mesmo conjunto (`blockers`), e o resultado final (`allowed = len(blockers) == 0`) já seria `False` só com o `CostAllocation`. **A remoção da Despesa não mudaria o comportamento de bloqueio de exclusão de tarefa.**

### 3.4 `agricola/alertas/service.py:1057-1083` (`_detectar_allocation_sem_reflexo_economico`) — **CONSUMIDOR REAL, mas inverso**
Usa `outerjoin(CostAllocation → Despesa)` filtrando `origem_tipo == "OPERACAO_AGRICOLA"` e `ativo == True`, para achar `CostAllocation` **sem** Despesa correspondente — gera achado de governança quando falta a despesa, não quando ela existe em duplicidade. Esse consumidor seria **eliminado**, não afetado negativamente, se a criação de `Despesa(OPERACAO_AGRICOLA)` fosse removida (a checagem perde sentido, mas não quebra nada — é um alerta de auditoria, não uma trava de negócio).

### 3.5 Router/serviço financeiro genérico — **CONSUMIDOR APARENTE (sem distinção)**
- `financeiro/routers/despesas.py` (endpoints `GET /despesas/`, `/despesas/vencendo`, `POST`, `PUT`, `DELETE`, `/baixar`) e `financeiro/services/despesa_service.py:listar_com_filtros` — **zero ocorrências de `origem_tipo`** em ambos os arquivos (confirmado por grep direcionado). Filtros disponíveis: `unidade_produtiva_id`, `status`, `vencimento_de/ate`. A Despesa de operação aparece **misturada, sem rótulo especial**, em qualquer listagem financeira genérica.
- Isso não é um "consumidor real" no sentido de mudar um cálculo — é superfície de exposição (ver seção 6).

---

## 4. Consumidores financeiros (tabela obrigatória)

| Consumidor | Consulta a despesa operacional? | Filtra origem? | Filtra status? | Efeito real |
|---|---:|---:|---:|---|
| `agricola/dre/service.py` | Sim | Sim (exclui se há CostAllocation) | Não | Evita dupla contagem só com CostAllocation da própria operação |
| `agricola/dashboard/service.py` | Sim | Sim (filtra por essa origem) | Não | **Muda ROI/margem/lucro exibidos na tela de resumo de safra** |
| `agricola/tarefas/service.py` | Sim | Sim | Sim (`ativo=True`) | Bloqueia exclusão de tarefa — **redundante com CostAllocation** |
| `agricola/alertas/service.py` | Sim (via outerjoin) | Sim | Sim (`ativo=True`) | Gera achado de auditoria quando a despesa **falta** |
| `financeiro/routers/despesas.py` + frontend genérico | Sim (sem filtro) | **Não** | Parcial (filtro de status é opcional, não exclui por padrão) | Exibe a despesa misturada em "Contas a Pagar"/listagem financeira genérica |

**Resposta direta:** *Sim — a aplicação de um insumo é apresentada como pagamento/saída de caixa em pelo menos duas superfícies*: (1) o dashboard de margem de safra, onde `despesa_total` com `status="PAGO"` entra diretamente no cálculo de `lucro_bruto`/ROI; (2) qualquer tela ou exportação genérica de "Contas a Pagar"/"Despesas" que não filtre por `origem_tipo`, onde a despesa aparece com `status="PAGO"` sem nenhuma indicação de que não houve uma transação financeira real — é uma anotação contábil automática, não um pagamento efetivo confirmado externamente.

---

## 5. APIs e routers

- `financeiro/routers/despesas.py`: endpoints CRUD genéricos, sem parâmetro de filtro por `origem_tipo`. Nenhum endpoint dedicado a "despesas de operação agrícola" separado do genérico.
- Não foi encontrado endpoint que exponha `origem_tipo` como filtro de query param, nem que oculte por padrão registros com essa origem.

**Resposta direta:** *Sim — um usuário financeiro vê a despesa operacional misturada às despesas reais de fornecedor*, sem filtro automático no backend nem no frontend (confirmado na seção 6).

---

## 6. Frontend Web

- `apps/web/src/app/(dashboard)/dashboard/financeiro/despesas/page.tsx`: grep por `origem_tipo`/`OPERACAO_AGRICOLA` retornou **zero ocorrências**. A tela consome o endpoint genérico de despesas sem tratamento especial dessa origem.
- **Respostas diretas:**
  - A origem `OPERACAO_AGRICOLA` é exibida? Não com rótulo distinto — aparece como qualquer outra despesa.
  - É rotulada como operação, custo ou pagamento? Não confirmado nenhum rótulo específico no frontend.
  - É distinguida de compra? Não.
  - Pode ser editada/cancelada/conciliada/exportada? Usa os mesmos endpoints CRUD genéricos — tecnicamente sim, sem tratamento diferenciado (risco: um usuário financeiro poderia editar/"pagar novamente" uma despesa que na verdade é uma anotação automática de custo).
  - Aparece em totais? Sim, nos totais da listagem genérica de despesas (sem exclusão).

---

## 7. Campo PWA

Grep por "despesa"/"financeiro" em `apps/campo` retornou **zero resultados**.

**Resposta direta:** *A remoção da `Despesa(OPERACAO_AGRICOLA)` não afetaria o Campo PWA* — confirmado, nenhuma dependência.

---

## 8. Webhooks e eventos

`services/api/tests/test_operacao_despesa_webhook.py` foi lido integralmente (7 testes, listados na auditoria `SOIL-PLAN-EXEC-04C0`/`04C1`). **Nenhum teste faz chamada HTTP, mock de `requests`, ou callback externo** — todos chamam `OperacaoService.criar()` diretamente (função Python) e verificam o registro no banco via `select(Despesa)`.

**Respostas diretas:**
- O teste valida um webhook real? **Não** — "webhook" é apenas o nome do arquivo/conceito interno para "efeito colateral automático in-process", não uma integração HTTP.
- Qual consumidor recebe esse webhook? Nenhum — não existe callback externo.
- O webhook é usado em produção? Não existe webhook real a ser usado.
- O evento depende da existência da `Despesa`, ou poderia ser emitido pela operação/CostAllocation diretamente? Como não há webhook real, esta pergunta é não aplicável — o "evento" é apenas a própria criação síncrona do registro no banco.

---

## 9. Integrações ERP

- Grep por `"Despesa"` dentro de `services/api/integracoes/` encontrou **um único arquivo relevante**: `integracoes/sankhya/services/external_association_helper.py` — mas trata-se de **sincronização inbound** (do ERP para o AgroSaaS): `sync_financeiro()` recebe um payload de `TituloFinanceiro` vindo do Sankhya e tenta **encontrar** (`_find_financeiro`, linhas 846-863) um `Despesa`/`Receita` local correspondente, por `numero_documento` (NF), `data_vencimento` e `valor` — para fins de reconciliação/associação (`ExternalRecordAssociation`), não para **enviar** despesas locais ao ERP.
- A `Despesa(OPERACAO_AGRICOLA)` não é criada com `numero_nf`/`chave_nfe` preenchidos (esses campos só são setados na `Despesa(COMPRA)`, via `recebimento.numero_nf` — confirmado na auditoria `SOIL-PLAN-EXEC-04B`, seção 5) — portanto a correspondência por `numero_documento` dificilmente casaria com uma despesa de operação. **Risco teórico residual, não confirmado como ativo**: se por coincidência `numero_documento`/`valor`/`vencimento` de um título do ERP colidissem com uma despesa de operação (que tipicamente teria esses campos nulos ou não-comparáveis), a associação poderia ocorrer incorretamente — mas não há evidência de que isso já tenha ocorrido ou seja um caminho exercitado na prática.

**Resposta direta:** *Não há risco confirmado de a despesa operacional ser enviada ao ERP como pagamento artificial* — o fluxo é de leitura/reconciliação inbound, não de envio outbound; e os campos usados para correspondência normalmente não estão presentes na despesa de operação.

---

## 10. Consumidores agrícolas e de custo

| Fonte | Usa `Despesa(OPERACAO_AGRICOLA)`? | Usa `CostAllocation`/`custo_total` diretamente? |
|---|---|---|
| `agricola/dashboard/service.py` (ROI/margem por safra) | **Sim, diretamente** | Sim, também (`custo_operacoes_total` via `OperacaoAgricola.custo_total`) — os dois coexistem com deduplicação manual |
| `agricola/custos/service.py` | Não confirmado uso direto — comentário no código indica preferência por `CostAllocation` como "fonte canônica em novos fluxos" | Sim, primário |
| `agricola/dre/service.py` | Sim, mas exclui via `CostAllocation` | Sim (fonte primária de `custos_operacionais`) |

**Resposta direta:** *Nenhum indicador agrícola depende **exclusivamente** da `Despesa(OPERACAO_AGRICOLA)`* — em todos os casos mapeados, `CostAllocation`/`OperacaoAgricola.custo_total` já carrega a mesma informação de custo de forma equivalente ou superior (mais granular, com `production_unit_id`). O único ponto onde a Despesa tem efeito **não redundante** é o dashboard de margem (seção 3.2), e mesmo ali `custo_operacoes_total` (via `custo_total`) já está disponível como alternativa — a lógica apenas ainda não foi migrada para usar somente essa fonte.

---

## 11. Auditoria e rastreabilidade

A rastreabilidade técnica operação→execução→consumo→custo já é garantida, independentemente da Despesa, por:
- `OperacaoExecucao` (execução, quantidade, custo_real, operador, máquina — auditoria `SOIL-PLAN-EXEC-04`);
- `CostAllocation` (apropriação de custo à unidade produtiva/safra);
- Movimentos FIFO em `EstoqueMovimento`/`LoteEstoque`;
- Eventos de caderno (`CadernoCampoEntrada`, criados pelo mesmo fluxo, agora sem o defeito `MissingGreenlet` — `SOIL-PLAN-EXEC-04C1`).

**Resposta direta:** *A rastreabilidade técnica já é suficiente sem a Despesa* — `OperacaoExecucao` + `CostAllocation` + movimento FIFO + evento de caderno cobrem toda a cadeia de "o que aconteceu, quando, quem, quanto custou, e onde foi apropriado". A Despesa adiciona apenas uma representação *financeira* (não técnica) desse mesmo fato, cujo único consumidor não-redundante é o dashboard de margem (seção 3.2) — uma necessidade de **exibição de número consolidado em tela**, não de rastreabilidade técnica.

---

## 12. Cancelamento

Confirmado (reforçando `SOIL-PLAN-EXEC-04B`): `_reverter_movimentos_estoque_operacao` não toca `Despesa` nem `CostAllocation`. Buscas adicionais por `status.*CANCELADO`, `ativo.*=.*False` em `despesa_service.py` e `operacoes/service.py` **não encontraram** nenhum escritor que desative a despesa de operação.

| Consumidor | Efeito após cancelamento não tratado |
|---|---|
| Dashboard de margem (3.2) | **Continua somando a despesa "fantasma"** — `despesa_total` permanece inflado mesmo após reversão de estoque |
| DRE (3.1) | Neutro — a exclusão por `CostAllocation` continua válida enquanto o `CostAllocation` também não for revertido (ambos permanecem "vivos" juntos, sem dupla contagem entre si, mas ambos incorretamente presentes) |
| Bloqueio de exclusão de tarefa (3.3) | Continua bloqueando (redundante com `CostAllocation`, que também não é revertido) |
| Alerta de governança (3.4) | Neutro — não dispara (a Despesa "falsa" ainda existe, então não há CostAllocation órfão) |
| Router/frontend financeiro genérico (3.5) | **Despesa "PAGO" permanece visível/editável indefinidamente**, sem qualquer marcação de que a operação de origem foi revertida |

**Resposta direta:** *A despesa permanece em caixa (não há caixa real, mas permanece com `status="PAGO"`), permanece na listagem de "Contas a Pagar"/despesas genérica, permanece no frontend, pode ser editada manualmente (via CRUD genérico), e não existe status "CANCELADO" nem soft-delete (`ativo=False`) aplicado a ela neste cenário.* A DRE não é afetada porque a exclusão por `CostAllocation` permanece consistente (os dois ficam órfãos juntos), mas o dashboard de margem (3.2) fica diretamente distorcido.

---

## 13. Testes executados

```bash
$ .venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_dre_agricola_v1.py tests/test_fifo_estoque.py -q
21 passed in 40.91s

$ .venv/bin/python -m pytest tests/integration/financeiro/test_despesas.py tests/test_multi_up_hardening_step01.py -q
17 passed in 34.58s

$ .venv/bin/python -m pytest tests/test_dashboard_financeiro_safra.py -q --tb=short
3 failed, 3 passed in 9.20s
FAILED test_resumo_financeiro_safra_valido — AssertionError: receita_total esperado != obtido
FAILED test_resumo_financeiro_safra_sem_operacoes — AssertionError: receita_total esperado 0.0, obtido 30000.0
FAILED test_resumo_roi_calculado — AssertionError: receita_total esperado 300000.0, obtido 330000.0
```

**Classificação das 3 falhas em `test_dashboard_financeiro_safra.py`:** não relacionadas a `Despesa(OPERACAO_AGRICOLA)` — os valores divergentes são de `receita_total` (soma de `Receita`/`ComercializacaoCommodity`), não de `despesa_total`/custo. Padrão consistente com **defeito de isolamento de teste/fixture** (dados residuais entre execuções, provavelmente por não escopar `ComercializacaoCommodity` corretamente por tenant/produto na query do serviço, `agricola/dashboard/service.py:267-282`, que filtra apenas por `tenant_id`, sem filtro adicional por `produto_colhido_id` quando a lista está vazia) — classificado como **"não relacionado"** ao escopo desta auditoria (confirma, porém, que o consumidor 3.2 tem cobertura de teste real, apenas com um defeito pré-existente e não investigado a fundo nesta etapa, conforme instrução de não corrigir). Nenhuma correção foi aplicada.

**Nenhum teste** cobre: cancelamento de operação + reversão da despesa; `ExternalRecordAssociation` envolvendo Despesa (não existe tal associação outbound); webhook HTTP real (não existe).

---

## 14. Matriz de consumidores

| Consumidor | Tipo | Usa OPERACAO_AGRICOLA? | Depende do registro? | Pode usar CostAllocation? | Impacto se remover |
|---|---|---:|---:|---:|---|
| DRE agrícola | Relatório | Sim | Não diretamente (já exclui) | Sim | Baixo — já é redundante com CostAllocation |
| Dashboard de margem de safra | Tela/cálculo | Sim | **Sim, diretamente** | Parcialmente (`custo_operacoes_total` já existe como alternativa, mas a lógica de dedup usaria só uma fonte) | **Médio-Alto** — requer migração de código antes de remover |
| Exclusão de tarefa (bloqueio) | Regra de negócio | Sim | Não (redundante com CostAllocation) | Sim | Nenhum |
| Alerta de governança (CostAllocation órfão) | Auditoria | Sim (para detectar ausência) | Não (a checagem apenas deixa de fazer sentido) | N/A | Nenhum — checagem se torna obsoleta, não quebra |
| Router/frontend financeiro genérico | Exposição | Sim (sem filtro) | Sim, no sentido de "deixa de aparecer" | N/A | Baixo — remove uma confusão, não uma funcionalidade |
| Campo PWA | — | Não | Não | N/A | Nenhum |
| Integração ERP (Sankhya, inbound) | Reconciliação | Não confirmado ativo | Não | N/A | Nenhum |

---

## 15. Consumidores reais versus aparentes

### Consumidores reais (mudam resultado/tela/decisão)
1. `agricola/dashboard/service.py` — muda ROI/margem/lucro exibidos.
2. `agricola/tarefas/service.py` — bloqueia exclusão (mas redundante com CostAllocation).
3. `agricola/alertas/service.py` — gera achado de auditoria quando a Despesa **falta** (efeito inverso).
4. `agricola/dre/service.py` — já tratado, efeito neutro (exclusão funcional).

### Consumidores aparentes (não mudam nada de forma exclusiva)
- `financeiro/routers/despesas.py` + frontend genérico — apenas expõe o registro junto com todos os outros, sem lógica condicionada a essa origem especificamente.
- `integracoes/sankhya/services/external_association_helper.py` — importa `Despesa` genericamente para reconciliação de qualquer origem, sem relação confirmada especificamente com `OPERACAO_AGRICOLA`.
- `agricola/operacoes/service.py:_buscar_despesa_existente` — parte do próprio mecanismo de criação, não um consumidor externo.
- Todos os testes que apenas confirmam a criação (`test_operacao_despesa_webhook.py`) — validam o comportamento de escrita, não são consumidores de leitura com efeito.

---

## 16. Respostas obrigatórias

```text
1. EXISTEM CONSUMIDORES REAIS FORA DA DRE: SIM
2. A DESPESA OPERACIONAL AFETA CAIXA: NÃO (nasce "PAGO" mas sem transação financeira real confirmada — é anotação contábil, não movimento de caixa efetivo)
3. A DESPESA OPERACIONAL AFETA CONTAS A PAGAR: SIM, EM EXPOSIÇÃO (aparece misturada na listagem genérica, sem filtro; não é tecnicamente "a pagar" pois já nasce PAGO, mas usa o mesmo modelo/tela)
4. A DESPESA OPERACIONAL É ENVIADA AO ERP: NÃO (fluxo confirmado é inbound/reconciliação, não outbound; sem evidência de envio ativo)
5. O CAMPO PWA DEPENDE DELA: NÃO
6. COSTALLOCATION PODE SUBSTITUÍ-LA: PARCIALMENTE (substitui integralmente os consumidores 3.3 e 3.4; o consumidor 3.2 — dashboard de margem — precisaria de migração de código, hoje usa Despesa diretamente)
7. SUA REMOÇÃO É SEGURA: NÃO, SEM RESSALVAS — COM RESSALVAS SIM (segura apenas após migrar o dashboard de margem de safra para usar CostAllocation/custo_total como fonte única)
8. DIREÇÃO RECOMENDADA: E
```

---

## 17. Decisão recomendada

**Direção E — separar compra financeira e custo agrícola**, com sequenciamento em duas etapas (não implementadas nesta auditoria):

1. **Pré-requisito:** migrar `agricola/dashboard/service.py:resumo_financeiro_safra` para calcular custo exclusivamente a partir de `OperacaoAgricola.custo_total`/`CostAllocation` (já disponível como `custo_operacoes_total`), removendo a dependência de `despesa_total` e a deduplicação `min()` ad-hoc.
2. **Depois:** neutralizar o efeito financeiro de `Despesa(OPERACAO_AGRICOLA)` — seja parando de criá-la, seja mantendo-a apenas como rastro histórico sem impacto em relatórios/telas (equivalente à Direção C, mas apenas como consequência de já não ter mais consumidor real dependente).

Justificativa: `CostAllocation` já é a fonte de verdade em todos os consumidores exceto um (dashboard de margem), que tem alternativa pronta e não usada (`custo_total`). O bloqueio de exclusão de tarefa e o alerta de governança não seriam afetados pela remoção. Nenhum consumidor de caixa real, ERP ou Campo depende da Despesa. O principal risco de manter como está é o gap de cancelamento (seção 12), que distorce justamente o único consumidor não-redundante (dashboard de margem).

**Direção D (transitória, alternativa de menor risco imediato)** também é defensável como primeiro passo: manter a Despesa por ora e apenas estender `_consolidar_despesas` da DRE para excluir também `origem_tipo="COMPRA"` quando há `CostAllocation` correspondente ao consumo do mesmo insumo (resolvendo a dupla contabilização confirmada em `SOIL-PLAN-EXEC-04B`), adiando a decisão sobre remover/reclassificar `Despesa(OPERACAO_AGRICOLA)` até que o dashboard de margem seja migrado. Isso desacopla a correção urgente (dupla contagem Compra×Aplicação na DRE) da decisão estrutural sobre a despesa operacional.

---

## 18. Menor próximo passo

Não implementar nesta etapa. Recomenda-se, como próxima ação:

1. **Curto prazo (resolve o achado crítico de `SOIL-PLAN-EXEC-04B`):** estender a exclusão em `agricola/dre/service.py:_consolidar_despesas` para cobrir `origem_tipo="COMPRA"` quando o insumo comprado já tiver `CostAllocation` de consumo — independente de qualquer decisão sobre `Despesa(OPERACAO_AGRICOLA)`.
2. **Médio prazo:** migrar `agricola/dashboard/service.py:resumo_financeiro_safra` para usar exclusivamente `custo_operacoes_total`/`CostAllocation`, eliminando a dependência de `despesa_total` e a deduplicação `min()`.
3. **Somente depois:** decidir remoção/reclassificação definitiva de `Despesa(OPERACAO_AGRICOLA)`, agora sem nenhum consumidor real dependente.
4. **Independente da decisão acima:** tratar o gap de cancelamento (seção 12) — hoje nenhuma reversão de operação desativa `Despesa` nem `CostAllocation`, o que distorce qualquer consumidor que ainda dependa deles.

---

## Validações executadas

```bash
$ git status --short
(nenhuma alteração introduzida por esta auditoria — arquivos modificados são de etapas anteriores desta sessão)

$ git diff --check
(sem saída — limpo)
```

O único arquivo novo criado nesta etapa é este relatório.

---

## Veredicto

```text
SOIL-PLAN-EXEC-04C
STATUS: GO COM RESSALVAS
```

```text
DIREÇÃO RECOMENDADA: E
```

```text
PRÓXIMO PASSO: Estender a exclusão de _consolidar_despesas (agricola/dre/service.py) para
origem_tipo="COMPRA" quando há CostAllocation correspondente ao consumo do insumo — resolve
a dupla contabilização crítica de SOIL-PLAN-EXEC-04B de forma independente da decisão sobre
Despesa(OPERACAO_AGRICOLA), cuja remoção/reclassificação definitiva fica condicionada à
migração prévia do dashboard de margem de safra (agricola/dashboard/service.py) para usar
CostAllocation/custo_total como fonte exclusiva.
```
