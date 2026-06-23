# EXECUTION-41 - Visualizacao bidirecional Propriedade <-> Imoveis Rurais

## Causa raiz
- A visao consolidada estava correta no dominio, mas a experiencia do frontend ainda dependia de seletores e fixtures pouco aderentes ao DOM real.
- A listagem de Imoveis Rurais usava `initialData` de forma a congelar a primeira renderizacao quando o snapshot inicial vinha vazio no ambiente de teste.
- Os testes E2E de visao territorial/fundiaria ainda supunham rótulos unicos onde a tela exibe o mesmo dado em mais de uma secao.

## Arquivos alterados
- `apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx`
- `apps/web/src/components/territorial/territorial-visao.tsx`
- `apps/web/tests/e2e/cadastros-imoveis.spec.ts`
- `apps/web/tests/e2e/territorial-visao.spec.ts`
- `services/api/imoveis/routers/imovel.py`
- `services/api/imoveis/services/imovel_service.py`
- `services/api/tests/unit/imoveis/test_imovel_service.py`
- `services/api/tests/unit/propriedade_imovel/test_visao_service.py`

## Arquivos criados
- `docs/implementation/reports/EXECUTION-41-visualizacao-bidirecional-propriedade-imoveis-rurais.md`

## Migration
- Nao houve migration.

## Ajustes backend
- A listagem de Imoveis Rurais passou a retornar todos os registros do tenant sem filtro implicito por contexto selecionado.
- O service de Imovel passou a anotar cada item com:
  - `propriedades_vinculadas_count`
  - `vinculo_status`
- A visao territorial e a visao fundiaria continuam usando `PropriedadeImovel` como ponte canonica N:N.
- As visoes agregadas retornam os vinculos com metadados relacionais:
  - tipo de vinculo
  - vigencia
  - area vinculada
  - percentual vinculado
  - indicador de principal

## Ajustes frontend
- A listagem de Imoveis Rurais deixou de depender do contexto ativo como filtro implcito.
- A tabela agora mostra status de vinculo e quantidade de propriedades vinculadas.
- A visao territorial ganhou uma leitura mais explicita dos Imoveis Rurais vinculados.
- A visao fundiaria ganhou uma leitura mais explicita das Propriedades vinculadas.
- Os links cruzados passaram a ficar visiveis em ambas as telas.
- O `initialData` da listagem foi trocado por `placeholderData` para nao bloquear o fetch do cliente em ambiente de E2E.
- O erro `imovel.area_total_ha.toFixed is not a function` foi eliminado com formatacao defensiva.

## Comportamento da listagem de Imoveis Rurais
- Mostra todos os Imoveis Rurais do tenant.
- Nao aplica filtro implicito por Propriedade.
- Exibe `VINCULADO` ou `NÃO VINCULADO`.
- Exibe a quantidade de propriedades vinculadas.

## Comportamento da visao territorial
- Mostra os Imoveis Rurais vinculados a Propriedade.
- Exibe matricula, CAR, CCIR, NIRF, tipo de vinculo, area vinculada, percentual e badge de principal.
- Mostra link para a visao fundiaria do Imovel Rural.

## Comportamento da visao fundiaria
- Mostra as Propriedades vinculadas ao Imovel Rural.
- Exibe tipo de vinculo, vigencia, area vinculada, percentual e badge de principal.
- Mostra link para a visao territorial da Propriedade.

## Testes executados
- `pnpm exec tsc --noEmit`
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts --project=chromium`
- `pnpm exec playwright test tests/e2e/territorial-visao.spec.ts --project=chromium`
- `services/api/.venv/bin/pytest services/api/tests/unit/imoveis/test_imovel_service.py services/api/tests/unit/propriedade_imovel/test_visao_service.py services/api/tests/integration/propriedade_imovel/test_visao_router.py services/api/tests/integration/test_exec39_fluxo_inverso_imovel_propriedade.py -q`
- `./.venv/bin/alembic heads`
- `git diff --check`

## Resultado dos testes
- TypeScript: passou.
- Playwright `cadastros-imoveis.spec.ts`: 4 passed.
- Playwright `territorial-visao.spec.ts`: 6 passed.
- Backend pytest: 19 passed.
- Alembic heads: 1 head (`09df6fa43b49`).
- `git diff --check`: passou.

## Riscos encontrados
- O ambiente de E2E depende de permissao elevada para subir o Chromium headless.
- A listagem de Imoveis Rurais continua usando um snapshot inicial do SSR; o contrato foi estabilizado para nao travar o fetch do cliente, mas esse ponto ainda depende do comportamento do backend no arranque.

## Pendencias reais
- Nenhuma pendencia funcional identificada apos as validacoes executadas.

## Compatibilidade preservada
- Propriedade continua como dominio operacional.
- Imovel Rural continua como fonte oficial fundiaria/documental.
- PropriedadeImovel continua como ponte canonica N:N.
- Nao houve migration.
- Legado nao foi removido.
