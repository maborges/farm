# MATERIAL-REQUISITION-FLOW-01G — Apropriação Econômica do Consumo Real

Data: 2026-09-26
Ambiente: PostgreSQL real de desenvolvimento/teste; nenhuma prova utilizou produção.

## 1. Resumo executivo

Foi implementada a apropriação econômica do consumo canônico sem criar estoque ou arquitetura financeira paralela.

OperacaoAgricola → OperacaoExecucao → CostAllocation → DRE / Dashboard

A entrega física continua sendo a única saída. Recebimento, consumo, perda, dano e extravio não criam nova saída; somente devolução cria entrada física.

O consumo é apropriado pela quantidade efetivamente consumida e pelo custo unitário do movimento de entrega exato. Veredicto: GO COM RESSALVAS, pois perda, dano e extravio ainda não possuem classificação econômica canônica própria no fluxo de requisição. Esses fatos não são convertidos em consumo.

## 2. Arquitetura auditada

Evidências:

- services/api/agricola/operacoes/models.py — OperacaoAgricola e OperacaoExecucao.
- services/api/agricola/custos/models.py — CostAllocation.
- services/api/agricola/dre/service.py — consolidação por ProductionUnit.
- services/api/agricola/dashboard/service.py — custo realizado.
- services/api/agricola/custos/allocation_service.py — porta oficial.
- services/api/events/outbox_service.py, outbox_relay.py e publisher.py — Outbox.

Não foi criada tabela econômica paralela nem integração direta Campo → DRE.

## 3. Matriz econômica

| Fato | Estoque físico | Efeito econômico |
|---|---:|---|
| ENTREGA | saída | nenhum custo definitivo |
| RECEBIMENTO | nenhum | nenhum |
| CONSUMO | nenhum | CostAllocation REQUISICAO_CONSUMO |
| DEVOLUCAO | entrada | nenhum novo custo |
| PERDA | nenhum | classificação própria pendente |
| DANO | nenhum | fato separado, não consumo |
| EXTRAVIO | nenhum | fato separado, não consumo |

## 4. Implementação do consumo

MaterialConsumptionCostService, em services/api/agricola/custos/material_consumption_service.py, valida tenant, evento canônico, OperacaoExecucao, operação de origem, ProductionUnit, entrega exata e movimento SAIDA com custo unitário.

O cálculo usa Decimal:

valor_apropriado = quantidade_do_evento × custo_unitario_do_movimento_de_entrega

A alocação grava source REQUISICAO_CONSUMO, source_id, requisicao_item_evento_id, operation_execution_id, production_unit_id, categoria INSUMO e a quantidade em allocation_basis.

MaterialConsumptionCostSubscriber, em services/api/agricola/custos/material_consumption_subscriber.py, consome somente operational.material_request.consumo. Não há subscriber econômico para entrega, recebimento, devolução, perda, dano ou extravio.

## 5. Idempotência e concorrência

A migration 20260926_material_requisition_01g adiciona:

- requisicao_item_evento_id em CostAllocation;
- FK composta tenant-safe para RequisicaoItemEvento;
- UNIQUE tenant_id + requisicao_item_evento_id;
- REQUISICAO_CONSUMO ao CHECK de source.

O serviço retorna a alocação existente. Em corrida, o conflito da constraint é tratado e retorna o fato existente.

## 6. Proteção contra dupla apropriação

Em services/api/agricola/operacoes/service.py:

- a busca da alocação agregada filtra source OPERATION_EXECUTION;
- a alocação agregada desconta REQUISICAO_CONSUMO já apropriado para a execução;
- materiais canônicos não são somados novamente no agregado legado.

O caminho canônico de entrega não chama o lançamento financeiro legado de estoque. Rotas históricas/manualizadas permanecem compatíveis, mas não são escritoras do consumo canônico novo.

## 7. Custo unitário, lote e execução

O consumo não executa FIFO nem consulta saldo genérico. Segue evento_entrega_id até o EstoqueMovimento SAIDA exato. Esse movimento preserva lote/origem e custo unitário definidos na entrega.

Todo consumo exige OperacaoExecucao compatível com a OperacaoAgricola de origem e o mesmo tenant. Múltiplas requisições para uma execução permanecem diferenciadas por item e evento.

## 8. DRE e Dashboard

DREAgricolaV1Service._consolidar_costs consolida REQUISICAO_CONSUMO como custo operacional. DashboardAgricolaService.resumo_financeiro_safra usa CostAllocation como fonte primária por operação. O método executivo resumo também foi alinhado à mesma precedência, com fallback para OperacaoAgricola.custo_total somente quando não houver allocation.

## 9. Cenários reais

Teste: services/api/tests/integration/operacional/test_requisicao_custo_01g_integration.py.

Cenário principal:
- entrega = 100 kg;
- recebimento = 100 kg;
- consumo = 80 kg;
- custo unitário controlado = R$ 5,00/kg.

Resultado:
- entrega: 0 CostAllocation;
- recebimento: 0 CostAllocation;
- consumo 80: 1 allocation de R$ 400,00;
- devolução: 0 nova apropriação;
- DRE: fonte REQUISICAO_CONSUMO = R$ 400,00;
- Dashboard: custo realizado inclui a allocation.

O cenário 01B com entregue=100, recebido=92 e divergência 8 permanece bloqueado pelo 01F até resolução da divergência; não foi fabricado consumo para os 8 não recebidos.

