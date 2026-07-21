# SOIL-PLAN-EXEC-04H — Auditoria da Necessidade de Despesa(OPERACAO_AGRICOLA)

**Etapa somente leitura. Nenhum código de produção, teste, model, schema, migration ou frontend foi
alterado. Único artefato produzido: este relatório.**

## 1. Resumo executivo

`Despesa(origem_tipo="OPERACAO_AGRICOLA")` é criada em um único ponto do sistema
(`agricola/operacoes/service.py`, método `criar()`), sempre com `status="PAGO"` e
**`valor_pago=None`** (nunca preenchido), sem `pessoa_id`/fornecedor real, sem `forma_pagamento`,
sem `numero_nf`. As etapas 04E–04G já eliminaram sua necessidade para DRE agrícola (fonte é
`CostAllocation`) e dashboard de margem (idem). **Porém a auditoria encontrou que o registro não é
inerte**: ele é lido, sem filtro por `origem_tipo`, por três serviços do módulo financeiro genérico
que **são rotas HTTP reais e montadas**:

- `GET /financeiro/dashboard` (`financeiro/services/dashboard_service.py`) — soma
  `coalesce(valor_pago, valor_total)` em `total_pago_mes`, inflando artificialmente o "total pago no
  mês" do dashboard financeiro da fazenda com o custo interno de cada operação agrícola.
- Livro Caixa / Carnê-Leão RFB (`financeiro/services/relatorio_service.py`) — usa
  `Despesa.valor_pago` diretamente; como é sempre `None`, a despesa aparece no export fiscal como
  linha "PAGO" com valor R$ 0,00 — poluição de um documento fiscal real, não distorção de valor.
- `financeiro/services/integracao_service.py` (Carnê-Leão / resumo contábil) — mesma exposição.

Além disso, dois alertas de governança do próprio módulo agrícola (`_detectar_
allocation_sem_reflexo_economico`, severidade `RISCO_ECONOMICO`, e
`validar_despesa_automatica_unica_origem`) **dependem ativamente** da existência da despesa como
âncora de reconciliação — removê-la sem ajustar esses alertas geraria alarme falso permanente.

**Conclusão:** `Despesa(OPERACAO_AGRICOLA)` não representa uma obrigação financeira real (sem
credor, sem vencimento útil, sem pagamento real, sem conciliação bancária, sem export ERP), mas
**não é segura para remoção isolada** — ela hoje vaza para relatórios financeiros genéricos e
alimenta alertas de governança que precisam ser corrigidos/redirecionados na mesma janela de
mudança. Recomenda-se remoção da criação (`OPERACAO-DESPESA-A`) condicionada a ajustar os dois
consumidores identificados nas seções 6 e 15 — não é uma remoção "livre de efeitos colaterais".

## 2. Origem e ciclo de vida

