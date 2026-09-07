import type { Metadata } from "next";
import { VisaoFundiariaImovelClient } from "@/components/territorial/territorial-visao";

export const metadata: Metadata = {
  title: "Visão Fundiária - AgroSaaS",
  description: "Visão consolidada do imóvel rural com propriedades vinculadas e leitura documental.",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function VisaoFundiariaPage({ params }: PageProps) {
  const { id } = await params;
  return <VisaoFundiariaImovelClient imovelId={id} />;
}
