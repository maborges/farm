import type { Metadata } from "next";
import { PropriedadeDetalheClient } from "./propriedade-detalhe-client";

export const metadata: Metadata = {
  title: "Detalhes da Propriedade - AgroSaaS",
  description: "Gerenciamento da área operacional e dados da propriedade.",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PropriedadeDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <PropriedadeDetalheClient propriedadeId={id} />;
}
