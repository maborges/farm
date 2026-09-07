import { ProdutoColhidoDetalheClient } from "./Client";

export default async function ProdutoColhidoDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProdutoColhidoDetalheClient produtoId={id} />;
}
