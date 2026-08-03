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

### Fase 2 (app de campo) — Backend — ✅ COMPLETO E TESTADO — Frontend — ❌ NÃO INICIADO

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

## 5. Pendente para a próxima sessão

1. **App de campo (apps/campo) — frontend**, consumindo os 3 endpoints já prontos:
   - Tela de listagem de requisições da OS (pode haver mais de uma).
   - Tela de confirmação de retirada com teclado de PIN, checklist de itens com campo de quantidade conferida.
   - Tela de confirmação de devolução (sobra de insumos).
2. **Devolução de ferramentas/patrimônio** — ainda não investigado. Usuário classificou como "domínio diferente" — checar se já existe alocação de equipamento/frota antes de desenhar.
3. Alerta automático (cron) para "colheita sem romaneio" — painel de pendências (abordagem manual) já existe; notificação proativa foi adiada, só retomar se o usuário pedir.
4. Possíveis ajustes de UX no fluxo de Plano Operacional/Requisições ainda não cobertos.

## 6. Como retomar

- Backend 100% pronto e testado para o fluxo completo (web + campo). Não precisa mexer em backend a menos que apareça bug.
- Próximo passo natural é criar as telas em `apps/campo/src/app/(campo)/campo/`, seguindo o padrão Dexie/IndexedDB + sync queue já usado nas outras telas de tarefa desse app.
