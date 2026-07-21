# SOIL-PLAN-EXEC-03 — Correção Mínima para Liberar o Dry Run

> Data: 2026-07-20

## 1. Resumo executivo

Foram corrigidos, de forma cirúrgica, os 4 defeitos identificados nas auditorias SOIL-PLAN-EXEC-01/02 que impediam o fluxo Laudo de Solo → Tarefa → Operação Planejada de ser executado em Dry Run com segurança: (1) bug de `PRECOS["POTASSIO"]` (já corrigido em commit anterior, confirmado presente), (2) falta de idempotência na geração de `SafraTarefa` a partir de `AnaliseSolo`, (3) ausência de exigência de aprovação antes de `gerar_operacao_planejada()`, e (4) falta de validação de que a safra informada pertence ao tenant da análise. Nenhuma tabela nova, evento de domínio, job ou motor de recomendação foi criado — toda a correção reutiliza `SafraTarefa`, `TarefaService`, `SafraService` e `OperacaoAgricola` existentes.

## 2. Defeitos corrigidos

1. **Potássio** — confirmado que `PRECOS["K2O"]` já estava em uso nas linhas 195/282/295/554/607 de `agricola/analises_solo/service.py` (fix de sessão anterior). Nenhuma alteração adicional necessária.
2. **Idempotência** — `vincular_e_gerar_tarefas` agora consulta `SafraTarefa` ativa antes de criar cada tipo de tarefa.
3. **Aprovação obrigatória** — `TarefasService.gerar_operacao_planejada()` agora exige status `APROVADA`.
4. **Validação de safra** — `vincular_e_gerar_tarefas` valida a safra via `SafraService.get_or_fail` (filtra por `tenant_id`).

## 3. Arquivos alterados

- `services/api/agricola/analises_solo/service.py` — método `_tarefa_ativa_existente` (novo, privado), validação de safra, checagem de idempotência nos 4 blocos (CALAGEM, ADUBACAO_FOSFORO, ADUBACAO_POTASSIO, ADUBACAO_NITROGENIO), retorno alterado de `list[UUID]` para `dict`.
- `services/api/agricola/analises_solo/router.py` — endpoint `POST /{id}/gerar-tarefas` adaptado ao novo contrato de retorno.
- `services/api/agricola/tarefas/service.py` — `gerar_operacao_planejada()` agora exige `status == "APROVADA"`.
- `services/api/tests/unit/agricola/test_soil_plan_exec_03.py` (novo) — 6 testes focados cobrindo os 4 defeitos.

## 4. Regra de idempotência

Antes de criar cada tarefa recomendada (CALAGEM / ADUBACAO_FOSFORO / ADUBACAO_POTASSIO / ADUBACAO_NITROGENIO), o service consulta `SafraTarefa` filtrando por `tenant_id + analise_solo_id + safra_id + talhao_id + tipo` e por status em `{PENDENTE_APROVACAO, APROVADA, EM_EXECUCAO, CONCLUIDA}` (constante `STATUS_TAREFA_ATIVA`). Se encontrar uma tarefa ativa, reaproveita o `id` existente em vez de criar duplicata. Nenhuma unique constraint nova foi criada — a garantia é por consulta prévia no service, como solicitado.

## 5. Tratamento de tarefas canceladas/invalidadas

Tarefas com status `CANCELADA` ou `INVALIDADA` **não** entram no filtro `STATUS_TAREFA_ATIVA` e, portanto, não bloqueiam a geração de uma nova tarefa equivalente — comportamento coberto pelo teste `test_tarefa_cancelada_permite_gerar_nova_tarefa_equivalente`.

## 6. Aprovação obrigatória

`gerar_operacao_planejada()` agora rejeita qualquer status diferente de `APROVADA` com `BusinessRuleError`, incluindo a mensagem do status atual. O comportamento para tarefa já `APROVADA` foi preservado integralmente (cria `OperacaoAgricola` com `status="PLANEJADA"`, mesmos vínculos de tenant/safra/talhão/tarefa). A regra de estoque (FIFO só em `REALIZADA`) não foi tocada.

