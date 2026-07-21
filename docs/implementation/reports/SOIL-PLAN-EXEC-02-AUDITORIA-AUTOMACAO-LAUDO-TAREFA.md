# SOIL-PLAN-EXEC-02 — Auditoria: Automação Laudo de Solo → SafraTarefa

**Data:** 2026-07-20 · **Tipo:** Auditoria somente leitura · **Escopo:** existe automação real que transforma `AnaliseSolo` em `SafraTarefa(origem="SOLO")`?

## 1. Resumo executivo

Existe um fluxo **real e funcional**, mas ele **não é automático**: depende de uma ação humana explícita — clique em botão no frontend que chama `POST /analises-solo/{id}/gerar-tarefas?safra_id=...`. Não há gatilho (evento, job, subscriber) disparado pela criação/conclusão da `AnaliseSolo`. Há também um segundo mecanismo, `RegraAgronomica` + `aplicar_regras()` (`/inteligencia`), que é código real mas **não tem dados** (nenhuma migration/seed insere linhas na tabela `agricola_regras_agronomicas` e não há CRUD para criá-las) — na prática está sempre vazio, hoje é uma peça morta. O mecanismo que efetivamente gera as tarefas (`vincular_e_gerar_tarefas`) usa fórmulas fixas em Python (V%, fallback Embrapa), não `RegraAgronomica`.

## 2. Veredicto

**SIM, MAS DEPENDE DE AÇÃO MANUAL** (para o caminho `gerar-tarefas`).
O caminho paralelo `RegraAgronomica`/`aplicar_regras` é **SOMENTE ESTRUTURA PREPARADA** (sem dados, sem uso na criação de tarefas).

## 3. Mapa exato do fluxo encontrado

```
Frontend: SoilDiagnosisDialog (apps/web/src/components/agricola/soil-diagnosis-dialog.tsx)
  → usuário abre diálogo de uma AnaliseSolo já existente
  → useSafrasAtivas() carrega lista de safras ativas do tenant
  → usuário SELECIONA manualmente a safra no <Select> (linha 37: selectedSafraId)
  → clique no botão "Gerar tarefas" → mutation.mutate()
  → POST /agricola/analises-solo/{analiseId}/gerar-tarefas?safra_id={selectedSafraId}
       (soil-diagnosis-dialog.tsx:59-62)

Backend: router.py:160-174 (gerar_tarefas_analise)
  → requer role agronomo|admin, módulo A1_PLANEJAMENTO, tier PROFISSIONAL
  → chama AnaliseSoloService.vincular_e_gerar_tarefas(id, safra_id, user_id)
       (analises_solo/service.py:532-646)
      → gerar_recomendacoes(analise) — cálculo de calagem (V%), P, K, N
        (fórmulas Python fixas, não usa RegraAgronomica)
      → para cada recomendação positiva, chama TarefaService.criar(
            safra_id, TarefaCreate(origem="SOLO", analise_solo_id=analise.id,
            talhao_id=analise.talhao_id, dose_estimada_kg_ha=..., custo_estimado=...))
      → TarefaService.criar (tarefas/service.py:75-99) grava status_inicial =
        "PENDENTE_APROVACAO" (porque origem != "MANUAL")
  → session.commit() no router (linha 173)
  → retorna {"tarefas_geradas": [ids]}
```

## 4. Gatilho

**Manual, via UI.** Não há subscriber/evento/job periódico ligado à criação ou conclusão de `AnaliseSolo`. Nenhum código em `services/api/events`, `alert_engine`, `background_jobs.py` referencia `AnaliseSolo` ou `analise_solo_id`. `AUSENTE` qualquer gatilho automático.
Evidência de ausência: `grep -rn "AnaliseSolo" services/api/core/background_jobs.py services/api/agricola/alertas` → nenhum resultado.

## 5. Motor de regras

Dois motores coexistem, **não integrados entre si**:

