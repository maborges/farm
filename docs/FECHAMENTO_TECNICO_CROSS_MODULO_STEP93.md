# Fechamento Tecnico Cross-Modulo - Step 93

**Data:** 2026-04-30  
**Escopo:** consolidacao final do estado tecnico apos os Steps 46-92, sem alterar codigo.

## 1. Resumo executivo

Os Steps 46-92 consolidaram uma direcao arquitetural unica para entidades cross-modulo, reduziram duplicidades historicas entre modulos produtivos e modulos integradores e fecharam duas trilhas principais de refatoracao:

- consolidacao de ownership canônico para entidades compartilhadas;
- consolidacao de `estoque_movimentos` como ledger unico de estoque;
- consolidacao de `cadastros_produtos` como catalogo canônico de produto/insumo;
- eliminacao do nome legado `insumo_id` em favor de `produto_id`;
- validacao final dos fluxos principais entre Estoque, Compras, Agricultura, Pecuaria e Financeiro.

No estado encerrado pelo Step 92:

- nao ha uso ativo de `estoque_movimentacoes` em codigo Python validado;
- nao ha uso ativo de `insumo_id` em codigo Python validado;
- os fluxos principais testados seguem operacionais no escopo coberto;
- as decisoes canônicas dos Steps 46-49 continuam sendo a referencia de arquitetura.

## 2. Decisoes arquiteturais tomadas

### 2.1 Regra estrutural

Agricultura e Pecuaria permanecem como modulos produtivos. Core, Estoque, Financeiro e demais modulos integradores permanecem como fontes compartilhadas para cadastros, movimentos fisicos e movimentos economicos. Modulos produtivos nao devem recriar cadastros, ledgers ou fluxos paralelos para entidades ja canônicas.

### 2.2 Ownership canônico congelado

As decisoes do Step 48 seguem ativas como regra de manutencao:

- `Tenant`, usuarios, RBAC e permissoes: ownership do Core.
- `UnidadeProdutiva` / compatibilidade com `Fazenda`: ownership do Core.
- `AreaRural`: ownership do Core para talhao, piquete, curral e equivalentes espaciais.
- `Pessoa`: ownership do Core/Pessoas para fornecedor, cliente e prestador.
- `Produto`: ownership do catalogo canônico consumido por Estoque e pelos modulos operacionais.
- `EstoqueMovimento`, `SaldoEstoque`, `LoteEstoque`, `Deposito`: ownership de Estoque/Operacional.
- `Despesa` e `Receita`: ownership do Financeiro.
- `Safra`, `Cultivo`, `OperacaoAgricola`: ownership da Agricultura.
- `Animal`, `LoteAnimal`, `ManejoLote`, `ProducaoLeite`: ownership da Pecuaria.

### 2.3 Ledger unico de estoque

Ficou consolidado que:

- `estoque_movimentos` e a unica fonte oficial de movimentacao de estoque;
- `estoque_saldos` e estado derivado, nao fonte primaria;
- correcoes devem ocorrer por novos movimentos, nao por sobrescrita historica;
- `LEGADO` e uma origem valida apenas para backfill/migracao/importacao historica;
- `MANUAL` permanece reservado a lancamentos manuais correntes do dominio atual.

### 2.4 Produto/insumo canônico

Ficou consolidado que:

- `cadastros_produtos` e o catalogo mestre de produto/insumo;
- referencias transacionais devem usar `produto_id`;
- `InsumoOperacao.insumo_id` era legado de nomenclatura e foi substituido por `produto_id`;
- Pecuaria passou a ter `produto_id` em `pec_manejos_lote` para vinculo com o catalogo canônico;
- `lote_estoque_id` e `unidade_medida_id` passaram a existir em `insumos_operacao` como campos canônicos aditivos.

## 3. Fontes canônicas atuais

As fontes abaixo devem ser tratadas como referencia atual para novas implementacoes e revisoes:

| Dominio | Fonte canônica atual | Referencia principal |
|---|---|---|
| Matriz cross-modulo e monetizacao | regras de integracao por modulo | `docs/contexts/step46-cross-module-integration-monetization-context.md` |
| Modelo de dados unificado | ownership e relacionamentos logicos | `docs/contexts/step47-unified-data-model-context.md` |
| Ownership congelado | fontes da verdade por entidade | `docs/contexts/step48-cross-module-ownership-context.md` |
| Plano incremental de migracao | ordem e politicas de migracao | `docs/contexts/step49-cross-module-migration-plan-context.md` |
| Ledger de estoque | `EstoqueMovimento` / `estoque_movimentos` | `docs/ESTOQUE_CANONICO_LEDGER_2026-04-28.md` |
| Catalogo de produto/insumo | `Produto` / `cadastros_produtos` | `docs/AUDITORIA_PRODUTO_CANONICO_STEP82.md` e Step 48 |
| Estado final do rename `produto_id` | fechamento pos-rename | `docs/AUDITORIA_PRODUTO_CANONICO_FINAL_STEP87.md` |
| Validacao funcional final | testes e correcoes finais | `docs/VALIDACAO_CROSS_MODULO_STEP92.md` |

