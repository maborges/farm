# Checklist por Fase — de template estático a processo rastreável

> Design em 2026-08-03; **implementado e testado no mesmo dia** (ver seção 8), incluindo a UI de "Minhas Pendências"/"sem responsável" (ver 8.2). Escopo do que ainda fica fora: resolução automática de talhão para `TAREFA_CAMPO` (ver 8.1) e notificação via motor de recomendações.

## 1. Problema identificado pelo usuário

Hoje o "checklist por fase" é só um **template que gera checklists** (`PhaseTemplateChecklistItem` → `SafraChecklistItem`), mas não gera **nenhum processo rastreável** dentro do acompanhamento da safra. Marcar um item como concluído é um checkbox solto — não abre uma tarefa, não atribui responsável, não tem prazo, e a validação de avanço de fase (`SafraService.avancar_fase`) só olha um booleano por item.

## 2. O que já existe hoje (investigado nesta sessão)

- `agricola/models/templates.py` — `PhaseTemplateChecklistItem` (definição do item no template: `titulo`, `descricao`, `obrigatorio`, `ordem`).
- `agricola/checklist/models.py` — `SafraChecklistItem` (instância por safra: `fase`, `concluido`, `usuario_id`, `concluido_em`, `cancelado`, `motivo_cancelamento`).
- `agricola/checklist/service.py` — `SafraChecklistService.gerar_para_fase(safra_id, cultura, fase)` já existe e instancia os itens do template para a safra.
- **Já é chamado automaticamente**: o componente web `apps/web/src/components/agricola/safra-checklist.tsx` (montado em `/agricola/safras/[id]/checklist`) dispara `POST .../checklist/{fase}/gerar` toda vez que a tela é aberta — não é um botão manual dependente de lembrar de clicar, mas também não é automático na *transição* de fase em si.
- `SafraService.avancar_fase` **já valida** que os itens `obrigatorio=True` da fase atual foram concluídos antes de permitir avançar — mas é um booleano simples (`concluido`/`não concluido`), sem os três níveis (OK/parcial/bloqueante) que o usuário quer.
- **Não existe** hoje: item de checklist gerando uma OS, uma tarefa de campo, uma requisição/pedido de compra, nem qualquer conceito de "responsável + prazo de resposta" (TODO) fora do que a própria OS/tarefa de campo já oferece via `operador_id`.

## 3. Decisões de desenho (conversa com o usuário)

1. **Item de checklist pode gerar processo real, não só um checkbox.** Antes de avançar de fase, a verificação deve retornar **OK / OK parcial / bloqueante** (não binário).
2. **Nem todo item gera OS.** OS (`OperacaoAgricola`) é inerentemente uma operação de campo (amarrada a talhão) — não deve ser generalizada para caber qualquer coisa. Em vez disso, o item de checklist ganha um campo `tipo_resultado` que decide o que ele gera:
   - **`TAREFA_CAMPO`** → gera uma OS normalmente, que já flui pelo pipeline existente: Plano Operacional → OS → tarefa de campo → Requisição de Material (tudo já construído e testado nesta sessão, doc irmã: `brainstorm-requisicao-material.md`).
   - **`SOLICITACAO_ESTOQUE`** → **pula a OS** e vai direto para o par Requisição de Material / Pedido de Compra. Exemplo motivador do usuário: item "conferir estoque de EPI" — verifica saldo, e se insuficiente, permite gerar a necessidade de compra diretamente, sem precisar de talhão/operação agrícola.
   - **`MANUAL`** (comportamento de hoje) → checkbox simples, sem geração de nada. É o "escape hatch" para qualquer ação futura ainda não modelada — evita ter que prever tudo agora.