## 7. Validação da safra

`vincular_e_gerar_tarefas` chama `SafraService(session, tenant_id).get_or_fail(safra_id)` antes de gerar recomendações — isso garante existência da safra e pertencimento ao mesmo tenant (o `BaseService.get_or_fail` já filtra por `tenant_id`, lançando `EntityNotFoundError` caso a safra seja de outro tenant ou não exista). **Limitação deliberadamente mantida**: não foi validado que a safra tenha vínculo declarado com o talhão da análise (`SafraTalhao`), pois o model atual não garante essa relação de forma determinística sem alterar regras de negócio fora do escopo. Isso fica registrado como risco remanescente, não como bug corrigido.

## 8. Contrato do endpoint

`POST /analises-solo/{id}/gerar-tarefas` agora retorna:
```json
{
  "tarefas_geradas": ["<uuid>", ...],
  "tarefas_existentes": ["<uuid>", ...],
  "quantidade_gerada": 2,
  "quantidade_existente": 2
}
```
O campo `tarefas_geradas` já existia; `tarefas_existentes`, `quantidade_gerada` e `quantidade_existente` são novos — nenhum campo foi removido, preservando compatibilidade com consumidores atuais.

## 9. Comportamento do frontend

Implementado em complemento a esta correção, em `apps/web/src/components/agricola/soil-diagnosis-dialog.tsx`:
- **Múltiplos cliques**: o botão "Gerar Planejamento" já usava `disabled={... || mutation.isPending}` e o botão "Fechar" já usava `disabled={mutation.isPending}` — comportamento confirmado correto, sem alteração necessária.
- **Tarefas novas vs já existentes**: `onSuccess` foi ajustado para ler `tarefas_geradas` e `tarefas_existentes` do novo contrato do endpoint (seção 8) e exibir toast diferenciado: sucesso quando há tarefas novas (mencionando também quantas já existiam, se houver), `toast.info` quando só havia tarefas já existentes, e `toast.info` quando não há recomendação aplicável.
- **Erro não fecha o diálogo silenciosamente**: `onError` já apenas exibia `toast.error` sem chamar `onClose()` — comportamento confirmado correto, sem alteração necessária.

Nenhum redesenho de tela, consolidação de rotas ou alteração de nomenclatura de módulos de recomendação econômica foi feito. Validado com `tsc --noEmit` (typecheck) sem erros no arquivo alterado; `npm run lint` do projeto não cobre este arquivo (script restrito a uma lista fixa de arquivos), então não foi executável para esta mudança.

## 10. Testes criados

Arquivo `services/api/tests/unit/agricola/test_soil_plan_exec_03.py`, estilo mock-based (mesmo padrão de `test_tarefas_integridade_documental.py`, sem tocar banco real):
1. `test_potassio_gera_tarefa_adubacao_potassio_sem_keyerror` — K2O não quebra o fluxo.
2. `test_segunda_chamada_nao_duplica_tarefas_ativas` — idempotência.
3. `test_tarefa_cancelada_permite_gerar_nova_tarefa_equivalente` — cancelada não bloqueia.
4. `test_safra_de_outro_tenant_e_rejeitada` — validação de tenant na safra.
5. `test_tarefa_pendente_aprovacao_bloqueia_operacao_planejada` — bloqueio funcional (`BusinessRuleError`, não 500).
6. `test_tarefa_aprovada_gera_operacao_planejada` — fluxo feliz preservado.

## 11. Comandos executados

```bash
.venv/bin/python -m pytest tests/unit/agricola/test_soil_plan_exec_03.py -q
.venv/bin/python -m pytest tests/unit/agricola/test_tarefas_integridade_documental.py -q
.venv/bin/python -m ruff check agricola/analises_solo/service.py agricola/analises_solo/router.py agricola/tarefas/service.py tests/unit/agricola/test_soil_plan_exec_03.py
```

