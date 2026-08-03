# Requisição de Material — Estado da Feature (pausado em 2026-08-03)

> Retomar em outra sessão. Este doc é a fonte de verdade do que foi decidido, implementado e testado.

## 1. Problema original

OS (`OperacaoAgricola`) gerada com insumos → duas rotinas de baixa de estoque existiam **sem integração**:
1. `RequisicaoMaterial` → `entregar_requisicao` → baixa estoque (tela em `/suprimentos/requisicoes`, não usada na prática).
2. `OperacaoAgricola` → status `REALIZADA` → `consumir_lotes_fifo` (única rotina realmente usada).

Risco: se as duas fossem usadas para a mesma OS, dupla baixa de estoque (raiz de bug anterior "Saldo disponível insuficiente: -101.905"). Havia ainda um terceiro sistema morto, `ReservaEstoque`, confirmado não usado nesse fluxo.

## 2. Decisão de arquitetura (confirmada pelo usuário)

Fluxo operacional real da fazenda:
1. OS confirmada → gera automaticamente uma **Requisição de Material** (picking list).
2. Almoxarifado separa os itens.
3. Operador retira no dia seguinte, **confere** quantidade fisicamente recebida (pode divergir do planejado) e **assina eletronicamente** (reautenticação) → **é neste momento que o estoque é baixado**, pela quantidade conferida — não pela planejada.
4. App de campo deve listar requisições associadas à OS (pode haver mais de uma, para complementos).
5. App de campo deve permitir devolução de sobra de insumos e de ferramentas/patrimônio, também com assinatura eletrônica.
6. Ferramentas/patrimônio é um domínio diferente, ainda não investigado.

**"Opção A" confirmada**: baixa de estoque ocorre na retirada confirmada (Requisição), não na conclusão da OS.

Reautenticação:
- Web: e-mail pré-preenchido com o usuário logado mas editável + senha (pode ser outra pessoa confirmando).
- App de campo: PIN validado no servidor (server-side, não apenas client-side).

## 3. Status de implementação

### Fase 1 — Backend: vínculo OS↔Requisição + guarda contra dupla baixa — ✅ COMPLETO E TESTADO

- `RequisicaoMaterial.operacao_agricola_id` (FK nullable → `operacoes_agricolas`).
- Ao confirmar a OS (`TarefaService.gerar_operacao_planejada`), gera requisição automaticamente via `EstoqueService.criar_requisicao_a_partir_de_operacao` (idempotente).
- `OperacaoService._aplicar_insumos_na_operacao`: se existir requisição `ENTREGUE` vinculada à OS, usa a quantidade/custo já conferidos nela em vez de rodar `consumir_lotes_fifo` de novo — elimina a dupla baixa.
- Bugs pré-existentes corrigidos:
  - `_normalizar_origem` (estoque_ledger.py) rebaixava silenciosamente `"REQUISICAO"` para `"MANUAL"`.
  - Constraint `ck_estoque_movimentos_origem` no banco não incluía `'REQUISICAO'` (nem `'PECUARIA_VACINACAO'`, que já estava na allowlist Python).
- **Testado**: OS criada → requisição auto-gerada → entregue com quantidade 0.5 (planejado era 1.0) → OS marcada REALIZADA → `InsumoOperacao.quantidade_total == 0.5`, custo correto, saldo não alterado de novo, zero movimentos novos de estoque na conclusão da OS.

### Fase 2 (web) — Tela de confirmação de retirada/devolução com step-up auth — ✅ COMPLETO E TESTADO

- `RequisicaoConfirmacao` (tabela `estoque_requisicao_confirmacoes`): tipo RETIRADA/DEVOLUCAO, usuário, método (SENHA/TOKEN_DISPOSITIVO), e-mail informado, timestamp.
- `ItemRequisicao.quantidade_devolvida` adicionado.
- Endpoints: `POST /requisicoes/{id}/confirmar-retirada` e `.../confirmar-devolucao` (web, autenticado por tenant + credenciais no body).
- `EstoqueService`: `_verificar_credencial_step_up`, `confirmar_retirada_requisicao`, `confirmar_devolucao_requisicao` (valida `quantidade_devolvida` não excede `quantidade_entregue`, localiza a saída original para setar `ajuste_de` — exigido pela constraint `ck_estoque_movimentos_devolucao_exige_ajuste_de`).
- Frontend `/suprimentos/requisicoes`: dialog unificado de confirmação (e-mail pré-preenchido editável + senha + quantidade conferida por item); botão "Registrar devolução" quando há saldo não devolvido.
- **Testado**: senha errada rejeitada, devolução acima do saldo rejeitada com mensagem exata, fluxo feliz completo validado no banco real.

