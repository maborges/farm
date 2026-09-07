import { redirect } from "next/navigation";

export default function OpenWeatherLegacyRedirectPage() {
  redirect("/dashboard/settings/integracoes/clima/openweather");
}
