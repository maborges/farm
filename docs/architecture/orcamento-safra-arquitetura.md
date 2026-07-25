# Arquitetura de Planejamento/Orçamento de Safra

## Diagnóstico do estado atual

- `Safra` (`agricola/safras/models.py:38`) + `SafraTalhao` já existem.
- `agricola/a1_planejamento/models.py:21` tem `ItemOrcamentoSafra` (tabela `agricola_orcamento_itens`): campos manuais (`custo_unitario`, `custo_total`, `categoria`), **sem vínculo com cadastros mestres** — hoje é digitado à mão, não gerado a partir de Produto/Máquina/Pessoa.
- `CostAllocation` (`agricola/custos/models.py:11`) é o motor único de custo **realizado**, alimentado por `agricola/operacoes/service.py:778`, `operational_cost_service.py`, `manejo_sync_service.py`, `despesa_service.py`. Ele já grava valor congelado (`amount`) no momento da execução — é o padrão de "snapshot" a replicar no planejado.
- Cadastros de custo mestre existem mas são heterogêneos: `Produto.preco_medio` (Float — nota: fora do padrão Decimal do projeto), `ColaboradorRH.valor_diaria/valor_hora`, custo de `Equipamento` é **calculado dinamicamente** (não persistido) em `frota_custo_service.py`, e não existe cadastro mestre de "Serviço" com preço padrão.

## Recomendação

Não criar um segundo motor de custo. Estender `ItemOrcamentoSafra` para ser gerado a partir dos cadastros mestres, com um snapshot imutável dos valores, e reaproveitar `CostAllocation` como fonte do "realizado" para a comparação planejado × realizado. Ver detalhes de modelos, regras de negócio, fluxo de geração automática, riscos (Float em Produto, custo de máquina não persistido, ausência de cadastro de Serviço) e plano de implementação incremental no restante do arquivo completo gerado nesta análise.

### Modelos propostos
1. `ItemOrcamentoSafra` (existente, estender): adicionar `origem_tipo` (PRODUTO/MAQUINA/PESSOA/SERVICO/MANUAL), `origem_id` (FK genérica), `custo_unitario_snapshot`, `custo_unitario_ajustado` (nullable — só preenchido se usuário sobrescrever), `custo_unitario_efetivo` (computed: ajustado ?? snapshot), `snapshot_data` (JSONB com o registro de origem na hora da captura), `capturado_em`.
2. Nenhum novo motor de custo: cálculo de "planejado" = soma de `custo_unitario_efetivo * quantidade` por `ItemOrcamentoSafra`; "realizado" = soma de `CostAllocation.amount` filtrado por `production_unit_id`/safra. Comparação vive num service de leitura (`OrcamentoComparativoService`), não em tabela nova.
3. Padronizar custo de Máquina: persistir `custo_hora_snapshot` calculado por `frota_custo_service` no momento da captura (hoje é só dinâmico — precisa existir um valor congelável).
4. Criar cadastro mínimo `TipoServico` (ou usar `Produto` com uma flag de serviço) para cobrir a lacuna hoje coberta só por categoria livre.

### Regras de negócio
- Captura de snapshot só ocorre em ação explícita "Adicionar ao orçamento" — não há job de recálculo automático.
- Edição do orçamento nunca escreve em Produto/Equipamento/ColaboradorRH — só em `custo_unitario_ajustado`.
- Se `origem_id` for apagado no cadastro mestre depois, o snapshot (`snapshot_data`) garante que o histórico não quebra (soft-delete/FK nullable com `ON DELETE SET NULL`, não CASCADE).
- Comparação planejado × realizado exige que `ItemOrcamentoSafra.production_unit_id` (ou `cultivo_id`) case com o `production_unit_id` usado em `CostAllocation` — reforçar isso como invariante testada (teste de isolamento por tenant + por production_unit).

### Riscos
- `Produto.preco_medio` é `Float` — ao snapshotar, converter para `Decimal` na captura (não persistir o Float bruto).
- Custo de máquina não é persistido hoje; sem essa mudança o "snapshot" de máquina fica sempre recalculado (não é imutável de fato).
- Falta cadastro de Serviço: setores usarão `MANUAL` para serviços até o cadastro existir, arriscando divergência maior planejado×realizado nessa categoria.
- Migração dos dados existentes em `ItemOrcamentoSafra` (hoje todos `origem_tipo = MANUAL`) precisa de plano de backfill, não é breaking.

## Custo/impacto de implementação

Estimativa por bloco (dev pleno, backend+frontend, sem contar QA de outro squad):

| Bloco | Escopo | Estimativa |
|---|---|---|
| 1. Migration `ItemOrcamentoSafra` | 6 colunas novas + índice, `alembic revision --autogenerate` + `COMMIT` explícito | 2-3h |
| 2. Snapshot de custo (service) | `CapturarSnapshotCustoService`: busca Produto/ColaboradorRH/Equipamento por `origem_tipo`+`origem_id`, converte Float→Decimal, monta `snapshot_data` | 6-8h |
| 3. Custo de máquina persistível | Expor `custo_hora` calculável e snapshotável a partir de `frota_custo_service.py` (hoje só dinâmico) — maior risco de regressão em telas que já consomem esse cálculo | 6-10h |
| 4. Endpoint/UI "Adicionar ao orçamento" | Busca produto/máquina/pessoa via autocomplete, prévia de custo antes de salvar, campo de ajuste manual visível separado do snapshot | 8-12h |
| 5. `OrcamentoComparativoService` (planejado × realizado) | Agregação por `production_unit_id`/categoria, cruzando `ItemOrcamentoSafra` e `CostAllocation` | 6-8h |
| 6. Tela de comparativo (dashboard) | Gráfico/tabela planejado vs realizado por categoria, dentro do padrão de Data Table/AlertDialog do projeto | 6-10h |
| 7. Cadastro mínimo `TipoServico` | Model+schema+service+router seguindo padrão `BaseService`, migration | 4-6h |
| 8. Backfill dos itens existentes | Script marcando registros antigos como `origem_tipo=MANUAL` com `snapshot_data=null` | 1-2h |
| 9. Testes (unit + isolamento de tenant) | Cobrir snapshot imutável, ajuste manual não afeta cadastro mestre, comparação por production_unit | 6-8h |

**Total estimado: ~45-65h (≈ 1,5-2 semanas para 1 dev, ou ~1 semana com 2 devs em paralelo backend/frontend).**

Maior fonte de incerteza: bloco 3 (custo de máquina) — hoje é cálculo espalhado em `frota_custo_service.py`/`frota_dashboard_detail_service.py`; torná-lo "congelável" pode exigir tocar código usado por outras telas de frota, então merece um spike de ~2h antes de estimar com confiança.

Impacto em produção: nenhuma mudança em `CostAllocation` (motor de realizado intocado), reduzindo risco de regressão em DRE/dashboard já existentes. O risco fica concentrado nos módulos `a1_planejamento` e frota.