| Local | Operação | Finalidade aparente | Consumidor real |
|---|---|---|---|
| `agricola/operacoes/service.py:1088-1112` (`criar()`) | **cria** | Registrar automaticamente o custo da operação como "despesa paga" | DRE (fallback quando não há `CostAllocation`), dashboard financeiro genérico, Livro Caixa/Carnê-Leão, alertas de reconciliação |
| `agricola/operacoes/service.py:514-524` (`_sincronizar_efeitos_operacao`) | **atualiza** | Manter `valor_total`/`data_*`/`unidade_produtiva_id`/`cultivo_id` sincronizados quando a operação é editada | mesmos acima |
| `agricola/operacoes/service.py` (`_buscar_despesa_existente`) | **consulta** | Localizar a despesa ativa de uma operação (idempotência de criação/atualização) | usado por `_sincronizar_efeitos_operacao`, `_reverter_efeitos_economicos_operacao` (04G) |
| `agricola/operacoes/service.py` (`_reverter_efeitos_economicos_operacao`, 04G) | **neutraliza** | `ativo=False`, `status="CANCELADO"` no cancelamento/reversão da operação | DRE/dashboard param de exclusão (`ativo=True`) |
| `agricola/dre/service.py:654,689,703` (`_consolidar_despesas`) | **consulta/exclui condicionalmente** | Excluir da DRE quando há `CostAllocation` correspondente (via `OperacaoExecucao`); caso não haja, a despesa **entra** na DRE como fallback implícito | DRE agrícola |
| `agricola/tarefas/service.py:253-263` | **consulta (bloqueio)** | Contar despesas ativas vinculadas para bloquear exclusão de tarefa (label `"financeiro"`, igual ao de `CostAllocation`) | fluxo de exclusão de tarefa |
| `agricola/alertas/service.py:508-511` (`classificar_origem_despesa`) | **classifica** | Determinar regra de governança (`AGRICOLA_OPERACIONAL`, exige origem rastreável) | `validar_despesa_origem_leve` |
| `agricola/alertas/service.py:1056-1080` (`_detectar_allocation_sem_reflexo_economico`) | **consulta (outer join)** | Alertar `CostAllocation` sem `Despesa` correspondente (`RISCO_ECONOMICO`) | DRE `kpis.warnings_relevantes`, dashboard |
| `agricola/alertas/service.py:660+` (`validar_despesa_automatica_unica_origem`) | **consulta (contagem)** | Alertar despesa automática duplicada para a mesma `origem_id` | governança de criação |
| `financeiro/services/dashboard_service.py:38-84` | **consulta (sem filtro de origem)** | KPIs `total_pago_mes`, `total_a_pagar`, `total_atrasado_despesas`, próximos vencimentos | `GET /financeiro/dashboard` |
| `financeiro/services/relatorio_service.py:260-286` | **consulta (sem filtro de origem)** | Livro Caixa (RFB), usa `Despesa.valor_pago` bruto | relatório fiscal Carnê-Leão |
| `financeiro/services/integracao_service.py` | **consulta (sem filtro de origem)** | Resumo para escritório contábil / export | integração contábil externa |
| `integracoes/sankhya/services/external_association_helper.py:851-869` | **consulta (match por NF)** | Associar título ERP a `Despesa` local por `numero_nf`/`nota_fiscal` | sincronização Sankhya (inbound) — não corresponde na prática (campos sempre `None`) |

## 3. Natureza econômica

Verificado em `financeiro/models/despesa.py`: o campo `pessoa_id` (fornecedor cadastrado) **não é
preenchido** na criação; `fornecedor` (texto livre) também não; `forma_pagamento` não; `numero_nf`/
`chave_nfe`/`nota_fiscal` não; `grupo_parcela_id`/`numero_parcela` não. `valor_pago` fica `None`
apesar de `status="PAGO"` — um estado inconsistente dentro do próprio contrato do modelo (`PAGO` sem
valor pago registrado).

Respostas:
- **Existe credor real associado?** Não.
- **Existe vencimento real?** Não — `data_vencimento = data_realizada` (mesma data da operação, não
  um vencimento financeiro).
- **Existe documento financeiro real?** Não.
- **Existe pagamento real?** Não (`valor_pago=None`, nenhum evento de pagamento).
- **Existe parcela?** Não.
- **Existe baixa?** Não.
- **Existe conciliação?** Não (nenhuma referência em `financeiro/models/conciliacao.py`).
- **Existe vínculo bancário?** Não.
- **Existe transmissão para ERP?** Não confirmada (ver seção 12).

O registro é, na prática, uma **espelhação de `OperacaoAgricola.custo_total`** (e, por extensão, do
que hoje é mais corretamente representado por `CostAllocation`) fantasiada de título financeiro
"PAGO" dentro da mesma tabela usada para contas a pagar reais (`fin_despesas`).

## 4. Contas a pagar e pagamentos