## 12. Resultados

- `test_soil_plan_exec_03.py`: **6 passed**.
- `test_tarefas_integridade_documental.py` (regressão): **11 passed**.
- `ruff check`: nenhum erro novo introduzido nos arquivos-alvo além de débito técnico pré-existente no `service.py`/`tarefas/service.py` (E501/E701/N806/I001 já presentes antes desta mudança, não relacionados à correção). Os testes novos aplicaram um ajuste de estilo espontâneo do linter do ambiente (renomeação de variável de mock), sem impacto funcional.

Estes testes são unitários com `AsyncMock`/`MagicMock` (sem conexão real a PostgreSQL), seguindo o padrão já existente no módulo `agricola/tarefas`. Não foi necessário conectar a um PostgreSQL local para esta suíte; nenhum SQLite foi usado.

## 13. Riscos remanescentes

- Não há validação de vínculo declarado safra↔talhão (ver seção 7).
- `TarefaCampo` continua sem FK para `SafraTarefa` (fora de escopo, já documentado em SOIL-PLAN-EXEC-01).

## 14. Limitações deliberadamente mantidas

- Nenhum gatilho automático pós-laudo foi criado.
- Nenhum evento de domínio/outbox foi criado.
- Nenhuma migration foi criada — idempotência garantida via consulta prévia.
- `AnaliseSolo.safra_id` não foi adicionado; seleção de safra continua manual.

## 15. Veredicto para o Dry Run (revisado)

Ver seção 16 — um segundo caminho de geração de tarefas foi encontrado após a primeira publicação deste relatório e corrigido na mesma sessão. O veredicto final consolidado está na seção 17.

## 16. Correção adicional — caminho paralelo em `cultivo-analise-drawer.tsx`

Durante a validação do fluxo em `/agricola/safras/[id]`, identificou-se um **segundo componente** de frontend com wizard de 4 steps (`apps/web/src/components/agricola/cultivo-analise-drawer.tsx`, steps "Análise → Região → Laudo → Confirmar") que também gera `SafraTarefa(origem="SOLO")` a partir de uma `AnaliseSolo`, mas **por um caminho diferente** do `SoilDiagnosisDialog`: em vez de chamar `POST /analises-solo/{id}/gerar-tarefas` (protegido na seção 4), o botão "Confirmar" itera a lista de tarefas do preview e chama `POST /safras/{id}/tarefas` **uma vez por tarefa**, que cai direto em `TarefaService.criar()`. Esse caminho **não** era coberto pela proteção de idempotência aplicada em `AnaliseSoloService.vincular_e_gerar_tarefas` — cliques repetidos em "Confirmar" duplicariam as tarefas.

**Correção aplicada:** a checagem de idempotência foi centralizada em `TarefaService.criar()` (`services/api/agricola/tarefas/service.py`), cobrindo os dois caminhos de uma vez:
- Novo método `_tarefa_solo_ativa_existente(analise_solo_id, safra_id, talhao_id, tipo)`, mesma consulta usada em `analises_solo/service.py`.
- `criar()` agora verifica essa condição sempre que `dados.origem == "SOLO"` e `dados.analise_solo_id` está presente; se já existir tarefa ativa equivalente, retorna a existente em vez de criar duplicata. Tarefas `origem="MANUAL"` (e outras origens) não são afetadas — a checagem é pulada.
- A constante `STATUS_TAREFA_ATIVA` foi movida de `analises_solo/service.py` para `agricola/tarefas/service.py` (fonte única) e importada de volta em `analises_solo/service.py`, evitando duas definições divergentes do mesmo conceito.

Nenhuma mudança foi feita no botão "Só vincular" (que não cria `SafraTarefa`, apenas faz o `PATCH` de vínculo `analise_solo_id` na área de cultivo) nem no drawer em si — a correção ficou inteiramente no backend, no ponto único de criação de tarefa.

