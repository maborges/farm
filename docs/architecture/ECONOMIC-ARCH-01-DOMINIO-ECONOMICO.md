# ECONOMIC-ARCH-01 — Domínio Econômico do AgroSaaS

## 1. Resumo executivo

Conclusão objetiva: o AgroSaaS já possui uma arquitetura econômica oficial parcialmente implementada, mas ela ainda não é a única arquitetura em execução na codebase.

O núcleo oficial atual é:

```text
Receita operacional  -> Receita
Despesa/obrigação    -> Despesa
Custo operacional    -> CostAllocation
DRE agrícola oficial -> agricola.dre.v1
Rentabilidade oficial -> agricola.rentabilidade.v1
Caixa/previsto       -> RelatorioService (Receita/Despesa)
```

O problema é que ainda coexistem caminhos paralelos relevantes:

- `financeiro.services.lancamento_service.gerar_dre()` mantém uma DRE legada baseada só em `LancamentoFinanceiro`.
- `operacional.services.estoque_service._criar_lancamento_insumo()` ainda gera custo em `LancamentoFinanceiro` a partir de estoque.
- `agricola.custos.service.CustosService.get_resumo_safra()` faz fallback para `OperacaoAgricola.custo_total` quando não encontra `CostAllocation`.
- `agricola.romaneios.service.RomaneioService.criar()` gera `Receita` automática em romaneio.
- `financeiro.comercializacao.service.ComercializacaoService._gerar_receita()` também gera `Receita` automática na comercialização.
- `pecuaria.services.manejo_service.ManejoLoteService` cria `Despesa` e `Receita` diretamente para alguns manejos, sem passar pelo motor oficial de custo operacional.
- `financeiro/hedge` calcula exposição e MTM, mas ainda não integra o resultado ao fluxo econômico oficial.

Classificação final: **Modelo C**.

Existe um desenho oficial claro para o lançamento, mas ainda existem caminhos paralelos relevantes demais para afirmar que a plataforma já opera sob uma arquitetura econômica única.

## 2. Escopo auditado

Backend auditado:

- `services/api/financeiro/`
- `services/api/agricola/custos/`
- `services/api/agricola/dre/`
- `services/api/agricola/rentabilidade/`
- `services/api/agricola/operacoes/`
- `services/api/operacional/`
- `services/api/rh/`
- `services/api/pecuaria/`
- `services/api/agricola/romaneios/`
- `services/api/financeiro/comercializacao/`
- `services/api/financeiro/hedge/`

Frontend auditado:

- `apps/web/src/app/(dashboard)/dashboard/financeiro/`
- `apps/web/src/app/(dashboard)/dashboard/agricola/`
- `apps/web/src/app/(dashboard)/dashboard/pecuaria/`
- `apps/web/src/app/(dashboard)/operacional/`
- `apps/web/src/app/(dashboard)/suprimentos/`

Testes auditados:

- `services/api/tests/test_launch_core01_operational_cost_engine.py`
- `services/api/tests/integration/agricola/test_dre_v1_endpoint.py`
- `services/api/tests/unit/operacional/test_compras_financeiro_integration.py`
- `services/api/tests/test_estoque_financeiro_step138.py`
- `services/api/tests/integration/agricola/test_beneficiamento_qualidade.py`
- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
- além de guardrails correlatos em `test_operational_workflow_governance_*`, `test_operacao_despesa_webhook.py`, `test_dashboard_financeiro_safra.py` e testes de pecuária/frota.

## 3. Inventário econômico