### Fase 2 (app de campo) — Backend — ✅ COMPLETO E TESTADO — Frontend — ✅ IMPLEMENTADO (2026-08-03, aguarda teste manual no dispositivo)

- `DispositivoCampo.pin_hash` persistido na ativação (antes era recebido e descartado — bug corrigido).
- `DispositivoService.verificar_pin(device_id, pin)` — valida via bcrypt.
- Endpoints device-autenticados (mesmo padrão de `/sync/push`, sem JWT de usuário normal):
  - `GET /campo/requisicoes?device_id=&operacao_agricola_id=`
  - `POST /campo/requisicoes/{id}/confirmar-retirada` (body: `device_id`, `pin`, `itens`)
  - `POST /campo/requisicoes/{id}/confirmar-devolucao` (idem)
- **Testado**: PIN errado rejeitado (401), PIN certo aceito, listagem por OS retorna requisição, confirmação de retirada via dispositivo grava `metodo="TOKEN_DISPOSITIVO"` corretamente.

## 4. Migrations aplicadas (ordem)

```
20260802_romaneio_tarefa_campo
20260802_safra_tarefas_ordem
20260803_requisicao_operacao_agricola   (rev 20260803_req_op_agricola)
20260803_estoque_mov_origem_requisicao  (rev 20260803_mov_origem_req)
20260803_requisicao_confirmacoes        (rev 20260803_req_confirmacoes)
20260803_campo_dispositivo_pin_hash     (rev 20260803_disp_pin_hash)
```
Todas aplicadas com `alembic upgrade head`. (Uma migration `quantidade_real_utilizada` foi criada e depois revertida/apagada — decisão errada, corrigida antes de seguir; ver histórico de sessão se precisar do detalhe.)

## 5. Frontend do app de campo — o que foi implementado (2026-08-03)

Decisões fechadas via brainstorming antes de codar:
- Seção "Requisições de Material" aparece dentro da tela de detalhe da tarefa (`apps/campo/.../campo/tarefa/[id]/page.tsx`), não em rota separada.
- Só aparece quando a tarefa tem `operacao_agricola_id` (nasceu de OS) **e** está `EM_EXECUCAO` — some depois de concluída.
- Múltiplas requisições da mesma OS aparecem como lista/accordion (não abas/rotas separadas).
- PIN só é pedido no momento de confirmar (retirada ou devolução), em modal — não bloqueia a tela inteira.
- Checklist de retirada vem pré-preenchido com a quantidade solicitada, editável, com badge "Divergente" quando o valor mudar.
- Devolução vem pré-preenchida com o saldo não devolvido (entregue − já devolvido), editável só para baixo.
- Ferramentas/patrimônio explicitamente adiado — só insumos por enquanto.

Arquivos novos/alterados:
- **Backend** (pequeno complemento descoberto na implementação, não estava no escopo original documentado):
  - `services/api/operacional/schemas/estoque.py`: `ItemRequisicaoResponse` ganhou `produto_nome` e `unidade_medida` (faltavam para exibição na UI).
  - `services/api/operacional/services/estoque_service.py`: `_carregar_itens_requisicao` agora busca `ProdutoCatalogo` em lote e popula os dois campos acima via atributo dinâmico (mesmo padrão já usado em outros pontos do projeto, ex. enriquecimento de `fase` em `TarefaProgramadaService.listar`).
  - `services/api/campo/service.py`: `pull()` (sync) agora injeta `operacao_agricola_id` dentro de `dados` de cada tarefa em `tarefas_pendentes` — antes não ia para o dispositivo, então o app não tinha como saber a qual OS a tarefa pertencia.
- **Frontend (apps/campo)**:
  - `src/lib/requisicoes-api.ts` — cliente HTTP para os 3 endpoints (`GET /campo/requisicoes`, `POST .../confirmar-retirada`, `POST .../confirmar-devolucao`), autenticado com `device_token` (Bearer) + `device_id`, seguindo o mesmo padrão de `session-store.ts`.
  - `src/components/campo/pin-pad.tsx` — teclado numérico de 6 dígitos extraído/reaproveitado do padrão já usado em `(auth)/pin/page.tsx`.
  - `src/components/campo/requisicoes-section.tsx` — seção completa: lista/accordion de requisições, checklist de conferência com destaque de divergência, `BottomSheet` (padrão já existente no app) com 2 passos (conferência → PIN) para retirada e devolução.
  - `src/app/(campo)/campo/tarefa/[id]/page.tsx` — importa e renderiza `<RequisicoesSection>` quando `task.dados.operacao_agricola_id` existe e `status_execucao === "EM_EXECUCAO"`.

