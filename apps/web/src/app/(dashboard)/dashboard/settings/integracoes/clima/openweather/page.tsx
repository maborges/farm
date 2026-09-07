import { CloudSun } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { OpenWeatherConsole } from "@/components/integracoes/openweather-console";

export default function OpenWeatherSettingsPage() {
  return (
    <div className="p-6 flex flex-col gap-6">
      <PageHeader
        title="OpenWeather"
        description="Configure o serviço de previsão do tempo (OpenWeather) para consultar o clima nas áreas da fazenda."
        icon={<CloudSun className="h-5 w-5" />}
        breadcrumbs={[
          { label: "Configurações", href: "/dashboard/settings" },
          { label: "Integrações" },
          { label: "Clima" },
          { label: "OpenWeather" },
        ]}
      />
      <OpenWeatherConsole />
    </div>
  );
}