**Arquivos adicionais alterados:**
- `services/api/agricola/tarefas/service.py` — `STATUS_TAREFA_ATIVA`, `_tarefa_solo_ativa_existente()`, guard em `criar()`.
- `services/api/agricola/analises_solo/service.py` — import de `STATUS_TAREFA_ATIVA` em vez de definição local.
- `services/api/tests/unit/agricola/test_soil_plan_exec_03.py` — 3 testes novos: reaproveita tarefa ativa existente quando chamado direto com `origem="SOLO"`; cria normalmente quando não há tarefa ativa; ignora a checagem para `origem="MANUAL"`.

**Testes:** 9/9 em `test_soil_plan_exec_03.py`; regressão completa de `tests/unit/agricola/` (215 testes): 211 passed, 4 failed — as 4 falhas (`test_analytics_request_cache`, `test_caderno_listar_alertas`, `test_cert_calibracao_sanitaria`, `test_field_core03_caderno_status`) são pré-existentes e não referenciam `tarefas.service` nem `analises_solo`, confirmadas sem relação com esta mudança. `ruff check` nos 3 arquivos Python alterados: nenhum erro novo além do débito técnico pré-existente já registrado na seção 12.

## 17. Veredicto final para o Dry Run

**GO PARA O DRY RUN** — os 4 defeitos originais (potássio, idempotência, aprovação obrigatória, validação de tenant da safra) e o gap adicional do caminho paralelo (`cultivo-analise-drawer.tsx` → `TarefaService.criar()`) estão corrigidos e testados. Os dois pontos de entrada do fluxo (`SoilDiagnosisDialog` e `cultivo-analise-drawer`) agora convergem para a mesma proteção de idempotência no backend. Ressalva única remanescente: ausência de validação declarada safra↔talhão (seção 7) — limitação de modelo pré-existente, não bloqueia o cenário manual do Dry Run.

## 18. Correção crítica adicional — router forçava `origem="MANUAL"`

Após validar a correção da seção 16, o usuário reportou em uso real que o botão "Confirmar" do drawer continuava criando a mesma tarefa duas ou mais vezes para o mesmo talhão. Investigação apontou a causa raiz: `agricola/tarefas/router.py:49` (antes da correção) continha `dados.origem = "MANUAL"`, sobrescrevendo **incondicionalmente** o campo `origem` enviado pelo cliente antes de chamar `TarefaService.criar()`.

**Efeito do bug:**
- O `cultivo-analise-drawer.tsx` envia `origem: "SOLO"` no corpo do `POST /safras/{id}/tarefas`, mas o router trocava para `"MANUAL"` antes da checagem de idempotência (seção 16) — como o guard só ativa quando `dados.origem == "SOLO"`, a proteção nunca era executada nesse caminho, permitindo duplicatas a cada clique em "Confirmar".
- Efeito colateral mais grave: as tarefas geradas pelo laudo de solo estavam sendo persistidas com `origem="MANUAL"` (perda de rastreabilidade da origem) e nascendo diretamente `APROVADA` em vez de `PENDENTE_APROVACAO` — pulando a barreira de aprovação humana antes de `gerar_operacao_planejada()` (seção 6).

**Correção:** removida a linha `dados.origem = "MANUAL"` do endpoint. Confirmado que o único outro consumidor do endpoint (`safra-tarefas.tsx`, form de tarefa manual) nunca envia `origem` no payload — o schema `TarefaCreate.origem` já default para `"MANUAL"`, então o comportamento do form manual é preservado sem qualquer override forçado no router. `origem="SOLO"` enviado pelo drawer agora chega intacto em `TarefaService.criar()`, onde a checagem de idempotência da seção 16 passa a funcionar como projetado.

**Arquivo alterado:** `services/api/agricola/tarefas/router.py` (2 linhas removidas/ajustadas: override de `origem` e texto do `summary` do endpoint).

