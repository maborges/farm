# LAUNCH-W4 — Requisição de Insumos → OS → Campo → Estoque → Financeiro → Rentabilidade

## Auditoria realizada

Auditoria baseada exclusivamente no código-fonte em `services/api/operacional/`, `services/api/agricola/`, `services/api/financeiro/`, `apps/web/` e `apps/campo/`.

## Lacunas encontradas

- A requisição já existia com aprovação, separação e entrega em `services/api/operacional/services/estoque_service.py`.
- A entrega da requisição gerava baixa de estoque, mas não carregava contexto de safra para o lançamento financeiro automático.
- O frontend de requisições não expunha a origem vinculada quando a requisição nascia de OS/tarefa.
- Não havia teste específico provando a passagem de safra do fluxo de requisição para o lançamento financeiro.

## Implementações realizadas

- `services/api/operacional/services/estoque_service.py`
  - Adicionado resolvedor de safra para requisições com base em origem de OS/tarefa ou safra ativa da unidade produtiva.
  - A entrega de requisição passou a repassar `safra_id` para a baixa de estoque.
- `apps/web/src/app/(dashboard)/suprimentos/requisicoes/page.tsx`
  - Adicionado campo de origem vinculada para requisições com origem `ORDEM_SERVICO`.
  - A tela passou a buscar safras ativas do tenant e listar tarefas disponíveis para vínculo quando a origem é OS.
- `services/api/tests/unit/operacional/test_requisicao_financeiro_integration.py`
  - Adicionado teste do resolvedor de safra.
  - Adicionado teste do repasse de `safra_id` para a baixa financeira.

## Integrações reutilizadas

- `RequisicaoMaterial`
- `ItemRequisicao`
- `EstoqueMovimento`
- `LancamentoFinanceiro`
- `Safra`
- `SafraTarefa`
- `OperacaoAgricola`
- `Cultivo` / `CultivoArea`
- `AreaRural`

## Testes

- `services/api/.venv/bin/pytest services/api/tests/unit/operacional/test_requisicao_financeiro_integration.py -q`
- `services/api/.venv/bin/ruff check services/api/tests/unit/operacional/test_requisicao_financeiro_integration.py`
- `pnpm exec eslint 'src/app/(dashboard)/suprimentos/requisicoes/page.tsx'`
- `git diff --check`

## Validações

- O novo teste unitário passou.
- O lint do frontend alterado passou.
- A baixa de estoque continua centralizada no `EstoqueService`.
- O fluxo passou a carregar contexto suficiente para gerar efeito financeiro/rentabilidade quando a requisição estiver vinculada a uma OS/tarefa ou safra ativa.

## Limitações remanescentes

- A resolução de safra por fallback usa a safra ativa mais recente vinculada aos talhões da unidade quando a requisição não traz origem explícita.
- O arquivo `services/api/operacional/services/estoque_service.py` já carregava dívida histórica de lint fora do escopo desta mudança; a validação completa de `ruff check` nesse arquivo ainda acusa esse passivo preexistente.
