# SOIL-PLAN-EXEC-04L0 — Auditoria e dry-run do reparo histórico de ProductionUnit e CostAllocation

Somente leitura. Nenhum INSERT/UPDATE/DELETE foi executado no banco real. Nenhuma ProductionUnit foi
criada. Nenhum código de produção, teste, model, schema ou migration foi alterado nesta etapa.

## 1. Resumo executivo

Conectividade com o PostgreSQL de dev/homologação (`192.168.0.2/farms`, somente SELECT) foi confirmada
(`SELECT 1` bem-sucedido via `psql`). A população real levantada nesta etapa é **maior** que a estimativa
de 04J: **151 operações `REALIZADA` com `custo_total > 0` sem `CostAllocation` válida** (verificando
ausência por **ambos** os vínculos históricos — `operation_execution_id` e `source_id`, conforme exigido
pela spec seção 5), contra os 103 estimados em 04J (que aparentemente checava só um dos vínculos ou uma
janela de dados diferente — divergência documentada, não reconciliada nesta etapa por estar fora de
escopo). Do total de 623 operações `REALIZADA` com custo>0 na base, 472 já possuem `CostAllocation` válida
(`SKIP_ALREADY_VALID`, fora do CSV de dry-run).

**Achado crítico não previsto na spec**: 47 dos 151 registros pertencem a um único tenant de teste
(`aaaaaaaa-0000-0000-0000-000000000010`) e a maioria dos 151 registros tem `data_realizada = 2026-07-21`
(data de execução desta auditoria) com valores redondos (`500.00`, `1000.00`, `2000.00`, `2500.00`) —
fortemente indicativo de **dados de fixture/teste gravados diretamente no banco de dev compartilhado**,
não histórico de negócio real. Isso não invalida a metodologia, mas exige cautela antes de qualquer
reparo real em 04L1: a população "histórica" está contaminada por execuções de teste concorrentes nesta
mesma janela de tempo.

**Veredicto desta etapa: GO COM RESSALVAS** — existe um conjunto seguro de reparo automático (1 caso),
mas a esmagadora maioria (150/151) exige revisão manual, principalmente por ausência de
`OperacaoExecucao` válida vinculada a uma `ProductionUnit` já presente (74 casos) ou por não existir
nenhuma `ProductionUnit` candidata (68 casos).

## 2. População analisada

Query-base (ver seção 15 para query completa): `operacoes_agricolas` com `status='REALIZADA'` e
`custo_total > 0`, tenant explícito em toda subquery, ausência de allocation checada via
`NOT EXISTS`-equivalente por `operation_execution_id` **e** `source_id`.

| Métrica | Valor |
|---|---|
| Operações `REALIZADA` com `custo_total > 0` (total na base) | 623 |
| ... com `CostAllocation` válida (por qualquer vínculo) | 472 |
| ... **sem** `CostAllocation` válida (população do dry-run) | **151** |
| Tenants distintos afetados | 103 tenants "reais" + 1 tenant de teste (47 registros) = 104 no total |

## 3. Distribuição por tenant

Agrupamento por `tenant_id` (UUID apenas, sem razão social — spec seção 6):

- **Tenant `aaaaaaaa-0000-0000-0000-000000000010`**: 47 operações, todas `MANUAL_MISSING_PU`, custo
  total R$ 308.500,00. Padrão de dados (data_realizada=hoje, valores redondos) sugere fixture de teste,
  não histórico de negócio.
- **Tenant `592b906e-0329-44df-8c58-80ca744ae243`**: 2 operações.
- **Demais 102 tenants**: 1 operação cada.
- Custo total dos 103 tenants "reais" (excluindo o tenant de teste): **R$ 56.060,00**.
- Custo total do tenant de teste: **R$ 308.500,00**.

Distribuição de categoria nos 103 tenants reais: `MANUAL_CONTEXT_INCONSISTENT`=74,
`MANUAL_MISSING_PU`=21, `MANUAL_REVERSED_OR_CANCELLED`=6, `MANUAL_VALUE_DIVERGENCE`=2, `AUTO_A`=1.

CSV completo com detalhamento por operação: `docs/implementation/reports/data/SOIL-PLAN-EXEC-04L0-DRYRUN.csv`.

## 4. Resolução de ProductionUnit