`status="PAGO"` faz com que a despesa **não apareça** nas telas/consultas de "a pagar"
(`Despesa.status.in_({"A_PAGAR","ATRASADO"})`, usadas em `dashboard_service.py:41-42` e nos "próximos
vencimentos" linha 78) — portanto **não gera obrigação financeira fictícia em aberto**. O risco real
está no lado oposto: por já nascer "PAGO", ela é somada em **`total_pago_mes`** (seção 1), inflando o
indicador de caixa efetivamente desembolsado no período — uma operação agrícola sem nenhuma saída de
caixa real passa a contar como dinheiro pago.

Pesquisa em `financeiro/models/`: nenhum model `Pagamento`, `ContaPagar`, `Parcela` ou `Baixa`
dedicado existe além dos campos embutidos em `Despesa` (`valor_pago`, `data_pagamento`,
`grupo_parcela_id`). `LancamentoFinanceiro` é um model separado, não populado pela criação de
`Despesa(OPERACAO_AGRICOLA)` (confirmado: nenhuma referência cruzada). `Conciliacao` (`ContaBancaria`,
`LancamentoBancario`) não referencia `Despesa` de origem agrícola.

**Classificação de risco: RISCO REAL** (não teórico) para o KPI `total_pago_mes` do dashboard
financeiro genérico e para a integridade do export Livro Caixa/Carnê-Leão (linhas fiscais "PAGO"
sem valor).

## 5. Pagamentos e baixa

Confirma-se, por leitura de `financeiro/routers/despesas.py` e `financeiro/services/despesa_service.py`,
que o fluxo de baixa/pagamento manual do módulo financeiro opera sobre qualquer `Despesa` ativa
independente de `origem_tipo` — ou seja, **é tecnicamente possível** um operador humano "baixar"
manualmente uma `Despesa(OPERACAO_AGRICOLA)` pela tela financeira, já que nada no schema/router
distingue despesas automáticas de despesas reais de compra. Isso é uma superfície de erro humano:
nada impede um usuário de "pagar novamente" (definir `valor_pago`) algo que nunca foi uma obrigação
de caixa.

## 6. Plano de contas

A conta é escolhida dinamicamente (`operacoes/service.py:1073-1083`): primeira `PlanoConta` ativa com
`categoria_rfb == "CUSTEIO"`, ordenada por `natureza` (analítica antes de sintética) — **a mesma
categoria fiscal usada por despesas reais de custeio** (compra de insumos, serviços). Não existe
distinção entre "custo apropriado internamente" e "obrigação financeira real" no plano de contas:
`categoria_rfb` mapeia diretamente para os grupos do Livro Caixa do Produtor Rural (RFB, ver
`financeiro/models/plano_conta.py:16`), então o lançamento **entra na mesma classificação fiscal**
usada para apuração real de custeio agropecuário.

## 7. DRE — cenários

Comportamento confirmado por leitura de `agricola/dre/service.py::_consolidar_despesas` (04E) e por
teste (`test_dre_v1_consolida_precedencia_e_nao_duplica_receita_rateio`):

| Cenário | `CostAllocation` | `Despesa(OPERACAO_AGRICOLA)` | Entra na DRE? |
|---|---|---|---|
| **A** — operação com allocation | existe | existe | Apenas `CostAllocation` (despesa excluída via `alloc_op_ids`) |
| **B** — operação histórica sem allocation | não existe | existe (custo_total) | **A despesa entra** — este é o fallback real e não documentado explicitamente como tal; a DRE não tem um fallback formal, apenas a ausência de exclusão condicional resulta no mesmo efeito |
| **C** — despesa órfã (operação inexistente, sem allocation) | não existe | ativa | Entra — `_consolidar_despesas` não valida existência da `OperacaoAgricola` de origem, apenas o vínculo por `origem_id`/`origem_tipo` |
| **D** — operação cancelada (04G) | removida | `ativo=False`/`status=CANCELADO` | Não entra (filtro `Despesa.ativo == True` já existente) |

**Achado relevante para a decisão:** o Cenário B mostra que a despesa **ainda cumpre uma função de
fallback real na DRE hoje** para operações antigas sem `CostAllocation` — diferente do dashboard
(04F), que tem fallback explícito e dedicado para `OperacaoAgricola.custo_total`. A DRE **não tem**
esse fallback direto; ela depende da despesa para não perder custo de operações pré-04-era. Isso é
uma dependência funcional real, ainda que estreita (só afeta dados históricos sem allocation).

## 8. Dashboard e demais relatórios

Confirmado (04F): `agricola/dashboard/service.py` não importa mais `Despesa` — usa `CostAllocation`
com fallback por `OperacaoAgricola.custo_total` por operação. Nenhuma alteração necessária ali.

Relatórios adicionais pesquisados além do escopo das etapas anteriores:
- `financeiro/services/dashboard_service.py` (dashboard financeiro genérico, `GET /financeiro/dashboard`)
  — **consumidor real e ativo**, sem filtro de `origem_tipo` (seção 1/4).
- `financeiro/services/relatorio_service.py` (Livro Caixa/Carnê-Leão) — **consumidor real e ativo**
  (seção 1).
- `financeiro/services/integracao_service.py` (resumo contábil/OFX) — **consumidor real** para o
  resumo contábil exportável.
- Margem por talhão (`resumo_margem_por_talhao` em `agricola/dashboard/service.py`) — usa
  `OperacaoAgricola.custo_total` diretamente, nunca `Despesa` — não afetado.
- Backoffice, CSV/XLSX/PDF exports do módulo agrícola: nenhuma referência a `Despesa` encontrada fora
  do módulo financeiro genérico.

## 9. Campo PWA

`grep -rl "despesa" apps/campo` → **zero resultados**. O Campo PWA não cria, recebe, exibe ou
depende da despesa para sincronização ou idempotência — opera exclusivamente sobre
operação/execução/estoque. Nenhum risco de quebra de contrato do app de campo.

## 10. ERP e integrações

`integracoes/sankhya/services/external_association_helper.py::_find_financeiro` faz *matching*
inbound (ERP → local) por `numero_nf`/`nota_fiscal` + `data_vencimento` + `valor_total`. Como
`Despesa(OPERACAO_AGRICOLA)` nunca preenche `numero_nf` nem `nota_fiscal` (ambos `None`), a condição
`or_(model.numero_nf == numero_documento, model.nota_fiscal == numero_documento)` nunca casa —
**na prática, nunca é associada a um título Sankhya**. Nenhum ponto de exportação outbound (local →
ERP) de `Despesa` foi encontrado em `integracoes/erp/` ou `integracoes/sankhya/`. **Classificação:
SEM RISCO para ERP.**

## 11. Eventos

A criação da despesa não dispara webhook nem evento de domínio dedicado — apenas duas chamadas de
validação/alerta síncronas (`validar_despesa_origem_leve`, `validar_despesa_automatica_unica_origem`,
seção 15). Nenhum event bus/outbox é usado. Esses dois efeitos **podem**, em tese, ser refeitos sobre
`OperacaoAgricola`/`OperacaoExecucao`/`CostAllocation` diretamente, mas isso é trabalho de uma etapa
de implementação futura, não desta auditoria.

## 12. Tarefas e bloqueios

`agricola/tarefas/service.py:253-263`: a contagem de `Despesa(OPERACAO_AGRICOLA, ativo=True)`
adiciona o **mesmo** blocker `"financeiro"` que a contagem de `CostAllocation` — não é um blocker
distinto, é redundante na label final. Para **dados criados após 04G** (allocation e despesa sempre
neutralizados juntos), a checagem de despesa nunca dispara isoladamente. Para **dados legados**
(operações criadas antes de 04G, ou casos onde `custo_total > 0` mas `production_unit_id` era nulo na
criação, cenário em que só a despesa foi criada e a allocation nunca existiu — ver
`_garantir_execucao_e_allocation_leves`, linha 616), a despesa **é a única evidência financeira**
retida — removê-la sem migração de dados poderia permitir excluir uma tarefa que ainda tem custo
lançado no Livro Caixa/dashboard financeiro genérico.

**Resposta:** o bloqueio por despesa é redundante para dados novos, mas **não é redundante para dados
legados sem allocation** — `CostAllocation` isoladamente não é suficiente para cobrir 100% do
histórico enquanto a despesa legada continuar existindo e sendo lida por outros relatórios.

## 13. Alertas de governança

- `_detectar_allocation_sem_reflexo_economico` (`agricola/alertas/service.py:1056`, severidade
  `RISCO_ECONOMICO`, código `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO`): detecta `CostAllocation`
  (`source="OPERATION_EXECUTION"`) sem `Despesa` ativa correspondente. Problema que pretendia
  detectar: divergência entre a camada de apropriação de custo e a camada financeira — no desenho
  original, um sintoma de bug de sincronização. **Se a criação de despesa for removida, esse alerta
  passa a disparar para 100% das operações novas com custo — falso positivo massivo e permanente.**
  Precisa ser reescrito ou removido antes/junto da remoção da criação de despesa.
- `validar_despesa_automatica_unica_origem`: detecta duplicidade de despesa automática para a mesma
  `origem_id`. Sem criação de despesa, fica automaticamente inerte (nunca mais dispara) — não é um
  problema, apenas se torna código morto a ser removido em limpeza futura.
- `validar_despesa_origem_leve` / `classificar_origem_despesa`: exige que despesas automáticas de
  origem `OPERACAO_AGRICOLA` tenham `origem_id` rastreável — também fica inerte, sem risco.

## 14. Dados existentes

Estimativa por leitura de código, **sem consulta ao banco de dados de produção** (fora do escopo de
uma auditoria somente leitura sem acesso operacional confirmado a essa instância; nenhuma string de
conexão de produção foi localizada de forma segura nesta sessão). **Limitação registrada
conforme item 16 do plano.** Uma consulta real (COUNT por status/ativo/allocation) deveria ser
executada em staging antes de qualquer decisão de remoção, usando exatamente os filtros descritos
na seção 2 (join `OperacaoExecucao`→`CostAllocation` por `operacao_id`, `Despesa.ativo`,
`Despesa.status`).

## 15. Cenários históricos e estratégia de compatibilidade

Se a criação for removida no futuro, os dados antigos permanecem intactos (nenhuma migration nesta
etapa). Consequências previstas:
- Operações antigas mantêm a despesa e continuam aparecendo no Livro Caixa/dashboard financeiro
  genérico e no fallback da DRE (Cenário B, seção 7) — comportamento inalterado para o passado.
- Operações novas deixam de gerar despesa — DRE passa a depender **exclusivamente** de
  `CostAllocation` para dados novos (correto, dado que 04G garante criação de allocation sempre que
  `custo_total > 0` e `production_unit_id` resolvido).
- O alerta `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO` (seção 13) precisa ser corrigido **antes** da
  remoção, ou passará a disparar para toda operação nova.
- Testes que hoje esperam criação automática (`test_operacao_despesa_webhook.py`,
  `test_multi_up_hardening_step01.py`, `test_operational_workflow_governance_step08/step10.py`)
  precisarão ser reescritos ou removidos na etapa de implementação.

Comparação de alternativas (sem implementar nenhuma):

| Alternativa | Risco | Benefício |
|---|---|---|
| **A — remover criação, manter histórico** | Requer corrigir o alerta `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO` e reescrever ~4 arquivos de teste; DRE perde fallback formal para dados futuros sem allocation (mitigado: 04G garante allocation sempre que há custo+PU) | Elimina a poluição do dashboard financeiro genérico e do Livro Caixa/Carnê-Leão para dados novos; simplifica o modelo mental (uma fonte de custo) |
| **B — manter apenas como fallback sem allocation** | Mistura conceito de "obrigação financeira" com "fallback de apropriação" — o próprio plano já marca essa alternativa como exigindo forte justificativa; ainda vaza para o dashboard financeiro/Livro Caixa nos casos de fallback | Preserva alguma cobertura para os poucos casos em que `production_unit_id` não resolve |
| **C — manter como registro informativo (fora do financeiro)** | O model `Despesa` (`fin_despesas`) não foi desenhado para isso — exigiria excluí-lo dos relatórios financeiros genéricos com filtros adicionais em 3 serviços (`dashboard_service`, `relatorio_service`, `integracao_service`), ou migrar para outro model | Preserva rastreabilidade textual sem risco fiscal, se implementado corretamente |
| **D — substituir por outro registro de apropriação** | `CostAllocation` já cumpre esse papel — criar um novo model duplicaria conceito sem necessidade comprovada | Nenhum benefício claro identificado |
| **E — manter como está** | Continua poluindo `total_pago_mes` do dashboard financeiro e o export fiscal Livro Caixa/Carnê-Leão indefinidamente | Nenhuma mudança de risco necessária a curto prazo |

## 16. Testes

Testes que dependem hoje da criação/comportamento de `Despesa(OPERACAO_AGRICOLA)`:
- `tests/test_operacao_despesa_webhook.py` — valida criação automática e ausência quando custo=0.
- `tests/test_operacao_reversao_economica.py` (04G) — valida neutralização no cancelamento.
- `tests/test_multi_up_hardening_step01.py` — valida `unidade_produtiva_id` correto na despesa gerada.
- `tests/test_operational_workflow_governance_step08.py` /
  `tests/test_operational_workflow_governance_step10.py` — validam os alertas de despesa automática
  duplicada/sem origem (seção 13).
- `tests/test_dre_agricola_v1.py` — valida exclusão condicional por precedência.
- `tests/test_dashboard_financeiro_safra.py` — não depende mais de `Despesa` para cálculo (04F), mas
  ainda cria despesas nos fixtures (não usadas no cálculo).

Execução:
```bash
.venv/bin/python -m pytest tests/test_operacao_despesa_webhook.py tests/test_operacao_reversao_economica.py \
  tests/test_dre_agricola_v1.py tests/test_dashboard_financeiro_safra.py tests/test_operacoes_validacao_fase.py \
  -q --tb=short
```
**Resultado: 42 passed, 3 failed** — as 3 falhas são as já documentadas (`receita_total`, poluição de
dados por `TENANT_A_ID` fixo entre testes de `test_dashboard_financeiro_safra.py`), não relacionadas
a `Despesa(OPERACAO_AGRICOLA)`, confirmadas idênticas ao baseline das etapas 04E–04G.

## 17. Respostas obrigatórias

1. **Representa obrigação financeira real?** Não — sem credor, sem pagamento, sem vencimento útil.
2. **Pode entrar em contas a pagar ou fluxo de caixa?** Não em "a pagar" (nasce `PAGO`); **sim** em
   fluxo de caixa pago (`total_pago_mes`), de forma indevida.
3. **Pode ser paga, baixada ou conciliada?** Tecnicamente sim pela tela financeira genérica (nenhum
   filtro impede), mas nunca é na prática pelo fluxo automático.
4. **É enviada ou consumida por ERP?** Não é enviada; teoricamente pesquisável por matching inbound,
   mas nunca casa na prática (sem NF).
5. **É usada pelo Campo PWA?** Não.
6. **Ainda é usada pela DRE?** Sim, como fallback implícito para operações sem `CostAllocation`
   (Cenário B).
7. **Ainda é usada pelo dashboard (agrícola)?** Não, desde 04F.
8. **É necessária para relatórios?** Sim, indiretamente e indevidamente: dashboard financeiro
   genérico e Livro Caixa/Carnê-Leão a leem sem filtro.
9. **É necessária para bloquear exclusão de tarefa?** Redundante para dados novos; ainda relevante
   para dados legados sem allocation.
10. **É necessária para alertas?** Sim, um alerta (`CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO`) depende
    dela ativamente hoje.
11. **`CostAllocation` substitui integralmente sua função econômica?** Sim, para o custo de produção;
    não substitui (nem deveria) qualquer papel financeiro, pois `CostAllocation` nunca teve esse papel.
12. **`OperacaoAgricola.custo_total` cobre fallback histórico?** Sim, para o dashboard (04F); não
    formalmente para a DRE (depende da despesa, Cenário B).
13. **Sua criação pode gerar duplicidade financeira?** Sim — infla `total_pago_mes` no dashboard
    financeiro genérico.
14. **Remover a criação é seguro para operações novas?** Seguro para DRE/dashboard agrícola
    (já usam `CostAllocation`); **não é seguro isoladamente** sem também corrigir o alerta
    `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO` e os testes dependentes.
15. **Dados antigos precisam ser alterados?** Não nesta etapa; recomenda-se avaliação de repair de
    dados em etapa futura, mas não é bloqueante para parar novas criações.

## 18. Alternativas comparadas

Ver tabela da seção 15. Alternativa **A** (remover criação, manter histórico) é a única que resolve a
poluição financeira identificada sem introduzir um modelo híbrido conceitualmente confuso (B, C, D).

## 19. Recomendação

**Direção recomendada: OPERACAO-DESPESA-A** — parar de criar `Despesa(OPERACAO_AGRICOLA)`, manter
dados antigos apenas por compatibilidade histórica.

Critérios do item 21 do plano, verificados:
- Não existe obrigação financeira real → confirmado (seção 3).
- Não existe pagamento legítimo → confirmado (seção 5).
- Não existe consumidor ERP → confirmado (seção 10).
- Não existe dependência do Campo → confirmado (seção 9).
- DRE e dashboard já usam `CostAllocation` → dashboard sim (04F); DRE parcialmente (fallback
  implícito ainda existe para dados sem allocation — seção 7, Cenário B).
- Bloqueios e alertas podem usar `CostAllocation` → parcialmente: bloqueio de tarefa sim para dados
  novos; **o alerta `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO` precisa ser reescrito antes**, não
  "pode" simplesmente passar a usar `CostAllocation` sem trabalho adicional.
- Histórico pode permanecer sem novas criações → sim, sem migration necessária.
- Remoção não quebra contrato público → confirmado (nenhuma rota pública expõe `despesa_id` da
  operação; Campo e frontend não dependem).

**Como nem todos os critérios estão 100% satisfeitos sem trabalho adicional** (alerta de governança e
testes dependentes precisam de ajuste concomitante), a recomendação é por uma **etapa intermediária
de implementação (04I)** que remova a criação **e** corrija o alerta/testes na mesma mudança — não
uma remoção isolada "big bang" sem tocar nos consumidores identificados.

## 20. Riscos

- **Alto, se ignorado:** remover a criação sem corrigir `_detectar_allocation_sem_reflexo_economico`
  gera alarme de `RISCO_ECONOMICO` para toda operação nova — regressão de governança visível.
- **Médio:** dados legados continuam poluindo `total_pago_mes`/Livro Caixa indefinidamente até uma
  eventual limpeza de dados — fora do escopo de "parar de criar".
- **Médio:** ~4 arquivos de teste precisam reescrita coordenada na etapa de implementação.
- **Baixo:** bloqueio de exclusão de tarefa para dados legados sem allocation depende da despesa
  continuar existindo (não é removida, apenas deixa de ser criada) — sem regressão, pois dados
  antigos não são tocados.
- **Baixo:** nenhuma migration, nenhum impacto em ERP, nenhum impacto no Campo PWA.

## 21. Veredicto

```
SOIL-PLAN-EXEC-04H
STATUS: GO COM RESSALVAS
```

```
DIREÇÃO RECOMENDADA:
OPERACAO-DESPESA-A
```

Ressalva principal: a remoção da criação (04I, se aprovada) deve ser feita **na mesma etapa** que:
(1) a correção/aposentadoria do alerta `CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO`
(`agricola/alertas/service.py`), e (2) a reescrita dos testes listados na seção 16 — não deve ser
tratada como uma remoção trivial de um único ponto de criação.