| Conceito | Model/Service | Owner | Fonte oficial? | Consumidores | Risco |
| --- | --- | --- | ---: | --- | --- |
| Receita | `financeiro.models.receita.Receita`, `ReceitaService` | Financeiro | Sim | Fluxo de caixa, livro caixa, DRE agrícola v1, dashboards financeiros | Alto quando coexistem romaneio e comercialização |
| Despesa | `financeiro.models.despesa.Despesa`, `DespesaService` | Financeiro | Sim | Fluxo de caixa, livro caixa, DRE agrícola v1, centro de custos | Alto quando coexistem despesa e cost allocation da mesma origem |
| PlanoConta | `financeiro.models.plano_conta.PlanoConta` | Financeiro | Sim | Receita, despesa, relatórios, integrações automáticas | Médio por fallback silencioso em fluxos automáticos |
| Centro de Custo | `RelatorioService.centro_custos()` sobre `Rateio` | Financeiro / Relatórios | Não, é agregação | UI `/dashboard/financeiro/custos` | Médio, porque não é entidade de verdade oficial |
| CostAllocation | `agricola.custos.models.CostAllocation`, `registrar_cost_allocation()` | Agrícola Custos | Sim | DRE agrícola v1, rentabilidade, diagnósticos, alertas, pecuária sanitária | Crítico se faltar ou duplicar |
| OperationalCostService | `OperationalCostAllocationService` | Agrícola Custos | Sim, para novos custos operacionais | Frota, RH, apontamento de frota | Médio, porque não cobre todos os módulos ainda |
| DRE | `agricola.dre.service.DREAgricolaV1Service` | Agrícola / Econômico | Sim para DRE agrícola oficial | UI agrícola, rentabilidade, prioridades, recomendações | Alto por convivência com DRE legada |
| Rentabilidade | `agricola.rentabilidade.service.RentabilidadeAgricolaV1Service` | Agrícola / Analítico | Sim | UI agrícola, diagnósticos, prioridades | Baixo no serviço; alto na adoção por existirem cálculos paralelos |
| Fluxo de Caixa | `financeiro.services.relatorio_service.RelatorioService.fluxo_caixa()` | Financeiro | Sim para caixa via Receita/Despesa | UI `/dashboard/financeiro/fluxo-caixa` | Médio, pois convive com `LancamentoFinanceiro` |
| ProdutoColhido | `agricola.colheita.models.ProdutoColhido` | Agrícola Colheita | Sim como lastro físico | Comercialização, hedge, beneficiamento, rastreabilidade | Médio se tratado como receita |
| Comercialização | `financeiro.comercializacao.models.ComercializacaoCommodity`, `ComercializacaoService` | Financeiro Comercialização | Sim como fato comercial | Receita, hedge, UI comercialização | Médio por precedência com romaneio |
| EstoqueMovimento | `operacional.models.estoque.EstoqueMovimento`, `EstoqueService` | Operacional Estoque | Sim como trilha física/valuation | Estoque, FIFO, reconciliação DRE, compras, pecuária | Alto se consumido como custo final |
| Compras | `operacional.models.compras.*`, `ComprasService` | Operacional Compras | Parcial | Estoque, despesa, analytics de savings | Alto por múltiplas fases do mesmo fato |
| RH | `rh.models.*`, `rh.service.*` | RH | Parcial | CostAllocation, Despesa, dashboards RH | Médio, porque diária/empreitada já usam motor oficial, mas não todo RH |
| Frota | `operacional.services.frota_*`, `AbastecimentoService`, `FrotaService` | Operacional Frota | Parcial | CostAllocation, Despesa, dashboards executivos de frota | Alto por analytics paralelos sobre custo bruto |
| Hedge | `financeiro.hedge.*` | Financeiro Hedge | Não para DRE/caixa; sim para exposição/MTM | UI hedge, snapshots, alertas de risco | Médio, porque ainda está fora da cadeia econômica oficial |
| Pecuária | `pecuaria.services.*` | Pecuária | Parcial | Despesa/Receita, CostAllocation sanitário, dashboards | Alto por caminhos mistos e sem precedência uniforme |

## 4. Fontes oficiais identificadas

### 4.1 Receita

Fonte oficial definida: **`Receita`**.

Regra oficial:

- receita operacional nasce em `Receita`;
- comercialização confirmada gera `Receita` automática com `origem_tipo="COMERCIALIZACAO"`;
- romaneio com `receita_total > 0` gera `Receita` automática com `origem_tipo="ROMANEIO_COLHEITA"`;
- receita manual via financeiro também cai em `Receita`;
- hedge não gera `Receita` oficial hoje;
- `LancamentoFinanceiro` não é a fonte oficial de receita operacional.

Situação real:

- `agricola.dre.v1` já aplica precedência: comercialização ganha de romaneio na mesma `ProductionUnit`;
- ainda assim, a codebase permite duas receitas operacionais do mesmo ciclo produtivo coexistirem;
- pecuária cria `Receita` direta em `ManejoLoteService` para `VENDA` e `ABATE`, fora do fluxo agrícola/comercialização.

Decisão:

- **fonte oficial de receita = `Receita`**;
- `RomaneioColheita` e `ComercializacaoCommodity` são origens possíveis da `Receita`, não fontes concorrentes;
- `LancamentoFinanceiro` é apenas trilha financeira legada/reconciliação.

### 4.2 Despesa

Fonte oficial definida: **`Despesa`**.

Regra oficial:

- obrigação financeira nasce em `Despesa`;
- compras geram `Despesa` automática `A_PAGAR` no recebimento;
- RH/frota/abastecimento/OS podem gerar `Despesa` automática;
- pecuária ainda gera `Despesa` direta em alguns manejos;
- `LancamentoFinanceiro` não é a fonte oficial da despesa operacional.

Decisão:

- **fonte oficial de despesa = `Despesa`**;
- `Rateio` distribui `Despesa`, não substitui `Despesa`;
- `LancamentoFinanceiro` permanece como camada legada/financeira, não obrigação primária.

### 4.3 Custo operacional

Fonte oficial definida: **`CostAllocation`**.

Regra oficial:

- custo operacional apropriado por safra/PU nasce em `CostAllocation`;
- `OperationalCostAllocationService` é a camada oficial para novos custos operacionais;
- `EstoqueMovimento`, `Despesa`, `Rateio` e `OperacaoExecucao` são insumos/origens, não custo final consolidado.

Decisão:

- **fonte oficial de custo operacional = `CostAllocation`**;
- `Despesa` não é custo operacional oficial quando já existir `CostAllocation`;
- `OperationalCostService` é o gateway recomendado, mas a entidade oficial persistida continua sendo `CostAllocation`.

## 5. Perguntas obrigatórias

### 5.1 Qual é a fonte oficial de Receita?

**`Receita`.**

Mapa auditado:

- romaneio: cria `Receita` estimada/automática;
- comercialização: cria `Receita` confirmada;
- financeiro manual: cria `Receita` manual;
- hedge: não cria receita oficial hoje;
- outras origens: pecuária cria `Receita` direta para venda/abate.

Precedência operacional atual:

- comercialização > romaneio na `DRE agrícola v1`;
- romaneio sem comercialização ainda entra como receita;
- `LancamentoFinanceiro` não substitui a fonte oficial.

### 5.2 Qual é a fonte oficial de Despesa?

**`Despesa`.**

Mapa auditado:

- compras: gera `Despesa` automática `A_PAGAR`;
- estoque: gera `LancamentoFinanceiro` legado, não `Despesa` oficial;
- RH: diária/empreitada usam `OperationalCostService` e podem criar `Despesa`;
- frota/manutenção/abastecimento externo: usam `OperationalCostService` e podem criar `Despesa`;
- operações agrícolas: ainda criam `Despesa` automática direta com `origem_tipo="OPERACAO_AGRICOLA"`;
- pecuária: vacinação/medicação geram `Despesa` direta em serviço legado.

### 5.3 Qual é a fonte oficial de custo operacional?

**`CostAllocation`.**

`OperationalCostAllocationService` é a porta de entrada recomendada para novos fluxos, mas o dado oficial persistido e consolidado é `CostAllocation`.

### 5.4 DRE consome o quê?

#### DRE agrícola oficial

`agricola.dre.v1` consome:

- `Receita` como receita operacional;
- `CostAllocation` como custo direto e custo operacional;
- `Despesa` apenas quando não houver camada econômica superior;
- `LancamentoFinanceiro` e `EstoqueMovimento` apenas para reconciliação;
- `ComercializacaoCommodity`, `ProdutoColhido` e `RomaneioColheita` só para rastrear origem da `Receita`.

#### DRE financeira legada

`financeiro.services.lancamento_service.gerar_dre()` consome:

- apenas `LancamentoFinanceiro`.

Conclusão:

- a DRE oficial já existe;
- a DRE legada ainda está ativa no produto.

### 5.5 Rentabilidade consome o quê?

**Somente `DREAgricolaV1Service`.**

`RentabilidadeAgricolaV1Service` deriva toda a leitura de margem da DRE agrícola v1 e de KPIs físicos auxiliares. Isso está correto e é o melhor alinhamento da codebase.

### 5.6 Existe risco de dupla contagem?

**Sim, ainda existe.**

Principais pontos:

- `Despesa` + `CostAllocation` da mesma origem operacional;
- compra + recebimento + estoque + despesa;
- romaneio + comercialização;
- RH legado + despesa automática;
- frota abastecimento/OS + despesa + allocation;
- estoque -> `LancamentoFinanceiro` legado + `CostAllocation` em fluxos novos;
- pecuária sanitária com leituras mistas entre `Despesa` direta e `CostAllocation`.

### 5.7 Existe caminho paralelo de custo?

**Sim.**

Principais caminhos paralelos encontrados:

- `LancamentoFinanceiro` de estoque (`origem="ESTOQUE"`);
- fallback `OperacaoAgricola.custo_total` em `CustosService.get_resumo_safra()`;
- dashboards de frota consolidados a partir de abastecimentos/OS/registros brutos;
- `ManejoLoteService` na pecuária criando `Despesa` sem `CostAllocation`;
- custos diretos de operação agrícola ainda gerando `Despesa` separada do custo apropriado.

### 5.8 Existe caminho paralelo de receita?

**Sim.**

Principais caminhos:

- `ROMANEIO_COLHEITA` gera `Receita`;
- `COMERCIALIZACAO` gera `Receita`;
- pecuária cria `Receita` direta em venda/abate;
- DRE financeira legada e resumos baseados em `LancamentoFinanceiro` podem produzir leitura paralela.

### 5.9 Plano de Contas é obrigatório onde deveria?

**No nível de `Receita` e `Despesa`, sim. No nível de integração automática, ainda não de forma totalmente rígida.**

Estado auditado:

- receita manual: obrigatório;
- despesa manual: obrigatório;
- compras: resolve automaticamente `PlanoConta`;
- comercialização: tenta resolver `PlanoConta`; se não encontrar, não quebra o fluxo e não cria a `Receita`;
- RH: usa `OperationalCostService`, que tenta resolver `PlanoConta`;
- frota: usa `OperationalCostService`, que tenta resolver `PlanoConta`;
- pecuária: busca `PlanoConta` antes de criar `Receita`/`Despesa`.

Conclusão:

- o modelo exige `PlanoConta`;
- algumas integrações automáticas ainda degradam silenciosamente quando a infraestrutura financeira não está pronta.

### 5.10 Centro de Custo é entidade oficial ou agregação?

**Agregação.**

No código, centro de custo não é uma entidade econômica oficial própria.

Hoje ele é derivado de:

- `Despesa` paga;
- `Rateio`;
- agrupamento por `(safra_id, talhao_id)` em `RelatorioService.centro_custos()`.

Logo:

- centro de custo é **visão analítica/agregada**;
- a entidade oficial de distribuição é `Rateio`;
- a entidade oficial de custo apropriado continua sendo `CostAllocation`.

## 6. Fluxos reais auditados

### 6.1 Compra

Fluxo real encontrado:

```text
PedidoCompra
  -> RecebimentoParcial
  -> LoteEstoque
  -> EstoqueMovimento (origem=COMPRA)
  -> Despesa (origem_tipo=COMPRA, A_PAGAR)
  -> Fluxo de caixa por Despesa
  -> DRE agrícola v1 apenas via Despesa, se aplicável e sem camada superior
```

Observação:

- compras ainda não projetam `CostAllocation` automaticamente;
- o custo fica físico em estoque e financeiro em `Despesa`;
- a apropriação econômica só ocorre depois, quando houver consumo/rateio/camada superior.

### 6.2 Estoque

Fluxo real encontrado:

```text
Movimento de estoque
  -> valuation físico em EstoqueMovimento/LoteEstoque
  -> em fluxo legado pode gerar LancamentoFinanceiro (ESTOQUE)
  -> em fluxo oficial deve gerar CostAllocation quando houver apropriação
  -> DRE agrícola v1 usa movimento só para reconciliação
```

Observação:

- este é um dos principais pontos de paralelismo ainda vivos.

### 6.3 Agricultura

Fluxo real encontrado:

```text
OperacaoAgricola
  -> OperacaoExecucao
  -> consumo de estoque / ledger
  -> CostAllocation (fonte OPERATION_EXECUTION)
  -> Despesa automática legada (origem OPERACAO_AGRICOLA)
  -> DRE agrícola v1 privilegia CostAllocation
  -> Rentabilidade deriva da DRE v1
```

Observação:

- a criação de `Despesa` automática ainda é compatibilidade legada;
- a apropriação correta já existe, mas a origem operacional continua duplicando a leitura financeira.

