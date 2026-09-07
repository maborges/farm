import { ImplantacaoAssistidaAuditPage } from "@/components/estoque/implantacao-assistida-client";

export default async function ImplantacaoAssistidaAuditoriaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ImplantacaoAssistidaAuditPage sessionId={id} />;
}