3. **Critério de conclusão passa a ser o estado do artefato gerado**, não um booleano solto:
   - `TAREFA_CAMPO`: olha o status da OS/tarefa de campo.
   - `SOLICITACAO_ESTOQUE`: verifica o saldo do produto configurado no template.
     - **Saldo suficiente** → gera uma `ReservaEstoque` (`operacional/models/estoque.py:170` — já existe, "bloqueio de saldo para uso futuro garantido", com `referencia_tipo`/`referencia_id` genéricos, hoje sem nenhum fluxo real conectado a ela) vinculada ao item do checklist. Isso trava o saldo pra não ser consumido por outra coisa antes do uso real na fase, e o item vai direto pra `OK`.
     - **Saldo insuficiente** → segue pro Pedido de Compra, com **override manual**: se o saldo ainda não atende mas o pedido de compra já foi gerado, o usuário pode dar "OK parcial" justificando ("já providenciei a compra"), sem precisar esperar a entrega física.
   - `MANUAL`: continua sendo o checkbox direto.
4. **Responsável + prazo (TODO) só se aplica a `SOLICITACAO_ESTOQUE` e `MANUAL`.** `TAREFA_CAMPO` já tem "responsável" de graça — é o `operador_id` da OS/tarefa de campo, já rastreado, já com app de campo, já com ciclo de vida completo. Só os tipos sem OS por trás (`SOLICITACAO_ESTOQUE`, `MANUAL`) precisam de um conceito novo de atribuição com prazo, porque hoje nada rastreia "quem" e "até quando" para eles.
5. **Notificação do TODO reaproveita o motor de recomendações** (`recommendations/providers/agricultura_provider.py`, mesmo padrão usado nesta sessão para o alerta de "colheita sem romaneio") — não criar infraestrutura de notificação nova. Prazo vencendo/vencido sobe a prioridade da recomendação (escalonamento).

6. **Atribuição explícita vs. implícita — como a pessoa fica sabendo, e como um item sem dono aparece pra alguém assumir.** Investigado: o motor de recomendações já suporta notificação por e-mail direcionada via `context["notification_recipients"]` (`recommendations/notification_bridge.py:255`) — mas isso é só o canal de aviso, não um filtro de "isso é meu" na tela. Não existe hoje coluna de atribuição por usuário nas recomendações (só `scope_type`/`scope_id` genéricos, ex. safra). Por isso a fonte de verdade de "quem" continua sendo `responsavel_id` direto em `SafraChecklistItem`, consultado pela tela — o motor de recomendações só entra como canal de notificação, não como lista de tarefas em si.
   - `responsavel_id` setado (explícito) → item aparece em "Minhas Pendências" da pessoa (query direta `SafraChecklistItem.responsavel_id = usuario_atual`); recomendação gerada **com** `notification_recipients=[email da pessoa]` e o prazo.
   - `responsavel_id` nulo (implícito, ninguém assumiu ainda) → item aparece numa lista compartilhada "Pendências sem responsável" (visível a quem tem permissão de agir na fase — gerente/agrônomo), com ação **"Assumir"** (PATCH que seta `responsavel_id = usuario_atual`, só permitido enquanto nulo). Recomendação ainda é gerada, mas **sem** destinatário de e-mail específico (cai só no feed geral do tenant) — ninguém foi apontado ainda, não faz sentido mandar e-mail pessoal.

## 4. Modelo de dados proposto (rascunho, não implementado)

### `PhaseTemplateChecklistItem` (template) — novos campos
```python
tipo_resultado: Mapped[str] = mapped_column(String(30), default="MANUAL")
# TAREFA_CAMPO | SOLICITACAO_ESTOQUE | MANUAL

# Só relevante quando tipo_resultado == "TAREFA_CAMPO":
tipo_operacao_agricola: Mapped[str | None]  # tipo da OS a gerar (ex.: "MANUTENCAO", "APLICACAO")

# Só relevante quando tipo_resultado == "SOLICITACAO_ESTOQUE":
produto_id_padrao: Mapped[uuid.UUID | None]  # produto a verificar (ex.: EPI específico)
quantidade_minima: Mapped[float | None]
```