### 6.4 Comercialização

Fluxo real encontrado:

```text
ProdutoColhido
  -> ComercializacaoCommodity
  -> Receita (origem COMERCIALIZACAO)
  -> Fluxo de caixa por Receita
  -> DRE agrícola v1
  -> Hedge usa comercialização como compromisso físico
```

### 6.5 RH

Fluxo real encontrado:

```text
Diária / Empreitada
  -> OperationalCostAllocationService
  -> CostAllocation quando houver contexto agrícola resolvido
  -> Despesa automática quando houver unidade produtiva
  -> DRE agrícola v1 usa CostAllocation e suprime Despesa duplicada
```

### 6.6 Frota

Fluxo real encontrado:

```text
Abastecimento / OS / Apontamento
  -> OperationalCostAllocationService
  -> CostAllocation
  -> Despesa automática quando aplicável
  -> DRE agrícola v1 privilegia CostAllocation
  -> dashboards de frota ainda calculam custos também por trilha própria
```

### 6.7 Pecuária

Fluxo real encontrado:

```text
Compra animal
  -> EventoAnimal tipo COMPRA
  -> Despesa (origem COMPRA)

Vacinação / medicação / venda / abate
  -> ManejoLoteService
  -> Despesa ou Receita direta

Vacinação sincronizada de campo
  -> EstoqueMovimento
  -> CostAllocation sanitário
  -> dashboards pecuários
```

Observação:

- pecuária ainda é o domínio mais heterogêneo economicamente;
- não há uma cadeia única para todos os fatos pecuários.

### 6.8 Hedge

Fluxo real encontrado:

```text
Contrato futuro / registro de hedge
  -> exposição
  -> MTM snapshot
  -> alertas e analytics de risco
```

Observação:

- hedge ainda não projeta `Receita`, `Despesa`, `Fluxo de Caixa` ou `DRE`;
- hoje é um subdomínio analítico/financeiro paralelo.

## 7. DRE e rentabilidade

### 7.1 Arquitetura oficial da DRE

Arquitetura oficial recomendada com base no código:

```text
Receitas operacionais      -> Receita
Custos operacionais        -> CostAllocation
Despesas sem camada acima  -> Despesa
Reconciliação              -> LancamentoFinanceiro + EstoqueMovimento
Consolidação               -> agricola.dre.v1
```

Decisão:

- `agricola.dre.v1` é a **DRE oficial do domínio econômico operacional por safra**;
- `financeiro/lancamentos/dre` é **legado compatível**, não referência arquitetural futura.

### 7.2 Arquitetura oficial da rentabilidade

Arquitetura oficial já está correta:

```text
DRE agrícola v1
  -> Rentabilidade agrícola v1
```

Rentabilidade não deve consumir:

- `LancamentoFinanceiro` diretamente;
- `OperacaoAgricola.custo_total` diretamente;
- `EstoqueMovimento` diretamente;
- agregações financeiras legadas fora da DRE oficial.

## 8. Plano de contas

Estado encontrado:

- `Receita` e `Despesa` exigem `plano_conta_id`;
- compras, comercialização, RH, frota e pecuária tentam mapear conta analítica automaticamente;
- a cobertura não é uniforme;
- alguns fluxos fazem fallback ou simplesmente não criam o lançamento financeiro quando a infraestrutura não existe.

Decisão:

- todo fato que materializa `Receita` ou `Despesa` em v1.0 deve exigir mapeamento de `PlanoConta`;
- falha de infraestrutura financeira não deve continuar silenciosa em fluxos críticos de v1.0.

## 9. Centro de custos

Decisão arquitetural:

- centro de custo **não é entidade oficial**;
- é uma visão analítica derivada de `Rateio` e `Despesa`;
- para custo operacional oficial por safra/PU, a referência deve ser `CostAllocation`, não centro de custo.

## 10. OperationalCostService

Diagnóstico:

- é a melhor peça nova do domínio;
- já integra frota, abastecimento, RH e apontamentos;
- aplica idempotência;
- cria `CostAllocation`;
- cria `Despesa` somente quando aplicável;
- resolve `ProductionUnit` automaticamente quando possível.

Decisão:

- `OperationalCostAllocationService` deve ser a porta oficial para novos custos operacionais;
- módulos ainda fora dele devem ser migrados progressivamente.