**Testes adicionados** em `test_soil_plan_exec_03.py`:
- `test_router_criar_tarefa_preserva_origem_solo_enviada_pelo_cliente` — regressão específica do bug: chama a função do router diretamente e confirma que `dados.origem == "SOLO"` chega intacto em `TarefaService.criar()`.
- `test_router_criar_tarefa_manual_sem_origem_permanece_manual` — confirma que o form manual, que não envia `origem`, continua criando tarefa `MANUAL` normalmente (nenhuma regressão no caminho legítimo original).

**Resultado:** 11/11 testes em `test_soil_plan_exec_03.py`; regressão completa de `tests/unit/agricola/` — 213 passed, 4 failed (mesmas 4 falhas pré-existentes e não relacionadas já registradas na seção 16, sem novas falhas). `ruff check` no arquivo alterado: nenhum erro novo (avisos `B008`/`UP035`/`UP007` são padrão idiomático do FastAPI, pré-existentes em todo o arquivo, não relacionados a esta mudança).

**Este era o bug real reportado pelo usuário** — a proteção de idempotência da seção 16 estava correta em isolamento, mas nunca era alcançada em produção por causa deste override no router. Com as duas correções combinadas (guard em `criar()` + remoção do override), o fluxo completo (`SoilDiagnosisDialog` e `cultivo-analise-drawer`, incluindo cliques repetidos em "Confirmar") está protegido contra duplicação.

## 19. Preenchimento de `fase` na geração automática de tarefas

O usuário questionou por que o campo `fase` da `SafraTarefa` não era preenchido na geração via laudo de solo, e confirmou que o conteúdo atual de `obs` (texto prescritivo da recomendação — dose, produto, prazo de incorporação, ajuste por irrigação) está correto e deve ser mantido.

**Causa:** nos 4 blocos de `AnaliseSoloService.gerar_recomendacoes`/`vincular_e_gerar_tarefas`, o `TarefaCreate(...)` nunca passava `fase`, e o schema default para `None`. O mesmo valia para o caminho do `cultivo-analise-drawer` (seção 16), que também nunca envia `fase` no payload.

**Correção:** preenchimento centralizado em `TarefaService.criar()` (mesmo ponto único já usado para idempotência e para o bug do router, seções 16 e 18) — cobre os dois caminhos de entrada sem exigir mudança em `analises_solo/service.py` nem no frontend:
- Novo método `_fase_atual_safra(safra_id)`: `SELECT Safra.status WHERE id=safra_id AND tenant_id=tenant_id`.
- Em `criar()`, quando `dados.fase is None` **e** `dados.origem != "MANUAL"` (ou seja, para `SOLO`/`TEMPLATE`), a tarefa é criada com `fase = status atual da safra` (`PLANEJADA`, `PREPARO_SOLO`, `PLANTIO`, `DESENVOLVIMENTO`, `COLHEITA`, `POS_COLHEITA` ou `ENCERRADA` — os mesmos valores usados no frontend em `FASE_LABEL`, `safra-tarefas.tsx:66-74`).
- Se o chamador informar `fase` explicitamente, o valor informado é preservado (não há sobrescrita).
- Tarefas `origem="MANUAL"` continuam **sem** preenchimento automático — preserva a opção "Sem fase" do form manual (`safra-tarefas.tsx`), que é uma escolha explícita do usuário, não uma omissão a ser corrigida.

**Arquivo alterado:** `services/api/agricola/tarefas/service.py` — import de `Safra`, método `_fase_atual_safra`, lógica de preenchimento em `criar()`.

**Testes adicionados** em `test_soil_plan_exec_03.py`:
- `test_criar_solo_preenche_fase_com_status_atual_da_safra_quando_nao_informada` — SOLO sem `fase` herda o status da safra.
- `test_criar_solo_preserva_fase_explicita_quando_informada` — SOLO com `fase` explícita não consulta a safra nem sobrescreve.
- `test_criar_manual_nao_preenche_fase_automaticamente` — MANUAL nunca aciona o preenchimento automático.

