# LAUNCH-W3 — Colheita → Estoque → Comercialização → Financeiro

## Auditoria realizada

Auditoria baseada no código-fonte em `services/api/agricola/`, `services/api/financeiro/comercializacao/`, `services/api/financeiro/`, `services/api/operacional/`, `apps/web/` e `apps/campo/`.

## Evidências encontradas

- `services/api/agricola/colheita/router.py` expõe CRUD de `ProdutoColhido`.
- `services/api/agricola/romaneios/service.py` materializa `ProdutoColhido` a partir de romaneio.
- `services/api/financeiro/comercializacao/service.py` implementa transições de status, reserva de `ProdutoColhido`, marcação de venda e geração de `Receita`.
- `services/api/financeiro/comercializacao/router.py` expõe CRUD e transição de status para comercializações.
- `services/api/agricola/dre/service.py` já consome comercializações para o DRE.
- `services/api/agricola/rastreabilidade/router.py` e `service.py` já conectam `ProdutoColhido` e comercializações na trilha de rastreabilidade.
- `apps/web/src/app/(dashboard)/dashboard/financeiro/page.tsx` já era a entrada financeira principal, mas não tinha atalho operacional para comercializações.

## Lacunas encontradas

- Não havia subrota operacional no frontend web para listar, criar e avançar comercializações.
- Não havia atalho explícito no painel financeiro para essa jornada.
- Os testes unitários de comercialização cobriam schema e transições permitidas, mas não provavam os efeitos canônicos de reserva de estoque e criação de receita.

## Implementações realizadas

- Criada a subrota `apps/web/src/app/(dashboard)/dashboard/financeiro/comercializacoes/page.tsx`.
- Adicionado atalho para comercializações no dashboard financeiro em `apps/web/src/app/(dashboard)/dashboard/financeiro/page.tsx`.
- Adicionado teste unitário cobrindo confirmação de comercialização, reserva de `ProdutoColhido`, geração de `Receita` e finalização da venda em `services/api/tests/unit/financeiro/test_comercializacao.py`.

## Integrações reutilizadas

- `ProdutoColhido`
- `ComercializacaoCommodity`
- `Receita`
- `PlanoConta`
- `Commodity`
- `Pessoa`

## Testes

- Teste novo de serviço para o fluxo canônico da comercialização.
- Cobertura existente de schema e transições preservada.

## Validações

- Fluxo operacional passou a ter ponto de entrada visível no web.
- O backend já possuía a regra de negócio central.
- A rastreabilidade entre comercialização, estoque colhido e financeiro foi mantida.

## Limitações remanescentes

- A interface criada é mínima e cobre o ciclo operacional principal, não um módulo comercial avançado completo.
- Não foi introduzida nova automação de eventos; o comportamento continua centralizado no serviço existente.