Reaplicada a mesma lógica determinística de `_resolve_production_unit_id`
(`services/api/agricola/operacoes/service.py:262-333`, aprovada em 04K): candidatas por
`tenant_id + safra_id + area_id (+ cultivo_id quando informado na operação)`; se múltiplas, reduz para
`status='ATIVA'`; se ainda múltiplas, ambíguo. Nenhuma decisão por `created_at`/`LIMIT 1`.

| Classificação | Contagem |
|---|---|
| Grupo A (`production_unit_id` presente, sem allocation) | 77 |
| Grupo B (ausente, única candidata determinística) | 0 |
| Grupo C (ausente, múltiplas candidatas — ambíguo) | 0 |
| Grupo D (ausente, nenhuma candidata) | 74 |
| Grupo E (allocation órfã/parcial) | 0 (nenhum caso — todos os 151 registros não têm allocation por
  nenhum dos dois vínculos; não há allocation parcial a considerar aqui) |

Nenhum caso de Grupo B ou C foi encontrado — isto é, entre os registros sem `production_unit_id`, nunca
havia exatamente uma ou múltiplas `ProductionUnit` já cadastrada para a combinação
`tenant+safra+área(+cultivo)`; sempre havia zero candidatas (Grupo D). Isso reforça a conclusão de 04J
seção 16: a resolução automática falha quando não há `ProductionUnit` pré-cadastrada, e não há bridge
`SafraTalhao → ProductionUnit`.

## 5. Execuções

| Classificação | Contagem |
|---|---|
| Execução válida (1 `OperacaoExecucao` REALIZADA, valor convergente) | 71 (77 do Grupo A menos 6
  reversões/canceladas) |
| Ausente (0 execuções REALIZADA) | 68 (todos no Grupo D, `MANUAL_MISSING_PU`) |
| Múltiplas execuções REALIZADA | 0 |
| PU divergente / órfã | 0 |
| Execução presente mas sem execução REALIZADA válida (todas canceladas/status≠REALIZADA) | 6 |
| Execução ausente mas PU presente (`MANUAL_CONTEXT_INCONSISTENT`) — combinação não coberta
  diretamente pela categoria "válida/ausente" acima porque a operação tem PU mas a checagem de
  execução falhou | 74 |

Nota de reconciliação: os 77 casos do Grupo A se dividem em 71 com exatamente 1 execução REALIZADA
válida (dos quais 1 é `AUTO_A`, 2 são `MANUAL_VALUE_DIVERGENCE` — ver seção 7 — e os demais foram
reclassificados como `MANUAL_CONTEXT_INCONSISTENT` por não terem execução REALIZADA no formato
esperado) e 6 com todas as execuções canceladas (`MANUAL_REVERSED_OR_CANCELLED`).

## 6. Estoque e FIFO

Nenhum dos 151 registros do dry-run possui movimento de `estoque_movimentos` vinculado
(`operacao_execucao_id`) com `tipo_movimento='SAIDA'` — `n_mov_estoque=0` em todos. Ou seja, o risco
"ALTO" descrito em 04J seção 11 (consumo físico de estoque sem apropriação econômica) **não se
materializa nesta população específica**: nenhuma dessas 151 operações consumiu insumo de estoque
rastreado por movimento; o custo é puramente operacional (mão de obra/serviço/maquinário, conforme
`operacoes_agricolas.custo_total` direto). Nenhum estorno/ajuste de estoque (`ajuste_de IS NOT NULL`)
encontrado nesta população. Portanto a coluna `risco` do CSV é `SEM_RISCO` para todos os 151 registros —
não há risco de duplicidade por movimento de estoque nesta população.

## 7. Definição de valor

Comparação `custo_total` (operação) vs soma de `custo_real` das execuções REALIZADA vs `custo_fifo`
(nulo em todos, seção 6):

- **VALOR-A (usar `custo_total`)**: aplicável nos 71 casos com exatamente 1 execução REALIZADA e
  `custo_real` igual a `custo_total` (convergência exata) — mas apenas 1 desses (`AUTO_A`) atende
  simultaneamente a todos os demais critérios da seção 15 da spec (ver seção 10 abaixo).
- **VALOR-D (revisão manual)**: 2 casos com **divergência real** entre `custo_total` e
  `custo_real`/soma das execuções — classificados `MANUAL_VALUE_DIVERGENCE`. Não foi aplicada nenhuma
  regra automática de "usar o maior" ou "usar o mais recente"; ambos exigem decisão humana.