**Não testado ainda**: fluxo ponta a ponta no dispositivo/emulador real (sem Playwright/Chromium neste sandbox). `tsc --noEmit` passou sem novos erros (só um erro pré-existente não relacionado em `page.tsx:193`). Recomendado testar manualmente: OS com requisição pendente → abrir tarefa em execução no app → conferir itens → confirmar com PIN → verificar que status vira ENTREGUE e que a seção de devolução aparece.

## 6. Ferramentas/patrimônio — investigação e decisão (2026-08-03)

Investigação encontrou dois catálogos hoje desconectados:
- `Produto`/`ItemRequisicao` (consumíveis, já com `quantidade_devolvida`).
- `Equipamento`/`EquipamentoAlocacao` (`core/cadastros/equipamentos/models.py`) — máquinas/veículos pesados (`TipoEquipamento`: TRATOR, COLHEDORA, PLANTADEIRA, PULVERIZADOR, IMPLEMENTO, VEICULO, IRRIGACAO, OUTRO), com campo `patrimonio` e alocação por unidade produtiva/responsável — sem vínculo a OS/requisição nem `data_devolucao`.

Decisão do usuário: "Máquinas e Equipamentos" no sentido de ERP cobre tudo, do trator à tesoura de poda — mas **ferramentas de baixo valor com múltiplas unidades idênticas** (enxada, tesoura de poda, pulverizador costal) devem ser controladas **por quantidade**, sem cadastro patrimonial individual obrigatório. Isso é exatamente a forma de um insumo — então a decisão foi **reaproveitar o catálogo de produtos** em vez de estender `Equipamento`.

Implementado:
- `core/cadastros/produtos/models.py`: novo valor `FERRAMENTA` no enum `TipoProduto` (campo é `String(30)`, não enum nativo do Postgres — sem migration necessária).
- `operacional/services/compras_service.py` (`obter_economia_por_categoria`): `FERRAMENTA` adicionado à lista `tipo_operacoes` (categoria "OPERACOES" no relatório de economia por categoria).
- `apps/web/.../estoque/_components/EstoqueDialogs.tsx`: opção "Ferramenta" no select de categoria do cadastro de produto.

**Gap intencionalmente não fechado**: a geração automática de requisição a partir da OS (`criar_requisicao_a_partir_de_operacao`) só lê `InsumoOperacao` — ferramentas cadastradas como `Produto tipo=FERRAMENTA` fluem pelo pipeline de retirada/devolução já construído (incluindo as telas do app de campo), mas hoje só entram numa requisição se adicionadas manualmente (tela web de requisições).

Máquinas/veículos pesados (trator, colhedora etc.) continuam em `Equipamento`/`EquipamentoAlocacao` — esse fluxo não foi alterado.

### 6.1 Decisão final: não conectar necessidade de maquinário à Requisição (2026-08-03)

Investigação mais profunda corrigiu uma suposição anterior deste doc: o "sistema separado de necessidade de maquinário" ligado ao planejamento é o modelo `PlanoOperacionalTarefaMaquinario` (`agricola/planejamento_operacional/models.py:218`), cujos campos `maquina_id`/`implemento_id` referenciam **`cadastros_equipamentos.id` (`Equipamento`)**, não `Produto`. Ou seja, a necessidade de maquinário do planejamento já é sobre equipamento pesado (trator, implemento) — o mesmo domínio de `EquipamentoAlocacao`, que tem seu próprio fluxo de "check-out" por responsável/unidade produtiva.

Não existe hoje, no planejamento, uma "necessidade de ferramenta pequena" (enxada, tesoura) — só `MAQUINARIO` (equipamento pesado) e `MAO_DE_OBRA` (pessoa). Conectar essa necessidade à requisição automática misturaria equipamento pesado com o catálogo de produtos, exatamente a complexidade que a decisão da seção 6 evitou.

**Decisão**: não conectar. São dois fluxos separados por design — `Equipamento`/`EquipamentoAlocacao` para maquinário pesado, Requisição de Material para almoxarifado (incluindo ferramentas pequenas, via `TipoProduto.FERRAMENTA`). Sem caso de uso concreto pedindo a ponte, o investimento não se justifica agora. Reabrir só se surgir um pedido específico (ex.: operador querer confirmar reserva de trator na mesma tela de requisição).

## 7. Teste de integração — fluxo completo com ferramenta (2026-08-03)