Consumos parciais:
- consumo 1 = 30 kg;
- consumo 2 = 20 kg;
- custo unitário = R$ 5,00/kg;
- 2 eventos, 2 allocations, total de R$ 250,00.

Retornável 01F1:
- 3 recebidos;
- 2 devolvidos;
- 1 danificado;
- consumo = 0;
- tentativa de consumo rejeitada.

## 10. Perda, dano e extravio

O domínio operacional diferencia os três fatos. Existe o caminho legado PERDA_ESTOQUE para ajustes/perdas de estoque com contexto próprio, mas não existe ainda contrato econômico completo para fatos de posse do novo fluxo de requisição.

Classificação: PARCIAL.

Regra aplicada:
- PERDA/DANO/EXTRAVIO: fato operacional separado;
- CONSUMO econômico: somente evento CONSUMO.

Recomenda-se um 01G1 para decidir categoria, conta e impacto econômico de perda, dano e extravio. Isso não bloqueia a apropriação do consumo canônico.

## 11. Devolução e histórico

Devolução gera entrada física no fluxo 01F, mas não novo CostAllocation de consumo nem estorno automático nesta fase. O subscriber econômico só escuta consumo.

A migration 01G é estrutural: não há backfill, eventos históricos, CostAllocation retroativo, recálculo de DRE ou inferência de consumo legado.

## 12. Migration e validações

Migration: services/api/migrations/versions/20260926_material_requisition_01g.py.

- upgrade 01E → 01G: PASS;
- downgrade 01G → 01E: PASS;
- upgrade 01E → 01G novamente: PASS;
- Alembic current: 20260926_material_requisition_01g (head).

Testes:
- 01G PostgreSQL real: 2 passed;
- regressão real 01D2 + 01E + 01F + 01F1: 7 passed;
- 01F1 PostgreSQL real dedicado: 3 passed;
- unitários 01C/01D/01E/01F + registry: 30 passed;
- app import e subscriber registrado: PASS;
- py_compile: PASS;
- git diff --check: PASS.

O lint dos arquivos novos 01G e do teste econômico passa. Há pendências de lint preexistentes nos grandes serviços legados de operação/dashboard; os arquivos afetados foram compilados e as regressões diretamente relacionadas passaram.

## 13. Riscos

- MEDIUM: perda/dano/extravio precisam de classificação econômica própria; não devem ser lançados como consumo.
- MEDIUM: rotas financeiras legadas/manualizadas permanecem compatíveis e devem ser cobertas pelo cutover final.
- LOW: CostAllocation aparece após processamento eventual da Outbox; falhas são recuperáveis por retry.

## 14. Respostas obrigatórias

A. O fato gerador é RequisicaoItemEvento com tipo CONSUMO.
B. Entrega não gera custo definitivo.
C. Recebimento não gera custo.
D. Devolução gera entrada física, não novo custo nem estorno automático.
E. O custo vem do EstoqueMovimento SAIDA exato da entrega.
F. Lote/origem são preservados pelo evento de entrega e movimento referenciados.
G. Consumo liga-se a OperacaoExecucao e valida a operação e o tenant.
H. CostAllocation liga-se ao evento por requisicao_item_evento_id e source_id.
I. Retry não duplica custo; foi validado no PostgreSQL real.
J. Workers concorrentes não duplicam pela unicidade tenant/evento e pelo tratamento do conflito.
K. Falha econômica mantém o fato operacional e permite retry pela Outbox.
L. Perda não é consumo; classificação própria permanece pendente.
M. Dano é fato separado, sem consumo econômico automático.
N. Extravio é fato separado, sem consumo econômico automático.
O. Retornável não aparece como consumo econômico.
P. Não foi detectado escritor paralelo no caminho canônico; há ressalva de cutover legado.
Q. Histórico não foi recalculado.
R. DRE e Dashboard refletem o custo canônico; foram exercitados/auditados no teste real.
S. Não há BLOCKING/HIGH para consumo canônico; há ressalvas MEDIUM para perda/dano/extravio e cutover legado.

## 15. Veredicto

O 01G está pronto para a validação final e cutover controlado do consumo canônico. A ressalva de perda/dano/extravio deve permanecer explícita e não pode ser resolvida classificando esses fatos como consumo.

~~~text
MATERIAL-REQUISITION-FLOW-01G
STATUS: GO COM RESSALVAS

CONSUMO REAL → COSTALLOCATION:
PASS

ENTREGA/RECEBIMENTO SEM APROPRIAÇÃO:
PASS

DEVOLUÇÃO SEM DUPLA APROPRIAÇÃO:
PASS

CUSTO UNITÁRIO CANÔNICO:
PASS

IDEMPOTÊNCIA ECONÔMICA:
PASS

PERDA/DANO/EXTRAVIO:
PARCIAL

RETORNÁVEL SEM CONSUMO ECONÔMICO:
PASS

DRE/DASHBOARD:
PASS

DUPLA APROPRIAÇÃO LEGADO/CANÔNICO:
NÃO

HISTÓRICO RECALCULADO:
NÃO

AUTORIZAÇÃO PARA 01H:
SIM

PRÓXIMA FASE:
MATERIAL-REQUISITION-FLOW-01H — Validação Final E2E, Cutover e Encerramento
~~~