1. **Motor efetivo (usado por `vincular_e_gerar_tarefas`)**: fórmulas hardcoded em `AnaliseSoloService.gerar_recomendacoes` (`service.py:147-360`) — cálculo de calagem por V% Embrapa (linha 235), interpretação de P/K via `SoloParametroCultura` cadastrado ou fallback Embrapa hardcoded (linhas 253-306), N por regra fixa "30 kg/ha se soja, senão 130" (linha 344). É código real e executa de fato.
2. **Motor `RegraAgronomica`** (`aplicar_regras`, `service.py:417-465`, exposto em `/inteligencia`, `router.py:148-158`): lê tabela `agricola_regras_agronomicas` (condição/ação como JSON genérico, sem campos fixos de cultura/dose/faixa/validade — tudo dentro de `condicao_json`/`acao_json`). **Não há nenhuma migration ou seed que insira registros nessa tabela** (`grep -rn "agricola_regras_agronomicas" migrations/versions/` só aparece em uma migration de outro assunto, sem INSERT) e **não há endpoint CRUD** para cadastrá-las manualmente. Na prática, `regras` sempre vem vazio — `/inteligencia` sempre retorna `[]`. Este motor **não gera SafraTarefa** — apenas devolve uma lista de recomendações ao chamador; não há código que pegue o retorno de `aplicar_regras` e crie uma `SafraTarefa`.

Conclusão: o motor de regras "declarativo" (RegraAgronomica) é estrutura preparada sem dados e sem consumidor que crie tarefas. O motor que efetivamente cria tarefas é hardcoded, sem tabela de regras configurável.

## 6. Determinação da safra

**Dependente de seleção manual.** `AnaliseSolo` não tem `safra_id`. `safra_id` chega como **query param obrigatório** no endpoint (`router.py:163`, `Query(..., description=...)`) e no frontend vem de um `<Select>` populado por `useSafrasAtivas()` (linha 36-37 do dialog) — o usuário escolhe explicitamente qual safra ativa receberá as tarefas. Não há inferência automática por talhão, cultivo ativo, ou data. Classificação: **dependente de seleção manual** (risco de erro humano se houver múltiplas safras ativas no mesmo talhão, mas não é "ambígua" no código — é uma escolha explícita e obrigatória, sem default).

## 7. Criação da tarefa

Confirmado em `TarefaCreate`/`TarefaService.criar`: grava `talhao_id`, `analise_solo_id`, `origem="SOLO"`, `tipo` (`CALAGEM`/`ADUBACAO_FOSFORO`/`ADUBACAO_POTASSIO`/`ADUBACAO_NITROGENIO`), `status="PENDENTE_APROVACAO"` (tarefas/service.py:77). Cria até 4 tarefas por chamada (uma por nutriente/calagem, se necessário).

## 8. Cálculo de dose e custo

- **Dose**: `dose_estimada_kg_ha` e `quantidade_total_estimada_kg` calculados a partir de área do talhão (`AreaRural.area_hectares_manual`/`area_hectares`) × dose recomendada (t/ha ou kg/ha) — `service.py:561-644`.
- **Preço**: dicionário `PRECOS` **hardcoded no service** (CALCARIO R$185/t, P2O5 R$5,40/kg, K2O R$4,90/kg, N R$4,50/kg — `service.py:551-556`), não vem de cadastro de insumo, FIFO de estoque nem tabela de preço. Há `TODO` explícito no código ("Buscar de cadastros_produtos.preco_medio se possível", linha 550) confirmando que é provisório.
- **Bug encontrado (evidência de baixa cobertura de testes)**: linha 607, bloco de Potássio, usa `PRECOS["POTASSIO"]`, mas o dicionário só define a chave `"K2O"` (linha 554) — isso lança `KeyError` em runtime sempre que houver recomendação de potássio positiva. **O fluxo de Potássio está quebrado hoje.**
- `custo_estimado` é gravado em `SafraTarefa.custo_estimado`, isolado — não há evidência de propagação automática para orçamento de safra nesta auditoria (fora de escopo reauditar `CustosService`, mas nenhuma chamada a `CustosService`/orçamento aparece dentro de `vincular_e_gerar_tarefas`).

## 9. Idempotência

