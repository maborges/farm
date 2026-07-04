# OPS-INTELLIGENCE-09B - Atalho de Recomendações no Campo

## Auditoria inicial

| Área | Achado | Classificação |
| --- | --- | --- |
| `apps/campo/src/components/campo/bottom-nav.tsx` | Existe o menu rápido principal do Campo, com itens base e atalhos por módulo. | EXISTE E ATENDE |
| `apps/campo/src/app/(campo)/home/page.tsx` | A home já tinha o card de recomendações operacionais criado no OPS-INTELLIGENCE-09. | EXISTE E ATENDE |
| `apps/campo/src/app/(campo)/recomendacoes/page.tsx` | A tela dedicada de recomendações já existia. | EXISTE E ATENDE |
| `apps/campo/src/lib/sync/pull.ts` | Sync e Dexie já estavam ajustados no OPS-INTELLIGENCE-09. | NÃO ALTERADO |
| `services/api/campo/*` | Backend e payload já estavam integrados no OPS-INTELLIGENCE-09. | NÃO ALTERADO |

## Decisão

- O atalho rápido foi inserido no componente oficial de navegação do Campo.
- O padrão reaproveitado foi o `CampoBottomNav`, que já concentra a navegação rápida do app.
- O item novo aponta para `/recomendacoes`.
- A mudança não alterou backend, sync, Dexie ou regra de negócio.

## Implementação

- Arquivo alterado: `apps/campo/src/components/campo/bottom-nav.tsx`
- Item novo:
  - `Recomendações`
  - ícone `Sparkles`
  - rota `/recomendacoes`
- O atalho foi adicionado junto aos outros itens rápidos, mantendo o mesmo estilo visual e responsivo.

## Restrições preservadas

- Não houve alteração em sync.
- Não houve alteração em backend.
- Não houve alteração em Dexie.
- Não houve implementação de lifecycle offline.
- Não houve criação de nova funcionalidade além do atalho.

## Validação executada

- `cd apps/campo && pnpm typecheck`
- `cd apps/campo && pnpm lint`
- `cd apps/campo && pnpm build`
- `git diff --check`

## Pendências futuras

- Nenhuma pendência funcional deste recorte.
- Se a navegação do Campo ganhar novos atalhos globais, manter o padrão centralizado em `bottom-nav.tsx`.