## 4. Migracoes executadas

### 4.1 Migracoes de schema

As migracoes explicitamente vinculadas ao fechamento desta refatoracao foram:

| Step | Migration | Efeito consolidado |
|---|---|---|
| 68 | `step24_estoque_movimentos_origem_legado.py` | liberou `LEGADO` na constraint de `estoque_movimentos` |
| 79 | `step25_drop_movimentacoes.py` | removeu fisicamente `estoque_movimentacoes` |
| 83/84 | `step26_produto_canonico.py` | adicionou `lote_estoque_id` e `unidade_medida_id` em `insumos_operacao`; adicionou `produto_id` em `pec_manejos_lote` |
| 86 | `step27_rename_insumo_id.py` | renomeou `insumos_operacao.insumo_id` para `produto_id` e recriou o indice canônico |

### 4.2 Migracao de dados / operacao assistida

| Step | Acao | Resultado consolidado |
|---|---|---|
| 70 | dry-run do backfill legado -> ledger | classificacao validada sem erro |
| 71 | backfill real `estoque_movimentacoes` -> `estoque_movimentos` | `4` registros persistidos como `LEGADO`, `4` ignorados, `1` pendente de revisao manual, `0` erros |
| 72 | revisao manual de `OPERACAO_AGRICOLA` legado | caso ambíguo nao foi promovido automaticamente |

## 5. Guardrails ativos

Os guardrails ativos ao final do Step 92 sao:

### 5.1 Guardrail de ownership cross-modulo

Arquivo: `services/api/tests/unit/test_cross_module_ownership_guardrails.py`

Garante que novos models/tabelas nao reintroduzam duplicidades para entidades ja canonizadas no Step 48, bloqueando padroes como:

- `fazendas`
- `fornecedores`
- `clientes`
- `produtos_estoque`
- `insumos_agricolas`
- `estoque_agricola`
- `estoque_pecuario`
- `maquina_veiculo`

### 5.2 Guardrail de legado de estoque

Arquivo: `services/api/tests/unit/operacional/test_estoque_legacy_guardrail.py`

Varre codigo Python ativo em `services/api` e `apps/web/services/api` para impedir reintroducao de:

- `MovimentacaoEstoque`
- `estoque_movimentacoes`

### 5.3 Guardrail semantico de produto canônico

A validacao do Step 92 confirmou por varredura estatica que nao ha uso ativo de `insumo_id` em codigo Python sob `services/api/**/*.py`. Na pratica, `produto_id` virou o nome permitido para novas referencias runtime do dominio.

## 6. Testes e validacoes executadas

### 6.1 Validacoes de migracao de estoque

- Step 65: auditoria do passivo legado para backfill.
- Step 70: dry-run do backfill com classificacao `IGNORAR`, `MIGRAR`, `MARCAR_COMO_LEGADO` e `REVISAR_MANUALMENTE`.
- Step 71: execucao real do backfill com idempotencia validada.
- Step 77: auditoria final pre-remocao fisica confirmando `0` usos funcionais do legado.
- Step 80: validacao final do ledger canônico apos o drop fisico da tabela legada.

### 6.2 Validacao final cross-modulo do Step 92

Comandos e resultados consolidados no Step 92:

- guardrails:
  - `3 passed in 0.58s`
- compilacao Python (`py_compile`) dos modulos impactados:
  - sem erros
- suite focada cross-modulo:
  - `76 passed, 2 xfailed, 44 warnings in 92.42s`
- validacao complementar em `apps/web`:
  - `6 passed in 0.36s`
  - `1 passed in 2.44s`
- `git diff --check`:
  - sem erros

### 6.3 Cobertura funcional validada

O Step 92 registrou cobertura valida para:

- Compras: criacao, recebimento e integracao com estoque/financeiro;
- Estoque: entrada, saida, ajuste, transferencia, FIFO e saldo;
- Agricultura: consumo com `produto_id`, uso de lote, ledger e leitura por safra;
- Pecuaria: manejo com `produto_id` e origem financeira;
- Financeiro: origem `MANUAL` para lancamentos manuais e origem operacional real para fluxos integrados.

## 7. Bugs corrigidos ao longo do fechamento

### 7.1 Correcao da trilha de estoque legado

Foi eliminada a dependencia funcional ativa de `MovimentacaoEstoque` e de `estoque_movimentacoes`, incluindo remanescentes identificados apos o rename canônico. O estado final validado no Step 92 confirma ausencia desses termos em codigo Python ativo.

### 7.2 Correcao da nomenclatura transacional de insumo/produto

`insumo_id` foi removido do runtime em favor de `produto_id`, alinhando Agricultura, Pecuaria, Estoque e demais consumidores sobre a mesma FK canônica para `cadastros_produtos`.