**Resultado:** 14/14 testes em `test_soil_plan_exec_03.py`; regressão completa de `tests/unit/agricola/`: 216 passed, 4 failed (mesmas 4 falhas pré-existentes e não relacionadas, sem novas falhas). `ruff check`: nenhum erro novo além do débito técnico pré-existente já registrado.

## 21. Bug real de `obs` vazia — chave errada no preview do drawer

O usuário reportou que, na prática, a observação da tarefa planejada não aparecia mesmo havendo recomendações no laudo. Investigação revelou que a seção 19 tratou apenas de `fase` — a causa da `obs` vazia era um bug **diferente e independente**, isolado no endpoint de preview usado exclusivamente pelo `cultivo-analise-drawer.tsx`.

**Causa raiz:** `agricola/cultivos/service.py:312`, dentro de `CultivoService.gerar_tarefas_solo()` (usado por `GET /safras/{id}/cultivos/{cultivo_id}/areas/{id}/tarefas-solo`, que alimenta o preview do Step 4 do drawer e é a fonte de `t.obs` enviado depois em `POST /safras/{id}/tarefas`), lia `rec.get("obs")`. Porém o dicionário retornado por `AnaliseSoloService.gerar_recomendacoes()` usa a chave `"observacao"` em todos os 4 blocos (calagem/fósforo/potássio/nitrogênio — confirmado em `analises_solo/service.py:250,274,305,342`), nunca `"obs"`. Resultado: `rec.get("obs")` sempre retornava `None`, e cada `TarefaSoloGerada` do preview chegava ao frontend com `obs: null` — daí a tarefa final nascer sem observação, mesmo quando a recomendação existia e tinha texto prescritivo.

**Importante — esse bug era isolado do caminho do `SoilDiagnosisDialog`:** o endpoint `POST /analises-solo/{id}/gerar-tarefas` (`AnaliseSoloService.vincular_e_gerar_tarefas`, seções 4/6/16) sempre leu `cal["observacao"]`, `p["observacao"]`, `k["observacao"]`, `n["observacao"]` corretamente — nunca teve esse bug. Ou seja, tarefas geradas pelo `SoilDiagnosisDialog` sempre tiveram `obs` preenchida; apenas as geradas pelo `cultivo-analise-drawer` (via botão "Confirmar") ficavam sem observação.

**Correção:** troca pontual de `rec.get("obs")` para `rec.get("observacao")` em `agricola/cultivos/service.py:312`. Uma linha, nenhuma mudança de contrato, nenhuma mudança de schema (`TarefaSoloGerada.obs` já existia e já era exposto corretamente ao frontend — só nunca recebia valor).

**Arquivo alterado:** `services/api/agricola/cultivos/service.py` (1 linha).

**Teste adicionado** em `test_soil_plan_exec_03.py`: `test_gerar_tarefas_solo_preview_preenche_obs_com_observacao_da_recomendacao` — mocka `AnaliseSoloService.gerar_recomendacoes` retornando uma recomendação de potássio com `"observacao"` preenchida e confirma que `TarefaSoloGerada.obs` reflete esse texto (antes da correção, o teste falharia com `obs is None`).

**Resultado:** 15/15 testes em `test_soil_plan_exec_03.py`; regressão completa de `tests/unit/agricola/`: 217 passed, 4 failed (mesmas 4 falhas pré-existentes e não relacionadas, sem novas falhas). `ruff check` em `cultivos/service.py`: nenhum erro novo na linha alterada (achados remanescentes são débito técnico pré-existente — `E501`/`I001` em outras linhas do arquivo).

## 22. Bug real de tarefas "sumindo" da lista — chave de invalidação de cache errada