- Não há casos VALOR-B (FIFO) ou VALOR-C (soma de componentes) nesta população (seção 6).

## 8. Duplicidades

Nenhum caso de `POSSIVEL_DUPLICIDADE` ou `DUPLICIDADE_CONFIRMADA` foi identificado: todos os 151
registros não têm allocation por nenhum dos vínculos (`operation_execution_id`, `source_id`), não têm
movimento de estoque associado (seção 6), e a checagem de allocations órfãs (`operation_execution_id IS
NULL` com `source_id` apontando para a mesma operação) não retornou casos adicionais além dos já
contabilizados. Risco de duplicidade: **SEM_RISCO** em 100% dos 151 registros.

## 9. Reversões

6 registros classificados `MANUAL_REVERSED_OR_CANCELLED`: todas as `OperacaoExecucao` vinculadas estão
com `status != 'REALIZADA'` (canceladas) — nenhuma execução ativa restante, apesar de
`operacoes_agricolas.status='REALIZADA'`. Conforme spec seção 13, estes **não** foram incluídos em
nenhuma categoria `AUTO_*`, mesmo tendo `production_unit_id` presente em alguns casos. Nenhum registro
com `origem_invalidada=true` foi encontrado nesta população (0 casos) — a checagem foi feita mas não
havia registros correspondentes.

## 10. Categorias automáticas

Apenas **1 registro** atende integralmente aos 12 critérios cumulativos da spec seção 15
(`AUTO_A`, tenant `ef90c72c-b8c1-4f14-b67b-8ef15aff75ef`, operação `175c09fb-9487-4669-b847-f57e13f91d57`):
`production_unit_id` já presente e válida (`f782fcc0-a89c-40f2-8baf-edcc2eacbb0a`), exatamente uma
`OperacaoExecucao` REALIZADA (`a0e29db2-a99e-4f65-b5a8-e9829d576223`), `custo_real=custo_total=R$500,00`
(inequívoco), sem movimento de estoque, sem allocation existente por nenhum vínculo, sem reversão,
sem ambiguidade de cultivo, tenant único. **AUTO_B e AUTO_C: 0 casos** — não houve nenhum registro sem
`production_unit_id` com exatamente uma candidata determinística (todo o Grupo B/C ficou vazio, seção 4).

## 11. Categorias manuais

| Categoria | Contagem | Motivo dominante |
|---|---|---|
| `MANUAL_CONTEXT_INCONSISTENT` | 74 | PU presente, mas sem `OperacaoExecucao` REALIZADA válida vinculada — origem do custo não rastreável sem decisão humana |
| `MANUAL_MISSING_PU` | 68 | Nenhuma `ProductionUnit` candidata (47 no tenant de teste, 21 em tenants reais) |
| `MANUAL_REVERSED_OR_CANCELLED` | 6 | Todas as execuções vinculadas estão canceladas |
| `MANUAL_VALUE_DIVERGENCE` | 2 | `custo_total` diverge do `custo_real` da execução |
| **Total manual** | **150** | |

Nenhum `MANUAL_AMBIGUOUS_PU` ou `MANUAL_MULTIPLE_EXECUTIONS` ocorreu nesta população (seção 4/5).
`MANUAL_POSSIBLE_DUPLICATE` também não ocorreu (seção 8).

## 12. Impacto estimado na DRE

Simulação (não executada): para o único caso `AUTO_A`, hoje a operação está **ausente da DRE**
(seção 9 de 04J: DRE constrói escopo só a partir de `ProductionUnit` com `CostAllocation`). Após reparo
real (04L1), a `CostAllocation` de R$500,00 passaria a ser reconhecida na `ProductionUnit
f782fcc0-a89c-40f2-8baf-edcc2eacbb0a` (safra `b6a40764-f63d-405f-8685-1c23a2cd02a6`), incrementando o
custo total daquela PU/safra em exatamente R$500,00 — impacto pontual e imaterial isoladamente. Para os
150 casos manuais, nenhuma simulação de impacto foi calculada (dependem de decisão humana sobre valor e
PU — spec seção 21 não permite propor regra sem análise caso a caso já concluída).
Valor total potencialmente recuperável para a DRE, se todos os 150 manuais forem eventualmente
resolvidos e reparados: R$ 364.060,00 - R$500,00 = R$ 363.560,00 (majoritariamente concentrado no tenant
de teste, R$ 308.500,00 — ver ressalva na seção 17).