### 7.3 Correcao de avancar fase de safra

No Step 92 foi corrigido o fluxo `POST /api/v1/safras/{id}/avancar-fase/{nova_fase}`:

- `novo_status` deixou de ser obrigatorio no corpo;
- a fase da URL permaneceu como fonte canônica;
- foi adicionada validacao defensiva para rejeitar divergencia entre URL e corpo.

### 7.4 Correcao de sinal na leitura de ledger por safra

No Step 92 a leitura historica por safra passou a normalizar `quantidade` com valor absoluto, mantendo a direcao do movimento no campo `tipo`, eliminando interpretacao ambigua para consumo.

### 7.5 Correcao de fixture de integracao no espelho `apps/web`

No Step 92 foi corrigido um bloqueio de teste por metadata/FK de `unidade_medida_id`, com registro explicito do modelo `UnidadeMedida` no teste de integracao espelhado.

## 8. Pendencias conhecidas

As pendencias abaixo continuam abertas apos o Step 92, mas nao bloqueiam o fechamento tecnico do ciclo 46-92:

- migrar Compras de `compras_fornecedores` para `cadastros_pessoas`, removendo duplicidade de fornecedor;
- depreciar `pec_piquetes` em favor de `cadastros_areas_rurais` tipo `PIQUETE`;
- consolidar padrao `equipamento_id` e eliminar nomenclatura legado `maquinario_id`;
- definir estrategia de centro de custo geral cross-modulo, hoje fragmentada entre `Rateio` e `CostAllocation`;
- evoluir `Produto.unidade_medida` de campo livre para FK canônica em `unidades_medida`;
- explicitar `ondelete` nas FKs transacionais que ainda dependem do comportamento padrao do banco;
- manter vigilancia contra recriacao de fluxos paralelos de estoque, produto, fornecedor e geografia produtiva.

Observacao importante: o caso legado de `OPERACAO_AGRICOLA` revisado no Step 72 foi deliberadamente mantido fora de migracao automatica por falta de remapeamento deterministico. Portanto, ele e uma decisao de encerramento controlado, nao um bug em aberto do runtime atual.

## 9. Proximos passos recomendados

### 9.1 Prioridade alta

1. Executar a migracao de fornecedor canônico em Compras (`compras_fornecedores` -> `cadastros_pessoas`).
2. Padronizar `origem_tipo/origem_id` nos fluxos restantes de Pecuaria, Frota, Compras e Vendas.
3. Tratar geografia produtiva como fonte unica, reduzindo cadastros espaciais paralelos.

### 9.2 Prioridade media

1. Definir entidade/estrategia de centro de custo geral cross-modulo.
2. Padronizar definitivamente `equipamento_id` em Frota/Maquinas.
3. Planejar migracao da unidade de medida de produto para FK canônica.

### 9.3 Regra operacional para os proximos steps

Qualquer nova implementacao cross-modulo deve:

- citar o Step 48 antes de criar entidade compartilhada;
- usar as fontes canônicas atuais antes de propor tabela nova;
- preservar `estoque_movimentos` como ledger unico;
- preservar `cadastros_produtos` como catalogo unico;
- evitar reintroduzir nomes ou contratos legados sem plano de compatibilidade explicito.

## 10. Referencias principais

- `docs/contexts/step46-cross-module-integration-monetization-context.md`
- `docs/contexts/step47-unified-data-model-context.md`
- `docs/contexts/step48-cross-module-ownership-context.md`
- `docs/contexts/step49-cross-module-migration-plan-context.md`
- `docs/AUDITORIA_BACKFILL_ESTOQUE_MOVIMENTOS_STEP65_2026-04-28.md`
- `docs/AUDITORIA_DRY_RUN_BACKFILL_ESTOQUE_MOVIMENTOS_STEP70_2026-04-28.md`
- `docs/AUDITORIA_BACKFILL_ESTOQUE_MOVIMENTOS_REAL_STEP71_2026-04-28.md`
- `docs/AUDITORIA_MANUAL_OPERACAO_AGRICOLA_STEP72_2026-04-28.md`
- `docs/ESTRATEGIA_DESATIVACAO_ESTOQUE_LEGADO_STEP73.md`
- `docs/AUDITORIA_FINAL_PRE_REMOCAO_FISICA_ESTOQUE_MOVIMENTACOES_STEP77_2026-04-28.md`
- `docs/PLANO_REMOCAO_FISICA_ESTOQUE_MOVIMENTACOES_STEP78.md`
- `docs/ESTOQUE_CANONICO_LEDGER_2026-04-28.md`
- `docs/AUDITORIA_PRODUTO_CANONICO_STEP82.md`
- `docs/PLANO_RENAME_INSUMO_ID_STEP85.md`
- `docs/AUDITORIA_PRODUTO_CANONICO_FINAL_STEP87.md`
- `docs/VALIDACAO_CROSS_MODULO_STEP92.md`
