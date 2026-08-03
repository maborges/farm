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

**Gap intencionalmente não fechado agora**: a geração automática de requisição a partir da OS (`criar_requisicao_a_partir_de_operacao`) só lê `InsumoOperacao` — ferramentas cadastradas como `Produto tipo=FERRAMENTA` fluem pelo pipeline de retirada/devolução já construído (incluindo as telas do app de campo), mas hoje só entram numa requisição se adicionadas manualmente (tela web de requisições). Existe também um sistema **separado** de "necessidade de maquinário" (`NecessidadeRecurso`, tipo `MAQUINARIO`, em `agricola/a1_planejamento/models.py`) ligado ao planejamento de tarefas — decidiu-se **não conectar os dois ainda**, para não expandir o escopo sem necessidade confirmada.

Máquinas/veículos pesados (trator, colhedora etc.) continuam em `Equipamento`/`EquipamentoAlocacao` — esse fluxo não foi alterado.

## 7. Pendente para a próxima sessão

1. **Teste manual/E2E do fluxo de campo** (retirada e devolução, insumos e agora também ferramentas) em ambiente real, já que não há automação de browser neste sandbox.
2. **Conectar `NecessidadeRecurso` (MAQUINARIO) à geração automática de requisição**, se o usuário confirmar que quer que ferramentas apareçam automaticamente na requisição da OS em vez de serem adicionadas manualmente.
3. Alerta automático (cron) para "colheita sem romaneio" — painel de pendências (abordagem manual) já existe; notificação proativa foi adiada, só retomar se o usuário pedir.
4. Possíveis ajustes de UX no fluxo de Plano Operacional/Requisições ainda não cobertos.

## 8. Como retomar

- Backend 100% pronto e testado para o fluxo completo (web + campo), incluindo `produto_nome`/`unidade_medida`, `operacao_agricola_id` no sync pull, e agora `TipoProduto.FERRAMENTA`.
- Frontend do app de campo implementado mas sem teste manual/E2E ainda — validar no dispositivo antes de considerar fechado.
- Ferramentas de baixo valor já podem ser cadastradas e fluir pelo pipeline de requisição; falta só decidir se a geração automática a partir da OS deve incluir necessidades de maquinário.