## 13. Impacto no dashboard

Confirmado por leitura de código (`agricola/dashboard/service.py:236-253`, sem execução): o fallback já
opera por `operacao_id` individual — quando a allocation agregada por operação não existe no mapa, usa
`op.custo_total`; quando existir (pós-reparo), a allocation **substitui** o fallback, não soma
(a chave do mapa é `operacao_id`, não há acumulação dupla). Portanto o reparo do caso `AUTO_A` (e de
qualquer caso manual futuro) **não introduz duplicidade no dashboard** — a métrica agregada de custo já
está correta hoje via fallback; o reparo apenas adiciona a dimensão de `ProductionUnit`/rastreabilidade
que falta atualmente, sem alterar o valor total exibido no dashboard.

## 14. Artefatos gerados

1. `docs/implementation/reports/SOIL-PLAN-EXEC-04L0-AUDITORIA-DRYRUN-REPARO-HISTORICO.md` (este arquivo)
2. `docs/implementation/reports/data/SOIL-PLAN-EXEC-04L0-DRYRUN.csv` (151 linhas + header, uma por
   operação, colunas conforme spec seção 17)
3. `docs/implementation/reports/data/SOIL-PLAN-EXEC-04L1-PLANO-REPARO.sql` (gerado, **não executado**)

Nenhum outro arquivo foi criado ou alterado.

## 15. SQL futuro

Ver `docs/implementation/reports/data/SOIL-PLAN-EXEC-04L1-PLANO-REPARO.sql`. Contém 1 bloco de
`INSERT INTO cost_allocations` (para o caso `AUTO_A`) dentro de `BEGIN;...ROLLBACK;` (sem `COMMIT`),
com precondições fortes (`WHERE id=... AND tenant_id=... AND status='REALIZADA' AND custo_total>0 AND
production_unit_id=...`) e `NOT EXISTS` cobrindo `operation_execution_id`, `source_id` e `tenant_id`,
mais uma checagem adicional de que ainda existe exatamente uma execução REALIZADA (proteção contra
mudança de estado entre o dry-run e a execução real). Os 150 casos manuais aparecem apenas como
comentário de referência — nenhum DML foi gerado para eles, conforme spec seção 20 (proibição de
criação implícita insegura de `ProductionUnit` e proibição de reparo automático de casos ambíguos).

Query-base utilizada para a população (equivalente à executada via `psql`):
```sql
SELECT oa.tenant_id, oa.id AS operacao_id, oa.safra_id, oa.talhao_id, oa.cultivo_id,
       oa.production_unit_id, oa.custo_total, oa.data_realizada, oa.status, oa.tipo,
       oa.origem_invalidada
FROM operacoes_agricolas oa
WHERE oa.status = 'REALIZADA' AND oa.custo_total > 0
  AND NOT EXISTS (
        SELECT 1 FROM cost_allocations ca
        WHERE ca.tenant_id = oa.tenant_id
          AND (
                ca.operation_execution_id IN (
                    SELECT oe.id FROM operacoes_execucoes oe WHERE oe.operacao_id = oa.id
                )
                OR ca.source_id = oa.id
          )
  )
ORDER BY oa.tenant_id, oa.data_realizada;
```

## 16. Testes

Executado (somente leitura, sem alteração de código):
```
tests/test_operacao_production_unit_enforcement.py tests/test_operacao_reversao_economica.py
tests/test_dre_agricola_v1.py tests/test_dashboard_financeiro_safra.py
```
Resultado: **41 passed, 3 failed** — as 3 falhas são as pré-existentes documentadas em 04K seção 16
(`test_dashboard_financeiro_safra.py`: `test_resumo_financeiro_safra_valido`,
`test_resumo_financeiro_safra_sem_operacoes`, `test_resumo_roi_calculado`), poluição de fixture de
tenant compartilhado — não corrigidas, fora de escopo desta etapa.

`git status --short` e `git diff --check` a partir da raiz do repo confirmam: nenhum arquivo de código
foi alterado por esta etapa. Os arquivos modificados listados (`services/api/agricola/...`,
`services/api/tests/...`) e os `.md` novos de 04E-04J já existiam na árvore antes desta tarefa
(alterações de 04E-04K, explicitamente preservadas conforme instrução). Os únicos itens novos
introduzidos por esta etapa são os 3 arquivos listados na seção 14 (o `.md` deste relatório e os 2
arquivos dentro de `docs/implementation/reports/data/`, diretório também novo). `git diff --check`
retornou vazio (sem conflitos/whitespace).

