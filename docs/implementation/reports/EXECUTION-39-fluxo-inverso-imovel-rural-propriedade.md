# EXECUTION-39 - Fluxo inverso de vínculo: Imóvel Rural -> Propriedade existente

## Causa raiz

O fluxo de cadastro/edição de Imóvel Rural não propagava `propriedade_id` para o backend e, portanto, não acionava a criação/reuso do vínculo canônico `PropriedadeImovel`.

Além disso:

- o `CREATE/UPDATE` de `ImovelRural` não chamava um helper idempotente para garantir o vínculo;
- o frontend não oferecia seleção de Propriedade existente;
- o payload do formulário não enviava `propriedade_id` nem `tipo_vinculo`;
- o botão de criação no Playwright depende de `PermissionGuard`, o que exigiu ajuste do mock de autenticação para tentar validar o fluxo.

## Arquivos alterados

Backend:

- `services/api/imoveis/routers/imovel.py`
- `services/api/imoveis/services/imovel_service.py`
- `services/api/core/cadastros/propriedade_imovel/service.py`
- `services/api/tests/unit/imoveis/test_imovel_router.py`
- `services/api/tests/unit/imoveis/test_imovel_service.py`
- `services/api/tests/unit/propriedade_imovel/test_service.py`
- `services/api/tests/integration/test_exec39_fluxo_inverso_imovel_propriedade.py`

Frontend:

- `apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx`
- `apps/web/tests/e2e/cadastros-imoveis.spec.ts`

## Migration

Nao houve migration.

`alembic heads` continua em `09df6fa43b49 (head)`.

## Regra implementada no CREATE

Quando `propriedade_id` e informado no `CREATE` de Imovel Rural:

- busca `Propriedade` e `ImovelRural` no mesmo tenant;
- cria ou reaproveita um `PropriedadeImovel` ativo;
- usa `tipo_vinculo = PROPRIEDADE_PRINCIPAL` por padrao quando nao informado;
- nao duplica o vinculo se a relacao ja existir;
- nao transforma `Propriedade` em fonte fundiaria;
- nao transforma `ImovelRural` em dominio operacional.

## Regra implementada no UPDATE

Quando `propriedade_id` e enviado no `PATCH` de Imovel Rural:

- o backend reaplica a mesma garantia idempotente de vínculo;
- se o vínculo já existir ativo, ele é reaproveitado;
- se o vínculo não existir, ele é criado no mesmo tenant;
- se `propriedade_id` não for enviado, o update preserva somente o Imovel Rural.

## Regra implementada na listagem de Imóveis Rurais

Nao houve alteracao de query nesta execucao.

A listagem continua usando `GET /imoveis/` com filtro por tenant/unidade produtiva, e a correcao central ficou no fluxo de CREATE/UPDATE para garantir que o `ImovelRural` oficial exista e permaneça visivel na listagem.

## Comportamento frontend

- adicionada selecao opcional de Propriedade no formulario de Imoveis Rurais;
- o campo envia `propriedade_id` apenas quando o usuario seleciona uma Propriedade;
- `tipo_vinculo` segue como opcional interno com default `PROPRIEDADE_PRINCIPAL`;
- `numero_matricula` permanece como campo oficial;
- `tenant_id` nao e enviado no payload;
- foram adicionados ids e `aria-labels` para estabilizar a automacao e o acesso.

## Testes executados

Backend:

- `services/api/.venv/bin/alembic heads`
- `services/api/.venv/bin/pytest services/api/tests/unit/imoveis/test_imovel_router.py services/api/tests/unit/imoveis/test_imovel_service.py services/api/tests/unit/propriedade_imovel/test_service.py services/api/tests/integration/test_exec39_fluxo_inverso_imovel_propriedade.py services/api/tests/integration/test_exec38_correcao_listagem_imovel_rural.py services/api/tests/integration/propriedade_imovel/test_router.py -q`
- `git diff --check`

Frontend:

- `pnpm exec tsc --noEmit`

Playwright:

- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts --project=chromium`
- `pnpm exec playwright test tests/e2e/cadastros-imoveis.spec.ts -g "cria imóvel vinculando" --project=chromium`

## Resultado dos testes

Backend:

- `36 passed` na suíte focada executada para esta execucao.

Frontend:

- `pnpm exec tsc --noEmit` passou.

Playwright:

- o spec completo de `cadastros-imoveis` falhou em um caso antigo de navegacao para `visao-fundiaria`;
- o teste novo de criacao/vinculo tambem falhou neste ambiente porque o botao `Novo Imóvel` nao ficou exposto no mock de autenticacao do spec.

## Riscos encontrados

- o fluxo de Playwright ainda depende do estado de permissao/mock do spec;
- o spec de imóveis tem um caso antigo de navegacao que nao passou nesta execucao, independente da correcao do vínculo;
- a regra idempotente agora cria/reaproveita o vinculo canônico no backend, mas nao foi adicionada uma nova query de listagem nesta execucao.

## Pendencias reais

- estabilizar o Playwright do cadastro de imóveis para o fluxo de criação;
- revisar o caso antigo de navegacao para `visao-fundiaria` no spec de `cadastros-imoveis` se ele for exigido como bloqueante.

## Compatibilidade preservada

- `Propriedade` continua no dominio operacional;
- `ImovelRural` continua sendo a fonte oficial fundiaria/documental;
- `PropriedadeImovel` continua sendo a ponte canonica N:N;
- nao houve migration;
- nao houve ruptura no contrato de listagem de Imóveis Rurais;
- nao houve remocao de legado.
