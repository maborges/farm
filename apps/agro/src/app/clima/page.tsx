import type { Metadata } from "next";
import { ClimaDashboardClient } from "@/components/clima/clima-dashboard-client";

export const metadata: Metadata = {
  title: "Clima e Agrometeorologia | DeepFarms Agro",
  description:
    "Previsão do tempo, agrometeorologia horária e seleção territorial de municípios para planejamento operacional de plantio e pulverização.",
};

export default function ClimaPage() {
  return <ClimaDashboardClient />;
}