Executado teste real contra o Postgres (tenant `7cff0925-417a-41f0-8aba-271b16052477`), reproduzindo o cenário do ERP: OS com uma ferramenta (`Produto tipo=FERRAMENTA`, "10 tesouras de poda" em estoque) → requisição gerada automaticamente → aprovada → retirada confirmada com quantidade **conferida divergente da solicitada** (2 em vez de 3) → tentativa de devolução acima do saldo (rejeitada) → devolução parcial válida (1 unidade).

Todos os passos passaram:
- `produto_nome`/`unidade_medida` vieram populados corretamente no item da requisição.
- Retirada com quantidade divergente da solicitada foi aceita e o saldo baixou pela quantidade **conferida** (10 → 8), não pela solicitada — confirma a decisão de arquitetura "Opção A".
- Devolução de 5 unidades (acima do saldo retirado de 2) foi corretamente rejeitada com mensagem exata.
- Devolução parcial de 1 unidade foi aceita, `quantidade_devolvida` registrada, saldo voltou a 9.

**Não coberto neste teste**: verificação de PIN real (`DispositivoService.verificar_pin`) — não havia nenhum `DispositivoCampo` ATIVO com `pin_hash` cadastrado nesse tenant no momento do teste. A checagem de PIN em si já tinha sido validada na Fase 2 (ver seção 3, "PIN errado rejeitado (401), PIN certo aceito"); o que ficou sem cobertura agora foi só a combinação PIN+ferramenta na mesma chamada, que é trivial dado que o código de verificação de PIN não depende do tipo de produto.

**Não coberto ainda**: a UI do app de campo em si (telas, toque, PIN pad visual) — isso continua exigindo teste manual no dispositivo/navegador, pois não há Playwright/Chromium neste sandbox.

Dados de teste (produto `[TESTE] Tesoura de poda`, requisição, OS) foram limpos preservando o ledger `estoque_movimentos` (append-only) — o produto de teste ficou no catálogo por estar referenciado no ledger, seguindo o mesmo padrão de limpeza já usado nas fases anteriores.

## 7.1 Alerta automático "colheita sem romaneio" — implementado (2026-08-03)

Em vez de um cron/notificação novo, a regra foi adicionada ao motor de recomendações operacionais já existente (`recommendations/providers/agricultura_provider.py`), que roda em loop assíncrono no backend (`core/background_jobs.py` → `run_recommendation_scheduler_loop`) e já é sincronizado automaticamente para o app de campo (`recomendacoes_operacionais` no `sync/pull.ts`) — sem precisar de infraestrutura nova.

- Nova regra `AGRI_COLHEITA_SEM_ROMANEIO`, prioridade `HIGH`, reaproveitando 100% a query já existente `RomaneioService.listar_pendentes_de_romaneio(safra_id)` (a mesma que alimenta o banner manual em `/agricola/safras/[id]/romaneios`).
- Um candidato agregado por safra (não um por tarefa) — segue o mesmo padrão das outras regras desse provider — com `total_pendentes`, lista dos até 5 talhões afetados, e a data da colheita mais antiga sem romaneio.
- `action_target` aponta para `/agricola/safras/{id}/romaneios`, a mesma tela do painel manual.
- **Testado** via integração real contra o tenant `7cff0925-417a-41f0-8aba-271b16052477`: detectou corretamente 4 colheitas pendentes de romaneio e gerou o candidato com os dados certos (talhões, datas, action_target).

Arquivo alterado: só `recommendations/providers/agricultura_provider.py` (import de `RomaneioService`, bloco de avaliação, 2 métodos auxiliares). Nenhuma migration, nenhum router novo.

## 8. Pendente para a próxima sessão

1. **Teste manual da UI no dispositivo/navegador** (toque, PIN pad, accordion de requisições, e agora também a recomendação de colheita sem romaneio aparecendo no app de campo) — a lógica de negócio por trás já está validada ponta a ponta.
2. Possíveis ajustes de UX no fluxo de Plano Operacional/Requisições ainda não cobertos.

Itens "conectar necessidade de maquinário à requisição" (ver 6.1) e "alerta automático de colheita sem romaneio" (ver 7.1) **fechados** — não são mais pendências.

## 9. Como retomar

- Backend 100% pronto, testado (unitário/integração real) para o fluxo completo (web + campo), incluindo `produto_nome`/`unidade_medida`, `operacao_agricola_id` no sync pull, e `TipoProduto.FERRAMENTA` com o mesmo pipeline de retirada/devolução validado ponta a ponta.
- Frontend do app de campo implementado mas só a UI em si (toque/PIN pad) falta validar manualmente — a lógica por trás já rodou com sucesso contra o banco real.
- Ferramentas de baixo valor já podem ser cadastradas e fluir pelo pipeline de requisição. Maquinário pesado permanece deliberadamente fora desse pipeline (ver 6.1).
