# Brainstorm — Sincronização automática CultivoArea ↔ ProductionUnit

> Data: 2026-07-20

## Problema

`CultivoArea` (definida na criação/edição da safra: cultivo + talhão + área) e `ProductionUnit`
(tela `/agricola/safras/[id]/production-units`, pivô obrigatório de `CostAllocation`, `cenarios`
e `rentabilidade/DRE`) não tinham sincronização automática. Consequência real: cenários econômicos
e DRE por unidade operacional ficavam vazios se o usuário não abrisse manualmente a tela de
Production Units, mesmo já tendo configurado os cultivos/áreas na safra.

## Abordagem escolhida

**Sincronização automática síncrona**, dentro da mesma transação de `CultivoService`
(`criar_com_areas` e `sincronizar_areas`), chamando diretamente `ProductionUnitService` — sem
eventos/outbox (infraestrutura não usada nesse fluxo hoje, fora de escopo).

- Ao criar/atualizar um `CultivoArea`: `ProductionUnitService.sincronizar_de_cultivo_area()`
  cria a PU com 100% de participação (se não existir) ou reaproveita a PU existente (mesmo que
  `ENCERRADA`, reativando-a), atualizando apenas `cultivo_area_id`/`area_ha` — **nunca sobrescreve
  `percentual_participacao`** ajustado manualmente (caso de consórcio).
- Ao remover um `CultivoArea` (via `sincronizar_areas`, que faz DELETE+INSERT completo por
  cultivo): `ProductionUnitService.encerrar_por_cultivo_area()` marca a PU como `ENCERRADA` —
  **nunca deleta**, preservando histórico de `CostAllocation`/DRE já lançado.

## Decisão de negócio confirmada com o usuário

Ao remover CultivoArea com PU associada: **encerrar (status=ENCERRADA), nunca deletar** —
uniforme, sem checagem condicional por existência de `CostAllocation`.

## Arquivos alterados

- `services/api/agricola/production_units/service.py` — métodos novos
  `sincronizar_de_cultivo_area()` e `encerrar_por_cultivo_area()`.
- `services/api/agricola/cultivos/service.py` — `criar_com_areas()` e `sincronizar_areas()`
  passam a chamar a sincronização de PU após persistir `CultivoArea`.
- `services/api/tests/unit/agricola/test_production_units_sync.py` (novo) — 7 testes cobrindo
  criação, idempotência, reativação de PU encerrada, encerramento sem deleção.
- `services/api/tests/unit/agricola/test_cultivos_production_unit_sync.py` (novo) — 2 testes de
  integração confirmando que `CultivoService` chama a sincronização corretamente.

## Fora de escopo (explicitamente adiado)

Unificação cross-módulo de rateio (`CostAllocation`/`Rateio`/`apropriacao_custo`, extensão a
pecuária/frota) — ver memória `project_rateio_unificacao_adiada`. Não implementar agora; é
projeto à parte, de escopo alto, para tratar após validação do Dry Run.

## Resultado dos testes

- 9 testes novos: todos verdes.
- Regressão completa `tests/unit/agricola/`: 225 passed, 4 failed (mesmas 4 falhas
  pré-existentes e não relacionadas: `test_analytics_request_cache`,
  `test_caderno_listar_alertas`, `test_cert_calibracao_sanitaria`,
  `test_field_core03_caderno_status`).
- `ruff check` nos arquivos alterados: nenhum erro novo introduzido (achados remanescentes são
  débito técnico pré-existente — imports não usados, linhas longas, ordenação de imports —
  presentes antes desta mudança).

## Pendências remanescentes para o Dry Run (não bloqueantes)

1. Validação declarada safra↔talhão em `vincular_e_gerar_tarefas` (SOIL-PLAN-EXEC-03, seção 7).
2. `TarefaCampo` sem FK para `SafraTarefa` (SOIL-PLAN-EXEC-01).
3. `RegraAgronomica` — motor morto, sem seed/CRUD, nunca chamado na prática (SOIL-PLAN-EXEC-02).
4. Duplicidade de rotas frontend de análise de solo (SOIL-PLAN-EXEC-01).
5. `agricola/prescricoes/models.py.bak` morto convivendo com módulo ativo.

Nenhum desses tem efeito funcional bloqueante hoje; ficam documentados como dívida técnica.