**Ausente — risco crítico.** `TarefaService.criar` (linhas 75-99) não faz nenhuma consulta prévia por `(tenant, analise_solo_id, safra_id, talhao_id, tipo)` antes do insert. Não há `UniqueConstraint` no modelo `SafraTarefa` cobrindo essa combinação (`grep -n "UniqueConstraint" agricola/tarefas/models.py` não retorna nada — só há `Index` normal em `tenant_id, safra_id, status`). Clicar "Gerar tarefas" duas vezes na mesma análise/safra duplica todas as tarefas (calagem, P, K, N) sem aviso.

## 10. Aprovação

Tarefas nascem em `PENDENTE_APROVACAO` (confirmado, item 7). `TarefaService.aprovar()` (`service.py:270-275`) muda status para `APROVADA`, exigindo `aprovador_id`. Exclusão de tarefa pendente é bloqueada se já existir operação/caderno vinculado (`_avaliar_exclusao_tarefa`, linhas 143-160). `gerar_operacao_planejada` (linha 525) aceita tarefas em `PENDENTE_APROVACAO` OU `APROVADA` — ou seja, tarefas de origem SOLO tecnicamente podem gerar operação **antes** de aprovação formal (o gate real de "aprovação obrigatória" não foi encontrado nesta chamada; isso não foi re-verificado a fundo pois pertence ao escopo já validado no relatório 01, mas é citado aqui por relevância direta ao fluxo de solo). Não há execução direta nem baixa de estoque neste fluxo — confirma-se que a criação de `SafraTarefa` não movimenta estoque nem gera custo real (apenas estimado).

## 11. Frontend

Existe ação visível: `SoilDiagnosisDialog` (`apps/web/src/components/agricola/soil-diagnosis-dialog.tsx`) exibe recomendações (via `GET /analises-solo/{id}/recomendacoes`, usado por `useRecomendacoes`), permite selecionar safra e clicar em "Gerar tarefas" (linha ~265). Feature bloqueada por tier PROFISSIONAL no frontend e no backend (double-gate). Não há tela de CRUD de `RegraAgronomica`, nem tela para "revisar tratamentos" regra-a-regra — a revisão acontece implicitamente ao aprovar/rejeitar cada `SafraTarefa` já criada. Rota de Dry Run: `POST /agricola/analises-solo/{id}/gerar-tarefas?safra_id=...` (role agronomo/admin, tier PROFISSIONAL).

## 12. Chegada ao Campo PWA

Não reauditado a fundo (fora de escopo, backbone já validado no relatório 01). Grep aponta uso de `SOLO`/`analise_solo_id` apenas em `apps/campo/src/lib/caderno-offline.ts`, `task-domain.ts`, `db.ts` e `caderno/page.tsx` — indícios de que o app de campo trata `origem` como metadado ao exibir tarefas/caderno, mas não foi encontrada rotina própria que crie `TarefaCampo` distinta a partir de `analise_solo_id`; o caminho seria o mesmo genérico de `SafraTarefa` → `OperacaoAgricola PLANEJADA` já confirmado no relatório 01. Registrado sem propor correção, conforme instrução.

## 13. Testes

- `services/api/tests/unit/agricola/test_p1_monetization_gates.py:34` — cobre **apenas** que a rota `/analises-solo/{id}/gerar-tarefas` está protegida por gate de módulo/tier (monetização). **Não** testa lógica de negócio.
- Nenhum teste encontrado (`grep -rn "vincular_e_gerar_tarefas\|aplicar_regras\|RegraAgronomica"` em `tests/`) que exercite: aplicação de regra sobre análise real, criação de `SafraTarefa` origem SOLO, não duplicação, aprovação, ou geração de `OperacaoAgricola PLANEJADA` a partir de tarefa SOLO.
- Classificação: **não coberto** (apenas 1 teste de gate de rota, mock de autorização, sem PostgreSQL real nem asserção de efeito colateral). O bug do item 8 (`PRECOS["POTASSIO"]`) provavelmente não foi pego justamente pela ausência de teste funcional.

## 14. Evidências por arquivo e linha

