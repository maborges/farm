import type { Metadata } from "next";
import { VisaoTerritorialPropriedadeClient } from "@/components/territorial/territorial-visao";

export const metadata: Metadata = {
  title: "Visão Territorial - AgroSaaS",
  description: "Visão consolidada da propriedade com imóveis vinculados e leitura territorial.",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function VisaoTerritorialPage({ params }: PageProps) {
  const { id } = await params;
  return <VisaoTerritorialPropriedadeClient propriedadeId={id} />;
}