## 17. Riscos

- **Contaminação de dados de teste no banco de dev compartilhado**: 47/151 registros (31%) pertencem a
  um tenant com padrão de UUID de fixture (`aaaaaaaa-0000-0000-0000-000000000010`) e a maioria dos 151
  registros tem `data_realizada` = data desta auditoria, com valores redondos — forte indício de que
  parte relevante da "dívida histórica" é, na verdade, ruído de execução de testes de integração contra
  este mesmo banco, não histórico de negócio real. Antes de 04L1, recomenda-se filtrar/confirmar quais
  tenants são de fato produção.
- **Divergência de contagem vs. 04J** (151 aqui vs. 103 lá): não reconciliada nesta etapa. Pode ser
  explicada por 04J checar só um dos dois vínculos de allocation, por diferença de data de corte, ou por
  novos registros inseridos entre as duas auditorias (dado o ponto acima, provável).
  Investigação de causa raiz fica fora do escopo de 04L0.
- **Ausência de dados FIFO/estoque na população não é garantia de ausência de risco em geral** — apenas
  confirma que, especificamente para estes 151 registros, não há esse vetor de risco.
- **`MANUAL_CONTEXT_INCONSISTENT` (74 casos) é a maior categoria e a mais heterogênea**: agrupa PU
  presente sem execução válida — pode esconder subcasos distintos (execução nunca criada vs. execução
  removida por reversão parcial) que mereceriam subclassificação adicional em uma futura iteração antes
  de 04L1 decidir caso a caso.

## 18. Recomendação

Prosseguir para **SOIL-PLAN-EXEC-04L1** apenas com o escopo do 1 caso `AUTO_A` identificado, executando
o SQL gerado (removendo `ROLLBACK`/trocando por `COMMIT` só após revisão humana e reconfirmação de
estado). Os 150 casos `MANUAL_REVIEW` devem ser tratados em lotes por categoria (começando por
`MANUAL_VALUE_DIVERGENCE`, que é o menor e mais objetivo, e `MANUAL_MISSING_PU` fora do tenant de teste,
21 casos reais), com decisão de negócio documentada individualmente conforme regra final da spec.
Antes de qualquer reparo em tenants reais, confirmar com o time de produto se
`aaaaaaaa-0000-0000-0000-000000000010` é de fato um tenant de teste a ser excluído do escopo de reparo
histórico (não simplesmente ignorado — precisa de decisão explícita).

## 19. Decisão final

```
SOIL-PLAN-EXEC-04L0
STATUS: GO COM RESSALVAS
AUTO_REPAIR_COUNT: 1
MANUAL_REVIEW_COUNT: 150
SKIP_COUNT: 472 (operações REALIZADA+custo>0 que já possuem CostAllocation válida)
TOTAL_COST_AUTO: R$ 500,00
TOTAL_COST_MANUAL: R$ 364.060,00 (R$ 308.500,00 em tenant de teste suspeito; R$ 55.560,00 em tenants
                    presumivelmente reais)
```

**REGRA FINAL (reafirmada)**: nenhum dado histórico foi alterado nesta etapa. O SQL de reparo gerado em
`SOIL-PLAN-EXEC-04L1-PLANO-REPARO.sql` está pronto para revisão, mas **não foi executado** (todos os
blocos terminam em `ROLLBACK`). Nenhuma `ProductionUnit` foi criada.

**PRÓXIMO PASSO (não executado agora)**: SOIL-PLAN-EXEC-04L1 — execução controlada do reparo histórico,
por tenant, transacional, começando pelo caso `AUTO_A` único, com validação de contagens antes/depois,
rollback possível, evidências registradas, sem criar PU ambígua, sem reparar casos manuais
automaticamente, e com decisão explícita sobre o tenant de teste identificado na seção 17.

---

## Validação de escopo (somente leitura)

```
git status --short   # deve mostrar apenas os 3 artefatos desta etapa como novos, além do que já
                      # estava modificado/novo por 04E-04K (preservado, não tocado)
git diff --check     # sem conflitos/whitespace em arquivos de código (confirmado vazio)
```
