# LAUNCH-UX-HEDGE-01 - Commodity derivada da Safra e fallback por lista de Commodities

## Auditoria realizada

- `services/api/financeiro/hedge/schemas.py`
- `services/api/financeiro/hedge/router.py`
- `services/api/financeiro/hedge/service.py`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/ContratosClient.tsx`
- hooks e servicos existentes de safra
- hooks e servicos existentes de commodities

## Decisao de produto

- O backend continua exigindo `commodity` no contrato.
- A UX do formulario de contratos passou a priorizar a safra:
  - quando a safra resolve uma commodity/cultura, o campo fica bloqueado e preenchido automaticamente;
  - quando nao ha safra, ou a safra nao resolve commodity, o usuario seleciona em lista suspensa.
- A persistencia de `commodity` foi mantida sem alterar modelo, tabela ou migration.

## Implementacao

### Backend

- Adicionada validacao defensiva em `services/api/financeiro/hedge/service.py`.
- Quando `safra_id` esta presente e a safra resolve uma commodity canonica:
  - a commodity do payload precisa corresponder ao valor derivado;
  - divergencias sao rejeitadas com erro claro.
- Quando a safra nao resolve commodity, o comportamento legado foi preservado.
- Nenhum schema foi removido ou tornado opcional.

### Frontend

- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/page.tsx` passou a carregar safra e commodities para inicializacao da tela.
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/ContratosClient.tsx` passou a:
  - derivar commodity a partir da safra quando possivel;
  - bloquear a edicao manual nesse caso;
  - exibir fallback manual em select quando a safra nao resolve;
  - manter envio de `commodity` no submit.
- Criado `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/commodity-resolution.ts` para resolver commodity a partir da safra sem duplicar regra no componente.

## Arquivos alterados

- `services/api/financeiro/hedge/service.py`
- `services/api/tests/integration/enterprise/test_hedge_mvp.py`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/ContratosClient.tsx`
- `apps/web/src/app/(dashboard)/dashboard/financeiro/hedge/contratos/commodity-resolution.ts`
- `apps/web/tests/e2e/hedge-commodity-ux.spec.ts`

## Testes executados

- `services/api/.venv/bin/pytest services/api/tests/integration/enterprise/test_hedge_mvp.py -q`
- `cd apps/web && pnpm exec playwright test tests/e2e/hedge-commodity-ux.spec.ts --project=chromium`
- `cd apps/web && pnpm exec eslint "src/app/(dashboard)/dashboard/financeiro/hedge/contratos/ContratosClient.tsx" "src/app/(dashboard)/dashboard/financeiro/hedge/contratos/page.tsx" "src/app/(dashboard)/dashboard/financeiro/hedge/contratos/commodity-resolution.ts" "tests/e2e/hedge-commodity-ux.spec.ts" --no-warn-ignored`
- `git diff --check`

## Validacao adicional

- O typecheck global do `apps/web` nao ficou limpo por erros preexistentes fora deste escopo:
  - `src/app/(dashboard)/dashboard/financeiro/hedge/mtm/MtMClient.tsx`
  - `src/app/(dashboard)/dashboard/financeiro/hedge/registros/RegistrosClient.tsx`
  - `src/app/(dashboard)/dashboard/pecuaria/animais/page.tsx`

## Limitacoes remanescentes

- O aviso do React Compiler sobre `form.watch()` em `ContratosClient.tsx` permanece como warning de lint, sem erro funcional.
- A resolucao da commodity por safra depende da compatibilidade entre `Safra.cultura` e os cadastros de commodity por nome ou codigo.

## Criterios de aceite confirmados

- `commodity` continua persistido no backend.
- `commodity` nao foi removido do schema.
- Safra selecionada define commodity automaticamente quando possivel.
- Quando nao e possivel derivar, o usuario seleciona commodity em lista suspensa.
- Contrato sem safra continua suportado.
- O payload sempre envia `commodity`.
- Nenhuma migration foi criada.
- Nenhum model duplicado foi criado.
- Nenhum endpoint duplicado foi criado.