### `SafraChecklistItem` (instância) — novos campos
```python
tipo_resultado: Mapped[str]  # copiado do template no momento da geração
operacao_agricola_id: Mapped[uuid.UUID | None]  # se TAREFA_CAMPO, a OS gerada
reserva_estoque_id: Mapped[uuid.UUID | None]  # se SOLICITACAO_ESTOQUE e saldo suficiente
requisicao_material_id: Mapped[uuid.UUID | None]  # se SOLICITACAO_ESTOQUE e precisou de compra

responsavel_id: Mapped[uuid.UUID | None]  # só usado se tipo_resultado != TAREFA_CAMPO
prazo_resposta: Mapped[date | None]

status_verificacao: Mapped[str] = mapped_column(default="PENDENTE")
# PENDENTE | OK | OK_PARCIAL | BLOQUEANTE

justificativa_ok_parcial: Mapped[str | None]  # obrigatório quando status_verificacao == OK_PARCIAL
```

### `SafraService.avancar_fase` — mudança de comportamento
Hoje: conta itens `obrigatorio=True` com `concluido=False` e bloqueia se houver algum.
Proposto: para cada item obrigatório, computa `status_verificacao` (a partir do artefato vinculado ou override manual) e agrega:
- Todos `OK` → libera.
- Algum `OK_PARCIAL`, nenhum `BLOQUEANTE` → libera com aviso (mostrar quais itens estão parciais e por quê).
- Algum `BLOQUEANTE` → impede avanço, `forcar_avanco` continua existindo como escape para gestor (já existe hoje).

## 5. Arquivos que seriam impactados (implementação futura)

**Backend:**
- `services/api/agricola/models/templates.py` — campos novos em `PhaseTemplateChecklistItem`.
- `services/api/agricola/checklist/models.py` — campos novos em `SafraChecklistItem`.
- `services/api/agricola/checklist/service.py` — `gerar_para_fase` passa a criar o artefato (OS, ou reserva/requisição conforme saldo) para `tipo_resultado`; novo método de cálculo de `status_verificacao`. Para `SOLICITACAO_ESTOQUE` com saldo suficiente, chama `EstoqueService.criar_reserva` (já existe em `operacional/services/estoque_service.py:1707`, nenhum código novo de reserva necessário — só o `referencia_tipo`/`referencia_id` apontando pro `SafraChecklistItem`).
- `services/api/agricola/checklist/schemas.py` / `router.py` — expor os novos campos, endpoint de override manual com justificativa, endpoint `POST /checklist-itens/{id}/assumir` (seta `responsavel_id`, só se nulo), e endpoints de listagem "minhas pendências" (`responsavel_id = eu`) e "sem responsável" (`responsavel_id IS NULL AND tipo_resultado != TAREFA_CAMPO`).
- `services/api/agricola/safras/service.py` — `avancar_fase` usa o novo veredito de três níveis.
- `services/api/recommendations/providers/agricultura_provider.py` — nova regra para notificar `responsavel_id` do TODO com prazo (reaproveitando o padrão da regra `AGRI_COLHEITA_SEM_ROMANEIO` já implementada).
- Migration Alembic manual (nunca autogenerate, ver `CLAUDE.md` e lição já aprendida nesta sessão) para os campos novos nas duas tabelas.

**Frontend (apps/web):**
- `components/agricola/safra-checklist.tsx` — exibir o tipo de resultado, o artefato vinculado (link pra OS/reserva/requisição), o responsável/prazo quando aplicável, a ação de override manual com justificativa, e o botão "Assumir" quando `responsavel_id` nulo.
- Novo widget/seção "Minhas Pendências" (dashboard ou sidebar) — lista itens de checklist com `responsavel_id = usuário atual` e prazo, entre módulos/safras.
- Tela/formulário de template (`agricola/templates/[id]/page.tsx`, já mexemos nela nesta sessão) — permitir escolher `tipo_resultado` ao criar/editar um item de checklist do template.

## 6. Escopo explicitamente fora desta rodada

- Ferramentas/patrimônio como resultado de checklist (fora de escopo, seria outro `tipo_resultado` futuro).
- Qualquer UI de "inbox" genérica de TODOs — a entrega inicial usa a recomendação já existente como canal, sem tela dedicada de inbox.

## 8. Implementação (2026-08-03)