## 11. CostAllocation

Diagnóstico:

- é a apropriação econômica oficial;
- já possui taxonomia de `source`;
- já possui guardrails de duplicidade;
- já é consumido pela DRE agrícola v1;
- já é consumido pela rentabilidade agrícola v1.

Decisão:

- `CostAllocation` é a fonte oficial de custo apropriado;
- nenhuma nova leitura de custo operacional deve entrar na DRE sem passar por `CostAllocation`.

## 12. Receitas

Diagnóstico consolidado:

- `Receita` é a fonte certa;
- mas há duas origens agrícolas concorrentes do mesmo ciclo: romaneio e comercialização;
- a DRE agrícola v1 já corrige a concorrência por precedência;
- o restante do produto ainda convive com ambas.

Decisão:

- em v1.0, comercialização confirmada deve ser tratada como reconhecimento operacional superior ao romaneio;
- romaneio deve permanecer como lastro físico e receita estimada/compatível, não como origem concorrente do fechamento final.

## 13. Despesas

Diagnóstico consolidado:

- `Despesa` está corretamente centralizada no modelo financeiro;
- `Rateio` está corretamente subordinado à `Despesa`;
- a principal inconsistência não é a modelagem, mas a convivência com `CostAllocation` e `LancamentoFinanceiro`.

Decisão:

- `Despesa` continua como obrigação financeira oficial;
- quando um fato operacional também gerar `CostAllocation`, a DRE operacional deve continuar privilegiando `CostAllocation`.

## 14. Riscos de dupla contagem

Riscos críticos identificados:

1. `RomaneioColheita` + `ComercializacaoCommodity`.
2. `Despesa` + `CostAllocation`.
3. `EstoqueMovimento` + `LancamentoFinanceiro` + `CostAllocation`.
4. `PedidoCompra` + `RecebimentoParcial` + `Despesa`.
5. frota em dashboards executivos somando custo bruto fora da camada econômica oficial.
6. pecuária criando `Despesa`/`Receita` direta sem precedência uniforme.
7. DRE legada em `LancamentoFinanceiro` convivendo com DRE agrícola v1.

## 15. Caminhos paralelos identificados

Principais caminhos paralelos ainda ativos:

- DRE legada em `financeiro.services.lancamento_service`;
- simulação DRE legada consumida pela UI `/dashboard/financeiro/dre`;
- custo de estoque em `LancamentoFinanceiro`;
- resumo de custos agrícolas com fallback para `OperacaoAgricola.custo_total`;
- romaneio gerando `Receita` automática;
- pecuária gerando `Despesa` e `Receita` direta em serviços legados;
- hedge fora da cadeia econômica oficial;
- analytics de frota consolidados fora de `CostAllocation`.

## 16. Compatibilidade legada

Compatibilidades que precisam permanecer por enquanto:

- `OperacaoAgricola.custo_total` e `custo_por_ha`;
- `RomaneioColheita.receita_total` como estimativa/compatibilidade;
- `Produto.preco_medio` como snapshot/fallback de interface, nunca valuation oficial;
- `Receita.cliente` textual;
- `Despesa.fornecedor` textual;
- `LancamentoFinanceiro` legado;
- DRE financeira legada;
- recebimento fallback em compras;
- despesas/receitas sem origem em fluxos antigos;
- rateios financeiros antigos ainda não refletidos em toda a cadeia.

## 17. Arquitetura alvo oficial

### 17.1 Custos operacionais

Arquitetura alvo oficial:

```text
Eventos operacionais
  -> OperationalCostAllocationService
  -> CostAllocation
  -> DRE agrícola v1
  -> Rentabilidade agrícola v1
```

Complemento:

- `Despesa` pode ser criada em paralelo como obrigação/realização financeira;
- mas o custo operacional oficial continua sendo `CostAllocation`.

### 17.2 Receitas, despesas e caixa

Arquitetura alvo oficial:

```text
Receitas / Despesas financeiras
  -> Receita / Despesa
  -> Fluxo de Caixa / Livro Caixa
  -> DRE agrícola v1 ou DRE financeira por competência/caixa
```

### 17.3 Reconciliação

```text
LancamentoFinanceiro + EstoqueMovimento
  -> Reconciliação
  -> Alertas de divergência
  -> Nunca consolidação primária de custo operacional
```

