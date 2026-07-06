# EXECUTION-38 - Revisao Auto-Vinculo Imoveis Rurais

## Contexto

O fluxo de cadastro das propriedades operacionais usa `UnidadeProdutiva` como entidade de entrada na tela de `Propriedades`, e não o service legado de `Propriedade`.
O auto-vinculo fundiario ja existia em `UnidadeProdutivaService`, mas a experiencia da pagina de `Imoveis Rurais` ainda tinha pontos de ruptura na leitura e no formulario.

## Causa Raiz

1. A pagina de `Imoveis Rurais` fazia fetch inicial com `situacao=all`, mas a rota aceitava apenas o enum `regular|pendente|irregular`, gerando erro de validacao na carga SSR.
2. O formulario de `Imoveis Rurais` estava usando o campo legado `matricula`, enquanto o backend oficial expunha `numero_matricula`.
3. O sync fundiario ja criava ou reutilizava `ImovelRural`, mas a reutilizacao de NIRF estava sendo feita sem escopo de tenant.

## O que foi ajustado

### CREATE / UPDATE

- Mantido o fluxo de CREATE/UPDATE em `UnidadeProdutivaService` para disparar o auto-vinculo fundiario.
- O helper de criacao sem validacao passou a respeitar o `tenant_id` na busca por NIRF.
- O fluxo continua preservando `UnidadeProdutiva` como dominio operacional, `ImovelRural` como fonte oficial e `PropriedadeImovel` como ponte oficial.

### Listagem de Imoveis Rurais

- A rota `GET /imoveis` passou a aceitar `situacao=all` como sinônimo de sem filtro.
- A pagina de `Imoveis Rurais` deixou de enviar `situacao=all` no fetch inicial SSR.
- O client de `Imoveis Rurais` passou a consumir e exibir `numero_matricula` de forma oficial.

### Compatibilidade

- O comportamento antigo de filtro por `regular|pendente|irregular` foi preservado.
- O auto-vinculo continua idempotente e sem duplicar `ImovelRural` ou `PropriedadeImovel`.

## Arquivos Alterados

- [`services/api/imoveis/routers/imovel.py`](/opt/lampp/htdocs/farm/services/api/imoveis/routers/imovel.py)
- [`services/api/imoveis/services/imovel_service.py`](/opt/lampp/htdocs/farm/services/api/imoveis/services/imovel_service.py)
- [`services/api/tests/unit/imoveis/test_imovel_router.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/imoveis/test_imovel_router.py)
- [`apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx`](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx)
- [`apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx`](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/ImoveisClient.tsx)
- [`services/api/core/services/unidade_produtiva_service.py`](/opt/lampp/htdocs/farm/services/api/core/services/unidade_produtiva_service.py)

## Migration

Nao houve migration.

## Testes Executados

- `services/api/.venv/bin/pytest services/api/tests/unit/imoveis/test_imovel_router.py services/api/tests/unit/imoveis/test_imovel_service.py services/api/tests/integration/test_exec37_auto_vinculo_fundiario.py services/api/tests/integration/test_exec38_correcao_listagem_imovel_rural.py -q`
- `pnpm exec tsc --noEmit` em `apps/web`
- `services/api/.venv/bin/alembic heads`
- `git diff --check`

## Resultado dos Testes

- `17 passed` no conjunto backend de regressao executado.
- `tsc --noEmit` concluido com sucesso.
- `alembic heads` retornou `09df6fa43b49 (head)`.
- `git diff --check` sem erros.

## Regra Implementada no CREATE

- Ao criar `UnidadeProdutiva`, se houver pelo menos um identificador fundiario, o service busca `ImovelRural` no mesmo tenant por CAR, NIRF, CCIR, SIGEF ou matricula.
- Se encontrar, reutiliza.
- Se nao encontrar, cria `ImovelRural` oficial.

## Regra Implementada no UPDATE

- Ao atualizar `UnidadeProdutiva`, o mesmo sync fundiario e executado.
- O fluxo permanece idempotente e preserva os vinculos existentes.

## Regra Implementada na Listagem de Imoveis Rurais

- A listagem oficial aceita `situacao=all` sem falha de validacao.
- O SSR da pagina de `Imoveis Rurais` agora busca a lista completa sem enviar o filtro invalido.
- O cliente exibe a matricula oficial via `numero_matricula`.

## Riscos Encontrados

- Existem alteracoes preexistentes no worktree fora deste escopo.
- O modulo de `Imoveis Rurais` ainda possui contratos legados no frontend, entao novas telas devem seguir `numero_matricula` como campo oficial.

## Pendencias Reais

- Harmonizar o modelo legado do frontend de `Imoveis Rurais` com o contrato oficial do backend em todo o modulo.
- Revisar se outras telas ainda enviam `matricula` em vez de `numero_matricula`.

## Compatibilidade Preservada

- Sim. O filtro tradicional de situacao continua funcionando.
- O auto-vinculo continua sem duplicacoes.
- O dominio operacional continua em `UnidadeProdutiva`.
- O dominio fundiario continua em `ImovelRural`.
- A ponte oficial continua em `PropriedadeImovel`.
