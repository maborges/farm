# LAUNCH-UX-HEDGE-01 - Commodity Safra Fallback

## Auditoria realizada

- Verifiquei `services/api/financeiro/hedge/` e confirmei que o contrato futuro ja persiste `commodity` e `commodity_id`.
- Auditei `services/api/agricola/safras/` e `services/api/agricola/cultivos/` para confirmar a relacao oficial `Safra -> Cultivo -> Commodity`.
- Auditei o frontend em `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/` para reaproveitar o formulario existente.
- Confirmei a existencia dos endpoints oficiais:
  - `GET /api/v1/safras`
  - `GET /api/v1/safras/{id}/cultivos`
  - `GET /api/v1/cadastros/commodities`
  - `POST /api/v1/financeiro/hedge/contratos`

## Componentes reutilizados

- `SafraService` e `CultivoService` existentes.
- Cadastro oficial de commodities em `core.cadastros.commodities`.
- Formulario e pagina de contratos do Hedge ja existentes.
- `react-hook-form`, `TanStack Query` e o design system atual de `shadcn/ui`.

## Endpoints reutilizados

- `GET /api/v1/safras`
- `GET /api/v1/safras/{id}/cultivos`
- `GET /api/v1/cadastros/commodities`
- `POST /api/v1/financeiro/hedge/contratos`

## Arquivos alterados

- `services/api/financeiro/hedge/service.py`
- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/ContratosClient.tsx`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/commodity-resolution.ts`
- `apps/web/tests/e2e/hedge-commodity-ux.spec.ts`

## O que mudou

- A commodity do contrato agora e derivada primeiro dos cultivos da safra.
- Se a safra tiver commodity conhecida, o campo fica somente leitura na UI.
- Se a safra nao permitir derivacao, o formulario cai para a lista oficial de commodities.
- Se nao houver safra, o formulario permanece no modo manual com a lista oficial.
- O backend rejeita divergencia entre safra e commodity com erro explicito.

## Testes executados

- `services/api/.venv/bin/pytest services/api/tests/integration/enterprise/test_hedge_mvp.py -q`
- `cd apps/web && pnpm exec eslint src/app/'(dashboard)'/dashboard/financeiro/hedge/contratos/ContratosClient.tsx src/app/'(dashboard)'/dashboard/financeiro/hedge/contratos/commodity-resolution.ts`
- `git diff --check`
- `git -C apps/web diff --check`

## Validacoes executadas

- `services/api/.venv/bin/pytest services/api/tests/integration/enterprise/test_hedge_mvp.py -q` passou.
- `eslint` nos arquivos alterados do frontend passou.
- `git diff --check` passou.
- `git -C apps/web diff --check` passou.

## Limitacoes remanescentes

- `cd apps/web && pnpm exec tsc --noEmit` falhou por erros preexistentes fora deste escopo em:
  - `src/app/(dashboard)/dashboard/financeiro/hedge/mtm/page.tsx`
  - `src/app/(dashboard)/dashboard/financeiro/hedge/painel/page.tsx`
  - `src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`
- `pnpm exec playwright test tests/e2e/hedge-commodity-ux.spec.ts --project=chromium` falhou no ambiente atual porque o Chromium nao conseguiu iniciar com o sandbox disponivel.
- `services/api/.venv/bin/ruff check services/api/financeiro/hedge/service.py services/api/tests/integration/enterprise/test_hedge_mvp.py` ainda aponta dividas antigas do modulo Hedge; os trechos novos foram tratados, mas o arquivo grande possui pendencias legadas fora deste ajuste.

## Aceite

- Nenhuma migration foi criada.
- Nenhum model novo foi criado.
- Nenhum CRUD novo foi criado.
- `commodity` permaneceu persistida no backend.
- `commodity` continua sendo enviada no payload.
- A Safra passou a definir Commodity automaticamente quando possivel.
- Quando nao foi possivel derivar, a lista oficial de commodities foi usada.
- Contratos sem Safra continuam suportados.
- A arquitetura do Hedge permaneceu intacta.
- Nao houve duplicacao de codigo funcional.