O usuário reportou que tarefas geradas a partir da análise de solo passaram a não aparecer em "Tarefas Planejadas", e que antes das correções de idempotência elas apareciam. Investigação: a tarefa **é persistida corretamente** (confirmado pelo backend, seções 16/18) — o problema é puramente de cache no frontend.

**Causa raiz:** a lista "Tarefas Planejadas" (`apps/web/src/components/agricola/safra-tarefas.tsx:195`) usa `useQuery({ queryKey: ["safras", safraId, "tarefas"], ... })`. Porém:
- `SoilDiagnosisDialog` invalidava `queryKey: ["safra-tarefas"]` — uma chave de **um único elemento, com nome diferente** (`"safra-tarefas"` vs `"safras"`), que nunca é prefixo de `["safras", safraId, "tarefas"]`.
- `cultivo-analise-drawer.tsx` invalidava `queryKey: ["tarefas", area.safra_id]` — também não bate (`"tarefas"` na primeira posição vs `"safras"` na lista real).

Como o `QueryClient` global (`apps/web/src/components/providers.tsx:24`) usa `staleTime: 1000 * 60 * 5` (5 minutos), o React Query não refaz a busca automaticamente ao montar a lista — ele confia no cache existente até a invalidação explícita ou até o cache expirar. Como nenhuma das duas chaves usadas pelos dois pontos de geração de tarefa batia com a chave real da lista, a invalidação **nunca surtia efeito**: a lista continuava mostrando o snapshot anterior por até 5 minutos (ou até um refresh manual da página, que reseta o cache do client).

**Por que parecia relacionado à correção de duplicidade:** não há relação causal direta — esse bug de chave sempre existiu nos dois componentes. É provável que, no fluxo de teste anterior às correções desta sessão, o usuário tenha dado reload manual da página logo após gerar as tarefas (o que reconstrói o `QueryClient` e força a busca), mascarando o problema. Com o fluxo agora sendo testado via clique em "Confirmar"/"Gerar Planejamento" sem reload subsequente, o cache desatualizado ficou visível.

**Correção:** as duas invalidações foram corrigidas para usar a chave real da lista:
- `soil-diagnosis-dialog.tsx`: `qc.invalidateQueries({ queryKey: ["safras", selectedSafraId, "tarefas"] })`.
- `cultivo-analise-drawer.tsx`: `queryClient.invalidateQueries({ queryKey: ["safras", area.safra_id, "tarefas"] })`.

**Arquivos alterados:** `apps/web/src/components/agricola/soil-diagnosis-dialog.tsx`, `apps/web/src/components/agricola/cultivo-analise-drawer.tsx` (1 linha cada). Validado com `tsc --noEmit` sem erros nos dois arquivos.

**Nenhum teste automatizado backend aplicável** — é um bug puramente de cache de frontend, fora do escopo dos testes pytest desta sessão; não há suíte de testes de componente React configurada no projeto para este componente (`apps/web` usa Playwright para e2e, não testes de unidade de componente isolado).

## 23. Bug crítico — apenas 1 de 4 tarefas era gerada pelo drawer (colapso de tipo)

O usuário reportou que, ao confirmar uma análise com 4 nutrientes precisando de correção (calagem, fósforo, potássio, nitrogênio) via botão "Confirmar" do `cultivo-analise-drawer`, apenas **1** tarefa era criada — antes da correção de duplicidade (seções 16/18), as 4 eram criadas (só que duplicando a cada novo clique).