Migration `20260803_checklist_processo` aplicada; models, service, schemas e routers atualizados; frontend (`safra-checklist.tsx` + formulário de template) atualizado. Testado por integração real contra o Postgres (não só leitura de código):

- `SOLICITACAO_ESTOQUE` com saldo insuficiente → `status_verificacao=BLOQUEANTE`, veredito da fase = `BLOQUEANTE`.
- `assumir_item`: primeira chamada atribui `responsavel_id`; segunda chamada (item já atribuído) rejeitada corretamente.
- `override_manual` com justificativa → `status_verificacao=OK_PARCIAL`; veredito da fase passa a `OK_PARCIAL` (libera avanço, com aviso).
- `SOLICITACAO_ESTOQUE` com saldo suficiente → gera `ReservaEstoque` de verdade (reaproveitando `EstoqueService.criar_reserva`, já existente) e marca `OK`.
- Item `MANUAL` marcado concluído → `status_verificacao=OK` sincronizado.

Dados de teste limpos ao final (nenhum ledger de estoque tocado, produto de teste sem movimentos foi removido por completo).

### 8.1 O que ficou fora desta rodada (intencional)

- **Resolução automática de talhão para `TAREFA_CAMPO`**: o método `vincular_operacao(item_id, operacao_agricola_id)` existe no service, mas nada cria a OS automaticamente — quem gerar a OS (fluxo normal de Plano Operacional) precisa vincular manualmente ao item do checklist. Gerar OS "às cegas" sem talhão definido seria inventar uma decisão de UX que não foi discutida.
- **Notificação por e-mail via motor de recomendações** (seção 3.5/6 do desenho original): não implementada — os campos `responsavel_id`/`prazo_resposta` existem e são gravados, mas nenhuma regra nova foi adicionada a `recommendations/providers/agricultura_provider.py` para notificar automaticamente. Seguir o mesmo padrão de `AGRI_COLHEITA_SEM_ROMANEIO` quando for feito.
- **Combobox de produto** no formulário de template: por ora é um campo de texto livre para o UUID do produto (`produto_id_padrao`), não um seletor com busca. Funcional mas pouco amigável — trocar por um combobox de produtos quando houver tempo.

### 8.2 UI de "Minhas Pendências" — implementada (2026-08-03)

Novo componente `apps/web/src/components/agricola/minhas-pendencias-checklist.tsx`, autocontido (fetch próprio via `useQuery`, sem depender do orchestrator de fetch do dashboard global) — consome `GET /checklist/minhas-pendencias` e `GET /checklist/sem-responsavel`. Duas seções: "Atribuídas a mim" e "Sem responsável" (com botão "Assumir" chamando `POST .../checklist/itens/{id}/assumir`). Cada card linka para `/agricola/safras/{safra_id}/checklist`. O componente retorna `null` quando não há nenhuma pendência (não polui a tela à toa).

Plugado em `app/(dashboard)/dashboard/agricola/page.tsx`, logo abaixo do `PageHeader` — essa página foi escolhida por já ser o dashboard agrícola central (não o dashboard global multi-módulo, que tem um fetch orchestration mais complexo e não valia a pena mexer para esse escopo).

**Validado**: `tsc --noEmit` sem erros novos; smoke test HTTP (Puppeteer + Chromium local) confirmou a rota carrega com status 200 e sem erros de runtime no console. **Não validado visualmente com sessão autenticada** — o smoke test bateu no redirecionamento de login (esperado, sem sessão configurada no browser headless); a lógica de dados em si (endpoints, veredito, assumir) já foi validada por integração real contra o Postgres na seção 8.

## 9. Como retomar

Núcleo funcional completo: avaliação de estoque, assumir, override, veredito de 3 níveis, `avancar_fase` respeitando o novo veredito, e UI de Minhas Pendências/sem responsável — tudo pronto e testado. Pendências restantes, em ordem de prioridade: (1) notificação via recomendações, (2) combobox de produto no form de template, (3) decidir e implementar a criação de OS a partir de `TAREFA_CAMPO` (depende de resolver a questão do talhão), (4) validação visual com sessão real no navegador.