## 18. Decisão final

**Modelo C — existem caminhos paralelos relevantes que precisam de consolidação antes da v1.0.**

Justificativa:

- a referência oficial já existe;
- a DRE agrícola v1 e a rentabilidade v1 já estão corretas;
- mas o produto ainda expõe e calcula visões econômicas paralelas importantes.

## 19. O que entra na v1.0

Deve entrar na v1.0:

- `Receita` como fonte oficial de receita;
- `Despesa` como fonte oficial de obrigação financeira;
- `CostAllocation` como fonte oficial de custo operacional;
- `OperationalCostAllocationService` como gateway obrigatório para novos custos operacionais;
- `agricola.dre.v1` como DRE oficial;
- `agricola.rentabilidade.v1` como rentabilidade oficial;
- precedência formal `comercialização > romaneio`;
- `LancamentoFinanceiro` e `EstoqueMovimento` restritos a reconciliação e compatibilidade;
- esta decisão arquitetural como referência oficial para novos desenvolvimentos.

## 20. O que pode ficar para v1.1

Pode ficar para v1.1:

- remoção gradual da DRE legada baseada em `LancamentoFinanceiro`;
- retirada do fallback por `OperacaoAgricola.custo_total` em resumos de custo;
- unificação econômica completa da pecuária;
- integração financeira/econômica do hedge;
- endurecimento de falha quando integração automática não encontrar `PlanoConta`;
- migração completa dos dashboards de frota para leitura a partir da camada econômica oficial;
- saneamento de receitas automáticas de romaneio em cenários já comercializados.

## 21. Plano recomendado

1. Congelar a referência oficial em `Receita`, `Despesa`, `CostAllocation`, `agricola.dre.v1` e `agricola.rentabilidade.v1`.
2. Declarar `financeiro/lancamentos/dre` e `LancamentoFinanceiro` como compatibilidade legada, não arquitetura oficial de resultado operacional.
3. Impedir novos custos operacionais fora de `OperationalCostAllocationService`.
4. Impedir novos dashboards de custo/rentabilidade que leiam `OperacaoAgricola.custo_total` ou `LancamentoFinanceiro` como fonte primária.
5. Criar backlog de consolidação para pecuária, estoque legado, romaneio e hedge.
6. Separar no produto as UIs oficiais das UIs legadas.

## 22. Resposta à pergunta central

**Existe uma arquitetura econômica oficial única no AgroSaaS para custos, receitas, apropriações, DRE, fluxo de caixa e rentabilidade, ou ainda existem caminhos paralelos relevantes que precisam ser corrigidos antes do lançamento?**

Resposta:

- **existe uma arquitetura oficial definida e tecnicamente defensável**;
- **mas ela ainda não é única na implementação atual**;
- **existem caminhos paralelos relevantes que devem ser tratados antes do lançamento v1.0**.

## 23. Critérios de aceite desta auditoria

Confirmações explícitas:

- A fonte oficial de receita foi definida: **`Receita`**.
- A fonte oficial de despesa foi definida: **`Despesa`**.
- A fonte oficial de custo operacional foi definida: **`CostAllocation`**.
- A relação entre `Despesa` e `CostAllocation` foi definida: **obrigação financeira vs apropriação econômica**.
- A DRE tem arquitetura oficial: **`agricola.dre.v1`**.
- A Rentabilidade tem arquitetura oficial: **`agricola.rentabilidade.v1`**.
- O risco de dupla contagem foi avaliado: **sim**.
- Caminhos paralelos foram identificados: **sim**.
- O que fica para v1.0 e v1.1 foi separado: **sim**.
- Nenhuma alteração operacional foi feita: **sim**.

## 24. Pergunta final obrigatória

**Após esta execução, qualquer novo desenvolvimento econômico no AgroSaaS terá uma referência arquitetural clara sobre como gerar receitas, despesas, custos operacionais, apropriações, DRE, fluxo de caixa e rentabilidade, sem criar caminhos paralelos ou dupla contagem?**

Resposta:

**Sim como referência arquitetural oficial. Não como estado já consolidado da codebase.**

Ou seja:

- a partir deste documento, a referência para novos desenvolvimentos fica clara;
- porém a base atual ainda contém caminhos paralelos legados que precisam ser respeitados como compatibilidade e reduzidos progressivamente.
