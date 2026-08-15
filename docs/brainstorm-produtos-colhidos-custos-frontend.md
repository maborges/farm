# Brainstorm — Consumo em frontend: custo/margem por lote (Alternativa C)

## Contexto
Backend já implementa 3 alternativas de custo/margem por lote comercializado (ver `docs/implementation/reports/OPERATIONS-GAP-01-DEEPDIVE-CUSTO-MARGEM-LOTE.md` e Seção 21 do relatório de auditoria). Alternativa C (tabela de junção auditável) foi decidida como fonte oficial. Frontend ainda não consome nenhuma das três.

## Decisões (via brainstorming com usuário)
- Página de detalhe **dedicada** por lote: `/dashboard/agricola/produtos-colhidos/[id]`.
- Acesso via **lista de lotes nova**: `/dashboard/agricola/produtos-colhidos`.
- Reconciliação de custo é **manual** (botão "Reconciliar"), a tela sempre exibe o que já está persistido (`GET .../custos`), nunca reconcilia automaticamente ao carregar.
- Override manual restrito a roles `agronomo`/`admin`, com `justificativa` obrigatória, via `AlertDialog`.

## Endpoints consumidos
- `GET /agricola/produtos-colhidos/` (lista)
- `GET /agricola/produtos-colhidos/{id}` (detalhe do lote)
- `GET /agricola/produtos-colhidos/{id}/custos` (itens + total)
- `POST /agricola/produtos-colhidos/{id}/reconciliar-custos`
- `POST /agricola/produtos-colhidos/{id}/custos/override` (agronomo/admin)

## Arquivos
1. `packages/zod-schemas/src/agricola/produto-colhido.ts` (novo) + registro em `agricola/index.ts`
2. `apps/web/src/app/(dashboard)/dashboard/agricola/produtos-colhidos/page.tsx` + `ProdutosColhidosClient.tsx` (lista, DataTable, filtros safra/commodity/status)
3. `apps/web/src/app/(dashboard)/dashboard/agricola/produtos-colhidos/[id]/page.tsx` + `Client.tsx` (detalhe, custos, reconciliar, override)
4. `apps/web/src/lib/permissions.ts` — nova chave `agricola:produto_colhido:custo_override` (admin, agronomo)
5. Sidebar — item "Produtos Colhidos" no grupo agrícola

## Ordem
zod-schemas → permissions.ts → lista → detalhe → sidebar → teste manual no browser.