- `services/api/agricola/analises_solo/models.py:67-90` — `RegraAgronomica` (JSON genérico, sem seed).
- `services/api/agricola/analises_solo/service.py:147-360` — `gerar_recomendacoes` (motor efetivo, hardcoded).
- `services/api/agricola/analises_solo/service.py:417-465` — `aplicar_regras` (motor declarativo, sem dados, sem consumidor de tarefa).
- `services/api/agricola/analises_solo/service.py:532-646` — `vincular_e_gerar_tarefas` (cria as `SafraTarefa`).
- `services/api/agricola/analises_solo/service.py:607` — bug `PRECOS["POTASSIO"]` (chave inexistente; correta seria `"K2O"`).
- `services/api/agricola/analises_solo/router.py:148-158` — endpoint `/inteligencia` (motor declarativo, sempre vazio hoje).
- `services/api/agricola/analises_solo/router.py:160-174` — endpoint `/gerar-tarefas` (gatilho manual real).
- `services/api/agricola/tarefas/service.py:75-99` — `TarefaService.criar`, sem checagem de duplicidade, status inicial `PENDENTE_APROVACAO`.
- `services/api/agricola/tarefas/service.py:270-275` — `aprovar()`.
- `services/api/agricola/tarefas/service.py:525-527` — `gerar_operacao_planejada` aceita `PENDENTE_APROVACAO` ou `APROVADA`.
- `apps/web/src/components/agricola/soil-diagnosis-dialog.tsx:36-62` — seleção manual de safra + chamada da mutation.
- `services/api/tests/unit/agricola/test_p1_monetization_gates.py:34` — único teste tocando a rota.

## 15. Lacunas

- `RegraAgronomica` sem seed e sem CRUD — tabela morta.
- Nenhum gatilho automático (evento/job) ligado à conclusão do laudo.
- Preços hardcoded, não vindos de cadastro/estoque/orçamento.
- Sem idempotência/dedupe.
- Sem teste funcional de ponta a ponta.
- `gerar_operacao_planejada` aceita tarefa apenas `PENDENTE_APROVACAO` sem exigir aprovação prévia formal neste ponto do código (revisão superficial; não reauditado a fundo por já validado no relatório 01, mas citado porque afeta diretamente o fluxo SOLO).

## 16. Riscos

- **Crítico**: duplicação de tarefas/custos ao clicar duas vezes em "Gerar tarefas" (sem dedupe).
- **Crítico**: `KeyError` não tratado ao recomendar Potássio — quebra a chamada inteira (as tarefas de Calagem/P já criadas antes do erro podem ficar sem rollback consistente, dependendo do commit único no router — como o `commit()` só ocorre após o retorno de `vincular_e_gerar_tarefas`, uma exceção no meio do laço provavelmente reverte tudo via rollback implícito do FastAPI/session, mas isso não foi testado nesta auditoria).
- **Alto**: seleção manual de safra sem validação de que o talhão pertence à safra escolhida (não verificado explicitamente no código lido).
- **Médio**: preços de insumo desatualizados/hardcoded distorcem custo estimado apresentado ao agrônomo.

## 17. Decisão para o Dry Run

**Opção B — automação depende de ação manual.**
Usar o fluxo atual no Dry Run. A ação humana que transforma o laudo em tarefa é: usuário com papel `agronomo` ou `admin`, tier PROFISSIONAL, abre `SoilDiagnosisDialog` para uma `AnaliseSolo` existente, seleciona manualmente a safra ativa no dropdown, e clica no botão que dispara `POST /agricola/analises-solo/{id}/gerar-tarefas?safra_id=...`. **Atenção**: antes do Dry Run, evitar cenário com recomendação de Potássio positiva devido ao bug do item 8, ou o Dry Run falhará com `KeyError`.

## 18. Menor próximo passo recomendado

Fora do escopo desta auditoria implementar, mas o menor próximo passo seria: (1) corrigir `PRECOS["POTASSIO"]` → `PRECOS["K2O"]` (correção de 1 linha, não uma nova arquitetura); (2) adicionar uma consulta de dedupe em `vincular_e_gerar_tarefas` antes de criar cada tarefa (checar `SafraTarefa` existente com mesmo `analise_solo_id`+`safra_id`+`tipo`). Não se recomenda investir no motor `RegraAgronomica` até haver um consumidor real e dados de seed — hoje é custo morto.