**Causa raiz:** `agricola/cultivos/service.py`, em `CultivoService.gerar_tarefas_solo()` (o endpoint de preview que alimenta o Step 4 do drawer), o loop:
```python
mapeamento = [
    ("calagem", "Calagem", "CALCARIO"),
    ("fosforo", "Adubação Fosfatada", "P₂O₅"),
    ("potassio", "Adubação Potássica", "K₂O"),
    ("nitrogenio", "Adubação Nitrogenada", "N"),
]
for chave, descricao, nutriente in mapeamento:
    ...
    tarefas.append(TarefaSoloGerada(nutriente=nutriente, ...))  # bug: símbolo químico, não a chave
```
preenchia `TarefaSoloGerada.nutriente` com o **símbolo químico** ("CALCARIO", "P₂O₅", "K₂O", "N") em vez da **chave semântica** ("calagem", "fosforo", "potassio", "nitrogenio"). No frontend, `cultivo-analise-drawer.tsx` usa esse valor para resolver o `tipo` da tarefa:
```js
const NUTRIENTE_TIPO: Record<string, string> = {
    calagem: "CALAGEM", fosforo: "ADUBACAO_FOSFORO",
    potassio: "ADUBACAO_POTASSIO", nitrogenio: "ADUBACAO_NITROGENIO",
};
tipo: NUTRIENTE_TIPO[t.nutriente] ?? "OUTRO",
```
Como `t.nutriente` nunca batia com nenhuma chave do mapa (símbolo vs. slug), **as 4 tarefas eram enviadas ao backend com `tipo: "OUTRO"` idêntico**. Isso sempre foi assim — mas antes da idempotência (seção 16/18) não importava, porque cada `POST /safras/{id}/tarefas` criava uma linha nova incondicionalmente (daí "geravam as 4", ainda que todas mal-tipadas como `OUTRO` em vez do tipo correto). Com a checagem de idempotência em `TarefaService.criar()` (chave: tenant+analise_solo+safra+talhao+**tipo**), a 1ª tarefa (calagem, tipo="OUTRO") era criada normalmente; a 2ª, 3ª e 4ª (fósforo/potássio/nitrogênio, também tipo="OUTRO" por causa do bug) eram então **reconhecidas como duplicatas da 1ª** e reaproveitadas em vez de criadas — resultando em só 1 tarefa persistida.

**Correção:** troca pontual de `nutriente=nutriente` para `nutriente=chave` em `agricola/cultivos/service.py:306`; a variável de loop antes usada só para esse fim foi renomeada para `_simbolo` (mantida para clareza do código, mas sem uso funcional). Nenhuma mudança no frontend foi necessária — `NUTRIENTE_TIPO` já esperava a chave semântica desde sempre; o bug era só o backend enviando o valor errado.

**Arquivo alterado:** `services/api/agricola/cultivos/service.py` (2 linhas: valor do campo `nutriente` e nome da variável de loop).

**Testes adicionados** em `test_soil_plan_exec_03.py`:
- Assert adicional no teste existente de `obs`: confirma que `nutriente == "potassio"` (chave semântica), não o símbolo `"K₂O"`.
- `test_gerar_tarefas_solo_preview_usa_chave_semantica_para_todos_os_nutrientes` — gera preview com as 4 recomendações positivas e confirma que os 4 itens retornam `nutriente` distintos e corretos (`{"calagem", "fosforo", "potassio", "nitrogenio"}`), prevenindo regressão do colapso em `tipo="OUTRO"`.

**Resultado:** 16/16 testes em `test_soil_plan_exec_03.py`; regressão completa de `tests/unit/agricola/`: 218 passed, 4 failed (mesmas 4 falhas pré-existentes e não relacionadas). `ruff check`: nenhum erro novo nas linhas alteradas.

## 24. Veredicto final (revisado)

**GO PARA O DRY RUN** — mantém-se o veredicto da seção 17/20/23, agora incluindo: (a) preenchimento correto de `fase` (seção 19); (b) correção do bug de `obs` vazia no drawer (seção 21); (c) correção da chave de invalidação de cache (seção 22); (d) correção do colapso de tipo que fazia só 1 de N tarefas sobreviver no drawer (seção 23). Recomenda-se ao usuário testar novamente o cenário completo (análise com múltiplas recomendações → "Confirmar" → conferir 4 tarefas distintas com tipos corretos em "Tarefas Planejadas") para validação final antes do Dry Run.
