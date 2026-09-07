import { ImplantacaoAssistidaDetailPage } from "@/components/estoque/implantacao-assistida-client";

export default async function ImplantacaoAssistidaSessaoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ImplantacaoAssistidaDetailPage sessionId={id} />;
}
